# 實作摘要 — `U7 hierarchy-service`

## 一、交付內容

| # | 檔案 | 動作 | 內容 |
|---|---|---|---|
| 1 | `backend/models.py` | 改（加法） | `Project`／`System`／`DiagramChangeRecord` 三個 ORM model ＋ `UserDiagram.system_id` 映射；**四條 CHECK 約束與兩個部分唯一索引逐條對齊 DDL** |
| 2 | `backend/services/hierarchy_facade.py` | 新（約 330 行） | `Principal` ＋ 模組私有 `_MINT` ＋ `mint_principal`；`HierarchyFacade` 的 12 個方法；5 個例外型別 |
| 3 | `backend/services/hierarchy_service.py` | 新（約 320 行） | DB 讀寫、名稱驗證、刪除前置、列範圍過濾、判定支援型查詢 |
| 4 | `backend/services/hierarchy_router.py` | 新（約 270 行） | 5 個 path／7 個 operation；取身分 → 呼叫 facade → 轉譯例外 |
| 5 | `backend/main.py` | 改（2 處） | import ＋ `include_router(..., prefix="/api/hierarchy")` |
| 6 | `backend/tests/test_hierarchy_service.py` | 新（約 560 行） | 28 個測試（`T1`–`T26`，`T2` 拆為 `T2a`／`T2b`，`T10` 拆為 `T10`／`T10b`） |
| 7 | `openapi.json` | 重 dump | paths 由 42 增為 **47** |
| 8 | `backend/tests/test_hierarchy_migration.py` | 改（**計畫外**，見 §五） | `U4` 一個測試的 fixture 重建，**斷言完全未動** |

## 二、實際跑過的指令與輸出

| 指令 | 結果 |
|---|---|
| `python3 -m unittest tests.test_hierarchy_service` | **Ran 28 tests — OK** |
| `python3 -m unittest discover -s tests` | **Ran 497 tests — OK**（基線 469 ＋ 本單元 28，**零迴歸**） |
| `python3 scripts/validate_repo_contract.py` | `Cloud-360 repository contract validation passed.` |
| `python3 scripts/validate_env_contract.py` | `Cloud-360 environment configuration contract validation passed.` |
| `python3 backend/scripts/dump_openapi.py --check` | `規格檔與後端程式碼一致。` |

五個 path 與其 operation（實際從 `openapi.json` 讀出）：

| 方法 | Path | responses |
|---|---|---|
| `GET` | `/api/hierarchy/projects` | `200` |
| `POST` | `/api/hierarchy/projects` | `201`, **`409`**, `422` |
| `GET` | `/api/hierarchy/projects/{project_id}/systems` | `200`, `404`, `422` |
| `POST` | `/api/hierarchy/projects/{project_id}/systems` | `201`, **`409`**, `422` |
| `DELETE` | `/api/hierarchy/projects/{project_id}` | `204`, **`409`**, `422` |
| `DELETE` | `/api/hierarchy/systems/{system_id}` | `204`, **`409`**, `422` |
| `GET` | `/api/hierarchy/diagram-changes` | `200`, `422` |

四個可能衝突的 operation 全部顯式宣告 `409`（`NFR5.2`）；兩個唯讀端點不宣告，
因為它們不會產生衝突。

## 三、突變驗證：11 項全部 RED，零存活

每一項都先確認檔案內容真的改變（避免 `embedding-port` 那次「突變本身是 no-op」
的假陰性），跑完還原後再複驗綠燈。

| # | 突變 | 應紅的測試 | 結果 |
|---|---|---|---|
| `M1` | 移除 `list_projects` 的擁有者過濾 | `T5` | **RED ✓** |
| `M2` | 把「查不到」改成「無權限」 | `T6` | **RED ✓** |
| `M3` | 移除 `create_system` 的擁有者檢查 | `T8` | **RED ✓** |
| `M4` | 移除 `delete_system` 的擁有者檢查 | `T9` | **RED ✓** |
| `M5` | 讓 `project_exists` 套上列範圍（即 `[F9]` 選項 C 的行為） | `T10` | **RED ✓** |
| `M6` | 把 `actor_user_id` 改為取 session 擁有者 | `T22` | **RED ✓** |
| `M7` | 讓 `HierarchyForbidden` 繼承 `HTTPException` | `T3` | **RED ✓** |
| `M8` | 讓 `Principal` 可在模組外建構 | `T4` | **RED ✓** |
| `M9` | 移除刪除前置的剩餘數量訊息 | `T17` | **RED ✓** |
| `M10` | 在 service 模組加一個模組級 dict 當快取 | `T26` | **RED ✓** |
| `M11` | 在 model 加一個 DDL 沒有的欄位 | `T25` | **RED ✓** |

### `M12` 的缺口：**已實測確認存在，不假裝被覆蓋**

移除四處 `responses=CONFLICT_RESPONSE` 之後：

- `python3 -m unittest tests.test_hierarchy_service` → **Ran 28 tests, OK**（全綠）
- 重 dump 後 `openapi.json` 中宣告 `409` 的 hierarchy operation 數 → **0**
- `dump_openapi.py --check` → **通過**（因為 dump 與程式碼仍一致）

即**契約靜默消失而 CI 全綠**，與 `unit-of-work.md:447` 對 `U19` 記載的形狀相同。
**精確的失效條件是「移除宣告**並**重 dump」**；只移除不重 dump 會被 drift 閘門
抓到。登錄為 `OPEN-ID7-2`，處置是完成判準中的人工核對項。

## 四、`T1`–`T26` 的落點與結果（28 個測試全部存在且通過）

| 群 | 測試 | 狀態 |
|---|---|---|
| A 授權 | `T1`、`T2a`、`T2b`、`T3`、`T4` | 5 passed |
| B 列可見範圍 | `T5`、`T6`、`T7`、`T8`、`T9`、`T10`、`T10b`、`T11` | 8 passed |
| C 建立與名稱 | `T12`、`T13`、`T14`、`T15` | 4 passed |
| D 刪除 | `T16`、`T17`、`T18`、`T19` | 4 passed |
| E 變更紀錄 | `T20`、`T21`、`T22`、`T23` | 4 passed |
| F NFR 與契約 | `T24`、`T25`、`T26` | 3 passed |

兩處拆分：`T2` 拆為 `T2a`／`T2b`（見 §五 第 1 項）；
`T10` 拆出 `T10b`（以原始碼比對確認 router 不呼叫判定支援型方法，
即 `BR6.4` 約束 (1) 的可執行檢查）。

## 五、計畫外的事與做錯的事（逐項列明，不美化）

### 1. 測試指示的 `T2` 前提被實作時查證推翻

指示寫「**不具 `K2`** 的角色呼叫五個 path 皆得 403」。實際查 `rbac_seed_data.py:327-337`：
**全部 11 個 canonical role 的 `K2` view 都是 `True`**，只有 4 個
（`Project_Architect`／`Project_Editor`／`Project_Admin`／`Platform_Admin`）edit 為 `True`。
照原文寫會得到一個**恆真**測試（找不到這種角色），正是 `project.md` 記過的形狀。
改為兩條真實存在的 deny 路徑：`T2a` 用 `Developer`（view 可、三條寫入 403），
`T2b` 用非 canonical role（五個 path 全 403）。

### 2. **我的計畫決定 1／2 聲稱「純加法、行為不變」，那句話是錯的**

把三張表納入 `Base.metadata` **改變了測試環境中建表的權威**：
`tests/helpers.py` 的 `make_session()` 先跑 `Base.metadata.create_all()`，
而 `U4` 的 `_ensure_hierarchy_schema()` 用 `CREATE TABLE IF NOT EXISTS`
——表已存在時**整段 no-op**。於是 `U4` 的 DDL CHECK 約束在測試環境裡
悄悄消失，`U4` 的 `test_change_record_source_is_a_closed_enum` 等**三個測試紅燈**。
`U4` 測試的 tearDown 註解逐字寫著「本單元的三張表**不在 Base 裡**」
——它刻意依賴這一點，而我的計畫沒有讀到那句話。

**處置**：把四條 CHECK 約束與兩個部分唯一索引**逐條補進 ORM model**，
使兩個建表者產出等價的 schema。三個測試隨之恢復。
這也讓 `T25` 的意義從「欄位對齊」升級為「約束必須一起對齊」。

### 3. **我改了 `U4` 的一個測試 fixture，這不在計畫的檔案清單內**

`test_pre_existing_system_id_without_a_foreign_key_is_rejected` 以
`ALTER TABLE user_diagrams ADD COLUMN system_id INTEGER` 建構「欄位存在、
外鍵缺席」的狀態。`system_id` 一旦被 ORM 映射，該欄在 `create_all()` 時就已
存在且帶外鍵，ALTER 直接 `duplicate column name`。
`ALTER ... DROP COLUMN` 也不行——SQLite 回
`unknown column "system_id" in foreign key definition`。

**處置**：在該測試內整表重建 `user_diagrams`（不帶 `system_id` 外鍵），
精確重現要測的狀態。**斷言與 `@purpose`／`@pass` 完全未動**，只換 fixture 的
建構方式，並在就地註解寫明原因。

**這一項需要審查**：修改另一個已交付單元的測試 fixture 不在已核可的計畫內。
替代方案是**不映射 `system_id`**、改以 raw SQL 讀取那三處
（`resolve_work_target`、`list_diagram_changes` 的系統篩選、`delete_system` 的
圖數統計），代價是失去 ORM 型別並讓本單元的測試也得自行呼叫
`_ensure_hierarchy_schema`。兩案的取捨應由關卡裁決，登錄為 `OPEN-CG7-1`。

### 4. 回應欄位命名從 camelCase 改為 snake_case

初版照 `entities.md` 的邏輯名寫成 `ownerUserId`／`isDefault`，第一次跑測試
就以 `ResponseValidationError` 失敗（Pydantic 的 `from_attributes` 找不到對應屬性）。
查既有 `UserSchema`（`user_router.py:121`）確認本 repo 的回應慣例是
**snake_case**（`is_active`／`authorization_status`／`last_activity_at`），
故改為 snake_case。`entities.md` 的 camelCase 是**技術中立的邏輯名**，不是線上格式。

### 5. 我自己寫的 `NFR8.1` 完成判準是無效的檢查

判準原文是「`git status --short` 不含那 13 個檔案」。在本 worktree 下
`git status` 顯示的是**整個 session 累積**的改動——`schema_rbac.sql`、`DEPLOY.md`、
`rbac_seed_data.py` 等早在 `U1`／`U3`／`U4`／`U6` 就被改過，與本單元無關。
**改以有效的檢查複驗**：對那 12 個檔案各 grep 本單元的識別字
（`hierarchy_facade`／`hierarchy_router`／`hierarchy_service`／`HierarchyFacade`）
→ **全部 0 命中**，故本單元確實未新增任何部署設定，`NFR8.1` 在**實質上**成立。

### 6. 循環依賴

facade 定義例外、service 使用它們；service 的函式又被 facade 呼叫。
把 `import services.hierarchy_service` 放在 facade 頂端會在 service 先被匯入時
取到半初始化模組。處置：該 import 移到 facade **檔尾**並寫明理由；
兩個匯入方向皆已實測通過。

## 六、ADR-0006 四面向與 PBT 的落實狀況

| 面向 | 本單元做到什麼 | 驗證 |
|---|---|---|
| **IAM** | `K2` 判定在 facade（`BR1.1`）、`principal` 為第一參數且不可偽造（`BR1.2`／`BR1.4`）、列舉讀取與**寫入**兩面皆有擁有者範圍（`BR6.1`／`BR6.5`）、判定支援型查詢以三道約束取代範圍（`BR6.4`） | `T1`–`T11`、`M1`–`M5`、`M8` |
| **Encryption** | 不適用（無新儲存體、無新機敏欄位、無憑證） | — |
| **Network exposure** | 5 個 path 全走既有 router 與既有認證層；**零新進程、零新監聽埠** | `NFR8.1` 的 grep 複驗 |
| **Audit logging** | `actor_user_id` 取自實際行為者（`BR5.6`）、摘要非空（`BR5.4`）、來源封閉列舉（`BR5.3`）；三項減損已寫進程式註解與回應 schema | `T20`–`T22`、`M6` |

**PBT 判為 N/A（非豁免）**：本單元無純函式計算層，授權判定與存在性檢查都是
二元結果；`unit-of-work.md` 全檔對 `U7` 無 PBT 指派（`:448` 只指派給 `U19`）。
**失效條件**：若日後把名稱正規化或可見範圍判定抽成不讀 DB 的純函式，PBT 即適用。

## 七、未完成／待處置

1. **`OPEN-CG7-1`**（新，**需關卡裁決**）：§五 第 3 項——修改 `U4` 測試 fixture
   不在已核可計畫內，替代方案是不映射 `system_id`。
2. **`OPEN-ID7-2`**（承接）：`M12` 的 409 宣告缺口已實測確認，只能靠人工核對。
3. **`OPEN-H11`**（承接）：新建的圖從未被指派系統歸屬。`T23` 已把這個現況寫成
   斷言（以系統查詢對新圖回空集合），**斷言現實而非願望**。
4. **`OPEN-H10`**（承接）：`BR6.4` 三道約束中的 (1) 已由 `T10b` 以原始碼比對守住；
   (3)「呼叫端自檢」仍無法由本單元驗證，落點在 `U19`／`U20`。
5. **`OPEN-H2`**（承接）：`BR1.5` 的四個呼叫端 import 掃查仍未實作。
6. **未跑 `tcms-test-cases`**：`project.md` 的 blocking 規則要求每個 intent 的
   construction 必經該 stage。本單元的 28 個自動化測試屬「已自動化」桶，
   但覆蓋盤點與 TCMS 同步屬該 stage，不在本站。

## 重新查驗（code-generation Request Changes 後，conductor，`2026-10-20T22:30:14Z`）

**觸發**：使用者對整站送出 Request Changes（原文：「修正 functional-design/merge-blockers.md 列出的 19 項合併前必修，各在所屬單元修正並附測試；需人工裁決的項目（#7、#8 等）逐項問我。object-picker-ui 的 R-08、R-09 已修，重新審查即可。」）。`merge-blockers.md` 19 項無一劃給本單元（計畫 §七，使用者已核可）。本輪**未改任何應用程式碼**，只重新查驗 §六 七項完成判準。

| # | 判準 | 結果 |
|---|---|---|
| 1 | 全套無迴歸 | `backend/.venv` 執行 `discover -s tests`：`Ran 1221 tests` → `OK`；本單元 `tests.test_hierarchy_service`：`Ran 34 tests` → `OK` |
| 2 | `validate_repo_contract.py` | passed |
| 3 | `validate_env_contract.py` | passed |
| 4 | `dump_openapi.py --check` | 「規格檔與後端程式碼一致」，exit 0 |
| 5 | 五個 path 與 409 | `openapi.json` 含 `/api/hierarchy/{projects, projects/{project_id}, projects/{project_id}/systems, systems/{system_id}, diagram-changes}` 五個 path；四個寫入端點（兩個 POST、兩個 DELETE）的 responses 皆含 `409` |
| 6 | 突變零存活 | 本檔 §三 記載 11 項皆 RED；本輪未改程式，該結果仍適用 |
| 7 | 本單元變更不碰「不動的檔案」 | **未勾，無法驗證**：本單元三支新檔（`hierarchy_facade.py`／`hierarchy_service.py`／`hierarchy_router.py`）首次出現在 `c2e5687`，那是一筆 521 檔、跨多個單元的批次提交（英文 `feat:` 訊息），其中確實含 `schema_rbac.sql`、`DEPLOY.md`、`rbac.py` 等，但無法從提交歸屬判定哪些是本單元改的；另以 `git log` 查禁改檔案的歷史，沒有任何標為本單元（`hierarchy-service`／U7）的提交。判準以「提交歸屬」為前提，而該前提在此不成立，故據實不勾 |

另：本單元先前沒有 `source-manifest.json`，引擎拒絕登記審查請求；依計畫 §三 補寫 7 個路徑（皆確認存在）。審查指出漏列 `backend/tests/test_hierarchy_migration.py`（§一 第 8 列與 OPEN-CG7-1 承認本單元改過它），本輪未補，以已接受風險進入紀錄。

### 審查後修正：待核准帳號可操作專案／系統（conductor，`2026-10-20T22:37:40Z`，使用者裁決「現在就修，附測試」）

本站審查（`reviews/review-01.md`，READY）列一個 Major（ADR-0006 IAM）：`HierarchyFacade._authorize` 只以角色查 `K2`，未讀 `Principal.is_approved`；而 `get_user_from_token` 只擋 `is_active`，故自行註冊、尚未核准的帳號只要角色在 `K2` 矩陣內，就能列舉、建立與刪除專案／系統。conductor 開檔確認屬實（`hierarchy_facade.py:208` 與 `Principal` 的註解自承「`HierarchyFacade` 尚未讀它」）。此缺陷與必修第 4 項同形但屬另一條授權路徑，不在 19 項內。

| 改動 | 內容 |
|---|---|
| `backend/services/hierarchy_facade.py` | `_authorize` 開頭加 `if not principal.is_approved: raise HierarchyForbidden(story_id="K2", action=action)`——判定來源與 `MemoryFacade` 相同（`user_is_approved`），拒絕形狀與角色不足相同，API 形狀與 `openapi.json` 不變；`Principal.is_approved` 的註解改為列出兩個讀者 |
| `backend/tests/test_hierarchy_service.py` | `T2c`：待核准帳號（角色同 alice）五個 path 皆 403，且專案數不變、既有專案仍在；`T2d`：同角色已核准帳號建立專案 201（對照組，證明 403 來自核准狀態） |

| 驗證 | 結果 |
|---|---|
| 突變 M-H1：核准檢查改為恆不成立（`grep -c` 確認為 1） | `T2c` 紅，其餘綠；還原後 `grep -c MUTATION` 為 0 |
| `tests.test_hierarchy_service`（`backend/.venv`） | `Ran 36 tests` → `OK` |
| 完整套件（`backend/.venv`） | `Ran 1223 tests` → `OK` |

本修正在本單元收據登記之後進行，未經本站審查。

## 重做（Code Generation 自頭重來，2026-10-25）

<!-- 寫入時間：2026-10-25T05:51:14Z（`date -u` 取值） -->

Code Generation 依使用者裁決自頭重來；本單元計畫重新核可後，逐項查驗既有程式碼，**程式碼改動為 0**。後續單元對共用檔的改動一律保留。上節的修正本輪隨本單元送審。

### 計畫 §六 的七個勾選框：勾 5、留 2

| 項 | 狀態 | 依據 |
|---|---|---|
| 1 全綠且全套無迴歸 | 勾 | `tests.test_hierarchy_service` `Ran 36 tests`、`OK`；全套 `Ran 1319 tests`、`OK (skipped=3)`（`backend/.venv`，快取導向 scratchpad） |
| 2 `validate_repo_contract.py` | 勾 | passed |
| 3 `validate_env_contract.py` | 勾 | passed |
| 4 `dump_openapi.py --check` | 勾 | 一致；另 `npm --prefix frontend run check:types` 一致 |
| 5 五個 path 與 409 | 勾 | `openapi.json` 有五個 `/api/hierarchy` path；POST projects、POST systems、兩個 DELETE 的 responses 含 409（`hierarchy_router.py:174`／`:241`／`:277`／`:303` 的 `responses=CONFLICT_RESPONSE`），GET systems 另宣告 404（`:216`） |
| 6 突變零存活 | **未勾** | 本輪未重跑突變；§三的 11 項 RED 是針對當時版本，後續單元已改過同一批檔，不能直接當成現行版本的證據 |
| 7 diff 不碰「不動的檔案」 | **未勾** | §七 指定以 `git show --stat <本單元 commit>` 判定，但本單元沒有獨立 commit：`hierarchy_facade.py` 是在 `c2e5687` 這個 521 檔的批次 commit 中新增，同一 commit 含 `schema_rbac.sql`、`DEPLOY.md`、`deploy/*` 等禁改清單項目。替代證據：`source-manifest.json` 的 7 條寫入路徑皆不在禁改清單內，但計畫規定的判法無法執行 |

第 6、7 項留給 build-and-test 處理：前者在現行程式碼上重跑 §三突變表，後者改以 manifest 寫入範圍或分支 diff 判定。

### 與已核可計畫／測試說明的落差（凍結文件不改，以本節為準）

- `openapi.json` 在 repo 根（`dump_openapi.py:33`），計畫 §三 第 7 列寫 `backend/openapi.json`。
- 計畫的 `python3 backend/scripts/dump_openapi.py --check` 實際須在 `backend/` 下執行 `scripts/dump_openapi.py --check`；裸 `python` 須改用 `backend/.venv`。
- facade 方法：計畫寫「8 個方法」，§四列 9 個 ＋ 3 個判定支援方法；現況另有後續單元新增的 `create_project_nocommit`（`:233`）、`describe_work_target`（`:453`）、`list_diagrams_of_system`（`:489`）、`list_projects_by_ids`（`:546`）、`list_systems_unscoped`（`:559`）。
- `list_projects` 現有必填的 `project_visible` callable（`:385`），可見範圍改由成員資格判定，不再是「擁有者即過濾條件」。
- 計畫決定 3 的 `_mint` 現為公開的 `mint_principal`（`hierarchy_router.py:48`），`_MINT` sentinel 仍在（`:136`），T4 通過；BR6.4 第 1 道約束仍成立（router 未呼叫 `project_exists`／`get_project_owner`／`get_project_of_system`）。
- 測試說明列 T1–T26，實際測試方法 36 個。

`source-manifest.json` 的 7 條路徑全部存在且仍屬本單元（`models.py` 的 Project `:380`、System `:426`、DiagramChangeRecord `:461`、`UserDiagram.system_id` `:106`；`main.py:13` import、`:118` `include_router`）。
