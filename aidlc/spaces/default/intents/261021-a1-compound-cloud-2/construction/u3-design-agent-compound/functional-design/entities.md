# Functional Design Entities — U3: u3-design-agent-compound

> Stage: functional-design (3.1) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)
> 追溯上游基準：
> - [contract-summary](../../../inception/contract-design/contract-summary.md) (Contract C3, C4)
> - [requirements](../../../inception/requirements-analysis/requirements.md) (FR2.1~FR2.3, NFR4, CON3)

---

## 1. 領域實體定義模型 (Entity Model YAML)

```yaml
entities:
  - name: AgentToolCallSpec
    description: LLM 調用架構圖繪製工具之參數輸入模型
    attributes:
      - name: provider
        type: string
        required: true
        allowed_values: ["AWS", "Azure", "GCP", "compound"]
        default: "compound"
        description: 繪圖目標提供商，多雲情境統一傳入 compound
      - name: instruction
        type: string
        required: true
        description: 使用者自然語言架構描述提示詞
      - name: caller_permissions
        type: array
        required: true
        description: 呼叫者所持有之 RBAC 權限清單（如 ["A1.read", "A1.edit"]）
    entity_constraints:
      - "必須包含 'A1.edit' 始得執行實際繪圖工具，否則拒絕並終止"

  - name: AgentStreamEvent
    description: SSE 串流傳遞給前端之對話與繪圖狀態事件實體
    attributes:
      - name: event_type
        type: string
        required: true
        allowed_values: ["status", "thought", "diagram_generated", "error"]
      - name: stage
        type: string
        required: false
        allowed_values: ["intent_detected", "building_geometry", "rendering_xml"]
      - name: payload
        type: object
        required: true
        description: 包含 xml、provider 或錯誤文字之 JSON 物件
```

---

## 2. 實體集合說明 (Entity Set Summary)

- `AgentToolCallSpec` 規範了 LangChain / OpenAI Function Calling 工具之參數簽章，確保 Agent 輸出符合結構化約束。
- `AgentStreamEvent` 封裝後端至前端的 Server-Sent Events (SSE)，讓使用者即時掌握繪圖進度。

