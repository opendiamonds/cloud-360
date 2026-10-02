# Technology Stack — Cloud-360

> **基準**：`34aeef3`（2026-10-02）。**新鮮度等級與證據標記的定義在 `reverse-engineering-timestamp.md`**。
> 版本值取自 `backend/requirements.txt` 與 `frontend/package.json` 的**宣告**（兩檔本輪皆整檔讀過），
> **非安裝後的解析結果**——backend 無 lockfile，實際安裝版本可能與宣告不同。
> 由 `codekb/cloud-360@2026-09-22` 與 `codekb/cloud@2026-10-01` 合併。

---

## 語言與執行環境 〔A／B〕

| 項目 | 版本 | 證據 | 等級 |
|---|---|---|---|
| Python | **3.12**（`python:3.12-slim`） | `[讀]` `backend/Dockerfile` | A |
| TypeScript | `~6.0.2`（宣告） | `[讀]` `frontend/package.json` | A |
| **Node** | **已不在 backend 映像內** | `[讀]` `backend/Dockerfile` 全檔，無 Node、無 npm；檔頭逐字「no Claude Code CLI / Node runtime in the image」。Node 僅用於前端建置 | A |
| **PostgreSQL** | **`pgvector/pgvector:pg18`**（deploy stack）／15-alpine（repo 根 `docker-compose.yml` 本機 db） | `[讀]` `deploy/docker-compose.deploy.yml:40` | A |
| **Redis** | **`redis:8-alpine`**（deploy stack 第 5 個服務） | `[讀]` `:160` | A |
| **Ollama** | **`ollama/ollama:latest`**（第 6 個服務，**未釘選**） | `[讀]` `:281` | A |
| nginx | `nginx:alpine` | `[承:cloud-360@2026-09-22]` | C |
| cloudflared | `cloudflare/cloudflared:latest`（**未釘選**） | `[讀]` `:334` | A |

> **三處重大變更，兩份 store 皆未記載** 〔A〕：
> 1. **`db` 由 `postgres:16-alpine` 升為 `pgvector/pgvector:pg18`**（PG 主版號 16 → 18 ＋ pgvector 擴充）。
> 2. **新增 `redis:8-alpine` 與 `ollama/ollama:latest` 兩個服務**。
> 3. **backend 映像移除 Node 22 ＋ `@anthropic-ai/claude-code` CLI。**
>
> 三者皆由 commit `7ce1bee`（2026-09-27，`功能(brain-infra): Redis 與 Ollama 兩個服務、
> PG 18＋pgvector、部署期資料面與 ACL 探測`）與 `b4f0cdc`（2026-10-01，A3 遷移）帶進來 `[跑]` `git log`。

---

## Backend 套件（`backend/requirements.txt`）〔A〕

**本輪以程式解析** `[跑]`：**18 項宣告 ＝ 3 支精確 pin ＋ 1 支下限 ＋ 14 支完全浮動，無 lockfile。**

| 套件 | 版本宣告 | 用途 |
|---|---|---|
| **`fastapi`** | **`==0.111.0`（精確）** | HTTP／WS／SSE 框架。**無 `[standard]` extra** |
| **`pydantic`** | **`==2.13.4`（精確）** | 請求／回應模型；**兩個 dump 的位元決定性都依賴它** |
| **`openpyxl`** | **`==3.1.5`（精確）** | Azure XLSX 估價表解析 |
| `PyYAML` | `>=6.0`（下限） | `cost/*.yaml` 設定載入 |
| `uvicorn` | 無 | ASGI server |
| `httpx` | 無 | HTTP 客戶端；**也是 `starlette.testclient` 的實際前置** |
| `python-dotenv` | 無 | `.env` 載入 |
| `sqlalchemy` | 無（**刻意不設上限**） | ORM |
| **`psycopg[binary]`** | 無 | **PostgreSQL 驅動（v3）** |
| `passlib[bcrypt]` / `bcrypt` | 無 | 密碼雜湊 |
| `pyjwt` | 無 | JWT |
| `langgraph` | 無 | **全部 LLM 路徑的圖執行** |
| `langchain-core` | 無 | messages／tools |
| `langchain-anthropic` | 無 | `design_agent.py:121` 的 `ChatAnthropic`（經 `base_url` 指向 OpenRouter） |
| `langchain-openai` | 無 | `langgraph_runtime` 的 `ChatOpenAI` → OpenRouter |
| `hypothesis` | 無 | property-based testing |
| `boto3` | 無 | AWS Price List Query（`cost/pricing_sdk.py`；ADR-0018 保留） |

### 三處必須更正的記載 〔A〕

| 誰說的 | 說了什麼 | HEAD 實況 |
|---|---|---|
| `cloud-360@2026-09-22` | 「**17 項**宣告」、`fastapi[standard]==0.141.1`、`langgraph==1.2.11`、`langchain-openai==1.6.2`、`psycopg2-binary`、`claude-agent-sdk`、「**5 支精確釘選 ＋ 1 下限 ＋ 11 未 pin**」 | **18 項**；`fastapi==0.111.0`（**無 extra、版本不同**）；`langgraph` 與 `langchain-openai` **皆無 pin**；**`psycopg[binary]`** 取代 `psycopg2-binary`；**無 `claude-agent-sdk`**；**3 ＋ 1 ＋ 14** |
| `cloud@2026-10-01` | 「`langchain-openai` **未列入**」、「`claude-agent-sdk` **未列入／未 pin**」 | `langchain-openai` **在**（無 pin）；`claude-agent-sdk` **確實不在**，但它是**已移除**而非「缺 pin」 |
| `team.md` | 「`fastapi[standard]==0.141.1` 與 `pydantic==2.13.4` 精確釘選；其餘 10 個套件未 pin」 | `fastapi==0.111.0`（無 extra）；未 pin 的是 **14** 個 |
| link 1（§8） | 「2 項精確 pin、1 項下限、15 項完全浮動」 | **3 項精確 pin**（它自己的表裡列了 `openpyxl==3.1.5` 卻沒計入摘要）、1 下限、**14** 浮動 |

### 兩處檔內註解自述的理由（值得傳下去）〔A〕

1. **為何用 `==` 而非 `~=`**（`requirements.txt` 檔頭 `[讀:link1]`）：OpenAPI 規格輸出
   在同版本下位元決定性、**跨版本會飄（實測換版產生 20 行差異）**，不釘會讓漂移檢查
   在無關 PR 上變紅且**與真漂移不可區分**。明言「相容釋出形式（`~=`）仍會浮動，
   形式選錯等於沒釘 —— 故用 `==`」。
   > **本輪補充**：`pydantic` 的精確釘選現在同時保護**兩個** dump
   > （`openapi.json` 與 `ws-contract.json`），`dump_ws_contract.py` 的 docstring 逐字要求
   > 「升版時必須在同一個 PR 內重新 dump 並 commit」。
2. **`psycopg` vs `psycopg2-binary`**（`requirements.txt:14–22` `[讀:link1]`）：
   兩者是**兩個不同的套件**；SQLAlchemy 2.1 把隱含預設由 psycopg2 改為 psycopg(v3)；
   **顯式指定 driver 之後不設版本上限**（曾以 `sqlalchemy<2.1` 止血，已改為根治）。
   `database.py:23` 的預設值為 `postgresql+psycopg://...`，
   `:34–35` 把裸 `postgresql://` 改寫為 `postgresql+psycopg://` `[讀:link1]`。
   `[算:link1]` `grep -n "psycopg2" backend/requirements.txt` → **零**。

> **對 `team.md` Testing Posture 的連帶影響** 〔A〕：
> 1. 「`requirements.txt` 已含 `fastapi[standard]` 與 `httpx`，`TestClient` 前置條件已滿足」
>    ——**`[standard]` extra 已不在**，但 `httpx` 仍獨立宣告，而 `httpx` 才是
>    `starlette.testclient` 的實際前置。**結論仍成立、理由要改寫。**
> 2. 「在任何 DB import 前 `sys.modules.setdefault("psycopg2", MagicMock())`」
>    ——**已改為條件式 stub `psycopg`（v3）**（本輪 `[讀]` `tests/helpers.py:1–25`）。
>
> 本 codekb **只記載落差，不改規則檔**。

---

## Frontend 套件（`frontend/package.json`）〔A〕

`[讀:link1]` 全檔。

**`dependencies`（5）**：`react ^19.2.6`、`react-dom ^19.2.6`、`react-router-dom ^7.18.2`、
`html2canvas ^1.4.1`、`jspdf ^4.2.1`。
**無任何圖表套件**（圓餅自畫 SVG，與 `refined-mockups:c21` 的既有決定一致）。

**`devDependencies`（19）**：`eslint ^10.3.0`、`@eslint/js ^10.0.1`、
`typescript-eslint ^8.59.2`、`eslint-plugin-react-hooks ^7.1.1`、
`eslint-plugin-react-refresh ^0.5.2`、`globals ^17.6.0`、`typescript ~6.0.2`、
`vite ^8.0.12`、`@vitejs/plugin-react ^6.0.1`、`tailwindcss ^4.3.0`、
`@tailwindcss/postcss ^4.3.0`、`postcss ^8.5.15`、`autoprefixer ^10.5.0`、
`@playwright/test ^1.56.0`、**`openapi-typescript 7.13.0`（唯一精確 pin）**、
`@types/node ^24.12.3`、`@types/react ^19.2.14`、`@types/react-dom ^19.2.3`。

**`overrides`**：`openapi-typescript` 的 `typescript` 綁到 `$typescript`。

**`scripts`（9）**：`dev`、`build`（`tsc -b && vite build`）、
`lint`（`eslint .`，**無 `--max-warnings 0`**，故只擋 error）、`preview`、
`test:e2e`（`playwright test`）、`gen:types`、`check:types`、
**`gen:ws-types`、`check:ws-types`（新增的 WS 契約那一對）**。

**`package-lock.json` 已 commit**，CI 用 `npm ci` `[算]`。
**對照組：frontend 有 lockfile，backend 沒有。**

**前端測試框架仍只有 Playwright** `[讀:link1]`：`devDependencies` 無 vitest／jest／
`@testing-library/*`。`team.md` 的這條記載**本輪複驗仍成立**。

> **Tailwind 設定的既知陷阱** 〔D〕：`frontend/tailwind.config.js` 在 Tailwind v4 下
> 未被任何 `@config` 載入、是死碼；實際生效的是 `src/index.css` 的 `@theme`。
> **兩輪皆未複驗此點**，沿用既有記載。

---

## 建置系統 〔B〕

三條**獨立**管線，無 monorepo 建置工具（無 Nx／Turborepo／Makefile）：

1. **Backend**：`pip install -r backend/requirements.txt`。
   **無 lockfile、無 `pyproject.toml`、無 `setup.cfg`** `[跑:link1]`（六個設定檔全部不存在）。
2. **Frontend**：`npm ci` ＋ `npm run build` = `tsc -b && vite build` `[讀]`。
3. **Docker**：兩支獨立 Dockerfile，由 compose 以 `context: ../backend` / `../frontend` 建置 〔C〕。

**兩條契約產生鏈**（各兩道 CI 閘門）見 `code-structure.md`「建置與產物鏈」。

---

## 工具鏈現況（誠實記載）〔A〕

| 面向 | Frontend | Backend |
|---|---|---|
| Linter | ESLint 10 flat config，CI 跑 `eslint .`（**未加 `--max-warnings 0`**，故只擋 error）。**本輪實跑：0 errors, 2 warnings** `[跑:link1]` | **無** `[跑:link1]` |
| Formatter | **無**（repo 根無 `.prettierrc`——`org.md` 預設的 Prettier **從未被引入**，非「引入後又拿掉」）`[跑:link1]` | **無**（無 Black）`[跑:link1]` |
| Type checker | `tsc -b`（隨 `npm run build`）`[讀]` | **無**（無 mypy／pyright）`[跑:link1]` |
| 依賴鎖定 | `package-lock.json` 已 commit | **無 lockfile** `[跑]` |
| 覆蓋率量測 | 無 | **無**（無 `.coveragerc`、無 `coverage`／`pytest-cov`、CI 無 coverage step）`[跑:link1]` |

**`org.md` 宣告的「Formatter: Black (Python)」「Linter: Ruff，CI 強制」在 backend 側不成立**
——這不是團隊決議不用，是尚未補上。
**`org.md` 宣告的「最低 80% line coverage」目前既無法量測也無法強制，是宣告而非閘門。**
（本 codekb 如實記載承載機制缺席，**不弱化 `org.md` 的原文**。）

**`tsc -b` 的既知盲區** 〔C〕：前端存在手寫本地 interface 的形狀，與後端 Pydantic schema
無編譯期連結；OpenAPI 漂移閘門縮窄了此缺口但**未歸零**——`api.d.ts` 只在被實際採用的
呼叫點才起作用。**本輪未複驗採用率。**

---

## 基礎設施與 CI/CD 〔A／B〕

| 項目 | 值 | 等級 |
|---|---|---|
| Staging 主機 | 自架 `192.168.10.10`，經 Cloudflare Tunnel 對外為 `cloud360.danniel.cc`（ADR-0007） | 規則層 |
| **Staging 服務數** | **6**（`db`／`backend`／`redis`／`ollama`／`frontend`／`cloudflared`）`[跑]` ——**兩份 store 皆記 4** | A |
| 網路 | 2 個（`edge`／`internal`）；compose 檔頭 `:4` 逐字「Only nginx is reachable from outside. backend, db, redis and ollama have no ...」 | A |
| Volume | 3 個（`db_pg18`／`redis_aof`／`ollama_models`） | A |
| CI | GitHub Actions `ci.yml`，**5 job／14 條可讓 CI 紅燈的步驟**（逐條清單見 `code-quality-assessment.md`） | A |
| CD | `deploy.yml`，self-hosted runner `[self-hosted, linux, x64, cloud360]`、30 分逾時、`concurrency: deploy-10-10` 且 `cancel-in-progress: false` | C |
| Agentic workflows | **11 支 gh-aw**，全部 `engine: copilot`；`.github/workflows/` 共 **34 檔** `[跑]` | B |
| 測案管理 | 自架 Kiwi TCMS（`tcms.danniel.cc`，於 `dc-infra` repo 維運） | 規則層 |

---

## LLM 執行路徑（已全數收斂）〔A〕

> **這一節取代兩份 store 的「雙框架並存」敘述。** 技術棧已統一到 LangGraph ＋ OpenRouter。

| 路徑 | 框架 | 客戶端 | 消費者 | base URL | 預設模型寫在 |
|---|---|---|---|---|---|
| A | LangGraph | `langchain_anthropic.ChatAnthropic`（Anthropic 相容） | `design_agent`、`review_agent`、lens | `https://openrouter.ai/api`（`llm_provider.py:49`） | `llm_provider.py:52–54` |
| B | LangGraph | `langchain_openai.ChatOpenAI`（OpenAI 相容） | `cost_advice_agent` | `https://openrouter.ai/api/v1`（`langgraph_runtime.py:16`） | `langgraph_runtime.py:17` |

**`LLM_PROVIDER` 的有效值只剩 `openrouter` 一個** `[讀:link1]` `llm_provider.py:42–43`。
**`cli` 已退役**（`:45–47` `_RETIRED_PROVIDERS = ("cli",)`）：
設它會 `logger.error` 後退回 `openrouter`，**不 raise**；打錯字則 `logger.warning` 後同樣退回。
退役的理由逐字寫在 `:69–77` 的 ERROR 訊息裡（RAID R-11，見 `code-quality-assessment.md` T-19）。

**`claude_agent_sdk` 全樹零 import** `[跑]`，且 `test_a3_langgraph_migration.py:33,40`
有**兩個 `assertNotIn` 斷言它不得回來**。

> **剩下的分歧不是框架，是設定值**：兩個 base URL 一個有 `/v1` 一個沒有，
> 預設模型名稱兩份物化，**無任何測試鎖住一致**（`architecture.md` 約束九、
> `code-quality-assessment.md` T-4）。

---

## 本 intent 會引入的新技術面（修訂版）〔A〕

> **這張表與 `cloud-360@2026-09-22` 的同名表方向多處相反**，因為基礎設施已先行落地。

| 新增 | 現況 | 落地條件 |
|---|---|---|
| **Redis session store** | **服務已佈建**（`redis:8-alpine`、AOF volume、ACL、healthcheck）；`REDIS_URL`／`REDIS_USER`／`REDIS_PASSWORD` 已由 `render-env.sh:121` 等寫入並列於兩份 `.env.example`；`LOCAL-DEV.md:23,78` 已列為硬依賴；`test_render_env_redis.py` 已鎖住環境契約（`K-01`）。**但 `requirements.txt` 無 `redis` 套件、backend 應用程式碼零 import** `[跑]` | **env contract 的 blocking 工作已完成**，剩下的是**新增 Python 套件依賴 ＋ 寫客戶端**。注意新增依賴會放大「無 lockfile」的曝光面。**不要照舊記載去重做一遍「加第 5 個服務」** |
| **向量記憶（pgvector ＋ Ollama embedding）** | `db` 已是 `pgvector/pgvector:pg18`；`database.py:199–231` 的 `_ensure_vector_extension()` 已執行 `CREATE EXTENSION IF NOT EXISTS vector` 且**必須早於 `create_all`**；`ollama/ollama:latest` 已佈建、`OLLAMA_EMBED_MODEL=bge-m3` 已設。**但全樹尚無任何 `vector` 欄位** `[讀]` | `_ensure_vector_extension` 的 docstring 明寫**失敗不在此拋出**，真正的大聲失敗留給 `U5` 的 `vector(1024)` 欄位落地之後的 `create_all()`。新增 `vector` 欄位時要同時處理「測試走 in-memory SQLite」這一層 |
| **MCP server ＋ client（獨立進程）** | **真正的零起點** `[跑]`：18 項依賴無任何 MCP 套件；無 MCP 檔名／模組／類別；現行唯一的工具暴露機制是同進程 LangChain `@tool` ＋ LangGraph `ToolNode`。**且 `MCP` 這個字已被 RBAC story `H3` 佔用**（`user_router.py:85`） | 要新增依賴（無 lockfile）；跨進程是全新形狀；**codekb 與設計必須標明 `MCP` 的雙重語意**，否則下一個人 grep 命中 story 標籤就會得到「已經有了」的反向結論 |
| **第二套 LangGraph runtime** | `langgraph` 已在依賴內並運行；**`langgraph_runtime.astream_graph` 存在但零消費者** 〔C〕 | **自建的理由不可寫成「既有的不能串流」（不成立）**；第三個 OpenRouter 入口的環境變數耦合須明寫 |
| **新 WebSocket** | 既有 **2 條**（`/api/collab/ws/...`、`/api/brain/ws`）；**WS 契約鏈與兩道 CI 閘門已存在**，但只涵蓋大腦 | 必須掛在 `/api/` 之下（nginx 限制）；新增大腦訊息型別要過兩道閘門並保留 `BR4.4` 的 JSDoc |
| **獨立 PostgreSQL schema** | **零前例** 〔C〕：全樹無 `CREATE SCHEMA`、無 `search_path`、無 `__table_args__ schema` | 測試走 in-memory SQLite（**無 schema 概念**），跨 schema 行為在現有測試基礎設施上**不可驗證** |
| **階層資料模型** | **三表 ＋ 一次性遷移 ＋ 終檢斷言已落地**；`DEPLOY.md` 已同步。**但不在 `models.py`** | 要被 ORM 查到須補 `models.py`；`diagram_change_records` 的 90 天清除機制尚未落地，且 `project.md` 禁止 repo 內無人值守排程——**承載形式本身是待決設計問題** |
