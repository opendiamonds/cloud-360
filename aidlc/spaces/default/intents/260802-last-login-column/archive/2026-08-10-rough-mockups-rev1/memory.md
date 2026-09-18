<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-04T00:48:32Z — Q5=B 引發的 scope 擴充依協定回跳 scope-definition 修訂重審後才回到本 stage 產出 artifact；本 stage 未擅自在 wireframe 中夾帶未核可的範圍。
- 2026-08-04T00:48:32Z — 逾期標示的圖示在 ASCII 線框以 (!) 表達（emoji ⚠ 非基本 ASCII，違反線框字元標準）；實作圖示樣式留 refined-mockups。
- 2026-08-04T00:48:32Z — 載入／錯誤態解讀為「沿用既有頁面模式」，不重新設計 — 本 feature 是加欄不是改版（載入模式除外於 PU-5 的卡片改造範圍）。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-04T00:56:50Z — reviewer iteration 1 NOT-READY 修正：ASCII box 改以腳本產生保證每行字元數一致（手寫 CJK 混排必然數錯）；user-flow 補流程圖；tooltip 文案改標示例；小螢幕註記補 landmark。手寫 ASCII box 含 CJK 時應一律用腳本驗證字元數。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-04T00:48:32Z — 小螢幕卡片線框只畫一種佈局（標籤: 值 逐行式），未併列多方案：PU-5 是剛擴充的範圍，先給單一基準讓 reviewer 與 gate 有具體對象，替代方案留 refined-mockups 探索。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-04T01:00:02Z — reviewer iteration 2 的 Finding 5（Minor）：wireframes Assumptions 的 skeleton 句掛了不對應的 [Q5] 標籤；READY 後不回改（會使 review receipt 失效且 iteration 已用罄），refined-mockups 修訂該檔時一併移除。
- 2026-08-04T00:48:32Z — 響應式斷點值（以既有內容破版處為準）留 refined-mockups 定值。
- 2026-08-04T00:48:32Z — 既有頁面是否已有 skeleton 載入慣例，refined-mockups 時查證對齊。
