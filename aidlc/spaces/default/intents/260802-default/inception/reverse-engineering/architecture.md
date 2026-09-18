# System Architecture (Reverse Engineered)

> As-built architecture from the current repository (not the aspirational full multi-agent SRS).  
> 依現況 repo 反推的 as-built 架構（非完整 SRS 願景）。


### 系統概覽

Monolith：一個 FastAPI 後端 + 一個 React（Vite）前端 + PostgreSQL。AI 產圖經 Claude Agent SDK → OpenRouter。Staging 部署採 Docker Compose + Cloudflare Tunnel（見 ADR-0007）。

### 架構圖

```mermaid
flowchart TB
  subgraph Client
    FE[React_Vite_SPA]
  end
  subgraph Backend
    Main[main.py]
    Auth[/api/auth]
    Arch[/api/architecture]
    Collab[/api/collab]
    RBAC[rbac.py]
    Agent[design_agent.py]
  end
  subgraph Data
    PG[(PostgreSQL_cloud360)]
  end
  subgraph External
    OR[OpenRouter]
    CF[Cloudflare_Tunnel]
  end

  FE --> Auth
  FE --> Arch
  FE --> Collab
  Auth --> RBAC
  Arch --> Agent
  Agent --> OR
  Collab --> PG
  Auth --> PG
  Arch --> PG
  CF --> FE
```

### 文字替代

```text
SPA -> /api/auth | /api/architecture | /api/collab
architecture -> design_agent -> OpenRouter
all APIs -> PostgreSQL; staging ingress via Cloudflare Tunnel -> frontend nginx
```

### 元件說明

| 元件 | 類型 | 目的 | 依賴 |
|---|---|---|---|
| `frontend` | Application | UI／畫布／權限路由 | backend HTTP／WS |
| `backend` | Application | API、Agent、RBAC | PostgreSQL、OpenRouter |
| `docker-compose.yml` / `deploy/` | Infrastructure | 本機 DB／staging compose | Docker |
| `.github/workflows` | CI/CD | contract、build、deploy、agentic | GitHub Actions |
| `tools/`、`workflows/n8n` | Supporting | MCP／Skill／n8n 範本（非核心執行路徑） | — |

### 關鍵資料流

1. **產圖**：ChatBox → `POST /api/architecture/generate`（JWT）→ Agent SDK → SSE（message／xml）→ DrawioCanvas。  
2. **共編**：DrawioCanvas 變更 → WS `/api/collab/ws/{id}` → 廣播 XML。  
3. **進場**：WorkspacePage → `GET /api/collab/workspace/bootstrap` → last diagram + chat。

### 整合點

| 類型 | 項目 | 用途 |
|---|---|---|
| External API | OpenRouter（Anthropic-compatible） | LLM／Agent |
| Database | PostgreSQL | users、diagrams、shares、chats、role_permissions |
| Optional | `N8N_WEBHOOK_URL` | 架構圖 icon |
| Deploy | Cloudflare Tunnel | 對外 `cloud360.danniel.cc` |
