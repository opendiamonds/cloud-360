# Environment Inventory — A1 混合雲繪圖功能 (Compound Cloud)

> Stage: environment-provisioning (4.2) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

---

## 1. 運行環境清單

- **Staging 運行環境 (ADR-0007)**:
  - 主機位址: `192.168.10.10`
  - 外部入口: `https://cloud360.danniel.cc` (Cloudflare Tunnel 端點保護)
  - 容器執行緒: Docker Engine + Docker Compose
- **外部依賴服務**:
  - **n8n Webhook Service**: 負責提供雲端各服務圖示（上行 `provider="compound"`，包含 5.0 秒逾時中斷保護）
  - **本地向量 SVG 備援**: 當 n8n 未連線時，本地即時生成 40x40 向量降級圖示，無外部外部硬性依賴。

---

## 2. 環境變數盤點

| 環境變數名稱 | 必要性 | 預設值 / 說明 |
| :--- | :---: | :--- |
| `N8N_WEBHOOK_URL` | 選用 | n8n 服務入口，未設定或逾時自動走本地向量圖示降級 |
| `DRAWIO_EMBED_URL` | 選用 | Draw.io 嵌入式位址（預設走官方安全嵌入 iframe） |
| `DATABASE_URL` | 必要 | PostgreSQL Staging 連線字串 |
| `SECRET_KEY` | 必要 | JWT 簽名與 Token 校驗金鑰 |

