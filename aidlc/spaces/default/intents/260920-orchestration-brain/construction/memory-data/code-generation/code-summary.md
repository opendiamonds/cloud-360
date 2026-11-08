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

> **時效註記（2026-10-30，review-02 R-06）**：`M1`–`M9` 對應的是本單元交付當時的
> `S1`–`S12`（當時 12 條）。之後他單元在 `backend/scripts/verify_memory_schema.sql`
> 新增的斷言**未重跑突變**。現行斷言 id 以 `grep -oE "\bS[0-9]+\b" … | sort -u -V`
> 實數為 14 個：`S1`、`S3`、`S4`、`S5`、`S6`、`S7`、`S8`、`S9`、`S10`、`S11`、`S12`、
> `S13`、`S14`、`S15`（`S2` 不存在，即兩次套用本身；檔案共 576 行）。
> `S1`–`S12` 的邏輯在交付後是否被他單元改動，本輪未逐段比對。

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

1. **`OPEN-CG5-1`（2026-10-30 依 review-02 R-03 改寫；ADR-0006 **IAM** 面向缺口）**：
   **`BR1.2` 的邊界目前未落地**：grant 只給 `current_user`、為空操作；無記憶專用角色、
   無對 `public` 的 REVOKE。（原文寫「沒有被任何自動化驗證」，把未實作描述成未驗證。）
   `schema_rbac.sql:548-566` 的 DO 區塊三條 `GRANT ... TO %I` 皆以 `current_user` 代入，
   即執行 DDL、本已擁有全部物件的角色。`DEPLOY.md` 2.2.8（`:534-536`「`BR1.2` 的 grant
   邊界整個作用方式就是『只開放 `memory` schema』」）與 `COMMENT ON SCHEMA memory`
   （`schema_rbac.sql:450-451`「the grant boundary (BR1.2) works by opening ONLY this schema」）
   的「邊界已生效」語氣與現況不符；**本輪因共用檔限制不改**（三檔皆在多個單元的審查收據內）。
   承接以 `construction/functional-design/merge-blockers.md` 第 29 列為準（建立記憶專用角色、
   REVOKE `public` 寫入、CI 以第二角色斷言越界被拒、同步修文件語氣），取代
   `traceability.json` 原寫的承接站 `U8 memory-service`。
   〔2026-11-06 加註，計畫 §八〕**邊界已由 `brain-infra` A1 落地（程式與文件層），真實 PostgreSQL 尚未驗證**：
   `schema_rbac.sql:594-596`（DO 區塊以 `pg_roles` 判斷、無密碼 `CREATE ROLE cloud360_memory LOGIN`）、
   `:600-606`（只授 `memory` 的 USAGE、表 DML、序列與 DEFAULT PRIVILEGES）、`:607-609`（撤銷 `public`
   的表、序列與 `CREATE`）、`:611`（`COMMENT ON ROLE`）；`ci.yml:389` 新步驟「Verify the memory-only role
   boundary (R0-R3)」以該角色本身連線跑 `backend/scripts/verify_memory_role.sql`；`DEPLOY.md:613` 起
   新增「記憶專用資料庫角色」小節並更正先前語氣。**驗證強度**：靜態測試 `test_memory_db_role`（7 個）綠；
   **真實 PostgreSQL 本輪未驗**（本機 Docker daemon 未啟動），且 A1 尚未 commit，**CI 亦尚未跑過**這段
   SQL 與 R0–R3。上面「原文」各行號是 2026-10-30 當時的定位，現已位移，不回改。
   部署前阻擋 `OPEN-MB20-SECRET` 見本檔末節。
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

## 共用檔異動後的重新驗證與補審（計畫 §七，2026-10-30）

<!-- 寫入時間：2026-10-30T00:30:11Z（`date -u` 取值） -->

本輪**零程式碼、零共用檔改動**；只寫入本目錄的 `code-summary.md`、`traceability.json`
與計畫的勾選。HEAD 為 `c6a40f91b80581173facc55a5285db9700146a9e`。

### 1. 重新驗證：`DEPLOY.md` 的變動未觸及 2.2.8

- 收據 `reviewed-source-a58ef1bdc213.tsv`（2026-10-25）與現況以 `shasum -a 256` 比對：
  `.github/workflows/ci.yml`（`a854442a…`）、`backend/scripts/verify_memory_schema.sql`
  （`2905225a…`）、`schema_rbac.sql`（`27e92ecd…`）**逐位元相同**；`source-manifest.json`
  亦與收據的 manifest 雜湊 `2875c74f…` 相同。唯一不同的是 `DEPLOY.md`：收據 `2608a131…`、
  現況 `d9b0571c…`（＝`git show 7a50a40:DEPLOY.md`，工作樹無未提交改動）。
- 逐 hunk 回退：以 `git show 624c170:DEPLOY.md` 為基底，`difflib` 對現況得 19 個非相等區段；
  **只把現行第 730–738 行（#24）與第 2229、2239 行（#26）三段換回 `624c170` 版本**，
  得到的雜湊恰為收據的 `2608a131203c6bff1af9e0bddd945b3eb1790be32bf5552cb2d21f7808455ba0`。
  故收據之後的變動**只有這三段**（腳本在 scratchpad，未寫入工作樹）。
- 落點：2.2.8 為現行第 531–616 行（`grep -n '^#### 2.2.'`）；730–738 落在 2.2.9
  （617–950，U18／U20 的「誠實的代價」段），2229／2239 落在 5.13（2223 起，U14 步驟 6a）。
  **三段皆不在 2.2.8，本單元的記憶層段落未被觸及。**

### 2. 判準 1、2 的依據：CI `memory-schema` job（pg18）

- **指定的 run `40423381616` 不是 CI**：`gh run view` 實查其 `workflowName` 為
  「UI Regression Reporter」（`.github/workflows/ui-regression.lock.yml`），結論 failure，
  建立於 `2026-10-26T23:58:57Z`（不是 2026-10-29），**沒有 `memory-schema` job**。
- 同一 head SHA（`c6a40f9`，即現行 HEAD）的 CI 有兩次（`gh run list --commit`，只讀）：
  push run `40423375585`（整體 success）與 pull_request run `40423381647`（整體 failure）。
  兩者的「Memory schema (real PostgreSQL)」job 皆 **success**（job `121923028241`、
  `121923078557`）。前者逐步查證：「Apply schema_rbac.sql」、「Re-apply schema_rbac.sql
  (BR1.3 idempotency)」、「Verify memory schema assertions (S1-S13)」皆 success。
- `git log c6a40f9..HEAD -- schema_rbac.sql backend/scripts/verify_memory_schema.sql .github/workflows/ci.yml`
  無輸出，`git diff --stat c6a40f9` 對三檔亦無輸出：**其後未再變動**。
- 判定：以 **run `40423375585` 的 `memory-schema` job（pg18、現行樹）**作為判準 1、2 的依據並勾選。
  **與計畫字面的差異**：計畫指名的 run id 指向另一個 workflow，此處以同 SHA 的 CI run 代替；
  若 conductor 認為必須以指名的 run 為準，判準 1、2 應退回未勾。
- 附帶觀察（非本單元）：PR run `40423381647` 的「Backend (import + unit tests)」紅燈為
  `FAIL: test_a1_allowed_role_reaches_request_sent_and_completes
  (test_work_orchestrator_authz.RealAppAuthorizationTest)`（`Ran 1326`、`failures=1`）；
  同 SHA 的 push run 該 job 綠、本機亦綠，形狀像不穩定測試。

### 3. 回歸

整樹 `rsync` 至 scratchpad 新子目錄（排除 `.venv`、`.git`、`node_modules`、快取），以工作樹的
`backend/.venv/bin/python -B`、`PYTHONDONTWRITEBYTECODE=1`、`HYPOTHESIS_STORAGE_DIRECTORY`
指向副本內執行 `-m unittest discover -s tests`：**`Ran 1326 tests` → `OK (skipped=3)`**。
副本已刪除；`find … -newer <marker>` 對工作樹的 `*.pyc` 與 `.hypothesis/` 無輸出。

### 4. R-03、R-06：見 §六 第 1 項與 §三 的時效註記

- `OPEN-CG5-1` 已改寫為「邊界未落地」並標明 ADR-0006 **IAM** 面向；承接 `merge-blockers.md`
  第 29 列。`traceability.json` 同步：`BR1.2` 由 `OK` 改為 `Deferred`（不用 `GAP`，因
  traceability sensor 對 `GAP` 直接 fail，而此項已有指名承接列）、`AC4.1.2` 註記更正、
  `OPEN-CG5-1` 改寫；另把 `OPEN-M5` 標為 `resolved`（與 §六 第 2 項 2026-10-20 的更正對齊，
  原 `traceability.json` 未同步）。

### 5. R-07：`ci.yml` 步驟名與腳本實際斷言不一致

- `ci.yml:376` 步驟名為「Verify memory schema assertions (S1-S13)」；腳本實際斷言 id
  （`grep -oE "\bS[0-9]+\b" | sort -u -V`）為 `S1`、`S3`–`S15` 共 14 個——含 `S14`、`S15`，
  且無 `S2`。**落點**：下一個動到 `ci.yml` 的工作（建議改為不寫死範圍）；本輪不改（共用檔）。

### 6. 勾選重設的核對

計畫 §五 七格在本輪開工時全為未勾（重開所致），逐項依現況核對後**全部勾回**：
1、2 依上第 2 點（CI run `40423375585`）；3 `validate_repo_contract.py` passed；
4 `validate_env_contract.py` passed；5 上第 3 點（1326、OK）；6 `DEPLOY.md` 2.2.8 兩表
`:541-542`、`psql` 驗證 `:570-588`、`NFR6.1` 主機加密 `:605-615`；7 依 §五 下方註記以寫入範圍
判定（manifest 4 檔不在「不動的檔案」清單；強度弱於其他格，未經 commit diff 驗證）。
寫入本節時以 `grep -c '^- \[x\]'` 實算計畫為 **13 勾**、`grep -c '^- \[ \]'` 為 **2 未勾**
（§七 的「勾選重設」與「收尾」兩項，於本節寫入後依序勾選）；最終數見末行處置紀錄。

處置紀錄（`2026-10-30T00:31:06Z`）：§七 八項完成；`validate_repo_contract.py` passed、`traceability.json` 經 `python3 -I` `json.load` 通過；寫入本行前計畫實算 14 勾／1 未勾（未勾者為「收尾」本身，緊接本行之後勾選）；勾後 `grep -c` 實算 **15 勾／0 未勾**（§五 7 ＋ §七 8）；未改任何程式碼與共用檔，未 commit。

## 2026-11-01 回歸（第 20／29 列落地後）

<!-- 寫入時間：2026-11-06T14:24:26Z（`date -u` 取值）。節名沿用計畫 §八 指定的日期（Request Changes 日），實際執行日為 2026-11-06。 -->

本輪**零程式碼、零共用檔改動**；只寫入本目錄的 `code-summary.md`、`traceability.json` 與計畫的勾選字元。
HEAD 為 `c6a40f91b80581173facc55a5285db9700146a9e`；brain-infra A1 的修改**全部在工作樹、尚未 commit**。

### 1. hunk 歸屬（基準：最新收據 `reviewed-source-1bf5dea07508.tsv`）

收據的四個雜湊與 `git show HEAD:<檔>` 逐位元相同，故「收據之後的變動」＝`git diff -U0 HEAD`。
`source-manifest.json` 雜湊 `2875c74f…` 與收據 manifest 列相同。

| 檔 | 收據 → 現況 | hunk 數 | 歸屬 |
|---|---|---|---|
| `backend/scripts/verify_memory_schema.sql` | `2905225a…` → `2905225a…` | 0 | **逐位元相同** |
| `schema_rbac.sql` | `27e92ecd…` → `7d9bb5d3…` | 4 | 檔頭 `I)` 涵蓋列與兩條驗證查詢（`:19-23`）、BR1.2 說明改寫（`:554-576`）、角色 DO 區塊＋GRANT／REVOKE＋`COMMENT ON ROLE`（`:593-612`）→ **brain-infra A1**；`project_members` 前的純註解（第 31 列 (c)(g)）→ 其他單元。**本單元 0** |
| `.github/workflows/ci.yml` | `a854442a…` → `3a9ec220…` | 7 | 新步驟「Verify the memory-only role boundary (R0-R3)」（`:383-402`）→ **brain-infra A1**；`P1-P16`→`P1-P17` 的註解與步驟名（多處）→ 第 30 列；`tests_pg` 步驟改名 → 第 33 列 (g)。**本單元 0** |
| `DEPLOY.md` | `d9b0571c…` → `8bb9f107…` | 14 | §2.2 表 `I` 列（`:250`）、2.2.8 的 `:543` 語氣更正、新小節「記憶專用資料庫角色」（`:613-663`）→ **brain-infra A1**；2.2.9 終檢句（原 `:708`）為混合：角色三項 → A1，「3→7 條外鍵、逐欄核對」→ 其他單元（該 hunk 未標列號）；其餘 10 個 hunk → 第 21／27／28／30／31／32／34／36／37 列（皆有列號註記）。2.2.8（`:539-675`）內只有 A1 的兩處。**本單元 0** |

### 2. 第 20 列 (a)(b)(c) 對本單元規則的符合性

| 規則 | 判定 | 依據 |
|---|---|---|
| `BR1.1` schema 名 | 符合 | 角色只授 `memory`（`schema_rbac.sql:600-606`）；兩表仍在 `memory.`，未動 |
| `BR1.2` 只授 `memory`、撤銷 `public` | 符合（靜態） | `:600-606` 只涉 `memory` 的 USAGE、兩表 DML、序列 USAGE/SELECT 與同範圍 DEFAULT PRIVILEGES；`:607-609` 撤銷 `public` 的表、序列與 `CREATE`。**解讀一處**：規則 logic 的「跨 schema 讀取 `public.users` 所需的最小權限單獨授予」——A1 未授任何 `public.users` 權限，理由是外鍵參照檢查以被參照表擁有者的權限執行（`:569-571` 註解）。若此成立，「所需的最小權限」即為零，與規則一致；此點只能由 `verify_memory_role.sql` 的 R2（以該角色寫入帶 `owner_user_id` 外鍵的列）在真實 PostgreSQL 上證實，**本輪未證實** |
| `BR1.3` 可重跑 | 符合（靜態） | DO 區塊以 `pg_roles` 判斷（`:594`）；GRANT／REVOKE／ALTER DEFAULT PRIVILEGES 冪等；全段無 psql 變數與 meta-command（`test_memory_db_role` 案例 1 靜態斷言）。兩次套用的實跑**本輪未做** |
| 既有斷言不衝突 | 符合（靜態） | `verify_memory_schema.sql` 位元組未變；`grep -n 'cloud360_memory\|current_user\|GRANT\|privilege'` 只命中 `:45` 的 S1 訊息字串，無任何對 grant 對象的斷言，新角色不會使既有斷言改判 |
| 文件語氣 (c) | 符合 | `COMMENT ON SCHEMA memory`（`:455-456`）描述機制（"works by opening ONLY this schema"），未寫「僅授 `current_user` 即已生效」；`DEPLOY.md:543` 已指向角色，`:615-617` 逐字更正先前寫法（「在此之前……邊界並不存在」）；`schema_rbac.sql:555-557` 寫明 `current_user` 那段「不構成邊界」 |

**ADR-0006 四面向**：IAM——本項即 IAM 缺口的處置，落地於程式，真實 PostgreSQL 未驗；encryption——未改（`NFR6.1` 仍由主機層承載）；network exposure——無新增連接埠或服務；audit logging——無變更。

**未發現 A1 違反本單元規則**，故未停下。

### 3. 驗證結果與強度

| 項 | 結果 | 強度 |
|---|---|---|
| 真實 PostgreSQL（兩次套用、密碼 script、`verify_memory_schema.sql`、以 `cloud360_memory` 跑 `verify_memory_role.sql`） | **本輪未驗** | `docker info`：`Cannot connect to the Docker daemon`（`desktop-linux`、`default`、`rancher-desktop` 三個 context 皆同）。未啟動任何 daemon、未連任何共用 DB。**CI 亦未跑過**：A1 尚未 commit，最近的 CI（push run `40423375585`、PR run `40423381647`，皆 `c6a40f9`）的 `memory-schema` job 雖為 success，跑的是 A1 之前的 `schema_rbac.sql`，且沒有 R0–R3 步驟 |
| `test_memory_db_role` | `Ran 7 tests` → `OK` | 實跑（scratchpad 副本），靜態形狀斷言 |
| 後端全套 | `Ran 1372 tests` → `OK (skipped=3)` | 實跑（scratchpad 副本，`backend/.venv/bin/python -B`、`PYTHONDONTWRITEBYTECODE=1`、`HYPOTHESIS_STORAGE_DIRECTORY` 指向 scratchpad） |
| `validate_repo_contract.py`／`validate_env_contract.py` | 皆 passed | 實跑，**在 repo 本體**以 `python3 -B` 執行（前者依賴 `git ls-files`，副本排除 `.git` 故不能在副本跑） |
| repo 內 `.pyc`／`__pycache__`／`.hypothesis` | 前後 `stat`（路徑、大小、mtime）清單 9628 列，`cmp` 相同，清單雜湊皆 `30f4f7df…` | 實測 |
| 副本清理 | `dev-u5`、`dev-u5-hyp` 已刪，`ls` 確認不存在 | 實測 |

### 4. 計畫勾選

本輪開工時 `grep -c '^\s*- \[x\]'` 為 **0**、`- [ ]` 為 **21**（§五 7＋§七 8＋§八 6，重開單元時全部重設）。逐項依現況核對：

- §五：3、4、5、6、7 勾回（6 依據：`DEPLOY.md` 2.2.8 兩表 `:549-550`、`psql` 驗證 `:578-595`、`NFR6.1` `:664`；7 依 §五 下方註記以寫入範圍判定——A1 動到的 `backend/database.py`、`deploy/`、`.env.example`、`backend/tests/` 雖在「不動的檔案」清單內，但屬 brain-infra 的變更，本單元 manifest 四檔未擴張）。**1、2 未勾**：現行 `schema_rbac.sql` 已被 A1 改動且未在任何真實 PostgreSQL（本機或 CI）上套用過；上一輪依據的 CI run `40423375585` 只代表 A1 之前的樹。
- §七：八格皆為已完成的紀錄類交付，產出仍在本檔（第 177 行起「共用檔異動後的重新驗證與補審」一節、`OPEN-CG5-1` 改寫、R-06 時效註記 `:48`、R-07 落點 `:234` 起），全部勾回。其中「判準 1、2 的依據」一格記的是當時（HEAD `c6a40f9`）的依據，對現況已不成立，現況以上一點為準。
- §八：hunk 歸屬、符合性、回歸、紀錄更新四格勾選；**「真實 PostgreSQL 驗證」未勾**：該格的備援寫法是「本輪未驗、只在 CI」，但 A1 未 commit，連 CI 也還沒跑過，勾選會讓人以為至少有一處真實驗證。

寫入本節時實算 **17 勾／4 未勾**（未勾：§五 1、2；§八 真實 PostgreSQL、收尾）；「收尾」於本節寫入後勾選，最終數見下方處置紀錄。

### 5. 偏離與待處置

- **`OPEN-MB20-SECRET`（部署前阻擋，照錄）**：`MEMORY_DB_PASSWORD` 在 secrets 與 variables 皆不存在（brain-infra A1 於 `2026-10-31T23:19:56Z` 以 `gh api` 只列名稱查證；本輪未重查）。已新增至 `traceability.json` 的 `open_items`。**未解決。**
- `traceability.json` 的 `BR1.2` status **刻意維持 `Deferred`**，只在 note 加註落地位置與驗證強度；`OPEN-CG5-1` 保持開啟——兩者都等 R0–R3 在真實 PostgreSQL 綠燈才改。
- 真實 PostgreSQL 驗證未做，判準 1、2 隨之未勾；下一次 push 後的 CI `memory-schema` job（含 R0–R3）是第一次真實驗證，該 job 紅燈時優先查 `BR1.2` 一列所述的外鍵權限解讀。
- 兩支 validator 在 repo 本體跑而非副本（理由見上表）。
- 節名日期依計畫寫「2026-11-01」，實際執行為 2026-11-06（見節首註解）。
- 本輪未 commit、未觸發任何 workflow；`gh` 只做 `run list`／`run view` 唯讀查詢。

處置紀錄（`2026-11-06T14:33:26Z`）：計畫 §八 完成 5／6 格；勾選「收尾」後 `grep -c` 實算 **18 勾／3 未勾**（未勾：§五 判準 1、2；§八 真實 PostgreSQL 驗證——皆因 A1 之後的 `schema_rbac.sql` 尚未在任何真實 PostgreSQL 上套用）；`traceability.json` 經 `python3 -I` 的 `json.load` 通過；未改任何程式碼與共用檔，未 commit。
