# 手動測試案例：A1 混合雲繪圖功能 (Compound Cloud)

## TC: 混合雲畫布載入與平台選取器互動驗證

- plan: A1-Compound-Cloud-Plan
- priority: P1

### 目的

驗證使用者進入架構設計工作區時，頂部平台選取器包含「混合雲 (Compound)」選項，且切換後畫布能正確載入並觸發 autoFit 自動適配。

### 受測介面

- UI: `/workspace` — 架構工作區頁面：平台下拉選單、Draw.io 畫布與側邊對話欄

### 前置條件

1. 執行前端服務（`bun run --cwd frontend dev`）並開啟瀏覽器訪問 `http://localhost:5173/workspace`。
2. 確保測試帳號具備架構檢視與編輯權限。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 開啟 `/workspace` 頁面 | 頂部工具列顯示平台選取器，預設為「AWS」 |
| 2 | 點擊平台下拉選單 | 選單項目包含「AWS」、「Azure」、「GCP」與「✨ 混合雲 (Compound)」 |
| 3 | 選取「✨ 混合雲 (Compound)」 | 平台選取器切換為「✨ 混合雲 (Compound)」，畫布觸發 autoFit postMessage 縮放適配（邊界維持 32px） |

### 通過條件

- 平台選單明確列出「✨ 混合雲 (Compound)」，選取後畫布無閃爍、無報錯，並自動居中自適應視窗。

### 追溯

- 實作：`frontend/src/pages/WorkspacePage.tsx`
- 自動化對應：無
- PR／commit：doreen/feat/a1-compound-cloud-2
- User story：US1.1, US1.3


## TC: 混合雲架構生成人機對話與視覺拓撲檢核

- plan: A1-Compound-Cloud-Plan
- priority: P1

### 目的

驗證使用者在對話框中輸入跨雲混合需求時，Agent 正確解析意圖並在單一 Draw.io 畫布上呈現 AWS、Azure、GCP 三雲拓撲與直角折線膠囊標籤。

### 受測介面

- UI: `/workspace` — 架構工作區頁面：對話框輸入與 Draw.io 嵌入式架構圖展示

### 前置條件

1. 啟動後端與前端服務，以具備架構編輯權限（`A1.edit`）之帳號登入 `/workspace`。
2. 確保網路可正常存取或本地降級圖示模組已啟用。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 於側邊對話框輸入「請畫出跨 AWS EKS、Azure AKS 與 GCP GKE 的混合雲架構」並送出 | Agent 開始思考並調用 `draw_architecture_diagram`（上行 `provider="compound"`） |
| 2 | 等待畫布更新繪圖結果 | 畫布載入混合雲架構圖，左側為 Azure 容器、中央為 AWS 核心、右側為 GCP 容器（雲間間距 120px） |
| 3 | 檢視跨雲連接線 | 連線為直角折線（orthogonalEdgeStyle），連線中央具有純白背景圓角膠囊協定標籤 |

### 通過條件

- 單一 Draw.io 畫布上同時完整呈現三雲容器群組，無拓撲重疊，跨雲標籤清晰可讀且符合對比度規範。

### 追溯

- 實作：`backend/services/diagram_builder.py`
- 自動化對應：`test_diagram_builder_compound.py::TestCompoundDiagramBuilder::test_build_compound_diagram_xml_basic`
- PR／commit：doreen/feat/a1-compound-cloud-2
- User story：US2.1, US2.2

