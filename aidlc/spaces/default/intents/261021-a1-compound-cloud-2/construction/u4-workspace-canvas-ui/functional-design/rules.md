# Business & UI Rules — U4: u4-workspace-canvas-ui

> Stage: functional-design (3.1) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u4-workspace-canvas-ui` (kind: `ui`)
> 追溯上游基準：
> - [contract-summary](../../../inception/contract-design/contract-summary.md) (Contract C4)
> - [requirements](../../../inception/requirements-analysis/requirements.md) (FR1.1~FR1.3, NFR5, CON3)
> - [stories](../../../inception/user-stories/stories.md) (US1.1~US1.3)

---

## 1. 前端互動與視覺規則清單 (UI Business Rules YAML)

```yaml
rules:
  - id: BR4.1
    statement: Toolbar 新增混合雲 (Compound) 選項且狀態雙向同步
    category: validation
    applies_to: ProviderSelect
    trigger: 當使用者點擊下拉選單或後端推送多雲事件時
    logic: "IF provider is 'compound' THEN select option and propagate state"
    violation_behavior: 阻擋未知 provider 值
    source: FR1.1

  - id: BR4.2
    statement: 多雲對話意圖識別時自動連動更新 Toolbar 下拉選單
    category: policy
    applies_to: WorkspacePage
    trigger: 當 ChatBox SSE 接收到 provider="compound" 事件時
    logic: "IF event.provider == 'compound' THEN update Toolbar selected state to 'compound'"
    violation_behavior: 自動同步，保證介面狀態一致性
    source: FR1.2

  - id: BR4.3
    statement: Drawio 畫布載入完成後 250ms 自適應視窗置中縮放
    category: calculation
    applies_to: DrawioCanvas
    trigger: 當 mxGraph XML 載入並完成 DOM 排版時
    logic: "Trigger fitWindow with padding=32px within 250ms ease-out animation"
    violation_behavior: 確保四周保留至少 20px 邊距且三雲皆在可視範圍內
    source: FR1.3
```

---

## 2. 規則彙整表 (Rules Summary Table)

| Rule ID | 類別 (Category) | 目標元件 (Applies To) | 核心邏輯簡述 | 追溯來源 (Source) |
| :--- | :--- | :--- | :--- | :--- |
| **BR4.1** | validation | `ProviderSelect` | Toolbar 選項擴充 `{ value: "compound", label: "混合雲 (Compound)" }`。 | FR1.1 / AC1.1.1 |
| **BR4.2** | policy | `WorkspacePage` | ChatBox 接收多雲意圖時自動同步切換 Toolbar 選項。 | FR1.2 / AC1.2.2 |
| **BR4.3** | calculation | `DrawioCanvas` | 產圖後 250ms 內平滑平移縮放至全視窗（四周 padding 32px）。 | FR1.3 / AC1.3.1 |

