# Tech Stack Decisions — cost-api

> Unit: `cost-api` · service

| 元件 | 決策 |
|---|---|
| HTTP | FastAPI router `prefix=/api/cost` |
| HTTP client | **httpx**（既有 backend 慣例） |
| ORM | SQLAlchemy Session via `get_db` |
| 設定 | `pricing_coverage.yaml`、`sku_map.yaml`、`supported_regions.yaml` 啟動載入 |
| 測試 | unittest TestClient + pricing stub |

**新依賴**：不新增 PyPI（httpx 已存在）。OpenAPI：`scripts/dump_openapi.py --check`。
