# Feasibility & Constraints — 釐清問題

> Stage: feasibility（Ideation 1.3）· Depth: Standard · Scope: feature
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。
> 上游輸入：`../intent-capture/intent-statement.md`（intent-statement）。market-research 已跳過，其可選輸入（competitive-analysis、market-trends、build-vs-buy）依 scope 設計不存在。

## Sources

查證事實（僅用於出題與選項設計，依 ideation 規則不寫入產出 artifact 的設計層）：

- [code:C1] `backend/services/user_router.py:352-376` — `POST /api/auth/login` 成功後只核發 token，**不寫任何資料庫紀錄、不輸出任何 log**；系統今日完全沒有登入時間的既有紀錄。
- [code:C2] `backend/services/auth.py` — JWT 無狀態認證，token 有效 8 小時，**無 refresh 機制**；`POST /api/auth/register` 註冊成功也會核發 token。
- [code:C3] `schema_rbac.sql:29-35`、`backend/models.py:22-51` — `users` 表無任何 last-login 類欄位。
- [code:C4] `backend/database.py:123-265` — 專案無 migration 框架；既有慣例是啟動時 `_ensure_*_schema` patch（`IF NOT EXISTS` 可重跑）。`DEPLOY.md:205` 記載既有環境升級為雙路徑：重跑 `schema_rbac.sql` **或**依賴 startup patch。
- [code:C5] `DEPLOY.md:250-253`、`schema_rbac.sql:180` — 重跑 `schema_rbac.sql` 會 DELETE 後重播 `role_permissions` seed，**覆寫線上以 Admin UI 調整過的權限**。
- [code:C6] `schema_rbac.sql:467-477` — J3a 今日可見角色僅 `Project_Admin`、`Platform_Admin`、`Platform_Owner`（view）；`Security_Reviewer` 全 false。seed 同時存在於 `schema_rbac.sql` 與 `backend/services/rbac_seed_data.py` 兩處，須同步。
- [intent:Q1] 業務問題：無法得知帳號最後活動時間，無法滿足存取稽核。
- [intent:Q3] 成功指標：顯示值「可與後端紀錄對照驗證」＋逾期未登入視覺標示（N 未定，assumption）。
- [intent:Q9] 資料模型只留最後一次，但須預留歷史擴充路徑。
- [intent:Q10/Q12] 已決定：給 `Security_Reviewer` J3a view，接受 4 角色可見（不再重問）。
- [memory:M1] `project.md#Mandated` — schema／seed 行為變更須同步更新 `schema_rbac.sql` 與 `DEPLOY.md`（blocking）。
- [memory:M4] `project.md#Decided` — security baseline hard constraint（ADR-0006）。

## Q1. 「帳號仍在使用」以什麼事件為準？

> 查證：登入後 token 有效 8 小時且無 refresh [code:C2]，因此「最後取得 token 的時刻」與「最後實際活動」最多可差 8 小時；且今日系統對兩者都沒有任何紀錄 [code:C1]。intent 的問題陳述是「最後**活動**時間」[intent:Q1]，但功能名稱是「最後**登入**時間」。稽核查驗的證據事件需要先定錨，否則成功指標無法驗證。

A. 只算成功登入 — 以每次成功登入（核發 token）的時刻為準；8 小時內的持續使用不更新。語意為「最後登入」，成本最低。
B. 登入＋註冊 — 同 A，另把註冊當下首次核發 token 也算一次登入，新帳號不會出現「從未登入」的空窗。
C. 任何有效活動 — 任何帶有效 token 的 API 請求都算，語意為「最後活動」；較貼近稽核原意，但每次請求都需記錄（或節流記錄），成本與效能影響明顯較大。
D. Not yet defined — 留到 requirements-analysis 再定。
X. Other (please specify)

[Answer]: C

## Q2. 上線前的歷史空窗如何處理？

> 查證：系統今日沒有任何可回填的登入紀錄來源（無資料庫紀錄、login 無 log 語句、log 亦無持久化）[code:C1]。功能上線那一刻，**所有既有帳號的最後登入時間必然是空值**，且此空窗無法用回填消除。

A. 接受空窗 — 空值顯示「無紀錄」，稽核接受「上線後才開始累積」；空窗大小 = 帳號自上線起實際未登入的時間。
B. 空值視同逾期 — 空值直接套用「超過 N 天未登入」的視覺標示邏輯，從嚴解讀。
C. 空窗不可接受 — 若稽核方要求歷史，因回填不可行，功能需先建立紀錄來源、延後欄位上線。
D. Not yet defined
X. Other (please specify)

[Answer]:A

## Q3. 既有環境（staging）如何取得這次的 schema 與權限變更？

> 查證：本功能同時觸發兩類變更 —（a）`users` 表新欄位、（b）`Security_Reviewer` 的 J3a seed 值翻轉 [code:C3][code:C6]。專案無 migration 框架，既有慣例是 startup patch 或重跑 `schema_rbac.sql` 雙路徑 [code:C4]；但重跑整支 SQL 會重置 `role_permissions`，覆寫線上手動調整過的權限 [code:C5]。無論選哪條路，M1 規定 `schema_rbac.sql` 與 `DEPLOY.md` 都必須同步更新（blocking）[memory:M1]。

A. 沿用既有慣例 — 新欄位走 startup patch（可重跑安全），權限值以最小範圍的更新語句套用；`schema_rbac.sql`／`DEPLOY.md` 同步更新但 staging 不重跑整支 SQL。
B. 重跑整支 SQL — 接受 `role_permissions` 被重置為 seed 預設值的副作用（重跑前需備份既有權限）。
C. 引入正式 migration 工具 — 一次還清技術債，但成本明顯超出本 feature 的份量。
D. Not yet defined — 留到 Construction 的部署規劃再定。
X. Other (please specify)

[Answer]: A

## Q4. 登入時間資料有沒有隱私或保存期限的約束？

> 登入時間屬於使用者行為資料。本平台為自有 staging 的內部工具（無雲端 production）[memory:M2 於 intent-statement 已載]，但稽核資料的保存政策仍應在建立能力前定錨；若未來擴充為登入歷史 [intent:Q9]，保存期限的影響會放大。

A. 無特殊約束 — 內部平台，登入時間不視為敏感個資，無限期保留。
B. 有保存上限 — 需定義保存期限（值可留待 requirements-analysis，此處先確認「有上限」這個約束存在）。
C. 需揭露 — 需在使用者可見的說明（如登入頁或使用條款）揭露登入時間會被記錄。
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q5. 有沒有時程、預算或組織性阻塞？

> intent 已確認本工作屬機會性改善、無外部期限 [intent:Q4=E]。可行性評估仍需確認沒有隱性阻塞（change freeze、競爭中的優先工作、依賴他人的時窗）。

A. 無阻塞 — 隨開發能量排入，無時間盒。
B. 有時間盒 — 希望在特定時間內收斂（請在 X 補充天數或日期）。
C. 有競爭優先事項 — 本功能隨時可能被插隊，接受中斷後再續。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 無阻塞（guided 補答，2026-08-03）

## Q6. 「值可與後端紀錄對照驗證」的驗證手段是什麼？

> 矛盾檢查：成功指標要求顯示值「可與後端紀錄對照驗證」[intent:Q3]，但查證顯示後端今日**沒有任何登入紀錄可供對照** [code:C1] — 本功能寫入的值就是唯一紀錄，形成「自己驗自己」。驗證手段需要先定錨，否則指標不可檢驗。

A. 受控測試驗證 — 以測試帳號實際登入，比對介面顯示值與登入動作的時刻；不要求第二資料來源。
B. 結構化 log 為第二來源 — 登入時同時輸出結構化 log，稽核可交叉比對資料庫值與 log；範圍隨之擴大。
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q6a. 追問：Q1=C 之下，Q6=A 的「登入動作」如何理解？

> Q6=A 的選項文字寫「以測試帳號實際登入，比對介面顯示值與登入動作的時刻」；Q1=C 已把記錄事件擴為「任何有效活動」。確認驗證比對的對象。

A. 比對任何活動 — 受控測試中以任一 API 活動（含登入）的時刻比對顯示值，與 Q1=C 語意一致。
B. 僅比對登入 — 測試只用登入動作驗證（登入也是活動的一種，仍與 Q1=C 相容，只是測試面較窄）。
C. Not yet defined
X. Other (please specify)

[Answer]: A. 比對任何活動（guided 補答，2026-08-03）

## Q7. `Security_Reviewer` 權限擴張的風險處置如何記錄？

> intent 已決定給 `Security_Reviewer` 整頁 view、接受 4 角色可見 [intent:Q10/Q12]，**本題不重開該決定**。但該決定與 security baseline 的最小權限面向存在已標記的張力（intent-statement assumption A4）[memory:M4]。合規視角要求風險處置（接受／緩解）要有落點，稽核時才有證據。

A. RAID log 記風險接受 — 本 stage 的 raid-log 記載「權限擴張已知、風險接受」，gate 核可即為證據。
B. 開 ADR — 權限模型的擴張屬架構級決策，於 inception 開 ADR 正式記錄（含替代方案與後果）。
C. RAID log ＋後續補償控制 — 風險接受之外，將「稽核欄位的存取軌跡」列為未來待辦（非本 feature 範圍）。
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q8. 語意對齊確認：欄位語意由「最後登入」改為「最後活動」？

> Q1=C 的直接後果：欄位記錄的是「最後活動時間」（任何帶有效 token 的 API 請求都會更新），不再是字面上的「最後登入時間」。原始請求 [desc] 與 intent 成功指標 [intent:Q3] 皆以「最後登入時間」表述。此為語意層的對齊確認，非重開 Q1。

A. 確認改為「最後活動」 — 產品語意即「帳號最後活動時間」，後續階段的名稱、欄位標題與稽核解讀一律以活動為準；原始請求的「最後登入時間」據此重新表述。
B. 保留「最後登入」語意 — 推翻 Q1=C，回到只記錄登入事件（Q1 改為 A 或 B，請說明）。
C. 兩者並存 — 同時呈現「最後登入」與「最後活動」兩個時間（範圍與成本進一步擴大）。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 確認改為「最後活動」（guided 補答，2026-08-03）

## Consolidated Summary Confirmation

> 全部 9 題已作答（7 題原題＋Q6a、Q8 追問）。矛盾檢查（§3）：Q8=A 解消 Q1=C 與原始請求字面「最後登入」的語意衝突；其餘答案互相一致。
> 記入 artifact 的張力（非矛盾）：(1) Q1=C 的每請求寫入成本 → 記為 risk，緩解手段（如節流）留待設計階段；(2) Q4=B 保存上限值未定 → assumption，留 requirements-analysis；(3) 語意改為「最後活動」後，上游 intent-statement 的「最後登入」表述不回改，以本 stage 確認為準向下游傳遞。
>
> 答案彙整：Q1=C（任何有效活動都算）、Q2=A（接受空窗，空值顯示「無紀錄」）、Q3=A（startup patch＋最小更新語句，SQL/DEPLOY 同步更新）、Q4=B（有保存上限，值未定）、Q5=A（無阻塞）、Q6=A＋Q6a=A（受控測試，比對任何活動）、Q7=A（RAID log 記風險接受）、Q8=A（語意確認為「最後活動」）。

**Prompt**: Does this all look correct before I generate the artifacts?

A. Looks correct — 依這些答案產出 artifact
B. Request changes — 先修改一或多題答案

[Answer]: A. Looks correct（2026-08-03）

## Assumption Confirmation

> 三份 artifact 的 `## Assumptions & Open Questions`（raid-log 為 `## Assumptions（假設）` 表格，內容互相對應）皆非 `None.`，依 learned rule 需人工確認。
> **接受不等於把 assumption 變成事實** —— `[assumption]` 標籤會原樣保留在 artifact 中。

**`feasibility-assessment.md`**

- [assumption] 「超過 N 天未活動」的門檻 N 仍未定義，承襲 intent 階段的未決項；成功指標在 N 決定前不可完整驗證 [intent:Q3]
- [assumption] 活動資料有保存上限，但上限值未定，留待 requirements-analysis 決定 [Q4]
- [assumption] 單一欄位覆寫模式下，「保存上限」的實際含意（例如帳號停用後何時清除該值）尚未定義，隨 [Q4] 的值一併釐清
- [assumption] 本平台為內部工具，登入／活動時間不受外部法規框架（如個資保護法規的跨境或在地化要求）約束；此判斷未經法務確認 [Q4]
- [assumption] （開放問題）語意由「最後登入」改為「最後活動」後 [Q8]，上游 intent-statement 的「最後登入」表述不回改；若日後稽核方堅持登入語意，需回到 [Q1] 重新定錨

**`constraint-register.md`**

- [assumption] 本平台為內部工具，無外部法規框架適用於活動時間資料；此判斷未經法務或合規方獨立確認 [Q4]
- [assumption] 保存上限的值與「單一欄位覆寫」模式下的清除語意未定義，留待 requirements-analysis [Q4]
- [assumption] （開放問題）O2 的自動部署管線之下，資料庫變更與程式碼變更的生效順序（啟動時補齊發生在服務重啟時）是否需要額外的部署順序約束，留待 Construction 的部署規劃檢驗 [Q3]

**`raid-log.md`**（Assumptions 表 A1–A4，內容與上列對應，另含 A4：受控測試足以驗證正確性、不需第二資料來源 [Q6] [Q6a]）

A. Accept assumptions — 保留 [assumption] 標籤，帶著這些未解項目進入 approval gate
B. Convert to follow-up questions — 補題釐清後再修訂 artifact

[Answer]: A. Accept assumptions（2026-08-03）
