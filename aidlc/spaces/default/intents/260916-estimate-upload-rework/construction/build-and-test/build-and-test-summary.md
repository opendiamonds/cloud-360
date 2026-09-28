# Build and Test Summary — C1 估價上傳改版

> Intent: `260916-estimate-upload-rework` · Test Strategy: **Standard**

## 整體狀態

| 項目 | 狀態 |
|---|---|
| Build | **ready**（frontend `npm run build` 綠；四支 validators 綠） |
| Unit／整合測試 | **ready**（backend 335 tests OK） |
| Deployment-ready | **條件式** — 程式與契約綠；正式雲端仍 out of scope（ADR-0001／0007） |

## 測試類型盤點

| 類型 | 產物 | 本次執行 |
|---|---|---|
| Build | `build-instructions.md` | 是 |
| Unit（per-unit 指令彙整） | 各 unit `unit-test-instructions.md` | 是（discover 一次） |
| Integration／邊界 | `integration-test-instructions.md` | 是（validators＋suite） |
| Performance | `performance-test-instructions.md` | 僅建置觀察；深度測 N/A（stage SKIP） |
| Security | `security-test-instructions.md` | 是（contract＋suite 內 RBAC／secret） |

## 覆蓋期望（per unit）

見 `cross-unit-traceability.md`。最低門檻：對應 unittest module 或 boundary script 綠。

## Target Verification Matrix

| Target ID | Source | Expected | Actual | Evidence | Owning Stage | Verdict |
|---|---|---|---|---|---|---|
| T-REPO-CONTRACT | `scripts/validate_repo_contract.py` | exit 0 | exit 0 | `test-results.md` | build-and-test | Met |
| T-ENV-CONTRACT | `scripts/validate_env_contract.py` | exit 0 | exit 0 | `test-results.md` | build-and-test | Met |
| T-COST-BOUNDARY | `scripts/validate_cost_calculator_boundary.py` | exit 0 | exit 0 | `test-results.md` | build-and-test | Met |
| T-PRICING-BOUNDARY | `scripts/validate_pricing_lookup_boundary.py` | exit 0 | exit 0 | `test-results.md` | build-and-test | Met |
| T-UNITTEST-ALL | per-unit unit-test-instructions／CI | discover OK | 335 OK | `test-results.md` | build-and-test | Met |
| T-FE-BUILD | U8／U9 unit-test-instructions | build exit 0 | exit 0 | `test-results.md` | build-and-test | Met |
| T-NFR-PERF-SCOPE | NFR performance 文件 | — | — | performance-validation **SKIP**；無可在本階段執行的量化門檻 | build-and-test | N/A |

## 就緒評估

- **build-ready**：是
- **test-ready**：是（本機 venv＋frontend）
- **deployment-ready**：staging 部署流程仍走既有 deploy workflow；本 stage 不執行部署

## 已知限制

- Playwright E2E 本次未重跑（依賴 docker test stack）；先前 CG 階段已驗證。
- `performance-validation` 已 SKIP；延遲類 NFR 不在本閘強制。
- Hypothesis 常數目錄為本機快取，不納入 source-manifest。
