# 效能測試指引

**不適用，未產生效能測試。** 測試策略為 Minimal，且本 intent 沒有 nfr-requirements／nfr-design 產出，也沒有效能類的量化目標。

唯一與量相關的需求是 NFR5（每次路由多送出的使用者內容不超過 6 × 400 字）。它是輸入上界而非延遲或吞吐目標，已由 `test_intent_routing_decisions.BuildStatePropertyTest` 以性質測試驗證（每則 ≤ 400 字、最多 6 則）。
