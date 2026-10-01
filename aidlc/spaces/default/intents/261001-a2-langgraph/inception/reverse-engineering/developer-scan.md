## Developer Code Scan Results

> Intent `261001-a2-langgraph`｜Focused / Minimal｜掃描日 2026-10-01（擴界再掃：併入 `llm_provider`／`llm_limits`／`main.py`／`Dockerfile`）  
> Snapshot：`store_generation` sha256:8c2194a60a24d3f2438fa78b3f6f2f625b0f2983aee2bd3199531bebef71f57d；`source_fingerprint` git:81c5a1600194da8a5429a3103e1bc84e396ef08b  
> 產品面：Assessment 評估儀表板（路由 `/assessment`、story **A3**）。Intent 名稱含「A2」；OpenAPI 的 `generate` 說明另提及架構編輯權「A1／A2／A4」。本掃描以 Assessment／WA 評核 agent 路徑為準。

### Scan Coverage
- **Analyzed deeply**:
  - `backend/services/agent_router.py`
  - `backend/services/design_agent.py`
  - `backend/services/langgraph_runtime.py`
  - `backend/services/review_agent.py`
  - `backend/services/review_orchestrator.py`
  - `backend/services/review_router.py`
  - `backend/services/wa_score_service.py`
  - `backend/services/wa_collab_orchestrator.py`
  - `backend/services/wa_lens_engine.py`（含 `answer_lens_with_agent` 與 Claude SDK 路徑）
  - `backend/services/wa_rule_engine.py`（模組契約、`evaluate`／`parse_diagram_summary`／`detect_provider`；各雲規則細節未逐條審）
  - `backend/services/llm_provider.py`（擴界新增）
  - `backend/services/llm_limits.py`（擴界新增）
  - `backend/main.py`（擴界新增）
  - `backend/Dockerfile`（擴界新增）
  - `backend/tests/test_langgraph_runtime.py`
  - `backend/tests/test_langgraph_migration.py`
  - `backend/test_agent.py`
  - `backend/requirements.txt`
  - `frontend/src/App.tsx`
  - `frontend/src/pages/AssessmentPage.tsx`（API／SSE／優化流程；UI 版面其餘段落為結構性閱讀）
  - `scripts/smoke_langgraph_openrouter.py`
  - `openapi.json`（`/api/architecture/*` 評核與 collab 相關路徑）
- **Skimmed only**:
  - `backend/services/` 其餘模組（`lens_router.py`、`collab_router.py`、`diagram_builder.py`、`env_bootstrap` 呼叫點說明僅經 `main.py`）
  - `backend/cost/`（成本／LangGraph 消費路徑，屬他 intent）
  - `backend/prompts/`（prompt 檔名列舉）
  - `frontend/src/pages/`（非 Assessment 頁）
  - `backend/tests/`（除兩支 langgraph 測試外；含 `test_llm_provider.py` 未深讀）

### Packages Found
- `backend/` — FastAPI 應用 — Python — A1 產圖、A3 評核、WA collab、lens／規則引擎
- `frontend/` — Vite／React — TypeScript — Assessment 儀表板與 SSE 客戶端
- `scripts/` — 工具腳本 — Python — OpenRouter／LangGraph smoke

### Build System
- **Type**: pip（`backend/requirements.txt`）+ npm／Vite（frontend，本掃描未深讀 `package.json`）
- **Config Files**: `backend/requirements.txt`；Docker 建置 `backend/Dockerfile`
- **Build Dependencies**:
  - 映像：Python 3.12-slim + Node 22 + 全域 `@anthropic-ai/claude-code`（`Dockerfile` L6–18）+ `pip install -r requirements.txt`（L22–23）
  - pip 含 `langgraph`／`langchain-core`／`langchain-anthropic`；**不含**明確的 `claude-agent-sdk`／`langchain-openai` pin
  - 執行使用者 uid 10001（L27–30）；健康檢查打 `GET /`（L34–35）

### APIs Discovered
- REST + SSE — `openapi.json`／`agent_router`／`review_router` — Assessment 相關重點：
  - `POST /api/architecture/generate` — A1 Design Agent SSE
  - `POST /api/architecture/generate-wa-collab` — A1↔A3 雙 agent 優化 SSE
  - `POST /api/architecture/reviews` — 發起評核 SSE（`rules_done` → `lens_done` → `suggestion_delta` → `complete`）
  - `POST /api/architecture/reviews/detect-provider`
  - `POST /api/architecture/reviews/commit-collab`
  - `GET /api/architecture/reviews`、`GET|DELETE /api/architecture/reviews/{id}`
  - `POST /api/architecture/reviews/{id}/persist-diagram`
  - `POST /api/architecture/reviews/{id}/retry-suggestions` — SSE
  - `POST /api/architecture/diagrams/render-png`
  - Lens CRUD／驗證等（`/api/architecture/lens/*`）— 列於 OpenAPI，Assessment 可切 lens 分頁；agent 框架重構非首要
- 輔助 JSON — `GET /api/collab/diagrams`（Assessment 選圖；實作在 `collab_router`，**未深讀**）
- Wiring（深讀 `main.py`）：
  - `agent_router` → `/api/architecture`（L52）
  - `review_router` → `/api/architecture`（L53）
  - `lens_router` → `/api/architecture`（L54）
  - `collab_router` → `/api/collab`（L56）
  - 啟動時 `load_backend_dotenv(override=True)` + `configure_provider_env()`（L24–27、startup L47–49）

### Frameworks & Libraries
- `langgraph` — 未釘版本（`requirements.txt` L18）— Design Agent `StateGraph` 已採用
- `langchain-core` — 未釘版本（L19）— messages／tools
- `langchain-anthropic` — 未釘版本（L20）— Design Agent `ChatAnthropic`
- `langchain-openai` — **未列入** `requirements.txt` — `langgraph_runtime.openrouter_chat_model` 惰性 import
- `claude_agent_sdk` — **未列入** `requirements.txt` — `review_agent`、`wa_lens_engine.answer_lens_with_agent` 執行時 import；執行時另依賴映像內 `claude` CLI
- OpenRouter／Gemini 模型名 — 見下方「模型與環境」專節（`llm_provider.py` 已深讀）

### Test Coverage
- **Test Directories**: `backend/tests/`；根層 `backend/test_agent.py`（手動 CLI）
- **Test Frameworks**: `unittest`（含 `IsolatedAsyncioTestCase`）；`hypothesis` 在 requirements（規則引擎 PBT 他處）
- **Coverage Config**: 本掃描未見專用 coverage 設定

### Code Quality Indicators
- **Linting**: 未在 snapshot 內確認（略）
- **CI/CD**: 未深讀 workflows；存在 `scripts/smoke_langgraph_openrouter.py`（無 key 則 SKIP）
- **Documentation**: agent／router／`llm_provider` docstring 詳盡；`Dockerfile` L2–5 註解仍寫 `design_agent.py` 驅動 `ClaudeSDKClient`——**與現況不符**（Design 已 LangGraph；CLI 仍為 Review／Lens 所需）

### Technical Debt Signals
- **雙框架並存**：Design（A1）已 LangGraph；Review／Lens 仍 Claude Agent SDK（CLI）
- **`langgraph_runtime` 與 Assessment 斷開**：共用 OpenRouter helper 未被 `review_agent`／`wa_lens_engine`／`design_agent` import；且 Design 走 `ChatAnthropic`+`ANTHROPIC_*`，runtime 走 `ChatOpenAI`+OpenAI-compatible base——兩條 OpenRouter 適配路徑
- **依賴缺口**：`claude-agent-sdk`、`langchain-openai` 未 pin 於 `requirements.txt`
- **Dockerfile 註解過時**（L2–5）：應改述「Review／Lens（及任何殘留 SDK 呼叫）仍需 Claude Code CLI」；Node／claude-code 安裝本身在 Assessment 全迁 LangGraph 前仍合理
- **模組頂註過時**（`llm_provider.py` L3–4）：寫「Every LLM feature … runs through claude-agent-sdk」——Design／`langgraph_runtime` 已例外
- **全域 progress queue**（`design_agent.py` `_progress_queue`）：非 thread-safe 多租戶隔離
- **MemorySaver 進程內記憶體**（`design_agent.py` L169）：重啟即失；多 worker 不共享

### 模型與環境（擴界深讀：`llm_provider.py`／`llm_limits.py`）

#### Provider 開關
- `LLM_PROVIDER`：`openrouter`（預設）｜`cli`（`get_provider` L82–101）
- **openrouter**：需 `OPENROUTER_API_KEY`（或既有 `ANTHROPIC_AUTH_TOKEN`）；`configure_provider_env` → `_configure_openrouter_env`（L127–143）
  - 設定 `ANTHROPIC_BASE_URL` 預設 `https://openrouter.ai/api`（L52、L132）
  - 將 key 寫入 `ANTHROPIC_AUTH_TOKEN`；強制 `ANTHROPIC_API_KEY=""` 以免直連 Anthropic（L133–136）
  - 若無 `ANTHROPIC_DEFAULT_SONNET_MODEL`，以 `LLM_MODEL` 或 `_OPENROUTER_DEFAULT_MODEL` 填入（L138–141）
- **cli**：自環境 **刪除**（非 blank）認證／alias 衝突變數（`_CLI_CONFLICTING_VARS` L71、L115–124），改用本機 `claude login`
- 部署哲學：缺 OpenRouter key 必須大聲失敗，不自動退回 CLI（模組 docstring L33–36）

#### 模型預設（Assessment 相關）
| Getter | 用途 | openrouter 預設 | cli 預設 | env 覆寫優先序 |
|--------|------|-----------------|----------|----------------|
| `get_design_model_name`（L201–211） | A1 Design／LangGraph | `google/gemini-2.5-flash` | `sonnet` | 僅 `DESIGN_LLM_MODEL` |
| `get_model_name`（L214–222） | WA lens 等一般 agent | `google/gemini-3.7-flash` | `sonnet` | `LLM_MODEL` →（openrouter）`ANTHROPIC_DEFAULT_SONNET_MODEL` |
| `get_review_model_name`（L225–237） | A3 Review 建議 | `google/gemini-3.7-flash`（`_OPENROUTER_DEFAULT_REVIEW_MODEL` L77） | `haiku` | `REVIEW_LLM_MODEL` → `LLM_MODEL` → sonnet alias |

- cli 模式若 env 殘留含 `/` 的 gateway slug（如 `google/gemini-3.7-flash`），`_resolve` 會忽略並退回 cli 預設（L175–183）
- 常數 `_OPENROUTER_DEFAULT_MODEL`／`_OPENROUTER_DEFAULT_REVIEW_MODEL` 皆為 `google/gemini-3.7-flash`（L76–77）；與 `langgraph_runtime.DEFAULT_OPENROUTER_MODEL` 同字串，但 **runtime 不呼叫 `llm_provider`**

#### Auth 就緒
- `llm_auth_ready`（L146–159）：cli 恒 True；openrouter 需 `OPENROUTER_API_KEY` 或 `ANTHROPIC_AUTH_TOKEN`
- `auth_error_message`（L162–167）：提示設 OpenRouter key 或改 `LLM_PROVIDER=cli`

#### `llm_limits`（Assessment agents）
- 輸出上限：預設 12_000，夾在 512–24_000；env `LLM_MAX_OUTPUT_TOKENS` 或 `CLAUDE_CODE_MAX_OUTPUT_TOKENS`（L13–24）
- XML／圖摘要上下文：預設 32_000 字元，夾在 2_000–200_000；`LLM_XML_CONTEXT_MAX_CHARS`（L27–33）；`truncate_text_for_llm` 供 Design prompt 截斷
- `apply_agent_token_limits_to_env`（L51–56）：寫入 `CLAUDE_CODE_MAX_OUTPUT_TOKENS`；若未設則 `MAX_THINKING_TOKENS=0`（關 extended thinking 省 token）——由 `configure_provider_env` 兩模式皆呼叫
- `agent_sdk_env`（L59–64）：傳入 `ClaudeAgentOptions.env`（Review／Lens SDK 路徑）
- **注意**：LangGraph Design／`langgraph_runtime` **不**經 `agent_sdk_env`；token 限額對那兩條路徑效力主要靠 prompt 截斷與各自 client 參數，而非 CLI env

### Intent 焦點答覆（對應五問）

#### 1. 目前 agent 框架？
| 表面 | 框架 | 證據 |
|------|------|------|
| A1 Design／產圖 | **LangGraph**（`StateGraph` + `ToolNode` + `ChatAnthropic`） | `design_agent.py` L9–16、L109–157、L171–216 |
| A3 Review 建議文字 | **Claude Agent SDK**（`ClaudeSDKClient`，無工具） | `review_agent.py` L1–5、L115–168 |
| A3 Lens 作答 | **Claude Agent SDK** + MCP tool `emit_lens_answers` | `wa_lens_engine.py` L468–556 |
| 規則分數 | **純函式**（無 LLM） | `wa_rule_engine.py` L1–5、`evaluate` |
| 成本／OpenRouter 共用 runtime | **LangGraph helpers**（與 A3 評核路徑平行、未接線） | `langgraph_runtime.py` L1–7 |
| 模型／認證適配 | **`llm_provider` + `llm_limits`**（為 SDK／Anthropic-compatible 路徑設計；模組註仍寫「全部經 SDK」已過時） | `llm_provider.py` L1–37、L104–237 |

#### 2. 入口與 call graph／模型選擇
```
AssessmentPage (/assessment, story A3)
  ├─ POST /api/architecture/reviews
  │    → review_router.create_review          （main: /api/architecture）
  │    → review_orchestrator.start_review
  │         ├─ wa_rule_engine.evaluate
  │         ├─ wa_lens_engine.answer_lens_with_agent  （SDK；get_model_name → 預設 gemini-3.7-flash）
  │         └─ review_agent.run_review_agent          （SDK；get_review_model_name → 同預設）
  ├─ POST /api/architecture/generate-wa-collab
  │    → agent_router → wa_collab_orchestrator.run_wa_collab
  │         ├─ design_agent.run_design_agent   （LangGraph；get_design_model_name → gemini-2.5-flash）
  │         ├─ wa_score_service.score_xml      （規則 + lens agent）
  │         └─ review_agent.run_review_agent
  └─ POST .../retry-suggestions → run_review_agent

啟動：main.load_backend_dotenv → configure_provider_env（openrouter 映射或 cli 清環境）
```
- Design 在 openrouter 下用 `ChatAnthropic(api_key=ANTHROPIC_AUTH_TOKEN, base_url=ANTHROPIC_BASE_URL)`，依賴 `configure_provider_env` 的映射（`design_agent.py` L117–126 + `llm_provider.py` L127–143）

#### 3. 既有 LangGraph vs 尚待 refactor
**已有：** Design graph、`langgraph_runtime` helpers、相關測試／smoke  
**Assessment 仍待迁：** `review_agent`、`wa_lens_engine.answer_lens_with_agent`（及 orchestrator／score／collab 對它們的呼叫）  
**迁徙時環境契約：** 若廢 SDK，需重新定義是否仍要映像內 `claude` CLI、以及 Review／Lens 是否改用 `langgraph_runtime.openrouter_chat_model`（今日與 `llm_provider` 平行）

#### 4. Frontend AssessmentPage ↔ backend 契約
（前次掃描仍有效）SSE 評核／collab；前端不傳 LLM model 名；僅雲 `provider`。路由掛載已由 `main.py` L52–53 確認。

#### 5. Dependencies pins（`requirements.txt` + Dockerfile）
```
langgraph / langchain-core / langchain-anthropic   # 未釘版本
# 缺：langchain-openai、claude-agent-sdk
# Docker 另裝：nodejs 22 + @anthropic-ai/claude-code（非 pip）
```
預設模型字串匯總：`google/gemini-3.7-flash`（lens／review／langgraph_runtime／openrouter 常數）；Design 預設 `google/gemini-2.5-flash`。

## Handoff Summary
- **Intent-relevant finding**: Assessment（A3）評核仍由 **Claude Agent SDK**（Review + Lens）驅動；Design 已 **LangGraph**。模型真相源為 `llm_provider`：部署預設 OpenRouter，Review／Lens 預設 `google/gemini-3.7-flash`，Design 預設 `google/gemini-2.5-flash`；`llm_limits` 透過 CLI env／`agent_sdk_env` 節流 SDK 路徑。`langgraph_runtime` 仍未接入 A3。重構應替換 Review／Lens、維持 SSE 契約，並決定是否統一到 `langgraph_runtime` 或沿用 `ChatAnthropic`+`llm_provider` 映射（證據：`llm_provider.py` L76–237、`llm_limits.py` L51–64、`main.py` L24–58、`Dockerfile` L2–18、`review_agent.py`／`wa_lens_engine.py`／`design_agent.py`）。
- **Risks / follow-up**:
  1. ~~必須擴 snapshot 深讀 `llm_provider`~~ — **已解決**（本輪已深讀 `llm_provider`／`llm_limits`／`main.py`／`Dockerfile`）。
  2. `claude-agent-sdk`／`langchain-openai` 仍未在 `requirements.txt`；Dockerfile 依賴全域 `claude` CLI —— 全迁 LangGraph 後可評估移除 Node／claude-code 層。
  3. Intent「A2」與程式 story「A3」命名不一致 — requirements 對齊。
  4. 雙 OpenRouter 適配（`llm_provider` Anthropic-compat vs `langgraph_runtime` OpenAI-compat）— 统一 runtime 時需選一或做薄適配。
  5. 可選後續擴界（非阻擋）：`backend/cost/`（既有 LangGraph 消費）、`collab_router.py`／`lens_router.py`、`env_bootstrap.py`、`backend/tests/test_llm_provider.py`。
  6. 文件漂移：更新 `Dockerfile` L2–5 與 `llm_provider.py` L3–4 頂註，避免後續 agent 誤判 Design 仍走 SDK。
