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

## 重新查驗（code-generation Request Changes 後）

> 查驗時間：`2026-10-22T23:36:08Z` 開始、`2026-10-22T23:42:01Z` 結束（皆取自 `date -u`）。
> 本輪**只做重新查驗，未改任何應用程式碼**；本單元的程式檔在工作樹上無未提交改動
> （`git status --short -- backend/services/memory_*.py backend/tests/test_memory_*.py backend/models.py` 無輸出）。

### 一、觸發原因

使用者對整站送出 Request Changes，原文：

> 「修正 functional-design/merge-blockers.md 列出的 19 項合併前必修，各在所屬單元修正並附測試；需人工裁決的項目（#7、#8 等）逐項問我。object-picker-ui 的 R-08、R-09 已修，重新審查即可。」

### 二、19 項中本單元 0 項

依計畫第十節的逐項對照，`construction/functional-design/merge-blockers.md` 的「單元」欄**沒有一項劃給 `memory-service`**。與本單元介面相關的兩項：

| 項 | 所屬單元 | 與本單元的關係 |
|---|---|---|
| 第 13 項（`intent_routing.py` 以 `except Exception` 吞下記憶讀取的所有錯誤） | `intent-router` | 本單元已以不同例外型別區分「拒絕」與「依賴失敗」（`memory_errors.py` 的 `MemoryForbidden`／`MemoryNotFound` 與其他例外），修法在呼叫端分別處理，不需改本單元 |
| 第 6 項（前端 `deleteMemoryRecord` 把任何 404 當成已刪除） | `memory-page-ui` | 本單元對「不存在」與「非擁有者」**刻意回同一個 404**（`[D1]`=A，`memory_facade.py:393-410`），前端無法以狀態碼分辨；修法在前端的解讀，不改本單元的回應語意 |

### 三、逐步查驗表

| 步驟 | 結果 | 依據（檔:行或命令） |
|---|---|---|
| 1.1 | 成立 | `git diff --stat -- backend/database.py` 無輸出 |
| 1.2 | 成立 | 兩個單元範圍指令實跑（見第四節）；unittest 以 `backend/.venv/bin/python` 代替 `python3`、psql 以臨時叢集 `127.0.0.1:54328` 代替 `localhost:5432`，指令形狀不變 |
| 1.3 | 成立（以現況判） | 這是開工前的時點檢查，git 上無法重現：`verify_memory_schema.sql` 與 HNSW 索引都在 `c2e5687` 一次進入歷史，該提交之前沒有可比較的版本。改以本步的目的（避免重複）查證：`schema_rbac.sql` 內 `USING hnsw` 僅 1 處（`:503-504`） |
| 1.4 | 成立（以現況判） | 同上，無 git 基準。結構可判：檔頭 `:1-2` 仍寫 `S1`–`S12` ＋ `S13`，本單元的 `S14`／`S15` 位於獨立區段 `:299` 起 |
| 2.1 | 成立 | `models.py:871` `MemoryRecord` 八欄、`:926` `MemoryAuditEvent` 七欄 |
| 2.2 | 成立 | `models.py:922`／`:962` `{"schema": "memory"}`；SQLite 以 `:828` 的 `ATTACH DATABASE ':memory:' AS memory` 處理，`helpers.py` 未改 |
| 2.3 | 成立 | `models.py:757-767` 的區塊註解 |
| **2.4** | **不成立，維持未勾** | 字面要求「不加 `CheckConstraint`」，而 `models.py` 有四條具名 CHECK（`ck_memory_records_kind`／`_content_not_blank`／`_episodic_has_expiry`／`ck_memory_audit_events_action`）。此偏離為刻意，理由見本檔 §三之一（DDL 有的約束 ORM 必須有，`C4` 鎖住） |
| 3.1 | 成立 | `memory_ranking.py:80` `key=lambda c: (-c.score, c.identifier)` |
| 3.2 | 成立 | `memory_ranking.py:32-34` import 集合恰為 `__future__`、`typing`；`C1` 綠燈 |
| 4.1 | 成立 | `memory_service.py:81-98` `SEARCH_SQL`，`:338` 以 `text()` 執行 |
| 4.2 | 成立 | `LIMIT` 在 `SEARCH_SQL` 內（`:97`），無應用層事後過濾；`S15` ③ 在真實 PG 上通過 |
| 4.3 | 成立 | `delete_with_audit` 單一 `commit()`（`:495`）、`widen_scope_with_audit` 單一 `commit()`（`:523`） |
| 4.4 | 成立 | `memory_facade.py:281` `port.embed` 先於 `:285` `create_record` |
| 4.5 | 成立 | `memory_service.py:404` `_log_empty_search`，`:449-450` 兩道候選筆數 |
| 4.6 | 成立 | 三個模組的 `HTTPException` 命中皆在 docstring；`memory_service.py` 無模組層可變容器（模組層 `=` 只有常數與 `__all__`） |
| 5.1 | 成立 | 五個方法 ＋ `list_records`；授權只在 facade。**本輪前已有後續變更**：`U15` 加入 `_authorize_approved`（`memory_facade.py:184`），仍在 facade 層，判準不受影響 |
| 5.2 | 成立 | `_authorize_role`（`:158`）一份，`widen_scope`（`:430`）與 `list_audit_events`（`:487`）共用 |
| 5.3 | 成立 | `memory_facade.py:401`／`:410` 皆拋 `MemoryNotFound`，`:404` 以 `REASON_OWNER` 記日誌；`A5`／`A6` 綠燈 |
| 5.4 | 成立 | `widen_scope` `:429-430` 先判身分與角色、`:440` 才取列；`list_audit_events` 同形（`:486-487`） |
| **5.5** | **不成立，維持未勾** | 字面要求「六條路由」，實際五條（`memory_router.py:164`／`:201`／`:246`／`:280`／`:311`）。刻意不為 `search` 開端點，理由見本檔 §三之三 |
| 5.6 | 成立 | `C3` 綠燈（router 無角色名稱字面值） |
| 5.7 | 成立 | `main.py:132` `app.include_router(memory_router, prefix="/api/memory")` |
| 6.1 | 成立 | `test_memory_contract.py` 11 條（`C1`–`C7`），全綠 |
| 6.2 | 成立 | `test_memory_ranking.py` 7 條、5 個 `@given`，全綠 |
| 6.3 | 成立 | `test_memory_authz.py` 23 條，全綠 |
| 6.4 | 成立 | router 無檢索端點，SQLite 測試不經向量路徑；向量路徑由 `S15` 在真實 PG 上通過 |
| 7.1 | 成立 | `schema_rbac.sql:503-504` `CREATE INDEX IF NOT EXISTS ix_memory_records_embedding_hnsw … USING hnsw (embedding vector_cosine_ops)` |
| 7.2 | 成立 | `run_meta_schema_migration.py:168`；實跑終檢通過 |
| 7.3 | 成立 | `verify_memory_schema.sql:320-384`（`S14`，`:367` `SET LOCAL enable_seqscan = off`） |
| 7.4 | 成立 | `verify_memory_schema.sql:388-574`（`S15` ①②③） |
| 7.5 | 成立 | `DEPLOY.md:1176` §2.2.12、`:250` 總表 `I` 列 |
| 8.1 | 成立 | `openapi.json` 含四個 `/api/memory` 路徑；`dump_openapi.py --check` 綠燈 |
| 8.2 | 成立 | `npm run check:types` 綠燈；`frontend/src/types/api.d.ts` 含 7 處 `/api/memory` |
| 8.3 | 成立 | 兩者已隨 `c2e5687` 同一提交進入歷史 |
| 10.1 | 成立 | 同 1.1 |
| 10.2 | 成立 | `git diff --stat -- backend/requirements.txt` 無輸出 |
| **10.3** | **不成立，維持未勾** | `git diff --stat -- deploy/` 無輸出，但 `.github/workflows/ci.yml` 有 `6 insertions(+), 6 deletions(-)`。差異全為本輪其他單元的 `P1-P12` → `P1-P16` 文字更正，**不含本單元的任何內容**。本檔 §十 已記載此判準在已有他人改動的工作樹上不可能字面成立 |
| 10.4 | 成立 | 兩支 validator 皆 `validation passed` |
| 10.5 | 成立 | `Ran 1241 tests … OK` |
| 10.6 | 成立 | `規格檔與後端程式碼一致。` |
| 11.1 | 成立 | `source-manifest.json` 17 個路徑，逐一確認存在 |
| 11.2 | 成立 | `traceability.json` 80 筆（`AC` 12、`BR` 24、`NFR` 35、`EC` 6、`K` 3），涵蓋計畫所稱 27 條 `NFRx.y` 以上 |
| 11.3 | 成立 | 本節 |

**合計：勾回 41 格，維持未勾 3 格（2.4、5.5、10.3），共 44 格（`grep -c '^\s*- \[x\]'` 實算），皆為字面與刻意偏離不符，偏離理由先前已記載。**
Step 9（突變驗證）是表格而非勾選項；本輪未重跑六項突變（只做重新查驗，且本單元程式未變）。

### 四、命令實際輸出

| 命令 | 結果 |
|---|---|
| `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest tests.test_memory_contract tests.test_memory_ranking tests.test_memory_authz -v` | `Ran 41 tests in 1.638s` → `OK` |
| `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests` | `Ran 1241 tests in 101.533s` → `OK`（日誌中的 19 行 `ERROR:` 為記錄器輸出，不是測試失敗；`FAIL: test`／`ERROR: test` 0 筆） |
| `psql … -v ON_ERROR_STOP=1 -f schema_rbac.sql`（兩次） | 兩次 `exit=0`，`ERROR` 0 筆 |
| `psql … -v ON_ERROR_STOP=1 -f backend/scripts/verify_memory_schema.sql` | `exit=0`，5 條 `NOTICE` 全部通過（含 `S14`、`S15`） |
| `DATABASE_URL=… .venv/bin/python scripts/run_meta_schema_migration.py` | `exit=0`，`終檢通過`；索引 **9** 個（本單元收尾時為 8，`U23` 在 `8677b7d` 新增一個） |
| `python3 scripts/dump_openapi.py --check`（`backend/`，venv） | `規格檔與後端程式碼一致。`，`exit=0` |
| `npm run check:types`（`frontend/`） | `API 型別檔與規格檔一致。` |
| `python3 scripts/validate_repo_contract.py` | `Cloud-360 repository contract validation passed.` |
| `python3 scripts/validate_env_contract.py` | `Cloud-360 environment configuration contract validation passed.` |

真實 PostgreSQL 的環境：本機無 Docker daemon、`localhost:5432` 無回應，故在 scratchpad 以 Homebrew `postgresql@17`（**17.7**）＋ `pgvector`（**0.8.1**）臨時 `initdb`，只開 TCP（`127.0.0.1:54328`，Unix socket 路徑超過 103 位元組上限故關閉），跑完已 `pg_ctl stop`（`pg_isready` 回 `no response`）。CI 用 `pgvector/pgvector:pg18`，主版號不同。

### 五、後續單元對本單元路徑的變更

| 提交／工作樹 | 單元 | 變更 | 對本單元判準的影響 |
|---|---|---|---|
| `8cf948c` | `U15` | `memory_facade.py` 加 `_authorize_approved`（六個公開方法第一行）；`memory_router.py` 的 `POST`／`DELETE` 補宣告 403；`memory_errors.py` 加 `reason="pending"` | 無：授權仍只在 facade、router 仍無角色字面值（`C3` 綠）、非擁有者仍為 404。`DELETE` 的 403 只來自帳號未核准，先於取列 |
| `6dff4d4`、`8677b7d` | `U20`、`U23` | `run_meta_schema_migration.py` 新增他們的物件 | 無：本單元的索引列（`:168`）未動 |
| 工作樹（未提交） | 合併前必修第 3 項 | `user_router.py:510-517` 直接以 ORM 查 `MemoryRecord`／`MemoryAuditEvent` 計數，作為使用者硬刪除的 409 前置檢查 | 唯讀計數，不經 facade。facade 為唯一入口本來就**無機械強制**（`memory_facade.py` 的「殘留缺口」段）；此處不讀 `content`、不寫入，不違反本單元任何斷言。如實記錄 |
| 工作樹（未提交） | `embedding-port` | `embedding_port.py` 新增 `FASTEMBED_REGISTRY_NAMES` | 無：`model_id` 不變，`CG8-1`（`fulltext` 之下 `model_id=None`）現況不變 |
| 工作樹（未提交） | 他單元 | `schema_rbac.sql`、`DEPLOY.md`、`openapi.json`、`api.d.ts`、`ci.yml`、`main.py` | 逐一檢查：`schema_rbac.sql` 的改動在 `H)`／`J)` 區塊的 COMMENT；`openapi.json` 的 diff 無 `/api/memory` 路徑；`main.py` 只加 `ensure_project_members_on_startup()`。皆不觸及本單元 |

### 六、`traceability.json` 狀態值

80 筆的 `status` 只有 `OK`（68）、`N/A`（11）、`Deferred`（1），**無非法值，未改動**。每一筆 `OK` 的 `target` 皆指向存在的檔案。

### 七、未驗項

| 項 | 理由 |
|---|---|
| Step 9 的六項突變 | 本輪不重跑（程式未變）；原紀錄見本檔 §四 |
| CI 的 `pg18` 主版號 | 本機只有 PG17；`S1`–`S15` 在 17.7 上通過 |
| `CG8-1`／`CG8-2` 等既有 open items | 本輪不處理，狀態不變（見本檔 §七） |

**本輪查驗未發現本單元的新缺陷。**

## 重做（Code Generation 自頭重來，2026-10-25）

<!-- 寫入時間：2026-10-25T12:58:36Z -->

本輪只查驗、未改任何程式或測試。計畫 44 格勾選 41 格（機械計數：`[x]` 41、`[ ]` 3）。三格未勾的理由記在本節，不寫進計畫檔（計畫檔內的註解會改變已核可內容）：

| 格 | 未勾理由 |
|---|---|
| 2.4 不加 `CheckConstraint` | `backend/models.py:908`／`:912`／`:916`／`:958` 有四條具名 CHECK（`ck_memory_records_kind`、`_content_not_blank`、`_episodic_has_expiry`、`ck_memory_audit_events_action`），字面不成立；偏離為刻意，理由見本檔 §三之一，由 `test_memory_contract` C4 鎖住 |
| 5.5 六條路由 | 實際五條（`memory_router.py:164`／`:201`／`:246`／`:280`／`:311`），`search` 刻意無 HTTP 端點（本檔 §三之三）；分頁與 `limit` 上限成立（A14／A14b 綠） |
| 10.3 `deploy/`、`ci.yml` diff 為空 | 工作樹上 `ci.yml`、`deploy/.env.example`、`deploy/docker-compose.deploy.yml` 有他單元未提交改動；逐一檢視不含本單元內容 |

勾選但帶限制：1.3／1.4（「開工前」狀態無法由 git 重現，以現況判斷）；10.2（`c2e5687` 為多單元合併提交，無法拆出本單元的那一份，但工作樹 diff 為空、檔內無 `pgvector`）；8.3（openapi 已隨 `c2e5687` 進版控，工作樹 diff 無 `/api/memory` 行）。Step 9 突變驗證本輪未重跑。

測試（`backend/.venv`、`-B`、`PYTHONDONTWRITEBYTECODE=1`）：`test_memory_contract` 11、`test_memory_ranking` 7、`test_memory_authz` 23、`test_memory_pending_authz`（U15 新增）9，合計 50 OK；完整套件 1319 OK（skipped=3）。臨時 PostgreSQL 17.7＋pgvector：`schema_rbac.sql` 連跑兩次 exit 0、`verify_memory_schema.sql` 五條 NOTICE 全通過（含 S14／S15）、`run_meta_schema_migration.py` 終檢通過；已停機並刪除資料目錄。CI 的 `pg18` 仍待確認。

計畫外的後續改動：U15 在 facade 加了 `_authorize_approved` 與對應測試；授權仍只在 facade，router 無角色字串（C3 綠）。

合併前必修清單無項目劃給本單元。相關觀察：#13 的 `intent_routing.py:232` 已單獨捕捉 `MemoryForbidden`，本單元例外足以區分；#6 的同一 404 為 `[D1]`=A 刻意設計；`user_router.py:510-517` 直接以 ORM 計數記憶列（唯讀、不讀 `content`），與 #20 同根——「facade 為唯一入口」無機械強制。

低嚴重度觀察（未列為合併前必修）：檢索與列出不過濾 `expires_at`，已過期但未清除的 episodic 記憶仍可見（functional-design 未規定，不違規）；同一筆記憶併發刪除時後者可能 500 而非 404（推論，未實測）。

## 合併前必修第 22 項處置（2026-10-26）

來源：`construction/functional-design/merge-blockers.md` 第 22 項；計畫第十一節 Step 12–15。

**更正上一段的推論**：併發刪除的後者**不是** 500。本輪在真實 PostgreSQL 上實測（修正前的程式）：第二次 `db.delete(record)` 影響 0 列，SQLAlchemy 只發 `SAWarning: DELETE statement on table 'memory_records' expected to delete 1 row(s); 0 were matched`，不報錯，於是**兩次刪除都「成功」且稽核 `deleted_by_user` 寫了兩筆**（`D1` 斷言失敗訊息 `MemoryNotFound not raised`；`D2` 為 `['deleted', 'deleted'] != ['deleted', 'not-found']`），與 review-03 的實測一致。

### 變更位置

| 檔案 | 位置 | 變更 |
|---|---|---|
| `backend/services/memory_service.py` | `:49` | 新增 `from services.memory_errors import MemoryNotFound` |
| `backend/services/memory_service.py` | `:477-527`（`delete_with_audit`） | 改以 `db.query(MemoryRecord).filter(id == …).delete(synchronize_session="evaluate")` 下刪除並讀回影響列數（`:511`）；**不為 1 時 `rollback()` 並拋 `MemoryNotFound`、不寫稽核**（`:516-518`）；稽核改在刪除之後 `add`，仍為同一交易、一次 `commit()`。選影響列數而不選 `SELECT … FOR UPDATE`：後者在 SQLite dialect 被靜默丟棄，前者在兩個方言上語意相同 |
| `backend/services/memory_service.py` | `:390-401`（`scored_candidates` docstring，函式 `:387` 起） | 原文「PBT 第 2 條性質是它唯一的機械防線」已不實（該 PBT 吃手造分數、驗不到取負號），改指向本輪兩道新測試。程式碼 `score=-distance`（`:403`）未改 |
| `backend/services/memory_facade.py` | `:412-420`（`delete`） | `delete_with_audit` 拋 `MemoryNotFound` 時以**呼叫端送來的原值**重拋，使競態下的 404 `detail` 與一般「不存在」逐字相同（`[D1]`=A）；不寫 `reason="owner"` 日誌、不寫稽核 |
| `backend/tests/test_memory_ranking.py` | `:167-240`（生成域 `distances`、輔助 `_pairs`、新類別 `ScoredCandidatesRealDistanceTest` `:190`） | Step 12：`test_closer_candidate_ranks_first`（`:217`，距離 0.6／1.7／0.05 打亂輸入）與 PBT `test_ranking_is_non_decreasing_in_distance`（`:231`，距離域 `[0, 2]`、200 例），皆照 `MemoryFacade.search` 的組合 `rank_candidates(scored_candidates(pairs))`，以**回查原始距離**斷言 |
| `backend/tests_pg/test_memory_service_pg.py` | 新檔 | Step 13 `V1`（`:186`）：經生產用 `create_record` 寫三筆（遠、中、近），斷言每列 `embedding IS NOT NULL`、`search_records` 依 `<=>` 回 `[近, 中, 遠]`，再經 `scored_candidates → rank_candidates` 仍為近者在前。Step 14 `D1`（`:230`）：兩 session 先取列再依序刪；`D2`（`:259`）：以 `before_cursor_execute` ＋ barrier 讓兩條連線同時送出 `DELETE`。兩者皆斷言恰一次成功、另一次 `MemoryNotFound`、`deleted_by_user` 稽核恰一筆。每個測試用專屬 `embedding_model` 與 `__u8_service_pg__` 前綴，依 id／前綴清理（無 TRUNCATE） |
| `source-manifest.json` | `writes` | 新增 `backend/tests_pg/test_memory_service_pg.py` |

`traceability.json` 未改：逐列查過，無註記因本輪變為不實（`BR4.2` 的「單一 commit」、`BR4.3` 的「不存在 → `MemoryNotFound` 且不產生稽核」仍成立）。無 DDL 變更，`schema_rbac.sql`／`DEPLOY.md` 不觸發同步。

### CI（Step 15.1）

`ci.yml` **未改**。CI 的 `concurrency` job（`Concurrency (real PostgreSQL row locks)`）使用 `pgvector/pgvector:pg18` service、先 `psql -f schema_rbac.sql`（含 `vector` extension 與 `memory` schema），再在 `backend/` 跑 `python -m unittest discover -s tests_pg -v`；新檔名符合預設 `test*.py`，會被撿到。merge-blockers 第 22 項 (e) 寫的是「memory-schema job」，但該 job 只跑 `psql`、沒有 Python，`tests_pg` 實際由 `concurrency` job 執行（計畫 Step 15.1 已以 `tests_pg` job 表述）。該 job 的步驟名稱仍寫「(C1-C3)」，與實際測試數不符（本輪之前即已過時），未改以免動到 `ci.yml` 的既有未提交變更。

### 測試數（本機）

| 套件 | 修改前 | 修改後 |
|---|---|---|
| `backend/.venv` 執行 `discover -s tests`（SQLite） | 1319，`OK (skipped=3)` | **1321**，`OK (skipped=3)` |
| `discover -s tests_pg`（一次性 PostgreSQL 17.7 ＋ pgvector 0.8.1，綁 `127.0.0.1:55422`，套用 `schema_rbac.sql`；用完即停機刪除） | 10，`OK` | **13**，`OK` |
| 本單元三檔 `test_memory_contract`／`test_memory_ranking`／`test_memory_authz` | 41 | 43，`OK`（含 `A15` 交易邊界與刪除 204 路徑，SQLite 路徑維持可用） |

`validate_repo_contract.py` 與 `validate_env_contract.py` 皆通過。測試快取寫到暫存區（`HYPOTHESIS_STORAGE_DIRECTORY`、`PYTHONDONTWRITEBYTECODE=1`、`-B`），repo 內無新增 `.hypothesis`／`.pyc`。

### 三項突變（只在暫存區的 `backend/` 副本執行，repo 檔未動）

| # | 突變 | 結果 | 還原後 |
|---|---|---|---|
| 12 | `scored_candidates` 的 `score=-distance` → `score=distance` | **紅**：`test_closer_candidate_ranks_first`、`test_ranking_is_non_decreasing_in_distance` 2 個 FAIL；本單元其餘 41 個測試**仍綠**（證實原缺口） | 9／9 綠 |
| 13 | `create_record` 的 `if embedding is not None and _supports_vector(db):` → `if False and …`（跳過 `UPDATE … SET embedding`） | **紅**：`V1` FAIL，訊息「embedding 是 NULL——create_record 的 UPDATE ... SET embedding 沒有生效」；本單元 SQLite 43 個測試**仍綠**（證實原缺口） | 3／3 綠 |
| 14 | 移除 `delete_with_audit` 的 `if deleted != 1: rollback(); raise MemoryNotFound` | **紅**：`D1`（`MemoryNotFound not raised`）、`D2`（`['deleted', 'deleted'] != ['deleted', 'not-found']`）2 個 FAIL | 3／3 綠 |

<!-- 寫入時間：2026-10-26T13:47:47Z -->
