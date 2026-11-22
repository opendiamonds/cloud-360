# Business & Validation Rules — U2: u2-compound-diagram-builder

> Stage: functional-design (3.1) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u2-compound-diagram-builder` (kind: `library`) · **Walking Skeleton**
> 追溯上游基準：
> - [contract-summary](../../../inception/contract-design/contract-summary.md) (Contract C2, C3)
> - [requirements](../../../inception/requirements-analysis/requirements.md) (FR3.1~FR3.3, NFR1, NFR2, CON1)
> - [stories](../../../inception/user-stories/stories.md) (US3.1~US3.4)

---

## 1. 商業與幾何佈局規則清單 (Business Rules YAML)

```yaml
rules:
  - id: BR2.1
    statement: 三雲頂層群組容器獨立且套用 GROUP_STYLES 樣式常數
    category: validation
    applies_to: CloudContainerSpec
    trigger: 當初始化各雲頂層容器 mxCell 時
    logic: "IF cloud provider in ['aws', 'azure', 'gcp'] THEN apply corresponding GROUP_STYLES style string"
    violation_behavior: 阻擋建置，確保邊框顏色與品牌樣式嚴格一致
    source: FR3.1

  - id: BR2.2
    statement: Hub-and-Spoke 幾何佈局與 120px 緩衝走廊計算
    category: calculation
    applies_to: CloudContainerSpec
    trigger: 當計算三雲頂層容器 X 座標時
    logic: "Azure_X = 40; AWS_X = Azure_X + Azure_Width + 120; GCP_X = AWS_X + AWS_Width + 120"
    violation_behavior: 容器間距強制重設為 120px，嚴禁群組座標重疊
    source: FR3.2

  - id: BR2.3
    statement: 容器基準寬度 AWS 480px、兩翼 360px
    category: constraint
    applies_to: CloudContainerSpec
    trigger: 當建立容器尺寸時
    logic: "IF provider == 'aws' THEN width >= 480.0 ELSE width >= 360.0"
    violation_behavior: 寬度小於基準值時強制提升至基準值
    source: FR3.2

  - id: BR2.4
    statement: 跨雲連線強制使用 orthogonalEdgeStyle 直角折線
    category: policy
    applies_to: CrossCloudConnectionSpec
    trigger: 當生成跨雲 edge mxCell 樣式時
    logic: "IF connection crosses different clouds THEN style MUST contain 'edgeStyle=orthogonalEdgeStyle;'"
    violation_behavior: 覆蓋樣式字串，禁止使用曲線或穿透斜線
    source: FR3.3

  - id: BR2.5
    statement: 協議標籤圓角純白底色覆蓋且對比度達標
    category: policy
    applies_to: CrossCloudConnectionSpec
    trigger: 當設置連線標籤樣式時
    logic: "labelBackgroundColor MUST BE '#FFFFFF' AND fontColor MUST BE '#1E293B'"
    violation_behavior: 自動注入純白覆蓋樣式，保證對比度達 13.5:1 (符合 WCAG 2.1 AA)
    source: FR3.3

  - id: BR2.6
    statement: 產圖端到端整體時限不超過 8.0 秒
    category: constraint
    applies_to: MxGraphCompoundDiagram
    trigger: 當完成組裝並輸出 XML 時
    logic: "IF build_duration_ms > 8000.0 THEN log WARNING for performance SLA breach"
    violation_behavior: 記錄效能日誌但不中斷回傳
    source: NFR3
```

---

## 2. 規則彙整表 (Rules Summary Table)

| Rule ID | 類別 (Category) | 目標實體 (Applies To) | 核心邏輯簡述 | 追溯來源 (Source) |
| :--- | :--- | :--- | :--- | :--- |
| **BR2.1** | validation | `CloudContainerSpec` | 套用 `GROUP_STYLES` (`aws_cloud`, `azure_cloud`, `gcp_cloud`)。 | FR3.1 / AC3.1.2 |
| **BR2.2** | calculation | `CloudContainerSpec` | 左 Azure ➔ 中 AWS ➔ 右 GCP，相鄰保留 120px 緩衝走廊。 | FR3.2 / AC3.2.2 |
| **BR2.3** | constraint | `CloudContainerSpec` | AWS 基準 480px、兩翼基準 360px。 | FR3.2 / AC3.2.1 |
| **BR2.4** | policy | `CrossCloudConnectionSpec` | 跨雲連線強制 `edgeStyle=orthogonalEdgeStyle;`。 | FR3.3 / AC3.3.1 |
| **BR2.5** | policy | `CrossCloudConnectionSpec` | 標籤白底圓角膠囊覆蓋，對比度 13.5:1 (WCAG 2.1 AA)。 | FR3.3 / AC3.4.2 |
| **BR2.6** | constraint | `MxGraphCompoundDiagram` | 產圖總耗時嚴格限制在 8.0 秒以內。 | NFR3 / AC4.2.3 |

