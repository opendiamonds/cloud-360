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
