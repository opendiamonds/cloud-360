<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-11-06T03:40:00Z — Q1–Q5／Q6b 全 A：Session＋三核心＋Ui；行程內產物；同步 HTTP；Agent 掛核心行為；圖走公開 API。
- 2026-11-06T03:40:00Z — 使用者對 Q6「互通」的關切解讀為 Session 串場能力，而非獨立 Agent 匯流排（Q6b=A）。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-11-06T03:40:00Z — 放棄本輪 Postgres 產物表與 SSE，換取較小 schema／契約面；重載丟失為已知代價。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-11-06T03:40:00Z — 同步 HTTP 是否觸碰閘道逾時，待 build-and-test／staging 實測；必要時另開 SSE ADR。
