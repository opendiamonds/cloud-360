# Code Summary — credential-pipeline（U4／B3）

> Unit: `credential-pipeline` · kind: **packaging**  
> 計畫：同目錄 `code-generation-plan.md`（6 步，全數完成）  
> Plan Approval：`Approve Plan`（session 已記錄）

## 變更檔案

| 檔案 | 變更 | 對應 |
|---|---|---|
| `scripts/validate_repo_contract.py` | 移除 `AWS_SECRET_ACCESS_KEY` 裸字串禁令；新增 `SECRET_VALUE_REGEXES`；`validate_no_obvious_secrets` 對追蹤檔掃值樣式 | FR11.2、NFR9.1、ADR-0018 §6 |
| `backend/tests/test_repo_contract_secret_patterns.py` | **新增** 7 案例（含突變） | Step 3 |
| `.github/workflows/deploy.yml` | deploy／rollback 注入 `AWS_ACCESS_KEY_ID`／`AWS_SECRET_ACCESS_KEY` | FR11.1、FR5.8 |
| `deploy/render-env.sh` | 寫出兩變數（可空）；`$` 檢查納入 secret；改 ADR-0018 註解 | FR11.1 |
| `deploy/docker-compose.deploy.yml` | backend 傳入兩變數；註解指向 ADR-0018 | FR11.1、FR5.9 |
| `DEPLOY.md` | Secrets 清單、最小權限、缺憑證可啟動、禁洩值 | FR11.3、FR11.4、NFR9.3 |
| `LOCAL-DEV.md` | 本機可不設憑證；禁真值進版控／log | FR11.4、NFR9.3 |
| `inception/decisions/0018-catalog-price-api-credentials.md` | §6 定案 regex；OQ7 → Closed | Step 1 |
| `construction/.../security-requirements.md` | NFR9.1 寫入具體 regex；R-01 → Addressed | R-01 |

**未變更（刻意）**：`docker-compose.test.yml`（不注入真密鑰）、`backend/.env.example`／`deploy/.env.example`（已有空值註解）、`pricing_client`／`pricing_sdk`（U5）。

## 關鍵實作決定

1. **值樣式掃全部 `git ls-files` 文字檔**；PEM／`AZURE_`／`GOOGLE_` 字串禁令仍限 `REQUIRED_FILES`（避免 ADR／NFR 文件討論 `BEGIN PRIVATE KEY` 誤紅）。
2. **假密鑰只活在 tempfile fixture**，不進本 repo。
3. **突變案例**內嵌於測試：暫時把裸字串禁令加回 `FORBIDDEN_CONTENT_PATTERNS`，確認名稱引用會變紅。

## 測試

| 指令 | 結果 |
|---|---|
| `python3 scripts/validate_repo_contract.py` | exit 0 |
| `python3 scripts/validate_env_contract.py` | exit 0 |
| `cd backend && python3 -m unittest tests.test_repo_contract_secret_patterns -v` | 7 OK |
| `cd backend && python3 -m unittest tests.test_repo_contract_production_paths -v` | 11 OK |
| `cd backend && python3 -m unittest discover -s tests -v` | 346 ran；**2 FAIL** 於 `test_pricing_azure`（stub 回 `0.12` vs 期望 `0.1`／`PriceMiss`）— **既有、與本 unit 無關**（未改 pricing 模組） |

## 與計畫的偏離

無實質偏離。NFR Q5「先寫 ADR」改為確認既有 ADR-0018＋關閉 OQ7（計畫已載明）。

## 不做（交 U5）

查價客戶端、降級、執行期 log 遮罩、Vault、帳單類 API。
