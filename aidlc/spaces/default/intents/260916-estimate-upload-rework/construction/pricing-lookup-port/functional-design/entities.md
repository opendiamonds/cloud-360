# 實體模型：U5 `pricing-lookup-port`

本 Unit 為 **library**：唯讀目錄價查詢 Port（文件稱 **PricingLookup**；公開入口保留既有 `fetch_hourly`，Q1=A）。  
**不擁有**業務資料庫表（`pricing_cache` 已隨 U3 archive）。建議寫入／Advice 屬 U7；上傳明細屬 U2。

## Source of truth

```yaml
entities:
  - name: PriceLookupQuery
    description: 單筆目錄價查詢請求
    attributes:
      - { name: cloud, type: enum, required: true, allowed_values: [aws, azure, gcp] }
      - { name: sku, type: string, required: true, description: "產品／服務家族識別（既有 coverage 映射鍵）" }
      - { name: region, type: string, required: true }
    constraints:
      - "不得含帳單帳戶、用量時段、Cost Explorer 查詢參數（FR5.7）"

  - name: PriceHit
    description: 成功取得目錄價
    attributes:
      - { name: kind, type: enum, required: true, allowed_values: [hit] }
      - { name: hourly, type: decimal, required: true, description: "每小時目錄價" }
      - { name: fetchedAt, type: datetime, required: true }
      - { name: source, type: string, required: true, description: "來源標籤（如 sdk／bulk／azure-retail／gcp-catalog）；不得含憑證" }
    constraints:
      - "hourly 僅供建議文字引用；不得進入 EstimateLineItem 寫入路徑（AH-6／FR5.5）"

  - name: PriceMiss
    description: 可嘗試但未取得價（含降級後仍無結果）
    attributes:
      - { name: kind, type: enum, required: true, allowed_values: [miss] }

  - name: PriceUnsupported
    description: 該 cloud／sku／region 不在覆蓋範圍
    attributes:
      - { name: kind, type: enum, required: true, allowed_values: [unsupported] }

  - name: OfferDiskCache
    description: 公開 Bulk／下載路徑的 24h 磁碟快取（Q2=A）
    attributes:
      - { name: directory, type: string, required: true, const: "backend/cost/.pricing_offer_cache/" }
      - { name: ttlHours, type: integer, required: true, const: 24 }
    constraints:
      - "不重建 Postgres pricing_cache；快取目錄須 gitignore"
      - "快取內容為公開目錄價片段，不得寫入 secret"

  - name: AwsSdkSettings
    description: AWS Price List Query（boto3）開關與降級（Q3=A）
    attributes:
      - { name: useSdkEnv, type: string, required: true, const: "COST_PRICING_USE_SDK" }
      - { name: defaultEnabled, type: boolean, required: true, description: "預設可啟用（FR9.4）；顯式 0/false 可關" }
      - { name: requiredIamActions, type: list, required: true, example: "[pricing:GetProducts]" }
    constraints:
      - "缺 IAM 或 SDK 失敗必須降級 Bulk，不得 raise 使呼叫端建議流程失敗（FR5.10）"

  - name: CatalogEndpointPolicy
    description: 允許的目錄價端點與禁止的帳單類 API（Q6=A）
    attributes:
      - { name: allowedAws, type: list, required: true, description: "Price List Query＋公開 Bulk" }
      - { name: allowedGcp, type: list, required: true, description: "Cloud Billing Catalog" }
      - { name: allowedAzure, type: list, required: true, description: "Retail Prices" }
      - { name: forbiddenApis, type: list, required: true, description: "Cost Explorer／Cost Management／Billing Export 等" }
    constraints:
      - "httpx／SDK 不得新增 forbiddenApis 客戶端；allowlist 由規則＋測試守住"

  - name: PricingLookupPort
    description: 本 Unit 對外契約的邏輯代稱（實作入口＝fetch_hourly）
    attributes:
      - { name: entrypoint, type: string, required: true, const: "cost.pricing_client.fetch_hourly" }
      - { name: resultUnion, type: enum, required: true, allowed_values: [PriceHit, PriceMiss, PriceUnsupported] }
      - { name: survivingModules, type: list, required: true, description: "pricing_sdk／query_parser／units／gcp／azure／offer_parser／config＋YAML（FR9.4／9.5）" }
    constraints:
      - "estimate_intake_* 與明細 ORM 寫入路徑不得 import 本 Port（Q5=A）；得延遲 import sku_catalog（BR5.11）"
      - "僅 CostAdviceAgent／U7 與測試為 fetch_hourly 的預期消費者"
```

## 摘要

| 實體 | 角色 |
|---|---|
| PriceLookupQuery | 查詢輸入 |
| PriceHit／Miss／Unsupported | 查詢結果聯合 |
| OfferDiskCache | 24h 磁碟快取 |
| AwsSdkSettings | SDK 開關與降級 |
| CatalogEndpointPolicy | 允許／禁止端點 |
| PricingLookupPort | 對外 Port 契約 |

無業務生命週期狀態機（單次查詢、結果交還呼叫端）。

<!-- post-confirmation save -->
