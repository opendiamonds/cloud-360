# RBAC + Full Schema Migration Notes

### 檔案

- **`schema_rbac.sql`** — **完整**環境部署腳本（建議新環境只跑這支）

### 內含

| 區塊 | 內容 |
|---|---|
| A | `users`、`user_diagrams`、`diagram_shares`（架構圖儲存與分享） |
| B | `user_diagram_chats`、`last_opened_diagram_id`（A4 聊天／上次開啟） |
| E | `architecture_reviews`（A3 評核）＋ `wa_lenses`（A3 可編輯 Offline Lens） |
| C | `role_permissions` + 308 列預設細項權限 |
| D | 預設帳號 `admin` / `admin123`（`Platform_Admin`） |

### 執行

```bash
psql "$DATABASE_URL" -f schema_rbac.sql
# 或
docker exec -i cloud360-db psql -U postgres -d cloud360 < schema_rbac.sql
```

### 注意

- 表皆 `IF NOT EXISTS`，可重複執行。  
- `role_permissions` 每次會清空重播預設；已用 Admin UI 調整過請先備份。  
- 不覆寫既有 `admin` 密碼。  
- `schema.sql` 僅作核心 DDL 參考；完整移轉以 `schema_rbac.sql` 為準。
