# Logical Components — cost-budget-banner

> Unit: `cost-budget-banner` · B2 · Q1=A lightweight helper

## 1. 邏輯元件圖

```text
Layout
  └─ OverspendBanner ──GET──► cost_router GET /banner
                                    │
                                    v
                              CostService.banner_for()
                                    │
                                    +─ visible_diagrams()
                                    +─ lightweight_total()  per diagram
                                    +─ cost_calculator.is_overspent()

CostPage
  └─ div[data-slot=cost-overspend]
       └─ OverspendFlag (B2)     ← reads page snapshot.overspent

CostPage (budget field)
  └─ CostBudgetField ──PUT──► apply_budget()

registerCostBudgetBanner()  (B2 merge only)
  └─ mountCostSlot('cost-banner', OverspendBanner)
  └─ mountCostSlot('cost-overspend', OverspendFlag)
```

## 2. 元件職責

| 元件 | 層 | 職責 |
|---|---|---|
| `banner_for` | backend | 聚合超支圖 |
| `apply_budget` | backend | UPSERT + audit |
| `lightweight_total` | backend | 僅 total；無 pie/lines DTO |
| `OverspendBanner` | frontend | Layout 橫幅、CTA、session dismiss |
| `OverspendFlag` | frontend | 頁內超支標記 |
| `CostBudgetField` | frontend | C1b.edit PUT |
| `registerCostBudgetBanner` | frontend | B2 掛 slot |

## 3. B1 / B2 邊界

| 項目 | B1 | B2 |
|---|---|---|
| `registerCostBudgetBanner` import | ❌ | ✓ in App/Layout bootstrap |
| PUT budget route | 404 | ✓ |
| GET /banner | 404 | ✓ |
| test-id hits | 0 | >0 when active |

## 4. 無新增基礎設施

- 無 WebSocket push
- 無 banner Redis

## 5. Code Gen 檢查清單

- [ ] B2 Bolt 才 merge `register.tsx`
- [ ] CTA `navigate(/cost?diagram=...)`
- [ ] 無「永遠關閉」按鈕
