# Logical Components — cost-api

> Unit: `cost-api` · service · Q2=A `CostService`

## 1. 邏輯元件圖

```text
HTTP Client / cost-ui
        |
        v
 cost_router.py          ← FastAPI routes, Pydantic, Depends(get_current_user)
        |
        v
 cost_service.py          ← CostService 編排（404/403, transactions）
        |
        +-- diagram_extractor.py    extract_priceable_cells(xml)
        +-- sku_mapper.py           cloud → sku/category
        +-- price_cache.py          Postgres read/write
        +-- pricing_client.py       httpx, timeout, PriceHit/Miss/Unsupported
        +-- cost_calculator.py      （library unit）
        |
        v
 SQLAlchemy Session / UserDiagram / cost_* tables
```

## 2. 元件職責

| 元件 | 職責 | 非職責 |
|---|---|---|
| `cost_router` | 路由表、422 驗證、dependency 注入 | 404/403 業務規則 |
| `CostService` | snapshot 編排、align_lines、audit、banner_for（B2） | Decimal 算術細節 |
| `diagram_extractor` | FR-1.1 cells | 定價 |
| `sku_mapper` | 預設 SKU（無 override 時） | 覆寫 override |
| `price_cache` | TTL cache | HTTP |
| `pricing_client` | 外網 fetch | RBAC |
| `cost_calculator` | 算術 | I/O |

## 3. 請求序列（GET snapshot）

```
router.get_snapshot
  → service.get_snapshot(user, id)
       → load diagram (404 gate)
       → C1.view (403 gate)
       → extract + align_lines
       → for line: resolve price (cache → client)
       → calculator.total_priced + pie_buckets
       → Snapshot DTO
```

## 4. B1 vs B2 路由

| 路由 | B1 | B2 |
|---|---|---|
| GET/PUT 第一段 methods | ✓ | ✓ |
| PUT `.../budget` | 404 | ✓ |
| GET `/banner` | 404 | ✓ |

## 5. 無新增基礎設施元件

| 類型 | 本期 |
|---|---|
| Message queue | ❌ |
| Circuit breaker 函式庫 | ❌（timeout + degrade 足夠） |
| 獨立 pricing microservice | ❌ |

## 6. Code Gen 檢查清單

- [ ] `CostService` 方法與 `component-methods.md` 對齊
- [ ] `pricing_coverage.yaml` 啟動載入（FD Q4=A）
- [ ] GET audit 回應含 `mxcell_id`（跨 unit BR-A-12）
