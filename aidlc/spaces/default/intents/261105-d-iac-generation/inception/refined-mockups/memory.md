<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-11-05T17:05:00Z — Q1–Q6 全 A：aside 選圖、自由步驟、aside Agent 進度、下載 modal、固定三欄殼、沿用 Tailwind＋WCAG AA；與 stories 自由檢視／執行閘一致。
- 2026-11-05T17:05:00Z — Secrets 步不改主區全寬（否決線框 Screen 4 全寬傾向），以 Q5=A 固定殼為準，降低兩套 landmark。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-11-05T17:05:00Z — DownloadConfirmDialog 明確要求 focus trap／Esc，不沿用 ShareModal 無 aria 的既有債（design-system-mapping 註明）。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-11-05T17:05:00Z — HCL 預覽維持淺色 mono，不做深色主題，避免雙軌對比檢查（Q6=A）。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-11-05T17:05:00Z — IaC 工作區是 Workspace 內嵌面板或同頁路由子狀態，本檔以「Workspace 內」為準；精確 React 路由掛點留給 functional-design／code-generation。
