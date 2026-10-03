<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-09-26T10:35:00Z — `delivery-planning:c6`（破壞性契約變更與其消費端不得分批）的逐字觸發條件是「凡涉及**既有**端點回應形狀變更的 Bolt 切分」。`U2` 是全新的 WebSocket 訊息型別來源，沒有任何既存消費端會因它上線而壞，故判定**不適用**，`U2` 留 B1、`U13`／`U14` 在 B6。判定已以 `[D7]` 提交使用者並取得採納，論證寫在 `risk-and-sequencing-rationale.md` 第五節供日後覆核
- 2026-09-26T10:40:00Z — `U13` 與 `U14` 同批的理由是 `[D3]`=B 的信心假說判準（閘道與其唯一消費端分開後，前者湊不出可展示成果），**不是** `c6` 的破壞性變更理由。兩者在產出中明確區分，避免下游把它們讀成同一條約束
- 2026-09-26T10:44:00Z — `team-formation`（1.5）未執行（本輪實查 `ideation/` 只有五個站的產出），依 stage 檔規定所有 Bolt 由 `aidlc-developer-agent` 執行。故 `team-allocation.md` **不是 Program Board**——Program Board 是團隊數大於 1 才有的東西；本檔以「人在哪裡介入」三類點取代

- 2026-10-03T03:25:09Z — **本站五份產出早於能力 11／12／13，覆蓋率是實測的 0**。開工先 `ls` 本站 record 目錄（依 `rough-mockups:b9a662f5`），五份產出 ＋ `memory.md` 全部在 2026-09-29。以腳本掃 **29 個關鍵詞**（三個能力名、`US11`–`US13`、`FR11.`–`FR13.`、七個新單元名、`U18`–`U24`、`K-15`–`K-18`、`X-04`、`ADR-0019`、`ws-contract`）：**28 個零命中**，唯一有命中的 `ws-contract`（7 處）指的是既有的 `U2 brain-ws-contract`，與新單元無關。既有 **9 個 Bolt（B1–B9）涵蓋 17 個單元、20 則故事**；新增的 **7 個單元與 11 則故事零 Bolt 歸屬**。
- 2026-10-03T03:25:09Z — **`UG-3` 在本站有一個具體落點，而它是一句已經變假的話**。`bolt-plan.md:141` 逐字寫「這是 `[RA:NFR5]` 的承載機制，而**既有兩道漂移閘門對 WebSocket 完全無效**」——那是 B1 的「做完會證明什麼」，也是當時把 `U2` 留在 B1 的理由（讓那道缺失的閘門提早五個 Bolt 上線）。實測該閘門**已交付**：`ws-contract.json`、`backend/services/brain_ws_contract.py`、`backend/scripts/dump_ws_contract.py`、`backend/tests/test_ws_contract.py`、`frontend/src/types/ws-contract.d.ts` 全部存在，`inception/decisions/0019-ws-contract-gates-and-generator-supply-chain.md` 即 ADR-0019。**`U2` 留在 B1 的那個理由已經實現、不再是待辦**；新增的 WebSocket 訊息型別要納入**既有**那份契約。這不是重排 Bolt 的理由（`U2` 本來就在最前面），而是那句論證必須就地更正，否則下游會以為閘門還沒有。
- 2026-10-03T03:25:09Z — **既有 B6 已集中 13／20 則故事（65%），而本輪要再加 11 則**。那個集中度是上一輪自己查出並記為「本計畫最大的風險項」的（`project.md` 的 `delivery-planning:bcd2e92c`：照單元與契約推導出的序列在依賴圖上完全合規，卻把大部分使用者可見價值壓在單一 Bolt 上，而這個事實在單元層級的任何檢查裡都看不到）。本輪的 11 則新故事**不會自動改善它**——`US11`／`US12` 的 UI 落在 `U23`／`U24`，兩者在依賴圖上都排在 service 層之後，若照同一套推導就會再堆出第二個高峰。**開工前就要把「每個 Bolt 完整交付幾則故事」當成設計輸入而非事後實算**，這是上一輪教訓的可執行形式。

- 2026-10-03T03:40:00Z — **我提給使用者的四個 Bolt 切分選項全部不成立，而只要跑一支十行腳本就會知道**。DP1 的 A／B／C／D **都假設新 Bolt 可以附在既有九個之後**。使用者選了 A，我接著要產出時才把提議的位置代入 DAG 跑合規檢查——查出 **6 處順序違反**：`U12`（B4）依賴 `U22`（提議 B10）、`U13`（B6）依賴 `U19`／`U20`／`U22`、`U17`（B8）依賴 `U23`／`U24`。既有 `bolt-plan.md` 把「每條邊的被依賴方都在同一或更早的 Bolt」寫成**以腳本逐條驗證過的硬規則**，所以四個選項各違反它 6 次。**新單元不是疊在既有序列之上，而是插在它中間**——這件事在單元層級看不出來，只有把 Bolt 位置代入邊集合才會浮現。**可執行補強**：為新單元提議 Bolt 位置**之前**（不是之後）就跑一次 DAG 合規檢查，把結果寫進選項說明。這與 `project.md` 已記的「提問前該算的不只是產出裡的數字，也包括選項代價裡的數字」同根，但那條講的是**成本**，這條講的是**選項本身是否可行**——一個不可行的選項不是代價被低估，是它根本不該出現在選單上。
- 2026-10-03T03:40:00Z — **我回頭向使用者說明並請其重選，而他的答覆是「已修正為最佳實踐就好」——那是把判斷權交回給我，不是省略判斷**。我據此選了「編號是識別字、順序另列一張表」：不重新編號的理由與 `units-generation` 修訂 4 拒絕插號同形（B1–B9 的編號在五份產出、`units-generation` 的交接表與 `contract-design` 裡被引用），而 2.9 本來就擁有「排序」這個交付物。**選完之後仍以腳本驗證**：交錯順序 `B1 → B10 → B2 → B11 → B3 → B12 → B13 → B4 → B5 → B6 → B7 → B8 → B9` 下，46 條邊 **0 處違反**、24 個單元零遺漏、31 則故事全部有歸屬。被授權自己決定不等於可以不驗。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-09-26T10:30:00Z — **本檔不含任何評分表**（WSJF、RICE、工時、時程）。stage 檔的範例提到優先序評分，但 `project.md` 的 `scope-definition:c5` 逐字寫「沒有真實輸入的相對分數是虛假精確」，而本 intent 的價值、急迫性、工量三項都沒有實證來源。排序以逐條的風險與依賴論證表達
- 2026-09-26T10:32:00Z — 不重問 walking skeleton 立場（`delivery-planning:c20`）。`team.md` 的 `## Walking Skeleton` 已定案 `skeleton: off`，本站直接引用其逐字理由

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-09-26T10:50:00Z — B1 裝了四個單元加五項跨單元定案，是本計畫最重的 Bolt。取舍：全 17 個單元中**只有** `U1`／`U2`／`U3`／`U6` 在自身與整條上游都沒有未決事項（實算），其餘 13 個各繼承 1–9 項阻塞。把定案點拆出去會讓第一個 Bolt 建在未定案的地基上；不拆的代價是 B1 可能裝不下（記為 R7，處置是拆成兩個 Bolt 並回報，而非把未定案推給後續）
- 2026-09-26T10:55:00Z — `U15`（記憶頁）技術上 B3 之後即可動工，卻排到 B7。取舍：提前做會讓頁面在寫入端落定前是空的，而「功能正常但沒資料」與「功能是壞的」在畫面上分不出來——一個分辨不出兩者的 Bolt，它的信心假說是假的。此約束**不在依賴圖上**，只有把「這個 Bolt 要證明什麼」代入才浮現，且已標明為可覆寫
- 2026-09-26T11:02:00Z — 接受 B6 的價值集中（13/20 則故事）而不拆它。另一条路是把 B6 拆成「先閘道與最小對話、再其餘畫面元件」，代價是 `U13` 單獨那半湊不出可展示成果（部署一個沒人呼叫的 WebSocket 端點）。集中是**結構性的**：`U14` 出現在 13 則故事的單元清單裡且在依賴圖第 5 層——入口頁是幾乎所有故事的最後一哩

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-09-26T11:05:00Z — **本站的疏漏，由機械檢查攝下**：四份產出寫完後，`upstream-coverage` sensor 回報 `unreferenced = ['stories', 'mockups', 'unit-of-work-story-map', 'team-practices']`。這不是 sensor 繁文縟節——我把九個 Bolt 全部照**單元與契約**推導，**沒有一次對回使用者故事**。補上 Bolt → 故事對應（以「故事的**最後**一個單元落在哪個 Bolt」實算）後，13/20 的集中分佈才浮現並成為 R9。若沒跟 sensor，這個平計畫最大的風險會整站遺漏
- 2026-09-26T11:05:30Z — `team-practices` 在本 intent **不存在**：`practices-discovery` 只在 `260819-cost-finops` 與 `260802-last-login-column` 跑過，內容已晉升至 `aidlc/spaces/default/memory/team.md`。本站引用的是後者，並在產出內寫明這件事，不讓下一個人回頭找一份不存在的檔
- 2026-09-26T11:06:00Z — **兩類緓線沒有機械保證**：B5 的進入條件（`OQ-10`＋`OQ-4`）與 B9 的執行與否（`OQ-13`），其落點與轉移目標**皆為 CONDITIONAL**，兩站都可能一併 skip。本計畫在 `bolt-plan.md`、`team-allocation.md` 與 `verification/phase-check-inception.md` 三處明寫「須重新提交使用者裁決，不得由實作者當場決定」——但**明寫不等於強制**
