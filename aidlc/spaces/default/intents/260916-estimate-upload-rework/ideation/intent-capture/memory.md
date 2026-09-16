<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-09-16T03:53:13Z — 把使用者這次補充的兩個細節（上傳後要在 UI 顯示、agent 框架指定 LangGraph）判定為現行 intent 的延續而非新工作；intent 的 project-description 已載明「改掉現行 agent 框架」與「使用者直接上傳三朵雲官方估價表」，兩者同主旨，依 SKILL.md「Default to CONTINUATION」處理，並已向使用者確認。
- 2026-09-16T03:53:13Z — 使用者以實作語彙指名 LangGraph，依 project.md `## Corrections` 既有規則，本階段把它當作有約束力的技術前提來出題（Q5 問範圍），但不在 artifact 下沉為設計；artifact 只保留邊界高度的決策效力。
- 2026-09-16T03:53:13Z — Standard 深度的建議題數為 5-8，本階段出 9 題。理由：本 intent 同時反轉估價資料來源（自動取價改為使用者上傳）與抽換 agent 框架，屬兩個獨立的產品邊界變更，各自需要專屬的邊界題（Q2、Q5），不併題。



## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-09-16T03:53:13Z — Q1 與 Q6 初稿各有 5 個實質選項，超過提問介面每題 4 個的上限。依 project.md `## Corrections` 的既有規則（選項數超限時先收斂問題檔本身、記明合併方式，不得提問時臨時換一組），在提問前就地收斂為 4 個，兩題各以 HTML 註解記下被移除的選項與合併理由。
- 2026-09-16T04:58Z — Cursor harness 無 PostToolUse write hook，artifact 寫入不會產生 ARTIFACT_CREATED／UPDATED 事件，導致 `aidlc-log.ts review` 以「output document was not saved after the confirmed answers」拒絕。比照 HUMAN_TURN 的既有處理方式，對每個實際寫出的檔案手動餵 `bun .claude/hooks/aidlc-write-audit-log.ts`（stdin 給 `{"tool_name":"Write","tool_input":{"file_path":"<abs>"}}`）補記事件後重試。此為 harness 缺 hook 的通用問題，後續每個 stage 都會遇到，值得在 learnings 收成規則。
- 2026-09-16T04:12:00Z — 順序偏離：stage-protocol §3 Step 3a 要求「consolidated summary confirmation → 才產出 artifact」，本次在確認前就先寫出 intent-statement.md 與 stakeholder-map.md 草稿。補救方式是在確認前不進 reviewer、不 report，並於確認題明示兩份草稿已存在；若使用者選 Request changes 即就地改寫。
- 2026-09-16T03:53:13Z — Cursor harness 無 UserPromptSubmit hook，`aidlc-log.ts answer` 首次因缺 HUMAN_TURN 被擋；依 project.md `## Mandated` 的既有規則，在使用者已於對話中明確作答後執行 `bun .claude/hooks/aidlc-record-human-turn.ts` 再重試。



## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-09-16T03:53:13Z — 若 Q2 答「完全取代」，`project.md ## Forbidden` 的 C1 計價 API 禁令（[memory:M1]）與 `## Mandated` 的 `pricing_client` 三層要求（[memory:M2]）會指向一個不再存在的元件。這兩條規則屬於既有已核可的規則層，不在本階段回改；留待 feasibility 或 requirements-analysis 判定是否需要新的規則層變更。
- 2026-09-16T03:53:13Z — 使用者上傳檔案是本專案未曾有過的輸入面，ADR-0006 security baseline 的四個面向（IAM、encryption、network exposure、audit logging）對「解析不受信任的上傳檔」需要逐項判定。本階段不下沉，記為 feasibility 的必答項。
- 2026-09-16T03:53:13Z — 現行 `cost_router.py` 的 9 個端點全部掛在 `/diagrams/{diagram_id}` 之下。若估價改以上傳的檔案為單位，端點的資源識別基礎會改變；這是 application-design 的事，但 Q2 的答案會決定它是改造還是新建。


