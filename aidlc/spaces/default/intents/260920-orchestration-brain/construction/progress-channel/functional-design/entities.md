# 實體模型 — `U22` `progress-channel`

> 單元：`U22` `progress-channel`（`library`，M）　Stage：`functional-design`（3.1）
> 本單元**無持久化**：下列實體全部是行程內狀態，無資料表、無跨行程可見性
> （`contract-summary.md` K-18 `observable_side_effects` 逐字「行程內狀態的建立與移除；
> 無持久化、無跨行程可見性」）。「實體」在此指**資料形狀與其不變量**，不是 DDL。

---

## 來源真實（機讀）

```yaml
entities:
  - name: RequestKey
    kind: value_object
    description: >
      單一請求的進度通道識別字。由入口端（`U13 brain-gateway`／`U12 work-orchestrator`）
      鑄造，一路以顯式參數傳遞至寫入端與讀取端；本單元不自行推導它（[Q1]=A）。
      它與 `thread_id` **並存且語意分離**——`thread_id` 繼續承載 LangGraph
      checkpointer 的對話記憶分區，本鍵只承載進度通道的隔離。
    attributes:
      - name: value
        logical_type: text
        required: true
        unique: true
        constraints: >
          **不透明且不可猜**。可見性由不可猜性保證、不由授權判定承擔
          （`contract-summary.md` K-18 `authorization_responsibility`）。
          **禁止的取值來源**（`key_contract.forbidden_keys` 逐字）：
          `thread_id`——`agent_router.py:125` 為 `f"user-{current_user.id}-design"`，
          是 **per-user**，且 `design_agent.py:198` 的
          `config = {"configurable": {"thread_id": thread_id}}` 證實它就是
          checkpointer 的 thread 鍵，改成 per-request 等於關掉對話記憶；
          「session」——`run_design_agent` 的簽章裡不存在這個參數（`[US:V-01]`）。
    entity_constraints:
      - "同一個 `value` 在同一時刻最多對應一個存活的 ProgressChannel
         （由 BR1.2 的 `DuplicateChannelKey` 承擔，不是靜默覆寫）"

  - name: ProgressEvent
    kind: value_object
    description: >
      一則要串流給使用者的事件。沿用 `design_agent.py` 既有的四種 `type`，
      不新增也不改名——改名會讓 `wa_collab_orchestrator.py:80-90` 的 remap 失效。
    attributes:
      - name: type
        logical_type: enumeration
        required: true
        allowed_values: [progress, xml, message, error]
        constraints: >
          取值集合來自既有程式：`progress`（`design_agent.py:82`／`:85`）、
          `xml`（`:97`）、`error`（`:102`），`message` 由 `:206` 的主迴圈直接 yield
          而不經佇列。**本欄決定該事件可否被容量壓力丟棄**——見 BR4.1。
      - name: content
        logical_type: text
        required: true
        constraints: >
          **不得含內部例外原文**（BR3.1，`AC13.1.3`）。現狀的 `AttributeError`
          原文被送進 SSE 給使用者，這是獨立的 ADR-0006 面。
    entity_constraints:
      - "本物件不可變。壓力下的處置是**丟棄整則**，不是截斷或改寫 content"

  - name: ProgressChannel
    kind: entity
    description: >
      單一請求的事件通道。生命週期與該請求等長：入口端 `open`，請求結束
      `close`（ADR-014）。
    attributes:
      - name: key
        logical_type: identifier
        required: true
        references: RequestKey
        constraints: "建立後不可變"
      - name: buffer
        logical_type: ordered_collection
        required: true
        default: empty
        constraints: >
          FIFO 順序。**有限上界**（[Q4]=A）——容量值本站不定（見
          `functional-spec.md §六` 的 `OQ-P1`，理由是它取決於 agent 的步數，
          而步數本站無依據可算）。滿載時的處置：丟棄**最舊的 `progress` 類**事件；
          `xml` 與 `error` **永不丟棄**（BR4.1）。
      - name: is_open
        logical_type: boolean
        required: true
        default: true
        constraints: >
          `close` 後為假。**已關閉與從未存在在對外行為上不可區分**——兩者的
          `drain` 都回空迭代器、`publish` 都是記 log 並丟棄（BR2.4、BR3.2）。
          這是刻意的：讓呼叫端能分辨會洩漏「那個鍵曾經存在」。
    entity_constraints:
      - "`buffer` 內的每一則 ProgressEvent 都必須是**經本通道的 `key` 寫入**的
         ——這就是 `AC13.1.1` 互斥不變量的資料層形式"
      - "`drain` 為**破壞性**讀取（[Q3]=A）：事件一經取出即自 `buffer` 移除，
         不保證重放。斷線重連是否補事件屬 `U13` 的對外協定，不是本實體的決定"

  - name: ProgressChannelRegistry
    kind: entity
    description: >
      全部存活通道的集合。取代 `design_agent.py:31` 的模組層全域
      `_progress_queue`（`FR13.1`）。
    attributes:
      - name: channels
        logical_type: keyed_collection
        required: true
        default: empty
        constraints: >
          形狀沿用 `backend/cost/advice_orchestrator.py:23-24` 的 per-key dict
          （`_progress: dict[int, dict[str, Any]] = {}`）。
          **不照抄它的 `threading.Lock`**（`:24`）：那支檔案用 Lock 是因為它有
          `ThreadPoolExecutor`（`:21` 的 `_executor`），本單元跑在**單執行緒的
          asyncio 事件迴圈**上，在那裡 `threading.Lock` 是 cargo cult 且會在
          `await` 邊界給出錯誤的安全感。鍵的型別亦不同（它是 `set_id` 的 int，
          本單元是不透明的 per-request 識別字）。
    entity_constraints:
      - "本集合的大小**必須隨請求結束而下降**。只寫不刪會把跨使用者錯送
         換成無上界的記憶體成長，即修掉一個失敗模式換來另一個（ADR-014）"

relationships:
  - "ProgressChannelRegistry 1 — 0..N ProgressChannel（以 RequestKey 為鍵）"
  - "ProgressChannel 1 — 0..N ProgressEvent（FIFO buffer，破壞性讀取）"
  - "RequestKey 1 — 0..1 ProgressChannel（同一時刻；由 BR1.2 保證）"
```

---

## 人讀摘要

四個實體，兩個是 value object（`RequestKey`、`ProgressEvent`），兩個是 entity
（`ProgressChannel`、`ProgressChannelRegistry`）。全部是行程內狀態。

**這個模型存在的唯一理由是把一個共用的格子換成一組各自獨立的格子。** 現狀
`design_agent.py:31` 只有一個 `_progress_queue`，所有請求共用；四個寫入端
（`:81`、`:84`、`:96`、`:101`）讀的都是那個模組全域，讀取端 `:203`／`:211`
把全域當引數傳進 `_drain_progress`——而**引數在呼叫當下才取值**。於是後到的請求在
`:183` 覆寫全域之後，先到的請求讀到的是後到者的佇列。

| 本站的決定 | 來源 |
|---|---|
| 鍵由入口端鑄造、顯式參數傳遞，本單元不推導 | `[Q1]`=A |
| 清除由呼叫端 `try/finally` 擁有，並加一條「被放棄的請求結束後鍵已消失」的測試 | `[Q2]`=A |
| `drain` 為破壞性，不支援重播 | `[Q3]`=A |
| `buffer` 有限上界；滿載丟最舊的 `progress`，`xml`／`error` 永不丟棄 | `[Q4]`=A |

**上界的數值不在本站定案**——它取決於單一 `run_design_agent` 呼叫能產生多少則
`progress`，而那由 agent 的步數決定，本站沒有量過也沒有依據可算。依
`delivery-planning:dp-L1`（任何可被計算的數字要能指出它由哪段程式算出來），
寧可把它記為具名開放項（`OQ-P1`，見 `functional-spec.md §六`）而不是寫一個看起來
合理的數字。本站定的是**性質**：有上界、丟棄有優先序、丟棄留痕。

### 既有符號的退場（`[CD4]`=A，契約層已宣告）

本單元完成的判準有一半在**既有程式裡的符號消失**，而那是可 grep 的條件
（`contract-summary.md` K-18 `completion_criterion`）。五項：

| 路徑 | 符號 | 處置 |
|---|---|---|
| `design_agent.py:31` | `_progress_queue` | **刪除**，由本模型取代 |
| `design_agent.py:32` | `_last_xml` | **刪除**（死狀態，從未被讀取；US13 DoD 要求一併清理，避免下一個人沿用同一形狀） |
| `design_agent.py:160` | `_drain_progress`（`:163` 的 `get_nowait()` 是崩潰點） | **改寫**為呼叫 `ProgressChannel.drain` |
| `design_agent.py:218` | 把全域設為 `None` | **刪除**，改為 `ProgressChannel.close(request_key)` |
| `wa_collab_orchestrator.py:79` | `run_design_agent(messages, current_xml)` | **補傳** per-request 的鍵 |

`design_agent.py:169` 的 `memory = MemorySaver()` **保留**——它是 LangGraph
checkpointer 的模組層單例，不是外洩路徑；列在此處是因為改 `thread_id` 語意時
必須把它一起看，而本單元不改它。
