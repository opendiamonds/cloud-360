# Requirements Analysis — 釐清問題

> Stage: requirements-analysis（Inception 2.3）· Depth: Standard · Scope: feature
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。
> **成本揭露**：本題組共 5 題，其中 Q1、Q2 是 ideation 明列的**上線前置**（不定案則 Must 集合不可完整交付）。Q4、Q5 若選擇納入會擴大範圍，需回跳 scope-definition 修訂重審 —— 各選項已標明。
> **每題均附建議選項**，建議理由與代價寫在選項描述內。
> **已由上游定案、不重問**：欄位語意為「最後活動時間」；空值**不套逾期標示**，其呈現形式依 rough-mockups 的已核可決策為**可聚焦的破折號 `—` ＋聚焦／hover 說明**（`[rm:Q4]=B`、`[rm:Q4a]=A`；feasibility 階段較早的「顯示無紀錄」措辭已被此更具體的決策取代，見下方修訂註）；時間格式為絕對時間 `YYYY-MM-DD HH:MM`；逾期標示為 `(!)` 圖示＋變色；4 個管理類角色可見；不做排序／篩選；WCAG 2.1 AA 全裝置；小螢幕卡片式佈局；三項測試底線（授權矩陣雙向測試／端點 `TestClient` 測試／前端 e2e 斷言）。
>
> **修訂註（2026-08-09，reviewer iteration 1 Finding 1）**：本前言初版誤將空值呈現寫為「顯示『無紀錄』」並標 `[feas:Q2]`。該措辭出自 feasibility 階段，其後已由 rough-mockups 的具體視覺決策（破折號＋可聚焦說明）取代並經 gate 核可。依 `team.md` correction（下游已確認的具體決定向下游傳遞，不被更早更籠統的措辭覆蓋）修正如上。此修訂**不改變任何一題的答案**，僅更正不重問清單的事實陳述。

## Sources

- [intent] `../../ideation/intent-capture/intent-statement.md` — 稽核目的與成功指標
- [scope] `../../ideation/scope-definition/scope-document.md`（Revision 1）— 五項 Must 能力
- [raid] `../../ideation/feasibility/raid-log.md` — R1 寫入頻率、A2 保存上限、D2 定案依賴
- [pd] `../practices-discovery/evidence.md` — 三方盲審查得的既有實作事實
- [kb] `aidlc/spaces/default/codekb/cloud-360/` — code-structure、architecture、business-overview
- [tp] `../practices-discovery/team-practices.md` — 本輪生效的測試底線

---

## Q1. 逾期門檻 N：超過幾天未活動要標示？

> 這是 ideation 全程懸置的**上線前置**（raid-log A1／D2、scope-document assumption）。成功指標「未活動超過門檻的帳號帶視覺標示」在 N 定案前不可完整驗證。
>
> 參考脈絡：本平台為內部工具，認證憑證效期 8 小時、無更新機制 [kb]。使用者為專案內的管理與工程角色，非大眾用戶。

A. **90 天** — 季度稽核節奏的自然對應；對內部工具而言，一季沒有任何活動足以構成「帳號可能該停用」的訊號。**（建議）** 代價：短期離開（如長假、輪調）的帳號不會被標示，需要更敏感的偵測時要改值。
B. **30 天** — 較敏感，一個月無活動即標示。適合帳號流動快的團隊。代價：長假或專案空窗期會產生較多誤報，標示的訊號價值下降。
C. **180 天** — 保守，半年才標示。誤報極少。代價：稽核價值降低，一個帳號可能閒置近半年才被看見。
D. **其他天數** — 請於 X 指明。
X. Other (please specify)

[Answer]: A. 90 天（採納建議：對應季度稽核節奏；內部工具一季無活動足以構成帳號可能該停用的訊號）

---

## Q2. 活動資料的保存上限與清除語意

> feasibility [Q4] 確認「活動資料有保存上限，但值未定」，且 raid-log A2 指出：在**單一欄位覆寫**的模式下（只留最後一次，不留歷史），「保存上限」的實際含意本身就需要釐清 —— 因為沒有歷史資料可以過期刪除。
>
> 換句話說：這個欄位只有一個值，它會被每次活動覆寫。所謂「保存上限」實際上只可能是「帳號停用或刪除後，該值何時清除」。

A. **無獨立保存規則，隨帳號生命週期** — 值隨 `users` 記錄存在而存在，帳號被刪除時一併消失（外鍵層級的自然結果）。單一欄位覆寫模式下這是最一致的語意，不需額外機制。**（建議）** 代價：若未來擴充為歷史紀錄，需重新定義保存政策（但那本來就是另一個 intent）。
B. **帳號停用後保留固定期間再清空** — 例如停用 N 天後把該欄位設為 NULL。代價：需要排程機制（本專案目前沒有背景 worker 或排程器），成本明顯高於本 feature 的其餘部分。
C. **明確宣告不適用** — 在 requirements 中記載「單一欄位覆寫模式下，保存上限概念不適用」，並註明擴充為歷史紀錄時需重新評估。與 A 實質相同但表述更明確。
D. Not yet defined — 留待後續階段（不建議：這是 ideation 指定在本階段定案的項目）。
X. Other (please specify)

[Answer]: A. 無獨立保存規則，隨帳號生命週期（採納建議：單一欄位覆寫模式下無歷史可過期；B 需排程機制而本專案無背景 worker）

---

## Q3. 寫入頻率的緩解手段：本階段定約束，還是留給設計階段選手段？

> raid-log R1：「任何有效活動都記錄」意味每個帶憑證的請求都可能觸發一次資料庫寫入。ideation 已記載風險與緩解方向（節流／彙整／非同步），並依 correction 明訂「**選定緩解手段**列為設計階段的必答項」。
>
> 本階段的問題不是「選哪個手段」（那是 application-design 的事），而是「requirements 要不要給出可驗證的約束」讓設計階段有標準可依。

A. **定出可驗證的約束，不指定手段** — 例如「同一帳號的活動時間更新，寫入頻率不得高於每 N 分鐘一次」；設計階段自由選擇節流／彙整／非同步等手段達成。**（建議）** 這符合 requirements 應「可測試」的原則（inception 護欄），也不侵犯設計階段的決定權。若選此項，請於 X 或答案後註明你認為合適的節流間隔（建議 5 分鐘：對「最後活動」的稽核語意而言，5 分鐘的精度綽綽有餘）。
B. **不定約束，完全留給設計階段** — requirements 只記載風險存在。代價：設計階段沒有驗收標準，「夠不夠快／夠不夠省」變成主觀判斷。
C. **本階段直接指定手段** — 例如明訂用節流。代價：違反 ideation 的既定分工（correction 明訂手段選擇屬設計階段），且在缺乏設計分析的情況下過早收斂。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 定出可驗證的約束，不指定手段 —— 節流間隔採 5 分鐘（採納建議：需求須可測試，且手段選擇留設計階段）

---

## Q4. 既有 bug：`UserSchema` 兩個構造點漏傳欄位 —— 本 intent 要不要一併修？

> practices-discovery 的 developer 盲審查得 [pd]：`UserSchema` 在 `user_router.py` 有三個具名構造點，其中 `update_user_active`（L602）與 `update_user_role`（L705）**現在就在靜默漏傳 `requested_role`**。
>
> **對本 intent 的直接影響**：新增的「最後活動時間」欄位若比照現有寫法，使用者在 Admin 頁改完角色或啟停用之後，該列的時間欄會**變成空白**（因為回傳的物件少了那個欄位），而且沒有任何現有工具會報錯 —— e2e 未斷言表格內容、`tsc -b` 因 `DbUser` 是手寫 interface 而無效。
>
> 這是既有缺陷，不在已核可的五項 Must 內。

A. **新欄位確保三個構造點都傳，但不修既有的 `requested_role` 漏傳** — 只保證本 intent 的欄位正確，既有 bug 另立項。**（建議）** 範圍最小、不觸發 scope 修訂，且本 intent 的交付物正確。代價：`requested_role` 的既有 bug 繼續存在（但它本來就存在，本 intent 不使其惡化）。
B. **順手把既有 `requested_role` 漏傳一併修掉** — 三個構造點全面收斂（例如抽共用 helper）。好處：根治。代價：屬 scope 擴充（修既有缺陷不在五項 Must 內），依協定需回跳 scope-definition 修訂重審並重走 approval gate。
C. **都不處理，新欄位比照現有寫法** — 不建議：會產生使用者可見的錯誤行為，且違反本輪新增的測試底線（端點變更需 `TestClient` 測試會抓到）。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 新欄位確保三個構造點都傳，但不修既有的 requested_role 漏傳（採納建議：範圍最小、不觸發 scope 修訂）

---

## Q5. 稽核軌跡易失性：權限變更紀錄實際保存期約等於兩次部署間隔

> devsecops 盲審查得 [pd]：權限變更的稽核記錄 `_audit_append()` 實作為 `logger.info`，而每次部署會重建容器並移除舊日誌 —— **稽核軌跡的實際保存期約等於兩次部署間隔**。
>
> 這對一個以「提供稽核能力」為價值主張的 intent 構成語意張力：我們正在為稽核者新增帳號活動證據，但系統本身的權限變更軌跡是易失的。
>
> 本 intent 的 PU-4 會變更權限矩陣（開通 `Security_Reviewer`），因此會產生一筆這樣的易失記錄。

A. **記載為已知限制，不在本 intent 處理** — 寫進 requirements 的 Constraints／Open Questions 並向下游傳遞，修復另立 intent。**（建議）** 稽核軌跡持久化是獨立的維運能力（涉及儲存選型、保存政策、查詢介面），與「加一個欄位」的範圍不成比例。代價：該限制繼續存在。
B. **納入本 intent，一併處理** — 把權限變更軌跡持久化納入範圍。代價：屬明顯的 scope 擴充（新增儲存與保存政策決策），需回跳 scope-definition 修訂重審；成本可能超過本 feature 其餘四項能力的總和。
C. **折衷：只要求本次權限變更留下持久證據** — 例如把這次的 `Security_Reviewer` 開通決定記入 `decisions-log.md` 或 ADR，不建系統性機制。範圍極小，但只解決這一次。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 記載為已知限制，不在本 intent 處理（採納建議：稽核軌跡持久化屬獨立維運能力，與加一欄的範圍不成比例）

---

## Consolidated Summary Confirmation

> 產生 `requirements.md` 前的強制確認關卡（stage-protocol.md Step 10）。以下是五題答案的合併總結：

| # | 決定 | 對需求的直接影響 |
| --- | --- | --- |
| Q1 | **逾期門檻 N = 90 天** | 成功指標自此可完整驗證；`N` 不再是 assumption，而是具體驗收值。超過 90 天無活動的帳號帶 `(!)` 標示 |
| Q2 | **無獨立保存規則，隨帳號生命週期** | 不需排程機制；值隨 `users` 記錄存廢。擴充為歷史紀錄時需重新評估保存政策 |
| Q3 | **定可驗證約束、不指定手段；節流間隔 5 分鐘** | 需求寫「同一帳號的活動時間更新頻率不高於每 5 分鐘一次」；節流／彙整／非同步的選擇留 application-design |
| Q4 | **新欄位確保三個構造點都傳，不修既有 `requested_role` 漏傳** | 本 intent 交付物正確；既有 bug 不惡化亦不修復，另立項 |
| Q5 | **稽核軌跡易失性記為已知限制** | 寫入 Constraints／Open Questions 向下游傳遞，不納入本 intent |

**範圍影響**：五項答案**皆不擴大已核可範圍**，不觸發回跳 scope-definition 修訂。

Does this all look correct before I generate the requirements artifact?

A. Looks correct — 依此產生 `requirements.md`
B. Request changes — 修改一或多項答案後再產生

[Answer]: A. Looks correct（2026-08-09）

---

# Revision 1（2026-08-11）— PU-6 使用者清單分頁

> **觸發來源**：`scope-document.md` **Revision 2** 新增 Must 能力 **(f) 使用者清單分頁**（PU-6）。本站以 Modify 模式疊加修訂：Q1〜Q5 的題幹、選項與答案**一律不動**，既有的 FR-1〜FR-5、NFR-1〜NFR-7、C-1〜C-8 亦不改寫；本節只補上分頁在**需求層**需要定案的行為契約。
>
> **已由上游定案、本節不重問**：
> - **分頁形式為頁碼式** —— `rough-mockups` Revision 1 已定案並經 gate 核可（見 `approval-handoff/initiative-brief.md` 的 assumption：「PU-6 的分頁形式（頁碼式已定…）」）。
> - **每頁筆數與回應 envelope 形式** —— `scope-document.md` Revision 2 的 assumption 明訂「屬設計決定，留 application-design 定案」。依 `project.md ## Corrections`（Must 能力含未定參數時不降級該能力，把「參數於指定階段定案」升格為上線前置依賴），本站**不越權代決**，改把它列為上線前置依賴（見 requirements 的開放問題 OQ-6）。
> - **不做互動排序／篩選** —— `scope-document.md` Revision 2 明確保留此排除；分頁是本次唯一新增的清單互動。
> - **不做全域逾期計數** —— `rough-mockups` Revision 1 評估後判定本輪不採用，狀態為「未承諾」。
> - **分頁控制的視覺與版位** —— 屬 `refined-mockups` 的既定職掌。
>
> **本節新增 2 題**，皆為**可觀察的行為契約**（what），非實作手段（how）：頁面內操作後的頁次行為、以及頁次超出範圍時的行為。兩者若不在需求層定案，Construction 會各自臆測，且都是使用者可見的錯誤面。**每題均附建議選項。**

## Sources（Revision 1 追加）

- [scope:r2] `../../ideation/scope-definition/scope-document.md` Revision 2 — Must 能力 (f) 與其兩條 assumption
- [ah:r1] `../../ideation/approval-handoff/initiative-brief.md` Revision 1 — 頁碼式已定、GO 不變
- [tp:cs] `../practices-discovery/team-practices.md` `## Code Style` — `AdminPage.tsx` 既有的資料抓取／狀態更新拆分形狀與 `react-hooks/immutability`

---

## Q6. 頁面內操作（角色調整／啟停用）之後，清單停在原本的頁次還是回到第 1 頁？

> ~~既有實作在這兩個操作成功後**不重抓清單**，而是以 `setUsers((prev) => prev.map(...))` 就地更新該列 [tp:cs]。~~ **（更正見下方 Revision 註 R1 —— 此前提對「啟停用」不成立，且 `[tp:cs]` 為誤引）**
>
> **更正後的既有行為** [impl]：**角色調整**（`AdminPage.tsx:89`）成功後以 `setUsers((prev) => prev.map(...))` 就地更新，不重抓；**啟停用**（`AdminPage.tsx:113`）與**刪除**（`AdminPage.tsx:129`）成功後皆呼叫 `fetchUsers()` **整份重抓清單**。三者並不一致。
>
> 導入分頁後，「就地更新」與「重抓當前頁」是兩種不同的行為，且結果對使用者可見。
>
> 這是需求層的問題，不是實作問題：稽核者在第 3 頁停用一個帳號後，被丟回第 1 頁會直接損害逐帳號查驗的工作流。

A. **維持目前頁次，就地更新該列** —— 操作成功後不改變頁次，只更新該列的呈現。**（建議）** ~~與既有行為一致（既有實作本來就是就地更新）、改動最小~~ **（更正見 R1：此理由只對「角色調整」成立；「啟停用」與「刪除」的既有路徑是整份重抓，選 A 對這兩者是行為變更，需實際修改）**，且保住逐帳號查驗的工作流。代價：若該操作理論上會改變該帳號在清單中的位置，就地更新會與重抓的結果不同 —— 但本清單無互動排序／篩選（Won't Have），排序準則固定，操作不改變位置，此代價在本 intent 不成立。
B. **維持目前頁次，但重抓當前頁** —— 操作後以相同頁次重新請求。好處：資料一定與後端一致。代價：多一次往返；且需處理「重抓後該頁變空」（例如他人同時刪除帳號）的邊界，複雜度高於本 feature 其餘部分。
C. **回到第 1 頁** —— 不建議：直接損害稽核者的逐帳號查驗工作流，且無任何補償價值。
D. Not yet defined —— 不建議：Construction 會臆測，且是使用者可見的錯誤面。
X. Other (please specify)

[Answer]: A. 維持目前頁次，就地更新該列（採納建議：保住逐帳號查驗的工作流；本清單無互動排序／篩選故位置不變）

> **R1 更正（2026-08-11，reviewer Revision 1 Finding 1｜Critical）** —— **答案不變，只更正理由。**
>
> 本題前言與選項 A 原本宣稱「既有實作在角色調整與啟停用兩個操作後皆不重抓清單」，並以此支撐「與既有行為一致、改動最小」。回 repo 逐行核對後此前提**對啟停用不成立**：`AdminPage.tsx:113` 的 `handleToggleActive` 成功後呼叫 `fetchUsers()`，是整份重抓；`AdminPage.tsx:129` 的 `handleDelete` 亦同。只有 `AdminPage.tsx:89` 的 `handleRoleChange` 是就地更新。
>
> 另：原引用的 `[tp:cs]`（`team-practices.md ## Code Style`）**不支持**「是否重抓清單」這個主張 —— 該段只規範抓取／狀態更新的三層拆分與 `react-hooks/immutability`，未涉及操作後的重抓策略。已改標 `[impl]`（本站對 repo 的直接實測，附行號）。
>
> **對決定的影響：無。** 三個選項的比較在更正後的事實下結論不變（A 仍是唯一保住逐帳號查驗工作流的選項，B 需處理重抓後空頁的邊界，C 直接損害工作流）。**對實作的影響：有，且重要** —— 選 A 對啟停用與刪除是**行為變更**，必須實際修改那兩條路徑，不可默認「沿用既有形狀」。此影響已寫入 `requirements.md` 的 C-10 與 FR-6 的「跨層影響」段。
>
> 處置依 `project.md ## Corrections`：「下游查證推翻的是選項的理由而非決定本身時，只修理由不改決定 —— 以 Revision 段記錄落差的來源與拆解，原答案與選項本文均不改寫，並在不成立的句子就地標註」。

---

## Q7. 請求的頁次超出實際範圍時（例如總共 2 頁卻請求第 5 頁），系統的行為是什麼？

> 這條路徑真的到得了：使用者手動改網址、書籤舊頁次、或在最後一頁時其他管理者刪除了帳號。不定義則後端與前端各自臆測，可能出現 500 或空白畫面。

A. **回傳空的資料清單，並照常附上分頁資訊（總筆數／總頁數／目前頁次）；前端顯示「沒有資料」並提供回到第 1 頁的方式** —— **（建議）** 以 200 表達「查詢合法但該頁無資料」，語意正確、前端只需一條空態分支，且分頁資訊仍在，使用者知道自己在哪。代價：需要一個空態的呈現（refined-mockups 定案文案與版位）。
B. **後端回 4xx 錯誤** —— 好處：明確拒絕不合法輸入。代價：一個超出範圍的頁次不是「不合法輸入」而是「合法查詢、結果為空」；用錯誤碼表達會讓前端把它當失敗處理，顯示錯誤訊息而非空態，對使用者是誤導。
C. **自動夾到最後一頁** —— 好處：使用者永遠看得到資料。代價：回應的「目前頁次」與請求不符，型別契約與前端狀態容易不同步；且掩蓋了書籤失效這件事。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 回傳空清單並照常附分頁資訊，前端顯示空態並可回到第 1 頁（採納建議：200 + 空清單語意正確，前端只需一條空態分支）

> **R2 補充（2026-08-11，reviewer Revision 1 Findings 2、4）** —— **答案不變，補足兩個原本留白的可測項。**
>
> 1. **「目前頁次」在此情境下的值**：**回顯請求值，不夾到最後一頁**（總共 2 頁時請求第 5 頁，回應的目前頁次為 5）。原選項只寫到「照常附分頁資訊」，未定義這個值，前端的「回到第 1 頁」實作方式會因此不同；本補充使該欄位在邊界情境下也可測。
> 2. **與 NFR-8 的分界**：本題處理的是**合法但超出範圍**的頁次（查詢合法、結果為空）；**型別或範圍非法**的參數（頁次或每頁筆數為非數值、負數、零，或每頁筆數過大）屬 NFR-8 的邊界驗證，**兩者是不同判定，不可互相取代**。reviewer 指出原 NFR-8 的文字說「分頁查詢參數」（複數）但驗收標準只列每頁筆數，頁次的非法值無任何條目涵蓋 —— 已於 `requirements.md` NFR-8 補齊頁次的驗證項。

---

## Consolidated Summary Confirmation — Revision 1

> 產生 `requirements.md` Revision 1 前的強制確認關卡。以下是本節兩題答案的合併總結：

| # | 決定 | 對需求的直接影響 |
| --- | --- | --- |
| Q6 | **維持目前頁次** | 新增 FR-6.5：角色調整／啟停用／刪除成功後頁次不變。**對啟停用與刪除是行為變更**（既有為整份重抓），見 R1 |
| Q7 | **超出範圍的頁次回傳空清單 + 完整分頁資訊，目前頁次回顯請求值** | 新增 FR-6.4：以 200 表達「合法查詢、該頁無資料」；目前頁次回顯請求值不夾頁；前端空態可回第 1 頁。見 R2 |
| R2-2 | **NFR-8 涵蓋頁次與每頁筆數兩個參數** | NFR-8 的驗收標準補齊頁次的型別／範圍驗證；與 FR-6.4 的「合法但超出範圍」明確分界 |

**範圍影響**：兩項答案**皆不擴大** `scope-document.md` Revision 2 已核可的範圍 —— 兩者都是 (f) 分頁能力自身的行為面，不新增能力、不解除任何排除項。不觸發回跳 scope-definition。

**未於本站定案、升格為上線前置依賴**：每頁筆數與回應 envelope 形式（application-design 定案，見 OQ-6）。

**新增假設的確認**（依 `project.md ## Corrections`，artifact 的 Assumptions 有增刪須同步 reset 本關卡並重新取得確認）。Revision 1 於 `requirements.md` 新增三條假設：

1. FR-6.5 的「就地更新不會與重抓結果不同」成立於「清單無互動排序／篩選、排序準則固定」這個前提。
2. FR-6.4 選擇 200＋空清單，前提是「超出範圍」屬合法查詢而非不合法輸入。
3. **（本站綜合判斷，非逐字承自 Q7 選項原文）** FR-6.4 與 NFR-8 是兩個不同判定，不可互相取代 —— 見 R2 第 2 點。

Does this all look correct before I revise the requirements artifact?

A. Looks correct — 依此修訂 `requirements.md`
B. Request changes — 修改一或多項答案後再產生

[Answer]: A. Looks correct（2026-08-11；**Revision 1 更正輪後重新確認**，涵蓋 R1、R2 與上列三條新增假設）
