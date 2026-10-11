# Code Summary — `U4 hierarchy-data`（`spec`）

<!-- Stage: code-generation（Construction 3.5）· Unit: hierarchy-data · kind: spec -->
<!-- 產出時間（date -u）：2026-09-28T12:52:16Z -->

## 〇、一句話結論

資料模型（三張新表 ＋ 一個新欄位 ＋ 兩個部分唯一索引 ＋ 兩層 `ON DELETE RESTRICT`）
與一次性遷移程序已落地，15 個測試案例全綠、既有 378 個測試維持全綠、四項驗證指令
全部通過；**另在本機以真實 PostgreSQL 18 容器實際執行過 `schema_rbac.sql`、
七個約束的行為、遷移兩次與 `DEPLOY.md` 的回復程序**。

零端點、零畫面、零外部呼叫、零新環境變數、零新 Python 套件（`SEC-1`／`SEC-2`／`SEC-3`）。

---

## 一、交付的檔案

### 新增（3）

| 檔案 | 行數 | 內容 |
|---|---|---|
| `backend/services/hierarchy_migration.py` | 479 | 遷移模組。**唯一公開入口** `migrate_hierarchy(db) -> MigrationCounts`；含 `WF-1` 步 1–3、5 的可重跑安全 DDL、逐使用者交易、三個計數、終檢 raise |
| `backend/scripts/run_hierarchy_migration.py` | 88 | 部署期獨立指令。結束碼 0／1／2；**不在啟動路徑上** |
| `backend/tests/test_hierarchy_migration.py` | 874 | 三個 `TestCase` 類、15 個案例（7／3／5）。**計畫定 13 個，多出的 2 個在 `§六` 第 3 項逐一說明** |

### 修改（3，皆為就地修改，無任何 `X_modified` 複本）

| 檔案 | 增行 | 內容 |
|---|---|---|
| `schema_rbac.sql` | +119 | 新區塊 `H) U4 hierarchy-data`（三表 ＋ `system_id` ＋ 兩個部分唯一索引 ＋ 兩個一般索引 ＋ 8 條 `COMMENT ON`）；檔頭涵蓋清單新增 H 段與「既有環境須另跑遷移指令」註記；檔尾驗證範例新增 6 條 |
| `DEPLOY.md` | +134 | §2.2 物件表新增 2 列；**新增 §2.2.7 全節**（物件說明、前進步驟與預期輸出、驗證查詢、靜止前置條件、中途失敗的處置、回復程序）；§4 部署順序新增第 9 步 |
| `schema.sql` | +57 | 區塊 H 的精簡核心 DDL（建議項，非 blocking） |

`source-manifest.json` 逐一列出上述 6 條路徑。

**未被修改的檔案（刻意）**：`backend/models.py`、`backend/database.py`、`backend/main.py`、
`.github/workflows/deploy.yml`、`.github/workflows/ci.yml`、任何 `frontend/` 檔、
任何 `.env.example`、`deploy/render-env.sh`。因此 `project.md` 的
「異動 `backend/database.py` 的 schema 補丁時須同步 `LOCAL-DEV.md`」**未被觸發**
（`functional-spec.md §七` 末段已預告此條以遷移程序的落點為條件）。

---

## 二、四項驗證指令的實際輸出

### 1. 本單元的精確指令（於 `backend/`）

```
$ python -m unittest tests.test_hierarchy_migration -v
...
Ran 15 tests in 0.398s

OK
```

15 個案例逐一為 `ok`：

```
TestHierarchyMigrationData.test_a_user_without_diagrams_gets_no_default_project ... ok
TestHierarchyMigrationData.test_each_users_diagrams_land_in_that_users_own_default_system ... ok
TestHierarchyMigrationData.test_migration_does_not_touch_any_existing_diagram_column ... ok
TestHierarchyMigrationLogic.test_counts_report_users_pairs_and_rewrites ... ok
TestHierarchyMigrationLogic.test_final_check_raises_with_the_residual_count ... ok
TestHierarchyMigrationLogic.test_rerun_after_a_failure_completes_the_remaining_work ... ok
TestHierarchyMigrationLogic.test_rerun_creates_no_second_pair_and_reassigns_nothing ... ok
TestHierarchyMigrationLogic.test_standalone_command_exits_non_zero_when_the_final_check_fails ... ok
TestHierarchySchema.test_change_record_requires_an_actor ... ok
TestHierarchySchema.test_change_record_source_is_a_closed_enum ... ok
TestHierarchySchema.test_on_delete_restrict_blocks_both_deletion_layers ... ok
TestHierarchySchema.test_partial_unique_indexes_block_a_second_default_at_each_layer ... ok
TestHierarchySchema.test_pre_existing_system_id_without_a_foreign_key_is_rejected ... ok
TestHierarchySchema.test_schema_rbac_sql_matches_migration_ddl ... ok
TestHierarchySchema.test_system_id_is_nullable_so_a_pre_migration_diagram_can_exist ... ok
```

### 2. 既有測試套件（於 `backend/`）

```
$ python -m unittest discover -s tests -v
...
Ran 393 tests in 27.3s

OK
$ echo $?
0
```

基準為本站開工前實測的 **378** 個（同一指令、同一樹）。393 − 378 = **15**，
與本單元新增的案例數相符——**既有案例一個都沒有被破壞，也沒有一個被跳過**。

### 3. Repo contract（於 repo 根）

```
$ python3 scripts/validate_repo_contract.py
Cloud-360 repository contract validation passed.
$ echo $?
0
```

### 4. Env contract（於 repo 根）

```
$ python3 scripts/validate_env_contract.py
Cloud-360 environment configuration contract validation passed.
$ echo $?
0
```

### 附帶（非要求，但 CI 會跑）：OpenAPI 漂移閘門

```
$ cd backend && python3 scripts/dump_openapi.py --check
規格檔與後端程式碼一致。
$ echo $?
0
```

這一條是 `SEC-1`／`SEC-3`（零端點）的**機械證據**：若本單元誤加了任何 router，
端點集合會變、`openapi.json` 未重 dump，這道閘門即紅燈。

---

## 三、`plan_profile.steps` 與計畫九步的逐步對照

| 步 | 狀態 | 落點 |
|---|---|---|
| 1 測試執行器就緒 | 完成 | 開工前實測 378 綠；本單元指令寫入 `unit-test-instructions.md §二` |
| 2 資料模型 DDL | 完成 | `schema_rbac.sql` 區塊 H |
| 3 資料模型測試 | 完成 | `TestHierarchySchema`（7 案例；計畫的 5 ＋ 2 個計畫外，見 `§六` 第 3 項） |
| 4 遷移資料讀寫 | 完成 | `hierarchy_migration.py` 的 `_users_holding_diagrams`／`_resolve_default_pair`／`_assign_unassigned_diagrams` |
| 5 資料讀寫測試 | 完成 | `TestHierarchyMigrationData`（3 案例） |
| 6 交易邊界／計數／終檢 | 完成 | `migrate_hierarchy`／`MigrationCounts`／`_assert_no_unassigned_diagrams`／`run_hierarchy_migration.py` |
| 7 業務邏輯測試 | 完成 | `TestHierarchyMigrationLogic`（5 案例） |
| 8 部署設定 | 完成 | `DEPLOY.md` §2.2／§2.2.7／§4；`schema.sql` |
| 9 文件與追溯 | 完成 | 本檔 ＋ `traceability.json`（50 個上游 id，逐一有 coverage 列）＋ `source-manifest.json` |

**方法論為 test-after**（Testing Contract `sha256:1f0b6822…`）：每一層先實作、再寫並跑
該層的測試，順序原樣保留。API／endpoint 與 Frontend behavior 兩層依計畫省略
（本單元交付零端點、零畫面）。

---

## 四、突變驗證：十個突變全部被抓到

`construction.md` 逐字禁止「不論實作如何都會通過」的測試。為了證明這 15 個案例不是
那種測試，對實作施加十個突變、每次跑全部 15 個案例、然後還原。
**以 `PYTHONDONTWRITEBYTECODE=1` 與 `python -B` 執行**（理由見 `§八` 的第 3 項）。

| 突變 | 結果 | 抓到它的案例 |
|---|---|---|
| **M1** 終檢改成 `logger.warning`（照抄既有 `_ensure_*` 形狀） | **CAUGHT** | `test_final_check_raises_with_the_residual_count`、`test_rerun_after_a_failure_completes_the_remaining_work`、`test_standalone_command_exits_non_zero_when_the_final_check_fails` |
| **M2a** `UPDATE` 一併改寫 `updated_at`（「順手把時間戳更新」的實作） | **CAUGHT** | `test_migration_does_not_touch_any_existing_diagram_column`，斷言訊息逐字為 `'2020-01-02 03:04:05' != '2026-09-28 12:55:56'`（兩張圖各一次） |
| **M2b** `UPDATE` 掉了 `system_id IS NULL` 的冪等守衛（重跑會重新指派） | **CAUGHT** | `test_counts_report_users_pairs_and_rewrites`、`test_rerun_after_a_failure_completes_the_remaining_work` |
| **M3** `projects` 的部分唯一索引改成全表唯一 | **CAUGHT** | `test_partial_unique_indexes_block_a_second_default_at_each_layer` |
| **M4** `systems` 的預設查詢不以 `project_id` 收窄（`BR2.5` 獨佔寫入紀律失效） | **CAUGHT** | `test_each_users_diagrams_land_in_that_users_own_default_system`、`test_rerun_after_a_failure_completes_the_remaining_work`、`test_rerun_creates_no_second_pair_and_reassigns_nothing` |
| **M5** 整個遷移包在單一交易內（`S-8` 的逐使用者邊界消失） | **CAUGHT** | `test_final_check_raises_with_the_residual_count`、`test_rerun_after_a_failure_completes_the_remaining_work` |
| **M6** `schema_rbac.sql` 漏掉 `diagram_change_records.requirement_label` | **CAUGHT** | `test_schema_rbac_sql_matches_migration_ddl` |
| **M7** `user_diagrams.system_id` 的 FK 由 `RESTRICT` 改為 `SET NULL` | **CAUGHT** | `test_on_delete_restrict_blocks_both_deletion_layers` |
| **M8** 獨立指令把失敗當成成功（`return 0`） | **CAUGHT** | `test_standalone_command_exits_non_zero_when_the_final_check_fails` |
| **M9** 「欄位已存在但外鍵不在」改記 `logger.warning` 而非 raise | **CAUGHT** | `test_pre_existing_system_id_without_a_foreign_key_is_rejected` |

**合計十個突變，十個全被抓到。**

M1、M5、M7 三個突變分別對應本 intent 最在意的三種「看起來成功的失敗」：靜默的警告、
被單一交易吞掉的部分進度、以及讓 `system_id` 懸空的 `SET NULL`。

**M2 的第一版已作廢，在此說明為什麼**：第一版把寫入改成 ORM
（`db.query(UserDiagram).filter(UserDiagram.system_id.is_(None))`），它確實讓測試變紅，
但紅的原因是 `AttributeError: type object 'UserDiagram' has no attribute 'system_id'`
——因為本單元刻意**沒有**把 `system_id` 加進 `models.py`。也就是說那個突變**根本不是一個
實作寫得出來的東西**，它證明不了 `BR2.3` 的斷言抓得到 `updated_at` 被改寫。
改以 M2a（照實際可寫出的形狀：在同一句 SQL 裡多寫一個 `updated_at = CURRENT_TIMESTAMP`）
與 M2b（掉了冪等守衛）取代，兩者都被抓到，且 M2a 的斷言訊息直接印出釘住的時間戳與被
改寫後的值。

**附帶收穫**：`models.UserDiagram` 沒有 `system_id` 屬性這件事本身就是一道護欄——
任何想用 ORM 更新這一欄的實作都會先撞上 `AttributeError`，而不是靜默地把
`updated_at` 一起改掉。

---

## 五、真實 PostgreSQL 18 的人工驗證（超出本站要求，但它關掉了本站最大的盲區）

本機有 Docker 與 `psql`，因此**沒有讓 PostgreSQL 方言的 DDL 停在「未被執行過」的狀態**。
以 `pgvector/pgvector:pg18`（`brain-infra` `NFR6.1` 所定的映像）起一個一次性容器：

1. **`psql -v ON_ERROR_STOP=1 -f schema_rbac.sql`** → 全檔執行成功（`COMMIT`，`rc=0`）。
   這驗到了 SQLite 驗不到的部分：`SERIAL`、`TIMESTAMPTZ`、`DO $$` 區塊、
   `COMMENT ON`、以及 `CHECK (length(trim(...)) > 0)` 在 PostgreSQL 的 `trim` 語法。
2. **七個約束逐一實測，以九條敘述執行**（七次必須被拒 ＋ 兩次必須被允許的對照，
   後者證明部分唯一索引真的是「部分」、以及 `systems` 的範圍真的是 `project_id`）。
   PostgreSQL 的訊息逐字如下：
   - `duplicate key value violates unique constraint "uq_projects_default_per_owner"` — 同一擁有者的第二個預設專案
   - 同一擁有者的**非**預設第二個專案 → `INSERT 0 1`（允許，證明索引真的是部分的）
   - `violates check constraint "ck_projects_name_not_blank"` — 空白名稱
   - `duplicate key value violates unique constraint "uq_systems_default_per_project"` — 同一專案的第二個預設系統
   - 同一擁有者**另一個**專案下的預設系統 → `INSERT 0 1`（允許，證明範圍是 `project_id` 而非擁有者）
   - `violates check constraint "ck_diagram_change_records_source"` — `source = 'manual_edit'`
   - `null value in column "actor_user_id" ... violates not-null constraint`
   - `update or delete on table "systems" violates RESTRICT setting of foreign key constraint "fk_user_diagrams_system"`
   - `update or delete on table "projects" violates RESTRICT setting of foreign key constraint "systems_project_id_fkey"`
3. **遷移指令連跑兩次**（`U4-V2`／`U4-V3`／`U4-V5` 的內容）：
   第一次 `(users_processed, default_pairs_created, diagrams_assigned) = (2, 2, 3)`、`rc=0`；
   第二次 `(2, 0, 0)`、`rc=0`；`system_id IS NULL` 的列數為 0；
   `projects` 與 `systems` 各 2 列（**沒有第二組**）；歸屬與擁有者一一對應
   （`alice 的專案／預設系統 → 2 張`、`bob 的專案／預設系統 → 1 張`）。
4. **`DEPLOY.md` 2.2.7 的回復程序逐字執行** → `UPDATE 3`／`DELETE 2`／`DELETE 2`，
   三個確認計數皆為 0。文件裡那段 SQL 是跑過的，不是寫出來看的。

**這不是 CI 閘門。** 它是一次人工驗證，容器已刪除；`U4-V1`–`U4-V5` 的承載仍是
`U5`／`N-2` 的共用 CI job（見 `§六` 的 open item 1）。

---

## 六、Open items（逐項附理由與可執行的下一步）

### 1. `U4-V1`–`U4-V6` 沒有任何 CI 承載者 —— **本單元無法關閉**

`U4-V1` 逐字要求共用 `U5`／`N-2` 的真實 PostgreSQL CI job 且「不另開第二個 job」，
而 `brain-infra` 的 `NFR6.1` 逐字記載那個 job「**尚未存在**」。本站在本機把該 job 的
六個步驟全部跑通（`§五`），但**沒有**把它寫進 `.github/workflows/`——那會是另開第二個
job，直接違反 `U4-V1`。

**落點** `ci-pipeline`（3.7，`CONDITIONAL`）或 `U5` 建立該 job 時。
**若兩者都沒發生，`U4-V1`–`U4-V5` 全部落空**，屆時判定 skip 的人必須把 `S-6`
重新提交給使用者。`§五` 的操作序列可直接搬進該 job。

### 2. `U4-V6`（靜止）目前**沒有承載者，而管線預設就違反它**

`.github/workflows/deploy.yml:121–124` 是單一個 `up -d --build --remove-orphans`
把整座 stack 一次拉起、`:126` 立刻等前端，**沒有任何一點是 db 起來而 backend 沒起來的**。
本站的承載只有兩件事，都是文件層的：`DEPLOY.md` 2.2.7 寫下手動取得窗口的四個步驟，
並**逐字寫明這個窗口目前不存在、不要把容器重建的無序中斷當成它**。

**本站刻意不改 `deploy.yml`**（計畫 §三 明列不做，`S-9` 的落點是
`ci-pipeline`／`deployment-pipeline`）。實作者與部署者都不得因為 `DEPLOY.md`
寫了靜止就認為靜止已經生效。

### 3. DDL 存在兩處，而**只有欄位集合被測試鎖住**

`schema_rbac.sql` 只在空 data volume 執行，既有環境的唯一路徑是遷移程序自己
（`K-04` 的 `context_why_migration_is_the_only_path` 逐字），所以兩處 DDL 是必要的，
不是疏漏。`test_schema_rbac_sql_matches_migration_ddl` 鎖住的是**欄位名集合**
與四個識別字的存在，**沒有**鎖住型別、`NOT NULL`、`CHECK` 條文與 `ON DELETE` 動作
——那需要把兩份 DDL 都套到同一個真實 PostgreSQL 再比對 `information_schema`，
屬 `§六` 第 1 項那個 CI job 的內容。

**本站新增了兩個計畫外的測試案例**（計畫定 13 個，實際 15 個）。這是**對計畫的偏離，
在此明白揭露**，不是悄悄加的：

- **第 14 個** `test_schema_rbac_sql_matches_migration_ddl`：`team.md` 的「單一真實來源」
  逐字要求「新增副本的同一個 PR 必須一併新增鎖住兩者一致的測試；無法寫測試的副本
  不新增」。DDL 的第二處副本是必要的（見上），而這個測試寫得出來，所以不寫等於違反該條。
- **第 15 個** `test_pre_existing_system_id_without_a_foreign_key_is_rejected`：它測的是
  `_ensure_hierarchy_schema` 的 raise 分支（**欄位已存在但外鍵不在或動作不是
  `RESTRICT`**）。那個分支是本站自己加的防禦路徑，而 `construction.md` 要求測試涵蓋
  happy path 與至少兩個錯誤／邊界情境；一條沒有任何案例碰過的 raise 路徑會靜默腐爛。
  突變 M9 驗證了它（把 raise 改成 `logger.warning` 即被抓到）。

`TestHierarchySchema` 因此是 7 個案例，仍落在 Standard 策略的「每元件 5–8 個」區間內
（`TestHierarchyMigrationData` 3 個、`TestHierarchyMigrationLogic` 5 個皆照計畫未動）。

**這個防禦分支自身的殘餘**：`ON DELETE` 動作的可見性依方言而異——PostgreSQL 回報
`SET NULL`／`CASCADE` 等非預設動作（`NO ACTION` 回報為空），**SQLite 一律回報為空**。
所以本站的判準是「**回報到的值不是 `RESTRICT` 才判為錯**」，回報為空時只記 log、
不判定，也**不反過來聲稱已驗證**。在 SQLite 上這個子檢查因此形同不存在；
它對部署真正有效的那一側（PostgreSQL）是有效的。

### 4. 覆蓋率的 80% 門檻**無法量測**

本 repo 沒有 `.coveragerc`、沒有 `coverage`／`pytest-cov`、CI 無 coverage step
（`team.md` 逐字如此記載）。本單元的實際門檻是 15 個案例全綠 ＋ 既有 378 個維持全綠，
兩者都已達成。**本站沒有引入 coverage 工具**——那是獨立的工具鏈決策，不由本單元夾帶。

### 5. `AC9.1.3` 的「既有頁面行為不變」只驗到欄位層

本單元逐欄斷言了 `user_id`／`title`／`xml_data`／`updated_at` 遷移前後不變，
但**既有架構圖頁面自身的 e2e 斷言不在本單元**（零畫面交付）。落點是 `U16`
與既有 Playwright 層（`security-requirements §六` 已記為殘餘風險）。

### 6. `DiagramChangeRecord` 本 intent 結束時會是空表

本單元交付它的結構，**不交付寫入端**（寫入端是 `U12`）。加上零讀取端（`Q2=A`）
與清除機制未落地（`U4-R2`／`S-5`），這張表在本 intent 結束時是一張
**沒有人寫、沒有人讀、沒有人清**的表。這是上游已接受的狀態，在此重述以免它被
當成已生效的能力。

### 7. `SEC-4` 第四處的稽核保證仍待 `OQ-H3`

`actor_user_id` 為 `NOT NULL` 且 `COMMENT ON COLUMN` 逐字寫明「不得預設填工作階段
擁有者」，但「多參與者共享工作階段裡的行動者是哪一位」仍未定案（落點 `U12`，
`CONDITIONAL`）。本站**不宣稱**稽核面向已滿足。

### 8. `schema_rbac.sql` 的 `users` 表缺 `authorization_status` —— **既有落差，不是本單元造成**

`§五` 的真實 PG 驗證意外查出：`schema_rbac.sql` 建的 `users` 沒有
`authorization_status` 欄位，而 `models.py::User` 有、`database.py::_ensure_j5_schema`
會補。也就是說**以 `schema_rbac.sql` 建立的全新資料庫，在 backend 啟動之前，
ORM 與實際 schema 是不一致的**。

本單元不受影響（遷移只 `SELECT users.id, users.username`，從不碰該欄）。
**本站不修它**——那是 J5 的 schema 資產，與本單元無關，趁機夾帶會讓這個 PR 的
可驗證範圍變模糊。記在此處供後續 intent 處置。

---

## 七、設計產出中發現的問題（逐項直說，沒有繞開）

### 1. 計畫的交付物表把全部 DDL 指給 `schema_rbac.sql`，但那樣**既有環境的遷移必然失敗**

`code-generation-plan.md §〇` 的交付物表只把 DDL 指給 `schema_rbac.sql`，
而 `functional-spec.md` 的 `WF-1` 步 1–3、5 是**遷移流程自己的步驟**
（逐字「以可重跑安全的方式」，且 `WF-2` 逐字「步 1–3、5 因可重跑安全的寫法而成為
無操作」）。兩者不一致。

**處置**：以 `WF-1`／`WF-2` 為準（它是有序行為的真實來源），把可重跑安全的 DDL 放進
遷移模組的私有 `_ensure_hierarchy_schema()`，`schema_rbac.sql` 保留為空 volume 的
可攜來源。**依據**：`K-04` 的 `context_why_migration_is_the_only_path` 逐字說
`schema_rbac.sql` 只在空 volume 執行；若 DDL 只在那裡，遷移在
`192.168.10.10` 上第一句就會是 `relation "projects" does not exist`——而那正是本單元
存在的理由。副作用（兩處 DDL）見 `§六` 第 3 項。

### 2. `diagram_change_records.diagram_id` 的 `ON DELETE` 行為**上游從未指定**

`entities.md`、`rules.md`、`K-04` 都沒有說刪除一張圖時它的變更紀錄怎麼辦。
不指定（PostgreSQL 預設 `NO ACTION`）會讓「刪除架構圖」這條**既有使用者路徑**
在該圖有變更紀錄之後開始失敗，直接違反 `AC9.1.3`。

**處置**：採 `ON DELETE CASCADE`，依據是 repo 既有慣例
（`user_diagram_chats.diagram_id` 與 `architecture_reviews.diagram_id` 皆為 `CASCADE`）
＋ `AC9.1.3`。**代價要說清楚**：刪除一張圖會連帶銷毀它的稽核紀錄，
而那張表正是 `SEC-4` 第四處所指的稽核資料。這是本站為了不破壞既有路徑而做的取捨，
若後續認為稽核資料不該隨圖消失，處置是新增一張獨立的保留表或改為軟刪除，
**不是**把它改成 `NO ACTION`（那會擋住既有的刪圖路徑）。

### 3. `entities.md` 的 `ArchitectureDiagram.owner_user_id` 與實際欄位名不符

`entities.md` 以 `owner_user_id` 稱該欄，而 `user_diagrams` 的實際欄位名是 `user_id`
（`schema_rbac.sql:64`、`models.py:95`）。`BR2.3` 的 `applies_to` 也寫成
`owner_user_id`。這是邏輯名與物理名的差異，不是矛盾，但本站據此把 `BR2.3` 的四欄
對應為 `user_id`／`title`／`xml_data`／`updated_at` 並在測試中逐欄比對。
**新建的 `projects.owner_user_id` 沿用上游的名稱**（它是新欄位，沒有既有物理名要遷就）。

### 4. `nfr-requirements §五`／`S-7` 預期的 SQLite 落差**實測為零**

`unit-test-instructions.md §五` 預留了「若某個約束在 SQLite 上無法忠實重現，
該案例標記為只能在真實 PostgreSQL 驗證」。實測結果是**一項都不需要標**：
部分唯一索引（`WHERE is_default`）、`ON DELETE RESTRICT`（需
`PRAGMA foreign_keys=ON`，測試以 `_set_sqlite_foreign_keys()` 明確開啟）、
兩種 `CHECK` 在 in-memory SQLite 上全部**真的擋住**，且同一組行為在真實
PostgreSQL 18 上也全部擋住（`§五`）。

**沒有任何約束為了讓測試變綠而被弱化或改寫成寬鬆版本。**

---

## 八、實作過程中值得記下的三件事

1. **`models.UserDiagram.updated_at` 帶 `onupdate=func.now()`** —— 所以遷移若以 ORM
   更新 `system_id`，`updated_at` 會被連帶改寫而違反 `BR2.3`。這是「走 ORM 還是走
   `text()`」從風格問題變成正確性問題的原因，已寫進模組 docstring 與
   `_assign_unassigned_diagrams` 的註解。突變 M2a 驗證了這條
   （它模擬的是在同一句 SQL 裡多寫一個 `updated_at = CURRENT_TIMESTAMP`——
   純 ORM 的那條路因為 `models.py` 沒有 `system_id` 而根本走不通，見 `§四` 的說明）。
2. **`BR2.3` 的測試必須先把 `updated_at` 釘成固定的過去時間**。若讓 ORM 的
   `server_default` 填 `CURRENT_TIMESTAMP`，SQLite 只有秒級解析度，同一秒內的重新
   觸發會產生**相同的值**，那個缺陷就會靜默通過。
3. **突變驗證必須關掉 bytecode 快取**。第一輪突變把
   `ON DELETE RESTRICT` 改成 `ON DELETE SET NULL`——**兩者位元組長度相同**，
   還原後檔案的 mtime 與 size 都與 `.pyc` 的紀錄相符，於是 Python 繼續載入
   **突變後的 bytecode**，`test_on_delete_restrict_blocks_both_deletion_layers`
   隨後連續失敗五次而原始碼完全正確。第二輪改以
   `python -B` ＋ `PYTHONDONTWRITEBYTECODE=1` 重跑，十個突變的結果才可信
   （M8 的第一輪報告曾多出一個受污染的失敗案例，已作廢）。
   **本檔 `§四` 的表格是第二輪的結果。**

---

## 九、`ADR-0006` 四面向 ＋ PBT hard constraint 逐項判定（自檢第七項）

| 面向 | 判定 | 本單元的落點 |
|---|---|---|
| **IAM** | 適用，**以交付面上不可構造滿足** | 零 `APIRouter`、零 service 層讀寫函式；模組公開名稱只有 `migrate_hierarchy`／`MigrationCounts`／`HierarchyMigrationError`／`CHANGE_RECORD_SOURCE_BRAIN`。OpenAPI 漂移閘門通過即端點集合未變。**殘餘不是「無」**：本單元交付的三張表正是 `unit-of-work.md` 記載的「同進程直呼 service 層會繞過 RBAC」那條路徑能讀寫的資料，該殘餘歸 `U7`／`U8`，本單元只保證沒有再開第三條路 |
| **IAM（特權操作）** | 適用 | 沿用既有 `DATABASE_URL`。兩支新檔對 `os.environ`／`getenv`／`API_KEY`／`PASSWORD`／`SECRET` 的 grep 結果為零；`validate_env_contract.py` 通過 |
| **Encryption** | 適用，**判定為不做任何加密**（沿用 `nfr-design §一`） | 零 `pgcrypto`、零金鑰、零 `sslmode`。殘餘風險（主機磁碟被取得即明文）原樣沿用該站記載，本站不改寫其強度 |
| **Network exposure** | **不適用，附理由** | 零端點、零連線、零對外介面。`SEC-3` 的 import／decorator 機械檢查已對 `source-manifest.json` 所列的本單元三支 Python 檔執行，命中數為零 |
| **Audit logging** | 適用，**其中一處只成立一半** | (1) 遷移失敗大聲＝OK；(2) 遷移留三個計數＝OK；(3) 清除留計數＝空轉（`S-5` 未落地）；(4) `DiagramChangeRecord` 結構＝OK（`actor_user_id NOT NULL` ＋ `COMMENT` 寫明不得預設填工作階段擁有者），但**稽核保證仍待 `OQ-H3`**——本站不宣稱已滿足 |
| **PBT hard constraint** | **不適用，附理由** | `ADR-0006` 點名 IaC generator、cost calculator、agent routing 三類純計算模組，本單元不含其中任何一個；`rules.md §二` 實算 `calculation` 類規則數為 **0**。本單元交付資料結構與一段順序固定的遷移流程，**沒有值域可供性質測試的純函式**。判定為 N/A 而非豁免。本 intent 的 PBT 落點是 `U11` 的門檻純函式與 `U6` 的 `EmbeddingPort` |

---

## 十、`project.md` blocking 規則的完成狀態

| 必做項 | 狀態 |
|---|---|
| `schema_rbac.sql`：DDL ＋ `COMMENT` ＋ `IF NOT EXISTS` 可重跑 ＋ 檔頭涵蓋清單 ＋ 驗證註解 | **完成**（區塊 H，+119 行；已在真實 PG 18 上 `ON_ERROR_STOP=1` 執行成功） |
| `DEPLOY.md`：表／欄位表 ＋ 新表與重要欄位說明 ＋ 建議的 `psql` 驗證指令 ＋ 既有環境升級說明 | **完成**（§2.2 兩列、§2.2.7 全節、§4 第 9 步，+134 行；回復程序已實際執行） |
| 建議一併更新 `schema.sql`（非 blocking） | **完成**（+57 行） |
| commit 前執行 `validate_repo_contract.py` | **完成**，passed |
| commit 前執行 `validate_env_contract.py` | **完成**，passed |
| 異動 `backend/database.py` 的 schema 補丁時同步 `LOCAL-DEV.md` | **未觸發**——本單元不改 `database.py`（遷移落在 `services/`，`functional-spec.md §七` 末段已預告此條以落點為條件） |
