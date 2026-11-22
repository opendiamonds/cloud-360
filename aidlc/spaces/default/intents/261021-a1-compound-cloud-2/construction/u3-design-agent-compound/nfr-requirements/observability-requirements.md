# Observability Requirements — U3: u3-design-agent-compound

> Stage: nfr-requirements (3.2) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)

## 1. 可觀測性 (Observability Targets)
- **結構化日誌**: 輸出包含 `session_id`, `provider="compound"`, `stage`, `elapsed_ms` 欄位之 JSON 日誌。
- **異常標籤**: 記錄 `[AGENT_ERROR]` 警報標籤供 ELK / CloudWatch 收集。

