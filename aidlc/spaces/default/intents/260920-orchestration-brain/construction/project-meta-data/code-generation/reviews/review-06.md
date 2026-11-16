## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-01 | Fixed | Minor | verify_meta_schema.sql 已有 P17，斷言 system_requirement_fields 欄位集合恰為 9 欄，檔頭註明共 17 條，ci.yml 的步驟註解也同步為 P1-P17。與 P1／P5 對稱。 |
| R-02 | Fixed | Minor | run_meta_schema_migration.py 的 EXPECTED_FK_DELETE_ACTIONS 現有 7 條，以欄名為鍵（user_id 與 invited_by 不再混淆）。原先的 8 條裡 updated_on_behalf_of 的外鍵已被 U20 移除，其缺席由 COLUMNS_WITHOUT_FK 與 P16 承擔，不再是缺口。 |
| R-07 | Fixed | Minor | verify_meta_schema.sql 第 101 行已寫恰為 9 欄（原為 8 欄）。ci.yml 的 P1-P17 敘述與歸屬正確（P1–P12 為 U18，P13／P14 為 U19，P15／P16 為 U20，P17 為第 30 列）。我 grep 過，已無舊的 P1-P16 或 12 條敘述。 |
| R-09 | Fixed | Minor | DEPLOY.md 以 grep 查詢，只剩第 857-860 行的 P1–P17，沒有 P1–P12 字樣，原先 :801 的殘留已消失。 |
| R-10 | Still applies | Minor | traceability.json 中 OPEN-P5 只出現在三則 note 或 text 內（約第 289、323、353 行），沒有獨立的 open_items 條目。code-summary 第八節仍寫「完整清單見 traceability.json 的 open_items」，與事實不符。屬紀錄層缺口，不影響 DDL 與閘門。 |
| R-11 | Still applies | Minor | code-summary 的 Step 7 判定句（約第 317 行）仍只寫 (c) 以 (c-2) 的形式勾選，沒有明說計畫字面閘門條件已被取代，也沒有指出 P15／P16 在 CI 真正會轉紅的路徑是 ci.yml 的 U20 步驟 A 降回舊定義、步驟 B 收斂、再次 verify。不影響 Step 7 的結論。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|

### Validation Tool Results

| 驗證 | 結果 | 解讀 |
|---|---|---|
| shasum -a 256 對 reviewed-source-73848765bae2.tsv 五列獨立重算（以 awk -F tab 取欄位） | 5 同、0 變（ci.yml、DEPLOY.md、run_meta_schema_migration.py、verify_meta_schema.sql、schema_rbac.sql） | 與 conductor 的重算一致。單元目錄下另有同為 11-08 14:23 的 reviewed-source-3a03dce7924a.tsv，其雜湊與現況不符，屬較舊的快照，以 73848765bae2 為準。未見更晚的收據。 |
| git diff HEAD 對 code-generation-plan.md | 零差異 | 勾選回復與 HEAD 版逐字相同。 |
| 計畫勾選 grep -c | 21 勾、0 未勾 | 無未勾格，因此不存在「理由過時而可勾」的項目。 |
| git diff HEAD 對 code-summary.md | 僅檔尾追加「整站重跑後的勾選回復」一節 6 行 | 該節三項陳述（5 同 0 變、21／0、無程式改動）皆與我的重算相符，屬實。 |
| git status 與 git log 對 backend/scripts、DEPLOY.md、.github | 本單元五個來源檔無工作樹變動；最近一次碰到它們的是 ff537a7 之前的已審查提交 | commit 33deb2e 只動 ci-jobs-golden.json、aidlc-sync-selftest.yml 與 test_work_orchestrator_authz.py，未碰本單元的修正段落。 |
| 測試、python、CI 重跑 | 依限制未執行 | 以讀碼推演。CI run 42454550208 除已知的 C3（membership-service）外全綠，不重複報告。 |

### Summary

本單元自上次 READY 審查後沒有程式改動：五個來源檔雜湊全數吻合，計畫勾選與 HEAD 逐字相同（21 勾、0 未勾），code-summary 新節屬實。R-01、R-02、R-07、R-09 已修好，R-10、R-11 仍是兩項不阻擋的紀錄層 Minor，沒有新發現，因此判 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | `backend/scripts/verify_meta_schema.sql` — group C (`system_requirement_fields`) assertions `P9`–`P12` | `P1` asserts `project_members` has *exactly* 6 columns and `P5` asserts `reselection_events` has *exactly* 8, each with an explicit "多一欄或少一欄皆紅" rationale in `unit-test-instructions.md`. No equivalent exact-column-count assertion exists for `system_requirement_fields` (9 columns per `components.md:820` and the actual DDL). `P9`–`P12` check specific nullability/CHECK/UNIQUE/COMMENT facts but never the column *set*, so an accidentally added extra column on this table (e.g. a stray sensitive field) would pass all 12 assertions silently — breaking the symmetry the unit's own test design explicitly claims to have established for the other two tables. | Add a 13th assertion (or extend `P9`) asserting `system_requirement_fields` has exactly 9 columns, mirroring `P1`/`P5`, or explicitly document in `unit-test-instructions.md` why group C is exempt from the pattern. | Unresolved |
| R-02 | Minor | `backend/scripts/run_meta_schema_migration.py` `EXPECTED_FK_DELETE_ACTIONS` (3 entries) vs. actual DDL (8 FKs in the `J)` block) | The migration script's post-condition check only verifies `ON DELETE` behaviour for 3 of the 8 foreign keys it creates (`project_members.project_id`, `project_members.user_id`, `system_requirement_fields.system_id`). The other 5 (`invited_by`, `promoted_user_id`, `previous_owner_user_id`, `updated_by`, `updated_on_behalf_of`) are covered only by the generic `pg_constraint` existence check inside `EXPECTED_CONSTRAINTS`/table-exists checks, not by name, so a future edit that silently changes one of their `ON DELETE` clauses (e.g. accidentally adding `CASCADE` to `updated_by`, which would let a user-deletion silently erase who cleared a requirement field) would not fail the migration script's self-check. Low risk given today's `ON DELETE` values are all the PostgreSQL default, but worth a conscious decision rather than an implicit one. | Either add the remaining 5 FKs to `EXPECTED_FK_DELETE_ACTIONS` (expected `'a'`) or note in the script's docstring that only semantically load-bearing `ON DELETE` clauses are checked. | Unresolved |
| R-03 | Minor | DEPLOY.md > 2.2.9 開頭段落與 :251 表格 J 列 | 兩處仍寫「三張表皆為全新、無資料遷移」，但 U20 之後 `J)` 區塊含一段條件式 DO（`updated_on_behalf_of` 由 integer 轉 varchar(64)，會重寫該欄，`schema_rbac.sql` 註解稱 OPEN-RF20-8，不再是純 DDL）。同檔 :829 已如實寫明這點，前後敘述不一致，只讀開頭的人會以為重跑遷移腳本沒有任何資料副作用。 | 在 2.2.9 開頭段與 :251 表格列各補半句：「U20 起含一段條件式欄位收斂，見本節 U20 小節」。非 blocking，可在下一次動 DEPLOY.md 時帶上。 | Resolved (reviewer) |
| R-04 | Minor | .github/workflows/ci.yml:389 步驟名稱「(P1-P12)」 | 腳本實際已有 P15／P16（`verify_meta_schema.sql:276-321`，結尾 NOTICE 也列到 P16），步驟名稱與 code-summary 的「P1–P12」說法都落後。DEPLOY.md :794 已承認「名稱比內容窄」，但仍未更正。 | 步驟名稱改為「(P1-P16)」或不列範圍；code-summary 末節同步。 | Resolved (reviewer) |
| R-05 | Minor | code-summary.md > 重新查驗表「本輪未驗」 | 如實標明 `verify_meta_schema.sql` 未重跑，風險判斷正確。補充我的查驗：a5200fc 之後 `J)` 區塊的改動有 U20（欄位型別收斂，驗證腳本已同步加 P15／P16、P5 改為 9 欄）、U23（新增 `ix_project_members_user_id`，遷移腳本 `EXPECTED_INDEXES` 已同步）、以及工作樹中 `hierarchy-data` 對 `projects.owner_user_id`／`project_members.user_id` 的 COMMENT 修改。驗證腳本對 COMMENT 內容只斷言 `system_requirement_fields` 表 COMMENT（P12 的關鍵詞），上述 COMMENT 改動不在其中，故不會破壞斷言；`COMMENT ON` 與 `CREATE INDEX IF NOT EXISTS` 皆可重跑。未驗風險低，但仍是推送後 CI 才能關閉的未驗項。 | 推送後確認 `memory-schema` job 為綠，並把結果回填 code-summary；不需本輪修改。 | Resolved (reviewer) |
| R-06 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-meta-data/code-generation/code-generation-plan.md > Step 7（未勾）；code-summary.md > §七 與「重做」節 | Step 7（突變驗證）未勾，與專案強制規則（每支腳本都要突變驗證）衝突。§七 的 N1–N10 對應的是 P1–P12 的舊版本。其後新增的 `cause` 欄與 `ck_reselection_events_cause`（P13／P14）、U20 的 varchar 轉型與條件式 DO 區塊（P15／P16）、`ix_project_members_user_id` 都沒有任何一條本單元認列的突變紀錄。另外 P5 已從 8 欄改成 9 欄，N9（移除 `promoted_user_id`）的判讀基準也變了。這幾條斷言「是否真會變紅」目前沒有證據。 | 補跑並記錄至少三項突變：拿掉 `ck_reselection_events_cause`、把 `updated_on_behalf_of` 改回 integer 並加外鍵、移除 `cause` 欄，確認 P13／P14／P15／P16 各自變紅後還原；勾選 Step 7。若決定留給下游階段，須在計畫中明文改派並說明承接站。 | Resolved (reviewer) |
| R-07 | Minor | backend/scripts/verify_meta_schema.sql:99；.github/workflows/ci.yml:328、:383 | 殘留過時敘述：`:99` 註解仍寫「恰為 8 欄」，下一行實際斷言 9 欄；`ci.yml:328` 寫「12 條斷言（P1-P16）」；`ci.yml:383` 說 P13–P16 由 U20 加入，但 `verify_meta_schema.sql:2-4` 寫 P13／P14 是 U19、P15／P16 才是 U20。code-summary 已自承這些但未改。 | 順手改成 9 欄、16 條，並更正 P13／P14 屬 U19；純註解，可與其他單元的清理合併。 | Unresolved |
| R-08 | Minor | code-summary.md > 與已核可計畫／測試說明的落差；unit-test-instructions.md | `unit-test-instructions.md` 仍只列 P1–P12 且寫 P5 為「恰為 8 欄」，與實際 16 條、9 欄不符。這份文件是 tcms 與後續單元查驗 U18 的主要依據，凍結不改只靠 code-summary 一節補丁，讀者容易只看前者。 | 在 `unit-test-instructions.md` 檔頭加一行指向 code-summary 的更正節，或直接更新條數與欄數；不影響 DDL。 | Resolved (reviewer) |
| R-09 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-meta-data/code-generation/code-summary.md > 四、R-07（OPEN-CG18-14）與 重做節「DEPLOY.md:795」 | 漏記一處過時敘述。DEPLOY.md:801 仍寫「本節的 P1–P12」，而同段 :797-798 已寫 16 條（P1–P16）。2026-10-25 的「重做」節把這個殘留記在 DEPLOY.md:795，但 #24 在 730–738 行多加 6 行後，它已移到 :801；本輪新的 OPEN-CG18-14 只列了 verify_meta_schema.sql 與 ci.yml，沒有帶上 DEPLOY.md。這一處落在 U18 自己的 §2.2.9。 | 在 OPEN-CG18-14 補上 DEPLOY.md:801，並註明原 :795 因 #24 位移而更正。下游若修 DEPLOY.md，順手改成 P1–P16。 | New |
| R-10 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-meta-data/code-generation/traceability.json > open_items；code-summary.md > 八、未解事項 | code-summary 的未解事項表寫「完整清單見 traceability.json 的 open_items」，但 OPEN-P1、OPEN-P2、OPEN-P4、OPEN-P5、OPEN-ND18-3、OQ-H1 在 traceability 中沒有條目（共 15 筆，只有 OPEN-CG18-* 與 R06）。OPEN-P5 的代價在本輪被 #24 改變（失敗由立即報錯變成靜默缺 COMMENT／缺 U20 收斂）。code-summary 第一節已如實揭露「更重」，但 traceability 沒有任何條目承載，下游若只讀 traceability 會看不到。 | 在 traceability.json 補一筆 OPEN-P5（或在 open_items 加一筆指向 DEPLOY.md:730-738 現行敘述的條目），或把 code-summary 的措辭改為「carried 項目只見於本表」。 | New |
| R-11 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-meta-data/code-generation/code-generation-plan.md > §八 R-06 項 ＋ code-summary.md > 三、判定 | 計畫 §八 自己寫「若 (a)–(c) 中任一項未致紅，不勾 Step 7」。(c) 按計畫字面（改檔案副本）是 no-op，實際勾選依據是替代的 (c-2)（對已套用資料庫做 ALTER）。這是合理的，也已誠實揭露，但判定句沒有明說「已偏離計畫的字面閘門條件」。另外，檔案層回退既然會被 DO 區塊自癒，P15／P16 在 CI 真正能轉紅的路徑只有 ci.yml 的 U20 步驟 A（降回舊定義）→ B → :447 的第二次 verify。code-summary 沒有把這點與 (c-1) 連起來寫。 | 在 code-summary「判定」補一句：計畫字面閘門被 (c-2) 取代，並指出 P15／P16 的實際轉紅路徑是 ci.yml 的 U20 步驟 A/B 之後的 verify（約 :447）。不影響 Step 7 的勾選結論。 | New |

> R-01 Not re-checked this round

> R-02 Not re-checked this round

> R-07 Not re-checked this round

> R-09 Not re-checked this round

> R-10 Not re-checked this round

> R-11 Not re-checked this round
