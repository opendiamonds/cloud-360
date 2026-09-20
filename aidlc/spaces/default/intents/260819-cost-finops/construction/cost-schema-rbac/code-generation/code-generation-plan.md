# Code Generation Plan — cost-schema-rbac

> Unit: `cost-schema-rbac` · Bolt B1 · 上游：functional-design、infrastructure-design、`schema_rbac.sql`。

## 落點

| 元件 | 檔案 | 性質 |
|---|---|---|
| ORM 四表 | `backend/models.py` | 追加 `DiagramCost`、`DiagramCostLine`、`PricingCache`、`CostAuditEvent` |
| 啟動補丁 | `backend/database.py` | `_ensure_cost_schema()`；`init_db()` 在 seed 後呼叫 `ensure_missing_role_permissions()` |
| RBAC 補丁 | `backend/services/rbac.py` | `ensure_missing_role_permissions()`（只 INSERT） |
| Seed 資料 | `backend/services/rbac_seed_data.py`、`schema_rbac.sql` | C1h/C1r/C1b/C1o 共 44 列 |
| 部署說明 | `DEPLOY.md` §2.2.4 | C1 四表與 RBAC 補丁 |

## 實作順序

1. `models.py` 四表 ORM
2. `schema_rbac.sql` + `rbac_seed_data.py` 種子
3. `database.py` DDL 補丁與啟動順序
4. `rbac.py` ensure_missing（既有 DB 升級路徑）
5. `DEPLOY.md` 同步

## 測試計畫

- 隨 `init_db()` 在 test stack 啟動時驗證表存在
- RBAC 列數由 `schema_rbac.sql` 與 cost-api TestClient 403/200 間接驗證
