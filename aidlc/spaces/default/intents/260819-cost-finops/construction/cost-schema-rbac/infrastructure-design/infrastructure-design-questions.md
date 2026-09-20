# Infrastructure Design — 釐清問題（cost-schema-rbac）

> Stage: infrastructure-design（3.4）· Unit: `cost-schema-rbac` · kind: **spec**  
> 本 unit **無** deployment-architecture／infrastructure-services／monitoring／cicd 產物（kind=spec）。

## 已由上游定案、不重問

| 事項 | 來源 |
|---|---|
| DDL／seed 進既有 Postgres | embedded |
| 同步 `schema_rbac.sql`、`DEPLOY.md`、`database.py` | project.md Mandated |
| 無新容器 | unit-of-work |

---

## Q1. 遷移執行時機？

A. **`init_db()` / startup `_ensure_cost_schema()`** + 新環境 `schema_rbac.sql` 全量 seed。**（建議）**  
B. 獨立 migration CLI。代價：超出 embedded 模型。  
C. Not yet defined  

[Answer]: A. **ensure + schema_rbac.sql**

---

## Plan Approval

- [x] 計畫已核可（Q1=A）
