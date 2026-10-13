# 觀測需求 — `U13 brain-gateway`

## 〇、本單元的觀測面

使用者看得到的是訊息本身。觀測需求是給**維運者與 `build-and-test` 的量測**：一輪的時間花在哪一段（`NFR13.1` 的歸因）、
記憶預取為什麼沒生效（`NFR1` 準確率在本單元的失敗形式：**預取靜默失敗會讓分類不帶記憶，而畫面上看不出來**）、連線為什麼
被拒或關閉。所有 log 同時受 `NFR13.15` 的禁令約束——只能出現 `BR67.3` 的允許欄位：`connId`、`sessionKey`、`turnId`、訊息
`type`、error code、關閉碼、例外類別名稱、`elapsedMs`（及其分段）、計數。

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR13.34`** | logger 名稱為 `"cloud360.brain_gateway"`（`BR67.3`；`team.md ## Code Style` 的新模組慣例），兩個新模組共用 | grep 本單元模組的 `getLogger` 引數：恰為該字串，無 `__name__` |
| **`NFR13.35`** | 每個使用者輪次結束時記**恰一筆** INFO，欄位：`turnId`、`preClassifyMs`、`classifyMs`、`toFirstContentMs`（自 `classify` 回傳到第一則內容或 `clarify` 送出；攔截輪次為 null）、`outcome`（`done`／`error:<code>`／`clarify`／`ended_silent`／`guard`）、`prefetch`（`hit`／`empty`／`failed`／`breaker_open`／`busy_skipped`）。這是 `NFR13.1` 的量測來源，也是 `NFR3` 端到端差額的歸因依據（`intent-router` `performance-requirements.md:103-108` 指出無歸因力的切分等於沒切） | `classify` 替身睡 200 ms、預取替身睡 100 ms：該輪恰一筆 INFO，`classifyMs ≥ 200`、`preClassifyMs ≥ 100`，三段皆為整數，`outcome == "done"`、`prefetch == "hit"`；熔斷開啟時 `prefetch == "breaker_open"`；攔截輪次 `outcome == "guard"` 且 `classifyMs` 為 null |
| **`NFR13.36`** | 連線生命週期：accept、ready、關閉各記 INFO（`connId`、`sessionKey`、關閉碼）；拒絕升級（無協定名、全域上限、每 key 上限）記 INFO 並帶原因類別；訊框過大與超頻各記 INFO 計數 | 依序觸發 4401、4403、4400、1011、未 accept（無協定名）、全域上限各一案：每案恰一筆對應的 INFO，含關閉碼或原因類別，不含 token（與 `NFR13.15` 同一套標記檢查） |
| **`NFR13.37`** | 記憶熔斷開啟記 WARNING（含觸發的例外類別名）、關閉記 INFO；熔斷期間與執行器滿而跳過的次數以計數記錄，**不逐則記 WARNING**（避免 Ollama 停擺時每則訊息洗版） | 以假時鐘觸發一次開啟、30 秒內 5 則訊息、再成功一次：恰 1 筆開啟 WARNING、恰 1 筆關閉 INFO，期間 5 則訊息未各自產生 WARNING |
| **`NFR13.38`** | `turnId` 是一次交辦的關聯鍵：傳入 `classify(..., turn_id=T)` 與 `dispatch(..., turn_id=T)`，並出現在本單元該輪的每一筆 log（承接 `D8-6` 的本單元一半；`MemoryFacade.search` 自身的 log 無此欄，屬 `OPEN-GW13-8` 的 `nfr-design`） | 替身記錄收到的 `turn_id`：`classify` 與 `dispatch` 收到的值等於客戶端收到的該輪 `turnId`；該輪擷取到的本 logger 紀錄全部帶相同 `turnId` |

## 刻意不設的目標

| 不設 | 理由 |
|---|---|
| metrics／告警管線 | repo 尚無 metrics 管線（`project.md ## Deployment`：observability 仍是真實待辦）；本單元以結構化 INFO 提供 `build-and-test` 可統計的原料，不單獨建立 |
| 分散式追蹤 | 呼叫皆在同一行程內，`turnId` 已足以串起一輪；`U12` 的 `workItemId` 串起背景工作（`NFR12.25`） |
| 記錄每則訊息的內容長度分佈 | 對容量規劃有用但非本單元的失敗診斷所需；`NFR13.19`／`NFR13.20` 的拒絕計數已涵蓋異常面 |
