# Code Generation Plan — cost-api

> Unit: `cost-api` · Bolt B1 · 上游：functional-design、`component-methods.md`、OQ-3 定案。

## 落點

| 元件 | 檔案 | 性質 |
|---|---|---|
| Router | `backend/cost/cost_router.py` | GET/PUT B1 路由；budget/banner → 404 |
| Service | `backend/cost/cost_service.py` | 協調 DB + calculator + pricing |
| Port | `backend/cost/pricing_client.py` | httpx + `COST_PRICING_STUB` |
| 支援模組 | `diagram_extractor.py`、`sku_mapper.py`、`price_cache.py`、`config.py` | |
| 設定 | `pricing_coverage.yaml`、`pricing_urls.yaml`、`sku_map.yaml` | repo 內 allowlist |
| 掛載 | `backend/main.py` | `prefix="/api/cost"` |
| 測試 | `backend/tests/test_cost_api.py` | TestClient allow/deny/422 |
| 規格 | `openapi.json` | `dump_openapi.py --check` |

## 實作順序

1. YAML 設定與 config 載入
2. pricing_client（stub 優先）
3. cost_service + diagram_extractor + sku_mapper
4. cost_router + main 掛載
5. TestClient + OpenAPI 同步

## 測試計畫

- TestClient：FinOps allow、Developer 403、hours 422、budget 404
- OpenAPI drift gate
