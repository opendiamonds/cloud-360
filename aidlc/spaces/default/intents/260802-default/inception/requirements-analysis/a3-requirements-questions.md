# A3 Requirements Clarification Questions

> AIDLC Inception → Requirements Analysis（A3 範圍）  
> Branch: `luojingting/feat/a3-well-architected-review`  
> Context: Story A3 exists in `stories.md`; no Construction unit yet; no A3 code.

Please answer with letter choices. Fill `[Answer]:` under each question.


### Question 1
本迭代 A3 的**交付範圍**要以哪一種為準？

A) **MVP**：對單一架構圖跑評核，產出分數＋發現清單（畫面內），暫不做 PDF／SPOF 模擬動畫

B) **Story 全文 AC**：五大支柱檢測 + SPOF／AZ 模擬（RPO/RTO）+ 可下載 PDF 報告（一次做完）

C) **分兩期**：本期做評核分數＋發現＋畫布標示；下期再做 PDF 與進階模擬

D) Other (please describe after [Answer]: tag below)

[Answer]:

### Question 2
評核的**雲端框架**以哪裡為準？

A) **僅 AWS** Well-Architected（先對齊現有 A1 AWS 產圖）

B) **多雲抽象**：通用五大支柱語意，不綁定單一雲商文件細節

C) **AWS 為主**，介面預留 GCP／Azure 開關（本期只實作 AWS）

D) Other (please describe after [Answer]: tag below)

[Answer]:

### Question 3
評核**輸入**從哪裡來？

A) 僅目前工作區**已開啟／選中的** `user_diagrams.xml_data`

B) 使用者可從圖表列表**挑選任一張有權限的圖**再執行

C) 支援上傳／貼上 XML（不一定已存 DB）

D) Other (please describe after [Answer]: tag below)

[Answer]:

### Question 4
評核**引擎**偏好？

A) **規則引擎**（解析 XML／節點類型套規則；可重現、可測）

B) **LLM／Agent**（讀 XML＋規則提示產出分數與建議；較彈性）

C) **混合**：規則先掃硬性問題（如缺備援），LLM 補建議文案

D) Other (please describe after [Answer]: tag below)

[Answer]:

### Question 5
評核結果要不要**持久化**？

A) **要**：新表（如 `architecture_reviews`），可查歷史與重開報告

B) **不要**：僅當次 session／前端顯示；需重跑才有結果

C) **輕量**：只存最近一次結果掛在 diagram 上（覆寫）

D) Other (please describe after [Answer]: tag below)

[Answer]:

### Question 6
UI 入口偏好？

A) 工作區內按鈕「執行架構評估」（結果 panel／drawer）

B) 獨立「評估儀表板」頁（對齊 stories 操作流程）

C) 兩者都要：工作區快捷 + 儀表板歷史

D) Other (please describe after [Answer]: tag below)

[Answer]:

### Question 7
與 **RBAC（A3 欄）** 的關係？

A) 沿用現有 `role_permissions` 的 A3 view／edit／review（無則補 seed）

B) 暫用 A1／架構圖編輯權即可發起評核（不另開 A3 細項）

C) 僅 Security_Reviewer／Project_Editor 等特定角色可發起（硬編碼 allowlist）

D) Other (please describe after [Answer]: tag below)

[Answer]:

### Question 8
Inception 文件策略（你先前提到 A3 inception 未齊）？

A) **補齊後再 Construction**：先修 SRS／stories／unit-of-work（U-A3），再 FD→Code

B) **精簡 Inception**：只補 unit + 本 requirements，stories 維持現狀即進 Construction

C) **直接 Construction FD**：Inception 僅更新 unit-of-work 一列，其餘沿用現有 A3 story

D) Other (please describe after [Answer]: tag below)

[Answer]:
