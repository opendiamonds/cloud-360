# API Documentation (As-Built)

> Reverse-engineered from routers; detailed contracts also in `frontend-backend-specification.md`.  
> 由 routers 反推；細節合約見 `frontend-backend-specification.md`。


### REST — `/api/auth`

| Method | Path | 目的 |
|---|---|---|
| POST | `/api/auth/login` | 登入，回傳 JWT |
| POST | `/api/auth/register` | 註冊（若開放） |
| GET | `/api/auth/me` | 目前使用者 + permissions |
| Admin | users／role 相關 | 使用者角色管理（J3） |
| Admin | role-permissions | 細項矩陣讀寫（J4） |

### REST — `/api/architecture`

| Method | Path | 目的 |
|---|---|---|
| POST | `/api/architecture/generate` | NL 產圖／局部更新；SSE 回傳 message／progress／xml／error |

需 JWT；套用架構圖 story 權限（A1 語意）。

### REST／WS — `/api/collab`

| Method | Path | 目的 |
|---|---|---|
| GET | `/workspace/bootstrap` | last-opened 圖 + 聊天 |
| PUT | `/workspace/last-opened` | 記錄上次開啟圖 |
| GET/POST/PUT/DELETE | `/diagrams`… | 架構圖 CRUD |
| GET/PUT/DELETE | `/diagrams/{id}/chat` | 聊天讀寫／清空 |
| — | share 相關 | `diagram_shares` |
| WS | `/ws/{workspace_id}` | XML 共編廣播 |

### 資料模型（摘要）

| Model | 重點欄位／關係 |
|---|---|
| User | username、password_hash、role、is_active、last_opened_diagram_id |
| UserDiagram | owner、xml、title |
| DiagramShare | diagram ↔ user、權限 |
| UserDiagramChat | user_id + diagram_id → messages |
| RolePermission | role × story_id × can_view／edit／review |
