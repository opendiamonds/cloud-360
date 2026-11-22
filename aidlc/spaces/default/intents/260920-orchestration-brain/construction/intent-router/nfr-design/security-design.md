# Security Design — `U11 intent-router`

> **本檔是本站的 review artifact。** 它把 `nfr-requirements/security-requirements.md`
> 的七條需求（`NFR6.60`／`NFR7.62`／`NFR9.60`／`SEC-1`–`SEC-5`）轉成**可被實作與
> 可被測試**的設計。設計階段：程式片段 ≤15 行、介面層級。

## 一、信任邊界圖（本單元有三條邊，形狀各不相同）

```
        ┌──────────────── 同進程（可信呼叫者） ────────────────┐
        │                                                      │
   U13 brain-gateway ──classify(principal, session, text)──▶ U11
        │                                                      │
        └──────────────────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │ 唯讀                   │ 唯讀＋授權              │ 出站（信任邊界外）
         ▼                       ▼                        ▼
   U10 SessionContext      K-08 MemoryFacade        OpenRouter → Jev
   （BR7.4：不得寫）        （SEC-1：授權由它承擔）   （使用者文字離開本平台）
```

**三條邊的設計重點各自不同**，混在一起談會漏掉第三條：

| 邊 | 性質 | 本單元的義務 |
|---|---|---|
| `U13` → `U11` | **同進程**，呼叫者可信 | 不自取身分（`SEC-1`）。身分真偽由 `U13` 的 WS 握手負責——這是 `in-process` 契約的既有信任邊界，**本單元不新增也不收緊它** |
| `U11` → `U10`／`K-08` | 同進程，**唯讀** | `BR7.4`（不寫 `SessionContext`）、`NFR6.60`（不繞過 facade） |
| `U11` → OpenRouter | **跨信任邊界，出站** | `NFR9.60`（最少上下文＝資料外送最小化）。**本 intent 唯一一條把使用者自由文字送出平台的新路徑** |

## 二、七條需求的設計落法

### `SEC-1` — `principal` 由參數傳入（IAM 面）

**設計**：`classify` 的簽章第一個參數即 `principal`（`K-10` 已固定）。模組內
**不得** import `fastapi.Request`、`services.auth.get_current_user` 或任何
context-local 身分來源。

**可執行檢查**（給 `code-generation` 與 `build-and-test`）：

```python
# 結構斷言，非行為測試。檔名為暫定範例，見下方註記。
FORBIDDEN = ("get_current_user", "Request", "ContextVar")
src = Path(ROUTER_MODULE_PATH).read_text()
assert not any(f in src for f in FORBIDDEN)
```

> **檔名註記（修訂 1，審查 `R-10`）**：`intent_router.py` 是**暫定範例**，
> 實際路徑由 `code-generation` 決定——它在任何上游產出
> （`domain-design`／`contract-design`／`functional-design`）都未出現過。
> **若沿用 `_router.py` 字尾，須在模組頂部註明「非 HTTP router，無 `APIRouter`」**：
> `team.md` 的既成命名慣例裡 `*_router.py` 專指「建立 `APIRouter` 並被 `main.py`
> include」的 HTTP 路由模組，而本單元的 `SEC-2` 明寫它**沒有** `APIRouter`
> ——用那個字尾命名一個刻意無端點的模組，與慣例暗示的意思相反。

### `SEC-2` — 不暴露端點、出站只經 `langgraph_runtime`（network exposure 面）

**設計**：模組不建立 `APIRouter`，不被 `main.py` `include_router`。
出站呼叫經**路由層專用的 client factory**（見 §四），而該 factory 自己
再經 `langgraph_runtime`——**不得** `import httpx` 直打。

**為什麼要多一層 factory 而不是直接用 `openrouter_chat_model`**：見 §四 的 `TS-3a`。

### `SEC-3`／`SEC-4`／`SEC-5` — 日誌面（Audit logging 面）

**設計：白名單而非黑名單。** 日誌不是「避免記某些東西」，而是**只能記清單上的欄位**。

| 允許 | 禁止 |
|---|---|
| `capability`（封閉列舉）、`rank`、`score`、`scoresAvailable`、`len(slots)`、述詞結果、耗時、錯誤型別、`turnId`、**`memory_degraded`** | `text`、`label`、`referent`、記憶內容、prompt 全文、模型原始回應 |

**設計上的落法是一個結構化事件型別，而不是 `logger.info(f"...")`**：

```python
@dataclass(frozen=True)
class RoutingObservation:          # 欄位集合即白名單
    turn_id: str
    slot_count: int
    capability_ranks: tuple[tuple[str, int], ...]
    scores_available: bool
    can_single_out: bool
    elapsed_ms: int
    error_kind: str | None         # 型別名，不是訊息
    memory_degraded: bool          # D-1：U8 不可用時降級，必須可觀測（R-02 補）
```

**白名單寫成型別的理由**：黑名單靠紀律，型別靠編譯。`text` 不在這個 dataclass 裡，
就沒有一條路徑能把它記出去——而 `project.md` 逐字記著本 repo 為 public、
Actions log 公開可讀，**一次意外 echo 即等同公開發布**。

**`referent` 必須在禁止側，而它最容易被漏**：它看起來像識別碼，實際上是解析
使用者句子得到的系統名或圖名——那是使用者的內容。

**`SEC-4` 的 `prompt_guard` 命中事件**沿用同一個型別，`error_kind` 填
`"prompt_guard_hit"`，**不帶任何輸入衍生欄位**。它是安全事件、必須可被計數，
但計數不需要知道他說了什麼。

### `NFR6.60` — 不繞過 `MemoryFacade`

**設計**：模組內只 import `services.memory_facade.MemoryFacade`，
**不得** import `memory_service`、`memory_types` 的查詢路徑或任何 DB session 型別。
結構斷言同 `SEC-1` 的形狀。

### `NFR7.62` — `kinds` 不得含情節記憶（**現行防護**）

**設計**：呼叫 `MemoryFacade.search` 時 `kinds` 參數由**模組層的常數**提供，
不由呼叫端傳入：

```python
# 模組層常數，非參數——呼叫端無從傳入 episodic
_REFERENT_MEMORY_KINDS: Final = ("semantic", "procedure")
...
hits = facade.search(principal, query=text, kinds=_REFERENT_MEMORY_KINDS, limit=K)
```

**把它寫成常數而不是預設參數值，是刻意的**：預設值可以被覆寫，常數不行。
測試斷言 `search` 實際被呼叫時的 `kinds` 引數等於該常數。

> **這條是現行防護，不是前置護欄。** `nfr-requirements/security-requirements.md`
> §三 已以實讀推翻原本的「死碼」判定：`backend/services/memory_router.py:158-183`
> 的 `POST /api/memory/records` 已呼叫 `facade.write(kind=payload.kind)` 且
> **不限制 `kind`**，封閉集合含 `episodic`——使用者今天就能建一筆情節記憶。
> `code-generation` **第一輪就要有這個斷言**，不得遞延。

### `NFR9.60` — 最少上下文（同時是資料外送最小化）

**設計**：prompt 組裝是一個**純函式**，輸入為（作業對象名稱、最後 K 則歷程、
能力清單、使用者文字），輸出為 prompt 字串。**它不接受 `BrainSession` 整個物件**
——不給它，它就送不出去。

**這是本檔最接近「用型別擋住人」的一處**，與 `SEC-3` 的白名單 dataclass 同精神：
資料外送最小化靠「拿不到」比靠「記得不要送」可靠。

## 三、殘留缺口（如實記載，比照 `OQ-N2` 的形狀）

| 缺口 | 內容 | 為什麼不加機制 |
|---|---|---|
| **語意記憶仍可能載有產出物名稱** | `NFR7.62` 的 `kinds` 排除只關掉情節記憶。語意記憶是「事實」，原則上可含系統名或圖名；而「用記憶理解術語」與「用記憶決定 `referent`」在**模型內部不可區分** | 要關掉它只能完全不給記憶，而那會讓 `FR6.1` 的指涉詞解析失去上下文。`contract-summary.md:1434` 的 `OQ-N2` 已立下先例：「決定不加機制是可以的，不追蹤它不行」 |
| **同進程呼叫者的身分真偽** | `SEC-1` 保證本單元不自取身分，但不保證 `U13` 傳來的 `principal` 為真 | 那是 `U13` 的 WS 握手職責（`K-12`）。本單元在 `in-process` 契約下信任呼叫者——**這是既有邊界，本站只是把它寫明** |
| **記憶降級可能改變分類結果，而不只是少一點輔助**（修訂 1，審查 `R-03`，Major） | `D-1` 把記憶定性為「加分項」，隱含假設是：降級後系統會**更常反問**。但 `BR5.5` 的 `residual_gap` 自己承認，模型在**實際生成** `capability`／`referent` 時無法把「理解術語」與「決定指涉」切開。所以有記憶時模型可能（經由術語理解）把某個候選的信心推高、使 `can_single_out` 為真；降級後同一句話可能得到一個**不同但同樣自信**的答案 | **本站不發明一個功能性保險，理由具體**：審查建議的做法是「降級時提高內部門檻」，但那**預設了 `scoresAvailable` 為真**——而 `OQ-10`（路由層能否產出可比較的信心值）至今未定案（承接 `build-and-test`）。在那之前設計一個只在有分數時才成立的保險，會是一條可能永遠走不到的分支（`project.md` 記過的「不可達的規則是死碼」）。**處置**：①如實記為殘留風險；②`memory_degraded` 欄位（`R-02` 已補）使「這一輪有沒有降級」**事後可歸因**——兩次不同答案時能查出是不是記憶服務不穩；③`OQ-10` 定案後，本項與 `AC6.1.3` 一併重新檢視 |

## 四、`TS-3a` 的設計面處置：路由層專用的 client factory

`tech-stack-decisions.md` 的 `TS-3a`：Jev 的 `supported_parameters` 為**空陣列**，
而 `langgraph_runtime.openrouter_chat_model` **無條件傳 `temperature=0.0`**
（`langgraph_runtime.py:95`）。

**設計**：路由層不直接呼叫該 helper，改建一個薄 factory：

```python
def router_chat_model():
    """Jev 不吃 temperature（supported_parameters 為空陣列，TS-3a）。"""
    return openrouter_chat_model(
        model=os.environ["BRAIN_ROUTER_MODEL"],
        timeout_seconds=_timeout_sec(),
        # temperature 刻意不傳 —— 需要 openrouter_chat_model 讓它可省略
    )
```

**這帶出一個對 `U6`／共用層的要求**：`openrouter_chat_model` 目前的簽章是
`temperature: float = 0.0`，**預設值會被無條件傳下去**。要讓它可省略需要改簽章
（例如 `temperature: float | None = 0.0`，`None` 時不放進 kwargs）。
**該改動影響既有呼叫者（A1／A3／C1），不屬本單元**——記為交接事項，
承接 `U11` 的 `code-generation`（它是第一個需要它的人），並在那裡以
「不改變既有呼叫者行為」為驗收條件（預設仍是 `0.0`，只多一個 `None` 的語意）。

## 五、STRIDE 複核（對照 `nfr-requirements` 的同表，只記**設計帶來的變化**）

| 類別 | 需求階段的處置 | **設計階段的增量** |
|---|---|---|
| **S** Spoofing | `SEC-1` | 結構斷言（禁 import 清單）使它可被機械檢查，不只靠 review |
| **T** Tampering | `prompt_guard` 前置、`capability` 封閉列舉 | **新增 `len(slots)` 上界 4**（`performance-design.md` §三）——沒有它，一個失控回應可宣告 1000 個槽位而 `U12` 會照建 |
| **R** Repudiation | 不是本單元的落點 | 無變化 |
| **I** Information Disclosure | `NFR9.60`／`SEC-3` | **白名單寫成 dataclass 型別**、**prompt 組裝函式不接受整個 `BrainSession`**——兩者都從「靠紀律」改成「拿不到」 |
| **D** Denial of Service | 逾時／單次呼叫／零重試 | **`maxItems` 8 ＋ 槽位上界 4** 另外壓住輸出側 |
| **E** Elevation of Privilege | `BR7.3`（不執行能力） | 無變化。`capability` 仍只是建議，授權在 `U12` 與各能力自身 |

## 六、審查處置表（`review-01.md`，十項，`VERDICT: NOT-READY`）

**十項全部接受。** 兩個 Critical 都是**同一份產出內部的自相矛盾**，不是對外部事實的誤判。

| ID | 嚴重度 | 判定 | 處置 |
|---|---|---|---|
| `R-01` | Critical | **接受** | `logical-components.md` §一 的圖與 fallback 把 I/O 邊畫在 L2，而 §二 的表格宣稱 L2 是純函式、I/O 在外層——**同一份檔對「誰呼叫 `SessionStore`／`MemoryFacade`」給出兩個互斥答案**。保留 §二 那一個（`BR6.1` 要能用無 mock 的測試驗證），新增顯式的 **L0 fetch** 層，圖、fallback、§二 表格三處同步。Mermaid 已重新算繪驗證 |
| `R-02` | Critical | **接受** | `memory_degraded: bool` 原本**只存在於要求句裡**（`grep -c` 全站 1 處命中），兩份 `RoutingObservation` 定義都沒有它。已補進**兩份**定義 ＋ `SEC-3`／`SEC-5` 白名單 ＋ `observability-design.md` §二 新增「記憶降級率」訊號列。**`D-1` 的正當性完全建立在「降級可被觀測」這一個條件上**，條件沒落地等於判斷沒有依據 |
| `R-03` | Major | **接受，但不發明功能性保險，理由具體** | 已在 §三 殘留缺口表新增「記憶降級可能改變分類結果」一列。審查建議的「降級時提高內部門檻」**預設了 `scoresAvailable` 為真**，而 `OQ-10` 至今未定案——在那之前設計一條只在有分數時才成立的保險，會是一條可能永遠走不到的分支（`project.md` 記過的「不可達的規則是死碼」）。處置是：如實記為殘留風險 ＋ 以 `memory_degraded` 讓它**事後可歸因** ＋ `OQ-10` 定案後與 `AC6.1.3` 一併重檢 |
| `R-04` | Major | **接受** | `performance-design.md` 的槽位超界原寫「走 `BR2.4`」，而 `BR2.4` 逐字是「候選清單為空」——與 `reliability-design.md` 的 `V-3`（`MalformedRouting`）矛盾。**我在同一份產出的兩個檔案裡，對同一個檢查點指派了兩個不同的失敗型別**，而這會直接污染 `NFR3.74` 的分型失敗率。已更正 |
| `R-05` | Major | **接受，並回上游修正** | `NFR3.67` 把「連線池」與「快取」「計數器」並列為三個**同等地位**的禁止範例，而我只在下游給了一個新論證、上游原樣不動。依 `project.md` 的規則回 `nfr-requirements/scalability-requirements.md` 加註對齊修正（明記「這是對齊修正、非本站新定案」並說明原瑕疵）。**附帶**：同一條 `NFR3.67` 在上一站審查（`R-04`）被抓過一次誤讀過寬，這次是反過來——解釋掉一個明文禁止項 |
| `R-06` | Major | **接受** | V-1～V-5 **全部**作用於輸入解析，而 `EC8` 約束的是**輸出構造**（攤平時 `label` 要帶出處）——沒有一道碰到它。已刪除「缺一則 `EC6`–`EC8` 不成立」的過度宣稱，並在 `reliability-design.md` 新增 §二之二：**`label` 的出處由程式附加，不依賴模型**（依賴模型是一個無法驗證的要求），槽位任務描述由 schema 的平行 `slot_labels` 欄位提供（仍扁平，不違反 `[D1]`=A） |
| `R-07` | Minor | **接受** | 第四個歷史 ID `NFR7.63` 已補為 `N/A`。**漏掉它的原因與 `R-01` 同形**——我列舉了要宣告的 ID 而列舉不全。已改用**差集法**複驗（全掃 `NFR\d+\.\d+` 與 `SEC-\d+` 再減去已宣告集合）：35 個全掃、35 個已宣告、差集為空 |
| `R-08` | Minor | **接受** | `len(slots)` 上界 **4 由「已定案」降為「暫定」**，列為 `D-7` 交接給 `code-generation` ＋ `build-and-test`（`NFR3.73` 的槽位數分佈正是覆核工具）。審查的論點成立：我把 `[D1]`（schema 形狀）升級為使用者問題，卻把同屬「選錯會在 `code-generation` 才爆出來」性質的這一項自行定案——標準不一致 |
| `R-09` | Minor | **接受** | `reliability-design.md` §四 補上**首要理由是結構性的**：`SEC-2` 明寫不建 `APIRouter`，所以「要不要建健康檢查端點」**從來不是一個選項**；「它會說謊」降為次要理由 |
| `R-10` | Minor | **接受** | 已把 `intent_router.py` 標為暫定範例，並加註：若沿用 `_router.py` 字尾，須在模組頂部註明「非 HTTP router，無 `APIRouter`」——`team.md` 的既成慣例裡該字尾專指有 `APIRouter` 的 HTTP 路由模組，與本單元的 `SEC-2` 相反 |

**兩個 Critical 的共同形狀**：它們都是**同一份產出（或同一組產出）內部的自相矛盾**
——圖對撞表格、要求句對撞型別定義。這與 `nfr-requirements` 那一輪的兩個 Critical
（查證範圍不足、引用了會過期的事實）是**不同的類別**：那兩個是對外部事實的誤判，
這兩個是對自己寫的東西沒有做一致性檢查。`project.md` 的 `domain-design:72ea0721`
已記過這個類別（「同一份檔內的敘述與宣告自相矛盾，而六項自檢沒有一項在檢查它」），
而本輪證明那條補強**還沒有進入我實際執行的清單**。
