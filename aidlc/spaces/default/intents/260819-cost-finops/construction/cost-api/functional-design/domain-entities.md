# Domain Entities — cost-api

> Unit: `cost-api` · Q1–Q5=A  
> 上游：`component-methods.md`、`components.md`、`cost-schema-rbac`／`cost-calculator` FD。

## 邊界

本 unit 的「實體」是 **API／service 層的值物件與 Port**，不是 ORM（ORM 在 `cost-schema-rbac`）。禁止在 router 寫公式；禁止 calculator import httpx。

## Snapshot（GET 回應形狀）

| 欄位 | 型別 | 第一段 |
|---|---|---|
| `id` | int | diagram id |
| `region` | str \| null | `diagram_cost.pricing_region`（若不在 `allowed_regions` 則視為未設） |
| `region_required` | bool | `region is null or region==''` |
| `diagram_cloud` | `aws`\|`gcp`\|`azure`\|null | SKU mapper 多數決 |
| `allowed_regions` | `str[]` | `by_cloud[diagram_cloud]` 或扁平全清單 |
| `lines` | `LineOut[]` | 見下 |
| `total` | number \| null | calculator `total_priced`；無任何 priced/manual_override 時 **null** |
| `unpriced_count` | int | status ∈ {unpriced, price_fetch_failed} 列數 |
| `pie` | `{compute,database,network,other}` | calculator `pie_buckets` |
| `pricing_as_of` | ISO-8601 UTC \| null | 本次用到的官方價 `fetched_at` 最大值；全 override／無價則 null |
| `coverage` | `CoverageEntry[]` | 靜態 YAML |
| `budget` | null | 第一段恒 null |
| `overspent` | false | 第一段恒 false |

### LineOut

| 欄位 | 來源 |
|---|---|
| `mxcell_id`, `label` | extractor + XML |
| `sku` | override 或 mapper 命中 |
| `category` | mapper／YAML |
| `hourly_list` | 官方價或 null |
| `hours` | line 表 |
| `subtotal` | calculator `line_subtotal` 或 null（未定價） |
| `status` | 見 business-rules BR-A-7 |

### CoverageEntry

`{ cloud: str, mode: "official_list" | "manual_override_only" }`

## Port：`pricing_client`

```python
fetch_hourly(cloud, sku, region) -> PriceHit | PriceMiss | PriceUnsupported
```

| 變體 | 欄位 | 語意 |
|---|---|---|
| `PriceHit` | `hourly: Decimal`, `fetched_at: datetime`, `source` | 寫 cache |
| `PriceMiss` | — | `official_list` 但失敗／無代表規格命中 |
| `PriceUnsupported` | — | `mode=manual_override_only`（本輪三雲皆不用；保留型態） |

## Port：`sku_mapper`

`MapResult = unique(sku, category) | none | ambiguous(candidates[])`

## 內部：`LineForCalc`（餵 calculator）

由 service 組裝，形狀見 `cost-calculator` FD。`hourly`：override 或 `hourly_list`；`category` 來自 mapper。

## AuditItem（GET audit）

| 欄位 | DB 對照 |
|---|---|
| `at` | `cost_audit_event.created_at` |
| `actor` | `actor_username` |
| `diagram_id` | FK |
| `field` | `field` |
| `mxcell_id` | 列級必填；預算 null |
| `old_value`, `new_value` | text |

Construction 須更新 OpenAPI／`api.d.ts` 含 `mxcell_id`（`cost-schema-rbac` FD 衍生）。

## 錯誤載體（422）

`{ "detail": [ { "loc": ["body","hours"], "msg": "hours must be 0-24" } ] }` — 對齊 FastAPI 慣例；列值不變。

## 與其他 unit

| unit | 關係 |
|---|---|
| `cost-schema-rbac` | R/W 四表 + RBAC 種子 |
| `cost-calculator` | import 五函式 |
| `cost-ui` | 消費 OpenAPI |
| `cost-budget-banner` | 第二段加路由；第一段 service 方法可 stub |
