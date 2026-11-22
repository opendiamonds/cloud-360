# Requirements Analysis — 需求分析問卷

> Stage: requirements-analysis（Inception 2.3）· Depth: Standard · Scope: feature
> 基準依據：`../../ideation/` 階段產出、共用 CodeKB、`team.md` 與 `project.md` 規範。
> 作答方式：本問卷已依技術查證與架構共識預填推薦答案（選項 A）。請確認各項功能性與非功能性需求規格。

## Sources

- [desc] Initial description: "A1 新增功能：畫混合雲架構圖，支援三個雲服務同時顯示在一張圖上，n8n 上行 provider 為 compound"
- [intent:S1] `../../ideation/intent-capture/intent-statement.md` — 支援 AWS / Azure / GCP 單圖共存
- [feas:S2] `../../ideation/feasibility/feasibility-assessment.md` — Hub-and-Spoke 空間佈局與 n8n 通訊技術可行性 HIGH
- [scope:S3] `../../ideation/scope-definition/scope-document.md` — MoSCoW 核心範疇與 7 個 Proto-Units
- [mockup:S4] `../../ideation/rough-mockups/wireframes.md` — 三雲線框與 Toolbar 選單
- [codekb:C1] `codekb/cloud-360/architecture.md` — 交易四：A1 混合雲繪圖拓撲與跨雲組裝
- [codekb:C2] `codekb/cloud-360/api-documentation.md` — `draw_architecture_diagram` tool 與 n8n webhook 契約
- [code:C3] `backend/services/diagram_builder.py:30-131` — `GROUP_STYLES` 三雲原生樣式
- [team:T1] `aidlc/spaces/default/memory/team.md` — 專屬單元測試集 `test_diagram_builder_compound.py` 護欄

---

## Q1. 三雲群組邊界與容器階層 (Cloud Boundary Representation)

查證：`diagram_builder.py` 之 `GROUP_STYLES` 原生包含 `aws_cloud`、`gcp_cloud` 與 `azure_cloud` [code:C3]。三雲在畫布 XML 上的群組邊界與階層應如何呈現？

- A. 三朵雲各自獨立作為頂層容器 (AWS, Azure, GCP 各為一獨立 Group Box)，內部分別容納其專屬 VPC/VNet、Subnet 與服務節點，彼此之間在幾何座標上完全隔離不重疊（推薦）
- B. 採單一統一混合雲外框，內部以虛線分區分隔三雲
- C. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Q2. 跨雲連線路徑與協議標籤 (Cross-Cloud Edge Routing & Labeling)

查證：多雲跨環境通訊易在畫布造成混亂交叉；`rough-mockups` 已確定直角折線 (Orthogonal Routing) 原則 [mockup:S4]。

- A. 跨雲 edges 採用直角折線 (Orthogonal Routing)，連線中點以清楚文字標示互連協定（如 "VPN Tunnel", "ExpressRoute / Cloud Interconnect", "HTTPS API"），連線端點錨定於群組邊緣或閘道節點（推薦）
- B. 採直線或平滑曲線，無額外標籤文字
- C. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Q3. n8n 圖示服務通訊與容錯降級 (n8n Webhook Contract & Fallback)

查證：`fetch_icon_from_n8n` HTTP POST payload 發送 `provider = "compound"` [codekb:C2]。當外部 n8n 服務無法解析新圖示或連線逾時時的容錯策略為何？

- A. 維持 5.0 秒逾時，當 n8n 服務無法解析或回傳非 200 時，回傳包含服務名稱之灰底文字 fallback SVG，記錄 Warning log，主繪圖流程繼續完成不中斷（推薦）
- B. 若任一圖示擷取失敗即終止整體產圖並報錯
- C. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Q4. 前端選單切換與對話意圖辨識 (Frontend Trigger & State Sync)

查證：前端 `WorkspacePage` 包含 Toolbar Provider 選單與 ChatBox 對話互動 [mockup:S4]。混合雲繪圖的觸發與互動行為模式為何？

- A. 雙重入口：Toolbar 新增 Compound 按鈕供手動選擇；若在既有 AWS/Azure/GCP 模式下於對話輸入包含跨雲關鍵字（如「同時在 AWS 與 GCP」、「混合雲」），由後端 Agent 智能辨識並自動切換為 compound 產圖（推薦）
- B. 僅支援 Toolbar 手動按鈕，不支援對話自動切換
- C. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Q5. 單元測試保護基準 (Unit Test Verification Baseline)

查證：依據 `team.md` Testing Posture 決策，核心演算法必須有專屬測試集防護 [team:T1]。

- A. 於 `backend/tests/test_diagram_builder_compound.py` 新增完整單元測試集，覆蓋三雲 XML 幾何組裝、Hub-and-Spoke 座標隔離、跨雲 edges 格式與 n8n compound 上行通訊 mock（推薦）
- B. 僅執行既有測試集，不新增獨立混合雲測試檔
- C. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Consolidated Summary Confirmation

在依據上述答案產出 requirements.md 規格文件前，請確認彙整內容正確。

- **三雲邊界 (Q1)**: [A] 三朵雲各自獨立為頂層 Group Box，幾何座標完全隔離不重疊。
- **跨雲連線 (Q2)**: [A] 採直角折線 (Orthogonal Routing)，中點標註通訊協定（VPN / Direct Connect / HTTPS 等）。
- **n8n 容錯 (Q3)**: [A] 發送 `provider = "compound"`，逾時 5.0s 或非 200 時走灰底文字 fallback SVG，不中斷產圖。
- **前端互動 (Q4)**: [A] 雙重入口：Toolbar Compound 按鈕手動選擇，配合 Chat 對話多雲意圖智能自動切換。
- **測試保護 (Q5)**: [A] 建立專屬單元測試集 `test_diagram_builder_compound.py`，完整斷言幾何組裝與通訊契約。

Does this all look correct before I generate the requirements artifact?
- Looks correct
- Request changes

[Answer]: Looks correct
