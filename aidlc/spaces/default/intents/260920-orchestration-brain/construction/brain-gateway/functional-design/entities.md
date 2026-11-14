# Entities — `U13 brain-gateway`

> 本單元**不擁有任何持久實體**。它擁有的全部是**行程內、隨連線存亡**的執行期狀態，以及四個純值物件與兩個執行期物件（`GatewaySink`、`MemoryExecutor`）。
> 持久狀態一律在別的單元：工作階段與工作項在 `U10`／`U12` 的 Redis key（`K-09`／`K-11`）、記憶在 `U8`
> （`K-08`）、作業對象的授權在 `U7`（`K-07`）。對外線上形狀以已交付的 `backend/services/brain_ws_contract.py`
> 為準（`K-02`），本檔**不另定義任何訊息欄位**；需要擴充的欄位全部列在 `functional-spec.md` 的
> `OPEN-GW13-1`（契約追認），本檔只寫它們若成立時本單元如何使用。
>
> 為何行程內狀態不違反 `[RA:NFR4]`（「session 與工作狀態一律放 Redis」）：下表每一項都是**連線層**的狀態，
> 連線斷了它本來就該消失（`K-12` `x-disconnect-behaviour.on_drop` 逐字「重連即為新的一輪」，
> `contract-summary.md:976`）；而連線登錄放在行程內是 `K-12` 自己指定的
> （`fanout_mechanism_and_its_assumption.registry`，`contract-summary.md:933-935`）。
> 會被重啟還原檢查的三樣東西（作業對象、共享模式、歷程）全部不在本表內。
>
> **修訂 1（2026-10-12，依 `reviews/review-01.md`）**：`SubprotocolOffer` 的 PBT 性質收斂定義域（R-06）；
> `Connection` 增 `lastValidatedAt` 與背景重驗（R-07）；`PendingClarify` 增 `kind` 與 `targets`（R-01）；
> `GatewaySink` 增 `segmentId`（R-09）；新增 `MemoryPrefetch`（R-03）。
>
> **修訂 2（2026-10-12T22:45Z，依 `reviews/review-02.md`）**：`Connection` 增 `pendingOutbound`、`ConnectionRegistry` 改為 hello 後即登錄
> （R-03）；`PendingClarify.utterance` 增加作為對象掃描來源的用途（R-02）；新增 `TargetCatalog`（R-01）與 `MemoryExecutor`（R-07）。

```yaml
entities:
  - name: SubprotocolOffer
    kind: value_object
    description: >
      握手請求的 Sec-WebSocket-Protocol 標頭解析結果。由純函式 parse_subprotocol_offer 產生（BR61.2）。
    attributes:
      - name: hasProtocolName
        type: boolean
        required: true
        constraints: 客戶端提供的清單內是否**逐字**含 cloud360.brain.v1（[GW1]=A）
      - name: bearerToken
        type: string
        required: false
        constraints: >
          清單中第一個以 "bearer." 開頭的項目，以 split('.', 1) 取第二段（brain_ws_contract.py:426
          的實作陷阱）；空字串視為不存在。**只存在記憶體**，不得寫入 log、關閉原因或任何持久層（BR62.2）
    invariants:
      - "解析只讀標頭，不讀 query string（BR61.5）"
      - >-
        PBT 性質一：t 取自**非空、不含逗號、無前後空白**的 RFC 7230 token 字元集（含 "."、"-"、"_"、英數字；JWT 的
        base64url 三段即屬此集），對任意順序與項目間任意空白，parse 回 t
      - "example-based（不入 PBT）：bearer 後為空字串、只有空白、或整個標頭為空 → bearerToken 不存在"

  - name: SessionKey
    kind: value_object
    description: >
      大腦工作階段的 Redis key。由純函式 session_key_for(user_id) 產生（BR62.3），
      x-session-key-derivation 逐字「U13 在握手成功後產生」（contract-summary.md:886-887）。
    attributes:
      - name: value
        type: string
        required: true
        constraints: 形狀 "brain:session:<userId 十進位>"；userId 為正整數
    invariants:
      - "user_id_from_session_key(session_key_for(u)) == u（PBT 性質二）"
      - "u1 != u2 ⇒ session_key_for(u1) != session_key_for(u2)（一個使用者一個 session，且不撞鍵）"

  - name: Connection
    kind: runtime_state
    owner: U13 brain-gateway
    storage: 行程記憶體；連線關閉即消失
    description: 一條已 accept 的 WebSocket 連線。
    attributes:
      - name: connId
        type: string
        required: true
        constraints: secrets.token_urlsafe(16)；只用於 log 關聯，不送給客戶端
      - name: sessionKey
        type: SessionKey
        required: true
      - name: userId
        type: integer
        required: true
        constraints: 握手時驗證的使用者 id；整條連線不變
      - name: bearerToken
        type: string
        required: true
        constraints: 握手時取得；每則客戶端訊息重新驗證（BR62.1）；傳給 U12 的 bearer_token（OPEN-WO12-3 第 1 點）
      - name: principal
        type: "hierarchy_facade.Principal"
        required: true
        constraints: >
          **每則客戶端訊息重新鑄造**（mint_principal，hierarchy_facade.py:145），不沿用握手當下的快照——
          角色或核准狀態在連線期間改變時，下一則訊息即生效（BR62.1）
      - name: phase
        type: enum
        required: true
        allowed_values: [awaiting_hello, loading, ready, closing]
      - name: sendLock
        type: asyncio.Lock
        required: true
        constraints: 同一連線的送出一律序列化（BR63.4）；事件迴圈單執行緒，故用 asyncio.Lock 而非 threading.Lock
      - name: lastValidatedAt
        type: datetime
        required: true
        constraints: 最近一次重驗成功的時刻；每則客戶端訊息（BR62.1）與每 60 秒的背景重驗（BR62.6）更新
      - name: pendingOutbound
        type: "list<WsEnvelope>"
        required: true
        constraints: phase=loading 期間的扇出與推播暫存，上限 256 則，超過即 1011；ready 之後清空且不再使用（BR63.6）
      - name: pendingClarify
        type: PendingClarify
        required: false
        constraints: 至多一個；新的 user_message 到達即作廢（BR64.8）
    lifecycle: "awaiting_hello →(hello v=1) loading →(load 與 list_items 成功、送出 ready，握手結束) ready →(斷線／4401／4403 關閉) 移出登錄"

  - name: ConnectionRegistry
    kind: runtime_state
    owner: U13 brain-gateway
    storage: 行程記憶體（一個行程一份）
    description: >
      sessionKey → 存活 Connection 集合。狀態訊息扇出與伺服器發起輪次的唯一依據（BR63.1）。
      **它是單一後端行程假設的唯一承載者**：K-12 逐字「加一個 worker 或一個 replica 之後，跨連線扇出會在
      不報任何錯的情況下失效」（contract-summary.md:939-941）。
    attributes:
      - name: connections
        type: "map<SessionKey, set<Connection>>"
        required: true
        constraints: 寫＝hello 驗證通過即登錄（phase=loading，BR63.1）；讀＝扇出與 emit_turn；清＝載入失敗、連線關閉或送出失敗時移除，集合空了即刪鍵（BR63.4）
    invariants:
      - "登錄中的每一條連線 phase ∈ {loading, ready}；loading 的連線只收進 pendingOutbound，不直接送出（BR63.6）"
      - "鍵集合 ⊆ 有存活連線的 sessionKey（不留空集合）"

  - name: TurnLedger
    kind: runtime_state
    owner: U13 brain-gateway
    storage: 行程記憶體；終止後即釋放
    description: >
      一輪（一個 turnId）的終止語意守門員。純狀態機（functional-spec.md §四之二），
      由 BR64.7 定義；所有輪次訊息（token／clarify／cost_card／done／error）都經它放行。
    attributes:
      - name: turnId
        type: string
        required: true
        constraints: 伺服器以 secrets.token_urlsafe(16) 鑄造（BR64.1）；客戶端不可指定（WsClientEnvelope 無此欄，brain_ws_contract.py:685）
      - name: origin
        type: "Connection | all_connections_of_key"
        required: true
        constraints: 使用者發起的輪次＝送出那一則訊息的連線；伺服器發起的輪次（emit_turn）＝該 key 全部存活連線（BR65.3）
      - name: state
        type: enum
        required: true
        allowed_values: [open, clarifying, streaming, done, error, ended_silent]
      - name: hasContent
        type: boolean
        required: true
        constraints: 已送出至少一則非空白 token 或一張 cost_card 才為 true；done 的前提（BR64.7）
    invariants:
      - "done／error 合計至多一個（K-12 at_most_one；U2 的規則 2.7）"
      - "進入 done、error、ended_silent 後不得再放行任何輪次訊息"
      - "hasContent == false 時不得放行 done，只能 error(EMPTY_RESPONSE)"

  - name: PendingClarify
    kind: runtime_state
    owner: U13 brain-gateway
    storage: 行程記憶體，掛在 Connection 上
    description: >
      反問等待選擇時保留的上下文。select_clarify_candidate 的「candidateId 是否屬於當前輪次」
      由它判定（brain_ws_contract.py:373-374 逐字「屬 U13」）。
    attributes:
      - name: turnId
        type: string
        required: true
        constraints: 送出 clarify 的那一輪；選定後沿用同一個 turnId 交辦與終止（U2 的規則 2.14「流程回到第一步」）
      - name: kind
        type: enum
        required: true
        allowed_values: [intent, target]
        constraints: intent＝分類低於門檻的反問（BR64.8）；target＝referent 多筆相符的反問（BR64.11）
      - name: candidates
        type: "list<ClarifyCandidate>"
        required: true
        constraints: 本輪送出的候選；非空（ClarifyPayload min_length=1）
      - name: targets
        type: "map<candidateId, (projectId, systemId|null)>"
        required: false
        constraints: kind=target 時必填；選定後以它呼叫 set_work_target
      - name: decision
        type: IntentDecision
        required: false
        constraints: kind=target 時必填；選定作業對象後以原判定交辦
      - name: segmentId
        type: string
        required: true
        allowed_values: [shared, workspace, assessment]
      - name: utterance
        type: string
        required: true
        constraints: 本輪使用者原句；選定後作為 dispatch 的 utterance，kind=intent 時也是 BR64.13 對象掃描的來源；只在記憶體
    lifecycle: "建立＝送出 clarify；清除＝收到 select（任一值）、新的 user_message、或連線關閉"

  - name: GatewaySink
    kind: runtime_object
    owner: U13 brain-gateway
    description: >
      交給 U12 的 sink（work-orchestrator functional-spec.md:33-39 的三個方法）。每次呼叫 dispatch／correct／
      list_items 時新建一個，**綁 sessionKey 而不綁單一 socket**——U12 的背景工作在原連線斷線後仍會呼叫它
      （BR65.1）。
    attributes:
      - name: sessionKey
        type: SessionKey
        required: true
      - name: originTurn
        type: "TurnLedger | null"
        required: false
        constraints: 只有 dispatch 傳入的 sink 有；emit_in_turn 只能寫進這一輪（BR65.2）
      - name: segmentId
        type: "string | null"
        required: false
        allowed_values: [shared, workspace, assessment, null]
        constraints: dispatch 的 sink＝本輪段；correct 的 sink＝該工作項的段；list_items 的 sink＝null（段不明，推播不入歷程，BR65.5）

  - name: MemoryPrefetch
    kind: value_object
    owner: U13 brain-gateway
    storage: contextvars.ContextVar，僅在單一 task 的一次 classify 期間存在
    description: >
      在 await classify 之前以 to_thread 取回的記憶檢索結果（BR67.10）。注入 IntentRouter 的轉接器只讀它，轉接器內無 I/O。
    attributes:
      - name: userId
        type: integer
        required: true
      - name: query
        type: string
        required: true
        constraints: 本輪原句；只在記憶體
      - name: kinds
        type: "tuple<string>"
        required: true
        constraints: ("semantic", "procedure")，與 U11 的取用值相同（intent_routing.py:108）
      - name: hits
        type: "list<MemoryView> | failed"
        required: true
        constraints: 至多 5 筆（intent_routing.py:113）；預取失敗、逾時或熔斷開啟時為 failed，轉接器據此拋出、由 U11 降級

  - name: TargetCatalog
    kind: value_object
    owner: U13 brain-gateway
    storage: 僅在當輪存在，不快取
    description: >
      referent 與原句名稱比對用的對象目錄（BR64.12）：使用者為擁有者的專案及其系統，經 HierarchyFacade 的 list_projects 與
      list_systems 取得。
    attributes:
      - name: projects
        type: "list<(projectId, name)>"
        required: true
        constraints: 至多 50 個；超過時 truncated=true 且 systems 為空
      - name: systems
        type: "list<(projectId, systemId, name)>"
        required: true
      - name: truncated
        type: boolean
        required: true

  - name: MemoryExecutor
    kind: runtime_object
    owner: U13 brain-gateway
    storage: 行程記憶體，一個行程一個，startup 建立、shutdown 關閉
    description: 會呼叫嵌入的工作專用的有界執行器與熔斷狀態（BR67.12）。
    attributes:
      - name: maxWorkers
        type: integer
        required: true
        constraints: 4
      - name: breakerOpenUntil
        type: "datetime | null"
        required: true
        constraints: 任一次預取或寫入逾時或失敗即設為 30 秒後；成功即清為 null
```

## 摘要

| 實體 | 種類 | 持久化 | 寫／讀／清 |
|---|---|---|---|
| `SubprotocolOffer` | 值物件 | 否 | 寫：握手解析；讀：認證；清：握手結束即丟 |
| `SessionKey` | 值物件 | 否（它是別人的 Redis key） | 寫：握手後推導；讀：`U10`／`U12` 全部方法；清：TTL（`U10`） |
| `Connection` | 執行期狀態 | 否 | 寫：accept；讀：每則訊息；清：關閉 |
| `ConnectionRegistry` | 執行期狀態 | 否 | 寫：`ready`；讀：扇出；清：關閉或送出失敗 |
| `TurnLedger` | 執行期狀態 | 否 | 寫：鑄造 turnId；讀：每則輪次訊息；清：終止 |
| `PendingClarify` | 執行期狀態 | 否 | 寫：送出 clarify；讀：`select_clarify_candidate`；清：選擇、新訊息或關閉 |
| `GatewaySink` | 執行期物件 | 否 | 寫：呼叫 `U12` 前建立；讀：`U12`；清：`U12` 不再持有時由 GC 回收 |
| `MemoryPrefetch` | 值物件 | 否 | 寫：分類前預取；讀：注入 `U11` 的轉接器；清：該 task 結束 |
| `TargetCatalog` | 值物件 | 否 | 寫：需要比對名稱時取得；讀：`BR64.9`／`BR64.11`／`BR64.13`；清：當輪結束 |
| `MemoryExecutor` | 執行期物件 | 否 | 寫：startup；讀：預取與 episodic 寫入；清：shutdown |

**刻意不擁有的東西**：`BrainSession`（`U10`）、`WorkItem`（`U12`）、`IntentDecision`（`U11`）、記憶列（`U8`）、
訊息型別（`U2`）、進度通道（`U22`，見 `BR67.8`）。
