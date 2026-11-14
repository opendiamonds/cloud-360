## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本單元（U15 memory-page-ui）的功能設計事實基礎紮實：契約端點三問齊備、ADR-0006 四面向各有落點、追溯完整。但凍結的產出自前次 review-01 以來未再修改（產出檔 mtime 早於 review-01），前次的 2 項 Major 與 6 項 Minor 全部仍留在產出裡，故在此重列。實作已在多處走在設計前面：`MemoryZone.tsx` 實作了刪除後的背景重抓、單一頁次調整者、黏著的 wasFull，`MemoryPage.tsx` 實作了身分未決的可區分錯誤態，都與凍結設計的字面（BR34.4「不重抓」、BR32.4）相反，這些情況下程式那一邊是對的。Major 剛好 2 項，落在 READY 容忍上限內，判 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/memory-page-ui/functional-design/rules.md > BR34.4、BR34.6、BR33.1；functional-spec.md > W4 第 5 至 6 步、六之一狀態機 | 前次 review-01 已提。「刪除後就地移除、不重抓」與 offset 分頁組合後，翻頁會漏列、hasNext 會過期，第一頁刪光時會誤顯示 empty（伺服器仍有第 21 筆以後）。設計與已落地程式矛盾：`frontend/src/components/memory/MemoryZone.tsx` 的 docstring 自述「偏離 BR34.4 字面『不發任何重抓』」，實作刪除後背景重抓當前頁，並以 `memoryPaging.ts` 的 `pageAfterEmptyRefetch` 作為單一頁次調整者，行為是對的，凍結的設計文字是錯的。因此下游（tcms-test-cases、U17 a11y-gate）若依凍結文字撰寫案例，會斷言錯誤行為。 | 以對齊修正的形式記錄：BR34.4／BR34.6／W4 以實作為準（背景重抓、empty 判定以重抓結果為準），並補一個 e2e 案例（21 至 25 則、第 1 頁刪一則、翻頁後原第 21 則出現）。凍結產出不回改，改以 corrections 檔取代並約束下游。 | New |
| R-02 | Major | construction/memory-page-ui/functional-design/functional-spec.md > 二（M4）、五 W5、八 OPEN-MP15-1；rules.md > BR31.2 | 前次 review-01 已提。`[M4]`=A 將入口頁捷徑渲染改派給 U14，但 `unit-of-work.md:188` 逐字把「入口頁捷徑（兩入口一個顯示條件）」列為 U15 的交付，U14 的依賴只有 U2、U13、U3，且 Bolt 順序上 U14 早於 U15，判定的定義方晚於第二個使用方，U14 到 U15 的邊不存在。落地結果：`frontend/src/pages/EntryPage.tsx:4,38` 已匯入並使用 `canSeeMemoryEntry`，所以實際是 INV-3 成立，但「誰交付捷徑」在單元清單與設計之間仍互相矛盾，OPEN-MP15-1 的「指派有效」判定只比對了 stage 游標，沒比對 Bolt 順序與交付清單。 | 在 corrections 檔或 unit-of-work 的修訂註記中明寫捷徑的實際交付單元與跨單元匯入方向，補上依賴邊或標明為何不需要；將 `[M4]` 列為需重新確認事項。 | New |
| R-03 | Minor | construction/memory-page-ui/functional-design/frontend-components.md > 四之一（user.id 未決視窗） | 前次 review-01 已提。設計未規定 `/me` 失敗後 `user.id` 永遠 undefined 的失敗出口。已落地程式 `frontend/src/pages/MemoryPage.tsx` 在 `isLoading` 為 false 且身分缺失時顯示 `memory-page-identity-error`，可區分的錯誤態已有，但無重試鍵（重試呼叫既有 refreshMe），與 BR32.3 的精神仍有差距。 | 於 corrections 補一條規則：身分未決的錯誤態必須可區分，並規定是否提供重試；補 e2e（攔截 `/api/auth/me`）。 | New |
| R-04 | Minor | construction/memory-page-ui/functional-design/functional-spec.md > 三（Sidebar 項列）、frontend-components.md > 一 | 前次 review-01 已提。`mockups.md` M0 畫的是側欄最上方的獨立項，設計與實作放在中段（`frontend/src/components/Sidebar.tsx:240-252`，原 DEMO 區塊位置），且未列為對齊修正（§三之一只列三處）。 | 要嘛移到 M0 所畫位置，要嘛將位置偏離登記為第四處對齊修正並說明理由。 | New |
| R-05 | Minor | construction/memory-page-ui/functional-design/functional-spec.md > 五 W3 第 3 步 | 前次 review-01 已提。W3 寫 `offset=<page*20>`，與 rules.md BR33.1 的 `(page-1)*pageSize` 矛盾；實作 `memoryPaging.ts` 的 `episodicOffset` 為 `(max(1,page)-1)*20`，故設計正本（W3）是錯的一邊。 | W3 改為與 BR33.1 同式並註明 page 為 1 起算。 | New |
| R-06 | Minor | construction/memory-page-ui/functional-design/rules.md > BR32.4；functional-spec.md > 二之一 | 前次 review-01 已提。情節區請求 limit=21，BR32.4 的「N 則／N+ 則」在最後一頁會讀成區內總數，違反本站自己推導的「畫面任何位置不得出現宣稱完整的計數」。實作 `MemoryZone.tsx:239` 以 `episodicOffset(page)+rendered.length` 加 hasNext 計「N+ 則」，已部分緩解，但語意仍是累計數而非設計寫的規則。 | 明定情節區標題的計數語意（累計至本頁，或不顯示計數）並同步 test id 的斷言範圍。 | New |
| R-07 | Minor | construction/memory-page-ui/functional-design/functional-spec.md > 三之一（「三處都是對齊修正」） | 前次 review-01 已提。已核可 M6 的其他陳述被靜默省略：「回入口」連結、稽核紀錄的揭露句、保存期限固定列、區標題副標。實作 `MemoryPage.tsx` 已保留稽核句與保存期限固定列，與「改為逐則保存至日期」的設計字面不同，設計與程式又多一處不一致。 | 逐項標為沿用、對齊修正或交 U14，並以實作現況為準更新。 | New |
| R-08 | Minor | construction/memory-page-ui/functional-design/rules.md > BR34.5；frontend-components.md > 五之一 | 前次 review-01 已提，且已落地程式仍有此缺陷：`frontend/src/memory/memoryApi.ts` 的 `deleteMemoryRecord` 對任何 404 一律回 `'already-gone'`，沒有檢查回應本文是否為帶 `detail` 的 JSON，路由錯配或反向代理的 404 會讓仍存在的記憶被移除並播報已刪除。 | 設計與實作同步收窄：僅在 404 且本文帶 `detail` 時視為已消失，否則視為失敗。 | New |
| R-09 | Minor | construction/memory-page-ui/functional-design/ 全部產出；缺少 corrections 檔 | 本次新提。凍結設計與已落地實作在多處分歧（R-01 的背景重抓、R-03 的身分錯誤態、R-06 的標題計數、R-07 的固定列），但同目錄沒有 `*-corrections.md`，下游無法分辨哪一邊是正本。 | 補一份 corrections 檔，逐項列出「設計字面、實作現況、以何者為準」。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 逐檔實讀（functional-spec.md、review-01.md、抽讀 rules.md 與實作） | 完成；rules.md 的 BR 摘要表為 19 條 | 前次發現未被處置；實作多處領先設計 |
| 實作抽查（memoryApi.ts、memoryPaging.ts、MemoryZone.tsx、MemoryPage.tsx、Sidebar.tsx、EntryPage.tsx） | 與設計有 R-01、R-03、R-05、R-06、R-07、R-08 所列分歧 | 以檔名與行號為證；未執行任何測試或建置 |
