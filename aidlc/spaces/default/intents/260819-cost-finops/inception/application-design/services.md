# Services — C1 成本估算

<!-- Stage: application-design。仍是模組化單體內的領域服務，不是獨立 process。 -->

## 上游輸入

requirements、stories、team-practices、architecture（無既有 cost 服務）。

## 服務清單

| 服務 | 執行期 | 生命週期 |
|---|---|---|
| `cost_service` | 每個 API 請求，FastAPI 依賴注入 Session | 無獨立縮放；跟 backend 容器 |
| `pricing_client` | 快取未命中時同步 httpx | 逾時／重試細節 functional-design；失敗 → `price_fetch_failed` |
| `sku_map` | 行程啟動載入 YAML，記憶體唯讀 | 改檔需部署 |
| SPA `CostPage` | 瀏覽器 | 與 Vite／nginx 靜態 |

沒有 message bus。溝通：**同步 REST**（choreography 不適用）。

## 編排（orchestration）

`cost_service.get_snapshot` 是唯一編排者：

```
XML → extractor → sku_mapper → (region? price_cache/pricing_client) → calculator → Snapshot
```

<!-- Text fallback: 服務讀圖 XML，擷取可估價格，對照 SKU，有區域才查快取或公開價，再交給純函式算出總額與圓餅。 -->

第一段部署：budget 路由、`GET /banner`、`OverspendBanner` **皆不註冊／不掛載**。第二段同一 `cost_service` 加上預算欄與 `banner_for`。

## 與既有服務的契約

| 既有 | 用法 |
|---|---|
| `get_current_user`／`require_story_action` | 每個 cost 端點 |
| `UserDiagram` + 分享列 | 可見性（與 collab 同一套擁有者／分享） |
| `dump_openapi.py` | 新路徑必須進 spec |
| A1 Workspace 成功卡 | 只多一顆 CTA，不呼叫 cost 於產圖當下 |

不呼叫：`design_agent`、`review_orchestrator`、`wa_rule_engine`。

## 失敗語意

| 情況 | 服務行為 |
|---|---|
| 公開價 HTTP 失敗或無價 | 該列 `price_fetch_failed`，不寫正價進 cache |
| 無公開端點的雲 | `PriceUnsupported`：不呼叫外網；列 unpriced 直到 override（FR-2.2） |
| 有端點但失敗／缺價 | `PriceMiss`：列 `price_fetch_failed`，不寫正價進 cache |
| 快取命中且未過 TTL | 不打外網 |
| 官方價路徑字串含 Explorer／Billing | CI／靜態禁止，非執行期開關 |
