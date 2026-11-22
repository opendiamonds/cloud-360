<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
2026-11-08T13:48:00Z — U1 圖示閘道確立在程序內引入 @lru_cache(maxsize=128)，確保多雲拓撲重複節點之圖示查詢在記憶體中極速命中，避免多次跨網路 HTTP 呼叫。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
2026-11-08T13:48:00Z — Fallback 40x40 灰底文字 SVG 文字截取前 4 字元大寫置中，取捨字串完整度以換取在小尺寸節點上的排版美觀性與高對比清晰度。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
