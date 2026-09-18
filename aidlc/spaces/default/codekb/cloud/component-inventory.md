# 元件清冊（Component Inventory）

> Reverse Engineering 合成產物｜repo `cloud`｜commit `8c90f40`｜著重 A1／A3 邊界

## Frontend 元件

| 元件 | 路徑 | 職責 | 主要依賴 |
|---|---|---|---|
| `Layout` | `frontend/src/components/Layout.tsx` | 全域殼：固定掛載 Sidebar＋內容區 | `Sidebar` |
| `Sidebar` | `frontend/src/components/Sidebar.tsx` | 導覽、品牌、登出；依 RBAC 顯示 A1／A3／Admin；**固定 `w-64`、扁平 IA** | `useAuth`、`NavLink` |
| `WorkspacePage` | `frontend/src/pages/WorkspacePage.tsx` | A1：聊天、產生、collab 圖狀態、`chatCollapsed`、autosave | `ChatBox`、`DrawioCanvas`、architecture／collab API |
| `AssessmentPage` | `frontend/src/pages/AssessmentPage.tsx` | A3：reviews／lens tabs、選圖、發起審核、預覽 | `DiagramPreviewPanel`、reviews／lens／collab API |
| `DrawioCanvas` | `frontend/src/components/DrawioCanvas.tsx` | diagrams.net iframe 橋：init、load、autosave、toolbar；**缺 save／exit；reload 傷 undo** | embed.diagrams.net、`downloadDrawio` |
| `ChatBox` | `frontend/src/components/ChatBox.tsx` | A1 提示輸入與訊息流 | `WorkspacePage` |
| `DiagramPreviewPanel` | `frontend/src/components/DiagramPreviewPanel.tsx` | A3／唯讀圖預覽 | Draw.io 或靜態預覽 |
| `RouteGuard` | `frontend/src/components/RouteGuard.tsx` | 路由級權限 | `auth-context` |
| `ShareModal` | `frontend/src/components/ShareModal.tsx` | 圖分享 UI | collab share API |
| `LensCriteriaEditor` | `frontend/src/components/LensCriteriaEditor.tsx` | Lens 準則編輯 | lens API |
| `RolePermissionsPage` | `frontend/src/pages/RolePermissionsPage.tsx` | 權限矩陣（含 pillars；側欄尚未對齊巢狀） | `/api/auth/role-permissions` |
| `AdminPage` 等 | `frontend/src/pages/*` | 使用者／授權請求管理 | `/api/auth/*` |
| `auth-context` | `frontend/src/context/*` | token、user、`can`／`canArch` | `/api/auth/me` |

## Backend 元件

| 元件 | 路徑 | 職責 | 主要依賴 |
|---|---|---|---|
| `main` app | `backend/main.py` | 組裝 middleware、router、startup | FastAPI、DB init |
| `agent_router` | `backend/services/agent_router.py` | 架構產生 HTTP 面 | `design_agent`、`wa_collab_orchestrator` |
| `design_agent` | `backend/services/design_agent.py` | LLM 產生；**無平台變更 refusal** | claude-agent-sdk、prompts |
| `diagram_builder` | `backend/services/diagram_builder.py` | 結構 → mxGraph XML；**edge ports／parent hotspot** | n8n icon fetch（可選） |
| `collab_router` | `backend/services/collab_router.py` | 圖 CRUD、chat、share、WS | ORM、auth |
| `review_router` | `backend/services/review_router.py` | 審核 API | orchestrator、DB |
| `review_orchestrator`／`wa_*` | `backend/services/review_*`、`wa_*` | A3 審核編排與評分 | LLM、lens engine |
| `lens_router`／`lens_service` | `backend/services/lens_*` | Lens CRUD／驗證／建議 | `lenses/*.json`、DB |
| `user_router` | `backend/services/user_router.py` | 認證與 RBAC 管理 | `auth`、`rbac` |
| `auth`／`rbac` | `backend/services/auth.py`、`rbac.py` | JWT／password、權限評估與 seed | PostgreSQL |

## 外部與基礎設施元件

| 元件 | 角色 |
|---|---|
| PostgreSQL | 使用者、圖、chat、reviews、role_permissions |
| embed.diagrams.net | 互動圖編輯運行時 |
| OpenRouter／Anthropic-compatible LLM | Agent／review 推理 |
| Staging host + Cloudflare Tunnel | `deploy/` + `deploy.yml` → `cloud360.danniel.cc` |
| Kiwi TCMS | 測案管理（`tcms.danniel.cc`，外部 `dc-infra`） |

元件耦合觀察：A1 的品質同時依賴 `design_agent` 輸出、`diagram_builder` 佈局，以及 `DrawioCanvas` 的載入策略——三處任一變更都可能影響 undo／圖面／儲存體驗，bugfix 應做聯合回歸。
