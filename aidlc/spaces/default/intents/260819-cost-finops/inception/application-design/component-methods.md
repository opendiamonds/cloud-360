# Component Methods — C1 成本估算

<!-- Stage: application-design。詳細商業規則在 functional-design；此檔只定公開契約。 -->

## 慣例

- 金額 JSON：number，**USD 兩位小數**（四捨五入在 calculator 出口一次完成）。
- 時數：整數 0–24；非法 **422**，body 含欄位錯誤字串，列值不變。
- 無權：HTTP **403**（與現有 `require_story_action` 同形）。
- 圖不可見（非擁有者且未分享）：**404**（不洩漏存在）。
- 未設區域時讀取仍 2xx，但 `priced` 列為空、`region_required: true`，且不呼叫官方價。
- OpenAPI dump 與 `frontend/src/types/api.d.ts` 同步（CI `--check`）。

## `cost_router`

| 方法 | 路徑 | 授權 | 成功 body 必含 |
|---|---|---|---|
| GET | `/diagrams` | `C1.view` | `{ items: [{ id, title }] }` 僅呼叫者可見圖 |
| GET | `/diagrams/{id}` | `C1.view` | 快照：`id`、`region`、`region_required`、`diagram_cloud`、`allowed_regions`、`lines[]`、`total`（無已定價時為 `null`）、`unpriced_count`、`pie`、`pricing_as_of`、`coverage`（見下）、`budget`（第一段恒 `null`）、`overspent`（第一段恒 `false`） |
| PUT | `/diagrams/{id}/region` | `C1r.edit` | `{ region }`；區域須屬該圖 `diagram_cloud` 的 `allowed_regions`，否則 **400** |
| PUT | `/diagrams/{id}/lines/{mxcell_id}/hours` | `C1h.edit` | `{ mxcell_id, hours }` |
| PUT | `/diagrams/{id}/lines/{mxcell_id}/sku` | `C1o.edit` | `{ mxcell_id, sku }` |
| PUT | `/diagrams/{id}/lines/{mxcell_id}/override` | `C1o.edit` | `{ mxcell_id, hourly_override }` |
| PUT | `/diagrams/{id}/budget` | `C1b.edit` | `{ budget }`；**第二段**才掛路由或恒 404 |
| GET | `/diagrams/{id}/audit` | `C1.view` | `{ items: [{ at, actor, diagram_id, field, old_value, new_value }] }` |
| GET | `/banner` | 有 `C1.view` 才由前端呼叫；**第一段不註冊此路由** | `{ active: bool, count, sample?: { id, title, total, budget } }` |

`coverage`：本輪雲別清單 `[{ cloud: str, mode: "official_list" | "manual_override_only" }]`。對應 FR-2.2／定價假設。靜態來自 `pricing_coverage.yaml`（現況三雲皆 `official_list`，見 ADR-C1-09）。

`diagram_cloud`：由圖上 SKU mapper **唯一命中**的 cloud 多數決（`aws`｜`gcp`｜`azure`｜null）。  
`allowed_regions`：`supported_regions.yaml` 的 `by_cloud[diagram_cloud]`；無法偵測雲時回傳扁平全清單。  
若 DB 已存區域不在 `allowed_regions`，本輪視為未設（`region` 回應為 null、`region_required: true`），強制重選。

`lines[]` 每列：`mxcell_id`、`label`、`sku`、`category`、`hourly_list`（nullable）、`hours`、`subtotal`（nullable）、`status` ∈ `priced`｜`unpriced`｜`price_fetch_failed`｜`manual_override`。

## `diagram_extractor`

```
extract_priceable_cells(xml: str) -> list[Cell]
# Cell: mxcell_id, label_plain, style
# 規則同 FR-1.1；不得呼叫 parse_diagram_summary
```

## `sku_mapper`

```
map_cell(label, style, table) -> MapResult
# unique | none | ambiguous(candidates)
```

## `cost_calculator`（純函式；PBT 掛此模組）

```
hourly_from_monthly(M) -> Decimal        # M/730
line_subtotal(hourly, hours) -> Decimal  # hourly * hours * 30
total_priced(lines) -> Decimal           # 只加 priced 與 manual_override
pie_buckets(lines) -> dict[str, Decimal] # compute/database/network/other
is_overspent(total, budget) -> bool      # budget is None => False；相等 False
```

模組內禁止 `httpx`、Session、`HTTPException`。

## `pricing_client`

```
fetch_hourly(cloud, sku, region) -> PriceHit | PriceMiss | PriceUnsupported
# PriceHit: hourly Decimal, fetched_at UTC, source
# PriceMiss: 該雲 official_list 但此次失敗或該 SKU 無代表規格命中 → 列 price_fetch_failed
# PriceUnsupported: coverage mode=manual_override_only（本輪不用）→ 不發 HTTP
# aws → SDK get_products → Bulk JSON；gcp → Catalog；azure → Retail Prices
# 測試可 COST_PRICING_STUB=1；禁止 Cost Explorer／客戶帳單路徑
```

## `cost_service`（編排）

```
get_snapshot(user, diagram_id) -> Snapshot
# 1 可見性 2 讀 XML 3 extract 4 對齊 line 表 5 map sku
# 6 若 region 已設：cache 或 pricing_client
# 7 calculator 8 組 pie／total
apply_hours / apply_region / apply_sku / apply_override / apply_budget
record_audit(...)
banner_for(user) -> Banner
```

覆寫與預算成功後寫 `cost_audit_event`。時數／區域本輪**不**強制稽核（故事未要求）。

## 前端方法（非 HTTP）

| 元件 | 行為 |
|---|---|
| `HoursInput` | blur／Enter → PUT hours；422 顯示列錯誤 |
| `RegionField` | `<select>`；選項依 snapshot `diagram_cloud` 過濾 → PUT region |
| `CostPage` | 掛載 GET snapshot；切圖重抓 |
| `OverspendBanner` | Layout：若 `can('C1','view')` 則 GET `/banner` |
| `SuccessCostCta` | `navigate('/cost?diagram=' + id)` |
