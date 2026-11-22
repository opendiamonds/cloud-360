<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-11-08T04:48:00Z — 混合雲功能之需求規格分為五大功能範疇 (FR1~FR5) 與五大非功能屬性 (NFR1~NFR5)，所有需求皆獲取穩定之唯一 ID 作為下游 User Stories 與 Architecture Design 之追溯鍵。
- 2026-11-08T04:48:00Z — 確定三雲群組在畫布上各自獨立為頂層 Group Box，幾何座標完全隔離不重疊，中央核心雲（預設 AWS）加寬至 480px，兩翼分居左右形成 Hub-and-Spoke 拓撲。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-11-08T04:48:00Z — 跨雲連線堅持採直角折線 (Orthogonal Routing) 並於中點動態標註協議文字，雖然計算複雜度略高於直接直線連線，但能大幅減少多雲多節點間的交叉凌亂。
- 2026-11-08T04:48:00Z — 對 n8n 圖示服務實施優雅降級 (Fallback)，非 200 或逾時 (5s) 時回傳灰底文字向量 SVG，保證主架構圖產出流程不中斷。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
