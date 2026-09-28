# Code Generation Plan — cost-calculator

> Unit: `cost-calculator` · 純函式庫 · 上游：`component-methods.md`、NFR-3、BR-C-1。

## 落點

| 元件 | 檔案 | 性質 |
|---|---|---|
| 計算核心 | `backend/cost/cost_calculator.py` | 五函式 + 最大餘數法 pie |
| PBT | `backend/tests/test_cost_calculator.py` | Hypothesis |
| CI 邊界 | `scripts/validate_cost_calculator_boundary.py` | 禁 httpx/sqlalchemy/fastapi import |

## 實作順序

1. `cost_calculator.py` 五函式
2. Hypothesis 測試
3. import boundary 腳本 + `ci.yml` repo-contract job

## 測試計畫

- `python -m unittest tests.test_cost_calculator`
- `python3 scripts/validate_cost_calculator_boundary.py`
