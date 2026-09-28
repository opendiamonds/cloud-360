# Observability Requirements — estimate-intake-api

> Unit: `estimate-intake-api`（U2）· Q5=A · NFR5。

## 稽核（必做）

| eventType（建議字面） | 何時 |
|---|---|
| `upload` | POST 成功建批次 |
| `share_replace` | PUT shares 成功 |
| `delete` | DELETE 成功 |
| `advice_enqueue` | enqueue 成功 |
| `advice_enqueue_failed` | enqueue 失敗（仍 201） |

欄位：actor、時間、set id、雲別／列數（若適用）；**禁止**金額、rawText、檔案內容。

## 應用日誌

- 結構化欄位：`estimate_set_id`、`user_id`、事件名、`duration_ms`（可選）。
- **禁止** log 金額／raw 列／檔案 bytes／JWT／憑證。
- 同步路徑超過 10s：warning 一級。

## 指標／APM

- **不**新增 OpenTelemetry 或新 APM 套件（Q5=A）。
- 沿用既有 logging 組態即可。

## 前端進度（NFR2）

- **不在本 unit**（U8／U9／SSE U7）。

<!-- confirmed: Looks correct -->
