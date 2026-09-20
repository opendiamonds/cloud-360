# Tech Stack Decisions — cost-advice-agent

| 面向 | 決策 | 理由 |
|---|---|---|
| 語言 | Python 3／FastAPI | brownfield |
| 模組 | `advice_orchestrator`／`cost_advice_agent`／`advice_stream_router` | FD Q1=A |
| Runtime | U6 `langgraph_runtime` | FR10.2 |
| Worker | `ThreadPoolExecutor(max_workers=2)` | Q4=A |
| SSE | Starlette/`StreamingResponse` text/event-stream | C3 |
| 查價 | 可選 `pricing_client.fetch_hourly` | Q5=A |
| 測試 | unittest＋mock | Q6=A |
| 不做 | Celery／Redis／Playwright／帳單 API | NFR8 |

<!-- confirmed: Looks correct -->
