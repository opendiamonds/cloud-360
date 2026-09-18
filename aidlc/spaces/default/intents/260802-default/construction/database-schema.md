# Cloud-360 Database Schema (A2 Collaboration + A4 Chat Persistence)

本文件紀錄 A2（多份草稿儲存、精準權限分享）與 A4（user × diagram 聊天持久化、上次開啟圖）的資料庫 Schema。

### 1. 核心關聯圖 (ERD)

```mermaid
erDiagram
    users ||--o{ user_diagrams : "owns"
    users }|--|{ diagram_shares : "shared_with"
    user_diagrams }|--|{ diagram_shares : "is_shared_to"
    users ||--o{ user_diagram_chats : "has_chat"
    user_diagrams ||--o{ user_diagram_chats : "chat_on"
    users }o--o| user_diagrams : "last_opened"

    users {
        int id PK
        string username
        string password_hash
        string role
        boolean is_active
        int last_opened_diagram_id FK "nullable"
    }

    user_diagrams {
        int id PK
        int user_id FK
        string title
        text xml_data
        datetime updated_at
    }

    diagram_shares {
        int user_id PK_FK
        int diagram_id PK_FK
    }

    user_diagram_chats {
        int user_id PK_FK
        int diagram_id PK_FK
        text messages_json
        datetime updated_at
    }
```

### 2. 資料表詳細說明

#### 2.1 `users`
身分驗證與角色；A4 新增 `last_opened_diagram_id`（可空 FK → `user_diagrams.id`，`ON DELETE SET NULL`）。

#### 2.2 `user_diagrams`
每張架構草稿：`id`、`user_id`（Owner）、`title`、`xml_data`、`updated_at`。僅 Owner 可覆寫與分享。

#### 2.3 `diagram_shares`
多對多分享：複合 PK `(user_id, diagram_id)`。

#### 2.4 `user_diagram_chats`（A4）
每位使用者在每張圖上的獨立聊天：複合 PK `(user_id, diagram_id)`；`messages_json` 存 `[{role, content}, ...]`；`updated_at`。

### 3. 權限與 API 重點

- 唯有 Owner 可分享：`POST /api/collab/diagrams/{id}/share`
- 讀寫圖／聊天：Owner 或 `diagram_shares` 成員，否則 403
- Bootstrap：`GET /api/collab/workspace/bootstrap` 還原 last_opened + 該圖 messages
- 清空聊天：`DELETE /api/collab/diagrams/{id}/chat`（不刪 XML）
- WebSocket：`/api/collab/ws/{diagramId}` 僅同步 XML

### 4. 對照實作

- ORM：`backend/models.py`（`User`、`UserDiagram`、`UserDiagramChat`）
- 啟動補 schema：`backend/database.py` → `_ensure_a4_schema()`
- 靜態 SQL：`schema.sql`
