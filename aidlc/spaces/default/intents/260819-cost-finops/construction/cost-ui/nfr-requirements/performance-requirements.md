# Performance Requirements — cost-ui

> Unit: `cost-ui` · NFR-4 消費端

## PERF-U-1 總額呈現（NFR-4 共同驗收）

- 計時起點：使用者已選圖、GET snapshot **已發出**
- 終點：`data-testid="cost-total"` **可見**且含數字
- 條件：同 NFR-4（快取／override、≤50 列）
- **不含** 首次冷查價等待

## PERF-U-2 互動

- 單列 hours PUT 成功後更新 total/pie **無全頁 reload**（FD）
- 非法 hours **不發** PUT（減少無效 RTT）

## PERF-U-3 Bundle

- 沿用 Vite code-split；cost 頁 lazy route `/cost`
- 不新增 heavyweight chart 函式庫（SVG 原生）
