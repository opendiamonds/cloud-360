# Tech Stack Decisions — cost-budget-banner

> Unit: `cost-budget-banner` · B2 register 模式

| 面向 | 決策 |
|---|---|
| 後端 | 同 `cost-api` router 加 budget/banner routes（B2 merge） |
| 前端 | 獨立模組 `frontend/src/cost/budget-banner/` |
| 掛載 | `registerCostBudgetBanner()` → `mountCostSlot`（cost-ui） |
| B1 | **不 import** register |

**新依賴**：無。
