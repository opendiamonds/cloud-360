# API Documentation — Cloud-360

> 逆向工程產出。基準 commit `c3de2c8`（branch `danniel/fix/production-path-check-noop`，2026-08-17）。
> 端點清單以 `python3` 解析 repo 根目錄的 `openapi.json` 取得精確計數，並回 router 原始碼
> 逐條核對 guard。**36 paths / 45 operations / 29 schemas。**

## API 面總覽

| 介面類型 | 數量 | 位置 | 在 `openapi.json` 內？ | 對外 |
|---|---|---|---|---|
| REST + SSE（FastAPI） | **45 operations**（36 paths） | `backend/services/*_router.py` | ✓ | 是 |
| **WebSocket** | 1 | `backend/services/collab_router.py` | **✗** | 是 |
| **SSE 事件型別** | 10 種 | 4 個模組 | **✗**（是 body 內的字串值，非 schema） | 是 |
| 行程內 MCP server | 1 tool | `backend/services/design_agent.py` | ✗ | **否**（僅供 Agent SDK 內部使用） |

**「36 vs 45」的讀法**：36 是 **path 數**，45 是 **method × path 的 operation 數**。
引用端點數量時務必指明是哪一種 —— 前一版 codekb 記的「46 個端點」是人工計數的混合值，
本次已改為以規格檔為準。

Router 掛載（`backend/main.py`）：

| Router | 前綴 | paths | operations |
|---|---|---|---|
| `agent_router` | `/api/architecture` | 2 | 2 |
| `review_router` | `/api/architecture` | 7 | 9 |
| `lens_router` | `/api/architecture` | 4 | 5 |
| `user_router` | `/api/auth` | 15 | 16 |
| `collab_router` | `/api/collab` | 7 | 12 |
| （root） | `/` | 1 | 1 |

**注意**：三個 router 共用 `/api/architecture` 前綴，端點命名空間靠子路徑區分
（`/generate*`、`/reviews*`、`/diagrams*`、`/lens/*`）。新增端點時要留意跨 router 的路徑衝突。

**前端 client 面**：**無集中式 API client**。所有頁面與元件直接呼叫原生 `fetch()`
搭配 `frontend/src/config/api.ts` 的 `apiUrl()`／`wsUrl()`，手動組
`Authorization: Bearer ${token}` header。共 **52 處呼叫點**散落在 10 支檔。

## 規格檔與型別契約鏈

這是本 API 面最重要的結構特徵，**前一版 codekb 尚未記載**：

| 環節 | 實作 | CI gate |
|---|---|---|
| 規格產生 | `backend/scripts/dump_openapi.py`（**由程式碼 import，非打 live 端點**） | ✓ `dump_openapi.py --check`（backend job）：重 dump 並與 committed `openapi.json` 比對 |
| 型別產生 | `npm run gen:types` → `openapi-typescript@7.13.0` → `frontend/src/types/api.d.ts`（2,385 行） | ✓ `npm run check:types`（frontend job）：重產到暫存檔並逐位元比對 |
| 規格不得外洩 | — | ✓ `find dist -name 'openapi*'` 非空即 fail（frontend job） |

**對變更的直接約束**：任何改動 `response_model`、路由或查詢參數的 PR，
**必須在同一個 PR 內**重跑 `dump_openapi.py` 與 `npm run gen:types` 並 commit 兩份產物，
否則上述兩道 gate 會紅燈。

**採用率**：`api.d.ts` 目前**只被 `AdminPage.tsx` import**（1/10）。其餘 9 支做 `fetch()`
的檔仍手寫本地 interface，不受這條契約鏈保護。

**已知脆弱點**：產生器版本字串 `openapi-typescript@7.13.0` 手寫在兩處
（`package.json` 的 `gen:types` 與 `frontend/scripts/check-api-types.mjs:21` 的 `GENERATOR`），
**無機制鎖住一致**；腳本註解自承兩處不一致時 gate 會誤報。

## 認證與授權契約

### 認證

- **機制**：JWT Bearer token，HTTP `Authorization: Bearer <token>` header。
- **演算法**：HS256。
- **效期**：8 小時（`ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8`）。
- **payload**：`sub` 為 username，`exp` 為到期時間。
- **驗證流程**（`auth.get_current_user`）：解 JWT → 取 `sub` → 查 `users` →
  檢查 `is_active`（停用者 403）→ **呼叫 `activity.record_activity`（條件式寫入）** →
  回傳 `User` 物件。JWT 無效或過期一律 401 並帶 `WWW-Authenticate: Bearer`。

**重要副作用**：`get_current_user` **不是純讀取**。每個帶有效憑證的請求都會經過
`record_activity`，距上次寫入超過 5 分鐘時 UPDATE `users.last_activity_at`。
任何在請求鏈上新增行為的設計都要考慮與這條寫入路徑的交互。

### 授權

授權一律以 guard 工廠注入，三種形式：

| Guard | 語意 |
|---|---|
| `get_current_user` | 只要求已登入，不檢查能力 |
| `require_story_action("<story>", "<action>")` | 檢查指定 story 的指定 action |
| `require_arch_action("<action>")` | 架構圖三合一（`A1`／`A2`／`A4`），內部改讀 `A1` |

**判定三關（順序固定）**：

1. `authorization_status != 'approved'` → 403「帳號尚未通過管理員授權」。
   **這一關在任何矩陣查詢之前**，pending／rejected 使用者一律無業務權限。
2. role 非 canonical role（含經 `ROLE_ALIASES` 正規化後）→ 拒絕。
3. 查 `role_permissions` 的 `(role, story_id)` 列：
   - `view` → `can_view OR can_edit OR can_review`
   - `edit` → `can_edit`
   - `review` → `can_review`

**錯誤碼慣例**：401 = 憑證問題；403 = 已登入但權限不足或帳號停用／未授權；
404 = 資源不存在或無權限存取（`get_accessible_diagram` 把「無權限」也回 404，避免資源探測）；
**422 = 查詢參數不合法**（由 FastAPI `Query(ge=..., le=...)` 在進入 handler 前擋下）。

## 端點完整清單（45 operations）

Guard 欄位由 router 原始碼的 `Depends(...)` 逐條核出。

### 根與健康檢查（1）

| Method | Path | Handler | 授權 | 用途 |
|---|---|---|---|---|
| GET | `/` | `read_root` | 無 | health check（Dockerfile HEALTHCHECK 目標） |

### A1 架構產圖（`agent_router`，2）

| Method | Path | Handler | 授權 | 用途 |
|---|---|---|---|---|
| POST | `/api/architecture/generate` | `chat_and_generate` | `require_arch_action("edit")` | A1 對話產圖，**SSE**。經 `prompt_guard` 前置檢查 |
| POST | `/api/architecture/generate-wa-collab` | `chat_and_generate_wa_collab` | `require_arch_action("edit")` | A1↔A3 雙 agent 協作產圖，**SSE** |

### A3 評核（`review_router`，9）

| Method | Path | Handler | 授權 | 用途 |
|---|---|---|---|---|
| POST | `/api/architecture/reviews/detect-provider` | `detect_review_provider` | `A3.edit` | 從 XML 偵測雲別 |
| POST | `/api/architecture/reviews` | `create_review` | `A3.edit` | 建立評核（選圖或上傳 XML），**SSE** |
| GET | `/api/architecture/reviews` | `list_reviews` | `A3.view` | 評核清單 |
| POST | `/api/architecture/reviews/commit-collab` | `commit_collab_review_endpoint` | `A3.edit` | 將協作結果落為 review |
| GET | `/api/architecture/reviews/{review_id}` | `get_review` | `A3.view` | 單筆評核 |
| DELETE | `/api/architecture/reviews/{review_id}` | `delete_review` | `A3.edit` | 刪除／封存評核 |
| POST | `/api/architecture/reviews/{review_id}/persist-diagram` | `persist_review_diagram` | `A3.edit` | 將評核用 XML 建檔為圖 |
| POST | `/api/architecture/reviews/{review_id}/retry-suggestions` | `retry_review_suggestions` | `A3.edit` | 重試建議生成（狀態須為 `rules_only`），**SSE** |
| POST | `/api/architecture/diagrams/render-png` | `render_diagram_png` | `A3.view` | 伺服端 PNG 轉檔 |

### Lens 編輯（`lens_router`，5）

**五個 operation 的 guard 一致為 `A3.review`。**

| Method | Path | Handler | 用途 |
|---|---|---|---|
| GET | `/api/architecture/lens/active` | `get_active_lens` | 讀取現行 Lens（`?provider=`） |
| PUT | `/api/architecture/lens/active` | `put_active_lens` | 更新現行 Lens |
| GET | `/api/architecture/lens/new-question-template` | `new_question_template` | 新問題模板 |
| POST | `/api/architecture/lens/suggest-improvement-plan` | `post_suggest_improvement` | AI 建議改善計畫 |
| POST | `/api/architecture/lens/validate` | `post_validate_lens` | Lens JSON 驗證 |

### 身分、註冊與使用者管理（`user_router`，16）

| Method | Path | Handler | 授權 | 用途 |
|---|---|---|---|---|
| GET | `/api/auth/roles/catalog` | `roles_catalog` | **公開（無 guard）** | 註冊頁角色功能目錄，動態源自 `role_permissions` |
| POST | `/api/auth/register` | `register` | **公開** | 註冊；建 `authorization_status='pending'` 使用者 + 授權申請 |
| POST | `/api/auth/login` | `login` | **公開** | 登入；回 JWT + role + authorization_status |
| GET | `/api/auth/me` | `get_me` | `get_current_user` | 目前身分 + 完整 permissions map + pending_request |
| PATCH | `/api/auth/me/authorization-request` | `patch_my_authorization_request` | `get_current_user` | pending 使用者改申請角色 |
| GET | `/api/auth/roles` | `list_canonical_roles` | `get_current_user` | 回 `CANONICAL_ROLES` 與 `STORY_IDS` |
| GET | `/api/auth/list` | `list_users` | `J3a.view` | **Admin 頁使用者清單（分頁）** |
| GET | `/api/auth/authorization-requests` | `list_authorization_requests` | `J3a.view` | 授權申請清單（`?status=`） |
| POST | `/api/auth/authorization-requests/{request_id}/approve` | `approve_authorization_request` | `J3a.edit` | 核准（受 BR-04 限制） |
| POST | `/api/auth/authorization-requests/{request_id}/reject` | `reject_authorization_request` | `J3a.edit` | 駁回 |
| PUT | `/api/auth/{user_id}/active` | `update_user_active` | `J3a.edit` | 啟用／停用 |
| PUT | `/api/auth/{user_id}/role` | `update_user_role` | `J3a.edit` | 指派角色 |
| DELETE | `/api/auth/{user_id}` | `delete_user` | `J3a.edit` | 硬刪除（擁有圖表時 403） |
| GET | `/api/auth/role-permissions` | `get_role_permissions` | `J3b.view` | 讀權限矩陣 |
| PUT | `/api/auth/role-permissions` | `put_role_permissions` | `J3b.edit` | 寫權限矩陣（`A1`/`A2`/`A4` 三 story 同步寫入） |
| POST | `/api/auth/role-permissions/reset-defaults` | `reset_role_permissions_defaults` | `J3b.review` | 重設為預設矩陣 |

#### `GET /api/auth/list` 的分頁契約（本輪新增）

| 參數 | 型別 | 約束 | 預設 |
|---|---|---|---|
| `page` | int | `ge=1` | 1 |
| `page_size` | int | `ge=1`, `le=MAX_PAGE_SIZE` | `DEFAULT_PAGE_SIZE` |

設計上值得下游注意的三點（皆有原始碼註解佐證）：

1. **約束以框架原生形式宣告**：非法值在**進入 handler 之前**就被擋下並回 **422**，
   結構上到不了查詢層；且約束會出現在 `openapi.json` 中，
   因此**同時被型別契約 gate 與規格漂移 gate 覆蓋**。
2. **頁次合法但超出範圍不是錯誤**：offset 超過總數時查詢自然回空清單，
   `page` 照樣回顯請求值（**不夾到最後一頁**）。
3. **`total` 是獨立的計數查詢**，不得由 `len(items)` 導出 —— 後者只在多頁時才錯，
   而目前資料量下多頁情境不會自然出現。**`ORDER BY id` 是「重複請求同一頁得到相同順序」
   的結構前提，不得移除。**

### 圖與共編（`collab_router`，12 + 1 WebSocket）

| Method | Path | Handler | 授權 | 用途 |
|---|---|---|---|---|
| **WS** | `/api/collab/ws/{workspace_id}` | `websocket_endpoint` | **無 guard** | 架構圖即時共編廣播（**不在 `openapi.json`**） |
| GET | `/api/collab/users` | `get_users` | arch `edit` | 分享對象清單 |
| GET | `/api/collab/diagrams` | `list_my_diagrams` | arch `view` | 我的加上被分享的圖 |
| POST | `/api/collab/diagrams` | `create_diagram` | arch `edit` | 建圖 |
| GET | `/api/collab/diagrams/{diagram_id}` | `get_diagram` | arch `view` | 讀單圖 |
| PUT | `/api/collab/diagrams/{diagram_id}` | `update_diagram` | arch `edit` | 更新圖 |
| DELETE | `/api/collab/diagrams/{diagram_id}` | `delete_diagram` | arch `edit` | 刪圖 |
| GET | `/api/collab/diagrams/{diagram_id}/chat` | `get_diagram_chat` | arch `view` | 讀 A4 聊天 |
| PUT | `/api/collab/diagrams/{diagram_id}/chat` | `save_diagram_chat` | arch `edit` | 存 A4 聊天 |
| DELETE | `/api/collab/diagrams/{diagram_id}/chat` | `clear_diagram_chat` | arch `edit` | 清空聊天（不刪圖） |
| POST | `/api/collab/diagrams/{diagram_id}/share` | `share_diagram` | arch `edit` | 分享給使用者 |
| GET | `/api/collab/workspace/bootstrap` | `workspace_bootstrap` | arch `view` | 還原 last_opened 與該圖聊天 |
| PUT | `/api/collab/workspace/last-opened` | `set_last_opened` | arch `view` | 更新 `users.last_opened_diagram_id` |

### 端點授權分布摘要

| 授權層級 | operations |
|---|---|
| 完全公開 | **4**（`GET /`、`roles/catalog`、`register`、`login`） |
| 僅需登入 | **3**（`me`、`me/authorization-request`、`roles`） |
| 需 `A3` 能力 | **14**（review 9 + lens 5） |
| 需架構圖能力 | **14**（agent 2 + collab 12） |
| 需 `J3a` 能力 | **7** |
| 需 `J3b` 能力 | **3** |
| **無任何 guard 的業務端點** | **1**（WebSocket，不計入 45） |

## SSE 串流契約

四個 operation 回傳 `text/event-stream`：`generate`、`generate-wa-collab`、`reviews`(POST)、
`retry-suggestions`。共同形狀：每個 chunk 為 `data: {JSON}\n\n`，JSON 一律含 `type` 欄位，
序列化時 `ensure_ascii=False`（中文不轉義）。

### ⚠️ 這整節的契約沒有任何機械檢查

事件名是 response body 內的**字串值**，不是 schema 結構，因此**不在 `openapi.json` 內**。
`dump_openapi.py --check`、`check-api-types.mjs`、`tcms_validate.py` 的 API 比對
**三者的輸入都是 `openapi.json`**，故都碰不到它。目前唯一的契約紀錄是
`agent_router.py` docstring 的「契約（前端依賴，請勿變更）」段。

**已實測到的後果**：前端 `AssessmentPage.tsx:632` 有一個處理 `type === 'unsupported'` 的
分支，但**後端從未產生該事件**（全 `backend/` grep 該字串只有一處命中，且是 DB 查詢的
過濾集合）。這段前端程式碼不可達，而六道 CI 檢查與 14 個 e2e case 全綠。

### 後端實際產生的事件型別（10 種）

| 事件 | 產生者 | 說明 |
|---|---|---|
| `message` | design_agent → agent_router | agent 文字輸出 |
| `progress` | design_agent、orchestrator | 進度訊息 |
| `xml` | design_agent → agent_router | 最終 draw.io XML |
| `xml_preview` | wa_collab_orchestrator | 協作過程的中間圖 |
| `score` | wa_collab_orchestrator | 帶 `round`、`overall_score`、`pillar_scores`、`findings`、`high_risk_count`、`passed` |
| `rules_done` | review_orchestrator | 規則階段完成，支柱分數與 findings 可用 |
| `lens_done` | review_orchestrator | Lens 階段完成 |
| `suggestion_delta` | review_orchestrator、review_agent | 逐塊串流的建議文字，帶 `content` 與 `review_id` |
| `complete` | 多處 | 終止事件 |
| `error` | 多處 | 可帶 `code`（例：`lens_error`、`invalid_status`） |

**事件 type 一律是字面字串**（本次實測全 `services/` 無變數化寫法）。

### A1 產圖（`POST /api/architecture/generate`）

- **request**：`{ messages: [{role, content}], current_xml?: string }`
- **response 事件 type**：`message`／`progress`／`xml`／`error`
- **前置檢查**：`prompt_guard` 命中平台自我竄改樣式時**不呼叫 LLM**，回固定拒絕訊息

### A1↔A3 協作（`POST /api/architecture/generate-wa-collab`）

- **request**：`{ messages, current_xml?, provider?, diagram_id?, persist_review?,
  baseline_findings?, baseline_overall_score? }`
- **response 事件 type**：`message`／`progress`／`xml_preview`／`score`／`complete`／`error`
- 最多 2 輪；目標為 lens 總分 ≥ 80（`TARGET_SCORE`）且無 `HIGH_RISK`

### A3 評核（`POST /api/architecture/reviews`）

- **事件序**：`rules_done` → `lens_done` → 多個 `suggestion_delta` → `complete`；
  任一階段可改送 `error`
- 逾時保護：Review Agent 75 秒（`AGENT_TIMEOUT_SEC`），lens agent 90 秒
  （`LENS_AGENT_TIMEOUT_SEC`）。逾時**不中斷串流**，改以 `rules_only` 狀態收尾
- 重試端點若狀態非 `rules_only`，回 `error` 且 `code` 為 `invalid_status`

### 基礎設施要求（不可省略）

`frontend/nginx.conf` 為 SSE 特別設定：**`proxy_buffering off`** 與 **600 秒 timeout**。
任何反向代理層變更都必須保留這兩項，否則串流會被緩衝或提前中斷。

## WebSocket 契約

- **路徑**：`/api/collab/ws/{workspace_id}`
- **用途**：架構圖即時共編廣播（`ConnectionManager`）
- **前端**：`frontend/src/hooks/useCollaboration.ts`（64 LOC）
- **nginx**：`/api/` location 已設 WS upgrade header
- **授權**：**無**。連線層不做 JWT 檢查，是唯一無 guard 的業務端點
- **機械檢查**：**無**。FastAPI 不把 WebSocket 路由寫進 OpenAPI 規格，
  故三道規格衍生的檢查全部碰不到它

**兩件事疊加**：唯一無授權的端點，同時也在唯一的機械檢查盲區內。

## 前端路由與權限對照

`frontend/src/App.tsx`：

| 路由 | 元件 | Guard |
|---|---|---|
| `/login` | `LoginPage` | 無 |
| `/403` | `ForbiddenPage` | 無 |
| `/waiting-approval` | `WaitingApprovalPage` | `ProtectedRoute` |
| `/workspace` | `WorkspacePage` | `ProtectedRoute` + `CapabilityRoute storyId="A1" action="view"` |
| `/assessment` | `AssessmentPage` | `A3.view` |
| `/admin/users` | `AdminPage` | `J3a.view` |
| `/admin/authorization-requests` | `AuthorizationRequestsPage` | `J3a.view` |
| `/admin/role-permissions` | `RolePermissionsPage` | `J3b.view` |
| `/admin` | redirect → `/admin/users` | — |
| `/` 與 `*` | `DefaultRedirect` | 依序 pending → `canArch('view')` → `A3` → `J3a` → `J3b` → `/403` |

**前端 guard 不是安全邊界**，只是體驗優化；每次業務呼叫後端都會重跑完整判定。

`tcms_validate.py` 會把測案宣告的 UI 路徑與這張路由表機械比對 —— 寫了不存在的路徑會被擋下。

## 資料契約

### `UserSchema`（`user_router.py:112-126`）

`GET /api/auth/list` 回應的元素型別，也是 `PUT /{user_id}/active` 與
`PUT /{user_id}/role` 的 `response_model`：

| 欄位 | 型別 | required | 備註 |
|---|---|---|---|
| `id` | int | ✓ | |
| `username` | str | ✓ | |
| `role` | `Optional[str]` | | pending 使用者為 `null` |
| `is_active` | bool | ✓ | |
| `authorization_status` | str | | default `'approved'` |
| `requested_role` | `Optional[str]` | | 由 `_pending_request_for_user()` 額外查得 |
| `last_activity_at` | `Optional[datetime]` | **✓** | **刻意無預設值** |
| `is_overdue` | bool | **✓** | **刻意無預設值** |

**`last_activity_at` 與 `is_overdue` 為何刻意不設預設值**（原始碼註解逐字說明）：
三個構造點皆為手寫具名引數，**帶預設值時漏傳會靜默通過**（既有的 `requested_role`
就是這樣漏掉的）；無預設值讓漏傳在**構造當下**就是 `ValidationError`。

**這是一個值得沿用的設計原則**：回應模型的新欄位若靠自動預設值補齊，
「後端漏構造」與「後端正確回傳空值」在線路上不可區分。

### `UserListPage`（`user_router.py:134-143`）

| 欄位 | 型別 | required |
|---|---|---|
| `items` | `List[UserSchema]` | ✓ |
| `total` | int | ✓ |
| `page` | int | ✓ |
| `page_size` | int | ✓ |

**四欄皆必填、皆無預設值**，理由同上（原始碼註解）：帶預設值會讓「完全沒讀查詢參數的
實作」也輸出四個形狀正確的 key，**使驗收只能驗到 key 存在而驗不到行為**。

### `User.to_dict()`

回傳 6 個欄位（`id`／`username`／`role`／`is_active`／`authorization_status`／
`last_opened_diagram_id`），**不含 `password_hash`**，亦**不含 `last_activity_at`**
—— 該欄位只經 `UserSchema` 對外。

### 角色與 story 常數

- `GET /api/auth/roles` 回傳 `CANONICAL_ROLES`（**11 個**）與 `STORY_IDS`（**28 個**）。
- `STORY_IDS` 於 `rbac.py:37` 由 `DEFAULT_ROLE_PERMISSIONS` **動態導出**
  （`sorted({row[1] for row in DEFAULT_ROLE_PERMISSIONS})`），非硬編碼。
  **改 seed 資料即改變全系統的 story 清單。**

## API 面的已知缺口

1. **HTTP 層測試只覆蓋 3/45 operation**。全 repo 唯一使用 `TestClient` 的測試檔是
   `test_user_list_endpoint.py`，它涵蓋 `GET /api/auth/list`、`PUT /api/auth/{id}/active`、
   `PUT /api/auth/{id}/role` 三個 operation。**其餘 42 個沒有任何 HTTP 層測試**
   （`review_router` 9、`collab_router` 12、`lens_router` 5、`agent_router` 2、
   `user_router` 其餘 13、root 1）。
   採用成本已被證明為零（依賴齊備、`app.dependency_overrides` 可覆寫
   `get_db`／`get_current_user`、`TestClient(app)` 不觸發 `init_db()`），
   故這是「尚未擴散」而非「做不到」。
2. **WebSocket 無驗證且在檢查盲區**（見上）。
3. **SSE 事件契約無機械檢查**，且已實測出一個雙向皆死的契約（`unsupported`）。
4. **公開端點可觸發 seed**：`roles_catalog`（公開無驗證）在回應前呼叫
   `ensure_role_permissions_seeded(db, force=False)` —— 匿名請求可觸發 seed 邏輯。
   實際影響有限（`force=False` 時表非空即 return），但這是一條匿名可達的寫入路徑。
5. **無 API 版本化**：路徑無 `/v1/` 之類的版本段。契約變更沒有並存機制。
   **在 deploy-on-merge 之下這一點特別重要**：破壞性契約變更與其消費端之間存在一條
   隱含的「同批次」約束，它比依賴順序更強 —— 不得分批部署。
6. **死碼 guard**：`auth.py` 的 `RoleChecker` 三個常數（`require_admin`、
   `require_architect`、`require_any_user`）**無任何端點使用**，是與 `rbac` 並行的
   舊粗粒度授權機制殘留。`require_any_user` 另持有一份 11 個角色的手寫 allowlist
   （角色清單的副本之一）。**新端點不應使用。**
