<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
2026-11-08T14:03:00Z — NFR 需求全數落實 ADR-0004 零新增外部依賴，後端以標準庫 xml.etree 與既有 httpx 滿足安全與逾時防護，前端以 Tailwind CSS 與既有 Draw.io postMessage 達成 GPU 加速。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
2026-11-08T14:03:00Z — 幾何計算單元設置單圖 500 節點上限以消除記憶體 DoS 風險，以常態架構規模保護伺服器不被惡意超大輸入耗盡資源。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
