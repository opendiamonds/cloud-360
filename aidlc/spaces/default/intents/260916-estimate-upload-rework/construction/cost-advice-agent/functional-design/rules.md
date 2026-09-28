# 業務規則：U7 `cost-advice-agent`

## Source of truth

```yaml
rules:
  - id: BR7.1
    statement: 省錢建議為 Must；跨雲／品質為 Should
    category: policy
    applies_to: CostAdviceAgent
    trigger: 建議產生
    logic: >
      IF 產出完成 THEN saving_text 必須非空；
      IF 跨雲資料不足 THEN comparison_text 可空且 unavailable_reasons 明示；
      IF 品質檢查本期未交付 THEN 不得用「產生中」佔位，須 unavailable_reasons 標本期未提供
    source: FR5.1, FR5.2, FR5.3

  - id: BR7.2
    statement: 送 LLM 的內容為完整解析結果
    category: constraint
    applies_to: CostAdviceAgent
    trigger: 組 prompt
    logic: IF 呼叫模型 THEN 含品項／規格／數量／金額之解析結果（FE-3）
    source: FR5.4

  - id: BR7.3
    statement: 查價可選且不得捏造現價
    category: policy
    applies_to: CostAdviceAgent, CatalogPriceNote
    trigger: 建議產生中
    logic: >
      IF 呼叫 fetch_hourly 失敗或 Miss THEN 流程繼續；
      正文不得宣稱有現價；可註明無目錄價
    violation: 因查價失敗中止建議或捏造數字
    source: FR5.10, Q5=A

  - id: BR7.4
    statement: 目錄價不得回寫明細
    category: policy
    applies_to: AdviceOrchestrator
    trigger: 查價成功
    logic: IF 取得 PriceHit THEN 僅寫入建議文字／暫存；禁止寫 EstimateLineItem
    source: FR5.5, AH-6

  - id: BR7.5
    statement: 去重與不自動重跑
    category: constraint
    applies_to: AdviceOrchestrator
    trigger: enqueue
    logic: >
      IF Advice.status=generating THEN enqueue no-op；
      IF completed|failed THEN 不自動重跑
    source: Q4=A

  - id: BR7.6
    statement: 五分鐘逾時
    category: policy
    applies_to: AdviceOrchestrator, AdviceEvent
    trigger: started_at 起算
    logic: >
      IF 超過 5 分鐘未完成 THEN status=failed、unavailable_reasons.timed_out、
      SSE type=timeout 後關閉；明細仍可用
    source: NFR1, C3, Q3=A

  - id: BR7.7
    statement: SSE 訂閱者斷線不取消背景工作
    category: policy
    applies_to: AdviceOrchestrator
    trigger: 客戶端斷線
    logic: IF SSE 連線關閉 THEN 背景建議繼續；可重連或改打 REST 快照
    source: F1=B, C3, Q4 contract

  - id: BR7.8
    statement: 授權經 U2 EstimateAccessControl
    category: authorization
    applies_to: advice_stream_router
    trigger: GET stream／內部讀寫前
    logic: IF 呼叫者對 set 不可見 THEN 403／404（與 U2 一致）
    source: contract R-01, F1=B

  - id: BR7.9
    statement: 使用 U6 runtime；不移除 claude-agent-sdk
    category: constraint
    applies_to: CostAdviceAgent
    trigger: 模型呼叫
    logic: IF 推論 THEN 經 langgraph_runtime（OpenRouter）；不改其他 agent 的 CLI 路徑
    source: FR10.2, FR10.3

  - id: BR7.10
    statement: generating 卡住須可清理
    category: reliability
    applies_to: AdviceOrchestrator
    trigger: 啟動或讀取 Advice
    logic: IF status=generating AND now-started_at>5m THEN 標記 failed（timed_out）
    source: OQ-DD3, Q2=A
```
