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
- 2026-09-20T17:30:29Z — 「openrouter 的 gemini flash 3.7」型號存在與否，先前判斷有誤已由使用者更正為 `google/gemini-3.7-flash`；本機端為 Claude Code CLI 的 Claude Sonnet。兩者屬實作層選擇，本階段不寫入產出，待 feasibility／nfr 階段定錨。
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
