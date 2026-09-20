<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-19T08:15:00Z — Application Design 必做：C1 是新 bounded context（router／service／calculator／頁），不是改現有元件欄位。不 skip。本站只問 OQ-1 權限掛載、持久化表形、價目快取、SKU 對照、稽核 HTTP；三層形狀與禁止 Cost Explorer 不重問。
- 2026-08-19T08:25:00Z — Q1–Q5 全 A。另定 USD 兩位小數。點出 ensure_role_permissions_seeded(force=False) 全表 no-op，Construction 必須只補缺失 (role, story_id) 列。
- 2026-08-19T08:35:00Z — Reviewer READY（0 Major）。折入：coverage 為雲別 official_list｜manual_override_only；第一段不註冊 GET /banner；pricing_client 三分 PriceHit／Miss／Unsupported。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
