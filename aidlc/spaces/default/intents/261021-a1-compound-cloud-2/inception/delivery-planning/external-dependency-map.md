# External Dependency Map — A1 混合雲繪圖功能 (Compound Cloud Diagram)

> Stage: delivery-planning (2.9) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游基準：
> - [contract-summary](../contract-design/contract-summary.md)
> - [bolt-plan](bolt-plan.md)

---

## 1. 外部相依性盤點與阻礙風險對映 (External Dependencies Register)

| 相依項名稱 | 類型 | 擁有者 / 提供方 | 阻擋之 Bolt | 風險評估與衝擊 | 應對與降級策略 (Fallback Plan) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **n8n Icon Webhook API** | 外部微服務 (HTTP REST) | 外部團隊 / 架構微服務集群 | **Bolt 1** (`bolt-icon-gateway`) | 若 n8n 服務不可用或響應延遲 > 5.0 秒，將造成產圖掛起。 | 實作 5.0s 嚴格逾時；遇到任何異常自動降級回傳本地 40x40 灰底文字 SVG，確保主繪圖流程不中斷。 |
| **Draw.io 內嵌 JavaScript 執行環境** | 前端第三方函式庫 (mxGraph) | 開源生態系 / 前端靜態資源 | **Bolt 4** (`bolt-workspace-canvas`) | 若 Draw.io 畫布載入緩慢或 API 接口不相容，可能影響自適應縮放。 | 沿用專案成熟穩定之 Draw.io 整合框架，透過既有 `DrawioCanvas.tsx` 之 postMessage 通訊協定驅動 `fitWindow`。 |
| **LLM Inference API** | 模型服務 (OpenAI / Azure / Bedrock) | 雲端提供商 | **Bolt 3** (`bolt-design-agent`) | 若模型輸出 JSON 格式偏離或意圖識別失敗。 | 透過嚴格 Prompt 規範與 Tool Call Schema 強制型別校驗，並於失敗時提供清晰錯誤反饋。 |

---

## 2. 交付環境前置準備 (Prerequisites Check)

- [x] 後端 Python 3.11+ 執行環境與 FastAPI 架構。
- [x] 前端 Vite + React 18 + TypeScript 開發環境。
- [x] 本地 pytest 測試工具鏈配置。
- [x] `N8N_WEBHOOK_URL` 環境變數配置（若未配置預設觸發 Fallback 模式）。

