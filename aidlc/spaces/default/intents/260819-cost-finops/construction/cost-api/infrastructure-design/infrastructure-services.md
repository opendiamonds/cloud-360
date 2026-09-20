# Infrastructure Services — cost-api

> Unit: `cost-api` · service · **OQ-3 主落點**（後續以 ADR-C1-09 擴為三雲官方價）

## 1. 覆蓋清單

檔案：`backend/cost/pricing_coverage.yaml`（啟動載入，隻讀）

```yaml
# C1 — 三雲皆走官方 list price（見 ADR-C1-09）
coverage:
  - cloud: aws
    mode: official_list
  - cloud: gcp
    mode: official_list
  - cloud: azure
    mode: official_list
```

| `mode` | `pricing_client` 行為 | 列 status |
|---|---|---|
| `official_list` | 允許對 allowlist host HTTP／SDK（見 §2） | priced / price_fetch_failed |
| `manual_override_only` | **`PriceUnsupported`**，零 HTTP | unpriced（除非 override）；本輪三雲皆不用此 mode |

## 2. 公開／官方價端點（allowlist）

檔案：`backend/cost/pricing_urls.yaml`（**禁止** runtime 任意 URL）

```yaml
allowlist_hosts:
  - pricing.us-east-1.amazonaws.com
  - cloudbilling.googleapis.com
  - prices.azure.com
```

| 雲 | HTTP／查價路徑 | 備註 |
|---|---|---|
| **AWS** | Price List Bulk JSON；可選 boto3 `pricing.get_products`（IAM `pricing:GetProducts`） | 禁止 Cost Explorer／帳單 API |
| **GCP** | Cloud Billing Catalog `…/services/{id}/skus` | 需 `GCP_BILLING_API_KEY`（僅 Catalog；非 Billing Account） |
| **Azure** | Retail Prices API `prices.azure.com/api/retail/prices` | **公開免帳號**；OData `$filter` |

**安全**：
- host ∈ `allowlist_hosts`；禁止 caller 傳入任意 base URL（SSRF）
- **禁止** AWS SigV4 打 Cost Explorer；**禁止** Azure／GCP 管理面 SDK（`azure-identity`、`google-cloud-billing` 帳號客戶端）
- 允許例外：GCP Catalog 的 `key=` query（環境變數 `GCP_BILLING_API_KEY`）；AWS Pricing Query 使用既有 IAM（與 Bulk 公開路徑並存）

## 3. 配套靜態檔

| 檔案 | 用途 |
|---|---|
| `backend/cost/sku_map.yaml` | label/style → cloud／SKU／category |
| `backend/cost/pricing_urls.yaml` | allowlist、`default_products`／`default_products_gcp`／`default_products_azure` 代表規格 |
| `backend/cost/supported_regions.yaml` | `by_cloud` + 扁平 `regions`（↔ frontend `supportedRegions.ts`） |
| `backend/cost/aws_region_locations.yaml` | AWS Pricing location／usagetype 前綴 |

區域含亞洲與 Taipei（例：`ap-east-2`、`asia-east1`、`japaneast`）；清單變更須 YAML 與 TS 同 PR。

## 4. Postgres 服務（既有實例）

| 表 | 用途 |
|---|---|
| `diagram_cost` | region、budget |
| `diagram_cost_line` | hours、overrides |
| `pricing_cache` | UK(cloud, sku, region)；TTL 24h |
| `cost_audit_event` | audit append-only |

## 5. Stub（B1／CI）

| 變數 | 範圍 | 行為 |
|---|---|---|
| `COST_PRICING_STUB=1` | CI、`docker-compose.test.yml`、本機可選 | 回固定 `PriceHit`；**不**出網 |
| （未設） | 本機／staging | 依雲打真實官方價（GCP 需 key；AWS 可 SDK 或 Bulk；Azure 公開） |

## 6. SSRF 防護

- URL 只來自 `pricing_urls.yaml`（及 AWS Bulk 路徑模板）
- 單元測試：非法 host → 拒絕

## 7. Code Gen／回歸檢查清單

- [ ] 三雲 `official_list` 與 allowlist 進 repo
- [ ] `backend/.env.example`／`deploy/.env.example` 記載可選 `GCP_BILLING_API_KEY`（**不**放 secrets）
- [ ] `validate_env_contract` 仍通過
- [ ] warm 腳本可預熱 AWS／GCP／Azure cache
