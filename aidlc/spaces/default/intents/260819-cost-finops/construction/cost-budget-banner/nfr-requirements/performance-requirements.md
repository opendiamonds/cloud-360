# Performance Requirements — cost-budget-banner

> Unit: `cost-budget-banner` · B2 · 後端 `banner_for` + 前端橫幅

## PERF-B-1 GET /banner

- **非** NFR-4 主路徑（成本頁 5s 不含 banner 聚合）
- 目標：Layout mount 後 **≤ 3s** 內得到回應或安全空 `{active:false}`（staging 手動）
- 實作：`banner_for` 可重用輕量 total 計算；可見圖數 ≤ 使用者圖列表上界（通常 <<100）

## PERF-B-2 前端

- 橫幅不阻塞 CostPage 首屏；fetch 與 CostPage 並行
- session dismiss 僅 CSS/DOM，無 API

## PERF-B-3 PUT budget

- 單列 UPSERT + audit；**< 500ms** p95 非正式目標（同既有 PUT）
