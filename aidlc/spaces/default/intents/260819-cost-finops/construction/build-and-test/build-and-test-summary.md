# Build and Test Summary — 260819-cost-finops（B1）

## 總覽

| 項目 | 結果 |
|---|---|
| Build（frontend） | ✅ lint 0 errors、check:types、vite build |
| Backend unittest | ✅ **223/223** |
| OpenAPI drift | ✅ |
| Repo + env + calculator boundary | ✅（env 已補 `COST_PRICING_STUB` 文件） |
| Playwright C1 | ✅ **5/5** |
| Playwright 全 suite | ⚠️ **17/19**（2 既有 admin 失敗，非 C1） |

## 三項測試底線（C1）

| 底線 | 觸發 | 落點 | 狀態 |
|---|---|---|---|
| **A** RBAC allow/deny | `/api/cost*` | `test_cost_api.py` | ✅ |
| **B** TestClient 端點 | cost router | 同上 5 cases | ✅ |
| **C** 前端 e2e | CostPage | `regression.spec.ts` 成本區塊 5 cases | ✅ |

## Unit 覆蓋盤點

| Unit | 自動化 |
|---|---|
| cost-schema-rbac | 間接（API + init_db） |
| cost-calculator | Hypothesis 6 + boundary gate |
| cost-api | TestClient 5 |
| cost-ui | Playwright 5 |
| cost-budget-banner | B2 deferred（404 + 0 DOM 已驗） |

## 本階段修正

1. **`get_snapshot()` commit** — e2e 發現 PUT hours 404
2. **`backend/.env.example`** — 補 `COST_PRICING_STUB`（env contract blocking）

## 已知缺口

| 缺口 | 承接 |
|---|---|
| GET audit 含 `mxcell_id` | 後續 PR |
| AWS offer 真解析 | MVP stub |
| 全 suite 2 admin 分頁 case | 既有技術債，非本 intent |
| 80% line coverage 量測 | org 宣告、repo 無 gate |

## 就緒度

| 維度 | 評估 |
|---|---|
| Build-ready | ✅ |
| Test-ready（B1） | ✅ |
| CI-ready | ✅（待 ci-pipeline stage 確認 workflow） |
| Deploy-ready（staging） | ✅ schema + DEPLOY.md 已同步 |

## 下一步

**ci-pipeline（3.7）** — 確認 `validate_cost_calculator_boundary.py` 已在 `ci.yml`、ui-regression 含成本 case。
