# Wireframes — A1 混合雲架構繪圖

<!-- Stage: rough-mockups（Ideation 1.6）· 低保真線框草圖 · 來源標籤定義見 rough-mockups-questions.md 的 ## Sources。
     ASCII 線框依 stage-protocol.md 規範，僅使用基本 ASCII 字符，保持視覺與語意清晰。 -->

## 上游輸入

- **intent-statement**（`../intent-capture/intent-statement.md`）：A1 混合雲繪圖功能、單張圖同時繪製 AWS、Azure、GCP 三朵雲、n8n 上行 provider = compound [intent:Q1] [intent:Q3]。
- **scope-document**（`../scope-definition/scope-document.md`）：Must 包含前端選單、Hub-and-Spoke 幾何佈局、跨雲連線與 n8n compound 上行；Could 包含 Fit to window 最佳縮放 [scope:Q1] [scope:Q4]。
- **intent-backlog**（`../scope-definition/intent-backlog.md`）：PU-1 至 PU-7 的功能交付順位。

## 設計決策摘要

| 決策項目 | 決策內容與視覺規格 | Source |
|---|---|---|
| 選單入口 | Provider 標籤選單新增 `[Compound / 混合雲]` 按鈕，且歡迎卡片提供多雲範本捷徑 | [Q1] |
| 容器佈局 | 採用中央核心＋雙翼 (Hub-and-Spoke) 佈局，核心雲居中、另外兩雲分列兩翼，外框帶清晰雲端標籤 | [Q2] [feas:Q1] |
| 跨雲連線 | 標準直角折線 (Orthogonal)，跨越雲邊界處帶有協議標籤文字（如 "HTTPS API"、"VPN Tunnel"） | [Q3] [feas:Q3] |
| 視角縮放 | 產圖完成後自動執行 Fit to Window 最適縮放，使用者可平滑平移與滾輪縮放 | [Q4] [scope:Q4] |
| 無障礙規範 | 符合 WCAG 2.1 AA 標準，選單與操作按鈕支援 Tab / Enter 鍵盤巡覽與 `aria-label` | [Q5] |

## 1. 前端畫布頂部 Provider 選單與入口

```
+---------------------------------------------------------------------------------------+
| Cloud-360  [Workspace]  [Assessment]  [Cost]  [Admin]                    [User: Admin]|
+---------------------------------------------------------------------------------------+
| Provider: [ AWS ]  [ Azure ]  [ GCP ]  [ Compound / 混合雲 ]*                          |
|                                         ^-- 本輪新增混合雲選單項 (Q1)                      |
+---------------------------------------------------------------------------------------+
| [對話面版 (左側 30%)]                     | [架構圖畫布工作區 (右側 70%)]                     |
|                                          |                                            |
| 對話助理:                                 | +----------------------------------------+ |
| 請描述您的混合雲架構需求，例如：               | | [Fit to Window]  [Zoom +]  [Zoom -]    | |
| 「以 AWS 為核心，串接 Azure VM 與            | +----------------------------------------+ |
|   GCP BigQuery」                         | |                                        | |
|                                          | | (畫布預設置中呈現 Hub-and-Spoke 三雲架構)| |
| [ 輸入跨雲架構描述...                 ]   | |                                        | |
| [ 發送產圖 (上行 provider=compound) ]    | |                                        | |
+---------------------------------------------------------------------------------------+
```

<!-- Text fallback: 畫布頂部 Provider 標籤列在既有 AWS、Azure、GCP 旁新增「Compound / 混合雲」按鈕；左側對話區引導多雲描述並向上行發送 compound 參數；右側畫布具備 Fit to Window 最佳縮放工具。 -->

**無障礙註記**：
- Heading: `h1` 為畫布工作區標題；`h2` 為對話面版與畫布工具列。
- Navigation: Provider 選單支援鍵盤 Tab 與箭頭鍵切換，當前選取項標註 `aria-selected="true"`。
- Contrast: 文字與背景對比度達 4.5:1。

## 2. 畫布三雲 Hub-and-Spoke 空間佈局與跨雲連線

```
+=======================================================================================+
| [畫布可視區] (自動 Fit to Window 置中)                                                  |
|                                                                                       |
| +---------------------+   +--------------------------+   +--------------------------+ |
| | [Azure Cloud] (翼側) |   |    [AWS Cloud] (核心)    |   |     [GCP Cloud] (翼側)   | |
| | +-----------------+ |   | +----------------------+ |   | +----------------------+ | |
| | | Azure VNet      | |   | | AWS VPC              | |   | | GCP VPC              | | |
| | |                 | |   | |                      | |   | |                      | | |
| | | [ Azure VM ]    | |   | | [ API Gateway ]      | |   | | [ Cloud Storage ]    | | |
| | |        ^        | |   | |        |             | |   | |        ^             | | |
| | |        |        | |   | |        v             | |   | |        |             | | |
| | |        |        | |   | | [ Amazon EKS ]-------+---+---+--------+             | | |
| | |        |        | |   | |                      | |   | |   [DirectConnect]    | | |
| | +--------+--------+ |   | +--------+-------------+ |   | +----------------------+ | |
| +----------|----------+   +----------|---------------+   +--------------------------+ |
|            |                         |                                                |
|            +======[ VPN Tunnel ]=====+                                                |
|                   (跨雲連線標籤 Q3)                                                    |
+=======================================================================================+
```

<!-- Text fallback: 畫布採用 Hub-and-Spoke 拓樸，AWS Cloud 作為中央核心，Azure Cloud 位於左翼，GCP Cloud 位於右翼。各雲具備獨立頂層容器邊框與內部 VPC/VNet。EKS 與 Azure VM 之間透過帶有「VPN Tunnel」標籤之跨雲折線連線相連；EKS 與 GCP Cloud Storage 透過 DirectConnect 跨雲相連。 -->

**佈局幾何要點**：
- **頂層容器**：三大雲端容器平行橫向排開，中央核心雲享有適當加寬寬度，兩翼雲對稱分佈。
- **跨雲 Edges**：連線跨越頂層邊界時以直角正交折線延伸，文字標籤居中顯示於半透明底色標籤框中，不遮擋節點圖示。
- **階層透明度**：各雲內部 Subnet / AZ 保持既有單雲色彩規範，頂層 Cloud Boundary 清楚標示雲端名稱。

## Assumptions & Open Questions

None.
