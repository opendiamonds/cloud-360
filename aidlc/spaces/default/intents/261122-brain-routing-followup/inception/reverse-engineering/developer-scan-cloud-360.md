# Developer 掃描結果 — cloud-360（intent `brain-routing-followup`）

> 掃描日期：2026-11-22（`date -u` 取值 `2026-11-22T14:15:13Z`）；基準 HEAD `2ad499a`（`2ad499aab0e32a034a3d0c034a3b0a3f844556bb`）加上工作樹中**未 commit** 的修正（`git diff --stat`：10 檔、+207／−18）。
> 廣度：使用者選 Full rescan（整個 repo）；深度：Minimal。下列每項事實標註取得方式：**〔實讀〕**＝開檔逐行讀過；**〔盤點〕**＝只看檔名、`grep` 輪廓、行數或 import；**〔執行〕**＝實際跑過指令的結果。

## Developer Code Scan Results

### Scan Coverage
- **Analyzed deeply**（整檔逐行讀過）:
  - `backend/services/intent_routing.py`
  - `backend/services/intent_routing_decisions.py`
  - `backend/services/intent_routing_port.py`
  - `backend/services/intent_routing_context.py`
  - `backend/services/work_orchestrator.py`
  - `backend/services/work_orchestrator_capabilities.py`
  - `backend/services/design_agent.py`
  - `backend/services/langgraph_runtime.py`
  - `frontend/src/components/brain/WorkItemList.tsx`
  - `frontend/src/components/brain/ClarifyCandidates.tsx`
- **Skimmed only**（只讀部分區段、輪廓或 import，**不得**視為已驗證）:
  - `backend/services/brain_gateway.py`——只讀 1–127、499–606、1294–1660、1900–2010 行；127–499、606–1294、1660–1900 未讀（握手、名稱推送、`_on_select`、記憶寫入）
  - `backend/services/work_orchestrator_rules.py`——只讀常數、`plan_waits`、`event_for_dependency_terminal`、`PHRASES` 的 diff 區段
  - `backend/services/intent_routing_types.py`、`intent_routing_predicate.py`、`intent_routing_parser.py`、`intent_routing_config.py`、`intent_routing_errors.py`——只看 import 與被引用的符號
  - `backend/services/session_store.py`、`session_types.py`、`session_errors.py`、`backend/services/session_scripts/*.lua`——只取 `grep` 輪廓（方法名、常數）
  - `backend/services/brain_gateway_rules.py`、`backend/services/agent_router.py`（只 `grep` 了 `thread_id`／`request_key`）
  - `frontend/src/components/brain/` 其餘 15 支 `.tsx`——只看 import／export
  - `backend/tests/` 的四支變更測試——**未讀內容**，只有〔執行〕結果
  - 其餘全 repo：`backend/`（cost、iac、mcp_bridge、scripts、prompts、lenses、其餘 services）、`frontend/src/`（pages、brain、cost、iac、memory、projects 等）、`frontend/tests/e2e/`、`deploy/`、`scripts/`、`.github/workflows/`（含 `aidlc-sync-*`，屬專案自建同步 workflow）、根目錄 `*.md`／`*.sql`／`openapi.json`／`ws-contract.json`——只到目錄與檔名盤點
- **Left out**（依 code-analysis-guide「What to Skip」與 brief 排除，未開啟）:
  - `frontend/node_modules/`、`backend/.venv/`（相依資料夾）
  - `backend/.hypothesis/`、各處 `__pycache__/`、`.pytest_cache/`（工具快取）
  - `frontend/dist/`（建置輸出）
  - `.claude/`、`.kiro/`、`.codex/`、`.cursor/`、`.opencode/`、`.aidlc/`、`aidlc/`（AI-DLC 安裝與工作區）
  - `.agents/rules/ai-dlc.md`、`.agents/rules/aidlc-engine.md`（AI-DLC 規則檔）

### Packages Found
- `backend` — 應用服務 — Python — FastAPI 後端（`backend/main.py` 掛 13 個 router，含 `/api/brain` WebSocket）〔盤點：`grep include_router`〕
- `backend/mcp_bridge` — 獨立行程 — Python — `python -m mcp_bridge`（MCP server）〔盤點〕
- `frontend` — SPA — TypeScript／React — Vite 建置〔盤點：`package.json`〕
- `deploy` — 部署資產 — docker compose／shell — staging 部署〔盤點〕
- `scripts` — 工具腳本 — Python — repo contract／env contract／TCMS／aidlc 同步〔盤點〕

### Build System
- **Type**: pip（`backend/requirements.txt`）＋ npm（`frontend/package.json`）＋ Docker（`backend/Dockerfile`、`frontend/Dockerfile`）
- **Config Files**: `backend/requirements.txt`、`frontend/package.json`、`frontend/vite.config.ts`、`frontend/tsconfig*.json`、`frontend/eslint.config.js`、`docker-compose.yml`、`deploy/docker-compose.deploy.yml`、`deploy/docker-compose.test.yml`
- **Build Dependencies**: `frontend` 的 `gen:types`／`gen:ws-types` 讀 repo 根 `openapi.json`／`ws-contract.json`（由 `backend/scripts/dump_openapi.py`、`dump_ws_contract.py` 產生）〔盤點〕

### APIs Discovered
- REST — `backend/main.py` 的 13 個 `include_router` — `openapi.json` 共 68 個 path〔執行：`json.load` 計數〕
- WebSocket — `/api/brain/ws`（`brain_gateway.router`）— 訊息型別定義在 `brain_ws_contract.py`、對外契約 `ws-contract.json`〔實讀 gateway 檔頭〕
- 出站 HTTP — OpenRouter Decisions API `https://openrouter.ai/api/alpha/decisions`（`langgraph_runtime.py:20`）〔實讀〕
- 同進程 ASGI — `CapabilityClient` 以 `httpx.ASGITransport` 呼叫自身的 A1／A3／C1 端點（`work_orchestrator_capabilities.py:244-252`）〔實讀〕

### Frameworks & Libraries
- FastAPI — `==0.111.0`（精確釘選）— Web 框架〔盤點 requirements〕
- Pydantic — `==2.13.4` — 契約模型〔盤點〕
- LangGraph／langchain-core／langchain-anthropic／langchain-openai — 未釘版 — LLM 圖執行〔盤點〕
- httpx — 未釘版 — 出站與 ASGI 傳輸〔盤點〕
- redis、websockets — 未釘版 — session store、WebSocket〔盤點〕
- hypothesis — 未釘版 — PBT〔盤點〕
- mcp `==2.3.0`、sse-starlette `==3.0.3`、mcp-types `==2.3.0` — MCP bridge〔盤點〕
- React `^19.2.6`、react-router-dom `^7.18.2`、Vite `^8.0.12`、TypeScript `~6.0.2`、Tailwind `^4.3.0`、Playwright `^1.56.0`〔盤點 package.json〕

### Test Coverage
- **Test Directories**: `backend/tests/`（137 支 `test_*.py`，`git ls-files` 計數）、`backend/tests_pg/`、`backend/tests_redis/`、`frontend/tests/e2e/`（12 支 spec）〔盤點〕
- **Test Frameworks**: Python `unittest`（本機無 pytest，`python3 -m pytest` 回 `No module named pytest`）＋ Hypothesis；前端 Playwright＋axe〔執行／盤點〕
- **Coverage Config**: 未見 coverage 設定檔〔盤點，未逐檔搜尋〕
- **執行結果**：`python3 -m unittest tests.test_intent_routing_decisions tests.test_work_orchestrator_capabilities tests.test_work_orchestrator_flow tests.test_work_orchestrator_rules` → `Ran 109 tests … OK`〔執行，2026-11-22，含未 commit 修正〕

### Code Quality Indicators
- **Linting**: 前端 ESLint（`frontend/eslint.config.js`）；後端未見 linter 設定〔盤點〕
- **CI/CD**: `.github/workflows/ci.yml`（job：gate、repo-contract、frontend、backend、memory-schema、concurrency、docker-build；backend job 用 Python 3.12）、`deploy.yml`（deploy、rollback、notify）、多支 gh-aw `*.md`＋`*.lock.yml`〔盤點 `grep` job 名〕
- **Documentation**: 深讀檔案皆有繁中模組 docstring 並逐條引用 BR／NFR 編號〔實讀〕

### Technical Debt Signals
- `intent_routing_decisions.py:66-67` 註解要求「**換字就要重新量測（NFR1）**，實測表（ADR-0024）的數字只對這組文字成立」；本次修正把 `CONTINUATION_RULE` 附加到 `PRIMARY_INSTRUCTIONS` 與三題 `wants_*`，屬於換字，ADR-0024 的量測數字不再保證成立〔實讀＋diff〕
- `DecisionsRoutingPort` 每輪新建 `httpx.AsyncClient`（`langgraph_runtime.py:211`），`intent_routing.py:347-349` 自述 P-4 連線重用在此路徑未落實〔實讀〕
- `design_agent.py:262` 的 `MemorySaver()` 為模組層、行程內記憶；架構設計的多輪對話記憶不跨重啟、不跨 worker〔實讀〕
- `work_orchestrator._recover`（`work_orchestrator.py:510-535`）只依被等待者的 `status` 推進等待者；「等你回覆」被記為 `完成`，若行程在 CAS 寫入 `完成` 之後、`_advance_dependents` 之前中止，復原掃描會把等待者當成「依賴完成」放行，在舊圖上執行〔實讀推導，未實測〕
- `build_state` 每則歷程截 400 字（`message_chars=400`）；A1 的提問若長於 400 字，選項清單可能被截掉〔實讀推導〕

## Handoff Summary
- **Intent-relevant finding**: 兩個症狀的根因都在深讀範圍內並已由工作樹 diff 處理：(1) `DecisionsRoutingPort.route`（`intent_routing_port.py:562-567`）原本不把 `recent_messages` 交給 `build_state`，而 `IntentRouter.classify` 其實已取好最後 6 則歷程（`intent_routing.py:252-282`、`:484-491`）——修正後 `build_state` 帶入最後 `message_limit=6` 則、每則截 400 字，並在 `primary`／`wants_*` 指示附上 `CONTINUATION_RULE`。歷程之所以含架構設計的提問，是因為 `GatewaySink.emit_turn` 在推播後以 `append_assistant_background` 寫回該段（`brain_gateway.py:570-597`、`:1906-1910`），而使用者本句在 `classify` **之後**才寫入（`:1424`）。(2) `judge_a1`（`work_orchestrator_capabilities.py:140-162`）原本「無 xml 即 `a1_no_xml`」；修正後「無 xml 但有文字」回 `awaiting_reply=True`，編排層 `_complete_awaiting_reply`（`work_orchestrator.py:1097-1116`）把工作項轉 `完成`、不存圖、不寫 procedure 記憶，並以 `dependency_awaiting_reply` 使等待它的檢視／成本失敗。〔實讀＋執行：109 測試 OK〕
- **Risks / follow-up**:
  - 架構設計能接續，依賴 `agent_router.py:153` 的 `thread_id=f"user-{id}-design"` 與 `design_agent.py:262` 的行程內 `MemorySaver`；編排層每次只送當句（`work_orchestrator_capabilities.py:302`）。重啟或多 worker 時接續會斷，且與工作區頁共用同一 thread。〔實讀〕
  - 修改了 ADR-0024 量測過的 Decisions 指示文字，需重新量測（NFR1）。〔實讀〕
  - 復原掃描無法區分「完成」與「等你回覆」（見 Technical Debt Signals）。〔實讀推導〕
  - 前端 `WorkItemList.tsx` 對 `完成` 不顯示任何細節，「等你回覆」只出現在對話訊息，工作項徽章顯示 `完成`。〔實讀〕
  - `team.md` 寫 React 18，`frontend/package.json` 為 `^19.2.6`。〔盤點〕
  - `project.md` 一條學習記錄宣稱 codekb 正本是 `codekb/cloud/`，本次 brief 指定 `cloud-360`；由 conductor 處理發布目標。
