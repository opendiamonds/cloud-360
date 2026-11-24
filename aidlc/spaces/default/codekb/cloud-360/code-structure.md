# 程式結構 — cloud-360

> 新鮮度：2026-11-22。目錄樹為〔盤點：`git ls-files`，排除 AI-DLC 安裝與工作區後共 654 個追蹤檔〕；「大腦模組分層」為〔實讀〕。

## 頂層目錄

| 路徑 | 內容 | 追蹤檔數 |
|---|---|---|
| `backend/services/` | 業務服務、router、大腦（路由、閘道、編排、session） | 73 |
| `backend/cost/` | C1 估價表解析、建議、公開價目 client | 25 |
| `backend/iac/` | D IaC 產生 | 14 |
| `backend/mcp_bridge/` | 獨立 MCP server 行程 | 19 |
| `backend/scripts/` | OpenAPI／WS 契約 dump、遷移、記憶清除 SQL | 15 |
| `backend/prompts/`、`backend/lenses/` | LLM system prompt、draw.io 範本、WA lens | 7、3 |
| `backend/tests/`、`tests_pg/`、`tests_redis/` | 單元／整合測試 | 145、8、2 |
| `frontend/src/` | React SPA | 131 |
| `frontend/tests/` | Playwright e2e 與 fixture | 14 |
| `deploy/` | compose、render-env、cloudflared | 6 |
| `scripts/` | repo／env contract、TCMS、aidlc 同步 | 11 |
| `.github/workflows/` | CI、deploy、gh-aw | 37 |
| 根目錄 | `schema.sql`、`schema_rbac.sql`、`openapi.json`、`ws-contract.json`、`DEPLOY.md`、`LOCAL-DEV.md`、`TESTING.md` | — |

## 大腦模組分層〔實讀〕

路由層採六層分解（`intent_routing.py` 檔頭表）：

| 層 | 檔案 | 純度 |
|---|---|---|
| L1 guard | `intent_routing.py`（呼叫 `prompt_guard`） | 純 |
| L0 fetch | `intent_routing.py` `fetch_routing_context`——唯一讀取 I/O | 不純 |
| L2 context | `intent_routing_context.py`（工具呼叫 prompt、名稱整理、`target_choices`） | 純 |
| L3 port | `intent_routing_port.py`（Decisions／工具呼叫）——唯一出站 I/O | 不純 |
| L4 parser | `intent_routing_parser.py`（工具呼叫）、`intent_routing_decisions.py`（Decisions） | 純 |
| L5 predicate | `intent_routing_predicate.py`（PBT 落點） | 純 |

編排層：`work_orchestrator.py`（狀態、CAS、背景執行）＋ `work_orchestrator_rules.py`（狀態機、文案 `PHRASES`、等待規劃）＋ `work_orchestrator_capabilities.py`（ASGI client 與 SSE 判定純函式）。

閘道層：`brain_gateway.py`（連線、回合、sink）＋ `brain_gateway_rules.py`（規則純函式，〔盤點〕）＋ `brain_ws_contract.py`（契約模型，〔盤點〕）。

Session 層：`session_store.py`＋`session_types.py`＋`session_scripts/*.lua`（Redis 原子操作）〔盤點〕。

## 檔案分類（依 code-analysis-guide）

| 類別 | 代表檔 |
|---|---|
| Controller/Handler | `*_router.py`、`brain_gateway.py` |
| Service/UseCase | `work_orchestrator.py`、`intent_routing.py`、`design_agent.py`、`*_service.py` |
| Model/Entity | `backend/models.py`、`*_types.py`、`brain_ws_contract.py` |
| Repository/DAO | `session_store.py`、`*_facade.py` |
| Utility/Helper | `intent_routing_context.py`、`intent_routing_decisions.py`、`work_orchestrator_rules.py`、`langgraph_runtime.py` |
| Configuration | `intent_routing_config.py`、`llm_provider.py`、`env_bootstrap.py` |
| Migration | `schema.sql`、`schema_rbac.sql`、`backend/scripts/run_*_migration.py` |
| Test | `backend/tests/**`、`frontend/tests/e2e/**` |

只有「大腦模組分層」為實讀，其餘分類依檔名歸類〔盤點〕。

## 程式慣例（深讀範圍內觀察到）〔實讀〕

- `from __future__ import annotations`、完整型別標註、繁中 docstring 逐條引用 BR／NFR 編號。
- 模組層不綁可變字面值（tuple／frozenset），`questions`／tool schema 每次呼叫新建（`NFR3.67`，由 `test_intent_routing_structure.py` 以 AST 鎖住，該測試〔盤點〕）。
- 例外分型、不靜默：外部邊界 `except` 一律記 log 並分型或降級。
- log 只記白名單欄位，不記使用者文字或 token。
