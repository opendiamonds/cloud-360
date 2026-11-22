# Tech Stack Decisions — U3: u3-design-agent-compound

> Stage: nfr-requirements (3.2) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)

## 1. 技術選型 (Tech Stack Decisions)
- **Web 框架**: FastAPI + sse-starlette（非同步串流）。
- **資料驗證**: Pydantic v2（嚴格型別校驗）。
- **語言**: Python 3.11。

