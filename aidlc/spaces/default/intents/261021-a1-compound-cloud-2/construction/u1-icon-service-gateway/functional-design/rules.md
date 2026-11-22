# Business & Validation Rules — U1: u1-icon-service-gateway

> Stage: functional-design (3.1) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u1-icon-service-gateway` (kind: `library`)
> 追溯上游基準：
> - [contract-summary](../../../inception/contract-design/contract-summary.md) (Contract C1, C2)
> - [requirements](../../../inception/requirements-analysis/requirements.md) (FR4.1, FR4.2, NFR3, CON2)
> - [stories](../../../inception/user-stories/stories.md) (US4.1, US4.2)

---

## 1. 商業與驗證規則清單 (Business Rules YAML)

```yaml
rules:
  - id: BR1.1
    statement: 上行 Payload 強制指定 provider="compound"
    category: validation
    applies_to: IconQueryRequest
    trigger: 當建構向 n8n Webhook 發送之請求體時
    logic: "IF request is created THEN provider MUST BE 'compound'"
    violation_behavior: 拋出 ValueError 並阻擋發送非合約之 provider 值
    source: FR4.1

  - id: BR1.2
    statement: 外部通訊嚴格限制 5.0 秒逾時
    category: constraint
    applies_to: IconQueryRequest
    trigger: 當發送 HTTP POST 請求至 ${N8N_WEBHOOK_URL} 時
    logic: "IF http request duration exceeds 5.0s THEN abort and trigger fallback"
    violation_behavior: 捕捉 Timeout 異常，立即切換為本地 Fallback 合成
    source: NFR3

  - id: BR1.3
    statement: 圖示查詢失敗保證優雅降級回傳本地 40x40 向量 SVG
    category: policy
    applies_to: IconQueryResult
    trigger: 當 n8n 回傳 404、500、連線錯誤或逾時觸發時
    logic: "IF external call fails for any reason THEN return valid 40x40 gray-background SVG string"
    violation_behavior: 絕不向調用端拋出中斷性例外，保證回傳值為合法 SVG
    source: FR4.2

  - id: BR1.4
    statement: Fallback 向量圖示文字排版截斷為前 4 字元大寫
    category: calculation
    applies_to: FallbackSvgSpec
    trigger: 當合成本地 40x40 向量 SVG 時
    logic: "IF service name length > 4 THEN display_text = uppercase(service[:4]) ELSE uppercase(service)"
    violation_behavior: 無，確定性計算保證
    source: FR4.2

  - id: BR1.5
    statement: 圖示查詢結果程序內 LRU 快取
    category: policy
    applies_to: IconQueryResult
    trigger: 當接收到重複之 (service, provider) 圖示查詢時
    logic: "IF key in lru_cache THEN return cached SVG directly without HTTP call"
    violation_behavior: 快取擊中時跳過外部網路請求
    source: CON2
```

---

## 2. 規則彙整表 (Rules Summary Table)

| Rule ID | 類別 (Category) | 目標實體 (Applies To) | 核心邏輯簡述 | 追溯來源 (Source) |
| :--- | :--- | :--- | :--- | :--- |
| **BR1.1** | validation | `IconQueryRequest` | 上行 payload 之 provider 強制固定為小寫 `compound`。 | FR4.1 / AC4.1.1 |
| **BR1.2** | constraint | `IconQueryRequest` | 外部 HTTP POST 設置嚴格 5.0 秒超時上限。 | NFR3 / AC4.1.2 |
| **BR1.3** | policy | `IconQueryResult` | 任何網路失敗或異常保證回傳 40x40 灰底文字向量 SVG，絕不崩潰。 | FR4.2 / AC4.2.1 |
| **BR1.4** | calculation | `FallbackSvgSpec` | 降級 SVG 文字截取前 4 字元大寫置中，確保排版清晰。 | FR4.2 / AC4.2.2 |
| **BR1.5** | policy | `IconQueryResult` | 啟用 `@lru_cache(maxsize=128)` 避免重複網路查詢。 | CON2 |

