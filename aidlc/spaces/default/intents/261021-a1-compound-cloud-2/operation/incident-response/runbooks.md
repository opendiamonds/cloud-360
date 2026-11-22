# Operational Runbooks — A1 Compound Cloud

> Stage: incident-response (4.5) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

## 1. Runbook-01: n8n 圖示服務無回應 / 連線超時處置

### 1.1 症狀
- 混合雲架構圖生成後，節點圖示呈現灰底純文字佔位圖。
- 後端日誌出現：`WARNING:services.diagram_builder:n8n 取得 <service> 圖示（供應商：compound）回應 HTTP <status>`。

### 1.2 診斷步驟
1. 驗證本機/容器至 n8n 端點之網路連線：
   ```bash
   docker exec -it cloud360-backend-1 curl -v -m 5 "http://192.168.10.10:5678/webhook/cloud-icon?provider=compound&service=eks"
   ```
2. 確認 n8n 服務容器是否健康運行：
   ```bash
   ssh deploy@192.168.10.10 "docker ps | grep n8n"
   ```

### 1.3 處置與復原程序
1. 若 n8n 容器當機，於 staging 主機重啟容器：
   ```bash
   ssh deploy@192.168.10.10 "docker restart n8n"
   ```
2. 若為短暫網路抖動，後端佔位圖降級機制已確保服務不中斷；連線恢復後新產生的圖表將自動取得 SVG 圖示。

---

## 2. Runbook-02: 前端畫布 XML 解析與載入異常

### 2.1 症狀
- 使用者回報架構圖產出後右側畫布未渲染圖形，或呈現 URL 編碼字串（`%3C...`）。

### 2.2 診斷與復原
1. 檢查瀏覽器 Console 是否有 iframe postMessage 阻擋或 decode 錯誤。
2. 檢查 `DrawioCanvas.tsx` 之 `postLoad` 是否正確接收標準 `<mxfile>` 或 `<mxGraphModel>`。
3. 若為本地快取異常，請使用者硬性重整（Cmd+Shift+R）載入最新前端 bundle。
