# 單元測試指示 — `U8 memory-service`

> 本單元的測試分佈於**三個載體**，而分界線不是品味問題——
> 它由「SQLite 能不能跑那段 SQL」決定。

## 一、框架與既有基礎設施（零新依賴）

| 載體 | 框架 | 執行者 | 本單元是否新建 |
|---|---|---|---|
| 靜態契約斷言 | Python 內建 `unittest`（**不是 pytest**） | 既有 `backend` job | **沿用**，新增一個測試檔 |
| PBT | `unittest` ＋ `hypothesis`（已在 `requirements.txt`） | 既有 `backend` job | **沿用**（repo 已有 13 個 `@given` 先例） |
| HTTP ＋ ORM（SQLite） | `starlette.testclient.TestClient` ＋ `backend/tests/helpers.py` | 既有 `backend` job | **沿用** |
| 真實 PostgreSQL 斷言 | `psql` ＋ `DO $$ ... RAISE EXCEPTION ... $$` | 既有 `memory-schema` job | **沿用 job**，新增兩條斷言進既有 `.sql` 檔 |

**`backend/requirements.txt` 的 diff 必須為空**（`NFR8.20` 的第一項判準）。
這也是 ORM 模型省略 `embedding` 的理由——宣告 `vector(1024)` 需要
`pgvector` 套件（見計畫 §1.2）。

## 二、執行本單元的測試（兩個指令，皆限定於本單元）

### 2.1 不需資料庫 ＋ SQLite 的三個測試檔

```bash
cd backend && python3 -m unittest tests.test_memory_contract tests.test_memory_ranking tests.test_memory_authz -v
```

### 2.2 真實 PostgreSQL 的斷言（**須於 repo 根目錄執行**）

```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d cloud360 \
  -v ON_ERROR_STOP=1 -f backend/scripts/verify_memory_schema.sql
```

**前置條件**：`schema_rbac.sql` 已套用（含本單元新增的 HNSW 索引）。
`memory-schema` job 無 `working-directory` 覆寫，故預設即為根目錄。

### 2.3 **不得**使用專案全域指令

`python3 -m unittest discover -s tests` 這類形式不得寫進本檔——
Build and Test 會逐單元執行每個單元的指令，不限定的指令會讓整套測試跑 24 次。

## 三、三個載體的分界線（這是本檔最重要的一節）

**分界由「SQLite 能不能跑那段 SQL」決定，不是由測試型態決定。**

| 受測對象 | 載體 | 為什麼 |
|---|---|---|
| 四層的禁令、ORM↔SQL 一致性、日誌呼叫形狀 | **靜態**（零 DB） | 讀版控檔案的文字即可判定 |
| 次級排序鍵 | **PBT**（零 DB） | 純函式 |
| 授權（兩套模型）、`[D1]`=A 三案例、酬載忽略、`limit` 上限、分頁 | **TestClient ＋ SQLite** | 這些路徑**不碰向量**；ORM 模型存在使 SQLite 有表可用（計畫 §1.1） |
| **向量檢索的組合正確性** | **`psql`（真實 PG）** | SQLite **無向量型別、無距離運算子**——該查詢**編不出來**（計畫 §1.3） |
| HNSW 索引與其 opclass | **`psql`（真實 PG）** | 索引型態與 `EXPLAIN` 計畫只在 PostgreSQL 有意義 |

### 3.1 這個分界線曾經是錯的，修正過程值得記下

`infrastructure-design/cicd-pipeline.md §三` 初稿寫「授權判定、過濾、交易邊界
在 SQLite 上的語意與 PostgreSQL 一致」——**但當時沒有查記憶表有沒有 ORM 模型**。
實測：`backend/models.py` 內零 Memory 模型，而 `helpers.py:50` 的
`create_all()` **只建有 ORM 模型的表**。沒有模型 ⇒ SQLite 裡沒有那兩張表
⇒ 連授權測試都跑不起來。

**修正不是改測試策略，是補上 ORM 模型**（計畫 Step 2），
使那句話從「有條件成立」變成「成立」。而補模型的同一個 PR 必須附
一致性測試——`team.md` 的「單一真實來源」逐字要求
「無法寫測試的副本不新增」。

## 四、測試清單

### 4.1 `backend/tests/test_memory_contract.py`（5 條，零 DB、零網路）

| # | 測試 | 斷言 | 突變 |
|---|---|---|---|
| 1 | `test_ranking_module_is_pure` | `memory_ranking.py` 不含 DB session 型別、不含 `HTTPException` | — |
| 2 | `test_facade_does_not_raise_http_exceptions` | `memory_facade.py` 不含 `HTTPException` | — |
| 3 | `test_router_contains_no_authorization` | `memory_router.py` 不含任何角色名稱字串 | — |
| 4 | `test_orm_mirrors_sql_columns` | `MemoryRecord` 欄位集合 ∪ `{embedding}` ＝ `schema_rbac.sql` 的 `memory_records` 欄位集合；`MemoryAuditEvent` 欄位集合 ＝ SQL 的七欄 | 突變 6 |
| 5 | `test_logging_never_passes_whole_model` | 日誌呼叫的引數不含裸的模型變數名 | — |

**第 4 條的取值方式**：以 regex 從 `schema_rbac.sql` 的 `I)` 區塊解析欄位名，
**不得**在測試檔內重新手寫欄位清單——那會讓被檢查的東西與檢查的依據
變成同一個人的記憶（`project.md` 已記過此形）。

**第 5 條的形狀**：掃 `logger.*(...)` 呼叫的引數，斷言不出現
`{memory}`／`{record}` 這類整個物件的插值。它是**靜態**的，
因為執行期字串比對（4.3 的第 12 條）只在被觸發的路徑上有效。

### 4.2 `backend/tests/test_memory_ranking.py`（PBT，`NFR3.24`）

| property | 內容 |
|---|---|
| 1 | **任意排列不變性**：同一輸入集合的任意排列，排序結果完全相同 |
| 2 | 分數遞減為主鍵：結果的分數序列非遞增 |
| 3 | 同分時以識別字遞增：分數相同的相鄰兩筆，識別字遞增 |

`hypothesis` 的 strategy：`st.lists(st.tuples(st.text(), st.floats(allow_nan=False)))`。
**`allow_nan=False` 是刻意的**——NaN 的比較語意會讓「任意排列不變性」
無意義地失敗，而向量相似度不會產生 NaN。

### 4.3 `backend/tests/test_memory_authz.py`（約 12 條，TestClient ＋ SQLite）

| # | 測試 | 期望 |
|---|---|---|
| 1 | 擁有者讀得到自己的記憶 | 200，列表含該筆 |
| 2 | 他人的 `owner` 範圍記憶不出現在我的列表 | 200，列表不含 |
| 3 | `platform` 範圍的記憶出現在他人列表 | 200，列表含 |
| 4 | **擁有者刪除自己的記憶** | **204** |
| 5 | **他人刪除該記憶** | **404**（非 403）＋ 日誌含 `reason="owner"` |
| 6 | **刪除不存在的 id** | **404** ＋ 日誌**不含** `reason="owner"` |
| 7 | `Platform_Admin` 刪除他人記憶 | **404**——角色不授予跨使用者刪除權 |
| 8 | `Platform_Admin` 放寬他人記憶的可見範圍 | 200 ＋ 稽核含前後值 |
| 9 | 非管理員放寬 | **403** |
| 10 | 非管理員放寬**不存在**的 id | **403**（非 404）——先判角色（`NFR7.22`） |
| 11 | 寫入時酬載帶 `ownerUserId`／`visibilityScope` | **成功（非 422）**，但兩欄為已驗證身分與 `owner` |
| 12 | 404 回應體不含 fixture 的 `content` | 字串比對不命中 |

**第 5、6 條合起來是 `[D1]`=A 的證據**，且**缺一不可**：
兩者的對外狀態碼刻意相同，差異只在日誌。
只測第 5 條的話，一個把兩者都收斂到 404 且**連日誌也收斂**的實作會通過
——而那會讓枚舉行為完全不可見（`nfr-design/observability-design.md §四`）。

**第 7 條是兩套授權模型不可互換的證據**：`Platform_Admin` 有放寬權（第 8 條）
但**沒有**刪除權。只測第 8 條的話，一個用角色模型判刪除的實作也會通過。

**第 10 條與第 6 條形狀相反，這是刻意的**：放寬路徑先判角色（故無權者永遠 403），
刪除路徑必須先取列才知道擁有者（故改用回應收斂）。
兩種手法不同、目的相同（見 `nfr-design/security-design.md §三`）。

### 4.4 `backend/scripts/verify_memory_schema.sql` 新增 `S14`／`S15`（4 條斷言）

| id | 斷言 |
|---|---|
| `S14` | `SET enable_seqscan = off` → `EXPLAIN` → 計畫使用該 HNSW 索引 |
| `S15` ① | 結果不含他人擁有且 `visibilityScope = owner` 的列 |
| `S15` ② | 結果不含不同 `embeddingModel` 的列 |
| `S15` ③ | **過濾後候選數 < `LIMIT` 時，回傳筆數等於過濾後的數量** |

**`S15` ③ 是唯一能區分「同查詢」與「先查再事後過濾」的斷言**：
一個先取 `LIMIT n` 再於應用層過濾的錯誤實作**也會通過 ①②**
（它確實濾掉了不該有的列，只是濾在錯的地方），只有 ③ 會紅。

**fixture 要求**：跨**兩個擁有者**與**兩個 `embeddingModel`**，
且總列數**大於** `LIMIT`——否則 ③ 無法構造。

## 五、覆蓋率目標

| 項目 | 值 |
|---|---|
| `org.md` 宣告 | 80% line coverage |
| repo 的量測機制 | **不存在**（`team.md` 逐字「是宣告而非閘門」） |
| **本單元的實際門檻** | 上述 **5 ＋ 3 ＋ 12 ＋ 4 ＝ 24 條**斷言全綠 ＋ 計畫 Step 9 的六項突變各自確認紅燈後還原 |

**不弱化 `org.md` 的宣稱**，也不假裝滿足它。

## 六、Mocking／stubbing 指引

| 情境 | 做法 |
|---|---|
| 靜態契約測試（4.1） | **不 mock 任何東西**——它讀版控檔案的真實內容 |
| PBT（4.2） | 不需要 mock（純函式） |
| TestClient（4.3） | 沿用 `helpers.py` 既有形狀：`psycopg2` 的 `MagicMock` ＋ in-memory SQLite ＋ `app.dependency_overrides` 覆寫 `get_db`／`get_current_user`。**不自創第二套** |
| `U6 EmbeddingPort` | 在 4.3 中以 `stub` 提供者設定；**不 mock `U6` 的內部**——它有自己的契約（`K-06`） |
| `psql` 斷言（4.4） | **不 mock 資料庫**。整組斷言存在的理由就是 SQLite 與 PostgreSQL 的語意差異 |

## 七、測試資料管理

| 規則 | 理由 |
|---|---|
| fixture 的 `content` 帶固定前綴（如 `__u8_fixture__`） | 清理依前綴，不碰其他資料 |
| `psql` 斷言的 fixture 自建自清 | `memory-schema` job 內多個斷言共用一座資料庫 |
| **不得**以 `TRUNCATE` 或無 WHERE 的 `DELETE` 清理 | 一個會清空整張表的清理動作，在本單元的語境下與被測缺陷長得一樣 |
| 時間戳一律相對 `now()` | 寫死日期會在某個未來日期無聲改變語意 |
| 兩個擁有者的 fixture 使用者以固定 username ＋ `ON CONFLICT DO NOTHING` 建立 | 可重跑；且 `S15` ① 需要**兩個不同**擁有者才構造得出來 |

## 八、不在本單元測試範圍

| 項目 | 為什麼 |
|---|---|
| `NFR3.20`／`NFR3.21` 的延遲實測 | 需要有真實資料量的環境 ＋ 記錄列數；CI 無此環境。屬 `tcms-test-cases` 的「只能手動」桶 |
| planner 是否真的選用 HNSW 索引 | 需數百至數千列 fixture，而本表目前是空的（`I8-3`） |
| `U12`／`U13` 的同進程寫入 | 屬那兩個單元；且它們寫入失敗時的行為未定（`D8-7`） |
| 前端記憶頁 | 屬 `U15 memory-page-ui` |
| grant 邊界 | 需第二個資料庫角色（`OPEN-CG5-1`，本單元不改善） |
