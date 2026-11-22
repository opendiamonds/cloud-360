# Business & Validation Rules — U3: u3-design-agent-compound

> Stage: functional-design (3.1) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)
> 追溯上游基準：
> - [contract-summary](../../../inception/contract-design/contract-summary.md) (Contract C3, C4)
> - [requirements](../../../inception/requirements-analysis/requirements.md) (FR2.1~FR2.3, NFR4, CON3)
> - [stories](../../../inception/user-stories/stories.md) (US2.1, US2.2)

---

## 1. 商業與 Agent 行為規則清單 (Business Rules YAML)

```yaml
rules:
  - id: BR3.1
    statement: Tool 介面容許 provider="compound" 參數
    category: validation
    applies_to: AgentToolCallSpec
    trigger: 當 LLM 產生工具調用時
    logic: "IF tool_call.provider in ['AWS', 'Azure', 'GCP', 'compound'] THEN permit call"
    violation_behavior: 拒絕無效的 provider 參數
    source: FR2.1

  - id: BR3.2
    statement: RBAC 權限管制驗證 A1.edit
    category: authorization
    applies_to: AgentToolCallSpec
    trigger: 當執行 draw_architecture_diagram 工具前
    logic: "IF 'A1.edit' not in caller_permissions THEN refuse tool execution and return friendly Chinese warning"
    violation_behavior: 阻擋繪圖，回傳權限不足文字
    source: FR2.1

  - id: BR3.3
    statement: 系統提示詞引導 Hub-and-Spoke 拓撲與金融語義
    category: policy
    applies_to: AgentToolCallSpec
    trigger: 當組裝 LLM 系統提示詞時
    logic: "System prompt MUST contain multi-cloud centering guideline and business semantic labeling"
    violation_behavior: 提示詞編譯期斷言
    source: FR2.2

  - id: BR3.4
    statement: SSE 狀態即時串流廣播
    category: policy
    applies_to: AgentStreamEvent
    trigger: 當架構圖繪製各階段狀態改變時
    logic: "Emit SSE event with stage and provider"
    violation_behavior: 無，非阻擋性通訊
    source: FR2.3
```

---

## 2. 規則彙整表 (Rules Summary Table)

| Rule ID | 類別 (Category) | 目標實體 (Applies To) | 核心邏輯簡述 | 追溯來源 (Source) |
| :--- | :--- | :--- | :--- | :--- |
| **BR3.1** | validation | `AgentToolCallSpec` | Tool 參數支援 `provider="compound"`。 | FR2.1 / AC2.1.1 |
| **BR3.2** | authorization | `AgentToolCallSpec` | 嚴格要求 `A1.edit` 權限始得繪圖。 | FR2.1 / AC2.1.3 |
| **BR3.3** | policy | `AgentToolCallSpec` | 提示詞納入核心雲置中與連線金融語義規範。 | FR2.2 / AC2.2.1 |
| **BR3.4** | policy | `AgentStreamEvent` | 透過 SSE 串流推送繪圖進度至前端。 | FR2.3 / AC2.1.2 |

