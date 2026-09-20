<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-19T03:18:41Z — 使用者回覆「A」確認另開第二個 intent；未另選 Q2 scope，依先前建議以 workflow-selected `mvp` 起跑（23/33 stages、20 approval gates），產品邊界是否等於此 scope 交 Q8 確認。
- 2026-08-19T03:38:19Z — 使用者將 4 條 assumption 轉成 Q11–Q14，不先接受。
- 2026-08-19T05:07:18Z — Q11–Q14 作答後四條假設皆有對應決定，artifact 的 Assumptions 改為 None.
- 2026-08-19T05:11:13Z — reviewer iteration 1 NOT-READY（人工覆寫張力、警告送達不可測）；以 Q15／Q16 解消後送 iteration 2。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-19T03:18:41Z — Standard 深度目標 5–8 題；除 stage 必問 8 題外加 Q9（第一輪產品切片），因 [desc] 同時寫了 C1→C2→C3 與 first-pass MVP，不釐清會把整柱 FinOps 寫進 intent。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
