<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
2026-11-10T03:06:00Z — NFR Design 階段各單元架構解耦完成：U1 確立 XSS-Safe 正則白名單過濾，U2 確立 XML 原生字元轉義與 500-node 邊界限制，U3 確立 RBAC 裝飾器防護，U4 確立 postMessage 來源白名單與 GPU 硬體加速縮放。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
2026-11-10T03:06:00Z — 前端選擇 250ms CSS GPU 硬體加速 transform 而非 JS 輪詢計算，以固定時間上限犧牲動態彈性換取嚴格 60 FPS 零掉幀體驗。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
