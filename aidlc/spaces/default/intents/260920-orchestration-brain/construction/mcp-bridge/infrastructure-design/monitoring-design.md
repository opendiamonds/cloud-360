# 監控設計 — `U21 mcp-bridge`

> 實作 `../nfr-design/observability-design.md` 的策略。repo **沒有** metrics 管線、告警系統或儀表板（`project.md ## Deployment` 第 4 點：
> observability、SLO／on-call 仍是真實待辦），且本版**沒有任何實際 client**（`OPEN-MB21-1`），經 bridge 的正式流量為 0。所以本站的
> 監控全部建立在三個既有來源上：容器的 `json-file` log、Docker 的健康狀態與重啟計數、`deploy.yml` 的 Actions log。本站不新增任何
> 監控元件、不新增 secret、不新增外送端點。

## 一、Metrics & KPIs（皆由既有來源導出，無收集管線）

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| 容器健康狀態（**health metric**） | `docker inspect --format '{{.State.Health.Status}}'`；compose healthcheck 每 10 秒探 `/healthz` | 非 `healthy` 即異常 | `/healthz` 在全部閘門之外（`../nfr-design/logical-components.md` §二），故並行飽和、backend 故障都**不會**讓它轉紅（`NFR21.19`、`NFR21.25`）；它轉紅只代表進程沒在服務 |
| 重啟次數 | `docker inspect --format '{{.RestartCount}}'` | 部署後兩次觀察之間 > 0 即查 | 抓兩類無聲失效：啟動自我驗證失敗（`BR71.5`，手改產物 → 退出碼 1 → `unless-stopped` 重啟迴圈）與 OOM kill（512m 上限，`infrastructure-specification.md` 第二節之二） |
| 記憶體用量 | `docker stats --no-stream`（主機上） | 穩態峰值 > 410m（上限的 80%）即重估上限 | 512m 是估計值；`DEPLOY.md` §5.6 的複量程序與 `build-and-test` 的 16 個 1 MiB 回應量測（nfr-design 審查 `R-08`）是唯二量測點 |
| 工具呼叫結果分佈（**error rate metric**） | log 的 `tool_call` 行，`outcome` 欄計數 | 本版無基準（流量 0）；`backend_unavailable`、`internal_error` 出現即逐筆查 | `outcome` 只取 `ok` 與 `BR76.1` 的七個錯誤碼（`BR77.1`）；錯誤率＝非 `ok` 行數 ／ `tool_call` 總行數 |
| 工具呼叫耗時 | `tool_call` 行的 `duration_ms` | 單筆 > 10000 即異常（超過 `NFR21.1` 的整體上限） | 驗證兩層逾時（`../nfr-design/performance-design.md` §一）在部署環境仍成立 |
| HTTP 層拒絕 | `request_rejected` 行，`reason` 計數（`over_concurrency`／`body_too_large`） | 本版無 client，任何一筆都值得查來源 | 濫用或設定錯誤的唯一紀錄（nfr-requirements 審查 `R-06` 第 2 點的收斂） |
| 啟動紀錄 | `startup port=8080 tools=3` 一行；失敗時 `startup_failed subject=…` 一行 | 每次容器啟動恰一行其一 | `NFR21.35`；`tools` 不等於 3 代表產物與部署不一致 |

`NFR21.3` 的附加時間 P50 由 `build-and-test` 在驗證拓樸上量測，不是部署環境的指標，本站不重複設置。

## 二、Alerts

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| 部署後 bridge 未健康 | `deploy` job 新步驟輪詢健康狀態 12 次（每 5 秒），最後一次仍非 `healthy` | Warning（**不讓部署失敗**） | Actions run 的 annotation 與 step summary；附 `docker compose logs mcp-bridge --tail=40`（只含 bridge 自己的單行 log，不含請求內容） |
| （無其他自動告警） | — | — | 理由：無告警管線；本版流量 0，`tool_call`／`request_rejected` 的計數沒有母體可設閾值。大腦 client 落地的後續 intent 與 Operations 的 observability 待辦一併評估 |

**為何部署後檢查只發 warning**：bridge 對使用者的影響本版為 0，而讓它擋部署會使一次與 bridge 無關的合併也被回滾（`infrastructure-specification.md` 第十節第 1 點）。
**探測只用 `docker inspect`、不呼叫 `/mcp`**：呼叫工具需要使用者 token，而本 repo 為 public、Actions log 公開可讀（與 `brain-gateway` 部署後實測不放進 workflow 的理由相同）。

## 三、SLIs / SLOs

| SLI | SLO target | Measurement window |
|---|---|---|
| 可用性：healthcheck 結果為 `healthy` 的比例 | **本版不設 SLO**（理由見下）；候選目標：99.0%，以容器健康狀態計 | 候選：30 天滾動 |
| 工具呼叫系統錯誤率：`outcome` 為 `backend_unavailable` 或 `internal_error` 的 `tool_call` 行數 ／ `tool_call` 總行數（`unauthenticated`、`agent_not_declared`、`invalid_argument`、`forbidden`、`not_found` 是呼叫端或授權的結果，不計入） | **本版不設**；候選：≤ 1% | 候選：30 天滾動 |

**不設的理由**：(1) 流量為 0，比例沒有母體；(2) repo 無 SLI 收集與告警機制，設了目標也沒有東西會在違反時發出訊號——一個沒人會被通知的 SLO
等於宣告而非承諾（`team.md` 對 80% 覆蓋率的同一判斷形狀）。候選值留給大腦 client 落地時的後續 intent 定案；Operations 階段的「SLO 須量化」護欄
屆時適用。

## 四、Logs & Tracing

| 面 | 設計 |
|---|---|
| 收集 | 容器 stderr → Docker `json-file` driver，`max-size: 50m`、`max-file: 5`（`*json_file_bounded`），單服務上限 250m；不外送、不集中化（與其餘六個服務相同） |
| 格式 | 一筆紀錄恰一行（`BridgeFormatter` 把 CR／LF 跳脫為字面 `\r`／`\n`）；本單元事件為 `<事件名> key=value …`，欄位固定順序（`../nfr-design/observability-design.md` §一） |
| 不記錄的內容 | token、簽章段、工具參數值、backend 回應本體、請求標頭、來源位址；uvicorn 存取 log 關閉（`NFR21.36`），故 10 秒一次的 healthcheck 不洗版 |
| 層級 | `cloud360.mcp_bridge` INFO；根、`httpx`、`mcp` WARNING；`mcp.server.lowlevel.server` ERROR（`NFR21.33`） |
| 查詢（主機上） | 最近的工具呼叫：`docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env logs mcp-bridge --since 1h \| grep ' tool_call '`；結果分佈：上式再 `\| grep -o 'outcome=[a-z_]*' \| sort \| uniq -c`；拒絕：`\| grep ' request_rejected '`；啟動：`\| grep -E ' startup( \|_failed)'` |
| 與 backend log 對照 | 只能依時間戳與 `duration_ms` 對照；本版不設關聯鍵（`OPEN-MB21-9` 已於 nfr-design 結案並揭露） |
| Tracing | 不設：一跳（bridge → backend）、無上游 client（`../nfr-design/observability-design.md` §七） |
| 儀表板 | 不設；以上表的查詢指令為維運者的檢視方式 |
| 保留 | 至多 5 個 50m 檔輪替；容器被刪除（`--remove-orphans`、rollback 到不含本服務的版本）時其 log 一併消失——無持久化需求，因為 log 不承載稽核主體（寫入稽核在 facade，`BR77.3`） |

## 五、上線後第一次要人工確認的事（維運者在 `192.168.10.10`，不需 token）

| # | 確認 | 通過條件 |
|---|---|---|
| 1 | 健康狀態 | `healthy`；`deploy` job 的新步驟無 warning |
| 2 | 啟動紀錄 | log 恰一行 `startup port=8080 tools=3` |
| 3 | 無對外埠、只在 `internal` | `infrastructure-specification.md` 第六節 IC-6 的三條驗證指令皆通過 |
| 4 | 記憶體 | `docker stats --no-stream` 的 `mcp-bridge` 用量寫進 `DEPLOY.md` §5.6 的複量欄 |
| 5 | 重啟次數 | 首日內為 0 |

**上游回寫（不回改上游檔，以本列為準）**：`brain-infra` `monitoring-design.md:177` 的 `mcp-bridge` 列「路徑本站刻意不訂」→ 定為 **`/healthz`**（`BR71.3`）。
