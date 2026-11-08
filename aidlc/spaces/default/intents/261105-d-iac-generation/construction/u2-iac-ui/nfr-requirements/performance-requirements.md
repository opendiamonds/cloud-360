# Performance Requirements — u2-iac-ui

> Unit: `u2-iac-ui`（ui）· Q1=A · 對齊 U1 D1 硬逾時 90s。

## 目標

| ID | 需求 | 目標 |
|---|---|---|
| NFR-PERF-UI-1.1 | D1／D2／D3 執行中 | 顯示 busy＋`iac-agent-status`；按鈕防重送；**不做**假進度百分比 |
| NFR-PERF-UI-1.2 | 前端請求逾時 | ≥ 後端硬逾時（**≥ 90s** 對 D1；非 LLM 路徑可較短但不得＜後端 p95 目標以致誤殺） |
| NFR-PERF-UI-1.3 | 首屏殼（有權進入後） | 互動可用 p95 ＜ **3s**（不含 D1 LLM 等待） |
| NFR-PERF-UI-1.4 | 切圖／忽略 stale | in-flight 回寫不更新 UI；不阻塞導覽 |

## 超時／失敗

- 逾時或錯誤：可重試＋依 `error.code` 文案；保留先前成功預覽（若有）。
- 不因 UI 先 Abort 造成「後端仍成功但 UI 空白」而無說明——失敗態必須可見。

## 不做

- 不定全站 Lighthouse 分數為本 Bolt 阻擋項。
- 不把 U1 LLM 延遲算進「首屏 3s」。

<!-- confirmed: Looks correct -->
