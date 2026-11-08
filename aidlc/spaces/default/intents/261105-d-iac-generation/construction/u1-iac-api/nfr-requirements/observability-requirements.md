# Observability Requirements — u1-iac-api

> Unit: `u1-iac-api`（service）· Q6=A · 承接 inception NFR7。

## 日誌（必做）

| ID | 需求 |
|---|---|
| NFR7.1 | Logger 前綴 `cloud360.iac.*`（對齊 NFR6）。 |
| NFR7.2 | 每請求必有：`request_id`、`user_id`（或 hash）、`diagram_id`、`route`、`status_code`、`error.code`（若有）、`duration_ms`。 |
| NFR7.3 | D1 可另記：`model`、粗量 token／latency；**禁止** prompt 全文、密文、完整 HCL。 |
| NFR7.4 | Agent／API 失敗須能在伺服器 log 與 U2 步驟錯誤碼對上（同一 `error.code` 或 `request_id`）。 |

## 指標與追蹤（本輪不做）

| ID | 聲明 |
|---|---|
| NFR7.5 | **暫無** Prometheus／RED 指標義務（Q6≠B）。 |
| NFR7.6 | **暫無** OpenTelemetry 分散式 tracing 義務（Q6≠C）。 |

## 告警

- 本 Bolt 不新增獨立 on-call 告警規則；依賴既有主機／容器日誌管線即可。
- 若 staging 已有 log-based 告警，可對 `error.code=generate_timeout` 等加規則——**非**本 unit 阻擋項。

## 不做

- 密文／JWT／檔案全文進 log。
- 以 message 字串作為唯一可觀測關聯鍵。

<!-- confirmed: Looks correct -->
