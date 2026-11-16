# Requirements Analysis — 釐清問題

> Intent：`261001-a2-langgraph`（refactor｜Minimal）  
> 權威描述：`我要進行 a2評估儀表板 將agent框架改成 langraph ,使用refactor`  
> 上游：`aidlc/spaces/default/codekb/cloud/`（Focused merge，2026-10-01）

## 前言：已由 reverse-engineering 鎖定、本站不重問

下列為 codekb 已驗證的現況，不另開題：

- Assessment 產品路由為 `/assessment`，故事 id 為 **A3**（Intent 名稱「A2」為口語／命名落差，見 Q1）。
- Design（A1）**已**走 LangGraph；Review／Lens（A3）仍走 **Claude Agent SDK**。
- `langgraph_runtime` 已存在但**未**接入 Assessment。
- 前端 Assessment SSE **不傳** LLM model 名，只傳雲 `provider`。
- OpenRouter 預設下 Review／Lens 模型為 `google/gemini-3.7-flash`；Design 為 `google/gemini-2.5-flash`。
- Standing constraints（ADR-0006 security／PBT、繁中文件）本站不重問。

本站只補仍缺的可測決策與範圍邊界。

## Sources（查證登錄｜非 ideation 來源 register）

- `[codekb:business-overview]` Assessment／Agent 框架現況表
- `[codekb:architecture]` 雙框架並存與評核 SSE 互動圖
- `[codekb:code-structure]` 模組呼叫面與 Dockerfile／requirements 落差
- `[scan:developer-scan.md]` Handoff：迁徙邊界、雙 OpenRouter 適配

---

## Q1 — 產品命名對齊

Intent 寫「A2 評估儀表板」，codekb 顯示評估頁／story 為 **A3**（OpenAPI 另有架構編輯權 A1／A2／A4 字樣）。本輪需求文件應如何定錨？

A. 以產品事實為準：本 intent 改的是 **A3 Assessment（`/assessment`）** 的 Review／Lens agent；文件內註明 Intent 口語「A2」＝A3  
B. 堅持稱 A2，並在需求中把「A2」定義為 Assessment 儀表板的別名（與 story id A3 並存說明）  
C. 先暫停：必須另開盤點／改名工作，本 refactor 不做實作直到命名統一  
X. Other (please specify)

[Answer]: A
<!-- answered 2026-10-01T07:45:46Z -->

---

## Q2 — 本輪迁徙範圍

哪些 agent 呼叫面必須在本 intent 改成 LangGraph？

A. **僅 A3**：`review_agent` ＋ `wa_lens_engine.answer_lens_with_agent`（含 orchestrator／score／collab 對它們的呼叫）；Design 已迁、C1 cost agent **不在本輪**  
B. A3 Review／Lens **加上** C1 `cost_pricing_agent`（一併離開 Claude Agent SDK）  
C. 僅 `review_agent`；Lens 維持 SDK（分兩階段）  
X. Other (please specify)

[Answer]: A
<!-- answered 2026-10-01T07:47:02Z; note: C1 cost_advice_agent already LangGraph via langgraph_runtime -->

---

## Q3 — LangGraph 實作樣式

A3 迁徙應對齊哪一種既有樣式？

A. **對齊 Design**：`StateGraph` + `ChatAnthropic`，繼續走 `llm_provider.configure_provider_env` 的 Anthropic-compat／OpenRouter 映射  
B. **改走 `langgraph_runtime`**：以 OpenAI-compat（`ChatOpenAI`／OpenRouter）為 A3 主路徑，並逐步收斂 Design 的雙適配（可本輪只接 A3）  
C. **新建第三套**薄適配，專門給 Review／Lens（不強制與 Design／runtime 統一）  
X. Other (please specify)

[Answer]: B
<!-- answered 2026-10-01T07:47:32Z -->

---

## Q4 — 對外契約不變式

Assessment 前端與 HTTP／SSE 契約，本輪硬約束是什麼？

A. **行為不變重構**：`AssessmentPage` 呼叫的路徑、SSE 事件語意、請求／回應欄位集合維持相容；使用者操作路徑不變；僅允許後端內部換 runtime  
B. 允許為 LangGraph 調整 SSE 事件或欄位，但必須同步改前端與 OpenAPI（允許同批契約變更）  
C. 允許破壞性契約變更，前端可另開 PR／後續 intent  
X. Other (please specify)

[Answer]: A
<!-- answered 2026-10-01T07:53:49Z -->

---

## Q5 — 模型指定

使用者曾提及「AI 模型指定為 gemini 3.7 flash」。對本輪 A3 Review／Lens 的要求是？

A. **鎖定** OpenRouter 下 Review／Lens 預設為 `google/gemini-3.7-flash`（與現況 `llm_provider` 常數一致）；文件寫成可測 FR／NFR；不改 Design 的 `gemini-2.5-flash` 預設  
B. Review／Lens **與 Design 統一**為同一模型字串（需選定一個）  
C. 模型名維持可由環境變數覆寫即可，不在需求鎖定具體字串  
X. Other (please specify)

[Answer]: A
<!-- answered 2026-10-01T07:54:21Z -->

---

## Q6 — Claude CLI／映像清理

今日 `Dockerfile` 仍安裝 Node + `@anthropic-ai/claude-code`（Review／Lens SDK 需要）。本輪收尾期望？

A. A3 全迁 LangGraph 且確認無殘留 SDK 呼叫後，**本 intent 一併**評估並移除映像內 Claude CLI／相關註解更新（若 C1 仍用 SDK 則**不得**移除，改記為阻擋項）  
B. 本輪**只迁程式**；映像／CLI 清理列為後續 intent（本輪更新過時註解即可）  
C. 無論 C1 是否仍用 SDK，本輪強制移除 CLI  
X. Other (please specify)

[Answer]: C
<!-- answered 2026-10-01T07:55:31Z; interpreted with Q2=A: after A3 LangGraph migration eliminates ClaudeSDKClient callers, this intent MUST remove Node/@anthropic-ai/claude-code from Dockerfile; in-container LLM_PROVIDER=cli unsupported; default openrouter unaffected -->

---

## Q7 — 驗證底線（refactor）

在既有測試須保持綠燈之外，本輪最低驗證要求？

A. 既有 `test_langgraph_*`／相關 unittest 綠燈 ＋ 為 Review／Lens 新路徑補最小自動化（至少一條可判定的遷移／契約測試）；手動只覆蓋無法自動化的 SSE 觀察面  
B. 僅要求既有測試綠燈；不強制新測試（符合 org 對 refactor 的「無新測試地板」預設）  
C. 另要求 Playwright e2e 覆蓋 `/assessment` 評核 happy path  
X. Other (please specify)

[Answer]: A
<!-- answered 2026-10-01T08:01:35Z -->

## Consolidated Summary Confirmation

- Q1 = A：以產品事實為準，本 intent 改 **A3 Assessment（`/assessment`）** Review／Lens；Intent 口語「A2」＝A3
- Q2 = A：本輪仅迁 A3（`review_agent`＋Lens）；Design／C1 不在範圍（C1 `cost_advice_agent` 已 LangGraph）
- Q3 = B：A3 對齊 **`langgraph_runtime`**（OpenAI-compat，與 C1 同套路）
- Q4 = A：**行為不變重構**——Assessment SSE／API 路徑與欄位集合相容
- Q5 = A：OpenRouter 下 Review／Lens 預設鎖定 **`google/gemini-3.7-flash`**；不改 Design 的 `gemini-2.5-flash`
- Q6 = C：A3 迁完且全 repo 無 `ClaudeSDKClient` 後，**本 intent 強制移除** Dockerfile 內 Node／`@anthropic-ai/claude-code`；容器內 `LLM_PROVIDER=cli` 不再支援
- Q7 = A：既有測試綠燈＋Review／Lens 新路徑最小自動化（≥1 條可判定遷移／契約測試）；手動僅無法自動化的 SSE 觀察面

Does this all look correct before I generate the requirements artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
<!-- answered 2026-10-01T08:02:43Z -->
