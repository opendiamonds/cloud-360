# Frontend Components — cost-budget-banner

> B2 only · 注入 `cost-ui` 預留 slot

## OverspendBanner

| Field | Value |
|---|---|
| Data | GET `/api/cost/banner` on Layout mount |
| CTA | 連到 `/cost?diagram={sample.id}` |
| Dismiss | 可選「本次工作階段關閉」；無永久 |

## CostBudgetField

Currency USD；`tabular-nums`；空值表示未設預算。

## OverspendFlag

條件：`snapshot.overspent === true`；文字「已超支」必須可見（不只顏色）。

## Register 契約

B2 `main.tsx` / `App.tsx` 呼叫 `registerCostBudgetBanner()` 一次。
