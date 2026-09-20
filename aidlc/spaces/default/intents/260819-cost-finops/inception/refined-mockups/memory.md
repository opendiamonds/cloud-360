<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-19T07:50:00Z — Refined Mockups 必做：C1 有使用者可見 Cost 頁、Sidebar、CTA、橫幅，且 ideation 已有線框。不 skip。線框已定層級／CTA／超支標示／就地編輯／AA；本站只問圓餅實作、時數控件、橫幅釘點、SKU 密度、視覺契約。
- 2026-08-19T08:00:00Z — Q1–Q5 全 A：SVG 圓餅無新依賴；時數數字框非法不送出；橫幅釘在 Layout 主區頂；SKU／小時價就地表格；沿用既有 Tailwind，僅數字對齊／總額字級／危險色特化。建議路由 `/cost`、test-id 表寫進 mockups，精確 path 留 application-design。
- 2026-08-19T08:10:00Z — Reviewer iteration 1 READY（1 Major／2 Minor，未擋）。已折入：M5a／M5b ASCII、多圖橫幅可見字串形狀、RegionField 暫定 select。
- 2026-08-19T08:20:00Z — 使用者補充（Interpretation）：已超支時要用與 A1／A3 相同路徑的 AI agent 提供修改建議。本輪 C1 仍只交付標示與橫幅；agent 建議另開 intent，不夾帶進 260819-cost-finops。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
