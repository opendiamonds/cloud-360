<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-19T05:57:06Z — CONDITIONAL 適用：本 intent 有使用者可見的成本畫面、Sidebar 入口、產圖後 CTA 與進產品橫幅，屬 user-facing UI，執行 rough-mockups。
- 2026-08-19T06:20:00Z — reviewer F1：刪頁面級「每日時數」，時數只在資源列就地改（Q1/Q4 列級模型）。
- 2026-08-19T06:20:00Z — reviewer F2：頁首改圖下拉；新增空狀態 2a；user-flow Flow 2 寫側欄落地（無圖／未選／有圖預選上次選擇）。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-19T05:57:06Z — 不重問圓餅是否要做、要不要 inbox、Sidebar 是否按故事大類分層（皆已由 intent／feasibility／project.md 定案）。
- 2026-08-19T05:57:06Z — 省略「有無品牌指南」專題：沿用既有 Cloud-360 畫面模式，加欄／加頁不另開設計系統。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-19T05:57:06Z — 6 題：層級、CTA 落點、超支畫面標示、覆寫操作、無障礙／裝置、第二段預算區塊位置。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
