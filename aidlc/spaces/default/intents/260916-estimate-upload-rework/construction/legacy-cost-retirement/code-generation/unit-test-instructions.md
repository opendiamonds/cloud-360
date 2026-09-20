# Unit Test Instructions — legacy-cost-retirement

> Unit: `legacy-cost-retirement` · Standard · test-after  
> 測試焦點：退場後契約綠、舊 API 不可達、存活集仍可 import、應用不碰 archive_*。

## Framework

- Python 內建 `unittest` + `unittest.mock`；既有 Playwright e2e（刪舊 cost 段）
- **不**引入 pytest；**不**手寫 TCMS

## Exact unit-scoped commands

```bash
# 退場後後端套件仍可發現測試（刪除 test_cost_api* 後）
cd backend && PYTHONPATH=. python3 -m unittest discover -s tests -v

# 契約
python3 scripts/validate_repo_contract.py
python3 scripts/validate_env_contract.py
python3 scripts/validate_cost_calculator_boundary.py
```

## Cases（目標 5–8；以「刪改後仍綠」為主）

| # | 情境 | 期望 |
|---|---|---|
| 1 | 舊 `/api/cost/diagrams` | TestClient 或不存在路由 → 404（或 router 未掛載） |
| 2 | U5 存活模組 | `import cost.pricing_sdk`／`pricing_client` 成功 |
| 3 | 應用原始碼 | 不得出現對 `archive_diagram_cost` 等的 ORM／查詢映射（允許 schema／DEPLOY 字串） |
| 4 | `requirements.txt` | 無裸 `playwright` 套件行 |
| 5 | 邊界腳本 | `validate_cost_calculator_boundary.py` 仍指向 estimate_parser 路徑、exit 0 |
| 6 | env contract | 舊 stub 變數移除後仍 exit 0 |
| 7 | e2e | 不再斷言 `$86.40`／舊 diagrams cost 段（刪或 skip） |

## Out of scope

- U8 新頁 e2e（U8 補）
- archive 表內容正確性查核（維運）
- TCMS 手寫
- 自動 DROP archive
