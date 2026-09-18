# API 文件（API Documentation）

> Reverse Engineering 合成產物｜repo `cloud`｜commit `8c90f40`

## 公開 HTTP 表面

後端於 `backend/main.py` 掛載五組 router（皆需依端點搭配 Bearer／cookie 認證與 RBAC；細節以原始碼 `Depends` 為準）。

### `/api/architecture`（產生、審核、Lens）

| 方法 | 路徑 | 用途 | 主要消費者 |
|---|---|---|---|
| POST | `/generate` | 架構產生（基礎路徑） | Workspace／agent |
| POST | `/generate-wa-collab` | WA 協作產生（A1 主路徑） | `WorkspacePage` |
| POST | `/reviews/detect-provider` | 偵測雲端供應商 | `AssessmentPage` |
| POST | `/reviews` | 建立審核 | A3 |
| POST | `/reviews/commit-collab` | 提交協作審核結果 | A3 |
| GET | `/reviews` | 列表（支援 `diagram_id`、`ephemeral`） | A3 |
| GET | `/reviews/{review_id}` | 審核詳情 | A3 |
| POST | `/reviews/{review_id}/persist-diagram` | 審核結果回寫圖 | A3 |
| DELETE | `/reviews/{review_id}` | 刪除審核 | A3 |
| POST | `/reviews/{review_id}/retry-suggestions` | 重試改善建議 | A3 |
| POST | `/diagrams/render-png` | 圖轉 PNG | 匯出／預覽 |
| GET/PUT | `/lens/active` | 作用中 lens | A3 lens tab |
| GET | `/lens/new-question-template` | 新問題範本 | Lens 編輯 |
| POST | `/lens/suggest-improvement-plan` | 改善計畫建議 | A3 |
| POST | `/lens/validate` | Lens 驗證 | Lens 編輯 |

實作：`agent_router.py`、`review_router.py`、`lens_router.py`。

### `/api/collab`（圖庫與即時同步）

| 方法 | 路徑 | 用途 |
|---|---|---|
| WS | `/ws/{workspace_id}` | 工作區即時同步 |
| GET | `/users` | 協作用戶 |
| GET | `/diagrams` | 圖列表 |
| GET | `/workspace/bootstrap` | 工作區啟動資料 |
| PUT | `/workspace/last-opened` | 記錄上次開啟 |
| GET/PUT/DELETE | `/diagrams/{id}/chat` | 聊天歷史 |
| GET/POST/PUT/DELETE | `/diagrams`、`/diagrams/{id}` | 圖 CRUD（含 `xml_data`） |
| POST | `/diagrams/{id}/share` | 分享 |

實作：`collab_router.py`。A1 autosave 與 A3 選圖皆依賴此面。

### `/api/auth`（使用者與權限）

涵蓋 `register`／`login`／`me`、授權請求核准／駁回、使用者啟用／角色指派、`role-permissions` 讀寫與 reset-defaults、roles catalog。實作：`user_router.py`；守衛依賴 `auth.py`／`rbac.py`。

健康檢查：`GET /` → `{"message": "Cloud-360 Backend is running"}`。

## 內部契約與副作用

| 內部邊界 | 契約摘要 | 副作用注意 |
|---|---|---|
| `design_agent` → `diagram_builder` | LLM tool 輸出 `groups`／`nodes`／`edges` → mxGraph XML 字串 | Edge 無 port、parent 固定 `"1"` 影響圖品質（A1） |
| `DrawioCanvas` ↔ iframe | `postMessage`：init、load XML、autosave；缺 save／exit | 前端 `onAutosave` → `setXml` 可能清 undo |
| Review orchestrator → DB | findings／scores_json 持久化 | ephemeral reviews 與 persist-diagram 語意不同 |
| OpenRouter env 映射 | `configure_openrouter_env` 將 `OPENROUTER_API_KEY` 映射為 Agent SDK 變數 | 不得把 secret 寫入 repo／artifacts |

前端以 `apiUrl()` 組絕對路徑；CORS 由 `CORS_ORIGINS` 控制（預設 localhost Vite）。

## A1／A3 關鍵序列與契約缺口

**A1 generate→canvas**

1. `POST /api/architecture/generate-wa-collab`（messages、可選 current XML）  
2. 回應 XML → `WorkspacePage.setXml` → `DrawioCanvas` load  
3. iframe autosave → `PUT /api/collab/diagrams/{id}`  

契約缺口：無伺服器端 prompt refusal（擋平台 DB／憑證／系統值變更請求）；embed 協議未文件化 save／exit。

**A3 review**

1. `GET /api/collab/diagrams/{id}` 取 XML  
2. `POST /api/architecture/reviews`（＋可選 detect-provider／lens）  
3. `GET /api/architecture/reviews*` 呈現 findings  

契約缺口：前端預覽與 commit-collab／persist-diagram 的狀態機需在 bugfix 時保持向後相容。
