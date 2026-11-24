# 元件清單 — cloud-360

> 新鮮度：2026-11-22。**「深讀元件」表的每一列都是整檔實讀過的**，其名稱即 `reverse-engineering-timestamp.md` 的 `analyzed.components`。「盤點元件」表只依檔名、import 與部分區段，**不得**當成已驗證。

## 深讀元件〔實讀〕

| 元件 | 檔案 | 職責 | 依賴 | 被誰呼叫 |
|---|---|---|---|---|
| `intent-router` | `backend/services/intent_routing.py` | `K-10` `IntentRouter.classify`：prompt_guard 前置 → 取該段最後 6 則歷程與作業對象、讀語意／程序記憶（不可用時降級、`MemoryForbidden` 原樣上拋）→ 呼叫路由 port → `decide()` → 寫觀測 log | `intent_routing_port`、`intent_routing_context`、`intent_routing_decisions`、`intent_routing_predicate`、`prompt_guard`、`MemoryFacade`（注入） | `brain_gateway`（每段一個實例，`brain_gateway.py` `build_brain_gateway`） |
| `routing-decisions` | `backend/services/intent_routing_decisions.py` | Decisions 路徑純函式：`build_questions`、`build_state`（本 intent 起帶最近 6 則對話＋`CONTINUATION_RULE`）、`parse_answers`、`routing_from_answers`（多意圖依固定先後；單一意圖 `primary=unclear` 或信心＜門檻 → 強制反問）、`resolve_referent`（指名信心 ≥ 0.8） | `intent_routing_types`、`work_orchestrator_rules.capability_name` | `routing-ports`、`intent-router`（`effective_threshold`） |
| `routing-ports` | `backend/services/intent_routing_port.py` | L3 唯一出站點；`select_routing_port` 依 `LLM_PROVIDER` 選 `DecisionsRoutingPort`（openrouter）或 `ToolCallingRoutingPort`（claude-code）；`CallBudget`；`classify_transport_failure` 分型為 `LlmUnavailable`／`LlmBudgetExceeded`／`MalformedRouting` | `langgraph_runtime`、`intent_routing_context`、`intent_routing_decisions`、`intent_routing_parser` | `intent-router` |
| `routing-context` | `backend/services/intent_routing_context.py` | 工具呼叫路徑的 prompt 組裝（最後 6 則、每則 400 字、記憶 5 筆）、`sanitize_target_name`、`target_choices`（上限 50）、`format_work_target` | `intent_routing_types` | `routing-ports`、`intent-router` |
| `work-orchestrator` | `backend/services/work_orchestrator.py` | `K-11`：`dispatch` 建工作項（上限 5 個進行中）、背景執行 A1／A3／C1、CAS 寫入、看門逾時、在途存檔 shield、復原掃描、等待者推進；本 intent 新增 `_complete_awaiting_reply` 與 `_advance_dependents(as_status, failure_phrase)` | `work_orchestrator_rules`、`capability-client`、`SessionStore`、`HierarchyFacade`、`MemoryFacade` | `brain_gateway` |
| `capability-client` | `backend/services/work_orchestrator_capabilities.py` | `CapabilityClient`（ASGI、使用者 token、每次新建）；`parse_sse`、`judge_a1`（本 intent 新增 `awaiting_reply`）、`judge_a3`、`judge_advice_snapshot` | `httpx` | `work-orchestrator` |
| `design-agent` | `backend/services/design_agent.py` | A1 LangGraph 圖（agent ↔ tools），`draw_architecture_diagram` 工具產 XML 經 `ProgressChannel` 發出；需求不足時以文字提問；`MemorySaver` 模組層、`thread_id` 由呼叫端給 | `diagram_builder`、`langgraph_runtime.chat_model`、`progress_channel`、`llm_provider` | `agent_router`（`/api/architecture/generate`） |
| `langgraph-runtime` | `backend/services/langgraph_runtime.py` | 所有 LLM 路徑的共同入口：`chat_model`（provider 選擇）、`openrouter_chat_model`、`openrouter_decide`（Decisions API，僅可重試 408/429/5xx） | `httpx`、`langchain_openai`、`llm_provider` | `routing-ports`、`design-agent`、其他 LLM 路徑〔盤點〕 |
| `brain-ui-work-items` | `frontend/src/components/brain/WorkItemList.tsx` | 工作項清單：狀態徽章、`等待中` 顯示「在等」、`失敗` 顯示 `failureReason`、`已停掉` 顯示副作用；`處理中`／`等待中` 提供「不是這個」 | `brainSession` | `ConversationView`〔盤點〕 |
| `brain-ui-clarify` | `frontend/src/components/brain/ClarifyCandidates.tsx` | 反問候選（intent／target 兩種）、「就是這個」與「都不是」 | `brainSession` | `ConversationView`〔盤點〕 |

## 盤點元件（未深讀）

| 元件 | 位置 | 依檔名／部分區段推定的職責 |
|---|---|---|
| `brain-gateway` | `backend/services/brain_gateway.py`（部分實讀，見 timestamp） | WebSocket 端點、回合管理、反問、交辦、`GatewaySink`、歷程寫回 |
| `brain-gateway-rules` | `backend/services/brain_gateway_rules.py` | 段解析、對象比對、錯誤碼對照 |
| `work-orchestrator-rules` | `backend/services/work_orchestrator_rules.py`（部分實讀） | 狀態機、`PHRASES`、`plan_waits`、能力名稱 |
| `session-store` | `backend/services/session_store.py`、`session_types.py`、`session_scripts/` | Redis 工作階段、歷程（每段上限）、工作項原子更新 |
| 路由其他純函式層 | `intent_routing_types.py`、`_predicate.py`、`_parser.py`、`_config.py`、`_errors.py` | 型別、述詞（PBT）、工具呼叫解析、設定、例外 |
| `agent-router` | `backend/services/agent_router.py` | `/api/architecture/generate`；`thread_id=f"user-{id}-design"`（第 153 行，實讀） |
| 其他 backend 服務 | `backend/services/*`（review、wa、hierarchy、membership、memory、requirement_field、rbac、collab、iac、cost） | 各業務能力 |
| `mcp-bridge` | `backend/mcp_bridge/` | 獨立 MCP server 行程 |
| 前端 brain 其餘元件 | `frontend/src/components/brain/` 其餘 15 支 | 對話、輸入、脈絡列、物件選擇器 |
| 前端其餘 | `frontend/src/pages/`、`brain/`、`cost/`、`iac/`、`memory/`、`projects/` | 各頁面與 API client |
