# Dependencies

> Internal and external dependency map (as-built).  
> 內部／外部相依關係（現況）。


### Internal Dependencies

| From | To | 關係 |
|---|---|---|
| `frontend` | `backend` | HTTP REST + WebSocket（`VITE_API_BASE_URL`） |
| `backend` routers | `auth`／`rbac` | JWT + story guards |
| `agent_router` | `design_agent`／`diagram_builder` | 產圖管線 |
| `collab_router` | `models`／DB | 圖、聊天、分享、WS |
| `database.init_db` | `schema`／seed | 空庫建表與 RBAC seed |
| CI／deploy | `backend`+`frontend` images | 建置與部署 |
| AIDLC docs | `.claude/`＋`aidlc/spaces/*/memory/` | 方法論約束（非 runtime） |

### External Dependencies

| 服務／套件 | 用途 | 設定 |
|---|---|---|
| PostgreSQL | 持久化 | `DATABASE_URL` |
| OpenRouter | LLM | `OPENROUTER_API_KEY`、model env |
| Cloudflare Tunnel | Staging ingress | `deploy/cloudflared/` |
| （選用）n8n webhook | 圖示 | `N8N_WEBHOOK_URL` |

### Dependency Risks

| 風險 | 說明 | 緩解方向 |
|---|---|---|
| OpenRouter／模型可用性 | 產圖核心路徑 | 錯誤 SSE、重試、金鑰分環境 |
| WS 未完整 JWT | 共編安全缺口 | 依 RBAC plan 補 WS JWT |
| 測試覆蓋薄 | 回歸風險 | 擴充 unit／e2e、property-based（extension） |
| Monolith 耦合 | A2／A4／A5 同 collab 模組 | unit 文件分開；程式可漸進拆分 |

```text
frontend --> backend --> PostgreSQL
backend.architecture --> OpenRouter
deploy --> Cloudflare --> frontend
```
