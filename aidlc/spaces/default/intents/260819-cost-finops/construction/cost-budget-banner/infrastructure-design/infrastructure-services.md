# Infrastructure Services — cost-budget-banner

> Unit: `cost-budget-banner` · B2

## 1. 後端服務

| 端點 | 依賴 |
|---|---|
| `PUT .../budget` | Postgres `diagram_cost.monthly_budget` |
| `GET /banner` | `visible_diagrams` + `lightweight_total` + `is_overspent` |

**無** 新表；**無** 新外部 HTTP；重用 cost-api DB 與 calculator。

## 2. 與 OQ-3 關係

- banner 聚合不重打 AWS Price List；total 來自已快取 lines／override
- 定價 stub 不影響 banner 邏輯（需有 priced 列才 meaningful）

## 3. 不引入

- 背景 job 預計算超支
- WebSocket push
- 獨立 banner cache

## 4. Code Gen 檢查清單

- [ ] `banner_for` 只掃可見圖
- [ ] audit on budget change
