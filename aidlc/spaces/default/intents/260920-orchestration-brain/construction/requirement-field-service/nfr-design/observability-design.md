# 觀測設計 — `U20 requirement-field-service`

## 〇、載體

| 載體 | 內容 | 讀者 |
|---|---|---|
| 資料列 | `updated_by`、`updated_at`、`cleared_at`、`updated_on_behalf_of` | `U23` 的「最後更新」、稽核 |
| 應用 log | logger `"cloud360.requirement_fields"`（`NFR20.30`） | 維運者 |

不另建稽核表（`ADR-015` 只保留最新值）；不引入指標、告警或追蹤（理由見
`observability-requirements.md` 第四節）。

## 一、log 事件設計

| 事件 | 等級 | 欄位（`extra=` 結構化帶入） | 不得包含 |
|---|---|---|---|
| `requirement_field.denied`（`NFR20.27`） | WARNING | `story_id="K4"`、`action`（view／edit）、`system_id`、`user_id`、`reason`（`pending`／`global`／`not_member`） | 值、代寫標示、例外原文 |
| `requirement_field.written`（`NFR20.28`） | INFO | `system_id`、`agent_group`、`field_key`、`user_id`、`on_behalf`（布林） | 值 |
| `requirement_field.cleared`（`NFR20.28`） | INFO | 同上（`on_behalf` 恆為 false，`BR45.3`） | 值 |
| no-op 清空（`NFR20.29`） | 不記 | — | — |

- `reason` 的三個值分別對應 `BR41.1`、`BR41.2`、`BR41.4`；系統不存在回 404 不記 denied
  （那不是授權拒絕）。
- 事件名寫在 log 訊息開頭，方便以字串搜尋；欄位以 `extra=` 帶入，不拼進訊息字串——拼進字串
  會讓「不得記值」只能靠人工審查保證。

## 二、測試形狀

`unittest` 的 `assertLogs("cloud360.requirement_fields", level=...)`：

- 拒絕案例：恰一筆 WARNING，`record.reason` 正確。
- 寫入案例：送一個含唯一標記字串的值，斷言所有 log 記錄的訊息與 `extra` 欄位都不含該字串。
- 重複清空：第二次無 INFO。

## 三、與使用者可見溯源的分工

「最後更新：由你／由大腦（成本 agent 請求）／從未更新」（`mockups.md` M12）完全由資料列推導，
不讀 log。`never_filled`（含第四種列）的 `FieldView` 一律回 null 的
`updatedAt`／`updatedBy`／`updatedOnBehalfOf`（承 functional-design `review-02` R-06），
避免畫面對一個「從未填過」的欄位顯示最後更新者。
