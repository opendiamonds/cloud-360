# Feasibility & Constraints — 釐清問題

> Stage: feasibility（Ideation 1.3）· Depth: Standard · Scope: feature
> 作答方式：本題本已依既有架構與最佳實踐預先填入推薦答案（選項 A）。您可直接在每題的 `[Answer]:` 確認或修改選項字母與說明。
> 上游輸入：`../intent-capture/intent-statement.md` (intent-statement)。

## Sources

- [desc] Initial description: "A1 新增功能：畫混合雲架構圖，支援三個雲服務同時顯示在一張圖上，n8n 上行 provider 為 compound"
- [intent:Q1] 企業客戶有多雲／混合雲架構評估需求，單選單一雲限制了展示能力。
- [intent:Q2] 主要使用者為雲端架構師 (Cloud Architect)，需快速產出跨三雲整合架構圖。
- [intent:Q3] 架構圖需以 Cloud Boundary / Grouping 清楚區隔 AWS、Azure、GCP 元件並正常連線；n8n 上行 provider = compound。
- [intent:Q6] 依循既有 A1 單雲繪圖實作慣例，以能打通 n8n compound 流程為最高優先。
- [code:C1] `backend/services/diagram_builder.py:30-131` — `GROUP_STYLES` 已包含 `aws_cloud`, `vpc`, `az`, `public_subnet`, `private_subnet`, `gcp_cloud`, `gcp_region`, `gcp_vpc`, `azure_cloud`, `azure_vnet`, `azure_subnet` 等三雲樣式。
- [code:C2] `backend/services/diagram_builder.py:1827-1875` — `fetch_icon_from_n8n` 向 n8n webhook 送出 `{"service": search_name, "provider": provider}`。
- [code:C3] `backend/services/design_agent.py:64-77` — `draw_architecture_diagram` tool 目前宣告 `provider: str ("AWS", "GCP", "Azure")`。
- [memory:M1] `project.md#Tech Stack`: "雲端範圍：AWS / GCP / Azure 三雲的架構與維運設計"。
- [memory:M2] `team.md#Testing Posture`: "B — 新增或修改 HTTP 端點需 TestClient 測試；A — 授權矩陣變更需 allow/deny 雙向測試"。

---

## Q1. 畫布三雲群組空間佈局方式 (Multi-Cloud Spatial Layout)

查證：`diagram_builder.py` 已內建 AWS、Azure、GCP 的雲端容器樣式 [code:C1]。在單一畫布上呈現跨三雲時，空間幾何佈局的標準規範為何？

- A. 水平三欄並排（推薦）— AWS、Azure、GCP 分別佔據左、中、右三個頂層獨立 Cloud 容器（或依主從關係排列），跨雲連線以水平跨區線條相連，版面清晰、最易於閱讀跨雲架構。
- B. 垂直三層排列 — 上、中、下分別為 AWS、Azure、GCP，適合資料流向明確由上至下的架構。
- C. 中央核心＋雙翼 (Hub-and-Spoke) — 以主要承載業務的雲端為中心，另外兩雲置於兩側作為混合延伸。
- D. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: C

---

## Q2. n8n 上行與各節點圖示查詢策略 (n8n Webhook Icon Retrieval Strategy)

查證：`fetch_icon_from_n8n` 向 webhook 發送 `json={"service": search_name, "provider": provider}` [code:C2]。使用者要求整體上行需帶 `provider = "compound"`。當畫布為混合雲時，個別節點圖示向 n8n 查詢之策略為何？

- A. 雙軌精確策略（推薦）— 整體繪圖上行參數標明 `provider = "compound"`；各節點向 n8n 請求個別圖示時，若節點或其所屬群組有明確雲別（如 AWS EC2 / Azure VM / GCP GKE），則以該特定雲別查詢以確保精準命中 icon，未標明者以 `"compound"` 查詢由 n8n 端判定。
- B. 一律全送 `provider: "compound"` — 後端所有對 n8n 的 icon 請求與整體狀態皆純粹發送 `provider = "compound"`，完全由 n8n webhook 流程內部解析與比對服務圖示。
- C. 本機靜態快取優先 — 使用本機已知的 SVG 快取，失敗才向 n8n 送 `compound`。
- D. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: X 混合雲的 provider 為 compound ,有別於單一雲是直接給 AWS ,GCP 或是 Azure

---

## Q3. 跨雲連線與網路邊界呈現 (Cross-Cloud Connectivity & Boundary)

查證：跨雲整合常涉及跨雲連線（如 Direct Connect / ExpressRoute / Cloud Interconnect 或公網 API / VPN）。圖面上跨雲連線（Edges）之呈現方式為何？

- A. 標準 mxGraph 連線＋支援協議標籤（推薦）— 跨雲連線沿用標準 Edge 幾何樣式，可支援在連線上標記協議或通道類型（如 "VPN Tunnel", "HTTPS API", "DirectConnect"），兩端分別錨定在不同雲端容器的節點上。
- B. 僅用普通箭頭連線 — 不額外客製跨雲樣式，維持既有單雲 edge 繪製機制，確保最大相容性與幾何計算穩定性。
- C. 需繪製「跨雲中繼/通道」特殊群組元件 — 例如在兩雲之間繪製專屬的 Cloud Interconnect 橋接群組。
- D. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Q4. 前端畫布觸發入口與選單 (Frontend Trigger & Menu Options)

查證：目前前端提供 AWS、Azure、GCP 之選擇。新增「混合雲 (Compound)」在前端介面的呈現方式為何？

- A. 在雲端選單中新增「混合雲 (Compound)」（推薦）— 與現有 AWS、Azure、GCP 並列於 Provider 選單（例如新增標籤或按鈕選項），點選後以混合雲模式上行傳遞 `provider: "compound"`。
- B. 介面選單新增＋對話自動偵測雙支援 — 既提供混合雲選單供主動點選，當使用者於對話輸入「多雲」、「混合雲」或提及跨雲服務時，亦能自動帶入 `provider = "compound"`。
- C. 僅由對話自動判斷 — 前端介面不增設按鈕，完全由對話模型根據需求判斷是否產出 compound 圖。
- D. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: B

---

## Q5. 測試策略與驗收護欄 (Testing & Validation Guardrails)

查證：`backend/tests/test_diagram_builder.py` 目前完整覆蓋單雲群組與幾何計算；`team.md` 要求純函式與核心繪圖需有單元測試防護 [memory:M2]。本次混合雲功能的測試標準為何？

- A. 新增專屬單元測試集（推薦）— 新增 `test_diagram_builder_compound.py`，完整驗證：1) `provider = "compound"` 上行 payload、2) 三雲頂層群組並存之幾何計算與 XML 組裝、3) 跨雲 edges 之路徑計算與避障、4) mock n8n 呼叫驗證。
- B. 於既有 `test_diagram_builder.py` 增補 compound 測試案例 — 不另立新檔，於既有測試檔內追加混合雲案例。
- C. 包含後端單元測試與前端 Playwright e2e 斷言 — 同時覆蓋後端 XML 產出與前端畫布混合雲選單渲染。
- D. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Consolidated Summary Confirmation

在依這些答案產出 feasibility-assessment.md、constraint-register.md 與 raid-log.md 之前，請確認彙整內容正確。

- **Multi-Cloud Spatial Layout (Q1)**: [C] 中央核心＋雙翼 (Hub-and-Spoke) — 以主要承載業務的雲端為中心，另外兩雲置於兩側作為混合延伸。
- **n8n Icon Retrieval Strategy (Q2)**: [X] 混合雲的 provider 為 compound，有別於單一雲是直接給 AWS、GCP 或是 Azure（向 n8n 發送之上行 payload 統一設定 provider = "compound"）。
- **Cross-Cloud Connectivity (Q3)**: [A] 標準 mxGraph 連線＋支援協議標籤（如 VPN Tunnel、HTTPS API 等），穩定連結跨雲節點。
- **Frontend Menu & Trigger (Q4)**: [B] 介面選單新增「混合雲 (Compound)」選項，並支援對話模型自動識別需求帶入 compound。
- **Testing & Guardrails (Q5)**: [A] 新增專屬單元測試集 `test_diagram_builder_compound.py`，嚴格覆蓋 compound payload、三雲群組幾何、跨雲 edges 與 mock n8n 圖示通訊。

Does this all look correct before I generate the artifacts?
- Looks correct
- Request changes

[Answer]: Looks correct
