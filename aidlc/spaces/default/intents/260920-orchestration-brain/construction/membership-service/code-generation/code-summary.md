# Code Generation 摘要 — `U19 membership-service`

> Testing Contract 解析為 **`methodology: test-after`**、**`test_strategy: standard`**。
> 實作順序照 `plan_profile.steps`：每一層先實作、再寫並跑該層的測試，**不是** TDD 的
> Red-first。`scope_floor`（既有測試套件維持綠燈）與 standard 策略的義務兩者皆已滿足。

## 一、交付的檔案（26 條，與 `source-manifest.json` 逐條相同）

### 新增（12）

| 檔案 | 內容 |
|---|---|
| `backend/services/membership_types.py` | 四個值物件：`ProjectRole`（封閉列舉，**不含 `project_owner`**）、`MemberSnapshot`（frozen dataclass，純函式輸入）、`MemberView`、`GuardedProjectRef` ＋ `LastAdminGuardReport`（409 的 response model） |
| `backend/services/membership_errors.py` | 四個領域例外，**皆不繼承 `HTTPException`**（`BR1.5`） |
| `backend/services/membership_selection.py` | **只有 `select_successor`**。獨立成檔使「純」可機械檢查（import 集合以 `ast` 實測為三項） |
| `backend/services/membership_service.py` | 資料存取 ＋ 業務邏輯 ＋ 稽核 ＋ 鎖輔助 ＋ 四個 log 事件名常數。**無授權檢查**（誠實宣告） |
| `backend/services/membership_facade.py` | `K-16` 的七個公開方法 ＋ `create_project_with_owner` ＋ 兩個橫幅方法 ＋ `run_auto_reselection` |
| `backend/services/membership_router.py` | 六個端點，掛在 `/api/membership`。**不 import `membership_service`** |
| `backend/scripts/backfill_project_members.py` | 一次性回填：單一交易、自我終檢、非零碼、冪等、`--dry-run` |
| `backend/tests/test_membership_data.py` | `M1`–`M8`（資料模型 ＋ 資料存取） |
| `backend/tests/test_membership_facade.py` | `F1`–`F8`（含 **blocking 的 PBT**）＋ `F1b`／`F2b`／`F5b` 共 11 個 |
| `backend/tests/test_membership_endpoints.py` | `E1`–`E7`（API／端點） |
| `backend/tests_pg/__init__.py` | 新測試根 ＋ `require_pg_url()`（缺值即大聲失敗） |
| `backend/tests_pg/test_membership_concurrency.py` | `C1`–`C3`（真實 PostgreSQL） |

### 改既有（14）

| 檔案 | 改了什麼 |
|---|---|
| `backend/models.py` | 新增 `ProjectMember`／`ReselectionEvent` 兩個 ORM model，逐條對齊 `infrastructure-specification.md §四之二` 的十一列表 |
| `backend/main.py` | 註冊 `membership_router`（prefix `/api/membership`） |
| `backend/services/user_router.py` | 停用端點：第三道前置檢查（在 `:682` 的寫入**之前**）、**顯式宣告 409 ＋ `LastAdminGuardReport`**、停用成功後觸發自動改選 |
| `backend/services/hierarchy_service.py` | 新增 `create_project_nocommit`（`OPEN-ND19-5` 的解）；`create_project` 退化為「它 ＋ commit」 |
| `backend/services/hierarchy_facade.py` | 新增 `create_project_nocommit`，與 `create_project` 共用同一個 `_authorize` |
| `backend/services/hierarchy_router.py` | `POST /projects` 退化為對 `create_project_with_owner` 的薄委派；`_translate` 另認 `MembershipNotFound` |
| `schema_rbac.sql` | `J)` 區塊加 `cause` ＋ `ck_reselection_events_cause` ＋ COMMENT；**改述四段既有 COMMENT** |
| `backend/scripts/verify_meta_schema.sql` | `P5` 8→9 欄；新增 `P13`／`P14`；**修一處既有斷言**（`P7` 的 INSERT 缺 `cause`） |
| `backend/scripts/run_meta_schema_migration.py` | 後條件：`reselection_events` 8→9 欄、`EXPECTED_CONSTRAINTS` 加一條 |
| `openapi.json` | 重 dump（51 paths／68 operations；409 宣告由 4 增為 **7**） |
| `frontend/src/types/api.d.ts` | 重產（`+928` 行） |
| `.github/workflows/ci.yml` | 新增 `concurrency` job |
| `DEPLOY.md` | §2.2.9 更新 ＋ **新增 §2.2.10** |
| `LOCAL-DEV.md` | 新增 `H6` ＋ 本機 `create_all` 陷阱 ＋ `tests_pg` 執行指令 |

**刪除：0。** **`backend/database.py` 的 diff 為空**（`NFR12.5`，`git diff --stat` 實跑無輸出）。

## 二、測試結果（全部實跑，非宣稱）

| 指令 | 結果 |
|---|---|
| `python -m unittest -v tests.test_membership_data tests.test_membership_facade tests.test_membership_endpoints` | **26 tests OK** |
| `DATABASE_URL=postgresql+psycopg://… python -m unittest -v tests_pg.test_membership_concurrency` | **3 tests OK**（3.2 秒；真實 PostgreSQL 17.7 ＋ pgvector） |
| `python -m unittest discover -s tests`（scope floor） | **523 tests OK**（基線 497 ＋ 本單元 26） |
| `psql -f backend/scripts/verify_meta_schema.sql` | **14 條斷言全部通過**（`P1`–`P14`） |
| `python3 scripts/validate_repo_contract.py` | **passed** |
| `python3 scripts/validate_env_contract.py` | **passed** |
| `python scripts/dump_openapi.py --check` | **一致** |
| `npm run check:types` / `check:ws-types` | **一致** |
| `npm run lint` / `npm run build` | **0 errors**（2 warnings，皆既存 `exhaustive-deps`）／build 成功 |

> `tests_pg` 跑在一個丟棄用的資料庫上（本機的 `cloud360` 開發庫**未被動到**；
> 它只有 `users` 一張表，套用 `schema_rbac.sql` 會重播 352 列 RBAC 矩陣）。
> 測試結束後該丟棄庫已刪除。

### 測試數分佈（standard：每元件 5–8）

| 元件 | 檔案 | 數 |
|---|---|---|
| 資料模型 ＋ 資料存取 | `test_membership_data.py` | **8** |
| 業務邏輯 ＋ 純函式 ＋ 稽核 | `test_membership_facade.py` | **11**（計畫寫 8；多出的三個是 `F1b` 空輸入、`F2b` `[FD1]`=A 的分歧格、`F5b` 兩層串聯） |
| API／端點 | `test_membership_endpoints.py` | **7** |
| 併發（真實 PG） | `tests_pg/test_membership_concurrency.py` | **3** |

## 三、突變驗證（`unit-test-instructions.md §七`，五項全部實跑）

每一項都跑三次：突變前必須綠、突變後必須紅、還原後必須再綠。

| # | 突變 | 要求 | **實測** | 紅燈的測試 |
|---|---|---|---|---|
| 1 | `select_successor` 的 tie-break 改成只按 `joined_at` | 紅燈 | **RED** ✓ | `F1`（PBT 排列不變性） |
| 2 | 移除 `lock_project` 的 `.with_for_update()` | 紅燈 | **RED** ✓ | `C1`（真實 PG） |
| 3 | `assert_can_deactivate` 的呼叫移到 `is_active` 寫入**之後** | 紅燈 | **RED** ✓ | `E6` |
| 4 | 橫幅查詢移除 `cause = 'auto_reselection'` 條件 | 紅燈 | **RED** ✓ | `F8` |
| 5 | `ReselectionEvent.project_id` 加上 `ForeignKey` | 紅燈 | **RED** ✓ | `M2` |

**五項的還原後複驗全部綠燈**（`revert ok`）。

**第 1 項值得單獨說明**：PBT 的生成策略刻意把 `joined_at` 抽自一個**只有三個值的
池**。沒有這個收斂，從完整 `st.datetimes()` 範圍抽樣幾乎永遠不會產生平手，於是
該突變**抓不到**——而測試仍會是綠的。這是「可失敗的性質」與「看起來在驗那個性質」
之間的差別。

## 四、本單元的三件「違反後 CI 全綠」，各自的處置與實測

| # | 風險 | 處置 | 實測證據 |
|---|---|---|---|
| 1 | **漏宣告 409**（`BR6.2`）。FastAPI 不從 `raise HTTPException` 推導狀態碼，故漏宣告時 spec 與型別都「正確地」少了它，**兩道漂移閘門一致通過** | 三個 operation 顯式 `responses={409: {"model": LastAdminGuardReport}}`；回應本體**就是**該 model（以 `JSONResponse` 回傳而非 `raise`），否則 spec 會說一件回應沒有做的事 | 重 dump 後 409 宣告由 **4 增為 7**，新增的三個都帶 `$ref: LastAdminGuardReport`（機械解析 `openapi.json`）；`api.d.ts` 含 `LastAdminGuardReport`／`GuardedProjectRef`；`E3` 驗三個入口的欄位集合 |
| 2 | **ORM 與 DDL 的約束／索引不一致**。既有 `T25` 只比對欄位名——約束名、索引名、partial 條件、外鍵有無都在它射程外 | `M1`–`M4`／`M8` 五條二元可判的斷言 | 突變 5 實測 RED；`M3` 比對**名稱集合相等**（同時擋下多加 CHECK 與漏掉 Index）；`M4` 驗兩個 dialect 的 `where` |
| 3 | **併發守門被繞過**。`with_for_update()` 在 SQLite dialect 下被**靜默丟棄**（編譯出的 SQL 無鎖子句、無錯誤、無警告），故跑在既有測試路徑上的併發測試驗證的是空氣 | 新測試根 `backend/tests_pg/` ＋ 新 `concurrency` CI job。隔離是**結構性**的（`discover -s tests` 看不到它），不需任何 env guard | 突變 2 實測 RED；`require_pg_url()` 在缺 `DATABASE_URL` 時大聲失敗、**不退回任何預設** |

## 五、本站實跑才發現的三件事（都不在計畫裡）

### 5.1 `verify_meta_schema.sql` 的既有 `P7` 會因 `cause` 的 NOT NULL 而紅燈

`P7` 的行為類斷言 `INSERT INTO reselection_events (...)` **原本省略 `cause`**。
加上 `NOT NULL` 之後它以
`null value in column "cause" ... violates not-null constraint` 失敗。

**若只改結構類斷言（`P5`／`P13`／`P14`）就交付，CI 的 `memory-schema` job 會紅燈，
而紅燈原因會指向 `P7` 而不是 `cause`。** 這是「跑一次 `psql -f`」與「讀一遍檔案」
的差別——它在靜態閱讀下看不出來，因為那個 `INSERT` 距離 `CREATE TABLE` 有 200 多行。

### 5.2 `run_meta_schema_migration.py` 的後條件也要同步，而計畫沒點名它

該腳本的 `EXPECTED_TABLES` 宣告 `reselection_events` 為 **8 欄**，
`EXPECTED_CONSTRAINTS` 不含 `ck_reselection_events_cause`。不改它的後果不是紅燈，
是**部署腳本在一個其實正確的資料庫上終檢失敗並 rollback**——而它是既有環境取得
這些物件的**唯一路徑**。

這兩項都是 `cause` 這個加欄的**必然後果**，不是範圍擴張；兩者都已列入
`source-manifest.json`。

### 5.3 `schema_rbac.sql` 的 `users` 比 ORM 的 `User` 窄一欄

`authorization_status` **不在** `A)` 區塊裡，它由 `backend/database.py` 的
`_ensure_j5_schema()` 在**後端啟動時**補上。後果：在一個只套用過
`schema_rbac.sql` 的資料庫（**正是新 `concurrency` job 所建的那種**）上，
任何 `db.add(User(...))` 會以
`UndefinedColumn: column "authorization_status" ... does not exist` 失敗。

**為什麼它到今天才被發現**：`memory-schema` job 只跑 raw SQL 斷言，從不碰 ORM；
而 `backend/tests` 的 in-memory SQLite 是用 `create_all()` 建表的，所以那裡的
`users` 一定有全部 ORM 欄位。**只有「真實 PostgreSQL ＋ ORM」這個組合會撞到它，
而本單元是第一個。**

本站**不修它**（`users` 不是本單元的表，`A)` 區塊屬 baseline，修它會改變一條既有
建表路徑），只繞開：`tests_pg` 以 raw SQL 建使用者列。記為 `OPEN-CG19-5`。

## 六、與計畫的偏離（三項，逐項理由）

### 6.1 計畫 Step 4 的第一條斷言照字面實作會與 DDL 衝突

計畫逐字寫「`ReselectionEvent.__table__.foreign_keys` 為**空集合**」。
而 `schema_rbac.sql` 的 `J)` 區塊對 `promoted_user_id`（NOT NULL）與
`previous_owner_user_id` 都宣告了 `REFERENCES users (id)`——**照字面斷言空集合，
就得把那兩條外鍵從 ORM 拿掉，而那會讓 ORM 與 DDL 不一致**，正是整組一致性測試
要防的事。

`[ND1]`=A 的實際內容、`infrastructure-specification.md §四之二` 的那一列、以及
`verify_meta_schema.sql` 的 `P6`（`rt.relname = 'projects'`）說的都是
「**不對 `projects` 設外鍵**」。

`M2` 因此斷言**兩個方向**，比計畫的字面更強：目標表集合**不含** `projects`
（擋下習慣性加上 `ForeignKey`），且**恰為** `{users}`（擋下把那兩條拿掉）。
記為 `OPEN-CG19-4`。

### 6.2 `test_membership_facade.py` 是 11 個測試而不是計畫的 8 個

多出的三個都是 `standard` 策略區間（5–8）之外、但有明確可失敗行為的：
`F1b`（空輸入大聲失敗）、`F2b`（`[FD1]`=A 比 `FR12.5` 字面更嚴的那一格）、
`F5b`（兩層串聯，`AC12.5.2` 的 deny 側）。`F2b` 與 `F5b` 各自對應一條
已核可的上游決定，省掉它們會讓那兩條決定沒有測試。

### 6.3 `concurrency` job 的 `timeout-minutes` 定為 15

計畫把值留給本站（`monitoring-design.md §六` 要求「明確設定」但不給數字）。
15 遠高於實測（三條斷言 3.2 秒 ＋ `pip install`），又遠低於 runner 預設的 360
分鐘——併發測試的失敗模式是**卡住**而不是紅燈。

## 七、本單元的一項可達性分析（`project.md` 的「先驗 X 可達」）

**自動改選真正會執行的狀態只有一種，而它不是直覺上的那一種。**

把守門與改選的次序代入：`assert_can_deactivate` 先判（`BR6.1`），通過之後才跑
`run_auto_reselection`（`BR4.4`）。於是：

| 專案狀態（owner = 被停用者 `X`） | 守門 | 改選 |
|---|---|---|
| `X` 是唯一的 `project_admin` | **擋下整個停用**（409） | 不會跑到 |
| `X` 與 `Y` 都是 `project_admin` | 放行 | **冪等命中**（排除 `X` 後仍有 `Y`）→ 不執行、不寫事件 |
| `X` 是 `member`，`Y` 是 `project_admin` | 放行 | 冪等命中 → 不執行 |
| **`X` 完全不是該專案的成員**，成員只有 `Y`／`Z`（皆非 admin） | 放行（`X` 不是任何專案的 admin） | **執行**：選最早加入者升為 `project_admin`，寫事件 |

所以改選唯一真正執行的狀態是「**`projects.owner_user_id` 指向 `X`，而 `X` 不在
`project_members` 裡**」——而那**正是回填之前每一個既有專案的狀態**
（`project_members` 是全新表，既有專案全部零成員）。

**這條分支是可達的、不是死碼**，而它的可達性直接依賴 `projects.owner_user_id`
與 `project_members` 是兩個獨立事實這一點（`ProjectRole` 刻意不含
`project_owner` 的同一個理由）。

**這也解釋了一個測試上的陷阱**：`F7` 的第一版讓被停用者同時擁有一個他是唯一管理者
的專案，於是 `run_auto_reselection` 產生了**兩筆**事件而測試預期一筆。那不是實作
缺陷——是測試直接呼叫 `run_auto_reselection` 構造了一個守門本來就會攔住的狀態。
已改為由另一位使用者擁有該孤兒專案，並把理由寫進測試的註解。

## 八、ADR-0006 四面向 ＋ PBT（逐格對照 `functional-spec.md §八` 的三欄表）

| 面向 | 判定（與上游一致） | **本站的實作落點** |
|---|---|---|
| **IAM** | **適用（本單元的核心）** | `membership_facade` 的兩層串聯（全域 `require_story_action` dependency ＋ per-project `_require_project_role`）、`BR1.5` 的領域例外、`BR1.6` 的 `None` 即拒絕、`assert_still_has_admin`／`projects_losing_last_admin` 的共同上游守門、`lock_project` 使守門在併發下仍成立。**殘留缺口**：`BR1.1` 無機械強制（`OPEN-CG19-1`，並指出 repo 已有兩支同形的 import-boundary validator 可照抄） |
| **Encryption** | **本單元無落點**（上游為此面點名的落點是 `McpBridge`／`U21`）。**不寫「不適用」**——那會讀成該面向對本修訂不成立 | 無 pattern。唯一相關的是 `NFR12.26` 的**禁令**（log 不得含 token／密碼／憑證），而那是禁令不是加密設計。回填腳本亦不輸出 `DATABASE_URL` 或其片段 |
| **Network exposure** | **適用，有落點** | 新端點掛在既有 `/api/` 之下（`/api/membership/*`），**零新監聽埠、零新環境變數、`deploy/` 零改動**；既有停用端點的回應契約擴充（`BR6.1` 的三道檢查次序、`BR6.2` 的顯式 409、`BR6.3` 既有兩道不得削弱）。**本站新增一項上游沒有的落點**：新 `concurrency` job 的 postgres service container（`ports: 5432:5432` 僅映射到 runner 的 localhost、生命週期等於 job、資料為合成測試資料，**不是**部署面的暴露增量） |
| **Audit logging** | **適用** | 兩個載體的界線：稽核列（`reselection_events`，**使用者**讀得到，`BR5.1`–`BR5.6`）與結構化 log（四個事件名常數，**維運者**讀，`NFR12.6`／`NFR12.27`–`NFR12.29`）。拒絕**不進**稽核表（`NFR12.7`）。`OPEN-ND18-3` 由 `cause` 的落地**關閉**；`OPEN-P4` 由 `[N2]`=A 的 WARN log **關閉** |

### PBT：**適用且 blocking**，且已落地並經突變驗證

| 項目 | 內容 |
|---|---|
| 作用對象 | `select_successor(list[MemberSnapshot]) -> MemberSnapshot` |
| 結構前提 | 獨立模組 `membership_selection.py`。以 `ast` 解析，import 集合**恰為三項**（`__future__`／`typing`／`services.membership_types`），四個禁止符號（`sqlalchemy`／`Session`／`httpx`／`HTTPException`）在**程式行**命中數皆為 **0**。**量測方式要寫明**：裸 `grep` 會各命中一次，命中的是該檔 docstring 裡「沒有這四者」那段散文自己。facade 的對應方法是 `staticmethod`（拿不到 `self._db`） |
| 可失敗的性質 | **排列不變性**（不是「同一組輸入選出同一人」——後者對純函式恆真） |
| 落點 | `F1`，`@given` ＋ `st.permutations`，`max_examples=200`，跑在既有 `backend` job |
| 突變 | tie-break 只按 `joined_at` → **實測 RED** |

## 九、仍然開放的項目

`traceability.json` 的 `open_items` 有 **17 項**，全部為 `named-gap` 或承接項，
另一項為 `blocking-downstream`。四項最需要讀的：

1. **`OPEN-ID19-2`（`blocking-downstream`）**：「回填已在 staging 執行過」必須是
   **第一個消費端所在批次**的前置條件。它**不在依賴圖上**，所以 Bolt 計畫不會
   自動帶上它；`deploy.yml` 不呼叫任何遷移腳本。
2. **`OPEN-CG19-2`**：`BR6.3` 要保護的「既有兩道」裡，**第二道在正式認證路徑上
   不可達**（推導見 `E5` 的 docstring）。這是**既存**狀態，不是本變更造成的，
   而本站原樣保留了它。
3. **`OPEN-CG19-3`**：停用端點 409 的本體沒有 `detail`，而既有
   `AdminPage.tsx:172` 的錯誤解包是 `data.detail || '更新狀態失敗'`。前端對 409
   的呈現須在**與本變更同批**的部署中落地（`BR6.4`）。
4. **`OPEN-ID19-6`**：`ut` **完全沒有必要狀態檢查**，故新 job 紅燈**不擋合併**
   ——它是訊號而不是閘門。

### `infrastructure-design` 收尾時的兩項 Minor：**仍然開放**（逐字記載）

該 stage 以 READY 收尾（0 Critical／0 Major／2 Minor），而它只有一輪審查額度，
引擎逐字回覆「Do not ask the reviewer again; include the findings in the approval
summary for the human」。本計畫**不就地編輯那兩份已凍結的檔案**（編輯會使該 stage
的 READY 收據失效而無額度可補），故兩項隨本 stage 的關卡再次呈現：

- **`R-01`**：`cicd-pipeline.md §五之三` 與 `infrastructure-specification.md §五之一`
  用「本站實查」描述 `assert_can_deactivate` 在零成員列時的行為，而該函式**當時
  尚未落地**；結論是由已發布的 `HAVING count(*) = 1` 查詢形狀推導而得。
  **本站可以補上一句**：該函式現已落地，而那個推導**正確**——零成員列時
  `HAVING count(*) = 1` 找不到任何列，故它**放行**（方向過寬而非過嚴），
  `M7` 的第 (1) 個案例即為此實測。
- **`R-02`**：「覆蓋面不可能靜默消失」一句在首次出現時缺限定詞；`ut` 目前無任何
  必要狀態檢查，故紅燈不擋合併（同 `OPEN-ID19-6`）。

## 十、完成判準逐項對照（計畫 §七）

| # | 判準 | 結果 |
|---|---|---|
| 1 | `validate_repo_contract.py` 綠燈 | ✅ passed |
| 2 | `validate_env_contract.py` 綠燈 | ✅ passed |
| 3 | `backend/database.py` 的 diff **為空** | ✅ `git diff --stat` 無輸出 |
| 4 | 既有 `unittest discover -s tests` 全綠 | ✅ 523 tests OK |
| 5 | 新 `concurrency` job 的三條斷言綠燈，且**每條都做過突變驗證** | ✅ 3 tests OK；突變 2（移除鎖）實測 RED，`C1` 紅燈 |
| 6 | `select_successor` 的 PBT 綠燈，且突變驗證 | ✅ 綠燈；突變 1 實測 RED |
| 7 | `dump_openapi.py --check` 綠燈，且 `openapi.json` 含停用端點的 `409` | ✅ 一致；`PUT /api/auth/{user_id}/active` 的 409 帶 `$ref: LastAdminGuardReport` |
| 8 | 前端型別產生器無漂移 | ✅ `check:types` ＋ `check:ws-types` 皆一致 |
| 9 | `source-manifest.json` 涵蓋每一個變更路徑 | ✅ 26 條，逐條存在於磁碟、無重複；以 `git status --short` 交叉核對後排除了其他單元的未提交變更 |

> 判準 5 的「每條都做過突變驗證」照字面是三條斷言各一個突變，而
> `unit-test-instructions.md §七` 只為併發面指定一個突變（移除
> `with_for_update()`）。實測該突變讓 `C1` 紅燈而 `C2`／`C3` 仍綠
> ——**那是正確的**：`C2`（不同專案不互相阻塞）與 `C3`（守門不取鎖）在沒有鎖
> 的世界裡本來就成立，它們防的是**相反方向**的錯誤（鎖的範圍過大）。
> 為它們各造一個突變需要分別引入「表級鎖」與「守門也取鎖」兩種實作，
> 而那兩個突變不在 `§七` 的清單裡。如實記載為差異而非宣稱已做。

## 重新查驗與合併前必修第 1、4、10、15、16 項

> 紀錄時間：2026-10-20T23:50:41Z（`date -u`）。來源：使用者對 code-generation 整站送
> Request Changes，本單元承接 `functional-design/merge-blockers.md` 第 1、4、10、15、16 項；
> 四項裁決皆選建議項（計畫 Step 15a–15e、`unit-test-instructions.md` §3.1）。

### 一、Steps 1–14 重新查驗

逐格對照 repo 現況，全部成立並勾回：例外與值物件（`membership_errors.py`／`membership_types.py`）、
ORM 兩表與 `cause` 欄（`schema_rbac.sql`、`verify_meta_schema.sql`、`DEPLOY.md` §2.2.9 為 9 欄）、
`M1`–`M8`、`hierarchy_service.create_project_nocommit` 與 `hierarchy_router` 經 facade 建專案、
停用端點的 409 宣告、回填腳本、`ci.yml` 的 `concurrency` job、`tests_pg/`、`DEPLOY.md` §2.2.10、
`LOCAL-DEV.md`、manifest 與追溯檔。兩點如實記載：

- Step 5「不改 `backend/database.py`」：本分支相對 `origin/ut` 該檔有 +47／−2，來源是其他單元
  （`7ce1bee9` brain-infra、`c80aba97`／`f06dd1e7` 驅動改 psycopg v3、`369a5468` 合併 ut），
  **本單元（含本輪）沒有改它**；工作樹相對 HEAD 的 diff 為空。
- Step 5 的「聚合版 `assert_can_deactivate` 一次 `HAVING count(*) = 1`」已被本輪 15a 取代（見下），
  勾回的是「當輪交付成立」，現行形狀以本節為準。

### 二、Step 15 的實作與改動檔:行（行號為本輪結束時）

| 項 | 改動 | 檔:行 |
|---|---|---|
| 15a（#1＋#4） | 單一謂詞 `is_qualified_successor`（啟用、`user_can(..., "K3", "edit", authorization_status=...)`）與集合版 `qualified_successors`（一次 join ＋ 以角色為鍵的快取） | `backend/services/membership_service.py:467`、`:515` |
| 15a | `projects_losing_last_admin` 改為「是管理者且無合格接手人」 | `membership_service.py:572` |
| 15a | `reselect_for_project` 候選與冪等判定只算合格者；參數更名 `deactivated_user_id` | `membership_service.py:944` |
| 15a | `reselection_scope`＝擁有的 ∪ 是管理者的專案 | `membership_service.py:1035` |
| 15a（#4 邀請） | `assert_invitee_has_global_permission` 補 `is_active`；拒絕訊息說明帳號狀態 | `membership_service.py:849`；`membership_errors.py:75`（`reason`） |
| 15a | 刪除已無呼叫者的 `member_snapshots`（改由 `qualified_successors` 產生 `MemberSnapshot`） | `membership_service.py`（原 `:282`） |
| 15b（#10） | `ReselectionOutcome`（events／failed_project_ids／lock_timeout_project_ids） | `membership_service.py:1018`、`:1051` |
| 15b | `ReselectionFailureReport` | `backend/services/membership_types.py:130` |
| 15b | 停用端點：`responses=` 宣告 500／503；條件改為 `not request.is_active`（已停用帳號重送即重跑改選、不重跑守門）；失敗回 500，全部為逾時回 503 | `backend/services/user_router.py:962`、`:971`、`:1067`、`:1071` |
| 15c（#15） | 新模組 `membership_backfill.py`（`run_backfill`／`ensure_project_members_on_startup`），SQL 改 `CURRENT_TIMESTAMP`、前置檢查改 `inspect().has_table` 以支援 SQLite | `backend/services/membership_backfill.py`（新檔） |
| 15c | startup 在 `init_db()` 之後呼叫 | `backend/main.py:24`、`:98` |
| 15c | 腳本改呼叫同一函式（輸出與結束碼語意不變） | `backend/scripts/backfill_project_members.py` |
| 15d（#16） | `LOCK_TIMEOUT_MS = 5000`、`SET LOCAL lock_timeout = '5000ms'`（PostgreSQL 方言才送）、`55P03` 轉 `MembershipLockTimeout` | `membership_service.py:114`、`:180`–`:228` |
| 15d | `MembershipLockTimeout` | `membership_errors.py:108` |
| 15d | router 轉 503，三個取鎖端點宣告 `LOCK_TIMEOUT_RESPONSE` | `backend/services/membership_router.py:129`、`:159`、`:214`、`:257`、`:294` |

**合格接手人的詮釋（如實揭露）**：裁決字面是「只回報該使用者是最後一位 `project_admin` 且沒有
合格接手人的專案」，同一段又規定改選冪等判定的「已有其他管理者」只算合格者。本實作把守門的
「最後一位管理者」也以同一口徑計算（其他管理者不合格則不算），判準因此收斂為「該使用者是管理者、
且專案內除他以外沒有任何合格成員」。差別只在「另有一位**不合格**的管理者」那一格：字面讀法會放行，
而放行後改選的冪等判定不承認那位管理者、又找不到合格接手人，專案停用後實際無人能管——正是本項
要消除的狀態。`M7` 的第 (3) 格明示這一格。

**`NFR12.10` 的取捨**：守門不再是單次 `HAVING count(*) = 1`。現為「一次取管理者專案（含名稱）
＋ 一次 join 取這些專案的其他成員與帳號狀態 ＋ 至多『不同全域角色數』次的權限列讀取
（`user_can`，11 個 canonical role 為上界）」，與專案數、成員數都無關，不是逐專案 N+1。
不把合格判定寫成 SQL 的理由：權限矩陣只有一份（`role_permissions`，經 `user_can` 讀），
在 SQL 另寫一份會違反 `team.md` 的「單一真實來源」。

**15c 的 guard 判斷**：不加「表不存在就略過」。startup 路徑上兩張表由 `init_db()` 的
`Base.metadata.create_all()` 建立（`Project`／`ProjectMember` 都在 `models.Base`），表不存在代表
`init_db()` 沒完成，應該啟動失敗。既有測試不受影響的原因：`TestClient(app)` 不觸發 startup；
唯一觸發 startup 的 `test_brain_gateway_startup.py` 把 `init_db` 換成替身，故同步把新步驟換成替身，
並把順序斷言擴為 `routing → gateway → init_db → backfill`。

### 三、新增與改寫的測試

| 檔 | 測試 | 對應 |
|---|---|---|
| `backend/tests/test_membership_facade.py` | `F9`（有合格接手人→放行並升任）、`F10`（停用／待核准／僅 view 三種不合格成員各自不解除守門、不被升任）、`F11`（非擁有但為最後管理者的專案也被改選）、`F12`（PostgreSQL 方言替身：SQL 順序、`55P03` 轉譯、其他 SQLSTATE 原樣拋）、`F12b`（SQLite 不送 `lock_timeout`） | #1、#4、#16 |
| 同檔改寫 | `F7`（候選改為 `K3.edit` 的 erin／frank，並放入更早加入但不合格的 carol 作反例）、`F8`（被改選者改為 alice） | #1 |
| `backend/tests/test_membership_endpoints.py` | `E8`（邀請停用／待核准帳號→422 且無成員列，同角色啟用帳號 201 對照）、`E9`（注入單一專案失敗→500、列出該專案、另一專案已改選；重送→200、不重複事件）、`E10`（取鎖逾時→邀請／改角色／移出 503，停用端點 503） | #4、#10、#16 |
| 同檔改寫 | `E2`（橫幅事件的被改選者改為 alice） | #1 |
| `backend/tests/test_membership_data.py` | `M9`（補齊、dry-run、不把被移出的擁有者加回）、`M10`（冪等）、`M11`（終檢失敗→拋出、記 ERROR、無寫入） | #15 |
| 同檔改寫 | `M7`（參照實作改為逐專案逐成員套用 `is_qualified_successor`；新增「不合格第二管理者仍受阻」「改為合格後解除」兩格） | #1 |
| `backend/tests/test_brain_gateway_startup.py` | 啟動順序斷言加入成員補齊；`_quiet_startup` 加入其替身 | #15 |
| `backend/tests_pg/test_membership_concurrency.py` | 新增 `C4`（真實逾時）；`C3` 改為移出 bob（bob 是合格接手人，降級不足以讓守門擋下）；`setUpClass` 呼叫 `database._ensure_j5_schema()` 補上 `users.authorization_status`（`schema_rbac.sql` 沒有這一欄，而守門現在會讀它） | #1、#16 |

新增測試皆有 `@purpose`／`@given`／`@step`／`@pass`／`@story`（HTTP 者另有 `@api`）註解。

### 四、突變驗證（每項以 Edit 寫入帶 `# MUTANT` 標記的突變，`grep -c MUTANT` 確認為 1 後執行，還原後確認為 0）

| # | 突變 | 結果 |
|---|---|---|
| a | `is_qualified_successor` 拿掉 `is_active` 檢查 | **RED**：`F10`（inactive）兩個斷言 |
| b | 合格判定的 `user_can` 改傳 `authorization_status=None` | **RED**：`F10`（pending）兩個斷言 |
| c | `SUCCESSOR_ACTION` 由 `edit` 改 `view` | **RED**：`F10`（view_only）、`F2b`、`F7` |
| d | `reselection_scope` 只取擁有的專案 | **RED**：`F11` |
| e | 邀請端拿掉 `is_active` 檢查 | **RED**：`E8`（ivy） |
| f | 停用端點拿掉失敗回報（`if False and outcome.failed_project_ids`） | **RED**：`E9`（200≠500）、`E10`（200≠503） |
| g | 補齊 SQL 拿掉「無成員列」條件 | **RED**：`M10`（唯一約束 IntegrityError）、`M9`（插入 2 列） |
| h | `lock_project` 不送 `SET LOCAL lock_timeout` | **RED**：`F12`；真實 PostgreSQL 上 `C4` 亦 RED（T2 卡在 `waiting_for_lock` 直到 60 秒 join 上限） |
| i | 改選呼叫條件改回 `deactivating`（已停用帳號重送不重跑） | **RED**：`E9` 重送後 frank 仍是 member |

全部還原後 `grep -c MUTANT` 於 `membership_service.py`／`membership_backfill.py`／`user_router.py`／
`membership_router.py` 皆為 0。未做：`membership_router._translate` 的 503 分支沒有單獨突變（`E10` 直接覆蓋它的輸出）。

### 五、各命令的實際輸出

| 命令 | 結果 |
|---|---|
| `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest tests.test_membership_data tests.test_membership_facade tests.test_membership_endpoints tests.test_brain_gateway_startup` | **Ran 44 tests, OK** |
| `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests` | **Ran 1234 tests in 103.3s, OK** |
| `DATABASE_URL=postgresql+psycopg://postgres@localhost:55432/cloud360 … -m unittest -v tests_pg.test_membership_concurrency`（本機丟棄式 PostgreSQL 17.7 ＋ pgvector，套用 `schema_rbac.sql`） | **Ran 4 tests in 8.1s, OK**；`C4` 實測等待 5001.2 ms 後逾時 |
| 同上，`discover -s tests_pg` | **Ran 10 tests, OK** |
| 補齊函式與腳本在同一個 PostgreSQL 上實跑 | dry-run `before=1 inserted=0`、實跑 `inserted=1`、重跑 `inserted=0`；腳本 `--dry-run` 與實跑皆 exit 0 |
| `backend/.venv/bin/python backend/scripts/dump_openapi.py` 後 `--check` | 「規格檔與後端程式碼一致」，exit 0 |
| `cd frontend && npm run gen:types && npm run check:types` | 「API 型別檔與規格檔一致」，exit 0 |
| `python3 scripts/validate_repo_contract.py` | passed |
| `python3 scripts/validate_env_contract.py` | passed |
| `git diff --stat -- backend/database.py deploy/` | 無輸出（本輪未改） |

`openapi.json` 的重 dump 另外帶進一處**不是本單元的**差異：`DELETE /api/auth/{user_id}` 等兩個端點的
409 `DeleteUserConflict`（`hierarchy-data` 合併前必修第 3 項的未提交改動，先前未重 dump）。
現在規格檔與程式一致；這兩處屬 `hierarchy-data`，此處只記載來源。

### 六、未驗項

- **CI 的 `concurrency` job** 本輪未觸發（未 push）；`tests_pg` 只在本機丟棄式 PostgreSQL 17.7 驗過，
  CI 用的是 `pgvector/pgvector:pg18`。
- **staging 首次啟動時的自動補齊**未驗；本機只在丟棄式資料庫上驗了補齊函式與腳本。
- 多個 backend 行程同時啟動時兩邊同時插入同一列、其一撞唯一約束而啟動失敗的情境未驗；目前 compose
  只有一個 `uvicorn` 行程，重啟後冪等收斂（已寫入 `DEPLOY.md` §2.2.10）。
- 前端消費端（不在本單元，未改）：`frontend/src/pages/AdminPage.tsx:161-186` 的 `handleToggleActive`
  在 `!res.ok` 時以 `data.detail` 顯示錯誤 toast，故 500／503 會顯示本體的 `detail`（「帳號已停用，但下列
  專案的自動改選失敗……請重送」），但**不列出 `failed_project_ids`**，且該列不就地更新、仍顯示「啟用」
  ——操作者再按一次送出的正好是 `is_active=false`，即重送補跑。此行為只由讀碼推得，未以 e2e 驗證。

### 七、與計畫的偏離

1. 15c 改動啟動路徑（原 Step 12 寫「不動啟動路徑」），依裁決落在 `main.py`，`database.py` 不動，判準 3 仍成立。
2. 15d 的語句寫成 `SET LOCAL lock_timeout = '5000ms'`（由 `LOCK_TIMEOUT_MS` 產生，與 `'5s'` 等價），避免常數與字面值兩份。
3. 停用端點的逾時回 503 的條件是「失敗**全部**是取鎖逾時」；混合失敗回 500。裁決只說「停用端點轉 503」，
   而停用端點的取鎖只發生在改選、且已被逐專案捕捉成失敗清單，故以此收斂並宣告兩者共用同一個本體。
4. 修改了另一單元的測試檔 `backend/tests/test_brain_gateway_startup.py`（把新 startup 步驟換成替身並納入順序斷言），
   否則該檔觸發 startup 時會連一個不存在的 PostgreSQL 而失敗。
5. `tests_pg` 呼叫 `database._ensure_j5_schema()`（私有函式）而非在測試內另寫 DDL，理由是單一真實來源。
6. 計畫 §三之一的兩項 Minor（`R-01`／`R-02`）仍為開放，本輪未處理。

### 審查後補正（conductor，`2026-10-21T00:02:49Z`）

本站審查（`reviews/review-03.md`）判定 READY（0 Critical、0 Major、5 Minor）。收據登記、單元完成後補兩項：

| Minor | 處置 |
|---|---|
| 2：`reselect_for_project` 的「無合格管理者也無合格接手人」分支只記 INFO、端點回 200，與第 10 項「失敗不得無聲」相悖 | 新增 `membership_errors.NoQualifiedSuccessor`，該分支改為拋出；`run_auto_reselection` 既有的例外處理把它計入 `failed_project_ids`（記 ERROR），停用端點因而回 500。`test_F10` 補斷言三種不合格情形的專案皆出現在 `failed_project_ids`。突變 M-R1（改回 `return None`；`grep -c` 確認為 1）→ `test_F10` 三個子案紅；還原後 `grep -c MUTANT` 為 0 |
| 3：`membership_backfill.py` 終檢失敗訊息把原因推測為孤兒 `owner_user_id`，但 `projects.owner_user_id` 有外鍵 | 訊息改為指出可能是查詢條件不一致或並行寫入，並指向 `--dry-run` |

驗證：本單元四支測試檔 `Ran 44 tests` → `OK`；完整套件（`backend/.venv`）`Ran 1234 tests` → `OK`；`dump_openapi.py --check` 一致。

其餘三項 Minor（1：自我降級／移出仍用原始管理者數，口徑與停用守門不一致；4：`users.authorization_status` 不在 `schema_rbac.sql`、`tests_pg` 依賴私有 `_ensure_j5_schema()`；5：`AdminPage.tsx` 遇 500／503 不顯示 `failed_project_ids`）以已接受風險進入紀錄；第 5 項屬 `AdminPage`（單元外消費端）。本補正在收據登記之後進行，未經本站審查。

## 重做（Code Generation 自頭重來，2026-10-25）

<!-- 寫入時間：2026-10-25T07:02:11Z（`date -u` 取值） -->

Code Generation 依使用者裁決自頭重來；本單元計畫重新核可後，逐步查驗既有程式碼，**程式碼改動為 0**。後續單元對共用檔的改動一律保留。上節的補正本輪隨本單元送審。

### 計畫 67 格：勾 59、留 8

留下的 8 格，對應的程式都已落地、測試全綠，未勾的理由分兩類：

| 格 | 理由 |
|---|---|
| Step 5「聚合版用一次 `GROUP BY … HAVING count(*) = 1`」 | 已被 Step 15a 取代：現為兩次查詢 ＋ 依角色快取的 `user_can`（`projects_losing_last_admin`，`membership_service.py:573`）；「不取鎖」仍成立 |
| Step 6 等價測試 | M7 用明確案例，不是計畫要求的隨機成員集合；其 docstring（`test_membership_data.py:347` 起）仍描述 `HAVING` |
| Step 7b | 七個方法、principal 在前、具名 `project_id`、單一交易、冪等規則皆在（`membership_facade.py:200-459`），但「三條路徑共用同一個守門判定」已被 15a 改寫，停用路徑改用合格接手人判準 |
| Step 7c | 觸發範圍與冪等條件已被 15a 改寫：範圍為「擁有的專案 ∪ 為管理者的專案」，冪等只計合格管理者（`reselection_scope`、`reselect_for_project`） |
| Step 12 第一條「不動啟動路徑」 | 與 15c 改為啟動時自動補齊（`main.py:93-99`）直接矛盾 |
| Step 15a、15b、15c | 實作與測試皆在且綠，但框內含突變驗證；本輪未重跑，前一輪紀錄見本檔「重新查驗與合併前必修」節 |

### 合併前必修第 1、4、10、15、16 項：程式與測試皆在

| 項 | 程式 | 測試 |
|---|---|---|
| #1 | `is_qualified_successor`／`qualified_successors`／`projects_losing_last_admin`（`membership_service.py:468-637`） | F9、F10、F11 |
| #4 | `assert_invitee_has_global_permission` 的 `is_active` 檢查 | E8、F10 |
| #10 | `ReselectionOutcome`；改選失敗時停用端點回 500／503，重送會重跑改選 | E9 |
| #15 | `membership_backfill.py`，`main.py:99` 啟動時呼叫 | M9、M10、M11 |
| #16 | `SET LOCAL lock_timeout`（`membership_service.py:228`），逾時轉 503 | F12、F12b、E10、`tests_pg` C4 |

### 測試與閘門（本輪實跑，`backend/.venv`，快取導向 scratchpad，未寫入 repo）

| 指令 | 結果 |
|---|---|
| 本單元四個模組（data／facade／endpoints／gateway startup） | `Ran 47 tests`、`OK` |
| `discover -s tests` | `Ran 1319 tests`、`OK (skipped=3)` |
| `tests_pg` | `Ran 10 tests`、`OK`；C1–C4 全綠，C4 等待 5001.8 ms。**Homebrew PostgreSQL 17.7 ＋ pgvector**，scratchpad 一次性實例（`127.0.0.1:55439`），套用 `schema_rbac.sql` 後執行；跑完停機、刪除資料目錄，無殘留程序，未碰共用或 staging 資料庫。CI 用 pg18 |
| `dump_openapi.py --check`、`npm --prefix frontend run check:types` | 皆一致 |
| `validate_repo_contract.py`、`validate_env_contract.py` | 皆 passed |

### 與已核可計畫／測試說明的落差（凍結文件不改，以本節為準）

- 計畫 Step 9c 的停用端點行號 `:654`／`:676`／`:682` 現約為 `user_router.py:1058`、`:1062-1081`、`:1116`。
- 計畫 Step 5、7b、7c、12 與 §七判準 3 的字面已被 Step 15a／15c 改寫而框內原文未改（即上表的未勾格）。
- 計畫 Step 9b 與 10 的「無權 → 403」：自合併前必修第 14 項（另一單元）起，非成員改回 404，只有成員內權限不足與缺 `K3` 仍為 403（E1、E12）。
- 測試說明 §2.2 只列 `tests_pg.test_membership_concurrency`，CI 與 `LOCAL-DEV.md` 實跑 `discover -s tests_pg`，會一併跑其他單元的 PG 測試。
- 測試說明 §三的測試數 8／8／7／3（合計 26）已過時，現為 data 11、facade 14、endpoints 13、pg 4。

`source-manifest.json` 的 28 條路徑全部存在且含本單元內容；`membership_backfill.py` 目前為 untracked。工作樹中 `deploy/` 等其他未提交變更屬其他單元，不列入本 manifest。

## 共用檔異動後的重新驗證與補審（計畫 §八，2026-10-30）

<!-- 寫入時間：2026-10-30T15:21:42Z（`date -u` 取值） -->

本輪**未改任何程式碼、SQL、workflow、`merge-blockers.md` 或其他共用檔**；只寫本檔、計畫勾選。工作樹 HEAD 為 `c6a40f9`。

### 一、收據比對（`reviewed-source-6441893ae787.tsv`，最新一份，2026-10-25）

收據列 28 個檔案。`shasum -a 256` 實算：**27 個與收據逐位元相同**（含 `schema_rbac.sql` `27e92ecdc5d0…`、`ci.yml` `a854442aae2a…`、`LOCAL-DEV.md` `0f8c56a0a937…`、`user_router.py` `a08279001a0c…`、本單元全部 `membership_*.py`、四支測試檔、`openapi.json`、`api.d.ts`），**只有 `DEPLOY.md` 不同**：收據 `2608a131203c…` → 現況 `d9b0571c5688…`。

**`DEPLOY.md` 的逐 hunk 判定**（腳本 `scratchpad/ms_hunks.py`，以 `difflib` 對 `git show 624c170:DEPLOY.md` 與現況切出 19 個 hunk，窮舉 2^19 種回退組合比對收據雜湊）：**恰有一組**等於收據——回退現行 **730–738**、**2229**、**2239** 三處。故收據之後的變動只有這三處，與前面單元（`project-meta-data` 同一份收據雜湊）證得的 #24（730–738）、#26（2229、2239）一致。（`difflib` 切出 19 個 hunk、git 切出 15 個，切法不同但結論相同。）

- **#26（2229、2239 行）**：位於 §5.13「入口頁部署後實測（U14 entry-page-ui）」（起於 2223 行），不在本單元段落。
- **#24（730–738 行）**：位於 §2.2.9（U18，起於 617 行）的「前進步驟」小節（681 行起），**不在**本單元的 §2.2.10（951–1073 行）。改的是「忘了跑 U18 腳本的後果」：由「立即報 `relation does not exist`」改為「`create_all` 依 ORM 建出三張表、只缺 COMMENT；舊定義則缺 U20 收斂」。
- **對本單元段落的影響**：§2.2.10 第 991–993 行原本就寫「否則 `projects`／`project_members` 由 `create_all` 建立而缺 COMMENT，見 2.2.9；補齊本身仍會成功」——收據當時這句與 §2.2.9 的舊敘述**互相矛盾**，#24 之後兩者一致。本單元段落的事實（回填步驟、驗證指令、`NFR12.25` 的理由、回滾不對稱、部署面零變更）**均未改變**，不需改 §2.2.10。

### 二、回歸（scratchpad 副本，未寫入 repo）

`rsync -a --delete`（排除 `.git`、`node_modules`、`.venv`）至 `scratchpad/ms-copy/`，以 repo 的 `backend/.venv/bin/python` 執行：

```
env PYTHONPATH=<副本>/backend PYTHONDONTWRITEBYTECODE=1 HYPOTHESIS_STORAGE_DIRECTORY=<副本>/backend/.hypothesis \
  backend/.venv/bin/python -P -B -m unittest -v tests.test_membership_data tests.test_membership_facade tests.test_membership_endpoints
```

**與計畫指令的偏離**：計畫要求在副本的 `backend/` 下執行，但本環境每次 shell 呼叫都會重設工作目錄、且不得以 `;`／`&&` 串接 `cd`。第一次嘗試（工作目錄在 repo 根）得 `ModuleNotFoundError: No module named 'tests'`（3 個載入錯誤，非測試失敗）。改以 `PYTHONPATH` 指向副本的 `backend/`，並加 `-P` 使工作目錄不進 `sys.path`（避免載入 repo 本體）；三支測試檔的檔案存取全以 `Path(__file__)` 為基準（`grep -n "open(\|Path(\|getcwd\|chdir"` 實查），故工作目錄不影響結果。traceback 中的路徑全為 `scratchpad/ms-copy/backend/...`，證實載入的是副本。

**結果：`Ran 41 tests in 1.651s` → `OK`。** 分佈（逐一數 `-v` 輸出）：`test_membership_data` **12**（M1、M2、M3、M3b、M4、M5–M8、M9–M11）、`test_membership_facade` **16**（F1、F1b、F2、F2b、F3、F4、F5、F5b、F6、F7、F8、F9、F10、F11、F12、F12b）、`test_membership_endpoints` **13**（E1–E13）。

`tests_pg`（4 個本單元案例 C1–C4）**本輪不跑**（不啟資料庫）。沿用前輪紀錄：本檔「重做（2026-10-25）」節的「測試與閘門」表（`tests_pg` `Ran 10 tests`、`OK`，本機丟棄式 PostgreSQL 17.7）。收據之後 `backend/tests_pg/*`、`membership_*.py`、`schema_rbac.sql` 皆逐位元未變，故前輪紀錄的依據仍對應現行檔案。

### 三、review-04 R-06（Major）

由 `merge-blockers.md` **第 21 列**承接（2026-10-25T07:10:48Z 使用者裁決「**獨自一人的專案不擋**」，狀態「待處置」）。須做事項 (a)–(e) 見該列：守門對「除被停用者外沒有任何成員」的專案放行；有其他成員但皆不合格仍擋；刪除路徑由第 3 列接手；兩條端到端測試加各一次突變；同步 docstring 與 `DEPLOY.md`。本輪不改程式。現況複查：`projects_losing_last_admin` 仍在 `membership_service.py:573`，行為未變（收據後該檔逐位元相同）。

### 四、review-04 R-10（Minor）— 測試數更正

上節「與已核可計畫／測試說明的落差」末條寫的「data 11、facade 14、endpoints 13」**不正確**；以本輪實跑為準：**data 12、facade 16、endpoints 13，合計 41**（`tests_pg` 4 為前輪紀錄）。上節原文不回改，以本節為準。

**本輪未重跑突變驗證的計畫格**（本輪只跑回歸，未做任何突變）與其最近一次紀錄：

| 計畫格 | 最近一次突變紀錄的位置 |
|---|---|
| Step 15a（合格謂詞三條件、改選範圍） | 本檔「重新查驗與合併前必修…」節 §四 表 |
| Step 15b（拿掉失敗回報） | 同上 §四 表；`NoQualifiedSuccessor` 分支另見「審查後補正」表的 M-R1 |
| Step 15c（拿掉「無成員列」條件） | 同上 §四 表 |
| Step 15d（`lock_timeout`／503；計畫框內未指定突變） | 同上 §四 表末段（`_translate` 的 503 分支無單獨突變，已記為未做） |
| §七 判準 5（`concurrency` job 三條斷言） | 本檔 §三「突變驗證」突變 2 ＋ §十 判準 5 註記（只有 `C1` 有突變，`C2`／`C3` 無，已記為差異） |
| §七 判準 6（`select_successor` PBT tie-break） | 本檔 §三「突變驗證」突變 1；§八 PBT 表 |

### 五、review-04 其餘 Minor：現況複查（`grep -n`／`sed -n` 實查，HEAD `c6a40f9`），記為已知限制

全部**仍成立**（收據後相關檔案逐位元未變）。承接由 conductor 併入 `merge-blockers.md`（若已有對應列則引用）；本輪實查 `merge-blockers.md` 第 1–30 列，**沒有**一列已承接下列七項（第 4 列僅涵蓋邀請端擋停用／待核准，與 R-07 部分相關）。

| 發現 | 現況（行號證據） | 承接方向 |
|---|---|---|
| R-01 | `admin_count_after`（`membership_service.py:430-465`）仍以原始 `project_admin` 列數計數（`:461-465` 迴圈只比 `role`），`is_qualified_successor(` 在該檔只在 `:560` 被呼叫（`qualified_successors` 內），`assert_still_has_admin`（`:639`）的自我降級／自我移出未改用合格口徑；docstring `:444-448` 仍寫「仍以本函式擋下管理者數歸零」而未記載此殘留 | 改用 `is_qualified_successor` 計數（可與 R-07 一併解），或至少在 docstring 記載殘留。由 conductor 併入 `merge-blockers.md` |
| R-03 | 終檢失敗訊息已修（`membership_backfill.py:155`「projects.owner_user_id 有外鍵，不會是孤兒擁有者」），但模組 docstring `:28-29` 仍寫「持續性的失敗（例如某專案的 `owner_user_id` 指向不存在的使用者）」，兩者矛盾 | 只需改 docstring。由 conductor 併入 `merge-blockers.md` |
| R-04 | `authorization_status` 在 `schema_rbac.sql` 與 `DEPLOY.md` 皆 0 命中；`membership_service.py:540` 的 `qualified_successors` 讀 `User.authorization_status`；`tests_pg/test_membership_concurrency.py:130-146` 仍依賴 `_ensure_j5_schema()` 補欄並事後查 `information_schema` | 在 `DEPLOY.md` 記載部署前提（需後端啟動過一次），或 `schema_rbac.sql` 以 `IF NOT EXISTS` 補欄。由 conductor 併入 `merge-blockers.md` |
| R-05 | `AdminPage.tsx:161-186` 的 `handleToggleActive` 於 `!res.ok`（`:172`）只丟 `data.detail`，不更新該列、不顯示 `failed_project_ids`（全檔 0 命中）；409 的 `LastAdminGuardReport` 無 `detail`，toast 只顯示「更新狀態失敗」（`OPEN-CG19-3`） | 單元外消費端（前端）：500／503 就地標為已停用並列出失敗專案，409 列出擋下的專案；補 e2e 或手動案例。由 conductor 併入 `merge-blockers.md` |
| R-07 | 部分緩解：`assert_invitee_has_global_permission`（`membership_service.py:829-875`）已擋停用（`:850`）與待核准（`:857-863`），但要求的是 `K3.view`（`:76` `REQUIRED_INVITEE_ACTION = "view"`），未對 `role == project_admin` 套用 `is_qualified_successor`（要求 `K3.edit`）；`change_role`（`membership_facade.py:339-402`）升為管理者時亦不檢查合格性。只有 `K3.view` 的「名義管理者」仍可產生 | 對升為 `project_admin` 的寫入套用 `is_qualified_successor`，或令 `admin_count_after` 只計合格者（同時解 R-01）。與 `merge-blockers.md` 第 4 列相關但未被其涵蓋；由 conductor 併入 |
| R-08 | `_authorize_global`（`membership_facade.py:101-119`）只呼叫 `user_can(self._db, principal.role, STORY_ID, action)`，不帶 `authorization_status`；`is_approved` 在該檔 0 命中；`list_my_pending_reselections`（`:581`）與 `acknowledge_reselection`（`:593`）無任何授權檢查。目前唯一呼叫端是已掛 `require_story_action` 的 router，不可被利用 | 加 `principal.is_approved` 檢查並補待核准 principal 的 deny 測試，與其他三個 facade 一致。由 conductor 併入 `merge-blockers.md` |
| R-09 | `_BACKFILL_SQL`（`membership_backfill.py:76-82`）對零成員專案一律寫入擁有者為 `project_admin`，不看 `is_active`；`reselection_scope`（`membership_service.py:1034-1047`）只在停用動作時觸發，已停用擁有者的專案永不被改選；`DEPLOY.md` §2.2.10（951–1073）未記載此殘留 | 回填後列出「唯一管理者已停用」的專案數或對其跑一次改選；至少在 `DEPLOY.md` §2.2.10 記載。由 conductor 併入 `merge-blockers.md` |

### 六、計畫勾選

計畫全檔 74 格（`grep -c -- "- \[ \]"` 本輪開始時為 74，即重開後全部重設為未勾）＝ Steps 1–15 的 67 格 ＋ §八 的 7 格（Step 11 不適用、無格；§七 為編號清單、無格）。

**第一階段**只勾了 §八 的 6 格，「勾選重設」那格沒勾。之後 conductor 澄清該格屬已核可計畫、在交辦範圍內，**第二階段**依下列判準補做。

**判準**：以 10-25「計畫 67 格：勾 59、留 8」的逐格核對紀錄為基準；一格的證據在本輪仍成立（相關檔案自收據後逐位元相同，或本輪已重驗）才勾。收據之後唯一變動的檔案是 `DEPLOY.md`，它影響的格子逐一確認：
- Step 3「`DEPLOY.md §2.2.9` 8→9 欄」與 Step 14a：`DEPLOY.md:626` 仍為「`reselection_events` | **9 欄**（原 8 欄；第 9 欄 `cause` 由 `U19` 依 `[FD3]`=A 回補）」，§2.2.10（951–1073）不在收據後的 3 個 hunk 內（見本節「一」）。
- Step 15 最後一格（`DEPLOY.md`、`LOCAL-DEV.md` 同步；`merge-blockers.md` 第 1、4、10、15、16 列回填）：`LOCAL-DEV.md` 與收據相同；`merge-blockers.md` 這五列實查皆為「**已修正**（2026-10-21，…Step 15a／15b／15c／15d）」。

**第二階段本輪補做的重驗**（Step 15「`openapi.json` 重 dump…完整套件全綠」那格的依據涉及其他單元的程式，不能只靠收據比對）：
- 完整套件（scratchpad 副本，`backend/.venv`，`discover -s tests`）：`Ran 1326 tests in 97.625s` → `OK (skipped=3)`。
- `backend/scripts/dump_openapi.py --check`（副本）：「規格檔與後端程式碼一致。」`openapi.json` 與 `frontend/src/types/api.d.ts` 皆與收據逐位元相同，故型別無漂移；`npm run check:types` 本輪未另跑。
- `validate_env_contract.py`：passed；`validate_repo_contract.py`：passed（見「七」）。
- Step 5「不改 `backend/database.py`」：`git status --short` 為空，最後一次 commit 為 2026-10-01 的 `369a5468`（早於本單元）。

**結果**：Steps 1–15 勾 **59**、留 **8**；未勾的 8 格與 10-25 相同，沿用原理由（見「重做」節表格）：Step 5 聚合版（`:186`）、Step 6 等價測試（`:195`）、Step 7b（`:201`）、Step 7c（`:206`）、Step 12 第一格「不動啟動路徑」（`:253`）、Step 15a／15b／15c（`:308-310`，框內含突變驗證，本輪未重跑）。§八 7 格全勾（含「勾選重設」）。

**全檔實算**（`grep -c -- "- \[x\]"`）：已勾 **66**；`grep -n -- "- \[ \]"` 列出的未勾 **8** 格正是上列 8 格；66 ＋ 8 ＝ 74。

### 七、收尾

- `python3 scripts/validate_repo_contract.py`：`Cloud-360 repository contract validation passed.`
- `traceability.json`：本輪無應用程式碼或路徑變動，**不需更新**；以 `python3 -I` 的 `json.load` 驗證可解析（輸出 `ok dict`）。

處置紀錄（2026-10-30T15:21:42Z）：§八 重新驗證完成；`DEPLOY.md` 收據後 3 個 hunk 皆不在 §2.2.10、不改變本單元段落事實；回歸 41 測試 OK；R-06 由第 21 列承接；R-10 已更正；R-01／R-03／R-04／R-05／R-07／R-08／R-09 仍成立，記為已知限制待 conductor 併入 `merge-blockers.md`。勾選重設補做後全檔已勾 66／74（Steps 1–15 勾 59、留 8；§八 7／7）。

## 2026-11-07 第 21、31 列剩餘項與回歸

<!-- 寫入時間：2026-11-07T00:54:21Z（`date -u` 取值） -->

依計畫 §九 執行。`brain-infra` 交接給本單元的唯一非共用檔項目是第 31 列 (b)；本節只改下列三類檔：`backend/services/membership_backfill.py`（僅 docstring）、新測試檔、本單元紀錄檔。`merge-blockers.md`、`DEPLOY.md` 與其他共用檔未動。

### 一、第 31 列 (b)：docstring 更正

- `backend/services/membership_backfill.py:28-37`（原 `:28-30`；`git diff --stat` 為 10 行插入、3 行刪除，hunk `@@ -28,3 +28,10 @@`）：拿掉「例如某專案的 `owner_user_id` 指向不存在的使用者」這個例子，改為「失敗原因要看 log 判斷，不要預設是『擁有者指向不存在的使用者』」，說明 `projects.owner_user_id` 有外鍵指向 `users`，並列出兩類實際原因：(1) 終檢回報的剩餘零成員專案數不為 0（`BackfillVerificationError`）；(2) `INSERT` 本身拋出例外（看 `membership.backfill_failed` 之後的 traceback，例如多個 backend 行程並行補齊撞上 `uq_project_members_project_user`，重啟即冪等收斂）。措辭與 `:158-162` 的終檢訊息（行號為本輪改動後；改動前外鍵那句在 `:155`）及 `DEPLOY.md:1018-1020` 一致。
- **零行為變更的證據**：把 HEAD 版與現行版各自解析成 AST、去掉模組 docstring 後比對 `ast.dump`，結果相同（`True`）。
- 改動前 repo 的 sha256 `c66f16f5…bed50`；改動後 `d85a8f82…0c1aa`。

### 二、鎖住一致性的測試：**新增**（判斷與理由）

判斷為值得新增，而非只改文字。理由：同一個歸因有三個載體（模組 docstring、`run_backfill` 的終檢訊息、`DEPLOY.md` §2.2.10），2026-10-31 的修正改到後兩者，docstring 是事後才被審查查出的殘留——這正是「改了一處、漏了同一事實的另一種表達」的形狀，而 docstring 是維運者面對重啟迴圈時會讀的判斷依據。測試成本是兩個案例、無新依賴。

新檔 `backend/tests/test_membership_backfill_docstring.py`（未放進 `test_membership_data.py`，因後者同時列在 `project-pages-ui` 的 manifest，屬共用檔），兩案皆附 §4.4 規格註解（`@purpose`／`@given`／`@step`／`@pass`／`@story`）：

| 案例 | 鎖住什麼 |
|---|---|
| `B1` | 模組 docstring：凡提到「指向不存在的使用者」或「孤兒」的句子，同句必須帶「不要預設」「不可能」或「不會是」；且全文含「外鍵」「剩餘零成員專案數」「INSERT」 |
| `B2` | 終檢的執行期訊息（以 `patch.object(backfill, return_value=0)` 觸發，與既有 `M11` 同法）：含「仍有 1 個零成員專案」「外鍵」，且無未被否定的孤兒歸因 |

判準刻意不是「不得出現『孤兒』」：更正後的文字本身要否定地提到它，禁掉字串會逼人拿掉那句警告。否定詞清單刻意不含一般的「不是」——舊句後半有「不是讓服務在權限錯誤的狀態下運行」，含「不是」會讓舊句誤判為已否定。

`DEPLOY.md` 是多單元共用檔，不在本測試射程內。

### 三、突變驗證（scratchpad 副本，非 repo）

| 突變 | 結果 | 還原 |
|---|---|---|
| M1：把副本的 `membership_backfill.py` 換回 HEAD 版（舊句「`owner_user_id` 指向不存在的使用者」在 `:29`） | `B1` 紅：`AssertionError: Lists differ`，列出未否定的那一句；`Ran 2 tests`、`FAILED (failures=1)` | 換回新版後 `cmp` 與 repo 相同（`CMP_SAME`）；`Ran 2 tests`、`OK` |
| M2a：終檢訊息的「（projects.owner_user_id 有外鍵，不會是孤兒擁有者。）」整句改為「（可能是孤兒擁有者。）」 | `B2` 紅（紅在「外鍵」斷言） | `cmp` 相同 |
| M2b：只把「不會是孤兒擁有者」改為「可能是孤兒擁有者」（保留「外鍵」） | `B2` 紅：`Lists differ: ['（projects.owner_user_id 有外鍵，可能是孤兒擁有者'] != []` | `cmp` 相同 |

### 四、第 21、31 列其餘項的歸屬查證（`grep -n` 實查，行號為現況）

**沒有「屬本單元而未修」的項目**；第 31 列 (b) 是唯一的本單元項，已於本節處理。

| 列／項 | 現況與落點 | 歸類 |
|---|---|---|
| 21 (a) 除被停用者外無任何成員時放行 | `membership_service.py:724` `projects_with_others`，`:744` `project_id in projects_with_others and not qualified[project_id]`；改選端 `_has_other_members`（`:1054`）與 `reason=no_other_members`（`:1106`） | 已由 brain-infra 修正（A2） |
| 21 (b) 有其他成員但皆不合格仍擋下 | 同上 `:744` 的 `not qualified[...]`；`test_membership_lone_owner.py:111` | 已由 brain-infra 修正（A2） |
| 21 (c) 刪除時由第 3 項接手 | `user_router.py:1229`「請先停用帳號後再刪除」；空預設專案清除見 `:622`、`:575`，非預設獨人專案 `owned_projects`（`:478`） | 已由 brain-infra 修正（A2，接第 3 列既有實作） |
| 21 (d) 端到端測試＋突變 | `test_membership_lone_owner.py:86`、`:111`、`:133`；突變 M1–M3 記於 `brain-infra` `code-summary.md:430-437` | 已由 brain-infra 修正 |
| 21 (e) docstring 與 `DEPLOY.md` 同步 | `membership_service.py:668`「獨自一人的專案不擋」；`DEPLOY.md:519` | 已由 brain-infra 修正 |
| 31 (a) 自我降級／移出的管理者計數套合格謂詞 | `membership_service.py:458` `admin_count_after`，`:508` `is_qualified_successor`；docstring `:471`、`:482` | 已由 brain-infra 修正（A6） |
| 31 (c) 守門依賴 `authorization_status` 須記載 | `schema_rbac.sql:644-646` 純註解；`DEPLOY.md:1128` 「成員守門的兩個前提」 | 已由 brain-infra 修正（A6，文件化） |
| 31 (e) 升任 `project_admin` 須合格 | `membership_service.py:519` `assert_can_be_promoted_to_admin`；`membership_facade.py:392` 在 `change_role` 內呼叫 | 已由 brain-infra 修正（A6） |
| 31 (f) `_authorize_global` 看核准狀態、橫幅兩方法補授權 | `membership_facade.py:118` `principal.is_approved`；`:629`、`:639` `_authorize_global(principal, "view")` | 已由 brain-infra 修正（A6） |
| 31 (g) `_BACKFILL_SQL` 不看 `is_active` | SQL 未變（`membership_backfill.py:83-90`，刻意保留，2026-10-31 裁決「只寫進文件」）；`DEPLOY.md:1128` 小節第二點記載 | 已由 brain-infra 修正（文件化；SQL 刻意不變） |
| 31 (d)（不在本節查證範圍，附記） | `AdminPage.tsx:172` 仍只 `throw new Error(data.detail \|\| '更新狀態失敗')`，不處理 `failed_project_ids` | 仍為已知限制，承接列為第 31 列 (d)，屬前端 admin 頁所屬單元 |

### 五、回歸

scratchpad 副本（`rsync -a --exclude .git --exclude node_modules`，含 `frontend/`），`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.`，`HYPOTHESIS_STORAGE_DIRECTORY` 指向副本外的 scratchpad 目錄，以 `backend/.venv/bin/python -B` 執行：

| 指令 | 實跑輸出 |
|---|---|
| `-m unittest -v tests.test_membership_data tests.test_membership_facade tests.test_membership_endpoints` | `Ran 41 tests`、`OK` |
| 同上加 `tests.test_membership_backfill_docstring` | `Ran 43 tests`、`OK` |
| `-m unittest discover -s tests` | `Ran 1375 tests in 104.263s`、`OK (skipped=3)` |
| repo 內 `python3 -B scripts/validate_repo_contract.py` | `Cloud-360 repository contract validation passed.` |
| repo 內 `python3 -B scripts/validate_env_contract.py` | `Cloud-360 environment configuration contract validation passed.` |
| repo 內 `backend/scripts/dump_openapi.py --check`（`-B`，為核對 Step 15 那一格） | `規格檔與後端程式碼一致。` |
| repo 內 `npm --prefix frontend run check:types`（同上） | `API 型別檔與規格檔一致。` |

- repo 內快取數前後不變：`.pyc` 8576 → 8576、`__pycache__` 675 → 675、`.hypothesis` 路徑 377 → 377（`find` 實算，排除 `node_modules`）。
- `tests_pg` 本輪**未跑**（不啟資料庫），沿用前輪紀錄（「重做」節：`Ran 10 tests`、`OK`，本機丟棄式 PostgreSQL 17.7）。
- scratchpad 副本與 hypothesis 目錄已刪除。

### 六、計畫勾選

引擎在重新核可時把全檔勾選重設為未勾（本輪開始時 `grep -c -- '- \[x\]'` 為 0、`'- \[ \]'` 為 79 ＝ Steps 1–15 的 67 格 ＋ §八 7 格 ＋ §九 5 格）。判準沿用 10-30 的做法：前輪證據在本輪仍成立才勾；收據之後被改過的檔（`brain-infra` 於 2026-10-31 改了 `membership_service.py`、`membership_facade.py`、`DEPLOY.md`、`openapi.json`、`frontend/src/types/api.d.ts`、`.github/workflows/ci.yml`、`backend/database.py` 等）逐一重驗相關格：

- 全套 1375 測試綠、本單元 41 測試綠（見「五」），涵蓋 Steps 4、6、8、10、15 各格所指的測試；
- Step 3／14a：`DEPLOY.md:685` 仍為「`reselection_events` | **9 欄**」，§2.2.10 在 `:1010`；
- Step 13：`ci.yml:567` `concurrency:` job、`:593` `timeout-minutes: 15`、`:610` `pgvector/pgvector:pg18`、`:649` `discover -s tests_pg`；
- Step 15 最後一格：`merge-blockers.md` 第 1、4、10、15、16 列仍為「**已修正**（2026-10-21，…）」；Step 15 的 openapi／型別那格：見「五」的兩條檢查；`openapi.json` 中 `"409"` 11 處；
- Step 14c：`source-manifest.json` 加入新測試檔後 29 條，全部存在（`os.path.exists` 實查）。

**結果**：`grep -c -- '- \[x\]'` 為 **70**、`grep -c -- '- \[ \]'` 為 **9**（70 ＋ 9 ＝ 79）。Steps 1–15 勾 58、留 9；§八 7／7；§九 5／5。

未勾的 9 格：
- 與 10-30 相同的 8 格，理由不變（見「重做」節表格）：Step 5 聚合版（`:186`）、Step 6 等價測試（`:195`）、Step 7b（`:201`）、Step 7c（`:206`）、Step 12 第一格「不動啟動路徑」（`:253`）、Step 15a／15b／15c（`:308-310`，框內含突變驗證，本輪未重跑）。
- **新增 1 格：Step 5「不改 `backend/database.py`（判準是該檔 diff 為空）」（`:188`）**。10-30 時 `git status --short backend/database.py` 為空；本輪為 ` M`，`git diff --stat` 為 72 行插入——來自 `brain-infra` 依合併前必修第 20／29 列新增的記憶專用連線（該檔列在 `brain-infra` 的 manifest，不在本單元的）。本單元自身仍未改它，`SessionLocal`／`engine` 兩行也未動（`NFR12.5` 的實質「不改 `SessionLocal`」仍成立），但這一格寫明的判準是「該檔 diff 為空」，字面已不成立，故留空，待 conductor 判定是否以「本單元未改、`SessionLocal` 未動」改判。`traceability.json` 的 `NFR12.5` 附註已同步記載此事。

### 七、追溯與 manifest

- `traceability.json`：新增 reverse 條目 `CG-MB31-B`（target 為新測試檔），記載第 31 列 (b) 在本單元的處置與突變結果；第 31 列 (b) 已關閉，故未新增 open item。`NFR12.5` 的 note 附加 2026-11-07 更正（見上）。`python3 -I` 的 `json.load` 驗證可解析（`ok dict`，reverse 18 條、open_items 18 條）。
- `source-manifest.json`：新增 `backend/tests/test_membership_backfill_docstring.py`（共 29 條）。

處置紀錄（2026-11-07T00:54:21Z）：第 31 列 (b) docstring 已更正、新增 `B1`／`B2` 並經突變驗證；第 21 列 (a)–(e) 與第 31 列 (a)(c)(e)(f)(g) 皆已由 brain-infra 處理，無屬本單元而未修的項目；回歸 41／43／1375 測試 OK、兩支 validator passed、repo 快取數不變；勾選 70／79。
