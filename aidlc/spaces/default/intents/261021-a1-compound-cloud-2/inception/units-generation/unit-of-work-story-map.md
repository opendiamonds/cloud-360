# Unit of Work Story Map — A1 混合雲繪圖功能 (Compound Cloud Diagram)

> Stage: units-generation (2.7) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游基準：
> - [components](../domain-design/components.md)
> - [decisions](../domain-design/decisions.md)
> - [requirements](../requirements-analysis/requirements.md)
> - [stories](../user-stories/stories.md)
> - [unit-of-work](unit-of-work.md)
> - [unit-of-work-dependency](unit-of-work-dependency.md)

---

## 1. 使用者故事至建構單元對映表 (Story-to-Unit Mapping Table)

本專案將 Stage 2.4 產出之 11 個使用者故事完整映射至 4 個建構單元，無任何未對應故事或空置單元：

| Story ID | 故事名稱簡述 | 優先級 (MoSCoW) | Unit ID | Directory | 單元類型 (Kind) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| US4.1 | n8n 上行發送 provider="compound" | Must Have | U1 | u1-icon-service-gateway | library |
| US4.2 | n8n 5.0 秒逾時保護與灰底向量 SVG Fallback | Must Have | U1 | u1-icon-service-gateway | library |
| US3.1 | 三雲頂層群組容器渲染與樣式套用 | Must Have | U2 | u2-compound-diagram-builder | library |
| US3.2 | Hub-and-Spoke 幾何空間計算與緩衝走廊 | Must Have | U2 | u2-compound-diagram-builder | library |
| US3.3 | 跨雲節點直角折線與端點錨定 | Must Have | U2 | u2-compound-diagram-builder | library |
| US3.4 | 跨雲通訊協議文字標籤動態渲染 | Must Have | U2 | u2-compound-diagram-builder | library |
| US2.1 | Design Agent 宣告 compound 繪圖參數 | Must Have | U3 | u3-design-agent-compound | service |
| US2.2 | System Prompt 引導核心雲置中拓撲 | Must Have | U3 | u3-design-agent-compound | service |
| US1.1 | Toolbar 提供混合雲模式手動切換 | Must Have | U4 | u4-workspace-canvas-ui | ui |
| US1.2 | ChatBox 自然語言意圖自動識別多雲 | Should Have | U4 | u4-workspace-canvas-ui | ui |
| US1.3 | DrawioCanvas 自動 Fit-to-Window 最佳視角 | Should Have | U4 | u4-workspace-canvas-ui | ui |

---

## 2. 單元內部故事實作順序 (Implementation Sequencing within Units)

### Unit 1: u1-icon-service-gateway (U1)
1. US4.1: 實作 provider="compound" 上行通訊參數與 Webhook 請求通道。
2. US4.2: 實作 5.0 秒逾時中斷與本地 40x40 灰底文字向量 SVG 降級邏輯。

### Unit 2: u2-compound-diagram-builder (U2)
1. US3.1: 實作三雲頂層 Group 容器與 GROUP_STYLES 樣式套用。
2. US3.2: 實作 Hub-and-Spoke 空間座標佈局演算法與 120px 緩衝走廊。
3. US3.3: 實作跨雲 edge 直角折線路由 (orthogonalEdgeStyle) 與網關端點錨定。
4. US3.4: 實作連線中點純白膠囊圓角背景協議文字標籤。

### Unit 3: u3-design-agent-compound (U3)
1. US2.1: 於 design_agent.py 之 draw_architecture_diagram tool 參數列舉中擴充 compound。
2. US2.2: 更新 Agent System Prompt 與 Tool Docstring，注入核心雲居中拓撲規劃指引。

### Unit 4: u4-workspace-canvas-ui (U4)
1. US1.1: 於 WorkspacePage.tsx 工具列 Provider 下拉選單中新增「混合雲 (Compound)」選項。
2. US1.2: 整合 ChatBox 自然語言多雲意圖識別事件，自動同步選單狀態並呈現 Badge 提示。
3. US1.3: 實作 DrawioCanvas 接收到混合雲 XML 渲染後之 250ms ease-out 平滑 Fit-to-Window 動效。

---

## 3. 故事覆蓋度驗證 (Coverage Verification)

- 總故事數: 11
- 已指派故事數: 11 (覆蓋率 100%)
- 未指派孤立故事: 0
- 空置單元: 0 (U1 擁有 2 故事、U2 擁有 4 故事、U3 擁有 2 故事、U4 擁有 3 故事)
- 驗證結論: 所有故事皆獲得建構單元承接，滿足架構可實現性標準。
