# Contract Summary Specification — A1 混合雲繪圖功能 (Compound Cloud Diagram)

> Stage: contract-design (2.8) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游基準：
> - [unit-of-work](../units-generation/unit-of-work.md)
> - [unit-of-work-dependency](../units-generation/unit-of-work-dependency.md)
> - [components](../domain-design/components.md)
> - [requirements](../requirements-analysis/requirements.md)

---

## 1. 系統介面契約總覽 (Contracts Register)

本專案依據建構單元相依圖，確立 4 個正式整合邊界合約，涵蓋單元間內部呼叫與外部 Webhook API：

| # | Provider Unit | Consumer | Mechanism | Owner | 契約目的簡述 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **C1** | `External: n8n Webhook API` | `u1-icon-service-gateway` | HTTP POST (REST) | `u1-icon-service-gateway` | 向外部 n8n 查詢服務向量圖示，上行 `provider="compound"`，限時 5.0 秒。 |
| **C2** | `u1-icon-service-gateway` | `u2-compound-diagram-builder` | In-process Python API | `u1-icon-service-gateway` | 提供具備嚴格型別註解之圖示擷取函式，保證回傳合法 SVG 字串。 |
| **C3** | `u2-compound-diagram-builder` | `u3-design-agent-compound` | In-process Python API | `u2-compound-diagram-builder` | 接收三雲容器與連線規格，組裝並回傳標準 mxGraph XML 字串。 |
| **C4** | `u3-design-agent-compound` | `u4-workspace-canvas-ui` | REST + SSE Stream | `u3-design-agent-compound` | 對話式架構生成、意圖識別廣播與 mxGraph XML 串流傳遞。 |

---

## 2. 契約詳細規格 (Detailed Contract Specifications)

### 2.1 C1: 外部圖示服務通訊契約 (External n8n Webhook API)

```yaml
openapi: 3.0.3
info:
  title: n8n Icon Service Webhook API (Compound Contract)
  version: 1.0.0
  description: 向 n8n 外部微服務查詢服務圖示，強制指定 provider="compound"。
paths:
  /webhook/icon-service:
    post:
      summary: 查詢雲端服務圖示
      operationId: fetchCompoundIcon
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - service
                - provider
              properties:
                service:
                  type: string
                  description: 雲端服務名稱（如 ec2, bigquery, aks）
                  example: ec2
                provider:
                  type: string
                  enum: [compound]
                  description: 必須精確為小寫 compound
                  example: compound
      responses:
        '200':
          description: 成功取得圖示
          content:
            application/json:
              schema:
                type: object
                properties:
                  svg:
                    type: string
                    description: 向量圖示 SVG XML 或 Data URI
            image/svg+xml:
              schema:
                type: string
        '404':
          description: 找不到對應圖示
        '500':
          description: n8n 內部錯誤
```

- **SLA 與容錯約制**:
  - 呼叫端逾時上限嚴格為 5.0 秒。
  - 當遇到 404、500 或 5.0 秒逾時，U1 自動回傳本地 40x40 灰底文字向量 SVG，絕不對外拋出中斷性例外。

---

### 2.2 C2: 圖示擷取函式內部呼叫契約 (In-Process Icon Gateway API)

依據 Units Generation 階段審查建議 R-01，落實嚴格 Python 3.11 型別簽章：

```yaml
shared-schema:
  title: IconGatewayInProcessContract
  version: 1.0.0
  interface:
    module: backend.services.diagram_builder
    function: fetch_icon_from_n8n
    signature: "def fetch_icon_from_n8n(service: str, provider: Literal['compound'] = 'compound') -> str"
    parameters:
      - name: service
        type: str
        description: 服務關鍵字名稱
      - name: provider
        type: Literal["compound"]
        default: "compound"
        description: 雲端提供商代碼，此處統一固定為 compound
    returns:
      type: str
      description: 保證回傳合法的 SVG 內容（或 Data URI），永不為 None
    guarantees:
      no_throw: true
      timeout_seconds: 5.0
      fallback_guaranteed: true
```

---

### 2.3 C3: 混合雲幾何組裝內部呼叫契約 (In-Process Diagram Assembly Contract)

```yaml
shared-schema:
  title: CompoundDiagramBuilderContract
  version: 1.0.0
  models:
    CloudContainerSpec:
      type: object
      properties:
        provider:
          type: string
          enum: [aws, azure, gcp]
        container_type:
          type: string
          enum: [aws_cloud, azure_cloud, gcp_cloud]
        title:
          type: string
        subnets:
          type: array
          items:
            type: string
        nodes:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
              service_name:
                type: string
              label:
                type: string
    CrossCloudConnectionSpec:
      type: object
      properties:
        source_node_id:
          type: string
        target_node_id:
          type: string
        protocol_name:
          type: string
          enum: [Direct Connect, ExpressRoute, Cloud Interconnect, VPN Tunnel, HTTPS API]
        edge_style:
          type: string
          default: orthogonalEdgeStyle
  interface:
    module: backend.services.diagram_builder
    function: build_compound_diagram_xml
    signature: "def build_compound_diagram_xml(clouds: list[CloudContainerSpec], connections: list[CrossCloudConnectionSpec]) -> str"
    returns:
      type: str
      description: 完整合法的 mxGraph XML 字串
```

---

### 2.4 C4: 前後端 Agent 互動與串流契約 (REST & SSE API)

```yaml
openapi: 3.0.3
info:
  title: A1 Design Agent API
  version: 1.0.0
paths:
  /api/v1/chat/stream:
    post:
      summary: 發起多雲對話與架構生成
      operationId: streamDesignChat
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - message
              properties:
                message:
                  type: string
                  example: 畫一個跨 AWS 與 GCP 的金融架構
                provider:
                  type: string
                  enum: [AWS, Azure, GCP, compound]
                  default: compound
      responses:
        '200':
          description: SSE 事件串流
          content:
            text/event-stream:
              schema:
                type: string
                description: |
                  串流事件序列：
                  event: status
                  data: {"stage": "intent_detected", "provider": "compound"}

                  event: diagram_generated
                  data: {"xml": "<mxfile>...", "provider": "compound", "duration_ms": 3200}
```

---

## 3. 契約所有權與演進政策 (Contract Ownership & Evolution Policy)

1. **單一所有權 (Single Ownership)**:
   - 每個契約均由其 Provider Unit 負責維護並簽署；消費者單元不得私自假定未公開之內部行為。
2. **破壞性變更審查 (Breaking Changes Policy)**:
   - 任何涉及欄位更名、刪除或型別改變之變更，必須提前在 Inception 階段發布 ADR，並由 `aidlc-architecture-reviewer-agent` 簽核。
3. **向後相容與寬容讀取 (Additive Safety & Postel's Law)**:
   - 消費者端（如前端 `WorkspacePage`）必須對未知欄位保持寬容忽視（Ignore unknown fields）；提供端新增可選欄位時，不得破壞既有單一雲或舊版呼叫。

---

## 4. 未決問題清單 (Open Questions)

| Contract | Question | Blocks |
| :--- | :--- | :--- |
| **None** | 所有 4 項整合邊界（C1 ~ C4）之型別、逾時上限、資料結構與 SSE 串流事件已達成 100% 閉環與規格定義，無任何未決問題。 | None |

