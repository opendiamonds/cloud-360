# 業務規則：U6 `langgraph-runtime`

## Source of truth

```yaml
rules:
  - id: BR10.1
    statement: 成本建議執行路徑使用 LangGraph 圖執行輔助，而非 claude-agent-sdk
    category: policy
    applies_to: invoke_graph, stream_graph, astream_graph
    trigger: U7 呼叫 runtime
    logic: IF 呼叫端透過本 Unit 執行圖 THEN 走 LangGraph 執行路徑；本 Unit 不呼叫 claude-agent-sdk
    violation: 不得在本 Unit 內引入 claude-agent-sdk 呼叫
    source: FR10.1

  - id: BR10.2
    statement: 模型存取走 OpenRouter 的 OpenAI 相容端點，與既有 llm_provider／CLI 路徑平行
    category: policy
    applies_to: OpenRouterSettings
    trigger: 建立客戶端或首次推論
    logic: >
      IF 需要 LLM 客戶端 THEN 使用 baseUrl=https://openrouter.ai/api/v1 與
      OPENROUTER_API_KEY；不得改寫 llm_provider 的 Anthropic／CLI 語意
    violation: 不得把 LangGraph 強制導向 claude-agent-sdk
    source: FR10.2

  - id: BR10.3
    statement: 不得移除 claude-agent-sdk 相依（其他 agent 仍用）
    category: constraint
    applies_to: requirements.txt, Dockerfile／Node 相關相依
    trigger: 相依變更／程式碼審查
    logic: IF 本 Unit 變更相依 THEN claude-agent-sdk 必須仍存在；不得刪除 Node 22／claude-code 以「清理」為由
    violation: 合併阻擋
    source: FR10.3

  - id: BR10.4
    statement: 缺 OPENROUTER_API_KEY 時必須失敗且訊息可診斷
    category: validation
    applies_to: RuntimeAuthError
    trigger: 建構客戶端或發起需金鑰的推論前
    logic: >
      IF 環境中無非空 OPENROUTER_API_KEY THEN 拋 RuntimeAuthError
      （message 含變數名 OPENROUTER_API_KEY；不得含金鑰值或部分遮罩以外的密文）
    violation: 不得靜默成功或 fallback 到 CLI
    source: FR10.2, B2 DoD, Q5=A

  - id: BR10.5
    statement: 圖拓樸與建議語意由呼叫端擁有；runtime 只執行傳入的已編譯圖
    category: constraint
    applies_to: GraphHandle, invoke_graph, stream_graph
    trigger: 任何執行入口
    logic: IF 呼叫 invoke／stream THEN 必須由呼叫端傳入已編譯圖；本 Unit 不得內建成本建議節點、提示詞或三類建議邏輯
    violation: 範圍越界（屬 U7）
    source: U6 boundaries, Q3=A

  - id: BR10.6
    statement: CI 不得因缺少真實 OpenRouter 金鑰而失敗；真實推論為選跑
    category: policy
    applies_to: 測試與 smoke
    trigger: CI／本機驗證
    logic: >
      IF 自動化測試 THEN 使用 mock／假客戶端覆蓋成功與缺金鑰路徑；
      真實 OpenRouter 推論僅經手動或本機選跑 smoke 腳本
    violation: 不得把「CI 必打真 API」設為合併閘門
    source: B2 DoD, Q4=A

  - id: BR10.7
    statement: 串流與同步結果不得外洩金鑰
    category: policy
    applies_to: StreamEvent, InvokeOutcome, 錯誤訊息
    trigger: 執行與錯誤處理
    logic: IF 序列化狀態、事件或例外訊息 THEN 不得包含 apiKey 明文
    violation: 安全缺陷；須修正後才能合併
    source: NFR／ADR-0006 精神, Q5=A

  - id: BR10.8
    statement: invoke_graph 成功時回傳 InvokeOutcome，不以裸 GraphState 作為公開回傳型別
    category: constraint
    applies_to: InvokeOutcome, invoke_graph
    trigger: 同步執行完成
    logic: IF invoke 成功 THEN 回傳 InvokeOutcome 且其 state 欄為終態；呼叫端經 outcome.state 讀取
    violation: 公開 API 型別漂移
    source: functional-design 審閱 R-01

  - id: BR10.9
    statement: 伺服器端 async 路徑必須使用 astream_graph；sync stream_graph 僅供腳本／smoke
    category: constraint
    applies_to: stream_graph, astream_graph
    trigger: 串流執行
    logic: >
      IF 呼叫端位於 async 事件迴圈（例如 FastAPI SSE）THEN 必須使用 astream_graph；
      IF 本機 smoke／同步腳本 THEN 可用 stream_graph；
      兩入口產出相同 StreamEvent 形狀
    violation: 在 async handler 內阻塞迭代 sync Iterator
    source: functional-design 審閱 R-02, Q3=A 精化
```

## 規則摘要

| ID | 一句話 |
|---|---|
| BR10.1 | 成本路徑用 LangGraph，不經 agent-sdk |
| BR10.2 | OpenRouter OpenAI 相容；平行於 llm_provider |
| BR10.3 | 保留 claude-agent-sdk |
| BR10.4 | 缺金鑰大聲失敗 |
| BR10.5 | 圖由 U7 傳入；無建議節點 |
| BR10.6 | CI mock；真推論選跑 |
| BR10.7 | 輸出不洩金鑰 |
| BR10.8 | invoke 回傳 InvokeOutcome |
| BR10.9 | async 用 astream；sync 僅腳本 |
