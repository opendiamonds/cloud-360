## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本單元（`U24 member-pages-ui`）的設計在三個面向站得住：橫幅宿主 `role="status"` 的無障礙約束、`canManage` 由 `list_members` 自身那列取得（`BR22.3`）、acknowledge 404 等價於成功（`BR26.3`）。六個端點的路徑與回應碼也與 `membership_router.py` 相符。前次 review-01、review-02 的主要發現已在凍結的產出中處置。但仍有一處契約端點缺口與設計不符實況：`AC12.2.2` 的「變更紀錄」在設計裡有讀者（`MemberChangeLog`、`BR24.3`）卻沒有任何提供者，已落地的程式自己查出此事並降級為佔位（`OPEN-MP24-7`），凍結的設計卻仍把它標為 `OK`。另有三項 Major：專案名稱缺口的指派落點無效、受邀者選擇器沒有資料來源、跨路由「就地更新」與元件狀態表自相矛盾。依規則（1 Critical、3 Major）判 NOT-READY。這份審查不涉及也未開啟任何兄弟單元的設計檔，只讀本單元產出、上游契約與已落地程式的必要行。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Critical | `construction/member-pages-ui/functional-design/functional-spec.md` §四（六個消費點）、§五 W4 第 2 步、§九 自檢 2 與 §九之二 Audit logging 列；`rules.md` `BR24.3`；`traceability.json` 的 `AC12.2.2`（status OK）；`frontend-components.md` §二 `<MemberChangeLog />` | **契約端點三問的「誰提供」一腿落空。** W4 第 2 步寫「抓取該成員資料與變更紀錄」，`MemberChangeLog` 的 props 是 `entries`，`BR24.3` 的 observable 是 `[data-testid="member-change-log"]` 最新一列含四項；但 §四 列出的六個端點裡**沒有任何一個**回傳變更紀錄，也沒有單一成員的讀取端點。實測 `membership_router.py` 只有 `:164`／`:192`／`:234`／`:270`／`:309`／`:328` 六條路由。§九 自檢 2 宣稱「另三處完整」，漏了這一條；§九之二 稱稽核紀錄「由 `U19` 的持久層提供、本單元只渲染」，但沒有讀取介面可渲染。已落地的 `MemberDetailPage.tsx:294-320` 自己查出此事（`OPEN-MP24-7`：資料存在於 `reselection_events`，但六個路由與十七個 facade 方法皆無讀取端），改渲染固定佔位 `member-change-log-unavailable`。結果是 `BR24.3` 與 `AC12.2.2` 在本單元**無法被任何 e2e 斷言**，而凍結的 `traceability.json` 仍把 `AC12.2.2` 標為 `OK`，與程式一側的 `Deferred` 矛盾。**程式一側是對的**：不捏造稽核資料是正確處置，錯的是設計。連帶影響 ADR-0006 audit logging 面，使用者可見的稽核面實際不可達。 | 將 `AC12.2.2`／`BR24.3` 在設計中改記為 `Deferred`，並新增開放項 `OPEN-MP24-7`，寫明缺口為「`U19` 缺變更紀錄讀取端」。由於 `U19` 的 `code-generation` 已完成且在游標之前，須在關卡上明講「無自然承接站」，交人裁決（是否開 `U19` 的契約擴充）；不得指派給 `ALWAYS` 但已在游標之前的站。同時更正 §九 自檢 2 與 §九之二 Audit logging 的敘述，並讓 `BR24.3` 的 observable 區分「有讀取端」與「佔位」兩種狀態。 | New |
| R-02 | Major | `functional-spec.md` §八 `OPEN-MP24-1`；`construction/member-pages-ui/functional-design/rules.md` `BR26.2`；已落地 `frontend/src/components/membership/ReselectionBanner.tsx` 的 `summaryText`、`專案 #{ev.project_id}` | **`OPEN-MP24-1` 的指派落點無效，且兩條建議的解法都不是 `U24` 能自行完成的。** 設計把「`ReselectionOut` 沒有專案名稱」指派給 `U24` 的 `code-generation`，並列兩條路：①`U19` 回應模型加欄位；②`U24` 對每筆事件再打專案端點（N+1）。但同一格又寫「本站不逕自改 `U19` 已完成的程式」；①需要改 `U19`，②沒有端點與先例。於是 `U24` 的 `code-generation` 實際上別無選擇，程式降級成「專案 #id」佔位，單筆文案也完全不含專案名，**與 `[D10]`=A「可展開列出專案名」不符**，而凍結的設計沒有把這個降級寫成被接受的結果。這是 `project.md` 記過的「指派給無權執行的站」形狀。 | 把 `OPEN-MP24-1` 改記為：誰有權改 `ReselectionOut`（`U19`，已在游標之前，無自然承接站）、`[D10]`=A 的「專案名」要求在此之前以何種降級呈現（例如 `專案 #id`），並在關卡上交人裁決是否接受降級或開契約擴充。`BR26.2` 與 W6 第 4、5 步須同步寫明「顯示名稱以 id 佔位」，否則文案與程式永久分歧。 | New |
| R-03 | Major | `functional-spec.md` §五 W3 第 2 步與其後說明（「受邀者來自選擇器」）；`frontend-components.md` §六（「邀請的受邀者：必填；未選即停用送出鈕」）、§四 `InviteMemberDialog`；已落地 `InviteMemberDialog.tsx:47-66`（`userIdText` 文字欄） | **「受邀者選擇器」有讀者、無資料來源。** 設計多處以「受邀者來自選擇器」為前提（含替 `BR23.1` 的低可達性辯護），但 §四 的六個消費點沒有任何列出可邀請使用者的端點，元件表也沒有承載候選清單的 state。已落地的程式實際是讓人手動輸入**數字 user_id**（`Number(userIdText)`），與「選擇器」不符；使用者必須事先知道對方的內部 id。設計沒有說明這是被接受的取捨，還是缺漏。同時這也牽動 IAM／資料揭露面：若日後補選擇器，需要一個使用者目錄端點，而該端點的授權範圍設計裡完全沒有。 | 決定並寫明：①受邀者輸入方式為何（數字 id、帳號、或選擇器），②若為選擇器，資料來源端點與授權範圍屬哪個單元，③若為數字 id，將「來自選擇器」的前提與依賴它的論證（`BR23.1` 的可達性評估）一併更正，並記為已知可用性限制。 | New |
| R-04 | Major | `functional-spec.md` §五 W4 第 4 步、W5 第 4 步；`rules.md` `BR24.1`、`BR25.2`；`frontend-components.md` §四（`MemberListPage` 與 `MemberDetailPage` 各自持有 `members`／`member` state）；已落地 `MemberDetailPage.tsx:44-46`、`:168`（`navigate` 後重新掛載） | **「就地更新清單與詳情兩處」「導回清單並就地移除該列」與設計自己的元件狀態表矛盾。** 清單與詳情是兩個不同路由（`/projects/:projectId/members` 與 `.../:userId`），元件表給兩頁各自獨立的 state，沒有共享的 context、store 或路由 state。換頁即卸載，所謂「就地更新兩處」在設計下做不到；實作也果然是各頁自行 `fetchMembers`，導回清單時重新抓取並出現載入態。`BR24.1` 的 observable「200 後清單顯示新角色，且無整頁載入態出現」與 `BR25.2` 的「就地移除」因此只能在**同頁**成立，跨頁的部分不可驗，或與實作衝突。AC 本身（列數 −1、新角色可見）仍可滿足，問題在於規則與 observable 的文字承諾了設計沒有的機制。 | 二選一並寫進設計：①明確引入跨路由共享狀態（誰擁有、誰清），或②承認兩頁各自重抓，將 `BR24.1`／`BR25.2` 的「就地」限縮為同頁內的更新，並刪去跨頁的「無載入態」斷言。 | New |
| R-05 | Minor | `functional-spec.md` §五 W4 第 2 步、§三；`rules.md` `BR22.3` 的 `applies_to: MemberListPage, MemberDetailPage` | **詳情頁的資料來源與非管理者直接進入的行為未寫。** 沒有單一成員讀取端點，詳情頁只能自行呼叫 `list_members` 再找人（已落地程式即如此，`MemberDetailPage.tsx:31` 註解「可被直接以 URL 進入」）。設計只寫 `[>]` 對一般成員不可見，沒寫一般成員直接輸入詳情網址時看到什麼。屬同一個 `canManage` 取得規則的延伸，但未被 `BR22.1` 的 observable 涵蓋。 | 在 W4 補一句詳情頁的資料來源，並在 `BR22.1` 或新規則補上「非管理者直接進入詳情頁」的可觀察行為。 | New |
| R-06 | Minor | `rules.md` `BR21.3`；`functional-spec.md` §六之一 `fetch-failed`；已落地 `ReselectionBanner.tsx` 的 `bannerForbiddenForToken` 與 `mayQuery` | **規則與散文在「何時不發請求」上分叉，且有兩個行為只存在於程式。** 規則文只規定「收到 403 後不再發請求」，而「缺 `K3 view` 者一開始就不發請求（計數 0）」只寫在 §六之一與 `frontend-components.md` §七的散文；已落地程式另外加了「閂以 token 為鍵，換人登入即失效」，設計完全沒提（`logout()` 不觸發整頁導覽，裸布林會讓前一位使用者的 403 擋住下一位）。程式一側是對的，設計未覆蓋。 | 把 `can('K3','view')` 前置條件與「閂不跨使用者」併入 `BR21.3` 的 logic 與 observable，使可測的規則文與散文一致。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 本站 `traceability.json` 結構檢視（人工解析） | 17 條 AC 皆有列；`AC12.2.2` 標 `OK` 而程式一側標 `Deferred` | 與 R-01 一致：設計一側高估了覆蓋 |
| 端點核對（`grep` `membership_router.py` 的 `@router`／`response_model`） | 6 條路由，無變更紀錄讀取端、無單一成員端點、無使用者目錄端點 | 支撐 R-01、R-03、R-05 |
| 引用抽查（`ReselectionOut` 九欄、`rbac_seed_data.py:343-345` 的 K3 view、`list_members` 無分頁參數與 `require_story_action("K3","view")`） | 與設計敘述一致 | 設計的事實性引用大致正確，缺口在契約完整性而非引用錯誤 |
| 執行型工具（測試、lint、建置） | 未執行（派工禁止寫檔或產生快取） | 以讀檔取代 |
