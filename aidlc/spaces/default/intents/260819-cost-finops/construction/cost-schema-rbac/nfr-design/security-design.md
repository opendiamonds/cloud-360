# Security Design — cost-schema-rbac

> Unit: `cost-schema-rbac` · spec · 承接 `../nfr-requirements/security-requirements.md`

## 1. IAM 設計（核心）

### 1.1 新增 story 與權限列

| Story | 能力 | 種子角色（摘要） |
|---|---|---|
| `C1` | view 成本頁／snapshot | FinOps_Analyst、Architect（view） |
| `C1h` | edit 每日時數 | FinOps_Analyst |
| `C1r` | edit 定價區域 | FinOps_Analyst |
| `C1o` | edit SKU／hourly override | FinOps_Analyst |
| `C1b` | edit 月預算（B2） | FinOps_Analyst |

44 列 C1* 寫入 `schema_rbac.sql`；與既有 `role_permissions` **append-only** 語意一致。

### 1.2 Brownfield 路徑

```
init_db / startup
  └─ _ensure_cost_schema()          # DDL idempotent
       └─ ensure_missing_role_permissions(force=False)
            └─ INSERT ... ON CONFLICT DO NOTHING（或等價「只補缺失」）
```

**禁止**：`force=True` 在 production-like 環境覆寫 Admin 自訂矩陣。

## 2. High-risk 變更流程（human approval）

| 步驟 | 內容 |
|---|---|
| Plan | 四表 + 種子 diff；`_ensure_cost_schema` 行為 |
| Impact | 缺列 → C1 端點 403；錯誤 UPSERT → 矩陣被改寫 |
| Rollback | Admin UI 逐格還原；**不得**重跑整份 `schema_rbac.sql`（DELETE 全表） |
| Gate | B1 squash-merge 前 reviewer + 人類確認 |

## 3. 稽核表設計（SEC-S-2）

`cost_audit_event`：

- FK → `user_diagrams(id)` ON DELETE CASCADE
- `field` ∈ `{sku, hourly, monthly_budget}`
- `old_value` / `new_value` TEXT；**禁止**存 credential
- 寫入：**僅** `cost-api` 成功 mutation 後

## 4. Encryption／Network

| 面向 | 設計 |
|---|---|
| Encryption | `NUMERIC(12,2)` 等金額欄走既有 Postgres TLS／磁碟政策；無欄位級加密 |
| Network | 無新入站埠；DDL 隨 backend migration 執行 |

## 5. 驗證設計

| 關卡 | 方法 |
|---|---|
| 種子只補缺失 | TestClient brownfield：`ensure_missing` 兩次，列數不減 |
| C1 allow/deny | `test_rbac.py` 擴充（team.md A 規則） |
| 禁止 force 覆寫 | 文件 + code review；可選 unittest mock |

## 6. Code Gen 檢查清單

- [ ] `schema_rbac.sql` 與 `DEPLOY.md` 同步（project.md Mandated）
- [ ] `database.py` `_ensure_cost_schema()` 與 FD 一致
- [ ] 新環境 seed 後 C1.view 端點非 403（smoke）
