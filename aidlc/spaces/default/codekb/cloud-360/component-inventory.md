# Component Inventory — Cloud-360

> **基準**：`dc4b687`（2026-09-22）。證據標記慣例見 `business-overview.md` 檔頭。

## 清單讀法（重要）

本檔**依本輪的掃描深度分成兩區**，這是刻意的結構，不是排版：

- `## 深讀元件` 底下的每個 H3，本輪都**逐行讀過其全部來源檔**，其名稱會逐字出現在
  `reverse-engineering-timestamp.md` 的 `analyzed.components`，下一輪重掃的守門員
  以字面比對它們。
- `## 淺掃元件` 底下的每個 H3，本輪**只取簽章、計數或檔頭**，**不在** `analyzed.components` 內。
  個別段落若標 `[讀]`，表示那一句話的來源行是實讀的，但該元件**整體**仍屬淺掃。

**為什麼不把部分讀過的檔升格為深讀**：`collab_router.py` 的 WebSocket 區段（L245–300）
與 `review_router.py` 的 SSE 區段本輪確實實讀，但掃描範圍的表達粒度是「檔案或目錄」，
無法表達行區間。把整支檔宣告為深讀會讓下一輪誤以為整檔已驗證，故它們留在淺掃區，
實讀的那幾行以 `[讀]` 就地標註。

---

## 深讀元件

### App Bootstrap
- **來源**：`backend/main.py` `[讀]`
- **職責**：建立 FastAPI `app`、CORS 中介層、`startup` 事件（`configure_provider_env()` ＋ `init_db()`）、7 個 `include_router`。
- **依賴**：`env_bootstrap`、`llm_provider`、`database`、7 個 router 模組。
- **本 intent 注意**：新 router 必須在此處註冊並選定 prefix；WebSocket 的 prefix 受 nginx 限制須落在 `/api/` 之下。

### ORM 資料模型
- **來源**：`backend/models.py` `[讀]`
- **職責**：13 個 ORM 模型 ＋ 1 個 association table。
- **清單** `[讀]`：`User`(`users`)、`RoleAuthorizationRequest`、`UserDiagram`、`UserDiagramChat`、`ArchitectureReview`、`WaLens`、`RolePermission`、`EstimateSet`、`Estimate`、`EstimateLineItem`、`EstimateShare`、`EstimateAuditEvent`、`Advice`；association table `diagram_shares`（`:25–30`）。
- **本 intent 注意**：唯一的擁有關係是 `users → user_diagrams`（`:91–105`，`user_id` 為 **NOT NULL** FK）。`system_id` 與 `project_id` 在 backend＋frontend＋`schema_rbac.sql` 全樹命中 **0** `[算]`。要插入 `專案 → 系統 → 架構圖` 中介層時，`UserDiagram.user_id` 的 NOT NULL 必須明確決定是保留（雙寫）還是改指。

### 資料庫連線與啟動補丁
- **來源**：`backend/database.py` `[讀]`
- **職責**：`engine`／`SessionLocal`／`get_db`（`:31`）／`init_db()`；6 支 `_ensure_*` 補丁（`:74–83`）：`_ensure_a4_schema`、`_ensure_j5_schema`、`_ensure_a3_schema`、`_ensure_cost_schema`、`_ensure_estimate_intake_schema`、`_ensure_last_activity_schema`；預設 persona 種子（受 `_allow_insecure_default_personas()` 閘門控制）。
- **C1 退役機制** `[讀]` `:330–383`：`_ensure_cost_schema()` 啟動時把 `diagram_cost`／`diagram_cost_line`／`pricing_cache`／`cost_audit_event` **RENAME 成 `archive_*`**，新環境不再建立 live 表，本函式不做 DROP。
- **風險**：6 支補丁**全部**以 `except Exception as e: logger.warning(...)` 吞掉失敗 `[讀]` `:204–209`、`:251–256`、`:321–326`、`:493–500`、`:519–526`。

### 認證核心
- **來源**：`backend/services/auth.py` `[讀]`
- **職責**：密碼雜湊、JWT 簽發與解析、`get_current_user`（`:39`）、`get_user_from_token`（`record` 參數控制是否寫活動時間，`:80–83`）、`require_any_user`（`:108–112`，11 個字串手寫 allowlist）。

### RBAC 授權核心
- **來源**：`backend/services/rbac.py`、`backend/services/rbac_seed_data.py` `[讀]`
- **職責**：`CANONICAL_ROLES`（`:23–35`，11 角色，**角色清單正本**）、`ensure_role_permissions_seeded`（`:58–111`，`force=False` 時表非空即整段 no-op，`:63–65`）、`ensure_missing_role_permissions`（`:84–111`，只 INSERT 缺失列）、`require_story_action`（`:255–280`）。
- **矩陣規模** `[算]`：`DEFAULT_ROLE_PERMISSIONS` 共 **308 列**＝11 角色 × 28 story id；C1／C2／C3 各 11 列。
- **本 intent 注意**：新 story id 必須走 `ensure_missing_role_permissions`，不可依賴 `force=False` 的種子。

### 帳號活動記錄
- **來源**：`backend/services/activity.py` `[讀]`
- **職責**：`record_activity` 以 **5 分鐘節流**（`:25`）更新 `users.last_activity_at`。
- **風險**：唯一呼叫點在 `auth.py:80–83` 的 `get_user_from_token(record=True)`；WebSocket 路徑以 `record=False` 繞過它。

### 提示防護
- **來源**：`backend/services/prompt_guard.py` `[讀]`
- **職責**：進 LLM 前的平台自我竄改預檢（DB／系統值／API key／金鑰等）；命中則不呼叫 LLM。
- **本 intent 注意**：大腦的任何新 LLM 入口都應經過同一道預檢，否則等於為既有防護開一個旁路。

### LLM 供應商環境調教
- **來源**：`backend/services/llm_provider.py` `[讀]`
- **職責**：依 `LLM_PROVIDER` 準備 Agent SDK 的環境；檔頭 L1–37 說明兩種 provider 的非對稱互斥。
- **風險**：`configure_provider_env()` 會**改寫整個行程的環境變數**（`:126–142`），且在**每個** A1／A3 請求都被呼叫（`agent_router.py:74`）。預設模型名稱寫在 `:75`。

### LangGraph Runtime
- **來源**：`backend/services/langgraph_runtime.py` `[讀]`
- **職責**：建立 `langchain_openai.ChatOpenAI` 指向 OpenRouter（`:71–98`，讀 `OPENROUTER_API_KEY`，`:61–68`）；提供 `invoke_graph` 與 **`astream_graph`（`:133–149`）**。
- **關鍵事實** `[算]`：`astream_graph` **零消費者**（全樹 grep 僅命中定義檔與 `test_langgraph_runtime.py`）。**「既有 runtime 不能串流」是錯的**。預設模型名稱寫在 `:17`，與 `llm_provider.py:75` 為同一事實的兩份物化，無測試鎖住一致。

### A1 產圖 Router
- **來源**：`backend/services/agent_router.py` `[讀]`
- **職責**：`POST /api/architecture/generate`（SSE，`:129`）、`POST /generate-wa-collab`（SSE，`:186`）；檔頭 L10–17 有「契約（前端依賴，請勿變更）」段，是本 repo docstring 深度的樣板。
- **依賴**：`prompt_guard`、`design_agent`、`llm_provider`（`:74`）。

### C1 估價 HTTP 入口
- **來源**：`backend/cost/estimate_intake_router.py` `[讀]`
- **職責**：`/api/cost/v1` 的 9 個 operation（清單與授權逐列見 `api-documentation.md`）。
- **關鍵事實**：授權全部由 `Depends(require_story_action("C1", ...))` 承擔，service 層無第二道角色檢查。

### C1 建議 SSE Router
- **來源**：`backend/cost/advice_stream_router.py` `[讀]`
- **職責**：`GET /sets/{set_id}/advice/stream`（`:161–179`）；`_event_stream`（`:81–158`）為 1 秒輪詢迴圈，事件型別僅 `progress`／`completed`／`failed`／`timeout`／`heartbeat`（`HEARTBEAT_SECONDS = 8.0`，`:25`）。
- **缺陷** `[讀]`：`:83` 使用未 import 的 `Any`（`:9` 只 import `AsyncIterator`）。目前不炸是因為 `:3` 有 `from __future__ import annotations`。移除那行 future import 即為 `NameError`，而 backend 沒有任何 type checker 會提前發現。

### C1 建議 Job 編排器
- **來源**：`backend/cost/advice_orchestrator.py` `[讀]`
- **職責**：`_executor`（`ThreadPoolExecutor(max_workers=2)`）、`_progress`、`_inflight`（三者皆模組層全域，`:21–26`）、`get_progress()`（`:75–77`，只讀本行程記憶體）、`reclaim_stale_generating`、結果寫回 `advice` 表（`:270–283`）、`TIMEOUT = timedelta(minutes=5)`（`:19`）。

### C1 建議 Agent
- **來源**：`backend/cost/cost_advice_agent.py` `[讀]`
- **職責**：LangGraph 圖定義與執行；`:132–162` 建立 `ChatOpenAI`；`:156` 為 `invoke_graph(compiled, {...})`——**同步 `invoke`，不是 `astream`**。
- **本 intent 注意**：這是 repo 內「LangGraph 圖 ＋ SSE 對外」的既有可運行前例。

### 前端應用殼與路由
- **來源**：`frontend/src/App.tsx` `[讀]`
- **職責**：11 條 Route（`:35–135`）、`RouteGuard` 包裹、`Layout`。

### 前端 API URL 組裝
- **來源**：`frontend/src/config/api.ts` `[讀]`
- **職責**：`apiUrl()` 與 `wsUrl()`，全前端 62 處 `fetch(` 一致沿用 `[算]`。
- **本 intent 注意**：大腦的 WebSocket 客戶端應沿用 `wsUrl()`，不要新造一套 URL 組裝。

### 前端認證 Context
- **來源**：`frontend/src/context/AuthContext.tsx`、`frontend/src/context/auth-context.ts` `[讀]`
- **職責**：Provider 元件與型別／hook 分兩檔（`react-refresh/only-export-components` 的直接後果）。

### 前端成本插槽註冊
- **來源**：`frontend/src/cost/slotRegistry.tsx` `[讀]`
- **職責**：成本頁的插槽註冊表，成本頁各面板以此掛載。
- **本 intent 注意**：這是 repo 內既有的「頁面內可擴充插槽」形狀，大腦若要在既有頁面嵌入入口，這是可參考的先例。

### 後端容器映像
- **來源**：`backend/Dockerfile`、`backend/requirements.txt` `[讀]`
- **職責**：`python:3.12-slim` ＋ Node 22 ＋ `@anthropic-ai/claude-code` CLI（`:3–18`）；`CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]`（`:36`，**無 `--workers`**）。
- **依賴宣告**：17 項，其中 5 支精確釘選（見 `technology-stack.md`）。

### 前端交付鏈
- **來源**：`frontend/package.json`、`frontend/Dockerfile`、`frontend/nginx.conf` `[讀]`
- **職責**：`npm run build` = `tsc -b && vite build`；`VITE_API_BASE_URL` 為**建置期** build arg（`Dockerfile:12–15`）；nginx `location /api/` 為唯一帶 `Upgrade`／`Connection $connection_upgrade` 的位置（`nginx.conf:16–32`），`$connection_upgrade` 的 `map` 由 `Dockerfile:21–23` 以 `printf` 寫入。

### 部署堆疊
- **來源**：`deploy/docker-compose.deploy.yml`、`deploy/docker-compose.test.yml`、`deploy/render-env.sh`、`deploy/.env.example`、`deploy/cloudflared/config.yml`、`docker-compose.yml` `[讀]`
- **職責**：staging 4 服務（`db`／`backend`／`frontend`／`cloudflared`，`:11–93`）；`schema_rbac.sql` 以 `:ro` 掛進 postgres 的 initdb 目錄（`:23`，**僅在空 volume 上執行**，註解逐字寫在 `:21–22`）；`render-env.sh` 為部署設定的**唯一產生點**（heredoc 在 `:73–98`，`:59–69` 拒絕含 `$` 的憑證值）；`docker-compose.yml`（repo 根）僅 db ＋ adminer，本機用。

### CI 管線
- **來源**：`.github/workflows/ci.yml` `[讀]`
- **職責**：5 個 job —— `gate`（偵測 `[aidlc-sync]` 回寫，命中則 skip 其餘四者）→ `repo-contract`、`frontend`、`backend`、`docker-build`（四者平行、皆 `needs: gate`）。逐步驟見 `code-quality-assessment.md`。

### OpenAPI 契約
- **來源**：`openapi.json` `[算]`（以程式解析全部 path／operation／schema，非逐行閱讀）
- **職責**：42 path／55 operation／32 schema，是前後端型別契約的單一真實來源；由 `backend/scripts/dump_openapi.py` 產生、`frontend/src/types/api.d.ts`（2,823 行）由它衍生。
- **缺口**：**不涵蓋 WebSocket**（FastAPI 不登錄 websocket route）。

---

## 淺掃元件

> 以下元件本輪**僅取簽章、計數或檔頭**，不在 `analyzed.components` 內。引用其內部行為前請自行複驗。

### 後端環境載入（`backend/env_bootstrap.py`）
強制由 `backend/.env` 載入環境而非行程 cwd；`main.py` 與 `database.py` 都經它 `[簽]`。

### 使用者與權限 Router（`backend/services/user_router.py`）
**892 行** `[算]`，無 service 層，商業邏輯直寫 handler；承載 `/api/auth` 的 16 個 operation。

### 共編 Router 與 WebSocket（`backend/services/collab_router.py`）
**593 行** `[算]`，無 service 層。**WS 區段 L245–300 為本輪實讀** `[讀]`：
`websocket_endpoint`（`:266–295`）不用 `Depends`、自建 `SessionLocal()`、從 query string 取 token、
經 `_authorize_ws_user`（`:254–262`）呼叫 `get_user_from_token(..., record=False)`（`:257`）；
`ConnectionManager.active_connections`（`:58–59`）為行程內字典。其餘 HTTP handler 僅 `[簽]`。

### WA 評核與 Lens 引擎群
`review_router`（SSE 區段 L55–115／L460–484 為 `[讀]`，其餘 `[簽]`）、`review_agent`、
`review_orchestrator`、`wa_collab_orchestrator`、`wa_score_service`、`wa_rule_engine`、
`wa_lens_engine`、`lens_router`、`lens_service`、`collab_suggestions`、`llm_limits`。

### 設計 Agent 與圖建構
`design_agent.py`（檔頭 L1–45 `[讀]`，以子行程驅動 `claude` CLI）、
`diagram_builder.py`（**1,818 行**，repo 最大單檔 `[算]`）。

### C1 估價解析與存取層
`estimate_intake_service`、`estimate_parser`、`estimate_readers`、`estimate_validator`、
`estimate_access`（`can_view_set` 在 `:29` `[簽]`）、`estimate_audit`、`config`。

### C1 計價 Port
`pricing_client`（檔頭 L1–120 `[讀]`：磁碟快取寫進 `backend/cost/.pricing_offer_cache/`，`:29`）、
`pricing_sdk`、`pricing_gcp`、`pricing_azure`、`pricing_offer_parser`、`pricing_query_parser`、
`pricing_units`，＋4 支 YAML 設定。

### 前端頁面群
9 支 `*Page.tsx` `[算]`：`AdminPage`、`AssessmentPage`（**1,861 行**）、
`AuthorizationRequestsPage`、`CostPage`（前 80 行 `[讀]`）、`ForbiddenPage`、`LoginPage`、
`RolePermissionsPage`、`WaitingApprovalPage`、`WorkspacePage`。

### 前端元件群
`frontend/src/components/` 12 支（`Sidebar.tsx` 前 140 行 `[讀]`、`Layout`、`RouteGuard`、
`ChatBox`、`DrawioCanvas`、`DiagramPreviewPanel`、`LastActivityCell`、`LensCriteriaEditor`、
`NavChromeContext`、`PaginationControl`、`ShareModal`、`SuggestionRichText`）
＋ `components/cost/` 9 支（8 支 `Estimate*.tsx` ＋ `types.ts`）`[算]`。

### 前端 hooks／utils／型別
`hooks/useCollaboration.ts`（既有唯一 WS 客戶端）、`utils/` 6 支、
`cost/supportedRegions.ts`、`types/api.d.ts`（2,823 行，自動產生）`[算]`。

### 測試套件
`backend/tests/` **37 支 `test_*.py`** ＋ `helpers.py` ＋ `fixtures/`；
`frontend/tests/e2e/` **2 支 spec**（`regression.spec.ts` 490 行、`estimate-workspace.spec.ts` 57 行）`[算]`。
**本輪未讀任何一支測試檔的內容。**

### repo 層腳本
`scripts/` 10 支 `.py` `[算]`：4 支 CI validator（`validate_repo_contract`、`validate_env_contract`、
`validate_cost_calculator_boundary`、`validate_pricing_lookup_boundary`——後兩支的檔頭 `[讀]`）、
2 支 TCMS（`tcms_validate`、`tcms_sync`）、3 支 aidlc-sync、1 支 LangGraph smoke
（`smoke_langgraph_openrouter.py`）。

### 資料庫可攜 schema
`schema_rbac.sql`（檔頭 L1–29、cost／estimate／RBAC 區塊 L160–330 `[讀]`；308 列 seed 的
逐列 INSERT 未逐行讀）、`schema.sql` `[簽]`。

### 部署工作流程與 gh-aw
`.github/workflows/deploy.yml`（僅讀 job／step 骨架 `[未驗]`）；
**11 支 gh-aw agentic workflow**（`.md` ＋ 對應 `.lock.yml`），**全部 `engine: copilot`** `[算]`：
`code-drift-alert`、`contract-guard`、`daily-digest`、`deploy-doctor`、`issue-triage`、
`lint-fix`、`local-dev-drift`、`pr-reviewer`、`release-watch`、`spec-sync`、`ui-regression`。
**本輪未讀任何一支 gh-aw `.md` 的內容。**

### 資料資產
`backend/prompts/`、`backend/lenses/`——**本輪未開啟** `[未驗]`。
