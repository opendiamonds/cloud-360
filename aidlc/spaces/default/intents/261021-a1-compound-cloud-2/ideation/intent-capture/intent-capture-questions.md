# Intent Capture & Framing Questions

## Sources
- [desc] Initial description: "A1 新增功能：畫混合雲架構圖，支援三個雲服務同時顯示在一張圖上，n8n 上行 provider 為 compound"
- [scope] Workflow-selected scope: `feature`.
- [memory:M1] `aidlc/spaces/default/memory/project.md#Tech Stack`: "- **雲端範圍**：AWS / GCP / Azure 三雲的架構與維運設計"
- [memory:M2] `aidlc/spaces/default/memory/project.md#Decided`: "- DECIDED: 專案定位為 AI-native multi-cloud architecture & operations platform，方法論基礎為 Spec-Driven Development（SRS、user stories、architecture、ADRs）。(ADR-0001)"

## Q1. 業務問題與核心價值 (Business Problem)
本次新增 A1 混合雲架構圖繪製能力（三個雲服務同時呈現在一張架構圖上），主要解決什麼業務或使用痛點？
- A. 使用者目前無法在單一畫布上表達跨雲（AWS / Azure / GCP）整合架構，必須手動分開繪製多張單雲架構圖再行拼湊
- B. 企業客戶有真實的多雲／混合雲架構評估需求，現行單選單一雲（AWS、Azure 或 GCP）限制了混合雲場景的展示與分析能力
- C. 業務與架構師向客戶提案混合雲架構時，缺乏自動化一次產出包含三雲服務之架構圖的工具
- D. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]:B

## Q2. 目標客群與痛點 (Target Customer & Pain Point)
本功能的目標使用者主要是誰？他們面臨的最主要痛點為何？
- A. 雲端架構師 (Cloud Architect)：需要快速產出跨 AWS、Azure、GCP 的混合雲整合架構圖並定義跨雲連線
- B. 專案經理與業務顧問 (Presales / Consultant)：向客戶提案混合雲專案時需要直觀的三雲架構視覺化圖表
- C. 內部維運與開發團隊 (DevOps / SRE)：需要檢視跨雲服務串接與資料流向以評估維運邊界
- D. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]:A

## Q3. 成功指標與驗收標準 (Success Metrics)
本次 A1 混合雲繪製功能的成功驗收指標與成果標準為何？
- A. 前端提供「混合雲 (Compound / Hybrid)」選項，點擊後 n8n 上行帶 provider = "compound"，且後端 diagram_builder 成功在一張圖中繪製出包含三朵雲元件的架構圖
- B. 產出的架構圖需清楚以分區或雲端群組 (Cloud Boundary / Grouping) 區隔 AWS、Azure、GCP 元件並正常連線展示
- C. 只要能在單一架構圖上同時渲染三種雲的代表服務與圖示，且與現有 n8n webhook 及前端畫布相容無報錯即可
- D. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]:B

## Q4. 觸發契機 (Initiative Trigger)
促成本次新增 A1 混合雲架構繪圖功能的關鍵觸發契機為何？
- A. 客戶或業務團隊近期有明確的跨雲整合架構諮詢提案需求（市場與商務機會）
- B. 補齊 Cloud-360 既有三朵單一雲繪圖功能之拼圖，達成真正 multi-cloud 平台的定位
- C. 配合後續 A2 評估或 A3 審查模組的混合雲支援規劃之技術鋪路
- D. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]:B

## Q5. 關鍵利害關係人 (Key Stakeholders)
本功能的主要利害關係人及其關注焦點為何？
- A. 架構團隊（注重圖形語意精確性、跨雲連線合理性）、前端團隊（注重畫布渲染與選單互動）、後端團隊（注重 n8n payload 與 diagram_builder 整合）
- B. 產品經理／業務團隊（注重混合雲生成體驗與提案展示效果）
- C. 目前僅為內部開發與 PoC 驗證，僅關注開發人員本身之技術打通
- D. 尚未識別 (Not identified)
- X. Other (please specify)

[Answer]:A

## Q6. 決策權限與優先順序 (Decision Authority)
關於本次功能之規格邊界（如：三雲如何分群、樣式、預設元件）的最終決策者是誰？
- A. 開發者 (Doreen / 侯冠瑜) 全權主導並做技術與規格決策
- B. 需與架構小組共同評審圖形標準與分群呈現方式
- C. 依循既有 A1 單雲繪圖實作慣例，以能打通 n8n compound 流程為最高優先
- D. 尚未識別 (Not identified)
- X. Other (please specify)

[Answer]:C

## Q7. 溝通與進度回報頻率 (Communication Cadence)
本次開發任務的進度回報或溝通頻率需求為何？
- A. 在分支完成各階段實作後，透過 PR 與展示回報即可，無日常會議要求
- B. 每個 AI-DLC 階段核可點確認，並在完成前後端整合後進行 demo 驗收
- C. 無特殊回報需求 (None)
- D. 不適用 (Not applicable)
- X. Other (please specify)

[Answer]:B

## Q8. 工作範疇確認 (Scope Confirmation)
本次工作流程由引擎選定為 feature Scope（包含完整 Ideation、Inception、Construction、Operation 護欄）。這是否符合您的產品與開發邊界預期？
- A. 確認採用 feature Scope（依序完成需求分析、設計、前後端實作與測試驗收）
- B. 偏好縮窄至更輕量的 Scope（例如 poc 或 express，以快速打通 n8n compound 上行為核心）
- C. 維持 feature Scope，但在 Construction 階段聚焦於 A1 畫布選單、API payload 與 diagram_builder 混合雲渲染
- D. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]:A

## Consolidated Summary Confirmation

在依這些答案產出 intent-statement.md 與 stakeholder-map.md 之前，請確認彙整內容正確。

- **Business Problem (Q1)**: [B] 企業客戶有真實的多雲／混合雲架構評估需求，現行單選單一雲（AWS、Azure 或 GCP）限制了混合雲場景的展示與分析能力。
- **Target Customer & Pain Points (Q2)**: [A] 雲端架構師 (Cloud Architect)，需要快速產出跨 AWS、Azure、GCP 混合架構並定義跨雲連線。
- **Success Metrics (Q3)**: [B] 架構圖需以分區或雲端群組 (Cloud Boundary / Grouping) 清楚區隔 AWS、Azure、GCP 元件並正常連線展示；n8n 上行 provider = compound。
- **Initiative Trigger (Q4)**: [B] 補齊 Cloud-360 既有三朵單一雲繪圖功能之拼圖，達成真正 multi-cloud 平台的定位。
- **Stakeholders (Q5)**: [A] 架構團隊（注重圖形語意精確性、跨雲連線合理性）、前端團隊（畫布選單與渲染）、後端團隊（n8n 與 diagram_builder 整合）。
- **Decision Authority (Q6)**: [C] 依循既有 A1 單雲繪圖實作慣例，以能打通 n8n compound 流程為最高優先。
- **Communication Cadence (Q7)**: [B] 每個 AI-DLC 階段核可點確認，並在完成前後端整合後進行 demo 驗收。
- **Scope Confirmation (Q8)**: [A] 確認採用 feature Scope（依序完成需求分析、設計、前後端實作與測試驗收）。

Does this all look correct before I generate the artifact?
- Looks correct
- Request changes

[Answer]: Looks correct
