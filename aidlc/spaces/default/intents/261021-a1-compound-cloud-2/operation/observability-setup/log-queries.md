# Saved Log Queries & Aggregations

> Stage: observability-setup (4.4) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

## 1. 集中式日誌查詢範本 (CloudWatch Insights / Loki)

### 1.1 混合雲產圖錯誤查詢
```sql
fields @timestamp, @message, request_id, user_id, provider
| filter provider = "compound" and (status >= 400 or level = "ERROR")
| sort @timestamp desc
| limit 50
```

### 1.2 n8n 圖示抓取與回退事件分析
```sql
fields @timestamp, service_name, status_code, fallback_reason
| filter @message like /n8n.*compound/ or fallback = 1
| stats count() by status_code, bin(5m)
```

### 1.3 畫布載入與 XML 解析異常查詢 (Client-Side)
```sql
fields @timestamp, user_agent, error_type, raw_xml_prefix
| filter error_type like /XmlDecodeError|DrawioPostLoadError/
| stats count() by error_type
```

## 2. 日誌保存策略 (Log Retention)
- Staging 環境日誌保存天數: 14 天。
- Production/Audit 審核日誌保存天數: 90 天。
