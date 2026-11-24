# API 文件 — cloud-360

> 新鮮度：2026-11-22。REST 清單為〔盤點〕（`main.py` 的 `include_router` 與 `openapi.json` 計數）；大腦相關契約為〔實讀〕。完整 REST 規格以 repo 根 `openapi.json` 為準（CI 以 `dump_openapi.py --check` 鎖住漂移）。

## REST（`openapi.json` 共 68 個 path，〔執行〕計數）

| 前綴 | router | 證據 |
|---|---|---|
| `/api/architecture` | `agent_router`、`review_router`、`lens_router` | 盤點 |
| `/api/auth` | `user_router` | 盤點 |
| `/api/collab` | `collab_router` | 盤點 |
| `/api/cost/v1` | `estimate_intake_router`、`advice_stream_router` | 盤點 |
| `/api/hierarchy` | `hierarchy_router` | 盤點 |
| `/api/membership` | `membership_router` | 盤點 |
| `/api/memory` | `memory_router` | 盤點 |
| `/api/requirements` | `requirement_field_router` | 盤點 |
| `/api/iac` | `iac_router` | 盤點 |

### 大腦編排層實際呼叫的端點〔實讀：`work_orchestrator_capabilities.py:13-22`、`:280-350`〕

| 用途 | 請求 | 回應被讀的欄位 |
|---|---|---|
| 讀圖 | `GET /api/collab/diagrams/{id}` | `title`、`xml_data`、`updated_at` |
| A1 產圖 | `POST /api/architecture/generate`，body `{"messages":[{"role":"user","content":<requestText>}],"current_xml":<xml>}`，SSE | 事件 `type ∈ {message, xml, error, progress}` |
| 存圖 | `PUT /api/collab/diagrams/{id}`，body `{xml_data, title}` | 狀態碼 |
| A3 檢視 | `POST /api/architecture/reviews`，body `{diagram_id, save_diagram:false}`，SSE | `complete.overall_score`、`complete.findings` |
| C1 估價表 | `GET /api/cost/v1/sets?include_history=true&page=&page_size=50` | `items[].diagram_id`、`total` |
| C1 建議快照 | `GET /api/cost/v1/sets/{id}/advice` | `status`、`started_at`、`unavailable_reasons` 等 |

**A1 判定規則（`judge_a1`，本 intent 修改後）**：任一 `error` → `a1_failed`；有非空 `xml` → 取最後一份、成功；無 xml 但 `message` 文字非空 → `awaiting_reply=True`（不是失敗）；兩者皆無 → `a1_no_xml`。

## WebSocket `/api/brain/ws`〔實讀：`brain_gateway.py` 檔頭〕

| 項目 | 值 |
|---|---|
| 子協定 | `cloud360.brain.v1` ＋ `bearer.<jwt>`；不讀 query string |
| 首則訊息 | `hello{v:1}`（10 秒內），回 `ready{protocolVersion:1}` |
| 關閉碼 | 4401／4403／4400／1011 |
| 伺服器訊息型別（本次讀到的） | `token`、`clarify`、`cost_card`、`done`、`error`、`work_items`、`work_target`、`sharing_mode`、`ready` |
| 客戶端訊息（本次讀到的處理器） | `user_message`、`select_clarify_candidate`、`set_work_target`、`set_sharing_mode`、`correct_work_item` |

完整訊息形狀以 `ws-contract.json`（由 `backend/scripts/dump_ws_contract.py` 產生）為準，本次未讀〔盤點〕。

### 本 intent 相關的伺服器訊息文案〔實讀：`work_orchestrator_rules.py` diff〕

| 鍵 | 文案 | 何時送出 |
|---|---|---|
| `awaiting_reply` | `{label}：架構設計在等你回覆上面的問題，直接回答即可` | A1 回了提問、沒有產圖 |
| `dependency_awaiting_reply` | `前一項{dependency_label}還在等你回覆，這一項沒有執行` | 等待該架構設計的檢視／成本被結束時的 `failureReason` |

## 同進程內部契約〔實讀〕

| 契約 | 簽章 | 消費端 |
|---|---|---|
| `K-10` `IntentRouter.classify` | `async classify(principal, session, text, *, turn_id="", target_names=None, target_catalog=()) -> IntentDecision`；raises `LlmUnavailable`、`LlmBudgetExceeded`（另有 `MalformedRouting`、`PlatformSelfModificationRefused` 等） | 只有 `brain_gateway` |
| `K-11` `WorkOrchestrator.dispatch／correct／list_items` | 見 `work_orchestrator.py` 檔頭表 | 只有 `brain_gateway` |
| 路由 port `route` | `route(*, text, work_target_hint, recent_messages, memory_notes, budget, target_catalog=()) -> RoutedClassification` | `IntentRouter` |
| `build_state`（本 intent 修改） | `build_state(*, user_text, work_target_hint=None, recent_messages=(), memory_notes=(), text_chars=4000, message_limit=6, message_chars=400, note_chars=400, note_limit=5) -> str` | `DecisionsRoutingPort` |

## 出站 API〔實讀：`langgraph_runtime.py`〕

| 目標 | 呼叫點 | 形狀 |
|---|---|---|
| OpenRouter Decisions `POST https://openrouter.ai/api/alpha/decisions` | `openrouter_decide` | `{model, state, questions}` → `answers`；`alpha` 路徑無穩定性承諾（ADR-0024） |
| OpenRouter chat（OpenAI 相容） | `openrouter_chat_model` | `ChatOpenAI` |
| 本機 `claude` CLI | `chat_model`（`LLM_PROVIDER=claude-code`） | `ClaudeCodeChatModel`（〔盤點〕） |
