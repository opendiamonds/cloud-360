# Business Rules — U-3 看板客戶端

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-3-board-client · kind: library -->

## R-1 群：item 查找（[Q1=A] 定案）

| # | 規則 |
| --- | --- |
| R-1.0 | **`Issue.projectItems` 這條路徑必須先被 PRE-1 實測確認可用**，才可據以實作。本站未實測——**追加實測項的正式登錄見下方**，不只是這一行的提醒 |
| R-1.1 | 由 `binding`（issue 編號）反查該 issue 所屬的 project items，**不列舉整個 Project** |
| R-1.2 | 反查結果須過濾出 `Config` 指定的那個 Project（一個 issue 可同時屬於多個 Project） |
| R-1.3 | 過濾後為零筆 → 該 issue 尚未在看板上，回一個 `status`／`field_value` 皆為 `null` 的 `ItemState` |
| R-1.4 | 過濾後多於一筆 → **`ExternalError`**，不猜哪一筆 |

**R-1.2 是 [Q1=A] 引入的新責任**：列舉整個 Project（[Q1=B]）時目標 Project 是查詢的起點，本來就不會拿到別的 Project 的 item；反查 issue 則會拿到它所屬的**全部** Project。過濾條件因此是必須的，不是防禦性程式碼。

**R-1.4 之所以是錯誤而非取第一筆**：同一個 issue 在同一個 Project 內出現兩筆 item 代表看板狀態已經壞了，猜一筆會讓機制在一個它無法理解的狀態上繼續寫入。**與 [req:FR-C1] 「拿不準時不寫」同精神。**

> **經 ADR-0016 §6 補充**（2026-08-31T00:37:44Z）—— **R-1.4 保留，但標記為「防禦性斷言，無可構造的反例」**。PRE-1 第六輪實測：`addProjectV2ItemById` **冪等**，對同一 (project, issue) 重複呼叫回**相同的 item id**、`totalCount` 維持 1 ⇒ **本機制自己會用的 mutation 產生不出兩筆**（其他路徑未測，此限定不可省略）。
>
> 這**強化**而非削弱 R-1.4 的理由：既然機制自己造不出這個狀態，它一旦出現就確實是機制無法解釋的外部狀態。受影響的是**驗證方式**——U-3 的完成判準若要求各條規則各有可達的反例，**本條寫不出來**，須明記為無可構造反例，**不得要求實作者發明假的觸發途徑**（那會產生一個永遠走不到、卻看起來被測過的分支；`project.md` 的 `functional-design:c10` 正是此形狀）。
>
> **另補 R-1 群兩項實測結論**：①`Issue.projectItems` 的反查條件是**同擁有者**，**不需要** `linkProjectV2ToRepository`——未連結狀態下即回 `totalCount: 1`，故 U-3 **不需**自行確保 repo↔project 連結；②R-1.2 的過濾**經實測確認為必須**——同一 issue 屬兩個 Project 時反查回 `totalCount: 2`，每筆各帶自己的 `project.id`。見 `../decisions/0016-credential-topology-and-pre1-amendments.md`

> **經 ADR-0016 §4 增訂：本群缺兩項規格**（2026-08-31T00:37:44Z）——下列兩點是 U-3 的設計**從未指定**的內容（非既有內容的更正），實作前須補齊：
>
> - **GraphQL 查詢根為 `user(login:)`，不是 `organization(login:)`**。`opendiamonds` 是個人帳號（實測 `GET /orgs/opendiamonds` → 404）。
> - **`NOT_FOUND` 不得對應成「這張卡不在板上」**（即不得走 R-1.3 的零筆分支）。實測確認 GraphQL 的 `NOT_FOUND` **同時涵蓋「不存在」與「無權限」**，PRE-1 第三輪即因此誤判過一次。誤對應的後果是**權限退化時靜默走上補建分支且不會紅燈**。R-1.3 的零筆分支只能由「查詢成功且過濾後為零筆」進入。

## R-2 群：寫入前回讀（[Q2=A] 定案）

| # | 規則 |
| --- | --- |
| R-2.1 | `write_status` **必先** `read_item`；`actual != expected` → 回 `Aborted{actual, expected}`，**不送出寫入** |
| R-2.2 | `Aborted` **不開 issue**——開 issue 是 C-5 的職責（[ad:component-methods.md] 逐字） |
| R-2.3 | `Aborted` **不使 workflow 紅燈**（[ad:services.md] 的失敗語意） |

### R-2.4：回讀與寫入之間的競態（[Q2=A]）

Projects v2 **沒有 compare-and-swap**。`read_item` 與 mutation 是兩次獨立呼叫，中間存在一個視窗：協作者若正好在此期間改了看板，機制會用過期的比對結果送出寫入，把改動蓋掉。

**定案：接受這個視窗，不做額外處理。**

承接方式與其邊界：

> **先前此處宣稱「被蓋掉的改動會在下一輪反向同步被偵測到，[US:S-6] 的保護仍然成立、只是慢一輪」。該宣稱經 reviewer iteration 1 沿時間軸重演後**不成立**，已於 2026-08-29T15:23:54Z 更正。**
>
> 反證（每一步都可回頭核對）：
>
> 1. 機制回讀得到 `actual == expected`，視窗開始。
> 2. 協作者在視窗內把看板改成 **Y**。
> 3. 機制的 mutation 執行，把 Y 覆寫成機制的 `desired`（記為 **X**）。
> 4. **同一輪**內，U-6 的 R-5.4 緊接著把 `sync-state.json` 的 `managed_block_hash` 更新為 **X 的雜湊**。（R-5.4 現在確實會在寫入後回讀一次——2026-08-29T16:19:47Z 的更正——但**那次回讀發生在覆寫之後**，讀到的是機制自己剛寫的 X，不是協作者的 Y。步驟 4 的結論因此不變，只是理由由「沒有回讀」換成「回讀的時點在覆寫之後」。此句於送審前自檢更正，2026-08-29T23:42:35Z。）
> 5. 下一輪 U-8 反向同步讀看板現況（仍是 X）、算雜湊、與記錄的雜湊（也是 X）比對 → **相同 → 判定「無人為變更」**。
>
> **機制自己的回寫把比對基準重置成自己寫的值**，於是 Y 從未在雜湊層留下任何痕跡。反向同步不會被觸發，不是「慢一輪」，是**永遠不會**。

- **真實代價（更正後）**：在視窗內發生的協作者改動會被**靜默丟失**——沒有反向 PR、沒有紅燈、沒有通報。
- **每日對帳也不會發現**：對帳比的是「看板 vs record」，而覆寫後兩者一致，對帳判定為正常。
- **這個視窗不會有任何測試涵蓋**——重現它需要精準的時序。[Q2=A] 的選項本文已載明視窗本身，但**未載明「兜底不成立」**，那是本輪新查出的。

> **不得把「有回讀比對」讀成「寫入是原子的」。** R-2.1 擋掉的是**上一輪之後、本輪回讀之前**發生的改動；它擋不掉回讀之後的。兩者的差別就是這個視窗，而它**沒有兜底**。
>
> **裁定維持接受（[Q2=A] 的決定不改），但理由必須換掉**：先前接受它是因為「反向同步會兜底」，那個理由不成立；現在接受它的理由是——Projects v2 沒有 compare-and-swap，唯一的替代是樂觀鎖式的「寫後再回讀比對、不符就重試」，而那會把每次寫入的 API 呼叫數加倍並引入重試迴圈，對一個視窗寬度約為單次 mutation 往返時間的競態而言不成比例。**這個代價必須在 Bolt 1 的 gate 被揭露**，因為它是一條使用者從未被告知的真實資料遺失路徑。**已綁定到 ADR-0015 §2**，成為 Bolt 1 DoD 的一條揭露項（先前只在本檔寫「必須揭露」而未綁定任何 DoD 條目，reviewer iteration 2 Major，2026-08-29T16:20:29Z）。

## 本站對 PRE-1 的追加實測項（reviewer iteration 1 Critical）

> **R-1.0 先前只寫「必須被加進 PRE-1 的實測清單」，沒有走本 intent 已示範過的有效傳遞管道。** 已核可的 `delivery-planning/bolt-plan.md` 的 PRE-1 五項表（憑證權限／操作上限／`createProjectV2Field`／A-1~A-8／PRE-1-a）**不含**這一項，而 Bolt 1 的 DoD 只檢查 PRE-1 的第 1／3／4 項。後果：**Bolt 1 有真實機率在 `read_item` 的核心查找路徑完全未驗證的情況下被判 DoD 全綠，並依 deploy-on-merge 上線**——而 `write_status`／`create_item`／`write_field` 全部經過它。

**PRE-1-b（本站追加）**：以真實憑證對真實 issue 呼叫 `Issue.projectItems`，確認 (a) 該欄位存在且可查；(b) 回傳結果可依 Project id 過濾（R-1.2）；(c) 一個 issue 屬於多個 Project 時的回傳形狀符合 R-1.4 的假設。

**指派**：`delivery-planning/bolt-plan.md` 的 PRE-1 表與 **Bolt 1 的 DoD**。**確認人為 Bolt 0 的 gate**——它必須在 Bolt 1 開工前完成，否則本單元的全部實作建立在未驗證的假設上。

> **先前此處宣稱「形狀比照 ADR-A2 的先例，那個管道已被證明會被接住」——該宣稱經 reviewer iteration 2 逐字重讀 `bolt-plan.md` 後推翻（2026-08-29T16:20:29Z）：該檔仍只有五項 PRE-1，PRE-1-b 不在其中。**
>
> **先例不同構的原因是時序**：ADR-A2 寫在 `decisions.md`，而該檔產出於 delivery-planning **之前**，所以 `bolt-plan.md` 自然吸收；本 stage 跑在 `bolt-plan.md` **定稿之後**，單元產出內的「指派」沒有任何機制保證會被回頭執行。**在單元產出裡寫「指派 X」，對已定稿的上游而言是一張沒有收件人的便條。**
>
> **本項已改由 ADR-0015 §1／§2 承載**（先例為同 intent 的 ADR-0014——它同樣是在下游發現上游缺口後，以 ADR 作為修訂載體）。確認人維持 **Bolt 0 的 gate**。

## R-3 群：首建（`create_item`）

| # | 規則 | 來源 |
| --- | --- | --- |
| R-3.1 | 先檢查 record 是否已有綁定編號；有則**不建**、回既有值 | [US:S-1 AC 6] |
| R-3.2 | 目標 Project 不符 `Config` → 中止 | [req:FR-C2] |
| R-3.3 | 首建成功後**不自行回寫綁定編號**——回寫是 U-4 的職責 | [ad:component-methods.md] 的元件分工 |

**R-3.1 的失敗模式值得重述**：`requirements.md` 的 A-8 明記「回寫觸發分支假設同步身分對 feature 分支有寫入權且不受分支保護阻擋；**未驗證**」。回寫失敗 ⇒ 下次 push 又看不到綁定 ⇒ 再建一則 issue ⇒ **每 push 一次多一張卡**。R-3.1 是這條路徑上唯一的攔截，而它依賴的「record 已有綁定編號」正是回寫失敗時不存在的東西——**所以 R-3.1 攔得住 workflow 重跑，攔不住回寫失敗**。後者的真正防線是 U-4 的 `Rejected` 會紅燈 ＋ 通報。

## R-4 群：欄位寫入與建立

| # | 規則 | 來源 |
| --- | --- | --- |
| R-4.1 | `write_field` 失敗回 `Failed`，**不影響 Status 寫入** | [US:S-5 AC 2] 的不連坐 |
| R-4.2 | `ensure_field` 的三種可達失敗前提（憑證缺 Projects 寫入權／同名欄位型別不同／組織政策阻擋）任一者回 `CannotCreate` | [ad:component-methods.md] |
| R-4.3 | `CannotCreate` 交 C-5 通報「需人工建立欄位」，**不紅燈** | 同上 ＋ [ad:services.md] |

> **經 ADR-0016 §4.2 增訂 R-4.4：單選欄位的 name→id 解析**（2026-08-31T00:37:44Z）——本群**從未指定**單選欄位如何由名稱定位到 option，而實測顯示這不是實作細節而是規格缺口：
>
> | # | 規則 |
> | --- | --- |
> | **R-4.4** | 單選欄位一律以 **option id** 寫入，且該 id 必須**在執行期依 Project 解析**（讀該 Project 的欄位與選項，比對名稱取 id），**不得寫死**。實測 #16 與測試看板 #23 的同名選項 **option id 不同** |
> | **R-4.5** | 解析為**大小寫敏感**。實測 `singleSelectOptionId:"07486F86"`（僅大小寫不同）回 `VALIDATION: The single select option Id does not belong to the field`。名稱端的大小寫政策由本單元自行決定並明文記載——平台不提供 |
> | **R-4.6** | 每個單選欄位的解析是**額外一次讀取呼叫**，須計入操作次數估算 |
>
> 由來：`requirements.md` A-3 原假設「依欄位名稱設定單選欄位、名稱不分大小寫」，實測推翻——那是**框架便利層**行為，非平台行為。以名稱直接寫入回 `VALIDATION: Did not receive a single select option Id to update a field of type single_select`。見 `../decisions/0016-credential-topology-and-pre1-amendments.md`

> **經 ADR-0016 §1 更正 R-4.2 的一項失敗前提**（2026-08-31T00:37:44Z）：R-4.2 列的三種可達失敗前提中，**「組織政策阻擋」現已不可達**——`opendiamonds` 是個人帳號（實測 `GET /orgs/opendiamonds` → 404），**無組織即無組織政策**。該前提留在規則裡會成為一條永遠走不到、卻看起來被涵蓋的分支（`project.md` 的 `functional-design:c10`）。可達前提剩**兩種**：憑證缺 Projects 寫入權、同名欄位型別不同。
>
> **附帶實測**：`createProjectV2Field` 與 `updateProjectV2Field` **均可用**（PRE-1 第五輪，於符合 ADR-A3 條件的測試看板 #23），故 [US:S-5 AC 2] 確定走「可自動建立」那一支；`CannotCreate` 分支的可達前提因此收斂為上述兩種。

## R-6 群：受管區塊寫入（`write_body`，ADR-0015 §11 增設；本群補於 2026-08-30T01:31:09Z）

`write_body: (binding, block_text) -> WriteResult` 是本單元的第七個方法，也是**受管區塊唯一的持久化路徑**。先前本檔對它零規則（reviewer iteration 4 Group B M-4）。

| # | 規則 |
| --- | --- |
| R-6.1 | 寫入目標是 **issue body**，不是 Projects v2 的自訂欄位。兩者是 [ad:component-methods.md] §自訂欄位格式明文區分的東西（該欄位 ≤50 字元、「完整敘述一律在受管區塊」） |
| R-6.2 | **只覆寫受管標記界定的區塊**，issue body 的其餘內容（人寫的敘述）一字不動。標記為 U-2 擁有的兩個具名常數 **`MANAGED_BLOCK_BEGIN`／`MANAGED_BLOCK_END`**（定義見 U-2 `domain-entities.md`；本單元**引用**它們，**不得自建副本**——副本會落在 U-2 的 R-4 群互鎖之外）。這是 [req:FR-G4] 防迴圈與 [US:S-6] 的共同前提 |
| R-6.3 | body 內**無** `MANAGED_BLOCK_BEGIN` 時，把區塊**附加**在既有內容之後；有標記時**替換 `BEGIN` 到 `END` 之間（含兩者）的整段**。本方法**自行以字串搜尋定位**，不需要呼叫端傳入跨度、也不需要 `parse` 回傳跨度——`render` 的輸出一律含首尾標記，這是 U-2 的格式契約保證的 |
| R-6.6 | **找到 `BEGIN` 但找不到 `END`**（或順序顛倒）⇒ 視為 body 已損壞，回 `Failed` 並交 C-5 通報，**不猜、不附加**。附加會產生第二個 `BEGIN`，使下一輪的定位更不確定 |
| R-6.4 | 失敗回 **`Failed { http_status, message }`**（回傳值，非例外），與 `write_field` 同形；**不連坐 Status 寫入** |
| R-6.5 | **本方法不做長度截斷**。受管區塊無長度上限，`Config.field_max_length` 只約束自訂欄位 |

> **R-6.2／R-6.3 於 2026-08-30T02:47:00Z（依檔案 mtime 重建；原填 09:55:00Z 為未經 `date -u` 的編造值，已更正） 改寫（reviewer iteration 5 Group B C-1 Critical）。** 先前它們要求「只覆寫受管標記界定的區塊」「有標記則就地替換」，**但受管標記的語法在上游與全 stage 產出中從未定義**，而 C-6 的三個方法（`render`／`parse`／`content_hash`）無一回傳標記的字面或跨度。實作者只有兩條路：自己發明一個標記（在 U-3 產生第二份格式知識，落在 U-2 的 R-4 群互鎖之外），或卡住。
>
> **修法是把標記定義補在 U-2**（它擁有 C-6 的格式契約），本群改為引用兩個具名常數。**`parse` 的簽章因此一字未改**——`write_body` 用字串搜尋定位，不需要跨度。

> **`Failed` 的連帶後果必須被呼叫端看見**：該輪受管區塊未更新 ⇒ U-6 的 R-5.4 回讀取得的是**舊**雜湊（或 `null`）⇒ 若仍回寫 `SyncState`，比對基準就與看板現況脫鉤。**呼叫端的處置規則在 U-6 的 R-5.12**（逐欄回寫實際寫成功的部分——`write_body` 失敗時 `managed_block_hash` 維持原值、其餘欄位照常回寫），本群只負責如實回報失敗。

## R-5 群：權限邊界

| # | 規則 |
| --- | --- |
| R-5.1 | 本元件**不得**提供任何「推 commit 到 `ut`／`main`」的方法 |
| R-5.2 | 本元件**不得**提供任何「改 record 目錄以外的檔案」的方法 |

**R-5.2 的可觀察性有一個已標出的缺口**：[US:S-10 AC 5] 的兩個例子中，**只有「直推保護分支」可由分支保護產生真的 403**；「改 record 目錄以外的檔案」在本設計下**無機制可產生 403**——GitHub App 沒有路徑層級授權。候選機制是 Repository Rulesets 的 file-path restriction，已列 **PRE-1-a** 實測。

**不可行時的處置**：該 AC 需回 user-stories 改寫（依 `project.md` 的 `user-stories:c4`——把防禦意圖移到碰得到真實失敗面的層次）。**本單元不得以「介面不提供」為由把該 AC 標為通過**——[ad:component-methods.md] 已明文區分「介面不提供」與「嘗試時回 403」是兩件事。

## 與上游的對應

方法契約與錯誤處理引自 [ad:component-methods.md] §C-3；失敗語意（哪些紅燈）引自 [ad:services.md]；403 的半邊缺口與 PRE-1-a 引自 [ad:decisions.md] ADR-A2 與 [ug:unit-of-work.md] 的 U-3 實作註記；FR-C1／FR-C2／FR-F2 與 A-8 引自 `requirements.md`；S-1 AC 6、S-3 AC 1／2、S-5 AC 2、S-10 AC 5 引自 `stories.md` 與 [ug:unit-of-work-story-map.md]；元件分層引自 [ad:components.md]；獨立測試 Project 引自 ADR-A3。
