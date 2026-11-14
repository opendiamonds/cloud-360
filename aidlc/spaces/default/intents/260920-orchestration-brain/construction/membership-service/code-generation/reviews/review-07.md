## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-01 | Fixed | Minor | `membership_service.py` 的 `assert_still_has_admin` docstring 已改為只數合格管理者（第 31 列 (a)），自我降級與自我移出與停用守門口徑一致。 |
| R-03 | Fixed | Minor | `membership_backfill.py:28-37` docstring 與 `:162` 終檢訊息已移除孤兒擁有者的推測，改述剩餘數與 INSERT 例外兩類原因。 |
| R-04 | Fixed | Minor | `DEPLOY.md:1130` 已記載守門依賴 `users.authorization_status` 且需後端啟動過一次；`tests_pg` setUpClass 的註解說明為何呼叫 `_ensure_j5_schema()` 而不另寫 DDL。 |
| R-05 | Still applies | Minor | `AdminPage.tsx` 的 `handleToggleActive` 仍只以 `data.detail` 丟錯誤，不更新該列也不顯示 `failed_project_ids`（`grep failed_project_ids` 在該檔 0 命中）。屬單元外前端消費端，code-summary 已列為已接受風險，不擋本單元。 |
| R-06 | Fixed | Major | 守門已實作「除被停用者外無其他成員則放行」（`projects_losing_last_admin` 的 `projects_with_others` 條件），並有 `test_membership_lone_owner.py` 承接先停用再刪除的案例；第 21 列、第 50 列記載一致。 |
| R-07 | Fixed | Minor | `membership_facade.change_role` 升任 `project_admin` 時呼叫 `assert_can_be_promoted_to_admin`（`:387-394`），套用合格謂詞。 |
| R-08 | Fixed | Minor | `_authorize_global` 現在先判 `principal.is_approved`（`:118`），兩個橫幅方法都呼叫 `_authorize_global(principal, "view")`。 |
| R-09 | Fixed | Minor | `DEPLOY.md:1136` 已記載回填不看 `is_active` 的殘留與處置。 |
| R-11 | Fixed | Minor | `DEPLOY.md:1018-1020` 已改為不預設孤兒擁有者，與 docstring 一致。 |
| R-12 | Fixed | Minor | merge-blockers 第 31 列已登錄該批 Minor，第 50 列記載處置結果，承接者已落地。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/membership-service/code-generation/code-summary.md > 「2026-11-08 合併前必修第 66 列（C3）」四、「未解的異常」 | 間歇性 exit 139 有如實記載，但「崩潰與本列無關」的結論只靠「本輪 diff 只動 tests_pg」成立，這只能證明本次改動沒有引入崩潰，不能證明 membership 相關測試（`test_membership_*` 同屬 `discover -s tests`，同一行程載入）與崩潰無關。崩潰點未定位，log 末幾行在 `brain_gateway` 的 `ws_ready`，較像另一個單元，但沒有證據排除。traceability 的 open_items 也未登錄此異常，只有 merge-blockers 第 66 列寫了承擔者 build-and-test。 | 把措辭改為「本次改動未引入；是否與 membership 測試有關未排除」，並在 traceability 的 open_items 登錄一筆指向 build-and-test，避免只存在於敘述中。不阻擋本單元。 |
| Minor | backend/tests_pg/test_membership_concurrency.py > `test_C3_assert_can_deactivate_takes_no_lock` | 新前提有鑑別力：bob 保留成員列並停用，滿足「有其他成員」與「其他成員皆不合格」兩個判準；T2 以 `mint_principal(self.bob)` 呼叫，而 `assert_can_deactivate` 不檢查 principal 權限，故停用 bob 不影響 T2 的 principal 或 barrier（讀碼確認）。唯一弱點：bob 是否被判為不合格取決於 `is_active` 這一條，測試因此同時鎖住了 `is_active` 條件；若日後有人把前提改成別的不合格條件，註解說明已足夠，無需處理。M1（守門恆回空）與 M2（守門加鎖）兩個突變分別打在兩半，敘述與程式自洽。 | 無需動作，僅記錄查證結果。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| shasum 對最新收據 `reviewed-source-7fe4ce9a1254.tsv` 逐列重算 | 29 列全部相同，0 變 | 最新收據與現況工作樹一致。 |
| shasum 對舊收據 `reviewed-source-c87d6c7478d7.tsv` 重算 | 3 變：`tests_pg/test_membership_concurrency.py`、`frontend/src/types/api.d.ts`、`openapi.json` | 與 conductor 重算相同。前者即本輪第 66 列修改；後兩者由 commit `ff537a7` 引入，`git diff 7a50a40 ff537a7` 只涉及記憶端點的 503 與 `maxLength`，不碰本單元端點。 |
| `git diff -- backend/tests_pg/test_membership_concurrency.py` | 15 增 9 刪，僅 C3 前提、註解與診斷訊息 | 與 code-summary 敘述（`:441`、`:444-457`、`:531`）一致。 |
| `membership_service.py` 狀態 | `git status` 無變動，sha256 `a9b00ca0…7230` | 確認未動，與記載一致。 |
| plan `git diff HEAD` | 只新增 §十（11 行），無任何刪除行；`[x]` 75、`[ ]` 9 | 既有內容只有勾選字元與 HEAD 一致；未勾 9 格理由（計畫字面已被 Step 15a／15c 改寫、`database.py` diff 為空不成立）仍成立，無需勾選。 |
| 測試執行 | 未執行（依限制） | 本輪只以讀碼推演；實跑證據沿用 code-summary 的 `tests_pg` 15 案與突變紀錄。 |

### Summary

第 66 列只改 C3 的測試前提，兩半鑑別力都保留，`membership_service.py` 未動，收據與計畫勾選與記載相符；先前開放發現除單元外前端的 R-05 外皆已修正。唯一值得追蹤的是間歇性 segfault 的歸因措辭過強，已列為 Minor。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | backend/services/membership_service.py > `admin_count_after` / `assert_still_has_admin`（自我降級、自我移出路徑） | 停用守門與改選已改用「合格」口徑（啟用、已核准、全域 K3.edit），但自我降級與自我移出仍用原始管理者列數。專案有兩位管理者 A（合格）與 B（已停用或只有 K3.view）時，A 降級自己或移出自己會被放行，之後專案沒有任何能執行管理動作的人。這兩條路徑也沒有後續的自動改選補位（改選只在停用時觸發）。docstring 說這兩條路徑「仍以本函式擋下管理者數歸零」，與第 1 項要消除的「實際無人能管」狀態不一致。 | 在 code-summary 或 docstring 如實記載這個殘留（歸零守門數的是原始列數，不是合格者），或在後續單元把 `assert_still_has_admin` 也改用同一個 `is_qualified_successor`。不阻擋本單元。 | Unresolved |
| R-02 | Minor | backend/services/membership_service.py > `reselect_for_project` 的 `no_qualified_candidate` 分支；backend/services/user_router.py > `update_user_active` 重送路徑 | 守門通過之後、改選之前，唯一的合格接手人若被停用（`OPEN-N19-2` 已承認的窗口），或對已停用帳號重送時守門不重跑，`reselect_for_project` 只記 INFO 並回 `None`。端點仍回 200，`failed_project_ids` 為空，專案實際沒有可運作的管理者。這與第 10 項「失敗不得無聲」的目標相悖，而且 500 本體叫操作者「重送補跑」，對這個分支重送也補不了。 | 至少讓該分支改記 WARNING 並寫進 code-summary 的殘留限制。若要堵住，把「他是管理者卻無合格候選」也計入 `failed_project_ids`（需另定義 500 本體語意，宜與使用者確認）。 | Resolved (reviewer) |
| R-03 | Minor | backend/services/membership_backfill.py > `run_backfill` 終檢失敗訊息；模組 docstring「持續性失敗」 | 訊息與 docstring 把終檢失敗歸因於「某專案的 `owner_user_id` 指向不存在的使用者，使 INSERT 的外鍵失敗」。但 `schema_rbac.sql:348` 的 `projects.owner_user_id` 是 `NOT NULL REFERENCES users (id)`，孤兒擁有者在資料庫層本就不可能存在。真正失敗時（例如 `role` CHECK、並行啟動撞唯一約束），操作者會被導去查一個不存在的資料問題。啟動失敗會觸發部署回滾與重啟迴圈，診斷訊息誤導的代價比一般 log 高。 | 改成不預設單一原因的訊息（列出 `remaining` 數與實際 INSERT 例外），或刪掉孤兒擁有者的推測。 | Unresolved |
| R-04 | Minor | backend/tests_pg/test_membership_concurrency.py > `setUpClass`（呼叫 `database._ensure_j5_schema()`）；schema_rbac.sql > `users` | 守門現在讀 `users.authorization_status`，但 `schema_rbac.sql` 的 `users` 沒有這一欄，它只由後端啟動時的 `_ensure_j5_schema()` 補上。測試因此依賴一個私有函式（且該函式吞掉失敗，測試靠事後查 information_schema 補救），也代表只套用 `schema_rbac.sql` 的環境（含 CI 的 `concurrency` job 本身）無法獨立跑守門。這是既有的 schema 與啟動補丁分家，本單元把它變成新的硬依賴。 | 在 `DEPLOY.md` 與 code-summary 明記「守門依賴 `users.authorization_status`，需後端啟動過一次」，或讓 `schema_rbac.sql` 補上該欄（`IF NOT EXISTS`）。測試呼叫私有函式的風險可接受，建議留一行註解說明為何不另寫 DDL。 | Unresolved |
| R-05 | Minor | frontend/src/pages/AdminPage.tsx > `handleToggleActive`（`!res.ok` 分支，單元外的消費端） | 停用端點新增 500／503，且此時帳號已停用。前端只以 toast 顯示 `detail`，不更新該列，列仍顯示「啟用中」，也不顯示 `failed_project_ids`。操作者要自己判斷「再按一次停用」才是補跑，且畫面與資料庫狀態不一致。code-summary 已如實記載這是讀碼推得、未用 e2e 驗證。 | 在本 intent 的前端單元（或後續）排入：500／503 時就地把該列標為已停用並顯示失敗專案。至少把它列為合併前的已知限制，並補一個 e2e 或手動案例。 | Unresolved |
| R-06 | Major | backend/services/membership_service.py > `projects_losing_last_admin`（`:573-636`）；backend/services/user_router.py > `update_user_active`、`delete_user`（`:1100`、`:1170` 附近的「請先停用帳號後再刪除」）；backend/tests/test_membership_endpoints.py > `test_E6` | 只有自己一位成員的專案（建立專案或回填後，擁有者就是唯一的 `project_admin`，包含每位持圖使用者的預設專案）會讓擁有者無法被停用：守門找不到合格接手人而回 409，`E6` 的前半段就是這個情形。刪除端點又要求帳號必須先停用，所以這類使用者既停用不了也刪除不了。`hierarchy-data` 合併前必修第 3 項「空預設專案隨使用者清除」要處理的正是這種使用者，但它的前置條件（已停用）在本單元落地後無法達成。平台管理員不是專案成員，沒有任何覆寫入口。整個設計文件與 code-summary 都沒有提到這個交互。 | 向使用者確認處置並寫進產出，二選一：(a) 守門對「無圖、無其他成員的預設專案」放行，並讓改選或刪除路徑處理該專案；(b) 明確記為已知限制，並提供平台管理員可用的出口（例如先移除擁有者的成員列，或刪除空專案的端點）。無論選哪個，都補一個「僅自己一位成員的預設專案擁有者，先停用再刪除」的端到端測試。 | Unresolved |
| R-07 | Minor | backend/services/membership_service.py > `assert_invitee_has_global_permission`（`:829-875`，只要 `K3.view`）；`set_member_role`／`change_role`（`membership_facade.py:339-402`） | 邀請時角色可直接指定為 `project_admin`，改角色也可把停用、待核准或只有 `K3.view` 的成員升為管理者，兩條路徑都不檢查 `is_qualified_successor`。這類「名義管理者」會被 `admin_count_after` 當成有效管理者，使 R-01 的自我降級放行更容易發生（專案剩一位真管理者加一位名義管理者，真管理者降級自己後，沒有人能執行管理動作）。 | 對升為 `project_admin` 的目標套用 `is_qualified_successor`（只限 `role == project_admin` 的寫入），或把 `admin_count_after` 改為只計合格者，並同時解掉 R-01。至少在 code-summary 如實記載。 | Unresolved |
| R-08 | Minor | backend/services/membership_facade.py > `_authorize_global`（`:101-119`）、`list_my_pending_reselections`、`acknowledge_reselection` | 同為 facade 的 `HierarchyFacade`、`MemoryFacade`、`RequirementFieldFacade` 都以 `principal.is_approved` 先擋待核准帳號，本 facade 的 `_authorize_global` 呼叫 `user_can` 時不帶 `authorization_status`，橫幅兩個方法更完全沒有授權檢查。目前唯一呼叫端是已有 `require_story_action` 的 router，所以不可被利用；但 K-16 的同進程呼叫端（大腦側）若直接呼叫，防線只剩 `_assert_project_exists` 內部轉換出的 404，橫幅方法則沒有。 | 在 `_authorize_global` 與兩個橫幅方法開頭加 `principal.is_approved` 檢查，行為與其他三個 facade 一致，並補一個待核准 principal 的 deny 測試。 | Unresolved |
| R-09 | Minor | backend/services/membership_backfill.py > `_BACKFILL_SQL`（`:76-82`）；`reselection_scope`（`membership_service.py:1034-1047`） | 回填對每個零成員專案一律把擁有者寫成 `project_admin`，不看帳號是否已停用。已停用帳號擁有的專案因此取得一位停用的管理者，而自動改選只在「停用動作」時觸發，這些專案永遠不會被改選，也沒有人能管理它們。屬一次性資料狀況，影響僅限啟動時已存在的停用擁有者專案。 | 回填完成後列出「唯一管理者已停用」的專案數（log 或 `--dry-run` 輸出），或對這些專案跑一次改選。至少在 `DEPLOY.md` §2.2.10 記載這個殘留。 | Unresolved |
| R-10 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/membership-service/code-generation/code-summary.md > 「與已核可計畫／測試說明的落差」末段 | 摘要寫現有測試數為 data 11、facade 14、endpoints 13（共 38），本輪實跑這三個模組為 41 個測試，數字對不上。另外 8 格未勾的計畫格依賴「本檔為準」的說明，審閱者必須自行對照才能知道哪些突變驗證沒有重跑。 | 以實跑輸出重數並更正測試數；在摘要列出未重跑突變驗證的格子與其最近一次紀錄的位置。 | Resolved (reviewer) |
| R-11 | Minor | DEPLOY.md > 2.2.10（第 959 行，約 951 到 1073 行）回填失敗處置說明 | 該行寫補齊失敗的處置通常是「某專案的 owner_user_id 指向不存在的使用者」，但 projects.owner_user_id 有外鍵，孤兒擁有者在資料庫層不可能存在。後端啟動失敗會造成重啟迴圈，操作者會被導去查不存在的資料問題。這與 R-03 同源，但出現在部署文件而不只是 docstring，而且 code-summary 的 R-03 處置只提到 docstring | 把 DEPLOY.md 該句改為不預設單一原因，指向終檢訊息中的剩餘數與實際 INSERT 例外，並與 docstring :28-29 一併修正，建議併入 merge-blockers 承接 R-03 的列 | New |
| R-12 | Minor | code-summary.md > 第五節（R-01 與 R-07 承接方向）與 merge-blockers.md | 七項 Minor 的承接寫成「由 conductor 併入 merge-blockers」，但本輪 merge-blockers 第 1 到 30 列並無對應列，目前沒有任何落地的承接者。若 conductor 未實際併入，七項只存在於單元摘要中 | 在本輪收尾前確認 conductor 已把七項實際寫入 merge-blockers，或在 code-summary 明記尚未登錄，避免已知限制無人追蹤 | New |

> R-01 Not re-checked this round

> R-03 Not re-checked this round

> R-04 Not re-checked this round

> R-05 Not re-checked this round

> R-06 Not re-checked this round

> R-07 Not re-checked this round

> R-08 Not re-checked this round

> R-09 Not re-checked this round

> R-11 Not re-checked this round

> R-12 Not re-checked this round
