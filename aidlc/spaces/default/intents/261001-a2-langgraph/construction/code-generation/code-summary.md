# Code Summary — A3 Assessment → LangGraph

> Intent `261001-a2-langgraph`｜code-generation（zero-Unit）

## 做了什麼

將 A3 Review 與 Offline Lens 的 LLM 執行路徑自 `ClaudeSDKClient`／MCP 迁徙至獨立 compiled LangGraph，經 `services.langgraph_runtime.openrouter_chat_model` 呼叫 OpenRouter。對外公開 API 與 SSE 契約不變。

### Review（`backend/services/review_agent.py`）

- 保留 `run_review_agent`（`AsyncIterator[str]`）、`load_review_system_prompt`、`fallback_suggestions_from_findings`、`_compact_payload`。
- 獨立 `StateGraph`；以 `stream_mode="messages"` 產出字串增量，供 orchestrator 映射 `suggestion_delta`。
- 模型：`get_review_model_name()`（預設 `google/gemini-3.7-flash`）。
- `RuntimeAuthError` → `RuntimeError(auth_error_message())`；空模型文字上拋；logger `cloud360.review_agent`。

### Lens（`backend/services/wa_lens_engine.py`）

- 重寫 `answer_lens_with_agent`：獨立 Lens graph；模型回 JSON `{question_id, selected_choice_ids}`，校驗後回 `dict[str, list[str]]`。
- 無 auth 時維持啟發式 fallback；空答案／硬失敗上拋；移除 MCP `emit_lens_answers`／SDK。
- Logger `cloud360.wa_lens_engine`。

### 依賴／映像／文件

- `backend/requirements.txt` 新增 `langchain-openai`。
- `backend/Dockerfile` 移除 Node／`@anthropic-ai/claude-code`。
- `DEPLOY.md`／`LOCAL-DEV.md` 同步：A3／映像不再需要 Claude CLI。

### FD 審查缺口（R-01～R-03）

- `rules.md`：BR3.2（secret）、BR3.3（`cloud360.*` logger）。
- `functional-spec.md`：retry 狀態轉換。
- FD `traceability.json`：NFR2.1→BR3.2、NFR1.2→BR3.3。

### 測試

- 新增 `backend/tests/test_a3_langgraph_migration.py`（串流 mock、答案形狀、無 SDK import）。
- 指令：`cd backend && python3 -m unittest tests.test_langgraph_runtime tests.test_review_agent tests.test_wa_lens_engine tests.test_a3_langgraph_migration -v` → **25 OK**。

## 刻意未改

- AssessmentPage／前端行為、`review_router` URL、SSE `suggestion_delta`。
- Design agent、cost_advice（既有 LangGraph）。
- DB schema／OpenAPI。
