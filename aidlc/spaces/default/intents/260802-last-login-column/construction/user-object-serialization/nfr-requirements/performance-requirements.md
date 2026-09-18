# 效能需求 — user-object-serialization（U2）

> Stage: nfr-requirements（Construction 3.2）· Unit: `user-object-serialization`（C-4 ＋ C-9 後端）

> **上游輸入**：本單元的 `../functional-design/business-logic-model.md`（Revision 1 的 envelope 與分頁查詢邏輯）、`../functional-design/business-rules.md`（**BR-P1〜BR-P5**：分頁契約、`total` 獨立計數、`ORDER BY id` 保留、超出範圍非錯誤、不接受非分頁參數）、`../functional-design/domain-entities.md`（`UserListPage` 的四欄皆必填無預設值）。本檔的每一條 NFR 皆為上述功能規則的非功能面展開，不新增行為。
> 本站於 2026-08-10 因 Q1 觸發 scope 擴充而暫停產出；上游（scope Revision 2 → requirements → stories → application-design → units-generation → delivery-planning → functional-design）已全數修訂並核可，本檔為重啟後的產出。

## 本單元的效能主張：設計上界，不是實測值

與 U1 同一立場 —— 下列全部是**設計上可推導的界限**，非量測結果。本 intent 未做效能量測，如實記載。

## P-1 單次回應的資料量有界（這是分頁的主要效能收益）

| 項目 | 值 |
|---|---|
| 上界 | 單次回應至多 `page_size` 筆使用者物件，而 `page_size` 的**上限由框架原生約束強制為 100** |
| 變更前 | **無上界** —— 清單端點回傳全部帳號，回應大小隨帳號數線性成長且無天花板 |
| 由誰保證 | 查詢參數的範圍約束（AD-11）。非法值在進入處理函式**之前**被擋下，故上界不依賴處理函式內的任何檢查 |

**這同時是 NFR-8 的安全面**：無上界的回應既是效能問題，也是「一次把整份帳號清單交出去」的暴露面。同一道約束涵蓋兩者。

## P-2 每次請求兩個查詢，兩者皆為既有索引可服務

分頁把原本的一個查詢變成兩個：

| 查詢 | 用途 | 索引 |
|---|---|---|
| `SELECT count(*) FROM users` | `total` | 全表計數，無索引需求 |
| `SELECT ... ORDER BY id OFFSET ? LIMIT ?` | `items` | `ORDER BY id` 走既有的主鍵索引 |

**不新增索引**（`services.md` Revision 1 已記載）。`total` **不得**由 `len(items)` 導出 —— 那會省下一個查詢，但讓 `total` 在多頁時直接是錯的。

**已知的效能特性（如實記載）**：offset 分頁在**深頁**時，資料庫仍需掃過前面的列。以本系統目前 12 個帳號、上限 100 筆／頁的規模，這在可預見的未來不構成問題；若帳號數成長到需要深頁瀏覽，改用鍵集分頁（keyset）是既定的下一步，但那會與已核可的「頁碼式、可跳頁」決定衝突，屬新的範圍決定。

## P-3 序列化不新增外部呼叫

`is_overdue` 由純函式計算（C-1），時區正規化亦為純函式。**每列的序列化零 I/O**；唯一的額外查詢是既有的待授權申請查詢（`_pending_request_for_user`），它只在該列為 `pending` 時觸發，與本 intent 無關且未被改動。

> **附帶記載**：該既有查詢是**每列一次**的 N+1 形狀。分頁把 N 從「全部帳號」縮小為「至多 100」，因此**分頁順帶改善了它**，但沒有修復它 —— 修復屬既有缺陷，不在本 intent 範圍。

## 明確不承諾的事

- 不承諾任何回應時間數字（無量測）
- 不承諾 offset 分頁在深頁時的效能
- 不修復既有的 N+1 待授權查詢
