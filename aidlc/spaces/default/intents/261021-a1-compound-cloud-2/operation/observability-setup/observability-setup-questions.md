# Observability Setup Questions & Clarifications

> Stage: observability-setup (4.4) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

---

## 1. 核心指標與監控範圍 (Golden Signals & Scope)
- **延遲 (Latency)**: 追蹤畫圖 API 生成延遲、n8n icon webhook 回應延遲、前端 fitWindow 動畫耗時（<250ms）。
- **流量 (Traffic)**: 追蹤 `/api/generate` 與 `/api/generate-wa-collab` 請求量。
- **錯誤 (Errors)**: 監控 4xx/5xx HTTP 錯誤率、n8n 回退佔位圖事件、SSE 斷線異常。
- **飽和度 (Saturation)**: 後端 FastAPI 工作線程池與資料庫連線池利用率。

---

## 2. 服務等級目標 (SLO / SLI)
- **可用性 (Availability)**: 核心產圖服務可用性達 99.5%。
- **延遲 (Latency)**: 95% 的架構圖生成請求在 5 秒內完成第一階段響應。

---

## 3. 日誌與追蹤策略 (Logs & Tracing)
- **結構化日誌**: JSON 格式日誌，紀錄 request_id, user_id, provider ("compound"), latency_ms。
- **集中化查詢**: 提供針對混合雲產圖錯誤與 n8n 回退之 CloudWatch / Loki 查詢語法。

---

## Consolidated Summary Confirmation

在產出監控儀表板、告警規則與 SLO 設定前，請確認以下彙整摘要正確無誤：

- **儀表板設計**: 涵蓋混合雲請求量、生成延遲、n8n 圖示命中率與前端畫布載入表現。
- **告警設定**: 涵蓋錯誤率高於 2%、n8n 連線異常與後端異常告警。
- **追蹤與查詢**: 具備請求關聯追蹤與結構化日誌查詢設定。

Does this all look correct before I generate the observability setup artifacts?
- Looks correct
- Request changes

[Answer]: Looks correct 
