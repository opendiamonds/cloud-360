# 相依關係（Dependencies）

> Reverse Engineering 合成產物｜repo `cloud`｜掃描日 2026-10-01｜intent `261001-a2-langgraph`｜mode **Focused merge（STALE）**
> 成本套件內部邊與八類掛鉤保留前一版散文；本輪補上 Assessment／LangGraph／`llm_provider` 邊。

## 跨套件相依方向

```
backend/main.py ──► backend/cost/ ──► backend/services/
                └─► backend/services/ ──► models / database / llm_provider
```

`services` 仍**不** import `cost.*`（前一版事實；本輪未反證）。

## Assessment／Agent 相依（本輪）

| 來源 | 目標 | 備註 |
|---|---|---|
| `main.py` | `agent_router`、`review_router`、`lens_router`、`configure_provider_env` | 掛載與啟動 |
| `review_orchestrator` | `wa_rule_engine`、`wa_lens_engine`、`review_agent` | 評核三階段 |
| `wa_collab_orchestrator` | `design_agent`、`wa_score_service`、`review_agent` | 雙框架 |
| `wa_score_service` | 規則 + lens agent | |
| `design_agent` | `llm_provider`、LangGraph、`ChatAnthropic` | **不** import `langgraph_runtime` |
| `review_agent`／`wa_lens_engine` | `claude_agent_sdk`、`llm_provider`、`llm_limits.agent_sdk_env` | **不** import `langgraph_runtime` |
| `langgraph_runtime` | `langchain-openai`（惰性） | **無** Assessment 消費者 |
| `llm_provider` | 環境變數映射 | Design／SDK 共用 Anthropic-compat |
| `AssessmentPage` | `/api/architecture/*`、`/api/collab/diagrams` | 無 model 參數 |

## 雙 OpenRouter 適配

1. **`llm_provider._configure_openrouter_env`**：設 `ANTHROPIC_BASE_URL`／`ANTHROPIC_AUTH_TOKEN`，供 SDK 與 Design `ChatAnthropic`。
2. **`langgraph_runtime.openrouter_chat_model`**：`ChatOpenAI` + OpenAI-compatible base——與上者平行，未统一。

## 外部套件共用（更新）

| 套件 | Assessment／A1 消費者 | 可否隨 A3 迁 LangGraph 移除 |
|---|---|---|
| `langgraph`／`langchain-*` | `design_agent`（已用）；runtime helpers | 不可移除；应補 pin／補 `langchain-openai` 若採用 runtime |
| `claude-agent-sdk` + 映像 `claude` CLI | `review_agent`、`wa_lens_engine`（+ C1） | **迁完 Review／Lens 且 C1 另案處理後**才可評估移除 |
| `httpx` | `llm_provider` 等 | 不可 |

## `backend/cost/` 內部與八類掛鉤（前一版保留｜shallow）

成本套件 DAG、`pricing_client` 最小存活 8 檔、CI／env／DDL／RBAC／前端／OpenAPI／測試八類掛鉤——見前一版完整表。本輪未重驗；STALE 後僅作散文參考。

## 建置期相依

`openapi.json` ← dump；`api.d.ts` ← gen:types；`deploy/.env` ← `render-env.sh`；DB init ← `schema_rbac.sql`（僅空 volume）。
