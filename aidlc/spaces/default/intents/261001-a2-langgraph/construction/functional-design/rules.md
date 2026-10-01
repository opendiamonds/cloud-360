# Business Rules — A3 Assessment LangGraph 迁徙

> Intent `261001-a2-langgraph`｜functional-design  
> YAML 為 source of truth。`BRx.y` 供 traceability 機械核對。

```yaml
rules:
  - id: BR1.1
    statement: A3 Review 與 Lens 的 LLM 執行必須經 langgraph_runtime，不得經 ClaudeSDKClient
    category: policy
    applies_to: ReviewGraphRun, LensGraphRun
    trigger: 每次 Review 或 Lens LLM 呼叫
    logic: IF 發起 Review 或 Lens LLM 呼叫 THEN 必須經 langgraph_runtime AND 不得 import 或呼叫 claude_agent_sdk
    violation: 阻擋合併／建置驗證失敗
    source: FR1.1, FR2.1, FR4.1

  - id: BR1.2
    statement: Review 與 Lens 使用兩個獨立 compiled graph
    category: constraint
    applies_to: ReviewGraphRun, LensGraphRun
    trigger: 設計／實作 graph 時
    logic: IF 實作 A3 LLM 路徑 THEN Review 與 Lens 各為獨立 compiled graph AND 僅共享 runtime helper 與模型預設
    violation: 設計不符，須重做切分
    source: FD-Q1

  - id: BR1.3
    statement: OpenRouter 預設模型為 google/gemini-3.7-flash；不得改 Design 的 gemini-2.5-flash 預設
    category: policy
    applies_to: ReviewGraphRun, LensGraphRun
    trigger: 解析預設模型名時
    logic: IF provider 為 openrouter 且未覆寫 THEN model_name = google/gemini-3.7-flash；Design 預設保持不變
    violation: 組態錯誤，測試失敗
    source: FR2.3, FR2.4

  - id: BR2.1
    statement: Review 串流增量必須映射為既有 suggestion_delta 事件
    category: constraint
    applies_to: ReviewSuggestionStream, AssessmentReviewSession
    trigger: Review graph 產生文字增量時
    logic: IF Review 產出增量文字 THEN 對外 SSE type 必須為 suggestion_delta 且累積語意與現況相容
    violation: 前端無法顯示即時建議；契約測試紅燈
    source: FR3.2, FD-Q3

  - id: BR2.2
    statement: AssessmentPage 行為與 API URL／事件處理不得因本迁徙而變更
    category: policy
    applies_to: AssessmentReviewSession
    trigger: 前端交付審查時
    logic: IF 本 intent 變更集包含 AssessmentPage THEN 僅允許無行為影響之註解／型別；不得改事件分支或 URL
    violation: Request Changes／回退
    source: FR3.1, FR3.3, FD-Q5

  - id: BR2.3
    statement: Lens 必須以結構化 schema（structured output／tool 節點）產出答案，形狀與現況 orchestrator 消費相容
    category: validation
    applies_to: LensAnswerSet, LensGraphRun
    trigger: Lens graph 完成時
    logic: IF Lens 完成 THEN answers 必須符合既定 schema AND 可被既有 orchestrator 路徑消費
    violation: Lens 階段失敗，向上拋錯（不得靜默空答案假裝成功）
    source: FD-Q2, FR1.1

  - id: BR3.1
    statement: LLM／runtime 硬失敗必須向上傳播，不得靜默成功
    category: policy
    applies_to: ReviewGraphRun, LensGraphRun, AssessmentReviewSession
    trigger: runtime 或模型硬錯誤
    logic: IF 發生硬失敗 THEN 向上拋錯或等價錯誤由 orchestrator／router 轉成既有失敗呈現 AND NOT 以空字串標示成功
    violation: 使用者看到假成功；NFR 違反
    source: FR3, NFR1.1, FD-Q4

  - id: BR3.2
    statement: 錯誤與 SSE 路徑不得洩漏 API key／token 等密文
    category: policy
    applies_to: ReviewGraphRun, LensGraphRun, AssessmentReviewSession, ReviewSuggestionStream
    trigger: runtime／LLM 錯誤轉成 SSE 或 HTTP 錯誤時
    logic: IF 對外呈現錯誤訊息（SSE／HTTP body／log 可見字串）THEN 不得包含 OPENROUTER_API_KEY、ANTHROPIC_AUTH_TOKEN 或其他 provider token／密文；僅允許安全訊息（如 auth_error_message）
    violation: 安全違規；合併阻擋／立即修補
    source: NFR2.1, ADR-0006

  - id: BR3.3
    statement: 評核路徑 logger 名稱必須維持 cloud360.* 慣例
    category: constraint
    applies_to: ReviewGraphRun, LensGraphRun
    trigger: 撰寫或修改評核相關 log 時
    logic: IF 評核路徑寫入結構化 log THEN logger 名稱必須以 cloud360. 開頭（例 cloud360.review_agent、cloud360.wa_lens_engine）AND 關鍵階段仍可於 log 辨識
    violation: 可觀測性回歸；測試或審查失敗
    source: NFR1.2

  - id: BR4.1
    statement: 應用程式碼零 ClaudeSDKClient 執行期呼叫後，同一 intent 必須移除映像內 Claude Code CLI
    category: policy
    applies_to: deployment_image
    trigger: FR4.1 驗證通過後
    logic: IF backend 無 ClaudeSDKClient 執行期呼叫 THEN Dockerfile 必須移除 Node 與 @anthropic-ai/claude-code；ELSE 不得移除並記阻擋項
    violation: FR4.4 阻擋部署完成宣告
    source: FR4.1, FR4.2, FR4.4

  - id: BR5.1
    statement: Review 與 Lens 路徑各至少一條自動化測試證明經 langgraph_runtime 且不 import SDK
    category: constraint
    applies_to: ReviewGraphRun, LensGraphRun
    trigger: build-and-test／CI
    logic: IF 本 intent 合併 THEN 存在可自動判定之 Review 測試 AND 存在可自動判定之 Lens 測試 AND 兩者皆斷言經 langgraph_runtime
    violation: CI 紅燈
    source: FR5.1, FR5.2, FD-Q6
```

## 規則摘要

| ID | 類別 | 一句話 |
|---|---|---|
| BR1.1 | policy | A3 LLM 只走 langgraph_runtime |
| BR1.2 | constraint | Review／Lens 雙獨立 graph |
| BR1.3 | policy | 預設 gemini-3.7-flash |
| BR2.1 | constraint | SSE = suggestion_delta |
| BR2.2 | policy | 前端零行為變更 |
| BR2.3 | validation | Lens 結構化 schema |
| BR3.1 | policy | 硬失敗上拋 |
| BR3.2 | policy | SSE／錯誤不洩漏 secret |
| BR3.3 | constraint | logger 維持 cloud360.* |
| BR4.1 | policy | 零 SDK 後移除 CLI |
| BR5.1 | constraint | Review＋Lens 雙測試 |
