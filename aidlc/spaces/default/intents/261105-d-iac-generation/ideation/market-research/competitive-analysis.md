# Competitive Analysis

## Scope of Comparison

本輪同時對標兩條路徑：[Q1]

1. **架構圖／設計 → IaC 生成**
2. **IaC 安全交付**（靜態掃描／Policy／Secrets）

比較對象涵蓋雲端原生、第三方平台與開源掃描／Secret Manager 生態。[Q2]

受眾限定 Cloud-360 租戶內架構師、平台工程、安全角色；不做對外市場佔有率推論。[Q6]

## Generation Path Competitors

| Capability | Cloud-360（目標） | AWS IaC Generator／Application Composer | Azure／GCP 匯出類 | Pulumi AI／類似 AI-IaC |
|---|---|---|---|---|
| 從架構圖／設計產出 | 以既有 Workspace 架構圖為輸入（差異化）[Q4] | 強於 AWS 服務圖／Composer 流程 | 多為資源匯出，非統一多雲圖 | 強於自然語言／程式碼生成，弱於「既有 draw.io 圖」一等公民 |
| 多雲草稿 | 目標支援既有多雲圖語意 [intent] | AWS 偏重 | 各雲偏重 | 視 provider |
| 與設計／評估／成本同工作區 | 與 A／C 同一 layout／agent 語彙 [Q4][intent] | 無 | 無 | 無（獨立產品） |
| 平台代 apply | 不做；使用者下載後自行 apply [intent] | 各雲有部署路徑 | 各雲有 | 常導向自家管線 |

**解讀**：生成路徑上，純雲端工具與 AI-IaC 產品在「單雲／NL→code」強，但缺少「與 Cloud-360 Design／Assessment／成本同一工作區、從既有架構圖一鍵產出」的定位。[Q4]

## Security Delivery Path Competitors

| Capability | Cloud-360（目標） | Terraform Cloud／HCP、Spacelift、env0 | Checkov／tfsec／Trivy＋OpenTofu | 雲端 Secret Manager |
|---|---|---|---|---|
| 靜態掃描／Policy-as-Code | D2 納入交付（table-stakes）[Q3][Q4] | 產品化管線＋策略閘門強 | CLI／CI 整合成熟、可嵌入 | N/A |
| Secrets 不進草稿明文 | D3；不內嵌 production secrets [intent][Q3] | 常與 vault／變數系統整合 | 需另接 | 原生存放與引用 |
| 與生成同工作區 | 生成後即見掃描結果（產品敘事）[Q4] | 偏獨立 IaC 平台 | 偏工具鏈 | 偏雲端控制台 |
| 代管 apply／漂移 | 本 intent 不做 [intent] | 核心賣點 | 無 | 無 |

**解讀**：安全交付路徑的 table-stakes 已由掃描＋Secret 引用定義；商業 IaC 平台強在代管 apply／漂移，與本 intent「平台不代 apply」邊界刻意錯開，避免做成第二套 Terraform Cloud。[Q4][intent]

## Positioning Summary

- **對齊而非取代**：不以完整 IaC 營運平台為競品目標；對齊「生成＋基本掃描」表態，差異化放在架構圖入口與 A／C 工作區一致性。[Q4][Q5]
- **威脅**：AI-IaC 與雲端原生產生器降低「只會吐 HCL」的差異；若無掃描／SM 與工作區整合，易被視為薄封裝。[Q3]
- **機會**：既有架構圖資產＋同一套 LangGraph／UI 語彙，是外部單點工具難以複製的切面。[Q4][intent]

## Open Gaps for Later Stages

- 具體掃描引擎與 SM 引用語法（哪家 CLI／哪種 `data` source）留待 requirements／設計細化；本文件只定「整合既有工具」方向。[Q5]
- 未做逐產品定價與完整功能打分矩陣（本輪深度為 Standard，非 Comprehensive）。[Q7]
