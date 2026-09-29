# Rules — `U3 rbac-story-ids`（`spec`）

<!-- Stage: functional-design（Construction 3.1）· Unit: rbac-story-ids · kind: spec -->

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
