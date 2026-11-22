# Performance Design — u2-iac-ui

> Q1=A · 對齊 NFR-PERF-UI-1.x 與 U1 90s。

## 請求生命週期

| 步驟 | 設計 |
|---|---|
| 發起 | `AbortController`；timeout ≥ **90s**（D1）；非 LLM 路徑 timeout 明顯大於 U1 p95（session／scan／rewrite **＞2s**；download **＞5s**） |
| 進行中 | busy＋`iac-agent-status`；執行鈕 disabled |
| 切圖／unmount | `abort()`；回應到達若已 stale → **不寫入** state |
| 結束 | 清除 busy；錯誤走 error.code 表 |

## 首屏

- 殼與 aside 資料沿用 Workspace 既有載入；不為 D1 預熱阻塞首屏 3s 目標。

## 不做

- 假進度百分比；RUM SDK。

<!-- confirmed: Looks correct -->
