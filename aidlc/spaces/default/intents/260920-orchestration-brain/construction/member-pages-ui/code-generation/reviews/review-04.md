## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-25T14:50:41Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | `frontend/src/pages/MemberDetailPage.tsx:46`、`:137-139`、`:170-173`、`:207`；`frontend/src/pages/MembersListPage.tsx:43`、`:124-128`、`:171` | 單一 `error` state 同時承載**抓取失敗**與**寫入失敗**，而主要內容的渲染條件是 `!error`。後果：任何寫入路徑的失敗都會把整頁內容卸載，**而清除 error 的唯一途徑（控件本身）就在被卸載的那個區塊裡**，因此是不可復原的死態，只能離開該頁。最可達的路徑不是 403 而是暫時性網路失敗：`changeMemberRole` 的 catch 丟 `Error('連線失敗')`（`membershipApi.ts:250-252`）→ `MemberDetailPage.tsx:137-139` `setError` → `:207` 的 `{!isLoading && !error && member && (...)}` 整塊消失（成員姓名、角色區、守門回報、變更紀錄、移出鈕一起不見）。清單頁同形：邀請 403 → `handleForbidden` → `:171` 的表格消失，而 `canManage` 仍為真故「邀請成員」鈕**還留著**，使用者得到一個沒有清單、只有邀請鈕的頁面。這一項不在 `code-summary.md` §四 的七項自述內，也沒有任何 e2e 斷言；`functional-spec.md:176` 只要求「清單頁顯示『你沒有管理這個專案的權限』」，沒有要求清掉清單 | 把寫入錯誤與抓取錯誤分成兩個 state：寫入錯誤渲染在控件旁、不參與主要內容的 `!error` 閘；或在每次使用者互動開始時清掉它並確保清除入口不被卸載 | Resolved (reviewer) |
| R-02 | Major | `frontend/src/components/membership/ReselectionBanner.tsx:62`、`:179`、`:194-196` | `BR21.3` 的永久失敗閂 `bannerForbiddenInThisSession` 是模組層布林值，**不綁任何身分**。而本 repo 的登出是純 state 清除（`AuthContext.tsx:56-61`）＋ `Sidebar.tsx:11-13` 的 `navigate('/login')`，**不重新載入文件**；登入同樣走 `navigate`（`LoginPage.tsx:105-107`）。故在同一個分頁內「使用者 A 收到 403 → 登出 → 使用者 B 登入」之後，B 的橫幅查詢永遠不發出，`US12.4`／`AC12.4.3` 的通知對 B **靜默消失**且無任何可觀察訊號（該路徑刻意不顯示錯誤）。元件 docstring 只承認「整頁重新載入時會重置」，未涵蓋換使用者這一面 | 把閂改為以身分為鍵（例如 `let forbiddenForToken: string \| null`，effect 內比對當前 token），或在 token 變更時重置。零新依賴、不觸碰 `NFR4.80` 的瀏覽器儲存禁令 | Resolved (reviewer) |
| R-03 | Major | `aidlc/.../code-generation/code-summary.md` §四 F-4／F-5／F-6／F-7；`frontend/tests/e2e/member-pages.spec.ts` 全檔 | 五條已實作規則零斷言（`BR21.3` 的 403 閂、`BR23.1` 的字串 `detail` 拒絕態、`BR24.2`、`BR26.2`、`BR26.3`），理由是「8 個案例由 `cicd-pipeline.md` §五 固定」＋「案例名稱是 TCMS 的鍵」。**兩個理由逐字核對後都不成立**：§五 的標題是「本單元**需要新增**的 e2e 案例」——那是下限清單，不是上限；而 `ui-regression.lock.yml:568` 的註解逐字約束的是 `--summary-template` 不得改（`changing it orphans the old cases`），**新增一個 test 只會新建一個 TCMS 案例，不會讓既有案例變成孤兒**。最要緊的是 `BR26.3`：它是審查 `R-02` 修掉「橫幅永遠清不掉」那條 Critical 的規則，而 `team.md` 記載前端**唯一**的自動化層就是 Playwright e2e，故它目前的迴歸保護是零。其構造成本極低（既有 dispatcher 已可按 method／path 分流，只需三筆事件 ＋ 令其中一筆回 500 ＋ 再按一次） | 至少為 `BR26.3` 補一個案例（名稱一旦合併即凍結，故一次定名）；或把「§五 是上限」這個讀法明白提交使用者在閘門上採納，而不是以一個不成立的機械約束當理由 | Resolved (reviewer) |
| R-04 | Minor | `frontend/src/pages/MembersListPage.tsx:105`；`frontend/src/pages/MemberDetailPage.tsx:94`；`nfr-design/security-design.md` §一 的「專案層角色」列 | `canManage` 的第一段以 `ownRole === 'project_admin' \|\| ownRole === 'project_owner'` 放寬，而 `project_owner` 這個值**在資料庫層不可能出現**：`models.py:585-587` 與 `schema_rbac.sql:597-598` 的 `ck_project_members_role` 把 `project_members.role` 限定為 `('project_admin','member')`，且 `membership_types.py:41` 逐字說 owner 是 `projects.owner_user_id` 承載的**專案屬性、不是成員角色**。`security-design.md` §一 把 `project_owner` 列為「`MemberView.role` 可讀的對應來源」之一——**那個前提是假的**。這是授權述詞裡的一個死分支：若那條 CHECK 日後被放寬，它會讓一個非 `project_admin` 的角色值取得管理者控件，而伺服器對三個寫入端點都要求 `project_admin`（`membership_facade.py:138-160`），正是 §一之三 設立兩段式要消除的那類永久 403。**無功能損失**（已查證 `POST /api/hierarchy/projects` → `create_project_with_owner` 在同一交易把建立者寫成 `project_admin`，`membership_facade.py:425-465`，故 `AC12.1.1` 成立），因此只記 Minor | 移除該 disjunct，或在程式與 `security-design.md` §一 寫明它是刻意的防禦性冗餘並附 CHECK 的引用；不要讓一個不可達值在設計文件裡看起來像一個真實的角色來源 | Resolved (reviewer) |
| R-05 | Minor | `frontend/tests/e2e/member-pages.spec.ts:373`、`:410` | 兩處「恰 N 次請求」用 `expect.poll(...).toBe(n)`。`expect.poll` 在**第一次**觀測到相符值時即通過，故它不是 settled-count 斷言。`:373` 的移出差額「恰為 1」在突變（`handleRemove` 自己多抓一次）之下，序列是「重抓 → +1」再「清單頁掛載 → +2」；若 poll 在兩者之間取樣就會看到 1 而**綠燈**。m3 回報 RED 可信（route 全部被攔截、兩個請求幾乎同時落地，首次取樣即為 2），但該偵測力依賴時序而非斷言結構 | 改為「先等到可判定的終點（例如 `waitForResponse` 等到清單頁掛載那次回應）再以一般 `expect` 斷言計數」，或 poll 之後加一次穩定期複驗 | Resolved (reviewer) |
| R-06 | Minor | `frontend/tests/e2e/member-pages.spec.ts:364-373`（案例 3 第 ③ 段）、`:150-170`（`setupApp` 的 members 回應）；`code-summary.md` §四 F-2 | `BR25.2` 的 observable（「204 後列數 −1」）完全沒有被驗證，而 F-2 宣稱「使用者可見結果與規則一致（清單少一列）」。測試夾具實際上**與該宣稱相反**：`setupApp` 的 dispatcher 固定回 `cfg.members`，其中仍含 `OTHER_ID`，故 DELETE 之後導回清單頁重抓到的清單**依然包含被移出的那位**；案例只斷言 URL、表格可見與請求差額，沒有斷言該列消失。於是「移出的結果會呈現在清單上」這件事在本輪是一個預測，不是已驗證的事實 | 把 F-2 的那句話改寫為「未驗證」，或讓 dispatcher 在 DELETE 之後回不含該成員的清單並斷言 `member-list-row-<id>` 為 0 命中 | Resolved (reviewer) |
| R-07 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/member-pages-ui/code-generation/code-generation-plan.md > Step 10（維持未勾） | Step 10 要求的兩件事中，路由已完成（`App.tsx:176`、`:189` 以 `CapabilityRoute` 包覆），入口也已可達：`Sidebar.tsx:234` 的「專案」連到 `/projects`，`ProjectDetailPage.tsx:83` 有 `project-members-link` 連到 `/projects/:id/members`。成員頁路徑帶 `:projectId`，全域 Sidebar 不可能有直達入口（沒有可填的專案）。F-1 的前提「無 `/projects` 路由」已被 U23 推翻，Step 10 因此不需要新增 Sidebar 項。計畫卻仍寫「Sidebar 新增入口」且未勾，閘門上會讀成未完成。 | 建議判為已滿足：把 Step 10 勾起，註記「入口經 U23 的側欄『專案』→ 專案詳情『成員』連結到達；成員頁為 per-project 路徑，無全域 Sidebar 入口是設計使然」，並以 `project-members-link` 作為 `US12.1` 入口可達性的追溯依據。不要為了勾選而加一個沒有 projectId 的假入口。 | Resolved (reviewer) |
| R-08 | Minor | frontend/src/pages/MembersListPage.tsx > 分頁列 `<nav aria-label="成員清單分頁">`（約 L243-277） | 自寫分頁列與 `PaginationControl.tsx` 相比少三項無障礙語意：按鈕沒有小螢幕 44px 觸控尺寸（既有元件用 `min-w-11 min-h-11 md:min-w-0`）、`aria-current` 無對應（本頁無頁碼鈕，可接受）、`member-list-page-info` 切頁後沒有 `aria-live` 或 `role="status"` 播報，螢幕閱讀器使用者按下一頁後聽不到頁次變化。不重用該元件的理由成立（深色主題、`aria-label` 寫死為「使用者清單分頁」、語意為伺服器分頁、改它會波及 `AdminPage`），但這代表兩套分頁 UI 並存。 | 在 `member-list-page-info` 加 `aria-live="polite"`（或把頁次餵給本頁既有的 `LiveRegion`），按鈕補上同樣的 `min-w-11 min-h-11 md:min-w-0 md:min-h-0`。兩套分頁並存記為已知不一致，待 `OPEN-MP24-6`（伺服器分頁）時一併收斂。 | Unresolved |
| R-09 | Minor | frontend/src/pages/MembersListPage.tsx > `handleInvited`（約 L121-131）；frontend/tests/e2e/member-pages.spec.ts | 邀請後跳頁的擴充邏輯正確：後端 `membership_service.py:334` 依 `joined_at, user_id` 排序，新成員 `joined_at` 最新，附加在尾端與伺服器順序一致。但 `setMembers` 用函式式更新、`setRequestedPage` 用閉包中的 `members.length`，兩者可能不同步（例如快速連續邀請時 `useCallback` 閉包仍是舊長度，頁次會算小一頁）。目前也沒有任何 e2e 斷言「邀請後跳到新列所在頁」，未驗項記載屬實，但缺的是這個擴充唯一的行為。 | 把頁次改為由新長度推導，例如 `setRequestedPage(Number.MAX_SAFE_INTEGER)` 讓導出值 `currentPage` 夾到最後一頁，避免閉包長度；或補一個 e2e：50 位成員時邀請 1 位，斷言頁次變為「第 2／2 頁」且新列可見。兩者擇一即可。 | Unresolved |
| R-10 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/member-pages-ui/code-generation/code-summary.md > 三、測試名稱變更；unit-test-instructions.md §七 | 案例 1 改名如實記錄（舊名、新名、新增 1b 都有列），並說明 TCMS 舊名案例會變成孤兒需手動封存，記載充分。但 TCMS 同步屬 `tcms-test-cases` 站，目前只是文字承諾，沒有把「封存舊名案例」列為該站的明確交接項；舊名字串仍描述「超過 100 改顯示提示」，若漏封存，TCMS 會留一份與行為相反的描述。 | 在 `tcms-test-cases` 站的交接清單或 `merge-blockers.md` 第 9 列加一句：該站須封存舊名案例，並在同步報告列出。 | Resolved (reviewer) |
| R-11 | Major | frontend/src/pages/MembersListPage.tsx:55；frontend/src/pages/MemberDetailPage.tsx:68 > 抓取 effect 的 `!Number.isFinite(projectId)` 提前 return | 網址的 `projectId` 不是數字（例如 `/projects/abc/members`）時，`Number('abc')` 為 NaN，effect 直接 return。`isLoading` 初始值為 true 且永遠不會被 `finally` 改掉，畫面永遠停在「載入中…」，live region 一直播報「正在載入成員清單」，沒有任何錯誤文字也沒有 console 訊號。這是一條對使用者無聲的失敗路徑，直接違反已核可的 `SEC-U24-6`（「每一條對使用者無聲的失敗路徑都必須輸出一筆 console 訊號」，`security-requirements.md:63`）。詳情頁只有 `projectId` 無效時會卡住；`userId` 為 NaN 時 effect 仍會執行並顯示「找不到這位成員」，所以 code-summary 把 `userId` 也列為會卡住並不精確。本單元沒有任何 e2e 案例走這條路徑。 | 在 effect 之外或之內明確處理無效的 `projectId`：不要靜默 return，改為在呼叫端 `.then/.catch` 形狀內（避開 `set-state-in-effect`，例如以導出值 `invalidId = !Number.isFinite(projectId)` 直接渲染固定句「查不到這個專案」，並呼叫 `emitFailureSignal({ kind: 'members-fetch-failed', endpoint: 'GET /projects/:id/members' })`），同時讓 `isLoading` 不再卡在 true。補一個 e2e：開 `/projects/abc/members` 與 `/projects/abc/members/1`，斷言出現固定句、不再顯示「載入中…」、console 有訊號且不含使用者文字。 | New |
| R-12 | Minor | frontend/src/components/membership/InviteMemberDialog.tsx:102-110；frontend/src/pages/MemberDetailPage.tsx:337-345 > `role="dialog" aria-modal="true"` | 兩個對話框宣告 `aria-modal="true"`，但沒有焦點圈限、不能按 Escape 關閉，Tab 會跑到背景控件，而 `aria-modal` 已讓輔助科技把背景視為不可達，鍵盤焦點與無障礙樹不一致。關閉後也不把焦點還給觸發鈕。本 repo 其他對話框（`ShareModal.tsx:49`、`EstimateSaveModal.tsx:27`、`ObjectPicker.tsx:389` 起含焦點陷阱）都有 Escape，本單元落後既有慣例。已核可設計只規定「焦點移入第一欄／預設在取消」，沒要求圈限，且使用者仍可 Tab 到取消鈕，故不阻擋；但這是 `aria-modal` 的假宣稱。 | 加上 Escape 關閉（送出中／移出中除外，與取消鈕的停用條件一致）、Tab/Shift+Tab 在對話框內循環、關閉時焦點還給觸發鈕；或退一步移除 `aria-modal` 並如實記為已知缺口。可沿用 `ObjectPicker.tsx` 的鍵盤處理形狀。 | New |
| R-13 | Minor | frontend/src/membership/membershipApi.ts:188、:210、:240-243、:251、:281、:289 > `emitFailureSignal` 的 `kind` | 訊號種類與實際失敗不符：邀請的網路失敗發 `invite-validation-failed`；移出、改角色的網路失敗與任何非 2xx（含 5xx、404）都發 `write-forbidden`。console 訊號的唯一用途是讓維運分辨失敗類型，把連線失敗標成「驗證失敗」「被禁止」會誤導判讀。`kind` 是封閉聯集，所以這也是 `failureSignal.ts` 缺少 `write-failed` 之類的值。 | 在 `SignalKind` 增加不帶使用者文字的字面值（例如 `write-failed`、`invite-network-failed`），網路失敗與 5xx 用它，只有 403 用 `write-forbidden`；讓案例 7 對各分支斷言正確的 kind。 | New |
| R-14 | Minor | frontend/tests/e2e/member-pages.spec.ts > `U24 member pages` 全檔；code-summary.md「重做」節 | 三條已實作的規則仍零斷言：「當前頁變空退回前一頁」（現行流程不可達）、「邀請後跳到新列所在頁」（案例 3 只有 2 位成員，新列本就在第 1 頁）、`BR21.3` 的 403 session 閂。其中第二條是 Step 15 為使 `BR23.2` 在超過 50 位時仍可觀察而新增的唯一行為，且 R-09 指出它有閉包缺陷，沒有測試就沒人會發現。 | 補一個 e2e：50 位成員時邀請 1 位，斷言頁次變為「第 2／2 頁」且新列可見；順便把頁次改為導出（`setRequestedPage(Number.MAX_SAFE_INTEGER)` 讓 `currentPage` 夾到最後一頁）以消除 R-09 的閉包長度。 | New |

> R-01 Reviewer note: 兩頁都已把 `actionError` 與抓取 `error` 分開（`MemberDetailPage.tsx:51`、`:216`；`MembersListPage.tsx:43`、`:187`），寫入失敗不再卸載主內容與控件。案例 `keeps the member block and its controls mounted after a failed write` 守著。

> R-02 Reviewer note: `ReselectionBanner.tsx:67` 改為 `bannerForbiddenForToken: string \| null`，`:184` 以當前 token 比對，換人登入後不再沿用上一位的 403 閂。仍無 e2e 斷言，已在 code-summary 逐項宣告。

> R-03 Reviewer note: 已補 `treats a 404 acknowledge as success and keeps genuinely failed ones pending`（spec:708），涵蓋 `BR26.3`。其餘四條無斷言已明列為覆蓋缺口，不再以不成立的理由遮蔽。

> R-04 Reviewer note: 兩頁 `isProjectManager` 只比 `project_admin`（`MembersListPage.tsx:115`、`MemberDetailPage.tsx:106`），死分支已移除。

> R-05 Reviewer note: 移出差額改為 `waitForLoadState('networkidle')` 後以一般 `expect` 斷言（spec:446-455）。spec:327 的 `expect.poll` 僅作同步點，真正計數在迴圈後的普通 `expect`，形狀正確。

> R-06 Reviewer note: 夾具改為可變，DELETE 後清單少一列，並斷言 `member-list-row-<OTHER_ID>` 為 0 命中（spec:442-443）。

> R-07 Reviewer note: 成員頁經 U23 的「專案」入口與 `project-members-link` 可達，建議視為已滿足（見 Summary）。

> R-08 Reviewer note: `member-list-page-info`（`MembersListPage.tsx:265`）仍無 `aria-live`／`role="status"`；上一頁／下一頁按鈕（`:256-276`）仍無 `min-h-11 min-w-11 md:` 觸控尺寸。`grep` 該檔 `aria-live`、`min-h-11` 皆無命中。

> R-09 Reviewer note: `handleInvited`（`MembersListPage.tsx:122-132`）仍用閉包內的 `members.length` 算頁次，快速連續邀請時會少算一頁。仍無 e2e 斷言「邀請後跳到新列所在頁」。

> R-10 Reviewer note: `merge-blockers.md` 第 9 列已寫明交接 `tcms-test-cases` 封存舊名案例 `renders the member list up to 100 rows…`。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `npx eslint`（兩個頁面、`components/membership`、`membership/`、spec） | 0 errors、0 warnings | 本單元檔案符合 `team.md` 的前端 lint 結構約束：抓取層純函式、state 更新在 `.then/.catch/.finally`、`useEffect` 內 `cancelled` flag、無就地修改物件。 |
| `tsc -b` | 未執行 | 會在 repo 內寫出 buildinfo，違反本次不產生 repo 快取的限制；以 code-summary 記載的通過結果與 eslint 為準，未獨立複驗。 |
| Playwright | 未執行 | 只做靜態閱讀；以突變說明判讀偵測力（見 Summary）。 |

### Summary

**#9 確實修好，且測試會失敗**：`MAX_RENDERED_MEMBERS`／整表隱藏閘已不在 `MembersListPage.tsx`，改為 `MEMBERS_PER_PAGE = 50` 的導出式分頁，`canManage` 仍以完整清單找自身那一列，切頁不發請求。案例 1 先斷言表格可見、本頁 50 列、「第 1／3 頁、共 101 位」，再翻到第 3 頁並進入第 101 位的詳情頁，還原整表隱藏閘即在第一個斷言紅燈；案例 1b 的 100 位邊界擋得住 `floor(len/50)+1` 的 off-by-one。#14 也成立：`fetchMembers` 與三個寫入函式的 404 一律丟 `ProjectNotFoundError`（固定句、不含 id），403 維持權限句，spec 以刻意帶舊形狀 detail（含專案編號）的 404 本體證明畫面不洩漏，這個斷言在實作改回顯示伺服器訊息時會紅。

**阻擋 READY 的一項**：非數字 `projectId` 使頁面永遠「載入中…」且無任何訊號，違反 `SEC-U24-6`，修法只需數行且不牴觸 lint 規則，必須在本單元內補上並加 e2e。對話框無障礙、訊號種類誤標、頁次跳轉無斷言均為 Minor，建議與上一項一併處理；R-08（分頁列播報與觸控尺寸）、R-09（邀請後頁次的閉包長度）兩項前輪 Minor 仍未動。

**Step 10 應視為已滿足**：路由半邊已完成（`App.tsx:176`、`:189` 以 `CapabilityRoute` `K3`／`view` 包覆），入口經 U23 的側欄「專案」→ `/projects` → `ProjectDetailPage.tsx:83` 的 `project-members-link` 到達；成員頁路徑帶 `:projectId`，全域 Sidebar 不可能有直達入口，加一個沒有 projectId 的假入口反而是錯的。原 F-1 的前提已被 U23 推翻，`merge-blockers.md` 第 9 列也已記載。建議 conductor 把 Step 10 勾起並以 `project-members-link` 作為 `US12.1` 的追溯依據。Step 9 的「就地移除」則維持如實記載的偏離（改為導回清單頁重抓，使用者可見的「少一列」已由案例 3 驗證），不構成阻擋。
