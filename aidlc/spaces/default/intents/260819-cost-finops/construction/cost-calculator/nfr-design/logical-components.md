# Logical Components — cost-calculator

> Unit: `cost-calculator` · library · Q1=A 單模組

## 1. 邏輯元件圖

```text
cost_service (cost-api)
        |  in-memory LineForCalc[]
        v
 cost_calculator.py  ← 本 unit 唯一元件
        |
        +-- hourly_from_monthly(M)
        +-- line_subtotal(hourly, hours)
        +-- total_priced(lines)
        +-- pie_buckets(lines)
        +-- is_overspent(total, budget)
```

無 I/O、無狀態、無背景執行緒。

## 2. 元件職責

| 元件 | 職責 | 非職責 |
|---|---|---|
| `cost_calculator` | Decimal 算術；`ROUND_HALF_UP` 出口；pie 最大餘數法 | SKU、XML、HTTP、RBAC、audit |
| （無其他） | — | — |

## 3. 常數契約

| 名稱 | 值 | 消費者 |
|---|---|---|
| `DAYS_PER_MONTH` | 30 | `line_subtotal` |
| `HOURS_PER_MONTH_LIST` | 730 | `hourly_from_monthly` |

非設定檔；變更需 ADR。

## 4. 與 FD 對齊

- `total_priced`：**先加精確小計，出口量化一次**（非逐列量化再加）
- `pie_buckets`：四桶量化後之和 **必須等於** `total_priced`（最大餘數法）
- `is_overspent`：不在此量化；B2 `banner_for` 重用

## 5. 無新增基礎設施

| 類型 | 本期 |
|---|---|
| Cache / Redis | ❌ |
| Queue / Worker | ❌ |
| 獨立 microservice | ❌ |

## 6. Code Gen 檢查清單

- [ ] `backend/cost/cost_calculator.py` 可被 `cost_service` import
- [ ] `backend/tests/test_cost_calculator.py` Hypothesis 全綠
- [ ] 禁用 import CI gate 通過
