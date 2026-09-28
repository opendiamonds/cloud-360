# Security Requirements — cost-schema-rbac

> Unit: `cost-schema-rbac` · spec · 上游 FD BR-S-*、`requirements.md` NFR-5、ADR-C1-02。

## ADR-0006 四面向

| 面向 | 判定 | 處置 |
|---|---|---|
| **IAM** | **適用 —— 本 unit 核心** | 新增 `C1h`/`C1r`/`C1b`/`C1o` 種子；`ensure_missing` 只 INSERT |
| **Encryption** | **沿用既有** | 金額欄 `NUMERIC` 走 DB 傳輸／磁碟政策；無欄位級加密 |
| **Network exposure** | **不適用** | 無新入站埠；僅 DDL／seed |
| **Audit logging** | **適用（表）** | `cost_audit_event` 表契約；寫入邏輯在 `cost-api` |

## IAM 變更：high-risk 三項

### Plan

- 四表 DDL + 44 列 C1* 種子（新環境 `schema_rbac.sql`）
- brownfield：`_ensure_cost_schema()` + `ensure_missing_role_permissions()`，**不** DELETE 既有 `role_permissions`

### Impact

- 缺列 ⇒ 403 on C1h/r/b/o endpoints（staging 常見）
- 錯用 `force=True` 或 UPSERT 覆寫 ⇒ Admin 矩陣被改寫（**禁止**）

### Rollback

- 種子：Admin UI 逐格調回；**不得**依賴重跑整份 `schema_rbac.sql`（會 DELETE 全表）
- DDL：forward-only ALTER；回滾需新 migration（本輪不交付 down migration）

### Human approval

- 併入 **B1 Bolt squash-merge** gate（`team.md` walking skeleton off）

## SEC-S-1 種子只補缺失

對齊 BR-S-2；TestClient brownfield 模擬必過。

## SEC-S-2 稽核表完整性

`cost_audit_event` FK cascade；`field` 枚舉三值；禁止存 secret。
