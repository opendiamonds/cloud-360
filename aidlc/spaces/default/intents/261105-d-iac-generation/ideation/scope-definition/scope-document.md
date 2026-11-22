# Scope Document

## In Scope

本 intent 一次交付下列能力，且 MVP 定義為三者皆有可演示路徑：[Q1]

- **D1**：從既有 Workspace 架構圖產出可下載／可檢視的 Terraform／OpenTofu 草稿；UI／agent 對齊 A／C。[intent][Q1]
- **D2**：對產出草稿執行／呈現靜態掃描結果。[Q1][Q2]
- **D3**：Secret Manager 整合（不內嵌 production secrets；具體成功形狀於 requirements 細化）。[Q1][intent]
- **三 agent**：D1／D2／D3 各一個 agent。[Q2][project learning]
- **平台接線**：RBAC（含相關權限）、OpenAPI／前端型別管線；前端工作區可與 D1 並行啟動。[Q2][Q3]
- **交付模式**：平台不代 apply；使用者下載後自行 apply。[Q2][intent]

## Out of Scope

- 代 apply／plan 管線。[Q6][Q2]
- production credentials、direct production IaC、destructive cloud operations。[Q6][feasibility]
- 商業 IaC 平台整包嵌入（Terraform Cloud／Spacelift 等作為產品核心）。[Q6][Q2]
- 自研靜態掃描引擎（整合既有 CLI）。[Q6][feasibility]

## MoSCoW

| Priority | Items |
|---|---|
| **Must** | D1、D2、D3、三 agent、RBAC／OpenAPI、不代 apply、對齊 A／C 工作區 |
| **Should** | 掃描引擎可配置 |
| **Could** | 多掃描引擎 |
| **Won't** | 代 apply、production 憑證、商業 IaC 平台嵌入 |

[Q2]

## Sequencing

- 依賴：D1 → D2 → D3；前端工作區與 RBAC 可與 D1 並行。[Q3]
- 排序偏好：Dependency-first。[Q4]
- 硬性 deadline：無。[Q5]

## Value Stream (summary)

架構圖確認 → D1 生成草稿 → D2 掃描回饋 → D3 secrets 安全化 → 使用者下載 → 於 Cloud-360 外自行 apply。[Q3][intent]
