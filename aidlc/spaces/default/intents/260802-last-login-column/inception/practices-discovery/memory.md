<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-08T17:00:00Z — 本次為 stage 檔的 Re-run 分支：team.md 的 `## Way of Working` 已有 ADR-0010 的 branch 命名與中文 commit type 規則（非空），依 Step 2 須以其為 current affirmed baseline；lead brief 明訂「延伸不重寫」，因為 practices-promote 是整段替換而非合併，lead 漏寫即等於刪除既有規則。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-09T01:35:00Z — 三位 support 提出的 18 項 OBJECT 未走 §5 的 round 2，而是分流處理：事實性修正（fetch 52/10、ESLint 16 條、掃描器作用域等）由 lead 整合時直接吸收，判斷型爭點才升為人工訪談 6 題。round 2 的用途是專家可裁決的知識爭議，而這批 OBJECT 多為 support 回 repo 實測後補上 lead 沒查到的事實，沒有可爭議之處。
- 2026-08-11T00:00:00Z — 本輪（scope-definition Revision 2 回跳後的重跑）**未重新執行 hub-and-spoke 訪談**，四份 artifact 內容維持不變，改以確定性驗證取代：本站產出全部由程式碼與流程資產的實況推導，而 `HEAD` 仍為原掃描基準 commit `8c90f40`、應用程式碼與 CI／部署資產的 diff 與 status 皆為空集合。PU-6 是**範圍**變更而非**實踐**變更 —— 分頁改的是既有端點的回應契約，不動測試框架、lint 工具鏈、CI 閘門、分支與 commit 慣例，故既有的 team-practices／discovered-rules／evidence 對本輪仍然成立。三份 support contribution 為前次訪談的原件，未偽造新輪次。判定與驗證指令記於 `practices-discovery-timestamp.md`。
- 2026-08-11T00:00:00Z — 本輪重跑 `practices-promote` 後對兩個工具副作用做了修正，兩者皆已逐字驗證，處置與理由如下：
  - **`team.md` 五個 section 內的 code fence 內容被整段吃掉**（`Way of Working` 的 commit 格式範本、三則 commit 範例、branch↔commit 對照、changelog parser regex 共四個 fenced block，被替換成等量空行）。以腳本逐節比對確認 **promote 前的 `team.md` 五節與 `team-practices.md` 草稿逐位元相同**（2930／403／4160／2053／4570 bytes 全等），亦即草稿本身含 fence、是 promote 的寫入端丟失內容。處置：還原 promote 前的 `team.md`（＝草稿內容），不改工具行為。若不還原，`project.md ## Corrections` 記載的「漏寫即等於刪除既有規則且會讓 contract 的 REQUIRED_TEXT 紅燈」會直接成真。
  - **`project.md` 的兩條規則被重複追加**：`practices-promote` 的去重是「規則原文 + `(affirmed <today>)`」的逐字比對，日期戳不同即不視為重複，故已存在的 `(affirmed 2026-08-09)` 兩條被以 `(affirmed 2026-08-10)` 再追加一次。處置：移除新追加的兩條、保留原 `2026-08-09` 戳 —— 該日的確認是真人在訪談 gate 作出的，今日只是同一份草稿在零變更前提下的重跑，保留原始確認日期較如實。`project.md` 現已與 promote 前逐位元相同。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-09T01:35:00Z — support agent 的 brief 明訂「認真找碴，不是背書」並要求自行回 repo 查證而非轉引 codekb：三位因此各自推翻了 lead 與 codekb 的部分前提（fetch 處數、角色副本數、ESLint 規則數、掃描器實際作用域），若只給 codekb 當證據會讓上游誤差原樣傳進 team.md。
- 2026-08-09T01:35:00Z — 未進入正式訪談的 support 追加題（devsecops Q9–Q13、developer Q-dev-1~3）不升格為規則，只以事實形式記入 evidence.md：practices 層只收錄人工已定案的內容，未經確認的建議寫進規則層等於用 agent 判斷取代人類決定。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-09T01:45:00Z — `aidlc-state.ts practices-promote` 有 bug：寫入 team.md 時剝除所有 fenced code block 的內容（來源 team-practices.md 8 個 fence → promote 後 0 個），使 commit message 格式模板、三個範例與 changelog regex 全數遺失。contract 未擋下（只比對關鍵字，而關鍵字剛好在表格內倖存）。本次以備份逐字還原四個區塊並驗證一致。upstream 工具問題，升級時應回報或加保護；下次跑本 stage 必須在 promote 後比對 fence 數。
- 2026-08-09T01:35:00Z — `UserSchema` 三個具名構造點中有兩個（`update_user_active` L602、`update_user_role` L705）現正靜默漏傳 `requested_role`；本 intent 新欄位若比照辦理會產生使用者可見 bug 且無工具會報錯。已記入 evidence.md 向下游傳遞，處置留 construction。
- 2026-08-09T01:35:00Z — 權限稽核軌跡 `_audit_append()` 為 `logger.info`，部署重建容器即失去舊日誌；對一個以稽核能力為價值主張的 intent 是實質張力，但修復不在本 intent 範圍，留待獨立立項。
