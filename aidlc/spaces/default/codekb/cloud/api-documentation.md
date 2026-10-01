# API 文件（API Documentation）

> Reverse Engineering 合成產物｜repo `cloud`｜掃描日 2026-10-01｜intent `261001-a2-langgraph`｜mode **Focused merge（STALE）**
> Assessment／architecture 評核路徑本輪對照 `openapi.json` 與 router；`/api/cost` 九端點保留前一版敘述（未重驗實作）。

## HTTP API 總覽

掛載（`main.py`）：`agent_router`／`review_router`／`lens_router` → `/api/architecture`；`collab_router` → `/api/collab`；另有 auth、cost。

| 群組 | 前綴 | 本輪焦點 |
|---|---|---|
| architecture（agent／review／lens） | `/api/architecture` | **深讀評核與 collab 相關** |
| collab | `/api/collab` | `GET /api/collab/diagrams` 輔助選圖（實作 skim） |
| cost（C1） | `/api/cost` | 前一版 9 operations（shallow） |
| auth | `/api/auth` | 未重掃 |

## Assessment／A1 相關 operations（本輪）

| Method 與路徑 | 用途 | 後端 |
|---|---|---|
| `POST /api/architecture/generate` | A1 Design Agent SSE | `agent_router` → `design_agent`（LangGraph） |
| `POST /api/architecture/generate-wa-collab` | A1↔A3 雙 agent 優化 SSE | `wa_collab_orchestrator` |
| `POST /api/architecture/reviews` | 發起評核 SSE（`rules_done`→`lens_done`→`suggestion_delta`→`complete`） | `review_orchestrator` |
| `POST /api/architecture/reviews/detect-provider` | 偵測雲 provider | `review_router` |
| `POST /api/architecture/reviews/commit-collab` | 提交 collab 結果 | `review_router` |
| `GET /api/architecture/reviews`、`GET\|DELETE .../{id}` | 評核 CRUD | `review_router` |
| `POST .../reviews/{id}/persist-diagram` | 持久化圖 | `review_router` |
| `POST .../reviews/{id}/retry-suggestions` | 重跑建議 SSE | `run_review_agent` |
| `POST /api/architecture/diagrams/render-png` | 圖轉 PNG | 列於 OpenAPI |
| `/api/architecture/lens/*` | Lens CRUD／驗證 | Assessment 可切分頁；agent 框架重構非首要 |

**前端契約**：`AssessmentPage` 消費上述 SSE／JSON；**不傳** LLM model 名，僅雲 `provider`。重構不得破壞事件順序與 payload 形狀。

## `/api/cost` 的 9 個 operations（前一版保留）

`list_diagrams`、`get_snapshot`（`run_agent` 預設 true）、`get_audit`、Calculator csv／xlsx 匯出、`apply_region`／`hours`／`override`／`sku`。授權經 `services.rbac.user_can`（`C1`／`C1h`／`C1r`／`C1o`）。細節見前一版；本輪未重驗。

## 內部／非 HTTP 契約

| 契約 | 說明 |
|---|---|
| Claude Agent SDK（Review／Lens／C1） | 執行時 import；映像需 `claude` CLI |
| Design LangGraph | `StateGraph` + tools；非 SDK |
| `langgraph_runtime` | OpenRouter helpers；**未**接 Assessment |
| C1 MCP `cloud360-cost` | 3 tools（前一版）；與 A3 无关 |
| `llm_provider`／`llm_limits` | 啟動時 `configure_provider_env`；SDK 路徑用 `agent_sdk_env` |

## 對外第三方（摘要）

OpenRouter 或本機 `claude` CLI（LLM）；n8n webhook（圖示）；雲端公開價目／Calculator（C1，shallow）；PostgreSQL；embed.diagrams.net（前端）。

## 前端路由表（`App.tsx`）

含 `/login`、`/403`、`/waiting-approval`、`/workspace`、`/assessment`、`/cost`、`/admin/*`、根 redirect。根導向仍優先 C1 → `/cost`（前一版事實）。

## 契約同步規則

改端點須同 PR 重產 `openapi.json` 與 `frontend/src/types/api.d.ts`，否則 CI drift 紅燈。`fastapi`／`pydantic` 精確釘選以保 dump 決定性（前一版）。
