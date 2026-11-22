# User Stories — A1 混合雲繪圖功能 (Compound Cloud Diagram)

> Stage: user-stories (2.4) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游基準：
> - [requirements](../requirements-analysis/requirements.md) (FR1~FR5, NFR1~NFR5, CON1~CON3)
> - [business-overview](../../../codekb/cloud-360/business-overview.md)
> - [component-inventory](../../../codekb/cloud-360/component-inventory.md)
> - [team-practices](../practices-discovery/team-practices.md)
> - [personas](personas.md) (Alex, Brenda, Charlie)

---

## 1. 使用者故事總覽與優先級矩陣 (Stories Overview & MoSCoW Matrix)

本專案將 A1 混合雲繪圖功能拆解為 4 大主題群組（共 11 個使用者故事），完整覆蓋前端交互、Agent 智能識別、後端幾何拓撲組裝與外部通訊容錯：

| Story ID | 主題分類 | 故事名稱簡述 | 角色 | 優先級 (MoSCoW) | 追溯需求 (Upstream) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **US1.1** | UI & 交互 | Toolbar 提供混合雲模式手動切換 | Brenda | **Must Have** | FR5, FR5.1 |
| **US1.2** | UI & 交互 | ChatBox 自然語言意圖自動識別多雲 | Brenda | **Should Have** | FR5, FR5.2 |
| **US1.3** | UI & 交互 | DrawioCanvas 自動 Fit-to-Window 最佳視角 | Brenda, Alex | **Should Have** | FR5, FR5.3 |
| **US2.1** | Agent 交互 | Design Agent 宣告 compound 繪圖參數 | Alex | **Must Have** | FR1, FR1.1, FR1.2, NFR2 |
| **US2.2** | Agent 交互 | System Prompt 引導核心雲置中拓撲 | Alex | **Must Have** | FR1, FR1.3 |
| **US3.1** | 幾何組裝 | 三雲頂層群組容器渲染與樣式套用 | Alex | **Must Have** | FR2, FR2.2, FR2.3, NFR3, NFR4 |
| **US3.2** | 幾何組裝 | Hub-and-Spoke 幾何空間計算與緩衝走廊 | Alex | **Must Have** | FR2, FR2.1, FR2.3 |
| **US3.3** | 連線路由 | 跨雲節點直角折線與端點錨定 | Alex | **Must Have** | FR3, FR3.1, FR3.2 |
| **US3.4** | 連線路由 | 跨雲通訊協議文字標籤動態渲染 | Alex | **Must Have** | FR3, FR3.3, NFR3 |
| **US4.1** | 外部通訊 | n8n 上行發送 provider="compound" | Charlie | **Must Have** | FR4, FR4.1, CON2 |
| **US4.2** | 外部通訊 | n8n 5.0 秒逾時保護與灰底向量 SVG Fallback | Charlie | **Must Have** | FR4, FR4.2, NFR1, NFR5 |

---

## 2. Group 1: 使用者介面與雙重觸發入口 (UI & Interaction)

### US1.1: Toolbar 提供混合雲模式手動切換
- **敘述**: As a **Brenda (售前顧問)**, I want **在 WorkspacePage 的 Toolbar 下拉選單中直接選擇「混合雲 (Compound)」選項**, so that **我能在客戶提案時手動一鍵切換至混合雲繪圖模式，清晰掌握當前雲端提供商狀態**。
- **優先級**: **Must Have**
- **追溯**: FR5, FR5.1
- **驗收標準 (Acceptance Criteria)**:
  - **AC1.1.1**: 在畫布頂部 Provider 選擇元件中，除了既有的 AWS、Azure、GCP 外，明確新增「混合雲 (Compound)」選項。
  - **AC1.1.2**: 使用者點擊切換為 Compound 時，前端全域狀態更新為 `provider = "compound"`，且在發起對話或繪圖請求時正確傳遞此參數。
  - **AC1.1.3**: 切換選項時，Toolbar 按鈕視覺狀態應具備清晰的高亮或選中反饋，符合 WCAG 2.1 AA 無障礙標準。

### US1.2: ChatBox 自然語言意圖自動識別多雲
- **敘述**: As a **Brenda (售前顧問)**, I want **在 ChatBox 對話框輸入包含多雲關鍵字時，系統能自主識別並調用混合雲繪圖能力**, so that **我無需手動切換按鈕即可流暢推進多雲架構對話**。
- **優先級**: **Should Have**
- **追溯**: FR5, FR5.2
- **驗收標準 (Acceptance Criteria)**:
  - **AC1.2.1**: 當使用者輸入包含跨雲關鍵字（如「跨 AWS 與 GCP」、「混合雲架構」、「同時呈現三個雲」）時，後端 Agent 準確調用 `draw_architecture_diagram(provider="compound", ...)`。
  - **AC1.2.2**: 前端收到混合雲產圖事件後，Toolbar 的 Provider 下拉選單自動同步選中「混合雲 (Compound)」選項，維持介面狀態一致。
  - **AC1.2.3**: 若使用者明確指定單一雲（如「只畫 AWS」），系統維持單一雲模式，不誤觸混合雲。

### US1.3: DrawioCanvas 自動 Fit-to-Window 最佳視角
- **敘述**: As a **Brenda (售前顧問) 與 Alex (企業架構師)**, I want **繪圖引擎產出混合雲巨型 XML 後，畫布自動執行最佳縮放 (Fit-to-Window)**, so that **我們在第一時間即可縱覽三雲全景，無需手動縮放與拖曳畫布**。
- **優先級**: **Should Have**
- **追溯**: FR5, FR5.3
- **驗收標準 (Acceptance Criteria)**:
  - **AC1.3.1**: 當接收到混合雲架構 XML 並完成 mxGraph DOM 渲染後，DrawioCanvas 觸發最佳視窗自我調整演算法。
  - **AC1.3.2**: 確保三朵雲（中央 AWS、兩翼 GCP 與 Azure）均完整落入目前瀏覽器視窗可視範圍內，四周留有適度邊距 (padding ≥ 20px)。
  - **AC1.3.3**: 視窗縮放動畫流暢，無畫面閃爍或局部元件遮蔽現象。

---

## 3. Group 2: 後端 Agent 宣告與提示引導 (Agent Interaction & Prompting)

### US2.1: Design Agent 宣告 compound 繪圖參數
- **敘述**: As a **Alex (企業架構師)**, I want **後端 Design Agent 在 Tool 宣告中正式支援 provider="compound" 參數**, so that **LLM 能在規劃多雲架構時合法調用混合雲繪圖介面**。
- **優先級**: **Must Have**
- **追溯**: FR1, FR1.1, FR1.2, NFR2
- **驗收標準 (Acceptance Criteria)**:
  - **AC2.1.1**: `backend/services/design_agent.py` 之 `draw_architecture_diagram` tool 參數定義中，`provider` 欄位列舉容許 `"compound"`。
  - **AC2.1.2**: Tool docstring 清楚描述混合雲模式的使用情境，引導 LLM 在多雲拓撲時輸出包含三雲頂層群組容器之資料結構。
  - **AC2.1.3**: 符合 ADR-0006 與既有 RBAC 權限管制，僅具備 `A1.edit` 權限的使用者能調用此 tool，唯讀使用者受拒絕保護。

### US2.2: System Prompt 引導核心雲置中拓撲
- **敘述**: As a **Alex (企業架構師)**, I want **Agent 系統提示詞引導 LLM 遵循主要業務核心雲置中、附屬雲分佈兩側的拓撲原則**, so that **生成的混合雲架構具備高度邏輯性與專業美感**。
- **優先級**: **Must Have**
- **追溯**: FR1, FR1.3
- **驗收標準 (Acceptance Criteria)**:
  - **AC2.2.1**: 更新 `backend/prompts/` 中的架構規劃提示詞，明確混合雲拓撲佈局規則：以運算或資料庫核心所在之主要公有雲居中（預設為 AWS），兩側對稱或並列分佈外部雲。
  - **AC2.2.2**: 提示詞要求在跨雲連線中標明明確業務語義（如身分同步、數據匯流、災難備援）。
  - **AC2.2.3**: 生成結果符合金融與企業架構審查標準，無不合理之跨雲反向繞行連線。

---

## 4. Group 3: 幾何佈局組裝與跨雲直角折線 (Topology Assembly & Routing)

### US3.1: 三雲頂層群組容器渲染與樣式套用
- **敘述**: As a **Alex (企業架構師)**, I want **單一張 Draw.io mxGraph XML 中同時包含分別代表 AWS、Azure、GCP 的頂層群組容器，並套用專屬視覺樣式**, so that **各公有雲邊界分明，視覺辨識度高**。
- **優先級**: **Must Have**
- **追溯**: FR2, FR2.2, FR2.3, NFR3, NFR4
- **驗收標準 (Acceptance Criteria)**:
  - **AC3.1.1**: `diagram_builder.py` 產出的 XML 中，三雲各自擁有獨立的頂層 Group Box 節點。
  - **AC3.1.2**: 正確套用既有 `GROUP_STYLES` 中的 `aws_cloud`、`azure_cloud`、`gcp_cloud` 樣式常數（含雲端品牌標準邊框色、標題與背景透明度）。
  - **AC3.1.3**: 所有子容器（VPC/VNet、Subnet）與節點（Node）嚴格收斂在其所屬雲之頂層邊界內，群組座標完全隔離不重疊。
  - **AC3.1.4**: 產出的 XML 100% 符合標準 draw.io / mxGraph 規範，支援匯出、儲存與本機編輯。

### US3.2: Hub-and-Spoke 幾何空間計算與緩衝走廊
- **敘述**: As a **Alex (企業架構師)**, I want **繪圖引擎採用 Hub-and-Spoke 空間座標計算，為中央核心雲配置 480px 寬度，兩側各配置 360px 寬度，並保留 120px 緩衝走廊**, so that **跨雲架構佈局工整、空間充裕，消除群組擠壓**。
- **優先級**: **Must Have**
- **追溯**: FR2, FR2.1, FR2.3
- **驗收標準 (Acceptance Criteria)**:
  - **AC3.2.1**: 中央核心雲頂層容器預設寬度設定為 480px，左右雙翼頂層容器寬度設定為 360px。
  - **AC3.2.2**: 中央雲與兩翼雲之間計算保留 120px 之跨雲通道緩衝走廊（Buffer Corridor）。
  - **AC3.2.3**: 當單一雲內節點過多時，自動依據子節點網格動態放大該雲容器尺寸，同時相應推移鄰近雲容器座標，嚴格維持 120px 緩衝隔離。

### US3.3: 跨雲節點直角折線與端點錨定
- **敘述**: As a **Alex (企業架構師)**, I want **跨越不同雲端群組的連線強制採用直角折線 (Orthogonal Routing)，且端點精確錨定於群組邊緣或網關節點**, so that **架構圖連線清晰整潔，避免斜線穿透節點造成的視覺混亂**。
- **優先級**: **Must Have**
- **追溯**: FR3, FR3.1, FR3.2
- **驗收標準 (Acceptance Criteria)**:
  - **AC3.3.1**: 跨雲 edge 的 mxGraph style 必須強制包含 `edgeStyle=orthogonalEdgeStyle;` 或直角路由定義，禁止使用貝茲曲線或穿透斜線。
  - **AC3.3.2**: 連線端點優先錨定於雲端網關元件（如 VPN Gateway、Direct Connect Gateway）或群組邊界連接埠（Connection Points）。
  - **AC3.3.3**: 折線路徑在穿過 120px 緩衝走廊時保持水平或垂直直線，無不規則雜亂交錯。

### US3.4: 跨雲通訊協議文字標籤動態渲染
- **敘述**: As a **Alex (企業架構師)**, I want **在跨雲連線的中點動態標註具體的通訊協議名稱（如 VPN Tunnel / Direct Connect / HTTPS API）**, so that **架構圖具備高度的技術精確性與審查說服力**。
- **優先級**: **Must Have**
- **追溯**: FR3, FR3.3, NFR3
- **驗收標準 (Acceptance Criteria)**:
  - **AC3.4.1**: 跨雲 edge 節點具備 `value` 屬性，正確顯示協議名稱（支援 "Direct Connect", "ExpressRoute", "Cloud Interconnect", "VPN Tunnel", "HTTPS API"）。
  - **AC3.4.2**: 協議標籤文字預設居中顯示於連線路徑中段，文字背景自動覆蓋白底或半透明背景，防止與背景折線重疊干擾閱讀。
  - **AC3.4.3**: 標籤文字色彩對比度符合 WCAG 2.1 AA 標準（對比度不低於 4.5:1）。

---

## 5. Group 4: n8n 圖示服務整合與容錯降級 (n8n Service & Resilience)

### US4.1: n8n 上行發送 provider="compound"
- **敘述**: As a **Charlie (SRE 工程師)**, I want **後端 fetch_icon_from_n8n 在處理混合雲服務圖示時，向外部 n8n 服務發送之上行參數統一為 provider = "compound"**, so that **外部圖示微服務能遵循約定協議正確解析跨雲圖示**。
- **優先級**: **Must Have**
- **追溯**: FR4, FR4.1, CON2
- **驗收標準 (Acceptance Criteria)**:
  - **AC4.1.1**: 向 `${N8N_WEBHOOK_URL}` 發送 POST 請求時，Request Body 結構精確為 `{"service": search_name, "provider": "compound"}`。
  - **AC4.1.2**: 上行 `provider` 參數嚴格為小寫小寫 `"compound"` 字串，禁止發送大寫或複合雲列表。
  - **AC4.1.3**: 取得之圖示正確快取或內嵌於 mxGraph cell style 中，供前端 draw.io 正常渲染。

### US4.2: n8n 5.0 秒逾時保護與灰底向量 SVG Fallback
- **敘述**: As a **Charlie (SRE 工程師)**, I want **單次 n8n 呼叫設置 5.0 秒嚴格逾時，並在非 200 或逾時情況下自動回退至灰底文字向量 SVG**, so that **外部服務故障時混合雲產圖流程依然 100% 順暢完成**。
- **優先級**: **Must Have**
- **追溯**: FR4, FR4.2, NFR1, NFR5
- **驗收標準 (Acceptance Criteria)**:
  - **AC4.2.1**: 後端對 n8n 之 HTTP Client 設置超時上限為 5.0 秒（`timeout=5.0`）。
  - **AC4.2.2**: 當請求超時、連線中斷或 HTTP Status 非 200 時，後端即時捕獲異常並回傳內建之灰底文字向量 SVG（包含該服務名稱首字母或簡稱）。
  - **AC4.2.3**: 後端記錄 Warning 等級日誌，架構圖 XML 生成流程 100% 繼續完成，前端無錯誤提示，終端產圖總耗時不超過 8.0 秒。
  - **AC4.2.4**: 實作全程採用 Python 標準函式庫與既有依賴，零新增外部套件。

---

## 6. INVEST 準則合規性驗證 (INVEST Criteria Validation)

所有故事皆已通過 INVEST 原則審查：
- **I (Independent)**: Group 1（前端 UI）、Group 2（Agent Prompt）、Group 3（幾何引擎）、Group 4（n8n 通訊）各自具備獨立的切分介面與驗收標準。
- **N (Negotiable)**: 緩衝走廊（120px）、容器寬度（480px / 360px）均採常數宣告，具備後續可調性。
- **V (Valuable)**: 每個 Story 均直接解決 Alex、Brenda 或 Charlie 之核心痛點。
- **E (Estimable)**: 經 Inception 2.1 Reverse Engineering 驗證，既有代碼具備直接擴充基礎，工作量高度可估。
- **S (Small)**: 故事粒度控制在單一模組範圍內，可於單一 Construction Unit 內獨立落實。
- **T (Testable)**: 每個 Story 均具備清晰編號之驗收標準（AC1.1.1 ~ AC4.2.4），可完全透過自動化單元測試與端到端測試進行機械斷言。
