# Reliability Design — cost-budget-banner

> Unit: `cost-budget-banner` · B2 · 承接 `../nfr-requirements/reliability-requirements.md`

## 1. 業務規則可靠性

| 條件 | 行為 |
|---|---|
| `monthly_budget IS NULL` | 不計超支；banner inactive（REL-B-1） |
| `total <= budget` | 不列入 overspent |
| 無可見圖 | `{active: false}` |

## 2. 故障降級（REL-B-2）

| 故障 | UI |
|---|---|
| GET `/banner` 5xx | Layout **不 crash**；不顯示橫幅 |
| GET network error | 同上（靜默或 debug log） |
| PUT budget 5xx | 保留舊 budget；列級錯誤 |

## 3. 一致性（REL-B-3）

- `overspent`（CostPage snapshot）與 `banner_for` 共用：
  - 同一 `is_overspent(total, budget)`（cost-calculator）
  - 同一 total 計算規則（priced + manual_override）

避免「頁面未超支、橫幅卻亮」。

## 4. Session dismiss（REL-B-4）

- 非故障；reload 後 banner 再現 — by design（AC-7.3）

## 5. 交易

- PUT budget：單 UPSERT + audit 同事务

## 6. Code Gen 檢查清單

- [ ] banner 與 snapshot overspent 同源測試
- [ ] Layout error boundary 不阻斷 children
