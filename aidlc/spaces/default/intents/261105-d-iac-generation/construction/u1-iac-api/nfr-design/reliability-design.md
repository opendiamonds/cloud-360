# Reliability Design — u1-iac-api

> Q1=A／Q2=A／Q5=A · NFR-REL-1.x。

## 失敗域

| 元件 | 故障 | 行為 |
|---|---|---|
| Generator／LLM | 逾時／5xx | 不寫部分 draft；回錯誤；不重試 |
| Scanner／Checkov | 缺 CLI／非 0／掛死 | 硬逾時（建議 ≤10s 牆鐘）；明確失敗；**不**空成功報告 |
| Redactor | 規則未匹配 | 仍回成功但清單可空；不得留下已知明文樣式 |
| Store | 進程重啟 | 清空；預期行為 |

## Checkov 子行程（Q2=A）

- 同步 `subprocess`；stdin 關；stdout／stderr 大小上限。
- 版本釘選於 tech-stack；啟動探测一次可快取「可用／不可用」旗標於進程生命週期。

## 健康

- 沿用既有平台 `/health`（若有）；本 unit **不**另訂多 AZ failover。
- 可選：readiness 報告 Checkov 是否可用（非阻擋 HTTP 服務啟動——缺 CLI 時僅 D2 失敗）。

## 重試政策

- **執行 POST：不自動重試**（契約）。
- 唯讀 GET 可由客戶端重試；服務端無冪等寫入重放。

<!-- confirmed: Looks correct -->
