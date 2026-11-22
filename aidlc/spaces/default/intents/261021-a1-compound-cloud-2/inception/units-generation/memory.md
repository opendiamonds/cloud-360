<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-11-08T08:37:00Z — 建構單元劃分為 U1 (gateway), U2 (builder), U3 (agent), U4 (ui)，拓撲依賴為嚴格單向無環鏈，各單元責任邊界與測試檔案完全解耦。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-11-08T08:37:00Z — 將 U1 (圖示閘道) 作為獨立 library 建構單元先行交付，雖增加單元數量，但能讓 U2 幾何測試在完全無需 mock 外部網路的情況下以純本地 fallback 順暢執行。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
