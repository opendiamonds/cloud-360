# CI/CD Pipeline — cost-ui

> Unit: `cost-ui` · ui

## 1. CI 步驟

| Job | 本 unit |
|---|---|
| `frontend` lint | `eslint` on `src/cost/**` |
| `tsc -b` | Cost 元件型別 |
| `npm run build` | 含 lazy `/cost` chunk |
| OpenAPI drift | 間接：`gen:types` 後 tsc |
| `ui-regression` | **新增** Playwright cost cases（team.md C） |

## 2. Playwright（NFR-4 + AC）

| Case | 斷言 |
|---|---|
| C1 可達 | Sidebar「成本」、路由 `/cost` |
| 核心欄位 | `cost-total` 或 M5b 0 命中規則 |
| B1 否定 | `cost-budget`、`cost-banner` **0 命中** |

執行環境：`docker-compose.test.yml` + `COST_PRICING_STUB=1`。

## 3. 無新增

- Vitest / Jest
- 獨立 frontend workflow
- Percy 視覺回歸

## 4. B2 增量

- 同一 `ui-regression` job 加 banner／budget cases
- `registerCostBudgetBanner` 在 B2 merge 後才 import

## 5. Code Gen 檢查清單

- [ ] e2e 至少一 case 可達 cost 頁
- [ ] test-id 與 mockups 表一致
