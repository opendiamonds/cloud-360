# Tracing 設定

**不引入任何 tracing 套件**（[Q2]=A；不用 X-Ray、不用 OpenTelemetry）。

## 現行的關聯方式

大腦一輪對話的四跳——閘道（`U13`）→ 意圖路由（`U11`）→ 工作編排（`U12`）→ 能力 agent——**全部在同一個 backend 行程內**（上游審查已複驗：成本 agent 經 `ThreadPoolExecutor` 跑在同一行程）。分散式 tracing 要解的是跨網路多服務的問題，本鏈不是。

關聯鍵是 `turnId`：

| 跳 | 日誌事件 | 鍵 |
|---|---|---|
| 閘道 | `turn_end turnId=… outcome=…` | `turnId` |
| 路由 | `intent routing turn=…` | `turn`（同一值） |
| 編排 | `work_item=… capability=…` | `work_item`——**不帶 `turnId`**（`backend/services/work_orchestrator.py` 的 `logger.warning("work_item=%s …")` 系列，grep 實查） |

查一輪在閘道與路由的軌跡：`docker logs cloud360-backend-1 --since 1h 2>&1 | grep '<turnId>'`（結果不得貼進 public 的 issue 或 PR）。

**已知缺口**：從一輪對話追到它交辦出的工作項，目前只能靠時間相近人工對照——編排層日誌沒有 `turnId`。補法是在交辦時的那一行 `work_item=… None->處理中` 日誌加上 `turnId`（白名單內的識別碼，不含內容），列為後續工作，本站不改程式。

## 重新評估的觸發條件

照上游 `construction/intent-router/infrastructure-design/monitoring-design.md` §四：鏈路若變成跨進程（例如某個能力 agent 獨立部署、或 `mcp-bridge` 成為對話主路徑），本判斷要重做。

## 上游涵蓋

`construction/*/nfr-design/performance-design.md` 的延遲預算（2 秒端到端、路由 800 ms）以 `turn_end` 的 `preClassifyMs`／`classifyMs`／`toFirstContentMs` 三個欄位拆段，不需要 span；`security-design.md` 的日誌白名單使任何 tracing 屬性都不得帶對話內容。
