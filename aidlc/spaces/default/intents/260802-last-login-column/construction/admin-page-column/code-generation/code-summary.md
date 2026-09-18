# Code Summary — admin-page-column（U3）

## 實際產出

| 檔案 | 變更 |
|---|---|
| `frontend/src/components/LastActivityCell.tsx` | **新增 73 行** |
| `frontend/src/components/PaginationControl.tsx` | **新增 128 行** |
| `frontend/src/pages/AdminPage.tsx` | **+385／-162**（大幅改寫） |
| `frontend/tests/e2e/regression.spec.ts` | `+116`：五個新 case ＋ 修復一個既有失效 case |

## 三個關鍵實作決定

**1. 三種抓取路徑，三種畫面行為，互不共用旗標**

既有程式碼只有一個 `isLoading`。沿用它做切頁 → 控制項在游標下消失、鍵盤焦點退回頁面主體（AC-5.10 必然失敗）；沿用它做刪除後的背景重抓 → 每刪一列整張表閃一次載入。故新增 `isBusy`，並讓第三種**不設任何旗標**。

**2. 分頁控制渲染在容器之外**

結構前提。既有的 `isLoading ? … : error ? … : (…)` 三元式替換的是**整個容器內容**。

**3. 三處整份重抓皆已改**

`:113`（啟停用）、`:129`（刪除）、`:91-94`（角色調整失敗）—— 漏改任一處，該路徑就會把頁次拉回第 1 頁，而其餘路徑正確（這種部分正確最難在人工測試中發現）。刪除另以目前頁次**背景**重抓補回 offset 位移。

## reviewer 查出並已修正的實作缺口

**正規化契約在文件裡是硬性規則，程式碼裡完全沒有** —— 資料從 `res.json()` 直接流到元件 props。已在 `applyPage` 與啟停用的落地點補上。

推翻的錯誤推論：「產生的型別已宣告必填，所以不需要執行期正規化」。型別是**編譯期**保證，`res.json()` 回 `any`、`as UserListPage` 只是斷言 —— 後端映像比前端舊時（`DEPLOY.md` 2.2.4 已警告的情境），欄位就是 `undefined` 而型別系統不會知道。

## 驗證結果

| 項目 | 結果 |
|---|---|
| `npm run lint` | **0 errors**（3 個 warning 為既有，未新增） |
| `npm run build`（含 `tsc -b`） | 通過 |
| Playwright e2e | **11/11 通過**（本 intent 前為 6 個，其中 1 個實際已失效） |

e2e 在本機的短生命週期 stack（`deploy/docker-compose.test.yml`，PostgreSQL ＋ 真實後端 ＋ nginx）上實跑，非僅列出。

## 一併修復的既有失效 case（非本 feature）

「Developer 看不到系統管理區」自 J5 授權流程（`f5214c9`）起就在失敗 —— 該 commit 把註冊按鈕改名並讓新帳號落在 `/waiting-approval`，而測試仍寫在 pre-J5 的行為上。`ui-regression` 是真閘門，不修的話本 PR 會因與本 feature 無關的原因紅燈。只更新按鈕文字與目的地，RBAC 的檢查意圖不變。

## Review — 實作審查（五單元）

> **修正紀錄（READY 後補，2026-08-11）—— 2 Major ＋ 5 Minor 全數已修正並重新驗證**
>
> - **Major 1**（`DEPLOY.md` §2.2.5 的 psql 期望值 `system_seed` 與程式碼實際寫入的 `system_patch.j3a_view` 不符，而那是本次權限變更在既有環境**唯一**的人工驗證依據）：已更正期望值，並補上「若看到 `system_seed` 或空值且 `can_view` 為 `f`，表示補丁**沒有執行**」的判讀指示。
> - **Major 2**（US-5 的 DoD 明列 5 個由 e2e 驗證的子句，實際交付的 5 個 case 一個都沒覆蓋）：**新增 3 個 e2e case 並擴充 1 個**，五個子句現在全部有實際通過的斷言 —— AC-5.10 以 `page.route` 延遲清單回應、在回應抵達前斷言 nav 仍可見且 `aria-busy="true"`；AC-5.9 以 `focus()` ＋ `toBeFocused()` ＋ `press('Enter')` 驗鍵盤可達與**可觸發**；AC-5.6 的刪除子句實走「停用 → 刪除 → 斷言仍在第 2 頁 ＋ 總筆數遞減」；AC-5.4 的 UI 子句以路由改寫強制超出範圍的頁次，斷言空態文字、分頁控制仍在畫面上、且「回到第 1 頁」可用；AC-5.7 的小螢幕子句擴充為斷言 `aria-current` 為 `[1]` 與總筆數。**e2e 由 11 個增為 14 個，全部在真實 docker stack 上通過。**
> - **Minor 3**（`should_record_activity()` 在 `try` 之外，例外會讓每個已認證端點回 500）：已移入 `try` 內。
> - **Minor 4**（`requestSeq` 併發保護只覆蓋成功分支，與程式碼註解的宣稱不符）：三條路徑的 `.catch` 皆已加上序號檢查。
> - **Minor 5**（`handleRoleChange` 只套 `role`，未套回應中重算的兩個欄位）：已改為套用整個回應，與 `handleToggleActive` 一致。
> - **Minor 6**（`page > totalPages` 的過渡態下沒有任何按鈕帶 `aria-current`／方括號）：`pageSequence()` 已把超出範圍的目前頁次納入序列。
> - **Minor 7**（U2 code-summary 自陳 16 個端點測試，實為 17）：已更正為實測值。
>
> 以下 Review 內文保留原判定時的觀察，不回改。

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-11T03:17:48Z
**Iteration:** 1

**審查範圍**：`git diff ut..HEAD`（7 commits）涵蓋的五個工作單元（backend-activity-policy／user-object-serialization／security-reviewer-permission／admin-page-column／api-type-contract）的實際程式碼與測試，對照 `inception/user-stories/stories.md` US-5（11 條 AC）、`inception/application-design/decisions.md` AD-1〜AD-12、`team.md ## Code Style`、`phases/construction.md`。以對抗立場逐檔精讀，並實跑驗證，不只讀 code-summary 的自述。

### 事實查證

| # | 項目 | 查證方法 | 結果 |
|---|---|---|---|
| 1 | 後端全套測試數與各單元自陳數字一致 | `python -m unittest discover -s tests -v`（backend/） | **通過，140/140**。94（既有）＋19（`test_activity.py`）＋17（`test_user_list_endpoint.py`，見查證 #12）＋10（`test_j3a_view_permission.py`）＝140，與各單元 code-summary 加總相符 |
| 2 | OpenAPI 規格漂移 gate | `DATABASE_URL=... JWT_SECRET=... python scripts/dump_openapi.py --check`（backend/） | **exit 0**，「規格檔與後端程式碼一致」 |
| 3 | 前端型別漂移 gate | `npm run check:types`（frontend/） | **exit 0**，「API 型別檔與規格檔一致」 |
| 4 | 前端 lint | `npm run lint`（frontend/） | **0 errors**，3 個既有 warning（`AssessmentPage.tsx`／`LoginPage.tsx`／`WorkspacePage.tsx` 皆為 `exhaustive-deps`），與 `team.md` 記載的既存基準一致，未新增 |
| 5 | 前端建置（含 `tsc -b`） | `npm run build`（frontend/） | **通過**，248 modules，`dist/` 產出正常 |
| 6 | `_apply_security_reviewer_j3a_view()` 真實 PostgreSQL 行為與 DEPLOY.md §2.2.5 驗證指令的期望值 | 起真實 `deploy/docker-compose.test.yml` stack（PostgreSQL＋backend＋nginx），`docker compose exec db psql -c "SELECT ... role_permissions WHERE role='Security_Reviewer' AND story_id='J3a'"`，並讀 backend 啟動日誌 | **DEPLOY.md 的期望值與實測不符**（見 Finding #1）。實際：`can_view=t`、`updated_by` 為空字串／NULL；啟動日誌為「J3a 權限套用：已跳過（Security_Reviewer/J3a 已為可檢視）」——因 `schema_rbac.sql` 已直接 seed `true`，走的是「已跳過」分支（不寫 `updated_by`），既非 DEPLOY.md 宣稱的 `system_seed`，也非「已套用」分支會寫入的 `system_patch.j3a_view`（後者由 `test_applies_when_row_is_still_seed_written` 獨立佐證，斷言的是 `J3A_PATCH_MARKER` 不是字面 `"system_seed"`） |
| 7 | `users.last_activity_at` 欄位與 `record_activity()` 端到端行為 | 同一 stack：`\d users`、`curl` 登入取得 token、`GET /api/auth/list` 前後比對、直接查 `SELECT username, last_activity_at FROM users WHERE username='admin'` | **成立**。欄位存在且型別正確（`timestamp with time zone`）；登入後的下一次已認證請求（`GET /api/auth/list`）確實把 `admin` 的 `last_activity_at` 寫回 DB，API 回應值與 DB 值逐字相符（`2026-08-11T03:17:00.575853Z`） |
| 8 | AC-5.4「頁次超出範圍」的線上契約 | 同一 stack：`curl` 對 `page=最後一頁+1` 發請求 | **成立**。回 200、`items: []`、`page` 回顯請求值（46）、`total` 不變（45），不夾頁 |
| 9 | Playwright e2e 全套（非僅讀 code-summary 的宣稱） | `BASE_URL=http://localhost:8090 npx playwright test`（frontend/，對真實 docker stack） | **11/11 通過**，與 U3 code-summary「11/11 通過」的自陳數字一致 |
| 10 | US-5 stories.md 的 DoD 表格「逐條指派驗證者」是否真的有對應 e2e case | `grep` `regression.spec.ts` 全檔比對 DoD 表指名的斷言形狀（`dialog`／`confirm`／刪除按鈕、`keyboard`／`Tab`／`toBeFocused`、`route`／`waitForResponse`／延遲攔截） | **五項 DoD 指名要 e2e 覆蓋的子句零命中**：無任何測試觸發刪除（`confirm()` 對話框）、無鍵盤 Tab 測試、無網路延遲/攔截測試。詳見 Finding #2 與下方 AC 對照表 |
| 11 | `min-w-11`／`min-h-11` 是否等於 44px（AC-5.9 觸控尺寸） | 讀 `frontend/dist/assets/index-*.css` 的 `.min-w-11` 規則與 `--spacing` 變數 | **成立**。`--spacing: .25rem`，`min-w-11 = calc(.25rem * 11) = 2.75rem = 44px` |
| 12 | U2（`user-object-serialization`）code-summary 自陳「16 個端點測試通過」 | `python -m unittest tests.test_user_list_endpoint -v \| grep -c "^test_"`（backend/） | **實際為 17，非 16**（`UserListEndpointTest` 15 個 ＋ `UserMutationEndpointTest` 2 個）。後端全套 140 的加總本身正確（見查證 #1），僅此單檔子計數有誤，屬 Finding #7 |
| 13 | `record_activity()` 的例外邊界 | 讀 `backend/services/activity.py:82-101` 逐行核對 try 區塊範圍 | `should_record_activity()`（L89）呼叫在 `try:`（L91）**之外**。見 Finding #3 |
| 14 | 前端 `requestSeq` 併發保護是否覆蓋三條抓取路徑的**失敗**分支 | 讀 `AdminPage.tsx` 三個 `.catch()`（L93／L110／L120）逐一核對是否有 `seq === requestSeq.current` 守衛 | 三者皆**無**。成功寫入（`.then`）三處皆有守衛，失敗分支（`setError`／`showToast`）皆無。見 Finding #4 |

### US-5 逐條 AC 對照

| AC | 程式碼是否滿足 | 若不滿足／未覆蓋，什麼測試會抓到 |
|---|---|---|
| AC-5.1（每頁筆數固定為 20 且小於總數） | **滿足**。`DEFAULT_PAGE_SIZE=20`，`user_router.py` 的 `.limit(page_size)` | `test_page_size_bounds_the_response` 已覆蓋；若違反該測試會紅 |
| AC-5.2（total／page／page_size 三值各自正確，含少於一頁情境） | **滿足** | `test_total_is_a_separate_count_not_len_items`、`test_three_pagination_values_correct_when_fewer_than_one_page` 已覆蓋 |
| AC-5.3（切頁無重複無遺漏、順序穩定） | 端點層**滿足**；e2e 端到端子句**弱化覆蓋**——僅斷言「第 1 頁與第 2 頁文字不相等」，未逐字驗證「無重複、無遺漏」 | 後端：`test_pages_do_not_overlap_and_cover_everything`、`test_same_page_twice_returns_same_order`。前端若真的重複／遺漏但兩頁文字仍不同，現有 e2e 斷言**不會**發現 |
| AC-5.4（超出範圍：200＋空清單＋頁次回顯；UI 空態＋分頁控制仍可用） | 後端契約**滿足**（並經真實 stack 驗證，事實查證 #8）；**UI 空態與返回入口子句 DoD 指名 e2e 驗證，但沒有對應測試** | `test_out_of_range_page_is_success_empty_and_echoes_page` 覆蓋後端；但 `AdminPage.tsx:290-301` 的「這一頁沒有資料／回到第 1 頁」分支與其外部的 `PaginationControl` 若被破壞（例如誤把它塞回容器內、或拿掉回頁 1 連結），**沒有任何自動化測試會發現** |
| AC-5.5（非法參數不進查詢層，422 不含帳號資料） | **滿足** | `test_illegal_parameters_are_rejected_without_leaking_data`、`test_negative_values_never_reach_the_query_layer` |
| AC-5.6（頁面內處置後仍停在原頁次；就地更新；刪除各自同理；失敗不彈回第 1 頁） | 「啟停用」子句經 e2e 覆蓋；**「刪除」子句（AC 本文特別點名的既有整份重抓行為變更）沒有任何 e2e 覆蓋**；「角色調整」子句的 e2e 只在第 1 頁（未切頁）執行，未驗證非首頁時是否維持頁次 | 若 `handleDelete`／`resyncCurrentPageInBackground`（`AdminPage.tsx:171-189`）的 `isBusy`／`isLoading` 隔離或 `requestSeq` 併發保護（AD-12 的核心設計）壞掉，**沒有任何自動化測試（backend 或 e2e）會發現**——前端完全無 unit 測試框架（`team.md` 已記載），e2e 又未觸及刪除 |
| AC-5.7（兩種佈局皆可跳頁、皆呈現頁次/總筆數/上下頁、邊界處置一致） | 桌面**滿足**（e2e test 3 隱含驗證跳頁）；**小螢幕的「可跳至特定頁次」「切換後取得的帳號集合相同」子句沒有 e2e 覆蓋**——mobile e2e（test 5）只驗證卡片版面出現與導覽列可見，未點擊任何分頁按鈕 | 若小螢幕的分頁按鈕在 `<768px` 斷點下失去互動性（例如被某個 CSS 規則蓋掉點擊區），現有 mobile e2e **不會發現** |
| AC-5.8（分頁切換路徑取得的欄位值與資料庫一致） | **滿足（by construction）**：`list_users` 內所有列皆經共用工廠 `_to_user_schema()`，與初次載入路徑同一段程式碼，不因 `page` 而分支 | `test_last_activity_value_matches_database_not_just_key_present`、`test_overdue_flag_is_computed_by_backend` 佐證該工廠本身正確；沒有專門「切到第 2 頁＋斷言逾期值」的組合測試，但風險低（無獨立的第二套序列化邏輯可分歧） |
| AC-5.9（鍵盤可達可觸發／非僅顏色／焦點可見／44×44） | 「非僅顏色」「44×44」**可驗證且成立**（事實查證 #11；`aria-current` ＋ `[N]` 方括號提供非色彩線索）；「焦點可見」「輔助技術可讀」DoD 已如實記載為人工項；**「鍵盤可達與觸發」DoD 指名 e2e（`page.keyboard.press('Tab')`），但沒有對應測試** | 若分頁按鈕的 `disabled` 邏輯或 Tab 序被意外破壞，現有測試**不會發現**；且目前正式環境僅 12 個帳號（單頁），`totalPages<=1` 時所有頁碼按鈕與上下頁鍵皆 `disabled`（原生不可 Tab 到達），這個「單頁時分頁列完全不可鍵盤互動」的狀態是否符合 AC-5.9 的字面前提（「Given 分頁控制已呈現」不限單頁）本身也未經任何測試釐清 |
| AC-5.10（切頁期間分頁控制不消失、焦點不離開） | 程式碼邏輯**滿足**：`isBusy` 只替換容器內容，`PaginationControl` 渲染在容器外（`AdminPage.tsx:397-405`），與 AD-12 的定案一致；**但「分頁控制仍在畫面上」子句 DoD 指名 e2e 驗證，沒有對應測試** | 沒有任何測試用 route 攔截／延遲來檢查「回應抵達前」的畫面，故若未來重構不慎把 `PaginationControl` 移回 `isBusy` 分支內，**沒有任何自動化測試會發現** |
| AC-5.11（非分頁參數不改變結果；不存在排序/篩選 UI） | **滿足** | `test_non_pagination_query_params_do_not_change_the_result` 覆蓋前半；後半經人工核對 `AdminPage.tsx` 全檔無排序/篩選控制項 |

**小結**：11 條 AC 中 6 條（AC-5.1／5.2／5.5／5.8／5.9 部分／5.11）有完整自動化覆蓋，AC-5.3／5.7 為部分覆蓋，AC-5.4／5.6／5.9 部分／5.10 這 4〜5 條的 **DoD 明確指名要由 Playwright e2e 驗證的子句在實際交付的 5 個新 e2e case 中缺席**（見 Finding #2）。逐一核對後，這些子句對應的**程式碼本身讀起來是對的**（未發現邏輯缺陷），差距在「DoD 承諾的自動化驗證」與「實際交付的測試」之間，不是已證實的功能缺陷。

### Findings

| # | Severity | File:line | Finding | Recommendation |
|---|---|---|---|---|
| 1 | Major | `DEPLOY.md:276`（§2.2.5） | **psql 驗證指令的期望值與程式碼實際行為不符，且是本次 RBAC 權限變更在既有環境唯一的人工驗證依據。** 文件宣稱套用後 `updated_by` 應為 `system_seed`；但 `database.py:361` 明文把 `updated_by` 覆寫為 `J3A_PATCH_MARKER`（`"system_patch.j3a_view"`），並由 `test_j3a_view_permission.py` 的 `test_applies_when_row_is_still_seed_written`／`test_applies_when_row_came_from_the_sql_seed` 斷言為 `J3A_PATCH_MARKER` 而非 `"system_seed"`；經真實 PostgreSQL stack 實測（事實查證 #6），「已跳過」分支下該欄實際為空字串／NULL，兩種真實可達的結局都不是文件宣稱的 `system_seed`。操作者依文件核對會得到不符預期的結果，可能誤判套用失敗（或反之誤判為正常）。 | 把 §2.2.5 的驗證指令改為列出「已套用」（`updated_by = system_patch.j3a_view`）與「已跳過」（`updated_by` 為原值，多半是空／NULL）兩種真實可能的結局，並各自對應到啟動日誌的哪一行；不要只給單一期望值 |
| 2 | Major | `inception/user-stories/stories.md`（US-5 DoD 表）對照 `frontend/tests/e2e/regression.spec.ts` | **US-5 的 Definition of Done 明列由 Playwright e2e 驗證的 5 個子句，實際交付的 5 個新 e2e case 一個都沒覆蓋**：AC-5.4 的「UI 空態與返回入口」、AC-5.6 的「刪除」子句（AC 本文特別點名這是「今日整份重抓」的既有行為變更，也是本輪風險最集中之處）、AC-5.7 的「小螢幕可跳頁」、AC-5.9 的「鍵盤可達與觸發」、AC-5.10 的「分頁控制仍在畫面上」。逐檔 `grep` 確認：全檔零個 `confirm`／`dialog`（無刪除測試）、零個 `keyboard`／`Tab`（無鍵盤測試）、零個 `route`／延遲攔截（無忙碌態中途斷言）。U3（`admin-page-column`）的 code-summary 只寫「11/11 通過」，未如 U1／U4 一樣揭露已知的覆蓋缺口，讀起來像是完整交付。逐一手動核對相關程式碼（`handleDelete`／`resyncCurrentPageInBackground`／`PaginationControl` 的渲染位置）本身邏輯正確，此為測試完整性缺口，非已證實的功能缺陷。 | 依 DoD 表格逐項補上缺席的 5 個 e2e case（刪除＋確認對話框、`page.keyboard.press('Tab')`＋`toBeFocused`、小螢幕跳頁、以 `page.route` 延遲回應斷言忙碌態畫面），或在 code-summary／DoD 表明確記載為已知缺口並排入後續 Bolt——依 `project.md ## Testing Posture` 團隊底線 C 與 stories 本身「不得默認略過」的措辭，沉默略過不是允許的處置 |
| 3 | Minor | `backend/services/activity.py:82-91` | `record_activity()` 的 `should_record_activity(user.last_activity_at, moment)` 呼叫（L89）位於 `try:`（L91）**之外**。若它拋出例外（現況下需要 `user.last_activity_at` 不是 `datetime`／`None`，在 SQLAlchemy `DateTime` 欄位型別保證下幾乎不可能），該例外會沿 `get_current_user()` 一路往上冒，讓**每一個**已認證端點回 500——直接牴觸 AD-8「任何失敗都不得讓使用者的原始請求失敗」的明文契約。實務可觸發機率極低，但與該契約「這三點列為介面契約而非實作細節」的措辭不一致。 | 把 `try:` 往前移到涵蓋 `should_record_activity()` 呼叫，或在其外再包一層防禦性 `try/except`；`test_activity.py` 補一個以 mock 讓判定函式拋例外、斷言 `record_activity` 仍回傳且不向上冒的測試 |
| 4 | Minor | `frontend/src/pages/AdminPage.tsx:93,110,120` | 三條抓取路徑的 `requestSeq` 併發保護（AD-12「併發保護」段的定案）**只覆蓋成功寫入（`.then` 內的 `applyPage`），未覆蓋失敗分支**：`useEffect`（L93）與 `handlePageChange`（L110）的 `.catch` 直接呼叫 `setError(...)`、`resyncCurrentPageInBackground`（L120）的 `.catch` 直接呼叫 `showToast(...)`，皆未檢查 `seq === requestSeq.current`。程式碼註解宣稱「只有『最後發出』的抓取回應能寫入 state」，但 `setError` 本身就是一次 state 寫入，這裡並未被守衛涵蓋。經逐一推演三條路徑的實際互動（`isBusy`／`isLoading` 會在忙碌期間隱藏刪除鍵與分頁鍵，天然阻止大多數重疊觸發），在目前 UI 下要讓「較舊請求的失敗覆寫較新請求的成功」實際發生，需要 token 中途變更等非典型路徑，正常點擊操作下難以觸發；`resyncCurrentPageInBackground` 的失敗分支雖可經「連續刪兩列」等真實操作重疊觸發，但後果僅止於一則可能多餘的 toast，不影響已正確顯示的資料。 | 在三個 `.catch` 內比照 `.then` 加上 `seq === requestSeq.current` 守衛，讓程式碼行為與註解宣稱的不變量一致；不需為此新增測試（前端無 unit 測試框架），但建議在 e2e 的「連續刪除」情境（若依 Finding #2 補上）順帶斷言不會出現非最新的錯誤畫面 |
| 5 | Minor | `frontend/src/pages/AdminPage.tsx:123-141`（`handleRoleChange`） | 角色調整成功後的樂觀更新只套用 `role` 欄位（`{...u, role: newRole}`），未如同檔 `handleToggleActive`（L156-160）一樣，把 PUT 回應中重新計算的 `last_activity_at`／`is_overdue` 一併套用回該列。由於角色調整不會改變目標使用者自身的 `last_activity_at`（記錄活動的是發出請求的管理員，不是被調整角色的目標使用者），此差異在絕大多數情況下無感；唯一會露餡的情境是該筆帳號恰好在使用者停留於本頁期間跨過 90 天逾期門檻，此時畫面上的 `is_overdue` 會短暫落後於後端「此刻」會算出的新值，直到下一次重抓或重新整理。 | 比照 `handleToggleActive` 的形狀，把 `handleRoleChange` 的樂觀更新也改為套用完整回應（含正規化 `last_activity_at`／`is_overdue`），維持兩個相似操作的處理形狀一致 |
| 6 | Minor | `frontend/src/components/PaginationControl.tsx:23-35,92-107` | `pageSequence(current, totalPages)` 只依 `totalPages` 產生頁碼清單。當 `page > totalPages`（AD-12 明文承認的過渡態：刪掉某頁唯一一列後，重抓完成前 `page` 仍是舊值）時，頁碼清單裡不會有任何一個按鈕的 `entry === page` 成立，因此沒有任何按鈕會帶上 `aria-current="page"` 或 `[N]` 方括號——「目前頁次」在這個過渡態失去視覺與 AT 可讀的指示，直到使用者點「上一頁」或空清單態的「回到第 1 頁」連結。使用者仍能正常復原，非阻斷性缺陷。 | 可選：`page > totalPages` 時額外渲染一個停用、帶 `aria-current` 的頁碼（顯示過渡態的請求頁次），或在該過渡態直接以文字告知「目前頁次已不存在」；影響小，不強制此輪修正 |
| 7 | Minor | `construction/user-object-serialization/code-generation/code-summary.md:22` | 該單元 code-summary 自陳「16 個端點測試通過」，實際執行 `test_user_list_endpoint.py` 為 **17** 個測試（`UserListEndpointTest` 15 個 ＋ `UserMutationEndpointTest` 2 個，事實查證 #12）。後端全套「140」的加總本身正確，僅此單檔子計數有誤，屬單純的計數疏失。 | 更正 U2 code-summary 的子計數為 17；不影響任何驗證結論 |

### Summary

五個單元的核心行為（活動時間記錄與節流、逾期判定、分頁契約、RBAC 目標式套用、OpenAPI↔TypeScript 漂移 gate）皆已用真實 PostgreSQL stack 與線上 API 逐一實測，未發現任何已證實會在正常操作下發生的執行期錯誤：140 個後端測試、11 個 Playwright e2e、兩道漂移 gate、lint 與 build 全數在本輪重新驗證通過，且 `record_activity`／`_apply_security_reviewer_j3a_view`／頁次超出範圍三項關鍵路徑額外經真實部署環境的端到端手動核對確認正確。0 Critical。2 Major：其一是 `DEPLOY.md` 對一項安全相關（IAM 權限授予）變更的唯一部署後人工驗證指令給出經證實錯誤的期望值；其二是 US-5 story 自己的 Definition of Done 表格點名要由 e2e 驗證的 5 個子句（尤其是本輪風險最集中的「刪除後重抓」路徑）在實際交付的測試裡缺席，且 U3 的 code-summary 未如其餘單元一樣揭露此缺口。其餘 5 項 Minor 集中在契約嚴謹度（例外邊界、併發守衛的宣稱與實作有落差）與計數/文件精確度，均非阻斷性。依「0 Critical、≤2 Major 不擋 READY」的裁決規則，本輪判定為 READY，但兩項 Major 建議在合併前一併處理，尤其是 Finding #1（會直接誤導部署後的人工核對）與 Finding #2（刪除路徑目前完全沒有自動化保護網）。
