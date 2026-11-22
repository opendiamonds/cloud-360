# Feasibility Assessment

## Verdict

**可行（Feasible）。** 在既有 Design／Assessment（A）與成本（C）的 LangGraph／Workspace 框架上，拆出 D1／D2／D3 三個 agent，並整合靜態掃描與 Secret Manager，技術與組織風險可控。[Q7][Q3]

不對雲端 production 代 apply；產出供使用者下載後自行使用。[Q6][intent]

## Technical Viability

| Area | Assessment | Basis |
|---|---|---|
| 圖 → IaC（D1） | 可行：輸入為既有 Workspace 架構圖；agent 框架可複用 A／C | [Q1][Q3][intent] |
| 靜態掃描（D2） | 可行：整合既有 CLI（Checkov／tfsec／Trivy 等），產品側建 UX／結果呈現 | [Q1][build-vs-buy] |
| Secret Manager（D3） | 可行：整合雲端 SM API／引用語法；成功形狀須在 requirements 細化 | [Q1][intent] |
| 三 agent 拆分 | 可行且為專案規則預設：D1／D2／D3 各一 agent | [Q7][project learning] |
| RBAC／OpenAPI／前端 | 可行：既有權限種子與型別管線須一併接上 | [Q1][Q3] |
| 多雲 | 可行於「圖語意→草稿」層；不綁 production 帳號代 apply | [Q6] |

## Platform Perspective (AWS / multi-cloud)

- 產品已承載 AWS／GCP／Azure 架構圖；本 intent 的雲端觸點是**圖資產與（可選）SM／掃描工具**，不是新開 production 帳號管線。[Q6]
- Staging／本機為自架（`192.168.10.10`／localhost）；與雲端 production 邊界維持既有 out-of-scope。[Q6][memory]
- 若掃描或 SM 之後需要帳號憑證，屬後續設計決策；本輪答案未要求綁定特定雲帳號才能開工。[Q6]=A（未選 B）

## Compliance Perspective

- 無額外外部合規專案（PCI／HIPAA／SOC2 等）；沿用 ADR-0006 security baseline：IAM、encryption、network exposure、audit logging。[Q2]
- 內部交付期待（掃描可審核、secrets 不進明文）仍由產品成功標準與 D2／D3 承載，但不另開合規認證範圍。[Q2][intent]

## Skills and Capacity

團隊已具備 LangGraph（A／C）、FastAPI、React／Vite、unittest／Playwright 與自架部署；判定技能足夠支撐 Build。[Q3]

無硬性外部 deadline；依 feature 正常節奏一次交付 D1＋D2＋D3。[Q4]

無已知組織阻礙。[Q5]

## Residual Risks (summary)

詳見 `raid-log.md`。主要剩餘：掃描引擎選定、D3 成功標準具體化、多雲圖語意到 Terraform 模組的品質落差。不構成「不可行」。[Q7]
