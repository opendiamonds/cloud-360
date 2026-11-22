# RAID Log — A1 混合雲架構繪圖

<!-- Stage: feasibility（Ideation 1.3）· 來源標籤定義見 feasibility-questions.md 的 ## Sources。
     Likelihood／Impact 採 Low／Medium／High 三級；處置採 mitigate／avoid／accept／transfer。 -->

## 上游輸入

- 風險與依賴脈絡承襲 intent-capture 的 **intent-statement**（`../intent-capture/intent-statement.md`）：A1 畫混合雲架構圖、單圖呈現 AWS/Azure/GCP 三朵雲、n8n 上行 provider = compound 之核心規定 [intent:Q1] [intent:Q3]。
- market-research 已依條件判定跳過（內部既有畫布延伸擴充，不涉及外部市場定位與競品研究），無市場面風險輸入。

## Risks（風險）

| # | 風險 | Likelihood | Impact | 處置 | 說明 | Source |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | 畫布三雲佈局導致寬度過大或視覺擁擠 | Medium | Medium | mitigate（設計階段） | 採用中央核心＋雙翼 (Hub-and-Spoke) 幾何配置，合理規劃三雲水平與垂直間距，並在前端載入時執行自動最適縮放 (Fit to window) | [Q1] |
| R2 | n8n Webhook 接收 compound 參數時若缺少特定雲別對照導致圖示降級 | Low | Medium | mitigate | 既有 `diagram_builder.py` 具備灰底 SVG fallback 機制，當 n8n 回應非 200 或找不到特定 icon 時自動以文字 fallback 呈現，不中斷畫布渲染流程 | [code:C2] [Q2] |
| R3 | 跨雲連線計算時被相鄰雲端容器判定為 Obstacle 導致線條折線異常 | Low | Medium | mitigate（設計階段） | 在跨雲 edge 幾何避障演算法中，將頂層 `cloud` 容器設為穿透或排除於避障計算，確保跨雲線條平順直覺 | [Q3] |
| R4 | LLM 生成多雲架構 JSON 時出現群組階層嵌套錯亂（例如把 GCP 放在 AWS VPC 內） | Medium | Medium | mitigate（設計階段） | 在 Inception 階段完善 system prompt 的 compound 幾何規範，並提供明確的三雲獨立頂層容器 JSON 範例供模型遵循 | [code:C3] |

## Assumptions（假設）

| # | 假設 | 驗證時點 | Source |
| --- | --- | --- | --- |
| A1 | n8n 服務端已具備或將對齊支援 `provider = "compound"` 之圖示查詢分流處理能力 | Inception / Construction 階段連線驗證 | [desc] [Q2] |
| A2 | 既有 `GROUP_STYLES` 內建之 AWS、Azure、GCP 樣式已能滿足混合雲畫布之視覺辨識度，不需新建額外圖形庫 | Construction 階段畫布渲染驗證 | [code:C1] [intent:Q3] |
| A3 | 混合雲模式使用者通常著重於跨雲服務互動與整體拓樸，各單一雲內之子網深度可適度精簡 | Inception 設計階段 | [intent:Q1] [intent:Q2] |

## Issues（議題）

| # | 議題 | 狀態 | Source |
| --- | --- | --- | --- |
| I1 | 既有 `draw_architecture_diagram` tool 定義限制 provider 僅為單選 ("AWS", "GCP", "Azure") | 已解（確認擴充 tool schema 支援 "compound"，並相應更新 prompt） | [code:C3] [Q2] |
| I2 | 三雲空間佈局幾何定義與單一雲 Multi-AZ 佈局之衝突 | 已解（Q1 選定中央核心＋雙翼 Hub-and-Spoke 空間配置，與單雲 Multi-AZ 水平並排相容） | [Q1] |

## Dependencies（依賴）

| # | 依賴 | 方向 | Source |
| --- | --- | --- | --- |
| D1 | 設計階段完善 compound 提示詞與三雲幾何範例 | 本功能 → Inception 設計 | [code:C3] [Q1] |
| D2 | `diagram_builder.py` 實作 compound 幾何佈局與跨雲 edges 支援 | 本功能 → Construction 實作 | [code:C1] [Q3] |
| D3 | Construction 必須交付專屬單元測試集 `test_diagram_builder_compound.py` | 本功能 → Build-and-Test | [Q5] [memory:M2] |
| D4 | 前端選單與對話串接支援傳遞 `provider = "compound"` | 本功能 → 前端實作 | [Q4] |
| D5 | 外部環境變數 `N8N_WEBHOOK_URL` 配置 | 本功能 ← 執行期環境 | [code:C2] |

## Assumptions & Open Questions

None.
