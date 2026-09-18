# Cloud-360 System Requirement Specification

- Status: Draft v0.2
- Date: 2026-05-22
- Owner: Danniel Chung / Anita

### 1. Platform Vision

Cloud-360 是專為雲端架構師、SRE、FinOps 與 Security 團隊設計的 AI-native 多雲架構與維運管理平台。

平台深度整合 LLM、多智能體協作框架、MCP servers、Cloud SDKs、Cloud CLIs、Terraform / OpenTofu 與可重用 Skills，並提供 MCP 與 Skill 管理功能，提供涵蓋 AWS、GCP、Azure 的端到端生命週期管理能力。

### 2. Target Users

- Cloud Architect
- SRE / Platform Engineer
- FinOps Analyst
- Security Reviewer
- Engineering Manager / Technical Decision Maker

### 3. Core Pillars

#### A. AI-Driven Architecture Design

Cloud-360 將自然語言需求轉成單雲或多雲架構藍圖。

**A1. 功能需求 (Functional Requirements)**
- **自然語言解析**: 必須能識別關鍵詞標籤，包含 workload 類型 (e.g., E-commerce, Data Processing)、HA 需求 (Multi-AZ, Multi-Region)、RTO/RPO 目標。
- **架構圖生成**: 支援生成 Mermaid、PlantUML 與符合 `.drawio` XML 規範的格式。
- **最佳實踐檢查**: 自動檢查 AWS / GCP / Azure Well-Architected Framework 的合規性。
- **災難復原設計**: 自動生成 Active-Active 或 Active-Passive 的跨雲災難復原方案建議。

**A2. 技術約束 (Technical Constraints)**
- **輸出格式**: draw.io XML 必須包含正確的雲端供應商元件圖示 (Shapes/Icons) 與 metadata。
- **架構上下文**: 生成的架構圖必須能轉換為內部 JSON 格式，供後續 Agent 讀取。

#### B. Cross-Cloud Component Selection

Cloud-360 根據 workload profile 提供 AWS / GCP / Azure 託管服務選型建議。

**B1. 功能需求 (Functional Requirements)**
- **等效服務比較**: 核心支援 Compute (VM/Container/Serverless)、Database (SQL/NoSQL/Cache)、Storage (Object/Block/File) 的對等比較。
- **選型指標**: 比較參數必須包含 SLA、硬體限制 (vCPU/Mem limits)、區域可用性、成本風險與廠商鎖定 (Vendor Lock-in) 指數。
- **決策矩陣**: 生成包含理由、優點、缺點與替代方案的決策矩陣。

**B2. 技術約束 (Technical Constraints)**
- **數據時效性**: 服務元件的規格與限制數據必須與雲端供應商官方文檔保持同步（或定義緩存過期機制）。
- **權重模型**: 推薦引擎需支援可調整的權重（例如：性能優先 vs. 成本優先）。

#### C. Cost Estimation & FinOps

Cloud-360 針對架構方案與雲端元件估算多雲 TCO。

**C1. 功能需求 (Functional Requirements)**
- **多維度成本預估**: 包含基礎設施（運算、儲存）、網路（Data Transfer/Egress）、數據服務（資料庫、快取）與維運工具。
- **計費模式比較**: 同時顯示 On-demand、Spot (AWS/Azure/GCP) 與預留實例 (RI/Savings Plan) 的對比。
- **跨雲傳輸分析**: 精確計算跨雲與跨區的 Data Egress 費用，並標註潛在的高額支出路徑。

**C2. 技術約束 (Technical Constraints)**
- **API 整合**: 必須整合 AWS Price List API、GCP Cloud Billing Catalog API 與 Azure Retail Prices API。
- **估算準確度**: 預估值需標註價格假設與數據來源的時間戳記。

#### D. Infrastructure as Code - Terraform / OpenTofu

Cloud-360 將確認後的架構藍圖轉為 Terraform / OpenTofu 模組草稿。

**Required capabilities:**
- 支援 `aws`、`google`、`azurerm` providers。
- 產出 `providers.tf`、`main.tf`、`variables.tf`、`outputs.tf` 與 `modules/` 結構。
- 不產生 production secrets。
- 所有 sensitive values 必須使用 variables、secret manager reference 或 workload identity。
- 整合 tfsec、trivy、Checkov 進行靜態掃描。

#### E. Operations Optimization Review

Cloud-360 針對已部署或設計中的架構進行持續健康檢查與效能檢視。

**Required capabilities:**
- 分析 CPU、memory、IOPS、network、storage、latency、error rate、SLO/SLA。
- 提供 right-sizing、autoscaling、backup、multi-AZ、multi-region 與 observability 建議。
- 根據雲端新服務提出架構現代化建議。

#### F. AI Multi-Cloud Operations

Cloud-360 透過 AI Chat 與 Agentic AI 管理多雲環境。

**Required capabilities:**
- AI Chat 主動式操作：使用者以自然語言查詢、分析與要求維運操作。
- Agentic AI 被動監控與主動分析：背景 agent 監控成本、安全、效能、可用性與政策風險。
- 串接 AWS / GCP / Azure MCP、SDK、CLI、API、Skills 與 Terraform providers。
- 所有高風險操作必須有人類審批。
- 所有操作必須記錄 audit log。

#### G. Cloud Security Posture & Policy Advisory

Cloud-360 檢視多雲安全策略並提出可執行的治理建議。

**Required capabilities:**
- 檢查 IAM / RBAC、Security Group / Firewall / NSG、bucket / blob access、KMS / encryption、audit logging、cloud-native policy guardrails。
- 整合 AWS IAM Access Analyzer、AWS Config、Security Hub、GuardDuty、GCP Security Command Center、GCP Organization Policy、Azure Policy、Defender for Cloud、Azure Advisor 等資料來源。
- 針對 findings 產生 severity、evidence、impact、recommended policy、remediation plan、IaC patch suggestion、verification command、rollback strategy。
- 支援 Policy-as-Code 建議，例如 OPA/Rego、Sentinel、Azure Policy、GCP Org Policy、AWS Config rule。

#### H. MCP & Skill Management

Cloud-360 需提供 MCP servers、MCP tools、AI Skills 與 cloud provider connectors 的集中管理功能。

**Required capabilities:**
- MCP Server Registry：登錄、設定、啟用/停用與檢查 MCP servers。
- Tool Catalog：列出 MCP tools、cloud SDK/CLI wrappers、Terraform tools 與 internal tools。
- Skill Catalog：管理 reusable AI Skills，例如 architecture design、FinOps、security posture review、Terraform generation、incident response。
- Permission & Risk Model：針對每個 MCP tool / Skill 標示 read-only、write、deploy、delete、permission-change、production-impacting 風險等級。
- Versioning：記錄版本、schema、owner、相依性、變更紀錄與 rollback target。
- Health Check：檢查 MCP server availability、tool schema、auth scope、latency、error rate 與最近執行狀態。
- Approval Workflow：新增、升級、停用高風險 MCP / Skill 或擴權時需 human approval。
- Agent Tool Selection Observability：Agent Routing Layer 需可依任務、上下文、風險與權限選擇合適 MCP / Skill，且可追蹤調用原因。

#### J. Identity Authentication & Role-Based Access Control

基於角色的存取控制 (RBAC) 確保平台使用者身分之安全性與權限邊界。

**J1. 功能需求 (Functional Requirements)**
- **統一登入入口**：系統必須提供安全、獨立之登入介面供使用者輸入帳號密碼進行身分驗證。
- **頁面權限控制**：使用者登入後，其側邊導航與可存取頁面必須嚴格限制在其角色權限範圍內。
- **權限編輯面板**：提供專屬於系統管理員 (`Project_Admin`) 的管理控制台，供管理員檢視、編輯並動態更新不同使用者的角色與權限範圍。

**J2. 技術約束 (Technical Constraints)**
- **路由安全防護**：前端路由與後端 API 必須同步實施 RBAC 驗證，防止未授權使用者通過修改 URL 路由或發送直接 API 請求來繞過權限控制（Bypass）。
- **機密資料保護**：身分憑證與 Session Token 的存取與傳輸必須符合安全傳輸協議 (HTTPS)，且密碼必須經過強雜湊算法 (e.g., bcrypt/Argon2) 加密儲存。
- **變更即時生效**：管理員修改權限後，新的角色權限必須即刻套用至目標使用者。
- **操作審計日誌**：所有使用者權限與角色的變更行為，必須被強制寫入系統審計日誌 (Audit Log)。

### 4. User Experience Requirements

#### Desktop Web
Desktop Web 是 Cloud-360 的完整工作台，必須支援：
- AI Chat
- draw.io / diagrams.net architecture canvas
- Terraform / policy code editor
- FinOps dashboard
- Security posture dashboard
- Operations dashboard
- Agent trace
- Audit log
- Approval gate management

#### Mobile Web / Responsive Web / PWA
手機版本也以 Web 方式呈現。第一階段不做 native iOS / Android app。

Mobile Web 聚焦：
- AI Chat
- Alerts
- Approval / reject workflow
- Cloud health digest
- Cost / security / operations findings
- Readonly architecture diagram view
- Incident quick triage

Mobile Web 不作為大型 draw.io 圖面拖拉編輯或 Terraform 深度開發的主要介面。

### 5. Architecture Visualization Requirements

Cloud-360 的架構圖能力以 draw.io / diagrams.net 相容格式為核心。

**Required capabilities:**
- 支援 `.drawio` / XML source format。
- 支援 SVG / PNG / PDF export。
- 支援 Mermaid / PlantUML derived output。
- AI Chat 可新增元件、刪除元件、調整連線、標註資料流、補 HA/DR/security/observability 元件。
- 每次 AI 修改需產生 change summary 與 version history。
- 圖面需可解析成 internal architecture graph，供 FinOps、IaC、Ops、Security agents 使用。

### 6. Cloud Integration Requirements

Cloud-360 必須透過受控 integration layer 串接雲平台。

**Integration types:**
- MCP servers
- Cloud SDKs
- Cloud CLIs
- Cloud APIs
- Terraform / OpenTofu providers
- AI Skills
- MCP / Skill Registry and Management APIs

**Safety requirements:**
- Read-only operations may execute after policy classification。
- Write / delete / deploy / permission change / production-impacting operations require human approval。
- Before execution, system must provide plan, impact, rollback strategy, affected resources and verification steps。
- Secrets must never be logged, committed, or returned to users。

### 7. Non-Functional Requirements

- Security by default
- Auditability
- RBAC and least privilege
- Human approval gate for high-risk actions
- Multi-cloud extensibility
- Explainable AI decisions
- Reproducible IaC generation
- Clear separation between recommendation and execution
- Responsive Web support for desktop, tablet and mobile browsers
- Governed MCP / Skill lifecycle management

### 8. Initial Out of Scope

- Native iOS application
- Native Android application
- Direct production deployment without approval workflow
- Storing plaintext cloud credentials
- Autonomous destructive cloud changes
- Treating third-party collaborative branches as editable without explicit authorization
