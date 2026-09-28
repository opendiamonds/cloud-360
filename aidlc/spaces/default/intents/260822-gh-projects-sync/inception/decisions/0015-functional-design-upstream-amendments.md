# ADR 0015: functional-design 逐單元設計揭出的上游修訂集

- Status: Accepted
- Date: 2026-08-29（本檔建立於 2026-08-29T16:18:39Z；先前寫 2026-08-30 是以本地時區 UTC+8 記日，與 ADR-0013／0014 的 UTC 基準不一致，於 2026-08-30T00:48:38Z 更正）
- Amended: 2026-08-30（§11〜§14 新增；§8 補齊更正指令與閘門；§13 的 blocking 宣稱撤回並依 Q5=A／Q6=A 改寫）
- 節數：**14**
- Amends: **`delivery-planning/bolt-plan.md`** 的 PRE-1 表與 Bolt 1／Bolt 2 的 DoD、**`units-generation/unit-of-work-story-map.md`** 的 S-6 AC 5 歸屬、**`application-design/components.md`** 的 workflow 對照表（reconcile 補 C-4、reverse 補 C-5）、**`application-design/component-methods.md`** 的 **§C-3**（增設 `write_body`）／**§C-6**（`parse` 兩種 `null`、`Block` 增設 `rejection_notice`）／§C-7（`latency_samples` 擁有權）／§自訂欄位格式（`undecidable` 缺前綴）、**`requirements-analysis/requirements.md`** 的 NFR-S1／NFR-O2。原 Amends 行未含 §C-3／§C-6（2026-08-30T01:31:09Z 補，reviewer iteration 4 Group B m-3）。以下原文： 對照表、**`application-design/component-methods.md`** 的 `parse` 簽章與 §C-7 `latency_samples`、**`requirements-analysis/requirements.md`** 的 NFR-S1 驗收判準與 NFR-O2 目標值。各原文皆維持，本 ADR 只更正其中被本文點名的部分。

## Context

Construction 的 `functional-design` 對十二個單元逐一設計後，八個單元的並行對抗式審查揭出一組已核可上游的缺口。它們的共同形狀是**契約有一端懸空**——欄位有讀者沒有寫者、方法有定義沒有呼叫者、驗收標準有歸屬但該單元結構上做不到。

**本 ADR 存在的直接理由，是一個被實測推翻的傳遞假設。** U-3 的 PRE-1 追加項原本比照 `ADR-A2 → PRE-1-a` 的先例處置——在單元產出內標出缺口並指名落點，期待 `bolt-plan.md` 吸收。但 reviewer 逐字重讀 `bolt-plan.md` 後確認它**仍只有五項 PRE-1**，追加項不在其中。

**先例不同構的原因是時序**：ADR-A2 寫在 `decisions.md`，而 `decisions.md` 產出於 delivery-planning **之前**，所以 `bolt-plan.md` 自然吸收了它；`functional-design` 跑在 `bolt-plan.md` **定稿之後**，單元產出內的「指派」沒有任何機制保證會被回頭執行。

**在單元產出裡寫「指派 X，確認人為 Bolt N gate」，對已定稿的上游而言是一張沒有收件人的便條。** 本 ADR 是這些修訂唯一有效的承載形式，先例為同一 intent 的 ADR-0014。

## Decision

### 1. `bolt-plan.md` 的 PRE-1 表增列 **PRE-1-b**

以真實憑證對真實 issue 呼叫 `Issue.projectItems`，確認 (a) 該欄位存在且可查；(b) 回傳可依 Project id 過濾；(c) 一個 issue 屬於多個 Project 時的回傳形狀符合 U-3 的 R-1.4 假設。

**理由**：這是本 repo 第一次呼叫 Projects v2，而 U-3 的 `read_item` 全部建立在這條未實測的查找路徑上，`write_status`／`create_item`／`write_field` 又全部經過 `read_item`。**Bolt 1 的 DoD 現行只檢查 PRE-1 的第 1／3／4 項**，因此存在「核心路徑零驗證即依 deploy-on-merge 上線」的真實機率。

### 2. Bolt 1 的 DoD 增列兩條

- **PRE-1-b 已綠**。
- **揭露 `write_status` 回讀視窗的資料遺失路徑**：Projects v2 無 compare-and-swap，回讀與 mutation 之間的視窗內若有協作者改動，該改動會被**靜默丟失**——沒有反向 PR、沒有紅燈、沒有通報，每日對帳也不會發現（覆寫後看板與 record 一致）。U-3 的 R-2.4 接受這個取捨，理由是替代方案（寫後回讀比對＋重試）會讓 API 呼叫加倍且不成比例。**核可 Bolt 1 的人必須先看到這條路徑。**

### 3. Bolt 2 的 DoD 增列一條

對帳報告須能區分「今天沒處理到」與「今天處理了且一致」（U-7 的 R-3.4）。具體形式待 PRE-1 第 2 項實測 C-T5 之後決定，但**接手點在此登錄**。

### 4. `unit-of-work-story-map.md` 的 S-6 AC 5 歸屬由 U-8 改為 **U-6**

AC 5 要求「**受管區塊**載有一則記錄」，而 `components.md` 給 `aidlc-sync-reverse.yml` 的元件鏈是 `C-3(讀) → C-6(雜湊比對) → C-4(寫檔) → 開 PR`——**沒有任何一步寫回看板**。寫受管區塊的路徑只在正向同步上。原歸屬會讓該 AC 在兩個單元都落空。

### 5. `components.md` 的 workflow 對照表為 `aidlc-sync-reverse.yml` 補上 **C-5**

現行元件集合不含 C-5，使反向同步的外部失敗只會讓 workflow 紅燈而**不產生通報 issue**，[req:FR-E1]／[US:S-8 AC 1] 的「外部失敗 → issue」保證在該路徑上不成立。

### 6. `component-methods.md` 的 `parse` 簽章需能區分兩種 `null`

現行 `parse: (issue_body) -> Block | null` 讓「完全沒有受管標記」與「標記版本高於當前渲染器」回傳同一個值，使 U-2 的 R-3.4 所宣稱的「該 item 不被覆寫」**字面不成立**——而 ADR-A6 把這條路徑點名為本設計最危險的失敗模式。二選一：(a) 三態回傳；(b) 另加述詞 `has_managed_marker(issue_body) -> bool`。

### 7. `component-methods.md` §C-7 的 `latency_samples` 擁有權移出 U-7

NFR-P1 量測的是**事件觸發**路徑的延遲，而 U-7 是每日批次、沒有任何機制擷取「push 完成時刻」。二選一：(a) 擁有權移到 U-6；(b) `SyncState` 新增觸發時刻欄位由 U-6 寫、U-7 讀。**在此之前 U-7 不填該欄位，且不得以「本輪執行耗時」冒充。**

### 8. `requirements.md` 的 NFR-S1 驗收判準補上 ADR-0014 的指標

> **經 ADR-0016 §2 更正**（2026-08-31T00:37:44Z）：本節把權限集合更正為四項，**分項判斷仍然正確**，但它預設的授予機制（GitHub App 的細緻權限勾選）已不適用——實測確認 `opendiamonds` 是個人帳號，**無組織可授「組織層 Projects」**。本節第一項改讀作**個人帳號 Projects v2 讀寫**（由 `project` scope 承載），後三項由 `repo` scope 整包承載而**不可分別授予**。連帶使本節要求的「無額外授予」判準結構性不可滿足。見 `0016-credential-topology-and-pre1-amendments.md`。

該欄仍逐字寫「等於上述**兩項**，無額外授予」，而 ADR-0014 已把集合更正為三項。ADR-0014 自己的 Alternatives 段明文指出：**這條驗收準則會主動阻止正確的憑證**——照它鑄出的憑證缺 Issues 寫入權，且會通過 PRE-1。

> **附帶（本 ADR 新增，非 ADR-0014 涵蓋）**：權限集合實為**四項**——`deploy.yml:174-175` 在本 repo 上正在運行的設定把推分支（`contents: write`）與開 PR（`pull-requests: write`）分列兩行且各有註解。ADR-0014 修掉了「Issues 併入 Contents」這個歸併錯誤，但沒有掃描同一句話裡的另一個歸併（「開 PR」）。
>
> **更正指令（2026-08-30T00:48:38Z 補上；先前此段只陳述事實而未給任何指令或閘門，reviewer iteration 3 判 Major）**：
> 1. `requirements.md` 的 NFR-S1 —— 權限集合由「三項」改為**四項**（組織層 Projects 讀寫、repo 內容寫入、Issues 寫入、**Pull requests 寫入**），驗收判準的「等於上述**兩項**」同步改為「等於上述四項」。
> 2. `bolt-plan.md` 的 PRE-1 第 1 項 —— 「三項憑證權限」改為**四項**。
> **確認人：Bolt 0 的 gate**，且必須在憑證鑄造之前。理由與 §1／§2 相同：憑證一旦於組織層安裝，變更需要組織管理者操作（`external-dependency-map.md` E-1）。缺 `pull-requests: write` 的直接後果是 U-8 的反向 PR **開不出來**，而 U-8 的 R-6.3 會把它判為當場紅燈——症狀明顯，但發生在 Bolt 3、且修復要回到 Bolt 0 的憑證。

### 9. `requirements.md` 的 NFR-O2 目標值需重新表述

一致率分子含 `unparseable`／`whitelisted` 後，「目標為 0」在白名單記錄（`260802-default`）存在期間**結構性不可達**。二選一：(a) 目標改為「分子中不含 `mismatch` 類」；(b) `whitelisted` 退出分子。

### 10. 新增一條跨單元不變式：**render → GitHub → parse 的雜湊等價**

U-6 寫入受管區塊後記錄的 `managed_block_hash`，必須與 U-8 日後 `read_item → parse → content_hash` 算出的值**逐位元組相等**。若 `render()` 的輸出與「該字串被 GitHub 儲存後再 parse 回來的 `Block`」在正規化上有任何差異（換行、markdown 轉義、HTML 註解排版），兩者會**永久不相等**——於是在**沒有任何人為變更**的情況下，U-8 每天為每個受管 intent 各開一則反向 PR。

**這是 ADR-A6 點名的最危險失敗模式的另一個觸發條件**，且觸發者是機制自己每一次正常的寫入。**驗證落點指派 U-9 的第二段（端到端）**，本 ADR 同時要求 U-6 以**回讀取得**的雜湊為準（見 Consequences）。

### 11. `component-methods.md` §C-3 增設 **`write_body`** —— 受管區塊目前**沒有寫者**

**這是本輪兩組審查各自獨立抓到的同一個 Critical**（Group A C-3、Group B F1），也是本 ADR 全部十二項中唯一會讓整個反向同步子系統靜默失效的一項。

`render: (Decision, Context) -> string`（§C-6）產生受管區塊的文字，`parse: (issue_body) -> Block | null` 把它讀回，`content_hash: (Block) -> sha256` 算雜湊，U-8 的 R-1.1 拿它比對——**四個角色齊備，就是沒有任何方法把那段文字寫進 issue body**。§C-3 的六個方法逐一核對：`read_item`（回讀）、`create_item`（首建 item）、`write_status`（Status 欄）、`write_field`（**自訂欄位**寫入）、`ensure_field`（建欄位）、`read_issue_state`（issue 開關）——無一觸及 issue body。`write_field` 曾被 U-6 誤指為受管區塊的寫入路徑，但本檔 §自訂欄位格式（`component-methods.md:57-58`）明訂該欄位「長度上限 50 字元」且「**完整敘述一律在受管區塊**……兩處不一致時以受管區塊為準」——上游自己把兩者定義為不同的東西。

**後果鏈（每一環都可逐字核對）**：issue body 永遠沒有受管標記 ⇒ `read_item` 回傳的 `managed_block_hash` 恆為 `null` ⇒ R-5.4 每輪把 `null` 寫進 `SyncState` ⇒ U-8 的 R-1.1 拿 `null` 比 `null` 恆相同 ⇒ **反向同步（FR-G 全組、[US:S-6] 全部 AC）永遠不觸發**；同時 [US-OQ-3] 的必載內容、[req:FR-F3] 的 `[S]`／`— SKIP` 差別、[req:FR-G4] 的防迴圈第一道防線、以及 §12 的 AC 5 告示鏈，**全部沒有載體**。

**決定**：§C-3 增設

| 方法 | 簽章 | 目的 | 錯誤處理 |
| --- | --- | --- | --- |
| `write_body` | `(binding, block_text) -> WriteResult` | 把受管區塊寫進 issue body（[req:FR-G4]、[US-OQ-3] 的唯一載體） | 與 `write_field` 同形：回傳值而非例外；失敗回 `Failed`，**不連坐 Status 寫入** |

**為什麼不出成選擇題**：受管區塊在 GitHub issue body 內，只能經 API 寫入；§C-3 是本設計唯一碰 GitHub API 的元件（`components.md`），故落點無第二個候選。所需權限 `Issues: write` 已在 ADR-0014 的集合內，不擴大權限面。依 `project.md`（`requirements-analysis:260822-ra-c5`），單一可行解不做成假選擇，改為在此揭露。

**呼叫者**：U-6（正向同步是唯一寫受管區塊的路徑）。**寫入順序**：`write_status` → `write_field` → **`write_body`** → 回讀 `read_item` 取 `managed_block_hash`（§10）。**U-3／U-6 的產出須同步更正**「受管區塊由 `write_field` 寫」這處誤述。

### 12. `Block` 增設 `rejection_notice` 欄位，並確認它是一次 `format_version` bump

[US:S-6 AC 5] 要求「受管區塊載有一則記錄，指出該次人工改動未被採納與其時間戳」。承接鏈為 U-6 的 R-6.2b 填 `Context.rejection_notice` → U-2 的 R-1.5 渲染。**但 `Block` 的六個欄位裡沒有任何一個承載它**——於是「告示經由 `Block` 進入 `content_hash` 涵蓋範圍」這個宣稱沒有依據，而該宣稱正是「告示不會被 U-8 誤讀為人為變更」的唯一保證（reviewer iteration 3 Group B F2）。

**決定**：`Block` 增設 `rejection_notice: { closed_at: ISO 8601 } | null`，與 `Context` 同名同型。連帶：

- **這是一次格式變更**，依 ADR-A6 與 U-2 的 R-4 群三道互鎖，須 bump `format_version` 並在**同一個 PR** 內重新基準化全部既有 item。
- 因此 **R-1.5 先前宣稱的「`null` 支輸出與引入前逐字相同」不成立且已撤回**（Group B F3）：`format_version` 內嵌於區塊文字且在雜湊涵蓋範圍內，bump 之後所有既有 item 的雜湊必然改變。兩個宣稱不可同真，保留的是 bump——因為「不 bump」會讓新舊渲染器對同一段文字給出不同的 `Block`，那正是 ADR-A6 點名的最危險失敗模式。
- **交付綁定**：§11 的 `write_body`、本節的 `Block` 欄位、U-2 的 R-1.5、U-6 的 R-6.2 必須**同批交付**（皆屬 Bolt 1）。任何一項單獨上線都會讓 AC 5 在該期間不成立，而 `write_body` 缺席時整條鏈連載體都沒有。

### 13. `components.md` 的 reconcile 元件鏈補上 **C-4** —— 回讀守門的唯一可行修法

`write_status(binding, expected: ItemState, desired: Status)` 內部「必先回讀」並與 `expected` 比對，不符即回 `Aborted`（§C-3、[req:FR-C1]）。**這條守門的全部價值取決於 `expected` 代表「機制上次寫進去的值」**——[req:FR-C3] 逐字：「後到者的回讀比對會偵測到前者已寫入的結果」；`stories.md:237` 同義。

**但 `SyncState` 會過期**：`components.md` 給 `aidlc-sync-reconcile.yml` 的元件鏈是 `C-7 →（內部）C-2／C-1／C-3／C-5`——**沒有 C-4**，於是 U-7 補平看板之後無法持久化任何欄位，`SyncState` 停在補平前的舊值，下一輪 U-6 必然判為不符並開一則**假通報**。functional-design 的 iteration 2 曾試圖改由「當下 `read_item`」取得 `expected` 來迴避，但那讓比對恆真、`Aborted` 不可達（iteration 3 C-1 Critical）——把假陽性換成了所有真陽性一起消失。

**決定**（人工裁決，`U-6/functional-design-questions.md` 的 Q5=A，2026-08-30T00:57:28Z）：`aidlc-sync-reconcile.yml` 的元件集合補上 **C-4**。U-7 補平看板後，比照 U-6 的 R-5.4 回寫 `SyncState`（至少 `last_status`／`last_field_value`／`last_reason_code`／`last_synced_at`，以及若該輪重寫過受管區塊則含 `managed_block_hash`）。`expected` 的正本因此回到 `SyncState` 三欄，守門恢復。

**被否決的替代方案**：
- **U-6 在 `actual != expected` 時加一層「`actual == desired` 即視為已補平」**：零上游變更，但殘留一個真實漏洞——U-7 補平為 X' 後 record 又變為 X''，三者互異，仍是假 `Aborted`。
- **U-7 不補平、只報告**：過期問題消失，但直接推翻已核可的 Bolt 2 信心假說（「落差會被每天發現**並補平**」）與 [US:S-9]／FR-D 的補平要求，範圍遠大於缺陷本身。

**代價**：reconcile 每日多一次 commit+push。`deploy.yml` 只在 PR merge 進 `ut` 或手動 `workflow_dispatch` 觸發，故**不觸發部署**；會被觸發的是 `ci.yml`，而 U-10a 已為 `sync-state.json` 設計 `paths-ignore`，沿用即可。**確認人為 Bolt 2 的 gate**（U-7 於該 Bolt 交付）。

**排程分支的落點（Q6=A 人工裁決，2026-08-30T01:31:09Z）**：

先前本節把這一項標為 **blocking**，理由是「`commit_and_push` 只推觸發分支 ＋ R-3.1 不得推 `ut`／`main` ⇒ U-7 無合法推送落點」。**該推導錯誤，已撤回**（reviewer iteration 4 Group A M-1）：「只推觸發分支」是**呼叫方式的描述、不是方法的內建限制**——`branch` 本來就是 `commit_and_push` 的參數，而這正是 U-8 推自建 `aidlc-sync/reverse/*` 分支合法的前提（`U-4/business-rules.md` 的 R-3.1 註記已如此定案）。推送落點從來就有。

**真正的問題在讀取端**，且是 reviewer 指出、本 ADR 先前沒想到的反向風險：`schedule` 只在預設分支觸發，本 repo 預設分支實測為 `main`，而 `main` 落後於整合主幹 `ut`——若不處理，reconcile 會拿**過期的 record** 去比看板，一致率與補平判定全部失真。

**決定**：`actions/checkout` 明訂 `ref: ut`。workflow 定義仍由預設分支讀取（GitHub 硬限制，無法繞過），但讀寫的 record 與推送分叉點全部是 `ut`。規則落點為 U-7 的 **R-7 群**（R-7.1 釘 `ref: ut`、R-7.2 推自 `ut` 分叉的自建分支、R-7.3 把 `ut` HEAD SHA 寫進報告以便事後查核、R-7.4 同樣適用於 U-8）。**使用者原話：「不應該在main上跑」。**

**被否決**：把預設分支改成 `ut`（會動到 PR 預設 base、branch protection、`ci.yml`／`deploy.yml` 觸發條件與所有現有 gh-aw 排程，需別開 ADR）；改用外部排程器觸發（引入 repo 外的新依賴與憑證，`external-dependency-map.md` 的 E-1〜E-4 不含它）。

**`SyncState` 落後的來源不只 U-7 補平**（reviewer iteration 4 Group A C-1）：U-6 自己的 `commit_and_push` 回 `Rejected`、或 R-5.4 的回讀拋 `ExternalError`，都會留下「看板已寫成功但沒記錄」。修復落點為 U-7 的 **R-6.5**——它有 U-6 沒有的第三個座標（record），故能在「看板 == record 而 `SyncState` ≠ 兩者」時判定那是遺失的回寫而非人為改動。**不可把這個判定放進 U-6**：它在事件路徑上無法分辨兩者，合併處理正是本 ADR §13 起因的那個守門恆真形狀。

**確認人為 Bolt 2 的 gate**（U-7 於該 Bolt 交付），已於 `bolt-plan.md` 的 Bolt 2 DoD 就地登錄。


### 14. `component-methods.md` §自訂欄位格式的前綴集合缺 `undecidable` 的對應

前綴為**四選一**（無／`parked @ `／`skipped `／`frozen: `）。會走到 `write_field` 的 `reason_code` 有四種，逐一對照後 `mapped`（無）、`parked`（`parked @ `）、`suppressed`（`frozen: `）皆有對應，**唯獨 `undecidable` 沒有**——`skipped ` 對應的是 `[S]` 標記（scope 內被跳過），與「訊號不落在對照表任一列」是兩回事。

`undecidable` 本身是 U-7 在缺口 G-1 標出、由 functional-design 新增的 `reason_code`（[US:S-2 AC 4] 要求對帳報告有「無法判定」清單，而 `ReconcileReport` 只有 `unparseable`）。這個前綴缺口是它的直接後果，上游來不及涵蓋。

**決定**：前綴集合增列第五項供 `undecidable` 使用，具體字面待實作期與 §12 的 `format_version` bump 一併定（兩者同屬受管區塊／自訂欄位的格式契約，同一個 bump 內處理最省）。**在它落地之前，`undecidable` 的自訂欄位行為未定義——實作不得自行猜一個前綴**，那會讓一個格式契約在沒人核可的情況下擴張。**確認人為 Bolt 1 的 gate**。

## Consequences

- **PRE-1 由五項增為六項**，Bolt 0 的成本略增；相對於「Bolt 1 才發現核心查找路徑不可用」，可忽略。
- **第 2、3 點讓兩個 Bolt 的 DoD 各多一條**，其中 Bolt 1 那條是**揭露**而非技術檢查——它要求核可者看見一條真實的資料遺失路徑，這是刻意的。
- **第 10 點的處置改變了 U-6 的實作成本**：`managed_block_hash` 改以寫入後的 `read_item` 回傳值為準，而非對 `render()` 的輸出直接計算。代價經實算為**每個進入寫入鏈的 intent 需 2 次 `read_item`**（`write_status` 內部的回讀比對一次、R-5.4 的寫入後回讀一次），相對於修正前的 1 次是 **2 倍**（先前寫「多一次讀取」，2026-08-30T01:31:09Z 重算）。**R-5.10 (b) 支例外**——`unparseable`／`whitelisted` 不產生任何看板寫入，一次也不讀。無漂移的 intent 完全不進寫入鏈。換得的是與 U-8 的計算路徑**完全相同**，等價性由構造保證而非由假設保證。
- **第 6、7、9 點都留了兩條候選修法而未定案**——它們需要的是實作期或下一輪設計的資訊，此處只鎖定「必須解決」與「在哪個閘門確認」。
- **第 11 點是唯一會讓子系統靜默失效的一項**：沒有它，反向同步不是「慢」或「偶爾漏」，而是**永遠不觸發且沒有任何紅燈**——比對基準與被比對值同為 `null`。它也解釋了為什麼前兩輪 reviewer 都沒抓到：`managed_block_hash` 的**寫者**缺口在 iteration 1 被抓到並修好了，而受管區塊**本身**的寫者缺口被那次修正掩蓋（舊版 R-5.4 對 `render()` 輸出直接算雜湊，讓 `render` 的輸出至少有一個消費者；改為回讀取值之後，`render` 的輸出在整份設計中再無任何具名去處）。
- **第 12 點使本批修訂含一次 `format_version` bump**，成本落在 Bolt 1：bump 與重新基準化必須同 PR（ADR-A6／U-2 R-4 群），而 Bolt 1 正是首次上線、既有受管 item 數為 0，**這是這次 bump 最便宜的時點**——延後到任何後續 Bolt 都要付重新基準化全部 item 的代價。
- **本 ADR 不改任何已核可 artifact 的原文**，一律以指標方式更正，與 ADR-0013、ADR-0014 的做法一致。**但「指標」必須真的存在於被修訂的檔案裡**——reviewer iteration 3（Group B F5）實測本 ADR 被 `Amends` 點名的五份上游檔中回指 `0015` 的處數為 **0**，而對照組 ADR-0014 在 `bolt-plan.md` 有 1 處、`requirements.md` 有 2 處。**這使本 ADR 一度成為它自己 Context 段所批評的那張便條，只是升了一層。** 已於 2026-08-30T00:48:38Z 在五份檔案就地補上指標，補法與 ADR-0014 的既有先例逐字同形。

## Alternatives Rejected

- **維持在單元產出內「標出＋指派」，不開 ADR。** 已被實測否決：`bolt-plan.md` 逐字重讀後仍無 PRE-1-b。時序決定了這條路不通——單元產出寫在上游定稿之後，沒有讀者。
- **逐項各開一份 ADR。** 本 ADR 現有 **14 節**（初版十節，functional-design 的 iteration 3／4 各再揭出兩節）——它們的共同根因是同一個（契約有一端懸空），且多數共用同一個確認閘門；拆開會讓 14 份 ADR 各自缺少「這是一組系統性缺口」這個最重要的脈絡。
- **回頭直接編輯 `bolt-plan.md` 與 `components.md` 等已核可產出。** 違反本專案「不逕自修改已通過 reviewer 的上游產出」的紀律；ADR 正是為此存在的修訂載體。
- **把第 10 點的等價性當成假設寫進 assumptions 而不指派驗證。** `project.md` 已有明文教訓：設計 artifact 承認某組合是「已知風險」時，必須把最壞情境實際畫進範例再判定可否接受——而這個最壞情境（每天為每個 intent 開一則 PR）顯然不可接受。

## Risk

- **第 1、2、8 點必須在 Bolt 0 之前生效**：憑證一旦鑄出並安裝於組織層，變更需要組織管理者操作（見 `external-dependency-map.md` 的 E-1）。
- **第 10 點若在 Bolt 1 才發現不成立**，影響範圍是全部受管 intent 且症狀是每日增生 PR——屬於會被立刻看見、但清理成本高的失敗。U-9 在 Bolt 4 才上線，故本 ADR 要求 U-6 直接採用回讀取得的雜湊，**不等 U-9 驗證**。
