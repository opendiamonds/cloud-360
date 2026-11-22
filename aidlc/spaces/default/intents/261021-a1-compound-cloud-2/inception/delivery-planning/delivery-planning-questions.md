# Delivery Planning Questionnaire & Alignment — A1 混合雲繪圖功能 (Compound Cloud Diagram)

> Stage: delivery-planning (2.9) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游基準：
> - [unit-of-work](../units-generation/unit-of-work.md)
> - [unit-of-work-dependency](../units-generation/unit-of-work-dependency.md)
> - [unit-of-work-story-map](../units-generation/unit-of-work-story-map.md)
> - [contract-summary](../contract-design/contract-summary.md)
> - [components](../domain-design/components.md)
> - [requirements](../requirements-analysis/requirements.md)

---

## 1. 交付策略與原則說明 (Delivery Strategy & Definitions)

本階段為 Inception 的收官階段（Capstone），核心任務是將 Stage 2.7 確立的 4 個建構單元（U1 ~ U4）規劃為可執行的 **Bolt 交付序列**（Construction Delivery Slices）：

- **Bolt（建構交付切片）**：一次完整的建構與驗收循環（包含程式碼實作、單元/整合測試與可執行的驗收展示），完成後產出可運行成果。
- **Walking Skeleton（骨架切片）**：首個端到端貫通的極簡實作切片，用以驗證核心架構鏈路是否通暢。
- **排程依據 (WSJF / 經濟與風險排序)**：依賴 Stage 2.7 之無環拓撲鏈 `U1 -> U2 -> U3 -> U4`，優先以「風險先降、合約先行」之順序推進。

---

## 2. 交付規劃關鍵問卷 (Clarifying Questions)

### Q1. Bolt 序列切割與分批策略 (Bolt Granularity & Sequencing)
依據 4 大單元的相依關係，我們規劃 4 個依序遞進的 Bolt 批次：
- **Bolt 1 (U1)**: 圖示閘道通訊與 Fallback 機制 (`u1-icon-service-gateway`)，驗證外部 n8n `provider="compound"` 連通與 5.0s 逾時防護。
- **Bolt 2 (U2)**: 混合雲幾何組裝引擎 (`u2-compound-diagram-builder`)，驗證 Hub-and-Spoke 座標、直角折線與協議標籤渲染，完成專屬單元測試集。
- **Bolt 3 (U3)**: 設計代理人介面 (`u3-design-agent-compound`)，驗證 Agent Tool 多雲意圖識別與 RBAC 整合。
- **Bolt 4 (U4)**: 畫布工作區前端元件 (`u4-workspace-canvas-ui`)，驗證前端工具列、對話框與 Draw.io 畫布 250ms 自適應縮放。

是否同意此一對一逐步推進的 Bolt 切割方式？
- [A] 同意，1 個 Bolt 對應 1 個 Unit，邊界清晰、驗收精確、回退風險最低。（推薦）
- [B] 建議合併 U1 與 U2 為單一 Bolt 進行後端整体验收。

[Answer]: [A]

### Q2. Walking Skeleton（骨架切片）認定
在本專案之 4 個 Bolt 中，哪一個作為核心 Walking Skeleton？
- [A] 以 **Bolt 2 (U2: Compound Diagram Builder)** 作為核心骨架驗證點，因其直接驗證三雲幾何空間組裝與 Draw.io XML 產生能力，是本功能最核心的架構成立前提。（推薦）
- [B] 以 Bolt 1 (U1) 作為骨架。
- [C] 不設立 Walking Skeleton，所有 Bolt 一律視為標準批次。

[Answer]: [A]

### Q3. Construction 執行模式與自主推進 (Execution Autonomy Mode)
進入 Stage 3 Construction 實作階段後，Bolt 的推進節奏建議如何執行？
- [A] **分段自主推進 (Autonomous with verification gates)**：各 Bolt 自動完成程式碼生成與單元測試，在各 Bolt 邊界執行驗收查核（推薦）
- [B] **嚴格單步審查 (Gate every Bolt)**：每個 Bolt 完成後均暫停等待人工確認。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出 `bolt-plan.md`、`team-allocation.md`、`risk-and-sequencing-rationale.md`、`external-dependency-map.md` 與 `verification/phase-check-inception.md` 前，請確認以下彙整摘要正確無誤：

- **Bolt 切割與序列 (Q1)**: [A] 4 個循序遞進的 Bolt（Bolt 1: U1 -> Bolt 2: U2 -> Bolt 3: U3 -> Bolt 4: U4）。
- **Walking Skeleton (Q2)**: [A] 以 Bolt 2 (U2) 作為核心骨架驗證點，確立 Draw.io XML 混合雲組裝核心能力。
- **Construction 執行模式 (Q3)**: [A] 分段自主推進，以自動化測試與規範為守門依據。

Does this all look correct before I generate the delivery planning artifacts?
- Looks correct
- Request changes

[Answer]: Looks correct

