# Logical Components — cost-ui

> Unit: `cost-ui` · ui · Q1=A local state

## 1. 邏輯元件圖

```text
App.tsx
  └─ Route /cost → CostPage (lazy)
Sidebar
  └─ CostNavGroup
CostPage
  ├─ DiagramSelect
  ├─ RegionField
  ├─ TotalSection (cost-total, cost-unpriced-count)
  ├─ PieBreakdown (SVG)
  ├─ ResourceTable → HoursInput × N
  ├─ PricingAssumptions
  └─ div[data-slot=cost-overspend]   ← B2 mount point
Layout
  └─ div[data-slot=cost-banner]      ← B2 mount point
slotRegistry.ts
  └─ mountCostSlot(name, node)       ← B2 registerCostBudgetBanner
SuccessCostCta (Workspace)
supportedRegions.ts                  ← 建置期常數
```

## 2. 元件職責

| 元件 | 職責 | 非職責 |
|---|---|---|
| `CostNavGroup` | RBAC 導航入口 | 資料 fetch |
| `CostPage` | snapshot 生命週期、diagram 選擇 | 定價 HTTP |
| `HoursInput` | 客戶端 hours 驗證、PUT | 算術 |
| `RegionField` | region PUT、未填提示 | 價目 |
| `TotalSection` | M5b、`aria-live` | banner |
| `PieBreakdown` | SVG 四類 | 後端 pie 算法 |
| `slotRegistry` | B2 掛點 registry | B1 不 import banner |

## 3. 資料流

```
CostPage mount
  → GET /api/cost/diagrams (list)
  → GET /api/cost/diagrams/{id} (snapshot)
  → setState(snapshot)

HoursInput commit
  → PUT .../lines/{mxcell_id}/hours
  → merge response snapshot fields
```

## 4. API 邊界

- 僅同源 `/api/cost*`
- 型別：`api.d.ts` 生成 + 本地 props

## 5. 無新增基礎設施

| 類型 | 本期 |
|---|---|
| Chart 函式庫 | ❌ |
| Frontend unit test runner | ❌（team.md D 不採） |
| Service Worker cache | ❌ |

## 6. Code Gen 檢查清單

- [ ] `/cost` 路由與 TCMS 受測介面一致
- [ ] `supportedRegions.ts` ↔ backend yaml 同步
- [ ] e2e 斷言 `cost-total`（team.md C）
