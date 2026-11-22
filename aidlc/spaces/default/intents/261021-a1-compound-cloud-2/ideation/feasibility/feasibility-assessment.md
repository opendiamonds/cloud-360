# Feasibility Assessment — A1 混合雲架構繪圖

<!-- Stage: feasibility（Ideation 1.3）· 來源標籤定義見 feasibility-questions.md 的 ## Sources。
     [Q<n>] 指本 stage 問題檔的已選答案；[intent:*] 指 intent-capture 產出；[code:C*] 指問題檔 Sources 登錄的查證事實；[memory:M*] 指 memory 層規則。 -->

## 上游輸入

- 本評估的必要上游為 intent-capture 的 **intent-statement**（`../intent-capture/intent-statement.md`）：問題陳述（單一雲限制多雲展示需求）、成功指標（三雲分區群組呈現、n8n 上行 provider = compound）與已確認的 feature 產品邊界皆承襲自該文件 [intent:Q1] [intent:Q3]。
- market-research 已依條件判定跳過（內部既有畫布延伸擴充，不涉及外部市場定位與競品研究），其可選產出 **competitive-analysis**、**market-trends**、**build-vs-buy** 不存在；本評估不依賴市場面輸入，此缺席屬合法略過而非缺漏。

## 評估結論

**技術高度可行（GO）**。A1 混合雲繪圖功能可在既有架構上平順落地，無外部法規或雲端 production 憑證阻擋 [memory:M1]，評估建立於下列已確認前提：

1. **三雲群組樣式已完備**：現有 `diagram_builder.py` 已經完整內建 AWS (`aws_cloud`, `vpc`, `az`)、GCP (`gcp_cloud`, `gcp_region`, `gcp_vpc`) 及 Azure (`azure_cloud`, `azure_vnet`, `azure_subnet`) 的樣式定義，無需新建基礎畫布群組樣式 [code:C1]。
2. **幾何佈局採中央核心＋雙翼 (Hub-and-Spoke)**：以主要承載業務或流量入口的雲端為中心，另外兩雲置於兩側作為混合延伸，幾何拓樸清晰且空間利用率高 [Q1]。
3. **n8n Webhook 統一上行 `provider = "compound"`**：前端至後端、後端至 n8n webhook 的上行 payload 統一帶入 `provider = "compound"`，由 n8n 服務目錄與比對流程進行多雲圖示支援 [Q2] [code:C2]。
4. **跨雲連線具備標籤能力**：跨雲連線沿用標準 mxGraph 連線並支援在連線上標記協議類型（如 VPN Tunnel、HTTPS API 等），跨雲連線幾何與端點錨定清晰穩定 [Q3]。
5. **前端介面與對話雙重觸發**：在 Provider 選單中新增「混合雲 (Compound)」選項供使用者主動選擇，同時對話模型在識別出跨雲關鍵字時亦可自動切換至 compound 模式 [Q4]。
6. **測試防護完整**：新增專屬單元測試集 `test_diagram_builder_compound.py`，完整覆蓋三雲群組、跨雲連線避障與 n8n compound payload [Q5] [memory:M2]。

## 技術可行性

以能力層描述現況與落差（技術細節出處見問題檔 Sources）：

| 面向 | 現況 | 落差與可行性 |
| --- | --- | --- |
| 畫布群組樣式 | `GROUP_STYLES` 已包含三雲容器定義（`aws_cloud`, `gcp_cloud`, `azure_cloud` 等）[code:C1] | **完全可行**。現有樣式直接可用，只需在 compound 模式下支援多個頂層雲容器共存於同一畫布 [Q1]。 |
| 空間幾何佈局 | 現行佈局主要針對單雲 VPC/VNet 左右並排 Multi-AZ [code:C1] | **高度可行**。實作 Hub-and-Spoke 幾何演算法，將中心雲置中、兩側雲分別放置於左右或水平兩翼，計算各雲群組的 X 座標偏移 [Q1]。 |
| n8n Webhook 整合 | `fetch_icon_from_n8n` 支援 POST 傳遞 `provider` 參數 [code:C2] | **完全可行**。將全圖上行之 `provider` 設定為 `"compound"`，傳遞給 n8n 流程進行處理 [Q2]。 |
| 跨雲連線 (Edges) | 現有 `_path_clear` 與障礙物避障邏輯支援單雲 Subnet 連線 | **高度可行**。跨雲連線會跨越不同的頂層 Cloud 容器，需確保避障計算（AABB）不會將相鄰雲容器判定為非法障礙，並支援 edge label [Q3]。 |
| 前端選單與觸發 | 前端畫布支援 provider 切換，但目前主要為單雲 | **完全可行**。於選單中新增「混合雲 (Compound)」選項，並於對話中引導生成 compound 圖 [Q4]。 |
| LLM Tool 定義 | `draw_architecture_diagram` 的 provider 參數宣告為 "AWS", "GCP", "Azure" [code:C3] | **完全可行**。擴充 `draw_architecture_diagram` 的 provider enum/type 包含 "compound"，並在 prompt 中補充三雲群組呼叫規範。 |

## 合規掃描

- **適用框架**：未指認外部強規（PCI-DSS、HIPAA 等）。本功能僅涉及架構幾何繪圖與圖示取得，不涉及任何真實雲端資源調度或 Production 存取 [memory:M1]。
- **憑證與機敏資料**：嚴格遵守禁止 commit 私鑰或雲端 credentials 之護欄 [memory:M1]；n8n webhook 僅使用環境變數設定之憑證，不儲存任何客戶敏感資訊。
- **security baseline 四面向**見 `constraint-register.md`；繪圖功能出站僅呼叫既有 n8n webhook，無額外網路暴露風險。

## 驗證方式

- **單元測試驗收**：新增 `test_diagram_builder_compound.py`，斷言在 `provider = "compound"` 時產出的 mxGraph XML 正確包含 AWS、Azure、GCP 三大群組節點及其對應階層 [Q5]。
- **n8n 通訊驗證**：以 mock httpx 驗證 `fetch_icon_from_n8n` 送出的 JSON payload 確實包含 `provider: "compound"` [Q2][Q5]。
- **幾何與連線驗證**：驗證跨雲 edges 正確建立，端點分別指向不同雲端之節點，且 XML edge style 符合標準連線規範 [Q3]。

## 風險分析

完整風險分析見同目錄 `raid-log.md`；關鍵風險與處置摘要：
- **R1 畫布尺寸與視覺擁擠**：三朵雲同時呈現在單一畫布上可能導致畫布過寬或節點重疊；處置：在 Hub-and-Spoke 佈局中設定合理的水平間距（Gap）與初始視角縮放（Zoom to fit）[Q1]。
- **R2 n8n compound 流程回傳圖示相容性**：若 n8n webhook 對 compound 識別未完全覆蓋特定多雲服務名，可能退回灰底 fallback；處置：維持既有灰底佔位圖機制，確保流程不中斷並記錄 warning log [code:C2]。
- **R3 LLM 對三雲拓樸的掌握度**：LLM 可能混淆不同雲的群組命名（如把 Azure 放在 VPC 內）；處置：在 Inception 階段完善 system prompt 的多雲邊界規範與結構化範例。

## Assumptions & Open Questions

None.
