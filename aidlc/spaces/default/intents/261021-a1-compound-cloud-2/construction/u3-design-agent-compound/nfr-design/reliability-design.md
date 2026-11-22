# Reliability Design — U3: u3-design-agent-compound

> Stage: nfr-design (3.3) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)

## 1. 可靠度設計 (Reliability Architecture)
- 實作結構化修復狀態機：當 Pydantic validation error 發生時，將原始錯誤回灌至 LLM 進行單次重試；若失敗則轉化為結構化 SSE error 事件。

