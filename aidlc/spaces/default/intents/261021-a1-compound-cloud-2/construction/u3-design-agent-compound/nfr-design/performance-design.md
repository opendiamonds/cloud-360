# Performance Design — U3: u3-design-agent-compound

> Stage: nfr-design (3.3) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)

## 1. 效能架構設計 (Performance Architecture)
- 透過 FastAPI `StreamingResponse` 與 Python `asyncio` 生成器，在意圖解析完成後立即推送首字 SSE 事件，確保 TTFB $\le 1000\text{ms}$。

