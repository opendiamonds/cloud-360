# 元件清冊（Component Inventory）

> Reverse Engineering 合成產物｜repo `cloud`｜掃描日 2026-10-01｜intent `261001-a2-langgraph`｜mode **Focused merge（STALE）**
> 元件名稱＝下列 H3；`## Scope of Analysis` 的 `analyzed.components` 僅列**本輪深讀**者。其餘元件保留前一版散文，驗證深度標為 shallow／inventory。

## 後端元件

### backend-app-shell

- **深度**：deep（本輪重讀 `main.py`）
- **職責**：CORS、startup（`configure_provider_env` + `init_db`）、router 掛載（含 `agent_router`／`review_router` → `/api/architecture`）。
- **依賴**：`services.*` routers、`cost.cost_router`、`llm_provider`。
- **健康**：healthy。
- **本輪**：確認 Assessment 路徑掛載於 L52–53；dotenv + provider 於啟動配置。

### persistence-orm

- **深度**：shallow（前一版 deep，STALE demote）
- **職責**：11 張 ORM 表與 `_ensure_*_schema()`。
- **健康**：at-risk（DDL 雙軌）。詳見前一版。

### cost-domain

- **深度**：shallow（前一版 deep，STALE demote）
- **職責**：C1 成本全域。相依方向仍為 `main → cost → services`。
- **健康**：at-risk。詳見前一版與 `dependencies.md`。

### architecture-generation

- **深度**：deep（本輪：`agent_router`、`design_agent`）
- **職責**：A1 產圖 SSE；**`design_agent` 已為 LangGraph**（`StateGraph` + `ToolNode` + `ChatAnthropic`），非 Claude Agent SDK。
- **依賴**：`llm_provider.get_design_model_name`、`diagram_builder`（skim）、n8n、`MemorySaver`。
- **健康**：at-risk。全域 `_progress_queue`；`MemorySaver` 進程內；`diagram_builder` 仍 oversized（未本輪逐行）。

### langgraph-runtime

- **深度**：deep（本輪新增）
- **職責**：共用 LangGraph／OpenRouter helpers（`openrouter_chat_model`／`ChatOpenAI`）。
- **依賴**：惰性 `langchain-openai`（**未**列入 `requirements.txt`）。
- **健康**：degraded（對 Assessment）。**未被** `review_agent`／`wa_lens_engine`／`design_agent` import；與 `llm_provider` Anthropic-compat 形成雙適配。

### wa-review

- **深度**：deep（本輪：`review_router`、`review_orchestrator`、`review_agent`、`wa_score_service`、`wa_collab_orchestrator`、`wa_rule_engine` 契約面）
- **職責**：A3 評核 SSE、分數、collab；規則純函式；**Review 建議仍 Claude Agent SDK**。
- **依賴**：`llm_provider.get_review_model_name`、`claude_agent_sdk`（執行時）、ORM、lens／design 呼叫。
- **健康**：at-risk。本 intent 主要重構面；`wa_rule_engine` 各雲規則細節未逐條。

### lens-management

- **深度**：deep（本輪：`wa_lens_engine.answer_lens_with_agent`）；`lens_router` skim
- **職責**：Lens 作答（SDK + MCP `emit_lens_answers`）與 CRUD（router 未深讀）。
- **依賴**：`get_model_name`、`agent_sdk_env`、`claude_agent_sdk`、`backend/lenses/`。
- **健康**：at-risk（agent 路径）。CRUD 面未本輪驗證。

### collaboration

- **深度**：shallow／inventory
- **職責**：架構圖 CRUD、WS；Assessment 用 `GET /api/collab/diagrams` 選圖。
- **健康**：at-risk（商業邏輯在 handler；私有函式被 cost 引用——前一版）。

### identity-and-rbac

- **深度**：shallow
- **職責**：JWT、故事級權限。C1／A3 story seeds 見前一版。

### llm-gateway

- **深度**：deep（本輪：`llm_provider`、`llm_limits`）
- **職責**：`LLM_PROVIDER`＝`openrouter`（預設）｜`cli`；模型 getter（design／一般／review）；token／XML 限額；`configure_provider_env`／`agent_sdk_env`。
- **依賴**：環境變數；SDK 路徑寫入 CLI env。LangGraph Design／`langgraph_runtime` **不**經 `agent_sdk_env`。
- **健康**：at-risk。頂註仍寫「全部經 SDK」——**過時**；Design／runtime 已例外。

### openapi-contract

- **深度**：deep（本輪：architecture 評核／collab 相關 paths）
- **職責**：HTTP 契約凍結快照。
- **健康**：healthy（drift 閘門；全表列舉屬前一版，本輪焦點子集）。

## 前端元件

### frontend-routing

- **深度**：deep（本輪重讀 `App.tsx`）
- **職責**：路由與落地頁；含 `/assessment`。
- **健康**：at-risk（根導向優先 C1——前一版）。

### assessment-page

- **深度**：deep（本輪新增：API／SSE／優化流程）
- **職責**：`/assessment` 儀表板——發起評核、collab、retry、選圖。
- **依賴**：`/api/architecture/*` reviews／generate-wa-collab；`/api/collab/diagrams`。
- **健康**：at-risk。大型頁面；UI 版面其餘僅結構性閱讀。

### frontend-cost-support / frontend-cost-page / frontend-shell / frontend-feature-pages

- **深度**：shallow（前一版或 inventory）
- **職責**：見前一版。`frontend-feature-pages` 中 Assessment 細節改由 `assessment-page` 承載。

## 契約、CI、部署、測試（前一版保留｜shallow）

### contract-validators / ci-core / agentic-workflows / deploy-workflow / deployment-compose / deployment-config / schema-sql-assets / ops-and-sync-scripts / backend-test-suite / frontend-e2e-suite / static-prompt-assets

前一版盤點仍有效作散文參考；**本輪未重驗證**。與 LangGraph 相關的測試增量：`test_langgraph_runtime.py`、`test_langgraph_migration.py`、`scripts/smoke_langgraph_openrouter.py`（本輪 deep）；`test_llm_provider.py` 未深讀。

## 外部與基礎設施

PostgreSQL、embed.diagrams.net、**OpenRouter 或 claude CLI**、n8n、雲價目／Calculator（C1）、Cloudflare Tunnel、Kiwi TCMS。Backend 映像內 Node 22 + `@anthropic-ai/claude-code` 仍為 Review／Lens（及任何殘留 SDK）所需。
