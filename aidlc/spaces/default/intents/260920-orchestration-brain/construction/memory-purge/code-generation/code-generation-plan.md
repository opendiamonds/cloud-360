# Code Generation 計畫 — `U9 memory-purge`

> 本單元的交付物**本身就是基礎設施**：兩個 GitHub Actions workflow、一份清除 SQL、
> 一列保留的系統 actor seed。**零 Python 應用程式邏輯、零端點、零前端面。**
>
> 故 `plan_profile.steps` 的 `API / endpoint` 與 `Frontend behavior` 兩層
> **對本單元不適用**（照 stage 檔「omitting genuinely inapplicable layers
> without changing the methodology」），而 `Repository / data access` 層由
> `Data model / database behavior` 吸收——清除沒有 ORM 層，它就是 SQL。
> 方法論維持 `test-after`，順序維持「先實作該層、再寫並跑該層的測試」。

## 〇、上游依據（逐一指名，便於複驗）

| 上游 | 本計畫用到它的什麼 |
|---|---|
| `nfr-requirements/security-requirements.md` | 八條需求 `NFR7.10`–`NFR7.15`、`NFR6.10`、`NFR8.10` 與其二元判準 |
| `nfr-design/security-design.md` | 系統 actor 的四個欄位與三道鎖（§一）、`NFR6.10` 的更正（§二）、順序與交易邊界（§三） |
| `infrastructure-design/infrastructure-specification.md` | 兩個 workflow 的落點與排程（§二之一）、`ON CONFLICT` 的可重跑要求（§五之一）、`DEPLOY.md` 同步義務（§五之二） |
| `infrastructure-design/monitoring-design.md` | `NFR7.13` 的監看機制、3 天門檻、去重、`RETURNING *` 禁令（§五之一） |
| `infrastructure-design/cicd-pipeline.md` | 同一次 `psql` 呼叫的交易邊界（§三之一）、`status=success` 過濾（§四之一）、不可逆性與 dry-run（§五之一） |
| `infrastructure-design/reviews/review-01.md` | `R-01`（compose 呼叫未固定 ＋ 與 `deploy.yml` 的並發未分析）、`R-02`（dry-run 只驗 count） |
| `inception/requirements-analysis/requirements.md` | `FR4.5`（90 天、**僅 episodic**）、`FR4.5a`（純 Actions 步驟）、`FR4.7`（刪除留稽核）、`OQ-13` |
| `inception/contract-design/contract-summary.md` | `K-05`（本單元消費的 schema 契約）、`K-15` 的 `observable_side_effects`（**本計畫第 3 步的關鍵約束**） |
| `inception/units-generation/unit-of-work.md` | `U9` 的擁有與交付、驗證方式（workflow 實跑）、`packaging`／S |
| `schema_rbac.sql`、`backend/scripts/run_meta_schema_migration.py`、`backend/services/user_router.py`、`backend/services/auth.py`、`.github/workflows/ci.yml`、`.github/workflows/deploy.yml`（版控） | 本計畫 §一 的五項實測事實 |

## 一、本計畫寫作期間實測查出的五項事實（其中三項改變了設計）

這五項全部以開檔核對取得，逐項附檔名與行號供複驗。

### 1.1 **上游的清除條件會刪錯列**（改變設計，最嚴重的一項）

`security-requirements.md` 的 `NFR7.10` 二元判準逐字寫
`memory.memory_records WHERE expires_at < now()`，**沒有 `kind` 過濾**。

| 事實 | 逐字依據 |
|---|---|
| `FR4.5` 的保存期**只**約束 episodic | `requirements.md:157` 逐字「**episodic memory** 保存 **90 天**」 |
| schema 自己也這樣寫 | `schema_rbac.sql:478` 逐字「FR4.5 scopes the 90-day retention to **episodic memory ONLY**」 |
| 而 CHECK **不禁止**非 episodic 帶 `expires_at` | `schema_rbac.sql:460-461`：`CHECK (kind <> 'episodic' OR expires_at IS NOT NULL)`——它要求「episodic ⇒ 非 NULL」，**沒有**要求「非 episodic ⇒ NULL」 |

**後果**：照 `NFR7.10` 的判準字面實作，一列 `kind = 'semantic'` 而恰好帶了過去
`expires_at` 的記憶**會被刪除**，而 `FR4.5` 明文不約束它。那是**永久資料損失**，
且 CI 不會抓（既有測試走 SQLite，沒有任何清除測試存在）。

**本計畫的處置**：清除條件一律為 `kind = 'episodic' AND expires_at < now()`，
並在第 7 步以一條專門的斷言（`R4`）鎖住它——fixture 內**刻意**放一列
`kind = 'semantic'` ＋ 過去 `expires_at`，斷言它在清除後**仍然存在**。
`NFR7.10` 的判準在本檔**收窄而非推翻**（它漏了一個條件，不是選錯條件），
並記為 `OPEN-CG9-1` 回報上游修訂判準文字。

### 1.2 **「重跑 `schema_rbac.sql`」是破壞性操作**（改變設計）

`infrastructure-specification.md §五` 第 2 步逐字寫「**重跑 `schema_rbac.sql`**
（既有環境取得 seed 的唯一路徑）」。該敘述的代價我當時沒有查。

| 事實 | 逐字依據 |
|---|---|
| 該檔會先清空再重播權限矩陣 | `schema_rbac.sql:715` 逐字 `DELETE FROM role_permissions;`，`:717` 起重播預設 |
| 檔頭自己警告過 | `schema_rbac.sql:23` 逐字「role_permissions 會 DELETE 後重播預設（**Admin UI 調過請先備份**）」 |

**後果**：照 §五 的指示在 staging 重跑整支檔，會**清掉任何經 Admin UI 調整過的
權限矩陣**。那不是「可重跑所以安全」，那是一次無聲的設定回退。

### 1.3 **既有的遷移腳本不能承載這個 seed**（改變設計）

既有環境取得 `X)`／`I)`／`J)` 的路徑是 `run_meta_schema_migration.py`，
它**直接解析 `schema_rbac.sql` 的區塊**執行（`:26` 逐字），所以 DDL 只有一份。
把 seed 掛上去看似順理成章，**但它被契約禁止**：

| 事實 | 逐字依據 |
|---|---|
| 該腳本的輸出自己宣告不寫資料 | `run_meta_schema_migration.py:446-448` 逐字「本指令**不驗證** schema_rbac.sql 的其餘區塊，**也不塞任何資料**（契約 `K-15` 的 `observable_side_effects` 逐字「不含任何資料寫入」）」 |
| 它以字母定位區塊，重複字母會大聲失敗 | `:196-200` 的 `RuntimeError`（「有兩個 `<letter>)` 區塊標題」） |
| 新字母不在 `BLOCKS_TO_RUN` 則被解析但不執行 | `:84` 的 `BLOCKS_TO_RUN = ("X", "I", "J")` ＋ `:204-218` 的 `for letter in letters` |

**本計畫的處置（§1.2 ＋ §1.3 的合併解）**：
seed 的 SQL **只有一份**，寫在 `schema_rbac.sql` 的**新 `K)` 區塊**；
由**新增的** `backend/scripts/seed_retention_system_actor.py` 解析 `K)` 並執行
——它 `import` 既有的 `extract_blocks`，所以不複製解析邏輯，也不複製 SQL。
三條路徑因此**不可能漂移**：空 volume（整支檔）、既有環境（新腳本解析 `K)`）、
CI（`memory-schema` job 套用整支檔）。
`K-15` 不被破壞（新腳本不是它約束的那一支），`role_permissions` 不被清空。

### 1.4 **系統 actor 的 `password_hash` 若為非 bcrypt 格式，會製造一個未驗證即可觸發的 500**（改變設計，與上游不一致，故在此明列）

`security-design.md §1.2` 逐字要求 `password_hash` 為
「**結構上不可能比對成功**的哨符字串（**非 bcrypt 格式**）」，理由逐字是
「給一個非 bcrypt 格式的值使 `bcrypt.checkpw` 不可能回 True」。

**該理由正確但不完整**，而缺的那一半把 401 變成 500：

| 事實 | 逐字依據 |
|---|---|
| 登入端點**先**比對密碼、**後**查 `is_active` | `user_router.py:406` 的 `if not verify_password(...)` 在 `:408` 的 `if not user.is_active:` **之前** |
| `verify_password` 沒有任何 `try/except` | `auth.py:37-40`：函式體就是 `return bcrypt.checkpw(plain_bytes, hashed_bytes)` |
| `bcrypt` 對非 bcrypt 格式的 hash **拋 `ValueError`**，不是回 `False` | 本 session 前一站以執行實測（`ValueError: Invalid salt`）；本計畫第 9 步把它轉成**可執行斷言**而非沿用轉述 |
| 登入查詢會把輸入轉小寫 | `user_router.py:403` 的 `.filter(User.username == request.username.lower())` |

**後果**：`POST /api/auth/login` 帶哨符 username ＋ 任意密碼 →
`verify_password` 拋 `ValueError` → FastAPI 轉 **500**。那是一個
**未經驗證即可遠端觸發的 500**，而且 500／401 的差異構成一個帳號存在性 oracle。
§1.2 的第一道鎖（`is_active = FALSE`）在登入路徑上**永遠輪不到執行**。

**本計畫的處置（兩項，皆零成本、皆不動既有程式）**：

| # | 處置 | 效果 |
|---|---|---|
| 1 | 哨符 username **含大寫字母**：`SYSTEM.retention-purge` | `user_router.py:403` 的 `.lower()` **永遠不可能**產生這個字串 → 查詢回 `None` → `:405` 回 **401**。`verify_password` 根本不被呼叫 |
| 2 | `password_hash` 改為**格式合法的 bcrypt hash，其明文為一次性隨機值且未被記錄** | 即使未來有別的路徑找到這一列，`checkpw` 會乾淨地回 `False` 而非拋例外。公開 repo 內放一個無已知前像的 bcrypt hash **不是憑證**，不可反推 |

**這是與已核可上游不一致的一格**，依 `project.md`（「與上游相反的判定比沒跑這道
檢查更糟」）在此明列而非靜默覆蓋：§1.2 的「非 bcrypt 格式」被本計畫**取代**，
理由是上游把「不可能回 True」與「會回 False」當成同一件事，而該函式**會拋**。
三道鎖的數量不減反增（大寫 username ＋ 格式合法但不可比對的 hash ＋
`is_active = FALSE` ＋ 非 canonical role，共四道）。

**不在本單元修的那一項**，記為 `OPEN-CG9-2`：`verify_password` 應當捕捉
`ValueError` 並回 `False`。它是**既有的**潛在 500——資料庫內**任何**來源的畸形
hash 都會觸發它，不是本單元引入的——而 `auth.py` 不屬本 `packaging` 單元，
`team.md` 也明文反對在功能變更的同一個 PR 夾帶既有共用程式的重構。

### 1.5 **R-01 的第二半不能照審查的建議做**（審查建議的其一會製造更糟的後果）

審查 `R-01` 建議「若可能有多行程則須新增與 `deploy.yml` **共用**的 concurrency 群組」。

| 事實 | 依據 |
|---|---|
| `deploy.yml` 的群組與設定 | `deploy.yml:20-22`：`group: deploy-10-10`、`cancel-in-progress: false` |
| 該 runner 上的所有 compose 呼叫都帶固定旗標 | `deploy.yml:124,137,198,250,349,350,364`（實測 9 處）全部帶 `-f deploy/docker-compose.deploy.yml --env-file deploy/.env` |
| `deploy.yml` 會重建 `db` 容器 | `:124` 與 `:471` 的 `up -d --build --remove-orphans` |
| GitHub 的排隊語意 | 同一 concurrency 群組**只允許一個 pending run**；新的排入會**取消先前那個 pending run** |

**後果**：若清除與 `deploy.yml` 共用 `deploy-10-10`，一個每日排程的清除排入時
**會取消一個正在排隊的部署**。部署是本 repo 的主路徑，而清除是一個每日兩秒的
維護作業——用「取消部署」去換「避免一次連線中斷」是錯的方向。

**本計畫的處置**：
1. **固定 compose 呼叫**（`R-01` 的第一半，照建議做）：清除的 compose 呼叫一律帶
   `-f deploy/docker-compose.deploy.yml --env-file deploy/.env`，不依賴預設工作目錄。
2. **清除使用自己的 concurrency 群組**，不與 `deploy-10-10` 共用，並在 workflow
   註解內寫明上表的四項事實與這個取捨。
3. **把「最壞情況是安全的」從宣稱變成測試**（第 8 步）：以真實 PostgreSQL ＋ 兩條
   連線，在清除交易**尚未 COMMIT** 時用 `pg_terminate_backend` 切斷它，斷言
   「一列都沒被刪、一列稽核都沒寫」。審查要求「補上此結論」——本計畫補的是
   **可執行的證明**而不是一段敘述。

## 二、交付物清單（14 個檔，其中 7 新 7 改）

| # | 路徑 | 新／改 | 內容 |
|---|---|---|---|
| 1 | `schema_rbac.sql` | 改 | 新 `K)` 區塊：保留系統 actor seed ＋ COMMENT；檔頭 TOC 與注意事項各加一條 |
| 2 | `backend/scripts/seed_retention_system_actor.py` | **新** | 既有環境的 seed 路徑；解析 `K)` 區塊，單一交易，後條件逐項查證 |
| 3 | `backend/scripts/purge_expired_memory.sql` | **新** | 清除本體。兩個顯式交易於**同一檔**，故交易邊界不依賴 workflow 怎麼切步驟 |
| 4 | `backend/scripts/purge_dry_run.sql` | **新** | dry-run（`OPEN-ID9-4`）：印計數**與選取範圍的邊界**（`R-02`） |
| 5 | `backend/scripts/verify_purge_sql.sql` | **新** | CI 斷言（`R1`–`R10`）。**`\i` 引入第 3 項**，故 CI 與生產跑的是同一份文字 |
| 6 | `backend/tests_pg/test_purge_atomicity.py` | **新** | 真實 PostgreSQL ＋ 兩條連線：證明 `R-01` 的最壞情況安全 |
| 7 | `backend/tests/test_retention_purge_contract.py` | **新** | 靜態契約斷言：`RETURNING *` 禁令、`kind = 'episodic'`、`ON CONFLICT`、`status=success`、單一真實來源 |
| 8 | `.github/workflows/memory-retention-purge.yml` | **新** | 自架 runner、每日排程 ＋ `workflow_dispatch`（含 `dry_run` 輸入） |
| 9 | `.github/workflows/memory-retention-watchdog.yml` | **新** | GitHub 託管、每日、`status=success`、3 天門檻、去重 |
| 10 | `.github/workflows/ci.yml` | 改 | `memory-schema` job 加一個步驟跑第 5 項 |
| 11 | `DEPLOY.md` | 改 | 新 §2.2.11（**blocking 同步**）：seed、兩個 workflow、**以及 §1.2 的更正** |
| 12 | `backend/scripts/verify_memory_schema.sql` | 改 | 加 `S13`：系統 actor 列存在且四道鎖成立 |
| 13 | `backend/scripts/run_meta_schema_migration.py` | 改 | **只加註解**：指出 `K)` 刻意不在 `BLOCKS_TO_RUN` 內及其理由（`K-15`） |
| 14 | `openapi.json`／`frontend/src/types/api.d.ts` | **不動** | 零端點。本單元不觸發 OpenAPI drift 閘門 |

**`LOCAL-DEV.md` 不觸發**：`project.md` 的觸發清單為「異動 `backend/database.py` 的
schema 補丁、`deploy/nginx.conf`、任一 `.env.example` 或 `render-env.sh`」
——本單元四者皆不動（`database.py` 的 diff 必須為空，第 13 步逐項驗）。

## 三、實作步驟

### Step 1 — 前置查證與測試執行器就緒（`runner_ready_before_first_test`）

- [x] 1.1 確認 `backend/tests_pg/` 與其 `__init__.py` 的 `require_pg_url` 存在（`U19` 交付），本單元**沿用**不新建
- [x] 1.2 記錄兩個單元範圍指令並確認在第一個測試步驟之前可執行：
  - `cd backend && python3 -m unittest tests.test_retention_purge_contract -v`
  - `cd backend && python3 -m unittest tests_pg.test_purge_atomicity -v`（需 `DATABASE_URL` 指向真實 PostgreSQL）
  - `psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/scripts/verify_purge_sql.sql`（於 repo 根目錄執行，`\i` 的相對路徑依賴它）
- [x] 1.3 `git diff --stat -- backend/database.py` 必須為空（開工前記錄基準）
- [ ] 1.4 確認 `schema_rbac.sql` 目前**沒有** `K)` 區塊標題（避免 `extract_blocks` 的重複字母 `RuntimeError`）

### Step 2 — 資料模型／資料庫行為：`K)` 區塊的系統 actor seed（implement）

- [x] 2.1 在 `schema_rbac.sql` 的 `J)` 區塊之後、`C) RBAC` 區塊**之前**插入新區塊，標題形狀必須與既有區塊一致（`-- ####…` 行 ＋ `-- K) …` 行），否則 `extract_blocks` 抓不到：

```sql
-- ###########################################################################
-- K) U9 memory-purge: reserved system actor（NFR7.11）
-- ###########################################################################
```

- [x] 2.2 區塊內容：一條 `INSERT ... ON CONFLICT (username) DO NOTHING`，四個欄位依下表。**`ON CONFLICT` 不是潔癖**：本檔是單一交易（`:43` 的 `BEGIN`），`ix_users_username` 的 UNIQUE 違反會讓**整支檔從那一行起全部中止**，包含其後的 `C)` 區塊

| 欄位 | 值 | 鎖 |
|---|---|---|
| `username` | `SYSTEM.retention-purge`（**含大寫**，見 §1.4） | 登入查詢的 `.lower()` 永不產生它 |
| `password_hash` | 格式合法的 bcrypt hash，明文為一次性隨機值且**不記錄** | `checkpw` 乾淨回 `False`，不拋 |
| `role` | `system`（**非** canonical role） | `rbac.py:54-55` 全部權限判為拒 |
| `is_active` | `FALSE` | `auth.py:75`／`user_router.py:408` 拒絕 |

- [x] 2.3 `COMMENT` 不可省：寫明它是什麼、四道鎖各由哪一行承載、以及**刪掉它的後果**（清除的稽核 INSERT 自那一刻起全部因外鍵違反而失敗，整個交易中止）
- [x] 2.4 更新 `schema_rbac.sql` 檔頭：TOC（`:5-16`）加 `K)` 一列；注意事項（`:21-40`）加一條說明既有環境的 seed 路徑是**新腳本**而**不是**重跑整支檔，並逐字指出 `:715` 的 `DELETE FROM role_permissions`（§1.2）
- [x] 2.5 `backend/scripts/run_meta_schema_migration.py`：在 `BLOCKS_TO_RUN`（`:84`）旁加註解，寫明 `K)` **刻意不在**此清單內及其理由（`K-15` 的 `observable_side_effects` 逐字「不含任何資料寫入」），並指向新腳本。**不改任何可執行行為**
- [ ] 2.6 `backend/scripts/seed_retention_system_actor.py`：`from run_meta_schema_migration import extract_blocks` 取得解析器（**不複製**），執行 `K)` 區塊，在 COMMIT **之前**逐項查證後條件：該 username 恰有 1 列、`is_active` 為 false、`role` 不在 `CANONICAL_ROLES`、`password_hash` 符合 bcrypt 格式。任一不成立則 rollback ＋ 非零碼。**不得輸出 `DATABASE_URL` 或其片段**（沿用既有腳本 `:55-59` 的禁令），只印 host 與 database 名

### Step 3 — 資料庫行為的測試（test-after，本層）

- [x] 3.1 `backend/scripts/verify_memory_schema.sql` 加 `S13`：系統 actor 列存在，且 `is_active = false`、`role` 非 canonical、`password_hash` 符合 `^\$2[aby]\$` 三者皆成立
- [x] 3.2 第 5 步的 `verify_purge_sql.sql` 會重跑一次 seed 區塊以驗可重跑性——由 `memory-schema` job 既有的「第二次套用」步驟涵蓋，本步只確認該步驟仍存在且會覆蓋 `K)`

### Step 4 — 業務邏輯：清除 SQL 本體（implement）

- [x] 4.1 `backend/scripts/purge_expired_memory.sql`，**兩個顯式交易，同一檔**。把交易邊界放進檔案而不是 workflow，使 `cicd-pipeline.md §三之一` 的要求**結構上不可能被拆步驟破壞**
- [x] 4.2 交易一：**單一敘述**的 data-modifying CTE，刪除與稽核不可分離：

```sql
BEGIN;
WITH purged AS (
  DELETE FROM memory.memory_records
   WHERE kind = 'episodic'          -- §1.1：少了這個條件會刪到非 episodic 的列
     AND expires_at < now()
  RETURNING id
), logged AS (
  INSERT INTO memory.memory_audit_events (memory_id, actor_user_id, action)
  SELECT p.id,
         (SELECT id FROM users WHERE username = 'SYSTEM.retention-purge'),
         'purged_by_retention'
    FROM purged p
  RETURNING id
)
SELECT (SELECT count(*) FROM purged) AS memories_purged,
       (SELECT count(*) FROM logged) AS audit_rows_written;
COMMIT;
```

  **為什麼是一條敘述而不是上游 §3.1 的兩步**：`security-design.md §3.1` 的順序
  （先寫稽核、再刪記憶）的理由逐字是「稽核必須先於它描述的對象消失落地」，
  要防的是**中途失敗留下「記憶已消失而稽核不存在」**。在單一交易內兩者同時於
  COMMIT 落地，該中間狀態**不存在**；而 CTE 形式更強一層：稽核列的來源是 DELETE
  的 `RETURNING`，故 `NFR7.11` 的「刪 N 列 ⇒ N 筆稽核」**結構上恆等**，
  而兩條獨立敘述之間的謂詞會被重新求值（兩次 `now()` 不同值）。
  **這是對已核可上游的步驟順序的偏離，理由如上，第 7 步以 `R6` 鎖住恆等性。**
- [x] 4.3 交易二（獨立）：`DELETE FROM memory.memory_audit_events WHERE occurred_at < now() - interval '90 days' RETURNING id;` ＋ 計數輸出
- [x] 4.4 **`RETURNING *` 絕對禁令**：全檔只許 `RETURNING id`。`RETURNING *` 會把
      `content` 印進**公開可讀**的 Actions log（`monitoring-design.md §五之一`）。
      第 9 步以靜態斷言鎖住它
- [x] 4.5 連線身分不得覆寫：檔內與呼叫端皆不得出現 `-U`（`NFR6.10` 的保留要求，`security-design.md §2.2`）
- [x] 4.6 `backend/scripts/purge_dry_run.sql`：**只 SELECT，零 DELETE、零 INSERT**。依 `R-02` 除計數外必須印出選取範圍的邊界——兩個集合各自的 `min`／`max` 時間戳與**最多 10 筆 id**。**不得**印 `content`、`embedding` 或任何可識別資料

### Step 5 — 清除 SQL 的測試（test-after，本層）

- [x] 5.1 `backend/scripts/verify_purge_sql.sql`：於 repo 根目錄以 `psql -f` 執行。fixture → `\i backend/scripts/purge_expired_memory.sql` → 斷言。**`\i` 是刻意的**：CI 與生產因此跑同一份文字，不可能漂移
- [x] 5.2 fixture 必須包含下列**邊界**列（這是 `R-02` 的本質：驗的是「選到哪些列」而不只是「選到幾列」）：

| fixture 列 | 期望 |
|---|---|
| `episodic`，`expires_at = now() - 1 day` | **被刪**，且產生 1 筆 `purged_by_retention` |
| `episodic`，`expires_at = now() + 1 day` | **保留** |
| **`semantic`，`expires_at = now() - 1 day`** | **保留**（§1.1 的陷阱列） |
| `procedure`，`expires_at IS NULL` | **保留** |
| 稽核列 `occurred_at = now() - 91 days` | **被刪** |
| 稽核列 `occurred_at = now() - 89 days` | **保留** |

- [x] 5.3 斷言 `R1`–`R10`（每條以 `DO $$ ... RAISE EXCEPTION ... $$` 形狀，沿用 `verify_memory_schema.sql` 既有樣板）：

| id | 斷言 |
|---|---|
| `R1` | 逾期 episodic 列已不存在 |
| `R2` | 未逾期 episodic 列仍存在 |
| `R3` | `procedure`／`expires_at IS NULL` 列仍存在 |
| `R4` | **`semantic` ＋ 過去 `expires_at` 的列仍存在**（§1.1） |
| `R5` | 新增的 `purged_by_retention` 稽核列數 **等於** 被刪的 episodic 列數 |
| `R6` | 每一筆新稽核列的 `memory_id` 都在被刪的 id 集合內，且無重複、無遺漏 |
| `R7` | 新稽核列的 `actor_user_id` 等於哨符 username 的 id，且**不等於**任何 fixture 記憶的 `owner_user_id` |
| `R8` | 91 天前的稽核列已不存在 |
| `R9` | 89 天前的稽核列仍存在 |
| `R10` | 步驟一剛寫的稽核列**未被**交易二刪除（`occurred_at = now()`，與順序無關，`security-design.md §3.1` 第 3 列的命題） |

### Step 6 — 原子性測試：`R-01` 最壞情況的可執行證明（test-after）

- [x] 6.1 `backend/tests_pg/test_purge_atomicity.py`，沿用 `U19` 的 `tests_pg` 形狀（`require_pg_url`，缺 `DATABASE_URL` 時**大聲失敗**而非退回 SQLite）
- [x] 6.2 三個測試：
  - `test_terminated_before_commit_deletes_nothing`：連線 A 開交易跑 CTE（**不 COMMIT**）；連線 B 以 `pg_terminate_backend` 切斷 A；斷言記憶列與稽核列數**完全不變**。這就是 `deploy.yml` 重建 `db` 容器時的情境
  - `test_committed_purge_is_atomic_in_both_directions`：正常 COMMIT 後，刪除數與稽核數相等且皆非零
  - `test_missing_system_actor_aborts_whole_transaction`：移除哨符列後跑 CTE，斷言拋錯**且記憶列一列都沒少**（`security-design.md §1.4` 的「大聲失敗」）

### Step 7 — 靜態契約測試：把三道「CI 不會抓」變成 CI 會抓（test-after）

- [x] 7.1 `backend/tests/test_retention_purge_contract.py`，純文字斷言，**零新依賴**，落在既有 `backend` job 的 `discover -s tests`
- [x] 7.2 斷言（8 條）：

| # | 斷言 | 它防的事 |
|---|---|---|
| 1 | `purge_expired_memory.sql` 不含 `RETURNING *` | 公開 log 洩漏記憶內容 |
| 2 | 同檔含 `kind = 'episodic'` | §1.1 的刪錯列 |
| 3 | 同檔不含 ` -U ` | `NFR6.10` 的身分覆寫 |
| 4 | `purge_dry_run.sql` 不含 `DELETE`／`INSERT`／`UPDATE` | dry-run 名不副實 |
| 5 | `schema_rbac.sql` 的 `K)` 區塊含 `ON CONFLICT (username) DO NOTHING` | 重跑整支檔從該行起全部中止 |
| 6 | 腳本的哨符常數與 `K)` 區塊、清除 SQL 內的字串**三者逐字相同** | 單一真實來源（`team.md`）；拼錯的後果是外鍵違反或永不命中 |
| 7 | `verify_password(<任意>, <K) 區塊內的 hash>)` 回 `False` **且不拋例外** | §1.4 的 500。**這是把轉述轉成可執行斷言** |
| 8 | watchdog workflow 含 `status=success` | `cicd-pipeline.md §四之一`：每天都失敗會被判為新鮮 |

### Step 8 — 環境／建置設定：清除 workflow（implement）

- [ ] 8.1 `.github/workflows/memory-retention-purge.yml`：

| 項目 | 值 |
|---|---|
| `runs-on` | `[self-hosted, linux, x64, cloud360]` |
| 觸發 | `schedule`（每日 UTC 離峰）＋ `workflow_dispatch`（含 boolean 輸入 `dry_run`，預設 `true`） |
| `permissions` | `contents: read`（僅此） |
| `concurrency` | **自己的**群組 ＋ `cancel-in-progress: false`（**不**與 `deploy-10-10` 共用，理由見 §1.5，須寫進註解） |
| `timeout-minutes` | 明確設定（10） |
| compose 呼叫 | **固定**：`docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env exec -T db psql ...`（`R-01` 第一半） |
| SQL 來源 | 版控的 `.sql` 檔，以 stdin 餵入；**不在 YAML 內內嵌 SQL**（單一真實來源） |
| 失敗行為 | 非零碼結束，**不重試**（`security-design.md §3.3`） |

- [x] 8.2 `dry_run` 為真時只跑 `purge_dry_run.sql`；為假時跑 `purge_expired_memory.sql`。**排程觸發一律走實際清除**（`dry_run` 的預設只影響手動觸發）
- [x] 8.3 兩條 SQL 都以**單一** `psql` 呼叫執行，且 `-v ON_ERROR_STOP=1`

### Step 9 — 環境／建置設定：監看 workflow（implement）

- [x] 9.1 `.github/workflows/memory-retention-watchdog.yml`：`ubuntu-latest`、每日 `schedule` ＋ `workflow_dispatch`、`permissions: {contents: read, actions: read, issues: write}`、`timeout-minutes: 5`
- [x] 9.2 邏輯（**純 Actions，零 LLM**，`NFR7.14`）：`gh api` 查清除 workflow **`status=success`** 的最新 run → 距今 > 3 天（或**查不到任何成功 run**）即視為逾期
- [x] 9.3 去重：開 issue 前以固定標題前綴查 open issue，已有則不開第二個（`monitoring-design.md §三之一`）
- [x] 9.4 逾期時**同時**開 issue **並**以非零碼結束（兩個可見面，讀者不同）
- [x] 9.5 **零新 secret**：只用內建 `GITHUB_TOKEN`

### Step 10 — 把斷言掛進 CI

- [x] 10.1 `ci.yml` 的 `memory-schema` job 加一個步驟跑 `verify_purge_sql.sql`，置於既有 `P1-P12` 步驟之後
- [x] 10.2 **不新增 job**：該 job 的前置條件（真實 PostgreSQL ＋ 已套用的 `schema_rbac.sql`）完全相同，另開一個等於把同一座 service container 建第二次（沿用 `ci.yml:314-320` 既有註解的同一個理由）
- [x] 10.3 `tests_pg/test_purge_atomicity.py` **不需**改 `ci.yml`：`concurrency` job 已是 `discover -s tests_pg`，新檔自動被撿到
- [x] 10.4 **誠實限定**：`ut` 沒有任何必要狀態檢查，故這兩道是**訊號而非閘門**（承 `OPEN-ID19-6`，不重複立項）

### Step 11 — 突變驗證（6 項，逐項紅燈後還原複驗）

每一項都必須：改成錯的行為 → 確認指定測試**紅燈** → 還原 → 確認**綠燈**。
結果逐項寫進 `code-summary.md`，含實際的錯誤輸出。

| # | 突變 | 期望紅燈的測試 |
|---|---|---|
| 1 | 清除 SQL 移除 `kind = 'episodic'` | `verify_purge_sql.sql` 的 `R4` ＋ 契約測試第 2 條 |
| 2 | `RETURNING id` 改 `RETURNING *` | 契約測試第 1 條 |
| 3 | `K)` 區塊移除 `ON CONFLICT ... DO NOTHING` | 契約測試第 5 條 ＋ `memory-schema` 的「第二次套用」步驟 |
| 4 | CTE 拆成兩條獨立敘述並在中間 `COMMIT` | `tests_pg` 的 `test_terminated_before_commit_deletes_nothing` |
| 5 | 稽核清除的 `- interval '90 days'` 改 `+` | `verify_purge_sql.sql` 的 `R8`／`R9` |
| 6 | watchdog 的查詢移除 `status=success` | 契約測試第 8 條 |

### Step 12 — 文件與追溯

- [x] 12.1 `DEPLOY.md` 新 §2.2.11（**blocking**，`project.md ## Mandated`）：
  - 「這支 SQL 會建立的表／欄位」區加入系統 actor seed 一列
  - 既有環境的取得路徑是 `cd backend && python3 scripts/seed_retention_system_actor.py`
  - **明文更正**：**不要**為了取得這個 seed 而重跑整支 `schema_rbac.sql`——`:715` 的 `DELETE FROM role_permissions` 會清掉 Admin UI 調整過的權限矩陣（§1.2）
  - 驗證指令：`psql -c "SELECT id, username, role, is_active FROM users WHERE username = 'SYSTEM.retention-purge'"` 應回一列且 `is_active` 為 `f`
  - 兩個 workflow：排程要到檔案進入預設分支後才排入；首次啟用前先以 `workflow_dispatch` ＋ `dry_run=true` 驗證選取條件（`OPEN-ID9-4`）
- [x] 12.2 `source-manifest.json`：列出上表第 1–13 項的全部路徑
- [x] 12.3 `traceability.json`：八條 `NFR` ＋ 相關 `FR` 逐項對應到實際檔案
- [x] 12.4 `code-summary.md`：檔案清單、§1.1–§1.5 五項實測的處置結果、六項突變驗證的實際輸出、與上游不一致的兩格（§1.4 的 `password_hash`、§4.2 的步驟順序）
- [x] 12.5 收尾核對：`git diff --stat -- backend/database.py` 仍為空；`python3 scripts/validate_repo_contract.py` 與 `python3 scripts/validate_env_contract.py` 皆綠燈；`cd backend && python3 -m unittest discover -s tests` 全綠

## 四、追溯：計畫步驟 ↔ 需求

| 需求 | 承載步驟 |
|---|---|
| `NFR7.10`（兩個清除目標） | Step 4.2、4.3；驗於 `R1`／`R8` |
| `NFR7.11`（每列一筆稽核、actor 為系統 actor） | Step 2、4.2；驗於 `R5`／`R6`／`R7`／`S13` |
| `NFR7.12`（連線路徑、零新 secret、`db` 無 host port） | Step 8.1；驗於 §2.2 的三項二元判準 |
| `NFR7.13`（漏跑可偵測） | Step 9；驗於契約測試第 8 條 |
| `NFR7.14`（純 Actions，零 LLM） | Step 8.1（SQL 來自版控 `.sql`）、Step 9.2 |
| `NFR7.15`（清除稽核本身不留稽核） | Step 4.3（只 DELETE，無 INSERT）；驗於 `R8`／`R9` |
| `NFR6.10`（不得顯式覆寫身分） | Step 4.5、8.1；驗於契約測試第 3 條 |
| `NFR8.10`（零新部署設定） | Step 12.5 的 `validate_env_contract.py` ＋ diff 檢查 |
| `FR4.5`（90 天、**僅 episodic**） | Step 4.2；驗於 `R4`（§1.1 的陷阱列） |
| `FR4.5a`（Actions 承載、決定性邏輯放純步驟） | Step 8、9 |
| `FR4.7`（刪除留稽核） | Step 4.2 的 CTE 恆等性；驗於 `R5`／`R6` |
| `OPEN-ID9-4`（不可逆操作的前置驗證） | Step 4.6（強化後的 dry-run）、Step 12.1 |

## 五、不在本單元範圍（逐項附承接）

| id | 內容 | 承接 |
|---|---|---|
| `OPEN-CG9-1` | `NFR7.10` 的二元判準文字漏了 `kind = 'episodic'`（§1.1）。本計畫已收窄實作，但**上游文字仍是錯的** | 下一輪 `nfr-requirements` 修訂或 practices-discovery |
| `OPEN-CG9-2` | `verify_password` 應捕捉 `ValueError`（§1.4）。**既有**的潛在 500，非本單元引入 | 擁有 `auth.py` 的後續單元或 intent |
| `OPEN-ND9-1`（承接） | 系統 actor 列會出現在 Admin 使用者清單上（`/api/auth/list` 的 `total` 會 +1） | `U19`／既有端點，或後續 intent |
| `OPEN-ND9-2`（承接） | 是否為清除新增真正受限的資料庫角色 | 後續 intent |
| `OPEN-ID9-1`（承接） | 沒有人監看監看者（依賴面已最小化） | 已接受的殘留風險 |
| `OPEN-ID9-2`（承接） | `issues: write` 無先例；替代方案已寫明 | 關卡上的具名權限增量 |
| `OPEN-ID9-3`（承接） | 既有 SQLite 測試路徑看不到 seed——本計畫以 `memory-schema` 的 `S13` ＋ `verify_purge_sql.sql` **部分關閉**它 | 本單元部分處置，餘留 |
| `OPEN-CG5-1`（承接） | grant 邊界未被 CI 驗證 | 與 `OPEN-ND9-2` 同一個決定 |
| `tcms-test-cases` | **blocking，且至今未對本 intent 的任何單元執行過** | construction 階段，部署之前 |

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

上方的 `## Testing Contract` 區塊由
`bun .claude/tools/aidlc-testing-posture.ts render --unit memory-purge` 產生，
**未經任何編輯**。它對本單元的落實方式：

| 契約項 | 本計畫的落實 |
|---|---|
| `methodology: test-after` | 每一層先實作再寫並跑該層測試：Step 2 → Step 3、Step 4 → Step 5／6、Step 8-9 → Step 7 的第 8 條 |
| `runner_ready_before_first_test: true` | Step 1.2 在任何測試步驟之前記錄並驗證三個單元範圍指令 |
| `testable_layers` 的 `API / endpoint`、`Frontend behavior` | **對本單元不適用**：零端點、零前端面（`unit-of-work.md:123-129` 的交付物是 workflow）。依 stage 檔「omitting genuinely inapplicable layers」省略，方法論不變 |
| `testable_layers` 的 `Repository / data access` | 由 `Data model / database behavior` 吸收——清除沒有 ORM 層，它就是 SQL |
| `test_strategy: standard`（每元件 5–8 個測試 ＋ 關鍵邊界的整合測試） | 契約測試 8 條 ＋ `tests_pg` 3 條 ＋ `verify_purge_sql.sql` 的 `R1`–`R10` ＋ `S13`，共 **22** 條斷言分佈於三個載體 |
| `scope_floor`：既有測試須維持綠燈 | Step 12.5 逐項核對 |
| `project.md` 的 PBT hard constraint | **N/A（非豁免）**：本單元無任何自己擁有的純函式（承 `security-requirements.md §四` 與 `security-design.md §四` 的同一判定，兩站一致） |

### 覆蓋率門檻

`org.md` 宣告 80% line coverage。本 repo **沒有覆蓋率量測機制**
（`team.md` 逐字「既無法量測也無法強制，是宣告而非閘門」），且本單元交付的是
SQL 與 YAML——Python 覆蓋率工具量不到它們。
**本計畫不宣稱滿足該數字，也不弱化它**：改以上表 22 條二元可判的斷言作為
本單元的實際門檻，並如實記載這個落差。

## 八、ADR-0006 四面向：本計畫的落實

逐格對照 `nfr-design/security-design.md §四` 與
`infrastructure-design/infrastructure-specification.md §六`。
**本計畫不改任何一格的判定**，只列出它在程式碼層的落點。

| 面向 | 判定（與上游一致） | 本計畫的落點 |
|---|---|---|
| **IAM** | 適用；`NFR6.10` 不構成邊界（`[ND2]`=A），保留「不得顯式覆寫」 | Step 4.5（SQL 內無 `-U`）＋ Step 7 第 3 條（靜態斷言）。**新增的 IAM 面**是 watchdog 的 `issues: write`（`OPEN-ID9-2`，Step 9.1）。**本計畫另新增一列系統 actor**——它是一個 IAM 主體，故 §1.4 的四道鎖與 Step 7 第 7 條的可執行斷言都在這一格之內 |
| **Encryption** | 本單元無增量（承 `U5` 的 `NFR6.1`／`NFR6.2`） | 清除流量留在 compose 內部（Step 8.1 的 `exec -T`）；watchdog 只打 GitHub API（HTTPS）。系統 actor 的 `password_hash` 是**無已知前像**的 bcrypt hash，不構成新機密（§1.4） |
| **Network exposure** | 零增量 | `db` 不取得 host port、無新 tunnel、無新監聽埠；watchdog 是**出向**呼叫，不接受入向連線。驗於 §2.2 的二元判準 |
| **Audit logging** | 適用（核心之一） | `NFR7.11` 由 Step 4.2 的 CTE **結構性**保證（稽核列的來源是 DELETE 的 `RETURNING`，不是另一條會重新求值的敘述）；驗於 `R5`／`R6`／`R7`。`NFR7.15`（清除稽核本身不留稽核）由 Step 4.3 的「只 DELETE」保證 |

## 九、公開 repo 的輸出禁令（本單元最危險的一類錯誤）

本 repo 為 public，**Actions log 公開可讀**——`project.md` 逐字
「一次意外 echo 即等同公開發布」。而本單元處理的是**個人對話歷程**。

| 禁令 | 落點 | 驗證 |
|---|---|---|
| 清除 SQL 不得 `RETURNING *` | Step 4.4 | Step 7 第 1 條（靜態斷言） |
| dry-run 不得印 `content`／`embedding`／可識別資料 | Step 4.6 | Step 7 第 4 條 ＋ 人工核對輸出欄位清單 |
| seed 腳本不得印 `DATABASE_URL` 或其片段 | Step 2.6 | 沿用 `run_meta_schema_migration.py:55-59` 的既有禁令與形狀 |
| workflow 不得 echo 任何連線字串或密碼 | Step 8.1、9.1 | 人工核對；兩者都只用既有機制（compose 的 `--env-file`、內建 `GITHUB_TOKEN`） |

**這四條沒有一條會被現有 CI 抓到**（除了已轉成斷言的第 1、4 條）。
把前兩條變成靜態斷言正是本計畫 Step 7 存在的理由。

## 十、合併前必修第 11、17 項（code-generation Request Changes 修訂，2026-10-20）

**來源**：`construction/functional-design/merge-blockers.md` 第 11、17 項（皆劃給本單元）。使用者於 2026-10-20 裁決，兩題皆選建議項。

### Step 13 — 第 11 項：系統清除帳號由程式擋下並自列表隱藏（裁決：程式擋下＋列表隱藏）

**缺陷**：保留系統 actor `SYSTEM.retention-purge`（`schema_rbac.sql` 的 `K)` 區塊 seed，`is_active=FALSE`）在應用程式中沒有任何辨識：`DELETE /api/auth/{user_id}` 只要求對象已停用，故可直接刪除；`GET /api/auth/list` 會列出它。刪除後 `memory.memory_audit_events.actor_user_id` 的外鍵使清除的稽核 INSERT 全部失敗，而稽核與刪除同一交易，90 天清除整個停擺。（`hierarchy-data` 本輪的必修第 3 項修正已使「被 `memory_audit_events` 參照的使用者」刪除時回 409，但只在**首次清除之後**成立。）

- [x] 新增 `backend/services/system_accounts.py`：唯一常數 `RETENTION_SYSTEM_ACTOR_USERNAME = "SYSTEM.retention-purge"` 與判定函式 `is_reserved_system_account(user)`；`backend/scripts/seed_retention_system_actor.py` 的 `SENTINEL_USERNAME` 以測試鎖住與此常數相等（腳本不 import 應用模組的既有慣例保留）。
- [x] `backend/services/user_router.py`：`DELETE /{user_id}`、`PUT /{user_id}/role`、`PUT /{user_id}/active` 對保留帳號一律回 **409**（訊息說明是系統保留帳號、刪改會讓 90 天清除停擺）；拒絕授權申請並刪除的路徑若能命中它，同樣擋下。`responses=` 宣告 409。依 `team.md` 就地沿用既有形狀。
- [x] `GET /api/auth/list` 排除保留帳號（總數與分頁一致地排除，不只是過濾當頁）。
- [ ] 測試（`backend/tests/`，TestClient）：seed 一列保留帳號 → 刪除 409 且列仍在；改角色 409；啟用 409；列表不含它且 `total` 不計入；常數與 seed 腳本 `SENTINEL_USERNAME` 相等。突變：拿掉刪除的保留判定 → 刪除案例紅；拿掉列表排除 → 列表案例紅。
- [x] 重 dump `openapi.json`（`--check` 綠）、前端型別無漂移。

### Step 14 — 第 17 項：併入 `main` 前以手動觸發過渡（裁決：手動觸發過渡，寫進部署文件）

**缺陷**：GitHub 只執行預設分支 `main` 上的 `schedule`，故清除（`memory-retention-purge.yml`）與監看（`memory-retention-watchdog.yml`）在 `ut` 併入 `main` 之前都不會排程執行。兩支 workflow 皆已有 `workflow_dispatch`，清除的 `dry_run` 預設為 `true`。

- [ ] 不改程式與 workflow。`DEPLOY.md` 的 90 天清除小節新增「合併進 `ut` 之後、併入 `main` 之前」的程序：① 以 `workflow_dispatch`、`ref=ut`、`dry_run=true` 跑一次並核對預覽（即 `OPEN-ID9-4` 要求的第一次真實執行前的 dry-run 驗證）；② 確認無誤後 `dry_run=false` 實際清除；③ 之後每週手動觸發一次清除與一次監看，直到 `ut` 併入 `main`、排程接手；④ 併入 `main` 後確認排程首次執行成功即停止手動。寫明這段期間**沒有自動提醒**。
- [ ] `merge-blockers.md` 第 17 列處置改為「已處置為人工義務：合併 `main` 前每週手動觸發」，並標明這是**持續中的人工義務**而非已修正。

### Step 15 — 驗證與紀錄

- [x] 完整套件（`backend/.venv`）全綠；`validate_repo_contract.py`／`validate_env_contract.py` 綠。
- [x] `merge-blockers.md` 第 11、17 列回填處置；`code-summary.md` append 本節紀錄（改動檔:行、測試、突變結果）；`source-manifest.json`、`traceability.json`（加 `MB-11`／`MB-17`）更新。
- 追溯：`merge-blockers.md` #11／#17；`NFR7.11`、`FR4.5a`、`OPEN-ID9-4`。
