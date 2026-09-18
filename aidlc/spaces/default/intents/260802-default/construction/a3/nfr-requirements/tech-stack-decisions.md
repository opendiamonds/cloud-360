# A3 Tech Stack Decisions

> Unit `U-A3` · Q7=A — reuse brownfield stack only


### 1. 決策

**完全沿用** Cloud-360 現有堆疊；本 unit **不**新增資料庫以外基礎設施（無 Redis／獨立 worker／新 APM 產品）。

### 2. 對照表

| 層 | 技術 | 用途（A3） |
|---|---|---|
| API | FastAPI | `/api/architecture/reviews*`、SSE |
| ORM／DB | SQLAlchemy + PostgreSQL | `architecture_reviews` |
| Authz | 既有 JWT + `rbac`／`role_permissions` | A3.view／edit |
| 規則 | Python 純函式模組 `wa_rule_engine` | deterministic 評分／findings |
| LLM | **Anthropic Agent SDK** + **OpenRouter**（與 A1 相同執行／env 約定） | `review_agent.py` 建議串流 |
| FE | React + Vite + 既有路由／Sidebar／AuthContext | `/assessment`、Workspace CTA |
| 測試 | unittest + **Hypothesis** | 規則 PBT ≥3；authz 可用 parametrize |
| 可觀測 | 標準 logging（結構化欄位）；metrics **可選** | 無新強制 APM |
| 部署 | 既有 Docker Compose／deploy workflow | 無新服務拓撲 |

### 3. 明確拒絕（本期）

| 選項 | 理由 |
|---|---|
| 第二套 LLM HTTP 客戶端 | 違反 FR-A3-04a／AD |
| Redis／Celery 評核佇列 | Q4=A、Q7=A |
| 新前端 SSE 專用套件 | Q7=A（用 fetch stream／原生即可） |

### 4. 與 A1 對齊點

- 共用 Agent SDK client／OpenRouter 環境變數模式  
- **獨立** MCP／system prompt／模組檔（不合併 `design_agent`）  
