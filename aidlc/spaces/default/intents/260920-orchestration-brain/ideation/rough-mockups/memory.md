<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
- 2026-09-21T08:59:32Z — **上游前提已失效，待以 Modify 模式回跳修訂**。本 intent 的 intent-capture 查證 V2 記載「成本／FinOps 能力完全不存在，`FinOps_Analyst` 只是 RBAC 角色名」，該事實在當時為真，但 `ut` 已於 2026-09-20T14:43Z 合併 PR #647（cost-estimation-finops），成本能力現已存在且規模不小：`backend/cost/` 套件含 `estimate_intake_router` 與 `advice_stream_router`；`/api/cost/v1/` 下 6 條端點，其中 `GET /sets/{set_id}/advice/stream` 為**串流式成本建議**；前端有 `CostPage`（路由 `/cost`，`can('C1','view')` 者登入即導向）；`schema_rbac.sql` 有 `archive_diagram_cost`、`archive_diagram_cost_line`、`archive_cost_audit_event` 三表。故第一版的問題不再是「要不要做一個會回『尚未提供』的空殼」，而是「大腦要怎麼編排一個已經存在、且自身也有串流的成本 agent」——這是不同的問題，不是同一問題的細節修正。受影響落點經逐一核對為 8 處：intent-capture 的 V2／[Q6]=C／[Q11]=B、`intent-statement.md` 的 Target Customer 成本列與 Initial Scope Signal、`stakeholder-map.md` 的成本關注者定位、feasibility 的 S 條目與能力表成本列、`constraint-register.md` 的 C-T9／C-S2、scope-definition 的 S3／S9 與 `scope-document.md`／`intent-backlog.md` 的分級與序 9。使用者已裁決**跳回 intent-capture 以 Modify 模式修訂**（非 feasibility——過期事實與 Q6／Q11 的決定都在 intent-capture）。未於本 session 執行的理由：AI-DLC 框架於本 session 期間由 2.7.0 升級至 2.9.0，指令介面與 stage 協定均已變更，而本 session 載入的是 2.7.0 協定；以舊協定驅動新引擎執行會動到生命週期狀態並重走三道關卡的操作，風險是污染稽核紀錄。應由新 session 以 2.9.0 協定執行。
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
