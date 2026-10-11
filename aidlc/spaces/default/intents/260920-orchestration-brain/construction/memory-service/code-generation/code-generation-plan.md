# Code Generation 計畫 — `U8 memory-service`

> 本單元是 `service`、size **L**，擁有 `US4.1`／`US4.2`／`US4.3`／`US4.4` 共 12 條 AC、
> 22 條 `BR` 規則、27 條 `NFRx.y`，以及契約 `K-08`（本 repo 的**第二套授權模型**）。
>
> **四個前置站全部跑過**（functional-design、nfr-requirements、nfr-design、
> infrastructure-design），各留下 NOT-READY 的 advisory 審查與其已處置的發現。
> 本計畫是它們的匯流點。

## 〇、上游依據（逐一指名）

| 上游 | 本計畫用到它的什麼 |
|---|---|
| `functional-design/entities.md` | 兩個邏輯實體、`EC1`–`EC6` 六條實體約束、三種 kind 的寫入端 |
| `functional-design/rules.md` | 22 條 `BR1.1`–`BR7.4`；§二之一 的兩套授權模型對照 |
| `functional-design/functional-spec.md` | §1.1–§1.6 六個工作流程、§2.1 狀態機、§〇 的五個介面 |
| `nfr-requirements/security-requirements.md` | `NFR7.20`–`NFR7.26`、`NFR6.20`／`NFR6.21` |
| `nfr-requirements/performance-requirements.md` | `NFR3.20`–`NFR3.24`（`[N1]`=A 修訂後） |
| `nfr-requirements/scalability-requirements.md` | `NFR7.27`–`NFR7.29`（分頁、`limit` 上限） |
| `nfr-requirements/reliability-requirements.md` | `NFR4.20`–`NFR4.23` |
| `nfr-requirements/observability-requirements.md` | `NFR7.30`–`NFR7.34` |
| `nfr-requirements/tech-stack-decisions.md` | §三 的四層形狀與各層禁令；`NFR8.20` 的四項判準 |
| `nfr-design/security-design.md` | §一 的 facade 為唯一入口；**§二 的 `[D1]`=A 回應收斂**；§四之二 的日誌白名單 |
| `nfr-design/performance-design.md` | §一 的單一 SQL；§二之一 的 `enable_seqscan` 斷言 |
| `nfr-design/logical-components.md` | §一 的四層與各層禁令；§二 的失敗域 |
| `infrastructure-design/infrastructure-specification.md` | §二 的 HNSW 索引四項 blocking 連帶義務 |
| `infrastructure-design/cicd-pipeline.md` | §一 的五道閘門；§二／§三之二 的 `S14`／`S15` |
| `inception/contract-design/contract-summary.md` | `K-08` 的五個 facade 方法與 OpenAPI 半邊 |
| `schema_rbac.sql`、`backend/models.py`、`backend/tests/helpers.py`（版控） | 本計畫 §一 的四項實測 |

## 一、本計畫寫作期間實測查出的四項事實（其中兩項改變設計）

### 1.1 **記憶表沒有 ORM 模型，而這讓 `infrastructure-design` 的一句話只是有條件地成立**（改變設計）

| 查證項 | 結果 |
|---|---|
| `backend/models.py` 內的 Memory 模型 | **零**（`grep "class Memory"` 無命中；唯一命中是 `:610` 一句提到 `memory_audit_events.memory_id` 的註解） |
| `U18`／`U19` 的先例 | **有**：`models.py:544` `class ProjectMember`、`:593` `class ReselectionEvent` |
| SQLite 測試環境怎麼建表 | `backend/tests/helpers.py:50` 的 `Base.metadata.create_all(bind=engine)`——**只建有 ORM 模型的表** |

**後果**：在沒有 ORM 模型的情況下，**SQLite 測試環境裡根本沒有 `memory` 的兩張表**，
故任何碰 DB 的記憶測試都跑不起來。而我在
`infrastructure-design/cicd-pipeline.md §三` 寫「授權判定、過濾、交易邊界在
SQLite 上的語意與 PostgreSQL 一致」——**那句話只有在 ORM 模型存在時才成立**，
而我當時沒有查它存不存在。

**處置（依 `team.md` 的規則，不另出題目）**：
`team.md ## Code Style` 的「單一真實來源」逐字要求
「若確實無法避免（如跨語言邊界），**新增副本的同一個 PR 必須一併新增鎖住兩者
一致的測試**；無法寫測試的副本不新增」。本案三項條件皆滿足——
先例存在（`U18`／`U19`）、一致性機制存在（`run_meta_schema_migration.py` 的
`EXPECTED_TABLES` 已逐表驗欄位數、`verify_memory_schema.sql` 逐條驗約束）、
且**可以寫出鎖住一致性的測試**。

故：**新增兩個 ORM 模型 ＋ 一條鎖住 ORM 與 SQL 一致的測試**（Step 2、Step 6）。

### 1.2 **`embedding` 欄位不能進 ORM 模型**，而這是 `NFR8.20` 逼出來的（改變設計）

`memory_records.embedding` 的型別是 pgvector 的 `vector(1024)`。
在 SQLAlchemy 宣告它需要 `pgvector` Python 套件，而
**`NFR8.20` 的第一項判準逐字是「`backend/requirements.txt` 的 diff 為空」**。

| 選項 | 代價 |
|---|---|
| 加 `pgvector` 套件 | **直接違反 `NFR8.20`**，且審查已實測確認 `requirements.txt` 目前無此套件 |
| **ORM 模型刻意省略 `embedding`（採用）** | ORM 成為**八欄的部分鏡像**。可接受，因為**向量路徑本來就走原生 SQL**（見 §1.3），ORM 只服務非向量路徑 |

**一致性測試因此要斷言的是「ORM 欄位集合 ∪ {embedding} ＝ SQL 欄位集合」**
——而不是「兩者相等」。省略是刻意的、可機械判定的，不是漂移。

### 1.3 向量檢索**必須**走原生 SQL（確認既有設計，非新決定）

同一個理由：pgvector 的距離運算子在沒有 `pgvector` 套件的情況下無法以
SQLAlchemy 表達式寫出。故 `nfr-design/performance-design.md §一` 的
「單一 SQL」在實作上是 `text()` ＋ 綁定參數。

**這也是 `S15` 存在的理由**（`infrastructure-design/cicd-pipeline.md §三之二`）：
該查詢在 SQLite 上編不出來，故它的正確性只能在真實 PostgreSQL 上驗。

### 1.4 router 註冊形狀與 prefix 慣例（照既有，不自創）

`backend/main.py:62-81` 的既有形狀：`app.include_router(x_router, prefix="/api/...")`。
`K-08` 的 OpenAPI 半邊用 `/api/memory/records`，故 prefix 為 `/api/memory`。

## 二、交付物清單（19 個檔：9 新、10 改）

### 2.1 新增的應用程式模組（六個，四層形狀）

| # | 路徑 | 層 | 禁令（違反即破壞結構前提） |
|---|---|---|---|
| 1 | `backend/services/memory_types.py` | 型別 | — |
| 2 | `backend/services/memory_errors.py` | 例外 | — |
| 3 | `backend/services/memory_ranking.py` | **純函式** | **不得** import DB session 型別、**不得** import `HTTPException`、不得讀 DB |
| 4 | `backend/services/memory_service.py` | service | **不得**拋 `HTTPException` |
| 5 | `backend/services/memory_facade.py` | facade（`K-08` 的 `sole_entry`） | **不得**碰 DB、**不得**拋 `HTTPException` |
| 6 | `backend/services/memory_router.py` | HTTP | **不得**做任何授權判定 |

### 2.2 新增的測試（三個）

| # | 路徑 | 內容 |
|---|---|---|
| 7 | `backend/tests/test_memory_authz.py` | 兩套授權模型 ＋ `[D1]`=A 的三案例（TestClient ＋ SQLite，依賴 §1.1 的 ORM 模型） |
| 8 | `backend/tests/test_memory_ranking.py` | 純函式的 PBT（`hypothesis`，`NFR3.24`） |
| 9 | `backend/tests/test_memory_contract.py` | 靜態契約斷言（日誌白名單、四層禁令、ORM↔SQL 一致性） |

### 2.3 修改的既有檔（十個）

| # | 路徑 | 變更 |
|---|---|---|
| 10 | `backend/models.py` | 新增兩個 ORM 模型（`embedding` 刻意省略，見 §1.2） |
| 11 | `backend/main.py` | 註冊 `memory_router`，prefix `/api/memory` |
| 12 | `schema_rbac.sql` | `I)` 區塊新增 HNSW 索引（`IF NOT EXISTS`） |
| 13 | `backend/scripts/run_meta_schema_migration.py` | `EXPECTED_INDEXES` 新增該索引 |
| 14 | `backend/scripts/verify_memory_schema.sql` | 新增 `S14`（索引 ＋ opclass）與 `S15`（檢索查詢組合正確性） |
| 15 | `DEPLOY.md` | 索引的 blocking 同步 |
| 16 | `openapi.json` | 重 dump（三處契約變更） |
| 17 | `frontend/src/types/api.d.ts` | 重跑 `gen:types` |
| 18 | `backend/.env.example` | **不動**（零新變數，`NFR8.20`） |
| 19 | `.github/workflows/ci.yml` | **不動**——`S14`／`S15` 進既有 `verify_memory_schema.sql`，而 `memory-schema` job 已執行它 |

**第 18、19 列刻意列為「不動」**：它們是 `NFR8.20` 與「不新增 CI job」兩項
宣稱的可驗證面——diff 為空即是證據。

## 三、實作步驟

### Step 1 — 前置查證與測試執行器就緒

- [x] 1.1 `git diff --stat -- backend/database.py` 必須為空（記錄基準）
- [x] 1.2 記錄並驗證三個單元範圍指令：
  - `cd backend && python3 -m unittest tests.test_memory_authz tests.test_memory_ranking tests.test_memory_contract -v`
  - `psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/scripts/verify_memory_schema.sql`（於 repo 根目錄）
- [x] 1.3 確認 `schema_rbac.sql` 的 `I)` 區塊目前無向量索引（避免重複）
- [x] 1.4 確認 `verify_memory_schema.sql` 現有斷言到 `S13`

### Step 2 — 資料模型層：ORM 鏡像（implement）

- [x] 2.1 `backend/models.py` 新增 `MemoryRecord`（**八欄**，省略 `embedding`）與 `MemoryAuditEvent`（七欄）
- [x] 2.2 兩個模型的 `__table_args__` 必須指定 `{"schema": "memory"}`；**但 SQLite 無 schema 概念**——確認 `create_all` 在 SQLite 下的行為（若 schema 前綴導致失敗，以 `helpers.py` 既有的處置形狀解決，**不得**改既有 helper 的語意）
- [x] 2.3 `embedding` 的省略必須有逐字註解，寫明理由（`NFR8.20` 的 `requirements.txt` diff 為空）與一致性測試的斷言形式
- [x] 2.4 **不加 `CheckConstraint`**：封閉集合在應用層承載（沿用 `U18` 先例，`functional-design/entities.md §三` 已定）

### Step 3 — 純函式層（implement）

- [x] 3.1 `memory_ranking.py`：同分時的決定性次級排序鍵。形狀抄 `backend/cost/estimate_readers.py:247-251` 的 `key=lambda item: (-item[1], item[0])`
- [x] 3.2 該模組內**不得** import DB session 型別、`HTTPException`、或任何 I/O

### Step 4 — service 層（implement）

- [x] 4.1 `memory_service.py`：以 `text()` 組**單一 SQL**——`WHERE`（可見範圍 ＋ `embeddingModel`）＋ `ORDER BY` 距離 ＋ `LIMIT`
- [x] 4.2 **`LIMIT` 必須作用在已過濾的集合上**（`nfr-design/performance-design.md §一`）：不得先查再於應用層過濾
- [x] 4.3 交易邊界：`delete`＋稽核、`widen_scope`＋稽核各為**單一交易**；不得以兩次 `commit()` 實作
- [x] 4.4 取向量在建立列**之前**（`functional-spec.md §1.1` 步 5–6 先於步 7）
- [x] 4.5 空結果時記錄兩道過濾後的候選筆數（`NFR7.34`）
- [x] 4.6 **不得**拋 `HTTPException`；不得有模組層可變容器（`NFR4.20`）

### Step 5 — facade 與 HTTP 層（implement）

- [x] 5.1 `memory_facade.py`：五個方法（`write`／`search`／`delete`／`widen_scope`／`list_audit_events`）＋ 列出。**授權判定只在這一層**
- [x] 5.2 角色判定**只實作一份**，由 `BR5.1` 與 `BR6.1` 共用
- [x] 5.3 **`[D1]`=A 的回應收斂**：`delete` 的「不存在」與「非擁有者」**皆拋 `MemoryNotFound`**；但拋出前以 `reason="owner"` 寫日誌
- [x] 5.4 `widen_scope`／`list_audit_events` **先判角色、後取記憶**（`NFR7.22`）
- [x] 5.5 `memory_router.py`：六條路由（含新增的 `POST`）＋ offset／limit 分頁 ＋ 伺服器端 `limit` 上限
- [x] 5.6 router **不做授權判定**，只做 HTTP ↔ 例外轉譯
- [x] 5.7 `main.py` 註冊，prefix `/api/memory`

### Step 6 — 測試（test-after）

- [x] 6.1 `test_memory_contract.py`（靜態，**零 DB**）：
  - ① `memory_ranking.py` 不含 DB session 型別、`HTTPException`
  - ② `memory_facade.py` 不含 `HTTPException`
  - ③ `memory_router.py` 不含角色名稱字串（授權不在這層）
  - ④ **ORM ↔ SQL 一致性**：`MemoryRecord` 的欄位集合 ∪ `{embedding}` ＝ `schema_rbac.sql` 的 `memory_records` 欄位集合（§1.2）
  - ⑤ 日誌呼叫不得傳整個模型物件
- [x] 6.2 `test_memory_ranking.py`：PBT——「同一輸入集合的任意排列，排序結果相同」
- [x] 6.3 `test_memory_authz.py`（TestClient ＋ SQLite）：
  - 擁有者模型：讀取過濾、刪除 allow/deny
  - 角色模型：`widen_scope`／`list_audit_events` 的 allow/deny
  - **`[D1]`=A 三案例**：擁有者 → 204；他人 → **404 ＋ 日誌含 `reason="owner"`**；不存在 → **404 ＋ 日誌不含**
  - 酬載忽略：`ownerUserId`／`visibilityScope` 帶了也不生效，**且回成功而非 422**
  - `limit` 上限：超大 `limit` 回傳筆數不超過上限
- [x] 6.4 **`search` 的向量路徑不在 SQLite 測試內**（§1.3）——它由 `S15` 覆蓋

### Step 7 — schema 與驗證腳本（implement）

- [x] 7.1 `schema_rbac.sql` 的 `I)` 區塊新增 HNSW 索引，`IF NOT EXISTS`，opclass 與 §4.1 的距離運算子一致
- [x] 7.2 `run_meta_schema_migration.py` 的 `EXPECTED_INDEXES` 新增該索引
- [x] 7.3 `verify_memory_schema.sql` 新增 **`S14`**：`SET enable_seqscan = off` → `EXPLAIN` → 斷言使用該索引
- [x] 7.4 新增 **`S15`**（承 `infrastructure-design` 審查 `R-01`）：fixture 跨兩個擁有者 ＋ 兩個 `embeddingModel`、列數 > `LIMIT`；三條斷言
  - ① 結果不含他人擁有且 `visibilityScope = owner` 的列
  - ② 結果不含不同 `embeddingModel` 的列
  - ③ **過濾後候選數 < `LIMIT` 時，回傳筆數等於過濾後的數量**（唯一能區分「同查詢」與「先查再事後過濾」的斷言）
- [x] 7.5 `DEPLOY.md` 的 blocking 同步

### Step 8 — 契約產物

- [x] 8.1 重 dump `openapi.json`（`cd backend && python3 scripts/dump_openapi.py`）
- [x] 8.2 重跑前端型別產生（`gen:types`）並 commit
- [x] 8.3 **兩者必須同一個 PR**（`infrastructure-design/cicd-pipeline.md §1.1`）：只做前者會讓 `backend` job 綠而前端型別與契約不一致

### Step 9 — 突變驗證（六項，逐項紅燈後還原複驗）

| # | 突變 | 期望紅燈 |
|---|---|---|
| 1 | `delete` 的非擁有者改回拋 `MemoryForbidden`（→ 403） | `test_memory_authz` 的 `[D1]` 三案例 |
| 2 | 移除 `delete` 失敗路徑的 `reason="owner"` 日誌 | 同上（「日誌可區分」那一條） |
| 3 | `search` 改為先查 `LIMIT n` 再於應用層過濾 | **`S15` 的第 ③ 條**（①② 仍會綠——這正是 ③ 存在的理由） |
| 4 | HNSW 索引的 opclass 改為不相符的 | `S14` |
| 5 | `memory_ranking` 移除次級排序鍵 | `test_memory_ranking` 的 PBT |
| 6 | ORM 模型多宣告一個不存在於 SQL 的欄位 | `test_memory_contract` 的第 ④ 條 |

### Step 10 — 收尾核對

- [x] 10.1 `git diff --stat -- backend/database.py` 仍為空
- [x] 10.2 `git diff --stat -- backend/requirements.txt` **為空**（`NFR8.20`）
- [x] 10.3 `git diff --stat -- deploy/ .github/workflows/ci.yml` **為空**
- [x] 10.4 `python3 scripts/validate_repo_contract.py` ＋ `validate_env_contract.py` 綠燈
- [x] 10.5 `cd backend && python3 -m unittest discover -s tests` 全綠
- [x] 10.6 `python3 scripts/dump_openapi.py --check` 綠燈

### Step 11 — 文件與追溯

- [x] 11.1 `source-manifest.json`：列出 §2 的全部變更路徑
- [x] 11.2 `traceability.json`：27 條 `NFRx.y` ＋ 12 條 AC 對應到實際檔案
- [x] 11.3 `code-summary.md`：檔案清單、§1.1–§1.4 的處置、六項突變的實際輸出、與上游不一致之處

## 四、追溯：計畫步驟 ↔ 需求

| 需求群 | 承載步驟 |
|---|---|
| `BR1`（擁有者寫入端） | Step 5.1；驗於 6.3 的酬載忽略 |
| `BR2`（可見範圍） | Step 4.1／4.2；驗於 6.3 ＋ `S15` ① |
| `BR3`（檢索） | Step 4.1／4.4；驗於 `S15` ①② ＋ `S14` |
| `BR4`（刪除與稽核） | Step 4.3／5.3；驗於 6.3 的三案例 |
| `BR5`（放寬） | Step 5.2／5.4；驗於 6.3 的角色 allow/deny |
| `BR6`（稽核查詢） | Step 5.2／5.4；同上 |
| `BR7`（寫入端） | Step 5.5 的 `POST`；`U12`／`U13` 的同進程呼叫屬那兩個單元 |
| `NFR3.20`–`NFR3.24` | Step 4.1／4.2／7.1／7.3；`NFR3.20`／`NFR3.21` 的實測屬 `build-and-test` |
| `NFR4.20`–`NFR4.23` | Step 4.3／4.6；驗於 6.1 ＋ 6.3 |
| `NFR6.20`／`NFR6.21` | Step 4.6（不新增 engine）／6.1 的第 ⑤ 條 |
| `NFR7.20`–`NFR7.34` | Step 5.1–5.6／4.5；驗於 6.1／6.3 |
| `NFR8.20` | Step 10.2／10.3 的 diff 為空 |

## 五、不在本單元範圍（逐項附承接）

| id | 內容 | 承接 |
|---|---|---|
| `D8-1` | `[D1]`=A 偏離 `K-08` 的 403 宣告 | 下一輪契約修訂 |
| `D8-4` | 分頁參數偏離 `K-08` 的 OpenAPI 半邊 | 同上 |
| `D8-5` | `semantic`／`procedure` 無保存期上界 | **無自然承接站**——須於本站核可關卡重新提交使用者 |
| `D8-6` | correlation id | `U13 brain-gateway` 的 `nfr-design`（轉移目標 `U13` 的 `code-generation`） |
| `D8-7` | `U12`／`U13` 寫入失敗時的行為未定 | 那兩個單元各自的 `functional-design` |
| `FD8-1` | **兩條新依賴邊須回報 `bolt-plan.md`** 並重審 Bolt 順序 | **`bolt-plan.md` 本身**（`delivery-planning` 已在游標之前，故非該站） |
| `I8-1` | 枚舉偵測（需日誌聚合） | 已接受的殘留風險 |
| `I8-2` | 索引失效在生產無偵測面 | 已接受；索引價值依賴 `S14` |
| `I8-4` | `git revert` 不會刪掉索引 | 已記載，無害 |
| `N8-1` | `NFR10` 的落點為 `U11` 的 `nfr-requirements` | `U11` |
| `N8-9` | 無備份策略記載 | 部署面，後續 intent |
| `N8-10` | metrics 承載機制 | **無承接站** |
| `tcms-test-cases` | **blocking，至今未對本 intent 任何單元執行** | construction 階段，部署之前 |
## Testing Contract

```json
{
  "version": 1,
  "methodology": "test-after",
  "source": "fallback",
  "ordering": "Implement each testable layer, then write and run that layer's tests.",
  "scope": "agent-orchestration-brain",
  "test_strategy": "standard",
  "project_type": "brownfield",
  "applicable_notes": [
    {
      "layer": "org",
      "text": "We treat tests as a first-class deliverable in every Bolt. Specific\nmethodology — TDD, BDD, ATDD, or classic test-after — is captured by the\ntesting-strategy stage when it ships.\n\nUntil then, our default per scope is:\n- `mvp`, `enterprise`, `feature`, `infra` → tests written alongside\n  code; minimum 80% line coverage; tests run in CI before merge.\n- `bugfix`, `security-patch` → regression test for the specific\n  bug/vulnerability; existing test suite must remain green.\n- `poc`, `refactor`, `workshop` → existing test suite remains green;\n  no new test floor required.\n\nAffirm a stricter posture in `team.md` if the team commits to one."
    },
    {
      "layer": "team",
      "text": "### 既成事實\n\n- **Backend 測試框架**為 Python 內建 `unittest` + `hypothesis` + `unittest.mock`，**未使用 pytest**。CI 以 `python -m unittest discover -s tests -v` 執行（`ci.yml`）。測試 DB 策略見 `backend/tests/helpers.py`：在任何 DB import 前 `sys.modules.setdefault(\"psycopg2\", MagicMock())`，改走 in-memory SQLite，每 session `ensure_role_permissions_seeded(db, force=True)`。規模：`backend/tests/` 21 個測試檔（HEAD `c3de2c8`；2026-08-06 版「14 個」已過時）。\n- **Frontend e2e** 為 Playwright（chromium 單一 project），涵蓋登入與 RBAC 可視性；`ui-regression` gh-aw workflow 每 PR 對短生命週期 stack 執行並回報 Kiwi TCMS。**這是真閘門**：`post-steps` 讀 `pw-report.json` 的 `.stats.unexpected`，非 0 即 `exit 1`；容忍 `stats.flaky`，`retries: 1`。HEAD 現有 e2e 涵蓋 Admin 最後活動與分頁，**無成本頁 e2e**。\n- **Frontend 完全沒有 unit／component 測試框架**：`frontend/package.json` 的 `devDependencies` 只有 `@playwright/test`，無 vitest、無 jest、無 `@testing-library/*`；`scripts` 只有 `test:e2e`。前端的唯一自動化驗證層就是 Playwright e2e。\n- **Property-based testing**：7 個檔共 13 個 `@given`（HEAD `c3de2c8`；覆蓋 `test_design_agent`、`test_wa_rule_engine`、`test_diagram_builder`、`test_diagram_icons`、`test_collab`、`test_auth`、`test_activity`），皆落在純函式模組，屬自發良好實踐。`project.md` ADR-0006 點名的三個 hard-constraint 落點（IaC generator、cost calculator、agent routing）中，**cost calculator 在本 repo 尚無對應實作模組**，故該約束目前對 repo 現況為 N/A（非豁免、非違反）。本 intent 若新建 calculator 模組，ADR-0006 PBT 約束隨即由 N/A 轉為 blocking。\n- **HTTP 層 TestClient 現況**：`backend/tests/test_user_list_endpoint.py` 用 `starlette.testclient.TestClient` 測 `/api/auth/list` 分頁欄位（樣板在 `tests/helpers.py`）。此為現行唯一 TestClient 使用例；**無 cost router 可測**。\n- **C1 / pricing 測試完全缺席**：無 `test_cost*`；`'C1'`／`\"C1\"` 在 `backend/tests/` 0 命中；`test_rbac.py` 不覆蓋 C1／C2／C3。WA `COST-*` findings 連 example-based 測試都沒有。\n- **完全沒有覆蓋率量測機制**（無 `.coveragerc`、無 `coverage`／`pytest-cov`、CI 無 coverage step）。`org.md` 宣告的「最低 80% line coverage」目前**既無法量測也無法強制，是宣告而非閘門**。\n- **既有授權測試皆在 service 層**：`test_rbac.py`、`test_j5_authz.py`、`test_review_authz.py` 皆非 HTTP 層測試。\n\n### 本輪新增規則（Q4 定案：A + B + C，D 不採）\n\n依據：本 intent 的六道現有 CI 閘門（`repo-contract`、frontend lint、`tsc -b`、backend import smoke、backend `unittest`、`ui-regression`）逐一查證後，**對「後端漏欄位、序列化成 null、前端渲染成空白」這條失敗路徑全部無效**——不是覆蓋率不足的程度問題，是這條變更路徑上沒有任何自動化斷言存在的有無問題。三項零新依賴的測試底線本輪起生效：\n\n- **A — 授權矩陣變更需 allow/deny 雙向測試**：任何 `role_permissions` 預設值變更，必須有測試同時驗證「該角色能做到」與「其他角色做不到」。零新依賴，直接擴充既有 `test_rbac.py`／`test_j5_authz.py` 形狀。C1 的 RBAC seed 種子已存在（`FinOps_Analyst` 與 C1 相關欄位）；若本 intent 改動 C1 預設值（例如讓架構師 edit 時數），屬 seed 變更，須 A 規則測試。\n- **B — 新增或修改 HTTP 端點需 `TestClient` 測試**：斷言其 status code 與 `response_model` 的欄位集合。採用成本為零——`backend/requirements.txt` 已含 `fastapi[standard]` 與 `httpx`，`starlette.testclient.TestClient` 前置條件已滿足；新測試檔放進 `backend/tests/` 即被現有 `python -m unittest discover -s tests` 撿到；`get_db`（`database.py:31`）與 `get_current_user`（`services/auth.py:39`）為穩定的模組層函式，可用 `app.dependency_overrides` 覆寫；以 `TestClient(app)` 直接使用不觸發 `@app.on_event(\"startup\")` 的 `init_db()`，不需要真實 DB。C1 若新增 `/api/cost*` 端點，須依 B 規則補 TestClient 測試，且 CI 的 OpenAPI drift 檢查會要求同步更新 `openapi.json`。\n- **C — 前端資料形狀變更需 e2e 斷言**：例如本次 Admin 表格加欄，須新增至少一個 Playwright case 斷言表頭出現該欄位、且至少一列顯示值或既定的「從未」佔位。用既有 Playwright，不需新依賴，且是目前**唯一**能碰到前端頁面的自動化層。C1 若新建 Cost 頁，資料形狀為全新，須 C 規則 e2e 斷言。\n- **D（不採用）— 引入前端 unit／component 測試框架**：需新增依賴（Vitest 或類似），成本明顯較高，且屬獨立的工具鏈決策，不由本次加欄 feature 夾帶。C 項的 e2e 斷言已覆蓋本 intent 的加欄驗證需求。\n\n- **Q3 定案（A）— C1 HTTP 消費者的最小授權測試義務**：即使 `role_permissions` seed 資料未修改（C1 種子已存在於 `rbac_seed_data.py`），第一個 C1 HTTP 端點落地時仍須補 allow/deny 雙向 TestClient 測試——「具 C1 權限的角色應收到 2xx」與「無 C1 權限的角色應收到 403」兩個案例缺一不可。此為 A 規則與 B 規則的交叉要求，適用於本 intent 新增的任何 `/api/cost*` 端點。\n\n### 80% 覆蓋率門檻的定位\n\n**維持 `org.md` 原文，不在本檔弱化或改寫其宣稱**（把「80% 是目標不是閘門」寫進 `team.md` 會構成 `team.md` 弱化 `org.md` 的矛盾，屬 §13 learning admission 應擋下的形狀）。如實記載目前無法量測、無法強制的現況（見上），並以上述 A/B/C 三項變更範圍內、二元可判、零工具成本的規則作為現階段的實際門檻。導入 `coverage.py` 量測工具列為待補承載機制（見 `discovered-rules.md`）。\n\n---"
    },
    {
      "layer": "project",
      "text": "**Property-based testing 為 hard constraint**（ADR-0006）。下列核心模組的測試必須包含 property-based 測試，不得只有 example-based：IaC generator、cost calculator、agent routing。其餘模組沿用 `org.md` 的預設門檻。"
    }
  ],
  "obligations": {
    "strategy": "standard",
    "strategy_volume": [
      "Five to eight tests per component.",
      "Unit tests plus integration tests for key boundaries.",
      "Add E2E, performance, or security tests when requirements demand them."
    ],
    "scope_floor": [
      "Keep the existing test suite green.",
      "This scope adds no extra new-test floor beyond the selected test strategy."
    ],
    "combination_rule": "Apply every selected-strategy obligation and every scope-floor obligation; neither replaces the other, and a targeted scope regression may add the narrowest necessary test type beyond the strategy default."
  },
  "plan_profile": {
    "methodology": "test-after",
    "runner_step": "Verify the existing test runner/configuration and record the exact unit-scoped command.",
    "runner_ready_before_first_test": true,
    "testable_layers": [
      "Data model / database behavior",
      "Repository / data access",
      "Business logic",
      "API / endpoint",
      "Frontend behavior"
    ],
    "steps": [
      "Project structure and production configuration skeleton.",
      "Verify the existing test runner/configuration and record the exact unit-scoped command.",
      "Data model / database behavior - implement.",
      "Data model / database behavior - write and run its tests after implementation.",
      "Repository / data access - implement.",
      "Repository / data access - write and run its tests after implementation.",
      "Business logic - implement.",
      "Business logic - write and run its tests after implementation.",
      "API / endpoint - implement.",
      "API / endpoint - write and run its tests after implementation.",
      "Frontend behavior - implement.",
      "Frontend behavior - write and run its tests after implementation.",
      "Environment/build configuration.",
      "Documentation and traceability."
    ]
  },
  "input_sha256": "sha256:1aedc10dd7de9a19bd06fecb49cbcb5f27456db7ce4b18e81d500355d460bea6",
  "contract_sha256": "sha256:1f0b6822601f52ff3e71a9bd20a949c9e106f87999f78c986398d5e1963f2f77"
}
```

## 七、方法論適用說明（`test-after`，`standard`）

上方的 `## Testing Contract` 由
`bun .claude/tools/aidlc-testing-posture.ts render --unit memory-service` 產生，
**未經任何編輯**。

| 契約項 | 本計畫的落實 |
|---|---|
| `methodology: test-after` | 每層先實作再測：Step 2 → 6.1 第 ④；Step 3 → 6.2；Step 4／5 → 6.3；Step 7 → `S14`／`S15` |
| `runner_ready_before_first_test: true` | Step 1.2 在任何測試步驟之前記錄並驗證兩個單元範圍指令 |
| `testable_layers` 的 `Data model / database behavior` | Step 2（ORM）＋ Step 7（schema ＋ `S14`／`S15`） |
| `testable_layers` 的 `Repository / data access` | Step 4（`memory_service` 的單一 SQL） |
| `testable_layers` 的 `Business logic` | Step 3（純函式）＋ Step 5.1–5.4（facade 的授權） |
| `testable_layers` 的 `API / endpoint` | Step 5.5–5.7 → 驗於 6.3 的 TestClient |
| `testable_layers` 的 `Frontend behavior` | **不適用**：本單元零前端面。`U15 memory-page-ui` 是消費端，屬該單元 |
| `test_strategy: standard`（每元件 5–8 測試 ＋ 關鍵邊界的整合測試） | 靜態契約 5 條 ＋ PBT 1 條（含多個 property）＋ TestClient 約 12 條 ＋ `S14`／`S15` 共 4 條斷言 |
| `scope_floor`：既有測試須維持綠燈 | Step 10.5 |
| `project.md` 的 PBT hard constraint | **N/A（非豁免）**——ADR-0006 點名的三個落點（IaC generator、cost calculator、agent routing）皆不是本單元。但 `NFR3.24` 的純函式**仍有** PBT（Step 6.2），屬 `team.md` 記載的自發良好實踐 |

### 覆蓋率門檻

`org.md` 宣告 80% line coverage；本 repo **無覆蓋率量測機制**
（`team.md` 逐字「既無法量測也無法強制，是宣告而非閘門」）。
**本計畫不宣稱滿足該數字、也不弱化它**，改以上表的斷言總數
＋ Step 9 的六項突變驗證作為實際門檻，並如實記載落差。

## 八、ADR-0006 四面向：本計畫的落點

逐格對照 `nfr-design/security-design.md §八` 與
`infrastructure-design/infrastructure-specification.md §六`。**不改任何判定。**

| 面向 | 判定 | 本計畫的程式落點 |
|---|---|---|
| **IAM** | 適用（本單元最寬的一格） | Step 5.1／5.2 的兩套模型分離 ＋ 角色判定只一份；Step 5.3 的 `[D1]`=A 收斂；驗於 6.3 的 allow/deny ＋ 6.1 第 ③ 條（router 不含角色字串） |
| **Encryption** | 適用，無增量 | 不新增儲存體；新 `POST` 走既有 TLS 路徑。**不寫「不適用」** |
| **Network exposure** | 適用，有增量 | 新增一條對外寫入面（`POST`），零新監聽埠；驗於 Step 10.3 的 `deploy/` diff 為空 |
| **Audit logging** | 適用（核心之一） | Step 4.3 的同交易邊界；**Step 5.3 之後日誌是枚舉偵測的唯一面**，故 6.3 必須斷言「狀態碼相同、日誌可區分」 |

## 九、公開 repo 的輸出禁令

本 repo 為 public，**Actions log 公開可讀**（`project.md` 逐字
「一次意外 echo 即等同公開發布」），而本單元處理的是**個人對話歷程**。

| 禁令 | 落點 | 驗證 |
|---|---|---|
| 日誌不得含 `content`／`embedding`／整個模型物件 | Step 4.5／5.3 的全部日誌呼叫 | **Step 6.1 第 ⑤ 條（靜態斷言）＋ 6.3 的字串比對** |
| 錯誤訊息不得回傳他人記憶的任何欄位 | Step 5.3 的 `MemoryNotFound` 不帶內容 | 6.3 斷言 404 回應體不含 fixture 的 `content` |
| 測試輸出不得印記憶內容 | Step 6 全部 | 人工核對 |

**第一條是本單元最容易出的錯**：`logger.warning(f"denied: {memory}")`
在功能上完全正常、測試也會綠，而它把整列（含 `content`）寫進公開可讀的日誌。
故 6.1 第 ⑤ 條是**靜態**斷言（掃日誌呼叫的引數形狀），
不只依賴 6.3 的執行期字串比對——後者只在被觸發的路徑上有效。
