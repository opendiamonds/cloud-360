# Rough Mockups Questions

上游：intent（Workspace 生成 IaC、對齊 A／C）、scope（D1→D2→D3、三 agent）、backlog（PU-D0…D3）。

---

## Q1. 主要進入點與關鍵畫面？

A. Workspace 既有「生成 IaC」入口 → IaC 工作區（草稿／掃描／secrets 分區或步驟）
B. 獨立 `/iac` 新頁（不經 Workspace）
C. 僅後端 API；本輪不做 UI mock（與「對齊 A／C UI」衝突，需確認）
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q2. Happy path 核心流程？

A. 選架構圖／工作區脈絡 → 跑 D1 生成 → 檢視／下載草稿 → 跑 D2 掃描 → 處理 D3 secrets 提示 → 結束（不 apply）
B. 一鍵跑完 D1＋D2＋D3，只看最終打包結果
C. 先掃描既有 IaC，再生成（與 scope 依賴 D1→D2 不符，需確認）
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q3. 資訊層級（畫面上什麼最重要）？

A. 草稿內容（HCL／檔案樹）為主；掃描 findings 與 secrets 警告為次欄／步驟
B. 掃描／安全結果為主；草稿為附檔
C. Agent 對話紀錄為主（類似 Chat）；產物在側欄
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q4. 設計系統／既有 UI 模式？

A. 嚴格沿用現有 A／C Workspace layout／元件語彙（同一套）
B. 沿用大框架，但 IaC 區可有新面板模式
C. 允許明顯新視覺（需另定指南）
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q5. 裝置／形式？

A. Desktop web 為主（與現有 Cloud-360 一致）；行動僅基本可用即可
B. Desktop＋平板同等優先
C. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q6. 無障礙要求？

A. 沿用現有前端慣例；本輪 wireframe 標 landmark／標題層級即可，不做新 WCAG 專案
B. 明確目標 WCAG 2.x AA（請說明）
C. Not applicable / Not yet defined
X. Other (please specify)

[Answer]: A

---

## Consolidated Summary Confirmation

依你的回答整理如下：

- **進入點**：Workspace「生成 IaC」→ IaC 工作區（草稿／掃描／secrets）。[Q1]=A
- **Happy path**：選圖／脈絡 → D1 生成 → 檢視／下載 → D2 掃描 → D3 secrets 提示 → 結束（不 apply）。[Q2]=A
- **資訊層級**：草稿（HCL／檔案樹）為主；掃描與 secrets 為次。[Q3]=A
- **UI**：嚴格沿用 A／C Workspace layout／元件語彙。[Q4]=A
- **裝置**：Desktop web 為主。[Q5]=A
- **無障礙**：沿用現有慣例；wireframe 標 landmark／標題即可。[Q6]=A

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
