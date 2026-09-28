# Stage Memory: contract-design

## Interpretations

- 2026-09-18 — 本站適用：多單元整合邊界＋對外 API（SPA）。units Q7=A 已鎖定正式化範圍為 HTTP＋SSE＋解析器輸出；查價結果不強制。
- 2026-09-18 — 不重問 units 已定的「要不要正式化查價」；只問路徑前綴、契約切分、版本、錯誤／逾時、授權邊界是否納入、解析器 schema 方言。

## Deviations

- 2026-09-18 — F1 解決 Q2／Q5 衝突：維持三份正式契約，授權邊界降為附註。

## Tradeoffs

- 2026-09-18 — Q3=B 引入 `/v1`／`/v2` 重疊：幾乎只有 SPA 仍付雙軌成本，換未來第二客戶端緩衝。
- 2026-09-18 — Q4=B 沿用 `detail` 而非 problem+json：與全站一致，犧牲 RFC 7807 機器可解析性。

## Open questions

- 2026-09-18 — OQ 見 contract-summary.md（cloud_overrides 形狀、timeout 狀態枚舉、SSE 是否進 openapi.json）。
