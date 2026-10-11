# 安全設計 — `U18 project-meta-data`

> 本站設計上游 `nfr-requirements` 定案的 `NFR8`（`NFR8.2`–`NFR8.5`）的**承載形式**，
> 並承擔本單元唯一適用的 ADR-0006 面向——**audit logging**。
> 本站**不複寫** `functional-design` 的 11 條規則（`team.md` 的單一真實來源）。
>
> 本單元的 `produces` 只有本檔與 `traceability.json`：`produces_kinds` 把
> performance／scalability／reliability／observability／logical-components 五項篩掉
> （它們的 kind 清單不含 `spec`）。

## 〇、上游依據

| 上游產出 | 本站用到它的什麼 |
|---|---|
| `security-requirements.md`（本單元） | `NFR8.2`–`NFR8.5` 四項二元判準（獨立腳本、大聲失敗、不動啟動路徑、`DEPLOY.md` 記步驟）；ADR-0006 四面向判定（audit logging **適用**，其餘三面不適用）；`OPEN-P2`／`OPEN-P4`／`OPEN-P5` |
| `tech-stack-decisions.md`（本單元） | 零技術增量；不建 ORM model 的兩項理由；驗證載體沿用 `U5` 的 `memory-schema` job 形狀，且**要求斷言涵蓋三態模型與四條外鍵** |
| `functional-spec.md`（本單元） | §二 三態模型；§三 對 `backend/database.py` 的實讀結果；§五 兩次 blocking 同步 |
| `rules.md`（本單元） | `BR1.1`–`BR1.5`（五個語意欄位）、`BR2.1`（可重跑）、`BR2.2`（COMMENT 義務）、`BR2.3`（**四條外鍵——本站指派修訂為三條**）、`BR3.1`（大聲失敗） |
| `entities.md`（本單元） | 三張表的欄位與 `entity_constraints`——**本站查出它少了九個欄位、且宣告零個索引**，見 §三、§四 |
| `contract-summary.md` | `K-15` 的 `foreign_keys`／`ddl_comment_requirement`／`blocking_sync`／`observable_side_effects`；`K-16`／`K-17` 的 facade 方法簽章（本站據以推導查詢形狀） |

## 〇之二、三個判為不適用的面向：本站同樣無 pattern，理由承接上游

| 面向 | 上游判定（`security-requirements.md` §二） | 本站 |
|---|---|---|
| **IAM** | 無增量（契約 `K-15` 逐字「DDL 不經使用者授權」），但本單元交付 per-project 授權的**資料基礎** | 無 pattern。授權判定屬 `K-16` 的 facade。**本站的 IAM 相關設計落在 §三**——`FR12.4b` 要求的「某人的 `project_admin` 是怎麼來的」屬稽核面而非授權面 |
| **Encryption** | 不適用（三張表無憑證／token／金鑰；`value` 是架構假設非個人機敏資料） | 無 pattern。**附帶一項已查證的事實見 §二之三**：腳本的失敗輸出不會洩漏連線憑證——這是查證結果，不是設計 |
| **Network exposure** | 不適用（零端點、零進程、零監聽埠；獨立腳本是手動 CLI 非服務） | 無 pattern。本站的設計也不新增任何監聽面 |

`functional-spec.md` §四「本單元**不**負責的事」是上述判定的依據。

## 一、`[ND1]`=A 的設計落地：三條外鍵 ＋ 一條刻意不設

**使用者裁決 `[ND1]`=A（2026-10-06T14:54:23Z）。** 本站把它落為下列 DDL 要求。

### 1.1 為什麼這件事需要設計而不是照抄

`BR2.3`（已核可）只說「四條外鍵必須存在且指向正確的表」。
`entities.md`、契約 `K-15` 的 `foreign_keys` 清單、`rules.md` 三處**都沒有提到
`ON DELETE`**——而 `U4` 已交付的 DDL 把它當成**必須逐條表態**的事項：

| `U4` 已交付的外鍵 | `ON DELETE` | 出處 |
|---|---|---|
| `systems.project_id → projects.id` | `RESTRICT` | `schema_rbac.sql:351` |
| `user_diagrams.system_id → systems.id` | `RESTRICT` | `schema_rbac.sql:384`；COMMENT（`:391`）逐字寫明理由 |
| `diagram_change_records.diagram_id → user_diagrams.id` | **`CASCADE`** | `schema_rbac.sql:395` |
| `projects.owner_user_id → users.id` | **刻意不決定** | `:330` 無子句；COMMENT（`:346`–`:347`）逐字「deliberately NOT decided (OQ-H1, landing U7)」 |

**慣例是：要嘛決定，要嘛在 COMMENT 寫明沒決定與落點。** 兩者皆無不是中立，是漏項。

而「稽核表的父列被刪時怎麼辦」在本 intent 已被用**兩種相反**的方式核可過
（`U4` 的 `diagram_change_records` 採 `CASCADE`；`U5` 的 `memory.memory_audit_events`
由使用者裁決 `[M1]`=A **完全不設外鍵**並以 `S8`／`S11` 鎖住存活）。
`reselection_events` 是第三張稽核表，所以沒有單一慣例可照——這是它必須被問的原因。

### 1.2 設計要求（落點 `code-generation` 的 DDL）

| 外鍵 | `ON DELETE` | 理由 |
|---|---|---|
| `project_members.project_id → projects.id` | **`CASCADE`** | 專案不存在時其成員關係無意義。採 `CASCADE` 也**避免弄壞已交付的程式**——見 1.3 |
| `project_members.user_id → users.id` | **不寫子句**（`NO ACTION`），並在 COMMENT 寫明承接 `OQ-H1` | 使用者硬刪除的行為**上游刻意未決**；`U4` 對 `projects.owner_user_id` 的處置逐字即此形狀，本單元沿用同一慣例而非自行決定 |
| `reselection_events.project_id` | **不設外鍵** | `[ND1]`=A。改選稽核在專案被刪後**獨立存活**（下節） |
| `system_requirement_fields.system_id → systems.id` | **`CASCADE`** | 系統不存在時其需求欄位值無意義。注意這與 `[UG:G9]`=A 不衝突：那條管的是**欄位定義**被移除時值列保留，不是系統被刪除 |

### 1.3 採 `CASCADE` 而非 `RESTRICT` 避開的具體後果

`hierarchy_service.delete_project()`（`:147`–`:162`，**`U7` 已交付**）只有兩道守門：

- `:153` `is_default` 為真即拒（`BR4.2`）
- `:156` 底下仍有系統即拒，訊息含剩餘系統數（`BR4.4`）

**沒有任何一道關於成員。** 而 `components.md:886` 逐字把 `ProjectMember` 的寫入端列為
「建立專案時的自動寫入 ＋ 邀請成功」——即 `U19` 落地後**每個新建專案至少有一列成員**。

若採 `RESTRICT`（或不寫子句，本情境下 `NO ACTION` 行為相同），`:161` 的
`db.delete(project)` 會在 `commit()` 丟出**未被捕捉的 `IntegrityError`**，
使用者看到 500 而非 `BR4.4` 那種帶訊息的 `HierarchyConflictError`。
**這是一條由新 DDL 引入既有程式的行為迴歸**，形狀與 `U7` 當初讓 `U4` 的四條 CHECK
在測試環境消失的那次相同。採 `CASCADE` 使 `delete_project` 的行為完全不變。

### 1.4 「不設外鍵」必須被兩條斷言鎖住，缺一不可

`U5` 已證實這一點：`S8` 驗**手段**（schema 上沒有外鍵），`S11` 驗**目的**
（刪除父列後稽核列仍然存在）。只有 `S8` 綠而 `S11` 紅會表示 `S11` 寫錯了。
本單元的對應兩條（落點 `code-generation` 的 CI 斷言）：

| id | 斷言 | 類別 |
|---|---|---|
| `P-FK0` | `reselection_events` 對 `projects` **沒有任何外鍵**（查 `information_schema.table_constraints` ＋ `constraint_column_usage`） | 結構 |
| `P-SURV` | 插入一列 `reselection_events` → 刪除其 `projects` 列 → 該稽核列**仍然存在** | 行為 |

**`P-SURV` 的前置條件**：刪除那列 `projects` 必須先滿足 `U4` 既有的兩道守門
（非預設專案、底下無系統），否則紅燈的原因會是守門而不是外鍵——
`U5` 的 `M1` 突變正是踩過「突變本身是 no-op」這個洞，故此處先寫明。

## 二、`NFR8`：獨立腳本的設計形狀

`[P1]`=A 在上游定下**要做什麼**（四項二元判準）。本站設計**怎麼做**，
並刻意與 `U4` 已交付的 `backend/scripts/run_hierarchy_migration.py` 保持同形。

### 2.1 單一交易，使退出碼可被信任

全部 DDL 包在**一個交易**內（PostgreSQL 的 DDL 可交易），於是：

> **退出碼 0 ⟺ 六個物件（五張表／三張新表 ＋ 其索引與約束）全部存在。**

`BR2.1` 的 `IF NOT EXISTS` 讓重跑安全，所以單一交易的價值**不在**可重跑，
而在**消除「部分成功而回報成功」這個狀態**。沒有它，一次中途失敗會留下
半套結構，而操作者從輸出看不出跑到哪裡。

### 2.2 自我終檢，使「跑過了」有意義

`U4` 的腳本在宣告成功前先驗自己的後條件（`:83` 逐字
「終檢通過：`user_diagrams` 中 `system_id IS NULL` 的列數為 0（`AC9.1.4`）」）。
本腳本沿用：commit 之前查 `information_schema` 確認三張表、其索引、
其 CHECK 與三條外鍵都在，任一缺即 rollback 並以非零碼結束。

**這不解決 `OPEN-P5`**（沒有機制保證有人去跑它），但它讓**一次成功的執行**
成為可信證據，而不只是「指令沒報錯」。

### 2.3 失敗輸出：已查證的事實與一項仍需遵守的要求

`U4` 的腳本在失敗路徑用 `traceback.print_exc(file=sys.stderr)`（`:69`）。
本站**實測**該路徑是否會把 `DATABASE_URL` 的憑證印出來——以假 URL
（`postgresql+psycopg://u360:<sentinel>@127.0.0.1:59999/db360`）觸發連線失敗並檢查
traceback 全文：

| 檢查 | 結果 |
|---|---|
| traceback 含密碼字串 | **否** |
| traceback 含使用者名稱 | **否** |
| traceback 含主機與埠 | 是（`connection to server at "127.0.0.1", port 59999 failed`） |

**所以沿用 `U4` 的 `traceback.print_exc()` 不會洩漏憑證**——SQLAlchemy／psycopg
在連線失敗訊息中已遮罩它。這一項**不是風險**，寫下來是為了讓下一個人不必重測。

仍然成立的要求（函式庫不保護的那一條路徑）：
**腳本自身不得輸出 `DATABASE_URL` 或其任何片段**，例如不得印
「正在連線到 `<url>`」這類進度行。要指出連線目標時只印主機與資料庫名。
理由是 `project.md` 的禁令（機敏資料不得寫進任何 log）與本 repo 為 public
且 Actions log 公開可讀。

## 三、Audit logging：本站唯一適用的面向，而本站在這裡查出缺口

### 3.1 `entities.md` 比 domain-design 少了九個欄位，其中六個正是稽核欄位

上游 `requirements.md:620` 判定 audit logging **適用**並點名兩處；
`FR12.4b`（`requirements.md:307`）逐字：

> 自動改選須留稽核：**誰、何時、對誰、舊角色、新角色**。**自動改選尤其必要**
> ——它由系統發起、無人按下按鈕，不留紀錄則事後無從得知某人的
> `project_admin` 是怎麼來的。

domain-design 把這五個事實實體化為 `ReselectionEvent` 的五個欄位
（`components.md:589` 的元件 `entities:` 區塊與 `:819` 的 Entity Ownership 表**兩處一致**），
而本單元的 `entities.md` 一個都沒有。逐實體實算（計數由
`scratchpad/u18_cols.py` 解析 `components.md` 的 Entity Ownership 表與
`entities.md` 的 yaml 區塊輸出，非手寫）：

| 實體 | domain-design 欄位數 | `entities.md` 欄位數 | 缺漏 | 缺漏欄位 |
|---|---|---|---|---|
| `ProjectMember` | 5 | 5 | **0** | — |
| `ReselectionEvent` | 7 | 2 | **5** | `promotedUserId`、`previousOwnerUserId`、`previousRole`、`newRole`、`occurredAt` |
| `SystemRequirementField` | 8 | 4 | **4** | `agentGroup`、`fieldKey`、`updatedAt`、`updatedBy` |

**合計 9 個。** 十七種拼法（camelCase ＋ snake_case）在整個
`construction/project-meta-data/` 目錄的命中數**全部為 0**——不是換了名字，是沒有。

### 3.2 為什麼這落在本站的面向上，而不是「不是我的欄位」

本單元自己的文字**承諾了**這些欄位能回答的問題，而它宣告的欄位集合答不出來：

| 本單元逐字寫的 | 宣告的欄位能答嗎 |
|---|---|
| `entities.md`：`clearedAt`「使清空動作可被稽核（**誰清**、何時清）」 | **只能答「何時」。** 唯一能答「誰」的 `updatedBy` 不在欄位集合裡 |
| `security-requirements.md` §二：「`reselection_events`（改選事件本身即稽核）」 | **否。** 只有 `project_id` ＋ `acknowledged_at` 的列記下「某專案發生過一次改選」，答不出誰拿到了管理權 |
| `security-requirements.md` §二 IAM 格：「改選選錯人等於把專案管理權給錯人」 | **事後無法查證選了誰**——這正是 `FR12.4b` 寫下理由的那個情境 |
| 契約 `K-17` 的 `clear_field` note 逐字：「保留列、`value` 設 null、記 `clearedAt` **與 `updatedBy`**」 | `updatedBy` 不存在，故契約的這一句目前不可實作 |

**被破壞的是一條已核可的 AC，而且可以指名。** `AC12.2.2`（`stories.md:777`）逐字：

> **Given** 我改了某人的角色，**When** 我檢視該成員詳情頁的變更紀錄，
> **Then** 它顯示**誰在何時把角色由什麼改為什麼** `[FR12.4b][FR12.4d][線框 §25]`

它的 Then 子句點名四件事——**誰**、**何時**、**由什麼**、**改為什麼**——
對應 `promotedUserId`／`occurredAt`／`previousRole`／`newRole`，
而這四個欄位**全在本站查出的缺漏清單裡**。
以 `entities.md` 現有的兩個欄位（`projectId` ＋ `acknowledgedAt`）建表，
成員詳情頁的變更紀錄**沒有任何內容可顯示**，`AC12.2.2` 永遠紅燈。

**而這條 AC 的歷史讓它更要緊**：`stories.md:781`–`:785` 記載 `[Q-11]`（Critical）
的處置逐字——使用者域唯一的稽核機制 `_audit_append` 寫 `logger.info`、
**UI 讀不到**，故實作「**不得**只沿用 `_audit_append`；需要一個可讀的持久層」，
並把「誰讀」那一腿指派 `domain-design`。

> **對齊修正（非本站新定案）**：上游兩處（`stories.md:782`、`unit-of-work.md:449`）
> 把 `_audit_append` 的位置寫成 `user_router.py:213`，而**本站開檔核對後**實際位置是
> **`:222`**（`:213` 的內容是 `username: str`）；`logger.info` 在 `:230`。
> **事實成立、定位偏 9 行。** 本站引用真實行號，**不回改**已核可的上游產出。
> 這與本 intent 另一處同形偏移（`user_router.py:673` 實為 `:682`）一致——
> `user_router.py` 在上游寫下這些引用之後長大了，故引用該檔的行號**一律須重驗**。
`domain-design` 確實交付了——`ReselectionEvent` 的七個欄位就是它的回應。
**斷點正好落在本單元的上游**：那七個欄位到 `entities.md` 只剩兩個。

另兩個（`agentGroup`／`fieldKey`）不是稽核欄位而是**身分**欄位，但它們的缺漏
使稽核也失去意義（不知道被清掉的是哪一個欄位），且使
`entities.md` 自己的 `entity_constraints`「同一系統內同一欄位名至多一列」
**無法建成**——該唯一約束指向一個未宣告的欄位。
`UnknownFieldKey`（契約 `K-17` 的 `raises`，對應 `AC11.2.2`）同樣沒有資料基礎。

### 3.3 處置：標出缺口並指派，不逕自改上游

依 `project.md`（「發現已核可上游的契約缺口時，處置形狀為：標出缺口、寫明它讓
哪一條 AC 目前不可滿足、指派具體落點與具體修法，**不逕自修改已通過 reviewer
的上游產出**」）：

| 缺口 | 目前不可滿足 | 指派落點 | 具體修法 |
|---|---|---|---|
| `ReselectionEvent` 缺五個稽核欄位 | `FR12.4b` 全條 **＋ `AC12.2.2`**（其 Then 的四件事對應四個缺漏欄位） | `code-generation`（`ALWAYS`，在游標之後） | DDL 直接依 `components.md:819` 的欄位清單建表；`entities.md` 的回補屬 `functional-design` 的修訂，由 `code-generation` 在 summary 中揭露 |
| `SystemRequirementField` 缺 `updatedBy` | `ADR-015` 的「誰清」；契約 `K-17` 的 `clear_field` note | 同上 | 同上 |
| 缺 `agentGroup`／`fieldKey` | `entity_constraints` 的唯一約束無法建成；`AC11.2.2` 的 `UnknownFieldKey` 無資料基礎 | 同上 | 同上；唯一約束為 `(system_id, agent_group, field_key)` |
| 缺 `updatedAt` | 無特定 AC，但寫入時間是 `K-17` 回傳形狀的一部分 | 同上 | 同上 |

**轉移目標不需要**：`code-generation` 是 `ALWAYS` 且在游標之後（本站的
`next_stage` 為 `Infrastructure Design`，`code-generation` 在其後），
故此指派不會落空。這一點是逐項查過 `aidlc-state.md` 的游標位置後寫下的，
不是憑 `execution` 欄推定——本 intent 已有三次指派給游標之前的站而落空的實例。

### 3.3.1 回補的九個欄位，三問的「誰寫」那一腿

`project.md` 記過「**『寫入端』是三問中最容易漏的一問**」，故逐一指名
（讀取端已在 §三之二 列出，清除端對稽核欄位不適用——稽核列本身不刪）：

| 欄位 | 誰寫 | 何時寫 |
|---|---|---|
| `promotedUserId`／`previousOwnerUserId`／`previousRole`／`newRole`／`occurredAt` | **`U19`**（契約 `K-16` 的自動改選；若 `OPEN-ND18-3` 決定一般化，則 `MembershipFacade` 的角色變更方法也寫它） | 自動改選執行時；人工角色變更時（視 `OPEN-ND18-3`） |
| `updatedBy`／`updatedAt` | **`U20`**（契約 `K-17` 的 `write_field` 與 `clear_field`） | 每次寫入或清空需求欄位值 |
| `agentGroup`／`fieldKey` | **`U20`**（同上；值由 `K-17` 的 `field_definition_source` 所述的**程式內常數**決定，非使用者輸入） | 同上 |

**三腿皆有歸屬，無懸空契約。** 本單元自己**不寫任何一列**
（契約 `K-15` 的 `observable_side_effects` 逐字「不含任何資料寫入」）。

### 3.4 `FR12.2` 的稽核在本 intent 沒有任何承載者

`requirements.md:620` 的 audit logging 格第 ② 項逐字：
「**`FR12.2`** 的角色指定同為授權變更，須留**同一組稽核欄位**」。

而 `FR12.2` 在 domain-design 與本單元的命中數**各為 0**。
`ReselectionEvent` 的欄位集合（`previousRole`／`newRole`／`occurredAt` …）
**恰好就是** `FR12.2` 需要的那一組，但該實體的名稱與描述都把它限定在
「`project_owner` 帳號被停用時**自動改選**的事件紀錄」。

**而一般化不只是「最便宜的正解」，它是一條已核可 AC 的要求**：`AC12.2.2`
的 Given 逐字是「**我改了某人的角色**」——那是**人工**的角色變更（`FR12.2`），
不是自動改選；而它的 When 指向「該成員詳情頁的**變更紀錄**」。
所以已核可的 AC 已經要求同一個變更紀錄同時承載人工與自動兩種角色變更，
而目前唯一為它建的實體在名稱與描述上只涵蓋後者。

**本站仍不自行決定表的語意範圍**——那是實體邊界的決定，屬 domain／functional
design。記為 `OPEN-ND18-3`，指派 `code-generation`（它必須在建表時決定
該表涵蓋哪些事件），並把上述 AC 依據一併交付供其判斷。

### 3.5 `reselection_events` 沒有保存期限，而這是刻意的

`U5` 的 `memory_audit_events` 有 90 天保存期（`NFR7.2`），本表**沒有**。
差別是對的：記憶稽核的母體是每日對話（無上界），而改選事件的母體是
「專案 owner 帳號被停用」（罕見）。`components.md:886` 逐字也已定下
「**清＝`acknowledgedAt`，事件列本身不刪**——這是刻意的，刪了就失去稽核」。

故本站**不**為它設計清除作業，並在此寫明理由，以免下一個人照 `U5` 的樣子
補一個 90 天清除而把 `FR12.4b` 的稽核清掉。

## 四、索引：唯一解，故不出成題目

`entities.md` 對「索引」「index」的命中數為 **0**——它宣告了兩個唯一約束與
四條外鍵，**零個索引**。而 `U4` 已交付的 DDL 是三條外鍵三個索引
（`schema_rbac.sql:336`／`:358`／`:388`），`models.py` 的六處 FK 欄位帶 `index=True`。
**PostgreSQL 不會自動為 referencing 欄位建索引**（它索引的是被參照的 PK）。

### 4.1 哪些查詢已經被唯一約束覆蓋（不是缺口，不要去「修」）

| 查詢（來源） | WHERE | 覆蓋者 |
|---|---|---|
| `resolve_project_role`（`K-16`，per-project 授權的唯一入口，最熱路徑） | `project_id = ? AND user_id = ?` | UNIQUE `(project_id, user_id)` ✓ |
| `list_members`（`K-16`） | `project_id = ?` | 同上，`project_id` 為前導欄 ✓ |
| `FR12.4` 自動改選挑選 | `project_id = ?` ＋ `ORDER BY joined_at, user_id` | 同上（過濾已覆蓋；排序的母體是單一專案的成員，量小） ✓ |
| `read_fields`（`K-17`） | `system_id = ?` | UNIQUE `(system_id, agent_group, field_key)` ✓ **但這個約束依賴 §三 的兩個缺漏欄位**——欄位沒回補，索引也不存在 |
| `project_members.project_id` 的 `CASCADE` 子側掃描 | 同第一列 | 同上 ✓ |

### 4.2 真正缺的那一個：`reselection_events` 完全沒有索引

`entity_constraints` 逐字「一個專案可以有多筆改選事件（每次改選一筆），
**故不可用專案做唯一鍵**」——這句話是對的，但它的後果是這張表
**連一個索引都沒有**，而它承載的是三張表中**頻率最高**的讀取：

`[M1]`=B 要求橫幅在**每次進入產品**時都看得到（`FR12.4c`），
故每一次落地頁載入都要查一次「這個人有沒有未確認的改選事件」。
欄位回補後的查詢形狀是 `WHERE promoted_user_id = ? AND acknowledged_at IS NULL`。

**設計決定**：建 partial index

```sql
CREATE INDEX IF NOT EXISTS ix_reselection_events_unack
  ON reselection_events (promoted_user_id) WHERE acknowledged_at IS NULL;
```

partial 的理由不只是省空間：**已確認的列會離開索引**，所以這個索引的大小
是「目前未確認的改選事件數」而非「歷來全部改選事件數」——而前者在正常運作下
趨近於零。本 repo 已有同一慣用法的先例（`schema_rbac.sql:341`
`uq_projects_default_per_owner ON projects (owner_user_id) WHERE is_default`），
故這不是新引入的手法。

另需 `ON (project_id)` 的普通索引供成員詳情頁的變更紀錄讀取
（`components.md:886` 逐字把 `ReselectionEvent` 的讀取端列為「橫幅、成員詳情的變更紀錄」）。

### 4.3 一個**目前不需要**、但要寫明何時會需要的索引

`project_members.user_id` **不是**任何索引的前導欄。它會在兩種情況下成為缺口，
兩者**本輪都不成立**，所以本站**不要求**建它：

1. **以成員身分列出「我參與的專案」**——`hierarchy_facade.list_projects`（`:231`）
   目前是 owner-scoped（`BR6.1`：只回傳 `owner_user_id` 等於請求者的列），
   這是 `[F8/R-02]`=「Owner-scoped now; flag membership as the known successor」
   的已核可結果。該後繼落地時這個索引才需要。
2. **使用者硬刪除時的外鍵子側掃描**——而使用者刪除行為是 `OQ-H1`，
   上游**刻意未決**（`schema_rbac.sql:346`–`:347` 的 COMMENT 逐字）。

寫下這兩個條件而不是直接建索引，理由是：**不需要的索引有寫入成本**，
而「以後可能要」不是現在建的依據。承接站 `U19`（成員服務，它擁有這兩條查詢路徑）。

## 五、ADR-0006 四面向：本站的增量

逐格對照上游 `security-requirements.md` §二 的同名表；**判定不同處已寫出理由**。

| 面向 | 上游判定 | 本站增量 |
|---|---|---|
| **IAM** | 無增量 | **無增量**（與上游相同）。授權判定屬 `K-16` 的 facade；本站只交付其資料基礎 |
| **Encryption** | 不適用 | **無 pattern**（與上游相同）。§二之三 的實測是查證結果而非設計，且結論是「不會洩漏」 |
| **Network exposure** | 不適用 | **無 pattern**（與上游相同）。獨立腳本是手動 CLI，不新增監聽面 |
| **Audit logging** | **適用** | **本站的實質產出**：① `[ND1]`=A 的落地——改選稽核不設外鍵並以 `P-FK0`／`P-SURV` 兩條斷言鎖住存活（§一）；② 查出九個缺漏欄位，其中六個正是 `FR12.4b`／`ADR-015` 點名的稽核事實，並指派回補（§三之一–三之三）；③ 查出 `FR12.2` 的稽核在本 intent 無任何承載者（§三之四）；④ 寫明本表**刻意沒有**保存期限的理由，以免被照 `U5` 的樣子補上清除作業（§三之五）；⑤ 橫幅查詢的 partial index（§四之二） |

**PBT 判定：N/A（非豁免）**，同上游兩站——本單元是 DDL，無任何函式。
**失效條件已指明且不變**：`U19` 的自動改選挑選函式應為不讀 DB 的純函式
（`unit-of-work.md:448`），PBT 在**那裡**適用，可失敗的性質是**排列不變性**
（`ORDER BY joined_at` 在時間戳相同時無穩定順序），而 `BR1.1` 是其資料層前提。

## 六、殘餘風險

1. **九個欄位的回補若在 `code-generation` 被漏掉，`FR12.4b` 整條無法滿足**，
   且**不會有任何測試或 sensor 抓到**——因為本單元的驗證載體是對 DDL 的斷言，
   而斷言是依 `entities.md` 寫的。`entities.md` 少了欄位，斷言就不會檢查它們。
   這與 `U5` 的 `occurredAt` 索引是同一個形狀：**缺口在規格裡，所以驗證也看不見它**。
   故記為 `OPEN-ND18-1`（`blocking-downstream`）。
2. **`BR2.3` 現為「四條外鍵」而設計已收為三條。** 已核可規則與本站設計不一致，
   處置是指派修訂（`OPEN-ND18-2`），**不回改** `rules.md`。
   風險是 `code-generation` 若只讀 `rules.md` 就會建出第四條外鍵，
   而那會讓 `P-FK0` 紅燈——**這一次缺口會被抓到**，與第 1 項相反。
3. **`FR12.2` 的角色變更稽核無承載者**（`OPEN-ND18-3`）。
4. **`OPEN-P5` 未改善**：沒有機制保證有人執行腳本。§二之二 的自我終檢讓
   *一次成功的執行*可信，但不讓「沒跑」變得可見。
   承接形式仍應是部署後的健康檢查而非把腳本塞進 `deploy.yml`
   （後者把資料庫結構變更放進自動部署路徑，屬 `project.md` 的 high-risk action 範圍）。
5. **`OPEN-P2` 承接**：`project_members.role` 與全域角色同名不同義，資料層無法強制區分，
   只能在 COMMENT 標明。
