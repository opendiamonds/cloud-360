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
