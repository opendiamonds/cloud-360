# 技術棧（Technology Stack）

> Reverse Engineering 合成產物｜repo `cloud`｜工作樹掃描日 2026-09-16｜intent `260916-estimate-upload-rework`｜mode **Full rescan**
> 版本以 `backend/requirements.txt`（逐行讀過）與 `frontend/package.json`（逐行讀過）為準。外部依賴的**消費關係**記在 `dependencies.md`，本檔只記版本與用途。

## 語言與執行環境

| 項目 | 版本 | 位置 |
|---|---|---|
| Python | 3.12 | `backend/`、`scripts/` |
| TypeScript | `~6.0.2` | `frontend/` |
| Node.js | 22 | 前端建置；**另存在於 backend 映像內**，為 `claude-agent-sdk` 所需的 `@anthropic-ai/claude-code` CLI |
| PostgreSQL | 16-alpine | `deploy/docker-compose.deploy.yml` 的 `db` 服務 |

## Backend 依賴（`backend/requirements.txt`，14 項）

| 名稱 | 版本 | 用途 |
|---|---|---|
| `fastapi[standard]` | `==0.141.1`（**精確釘選**） | Web 框架；釘選是為了 `openapi.json` 的位元決定性 |
| `pydantic` | `==2.13.4`（**精確釘選**） | 資料驗證與 OpenAPI schema；同上理由 |
| `PyYAML` | `>=6.0` | `cost/config.py` 載入 9 份 YAML |
| `uvicorn` | 未釘 | ASGI server |
| `httpx` | 未釘 | 查價與外部 HTTP（AWS Bulk／Azure Retail／GCP Catalog／OpenRouter） |
| `sqlalchemy` | 未釘 | ORM |
| `psycopg2-binary` | 未釘 | PostgreSQL driver（測試中以 `MagicMock` 取代） |
| `passlib[bcrypt]`、`bcrypt`、`pyjwt` | 未釘 | 認證與密碼雜湊 |
| `python-dotenv` | 未釘 | `env_bootstrap.py` |
| `claude-agent-sdk` | 未釘 | Agent 執行框架 |
| `hypothesis` | 未釘 | property-based testing（ADR-0006 hard constraint） |
| `boto3` | 未釘 | **全 repo 唯一使用者為 `cost/pricing_sdk.py`** |
| `playwright` | 未釘 | Azure／GCP Calculator 自動化 |

**14 項中只有 2 項精確釘選，無 lockfile。** CI、Docker build 與 staging 部署三處各自解析當下最新版，可能彼此不同。

### 兩項與本 intent 直接相關的版本事實

1. **`claude-agent-sdk` 不能因 C1 遷移而移除**：repo 內另有 3 個非 cost 消費者——`services/design_agent.py`、`services/review_agent.py`、`services/wa_lens_engine.py`。連帶地，`backend/Dockerfile` 內的 Node 22 與 `@anthropic-ai/claude-code` CLI 也不能拿掉。
2. **`boto3` 可隨 `pricing_sdk.py` 一併移除**：它是 repo 內唯一的 boto3 使用者。但移除前必須改寫 `pricing_client.py:20` 與 `:280-283` 的 `use_sdk_enabled()` 分支，且 `tests/test_pricing_client.py:73-74` 正好 patch 這兩個符號。

## Frontend 依賴（`frontend/package.json`）

**Runtime**：React `^19.2.6`、react-dom `^19.2.6`、react-router-dom `^7.18.2`、html2canvas `^1.4.1`、jspdf `^4.2.1`。

**Dev**：Vite `^8.0.12`、TypeScript `~6.0.2`、ESLint `^10.3.0`、typescript-eslint `^8.59.2`、Tailwind `^4.3.0`、`@playwright/test` `^1.56.0`、`@types/node` `^24.12.3`。

- 有已 commit 的 `package-lock.json`，CI 用 `npm ci`（與後端形成對照）。
- **無任何前端 unit／component 測試框架**（無 vitest、無 jest、無 `@testing-library/*`）；唯一自動化驗證層是 Playwright e2e。
- Tailwind 為 v4：`frontend/tailwind.config.js` 未被任何 `@config` 載入，實際生效的是 `src/index.css` 的 `@theme`。

## 建置與工具鏈

| 類型 | 工具 | 設定檔 |
|---|---|---|
| Python 套件 | pip | `backend/requirements.txt` |
| 前端套件 | npm（`npm ci`） | `frontend/package.json`、`package-lock.json` |
| 前端建置 | Vite + `tsc -b` | `vite.config.ts`、`tsconfig{,.app,.node}.json` |
| 樣式 | Tailwind 4 + PostCSS | `tailwind.config.js`（死碼）、`postcss.config.js`、`src/index.css` |
| Lint | ESLint 10 flat config | `frontend/eslint.config.js` |
| E2E | Playwright（chromium 單一 project） | `frontend/playwright.config.ts` |
| 容器 | Docker + docker compose | `backend/Dockerfile`、`frontend/Dockerfile`、根 `docker-compose.yml`、`deploy/docker-compose.deploy.yml`、`deploy/docker-compose.test.yml` |
| 部署設定產生 | Shell | `deploy/render-env.sh` |
| CI／CD | GitHub Actions（33 支 workflow） | `.github/workflows/` |

**後端工具鏈的缺口**：無 linter、無 formatter、無 type checker（無 Ruff／flake8／black／mypy／pyright 設定），也無覆蓋率設定（無 `.coveragerc`／`pytest.ini`／`pyproject.toml`）。Python 端唯一的機械把關是 import smoke test 與三支自製契約腳本。

## 執行期外部服務

PostgreSQL 16-alpine、cloudflared、embed.diagrams.net、OpenRouter 或本機 `claude` CLI、n8n webhook、AWS／Azure／GCP 公開價目端點、Azure／GCP Calculator 網頁、Kiwi TCMS。各自的憑證需求見 `api-documentation.md` 的「對外呼叫的第三方 API」表。

**部署映像的 Playwright 缺口**：`requirements.txt` 裝了 `playwright` 套件，但 `backend/Dockerfile` **沒有** `playwright install chromium`，容器內無瀏覽器二進位。詳見 `code-quality-assessment.md`。
