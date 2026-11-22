<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-10-21T05:10:00Z — 混合雲向 n8n 發送之上行 payload 統一設定 provider = "compound"，有別於單一雲直接給定 AWS、GCP 或 Azure，由 n8n 服務端統一進行多雲圖示查詢。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-10-21T05:10:00Z — 畫布三雲空間幾何佈局選定「中央核心＋雙翼 (Hub-and-Spoke)」，以核心業務雲居中、另外兩雲分列兩翼，兼顧空間排版與跨雲連線可讀性。
- 2026-10-21T05:10:00Z — 前端觸發機制採選單主動選取「混合雲 (Compound)」與對話模型自動識別之雙軌支援，兼顧手動指定與自然對話引導。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
