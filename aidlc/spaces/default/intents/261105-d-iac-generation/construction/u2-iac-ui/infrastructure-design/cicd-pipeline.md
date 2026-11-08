# CI/CD Pipeline — u2-iac-ui

> Q4=A · 沿用既有 GitHub Actions／ui-regression；不加獨立 frontend-only workflow。  
> 對齊 `functional-spec` 步驟與 `logical-components` test-id；契約形狀見 `contract-summary`。

## Pipeline 對照

| Stage | Gate | 本 unit 增量 |
|---|---|---|
| repo-contract | 紅燈擋 | 無 forbidden path／credential；env contract |
| frontend lint／`tsc -b`／build | 紅燈擋 | IaC Workspace 頁／元件納入既有 frontend job |
| ui-regression（Playwright） | 紅燈擋（`unexpected≠0`） | 新增 IaC 頁 e2e（test-id、步驟、下載確認、403 說明）；允許 MSW／stub 至 U1 合入 |
| Docker build | 紅燈擋 | 既有 frontend 映像含新靜態資產 |
| deploy.yml（`ut`） | 部署 staging | 無新拓撲；`render-env.sh`；rollback 既有 |

## 明確不做

- 獨立「只測 IaC Workspace」workflow。
- 人工 SSH 部署前端。
- 新增 RUM／前端 metrics 收集 pipeline 步驟。
- CI Checkov／掃產出 HCL（屬 U1／requirements 約束）。

## Secrets in CI／CD

- 前端映像**不**承載 LLM／雲端金鑰；僅建置期 `VITE_*` 依環境契約。
- 部署態 API base 由 compose／nginx 推導，範本不硬寫 localhost。

## Rollback

- 沿用 `deploy.yml` rollback；靜態資產隨映像回滾；瀏覽器 blob URL 自然失效。

<!-- confirmed: Looks correct -->
