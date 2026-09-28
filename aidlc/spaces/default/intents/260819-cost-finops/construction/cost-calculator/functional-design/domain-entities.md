# Domain Entities — cost-calculator

> Unit: `cost-calculator` · Q1–Q3=A  
> 上游：`unit-of-work.md`、`unit-of-work-story-map.md`、`requirements.md`、`components.md`、`component-methods.md`、`services.md`。

## 型別（Python，無 ORM）

本 library 沒有資料表。實體是記憶體內的值物件，給 `cost_service` 組裝 snapshot 用。

### Money

- `Decimal`，非負（負值拒絕於入口）
- 出口：scale=2、`ROUND_HALF_UP`
- JSON 邊界由 router 變成 number；此處不碰序列化

### LineForCalc

| 欄位 | 型別 | 來源 |
|---|---|---|
| `status` | `priced` \| `unpriced` \| `price_fetch_failed` \| `manual_override` | service |
| `hourly` | `Decimal \| None` | 官方或覆寫；未定價為 None。`manual_override` 時此欄即覆寫小時價 |
| `hours` | `int` | 列狀態；預設 24 不在本 library 設 |
| `category` | `str` | mapper／service；calculator 不推導（Q2=A） |

**不**帶 `subtotal` 欄。`total_priced`／`pie_buckets` 一律用 `hourly×hours×30` 的精確值重算，再套出口量化與最大餘數法。status 決定是否納入，不讀呼叫端預先算好的小計。

### PieBuckets

固定四鍵：`compute`、`database`、`network`、`other` → `Money`。

### OverspendInput

`total: Decimal`、`budget: Decimal \| None`。

## 生命週期

無狀態、無 identity。每次 snapshot 由 service 新建 `LineForCalc` 清單再丟進來。不快取。

## 與其他 unit 的契約

| 對方 | 方向 | 形狀 |
|---|---|---|
| `cost-api` `cost_service` | 消費者 | 上列函式；本 library `depends_on: []` |
| `cost-schema-rbac` | 無直接邊 | 表裡的 hours／override 由 service 讀出再傳入 |
| `cost-ui` | 無直接邊 | 只看見量化後的 JSON number |

禁止：calculator → pricing_client（`component-dependency.md` 零依賴）。
