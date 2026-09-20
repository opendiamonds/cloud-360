# Business Rules — cost-schema-rbac

> Unit: `cost-schema-rbac` · Q1–Q4=A  
> 上游：`unit-of-work.md`、`unit-of-work-story-map.md`、`requirements.md`、`components.md`、`decisions.md`、`team-practices.md`。

## 不變量

| ID | 規則 | 違反 |
|---|---|---|
| BR-S-1 | 四表名稱與欄位以 `domain-entities.md` 為準；變更須同步三件套 | CI contract／staging 缺表 |
| BR-S-2 | `ensure_missing_role_permissions()` **只 INSERT** 缺失 `(role, story_id)`；`updated_by='system_seed'`；不 UPDATE／DELETE | Admin 矩陣被覆寫；ADR-C1-02 |
| BR-S-3 | `init_db()` 順序：`ensure_role_permissions_seeded(force=False)` → **`ensure_missing_role_permissions()`** → 其他補丁 | staging 永遠缺 C1h 等列 |
| BR-S-4 | `C1h`／`C1r`／`C1b`／`C1o` 種子：**11×4=44 列**全寫；僅 ADR 矩陣的 `can_edit=true` | Admin 矩陣缺列；403 測試假陽性 |
| BR-S-5 | 金額欄 `NUMERIC(12,2)`；時數 `INTEGER DEFAULT 24` | 與 ADR-C1-07／calculator 不一致 |
| BR-S-6 | `user_diagrams` 刪除 cascade 三張從屬表 | 孤兒列、FR-1.5 對齊失敗 |
| BR-S-7 | `pricing_cache` UK `(cloud, sku, region)`；TTL 語意 24h（判斷在 service，欄位只存 `fetched_at`） | 重複快取列或無限外網 |
| BR-S-8 | `cost_audit_event.field` 僅允許 `hourly_override`｜`sku_override`｜`monthly_budget` | 稽核 GET 契約漂移 |
| BR-S-9 | 時數／區域變更**不** insert 稽核列 | ADR-C1-06 |

## 種子矩陣（44 列，`can_edit=true` 僅下列）

**11 個 canonical role**（與 `rbac.py` `CANONICAL_ROLES` 一致）：`Project_Architect`、`Developer`、`Project_Editor`、`Project_Admin`、`FinOps_Analyst`、`SRE`、`Ops_Lead`、`Platform_Engineer`、`Security_Reviewer`、`Platform_Admin`、`Platform_Owner`。真實來源：`services/rbac_seed_data.py` 的 `DEFAULT_ROLE_PERMISSIONS` 增量。

| story_id | role | can_view | can_edit | can_review |
|---|---|---|---|---|
| `C1h` | `Project_Architect` | false | **true** | false |
| `C1r` | `Project_Architect` | false | **true** | false |
| `C1b` | `FinOps_Analyst` | false | **true** | false |
| `C1b` | `Project_Editor` | false | **true** | false |
| `C1o` | `FinOps_Analyst` | false | **true** | false |
| *其餘 39 列* | 各 role × 各 story | false | false | false |

`C1` 既有 11 列維持 `schema_rbac.sql`／`rbac_seed_data.py` 現值（含 FinOps 對 `C1` 的 `can_edit=true` 歷史種子——**不在本 unit 改寫**）。

## `ensure_missing_role_permissions()` 算法

```
for (role, story_id, can_view, can_edit, can_review) in DEFAULT_ROLE_PERMISSIONS:
  if not exists(role, story_id):
    INSERT with updated_by='system_seed'
return inserted_count
```

- **禁止**在 `(role, story_id)` 已存在時改旗標（即使與 DEFAULT 不同）。
- **禁止** delete 後全量重插（那是 `force=True` 路徑，Admin 會痛）。
- 回傳插入列數；`0` 在 staging 已補齊時為正常。
- 記錄 INFO：`ensure_missing_role_permissions: inserted N rows`。

## 部署三件套（blocking）

| 產物 | 內容 |
|---|---|
| `schema_rbac.sql` | `CREATE TABLE IF NOT EXISTS` 四表 + 索引 + COMMENT；`role_permissions` INSERT 區加入 44 列 C1*（新環境一次到位） |
| `DEPLOY.md` | 新表說明、既有環境「重跑 sql 會重播 role_permissions DELETE」警告、建議靠 `_ensure_cost_schema()` + 啟動補種子 |
| `database.py` | `_ensure_cost_schema()` 在 `init_db()` 早段（`create_all` 後）；`ensure_missing` 在 seed 後 |

brownfield **不得**要求重跑整份 `schema_rbac.sql` 才長表——與 J5／A3 先例一致。

## 驗證（Construction 測試掛點）

對齊 `team-practices` 規則 A／B 與 B1 DoD：

- Migration 後四表存在、UK／FK 可查（ `\d diagram_cost_line` 或 ORM metadata）
- 空表 CI：`ensure_role_permissions_seeded(force=True)` 後 `STORY_IDS` 含 `C1h`～`C1o`
- **Brownfield 模擬**：預填 `role_permissions`（僅舊 story）→ 只跑 `ensure_missing` → 新 story 列出現、舊列旗標不變
- `diagram_cost_line.hours` DEFAULT 24：insert 只給 PK 時 hours=24
- 刪 `user_diagrams` 一列 → 三從屬表無孤兒

## 錯誤政策

- DDL 補丁失敗：`logger.warning` 不阻斷整個 `init_db`（沿用 `_ensure_a3_schema` 模式），但 **B1 DoD 測試必須 assert 表存在**——silent fail 由測試攔截。
- `ensure_missing` 失敗：`rollback` + `logger.error`；下次啟動重試。

## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-20T01:37:37Z
**Iteration:** 1

### Findings

| # | Severity | Location | Finding | Recommendation |
|---|---|---|---|---|
| 1 | Minor | `domain-entities.md` CostAuditEvent | `mxcell_id` 欄位在實體中對 `hourly_override`／`sku_override` 為 NOT NULL（必填），但 `component-methods.md` GET `/diagrams/{id}/audit` 回應形狀 `{ items: [{ at, actor, diagram_id, field, old_value, new_value }] }` 未含此欄。`domain-entities.md` 聲稱「對齊 GET audit 的 items[] 形狀」，卻存在此不一致：呼叫端從 API 回應無法得知哪個 cell 被修改（同一圖的兩筆 `hourly_override` 無法區分）。 | 在 `component-methods.md` GET audit 回應形狀中補上 `mxcell_id?`（nullable，預算類型為 null）；或在 `domain-entities.md` 顯式標注「`mxcell_id` 僅儲存，本輪不回應」並更新對齊聲明。兩者擇一，Construction 實作前需明確。 |
| 2 | Minor | `domain-entities.md` §關係圖 Mermaid | ER 圖含 `pricing_cache }o--|| pricing_cache : "standalone"` 自身循環邊，語意矛盾（`pricing_cache` 作為自身的 1-to-N 端）。文字 fallback 正確（「pricing_cache 無 FK」），但圖形可能誤導開發者，且在部分 Mermaid 渲染器中會產生非法輸出。 | 將該行改為僅宣告節點：`pricing_cache { cloud sku region }`，不添加任何關係邊，或直接移除該行並只保留文字 fallback。 |
| 3 | Minor | `business-rules.md` §種子矩陣 | 文件參照「11×4=44 列」但未列出 11 個 canonical role 名稱，也未明示以哪支現有檔案為 role 列表的真實來源（`rbac_seed_data.py` `DEFAULT_ROLE_PERMISSIONS`？`schema_rbac.sql` INSERT 區？）。開發者須自行查閱既有程式才能組出完整 44 列增量，隱含不可見的外部依賴。 | 在種子矩陣或 §`ensure_missing_role_permissions()` 演算法區塊補一句：「11 個 canonical role 以 `services/rbac_seed_data.py` `DEFAULT_ROLE_PERMISSIONS` 的既有 role 為準；Construction 在擴充前需先確認此列表」；或直接內嵌 role 清單。 |

### Validation Tool Results

| 工具 | 結果 | 說明 |
|---|---|---|
| ADR-C1-02 insert-only 語意比對 | PASS | BR-S-2 與 §演算法均明文「只 INSERT 缺失 `(role, story_id)`；`updated_by='system_seed'`；禁止 UPDATE／DELETE」；禁止 `force=False` no-op 路徑。與 ADR-C1-02 逐字一致。 |
| 四表名稱對齊 `components.md` | PASS | `diagram_cost`、`diagram_cost_line`、`pricing_cache`、`cost_audit_event` 四表，在 `components.md` §資料元件與 `domain-entities.md` §實體一覽中完全匹配；BR-S-1 標注「四表名稱與欄位以 `domain-entities.md` 為準」形成閉環。 |
| 稽核欄位對齊 GET audit 形狀 | PARTIAL（找到 Minor #1） | `id`、`diagram_id`、`field`、`old_value`、`new_value`、`actor_username→actor`、`created_at→at` 七欄均可映射至 `component-methods.md` 回應；惟 `mxcell_id` 存於 DB（必填）卻未出現在回應定義，形成文件層不一致（見 Finding #1）。 |
| 種子矩陣對齊 ADR-C1-02 角色 | PASS | `C1h`/Project_Architect、`C1r`/Project_Architect、`C1b`/FinOps_Analyst、`C1b`/Project_Editor、`C1o`/FinOps_Analyst 的 `can_edit=true` 與 ADR-C1-02「預設 edit：Architect=C1h+C1r；FinOps=C1o+C1b；Editor=C1b」完全吻合；其餘 39 列 false 一致。 |
| 部署三件套文件完整性 | PASS | `schema_rbac.sql`、`DEPLOY.md`、`database.py` 三件套均有明確說明（schema DDL + 44 列種子、brownfield 警告、`_ensure_cost_schema()` + `ensure_missing` 啟動序）。同步義務 blocking 標注存在。 |
| spec unit 無 HTTP／公式洩漏 | PASS | `domain-entities.md` §範圍明文「不含 HTTP、公式、頁面」；§不在本 unit 明列 OpenAPI 形狀、extractor 規則、Hypothesis、Playwright；business-rules.md 各規則均止於 DDL／種子／錯誤政策層，無 endpoint 定義或公式計算。 |
| 循環依賴掃描 | PASS | `cost-schema-rbac` 為 spec unit，僅被 `cost-api`、`cost-budget-banner` 消費；無反向依賴邊；`unit-of-work.md` 與 `component-dependency.md`（via decisions.md 引用）確認拓樸為有向無環圖。 |
| Mermaid 語法驗證 | FAIL（見 Finding #2） | ER 圖中 `pricing_cache }o--\|\| pricing_cache` 自身循環邊語義無效；文字 fallback 正確，不阻擋實作，但圖形需修正（Minor）。 |

### Summary

`cost-schema-rbac` functional design 結構清晰：四表定義完整、cascade 關係一致、`ensure_missing` insert-only 語意與 ADR-C1-02 逐字吻合、部署三件套有 blocking 標注、spec unit 邊界乾淨（無 HTTP／公式滲透）。三項 Minor 發現均不影響實作可行性：`mxcell_id` 回應一致性問題一行可解；Mermaid 自循環邊不影響 DB 設計；11 role 列表缺失可查現有 `rbac_seed_data.py`。開發者無需返回設計者澄清架構決策，Construction 可開始實作。
