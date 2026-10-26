# 安全設計 — `U22` `progress-channel`

> 單元：`U22` `progress-channel`（`library`，M）　Stage：`nfr-design`（3.3）　Depth：`Minimal`
> 本檔是設計層：描述**模式與結構**，不是實作。完整函式本體屬 `code-generation`。
> 依 stage 檔約束，程式片段限 ≤15 行的介面層示意。

---

## §〇 一句話：本單元的安全設計就是「隔離」與「不洩漏」兩件事

它**沒有授權判定**（`contract-summary.md` K-18 逐字「無受保護操作」），所以沒有
authn／authz 流程可設計。要設計的是兩個結構：

1. **隔離結構**——讓一個請求的事件在結構上不可能流到另一個請求（`SEC-1` 的承載）。
2. **錯誤出口結構**——讓例外原文在結構上沒有通往使用者的路（`SEC-2` 的承載）。

兩者都**不靠規則與自制，而靠結構**。這是本站兩個決定的共同形狀。

---

## §一 隔離結構的設計

### 設計

```python
# 介面層示意（≤15 行；完整實作屬 code-generation）
class ProgressChannelRegistry:
    _channels: dict[str, _Channel]          # 鍵由入口端傳入，本類別不鑄造

    def open(self, key: str) -> None: ...    # key 已存在 → raise DuplicateChannelKey
    async def publish(self, key: str, event: ProgressEvent) -> None: ...
    async def drain(self, key: str) -> AsyncIterator[ProgressEvent]: ...
    def close(self, key: str) -> None: ...   # 冪等
```

### 為什麼這個結構就是隔離

現狀的洩漏不是「檢查寫錯了」，是**根本沒有可檢查的東西**——`design_agent.py:31` 是
一個模組層全域，兩個請求指向同一個物件，所以「A 不該看到 B 的事件」這個命題在
資料結構上無從表達。改成 per-key dict 之後，`drain(kA)` 能取到的集合由 `_channels[kA]`
界定，**跨鍵取值需要一個不存在的操作**。

這就是為什麼 `project.md` 要求的處置是**隔離而非加授權**（`requirements.md:808` 的
IAM 列第 ④ 項逐字把它判為「跨使用者資料暴露而非單純競態」）：加授權是在一個共用
格子前面放一道檢查，而隔離是讓格子不再共用。前者多一個會寫錯的地方，後者少一個。

### `SEC-1` 的設計落點

| `SEC-1` 的要求 | 本單元的設計承擔 | 不在本單元的部分 |
|---|---|---|
| 鍵來自密碼學安全隨機源 | **無**——本類別不鑄造鍵（`_channels` 的鍵一律由參數傳入） | 鑄造在 `U13`／`U12`，`S-5` |
| 禁止可預測來源 | 以「本模組不 import `uuid`／`secrets`／`random`、無任何回傳新鍵的函式」作為結構保證（`U22-V5`） | 同上 |

**審查 `R-06` 的更正已採納**：禁止遞增計數器的理由**不是**「怕外部猜」——這個
`library` 被同進程的自家程式呼叫，沒有不受信任的呼叫端（`functional-design` 審查
`R-13` 已判定）。真正的理由是**同一行程內兩個請求的鍵必須互不碰撞、且不因重啟而
重用**：遞增計數器在重啟後從頭開始，而若有任何狀態（log、測試夾具、外部紀錄）
仍帶著舊鍵，重用會讓兩個不同請求在紀錄上無法區分。本檔以此理由取代 `nfr-requirements`
§〇 的「對外安全邊界」說法。

---

## §二 錯誤出口結構的設計 —— 兩處，不是一處

### 這一節更正了一個已凍結需求的範圍

`nfr-requirements` 的 `SEC-2` 寫 `design_agent.py:216` 是「**唯一**」的例外原文洩漏點。
**那是錯的**，審查 `R-01`（Critical）查出並經本站複驗：全檔只有兩行把例外插進字串。

```
:100  logger.exception("draw_architecture_diagram 失敗")                      ← 原文的正確出口，已存在
:101  if _progress_queue is not None:
:102  await _progress_queue.put({"type": "error", "content": "產圖發生錯誤"})   ← 正確：固定字串
:103  return f"產圖失敗：{e}"                                                  ← 洩漏（SEC-2 漏掉的）
:214  except Exception as e:                                                   ← DuplicateChannelKey 會被這裡接住
:216  yield {"type": "error", "content": f"發生未預期錯誤：{e}"}                ← 洩漏（SEC-2 點名的）
```

> 上列五行皆逐行 `sed -n` 印出比對過。**初稿把固定字串那一行寫成 `:101`，實為
> `:102`**（`:101` 是 `if _progress_queue is not None:`）——事實對、定位錯一行，
> 送審前自檢 3 抓到並更正。

`SEC-2` 的需求本文已隨 `nfr-requirements` 的收據凍結，**本站不回改它**；本節以設計
涵蓋兩處，並在 `traceability.json` 明記這是對該需求範圍的更正（與 `nfr-requirements`
承接 `functional-design` 凍結 Critical 的手法相同，只是往下一層）。

### 設計：單一出口

```
例外發生
  ├─→ logger.exception(...)        # 原文的唯一出口（:100 已是這個形狀）
  └─→ 對外的值一律為固定字串        # 不含 e、不含 repr(e)、不含 traceback
```

| 位置 | 性質 | 處置（`[Q2]`=A） |
|---|---|---|
| `:103` | **工具回傳值**，進入 LLM 的 context | 改為固定字串。`:102` 在同一個 `except` 區塊**已經是這個形狀**，所以這是消除同區塊內的不一致，不是新增限制 |
| `:216` | `yield` 給 SSE，**直送使用者** | 改為固定字串 |
| `DuplicateChannelKey`（`BR1.2` 新增） | 會被 `:214` 的 `except Exception` 接住 | 同樣經上述單一出口，故**不會**因為修法而新增一個洩漏來源 |

**為什麼 `:103` 不能「只給 LLM 看」**：LLM 的輸出直接送給使用者，所以那不是一道
邊界，而是「使用者可能看到，取決於模型當下的判斷」。`AC13.1.3` 逐字要求「回應
**不含**內部例外的原文」——若採那個選項，這條 AC 的成立條件會變成模型行為而非程式
行為，而 `project.md` 把「所有 LLM 路徑」列為本 repo 三塊**結構性**自動化盲區之一，
意即沒有任何自動化測得出它有沒有被遵守。

### 驗證設計

`SEC-2` 原本的驗證只 grep `f"發生未預期錯誤：{e}"` 這一個句型——**那個 grep 抓不到
`:103`**，所以漏掉的那一半會在閘門上長得像已經修好。本站把驗證改為**形狀級**而非
字面級：

> `design_agent.py` 內，`except` 區塊回傳或 yield 給呼叫端的值，不得由 f-string
> 插入例外變數構成。可機械檢查的近似式：對 `{e}`／`{exc}`／`str(e)`／`repr(e)` 的
> grep 結果為零（本站實測現狀為兩處命中：`:103`、`:216`）。

這個條件的好處是它**不依賴訊息文字**：日後若有人新增第三個 `except` 並插入例外，
同一條 grep 會抓到。

---

## §三 臨界區段的結構保證（`[Q1]`=A）

### 設計

```python
# 介面層示意
class _Channel:
    buffer: deque[ProgressEvent]

def _admit(channel: _Channel, event: ProgressEvent) -> None:
    """容量檢查 ＋ 丟棄 ＋ 寫入。**同步函式——在這裡寫 await 是 SyntaxError。**"""
    ...

class ProgressChannelRegistry:
    async def publish(self, key: str, event: ProgressEvent) -> None:
        ch = self._channels.get(key)
        if ch is None:
            logger.error(...)        # BR3.2：記 log 並丟棄，不崩潰、不靜默成功
            return
        _admit(ch, event)            # 整段不可被其他協程插入
```

### 為什麼這取代了「靠人遵守」

`nfr-requirements` 的 `U22-V4` 把「容量檢查與 buffer 變動之間不得有 `await`」定為
需求，而我當時記成「靠人遵守、沒有自動化會擋」（`S-4`）。審查 `R-05` 指出那句太重：
把整段抽成一個**同步 `def`**，`await` 在其中是 **`SyntaxError`**——語言層面保證，
零契約成本（`K-18` 只規定 `publish` 的 `form: async`，沒規定它內部不能呼叫同步私有
函式），零新依賴。

**本站因此把 `S-4` 的風險由「中」下調為「低」**，但**不回改**已凍結的
`nfr-requirements`；下調與其理由記在 `traceability.json` 的 `U22-V4` 列。
`U22-V4` 的驗證方式由「人工 code review」升級為「結構即保證 ＋ 一條 grep
（`_admit` 內無 `await`，而它是 `def` 故也不可能有）」。

`assert` 型的額外檢查（`[Q1]` 選項 C）被否決：`assert` 在 `python -O` 下會被移除，
且「其他協程有沒有改動」在單執行緒下需要額外的版本號欄位才驗得出來——為一個已由
結構排除的問題再加機制。

---

## §四 ADR-0006 四面向（設計層判定）

> 本表的宣告範圍是**本站的三個設計結構**（隔離結構、錯誤出口結構、臨界區段結構），
> 與 `functional-design §五`（設計決定）、`nfr-requirements §二`（需求）的宣告範圍不同。
> 四格皆有判定與理由，無空白。

| 面向 | 判定 | 設計層的處置 |
|---|---|---|
| **IAM** | **適用** | §一 的隔離結構是本單元唯一的存取控制設計。**設計選擇是隔離而非加授權**，理由見 §一（加授權是在共用格子前放檢查、多一個會寫錯的地方；隔離是讓格子不再共用）。`SEC-1` 的鑄造端半邊不在本單元（`S-5`），本站**不宣稱涵蓋它**。 |
| **Encryption** | **不適用** | 無持久化、無跨進程傳輸（`SEC-4`）。事件只存在於單一行程記憶體；其後的傳輸加密屬 `U13`。本面向在本單元**沒有標的**，不是被豁免。 |
| **Network exposure** | **不適用** | `library`，無獨立執行期；`SEC-4` 禁止新增 socket／port／進程。本 intent 的兩個新增進程邊界是 Redis 與 `U21` 的 MCP server（`requirements.md:810`），**本單元不是其中之一**。 |
| **Audit logging** | **適用（三處，其中一處是本站新增）** | ① `BR3.2`／`U22-D6`：`publish` 到不存在的通道記 **ERROR**（程式錯誤，`construction.md` 逐字「Errors must be surfaced」）。② `BR4.2`：容量丟棄記 **WARN**。③ **本站新增**：§二 的單一出口把 `logger.exception` 定為例外原文的**唯一**出口——它既是不洩漏的設計，也是稽核的設計（原文不會消失，只是不往使用者那條路走）。三處皆受 `SEC-3` 的反向約束：**不得記錄 `ProgressEvent.content`**（`xml` 是使用者的架構圖內容）。本站實測確認 backend **無任何 metrics 基礎設施**（`prometheus`／`statsd`／`opentelemetry`／`OTEL` 全樹只命中 `wa_rule_engine.py:375` 與 `wa_lens_engine.py:416` 兩處字串常值），故「可觀察」只能是 log，沒有計數器可匯出。 |

### PBT

**不適用。** 承 `requirements.md:630` 逐字。本站補一層設計層的理由：三個結構的正確性
分別由**型別**（`_admit` 是 `def`，`await` 即 `SyntaxError`）、**資料結構**（per-key
dict 使跨鍵取值需要不存在的操作）與**控制流**（單一出口）保證，皆非輸入值域的性質。

---

## §五 Assumptions & Open Questions

| id | 項目 | 落點 | `execution` | 風險 |
|---|---|---|---|---|
| `S-7` | **`SEC-2` 的範圍更正**：需求本文寫 `:216` 為「唯一」，實為 `:103` ＋ `:216` 兩處。本站以 §二 的設計涵蓋兩處並改用形狀級 grep（對 `{e}`／`{exc}`／`str(e)`／`repr(e)` 零命中）取代字面級 grep。 | `code-generation`（3.5） | **ALWAYS** | **中**。設計已涵蓋，但凍結的需求本文仍寫「唯一」；若日後有人只讀 `security-requirements.md` 而不讀本檔，會漏掉 `:103`。故具名。 |
| `S-8` | **`S-4` 的風險下調**：由「中」改「低」，因 `[Q1]`=A 的私有同步函式把它從人為規則變成語言層保證。凍結的 `nfr-requirements` 仍記「中」。 | 閘門上揭露 | — | **低**。方向是風險下降，不是上升。 |
| `S-5`（承上游） | `SEC-1` 的鑄造端驗證落在 `U13`／`U12`（皆 `CONDITIONAL`）。審查 `R-02` 指出 `code-generation` 是 **per-unit**，故該 fallback **到不了**那兩個單元。 | `U13`／`U12` 的 `nfr-requirements`；**實際可靠落點**：把斷言寫進 `U22-V3` 的 grep 範圍 | `CONDITIONAL`／`CONDITIONAL` | **中**。本站無法擴充已凍結的 `U22-V3`，故在此明記：**`code-generation` 實作 `U22-V3` 的 grep 時應一併斷言那兩個入口端以 `uuid4`／`secrets` 鑄造**。成本一條 grep。 |
| `S-1`（承上游） | buffer 上界數值 ＋ 定值前須先量 | `code-generation` | **ALWAYS** | 低 |
| `S-2`（承上游） | `run_design_agent` 的三個呼叫點全部傳入新鍵 | `code-generation` | **ALWAYS** | **高**——漏掉 `agent_router.py:125` 則主路徑未修 |
| `S-6`（承上游） | `NFR4` 不適用的判定（審查已證實理由 ① 決定性；理由 ③ 與 `requirements.md:664` 逐字的「FR4 的 Redis 往返在同一個 compose 網路內約 1ms，可忽略」相反，交付時應把 ① 放最前面） | 閘門裁決 | — | 低 |
| `S-4`（承上游，**本站下調其風險**） | `U22-V4` 的 `await` 禁令。`nfr-requirements` 記為「靠人遵守、無自動化會擋」、風險中；`[Q1]`=A 的私有同步 `def` 使它成為語言層保證，風險降為低。詳見 `S-8`。 | 已由本站 §三 的設計承擔 | — | **低**（由中下調） |

> **引用更正**：審查給我的行號是 `requirements.md:663`，我初稿直接採用而沒複驗
> ——實測 `:493` 是「與 `NFR10` 的連動（必讀）」那一行，「Redis 往返…可忽略」在
> **`:494`**。這正是 `project.md` 記載過的形狀（其他 agent 回報的結果不要照單全收），
> 而本 session 稍早我才在另一個單元指出過審查員的引用需要同等複驗。已更正為 `:494`。

### 本階段新增、已核可 scope 尚未涵蓋

**無新增能力。** 本站的兩個決定都是**把既定需求改以更強的機制承載**（`[Q1]`：註解 →
型別保證；`[Q2]`：一處 → 兩處且改用形狀級檢查），不擴大任何範圍。`scope` 仍為 12 項。
