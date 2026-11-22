# API Documentation — Cloud-360

> **基準**：`dc4b687`（2026-09-22）。證據標記慣例見 `business-overview.md` 檔頭。
> 本檔的 HTTP 面由**程式解析 `openapi.json` 全部 path／operation／schema** 取得 `[算]`，
> 非人工計數；SSE 與 WebSocket 面由實讀 router 取得 `[讀]`。

## API 面總覽

| 型態 | 位置 | 數量 | 證據 |
|---|---|---|---|
| REST／HTTP（已登錄 OpenAPI） | `openapi.json` | **42 個 path、55 個 operation、32 個 schema** | `[算]` |
| SSE（`text/event-stream`） | `agent_router`、`review_router`、`advice_stream_router` | **5 個端點** | `[讀]` |
| WebSocket | `collab_router.py:266` | **1 個**，**不在 `openapi.json` 內** | `[讀]`＋`[算]` |

> **數字更正**：`ci.yml:204` 的註解逐字寫「The OpenAPI spec is a complete API map
> (36 paths, 29 schemas)」，本輪實測為 **42 paths、32 schemas** `[算]`。該註解是說明性的、
> 不影響該 step 行為，但它是既有文件已對不上現況的實例。

## Router → prefix 對照 `[讀]` `backend/main.py:52–58`

| Router | prefix | operation 數 `[算]` |
|---|---|---|
| `agent_router`、`review_router`、`lens_router` | `/api/architecture` | 16 |
| `user_router` | `/api/auth` | 16 |
| `collab_router` | `/api/collab` | 12（＋1 個 WS，不計入 OpenAPI） |
| `estimate_intake_router`、`advice_stream_router` | `/api/cost/v1` | 10 |
| （根） | `/` | 1 |

## `/api/cost/v1` 完整面（10 個 operation，授權逐一實讀）

本節是本 intent 的直接編排對象，故逐列列出。`[讀]`

| Method | Path | 授權 dependency | 行號 |
|---|---|---|---|
| POST | `/sets`（201） | `require_story_action("C1","edit")` | `estimate_intake_router.py:45,52` |
| PATCH | `/sets/{set_id}` | `C1.edit` | `:77,82` |
| GET | `/share-users` | `C1.view` | `:92,95` |
| GET | `/sets` | `C1.view` | `:100,108` |
| GET | `/sets/{set_id}` | `C1.view` | `:119,123` |
| DELETE | `/sets/{set_id}`（204） | `C1.edit` | `:128,132` |
| GET | `/sets/{set_id}/shares` | `C1.view` | `:138,142` |
| PUT | `/sets/{set_id}/shares` | `C1.edit` | `:147,152` |
| GET | `/sets/{set_id}/advice` | `C1.view` | `:159,163` |
| GET | `/sets/{set_id}/advice/stream` | `C1.view` | `advice_stream_router.py:161,165` |

**授權全在 dependency 層，service 層無第二道角色檢查** —— `require_story_action`
定義於 `rbac.py:255–280`，先檢查 `authorization_status != "approved"` 直接 403（`:262–267`），
再查 `role_permissions` 表 `[讀]`。`cost/estimate_intake_service.py` 內部**沒有**
第二道角色檢查（`estimate_access.py:29` 的 `can_view_set` 只做擁有者／被分享者的
**row-level** 可見性過濾，不是 role-level）`[簽]`。
→ **直接推論**：大腦以 HTTP 攜帶使用者 token 呼叫 `/api/cost/v1` 是**唯一**能保留
C1 角色授權的呼叫方式；同進程直呼 service 函式會整個繞過 `require_story_action`，
而現有程式碼裡沒有任何備援會補上那一層。

## `/api/auth` 面（16 個 operation）`[算]`

`POST /login`、`POST /register`、`GET /me`、`PATCH /me/authorization-request`、
`GET /list`、`GET /roles`、`GET /roles/catalog`、`GET /role-permissions`、
`PUT /role-permissions`、`POST /role-permissions/reset-defaults`、
`GET /authorization-requests`、`POST /authorization-requests/{request_id}/approve`、
`POST /authorization-requests/{request_id}/reject`、`PUT /{user_id}/role`、
`PUT /{user_id}/active`、`DELETE /{user_id}`。

## `/api/architecture` 面（16 個 operation）`[算]`

`POST /generate`（SSE）、`POST /generate-wa-collab`（SSE）、`POST /diagrams/render-png`、
`GET /reviews`、`POST /reviews`（SSE）、`GET /reviews/{review_id}`、
`DELETE /reviews/{review_id}`、`POST /reviews/{review_id}/retry-suggestions`（SSE）、
`POST /reviews/{review_id}/persist-diagram`、`POST /reviews/commit-collab`、
`POST /reviews/detect-provider`、`GET /lens/active`、`PUT /lens/active`、
`GET /lens/new-question-template`、`POST /lens/suggest-improvement-plan`、
`POST /lens/validate`。

## `/api/collab` 面（12 個 HTTP operation ＋ 1 個 WebSocket）`[算]`

`GET|POST /diagrams`、`GET|PUT|DELETE /diagrams/{diagram_id}`、
`GET|PUT|DELETE /diagrams/{diagram_id}/chat`、`POST /diagrams/{diagram_id}/share`、
`GET /users`、`GET /workspace/bootstrap`、`PUT /workspace/last-opened`。

## SSE 端點（5 個，逐一實讀確認 `media_type="text/event-stream"`）`[讀]`

1. `POST /api/architecture/generate` — `agent_router.py:129`
2. `POST /api/architecture/generate-wa-collab` — `agent_router.py:186`
3. `POST /api/architecture/reviews` — `review_router.py:173`（`_sse_response`，定義於 L70）
4. `POST /api/architecture/reviews/{review_id}/retry-suggestions` — `review_router.py:484`
5. `GET /api/cost/v1/sets/{set_id}/advice/stream` — `advice_stream_router.py:161–179`

> **「三個 SSE 端點」是誤述，正確為 5 個。** 「3」對得上的是**前端三個消費點**——
> `WorkspacePage.tsx:514`、`AssessmentPage.tsx:104`、
> `components/cost/EstimateAdvicePanel.tsx:111` `[算]` grep `getReader()`。
> 後端實際為 5 個端點。

### C1 SSE 的事件語彙（本 intent 若要轉送，這就是可轉送的全部）

| 事件 | 觸發 | 證據 |
|---|---|---|
| `progress` | 每輪輪詢後送出當前進度 | `[讀]` `advice_stream_router.py:81–158` |
| `heartbeat` | 每 `HEARTBEAT_SECONDS = 8.0` 秒 | `[讀]` `:25` |
| `completed` | `advice` 列狀態轉為完成 | `[讀]` |
| `failed` | agent 失敗 | `[讀]` |
| `timeout` | `TIMEOUT = timedelta(minutes=5)` | `[讀]` `advice_orchestrator.py:19` |

**沒有任何 token 級增量。** 迴圈形狀為 `while True`：
`orch.reclaim_stale_generating(db, set_id)` → 查 `Advice` 列 →
`await asyncio.sleep(1.0)` → `db.expire_all()`。

## WebSocket 契約

| 項目 | 值 | 證據 |
|---|---|---|
| 路徑 | `/api/collab/ws/{workspace_id}` | `[讀]` `collab_router.py:266` |
| 認證 | **不用 `Depends`**；自建 `SessionLocal()`，從 `websocket.query_params.get("token")` 取 token | `[讀]` `:266–295` |
| 授權函式 | `_authorize_ws_user`（`:254–262`）→ `get_user_from_token(token, db, record=False)` | `[讀]` `:257` |
| 連線登錄 | `ConnectionManager.active_connections: Dict[str, List[WebSocket]]`（**行程內字典**） | `[讀]` `:58–59` |
| OpenAPI 登錄 | **無**——FastAPI 不登錄 websocket route | `[算]` |

### 三項必須傳給下游的 WebSocket 事實

1. **零契約閘門（本輪新發現的風險）**：`dump_openapi.py --check` 與
   `npm run check:types` 兩道漂移閘門**對 WebSocket 完全無效**。
   本 intent 規劃的新 WebSocket 一道都不過——新 REST 端點要過兩道，新 WS 過零道。
2. **靜默停止更新最後活動時間（本輪新發現的風險）**：`record=False` 跳過
   `auth.py:80–83` 的 `record_activity`，故 **WS 流量不會更新 `users.last_activity_at`**
   （節流 5 分鐘，`activity.py:25`）。大腦若以 WS 為主要互動通道，
   「最後活動時間」這個既有能力會對大腦使用者無聲失效。
3. **token 在 query string**：會進 nginx／cloudflared 的 access log。這是既有做法，
   新 WS 若照抄即承接同一個暴露面（對應 ADR-0006 的 audit logging 與 network exposure）。

## 新增 API 的契約義務

| 新增什麼 | 必做 | 證據 |
|---|---|---|
| REST 端點 | 同一個 PR 重跑 `python scripts/dump_openapi.py --check` 更新 `openapi.json`；前端重產 `src/types/api.d.ts`（2,823 行、已 commit） | `[讀]` `ci.yml:197–198,256–260` |
| REST 端點（測試） | `team.md` B 規則：`TestClient` 斷言 status code 與 `response_model` 欄位集合 | 規則層 |
| 觸及 RBAC 的端點 | `project.md`：allow/deny 雙向 TestClient（有權限 2xx、無權限 403），不得只測 happy path | 規則層 |
| WebSocket | **無任何機械閘門**——契約只能靠人工紀律與測試 | `[算]` |
| 新 story id | 不可依賴 `ensure_role_permissions_seeded(force=False)`（表非空時整段 no-op，`rbac.py:63–65`）；正確落點是 `ensure_missing_role_permissions`（`rbac.py:84–111`，已在 `database.py:168–172` 被呼叫） | `[讀]` |
