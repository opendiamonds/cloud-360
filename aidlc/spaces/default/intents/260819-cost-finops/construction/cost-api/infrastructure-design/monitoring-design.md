# Monitoring Design — cost-api

> Unit: `cost-api` · service · MVP 沿用既有 observability

## 1. 範圍

本 intent **不**新增 CloudWatch／Prometheus／Sentry 整合。監控依既有 backend logging + staging 人工驗收。

## 2. 結構化 log（建議欄位）

| 事件 | level | 欄位 |
|---|---|---|
| snapshot 完成 | INFO | `diagram_id`, `line_count`, `cache_hits`, `cache_misses`, `duration_ms` |
| 定價 miss | WARNING | `cloud`, `sku`, `region`, `reason`（**不含**完整 URL query PII） |
| 定價 unsupported | DEBUG | `cloud` |
| align_lines 失敗 | ERROR | `diagram_id`, `exc_type` |

**禁止** INFO 記錄完整 `xml_data` 或 offer JSON 全文。

## 3. 健康檢查

- 沿用 `/api/health`（若存在）或既有 backend health；**不**新增 cost 專用 health endpoint
- Postgres down → 現有 5xx 行為

## 4. 告警（out of scope）

- 無 PagerDuty／Slack 新路由
- NFR-4 5s：Playwright staging 手動 + TCMS，非 APM 告警

## 5. 營運查詢（手動）

| 問題 | 查法 |
|---|---|
| cache 命中率低 | grep `cache_misses` in backend logs |
| AWS 出站被擋 | miss 飆升 + staging 無 priced 列 |
| 403 暴增 | 既有 auth log + RBAC seed 檢查 |

## 6. Code Gen 檢查清單

- [ ] pricing_client 失敗有 WARNING 一行
- [ ] 無 print debug 殘留
