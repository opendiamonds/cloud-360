# Shared Infrastructure — C1 Cost（跨 unit）

> Stage: infrastructure-design · Intent: `260819-cost-finops`  
> 可選產物；記錄五 unit 共用的 embedded 資源（非新雲端 stack）。

## 1. 共用 runtime

| 資源 | 消費者 |
|---|---|
| FastAPI backend 單 process | cost-api、cost-budget-banner（B2 路由） |
| Postgres 單實例 | cost-schema-rbac 表、pricing_cache、audit |
| frontend nginx SPA | cost-ui、cost-budget-banner（B2 register） |
| Cloudflare Tunnel → staging | 全站 |

## 2. 共用設定檔（repo 內）

| 檔案 | 擁有語意 | 消費者 |
|---|---|---|
| `pricing_coverage.yaml` | OQ-3／ADR-C1-09：三雲 `official_list` | cost-api → snapshot.coverage |
| `pricing_urls.yaml` | allowlist + 各雲 default_products | pricing_client |
| `sku_map.yaml` | SKU 對照 | sku_mapper |
| `supported_regions.yaml` | `by_cloud` + 扁平 regions | cost-api（`allowed_regions`）+ cost-ui |

## 3. 共用 CI 變數

| 變數 | 範圍 |
|---|---|
| `COST_PRICING_STUB=1` | test compose only |

## 4. 刻意不共用

- 雲端 **Billing Account**／Cost Explorer credential（全 intent 禁止）
- Redis / queue
- 第二 database
- 備註：可選 `GCP_BILLING_API_KEY` 僅供 Catalog 公開價查詢（ADR-C1-09），非帳號型 Billing SDK

## 5. DEPLOY.md 同步項（code-generation）

- 新表 ensure 行為
- staging 出站需能連 allowlist：AWS Price List、`cloudbilling.googleapis.com`、`prices.azure.com`（真實價；CI 仍 stub）
- 可選：`GCP_BILLING_API_KEY` 記載於 env example（不 commit secrets）
