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
2. **`OPEN-M5`（已關閉，2026-10-20 更正）**：原記「既有非空 volume 的 schema 建立路徑未定」。
   該路徑已由 U18 的 `backend/scripts/run_meta_schema_migration.py` 作成
   （`BLOCKS_TO_RUN = ("X", "I", "J")` 含記憶區塊 `I`，見 `DEPLOY.md` 2.2.9）；
   `DEPLOY.md` 2.2.8 的對應段落已改為指向 2.2.9（本單元 code-generation review-01 的 Major）。
3. **`NFR6.1` 的主機加密狀態為空白待填**：`DEPLOY.md` 2.2.8 已留欄位並逐字寫明
   「留白不代表已加密」。本 repo 無法驗證它。
4. **`N-2` 尚未在真實 CI 上跑過**：本機以 PostgreSQL **14** 驗證，而 CI 與部署用 **18**。
   DDL 未使用任何 15+ 專屬語法，但**版本差異本身是未驗證的**——記為 `OPEN-CG5-2`。
5. **`tcms-test-cases` 未跑**（`project.md` 的 blocking stage，不在本站）。

## 重新查驗（code-generation Request Changes 後，conductor，`2026-10-20T22:56:56Z`）

**觸發**：使用者對整站送出 Request Changes（原文：「修正 functional-design/merge-blockers.md 列出的 19 項合併前必修，各在所屬單元修正並附測試；需人工裁決的項目（#7、#8 等）逐項問我。object-picker-ui 的 R-08、R-09 已修，重新審查即可。」）。19 項無一劃給本單元（計畫 §六，使用者已核可）。本輪**未改任何應用程式碼**；補寫先前缺漏的 `source-manifest.json`（依計畫 §二 四個檔，引擎登記審查前要求）。

| # | 判準 | 結果 |
|---|---|---|
| 1 | `N-2` 兩次套用皆成功 | **未勾**（審查查證：記憶區塊 `I)` 自 `a5200fc` 起位元組未變，風險來自其他單元的 DDL，屬低風險）：本機無 Docker daemon、`localhost:5432` 無回應，無法跑真實 PostgreSQL。CI 最近一次 `Memory schema (real PostgreSQL)` job（run `38117175745`，`a5200fc`，2026-10-11）為 success，但其後 `schema_rbac.sql` 已被 `6dff4d4`（U20）、`8677b7d`（U23）與本輪 `hierarchy-data` 的 COMMENT 修改，該結果不代表現況。下次推送後由 CI 判定 |
| 2 | `verify_memory_schema.sql` 全部斷言通過 | **未勾**，理由同上 |
| 3 | `validate_repo_contract.py` | passed |
| 4 | `validate_env_contract.py` | passed |
| 5 | 完整套件無迴歸 | 基線 497 已過時；以「全綠」判定：`backend/.venv` 執行 `discover -s tests`，`Ran 1223 tests` → `OK`（含本輪其他單元的修正） |
| 6 | `DEPLOY.md` 兩表、`psql` 驗證、主機加密 | §2.2.8（`:531` 起）含兩表與四條 `psql` 驗證指令；`:604` 起記載 `NFR6.1` 由主機層（磁碟／LUKS）承載 |
| 7 | 本單元變更不碰「不動的檔案」 | **未勾，無法驗證**：本單元檔案首次出現在 521 檔批次提交 `c2e5687`，提交歸屬不可得（同 `hierarchy-service` 的判定） |

## 重做（Code Generation 自頭重來，2026-10-25）

<!-- 寫入時間：2026-10-25T06:10:38Z（`date -u` 取值） -->

Code Generation 依使用者裁決自頭重來；本單元計畫重新核可後，逐項查驗既有產出，**程式碼與文件改動為 0**，計畫 §五 七格全部勾選。後續單元對同一批共用檔的改動一律保留。突變本輪未重跑，沿用 §三紀錄。

### 七項判準

| 項 | 依據 |
|---|---|
| 1 套用兩次皆成功 | **本機真實 PostgreSQL 實跑**：Docker daemon 未啟動，改用 Homebrew `postgresql@17` ＋ pgvector 0.8.1，在 scratchpad 以 `initdb` 建一次性叢集（`127.0.0.1:55439`、資料庫 `cloud360`），兩次套用 `schema_rbac.sql` 皆成功，之後 `memory_records` 9 欄、`memory_audit_events` 7 欄；跑完 `pg_ctl stop` 並刪除資料目錄，未碰任何共用或 staging 資料庫。CI 設定在 `ci.yml:322-381`（`pgvector/pgvector:pg18`，`:343`；兩次套用 `:359`、`:368`；驗證 `:376-381`）。CI 最近一次 pg18 綠燈（run 38117175745，2026-10-11）跑的是 `a5200fc`，比現行樹舊 |
| 2 驗證腳本全部通過 | 同一叢集實跑 `verify_memory_schema.sql`：S1、S3–S15 全部「通過」（S2 即判準 1 的兩次套用） |
| 3、4 兩支 validator | 皆 passed |
| 5 全套無迴歸 | `backend/.venv`：`Ran 1319 tests`、`OK (skipped=3)`（快取導向 scratchpad） |
| 6 `DEPLOY.md` | 兩張新表 `:540-542`、psql 驗證指令 `:569-588`、NFR6.1 主機加密 `:605-615`（「`192.168.10.10` 的目前狀態：未經本 repo 確認」，屬運維承諾、非閘門） |
| 7 不碰「不動的檔案」 | 依計畫 §六 的解讀（只看本單元自己的變更）以**寫入範圍**判定：manifest 的 4 個檔皆不在 §二 清單內。**注意**：這與上節「未勾、無法驗證」的判定不同——提交歸屬仍不可得（`c2e5687` 批次提交），本輪勾選的依據是寫入範圍，不是 commit diff；照字面跑 `git diff --stat` 會列出其他單元在工作樹中的修改 |

### 與已核可計畫／測試說明的落差（凍結文件不改，以本節為準）

- 斷言數：測試說明寫 S1–S12、計畫說 12 條；腳本現另有 S13（U9 系統 actor seed）、S14（U8 HNSW 索引與 opclass）、S15（U8 檢索查詢）。`ci.yml` 的步驟名仍寫「S1-S13」。
- `memory-schema` job 現另跑 U18 的 `verify_meta_schema.sql`（P1–P16）與 U20 的遷移步驟（`ci.yml:383` 起）。
- `schema_rbac.sql` I) 區塊（`:441-566`）另有 U8 的 `ix_memory_records_embedding_hnsw`（`:503-504`）與 `owner_user_id`、`expires_at`、`embedding_model` 三個索引；計畫 §二 只提 `occurredAt` 索引。
- 測試基線：計畫寫 497、上節寫 1223，現為 1319。
- 計畫 §一 的 OPEN-M5 已由 `DEPLOY.md:600-603` 改寫為 `run_meta_schema_migration.py` 承載（`BLOCKS_TO_RUN` 含 `"I"`）。
- **待確認**：本輪只在 PG17 實跑；下一次 push 後須確認 `memory-schema` job 在 pg18 上對現行樹仍綠。
- **仍未解**：OPEN-CG5-1——BR1.2 的 grant 邊界沒有任何 CI 斷言（`schema_rbac.sql:546-553` 如實記載）。

`source-manifest.json` 的 4 條路徑全部存在且仍屬本單元（`verify_memory_schema.sql` 共 576 行）。
