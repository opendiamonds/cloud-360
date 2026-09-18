# A4 Chat Persistence — Implementation Summary

### 結果

重整／重新進入工作區後，會自動開啟**上次架構圖**並還原該使用者在該圖的**對話紀錄**。聊天鍵值為 **user × diagram**；「清空對話」只刪聊天、不刪圖 XML。

### 資料

| 項目 | 說明 |
|---|---|
| `users.last_opened_diagram_id` | 上次開啟圖（可空 FK） |
| `user_diagram_chats` | `(user_id, diagram_id)` + `messages_json` |

### API（`/api/collab`）

| Method | Path | 說明 |
|---|---|---|
| GET | `/workspace/bootstrap` | last_opened + diagram + messages |
| GET/PUT/DELETE | `/diagrams/{id}/chat` | 讀／寫／清空聊天 |
| PUT | `/workspace/last-opened` | 更新上次開啟圖 |

### 前端

- `WorkspacePage`：bootstrap 還原；切圖載入 chat；對話結束 PUT；存檔後綁定 chat；「清空對話」確認後 DELETE
- `ChatBox`：按鈕文案改為「清空對話」

### 手動驗收

1. 登入 → 開圖 → 對話數輪 → 重整 → 同圖同聊天  
2. 換另一張圖 → 聊天隔離  
3. 清空對話 → 歡迎訊息；畫布 XML 仍在  
4. 無權限 diagram → 403
