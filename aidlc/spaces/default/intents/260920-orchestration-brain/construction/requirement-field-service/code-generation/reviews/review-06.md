## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-02 | Still applies | Minor | 讀碼確認未改：requirement_field_definitions.py:33 仍為 `^[a-z0-9_]{1,64}$`，以 `.match` 使用於 definitions.py:97、:109 與 requirement_field_errors.py:99，結尾換行仍可通過。開發者已在 code-summary Step 22 登記交 conductor。 |
| R-03 | Still applies | Minor | 讀碼確認未改：requirement_field_router.py:173 `body` 仍排在 :174 `current_user` 之前。已登記交 conductor。 |
| R-04 | Still applies | Minor | ci.yml:445-446 仍 `pip install -r backend/requirements.txt`。本輪的本機等價流程只是輔助證據，不是 CI 實跑證據。 |
| R-05 | Still applies | Minor | write_field_from_body（requirement_field_facade.py:341）仍是 K-17 之外的公開入口，K-16 字面與實作相反的交接寫在 code-summary 第 135 行與第 145-152 行；無法由本單元確認 U13／U21 已讀到。 |
| R-06 | Still applies | Minor | 本輪補了紀錄：user_router.py:510-516 的預檢仍列 system_requirement_fields，且 backend/tests 與 tests_pg 對標籤「系統需求欄位的最後修改者紀錄」零命中（我自行 grep 確認），已明寫為需新增測試並交 build-and-test。紀錄義務已滿足，缺口本身（無案例鎖住 409 類別）仍在，落點在 user_router 刪除路徑，不在本單元。 |
| R-09 | Still applies | Minor | router 的 422 說明（requirement_field_router.py:103-110）仍未列 NUL；固定訊息在 requirement_field_errors.py:132。本單元未改程式，登記為已知限制。 |
| R-10 | Still applies | Minor | 開發者本輪在本機 PostgreSQL 17 實跑 G4 為 ok（test_requirement_field_pg.py:246），但仍不是審查員獨立重跑；本審查依限制也未執行。證據強度僅為開發者自述。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|

### Validation Tool Results

本輪依限制只讀、不執行任何測試或指令，以下為讀碼與唯讀指令的獨立查證，不是測試結果。

| Tool | Result | Interpretation |
|---|---|---|
| shasum 比對收據 reviewed-source-939a1074e36d.tsv 的 22 檔 | 15 檔逐位元相同；7 檔不同：ci.yml、DEPLOY.md、run_meta_schema_migration.py、verify_meta_schema.sql、api.d.ts、openapi.json、schema_rbac.sql | 與開發者清單的 7 檔完全一致，沒有漏列，也沒有多列。本單元 requirement_field_* 六支、四支測試、tests_pg、main.py、models.py、scripts/ci 兩支 SQL 皆未變。 |
| git diff HEAD run_meta_schema_migration.py | EXPECTED_FK_DELETE_ACTIONS 改為以欄位為鍵並列滿 7 條，含 system_requirement_fields.system_id 為 c 與 updated_by 為 a | 對照 schema_rbac.sql:753 與 :760：system_id 為 ON DELETE CASCADE，updated_by 為 REFERENCES users 且無 ON DELETE（NO ACTION），兩條期望值與本單元 DDL 一致。 |
| git diff HEAD verify_meta_schema.sql | 新增 P17：system_requirement_fields 恰為 9 欄 | 數 DDL 欄位：id、system_id、agent_group、field_key、value、cleared_at、updated_at、updated_by、updated_on_behalf_of，共 9，與 P17 與 DEPLOY.md:686 一致。 |
| git diff HEAD -U0 schema_rbac.sql | hunk 位於檔頭、約 555-592、約 642-652（記憶角色與 J 區開頭純註解） | system_requirement_fields 的 DDL（752-764）與其後收斂 DO 區塊無 hunk，不碰本單元。 |
| git diff HEAD ci.yml、openapi.json、api.d.ts | 無 hunk 落在 U20 step 0 與 A–E（438-535）；openapi 的 /api/requirements 兩條 path（5505、5573）與 api.d.ts 三個 requirement 操作（4583、4632、4698）無 hunk | 與開發者結論相符。 |
| git diff HEAD DEPLOY.md | 2.2.9 內兩處計數：第 767 行「7 條外鍵」、第 856-860 行「17 條斷言」；U20 小節（868 起）與原 730-738 說明（現位移至約 779-797）無 hunk | 7 條外鍵與 migration 的 EXPECTED_FK_DELETE_ACTIONS 筆數一致；17 條與 P1 至 P17 一致。 |
| 計畫檔 git diff HEAD | 與 HEAD 差異只有：Step 11 與 Step 17 由 [x] 改 [ ]，以及新增的第八、九節（含 Step 18-24 勾選格） | 以正規化比對確認 Step 11 與 17 改動僅勾選字元，其餘既有內文逐字未動。traceability.json 與 source-manifest.json 的 git diff 為空，確實未改。 |
| 勾選實算 grep -c | 已勾 22、未勾 2 | 與 code-summary 第 396 行宣稱相符。 |
| code-summary 附帶的行號逐一開檔核對 | schema_rbac.sql、DEPLOY.md、ci.yml、router、definitions、errors、user_router、hierarchy_facade、membership_facade、membership_service、main.py、openapi.json、api.d.ts、tests_pg 的引用行號全部指向所述內容 | 未發現位移或錯引；計畫 Step 20 的 `/api/requirement-fields` 確為筆誤，實際掛載為 main.py:138 的 `/api/requirements`，開發者已據實指出。 |
| 他單元授權入口 | hierarchy_facade 的 hunk 在 96-114 與 delete_project／delete_system（約 318-379），requirement_field_facade._authorize（:244-277）只呼叫 get_project_of_system（:636）、resolve_project_role（membership_facade:209）與自己的 user_can／is_approved 檢查 | 本單元不經過 _authorize_global 與刪除路徑；本單元四支測試對 delete_system、delete_project 零引用。未發現波及。 |
| tests_pg C3 歸因 | test_membership_concurrency.py:431 的 C3 把 bob 整列移出、令 alice 成為唯一成員後期待守門 raise，失敗訊息為 passed 對 guard | 與 membership_service 第 21 列「獨自一人的專案不擋」的 projects_losing_last_admin 改動（hunk 約 665-745）語意吻合。該測試與 requirement_field 零關聯，研判合理，屬 membership-service 單元，並已列入交 conductor 清單。 |

### Summary

本輪只做回歸與紀錄，未改程式。我獨立重算雜湊，確認 7 檔變動清單完整；migration 的 7 條外鍵期望、P17 的 9 欄與 DEPLOY.md 的兩處計數都與 schema_rbac.sql 的本單元 DDL 對得上，其餘變動未落入本單元的段落或程式。Step 11 與 Step 17 改為未勾的理由成立（api.d.ts 自收據後被他單元改動且 check:types 未重跑；完整 tests_pg 有他單元的 C3 紅燈），其餘 22 格維持勾選有依據，計畫內文除勾選字元外未被改。7 項前輪 Minor 全數仍在，皆已據實登記為已知限制，無新增發現，故判 READY。限制說明：依規定我未執行任何測試，SQLite 35 案、完整套件與 PG 的綠燈結果只有開發者自述；C3 歸因是讀碼推演，不是重現。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-00 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/requirement-field-service/code-generation/code-generation-plan.md > review findings table | The reviewer's findings table could not be read, so its rows are not listed here: aidlc/spaces/default/intents/260920-orchestration-brain/construction/requirement-field-service/code-generation/code-generation-plan.md: findings table header declares ID, Severity, Location, Finding, Status. Expected columns: ID, Severity, Location, Finding, Required action, Status. Missing: Required action | Address the reviewer's findings as written below this table. | Resolved (reviewer) |
| R-01 | Major | backend/services/requirement_field_facade.py > _write_authorized；backend/services/requirement_field_types.py > RequirementFieldWriteIn | 承自 review-01，本輪未改。值只檢查型別、去空白與長度，未處理 NUL（u0000）；含 NUL 的值可通過 pydantic 與長度檢查，在 PostgreSQL 上以 DataError 變成 500，SQLite 測試抓不到。 | 在 _write_authorized 加入含 NUL 即回 RequirementFieldValidationError（登錄新的固定訊息），並補一個 422 案例與突變驗證。 | Resolved (reviewer) |
| R-02 | Minor | backend/services/requirement_field_definitions.py:33 KEY_PATTERN；requirement_field_errors.py:85 | 承自 review-01，本輪未改。KEY_PATTERN 用 ^…$ 搭配 match，結尾換行仍會通過並被回顯進 detail。 | 改用 fullmatch 或 Z，定義檔的自我檢查同步。 | Unresolved |
| R-03 | Minor | backend/services/requirement_field_router.py > write_requirement_field（body 參數） | 承自 review-01，本輪未改。body dependency 排在 current_user 之前，原始本體在驗證身分前就被完整讀入。 | 把 current_user 排在 body 之前，或在讀取時設上限。 | Unresolved |
| R-04 | Minor | .github/workflows/ci.yml > memory-schema job 步驟 0 | 承自 review-01，本輪未改。步驟 0 安裝完整後端相依，相依漂移可能讓 U20 步驟因與 schema 無關的原因紅燈，且尚無 CI 實跑證據。 | 第一次 CI 實跑後把結果記入 code-summary，並考慮只安裝遷移腳本所需的最小套件。 | Unresolved |
| R-05 | Minor | backend/services/requirement_field_facade.py > write_field_from_body；code-summary.md §七 | 承自 review-01，本輪未改。write_field_from_body 是 K-17 之外的公開入口，K-16 anti_double_check 字面與實作相反的交接仍待 U13／U21 實作者讀到。 | 無須改本單元程式；確認交接已傳達給 U13／U21。 | Unresolved |
| R-06 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/requirement-field-service/code-generation/code-summary.md > §九 | 新發現。§九說前序改動未讓本單元測試轉紅，但沒說明 U20 與使用者刪除路徑的實際交會：user_router.py:501-508 的刪除預檢已把 system_requirement_fields.updated_by 列入參照清單，沒指出是哪個測試鎖住它。 | 在 §九補一句並指名鎖住它的測試；若沒有對應案例，記為交接給 hierarchy-data 或 build-and-test。 | Unresolved |
| R-07 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/requirement-field-service/code-generation/code-summary.md > 重做段「與既有文字不符之處」第 1 點；code-generation-plan.md > §六 | 重做段已承認計畫 §六「19 項中沒有一項劃給本單元」過時（現為 23 項、第 14 項劃給本單元，非成員由 403 改為 404），但計畫本身依規則不改，§六仍留著錯誤的陳述，下游讀計畫會得到相反結論。 | 在 code-summary 的交接段明列「以第 14 項為準、計畫 §六已過時」，並指出對應測試為 H1 ②⑩⑫、H8、H9；或在計畫加一行就地更正註記。 | Resolved (reviewer) |
| R-08 | Minor | DEPLOY.md > 約第 730–732 行與 U20 小節（約第 842 行） | 兩處對「表不存在時的行為」陳述相反：前者稱 U19／U20 查詢會報 `relation does not exist`，後者說 `create_all` 會建表、只缺 COMMENT。code-summary 已揭露但只推給 build-and-test；DEPLOY.md 是本單元依 blocking 規則必須同步的部署資產，留著自相矛盾的上線說明。 | 在本單元內把前者改成與 U20 小節一致（`create_all` 建出表、只缺 COMMENT 與收斂），或明確登記為 build-and-test 的阻擋性交接項。 | Resolved (reviewer) |
| R-09 | Minor | backend/services/requirement_field_router.py > ERROR_RESPONSES 的 422 說明 | 422 說明文字沒有列出值含 NUL 這個原因。開發者已在 code-summary 揭露並刻意不改，因為會連動 openapi.json 與 api.d.ts。這是契約文件缺口，不影響行為。 | 下一次因其他原因重 dump openapi.json 時順手補上，或在 code-summary 登記為後續項。 | Unresolved |
| R-10 | Minor | backend/tests_pg/test_requirement_field_pg.py:246 G4 | 本輪未能在真實 PostgreSQL 上實跑 G4，因為審查環境不允許啟動一次性資料庫行程。G4 的 DataError 重現只有開發者的紀錄，沒有獨立驗證。SQLite 上的 H10 突變已驗證驗證層本身有效。 | 由主工作流程或 build-and-test 在 PostgreSQL 上跑一次 G4，並把結果記入 code-summary。 | Unresolved |

> R-02 Not re-checked this round

> R-03 Not re-checked this round

> R-04 Not re-checked this round

> R-05 Not re-checked this round

> R-06 Not re-checked this round

> R-09 Not re-checked this round

> R-10 Not re-checked this round
