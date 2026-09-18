# Technology Stack

> As-built stack discovered in the repository.  
> 由 repo 盤點的現行技術棧。


### Programming Languages

| 語言 | 用途 |
|---|---|
| Python 3.x | Backend API、Agent、scripts |
| TypeScript | Frontend SPA |
| SQL | PostgreSQL schema |
| Markdown／Mermaid／HTML | Specs、AIDLC docs、development-plan |

### Frameworks & Libraries

| 項目 | 用途 |
|---|---|
| FastAPI + Uvicorn | HTTP／SSE／WS API |
| SQLAlchemy + psycopg2 | ORM／PostgreSQL |
| React 19 + React Router 6 | UI／路由 |
| Vite 8 + Tailwind 4 | 建置／樣式 |
| Claude Agent SDK | 架構設計 Agent |
| PyJWT + bcrypt | 認證 |

### Infrastructure

| 項目 | 用途 |
|---|---|
| PostgreSQL 15 | 主資料庫 |
| Docker／Compose | 本機 DB 與 staging 服務 |
| Cloudflare Tunnel | Staging 對外入口 |
| GitHub Actions（含 self-hosted runner） | CI 與部署 |
| Adminer | 本機 DB UI（開發） |

### Build Tools

| 工具 | 用途 |
|---|---|
| npm／Vite | Frontend build |
| pip | Backend deps |
| Docker build | Staging images |

### Testing Tools

| 工具 | 現況 |
|---|---|
| pytest（預期） | `backend/tests/test_rbac.py` 存在；CI 尚未跑完整 suite |
| ESLint／tsc | Frontend CI |
| `validate_repo_contract.py` | 契約／雙語檢查 |
