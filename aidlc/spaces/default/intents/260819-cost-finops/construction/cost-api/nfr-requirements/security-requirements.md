# Security Requirements — cost-api

> Unit: `cost-api` · service · ADR-0006、FR-2.5

## ADR-0006 四面向

| 面向 | 判定 | 處置 |
|---|---|---|
| **IAM** | **適用** | `require_story_action` / service 內 C1.view；404→403 順序（FD BR-A-2） |
| **Encryption** | **沿用** | HTTPS 終端；DB 走既有 TLS |
| **Network exposure** | **適用** | **僅出站** 公開價目 HTTPS；禁止 Billing/Cost Explorer 路徑（靜態掃描 + stub） |
| **Audit logging** | **適用** | `record_audit` on override/sku/budget |

## SEC-A-1 圖可見性

不可見圖 **404**（不洩漏存在）；可見無權 **403**。

## SEC-A-2 輸入驗證

- hours 0–24 → 422
- 負 budget → 422（B2）
- 禁止 log 完整 XML 於 INFO（可能含 label PII）

## SEC-A-3 PriceUnsupported

無端點雲 **不發 HTTP**（FR-2.2）；避免誤用帳號 API。

## SEC-A-4 OpenAPI 同步

新 `/api/cost*` 同 PR 更新 `openapi.json` + `api.d.ts`（requirements 約束）。
