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
| R-09 | Minor | backend/services/requirement_field_router.py > ERROR_RESPONSES 的 422 說明 | 422 說明文字沒有列出值含 NUL 這個原因。開發者已在 code-summary 揭露並刻意不改，因為會連動 openapi.json 與 api.d.ts。這是契約文件缺口，不影響行為。 | 下一次因其他原因重 dump openapi.json 時順手補上，或在 code-summary 登記為後續項。 | Unresolved |
| R-10 | Minor | backend/tests_pg/test_requirement_field_pg.py:246 G4 | 本輪未能在真實 PostgreSQL 上實跑 G4，因為審查環境不允許啟動一次性資料庫行程。G4 的 DataError 重現只有開發者的紀錄，沒有獨立驗證。SQLite 上的 H10 突變已驗證驗證層本身有效。 | 由主工作流程或 build-and-test 在 PostgreSQL 上跑一次 G4，並把結果記入 code-summary。 | Unresolved |

> R-02 Reviewer note: requirement_field_definitions.py:33 的 KEY_PATTERN 仍是 ^…$ 搭配 match（第 97、109 行），檔案與收據逐位元相同，未改。

> R-03 Reviewer note: requirement_field_router.py 與收據相同，body 與 current_user 的依賴順序未變。

> R-04 Reviewer note: ci.yml 與收據相同；code-summary 未見 memory-schema job 的 CI 實跑結果。

> R-05 Reviewer note: requirement_field_facade.py 未變；K-16 交接仍待 U13／U21 實作者讀到。

> R-06 Reviewer note: code-summary 的 §九 仍未提 user_router.py 刪除預檢與 system_requirement_fields.updated_by 的交會，也沒指名鎖住它的測試。

> R-09 Reviewer note: ERROR_RESPONSES 的 422 說明仍未列 NUL；openapi.json 與 api.d.ts 與收據相同。

> R-10 Reviewer note: 本輪同樣未在真實 PostgreSQL 實跑 G4；code-summary 第 257 行有開發者自己的 tests_pg 紀錄，但無獨立驗證。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 逐檔 sha256 比對 reviewed-source-90c2466fff25.tsv（22 檔）與 git status | 21 檔相同；僅 DEPLOY.md 不同；清單內檔案相對 HEAD 皆無未提交變動 | 與開發者「只有 DEPLOY.md 變」的說法一致。 |
| 獨立重建 DEPLOY.md 收據版本：取 HEAD 版，把第 2229、2239 行換回 624c170 的第 2088、2098 行 | sha256 為 27898f42…3406，與收據逐位元相同 | 自收據以來 DEPLOY.md 的差異恰為 §5.13 這兩行，無其他。 |
| 本單元 SQLite 測試（副本、PYTHONDONTWRITEBYTECODE=1、-B）：test_requirement_field_data、service、facade、http | Ran 35 tests，OK | 與開發者結果一致；副本已刪，工作樹未產生快取。 |

### Summary

自上一輪 READY 審查以來，本單元程式、測試、schema、CI、OpenAPI 與型別檔零變動，DEPLOY.md 唯一差異是合併前必修第 26 項對 §5.13 的兩行改寫（6a 失敗不開 revert PR），內容講的是 deploy.yml 步驟 6a 的 rollback 行為，與 2.2.9 及約第 730–738 行的 U20 說明（資料庫遷移與欄位轉型）沒有矛盾。前輪七項 Minor 全部仍適用且皆不阻擋，無 Critical 或 Major，判定 READY。
