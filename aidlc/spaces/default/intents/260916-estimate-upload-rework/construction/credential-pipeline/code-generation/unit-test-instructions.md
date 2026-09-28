# Unit Test Instructions — credential-pipeline

> Unit: `credential-pipeline` · Standard · test-after  
> 本 unit **無** HTTP／UI／DB；測試對象為 `scripts/validate_repo_contract.py` 的密鑰值樣式閘門。

## Framework

- Python 內建 `unittest`（與 CI `python -m unittest discover -s tests -v` 一致）
- **不**引入 pytest
- 載入方式：`importlib.util.spec_from_file_location` 載入 repo 根的 `scripts/validate_repo_contract.py`，並 patch 模組 `ROOT` 至暫存 git 目錄（沿用 `test_repo_contract_production_paths.py` 形狀，若該檔存在；否則照同 idiom 新建）

## Exact unit-scoped command（須在第一個實作測試前可跑）

```bash
cd backend && python -m unittest tests.test_repo_contract_secret_patterns -v
```

（檔案路徑：`backend/tests/test_repo_contract_secret_patterns.py`）

## Cases（目標 5–8）

| # | 情境 | 期望 |
|---|---|---|
| 1 | 版控檔僅含註解／空值 `AWS_SECRET_ACCESS_KEY=` | exit 0 |
| 2 | 版控檔含識別字 `AWS_SECRET_ACCESS_KEY` 無賦值密鑰 | exit 0 |
| 3 | `AWS_SECRET_ACCESS_KEY=` + 40 字元 `[A-Za-z0-9/+=]` | 非 0 |
| 4 | `GCP_BILLING_API_KEY=AIza` + 35 合法字元 | 非 0 |
| 5 | 含 `BEGIN PRIVATE KEY` | 非 0 |
| 6 | 乾淨無相關字串 | exit 0 |
| 7（可選） | 突變：還原裸字串禁變數名後，案例 2 應失敗 | 見計畫 Step 3 |

## Coverage / mocking

- 無 coverage.py 閘門；本 unit 以二元通過／失敗為準
- Mock：僅 patch 受測模組的 `ROOT`；不 mock 正則本身
- 假密鑰字串僅存在於暫存目錄，**不得** commit 到本 repo

## Out of scope

- U5 執行期 log 遮罩測試
- Playwright／TestClient
- `validate_env_contract.py` 的單元測試（以手動跑腳本綠燈為準，屬 Step 6）
