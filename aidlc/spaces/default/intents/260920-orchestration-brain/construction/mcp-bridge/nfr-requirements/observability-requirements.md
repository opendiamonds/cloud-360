# 觀測需求 — `U21 mcp-bridge`

> `NFR21` 的 parent id 理由與判準前提見 `performance-requirements.md` 檔頭。

## 〇、本單元的觀測面

觀測需求是給**維運者與 `build-and-test` 的量測**：一次工具呼叫的結果是什麼、花了多久、誰（哪個 agent）發起、為什麼被拒。
所有 log 同時受 `NFR21.8` 的禁令約束——只能出現 `BR77.1` 的允許欄位：`tool`、`agent`（正規化值）、`outcome`、`http_status`、
`duration_ms`；不得含 token、工具參數（含 `system_id`）、backend 回應本體、例外文字（`BR77.2`）。依 `[MBN1]`=A，log **不含**任何
使用者識別（`NFR21.18`），故讀取的事後追查只到「哪個時刻、哪個工具、哪個 agent」（`security-requirements.md` 第五節）。

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR21.33`** | （`BR77.1`、`BR77.2`；`team.md ## Code Style`）bridge 的 logger 名稱為 `"cloud360.mcp_bridge"`；`configure_logging()` 把 `httpx` 與 `mcp` 的 logger 設為 WARNING 以上（httpx 在 INFO 會記錄含 `system_id` 的請求 URL） | grep `backend/mcp_bridge/` 的 `getLogger` 引數：只有 `"cloud360.mcp_bridge"`，無 `__name__`；呼叫 `configure_logging()` 後 `logging.getLogger("httpx").getEffectiveLevel()` 與 `"mcp"` 者皆 ≥ `WARNING` |
| **`NFR21.34`** | （`BR77.1`；帶入項 `R-19`）每一次 `tools/call`——含本地拒絕（`unauthenticated`、`agent_not_declared`、`invalid_argument`）、SDK 預先驗證的拒絕、backend 各狀態、未預期例外——**恰好**產生一行 INFO，欄位集合恰為 `{tool, agent, outcome, http_status, duration_ms}`；`agent` 只取已登錄名、`undeclared`、`unregistered`（不寫原值，防 log 注入）；`outcome` 為 `ok` 或 `BR76.1` 的錯誤碼；`http_status` 為 backend 狀態碼或 null | 對 `NFR21.8` 觸發的每一分支，收集 `cloud360.mcp_bridge` 的 INFO 紀錄：每次工具呼叫恰 1 筆，且其結構化欄位（`extra`）鍵集合恰為上述五個。`X-Cloud360-Agent: "evil\nINJECTED"` 一案：`agent` 為 `unregistered`，全部 log 文字不含 `INJECTED`。`duration_ms` 為非負整數 |
| **`NFR21.35`** | （MB-W1；`BR71.5`）啟動成功記一行 INFO（只含埠與載入的工具數）；`BR71.5` 失敗記一行 ERROR，只含違規的工具名或 agent 名，然後非零退出 | 正常啟動：恰一筆啟動 INFO，含工具數 `3`；`NFR21.6` 的四份手改產物：各恰一筆 ERROR，內容除固定字串外只出現工具名或 agent 名（以白名單比對） |
| **`NFR21.36`** | uvicorn 的存取 log 關閉（`access_log=False`）：每次請求已有 `NFR21.34` 的一行，存取 log 重複且使 compose healthcheck 每 30 秒洗一行 | uvicorn 以程式方式啟動的參數含 `access_log=False`（grep）；驗證拓樸下打 5 次 `/healthz`，`uvicorn.access` logger 收集到 0 筆 |

## 刻意不設的目標

| 不設 | 理由 |
|---|---|
| bridge 與 backend log 的關聯鍵（請求 id） | `OPEN-MB21-9` 已指派 `nfr-design`（→ `code-generation`）；加請求 id 需 backend 也記錄它，越出本站 |
| metrics／告警管線 | repo 尚無 metrics 管線（`project.md ## Deployment`：observability 仍是真實待辦）；本單元以結構化 INFO 提供 `build-and-test` 可統計的原料（`NFR21.3` 的附加時間量測、各錯誤碼計數） |
| 分散式追蹤 | 一次工具呼叫只有 bridge → backend 一跳；本版無上游 client 可串接 |
| 讀取的使用者稽核 | `[MBN1]`=A |
| `/healthz` 與 `tools/list` 的 log | 免認證、無副作用的面；記錄只會被 healthcheck 洗版。異常由 compose 的健康狀態呈現（`NFR21.32`） |
