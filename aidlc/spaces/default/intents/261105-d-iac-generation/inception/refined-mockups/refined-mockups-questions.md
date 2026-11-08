# Refined Mockups — 釐清問題

> Stage: refined-mockups（Inception，inline）· Depth: Standard · Scope: feature  
> Intent: `261105-d-iac-generation`（Story D）  
> 作答：在每題 `[Answer]:` 後填選項字母。X 為自由填答。  
> **成本揭露**：本題組共 6 題。答完並確認摘要後產出 mockups、interaction-spec、design-system-mapping、accessibility-checklist。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 入口在 Workspace「生成 IaC」，不另開獨立 `/iac` 主路徑 | [rm:Q1]=A |
| 草稿為主區；掃描／Secrets 為步驟／次欄；不代 apply | [rm:Q2–Q3] |
| 自由**檢視**各步驟；執行 D2／D3／下載需 D1；執行 D3 另需 D2 成功報告 | [stories US3.1／US4.1／US4.2] [req FR6] |
| 切圖清空產物＋可見文字提示；進行中請求不得寫回舊圖草稿 | [stories US1.3] |
| 無權入口：**disabled＋說明**（非隱藏） | [stories AC1.1.2] |
| HIGH／CRITICAL 嚴重度文字標籤；下載前摘要含確認／取消；無 HIGH 則不彈閘 | [stories US3.2／US5.1] |
| 端到端演示多角色（種子無三角 edit）——不影響版面殼層 | [stories US6.2] |
| WCAG 2.1 AA 方向；嚴重度不單靠顏色；鍵盤操作已有故事 AC | [req NFR5] [stories AC1.1.3] |

## Sources

- [rm] `../../ideation/rough-mockups/wireframes.md`、`user-flow.md`
- [stories] `../user-stories/stories.md`、`personas.md`
- [req] `../requirements-analysis/requirements.md`
- [tp] `../practices-discovery/team-practices.md`
- [code] `frontend/src/pages/WorkspacePage.tsx`、`CostPage.tsx`、`components/Sidebar.tsx`、`Layout.tsx`

---

## Q1. 選圖／脈絡控件放哪裡？

> 故事要求：進場帶入活躍圖、可下拉改選、可上傳 `.drawio`／`.xml`；無圖則阻擋。線框 aside 只寫「脈絡：所選架構圖」，互動未釘死。這會決定 Screen 2 頂部密度與上傳失敗提示的落點（US1.2／US1.4）。

A. **Aside 脈絡卡**：圖名＋下拉改選＋「上傳」連結／次按鈕；無圖時 aside／主區顯示阻擋＋回 Workspace CTA。**（建議）** 對齊線框 aside，不搶草稿主區。
B. **主區頂部工具列**：草稿上方一條「目前架構圖」列含下拉與上傳；aside 只留 Agent 狀態與下載。代價：主區垂直空間變少。
C. **進場先彈選圖 modal**（可略過若已有活躍圖），工作區內改選仍用 aside。代價：多一步，但首次較清楚。
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q2. 步驟導覽：自由點步驟，還是只能「上一步／下一步」？

> FR6.1／US3.1／US4.2 要求無草稿也可**打開**掃描／Secrets 看空狀態，但執行仍 disabled。線框同時有左側步驟列與 footer「下一步：掃描」。需釘死避免實作成硬精靈。

A. **左側步驟可隨時點開**（自由檢視）；footer「下一步」僅為便利導覽（等同點下一步驟），**不**等於執行 D1／D2／D3。執行用各步獨立主按鈕（「執行生成／掃描／改寫」）。**（建議）** 對齊故事自由檢視。
B. **硬精靈**：未完成當步不可點後步；footer 下一步在成功後才啟用。代價：與 FR6.1「可檢視空狀態」衝突，除非後步仍可開但灰階——易混淆。
C. **步驟可點，但無草稿時後步以 modal 攔截並導回生成步**。代價：多一次打斷，與「可看空狀態」較遠。
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q3. D1／D2／D3「進行中」進度長什麼樣子？

> 故事要求進行中態＋不可重複送出（AC2.1.3／AC3.1.4／AC4.1.4）。Workspace 已有 `progress` 字串與 agent 訊息語彙。需決定 IaC 工作區要重用到什麼程度。

A. **Aside「Agent 狀態」區**顯示階段文字（如「正在產生模組…」），主區草稿可骨架／淡出；執行鈕進入 busy／disabled。對齊 A／C agent 語彙。**（建議）**
B. **主區全幅進度面板**蓋住草稿，完成後才還原。代價：進行中無法對照既有檔案樹。
C. **僅按鈕 spinner**，無 aside 文案。代價：較難對齊既有 Workspace agent 敘事，螢幕閱讀器宣告也較弱。
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q4. 有 HIGH／CRITICAL 時，下載前摘要確認用什麼元件？

> US5.1 要求先出摘要（計數或清單）、確認前不完成下載、取消則不下載。需選可做 focus trap／Esc 的形態，並與「無 apply」並列的下載主路徑相容。

A. **居中 modal dialog**（標題＋HIGH／CRITICAL 計數或短清單＋「仍要下載」／「取消」）；開啟時焦點落入 dialog，Esc／取消關閉且不觸發下載。**（建議）**
B. **右側 drawer** 滑出摘要。代價：與 aside 下載區重疊動線，窄窗較擠。
C. **下載鈕下方 inline 展開確認條**，無 modal。代價：焦點陷阱與「確認前不完成下載」較難保證。
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q5. 掃描 findings 與 Secrets 改寫清單的版面關係？

> Screen 3 線框把 findings 放右欄；Screen 4 改為主區警告＋清單。故事允許有 HIGH 仍進 Secrets（Advisory）。需釘死三步驟切換時草稿／findings／改寫清單誰佔主區。

A. **固定殼**：左步驟｜中草稿檔案樹＋預覽（各步皆可見，掃描／Secrets 時可唯讀）｜右欄依步驟切換（生成：脈絡／Agent／下載；掃描：findings；Secrets：改寫清單＋警告）。**（建議）** 最少改線框、草稿始終可對照。
B. **Secrets 步改為主區全寬清單**，草稿縮成可摺疊底欄。代價：兩套佈局，實作與 a11y landmark 較複雜。
C. **掃描與 Secrets 共用右欄「安全面板」**（上方 findings、下方改寫），生成步右欄仍為脈絡。代價：右欄很長，需內捲。
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q6. 視覺與響應式契約（對齊 A／C）？

> 產品已有 Tailwind brand token、Workspace／Cost 按鈕與表格語彙。NFR5 對比閾值本 stage 需寫進 checklist。IaC 頁不要另創品牌色。

A. **完全沿用既有 Tailwind／按鈕／空狀態／危險色 token**；IaC 只加步驟列與檔案樹預覽密度。桌面優先；窄窗步驟列改頂部橫向捲動，主／aside 改上下堆疊。對比採 WCAG 2.1 AA（正文 4.5:1、大字 3:1）。**（建議）**
B. **IaC 工作區用更深的「程式碼預覽」主題**（深色 HCL 預覽區），其餘 chrome 仍用既有淺色殼。代價：兩套對比檢查。
C. **新開 IaC 視覺語言**（獨立色票／卡片儀表）。代價：與 A／C 不一致，超出本輪。
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Consolidated Summary Confirmation

1. **Q1=A** — 選圖／上傳在 aside 脈絡卡；無圖時 aside／主區阻擋＋回 Workspace CTA。
2. **Q2=A** — 左側步驟可隨時點開（自由檢視）；footer「下一步」僅導覽；執行用各步獨立主按鈕。
3. **Q3=A** — 進行中：aside Agent 狀態文案＋主區骨架／淡出；執行鈕 busy／disabled。
4. **Q4=A** — HIGH／CRITICAL 下載前用居中 modal（確認／取消；Esc 取消不下載）。
5. **Q5=A** — 固定殼：左步驟｜中草稿｜右欄依步驟切換（脈絡／findings／改寫清單）。
6. **Q6=A** — 沿用既有 Tailwind／控件；窄窗步驟橫向＋主／aside 堆疊；WCAG 2.1 AA 對比。

Does this all look correct before I generate the artifacts?

- Looks correct
- Request changes

[Answer]: Looks correct
