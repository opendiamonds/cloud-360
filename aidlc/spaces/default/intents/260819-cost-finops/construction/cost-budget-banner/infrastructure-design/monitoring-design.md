# Monitoring Design — cost-budget-banner

> Unit: `cost-budget-banner` · B2

## 1. Log

| 事件 | level | 欄位 |
|---|---|---|
| GET /banner | INFO | `active`, `count`, `duration_ms` |
| PUT budget | INFO | `diagram_id`, `actor`（不含 budget 若視為敏感 — 可只 log changed） |
| banner 5xx | ERROR | `exc_type` |

## 2. 前端降級

- GET /banner 失敗 → Layout 不 crash（nfr-design REL-B-2）
- 無額外 APM

## 3. Code Gen 檢查清單

- [ ] 失敗不 block Layout children
