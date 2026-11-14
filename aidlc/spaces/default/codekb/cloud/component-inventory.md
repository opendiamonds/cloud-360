# Component Inventory — Cloud-360

> **基準**：`34aeef3`（2026-10-02）。**新鮮度等級與證據標記的定義在 `reverse-engineering-timestamp.md`**。
> 本檔由 `codekb/cloud-360@2026-09-22`（42 節）與 `codekb/cloud@2026-10-01`（20 節）合併，
> 並加入本輪新發現的三組元件。

## 清單讀法（重要，先讀這段再往下）

本檔依**本輪的掃描深度**分成兩區，這是刻意的結構，不是排版：

- `## 深讀元件`（本輪整檔讀過）底下的 H3 名稱**逐字出現在**
  `reverse-engineering-timestamp.md` 的 `analyzed.components`，下一輪重掃的守門員以字面比對它們。
- `## 淺掃元件`（本輪只取簽章、計數、docstring 或片段）底下的 H3 **不在** `analyzed.components` 內。
  個別段落若標 `[讀]`，表示**那一句話的來源行**是實讀的，但該元件**整體**仍屬淺掃。

**本輪的深讀元件只有 5 個**，遠少於 `cloud-360@2026-09-22` 的 25 個。這是**刻意低報**，
不是覆蓋退步：那 25 個的內容**全部保留在本檔**（以 〔C〕 標記進淺掃區），但它們在
`34aeef3` 上**本輪未複驗**，故不得再讓 rerun guard 把它們當成已驗證。
依 `project.md` 的既有規則：「寧可低報覆蓋，也不可讓 rerun guard 之後把整支檔當成已驗證」。

**為什麼部分讀過的檔不升格**：掃描範圍的表達粒度是「檔案或目錄」，無法表達行區間。
把 `brain_router.py`（只讀了 455 行裡的 docstring ＋ 骨架）或 `database.py`
（只讀了 `init_db` 與幾處行號）宣告為深讀，會讓下一輪誤以為整檔已驗證。

---

## 深讀元件

### backend-app-shell 〔A〕
- **來源**：`backend/main.py`（67 行，**本輪整檔範圍內**）`[讀]`
- **職責**：建立 FastAPI `app`（`:31`，`title="Cloud-360 API"`）、CORS 中介層（`:35–45`，
  由 `CORS_ORIGINS` 注入，預設 `http://localhost:5173,http://127.0.0.1:5173`）、
  `startup` 事件（`:48–52`：`configure_provider_env()` ＋ `init_db()`）、
  **8 條 `include_router`**（`:54–63`）、`GET /` 回 `{"message": "Cloud-360 Backend is running"}`（`:65–67`）。
- **Router → prefix 對照** `[讀]` `:54–63`：

  | 行 | router | prefix |
  |---|---|---|
  | `:54` | `agent_router` | `/api/architecture` |
  | `:55` | `review_router` | `/api/architecture` |
  | `:56` | `lens_router` | `/api/architecture` |
  | `:57` | `user_router` | `/api/auth` |
  | `:58` | `collab_router` | `/api/collab` |
  | `:59` | `estimate_intake_router` | `/api/cost/v1` |
  | `:60` | `advice_stream_router` | `/api/cost/v1` |
  | `:63` | `brain_router` | `/api/brain`（**DEMO SCOPE**） |

- **環境載入形狀** `[讀]`：`:3` `from env_bootstrap import BACKEND_DIR, load_backend_dotenv`、
  `:25` `load_backend_dotenv(override=True)`——`.env` **只從 `backend/.env` 載入**，
  不看行程啟動目錄（`:21–24` 的註解說明這防的是什麼）。
- **`configure_provider_env()` 被呼叫兩次** `[讀]`：`:29`（模組層）與 `:48–52`（startup）。
  `:27–28` 的註解說明第二次的目的是**讓退役的 `LLM_PROVIDER=cli` 在啟動時就記一行 ERROR**。
- **本 intent 注意**：新 router 必須在此處註冊並選定 prefix；WebSocket 的 prefix 受 nginx 限制
  須落在 `/api/` 之下（`architecture.md` 約束一）。移除 brain demo 時要動**兩處**：
  `:7` 的 import 與 `:63` 的 `include_router`（`:62` 的註解寫「下面兩行」但 `:63` 之後只有一行）。

### design-agent-core 〔A〕
- **來源**：`backend/services/design_agent.py`（218 行，link 1 逐行 `[讀]`，`_progress_queue`
  13 處命中逐段複驗，行號本輪複驗值）
- **職責**：A1 產圖的 LangGraph agent。`:9–12` imports `StateGraph`／`START`／`END`／
  `add_messages`／`MemorySaver`／`ToolNode`；`:15` `from langchain_core.tools import tool`；
  `:64` `@tool`（`draw_architecture_diagram`）；`:111` `tool_node = ToolNode(tools)`；
  `:121` `ChatAnthropic(...)`；`:169` `memory = MemorySaver()`；
  `:171–175` 簽章 `async def run_design_agent(messages, current_xml=None, thread_id="default-thread")`。
- **這是 repo 內「agent 對 LLM 暴露工具」的唯一機制**：同進程 LangChain `@tool` ＋
  LangGraph `ToolNode`，**沒有任何跨進程協定**（`architecture.md` 約束十二）。
- **缺陷（高嚴重度）**：`:31` `_progress_queue` 與 `:32` `_last_xml` 皆為**模組層單槽全域**，
  工具端與入口端都讀「當下的模組全域」。**兩個重疊請求即導致跨使用者內容錯送**
  （A 收到 B 的架構圖 XML）或**事件靜默丟棄**（含 `error`）。
  逐行證據、兩種危害、兩個生產呼叫點、`thread_id` 為何不是解法、以及
  **repo 內已有的正解**，完整寫在 `architecture.md` 約束四。
  登錄為上游約束 `C-R3`，是能力 1 與能力 8 的實作前置條件。
- **金鑰讀取** `[讀:link1]` `:118–119`：
  `api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("OPENROUTER_API_KEY") or ""`、
  `base_url = os.environ.get("ANTHROPIC_BASE_URL")`。`or ""` 的兜底使**金鑰為空字串時
  `ChatAnthropic` 仍會被建起來**（`:121`），失敗落在呼叫時——這是 RAID R-11 的機制一半。

### llm-provider-gateway 〔A〕
- **來源**：`backend/services/llm_provider.py`（**178 行**，`[跑]` `wc -l`；link 1 全檔逐行 `[讀]`）
- **本輪重大變更**：**本檔已於 `34aeef3` 重寫（237 → 178 行）**，`LLM_PROVIDER=cli` **退役**。
  兩份 store 對本模組的記載**皆已過時**。
- **職責與逐行事實** `[讀:link1]`：

  | 行 | 事實 |
  |---|---|
  | `:42–43` | `OPENROUTER = "openrouter"` / `_VALID_PROVIDERS = (OPENROUTER,)` ← **有效值只剩一個** |
  | `:45–47` | 註解「Recognised, but no longer selectable」/ `_RETIRED_PROVIDERS = ("cli",)` |
  | `:49` | `ANTHROPIC_BASE_URL` → `https://openrouter.ai/api`（**無 `/v1`**） |
  | `:52–54` | 預設模型名稱（`google/gemini-3.7-flash` ×2、`google/gemini-2.5-flash` ×1） |
  | `:60–63` | docstring 逐字：「A retired value logs at ERROR and a typo logs at WARNING; neither raises」 |
  | `:65` | `raw = os.environ.get("LLM_PROVIDER", "").strip().lower()` |
  | `:66–67` | 空值 → `return OPENROUTER` |
  | `:68–78` | 退役值 → `logger.error(...)` 後 `return OPENROUTER`。**ERROR 級，不 raise** |
  | `:79–86` | 打錯字 → `logger.warning(...)` 後 `return OPENROUTER`。**WARNING 級** |
  | `:120–130` | `llm_auth_ready()` → `bool(OPENROUTER_API_KEY or ANTHROPIC_AUTH_TOKEN)` |
- **退役的 ERROR 訊息逐字點名原因** `[讀:link1]` `:69–77`（繁中）：
  「A3 遷移到 LangGraph／OpenRouter 之後已無 `claude` CLI 子行程可認證，而該模式會刪除
  `ANTHROPIC_AUTH_TOKEN`／`ANTHROPIC_BASE_URL`——留著它會讓金鑰被清空而健康檢查仍回報正常（RAID R-11）」。
- **`configure_provider_env()` 改寫整個行程的環境變數**，在 `main.py:29` 與 `:48–52` 各呼叫一次。
- **本 intent 注意**：第三個 LLM 入口若自建客戶端，會與本模組共用同一份行程環境
  （`architecture.md` 約束九）。

### backend-container-image 〔A〕
- **來源**：`backend/Dockerfile`（31 行，**本輪整檔** `[讀]`）＋ `backend/requirements.txt`
  （18 項宣告，link 1 全檔 `[讀]` ＋ 本輪程式重新解析 `[跑]`）
- **本輪重大變更**：**映像已移除 Node 22 與 `@anthropic-ai/claude-code` CLI。**
  現為 `FROM python:3.12-slim` ＋ `apt-get install curl ca-certificates`，無 Node、無 npm。
  檔頭註解逐字：「LLM paths (A1 Design / A3 Review / Lens / cost advice) use LangGraph +
  OpenRouter HTTP clients — **no Claude Code CLI / Node runtime in the image**」。
  **兩份 store 的「image 內含 Node 22 ＋ claude CLI」與「CLI 缺席會在請求時失敗」皆已作廢。**
- **其他本輪實讀事實**：`ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1`；
  `WORKDIR /app`；**非 root 使用者** `useradd --create-home --uid 10001 appuser` ＋
  `chown -R appuser:appuser /app` ＋ `USER appuser`；`EXPOSE 8000`；
  **`HEALTHCHECK`**（30s 間隔、5s 逾時、40s start-period、3 retries，以 `urllib.request`
  打 `http://127.0.0.1:8000/` 判 200）；
  `CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]`——**無 `--workers`**，故單 worker。
- **依賴宣告** `[跑]` 程式解析：**18 項 ＝ 3 支精確 pin（`fastapi==0.111.0`、
  `pydantic==2.13.4`、`openpyxl==3.1.5`）＋ 1 支下限（`PyYAML>=6.0`）＋ 14 支未 pin，無 lockfile**。
  逐項清單見 `technology-stack.md`。
- **本 intent 注意**：新增 MCP 套件或 `redis` 客戶端都會動到這 18 項，而**無 lockfile**
  ——CI／Docker build／staging 三處各自解析當下最新版。

### openapi-contract 〔A〕
- **來源**：`openapi.json`（repo 根，**本輪以 Python 完整解析全部 path／operation／schema** `[跑]`）
- **職責**：前後端型別契約的單一真實來源；由 `backend/scripts/dump_openapi.py` 產生，
  `frontend/src/types/api.d.ts` 由它衍生。
- **本輪實算** `[跑]`：OpenAPI **3.1.0**、**42 path**、**55 operation**、**39 schema**。
  per-prefix：`/` 1／1、`/api/architecture` 13／16、`/api/auth` 15／16、
  `/api/collab` 7／12、`/api/cost` 6／10。
  > **更正**：`cloud-360/` 記「32 個 schema」`[承:cloud-360@2026-09-22]`，**HEAD 是 39**。
- **缺口**：**不涵蓋 WebSocket**（FastAPI 不登錄 websocket route）。兩條 WS
  （`/api/collab/ws/{workspace_id}`、`/api/brain/ws`）都不在 42 個 path 內。
  **但 WS 另有獨立的契約鏈與兩道閘門**——見「WS 訊息型別契約」元件與 `architecture.md` 約束二。

---

## 淺掃元件

> 以下元件本輪**僅取簽章、計數、docstring 或片段**，**不在** `analyzed.components` 內。
> 引用其內部行為前請自行複驗。段落的 〔等級〕 標示該節內容的來源與新鮮度。

### 大腦 WS Gateway（demo scope）〔B，新增〕
- **來源**：`backend/services/brain_router.py`（**455 LOC** `[跑]`）。
  **本輪只讀 docstring `:1–31` `[讀]` ＋ 函式骨架 `[算]`；455 行的本體未讀。**
- **落地**：commit `f9c5bda`（2026-09-28，`功能(brain): demo-scope 的大腦垂直切片，供今晚展示用`）`[跑]`
- **職責**：`/api/brain/ws`（`:238` `@router.websocket("/ws")` → `:239` `async def brain_ws(websocket)`）。
- **函式骨架** `[算]`：`:51` `router = APIRouter()`、`:87` `_session_for(user_id)`、
  `:116` `_classify(text)`、`:148` `_llm_available()`、`:152` `_respond(capability, text)`、
  `:169` `_respond_via_llm(...)`、`:200` `_respond_locally(...)`、`:210` `_envelope(...)`、
  `:226` `_send(...)`、`:230` `_send_error(...)`、`:411` `_run_turn(...)`。
- **⚠️ 這是 DEMO SCOPE，不是 `U13` 的正式交付。** docstring 逐字自述它
  「為了**今晚的成果展示**而寫的最小垂直切片，**不屬於任何已核可的 AI-DLC 工作單元**」，
  且「`U13` 落地時**整支取代本檔**（而不是逐段改寫）」。
  **完整的「做了什麼／刻意沒做什麼／指派給哪個單元」對照表在 `architecture.md`
  的「本輪新發現：大腦 demo-scope 垂直切片已存在且正在運行」一節。**
- **三件不能漏的事**：(1) 它**存在且已掛載**；(2) 它**不是 `U13`**，`U11`／`U13`／`U14` 仍未開始；
  (3) **不要把 `_classify` 的關鍵詞計分當成「信心值模型已有雛形」**——那正是 `OQ-10` 在質疑的東西。
- **行程內 session**：`_session_for(user_id)` 背後是行程內 dict，docstring 自述「**重啟即失憶**」，
  沿用 `K-12` 的「單一後端行程」假設；Redis 持久化指派給 `U10 session-store`。

### WS 訊息型別契約 〔B，新增〕
- **來源**：`backend/services/brain_ws_contract.py`（**783 LOC** `[跑]`）
  ＋ `backend/scripts/dump_ws_contract.py`（`[讀]` `:1–40` docstring）
  ＋ `ws-contract.json`（repo 根，**31,012 bytes** `[跑]` `wc -c`；本輪只取頂層 key
  `['components','info','openapi','paths']`）
  ＋ `frontend/src/types/ws-contract.d.ts`（產生檔）
- **落地**：commit `c619c3f`（2026-09-28，`功能(brain-ws-contract): WS 訊息型別契約與兩道 CI 型別閘門`）`[跑]`
- **⚠️ 契約本體（783 行）本輪完全未讀**（E 級）。九種伺服器訊息、六種客戶端訊息的
  **完整 payload 欄位定義是 `U2`／`U13` 的直接輸入，列為待查**。
  本輪只從 `brain_router.py` 的 docstring 得知其子集。
- **兩道 CI 漂移閘門（本輪實查存在）** `[算]`：
  `ci.yml:291` `python scripts/dump_ws_contract.py --check`（backend job）、
  `ci.yml:210` `npm run check:ws-types`（frontend job）。
  測試另有 `backend/tests/test_dump_ws_contract.py`、`test_ws_contract.py`（兩者含 `@given`）。
- **覆蓋範圍的洞** `[跑]` `grep -c "collab" ws-contract.json` → **0**：
  **只涵蓋大腦，不涵蓋 `/api/collab/ws/{workspace_id}`。** 既有共編 WS 仍零契約閘門。
- **三項設計決定**（docstring 逐字，`architecture.md` 約束二有完整引述）：刻意不 import `main`、
  規格檔刻意放 repo 根而非 `frontend/public/`（避免把訊息地圖對未認證訪客公開）、fail-closed。

### 階層遷移 〔B，新增〕
- **來源**：`backend/services/hierarchy_migration.py`（**496 LOC** `[跑]`，**本輪只取骨架** `[算]`）
  ＋ `backend/scripts/run_hierarchy_migration.py`（`[未掃]`）
- **落地**：commit `9e14145`（2026-09-28，`功能(hierarchy-data): projects／systems／diagram_change_records 三表與一次性遷移`）`[跑]`
- **骨架** `[算]`：`:204` `migrate_hierarchy(db) -> MigrationCounts`、`:269` `_ensure_hierarchy_schema(db)`、
  `:361` `_users_holding_diagrams(db)`、`:380` `_resolve_default_pair(...)`、
  `:458` `_assign_unassigned_diagrams(db, user_id, system_id)`、`:477` `_assert_no_unassigned_diagrams(db)`。
- **這是本 repo 第一個「有終檢斷言的一次性遷移」前例**；`[跑:link1]` 其測試本輪跑綠並印出
  `users_processed = 1`／`default_pairs_created = 1`／`diagrams_assigned = 1`
  與「終檢通過：`user_diagrams` 中 `system_id IS NULL` 的列數為 0（`AC9.1.4`）」。
- **邊界（下游最容易誤讀的一點）**：schema ＋ 遷移 ＋ 遷移測試**已有**；
  **ORM model、router、service 都還沒有**。`[跑:link1]`
  `grep -rln "system_id" backend/ --include='*.py'` → 僅 4 檔（本模組、其測試、CLI 入口、brain demo）。
  **這推翻 `project.md` 記載的「`system_id` 命中 0 次」**——那在當時為真，在 HEAD 上已不為真。
  完整說明在 `architecture.md`「階層三表已在 schema，但不在 ORM／router／service」。

### 大腦前端入口 〔E，新增〕
- **來源**：`frontend/src/pages/BrainPage.tsx`（**403 LOC** `[跑]` `wc -l`）
- **路由**：`frontend/src/App.tsx:88` 的 `/brain` `[讀:link1]`
- **⚠️ 本輪完全未讀其內容。** 只知檔名、LOC 與路由掛載點。
  **`/brain` 路由在兩份 store 都沒有記載**（`cloud/` 的 `App.tsx` 雖在其 deep 集合內，
  但掃描 commit `5fd8f14` 早於 `BrainPage` 落地）。

### Session／向量基礎設施（已佈建，應用零消費）〔A，新增〕
- **來源**：`deploy/docker-compose.deploy.yml`（`[讀]` 區塊結構 ＋ image 行 ＋ redis 相關註解）
  ＋ `deploy/render-env.sh:121` ＋ `deploy/.env.example:94–124` ＋ `backend/.env.example:101–124`
  ＋ `backend/tests/test_render_env_redis.py`（`[算]`，只讀 5 行）
- **落地**：commit `7ce1bee`（2026-09-27，`功能(brain-infra): Redis 與 Ollama 兩個服務、
  PG 18＋pgvector、部署期資料面與 ACL 探測`）`[跑]`
- **已就緒**：`redis:8-alpine`（第 5 個 service，無 `ports:`，AOF volume，ACL，healthcheck）、
  `ollama/ollama:latest`（第 6 個 service）、`db` 升為 `pgvector/pgvector:pg18`、
  `REDIS_URL`／`REDIS_USER`／`REDIS_PASSWORD`／`OLLAMA_BASE_URL`／`OLLAMA_EMBED_MODEL`
  已由 `render-env.sh` 寫入並列於兩份範本、`LOCAL-DEV.md` 已列為本機硬依賴。
- **未就緒（`U10` 的真正起點）** `[跑]`：`requirements.txt` **無 `redis` 套件**；
  backend 應用程式碼**零 import**（唯一命中是上述那支**部署設定契約測試**，不是客戶端）。
- **⚠️ 這整段推翻 `cloud-360/architecture.md` 約束八**（「Redis 是全新的第 5 個服務」）
  **與其 System Overview**（「4 個服務／無快取層／無 Redis」）。**link 1 也沒發現這一項。**
  完整說明在 `architecture.md` 約束八。

### ORM 資料模型 〔B〕
- **來源**：`backend/models.py`（348 行）。本輪**只以程式解析 `__tablename__` 與 `Table(`** `[跑]`。
- **13 個 ORM 模型 ＋ 1 個 association table** `[跑]`：`users`、`role_authorization_requests`、
  `user_diagrams`、`user_diagram_chats`、`architecture_reviews`、`wa_lenses`、`role_permissions`、
  `estimate_sets`、`estimates`、`estimate_line_items`、`estimate_shares`、
  `estimate_audit_events`、`advice`；association table `diagram_shares`。
- **`projects`／`systems`／`diagram_change_records` 三表不在 ORM 內** `[跑]`
  ——雖然它們已在 `schema_rbac.sql`（見「階層遷移」）。
- **既有擁有關係** `[承:cloud-360@2026-09-22]`：唯一的是 `users → user_diagrams`
  （`:91–105`，`user_id` 為 **NOT NULL** FK）。
  **但歸屬的權威來源已改為 `user_diagrams.system_id`**（`DEPLOY.md:309` 逐字：
  「`user_id` 只回答『誰建的』，不回答歸屬」）`[讀]`——這一句是本輪新查到的，
  它改變了「插入中介層時 `user_id` 的 NOT NULL 要保留還是改指」這個問題的框架。

### 資料庫連線與啟動補丁 〔B〕
- **來源**：`backend/database.py`（656 行 `[跑]`）。本輪實讀 `init_db()`（`:85–96`）、
  7 支 `_ensure_*` 的定義行、12 處 `except Exception` 的行號、`_ensure_vector_extension`
  的 docstring（`:199–231`）；**其餘未讀**。
- **職責**：`engine`／`SessionLocal`／`get_db`／`init_db()`；**7 支** `_ensure_*` 補丁；
  預設 persona 種子（受 `_allow_insecure_default_personas()` 閘門控制 `[承:cloud-360@2026-09-22]`）。
- **7 支補丁與執行順序** `[讀]` `:85–96`（**第 1 支在 `create_all` 之前，方向與其餘六支相反**）：
  `_ensure_vector_extension()`（`:199`）→ `create_all` → `_ensure_a4_schema()`（`:234`）
  → `_ensure_j5_schema()`（`:262`）→ `_ensure_a3_schema()`（`:309`）
  → `_ensure_cost_schema()`（`:379`）→ `_ensure_estimate_intake_schema()`（`:435`）
  → `_ensure_last_activity_schema()`（`:563`）。
  > `cloud-360/` 記「6 支（`:74–83`）」`[承:cloud-360@2026-09-22]` ——**HEAD 是 7 支、`:85–96`**。
- **`_ensure_vector_extension` 的設計** `[讀]` `:199–231`：執行
  `CREATE EXTENSION IF NOT EXISTS vector`；**必須早於 `create_all`**，因為 `vector` 型別不存在時
  任何宣告 `vector` 欄位的表會在 `create_all()` 就以 `type "vector" does not exist` 失敗；
  **失敗不在此拋出**（只記 warning，真正的大聲失敗留給 `U5` 的 `vector(1024)` 欄位落地之後）。
  `init_db()` 的註解逐字：「順序寫錯的後果是**啟動失敗**，不是延後修復」。
- **C1 退役機制** `[承:cloud-360@2026-09-22]`：`_ensure_cost_schema()` 啟動時把
  `diagram_cost`／`diagram_cost_line`／`pricing_cache`／`cost_audit_event`
  **RENAME 成 `archive_*`**，新環境不再建立 live 表，本函式不做 DROP。
  （本輪 `[跑]` 複驗 `schema_rbac.sql` 的 `archive_*` 四表在 `:191`／`:198`／`:208`／`:217`。）
- **風險（行號已更新）** `[算]` 本輪重新定位：補丁一律以
  `except Exception as e: logger.warning(...)` 吞掉失敗。12 處 `except Exception` 在
  `:192`、`:228`、`:257`、`:304`、`:374`、`:402`、`:406`、`:421`、`:430`、`:556`、`:582`、`:654`；
  其中 `:193` 是 `logger.error`，`:229` 的註解逐字「**不靜默**：留下可搜尋的 warning。
  真正的阻斷由 `create_all()` 承擔」，其餘為 `logger.warning`。
  > `cloud-360/` 記的 `:204–209`／`:251–256`／`:321–326`／`:493–500`／`:519–526` **行號已全部位移**。

### 認證核心 〔C〕
- **來源**：`backend/services/auth.py`（112 行）`[承:cloud-360@2026-09-22]`，**本輪未複驗**。
- **職責**：密碼雜湊、JWT 簽發與解析、`get_current_user`（`:39`）、
  `get_user_from_token`（`record` 參數控制是否寫活動時間，`:80–83`）、
  `require_any_user`（`:108–112`，**11 個字串手寫 allowlist**）。

### RBAC 授權核心 〔B〕
- **來源**：`backend/services/rbac.py`（302 行）、`backend/services/rbac_seed_data.py`（317 行）
  `[承:cloud-360@2026-09-22]`；**本輪只以 Python import 兩個模組重算規模** `[跑]`。
- **職責** 〔C〕：`CANONICAL_ROLES`（`:23–35`，**角色清單正本**）、
  `ensure_role_permissions_seeded`（`:58–111`，`force=False` 時表非空即**整段 no-op**，`:63–65`）、
  `ensure_missing_role_permissions`（`:84–111`，**只 INSERT 缺失列**）、
  `require_story_action`（`:255–280`，先擋 `authorization_status != "approved"` 直接 403，`:262–267`）。
- **規模（本輪實算）** `[跑]`：`CANONICAL_ROLES` **11 個角色**；
  `DEFAULT_ROLE_PERMISSIONS` **308 列**（元組形狀，例：`('Project_Architect','A1',True,True,False)`）
  ＝ 11 角色 × 28 story id。`[跑:link1]` 測試輸出亦顯示每 session seed 308 列。
- **本 intent 注意**：新 story id **必須**走 `ensure_missing_role_permissions`，
  不可依賴 `force=False` 的種子（它在表非空時什麼也不做）。

### 帳號活動記錄 〔C〕
- **來源**：`backend/services/activity.py`（104 行）`[承:cloud-360@2026-09-22]`，**本輪未複驗**。
- **職責**：`record_activity` 以 **5 分鐘節流**（`:25`）更新 `users.last_activity_at`。
- **風險**：唯一呼叫點在 `auth.py:80–83` 的 `get_user_from_token(record=True)`；
  `collab_router` 的 WebSocket 路徑以 `record=False` 繞過它
  （但 brain demo 的 WS 用 `record=True`，見 `architecture.md` 約束三）。

### 提示防護 〔C〕
- **來源**：`backend/services/prompt_guard.py`（63 行）`[承:cloud-360@2026-09-22]`，**本輪未複驗**。
- **職責**：進 LLM 前的平台自我竄改預檢（Cloud-360 的 DB／系統值／API key／金鑰等）；
  命中則**不呼叫 LLM**，回固定訊息。呼叫端在 `agent_router.py:112–119`。
- **本 intent 注意**：**大腦的任何新 LLM 入口都應經過同一道預檢**，
  否則等於為既有防護開一個旁路。這是 `project.md` `## Mandated` 的既有條款。

### LangGraph Runtime 〔B〕
- **來源**：`backend/services/langgraph_runtime.py`（165 LOC `[算]`）。
  本輪只讀 `:1–25` `[讀:link1]`；其餘 〔C〕。
- **職責**：建立 `langchain_openai.ChatOpenAI` 指向 OpenRouter（`:71–98`，讀 `OPENROUTER_API_KEY`，
  `:61–68`）；提供 `invoke_graph` 與 **`astream_graph`（`:133–149`）**。
- **常數** `[讀:link1]`：`:16` `DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"`、
  `:17` `DEFAULT_OPENROUTER_MODEL = "google/gemini-3.7-flash"`、`:18` `DEFAULT_TIMEOUT_SECONDS = 60.0`；
  `:23` `class RuntimeAuthError(Exception)`，docstring 註明「domain error, not HTTP」。
- **關鍵事實** 〔C〕：`astream_graph` **零消費者**（grep 僅命中定義檔與 `test_langgraph_runtime.py`）。
  **「既有 runtime 不能串流」是錯的**。
- **兩份物化**：預設模型名稱與 base URL 皆與 `llm_provider.py` 各有一份，無測試鎖住一致
  （`architecture.md` 約束九）。

### A1 產圖 Router 〔B〕
- **來源**：`backend/services/agent_router.py`（186 LOC）。本輪只讀 `:115–135` `[讀:link1]`；其餘 〔C〕。
- **職責** 〔C〕：`POST /api/architecture/generate`（SSE，`:129`）、
  `POST /generate-wa-collab`（SSE，`:186`）、另一個 SSE 在 `:97`；
  檔頭 `:10–17` 有「契約（前端依賴，請勿變更）」段，是本 repo docstring 深度的樣板。
- **本輪實讀** `[讀:link1]`：`:121` `_ensure_llm_keys()`、
  `:125` `async for event in run_design_agent(payload, request.current_xml, thread_id=f"user-{current_user.id}-design")`、
  `:129` `StreamingResponse(..., media_type="text/event-stream")`。
- **`:74`** 呼叫 `configure_provider_env()`（**每個 A1／A3 請求一次**）〔C〕。

### 使用者與權限 Router 〔B〕
- **來源**：`backend/services/user_router.py`（**892 LOC** `[算]`）。本輪只讀 `:80–92` `[讀:link1]`。
- **無 service 層**，商業邏輯直寫 handler；承載 `/api/auth` 的 16 個 operation。
- **本輪實讀的那一段** `[讀:link1]` `:80–92`：一個 `story_id → 中文顯示名`的字典，
  含 **`:85` `"H3": "MCP／Skill 生命週期"`**（鄰居 `"G1"`／`"H1"`／`"H2"`／`"J3a"`），
  緊接 `:89` `CATALOG_EXCLUDED_STORIES = frozenset({"J1"})`。
  **這是全 `backend/` 唯一的 `mcp` 命中，是 RBAC story 標籤、不是實作**
  （`architecture.md` 約束十二）。
- `team.md` 記 831 LOC，`cloud-360/` 記 892——**HEAD 是 892** `[算]`。

### 共編 Router 與 WebSocket 〔C〕
- **來源**：`backend/services/collab_router.py`（**593 LOC** `[算]` 本輪複驗）。
  **WS 區段 L245–300 為 `cloud-360@2026-09-22` 實讀** `[承:cloud-360@2026-09-22]`，本輪只複驗
  `:266` 的 `@router.websocket("/ws/{workspace_id}")` `[跑]`。
- **無 service 層。** `websocket_endpoint`（`:266–295`）不用 `Depends`、自建 `SessionLocal()`、
  從 query string 取 token、經 `_authorize_ws_user`（`:254–262`）呼叫
  `get_user_from_token(..., record=False)`（`:257`）；
  `ConnectionManager.active_connections: Dict[str, List[WebSocket]]`（`:58–59`）為行程內字典。
- `team.md` 記 527 LOC——**HEAD 是 593** `[算]`。

### WA 評核與 Lens 引擎群 〔C／B〕
- `review_router.py`（**484 LOC** `[算]` 本輪複驗；SSE 在 `:73` 與 `:484`）、
  `review_orchestrator.py`（510）、`wa_collab_orchestrator.py`（563）、
  `wa_score_service.py`（104）、`wa_rule_engine.py`（**973**，純函式、PBT 落點）、
  `wa_lens_engine.py`（**631**，純函式）、`lens_router.py`（108）、`lens_service.py`（203）、
  `collab_suggestions.py`（147）、`llm_limits.py`（64）。LOC 皆本輪 `[算]` `wc -l`。
- **`review_agent.py`（205 LOC）的框架已改** 〔A〕 `[讀]` `:1–12`：docstring 逐字
  **「A3 Review Agent（LangGraph + OpenRouter）」**，「串流：model／graph messages stream →
  SSE `suggestion_delta`」，imports 為 `from services.llm_provider import ...`。
  > **這推翻 `cloud/` store 的「Review／Lens＝Claude Agent SDK」**（`architecture.md` 約束九）。
- **`wa_collab_orchestrator.py:79`** 呼叫 `run_design_agent(messages, current_xml)`
  **未傳 `thread_id`** `[讀:link1]` → 落回預設 `"default-thread"`，
  即 **A4 共編路徑的所有使用者共用同一個 LangGraph checkpointer thread**。〔A〕
- `:70` `_remap_design_events` 把 design 事件改名 `[讀:link1]`。

### 設計圖建構 〔C〕
- `backend/services/diagram_builder.py`——**2,080 LOC** `[算]` 本輪複驗，**repo 最大單檔**。
  mxGraph XML 產生，純函式層、PBT 落點。
  > `cloud-360/` 記 1,818 行 `[承:cloud-360@2026-09-22]`——**HEAD 是 2,080**。
- 連線不得與元件 icon 重疊時，優先在此以 exit／entry 連接點與 waypoint 修正，
  不只靠前端 post-process（`project.md` `## Code Style` 的既有規則）。

### 後端環境載入 〔C〕
`backend/env_bootstrap.py`（36 LOC）：強制由 `backend/.env` 載入環境而非行程 cwd；
`main.py` 與 `database.py` 都經它 `[承:cloud-360@2026-09-22]`。

### C1 估價 HTTP 入口 〔C〕
- **來源**：`backend/cost/estimate_intake_router.py`（235 LOC `[算]`）`[承:cloud-360@2026-09-22]`
- **職責**：`/api/cost/v1` 的 operation（清單與授權逐列見 `api-documentation.md`）。
- **關鍵事實**：授權**全部**由 `Depends(require_story_action("C1", ...))` 承擔，
  service 層無第二道角色檢查（`architecture.md` 約束十一）。

### C1 建議 SSE Router 〔B〕
- **來源**：`backend/cost/advice_stream_router.py`（179 LOC `[算]`）。
  本輪只讀 `:5–9`、`:83`、`:173` `[讀]`；其餘 〔C〕。
- **職責** 〔C〕：`GET /sets/{set_id}/advice/stream`（`:161–179`，本輪複驗
  `:173` `media_type="text/event-stream"` `[讀]`）；`_event_stream`（`:81–158`）為 1 秒輪詢迴圈，
  事件型別僅 `progress`／`completed`／`failed`／`timeout`／`heartbeat`（`HEARTBEAT_SECONDS = 8.0`，`:25`）。
- **缺陷（本輪複驗仍在）** 〔A〕 `[讀]`：`:83` 寫 `last_progress_key: tuple[Any, ...] | None = None`
  但 `:9` 只 `from typing import AsyncIterator`——**`Any` 未 import**。
  目前不炸是因為 `:3` 有 `from __future__ import annotations`。
  **移除那行 future import 即為 `NameError`**，而 backend 沒有任何 type checker 會提前發現。

### C1 建議 Job 編排器 〔B〕
- **來源**：`backend/cost/advice_orchestrator.py`（**358 LOC** `[算]`）。
  **本輪只深讀 `:1–82`** `[讀:link1]`；`:83–358` 未讀。
- **本輪實讀的部分（這是最有用的一半）** `[讀:link1]`：
  `:7` `import threading`、`:21` `_executor: ThreadPoolExecutor | None`（`_MAX_WORKERS = 2`）、
  `:22` `_executor_lock = threading.Lock()`、
  **`:23` `_progress: dict[int, dict[str, Any]] = {}`（以 `set_id` 為鍵的字典，不是單槽）**、
  `:24` `_progress_lock = threading.Lock()`、`:26` `_inflight: set[int]`、
  `:61–72` `set_progress(set_id, **fields)`（鎖內讀改寫）、
  `:75–77` `get_progress(set_id)`（鎖內**回傳副本**）、
  `:80–82` `clear_progress(set_id)`（鎖內 `pop`）。
- **這是 `design_agent._progress_queue` 缺陷的 in-repo 正解**：
  **per-job 鍵 ＋ 鎖保護 ＋ 三個封裝好的存取函式（寫／讀／清），讀取回傳副本。**
  `_progress` 在整個檔內只被那三個函式碰到（`[算]` 14 處命中中，除宣告與三個函式本體外，
  其餘 9 處都是 `set_progress(...)` 呼叫）。
- 其餘 〔C〕：`reclaim_stale_generating`、結果寫回 `advice` 表（`:270–283`）、
  `TIMEOUT = timedelta(minutes=5)`（`:19`）。
- **`_inflight` 的鎖本輪未確認** `[未掃]`。

### C1 建議 Agent 〔C〕
- **來源**：`backend/cost/cost_advice_agent.py`（240 LOC `[算]`）`[承:cloud-360@2026-09-22]`
- **職責**：LangGraph 圖定義與執行；`:132–162` 建立 `ChatOpenAI`；
  `:156` 為 `invoke_graph(compiled, {...})`——**同步 `invoke`，不是 `astream`**。
- **本 intent 注意**：這是 repo 內「LangGraph 圖 ＋ SSE 對外」的既有可運行前例。

### C1 估價解析與存取層 〔B〕
`estimate_intake_service`（**686 LOC**，最大的 cost 模組）、
**純函式三支**：`estimate_parser`（322）、`estimate_readers`（384）、`estimate_validator`（122）
——`[跑:link1]` `validate_cost_calculator_boundary.py` 確認這三支無禁止的 I/O import；
另 `estimate_access`（58，`can_view_set` 在 `:29`，row-level 可見性）、
`estimate_audit`（74）、`config`（41）。LOC 皆 `[算]`。
**`sku_catalog.py`（265）的 `:18` `import httpx` 不違反邊界**，因為它不在那三支之內。

### C1 計價 Port 〔C〕
`pricing_client`（287，磁碟快取寫進 `backend/cost/.pricing_offer_cache/`，`:29`）、
`pricing_sdk`（203，AWS Price List Query／boto3；ADR-0018 由「確定刪除」改為保留）、
`pricing_gcp`（236）、`pricing_azure`（219，Azure Retail Prices）、
`pricing_offer_parser`（83）、`pricing_query_parser`（120）、`pricing_units`（47）、
`workload_context`（106），＋4 支 YAML 設定（`aws_region_locations`／`pricing_coverage`／
`pricing_urls`／`supported_regions`）。LOC 皆 `[算]`。

### 前端應用殼與路由 〔B〕
- **來源**：`frontend/src/App.tsx`（160 LOC `[跑]`）。**本輪只讀路由表** `[讀:link1]`。
- **13 條路由**（本輪複驗行號）：`/login`（`:36`）、`/403`（`:37`）、
  `/waiting-approval`（`:39`）、`/workspace`（`:48`）、`/assessment`（`:61`）、`/cost`（`:74`）、
  **`/brain`（`:88`，新增）**、`/admin/users`（`:99`）、
  `/admin/authorization-requests`（`:112`）、`/admin/role-permissions`（`:125`）、
  `/admin`（`:137`，redirect → `/admin/users`）、`/`（`:139`）、`*`（`:147`）。
  > `cloud-360/` 記「11 條路由」`[承:cloud-360@2026-09-22]`——**HEAD 是 13**（含 `/brain`）。
- `RouteGuard` 包裹 ＋ `Layout` 〔C〕。

### 前端 API URL 組裝 〔C〕
- **來源**：`frontend/src/config/api.ts` `[承:cloud-360@2026-09-22]`
- **職責**：`apiUrl()` 與 `wsUrl()`。本輪實算 `[算]`：前端 `fetch(` **62 處／15 支檔**、
  手寫 `Authorization: Bearer` **36 處**（`team.md` 的「52 處／10 支」已過時）。
- **本 intent 注意**：大腦的 WebSocket 客戶端應沿用 `wsUrl()`，不要新造一套 URL 組裝。

### 前端認證 Context 〔C〕
`frontend/src/context/AuthContext.tsx`（Provider 元件）＋ `auth-context.ts`（型別與 hook）
——拆兩檔是 `react-refresh/only-export-components` 的直接後果 `[承:cloud-360@2026-09-22]`。

### 前端成本插槽註冊 〔C〕
`frontend/src/cost/slotRegistry.tsx` `[承:cloud-360@2026-09-22]`：成本頁的插槽註冊表。
**本 intent 注意**：這是 repo 內既有的「頁面內可擴充插槽」形狀，
大腦若要在既有頁面嵌入入口，這是可參考的先例。

### 前端頁面群 〔B〕
**10 支 `*Page.tsx`**，LOC 皆本輪 `[算]`：`AssessmentPage` **1,861**、`WorkspacePage` **1,194**、
`RolePermissionsPage` 499、`AdminPage` 426、**`BrainPage` 403（新增）**、`CostPage` 344、
`LoginPage` 292、`AuthorizationRequestsPage` 202、`WaitingApprovalPage` 120、`ForbiddenPage` 35。
合計 5,376 行。**本輪未讀任何一支的內容。**
> `cloud-360/` 記「9 支」`[承:cloud-360@2026-09-22]`——**HEAD 是 10**。

### 前端元件群 〔B〕
`frontend/src/components/` **12 支** `[算]`：`ChatBox`、`DiagramPreviewPanel`、`DrawioCanvas`、
`LastActivityCell`、`Layout`、`LensCriteriaEditor`、`NavChromeContext`、`PaginationControl`、
`RouteGuard`、`ShareModal`、`Sidebar`、`SuggestionRichText`。
`components/cost/` **12 支** `[算]`：`EstimateAdvicePanel`、`EstimateCalculatorGuideModal`、
`EstimateChecksPanel`、`EstimateCloudCard`、`EstimateHistoryDrawer`、
`EstimateOfficialCalculators`、`EstimateSaveModal`、`EstimateShareModal`、
`EstimateUploadZone`、`EstimateWorkloadForm`、`types.ts`、`workloadContext.ts`。
> `cloud-360/` 記 `components/cost/` 「9 支（8 支 `Estimate*.tsx` ＋ `types.ts`）」——**HEAD 是 12**。
**本輪未讀任何一支的內容。**

### 前端 hooks／utils／型別 〔B〕
`hooks/useCollaboration.ts`（既有唯一 WS 客戶端，`[未掃]`）、`utils/` 6 支、`lib/` 1 支、
`cost/` 2 支、`config/` 1 支、`context/` 2 支。
**`types/` 2 支且兩者皆為產生檔** `[算]`：`api.d.ts`（由 `openapi.json` 經 `gen:types` 產生）
與 **`ws-contract.d.ts`（由 `ws-contract.json` 經 `gen:ws-types` 產生，新增）**。

### 前端交付鏈 〔B〕
`frontend/package.json`（**本輪由 link 1 全檔 `[讀]`**，但本元件另需 `Dockerfile`／`nginx.conf`
故整體仍為淺掃）：`npm run build` = `tsc -b && vite build`；8 支 `scripts`
（`dev`／`build`／`lint`／`preview`／`test:e2e`／`gen:types`／`check:types`／`gen:ws-types`／`check:ws-types`
——實為 9 支，含兩組型別產生／檢查對）。
〔C〕：`VITE_API_BASE_URL` 為**建置期** build arg（`Dockerfile:12–15`）；
nginx `location /api/` 為唯一帶 `Upgrade`／`Connection $connection_upgrade` 的位置
（`nginx.conf:16–32`），`$connection_upgrade` 的 `map` 由 `Dockerfile:21–23` 以 `printf` 寫入。

### 部署堆疊 〔B〕
- **來源**：`deploy/docker-compose.deploy.yml`（384 行；本輪以程式解析區塊結構 ＋ 讀 image 行
  與 redis 註解 `[讀]`／`[跑]`）、`deploy/render-env.sh`、`deploy/.env.example`、
  `deploy/docker-compose.test.yml`、`deploy/cloudflared/config.yml`、`docker-compose.yml`。
- **6 個 service（本輪實算，兩份 store 皆記 4）** `[跑]`：
  `db`（`:35`，`pgvector/pgvector:pg18`）、`backend`（`:79`）、`redis`（`:157`，`redis:8-alpine`）、
  `ollama`（`:270`，`ollama/ollama:latest`）、`frontend`（`:311`）、
  `cloudflared`（`:333`，`cloudflare/cloudflared:latest`，**未釘選**）。
  **2 個 network**：`edge`（`:376`）、`internal`（`:377`）。
  **3 個 volume**：`db_pg18`（`:382`）、`redis_aof`（`:383`）、`ollama_models`（`:384`）。
- 〔C〕：`schema_rbac.sql` 以 `:ro` 掛進 postgres 的 initdb 目錄（**僅在空 volume 上執行**，
  註解逐字寫在 `:21–22`）；`render-env.sh` 為部署設定的**唯一產生點**
  （heredoc 在 `:73–98`，`:59–69` 拒絕含 `$` 的憑證值）；
  `docker-compose.yml`（repo 根）僅 db ＋ adminer，本機用。
- 本輪 `[讀]`：`render-env.sh:121` `REDIS_URL=redis://redis:6379/0`；
  compose 檔頭 `:4` 註解逐字「Only nginx is reachable from outside. backend, db, redis and ollama
  have no ...」；`redis` 服務的註解說明 `maxmemory`／policy 刻意留在 compose 的 CLI 旗標
  而非掛載的 `redis.conf`，以及 healthcheck 為何需要 `@connection` 而非只 `+ping`。

### CI 管線 〔B〕
- **來源**：`.github/workflows/ci.yml`。本輪只讀 **5 個 job 標題行 ＋ 14 條 `run:` 步驟** `[算]`；
  每個 step 的實作本體未讀。
- **5 個 job** `[算]`：`gate`（`:55`）、`repo-contract`（`:141`）、`frontend`（`:169`）、
  `backend`（`:233`）、`docker-build`（`:299`）。
- 逐步驟與完整閘門清單見 `code-quality-assessment.md`。

### 測試套件 〔B〕
- `backend/tests/`：**46 支 `test_*.py`** ＋ `helpers.py` ＋ `__init__.py`
  （目錄內 `.py` 共 48 支）`[跑]`。`frontend/tests/e2e/` **2 支 spec** `[算]`。
- `[跑:link1]` `python3 -m unittest discover -s tests` → **Ran 419 tests ... OK**（28.557s）。
- `[跑]` `@given` **48 處／16 支檔**；`TestClient` **6 支測試檔 ＋ `helpers.py`**。
- **`helpers.py:1–25` 為本輪實讀** `[讀]`：驅動樁已由無條件 stub `psycopg2` 改為
  **條件式** stub `psycopg`（v3，含 `__version__ = "3.2.0"` 以通過 dialect 的版號 `re.match`），
  仍走 in-memory SQLite。**`team.md` 逐字記載的舊 mock 已過時。**
- **其餘 45 支測試檔的內容本輪未讀** 〔E〕。

### repo 層腳本 〔B〕
`scripts/` **10 支 `.py`** `[跑]`：4 支 CI validator（`validate_repo_contract`、
`validate_env_contract`、`validate_cost_calculator_boundary`、`validate_pricing_lookup_boundary`）、
2 支 TCMS（`tcms_validate`、`tcms_sync`）、3 支 aidlc-sync（`aidlc_sync_buglist`／`_pull`／`_push`）、
1 支 LangGraph smoke（`smoke_langgraph_openrouter.py`）。
`backend/scripts/` **3 支** `[跑]`：`dump_openapi.py`、**`dump_ws_contract.py`（新增）**、
**`run_hierarchy_migration.py`（新增）**。

### 資料庫可攜 schema 〔B〕
`schema_rbac.sql`（>770 行）：本輪 `[跑]` 複驗 **20 處 `CREATE TABLE IF NOT EXISTS`**，
含 `archive_*` 四表（`:191`／`:198`／`:208`／`:217`）、estimate 六表（`:240`–`:306`）、
**階層三表（`:327` `projects`、`:349` `systems`、`:393` `diagram_change_records`）**、
`role_permissions`（`:426`）；**裸的 `DELETE FROM role_permissions;` 在 `:443`**；
`projects.owner_user_id` 在 **`:330`**（`INTEGER NOT NULL REFERENCES users (id)`，**無 `ON DELETE`**）`[讀]`。
`user_diagrams.system_id` 相關在 `:11`／`:370`／`:373`／`:382`／`:388`／`:390`／`:772`–`:777` `[算]`。
`schema.sql` 〔E〕。
> `cloud-360/` 記 `DELETE FROM role_permissions` 在 L319、區塊標題在 L166–167
> `[承:cloud-360@2026-09-22]`——**行號已位移**（階層三表插入所致）。

### 部署工作流程與 gh-aw 〔E〕
`.github/workflows/deploy.yml`（兩輪皆只讀 job／step 骨架）；
**11 支 gh-aw agentic workflow**（`.md` ＋ 對應 `.lock.yml`），**全部 `engine: copilot`**
`[承:cloud-360@2026-09-22]`：`code-drift-alert`、`contract-guard`、`daily-digest`、
`deploy-doctor`、`issue-triage`、`lint-fix`、`local-dev-drift`、`pr-reviewer`、
`release-watch`、`spec-sync`、`ui-regression`。
**兩輪都未讀任何一支 gh-aw `.md` 的內容。**

### 資料資產 〔E〕
`backend/prompts/`（`.md` system prompts）、`backend/lenses/`（`.yaml` lens 定義）
——**兩輪皆未開啟**。

### 外部與基礎設施 〔B〕
PostgreSQL（**映像已升 `pgvector/pgvector:pg18`** 〔A〕）、**Redis 8**〔A，新增，應用零消費〕、
**Ollama**〔A，新增，應用零消費〕、OpenRouter（LLM，**唯一 provider**）〔A〕、
n8n webhook（架構圖 icons）〔C〕、draw.io／embed.diagrams.net（前端 iframe）〔C〕、
Cloudflare Tunnel（staging 對外）〔C〕、Kiwi TCMS（測案管理）〔C〕。
> **`claude` CLI 已不再是外部依賴**〔A〕——`backend/Dockerfile` 已移除 Node 與該 CLI。

---

## 本 intent 的元件缺口（哪些該有而沒有）

| 能力 | 已存在的 | **還沒有的** | 等級 |
|---|---|---|---|
| 大腦 WS gateway | demo-scope 的 `brain_router.py`（455 LOC，整支待取代） | `U13` 的正式實作 | A |
| WS 訊息契約 | `brain_ws_contract.py` ＋ 兩道 CI 閘門 | 契約未涵蓋 `collab` WS | A |
| Session 持久化 | Redis 服務、`REDIS_URL`、env 契約、`LOCAL-DEV.md` | **`redis` Python 套件、任何客戶端程式** | A |
| 向量記憶 | pgvector 擴充（`_ensure_vector_extension`）、Ollama 服務、`OLLAMA_EMBED_MODEL` | **任何 `vector` 欄位、embedding 客戶端** | A |
| 專案／系統階層 | 三張表、一次性遷移、終檢、`DEPLOY.md` | **ORM model、router、service** | A |
| 意圖路由 | demo 的 `_classify` 關鍵詞計分 | **信心值模型**（`OQ-10` 在質疑的正是這一點） | A |
| MCP server／client | **零** | **套件、server、client、跨進程通道**（`MCP` 這個字已被 story `H3` 佔用） | A |
| `diagram_change_records` 的 90 天清除 | 表、索引、`created_at` | **清除機制**（`DEPLOY.md:310` 逐字承認未落地） | A |
