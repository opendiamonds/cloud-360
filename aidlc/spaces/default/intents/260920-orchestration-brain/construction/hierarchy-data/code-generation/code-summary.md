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

---

## 十一、重新查驗（Request Changes 後）

<!-- 2026-10-20T07:51:36Z（`date -u` 取值） -->

使用者對整站送 Request Changes，引擎把計畫步 1–9 的勾選重設。本節逐格回 repo 現況開檔查證，**不是**沿用上一輪的結論。步 1–9 的程式在 `9e14145`（`功能(hierarchy-data): projects／systems／diagram_change_records 三表與一次性遷移`）落地，本輪**未修改**其中任何一支檔。

**結果：步 1–9 共 47 格全部勾回 `[x]`，未勾 0 格**（`grep -c` 計畫檔的 `- [x]` 得 54，扣步 10 的 7 格）。

| 步 | 查證方式 | 結論 |
|---|---|---|
| 1 | `backend/.venv` 跑 `unittest discover`（基線見下）；讀 `tests/helpers.py`；`unit-test-instructions.md §二` 的精確指令仍在 | 成立。**後續單元已合法改動 `helpers.py`**：stub 對象由 `psycopg2` 改為 `psycopg`（v3），且只在未安裝時才 stub；in-memory SQLite ＋ `StaticPool` 策略不變，仍可承載本單元 |
| 2 | 讀 `schema_rbac.sql:340-438`（區塊 H） | 成立：三表、`system_id` 可空 ＋ `fk_user_diagrams_system` `ON DELETE RESTRICT`、`systems.project_id` `ON DELETE RESTRICT`、`uq_projects_default_per_owner`／`uq_systems_default_per_project` 兩個部分唯一索引各只引用本表欄位、`ix_diagram_change_records_created_at`、`IF NOT EXISTS`／條件式 `DO` 區塊、三處 `COMMENT`、檔頭 `:10-11` 涵蓋清單 |
| 3 | `TestHierarchySchema` 的案例名 ＋ 實跑 | 成立（五項各有對應案例；另有兩個結構守門案例） |
| 4 | 讀 `backend/services/hierarchy_migration.py` | 成立：`migrate_hierarchy(db) -> MigrationCounts`、`_users_holding_diagrams`（join `users`）、`_resolve_default_pair` 先專案後以 `project_id` 找系統、`_assign_unassigned_diagrams` 走 `text()` 不走 ORM |
| 5 | `TestHierarchyMigrationData` 三案 ＋ 實跑 | 成立 |
| 6 | 同上檔 ＋ 讀 `backend/scripts/run_hierarchy_migration.py` | 成立：逐使用者 commit、例外 rollback 後 `raise`（不吞）、終檢 `raise HierarchyMigrationError`、logger `"cloud360.hierarchy_migration"`、獨立指令失敗回 1 |
| 7 | `TestHierarchyMigrationLogic` 五案 ＋ 實跑 | 成立 |
| 8 | 讀 `DEPLOY.md` §2.2 物件表與 §2.2.7（前進步驟、靜止前置含 `deploy.yml:121–124` 的誠實記載、中途失敗可恢復、回復程序）；`schema.sql` 區塊 H | 成立 |
| 9 | 本檔、`traceability.json`、`source-manifest.json` 皆存在 | 成立 |

**實際輸出**：

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest tests.test_hierarchy_migration` → `Ran 15 tests … OK`（`unit-test-instructions.md §三` 寫 13 個；實際多兩個結構守門案例 `test_pre_existing_system_id_without_a_foreign_key_is_rejected` 與 `test_schema_rbac_sql_matches_migration_ddl`，本輪未增減）
- 改動前的完整套件基線：`Ran 1210 tests in 91.490s` → `OK`

**後續單元改過、但與步 1–9 的宣稱有出入的一處（如實記錄，本輪不改）**：`projects.is_default` 的 COMMENT 仍寫「Written ONLY by services/hierarchy_migration.py」；本輪未查證後續單元（`U7` 建圖路徑等）是否已成為第二個寫入端。若已是，`BR2.5` 的「獨佔寫入紀律」前提需另行重審。

---

## 十二、合併前必修第 3 項：刪除使用者不得回 500（計畫步 10）

<!-- 2026-10-20T07:51:36Z（`date -u` 取值） -->

來源：`construction/functional-design/merge-blockers.md` 第 3 項（`review-06` R-04）。`OQ-H1` 裁決（使用者，2026-10-20）：**空的預設專案一併清掉，其餘改回 409**。

### 1. 改動的檔（行號為改動後）

| 檔 | 位置 | 內容 |
|---|---|---|
| `backend/services/user_router.py` | `:14-15`、`:23-37` | 匯入 `or_`、`IntegrityError` 與十一個模型 |
| 同上 | `:325-374` | `DeleteUserBlockingReference`、`DeleteUserConflict`（409 本體）、`_UserDeleteBlocked`、`_DELETE_USER_409_DOC`、`_delete_blocked_response` |
| 同上 | `:377-406` | `_empty_default_project_ids`（規則 1 的判定） |
| 同上 | `:409-511` | `_blocking_user_references`（規則 2 的一次性預檢，11 類） |
| 同上 | `:514-540` | `_purge_empty_default_projects`（規則 1 的清除） |
| 同上 | `:543-599` | `_hard_delete_user`：既有 403 原樣保留在預檢之前（規則 4）；預檢 → 409；清除 → `db.delete(user)` → commit；`IntegrityError` → rollback ＋ `logger.error` ＋ 通用 409（規則 3） |
| 同上 | `:888-894`、`:918-930` | `POST /authorization-requests/{id}/reject`：`responses=` 宣告 409；攔 `_UserDeleteBlocked` 回 409 |
| 同上 | `:1047`、`:1083-1086` | `DELETE /{user_id}`：同上（規則 5：兩入口共用 `_hard_delete_user`） |
| `backend/tests/test_user_delete_hierarchy.py` | 新檔，323 行 | 7 個 TestClient 案例 (a)–(g) |
| `openapi.json` | +65 | 兩個端點的 409 ＋ 兩個 schema |
| `frontend/src/types/api.d.ts` | +48 | `npm run gen:types` 重產 |
| `schema_rbac.sql` | `:365`、`:598-600`、`:629` | `projects.owner_user_id` 與 `project_members.user_id` 兩處 COMMENT 改記裁決與落點；`:598-600` 的行內 SQL 註解同步（原寫「上游刻意未決」，不改會與 COMMENT 矛盾）。**無 DDL 結構變更** |
| `DEPLOY.md` | `:498-529` | 新增「刪除使用者的行為」小節：規則表、409 類別清單、維運意涵、只讀查詢 |

### 2. 預檢涵蓋的參照清單（實作前自行重數）

`grep -n -i "references *\(public\.\)\?users" schema_rbac.sql` 得 19 欄（排除 `:703`／`:811`／`:862` 三處註解與 COMMENT 字串）。處置分四類：

| 欄（`schema_rbac.sql` 行） | ON DELETE | 處置 |
|---|---|---|
| `user_diagrams.user_id`（:90） | 無 | 既有 403（規則 4，不變） |
| `diagram_shares.user_id`（:113）、`user_diagram_chats.user_id`（:126） | 無 | 既有流程先刪（不變） |
| `estimate_sets.owner_user_id`（:260）、`estimate_shares.user_id`（:305） | CASCADE | 不需處理 |
| `role_authorization_requests.user_id` | CASCADE（ORM `models.py:80`；**不在** `schema_rbac.sql`） | 既有流程先刪（不變） |
| `projects.owner_user_id`（:348） | 無 | 規則 1 清除範圍外 → `owned_projects` |
| `project_members.user_id`（:600）／`invited_by`（:603） | 無 | 規則 1 範圍外 → `project_memberships`／`project_member_invitations` |
| `reselection_events.promoted_user_id`（:649）／`previous_owner_user_id`（:650） | 無 | `reselection_events`（稽核，不刪） |
| `system_requirement_fields.updated_by`（:701） | 無 | 規則 1 範圍外的系統 → `system_requirement_fields` |
| `memory.memory_records.owner_user_id`（:456） | 無 | `memory_records` |
| `memory.memory_audit_events.actor_user_id`（:517） | 無 | `memory_audit_events`（稽核） |
| `diagram_change_records.actor_user_id`（:415） | 無 | `diagram_change_records`（稽核） |
| `estimate_audit_events.actor_user_id`（:312） | 無 | `estimate_audit_events`（稽核） |
| `architecture_reviews.created_by`（:143） | 無 | `architecture_reviews` |
| `wa_lenses.updated_by`（:183） | 無 | `wa_lenses` |

**計畫列出的 13 欄全數涵蓋，計畫沒有漏列的無 `ON DELETE` 參照。** ORM 一致性：對 `backend/` 全部 `.py` grep `ForeignKey("users.id"`，上表每一欄在 `models.py` 都有對應且 `ondelete` 一致（`Project.owner_user_id:394`、`ProjectMember.user_id:563`／`invited_by:577`、`ReselectionEvent:622`／`:629`、`SystemRequirementField.updated_by:724`、`MemoryRecord.owner_user_id:885`、`MemoryAuditEvent.actor_user_id:943`、`DiagramChangeRecord.actor_user_id:486`、`EstimateAuditEvent.actor_user_id:325`、`ArchitectureReview.created_by:147`、`WaLens.updated_by:174`）。`backend/database.py:245/318/346/525` 的補丁 DDL 與上表同形。

### 3. 實作中的判斷（偏離或補充，逐項說明）

1. **409 本體的 `detail` 維持字串，結構化清單另放 `blocking_references`**。`AdminPage.tsx:197` 與 `AuthorizationRequestsPage.tsx` 都以 `data.detail` 顯示錯誤；`HTTPException(detail=<dict>)` 會讓畫面顯示 `[object Object]`。因此改用 `JSONResponse`（比照同檔 `update_user_active` 的 409 寫法），本體為 `{"detail": "<含類別與筆數的可讀字串>", "blocking_references": [...]}`。`blocking_references` 在 spec 中非必填，因為拒絕端點既有的「此申請已處理」409 只有 `detail`。
2. **規則 1 的子列以明確刪除處理**（`project_members`、`system_requirement_fields`），不只依賴 `ON DELETE CASCADE`：bulk `query.delete()` 不走 ORM cascade，SQLite 未開外鍵時也不會連帶刪除；明確刪除讓兩種方言結果一致。**後果需揭露**：空預設專案底下若有需求欄位值，會隨系統一起刪掉（裁決的「空」以「無架構圖、無他人成員」定義，未把需求欄位列為「非空」條件）。
3. **(g) 以真實外鍵模擬，未用 mock**：測試在 SQLite 建一張預檢不認識、外鍵指向 `users` 的表並插一列，刪除父列時 commit 的 flush 拋出真正的 `IntegrityError`。比 `unit-test-instructions.md` 寫的「以 mock 注入」更接近正式環境，故採用。
4. **既存缺陷順手修掉，由 (f) 實測抓到**：拒絕並刪除端點在 `_hard_delete_user` commit 之後才讀 `req.requested_role`；該申請列已被刪除，refresh 觸發 `ObjectDeletedError` → **500，而帳號其實已刪除**（HEAD 的 `:645` 同樣如此，正式環境 `SessionLocal` 預設 `expire_on_commit=True`，與測試同）。修法是刪除前先取值（`:921`）。既有測試沒有任何一支走過這個端點，所以這個 500 一直沒被看到。
5. **與 `BR1.1`「`MembershipFacade` 是唯一入口」的張力**：清除與預檢在 `user_router.py` 直接以 ORM 讀寫 `projects`／`project_members`，沒有經 facade。計畫明文要求就地沿用、不抽 service 層（`team.md` 的 `user_router.py` 規則），且 `BR1.1` 約束的是 per-project **授權判定**，不是帳號刪除時的資料清理；`test_project_visibility_static.py` 的五條靜態斷言全綠。仍列為審查時應確認的一點。

### 4. 測試與突變結果

精確指令（於 `backend/`）：`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest tests.test_hierarchy_migration tests.test_user_delete_hierarchy -v` → `Ran 22 tests … OK`（15 ＋ 7）。

`setUp` 以 `PRAGMA foreign_keys=ON` 開啟外鍵並讀回 `1` 守門；`tearDown` 先關外鍵再 `drop_all`（否則 `DROP TABLE users` 被外鍵擋下——第一次實跑即因此 7 個 teardown error，已修）。

| 突變 | 改法 | 預期紅 | 實際 |
|---|---|---|---|
| M-D1 | `_purge_empty_default_projects(...)` 改成 `pass` | (a) | **(a)(f) 紅**（落到保底 409，非 200） |
| M-D2 | `blocking = []` 取代預檢 | (c)(d) | **(c)(d)(e) 紅**（落到保底 409、清單為空） |
| M-D3 | `except IntegrityError` 改成 `except ZeroDivisionError` | (g) | **(g) 紅**：`AssertionError: 500 != 409` |

每次突變前以 `grep -c "MUTATION"` 確認突變已寫入（回 1）、還原後回 0，還原後 22 個案例全綠。

### 5. 各命令的實際輸出

| 命令 | 結果 |
|---|---|
| `.venv/bin/python scripts/dump_openapi.py` 後 `--check` | `已寫入 openapi.json`；`規格檔與後端程式碼一致。` exit 0；`openapi.json` +65 行 |
| `npm run check:types`（重產前） | `型別檔已漂移`（預期） |
| `npm run gen:types` 後 `npm run check:types` | `API 型別檔與規格檔一致。`；`api.d.ts` +48 行 |
| `npx tsc -b`（於 `frontend/`） | exit 0，無輸出 |
| `python3 scripts/validate_repo_contract.py` | `Cloud-360 repository contract validation passed.` |
| `python3 scripts/validate_env_contract.py` | `Cloud-360 environment configuration contract validation passed.` |
| 完整套件 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests` | `Ran 1217 tests in 92.282s` → `OK`（基線 1210 ＋ 本輪 7） |

**沒有跑的**：前端 `npm run lint` 與 Playwright e2e（本項未改任何手寫前端檔，只重產型別檔）；真實 PostgreSQL 上的刪除行為（預檢與保底只在 SQLite 外鍵開啟下驗證；PostgreSQL 對 `NO ACTION` 的檢查時點在敘述結束，結果相同但未實測）。

### 6. ADR-0006 四面向

| 面向 | 判定 |
|---|---|
| IAM | 適用，**不變**：兩端點仍掛 `require_story_action("J3a", "edit")`；拒絕端點的 `admin_may_decide_role` 仍在刪除之前 |
| Encryption | 不適用：無新資料、無新傳輸 |
| Network exposure | 適用，**無新暴露面**：零新端點；409 本體多回各類資料筆數，只對已具 `J3a.edit` 的管理員可見 |
| Audit logging | 適用：稽核類紀錄（`reselection_events`、`memory_audit_events`、`diagram_change_records`、`estimate_audit_events`）一律保留、改回 409；保底路徑記 `logger.error`；`_audit_append` 只在刪除成功後寫 |

### 7. Open items

- 新增指向 `users.id` 且無 `ON DELETE` 的欄位時，須手動加進 `_blocking_user_references`；**沒有機械檢查**強制這一點，漏了只會退成通用 409（不會 500）。
- 曾操作過稽核類資料的帳號無法硬刪除——這是裁決的直接後果，維運改用停用；已寫進 `DEPLOY.md`。

## 十三、審查後補測（conductor，`2026-10-20T08:07:29Z`）

本站審查（`reviews/review-02.md`）判定 READY，但列一個 Major：規則 1「空預設專案」的兩個條件沒有測試守住——拿掉「除本人外無其他成員」會經 `project_members` 的 `ON DELETE CASCADE` 靜默刪掉他人的成員列與整個專案；`test_b` 的圖屬於 target，只走到既有 403，碰不到 `has_diagram` 條件。這是誤刪資料類缺口，依「殘留當場修」於收據登記、單元完成後立即補上（不改產品程式，只加測試）：

| 新測試 | Given | 斷言 |
|---|---|---|
| `test_h_default_project_with_another_member_is_not_purged` | target 的預設專案（無圖）有 alice 為 member | 409、`owned_projects`；專案與 alice 的成員列、target 皆仍在 |
| `test_i_default_project_holding_someone_elses_diagram_is_not_purged` | target 的預設系統下掛 alice 的圖，target 本人無圖 | 409、`owned_projects`；專案、系統、圖、target 皆仍在 |

突變驗證（先以 `grep -c MUTATION` 確認突變已寫入，還原後確認為 0）：

| # | 突變 | 結果 |
|---|---|---|
| M-D4 | `_empty_default_project_ids` 的 `other_member` 條件改為恆不成立 | `test_h` 紅（其餘 8 案綠） |
| M-D5 | `has_diagram` 條件改為恆不成立 | `test_i` 紅（其餘 8 案綠） |

還原後 `tests.test_user_delete_hierarchy`：`Ran 9 tests` → `OK`；完整套件（`backend/.venv`）：`Ran 1219 tests` → `OK`。

審查其餘四項 Minor（清除未逐筆稽核、409 未給下一步、拒絕路徑修正無突變、預檢與 commit 之間的競態）未在本輪處置，以已接受風險進入紀錄；其中「清除會連帶刪掉空預設專案下使用者填寫的系統需求欄位」已向使用者揭露。

## 十四、重做（Code Generation 自頭重來，2026-10-25）

<!-- 寫入時間：2026-10-25T00:07:58Z（`date -u` 取值） -->

Code Generation 依使用者裁決自頭重來；本單元計畫重新核可後，逐步查驗既有程式碼，**程式碼改動為 0**。計畫 54 格全部勾選；後續單元對共用檔（`schema_rbac.sql`、`DEPLOY.md`、`user_router.py`、`openapi.json`、`api.d.ts`）的改動一律保留。

### 逐步查驗摘要

- 步 1–9：DDL（`schema_rbac.sql:338-437` 的 H 區塊、兩層 `ON DELETE RESTRICT`、兩個部分唯一索引）、遷移讀寫與邏輯、獨立指令的非零結束碼、`DEPLOY.md` §2.2.7 與 `schema.sql:82-118` 皆與計畫相符。
- 步 10（合併前必修第 3 項）：`user_router.py:581-637` 的 `_hard_delete_user` 三條規則（空預設專案同交易清除、11 類參照預檢回 409、`IntegrityError` 保底 409）、兩個端點的 `responses=_DELETE_USER_409_DOC`、`openapi.json`／`api.d.ts` 的 `DeleteUserConflict` 皆在。**突變 M-D1～M-D5 本輪未重跑**（須暫時改壞程式碼），沿用 §十二、§十三 的紀錄。

### 測試與閘門（本輪實跑，快取導向 scratchpad，未寫入 repo）

| 指令 | 結果 |
|---|---|
| `python3 -B -m unittest tests.test_hierarchy_migration tests.test_user_delete_hierarchy -v`（`backend/`） | `Ran 24 tests`、`OK`（遷移 15 ＝ 計畫 13 ＋ 外鍵守門、DDL 一致性 2；刪除 9 ＝ 計畫 (a)–(g) ＋ (h) 預設專案有其他成員、(i) 預設專案下有他人建立的圖） |
| `python3 -B -m unittest discover -s tests`（系統 `python3` 與 `backend/.venv` 各一次） | 皆 `Ran 1319 tests`、`OK (skipped=3)` |
| `python3 -B scripts/dump_openapi.py --check` | 一致，exit 0 |
| `npm --prefix frontend run check:types` | 一致，exit 0 |
| `python3 scripts/validate_repo_contract.py`、`python3 scripts/validate_env_contract.py` | 皆 passed |

### 與已核可測試說明的落差（凍結文件不改，以本節為準）

`unit-test-instructions.md` §二的單元指令只列 `tests.test_hierarchy_migration`，實際單元範圍另含 `tests.test_user_delete_hierarchy`；§三的「合計 13 個案例」與刪除測試「7 個案例」已過時，現況為 24 個（遷移 15、刪除 9）。`source-manifest.json` 的 10 條路徑全部存在且仍屬本單元。
