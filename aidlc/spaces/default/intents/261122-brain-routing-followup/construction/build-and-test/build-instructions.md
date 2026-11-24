# Build 指引

本 intent 只改後端 Python（`backend/services/intent_routing_*`、`backend/services/work_orchestrator*` 與對應測試），不動前端、OpenAPI、WebSocket 契約、資料庫 schema 與環境變數。build 指的是 CI `backend` job 的建置檢查，指令逐字取自 `.github/workflows/ci.yml`。

## 相依套件

```bash
cd backend && pip install -r requirements.txt
```

本 intent 不新增套件；Hypothesis 已在 `backend/requirements.txt`。

## 環境設定

- 不需資料庫、Redis 或網路；測試以 `tests/helpers.py` 的 stub 與 `tests/work_orchestrator_fakes.py` 的替身執行。
- import smoke 與 OpenAPI 漂移檢查需要兩個環境變數（值與 CI 相同，非真實憑證）：
  - `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/cloud360`
  - `JWT_SECRET=ci_only_not_a_real_secret`

## Build 指令（自 `backend/` 執行）

| 檢查 | 指令 | 預期輸出 |
|---|---|---|
| import smoke | `DATABASE_URL=… JWT_SECRET=… python3 -c "import main; print('app:', main.app.title)"` | `app: Cloud-360 API` |
| OpenAPI 漂移 | `DATABASE_URL=… JWT_SECRET=… python3 scripts/dump_openapi.py --check` | `規格檔與後端程式碼一致。` |
| WS 契約漂移 | `python3 scripts/dump_ws_contract.py --check` | `WS 契約規格檔與後端程式碼一致。` |

## Build 驗證

repo 根目錄：

```bash
python3 scripts/validate_repo_contract.py
python3 scripts/validate_env_contract.py
```

兩支都須印出 `... validation passed.`。

## 常見問題

- import smoke 報 `psycopg` 相關錯誤：確認 `DATABASE_URL` 帶 `+psycopg` driver（CI 註解有說明 SQLAlchemy 2.1 預設 driver 的變化）。
- OpenAPI 漂移紅燈：本 intent 不應改動任何端點；若紅燈，先以 `git diff backend/` 確認是否誤改 router。
