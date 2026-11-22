# User Stories — 規劃問題

> Stage: user-stories（Inception）· Depth: Standard · Scope: feature
> Intent: `261105-d-iac-generation`
> 作答：在每題 `[Answer]:` 後填選項字母。X 為自由填答。

## 已定案、不重問

- Persona 候選：Alex（架構師）、Elena（平台）、Fiona（安全）— 來自 intent
- 一次交付 D1＋D2＋D3；平台不代 apply；`backend/iac/`；PBT 三核心
- 選圖：活躍圖＋改選＋上傳；自由**檢視**步驟；執行 D2／D3／下載需 D1 成功草稿
- requirements 審查 **R-01 Critical 未解**：執行 D3 是否要求 D2 曾成功——本輪故事規劃必須處理

## Sources

- [req] `../requirements-analysis/requirements.md`
- [review] `../requirements-analysis/reviews/review-01.md`（R-01–R-05）
- [intent] personas／成功指標
- [tp] team-practices

## Q1. 故事怎麼切？

A. **依工作流程**：Epic＝進入與選圖 → D1 產碼 → D2 掃描 → D3 secrets → 下載／權限與錯誤（推薦，對齊線框步驟）。
B. **依 persona**：Alex／Elena／Fiona 各一組故事為主軸。
C. **依 FR 編號**：FR1…FR8 各一 epic，幾乎 1:1。
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. 粒度？

A. **標準**：每個 Must 步驟 2–4 個故事（含至少一條錯誤／空狀態）；Should（掃描引擎可配置等）各 ≤1 或標後續。
B. **較細**：每個 FR 子項幾乎一則故事（故事數偏多，適合嚴格 AC 追溯）。
C. **較粗**：D1／D2／D3 各一則大故事＋共用選圖／下載。
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. requirements R-01（執行 D3 是否要先跑過 D2）在故事層怎麼處理？

> 核准 requirements 時未修補。故事若再靜默，AC 會繼續歧義。

A. **本輪定案寫進故事**：執行 D3 **必須**已有至少一次 D2 成功報告（可為零 finding）；否則 disabled／API 4xx。並加對應 Must 故事／AC。（建議：對齊 scope D1→D2→D3 與掃描目的）
B. **本輪定案寫進故事**：有 D1 草稿即可執行 D3（可跳過掃描執行）；下載前若已有 HIGH／CRITICAL 仍要摘要（Q4）。
C. **留 Open**：每則相關故事 AC 標 `[open: R-01]`，強制 refined-mockups／delivery 前關閉；本 stage 不選 A／B。
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. R-02（切圖後草稿命運）？

A. 切換脈絡圖時：**清空**當次 D1／D2／D3 工作產物並提示；需重新跑 D1。
B. **保留**舊草稿但標「脈絡已更換／可能不符」；新 D1 成功後覆蓋。
C. 留 Open 給設計（故事只寫「切圖後行為須可測，細節於 refined-mockups 凍結」）。
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q5. Persona 優先與故事主角？

A. 主故事以 **Alex（架構師）** 為主路徑；Elena／Fiona 各至少一則 Must（權限／掃描關注點）。
B. 三 persona 等權各一條主路徑（故事數較多）。
C. 只寫角色中立「使用者」，persona 檔僅描述不綁故事。
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Consolidated Summary Confirmation

依你的回答，故事規劃如下：

- **切法**：依工作流程（選圖 → D1 → D2 → D3 → 下載／權限錯誤）。[Q1]=A
- **粒度**：標準（每 Must 步驟 2–4 則，含錯誤／空狀態）。[Q2]=A
- **R-01**：執行 D3 前須有至少一次 D2 成功報告；否則 disabled／4xx。[Q3]=A
- **切圖**：清空當次 D1／D2／D3 產物並提示；需重跑 D1。[Q4]=A
- **Persona**：主路徑 Alex；Elena／Fiona 各至少一則 Must。[Q5]=A

預計產出：約 12–18 則故事＋3 persona；mob（設計／開發／品質）盲評後再送核准。

Does this all look correct before I generate the stories artifacts?

- Looks correct
- Request changes

[Answer]: Looks correct
