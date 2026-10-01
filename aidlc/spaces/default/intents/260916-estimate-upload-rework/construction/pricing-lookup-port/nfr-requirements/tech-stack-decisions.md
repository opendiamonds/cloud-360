# Tech Stack Decisions — pricing-lookup-port

> Unit: `pricing-lookup-port`（U5）· kind: **library** · Q1–Q6=A。

| 面向 | 決策 | 理由 |
|---|---|---|
| 語言／執行期 | **既有 Python 3**（backend） | brownfield；無新 runtime |
| 模組位置 | **`backend/cost/pricing_client.py`** 為 `fetch_hourly` 公開入口；文件稱 PricingLookup | FD Q1=A、FR9.5 |
| 存活集 | **保留** `pricing_sdk`、`pricing_query_parser`、`pricing_units`、`pricing_offer_parser`、`pricing_gcp`、`pricing_azure`、`config`＋ YAML | FR9.4、FR9.5、BR5.9 |
| AWS 查價 | **boto3 Price List Query**（可開關）＋公開 Bulk Price List | FR5.6、FR9.4、Q4=A |
| GCP／Azure | **既有** Catalog／Retail 客戶（httpx） | FD Q6=A |
| HTTP 客戶 | **既有 `httpx`**；逾時 connect 3s／read 180s（可 env） | Q1=A；不新引入 requests 為預設 |
| 快取 | **磁碟** `.pricing_offer_cache`，TTL 24h；**不**重建 Postgres `pricing_cache` | FD Q2=A、BR5.6 |
| SDK 開關 | **`COST_PRICING_USE_SDK`**：未設／`auto`＝可啟用；`0`／`false`／`no`＝關 | Q4=A、FR9.4 |
| 重試 | **無額外重試迴圈**；降級鏈即容錯 | Q2=A |
| 邊界檢查 | **CI 腳本**：intake 禁 import Port；`sku_catalog` 列入存活／允許集（只取描述） | Q5=A、BR5.7–5.8、BR5.11 |
| 測試 | **`unittest` + mock**；邊界腳本進 CI；不強制 CI 真金鑰 | Q3=A、Q6=A、NFR8 |
| 新基礎設施 | **無**（無佇列、無新服務、無 Playwright） | NFR8 |

## 依賴變更（code-gen）

| 套件 | 動作 | 備註 |
|---|---|---|
| `httpx` | **保留** | Bulk／GCP／Azure |
| `boto3`／`botocore` | **保留** | FR9.4 SDK 路徑 |
| Playwright／瀏覽器 | **不得新增** | NFR8 |

## 不做

- 不重建 live `pricing_cache` 表或讀寫 `archive_*` 作目錄價快取
- 不引入 Cost Explorer／Cost Management／Billing Export 客戶端
- 不把目錄**價格**寫入 Estimate／EstimateLineItem 金額欄（描述見 FR13／`sku_catalog`）
- 不為本 unit 手寫 TCMS（歸 `tcms-test-cases`）

<!-- confirmed: Looks correct -->
