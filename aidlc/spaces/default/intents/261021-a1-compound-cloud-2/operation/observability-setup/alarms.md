# Observability Alarms & Alerting Rules

> Stage: observability-setup (4.4) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

## 1. 告警規則清單 (Alerting Rules)

| 告警名稱 | 監控指標與條件 | 嚴重性 (Severity) | 評估週期 | 通知管道與動作 |
| :--- | :--- | :--- | :--- | :--- |
| `HighErrorRate` | 混合雲產圖 HTTP 5xx 率 > 2% | Critical (P1) | 5 分鐘連續 2 次 | 觸發 PagerDuty + Slack `#cloud360-ops` |
| `HighLatencyP95` | 產圖延遲 p95 > 8000ms | Warning (P2) | 10 分鐘 | Slack `#cloud360-alerts` |
| `N8nIconOutage` | n8n Webhook 呼叫連續 5 次回傳非 200 | Warning (P2) | 3 分鐘 | Slack `#cloud360-alerts`，自動觸發降級佔位圖 |
| `FrontendXmlDecodeError` | 前端 XML 解碼失敗率 > 0.5% | Warning (P3) | 15 分鐘 | Slack `#cloud360-frontend` |
| `DbPoolExhaustion` | PostgreSQL 連線池使用率 > 85% | Critical (P1) | 3 分鐘 | 自動告警維運團隊 |

## 2. 升級處置流程 (Escalation Runbook)
1. **P1 告警**:
   - 若為 `HighErrorRate`，立即檢查後端容器日誌 `docker logs cloud360-backend-1`。
   - 確認是否為 LLM API 限流、金鑰過期或語法建構異常。
2. **P2 告警 (n8n 降級)**:
   - 檢查 n8n 主機與 Webhook 端點存活性。
   - 後端具備佔位圖保護機制，系統仍可正常出圖，不影響主流程。
