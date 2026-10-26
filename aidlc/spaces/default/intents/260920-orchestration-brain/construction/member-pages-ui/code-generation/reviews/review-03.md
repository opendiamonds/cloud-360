## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | `frontend/src/pages/MemberDetailPage.tsx:46`、`:137-139`、`:170-173`、`:207`；`frontend/src/pages/MembersListPage.tsx:43`、`:124-128`、`:171` | 單一 `error` state 同時承載**抓取失敗**與**寫入失敗**，而主要內容的渲染條件是 `!error`。後果：任何寫入路徑的失敗都會把整頁內容卸載，**而清除 error 的唯一途徑（控件本身）就在被卸載的那個區塊裡**，因此是不可復原的死態，只能離開該頁。最可達的路徑不是 403 而是暫時性網路失敗：`changeMemberRole` 的 catch 丟 `Error('連線失敗')`（`membershipApi.ts:250-252`）→ `MemberDetailPage.tsx:137-139` `setError` → `:207` 的 `{!isLoading && !error && member && (...)}` 整塊消失（成員姓名、角色區、守門回報、變更紀錄、移出鈕一起不見）。清單頁同形：邀請 403 → `handleForbidden` → `:171` 的表格消失，而 `canManage` 仍為真故「邀請成員」鈕**還留著**，使用者得到一個沒有清單、只有邀請鈕的頁面。這一項不在 `code-summary.md` §四 的七項自述內，也沒有任何 e2e 斷言；`functional-spec.md:176` 只要求「清單頁顯示『你沒有管理這個專案的權限』」，沒有要求清掉清單 | 把寫入錯誤與抓取錯誤分成兩個 state：寫入錯誤渲染在控件旁、不參與主要內容的 `!error` 閘；或在每次使用者互動開始時清掉它並確保清除入口不被卸載 | New |
| R-02 | Major | `frontend/src/components/membership/ReselectionBanner.tsx:62`、`:179`、`:194-196` | `BR21.3` 的永久失敗閂 `bannerForbiddenInThisSession` 是模組層布林值，**不綁任何身分**。而本 repo 的登出是純 state 清除（`AuthContext.tsx:56-61`）＋ `Sidebar.tsx:11-13` 的 `navigate('/login')`，**不重新載入文件**；登入同樣走 `navigate`（`LoginPage.tsx:105-107`）。故在同一個分頁內「使用者 A 收到 403 → 登出 → 使用者 B 登入」之後，B 的橫幅查詢永遠不發出，`US12.4`／`AC12.4.3` 的通知對 B **靜默消失**且無任何可觀察訊號（該路徑刻意不顯示錯誤）。元件 docstring 只承認「整頁重新載入時會重置」，未涵蓋換使用者這一面 | 把閂改為以身分為鍵（例如 `let forbiddenForToken: string \| null`，effect 內比對當前 token），或在 token 變更時重置。零新依賴、不觸碰 `NFR4.80` 的瀏覽器儲存禁令 | New |
| R-03 | Major | `aidlc/.../code-generation/code-summary.md` §四 F-4／F-5／F-6／F-7；`frontend/tests/e2e/member-pages.spec.ts` 全檔 | 五條已實作規則零斷言（`BR21.3` 的 403 閂、`BR23.1` 的字串 `detail` 拒絕態、`BR24.2`、`BR26.2`、`BR26.3`），理由是「8 個案例由 `cicd-pipeline.md` §五 固定」＋「案例名稱是 TCMS 的鍵」。**兩個理由逐字核對後都不成立**：§五 的標題是「本單元**需要新增**的 e2e 案例」——那是下限清單，不是上限；而 `ui-regression.lock.yml:568` 的註解逐字約束的是 `--summary-template` 不得改（`changing it orphans the old cases`），**新增一個 test 只會新建一個 TCMS 案例，不會讓既有案例變成孤兒**。最要緊的是 `BR26.3`：它是審查 `R-02` 修掉「橫幅永遠清不掉」那條 Critical 的規則，而 `team.md` 記載前端**唯一**的自動化層就是 Playwright e2e，故它目前的迴歸保護是零。其構造成本極低（既有 dispatcher 已可按 method／path 分流，只需三筆事件 ＋ 令其中一筆回 500 ＋ 再按一次） | 至少為 `BR26.3` 補一個案例（名稱一旦合併即凍結，故一次定名）；或把「§五 是上限」這個讀法明白提交使用者在閘門上採納，而不是以一個不成立的機械約束當理由 | New |
| R-04 | Minor | `frontend/src/pages/MembersListPage.tsx:105`；`frontend/src/pages/MemberDetailPage.tsx:94`；`nfr-design/security-design.md` §一 的「專案層角色」列 | `canManage` 的第一段以 `ownRole === 'project_admin' \|\| ownRole === 'project_owner'` 放寬，而 `project_owner` 這個值**在資料庫層不可能出現**：`models.py:585-587` 與 `schema_rbac.sql:597-598` 的 `ck_project_members_role` 把 `project_members.role` 限定為 `('project_admin','member')`，且 `membership_types.py:41` 逐字說 owner 是 `projects.owner_user_id` 承載的**專案屬性、不是成員角色**。`security-design.md` §一 把 `project_owner` 列為「`MemberView.role` 可讀的對應來源」之一——**那個前提是假的**。這是授權述詞裡的一個死分支：若那條 CHECK 日後被放寬，它會讓一個非 `project_admin` 的角色值取得管理者控件，而伺服器對三個寫入端點都要求 `project_admin`（`membership_facade.py:138-160`），正是 §一之三 設立兩段式要消除的那類永久 403。**無功能損失**（已查證 `POST /api/hierarchy/projects` → `create_project_with_owner` 在同一交易把建立者寫成 `project_admin`，`membership_facade.py:425-465`，故 `AC12.1.1` 成立），因此只記 Minor | 移除該 disjunct，或在程式與 `security-design.md` §一 寫明它是刻意的防禦性冗餘並附 CHECK 的引用；不要讓一個不可達值在設計文件裡看起來像一個真實的角色來源 | New |
| R-05 | Minor | `frontend/tests/e2e/member-pages.spec.ts:373`、`:410` | 兩處「恰 N 次請求」用 `expect.poll(...).toBe(n)`。`expect.poll` 在**第一次**觀測到相符值時即通過，故它不是 settled-count 斷言。`:373` 的移出差額「恰為 1」在突變（`handleRemove` 自己多抓一次）之下，序列是「重抓 → +1」再「清單頁掛載 → +2」；若 poll 在兩者之間取樣就會看到 1 而**綠燈**。m3 回報 RED 可信（route 全部被攔截、兩個請求幾乎同時落地，首次取樣即為 2），但該偵測力依賴時序而非斷言結構 | 改為「先等到可判定的終點（例如 `waitForResponse` 等到清單頁掛載那次回應）再以一般 `expect` 斷言計數」，或 poll 之後加一次穩定期複驗 | New |
| R-06 | Minor | `frontend/tests/e2e/member-pages.spec.ts:364-373`（案例 3 第 ③ 段）、`:150-170`（`setupApp` 的 members 回應）；`code-summary.md` §四 F-2 | `BR25.2` 的 observable（「204 後列數 −1」）完全沒有被驗證，而 F-2 宣稱「使用者可見結果與規則一致（清單少一列）」。測試夾具實際上**與該宣稱相反**：`setupApp` 的 dispatcher 固定回 `cfg.members`，其中仍含 `OTHER_ID`，故 DELETE 之後導回清單頁重抓到的清單**依然包含被移出的那位**；案例只斷言 URL、表格可見與請求差額，沒有斷言該列消失。於是「移出的結果會呈現在清單上」這件事在本輪是一個預測，不是已驗證的事實 | 把 F-2 的那句話改寫為「未驗證」，或讓 dispatcher 在 DELETE 之後回不含該成員的清單並斷言 `member-list-row-<id>` 為 0 命中 | New |
| R-07 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/member-pages-ui/code-generation/code-generation-plan.md > Step 10（維持未勾） | Step 10 要求的兩件事中，路由已完成（`App.tsx:176`、`:189` 以 `CapabilityRoute` 包覆），入口也已可達：`Sidebar.tsx:234` 的「專案」連到 `/projects`，`ProjectDetailPage.tsx:83` 有 `project-members-link` 連到 `/projects/:id/members`。成員頁路徑帶 `:projectId`，全域 Sidebar 不可能有直達入口（沒有可填的專案）。F-1 的前提「無 `/projects` 路由」已被 U23 推翻，Step 10 因此不需要新增 Sidebar 項。計畫卻仍寫「Sidebar 新增入口」且未勾，閘門上會讀成未完成。 | 建議判為已滿足：把 Step 10 勾起，註記「入口經 U23 的側欄『專案』→ 專案詳情『成員』連結到達；成員頁為 per-project 路徑，無全域 Sidebar 入口是設計使然」，並以 `project-members-link` 作為 `US12.1` 入口可達性的追溯依據。不要為了勾選而加一個沒有 projectId 的假入口。 | New |
| R-08 | Minor | frontend/src/pages/MembersListPage.tsx > 分頁列 `<nav aria-label="成員清單分頁">`（約 L243-277） | 自寫分頁列與 `PaginationControl.tsx` 相比少三項無障礙語意：按鈕沒有小螢幕 44px 觸控尺寸（既有元件用 `min-w-11 min-h-11 md:min-w-0`）、`aria-current` 無對應（本頁無頁碼鈕，可接受）、`member-list-page-info` 切頁後沒有 `aria-live` 或 `role="status"` 播報，螢幕閱讀器使用者按下一頁後聽不到頁次變化。不重用該元件的理由成立（深色主題、`aria-label` 寫死為「使用者清單分頁」、語意為伺服器分頁、改它會波及 `AdminPage`），但這代表兩套分頁 UI 並存。 | 在 `member-list-page-info` 加 `aria-live="polite"`（或把頁次餵給本頁既有的 `LiveRegion`），按鈕補上同樣的 `min-w-11 min-h-11 md:min-w-0 md:min-h-0`。兩套分頁並存記為已知不一致，待 `OPEN-MP24-6`（伺服器分頁）時一併收斂。 | New |
| R-09 | Minor | frontend/src/pages/MembersListPage.tsx > `handleInvited`（約 L121-131）；frontend/tests/e2e/member-pages.spec.ts | 邀請後跳頁的擴充邏輯正確：後端 `membership_service.py:334` 依 `joined_at, user_id` 排序，新成員 `joined_at` 最新，附加在尾端與伺服器順序一致。但 `setMembers` 用函式式更新、`setRequestedPage` 用閉包中的 `members.length`，兩者可能不同步（例如快速連續邀請時 `useCallback` 閉包仍是舊長度，頁次會算小一頁）。目前也沒有任何 e2e 斷言「邀請後跳到新列所在頁」，未驗項記載屬實，但缺的是這個擴充唯一的行為。 | 把頁次改為由新長度推導，例如 `setRequestedPage(Number.MAX_SAFE_INTEGER)` 讓導出值 `currentPage` 夾到最後一頁，避免閉包長度；或補一個 e2e：50 位成員時邀請 1 位，斷言頁次變為「第 2／2 頁」且新列可見。兩者擇一即可。 | New |
| R-10 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/member-pages-ui/code-generation/code-summary.md > 三、測試名稱變更；unit-test-instructions.md §七 | 案例 1 改名如實記錄（舊名、新名、新增 1b 都有列），並說明 TCMS 舊名案例會變成孤兒需手動封存，記載充分。但 TCMS 同步屬 `tcms-test-cases` 站，目前只是文字承諾，沒有把「封存舊名案例」列為該站的明確交接項；舊名字串仍描述「超過 100 改顯示提示」，若漏封存，TCMS 會留一份與行為相反的描述。 | 在 `tcms-test-cases` 站的交接清單或 `merge-blockers.md` 第 9 列加一句：該站須封存舊名案例，並在同步報告列出。 | New |

> R-01 Not re-checked this round

> R-02 Not re-checked this round

> R-03 Not re-checked this round

> R-04 Not re-checked this round

> R-05 Not re-checked this round

> R-06 Not re-checked this round

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 讀檔與 grep（依指示未執行任何測試、lint、build） | `MAX_RENDERED_MEMBERS`／整表閘已移除；分頁邊界推導成立（0 位→第 1／1 頁；50→1 頁；51→2 頁；100→2 頁；101→3 頁）；`canManage` 仍以完整 `members` 找自身那一列；切頁不呼叫 fetch；頁次為導出值，無 effect 內 setState，符合 `set-state-in-effect`、`immutability` 與兩層抓取形狀 | 實作本身無 Critical 或 Major。案例 1 抓得到整表閘（表格存在斷言）與切頁請求數，案例 1b 抓得到 off-by-one（101 位時兩式皆得 3，故 1b 對 100 位的存在有必要）。「退回前一頁」目前在使用者流程中不可觸發，未驗項嚴重度低。 |
| 共用檔影響（`api.d.ts`、`ws-contract.d.ts`、`useBrainConnection.ts` 的 `?? ''`） | 屬其他單元對 `error` 非輪次 `turnId` 為 null 的型別修正，與本頁無交集 | 不影響本單元。 |
| ADR-0006 四面向（前端權限控件可見性） | IAM：管理控件仍受 `canManage`（per-project `project_admin` AND `can('K3','edit')`）把關，分頁不改變此判定；詳情連結只在 `canManage` 時渲染。encryption、network exposure：N/A，未新增請求或端點。audit logging：N/A，前端不寫稽核。 | 無退步。 |

### Summary

第 9 項的前端分頁修法正確：每位成員都可翻頁到達、不新增請求、符合前端 lint 結構約束，兩個突變驗證與案例設計足以抓到原缺陷。剩下的是 Step 10 應判為已滿足的簿記、分頁列的無障礙小落差、邀請跳頁缺 e2e 與閉包長度風險，以及 TCMS 孤兒案例的交接，皆為 Minor。
