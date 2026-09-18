# 技術棧（Technology Stack）

> Reverse Engineering 合成產物｜repo `cloud`｜commit `8c90f40`

## 執行時與語言

| 層 | 語言／執行時 | 備註 |
|---|---|---|
| Frontend | TypeScript ~6.0、React 19.2、瀏覽器 SPA | `frontend/package.json`；Vite 開發／建置 |
| Backend | Python 3（測試見 cpython-313 產物）、FastAPI | `uvicorn` 服務；`fastapi[standard]` |
| Data | PostgreSQL | `psycopg2-binary`、SQLAlchemy ORM |
| Embed | JavaScript（第三方 iframe） | embed.diagrams.net |
| Tooling | Bun（AIDLC 工具鏈）、Node（frontend）、pip | `bun` 用於 `.claude/tools` |

## 框架與主要程式庫版本

### Frontend（npm）

| 套件 | 版本約束 | 用途 |
|---|---|---|
| `react`／`react-dom` | ^19.2.6 | UI |
| `react-router-dom` | ^6.22.0 | SPA 路由 |
| `vite` | ^8.0.12 | 建置／dev server |
| `typescript` | ~6.0.2 | 型別 |
| `tailwindcss`＋`@tailwindcss/postcss` | ^4.3.0 | 樣式 |
| `html2canvas`／`jspdf` | ^1.4.1／^4.2.1 | 匯出 |
| `eslint` 生態 | eslint ^10、typescript-eslint ^8 | Lint |
| `@playwright/test` | ^1.56.0 | e2e |

腳本：`dev`、`build`（`tsc -b && vite build`）、`lint`、`test:e2e`。無 React 單元測試 runner。

### Backend（pip，`requirements.txt`）

| 套件 | 用途 |
|---|---|
| `fastapi[standard]`、`uvicorn`、`pydantic` | HTTP API |
| `sqlalchemy`、`psycopg2-binary` | ORM／DB |
| `passlib[bcrypt]`、`bcrypt`、`pyjwt` | 認證 |
| `claude-agent-sdk` | Agent 編排 |
| `httpx`、`python-dotenv` | HTTP 客戶端／環境 |
| `hypothesis` | Property-based testing（ADR-0006 hard constraint） |

## 建置、部署與品質工具

| 能力 | 工具 |
|---|---|
| Frontend build | Vite 8 + `tsc -b` |
| Backend image | `backend/Dockerfile` |
| Compose staging | `deploy/` |
| CI | `.github/workflows/ci.yml`：repo contract → lint／build → unittest → Docker build |
| Deploy | `.github/workflows/deploy.yml`（合併至 `ut`） |
| Contract | `scripts/validate_repo_contract.py` |
| Agentic WF | gh-aw：contract-guard、pr-reviewer、ui-regression、deploy-doctor、spec-sync 等 |
| Specs | Markdown、Mermaid、draw.io；AIDLC v2 於 `aidlc/` |

安全基線延伸（ADR-0006）預設啟用，與本技術棧並行；production 雲帳號不在本 repo 技術棧範圍。
