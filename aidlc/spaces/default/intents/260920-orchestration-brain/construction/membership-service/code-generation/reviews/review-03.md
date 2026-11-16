## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-20T23:54:27Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | backend/services/membership_service.py > `admin_count_after` / `assert_still_has_admin`（自我降級、自我移出路徑） | 停用守門與改選已改用「合格」口徑（啟用、已核准、全域 K3.edit），但自我降級與自我移出仍用原始管理者列數。專案有兩位管理者 A（合格）與 B（已停用或只有 K3.view）時，A 降級自己或移出自己會被放行，之後專案沒有任何能執行管理動作的人。這兩條路徑也沒有後續的自動改選補位（改選只在停用時觸發）。docstring 說這兩條路徑「仍以本函式擋下管理者數歸零」，與第 1 項要消除的「實際無人能管」狀態不一致。 | 在 code-summary 或 docstring 如實記載這個殘留（歸零守門數的是原始列數，不是合格者），或在後續單元把 `assert_still_has_admin` 也改用同一個 `is_qualified_successor`。不阻擋本單元。 | New |
| R-02 | Minor | backend/services/membership_service.py > `reselect_for_project` 的 `no_qualified_candidate` 分支；backend/services/user_router.py > `update_user_active` 重送路徑 | 守門通過之後、改選之前，唯一的合格接手人若被停用（`OPEN-N19-2` 已承認的窗口），或對已停用帳號重送時守門不重跑，`reselect_for_project` 只記 INFO 並回 `None`。端點仍回 200，`failed_project_ids` 為空，專案實際沒有可運作的管理者。這與第 10 項「失敗不得無聲」的目標相悖，而且 500 本體叫操作者「重送補跑」，對這個分支重送也補不了。 | 至少讓該分支改記 WARNING 並寫進 code-summary 的殘留限制。若要堵住，把「他是管理者卻無合格候選」也計入 `failed_project_ids`（需另定義 500 本體語意，宜與使用者確認）。 | New |
| R-03 | Minor | backend/services/membership_backfill.py > `run_backfill` 終檢失敗訊息；模組 docstring「持續性失敗」 | 訊息與 docstring 把終檢失敗歸因於「某專案的 `owner_user_id` 指向不存在的使用者，使 INSERT 的外鍵失敗」。但 `schema_rbac.sql:348` 的 `projects.owner_user_id` 是 `NOT NULL REFERENCES users (id)`，孤兒擁有者在資料庫層本就不可能存在。真正失敗時（例如 `role` CHECK、並行啟動撞唯一約束），操作者會被導去查一個不存在的資料問題。啟動失敗會觸發部署回滾與重啟迴圈，診斷訊息誤導的代價比一般 log 高。 | 改成不預設單一原因的訊息（列出 `remaining` 數與實際 INSERT 例外），或刪掉孤兒擁有者的推測。 | New |
| R-04 | Minor | backend/tests_pg/test_membership_concurrency.py > `setUpClass`（呼叫 `database._ensure_j5_schema()`）；schema_rbac.sql > `users` | 守門現在讀 `users.authorization_status`，但 `schema_rbac.sql` 的 `users` 沒有這一欄，它只由後端啟動時的 `_ensure_j5_schema()` 補上。測試因此依賴一個私有函式（且該函式吞掉失敗，測試靠事後查 information_schema 補救），也代表只套用 `schema_rbac.sql` 的環境（含 CI 的 `concurrency` job 本身）無法獨立跑守門。這是既有的 schema 與啟動補丁分家，本單元把它變成新的硬依賴。 | 在 `DEPLOY.md` 與 code-summary 明記「守門依賴 `users.authorization_status`，需後端啟動過一次」，或讓 `schema_rbac.sql` 補上該欄（`IF NOT EXISTS`）。測試呼叫私有函式的風險可接受，建議留一行註解說明為何不另寫 DDL。 | New |
| R-05 | Minor | frontend/src/pages/AdminPage.tsx > `handleToggleActive`（`!res.ok` 分支，單元外的消費端） | 停用端點新增 500／503，且此時帳號已停用。前端只以 toast 顯示 `detail`，不更新該列，列仍顯示「啟用中」，也不顯示 `failed_project_ids`。操作者要自己判斷「再按一次停用」才是補跑，且畫面與資料庫狀態不一致。code-summary 已如實記載這是讀碼推得、未用 e2e 驗證。 | 在本 intent 的前端單元（或後續）排入：500／503 時就地把該列標為已停用並顯示失敗專案。至少把它列為合併前的已知限制，並補一個 e2e 或手動案例。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 按指示未執行任何測試、lint、build、dump 或 Python 命令 | N/A | 結論來自讀檔與 `git diff`。9 項突變與 1234 個測試的結果引用 `code-summary.md`，我沒有獨立複驗。 |

### Summary

本輪五項裁決（#1、#4、#10、#15、#16）在程式與測試上都對得起來。合格謂詞只有一份（`is_qualified_successor`），守門與改選共用它。`projects_losing_last_admin` 的查詢次數以不同角色數為界。對 15a 的詮釋（不合格的第二位管理者不算數）符合 `BR7.3` 與 `AC12.4.1`，沒有擋過頭：專案另有合格但非管理者的成員時會放行並改選。改選範圍擴大後，`F11` 斷言事件只出現在無合格管理者的專案，冪等判定擋得住。`SET LOCAL` 只作用於當前交易，SQLSTATE 判斷與 `C4` 的真實逾時一致，重送路徑沒有繞過自我停用或最後一位全域管理員的守門。啟動補齊失敗會讓部署健康檢查失敗而走既有回滾，這是刻意的。剩下的都是 Minor：自我降級的原始列數與合格口徑不一致、一個靜默的無候選分支、一則可能誤導的診斷訊息、以及 schema 與啟動補丁分家造成的測試依賴。
