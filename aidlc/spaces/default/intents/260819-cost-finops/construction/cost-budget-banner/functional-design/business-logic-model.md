# Business Logic Model — cost-budget-banner

> Unit: `cost-budget-banner` · B2 · Q1–Q3=A

## 後端

### `apply_budget(user, diagram_id, budget)`

404 可見性 → 403 `C1b.edit` → 驗證：`budget is null` 允許（清除預算）；否則非負 Decimal 量化兩位 → UPSERT `diagram_cost.monthly_budget` → `record_audit(field=monthly_budget)` → 回 `{budget}`。

### `banner_for(user)`

```
overspent = []
for d in visible_diagrams(user):
  if budget is None: continue
  snap = lightweight total (reuse get_snapshot totals only)
  if is_overspent(total, budget): overspent.append(d)
if empty: return {active: false, count: 0}
else: return {active: true, count: len(overspent), sample: first entry metadata}
```

`GET /banner` 註冊於 B2 router include。

## 前端

### Register（B2 merge）

```tsx
// budget-banner/register.tsx
import { mountCostSlot } from "../cost/slotRegistry";

export function registerCostBudgetBanner() {
  mountCostSlot("cost-overspend", <OverspendFlag />);
  mountCostSlot("cost-banner", <OverspendBanner />);
}
```

B1：`registerCostBudgetBanner` **不被 import**。

### OverspendFlag

讀當前 CostPage snapshot：`overspent===true` → 渲染「已超支」+ 危險色 + test-id `cost-overspend-flag`。

### OverspendBanner

Layout mount：**僅當** `can('C1','view')` 時 GET `/api/cost/banner`；`active` → 顯示橫幅；CTA `navigate(/cost?diagram=sample.id)`；**無**「永遠關閉」；session dismiss 僅隱藏至 reload。

### CostBudgetField

`can('C1b','edit')`；test-id `cost-budget`；blur/Enter → PUT budget。

## 不在 B1

上述路由與 register 皆 B2 Bolt 才 merge。
