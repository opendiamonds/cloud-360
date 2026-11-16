<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
- [2026-10-01T07:47:02Z] Interpretation: Q2=A；使用者確認 C1 已 LangGraph——核對 `cost_advice_agent.py` 確走 `langgraph_runtime`；codekb 舊「C1 仍 SDK」敘述過時。本輪範圍仍僅 A3。
- [2026-10-01T07:43:42Z] Interpretation: refactor Minimal：不重問 codekb 已鎖現況；出 7 題鎖定命名、迁徙範圍、LangGraph 樣式、SSE 不變式、gemini-3.7-flash、CLI 清理、驗證底線。
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
- [2026-10-01T07:55:31Z] Tradeoff: Q6=C 強制本輪移除 CLI。唯 SDK 呼叫點為 review_agent／wa_lens_engine；與 Q2=A 合讀為「A3 迁完且零 ClaudeSDKClient 後同 intent 移除映像 CLI」。容器內 LLM_PROVIDER=cli 不再支援。
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
