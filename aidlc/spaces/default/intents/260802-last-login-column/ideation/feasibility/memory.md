<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-02T23:28:53Z — 判定本 CONDITIONAL stage 適用而非 skip；本功能存在整合約束（RBAC seed 兩處同步、部署資產同步 blocking）與技術不確定性（系統無任何既有登入紀錄），不符「trivial change with no technical risk」的跳過條件。
- 2026-08-02T23:28:53Z — 省略 stage 檔範例中的「AWS services and accounts」題；本功能僅觸及自有 staging，與雲端供應商環境無關（ADR-0007 / scope overrides），問了只會製造噪音。
- 2026-08-02T23:28:53Z — Q8=A 確認語意由「最後登入」改為「最後活動」後，上游 intent-statement 的「最後登入」表述不回改；以本 stage 問題檔的確認為準向下游傳遞，避免回頭改已核可的上游 artifact。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-02T23:28:53Z — 出題前以唯讀探查 agent 查證 code／schema／部署文件事實（登入流程無任何落紀錄、無 migration 框架、重跑 SQL 會重置權限 seed 等），查證結果登錄於問題檔 Sources 供選項設計；artifact 維持能力層表述。此為既有 learned rule（ideation 禁實作細節約束 artifact 內容、不約束查證行為）的直接應用。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-02T23:28:53Z — 問題數取 7 原題＋2 追問（Standard 範圍上緣）；Q6a／Q8 為 Q1=C 引發的一致性追問，寧多問一輪也不讓「登入 vs 活動」語意歧義流入 requirements-analysis。
- 2026-08-02T23:28:53Z — R1（每請求寫入的負載風險）只記風險與緩解方向（節流／彙整／非同步），不在 ideation 預選手段；代價是設計階段必須回頭處理，換取本階段不下沉到設計。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-02T23:28:53Z — 保存上限的值（Q4=B 只確認「有上限」）與單一欄位覆寫模式下「清除」的實際語意（帳號停用後何時清除），留 requirements-analysis。
- 2026-08-02T23:28:53Z — 「超過 N 天未活動」的 N 承襲 intent 未決項，requirements-analysis 需定案。
