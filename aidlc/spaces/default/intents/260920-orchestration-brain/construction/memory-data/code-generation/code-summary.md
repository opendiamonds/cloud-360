# 實作摘要 — `U5 memory-data`

## 〇、上游依據（逐一指名，含檔名）

| 上游產出 | 本站用到它的什麼 |
|---|---|
| `rules.md`（本單元 functional-design） | 13 條規則 `BR1.1`–`BR4.3`，逐條對應 DDL、CHECK、索引、COMMENT 與斷言（見 `traceability.json` 的 `coverage`） |
| `entities.md`（本單元） | 兩個實體的欄位集合與邏輯型別——`memory_records` 的 9 欄由斷言 `S4` 鎖住 |
| `functional-spec.md`（本單元） | §一 的 `DG-1` 處置與其兩項代價、§二 的 `embeddingModel` 靜默失敗模式、§五 的 blocking 同步義務 |
| `security-design.md`（本單元 nfr-design） | 清除查詢的形狀（不 join）、**`occurred_at` 索引**（本單元實作它）、兩個清除目標與順序、三項「讓加密決定不被誤讀」的設計 |
| `security-requirements.md`（本單元 nfr-requirements） | `NFR6.1`／`NFR6.2`／`NFR7.2` 三項定案 |
| `tech-stack-decisions.md`（本單元） | pgvector 為唯一新技術層；`N-2` 是交付物而非既有能力；`OPEN-N5-3`（本站關閉） |
| `performance-design.md`（本單元 nfr-design） | 判定「無新延遲預算」——故本單元的索引只為清除作業的可行性而建，**不是**為了達成某個效能目標 |
| `infrastructure-specification.md` | 不存在：`infrastructure-design` 對本 `spec` 單元被判不適用並由引擎 skip，故 `OPEN-N5-3`／`OPEN-ND5-2` 的轉移目標落到本站（與 `nfr-design` 當時寫下的轉移目標一致） |
| `contract-summary.md` | 契約 `K-05` 的 `schema_isolation`／`invariants`／`known_gap`（`DG-1`）／`retry_and_idempotency`／`verification`；契約 `K-01` 對 `OLLAMA_EMBED_MODEL` 的 1024 維 validation |
| `unit-of-work.md` | `:91` 的交付清單（schema ＋ grant ＋ `vector(1024)` ＋ `embeddingModel`）；`:218` 的「獨立 schema 零前例」風險；`:715` 的 `N-2` 定義 |

## 一、交付內容（四個檔案，與計畫完全一致）

| # | 檔案 | 動作 | 內容 |
|---|---|---|---|
| 1 | `schema_rbac.sql` | 改（新增 `I)` 區塊，+109 行） | `CREATE SCHEMA IF NOT EXISTS memory`；兩張表；**四條 CHECK**；**五個索引**（含 `occurred_at`）；grant（`DO` 區塊，不假設角色名）；**八段 COMMENT** |
| 2 | `backend/scripts/verify_memory_schema.sql` | 新 | 12 條斷言（`S1`–`S12`），純 SQL，不經 Python |
| 3 | `.github/workflows/ci.yml` | 改（新增 `memory-schema` job） | 交付物 **`N-2`**：`pgvector/pgvector:pg18` service container，套用 schema **兩次**後執行斷言 |
| 4 | `DEPLOY.md` | 改 | 2.2 表新增 `I` 列；新增 **2.2.8** 節（三件易誤讀的事、四條 `psql` 驗證指令、`NFR6.1` 主機加密狀態欄位） |

**未動**：`backend/models.py`（不建 ORM model，見 §三）、`backend/services/` 全部、
`backend/tests/` 全部、`deploy/` 全部、任一 `.env.example`、`render-env.sh`、
`schema.sql`、`openapi.json`。

## 二、實際跑過的驗證（**在真實 PostgreSQL 上跑的，不是推論**）

本機有執行中的 PostgreSQL 14 ＋ Homebrew `pgvector`，故**沒有等 CI**，
直接在 scratch database 上實測：

| 驗證 | 指令／方式 | 結果 |
|---|---|---|
| 第一次套用記憶區塊 | `psql -v ON_ERROR_STOP=1 -f`（含最小 `public.users` 與 `CREATE EXTENSION vector`） | **成功** |
| **第二次**套用（`BR1.3` 可重跑） | 同上，再跑一次 | **成功**，只有 `already exists, skipping` 的 NOTICE |
| 12 條斷言 | `psql -f backend/scripts/verify_memory_schema.sql` | **全部通過**（結構類 `S1`／`S3`／`S4`／`S5`／`S8`／`S9`／`S12` ＋ 行為類 `S6`／`S7`／`S10`／`S11`） |
| 全套 Python 測試 | `cd backend && python3 -m unittest discover -s tests` | **Ran 497 tests — OK**（與基線相同；本單元不新增 Python 測試，故**應**維持 497） |
| repo contract | `python3 scripts/validate_repo_contract.py` | passed |
| env contract | `python3 scripts/validate_env_contract.py` | passed |
| `ci.yml` 可解析 | `yaml.safe_load` | 6 個 job（新增 `memory-schema`） |

## 三、突變驗證：9 項全部 RED，零存活

| # | 突變 | 應紅 | 結果 |
|---|---|---|---|
| `M1` | 兩表建在 `public` 而非 `memory` | `S1` | **RED ✓**（見下方說明） |
| `M2` | `vector(1024)` → `vector(768)` | `S3` | **RED ✓** |
| `M3` | `embedding_model` 改為可空 | `S5` | **RED ✓** |
| `M4` | 移除 `kind` 的 CHECK | `S6` | **RED ✓** |
| `M5` | 移除「`episodic` 則 `expires_at` 必填」的 CHECK | `S7` | **RED ✓** |
| `M6` | 為 `memory_id` 加上 `ON DELETE CASCADE` 外鍵 | `S8` | **RED ✓** |
| `M7` | 稽核表加一個 `content` 欄位 | `S9` | **RED ✓** |
| `M8` | 移除 `occurred_at` 索引 | `S12` | **RED ✓** |
| `M9` | `CREATE TABLE IF NOT EXISTS` → `CREATE TABLE` | 第二次套用 | **RED ✓**（對照組兩次皆 `rc=0`；突變組第一次 `rc=0`、**第二次 `rc=3`**） |

### `M1` 第一次是假陰性，而原因正是我寫在測試指示裡的那一條

第一版 `M1` 我加了 `SET search_path TO public;`，結果 **GREEN**。
但 DDL 用的是**明確的 `memory.` 前綴**（`CREATE TABLE IF NOT EXISTS
memory.memory_records`），`search_path` 對它完全無效——**突變本身是 no-op**，
不是「斷言沒抓到」。

改成把 `memory.` 前綴整批替換為 `public.` 之後：**RED**，且行為探測確認
兩張表真的落在 `public`（`public.memory_audit_events, public.memory_records`）。

這正是 `unit-test-instructions.md` §三 逐字要求的「每一項突變都要先確認
DDL 真的改變了」——而我自己第一次就踩了它。

## 四、`OPEN-N5-3` 已關閉（查證結果與上游的擔憂相反）

上游擔心標準 `postgres:*-alpine` 不含 pgvector。實查：

- `deploy/docker-compose.deploy.yml:40` 與 `docker-compose.test.yml:51`
  **皆為 `pgvector/pgvector:pg18`**；
- 該檔 `:36-39` 的註解逐字「PG 18 + pgvector. The `vector` type must exist
  before any table declaring a `vector(1024)` column is created」；
- `schema_rbac.sql:45` **已有** `CREATE EXTENSION IF NOT EXISTS vector;`
  且位於 `BEGIN;` 之後第一條（`X)` 區塊）。

故**不需換 image、不需改任何部署設定、也不需在本區塊再建擴充**。
`U1 brain-infra` 與 `U4` 已把這條路鋪好。
**本站刻意不猜是對的**——若當初猜「不含」而去改 image，會是一次無謂的部署層變更。

## 五、`project.md` 的 blocking 同步已完成

| 必做 | 狀態 |
|---|---|
| `schema_rbac.sql` 寫入可重跑 DDL ＋ COMMENT ＋ 更新區塊清單 | **完成**（`I)` 區塊，八段 COMMENT 寫明每個刻意決定的理由與其失敗模式） |
| `DEPLOY.md` 更新表清單 ＋ `psql` 驗證指令 | **完成**（2.2 表的 `I` 列 ＋ 2.2.8 節） |

## 六、未完成／待處置

1. **`OPEN-CG5-1`（已知且已揭露）**：**`BR1.2` 的 grant 邊界沒有被任何自動化驗證。**
   驗它需要第二個資料庫角色並以該角色嘗試越界，而 `N-2` 的 service container
   只有 superuser。**這是資料庫層的唯一邊界**，且使用者已在計畫核可時知悉。
2. **`OPEN-M5`（承接，仍開啟）**：既有非空 volume 的 schema 建立路徑未定。
   `schema_rbac.sql` 只在空 volume 執行，而 `192.168.10.10` 是既有環境。
   已寫進 `DEPLOY.md` 2.2.8 作為部署前必須決定的事項。
3. **`NFR6.1` 的主機加密狀態為空白待填**：`DEPLOY.md` 2.2.8 已留欄位並逐字寫明
   「留白不代表已加密」。本 repo 無法驗證它。
4. **`N-2` 尚未在真實 CI 上跑過**：本機以 PostgreSQL **14** 驗證，而 CI 與部署用 **18**。
   DDL 未使用任何 15+ 專屬語法，但**版本差異本身是未驗證的**——記為 `OPEN-CG5-2`。
5. **`tcms-test-cases` 未跑**（`project.md` 的 blocking stage，不在本站）。
