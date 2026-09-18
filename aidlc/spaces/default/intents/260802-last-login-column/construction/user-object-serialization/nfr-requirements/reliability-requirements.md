# 可靠性需求 — user-object-serialization（U2）

> **上游輸入**：本單元的 `../functional-design/business-logic-model.md`（Revision 1 的 envelope 與分頁查詢邏輯）、`../functional-design/business-rules.md`（**BR-P1〜BR-P5**：分頁契約、`total` 獨立計數、`ORDER BY id` 保留、超出範圍非錯誤、不接受非分頁參數）、`../functional-design/domain-entities.md`（`UserListPage` 的四欄皆必填無預設值）。本檔的每一條 NFR 皆為上述功能規則的非功能面展開，不新增行為。

## R-1 回應構造不得靜默漏欄位（本單元最主要的可靠性主張）

本 repo 已經發生過這件事：`requested_role` 在兩個更新端點的回應構造中被漏傳，且**至今仍在漏**。本單元新增的欄位若比照現行寫法，會複製同一缺陷。

**兩道獨立的保護，兩者皆採用**：

| 保護 | 機制 | 擋住什麼 |
|---|---|---|
| 欄位**無預設值** | `UserSchema` 的兩個新欄位與 `UserListPage` 的四個欄位皆不設預設值 | 漏傳在**構造當下**就是 `ValidationError`，不會靜默通過（實測：Pydantic 立即拋 `Field required`） |
| **單一共用工廠** | 三個 `UserSchema` 構造點一律經 `_to_user_schema()` | 三處不可能分歧；新增第四個構造點時也只有一個地方要改 |

第二道是 application-design C-4 明文允許的兩個手段之一；本站採**兩者兼具**而非擇一，因為 envelope 的加入使構造點由三處變四處，數量上升則分歧風險上升。

## R-2 時間值必須帶時區位移

**這條看起來像格式問題，實際是可靠性問題**：不帶位移的時間字串會被瀏覽器的 `new Date()` 當成**本地時間**解讀，顯示時間整體偏移一個時區位移量 —— AC-1.6 直接失敗，**而畫面上完全看不出來**（時間格式正確、數字合理，只是錯了幾小時）。

| 項目 | 內容 |
|---|---|
| 風險來源 | 資料庫可能回傳不帶時區的值（SQLite 會，PostgreSQL 不會）。本 repo 的測試環境正是 SQLite |
| 處置 | 序列化前一律經 `as_aware_utc()` 正規化 |
| 驗證 | `test_serialised_timestamp_carries_a_utc_offset` —— **在 SQLite 上跑**，即最會露餡的環境 |

## R-3 `total` 的正確性

`total` **必須**是獨立的計數查詢，不得由 `len(items)` 導出。

由 `len(items)` 導出的實作在「總數少於一頁」時**完全正確**，只在多頁時錯 —— 而目前系統只有 12 個帳號，多頁情境在正式環境不會自然出現。**這條規則的價值就在於讓那個錯誤在測試中被抓到，而不是等到帳號數成長後才在正式環境發現。**

驗證：`test_total_is_a_separate_count_not_len_items`（多頁）＋ `test_three_pagination_values_correct_when_fewer_than_one_page`（單頁，唯一能分辨自我回報式實作的情境）。

## R-4 排序穩定性

`ORDER BY id` **不得**在分頁改動中被移除。沒有確定全序時，`LIMIT`／`OFFSET` 的結果集順序未定義，切頁可能重複或遺漏帳號 —— 而那種失敗是**間歇性**的，CI 對 flaky 的容忍（`retries: 1`、`ui-regression` 容忍 `stats.flaky`）會把它吸收掉。

驗證：`test_same_page_twice_returns_same_order`。**這條斷言偏弱**（不穩定排序未必每次都露餡），如實記載。

## R-5 本單元不改變任何錯誤處理形狀

沿用既有慣例：DB／驗證錯誤直接 `raise HTTPException`，不 try/except 吞掉。本單元**不新增任何 try/except** —— 非法參數由框架處理，查詢失敗沿用既有的傳播路徑。
