# Distributed Tracing Configuration

> Stage: observability-setup (4.4) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

## 1. OpenTelemetry / AWS X-Ray 鏈路追蹤配置

### 1.1 Trace 傳播標準
- 採用 W3C Trace Context 協議（`traceparent` 請求標頭）。
- 鏈路節點涵蓋：
  1. `client_request`: 前端對話發起。
  2. `fastapi_router`: `/api/generate` 轉發與 RBAC 檢查。
  3. `design_agent_langgraph`: LangGraph 執行工作流與意圖識別。
  4. `diagram_builder_compound`: Hub-and-Spoke 幾何拓樸運算與 XML 序列化。
  5. `n8n_icon_service`: 外部圖示下載與 SVG 嵌入。

### 1.2 取樣率配置 (Sampling Rules)
- 混合雲產圖請求: 100% 取樣（利於除錯跨三雲座標與 n8n 連線）。
- 一般高頻心跳與健康檢查: 1% 取樣。
