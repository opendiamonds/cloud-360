# A4 Domain Entities — Chat & Last-Opened Persistence

> Unit `U-A4` · Story A4  
> Retrospective FD（對齊 `a4/code/chat-persistence-summary.md`、`database-schema.md`）


### 實體關係

```text
User 1 ──* UserDiagramChat *── 1 UserDiagram
  │
  └── last_opened_diagram_id → UserDiagram?（可空 FK）
```

### User（擴充欄）

| 欄位 | 說明 |
|---|---|
| `last_opened_diagram_id` | 上次開啟圖；`ON DELETE SET NULL` |

### UserDiagramChat

| 欄位 | 型別 | 說明 |
|---|---|---|
| `user_id` | PK/FK | |
| `diagram_id` | PK/FK | 複合鍵 = **user × diagram** |
| `messages_json` | text | `[{role, content}, ...]` |
| `updated_at` | timestamp | |

### Bootstrap DTO

| 欄位 | 說明 |
|---|---|
| `last_opened_diagram` | 圖 metadata + xml |
| `messages` | 該 user×diagram 聊天 |
