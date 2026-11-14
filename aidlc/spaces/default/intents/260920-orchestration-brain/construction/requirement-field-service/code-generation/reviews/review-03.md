## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-26T00:27:09Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-00 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/requirement-field-service/code-generation/code-generation-plan.md > review findings table | The reviewer's findings table could not be read, so its rows are not listed here: aidlc/spaces/default/intents/260920-orchestration-brain/construction/requirement-field-service/code-generation/code-generation-plan.md: findings table header declares ID, Severity, Location, Finding, Status. Expected columns: ID, Severity, Location, Finding, Required action, Status. Missing: Required action | Address the reviewer's findings as written below this table. | Resolved (reviewer) |
| R-01 | Major | backend/services/requirement_field_facade.py > _write_authorized；backend/services/requirement_field_types.py > RequirementFieldWriteIn | 承自 review-01，本輪未改。值只檢查型別、去空白與長度，未處理 NUL（u0000）；含 NUL 的值可通過 pydantic 與長度檢查，在 PostgreSQL 上以 DataError 變成 500，SQLite 測試抓不到。 | 在 _write_authorized 加入含 NUL 即回 RequirementFieldValidationError（登錄新的固定訊息），並補一個 422 案例與突變驗證。 | Unresolved |
| R-02 | Minor | backend/services/requirement_field_definitions.py:33 KEY_PATTERN；requirement_field_errors.py:85 | 承自 review-01，本輪未改。KEY_PATTERN 用 ^…$ 搭配 match，結尾換行仍會通過並被回顯進 detail。 | 改用 fullmatch 或 Z，定義檔的自我檢查同步。 | Unresolved |
| R-03 | Minor | backend/services/requirement_field_router.py > write_requirement_field（body 參數） | 承自 review-01，本輪未改。body dependency 排在 current_user 之前，原始本體在驗證身分前就被完整讀入。 | 把 current_user 排在 body 之前，或在讀取時設上限。 | Unresolved |
| R-04 | Minor | .github/workflows/ci.yml > memory-schema job 步驟 0 | 承自 review-01，本輪未改。步驟 0 安裝完整後端相依，相依漂移可能讓 U20 步驟因與 schema 無關的原因紅燈，且尚無 CI 實跑證據。 | 第一次 CI 實跑後把結果記入 code-summary，並考慮只安裝遷移腳本所需的最小套件。 | Unresolved |
| R-05 | Minor | backend/services/requirement_field_facade.py > write_field_from_body；code-summary.md §七 | 承自 review-01，本輪未改。write_field_from_body 是 K-17 之外的公開入口，K-16 anti_double_check 字面與實作相反的交接仍待 U13／U21 實作者讀到。 | 無須改本單元程式；確認交接已傳達給 U13／U21。 | Unresolved |
| R-06 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/requirement-field-service/code-generation/code-summary.md > §九 | 新發現。§九說前序改動未讓本單元測試轉紅，但沒說明 U20 與使用者刪除路徑的實際交會：user_router.py:501-508 的刪除預檢已把 system_requirement_fields.updated_by 列入參照清單，沒指出是哪個測試鎖住它。 | 在 §九補一句並指名鎖住它的測試；若沒有對應案例，記為交接給 hierarchy-data 或 build-and-test。 | Unresolved |
| R-07 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/requirement-field-service/code-generation/code-summary.md > 重做段「與既有文字不符之處」第 1 點；code-generation-plan.md > §六 | 重做段已承認計畫 §六「19 項中沒有一項劃給本單元」過時（現為 23 項、第 14 項劃給本單元，非成員由 403 改為 404），但計畫本身依規則不改，§六仍留著錯誤的陳述，下游讀計畫會得到相反結論。 | 在 code-summary 的交接段明列「以第 14 項為準、計畫 §六已過時」，並指出對應測試為 H1 ②⑩⑫、H8、H9；或在計畫加一行就地更正註記。 | New |
| R-08 | Minor | DEPLOY.md > 約第 730–732 行與 U20 小節（約第 842 行） | 兩處對「表不存在時的行為」陳述相反：前者稱 U19／U20 查詢會報 `relation does not exist`，後者說 `create_all` 會建表、只缺 COMMENT。code-summary 已揭露但只推給 build-and-test；DEPLOY.md 是本單元依 blocking 規則必須同步的部署資產，留著自相矛盾的上線說明。 | 在本單元內把前者改成與 U20 小節一致（`create_all` 建出表、只缺 COMMENT 與收斂），或明確登記為 build-and-test 的阻擋性交接項。 | New |

> R-00 Reviewer note: 前輪表格無法讀取，其內容已由本輪全新審查取代：重新閱讀 facade、router、service、types、definitions、errors 六支來源與 code-summary，所有顧慮重新逐項記錄於本表與 New findings。本項不再獨立成立。

> R-01 Reviewer note: 實測可達。pydantic 的 `RequirementFieldWriteIn.model_validate_json(b'{"value":"a\u0000b"}')` 放行，得到 `'ax00b'`；`strip()` 與 2000 字檢查都不處理 NUL。本 repo 驅動為 psycopg 3.3.6，對含 NUL 的字串在 dump 階段拋 `psycopg.DataError: PostgreSQL text fields cannot contain NUL (0x00) bytes`（`StrDumper.dump` 與 `as_literal` 皆實測）。`_write_authorized` 的 `except Exception: rollback; raise` 會原樣上拋，router 只轉譯 `RequirementFieldError`，所以結果是 500，且不符 router 文件自己宣告的「每一個 422 都來自領域例外」。SQLite 接受 NUL，全部 34 個 SQLite 測試與 `tests_pg` 都沒有 NUL 案例，故測試綠燈抓不到。僅具 K4 edit 的已授權者可觸發，無資料損毀，但屬於輸入驗證缺口。

> R-02 Reviewer note: `requirement_field_definitions.py:33` 的 `KEY_PATTERN` 仍為 `^[a-z0-9_]{1,64}$` 搭配 `match`；實測 `match('abcn')` 為真。`UnknownFieldKey` 因此會把帶結尾換行的路徑片段回顯進 `detail`。僅影響訊息回顯，不改狀態碼。

> R-03 Reviewer note: `write_requirement_field` 的參數順序仍是 `body: bytes = Depends(_read_raw_body)` 先於 `current_user`，原始本體在身分驗證前即被完整讀入記憶體，無大小上限。

> R-04 Reviewer note: `.github/workflows/ci.yml` 的 U20 步驟 0 仍執行 `pip install -r backend/requirements.txt`；code-summary 也承認 CI 上的實跑尚未發生，PG 17 與 CI 的 pg18 有版本差。

> R-05 Reviewer note: 交接內容已寫進 code-summary §七（K-16 `anti_double_check` 與實作相反、`write_field_from_body` 為 K-17 之外的入口），本單元無須改程式。是否已傳達給 U13／U21 實作者無法在本單元內驗證，保留為追蹤項。

> R-06 Reviewer note: `user_router.py:501-508` 的刪除預檢確實把 `system_requirement_fields.updated_by` 列為參照類別，但在 `tests/`、`tests_pg/` 中除 U20 自身測試外，只有 `test_project_write_guard.py` 與 `test_mcp_bridge_e2e.py` 碰到該表，沒有任何測試斷言 `blocking_references` 含 `system_requirement_fields`（`test_user_delete_hierarchy.py` 對該字串零命中）。code-summary §九與「重做」段仍未指名鎖住這個交會的測試，也未登記為交接。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `unittest tests.test_requirement_field_data / _service / _facade / _http`（backend，快取導向 scratchpad） | 34 tests OK | 與 code-summary 一致；但 SQLite 對 NUL 不設防，無法證明 R-01 已被擋。 |
| pydantic `model_validate_json` 含 `\u0000` | 通過，值為 `'a\x00b'` | R-01 在驗證層可達。 |
| psycopg 3.3.6 `StrDumper.dump('a\x00b')`／`as_literal` | 皆拋 `DataError: PostgreSQL text fields cannot contain NUL (0x00) bytes` | R-01 在 PostgreSQL 路徑會變 500。 |
| 搜尋 `blocking_references` 含 `system_requirement_fields` 的測試 | 無命中 | R-06 仍成立。 |

### Summary

主要顧慮仍是 R-01：含 NUL 的值能通過所有驗證，在正式使用的 psycopg 3 上變成 500，違背 router 所宣稱的固定 422 契約，而 SQLite 測試完全看不到；授權順序、單一條件式清空、upsert 與非成員 404 的實作與測試都扎實。R-01 修復（在 `_write_authorized` 拒絕含 NUL 的值並補 422 案例與突變驗證）前不建議放行，其餘為 Minor。
