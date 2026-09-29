# Developer Code Scan — cloud-360（reverse-engineering link 1）

- **Repo**：`opendiamonds/cloud-360`（工作目錄為 worktree `chiton`，目錄名不等於 repo 名）
- **HEAD**：`dc4b687b38f653ffc960ab0a23dd47ce4b1647aa`（`dc4b687`，2026-09-22 08:30:26 +0800）
- **Branch**：`danniel/docs/orchestration-brain-ideation`
- **掃描模式**：Full rescan（既有 store 回報 `UNKNOWN_SCOPE`，其覆蓋宣稱一律不採信）
- **深度**：Standard
- **證據標記慣例**（本檔全篇適用）：`[讀]` = 實際開檔逐行讀過；`[簽]` = 只以 grep／AST 取得函式或路由簽章，未讀實作；`[算]` = 由指令實際計算（指令附於該處）；`[未驗]` = 本輪未執行、未複驗，僅為靜態觀察。**本輪未執行任何測試、lint 或 validator**，故凡「通過／全綠」類宣稱一律不出現。

---

## Developer Code Scan Results

### Scan Coverage

- **Analyzed deeply**:
  - `backend/main.py`
  - `backend/models.py`
  - `backend/database.py`
  - `backend/requirements.txt`
  - `backend/services/agent_router.py`
  - `backend/services/rbac.py`
  - `backend/services/rbac_seed_data.py`
  - `backend/services/auth.py`
  - `backend/services/activity.py`
  - `backend/services/langgraph_runtime.py`
  - `backend/services/llm_provider.py`
  - `backend/services/prompt_guard.py`
  - `backend/cost/estimate_intake_router.py`
  - `backend/cost/advice_stream_router.py`
  - `backend/cost/advice_orchestrator.py`
  - `backend/cost/cost_advice_agent.py`
  - `backend/Dockerfile`
  - `frontend/src/App.tsx`
  - `frontend/src/config/api.ts`
  - `frontend/src/context/AuthContext.tsx`
  - `frontend/src/context/auth-context.ts`
  - `frontend/src/cost/slotRegistry.tsx`
  - `frontend/nginx.conf`
  - `frontend/Dockerfile`
  - `frontend/package.json`
  - `deploy/docker-compose.deploy.yml`
  - `deploy/docker-compose.test.yml`
  - `deploy/render-env.sh`
  - `deploy/.env.example`
  - `deploy/cloudflared/config.yml`
  - `docker-compose.yml`
  - `.github/workflows/ci.yml`
  - `openapi.json`（以程式解析全部 path／operation／schema，非逐行閱讀）

- **Skimmed only**:
  - `backend/services/`（除上列五支之外的 15 支模組：`diagram_builder.py`、`wa_rule_engine.py`、`wa_lens_engine.py`、`wa_collab_orchestrator.py`、`wa_score_service.py`、`review_orchestrator.py`、`review_router.py`、`review_agent.py`、`lens_router.py`、`lens_service.py`、`collab_router.py`、`collab_suggestions.py`、`user_router.py`、`design_agent.py`、`llm_limits.py`；其中 `review_router.py` 的 SSE 區段（L55–115、L460–484）與 `collab_router.py` 的 WebSocket 區段（L245–300）、`design_agent.py` 檔頭 L1–45 為實讀，其餘僅取簽章）
  - `backend/cost/`（除上列四支之外的 12 支模組：`estimate_intake_service.py`、`estimate_parser.py`、`estimate_readers.py`、`estimate_validator.py`、`estimate_access.py`、`estimate_audit.py`、`config.py`、`pricing_gcp.py`、`pricing_azure.py`、`pricing_offer_parser.py`、`pricing_query_parser.py`、`pricing_units.py`、`pricing_sdk.py`；`pricing_client.py` 為檔頭 L1–120 實讀＋其餘簽章）
  - `backend/tests/`（37 支測試檔：僅檔名清單與 grep 統計，未讀任何一支測試內容）
  - `backend/prompts/`、`backend/lenses/`（未開啟）
  - `backend/scripts/`
  - `frontend/src/pages/`（除 `App.tsx` 外；`CostPage.tsx` 讀前 80 行，其餘 8 支僅 grep）
  - `frontend/src/components/`（`Sidebar.tsx` 讀前 140 行，其餘僅 grep）
  - `frontend/src/hooks/`、`frontend/src/utils/`、`frontend/src/types/`
  - `frontend/tests/`
  - `scripts/`（`validate_cost_calculator_boundary.py` 與 `validate_pricing_lookup_boundary.py` 讀檔頭，其餘 8 支僅檔名）
  - `schema_rbac.sql`（讀檔頭 L1–29、cost／estimate／RBAC 區塊 L160–330，以及全檔的 `CREATE TABLE`／`COMMENT ON`／區塊標題 grep；308 列 seed 的逐列 INSERT 未逐行讀）
  - `schema.sql`
  - `.github/workflows/`（`ci.yml` 為實讀；`deploy.yml` 僅讀 job／step 骨架；11 支 gh-aw `*.md` 僅計數與 `engine:` 統計；其餘 `aidlc-sync-*.yml` 未開啟）
  - `.claude/`、`aidlc/`（框架與工作區，非應用程式碼，本輪不掃描）

### Packages Found

| 套件 | 型態 | 語言 | 用途 | 證據 |
|---|---|---|---|---|
| `backend/` | FastAPI 應用（單體） | Python 3.12 | 全部 HTTP／WS／SSE 對外介面 | `backend/Dockerfile:6`、`ci.yml:234` `[讀]` |
| `backend/services/` | 功能模組群（20 支 `.py`） | Python | A1 產圖、A3 WA 評核、A4 聊天、共編、RBAC、認證、LLM 供應商、LangGraph runtime | `[簽]` |
| `backend/cost/` | C1 成本／估價功能域（16 支 `.py` ＋ 4 支 YAML） | Python | 估價表上傳解析、建議 agent、目錄價 Port | `[簽]`＋4 支 `[讀]` |
| `backend/tests/` | 測試套件（37 支 `test_*.py`） | Python | `unittest` + `hypothesis` + `TestClient` | `[算]` `ls backend/tests/test_*.py \| wc -l` = 37 |
| `backend/lenses/`、`backend/prompts/` | 資料資產 | JSON／Markdown／drawio XML | WA Lens 標準、系統提示、架構圖模板 | `[未驗]` 僅檔名 |
| `frontend/` | Vite + React SPA | TypeScript | 6 個受保護頁面＋登入／403／等待授權 | `[讀]` `App.tsx` |
| `frontend/src/components/cost/` | C1 成本頁元件群（9 支） | TSX | 上傳區、雲別卡、檢查面板、建議面板、分享／儲存／歷史 | `[簽]` |
| `frontend/tests/e2e/` | Playwright e2e（2 支 spec） | TypeScript | 登入／RBAC 可視性／Admin 最後活動／估價工作區 | `[算]` `ls frontend/tests/e2e/` |
| `scripts/` | repo 層工具（10 支 `.py`） | Python | 4 支 CI validator、2 支 TCMS、3 支 aidlc-sync、1 支 LangGraph smoke | `[算]` `git ls-files scripts` |
| `deploy/` | 部署資產（5 檔） | YAML／Bash | staging compose、env 產生器、Cloudflare tunnel | `[讀]` |

**程式碼規模** `[算]`（`wc -l`）：backend Python 共 19,542 行（43 支非測試模組 + 37 支測試）；frontend `src/` + `tests/` 共 13,578 行（含 2,823 行自動產生的 `src/types/api.d.ts`）。最大單檔為 `backend/services/diagram_builder.py`（1,818 行）與 `frontend/src/pages/AssessmentPage.tsx`（1,861 行）。

### Build System

- **Type**：三條獨立管線，無 monorepo 建置工具（無 Nx／Turborepo／Makefile）。
  1. **Backend**：`pip install -r backend/requirements.txt`，無 lockfile、無 `pyproject.toml`、無 `setup.cfg` `[算]`（`find . -maxdepth 3 -name pyproject.toml -o -name .coveragerc …` 回傳空）。
  2. **Frontend**：npm + 已 commit 的 `package-lock.json`，CI 用 `npm ci`；`npm run build` = `tsc -b && vite build` `[讀]` `frontend/package.json`。
  3. **Docker**：兩支獨立 Dockerfile，由 compose 以 `context: ../backend` / `../frontend` 建置 `[讀]`。

- **Config Files**：`backend/requirements.txt`、`backend/Dockerfile`、`backend/.env.example`、`frontend/package.json`、`frontend/package-lock.json`、`frontend/vite.config.ts`、`frontend/tsconfig.json`（＋`tsconfig.app.json`、`tsconfig.node.json`）、`frontend/eslint.config.js`、`frontend/postcss.config.js`、`frontend/tailwind.config.js`、`frontend/playwright.config.ts`、`frontend/Dockerfile`、`frontend/nginx.conf`、`docker-compose.yml`（僅 db + adminer，本機用）、`deploy/docker-compose.deploy.yml`、`deploy/docker-compose.test.yml`、`deploy/render-env.sh`、`deploy/.env.example`、`deploy/cloudflared/config.yml`。

- **Build Dependencies（實際存在的耦合，非套件圖）**：
  - `backend` → `schema_rbac.sql`：compose 以 `../schema_rbac.sql:/docker-entrypoint-initdb.d/01-schema_rbac.sql:ro` 掛進 postgres `[讀]` `deploy/docker-compose.deploy.yml:23`。**僅在空 data volume 上執行**（註解逐字寫在 L21–22）。
  - `frontend` → `PUBLIC_URL`：`VITE_API_BASE_URL` 是**建置期** build arg，Vite 內聯，改 URL 必須重建 image `[讀]` `deploy/docker-compose.deploy.yml:71–73`、`frontend/Dockerfile:12–15`。
  - `openapi.json` ↔ `frontend/src/types/api.d.ts`：兩道漂移閘門互補 —— backend job 跑 `python scripts/dump_openapi.py --check`（規格 vs 程式）`[讀]` `ci.yml:256–260`；frontend job 跑 `npm run check:types`（型別檔 vs 規格）`[讀]` `ci.yml:197–198`。
  - `fastapi[standard]==0.141.1` / `pydantic==2.13.4` 的精確釘選正是為了讓上述 dump 位元決定性 `[讀]` `backend/requirements.txt:1–9`。
  - `backend` image 內含 Node 22 與 `@anthropic-ai/claude-code` CLI —— `design_agent.py` 以子行程驅動它，缺了會在**請求時**而非建置時失敗 `[讀]` `backend/Dockerfile:3–18`。

### APIs Discovered

| API 型態 | 位置 | 數量 | 證據 |
|---|---|---|---|
| REST / HTTP（已登錄 OpenAPI） | `openapi.json` | **42 個 path、55 個 operation、32 個 schema** | `[算]` python 解析 `openapi.json` |
| SSE（`text/event-stream`） | `agent_router.py`、`review_router.py`、`advice_stream_router.py` | **5 個端點**（見下） | `[讀]` |
| WebSocket | `collab_router.py:266` | **1 個**（`/api/collab/ws/{workspace_id}`），**未出現在 `openapi.json`** | `[讀]` |

**Router → prefix 對照** `[讀]` `backend/main.py:52–58`：

| Router | prefix |
|---|---|
| `agent_router` | `/api/architecture` |
| `review_router` | `/api/architecture` |
| `lens_router` | `/api/architecture` |
| `user_router` | `/api/auth` |
| `collab_router` | `/api/collab` |
| `estimate_intake_router` | `/api/cost/v1` |
| `advice_stream_router` | `/api/cost/v1` |

**5 個 SSE 端點（逐一實讀確認回傳 `media_type="text/event-stream"`）**：

1. `POST /api/architecture/generate` — `agent_router.py:129`
2. `POST /api/architecture/generate-wa-collab` — `agent_router.py:186`
3. `POST /api/architecture/reviews` — `review_router.py:173`（`_sse_response`，定義於 L70）
4. `POST /api/architecture/reviews/{review_id}/retry-suggestions` — `review_router.py:484`
5. `GET /api/cost/v1/sets/{set_id}/advice/stream` — `advice_stream_router.py:161–179`

> 派工 brief 所述的「三個既有 SSE 端點」對得上的是**前端三個消費點**，不是端點數：`WorkspacePage.tsx:514`、`AssessmentPage.tsx:104`、`components/cost/EstimateAdvicePanel.tsx:111` `[算]` grep `getReader()`。後端實際是 5 個。

**`/api/cost/v1` 完整面（10 個 operation）** `[讀]` `estimate_intake_router.py` + `advice_stream_router.py`：

| Method | Path | 授權 dependency | 行號 |
|---|---|---|---|
| POST | `/sets`（201） | `require_story_action("C1","edit")` | `:45,52` |
| PATCH | `/sets/{set_id}` | `C1.edit` | `:77,82` |
| GET | `/share-users` | `C1.view` | `:92,95` |
| GET | `/sets` | `C1.view` | `:100,108` |
| GET | `/sets/{set_id}` | `C1.view` | `:119,123` |
| DELETE | `/sets/{set_id}`（204） | `C1.edit` | `:128,132` |
| GET | `/sets/{set_id}/shares` | `C1.view` | `:138,142` |
| PUT | `/sets/{set_id}/shares` | `C1.edit` | `:147,152` |
| GET | `/sets/{set_id}/advice` | `C1.view` | `:159,163` |
| GET | `/sets/{set_id}/advice/stream` | `C1.view` | `advice_stream_router.py:161,165` |

**前端 API 呼叫形狀** `[算]`：`fetch(` 共 62 處、分佈 15 支檔（team.md 記載的「52 處／10 支」已過時）；手寫 `Authorization: Bearer` 共 36 處。URL 一律經 `src/config/api.ts` 的 `apiUrl()` / `wsUrl()` `[讀]`。

### Frameworks & Libraries

**Backend**（`backend/requirements.txt` `[讀]`，14 行宣告）：

| 套件 | 版本宣告 | 用途 |
|---|---|---|
| `fastapi[standard]` | `==0.141.1`（精確） | HTTP／WS／SSE 框架 |
| `pydantic` | `==2.13.4`（精確） | 請求／回應模型 |
| `langgraph` | `==1.2.11`（精確） | 成本建議 agent 的圖執行 |
| `langchain-openai` | `==1.6.2`（精確） | `ChatOpenAI` → OpenRouter |
| `openpyxl` | `==3.1.5`（精確） | Azure XLSX 估價表解析 |
| `PyYAML` | `>=6.0`（下限） | `cost/*.yaml` 設定載入 |
| `uvicorn`、`httpx`、`python-dotenv`、`sqlalchemy`、`psycopg2-binary`、`passlib[bcrypt]`、`bcrypt`、`pyjwt`、`claude-agent-sdk`、`hypothesis`、`boto3` | **未 pin** | — |

> 更新既有記載：team.md 寫「僅 `fastapi` 與 `pydantic` 兩支精確釘選、其餘 10 支未 pin」——本輪實測為 **5 支精確釘選 + 1 支下限 + 11 支未 pin**，且仍無 lockfile。

**Frontend**（`frontend/package.json` `[讀]`）：

| 套件 | 版本 | 用途 |
|---|---|---|
| `react` / `react-dom` | `^19.2.6` | UI |
| `react-router-dom` | `^7.18.2` | 路由 |
| `html2canvas` `^1.4.1`、`jspdf` `^4.2.1` | — | 評核 PDF／PNG 匯出 |
| `vite` | `^8.0.12` | 建置 |
| `typescript` | `~6.0.2` | 型別檢查 |
| `eslint` `^10.3.0` + `typescript-eslint` `^8.59.2` + `eslint-plugin-react-hooks` `^7.1.1` + `eslint-plugin-react-refresh` `^0.5.2` | — | lint（flat config） |
| `tailwindcss` `^4.3.0` + `@tailwindcss/postcss` `^4.3.0` | — | 樣式 |
| `@playwright/test` | `^1.56.0` | **唯一**的前端測試框架 |

> **無 vitest／jest／`@testing-library/*`** `[算]`（`package.json` `devDependencies` 逐項核對）——前端仍無 unit／component 測試層，team.md 該項記載成立。

**基礎設施**：PostgreSQL 16-alpine（deploy／test stack）／15-alpine（repo 根 `docker-compose.yml` 的本機 db）`[讀]`；nginx:alpine；`cloudflare/cloudflared:latest`；Python 3.12-slim；Node 22（backend image 內，供 `claude` CLI）。

### Test Coverage

- **Test Directories**：`backend/tests/`、`frontend/tests/e2e/`（＋`frontend/tests/fixtures/`、`backend/tests/fixtures/`）。
- **Test Frameworks**：
  - Backend：Python 內建 `unittest`（CI 指令 `python -m unittest discover -s tests -v` `[讀]` `ci.yml:266`）＋ `hypothesis` ＋ `unittest.mock`。**未使用 pytest** `[算]`（`requirements.txt` 無 pytest）。
  - Frontend：Playwright，單一 `chromium` project、`retries: process.env.CI ? 1 : 0` `[讀]` `frontend/playwright.config.ts:17,32–33`。
- **規模** `[算]`：
  - backend 測試檔 **37 支**（team.md 記載的 21 支已過時）。
  - `@given`（property-based）**17 處，分佈 10 支檔**：`test_estimate_parser`、`test_collab`、`test_activity`、`test_auth`、`test_diagram_builder`、`test_diagram_icons`、`test_design_agent`、`test_wa_rule_engine`、`test_estimate_validator`、`test_repo_contract_production_paths`（team.md 記載的「13 處／7 支」已過時）。
  - `TestClient` 出現於 **6 支測試檔 + `helpers.py`**：`test_auth`、`test_estimate_intake_api`、`test_user_list_endpoint`、`test_me_endpoint`、`test_cost_advice_agent`、`test_legacy_cost_retirement`（team.md 記載的「唯一使用例是 `test_user_list_endpoint`」已過時）。
  - frontend e2e **2 支 spec**：`regression.spec.ts`（490 行）、`estimate-workspace.spec.ts`（57 行）。
- **Coverage Config**：**absent**。`[算]` 全樹無 `.coveragerc`、無 `pyproject.toml`、無 `setup.cfg`，`requirements.txt` 無 `coverage` / `pytest-cov`，`ci.yml` 無任何 coverage step。`org.md` 宣告的 80% line coverage 目前**無量測機制**。
- **本輪未執行測試**：本機未安裝 backend 依賴，強行執行有耗盡時間預算的風險，故所有測試相關數字皆為靜態計數，**非執行結果** `[未驗]`。

### Code Quality Indicators

- **Linting**：
  - Frontend：`frontend/eslint.config.js`（flat config）；CI 跑 `npm run lint` = `eslint .`，**未加 `--max-warnings 0`** `[讀]` `package.json`、`ci.yml:188–189`。本輪未執行 lint，故不重述既有的「0 errors, 3 warnings」基準 `[未驗]`。
  - Backend：**完全沒有 linter／formatter／type checker** `[算]` —— 無 Ruff、無 Black、無 mypy／pyright，無 `pyproject.toml`、無 `.prettierrc`（repo 根亦無）。
- **CI/CD**（`.github/workflows/`，共 33 檔）：
  - `ci.yml` `[讀]`：5 個 job —— `gate`（偵測 `[aidlc-sync]` 回寫，命中則 skip 其餘四者）→ `repo-contract`、`frontend`、`backend`、`docker-build`（四者平行，皆 `needs: gate`）。
    - `repo-contract` 跑 **4 支 validator**：`validate_repo_contract.py`、`validate_env_contract.py`、`validate_cost_calculator_boundary.py`、`validate_pricing_lookup_boundary.py`（後兩支為新增，team.md 的「六道閘門」描述已不完整）。
    - `frontend` 跑 4 步：`npm run lint`、`npm run check:types`（API 型別漂移）、`npm run build`（含 `tsc -b`）、`dist/` 不得含 openapi 規格檔。
    - `backend` 跑 3 步：import smoke、`dump_openapi.py --check`（規格漂移）、`unittest discover`。
    - `docker-build` 建兩個 image，`push: false`。
  - `deploy.yml` `[未驗，僅讀骨架]`：3 個 job —— `deploy`（self-hosted `[self-hosted, linux, x64, cloud360]`、30 分逾時、`concurrency: deploy-10-10` 且 `cancel-in-progress: false`）→ `rollback`（20 分逾時，還原 last-good、開 revert PR、dispatch Deploy Doctor）→ `notify`（Slack）。部署後 `Remove the generated env file`（`if: always()`）。
  - **11 支 gh-aw agentic workflow**（`*.md` + 對應 `*.lock.yml`），**全部 `engine: copilot`** `[算]`：`code-drift-alert`、`contract-guard`、`daily-digest`、`deploy-doctor`、`issue-triage`、`lint-fix`、`local-dev-drift`、`pr-reviewer`、`release-watch`、`spec-sync`、`ui-regression`。
- **Documentation**：
  - repo 根有 `README.md`、`CLAUDE.md`、`AGENTS.md`、`DEPLOY.md`、`LOCAL-DEV.md`、`TESTING.md`。
  - 模組級 docstring 品質**高於一般水準**且偏向「寫下為什麼」：`llm_provider.py:1–37`（37 行檔頭說明兩種 provider 的非對稱互斥）、`activity.py:1–9`、`database.py:536–552`（`_apply_security_reviewer_j3a_view` 的四條契約）、`agent_router.py:10–17`（「契約（前端依賴，請勿變更）」）皆為實例 `[讀]`。
  - 設定檔註解同樣承載決策理由（`ci.yml:32–44` 說明為何不把 `github.actor` 放進 concurrency group；`requirements.txt:1–7` 說明為何用 `==` 而非 `~=`）`[讀]`。

### Technical Debt Signals

1. **`schema_rbac.sql` 無法作為既有環境的遷移手段（結構性）** `[讀]`
   - 它只在空 data volume 上執行（`deploy/docker-compose.deploy.yml:21–23` 的註解逐字說明）。
   - 且它在 L319 有裸的 `DELETE FROM role_permissions;`，檔頭 L18 亦逐字警告「role_permissions 會 DELETE 後重播預設（Admin UI 調過請先備份）」——對既有 staging 重跑會抹掉管理者的人工調整。
   - 唯一的線上 schema 演進路徑是 `backend/database.py` 的六支 `_ensure_*` 補丁（`:78–83`）。

2. **`_ensure_*` 補丁全部以 try/except 吞掉失敗** `[讀]` `database.py:204–209`、`:251–256`、`:321–326`、`:493–500`、`:519–526`
   - 每支的形狀都是 `except Exception as e: logger.warning(...)`，補丁失敗只留一行 warning，應用照常啟動。`_ensure_last_activity_schema` 的 docstring（`:504–510`）自己寫明了這個模式的代價：「不補則 staging 上每個已認證的請求都會失敗，而 CI 全綠 —— 測試以 in-memory SQLite 直接建表、從不經過本流程」。

3. **單行程假設散佈在三處狀態容器** `[讀]`
   - `collab_router.py:58–59` `ConnectionManager.active_connections: Dict[str, List[WebSocket]]`（行程內字典）。
   - `advice_orchestrator.py:21–26` `_executor`（`ThreadPoolExecutor(max_workers=2)`）、`_progress`、`_inflight` 皆為模組層全域。
   - `pricing_client.py:29` 磁碟快取寫進 `backend/cost/.pricing_offer_cache/`（容器本地，非共享）。
   - 目前成立是因為 `backend/Dockerfile:36` 的 `CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]` 沒有 `--workers`（單 worker）。任何多 worker／多副本化都會同時打破三者。

4. **兩套 LLM 客戶端棧已並存（不是一套）** `[讀]`
   - A 路徑：`claude-agent-sdk` → 子行程 `claude` CLI → OpenRouter，環境由 `services/llm_provider.py` 調教（`configure_provider_env()` 會改寫／刪除 `ANTHROPIC_*` 系列環境變數，`:114–142`）。消費者為 `design_agent.py`、`review_agent.py`、lens 相關模組。
   - B 路徑：`langchain_openai.ChatOpenAI` → OpenRouter HTTP，由 `services/langgraph_runtime.py:71–98` 建立，讀 `OPENROUTER_API_KEY`。消費者為 `cost/cost_advice_agent.py:132–162`。
   - 兩者對「模型名稱」的預設也不同：A 路徑預設 `google/gemini-3.7-flash`（`llm_provider.py:75`），B 路徑預設同樣字串但寫在 `langgraph_runtime.py:17` —— 同一個事實兩份物化，無任何測試鎖住兩者一致。

5. **`advice_stream_router.py:83` 使用未 import 的 `Any`** `[讀]`
   - `from typing import AsyncIterator`（L9）沒有帶入 `Any`，但 L83 寫 `last_progress_key: tuple[Any, ...] | None = None`。目前不炸是因為 L3 有 `from __future__ import annotations`（加上 PEP 526 的區域變數註解本就不求值）。**若有人移除那行 future import，即為 `NameError`**；而 backend 沒有任何 type checker 會提前發現。

6. **`ci.yml:204` 的註解與事實不符** `[算]`
   - 註解逐字寫「The OpenAPI spec is a complete API map (36 paths, 29 schemas)」，實測為 **42 paths、32 schemas**。註解是說明性的、不影響該 step 行為，但它是既有文件已對不上現況的實例。

7. **`role_permissions` 的 seed 有兩條語意不同的路徑** `[讀]` `rbac.py:58–111`、`database.py:154–172`
   - `ensure_role_permissions_seeded(db, force=False)` 在表**非空時整段 no-op**（`:63–65`）——改了 `DEFAULT_ROLE_PERMISSIONS` 對既有環境不生效。
   - 補救是 `ensure_missing_role_permissions(db)`（只 INSERT 缺失的 `(role, story_id)`，不 UPDATE／DELETE），在 `database.py:168–172` 被呼叫。任何新增 story id 必須走後者。
   - 此外 `database.py:536–597` 的 `_apply_security_reviewer_j3a_view` 是針對**單一列**的目標式補丁，用四態日誌（已套用／已跳過／已被管理員異動／未命中目標列）代替測試——docstring 自述「部署後人工核對是本變更唯一的驗證方式」。

8. **權限清單有三份物化，無一致性測試** `[讀]`
   - 正本 `rbac.py:23–35` `CANONICAL_ROLES`（11 個角色）。
   - 副本 1：`auth.py:108–112` `require_any_user` 的 11 個字串手寫 allowlist。
   - 副本 2：`schema_rbac.sql` L321+ 的 308 列 INSERT（與 `rbac_seed_data.py` 的 `DEFAULT_ROLE_PERMISSIONS` 互為兩份，後者檔頭自述「由 schema_rbac.sql 產生（勿手改；改 SQL 後重跑產生腳本）」——產生腳本本身不在 `scripts/` 內 `[算]`，即此宣稱的機制目前無對應檔案）。

9. **零 TODO／FIXME／HACK／XXX 標記** `[算]`
   - `grep -rn "TODO\|FIXME\|HACK\|XXX" backend/services backend/cost backend/*.py frontend/src scripts deploy` 僅 1 命中，且那一處是 `scripts/validate_env_contract.py:82` 把 `"TODO"` 當成偵測用的佔位字串樣式。此紀律應予保護。

10. **`openapi.json` 涵蓋不到 WebSocket** `[算]`
    - `/api/collab/ws/{workspace_id}` 存在於程式（`collab_router.py:266`）但不在 `openapi.json` 的 42 個 path 內（FastAPI 不登錄 websocket route）。結論：`dump_openapi.py --check` 與 `npm run check:types` 兩道漂移閘門**對 WebSocket 契約完全無效**。

11. **`user_router.py`（892 行）與 `collab_router.py`（593 行）無 service 層**，商業邏輯直寫 handler `[算]` `wc -l` ＋ `[簽]`。此為 team.md 已記載的既成事實，本輪複驗行數（team.md 記的 831／527 已過時）。

---

## Handoff Summary

- **Intent-relevant finding**：

  **既有成本能力的「可編排面」已經齊備且全部掛在 FastAPI dependency 上，但它對外的「串流」是 DB 輪詢的狀態事件、不是 token 串流——這兩件事共同決定了大腦能怎麼接。**

  1. **授權全在 dependency 層，不在 service 層。** `/api/cost/v1` 的 10 個 operation，每一個的授權都由 `Depends(require_story_action("C1", "view"|"edit"))` 承擔——`estimate_intake_router.py:52,82,95,108,123,132,142,152,163` 與 `advice_stream_router.py:165`，逐一實讀確認。`require_story_action` 定義於 `rbac.py:255–280`，它先檢查 `authorization_status != "approved"` 直接 403（`:262–267`），再查 `role_permissions` 表。**`cost/estimate_intake_service.py` 內部沒有第二道角色檢查**（僅 `estimate_access.py:29` 的 `can_view_set` 做擁有者／被分享者的資料列可見性過濾，那是 row-level 而非 role-level）`[簽]`。
     → 直接推論：intent 決定的「大腦以 HTTP 攜帶使用者 token 呼叫 `/api/cost/v1`」是**唯一能保留 C1 角色授權的呼叫方式**；同進程直呼 service 函式會整個繞過 `require_story_action`，而現有程式碼裡沒有任何備援會補上那一層。

  2. **C1 的 RBAC 種子早於本輪就存在，且不是空的。** `DEFAULT_ROLE_PERMISSIONS` 共 **308 列 × 11 角色 × 28 個 story id**，C1 有 11 列、C2 有 11 列、C3 有 11 列 `[算]`（import `services.rbac_seed_data` 實算）。C1 具 `edit` 的角色為 `Project_Architect`、`Project_Editor`、`Project_Admin`、`FinOps_Analyst`、`Platform_Admin`；`Developer`／`Platform_Engineer`／`Security_Reviewer` 三者 C1 三旗標全 false（即 `can('C1','view')` 為假，Sidebar 與 `/cost` 路由都會對他們隱藏／403）。

  3. **「串流」的實際形狀。** `advice_stream_router.py:81–158` 的 `_event_stream` 是一個 `while True` 迴圈：每輪 `orch.reclaim_stale_generating(db, set_id)` → 查 `Advice` 資料列 → `await asyncio.sleep(1.0)` → `db.expire_all()`。它送出的事件型別只有 `progress` / `completed` / `failed` / `timeout` / `heartbeat`（心跳間隔 `HEARTBEAT_SECONDS = 8.0`，L25），**沒有任何 token 級增量**。真正的 LLM 呼叫是 `cost_advice_agent.py:156` 的 `invoke_graph(compiled, {...})`——**同步 `invoke`，不是 `astream`**，跑在 `advice_orchestrator.py:55–57` 的 `ThreadPoolExecutor(max_workers=2)` 工作執行緒裡，結果一次寫回 `advice` 資料表（`:270–283`）。逾時為 `TIMEOUT = timedelta(minutes=5)`（`:19`）。
     → 直接推論：大腦若要把成本查詢的進度「逐字轉送」給使用者，**來源端沒有逐字可轉**；能轉送的只有 5 種狀態事件加一個完成後的完整文字。此點與上游 feasibility 已記錄的結論一致，本輪實讀複驗成立。

  4. **`langgraph_runtime.py` 具備 `astream_graph`（`:133–149`）但目前零消費者** `[算]`（全樹 grep `astream_graph` 僅命中定義檔與 `test_langgraph_runtime.py`）。亦即「既有 runtime 不支援串流」並非事實——它支援，只是 C1 沒有用。大腦決定自建 runtime 的理由若寫成「既有的不能串流」會是錯的；若寫成「避免與 C1 的同步 invoke 契約互相牽制」才對得上程式碼。

- **Risks / follow-up**（下游必須保留的事實）：

  1. **新資料模型無法靠 `schema_rbac.sql` 上線。** intent 能力 9（project → system → architecture-diagram 階層）與能力 4（記憶用獨立 schema）都是新 DDL。`schema_rbac.sql` 只跑在空 volume（`deploy/docker-compose.deploy.yml:21–23`），且會 `DELETE FROM role_permissions`（`schema_rbac.sql:319`）。既有 staging 的唯一遷移路徑是在 `backend/database.py` 新增 `_ensure_*` 補丁並掛進 `init_db()`（`:74–83`）——而那些補丁**全部吞掉例外**（`:204–209` 等五處），失敗只有 warning。`project.md` 的 blocking 規則（`schema_rbac.sql` + `DEPLOY.md` 同步）仍須照做，但要理解那是**新環境**的來源，不是**既有環境**的遷移手段。

  2. **階層確認不存在（複驗上游）** `[算]`：`system_id` 在 `backend` + `frontend/src` + `schema_rbac.sql` 全樹命中 **0**；`project_id` 同為 **0**；`schema_rbac.sql` 無 `projects`／`systems` 表。現行唯一的擁有關係是 `users → user_diagrams`（`models.py:91–105`，`user_id` 為 NOT NULL FK）＋ `diagram_shares` 多對多（`models.py:25–30`）。遷移既有架構圖時，`UserDiagram.user_id` 是 NOT NULL，新增中介層必須決定它是保留（雙寫）還是改指。

  3. **無 `CREATE SCHEMA` 先例** `[算]`：全樹無 `CREATE SCHEMA`、無 `search_path` 設定。`DATABASE_URL` 單一連線字串（`database.py:22–24`），SQLAlchemy `Base` 也沒有 `__table_args__ = {"schema": ...}` 的用例。「同一資料庫、獨立 schema」在本 repo 是零前例的做法，且測試路徑走 in-memory SQLite（`tests/helpers.py` 以 `sys.modules.setdefault("psycopg2", MagicMock())` 換掉驅動）——**SQLite 沒有 PostgreSQL 的 schema 概念**，跨 schema 的行為在現有測試基礎設施上無法被驗證。這是一個下游必須正面處理的驗證缺口。

  4. **Redis 確實是全新的第 5 個服務** `[算]`：全樹 13 個 `redis` 命中**全部**是領域內容（WA 規則建議文字 `wa_rule_engine.py:349,732,739,741`、lens JSON、drawio 模板、AWS 服務清單 prompt），**零基礎設施用途**。現有 deploy stack 為 4 個服務（`db`、`backend`、`frontend`、`cloudflared`，`deploy/docker-compose.deploy.yml:11–93`）。加第 5 個會同時觸發 `project.md` 的 env contract blocking 規則：新變數必須在**同一個 PR** 內讓 `deploy/render-env.sh`（L73–98 的 heredoc）寫它、`deploy/.env.example` 列它，否則 `scripts/validate_env_contract.py` 紅燈。另注意 `render-env.sh:59–69` 會拒絕任何含 `$` 的憑證值。

  5. **WebSocket 的網路路徑已經通，但有一個硬約束：必須掛在 `/api/` 之下。** `frontend/nginx.conf:16–32` 只有 `location /api/` 帶 `proxy_set_header Upgrade` / `Connection $connection_upgrade`；`$connection_upgrade` 的 `map` 是在 `frontend/Dockerfile:21–23` 以 `printf` 寫進 `/etc/nginx/conf.d/upgrade-map.conf` 的。`deploy/cloudflared/config.yml:17–18` 也已為 WS 設 `tcpKeepAlive: 30s`。`location /` 走 `try_files … /index.html`，WS 握手落在那裡會直接拿到 HTML。

  6. **既有 WebSocket 的授權模型與 REST 完全不同，且是唯一前例。** `collab_router.py:266–295` 的 `websocket_endpoint` **不用 `Depends`**：它自建 `SessionLocal()`，從 `websocket.query_params.get("token")` 取 token，呼叫 `_authorize_ws_user`（`:254–262`）→ `get_user_from_token(token, db, record=False)`。**`record=False` 是關鍵**：它跳過 `auth.py:80–83` 的 `record_activity` 寫入。也就是說，走 WebSocket 的互動**不會更新 `users.last_activity_at`**（節流 5 分鐘，`activity.py:25`）。大腦若以 WS 為主要互動通道，「最後活動時間」這個既有能力會對大腦使用者失效——這是一條會無聲發生的迴歸。
     另：token 放在 query string，會進 nginx／cloudflared 的 access log。這是既有做法，新 WS 若照抄即承接同一個暴露面（對應 ADR-0006 的 audit logging／network exposure 面向）。

  7. **新 HTTP 端點要過兩道漂移閘門，新 WebSocket 一道都不過。** 任何新 REST 端點必須在同一個 PR 重新 dump `openapi.json`（`ci.yml:256–260`）並重產 `frontend/src/types/api.d.ts`（`ci.yml:197–198`，2,823 行、已 commit）。WebSocket 不進 `openapi.json`（見 Technical Debt 第 10 點），所以大腦的 WS 事件語彙**沒有任何機械閘門**能擋住前後端漂移——`team.md` 記載的「`tsc -b` 對前後端 schema 落差無效」在 WS 這條路上是完整成立的，且連 OpenAPI 閘門這個補救都不存在。

  8. **成本建議的 job 模型無法承受多副本。** `advice_orchestrator.py` 的 `_executor` / `_progress` / `_inflight` 全是模組層全域（`:21–26`），`get_progress()` 只讀本行程記憶體（`:75–77`）。SSE router 在 `_progress_event`（`advice_stream_router.py:59–78`）直接呼叫 `orch.get_progress()`。若大腦的引入導致 backend 需要多 worker 或多副本，**同一個 estimate_set 的 SSE 連線可能落在沒有該 job 進度的行程上**，畫面會停在 `progress` 而永不 `completed`。`collab_router.py:58–59` 的 WS 廣播字典有完全相同的形狀。

  9. **第三個 OpenRouter 入口，不是第二個。** 見 Technical Debt 第 4 點：A 路徑（`claude-agent-sdk` + CLI 子行程）與 B 路徑（`langchain_openai.ChatOpenAI`）已經並存。intent 記錄的「兩份 OpenRouter 客戶端」這個債務描述，在大腦自建 runtime 之後實際會是**三份**。另有一個具體風險：`llm_provider.configure_provider_env()` 會**改寫整個行程的環境變數**（`:126–142` 會 `os.environ["ANTHROPIC_API_KEY"] = ""`、`setdefault("ANTHROPIC_BASE_URL", …)`），而它在每個 A1／A3 請求都被呼叫（`agent_router.py:74`）。`langgraph_runtime.py:61–68` 讀的是 `OPENROUTER_API_KEY`，目前不受影響——但兩者共用同一個行程環境，新增第三份客戶端時這個耦合必須被明寫。

  10. **`scripts/` 底下已有兩支針對 cost 的 import 邊界 validator，且在 CI 阻擋。** `validate_cost_calculator_boundary.py` 禁止 `estimate_parser.py` / `estimate_validator.py` / `estimate_readers.py` 及其遞移 import 的同套件模組出現 `httpx|requests|sqlalchemy|fastapi`（`:15–24`）；`validate_pricing_lookup_boundary.py` 禁止 4 支 intake 寫入路徑模組 import `pricing_client` / `pricing_sdk`（`:20–31`），並禁止 `SURVIVAL_RELATIVE` 白名單（8 支 `cost/pricing_*` 與 `cost/config.py`）以外的 backend Python 硬編 3 個計價 host（`:33–48`）。大腦若在 `backend/` 內新增任何會被這兩支掃到的模組（前者以 AST 遞移追 import，後者掃全 `backend/` 的 host 字串），必須先確認不會誤觸。

  11. **新增 story id 不可依賴空表 seed。** 若大腦需要自己的權限格（例如新的 story id），`ensure_role_permissions_seeded(force=False)` 在既有環境會整段 no-op（`rbac.py:63–65`）。正確落點是 `ensure_missing_role_permissions`（`rbac.py:84–111`，已在 `database.py:168–172` 被呼叫），它只 INSERT 缺失列。同時 `team.md` 的 A 規則要求 allow/deny 雙向測試，`project.md` 要求第一個新端點落地時補 TestClient 的 2xx／403 兩案。

  12. **既有記載已過時的數字（下游若引用 codekb 或 team.md 請以本輪為準）**：backend 測試檔 21 → **37**；`@given` 13 處／7 檔 → **17 處／10 檔**；`TestClient` 唯一使用例 → **6 支測試檔＋helpers**；backend 精確 pin 2 支 → **5 支＋1 支下限**；前端 `fetch(` 52 處／10 檔 → **62 處／15 檔**；`user_router.py` 831 行 → **892**；`collab_router.py` 527 行 → **593**；CI「六道閘門」→ `repo-contract` 已擴為 **4 支 validator**，全 CI 為 5 個 job／11 個檢查步驟。以上皆 `[算]`。

  13. **本輪未執行的事項（誠實記錄，不得被讀成已驗證）**：未執行 `python -m unittest`、未執行 `npm run lint`、未執行任何 `scripts/validate_*.py`、未啟動任何 compose stack、未讀任何一支測試檔的內容、未讀 `backend/prompts/` 與 `backend/lenses/` 的資料資產、未讀 `.github/workflows/` 的 11 支 gh-aw `*.md` 內容（僅計數與 `engine:` 統計）、未讀 `deploy.yml` 的 step 實作（僅骨架）。`backend/services/` 的 15 支與 `backend/cost/` 的 12 支模組僅取簽章，其內部行為在本份產出中**不構成已驗證事實**。
