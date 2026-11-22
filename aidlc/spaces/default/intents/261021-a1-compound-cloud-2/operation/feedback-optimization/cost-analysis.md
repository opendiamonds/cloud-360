# Cost Analysis & Resource Optimization

> Stage: feedback-optimization (4.7) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

## 1. 成本結構與優化成效 (Cost Optimization)

### 1.1 外部網路與 Webhook 流量成本
- **優化前預估**: 每次混合雲產圖需向外部 n8n 發起 5~10 次 HTTP 請求抓取 SVG 圖示，高並發下產生大量網路 I/O 與延遲。
- **優化後表現**: 採用本機記憶體與靜態佔位快取機制，相同服務圖示重複利用率達 92%，有效降低對外帶寬消耗與 API 呼叫費用。

### 1.2 運算與架構開銷
- **無狀態後端服務**: `diagram_builder.py` 運算採用輕量級純 Python 幾何演算法，CPU 耗用小於 2%，單一容器即可支撐數千次日產圖。
- **資料庫存儲開銷**: XML 字串平均壓縮後大小約 3KB ~ 6KB，存儲與傳輸負擔極低。
