# Reliability Requirements — cost-api

> Unit: `cost-api` · service

## REL-A-1 定價失敗降級

- `PriceMiss` / timeout → 列 `price_fetch_failed`；**不** 500 整包 snapshot
- `PriceUnsupported` → `unpriced`
- 單列失敗不阻斷其他列

## REL-A-2 交易

- `align_lines` + PUT _mutations：單 DB transaction；失敗 rollback
- cache 寫入：僅 `PriceHit` 成功後

## REL-A-3 依賴

- Postgres down → 5xx（與既有 backend 一致）
- 外網 down → 降級未定價，**可用** 2xx snapshot

## REL-A-4 無 DR 新需求

沿用 deploy 主機備份；本 intent 不新增 RPO/RTO
