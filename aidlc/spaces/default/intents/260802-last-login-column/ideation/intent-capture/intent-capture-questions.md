# Intent Capture — 釐清問題

> Stage: intent-capture（Ideation 1.1）· Depth: Standard · Scope: feature
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。

## Sources

- [desc] Initial description: "在 Admin 頁加上使用者最後登入時間欄位"
- [scope] Workflow-selected scope: `feature`.
- [memory:M1] `aidlc/spaces/default/memory/project.md#Mandated`: "ALWAYS 在變更**資料庫結構或部署必知的 schema／seed 行為**時同步更新部署資產（blocking，未完成不得標示相關 Construction／部署階段為完成）："
- [memory:M2] `aidlc/spaces/default/memory/project.md#Scope Overrides`: "❌ **Out of scope（除非經新 ADR 核可）**：雲端供應商 production 環境、production credentials、environment-specific secrets、direct production IaC、destructive cloud operations、native iOS/Android app。"
- [memory:M3] `aidlc/spaces/default/memory/team.md#Mandated`: "✅ **小步前進**：每個 stage 完成後產出 stage-completion summary，附 extension compliance（compliant / non-compliant / N/A 與理由），等使用者確認再進下一階段。"
- [memory:M4] `aidlc/spaces/default/memory/project.md#Decided`: "DECIDED: `extensions/security/baseline/` 預設啟用，為 hard constraint（IAM、encryption、network exposure、audit logging）。requirements analysis 階段不需再詢問。(ADR-0006)"

## Q1. 這個功能要解決什麼業務問題？

A. 稽核需求 — 需要知道帳號最後活動時間以符合存取稽核
B. 帳號治理 — 找出長期未登入的殭屍帳號以便停用或回收
C. 支援排查 — 客服／管理員排查「使用者說登不進去」時需要佐證
D. 純資訊展示 — 沒有特定驅動，只是 Admin 頁該有的欄位
E. Not yet defined — 尚未定義，先做再說
X. Other (please specify)

[Answer]: A. 稽核需求 — 需要知道帳號最後活動時間以符合存取稽核（chat 模式，2026-08-02）

## Q2. 誰會實際看這個欄位？他們現在遇到什麼痛點？

A. Platform_Admin／Platform_Owner — 目前完全查不到登入紀錄，只能問當事人
B. Security_Reviewer — 需要稽核證據，目前得翻後端 log
C. Ops_Lead／SRE — 需要判斷帳號是否仍在使用
D. 所有能進 Admin 頁的角色都看得到即可，不特別區分
E. Not yet defined
X. Other (please specify)

[Answer]: X. 限 `Platform_Admin` 與 `Security_Reviewer` 兩個角色可見（chat 模式，2026-08-02）。註：使用者明確指定這兩個角色，未包含選項 A 併列的 `Platform_Owner`；痛點面向以稽核為主（見 Q1）。
>
> **⚠️ 本答案的「只有」已由 Q12=A 取代**：實際可見角色為 `Project_Admin`、`Platform_Admin`、`Platform_Owner`、`Security_Reviewer`（4 個）。原答案保留作為決策軌跡，不改寫。

## Q3. 成功長什麼樣子？用什麼衡量？

A. Admin 頁能顯示每個使用者的最後登入時間，且值正確（可與後端 log 對照）
B. 上述 A，另加「可依最後登入時間排序／篩選」
C. 上述 A，另加「超過 N 天未登入的帳號有視覺標示」
D. 能匯出稽核報表（含最後登入時間）
E. Not yet defined — 只要欄位出現就算成功
X. Other (please specify)

[Answer]: C

## Q4. 為什麼是現在做？觸發原因是什麼？

A. 稽核／合規要求，有外部期限
B. 實際發生過帳號治理問題（殭屍帳號、離職未停用）
C. J5 授權申請流程上線後，管理員需要更多帳號脈絡
D. 技術債清理 — 這個欄位本來就該有
E. None — 沒有特定觸發，屬機會性改善
X. Other (please specify)

[Answer]: E

## Q5. 關鍵 stakeholder 有哪些？各自在意什麼？（可複選）

A. Platform_Admin — 在意日常帳號管理效率
B. Security_Reviewer — 在意稽核軌跡的完整性與正確性
C. 一般使用者 — 在意自己的登入時間是否被記錄（隱私）
D. 開發團隊 — 在意實作成本與對既有登入流程的影響
E. Not identified — 目前只有你一個決策者
X. Other (please specify)

[Answer]: A

## Q6. 誰決定範圍與優先序？誰有影響力但不決策？

A. 你（Danniel）單獨決定
B. 你決定，但 Security_Reviewer 對稽核欄位有否決權
C. 需要團隊共識（多人會審）
D. Not identified
X. Other (please specify)

[Answer]: A

## Q7. 有溝通或回報節奏的需求嗎？

A. 無 — 做完在 PR 說明即可
B. 需要在 decisions-log 記錄決議
C. 需要開 ADR（若牽涉隱私／稽核資料保存政策）
D. Not applicable
X. Other (please specify)

[Answer]: B

## Q8. 這個 workflow 以 `feature` scope 起跑（32/32 stages、Standard 深度、29 個 approval gate）。這符合你心中的產品邊界嗎？

> 本題區分「確認 workflow 選定的 scope」與「定義不同的產品邊界」。

A. 確認 — `feature` scope 就是我要的產品邊界
B. 產品邊界更小 — 只是加一個欄位，希望改用較輕的 scope（如 `mvp`）
C. 產品邊界更大 — 這其實是「帳號活動追蹤」的第一步，之後還有更多
D. Not yet defined — 先跑，之後在 gate 調整
X. Other (please specify)

[Answer]: A

## Q9. 稽核需要「歷史」還是只要「最後一次」？

> 這題決定資料模型，是本 stage 最有成本影響的分岔。Q1 選了稽核需求，但「最後登入時間」單一欄位會覆寫歷史。

A. 只要最後一次 — `users` 加 `last_login_at` 欄位，登入時覆寫。稽核只問「這帳號多久沒動」。
B. 需要歷史 — 新增登入事件表，保留每次登入。稽核會問「過去 N 天登入幾次／何時」。
C. 先做 A，但資料模型要預留 B 的擴充路徑（不現在做表，但不擋未來）
D. Not yet defined — 需要先確認稽核方要什麼
X. Other (please specify)

[Answer]: C. 先做單一欄位，資料模型預留擴充路徑（chat 模式，2026-08-02）

## Q10. `Security_Reviewer` 目前在 J3a（使用者設定）的權限是 `false/false/false` — 完全進不了 Admin 使用者頁。要怎麼給他看到這個欄位？

> 事實來源：`schema_rbac.sql` 第 475 行 `('Security_Reviewer', 'J3a', false, false, false)`。

A. 給 `Security_Reviewer` J3a 的 view 權限 — 他會看到整個 Admin 使用者頁（含所有既有欄位）
B. 新增一個獨立 story（如 J3c「帳號稽核資訊」）給稽核欄位，`Security_Reviewer` 只拿這個 — 權限更精準，但要動 RBAC 矩陣與 seed
C. 不給 `Security_Reviewer` 頁面權限，改成匯出稽核報表的獨立管道
D. Not yet defined
X. Other (please specify)

[Answer]: A. 給 `Security_Reviewer` J3a 的 view 權限（chat 模式，2026-08-02）

## Q11. `Project_Admin`（J3a 全 true）與 `Platform_Owner`（J3a view）目前看得到 Admin 使用者頁。他們該看到這個新欄位嗎？

> 目前 RBAC 的粒度是 story × action，**沒有欄位級權限**。若要讓部分能看頁面的角色看不到單一欄位，是新的權限概念。

A. 他們也可以看到 — 不需要欄位級權限，維持現狀粒度（最省）
B. 他們不該看到 — 接受引入欄位級權限或獨立 story 的成本
C. `Platform_Owner` 可以看、`Project_Admin` 不行（或反之，請在 X 說明）
D. Not yet defined
X. Other (please specify)

[Answer]: A. 他們也可以看到，維持現狀粒度（chat 模式，2026-08-02）

## Q12. 矛盾解消：Q2 說「只有兩個角色看得到」，Q11=A 卻讓四個角色都看得到

> **偵測到的矛盾**（stage-protocol.md §3 強制檢查）：
>
> | 來源 | 內容 |
> |---|---|
> | Q2 | 「只有 `Platform_Admin` 與 `Security_Reviewer` 看得到」 |
> | Q10=A | 給 `Security_Reviewer` J3a view 權限 → 他看得到**整個** Admin 使用者頁 |
> | Q11=A | `Project_Admin`、`Platform_Owner` 也看得到新欄位 |
>
> Q10+Q11 的實際結果是 **4 個角色**可見：`Project_Admin`、`Platform_Admin`、`Platform_Owner`、`Security_Reviewer`。
> 這與 Q2 的「只有」不相容，且與 Q1 的稽核意圖（限制稽核資料的接觸面）張力明顯。

A. 放寬 Q2 — 接受 4 個角色都看得到。理由：能進 Admin 使用者頁的本來就是管理類角色，稽核欄位對他們不算越權。最省，不動既有權限。
B. 堅持 Q2 — 推翻 Q11=A，接受欄位級權限或獨立 story（如 J3c）的成本
C. 收回既有權限 — 移除 `Project_Admin`／`Platform_Owner` 的 J3a view，使實際可見者回到兩個角色。**注意：這會影響他們現有的使用者管理工作**
D. 稽核資料另開介面 — 不放在 Admin 使用者頁，改為獨立的稽核檢視（自帶 story 與權限），Q11 的欄位級問題自然消失
X. Other (please specify)

[Answer]: A. 放寬 Q2，接受 4 個角色都看得到（chat 模式，2026-08-02）

## Q13. 矛盾解消：`Security_Reviewer` 是受益者且我們正在為他改權限，但 Q5 沒把他列為 stakeholder

> **偵測到的矛盾**（stage-protocol.md §3 強制檢查）：
>
> | 來源 | 內容 |
> |---|---|
> | Q1 | 業務問題是「稽核需求」 |
> | Q2 | 點名 `Security_Reviewer` 為可見角色 |
> | Q10=A | **為他新增** J3a view 權限（實際的 RBAC 變更） |
> | Q5=A | 關鍵 stakeholder **只有** `Platform_Admin`／`Platform_Owner` |
>
> 若 `Security_Reviewer` 不是 stakeholder，`stakeholder-map.md` 就不會有他 —— 但整個功能的目的是稽核，且我們正在為他改權限。

A. 補上 `Security_Reviewer` 為 stakeholder（在意稽核軌跡的完整性與正確性）
B. 維持 Q5=A — `Security_Reviewer` 是使用者但非 stakeholder（不參與需求或優先序決策）；stakeholder-map 只列決策相關方
C. 補上 `Security_Reviewer`，另補開發團隊（在意實作成本）
X. Other (please specify)

[Answer]: A. 補上 `Security_Reviewer` 為 stakeholder（chat 模式，2026-08-02）

## Q14. Q3=C 的「超過 N 天未登入」— N 是多少？

> phases/ideation.md 要求「Success metrics must be measurable — avoid vague outcomes」。N 未定義的話，這個成功指標不可驗證。

A. 30 天
B. 60 天
C. 90 天（常見的存取稽核週期）
D. 可設定 — 由管理者自行調整門檻（成本較高，需設定介面）
E. Not yet defined — 留到 requirements-analysis 再定，本階段標記為 assumption（chat 模式，2026-08-02）
X. Other (please specify)

[Answer]: E. Not yet defined — 留到 requirements-analysis 再定，標記為 assumption

## Consolidated Summary Confirmation

> 全部 14 題已作答。矛盾檢查（§3）第二輪通過：Q12 解消「可見角色數」矛盾、Q13 解消「stakeholder 缺漏」矛盾、Q14 解消「N 未定義」的不可衡量問題。
> 餘下三項為**張力而非矛盾**，將以 `[assumption]` 寫入 artifact，不阻斷流程：
> (1) Q1 稽核需求 vs Q4 無外部觸發；(2) Q4 機會性改善 vs Q8 完整 32-stage scope；(3) Q10=A 授予整頁 view 造成的權限擴張 vs M4 security baseline 的最小權限原則。

**Prompt**: Does this all look correct before I generate the artifact?

A. Looks correct — 依這些答案產出 artifact
B. Request changes — 先修改一或多題答案

[Answer]: A. Looks correct（2026-08-02）

## Assumption Confirmation（第 1 輪，已被下方第 2 輪取代）

> 兩份 artifact 的 `## Assumptions & Open Questions` 皆非 `None.`，依 stage 檔 Step 6 需確認。
> **接受不等於把 assumption 變成事實** —— `[assumption]` 標籤會原樣保留在 artifact 中。

**`intent-statement.md`**

| # | Assumption / Open question | Source |
|---|---|---|
| A1 | 「超過 N 天未登入」的 N 尚未定義；成功指標在 N 決定前不可完整驗證 | [Q3] [Q14] |
| A2 | 業務問題為稽核需求但無外部觸發；理解為「自發建立稽核能力」而非回應既有稽核缺失 | [Q1] [Q4] |
| A3 | 描述為機會性改善卻採用 `feature` 完整階段集；成本與驅動力的比例未在本階段檢驗 | [Q4] [Q8] [scope] |
| A4 | 為 `Security_Reviewer` 開通的檢視權限接觸面大於稽核欄位本身，與 security baseline 最小權限存在張力；未取得針對該副作用的獨立確認 | [Q10] [memory:M4] |
| O1 | 未來保留登入歷史的擴充路徑形式尚未探討 | [Q9] |

**`stakeholder-map.md`**

| # | Assumption / Open question | Source |
|---|---|---|
| A5 | 「影響者但非決策者」未被指認；不推定任何角色具影響力 | [Q6] |
| A6 | 除決議紀錄外的回報節奏未被指認；不推定任何節奏需求 | [Q7] |
| A7 | `Security_Reviewer` 為 stakeholder，但其權責（否決權、是否參與 N 值決定）未界定 | [Q13] [Q6] |
| O2 | `Security_Reviewer` 作為 stakeholder 的利益範圍是否僅限稽核欄位，未釐清 | [Q10] [Q13] |

A. Accept assumptions — 保留 `[assumption]` 標籤，帶著這些未解項目進入下一階段
B. Convert to follow-up questions — 針對其中一或多項補題釐清後再修訂 artifact

[Answer]: A. Accept assumptions（涵蓋 A1–A4、O1、A5–A7、O2 共 9 項；reviewer iteration 2 後新增 A8，故重跑本關卡）

## Assumption Confirmation

> 第 2 輪（取代上方第 1 輪）：reviewer iteration 2 指出為修正 Critical 而新增的 assumption（A8）未經人工確認，故重跑本關卡。
> 下列條目逐字對應兩份 artifact 的 `## Assumptions & Open Questions` 現行內容（intent-statement 5 條、stakeholder-map 5 條）。

**`intent-statement.md`**

- [assumption] 「超過 N 天未登入」的 N 尚未定義，本階段不假設任何數值；成功指標在 N 決定前不可完整驗證 [Q3] [Q14]
- [assumption] 業務問題被指認為稽核需求，同時又無外部觸發或期限；本文件據此理解為「自發建立稽核能力」，而非回應既有稽核缺失 [Q1] [Q4]
- [assumption] 本工作被描述為機會性改善，卻採用 `feature` scope 的完整階段集；成本與驅動力的比例關係未在本階段檢驗 [Q4] [Q8]
- [assumption] 為 `Security_Reviewer` 開通的是使用者管理介面的檢視權限，其接觸面大於稽核欄位本身；此擴張與 security baseline 的最小權限面向存在張力，本階段未取得針對該副作用的獨立確認 [Q10] [memory:M4]
- [assumption] （開放問題）未來若需保留登入歷史，擴充路徑的具體形式尚未探討；本階段僅確認需預留，不定義做法 [Q9]

**`stakeholder-map.md`**

- [assumption] `Project_Admin` 與 `Platform_Owner` 具備使用者管理介面的可見性 [Q11] [Q12]，但兩者在本工作中的利益均未被指認 —— `Q5` 的已選選項只涵蓋 `Platform_Admin`。本階段不推定其利益內容，亦不將其列為受益者或排除 [Q5] [Q11] [Q12]
- [assumption] 「影響者但非決策者」未被指認；本階段不推定任何角色具影響力 [Q6]
- [assumption] 除決議紀錄外的回報節奏未被指認；本階段不推定任何節奏需求 [Q7]
- [assumption] `Security_Reviewer` 被確認為 stakeholder，但其在稽核欄位上的權責（是否具否決權、是否參與 N 值決定）未被界定 [Q13] [Q6]
- [assumption] （開放問題）`Security_Reviewer` 將取得使用者管理介面的完整檢視權限 [Q10]，其作為 stakeholder 的利益範圍是否僅限稽核欄位，本階段未釐清 [Q13]

A. Accept assumptions — 保留 [assumption] 標籤，帶著這 10 項進入 approval gate
B. Convert to follow-up questions — 補題釐清後再修訂 artifact

[Answer]: A. Accept assumptions
