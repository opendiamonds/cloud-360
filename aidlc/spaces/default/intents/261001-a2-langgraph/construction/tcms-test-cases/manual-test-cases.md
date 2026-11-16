# 手動測試案例 — A3 Assessment → LangGraph

> Intent：`261001-a2-langgraph`  
> 由 `tcms-test-cases` stage 產出。本檔是手動案例的**授權來源**。  
> 口語「A2」＝產品 **A3 Assessment**（`/assessment`）。

---

## 覆蓋盤點

外部可觀察行為（本 intent 引入／變更）共 **10 項**。分桶：

| 桶 | 數量 |
|---|---|
| 已自動化 | 7 |
| 待自動化 —— 本 stage 新寫腳本 | 0 |
| 待自動化 —— 本輪 open item | 0 |
| 只能手動 | **3** |
| 無法分類 | **0** |

### 已自動化（7 項）

| # | 行為 | 斷言落點 |
|---|---|---|
| A-1 | Review 經 `openrouter_chat_model`／LangGraph 串流字串增量 | `tests.test_a3_langgraph_migration.TestA3LangGraphMigration.test_run_review_agent_streams_chunks_via_openrouter` |
| A-2 | Review／Lens 原始碼不含 `claude_agent_sdk`／`ClaudeSDKClient` | `test_review_agent_source_has_no_claude_sdk_import`、`test_wa_lens_engine_source_has_no_claude_sdk_import` |
| A-3 | Lens 結構化答案校驗後可被 `score_answers` 消費 | `test_answer_lens_with_agent_returns_validated_shape` |
| A-4 | Lens 空答案上拋（非假成功） | `test_answer_lens_empty_model_raises` |
| A-5 | 缺 OpenRouter 金鑰時錯誤訊息不含 secret | `test_run_review_agent_auth_error_raises_safe_message`、`tests.test_langgraph_runtime` |
| A-6 | 備援建議／Lens heuristic／score 既有行為 | `tests.test_review_agent`、`tests.test_wa_lens_engine` |
| A-7 | 公開 API 簽名保留（`run_review_agent` async gen 等） | `test_public_api_signatures_preserved` |

> 不上手動案例覆寫以上行為（TESTING.md §1）。

### 只能手動（3 項）

| # | 行為 | 為何不能自動化 |
|---|---|---|
| M-1 | 真實 OpenRouter 下 A3 評核 SSE `suggestion_delta` 跑完 | 每跑一次花錢（LLM） |
| M-2 | 真實金鑰下重試建議再次串流 | 同上 |
| M-3 | 本機缺／清空 `OPENROUTER_API_KEY` 時評核降級可讀、且 UI／錯誤不含金鑰字串 | 依賴真實 `.env` 殘值／缺值；CI mock 遮住此路徑 |

---

## TC: 真實 OpenRouter 金鑰下 A3 評核建議串流完整結束

- plan: Cloud-360 A3 LangGraph Refactor
- priority: P1

### 目的

保護 FR3／FR5：有有效 OpenRouter 金鑰時，在 `/assessment` 發起評核必須經 SSE 收到 `suggestion_delta` 文字增量並結束，不得永久停在建議「產生中」或空白。

### 背景

1. 症狀：評核完成分數有了，但建議區一直空白或轉圈，使用者以為 Review agent 當掉。  
2. 錯誤訊息：可能在 Network 中看到 `POST /api/architecture/reviews` 的 EventStream 中斷，或後端 log 出現 `ReviewAgent`／`cloud360.review_agent` 例外字串。  
3. 既有自動化層為何沒抓到：`ui-regression` 與 unittest 皆 **mock LLM**，刻意不打真實 OpenRouter（費用與外網 flaky）；本 intent 結構性盲區即「所有 LLM 路徑」。

### 受測介面

- API: `POST /api/auth/login` → 200 — 取得 JWT
- API: `POST /api/architecture/reviews` → 200 — 發起評核（SSE，含 `suggestion_delta`）
- UI: `/assessment` — A3 評核儀表板：發起評核、分數／findings／建議顯示

### 前置條件

1. 依 `LOCAL-DEV.md` 啟動 backend（`backend/.venv`）與 frontend：  
   `cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8010`  
   `cd frontend && npm run dev`  
2. `backend/.env` 設有**有效** `OPENROUTER_API_KEY`；`LLM_PROVIDER` 建議 `openrouter`。改過 `.env` 後**必須重啟** uvicorn（`--reload` 不監看 `.env`）。  
3. 測試帳號具備 A3 view（例如專案預設 `admin`／其密碼）。  
4. 已有至少一張可評核的架構圖（或先用 Design 建一張最小圖）。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 登入後開啟 `/assessment` | 看到評核相關 UI（圖選擇／發起評核），側欄或路由仍為 Assessment |
| 2 | 選擇一張圖並發起評核 | Network 出現 `POST /api/architecture/reviews`；連線為 EventStream／streaming |
| 3 | 觀察評核進行中建議區 | 出現至少一次建議文字增量（字數變多），對應 SSE 事件 `type` 為 `suggestion_delta`（可於 DevTools EventStream 或前端累積狀態觀察） |
| 4 | 等待評核結束（完成事件或 UI 離開進行中） | 顯示 overall／pillar 分數與 findings；建議區最終為非空白文字；不得在 3 分鐘內一直卡在「無增量且無結束」 |

### 通過條件

- 有效金鑰下，3 分鐘內評核結束，建議區有非空文字，且過程中曾觀察到建議增量（`suggestion_delta` 語意）。

### 追溯

- 實作：`backend/services/review_agent.py`、`backend/services/wa_lens_engine.py`、`backend/services/review_orchestrator.py`、`backend/services/langgraph_runtime.py`、`frontend/src/pages/AssessmentPage.tsx`（路徑以 repo 實際 Assessment 頁為準）
- 自動化對應：無
- PR／commit：intent `261001-a2-langgraph` construction
- User story：FR3.2、FR5、NFR1.1

### 清理

- 無需刪帳號；評核紀錄可留在環境或依團隊慣例刪除。

---

## TC: 真實金鑰下重試建議再次產生 suggestion_delta

- plan: Cloud-360 A3 LangGraph Refactor
- priority: P1

### 目的

保護 WF2／FR3：評核完成後觸發既有「重試建議」必須再次經 LangGraph Review 路徑產生建議串流，前端行為與 URL 不變。

### 背景

1. 症狀：按重試後建議區不變，或 Network 打到錯誤路徑／無 SSE。  
2. 錯誤訊息：可能看到 `POST .../retry-suggestions` 非 2xx，或串流零事件。  
3. 既有自動化層為何沒抓到：重試路徑同樣依賴真實 LLM；單元測試只 mock `run_review_agent`，不覆蓋瀏覽器重試 UX。

### 受測介面

- API: `POST /api/auth/login` → 200 — 取得 JWT
- API: `POST /api/architecture/reviews/{review_id}/retry-suggestions` → 200 — 重試建議 SSE
- UI: `/assessment` — 評核結果上的重試建議操作

### 前置條件

1. 已通過「真實 OpenRouter 金鑰下 A3 評核建議串流完整結束」或同等：畫面上有一筆**已完成**且可見 `review_id` 的評核。  
2. `OPENROUTER_API_KEY` 仍有效；backend／frontend 仍在跑。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 在該筆評核結果觸發「重試建議」（或同等標籤按鈕） | Network 出現 `POST /api/architecture/reviews/{id}/retry-suggestions` |
| 2 | 觀察建議區 | 再次出現文字增量；最終建議文字與重試前相比可更新（允許相同語意，但必須有新的串流事件） |
| 3 | 檢查 URL／頁面 | 仍停留在 `/assessment`；未改打到其他產品路徑 |

### 通過條件

- `retry-suggestions` 回 2xx 串流，且建議區在 3 分鐘內再次收到非空建議文字增量。

### 追溯

- 實作：`backend/services/review_router.py`、`backend/services/review_orchestrator.py`、`backend/services/review_agent.py`
- 自動化對應：無
- PR／commit：intent `261001-a2-langgraph` construction
- User story：FR3.2、FR3.4、BR2.1

---

## TC: 本機缺 OpenRouter 金鑰時評核降級可讀且不洩漏 secret

- plan: Cloud-360 A3 LangGraph Refactor
- priority: P1

### 目的

保護 NFR2.1／BR3.2 與缺金鑰降級：清空 `OPENROUTER_API_KEY` 後發起評核，UI／可見錯誤不得出現 API key 或 token 字面；系統須呈現可理解的降級或錯誤（備援建議／啟發式／明確缺金鑰提示），不得空白假成功。

### 背景

1. 症狀：開發者本機 `.env` 金鑰被清掉或尚未設定，評核看起來「成功」但建議空白，或錯誤泡泡貼出整段金鑰。  
2. 錯誤訊息：預期可見類似「尚未設定 OPENROUTER_API_KEY…」的**安全摘要**；不得出現 `sk-` 開頭字串或完整 token。  
3. 既有自動化層為何沒抓到：CI 用 mock；`llm_auth_ready`／`RuntimeAuthError` 單元測有覆蓋，但**瀏覽器可見面與真實 `.env` 重啟行為**不在 CI。

### 受測介面

- API: `POST /api/auth/login` → 200 — 取得 JWT
- API: `POST /api/architecture/reviews` → 200 — 發起評核（可能降級／錯誤事件）
- UI: `/assessment` — 評核結果與錯誤／備援建議呈現
- 外部相依: 本機 `backend/.env` 的 `OPENROUTER_API_KEY` 狀態

### 前置條件

1. 備份目前 `backend/.env` 的 `OPENROUTER_API_KEY` 值。  
2. 將 `OPENROUTER_API_KEY` **清空**（留空，不要填佔位字串），**重啟** uvicorn。  
3. frontend 仍可連到 backend；測試帳號具備 A3 view。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 開啟 `/assessment` 並發起評核 | 評核流程可結束或明確失敗；不得無限轉圈超過 3 分鐘 |
| 2 | 檢視建議區與任何錯誤提示 | 若有備援建議文字，內容可讀且標示不可用／備援語意；若有錯誤提示，文字**不含**先前金鑰字面、不含 `sk-` 片段 |
| 3 | （可選）在後端 log 搜尋剛發起的評核 | logger 名稱含 `cloud360.`；log 行同樣不得印出完整 API key |

### 通過條件

- 缺金鑰下評核不呈現「空白卻標示成功」；任何使用者可見訊息與抽樣 log **都不含** API key／token 字面。

### 追溯

- 實作：`backend/services/review_agent.py`、`backend/services/wa_lens_engine.py`、`backend/services/llm_provider.py`、`backend/services/langgraph_runtime.py`
- 自動化對應：`tests.test_a3_langgraph_migration.TestA3LangGraphMigration.test_run_review_agent_auth_error_raises_safe_message`（僅後端訊息；本案例補 UI／本機 env）
- PR／commit：intent `261001-a2-langgraph` construction
- User story：NFR2.1、BR3.2、FR3

### 清理

1. 還原 `OPENROUTER_API_KEY` 並重啟 uvicorn。
