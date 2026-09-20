# Tech Stack Decisions — cost-schema-rbac

> Unit: `cost-schema-rbac` · spec

| 面向 | 決策 |
|---|---|
| RDBMS | PostgreSQL（deploy）；SQLite in-memory（CI unittest） |
| 遷移 | **`schema_rbac.sql` + `database._ensure_cost_schema()`**；不引入 Alembic 本 intent |
| ORM | SQLAlchemy models 對齊 DDL（與既有 `models.py` 風格） |
| 新依賴 | **無** |

同步 blocking：`schema_rbac.sql`、`DEPLOY.md`、`database.py`（BR-S 三件套）。
