# Functional Design Entities — U1: u1-icon-service-gateway

> Stage: functional-design (3.1) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u1-icon-service-gateway` (kind: `library`)
> 追溯上游基準：
> - [contract-summary](../../../inception/contract-design/contract-summary.md) (Contract C1, C2)
> - [requirements](../../../inception/requirements-analysis/requirements.md) (FR4.1, FR4.2, NFR3, CON2)

---

## 1. 領域實體定義模型 (Entity Model YAML)

```yaml
entities:
  - name: IconQueryRequest
    description: 封裝向外部 n8n Webhook 發起之圖示查詢請求參數實體
    attributes:
      - name: service
        type: string
        required: true
        unique: false
        description: 雲端服務代碼或名稱（例如 ec2, s3, bigquery, aks）
        constraints:
          min_length: 1
          max_length: 64
      - name: provider
        type: string
        required: true
        unique: false
        allowed_values: ["compound"]
        default: "compound"
        description: 固定為小寫 compound，強制驅動外部服務以混合雲多雲模式解析
    entity_constraints:
      - "provider 必須嚴格等於 'compound'，不允許 None 或其他非預期字串"

  - name: IconQueryResult
    description: 圖示擷取之標準回傳結果實體，保證回傳合法向量 SVG
    attributes:
      - name: svg_content
        type: string
        required: true
        unique: false
        description: 合法的 SVG XML 字串或 Data URI，永不為 None 或空字串
      - name: is_fallback
        type: boolean
        required: true
        unique: false
        description: 標記此圖示是否來自本地 40x40 灰底降級合成器
      - name: service_name
        type: string
        required: true
        unique: false
        description: 對應之服務代碼
      - name: elapsed_ms
        type: float
        required: true
        unique: false
        description: 查詢總耗時毫秒數，受到 5.0 秒硬性邊界約束
    relationships:
      - target: IconQueryRequest
        cardinality: "1:1"
        direction: unidirectional
        description: 每個查詢請求產出精確一個結果實體

  - name: FallbackSvgSpec
    description: 降級向量圖示之視覺常數與幾何規範實體
    attributes:
      - name: width
        type: integer
        required: true
        default: 40
      - name: height
        type: integer
        required: true
        default: 40
      - name: bg_color
        type: string
        required: true
        default: "#F1F5F9"
      - name: border_color
        type: string
        required: true
        default: "#CBD5E1"
      - name: text_color
        type: string
        required: true
        default: "#475569"
      - name: display_text
        type: string
        required: true
        description: 截取前 4 個英文字元並轉為大寫居中
```

---

## 2. 實體集合說明 (Entity Set Summary)

- `IconQueryRequest` 保證與外部 n8n 的 payload 契約（Contract C1）一致，將 `provider` 強制鎖定為 `"compound"`。
- `IconQueryResult` 作為程序內 API `fetch_icon_from_n8n()` 的內部傳遞依據，保證無論外部微服務狀態如何，皆回傳不為空的 `svg_content`。
- `FallbackSvgSpec` 固化了本地 SVG 生成之色碼與幾何尺寸，確保在畫布上渲染時維持風格統一與文字清晰可讀。

