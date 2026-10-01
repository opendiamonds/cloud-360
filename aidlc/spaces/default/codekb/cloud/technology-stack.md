# 技術棧（Technology Stack）

> Reverse Engineering 合成產物｜repo `cloud`｜掃描日 2026-10-01｜intent `261001-a2-langgraph`｜mode **Focused merge（STALE）**
> 本輪以 `backend/requirements.txt`、`Dockerfile`、agent 執行時依賴為準；frontend `package.json` 細節屬前一版 shallow。

## 語言與執行環境

| 項目 | 版本 | 位置 |
|---|---|---|
| Python | 3.12 | `backend/`、`scripts/` |
| Node.js | 22 | 前端建置；**backend 映像內**供 `@anthropic-ai/claude-code` |
| TypeScript / React / Vite | 前一版紀錄 | `frontend/`（本輪未重讀 package.json） |
| PostgreSQL | 16-alpine | deploy compose（shallow） |

## Backend 依賴（與本 intent 相關）

| 名稱 | 版本（requirements） | 用途／狀態 |
|---|---|---|
| `langgraph` | 未釘（L18） | Design Agent `StateGraph` **已採用** |
| `langchain-core` | 未釘（L19） | messages／tools |
| `langchain-anthropic` | 未釘（L20） | Design `ChatAnthropic` |
| `langchain-openai` | **未列入** | `langgraph_runtime` 惰性 import |
| `claude-agent-sdk` | **未列入／未 pin** | `review_agent`、`wa_lens_engine`、C1 agent **執行時** import |
| `fastapi[standard]`／`pydantic` | 精確釘選（前一版） | OpenAPI 決定性 |
| `httpx`、`hypothesis`、`boto3`、`playwright` 等 | 見前一版 | C1／通用（shallow） |

**映像額外**：`Dockerfile` 安裝 Node 22 + 全域 `@anthropic-ai/claude-code`（非 pip）。註解 L2–5 仍稱 Design 由 SDK 驅動——**與現況不符**（Design 已 LangGraph；CLI 仍為 Review／Lens 所需）。

## Agent／LLM 執行路徑

| 路徑 | 框架 | 模型預設（openrouter） | 適配 |
|---|---|---|---|
| Design | LangGraph + `ChatAnthropic` | `google/gemini-2.5-flash`（`DESIGN_LLM_MODEL`） | `llm_provider` → `ANTHROPIC_*` |
| Review | Claude Agent SDK | `google/gemini-3.7-flash`（`REVIEW_LLM_MODEL`／`LLM_MODEL`） | SDK + `agent_sdk_env` |
| Lens | Claude Agent SDK + MCP | `google/gemini-3.7-flash`（`get_model_name`） | 同上 |
| `langgraph_runtime` | LangGraph + `ChatOpenAI` | 同字串常數 `gemini-3.7-flash` | OpenAI-compat；**不呼叫** `llm_provider` |

`LLM_PROVIDER`：`openrouter`（預設）｜`cli`。缺 OpenRouter key 須大聲失敗，不自動退回 CLI。

## Frontend（摘要｜shallow）

React 19、Vite、react-router、Playwright e2e、Tailwind 4——版本數字以前一版 `technology-stack.md` 為準，本輪未重驗。

## 建置與工具鏈

pip（`requirements.txt`，無 lockfile）＋ npm／Vite；Docker backend／frontend；CI GitHub Actions（shallow）。後端仍無 Ruff／mypy／coverage 設定（前一版）。

## 執行期外部服務

OpenRouter 或本機 `claude` CLI、n8n、PostgreSQL、draw.io、雲價目／Calculator（C1）、Kiwi TCMS。
