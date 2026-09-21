<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
- 2026-09-20T17:55:24Z — Q5 定案為「本次一併建立專案／系統階層」，使本 intent 從「加一層編排」擴為「同時建立新的核心資料模型」。此決定會觸發 project.md 的 blocking 規則（schema_rbac.sql 與 DEPLOY.md 必須同步），下游 feasibility 與 scope-definition 必須把它當成第一級範圍項而非附帶工作。
- 2026-09-20T17:30:29Z — 描述中的「專案 → 系統 → 架構圖」階層在 repo 中不存在，故不視為既有事實而改列為 Q5 的待決問題；`schema_rbac.sql` 只有 users→user_diagrams，backend 全樹 `system_id` 命中 0 次。若逕自當成既有階層，整份需求會建立在一個不存在的資料模型上。
- 2026-09-20T17:30:29Z — 描述點名的「成本及 FinOps agent」在 repo 中只有 `FinOps_Analyst` 這個 RBAC 角色，沒有任何成本資料、服務或模組，故 Q6 把「編排既有能力」與「同時建成本能力」拆成不同選項，讓範圍差異顯性化。
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
- 2026-09-20T17:55:24Z — 收齊答案後的矛盾偵測抓到兩處跨題不一致（Q2 的管理者 vs Q7 的共享範圍、Q2 的成本關注者 vs Q6 的成本空殼），依 stage-protocol §3 加開 Q10／Q11 當場定錨並回寫問題檔，未讓歧義流入下一階段。問題數因此由 9 增為 11。
- 2026-09-20T17:30:29Z — 依 project.md 的 `intent-capture:c3`，出題前的唯讀查證結果（V1–V6）寫進問題檔的獨立「查證紀錄（非來源）」區塊，未登錄進 `## Sources` register；register 僅保留 [desc]／[scope]／[memory:M1–M3] 三種允許形式。
- 2026-09-20T17:30:29Z — 問題數為 9 題，略高於 Standard depth 的 5–8 題指引。理由是本 intent 橫跨編排框架、session 層、三種記憶、串流、推播與多意圖識別六個面向，且其中兩個面向（專案階層、成本能力）的前提在 repo 中不成立，壓到 8 題以內會使其中一項無法被問到。
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
- 2026-09-20T17:55:24Z — Q11 定案為 B（空殼要能正確回「尚未提供」）而非 C（實作最小成本能力）。取捨是：保住「成本關注者」這個角色在第一版有可驗證的行為（路由正確、回覆明確），同時不把成本資料來源這個獨立子系統拉進本 intent——而本 intent 已因 Q5=B 承擔了新資料模型。
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
- 2026-09-21T08:59:32Z — **上游前提已失效，待以 Modify 模式回跳修訂**。本 intent 的 intent-capture 查證 V2 記載「成本／FinOps 能力完全不存在，`FinOps_Analyst` 只是 RBAC 角色名」，該事實在當時為真，但 `ut` 已於 2026-09-20T14:43Z 合併 PR #647（cost-estimation-finops），成本能力現已存在且規模不小：`backend/cost/` 套件含 `estimate_intake_router` 與 `advice_stream_router`；`/api/cost/v1/` 下 6 條端點，其中 `GET /sets/{set_id}/advice/stream` 為**串流式成本建議**；前端有 `CostPage`（路由 `/cost`，`can('C1','view')` 者登入即導向）；`schema_rbac.sql` 有 `archive_diagram_cost`、`archive_diagram_cost_line`、`archive_cost_audit_event` 三表。故第一版的問題不再是「要不要做一個會回『尚未提供』的空殼」，而是「大腦要怎麼編排一個已經存在、且自身也有串流的成本 agent」——這是不同的問題，不是同一問題的細節修正。受影響落點經逐一核對為 8 處：intent-capture 的 V2／[Q6]=C／[Q11]=B、`intent-statement.md` 的 Target Customer 成本列與 Initial Scope Signal、`stakeholder-map.md` 的成本關注者定位、feasibility 的 S 條目與能力表成本列、`constraint-register.md` 的 C-T9／C-S2、scope-definition 的 S3／S9 與 `scope-document.md`／`intent-backlog.md` 的分級與序 9。使用者已裁決**跳回 intent-capture 以 Modify 模式修訂**（非 feasibility——過期事實與 Q6／Q11 的決定都在 intent-capture）。未於本 session 執行的理由：AI-DLC 框架於本 session 期間由 2.7.0 升級至 2.9.0，指令介面與 stage 協定均已變更，而本 session 載入的是 2.7.0 協定；以舊協定驅動新引擎執行會動到生命週期狀態並重走三道關卡的操作，風險是污染稽核紀錄。應由新 session 以 2.9.0 協定執行。
- 2026-09-20T17:30:29Z — 「openrouter 的 gemini flash 3.7」型號存在與否，先前判斷有誤已由使用者更正為 `google/gemini-3.7-flash`；本機端為 Claude Code CLI 的 Claude Sonnet。兩者屬實作層選擇，本階段不寫入產出，待 feasibility／nfr 階段定錨。
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
