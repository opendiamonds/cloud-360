# 建置說明（261116-brain-create-diagram）

> 撰寫時間 2026-11-22T14:21:37Z（`date -u`）。分支 `danniel/feat/brain-create-diagram`，未 commit。

## 1. 相依套件安裝

| 層 | 指令 | 說明 |
|---|---|---|
| Backend | `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` | 本機以 `backend/.venv/bin/python` 執行；測試走 in-memory SQLite，`tests/helpers.py` 會先替 `psycopg2` 放替身，**不需要** psycopg2 或 PostgreSQL |
| Frontend | `cd frontend && npm ci` | 依 `package-lock.json` |

## 2. 環境設定

- 單元測試不需要 `.env`、不連任何資料庫或 Redis（`team.md` 既成事實）。
- 本 intent **新增一個啟動補丁** `backend/database.py::_ensure_diagram_status_schema()`：backend 啟動時對既有資料庫補上 `user_diagrams.status`（`NOT NULL DEFAULT 'ready'`＋`ck_user_diagrams_status`）。與其他六支 `create_all()` 之後的 `_ensure_*` 不同，**它失敗會讓啟動失敗**；`DEPLOY.md` 與 `LOCAL-DEV.md` 已同步說明。
- 空 volume 路徑：`schema_rbac.sql` 的同名區塊（`ADD COLUMN IF NOT EXISTS` ＋ `pg_constraint` 判斷）。

## 3. 建置指令

| 項目 | 指令 |
|---|---|
| Frontend lint | `cd frontend && npm run lint` |
| Frontend 建置（含 `tsc -b`） | `cd frontend && npm run build` |
| API 型別與規格一致 | `cd frontend && npm run check:types` |
| OpenAPI 漂移 | `backend/.venv/bin/python backend/scripts/dump_openapi.py --check` |
| WS 契約漂移 | `backend/.venv/bin/python backend/scripts/dump_ws_contract.py --check` |
| Repo contract | `python3 scripts/validate_repo_contract.py` |
| 環境設定 contract | `python3 scripts/validate_env_contract.py` |

## 4. 建置驗證

- lint：`0 errors`；警告數維持既存的 2 個（`exhaustive-deps`），不得增加。
- build：成功（chunk 大小警告為既存）。
- 四支 `--check`／validator 皆印出「一致」或「passed」。

## 5. 常見問題

| 症狀 | 原因與處置 |
|---|---|
| 舊 volume 升級後 backend 起不來，日誌含 `diagram status schema 補丁失敗` | 補欄位的 DDL 被拒（權限或鎖）。刻意讓啟動失敗——缺欄時讀圖必 500。依 `DEPLOY.md` 的回復段處理，不要改成吞掉例外 |
| `npm run check:types` 報不一致 | 後端回應形狀改了但沒重跑 `npm run gen:types` |
| 本機 Docker daemon 未啟動 | 只影響 `docker-compose.test.yml` 的 CI stack；單元測試與本站的 PostgreSQL 驗證不需要 Docker（後者用 Homebrew PostgreSQL 17 起一次性叢集，見 `integration-test-instructions.md` §3） |
