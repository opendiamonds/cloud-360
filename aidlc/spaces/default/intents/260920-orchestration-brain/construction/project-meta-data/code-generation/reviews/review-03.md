## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-25
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | `backend/scripts/verify_meta_schema.sql` — group C (`system_requirement_fields`) assertions `P9`–`P12` | `P1` asserts `project_members` has *exactly* 6 columns and `P5` asserts `reselection_events` has *exactly* 8, each with an explicit "多一欄或少一欄皆紅" rationale in `unit-test-instructions.md`. No equivalent exact-column-count assertion exists for `system_requirement_fields` (9 columns per `components.md:820` and the actual DDL). `P9`–`P12` check specific nullability/CHECK/UNIQUE/COMMENT facts but never the column *set*, so an accidentally added extra column on this table (e.g. a stray sensitive field) would pass all 12 assertions silently — breaking the symmetry the unit's own test design explicitly claims to have established for the other two tables. | Add a 13th assertion (or extend `P9`) asserting `system_requirement_fields` has exactly 9 columns, mirroring `P1`/`P5`, or explicitly document in `unit-test-instructions.md` why group C is exempt from the pattern. | Unresolved |
| R-02 | Minor | `backend/scripts/run_meta_schema_migration.py` `EXPECTED_FK_DELETE_ACTIONS` (3 entries) vs. actual DDL (8 FKs in the `J)` block) | The migration script's post-condition check only verifies `ON DELETE` behaviour for 3 of the 8 foreign keys it creates (`project_members.project_id`, `project_members.user_id`, `system_requirement_fields.system_id`). The other 5 (`invited_by`, `promoted_user_id`, `previous_owner_user_id`, `updated_by`, `updated_on_behalf_of`) are covered only by the generic `pg_constraint` existence check inside `EXPECTED_CONSTRAINTS`/table-exists checks, not by name, so a future edit that silently changes one of their `ON DELETE` clauses (e.g. accidentally adding `CASCADE` to `updated_by`, which would let a user-deletion silently erase who cleared a requirement field) would not fail the migration script's self-check. Low risk given today's `ON DELETE` values are all the PostgreSQL default, but worth a conscious decision rather than an implicit one. | Either add the remaining 5 FKs to `EXPECTED_FK_DELETE_ACTIONS` (expected `'a'`) or note in the script's docstring that only semantically load-bearing `ON DELETE` clauses are checked. | Unresolved |
| R-03 | Minor | DEPLOY.md > 2.2.9 開頭段落與 :251 表格 J 列 | 兩處仍寫「三張表皆為全新、無資料遷移」，但 U20 之後 `J)` 區塊含一段條件式 DO（`updated_on_behalf_of` 由 integer 轉 varchar(64)，會重寫該欄，`schema_rbac.sql` 註解稱 OPEN-RF20-8，不再是純 DDL）。同檔 :829 已如實寫明這點，前後敘述不一致，只讀開頭的人會以為重跑遷移腳本沒有任何資料副作用。 | 在 2.2.9 開頭段與 :251 表格列各補半句：「U20 起含一段條件式欄位收斂，見本節 U20 小節」。非 blocking，可在下一次動 DEPLOY.md 時帶上。 | Resolved (reviewer) |
| R-04 | Minor | .github/workflows/ci.yml:389 步驟名稱「(P1-P12)」 | 腳本實際已有 P15／P16（`verify_meta_schema.sql:276-321`，結尾 NOTICE 也列到 P16），步驟名稱與 code-summary 的「P1–P12」說法都落後。DEPLOY.md :794 已承認「名稱比內容窄」，但仍未更正。 | 步驟名稱改為「(P1-P16)」或不列範圍；code-summary 末節同步。 | Resolved (reviewer) |
| R-05 | Minor | code-summary.md > 重新查驗表「本輪未驗」 | 如實標明 `verify_meta_schema.sql` 未重跑，風險判斷正確。補充我的查驗：a5200fc 之後 `J)` 區塊的改動有 U20（欄位型別收斂，驗證腳本已同步加 P15／P16、P5 改為 9 欄）、U23（新增 `ix_project_members_user_id`，遷移腳本 `EXPECTED_INDEXES` 已同步）、以及工作樹中 `hierarchy-data` 對 `projects.owner_user_id`／`project_members.user_id` 的 COMMENT 修改。驗證腳本對 COMMENT 內容只斷言 `system_requirement_fields` 表 COMMENT（P12 的關鍵詞），上述 COMMENT 改動不在其中，故不會破壞斷言；`COMMENT ON` 與 `CREATE INDEX IF NOT EXISTS` 皆可重跑。未驗風險低，但仍是推送後 CI 才能關閉的未驗項。 | 推送後確認 `memory-schema` job 為綠，並把結果回填 code-summary；不需本輪修改。 | Resolved (reviewer) |
| R-06 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-meta-data/code-generation/code-generation-plan.md > Step 7（未勾）；code-summary.md > §七 與「重做」節 | Step 7（突變驗證）未勾，與專案強制規則（每支腳本都要突變驗證）衝突。§七 的 N1–N10 對應的是 P1–P12 的舊版本。其後新增的 `cause` 欄與 `ck_reselection_events_cause`（P13／P14）、U20 的 varchar 轉型與條件式 DO 區塊（P15／P16）、`ix_project_members_user_id` 都沒有任何一條本單元認列的突變紀錄。另外 P5 已從 8 欄改成 9 欄，N9（移除 `promoted_user_id`）的判讀基準也變了。這幾條斷言「是否真會變紅」目前沒有證據。 | 補跑並記錄至少三項突變：拿掉 `ck_reselection_events_cause`、把 `updated_on_behalf_of` 改回 integer 並加外鍵、移除 `cause` 欄，確認 P13／P14／P15／P16 各自變紅後還原；勾選 Step 7。若決定留給下游階段，須在計畫中明文改派並說明承接站。 | New |
| R-07 | Minor | backend/scripts/verify_meta_schema.sql:99；.github/workflows/ci.yml:328、:383 | 殘留過時敘述：`:99` 註解仍寫「恰為 8 欄」，下一行實際斷言 9 欄；`ci.yml:328` 寫「12 條斷言（P1-P16）」；`ci.yml:383` 說 P13–P16 由 U20 加入，但 `verify_meta_schema.sql:2-4` 寫 P13／P14 是 U19、P15／P16 才是 U20。code-summary 已自承這些但未改。 | 順手改成 9 欄、16 條，並更正 P13／P14 屬 U19；純註解，可與其他單元的清理合併。 | New |
| R-08 | Minor | code-summary.md > 與已核可計畫／測試說明的落差；unit-test-instructions.md | `unit-test-instructions.md` 仍只列 P1–P12 且寫 P5 為「恰為 8 欄」，與實際 16 條、9 欄不符。這份文件是 tcms 與後續單元查驗 U18 的主要依據，凍結不改只靠 code-summary 一節補丁，讀者容易只看前者。 | 在 `unit-test-instructions.md` 檔頭加一行指向 code-summary 的更正節，或直接更新條數與欄數；不影響 DDL。 | New |

> R-01 Reviewer note: `verify_meta_schema.sql` 的 `P9`（:224-245）、`P12`（:247-274）仍只驗 nullability 與 COMMENT 關鍵詞，沒有 `system_requirement_fields` 欄位數（9）的斷言；`P1`／`P5` 對另兩張表則有恰好欄數檢查。多一個欄位不會被任何斷言抓到。

> R-02 Reviewer note: `run_meta_schema_migration.py:195-199` 的 `EXPECTED_FK_DELETE_ACTIONS` 仍只有 3 條。U20 新增的 `EXPECTED_COLUMN_FKS` 只驗 `updated_by` 的外鍵「存在」，不驗 `ON DELETE`；`invited_by`、`promoted_user_id`、`previous_owner_user_id` 三條的刪除行為仍無自檢。

> R-03 Reviewer note: `DEPLOY.md:251` 已補「唯一例外是 U20 起的條件式欄位轉型…」，`:829` 與之一致。

> R-04 Reviewer note: `ci.yml:388` 步驟名稱已是「(P1-P16)」，`:329`、`:383`、`:406` 同步。`ci.yml:328` 的「12 條斷言」與 `:383` 的歸屬敘述仍有殘留，見新發現。

> R-05 Reviewer note: 本輪在一次性 PostgreSQL 17.7 上實跑 `verify_meta_schema.sql`，P1–P16 全部通過，並走完 U20 降級再遷移再驗證。仍是 pg17，CI 用 pg18，兩者差異已記為 `OPEN-CG18-5`；此項不再是「完全未驗」。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 讀取 `schema_rbac.sql` J) 區塊（:567-808 一帶） | 結構與契約相符 | `project_members` 的 `project_id` 為 CASCADE、`user_id` 無 ON DELETE（NO ACTION）、`uq_project_members_project_user`；`reselection_events` 對 `projects` 無外鍵（[ND1]=A 保留）；`system_requirement_fields` 三態 CHECK 與三欄唯一鍵完好。U19／U20／U23 的後續改動沒有破壞 U18 契約。 |
| 查 `origin/ut:schema_rbac.sql` 中 `reselection_events` 命中數 | 0 | 三張表尚未進入任何已部署環境，`CREATE TABLE IF NOT EXISTS` 內直接加 `cause NOT NULL` 不會留下「舊表缺欄」的升級缺口（`schema_rbac.sql:648` 註解亦已說明）。 |
| 單一交易遷移腳本 | 靜態檢視 | `BLOCKS_TO_RUN = ("X","I","J")`，後條件檢查含 3 條 FK 刪除行為、禁止外鍵、欄位型別與外鍵存在性；與 summary 實跑記錄一致。未執行（依指示不啟動資料庫）。 |

### Summary

U18 的資料基礎在 U19／U20／U23 改動後仍成立，沒有 Critical，三張表的外鍵、三態 CHECK、唯一鍵與單交易遷移契約都在。主要缺口是 Step 7 突變驗證未補，使後來加入的 P13–P16 缺少會紅燈的證據（1 Major）；另有 3 項舊 Minor 仍在（R-01、R-02 持續，R-03、R-04、R-05 已修）、2 項新 Minor 為文件與註解殘留。
