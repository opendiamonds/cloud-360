# 程式碼結構（Code Structure）

> Reverse Engineering 合成產物｜repo `cloud`｜commit `8c90f40`

## 頂層目錄組織

| 路徑 | 角色 |
|---|---|
| `backend/` | FastAPI 應用、服務層、prompts、lenses、unittest |
| `frontend/` | React SPA（Vite）、元件、頁面、e2e Playwright |
| `deploy/` | Staging Docker Compose 與部署資產 |
| `scripts/` | `validate_repo_contract.py` 等契約／維運腳本 |
| `schema.sql`、`schema_rbac.sql` | 可攜 PostgreSQL DDL／RBAC seed 來源 |
| `aidlc/` | AI-DLC 工作區（memory、intents、codekb、knowledge） |
| `.github/workflows/` | CI、deploy、gh-aw agentic workflows |
| `.claude/` | upstream AI-DLC 框架（升級時覆蓋；規則寫在 `aidlc/.../memory`） |

應用執行時碼與 AIDLC 產物刻意分離：執行時留在 `backend/`／`frontend/`；本檔所在的 `aidlc/spaces/default/codekb/cloud/` 為 space 級程式知識庫。

## Backend 模組分類

```
backend/
  main.py                 # FastAPI app、CORS、router mount、startup init_db
  database.py             # 連線與 schema ensure
  models.py               # SQLAlchemy ORM
  lenses/                 # WA lens JSON（如 cloud360-core-mvp-lens.json）
  prompts/                # design agent system prompt
  services/
    agent_router.py       # POST /generate、/generate-wa-collab
    design_agent.py       # LLM 架構產生
    diagram_builder.py    # groups/nodes/edges → mxGraph XML（A1 hotspot）
    review_router.py      # reviews CRUD、PNG、retry
    review_agent.py / review_orchestrator.py / wa_*  # A3 審核編排
    lens_router.py / lens_service.py / wa_lens_engine.py
    collab_router.py      # diagrams、chat、share、WS
    user_router.py        # auth、users、roles、permissions
    auth.py / rbac.py / rbac_seed_data.py
    wa_collab_orchestrator.py
  tests/                  # unittest + Hypothesis
```

模式：Router 薄、Service 厚；agent／WA 邏輯與 HTTP 邊界分離。DDL 變更須同步 `schema_rbac.sql` 與 `DEPLOY.md`（project Mandated）。

## Frontend 模組分類

```
frontend/src/
  pages/
    WorkspacePage.tsx     # A1：聊天＋畫布＋collab 狀態
    AssessmentPage.tsx    # A3：reviews／lens tabs
    AdminPage.tsx / RolePermissionsPage.tsx / ...
  components/
    Layout.tsx / Sidebar.tsx   # 全域殼層（固定 w-64；UX hotspot）
    DrawioCanvas.tsx           # diagrams.net embed 橋（UX hotspot）
    ChatBox.tsx / DiagramPreviewPanel.tsx / ShareModal.tsx / RouteGuard.tsx
  context/                # auth-context（token、can、canArch）
  utils/                  # apiUrl、downloadDrawio 等
```

模式：頁面擁有資料流與 fetch；畫布透過 controlled `xml`＋`onAutosave`；權限以 hook 門禁而非後端獨斷 UI。

## 慣用模式與熱點檔案

| 模式 | 說明 | 代表檔 |
|---|---|---|
| Streaming／協作生成 | Workspace 呼叫 `generate-wa-collab` 並更新 xml | `WorkspacePage.tsx`、`agent_router.py` |
| Embed 橋接 | iframe `postMessage` 裝載／autosave | `DrawioCanvas.tsx` |
| XML 組裝 | 絕對座標 → 相對 parent → mxCell | `diagram_builder.py` |
| RBAC 矩陣 | 角色 × 故事旗標 | `rbac.py`、`RolePermissionsPage.tsx` |
| Property-based 約束 | agent routing 等核心需 Hypothesis | `backend/tests/` |

與 intent 相關的修改面（blast radius 起點）：`Layout.tsx`、`Sidebar.tsx`、`WorkspacePage.tsx`（`chatCollapsed`）、`DrawioCanvas.tsx`、`diagram_builder.py`、`design_agent.py`、`agent_router.py`。
