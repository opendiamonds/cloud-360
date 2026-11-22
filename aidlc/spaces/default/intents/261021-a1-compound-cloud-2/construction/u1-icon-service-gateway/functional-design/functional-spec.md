# Functional Specification — U1: u1-icon-service-gateway

> Stage: functional-design (3.1) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u1-icon-service-gateway` (kind: `library`)
> 追溯上游基準：
> - [entities](entities.md)
> - [rules](rules.md)
> - [contract-summary](../../../inception/contract-design/contract-summary.md) (Contract C1, C2)

---

## 1. 行為工作流程與狀態機 (Workflows & State Transition)

### 1.1 圖示查詢標準流程 (Icon Query Workflow)

```mermaid
sequenceDiagram
    autonumber
    participant Caller as U2: CompoundDiagramBuilder
    participant Gateway as U1: fetch_icon_from_n8n
    participant Cache as In-Memory LRU Cache
    participant Remote as External n8n Webhook

    Caller->>Gateway: fetch_icon_from_n8n(service="ec2", provider="compound")
    Gateway->>Cache: 檢查是否命中快取
    alt 快取命中 (Cache Hit)
        Cache-->>Gateway: 回傳快取的 SVG 字串
        Gateway-->>Caller: 回傳 SVG 字串
    else 快取未命中 (Cache Miss)
        Gateway->>Remote: POST /webhook/icon-service (timeout=5.0s, {"service":"ec2","provider":"compound"})
        alt HTTP 200 成功
            Remote-->>Gateway: {"svg": "<svg ...>"}
            Gateway->>Cache: 存入快取
            Gateway-->>Caller: 回傳遠端 SVG
        else 逾時 (> 5.0s) 或 HTTP 404/500/網路異常
            Gateway->>Gateway: 觸發 Fallback: 合成 40x40 灰底文字 SVG (前4字元大寫)
            Gateway->>Gateway: 輸出 WARNING [ICON_FALLBACK] 結構化日誌
            Gateway->>Cache: 存入快取 (保證下次快速回傳)
            Gateway-->>Caller: 回傳本地 40x40 灰底 SVG
        end
    end
```

---

## 2. 領域實體關係圖 (Derived Entity-Relationship View)

```mermaid
erDiagram
    IconQueryRequest ||--|| IconQueryResult : produces
    IconQueryResult ||--o| FallbackSvgSpec : "derived if fallback triggered"

    IconQueryRequest {
        string service
        string provider
    }
    IconQueryResult {
        string svg_content
        boolean is_fallback
        string service_name
        float elapsed_ms
    }
    FallbackSvgSpec {
        int width
        int height
        string bg_color
        string border_color
        string text_color
        string display_text
    }
```

---

## 3. 商業規則彙整與對映 (Derived Rules Summary View)

| Rule ID | 觸發點 | 決策邏輯 (IF...THEN) | 保證結果 |
| :--- | :--- | :--- | :--- |
| **BR1.1** | 構造上行 payload | IF 請求發起 THEN `provider="compound"` | 符合 Contract C1 外部約定 |
| **BR1.2** | 發送網路請求 | IF 呼叫超過 5.0 秒 THEN 立即 abort | 滿足 NFR3 總繪圖時限 $\le 8.0$ 秒 |
| **BR1.3** | 網路失敗 / 404 / 500 / 逾時 | IF 發生任何異常 THEN 回傳灰底 SVG | 絕不對外拋出例外，達成 C2 `no_throw: true` |
| **BR1.4** | Fallback 文字渲染 | IF 字串過長 THEN 截取前 4 碼大寫 | 確保 40x40 圖示文字對比與排版美觀 |
| **BR1.5** | 查詢入口 | IF 已在 LRU 快取中 THEN 直接回傳 | 減少跨網路延遲與外部服務負擔 |

