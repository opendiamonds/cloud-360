# Deployment Architecture — cost-ui

> Unit: `cost-ui` · ui · embedded SPA

## 1. 交付形態

```text
frontend container (nginx)
  └── /usr/share/nginx/html/
        ├── index.html
        ├── assets/index-*.js
        └── assets/CostPage-*.js    ← lazy chunk /cost
```

- **無** 獨立 CDN bucket 或第二 frontend service
- API 同源：`VITE_API_BASE_URL` = `PUBLIC_URL`（deploy compose 推導）

## 2. 路由

| 路徑 | 元件 | 授權 |
|---|---|---|
| `/cost` | `CostPage` | `CapabilityRoute` C1.view |
| `/403` | 既有 | 無 C1 |

`App.tsx` 註冊 lazy import；與 `openapi.json` 無直接 deploy 依賴。

## 3. 靜態資產同步

| 資產 | 同步 |
|---|---|
| `frontend/src/cost/supportedRegions.ts` | ↔ `backend/cost/supported_regions.yaml`（同 PR） |
| SVG pie | 無外部 font/chart CDN |

## 4. B1 DOM 契約

- `data-slot="cost-banner"`、`cost-overspend` 空節點常駐
- B1 build **不** import `registerCostBudgetBanner`

## 5. 環境

| 環境 | 備註 |
|---|---|
| dev | `vite` HMR；proxy 至 local backend |
| staging | nginx 靜態 + tunnel |
| CI test | Playwright 對短生命週期 stack |

## 6. Code Gen 檢查清單

- [ ] build 通過 `tsc -b`
- [ ] lazy route 不拖垮首屏 bundle 過大（chunk 分離即可）
