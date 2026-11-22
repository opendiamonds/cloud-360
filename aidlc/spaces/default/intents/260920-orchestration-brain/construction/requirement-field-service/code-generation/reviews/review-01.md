## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

審查範圍：U20 的 service／facade／router／errors、`schema_rbac.sql` 收斂 DO 區塊、遷移腳本、CI 步驟 0／A–E 與 fixture SQL、四支 SQLite 測試（以指定的免快取指令實跑，28 tests OK）。授權順序（待核准、全域 K4、系統查詢、成員判定，皆早於資料存取與本體解析）在 HTTP 與同進程兩條路徑一致，`write_field_from_body`、清空路徑、讀取路徑都沒有繞過；12 列矩陣的列②（非成員但具 K4.edit 的 Project_Editor）確實涵蓋 PUT／DELETE。upsert 的衝突目標、條件式清空、方言選擇、時間戳由呼叫端注入都正確。收斂 DO 區塊具冪等性、以 conkey 查外鍵、只動 `updated_on_behalf_of`、`lock_timeout` 在交易內還原。未發現 Critical。有一項 Major（含 NUL 字元的值會造成 500）與數項 Minor，皆不阻擋。

### Findings

| ID | Severity | Location | Finding | Status |
|---|---|---|---|---|
| R-01 | Major | backend/services/requirement_field_facade.py `_write_authorized`（約第 276–300 行）；backend/services/requirement_field_types.py `RequirementFieldWriteIn` | 值只檢查型別、去空白與長度，未處理 NUL（`\u0000`）。JSON 本體 `{"value":"a\u0000b"}` 可通過 pydantic 與長度檢查，PostgreSQL 的 text 欄位不接受 NUL，驅動會丟 `DataError`；facade 的 `except Exception` 只 rollback 後原樣重拋，router 只轉譯 `RequirementFieldError`，結果是已授權使用者可穩定觸發 500，違反 BR46.1「錯誤為單一固定字串形狀」的意圖。SQLite 測試庫不拒絕 NUL，28 個測試與 PG 測試都不會變紅。建議：在 `_write_authorized` 加入「含 NUL 即 `RequirementFieldValidationError('value','invalid_chars')`」（登錄新的固定訊息），並補一個 H5 類的 422 案例（以突變驗證確認會紅）。 | New |
| R-02 | Minor | backend/services/requirement_field_definitions.py:33（`KEY_PATTERN = ^[a-z0-9_]{1,64}$`）；requirement_field_errors.py `UnknownFieldKey` | `$` 會匹配結尾換行，`re.match("cost\n")` 為真，所以路徑片段 `cost%0A` 會通過「合格識別字形狀」判斷而被回顯進 `detail`（含換行）。只是定址片段、不是欄位值，影響很小，但與「不合形狀不回顯」的註解意圖不符。建議改用 `fullmatch` 或 `\Z`（定義檔的自我檢查亦同）。 | New |
| R-03 | Minor | backend/services/requirement_field_router.py `write_requirement_field`（`body: bytes = Depends(_read_raw_body)` 位於 `get_current_user` 之前） | 參數順序使原始本體在身分驗證之前就被完整讀入記憶體；未登入者可送大本體消耗記憶體（長度上限 2000 只在授權之後的解析才套用）。授權順序本身（BR41）不受影響，因為尚未解析也未碰資料。建議把 `current_user` 排在 `body` 之前，或在讀取時設上限。 | New |
| R-04 | Minor | .github/workflows/ci.yml U20 step 0（`pip install -r backend/requirements.txt`） | 步驟 0 在 memory-schema job 內安裝完整後端相依，作者已在註解揭露這是對 concurrency job 取捨的有意違反。風險是相依解析在 CI 上漂移（requirements 除 fastapi／pydantic 外未 pin），使 U20 步驟紅燈的原因與 schema 無關。本機只在 PG 17.7 驗證過、CI 為 pg18，尚未有 CI 實跑證據。建議第一次 CI 實跑後把結果記入 code-summary，並考慮只安裝遷移腳本所需的最小套件。 | New |
| R-05 | Minor | backend/services/requirement_field_facade.py `write_field_from_body` 與 code-summary §六第 4 項 | `write_field_from_body` 為 K-17 之外新增的公開方法，同進程呼叫端若誤用它仍會經授權（安全），但它讓契約面多一個入口。作者已列入追認清單；另 `K-16 anti_double_check` 字面與實作相反的風險已揭露，須確保 U13／U21 的實作單元實際讀到該交接。無須修改本單元程式。 | New |
