# Deployment Architecture — cost-budget-banner

> Unit: `cost-budget-banner` · B2 · embedded

## 1. 拓樸增量

```text
Layout (SPA)
  └─ OverspendBanner ──GET /api/cost/banner──► backend (同 cost-api 程序)

CostPage
  └─ CostBudgetField ──PUT .../budget──► backend
  └─ OverspendFlag ← snapshot.overspent
```

**無** 新容器、新 port、新 tunnel 路徑。

## 2. B1 vs B2 建置

| 項目 | B1 artifact | B2 artifact |
|---|---|---|
| `registerCostBudgetBanner()` | 不 import | `App.tsx` 或 Layout bootstrap import |
| PUT budget | router 404 | 註冊 |
| GET /banner | router 404 | 註冊 |
| DOM slot | 空 | 掛元件 |

Deploy **同一** `deploy/docker-compose.deploy.yml`；B2 = trunk 上多一 commit（Bolt 2 squash）。

## 3. 前端掛載點

- `data-slot="cost-banner"`：Layout 主區頂（mockups Q3）
- `data-slot="cost-overspend"`：CostPage 內

## 4. Code Gen 檢查清單

- [ ] B1 CI 仍 0 命中 budget/banner test-id
- [ ] B2 e2e 橫幅 active 場景
