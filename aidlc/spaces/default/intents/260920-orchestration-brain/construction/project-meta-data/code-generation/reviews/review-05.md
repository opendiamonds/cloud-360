## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-01 | Resolved | Minor | `backend/scripts/verify_meta_schema.sql:279-290` 已有 P17（`IF n <> 9`），訊息點名要同步 `EXPECTED_TABLES`。新測試 `test_p17_pins_system_requirement_fields_to_its_column_count` 對照 J) 區塊欄位數、`EXPECTED_TABLES`、P17 的 N，三者皆為 9。我在 scratchpad 副本重跑 `tests.test_meta_schema_expectations`：3 個測試全部 OK。 |
| R-02 | Resolved | Minor | `EXPECTED_FK_DELETE_ACTIONS` 已擴為 7 條、以欄名為鍵（`user_id` 與 `invited_by` 不再混淆）。`test_fk_expectations_equal_every_reference_in_j_block` 用 `extract_blocks` 解析 J) 區塊，斷言清單等於實際宣告的 7 條 REFERENCES（含 CASCADE 與否）。審查時的「8 條」是 U20 移除 `updated_on_behalf_of` 外鍵之前的數字，現行 7 條正確；該欄的缺席由 `COLUMNS_WITHOUT_FK` 與 P16 承擔。 |
| R-07 | Resolved | Minor | 我逐檔查證：`verify_meta_schema.sql:101` 已寫「恰為 9 欄（原為 8 欄…）」；`ci.yml` 的 :329、:404-405、:410 皆為 P1-P17 且歸屬（P1–P12 為 U18、P13／P14 為 U19、P15／P16 為 U20、P17 為第 30 列）正確；`DEPLOY.md:858-860` 為 P1–P17。本輪最後一處 `verify_meta_schema.sql:340` 已補入 P17。我自行比對該 DO 區塊內全部 `'P<n> FAILED` 編號（P1、P2、P3、P5、P6、P8、P9、P12、P13、P14、P15、P16、P17）與通過訊息清單，兩者相同；P4／P7 屬行為類區塊，不在此列。 |
| R-09 | Resolved | Minor | `DEPLOY.md` 內已無「P1–P12」「P1-P12」字樣（我以 `grep` 查 `P1[–-]P1[0-9]`：只剩 :858、:860 的 P1–P17）。原 :801 的過時敘述已由 brain-infra A5 更正。OPEN-CG18-14 現已以 `:340` 與測試行號結案，不再有遺漏的 DEPLOY.md 項。 |
| R-10 | Still applies | Minor | `traceability.json` 的 `open_items` 仍是 15 筆（OPEN-CG18-1 至 -14 加 R06-MUTATIONS-2026-10-30），我以 `json.load` 驗證。OPEN-P5 完全沒有條目，OPEN-P2、OPEN-ND18-3 只出現在其他項目的 note 內，不是獨立條目。`code-summary.md` 第八節仍寫「完整清單見 `traceability.json` 的 `open_items`」，與事實不符。本輪未處理。屬紀錄層缺口，不影響 DDL 與閘門。 |
| R-11 | Still applies | Minor | 2026-10-30 一節的「判定」只寫「(c) 以 (c-2) 的形式…勾 Step 7」，沒有明說「計畫 §八 的字面閘門條件（改檔案副本）已被取代」，也沒有指出 P15／P16 在 CI 實際可能轉紅的路徑是 `ci.yml` U20 步驟 A 降回舊定義、步驟 B 收斂、再 verify（約 `:447` 一帶）。後續幾節（11-01、11-07）亦未補。不影響 Step 7 的結論。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|

### Validation Tool Results

| 驗證 | 結果 | 解讀 |
|---|---|---|
| `tests.test_meta_schema_expectations`（scratchpad 副本，backend/.venv） | `Ran 3 tests`，OK | 三個案例（外鍵清單、P17 欄數、通過訊息編號一致）皆綠 |
| 獨立突變 M4（副本中把 `／P16／P17）全部通過` 改回 `／P16）全部通過`） | `Ran 3 tests`，`FAILED (failures=1)` | 新測試確實會抓到「P17 從通過訊息消失」，證實 code-summary 所述突變結果；副本已刪除，repo 本體未動 |
| 結構類 DO 區塊斷言編號對照通過訊息 | 相同集合（含 P17） | 殘留已清 |
| `grep` 查 `ci.yml`、`DEPLOY.md`、`verify_meta_schema.sql` 的 P 區間敘述 | 無「P1–P12」「P1-P16」「恰為 8 欄」殘留 | R-07、R-09 屬實 |
| 計畫勾選 `grep -c` | `- [x]` 為 21、`- [ ]` 為 0 | 見 Summary 對 re-tick 的判斷 |
| `validate_repo_contract.py`、`validate_env_contract.py` | 本輪未重跑；code-summary 記載兩者 passed。此次覆核未改任何 repo 檔案，僅讀取 | 可接受；本輪新增內容只有一行 SQL 通知文字與一則測試 |

### Summary

本輪修補實在：R-01、R-02、R-07、R-09 在程式與文件層皆已解決，新增的第三個測試經我獨立突變驗證為有效（P17 若從通過訊息消失即轉紅）。計畫 19 格 re-tick 有證據支撐：引擎重新核可會重設勾選（`code-summary.md` 在 10-20 與 11-06 兩節均有同一記載），conductor 重核的依據（`unit-test-instructions.md` 的 psql 指令、`run_meta_schema_migration.py` 的 `BLOCKS_TO_RUN`、J) 區塊、`ci.yml` 執行點、`DEPLOY.md` 表格）與先前一節相同，且其後只有 `:340` 文字與一則測試變動；Step 7 的突變證據來自 2026-10-30 與 2026-11-01，仍適用，因為 DDL 未再變動。R-10、R-11 仍是兩項紀錄層 Minor，不阻擋。新發現共 0 項：新引入 0、既存漏審 0、新設計問題 0。無 Critical、無 Major，故為 READY。

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
