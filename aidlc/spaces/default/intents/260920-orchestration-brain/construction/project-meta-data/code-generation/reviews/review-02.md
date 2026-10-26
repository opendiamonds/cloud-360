## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-20T23:07:35Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | `backend/scripts/verify_meta_schema.sql` — group C (`system_requirement_fields`) assertions `P9`–`P12` | `P1` asserts `project_members` has *exactly* 6 columns and `P5` asserts `reselection_events` has *exactly* 8, each with an explicit "多一欄或少一欄皆紅" rationale in `unit-test-instructions.md`. No equivalent exact-column-count assertion exists for `system_requirement_fields` (9 columns per `components.md:820` and the actual DDL). `P9`–`P12` check specific nullability/CHECK/UNIQUE/COMMENT facts but never the column *set*, so an accidentally added extra column on this table (e.g. a stray sensitive field) would pass all 12 assertions silently — breaking the symmetry the unit's own test design explicitly claims to have established for the other two tables. | Add a 13th assertion (or extend `P9`) asserting `system_requirement_fields` has exactly 9 columns, mirroring `P1`/`P5`, or explicitly document in `unit-test-instructions.md` why group C is exempt from the pattern. | New |
| R-02 | Minor | `backend/scripts/run_meta_schema_migration.py` `EXPECTED_FK_DELETE_ACTIONS` (3 entries) vs. actual DDL (8 FKs in the `J)` block) | The migration script's post-condition check only verifies `ON DELETE` behaviour for 3 of the 8 foreign keys it creates (`project_members.project_id`, `project_members.user_id`, `system_requirement_fields.system_id`). The other 5 (`invited_by`, `promoted_user_id`, `previous_owner_user_id`, `updated_by`, `updated_on_behalf_of`) are covered only by the generic `pg_constraint` existence check inside `EXPECTED_CONSTRAINTS`/table-exists checks, not by name, so a future edit that silently changes one of their `ON DELETE` clauses (e.g. accidentally adding `CASCADE` to `updated_by`, which would let a user-deletion silently erase who cleared a requirement field) would not fail the migration script's self-check. Low risk given today's `ON DELETE` values are all the PostgreSQL default, but worth a conscious decision rather than an implicit one. | Either add the remaining 5 FKs to `EXPECTED_FK_DELETE_ACTIONS` (expected `'a'`) or note in the script's docstring that only semantically load-bearing `ON DELETE` clauses are checked. | New |
| R-03 | Minor | DEPLOY.md > 2.2.9 開頭段落與 :251 表格 J 列 | 兩處仍寫「三張表皆為全新、無資料遷移」，但 U20 之後 `J)` 區塊含一段條件式 DO（`updated_on_behalf_of` 由 integer 轉 varchar(64)，會重寫該欄，`schema_rbac.sql` 註解稱 OPEN-RF20-8，不再是純 DDL）。同檔 :829 已如實寫明這點，前後敘述不一致，只讀開頭的人會以為重跑遷移腳本沒有任何資料副作用。 | 在 2.2.9 開頭段與 :251 表格列各補半句：「U20 起含一段條件式欄位收斂，見本節 U20 小節」。非 blocking，可在下一次動 DEPLOY.md 時帶上。 | New |
| R-04 | Minor | .github/workflows/ci.yml:389 步驟名稱「(P1-P12)」 | 腳本實際已有 P15／P16（`verify_meta_schema.sql:276-321`，結尾 NOTICE 也列到 P16），步驟名稱與 code-summary 的「P1–P12」說法都落後。DEPLOY.md :794 已承認「名稱比內容窄」，但仍未更正。 | 步驟名稱改為「(P1-P16)」或不列範圍；code-summary 末節同步。 | New |
| R-05 | Minor | code-summary.md > 重新查驗表「本輪未驗」 | 如實標明 `verify_meta_schema.sql` 未重跑，風險判斷正確。補充我的查驗：a5200fc 之後 `J)` 區塊的改動有 U20（欄位型別收斂，驗證腳本已同步加 P15／P16、P5 改為 9 欄）、U23（新增 `ix_project_members_user_id`，遷移腳本 `EXPECTED_INDEXES` 已同步）、以及工作樹中 `hierarchy-data` 對 `projects.owner_user_id`／`project_members.user_id` 的 COMMENT 修改。驗證腳本對 COMMENT 內容只斷言 `system_requirement_fields` 表 COMMENT（P12 的關鍵詞），上述 COMMENT 改動不在其中，故不會破壞斷言；`COMMENT ON` 與 `CREATE INDEX IF NOT EXISTS` 皆可重跑。未驗風險低，但仍是推送後 CI 才能關閉的未驗項。 | 推送後確認 `memory-schema` job 為綠，並把結果回填 code-summary；不需本輪修改。 | New |

> R-01 Not re-checked this round

> R-02 Not re-checked this round

### 重點查證結論

- (a) 19 項合併前必修無一應落在本單元，成立。#15（回填 `project_members` 的部署順序）：回填由 U19 的 `backfill_project_members.py` 承載，DEPLOY.md 2.2.10 已把它排在遷移腳本之後並列出順序表；本單元的 `run_meta_schema_migration.py` 只負責建表與索引，不應夾帶資料回填，否則 U18「無資料寫入」的契約（K-15）會被破壞。#11（系統 actor）屬 K) 區塊的 U9 seed 與使用者刪除路徑，不在本單元的三張表。#1／#4／#10 是 membership-service 的應用層邏輯；我檢視 `reselection_events` 現有欄位（含 U19 補的 `cause`、9 欄）與 `ix_reselection_events_unack`，沒看到這三項需要新增表結構。
- (b) 8 格勾選抽查成立：`schema_rbac.sql` 有 `J)` 區塊與檔頭涵蓋清單、`ci.yml:389-394` 於 `memory-schema` job 執行驗證腳本、DEPLOY.md :251 與 2.2.9 存在、遷移腳本 `EXPECTED_*` 與驗證腳本欄數（9）一致。
- (c)(d) 見第三列：改動與斷言不衝突，可重跑性維持。
- (e) ADR-0006：本輪未改應用程式碼，無新增的 IAM／網路面向；encryption 與 audit 面向（表 COMMENT 標明授權責任在 K-16、`reselection_events` 為稽核表且不設 90 天清除）沿用先前審查結論，未見退化。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 依指示未執行任何測試或建置命令 | N/A | 全部以讀檔與 git diff 查證；`verify_meta_schema.sql` 的實跑仍需推送後的 CI。 |

### Summary

本單元本輪無需修改，「19 項皆不屬本單元」的判定站得住腳；剩下的是文件措辭落後（DEPLOY.md 的「無資料遷移」、CI 步驟名稱的 P 範圍）與一個需靠推送後 CI 關閉的未驗項，均為 Minor。
