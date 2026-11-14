## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U15 memory-page-ui 的 nfr-requirements 產出（performance、security、tech-stack、traceability）整體自洽。11 條 inception NFR 都有逐條處置，孤兒要求（UIP-n、SEC-U15-n、TS-U15-n）逐一寫明理由，ADR-0006 四面向的判定與 functional-spec §九之二 一致。我抽查了出貨程式，行號與事實大致相符：memory_service.py:72-73 的 50／200 上限、_visible_to、memory_types.py:100 的 SCOPE_WIDENING_ROLES、AdminPage.tsx:198-203 的補償先例、DeleteConfirmRow 的「此刪除會被記錄」文案，以及 frontend/src/memory 與 components/memory 下沒有儲存識別字。主要缺口有兩個 Major。第一，沒有任何可測要求約束「刪除後分頁不漏列」，且 TS-U15-4 宣稱 cancelled flag 能解決的競態，後續 nfr-design review-01 R-01 已證明它管不到。第二，本站省略了可靠性與無障礙兩類 NFR，而 U17 a11y-gate 明確依賴本單元。兩項皆不阻擋實作，但應在關卡上由人裁決。因 Critical 為 0、Major 為 2，判 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/memory-page-ui/nfr-requirements/tech-stack-decisions.md TS-U15-4 與 TS-U15-6；performance-requirements.md UIP-3、三之一 | UIP-3 只規定刪除的請求預算（1 次 DELETE 加至多 1 次 GET），沒有任何「刪除後翻頁不漏列、不誤顯示 empty」的可測不變量。TS-U15-6 明知先例 AdminPage.tsx:198-203 靠補償重抓防漏列，卻把正確性要求只放進交接表，沒有寫成 NFR。TS-U15-4 又稱 cancelled flag「同時解決翻頁時舊請求晚到覆蓋新頁的競態」。但補償重抓由刪除的事件處理函式發出、不在 useEffect 內，cancelled flag 管不到，nfr-design review-01 的 R-01 已查出此點（先例實際用 requestSeq 序號比對，AdminPage.tsx:124-131）。本站的相容性判定因此過度樂觀，且留下「請求預算合規但資料漏列」仍可通過驗收的空隙。 | 在 performance-requirements 或 security-requirements 補一條可測不變量，例如「刪除一則情節記憶後，依序翻頁所見的集合不漏列、不重複，刪空第一頁不顯示 empty」，並指定 e2e 以 page.route 模擬 offset 位移來驗證。同時更正 TS-U15-4 的相容性欄：cancelled flag 只涵蓋 effect 內的抓取，事件處理函式發出的重抓需要序號機制。 | New |
| R-02 | Major | construction/memory-page-ui/nfr-requirements/performance-requirements.md 三之三 與 security-requirements.md 四之一（R-03 列）；整個目錄缺 reliability／accessibility 文件 | 本站宣稱 reliability 屬 service 專屬、不適用 ui 單元，但 ui 單元仍有真實的可靠性與無障礙 NFR。(1) 可靠性：三之三承認 login() 吞掉 /me 失敗會使 user.id 永遠 undefined、頁面無限轉圈，稱之為「可靠性缺口」，卻只放進交接表，並註明「非使用者裁決範圍」。沒有任何要求規定 /me 失敗、列出 GET 失敗、DELETE 失敗時的畫面行為，也沒有「不得無限載入」這類可測條款。(2) 無障礙：unit-of-work.md 第 186-205 行與 unit-of-work-dependency.md 第 129 行都顯示 U17 a11y-gate 依賴 U15（N-9 的 axe 掃描對象之一），但本站四份文件對 a11y、axe、aria 零命中。TS-U15-7 提到 LiveRegion 卻只作為技術選擇，沒有成為要求。實作 MemoryPage.tsx:20-26 已處理 /me 失敗，說明需求面被補在程式裡，卻沒有進入需求文件。 | 補兩條要求。其一，可靠性：「三個清單與刪除的失敗態都有可見的文字提示，且 /me 失敗時不得無限載入」，附 e2e 驗證。其二，無障礙：「/memory 頁通過 axe 掃描、刪除結果透過 live region 播報」，並指向 U17 為量測擁有者。或者在 traceability 明確宣告這兩類為「承接於他單元」，寫出承接者與依據。 | New |
| R-03 | Minor | construction/memory-page-ui/nfr-requirements/security-requirements.md SEC-U15-2 | SEC-U15-2 寫「若不存在則記為交接缺口」，但沒有給出查證結果，留成條件句。實際上後端測試已存在：backend/tests/test_memory_authz.py:249（test_A5 非擁有者刪除得 404）與 :319（test_A7 平台管理者不能刪他人記憶）。產出凍結後這個條件句永遠不會被解決，下游讀者要自己再查一次。 | 在 SEC-U15-2 或交接表就地寫明已查證，測試位置為 test_memory_authz.py:249 與 :319，並把條件句改為已確認的事實。 | New |
| R-04 | Minor | construction/memory-page-ui/nfr-requirements/security-requirements.md NFR4.90、NFR7.90；traceability.json NFR4／NFR7 | NFR4.90 標為「繼承」NFR4，但 NFR4 的原文是大腦 session 與工作狀態放 Redis、可測不變量是重啟 backend 後脈絡可還原，與「前端不寫瀏覽器儲存」不同題。「前端同構對應」是合理延伸，但應標為 SEC-U15-n 孤兒或明寫「類比而非繼承」。NFR7.90 同理：NFR7 要求「靜態儲存與傳輸的加密須於設計階段明確」，本站只回答了用戶端這一端，伺服端靜態加密的擁有者（U5 memory-data 或 U8）沒有被點名，讀者看不出該要求最終落在哪裡。 | 將 NFR4.90 的父條關係改寫為「類比」，或改以孤兒宣告。在 NFR7.90 補一句，指出伺服端靜態加密與傳輸要求由哪個單元承接（並引用其產出位置）。 | New |
| R-05 | Minor | construction/memory-page-ui/nfr-requirements/security-requirements.md SEC-U15-5 與 NFR4.90 | SEC-U15-5 的主要驗證寫「code review 可判」，不是機械條件，與 NFR4.90 以命中數為 0 的掃描形成落差。出貨的 frontend/src/memory/memoryApi.ts:74、:79、:105、:111 有 4 處 console.warn，內容只含 kind 與 status，目前合規，但沒有任何機械檢查防止日後把記憶內容放進去。另外 SEC-U15-4 讓他人數值 id 出現在 data-owner-user-id 屬性中，卻沒有說明這是刻意取捨（前次 nfr-design review-01 R-07 已提）。 | 補一條 grep 型不變量，例如「console.* 的引數不得含 content、record、item 變數名」，並在 SEC-U15-4 註明 data 屬性是刻意取捨及其理由（API 回應本來就帶該 id）。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 出貨程式抽查（memory_service.py、memory_types.py、AdminPage.tsx、api.ts、frontend/src/memory、components/memory） | 引用的行號與事實大致相符；console.warn 4 處僅含 kind／status；components/memory 與 memory 目錄下無 localStorage／sessionStorage／indexedDB 命中 | 設計主張與已落地程式沒有矛盾；NFR4.90 與 NFR7.91 皆已落實於 DeleteConfirmRow.tsx:50 |
| 後端授權測試存在性（test_memory_authz.py） | test_A5 :249 與 test_A7 :319 存在 | SEC-U15-2 的交接缺口條件不成立，見 R-03 |
| 上游承接（units-generation U15 條目、story map US4.2／US4.4、NFR1-NFR11 逐條處置） | 11 條 NFR 皆有處置，6 條 UIP、5 條 SEC、9 條 TS 皆有孤兒理由 | 承接完整；缺口只在 R-01、R-02 所述的兩類要求 |
