<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
- 2026-09-21T07:09:49Z — 抽象的衝突清單不足以讓人察覺答案讀反；**具體呈現「照此執行下一步會產出什麼」才有效**。本站先以矛盾偵測列出 S9 結果與 [Q1]／[Q3]／[Q5] 的三處衝突並明示「方向可能讀反」，使用者回覆「沒反，就是這樣」；直到 S10 把後果具體化為「兩項 Must 各自依賴一項 Should，故 Must 集合無法獨立交付」，使用者才主動更正為 8 Must／2 Should。下次遇到「答案與多處上游定案衝突且疑似讀反」時，直接推導到下一步的具體產出，不要停在衝突清單。
- 2026-09-21T02:56:24Z — feasibility 的 [F8] 是單選題，使用者選「有預算或成本上限」，**未選中**「有目標時程」。依 `scope-definition:c1`（未選中的選項不得被當成排除），時程並未被回答，故本站以 S7 補問硬期限，而非推定為「無期限」。
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
- 2026-09-21T07:09:49Z — S9 的分級曾被記為反向（降 8 項、Must 僅 2 項）並據以在 S10 寫出「Must 集合無法獨立交付」的發現。使用者更正後，本站同步改了三處：S9 的答案與後果段、S10 的先行發現段（依賴方向由 Must→Should 改為 Should→Must，結論由「阻塞」改為「可獨立交付」）、以及「三處衝突失效、不得帶入 scope-document」的明記。依 `rough-mockups:rev1-c10`，更正須一路追到最下游的落點。
- 2026-09-21T02:56:24Z — 依 `scope-definition:c5`（單一決策者、依賴序已定的 backlog 不做 WSJF／RICE 數值評分——沒有真實輸入的相對分數是虛假精確），本站的 intent-backlog 將以 MoSCoW ＋ 依賴序表達優先，不產生任何數值分數。決策者為單一人由 intent-capture [Q8]=A 確認。
- 2026-09-21T02:56:24Z — stage 檔 Step 4 提及 value stream map，但 `produces` 清單未列該檔。依 `scope-definition:c3`（produces 清單是 artifact 集合的正式來源），value stream map 將併入 `scope-document.md` 的段落表達，不自創新檔。
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
- 2026-09-21T08:59:32Z — **上游前提已失效，待以 Modify 模式回跳修訂**。本 intent 的 intent-capture 查證 V2 記載「成本／FinOps 能力完全不存在，`FinOps_Analyst` 只是 RBAC 角色名」，該事實在當時為真，但 `ut` 已於 2026-09-20T14:43Z 合併 PR #647（cost-estimation-finops），成本能力現已存在且規模不小：`backend/cost/` 套件含 `estimate_intake_router` 與 `advice_stream_router`；`/api/cost/v1/` 下 6 條端點，其中 `GET /sets/{set_id}/advice/stream` 為**串流式成本建議**；前端有 `CostPage`（路由 `/cost`，`can('C1','view')` 者登入即導向）；`schema_rbac.sql` 有 `archive_diagram_cost`、`archive_diagram_cost_line`、`archive_cost_audit_event` 三表。故第一版的問題不再是「要不要做一個會回『尚未提供』的空殼」，而是「大腦要怎麼編排一個已經存在、且自身也有串流的成本 agent」——這是不同的問題，不是同一問題的細節修正。受影響落點經逐一核對為 8 處：intent-capture 的 V2／[Q6]=C／[Q11]=B、`intent-statement.md` 的 Target Customer 成本列與 Initial Scope Signal、`stakeholder-map.md` 的成本關注者定位、feasibility 的 S 條目與能力表成本列、`constraint-register.md` 的 C-T9／C-S2、scope-definition 的 S3／S9 與 `scope-document.md`／`intent-backlog.md` 的分級與序 9。使用者已裁決**跳回 intent-capture 以 Modify 模式修訂**（非 feasibility——過期事實與 Q6／Q11 的決定都在 intent-capture）。未於本 session 執行的理由：AI-DLC 框架於本 session 期間由 2.7.0 升級至 2.9.0，指令介面與 stage 協定均已變更，而本 session 載入的是 2.7.0 協定；以舊協定驅動新引擎執行會動到生命週期狀態並重走三道關卡的操作，風險是污染稽核紀錄。應由新 session 以 2.9.0 協定執行。
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
