 [Answer]: A
[Answer]: A
[Answer]: B
[Answer]: B
[Answer]: B

# Rough Mockups — 釐清問題

> Stage: rough-mockups（Ideation 1.6）· Depth: Standard · Scope: feature
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。
> 上游輸入：`../intent-capture/intent-statement.md`（intent-statement）、`../scope-definition/scope-document.md`（scope-document）、`../scope-definition/intent-backlog.md`（intent-backlog）。
> 已由上游定案、本階段**不重問**：欄位語意為「最後活動時間」；空值顯示「無紀錄」且不套逾期標示；不做排序／篩選；4 個管理類角色可見。

## Sources

- [code:C7] `frontend/src/pages/AdminPage.tsx:167-263` — 既有使用者管理頁為單一 `<table>`，現有 5 欄依序：`使用者`／`授權狀態`／`角色`／`操作`／`啟用`；容器可水平捲動、表頭 sticky。（查證用於出題，不入 artifact 設計層）
- [intent:Q3] 成功指標含「超過 N 天未活動的帳號帶視覺標示」。
- [feas:Q2] 空值顯示「無紀錄」，不套用逾期標示。
- [scope:PU-2/PU-3] 顯示欄位與逾期標示為兩個 Must proto-unit，標示疊加在顯示之上。

## Q1. 新欄位在表格中的位置？

> 既有欄序：`使用者`／`授權狀態`／`角色`／`操作`／`啟用` [code:C7]。位置影響掃讀動線（F-pattern：越左越常被讀）。

A. 插在「角色」之後、「操作」之前 — 資訊欄（身分→狀態→活動）集中在左，操作欄維持在右。
B. 插在「授權狀態」之後 — 帳號狀態類資訊相鄰。
C. 加在最右（「啟用」之後）— 不動既有欄序，風險最低。
D. Not yet defined — 留給 refined-mockups 決定。
X. Other (please specify)

## Q2. 時間值的顯示格式？

> 稽核場景需要可比對的精確值 [intent:Q3]，日常掃讀偏好相對時間（「3 天前」）。

A. 絕對時間 — 固定格式（如 `2026-08-03 14:52`），稽核可直接抄錄比對。
B. 相對時間 — 「3 天前」「2 小時前」，掃讀快但不可直接比對。
C. 相對時間為主、hover／輔助文字顯示絕對時間 — 兼顧掃讀與稽核，成本略高。
D. Not yet defined
X. Other (please specify)

## Q3. 逾期未活動的視覺標示形式？

> WCAG：不得只靠顏色傳達意義（需圖示、文字或紋理輔助）。空值「無紀錄」不套標示 [feas:Q2]。

A. 文字 badge — 時間值旁加「逾期」字樣標籤（底色＋文字，非僅顏色）。
B. 圖示＋顏色 — 警示圖示（如 ⚠）加時間值變色。
C. 整列淡化或標記 — 整列視覺弱化或列首加標記，掃讀時整列可辨。
D. Not yet defined
X. Other (please specify)

## Q4. 「無紀錄」空值的呈現？

> 空值語意是「上線前無資料」[feas:Q2]，要與「有值但逾期」在視覺上明確區隔。

A. 灰字「無紀錄」 — 文字明示，弱化處理，與逾期標示明顯不同。
B. 破折號「—」加 hover 說明 — 最簡潔，語意藏在 hover。
C. 灰字「無紀錄」＋輔助說明（tooltip：「本功能上線前無活動資料」）。
D. Not yet defined
X. Other (please specify)

## Q4a. 追問：Q4=B 的 hover 說明在 WCAG AA 下的可及性？

> hover-only 的 tooltip 對鍵盤與觸控使用者不可及；Q5 選了 WCAG AA，說明文字需可聚焦或以其他可及方式提供。

A. tooltip 需鍵盤可達 — 破折號可聚焦（focusable），聚焦時顯示說明；wireframe 據此註記。
B. 改用 aria-label — 視覺僅破折號，語意由 screen reader 讀出；一般使用者 hover 才見說明。
C. 回到灰字「無紀錄」（Q4 改 A）— 文字明示最可及，放棄極簡。
D. Not yet defined
X. Other (please specify)

[Answer][Answer]: A. tooltip 需鍵盤可達（guided 補答，2026-08-04）

## Q5. 無障礙與裝置支援的底線？

> 管理介面目前為桌面操作為主，表格已支援水平捲動 [code:C7]。本題定錨驗收底線，避免 refined-mockups 時回頭補。

A. WCAG 2.1 AA＋桌面優先 — 對比 4.5:1、鍵盤可達、screen reader 可讀；行動裝置靠既有水平捲動，不另做響應式改造。
B. WCAG 2.1 AA＋行動響應式 — 另含小螢幕卡片式改造（成本明顯擴大，動到既有表格架構）。
C. 僅基本可用 — 不設無障礙驗收底線（不建議：與平台品質基線不符）。
D. Not yet defined
X. Other (please specify)

## Q5a. 矛盾解消：Q5=B 的行動響應式改造超出已核可的 scope 邊界

> **偵測到的範圍張力**（stage-protocol.md §3 強制檢查）：
>
> | 來源                     | 內容                                                                                             |
> | ------------------------ | ------------------------------------------------------------------------------------------------ |
> | scope-document（已核可） | In scope 為四項 Must：記錄／顯示欄位／逾期標示／權限開通；「顯示」的內涵是在既有管理頁表格加一欄 |
> | Q5=B                     | 「小螢幕卡片式改造」需重構整個使用者管理頁的行動版佈局，動到既有表格架構                         |
>
> 卡片式改造既不在四項 Must 內、也不在 Won't Have 清單。需定錨其去向，否則 refined-mockups 與後續估算的範圍不可判。

A. 縮回本 feature 邊界 — Q5 改為 A（AA＋桌面優先）；行動響應式改造記為「未承諾」，未來另立 intent。
B. 擴充 scope — 行動響應式改造納入本 feature 為第五項能力；scope-document／intent-backlog 需修訂並重新核可（成本與時程明顯擴大）。
C. 折衷 — 僅要求**新欄位**在小螢幕的可讀性（欄位不被裁切、標示可見），不改造整表佈局；AA 底線全裝置適用。
D. Not yet defined
X. Other (please specify)

[Answer][Answer]: B. 擴充 scope（guided 釐清，2026-08-04）— 行動響應式改造納入本 feature，scope-definition 需回頭修訂並重新核可

## Assumption Confirmation

> 兩份 artifact 的 `## Assumptions & Open Questions` 皆非 `None.`，依 learned rule 需人工確認。
> **接受不等於把 assumption 變成事實** —— `[assumption]` 標籤會原樣保留在 artifact 中。

**`wireframes.md`**

- [assumption] 逾期門檻 N 未定，線框中逾期態以「N 天」佔位表達；N 於 requirements-analysis 定案後不影響版面結構 [intent:Q3]
- [assumption] 載入與錯誤態沿用既有頁面模式，本階段不重新設計；若既有頁面無 skeleton 慣例，於 refined-mockups 對齊（註：本條的 [Q5] 引用經 reviewer Finding 5 指認為不對應，refined-mockups 修訂時移除）
- [assumption] 卡片式佈局的響應式斷點值未定，以既有內容破版處為準，refined-mockups 定值 [Q5] [Q5a]

**`user-flow.md`**

- [assumption] `Security_Reviewer` 的稽核操作僅為「讀取＋人工抄錄」；系統不提供匯出（scope-document 列為未承諾）
- [assumption] （開放問題）逾期帳號的後續處置（停用等）沿用既有操作，本 feature 不設計新流程；若稽核實務需要批次處置，屬未來另立 intent

A. Accept assumptions — 保留 [assumption] 標籤，帶著這 5 項進入 approval gate
B. Convert to follow-up questions — 補題釐清後再修訂 artifact

[Answer][Answer]: A. Accept assumptions（2026-08-04）
