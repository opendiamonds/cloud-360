# Technology Stack — Cloud-360

> 逆向工程產出。基準 commit `c3de2c8`（branch `danniel/fix/production-path-check-noop`，2026-08-17）。
> 版本欄位為掃描時**宣告檔內的字面值**，非實際解析後的鎖定版本（除非該行本身是精確釘選）。

## 語言與執行環境

| 語言 | 版本 | 範圍 | 規模 |
|---|---|---|---|
| Python | 3.12（Dockerfile 與 CI 一致） | `backend/`、`scripts/` | 8,775 LOC 產品碼 + 3,199 LOC 測試 + 1,595 LOC 驗證／同步腳本 |
| TypeScript | `~6.0.2` | `frontend/` | 10,539 LOC TS/TSX（含 2,385 行**產生**的 `api.d.ts`） |
| CSS | — | `frontend/` | 234 LOC（`App.css` 184 + `index.css` 50） |
| SQL | PostgreSQL 方言 | `schema.sql`(78 行)、`schema_rbac.sql`(531 行) | — |
| Node.js | 22 | frontend build、**backend runtime（供 Claude Code CLI）**、CI | — |
| Markdown / Mermaid / draw.io XML | — | specs、prompts、圖形資產 | — |

## Backend 技術堆疊

宣告於 `backend/requirements.txt`，共 **12 條**。

| 套件 | 版本 | 角色 | 備註 |
|---|---|---|---|
| `fastapi[standard]` | **`==0.141.1`（精確釘選）** | Web framework | `[standard]` extra 帶入 uvicorn、httptools、websockets 等 |
| `pydantic` | **`==2.13.4`（精確釘選）** | 請求／回應 schema 驗證 | **程式碼仍有 v1 風格殘留**：`user_router.py:126,207` 的 `class Config: orm_mode = True` |
| `uvicorn` | 未 pin | ASGI server | 啟動指令 `uvicorn main:app --host 0.0.0.0 --port 8000` |
| `httpx` | 未 pin | 非同步 HTTP client | n8n webhook；**亦為 `TestClient` 的前置依賴** |
| `python-dotenv` | 未 pin | `.env` 載入 | `load_dotenv(override=True)` |
| `sqlalchemy` | 未 pin | ORM | declarative + `Table` 關聯表 |
| `psycopg2-binary` | 未 pin | PostgreSQL driver | 測試中被 `MagicMock` 取代，改走 in-memory SQLite |
| `passlib[bcrypt]` | 未 pin | （宣告但未使用） | 程式碼**未見任何 `passlib` import**，是可移除的殘留 |
| `bcrypt` | 未 pin | 密碼雜湊 | `auth.py` 與 `database.py` **各自實作一份**逐字相同的 hash 函式 |
| `pyjwt` | 未 pin | JWT 簽發與驗證 | HS256，8 小時效期 |
| `claude-agent-sdk` | 未 pin | Anthropic Agent SDK | **會 spawn Claude Code CLI 子行程**，見 `dependencies.md` 的隱性硬依賴 |
| `hypothesis` | 未 pin | Property-based testing | ADR-0006 hard constraint 的實際落點 |

### 為何只有 `fastapi` 與 `pydantic` 被釘選（`requirements.txt` 檔頭逐字說明）

這**不是隨機的部分釘選**，理由寫在檔頭且值得下游知道：

> OpenAPI 規格的輸出在同一組版本下是位元決定性的，但**跨版本會飄**
>（實測：同一份原始碼換這兩支的版本即產生 20 行差異）。本 repo 的依賴全部未 pin、
> CI 每次重新解析最新版，不釘會讓規格漂移檢查在完全無關的 PR 上變紅，
> 且該紅燈與「真的漂移了」在訊號上不可區分。

兩個推論：

1. **釘選動機是規格漂移 gate 的穩定性，不是供應鏈可重現性** —— 後者仍未解（另 10 支未 pin、無 lockfile）。
2. **刻意選 `==` 而非 `~=`**：相容釋出形式仍會在次版本線上浮動，形式選錯等於沒釘。
3. **升版這兩支時，必須在同一個 PR 內重新 dump `openapi.json` 並重產前端型別檔**，
   否則兩道 gate 會紅燈。

**測試工具**：Python 內建 `unittest`（`python -m unittest discover -s tests -v`）、
`unittest.mock`、`hypothesis`，以及 `starlette.testclient.TestClient`（**本輪新增使用**）。
**未使用 pytest。**

**Backend 完全沒有**：linter、formatter、type checker、coverage 工具、`pyproject.toml`、
`setup.py`、lockfile。

## Frontend 技術堆疊

### Runtime 依賴（5）

| 套件 | 版本 | 角色 |
|---|---|---|
| `react` | `^19.2.6` | UI framework |
| `react-dom` | `^19.2.6` | DOM renderer |
| `react-router-dom` | `^6.22.0` | 路由 |
| `html2canvas` | `^1.4.1` | 瀏覽器端截圖（PNG／PDF 匯出） |
| `jspdf` | `^4.2.1` | WA review PDF 匯出 |

### 建置與開發依賴（18）

| 套件 | 版本 | 角色 | 備註 |
|---|---|---|---|
| `vite` | `^8.0.12` | bundler / dev server | `vite.config.ts` 僅掛 react plugin，無 proxy／alias／build 調校 |
| `@vitejs/plugin-react` | `^6.0.1` | React 支援 | |
| `typescript` | `~6.0.2` | 型別系統 | `tsconfig` project references 三分檔 |
| `eslint` | `^10.3.0` | linter | flat config |
| `@eslint/js` | `^10.0.1` | ESLint 基礎規則 | |
| `typescript-eslint` | `^8.59.2` | TS 規則 | |
| `eslint-plugin-react-hooks` | `^7.1.1` | React hooks 規則 | **16 條 error 級規則**，已實質約束程式碼結構（見下） |
| `eslint-plugin-react-refresh` | `^0.5.2` | HMR 規則 | **迫使 `AuthContext` 拆兩檔** |
| `tailwindcss` | `^4.3.0` | CSS framework | **Tailwind v4** |
| `@tailwindcss/postcss` | `^4.3.0` | PostCSS 整合 | v4 的新整合方式 |
| `postcss` | `^8.5.15` | CSS 處理 | |
| `autoprefixer` | `^10.5.0` | 前綴補齊 | |
| `@playwright/test` | `^1.56.0` | e2e 測試 | chromium 單一 project |
| `@types/node` | `^24.12.3` | Node 型別 | |
| `@types/react` | `^19.2.14` | React 型別 | |
| `@types/react-dom` | `^19.2.3` | ReactDOM 型別 | |
| `@types/react-router-dom` | `^5.3.3` | 路由型別 | **版本錯配**：v5 型別搭 v6 runtime（v6 起自帶型別，此套件應移除） |
| `globals` | `^17.6.0` | ESLint globals | |

### 非宣告依賴（執行期以 `npx --yes` 抓取）

| 工具 | 版本 | 用途 | 風險 |
|---|---|---|---|
| `openapi-typescript` | `7.13.0` | 由 `openapi.json` 產生 `src/types/api.d.ts` | **版本字串手寫兩份**：`package.json` 的 `gen:types` 與 `frontend/scripts/check-api-types.mjs:21` 的 `GENERATOR` 常數。腳本註解自承「兩處若不一致，這道 gate 會比對到不同產生器的輸出而誤報」，**無機制鎖住一致** |

### ESLint 規則對程式碼結構的約束

**這不是風格偏好，是 error 級規則的直接後果，違反即 CI 紅燈。**

flat config 組成：`js.recommended` + `tseslint.recommended` + `react-hooks.flat.recommended`
+ `react-refresh.vite`；ignore `dist`。

`eslint-plugin-react-hooks@7.1.1` 的 16 條 error 級規則中，三條已實質決定既有程式碼形狀：

| 規則 | 造成的結構 | 現例 |
|---|---|---|
| `react-refresh/only-export-components` | **Context 拆兩檔**：Provider 放 `.tsx`，型別與 hook 放同名 `.ts` | `AuthContext.tsx` + `auth-context.ts` |
| `react-hooks/set-state-in-effect` | **資料抓取拆兩層**：純抓取函式（不碰 state）+ 呼叫端在 `.then/.catch/.finally` 更新 state + `useEffect` 內 `cancelled` flag | `AdminPage.tsx` 的 `fetchUserList` / `fetchUsers` |
| `react-hooks/immutability` | **不可就地修改物件**，state 更新一律回傳新物件 | `setUsers((prev) => prev.map(...))` |

另 `exhaustive-deps`、`incompatible-library`、`unsupported-syntax` 為 **warn 級**。

**CI 只擋 error**：`npm run lint` = `eslint .`，**未加 `--max-warnings 0`**。
本次實測狀態為 **0 errors, 3 warnings**（`AssessmentPage.tsx:365`、`LoginPage.tsx:36`、
`WorkspacePage.tsx:301`，皆為 `exhaustive-deps`）。這是已知既存狀態，不代表 lint 沒在跑。

**根目錄無 `.prettierrc`** —— `org.md` 預設的 Prettier 從未被引入（非「引入後又拿掉」）。

### ⚠️ `tailwind.config.js` 是死碼

`frontend/tailwind.config.js` 在 **Tailwind v4** 下**未被任何 `@config` 指令載入**，
實際生效的是 `src/index.css` 的 `@theme` 區塊。檔案仍存在會誤導讀者以為它是設定來源。

**引用 Tailwind 尺度（間距、斷點、色階）前，必須先確認哪一份設定真的生效**；
能實際編譯驗證的數值就直接編譯驗證，不要停在假設。

## 基礎設施技術

| 技術 | 版本 | 用途 | 備註 |
|---|---|---|---|
| PostgreSQL | **15**-alpine（本機）／**16**-alpine（staging 與 CI 測試 stack） | 唯一持久層 | **本機與其他兩處版本不一致** |
| nginx | alpine | SPA 服務 + `/api/` 反向代理 | 唯一對外的容器；SSE 設定是功能前提 |
| Docker / Compose | — | 本機與 staging | 三份 compose：根、`deploy/*.deploy.yml`、`deploy/*.test.yml` |
| Cloudflare Tunnel（`cloudflared`） | `latest` | 對外曝露 `cloud360.danniel.cc` | 以 `user: "1000:1000"` 執行以讀取 0400 憑證 |
| adminer | `latest` | 本機 DB 管理 | 僅本機 |
| GitHub Actions | — | CI/CD | `ci.yml`(4 job) + `deploy.yml`(3 job) + **11 組 gh-aw** |
| gh-aw（agentic workflows） | — | 開發流程自動化 | `.md` 原始檔 + 編譯後 `.lock.yml`；engine 皆為 `copilot` |
| Kiwi TCMS | 自架於 `tcms.danniel.cc` | 測案管理 | 於 `dc-infra` repo 維運；`ui-regression` workflow 送結果 |
| `@anthropic-ai/claude-code` | **未 pin**（`npm i -g`） | backend 容器內的 LLM 執行體 | 見 `dependencies.md` 隱性硬依賴 |
| OpenRouter | — | LLM 閘道（`LLM_PROVIDER=openrouter`，部署預設） | `ANTHROPIC_BASE_URL=https://openrouter.ai/api` |
| 本機 claude CLI | — | LLM 存取（`LLM_PROVIDER=cli`，本機開發） | macOS Keychain／`~/.claude`；**容器不可用** |
| n8n | — | 動態圖示 SVG webhook | 選填；失敗有 fallback 並記 WARNING |

### staging 部署目標

自有主機 `192.168.10.10`，經 Cloudflare Tunnel 對外為 `cloud360.danniel.cc`（ADR-0007）。
**雲端供應商 production 在範圍外**（ADR-0001／ADR-0002）。

## 建置系統

**類型：雙 build system，無 monorepo 工具。** 無 workspace、無 turborepo、無 nx、無 Makefile。
兩側各自獨立建置，由 CI 分 job 執行。

| 側 | 工具 | lockfile | 產出 |
|---|---|---|---|
| Backend | `pip` + `requirements.txt` | **無** | Docker image（無中間 artifact） |
| Frontend | `npm` + `package.json` | **`package-lock.json` 已 commit**（CI 用 `npm ci`） | `dist/` 靜態資產 → nginx image |

### npm scripts

| script | 指令 | 備註 |
|---|---|---|
| `dev` | `vite` | |
| `build` | `tsc -b && vite build` | **型別檢查在此發生** |
| `lint` | `eslint .` | 只擋 error |
| `preview` | `vite preview` | |
| `test:e2e` | `playwright test` | |
| **`gen:types`** | `npx --yes openapi-typescript@7.13.0 ../openapi.json -o src/types/api.d.ts` | **改 API 後必跑並 commit** |
| **`check:types`** | `node scripts/check-api-types.mjs` | **CI gate**：重產並逐位元比對 |

### 跨語言建置相依關係（本堆疊最重要的結構）

```
backend/main.py + 5 routers
        │ (backend/scripts/dump_openapi.py，由程式碼 import 而非打 live 端點)
        ▼
   openapi.json  ── CI gate: dump_openapi.py --check
        │ (openapi-typescript@7.13.0)
        ▼
frontend/src/types/api.d.ts  ── CI gate: npm run check:types
        │ (import type)
        ▼
   AdminPage.tsx（目前唯一消費者，其餘 9 支 fetch 檔仍手寫 interface）

frontend/Dockerfile ──build arg VITE_API_BASE_URL──► dist/（值編進 bundle）
deploy/render-env.sh ──► deploy/.env ──► docker-compose.deploy.yml ──► 容器
schema_rbac.sql ──(手動；產生腳本不在 repo)──► backend/services/rbac_seed_data.py
```

其他建置事實：

- `frontend` build **不依賴** `backend` 執行期（只需要 build 時的 `VITE_API_BASE_URL` 字串
  與 committed 的 `openapi.json`）。
- **`VITE_API_BASE_URL` 是 build ARG**：Vite 在建置期內聯，**執行期不可改**，
  改值必須重建 frontend image，不能只重啟容器。
- `deploy` stack 啟動順序：`db` → `backend` → `frontend`(nginx) → `cloudflared`。
- `db` 初始化掛載 `../schema_rbac.sql` 至 `/docker-entrypoint-initdb.d/01-schema_rbac.sql`，
  **僅在資料 volume 為空時執行一次**。
- backend image **額外裝 Node 22 + `@anthropic-ai/claude-code`**：`design_agent` 經
  claude-agent-sdk 以子行程呼叫 CLI，**缺 Node 會在請求期而非建置期爆炸**。

### Playwright 設定

`testDir: ./tests/e2e`；`BASE_URL` 指向 `docker-compose.test.yml` 起的 nginx（預設
`http://localhost:8090`）；timeout 30 秒；`workers: 1`；`fullyParallel: false`；
CI 下 `retries: 1`；reporter 為 `list` + `json`(`pw-report.json`) + `junit`(`junit.xml`)。

`ui-regression` workflow 讀 `pw-report.json` 的 `.stats.unexpected`，**非 0 即 `exit 1`**
（容忍 `stats.flaky`）。

## 版本治理現況

### Backend 依賴釘選：2/12（本輪由 0/12 改善）

`fastapi[standard]==0.141.1` 與 `pydantic==2.13.4` 已精確釘選，理由見上。
**其餘 10 支未 pin、無 lockfile**（無 `requirements.lock`、無 `poetry.lock`、無 `pyproject.toml`）。

**後果**：三個地方各自在執行當下解析最新版，彼此可能不同：

1. CI 的 `backend` job（`pip install`）
2. Docker image build（`backend/Dockerfile`）
3. staging 部署（`docker compose up --build`）

意即「CI 綠燈」與「staging 跑得起來」用的可能不是同一組套件版本，
且**上游任何一次 breaking release 都會直接打到部署**。這也讓「CI 綠但部署紅」難以重現。

**已被緩解的部分**：`fastapi`／`pydantic` 這兩支最會影響規格輸出的依賴已固定，
規格漂移 gate 的訊號因此可信。**未被緩解的部分**：供應鏈可重現性
（`sqlalchemy`、`claude-agent-sdk`、`bcrypt` 等仍浮動）。

**對照**：frontend 有已 commit 的 `package-lock.json`，前後端在這件事上治理水準仍不對等。

### 其他未 pin 的執行期元件

| 元件 | 現況 |
|---|---|
| `@anthropic-ai/claude-code` | `npm i -g` 無版本，backend image 每次 build 取最新 |
| `openapi-typescript` | 版本字串釘在 `7.13.0`，但**手寫兩份**且無一致性檢查 |
| `cloudflared` | image tag `latest` |
| `adminer` | image tag `latest`（僅本機，影響小） |

### 已 pin 或已鎖定的部分

| 元件 | 鎖定方式 |
|---|---|
| `fastapi` / `pydantic` | `==` 精確釘選 |
| frontend npm 依賴 | `package-lock.json`（已 commit），CI 用 `npm ci` |
| GitHub Actions | `.github/aw/actions-lock.json` |
| Python 執行環境 | `python:3.12-slim`（Dockerfile 與 CI 一致） |
| Node（frontend build） | `node:22-alpine` |
| PostgreSQL | image tag 有指定 major（15／16），但兩環境不同 |

### 版本錯配與 deprecated API 清單

1. **PostgreSQL 15（本機）vs 16（staging／CI 測試 stack）** —— 本機測不到的行為差異會在
   staging 才出現。
2. **`@types/react-router-dom@^5.3.3` vs `react-router-dom@^6.22.0`** ——
   v6 起自帶型別，此 `@types` 套件不但多餘，且型別描述的是 v5 API。
3. **pydantic v1 風格殘留**：`user_router.py:126,207` 仍用 `class Config: orm_mode = True`。
   pydantic v2 對此僅發出 deprecation warning。**因 pydantic 現已精確釘選，這不是立即風險**，
   但會在升版時浮現。
4. **`@app.on_event("startup")`**（`main.py:41`）：FastAPI 0.141.1 已推薦
   `lifespan` context manager。同樣因釘選而非立即風險。
5. **`datetime.utcnow()`**（`auth.py:33,35`）：Python 3.12 已 deprecated，
   應改 `datetime.now(timezone.utc)`。**注意 `activity.py` 已正確使用 timezone-aware
   的寫法**（`as_aware_utc()`），兩支模組在同一件事上做法不一致。
