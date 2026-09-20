# Test Results — C1 估價上傳改版

> 執行時間：2026-09-19T20:20:00Z · 主機：本機 Cursor agent

## Build

| 命令 | 結果 |
|---|---|
| `cd frontend && npm run build` | **success**（exit 0；vite 756ms；chunk 警告非阻擋） |
| `python3 scripts/validate_repo_contract.py` | **success**（exit 0） |
| `python3 scripts/validate_env_contract.py` | **success**（exit 0） |
| `python3 scripts/validate_cost_calculator_boundary.py` | **success**（exit 0） |
| `python3 scripts/validate_pricing_lookup_boundary.py` | **success**（exit 0） |

## Unit / Integration（backend）

| 命令 | 結果 |
|---|---|
| `cd backend && PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v` | **success** — Ran **335** tests in ~20.3s，**OK**（0 fail / 0 error） |

環境：`backend/.venv`（Python 3.13 + `requirements.txt`）。系統 Python 3.9 缺依賴，不作為證據。

## E2E

| 命令 | 結果 |
|---|---|
| Playwright `estimate-workspace.spec.ts` | **未於本次重跑**（先前 U8/U9 CG 已綠；本階段以 unittest＋validators＋frontend build 為閘）。標為矩陣外選跑項。 |

## Coverage

unittest 未強制 coverage 報告；CI 與 unit-test-instructions 以 discover OK 為準。

## Target Verification Matrix

| Target ID | Source | Expected | Actual | Evidence | Owning Stage | Verdict |
|---|---|---|---|---|---|---|
| T-REPO-CONTRACT | `scripts/validate_repo_contract.py` | exit 0 | exit 0 | 本檔 Build 表 | build-and-test | Met |
| T-ENV-CONTRACT | `scripts/validate_env_contract.py` | exit 0 | exit 0 | 本檔 Build 表 | build-and-test | Met |
| T-COST-BOUNDARY | `scripts/validate_cost_calculator_boundary.py` | exit 0 | exit 0 | 本檔 Build 表 | build-and-test | Met |
| T-PRICING-BOUNDARY | `scripts/validate_pricing_lookup_boundary.py` | exit 0 | exit 0 | 本檔 Build 表 | build-and-test | Met |
| T-UNITTEST-ALL | `*/unit-test-instructions.md`＋CI | discover OK | 335 OK | `/tmp/bat-unittest.log`（本機跑） | build-and-test | Met |
| T-FE-BUILD | `estimate-workspace-ui`／`advice-presentation-ui` unit-test-instructions | `npm run build` exit 0 | exit 0 | 本檔 Build 表 | build-and-test | Met |
| T-NFR-PERF-SCOPE | NFR performance（多 unit） | — | — | `performance-validation` 於本 intent **SKIP**；無本機可執行且無後續 owning stage 的可測數值 | build-and-test | N/A |

## Loop-Back Log

（無）
