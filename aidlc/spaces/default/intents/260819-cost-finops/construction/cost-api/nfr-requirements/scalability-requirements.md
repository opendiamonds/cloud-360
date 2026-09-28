# Scalability Requirements — cost-api

> Unit: `cost-api` · embedded monolith · MVP

## SCL-A-1 並發

- 單 FastAPI process；無 horizontal scale 本 intent
- Postgres `pricing_cache` 共享；UK 防重複列

## SCL-A-2 資料量

| 實體 | 上界（設計） |
|---|---|
| 每圖列 | ~50 priceable cells（NFR-4 假設） |
| cache 列 | O(雲×SKU×區域)；TTL 24h 自然淘汰 |
| audit | append-only；本輪無 purge API |

## SCL-A-3 瓶頸

- 外網定價 sequential → **cache 必須有效** 才能滿 NFR-4

## SCL-A-4 不引入

Redis、queue、read replica — out of scope（`components.md`）
