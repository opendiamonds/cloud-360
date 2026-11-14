# 建置說明（build-and-test）

- 撰寫時間（`date -u`）：`2026-11-14T02:19:24Z`
- 依據：本 intent 24 個單元的 `code-generation/unit-test-instructions.md`、`.github/workflows/ci.yml`、`team.md` ## Testing Posture／## Deployment
- 基準：分支 `danniel/docs/orchestration-brain-ideation`，HEAD `ff537a7` ＋ **未 commit 的工作樹**（含 F1／F2／F4／語意記憶與本機 Claude Code provider 的改動，見 `test-results.md` 的「本站內的程式修正（未經 loop-back）」）

## 前置條件

| 項目 | 需求 | 本站實測版本 | 說明 |
|---|---|---|---|
| Python | 3.12（CI `actions/setup-python`） | 本機 `backend/.venv` 為 3.13.7 | 本機**一律**用 `backend/.venv/bin/python -B`：系統 Python 的套件版本與 `requirements.txt` 不一致（多個單元的 unit-test-instructions 已記載）；本機亦無 `python` 指令，只有 `python3` |
| Node.js | `package-lock.json` ＋ `npm ci` | v25.2.1 | 前端無 unit 測試框架，只有 Playwright e2e（`team.md`） |
| Playwright 瀏覽器 | chromium | `~/Library/Caches/ms-playwright/chromium-1228` | `npx playwright install chromium` |
| PostgreSQL | **`pgvector/pgvector:pg18`**（`schema_rbac.sql` 第一條敘述是 `CREATE EXTENSION vector`，標準 `postgres:*-alpine` 跑不過） | 臨時容器 | 只供 `tests_pg/` 與 `backend/scripts/verify_*.sql` |
| Redis | **`redis:8-alpine`**（兩份 compose 的釘選） | 臨時容器 | 只供 opt-in 的 `tests_redis/`；**不得用 Redis 7.x 驗**：見 `test-results.md` 的 Lua 空陣列觀察 |
| psql 客戶端 | **≥ 15** | 本機 Homebrew 為 14.20 | `deploy/initdb/02-memory-role-password.sh` 用 `\getenv`（psql 15 起）；本機請改在 pg18 容器內執行 |

## 相依安裝

```bash
# 後端
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 前端
cd ../frontend
npm ci
npx playwright install chromium
```

## 環境設定

三個範圍互不混用（`project.md` ## Mandated、`scripts/validate_env_contract.py`）：

| 範圍 | 設定來源 | 本站用途 |
|---|---|---|
| 本機 dev | `backend/.env`、`frontend/.env`（範本 `*.env.example`） | 本站**不使用**；測試只以下列環境變數執行 |
| CI 測試 | `deploy/docker-compose.test.yml`（值全內嵌） | `ui-regression` 的真實 stack；本站**不起** |
| 部署 | `deploy/.env`（`deploy/render-env.sh` 產生） | 本站不碰 |

測試用環境變數（皆為假值，不是憑證）：

```bash
export PYTHONDONTWRITEBYTECODE=1                 # 避免在 repo 內產生 .pyc（改動引擎的來源指紋）
export HYPOTHESIS_STORAGE_DIRECTORY=<scratchpad>/hyp   # 避免在 repo 內寫 .hypothesis
export JWT_SECRET=ci_only_not_a_real_secret
# 只有 tests_pg／import smoke／dump_openapi 需要：
export DATABASE_URL=postgresql+psycopg://postgres:<密碼>@127.0.0.1:<埠>/cloud360   # 密碼 [REDACTED]
# 只有 tests_redis 需要：
export REDIS_URL=redis://127.0.0.1:<埠>/15
```

`DATABASE_URL` 必須顯式帶 `+psycopg`（`ci.yml` 註解：裸 `postgresql://` 依賴 SQLAlchemy 隱含預設，2.1 起由 psycopg2 改為 psycopg）。

### 本機副本（建議做法，本站即如此執行）

在 repo 內直接跑測試會寫入 `.hypothesis/` 與 `__pycache__/`，而引擎的 workspace 來源指紋會把它們算進去（`project.md` 的 `source-fingerprint-includes-caches`）。故一律在副本執行：

```bash
rsync -a --delete --exclude .git --exclude node_modules --exclude .venv \
  --exclude '__pycache__' --exclude .hypothesis --exclude .env <repo>/ <scratchpad>/bt-copy/
cp -Rc <repo>/frontend/node_modules <scratchpad>/bt-copy/frontend/
```

副本沒有 `.git`，故 `scripts/validate_repo_contract.py`（以 `git ls-files` 掃描）必須在 repo 內執行；兩支 validator 都是唯讀檢查。

## 建置指令

| # | 指令（工作目錄） | 作用 |
|---|---|---|
| B1 | `python -B -c "import main; print('app:', main.app.title)"`（`backend/`，帶 `DATABASE_URL`、`JWT_SECRET`） | import smoke：語法、import、router 接線 |
| B2 | `python -B scripts/dump_openapi.py --check`（`backend/`，同上 env） | OpenAPI 漂移閘門 1/2 |
| B3 | `python -B scripts/dump_ws_contract.py --check`（`backend/`，不需 env） | WS 契約漂移閘門 1/2 |
| B4 | `python -B scripts/gen_mcp_tools.py --check`（`backend/`，不需 env） | MCP 工具宣告漂移閘門 |
| B5 | `npm run lint`（`frontend/`） | ESLint；CI 只擋 error |
| B6 | `npm run check:types`（`frontend/`） | OpenAPI 型別檔漂移閘門 2/2 |
| B7 | `npm run check:ws-types`（`frontend/`） | WS 型別檔漂移閘門 2/2 |
| B8 | `npm run build`（`frontend/`）＝ `tsc -b && vite build` | 型別檢查＋打包 |
| B9 | `python3 -B scripts/validate_repo_contract.py`（repo 根） | repo contract |
| B10 | `python3 -B scripts/validate_env_contract.py`（repo 根） | 三環境設定 contract |
| B11 | `docker buildx build`（CI `docker-build` job） | 兩個 image；**本站未執行**（見 test-results） |

## 建置驗證

全部 exit 0 才算建置成功。B5 允許既存的 warning（現況 `0 errors, 2 warnings`，皆 `exhaustive-deps`：`AssessmentPage.tsx:395`、`WorkspacePage.tsx:344`）；B8 的「chunk 大於 500 kB」提示為既存訊息、非失敗。

## 常見建置問題

| 症狀 | 原因 | 處置 |
|---|---|---|
| `command not found: python` | 本機只有 `python3` | 用 `backend/.venv/bin/python -B` |
| 系統 Python 下 import／版本錯誤 | 系統套件版本與 `requirements.txt` 不一致 | 用 `.venv` |
| `verify_purge_sql.sql: … purge_expired_memory.sql: No such file or directory` | 該檔以 `\i` 相對路徑引入，`psql` 工作目錄須為 repo 根；以 stdin 餵入時相對路徑失效 | 以 `psql -f backend/scripts/verify_purge_sql.sql` 在 repo 根（或容器內同結構目錄）執行 |
| `invalid command \getenv` | psql < 15 | 改在 pg18 容器內執行 `02-memory-role-password.sh` |
| `tests_redis` 10 項 FAIL、`tags: {}` vs `[]` | 用了 Redis 7.x | 改用 `redis:8-alpine` |
| `tests_pg` 一開始就失敗並說缺 `DATABASE_URL` | 刻意設計：`tests_pg/__init__.py` 缺值時大聲失敗，不退回 SQLite | 設定 `DATABASE_URL` 指向套過 `schema_rbac.sql` 的 pg18 |
| repo 內 `.pyc`／`.hypothesis` 數變多 | 在 repo 內直接跑測試 | 改在副本跑；收尾以 `find` 計數比對 |
