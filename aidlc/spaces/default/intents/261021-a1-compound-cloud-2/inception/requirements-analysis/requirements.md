# Requirements Specification — A1 混合雲繪圖功能 (Compound Cloud Diagram)

> Stage: requirements-analysis (2.3) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游基準：
> - [intent-statement](../../ideation/intent-capture/intent-statement.md)
> - [scope-document](../../ideation/scope-definition/scope-document.md)
> - [business-overview](../../../codekb/cloud-360/business-overview.md)
> - [architecture](../../../codekb/cloud-360/architecture.md)
> - [code-structure](../../../codekb/cloud-360/code-structure.md)
> - [team-practices](../practices-discovery/team-practices.md)

## Intent Analysis

### 業務目標與意圖
A1 平台核心目標為提供直覺、高效的 AI 雲端架構設計能力。過去架構繪圖僅限單一雲平台（AWS / GCP / Azure 擇一），無法滿足大型企業客戶進行混合雲規劃、評估與提案之視覺化需求。本次功能的核心意圖是：
1. **單圖三雲全貌展示**：使架構師能在單一張 Draw.io 畫布上，同時呈現 AWS、Azure、GCP 三個主流公有雲服務之資源拓撲與互連架構。
2. **標準化上行通信協議**：統一向 n8n 服務發送 `provider = "compound"`，支援跨雲圖示解析與 fallback 機制。
3. **優質空間佈局與交互體驗**：以 Hub-and-Spoke 空間佈局與直角折線消除跨雲連線混亂，並在前端提供 Toolbar 按鈕手動選擇與對話多雲意圖智能識別之雙重入口。

---

## Functional Requirements

### 1. 後端 Tool 宣告與 Prompt 引導 (Agent Interaction)

- **FR1 (Tool 定義擴充)**：後端必須擴充 `backend/services/design_agent.py` 中的 `draw_architecture_diagram` tool 定義，支援混合雲模式。
  - **FR1.1**：`provider` 參數的列舉或容許值必須納入 `"compound"`。
  - **FR1.2**：Tool docstring 必須更新，明確指引 LLM 在多雲情境下輸出分別歸屬於 AWS、Azure、GCP 的頂層群組容器定義。
  - **FR1.3**：更新 Agent System Prompt（`backend/prompts/`），明確混合雲拓撲規劃規則，要求以主要業務核心雲居中、兩側分佈附屬雲。

### 2. Hub-and-Spoke 幾何組裝與群組渲染 (Geometry & Assembly)

- **FR2 (三雲群組共存與佈局)**：後端 `backend/services/diagram_builder.py` 必須支援單一 mxGraph XML 中同時包含三雲頂層群組與內部巢狀容器。
  - **FR2.1 (Hub-and-Spoke 佈局計算)**：實作混合雲空間座標演算法。中央核心雲（預設 AWS）容器寬度預設加寬至 480px，左右雙翼（GCP 與 Azure）各為 360px，雲與雲之間保留 120px 跨雲緩衝走廊。
  - **FR2.2 (群組樣式套用)**：依據容器之 provider / type 正確套用 `GROUP_STYLES` 中的 `aws_cloud`、`gcp_cloud` 與 `azure_cloud` 樣式常數，確保三雲視覺辨識度分明。
  - **FR2.3 (座標邊界隔離)**：所有子容器（VPC/VNet、Subnet）與節點節點（Node）的絕對與相對座標必須完全收斂在其所屬雲之頂層邊界內，嚴格禁止群組重疊。

### 3. 跨雲連線與協定標籤 (Cross-Cloud Edges)

- **FR3 (跨雲連線路徑與標籤)**：支援跨越不同雲端群組之節點間拓撲連線。
  - **FR3.1 (直角折線路由)**：跨雲 edges 必須採用直角折線 (Orthogonal Routing)，避免貝茲曲線或斜直線造成的節點穿透與雜亂。
  - **FR3.2 (連線端點錨定)**：跨雲 edges 端點優先錨定於群組邊緣連接點或特定網關節點（如 Direct Connect Gateway、VPN Gateway）。
  - **FR3.3 (協議標籤渲染)**：連線中點必須支援動態顯示通訊協議標籤（如 "VPN Tunnel", "ExpressRoute", "HTTPS API"），字體與色彩需符合無障礙標準。

### 4. n8n 圖示服務通訊與容錯 (Icon Fetching & Fallback)

- **FR4 (n8n 上行通訊)**：後端 `fetch_icon_from_n8n` 在處理混合雲架構時，向 n8n 發送之上行 payload 必須設定 `provider = "compound"`。
  - **FR4.1 (上行 Payload 格式)**：向 `${N8N_WEBHOOK_URL}` 發送 POST 請求，body 結構為 `{"service": search_name, "provider": "compound"}`。
  - **FR4.2 (逾時與異常容錯)**：HTTP 請求逾時設定為 5.0 秒。若 n8n 回傳非 200、逾時或連線中斷，必須自動回傳包含該服務名稱之灰底文字向量 SVG，並記錄 Warning 日誌，絕不中斷整個架構圖 XML 生成流程。

### 5. 前端 Toolbar 與對話互動整合 (Frontend Interaction)

- **FR5 (雙重入口支援)**：前端 `WorkspacePage` 必須提供手動選單與對話自動識別雙重觸發途徑。
  - **FR5.1 (Toolbar 選單擴充)**：畫布頂部 Provider 下拉選單或按鈕列新增「混合雲 (Compound)」選項，使用者點擊後狀態切換為 `provider="compound"`。
  - **FR5.2 (對話意圖自動切換)**：當使用者在 ChatBox 輸入包含多雲關鍵字（如「跨 AWS 與 GCP」、「畫一個三雲混合拓撲」）時，後端 Agent 自主辨識並呼叫 `draw_architecture_diagram(provider="compound", ...)`，前端收到 XML 後自動同步選單狀態。
  - **FR5.3 (畫布自動最佳視角)**：收到混合雲巨型 XML 渲染後，DrawioCanvas 自動執行 Fit-to-Window，確保三雲全貌即時可見。

---

## Non-Functional Requirements

- **NFR1 (效能與逾時)**：
  - 單張混合雲架構圖（包含三雲群組、最多 20 個元件節點與 15 條連線）的 XML 幾何組裝與 n8n 查詢整體耗時不得超過 8.0 秒。
  - 單次 n8n HTTP 呼叫逾時上限嚴格鎖定為 5.0 秒。
- **NFR2 (資安與權限管制)**：
  - 符合 ADR-0006 與既有 RBAC 政策，發起混合雲產圖與對話必須具備 `A1.edit` 權限；唯讀使用者 (`A1.view`) 僅能檢視。
  - A1 Design Agent 維持行程內 MCP tool 唯一授權，嚴格禁止 Bash、Read、Write、Edit 等檔案系統存取權限。
- **NFR3 (視覺無障礙與對比度)**：
  - 三雲頂層群組邊框色彩與標籤文字對比度必須符合 WCAG 2.1 AA 標準（對比度不低於 4.5:1）。
- **NFR4 (可靠度與相容性)**：
  - 混合雲 XML 必須 100% 相容於標準 draw.io / mxGraph 渲染器，不破壞既有單一雲 (AWS / GCP / Azure) 存檔與下載功能。
- **NFR5 (零新外部依賴)**：
  - 不引入任何新增的外部 Python 套件或前端 npm 依賴套件。

---

## Constraints

- **CON1 (技術棧約制)**：後端限用 Python 3.11+ / FastAPI，前端限用 TypeScript / React 18。
- **CON2 (n8n 上行參數唯一性)**：向 n8n 請求圖示時，`provider` 參數值必須精確為小寫 `"compound"`，不得發送其他非標準字串。
- **CON3 (測試套件架構)**：新增之單元測試必須使用 Python 內建 `unittest`，放置於 `backend/tests/test_diagram_builder_compound.py`，受 CI 既有 `python -m unittest discover` 自動涵蓋。

---

## Assumptions

- **Assumptions: None.**
- **Rationale**: 所有架構與行為需求均已在既有程式庫（`diagram_builder.py` 內建三雲樣式、`fetch_icon_from_n8n` HTTP 結構、`design_agent.py` Tool 介面）中逐行完成源碼查證，並經 Product Lead 審查確認，無任何未決或未經驗證之工程假設。

---

## Out of Scope

- **OOS1**：真實雲端帳號之資源狀態反向同步與即時拓撲發現。
- **OOS2**：第四雲（如 Alibaba Cloud、Oracle Cloud、IBM Cloud）之擴充支援。
- **OOS3**：跨雲即時網絡流量、延遲遙測數據與動態告警視覺化。
- **OOS4**：混合雲架構之即時帳單或計費試算聯動（屬 FinOps/C1 範疇）。

---

## Open Questions

- **Open Questions: None.**
- **Rationale**: 需求分析問卷（Q1 ~ Q5）已就三雲群組邊界、直角折線與協議標籤、n8n 容錯、雙重入口與單元測試保護達成完全一致，所有需求邊界均已閉環。
