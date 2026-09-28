# Code Summary — cost-api

## 實際產出

| 檔案 | 變更 |
|---|---|
| `backend/cost/*.py` | **新增** router/service/client 等 9 模組 |
| `backend/cost/*.yaml` | coverage、urls、sku_map |
| `backend/main.py` | include_router `/api/cost` |
| `backend/requirements.txt` | `PyYAML>=6.0` |
| `backend/tests/test_cost_api.py` | **5** TestClient cases |
| `openapi.json` | C1 端點同步 |

## 關鍵決定

- **OQ-3／ADR-C1-09**：三雲皆 `official_list`（AWS Bulk／Pricing SDK；GCP Catalog + `GCP_BILLING_API_KEY`；Azure Retail Prices 公開）。
- **區域**：snapshot 回傳 `diagram_cloud`／`allowed_regions`；跨雲 PUT region → 400。
- **B1 路由裁切**：`PUT .../budget`、`GET /banner` 未註冊（404）。
- **CI stub**：`COST_PRICING_STUB=1` 固定 hourly、不出網。

## 驗證結果

| 項目 | 結果 |
|---|---|
| `tests.test_cost_api` | **5/5 OK** |
| `dump_openapi.py --check` | **exit 0** |
| test stack | `COST_PRICING_STUB=1` 內嵌 |

## 已知缺口（非 B1 阻擋）

- GET audit 回應含 `mxcell_id`（BR-A-12）待 B1 後續補強。

## B1 修正（e2e 發現）

- `get_snapshot()` 在 `align_lines` 後補 `db.commit()`，否則跨請求 PUT hours 404。

## Review

**Verdict:** READY  
**Reviewer:** aidlc-architecture-reviewer-agent  
**Date:** 2026-08-20T02:30:00Z  
**Iteration:** 1

### 摘要

B1 HTTP 契約、分層與定價 stub 已落地。無 Critical／Major。
