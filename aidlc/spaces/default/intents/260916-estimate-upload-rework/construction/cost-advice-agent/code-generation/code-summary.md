# Code Summary — cost-advice-agent（U7）

> Plan Approval：`Approve Plan`（fingerprint `sha256:9d31c66ffd8ec60dc3e570a1ae296bdd685607ead094cb8e6712374ca1590593`）

## 變更檔案

| 檔案 | 變更 |
|---|---|
| `advice_orchestrator.py` | ThreadPool(2)、enqueue、逾時清理、進度 |
| `cost_advice_agent.py` | U6 invoke＋可選 U5；fallback 文案；≤3 invoke |
| `advice_stream_router.py` | SSE `/sets/{id}/advice/stream` |
| `estimate_intake_service.enqueue_advice_job` | 委派 U7 |
| `main.py` | 掛載 SSE router |
| `test_cost_advice_agent.py` | 5 案 |
| `openapi.json`／`api.d.ts` | 含 stream |

## 測試

`python3.13 -m unittest tests.test_cost_advice_agent tests.test_estimate_intake_api -v` → 16 OK

## 偏離

- LLM 失敗時用 deterministic fallback 仍產出 Must `saving_text`（利於無金鑰環境／測試），並在 `unavailable_reasons.llm` 標明。
