# Rough Mockups — 釐清問題

> Stage: rough-mockups（Ideation 1.6）· Depth: Standard · Scope: feature
> 作答方式：本題本已依既有架構與最佳實踐預先填入推薦答案（選項 A 或 C）。您可直接在每題的 `[Answer]:` 確認或修改選項字母與說明。
> 上游輸入：`../intent-capture/intent-statement.md`、`../scope-definition/scope-document.md`、`../scope-definition/intent-backlog.md`。

## 已由上游定案、不重問

- A1 混合雲架構繪圖，單張圖同時繪製 AWS、Azure、GCP 三朵雲 [intent:Q1] [intent:Q3]
- 向 n8n 發送之上行 payload 統一設定 `provider = "compound"` [feas:Q2]
- 畫布空間佈局採中央核心＋雙翼 (Hub-and-Spoke) 配置 [feas:Q1]
- 跨雲連線支援標準 mxGraph 連線與協議標籤（VPN Tunnel、HTTPS API 等）[feas:Q3]
- 前端 Provider 選單新增「混合雲 (Compound)」選項並支援對話自動識別 [feas:Q4] [scope:Q4]
- 線框圖示使用基本 ASCII，不依賴複雜 emoji 或不相容符號 [project.md]

## Sources

- [desc] Initial description: "A1 新增功能：畫混合雲架構圖，支援三個雲服務同時顯示在一張圖上，n8n 上行 provider 為 compound"
- [intent:Q3] 架構圖需以 Cloud Boundary / Grouping 區隔三雲元件與跨雲連線；n8n 上行 provider = compound。
- [feas:Q1] 畫布空間佈局選定中央核心＋雙翼 (Hub-and-Spoke)。
- [feas:Q2] 上行 payload 統一明確給定 `provider = "compound"`。
- [feas:Q3] 跨雲連線支援協議標籤與跨容器端點錨定。
- [feas:Q4] 前端選單新增混合雲選項，並支援對話自動識別切換。
- [scope:Q1] 整包交付 (All-in-One Must)：包含前端選單、Builder 幾何、n8n compound 通訊與單元測試。
- [scope:Q4] MoSCoW：Must 含前端 compound 選單與 Hub-and-Spoke 幾何；Could 含 Fit to Window 最佳縮放。
- [code:C1] `frontend/src/pages/WorkspacePage.tsx` — 畫布工作區具有 Provider 選單、對話面版與 mxGraph 繪圖區域。
- [code:C2] `backend/services/diagram_builder.py:30-131` — `GROUP_STYLES` 已包含 `aws_cloud`, `gcp_cloud`, `azure_cloud` 樣式。

---

## Q1. 前端畫布 Provider 選單的 UI 呈現方式

查證：`WorkspacePage.tsx` 目前提供單一雲別選單 [code:C1]。新增「混合雲 (Compound)」時之呈現形式為何？

- A. 與三單一雲並列於 Provider 標籤/按鈕（推薦）— 在現有 `[AWS] [Azure] [GCP]` 選單旁新增 `[Compound / 混合雲]` 標籤按鈕，點選後啟用混合雲對話引導與上行模式。
- B. 歡迎區快速範本卡片 — 於初始空畫布的歡迎卡片區提供「混合雲跨雲架構」捷徑卡片，點擊後直接進入對話引導。
- C. 兩者皆提供（推薦）— Provider 選單新增 `[Compound / 混合雲]` 按鈕，且歡迎卡片提供「混合雲整合架構」快速範本卡片。
- D. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: C

---

## Q2. 畫布上三雲 Hub-and-Spoke 視覺容器邊界與標題呈現

查證：Hub-and-Spoke 幾何配置以核心雲居中、另外兩雲分列兩翼 [feas:Q1]。畫布上三朵雲頂層容器的視覺邊界如何呈現？

- A. 明確的雲端供應商標題與各雲專屬樣式邊框（推薦）— 中央核心雲（如 AWS）與兩側延伸雲（如 Azure、GCP）各自帶有標準雲端邊框標籤（"AWS Cloud", "Azure Cloud", "GCP Cloud"）及既有對應色系，邊框標題清晰。
- B. 中性灰色虛線框統一呈現 — 三朵雲皆採用中性灰色虛線框，僅靠框內節點圖示與群組名稱區隔。
- C. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Q3. 跨雲連線 (Cross-Cloud Edges) 的視覺線條與標籤排版

查證：跨雲整合常涉及跨越長距離之連線與協議識別 [feas:Q3]。跨雲 edges 的視覺線條與協議標籤呈現方式為何？

- A. 標準直角折線 (Orthogonal)＋居中文字標籤（推薦）— 連線跨越雲邊界時保持直角折線平順走線，中央附帶小背景文字標籤（如 "REST API"、"VPN Tunnel"），清晰易辨且不遮擋元件。
- B. 直線無標籤 — 兩節點間以直接連線相連，不標註文字標籤，保持圖面精簡。
- C. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Q4. 畫布自動最佳縮放 (Fit to Window) 的使用者互動體驗

查證：混合雲圖表寬度較一般單雲為寬 [scope:Q4]。產圖完成後畫布之縮放與瀏覽體驗為何？

- A. 產圖後自動 Fit to Window 置中顯示全景（推薦）— 產圖完成後自動計算縮放比率，將三朵雲完整呈現在可視畫布區域內，使用者可隨時用滾輪縮放或拖曳平移細看。
- B. 維持 100% 原始比例，需手動捲動或縮放 — 畫面預設停留在核心雲，兩側雲需手動水平捲動瀏覽。
- C. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Q5. 無障礙與鍵盤導航標準 (Accessibility)

查證：前端新選單與畫布互動需符合基本無障礙規範。驗收標準為何？

- A. WCAG 2.1 AA 鍵盤導航可達（推薦）— Provider 選單支援 Tab / 方向鍵巡覽與 Enter 選取；畫布工具列按鈕具備 `aria-label`；顏色對比度符合 4.5:1。
- B. 基本滑鼠可用即可 — 不設正式無障礙鍵盤巡覽驗收要求。
- C. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Consolidated Summary Confirmation

在依這些答案產出 wireframes.md 與 user-flow.md 之前，請確認彙整內容正確。

- **Provider Selector UI (Q1)**: [C] 兩者皆提供：Provider 選單新增 [Compound / 混合雲] 按鈕，歡迎卡片亦提供混合雲範本捷徑。
- **Three-Cloud Container Styling (Q2)**: [A] 明確的雲端供應商標題與各雲專屬樣式邊框，中央核心雲與兩翼雲階層清晰。
- **Cross-Cloud Edges (Q3)**: [A] 標準直角折線＋居中協議文字標籤（如 VPN Tunnel、REST API 等），連線平順無重疊遮擋。
- **Auto Fit to Window (Q4)**: [A] 產圖完成後自動 Fit to Window 置中呈現三雲全貌，支援平滑縮放與平移。
- **Accessibility (Q5)**: [A] 符合 WCAG 2.1 AA 鍵盤巡覽標準，選單與按鈕支援 Tab/Enter 與清晰 aria-label。

Does this all look correct before I generate the artifacts?
- Looks correct
- Request changes

[Answer]: Looks correct
