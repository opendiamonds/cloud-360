# 技術堆疊 — cloud-360

> 新鮮度：2026-11-22。版本取自 `backend/requirements.txt` 與 `frontend/package.json`〔盤點〕；執行環境版本另註。外部依賴的方向與風險見 `dependencies.md`。

## 後端

| 項目 | 版本 | 證據 |
|---|---|---|
| Python | CI 與 backend 映像 3.12（`ci.yml` `python-version: '3.12'`；`requirements.txt` 註解）；本機掃描以 3.13 執行測試 | 盤點／執行 |
| FastAPI | `==0.111.0`（精確釘選，理由：OpenAPI 輸出跨版本會飄） | 盤點 |
| Pydantic | `==2.13.4` | 盤點 |
| uvicorn、websockets | 未釘版 | 盤點 |
| SQLAlchemy ＋ psycopg v3 | 未釘版（driver 以 `postgresql+psycopg://` 顯式指定） | 盤點 |
| Redis client（`redis`） | 未釘版 | 盤點 |
| LangGraph、langchain-core、langchain-anthropic、langchain-openai | 未釘版 | 盤點 |
| httpx | 未釘版 | 盤點 |
| Hypothesis | 未釘版 | 盤點 |
| mcp ／ sse-starlette ／ mcp-types | `==2.3.0` ／ `==3.0.3` ／ `==2.3.0` | 盤點 |
| 其他 | pyjwt、passlib[bcrypt]、openpyxl `==3.1.5`、PyYAML、boto3、checkov `==3.4.3` | 盤點 |

## 前端

| 項目 | 版本 | 證據 |
|---|---|---|
| React ／ react-dom | `^19.2.6` | 盤點 |
| react-router-dom | `^7.18.2` | 盤點 |
| TypeScript | `~6.0.2` | 盤點 |
| Vite ／ @vitejs/plugin-react | `^8.0.12` ／ `^6.0.1` | 盤點 |
| Tailwind CSS | `^4.3.0` | 盤點 |
| ESLint | `^10.3.0` | 盤點 |
| Playwright ／ axe | `^1.56.0` ／ `4.13.0` | 盤點 |
| openapi-typescript | `7.13.0`（產生 `api.d.ts`、`ws-contract.d.ts`） | 盤點 |

**落差**：`aidlc/spaces/default/memory/team.md` 的 Code Style 寫「TypeScript + React 18」，`package.json` 實為 React 19。

## LLM 與外部服務

| 項目 | 用途 | 證據 |
|---|---|---|
| OpenRouter Decisions API（`typesafe/jev-1.14`，ADR-0024） | 部署環境的意圖路由 | 實讀（`langgraph_runtime.py`、`intent_routing_decisions.py` 檔頭） |
| OpenRouter chat（預設模型 `google/gemini-3.7-flash`） | 其他 LLM 路徑的預設 | 實讀（`langgraph_runtime.py:24`） |
| `ChatAnthropic`（經 `ANTHROPIC_BASE_URL`） | A1 design agent（openrouter 路徑） | 實讀（`design_agent.py:186-195`） |
| 本機 `claude` CLI | `LLM_PROVIDER=claude-code` 的開發路徑 | 實讀（`langgraph_runtime.chat_model`） |
| PostgreSQL | 主資料庫 | 盤點 |
| Redis | 大腦 session 與工作項 | 盤點 |
| n8n | 架構圖 icon 取得（`CLAUDE.md`、`LOCAL-DEV.md` 所述） | 盤點 |

## 基礎設施與交付

Docker（backend／frontend 映像）、docker compose（`docker-compose.yml`、`deploy/docker-compose.deploy.yml`、`deploy/docker-compose.test.yml`）、Cloudflare Tunnel 對外、GitHub Actions（`ci.yml`、`deploy.yml`）與 gh-aw agentic workflows〔盤點〕。
