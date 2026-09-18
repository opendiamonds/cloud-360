# A3 增量釐清問題：自行上傳架構圖 ＋ 完善 GCP／Azure

> Branch: `luojingting/feat/a3-feature-updates`  
> 日期: 2026-07-27  
> 現況摘要：評核僅對**已入庫** `user_diagrams`；`provider≠aws` 會建 `unsupported` 紀錄；規則包僅 AWS 啟發式；Assessment 已有 provider 下拉但 GCP／Azure 未實作。

請在每個問題的 `[Answer]:` 後填入選項字母（可加簡短說明）。選 **Other** 時請描述你的方案。

---

## Question 1

本期優先順序？

A) 先做「自行上傳架構圖評核」，GCP／Azure 下一期

B) 先做「完善 GCP／Azure 評核」，上傳下一期

C) **同一期一起做**（上傳 ＋ 多雲）

D) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 2

「自行上傳」接受哪些檔案？

A) 僅 **draw.io／`.drawio`／mxGraph XML**（與現有評核輸入一致）

B) draw.io XML ＋ 匯出圖檔（PNG／SVG）— 圖檔需另走視覺／OCR 路徑（複雜度高）

C) 允許貼上 XML 文字（不必選檔），效果等同上傳

D) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 3

上傳後資料怎麼處理？

A) **一律建檔**：上傳 → 建立／更新 `user_diagrams`（使用者擁有）→ 再評核（與現有流程一致、可歷史重跑）

B) **可選建檔**：預設一次性評核；使用者可勾「同時存成架構圖」

C) **純暫時**：不入庫圖檔，只存 `architecture_reviews`（無法從工作區再開該圖）

D) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 4

上傳入口放哪裡？

A) 主要在 **評估儀表板（Assessment）**：選圖旁新增「上傳架構圖」

B) 主要在 **工作區（Workspace）**：上傳後進畫布，再點 Well-Architected

C) **兩處都有**

D) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 5

GCP／Azure「完善」要做到哪一層？

A) **最小可用**：解除 `unsupported`；用該雲關鍵字啟發式規則＋現有 Custom Lens 自動填答／打分（深度可低於 AWS）

B) **對齊 AWS 深度**：各雲獨立 rule pack（服務／邊界語意）＋ Lens／Agent 填答與建議都可跑通

C) **分階段**：本期 A（最小可用），下期再補齊各雲專屬規則深度

D) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 6

多雲評核的「支柱／框架」語意？

A) **統一沿用 AWS WA 五支柱**（操作卓越／安全／可靠／效能／成本），GCP／Azure 服務對應到同一套支柱與（可共用或微調的）Lens

B) **各雲對應官方框架名稱**（例：Azure WAF 支柱、Google CAF／Architecture Framework），UI 依 provider 切換標籤與規則

C) 本期先 A；UI 標註「以 AWS WA 支柱對照評核 GCP／Azure 圖」

D) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 7

Provider 如何決定？

A) **使用者手動選**（現有下拉：aws／gcp／azure）

B) **依圖自動偵測**（節點／圖示關鍵字），可手動覆寫

C) 上傳時必選；既有圖沿用上次或預設 aws

D) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 8

Custom Lens（`wa_lenses`／題目編輯）與多雲關係？

A) **同一套 Active Lens** 套用三雲（riskRules 仍以選擇／填答為準，與雲無關）

B) **每雲一份 Active Lens**（aws／gcp／azure 各一）

C) 本期共用一套；後續再拆

D) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 9

本期明確 **不做** 哪些？（可多選，填如 `A,C`）

A) SPOF／中斷模擬動畫

B) 呼叫雲端官方 WA API（AWS WA Tool／Azure Review 等）

C) 圖片／PDF 視覺評核（非 draw.io）

D) 以上都先不做（預設）

E) Other (please describe after [Answer]: tag below)

[Answer]:

---

填完後回覆「已回答」或貼上答案摘要，我會據此寫 requirements 並進入 Workflow Planning。
