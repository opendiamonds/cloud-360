# Functional Design Entities — U2: u2-compound-diagram-builder

> Stage: functional-design (3.1) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u2-compound-diagram-builder` (kind: `library`) · **Walking Skeleton**
> 追溯上游基準：
> - [contract-summary](../../../inception/contract-design/contract-summary.md) (Contract C2, C3)
> - [requirements](../../../inception/requirements-analysis/requirements.md) (FR3.1~FR3.3, NFR1, NFR2, CON1)

---

## 1. 領域實體定義模型 (Entity Model YAML)

```yaml
entities:
  - name: CloudContainerSpec
    description: 單一雲端提供商頂層群組容器之幾何位置與資源配置實體
    attributes:
      - name: provider
        type: string
        required: true
        unique: false
        allowed_values: ["aws", "azure", "gcp"]
      - name: container_type
        type: string
        required: true
        allowed_values: ["aws_cloud", "azure_cloud", "gcp_cloud"]
      - name: title
        type: string
        required: true
        description: 容器標題（例如 "AWS Cloud (Center Hub)", "Azure Cloud", "GCP Cloud"）
      - name: x
        type: float
        required: true
        description: 絕對 X 座標
      - name: y
        type: float
        required: true
        default: 40.0
      - name: width
        type: float
        required: true
        description: 容器寬度（AWS 基準 480px，兩翼基準 360px）
      - name: height
        type: float
        required: true
        default: 500.0
      - name: nodes
        type: array
        required: true
        description: 該雲內收斂之服務節點清單
    entity_constraints:
      - "同一圖中 provider 值不可重複"
      - "width 在 AWS 下必須 >= 480.0，在 Azure/GCP 下必須 >= 360.0"

  - name: CrossCloudConnectionSpec
    description: 跨越兩個雲端容器之直角連線與協議標籤規格實體
    attributes:
      - name: source_node_id
        type: string
        required: true
        description: 起點節點之 mxCell ID
      - name: target_node_id
        type: string
        required: true
        description: 終點節點之 mxCell ID
      - name: protocol_name
        type: string
        required: true
        allowed_values: ["Direct Connect", "ExpressRoute", "Cloud Interconnect", "VPN Tunnel", "HTTPS API"]
      - name: edge_style
        type: string
        required: true
        default: "orthogonalEdgeStyle"
      - name: label_bg_color
        type: string
        required: true
        default: "#FFFFFF"
      - name: label_font_color
        type: string
        required: true
        default: "#1E293B"

  - name: MxGraphCompoundDiagram
    description: 最終合成之完整 Draw.io / mxGraph XML 架構圖實體
    attributes:
      - name: xml_content
        type: string
        required: true
        description: 完整合法的 <mxfile> XML 字串
      - name: total_clouds
        type: integer
        required: true
        default: 3
      - name: total_connections
        type: integer
        required: true
      - name: build_duration_ms
        type: float
        required: true
        description: 幾何計算與 XML 組裝總耗時，保證 <= 8000.0 ms
    relationships:
      - target: CloudContainerSpec
        cardinality: "1:N"
        direction: unidirectional
      - target: CrossCloudConnectionSpec
        cardinality: "1:N"
        direction: unidirectional
```

---

## 2. 實體集合說明 (Entity Set Summary)

- `CloudContainerSpec` 定義了 Hub-and-Spoke 幾何模型中各雲頂層 Group Box 的座標與邊界尺寸。
- `CrossCloudConnectionSpec` 嚴格約束了跨雲連線必須採用直角折線與高對比圓角白底標籤。
- `MxGraphCompoundDiagram` 封裝產出之完整 XML 實體，作為前端 DrawioCanvas 渲染之直接資料源。

