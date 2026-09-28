# Cross-Unit Traceability — C1 估價上傳改版

| Unit | Stories／需求 | Code summary | Unit tests | Integration／E2E |
|---|---|---|---|---|
| estimate-parser | 估價表解析 | `estimate-parser/code-generation/code-summary.md` | `tests.test_estimate_parser`／`validator` | discover suite |
| estimate-intake-api | 上傳／列表／RBAC | `estimate-intake-api/.../code-summary.md` | `tests.test_estimate_intake_api` | TestClient boundaries |
| credential-pipeline | 密文／contract | `credential-pipeline/.../code-summary.md` | `tests.test_repo_contract_secret_patterns` | validate_repo_contract |
| legacy-cost-retirement | 舊 cost 退役 | `legacy-cost-retirement/.../code-summary.md` | discover＋boundary scripts | validate_cost_calculator_boundary |
| pricing-lookup-port | 三雲定價埠 | `pricing-lookup-port/.../code-summary.md` | `tests.test_pricing_*` | validate_pricing_lookup_boundary |
| langgraph-runtime | agent runtime | `langgraph-runtime/.../code-summary.md` | `tests.test_langgraph_runtime` | mock；無金鑰不打真 API |
| cost-advice-agent | 成本建議 | `cost-advice-agent/.../code-summary.md` | `tests.test_cost_advice_agent` | 與 intake 共用 suite |
| estimate-workspace-ui | CostPage SPA | `estimate-workspace-ui/.../code-summary.md` | Playwright estimate-workspace | 需 :8090 stack |
| advice-presentation-ui | SSE 建議面板 | `advice-presentation-ui/.../code-summary.md` | 同上 e2e | JWT fetch SSE |

需求追溯主檔：`inception/requirements-analysis/requirements.md`。
