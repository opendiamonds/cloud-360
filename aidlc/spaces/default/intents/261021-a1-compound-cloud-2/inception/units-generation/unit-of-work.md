# Units of Work Specification — A1 混合雲繪圖功能 (Compound Cloud Diagram)

> Stage: units-generation (2.7) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游基準：
> - [components](../domain-design/components.md)
> - [decisions](../domain-design/decisions.md)
> - [requirements](../requirements-analysis/requirements.md)
> - [stories](../user-stories/stories.md)

---

## 1. 建構單元定義與目錄總覽 (Unit Definitions & Directory Mapping)

本專案依據領域驅動設計原則，將混合雲功能分解為 4 個獨立的 Construction Units。各單元具備獨立的代碼範疇、測試防護網與明確的交付價值：

| Unit ID | Directory | 單元名稱 (Unit Name) | 類型 (Kind) | 部署模型 (Deployment Model) | 複雜度 (Complexity) | 核心技術棧 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **U1** | `u1-icon-service-gateway` | 圖示服務通訊與容錯閘道單元 | `library` | Embedded in backend | **S** (Small) | Python 3.11, urllib / httpx |
| **U2** | `u2-compound-diagram-builder` | 混合雲幾何組裝與連線渲染單元 | `library` | Embedded in backend | **M** (Medium) | Python 3.11, xml.etree, unittest |
| **U3** | `u3-design-agent-compound` | AI 代理人介面與提示詞引導單元 | `service` | Shared backend service | **S** (Small) | Python 3.11, FastAPI, LangChain |
| **U4** | `u4-workspace-canvas-ui` | 前端畫布工具列與視角動效單元 | `ui` | Frontend SPA package | **M** (Medium) | TypeScript, React 18, Vite |

---

## 2. 各建構單元職責與交付範圍 (Unit Responsibilities & Deliverables)

### U1: `u1-icon-service-gateway`
- **所屬領域元件**: `IconServiceGatewayComponent`
- **核心職責**:
  - 封裝 `fetch_icon_from_n8n()` 函式。
  - 統一組裝向 `${N8N_WEBHOOK_URL}` 發送之 POST Payload：`{"service": name, "provider": "compound"}`。
  - 設置嚴格 5.0 秒逾時機制 (`timeout=5.0`)。
  - 捕獲所有網路逾時與非 200 回應，動態合成 40x40 灰底文字向量 SVG（`#F1F5F9` 底色、`#475569` 文字），絕不拋出未捕捉之例外。
- **對應故事**: US4.1, US4.2

### U2: `u2-compound-diagram-builder`
- **所屬領域元件**: `CompoundDiagramBuilderComponent`
- **核心職責**:
  - 實作 Hub-and-Spoke 幾何座標計算演算法：中央 AWS 容器寬度加寬至 480px，兩翼 Azure 與 GCP 各 360px，雲與雲之間保留 120px 緩衝走廊。
  - 套用 `GROUP_STYLES` 中的 `aws_cloud`、`azure_cloud` 與 `gcp_cloud` 樣式常數，確保三雲邊界完全隔離不重疊。
  - 實作直角折線路由 (`edgeStyle=orthogonalEdgeStyle;`) 與網關節點邊緣錨定。
  - 實作連線中點純白膠囊圓角背景協議標籤（`#FFFFFF` 背景、`#1E293B` 文字、對比度 13.5:1）。
  - 建立專屬單元測試集 `backend/tests/test_diagram_builder_compound.py`，完整斷言 XML 幾何、間距與 mock n8n 通訊。
- **對應故事**: US3.1, US3.2, US3.3, US3.4

### U3: `u3-design-agent-compound`
- **所屬領域元件**: `DesignAgentComponent`
- **核心職責**:
  - 擴充 `backend/services/design_agent.py` 中的 `draw_architecture_diagram` tool 介面，`provider` 參數容許 `"compound"`。
  - 更新 Tool Docstrings 與 `backend/prompts/` 系統提示詞，明確引導 LLM 在多雲情境下以核心雲居中、附屬雲分佈兩側。
  - 檢驗呼叫者具備 `A1.edit` 權限，符合 RBAC 規範。
- **對應故事**: US2.1, US2.2

### U4: `u4-workspace-canvas-ui`
- **所屬領域元件**: `WorkspaceCanvasToolbarComponent`
- **核心職責**:
  - 擴充 `WorkspacePage.tsx` 頂部 Provider 下拉選單，新增「混合雲 (Compound)」選項並管理選中狀態。
  - 整合 ChatBox 自然語言意圖辨識，當接收到多雲意圖時輸出狀態 Badge，並自動同步切換 Toolbar 選項。
  - 接收到混合雲 XML 渲染完成事件後，自動觸發 DrawioCanvas 之 Fit-to-Window 平滑縮放動畫（時長 250ms ease-out，四周 padding 保留 32px）。
- **對應故事**: US1.1, US1.2, US1.3

---

## 3. 建構約制與品質護欄 (Constraints & Guardrails)

1. **零新增外部套件 (NFR5)**: U1 與 U2 實作限用 Python 內建函式庫（`urllib`, `xml.etree`）與現有依賴；U4 限用現有 npm 套件。
2. **測試防護網 (CON3)**: U2 單元測試集 `test_diagram_builder_compound.py` 必須具備 100% 通過率，並納入 CI 流程。
3. **無障礙合規 (NFR3)**: U2 與 U4 所有視覺元素（協議標籤、Toolbar 按鈕）必須符合 WCAG 2.1 AA 規範。

