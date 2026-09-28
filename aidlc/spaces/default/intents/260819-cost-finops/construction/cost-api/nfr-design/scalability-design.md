# Scalability Design — cost-api

> Unit: `cost-api` · service · 承接 `../nfr-requirements/scalability-requirements.md`

## 1. 部署拓樸

```text
[Single FastAPI process] ──► [Postgres]
        │
        └── outbound HTTPS (pricing)
```

- **無** horizontal scale 本 intent
- **無** Redis / read replica / queue

## 2. 資料量上界

| 實體 | 設計上界 | 策略 |
|---|---|---|
| 每圖 priceable 列 | ~50 | NFR-4 假設；align_lines 線性 |
| `pricing_cache` 列 | O(雲×SKU×區域) | TTL 24h；無 purge API 本輪 |
| `cost_audit_event` | append-only | 無 archive API |

## 3. 瓶頸與緩解

| 瓶頸 | 緩解 |
|---|---|
| Sequential 外網定價 | Cache hit；miss 標 `price_fetch_failed` |
| 大 XML parse | 單圖 scope；禁 summary parser |
| DB connection | 沿用既有 pool |

## 4. 不引入元件

- Celery / RQ
- Redis cache layer
- CDN for API

## 5. 未來擴展（out of scope）

若 N>50 或冷查價常態：parallel fetch + rate limit — 需新 ADR，不在 C1 MVP。

## 6. Code Gen 檢查清單

- [ ] cache UK 約束在 DDL
- [ ] align_lines 單 transaction（見 reliability）
