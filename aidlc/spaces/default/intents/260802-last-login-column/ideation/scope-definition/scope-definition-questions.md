# Scope Definition — 釐清問題

> Stage: scope-definition（Ideation 1.4）· Depth: Standard · Scope: feature
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。
> 上游輸入：`../intent-capture/intent-statement.md`（intent-statement）、`../feasibility/feasibility-assessment.md`（feasibility-assessment）、`../feasibility/constraint-register.md`（constraint-register）。
> 已由上游定案、本階段**不重問**：產品邊界為 `feature`［intent:Q8］；欄位語意為「最後活動時間」［feas:Q8］；空值顯示「無紀錄」［feas:Q2］；無時程阻塞［feas:Q5］；變更套用路徑［feas:Q3］。

## Sources

- [intent:Q3] 成功指標：介面顯示每帳號最後活動時間（可驗證）＋「超過 N 天未活動」視覺標示（N 未定，assumption）。
- [intent:Q9] 只留最後一次，資料模型預留歷史擴充路徑。
- [intent:Q10/Q12] 已決定開通 `Security_Reviewer` 檢視權限，4 個管理類角色可見。
- [intent:Q11] 已拒絕欄位級權限（維持 story × action 粒度）。
- [intent:Q14] N 值留 requirements-analysis；「可設定門檻」選項（D）未被選取。
- [feas:Q1/Q8] 記錄事件＝任何有效活動；欄位語意＝最後活動時間。
- [feas:Q4] 保存上限存在、值未定。
- [feas:Q7] 權限擴張風險接受記入 RAID log。
- [memory:M1] schema／seed 變更須同步更新部署資產（blocking）。

## Q1. 四項能力的 MoSCoW 分級？

> 候選能力：(a) 記錄帳號最後活動時間；(b) 管理介面顯示該欄位；(c) 逾期未活動視覺標示（N 未定）；(d) `Security_Reviewer` 檢視權限開通。
> (a)(b) 顯然是 Must（沒有它們功能不存在）。分歧點在 (c) 與 (d)。

A. 全部 Must — 四項缺一不可，一起上線才算完成。
B. (a)(b) Must；(c) Should（N 定案後補上，不阻擋欄位先上線）；(d) Must。
C. (a)(b) Must；(c) Should；(d) Should（權限開通可後補，先讓既有 3 個角色看到）。
D. (a)(b) Must；(c) Could；(d) Must。
X. Other (please specify)

[Answer]: A

## Q2. 交付排序偏好？

> 依賴關係固定：(a) 記錄 →(b) 顯示 →(c) 標示；(d) 權限開通與 (a)(b)(c) 無技術依賴，可平行。排序策略決定 inception 的 backlog 順位與未來 Bolt 次序。

A. Dependency-first — 依 (a)→(b)→(c) 依賴鏈排序，(d) 排最後（最直觀）。
B. Value-first — 先讓看得到的價值最大化：(a)(b) 先行，(d) 緊隨（稽核受益者早日看到），(c) 殿後。
C. Risk-first — 先做不確定性最高的 (a)（活動記錄的寫入頻率與緩解手段），其餘依賴序跟上。
D. Not yet defined — 交由 delivery-planning 決定。
X. Other (please specify)

[Answer]: A

## Q3. Won't Have（本次明確排除）清單確認？（select all that apply）

> 「Won't Have」是 scope 最有價值的部分：明列不做的事，防止範圍蔓延。下列候選皆源自上游已拒絕或未選取的選項。

A. 登入／活動歷史紀錄（僅預留擴充路徑，不實作）[intent:Q9]
B. 稽核報表匯出 [intent:Q3 選項 D 未選]
C. 門檻 N 的管理介面可設定功能 [intent:Q14 選項 D 未選]
D. 欄位級權限控制 [intent:Q11 已拒絕]
E. 依最後活動時間排序／篩選 [intent:Q3 選項 B 未選]
X. Other (please specify)

[Answer]: X. 部分列入：A, C, D, E（使用者逐字輸入「ACDE」；B 稽核報表匯出不列入 Won't Have）（guided 釐清，2026-08-03）

## Q4. 部署資產同步（schema_rbac.sql／DEPLOY.md 更新）在 backlog 的定位？

> M1 規定此為 blocking 義務 [memory:M1]：未完成不得標示相關 Construction／部署階段為完成。問題是它在 backlog 的「表現形式」。

A. 內建於 Must 能力的完成定義 — 不獨立成項，(a)(d) 的 Definition of Done 各自內含對應的部署資產更新。
B. 獨立 backlog 項目 — 單獨列為一個 Must 項目，集中追蹤。
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Consolidated Summary Confirmation

> 4 題已作答（Q3 經一輪釐清）。矛盾檢查（§3）：無阻斷矛盾。
> 需記載的依賴：Q1=A 把視覺標示 (c) 列為 Must，而 N 值未定 → 「N 於 requirements-analysis 定案」成為上線前置依賴（承 feasibility raid-log D2）。
> B 稽核報表匯出未列入 Won't Have，也未被任何已選選項納入範圍 → 以「未承諾」狀態記入 assumption。
>
> 答案彙整：Q1=A（記錄／顯示／視覺標示／權限開通四項全 Must）、Q2=A（dependency-first：(a)→(b)→(c)，(d) 殿後）、Q3=X（Won't Have = A 歷史紀錄、C 門檻可設定介面、D 欄位級權限、E 排序／篩選）、Q4=A（部署資產同步內建於 DoD，不獨立成項）。

**Prompt**: Does this all look correct before I generate the artifacts?

A. Looks correct — 依這些答案產出 artifact
B. Request changes — 先修改一或多題答案

[Answer]: A. Looks correct（2026-08-03）

## Assumption Confirmation

> 兩份 artifact 的 `## Assumptions & Open Questions` 皆非 `None.`，依 learned rule 需人工確認。
> **接受不等於把 assumption 變成事實** —— `[assumption]` 標籤會原樣保留在 artifact 中。

**`scope-document.md`**

- [assumption] 視覺標示 (c) 為 Must 且門檻 N 未定 [Q1] [intent:Q3]；「N 於 requirements-analysis 定案」因此成為上線前置依賴，N 不定案則 Must 集合不可完整交付
- [assumption] 稽核報表匯出處於「未承諾」狀態 [Q3]：不在範圍、不在排除清單；本階段不推定其未來去向
- [assumption] 活動資料保存上限的值未定（承 feasibility-assessment 的既有 assumption），與本範圍的 (a) 能力共享同一個 requirements-analysis 定案時點 [feas:Q4]

**`intent-backlog.md`**

- [assumption] PU-3 的 Must 地位使 N 值定案成為整體上線的前置條件 [Q1] [intent:Q14]；若 requirements-analysis 未定 N，Must 集合不可完整交付
- [assumption] 四項 proto-unit 的粒度是否即為最終 Unit 切分，由 units-generation 檢驗；本清單不預作技術切分承諾
- [assumption] （開放問題）PU-1 的寫入頻率緩解手段（節流／彙整／非同步）尚未選定，承 feasibility-assessment 的 R1，設計階段必答

A. Accept assumptions — 保留 [assumption] 標籤，帶著這 6 項進入 approval gate
B. Convert to follow-up questions — 補題釐清後再修訂 artifact

[Answer]: A. Accept assumptions（2026-08-03）

## Revision 1（2026-08-04，backward jump 修訂）

> 來源：rough-mockups 問題檔（`../rough-mockups/rough-mockups-questions.md`）的已確認答案 —
> [rm:Q5]=B（WCAG 2.1 AA＋行動響應式，含小螢幕卡片式改造）、[rm:Q5a]=B（擴充 scope：改造納入本 feature 為第五項能力）、
> 影響分析經使用者確認（「確認回跳修訂」）。
>
> 修訂內容：
> - scope-document：In scope 新增第五項 Must 能力 (e) 行動響應式卡片改造；MoSCoW 總表更新；assumptions 增列前端回歸風險。
> - intent-backlog：新增 PU-5（依賴 PU-2／PU-3）；排序圖更新。
> - Won't Have 清單與「未承諾」項目不變。
>
> 本 revision 不改既有 Q1–Q4 的答案；Q1=A 的「全 Must」原則延伸適用於第五項能力（與 [rm:Q5a]=B 的擴充決定一致）。

## Assumption Confirmation（Revision 1 重設）

> Revision 1 使兩份 artifact 的 `## Assumptions & Open Questions` 各新增一條，依 learned rule 重設本關卡並重新取得人工確認。
> **接受不等於把 assumption 變成事實** —— `[assumption]` 標籤會原樣保留在 artifact 中。

**`scope-document.md`**（4 條：原 3 條＋新增 1 條）

- [assumption] 視覺標示 (c) 為 Must 且門檻 N 未定 [Q1] [intent:Q3]；「N 於 requirements-analysis 定案」因此成為上線前置依賴，N 不定案則 Must 集合不可完整交付
- [assumption] 稽核報表匯出處於「未承諾」狀態 [Q3]：不在範圍、不在排除清單；本階段不推定其未來去向
- [assumption] 活動資料保存上限的值未定（承 feasibility-assessment 的既有 assumption），與本範圍的 (a) 能力共享同一個 requirements-analysis 定案時點 [feas:Q4]
- [assumption] 卡片改造 (e) 動到既有使用者管理頁的表格架構，對既有功能（操作、啟停用等）構成前端回歸風險 [rm:Q5]；回歸涵蓋面於 PU-5 的 DoD 落實，具體測試範圍留待 inception 界定

**`intent-backlog.md`**（4 條：原 3 條（其一改「五項」）＋新增 1 條）

- [assumption] PU-3 的 Must 地位使 N 值定案成為整體上線的前置條件 [Q1] [intent:Q14]；若 requirements-analysis 未定 N，Must 集合不可完整交付
- [assumption] 五項 proto-unit 的粒度是否即為最終 Unit 切分，由 units-generation 檢驗；本清單不預作技術切分承諾
- [assumption] （開放問題）PU-1 的寫入頻率緩解手段（節流／彙整／非同步）尚未選定，承 feasibility-assessment 的 R1，設計階段必答
- [assumption] PU-5 的前端回歸驗證涵蓋面（既有管理頁功能在卡片佈局下的測試範圍）尚未界定，留待 inception [rm:Q5]

A. Accept assumptions — 保留 [assumption] 標籤，帶著這 8 項進入 approval gate
B. Convert to follow-up questions — 補題釐清後再修訂 artifact

[Answer]: A. Accept assumptions（2026-08-04，Revision 1）


---

## Revision 2（2026-08-10，backward jump 修訂）

**觸發來源**：Construction 3.2（NFR Requirements）為 U2 `user-object-serialization` 出題時，實測 `user_router.py` 的清單端點為 `db.query(User).order_by(User.id).all()` —— **無分頁、無上限**，回傳全部帳號；且迴圈內對每個待授權使用者另有一次查詢（既有 N+1）。決策者判定應訂下分頁需求，而非僅記載現況。

依 `project.md ## Corrections` 的既有規則：「下游 stage 的答案觸發 scope 擴充時，回跳上游 stage 以 Modify 模式疊加修訂（歸檔舊 artifact、既有答案與清單不動、修訂來源記入問題檔 Revision 段）並重走 approval gate」。

**既有答案（Q1〜Qn 與 Revision 1）一律不改寫。** 本次新增三題。

### R1. 分頁在 scope 上的定位

A. **新增獨立能力 (f)** — **（建議，已採用）** 分頁有自己的驗收面（回應形狀、兩種佈局的互動、型別契約）與失敗模式，且會影響 U2／U3／U5 三個單元。埋進 (b) 的 DoD 會讓它在 units-generation 時沒有可追蹤的獨立身分。
B. 併入 (b) 的 Definition of Done — 代價：分頁實際改的是 API 回應契約（U2），不只是顯示（U3），埋進 (b) 會低估其跨層影響。

[Answer]: A

### R2. 分頁的優先層級

A. **Must，與其他五項一起上線** — **（建議，已採用）** 維持 Q1 已定案的「無次級優先層」結構，不因本次修訂而改變。代價：關鍵路徑變長。
B. 新設 Should 層 — 代價：推翻 Q1 已定案的結構；且分頁會改變 U2 的回應契約，先上無分頁版再加分頁等於改兩次契約。

[Answer]: A

### R3. 分頁與 Won't Have「不做互動排序／篩選」的邊界

A. **排序／篩選維持排除，只加分頁** — **（建議，已採用）** Won't Have 該條**不變**，並明寫「分頁是本次新增的唯一清單互動，不連帶鬆動排序與篩選的排除」，避免下游誤讀為清單互動已解禁。
B. 連帶解除排序的排除 — 代價：再一層範圍擴充，會再影響 mockups、端點契約與型別；且該排除項是 intent-capture 階段就定案的。

[Answer]: A

## Assumption Confirmation（Revision 2 重設）

> Revision 2 使兩份 artifact 的 `## Assumptions & Open Questions` 各新增條目，依 `project.md` 的既有規則重設本關卡並重新取得人工確認。

**新增的假設**（兩份 artifact 合計三條，內容互相對應）：

1. 分頁形式（頁碼式／游標式、每頁筆數、回應是否包 envelope）屬設計決定，留 application-design 定案
2. 分頁與逾期標示的互動（逾期帳號散落多頁時是否需跨頁彙總）留 refined-mockups 評估
3. PU-6 對 PU-5 的排序約束是**避免重工**而非技術依賴，下游可在記明重工緩解方式的前提下覆寫

A. Accept assumptions
B. Modify（請指明哪一條）

[Answer]: A. Accept assumptions（2026-08-10，Revision 2）
