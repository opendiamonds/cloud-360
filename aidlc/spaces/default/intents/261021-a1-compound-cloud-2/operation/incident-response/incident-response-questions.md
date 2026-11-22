# Incident Response Questions & Clarifications

> Stage: incident-response (4.5) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

---

## 1. 故障情境與復原目標 (Failure Scenarios & RTO/RPO)
- **主要故障模式**:
  1. n8n 圖示服務無回應 / 連線超時。
  2. 混合雲跨雲幾何運算例外。
  3. 前端 DrawioCanvas XML 解析異常或 iframe 載入崩潰。
- **復原時間目標 (RTO)**: 核心產圖服務 RTO < 15 分鐘。
- **復原點目標 (RPO)**: 架構圖資料自動儲存與同步 RPO < 1 分鐘。

---

## 2. 升級處置與值班通報 (Escalation & Communication)
- **值班矩陣**: 依嚴重等級（P1/P2/P3）分派 SRE 與後端/前端工程師。
- **溝通管道**: Slack 專屬頻道 `#cloud360-incidents` 與內部 StatusPage。

---

## Consolidated Summary Confirmation

在產出應變指引手冊、應變計畫與升級矩陣前，請確認以下彙整摘要正確無誤：

- **應變手冊 (Runbooks)**: 包含 n8n 圖示連線異常處理、跨雲連線標籤異常修復、後端容器重啟與回退程序。
- **應變計畫 (Incident Plan)**: 包含事故分級定義、應變小組權責劃分、事後復盤 (Post-mortem) 機制。
- **升級矩陣 (Escalation Matrix)**: 明確定義 P1/P2 通報鏈與在線工程支援。

Does this all look correct before I generate the incident response artifacts?
- Looks correct
- Request changes

[Answer]: Looks correct
