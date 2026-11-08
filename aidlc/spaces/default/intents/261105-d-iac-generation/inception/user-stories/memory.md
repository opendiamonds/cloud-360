<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-11-05T16:55:00Z — US6.2 端到端改為多角色協作演示，不改 RBAC 種子；Alex 主路徑限於選圖／D1／下載（Q5=A 字面保留）。現行種子無三角 edit，單一 Architect 無法執行 D2／D3；故事層以多帳號 AC6.2.1–6.2.3 對齊事實，避免假演示。
- 2026-11-05T16:55:00Z — 執行 D3 前置以 US4.1 契約註記補強／覆寫 FR6.2（D1∧D2 成功報告）；requirements.md 表字面未同步，advisory 標為 Major 雙來源，交人工閘門權衡是否回修 FR 或留 contract-design 以故事為準。
- 2026-11-05T16:55:00Z — 無權入口採 disabled＋說明（非 hide），以便 Fiona 痛點「看不到為何不能用」可測；view／edit 分列寫進 AC。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-11-05T16:55:00Z — Round 1 OBJECT 中「Alex 一人走完」與種子衝突屬判斷題，未再開 Q；lead 逕選多角色演示並於整合摘要揭露。理由：Q5=A 已確認 Alex 主路徑語意為產品主敘，非 RBAC 三角 edit 承諾。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-11-05T16:55:00Z — US2.1 不拆第二則 Must，改 UI AC＋generator DoD 分層；保留標準粒度同時避免 UI／PBT 假完成混驗。
- 2026-11-05T16:55:00Z — 上傳失敗（R-03）自 Should 升 Must（US1.4），換取本輪可測關閉，略增故事數。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-11-05T16:55:00Z — requirements FR6.2 是否在本閘前同步改字，或契約層以 US4.1 為權威（advisory R-01）。
- 2026-11-05T16:55:00Z — zip 打包格式、掃描 CLI 品牌、實驗性標籤文案、PBT 擴張是否另開 ADR——沿自 requirements OQ，本 stage 未關。
