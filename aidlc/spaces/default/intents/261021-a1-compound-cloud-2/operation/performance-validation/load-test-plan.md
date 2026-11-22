# Load Test Plan — A1 Compound Cloud

> Stage: performance-validation (4.6) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

## 1. 測試目標與場景設計 (Test Objectives & Scenarios)

### 1.1 測試環境與工具
- **測試環境**: 自有 Staging 環境 (`http://192.168.10.10:8000` / `cloud360.danniel.cc`)。
- **測試工具**: Locust / k6 負載測試工具。
- **後端容器**: `cloud360-backend-1` (FastAPI + Uvicorn)。

### 1.2 測試場景清單
1. **場景一：標準混合雲端點負載 (Normal Concurrency)**
   - 並發量: 10 VUs (Virtual Users)。
   - 請求行為: 模擬對話詢問並發起跨 AWS、Azure、GCP 混合雲繪圖請求。
   - 持續時間: 10 分鐘。
2. **場景二：尖峰負載與突波壓力 (Peak & Spike)**
   - 並發量: 20 VUs。
   - 突波階梯: 每 30 秒增加 5 VUs 直至 20 VUs。
   - 持續時間: 15 分鐘。
3. **場景三：前端自適應縮放動畫 (Client Fit Animation)**
   - 測量項目: DrawioCanvas 接收 XML 後 50ms 延遲觸發之 250ms 動畫流暢度。
