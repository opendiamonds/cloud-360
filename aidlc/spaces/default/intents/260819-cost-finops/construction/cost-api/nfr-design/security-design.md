# Security Design — cost-api

> Unit: `cost-api` · service · 承接 `../nfr-requirements/security-requirements.md`

## 1. IAM 閘門

```text
Client → cost_router
           Depends(get_current_user)     # JWT
           → cost_service.*
                1. diagram 不可見 → HTTP 404
                2. !user_can(C1, view) → HTTP 403
                3. mutating: !user_can(C1h|r|o|b, edit) → HTTP 403
```

**順序不可顛倒**：404 優先於 403，避免枚舉私有圖 id。

| 端點族 | Story |
|---|---|
| GET snapshot / list | `C1.view` |
| PUT hours | `C1h.edit` |
| PUT region | `C1r.edit` |
| PUT sku / override | `C1o.edit` |
| PUT budget（B2） | `C1b.edit` |

## 2. 輸入驗證

| 欄位 | 規則 | HTTP |
|---|---|---|
| `hours` | int 0–24 | 422 |
| `region` | 非空 str len≤64 | 422 |
| `hourly` override | Decimal ≥0 | 422 |
| `budget` | null 或 Decimal ≥0 | 422 |

Calculator 非法域 → service **不**下沉；router 邊界已擋。

## 3. Network exposure

| 允許 | 禁止 |
|---|---|
| 出站 HTTPS 至公開價目 URL（infrastructure-design 定義） | AWS Billing / Cost Explorer API |
| 同源 REST `/api/cost*` | 任意 cloud account API |

靜態掃描：`pricing_client` 內 URL 白名單或 coverage yaml 驅動。

## 4. 敏感資料

- **禁止** INFO log 完整 `xml_data`（label 可能含 PII）
- 環境變數：價目 URL 模板在 deploy env；**無** cloud credential
- Audit：`cost_audit_event` 不含 secret

## 5. OpenAPI 契約

新路由同 PR：

1. `backend/scripts/dump_openapi.py --check`
2. `frontend` `gen:types` 更新 `api.d.ts`

## 6. ADR-0006 對照

| 面向 | 實作 |
|---|---|
| IAM | RBAC + 404/403 順序 |
| Encryption | 沿用 HTTPS + Postgres TLS |
| Network | 僅公開價目 HTTPS 出站 |
| Audit | `record_audit` on sku/override/budget |

## 7. Code Gen 檢查清單

- [ ] TestClient allow/deny C1（team.md Q3）
- [ ] 不可見 diagram_id → 404 非 403
- [ ] B1 無 budget/banner 路由註冊
