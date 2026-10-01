# 自動化測試計畫 — C1 估價上傳改版

> Intent：`260916-estimate-upload-rework`  
> 分桶見 `manual-test-cases.md`。FR12 教學彈窗 e2e 與 FR13 mock enrich 已補；真實目錄查詢仍屬手動。

## 1. 已自動化落點（本 stage 不重寫）

| 層級 | 路徑 | 涵蓋 |
|---|---|---|
| Backend unittest | `backend/tests/test_estimate_*.py`、`test_cost_advice_agent.py`、`test_langgraph_runtime.py`、`test_pricing_*.py` | 上傳、解析、建議（mock）、定價埠 |
| Boundary scripts | `scripts/validate_*_boundary.py`、`validate_repo_contract.py`、`validate_env_contract.py` | 純函式邊界、契約 |
| Playwright | `frontend/tests/e2e/estimate-workspace.spec.ts` | `/cost` 工作區＋建議面板＋FR12 教學彈窗 |
| Backend unittest | `backend/tests/test_sku_catalog.py` | FR13 形狀判斷與 mock enrich |

規格註解（`@purpose` 等）以各測試檔為準，**不**在 TCMS 手寫自動化描述。

## 2. 本 stage 新寫腳本

- `frontend/tests/e2e/estimate-workspace.spec.ts`：官方估價教學彈窗
- `backend/tests/test_sku_catalog.py`：目錄 SKU enrich（mock）

## 3. Open items

真實 LLM／本機 `.env`／缺定價憑證／真實目錄 SKU 解讀歸手動桶（M-1–M-4）。

## 4. 突變驗證

本 stage 未新增腳本，不另做突變。既有 suite 於 build-and-test 以 `AIDLC` 本機 venv 跑過 **335 OK**（見 `construction/build-and-test/test-results.md`）。
