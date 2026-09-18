<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-09T10:00:00Z — 三個 stage 範例題目不問，因既有規則已定案：①WSJF 數值評分 —— `project.md` 已載明「單一決策者、全 Must、依賴序已定的 backlog 不做 WSJF／RICE 數值評分，沒有真實輸入的相對分數是虛假精確」；②walking skeleton —— `team.md` Q3 定案 `skeleton: off`；③外部依賴 —— 本 intent 全部落在自有 repo 與自有 staging，無外部 API、無資料可得性窗口、無外部團隊交接，`external-dependency-map.md` 將為近空白（如實記載而非虛構條目）。
- 2026-08-09T10:00:00Z — team allocation 為單人：`team-formation`（1.5）在本 workflow 標記為 `[S]` skipped，且本專案為單一決策者。stage 檔的「當 1.5 SKIP 時預設全部由 developer agent 執行」適用。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-09T10:20:00Z — Bolt 合併的判準是「能不能湊出一個有意義的信心假說」，不是元件數量的平均分配。五單元各成一個 Bolt 會產生兩個沒有可展示成果的 Bolt（U2 單獨＝回應多兩個欄位但無讀取端、U5 單獨＝一個型別檔）；合併成三個之後每個 Bolt 都有可驗證的整體。
- 2026-08-09T10:25:00Z — 排序只有**一個真正自由的變數**（U4 的位置），其餘由 DAG 強制。因此不做 WSJF 不只是遵守既有規則，也是實質正確的 —— 替五個單元編三個維度的分數再相除，產出的排序仍然只由那一個變數決定，分數不帶來額外資訊。
- 2026-08-09T10:30:00Z — U4 排最前的決定性理由是**驗收依賴**而非風險：deploy-on-merge 之下，若顯示鏈先上而權限未上，那些部署對主要 persona 完全不可驗收。風險（失敗模式最隱蔽）是第二理由，零耦合是第三 —— 三者同向，但即使只有第一條也足以定案。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-09T10:35:00Z — 已向使用者揭露但未處置的成本：Construction 的 3.1〜3.5 全為 `for_each: unit-of-work`，5 個單元表示逐單元的 stage 執行次數至多 25 次。其中 3.3（NFR 設計）與 3.4（基礎設施設計）為 CONDITIONAL，而本 intent 依 AD-5 完全不動基礎設施 —— 若判定不適用可降至至多 15 次。此屬 workflow plan 的重塑（compose／recompose），非本站決定，已擺在使用者看得到的位置但未代為執行。
- 2026-08-09T10:35:00Z — 階段邊界驗證的八項缺口全數帶入 Construction，各有承載單元與 Bolt（見 `<record>/verification/phase-check-inception.md`）。其共同性質是來自 repo 既有的測試涵蓋現況，非本 intent 引入。
- 2026-08-11T00:30:00Z — 本輪的關鍵發現不是來自任何上游 artifact，而是把「每個 Bolt 邊界都是一次真實部署」代入既有計畫後浮現的：U2 的 envelope 是破壞性契約變更，原計畫把它放在 B2、消費端在 B3，deploy-on-merge 之下 staging 的管理頁會壞在兩次部署之間，而三道相關 CI gate 全綠（`tsc -b` 對 `res.json()` 無感、六個 e2e 無一進管理頁、docker-build 只驗建置）。處置為 avoid（調邊界）而非 mitigate。
- 2026-08-11T00:30:00Z — 一般化後值得帶走的是：**deploy-on-merge 下，破壞性契約變更與其消費端之間存在一條隱含的「同批次」約束，它比 DAG 邊更強** —— DAG 只說先後，這條說「不得分批」。它不出現在依賴圖上，只有實際代入部署模型才會浮現。
- 2026-08-11T00:30:00Z — B2 縮為 U1 單一單元後，必須重新論證它湊得出信心假說（前一版明文說 U1 單獨部署「湊不出有意義的假說」）。重新檢視後結論相反：U1 的「補欄在既有環境真的生效」正是計畫既有記載中**最容易靜默落空**的一條（無自動化驗證、承接方式本來就是部署後人工核對資料庫），單獨拉出來先證偽反而是收益。前一版的判斷失誤在於把「UI 上看不見」等同於「無法驗收」。
- 2026-08-11T00:32:00Z — 本站的 stage 檔**未宣告 reviewer**（`grep "^reviewer" delivery-planning.md` 零命中），我卻先發了一個 REVIEW_REQUESTED。處置：不留懸空的 receipt，改以 inline 自行查證關鍵事實後補上 REVIEW_COMPLETED 並在此記明它不是 dispatched reviewer 的產物。查證內容：`AdminPage.tsx:32` 的 `users` state 型別為 `DbUser[]`、`:56` 為 `.then(setUsers)`、`:178` 為 `users.map(...)` —— envelope 一到，`users` 成為物件、`.map` 不是函式，管理頁確實會壞。Q4 的前提為真。
