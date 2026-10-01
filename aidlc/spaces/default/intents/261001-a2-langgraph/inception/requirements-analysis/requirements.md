# 需求規格：A3 Assessment agent 框架迁至 LangGraph

> Intent `261001-a2-langgraph`｜階段 inception / requirements-analysis｜深度 Minimal｜scope refactor  
> 權威描述（`project-description` 工具逐字）：「我要進行 a2評估儀表板 將agent框架改成 langraph ,使用refactor」  
> `FR{n}` 與 `NFR{n}` 為永久追溯鍵，下游階段必須原樣保留，不得重新編號或改以散文指涉。  
> 答案來源：`requirements-analysis-questions.md`（Q1–Q7；Consolidated Summary = Looks correct）  
> **架構決策**：`../decisions/0019-a3-langgraph-openrouter-runtime.md`（ADR-0019；A3→LangGraph／OpenRouter、CLI 退場、A1／C1 界線）

## 意圖分析

使用者要達成的目標是：**把 Assessment（產品面為 A3／`/assessment`）評核路徑上仍使用 Claude Agent SDK 的 agent，改成 LangGraph**，並在行为上對前端維持相容。

Intent 口語「A2 評估儀表板」在本文件中定錨為 **A3 Assessment**（Q1=A）：與 story id、路由 `/assessment` 一致；文件提及「A2」時一律視為該口語別名，不以 OpenAPI 中架構編輯權「A2」字樣覆寫本 intent 範圍。

### 與現況的落差（codekb）

| 表面 | 現況 | 本輪 |
|---|---|---|
| A1 Design | 已 LangGraph（`ChatAnthropic` + `llm_provider`） | **不在範圍** |
| A3 Review／Lens | Claude Agent SDK（`ClaudeSDKClient`） | **必须迁至 LangGraph** |
| C1 `cost_advice_agent` | 已 LangGraph（`langgraph_runtime`） | **不在範圍**（Q2=A） |
| `langgraph_runtime` | 存在但未接 A3 | **本輪 A3 主路徑**（Q3=B） |

核心價值：評核功能對使用者不變；底層 runtime 與 Design／C1 的 LangGraph 生態對齊，並移除對映像內 Claude Code CLI 的依賴（Q6=C）。

---

## 功能需求

### FR1 — 迁徙範圍與命名

- **FR1.1** 本 intent 必須將下列呼叫面改為 LangGraph 實作，且不得再透過 `ClaudeSDKClient`／`claude_agent_sdk` 執行：`review_agent` 的建議產生、`wa_lens_engine.answer_lens_with_agent` 的 lens 作答，以及 `review_orchestrator`／`wa_score_service`／`wa_collab_orchestrator` 對上述兩者的呼叫鏈。[Q2]
- **FR1.2** Design（A1）與 C1 cost agent **不得**因本 intent 被改寫行為或被迫重迁（得為共用 helper 做非破壞性擴充）。[Q2]
- **FR1.3** 需求、設計與測試文件中，本改動的產品名稱必須標為 **A3 Assessment**；若出現 Intent 口語「A2」，必須註明等同 A3 Assessment，不得與架構編輯權 id「A2」混淆。[Q1]

### FR2 — LangGraph 實作樣式

- **FR2.1** A3 Review 與 Lens 的 LLM 執行必須經 `services.langgraph_runtime`（OpenAI-compat／OpenRouter 路徑），與 C1 `cost_advice_agent` 同套路；不得新建第三套平行適配層作為主路徑。[Q3]
- **FR2.2** 不得以「對齊 Design 的 `ChatAnthropic` + Anthropic-compat」作為 A3 主路徑（Design 現況可保留；本輪不要求 Design 改走 `langgraph_runtime`）。[Q3]
- **FR2.3** Review 與 Lens 所需的模型名稱解析，在 OpenRouter 預設下必須使用 `google/gemini-3.7-flash`（可與 `langgraph_runtime.DEFAULT_OPENROUTER_MODEL`／既有 review 預設常數對齊）；環境變數覆寫機制可保留，但**預設值**必須符合本條。[Q5]
- **FR2.4** 不得因本 intent 變更 Design 預設模型 `google/gemini-2.5-flash`。[Q5]

### FR3 — 對外契約不變式（行為不變重構）

- **FR3.1** `AssessmentPage` 既有呼叫的 HTTP 路徑集合（含 `/api/architecture` 下 reviews／collab／retry 等評核相關端點）必須維持可呼叫且語意相容。[Q4]
- **FR3.2** 評核／collab 的 SSE（或等價串流）事件類型與前端依賴的欄位集合必須維持相容；使用者完成「發起評核 → 看見分數／findings／建議」的操作路徑不得因本重構而改變。[Q4]
- **FR3.3** 前端仍不得被要求傳入 LLM model 名；僅雲 `provider`（若現況已傳）等既有欄位可保留。[Q4][codekb]
- **FR3.4** 若 OpenAPI 因實作細節需更新，不得引入對 FR3.1–FR3.3 的破壞性變更；契約變更僅限文件化既有相容行為或非使用者可見的內部欄位（若無必要則不改契約）。[Q4]

### FR4 — Claude Agent SDK 與映像 CLI 退場

- **FR4.1** 本 intent 完成時，`backend/` 應用程式碼中不得再存在對 `ClaudeSDKClient`／`claude_agent_sdk` 的執行期呼叫（含動態 import 成功路徑）。允許測試中以 mock／否定斷言提及該名稱。[Q2][Q6]
- **FR4.2** 在 FR4.1 滿足後，同一 intent 必須自 `backend/Dockerfile` 移除 Node.js 與全域 `@anthropic-ai/claude-code`（Claude Code CLI）安裝步驟，並更新過時註解（不得再宣稱 Design／Review 依賴該 CLI）。[Q6]
- **FR4.3** 部署預設路徑（OpenRouter）在移除 CLI 後必須仍能完成 A3 評核。容器內 `LLM_PROVIDER=cli` 得標記為不再支援；若文件仍提及該模式，必須註明僅適用於本機自備 CLI 的非容器情境或不支援。[Q6]
- **FR4.4** 若施工中發現 FR4.1 無法達成（仍有非本輪範圍的強制 SDK 依賴），不得執行 FR4.2；必須在 construction 閘門升級為阻擋項並回報，而不是留下半残映像。[Q6]

### FR5 — 驗證

- **FR5.1** 既有自動化測試套件（含既有 `test_langgraph_*` 等）在變更後必須維持綠燈。[Q7]
- **FR5.2** 必須新增至少一條可自動判定的測試，覆蓋下列至少一項：Review 或 Lens 經 `langgraph_runtime` 的遷移行為、或評核相關 API／串流契約在 mock LLM 下的相容斷言。[Q7]
- **FR5.3** 無法以單元／TestClient 穩定覆蓋的 SSE 使用者觀察面，得列入手動測案；不得用手動案例重複已自動化斷言的行為。[Q7]

---

## 非功能需求

### NFR1 — 相容與可觀測

- **NFR1.1** 重構不得引入新的使用者可見錯誤碼語意，除非對應現況已有之失敗模式（例如 LLM 失敗降級）。
- **NFR1.2** 評核路徑的結構化 log logger 名稱應維持 `cloud360.*` 慣例；關鍵階段（開始／完成／LLM 失敗）須仍可於 log 中辨識。

### NFR2 — 安全（ADR-0006 四面向判定）

| 面向 | 判定 | 理由 |
|---|---|---|
| IAM | 不適用 | 不改 RBAC seed／故事權限；A3 既有授權邊界不變 |
| Encryption | 不適用 | 不改傳輸／靜態加密；持續經既有 HTTPS／既有 secret 注入 |
| Network exposure | 適用／維持 | LLM 呼叫維持既有 OpenRouter（或文件化之 provider）出口；移除 CLI 不新增暴露面 |
| Audit logging | 適用／維持 | 不削弱既有評核稽核／log；不新增未遮罩的 secret 輸出 |

- **NFR2.1** 不得將 API key、token 寫入評核 SSE 或前端可見錯誤訊息。

### NFR3 — 維運與建置

- **NFR3.1** `requirements.txt` 必須能支撐 `langgraph_runtime` 路徑（含其 OpenAI-compat 依賴）；若執行期需要而尚未 pin 的套件，本 intent 必須補齊並避免「映像能建、執行期 ImportError」的缺口。[codekb]
- **NFR3.2** Docker 映像在移除 Claude CLI 後必須仍能通過既有 docker-build CI job。

---

## 約束

- **C1** Scope = refactor／Minimal：以行為不變重構為主，不擴 A3 產品功能（新 lens UX、新分數演算法等另開 intent）。
- **C2** Standing：文件繁中；security baseline 與 PBT hard constraint 若觸及純函式新核心則適用——本輪以 runtime 替换為主，若抽出純轉換函式則依 ADR-0006 評估 PBT。
- **C3** 帳單／用量類雲端 API 禁令不因本 intent 改變（與成本域 ADR 無關但不得誤開）。

---

## 假設

- **A1** 部署預設 `LLM_PROVIDER` 為 openrouter（或等價使 `langgraph_runtime` 可取得 OpenRouter 憑證的配置），與現況 staging 一致。[codekb]
- **A2** C1 `cost_advice_agent` 在本輪施工期間維持 LangGraph，不回退 SDK。
- **A3** Assessment 前端不傳 model 名的契約在施工期間不被其他並行 PR 破壞。

---

## 不在範圍（Out of scope）

- 将 Design 從 `ChatAnthropic` 適配迁到 `langgraph_runtime`（可列後續）。
- C1 成本功能行為／估價表／pricing 端點變更。
- A3 產品功能增強（新 UI 流程、新 WA 規則內容、新權限模型）。
- Playwright e2e 覆蓋 `/assessment`（Q7 未選 C；非本輪地板）。
- 雲端供應商 production、destructive cloud operations。

---

## 開放問題（留给下游）

- **OQ1** Review 與 Lens 的 graph 節點切分、checkpoint／串流對 SSE 的精确映射——functional-design。
- **OQ2** `llm_provider` 與 `langgraph_runtime` 雙適配的長期收斂（本輪只要求 A3 走 runtime）。
- **OQ3** 移除 CLI 後，本機 `LLM_PROVIDER=cli` 文件與 `LOCAL-DEV.md` 的表述——construction 時同步。

---

## 追溯

| 決策 | 來源 |
|---|---|
| A3 命名 | Q1=A |
| 仅迁 Review／Lens | Q2=A |
| `langgraph_runtime` | Q3=B |
| SSE／API 相容 | Q4=A |
| `gemini-3.7-flash` | Q5=A |
| 移除 Dockerfile CLI | Q6=C |
| 測試地板 | Q7=A |
| 現況架構 | `aidlc/spaces/default/codekb/cloud/` |
