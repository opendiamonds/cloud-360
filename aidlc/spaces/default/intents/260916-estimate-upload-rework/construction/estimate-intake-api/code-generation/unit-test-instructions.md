# Unit Test Instructions — estimate-intake-api

> Unit: `estimate-intake-api` · Standard · test-after  
> 測試對象：`/api/cost/v1` router＋service＋access；ORM／seed。

## Framework

- Python `unittest`＋`starlette.testclient.TestClient`＋`unittest.mock`
- **不**引入 pytest；**不**手寫 TCMS；**不** Playwright（U8）

## Exact unit-scoped command

```bash
cd backend && PYTHONPATH=. python3 -m unittest tests.test_estimate_intake_api -v
```

全套回歸：

```bash
cd backend && PYTHONPATH=. python3 -m unittest discover -s tests -v
python3 scripts/validate_repo_contract.py
python3 scripts/validate_env_contract.py
```

## Cases（目標 5–8）

| # | 情境 | 期望 |
|---|---|---|
| 1 | 有 C1 的使用者 POST 合法 CSV／XLSX（mock parse） | 201；Detail 含 estimates／checks |
| 2 | 無 C1 使用者 POST | 403 |
| 3 | 單檔 >5MB 或副檔名錯 | 413／400；固定 detail；不寫庫 |
| 4 | ambiguous 無 override | 400 |
| 5 | 非 owner／非分享 GET | 404 |
| 6 | owner DELETE | 204；再 GET 404 |
| 7 | enqueue 拋錯（mock） | 仍 201；Advice failed 或等價＋audit |
| 8 | seed：C1h 等 story 不存在；C1 allow／deny | 矩陣斷言 |

## Out of scope

- U8 e2e、U7 建議正文、真 OpenRouter、TCMS 手寫
