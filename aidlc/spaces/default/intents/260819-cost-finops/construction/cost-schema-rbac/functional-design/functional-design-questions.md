# Functional Design — 釐清問題（cost-schema-rbac）

> Stage: functional-design（Construction 3.1，inline）· Unit: `cost-schema-rbac` · Kind: **spec**
> 本 unit 不產 `business-logic-model.md`／`frontend-components.md`（`produces_kinds` 僅 spec 的 business-rules、domain-entities）。
> 上游：`unit-of-work.md`、`unit-of-work-story-map.md`、`requirements.md`、`components.md`、`component-methods.md`、`services.md`。
> **成本揭露**：4 題。答完產出 business-rules／domain-entities。本 unit **gate: false**（五 unit 都寫完才開 Functional Design 總閘）。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 四表：`diagram_cost`、`diagram_cost_line`、`pricing_cache`、`cost_audit_event` | ADR-C1-03、ADR-C1-04、ADR-C1-06、`components.md` |
| `C1.view` 管頁面；`C1h`／`C1r`／`C1b`／`C1o` 管四種 edit | ADR-C1-02 |
| 只補缺失 `(role, story_id)` 種子；禁止 `force=False` 全表 no-op 當唯一路徑 | ADR-C1-02、`components.md` 種子缺口 |
| 同步 `schema_rbac.sql`、`DEPLOY.md`、`database.py` ensure | `unit-of-work.md`、`project.md` Mandated |
| 圖刪 cascade；line UK `(diagram_id, mxcell_id)` | ADR-C1-03 |
| 快取鍵 `(cloud, sku, region)`、TTL 24h | ADR-C1-04 |
| 稽核只寫覆寫／SKU／預算；時數／區域不寫 | ADR-C1-06、`component-methods.md` |
| USD 兩位 | ADR-C1-07 |

協作故事：C1-1～C1-7 皆間接依賴表與 RBAC（`unit-of-work-story-map.md`）。

---

## Q1. `ensure_missing_role_permissions()` 語意？

> staging 表非空時，現有 `ensure_role_permissions_seeded(force=False)` 整段 no-op（`rbac.py` L63–65）。C1 新 story 必須補進去且不覆寫 Admin 已調過的列。

A. **只 INSERT 缺失的 `(role, story_id)`**；`updated_by='system_seed'`；**不 UPDATE、不 DELETE** 既有列。**（建議，ADR-C1-02）**  
B. **UPSERT**：缺失插入、已存在則覆寫三旗標。代價：抹掉 Admin UI 調整。  
C. Not yet defined  
X. Other (please specify)

[Answer]: A. **只 INSERT 缺失的 `(role, story_id)`**；`updated_by='system_seed'`；**不 UPDATE、不 DELETE** 既有列。**（建議，ADR-C1-02）**

---

## Q2. `C1h`／`C1r`／`C1b`／`C1o` 預設種子矩陣？

> 需 11 個 canonical role × 4 個新 story = 44 列。本輪只使用 `edit` action。

A. **全 44 列都寫入種子**；僅 ADR 指定角色 `can_edit=true`，其餘角色三旗標皆 false（`can_view` 不另開；執行期 `user_can` 仍把 edit 當成可 view）。**（建議）**  
B. **只插入有 edit=true 的列**（約 5 列）。代價：Admin 矩陣缺列、其他 role 查不到 story。  
C. Not yet defined  
X. Other (please specify)

[Answer]: A. **全 44 列都寫入種子**；僅 ADR 指定角色 `can_edit=true`，其餘三旗標 false。**（建議）**

---

## Q3. 金額與時數欄位型別？

> 需對齊 calculator 兩位 USD 與 PBT；Postgres 為主、SQLite 測試需可建表。

A. **金額 `NUMERIC(12,2)`**（`monthly_budget`、`hourly_override`、`pricing_cache.hourly`）；**時數 `INTEGER NOT NULL DEFAULT 24`**；字串欄用 `VARCHAR`。**（建議）**  
B. **金額 `DOUBLE PRECISION`**。代價：與 Decimal／PBT 不一致。  
C. Not yet defined  
X. Other (please specify)

[Answer]: A. **金額 `NUMERIC(12,2)`**；**時數 `INTEGER NOT NULL DEFAULT 24`**。**（建議）**

---

## Q4. 既有 DB 升級與 ensure 順序？

> brownfield 靠 `database._ensure_*()`；新環境靠 `schema_rbac.sql`。

A. **`schema_rbac.sql` 新增四表 DDL + 44 列 C1* 種子（連同既有 C1 列一併在 INSERT 區）**；`database.py` 加 `_ensure_cost_schema()`（`CREATE TABLE IF NOT EXISTS` + 索引）；`init_db()` 在 **`ensure_role_permissions_seeded` 之後**呼叫 `ensure_missing_role_permissions()`。**（建議）**  
B. **只靠 `create_all()` 新 ORM**。代價：staging 不跑 migrate 就缺表。  
C. Not yet defined  
X. Other (please specify)

[Answer]: A. **`schema_rbac.sql` + `_ensure_cost_schema()` + seed 後 `ensure_missing_role_permissions()`**。**（建議）**

---

## Plan Approval

- [x] 計畫已核可（延續前序 stage 節奏；Q1–Q4=A）
