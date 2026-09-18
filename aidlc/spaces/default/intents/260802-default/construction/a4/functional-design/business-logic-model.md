# A4 Business Logic Model — Flows & API


### 1. Bootstrap 還原

```mermaid
sequenceDiagram
  participant FE as WorkspacePage
  participant API as /api/collab
  participant DB as PostgreSQL

  FE->>API: GET /workspace/bootstrap
  API->>DB: user.last_opened + diagram + chat
  API-->>FE: diagram + messages
  FE->>FE: 選圖 + 還原 ChatBox
```

### 2. API 契約

| Method | Path | 說明 |
|---|---|---|
| GET | `/api/collab/workspace/bootstrap` | last_opened + diagram + messages |
| GET/PUT/DELETE | `/api/collab/diagrams/{id}/chat` | 讀／寫／清空聊天 |
| PUT | `/api/collab/workspace/last-opened` | 更新上次開啟圖 |

### 3. 程式對照

| 層 | 檔案 |
|---|---|
| BE | `models.UserDiagramChat`、`database._ensure_a4_schema`、`collab_router` |
| FE | `WorkspacePage` bootstrap／切圖／清空；`ChatBox`「清空對話」 |

### 4. 狀態

Code done；待手動 E2E。見 `a4/code/chat-persistence-summary.md`。
