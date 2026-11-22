# User Stories Planning & Questionnaire — A1 混合雲繪圖功能 (Compound Cloud Diagram)

> Stage: user-stories (2.4) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游需求：[requirements.md](../requirements-analysis/requirements.md) (FR1~FR5, NFR1~NFR5, CON1~CON3)

---

## 1. Persona 開發規劃 (Persona Development Approach)

為確保使用者故事能夠精確反映真實業務情境與終端操作期望，我們定義三類關鍵角色：

1. **Alex — 企業雲端架構師 (Enterprise Cloud Architect)**
   - **目標**: 需要在一張統一的 Draw.io 架構圖中同時規劃、評估並展示跨 AWS、Azure 與 GCP 的企業級多雲服務拓撲。
   - **痛點**: 過去僅能分開畫三張圖，無法直觀呈現跨雲專線（Direct Connect / ExpressRoute / VPN）與服務互連關係；跨雲群組容易重疊混亂。
   - **價值**: 透過清晰的 Hub-and-Spoke 三雲隔離邊界與標註清楚的連線協議，大幅提升架構評審與合規審核效率。

2. **Brenda — 售前解決方案顧問 (Presales Solution Consultant)**
   - **目標**: 在客戶架構諮詢與提案現場，能透過對話（Chat）或 Toolbar 一鍵快速產出具專業美感的三雲混合拓撲圖。
   - **痛點**: 手動調整三雲位置耗時費力，且文字描述複雜時往往無法自動觸發混合雲模式。
   - **价值**: 雙重入口（Toolbar 按鈕手動指定 + 對話智能識別）與自動 Fit-to-Window，實現 10 秒內即時生成可提案的精美架構。

3. **Charlie — 平台維運與 SRE 工程師 (Platform SRE / DevOps)**
   - **目標**: 確保架構繪圖流程高可用、不中斷，即使外部服務（n8n 圖示服務）抖動或逾時，也能優雅降級。
   - **痛點**: 過去外部依賴若失敗可能導致整張圖產出中斷或拋出 500 錯誤。
   - **價值**: n8n 嚴格 5.0 秒逾時保護與灰底向量 SVG Fallback 機制，確保產圖穩定率達 99.9% 以上。

---

## 2. 故事格式與 INVEST 準則 (Story Format & INVEST Criteria)

所有使用者故事均遵循敏捷標準格式：
`As a [persona], I want [goal], so that [benefit]`

並嚴格遵循 **INVEST** 準則：
- **Independent (獨立性)**: 故事間低耦合，各組故事具備明確驗收邊界。
- **Negotiable (可協商性)**: 驗收標準保留實作彈性（如緩衝寬度、直角路由轉折點）。
- **Valuable (具價值性)**: 每個故事均直接提供使用者可感知的操作或視覺價值。
- **Estimable (可估算性)**: 故事範圍收斂，技術難度在 Inception 2.1 Reverse Engineering 中已充分摸底。
- **Small (規模適中)**: 每個 Story 拆解至可在 1~2 天內由單一工程師完成與測試之規模。
- **Testable (可測試性)**: 每個 Story 具備明確、具體、可判定的 `AC{group}.{seq}.{crit}` 驗收標準。

---

## 3. 故事分類與切分策略 (Story Breakdown Approach)

本階段採用 **Feature & Architectural Flow Hybrid**（功能與架構流程混合切分），將需求拆解為 4 大 Story Groups：

- **Group 1: 使用者介面與雙重觸發入口 (UI & Interaction)**
  - 涵蓋 FR5.1, FR5.2, FR5.3
  - 核心：Toolbar 混合雲選項、對話關鍵字智能判定切換、畫布自動 Fit-to-Window。
- **Group 2: 後端 Agent 宣告與提示引導 (Agent Interaction & Prompting)**
  - 涵蓋 FR1.1, FR1.2, FR1.3, NFR2
  - 核心：`draw_architecture_diagram` tool 擴充、Prompt 核心雲置中拓撲指引、RBAC 權限管制。
- **Group 3: 幾何佈局組裝與跨雲直角折線 (Topology Assembly & Routing)**
  - 涵蓋 FR2.1, FR2.2, FR2.3, FR3.1, FR3.2, FR3.3, NFR3, NFR4
  - 核心：Hub-and-Spoke 座標隔離（中央 480px, 兩翼 360px, 緩衝走廊 120px）、`GROUP_STYLES` 套用、直角折線與協議標籤。
- **Group 4: n8n 圖示服務整合與容錯降級 (n8n Service & Resilience)**
  - 涵蓋 FR4.1, FR4.2, NFR1, NFR5, CON2
  - 核心：`provider="compound"` 上行通訊、5.0 秒逾時、灰底 SVG Fallback、零新外部依賴。

---

## 4. 優先級劃分策略 (MoSCoW Prioritization)

- **Must Have (必備)**:
  - US1.1 (Toolbar 選擇混合雲模式)
  - US2.1 (Design Agent 支援 compound 參數宣告)
  - US3.1 (三雲頂層群組 Hub-and-Spoke 空間隔離佈局)
  - US3.2 (跨雲節點直角折線與通訊協議標籤)
  - US4.1 (n8n provider="compound" 上行請求與圖示取得)
  - US4.2 (n8n 5.0 秒逾時與非 200 灰底 SVG 容錯降級)
- **Should Have (應備)**:
  - US1.2 (ChatBox 自然語言意圖自動識別多雲並同步 Toolbar)
  - US1.3 (DrawioCanvas 混合雲渲染自動 Fit-to-Window 最佳縮放)
- **Could Have (可備)**:
  - 自訂跨雲緩衝走廊間距設定（本期預設 120px 寫入常數）。
- **Won't Have (暫不具備)**:
  - OOS1~OOS4（即時雲端帳號反向同步、第四公有雲支援、即時流量遙測、帳單試算）。

---

## 5. 規劃問題與回饋 (Questions)

### Question 1: Persona 設計覆蓋度
本專案規劃之三位 Persona（Alex-企業雲端架構師、Brenda-售前顧問、Charlie-SRE/維運）是否足以涵蓋目標使用者族群？
- [A] 認同，此三角色已完整涵蓋架構規劃、業務展示與系統可靠度維度。
- [B] 建議增減特定角色（請說明）。

[Answer]: [A]

### Question 2: 故事切分顆粒度
將混合雲故事劃分為 4 個 Groups（UI 雙入口、Agent 宣告、幾何佈局/連線、n8n 整合/容錯），是否符合開發與驗收期望？
- [A] 認同，此切分具備高度內聚性，前後端責任邊界清楚，便於後續 Unit Generation 與平行開發。
- [B] 建議合併或進一步拆細（請說明）。

[Answer]: [A]

### Question 3: 驗收標準與 MoSCoW 策略
核心繪圖邏輯（三雲邊界、連線標籤、n8n compound、容錯）均設定為 Must Have，對話自動識別與 Fit-to-Window 設定為 Should Have，此優先度是否適當？
- [A] 認同，確保核心產圖功能優先穩定落地，使用者體驗增強作為重要輔助。
- [B] 建議調整特定故事之優先度（請說明）。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述規劃產出 personas.md 與 stories.md 前，請確認以下彙整摘要正確無誤：

- **角色設定 (Persona)**: Alex（企業雲端架構師）、Brenda（售前顧問）、Charlie（SRE 維運）。
- **切分維度 (Breakdown)**: 4 大 Group（UI 雙入口、Agent 宣告、幾何佈局/連線、n8n 整合/容錯）。
- **優先策略 (MoSCoW)**: 核心產圖邏輯與三雲隔離為 Must Have，對話自動判定與縮放為 Should Have。

Does this all look correct before I generate the user stories artifacts?
- Looks correct
- Request changes

[Answer]: Looks correct
