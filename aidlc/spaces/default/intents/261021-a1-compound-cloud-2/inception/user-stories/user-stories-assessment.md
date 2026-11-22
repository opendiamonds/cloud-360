# User Stories Assessment — A1 混合雲繪圖功能 (Compound Cloud Diagram)

> Stage: user-stories (2.4) · Phase: Inception · Scope: feature · Depth: Standard

## 1. 評估決策 (Assessment Decision)
- **決策**: **Execute (執行)**
- **狀態**: Approved for Elaboration

## 2. 評估理由 (Rationale)
本專案為 A1 核心架構繪圖平台的 Brownfield 重大功能擴充，具備強烈的終端使用者交互、多重使用者角色需求，以及高複雜度的跨雲拓撲幾何組裝邏輯。單純的 Functional Requirements (FR) 雖然定義了技術細節，但無法完整表述不同角色（雲端架構師、售前顧問、維運人員）在操作畫布、對話引導、視覺反饋及容錯體驗上的情境旅程與驗收標準。因此，執行 User Stories 階段能顯著降低人機交互與交付驗收的不確定性。

## 3. 考量因素 (Factors Considered)
1. **專案類型 (Project Type)**: Brownfield 擴充，既有代碼（`diagram_builder.py`、`design_agent.py`、`WorkspacePage.tsx`）已具備單一雲繪圖邏輯，混合雲引入全新的多雲群組共存與上行通訊契約。
2. **面向使用者範疇 (User-Facing Scope)**: 包含畫布 Toolbar 下拉選單/按鈕切換、ChatBox 自然語言意圖辨識智能切換、DrawioCanvas 自動 Fit-to-Window 最佳視角縮放，均直接影響架構師操作體驗。
3. **複雜度特徵 (Complexity Signals)**:
   - 空間幾何：Hub-and-Spoke 三雲佈局（中央 AWS 480px，兩翼 Azure/GCP 各 360px，緩衝走廊 120px）。
   - 連線拓撲：直角折線 (Orthogonal Routing) 與連線協議文字標籤。
   - 通訊容錯：n8n `provider="compound"` 上行，5.0 秒逾時 fallback 灰底 SVG，不中斷產圖。
   - 權限規範：`A1.edit` 編輯權限與唯讀 `A1.view` 權限分離。

## 4. 使用者故事之核心價值領域 (Key Value Areas)
1. **雲端架構師 (Enterprise Cloud Architect)**: 能夠在單一視窗中綜觀評估跨 AWS/Azure/GCP 的混合雲整合架構，精確辨識跨雲通道與邊界。
2. **售前顧問 / 解決方案架構師 (Solution Consultant)**: 能夠在客戶提案現場，透過 Chat 對話快速引導產出美觀且規範統一的三雲拓撲圖，提高提案說服力。
3. **維運與資安工程師 (SRE / Platform Engineer)**: 保證 n8n 圖示服務異常時產圖穩定不 crash，且跨雲連線標記清楚可追溯，視覺色彩對比合規（WCAG 2.1 AA）。
