# Code Generation Plan — cost-budget-banner

> Unit: `cost-budget-banner` · **Bolt B2（本 stage 略過實作）** · 上游：functional-design、ADR-C1-08。

## B1 範圍

本 unit 屬 B2 增量。code-generation（B1）**不交付**程式碼，僅保留 B2 掛點契約：

| 掛點 | B1 狀態 |
|---|---|
| `PUT .../budget` | 路由未註冊 → 404 |
| `GET /api/cost/banner` | 未註冊 → 404 |
| `data-slot="cost-banner"` | Layout 空 div |
| `data-slot="cost-overspend"` | CostPage 空 div |
| `cost-budget`／`cost-banner` test-id | **0 命中**（e2e 已斷言） |

## B2 待實作（approve B1 後）

1. budget 路由 + CostPage 預算欄
2. OverspendBanner + slotRegistry 註冊
3. Playwright 超支場景
