# Monitoring Design — `U16 object-picker-ui`

> 撰寫時間 2026-10-18T02:25:30Z（`date -u` 取值）。精簡版（by-reference），理由見 `infrastructure-specification.md` 前言。

## 指標與 log

| 項 | 本單元 | 理由 |
|---|---|---|
| 新 metric | 無 | 本 repo 無前端遙測機制；後端零新增程式 |
| 新 log | 無；選單**不得**輸出主控台訊息 | `OPN-15`，由 lint `no-console` 承載（`security-design.md` §一） |
| 既有後端 log | 建立專案／系統的稽核由 `U7` 的 `create_*` 寫入，不變 | `security-design.md` §七 Audit logging |

## 告警

| 告警 | 本單元 |
|---|---|
| 新增告警規則 | 無 |

## 可觀察的品質訊號（CI）

| 訊號 | 來源 | 失敗意義 |
|---|---|---|
| `npm run lint` 紅 | `ci.yml:198`；選單 lint 區塊 | 選單檔案出現主控台、瀏覽器儲存、`innerHTML`、`RegExp`、直接建立呼叫或 `new WebSocket` |
| `ui-regression` 的 `stats.unexpected` 非 0 | `frontend/tests/e2e/object-picker.spec.ts`、`a11y.spec.ts` 新掃描點 | 請求數上界、單發、斷線關閉、型別邊界、無障礙任一退化 |
