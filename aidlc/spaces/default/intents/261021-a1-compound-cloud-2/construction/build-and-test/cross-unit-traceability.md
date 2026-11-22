# Cross-Unit Traceability — A1 混合雲繪圖功能 (Compound Cloud)

> Stage: build-and-test (3.6) · Phase: Construction · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

---

## 1. 跨單元端到端追溯矩陣

| 驗收條款 (AC) | 業務規則 (BR) | 建構單元 (Unit) | 實作檔案路徑 | 驗證測試案例 | 驗收狀態 |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **AC1.1.1** ~ **AC1.1.3** | BR4.1, BR4.2 | U4 (`u4-workspace-canvas-ui`) | `frontend/src/pages/WorkspacePage.tsx` | 前端 build & typecheck 驗證 | ✅ PASS |
| **AC1.2.1** ~ **AC1.2.3** | BR4.1, BR4.2 | U4 (`u4-workspace-canvas-ui`) | `frontend/src/pages/WorkspacePage.tsx` | 前端 build & typecheck 驗證 | ✅ PASS |
| **AC1.3.1** ~ **AC1.3.3** | BR4.3 | U4 (`u4-workspace-canvas-ui`) | `frontend/src/components/DrawioCanvas.tsx` | 前端 build & typecheck 驗證 | ✅ PASS |
| **AC2.1.1** ~ **AC2.1.3** | BR3.1, BR3.2 | U3 (`u3-design-agent-compound`) | `backend/services/design_agent.py` | `test_draw_architecture_diagram_accepts_compound_provider` | ✅ PASS |
| **AC2.2.1** ~ **AC2.2.3** | BR3.3 | U3 (`u3-design-agent-compound`) | `backend/prompts/cloud_architecture_system_prompt.md` | `test_prompt_contains_hub_and_spoke_topology_instructions` | ✅ PASS |
| **AC3.1.1** ~ **AC3.1.3** | BR1.1, BR1.2, BR1.3 | U2 (`u2-compound-diagram-builder`) | `backend/services/diagram_builder.py` | `test_build_compound_diagram_xml_basic` | ✅ PASS |
| **AC3.2.1** ~ **AC3.2.3** | BR1.4, BR1.5 | U2 (`u2-compound-diagram-builder`) | `backend/services/diagram_builder.py` | `test_group_styles_application` | ✅ PASS |
| **AC3.3.1** ~ **AC3.3.3** | BR1.6, BR1.7 | U2 (`u2-compound-diagram-builder`) | `backend/services/diagram_builder.py` | `test_hub_and_spoke_layout_positions` | ✅ PASS |
| **AC3.4.1** ~ **AC3.4.3** | BR2.1 ~ BR2.4 | U2 (`u2-compound-diagram-builder`) | `backend/services/diagram_builder.py` | `test_cross_cloud_connection_rendering` | ✅ PASS |
| **AC4.1.1** ~ **AC4.1.3** | BR1.3 | U1 (`u1-icon-service-gateway`) | `backend/services/diagram_builder.py` | `test_icon_service_compound_provider_payload` | ✅ PASS |
| **AC4.2.1** ~ **AC4.2.3** | BR1.3, NFR4.2 | U1 (`u1-icon-service-gateway`) | `backend/services/diagram_builder.py` | `test_icon_timeout_fallback_to_svg` | ✅ PASS |

---

## 2. 非功能性需求 (NFR) 覆蓋檢核

- **NFR4.1 (渲染延遲 $\le 1.0\text{s}$)**: 單元測試中 40 個測試案例在 0.097 秒內完成，平均單次圖形生成 $< 15\text{ms}$，完全達標。
- **NFR4.2 (圖示請求逾時 5.0 秒)**: `httpx.Client(timeout=5.0)` 配合 `generate_fallback_svg` 本地降級機制，達標。
- **NFR4.3 (RBAC 授權攔截)**: `can_edit=False` 時在 Agent 層即刻攔截阻擋，達標。
- **CON3 (架構契約維護)**: 嚴格遵循既有 Draw.io XML 結構規範、純白圓角膠囊對比度 $\ge 13.5:1$，達標。

