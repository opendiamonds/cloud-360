# Initiative Brief — Story D IaC Generation

## Intent

標準化 IaC 生成與安全交付：從既有架構圖產出 Terraform／OpenTofu（D1），附靜態掃描（D2）與 Secret Manager 整合（D3）；UI／agent 對齊 A／C；平台不代 apply。[intent][Q1]

## Market Validation

Build 主路徑：自建 LangGraph／Workspace；掃描／SM 整合既有工具。差異化＝架構圖入口＋與 Design／Assessment／成本同工作區。內部租戶能力，不做對外 TAM。[market][Q5]

## Feasibility & Risks

判定**可行**。關鍵剩餘：D3 成功標準細化、選圖互動（rough R-01）、掃描引擎選定、圖→HCL 品質。已承認可進 Inception。[feasibility][Q2]

## Scope Boundary

| In | Out |
|---|---|
| D1＋D2＋D3、三 agent、RBAC／OpenAPI、對齊 A／C | 代 apply、production 憑證、商業 IaC 平台嵌入、自研掃描引擎 |

依賴：D1 → D2 → D3；排序 dependency-first。[scope]

## Concept

Workspace「生成 IaC」→ 草稿為主工作區 → 掃描 → secrets 提示 → 下載結束。[wireframes][Q4]

## Team

luojingting＋AI-DLC；solo／pair；決策者＝開 workflow 工程師。[team][Q3][Q6]

## Go / No-Go

**Go** — 進入 Inception（下一階段 Reverse Engineering）。[Q7]
