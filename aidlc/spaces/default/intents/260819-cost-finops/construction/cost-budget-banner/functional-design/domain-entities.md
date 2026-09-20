# Domain Entities — cost-budget-banner

## API

| 端點 | Body |
|---|---|
| PUT `/diagrams/{id}/budget` | `{ budget: number \| null }` |
| GET `/banner` | `{ active, count, sample?: { id, title, total, budget } }` |

Snapshot 擴充（B2）：`budget` 非 null；`overspent` 來自 `is_overspent`。

## UI 元件

| 元件 | test-id | 掛點 |
|---|---|---|
| `CostBudgetField` | `cost-budget` | CostPage |
| `OverspendFlag` | `cost-overspend-flag` | `data-slot=cost-overspend` |
| `OverspendBanner` | `cost-banner` | `data-slot=cost-banner`；經 `mountCostSlot("cost-banner", …)` 注入 |

## Session state

`bannerDismissed: boolean`（React state only；重登重置）。
