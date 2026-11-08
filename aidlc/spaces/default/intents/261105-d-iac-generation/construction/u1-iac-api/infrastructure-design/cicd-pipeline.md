# CI/CD Pipeline — u1-iac-api

> Q4=A · 沿用既有 GitHub Actions；不加 CI Checkov job。

## Pipeline 對照

| Stage | Gate | 本 unit 增量 |
|---|---|---|
| repo-contract | 紅燈擋 | 無 path `secrets`／credential；env contract |
| lint／build | 紅燈擋 | `backend/iac/` 納入既有 Python／映像 build |
| test | 紅燈擋 | 新增 unittest＋Hypothesis（三核心）；TestClient 403／2xx |
| Docker build | 紅燈擋 | **映像安裝釘版 Checkov**（Q1） |
| deploy.yml（`ut`） | 部署 staging | `render-env.sh`；無新 secret 後端；rollback 既有 |

## 明確不做

- CI 內 Checkov／tfsec 掃 repo 或產出 HCL（requirements 約束）。
- 獨立 `/api/iac` workflow。
- 藍綠／金絲雀新拓撲（維持現有 rolling／compose 重啟）。

## Secrets in CI／CD

- 沿用既有 Actions secrets／deploy env；**禁止**把 LLM key 烘焙進 image layer。
- 本機：`.env.example` 記載變數名；`LOCAL-DEV.md` 若涉 Checkov／LLM 前置則同步更新。

## Rollback

- 沿用 `deploy.yml` rollback job＋`render-env.sh`；session 清空為預期（NFR）。

<!-- confirmed: Looks correct -->
