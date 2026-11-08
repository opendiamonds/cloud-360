# 技術棧（Technology Stack）

> Reverse Engineering 合成產物｜repo `cloud`｜掃描日 2026-11-05｜HEAD `0bffc82`｜intent `261105-d-iac-generation`｜mode **Focused merge（STALE）**
> 證據標籤：`[實讀]`＝本輪 analyzed.paths 實讀；`[抽查]`＝architect 本輪讀檔／grep（**不在** analyzed.paths，如 `requirements.txt`、`Dockerfile`）；`[繼承]`＝前一輪未複驗。

## 語言與執行環境

| 項目 | 版本 | 位置 |
|---|---|---|
| Python | 3.12（`python:3.12-slim`） | `backend/Dockerfile` [抽查] |
| Node.js | 前端建置用；**backend 映像已不含**（Dockerfile 頂註「no Claude Code CLI / Node runtime in the image」）| [抽查] |
| TypeScript / React / Vite | 前一輪紀錄 | `frontend/`（`package.json` 本輪未讀）[繼承] |
| PostgreSQL | 16-alpine（deploy compose） | [繼承] |

## Backend 依賴（`backend/requirements.txt` 全文｜[抽查]）

| 名稱 | 版本 | 用途／狀態 |
|---|---|---|
| `fastapi` | `==0.111.0` | OpenAPI 決定性釘選（檔內註解）。**與 `team.md` 記載的 `fastapi[standard]==0.141.1` 不一致**——extras 與版本皆不同，需下游以 CI／lockfile 實證 |
| `pydantic` | `==2.13.4` | 同上 |
| `uvicorn`、`httpx`、`python-dotenv`、`sqlalchemy`、`psycopg2-binary`、`passlib[bcrypt]`、`bcrypt`、`pyjwt` | 未 pin | 通用 |
| `langgraph`、`langchain-core`、`langchain-anthropic` | 未 pin | Design（`ChatAnthropic`）與全部 `StateGraph` |
| `langchain-openai` | 未 pin（**現已列入**） | `langgraph_runtime.openrouter_chat_model`（前一輪記為缺漏，已補） |
| `hypothesis` | 未 pin | property-based 測試（ADR-0006） |
| `openpyxl` | `==3.1.5` | 估價表讀取（cost） |
| `PyYAML>=6.0` | 下限 | YAML 資產 |
| `boto3` | 未 pin | 保留（`team.md` ADR-0018 §2：AWS Price List Query） |
| `claude-agent-sdk` | **未列入** | 後端 import 為零 [抽查] |
| `playwright` | **未列入** | 前一輪的 Calculator runners 已不在 cost 目錄 [抽查] |

無 lockfile；CI／Docker／staging 各自解析未 pin 套件（`team.md` 既成事實）。

## Agent／LLM 執行路徑

| 路徑 | 框架 | 模型預設（openrouter） | 適配 |
|---|---|---|---|
| Design | LangGraph `StateGraph`＋`ChatAnthropic` | 前一輪：`google/gemini-2.5-flash`（`DESIGN_LLM_MODEL`）[繼承] | `llm_provider` → `ANTHROPIC_BASE_URL`／`ANTHROPIC_AUTH_TOKEN` |
| Review／Lens | LangGraph `StateGraph`＋`openrouter_chat_model`（`ChatOpenAI`） | `langgraph_runtime` 常數 `google/gemini-3.7-flash`；呼叫端可傳 `model=` | `OPENROUTER_API_KEY`；缺則 `RuntimeAuthError` [實讀 runtime／抽查 agent] |
| Cost advice | 同上（單節點 `StateGraph(dict)`） | 預設 | 同上 |
| `langgraph_runtime` | `langchain_openai.ChatOpenAI`；base `https://openrouter.ai/api/v1`；逾時 60s | `google/gemini-3.7-flash` | 不呼叫 `llm_provider` |

`LLM_PROVIDER`：`openrouter`（預設）｜`cli`（僅本機；`.env.example`、`LOCAL-DEV.md`、`render-env.sh` 仍提及 `claude` CLI，內容未逐行核對其與 LangGraph 路徑是否一致）。

## IaC／D 柱相關技術棧現況

- **無** Terraform／HCL 解析或產生、`tfsec`／`checkov` 類掃描、secret 偵測（gitleaks 類）等任何相依；`requirements.txt` 無相關套件 [抽查]。
- 可複用：LangGraph＋OpenRouter（`langgraph_runtime`）、Hypothesis（PBT）、FastAPI＋`require_story_action`、SSE（`StreamingResponse`）。
- 前端：draw.io iframe（embed.diagrams.net）＋React Router `CapabilityRoute`；toast CTA 為內嵌 JSX（`WorkspacePage`）[實讀]。
- 範圍紅線：不得 `apply` 到雲端 production；IaC 輸出以「產生文字／掃描」為界，apply 屬 high-risk action 須人工閘門（`project.md`）。

## Frontend（摘要｜繼承）

React 19、Vite、react-router、Playwright e2e、Tailwind 4（版本數字以前一輪為準，本輪未重驗；`team.md` 另記 ESLint 10 flat config）。

## 建置與工具鏈

pip（`requirements.txt`，無 lockfile）＋ npm／Vite；Docker backend／frontend；CI GitHub Actions（本輪未讀）。後端無 Ruff／mypy／coverage（`team.md` 既成事實；本輪未反證）。
