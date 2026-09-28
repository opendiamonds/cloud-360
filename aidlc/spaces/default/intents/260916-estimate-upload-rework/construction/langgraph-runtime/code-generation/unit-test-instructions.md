# Unit Test Instructions — langgraph-runtime

> Unit: `langgraph-runtime` · Standard · test-after  
> 測試對象：`backend/services/langgraph_runtime.py`（OpenRouter 客戶＋圖執行輔助；無 HTTP 路由／DB）。

## Framework

- Python 內建 `unittest` + `unittest.mock`
- **不**引入 pytest；CI 無金鑰時不得打真 OpenRouter
- CI：`cd backend && python -m unittest discover -s tests -v`

## Exact unit-scoped command（須在第一個實作測試前可跑）

```bash
cd backend && PYTHONPATH=. python3 -m unittest tests.test_langgraph_runtime -v
```

## Cases（目標 5–8）

| # | 情境 | 期望 |
|---|---|---|
| 1 | 缺 `OPENROUTER_API_KEY` | 拋 `RuntimeAuthError`；訊息含 `OPENROUTER_API_KEY`、不含金鑰值 |
| 2 | mock 客戶端成功 `invoke_graph` | 回傳 `InvokeOutcome`，`state` 為終態 |
| 3 | mock `stream_graph` | 產出 ≥1 `StreamEvent`；事件無金鑰 |
| 4 | mock `astream_graph` | async 可迭代；形狀同 stream |
| 5 | 例外／回傳字串金鑰紅線 | 人為注入假金鑰後，公開錯誤／事件字串不得含該值 |
| 6 | 預設逾時可觀測 | 建構參數 timeout=60（或等價）可被測試讀取／斷言 |

## Coverage / mocking

- 以 mock／假客戶端覆蓋；不在 CI 使用真實 `OPENROUTER_API_KEY`
- smoke 腳本本機選跑，失敗不擋 unittest

## Out of scope

- U7 建議圖節點測試
- TestClient／Playwright
- TCMS 手寫
