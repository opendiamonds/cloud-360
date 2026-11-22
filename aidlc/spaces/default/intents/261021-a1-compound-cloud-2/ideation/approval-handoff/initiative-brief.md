# Initiative Brief — A1 混合雲繪圖功能 (Compound Cloud Diagram)

> Stage: approval-handoff (1.7) · Phase: Ideation · Scope: feature · Depth: Standard
> 彙整基準：Ideation 階段所有定案產物 (`intent-statement.md`, `stakeholder-map.md`, `feasibility-assessment.md`, `constraint-register.md`, `raid-log.md`, `scope-document.md`, `intent-backlog.md`, `wireframes.md`, `user-flow.md`)

## Executive Summary

本項目為 A1 核心架構繪圖平台之重大功能升級，旨在支援「混合雲 (Compound Cloud)」架構繪圖——單張架構圖中同時呈現 AWS、Azure、GCP 三大雲端服務提供商之元件群組與跨雲交互拓撲，並統一向上游 n8n 服務發送 `provider = "compound"` 進行圖示解析。本 Initiative Brief 彙整 Ideation 階段之問題釐清、技術可行性評估、邊界定義、線框視覺與團隊分工，作為進入 Inception 階段之正式交接依據。

## Intent and Problem Statement

### 核心問題
現行 Cloud-360 A1 架構繪圖功能僅支援單一雲提供商模式（AWS / GCP / Azure 擇一），當架構師或業務顧問需要為大型企業客戶規劃或評估混合雲／多雲拓撲時，無法在單一張圖上統合展示跨雲架構（例如：以 AWS 為核心業務 VPC，兩翼分別串接 Azure AD / ExpressRoute 與 GCP BigQuery / Cloud Interconnect）。

### 預期價值與目標
- **一站式混合雲視覺化**：架構師可透過對話模型或 Toolbar 手動選擇「Compound」，一次生成涵蓋三雲的完整拓撲圖。
- **標準化通訊協議**：後端向 n8n 服務請求圖示時，統一發送 `provider = "compound"`，確保後續擴展一致性。
- **追溯來源**：
  - [intent-statement.md](../intent-capture/intent-statement.md)
  - [stakeholder-map.md](../intent-capture/stakeholder-map.md)

## Market Validation Summary

依據 AI-DLC v2 之 Condition 條款判定，本項目為既有內部專有產品 (Cloud-360 A1) 之特定演算法與架構幾何擴展，非面向公開市場之全新產品，故 Stage 1.2 Market Research 判定為 `skipped`。相關需求直接源於內部企業架構顧問之高頻提案痛點，業務價值與投資必要性明確。

## Feasibility and Risk Highlights

### 技術可行性 (Feasibility Assessment)
經過現有程式庫逐行查證，整體技術可行性評定為 **HIGH**：
1. **多雲群組共存**：`backend/services/diagram_builder.py` 內建之 `GROUP_STYLES` 已原生具備 `aws_cloud`、`gcp_cloud`、`azure_cloud` 樣式，可直接在同一 XML 內並存渲染。
2. **n8n 上行參數**：`fetch_icon_from_n8n` HTTP POST payload 擴充 `provider = "compound"`，相容現有通訊管道。
3. **幾何佈局選型**：經評估選定中央核心雲加寬、左右雙翼對稱分佈之 **Hub-and-Spoke** 空間幾何佈局，兼顧美觀與節點容納度。

### 關鍵風險與緩解 (RAID Log)
- **R-01 (n8n compound 圖示支援度)**：若 n8n 尚未完全索引 compound 特有圖示，採用既有 cloud provider fallback 機制，保證不中斷流程。
- **R-02 (三雲節點重疊與連線交錯)**：嚴格實施 Hub-and-Spoke 幾何邊界隔離與直角折線 (Orthogonal Routing)，並在 Inception 明訂最小容器約束。
- **R-03 (前端畫布相容性)**：頂部 Provider 選單新增 Compound 選項，相容現有 mxGraph XML 解析引擎。
- **追溯來源**：
  - [feasibility-assessment.md](../feasibility/feasibility-assessment.md)
  - [constraint-register.md](../feasibility/constraint-register.md)
  - [raid-log.md](../feasibility/raid-log.md)

## Scope Boundary and Backlog

### MoSCoW 範疇邊界
- **Must Have (本次全包交付)**：
  - 後端 `draw_architecture_diagram` tool 參數支援 `provider = "compound"`。
  - 後端 `diagram_builder.py` 實作 Hub-and-Spoke 幾何佈局、三雲群組共存與直角跨雲連線。
  - 後端 `fetch_icon_from_n8n` 上行發送 `provider = "compound"`。
  - 前端 Toolbar 新增「混合雲 (Compound)」按鈕，支援雙向選單狀態同步。
  - 專屬單元測試集 `test_diagram_builder_compound.py`。
- **Should Have**：
  - Chat 對話模型多雲關鍵字自動識別切換。
  - 跨雲連線中點協議標籤 (VPN / Direct Connect / HTTPS)。
- **Could Have**：
  - 畫布初始載入 Fit-to-Window 自動最佳縮放。
- **Won't Have (本次明確排除)**：
  - 真實雲端資源即時反向同步。
  - 第四雲（如阿里雲、Oracle Cloud）擴充。
  - 混合雲計費試算聯動與即時網絡遙測。

### 交付計畫 (Intent Backlog)
採用 Dependency-first 策略拆解為 7 個 Proto-Units：
1. `proto-unit-1-tool-schema`：擴充後端 tool schema 與 system prompt。
2. `proto-unit-2-builder-geometry`：實作 Hub-and-Spoke 幾何計算與群組 XML。
3. `proto-unit-3-n8n-client`：實作 compound provider 上行與 fallback。
4. `proto-unit-4-cross-cloud-edges`：直角折線與連線協議標籤。
5. `proto-unit-5-frontend-menu`：前端 Toolbar 選單與切換事件。
6. `proto-unit-6-intent-detection`：對話自動辨識多雲關鍵字。
7. `proto-unit-7-unit-tests`：建立獨立單元測試集防護。
- **追溯來源**：
  - [scope-document.md](../scope-definition/scope-document.md)
  - [intent-backlog.md](../scope-definition/intent-backlog.md)

## Concept Visuals and User Journey

### 線框設計亮點 (Rough Mockups)
- **佈局結構**：採用標準 Hub-and-Spoke，中央為核心雲（AWS，加寬至 480px），左翼為 GCP (360px)，右翼為 Azure (360px)，兩側留有 120px 跨雲走廊。
- **雙重入口**：使用者可由 Toolbar 主動點擊 `[Compound]` 按鈕，亦可在對話中輸入「幫我畫一個跨 AWS、GCP 和 Azure 的混合雲架構」自動切換。
- **無障礙標準**：符合 WCAG 2.1 AA 標準，三雲邊框與標籤色彩對比度均達 4.5:1 以上。
- **追溯來源**：
  - [wireframes.md](../rough-mockups/wireframes.md)
  - [user-flow.md](../rough-mockups/user-flow.md)

## Team and Execution Plan

本項目依據 Stage 1.5 之評估，採用小型敏捷／Solo 開發模式，由全端工程角色搭配 AI-DLC 自動化輔助推進。進入 Inception 階段後將接續進行 Reverse Engineering、Requirements Analysis、Architecture Design 等工程設計作業。

## Go/No-Go Recommendation

### 結論：GO :white_check_mark:
- **技術無未決阻礙**：所有核心依賴皆為現有模組，無新增外部套件風險。
- **邊界清晰嚴密**：MoSCoW 鎖定核心繪圖與前後端串接，排除非必要延伸。
- **審查通過**：Stage 1.6 Rough Mockups 已獲 Product Lead 評定為 READY。
- **建議正式核准推進至 Inception 階段。**
