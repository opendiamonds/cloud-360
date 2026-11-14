## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-02 | Still applies | Minor | requirement_field_definitions.py 第 33 行 KEY_PATTERN 仍為 ^[a-z0-9_]{1,64}$ 搭配 match（第 97、109 行與 requirement_field_errors.py 第 99 行皆用 match），結尾換行仍會通過。檔案雜湊與收據相同，未改。 |
| R-03 | Still applies | Minor | requirement_field_router.py 第 173 行 body 的 dependency 仍排在第 174 行 current_user 之前，未改。 |
| R-04 | Still applies | Minor | ci.yml 第 446 行仍安裝完整 backend/requirements.txt，最小安裝未做。依 brief，PR 650 的 CI run 除 tests_pg C3 外全綠，這代表 memory-schema job 已有實跑證據，但該證據未記入 code-summary，請補記後可關閉實跑部分。 |
| R-05 | Still applies | Minor | write_field_from_body 仍是 K-17 之外的公開入口，K-16 交接留在 code-summary，無法由本單元確認 U13 與 U21 已讀到。屬交接事項，不影響本單元程式。 |
| R-06 | Still applies | Minor | 重新查證：user_router.py 第 511 行仍把 system_requirement_fields 列入刪除預檢，而 backend 的 tests、tests_pg 沒有任何檔含該 409 類別標籤字串，無測試鎖住它。code-summary 已誠實登記為交接，仍屬未覆蓋缺口。 |
| R-09 | Still applies | Minor | 422 說明仍未列出值含 NUL，程式未改。屬契約文件缺口，不影響行為。 |
| R-10 | Still applies | Minor | G4 仍只有開發者本機的實跑紀錄，本審查依限制不得執行測試，無法獨立驗證。以讀碼推演，NUL 檢查位於寫入之前，邏輯成立。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/requirement-field-service/code-generation/code-generation-plan.md > Step 11 | 未勾的理由已過時。該格的內容是兩支 contract 腳本與前端 check:types 通過，而 ci.yml 第 154、159、207 行都在 CI 跑這三項，依 brief 提供的 PR 650 CI run 它們全綠，且 api.d.ts 與 openapi.json 的雜湊與收據相同。 | 以 CI run 42454550208 為證據勾選 Step 11，並在 code-summary 註明證據來源是 CI 而非本機實跑。 |
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/requirement-field-service/code-generation/code-generation-plan.md > Step 17 | 維持未勾是正確的：該格宣告 tests_pg 全綠，而 CI 的 tests_pg 仍有他單元的 C3 失敗（backend/tests_pg/test_membership_concurrency.py）。失敗不在本單元，但字面宣告不成立。 | 待 C3 修好、CI 全綠後勾選，或把該格宣告改成只限本單元的 G1 至 G4。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| shasum 對收據 reviewed-source-ed3c4b9bde06.tsv 逐列重算 | 22 列全數吻合，0 變動 | 本單元 22 個來源檔與收據逐位元相同，33deb2e 與 ff537a7 的變動未碰到本單元檔案。另一份同時間收據 reviewed-source-939a1074e36d.tsv 有 7 列不同（ci.yml、DEPLOY.md、兩支 migration 腳本、api.d.ts、openapi.json、schema_rbac.sql），屬較早狀態，以 ed3c 為準。 |
| git diff HEAD 對 code-generation-plan.md | 無差異 | 計畫內容與 HEAD 完全相同，22 勾與 2 未勾屬實（grep 實算）。 |
| git diff HEAD 對 code-summary.md | 僅檔尾追加 8 行 | 新節「整站重跑後的勾選回復」內容屬實：22 同與 0 變、22 勾與 2 未勾皆已獨立驗證。code-generation-questions.md 的差異只是計畫核准紀錄文字，無實質影響。 |
| 測試、型別檢查、CI 腳本 | 未執行 | 依 brief 限制，只做讀碼與雜湊推演。 |

### Summary

本單元程式與收據逐位元相同，計畫與摘要的勾選記錄屬實，沒有 Critical 或 Major 發現。七項既有發現全為 Minor 且仍適用，另建議依 CI 證據勾選 Step 11，Step 17 因他單元的 tests_pg C3 失敗而維持未勾，因此判定 READY。

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
