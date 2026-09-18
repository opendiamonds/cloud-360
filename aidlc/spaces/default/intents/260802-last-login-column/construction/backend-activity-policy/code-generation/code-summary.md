# Code Summary — backend-activity-policy（U1）

## 實際產出

| 檔案 | 變更 |
|---|---|
| `backend/services/activity.py` | **新增 101 行**。兩個純函式判定（`should_record_activity`、`is_overdue`）、一個公開的時區正規化（`as_aware_utc`）、一個記錄器（`record_activity`），兩個模組層常數（節流 5 分鐘、門檻 90 天） |
| `backend/models.py` | `+4` 行：`last_activity_at`（帶時區、可為空、**無 server_default**） |
| `backend/services/auth.py` | `+5` 行：import ＋ `get_current_user` 內一行呼叫 |
| `backend/database.py` | `_ensure_last_activity_schema()`（新）掛進 `init_db()` |
| `backend/tests/test_activity.py` | **新增 142 行 / 19 個測試** |
| `schema_rbac.sql`、`DEPLOY.md` | 同步（blocking 義務） |

## 三個實作決定與理由

**1. 記錄器掛在 `get_current_user` 而非各 router** —— 那是所有認證請求的唯一必經點。掛在 router 層會漏（新增 router 時忘記掛），而且會讓「任何有效活動」這個需求變成「記得掛的那些活動」。

**2. 記錄器自行提交，且失敗先復原再記錄** —— 兩者都是契約而非細節。不自行提交：`get_db()` 供應器不提交、唯讀端點本身也不提交，寫入會被整個丟棄。不先復原：session 停在失敗狀態，**後續的權限檢查查詢會一併拋錯**，使用者的請求照樣失敗 —— 一個記錄活動的副作用不該讓主要功能掛掉。

**3. 欄位刻意無預設值** —— 有預設值就無法區分「從未活動」與「剛建立」，而「從未活動」正是上線初期**全部**帳號的狀態，也是「不套用逾期標示」的判定依據。

## 驗證結果

| 項目 | 結果 |
|---|---|
| `tests/test_activity.py` | 19 個測試通過（含 4 個 property-based） |
| 後端全套 | **140 個測試通過**（本 intent 前為 94） |
| import smoke | 通過 |

## 已知缺口的實際處置（超出設計要求的部分）

設計把 C-3 的既有環境補欄記為「無自動化驗證，承接方式為部署後重啟 ＋ 人工核對」。**本輪在真實的 docker stack（PostgreSQL）上實際執行了那次核對**：

```
psql -c "\d users" | grep last_activity_at
  →  last_activity_at | timestamp with time zone |
啟動日誌：INFO:cloud360.database:last_activity schema 檢查完成
```

補欄在真實 PostgreSQL 上確實生效。這不取代設計記載的缺口（自動化測試仍然碰不到這條路徑），但本次交付的這一項已被實際驗證過，不是僅憑推論。
