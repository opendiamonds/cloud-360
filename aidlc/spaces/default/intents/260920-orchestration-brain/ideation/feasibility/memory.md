<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
- 2026-09-21T02:42:25Z — F13 取代 F12：使用者「用系統admin功能去設定」的回覆被判讀為**重新框定**而非選項之一，依 `application-design:260822-ad-L3` 先查證（llm_limits.py 管的是單次 token 上限非花費、user_router 無任何設定類端點、強制花費上限需成本計量而 [Q6]=C／[Q11]=B 已排除成本計算），確認它同時是跨階段矛盾與範圍擴充，故改問真正的決策點而非直接採納。使用者選 A（改在 OpenRouter 後台設），矛盾解除、範圍不變、不需回跳上游。
- 2026-09-21T01:40:34Z — CONDITIONAL 適用性逐項判定（依 project.md `feasibility:c1`，不憑 feature 表面大小直覺）：**整合約束＝成立**（須接既有 agent 端點、既有 LLM provider 切換層、既有 auth／RBAC，並在既有 user_diagrams 之上疊專案／系統階層）；**法規要求＝部分成立**（episodic memory 是 by user 的對話紀錄，有保存期與刪除的隱私面，雖僅限自有 staging）；**顯著技術不確定性＝成立**（LangGraph 與 Redis 在 repo 內引用為 0，三種記憶與推播皆無前例）。三款有二款明確成立，故本 stage EXECUTE。
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
- 2026-09-21T02:42:25Z — 提問時把某題的選項順序重排（為了讓建議項排前面），寫回問題檔時卻依**位置**而非依**內容**對應，把 F11 使用者實選的 A 誤記為 C。此即 `requirements-analysis:260822-ra-c2` 警告的形狀，但該規則談的是「選項數超過上限時先收斂」，未涵蓋「順序重排後的回寫對應」。已在問題檔就地記錄更正與原因。
- 2026-09-21T01:40:34Z — 依 project.md `feasibility:c2`，省略 stage 檔範例題「What AWS services and accounts are currently in use?」。理由：本 repo 的部署目標只有自有 staging（ADR-0007），雲端供應商 production 環境與 credentials 由 ADR-0001／0002 排除在範圍外（project.md `## Scope Overrides`），沒有雲端帳號盤點的標的。
- 2026-09-21T01:40:34Z — 省略「組織阻礙（change freeze、競爭優先序）」一題。理由可引用：intent-capture 的 [Q8] 已定案為「單一決策者（你），無其他關係人：範圍、優先順序、驗收皆由你決定，不需要對外回報節奏」，組織層阻礙在此結構下不存在。依 project.md `scope-definition:260822-c5`，省略時必須能引用定案原文，此處可引用。
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
- 2026-09-21T02:42:25Z — F6 只選兩個 spike（LangGraph 編排、記憶層資料模型），未含既有資料遷移。依 `feasibility:260822-c1` 的覆蓋檢查主動加開 F10，使用者選 A（交給設計階段處理）。取捨是：遷移風險不在本站以試探消除，改以對 application-design／functional-design 的明確指派承載——故該指派必須寫進產出，否則會無聲落空。
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
- 2026-09-21T02:42:25Z — F11=B（無硬數字、原則盡量省）與 F13=A（上限由 OpenRouter 後台承載）銜接後，本專案不掌握該上限的實際數值。當外部上限觸發、OpenRouter 開始拒絕請求時，系統當下的行為未定。此項列入 RAID 風險，緩解方向於設計階段選定。
- 2026-09-21T01:40:34Z — team.md `## Code Style` 記載「Backend 依賴 100% 未 pin、無 lockfile……11 個依賴無一有版本約束」，但實測 `backend/requirements.txt` 現已有 `fastapi[standard]==0.141.1` 與 `pydantic==2.13.4` 兩項精確釘選（且附有與 openapi.json 漂移檢查相關的理由註解）。該規則層敘述已過期，待下一輪 practices-discovery 更正；本 stage 以實測值為準。
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
