# Infrastructure Specification — u2-iac-ui

> Q1–Q4=A · 沿用 ADR-0007 staging；Workspace 內頁；無新 CDN／RUM／獨立 workflow。

## Sources

- `performance-design`／`security-design`／`logical-components`（本 unit `nfr-design/`）
- UI 不產 `scalability-design`／`reliability-design`／`observability-design`（N/A；義務薄適用，見 NFR Requirements）
- `components`（`inception/domain-design/`）
- `functional-spec`（本 unit `functional-design/`）
- `contract-summary`（`inception/contract-design/`）

## Deployment

| Facet | Choice | Rationale |
|---|---|---|
| Compute | 既有 **frontend Docker**（Vite build → nginx 靜態） | Q1=A；與現況一致 |
| Networking | Cloudflare Tunnel → staging → nginx；同源服務 SPA | ADR-0007；Q2=A |
| Storage | **無**本 unit 伺服器端狀態；blob URL 僅瀏覽器暫存 | NFR／FD |
| Environments | 本機 Vite／CI test compose／staging deploy 三分離 | env contract |
| IaC approach | **不**用雲端 IaC 部署本 UI；產品 HCL 不 apply | 範圍邊界 |
| Sizing | 靜態資產；無 UI 側 auto-scale | NFR 無 RUM／無 metrics |
| API reachability | nginx 反代／`VITE_API_BASE_URL` 契約 | Q2=A |

## Infrastructure Services

| Service | Role | Configuration | Notes |
|---|---|---|---|
| nginx（frontend 映像） | 靜態＋／或反代 `/api` | 既有 `deploy/nginx.conf` | 本 unit 僅加 SPA 路由／頁面資產 |
| Vite build | 打包 | CI／映像 build stage | 不新增 CDN |
| MSW（dev／CI 可選） | stub `/api/iac` | Playwright／平行開發 | 合併後改真 API |
| RUM／CDN／獨立 LB | — | **不部署** | Q1／Q3=A |

## Shared Infrastructure

| Shared Resource | Owner Unit | Consumer Units | Access Boundary |
|---|---|---|---|
| staging compose／nginx／Tunnel | 平台（既有） | u1-iac-api、u2-iac-ui | 同源 HTTP；UI → `/api/iac` |
| JWT cookie／既有 auth UX | 既有 auth | u2 | 無權入口 disabled＋說明 |
| U1 後端結構化 log | u1-iac-api | 運維（間接） | UI 不寫伺服器 log |

<!-- confirmed: Looks correct -->
