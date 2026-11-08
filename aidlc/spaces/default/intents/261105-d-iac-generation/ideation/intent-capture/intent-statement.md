# Intent Statement

## Problem Statement

Workspace 上「生成 IaC」能力仍為缺口，須補齊並與既有 Design／Assessment（A）及成本（C）工作區體驗對齊。[Q1][desc]

同時，產出的 IaC 若缺少靜態掃描與 Secret 管控，安全交付不足；本意圖要標準化 IaC 生成與安全交付（D1 模板化 Terraform／OpenTofu、D2 靜態掃描、D3 Secret Manager）。[Q1][desc]

Brownfield：從現有架構圖產出 IaC。[desc]

## Target Customer

主要受益者（主→次）：[Q2]

- Alex／架構師：確認後的架構圖要能轉成完整 Terraform 模組草稿。[Q2]
- Elena／平台工程師：需要標準化、不含 production secrets 的模組化 IaC，減少手動開通。[Q2]
- Fiona／安全審查：產出須內建靜態掃描，避免危險 IAM／設定流入交付。[Q2]

## Success Metrics

- 使用者可從既有架構圖產出可下載／可檢視的 Terraform／OpenTofu 草稿，且 UI／agent 體驗對齊 A／C。[Q3]
- 產出物通過（或附帶）靜態掃描結果，且不內嵌 production secrets。[Q3]
- 使用者在 Workspace 下載／複製草稿後，於 Cloud-360 外自行 apply；平台不代 apply。[Q9]

## Initiative Trigger

客戶或內部使用者明確要求從架構圖產出 IaC。[Q4]

## Initial Scope Signal

- Workflow-selected scope：`feature`。[scope]
- User-confirmed product boundary：維持 `feature` — 在既有 Cloud-360 上新增／補齊 story D（同一套 LangGraph agent 框架；UI 風格與現有 A／C 工作區一致），不另定產品邊界。[Q8][desc]
- 本 intent 一次交付 D1＋D2＋D3（生成＋靜態掃描＋Secret Manager 整合）。[Q7]
- 既定護欄：IaC generator design 在專案範圍內；雲端供應商 production、production credentials、environment-specific secrets、direct production IaC、destructive cloud operations 在範圍外（除非經新 ADR）。[memory:M1][memory:M2]
- 未取得 human approval 不得執行 production write、IaC apply 或 IAM 變更。[memory:M4]
- IaC generator 屬 ADR-0006 property-based testing hard constraint 落點。[memory:M3]

## Assumptions & Open Questions

- 範圍／優先序的最終決策者與影響者尚未識別（Q6＝Not identified）；利害關係人利益已描述，但決策權威欄位待補。[assumption]
- 成功指標未要求「D1＋D2＋D3 皆可演示的端到端路徑」，但產品邊界選定一次交付三者；演示深度與驗收粒度留待 requirements 細化。[assumption]
