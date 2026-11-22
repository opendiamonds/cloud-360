# Technology Stack — Cloud-360

> **基準**：`dc4b687`（2026-09-22）。證據標記慣例見 `business-overview.md` 檔頭。
> 版本值取自 `backend/requirements.txt` 與 `frontend/package.json` 的**宣告** `[讀]`，
> **非安裝後的解析結果**——backend 無 lockfile，實際安裝版本可能與宣告不同。

## 語言與執行環境

| 項目 | 版本 | 證據 |
|---|---|---|
| Python | 3.12（`python:3.12-slim`） | `[讀]` `backend/Dockerfile:6` |
| TypeScript | `~6.0.2`（宣告） | `[讀]` `frontend/package.json` |
| Node | 22（**在 backend image 內**，供 `claude` CLI） | `[讀]` `backend/Dockerfile:3–18` |
| PostgreSQL | 16-alpine（deploy／test stack）／15-alpine（repo 根 `docker-compose.yml` 本機 db） | `[讀]` |
| nginx | `nginx:alpine` | `[讀]` `frontend/Dockerfile` |
| cloudflared | `cloudflare/cloudflared:latest`（**未釘選**） | `[讀]` `deploy/docker-compose.deploy.yml` |

## Backend 套件（`backend/requirements.txt`，17 項宣告）`[讀]`

| 套件 | 版本宣告 | 用途 |
|---|---|---|
| `fastapi[standard]` | `==0.141.1`（精確） | HTTP／WS／SSE 框架 |
| `pydantic` | `==2.13.4`（精確） | 請求／回應模型 |
| `langgraph` | `==1.2.11`（精確） | C1 建議 agent 的圖執行 |
| `langchain-openai` | `==1.6.2`（精確） | `ChatOpenAI` → OpenRouter |
| `openpyxl` | `==3.1.5`（精確） | Azure XLSX 估價表解析 |
| `PyYAML` | `>=6.0`（下限） | `cost/*.yaml` 設定載入 |
| `uvicorn`、`httpx`、`python-dotenv`、`sqlalchemy`、`psycopg2-binary`、`passlib[bcrypt]`、`bcrypt`、`pyjwt`、`claude-agent-sdk`、`hypothesis`、`boto3` | **未 pin** | — |

**釘選現況更正** `[讀]`：實測為 **5 支精確釘選 ＋ 1 支下限 ＋ 11 支未 pin**，
且**仍無 lockfile**（`team.md` 記載的「僅 2 支精確釘選、其餘 10 支未 pin」已過時）。
`requirements.txt:1–7` 的註解自述用 `==` 而非 `~=` 的理由：讓 OpenAPI dump 位元決定性。

> **`langgraph==1.2.11` 已在部署環境運行**——本 intent 的 LangGraph 相容性不是待驗假設，
> 是既有事實；而 `cost_advice_agent.py` 正是「LangGraph 圖 ＋ SSE 對外」的可運行前例。

## Frontend 套件（`frontend/package.json`）`[讀]`

| 套件 | 版本 | 用途 |
|---|---|---|
| `react` / `react-dom` | `^19.2.6` | UI |
| `react-router-dom` | `^7.18.2` | 路由 |
| `html2canvas` / `jspdf` | `^1.4.1` / `^4.2.1` | 評核 PDF／PNG 匯出 |
| `vite` | `^8.0.12` | 建置 |
| `typescript` | `~6.0.2` | 型別檢查 |
| `eslint` ＋ `typescript-eslint` ＋ `eslint-plugin-react-hooks` ＋ `eslint-plugin-react-refresh` | `^10.3.0` / `^8.59.2` / `^7.1.1` / `^0.5.2` | lint（flat config） |
| `tailwindcss` ＋ `@tailwindcss/postcss` | `^4.3.0` | 樣式 |
| `@playwright/test` | `^1.56.0` | **唯一**的前端測試框架 |

**無 vitest／jest／`@testing-library/*`** `[算]`（`devDependencies` 逐項核對）——
前端仍無 unit／component 測試層。有已 commit 的 `package-lock.json`，CI 用 `npm ci`。

> **Tailwind 設定的既知陷阱**：`frontend/tailwind.config.js` 在 Tailwind v4 下
> 未被任何 `@config` 載入、是死碼；實際生效的是 `src/index.css` 的 `@theme`。
> 本輪未複驗此點，沿用既有記載 `[未驗]`。

## 建置系統

三條**獨立**管線，無 monorepo 建置工具（無 Nx／Turborepo／Makefile）`[算]`：

1. **Backend**：`pip install -r backend/requirements.txt`。**無 lockfile、無 `pyproject.toml`、
   無 `setup.cfg`** `[算]`（`find . -maxdepth 3 -name pyproject.toml …` 回傳空）。
2. **Frontend**：`npm ci` ＋ `npm run build` = `tsc -b && vite build` `[讀]`。
3. **Docker**：兩支獨立 Dockerfile，由 compose 以 `context: ../backend` / `../frontend` 建置 `[讀]`。

## 工具鏈現況（誠實記載）

| 面向 | Frontend | Backend |
|---|---|---|
| Linter | ESLint 10 flat config，CI 跑 `eslint .`（**未加 `--max-warnings 0`**，故只擋 error）`[讀]` | **無** `[算]` |
| Formatter | **無**（repo 根無 `.prettierrc`）`[算]` | **無**（無 Black）`[算]` |
| Type checker | `tsc -b`（隨 `npm run build`）`[讀]` | **無**（無 mypy／pyright）`[算]` |
| 依賴鎖定 | `package-lock.json` 已 commit `[讀]` | **無 lockfile** `[算]` |
| 覆蓋率量測 | 無 | **無**（無 `.coveragerc`、無 `coverage`／`pytest-cov`、CI 無 coverage step）`[算]` |

**本輪未執行 lint**，故不重述任何 error／warning 計數 `[未驗]`。

## 基礎設施與 CI/CD

| 項目 | 值 | 證據 |
|---|---|---|
| Staging 主機 | 自架 `192.168.10.10`，經 Cloudflare Tunnel 對外為 `cloud360.danniel.cc` | ADR-0007 |
| Staging 服務數 | **4**（`db`／`backend`／`frontend`／`cloudflared`） | `[讀]` `deploy/docker-compose.deploy.yml:11–93` |
| CI | GitHub Actions `ci.yml`，5 job／11 檢查步驟 | `[讀]` |
| CD | `deploy.yml`，self-hosted runner `[self-hosted, linux, x64, cloud360]`、30 分逾時、`concurrency: deploy-10-10` 且 `cancel-in-progress: false` | `[未驗，僅讀骨架]` |
| Agentic workflows | 11 支 gh-aw，**全部 `engine: copilot`** | `[算]` |
| 測案管理 | 自架 Kiwi TCMS（`tcms.danniel.cc`，於 `dc-infra` repo 維運） | 規則層 |

## 本 intent 會引入的新技術面

| 新增 | 現況 | 落地條件 |
|---|---|---|
| **Redis 容器（第 5 個服務）** | 全樹 **零基礎設施用途** `[算]`（13 個 `redis` 命中全部是 WA 規則文字、lens JSON、drawio 模板、prompt 內的服務清單） | 新環境變數必須在**同一個 PR** 內由 `deploy/render-env.sh`（`:73–98`）寫入、`deploy/.env.example` 列出，否則 `validate_env_contract.py` 紅燈；憑證值不得含 `$`（`render-env.sh:59–69` 會擋） |
| **第二套 LangGraph runtime** | `langgraph==1.2.11` 已運行；既有 `langgraph_runtime.astream_graph` 存在但零消費者 `[算]` | 自建的理由不可寫成「既有的不能串流」（不成立）；第三個 OpenRouter 入口的環境變數耦合須明寫 |
| **獨立 PostgreSQL schema** | **零前例**：全樹無 `CREATE SCHEMA`、無 `search_path`、無 `__table_args__ schema` `[算]` | 測試走 in-memory SQLite（無 schema 概念），跨 schema 行為在現有測試基礎設施上**不可驗證** |
| **新 WebSocket** | 既有 1 個（`/api/collab/ws/...`），網路路徑已通 | 必須掛在 `/api/` 之下（nginx 限制）；**零契約閘門** |
