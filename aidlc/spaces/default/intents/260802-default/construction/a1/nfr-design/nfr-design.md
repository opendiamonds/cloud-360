# NFR Design - Unit A1 (Architecture Design Agent)

## 1. 性能設計 (Performance Design)
* **串流傳輸 (SSE)**：後端 API `/api/architecture/generate` 採用 FastAPI 的 `EventSourceResponse`，將 Design Agent 的執行進度事件與最終產出的 XML 資料以 SSE 格式即時推送至前端。
* **Webhook 超時保護**：在 `diagram_builder.py` 中的 `fetch_icon_from_n8n` 函式，利用 `httpx.AsyncClient` 並明確設定 `timeout=5.0`。若發生超時，會藉由 Python `try-except` 機制擷取，並立即回傳一個在記憶體中生成的灰底 SVG 代替，防止 API 阻斷。

## 2. 安全性設計 (Security Design)
* **RBAC 整合門禁**：
  * 對話端點使用 `AuthContext` 提供的 JWT 進行身份與簽章校驗。
  * 後端在路由層（`agent_router.py`）使用 `check_permission("A1.edit")` 對 `/api/architecture/generate` 進行保護。無此權限的使用者將被拒絕連線。
* **敏感資料保護**：OpenRouter Key (`OPENROUTER_API_KEY`) 由後端伺服器的環境變數管理，不留存於資料庫，前端亦無法存取。

## 3. 可用性設計 (Availability Design)
* **資料庫隔離**：產圖與設計代理主要依賴外部 LLM，若本地 PostgreSQL 資料庫斷線，僅影響「儲存畫布」功能，對話與產圖預覽仍能正常運作。
