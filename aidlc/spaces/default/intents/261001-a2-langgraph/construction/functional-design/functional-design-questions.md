# Functional Design 問答：A3 Assessment → LangGraph

> Intent `261001-a2-langgraph`｜construction／functional-design（zero-Unit refactor）｜Minimal  
> 上游需求：`inception/requirements-analysis/requirements.md`（已核可）  
> 本站釘**行為與邊界**，不寫實作碼、不寫框架專屬完整類別。

## 已由 requirements 鎖定、本站不重問

- 迁徙面：Review + Lens；走 `langgraph_runtime`；SSE／API 行為不變；預設 `google/gemini-3.7-flash`；零 `ClaudeSDKClient` 後移除 Dockerfile CLI；既有測試綠＋≥1 自動化遷移／契約測試。
- C1／Design 不在本輪改寫範圍。

## Sources

- **[S1]** FR1–FR5、NFR1–NFR3（requirements.md）
- **[S2]** codekb `architecture.md` Assessment SSE 互動圖；`review_agent` yield → `suggestion_delta`
- **[S3]** 既有 U6 定案：`langgraph_runtime` 提供 `invoke_graph`／`stream_graph`；OpenAI-compat OpenRouter
- **[S4]** `AssessmentPage.tsx` 依賴 SSE `type === 'suggestion_delta'` 與 `suggestions_text` 等欄位

---

## Q1 — Review 與 Lens 的圖邊界

- **A.** **兩個獨立 compiled graph**（`review_graph`、`lens_graph`），各自經 `langgraph_runtime` 執行；共享的只有 runtime helper 與模型預設
- **B.** **單一共用 graph 骨架**＋不同 prompt／工具節點配置（同一 compile 工廠，兩種 mode）
- **C.** Review 用 graph；Lens 只做單次 `invoke` 無多節點（極簡）
- **X.** Other (please specify)

[Answer]: A
<!-- answered 2026-10-01T08:16:10Z -->

---

## Q2 — Lens 的結構化輸出（取代 MCP `emit_lens_answers`）

現況 Lens 經 Claude Agent SDK + MCP tool `emit_lens_answers` 收集結構化答案。迁到 LangGraph 後：

- **A.** 以 **structured output／tool 節點**（等價強制 schema）在 graph 內收集答案，orchestrator  consum 的資料形狀與現況 lens 結果相容
- **B.** 模型自由文字 + **後置解析器**還原既有結構（解析失敗走與現況相同的失敗語意）
- **C.** 改為純規則、本輪取消 LLM lens（違反 FR1，不建議）
- **X.** Other (please specify)

[Answer]: A
<!-- answered 2026-10-01T08:17:00Z -->

---

## Q3 — Review 串流如何對到既有 SSE

前端依賴 `suggestion_delta`（累積建議文字）。LangGraph 串流應對齊：

- **A.** `stream_graph` 的 token／訊息增量 **映射為既有 `suggestion_delta` 事件**（欄位名與語意不變）；完成事件仍由 orchestrator 發現況的 complete／等同事件
- **B.** 新增內部串流事件類型，再由 router 改編成 `suggestion_delta`（對外仍相容，但多一層）
- **C.** 改為非串流：整段建議一次回傳（會改 UX，違反 FR3）
- **X.** Other (please specify)

[Answer]: A
<!-- answered 2026-10-01T08:17:22Z -->

---

## Q4 — LLM／runtime 硬失敗時的行為

- **A.** **維持現況語意**：硬失敗向上拋（或等價錯誤），由 orchestrator／router 轉成既有錯誤／SSE 失敗呈現；不得靜默空字串假裝成功
- **B.** 軟降級：回傳固定「建議產生失敗」字串並標 complete（改變失敗可觀測性）
- **C.** 自動 fallback 到 Claude Agent SDK（違反 FR4）
- **X.** Other (please specify)

[Answer]: A
<!-- answered 2026-10-01T08:17:40Z -->

---

## Q5 — 前端變更範圍

- **A.** **`AssessmentPage.tsx` 零行為變更**（不改事件處理、不改 API URL）；若僅型別／註解則可，但不得作為完成 FR 的必要條件
- **B.** 允許小幅前端調整以適配新事件（需同批改 OpenAPI／契約——與 FR3=A 衝突風險高）
- **X.** Other (please specify)

[Answer]: A
<!-- answered 2026-10-01T08:17:56Z -->

---

## Q6 — 自動化驗證最小集合（回應 reviewer R-04）

FR5.2 要求 ≥1 條。設計層把底線釘成：

- **A.** **兩條**：Review 路徑與 Lens 路徑各至少一條可自動判定測試（mock LLM／runtime），證明皆經 `langgraph_runtime` 且不再 import `claude_agent_sdk`
- **B.** **一條整合測試**同時覆蓋 Review＋Lens 兩路徑（單測內兩段 assert）
- **C.** 維持字面「至少一條」（可只覆蓋其中一條）
- **X.** Other (please specify)

[Answer]: A
<!-- answered 2026-10-01T08:18:24Z -->

## Consolidated Summary Confirmation

- Q1 = A：Review 與 Lens 各一個獨立 compiled graph；共享 `langgraph_runtime` 與模型預設
- Q2 = A：Lens 用 structured output／tool 節點強制 schema，消費形狀與現況相容
- Q3 = A：LangGraph 串流增量直接映射為既有 SSE `suggestion_delta`
- Q4 = A：硬失敗向上拋，由既有 orchestrator／router 錯誤路徑呈現
- Q5 = A：`AssessmentPage.tsx` 零行為變更
- Q6 = A：Review 與 Lens 各至少一條自動化遷移／契約測試（經 `langgraph_runtime`、不 import SDK）

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
<!-- answered 2026-10-01T08:19:03Z -->
