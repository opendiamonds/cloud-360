## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-25T07:07:07Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | backend/services/membership_service.py > `admin_count_after` / `assert_still_has_admin`（自我降級、自我移出路徑） | 停用守門與改選已改用「合格」口徑（啟用、已核准、全域 K3.edit），但自我降級與自我移出仍用原始管理者列數。專案有兩位管理者 A（合格）與 B（已停用或只有 K3.view）時，A 降級自己或移出自己會被放行，之後專案沒有任何能執行管理動作的人。這兩條路徑也沒有後續的自動改選補位（改選只在停用時觸發）。docstring 說這兩條路徑「仍以本函式擋下管理者數歸零」，與第 1 項要消除的「實際無人能管」狀態不一致。 | 在 code-summary 或 docstring 如實記載這個殘留（歸零守門數的是原始列數，不是合格者），或在後續單元把 `assert_still_has_admin` 也改用同一個 `is_qualified_successor`。不阻擋本單元。 | Unresolved |
| R-02 | Minor | backend/services/membership_service.py > `reselect_for_project` 的 `no_qualified_candidate` 分支；backend/services/user_router.py > `update_user_active` 重送路徑 | 守門通過之後、改選之前，唯一的合格接手人若被停用（`OPEN-N19-2` 已承認的窗口），或對已停用帳號重送時守門不重跑，`reselect_for_project` 只記 INFO 並回 `None`。端點仍回 200，`failed_project_ids` 為空，專案實際沒有可運作的管理者。這與第 10 項「失敗不得無聲」的目標相悖，而且 500 本體叫操作者「重送補跑」，對這個分支重送也補不了。 | 至少讓該分支改記 WARNING 並寫進 code-summary 的殘留限制。若要堵住，把「他是管理者卻無合格候選」也計入 `failed_project_ids`（需另定義 500 本體語意，宜與使用者確認）。 | Resolved (reviewer) |
| R-03 | Minor | backend/services/membership_backfill.py > `run_backfill` 終檢失敗訊息；模組 docstring「持續性失敗」 | 訊息與 docstring 把終檢失敗歸因於「某專案的 `owner_user_id` 指向不存在的使用者，使 INSERT 的外鍵失敗」。但 `schema_rbac.sql:348` 的 `projects.owner_user_id` 是 `NOT NULL REFERENCES users (id)`，孤兒擁有者在資料庫層本就不可能存在。真正失敗時（例如 `role` CHECK、並行啟動撞唯一約束），操作者會被導去查一個不存在的資料問題。啟動失敗會觸發部署回滾與重啟迴圈，診斷訊息誤導的代價比一般 log 高。 | 改成不預設單一原因的訊息（列出 `remaining` 數與實際 INSERT 例外），或刪掉孤兒擁有者的推測。 | Unresolved |
| R-04 | Minor | backend/tests_pg/test_membership_concurrency.py > `setUpClass`（呼叫 `database._ensure_j5_schema()`）；schema_rbac.sql > `users` | 守門現在讀 `users.authorization_status`，但 `schema_rbac.sql` 的 `users` 沒有這一欄，它只由後端啟動時的 `_ensure_j5_schema()` 補上。測試因此依賴一個私有函式（且該函式吞掉失敗，測試靠事後查 information_schema 補救），也代表只套用 `schema_rbac.sql` 的環境（含 CI 的 `concurrency` job 本身）無法獨立跑守門。這是既有的 schema 與啟動補丁分家，本單元把它變成新的硬依賴。 | 在 `DEPLOY.md` 與 code-summary 明記「守門依賴 `users.authorization_status`，需後端啟動過一次」，或讓 `schema_rbac.sql` 補上該欄（`IF NOT EXISTS`）。測試呼叫私有函式的風險可接受，建議留一行註解說明為何不另寫 DDL。 | Unresolved |
| R-05 | Minor | frontend/src/pages/AdminPage.tsx > `handleToggleActive`（`!res.ok` 分支，單元外的消費端） | 停用端點新增 500／503，且此時帳號已停用。前端只以 toast 顯示 `detail`，不更新該列，列仍顯示「啟用中」，也不顯示 `failed_project_ids`。操作者要自己判斷「再按一次停用」才是補跑，且畫面與資料庫狀態不一致。code-summary 已如實記載這是讀碼推得、未用 e2e 驗證。 | 在本 intent 的前端單元（或後續）排入：500／503 時就地把該列標為已停用並顯示失敗專案。至少把它列為合併前的已知限制，並補一個 e2e 或手動案例。 | Unresolved |
| R-06 | Major | backend/services/membership_service.py > `projects_losing_last_admin`（`:573-636`）；backend/services/user_router.py > `update_user_active`、`delete_user`（`:1100`、`:1170` 附近的「請先停用帳號後再刪除」）；backend/tests/test_membership_endpoints.py > `test_E6` | 只有自己一位成員的專案（建立專案或回填後，擁有者就是唯一的 `project_admin`，包含每位持圖使用者的預設專案）會讓擁有者無法被停用：守門找不到合格接手人而回 409，`E6` 的前半段就是這個情形。刪除端點又要求帳號必須先停用，所以這類使用者既停用不了也刪除不了。`hierarchy-data` 合併前必修第 3 項「空預設專案隨使用者清除」要處理的正是這種使用者，但它的前置條件（已停用）在本單元落地後無法達成。平台管理員不是專案成員，沒有任何覆寫入口。整個設計文件與 code-summary 都沒有提到這個交互。 | 向使用者確認處置並寫進產出，二選一：(a) 守門對「無圖、無其他成員的預設專案」放行，並讓改選或刪除路徑處理該專案；(b) 明確記為已知限制，並提供平台管理員可用的出口（例如先移除擁有者的成員列，或刪除空專案的端點）。無論選哪個，都補一個「僅自己一位成員的預設專案擁有者，先停用再刪除」的端到端測試。 | New |
| R-07 | Minor | backend/services/membership_service.py > `assert_invitee_has_global_permission`（`:829-875`，只要 `K3.view`）；`set_member_role`／`change_role`（`membership_facade.py:339-402`） | 邀請時角色可直接指定為 `project_admin`，改角色也可把停用、待核准或只有 `K3.view` 的成員升為管理者，兩條路徑都不檢查 `is_qualified_successor`。這類「名義管理者」會被 `admin_count_after` 當成有效管理者，使 R-01 的自我降級放行更容易發生（專案剩一位真管理者加一位名義管理者，真管理者降級自己後，沒有人能執行管理動作）。 | 對升為 `project_admin` 的目標套用 `is_qualified_successor`（只限 `role == project_admin` 的寫入），或把 `admin_count_after` 改為只計合格者，並同時解掉 R-01。至少在 code-summary 如實記載。 | New |
| R-08 | Minor | backend/services/membership_facade.py > `_authorize_global`（`:101-119`）、`list_my_pending_reselections`、`acknowledge_reselection` | 同為 facade 的 `HierarchyFacade`、`MemoryFacade`、`RequirementFieldFacade` 都以 `principal.is_approved` 先擋待核准帳號，本 facade 的 `_authorize_global` 呼叫 `user_can` 時不帶 `authorization_status`，橫幅兩個方法更完全沒有授權檢查。目前唯一呼叫端是已有 `require_story_action` 的 router，所以不可被利用；但 K-16 的同進程呼叫端（大腦側）若直接呼叫，防線只剩 `_assert_project_exists` 內部轉換出的 404，橫幅方法則沒有。 | 在 `_authorize_global` 與兩個橫幅方法開頭加 `principal.is_approved` 檢查，行為與其他三個 facade 一致，並補一個待核准 principal 的 deny 測試。 | New |
| R-09 | Minor | backend/services/membership_backfill.py > `_BACKFILL_SQL`（`:76-82`）；`reselection_scope`（`membership_service.py:1034-1047`） | 回填對每個零成員專案一律把擁有者寫成 `project_admin`，不看帳號是否已停用。已停用帳號擁有的專案因此取得一位停用的管理者，而自動改選只在「停用動作」時觸發，這些專案永遠不會被改選，也沒有人能管理它們。屬一次性資料狀況，影響僅限啟動時已存在的停用擁有者專案。 | 回填完成後列出「唯一管理者已停用」的專案數（log 或 `--dry-run` 輸出），或對這些專案跑一次改選。至少在 `DEPLOY.md` §2.2.10 記載這個殘留。 | New |
| R-10 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/membership-service/code-generation/code-summary.md > 「與已核可計畫／測試說明的落差」末段 | 摘要寫現有測試數為 data 11、facade 14、endpoints 13（共 38），本輪實跑這三個模組為 41 個測試，數字對不上。另外 8 格未勾的計畫格依賴「本檔為準」的說明，審閱者必須自行對照才能知道哪些突變驗證沒有重跑。 | 以實跑輸出重數並更正測試數；在摘要列出未重跑突變驗證的格子與其最近一次紀錄的位置。 | New |

> R-01 Reviewer note: `membership_service.py:430-465` 的 `admin_count_after` 仍以原始管理者列數判斷，`assert_still_has_admin`（`:639-668`）的自我降級與自我移出走這條路徑，未改用 `is_qualified_successor`。code-summary 末節把它列為「已接受風險」，沒有在 docstring 或 DEPLOY.md 如實記載殘留。下方新發現 2 說明這個缺口比當初更容易被觸發。

> R-02 Reviewer note: `reselect_for_project`（`membership_service.py:978-983`）在無合格管理者也無合格接手人時改拋 `NoQualifiedSuccessor`，`run_auto_reselection` 計入 `failed_project_ids`，停用端點回 500。測試 `F10` 與 `E9` 全綠（本輪實跑 41 個測試 OK）。

> R-03 Reviewer note: 終檢失敗訊息（`membership_backfill.py:150-156`）已改成不預設單一原因，且明說外鍵不會有孤兒。但同一檔的模組 docstring（`:28-30`）仍寫「持續性的失敗（例如某專案的 `owner_user_id` 指向不存在的使用者）」，與訊息互相矛盾。只剩 docstring 需要改。

> R-04 Reviewer note: `schema_rbac.sql` 與 `DEPLOY.md` 都沒有 `authorization_status` 這個字樣（實查 grep 無命中）。守門（`qualified_successors` 讀 `User.authorization_status`）依賴後端啟動時 `_ensure_j5_schema()` 補欄，`tests_pg` 仍呼叫該私有函式。未記載成部署前提。

> R-05 Reviewer note: `frontend/src/pages/AdminPage.tsx:160-186` 未改：`!res.ok` 只丟 `data.detail`。500／503 本體有 `detail`，但不列 `failed_project_ids`，該列也不更新。409 的 `LastAdminGuardReport` 本體沒有 `detail`，toast 只會顯示「更新狀態失敗」，操作者看不到是哪些專案擋下（即 `OPEN-CG19-3`，目前仍開放）。屬單元外消費端。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `python3 -B -m unittest tests.test_membership_data tests.test_membership_facade tests.test_membership_endpoints`（`backend/`，指定的 hypothesis 與 bytecode 設定） | Ran 41 tests，OK | 三個測試模組全綠；測試數與摘要不符，見新發現 5。 |
| 合併前必修 #1、#4（`qualified_successors`、`is_qualified_successor`、`assert_invitee_has_global_permission`） | 程式存在且一致，守門與改選共用同一謂詞 | 已在程式碼確認；`F9`、`F10`、`F11`、`E8` 覆蓋。 |
| 合併前必修 #10、#16（`ReselectionOutcome`、500／503、`SET LOCAL lock_timeout`、`55P03` 轉 `MembershipLockTimeout`） | 程式存在（`lock_project`、`update_user_active`、router `_translate`） | 已在程式碼確認；`E9`、`E10`、`F12` 覆蓋。真實 PostgreSQL 的 `C4` 本輪未重跑（依指示不啟動資料庫），只採信摘要紀錄。 |
| 合併前必修 #15（`membership_backfill.py`、`main.py` 啟動呼叫） | 程式存在，終檢訊息已修 | `M9`–`M11` 覆蓋；docstring 殘留見 R-03。 |
| 後續單元對共用檔的改動 | `create_project_with_owner`、`HierarchyFacade` 的 `is_approved` 與 404 規則、`PROJECT_NOT_FOUND_DETAIL` 與本單元契約相容 | 測試全綠；本單元的非成員 404 與成員內 403 行為符合 #14。 |

### Summary

0 個 Critical、1 個 Major、5 個新 Minor，5 個前次 Minor 中 1 個已修、4 個仍存在。五項合併前必修在程式與測試中成立；主要風險是新守門與既有「先停用才能刪除」的組合讓僅有自己一位成員的專案擁有者無法停用，也就無法刪除，需要使用者裁決出口。
