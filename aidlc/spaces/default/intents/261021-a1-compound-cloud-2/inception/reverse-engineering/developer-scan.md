# Developer Code Scan — cloud-360

> Stage: reverse-engineering (2.1) · Phase: Inception · Agent: aidlc-developer-agent
> Scan Mode: Focused scan (A1 Compound Cloud Diagram)

## Developer Code Scan Results

### Scan Coverage
- **Analyzed deeply**:
  - `backend/services/diagram_builder.py`
  - `backend/services/design_agent.py`
  - `frontend/src/`
- **Skimmed only**:
  - `backend/tests/`
  - `backend/routers/`
  - `frontend/src/components/`

### Packages Found
- `backend` — backend-service — Python 3.11 — FastAPI 核心後端服務，包含 AI 設計代理人 (design_agent)、mxGraph XML 架構圖組裝器 (diagram_builder) 與評核路由器
- `frontend` — web-spa — TypeScript / React 18 — Vite 構建之 SPA 單頁應用，包含 Workspace 架構設計畫布 (Draw.io iframe / mxGraph) 與對話式 AI 互動面板

### Build System
- **Type**: Multi-tier (FastAPI backend + Vite frontend)
- **Config Files**:
  - `backend/requirements.txt`
  - `frontend/package.json`
  - `frontend/vite.config.ts`
  - `frontend/tsconfig.json`
- **Build Dependencies**:
  - `frontend` 透過 REST API (`/api/*`) 與 SSE 事件串流呼叫 `backend`
  - `backend` 透過 HTTP POST Webhook 呼叫外部 `n8n` 服務以取得雲端服務圖示

### APIs Discovered
- Internal Tool — `backend/services/design_agent.py:64-77` — `draw_architecture_diagram` (LangChain `@tool`, provider, groups, nodes, edges)
- Service Function — `backend/services/diagram_builder.py:1827-1875` — `fetch_icon_from_n8n` (HTTP POST to n8n webhook)
- XML Assembler — `backend/services/diagram_builder.py:1924-2081` — `build_mxgraph_xml` (組合三雲群組、元件節點、連線 edges 之 mxGraph XML)
- Frontend Canvas API — `frontend/src/components/DrawioCanvas.tsx` — `DrawioCanvasRef.mergeXml` (postMessage 通訊載入 XML)

### Frameworks & Libraries
- `fastapi` — 0.111.0+ — 後端 API 框架與非同步路由
- `langchain-core` — 0.3.x — 代理人 Tool Calling 抽象
- `httpx` — 0.27.x — 非同步 HTTP 客戶端，用於與 n8n 通訊
- `react` — 18.3.1 — 前端 UI 核心框架
- `vite` — 5.4.x — 前端構建與開發伺服器
- `unittest` / `hypothesis` — Python 內建 + 6.x — 後端測試與性質測試 (PBT)

### Test Coverage
- **Test Directories**: `backend/tests/`
- **Test Frameworks**: Python `unittest`, `hypothesis` (PBT), Playwright (E2E)
- **Coverage Config**: 既有 CI 包含 `backend unittest` 與 `frontend lint/typecheck`，但尚無全域 line coverage 實體計量

### Code Quality Indicators
- **Linting**: Ruff / Flake8 (backend), ESLint + Prettier (frontend)
- **CI/CD**: `.github/workflows/ci.yml` (包含 repo-contract, frontend lint, tsc -b, backend unittest, docker-build)
- **Documentation**: 模組包含完整型別標註與繁體中文 Docstrings

### Technical Debt Signals
- `design_agent.py` 中 `draw_architecture_diagram` 之 `provider` 參數目前硬編碼僅支援 `("AWS", "GCP", "Azure")`，尚未宣告 `"compound"`。
- `diagram_builder.py` 內建 `GROUP_STYLES` 已包含三雲樣式，但頂層多群組並存時缺乏多雲 Hub-and-Spoke 幾何佈局計算邏輯。

## Handoff Summary
- **Intent-relevant finding**:
  - `backend/services/diagram_builder.py:30-131` 已完整具備 `aws_cloud`、`gcp_cloud`、`azure_cloud` 樣式常數，三雲群組在技術上完全支援在單一 XML 中共存渲染。
  - `backend/services/diagram_builder.py:1827-1875` 之 `fetch_icon_from_n8n` 直接接收 `provider` 參數並以 JSON payload 發送，只需傳遞 `provider="compound"` 即可無縫串接上游。
- **Risks / follow-up**:
  - 在實作 Hub-and-Spoke 幾何佈局時，需為三雲獨立計算 X/Y 偏移量與容器邊界，確保跨雲連線端點與標籤清晰可讀。
  - 需新增專屬單元測試集 `test_diagram_builder_compound.py` 驗證三雲 XML 幾何組裝與 n8n compound 上行。
