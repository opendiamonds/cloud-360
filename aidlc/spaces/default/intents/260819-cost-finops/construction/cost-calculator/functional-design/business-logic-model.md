# Business Logic Model — cost-calculator

> Unit: `cost-calculator`（library）· Q1–Q3=A  
> 上游：`unit-of-work.md`、`unit-of-work-story-map.md`、`requirements.md`、`components.md`、`component-methods.md`、`services.md`。

## 職責邊界

本 library **只做錢的算術**。不讀 DB、不發 HTTP、不 raise `HTTPException`。`cost_service`（`cost-api`）在組 snapshot 前呼叫這裡。

常數（契約，不是設定檔）：

| 符號 | 值 | 用途 |
|---|---|---|
| `DAYS_PER_MONTH` | 30 | 小計 `hourly × hours × 30`（FR-3.3；日數因子，不是「每月工時」） |
| `HOURS_PER_MONTH_LIST` | 730 | 月價 → 小時價 `M/730` |

## 處理序列

```
validate inputs
  → compute exact Decimal (no quantize)
  → at each public function return: ROUND_HALF_UP to 2 places (Q1=A)
```

`total_priced`：**先對未量化的列小計加總，再出口量化一次**（不是 Q1-C 的「每列量化再加」）。

`pie_buckets`（FR-3.4：四類量化後之和**必須等於**量化後 `total_priced`）：

1. 與 `total_priced` 同一批已定價列，用**未量化**小計按 `category` 累加四桶精確值。
2. `total_q = ROUND_HALF_UP(sum of those exact subtotals, 2)`（與 `total_priced` 同一結果）。
3. 四桶各自 `ROUND_HALF_UP` 到兩位後，其和可能與 `total_q` 差 ±0.0N。用**最大餘數法**：依各桶量化前小數部分由大到小，把差額（分）分配到桶上，直到 `compute+database+network+other == total_q`。
4. 空清單：四桶與 total 皆 `0.00`。

公開 `line_subtotal` 仍各自量化（列上顯示）。列小計加總不必等於 `total`；**圓餅四類與總額必須相等**。

## 函式

### `hourly_from_monthly(M)`

`M / 730`，出口兩位。`M < 0` 或非有限 → `ValueError`。

### `line_subtotal(hourly, hours)`

`hourly × hours × 30`。`hours` 為整數且 `>= 0`（0 → `0.00`）。`hourly < 0` 或非有限 → `ValueError`。覆寫與官方價走同一公式，只是 `hourly` 來源不同（C1-5 `O × h × 30`）。

### `total_priced(lines)`

只納入 `status ∈ {priced, manual_override}` 且 `hourly` 非空的列。在函式內重算精確小計。`unpriced`／`price_fetch_failed` 不進總額（FR-1.6、C1-2）。出口量化一次。空清單 → `0.00`（呼叫端可改顯示為未完成估價，那是 UI／service）。

### `pie_buckets(lines)`

同樣只納入已定價列。用呼叫端給的 `category`；不在 `{compute, database, network, other}` 內 → `other`（Q2=A）。四鍵皆在，缺類為 `0.00`。

### `is_overspent(total, budget)`

`budget is None` → `False`。`total > budget` → `True`。相等 → `False`。不在此量化（呼叫端傳已量化的 total／budget）。

## 不在本 unit

SKU 對照、XML 擷取、快取、HTTP 422、圓餅 SVG。
