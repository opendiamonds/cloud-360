# API Documentation — Cloud-360

> **基準**：`34aeef3`（2026-10-02）。**新鮮度等級與證據標記的定義在 `reverse-engineering-timestamp.md`**。
> 本檔的 HTTP 面由**本輪以 Python 完整解析 `openapi.json`** 取得 `[跑]`，**非人工計數**；
> SSE 與 WebSocket 面由 router 的實讀片段取得。
> 由 `codekb/cloud-360@2026-09-22` 與 `codekb/cloud@2026-10-01` 合併。

---

## API 面總覽 〔A〕

| 型態 | 位置 | 數量 | 證據 |
|---|---|---|---|
| REST／HTTP（已登錄 OpenAPI） | `openapi.json`（OpenAPI **3.1.0**） | **42 path、55 operation、39 schema** | `[跑]` 程式解析 |
| SSE（`text/event-stream`） | `agent_router`、`review_router`、`advice_stream_router` | **5 個端點** | `[跑:link1]` grep ＋ `[讀]` 複驗其中 1 處 |
| **WebSocket** | `collab_router.py:266`、**`brain_router.py:238`** | **2 個**，**兩者皆不在 `openapi.json` 內** | `[跑]` |

> **數字更正兩處** 〔A〕：
> 1. `cloud-360/` 記 **32 個 schema** `[承:cloud-360@2026-09-22]`——**本輪實算為 39**。
> 2. `cloud-360/` 記 WebSocket 「**1 個**」——**本輪實算為 2 個**
>    （`[跑]` `grep -rn '@router.websocket' backend/`）。
>
> 另：`ci.yml:216` 的註解逐字寫「The OpenAPI spec is a complete API map
> (36 paths, 29 schemas)」`[讀]`——**兩個數字都錯**，且比 `cloud-360@2026-09-22`
> 當時記的偏離量更大。該註解是說明性的、不影響 step 行為，
> 但它是既有文件已對不上現況的實例（`code-quality-assessment.md` T-6）。

---

## Router → prefix 對照 〔A〕

`[讀]` `backend/main.py:54–63`（**行號已更新**；`cloud-360/` 引用的 `:52–58` 已位移，且少記 `brain_router`）：

| 行 | Router | prefix | operation 數 `[跑]` |
|---|---|---|---|
| `:54` | `agent_router` | `/api/architecture` | 13 path／**16 op** |
| `:55` | `review_router` | `/api/architecture` | （同上合計） |
| `:56` | `lens_router` | `/api/architecture` | （同上合計） |
| `:57` | `user_router` | `/api/auth` | 15 path／**16 op** |
| `:58` | `collab_router` | `/api/collab` | 7 path／**12 op**（＋**1 個 WS**，不計入 OpenAPI） |
| `:59` | `estimate_intake_router` | `/api/cost/v1` | 6 path／**10 op** |
| `:60` | `advice_stream_router` | `/api/cost/v1` | （同上合計） |
| **`:63`** | **`brain_router`** | **`/api/brain`（DEMO SCOPE）** | **0 op**（只有 WS，故完全不在 `openapi.json`） |
| — | （根） | `/` | 1 path／1 op |
| | | **合計** | **42 path／55 op** |

---

## `/api/cost/v1` 完整面（10 個 operation）〔C〕

本節是本 intent 的直接編排對象，故逐列列出。
`[承:cloud-360@2026-09-22]`，**本輪只以程式複驗 operation 總數為 10，未重讀授權行號**。

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

**授權全在 dependency 層，service 層無第二道角色檢查** `[承:cloud-360@2026-09-22]`
——`require_story_action` 定義於 `rbac.py:255–280`，先檢查
`authorization_status != "approved"` 直接 403（`:262–267`），再查 `role_permissions` 表。
`cost/estimate_intake_service.py` 內部**沒有**第二道角色檢查
（`estimate_access.py:29` 的 `can_view_set` 只做擁有者／被分享者的 **row-level** 可見性過濾，
不是 role-level）。

> **直接推論（對本 intent 最要緊的一條）**：大腦以 HTTP 攜帶使用者 token 呼叫
> `/api/cost/v1` 是**唯一**能保留 C1 角色授權的呼叫方式；
> **同進程直呼 service 函式會整個繞過 `require_story_action`，
> 而現有程式碼裡沒有任何備援會補上那一層。**

> ⚠️ **`cloud/` 的「`/api/cost` 的 9 個 operations」整段已作廢** 〔A〕：
> 它列的是 `list_diagrams`／`get_snapshot`（`run_agent` 預設 true）／`get_audit`／
> Calculator csv／xlsx 匯出／`apply_region`／`hours`／`override`／`sku`，
> 授權經 `services.rbac.user_can`（`C1`／`C1h`／`C1r`／`C1o`）`[承:cloud@2026-10-01]`。
> **那是已退役的 C1 舊實作**（prefix 也不同：`/api/cost` vs 現行 `/api/cost/v1`）。
> 本檔刻意不保留，因為保留會讓下游誤以為兩套 API 並存。

---

## `/api/auth` 面（16 個 operation）〔C〕

`[承:cloud-360@2026-09-22]`（本輪只複驗總數）：
`POST /login`、`POST /register`、`GET /me`、`PATCH /me/authorization-request`、
`GET /list`、`GET /roles`、`GET /roles/catalog`、`GET /role-permissions`、
`PUT /role-permissions`、`POST /role-permissions/reset-defaults`、
`GET /authorization-requests`、`POST /authorization-requests/{request_id}/approve`、
`POST /authorization-requests/{request_id}/reject`、`PUT /{user_id}/role`、
`PUT /{user_id}/active`、`DELETE /{user_id}`。

`[跑:link1]` 測試輸出證實 `TestClient` 確實打過其中數個
（`GET /api/auth/list`、`PUT /api/auth/2/active`、`PUT /api/auth/2/role` 皆回 200）。

---

## `/api/architecture` 面（16 個 operation）〔C〕

`[承:cloud-360@2026-09-22]`（本輪只複驗總數）：
`POST /generate`（SSE）、`POST /generate-wa-collab`（SSE）、`POST /diagrams/render-png`、
`GET /reviews`、`POST /reviews`（SSE）、`GET /reviews/{review_id}`、
`DELETE /reviews/{review_id}`、`POST /reviews/{review_id}/retry-suggestions`（SSE）、
`POST /reviews/{review_id}/persist-diagram`、`POST /reviews/commit-collab`、
`POST /reviews/detect-provider`、`GET /lens/active`、`PUT /lens/active`、
`GET /lens/new-question-template`、`POST /lens/suggest-improvement-plan`、
`POST /lens/validate`。

**前端契約** `[承:cloud@2026-10-01]`：`AssessmentPage` 消費上述 SSE／JSON；
**不傳** LLM model 名，僅傳雲 `provider`。重構不得破壞事件順序與 payload 形狀。
A3 SSE 的事件順序為 `rules_done` → `lens_done` → `suggestion_delta` → `complete`。

---

## `/api/collab` 面（12 個 HTTP operation ＋ 1 個 WebSocket）〔C〕

`[承:cloud-360@2026-09-22]`：
`GET|POST /diagrams`、`GET|PUT|DELETE /diagrams/{diagram_id}`、
`GET|PUT|DELETE /diagrams/{diagram_id}/chat`、`POST /diagrams/{diagram_id}/share`、
`GET /users`、`GET /workspace/bootstrap`、`PUT /workspace/last-opened`。

---

## SSE 端點（5 個）〔B〕

`[跑:link1]` `grep -rn 'text/event-stream' backend/`（排除 tests）→ 5 個實際端點：

1. `POST /api/architecture/generate` — `agent_router.py:129` 〔A，本輪 `[讀:link1]` 複驗〕
2. `POST /api/architecture/generate-wa-collab` — `agent_router.py:186`
3. `POST /api/architecture/reviews` — `review_router.py:73`（`_sse_response`）
4. `POST /api/architecture/reviews/{review_id}/retry-suggestions` — `review_router.py:484`
5. `GET /api/cost/v1/sets/{set_id}/advice/stream` — `advice_stream_router.py:173` 〔A，本輪 `[讀]` 複驗〕

（`agent_router.py:13` 另有一處是 docstring 內的契約說明，非端點。）

> **「三個 SSE 端點」是誤述，正確為 5 個。** 「3」對得上的是**前端三個消費點**
> ——`WorkspacePage.tsx:514`、`AssessmentPage.tsx:104`、
> `components/cost/EstimateAdvicePanel.tsx:111` `[承:cloud-360@2026-09-22]`（grep `getReader()`）。
> **注意**：那三個行號是 `dc4b687` 的值，且 `WorkspacePage` 自那時起已由 1,194 行變動過，
> 本輪未複驗那三個行號。

### C1 SSE 的事件語彙（本 intent 若要轉送，這就是可轉送的全部）〔C〕

| 事件 | 觸發 | 證據 |
|---|---|---|
| `progress` | 每輪輪詢後送出當前進度 | `advice_stream_router.py:81–158` |
| `heartbeat` | 每 `HEARTBEAT_SECONDS = 8.0` 秒 | `:25` |
| `completed` | `advice` 列狀態轉為完成 | — |
| `failed` | agent 失敗 | — |
| `timeout` | `TIMEOUT = timedelta(minutes=5)` | `advice_orchestrator.py:19` |

全部 `[承:cloud-360@2026-09-22]`。**沒有任何 token 級增量。**
迴圈形狀為 `while True`：`orch.reclaim_stale_generating(db, set_id)` → 查 `Advice` 列 →
`await asyncio.sleep(1.0)` → `db.expire_all()`。

> **這一段對本 intent 的設計直接有約束力**：上游若以「逐字轉送／彙整後再送／並存」
> 三選一來處理成本查詢的串流，**那個框架不成立**——來源端是**狀態事件**，不是 token 串流。

---

## WebSocket 契約

### 兩條 WS 的對照 〔B〕

`[跑]` `grep -rn '@router.websocket' backend/`：

| 面向 | `/api/collab/ws/{workspace_id}` | `/api/brain/ws` |
|---|---|---|
| 定義處 | `collab_router.py:266` `@router.websocket("/ws/{workspace_id}")` `[跑]` | `brain_router.py:238` `@router.websocket("/ws")` `[跑]` |
| 狀態 | 正式功能（A4 共編） | **DEMO SCOPE**，`U13` 落地時整支取代 |
| 認證位置 | **query string**（`?token=...`） 〔C〕 | **`Sec-WebSocket-Protocol` 標頭** 〔B，docstring 自述〕 |
| 授權函式 | `_authorize_ws_user`（`:254–262`）→ `get_user_from_token(token, db, record=False)`（`:257`） 〔C〕 | `get_user_from_token(..., record=True)` 〔B〕 |
| 活動時間 | **不更新** `users.last_activity_at` | **會更新** |
| Session 持有 | `ConnectionManager.active_connections: Dict[str, List[WebSocket]]`（行程內字典，`:58–59`） 〔C〕 | 行程內 dict（`_session_for`，`:87`），docstring 自述「**重啟即失憶**」 〔B〕 |
| FastAPI `Depends` | **不用**；自建 `SessionLocal()` 〔C〕 | 〔E〕本輪未讀本體 |
| 版本協商 | **無** | `hello {v}` → `ready {protocolVersion}`；不符以 **4400** 關閉並帶 expected／received 〔B〕 |
| 訊息封包 | 無宣告型別 | `{v, type, turnId, payload}`，`v` 字面值 `1` 〔B〕 |
| OpenAPI 登錄 | **無** 〔A〕 | **無** 〔A〕 |
| **契約閘門** | **零** 〔A〕 | **兩道** 〔A〕 |

### 大腦 WS 的訊息型別（docstring 自述的子集）〔B〕

`[讀]` `brain_router.py:1–31`。**完整定義在 `brain_ws_contract.py`（783 LOC），本輪未讀** 〔E〕
——**那是 `U2`／`U13` 的直接輸入，列為待查。**

| 方向 | 總數 | demo 已實作的 |
|---|---|---|
| 伺服器 → 客戶端 | **9 種** | `ready`／`token`／`clarify`／`work_items`／`done`／`error`（6 種） |
| 客戶端 → 伺服器 | **6 種** | `hello`／`user_message`／`select_clarify_candidate`／`set_work_target`（4 種） |

**未實作的訊息**：`cost_card`、`sharing_mode`（另加多連線扇出、`correct_work_item`）。

**終止語意（docstring 逐字）**：**零內容不得以 `done` 結束，一律走 `error(EMPTY_RESPONSE)`。**
`error.code` 是**封閉的四值**。

**一條本輪從 `ci.yml` 讀到、對 `U2`／`U13` 直接可用的約束** 〔A〕 `[讀]` `ci.yml:205–208`：
`check:ws-types` 步驟同時承載 `BR4.4` 斷言——**產生出的 `.d.ts` 必須保留解釋
`WorkItem.sideEffect` 兩個 sentinel 值的 JSDoc**，因為 TypeScript 會把
`"none" | "unknown" | string` 收斂成 `string`，**那兩個 sentinel 的語意在別處無處存活**。

### WS 契約鏈與它的兩道閘門 〔A〕

> **這整段是本輪新增，且它推翻 `cloud-360/` 的一句核心主張**
> （「新 WebSocket 契約沒有任何機械閘門」／「新 WS 過零道」）。

```
brain_ws_contract.py（783 LOC，Pydantic 型別定義）
   │ backend/scripts/dump_ws_contract.py
   ▼
ws-contract.json（repo 根，31,012 bytes，帶一層 OpenAPI 外殼 paths:{}）
   │ npm run gen:ws-types（openapi-typescript 7.13.0）
   ▼
frontend/src/types/ws-contract.d.ts
```

| 閘門 | 位置 | 擋什麼 |
|---|---|---|
| `python scripts/dump_ws_contract.py --check` | `ci.yml:291`（backend job） | 契約模組改了但 `ws-contract.json` 沒重 dump |
| `npm run check:ws-types` | `ci.yml:210`（frontend job） | `ws-contract.json` 改了但前端型別檔沒重產 |

測試另有 `backend/tests/test_dump_ws_contract.py`、`test_ws_contract.py`
（兩者含 `@given` `[跑]`；**內容本輪未讀**）。

**覆蓋範圍的洞** `[跑]` `grep -c "collab" ws-contract.json` → **0**：
**只涵蓋大腦，不涵蓋 `/api/collab/ws/{workspace_id}`。** 既有共編 WS 仍零契約閘門。

**`dump_ws_contract.py:1–40` 的三項設計決定**（docstring 逐字 `[讀]`，對新增 WS 直接有約束力）：

1. **刻意不 import `main`**——三個具體差別：閘門紅燈只代表**契約本身**漂移
   （應用任何 import 失敗不會連帶紅燈）；不需要 DB 樁
   （對照 `dump_openapi.py:36` 得先 `sys.modules.setdefault("psycopg", MagicMock())`）；
   契約邊界更誠實（模型定義了即進契約，與有沒有被 router 用到無關）。
2. **規格檔刻意放 repo 根而非 `frontend/public/`**（`NFR5.6`）——nginx 是
   `root /usr/share/nginx/html` ＋ `try_files $uri`，而 Vite 會把 `public/` 原樣複製進 `dist/`。
   放那裡等於把**完整的訊息地圖**（九種伺服器訊息、六種客戶端訊息與全部 payload 欄位，
   即大腦的內部協定與能力邊界）對未認證訪客公開。
   **連帶禁止**：不得把該規格檔 import 進前端程式碼
   （型別檔只有型別、不產生執行期程式碼，故它本身不是洩漏面）。
3. **fail-closed**（`nfr-design §六`）——規格檔不存在、契約模組 import 失敗、任一斷言失敗，
   三者皆 exit 非 0；且**刻意不**以 try/except 包住契約模組的 import
   （「一個把例外吞掉後回報『無漂移』的檢查腳本，它的綠燈不構成任何證據」，
   `construction.md` 的 `## Error Handling` 逐字禁止那個形狀）。

**決定性**（`BR4.2`／`BR4.6`）：`sort_keys=True`（輸出與 dict 插入順序無關）、
`ensure_ascii=False`（中文 description 以原字元存放使 diff 可讀）、尾端換行。
**跨 `pydantic` 版本會飄，故 `requirements.txt` 對它採精確等值釘選（`pydantic==2.13.4`）；
升版時必須在同一個 PR 內重新 dump 並 commit。**

---

## 三項必須傳給下游的 WebSocket 事實（修訂版）〔A〕

1. **契約閘門不是零，但覆蓋不全。** `openapi.json` 的兩道閘門對 WS **結構上完全無效**
   （`ci.yml:200–204` 的註解逐字承認：「not under-covered, but **with no assertion at all**
   on that change path」）；但 WS 另有自己的一對閘門，**只是只涵蓋大腦**。
   新增大腦訊息型別 → 過兩道；新增或修改 `collab` WS → 仍過零道。
2. **活動時間的風險只在舊那條。** `collab_router.py:257` 的 `record=False` 會讓
   `users.last_activity_at` 對該通道的使用者靜默失效；大腦 demo 已用 `record=True` 避開。
   **但 demo 會被整支取代——`U13` 必須自己重新做對這件事。**
3. **token 的位置兩條不同。** 舊那條在 query string（會進 nginx／cloudflared 的 access log，
   對應 ADR-0006 的 audit logging 與 network exposure）；
   大腦 demo 走 `Sec-WebSocket-Protocol` 標頭。**新 WS 不要照抄舊那條。**

---

## 新增 API 的契約義務 〔A／B〕

| 新增什麼 | 必做 | 證據 |
|---|---|---|
| **REST 端點** | 同一個 PR 重跑 `python scripts/dump_openapi.py --check` 更新 `openapi.json`（`ci.yml:280`）；前端重產 `src/types/api.d.ts`（`ci.yml:198` `check:types`） | `[算]` |
| **REST 端點（測試）** | `team.md` B 規則：`TestClient` 斷言 status code 與 `response_model` 欄位集合。**HEAD 已有 6 支先例**（`team.md` 記的「唯一使用例」已過時） | `[跑]` |
| **觸及 RBAC 的端點** | `project.md`：allow/deny 雙向 `TestClient`（有權限 2xx、無權限 403），**不得只測 happy path** | 規則層 |
| **WebSocket（大腦訊息型別）** | 改 `brain_ws_contract.py` 後**同一個 PR** 重跑 `dump_ws_contract.py`（`ci.yml:291`）並重產 `ws-contract.d.ts`（`ci.yml:210`）。**另須保留 `WorkItem.sideEffect` 的 JSDoc（`BR4.4`）** | `[讀]`／`[算]` |
| **WebSocket（其他）** | **無任何機械閘門**——`collab` WS 的契約只能靠人工紀律與測試 | `[跑]` |
| **升 `pydantic`／`fastapi`** | **兩個 dump 都要重跑並 commit**（OpenAPI 與 WS 規格都對版本敏感） | `[讀]` |
| **新 story id** | 不可依賴 `ensure_role_permissions_seeded(force=False)`（表非空時整段 no-op，`rbac.py:63–65`）；正確落點是 `ensure_missing_role_permissions`（`rbac.py:84–111`，已在 `database.py:168–172` 被呼叫）。**同時觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步** | 〔C〕＋規則層 |
| **新資料表** | `schema_rbac.sql`（空 volume）＋ 既有環境的演進路徑（`_ensure_*` 或獨立 migration）＋ `DEPLOY.md`（blocking）。**若要被 ORM 查到，還要補 `models.py`** ——階層三表正是只做了前兩者的實例 | 〔A〕 |
| **新環境變數（compose 消費）** | 同一個 PR 內讓 `deploy/render-env.sh` 寫它、`deploy/.env.example` 列它，否則 `validate_env_contract.py` 紅燈（`ci.yml:159`）。**憑證不得含 `$`** | 〔A〕 |

---

## 對外第三方 〔B〕

| 服務 | 用途 | 等級 |
|---|---|---|
| **OpenRouter** | **唯一的 LLM provider**（`llm_provider.py:42–43` 的 `_VALID_PROVIDERS` 只剩一個值） | A |
| n8n webhook | 架構圖 icon 取得 | C |
| 雲端公開／目錄價目端點 | C1 的 `pricing_client`（agent 按需查價，結果只寫入建議文字） | C |
| PostgreSQL | 全部持久化（映像已升 `pgvector/pgvector:pg18`） | A |
| embed.diagrams.net | 前端 draw.io iframe | C |
| Cloudflare Tunnel | staging 對外唯一入口 | C |
| Kiwi TCMS | 測案管理 | C |
| **Redis 8** | **已佈建、應用零消費** | A |
| **Ollama** | **已佈建、應用零消費**（`OLLAMA_EMBED_MODEL=bge-m3`） | A |

> **`claude` CLI 已不再是外部依賴** 〔A〕——`backend/Dockerfile` 已移除 Node 與該 CLI，
> `[跑:link1]` 全樹零子行程呼叫。兩份 store 的「映像需 `claude` CLI」皆已作廢。

---

## 契約同步規則（彙整）〔A〕

本 repo 有**兩條**契約鏈，各有兩道閘門，形狀相同但來源不同：

| 鏈 | 來源 | 中間產物 | 前端型別 | 後端閘門 | 前端閘門 |
|---|---|---|---|---|---|
| HTTP | FastAPI app | `openapi.json`（repo 根） | `src/types/api.d.ts` | `ci.yml:280` | `ci.yml:198` |
| **WS** | `brain_ws_contract.py` | `ws-contract.json`（repo 根） | `src/types/ws-contract.d.ts` | `ci.yml:291` | `ci.yml:210` |

**兩個規格檔都刻意放 repo 根而非 `frontend/public/`**，理由相同（nginx ＋ Vite 會把它變成
未認證可讀的公開檔案）；`ci.yml:224` 另有一道「`dist/` 內不得出現 `openapi*` 檔」的檢查，
**是什麼在阻止未來的某次編輯悄悄撤銷這個佈局**。
