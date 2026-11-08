# Developer Code Scan — cloud（focused，intent `261105-d-iac-generation`）

> Link 1 of reverse-engineering pipeline. Breadth: FOCUSED；Depth: Standard。  
> Snapshot 深讀路徑限於派工清單；本檔供 architect 合成 codekb，**不**自行寫入九份 codekb artifacts。  
> 掃描時間（UTC）：`2026-11-05T15:03:59Z`；HEAD：`0bffc82d01cfe01edb1f3f5a8931290d5f885501`。  
> 證據強度：下列主張皆為**實讀原始碼**（非僅 diffstat）。

## Developer Code Scan Results

### Scan Coverage

- **Analyzed deeply**（派工 snapshot；逐檔精讀／對 IaC 相關符號 grep＋關鍵區段 Read）:
  - `frontend/src/pages/WorkspacePage.tsx`
  - `frontend/src/pages/RolePermissionsPage.tsx`
  - `frontend/src/App.tsx`
  - `backend/services/user_router.py`
  - `backend/services/langgraph_runtime.py`
  - `backend/services/agent_router.py`
  - `backend/services/rbac_seed_data.py`
  - `backend/main.py`
  - `openapi.json`（路徑／operation 盤點；無 IaC 端點）

- **Skimmed only**（附近 import／對照模式，目錄粒度，未整檔深讀）:
  - `backend/services/rbac.py`（`require_arch_action`／`require_story_action`／`STORY_IDS`）
  - `backend/services/design_agent.py`（A1 LangGraph＋工具產圖形狀）
  - `backend/cost/cost_advice_agent.py`（C 柱 LangGraph＋`langgraph_runtime` 復用樣板）
  - `backend/cost/advice_stream_router.py`／`advice_orchestrator.py`（SSE／背景 job 形狀）
  - `backend/services/review_agent.py`／`wa_lens_engine.py`（A3 OpenRouter／StateGraph 遷移路徑）
  - `frontend/src/config/api.ts`（`apiUrl` 慣例）
  - `frontend/src/context/auth-context.ts`（`can`／`canArch` 消費面，未整檔）

### Packages Found

- `frontend/` — application — TypeScript／React／Vite — Workspace UI、RBAC 權限頁、路由閘
- `backend/` — application — Python／FastAPI — agent／auth／cost routers、LangGraph runtime、RBAC seed
- （本 focused 掃描未深讀根層 `deploy/`、`scripts/`、測試套件）

### Build System

- **Type**: 前後端分離 monorepo（npm frontend + pip backend）；本輪未重跑建置
- **Config Files**（淺層已知／未重開）: `frontend/package.json`、`frontend/tsconfig*.json`、`backend/requirements.txt`
- **Build Dependencies**: 前端 Vite 建置；後端 uvicorn／FastAPI；CI 另有 OpenAPI dump drift 檢查

### APIs Discovered（與 IaC／對齊 A／C 相關）

| 類型 | 位置 | 端點／方法（本輪） | IaC 相關 |
|---|---|---|---|
| REST＋SSE | `agent_router` @ `/api/architecture` | `POST /generate`、`POST /generate-wa-collab` | 無；產圖入口 |
| REST | `user_router` @ `/api/auth` | `GET/PUT /role-permissions`、`POST …/reset-defaults`、roles catalog | 矩陣含 D1／D2／D3 **標籤＋種子**，無 IaC 業務 API |
| REST＋SSE | cost routers @ `/api/cost/v1` | sets CRUD、`…/advice`、`…/advice/stream` | 無 IaC；**C 柱 LangGraph／SSE 可複用形狀** |
| REST／WS | collab（Workspace 呼叫，淺層） | diagrams／chat／bootstrap／last-opened | 架構圖持久化；非 IaC |
| OpenAPI | `openapi.json` | `iac`／`terraform`／`/api/*d*` 業務路徑 **0 命中** | **無任何 IaC 契約** |

### Frameworks & Libraries（本輪深讀所見）

- FastAPI／Pydantic — HTTP 層與 OpenAPI
- LangGraph（`StateGraph`）— A1 `design_agent`、A3 review／lens、C `cost_advice_agent`
- `langchain_openai.ChatOpenAI` via `langgraph_runtime.openrouter_chat_model` — C／A3 共用 OpenRouter 路徑
- `langchain_anthropic.ChatAnthropic` — A1 design_agent 仍走 Anthropic／Agent-SDK 環境路徑（與 U6 helpers **平行**）
- React Router — `CapabilityRoute` 以 storyId 閘頁
- draw.io iframe（Workspace 畫布）— 產圖成功後 CTA 掛「生成 IaC」stub

### Test Coverage（focused 範圍內觀察）

- **Test Directories**: `backend/tests/`（本輪未深讀；已知有 `test_langgraph_runtime.py`、`test_cost_advice_agent.py`、`test_a3_langgraph_migration.py`）
- **Test Frameworks**: `unittest`＋Hypothesis（team.md 既成事實）
- **Coverage Config**:  absent（無法量測 80%）
- **IaC／D1–D3**: 深讀路徑與 openapi **無**對應測試或端點可掛 TestClient

### Code Quality Indicators

- **Linting**: 前端 ESLint flat config（team.md）；後端無 Ruff／Black
- **CI/CD**: `ci.yml`／`deploy.yml`（本輪未重開檔）
- **Documentation**: `agent_router.py` 模組 docstring 含「契約（前端依賴，請勿變更）」樣板；`langgraph_runtime.py` 明確標示與 `llm_provider`／Claude Agent SDK **平行、不互改語意**

### Technical Debt Signals（對 IaC 意圖有意義）

1. **矩陣領先實作（D1／D2／D3）**：`rbac_seed_data.py`、權限頁標籤、`user_router.STORY_FEATURE_LABELS` 已有 D 柱，但 **無 router／頁／OpenAPI**——與 C1 歷史「種子≠產品」同形（`project.md` reverse-engineering:c9）。
2. **Workspace「生成 IaC 代碼」為 Coming Soon stub**：成功 toast CTA（約 L966–969）呼叫 `showComingSoon('IaC 代碼生成')`（L259–265），**未**檢查 `can('D1', …)`，也**未**打任何 API。
3. **雙 LLM 執行路徑並存**：Workspace 實際產圖走 `POST /api/architecture/generate-wa-collab`（A1↔A3），底層 design 仍偏 Agent SDK／Anthropic；C／A3 建議／評核已遷 `langgraph_runtime`＋OpenRouter。D 柱若對齊 A／C「LangGraph＋Workspace UI」，應預設複用 **U6 `langgraph_runtime`**，避免再長一條 Claude-SDK-only 路徑。
4. **`openapi.json` 對 SSE 端點回應 schema 為空物件**：`/generate`／`generate-wa-collab` 的 200 schema `{}`——契約靠模組 docstring／前端解析慣例，非 OpenAPI 強型別。
5. **ADR-0006 PBT**：IaC generator 為 hard-constraint 落點；repo 尚無 generator 模組 → 約束目前對 D 為「一旦落地即 blocking」。

---

### Intent-focused findings（Story D／對齊 A／C）

#### 1. Workspace「生成 IaC」Coming Soon 入口

- 觸發時機：產圖成功（或 WA collab `passed`／一般成功）toast 且 `showCtas: true` 時，CTA 列顯示「生成 IaC 代碼」。
- 行為：`showComingSoon` → toast「IaC 代碼生成即將推出」＋ hint「此功能尚在規劃中…」，`showCtas: false`。
- 對照：同區塊「Well-Architected」已接真導航 `goWellArchitected()`（權限 `A3`＋diagramId）；IaC **尚未**對等落地。
- 前端全樹除權限頁標籤外，**僅此 CTA** 提及 IaC（`frontend/src` grep）。

#### 2. RBAC D1／D2／D3 標籤與種子（矩陣領先）

| Story | UI／catalog 短名 | 描述（權限頁） |
|---|---|---|
| D1 | Terraform 產出 | 產出 Terraform／IaC（D1） |
| D2 | IaC 安全掃描 | IaC 安全掃描（D2） |
| D3 | Secret／敏感值 | Secret／敏感值處理（D3） |

- Pillar D 顯示名：「基礎建設即程式碼」（`RolePermissionsPage` `PILLAR_LABELS`）。
- 種子摘要（`DEFAULT_ROLE_PERMISSIONS`，`(view, edit, review)`）：
  - **D1 edit=true**：`Project_Architect`、`Developer`、`Platform_Engineer`
  - **D2 edit=true**：`Platform_Engineer`、`Security_Reviewer`
  - **D3 edit=true**：`Developer`、`Security_Reviewer`
  - **FinOps_Analyst**：D1／D2／D3 全 false
  - 多數其他角色：多為 view-only 或 false
- 授權掛載樣板已存在：`require_story_action("D1"|"D2"|"D3", action)`（`rbac.py`）；C1 cost／J3b 已用同形。**尚無任何 handler Depends 掛 D\***。

#### 3. A／C 如何用 LangGraph（可複用模式）

| 柱 | 入口 | Graph／Runtime | 串流／授權 |
|---|---|---|---|
| A1 產圖 | `agent_router` `POST …/generate` → `run_design_agent` | `design_agent.build_graph()`：`StateGraph`＋tool `draw_architecture_diagram`；ChatAnthropic／SDK env | SSE；`require_arch_action("edit")`；`prompt_guard` 平台自改預檢 |
| A1↔A3 | `POST …/generate-wa-collab` → `run_wa_collab` | 編排層；Workspace **實打此端點** | SSE（message／progress／xml_preview／score／complete／error） |
| A3 | review／lens（淺層） | `StateGraph`＋`openrouter_chat_model`（`langgraph_runtime`） | 既有 review／lens HTTP |
| C 建議 | `cost_advice_agent._invoke_once` | 單節點 `StateGraph(dict)` → `invoke_graph`；`openrouter_chat_model()` | 背景 job＋`GET …/advice/stream` SSE；intake router 掛 C1 權限 |

**`langgraph_runtime.py` 契約（D 應視為預設底座）**：

- `openrouter_chat_model()`：需 `OPENROUTER_API_KEY`；缺則 `RuntimeAuthError`（domain，非 HTTP）
- `invoke_graph`／`stream_graph`／`astream_graph`：呼叫端自編譯 graph；本模組不擁有 cost／IaC 節點
- 與 `llm_provider`／Claude Agent SDK **刻意平行**

#### 4. 路由／API 表面（現況 vs D 缺口）

**`App.tsx` 頁面**（無 D／IaC 路由）：

- `/workspace` → `CapabilityRoute storyId="A1" action="view"`
- `/assessment` → A3；`/cost` → C1；admin J3a／J3b

**`main.py` include_router**：

- `/api/architecture` ← agent＋review＋lens  
- `/api/auth` ← user  
- `/api/collab`  
- `/api/cost/v1` ← estimate＋advice stream  
- **無** `/api/iac*` 或類似前綴

**OpenAPI**：architecture／auth／collab／cost 齊；**零** IaC／Terraform／secret-scan 路徑。

#### 5. Gaps for D1／D2／D3（給下游）

| ID | 缺口 | 證據 |
|---|---|---|
| G1 | 無 IaC HTTP／SSE 契約與 `openapi.json` 條目 | openapi grep 0；main 無 router |
| G2 | 無 IaC 業務模組（generator／scan／secret）與 PBT 落點 | 深讀路徑無實作；ADR-0006 點名 IaC generator |
| G3 | Workspace CTA 未接 D1 權限或真實 flow | Coming Soon only；無 `can('D1')` |
| G4 | 無獨立 IaC 頁／路由；入口僅 workspace toast | `App.tsx` 無 path |
| G5 | 三 agent（D1／D2／D3）尚未有對應 runtime／編排（market-research：非單一 agent 包辦） | 僅 RBAC id 與 UI 標籤 |
| G6 | 若沿用 C：需三層＋純函式 generator（PBT）＋ router Depends `require_story_action`；A／B／C 測試規則（allow／deny TestClient、e2e）於首個 D 端點即適用 | team／project Mandated |
| G7 | Scope 邊界：direct production IaC／destructive cloud ops **out of scope**（project Scope Overrides）——產出／掃描設計不得踩 apply 到雲端 production | memory |

**建議複用（非定案，供 architect）**：

1. Runtime：優先 `langgraph_runtime`＋OpenRouter（對齊 C／A3），Workspace SSE 消費形狀對齊 `generate-wa-collab` 或 cost advice stream。  
2. 授權：首端點即 `Depends(require_story_action("D1"|"D2"|"D3", …))`＋allow／deny TestClient。  
3. UI：替換 Coming Soon；CTA 應尊重 D1（至少 edit）權限，避免無種子角色仍見可點按鈕後只跳「即將推出」。  
4. 勿把 D 邏輯塞進 `user_router`／`agent_router` 上帝檔；新 `*_router`＋純函式核心（對齊 cost 三層精神／ADR-0006）。

---

## Handoff Summary

- **Intent-relevant finding**: Story D 在產品面上仍是 **RBAC＋權限頁標籤＋Workspace「生成 IaC 代碼」Coming Soon stub**；**零** backend router／OpenAPI／LangGraph IaC agent。可複用底座已在 repo：`langgraph_runtime`（C／A3）、Workspace SSE 消費（`generate-wa-collab`）、`require_story_action` 掛權。證據：`WorkspacePage.tsx` L259–265／L966–969；`RolePermissionsPage.tsx` L41–43／L75–77；`rbac_seed_data.py` L117–149；`main.py` L52–58；`openapi.json` 無 iac／terraform。
- **Risks / follow-up**:
  1. 勿把種子／權限頁 D 欄讀成「已有 IaC 能力」（矩陣領先實作）。
  2. D1／D2／D3 預設三 agent 拆分（memory correction）；設計勿收成單一 agent。
  3. 首個 generator 落地即觸發 ADR-0006 PBT；首 HTTP 端點觸發 allow／deny＋OpenAPI drift。
  4. Architect 合成 codekb 時本掃描為 **partial／focused**——僅上述 deep 路徑可宣稱深讀；其餘為 skimmed。
  5. Production IaC apply 仍在 scope 外；高風險動作需 human approval gate。
`)