# Tech Stack Decisions — cost-ui

> Unit: `cost-ui`

| 面向 | 決策 |
|---|---|
| 框架 | React + Vite（既有） |
| 型別 | generated `frontend/src/types/api.d.ts` |
| 路由 | React Router；`/cost?diagram=` |
| 樣式 | Tailwind（既有）；`tabular-nums` |
| a11y | 原生控件 + `aria-live` on total |
| B2 擴充 | `mountCostSlot` from `slotRegistry.tsx` |

**新 npm 依賴**：無（不引入 chart.js 等）。
