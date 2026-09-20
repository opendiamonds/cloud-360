# Performance Requirements — cost-api

> Unit: `cost-api` · service · NFR-4

## PERF-A-1 Snapshot 延遲（NFR-4 主落點）

| 條件 | 目標 | 量測 |
|---|---|---|
| 已快取官方價或全 `manual_override`；≤50 列 | **≤ 5s** 自 GET `/api/cost/diagrams/{id}` 起至回應含 `total` | Playwright `cost-total` 或 TestClient + 前端計時 |
| 含冷查價目（cache miss） | **不保證** 5s | 排除 NFR-4 驗收 |

## PERF-A-2 單 SKU 外網

- `pricing_client`：connect **3s** + read **3s**，**0** retry（FD）
- 50 列 worst case：sequential 定價可能超 5s → **依賴 cache 命中**；miss 列標 `price_fetch_failed`/`unpriced`，不阻塞整包 5s 量測場景

## PERF-A-3 Calculator 呼叫

- 純函式 O(n)；n≤50 可忽略 vs I/O

## PERF-A-4 CI

- 不跑 load test；5s 由 **tcms 手動／Playwright** 在 staging 驗（B1 DoD）
