# 實體模型：U6 `langgraph-runtime`

本 Unit 為 library，**不擁有資料庫表**。下列為執行期值物件／結果形狀；屬性型別為邏輯型別。建議圖節點與 Advice 實體屬 U7，不在此列。

## Source of truth

```yaml
entities:
  - name: OpenRouterSettings
    description: OpenAI 相容路徑的連線設定（與 claude-agent-sdk／llm_provider 平行）
    attributes:
      - { name: apiKeyEnvName, type: string, required: true, const: "OPENROUTER_API_KEY" }
      - { name: baseUrl, type: string, required: true, const: "https://openrouter.ai/api/v1" }
      - { name: defaultModel, type: string, required: true, description: "預設模型 slug；可由呼叫端覆寫" }
    constraints:
      - "apiKey 值不得寫入本實體的持久化或字串化輸出；僅以「是否存在」在執行期檢查"

  - name: GraphHandle
    description: 呼叫端（U7）已編譯的圖物件之邏輯代稱；本 Unit 不擁有圖拓樸
    attributes:
      - { name: compiled, type: opaque, required: true, description: "已 compile 的圖；由呼叫端傳入" }
    constraints:
      - "本 Unit 不得內建成本建議節點或提示詞"

  - name: GraphState
    description: 圖執行的輸入／輸出狀態（結構由呼叫端定義）
    attributes:
      - { name: payload, type: object, required: true, description: "任意狀態映射；runtime 不詮釋業務欄位" }

  - name: StreamEvent
    description: stream_graph 產出的單次事件
    attributes:
      - { name: kind, type: string, required: true, description: "事件種類（由底層串流對應，如 updates／messages）" }
      - { name: data, type: object, required: true }
    constraints:
      - "事件不得夾帶 apiKey 明文"

  - name: InvokeOutcome
    description: invoke_graph 的唯一成功回傳形狀（不得改為回傳裸 GraphState）
    attributes:
      - { name: state, type: GraphState, required: true, description: "終態；呼叫端經 outcome.state 讀取" }

  - name: RuntimeAuthError
    description: 缺金鑰或設定不足時的領域錯誤（非 HTTP）
    attributes:
      - { name: code, type: enum, required: true, allowed_values: [missing_openrouter_api_key] }
      - { name: message, type: string, required: true, constraint: "含環境變數名；不得含金鑰值" }
```

## 摘要

| 實體 | 角色 |
|---|---|
| OpenRouterSettings | OpenAI 相容連線設定 |
| GraphHandle | 呼叫端編譯後的圖 |
| GraphState | 圖狀態（不詮釋業務） |
| StreamEvent | 串流事件 |
| InvokeOutcome | 同步執行結果 |
| RuntimeAuthError | 缺金鑰等領域錯誤 |

無生命週期狀態機（執行一次、結果交還呼叫端）。
