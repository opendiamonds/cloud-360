# 程式結構（Code Structure）

> Reverse Engineering 合成產物｜repo `cloud`｜掃描日 2026-10-01｜intent `261001-a2-langgraph`｜mode **Focused merge（STALE）**

## 頂層目錄與檔案分佈

應用程式碼為 `backend/` + `frontend/`。本輪深讀集中在 Assessment／agent／LangGraph／`llm_provider`；`backend/cost/`、CI、deploy 等為前一版深讀後 demote 為 shallow。

| 目錄 | 性質（本輪） |
|---|---|
| `backend/services/` | **焦點**：agent／review／WA／LLM 模組深讀；其餘 skim |
| `backend/cost/` | 前一版深讀 → 本輪 shallow |
| `frontend/src/pages/AssessmentPage.tsx` | 深讀 API／SSE／優化流程 |
| `scripts/smoke_langgraph_openrouter.py` | 深讀 |
| `aidlc/`、`.claude/` | 未深讀 |

## `backend/` 組織

`backend/` 為 flat module（無頂層 `__init__.py`）。

| 子目錄／檔案 | 內容 | 本輪深度 |
|---|---|---|
| `main.py` | CORS、startup（`load_backend_dotenv` + `configure_provider_env`）、router 掛載 | deep |
| `Dockerfile` | Python 3.12-slim + Node 22 + `@anthropic-ai/claude-code`；註解仍寫 Design 走 SDK（**過時**） | deep |
| `requirements.txt` | 含 `langgraph`／`langchain-core`／`langchain-anthropic`（未釘版）；**缺** `langchain-openai`、`claude-agent-sdk` pin | deep |
| `services/design_agent.py` | LangGraph `StateGraph` + `ChatAnthropic` | deep |
| `services/langgraph_runtime.py` | OpenRouter／`ChatOpenAI` helpers；**未被** Assessment／Design import | deep |
| `services/review_*.py`、`wa_*.py` | A3 評核／分數／collab／規則／lens | deep（規則細節未逐條） |
| `services/llm_provider.py`、`llm_limits.py` | Provider 開關、模型 getter、token／XML 限額 | deep |
| `services/agent_router.py` | A1 generate／wa-collab SSE | deep |
| `cost/` | C1 領域套件 | shallow（前一版） |
| `tests/test_langgraph_*.py`、`test_agent.py` | LangGraph／遷移／手動 CLI | deep |
| `prompts/`、`lenses/` | 靜態資產 | skim |

## Assessment／Agent 模組呼叫面（本輪）

```
AssessmentPage
  → review_router / agent_router（main: /api/architecture）
       → review_orchestrator / wa_collab_orchestrator / wa_score_service
            → wa_rule_engine | wa_lens_engine | review_agent | design_agent
```

啟動：`main` → `configure_provider_env`（openrouter 映射或 cli 清衝突變數）→ `apply_agent_token_limits_to_env`。

## 資料模型（摘要｜前一版保留）

11 張 ORM 表：認證／RBAC／`user_diagrams`／`architecture_reviews`／`wa_lenses`／C1 四表。啟動補丁 `_ensure_a3_schema`、`_ensure_cost_schema` 等見前一版 `code-structure` 敘述（本輪未重讀 `models.py`／`database.py`）。

## `frontend/` 組織

| 路徑 | 本輪 |
|---|---|
| `src/App.tsx` | deep（路由含 `/assessment`） |
| `src/pages/AssessmentPage.tsx` | deep（SSE／API；版面其餘結構性閱讀） |
| 其餘 pages／components | skim |
| `src/cost/` | shallow（前一版） |

## 程式慣例

- WA 引擎 `wa_*`；router `*_router.py`。
- Design＝LangGraph；Review／Lens／C1 agent＝Claude Agent SDK（執行時 import）。
- Logger：`logging.getLogger("cloud360.<module>")` 為主。

## 建置與產物鏈

| 產物 | 來源 | 守門 |
|---|---|---|
| `openapi.json` | `dump_openapi.py` | CI `--check` |
| `frontend/src/types/api.d.ts` | `gen:types` | `check:types` |
| backend 映像 | `backend/Dockerfile` | 含 Node／claude CLI（Review／Lens 仍需） |
