# Rough Mockups — 釐清問題

> Stage: rough-mockups（Ideation 1.6）· Depth: Standard · Scope: mvp
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。
> 上游輸入：`../intent-capture/intent-statement.md`、`../scope-definition/scope-document.md`、`../scope-definition/intent-backlog.md`。

## 已由上游定案、不重問

- 要圓餅拆解與總額、時數可覆寫 [intent:Q3]
- Sidebar 大類 C；產圖後 CTA「查看預估成本」[intent:Q13] [memory:M5]
- 超支時成本畫面要有視覺標示；進產品橫幅在超支期間每次都出現、無 inbox [intent:Q16] [feas:Q6]
- 未定價列名且不計入總額 [feas:Q7]
- 第一段可單獨上線（尚無預算區塊）；第二段才有每圖預算 [scope:Q1]
- 線框圖示用基本 ASCII，不用 emoji [project.md Corrections]

## Sources

- [code:S1] `frontend/src/components/Sidebar.tsx:17-22,120-154` — 側欄分組「架構」「Admin」；架構下有「架構圖生成」「Assessment」。
- [code:S2] `frontend/src/pages/WorkspacePage.tsx:931-976` — 產圖成功為中央大張成功卡，CTA 現有「繼續對話編輯」「生成 IaC 代碼」「Well-Architected」。
- [intent:Q13] Sidebar C＋產圖後 CTA「查看預估成本」
- [intent:Q16] 成本畫面視覺標示（變色或橫幅）＋進產品通知
- [feas:Q6] 超支期間每次進入產品都看到橫幅
- [scope:Q1] 兩段增量；第一段可無預算上線

## Q1. 成本畫面的資訊層級（由上到下）？

> 第一段必須同時看到總額、圓餅、資源列、時數。層級決定掃讀順序。

A. 總額置頂 → 圓餅 → 資源列（含未定價）→ 時數在列上或列底可改。
B. 圓餅與總額並排置頂 → 其下資源列；時數在每列。
C. 資源列為主（對到圖上元件）→ 總額與圓餅在側欄或底部摘要。
D. Not yet defined — 留給 refined-mockups。
X. Other (please specify)

[Answer]: A. 總額置頂 → 圓餅 → 資源列（含未定價）→ 時數在列上或列底可改。

## Q2. 「查看預估成本」CTA 放在產圖成功流程的哪裡？

> 查證：產圖成功已有中央成功卡，上面已有繼續編輯、生成 IaC、Well-Architected [code:S2]。intent 要產圖後 CTA，沒說是否併入這張卡。

A. 加進既有成功卡 — 與 IaC／Well-Architected 並列第三個主按鈕（或取代較弱的一顆），沿用既有成功態。
B. 成功卡以外另開一條 — 例如畫布工具列或儲存後提示，不擠進現有三顆按鈕。
C. 兩處都有 — 成功卡一顆，Sidebar C 隨時可進；成功卡是捷徑。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 加進既有成功卡 — 與 IaC／Well-Architected 並列第三個主按鈕（或取代較弱的一顆），沿用既有成功態。

## Q3. 成本畫面上的超支視覺標示要長什麼樣子？

> 進產品橫幅已定 [feas:Q6]。本題只定**成本畫面本身**（intent 寫「總額變色或橫幅」[intent:Q16]）。WCAG：不得只靠顏色。

A. 總額旁文字標籤「已超支」＋總額變色（文字＋顏色，非只靠顏色）。
B. 成本畫面頂部橫幅「本圖已超過每月預算」，加上總額變色。
C. 只做 A，進產品橫幅已夠醒目，成本畫面不再加橫幅。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 總額旁文字標籤「已超支」＋總額變色（文字＋顏色，非只靠顏色）。

## Q4. 單價 Manual Override 與時數覆寫，在畫面上怎麼操作？

> 時數隨時可改；單價只在缺價／失敗時可改，且要標 Manual Override。未定價列必須看得見 [feas:Q7]。

A. 就地編輯 — 資源列上時數與（允許時）單價是可點的欄位；覆寫列顯示「Manual Override」文字。
B. 列上時數就地改；單價覆寫開一層小對話框，確認後列上標記。
C. 全部進「調整假設」面板，主畫面只讀。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 就地編輯 — 資源列上時數與（允許時）單價是可點的欄位；覆寫列顯示「Manual Override」文字。

## Q5. 無障礙與裝置底線？

> 現有產品以桌面為主（Workspace 雙欄、側欄）。新成本頁與橫幅必須可鍵盤到達。

A. WCAG 2.1 AA＋桌面優先 — 對比 4.5:1、鍵盤可達、screen reader 可讀；小螢幕靠捲動，不另做卡片佈局。
B. WCAG 2.1 AA＋小螢幕另做單欄堆疊（總額→圓餅→列表），成本明顯較高。
C. 僅基本可用 — 不設無障礙驗收底線（不建議）。
D. Not yet defined
X. Other (please specify)

[Answer]: A. WCAG 2.1 AA＋桌面優先 — 對比 4.5:1、鍵盤可達、screen reader 可讀；小螢幕靠捲動，不另做卡片佈局。

## Q6. 第二段的「每圖預算」放在成本畫面的哪裡？

> 第一段上線時這個區塊可以不在。第二段加上時，要讓 FinOps／工程主管設上限，且超支比對看得到。

A. 同一頁頂部，總額旁邊 — 「本圖每月預算」可編輯；第一段該位留空或隱藏。
B. 同一頁但收在「預算」一區，預設摺疊；第一段整區不渲染。
C. 獨立的預算設定，不跟估價主畫面混在一起。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 同一頁頂部，總額旁邊 — 「本圖每月預算」可編輯；第一段該位留空或隱藏。

## Consolidated Summary Confirmation

> 6 題已作答。矛盾檢查（§3）：無阻斷矛盾。Q3=A 與 Q6=A 都落在總額列，wireframe 把「已超支」標籤與預算欄放在總額同一列。Q2=A 可能讓成功卡按鈕變四顆，屬版面張力，線框時畫進成功卡再判定要並列還是取代較弱的一顆。
>
> 答案彙整：Q1=A（總額→圓餅→資源列）、Q2=A（CTA 進既有成功卡）、Q3=A（已超支文字標籤＋總額變色）、Q4=A（就地編輯＋Manual Override 標記）、Q5=A（WCAG 2.1 AA＋桌面優先）、Q6=A（預算在總額旁；第一段隱藏）。

**Prompt**: Does this all look correct before I generate the artifacts?

A. Looks correct — 依這些答案產出 artifact
B. Request changes — 先修改一或多題答案

[Answer]: A. Looks correct — 依這些答案產出 artifact

## Assumption Confirmation

> 兩份 artifact 的 Assumptions 皆非 `None.`
> **接受不等於把 assumption 變成事實**。

**`wireframes.md`**

- [assumption] 成功卡畫成四顆按鈕，不預先刪 IaC 或 Well-Architected；若過擠由 refined-mockups 決定是否改排 [Q2]
- [assumption] 示意金額與資源名非正式報價
- [assumption] 橫幅出現的具體頁面仍留設計 [feas:Q6]

**`user-flow.md`**

- [assumption] 橫幅綁「使用者有權看到的超支圖」，多圖時如何堆疊留 refined-mockups
- [assumption] Flow 2 的不可編態細節留設計

A. Accept assumptions — 保留 [assumption] 標籤
B. Convert to follow-up questions — 補題後再修訂

[Answer]: A. Accept assumptions — 保留 [assumption] 標籤
