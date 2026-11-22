# Service Level Objectives (SLO) & Indicators (SLI)

> Stage: observability-setup (4.4) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

## 1. 服務等級目標定義 (SLO Definitions)

### 1.1 可用性目標 (Availability SLO)
- **目標值**: 99.5% 成功率（月度計算）。
- **SLI 計算公式**: `(成功之 2xx / 3xx 產圖請求數) / (總產圖請求數 - 使用者端中斷請求數) * 100%`。
- **錯誤預算 (Error Budget)**: 每月允許 0.5% 的錯誤請求（約等於每月 3.6 小時降級時間）。

### 1.2 延遲目標 (Latency SLO)
- **目標值**: 95% 的混合雲架構生成請求在 5,000ms 內完成第一階段串流推送。
- **SLI 計算公式**: `(耗時 <= 5,000ms 的產圖請求數) / (總有效產圖請求數) * 100% >= 95%`。

### 1.3 前端互動目標 (Frontend Responsiveness SLO)
- **目標值**: 99% 的畫布載入與 fitWindow 縮放自適應在 250ms 內完成動畫渲染。

---

## 2. 錯誤預算消耗原則 (Error Budget Policy)
- 當月度錯誤預算消耗超過 75% 時，暫緩非關鍵功能發布，優先修復穩定性議題。
- 當錯誤預算耗盡（100%）時，啟動架構穩定性審查會議。
