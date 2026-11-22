# Security Requirements — U1: u1-icon-service-gateway

> Stage: nfr-requirements (3.2) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u1-icon-service-gateway` (kind: `library`)
> 追溯上游基準：
> - [functional-spec](../functional-design/functional-spec.md)
> - [rules](../functional-design/rules.md)
> - [contract-summary](../../../inception/contract-design/contract-summary.md) (Contract C1, C2)

---

## 1. 安全需求與防護模型 (Security Specifications)

### 1.1 傳輸加密與端點安全 (NFR3.1)
- 向外部 n8n 伺服器發送之 Webhook 請求必須使用 HTTPS 通訊協定（TLS 1.2+），避免中間人攻擊 (MITM) 竊聽服務結構資訊。
- `N8N_WEBHOOK_URL` 僅透過環境變數注入，嚴禁寫死任何主機位址或金鑰於程式碼內。

### 1.2 機密防護與安全日誌 (NFR4.1)
- 在輸出 WARNING `[ICON_FALLBACK]` 結構化日誌時，僅記錄服務名稱與狀態碼，絕不記錄 Authorization Headers、Cookie 或完整環境變數字典。

### 1.3 注入與 XSS 防護 (NFR5.1)
- 本地 40x40 灰底向量 SVG 合成時，對傳入之 `service` 名稱字串執行嚴格字符過濾（僅允許 `[a-zA-Z0-9_-]`），杜絕 SVG 內嵌腳本或 XSS 注入攻擊。
