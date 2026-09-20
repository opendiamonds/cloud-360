# Code Generation Plan — cost-ui

> Unit: `cost-ui` · Bolt B1 · 上游：frontend-components、interaction-spec、mockups test-id。

## 落點

| 元件 | 檔案 | 性質 |
|---|---|---|
| 成本頁 | `frontend/src/pages/CostPage.tsx` | **新檔** |
| 區域常數 | `frontend/src/cost/supportedRegions.ts` | 與 backend YAML 同步 |
| B2 slot | `frontend/src/cost/slotRegistry.tsx` | B1 空實作 |
| 路由 | `frontend/src/App.tsx` | `/cost` + `CapabilityRoute C1.view` |
| 導覽 | `frontend/src/components/Sidebar.tsx` | 成本群組 |
| Layout 掛點 | `frontend/src/components/Layout.tsx` | `data-slot="cost-banner"` 空 |
| e2e | `frontend/tests/e2e/regression.spec.ts` | **5** 個 B1 case |

## 實作順序

1. `supportedRegions.ts` + CostPage 狀態機
2. App 路由 + Sidebar + Layout slot
3. Playwright B1 斷言（含 0 命中 budget/banner）

## 測試計畫

Playwright（唯一前端自動化層）：Sidebar、cost-total、時數更新、pie、coverage 文案；`cost-budget`／`cost-banner`／`cost-overspend-flag` **0 命中**。
