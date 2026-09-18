# Code Structure

> Brownfield file inventory for Construction modifications.  
> 供 Construction 修改時參考的現況檔案清單。


### Build System

| 區域 | 類型 | 設定 |
|---|---|---|
| Frontend | npm / Vite | `frontend/package.json`、`vite.config.ts` |
| Backend | Python pip | `backend/requirements.txt`；本機 `uvicorn main:app` |
| Contract | Python script | `scripts/validate_repo_contract.py` |
| Deploy | Docker Compose | `docker-compose.yml`、`deploy/docker-compose.deploy.yml` |
| CI | GitHub Actions | `.github/workflows/ci.yml`、`deploy.yml` |

### 模組階層

```text
backend/
  main.py                 # FastAPI app + CORS + startup init_db
  database.py / models.py
  services/
    auth.py, user_router.py, rbac.py, rbac_seed_data.py
    agent_router.py, design_agent.py, diagram_builder.py
    collab_router.py
  tests/test_rbac.py
frontend/src/
  pages/   Login, Workspace, Admin, RolePermissions, Forbidden
  components/ ChatBox, DrawioCanvas, ShareModal, Sidebar, Layout, RouteGuard
  context/AuthContext.tsx
  hooks/useCollaboration.ts
  config/api.ts
```

### 現有檔案清單（核心）

| 路徑 | 職責 |
|---|---|
| `backend/main.py` | App 入口、CORS、router 掛載、startup |
| `backend/database.py` | Engine、session、init_db／seed |
| `backend/models.py` | SQLAlchemy models |
| `backend/services/auth.py` | JWT、password、`get_current_user` |
| `backend/services/user_router.py` | 登入／註冊／me／Admin user APIs |
| `backend/services/rbac.py` | story action guards |
| `backend/services/agent_router.py` | `/api/architecture` SSE generate |
| `backend/services/design_agent.py` | Agent SDK + OpenRouter env |
| `backend/services/diagram_builder.py` | XML／icon 組裝 |
| `backend/services/collab_router.py` | diagrams、chat、share、bootstrap、WS |
| `frontend/src/pages/WorkspacePage.tsx` | 工作區主頁 |
| `frontend/src/components/ChatBox.tsx` | AI 聊天／產圖 |
| `frontend/src/components/DrawioCanvas.tsx` | 畫布 |
| `frontend/src/hooks/useCollaboration.ts` | WebSocket 共編 |
| `frontend/src/context/AuthContext.tsx` | JWT、`can`／`canArch` |
| `schema_rbac.sql` | 建表 + RBAC seed |
| `scripts/validate_repo_contract.py` | Repo contract |

### 設計模式

| 模式 | 位置 | 用途 |
|---|---|---|
| Bearer JWT + Depends | `auth.py`、routers | API 身分 |
| Capability / story guard | `rbac.py`、RouteGuard | 細項權限 |
| SSE streaming | `agent_router.py` | 產圖進度／XML |
| WebSocket fan-out | `collab_router.py` | 共編 XML |
| Context provider | `AuthContext` | 前端權限狀態 |

### 關鍵依賴

| 依賴 | 用途 |
|---|---|
| FastAPI、SQLAlchemy、psycopg2 | API／ORM／PG |
| PyJWT、bcrypt／passlib | 認證 |
| claude-agent-sdk、httpx | Agent／HTTP |
| React 19、react-router、Vite 8、Tailwind 4 | 前端 |
