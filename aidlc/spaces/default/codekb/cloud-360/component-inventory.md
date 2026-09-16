# Component Inventory — Cloud-360

> 逆向工程產出。**基準 commit `9307dbc`（2026-08-23）**；前一基準為 `c3de2c8`（2026-08-17）。
> **本輪為兩區定向掃描 ＋ 差異標註，不是完整重掃**。節標題後的新鮮度標記：
> **［本輪重寫］**｜**［本輪機械複驗］**｜**［差異標註］**｜**［沿用 `c3de2c8`］**。
> 讀法與跨分支限制見 `reverse-engineering-timestamp.md`。
>
> **用詞提醒**：在標記為［沿用 `c3de2c8`］或［差異標註］的段落內，「本輪／本次」指的是
> **`c3de2c8` 那一輪掃描**；在［本輪重寫］／［本輪機械複驗］段落內，以及任何加 **★** 的
> 條目，指的才是本輪（`9307dbc`，2026-08-23）。
>
> 本檔是元件的完整清單與職責定義。架構關係見 `architecture.md`，檔案佈局見 `code-structure.md`。
>
> **LOC 與測試數若未特別標註，皆為 `c3de2c8` 的量測值，本輪未重新計算。**

## 清單讀法

- **LOC** 為本次實測行數（`git ls-files` + `wc -l`）。
- **上游** = 誰呼叫它；**下游** = 它呼叫誰。
- **測試** 欄標示是否有直接對應的測試檔，括號內為該測試檔的 LOC 與 test 數。
  **test 數為 `grep -c "def test_"` 的靜態計數，本次未執行測試套件**（掃描環境缺
  `fastapi`／`hypothesis`）—— 不得解讀為「N 個測試通過」。
- 「純函式」意指不讀資料庫、不做網路 I/O，可在無環境下直接測試。

## Backend 元件 ［差異標註］

### 應用骨架

| 元件 | LOC | 職責 | 上游 | 下游 | 測試 |
|---|---|---|---|---|---|
| `main.py` | 55 | 建立 `FastAPI` app；CORS middleware（來源由 `CORS_ORIGINS` 注入）；掛 5 個 router；startup 事件呼叫 `init_db()` 與 LLM 環境設定。**無模組 docstring**。★ 本輪：`load_dotenv(override=True)` → `env_bootstrap.load_backend_dotenv(override=True)` | uvicorn | 5 router、`database`、`llm_provider`、**`env_bootstrap`** | 無（CI 有 import smoke） |
| **`env_bootstrap.py`** | **36** | **★ 本輪新增（全文已讀）。`backend/.env` 的唯一載入點**；路徑釘死 `Path(__file__).resolve().parent / ".env"`，取代 `load_dotenv()` 的 cwd 向上搜尋。`override` 預設 `False`；檔案不存在不是錯誤。docstring 完整記錄「摸到使用者家目錄 `.env`」的實際事故與「只修 `main.py` 無效」的原因 | `main.py`、`database.py` | `python-dotenv` | **`test_dotenv_path.py`(101)** |
| `models.py` | 175 | SQLAlchemy declarative Base；7 個實體模型 + 1 個 association table；`User.to_dict()`；relationship 定義 | 全部 service | — | 間接 |
| `database.py` | 366 | engine／`SessionLocal`／`get_db()` 依賴注入；`init_db()`（建表 + seed 帳號 + seed 矩陣）；**4 支 `_ensure_*_schema()` runtime DDL 補丁**加 `_apply_security_reviewer_j3a_view()`。**無模組 docstring**。★ 本輪新增 **`APP_ENV` 閘門三函式**：`_allow_insecure_default_users()`／`_allow_insecure_default_personas()`／`_bootstrap_admin_password()`——11 位 persona demo 帳號只在 `APP_ENV=local` 建立；固定密碼只在 local/test/ci 或 `ALLOW_INSECURE_DEFAULT_USERS` opt-in；否則需 `CLOUD360_BOOTSTRAP_ADMIN_PASSWORD`，未設則不建 admin 並記 log | `main.py`、全部 router | `models`、`rbac`、**`env_bootstrap`** | **`test_database_security.py`(65，本輪新增)** |
| `scripts/dump_openapi.py` | 90 | 由**程式碼**（非 live 端點）dump OpenAPI 規格至 repo 根 `openapi.json`；`--check` 供 CI 比對 | CI backend job | `main` | 無（本身即 gate） |

### HTTP 邊界層（Router，5 支）

| 元件 | LOC | 職責 | 下游 | HTTP 層測試 |
|---|---|---|---|---|
| `services/user_router.py` | 884（+24 未重量） | 登入／註冊／使用者清單與**分頁**／角色指派／啟停用／刪除／J5 授權申請／J3b 權限矩陣 CRUD。**商業邏輯直寫 handler，無 service 層**。★ 本輪三項變更：①`MeResponse` 補 `last_opened_diagram_id`（修 `spec-sync` #468 揭露的漂移）；②`UserSchema`／`AuthorizationRequestSchema` 由 pydantic v1 `class Config: orm_mode` 改為 v2 `model_config = ConfigDict(from_attributes=True)`；③`login()` 新增 `record_activity(db, user)` ＋ `db.refresh(user)` | `auth`、`rbac`、`activity`、`models` | **部分**：`test_user_list_endpoint.py`(282／17，本輪 +10) 涵蓋 3 個 operation；**`test_me_endpoint.py`(77，本輪新增)** 涵蓋 `GET /api/auth/me` |
| `services/collab_router.py` | 527（+76 未重量） | 架構圖 CRUD、分享 ACL、WebSocket 共編廣播（`ConnectionManager`）、A4 聊天持久化、workspace bootstrap。**商業邏輯直寫 handler**。★ 本輪新增 **`_authorize_ws_user()`**（`:255`）：WebSocket 由無認證改為必須帶 `?token=`，驗 token → 檢查 diagram 可存取 → 檢查 arch edit 權，失敗以 close code 1008／1003 斷線；另新增 payload 上限驗證（2 MB／必須含 `<mxgraphmodel>`／`<mxfile>`／聊天 100 則 × 8000 字）；`manager.disconnect` 移入 `finally` | `rbac`、`models`、**`auth.get_user_from_token`** | **無**（`test_collab.py`(184／12，本輪 +64) 涵蓋 service 層邏輯；**WebSocket 授權路徑本身無測試**——本輪 grep `websocket_connect` 無命中） |
| `services/review_router.py` | 484 | A3 評核 API（SSE + JSON）、上傳 XML、provider 偵測、PNG 轉檔 | `review_orchestrator`、`rbac` | **無**（`test_review_authz.py`(93／5) 涵蓋授權判定） |
| `services/agent_router.py` | 186 | A1 SSE 適配層：授權、`prompt_guard` 前置檢查、把 agent 事件轉 SSE、雙 agent 協作端點。**不直接呼叫 LLM**。docstring 含「契約（前端依賴，請勿變更）」段，為全 repo 樣板 | `prompt_guard`、`design_agent`、`wa_collab_orchestrator`、`rbac` | **無** |
| `services/lens_router.py` | 108 | A3 Offline Custom Lens 編輯 API（五個 operation 皆需 `A3.review`），支援 per-cloud provider | `lens_service`、`rbac` | **無** |

### 授權與驗證核心

| 元件 | LOC | 職責 | 上游 | 測試 |
|---|---|---|---|---|
| `services/rbac.py` | 272 | **全系統授權核心**。`CANONICAL_ROLES`(11)／`STORY_IDS`(動態導出 28)／`ROLE_ALIASES`；`user_can`／`user_can_arch`；guard 工廠 `require_story_action`／`require_arch_action`；`permissions_map_for_role`；`sync_arch_permission_flags`；`ensure_role_permissions_seeded`；`admin_may_decide_role`（BR-04） | 5 個 router 全部、`database` | `test_rbac.py`(56／6)、`test_j5_authz.py`(123／9)、`test_j3a_view_permission.py`(172／10) |
| `services/auth.py` | 91（+49 未重量） | bcrypt 雜湊與驗證；PyJWT 簽發／解碼（HS256，8 小時）；`RoleChecker` 角色 allowlist（**死碼**）。**無模組 docstring**。★ 本輪三項變更：①**`_resolve_secret_key()`**（`:22`）——`JWT_SECRET` 不再無條件 fallback，僅 `APP_ENV ∈ {local,test,ci}` 允許 `INSECURE_DEV_SECRET`，否則 `raise RuntimeError`；②`datetime.utcnow()` → `datetime.now(timezone.utc)`；③**抽出公開函式 `get_user_from_token(token, db, *, record=True)`**（`:58`），`get_current_user`（`:87`）成為其薄包裝 | `rbac`、`user_router`、**`collab_router`（以 `record=False` 呼叫）** | `test_auth.py`(124／10，本輪 +57，含 1 個 `@given`；本輪起使用 `TestClient` 覆蓋 `POST /api/auth/login`) |
| `services/rbac_seed_data.py` | 315 | 純資料常數 `DEFAULT_ROLE_PERMISSIONS`：**308 筆 tuple**（11 角色 × 28 story，本次以 `ast.literal_eval` 實測確認）。docstring 宣稱「由 `schema_rbac.sql` 產生（勿手改）」，**但產生腳本不存在於 repo** | `rbac` | 間接（`STORY_IDS` 由此導出） |

### LLM Agent、編排器與供應商層

| 元件 | LOC | 職責 | 下游 | 測試 |
|---|---|---|---|---|
| `services/wa_collab_orchestrator.py` | 551 | **A1↔A3 雙 agent 協作**。Design 與 Review 互相對話最多 2 輪，目標 lens 總分 ≥ `TARGET_SCORE`(80) 且無 `HIGH_RISK`；產生 `score` 與 `xml_preview` 事件 | `design_agent`、`review_agent`、`wa_score_service` | `test_wa_collab.py`(48／3) |
| `services/review_orchestrator.py` | 510 | **A3 評核狀態機**。狀態流轉（`pending`→`rules_complete`→`complete`／`rules_only`）；逾時控制（75s／90s）；`_archive_previous()`；SSE 事件序；`audit_log`；`get_accessible_diagram`／`review_to_dict`／`user_can_read_review` | `wa_rule_engine`、`wa_lens_engine`、`review_agent` | **狀態機主體無直接測試** |
| `services/design_agent.py` | 328 | **A1 Design Agent**。`claude-agent-sdk` → spawn Claude Code CLI 子行程；提供行程內 MCP tool `draw_architecture_diagram`（allowed_tools 唯一項）；**明確禁用 Bash／Read／Write／Edit** | `diagram_builder`、`llm_provider`、外部 CLI | `test_design_agent.py`(85／7)，含 2 個 `@given` |
| `services/llm_provider.py` | 223 | **本輪新增**。LLM 供應商切換：`openrouter`（部署預設）↔ `cli`（本機已登入的 claude CLI）；`llm_auth_ready()`。docstring 40+ 行，逐項解釋為何 `cli` 模式必須 **delete** 而非清空 6 個衝突環境變數 | 環境變數、外部 CLI | `test_llm_provider.py`(243／**25**，全 repo 最多) |
| `services/review_agent.py` | 174 | **A3 改善建議 agent**。不掛 MCP、壓縮 findings、串流 `suggestion_delta` | `llm_provider`、外部 CLI | `test_review_agent.py`(39／2) |

### 純函式引擎（可 PBT 的核心）

| 元件 | LOC | 職責 | 外部相依 | 測試 |
|---|---|---|---|---|
| `services/diagram_builder.py` | **1,818（全 repo 最大模組）** | groups／nodes／edges → draw.io `mxGraphModel` XML；版面正規化、icon 與邊線去擁擠、orthogonal edge。**唯一 I/O 是 `fetch_icon_from_n8n()`** | 選填 n8n webhook | `test_diagram_builder.py`(546／18，含 2 個 `@given`)、`test_diagram_builder_edges.py`(234／11)、`test_diagram_icons.py`(196／19，含 1 個 `@given`) |
| `services/wa_rule_engine.py` | 973 | 解析 draw.io mxGraph XML 的 `mxCell` value 與 style，產出 Well-Architected 支柱分數與 findings。**不連 AWS API、不讀 DB** | 無 | `test_wa_rule_engine.py`(150／9)，含 2 個 `@given` |
| `services/wa_lens_engine.py` | 556 | Offline Custom Lens loader 與 `riskRules` 評估。相容 AWS WA Custom Lens `schemaVersion 2021-11-01`。**不呼叫 AWS API** | 無 | `test_wa_lens_engine.py`(146／8) |
| `services/collab_suggestions.py` | 147 | 優化前後 findings 的差異摘要 | 無 | `test_collab_suggestions.py`(52／2) |
| `services/activity.py` | 104 | **本輪新增**。帳號最後活動時間政策：`ACTIVITY_WRITE_THROTTLE`(5 分)、`OVERDUE_THRESHOLD`(90 天)；純判定 `should_record_activity()`／`is_overdue()`／`as_aware_utc()`；薄寫入器 `record_activity()` | 僅 `record_activity` 碰 DB | `test_activity.py`(142／19)，含 **4 個 `@given`**（全 repo 最多） |
| `services/llm_limits.py` | 64 | Agent SDK token／context 上限常數（output 512–24,000，預設 12,000；XML context 預設 32,000 字元） | 無 | `test_llm_limits.py`(41／5) |
| `services/prompt_guard.py` | 63 | **本輪新增**。平台自我竄改預檢；命中即回固定 `REFUSAL_MESSAGE`，**不呼叫 LLM** | 無 | `test_prompt_guard.py`(71／9) |

### 服務模組

| 元件 | LOC | 職責 | 測試 |
|---|---|---|---|
| `services/lens_service.py` | 203 | Lens 讀寫與驗證；per-cloud active lens 管理（aws／gcp／azure） | `test_lens_service.py`(86／6) |
| `services/wa_score_service.py` | 104 | 對 XML 做 A3 同源的 lens 打分，**不強制寫入 review**；定義 `TARGET_SCORE` | **無** |

### 資料資產

| 資產 | 內容 | 用途 |
|---|---|---|
| `backend/lenses/cloud360-core-mvp-lens.json` | AWS lens 定義 | 無 DB 資料時的 fallback |
| `backend/lenses/cloud360-core-mvp-lens-gcp.json` | GCP lens 定義 | 同上 |
| `backend/lenses/cloud360-core-mvp-lens-azure.json` | Azure lens 定義 | 同上 |
| `backend/prompts/`（6 檔） | 3 個 system prompt（AWS／通用雲／WA review）+ 3 個 draw.io 模板 | Agent 的 prompt 與初始圖形 |

### ORM 模型（7 實體 + 1 association table）

| 模型／表 | 時間戳 | 備註 |
|---|---|---|
| `users` | **`last_activity_at`（本輪新增）** | 見下方專節 |
| `user_diagrams` | `updated_at` | 架構圖本體，含 `xml_data` |
| `diagram_shares` | 無 | 分享 ACL 關聯表（association table） |
| `user_diagram_chats` | `updated_at` | A4 聊天持久化 |
| `role_authorization_requests` | `created_at`／`updated_at`／`decided_at` | J5 授權申請 |
| `architecture_reviews` | `created_at`／`updated_at` | A3 評核結果；`status` 預設 `pending` |
| `wa_lenses` | `created_at`／`updated_at` | Lens 持久化 |
| `role_permissions` | `updated_at`（+`updated_by`） | 權限矩陣，`(role, story_id)` 複合主鍵 |

**時間戳慣例**：既有時間戳一律 `DateTime(timezone=True)` + `server_default=func.now()`
（`updated_at` 另加 `onupdate=func.now()`），SQL 側為 `TIMESTAMPTZ DEFAULT now()`。
**`last_activity_at` 是刻意的例外**（見下）。

#### `users` 表詳解（執行期權威為 ORM，`models.py`）

| 欄位 | 型別 | 約束 | 定義於 |
|---|---|---|---|
| `id` | Integer | PK, index | 三處一致 |
| `username` | String | unique, index, NOT NULL | 三處一致 |
| `password_hash` | String | NOT NULL | 三處一致 |
| `role` | String | **nullable=True**（J5 pending 時為 NULL） | ORM nullable；兩支 SQL 皆 `NOT NULL`，靠 `_ensure_j5_schema()` 的 `ALTER ... DROP NOT NULL` 拉齊 |
| `is_active` | Boolean | default True | 三處一致 |
| `authorization_status` | String(32) | NOT NULL, default `'approved'`；值域 `pending`／`approved`／`rejected` | **僅 ORM + `_ensure_j5_schema()`；兩支 SQL 皆無** |
| `last_opened_diagram_id` | Integer | FK → `user_diagrams.id` ON DELETE SET NULL, nullable | 三處皆有 |
| **`last_activity_at`** | **DateTime(timezone=True)** | **nullable=True，刻意無 `server_default`** | **ORM + `_ensure_last_activity_schema()` + `schema_rbac.sql`（三處已同步）** |

**`last_activity_at` 的三個設計決定**（皆有原始碼註解佐證，下游變更時不要無意間推翻）：

1. **任何以有效憑證發出的請求都更新它**，不是只有登入。記錄點在
   `auth.get_current_user` → `activity.record_activity`。
2. **同一帳號至多每 5 分鐘寫一次**（滑動視窗，基準為上次成功寫入時刻）。
   這是以精度換寫入量的刻意取捨。
3. **刻意不設 `server_default`**：有預設值會讓「從未活動」與「剛建立」無法區分。
   空值 = 從未活動；上線前的既有帳號皆為此態，**且不套用逾期標示**。

**與 J5 欄位的對比值得注意**：`last_activity_at` **有**落到 `schema_rbac.sql`（三處同步），
而 `authorization_status` 與 `role_authorization_requests` **沒有**。
這證明 `project.md` 的 blocking 同步規則實務上可行，J5 是歷史欠帳而非結構性做不到。

## Frontend 元件 ［差異標註］

### 頁面（8 支）

| 元件 | LOC | 職責 | 對應能力 |
|---|---|---|---|
| `AssessmentPage.tsx` | **1,861（全前端最大檔）** | A3 評核完整 UI：建立評核、SSE 接收、findings 展示、建議、優化流程、PDF 匯出。**含兩段不可達的 `unsupported` 分支**（:632、:1195） | `A3` |
| `WorkspacePage.tsx` | **1,193** | A1 工作區：聊天、畫布、圖清單、分享、共編 | `A1`／`A2`／`A4` |
| `RolePermissionsPage.tsx` | 427 | 11 × 28 權限矩陣編輯 UI | `J3b` |
| `AdminPage.tsx` | 426 | 使用者清單表格、角色指派、啟停用、刪除、**最後活動時間欄與分頁**。**全前端唯一使用產生型別的檔** | `J3a` |
| `LoginPage.tsx` | 289 | 登入與註冊（含角色功能目錄） | 公開 |
| `AuthorizationRequestsPage.tsx` | 202 | 授權申請審核 | `J3a` |
| `WaitingApprovalPage.tsx` | 120 | pending 使用者落點，可改申請角色 | 僅需登入 |
| `ForbiddenPage.tsx` | 35 | 403 落點 | 公開 |

### 元件（12 支）

| 元件 | LOC | 職責 |
|---|---|---|
| `LensCriteriaEditor.tsx` | 473 | Lens 準則編輯器（對應 `lens_router` 五個 operation） |
| `ChatBox.tsx` | 385 | A1／A4 對話介面，接收 SSE `message`／`progress` |
| `DrawioCanvas.tsx` | 343 | draw.io 畫布嵌入與 XML 載入 |
| `Sidebar.tsx` | 285 | 導覽；含 `can()` 能力判定決定顯示哪些入口。依 story 大類分層（A、J），故事層為第二層 |
| `SuggestionRichText.tsx` | 210 | 建議文字的富文本渲染 |
| `PaginationControl.tsx` | 138 | **本輪新增**。使用者清單分頁控制；切頁期間不消失、鍵盤可達 |
| `ShareModal.tsx` | 136 | 分享對話框 |
| `LastActivityCell.tsx` | 73 | **本輪新增**。最後活動時間顯示；空值顯示破折號，逾期加標示 |
| `NavChromeContext.tsx` | 68 | 導覽外框的 context |
| `RouteGuard.tsx` | 62 | `ProtectedRoute`（登入與否）與 `CapabilityRoute`（story × action） |
| `DiagramPreviewPanel.tsx` | 53 | 圖形預覽面板 |
| `Layout.tsx` | 21 | 頁面外框 |

### 狀態、型別與基礎設施

| 元件 | LOC | 職責 |
|---|---|---|
| **`types/api.d.ts`** | **2,385** | **由 `openapi.json` 產生（勿手改）**。受 `npm run check:types` gate 保護。**唯一消費者是 `AdminPage.tsx`** |
| `context/AuthContext.tsx` | 142（+42 未重量） | Auth Provider component。**必須與型別檔分開**（`react-refresh/only-export-components`）。★ 本輪：**token 由 `localStorage` 改存 `sessionStorage`**（`TOKEN_STORAGE_KEY`），並在登入／登出／初始化三處呼叫新增的 `clearLegacyAuthStorage()`，移除四個舊 `localStorage` key（`token`／`username`／`role`／`authorization_status`）。**語意變化**：關閉分頁即失去憑證、不再跨分頁共用 |
| `context/auth-context.ts` | 63 | 型別定義與 `useAuth` hook；持有 permissions map，供 `CapabilityRoute` 與 `Sidebar` 判定 |
| `config/api.ts` | 34 | `API_BASE_URL`／`WS_BASE_URL`／`apiUrl()`／`wsUrl()`；由 `VITE_API_BASE_URL` **build ARG** 注入 |
| `hooks/useCollaboration.ts` | 64 | WebSocket 共編連線（連 `/api/collab/ws/{workspaceId}`） |
| `utils/`（6 支，877 LOC） | — | `exportReviewPdf`(446)、`optimizeSuggestions`(180)、`exportDiagramPng`(105)、`parseChoiceOptions`(64)、`downloadDrawio`(45)、`diagramViewer`(37) |
| `lib/plainText.ts` | 20 | 純文字處理 |
| `scripts/check-api-types.mjs` | — | **型別漂移 gate**：重產型別到暫存檔並與 committed 逐位元比對。`GENERATOR` 常數是版本字串的第二份手寫副本 |

## 基礎設施與流程元件 ［部分本輪重寫］

### 容器與部署

| 元件 | 職責 |
|---|---|
| `backend/Dockerfile` | `python:3.12-slim` + **Node 22 + 全域 `@anthropic-ai/claude-code`**；非 root（uid 10001）；HEALTHCHECK 打 `/` |
| `frontend/Dockerfile` | 多階段：`node:22-alpine` build → `nginx:alpine`；`VITE_API_BASE_URL` 為 **build ARG**（執行期不可改） |
| `frontend/nginx.conf` | `/api/` → `backend:8000`（含 WS upgrade、**`proxy_buffering off`**、**600s timeout**）；SPA fallback |
| `deploy/docker-compose.deploy.yml` | staging stack：`db`(postgres:16-alpine) + `backend` + `frontend`(nginx) + `cloudflared`；**只有 nginx 對外**；掛 `../schema_rbac.sql` 為 initdb |
| `deploy/docker-compose.test.yml` | CI `ui-regression` 的短生命週期全端 stack（值全內嵌且有預設） |
| `deploy/render-env.sh` | **部署設定的唯一產生點**，寫出 14 個變數；**擋下含 `$` 的憑證**（compose 會對 `--env-file` 的值內插而無聲截斷） |
| `deploy/cloudflared/config.yml` | Cloudflare Tunnel ingress；憑證 0400、以 uid 1000 讀取 |
| `docker-compose.yml`（根） | 本機開發：`postgres:15-alpine` + adminer。**版本與 staging 的 16 不一致** |

### CI/CD 與治理

| 元件 | 職責 |
|---|---|
| `.github/workflows/ci.yml` | **4 個 job、11 個實質檢查步驟**（詳見 `code-quality-assessment.md`） |
| `.github/workflows/deploy.yml` | **3 個 job**：`deploy`（self-hosted runner、30 分逾時、`concurrency: deploy-10-10` 且 `cancel-in-progress: false`）／`rollback`（還原 last-good、開 revert PR、dispatch Deploy Doctor；**權限提升為 `contents: write` + `pull-requests: write` + `actions: write`**）／`notify`（Slack，token 未設時跳過） |
| `.github/aw/actions-lock.json` | 鎖定 GitHub Action 版本 |
| `scripts/validate_repo_contract.py` | 405 LOC。`REQUIRED_FILES`／`REQUIRED_TEXT`／record 層 baseline／文件語言／禁止路徑／禁止內容。**CI 第一道關卡**。★ 本輪：production 路徑檢查由 `git_diff_name_only()` 改為 **`git_ls_files()`** 全域掃描（issue #509），並新增回歸測試 `test_repo_contract_production_paths.py`(287) |
| `scripts/validate_env_contract.py` | 315 LOC。三環境設定分離與完整性（六項檢查）。同屬 `repo-contract` job |
| `scripts/tcms_sync.py` | 515 LOC。手動案例 `--file`（建立＋更新）／自動化案例 `--spec`（只更新） |
| `scripts/tcms_validate.py` | 360 LOC。四類機械檢查，含比對 `openapi.json` 與 `frontend/src/App.tsx` 路由表 |

### 11 組 gh-aw agentic workflows ［本輪重寫］

每個 `.md` 配一個編譯後的 `.lock.yml`；**全部 `engine: copilot`、`network: defaults`**；
編譯器 **`v0.81.6`**（`origin/ut` 已升至 `v0.86.2`，engine `1.0.65` → `1.0.79`）。
**GitHub Actions 只執行 `.lock.yml`，`.md` 對 runtime 完全惰性，且兩者無同步守門員。**

`.md` **都沒有** `name:` frontmatter key——顯示名取自 **body 的第一個 H1**，
且該名稱同時決定 concurrency group（`gh-aw-<name>`）。

| Workflow（`.md`） | 顯示名（body H1） | 觸發 | timeout | safe-outputs | 是否阻擋？ |
|---|---|---|---|---|---|
| `ui-regression` | UI Regression Reporter | PR[3] ＋ dispatch | 30 | `add-comment` ×1 | **✓ 真閘門**（`post-steps` 讀 `pw-report.json` 的 `.stats.unexpected`，非 0 即 `exit 1`；容忍 `flaky`，`retries: 1`） |
| `pr-reviewer` | PR Reviewer | PR[3] ＋ dispatch | 20 | `add-comment` ×1 | ✗ 提問 |
| `contract-guard` | Contract Guard | PR[3] ＋ dispatch | 20 | `add-comment` ×1；`push-to-pull-request-branch` ×1 | ✗（帶 `edit:` bash 權限，會自動修） |
| `code-drift-alert` | Code Drift Alert | PR[3] ＋ **paths**（`backend/main.py`、`backend/services/**`、`backend/models.py`、`schema_rbac.sql`、`schema.sql`）＋ dispatch | 15 | `add-comment` ×1 | ✗ 提問 |
| `local-dev-drift` | Local Dev Drift | PR[3] ＋ **paths**（`backend/database.py`、`deploy/nginx.conf`、`deploy/render-env.sh`、三個 `.env.example`）＋ dispatch | 15 | `add-comment` ×1 | ✗ 提問 |
| `lint-fix` | Lint Fixer | PR[3] ＋ dispatch | 25 | `add-comment` ×1；`push-to-pull-request-branch` ×1 | ✗（帶 `edit:`；**無 github toolset**） |
| `spec-sync` | Spec Sync | **`push` to `ut`** ＋ **paths**（`.../inception/application-design/frontend-backend-specification.md`、`.../construction/database-schema.md`）＋ dispatch | 20 | `create-issue` ×1 labels[spec-drift] | ✗ |
| `issue-triage` | Issue Triage | `issues`[opened,reopened] ＋ dispatch | 15 | `add-comment` ×1；`add-labels` ×3 ＋ 10 項 allowlist | ✗ |
| `daily-digest` | Daily Digest | `schedule` cron **`0 23 * * 1-5`** ＋ dispatch | 20 | `create-issue` ×1 labels[digest]；`close-issue` ×1 | ✗ |
| `release-watch` | Release Watch | **`schedule: weekly on monday`**（gh-aw 模糊排程語法，非 cron） ＋ dispatch | 25 | `create-issue` ×1 labels[dependencies] | ✗ |
| `deploy-doctor` | Deploy Doctor | **`workflow_dispatch` only**（inputs `run_id` required／`pr_number`／`failure_log`） | 15 | `create-issue` ×1 labels[deploy-failure] | ✗（由 `deploy.yml` 的 rollback job dispatch） |

（PR[3] = `pull_request` types `[opened, synchronize, reopened]`。）

**`.md` 宣告的 `permissions:` 全部是唯讀**（`contents`／`pull-requests`／`issues`／`actions`
的 `read` 組合）。**寫入權限由編譯器依 `safe-outputs:` 注入到 `safe_outputs` 與
`conclusion` 兩個 job**——`.md` 的 `permissions:` **只設定 `agent` job**。
詳見 `architecture.md` 的 job 拓撲圖。

> **本 repo 用過的 safe-output 只有 5 種**（`add-comment` 7、`create-issue` 4、
> `push-to-pull-request-branch` 2、`add-labels` 1、`close-issue` 1）。
> **這是用量，不是 gh-aw 的完整目錄**——ADR-0013 已查證框架另有 `update-project` 等
> Projects 相關 safe-output（該事實來自 ADR-0013，非本次掃描）。

**只有 `ui-regression.md` 使用 `pre-agent-steps:` / `post-steps:`**（7 個 pre step：checkout、
setup-node、compose up、等 8090、cache Playwright browsers、install、run suite、報 Kiwi TCMS；
post：teardown ＋ 重新拉紅）。其餘 10 支是純 agent workflow。

另有 `agentics-maintenance.yml`（gh-aw 自動產生，cron `37 0 * * *`，**無對應 `.md`**，
本輪只讀前 60 行）與 `copilot-setup-steps.yml`（772 B，**本輪未讀**）。

### 測試元件

| 元件 | 內容 |
|---|---|
| `backend/tests/helpers.py`(85) | 在任何 DB import 前 `sys.modules.setdefault("psycopg2", MagicMock())`，改用 in-memory SQLite；**使用 `StaticPool`**（預設的 `SingletonThreadPool` 會讓 `TestClient` 的另一個執行緒拿到空資料庫，出現 `no such table`）；每 session 以 `ensure_role_permissions_seeded(db, force=True)` 灌 308 列 |
| `backend/tests/test_*.py`（**25 支** ← 本輪機械複驗，`c3de2c8` 為 21） | unittest + hypothesis + `unittest.mock`；**247 個 `def test_`、14 個 `@given`（8 檔）——皆為本輪 `grep -c` 靜態計數**。LOC 未重新量測。本輪新增 4 檔：`test_dotenv_path.py`(101)、`test_me_endpoint.py`(77)、`test_database_security.py`(65)、`test_repo_contract_production_paths.py`(287)；擴充 3 檔：`test_auth.py`(+57)、`test_collab.py`(+64)、`test_user_list_endpoint.py`(+10) |
| **使用 `TestClient` 的測試檔（3 支 ＋ helpers）** | `test_user_list_endpoint.py`、`test_me_endpoint.py`、**`test_auth.py`（本輪起）**。合計覆蓋 **5/45 operation**（`c3de2c8` 為 3/45）：`GET /api/auth/list`、`PUT /{id}/active`、`PUT /{id}/role`、`GET /api/auth/me`、`POST /api/auth/login` |
| `frontend/tests/e2e/regression.spec.ts`(490) | Playwright；**3 個 describe／14 個 `test()`（靜態計數）**：身分驗證(4)、RBAC 存取控制(2)、**使用者管理頁 — 最後活動時間與分頁(8)**。全部 case 帶 `@purpose`／`@api`／`@ui`／`@story`／`@pass` 結構化規格註解，供 `tcms_validate.py` 機械比對 |
| `TESTING.md`(242) | **測試案例格式的唯一真實來源**：六個必填欄位、手動／自動化分流判準、`required-sections` 機械標記 |

## 元件依賴摘要 ［差異標註］

**扇入最高（被最多元件依賴）**：

1. `models.py` — 全部 service 依賴
2. `rbac.py` — 5 個 router 全部依賴（唯一的全域橫切）
3. `database.py` — 全部 router 經 `get_db()` 依賴
4. `activity.py` — **本輪新增的橫切**：經 `auth.get_current_user` 影響**每一個**帶憑證的請求

**扇出最高（依賴最多元件）**：

1. `wa_collab_orchestrator.py` — `design_agent` + `review_agent` + `wa_score_service` +
   `wa_lens_engine` + models
2. `review_orchestrator.py` — `wa_rule_engine` + `wa_lens_engine` + `review_agent` + models
3. `main.py` — 5 router + database + llm_provider

**零扇出（葉節點，最容易測試與替換）**：`wa_rule_engine.py`、`wa_lens_engine.py`、
`llm_limits.py`、`prompt_guard.py`、`rbac_seed_data.py`

**跨行程邊界的元件**（失敗會影響大範圍）：`design_agent.py` 與 `review_agent.py`
都經 `claude-agent-sdk` spawn 外部 CLI；若 backend 容器缺 Node 22 或 Claude Code CLI，
A1 產圖與 A3 建議階段**同時失效**（A3 會降級為 `rules_only`，A1 則無法產圖）。
`llm_provider.py` 是這兩者共同的環境設定層。

## 測試涵蓋的元件分布 ［本輪機械複驗］

| 模組類別 | 有對應測試檔 | 無對應測試檔 |
|---|---|---|
| 純函式引擎（7） | `diagram_builder`(3 檔)、`wa_rule_engine`、`wa_lens_engine`、`collab_suggestions`、`activity`、`llm_limits`、`prompt_guard` | — |
| Service（4） | `rbac`(3 檔)、`auth`、`lens_service`、`llm_provider` | `wa_score_service` |
| Orchestrator／Agent（5） | `wa_collab_orchestrator`、`design_agent`、`review_agent` | **`review_orchestrator`（狀態機主體）** |
| Router（5，HTTP 層） | `user_router`（**5/16 operation** ← 本輪複驗，含 `login`、`me`） | `review_router`、`agent_router`、`lens_router`、`collab_router` **完全無 HTTP 層測試**（`collab_router` 的 WebSocket 授權路徑亦無） |

**分布特徵**：測試落點沿架構分層，非隨機分布 —— 可直接呼叫的純函式模組覆蓋完整；
需要組裝 HTTP 請求的 router 層幾乎空白。**`review_orchestrator` 無測試特別值得注意**：
它是系統中唯一有明確狀態流轉、逾時分支與降級語意的元件，正是最需要測試的形狀。
