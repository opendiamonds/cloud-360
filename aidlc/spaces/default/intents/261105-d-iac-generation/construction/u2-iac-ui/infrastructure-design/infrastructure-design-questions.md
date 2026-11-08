# Infrastructure Design 問答：U2 `u2-iac-ui`

> Stage: infrastructure-design · Unit: `u2-iac-ui`（ui）  
> 設計層：前端部署／監控／CI 要什麼；禁止完整 IaC／CDN 合約草稿。  
> **成本揭露**：本題組共 4 題。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 自有 staging＋Tunnel；`ut`→deploy.yml；三環境分離 | ADR-0007／env contract |
| Workspace 內頁；AbortController≥90s；無 RUM SDK；無 apply | [fd]／[nfr] |
| 既有 React／Vite／Tailwind／Playwright＋MSW | [nfr] |
| U1：Checkov 在 backend image；結構化 log；沿用 ci／deploy | U1 infra Q1–Q4=A |

## Sources

- [nfr] `../nfr-design/*`、`../nfr-requirements/*`
- [fd] `../functional-design/functional-spec.md`、`frontend-components.md`
- [dd] `../../../inception/domain-design/components.md`
- [cd] `../../../inception/contract-design/contract-summary.md`
- U1 `../../u1-iac-api/infrastructure-design/*`（共用 compose／nginx）

---

## Q1. 前端產物如何部署到 staging／CI？

A. **沿用既有 frontend Docker／Vite build → nginx 靜態服務**（compose 既有服務）；本 unit **不**另開 CDN／獨立靜態主機。**（建議）**
B. 本輪新增獨立靜態託管（S3／CloudFront 等，需另開範圍）。
C. 僅本機 `vite preview`；staging 不部署 UI（與 ADR-0007 衝突）。
X. Other (please specify)

[Answer]:Ａ

---

## Q2. 瀏覽器如何打到 `/api/iac`？

A. **沿用同源／nginx 反代＋既有 `VITE_API_BASE_URL` 環境契約**（dev／CI／deploy 分離；部署態由 compose／nginx 推導，不在範本硬寫 localhost）。**（建議）**
B. 前端直連後端容器 IP／port（繞過 nginx）。
C. 另開 CORS 專用 gateway。
X. Other (please specify)

[Answer]:Ａ

---

## Q3. UI 側監控與告警？

A. **不新增 RUM／前端 metrics SDK**（對齊 NFR）；可觀測性靠 UX 狀態＋`error.code` 與 **U1 後端結構化 log**；本 unit **不**新增 Grafana 面板義務。**（建議）**
B. 強制接入第三方 RUM（與 NFR Q5=A 衝突，需回改）。
X. Other (please specify)

[Answer]:Ａ

---

## Q4. CI／CD 對本 unit 的變更範圍？

A. **沿用 ci.yml／deploy.yml／ui-regression**；code-gen 把 Playwright／MSW 案例掛進既有 UI 回歸 job；**不**改 deploy-on-merge 拓撲、不加獨立 frontend-only workflow。**（建議）**
B. 新增獨立 workflow 只測 IaC Workspace。
C. 前端改動需人工 SSH 部署（違反既有 deploy.yml）。
X. Other (please specify)

[Answer]:Ａ

---

## Consolidated Summary Confirmation

1. **Q1=A** — 沿用既有 frontend Docker／Vite → nginx 靜態服務；不另開 CDN。
2. **Q2=A** — 同源／nginx 反代＋`VITE_API_BASE_URL` 環境契約。
3. **Q3=A** — 不新增 RUM；UX＋`error.code`＋U1 結構化 log。
4. **Q4=A** — 沿用 ci／deploy／ui-regression；測案進既有 UI job。

**將產出**：infrastructure-specification／monitoring-design／cicd-pipeline／traceability。

Does this all look correct before I generate the artifacts?

- Looks correct
- Request changes

[Answer]: Looks correct
