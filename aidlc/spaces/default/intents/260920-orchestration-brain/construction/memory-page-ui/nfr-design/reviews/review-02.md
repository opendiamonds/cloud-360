## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

凍結的 nfr-design 產出（performance-design.md、security-design.md、logical-components.md）仍保留前次 review-01 已提的缺口：補償重抓的競態防護機制寫錯、失敗路徑靜默、與 BR34.4／BR34.6 未對齊、pending 帳號修法落點與已核可的 router 契約衝突。已落地的程式（依 code-summary.md）在四處改採不同且較正確的做法（requestSeq 序號、同步失敗提示、單一退頁者、facade 層檢查），代表凍結的設計文字與實際落地互相矛盾，下游若依設計文字實作會得到有缺陷的結果。Major 超過兩項，故判 NOT-READY。矛盾處皆是程式端正確、設計文字錯誤。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | memory-page-ui/nfr-design/performance-design.md 第三節、第五節 | 前次 review-01 已提 R-01：背景重抓由刪除的事件處理函式發出，不在 useEffect 內，第三節與第五節倚賴的 effect cleanup 之 cancelled flag 管不到它。重抓進行中翻頁、或兩次重抓亂序到達，舊回應會覆蓋新頁或讓剛刪的列重現。設計自稱沿用 AdminPage.tsx:198-203，但先例實際靠 requestSeq 序號比對（AdminPage.tsx:124-131）。code-summary.md 第二節與突變驗證（移除序號比對則 E7 紅）顯示程式已採序號，故程式是對的一邊，設計文字是錯的。 | 以對齊修正的形式更正 performance-design.md 第三、第五節：重抓以序號比對防亂序，並明記這是對齊修正、非新定案；刪除 cancelled flag 可管重抓的主張。 | New |
| R-02 | Major | memory-page-ui/nfr-design/performance-design.md 第二節第 2 點「重抓失敗」 | 前次 review-01 已提 R-02：設計寫重抓失敗時靜默保留、下一次翻頁自然拿到正確資料，此為假。offset 分頁下，第 1 頁刪一則後若重抓失敗，按下一頁以 offset 20 取得，遞補上來的原第 21 筆永遠不出現，且無任何提示。先例 AdminPage.tsx 失敗時有 toast。code-summary.md 顯示程式已顯示「清單同步失敗」並播報（E8），設計仍寫靜默。 | 把失敗行為改為可見提示加播報，並補寫最後一頁刪除、失敗後有無重試的行為；與程式一致。 | New |
| R-03 | Major | memory-page-ui/nfr-design/performance-design.md 第二節第 2 點，對照 memory-page-ui/functional-design/rules.md 的 BR34.4（第 212 行）與 BR34.6（第 240 行） | 前次 review-01 已提 R-03：設計加入背景重抓，但 BR34.4 仍逐字「不發任何重抓」，設計文件內未記錄這是對 BR34.4 的偏離（偏離只出現在 code-summary.md 偏離表第 9 項）。另外設計說重抓回來為空且 page 大於 1 時「套用 BR34.6」，與本地刪空即退頁並存會連退兩頁；程式以「單一退頁者」解決，但設計未定義。 | 在 nfr-design 產出內明記對 BR34.4 的偏離及原因，並寫入單一退頁者規則：一次刪除只由重抓回應決定是否退頁，頁次已被改動的重抓回應丟棄。 | New |
| R-04 | Major | memory-page-ui/nfr-design/security-design.md 第四節，對照 memory-page-ui/code-generation/code-summary.md 偏離表第 11 項 | 前次 review-01 已提 R-05：設計方向是在記憶 API 的 router 層加已核准 dependency，與 memory_router.py 檔頭及 C3 測試宣告的「授權全在 facade（K-08 sole_entry）」衝突，且對 intent_routing.py 的同進程直呼 facade 無效。程式已改為 facade 六個公開方法首行檢查（Principal.is_approved），故設計文字與落地矛盾，程式是對的一邊。此改動擴大了已核可 K-08 契約的 MemoryForbidden.reason 集合與 DELETE 的 403 宣告（原 D1=A、D8-1、D8-2 刻意不宣告），目前只記在 code-summary.md，nfr-design 與契約摘要皆無追認。 | 更正 security-design.md 第四節的落點為 facade 層，並把對 K-08 契約與 D8-1／D8-2 的擴大列為明確的跨單元交接事項，指派承接的修訂站。 | New |
| R-05 | Major | memory-page-ui/nfr-design/performance-design.md 全檔；memory-page-ui/nfr-requirements/performance-requirements.md UIP-3 驗證欄 | 前次 review-01 已提 R-04：本設計新增的行為（重抓、重抓中翻頁、刪空頁、重抓失敗）沒有對應的設計層驗證。UIP-3 驗證只計請求數，不驗跳列是否消失。code-generation 後來補了 E6 到 E8、E11 到 E15，但這些不在 nfr-design 的驗證欄，設計層仍是空缺（前端無 unit 測試框架，e2e 是唯一防線）。 | 在 performance-design.md 補一張驗證表，列出模擬 offset 位移的路由攔截、重抓中翻頁、刪空頁、重抓失敗四情境，並對應到已存在的 e2e 案例。 | New |
| R-06 | Minor | memory-page-ui/nfr-design/performance-design.md 第二節第 3 點 | 前次 review-01 已提 R-06：語意與程序區滿 200 則時的計數標示被丟給 code-generation，但 BR32.4 已規定滿載顯示「N+ 則」，刪除後就地移除使 200 變 199 會變成錯的精確數。應在設計層定案：原為滿載者刪除後保留「+」。 | 在設計中定案並寫入，或明記為開放項並指派承接者。 | New |
| R-07 | Minor | memory-page-ui/nfr-design/security-design.md 第三節 XSS、SEC-U15-4、SEC-U15-5 | 前次 review-01 已提 R-07：XSS 的 e2e 在 React 預設行為下不可能失敗，只在改用 dangerouslySetInnerHTML 時變紅，應明寫目的是防未來回歸並以 grep 為主要驗證（突變驗證 E9 已證實此偵測力）。data-owner-user-id 把他人數值 id 放進 DOM 屬刻意取捨，未註明。console 檢查只涵蓋本單元自己的 log。 | 在設計中註明這些驗證的實際偵測範圍，以及 data-owner-user-id 為刻意取捨。 | New |
| R-08 | Minor | memory-page-ui/nfr-design/logical-components.md 第一節元件清單 | 元件清單與失效範圍表缺少兩個已落地的元件或狀態：/me 失敗時 user.id 永遠 undefined 的 memory-page-identity-error 錯誤態（nfr-requirements 的 R-03 交接項），以及 memory-zone-episodic-sync-failed 同步失敗提示。兩者在 code-summary.md 偏離表第 6 項才出現；nfr-design 沒有承接該交接項，也沒有寫這兩者的失效範圍。 | 補入元件清單與失效範圍，並說明 identity-error 屬整頁失效。 | New |
| R-09 | Minor | memory-page-ui/nfr-design/nfr-design-questions.md（零題的理由） | 前次 review-01 已提 R-08：零題的前提是沿用 AdminPage 先例不需新判斷，但上述 R-01、R-02 顯示設計實際偏離先例（cancelled flag 對序號、靜默對 toast），零題理由不能照字面成立。 | 在核可紀錄中說明偏離先例的兩處，或修正零題理由。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀取 nfr-design 全部產出、nfr-requirements、前次 review-01 | 完成 | 前次 R-01 至 R-08 的缺口幾乎全部仍留在凍結產出中 |
| code-summary.md 抽查（僅讀本單元路徑） | 完成 | 程式在序號防亂序、同步失敗提示、單一退頁者、facade 層核准檢查四處與設計文字矛盾，程式端正確 |
| 實際原始碼檔案 | 未開啟 | 審查範圍限本單元路徑，程式行為以 code-summary.md 與其突變驗證紀錄為準 |
