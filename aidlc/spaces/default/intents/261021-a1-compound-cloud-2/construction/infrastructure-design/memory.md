<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
2026-11-10T03:51:00Z — 基礎設施設計全數沿用既有容器與 GitHub Actions 測試管線：U1/U2 透過 pytest 進行單元斷言，U3 於共享 FastAPI 容器執行並配置 SSE 監控指標，U4 透過既有 Vite 打包輸出至 Nginx 靜態目錄，維持零架構變更與最高相容性。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
2026-11-10T03:51:00Z — 選擇將 U3 作為 FastAPI 共享模組而非獨立微服務，以省去額外 Kubernetes 部署維護成本，代價是與其他後端服務共用 CPU/RAM 資源配額。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
