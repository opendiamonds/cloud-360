# Functional Specification — U3: u3-design-agent-compound

> Stage: functional-design (3.1) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)
> 追溯上游基準：
> - [entities](entities.md)
> - [rules](rules.md)
> - [contract-summary](../../../inception/contract-design/contract-summary.md) (Contract C3, C4)

---

## 1. 行為工作流程與狀態機 (Workflows & State Transition)

### 1.1 Agent 意圖識別與 Tool 調用流程 (Agent Execution Workflow)

```mermaid
sequenceDiagram
    autonumber
    participant UI as U4: Frontend ChatBox
    participant Agent as U3: DesignAgent
    participant RBAC as Security Gateway
    participant Builder as U2: CompoundDiagramBuilder

    UI->>Agent: POST /api/v1/chat/stream {"message": "畫一個金融混合雲"}
    Agent->>Agent: 意圖識別：發現多雲關鍵字，標定 provider="compound"
    Agent->>UI: SSE event: status {"stage": "intent_detected", "provider": "compound"}
    Agent->>RBAC: 檢查是否具備 A1.edit 權限
    alt 權限不足
        RBAC-->>Agent: 權限拒絕 (Missing A1.edit)
        Agent->>UI: SSE event: thought "您目前僅具備唯讀權限，無法執行架構圖變更"
    else 權限通過
        RBAC-->>Agent: 權限通過
        Agent->>UI: SSE event: status {"stage": "building_geometry"}
        Agent->>Builder: build_compound_diagram_xml(clouds, connections)
        Builder-->>Agent: 回傳完整 mxGraph XML
        Agent->>UI: SSE event: diagram_generated {"xml": "<mxfile>...", "provider": "compound"}
    end
```

---

## 2. 領域實體關係圖 (Derived Entity-Relationship View)

```mermaid
erDiagram
    AgentToolCallSpec ||--o{ AgentStreamEvent : emits

    AgentToolCallSpec {
        string provider
        string instruction
        array caller_permissions
    }
    AgentStreamEvent {
        string event_type
        string stage
        object payload
    }
```

---

## 3. 商業規則彙整與對映 (Derived Rules Summary View)

| Rule ID | 觸發點 | 決策邏輯 (IF...THEN) | 保證結果 |
| :--- | :--- | :--- | :--- |
| **BR3.1** | 工具調用 | 接受 `provider="compound"` | 滿足 Contract C4 API 規格 |
| **BR3.2** | 執行前防護 | IF 無 `A1.edit` THEN 阻擋調用並回覆警告 | 遵守 ADR-0006 專案基線安全約定 |
| **BR3.3** | 提示詞編譯 | 注入 Hub-and-Spoke 拓撲指引 | 引導模型輸出規範對稱之多雲結構 |
| **BR3.4** | 串流事件推送 | 階段變更時發送 SSE 訊息 | 前端即時感知繪圖狀態 |

