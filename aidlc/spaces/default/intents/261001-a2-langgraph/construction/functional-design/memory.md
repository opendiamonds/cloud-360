<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
- [2026-10-01T08:14:46Z] Interpretation: zero-Unit refactor FD：不重問已核可 FR；6 題鎖定 graph 邊界、Lens 結構化輸出、SSE 映射、失敗語意、前端零變更、雙路徑測試（回應 R-04）。
- [2026-10-01T08:20:51Z] Interpretation: 產物鎖定雙獨立 graph、Lens 結構化輸出、suggestion_delta SSE、前端零變更、硬失敗上拋、零 SDK 後移除 CLI、Review+Lens 雙測試。
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
