# Monitoring Design — U3: u3-design-agent-compound

> Stage: infrastructure-design (3.4) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)

## 1. 監控指標與告警閾值 (Metrics & Alerts)
- **指標項**:
  - `agent_stream_connections_total`: 當前在線 SSE 連線數。
  - `agent_intent_classification_latency_ms`: 意圖識別耗時。
  - `agent_error_count{reason="rbac_denied"}`: RBAC 攔截計數。
- **告警閾值**: 連續 5 分鐘錯誤率 > 2% 觸發警告。

