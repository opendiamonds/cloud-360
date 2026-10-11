# 單元測試指示 — `U9 memory-purge`

> 本單元交付 SQL 與 YAML，**零 Python 應用程式邏輯**。故測試分佈於**三個載體**，
> 而不是一個：既有的 `unittest` 套件（靜態契約）、真實 PostgreSQL 的 `psql` 斷言
> （行為）、以及 `tests_pg` 的雙連線測試（原子性）。
>
> **三者缺一都會留下一塊 CI 完全看不到的失敗面。**

## 一、框架與既有基礎設施（零新依賴）

| 載體 | 框架 | 由誰執行 | 本單元是否新建 |
|---|---|---|---|
| 靜態契約斷言 | Python 內建 `unittest`（**不是 pytest**） | `ci.yml` 的 `backend` job，`python -m unittest discover -s tests -v` | **沿用**，新增一個測試檔 |
| 行為斷言（真實 PostgreSQL） | `psql` ＋ `DO $$ ... RAISE EXCEPTION ... $$` | `ci.yml` 的 `memory-schema` job | **沿用** job，新增一個 `.sql` 檔與一個步驟 |
| 原子性（雙連線） | `unittest` ＋ SQLAlchemy／psycopg，真實 PostgreSQL | `ci.yml` 的 `concurrency` job，`python -m unittest discover -s tests_pg -v` | **沿用**（`U19` 交付），新增一個測試檔，**不需改 `ci.yml`** |

**零新依賴**：`backend/requirements.txt` 不變。
`hypothesis` 已在其中但本單元不用它（PBT 判定為 N/A，見計畫 §八）。

## 二、執行本單元的測試（三個指令，全部限定於本單元）

### 2.1 靜態契約斷言（不需資料庫）

```bash
cd backend && python3 -m unittest tests.test_retention_purge_contract -v
```

### 2.2 原子性測試（需真實 PostgreSQL）

```bash
cd backend && DATABASE_URL='postgresql+psycopg://postgres:postgres@localhost:5432/cloud360' \
  python3 -m unittest tests_pg.test_purge_atomicity -v
```

`DATABASE_URL` **缺值時必須大聲失敗**而非退回 SQLite——`tests_pg/__init__.py` 的
`require_pg_url`（`U19` 交付）已承載這一點。退回 SQLite 是本測試唯一不可接受的
失敗方式：SQLite 沒有 `pg_terminate_backend`，整個檔會變成一個綠燈的空殼。

### 2.3 行為斷言（需真實 PostgreSQL，且**須於 repo 根目錄執行**）

```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d cloud360 \
  -v ON_ERROR_STOP=1 -f backend/scripts/verify_purge_sql.sql
```

**工作目錄必須是 repo 根目錄**：該檔以 `\i backend/scripts/purge_expired_memory.sql`
引入清除 SQL 本體，而 `\i` 的相對路徑是相對於 `psql` 的工作目錄。
`ci.yml` 的 `memory-schema` job 沒有 `working-directory` 覆寫，故預設即為根目錄。

**前置條件**：`schema_rbac.sql` 已套用過（含新的 `K)` 區塊），否則
`memory` schema 與哨符列都不存在。

### 2.4 本單元的測試**不是**專案全域指令

上述三個指令分別限定於單一測試模組、單一測試套件目錄、單一 `.sql` 檔。
`python3 -m unittest discover -s tests` 這類全域形式**不得**寫進本檔
——Build and Test 會逐單元執行每個單元的指令，不限定的指令會讓整套測試跑 24 次。

## 三、測試清單（22 條斷言，分三個載體）

### 3.1 `backend/tests/test_retention_purge_contract.py`（8 條）

純文字斷言，讀取版控檔案內容後比對。**零資料庫、零網路。**

| # | 測試 | 斷言 | 突變驗證 |
|---|---|---|---|
| 1 | `test_purge_sql_never_returns_all_columns` | `purge_expired_memory.sql` 不含 `RETURNING *` | 突變 2 |
| 2 | `test_purge_sql_scopes_to_episodic` | 同檔含 `kind = 'episodic'` | 突變 1 |
| 3 | `test_purge_sql_does_not_override_connection_identity` | 同檔不含 ` -U ` | — |
| 4 | `test_dry_run_sql_is_read_only` | `purge_dry_run.sql` 不含 `DELETE`／`INSERT`／`UPDATE`（不分大小寫） | — |
| 5 | `test_system_actor_seed_is_rerunnable` | `schema_rbac.sql` 的 `K)` 區塊含 `ON CONFLICT (username) DO NOTHING` | 突變 3 |
| 6 | `test_sentinel_username_has_one_source` | 哨符字串在 `K)` 區塊、清除 SQL、seed 腳本常數三處**逐字相同** | — |
| 7 | `test_sentinel_hash_rejects_cleanly_without_raising` | `verify_password('any', <K) 區塊內的 hash>)` 回 `False` **且不拋例外** | — |
| 8 | `test_watchdog_filters_to_successful_runs` | watchdog workflow 含 `status=success` | 突變 6 |

**第 6 條的取值方式**：以 regex 從 `K)` 區塊與清除 SQL 內抓出單引號字串，
**不得**在測試檔內重新手寫哨符值——那會讓測試與被測內容變成同一個人的記憶
（`project.md` 逐字：「腳本必須從產出檔本身解析輸入，不得在腳本裡重新列舉」）。

**第 7 條是本檔最重要的一條**：它把計畫 §1.4 的「`bcrypt` 對非 bcrypt 格式的
hash 會拋 `ValueError`」從一句轉述變成一條可執行斷言。
`assertFalse` 不夠——必須同時確認**不拋例外**，因為拋例外正是那個 500 的成因。

### 3.2 `backend/tests_pg/test_purge_atomicity.py`（3 條）

真實 PostgreSQL，兩條獨立連線。沿用 `U19` 的 `tests_pg` 形狀。

| # | 測試 | 斷言 |
|---|---|---|
| 1 | `test_terminated_before_commit_deletes_nothing` | 連線 A 開交易跑清除 CTE 但**不 COMMIT**；連線 B 以 `pg_terminate_backend(<A 的 pid>)` 切斷；斷言記憶列數與稽核列數**完全不變** |
| 2 | `test_committed_purge_writes_one_audit_row_per_deleted_memory` | 正常 COMMIT；斷言刪除數 == 新稽核數 且 > 0 |
| 3 | `test_missing_system_actor_aborts_whole_transaction` | 暫時移除哨符列後跑 CTE；斷言**拋錯**且記憶列**一列都沒少** |

**第 1 條就是 `R-01` 的最壞情境**（`deploy.yml` 的
`up -d --build --remove-orphans` 重建 `db` 容器，連線在 COMMIT 之前斷掉）。
審查要求把「PostgreSQL 會回滾，不留部分寫入」這個結論**補上**——
本檔補的是可執行的證明而不是一段敘述。

**fixture 管理**：每個測試自建自清。`setUp` 以固定前綴的 `content` 建立 fixture
列，`tearDown` 依該前綴刪除。**不得**依賴資料庫的既有內容，也不得清空整張表
（`memory-schema` job 與本 job 是不同的 service container，但同一個 job 內多個
測試會共用一座資料庫）。

### 3.3 `backend/scripts/verify_purge_sql.sql`（`R1`–`R10`）＋ `verify_memory_schema.sql` 的 `S13`（共 11 條）

形狀沿用 `verify_memory_schema.sql` 既有的 `DO $$ BEGIN IF NOT ... THEN
RAISE EXCEPTION '...' END IF; END $$;` 樣板。`-v ON_ERROR_STOP=1` 使任一條
`RAISE EXCEPTION` 讓整個 `psql` 以非零碼結束。

**檔案結構（三段，順序不可換）**：

1. **fixture**：建立下表六類邊界列（含一個專用的 owner 使用者，以固定 username
   ＋ `ON CONFLICT DO NOTHING` 建立，與哨符列不同）
2. **`\i backend/scripts/purge_expired_memory.sql`** — 引入**生產用的那一份**
3. **斷言 `R1`–`R10`**

| fixture 類 | `kind` | 時間 | 期望 |
|---|---|---|---|
| a | `episodic` | `expires_at = now() - 1 day` | **被刪** ＋ 1 筆稽核 |
| b | `episodic` | `expires_at = now() + 1 day` | 保留 |
| c | **`semantic`** | `expires_at = now() - 1 day` | **保留**（計畫 §1.1 的陷阱列） |
| d | `procedure` | `expires_at IS NULL` | 保留 |
| e | 稽核列 | `occurred_at = now() - 91 days` | **被刪** |
| f | 稽核列 | `occurred_at = now() - 89 days` | 保留 |

| id | 斷言 |
|---|---|
| `R1` | fixture a 已不存在 |
| `R2` | fixture b 仍存在 |
| `R3` | fixture d 仍存在 |
| `R4` | **fixture c 仍存在** |
| `R5` | 新增 `purged_by_retention` 列數 == 被刪 episodic 列數 |
| `R6` | 每筆新稽核的 `memory_id` 都在被刪 id 集合內，無重複、無遺漏 |
| `R7` | 新稽核的 `actor_user_id` == 哨符列的 id，且 != fixture 的 `owner_user_id` |
| `R8` | fixture e 已不存在 |
| `R9` | fixture f 仍存在 |
| `R10` | 步驟一剛寫的稽核列**未被**交易二刪除 |
| `S13`（於 `verify_memory_schema.sql`） | 哨符列存在，且 `is_active = false`、`role` 非 canonical、`password_hash` 符合 `^\$2[aby]\$` |

**`R6` 是 `NFR7.11` 真正的斷言**。`R5` 只比對數量——數量相等但對應錯亂
（例如重複記同一個 `memory_id` 兩次、漏一個）仍會通過 `R5`。
`R6` 比對的是**集合相等**，而那是 `FR4.7`「刪除留稽核」在列層級的實際內容。

## 四、覆蓋率目標

| 項目 | 值 |
|---|---|
| `org.md` 宣告 | 80% line coverage |
| 本 repo 的量測機制 | **不存在**（`team.md` 逐字「既無法量測也無法強制，是宣告而非閘門」） |
| 本單元的交付物型態 | SQL ＋ YAML——**Python 覆蓋率工具量不到它們** |
| **本單元的實際門檻** | 上述 **22 條二元可判斷言全綠** ＋ 六項突變驗證各自確認紅燈後還原 |

**不弱化 `org.md` 的宣稱**，也不假裝滿足它：如實記載這個落差，
並以可量測的替代門檻取代。導入 `coverage.py` 屬 `team.md` 已記載的待補承載機制。

## 五、Mocking／stubbing 指引

| 情境 | 做法 |
|---|---|
| 靜態契約測試（3.1） | **不 mock 任何東西**。它讀版控檔案的真實內容——mock 掉檔案內容會讓這些斷言失去全部意義 |
| 第 7 條需要 `verify_password` | 直接 `from services.auth import verify_password`。**不 mock `bcrypt`**——要驗的正是 `bcrypt` 的真實行為 |
| `tests_pg`（3.2） | **不 mock 資料庫**。整個檔存在的理由就是 SQLite 與真實 PostgreSQL 在交易與 `pg_terminate_backend` 上的語意差異 |
| `backend/tests/helpers.py` 的 SQLite 路徑 | 3.1 **不需要**它（不碰資料庫）。若因 import 鏈需要，沿用既有 `helpers` 的 `psycopg2` mock 形狀，**不自創** |

**本單元沒有任何該被 mock 的外部依賴**：清除的唯一依賴是同一主機上的資料庫，
而 watchdog 的唯一依賴是 GitHub 自己的 API（它在 CI 中不被執行，只被靜態斷言檢查）。

## 六、測試資料管理

| 規則 | 理由 |
|---|---|
| fixture 的 `content` 一律帶固定前綴（如 `__u9_fixture__`） | 清理時依前綴刪除，不碰同一座資料庫上的其他資料 |
| 每個測試自建自清（`setUp`／`tearDown`） | `concurrency` job 內多個測試共用一座 service container |
| **不得**以 `TRUNCATE` 或無 WHERE 的 `DELETE` 清理 | 一個會清空整張表的清理動作，在本單元的語境下與被測的缺陷**長得一樣** |
| fixture 的時間戳一律相對於 `now()`，不寫死日期 | 寫死日期的測試會在某個未來日期無聲地改變語意 |
| fixture 的 owner 使用者以固定 username ＋ `ON CONFLICT DO NOTHING` 建立 | 可重跑；且**不得**重用哨符列當 owner——`R7` 正是要驗它們不同 |

## 七、不在本單元測試範圍（逐項附理由）

| 項目 | 為什麼不在這裡 |
|---|---|
| workflow 的端到端實跑 | 需要製造「runner 離線」與「連續 3 天未成功」的狀態，在 CI 中無法合成。`unit-of-work.md:127` 的驗證方式逐字是「workflow 實跑」——那屬 `tcms-test-cases` 的「只能手動」桶（`cicd-pipeline.md §六` 已預判分桶） |
| watchdog 真的開 issue | 同上；且在 CI 中執行它會在本 repo 開出測試 issue |
| grant 邊界（`NFR6.10`）的機械驗證 | 需要第二個資料庫角色，而 service container 只有 superuser（承 `OPEN-CG5-1`，本單元不改善） |
| 前端與端點 | 本單元零端點、零前端面 |
