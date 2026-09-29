<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
- 2026-09-21T10:14:41Z — 修訂 1：上游前提變動後重審可行性，結果是**信心上調而非下調**。逐項對照可行性面向（新服務／新依賴／新基礎設施／新技術層）後，Q12／Q13／Q14 三項新決定一項都沒引入新的——成本能力已存在且以 HTTP 呼叫、LangGraph 已是釘選依賴、狀態事件轉譯不需新機制。依 approval-handoff:rev1-c2，不因範圍變動就自動下修信心。
- 2026-09-21T10:14:41Z — 查證揭露成本 agent 的「串流」是 job 狀態輪詢（每秒查 DB 送 progress／completed／timeout／failed／heartbeat）而非 token 級串流。這比上游假設的簡單，但也多出一個上游沒看到的風險：timeout 與 failed 兩種終態若在大腦側沒有對應訊息會靜默（已記為 R-9）。
- 2026-09-21T02:42:25Z — F13 取代 F12：使用者「用系統admin功能去設定」的回覆被判讀為**重新框定**而非選項之一，依 `application-design:260822-ad-L3` 先查證（llm_limits.py 管的是單次 token 上限非花費、user_router 無任何設定類端點、強制花費上限需成本計量而 [Q6]=C／[Q11]=B 已排除成本計算），確認它同時是跨階段矛盾與範圍擴充，故改問真正的決策點而非直接採納。使用者選 A（改在 OpenRouter 後台設），矛盾解除、範圍不變、不需回跳上游。
- 2026-09-21T01:40:34Z — CONDITIONAL 適用性逐項判定（依 project.md `feasibility:c1`，不憑 feature 表面大小直覺）：**整合約束＝成立**（須接既有 agent 端點、既有 LLM provider 切換層、既有 auth／RBAC，並在既有 user_diagrams 之上疊專案／系統階層）；**法規要求＝部分成立**（episodic memory 是 by user 的對話紀錄，有保存期與刪除的隱私面，雖僅限自有 staging）；**顯著技術不確定性＝成立**（LangGraph 與 Redis 在 repo 內引用為 0，三種記憶與推播皆無前例）。三款有二款明確成立，故本 stage EXECUTE。
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
- 2026-09-21T10:23:32Z — 稽核收據的正確順序本輪才摸清，記下來給後續 stage：(1) 先把所有產出寫到定稿；(2) `aidlc-log decision --checkpoint summary-confirmation` 登記提示；(3) 提問；(4) `aidlc-log answer` 記錄選擇（產生 Summary Authorization Id）；(5) **之後**才用 Write/Edit 工具重存每一份產出，讓 hook 蓋上該 id。本輪踩到兩個坑：產出在收據之前就寫好 → SUMMARY_ARTIFACT_UNAUTHORIZED；收據之後又去改問題檔（只加了一段 HTML 註解）→ SUMMARY_CONTENT_STALE，因為收據綁定的是問題檔在確認當下的內容。問題檔若也需要帶戳記的寫入，做法是以 Edit 還原成確認當下的內容——工具呼叫觸發 hook，而內容雜湊不變。
- 2026-09-21T10:14:41Z — 收窄了 F6 的 LangGraph 試探範圍。原問題「LangGraph 能否乾淨包住既有 SSE agent 端點」已被 repo 內的可運行前例回答（cost_advice_agent.py 正是該形狀且已在部署環境運行），再做等於重複驗證已證明的事。收窄後聚焦本 intent 獨有的部分：多意圖分支結構、session 注入、兩份 runtime 的一致性。F6 的作答本身不改。
- 2026-09-21T10:14:41Z — A-3（LangGraph 與 Python 3.12 相容）由假設升為既成事實，C-T7 的「新引入的套件（LangGraph 等）」一併更正——LangGraph 已非新引入，該條對本 intent 的剩餘適用對象是 Redis 客戶端。
- 2026-09-21T02:42:25Z — 提問時把某題的選項順序重排（為了讓建議項排前面），寫回問題檔時卻依**位置**而非依**內容**對應，把 F11 使用者實選的 A 誤記為 C。此即 `requirements-analysis:260822-ra-c2` 警告的形狀，但該規則談的是「選項數超過上限時先收斂」，未涵蓋「順序重排後的回寫對應」。已在問題檔就地記錄更正與原因。
- 2026-09-21T01:40:34Z — 依 project.md `feasibility:c2`，省略 stage 檔範例題「What AWS services and accounts are currently in use?」。理由：本 repo 的部署目標只有自有 staging（ADR-0007），雲端供應商 production 環境與 credentials 由 ADR-0001／0002 排除在範圍外（project.md `## Scope Overrides`），沒有雲端帳號盤點的標的。
- 2026-09-21T01:40:34Z — 省略「組織阻礙（change freeze、競爭優先序）」一題。理由可引用：intent-capture 的 [Q8] 已定案為「單一決策者（你），無其他關係人：範圍、優先順序、驗收皆由你決定，不需要對外回報節奏」，組織層阻礙在此結構下不存在。依 project.md `scope-definition:260822-c5`，省略時必須能引用定案原文，此處可引用。
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
- 2026-09-21T10:14:41Z — F14 定案 A（HTTP 帶使用者 token）而非 B（同進程呼叫 service 層）。取捨是多一跳本機 HTTP，換到既有 require_story_action dependency 照常執行——授權在機制上不可能被繞過，稽核主體自然是使用者本人。這一題同時關掉 intent-statement 的假設⑧與⑨，兩者都不需要新機制。
- 2026-09-21T02:42:25Z — F6 只選兩個 spike（LangGraph 編排、記憶層資料模型），未含既有資料遷移。依 `feasibility:260822-c1` 的覆蓋檢查主動加開 F10，使用者選 A（交給設計階段處理）。取捨是：遷移風險不在本站以試探消除，改以對 application-design／functional-design 的明確指派承載——故該指派必須寫進產出，否則會無聲落空。
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
- 2026-09-21T10:14:41Z — R-8（兩份 runtime 並存後各自漂移）的緩解手段刻意不在本站預選，依 feasibility:c6 只記風險與方向。但這一項與其他 RAID 項不同：它是使用者知情選擇（Q13=B）的直接後果，不是外部不確定性——若設計階段未接下 D-6 的指派，它會無聲落空而沒有任何人會發現。
- 2026-09-21T08:59:32Z — **上游前提已失效，待以 Modify 模式回跳修訂**。本 intent 的 intent-capture 查證 V2 記載「成本／FinOps 能力完全不存在，`FinOps_Analyst` 只是 RBAC 角色名」，該事實在當時為真，但 `ut` 已於 2026-09-20T14:43Z 合併 PR #647（cost-estimation-finops），成本能力現已存在且規模不小：`backend/cost/` 套件含 `estimate_intake_router` 與 `advice_stream_router`；`/api/cost/v1/` 下 6 條端點，其中 `GET /sets/{set_id}/advice/stream` 為**串流式成本建議**；前端有 `CostPage`（路由 `/cost`，`can('C1','view')` 者登入即導向）；`schema_rbac.sql` 有 `archive_diagram_cost`、`archive_diagram_cost_line`、`archive_cost_audit_event` 三表。故第一版的問題不再是「要不要做一個會回『尚未提供』的空殼」，而是「大腦要怎麼編排一個已經存在、且自身也有串流的成本 agent」——這是不同的問題，不是同一問題的細節修正。受影響落點經逐一核對為 8 處：intent-capture 的 V2／[Q6]=C／[Q11]=B、`intent-statement.md` 的 Target Customer 成本列與 Initial Scope Signal、`stakeholder-map.md` 的成本關注者定位、feasibility 的 S 條目與能力表成本列、`constraint-register.md` 的 C-T9／C-S2、scope-definition 的 S3／S9 與 `scope-document.md`／`intent-backlog.md` 的分級與序 9。使用者已裁決**跳回 intent-capture 以 Modify 模式修訂**（非 feasibility——過期事實與 Q6／Q11 的決定都在 intent-capture）。未於本 session 執行的理由：AI-DLC 框架於本 session 期間由 2.7.0 升級至 2.9.0，指令介面與 stage 協定均已變更，而本 session 載入的是 2.7.0 協定；以舊協定驅動新引擎執行會動到生命週期狀態並重走三道關卡的操作，風險是污染稽核紀錄。應由新 session 以 2.9.0 協定執行。
- 2026-09-21T02:42:25Z — F11=B（無硬數字、原則盡量省）與 F13=A（上限由 OpenRouter 後台承載）銜接後，本專案不掌握該上限的實際數值。當外部上限觸發、OpenRouter 開始拒絕請求時，系統當下的行為未定。此項列入 RAID 風險，緩解方向於設計階段選定。
- 2026-09-21T01:40:34Z — team.md `## Code Style` 記載「Backend 依賴 100% 未 pin、無 lockfile……11 個依賴無一有版本約束」，但實測 `backend/requirements.txt` 現已有 `fastapi[standard]==0.141.1` 與 `pydantic==2.13.4` 兩項精確釘選（且附有與 openapi.json 漂移檢查相關的理由註解）。該規則層敘述已過期，待下一輪 practices-discovery 更正；本 stage 以實測值為準。
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
