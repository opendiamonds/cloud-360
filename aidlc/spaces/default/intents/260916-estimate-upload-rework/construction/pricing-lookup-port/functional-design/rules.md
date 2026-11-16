# 業務規則：U5 `pricing-lookup-port`

## Source of truth

```yaml
rules:
  - id: BR5.1
    statement: 公開入口為 fetch_hourly；結果僅 hit／miss／unsupported
    category: constraint
    applies_to: PricingLookupPort
    trigger: 任何查價呼叫
    logic: >
      IF 呼叫目錄價 THEN 經 cost.pricing_client.fetch_hourly(cloud, sku, region)
      回傳 PriceHit|PriceMiss|PriceUnsupported；不得改為拋 HTTP 例外給建議流程
    violation: 呼叫端因查價例外而中止建議
    source: FR5.5, Q1=A

  - id: BR5.2
    statement: 查得價格不得進入估價明細寫入路徑
    category: policy
    applies_to: PriceHit, PricingLookupPort
    trigger: 查價成功後
    logic: >
      IF 取得 PriceHit THEN 僅允許寫入建議文字／暫存於 agent 狀態；
      禁止 Estimate／EstimateLineItem／EstimateSet 持久化路徑消費該結果
    violation: 明細列出現目錄價覆寫
    source: FR5.5, AH-6

  - id: BR5.3
    statement: 僅允許目錄價端點；禁止帳單／用量類 API
    category: constraint
    applies_to: CatalogEndpointPolicy
    trigger: 新增或呼叫外部定價客戶端
    logic: >
      IF 目標為 Cost Explorer／Cost Management／Billing Export 或等價 THEN 禁止實作與呼叫；
      允許：AWS Price List Query＋Bulk、GCP Catalog、Azure Retail
    violation: CI／邊界測試失敗；不得合併
    source: FR5.6, FR5.7, Q6=A

  - id: BR5.4
    statement: AWS SDK 可啟用；失敗或無憑證必須降級
    category: policy
    applies_to: AwsSdkSettings, PricingLookupPort
    trigger: cloud=aws 查價
    logic: >
      IF COST_PRICING_USE_SDK 未顯式關閉 THEN 可嘗試 SDK；
      IF 無 IAM／SDK 錯誤 THEN 降級公開 Bulk；
      IF 仍無價 THEN PriceMiss 或 PriceUnsupported；不得使建議流程失敗
    violation: 缺憑證或 SDK 錯誤導致未處理例外向上拋
    source: FR5.10, FR9.4, FR11.4, Q3=A

  - id: BR5.5
    statement: IAM／API key 範圍最小化（消費端執行期）
    category: authorization
    applies_to: AwsSdkSettings, CatalogEndpointPolicy
    trigger: 使用雲端憑證查價
    logic: >
      IF 使用 AWS IAM THEN 僅 Price List Query 所需動作（如 pricing:GetProducts）；
      IF 使用 GCP API key THEN 限用於 Cloud Billing Catalog
    violation: 擴大至帳戶資源或帳單讀取
    source: FR5.9, ADR-0018

  - id: BR5.6
    statement: 保留 24h 磁碟 offer 快取；不重建 DB pricing_cache
    category: policy
    applies_to: OfferDiskCache
    trigger: Bulk／下載路徑查價
    logic: >
      IF 走公開 offer 下載 THEN 可讀寫 .pricing_offer_cache／TTL 24h；
      IF 需要跨行程快取 THEN 不得新建 Postgres pricing_cache 表
    violation: 重新引入 live pricing_cache 表或應用讀寫 archive_*
    source: FR9.2, OQ-DD2, Q2=A

  - id: BR5.7
    statement: httpx 不得在 Port 外直打雲端 Pricing API
    category: constraint
    applies_to: PricingLookupPort
    trigger: 程式碼變更／CI
    logic: >
      IF backend 他處（非 pricing_* 存活集、且非 cost/sku_catalog.py）
      以 httpx／requests 直打 allowlist 定價 host THEN 邊界檢查失敗
    violation: CI 紅燈
    source: unit-of-work U5, domain, FR13.4

  - id: BR5.8
    statement: intake 寫入路徑不得 import PricingLookup
    category: policy
    applies_to: PricingLookupPort
    trigger: CI 邊界腳本
    logic: >
      IF estimate_intake_router／estimate_intake_service／estimate_access／
      estimate_audit（或等價明細寫入模組）import pricing_client／pricing_sdk
      THEN 檢查失敗。
      允許 intake 延遲 import cost.sku_catalog（只取描述，見 BR5.11）
    violation: CI 紅燈
    source: AH-6, Q5=A, FR13.4

  - id: BR5.9
    statement: 保留 pricing_sdk 與最小存活模組集
    category: constraint
    applies_to: PricingLookupPort
    trigger: 退場／重構
    logic: >
      IF 本 Unit 合併 THEN 仍存在 pricing_sdk、pricing_query_parser、
      pricing_units、pricing_gcp、pricing_azure、pricing_offer_parser、config＋YAML
      與 fetch_hourly 入口
    violation: 誤刪導致三雲查價不可用
    source: FR9.4, FR9.5

  - id: BR5.10
    statement: warm／死腳本須盤點修或刪，且不阻啟動
    category: policy
    applies_to: OfferDiskCache
    trigger: 本 Unit code-generation
    logic: >
      IF 仍有 warm_aws_pricing_cache 或文件引用已退場 price_cache／DB
      THEN 改為暖磁碟／呼叫 Port 或刪除死引用；缺憑證時腳本失敗不得阻止應用啟動
    violation: 啟動依賴 warm 腳本成功或引用已刪模組
    source: FR9.7, Q4=A

  - id: BR5.11
    statement: sku_catalog 只解讀 SKU 描述，不經 Port 取價
    category: constraint
    applies_to: CatalogEndpointPolicy
    trigger: 上傳寫入前的規格解讀
    logic: >
      IF 呼叫 sku_catalog THEN 僅回傳人類可讀描述；不得回傳或持久化 hourly；
      不得 import／轉呼叫 fetch_hourly；須列入 validate_pricing_lookup_boundary 存活集；
      失敗靜默。PriceHit 路徑仍僅供 U7 建議文字
    violation: intake 經 Port 取價並寫回明細
    source: FR13, FR5.5, AH-6
```

## 規則摘要表

| ID | 一句話 |
|---|---|
| BR5.1 | `fetch_hourly` → hit／miss／unsupported |
| BR5.2 | 價不回寫明細（AH-6） |
| BR5.3 | 僅目錄價；禁帳單 API |
| BR5.4 | SDK 可啟用；失敗降級 |
| BR5.5 | 最小 IAM／API key 範圍 |
| BR5.6 | 保留磁碟快取；不重建 DB |
| BR5.7 | httpx 不得 Port 外直打 |
| BR5.8 | intake 不得 import Port |
| BR5.9 | 保留 sdk／存活集 |
| BR5.10 | warm／死引用盤點 |
| BR5.11 | sku_catalog 只寫描述 |

<!-- post-confirmation save -->
