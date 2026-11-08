# API 文件（API Documentation）

> Reverse Engineering 合成產物｜repo `cloud`｜掃描日 2026-11-05｜HEAD `0bffc82`｜intent `261105-d-iac-generation`｜mode **Focused merge（STALE）**
> 本輪以 `openapi.json`（deep）與 `main.py`／`agent_router`／`user_router`（deep）為準。證據標籤：`[實讀]`／`[抽查]`／`[繼承]` 同 `business-overview.md`。

## HTTP API 總覽

`openapi.json` 共 **42 paths、55 operations**（腳本計數）[實讀]。掛載（`main.py` L52–58）：

| 群組 | 前綴 | router | 本輪 |
|---|---|---|---|
| architecture（agent／review／lens） | `/api/architecture` | `agent_router`、`review_router`、`lens_router` | agent_router 深讀 |
| auth | `/api/auth` | `user_router` | 深讀（role-permissions／roles／標籤） |
| collab | `/api/collab` | `collab_router` | 僅 openapi 盤點 |
| cost | `/api/cost/v1` | `estimate_intake_router`、`advice_stream_router` | 僅 openapi 盤點＋skim |
| **IaC／Terraform／secret-scan** | — | — | **無**：openapi 對 `iac`／`terraform` 與 D 柱業務路徑 0 命中；`main.py` 無對應 router [實讀] |

## 全 path 清單（`openapi.json`｜[實讀]）

- `/`：GET
- `/api/architecture/`：`diagrams/render-png` POST；`generate` POST；`generate-wa-collab` POST；`lens/active` GET／PUT；`lens/new-question-template` GET；`lens/suggest-improvement-plan` POST；`lens/validate` POST；`reviews` GET／POST；`reviews/commit-collab` POST；`reviews/detect-provider` POST；`reviews/{review_id}` GET／DELETE；`reviews/{review_id}/persist-diagram` POST；`reviews/{review_id}/retry-suggestions` POST
- `/api/auth/`：`authorization-requests` GET；`authorization-requests/{request_id}/approve`／`reject` POST；`list` GET；`login` POST；`me` GET；`me/authorization-request` PATCH；`register` POST；`role-permissions` GET／PUT；`role-permissions/reset-defaults` POST；`roles` GET；`roles/catalog` GET；`{user_id}` DELETE；`{user_id}/active` PUT；`{user_id}/role` PUT
- `/api/collab/`：`diagrams` GET／POST；`diagrams/{diagram_id}` GET／PUT／DELETE；`diagrams/{diagram_id}/chat` GET／PUT／DELETE；`diagrams/{diagram_id}/share` POST；`users` GET；`workspace/bootstrap` GET；`workspace/last-opened` PUT
- `/api/cost/v1/`：`sets` GET／POST；`sets/{set_id}` GET／PATCH／DELETE；`sets/{set_id}/advice` GET；`sets/{set_id}/advice/stream` GET；`sets/{set_id}/shares` GET／PUT；`share-users` GET（共 10 operations）

> 前一輪「`/api/cost` 九個 operations（`list_diagrams`、`get_snapshot`…`apply_sku`）」**已不符 HEAD**：這些 path 不在現行 openapi [實讀]。

## A1 產圖 operations（本輪深讀）

| Method 與路徑 | 授權 | 契約 |
|---|---|---|
| `POST /api/architecture/generate` | `require_arch_action("edit")`（A1／A2／A4 共用編輯權） | body `{messages:[{role,content}], current_xml?}`；response `text/event-stream`，`data: {type, content}`；`type` 見 docstring `message／progress／xml／error` |
| `POST /api/architecture/generate-wa-collab` | 同上 | body `{messages, current_xml?, provider?, diagram_id?, persist_review=true, baseline_findings?, baseline_overall_score?}`；SSE `type ∈ {message, progress, xml_preview, score, complete, error}`；`diagram_id` 不可存取回 404；空 `messages` 回 400 |

共通行為：`prompt_guard` 命中平台自改 → 回固定拒絕 SSE（`message` 後 `complete`），不呼叫 LLM；`_ensure_llm_keys()` 失敗 → 500 `auth_error_message()`；`/generate` 以 `thread_id=f"user-{id}-design"` 呼叫 `run_design_agent` [實讀 agent_router]。

**契約缺口（OpenAPI）**：兩個 SSE 端點的 200 response schema 為空物件 `{}`，事件形狀只存在於 `agent_router` 模組 docstring（「契約（前端依賴，請勿變更）」）與前端解析慣例 [實讀 dev 報告]。

**命名漂移**：端點 docstring 與 log 仍寫「Design Agent（Agent SDK）」「Agent SDK 路徑」，而 `design_agent` 現為 LangGraph [實讀 agent_router docstring／抽查 design_agent]。

## RBAC 相關 operations（本輪深讀）

| Method 與路徑 | 說明 |
|---|---|
| `GET /api/auth/role-permissions` | 回傳矩陣列（`RolePermissionRow`）；含 D1／D2／D3 列 |
| `PUT /api/auth/role-permissions` | 批次寫入；對架構 story 去重（`seen_arch_roles`） |
| `POST /api/auth/role-permissions/reset-defaults` | 以 `DEFAULT_ROLE_PERMISSIONS` 覆寫 |
| `GET /api/auth/roles` | `{roles: CANONICAL_ROLES, stories: STORY_IDS}` |
| `GET /api/auth/roles/catalog` | 角色目錄（`_build_role_catalog(db)`；是否內嵌 story 標籤未逐行核對） |

D1／D2／D3 的短名「Terraform 產出」「IaC 安全掃描」「Secret／敏感值」定義於 `user_router.STORY_FEATURE_LABELS`（後端）與 `RolePermissionsPage`（前端）兩處 [實讀]。

## 授權掛載樣板（供 D 端點沿用）

`services/rbac.py`：`require_arch_action(action)`（L188，架構編輯權）與 `require_story_action(story_id, action)`（L255）。後者要求 `authorization_status == "approved"`，否則 403「帳號尚未通過管理員授權」；再以 `user_can(db, role, story_id, action, …)` 判定，否則 403「權限不足：需要 {story}.{action}，目前角色為 {role}」[抽查：L255–275 讀取]。**目前沒有任何 handler 掛 `D1`／`D2`／`D3`** [實讀 dev 報告]。

## 內部／非 HTTP 契約

| 契約 | 說明 |
|---|---|
| `langgraph_runtime` | `openrouter_chat_model(model=…)`（缺 `OPENROUTER_API_KEY` → `RuntimeAuthError(code="missing_openrouter_api_key")`，domain 錯誤，非 HTTP）；`invoke_graph`／`stream_graph`／`astream_graph` 接受呼叫端編譯好的 graph，本模組不擁有 cost／IaC 節點；預設 base URL `https://openrouter.ai/api/v1`、預設模型 `google/gemini-3.7-flash`、逾時 60s [實讀] |
| `llm_provider`／`llm_limits` | 啟動時 `configure_provider_env`；Design 經 `ANTHROPIC_*` 映射 [抽查／繼承] |
| Claude Agent SDK | 後端 import 已為零（見 `business-overview.md`）；前一輪 MCP `emit_lens_answers`／`cloud360-cost` 敘述不再成立 [抽查] |

## 對外第三方（摘要）

OpenRouter（LLM）；n8n webhook（圖示）；embed.diagrams.net（前端）；PostgreSQL；公開／憑證型雲價目端點（cost，shallow）。[繼承／抽查]

## 前端路由表（`App.tsx`｜[實讀]）

`/login`、`/403`、`/waiting-approval`、`/workspace`（A1 view）、`/assessment`（A3 view）、`/cost`（C1 view）、`/admin/users`（J3a）、`/admin/authorization-requests`（J3a）、`/admin/role-permissions`（J3b）、`/admin`→`/admin/users`、根 `/` 導向、`*` 兜底。**無 D／IaC 路由**。`CapabilityRoute` 以 `storyId` ＋ `action` 閘頁。

## 契約同步規則

改端點須同 PR 重產 `openapi.json` 與 `frontend/src/types/api.d.ts`，否則 CI drift 紅燈（`team.md`）。D 柱首個端點將首次改動此契約面。
