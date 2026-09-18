# Tech Stack Decisions - Unit A1 (Architecture Design Agent)

## 1. 決定採用：Anthropic Agent SDK × OpenRouter
* **背景**：系統需要利用資深雲端架構師角色，引導使用者完成雲端需求評估（AWS vs GCP）並產出結構化圖面資料。
* **決定理由**：
  * Anthropic Agent SDK 提供原生的工具呼叫與對話流控制機制。
  * 利用 OpenRouter 做為 API 代理，讓後端在不直接連結 Anthropic API 的情況下，使用 Anthropic Claude 3.5 Sonnet 模型，確保對話邏輯與架構圖輸出的高品質。

## 2. 決定採用：n8n 外部 Webhook 為動態 SVG 來源
* **背景**：產出之 draw.io 圖面節點需要顯示精準的雲端服務圖示（GCP 核心 4 色/二色，AWS 圖示）。
* **決定理由**：
  * 將圖示映射與下載邏輯外包給 n8n Webhook，可避免後端程式包入數百張 SVG 靜態資源。
  * 透過 `provider` 參數（AWS/GCP）向 n8n Webhook 進行查詢，可在後端動態拼接出符合 provider 的 base64 圖示樣式。

## 3. 決定採用：絕對座標 + geometries 重組的自研 Builder
* **背景**：傳統 draw.io 產圖高度依賴 XML 元件排版，AI 很難直接生成巢狀 XML。
* **決定理由**：
  * 讓 AI 僅輸出簡易的節點列表（含 X, Y 座標），由後端 `diagram_builder.py` 處理幾何包含關係並自動生成層級 XML，降低了 LLM 對 XML 生成的失誤率。
