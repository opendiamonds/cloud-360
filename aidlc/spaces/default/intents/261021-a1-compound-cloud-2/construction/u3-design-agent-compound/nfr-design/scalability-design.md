# Scalability Design — U3: u3-design-agent-compound

> Stage: nfr-design (3.3) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)

## 1. 可擴展性設計 (Scalability Architecture)
- 繪圖 Tool 呼叫採非同步背景工作調度，不阻塞 FastAPI 主事件循環，輕易承載 50+ 並發對話串流。

