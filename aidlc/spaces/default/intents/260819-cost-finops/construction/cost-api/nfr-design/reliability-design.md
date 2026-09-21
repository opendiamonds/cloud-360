# Reliability Design — cost-api

> Unit: `cost-api` · service · 承接 `../nfr-requirements/reliability-requirements.md`

## 1. 降級矩陣

| 故障 | 使用者可見行為 | HTTP |
|---|---|---|
| 單 SKU 定價 timeout / 4xx | 該列 `price_fetch_failed`；其餘正常 | 200 snapshot |
| 雲 mode `manual_override_only` | 列 `unpriced`；無 HTTP | 200 |
| 全列無法定價 | `total=null`；pie 空或 0 | 200 |
| Postgres down | 與既有 backend 一致 | 5xx |
| 外網全 down | 多列 miss；頁面仍可用 | 200 |

**原則**：單列失敗 **不** 500 整包。

## 2. 交易邊界

```
align_lines + line mutations:
  BEGIN
    DELETE orphan lines
    INSERT/UPDATE lines
  COMMIT / ROLLBACK on error

cache write:
  僅 PriceHit 後 INSERT/UPDATE（可與 snapshot 同 request，失敗不 corrupt line state）
```

## 3. 狀態一致性

| 操作 | 一致性 |
|---|---|
| PUT hours → GET snapshot | 同 transaction 可見 |
| Cache stale | 過期視 miss；不阻斷讀 |
| Audit | mutation commit 後 insert |

## 4. 依賴可用性

| 依賴 | 策略 |
|---|---|
| Postgres | fail fast 5xx |
| pricing HTTPS | degrade per-line |
| cost_calculator | 純函式；無外部依賴 |

## 5. DR

沿用 deploy 主機備份；**不**新增 RPO/RTO 目標。

## 6. Code Gen 檢查清單

- [ ] `get_snapshot` 外層 try/except 不吞 PriceMiss
- [ ] align_lines rollback 測試
- [ ] 空 lines 仍 200（非 404）
