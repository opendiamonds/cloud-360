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


---

## Revision 1（2026-08-10，因 scope-definition Revision 2 而修訂）

**觸發來源**：scope-definition Revision 2 新增 Must 能力 **(f) 使用者清單分頁**（PU-6）。本站的 condition 為「有使用者可見 UI 就執行」，分頁在兩種佈局都需要控制項，屬實質適用。

**既有答案（Q1〜Q5a）一律不改寫，既有線框原樣保留。** 本次新增兩題。

### R1. 分頁控制的形式

A. **頁碼式** — **（建議，已採用）** 可直接跳回某一頁重新核對；總頁數讓稽核者判斷「掃過全部帳號」的進度與是否漏頁。代價：後端需回傳總筆數（多一次計數查詢）。
   > **理由的來源狀態（reviewer iteration 1 補正）**：本題的選型理由**屬本站的設計判斷，上游未就此表態**，不宣稱有上游依據。初版另有「知道總共幾頁＝知道帳號規模」一句，該推論在上游查無依據，已移除。
B. 上一頁／下一頁（游標式） — 代價：無法得知帳號總數、不能跳頁，對「掃過全部帳號」這個稽核動作不友善。
C. 載入更多（無限滾動） — 代價：無法回到特定位置、無法得知進度；且與既有的「載入態整塊替換整個表格」模式衝突。

[Answer]: A

### R2. 逾期帳號散落多頁時，是否提供跨頁的逾期資訊

A. **顯示全域逾期總數** — **（建議，已採用）** 在列表上方顯示「共 N 個帳號逾期未活動」的全域計數（不限本頁）。代價：後端多一次條件計數。
   > **理由已整段更正（reviewer iteration 1）**：初版寫「本 intent 的核心價值是『一眼看出哪些帳號已逾期』，分頁把它打了對折，全域計數是補償」。**該核心價值主張無來源且與上游不符** —— 上游記載的是**逐帳號**的稽核證據取得（`intent-statement.md`：「存取稽核對『帳號是否仍在使用』的查驗需求」）。分頁前能一次看完全部帳號，是「清單不分頁」這個技術現況的副作用，非產品需求。
   > **修正後的理由**：全域計數是**便利功能** —— 成本低，且「共有幾個帳號逾期」對帳號治理決策有參考價值。它**不是**核心價值損害的補償，因為那個損害不成立。
   > **iteration 3／5 再次更正（涵蓋選項 A 與 C 的本文）**：選項 A 本文的「在列表上方顯示」與選項 C 本文的「比全域計數更能回答」**皆已不成立** —— 全域計數定案為本輪不採用。**兩處原文一律不改寫**（比照本檔既有慣例：原文保留、以本區塊級 addendum 覆寫）。本題定案 A 的**呈現方式**已改變 —— 全域計數**不畫入線框**，僅記於 Assumptions（比照「稽核報表匯出」的未承諾處置先例）。理由：①iteration 2 的「畫進線框但標註候選」折衷在文件五處中漏了兩處未同步，傳播失敗即為該方案脆弱的證據；②與同等核可地位的「稽核報表匯出」處置不一致；③視覺位階的說服力大於文字標註。**原答案不改寫**，改的是它的呈現規格。
B. 不提供，只看本頁 — 代價：稽核者要回答「有幾個帳號逾期」必須翻完全部頁面。
C. 提供逾期優先排序 — **產品面評估（iteration 2 補上，原僅有程序面理由）**：排序確實是「逐一處理逾期帳號」最直接的解，且比全域計數更能回答「它們在哪」。**若稽核者真有逐一處理的需求，排序在產品上優於本題採用的 A**。**程序面**：「依最後活動時間排序」在 scope-definition Revision 2 剛被明確保留於 Won't Have，選此等於立刻推翻上一站定案。**兩者結論**：不在本站採用；若後續確認稽核者有逐一處理需求，正確路徑是回跳 scope-definition 重新審視該排除項，而非在本站繞道。

[Answer]: A

## Assumption Confirmation（Revision 1 重設）

> Revision 1 使 `wireframes.md` 新增兩條假設、`user-flow.md` 新增一條，依 `project.md` 的既有規則重設本關卡並重新取得人工確認。

> 以下三條為 `wireframes.md` 與 `user-flow.md` 的 `## Assumptions & Open Questions` 新增條目**逐字轉錄**（reviewer iteration 1 Minor：初版為改寫而非逐字）。

1. （`wireframes.md`）**分頁控制**的確切樣式、每頁筆數、鍵盤操作與網址狀態留 refined-mockups 定案；本站只確立它存在、形式為頁碼式。**全域逾期計數**曾於本站評估，因缺乏強理由支撐而**不建議本輪採用**，故不畫入線框、僅記於 Assumptions；若未來需要須另行提案並經 scope-definition 核可（處置比照「稽核報表匯出」的未承諾先例）
2. （`wireframes.md`）頁碼式分頁需要後端回傳總筆數，查詢成本在本站視為可接受，實際形式與成本評估留 application-design。（全域逾期計數的條件計數成本不再列入 —— 該項已不建議本輪採用）
3. （`user-flow.md`）分頁後，稽核者無法從清單本身得知「共有幾個帳號逾期」，也無法定位它們在哪 —— 全域計數已定案**不於本輪採用**（見 `wireframes.md` §全域逾期計數的處置），即使採用也只回答前者。完整解法需排序或篩選，而該兩項仍在 Won't Have —— 此限制如實記載，留待未來若有需求再另立項

A. Accept assumptions
B. Modify（請指明哪一條）

[Answer]: A. Accept assumptions（2026-08-10，Revision 1）

> **Revision 1 iteration 3 後重設**：上述第 1、2 條的內容已因 reviewer iteration 3 的定案而**實質改變**（全域逾期計數由「本站確立其存在」改為「不建議本輪採用、不畫入線框」），依 `project.md` 的既有規則需**重新取得人工確認**。
>
> [Answer]: A. Accept assumptions（2026-08-11，Revision 1 iteration 3 重確認）
>
> **iteration 4 措辭同步 —— 重設本關卡（iteration 5 更正）**：初版判定「不需重設」，**該判定不成立**。reviewer iteration 5 指出：2026-08-11 的既有確認是在第 3 條與第 1、2 條**互相矛盾**的狀態下完成的（第 1、2 條已改為「計數本輪不採用」，第 3 條仍寫「計數回答『有幾個』」）。iteration 4 修掉了該矛盾卻未重新確認，使「已確認集合」與 artifact 現況不一致 —— 正是 `project.md`（`cid:intent-capture:c12`）描述的失效情境。
>
> 我原本的判準是「operative 內容未變」，那個判準用錯了：**先前被確認的狀態本身就內部不一致**，拿它當比較基準沒有意義。
>
> 本關卡依規則重設，三條假設以現況重新確認：
>
> 1. （`wireframes.md`）**分頁控制**的樣式、每頁筆數、鍵盤操作與網址狀態留 refined-mockups；本站只確立它存在、形式為頁碼式。**全域逾期計數**因缺乏強理由支撐而**不建議本輪採用**，不畫入線框、僅記於 Assumptions；若未來需要須另行提案並經 scope-definition 核可
> 2. （`wireframes.md`）頁碼式分頁需後端回傳總筆數，成本本站視為可接受，實際形式與評估留 application-design
> 3. （`user-flow.md`）分頁後稽核者無法從清單本身得知「共有幾個帳號逾期」，也無法定位它們在哪；全域計數已定案本輪不採用，即使採用也只回答前者。完整解法需排序或篩選，該兩項仍在 Won't Have
>
> [Answer]: A. Accept assumptions（2026-08-11，Revision 1 iteration 5 重確認 —— 依使用者授權以建議選項作答）