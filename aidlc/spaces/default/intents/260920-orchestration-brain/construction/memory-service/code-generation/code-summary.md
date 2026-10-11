# Code Generation 摘要 — `U8 memory-service`

> 方法論 `test-after`（契約指紋 `sha256:1f0b6822…3f2f77`）：每層先實作再測。
> 全部驗證皆在本機實跑，含**真實 PostgreSQL 17.7 ＋ pgvector 0.8.1** 上的
> `S14`／`S15`。

## 〇、一眼看完

| 項目 | 值 |
|---|---|
| 新增應用程式模組 | 6（四層形狀） |
| 新增測試檔 | 3 |
| 修改既有檔 | 8 |
| **自動化斷言** | **41 個 unittest**（11 靜態 ＋ 7 排序 ＋ 23 授權／端點）＋ psql 的 **4 個指定斷言 id**（`S14`、`S15` ①②③），實作為 **8 個 `RAISE EXCEPTION` 失敗點**（`S14` 3 ＋ `S15` 3 ＋ 2 個 fixture 前提守門） |
| 既有測試 | **574 passed, 0 failed**（開工前 533；新增 41） |
| 突變驗證 | **6 項全部確認紅燈後還原複驗**（另加 1 項衍生實驗） |
| 四項 diff 須為空 | **全部通過**（`database.py`／`requirements.txt`／`deploy/`／`ci.yml`） |

**最重要的一項發現**：計畫 Step 9 的突變 3 期望 `S15` ③ 變紅，而**實測
`S15` 三條全部維持綠燈**——`S15` 是純 psql，看不到 Python。詳見 §四之三。

## 一、交付物清單（逐檔一行理由）

### 1.1 新增的應用程式模組（6）

| 路徑 | 層 | 理由 |
|---|---|---|
| `backend/services/memory_types.py` | 型別 | `K-08` 引用的值物件 ＋ `EC3` 三處封閉集合的應用層落點 |
| `backend/services/memory_errors.py` | 例外 | 四個領域例外，**皆非** `HTTPException` 子類（facade 同時被 HTTP 與同進程消費） |
| `backend/services/memory_ranking.py` | **純函式** | `NFR3.24` 的次級排序鍵；import 集合恰為 `{__future__, typing}` |
| `backend/services/memory_service.py` | service | 單一 SQL（`SEARCH_SQL`）＋ 兩條單一交易邊界 |
| `backend/services/memory_facade.py` | facade | `K-08` 的 `sole_entry`：兩套授權模型各一份 ＋ `[D1]`=A 的回應收斂 |
| `backend/services/memory_router.py` | HTTP | 五條路由；**零授權判定、零角色名稱字面值** |

### 1.2 新增的測試（3）

| 路徑 | 條數 | 內容 |
|---|---|---|
| `backend/tests/test_memory_contract.py` | 11 | 四層禁令（`ast`）、ORM↔SQL 一致性、日誌衛生、`SEARCH_SQL` 結構 |
| `backend/tests/test_memory_ranking.py` | 7（含 **5 個 `@given`**） | 排列不變性、分數遞減、同分識別字遞增 ＋ 三個具體例 |
| `backend/tests/test_memory_authz.py` | 23 | 兩套授權模型、`[D1]`=A 三案例、酬載忽略、`limit` 上限、分頁、交易邊界 |

### 1.3 修改的既有檔（8）

| 路徑 | 變更 |
|---|---|
| `backend/models.py` | 新增兩個 ORM 模型（`embedding` 刻意省略）＋ SQLite ATTACH shim ＋ `before_create` 守門 |
| `backend/main.py` | 註冊 `memory_router`，prefix `/api/memory` |
| `schema_rbac.sql` | `I)` 區塊新增 HNSW 索引（`IF NOT EXISTS`，opclass `vector_cosine_ops`） |
| `backend/scripts/run_meta_schema_migration.py` | `EXPECTED_INDEXES` 新增該索引（索引數 7 → **8**） |
| `backend/scripts/verify_memory_schema.sql` | 新增 `S14`（1 條）與 `S15`（3 條） |
| `DEPLOY.md` | 新增 §2.2.12；更正 §2.2 總表的 `I` 列與 §2.2.8 一處過期計數 |
| `openapi.json` | 重 dump（路徑 51 → **55**） |
| `frontend/src/types/api.d.ts` | 重跑 `gen:types` |

### 1.4 刻意不動（diff 為空即是證據）

| 路徑 | 判準 |
|---|---|
| `backend/database.py` | 計畫 Step 1.1／10.1 |
| `backend/requirements.txt` | `NFR8.20` 第一項判準（**也是** ORM 省略 `embedding` 的理由） |
| `backend/.env.example` | 零新環境變數 |
| `deploy/`、`.github/workflows/ci.yml` | 零新部署設定、不新增 CI job |

**`deploy/` 與 `ci.yml` 在本單元開工前已帶有先前單元的改動**，故「diff 為空」
在此的正確判準是**與開工基準逐位元相同**。開工時錄下基準
（`sha256` 前 16 碼 `7d3fe2e44fb0e350`），收尾複驗結果相同 → 本單元未添加任何改動。

## 二、計畫 §1.1–§1.4 的四項實測處置

| 計畫項 | 處置 |
|---|---|
| §1.1 記憶表無 ORM 模型 | 已補兩個模型。實測確認：補之前 SQLite 無表，補之後 574 測試全綠 |
| §1.2 `embedding` 不能進 ORM | 確認。`requirements.txt` diff 為空，ORM 為八欄部分鏡像；但**寫入路徑另需處置**，見 §三之二 |
| §1.3 向量檢索走原生 SQL | 確認，且**寫入方向同樣必須**（§三之二） |
| §1.4 router prefix | 照既有形狀 `app.include_router(memory_router, prefix="/api/memory")` |

## 三、與計畫不一致之處（5 項，逐項附依據）

### 3.1 Step 2.4「不加 `CheckConstraint`」——**未照做，且這是刻意的**

計畫逐字「**不加 `CheckConstraint`**：封閉集合在應用層承載（沿用 `U18` 先例）」。
**本單元鏡像了 `I)` 區塊的全部四條具名 CHECK。**

依據是 repo 自己寫下的明文教訓。`backend/models.py` 的 `U19` 區塊逐字：

> **約束必須與 DDL 逐條對齊，不只是欄位**（`U7` 已踩過這個洞）……納入 `Base`
> 之後，`database.py:90` 的 `Base.metadata.create_all(bind=engine)` 就成為
> **第二條建表路徑**，於是「少寫一條 CHECK」等於在測試環境裡悄悄移除它。

而計畫引用的 `U18` 先例其實指向相反方向：`project_members.role` 的
`ck_project_members_role` 在 DDL 與 ORM **都有**；`U18` 真正刻意不加 CHECK 的是
`reselection_events.previous_role`／`new_role`，而那兩欄在 **DDL 側也沒有**。
**判準是「DDL 有沒有」，不是「封閉集合由誰承載」。**

兩者並不矛盾：`visibility_scope`／`previous_scope`／`new_scope` 在 DDL 確實沒有
約束（`FD8-3`），由 `memory_types.VISIBILITY_SCOPES` 承載；`kind` 與 `action`
的 DDL 有，故 ORM 必須有。

**實測證明這不是風格之爭**：三條 CHECK 在 SQLite 上**真的會擋**
（`bad kind`／`blank content`／`episodic w/o expiry` 皆得 `IntegrityError`）。
照計畫字面實作會讓它們在 SQLite 測試環境裡靜默消失——而 `A15`（交易邊界）
正是靠 `ck_memory_audit_events_action` 在 SQLite 上生效才測得起來。
既有的 `test_membership_data.py` 的 `M3` 就是斷言「ORM 與 DDL 的具名約束集合
**相等**」，本單元的 `C4` 沿用它。

### 3.2 Step 6.1 ①②的字串比對——改以 `ast` 實作

計畫寫「`memory_ranking.py` **不含** DB session 型別、`HTTPException`」。
照字面做成 `"HTTPException" in source` 會**永遠紅燈**：這三個模組的 docstring
都在解釋「為什麼不拋 `HTTPException`」。

`services/membership_selection.py` 的檔頭逐字記下了這個陷阱：

> 對本檔跑裸 `grep` 會各命中一次——就是上面這段散文自己。
> **量測純度要看 import 集合與程式行，不是整個檔案的字串命中。**

故 `C1`／`C2` 以 import 集合 ＋ AST 程式行節點斷言，`C3` 以**非 docstring 的
字串字面值**斷言。斷言比字面更強：`C1` 要求 import 集合**恰為**
`{__future__, typing}`（而非「不含某些項」），故「多一個 import」也會紅。

### 3.3 Step 5.5「六條路由」——實際五條

`functional-spec.md §〇` 的表有六列，但第 2 列（`MemoryFacade.search`）的 HTTP
欄逐字是「—（同進程，`U11` 消費）」，而 `cicd-pipeline.md §三之一` 再次確認
「`search` 有 HTTP 端點嗎 → **沒有**」。計畫數到的是六個 **facade 方法**。

**刻意不為 `search` 開端點**——那會同時牴觸上述兩處已核可敘述。

### 3.4 `rules.md` 的「22 條 BR」實為 **24 條**（上游計數錯誤）

機械實算：`grep -cE "^  - id: BR" rules.md` → **24**。
各組計數（`BR1`=2、`BR2`=3、`BR3`=5、`BR4`=3、`BR5`=4、`BR6`=3、`BR7`=4）
**逐項正確**，相加為 24，但 `rules.md:367` 與 `functional-spec.md:204` 的
「合計 22」與之不符，且該數字傳播進了本站的計畫標頭。

**不回改已核可的上游產出**（`refined-mockups:c3` 的形狀）；
`traceability.json` 如實登錄全部 **24** 條。

### 3.5 Step 2.2 的 SQLite schema 問題——以 `models.py` 的 shim 解決

實測：`{"schema": "memory"}` 之下 SQLite 的 `create_all()` 以
`unknown database memory` 失敗，而 `create_all` 走訪**整個** `Base.metadata`，
故受害的是 `backend/tests/` 的**每一個**測試檔。

處置是在 `models.py` 加一個 `Engine` 層級的 `connect` listener，對 SQLite
（以 `isinstance(conn, sqlite3.Connection)` 判斷）執行
`ATTACH DATABASE ':memory:' AS memory`。放在 `models.py` 而非 `helpers.py` 的
理由：`helpers.py` 的既有語意不得改動（計畫 Step 2.2），而 shim 必須在任何
engine 連線之前就位。對 PostgreSQL 為無作用。

## 四、突變驗證（6 項計畫項 ＋ 1 項衍生，全部實跑）

每項：套用 → 確認紅燈（保留實際輸出）→ 還原 → 確認綠燈。
收尾以逐檔 `diff` 確認**零殘留**（6 個檔全部 `clean`）。

### 突變 1 — `delete` 的非擁有者改回拋 `MemoryForbidden`（→ 403）

**紅燈，4 項失敗**：

```
FAIL: test_A5_other_user_deleting_gets_404_and_an_owner_reason_log
AssertionError: 403 != 404 : 非擁有者必須得到 404 而非 403（[D1]=A）——403 會重開整張表的枚舉 oracle
FAIL: test_A5_A6_are_externally_indistinguishable      AssertionError: 403 != 404
FAIL: test_A7_platform_admin_cannot_delete_another_users_memory  AssertionError: 403 != 404
FAIL: test_A12_404_body_never_contains_the_fixture_content       AssertionError: 403 != 404
Ran 23 tests ... FAILED (failures=4)
```

### 突變 2 — 移除 `delete` 失敗路徑的 `reason="owner"` 日誌

**紅燈，1 項失敗**，而這一項正是重點：

```
FAIL: test_A5_other_user_deleting_gets_404_and_an_owner_reason_log
AssertionError: no logs of level WARNING or higher triggered on cloud360.memory_service
Ran 23 tests ... FAILED (failures=1)
```

**狀態碼完全沒有變化**（`A5`／`A6` 都仍是 404，
`test_A5_A6_are_externally_indistinguishable` 照樣綠）——這正是
`security-design.md §二之二` 預見的情境：一個「連日誌也收斂」的實作在對外
行為上完全正常，而枚舉行為變得不可見。**只有日誌斷言抓得到它。**

### 突變 3 — `search` 改為先查 `LIMIT n` 再於應用層過濾

**這一項的結果與計畫的期望不同，且差異本身是本單元最重要的發現。**

| 斷言 | 計畫期望 | **實測** |
|---|---|---|
| `S15` ① | 綠 | **綠** |
| `S15` ② | 綠 | **綠** |
| `S15` ③ | **紅** | **綠 ← 不符** |
| `C6`（本站新增） | — | **紅，2 項失敗** |

```
# psql 全檔（S1–S15）：exit=0，S14／S15 皆 NOTICE 通過
FAIL: test_C6_search_sql_is_one_statement_with_both_filters
AssertionError: 'owner_user_id = :principal_user_id' not found in ' where kind = any(cast(:kinds as varchar[]))'
FAIL: test_C6_s15_query_agrees_with_the_service_sql (fragment='無向量的列（BR3.3）')
AssertionError: 'embedding is not null' not found in 'select id, ... from memory.memory_records where kind = any(...) order by ... limit :limit'
Ran 41 tests ... FAILED (failures=2)
```

**根因**：`S15` 是**純 psql**。它執行 `verify_memory_schema.sql` 裡的查詢，
**完全看不到 Python**。改 `memory_service.SEARCH_SQL` 不會讓它的任何一條變色。

故 `S15` 證明的是「**這樣寫的 SQL** 在真實 PostgreSQL 上行為正確」，
**不是**「服務真的這樣查」。後者需要 Python 側的斷言——那就是 `C6`
（本站對計畫的新增，見 §五之一）。

### 突變 3b（衍生實驗）— 把同一個突變套在 `S15` **自己執行的** SQL 上

為了確認 `S15` ③ 本身**有**鑑別力，另把 query-then-filter 套進 `S15` 的查詢：

```
NOTICE:  S14（HNSW 索引存在／型態／opclass／planner 可用）通過
ERROR:  S15 ③ FAILED (performance-design §一): 過濾後候選數為 4（< LIMIT 5），
        故回傳筆數應等於 4，實際 2。這個差距的意思是 LIMIT 作用在**未過濾**的
        集合上——即「先查再於應用層過濾」。①② 對那種實作仍會通過，只有本條會紅。
psql exit=3
```

**`S14` 綠、`S15` ①② 綠、只有 ③ 紅**——與計畫的期望逐字相符。
結論：`S15` ③ 的設計是對的，射程是「它執行的那段 SQL」。

**本輪另修了 `S15` 的 fixture 使 ③ 的紅燈成為決定性的。** 初版七列共用同一個
向量 ⇒ 距離全部相同 ⇒ 排序任意 ⇒ 錯誤實作有 `C(3,1)/C(7,5)=3/21` 的機率
剛好把四個好列都取進那五筆而讓 ③ 通過。那會是一個**偶爾變綠**的斷言，
比沒有斷言更糟。修法：讓三個「應被濾掉」的列**離查詢向量最近**（距離 0）、
四個「應留下」的列最遠（距離 2）。實測：正確實作回 **4**、錯誤實作回 **2**。

### 突變 4 — HNSW 索引的 opclass 改為 `vector_l2_ops`（與 `<=>` 不相符）

**紅燈，三處獨立命中**：

```
# psql
ERROR:  S14 FAILED (U8/NFR3.22): 索引應為 hnsw/vector_cosine_ops，實際 hnsw/vector_l2_ops。
        opclass 必須與 memory_service.SEARCH_SQL 的距離運算子 <=> 成對…
# Python
AssertionError: 'vector_l2_ops' != 'vector_cosine_ops'   （C6）
# 行為面（S14c 單獨查證）：enable_seqscan=off 之下計畫退化為 Sort
Limit → InitPlan 1 → Result → Sort → Sort Key: ((memory_records.embedding <=> …))
```

第三項證明 `S14` 的 `EXPLAIN` 斷言**不是** metadata 檢查的冗語：
它驗的是「索引可用」，而只有行為面看得出 opclass 不符會讓 planner 放棄索引。

### 突變 5 — `memory_ranking` 移除次級排序鍵

**紅燈，4 項失敗**，其中 PBT 找到反例：

```
FAIL: test_permutation_invariance
AssertionError: Lists differ:
  [('', 0.0), ('', 0.0), ('', 0.0), ('', 0.0), ('', 0.0), ('', 0.0), ('0', 0.0)]
!=[('', 0.0), ('', 0.0), ('', 0.0), ('', 0.0), ('', 0.0), ('0', 0.0), ('', 0.0)]
FAIL: test_ties_break_on_ascending_identifier   AssertionError: '0' not less than or equal to ''
FAIL: test_known_tie_is_broken_deterministically    AssertionError: ['9', '10'] != ['10', '9']
FAIL: test_negative_zero_ties_with_positive_zero    AssertionError: ['b', 'a'] != ['a', 'b']
Ran 7 tests ... FAILED (failures=4)
```

### 突變 6 — ORM 多宣告一個不存在於 SQL 的欄位（`pinned_by_user`）

**紅燈**：

```
FAIL: test_C4_orm_mirrors_sql_columns
AssertionError: Items in the first set but not the second:
'pinned_by_user' : memory.memory_records：ORM ∪ {'embedding'} 應等於 DDL
                   (ORM only={'pinned_by_user'}, DDL only=set())
Ran 11 tests ... FAILED (failures=1)
```

## 五、計畫未預見的事（4 項）

### 5.1 `S15` 看不到 Python，故需要一個 Python 側的鎖（已補 `C6`）

見 §四之三。`C6` 同時滿足 `team.md ## Code Style` 的「單一真實來源」：
同一個查詢在 `SEARCH_SQL` 與 `S15` 各有一份物化，而該規則逐字要求
「若確實無法避免（如跨語言邊界），**新增副本的同一個 PR 必須一併新增鎖住
兩者一致的測試**」——psql 無法 import Python，正是跨語言邊界。

### 5.2 **`embedding` 寫不進去**：計畫 §1.2 的理由只套用在讀的那一半

計畫 §1.2 的理由逐字「向量路徑本來就走原生 SQL……ORM 只服務非向量路徑」。
那句話必須**同時**套用在讀與寫兩個方向上。

只套用在讀的那一半會得到一個**功能完整但永遠寫不進向量**的實作：每一列的
`embedding` 都是 NULL，於是 `SEARCH_SQL` 的 `embedding IS NOT NULL` 把它們
全部濾掉，**相似度檢索永遠回空集合而不報任何錯**——而 `BR3.3`
（無向量的列不被看到且不是錯誤）會讓它看起來完全正常。

處置：八個可鏡像的欄位走 ORM，`embedding` 隨後以
`UPDATE … SET embedding = CAST(:v AS vector)` 補上，**兩者同一個交易**
（`db.flush()` → `UPDATE` → 一次 `commit()`）。
PostgreSQL 以外的後端跳過該 `UPDATE`（SQLite 根本沒有那個欄位）。

### 5.3 ORM 成為第二條建表路徑，而它缺一個欄位——已加守門並實測

把兩張表納入 `Base` 之後，`create_all` 在「`memory` schema 存在但表不存在」
的 PostgreSQL 上會建出一張**缺少 `embedding`** 的 `memory_records`，
而之後重跑 `schema_rbac.sql` **也補不回來**（`CREATE TABLE IF NOT EXISTS`
整段 no-op）⇒ 向量檢索永久失效且無任何錯誤。

`U19` 的 `OPEN-ID19-1` 記載過同形問題的較輕版本（建出來的表沒有 COMMENT）；
本單元的版本嚴重得多，因為少的是一個**欄位**。

處置：兩張表各掛一個 `before_create` listener，在 PostgreSQL 上**拒絕**並印出
處置方式。**兩個方向都已實測**：

| 情境 | 實測 |
|---|---|
| schema 存在、表不存在 | `RuntimeError: 拒絕以 create_all() 建立 memory.memory_records…處置：先套用 schema_rbac.sql，或執行 run_meta_schema_migration.py` |
| 表已存在（正常路徑） | **no-op，守門未觸發**；真實表仍為 9 欄且含 `embedding` |
| SQLite | 不在守門範圍（那裡 `create_all` 正是我們要的建表路徑） |

另一個方向**刻意不處置**：`memory` schema 不存在時 `create_all` 會以
`schema "memory" does not exist` 失敗而導致**啟動失敗**。這是刻意保留的大聲
失敗——替代方案（自動 `CREATE SCHEMA`）會把它變成上表第一列那個靜默情境。
已寫入 `DEPLOY.md §2.2.12` 作為既有環境的部署前置條件。

### 5.4 `EMBEDDING_PROVIDER=fulltext` 之下 `write` 無法成立（`CG8-1`，**上游契約缺口**）

| 事實 | 依據 |
|---|---|
| `fulltext` 之下 `model_id` 為 `None` | `embedding_port.py:379` 逐字 `model_id=None` |
| `memory_records.embedding_model` 為 **NOT NULL** | `schema_rbac.sql` 的 `I)` 區塊 |
| 「即使 `embedding` 為 NULL 本欄仍必填」 | `entities.md` 的 `embeddingModel` 逐字 |
| **而 `backend/.env.example:120` 的預設正是 `fulltext`** | 實查 |

**三者直接對撞，且沒有任何已核可來源說過 fulltext 之下該欄要填什麼。**

處置是**大聲失敗並說明兩個可行方向**，而不是自行發明哨兵值：
`MEMORY_RECORD_EMBEDDING_MODELS` 是 `U6` 已交付的封閉集合
（`("bge-m3", "multilingual-e5-large", "stub-v1")`），往裡面塞 `"fulltext"`
會替一個跨單元契約做決定，並在資料層產生第四個向量空間身分——而
`schema_rbac.sql` 的 COMMENT 逐字要求換模型身分必須同時規劃既有列的遷移
（`ADR-008`）。

**這一項未加自動化斷言**（連帶 `NFR4.22`／`NFR7.32`／`NFR7.34` 三條亦未斷言），
列為 open item，見 §七。

## 六、本單元執行的指令（逐條，皆限定於本單元）

### 6.1 unittest（不需資料庫 ＋ SQLite）

```bash
cd backend && python3 -m unittest tests.test_memory_contract tests.test_memory_ranking tests.test_memory_authz -v
```

**實跑結果：`Ran 41 tests … OK`**（11 ＋ 7 ＋ 23）。

### 6.2 真實 PostgreSQL 的斷言（於 repo 根目錄）

```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d cloud360 \
  -v ON_ERROR_STOP=1 -f backend/scripts/verify_memory_schema.sql
```

**實跑結果：`exit=0`，5 條 `NOTICE` 全部通過**（含 `S14`、`S15`）。
`NOTICE` 是**斷言群**的數量（本檔原有 3 群 ＋ 本單元新增 `S14`／`S15` 兩群）；
本單元新增的失敗點共 **8 個**（見 §〇 的表）。
本機以 `u8_verify` 庫複製 CI 條件：**套用 `schema_rbac.sql` 兩次**
（`BR1.3` 可重跑性，兩次皆 `exit=0`）後執行。
環境為 PostgreSQL **17.7** ＋ pgvector **0.8.1**（CI 用 `pgvector/pgvector:pg18`）。

### 6.3 收尾核對（Step 10）

| # | 指令 | 結果 |
|---|---|---|
| 10.1 | `git diff --stat -- backend/database.py` | **空** |
| 10.2 | `git diff --stat -- backend/requirements.txt` | **空** |
| 10.3 | `git diff -- deploy/ .github/workflows/ci.yml` 與開工基準比對 | **逐位元相同**（`sha` 前 16 碼 `7d3fe2e44fb0e350`，前後一致） |
| 10.4 | `python3 scripts/validate_repo_contract.py` | `validation passed` |
| 10.4 | `python3 scripts/validate_env_contract.py` | `validation passed` |
| 10.5 | `cd backend && python3 -m unittest discover -s tests` | **`Ran 574 tests … OK`** |
| 10.6 | `cd backend && python3 scripts/dump_openapi.py --check` | `規格檔與後端程式碼一致。` |
| 附 | `cd frontend && npm run check:types` | `API 型別檔與規格檔一致。` |
| 附 | `run_meta_schema_migration.py`（對 `u8_verify`） | `終檢通過`；索引數 **8**（含新索引） |

## 七、Open items（逐項附承接）

| id | 內容 | 承接 |
|---|---|---|
| **`CG8-1`** | **`fulltext` 之下 `write`／`search` 不可用**（`model_id=None` vs `embedding_model NOT NULL`），而它是 `.env.example` 的**預設值**。本單元大聲失敗，不自行發明哨兵值 | **須於本站核可關卡提交使用者**——它牽涉 `U6` 已交付的封閉集合與 `ADR-008` 的遷移規劃 |
| `CG8-2` | `NFR4.22`／`NFR7.32`／`NFR7.34` 三條**無自動化斷言**：前兩條落在 `fulltext`／提供者不可用路徑（同 `CG8-1`），第三條（空結果的兩道候選筆數）在 SQLite 上不可達——`search` 的向量路徑在那裡不存在 | `build-and-test`；`NFR7.34` 可考慮併入 `S15` 的 psql 情境 |
| `CG8-3` | `rules.md:367`／`functional-spec.md:204` 的「合計 22」實為 **24**（§三之四） | 下一輪上游修訂；本站已如實登錄 24 條 |
| `CG8-4` | `ci.yml` 的步驟名仍是 `Verify memory schema assertions (S1-S13)`，而該檔現含 `S1`–`S15`。**刻意不改**（`ci.yml` 的 diff 須為空），與該 job 自身註解的同形取捨一致 | 下一次有正當理由改 `ci.yml` 時順手更正 |
| `D8-1`（承接） | `[D1]`=A 偏離 `K-08`（`delete` 的 403 不再可達） | 下一輪契約修訂追認 |
| `D8-4`（承接） | 分頁參數 `offset`／`limit` 偏離 `K-08` 的 OpenAPI 半邊 | 同上 |
| **`D8-5`**（承接） | `semantic`／`procedure` **無保存期上界** | **無自然承接站**——須於本站核可關卡重新提交使用者 |
| `D8-6`／`D8-7`（承接） | correlation id；`U12`／`U13` 寫入失敗時的行為未定 | `U13`／`U12` 各自的站 |
| **`FD8-1`**（承接） | **兩條新依賴邊 `U12` → `U8`、`U13` → `U8` 須回報 `bolt-plan.md` 並重審 Bolt 順序** | `bolt-plan.md` 本身（`delivery-planning` 已在游標之前） |
| `I8-3`（承接） | `S14` 不證明生產 planner 的選擇傾向（需數百至數千列 fixture） | 後續，待表有真實資料量 |
| `I8-4`（承接） | `git revert` 不會刪掉 HNSW 索引 | 已記載於 `DEPLOY.md §2.2.12`，無害 |
| `OPEN-CG5-1`（承接） | grant 邊界未被 CI 驗證，而本單元是一個**有 DELETE 權的新消費者** | 與 `OPEN-ND9-2` 同一決定 |
| **`tcms-test-cases`** | **blocking，至今未對本 intent 任何單元執行** | construction 階段，部署之前 |

## 八、覆蓋率

| 項目 | 值 |
|---|---|
| `org.md` 宣告 | 80% line coverage |
| repo 的量測機制 | **不存在**（`team.md` 逐字「既無法量測也無法強制，是宣告而非閘門」） |
| **本單元的實際門檻** | **41 個 unittest ＋ psql 的 4 個指定斷言 id（8 個失敗點）全綠 ＋ 6 項突變各自確認紅燈後還原** |

**不宣稱滿足該數字、也不弱化它**；落差如實記載。
（計畫 §七預估「5 ＋ 3 ＋ 12 ＋ 4 ＝ 24 條」，實際交付 **41 ＋ 4 ＝ 45 個斷言**
（psql 側以指定的 4 個 id 計；若按失敗點計為 41 ＋ 8 ＝ 49）——
差額主要來自授權檔由 12 條擴為 23 條：`[D1]`=A 的對外不可區分性、
放寬的方向性、分頁的無重複無遺漏、交易邊界各自需要獨立斷言。）

## 十、刻意不動的五個路徑（由 `source-manifest.json` 移入）

`source-manifest.json` 的 schema 只接受 `stage`／`unit`／`version`／`writes`
四個欄位（引擎逐字拒絕：`source-manifest.json has unknown field(s):
deliberately_unchanged`），故這五筆「刻意不動」的記載移到本檔。

**它們不是遺漏，而是兩項宣稱的可驗證面**——diff 為空（或與基準逐位元相同）
即是證據：

| 路徑 | 為什麼必須不動 | 驗證方式 |
|---|---|---|
| `backend/database.py` | 計畫 Step 1.1／10.1 | `git diff --stat` 為空 |
| `backend/requirements.txt` | `NFR8.20` 的第一項判準。**這同時是 ORM 省略 `embedding` 的理由**——宣告 `vector(1024)` 需要 `pgvector` 套件 | `git diff --stat` 為空 |
| `backend/.env.example` | 零新環境變數（`NFR8.20`） | 僅含 `embedding-port` 的兩個既有變數，無本單元新增 |
| `deploy/` | 零新部署設定、零新監聽埠（`NFR8.20`） | **與開工前基準逐位元相同**（該目錄已帶有先前單元的改動，故「空」只能指「與基準未變」） |
| `.github/workflows/ci.yml` | 不新增 CI job——`S14`／`S15` 進既有 `verify_memory_schema.sql`，而 `memory-schema` job 已在執行它 | 同上 |

**最後兩列的判準形式值得記下**：計畫 Step 10.3 原本寫成
「`git diff --stat -- deploy/ .github/workflows/ci.yml` **為空**」，
而那在一個已帶有先前單元未提交改動的工作樹上**永遠不會成立**——
正確的判準是「**本單元未新增任何東西**」，不是「檔案未被修改」。
這是計畫自身的一處驗證步驟缺陷。
