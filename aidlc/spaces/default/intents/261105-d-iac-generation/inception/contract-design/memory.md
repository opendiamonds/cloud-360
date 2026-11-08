<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-11-06T04:37:00Z — Q1–Q5=A：能力動詞 `/api/iac`、422＋error.code、zip 二進位、無 URL 版號、執行 POST 不自動重試；單一跨 unit 契約 C1（U1→U2）。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-11-06T04:37:00Z — 圖 API／RBAC 不重寫為新建契約，僅附註依賴；避免與 ADR-005／既有 JWT 面重複規格。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-11-06T04:37:00Z — 同步 HTTP 明確超時秒數、zip 目錄慣例、掃描 CLI 品牌、實驗性標記字串、PBT 擴張 ADR——沿自上游 OQ，契約路徑已釘、數值未釘。
