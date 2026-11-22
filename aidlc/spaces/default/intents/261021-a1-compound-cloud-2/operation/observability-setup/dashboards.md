# Observability Dashboards — A1 Compound Cloud

> Stage: observability-setup (4.4) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

## 1. 儀表板架構與分區 (Dashboard Architecture)

### 1.1 核心 Golden Signals 總覽
- **Latency (延遲)**:
  - `p50`, `p95`, `p99` 產圖請求端到端耗時 (目標: p95 < 5000ms)。
  - n8n 圖示 Webhook 呼叫延遲 (目標: p95 < 800ms)。
  - 前端 DrawioCanvas `fitWindow` 平滑縮放動畫耗時 (<250ms)。
- **Traffic (流量)**:
  - 混合雲產圖請求量 (`provider = "compound"` vs 單雲請求量)。
  - WebSocket 協作連線數。
- **Errors (錯誤)**:
  - 4xx / 5xx 錯誤率 (告警門檻: 5 分鐘 > 2%)。
  - n8n 回退佔位圖次數 (`fallback_count` / `fallback_rate`)。
  - 前端 XML 解碼異常計數。
- **Saturation (飽和度)**:
  - 後端 FastAPI worker 併發執行緒池使用率。
  - PostgreSQL 資料庫連線池利用率。

---

## 2. CloudWatch / Grafana Dashboard 佈局定義

```json
{
  "dashboardName": "Cloud360-A1-Compound-Cloud-Metrics",
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "title": "Compound Cloud Generation Latency (p50 / p95)",
        "metrics": [
          ["Cloud360/A1", "GenerationLatency", "Provider", "compound", {"stat": "p50"}],
          ["...", {"stat": "p95"}]
        ],
        "period": 60,
        "region": "ap-northeast-1"
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "n8n Icon Webhook Latency & Error Rate",
        "metrics": [
          ["Cloud360/A1", "N8nWebhookLatency", {"stat": "Average"}],
          ["Cloud360/A1", "N8nFallbackCount", {"stat": "Sum"}]
        ],
        "period": 60,
        "region": "ap-northeast-1"
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Canvas Fit & Render Duration (Frontend)",
        "metrics": [
          ["Cloud360/Frontend", "CanvasFitWindowDuration", {"stat": "Average"}]
        ],
        "period": 60,
        "region": "ap-northeast-1"
      }
    }
  ]
}
```

## 3. 追溯性 (Traceability)
- 映射上游需求: U3 (Hub-and-Spoke 生成), U4 (前端平滑適配)。
- 監控依據: `monitoring-design.md`, `performance-design.md`。
