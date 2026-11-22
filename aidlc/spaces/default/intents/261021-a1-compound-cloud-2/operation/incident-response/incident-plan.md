# Incident Response Plan — A1 Compound Cloud

> Stage: incident-response (4.5) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

## 1. 事故嚴重性等級定義 (Severity Levels)

| 等級 | 嚴重性 | 判定標準 | 應變時效 (RTO) |
| :--- | :--- | :--- | :--- |
| **P1** | 阻斷性 (Critical) | `/api/generate` 全面中斷，使用者無法產生任何架構圖 | < 15 分鐘 |
| **P2** | 主要功能受損 (Major) | 混合雲產圖成功但跨雲連線遺失、或 n8n 服務長時間失效全部回退佔位圖 | < 60 分鐘 |
| **P3** | 次要瑕疵 (Minor) | 前端適配微調動畫抖動、單一非關鍵圖示顯示缺失 | < 24 小時 |

## 2. 應變作業流程 (Response Lifecycle)
1. **偵測與告警 (Detection)**: CloudWatch 或使用者回報觸發。
2. **通報與召集 (Triage & Mobilization)**: 值班工程師進駐 `#cloud360-incidents` 頻道。
3. **止血與降級 (Mitigation)**: 依 Runbook 執行快速回退或重啟容器。
4. **根因分析與復盤 (Post-mortem)**: 事故結束後 48 小時內產出事後復盤報告，並記錄於 `decisions-log.md`。
