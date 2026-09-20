# CI/CD Pipeline — cost-api

> Unit: `cost-api` · service

## 1. 既有 CI 擴充

| 步驟 | 本 unit 交付 |
|---|---|
| `repo-contract` | OpenAPI drift、`schema_rbac` 同步檢查 |
| `backend` unittest | `test_cost_api*.py` TestClient（allow/deny C1、404/403/422） |
| `dump_openapi.py --check` | 新 `/api/cost*` 路由 |
| `docker-build` | backend image 含 `backend/cost/` |

## 2. 測試 stack（`docker-compose.test.yml`）

```yaml
# 伪示意 — code-generation 內嵌
environment:
  COST_PRICING_STUB: "1"
```

- ui-regression / Playwright 依 stub 穩定 `cost-total`
- **不**在 CI 打真實 AWS Price List（flaky／出站）

## 3. OpenAPI → 前端型別

同 PR 流程：

1. 實作 router
2. `python backend/scripts/dump_openapi.py --check`
3. frontend `npm run gen:types`

## 4. 靜態安全 gate（建議同 PR）

| 檢查 | 目的 |
|---|---|
| `rg azure-identity\|CostExplorer\|ce\.get_cost backend/cost/` | 禁管理面／帳單 SDK |
| `rg google.cloud.billing\|google-cloud-billing backend/cost/` | 禁 GCP 帳號客戶端（Catalog 僅 httpx + key） |
| host allowlist 單元測試 | SSRF |
| （允許）`boto3` `pricing.get_products` | 僅 Pricing Query；與 Bulk 並存（ADR-C1-09） |

## 5. Deploy

- merge `ut` → `deploy.yml` 既有路徑
- **無** cost 專用 workflow
- B2：同 pipeline 多路由；無第二 deploy job

## 6. Code Gen 檢查清單

- [ ] TestClient C1 allow/deny（team.md Q3）
- [ ] CI 綠 + OpenAPI 同步
- [ ] test compose 設 `COST_PRICING_STUB=1`
