# NFR Requirements - Unit A1 (Architecture Design Agent)

## 1. 性能與響應時間 (Performance)
* **LLM 回應處理**：所有對話與畫圖請求使用 SSE (Server-Sent Events) 進行串流傳輸，確保使用者能即時看見進度與代理思考過程，首字延遲 (TTFT) 應小於 3 秒。
* **Webhook 外部請求**：向 n8n 查詢服務圖示 SVG 的請求必須設定明確的超時時間（上限 5.0 秒），以防止因 n8n 服務無響應導致整個繪圖 API 掛起。
* **圖示 Fallback**：若圖示取得超時或失敗，必須於 0.5 秒內切換至灰底 fallback 圖示，保證產圖流程不因圖示缺失中斷。

## 2. 安全性與合規性 (Security & Compliance)
* **RBAC 權限管控**：繪圖工具 (`draw_architecture_diagram`) 與對話產生端點均必須受 JWT 機制保護，且發起帳號必須擁有 `A1.edit`（寫入/畫圖）或 `A1.view`（檢視/對話）權限。
* **金鑰安全性**：API 金鑰（如 OpenRouter Key）嚴禁明文寫入程式碼或提交至 git，必須一律通過 `backend/.env` 環境變數注入。

## 3. 可用性與彈性 (Availability & Resiliency)
* **故障降級**：在 OpenRouter 連線失效時，應能回報明確的「外部 AI 服務無法連線」錯誤，而非引發系統崩潰，不影響其他本地資料庫與共編模組的運作。
