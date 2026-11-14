## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

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
| R-09 | Minor | backend/services/requirement_field_router.py > ERROR_RESPONSES 的 422 說明 | 422 說明文字沒有列出值含 NUL 這個原因。開發者已在 code-summary 揭露並刻意不改，因為會連動 openapi.json 與 api.d.ts。這是契約文件缺口，不影響行為。 | 下一次因其他原因重 dump openapi.json 時順手補上，或在 code-summary 登記為後續項。 | New |
| R-10 | Minor | backend/tests_pg/test_requirement_field_pg.py:246 G4 | 本輪未能在真實 PostgreSQL 上實跑 G4，因為審查環境不允許啟動一次性資料庫行程。G4 的 DataError 重現只有開發者的紀錄，沒有獨立驗證。SQLite 上的 H10 突變已驗證驗證層本身有效。 | 由主工作流程或 build-and-test 在 PostgreSQL 上跑一次 G4，並把結果記入 code-summary。 | New |

> R-01 Reviewer note: facade 的 _write_authorized 在 strip 前以固定訊息擋下 NUL（requirement_field_facade.py:374-380，訊息登錄於 requirement_field_errors.py:130-132，不回顯值）。值寫進資料庫的路徑只有 upsert_value，其唯一呼叫者是 _write_authorized；write_field 與 write_field_from_body 皆經過它。on_behalf_of、agent_group、field_key 為白名單，system_id 轉整數。在 scratchpad 副本拿掉檢查後 H10 轉紅（9 個失敗），還原後綠。

> R-02 Reviewer note: KEY_PATTERN 仍為 ^[a-z0-9_]{1,64}$ 搭配 match（requirement_field_definitions.py:33、:97、:109；requirement_field_errors.py:99）。

> R-03 Reviewer note: write_requirement_field 的 body dependency 仍排在 current_user 之前（requirement_field_router.py:173-174）。

> R-04 Reviewer note: 本輪未改 CI 步驟 0，沒有 CI 實跑證據。

> R-05 Reviewer note: write_field_from_body 仍是 K-17 之外的公開入口，交接尚待 U13 與 U21 讀到。

> R-06 Reviewer note: code-summary §九 仍沒有指名鎖住 user_router.py:501-508 對 system_requirement_fields.updated_by 預檢的測試。

> R-07 Reviewer note: code-summary.md:207 已明寫以第 14 項為準、計畫 §六已過時，並列出對應測試 H1、H8、H9。

> R-08 Reviewer note: DEPLOY.md 約 730-738 行已與 U20 小節及部署順序表一致：表不存在時由 create_all 建表，只缺 COMMENT；表已存在時缺的是欄位收斂。全檔不再有 relation does not exist 的矛盾陳述。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 副本內執行 test_requirement_field_data、service、facade、http（PYTHONDONTWRITEBYTECODE=1，副本位於 scratchpad） | Ran 35 tests，OK | 本單元 SQLite 測試全綠；工作樹只用讀取，未執行任何東西。 |
| 突變：副本內把 NUL 檢查改成 if False 後跑 test_requirement_field_http | 10 個測試中 9 個失敗 | H10 能真的失敗；還原後 10 個全綠。 |
| 副本內跑全套 discover | 有失敗與錯誤，集中在部署探針、compose、workflow、MCP bridge 等測試 | 副本只複製 backend 與 schema_rbac.sql，這些測試要讀 repo 根目錄的 workflow 與 compose 檔，屬副本環境缺檔，與本單元無關；本單元的測試檔全綠，我沒有把這當成回歸。 |
| tests_pg G4 | 未實跑 | 見新發現第二列。 |

### Summary

第 24 項的 NUL 缺口已在唯一寫入入口的共同上游補上：訊息固定、不回顯值，H10 通過突變驗證，DEPLOY.md 的矛盾已消除。0 個 Critical、0 個 Major；仍適用的是前輪遺留的 R-02 至 R-06（皆 Minor），另有 2 個新的 Minor（422 說明未列 NUL、G4 未在 PostgreSQL 上獨立實跑）。
