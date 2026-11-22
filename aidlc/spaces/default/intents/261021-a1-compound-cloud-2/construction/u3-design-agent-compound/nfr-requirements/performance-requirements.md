# Performance Requirements — U3: u3-design-agent-compound

> Stage: nfr-requirements (3.2) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)

## 1. 效能指標 (Performance Targets)
- **SSE 首字響應時間 (TTFB)**: $\le 1000\text{ms}$，即時向使用者回饋 `intent_detected`。
- **整體對話與產圖延遲**: $\le 6000\text{ms}$（扣除幾何組裝與 I/O），確保端到端 $\le 8.0\text{s}$。

