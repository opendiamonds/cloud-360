# Build vs Buy vs Partner

## Decision Summary

**傾向：Build（內建）。** 在 Cloud-360 內以既有 Workspace 與 LangGraph agent 框架實作生成體驗，並與 Design／Assessment（A）及成本（C）對齊；靜態掃描與 Secret Manager 以**整合既有工具／雲端服務**為主，而非購買完整商業 IaC 平台作為產品核心。[Q5][intent]

## Options Considered

| Option | What it means here | Fit |
|---|---|---|
| **Build** | 自建圖→IaC agent、Workspace UI、產出下載；掃描／SM 接現成工具 | 選定 [Q5] |
| **Buy／Embed** | 嵌入 Terraform Cloud／Spacelift／商業掃描 SaaS 為主體，Cloud-360 只做入口 | 未選；易變成薄封裝且常綁代 apply [Q5][Q4] |
| **Partner／Wrap only** | 生成也外包、僅包一層 API | 未選為主策略；與「對齊 A／C 同一套 agent／UI」衝突 [Q5][intent] |

## Rationale

1. **產品邊界**：成功標準是可下載草稿＋掃描／無 production secrets，平台**不代 apply**；商業 IaC 平台核心價值常在 apply／漂移，買入會拉歪範圍。[intent][Q4]
2. **差異化資產**：既有架構圖與 A／C 工作區語彙是自建理由；買現成產生器難以復用同一 layout／agent。[Q4][intent]
3. **安全交付**：掃描與 SM 屬成熟工具鏈（Checkov／tfsec／Trivy、雲端 Secret Manager），適合整合而非重寫引擎——仍落在「Build 產品體驗、整合既有工具」的 Build 敘事內。[Q2][Q5]
4. **受眾**：內部租戶能力，不需為搶外部市佔去貼牌商業平台。[Q6]

## What We Build vs Integrate

| Layer | Approach |
|---|---|
| 架構圖 → Terraform／OpenTofu 草稿（D1） | **Build**（LangGraph＋Workspace）[Q5] |
| 靜態掃描結果呈現（D2） | **Build UX**＋**整合**既有掃描工具 [Q5] |
| Secret Manager 引用／不落明文（D3） | **Build UX／產出規則**＋**整合**雲端 SM [Q5] |
| Apply／狀態後端 | **Out of scope**（使用者自行 apply）[intent] |

## Risks of the Build Path

- 若生成品質或掃描整合落後 AI-IaC／雲端原生產生器，「只有工作區整合」不足以留住使用者。[Q3]
- D3 成功標準尚需在 requirements 具體化（審閱已標），Build 範圍需避免做成完整 SM 產品。[intent-capture review R-01]

## Recommendation

維持 **Build 主路徑**：自建生成與工作區體驗；掃描／SM **整合不重造**；明確拒絕以商業 IaC 營運平台取代本 intent。[Q5][Q4]
