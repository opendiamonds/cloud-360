# Deployment Architecture — cost-api

> Unit: `cost-api` · service · embedded monolith

## 1. 拓樸（無新節點）

```text
Internet
    │
    ▼
Cloudflare Tunnel ──► nginx (frontend container)
                           │
                           ├── /api/* ──► backend:8000 (FastAPI)
                           │                  │
                           │                  ├── /api/cost/*  ← 本 unit
                           │                  └── existing routers
                           └── /* SPA

backend ──HTTPS outbound──► pricing.us-east-1.amazonaws.com  (AWS Price List / Pricing API)
backend ──HTTPS outbound──► cloudbilling.googleapis.com      (GCP Catalog；可選 API key)
backend ──HTTPS outbound──► prices.azure.com                 (Azure Retail Prices)
backend ──TCP────────────► postgres:5432
```

## 2. 程序邊界

| 元件 | 位置 | 備註 |
|---|---|---|
| `cost_router` | `backend/main.py` include | prefix `/api/cost` |
| `pricing_client` | backend process | 同步 httpx；3s timeout |
| `price_cache` | Postgres 表 | 同 DB 實例 |
| 設定 YAML | image 內 `backend/cost/*.yaml` | 改檔需 rebuild／redeploy |

## 3. B1 / B2 路由

| 路由 | B1 image | B2 image |
|---|---|---|
| GET/PUT 第一段 | ✓ | ✓ |
| PUT budget、GET /banner | **未註冊** | ✓（同容器熱更新） |

## 4. 環境分離

| 環境 | 設定 |
|---|---|
| 本機 dev | `backend/.env` **不含** 查價 key；可手設 `COST_PRICING_STUB=1` |
| CI test stack | `docker-compose.test.yml` 內嵌 `COST_PRICING_STUB=1` |
| staging deploy | `deploy/.env` **不新增** 雲 credential；AWS 走公開 URL |

## 5. 不部署

- 獨立 cost microservice
- Redis / ElastiCache
- 雲端 IAM role 供查價

## 6. Code Gen 檢查清單

- [ ] `main.py` 掛 router
- [ ] `deploy/docker-compose.deploy.yml` 無新 service
- [ ] B1 驗證 budget/banner 404
