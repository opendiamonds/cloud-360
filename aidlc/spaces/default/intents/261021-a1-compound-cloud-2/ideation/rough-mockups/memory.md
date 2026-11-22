<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-10-21T09:25:00Z — 混合雲架構視覺呈現採 Hub-and-Spoke 空間佈局，以核心雲居中（預設 AWS）且加寬容納跨雲服務，Azure 與 GCP 分居左右兩側形成對稱翼展。
- 2026-10-21T09:25:00Z — 前端採雙重入口設計：頂部 Toolbar 提供 Compound 按鈕手動觸發，亦支援在 Chat 對話中輸入多雲指令時由後端智能推斷自動切換選單。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-10-21T09:25:00Z — 跨雲連線採直角折線 (Orthogonal Routing) 並於中點標註協議名稱（如 ExpressRoute、VPN），相比貝茲曲線能大幅減少多雲多節點間的交叉凌亂。
- 2026-10-21T09:25:00Z — 畫布初次載入採 Fit-to-Window 自動縮放並對齊中央，在兼顧三雲巨型架構全貌的同時，透過平移與滾輪縮放保證細節可讀性。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
