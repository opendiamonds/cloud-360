<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-06T12:18:57Z — stage 檔的六題範例問題僅兩題與本 intent 相關（未決項交接、go/no-go 建議）；其餘四題依 learned rule 省略：stakeholder 同意（單一決策者已逐 gate 核可）、預算資源（feasibility Q5 已確認無阻塞）、mockups 共識（rough-mockups gate 已兩度核可）、market research 支撐（該 stage 依 scope 跳過）、mob 編制（team-formation 依 scope 跳過，單人決策者＋AI agents）。省略清單同步記於問題檔前言。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-06T15:45:30Z — initiative-brief 的 Assumptions 清單與 Q1 的五項未決項逐字對應，Q1 作答即為該清單的人工確認，不另設重複的 Assumption Confirmation 關卡；同一清單雙重確認徒增儀式成本。
- 2026-08-06T15:45:30Z — decision-log 採「逐站表格」而非時間軸流水帳 — 交接讀者要查「哪一站定了什麼」，完整時間序已由 audit shard 保存，不重複。
- 2026-08-06T15:45:30Z — phase-check 對 PU-5 的 feasibility backing 判定為「間接涵蓋（可接受）＋非阻擋警示」而非重開 feasibility：純前端改造無 schema 觸發，回歸風險已記錄且有 inception 檢驗點，重開上游的成本不成比例。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
