# A3 Lens Editor — Clarification Questions

> 偵測到答題矛盾，需先釐清後才能鎖定需求並進入完整 Inception（Q7=B）。  
> 請在每個 `[Answer]:` 後填寫選項字母。


### Contradiction 1：編輯深度 vs 增刪題目

| 題號 | 你的答案 | 含義 |
|---|---|---|
| **Q1** | **A** | 只改題目／選項**文字**；**不改** `id`、**不改** `riskRules` |
| **Q6** | **B**（並給預設建議） | 可在五大柱下**新增／刪除**題目 |

這兩者衝突：新增／刪除題目必然產生新 `id`，且通常需要對應的 `riskRules`（否則無法評分）。

### Clarification Question 1

本期「可編輯範圍」以哪一項為準？

A) **以 Q6=B 為準（建議）**：可增刪五大柱下的題目；既有題可改文案；**新增題**由系統套用預設模板（含預設 choices／`riskRules`／improvementPlan），使用者可改文案；**本期 UI 仍不開放手改 riskRules 條件式**（進階 JSON 下期）

B) **以 Q1=A 為準**：固定現有題目集合與 `id`／`riskRules`，**只能改文案**；Q6 改為不可增刪

C) **完整進階**：增刪題目＋UI 可編輯 `riskRules`（等同原 Q1=B）

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

### Ambiguity 1：Q6「並給預設建議」

### Clarification Question 2

「預設建議」是指什麼？

A) **新增題時的系統模板**：自動帶入一組預設 choice 文案、improvementPlan、以及對應的預設 `riskRules`（使用者再改中文／英文文案）

B) **僅 improvementPlan 文案**：系統依題目標題產生建議改善文字（可接受／可改）

C) **A + B**（模板結構＋可產生／編輯改善建議文案）

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

### Clarification Question 3

刪除題目時的行為？

A) **軟限制**：至少每柱保留 1 題；刪除前確認；刪後只影響**之後**新評核

B) **可刪到空柱**（該柱評分／發現可能為空，需在 UI 警告）

C) **本期不可刪**，只能新增與改文案（增題可，刪題下期）

X) Other (please describe after [Answer]: tag below)

[Answer]:
