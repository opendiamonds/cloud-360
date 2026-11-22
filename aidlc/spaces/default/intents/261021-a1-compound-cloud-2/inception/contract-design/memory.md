<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
2026-11-08T09:20:00Z — C1 provider 欄位統一固定為小寫 "compound"（非 enum 聯集），確保向外部 n8n 服務的 payload 語意一致；若未來支援單雲模式，需透過 ADR 擴充 C1/C4 enum。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
2026-11-08T09:20:00Z — C2/C3 採 in-process Python call（非 HTTP）以降低跨網路延遲與錯誤複雜度；代價是 U1/U2/U3 只能在同一 Python process 部署，擴展需考量 worker pool。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
