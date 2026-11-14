# Rules — `U3 rbac-story-ids`（`spec`）

<!-- Stage: functional-design（Construction 3.1）· Unit: rbac-story-ids · kind: spec -->

> **⚠ 本檔有修訂 1（2026-10-04）**：新增 `BR5`–`BR7` 與 `BR4.5` 共 16 條、取代 `BR3.4`／`BR4.1`–`BR4.4`
> 共 5 條，合併後 **32** 條規則，`authorization` 類別由 0 變為 **3**。
> 下方第一個 YAML 區塊與其摘要表為**修訂前原文**（16 條，矩陣 330 列）。
> **讀本檔請一併讀文末的「修訂 1」段**，兩個 YAML 區塊合併讀取、id 重複者以修訂 1 為準。

下方 YAML 區塊是本檔的 source of truth；其後的摘要表為衍生視圖。

```yaml
rules:

  # ── BR1 群：K1（統一入口頁）的語意與預設值 ────────────────────────

  - id: BR1.1
    statement: >
      K1 的 22 列中屬於它的 11 列，其 can_view 為 true 者恰為八個角色：
      Project_Architect、Developer、Project_Editor、Project_Admin、
      FinOps_Analyst、Security_Reviewer、Platform_Admin、Platform_Owner；
      其餘三個角色（SRE、Ops_Lead、Platform_Engineer）的列存在但三個旗標皆 false。
    category: constraint
    applies_to: RolePermission（story_id = K1 的 11 列）
    trigger: 預設矩陣被寫入或被重建時
    logic: >
      IF role ∈ {上列八個角色} THEN can_view = true
      ELSE can_view = false（列仍必須存在，見 entities.md EC-2）
    violation_behaviour: >
      少寫任何一列 → 矩陣不完整，權限頁在該格出現破洞，且 user_can 對該
      (role, K1) 回 false 但原因無法與「刻意不給」區分。
      多給三個維運角色任何一個 → BR1.3 的可達性保證同時被破壞。
    source: FR1.8；本站 Q2=A

  - id: BR1.2
    statement: K1 的 can_edit 與 can_review 在全部 11 列皆恆為 false。
    category: constraint
    applies_to: RolePermission（story_id = K1）
    trigger: 預設矩陣被寫入或被重建時
    logic: IF story_id = K1 THEN can_edit = false AND can_review = false
    violation_behaviour: >
      給任一列 can_edit = true 會經由 user_can 的 OR 語意（entities.md EC-3）
      隱含開啟 view，使該角色事實上持有 K1——若該角色屬 BR1.1 的三個不持有者，
      BR1.3 立刻被破壞，而畫面上看不出來。
    source: >
      本站 Q1（使用者重新框定為「Figma 不一定是對的，可以重新設計」）。
      依據為上游零雙態需求：FR1.8 與 US1.4 四條 AC 只談「持不持有」；
      mockups.md:117 逐字記載無權限者的入口頁「不可達」，與唯讀入口頁相斥。

  - id: BR1.3
    statement: >
      **可達性保證**：至少一個持有 A1 view 的正式角色不得持有 K1。
    category: constraint
    applies_to: 預設矩陣整體
    trigger: 預設矩陣被寫入或被重建時；任何一次 K1 預設值的後續調整
    logic: >
      IF 存在 role 使得 user_can(role, 'A1', 'view') = true
         AND user_can(role, 'K1', 'view') = false
      THEN 保證成立 ELSE 違反
    violation_behaviour: >
      AC1.4.2 的 Given「不持有入口頁權限但持有架構圖權限」變成不可構造，
      該 AC 成為永遠不會失敗的死碼。這**正是** AC1.4.4 被改寫要消除的缺陷類型
      （stories.md:107–112 逐字記載：原 Given 在預設 seed 下不可達，因為
      11 個角色全部具備 A1 view）。
      違反時不會有任何錯誤訊息——測試照樣綠燈，因為它測不到東西。
    source: >
      user-stories 審查 R-01（品質工程師 QA-3，Major）提出的 seed guard。
      該建議未落入 US1 的 DoD（DoD 只列 allow/deny 測試與 schema 同步），
      本規則是它在本單元的落點。
    note: >
      BR1.1 的當前值使本規則成立（三個不持有者都有 A1 view）。
      本規則獨立於 BR1.1 存在，是為了讓**日後調整 K1 預設值**時這條限制仍被檢查。

  - id: BR1.4
    statement: >
      本單元只保證 K1 這個 story id 存在且其列有預設值；**任何授權判定、
      落地順序與畫面呈現都不屬於本單元**。
    category: policy
    applies_to: 本單元的範圍邊界
    trigger: 下游單元引用 K1 時
    logic: >
      IF 需求是「判斷某人能否進入口頁」或「決定 / 導向哪裡」
      THEN 落點為 U14 entry-page-ui，經既有 require_story_action 與
           DefaultRedirect；本單元不提供任何端點或判定函式
    violation_behaviour: >
      若在本單元加入判定邏輯，會製造第二條授權路徑，違反 FR9.5 逐字的
      「不得有任何繞過該 dependency 的路徑」。
    source: K-03 的 behaviour_semantics.authorization_responsibility 逐字

  # ── BR2 群：K2（專案／系統階層）的語意與預設值 ────────────────────

  - id: BR2.1
    statement: K2 的 can_view 在全部 11 列皆為 true。
    category: constraint
    applies_to: RolePermission（story_id = K2）
    trigger: 預設矩陣被寫入或被重建時
    logic: IF story_id = K2 THEN can_view = true
    violation_behaviour: >
      不給 view 的角色看不到自己的架構圖歸屬於哪個專案／系統，
      脈絡列（US2 整群）對該角色顯示不出三元組。
    source: 本站 Q3=A

  - id: BR2.2
    statement: >
      K2 的 can_edit 為 true 者恰為四個角色：Project_Architect、
      Project_Editor、Project_Admin、Platform_Admin。其餘七個為 false。
    category: constraint
    applies_to: RolePermission（story_id = K2）
    trigger: 預設矩陣被寫入或被重建時
    logic: >
      IF role ∈ {Project_Architect, Project_Editor, Project_Admin, Platform_Admin}
      THEN can_edit = true ELSE can_edit = false
    violation_behaviour: >
      全給 → AC9.2.3 的 Given「不具備該權限」不可構造，該 AC 成為死碼
      （與 BR1.3 同一類缺陷，只是落在 K2 上）。
      全不給 → US9.2 的身分「架構設計者 [P-1]」無法建立專案，整則故事無法達成。
    source: 本站 Q3=A
    note: >
      Platform_Owner 不在其中是刻意的：它在既有 28 個 story id 上全為 v--
      （全域唯讀），給它 K2.edit 會打破該一致形狀。此判斷以本站實算的
      DEFAULT_ROLE_PERMISSIONS 矩陣為據，非印象。

  - id: BR2.3
    statement: >
      K2.edit 同時涵蓋建立、修改、刪除三種操作，不再細分。
    category: policy
    applies_to: U7 對 projects／systems 的寫入類端點
    trigger: U7 實作任一寫入端點時
    logic: >
      IF 操作 ∈ {建立, 修改, 刪除} THEN 閘門為 require_story_action('K2', 'edit')
    violation_behaviour: >
      若為刪除另設閘門（無論走 can_review 或 service 層），
      前者挪用 can_review 的既有語意（A3 的 Security_Reviewer 審核），
      後者直接違反 FR9.5 逐字的「一律經 require_story_action」。
    source: >
      ADR-004 的 Alternatives Rejected 已拒絕拆成三個 story id；本站 Q4=A

  - id: BR2.4
    statement: K2 的 can_review 在全部 11 列皆恆為 false。
    category: constraint
    applies_to: RolePermission（story_id = K2）
    trigger: 預設矩陣被寫入或被重建時
    logic: IF story_id = K2 THEN can_review = false
    violation_behaviour: >
      can_review 的既有語意是「審核」，目前只有 A3 的 Security_Reviewer 使用
      （矩陣中唯一 can_review = true 的列）。在 K2 挪用它會讓權限頁該欄的標籤
      對不同列代表不同意思，而畫面上沒有任何跡象顯示這件事。
    source: 本站 Q4=A

  # ── BR3 群：寫入端與冪等 ───────────────────────────────────────

  - id: BR3.1
    statement: >
      新增的 22 列必須由 ensure_missing_role_permissions 寫入。
    category: constraint
    applies_to: 啟動路徑的 seed 行為
    trigger: 應用程式啟動時
    logic: >
      IF (role, story_id) 在 role_permissions 中不存在
      THEN INSERT 該列（取 DEFAULT_ROLE_PERMISSIONS 的值）
      ELSE 略過，不 UPDATE、不 DELETE
    violation_behaviour: >
      既有環境的 role_permissions 非空，K1／K2 的列永遠不會出現，
      而應用程式**不會報錯**——user_can 對缺列回 false（rbac.py:150–151），
      所以現象是「所有人都沒有入口頁權限」，而不是一個可辨識的錯誤。
    source: K-03 的 forbidden 段；ADR-004 Consequences
    note: >
      本站查證：該函式已存在於 rbac.py:84–111，且**已被 database.py:171–175
      在啟動時呼叫**。故本單元在這一項上不需新增機制，只需讓 22 列進入
      DEFAULT_ROLE_PERMISSIONS。
      歧義只出在 K-03：它把該函式列為本單元的 provides.writer，單看那一欄會讀成
      要新建。ADR-004 的 Consequences 段**已經寫對**——它逐字引用 rbac.py:84–111
      這個行號區間，明示該函式既有。
      （審查 R-01 更正：原文寫「上游的措辭會讓人以為要新建」，把兩份上游文件
      一概而論，而較具決策權威的那一份並沒有錯。）

  - id: BR3.2
    statement: >
      禁止依賴 ensure_role_permissions_seeded(force=False) 讓新 story id 生效。
    category: constraint
    applies_to: 啟動路徑的 seed 行為
    trigger: 任何「讓預設矩陣生效」的程式路徑
    logic: >
      IF 表非空 THEN 該函式整段 no-op 並回 0（rbac.py:63–65）
      THEREFORE 它對「既有環境新增 story id」永遠無效
    violation_behaviour: 同 BR3.1——靜默失效，無錯誤訊息。
    source: K-03 的 forbidden 段逐字
    note: >
      對照：同檔的 force=True 路徑會先 DELETE 全表再重寫
      （rbac.py:66–67），那會**清掉管理者在權限頁做過的所有調整**。
      本單元不使用該路徑，但 user_router.py:885 存在一個以 force=True
      呼叫它的端點——K1／K2 進入 DEFAULT_ROLE_PERMISSIONS 後，
      該端點的重置目標會一併包含新兩欄，這是正確的，記此以免被誤讀為缺陷。

  - id: BR3.3
    statement: >
      寫入必須可重複執行且不覆寫既有列，故每次啟動呼叫皆安全。
    category: constraint
    applies_to: ensure_missing_role_permissions 的行為
    trigger: 每次應用程式啟動
    logic: >
      IF 列已存在 THEN 不動它（即使其旗標與 DEFAULT_ROLE_PERMISSIONS 不同）
    violation_behaviour: >
      若改為覆寫，管理者在權限頁對 K1／K2 做過的調整會在下次重啟時被靜默
      還原成預設值。
    source: K-03 的 behaviour_semantics.retry_and_idempotency 逐字

  - id: BR3.4
    statement: 本單元完成後，預設矩陣恰為 330 列（11 角色 × 30 個 story id）。
    category: validation
    applies_to: DEFAULT_ROLE_PERMISSIONS
    trigger: 測試與 CI
    logic: >
      IF len(DEFAULT_ROLE_PERMISSIONS) ≠ 330 OR 存在缺漏的 (role, story_id) 組合
      THEN 視為違反
    violation_behaviour: >
      列數對但組合有缺漏時，缺的那格在權限頁是破洞而總數看起來正常——
      故檢查必須同時驗總數**與**組合完整性，只驗總數會漏掉這種情形。
    source: ADR-004 的 Decision 段（實算 308 + 11 × 2）

  # ── BR4 群：同步義務（blocking） ──────────────────────────────

  - id: BR4.1
    statement: >
      22 列的預設值必須同步寫進 schema_rbac.sql 的 role_permissions seed 區塊。
    category: policy
    applies_to: 交付條件
    trigger: DEFAULT_ROLE_PERMISSIONS 有任何異動
    logic: >
      IF seed 語意變更 THEN schema_rbac.sql 必須同步，否則空 volume 建出的
      新環境與程式內的預設值不一致
    violation_behaviour: project.md ## Mandated 判定為 blocking，階段不得標示完成。
    source: project.md ## Mandated；K-03 的 sync_obligations
    note: >
      **檔頭指示的那支產生腳本不存在**（本站查證，審查後補入）。
      rbac_seed_data.py 的檔頭逐字寫「由 schema_rbac.sql 產生的預設
      role_permissions 列（勿手改；改 SQL 後重跑產生腳本）」，但全樹搜尋
      rbac_seed_data 只命中 rbac.py（import 它）、該檔自身、測試與 codekb 文件——
      backend/scripts/ 下只有 dump_openapi.py、dump_ws_contract.py、
      run_hierarchy_migration.py，**沒有任何 seed 產生器**。
      故「先改 SQL 再重新產生 Python」照字面不可執行；實際做法是兩邊人工同步，
      而這正是 BR4.4 存在的理由。
      ---
      **schema_rbac.sql 內另有一處既存漂移**（本站查證，審查後補入）：
      第 759 行的驗證註解寫 `-- 352`，但該檔 INSERT INTO role_permissions 區塊
      本站逐列實算為 **308** 列（11 角色 × 28 story id），與檔頭第 12 行的
      「預設矩陣（308 列）」一致。352 不知其來源，且照它去驗會誤判 seed 壞掉。
      本單元把總數改為 330 時，**三處都要改**：檔頭第 12 行、第 759 行的驗證註解、
      以及 DEPLOY.md 第 594／613 行的「約 308」。第 759 行是順手修掉既存錯誤，
      不是本單元造成的。

  - id: BR4.2
    statement: >
      DEPLOY.md 的權限矩陣說明必須同步反映 330 列與兩個新 story id。
    category: policy
    applies_to: 交付條件
    trigger: 同 BR4.1
    logic: IF seed 語意變更 THEN DEPLOY.md 必須同步
    violation_behaviour: 同 BR4.1，blocking。
    source: project.md ## Mandated；K-03 的 sync_obligations

  - id: BR4.3
    statement: >
      K1 與 K2 必須有對應的功能標籤，否則權限頁與註冊功能摘要出現無名稱的列。
    category: constraint
    applies_to: user_router.py 的 STORY_FEATURE_LABELS
    trigger: 新增 story id 時
    logic: >
      IF story_id 不在 STORY_FEATURE_LABELS THEN _feature_label 回 None
      （user_router.py:242–246），該列在摘要中沒有名稱
    violation_behaviour: >
      不會報錯，只是畫面上出現一個沒有名字的權限列。
    source: >
      本站查證 user_router.py:60–88 得到；**上游三份文件（ADR-004、K-03、
      unit-of-work.md）皆未記載此相依**。

  - id: BR4.4
    statement: >
      同一個 PR 必須新增一支測試，斷言 schema_rbac.sql 的
      INSERT INTO role_permissions 區塊與 rbac_seed_data.py 的
      DEFAULT_ROLE_PERMISSIONS **逐列等值**（相同的 (role, story_id) 集合，
      且每一列的三個旗標相同）。
    category: policy
    applies_to: 交付條件
    trigger: 本單元往兩份 seed 副本各加 22 列時
    logic: >
      IF 兩份副本的 (role, story_id, can_view, can_edit, can_review) 集合不相等
      THEN 測試失敗
    violation_behaviour: >
      兩份副本會無聲漂移。失敗模式是**環境相依**且不會報錯：從 schema_rbac.sql
      建的新環境拿到 SQL 那份的值，既有環境經 ensure_missing_role_permissions
      拿到 Python 那份的值，兩者不同時沒有任何閘門會紅燈，
      而現象是「同一個角色在不同環境有不同權限」。
    source: >
      team.md ## Code Style 的「單一真實來源」逐字：「若確實無法避免（如跨語言
      邊界），新增副本的同一個 PR 必須一併新增鎖住兩者一致的測試；無法寫測試的
      副本不新增。」本站查證：**目前沒有任何測試做這件事**——backend/tests/ 下
      提及 schema_rbac 的三個檔（test_j3a_view_permission.py、
      test_vector_extension_bootstrap.py、test_hierarchy_migration.py）驗的都是
      別的東西；test_collab.py:79 雖 import DEFAULT_ROLE_PERMISSIONS 但用途無關。
      本條為審查後補入（審查未提出，屬本站自查）。
    note: >
      可行性已確認：兩份都是可被 Python 解析的純文字，
      U4 的 test_schema_rbac_sql_matches_migration_ddl 已有「解析 schema_rbac.sql
      再比對程式內定義」的既有樣板，零新依賴。
      落點為 code-generation，測試檔沿用 backend/tests/ 的既有 unittest 形狀。
```

## 規則摘要（衍生自上方 YAML）

| ID | 類別 | 一句話 |
|---|---|---|
| `BR1.1` | constraint | `K1` 給八個角色，三個維運／平台角色的列存在但全 `false` |
| `BR1.2` | constraint | `K1` 的 `can_edit`／`can_review` 恆 `false` |
| `BR1.3` | constraint | **至少一個有 `A1` view 的角色不得持有 `K1`**，否則 `AC1.4.2` 成死碼 |
| `BR1.4` | policy | 本單元只保證 story id 存在，判定與落地都不在此 |
| `BR2.1` | constraint | `K2.can_view` 給全部 11 |
| `BR2.2` | constraint | `K2.can_edit` 給四個角色，其餘七個 `false` |
| `BR2.3` | policy | `K2.edit` 涵蓋建立／修改／刪除，不細分 |
| `BR2.4` | constraint | `K2.can_review` 恆 `false`，不挪用審核語意 |
| `BR3.1` | constraint | 寫入端為 `ensure_missing_role_permissions`（已存在且已被啟動路徑呼叫） |
| `BR3.2` | constraint | 禁止依賴 `ensure_role_permissions_seeded(force=False)`（表非空時整段 no-op） |
| `BR3.3` | constraint | 寫入冪等且不覆寫既有列 |
| `BR3.4` | validation | 完成後恰 330 列，且須同時驗組合完整性 |
| `BR4.1` | policy | `schema_rbac.sql` 同步（**blocking**） |
| `BR4.2` | policy | `DEPLOY.md` 同步（**blocking**） |
| `BR4.3` | constraint | 補 `STORY_FEATURE_LABELS` 兩個標籤（**上游未記載的相依**） |
| `BR4.4` | policy | 新增測試鎖住兩份 seed 副本逐列等值（`team.md` 單一真實來源要求，**目前零測試**） |

**類別實算**：constraint 10、policy 5、validation 1、authorization 0、calculation 0（合計 16）。

`calculation` 為 0，故本單元**不適用** ADR-0006 的 property-based testing hard
constraint——該約束點名的三個模組（IaC generator、cost calculator、agent routing）
不含本單元，且這裡沒有任何值域性質可寫成 property。判定為 **N/A 而非豁免**。

`authorization` 為 0 是刻意的，不是遺漏：本單元**定義**授權資料，
**不執行**授權判定（`BR1.4`）。判定規則屬 `U7`／`U14`。

---

# 修訂 1（2026-10-04）— `K3`／`K4` 的規則，與四條既有規則的取代

<!-- 本段為 append。上方 BR1–BR4 的原文**不回改**。下方第二個 yaml 區塊與上方
     第一個**同格式、合併讀取**；被取代的條目以 supersedes 明寫，取代後以本區塊
     為準。合併手法與 `components.md` 的 `Part A''` 相同。 -->

```yaml
# ── 修訂 1：與上方 rules 區塊合併讀取 ──────────────────────────────
# 合併規則：id 不重複者直接併入；id 重複者以本區塊為準（supersedes 欄位明寫）。

rules_amended:

  # ── BR5 群：K3（專案成員管理）的語意與預設值 ──────────────────────

  - id: BR5.1
    statement: >
      K3 的 11 列中，can_view 為 true 者恰為八個角色：Project_Architect、
      Developer、Project_Editor、Project_Admin、FinOps_Analyst、
      Security_Reviewer、Platform_Admin、Platform_Owner；其餘三個角色
      （SRE、Ops_Lead、Platform_Engineer）的列存在但三個旗標皆 false。
    category: constraint
    applies_to: RolePermission（story_id = K3 的 11 列）
    trigger: 預設矩陣被寫入或被重建時
    logic: >
      IF role ∈ {上列八個角色} THEN can_view = true
      ELSE can_view = false（列仍必須存在，見 entities.md EC-2）
    violation_behaviour: >
      少寫任何一列 → 矩陣不完整，權限頁在該格出現破洞；user_can 對該
      (role, K3) 回 false 但原因無法與「刻意不給」區分。
      給滿 11 個 → BR5.3 的可達性保證被破壞，AC12.5.1 成為死碼。
    source: 修訂 1 Q5=A
    note: >
      持有者集合與 K1（BR1.1）**逐字相同**。這是刻意的：它使「誰是這個產品裡的
      專案參與者」在全域層只有一個答案。

  - id: BR5.2
    statement: >
      K3 的 can_edit 為 true 者恰為四個角色：Project_Architect、Project_Editor、
      Project_Admin、Platform_Admin。其餘七個為 false。
    category: constraint
    applies_to: RolePermission（story_id = K3）
    trigger: 預設矩陣被寫入或被重建時
    logic: >
      IF role ∈ {Project_Architect, Project_Editor, Project_Admin, Platform_Admin}
      THEN can_edit = true ELSE can_edit = false
    violation_behaviour: >
      少給任一個 → BR5.4 的硬約束被破壞（見該條）。
      全給 → AC12.5.1 在「邀為專案管理者」那條路徑上不可構造（BR7.2）。
    source: 修訂 1 Q5=A
    note: >
      此集合與 K2.can_edit（BR2.2）相同，而 K2.edit 的持有者就是「能建立專案」
      的集合——這正是 BR5.4 成立的原因。

  - id: BR5.3
    statement: >
      **可達性保證**：至少一個持有 A1 view 的正式角色不得持有 K3 的任何旗標。
    category: constraint
    applies_to: 預設矩陣整體
    trigger: 預設矩陣被寫入或被重建時；任何一次 K3 預設值的後續調整
    logic: >
      IF 存在 role 使得 user_can(role, 'A1', 'view') = true
         AND user_can(role, 'K3', 'view') = false
      THEN 保證成立 ELSE 違反
    violation_behaviour: >
      AC12.5.1 的 Given「一位沒有對應全域功能權限的使用者」變成不可構造，
      該 AC 成為永遠不會失敗的死碼；AC12.5.3（拒絕不留半套狀態）連帶失效，
      因為它的 Given 是「一次因缺少全域權限而被拒絕的邀請」。
      違反時不會有任何錯誤訊息——測試照樣綠燈，因為它測不到東西。
    source: >
      與 BR1.3 同一形狀，落在 K3 上。BR1.3 的由來是 user-stories 審查 R-01
      的 seed guard；本條是本修訂依同一判準自行加上的。
    note: >
      BR5.1 的當前值使本規則成立：SRE／Ops_Lead／Platform_Engineer 三者皆持有
      A1 view（本站以腳本實算複驗，11 個角色全部具備 A1 view）。
      本規則獨立於 BR5.1 存在，是為了讓日後調整 K3 預設值時這條限制仍被檢查。

  - id: BR5.4
    statement: >
      **凡持有 K2.can_edit 的角色必須持有 K3.can_edit。**
    category: constraint
    applies_to: 預設矩陣整體
    trigger: 預設矩陣被寫入或被重建時；K2 或 K3 預設值的任何後續調整
    logic: >
      IF user_can(role, 'K2', 'edit') THEN user_can(role, 'K3', 'edit') 必須為 true
    violation_behaviour: >
      該角色能建立專案（K2.edit 涵蓋建立，BR2.3）、依 FR12.1 自動成為該專案的
      project_admin，卻因缺 K3.edit 而在全域層被擋住每一個成員管理動作——
      AC12.1.2 逐字「Given 我剛建立一個專案，When 我嘗試邀請成員，Then 該動作
      可用——**不需任何額外授權步驟**」直接失敗。
      現象是「我建的專案，我管不動」，而權限頁上看不出原因（兩層串聯的失敗層
      不會被標示出來）。
    source: >
      本修訂從 `stories.md` 的 AC12.1.2 ＋ `requirements.md` 的 FR12.6（兩層串聯：
      「全域 role_permissions（能不能用這個功能）與 per-project 角色（能不能碰這個
      專案的資料），任一層不過即拒」）推導而得，**不是偏好**。
      它是修訂 1 Q5 的硬約束，寫在題幹而非選項裡。
    note: >
      反向不成立：持有 K3.edit 而不持有 K2.edit 是允許的（例如日後讓某個角色
      只管成員、不建專案）。本條只約束單向蘊含。

  - id: BR5.5
    statement: >
      本單元只保證 K3 這個 story id 存在且其列有預設值；**成員關係本身的判定、
      per-project 角色的解析與畫面呈現都不屬於本單元**。
    category: policy
    applies_to: 本單元的範圍邊界
    trigger: 下游單元引用 K3 時
    logic: >
      IF 需求是「判斷某人在某專案是什麼角色」或「能不能邀請／移出」
      THEN 落點為 U19 membership-service 的 MembershipFacade（K-16），
           全域層由其 router 的 require_story_action 承擔；
           畫面落點為 U24 member-pages-ui
    violation_behaviour: >
      若在本單元加入判定邏輯，會製造第二條授權路徑；K-16 的
      authorization_model.sole_entry 逐字為 MembershipFacade。
    source: 與 BR1.4 同一形狀；K-16 的 authorization_model

  # ── BR6 群：K4（需求欄位）的語意、把關範圍與預設值 ────────────────

  - id: BR6.1
    statement: >
      K4 的 can_view 為 true 者恰為 BR5.1 的同八個角色；SRE、Ops_Lead、
      Platform_Engineer 三列三旗標皆 false。
    category: constraint
    applies_to: RolePermission（story_id = K4 的 11 列）
    trigger: 預設矩陣被寫入或被重建時
    logic: 同 BR5.1，story_id 換為 K4
    violation_behaviour: >
      少寫 → 矩陣破洞。給滿 11 個 → BR6.5 的可達性保證被破壞。
    source: 修訂 1 Q6=A

  - id: BR6.2
    statement: >
      K4 的 can_edit 為 true 者恰為 BR5.2 的同四個角色（建立者集合）。
    category: constraint
    applies_to: RolePermission（story_id = K4）
    trigger: 預設矩陣被寫入或被重建時
    logic: 同 BR5.2，story_id 換為 K4
    violation_behaviour: >
      全給 → 任何角色都能改架構假設（SLA／TPS／預算），與 team.md 的 C1 既有
      先例相反（逐字「估價區域與每日時數同屬架構假設：由架構師設定／修改，
      非該角色 API 403」）。
      全不給 → US11.2／US11.3 的填寫動作無人可執行，兩則故事無法達成。
    source: 修訂 1 Q6=A

  - id: BR6.3
    statement: >
      **K4 把關的範圍限於需求籤與其欄位的讀寫**，不涵蓋專案／系統清單頁、
      建立頁與總覽籤——後三者由 K2 把關。
    category: policy
    applies_to: U23 project-pages-ui 的路由守衛與 U20 的 router
    trigger: U23／U20 實作可見性把關時
    logic: >
      IF 畫面 ∈ {清單頁, 建立頁, 總覽籤} THEN 把關為 K2
      IF 畫面 = 需求籤 OR 操作 ∈ {讀欄位, 寫欄位} THEN 把關為 K4
    violation_behaviour: >
      若照 K-19 的字面把整個專案頁掛在 K4 之下，K4 與 K2.view（已給全部 11）
      在全域層完全重複，[UG:G8]=C 的「全域邊界最細」整個落空；
      且三個維運角色（有 K2.view、無 K4）會看不到專案頁，而 BR2.1 給他們
      K2.view 的理由逐字是「不給 view 的角色看不到自己的架構圖歸屬於哪個
      專案／系統」——專案頁正是看那件事的地方，兩條規則會在同一個畫面上抵消。
    source: >
      修訂 1 Q6=A。**這是對齊修正，不是本站新定案**：K-19 的
      behaviour_semantics.authorization_responsibility 逐字為「頁面自身的可見性
      把關由 K-03 的 K4 story id 承擔」，而它的 test_target_surface.routes 是
      「專案／系統清單頁、建立頁、專案詳情頁（總覽／需求／記憶摘要三籤）」
      ——即整個專案頁；而 [UG:G8]=C 逐字只說「需求欄位對應 K4」。
      兩者皆已核可且互相矛盾，本站依 Q6=A 定錨為後者。
      依 `refined-mockups:c3` **不回改** contract-summary.md，在此就地記明。

  - id: BR6.4
    statement: >
      不持有 K4 的使用者在總覽籤**不顯示**「未填需求欄位」計數（整個指標隱藏，
      不是顯示 0）。
    category: constraint
    applies_to: U20 的回應契約與 U23 的總覽籤
    trigger: 總覽籤載入時
    logic: >
      IF NOT user_can(role, 'K4', 'view')
      THEN 回應不含 unfilled_count，畫面不渲染該指標
    violation_behaviour: >
      顯示 0 會與 AC11.3.3（「欄位全部已填時顯示 0」）無法區分——同一個畫面
      上的 0 代表兩件相反的事。顯示真實數字則讓他看得到數字卻看不到明細
      （需求籤被 K4 擋住），AC11.3.1／AC11.3.2 的一致性斷言在他身上無法驗證。
    source: >
      修訂 1 Q6=A 的作答後果，**本站新增的明訂**。上游沒有任何一條規則處理
      「有 K2 無 K4」這個組合——它是 Q6=A 把兩個畫面掛在不同 story id 上之後
      才出現的狀態。
    note: >
      落點是 U20 的端點契約（K-17 的 read_fields 回傳 unfilled_count），不是前端
      ——依 units-generation 對 U20 的注意事項，兩處計數必須由同一次查詢推導。

  - id: BR6.5
    statement: >
      **可達性保證**：至少一個正式角色不得持有 K4 的任何旗標。
    category: constraint
    applies_to: 預設矩陣整體
    trigger: 預設矩陣被寫入或被重建時；任何一次 K4 預設值的後續調整
    logic: >
      IF 存在 role 使得 user_can(role, 'K4', 'view') = false
      THEN 保證成立 ELSE 違反
    violation_behaviour: >
      BR6.4 本身成為不可觸發的死碼（沒有人處於「有 K2 無 K4」的狀態），
      而它正是本修訂新增的規則。
    source: 修訂 1 Q6=A
    note: >
      BR6.1 的當前值使本規則成立（三個維運角色全 false）。
      注意：AC11.4.1 的 deny 側（agent 經 MCP 讀「我無權存取的專案」）
      **不依賴本規則**——它的 Given 是 per-project 非成員，由 K-16 的
      resolve_project_role 回 None 構造，與全域層無關。本條保護的是 BR6.4。

  # ── BR7 群：加入時與自動改選的全域層檢查（修訂 1 Q7=A）──────────

  - id: BR7.1
    statement: >
      邀請一位使用者為**一般成員**時，全域層檢查 K3.can_view；不持有者
      邀請被拒。
    category: authorization
    applies_to: U19 的邀請操作（K-16 的 MembershipFacade）
    trigger: 邀請動作送出時，在任何寫入之前
    logic: >
      IF NOT user_can(invitee_role, 'K3', 'view') THEN 拒絕邀請，不寫入任何列
    violation_behaviour: >
      成員列被寫入但該成員進來什麼都看不到——這正是 [RA-2] 的 A 選項
      （已被否決）所描述的情形，而 FR12.6a 選的是 C（不得被邀請）。
    source: >
      `requirements.md` 的 FR12.6a（逐字「缺少對應全域功能權限的使用者不得被邀請
      加入專案；邀請動作須被拒絕並說明原因」，`[RA-2]`=C）；修訂 1 Q7=A。
      定位：撰寫時為 requirements.md:514–369，**行號會隨上游修訂衰減，以 FR 編號
      為錨**（本 record 已有 26 個相異行號、77 處引用因上游修訂而失效的實例）
    note: >
      user_can 的 view 是 OR 語意（entities.md EC-3），故持有 K3.edit 者
      自動通過本檢查。

  - id: BR7.2
    statement: >
      邀請一位使用者為**專案管理者**（或把既有成員的角色改為專案管理者）時，
      全域層檢查 K3.can_edit；不持有者該操作被拒。
    category: authorization
    applies_to: U19 的邀請與角色變更操作
    trigger: 指定或變更 per-project 角色為 project_admin 時，在任何寫入之前
    logic: >
      IF 目標 per-project 角色 = project_admin
         AND NOT user_can(target_role, 'K3', 'edit')
      THEN 拒絕，不寫入
    violation_behaviour: >
      他成為 project_admin 但每一個管理動作都被全域層擋成 403——
      AC12.4.3 的已核可文案「系統自動把管理權交給你」對他為假，
      而畫面上看不出原因（兩層串聯不會標示失敗的是哪一層）。
    source: >
      修訂 1 Q7=A；疊加於 `requirements.md` 的 FR12.6 兩層串聯之上
    note: >
      AC12.2.1（把一般成員改為專案管理者）的 Given 因此需要一位持有
      K3.edit 的目標使用者；AC12.2.4（兩位管理者都能執行管理動作）同理。

  - id: BR7.3
    statement: >
      自動改選（FR12.4）的候選集合**只含持有 K3.can_edit 的成員**。
      若該專案沒有任何符合的成員，**擋下停用**並要求先指定接手人。
    category: authorization
    applies_to: U19 的自動改選路徑與既有停用端點的前置檢查
    trigger: 一位 project_admin 被停用時
    logic: >
      candidates ← {m ∈ members(project) | m ≠ 被停用者 AND user_can(m.role, 'K3', 'edit')}
      IF candidates = ∅ THEN 擋下停用（回 409 並列出受影響的專案）
      ELSE 依 AC12.4.2 的決定性挑選規則選出一位
    violation_behaviour: >
      若不過濾候選集合，被選中者可能只有 K3.view，於是他收到橫幅
      「系統自動把管理權交給你」卻管不動——與 BR7.2 同一個失敗模式，
      但更糟：它由系統發起，沒有任何人按下按鈕可以被告知失敗。
    source: >
      修訂 1 Q7=A；`requirements.md` 的 FR12.4（自動改選）為其觸發來源
    note: >
      「擋下停用」沿用 [M3]=A 已核可的形狀（擋下並要求先指定接手人），
      與既有停用端點的前置檢查是**同一個閘門**——依 [US:D-06] 與
      project.md 的 functional-design:c34，守門必須位在三條路徑的共同上游，
      本條不是第四個獨立檢查。
    alignment_correction: >                  # 審查 R-01（Major）的處置，格式比照 BR6.3
      **本條窄化了一條已核可的驗收標準，在此明寫**：`stories.md` 的 AC12.4.1 逐字為
      「**Given** 某專案的 owner 帳號**已被系統管理者 [P-4] 停用**且該專案另有成員，
      **When** 系統自動改選，**Then** 被選中者為該專案**最早加入**的成員」
      ——「最早加入的成員」**沒有任何資格限定詞**。本條把候選集合窄化為
      「最早加入**且持有全域 K3.edit**」的成員。
      ---
      **可構造的反例**（審查指出，本站以腳本重算角色集合後寫下）：
      11 個角色中 **7** 個不持有 K3.edit
      （Developer、FinOps_Analyst、SRE、Ops_Lead、Platform_Engineer、Security_Reviewer、Platform_Owner）；
      其中 **3** 個在 BR5.1 之下連 K3.view 都沒有
      （SRE、Ops_Lead、Platform_Engineer），故**真正落在「可合法成為一般成員、但不可成為管理者」
      的是 4 個**：Developer、FinOps_Analyst、Security_Reviewer、Platform_Owner。若某專案最早加入的非 owner 成員是
      其中之一，AC12.4.1 的字面應選中他，而本條會跳過他改選下一位持有 K3.edit 者，
      或在無人符合時走 BR7.3 的第三種結果（擋下停用）——那是 AC12.4.1 字面
      從未涵蓋的結果。
      ---
      **為什麼仍然採用本條而不改回字面**：不窄化的後果是被選中者成為 project_admin
      後每個管理動作都被全域層擋成 403，而 AC12.4.3 的已核可文案逐字
      「系統自動把管理權交給你」對他為假，且該路徑**沒有任何人按下按鈕**可以被告知
      失敗（這正是 BR7.3 存在的理由，見上方 violation_behaviour）。
      ---
      **處置**：依 `refined-mockups:c3` **不回改** stories.md，在此就地記明為對齊修正，
      並登記為交接事項 H-11（見 functional-spec.md §七′），指派 AC12.4.1 的擁有者
      （`user-stories`，但位於游標之前；真正的承接站為 `code-generation`，ALWAYS）
      於下一次觸達時收斂或更正驗收標準原文。
      ---
      **修訂 1 Q7 的揭露缺口，如實記載**：Q7=A 的選項只向使用者揭露了「挑選純函式要多
      一個輸入、且不得讀 DB」這項**實作**代價，**沒有**揭露它會窄化一條已核可 AC 的
      選取範圍這項**語意**代價。這是本輪的揭露不足，不是使用者選錯——審查 R-01 指出
      本檔自己在 BR6.3 用過正確的格式（明寫對齊修正 ＋ 交接），卻沒對 BR7.3 比照辦理。

  - id: BR7.4
    statement: >
      AC12.4.2 的挑選純函式**不得讀 DB**，故每個候選者的 K3.can_edit 旗標
      必須由呼叫端查好後作為輸入傳入。
    category: constraint
    applies_to: U19 的挑選函式簽章
    trigger: 實作自動改選時
    logic: >
      挑選函式的輸入為「已過濾的候選者集合」或「候選者 ＋ 其 K3.edit 旗標」，
      不得在函式內查詢 role_permissions
    violation_behaviour: >
      函式一旦讀 DB，ADR-0006 的 PBT hard constraint 在它身上失去結構前提
      ——units-generation 對 U19 的注意事項逐字要求它是「不讀 DB 的純函式」，
      因為那是 PBT 能作用的前提，而真正要驗的性質是**排列不變性**
      （ORDER BY joined_at 在時間戳相同時沒有穩定順序）。
    source: >
      修訂 1 Q7=A 的作答後果；units-generation 對 U19 的注意事項
      （前例 backend/cost/estimate_readers.py:247-251 的 best_clouds 用
      key=lambda item: (-item[1], item[0]) 做決定性 tie-break）
    note: >
      這條改變了該純函式的簽章，是本修訂對 U19 的具體指派。
      **另見 BR7.3 的 alignment_correction**：本條傳入的旗標正是那條窄化的載體，
      故 AC12.4.1 的字面偏離同樣適用於本條，交接事項同為 H-11。

  - id: BR7.5
    statement: >
      邀請被拒的訊息必須分辨兩種情形：(a) 完全不持有 K3——不可加入任何專案；
      (b) 持有 K3.view 但不持有 K3.edit——可加入為一般成員、不可為專案管理者。
    category: constraint
    applies_to: U19 的拒絕回應與 U24 的畫面文案
    trigger: BR7.1 或 BR7.2 拒絕時
    logic: >
      IF NOT user_can(x,'K3','view') THEN reason = 'missing_k3'
      ELIF 目標角色 = project_admin AND NOT user_can(x,'K3','edit')
      THEN reason = 'missing_k3_edit'
    violation_behaviour: >
      AC12.5.1 逐字要求「邀請被拒絕且畫面說明**他缺少什麼**」。
      只回一句「權限不足」無法滿足它，而兩種情形的處置完全不同
      （前者要先授予全域權限，後者改邀為一般成員即可）。
    source: >
      `stories.md` 的 AC12.5.1（逐字「邀請被拒絕且畫面說明他缺少什麼」）；
      其上游為 `requirements.md` 的 FR12.6a；修訂 1 Q7=A

  # ── 既有四條規則的取代（數量由 2 個 id 擴為 4 個）────────────────

  - id: BR3.4
    supersedes: BR3.4
    statement: 本單元完成後，預設矩陣恰為 352 列（11 角色 × 32 個 story id）。
    category: validation
    applies_to: DEFAULT_ROLE_PERMISSIONS
    trigger: 測試與 CI
    logic: >
      IF len(DEFAULT_ROLE_PERMISSIONS) ≠ 352 OR 存在缺漏的 (role, story_id) 組合
      THEN 視為違反
    violation_behaviour: >
      列數對但組合有缺漏時，缺的那格在權限頁是破洞而總數看起來正常——
      故檢查必須同時驗總數**與**組合完整性，只驗總數會漏掉這種情形。
    source: >
      [UG:G8]=C；**本站以腳本實算複驗，不照抄算式**：既有 308 列 ＝ 11 × 28
      （組合完整），308 ＋ 11 × 4 ＝ 352。units-generation 逐字要求
      「施工時須以 rbac_seed_data.py 的實際角色數複算，不得照抄」，已照做。

  - id: BR4.1
    supersedes: BR4.1
    statement: >
      44 列的預設值必須同步寫進 schema_rbac.sql 的 role_permissions seed 區塊，
      並更新該檔**兩處**數字。
    category: policy
    applies_to: 交付條件
    trigger: DEFAULT_ROLE_PERMISSIONS 有任何異動
    logic: >
      IF seed 語意變更 THEN schema_rbac.sql 必須同步，否則空 volume 建出的
      新環境與程式內的預設值不一致
    violation_behaviour: project.md ## Mandated 判定為 blocking，階段不得標示完成。
    source: project.md ## Mandated；K-03 的 sync_obligations
    note: >
      **行號已於本修訂重新核對**（原文的 759 已失效）：
      (1) 第 12 行，逐字「--   C) RBAC：role_permissions + 預設矩陣（308 列）」
          → 改為 352。
      (2) 第 **761** 行，逐字
          「-- SELECT count(*) FROM role_permissions;           -- 352」。
      ---
      **第 761 行是一個陷阱，必須明寫**：它**現在**就寫 352，而該檔的 INSERT
      區塊本站逐列實算為 **308**——即原文記載的既存漂移。本單元把總數改為 352
      之後，這一行會**碰巧變成正確**。不得因此認為它本來就對：它的正確性是
      本單元的副作用，而不是任何人修過它。若日後總數再變，這一行仍需手動改。
      ---
      **檔頭指示的那支產生腳本不存在**（原文記載，本修訂複驗仍成立）：
      rbac_seed_data.py 的檔頭逐字寫「由 schema_rbac.sql 產生的預設
      role_permissions 列（勿手改；改 SQL 後重跑產生腳本）」，但
      backend/scripts/ 下只有 dump_openapi.py、dump_ws_contract.py、
      run_hierarchy_migration.py，沒有任何 seed 產生器。故「先改 SQL 再重新
      產生 Python」照字面不可執行；實際做法是兩邊人工同步，而這正是 BR4.4
      存在的理由。

  - id: BR4.2
    supersedes: BR4.2
    statement: >
      DEPLOY.md 的權限矩陣說明必須同步反映 352 列與四個新 story id，
      **共五處**。
    category: policy
    applies_to: 交付條件
    trigger: 同 BR4.1
    logic: IF seed 語意變更 THEN DEPLOY.md 必須同步
    violation_behaviour: 同 BR4.1，blocking。
    source: project.md ## Mandated；K-03 的 sync_obligations
    note: >
      **原文寫「第 594／613 行」兩處，本修訂實測為五處且行號全不同**
      （上游修訂後整體位移）。逐處核對結果：
      :577「寫入設計預設矩陣（約 **308** 列，11 角色 × 各 Story）」、
      :591「或確認啟動後 role_permissions 列數約 308」、
      :596「-- 預期約 308」、
      :1259「Seeds ~**308** role_permissions rows.」、
      :1270「or confirm ~308 rows after backend empty-DB seed」。
      最後兩處在英文段落內，照中文關鍵詞搜尋會漏掉——這是原文只找到兩處的
      可能原因。**引用行號前須重新核對**：本 record 已有 26 個相異行號、
      77 處引用因上游修訂而失效的實例。

  - id: BR4.3
    supersedes: BR4.3
    statement: >
      K1、K2、K3、K4 **四個**都必須有對應的功能標籤，否則權限頁與註冊功能
      摘要出現無名稱的列。
    category: constraint
    applies_to: user_router.py 的 STORY_FEATURE_LABELS
    trigger: 新增 story id 時
    logic: >
      IF story_id 不在 STORY_FEATURE_LABELS AND 不在 CATALOG_EXCLUDED_STORIES
      THEN _feature_label 回 None，該列在摘要中沒有名稱
    violation_behaviour: 不會報錯，只是畫面上出現沒有名字的權限列。
    source: >
      原文由本站查證 user_router.py 得到；上游三份文件皆未記載此相依。
      本修訂複驗：該字典現有 27 個鍵，加上 CATALOG_EXCLUDED_STORIES 的 J1
      恰覆蓋既有 28 個 id，無遺漏——故新增四個 id 必須補四個鍵。

  - id: BR4.4
    supersedes: BR4.4
    statement: >
      同一個 PR 必須新增一支測試，斷言 schema_rbac.sql 的
      INSERT INTO role_permissions 區塊與 rbac_seed_data.py 的
      DEFAULT_ROLE_PERMISSIONS **逐列等值**（相同的 (role, story_id) 集合，
      且每一列的三個旗標相同）。範圍由 22 列擴為 **44 列**，規則本身不變。
    category: policy
    applies_to: 交付條件
    trigger: 本單元往兩份 seed 副本各加 44 列時
    logic: >
      IF 兩份副本的 (role, story_id, can_view, can_edit, can_review) 集合不相等
      THEN 測試失敗
    violation_behaviour: >
      兩份副本會無聲漂移。失敗模式是**環境相依**且不會報錯：從 schema_rbac.sql
      建的新環境拿到 SQL 那份的值，既有環境經 ensure_missing_role_permissions
      拿到 Python 那份的值，兩者不同時沒有任何閘門會紅燈，
      而現象是「同一個角色在不同環境有不同權限」。
    source: >
      team.md ## Code Style 的「單一真實來源」逐字。本修訂複驗：
      backend/tests/ 仍然沒有任何測試做這件事。
    note: >
      可行性已確認：兩份都是可被 Python 解析的純文字。本站已實作出該解析
      （用於複算 308 與 352），故此測試的核心邏輯已有可運行的前例，
      落點為 code-generation。

  # ── 自檢 2（契約端點三問）查出的一條新規則 ──────────────────────

  - id: BR4.5
    statement: >
      K1–K4 **不**加入 CATALOG_EXCLUDED_STORIES，故四個標籤會出現在**公開的**
      /roles/catalog 回應中（未經身分驗證即可讀）。
    category: policy
    applies_to: user_router.py 的 CATALOG_EXCLUDED_STORIES 與 /roles/catalog
    trigger: 新增 story id 並補上 STORY_FEATURE_LABELS 標籤時
    logic: >
      IF story_id ∈ STORY_FEATURE_LABELS AND story_id ∉ CATALOG_EXCLUDED_STORIES
      THEN 其中文標籤出現在 /roles/catalog 的 features 陣列（_build_role_catalog）
    violation_behaviour: >
      若誤加入排除集合，註冊頁的角色功能目錄會少列四項能力，
      而該頁的全部目的就是讓使用者知道各角色能做什麼——缺項不會報錯。
    source: >
      **本站自檢 2（契約端點三問）查出，上游零記載。** 實測：
      user_router.py:310 的 /roles/catalog 其 docstring 逐字「**公開**：註冊頁角色
      功能目錄（動態來自 role_permissions）」，且**無任何 Depends(get_current_user)**；
      它在 :313 呼叫 ensure_role_permissions_seeded(db, force=False)，
      再由 _build_role_catalog（**:249**，審查 R-03 更正，原寫 :250）逐角色列出其持有能力的中文標籤。
      這是 ensure_role_permissions_seeded 的**第三個**呼叫點，原文只記載了
      兩個（啟動路徑與 :885 的 force=True 重置端點）。
    note: >
      **判定為「照既有先例發布，不排除」，理由是既有先例已經如此**：
      CATALOG_EXCLUDED_STORIES 目前只含 J1（登入能力，不是功能），而
      J3a「使用者設定」與 J3b「細項設定」這兩個**管理類**標籤**已經是公開的**。
      故 K3「專案成員管理」與 K4「需求欄位」公開並不引入新的揭露類別。
      揭露的內容是四個中文功能名。**精確說法（審查 R-04 更正）**：該端點本就逐角色
      列出其持有能力的中文標籤，即**確實**揭露「哪個角色能做什麼」的對應——那是它的
      既有設計目的（_build_role_catalog，user_router.py:249）；它不揭露的是
      「**誰**是什麼角色」（使用者與角色的對應）。K1–K4 不改變揭露的類別。
      **此判定已寫進 functional-spec.md §六′ 的 network exposure 列**
      （該列因此由「不適用」改為「適用（一處）」）。
```

## 修訂 1 的規則摘要（衍生自上方 YAML）

| ID | 類別 | 一句話 |
|---|---|---|
| `BR5.1` | constraint | `K3.view` 給八個角色（同 `K1`），三個維運角色全 `false` |
| `BR5.2` | constraint | `K3.edit` 給四個建立者角色，其餘七個 `false` |
| `BR5.3` | constraint | **至少一個有 `A1` view 的角色不得持有 `K3`**，否則 `AC12.5.1` 成死碼 |
| `BR5.4` | constraint | **持有 `K2.edit` 者必須持有 `K3.edit`**，否則「我建的專案我管不動」 |
| `BR5.5` | policy | 本單元只保證 story id 存在；成員判定屬 `U19`、畫面屬 `U24` |
| `BR6.1` | constraint | `K4.view` 給同八個角色 |
| `BR6.2` | constraint | `K4.edit` 給同四個建立者角色 |
| `BR6.3` | policy | **`K4` 只把關需求籤**；清單／建立／總覽籤由 `K2` 把關（對齊修正） |
| `BR6.4` | constraint | 無 `K4` 者在總覽籤**隱藏**未填計數，不是顯示 0 |
| `BR6.5` | constraint | 至少一個角色不得持有 `K4`，否則 `BR6.4` 成死碼 |
| `BR7.1` | authorization | 邀為一般成員 → 查 `K3.view`，不持有即拒 |
| `BR7.2` | authorization | 邀／改為專案管理者 → 查 `K3.edit`，不持有即拒 |
| `BR7.3` | authorization | 自動改選候選集合只含 `K3.edit` 持有者；無人符合則擋下停用。**窄化了 `AC12.4.1` 的「最早加入的成員」，已記為對齊修正 ＋ `H-11`**（審查 `R-01`） |
| `BR7.4` | constraint | 挑選純函式不得讀 DB，`K3.edit` 旗標由呼叫端傳入（改變簽章） |
| `BR7.5` | constraint | 拒絕訊息須分辨「完全不持有 `K3`」與「有 view 無 edit」 |
| `BR3.4`′ | validation | 完成後恰 **352** 列，且須同時驗組合完整性 |
| `BR4.1`′ | policy | `schema_rbac.sql` 同步 **＋ 兩處數字**（含第 761 行的陷阱） |
| `BR4.2`′ | policy | `DEPLOY.md` 同步 **五處**（原文記兩處且行號已失效） |
| `BR4.3`′ | constraint | 補 **四個** `STORY_FEATURE_LABELS` 標籤 |
| `BR4.4`′ | policy | 兩份 seed 副本逐列等值測試，範圍擴為 44 列 |
| `BR4.5` | policy | **四個標籤會出現在公開的 `/roles/catalog`**（自檢 2 查出，照既有先例不排除） |

**合併後的規則集合與類別實算**：見下方「實算結果」段——數字由腳本從本檔
兩個 YAML 區塊解析後輸出，不手寫。

## `authorization` 類別由 0 變為 3——這是本修訂的實質變化

上方原文逐字寫「`authorization` 為 0 是刻意的，不是遺漏：本單元**定義**授權資料，
**不執行**授權判定（`BR1.4`）」。**修訂 1 之後這句話只對 `K1`／`K2` 成立。**

`BR7.1`–`BR7.3` 是 `authorization` 類別的規則，因為 `FR12.6a` 把一個**加入時的
前置條件**疊加在兩層串聯之上——它不是執行期的資源存取判定，而是「這個人能不能
成為成員」的判定，而其唯一的資料依據就是本單元擁有的矩陣。`[RA-2]`=C 的作答
註解逐字說明它「是在其上**疊加**限制而非與它矛盾」。

**但判定的執行落點仍然不在本單元**（`BR5.5`）：`BR7.1`–`BR7.5` 是本單元**定義**
而由 `U19` **執行**的規則。它們寫在這裡，是因為「要檢查哪一個 story id 的哪一個
旗標」這件事只有矩陣的擁有者能定——而上游（`[UG:G8]`=C）明文把它留了下來。

## ADR-0006 的 PBT hard constraint 判定（修訂 1 重新判定）

原文判定為 **N/A**，理由是「`calculation` 實算為 0」。**修訂 1 維持 N/A，但理由須
補一項**：`BR7.4` 點名的那個挑選純函式**確實**是 PBT 的標的（排列不變性），
而它**不在本單元**——它是 `U19 membership-service` 的交付物。本單元交付的是
「候選集合必須先依 `K3.edit` 過濾」這條規則，而規則本身沒有值域性質可寫成 property。

**故判定仍為 N/A，且本修訂明確把 PBT 義務指派給 `U19`**，不讓它在兩個單元之間
掉落。`units-generation` 對 `U19` 的注意事項已經記載該義務，本修訂與它一致。

## 實算結果（由腳本從本檔的兩個 YAML 區塊解析後輸出，非手寫）

- **原區塊的規則數**：16（`BR1`–`BR4`）
- **修訂 1 區塊的條目數**：21，其中 **5** 條為取代既有 id（`BR3.4`、`BR4.1`、`BR4.2`、`BR4.3`、`BR4.4`）、**16** 條為新增
- **合併後的相異規則數**：**32**（原 16 ＋ 新增 16；取代不增加總數）

| 群組 | 條數 | 主題 |
|---|---|---|
| `BR1` | 4 | `K1` 統一入口頁 |
| `BR2` | 4 | `K2` 專案／系統階層 |
| `BR3` | 4 | 寫入端與冪等 |
| `BR4` | 5 | 同步義務（blocking） |
| `BR5` | 5 | `K3` 專案成員管理 |
| `BR6` | 5 | `K4` 需求欄位 |
| `BR7` | 5 | 加入時與自動改選的全域層檢查 |

**類別實算（合併後）**：constraint 20、policy 8、authorization 3、validation 1（合計 32）

對照原文的「constraint 10、policy 5、validation 1、authorization 0、calculation 0（合計 16）」：`authorization` 由 **0 變為 3**（`BR7` 群），`calculation` 仍為 **0**。
