# Scope Definition — 釐清問題

> Stage: scope-definition（Ideation 1.4）· Depth: Standard · Scope: feature
> 作答方式：本題本已依既有架構與最佳實踐預先填入推薦答案（選項 A）。您可直接在每題的 `[Answer]:` 確認或修改選項字母與說明。
> 上游輸入：`../intent-capture/intent-statement.md`、`../feasibility/feasibility-assessment.md`、`../feasibility/constraint-register.md`。

## 已由上游定案、不重問

- 任務核心為 A1 混合雲架構繪圖，單張圖同時繪製 AWS、Azure、GCP 三朵雲 [intent:Q1] [intent:Q3]
- 向 n8n 發送之上行 payload 統一設定 `provider = "compound"` [feas:Q2]
- 空間幾何佈局採中央核心＋雙翼 (Hub-and-Spoke) 配置 [feas:Q1]
- 跨雲連線支援標準 mxGraph 連線與協議標籤（VPN Tunnel、HTTPS API 等）[feas:Q3]
- 前端支援 Provider 選單新增「混合雲 (Compound)」與對話自動識別雙軌模式 [feas:Q4]
- 測試護欄需新增專屬單元測試集 `test_diagram_builder_compound.py` [feas:Q5]

## Sources

- [desc] Initial description: "A1 新增功能：畫混合雲架構圖，支援三個雲服務同時顯示在一張圖上，n8n 上行 provider 為 compound"
- [intent:Q1] 企業客戶多雲評估需求，單選單一雲限制展示能力。
- [intent:Q3] 架構圖需以 Cloud Boundary / Grouping 區隔三雲元件與跨雲連線；n8n 上行 provider = compound。
- [intent:Q8] 工作範疇確認為 feature Scope。
- [feas:Q1] 畫布空間佈局選定中央核心＋雙翼 (Hub-and-Spoke)。
- [feas:Q2] 上行 payload 統一明確給定 `provider = "compound"`。
- [feas:Q3] 跨雲連線支援協議標籤與跨容器端點錨定。
- [feas:Q4] 前端選單新增混合雲選項，並支援對話自動識別切換。
- [feas:Q5] 測試策略新增 `test_diagram_builder_compound.py` 單元測試集。
- [code:C1] `backend/services/diagram_builder.py:30-131` — `GROUP_STYLES` 已包含三雲樣式。
- [code:C2] `backend/services/diagram_builder.py:1827-1875` — `fetch_icon_from_n8n` 透過 HTTP POST 發送 provider 參數。
- [code:C3] `backend/services/design_agent.py:64-77` — `draw_architecture_diagram` tool 參數宣告。
- [memory:M1] `project.md#Tech Stack`: "雲端範圍：AWS / GCP / Azure 三雲的架構與維運設計"。
- [memory:M2] `team.md#Testing Posture`: 核心模組需有單元測試防護。

---

## Q1. 交付切片與最小可行範圍 (Release Slicing)

查證：上游已確定核心能力（n8n compound 上行、三雲群組渲染、Hub-and-Spoke 幾何與跨雲連線）[intent:Q3] [feas:Q1]。本次功能的交付切片策略為何？

- A. 整包交付 (All-in-One Must)（推薦）— 後端 n8n compound 上行與幾何佈局、前端混合雲選單、跨雲連線與專屬單元測試集，作為單一完整 feature 交付。
- B. 兩階段切片交付 — 第一階段先完成後端 `diagram_builder` compound 渲染與 n8n 通訊；第二階段再進行前端畫布選單與對話自動識別。
- C. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Q2. 開發優先順序偏好 (Sequencing Preference)

查證：各能力間的技術依賴鏈清晰（Prompt/Tool 定義 → Builder 幾何與 n8n 通訊 → 前端觸發 → 測試防護）。本次工作的推進順序偏好為何？

- A. Dependency-first（推薦）— 依技術依賴鏈推進：(1) 後端 tool schema 與 prompt 擴充 → (2) `diagram_builder.py` compound 幾何佈局與 n8n 上行 → (3) 前端選單與觸發 → (4) 單元測試與驗證。
- B. Risk-first — 先於單元測試集中以 mock 驗證 n8n compound 上行與三雲 XML 幾何組裝（攻克最高幾何風險），再實作主流程與前端。
- C. Value-first — 先打通前端畫布混合雲選單與展示效果，後續再補齊跨雲 edges 細節與測試。
- D. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Q3. 本次明確排除事項 (Won't Have Boundary)

查證：明確排除非必要範圍可避免範圍蔓延。下列項目是否確認為本輪 Won't Have？
1. 雲端真實資源反向同步（Reverse Engineering 既有雲端實例產圖）。
2. 超過三朵雲之第四雲（如 Alibaba Cloud、OCI 等）。
3. 雲端架構圖之成本自動估算（C1 cost calculator）關聯至混合雲。
4. 跨雲連線的實體網絡延遲或頻寬即時遙測分析。

- A. 接受上列全部為本輪 Won't Have（推薦）
- B. 上列太嚴格 — 需調整排除清單（請於 Other 註明）
- C. 需額外再排除其他項目（請於 Other 註明）
- D. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Q4. 需求優先級定義 (MoSCoW Prioritization)

查證：本 feature 依價值與技術可行性劃分優先級。以下 MoSCoW 分級是否符合預期？
- **Must Have**:
  - 前端畫布支援混合雲 (Compound) 選單入口。
  - 後端向 n8n 傳送 `provider = "compound"`。
  - 單一畫布 XML 同時包含 AWS、Azure、GCP 三大群組。
  - Hub-and-Spoke 空間幾何佈局與跨雲 edges。
  - 專屬單元測試集 `test_diagram_builder_compound.py`。
- **Should Have**:
  - 對話模型在辨識出多雲關鍵字時自動引導至 compound 繪圖。
  - 跨雲連線上標示連線協議標籤（如 VPN / HTTPS）。
- **Could Have**:
  - 前端畫布載入完成後自動執行 Fit to Window 最佳縮放視角。

- A. 確認此 MoSCoW 分級符合預期（推薦）
- B. 需微調優先級（請於 Other 說明調整項目）
- C. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Q5. 交付排程與時間約束 (Timeline & Deadlines)

查證：本次功能之時程與優先級約束為何？

- A. 無外部硬性死線，但以高品質完成前後端打通為目標（推薦）
- B. 有固定 Release Sprint 期限（請於 Other 註明）
- C. 有競爭優先事項，可視情況彈性調配
- D. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Consolidated Summary Confirmation

在依這些答案產出 scope-document.md 與 intent-backlog.md 之前，請確認彙整內容正確。

- **Release Slicing (Q1)**: [A] 整包交付 (All-in-One Must)：後端 compound 幾何佈局、n8n compound 上行、前端選單、跨雲 edges 與單元測試集作為單一完整 feature 交付。
- **Sequencing Preference (Q2)**: [A] Dependency-first：依 Tool/Prompt 定義 → Builder 幾何與 n8n 通訊 → 前端選單與觸發 → 單元測試與驗證順序推進。
- **Won't Have Boundary (Q3)**: [A] 明確排除真實雲端資源同步、第四雲擴充、混合雲成本試算聯動與即時網絡遙測。
- **MoSCoW Prioritization (Q4)**: [A] Must（前端 compound 選單、n8n compound 上行、三雲群組共存、Hub-and-Spoke 幾何、單元測試集）；Should（對話自動辨識、協議標籤）；Could（畫布自動縮放 Fit to window）。
- **Timeline & Deadlines (Q5)**: [A] 無外部硬性死線，聚焦於高品質前後端打通與驗收。

Does this all look correct before I generate the artifacts?
- Looks correct
- Request changes

[Answer]: Looks correct
