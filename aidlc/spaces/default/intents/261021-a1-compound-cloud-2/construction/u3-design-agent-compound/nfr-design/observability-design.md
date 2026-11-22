# Observability Design — U3: u3-design-agent-compound

> Stage: nfr-design (3.3) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)

## 1. 可觀測性設計 (Observability Architecture)
- 整合 Python `logging` 與自訂 JSON Formatter，每筆對話日誌包含 `trace_id`, `session_id`, `provider="compound"` 與各階段 duration。

