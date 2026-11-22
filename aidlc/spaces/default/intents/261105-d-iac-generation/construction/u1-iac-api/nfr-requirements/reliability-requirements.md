# Reliability Requirements — u1-iac-api

> Unit: `u1-iac-api`（service）· Q5=A · 與 FD in-memory store 一致。

## 可用性姿態

| ID | 聲明 |
|---|---|
| NFR-REL-1.1 | **單進程 best-effort**：可用性跟隨 staging 主機與既有 FastAPI 進程；**不**另訂多 AZ／自動 failover SLO。 |
| NFR-REL-1.2 | 進程重啟／部署／crash → session 清空為**預期行為**（RPO＝進程生命週期；RTO＝使用者重新 D1）。 |
| NFR-REL-1.3 | 錯誤回應須可讓 U2 提示「請重新產生／重新掃描」；不得假裝資料仍在。 |

## 故障域

| 故障 | 預期行為 |
|---|---|
| LLM／OpenRouter 逾時或 5xx | D1 失敗；不寫部分 draft；可重試（手動） |
| Checkov CLI 缺失或非 0 且無法產報告 | D2 明確失敗碼；**不**回空成功報告（Q3=A） |
| 同槽競態 POST | 單 in-flight；其餘依 Q4 拒絕／忽略 |

## 明確不做

- 本輪持久化 session／跨副本複製。
- 執行 POST 自動重試迴圈。
- 將平台可用性宣傳為 99.9%＋（與 Q5=A 矛盾）。

<!-- confirmed: Looks correct -->
