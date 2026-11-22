# Risk & Sequencing Rationale — A1 混合雲繪圖功能 (Compound Cloud Diagram)

> Stage: delivery-planning (2.9) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游基準：
> - [bolt-plan](bolt-plan.md)
> - [unit-of-work-dependency](../units-generation/unit-of-work-dependency.md)
> - [requirements](../requirements-analysis/requirements.md)

---

## 1. 排程策略與評分依據 (Sequencing Heuristic & WSJF)

本專案採用 **WSJF (Weighted Shortest Job First)** 結合「風險先降 (Risk-First)」與「骨架先行 (Walking Skeleton First)」混合策略：

$$WSJF = \frac{\text{User-Business Value} + \text{Time Criticality} + \text{Risk Reduction / Opportunity Enablement}}{\text{Job Size}}$$

| Bolt ID | Name | 商業價值 (1-5) | 時間急迫性 (1-5) | 風險降低/基石價值 (1-5) | 規模大小 (Job Size) | WSJF 得分 | 排序推薦 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Bolt 1** | `bolt-icon-gateway` | 3 | 4 | 5 (消除外部相依阻礙) | 2 (小) | **6.0** | **第 1 位** |
| **Bolt 2** | `bolt-diagram-builder` | 5 | 5 | 5 (核心幾何骨架) | 3 (中) | **5.0** | **第 2 位** |
| **Bolt 3** | `bolt-design-agent` | 4 | 4 | 3 (內部介面銜接) | 2 (小) | **5.5** | **第 3 位** |
| **Bolt 4** | `bolt-workspace-canvas` | 5 | 4 | 2 (視覺呈現) | 3 (中) | **3.67** | **第 4 位** |

---

## 2. 排序依據深度剖析 (Rationale Breakdown)

1. **優先交付 Bolt 1 的理由 (External Risk First)**:
   - 外部 n8n 服務的連通性與容錯是整個架構中最脆弱的外部環節（CON2 / NFR3）。若不先固化 5.0s 逾時與 40x40 灰底文字 SVG Fallback，後續圖形組裝可能在測試階段因網路中斷而產生不確定性。
2. **Bolt 2 作為 Walking Skeleton 的理由 (Architectural Proof)**:
   - 混合雲幾何計算（AWS 480px 置中、兩側 360px、折線連線）為本次功能最核心的技術創新。一旦 Bolt 2 完成並通過單元測試，即代表「混合雲架構圖能被計算並產出 mxGraph XML」的技術假說成立。
3. **Bolt 3 與 Bolt 4 緊隨其後的理由 (Consumer Integration)**:
   - Agent 與前端 UI 分別為該幾何引擎的兩層消費者，遵循上游穩定下游實作之相依性遞進。

