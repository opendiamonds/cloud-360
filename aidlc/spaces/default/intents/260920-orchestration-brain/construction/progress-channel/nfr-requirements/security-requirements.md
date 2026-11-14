# 安全與非功能需求 — `U22` `progress-channel`

> 單元：`U22` `progress-channel`（`library`，M）　Stage：`nfr-requirements`（3.2）　Depth：`Minimal`
> `produces_kinds` 使 `performance-requirements`／`scalability-requirements`／
> `reliability-requirements`／`observability-requirements` 對 `library` 不適用；
> 本檔承載安全需求與本單元的驗證需求。

---

## §〇 本單元的威脅模型只有一條路

`contract-summary.md` K-18 的 `behaviour_semantics.authorization_responsibility` 逐字：
**「無受保護操作——進度事件的可見性由 `request_key` 的不可猜性保證，不由授權判定」**。

把這句話的後果攤開：`drain(request_key)` **不做任何身分檢查**。拿到鍵就拿到那個請求的
全部事件。所以本單元的存取控制機制**就是鍵的產生方式**，沒有第二道。`functional-design`
只寫了「不透明且不可猜」五個字，而五個字不是可驗證的需求——`[US:V-01]` 的教訓正是
這個形狀（`FR13.1` 寫「鍵為 session 或 `thread_id`」，照字面實作完 AC 仍會紅燈，
因為那句話沒有被檢查成立）。`SEC-1` 就是把那五個字變成可檢查的東西。

---

## §一 安全需求

### `SEC-1` 鍵必須由密碼學安全的隨機來源產生

**需求**：`RequestKey` 的值必須來自密碼學安全的隨機來源。**允許**：`uuid.uuid4()`
（CPython 下走 `os.urandom`）或 `secrets.token_urlsafe()`。**禁止**：遞增計數器、
時間戳、`random` 模組、以及任何由使用者 id、`thread_id` 或請求內容推導的值。

**理由**：見 §〇。鍵是唯一的存取控制機制。

**可驗證方式**：本單元**無法**驗證它——鑄造端在 `U13`／`U12`（`[Q1]`=A：呼叫端鑄造）。
本單元能驗證的是它自己**沒有**鑄造函式。故本需求的驗證分兩半：

- 本單元側（可立刻驗）：`backend/services/progress_channel.py` 內**不存在**任何產生鍵的
  函式——鍵一律由參數傳入。這是一個 grep 條件。
- 鑄造端側：落點為 `U13`／`U12`，具名交接 `S-5`。**本站不得宣稱已涵蓋鑄造端。**

**來源**：`[Q4]`=A；`contract-summary.md` K-18 `authorization_responsibility`。

### `SEC-2` 對外的錯誤不得含內部例外原文，且必須涵蓋既有的那個洩漏點

**需求**：本單元對外回報的任何錯誤，其 `content` 必須是預先定好的固定字串，
不得由例外物件的字串表示拼接而成（承 `BR3.1`）。**並且**——這是本站新增的那一半——
`design_agent.py:216` 必須一併改掉。

**為什麼要把這一行寫進需求**：`functional-design` 的審查（`R-02`，Critical）查出
`BR3.1` 只說「對外錯誤為固定訊息」，而 `BR5.1` 的五項退場符號**不含 `:216`**，
於是實作者可以滿足全部 13 條規則而把 `:216` 原封不動留著。該行逐字為：

```
yield {"type": "error", "content": f"發生未預期錯誤：{e}"}
```

**它是唯一真正把例外原文送給使用者的那一行**（`AC13.1.3` 要關的就是它）。更要緊的是
`BR1.2` 新增的 `DuplicateChannelKey` 會被同一個 `except Exception`（`:214`）接住、
再經 `:216` 外洩——**修法本身往那條路徑上加了一個新的洩漏來源**。

**可驗證方式**：`design_agent.py` 內對 `f"發生未預期錯誤：{e}"` 這個形狀的 grep
結果為零；且 `except Exception as e` 區塊 yield 的 `content` 為固定字串。
`AC13.1.3` 的測試必須以**併發情境下真的觸發該 except** 來驗，而非只驗正常路徑。

**來源**：`AC13.1.3`、`BR3.1`、`functional-design` 審查 `R-02`（本站承接，具名 `S-3`）。

### `SEC-3` log 不得含事件的 `content`

**需求**：`BR3.2`（通道不存在）與 `BR4.2`（容量丟棄）要求的 log，其內容限於
**鍵、事件類別、累計丟棄數**。**不得**記錄 `ProgressEvent.content`。

**理由**：`xml` 類事件的 `content` 是使用者的架構圖內容；把它寫進 log 等於把本單元
要修的那個跨帳號外洩，換個出口重演一次（log 的讀者與該架構圖的擁有者不是同一群人）。
`team.md` 的 `## Forbidden` 逐字要求敏感資料不得寫進任何 log。

**可驗證方式**：log 呼叫的參數清單中不出現 `event.content` 或 `event["content"]`
（grep 條件）。

**來源**：`BR3.2`、`BR4.2`、`team.md` `## Forbidden`。

### `SEC-4` 不新增設定面、不新增機敏值、不新增進程邊界或網路暴露面

**需求**：本單元不得新增任何環境變數、secret、設定檔項目、socket、port 或進程。

**這不是空話，它排除了一個真實的選項**：`[Q1]` 的選項 C（把 buffer 上界做成環境變數）
會新增一個環境變數，而那會連帶觸發 `project.md` `## Mandated` 的部署設定義務
（`deploy/render-env.sh` 要寫它、`deploy/.env.example` 要列它、`backend/.env.example`
要記載它），也就是把 **NFR8** 由不適用變成適用。`[Q1]`=A 選了「不定數值但要求先量」，
故本需求成立且 NFR8 維持不適用。

**可驗證方式**：`scripts/validate_env_contract.py` 通過且三個 `.env.example` 的
diff 為空；`deploy/docker-compose.deploy.yml` 的服務數不變（維持 6 個）。

**來源**：`[Q1]`=A 的連帶；`unit-of-work.md:310` 逐字「行程內狀態容器，無獨立執行期」。

---

## §二 ADR-0006 安全基線四面向（本站的獨立判定）

> `project.md` 的 hard constraint 要求逐面向判定並附理由，不得僅以「已有 ADR-0006」
> 帶過。本表是本站的判定，與 `functional-design §五` 的那張表**宣告範圍不同**——
> 那一張判的是設計決定，本張判的是本站新增的四條需求。

| 面向 | 判定 | 落點與處置 |
|---|---|---|
| **IAM** | **適用** | `SEC-1` 是本單元唯一的存取控制需求。本單元不做授權判定（契約逐字「無受保護操作」），但它要修的缺陷本身是 IAM 面——`requirements.md:808` 的 IAM 列第 ④ 項逐字「`_progress_queue` 使 A 取得 B 產生的架構圖內容，這是**跨使用者資料暴露而非單純競態**」。`SEC-1` 的鑄造端半邊不在本單元，已具名 `S-5`，**本站不宣稱涵蓋它**。 |
| **Encryption** | **不適用** | 本單元無持久化、無跨進程傳輸（`SEC-4`）。事件只存在於單一行程的記憶體中；其後經 SSE／WebSocket 送出的傳輸加密屬 `U13`。本面向在本單元**沒有標的**，不是被豁免。 |
| **Network exposure** | **不適用** | `SEC-4` 明文禁止新增 socket／port／進程。對照：本 intent 確實有兩個新增進程邊界（Redis 與 `U21` 的 MCP server，`requirements.md:810` 逐字），**本單元不是其中之一**。 |
| **Audit logging** | **適用（兩處）** | `BR3.2` 的 ERROR 與 `BR4.2` 的 WARN（`[Q2]`=A 的分級）。**而 `SEC-3` 是這一面向的反向約束**——要記，但不得把使用者內容記進去。本站查證確認 **backend 完全沒有 metrics／可觀測性基礎設施**（對 `prometheus`／`statsd`／`opentelemetry`／`OTEL` 全樹搜尋只命中 `wa_rule_engine.py:375` 與 `wa_lens_engine.py:416` 兩處**字串常值**，那是在檢查使用者的架構圖有沒有提到監控工具，不是本系統的 metrics），所以「可觀察」目前只能是一行 Python `logging`，**沒有計數器可匯出、沒有儀表板會顯示它**。這個限制是 `[Q2]`=A 選擇分級（而非都記 WARN）的直接理由：WARN 在沒有 metrics 補償的系統裡實務上沒人看。 |

### PBT hard constraint

**不適用。** 承 `requirements.md:630` 逐字「`FR13.2` 併發事件互斥 — **不適用 PBT**：
它需要併發編排而非輸入空間探索」。本站補一層：本單元四個操作全部是對共享可變狀態的
操作，正確性由**交錯順序**決定而非輸入值域，而 PBT 探索的是後者。ADR-0006 點名的三個
PBT 落點（IaC generator、cost calculator、agent routing）皆不在本單元。

---

## §三 本站的驗證需求

| id | 需求 | 可驗證方式 | 承載者 |
|---|---|---|---|
| `U22-V1` | 兩個重疊請求的事件集合**互斥且各自非空** | `IsolatedAsyncioTestCase` ＋ `asyncio.Event` barrier 釘住交錯順序，**不得以 `sleep` 製造**。前例 `backend/tests/test_langgraph_migration.py`（patch `ChatAnthropic`／`build_graph`／`build_system_prompt`／`format_user_prompt`），US13 DoD 逐字「**不需新 seam**」 | 既有 `backend` job 的 `python -m unittest discover -s tests` |
| `U22-V2` | **被中途放棄**的請求結束後鍵不殘留 | 模擬客戶端斷線（關閉回應 generator 而非跑完），斷言 registry 不含該鍵。`[Q2]`=A 逐字要求以測試承載而非以推論成立 | 同上 |
| `U22-V3` | 五個退場符號 ＋ **三個呼叫點**全部處理完畢 | grep 條件。`design_agent.py` 的 `_progress_queue`／`_last_xml` 零命中、`:218` 的設 `None` 零命中、`_drain_progress` 已改寫；**且 `run_design_agent` 的三個呼叫點全部傳入新鍵**——見 `S-2`，這是 `functional-design` 的 `BR5.1` 漏掉的那一半 | CI（grep 可寫成 `backend` job 的一個步驟） |
| `U22-V4` | `publish` 的容量檢查與 buffer 變動之間**無 `await`** | `[Q3]`=A：以需求規定，並寫進**函式本體註解**（不只模組 docstring）。**本站如實記載它靠人遵守、無自動化會擋**；可做的補強是把註解放在最容易被看到的位置 | 人工 code review |
| `U22-V5` | 本單元**不含**任何鍵鑄造函式 | grep：`progress_channel.py` 內無 `uuid`／`secrets`／`random` 的 import，亦無任何回傳新鍵的函式 | CI grep ／ 人工 |
| `U22-V6` | `drain` 不得成為首字延遲的來源 | 見 §四 NFR3 列。`drain` 為純同步的 `deque` 取出迴圈，無 I/O、無 `await`；複雜度為 O(取出則數) | 人工 code review ＋ NFR3 的量測（落點 `build-and-test`） |

---

## §四 上游 NFR 的逐項適用性判定

> 十一條 inception 層 NFR 逐一判定。**一條適用、十條不適用**，每條不適用皆附理由
> （`project.md` 的「缺一不可型 hard constraint 以逐項判定表呈現，不留空白」）。

| NFR | 判定 | 理由 |
|---|---|---|
| `NFR1` 意圖識別準確率 | **不適用** | 本單元不做意圖識別。落點 `U11 intent-router`。 |
| `NFR2` 跨頁面上下文保留率 | **不適用** | 本單元無跨頁面上下文；它的狀態生命週期等於**單一請求**。落點 `U10 session-store`。 |
| `NFR3` 首字回應時間 P50 ≤ 2 秒 | **適用（間接，但真實）** | 進度事件經 `drain` 流向使用者，**本單元在首字路徑上**。若 `drain` 阻塞或做 I/O，它會直接計入 `NFR3` 量測的那個差值（`requirements.md:652-490`：送出時刻 → 收到第一個內容 token 的時刻）。處置為 `U22-V6`。**本站不自行定本單元的延遲預算**——`NFR3` 是端到端門檻，把它切成各單元的子預算需要全鏈的資料，本站沒有；故本站只要求「不引入 I/O 與 `await`」這個可檢查的必要條件。 |
| `NFR4` 狀態外部化與重啟還原 | **不適用——但這一格需要明講，因為字面看起來相反** | `NFR4` 逐字「大腦的 session 與工作狀態**一律放 Redis，不得放行程記憶體**」，而 `unit-of-work.md:310` 把本單元逐字定義為「**行程內狀態容器**」。**兩句話字面對撞，判定為不適用的依據有三層**：① `NFR4` 的主詞是「session 與**工作狀態**」，其可測不變量逐字為「**重啟 backend 後，既有對話的脈絡與作業對象仍可完整還原**」——本單元持有的是**單一請求內的暫態進度事件**，重啟會讓那個請求本身消失，沒有「還原」的對象。② `NFR4` 自己的排除清單逐字點名三處既有行程內狀態容器**不在本 intent 範圍內、維持原狀**，其中包含 `advice_orchestrator` 的 `_progress`——而 `K-18` 的 `shape_precedent` 正是要本單元**沿用那個形狀**。把本單元的 buffer 放進 Redis 會與該排除清單的精神相反。③ 把暫態進度事件寫進 Redis 會為每一則進度訊息新增一次網路往返，直接損害 `NFR3`。**處置**：本判定連同三層理由寫進本檔，使下游不會把「`U22` 是行程內狀態容器」讀成 `NFR4` 的違反。若使用者認為此判定有誤，它會改寫整個單元的形狀，故列為具名開放項 `S-6`。 |
| `NFR5` WebSocket 契約閘門 | **不適用** | 本單元不擁有任何 WS 訊息型別。`ProgressEvent` 的四種 `type` 是**行程內**的形狀，送出前由 `U13` 轉成 WS 訊息；WS 契約閘門屬 `U2 brain-ws-contract`（已交付）與 `U13`。 |
| `NFR6` 記憶層 schema 隔離與其驗證 | **不適用** | 本單元無 schema、無資料表、不碰資料庫。落點 `U5 memory-data`。 |
| `NFR7` episodic memory 的保存與刪除稽核 | **不適用** | 本單元無持久化，沒有「保存期」這個概念——buffer 的壽命是單一請求。落點 `U5`／`U9 memory-purge`。 |
| `NFR8` 新增元件的部署設定完整性 | **不適用，且這是一個選擇的後果而非既定事實** | `SEC-4` 禁止新增環境變數。**但 `[Q1]` 的選項 C 會讓它變成適用**——把 buffer 上界做成環境變數即觸發 `render-env.sh` ＋ 兩個 `.env.example` 的同步義務。`[Q1]`=A 選了「不定數值但要求先量」，故本條維持不適用。記此以免下游在實作時「順手」把上界做成可配置而不知道它帶著一條 blocking 義務。 |
| `NFR9` 成本原則 | **不適用** | 本單元不呼叫任何 LLM、不選模型。 |
| `NFR10` 路由層模型的可替換性 | **不適用** | 本單元與模型選擇無關。 |
| `NFR11` 跨功能任務的頁面切換次數 | **不適用** | 本單元無 UI。 |

---

## §五 Assumptions & Open Questions

| id | 項目 | 落點 | `execution`（已查 `stage-graph.json`） | 風險 |
|---|---|---|---|---|
| `S-1` | **buffer 上界的數值，以及「定值前必須先量」的義務。** `[Q1]`=A：`code-generation` 定值前須實跑一次典型產圖、記下 `progress` 事件的實際則數、上界取該數的某個倍數，**且測量值與倍數都要寫進程式註解**。 | `code-generation`（3.5） | **ALWAYS**，不需轉移目標 | **低**。本站把它由「待辦」升級為「有驗收條件的待辦」——驗收條件是註解裡有那個測量值。 |
| `S-2` | **`run_design_agent` 的三個呼叫點**。`functional-design` 的 `BR5.1` 只列了 `wa_collab_orchestrator.py:79`，實測有三處：`agent_router.py:125`（**使用者路徑的真實 SSE 入口**）、`wa_collab_orchestrator.py:79`、`backend/test_agent.py:41`。**三處都必須傳入新鍵。** | `code-generation`（3.5） | **ALWAYS** | **高——這是本單元能否真的修好主路徑的分水嶺**。漏掉 `agent_router.py:125`：新參數若必填則該端點直接壞，若選填則它的事件全部走 `BR3.2` 的記 log 丟棄，`AC13.1.1` 的「各自非空」必紅。已寫進 `U22-V3` 的 grep 條件。本項承接 `functional-design` 審查的 `R-01`（Critical）——該產出已終局凍結、無法回改，**本站以具名需求承接它**。 |
| `S-3` | **`design_agent.py:216` 的例外原文洩漏點。** 見 `SEC-2`。`BR5.1` 的五項退場符號不含它，而它是唯一真正外洩的那一行；且 `BR1.2` 新增的 `DuplicateChannelKey` 會經同一條路徑外洩。 | `code-generation`（3.5） | **ALWAYS** | **高**。承接 `functional-design` 審查的 `R-02`（Critical），同樣以具名需求而非回改凍結產出的方式處理。`AC13.1.3` 的測試必須真的觸發 `:214` 的 `except`，否則修後會綠而機制還活著。 |
| `S-4` | **`U22-V4` 的 `await` 禁令靠人遵守，無自動化。** `[Q3]`=A 選的是「以需求規定並寫進函式本體註解」而非 `asyncio.Lock`。本站如實記載這個取捨：它防的是一個「只要不寫 `await` 就不存在」的問題，加鎖會讓熱路徑多一次 `await`，但代價是規則沒有機制保證。 | `code-generation`（3.5）＋ 人工 code review | **ALWAYS** | **中**。失效是安靜的（偶爾多出或少掉一則事件），而本單元存在的全部理由就是修一個安靜失效的缺陷。若日後觀察到事件計數異常，第一個該查的就是這裡。 |
| `S-5` | **`SEC-1` 的鑄造端半邊**：鍵由 `U13`／`U12` 鑄造，故「必須用密碼學安全隨機來源」這條需求的驗證落在那兩個單元，不在本單元。本站只驗「本單元不含鑄造函式」（`U22-V5`）。 | `U13 brain-gateway`／`U12 work-orchestrator` 的 `nfr-requirements` | 兩者皆 **CONDITIONAL** | **中**。CONDITIONAL 代表可能被 skip。**轉移目標**：`code-generation`（`ALWAYS`）。若兩單元的 `nfr-requirements` 皆被 skip，判定 skip 的人須把 `S-5` 重新提交給使用者——本單元的唯一存取控制機制不能沒有落點。 |
| `S-6` | **`NFR4` 判定為不適用的三層理由**（見 §四）。若使用者認為該判定有誤（即認為 buffer 也該外部化到 Redis），它會改寫整個單元的形狀——不只是加一個 Redis 呼叫，而是讓一個 `library` 變成有外部依賴的元件，並直接損害 `NFR3`。 | 使用者於閘門裁決 | — | **低**（我對三層理由有信心），但後果大，故具名而非埋在散文裡。 |

### 本階段新增、已核可 scope 尚未涵蓋

**無新增能力。** 四條安全需求與六條驗證需求全部落在 `FR13` 與契約 `K-18` 的既有範圍內。
`S-2` 與 `S-3` 是**承接審查已查出的缺口**而非新增範圍——它們要修的本來就在 `FR13` 的
射程內（`FR13.2` 的互斥、`AC13.1.3` 的不外洩），只是 `functional-design` 的規則漏了
具體落點。`scope` 仍為 12 項能力，`FR13` 依 `requirements.md:524` 逐字「它不增加能力總數」。
