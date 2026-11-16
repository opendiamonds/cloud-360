# ADR 0019: A3 Assessment Review／Lens 迁至 LangGraph + OpenRouter，並退出映像內 Claude Code CLI

- Status: Accepted
- Date: 2026-10-01
- Intent: `261001-a2-langgraph`
- Relates: **ADR-0002**（agent routing／tool execution 可追溯）；**ADR-0006**（security baseline）；**ADR-0007**（staging 部署）
- Amends: 無。不修改 ADR-0002 原文；本 ADR 為其「未來 agent 以 ADR 擴充」出口的實例化。
- Downstream: `inception/requirements-analysis/requirements.md` FR1–FR5／NFR1–NFR3；`construction/functional-design/*`；`backend/services/review_agent.py`、`wa_lens_engine.py`、`langgraph_runtime.py`；`backend/Dockerfile`

## Context

Assessment（產品面 A3、`/assessment`）評核路徑上，Review 建議與 Lens 作答仍透過 Claude Agent SDK（`ClaudeSDKClient`）執行，部署映像因此必須安裝 Node.js 與全域 `@anthropic-ai/claude-code`。同 repo 內：

| 路徑 | 執行框架 | 備註 |
|---|---|---|
| A1 Design | 已 LangGraph（`ChatAnthropic` + `llm_provider`） | 不在本 intent 改寫範圍 |
| C1 `cost_advice_agent` | 已 LangGraph（`services.langgraph_runtime` → OpenRouter） | 不在本 intent 改寫範圍 |
| A3 Review／Lens | Claude Agent SDK + 映像 CLI | **本 ADR 處置對象** |

問題：

1. A3 與 Design／C1 的 runtime 分裂，維運與除錯成本上升。
2. 映像依賴 Claude Code CLI 與 OpenRouter HTTP 路徑重疊，增加映像體積與失敗面。
3. ADR-0002 要求 agent／tool execution 變更可追溯；本轮属架构级 runtime 替换，不得只改程式不留決策紀錄。

觸發來源：intent `261001-a2-langgraph` requirements-analysis（Q2=A 僅 A3；Q3=B 走 `langgraph_runtime`；Q5 預設 `google/gemini-3.7-flash`；Q6=C 零 SDK 後移除 CLI）。

## Decision

### 1. A3 Review／Lens 主路徑改為 LangGraph

- `review_agent.run_review_agent` 與 `wa_lens_engine.answer_lens_with_agent` **必須**以獨立 compiled LangGraph 執行 LLM，不得再經 `ClaudeSDKClient`／`claude_agent_sdk` 成功路徑。
- Review 與 Lens 各為單節點 graph（節點名 `generate`）；不得為此合併成與 Design 相同的 agent↔tools 雙節點圖。
- Graph state schema **必須**使用 TypedDict（或等價具名 channel），不得以 `StateGraph(dict)` 搭配 TypedDict 節點註解（該組合在 `stream_mode="messages"` + `ChatOpenAI` 下會清空 state，導致 `KeyError: 'user_prompt'`）。

### 2. OpenRouter 為 A3 預設執行路徑

- A3 必須經 `services.langgraph_runtime.openrouter_chat_model`（OpenAI-compat／OpenRouter），與 C1 `cost_advice_agent` 同套路。
- OpenRouter 預設模型：`google/gemini-3.7-flash`（可由既有環境變數覆寫；**預設值**不得改回 Claude CLI 模型別名）。
- 不得新建第三套平行適配層作為 A3 主路徑。
- **不得**以「對齊 Design 的 `ChatAnthropic`」作為 A3 主路徑（Design 現況可保留，本 ADR 不要求 Design 改走 `langgraph_runtime`）。

### 3. Claude Agent SDK 與映像 CLI 退場

- 應用程式碼（`backend/` 非測試否定斷言）不得再存在對 `ClaudeSDKClient`／`claude_agent_sdk` 的執行期呼叫。
- 在上一條滿足後，同一變更必須自 `backend/Dockerfile` 移除 Node.js 與全域 `@anthropic-ai/claude-code` 安裝步驟，並更新 DEPLOY／LOCAL-DEV 過時敘述。
- 部署預設（OpenRouter）在移除 CLI 後必須仍能完成 A3 評核。容器內 `LLM_PROVIDER=cli` 視為不再支援；文件若提及，須標明僅本機自備 CLI 的非容器情境或不支援。
- 若施工中仍有非本輪範圍的強制 SDK 依賴，**不得**半残移除 CLI；必須阻擋合併並回報。

### 4. 對外契約與產品行為不變

- `/assessment` 既有 HTTP／SSE 契約（含 `suggestion_delta`）維持語意相容；前端不傳 model 名。
- 硬失敗仍向上傳播；不得以空字串假装成功。缺金鑰／供應商錯誤不得把 secret 寫入 SSE 或前端可見錯誤（ADR-0006）。

### 5. 與 A1／C1 的界線

| 範圍 | 本 ADR |
|---|---|
| A3 Review／Lens | **必改** |
| A1 Design Agent | **禁止**因本 ADR 改行為或被迫重迁；允許非破壞性共用 helper |
| C1 cost advice | **禁止**改行為；可繼續使用既有 `langgraph_runtime` |
| 估價表／pricing／帳單 API | **不在範圍**（見 ADR-0017／0018） |

### 6. 相容與回滾策略

| 情境 | 作法 |
|---|---|
| 程式回滾 | 還原 `review_agent.py`／`wa_lens_engine.py` 與相關測試；若回滾到 SDK 路徑，必須同步還原 Dockerfile CLI 安裝，否則映像無法執行舊路徑 |
| 設定回滾 | 保留 `OPENROUTER_API_KEY` 與既有 `LLM_*` 覆寫；不引入新的必填秘密名稱作為唯一金鑰來源 |
| 漸進驗證 | 單元測試 mock graph／OpenRouter；手動測案覆蓋真實串流與缺金鑰降級（見本 intent TCMS） |
| 映像驗證 | docker-build CI 必須在無 Claude CLI 層的前提下通過 |

## Consequences

### Positive

- A3／C1 共用 OpenRouter runtime 語意，除錯與依賴盤點一致。
- 映像變小、少一層 Node／CLI 供應鏈與啟動失敗面。
- Assessment UX 與 API 契約維持，重構對使用者透明。

### Negative

- Design 仍走 `ChatAnthropic`，長期仍有雙適配（OQ：後續 intent 收斂）。
- 依賴 LangGraph channel／streaming 語意；schema 標註錯誤會在執行期才爆（已以 TypedDict + 回歸測試緩解）。
- 容器內 CLI 模式不可用，本機若堅持 CLI 須自備工具且不在預設支援矩陣。

### Neutral

- ADR-0002 的角色清單不因本 ADR 改寫；本 ADR 只固定 A3 Review／Lens 的 **execution substrate**。
- C1 估價上傳／SKU 目錄等能力由其他 intent／ADR 管轄。

## Alternatives Considered

### Alternative 1: 維持 Claude Agent SDK + 映像 CLI

- Pros: 零迁徙風險。
- Cons: 與 Design／C1 分裂；映像依賴持續；違反本 intent 目標。

### Alternative 2: A3 改走 Design 同款 `ChatAnthropic`

- Pros: 與 Design 程式風格接近。
- Cons: 再建一條 Anthropic-compat 適配，與已存在的 `langgraph_runtime` 重複；不利 CLI 退場與 OpenRouter 預設。

### Alternative 3: Review／Lens 合併為單一多節點 graph

- Pros: 理論上可共用 checkpoint。
- Cons: 兩路徑輸入／輸出契約不同（串流建議 vs 結構化 JSON）；過度設計且超出 Minimal refactor 範圍。

## References

- `aidlc/spaces/default/intents/261001-a2-langgraph/inception/requirements-analysis/requirements.md`
- `aidlc/spaces/default/intents/260802-default/inception/decisions/0002-agent-routing-layer.md`
- `backend/services/langgraph_runtime.py`
- `backend/tests/test_a3_langgraph_migration.py`
