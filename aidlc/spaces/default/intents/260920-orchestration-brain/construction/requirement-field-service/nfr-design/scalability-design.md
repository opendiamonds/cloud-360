# 擴展設計 — `U20 requirement-field-service`

## 〇、擴展單位

embedded：新 router 掛在既有 FastAPI 進程（`/api/requirements`），隨既有後端副本一起擴展，
無狀態（不在行程內保存任何欄位值或授權結論），故任何副本都能服務任何請求，不需黏著。

## 一、資料成長（`NFR20.15`／`NFR20.16`）

- **每系統有效列數 = 當前已宣告欄位數**（第一版 7）。由 `(system_id, agent_group, field_key)`
  唯一鍵與 upsert（`performance-design.md` 第二節）保證：重複寫入同一欄位永遠只動同一列。
- **列數只增不減**：本單元沒有 `DELETE` 敘述。系統刪除由 `U18` 的 `ON DELETE CASCADE` 處理；
  該行為的驗證落在真實 PostgreSQL（`reliability-design.md` 第三節），因為測試用的 SQLite
  預設不開外鍵、不執行 CASCADE（`backend/tests/helpers.py` 未設 `PRAGMA foreign_keys`）。
- **不分頁**：一次讀取的上界是常數（已宣告欄位數），不是使用者可無限增長的集合。

## 二、併發（`NFR20.17`／`NFR20.18`）

| 情境 | 設計 | 結果 |
|---|---|---|
| 同欄兩個併發首寫 | 單一 `INSERT … ON CONFLICT DO UPDATE` | 不撞唯一鍵、不回 500；後提交者的值留下 |
| 同欄兩個併發寫入 | 同上 | 最後寫入者勝（`OPEN-RF20-2`，已揭露） |
| 寫入與清空併發 | 清空為條件式 `UPDATE … WHERE value IS NOT NULL`；寫入為 upsert | 結果必為兩者之一的合法狀態；`U18` 的 CHECK 擋下「有值且已清空」 |
| 兩個併發清空 | 條件式 `UPDATE`：第二個在第一個提交後重新評估 `WHERE`，`value` 已為 null → 0 列 | 只有一個生效，`cleared_at` 與 `updated_by` 屬於先完成者（`BR43.4` 冪等，承 `review-01` R-08） |

**不加鎖**：沒有跨列不變量；每欄獨立一列，PostgreSQL 預設的 READ COMMITTED 加上單一敘述
的列級鎖已足夠。

## 三、容量門檻與自動擴展

不設。本單元不是獨立的擴展單位，沒有自己的擴展觸發條件（理由同
`scalability-requirements.md` 第三節）。
