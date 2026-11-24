# 整合測試指引

**本 intent 不另產生整合測試。** 測試策略為 Minimal（`aidlc-state.md` 的 `Test Strategy`），依 stage 規則不額外產生整合測試指引；單元測試由 code-generation 的 `unit-test-instructions.md` 涵蓋。

## 為何單元層已足夠

- 路由端對端行為（歷程進入 Decisions 請求的 `state`）已由 `test_intent_routing_decisions.DecisionsEndToEndTest` 以 `FakeHttp` transport 攔截真實請求形狀驗證，跨 `intent_routing_port` → `intent_routing_decisions` 兩個模組。
- 編排行為（A1 只回提問 → 工作項「完成」、等待者不在舊圖執行、重啟復原）已由 `test_work_orchestrator_flow` 以 `Harness` 走完整編排流程驗證，跨 `work_orchestrator`、`work_orchestrator_capabilities`、`work_orchestrator_rules`。

## 唯一需要真實外部服務的驗證

真實 OpenRouter `typesafe/jev-1.14` 的路由結果（NFR1）無法在本機或 CI 執行：需要部署到 staging 後重新量測，見 `build-and-test-summary.md` 與 `cross-unit-traceability.md` 的未結項。
