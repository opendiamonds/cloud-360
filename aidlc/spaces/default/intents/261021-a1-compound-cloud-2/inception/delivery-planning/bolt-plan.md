# Bolt Delivery Plan — A1 混合雲繪圖功能 (Compound Cloud Diagram)

> Stage: delivery-planning (2.9) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游基準：
> - [unit-of-work](../units-generation/unit-of-work.md)
> - [unit-of-work-dependency](../units-generation/unit-of-work-dependency.md)
> - [unit-of-work-story-map](../units-generation/unit-of-work-story-map.md)
> - [contract-summary](../contract-design/contract-summary.md)
> - [components](../domain-design/components.md)

---

## 1. Bolt 交付序列總覽 (Bolt Delivery Sequence)

本專案採循序推進之 Bolt 交付序列（Bolt 意即單一完整的建構交付切片，包含程式碼、自動化測試與可驗收功能）：

| Bolt ID | Name | Included Units | Walking Skeleton | 核心交付標的 | 驗收展示 (Expected Demo) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Bolt 1** | `bolt-icon-gateway` | `u1-icon-service-gateway` | 否 | n8n 上行圖示查詢、`provider="compound"`、5.0s 逾時與 SVG Fallback | 呼叫 `fetch_icon_from_n8n()`，成功與逾時場景皆回傳合法向量 SVG。 |
| **Bolt 2** | `bolt-diagram-builder` | `u2-compound-diagram-builder` | **是 (Core Architecture)** | Hub-and-Spoke 幾何運算、三雲容器座標、直角折線與協議標籤渲染 | 執行 `pytest backend/tests/test_diagram_builder_compound.py`，成功產出三雲混合架構 Draw.io XML。 |
| **Bolt 3** | `bolt-design-agent` | `u3-design-agent-compound` | 否 | Agent 工具擴充、多雲提示詞規則、RBAC 權限校驗 | 透過 Agent API 發送混合雲指令，正確觸發 `draw_architecture_diagram(provider="compound")`。 |
| **Bolt 4** | `bolt-workspace-canvas` | `u4-workspace-canvas-ui` | 否 | 前端 Toolbar Provider 下拉選單、對話框連動反饋、Draw.io 250ms 自適應畫布 | 在 UI 選擇「混合雲」並發送提示詞，畫布自動載入並置中縮放三雲架構圖。 |

---

## 2. 各 Bolt 詳細定義與驗收準則 (Definition of Done & Hypotheses)

### 2.1 Bolt 1: u1-icon-service-gateway
- **Included Unit**: `u1-icon-service-gateway` (kind: `library`)
- **涵蓋故事**: US4.1, US4.2
- **Confidence Hypothesis（信心假說）**:
  - 驗證外部 n8n 圖示服務在強制 `provider="compound"` 下能正確被調用；且在網路中斷或逾時 > 5.0 秒時，系統能保證於 5.0 秒內優雅降級回本地灰底向量 SVG，確保畫圖流程絕不拋出未捕捉例外。
- **Definition of Done (DoD)**:
  1. `diagram_builder.py` 內之 `fetch_icon_from_n8n()` 支援 `provider="compound"`。
  2. 逾時機制嚴格限制 5.0s。
  3. 404 / 500 / Timeout 場景回傳 40x40 灰底文字向量 SVG。
  4. 單元測試覆蓋正常取得與 Fallback 分支。

---

### 2.2 Bolt 2: u2-compound-diagram-builder (Walking Skeleton)
- **Included Unit**: `u2-compound-diagram-builder` (kind: `library`)
- **涵蓋故事**: US3.1, US3.2, US3.3, US3.4
- **Confidence Hypothesis（信心假說）**:
  - 驗證 Hub-and-Spoke 空間佈局演算法（中央 AWS 480px、兩側 Azure/GCP 各 360px、間距 120px）能產出無元素重疊、視覺結構對稱之標準 mxGraph XML，且跨雲連線標籤符合 WCAG 2.1 AA 對比度標準。
- **Definition of Done (DoD)**:
  1. 實作 `build_compound_diagram_xml()` 及其容器座標計算函式。
  2. 跨雲連線套用 `orthogonalEdgeStyle` 及純白膠囊協議標籤。
  3. 建立測試檔案 `backend/tests/test_diagram_builder_compound.py`，涵蓋座標幾何與 XML 結構斷言。
  4. 產圖端到端時間 $\le 8.0$ 秒。

---

### 2.3 Bolt 3: u3-design-agent-compound
- **Included Unit**: `u3-design-agent-compound` (kind: `service`)
- **涵蓋故事**: US2.1, US2.2
- **Confidence Hypothesis（信心假說）**:
  - 驗證 LLM Agent 能夠自使用者自然語言對話精準識別跨雲混合意圖，呼叫 Tool 帶入 `provider="compound"`，並受既有 RBAC 權限控管。
- **Definition of Done (DoD)**:
  1. `backend/agents/design_agent.py` 之 `draw_architecture_diagram` 工具參數支援 `compound`。
  2. 系統提示詞納入「跨雲混合場景採用 Hub-and-Spoke 置中拓撲」指引。
  3. 權限檢查機制無縫相容。

---

### 2.4 Bolt 4: u4-workspace-canvas-ui
- **Included Unit**: `u4-workspace-canvas-ui` (kind: `ui`)
- **涵蓋故事**: US1.1, US1.2, US1.3
- **Confidence Hypothesis（信心假說）**:
  - 驗證前端操作介面之整體流暢度，使用者能從下拉選單切換至混合雲，並在 Agent 回傳 XML 後 250ms 內平滑平移並縮放至全視窗可見。
- **Definition of Done (DoD)**:
  1. `frontend/src/components/Toolbar.tsx` 新增「混合雲 (Compound)」選項。
  2. `ChatBox.tsx` 狀態提示多雲繪圖階段進度。
  3. `DrawioCanvas.tsx` 整合 `fitWindow` 動效，總耗時 250ms ease-out。

