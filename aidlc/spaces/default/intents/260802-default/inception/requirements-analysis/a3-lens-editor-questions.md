# A3 Lens Editor — Requirements Clarification Questions

> AIDLC Inception（增量）— `Security_Reviewer` 動態編輯 Offline Custom Lens 五大柱審核標準  
> 現況：Lens 固定讀取 `backend/lenses/cloud360-core-mvp-lens.json`（5 pillars：Security / Reliability / Cost / Performance / Operational Excellence）；評核引擎 `wa_lens_engine.load_lens()`。  
> 請在每個 `[Answer]:` 後填寫選項字母（可複選時用逗號，例如 `A,C`）。


請回答下列問題，以鎖定本期範圍。

---

## Question 1

「動態編輯審核標準」本期要開放到哪個深度？

A) **題目／選項文字**（title、description、choice title、improvementPlan）— 不改 `id`、不改 `riskRules`

B) **完整 Lens JSON 結構**（含新增／刪除題目、choices、riskRules condition）— UI 表單或 JSON 編輯器

C) **僅支柱層級說明**（pillar name／description）— 題目內容仍靠改檔／之後再做

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 2

編輯後的 Lens 要存在哪裡？（影響部署與 `schema_rbac.sql`／`DEPLOY.md`）

A) **資料庫**（新表，例如 `wa_lenses`：現行 active 一份 JSON；啟動／評核時優先讀 DB，無則 fallback 檔案）

B) **直接覆寫** repo 內 `cloud360-core-mvp-lens.json`（僅本機／有檔案寫入權的部署可用；容器唯讀則不可行）

C) **DB 為主 + 匯出／匯入 JSON**（可下載備份、可從檔案還原）

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 3

誰可以編輯？

A) 僅 **`Security_Reviewer`**（Fiona）

B) **`Security_Reviewer` + `Platform_Admin`／`Platform_Owner`**

C) 具 **新權限旗標**（例如 `A3.lens_edit`）者；預設 seed 給 `Security_Reviewer`（Admin 可在角色權限頁調整）

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 4

儲存新標準後，對**歷史評核**與**之後新評核**的影響？

A) **只影響之後新評核**；歷史列保留當下已存的 scores／findings（不變）

B) **新評核用新 Lens**；歷史詳情額外顯示「評核當下 lens 版本／快照」（需存 `lens_version` 或 JSON 快照）

C) 允許對舊評核**一鍵重跑**套用新標準（另開功能）

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 5

UI 入口放哪裡？

A) **評估儀表板（Assessment）** 內新增「Lens 標準」分頁／按鈕（僅有權限者可見）

B) **獨立管理頁**（例如 `/admin/lens` 或 Sidebar「審核標準」）

C) **Admin 頁**擴充一個區塊（與角色權限同區）

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 6

本期是否允許**新增／刪除**題目（不只改五大柱既有題）？

A) **否** — 固定現有題目 id／數量，只改文案與（若 Q1=B）既有 riskRules

B) **是** — 可在五大柱下增刪題目（仍禁止改 pillar id 集合：維持現有五柱、不做 Sustainability）

C) **是，且可增減支柱**（超出 MVP，需另估）

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 7

本期交付深度（AIDLC）？

A) **精簡增量**：補 FR + 短 FD／計畫 → 直接 Code Gen（API＋UI＋RBAC＋測）

B) **完整增量 Inception**：RA → 修 stories → WP → FD → Code

C) **先只做後端 API**（讀寫 active lens）；UI 下期

X) Other (please describe after [Answer]: tag below)

[Answer]:
