## Review

**Verdict:** NOT-READY

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

### Summary

0 Critical、3 Major、3 Minor。依裁決規則（>2 Major）判 **NOT-READY**；本輪為 advisory，故此判定是給閘門上的人的決策支援，不是修復迴圈。

分類：R-01／R-02／R-04／R-05／R-06 為 **new-introduced**（本輪寫下的程式或測試造成）；R-03 為 **new-design-problem**（上游 `cicd-pipeline.md` §五 被讀成上限，以及一個不成立的 TCMS 機械約束被當成理由）；無 pre-existing-unreviewed 項。

先說明我**查證後未能證成**的幾項，因為它們是本次派工點名要攻擊的面：`canManage` 的兩段式 AND 在兩頁都真的存在（`MembersListPage.tsx:106`、`MemberDetailPage.tsx:95`），403 在三個寫入端點都是終態、全檔沒有任何一條 403 之後的重抓路徑；橫幅的 `can('K3','view')` 前置條件確實在 `useEffect` 的第一個 guard（`:179`），案例 2 的 B 分支以兩個 happens-after 訊號 ＋ 兩次落地讓「0」不是假 0；`FailureSignal` 兩欄確為字面值聯集，本單元七支應用檔的 `console.*` 命中數為 **1**（只有 `failureSignal.ts:66`）、`localStorage`／`sessionStorage`／`dangerouslySetInnerHTML` 命中數為 **0**、六個 `fetch` 全部經 `apiUrl()`；`role="status"` 宿主內只有 `summaryText()` 的文字，兩個動作鈕與可展開清單是兄弟節點（`ReselectionBanner.tsx:241-254`）。F-1 的 grep 宣稱我獨立複驗為真（全前端只有本單元新增的那兩條 `/projects` 路由，無專案頁），`AC12.2.2`／`BR24.3`／`UIP-5` 的 Deferred 是誠實的（`traceability.json` 實算 49 OK／4 Deferred／7 N/A，且標 `OK` 而無斷言的那幾列都在同一格的 note 裡寫明「無 e2e 斷言」——沒有洗成 OK）。F-3 的「`UIP-4` 與 `UIP-2` 字面互斥」判讀正確。

最承重的一項是 **R-01**。它不是規則被讀錯，是一個**沒有被寫下來的狀態**：寫入錯誤與抓取錯誤共用一個 state，而主要內容的渲染閘掛在那個 state 上，於是一次網路抖動就會讓成員詳情頁變成一行紅字且**無法恢復**——而本單元是管理成員的唯一入口。它既不在七項自述裡，也不在任何斷言裡，七項送審前自檢的結構上抓不到它（那六到七項檢查的都是「我寫下的內容對不對」，沒有一項問「這兩個 state 合用會產生什麼」）。R-02 屬同一類：模組層閂的識別維度從未被寫下來過。

VERDICT: NOT-READY
