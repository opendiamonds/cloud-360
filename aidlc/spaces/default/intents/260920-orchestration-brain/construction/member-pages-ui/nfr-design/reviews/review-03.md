## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本站產出（performance-design、security-design、logical-components、traceability）自洽，且已吸收前次 review-01／review-02 的 Critical／Major（K3 edit 兩段式 canManage、K3 view 發出前置條件、FailureSignal 字面值聯集、掛載機制選型、LiveRegion 責任歸屬）。抽查行號全部正確：membership_router.py 的 171／210／246／283／311／335 對應 view／edit 分佈，rbac_seed_data.py 的 342-348 對應三個缺 view 的角色與只有 view 的角色，unit-of-work.md 的 427／428 為 U24 的依賴與被依賴。已落地程式與設計一致：MembersListPage.tsx:117 與 MemberDetailPage.tsx:107 皆為 `isProjectManager && can('K3','edit')`，Layout.tsx 直接渲染 ReselectionBanner，failureSignal.ts 輸出 console.warn。唯一實質缺口是 BR21.3 的 403 永久失敗閂：設計沒有定義它，而 performance-design 的一句話與落地程式相反。其餘為 Minor。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/member-pages-ui/nfr-design/performance-design.md 第一節 UIP-2 列與第三節；logical-components.md 第二節「橫幅查詢失敗」列；對照 frontend/src/components/membership/ReselectionBanner.tsx 的 bannerForbiddenForToken（約第 66 行） | performance-design 的 UIP-2 手段寫「請求函式不持有模組層狀態」，但 BR21.3 逐字要求 403 後本工作階段不再發請求，這必然需要跨元件實例存活的狀態。落地程式用模組層變數 bannerForbiddenForToken，以 token 為鍵。本站任何產出都沒有設計這個閂，契約三問缺口：誰寫是 catch 內的 BannerForbidden 分支，誰讀是 useEffect 的前置條件，誰清則只有換 token 或整頁重載，設計完全沒寫。logical-components 第二節只說「403 永久失敗本工作階段不再發請求」，沒有說範圍。此外「同一分頁換人登入」這個真實可達的失敗（logout 不觸發整頁導航）完全靠程式碼審查補上，不在設計裡。程式是對的（符合 BR21.3 且處理換人），設計文字是錯的或缺的。 | 在 performance-design 或 logical-components 補一節定義永久失敗閂：存放位置、以 token 為鍵的理由、寫入／讀取／清除三方、整頁重載即重置的代價；並更正 UIP-2 列「不持有模組層狀態」的措辭，改為「不快取回應資料，僅保留永久失敗閂」。 | New |
| R-02 | Minor | construction/member-pages-ui/nfr-design/security-design.md 第四節 FailureSignal 型別 | SignalKind 與 SignalEndpoint 是兩個獨立的字面值聯集，可組出無意義的配對（例如 banner-fetch-failed 搭配 POST 成員端點），型別層只保證不含識別字，不保證 kind 與 endpoint 對應。設計也未列出每個失敗路徑應輸出哪一組配對，SEC-U24-6 的兜底規則因此無從逐項驗證。 | 補一張 kind 對 endpoint 的合法配對表，或將型別改為判別聯集；註明 e2e 斷言哪些配對。 | New |
| R-03 | Minor | construction/member-pages-ui/nfr-design/security-design.md 第一之三節 403 終態處方；logical-components.md 第二節「三種寫入操作失敗」列 | 403 改為終態、不重抓後，can('K3','edit') 讀的是登入時載入的 user.permissions，工作階段中途被授權的使用者沒有任何恢復路徑，只能重新登入或重載。設計未寫明這個代價，與橫幅閂「整頁重載才重置」一樣是已知限制，卻只記了一邊。 | 在 403 終態處方補一句恢復路徑與代價（重新登入或重載後才重新評估），並說明是否接受。 | New |
| R-04 | Minor | construction/member-pages-ui/nfr-design/performance-design.md 第一節 UIP-1 列 | 100 列渲染閘使超過 100 位成員的專案無法在本單元管理成員（上游 nfr-requirements 已記載此代價）。本站設計只寫閘門位置，未重述這個功能斷崖，也未指出哪些已核可 AC 因此在大型專案不可驗證，後續讀者只讀本站會誤以為是純效能取捨。 | 在 UIP-1 列加一句斷崖後果並引用 OPEN-MP24-6 作為伺服器分頁的承接，列出不可驗證的 AC。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 行號抽查（membership_router.py、rbac_seed_data.py、unit-of-work.md） | 全部吻合 | 引用定位與事實皆正確，無殘留錯誤行號 |
| 設計對落地程式比對（canManage、Layout 掛載、LiveRegion、failureSignal） | 一致 | 僅 R-01 的模組層閂在設計中缺席且與一句設計文字相反 |
| 與前次 review-01／review-02 比對 | 先前 Critical／Major 已在產出中處置 | 前次發現不重列 |
