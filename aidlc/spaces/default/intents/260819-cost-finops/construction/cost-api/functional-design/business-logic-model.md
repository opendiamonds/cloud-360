# Business Logic Model — cost-api

> Unit: `cost-api` · Q1–Q5=A  
> 上游：`component-methods.md`、`services.md`、`cost-calculator`／`cost-schema-rbac` FD。

## 模組邊界

```
cost_router → cost_service → { diagram_extractor, sku_mapper, price_cache, pricing_client, cost_calculator }
                          → SQLAlchemy Session / UserDiagram
```

Router：Pydantic、HTTP 狀態、`require_story_action`。Service：編排與交易；**不**把 `ValueError` 直接變 422（時數在 router／service 入口驗 0–24）。

## `get_snapshot(user, diagram_id)`

**HTTP 依賴順序（Q2=A）**：router 只掛 `Depends(get_current_user)`；**不在 router 掛** `require_story_action("C1")`，避免 Depends 先於 body 執行而把「不存在圖」變成 403。403／404 全在 service 內決定。

```
1. load UserDiagram by id
   └─ missing OR NOT _user_can_access_diagram → HTTP 404
2. user_can(user, "C1", "view") → False → HTTP 403
3. read xml_data
4. cells = extract_priceable_cells(xml)     # FR-1.1；禁 parse_diagram_summary
5. align_lines(diagram_id, cells)           # 見 §align_lines
6. load diagram_cost row (lazy insert empty region if absent)
7. region = pricing_region; region_required = not region
8. coverage = STATIC_COVERAGE (啟動載入 pricing_coverage.yaml，Q4=A)
9. for each aligned line (in cell order):
     build LineOut + LineForCalc:
       - label from cell
       - resolve sku/category via mapper unless sku_override
       - if hourly_override: status path → manual_override (skip pricing)
       - elif region set AND cloud mode official_list:
            cache lookup → miss → pricing_client.fetch_hourly (Q1 timeout)
            map PriceHit/Miss/Unsupported → status + hourly_list
       - else: unpriced (no region or manual-only cloud)
       - subtotal via line_subtotal when status priced/manual_override
10. lines_for_calc = filter priced + manual_override
11. total = total_priced(lines_for_calc) or null if empty
12. unpriced_count = count(status in {unpriced, price_fetch_failed})
13. pie = pie_buckets(lines_for_calc)
14. pricing_as_of = max(fetched_at) of hits used this request
15. return Snapshot(budget=null, overspent=false, coverage=coverage)
```

Mutating `apply_*` 同序：**404 → story edit 403 → 422**；router 對 edit 端點可掛 `require_story_action(C1h|C1r|C1o)` **僅在** service 確認 diagram 存在且可見之後——實作建議 router 薄封裝：先呼叫 `_assert_diagram_visible` helper 再跑 Depends，或統一由 service 拋 403 不用 Depends。

## `align_lines(diagram_id, cells)`

```
existing = SELECT lines for diagram
cell_ids = {c.mxcell_id for c in cells}
DELETE lines WHERE diagram_id AND mxcell_id NOT IN cell_ids
FOR c IN cells:
  IF NOT EXISTS line(diagram_id, c.mxcell_id):
    INSERT hours=24
  ELSE keep hours, sku_override, hourly_override
```

FR-1.5：FinOps 指定 SKU／覆寫價不會被 mapper 重蓋（mapper 只在無 override 時跑）。

## `apply_hours` / `apply_region` / `apply_sku` / `apply_override`

| 方法 | 授權 | 驗證 | 持久化 | 稽核 |
|---|---|---|---|---|
| `apply_hours` | C1h.edit | hours ∈ [0,24] int else 422 | UPDATE line.hours | 無 |
| `apply_region` | C1r.edit | non-empty str len≤64 | UPSERT diagram_cost.region | 無 |
| `apply_sku` | C1o.edit | sku 非空 | UPDATE line.sku_override | record_audit sku |
| `apply_override` | C1o.edit | hourly ≥0 Decimal | UPDATE line.hourly_override | record_audit hourly |

成功後回 **新 snapshot**（同 GET）或 PUT 契約欄位子集（methods 表）。

## `record_audit`

```
INSERT cost_audit_event(diagram_id, field, mxcell_id?, old_value, new_value, actor_username)
```

僅 `apply_sku`、`apply_override` 成功後 insert。（第二段 `apply_budget` 見 `cost-budget-banner` unit。）

## `pricing_client.fetch_hourly`

```
IF coverage[cloud].mode == manual_override_only:
  return PriceUnsupported   # 不發 HTTP
TRY httpx GET ... timeout=(3,3)
  parse hourly → PriceHit + write cache
EXCEPT/ bad status / parse → PriceMiss
```

無 region 時 service **不呼叫** client（FR-4.1）。

## `GET /diagrams`

```
visible = owned ∪ shared (same as collab list semantics)
filter user_can C1.view
return {id, title}
```

## 第一段路由表

| 註冊 | 路徑 |
|---|---|
| ✓ | GET/PUT 第一段 methods 列（除 budget、banner） |
| ✗ | PUT `.../budget`、GET `/banner` → 404 |

## 不在本 unit

Playwright、Layout、OpenAPI codegen 腳本、infra URL 字典細節（留 infrastructure-design）；`banner_for` 實作細節（B2）。
