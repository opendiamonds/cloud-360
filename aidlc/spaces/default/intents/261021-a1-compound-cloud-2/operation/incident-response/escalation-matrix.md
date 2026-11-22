# Incident Escalation Matrix

> Stage: incident-response (4.5) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

## 1. 職能矩陣與升級鏈路 (Escalation Path)

| 事故等級 | 初始回應 (0-15m) | 二級升級 (15-30m) | 決策者升級 (>30m) |
| :--- | :--- | :--- | :--- |
| **P1 (阻斷性)** | 在線 SRE / 後端值班工程師 | 後端架構負責人 + DevOps Lead | 產品技術主管 (Tech Lead) |
| **P2 (主要受損)** | 後端值班工程師 | 後端小組負責人 | SRE Lead |
| **P3 (次要瑕疵)** | 前端 / 後端待命成員 | 次日日常站會排程修復 | — |

## 2. 聯絡窗口與通報渠道
- **即時通訊**: Slack `#cloud360-incidents` (P1 自動 @channel)
- **通報系統**: PagerDuty Escalation Policy `Cloud360-Core-Service`
- **狀態公佈**: `https://status.cloud360.danniel.cc`
