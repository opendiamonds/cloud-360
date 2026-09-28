# Performance Design — cost-ui

> Unit: `cost-ui` · ui · 承接 `../nfr-requirements/performance-requirements.md`

## 1. NFR-4 消費端預算

| 起點 | 終點 | 條件 |
|---|---|---|
| GET snapshot **已發出**（圖已選） | `[data-testid="cost-total"]` visible 且含數字 | 後端快取／override；≤50 列 |

**不含**：首次路由進 `/cost`、冷查價等待、Sidebar 展開。

## 2. 互動效能（PERF-U-2）

```
HoursInput onCommitted
  → PUT hours（非法不發）
  → 更新 local snapshot state
  → 重算 total/pie DOM（無 window.location.reload）
```

| 模式 | 行為 |
|---|---|
| Optimistic（可選） | 不採；等 PUT 2xx 再更新（簡化一致性） |
| Error | 保留舊值；toast 或 inline error |

## 3. Bundle 與載入

| 項目 | 設計 |
|---|---|
| Route | `/cost` lazy import（Vite `React.lazy`） |
| Chart | 原生 SVG `<path>`；無第三方 |
| Regions | 建置期 `supportedRegions.ts`（無 runtime API） |

## 4. 渲染熱點

| 元件 | 策略 |
|---|---|
| ResourceTable ≤50 列 | 單次 map；無 virtual scroll |
| PieBreakdown | 4 扇區固定；O(1) |
| PricingAssumptions | 靜態字串拼接 |

## 5. 量測

- Playwright：`cost-total` waitFor visible（staging NFR-4）
- Lighthouse：非 blocking；參考 only

## 6. Code Gen 檢查清單

- [ ] lazy route 註冊於 `App.tsx`
- [ ] PUT hours 不觸發全頁 reload
- [ ] `unpriced_count==0` 時 `cost-unpriced-count` 0 命中
