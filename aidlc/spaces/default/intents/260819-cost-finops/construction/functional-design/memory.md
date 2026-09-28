<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-20T01:20:00Z — Construction 第一個 unit 為 `cost-calculator`（library；yaml 兩根之一）。Walking skeleton 依 team.md 定 `off`。本 unit 三題只問捨入、圓餅歸屬、非法輸入；公式不重問。
- 2026-08-20T01:28:00Z — Q1–Q3=A：HALF_UP 出口一次；category 由呼叫端；負數 ValueError。
- 2026-08-20T01:35:00Z — `cost-calculator` FD iteration 2 READY（0 Major）。`cost-schema-rbac` 為下一 unit（spec）；Q1–Q4=A：只 INSERT 缺失種子、44 列 C1* 矩陣、NUMERIC(12,2)、三件套 + `_ensure_cost_schema()`。
- 2026-08-20T01:50:00Z — 五 unit FD 初稿完成；calculator/schema-rbac/api/ui/budget-banner 皆 reviewer READY（含 slotRegistry、RegionField 常數來源等修補）。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
