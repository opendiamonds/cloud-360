# 實作摘要 — `U18 project-meta-data`

## 〇、上游依據（逐一指名，含檔名）

| 上游產出 | 本站用到它的什麼 |
|---|---|
| `code-generation-plan.md`（本單元） | 八個步驟、§三 的逐欄 DDL 形狀、§四 的三個決定、§五 的三處待揭露缺口；內嵌的 `## Testing Contract`（`test-after`／`standard`／`brownfield`）為方法論的唯一權威 |
| `unit-test-instructions.md`（本單元） | 12 條斷言 `P1`–`P12`、確切執行指令、10 項突變 `N1`–`N10`、以及**刻意不寫**的五類斷言與其理由 |
| `security-design.md`（本單元 nfr-design） | §一 `[ND1]`=A 的四條外鍵處置與 `CASCADE` 的既有程式理由、§二 獨立腳本的形狀（單一交易／自我終檢／輸出禁令）、§三 九個缺漏欄位與 `OPEN-ND18-1`–`3`、§四 索引設計（partial index ＋ 刻意不建的那一個） |
| `security-requirements.md`（本單元 nfr-requirements） | `NFR8.2`–`NFR8.5` 四項二元判準；選 A 而非 B／C 的三項理由；`OPEN-P5` 的誠實代價 |
| `tech-stack-decisions.md`（本單元） | 零技術增量；**不建 ORM model** 的兩項理由（避免重演 `U7` 的建表權威問題）；驗證載體沿用 `U5` 的 job 形狀 |
| `rules.md`（本單元 functional-design） | 11 條規則 `BR1.1`–`BR3.3`，逐條對應 DDL／CHECK／索引／COMMENT／斷言（見 `traceability.json` 的 `coverage`） |
| `entities.md`（本單元） | 三個實體與 `entity_constraints`。**本站未依它建表**——它少九個欄位，見 §四之一 |
| `functional-spec.md`（本單元） | §二 三態模型、§三 對 `backend/database.py` 的實讀結果、§五 兩次 blocking 同步不可互相替代 |
| `contract-summary.md` | `K-15` 全文（`tables`／`foreign_keys`／`columns_that_carry_semantics`／`ddl_comment_requirement`／`blocking_sync`／`behaviour_semantics`）；`K-16`／`K-17` 的 facade 簽章（據以推導查詢形狀與索引） |
| `components.md` | **`:819`／`:820` 的 Entity Ownership 表是本站欄位集合的權威來源**；`:886` 的三問結果（改選事件列永不刪除、讀取端為橫幅與成員詳情） |
| `requirements.md` | `FR12.4b`（`:307`，稽核五事實）、`:620` 的 ADR-0006 四面向表 |
| `stories.md` | `AC12.2.2`（`:777`），其 Then 的四件事對應四個被回補的欄位 |
| `schema_rbac.sql` | `H)` 區塊（`U4`）與 `I)` 區塊（`U5`）的既有形狀，逐項沿用 |
| `backend/scripts/run_hierarchy_migration.py` | 遷移腳本的形狀：`main()` 回 int、`sys.exit(main(...))`、失敗時 `traceback.print_exc(file=sys.stderr)`、宣告成功前先驗自己的後條件 |
| `backend/scripts/verify_memory_schema.sql` | SQL 斷言的形狀：結構類一個 `DO $$`、行為類一個交易並以 `ROLLBACK` 收尾 |
| `.github/workflows/ci.yml` | 既有 `memory-schema` job（`:308` 起）：service container、套用兩次、執行斷言 |

## 一、交付內容（五個檔案，與計畫一致）

| # | 檔案 | 動作 | 本站的行數 | 內容 |
|---|---|---|---|---|
| 1 | `schema_rbac.sql` | 改 | **+176**（`J)` 區塊 148、檔頭涵蓋清單 2、檔頭注意事項 4、檔尾驗證註解 22） | `J)` 區塊：三張表、**8 條外鍵**（其中 2 條 `CASCADE`）、2 個 CHECK、2 個 UNIQUE、2 個索引（含 1 個 **partial**）、**22 段 COMMENT**（1 段表 COMMENT 承載 `[UG:G9]`=A 的三件事 ＋ 3 段表 COMMENT ＋ 18 段欄位 COMMENT） |
| 2 | `backend/scripts/run_meta_schema_migration.py` | 新 | **446** | `[P1]`=A 的落地：一支腳本建 `U5` ＋ `U18` 的全部新物件（`memory` schema ＋ 5 張表 ＋ 7 個索引 ＋ 8 條 CHECK／UNIQUE ＋ grant ＋ COMMENT）。單一交易、COMMIT 前自我終檢、失敗 rollback ＋ 非零碼 |
| 3 | `backend/scripts/verify_meta_schema.sql` | 新 | **415** | 12 條斷言 `P1`–`P12`（29 處 `RAISE EXCEPTION`），純 SQL 不經 Python。結構類 8 條一個 `DO $$`；行為類 4 條一個交易並 `ROLLBACK` |
| 4 | `.github/workflows/ci.yml` | 改 | **+19**（job 內註解 7、新步驟 12） | 既有 `memory-schema` job 新增一個步驟執行 `P1`–`P12`。**`id` 與 `name:` 皆未改** |
| 5 | `DEPLOY.md` | 改 | **+150**（2.2 表 1 列、`2.2.9` 節 149 行） | `BR3.3` 的 blocking 同步：表清單加 `J` 列；新增 **2.2.9** 節（四件易誤讀的事、三態表、腳本執行步驟與前置條件、**9 條 `psql` 驗證指令**） |

**未動**（逐一查證 `git diff` 為空或零命中）：
`backend/database.py`（`NFR8.4` 的二元判準，**實測 diff 為空**）、
`backend/models.py`（本站零改動；三張表在該檔的命中數為 **0**——`tech-stack-decisions.md §二` 的「不建 ORM model」）、
`backend/services/` 全部、`backend/tests/` 全部、`deploy/` 全部、
任一 `.env.example`、`render-env.sh`、`openapi.json`、`ws-contract.json`、`frontend/` 全部。
三張表的名稱在 `backend/**/*.py` 的命中數為 **0**（唯一例外是本站新增的遷移腳本）——
本單元是 `spec`，**零應用程式碼、零端點、零畫面、零 ORM model**。

`schema.sql` **刻意未更新**（`project.md` 列為「建議一併更新（非 blocking）」）：
沿用 `U5` 的先例（該站也未把 `I)` 加進去，故該檔現在有 `H)` 而無 `I)`），
且再加一份 DDL 物化會與本站對遷移腳本採取的單一真實來源理由直接矛盾（§三之一）。
記為 `OPEN-CG18-9`。

## 二、實際跑過的驗證（**在真實 PostgreSQL 上跑的，不是推論**）

本機有執行中的 **PostgreSQL 17.7 ＋ pgvector 0.8.1**，故沒有等 CI，
直接在三個一次性 scratch database 上實測（既有的本機 `cloud360` 庫**未被碰到**）：

| 驗證 | 指令／方式 | 結果 |
|---|---|---|
| 第一次套用 `schema_rbac.sql` | `psql -v ON_ERROR_STOP=1 -f`（空庫） | **exit 0** |
| **第二次**套用（`BR2.1` 可重跑） | 同上，再跑一次 | **exit 0**，只有 `already exists, skipping` 的 NOTICE |
| 12 條斷言 | `psql -v ON_ERROR_STOP=1 -f backend/scripts/verify_meta_schema.sql` | **exit 0；12 條全部通過**（結構類 `P1`／`P2`／`P3`／`P5`／`P6`／`P8`／`P9`／`P12` ＋ 行為類 `P4`／`P7`／`P10`／`P11`） |
| 斷言的 `ROLLBACK` 是否乾淨 | 斷言後查六張表的列數 | **全部為 0**（`users`／`projects`／`systems`／三張新表） |
| 遷移腳本（模擬既有非空環境） | 以剝掉 `X)`／`I)`／`J)` 的 `schema_rbac.sql` 建庫，再跑腳本 | **exit 0**；印出 1 schema／5 表／7 索引／8 約束／3 條外鍵刪除行為 |
| 腳本重跑（冪等） | 同庫再跑一次 | **exit 0** |
| **腳本產出是否滿足 CI 斷言** | 對腳本遷移過的庫跑 `P1`–`P12` | **exit 0；12 條全部通過**（兩條路徑產出同一組結構） |
| 腳本的前置條件守門 | 對一個完全空的庫跑腳本 | **exit 1**，訊息指名缺 `users`／`projects`／`systems` 並指向 `run_hierarchy_migration.py` |
| 腳本不洩漏 `DATABASE_URL` | 以哨兵帳密指向不存在的埠觸發連線失敗，掃 stdout ＋ stderr 全文 | 密碼 **0 命中**、使用者名稱 **0 命中**、`postgresql+psycopg` **0 命中**；stdout 只有 `host=… database=…`（獨立複驗 `security-design.md §二之三` 的結論） |
| 全套 Python 測試 | `cd backend && python3 -m unittest discover -s tests` | **Ran 497 tests — OK**（與 `U5` 當時的基線相同；本單元不新增 Python 測試，故**應**維持 497） |
| OpenAPI 漂移 | `python3 backend/scripts/dump_openapi.py --check` | exit 0（「規格檔與後端程式碼一致」） |
| WS 契約漂移 | `python3 backend/scripts/dump_ws_contract.py --check` | exit 0 |
| repo contract | `python3 scripts/validate_repo_contract.py` | **passed** |
| env contract | `python3 scripts/validate_env_contract.py` | **passed** |
| `ci.yml` 可解析且 job 身分未變 | `yaml.safe_load` | 6 個 job（**未新增 job**）；`memory-schema` 的 `name:` 仍為 `Memory schema (real PostgreSQL)`；該 job 由 4 個步驟變為 5 個 |

## 三、三個計畫決定的落地

### 3.1 `[ND1]`=A：三條被點名的外鍵 ＋ 一條刻意不設

| 外鍵 | `ON DELETE` | 實測 `confdeltype` |
|---|---|---|
| `project_members.project_id → projects.id` | `CASCADE` | `c` ✓ |
| `project_members.user_id → users.id` | 無子句（`NO ACTION`）＋ COMMENT 承接 `OQ-H1` | `a` ✓ |
| `reselection_events.project_id` | **不設外鍵** | 對 `projects` 的外鍵數 **0** ✓（`information_schema` 與 `pg_constraint` 兩種查法各驗一次） |
| `system_requirement_fields.system_id → systems.id` | `CASCADE` | `c` ✓ |

`CASCADE` 而非 `RESTRICT` 的理由已實地複驗：`hierarchy_service.delete_project()`
的兩道守門在 `:153`（`is_default`）與 `:156`（剩餘系統數），**沒有任何一道關於成員**，
而 `:161` 是 `db.delete(project)`。`P4` 以行為面鎖住它（刪專案不得被外鍵擋下），
`N2` 證實把它改成 `RESTRICT` 會讓 `P3` 與 `P4` **同時**紅燈。

### 3.2 CI job 不改名

既有 `memory-schema` job 新增一個步驟，**`id` 與 `name:` 皆未改**——GitHub 的
check name 取自 job 的 `name:`，改它會讓 branch protection 的必要檢查變成
「缺少必要檢查」。代價是 job 名稱比它實際涵蓋的範圍窄，已在 job 內以 7 行註解
寫明原因與「下次新增別的 schema 斷言時照同一形狀再加一個步驟」。

### 3.3 刻意不建 `project_members.user_id` 的索引

兩個條件本輪都不成立（成員視角的專案清單尚未存在、使用者硬刪除是 `OQ-H1`），
故不建，並在 `J)` 區塊以註解寫明「它何時會需要」與承接站 `U19`。
`project_id` 側不需另建：`uq_project_members_project_user` 以它為前導欄，
同時覆蓋 `resolve_project_role`、`list_members`、`FR12.4` 的挑選過濾與 `CASCADE`
的子側掃描。

## 四、要揭露的上游缺口與本站的新發現

### 4.1 計畫 §五 的三處（原定揭露項）

| # | 缺口 | 本站處置 |
|---|---|---|
| 1 | **`entities.md` 少九個欄位**（`ReselectionEvent` 5、`SystemRequirementField` 4） | DDL 依 `components.md:819`／`:820` 建**全欄**；`P5` 斷言「8 欄且五個稽核欄位都在」，`N9` 證實少一欄即紅。**不回改 `entities.md`**（已核可上游）。`entities.md` 的 `entity_constraints` 另有一處：它寫「同一系統內同一欄位名至多一列」（兩欄），本站**刻意加寬為三欄** `(system_id, agent_group, field_key)`，理由寫進欄位 COMMENT 與 `P11` 的錯誤訊息；`P11` 的**第二半**（同一 `field_key` 在不同 agent 組下可以插入）就是為了讓兩欄鍵被 `N7` 抓到——只驗「重複三元組被拒」那一半的話，兩欄鍵會通過 |
| 2 | **`rules.md` 的 `BR2.3` 寫「四條外鍵」**，`[ND1]`=A 後實為三條 | DDL 建三條（見 §三之一）；`P6` 在第四條被加回來時紅燈（`N3` 證實）。**不回改 `rules.md`** |
| 3 | **契約 `K-15` 的 `foreign_keys` 同樣列了第四條** | 一併揭露。這是 `nfr-design` 審查發現 `R-01`（Major），該站只對 `rules.md` 開了修訂指派而**漏了 `K-15`**——而 `K-15` 是 `U19`／`U20` 讀的跨單元契約，比 `rules.md` 的影響面更大。兩處都在本摘要內可見 |

### 4.2 本站新查出的五處

| # | 發現 | 證據 | 處置 |
|---|---|---|---|
| 4 | **`BR2.3` 的「四條」在第二個意義上也不對：回補九個欄位同時帶進五條 `BR2.3` 從未列舉的外鍵。** 實際外鍵總數是 **8**（`project_members.invited_by`、`reselection_events.promoted_user_id`、`reselection_events.previous_owner_user_id`、`system_requirement_fields.updated_by`、`system_requirement_fields.updated_on_behalf_of` 五條，加上 `BR2.3` 原列四條中存活的三條） | `pg_constraint` 實查 8 條，逐條列於 `traceability.json` 的 `CG-SCHEMA-J` | 揭露。修訂 `BR2.3` 時**不能只把「四」改成「三」**——那會留下一個仍然錯的數字。`OPEN-CG18-3` |
| 5 | **`system_requirement_fields.updated_on_behalf_of` 的外鍵指向 `users`，而 `entities.md` 逐字寫 `references: users.id 或 agent 識別`。** 若該 agent 的識別不是 `users` 的一列，這條外鍵會擋住 `BR1.5` 的寫入。計畫 §三之三 明確指定 `INTEGER REFERENCES users (id)`，故本站照建並揭露張力 | `entities.md` 該屬性的 `references` 欄逐字；`K-17` 的 `write_field` 簽章為 `on_behalf_of: str|None` | 揭露並指派 `U20`（`K-17` 的擁有者）：若 agent 識別不是使用者列，這條外鍵必須在 `U20` 落地前改掉。`OPEN-CG18-6` |
| 6 | **三態模型的 CHECK 允許一個第四種、未被命名的狀態**：`value IS NULL AND cleared_at IS NULL`（列存在、從未填過、也沒清空過）。`cleared_at IS NULL OR value IS NULL` 擋不住它 | CHECK 運算式本身；`P10` 的三個案例不涵蓋該組合 | **不收緊**：計畫 §三之三 逐字固定了該運算式，收緊即偏離已核可的 DDL 形狀；且該狀態經 `K-17` 的 `write_field`／`clear_field` **不可達**（兩者各自必定設定其中一個欄位）。揭露供 `U20` 在 facade 層判定是否需要額外守門。`OPEN-CG18-7` |
| 7 | **遷移腳本沒有任何自動化覆蓋，而本站在手動執行時抓到兩個真實缺陷。** ① `conn.exec_driver_sql()` 走 SQLAlchemy 的 pyformat 參數路徑，於是 `I)` 區塊的 `format('GRANT … TO %I', current_user)` 以 `only '%s', '%b', '%t' are allowed as placeholders, got '%I'` 失敗；改走 DBAPI cursor（psycopg v3 無參數時不做 `%` 插值）才通。② `text("… :q::regclass …")` 的 `:q` 不被 SQLAlchemy 認成 bindparam，冒號原樣送到伺服器並以 `syntax error at or near ":"` 失敗；改為 `cast(:q AS regclass)`。**兩者 CI 都抓不到**，因為 `deploy.yml` 與 `ci.yml` 都不執行這支腳本 | 兩次實測的錯誤訊息逐字（已寫進腳本內的註解以免下一個人重踩） | 揭露為命名缺口。`P1`–`P12` 驗的是 `schema_rbac.sql` 那條路徑，不是腳本那條路徑；本站以「對腳本遷移過的庫跑 `P1`–`P12`」作為替代證據（通過），但那是一次人工執行而非閘門。`OPEN-CG18-4` |
| 8 | **腳本有一個上游沒有寫下的順序前置條件**：`J)` 的兩條外鍵指向 `projects`／`systems`，故 `U4` 的 `run_hierarchy_migration.py` 必須**先**跑過 | 外鍵定義；對完全空的庫實測得到 `UndefinedTable` 的前身 | 腳本加入明確的前置條件檢查（回可讀訊息並指向 2.2.7），`DEPLOY.md 2.2.9` 第一個程式碼區塊寫明。**仍無機械強制**（`deploy.yml` 不呼叫任何遷移腳本）。`OPEN-CG18-10` |

### 4.3 兩處「有意為之、容易被下一個人誤判為缺漏」

| 事項 | 為什麼不是缺漏 |
|---|---|
| **`reselection_events.previous_role`／`new_role` 沒有 CHECK** | 形狀對照 `U5` 的 `previous_scope`／`new_scope`（兩者同樣無 CHECK，只有 `action` 有）。更要緊的理由是 `OPEN-ND18-3` **尚未決定本表是否同時承載人工的 `FR12.2` 角色變更**，而封閉列舉會替那個決定先下結論。已寫進 `previous_role` 的 COMMENT |
| **`reselection_events` 沒有保存期限** | `components.md:886` 逐字「清＝`acknowledgedAt`，事件列本身不刪——這是刻意的，刪了就失去稽核」。已在表 COMMENT 逐字寫「do NOT add a 90-day purge by analogy with U5」，並在 `DEPLOY.md 2.2.9` 列為四件易誤讀的事之一 |

### 4.4 一處既有的文件不一致（非本站造成，未代為修正）

`schema_rbac.sql` 的檔頭涵蓋清單原本就缺 `F)`（C1 退場）、`G)`（U2 估價上傳）、
`I)`（U5 記憶層）三個區塊。本站**只加了 `J)`**——代為補齊其他單元的條目不在本單元
範圍內，且會讓本站的 diff 看起來動了別人的交付。記為 `OPEN-CG18-11`（文件層，非結構層）。

## 五、ADR-0006 四面向 ＋ PBT 的逐項判定（本站落點）

逐格對照上游 `security-requirements.md §二` 與 `security-design.md §五` 的同名表；
**判定與上游相同處寫明「與上游相同」，不同處必須寫出理由**（本站無不同處）。

| 面向 | 上游判定 | 本站的實作落點 |
|---|---|---|
| **IAM** | 無增量（`K-15` 逐字「DDL 不經使用者授權」） | **與上游相同：無增量。** 本站交付 per-project 授權的**資料基礎**，判定屬 `K-16` 的 facade。`BR1.1`（`joined_at` 非空）間接影響授權正確性——改選選錯人等於把專案管理權給錯人——故它有一條專屬斷言（`P2`）與一項突變（`N1`）。另 `project_members.role` 的 COMMENT 逐字寫明它與全域 `Project_Admin` **同名不同義**且 `FR12.6` 要求兩層串聯（`OPEN-P2` 的唯一承載形式） |
| **Encryption** | 不適用 | **與上游相同：無 pattern。** 三張表無憑證／token／金鑰。本站額外**實測**腳本的失敗輸出不洩漏 `DATABASE_URL`（§二的驗證表，哨兵帳密 0 命中），並把「腳本不得輸出 URL 或其片段」寫成腳本 docstring 的明文禁令 |
| **Network exposure** | 不適用 | **與上游相同：不新增任何暴露面。** 零端點、零進程、零監聽埠；遷移腳本是手動 CLI 不是服務 |
| **Audit logging** | **適用** | **本站的實質產出：** ① `[ND1]`=A 落地——改選稽核不設外鍵，並以 `P6`（手段）＋ `P7`（目的）兩條斷言鎖住存活，`N3` 證實兩者同時紅；② 回補 `FR12.4b` 的五個稽核欄位並以 `P5` 的兩半鎖住（`N9` 證實），其中四個正是 `AC12.2.2` 的 Then 點名的「誰／何時／由什麼／改為什麼」；③ `updated_by` 為 `NOT NULL`（`P9`），使 `K-17` 的 `clear_field` 逐字要求的「記 `clearedAt` **與 `updatedBy`**」在資料層成立；④ `cleared_at` 獨立於 `value` 並以 CHECK 鎖住配對（`P10`／`N6`）；⑤ 表 COMMENT 逐字寫明本表**刻意沒有**保存期限的理由，以免被照 `U5` 的樣子補上 90 天清除而把 `FR12.4b` 的稽核清掉；⑥ `FR12.2` 的角色變更稽核**仍無承載者**（`OPEN-ND18-3`）——本站不自行決定表的語意範圍，但已在表 COMMENT 寫明該開放問題與 `AC12.2.2` 的 Given 是人工變更這項證據 |

**PBT 判定：N/A（非豁免）** —— 與上游兩站相同。本單元是 DDL，**沒有任何函式**，
`hypothesis` 的生成器沒有作用對象。**失效條件已指明且不變**：`U19` 的自動改選挑選
函式應為不讀 DB 的純函式（`unit-of-work.md:448`、`K-16` 的 `select_successor`），
PBT 在**那裡**適用，可失敗的性質是**排列不變性**（`ORDER BY joined_at` 在時間戳
相同時無穩定順序），而本單元的 `BR1.1` 是那個性質可被驗證的資料層前提。

## 六、Testing Contract 的遵循（`test-after`／`standard`／`brownfield`）

| contract 條款 | 本站的落實 |
|---|---|
| `methodology: test-after` | 順序逐步照做：Step 2–4 先實作（`schema_rbac.sql`／腳本／`DEPLOY.md`），Step 5 才寫斷言檔，Step 6 接線，Step 7 突變。**沒有先寫測試** |
| `runner_step`（runner readiness 先於第一個測試步驟） | Step 1 驗證既有載體：`memory-schema` job 已提供 PG service container 與已套用的 `schema_rbac.sql`，前置條件已滿足，**brownfield 不需 bootstrap**。確切指令記於 `unit-test-instructions.md §〇` 並已在本機逐字執行 |
| `testable_layers` 五層 | 只有 **Data model / database behavior** 適用；Repository／Business logic／API／Frontend 四層在本單元**不存在**（零程式碼、零端點、零畫面），故對應步驟省略 |
| `strategy_volume`：每個 component 5–8 個測試 | 三張表＝三個 component，12 條斷言分佈 **4／4／4**，落在區間下緣。DDL 的可觀察行為少於一般 component，故不以湊數補到 8 |
| `strategy_volume`：unit ＋ key boundaries 的 integration | 結構類 8 條是「unit」層（讀系統目錄）；行為類 4 條是真實寫入／刪除的「integration」層（`CASCADE` 連帶刪除、稽核存活、三態 CHECK、三欄唯一鍵） |
| `scope_floor`：既有測試維持綠燈 | `Ran 497 tests — OK`（與基線相同） |
| `scope_floor`：不另加新測試底線 | 本單元不新增 Python 測試（理由見 `unit-test-instructions.md` 檔頭：SQLite 對外鍵／`ON DELETE`／partial index 的語意不同，在它上面「通過」不構成任何保證） |
| 80% line coverage | **無量測對象**——零 Python／TS 應用程式碼。唯一的程式檔是遷移腳本，而它的驗證是執行它本身（§二）。`team.md` 已記載本 repo **完全沒有覆蓋率量測機制**，故此處不宣稱任何百分比；以「斷言數 ÷ 可觀察行為數」替代說明：12 條斷言涵蓋三張表的全部 CHECK／UNIQUE／nullability／外鍵刪除行為／partial index／防呆 COMMENT，加上兩條行為路徑 |

## 七、突變驗證：10 項全部 RED，零存活

**每一項突變都先確認 DDL 真的改變了**（改動前後各查一次 `information_schema`／
`pg_catalog`／檔案 sha256，兩者必須不同），才判讀斷言結果——`U5` 的 `M1` 踩過
「突變本身是 no-op」，使「測試沒抓到」實際上是「突變沒發生」。

| # | 突變 | 應紅 | DDL 改變驗證（before → after） | 結果 |
|---|---|---|---|---|
| `N1` | `joined_at` 改為 nullable | `P2` | `is_nullable`：`NO` → `YES` | **RED ✓** exit 3，紅燈 `P2` |
| `N2` | `project_members.project_id` 的 `CASCADE` 改為 `RESTRICT` | `P3` ＋ `P4` | `confdeltype`：`c` → `r` | **RED ✓** 全檔跑 exit 3 紅燈 `P3`；**行為類單獨跑** exit 3 紅燈 `P4` |
| `N3` | 為 `reselection_events.project_id` 加上指向 `projects` 的外鍵 | `P6` ＋ `P7` | 對 `projects` 的外鍵數：`0` → `1` | **RED ✓** 全檔跑 exit 3 紅燈 `P6`；**行為類單獨跑** exit 3 紅燈 `P7` |
| `N4` | 拿掉 `ix_reselection_events_unack` 的 `WHERE acknowledged_at IS NULL` | `P8` | `indexdef`：含 `WHERE (acknowledged_at IS NULL)` → 不含 | **RED ✓** exit 3，紅燈 `P8` |
| `N5` | 在獨立腳本執行的 DDL 中插入一條引用不存在表的敘述 | **腳本退出碼非零** | `schema_rbac.sql` sha256：`7f902e85169d` → `e5001320abae`（事後還原並以 sha256 核對相符） | **RED ✓** 腳本 exit **1**；**回滾後三張表存在數 = 0**（證實單一交易）；輸出洩漏 `DATABASE_URL` = False |
| `N6` | 移除三態的 CHECK | `P10` | 該約束存在數：`1` → `0` | **RED ✓** exit 3，紅燈 `P10` |
| `N7` | 唯一約束由三欄改為兩欄 `(system_id, field_key)` | `P11` | `pg_get_constraintdef`：`UNIQUE (system_id, agent_group, field_key)` → `UNIQUE (system_id, field_key)` | **RED ✓** exit 3，紅燈 `P11`（命中的是**第二半**——同一 `field_key` 在不同組下被拒；第一半在兩欄鍵下仍然綠，這正是 `P11` 必須有兩半的理由） |
| `N8` | 刪掉 `system_requirement_fields` 的表 COMMENT | `P12` | COMMENT 長度：`967` → `<null>` | **RED ✓** exit 3，紅燈 `P12` |
| `N9` | 移除 `reselection_events.promoted_user_id` 欄位 | `P5` | 欄位數：`8` → `7` | **RED ✓** exit 3，紅燈 `P5` |
| `N10` | `CREATE TABLE IF NOT EXISTS project_members` 改成 `CREATE TABLE` | 既有的「第二次套用」步驟 | `schema_rbac.sql` sha256：`7f902e85169d` → `7ea48b8e4afe`（事後還原並核對相符） | **RED ✓** 第一次套用 exit 0、**第二次 exit 3**，錯誤逐字 `ERROR: relation "project_members" already exists` |

**`N2`／`N3` 的兩半都看了。** 只有結構斷言紅而行為斷言綠，會表示行為斷言寫錯了
（它應該在外鍵存在時因級聯或拒絕而失敗）。做法是從**真實的斷言檔**切出行為類那一段
另存執行，而不是另寫一份——另寫一份會驗到一個不存在的東西。

突變 harness 在每次突變前都先確認「突變前的斷言本身是綠的」；若不是就記為
`SETUP FAILED` 而不是 PASS。10 項全部走完該檢查。

## 八、未解事項（完整清單見 `traceability.json` 的 `open_items`）

| id | 嚴重度 | 一句話 |
|---|---|---|
| `OPEN-CG18-1` | named-gap | `entities.md` 仍宣告 2／4 欄與兩欄唯一鍵；DDL 刻意不同，回補需修訂已核可的上游 |
| `OPEN-CG18-2` | named-gap | `rules.md BR2.3` 與契約 `K-15` 的 `foreign_keys` **兩處**都還列著第四條外鍵 |
| `OPEN-CG18-3` | named-gap | `BR2.3` 的「四條」在第二個意義上也錯：實際有 **8** 條外鍵 |
| `OPEN-CG18-4` | named-gap | **遷移腳本零自動化覆蓋**；本站手動執行時抓到兩個真實缺陷 |
| `OPEN-CG18-5` | named-gap | 本機驗證用 PG **17.7**，CI 與部署用 **pg18**；版本差異本身未被驗證 |
| `OPEN-CG18-6` | named-gap | `updated_on_behalf_of` 的外鍵指向 `users`，與 `entities.md` 的「或 agent 識別」有張力 |
| `OPEN-CG18-7` | named-gap | 三態 CHECK 允許第四種未命名狀態（`value` 與 `cleared_at` 皆 NULL） |
| `OPEN-CG18-8` | process | `tcms-test-cases` 未跑（`project.md ## Mandated` 的 blocking stage） |
| `OPEN-CG18-9` | named-gap | `schema.sql` 未更新（非 blocking），沿用 `U5` 先例 |
| `OPEN-CG18-10` | named-gap | 腳本的順序前置條件（`U4` 的遷移必須先跑）只有文件與腳本內檢查，無機械強制 |
| `OPEN-CG18-11` | named-gap | `schema_rbac.sql` 檔頭涵蓋清單原本就缺 `F)`／`G)`／`I)`；本站只補 `J)` |
| `OPEN-P1` | **resolved** | 既有環境的建立路徑已有唯一答案：`run_meta_schema_migration.py` |
| `OPEN-P2` | carried | per-project `role` 與全域角色同名不同義，只能以 COMMENT 標明 |
| `OPEN-P4` | carried | 拒絕事件不留稽核（屬 `U19` 的 `H-8`） |
| `OPEN-P5` | carried | 沒有機制保證有人去執行腳本；`deploy.yml` 不呼叫任何遷移腳本 |
| `OPEN-ND18-3` | carried | `FR12.2` 的人工角色變更稽核仍無承載者；本站不自行決定表的語意範圍 |
| `OQ-H1` | carried | 使用者硬刪除的行為上游刻意未決，以 COMMENT 承接 |

## 重新查驗（code-generation Request Changes 後，conductor，`2026-10-20T23:05:36Z`）

**觸發**：使用者對整站送出 Request Changes（原文：「修正 functional-design/merge-blockers.md 列出的 19 項合併前必修，各在所屬單元修正並附測試；需人工裁決的項目（#7、#8 等）逐項問我。object-picker-ui 的 R-08、R-09 已修，重新審查即可。」）。19 項無一劃給本單元（計畫 §七，使用者已核可）。本輪**未改任何應用程式碼**；引擎於核可時重設 8 格勾選，逐格對照現況勾回。

| Step | 查驗依據 |
|---|---|
| 1、5 | `backend/scripts/verify_meta_schema.sql` 存在，執行指令記於 `unit-test-instructions.md` |
| 2 | `schema_rbac.sql:568` 起為 `J) U18 project-meta-data` 區塊；檔頭 `:12` 列入涵蓋清單 |
| 3 | `backend/scripts/run_meta_schema_migration.py` 存在，`BLOCKS_TO_RUN = ("X", "I", "J")` |
| 4 | `DEPLOY.md:251` 表格列 J、§2.2.9 為執行步驟；§2.2.8 已改為指向 2.2.9 |
| 6 | `.github/workflows/ci.yml:393` 在 `memory-schema` job 內執行 `verify_meta_schema.sql` |
| 7 | 突變紀錄見本檔先前章節；本輪未改 DDL 結構（只改 COMMENT），該結果仍適用 |
| 8 | 本檔、`source-manifest.json`（5 個路徑，皆存在）、`traceability.json` 存在 |

| 命令（`backend/`，`.venv`） | 結果 |
|---|---|
| `tests.test_retention_purge_contract` | `Ran 10 tests` → `OK` |
| `tests.test_membership_data` | `Ran 9 tests` → `OK` |
| 完整套件 | `Ran 1223 tests` → `OK`（本輪 memory-data 查驗時所跑，其後無程式變更） |

**本輪未驗**：`verify_meta_schema.sql` 需要真實 PostgreSQL；本機無 Docker daemon、`localhost:5432` 無回應。CI 最近一次 `memory-schema` job（run `38117175745`，`a5200fc`）為 success，其後 `J)` 區塊被 `6dff4d4`（U20）與 `8677b7d`（U23）改過，並有本輪 `hierarchy-data` 的 COMMENT 修改，故以下次推送後的 CI 結果為準。

**狀態更新**：上表 `OQ-H1` 已由 `hierarchy-data` 本輪的必修第 3 項作成（使用者裁決：空預設專案隨使用者清除、其餘參照回 409），`project_members.user_id` 的 COMMENT 已同步更新；本表該列保留原文作為歷史紀錄。

**審查後補正（review-02，READY，3 個 Minor）**：`ci.yml` 的步驟名稱與註解由「P1-P12」更新為「P1-P16」（U20 加了 P13–P16；只改步驟名稱與註解，job 的 `id`／`name:` 不變，故不影響必要檢查名稱，YAML 解析通過）；`DEPLOY.md:251` 的「無資料遷移」補上 U20 條件式欄位轉型的例外。第三項（`verify_meta_schema.sql` 未重跑）維持，待推送後以 CI 結果回填。

## 重做（Code Generation 自頭重來，2026-10-25）

<!-- 寫入時間：2026-10-25T06:30:04Z（`date -u` 取值） -->

Code Generation 依使用者裁決自頭重來；本單元計畫重新核可後，逐步查驗既有產出，**程式碼與文件改動為 0**。計畫 8 格勾 7 格：**Step 7（突變驗證）未勾**——計畫要求實際改壞 DDL 確認紅燈，本輪未重跑；§七的 10 項 RED 是先前版本的紀錄。後續單元的改動一律保留（U19 的 `cause` 欄與 `ck_reselection_events_cause`、U20 的 varchar 型別與條件式收斂 DO 區塊、U23 的 `ix_project_members_user_id`）。

### 本機真實 PostgreSQL 實跑（上節第三項「未重跑」本輪補上）

Homebrew PostgreSQL **17.7** ＋ pgvector 0.8.1，在 scratchpad 建一次性叢集（只開 TCP，port 55432）；CI 用 `pgvector:pg18`，版本不同。跑完已停機、刪除資料目錄，未碰任何共用或 staging 資料庫，無殘留程序。

| 步驟 | 結果 |
|---|---|
| 第一次套用 `schema_rbac.sql` | exit 0（3 則 already exists 通知） |
| 第二次套用（可重跑） | exit 0 |
| `verify_meta_schema.sql` | exit 0；結構類 P1／P2／P3／P5／P6／P8／P9／P12／P13／P14／P15／P16 與行為類 P4／P7／P10／P11 全部通過 |
| 照 CI 的 U20 步驟 A 降回舊定義（`downgrade_requirement_fields.sql`） | exit 0 |
| 步驟 B `run_meta_schema_migration.py` | exit 0；索引 9 個、CHECK／UNIQUE 9 條、U20 欄位收斂本次有執行、清掉非空舊值 0 筆、終檢通過 |
| 收斂後再跑 verify | exit 0，P1–P16 全通過 |
| 再跑一次遷移腳本 | 「本次未執行（欄位已是 varchar(64)…）」、「終檢通過」（經管線執行，exit code 未直接擷取；「終檢通過」只在回傳 0 的路徑印出） |
| 全套 `-m unittest discover -s tests`（`backend/.venv`） | `Ran 1319 tests`、`OK (skipped=3)`（本單元無 Python 測試模組） |
| `validate_repo_contract.py`、`validate_env_contract.py` | 皆 passed |

### 與已核可計畫／測試說明的落差（凍結文件不改，以本節為準）

- 計畫 §三之二 寫 `reselection_events` 8 欄，現為 9 欄（U19 的 `cause`）；§三之三 寫 `updated_on_behalf_of` 為 `INTEGER REFERENCES users`，現為 `VARCHAR(64)`、無外鍵（U20）；§四之三 說不建 `user_id` 索引，現已由 U23 建立。
- 測試說明只列 P1–P12（實為 P1–P16），P5 寫「恰為 8 欄」（斷言實為 9 欄）；指令的 `-d cloud360` 與預設 port 視環境而定。
- 檔內過時註解（不影響行為，本輪未改，交 build-and-test 一併清理）：`verify_meta_schema.sql:99` 仍寫 8 欄（`:103` 實查 9 欄）；`ci.yml:328` 寫「12 條斷言（P1-P16）」；`ci.yml:383` 寫 P13–P16 由 U20 加入，實際 P13／P14 為 U19（`verify_meta_schema.sql:2-4`）；`DEPLOY.md:795` 仍寫「本節的 P1–P12」，同段 `:791` 已寫 16 條。

`source-manifest.json` 的 5 條路徑全部存在且仍屬本單元（J) 區塊 `schema_rbac.sql:567-808`；`ci.yml:388-393`）。

## 共用檔異動後的重新驗證與補審（計畫 §八，2026-10-30）

<!-- 寫入時間：2026-10-30T01:53:26Z（`date -u` 取值） -->

本輪**未改任何程式碼、SQL、workflow 或共用檔**；突變只在 scratchpad 的副本與一次性資料庫上做。工作樹 HEAD 為 `c6a40f9`。

### 一、收據比對（`reviewed-source-3decc3ed696e.tsv`，最新一份）

| 檔案 | 收據 sha256 | 現況 sha256 | 結果 |
|---|---|---|---|
| `schema_rbac.sql` | `27e92ecdc5d0…` | `27e92ecdc5d0…` | 相同 |
| `backend/scripts/run_meta_schema_migration.py` | `d389b302aa80…` | `d389b302aa80…` | 相同 |
| `backend/scripts/verify_meta_schema.sql` | `1246c5ef8e8a…` | `1246c5ef8e8a…` | 相同 |
| `.github/workflows/ci.yml` | `a854442aae2a…` | `a854442aae2a…` | 相同 |
| `DEPLOY.md` | `2608a131203c…` | `d9b0571c5688…` | **不同**（見下） |

**`DEPLOY.md` 的逐 hunk 判定。** `git show 624c170:DEPLOY.md` 的雜湊是 `d499fb4824a1…`，**不等於**收據；DEPLOY.md 的歷次 commit（最近 15 個）也沒有一個等於收據——收據是 10-25 當時未提交的工作樹狀態。故改以「從現況逐 hunk 回退到 `624c170`」的方式比對：對 `624c170` 與現況之間的 15 個 hunk 做全部 2^15 種回退組合，**恰有一組**的結果等於收據雜湊：回退第 4（現行 730–738 行）、14（2229 行）、15（2239 行）三個 hunk。故收據之後的變動**只有這三處**，與前面單元證得的 #24（730–738）、#26（2229、2239）一致；其餘 12 個 hunk 在收據當時已存在（含 2.2 表 J 列的第 251 行，已在 review-03 範圍內）。

- **#26（2229、2239 行，§5.13）**：U14 的 6a 回滾敘述，不在本單元段落。
- **#24（730–738 行）落在本單元 2.2.9 的「前進步驟」小節內**（2.2.9 起於第 617 行、U20 小節起於第 809 行，故 730–738 屬 U18 自己的段落，不是 U20 小節）。逐字判定：
  - 改的是 **U18 段落的一句事實**：原文「忘了跑就沒有表……`U19`／`U20` 的任何查詢會立即報 `relation "project_members" does not exist`，不是靜默降級」，改為「忘了跑**不會**沒有表：後端啟動的 `Base.metadata.create_all()` 會依 ORM（`ProjectMember`、`ReselectionEvent`、`SystemRequirementField`）建出三張表，只缺 COMMENT；表若以舊定義存在則缺 U20 的欄位收斂」。
  - 修改者是 #24（`merge-blockers.md` 第 24 列，單元 `requirement-field-service`／U20），該列逐字指出這段與同檔 U20 小節「說法相反」。
  - 新敘述**屬實**：ORM 類別在 `backend/models.py:546`（`ProjectMember`）、`:599`（`ReselectionEvent`）、`:696`（`SystemRequirementField`），`create_all` 在 `backend/database.py:90`。這些 ORM 由 U19／U20 加入，**不是本單元的交付**（本單元仍為零 ORM model，§一 的「未動」敘述就本單元自身的 diff 而言仍成立）。
  - **對本單元段落的影響**：本單元的 DDL、遷移腳本、驗證指令與「手動步驟、`deploy.yml` 不呼叫遷移腳本」這兩句都沒變；改變的是「忘了跑的失敗模式」——由「立即報錯」變成「靜默缺 COMMENT／缺收斂」。這使 §4.2 第 8 項與 `OPEN-P5` 的代價**更重**（失敗由大聲變靜默），本單元不需改 DDL，但下游讀 `OPEN-P5` 時應以 `DEPLOY.md:730-738` 的現行敘述為準。

### 二、真實 PostgreSQL 依據（只讀）

- `gh run view 40423375585`：workflow `CI`、event `push`、headSha `c6a40f91b805…`、conclusion `success`。`Memory schema (real PostgreSQL)` job（`121923028241`，2026-10-26T23:59:01Z–23:59:55Z）第 7 步「**Verify project-meta schema assertions (P1-P16)**」為 **success**；同 job 第 10–14 步（U20 的 A 降回舊定義 → B 收斂 → C/D/E）亦全為 success。
- `git log --oneline c6a40f9..HEAD -- schema_rbac.sql backend/scripts/verify_meta_schema.sql backend/scripts/run_meta_schema_migration.py`：**空**（HEAD 即 `c6a40f9`），三檔亦無未提交變動（`git status --short` 為空）。故 CI 驗的就是現行檔案。
- 未觸發任何 workflow／rerun。

### 三、R-06（Major）— `P13`–`P16` 的突變

**環境**：Homebrew PostgreSQL **17.7**（`/opt/homebrew/opt/postgresql@17/bin`；PATH 上的 `initdb` 是 14.20，故改用 17 的絕對路徑）＋ 本機既有 pgvector（`vector` 擴充可用，`schema_rbac.sql` 未略過任何段落）。`initdb -U postgres --auth=trust` 於 `$S/u18pg/data`，以 `listen_addresses=127.0.0.1 -p 47391` 啟動。**與計畫的偏離**：指定的 `-k $S/u18pg` 因 Unix socket 路徑超過 103 bytes 啟動失敗（log 逐字 `Unix-domain socket path ... is too long (maximum 103 bytes)`），改為 `unix_socket_directories=''`（只開 TCP）。所有 psql 均帶 `-h 127.0.0.1 -p 47391 -U postgres`，未讀 `.env`／`DATABASE_URL`，未連任何其他主機。CI 用 `pgvector:pg18`，版本差異仍未驗（`OPEN-CG18-5` 不變）。

**基準**：副本 `schema_rbac.sql`（sha256 與 repo 相同 `27e92ecdc5d0…`）在空庫 `u18_base` 套用兩次皆 exit 0；副本 `verify_meta_schema.sql`（`1246c5ef8e8a…`）exit 0，結構類 12 條與行為類 4 條全通過。

| # | 突變（只改副本） | DDL 確實改變（突變庫 vs 基準庫） | 結果 |
|---|---|---|---|
| (a) | 拿掉 `CONSTRAINT ck_reselection_events_cause CHECK (...)` | `pg_constraint` 中該名稱：基準 `1` → 突變 `0` | **RED ✓** exit 3：`P14 FAILED (U19/[FD3]=A／BR5.3): 缺少約束 ck_reselection_events_cause。沒有它，一個拼錯的 cause 值（例如 'auto_reselect'）會寫入成功，而後果是**橫幅永遠不出現**…` |
| (b) | 移除 `cause` 欄（連帶移除引用它的 CHECK 與 `COMMENT ON COLUMN ... cause`，否則副本本身套用失敗） | `reselection_events` 欄數：基準 `9`（含 `cause`）→ 突變 `8`（無 `cause`） | **RED ✓** exit 3，**先紅的是 `P5`**：`P5 FAILED (FR12.4b): reselection_events 應有 9 欄，實際 8。…`。`P5` 排在 `P13` 之前，故 `P13` 被遮住；以**診斷副本**（只把 P5 欄數那一半的條件改為 `IF false`）重跑，**`P13` 紅**：`P13 FAILED (U19/[FD3]=A): reselection_events 缺少 cause 欄。…`。兩條各自抓得到 |
| (c-1) | 只在副本 `CREATE TABLE` 把 `updated_on_behalf_of` 改為 `INTEGER REFERENCES users (id)` | **套用後未改變**：同檔 U20 的條件式 DO 區塊偵測到 integer，NOTICE 逐字「已移除 updated_on_behalf_of 的外鍵 system_requirement_fields_updated_on_behalf_of_fkey」「已由 integer 轉為 varchar(64)，清掉的非空舊值 0 筆」；套用後型別 `character varying(64)`、該欄外鍵 `0` | 斷言**綠**——這是**突變 no-op**，不是斷言漏抓：`schema_rbac.sql` 的收斂設計本來就會把這個突變自我修復（`U5` 的 `M1` 所警告的形狀）。故改用 (c-2) |
| (c-2) | 在已套用的庫上以 `ALTER COLUMN updated_on_behalf_of TYPE INTEGER USING NULL` ＋ `ADD CONSTRAINT ... FOREIGN KEY (updated_on_behalf_of) REFERENCES users (id)` 模擬「未收斂的舊定義資料庫」（與 CI 的 U20 步驟 A 同形） | 型別 `character varying(64)` → `integer`；該欄外鍵 `0` → `1` | **RED ✓** exit 3，**先紅的是 `P15`**：`P15 FAILED (U20/BR47.1): updated_on_behalf_of 應為 character varying(64)（agent 組識別字），實際 integer。…`。以診斷副本暫停 P15 重跑，**`P16` 紅**：`P16 FAILED (U20/[FD1]=A): updated_on_behalf_of 不得有外鍵，實際 1 條。…` |

**還原後複驗**：(c) 的庫重套原始副本 → DO 區塊收斂 → verify exit 0；另建新庫 `u18_restore` 套用原始副本 ＋ verify，結構類與行為類全通過。

**清理**：`pg_ctl stop -m fast` 完成；`lsof -nP -iTCP:47391 -sTCP:LISTEN` 無輸出；`pgrep -fl u18pg` 無輸出；`$S/u18pg` 已整個刪除。

**判定**：(a)、(b)、(c) 三項突變皆致紅（(c) 以 (c-2) 的形式；(c-1) 的 no-op 已如實記錄並說明原因），故**勾 Step 7**。限制：診斷副本改動了斷言檔副本的一個 `IF` 條件以觀察被遮住的斷言，這是觀察手段而非替代斷言；`P5` 與 `P15` 先紅本身已足以讓 CI 紅燈。

### 四、R-01、R-02、R-07 — 已知限制（本輪不改共用檔）

- **R-01**（`OPEN-CG18-12`）：`system_requirement_fields` 沒有恰好欄數斷言（現為 9 欄：`schema_rbac.sql:695-706` 的 `id`／`system_id`／`agent_group`／`field_key`／`value`／`cleared_at`／`updated_at`／`updated_by`／`updated_on_behalf_of`）；`P1`（6 欄）、`P5`（9 欄）對另兩張表有。多一欄不會被任何斷言抓到。
- **R-02**（`OPEN-CG18-13`）：`run_meta_schema_migration.py:195-199` 的 `EXPECTED_FK_DELETE_ACTIONS` 只有 3 條。審查寫「8 條外鍵」是 U20 移除 `updated_on_behalf_of` 外鍵**之前**的數字；以 `grep -n REFERENCES` 實查 `J)` 區塊現為 **7 條**（`:597`、`:601`、`:604`、`:650`、`:651`、`:696`、`:702`）。審查點名的另 5 條逐條現況：
  1. `project_members.invited_by → users`（`:604`）：刪除行為未核對；
  2. `reselection_events.promoted_user_id → users`（`:650`）：未核對；
  3. `reselection_events.previous_owner_user_id → users`（`:651`）：未核對；
  4. `system_requirement_fields.updated_by → users`（`:702`）：只由 `EXPECTED_COLUMN_FKS` 驗**存在**，不驗 `ON DELETE`；
  5. `system_requirement_fields.updated_on_behalf_of`：**已無外鍵**，其缺席由腳本的 `COLUMNS_WITHOUT_FK` 與 `P16` 驗（上表 (c-2) 證實 `P16` 會紅）。
  另：`("public", "project_members", "users", "a")` 以（表、被參照表）為鍵，分不出 `user_id`（`:601`）與 `invited_by`（`:604`）兩條；目前兩者皆為 `a` 故無誤判，但任一條被改成 `CASCADE` 時，腳本可能讀到另一條而通過。
- **R-07**（`OPEN-CG18-14`，`grep -n` 實查）：`verify_meta_schema.sql:99` 註解仍寫「欄位集合恰為 8 欄」，`:103` 實際斷言 9；`ci.yml:328` 寫「U18 project-meta-data 的 12 條」，`:329` 同句寫「斷言（P1-P16）」；`ci.yml:383` 寫「P1-P16；P13–P16 由 U20 加入」，而 `verify_meta_schema.sql:2-4` 寫 P13／P14 屬 U19、P15／P16 屬 U20。
- **2026-11-01 回歸加註（計畫 §九；上三項的行號為 2026-10-30 當時的行號，不回改）**：
  - **R-01／`OPEN-CG18-12` → 關閉**。已由 brain-infra A5 修正：`verify_meta_schema.sql:279-290` 的 `P17`（`:285` `IF n <> 9`）。驗證強度：**本機真實 PostgreSQL 17.7 實跑**——基準綠；刪 `updated_at` 的突變紅（訊息 `P17 FAILED: … 實際 8`）；還原綠。CI `pgvector:pg18` 首跑待該變更 push 後確認。
  - **R-02／`OPEN-CG18-13` → 關閉**。已由 brain-infra A5 修正：`run_meta_schema_migration.py:205-213`（7 條、以欄名為鍵）、`:457` 起的核對查詢。驗證強度：**本機真實 PostgreSQL 17.7 實跑**——基準 exit 0；`invited_by` 改 `ON DELETE SET NULL` 的突變 exit 1，訊息點名 `project_members.invited_by`；還原 exit 0。CI pg18 首跑待確認。
  - **R-07／`OPEN-CG18-14` → 保持開啟**。原列三處已由 A5 更正（`grep -n` 實查：`verify_meta_schema.sql:101`、`ci.yml:328-329`／`:404-405`／`:410`、`DEPLOY.md:767`／`:856-860`）。但新發現一處 A5 未涵蓋的殘留：`verify_meta_schema.sql:340` 結構類通過訊息漏列 `P17`。驗證強度：靜態 `grep` ＋ 本機實跑觀察到的 NOTICE。本站不改共用檔，已回報 conductor。
- **承接**：以 `grep` 查 `construction/functional-design/merge-blockers.md`（38 行、第 1–29 列）對 `verify_meta_schema`、`EXPECTED_FK_DELETE_ACTIONS` 皆**零命中**，未找到對應的文件同步列；依計畫「若已有對應列則引用，不重複登錄」，本站不自行編輯該檔，**交 conductor 決定是否新登一列**。

### 五、勾選重設

重開使計畫 14 格勾選全被重設。逐格依現況核對後勾回：`grep -c '\- \[x\]'` = **14**、`grep -c '\- \[ \]'` = **0**。§二 的 Step 1–8 依據同上一節「重新查驗」表（行號本輪重查：`schema_rbac.sql:568` 為 `J)` 區塊、`:12` 檔頭涵蓋清單；`run_meta_schema_migration.py:95` 的 `BLOCKS_TO_RUN = ("X", "I", "J")`；`DEPLOY.md:251` 表格 J 列、`:617` 起 §2.2.9；`ci.yml:388-393` 與 `:447` 兩處執行 `verify_meta_schema.sql`；`unit-test-instructions.md:15` 的 `psql` 指令），Step 7 依本節 §三。§八 的六項依本節 §一–§六。**無未勾項。**

### 六、收尾

- `python3 scripts/validate_repo_contract.py`：`Cloud-360 repository contract validation passed.`
- `traceability.json`：以 `python3 -I` 的 `json.load` 驗證可解析；本輪新增 `open_items` 四筆（`OPEN-CG18-12`／`13`／`14`、`R06-MUTATIONS-2026-10-30`），共 15 筆。
- 本輪未跑 Python 測試套件（未改任何程式）。

處置紀錄：2026-10-30T01:53:26Z — 計畫 §八 六項完成；DEPLOY.md 收據後僅 #24（730–738，U20 修正本單元 2.2.9 段落的失敗模式敘述、未改 DDL 事實）與 #26（2229、2239，§5.13）三個 hunk；CI run 40423375585 的 P1-P16 步驟 success；R-06 三項突變皆致紅；R-01／R-02／R-07 記為已知限制；計畫勾選 14／0。

## 2026-11-01 回歸（第 30 列落地後）

依計畫 §九 執行。本輪**未改任何應用程式、測試、SQL、腳本、workflow、部署檔或共用文件**；寫入只有本單元的 `code-summary.md`、`traceability.json` 與計畫檔的勾選字元。未 commit。

### 一、hunk 歸屬（基準：`reviewed-source-3a03dce7924a.tsv`）

收據內五檔的雜湊與 `git show HEAD:<檔>` 逐一相同（`schema_rbac.sql` `27e92ecdc5d0…`、`run_meta_schema_migration.py` `d389b302aa80…`、`verify_meta_schema.sql` `1246c5ef8e8a…`、`ci.yml` `a854442aae2a…`、`DEPLOY.md` `d9b0571c5688…`），故以 `git diff HEAD` 逐 hunk 判定。五檔**全部**有變動（現值依序 `7d9bb5d3888d…`、`5e86701cbdd4…`、`a3e1d93704fc…`、`3a9ec2206bc7…`、`8bb9f107bd52…`），無逐位元相同者。

| 檔 | hunk | 來源 | 觸及本單元 `J)`／2.2.9 的 DDL 事實？ |
|---|---|---|---|
| `verify_meta_schema.sql` | 檔頭 `:5-6`、`P5` 註解 `:101-102`、`P17` `:279-290` | brain-infra A5（第 30 列 (a)(c)） | 新增斷言，未改 DDL |
| `run_meta_schema_migration.py` | `EXPECTED_FK_DELETE_ACTIONS` `:197-213`、核對查詢 `:457` 起 | A5（第 30 列 (b)） | 只改後條件核對 |
| 同上 | `BLOCK_SENTINELS` 的 `I` 加兩個哨兵、後條件末段的 `cloud360_memory` 三項檢查 | 第 20／29 列（記憶專用角色） | 否（`I)` 區塊） |
| `schema_rbac.sql` | 檔頭 `I)` 涵蓋說明、`I)` 區塊的 `cloud360_memory` 角色與 grant | 第 20／29 列 | 否 |
| 同上 | `J)` 區塊 `project_members` 之前的純 `--` 註解 | 第 31 列 (c)(g) | 否（無 DDL／COMMENT ON 變更；A4 已註明） |
| `ci.yml` | `:328-329`、`:404-405`、`:410`（步驟名）、`:428`、`:431`、`:547` | A5（第 30 列 (c)） | 否（註解與步驟名；job `id`／`name:` 未改，`:322`、`:335`） |
| 同上 | 新步驟「Verify the memory-only role boundary (R0-R3)」 | 第 20／29 列 | 否 |
| 同上 | `tests_pg` 步驟名 | 第 33 列 (g) | 否 |
| `DEPLOY.md` | `:767`（2.2.9 結束碼語意：7 條外鍵逐欄核對）——同一 hunk 另含 `cloud360_memory` 的後條件 | A5（第 30 列 (c)）＋ 第 20／29 列 | 只改文字，與 DDL 一致 |
| 同上 | `:856-860`（17 條、`P1`–`P17` 與歸屬） | A5（第 30 列 (c)） | 同上 |
| 同上 | `:250`、`:543`、`:613` 起（I 列、grant 邊界、記憶專用角色小節） | 第 20／29 列 | 否 |
| 同上 | `:361`（2.2.7 結束碼）、`:513`（第 27 列稽核筆數）、`:1018`（2.2.10，第 31 列 (b)）、`:1128`（第 31 列 (c)(g)）、`:1244`（第 32 列 (f)）、`:1920`／`:1931`（第 34／36 列）、`:2340` | 其他列 | 否（皆在 2.2.9 之外，2.2.9 為 `:676`–`:1009`） |

**無任何 hunk 改變 `J)` 區塊的 DDL**：`schema_rbac.sql` 的 `J)` 內唯一變動是純註解。

### 二、第 30 列 (a)(b)(c) 的完整性

- **(a) 一致**：`P17` 的 N＝9（`verify_meta_schema.sql:285`）；計畫 §三.3 列 9 欄；`schema_rbac.sql:752-776` 的 `CREATE TABLE system_requirement_fields` 實為 9 欄（`id`／`system_id`／`agent_group`／`field_key`／`value`／`cleared_at`／`updated_at`／`updated_by`／`updated_on_behalf_of`）；本機真實庫 `information_schema.columns` 計數 9。
- **(b) 一致**：`EXPECTED_FK_DELETE_ACTIONS` 7 條＝`J)` 的 7 條 `REFERENCES`（`:655` project_id→projects CASCADE、`:659` user_id→users、`:662` invited_by→users、`:708` promoted_user_id→users、`:709` previous_owner_user_id→users、`:754` system_id→systems CASCADE、`:760` updated_by→users；未標 CASCADE 者皆 NO ACTION），與本機真實庫 `pg_constraint` 查得的 7 條逐條相同。`(project_members, users)` 兩條以欄名 `user_id`／`invited_by` 區分。**與 §三 的差異（非 A5 缺陷）**：§三.3 原寫 `updated_on_behalf_of INTEGER REFERENCES users (id)`，已由 U20 `[FD1]`=A／`BR47.3` 改為 `VARCHAR(64)` 且無外鍵（`schema_rbac.sql:762-764`，`P16` 驗其缺席）；§三.2 未列 U19 回補的 `cause`。故 §三 的外鍵數為 8、現行為 7，以現行為準。
- **(c) 原列殘留已清，但有一處 A5 未涵蓋**：`grep -n` 實查「8 欄」「12 條」「16 條」「P1-P16」「P1–P16」「P13–P16 由 U20」「本節的 `P1`–`P12`」「3 條外鍵」「**16**」於三檔——僅剩 `verify_meta_schema.sql:1`（「U18 的 12 條（P1–P12）」，正確歸屬）、`:101`／`:111` 與 `DEPLOY.md:685`（「原為 8 欄」，歷史說明）。**新發現**：`verify_meta_schema.sql:340` 的 `RAISE NOTICE '結構類斷言（P1／P2／P3／P5／P6／P8／P9／P12／P13／P14／P15／P16）全部通過'` **漏列 `P17`**（`P17` 位於 `:279-290`，同一個 `DO` 區塊，實跑證實會執行且會紅）。不影響閘門，但 CI log 會讓人以為 P17 沒跑。依計畫不改共用檔，**回報 conductor**，該格**不勾**。附帶觀察（非第 30 列範圍）：`DEPLOY.md:860` 「2.2.8 的 `S1`–`S12`」與 `DEPLOY.md:603` 自述「`S13`–`S15` 已擴充」不一致，屬記憶 schema 段落。

### 三、真實 PostgreSQL 驗證——**本機實跑**

- 環境：Homebrew PostgreSQL **17.7**（`/opt/homebrew/opt/postgresql@17/bin`）＋ pgvector **0.8.1**（`vector` 擴充可用，`schema_rbac.sql` 未略過任何段落）。scratchpad 下 `initdb -U postgres --auth=trust`，以 `listen_addresses=127.0.0.1`、隨機埠 `47911`、`unix_socket_directories=''` 啟動。未讀 `.env`、未連 staging／共用 DB／Redis，未觸發任何 workflow，未使用 `gh`。資料庫無密碼（trust），故無需遮罩的憑證。
- 基準（全部對 rsync 副本的檔，sha 與 repo 相同）：`schema_rbac.sql` 套用兩次 exit 0／0；`verify_meta_schema.sql` exit 0（兩則通過 NOTICE）；`run_meta_schema_migration.py`（`DATABASE_URL` 指向本機叢集）exit 0，輸出「外鍵刪除行為 7 條已逐條核對（另驗 1 條必須不存在的外鍵）」「終檢通過」。

| # | 突變（只改副本，套到新庫） | DDL 確實改變 | 結果 |
|---|---|---|---|
| M1 | 刪 `system_requirement_fields.updated_at` 欄及其 `COMMENT ON COLUMN` | 欄數 9 → 8 | **RED ✓** `verify_meta_schema.sql` exit 3：`P17 FAILED: system_requirement_fields 應有 9 欄（…），實際 8 —— 欄位集合變動須同步 run_meta_schema_migration.py 的 EXPECTED_TABLES` |
| M2 | `project_members.invited_by` 改 `REFERENCES users (id) ON DELETE SET NULL` | `confdeltype` a → n | **RED ✓** `run_meta_schema_migration.py` exit 1：`public.project_members.invited_by → users 的 ON DELETE 應為 confdeltype=a，實際 n`（同表另一條 `user_id→users` 仍為 a，證明以欄名為鍵生效）。同庫的 `verify_meta_schema.sql` 仍 exit 0——`invited_by` 的刪除行為只由腳本承擔，CI 經 U20 步驟 B／D 執行該腳本 |

- 還原後複驗：新庫 `u18_restore` 套用原副本兩次 exit 0／0、`verify_meta_schema.sql` exit 0、腳本 exit 0（7 條）。
- 清理：`pg_ctl stop -m fast` 完成；資料目錄與突變副本已刪除；`lsof -nP -iTCP:47911 -sTCP:LISTEN` 無輸出；`pgrep -fl u18pg` 無輸出。
- 限制：CI 用 `pgvector:pg18`，本機為 17.7，版本差異未驗（`OPEN-CG18-5` 不變）；本輪變更尚未 push，CI 首跑結果不存在。

### 四、Python 回歸

- 副本：`rsync -a --exclude .git` 至 scratchpad（含 frontend）。
- `tests.test_meta_schema_expectations`：`Ran 2 tests` → `OK`。
- 後端全套（`unittest discover -s tests`）：`Ran 1372 tests in 107.643s` → `OK (skipped=3)`。輸出中的 `ERROR:cloud360.*` 為受測路徑的預期 log（如 `redis_unreachable`），非測試失敗。
- repo 本體：`python3 -B scripts/validate_repo_contract.py` → `Cloud-360 repository contract validation passed.`；`python3 -B scripts/validate_env_contract.py` → `Cloud-360 environment configuration contract validation passed.`
- `.pyc`／`__pycache__`／`.hypothesis`：跑前跑後以 `stat` 列出 repo 內全部（9628 筆，含路徑、大小、mtime），`cmp` **完全相同**。副本與 hyp 目錄已刪除。

### 五、紀錄更新

- `OPEN-CG18-12`（R-01）：**關閉**——本機 PG17 實跑通過；CI pg18 首跑待確認。
- `OPEN-CG18-13`（R-02）：**關閉**——同上。
- `OPEN-CG18-14`（R-07）：**保持開啟**——原列已更正，但 `verify_meta_schema.sql:340` 漏列 `P17`。
- `traceability.json` 三筆 `open_items` 的 `text` 末尾附加加註（`severity` 欄保留原值，未刪除既有內容）；`python3 -I` 的 `json.load` 驗證可解析，`open_items` 仍為 15 筆。本檔 §四 亦附加對應加註。

### 六、勾選數（`grep -c` 實算，寫入本節前已完成勾選）

`grep -c '^- \[x\]'` = **19**、`grep -c '^- \[ \]'` = **1**。§二 Step 1–8 依現況重核後勾回（`unit-test-instructions.md:15` 的 `psql` 指令；`schema_rbac.sql:615` 起的 `J)` 區塊；`run_meta_schema_migration.py:95` 的 `BLOCKS_TO_RUN = ("X", "I", "J")`；`DEPLOY.md:676` 起的 2.2.9；`verify_meta_schema.sql` 存在且本輪實跑；`ci.yml:322`／`:335` job id／name 未改、`:415` 執行斷言檔；Step 7 有 2026-10-30 的 R-06 突變表與本輪 M1／M2；Step 8 本檔與 `traceability.json`）。§八 六格依本檔 2026-10-30 一節的 §一–§六 紀錄勾回（皆為當時已完成的歷史事實；其中「git log c6a40f9..HEAD 三檔未變」只對當時成立，現況變動由本節 §一 承接）。§九 未勾的一格為「第 30 列 (a)(b)(c) 的完整性」，理由見本節 §二 (c)。

### 七、偏離事項

1. 指示要求「發現 A5 不完整即停下回報」。發現 `verify_meta_schema.sql:340` 的 NOTICE 漏列 `P17` 後，**未修正**、該格不勾並回報；但仍完成其餘驗證——判斷依據是該殘留只影響 log 文字，不影響任何閘門判定，而其餘驗證全為唯讀或只在副本／一次性叢集上進行。若 conductor 認為應在發現當下即中止，本節 §三–§四 的結果可視為額外資訊。
2. 第一次起叢集時以 shell 變數組出執行檔路徑，被 hook 擋下（「cannot run dynamic executable」）；改為絕對路徑後正常，未繞過任何檢查。
3. 計畫 §三.3 的 `updated_on_behalf_of` 外鍵已由 U20 推翻，本輪以現行 DDL 為準比對（見 §二 (b)），未回改計畫內容。

處置紀錄：2026-11-06T22:09:46Z — 計畫 §九 完成五格、一格（第 30 列完整性）因 `verify_meta_schema.sql:340` 漏列 P17 而不勾並回報；本機 PG17.7 實跑基準綠、M1（P17）與 M2（invited_by 外鍵）皆紅、還原綠；後端 1372 測試 OK；`OPEN-CG18-12`／`-13` 關閉、`-14` 保持開啟；計畫勾選 19／1。

## 2026-11-07 第 30 列 (c) 殘留補修

依計畫 §十（使用者 2026-11-07 裁決：在本單元補修，不帶到下一站）。

### 一、改動

- `backend/scripts/verify_meta_schema.sql:340`：結構類 DO 區塊（`:40` 起、`:341` 止）的「全部通過」`RAISE NOTICE` 清單由「P1／…／P16」補為「P1／P2／P3／P5／P6／P8／P9／P12／P13／P14／P15／P16／P17」。只改這一行文字，斷言邏輯未動（`P17` 本體仍在 `:279-290`）。
- `backend/tests/test_meta_schema_expectations.py`：
  - `:14-19` 檔頭突變清單補 `M4`（「把 `P17` 從結構類 DO 區塊的『全部通過』RAISE NOTICE 清單拿掉 → 案例 3 紅」）。
  - `:104` 起新增 `test_structural_block_pass_notice_lists_every_assertion_in_the_block`（附 `@purpose`／`@given`／`@step`／`@pass`／`@story US11.1`）：以 `^DO $$ … ^END $$;` 切出各 DO 區塊，取含 `'P17 FAILED` 者（斷言恰 1 個），收集區塊內所有 `'P<n> FAILED` 編號，與同區塊「全部通過」NOTICE 全形括號內的編號集合比對相等，並斷言含 17。`'P4 SETUP FAILED` 這類非斷言訊息不被 `'P(\d+) FAILED` 命中（且不在該區塊）。

### 二、突變驗證（只在 scratchpad 副本，repo 本體未做突變）

| # | 突變 | 結果 |
|---|---|---|
| M4 | 副本 `verify_meta_schema.sql:340` 以 `sed` 把 `／P16／P17）全部通過` 改回 `／P16）全部通過` | **RED ✓** `FAIL: test_structural_block_pass_notice_lists_every_assertion_in_the_block`，`AssertionError: Items in the second set but not the first:`（`17` 只在斷言集合）；`Ran 3 tests` → `FAILED (failures=1)` |
| 還原 | 以備份覆蓋，`cmp` 與 repo 本體逐位元相同 | **GREEN ✓** `Ran 3 tests` → `OK` |

### 三、回歸

- 副本：`rsync -a --exclude .git` 至 scratchpad（含 frontend），`backend/.venv/bin/python -B`，`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. HYPOTHESIS_STORAGE_DIRECTORY=<scratchpad>/hyp-u18b`，於 `backend/` 執行。
- `-m unittest tests.test_meta_schema_expectations -v`：`Ran 3 tests in 0.003s` → `OK`。
- `-m unittest discover -s tests`：`Ran 1373 tests in 108.203s` → `OK (skipped=3)`（上一節 1372 ＋ 本節新增 1）。
- repo 本體：`python3 -B scripts/validate_repo_contract.py` → `Cloud-360 repository contract validation passed.`；`python3 -B scripts/validate_env_contract.py` → `Cloud-360 environment configuration contract validation passed.`
- repo 內快取數（`find` 計數，排除 `node_modules`）：跑前 `pyc=8576 pycache=675 hyp=377`，跑後相同（`cmp` 一致）。副本、hyp 目錄與突變備份已刪除。
- 未連任何 DB／Redis／網路，未觸發 workflow，未 commit。

### 四、§九 第 2 格 (c) 重核

以 `grep -n` 對 `verify_meta_schema.sql`、`ci.yml`、`DEPLOY.md` 重查：「P13–P16 由 U20」「本節的 P1–P12」「P1-P16」0 筆；「8 欄」3 筆（`verify_meta_schema.sql:101`、`:111` 為「原為 8 欄」的歷史敘述，`DEPLOY.md:685` 為「原 8 欄」）、「12 條」2 筆（`verify_meta_schema.sql:1` 為正確歸屬「U18 的 12 條（P1–P12）」，`DEPLOY.md:603` 為「原文寫『全部 12 條斷言』」的歷史敘述）——皆非殘留。加上 `:340` 已補 `P17`，(a)(b)(c) 皆成立，該格勾回。

### 五、紀錄更新

- `traceability.json` 的 `OPEN-CG18-14`：`text` 末尾附加「【2026-11-07 補修加註（計畫 §十）】……狀態：**關閉**」（附 `:340` 與測試 `:104` 行號），`severity` 依既有慣例保留原值；`python3 -I` 的 `json.load` 可解析，`open_items` 仍為 15 筆。
- 計畫：只把 §九 第 2 格與 §十 那一格由 `[ ]` 改為 `[x]`，其他文字未動。

### 六、勾選數（`grep -c` 實算，寫入本節前已完成勾選）

`grep -c '^- \[x\]'` = **2**、`grep -c '^- \[ \]'` = **19**。**與上一節 §六 的 19／1 不一致**：本輪開工時實測計畫內 21 格**全部**為 `[ ]`（`grep -c '^- \[x\]'` = 0），即上一節勾回的 19 格已在之後被重設（推定為 §十 加入後重新取得計畫核可時的勾選重設；本輪未查證成因）。本輪依指示只勾 §十 指名的兩格，其餘 19 格未依現況重核勾回，留待 conductor 決定。

處置紀錄：2026-11-06T23:44:01Z（UTC；台灣時間 2026-11-07）— `verify_meta_schema.sql:340` 補 `P17`；新增一則測試鎖定通過訊息與斷言編號集合一致；M4 紅、還原綠；後端 1373 測試 OK；`OPEN-CG18-14` 關閉；計畫勾選 2／19。

處置紀錄（conductor）：2026-11-06T23:49:09Z — 上一節 §六 的 19 格未勾係引擎於計畫重新核可時重設（與本檔 :215 記載的同一行為）。conductor 依 §九「收尾」的指示重核證據（`unit-test-instructions.md:15` 的 `psql` 指令、`run_meta_schema_migration.py:95`、`schema_rbac.sql:615` 的 `J)` 區塊、`ci.yml:415`、`DEPLOY.md:251`；repo 內無新增 `.pyc`／`.hypothesis`），19 格的依據與 2026-11-06T22:09:46Z 一節相同且其後只有 `:340` 訊息文字與一則新測試變動，故勾回。現況 `grep -c`：**21／0**。

## 整站重跑後的勾選回復（2026-11-08T12:28:32Z）

- 背景：2026-11-08T06:40:14Z 使用者決定重跑整個 code-generation 階段（整站關卡因審查收據失效卡死，唯一出路）。引擎在 `unit start` 時把本計畫勾選全部重設為未勾。
- 依據：本單元自上次 READY 審查後無程式改動；以 Python `hashlib` 重算上一次審查留下、與現況最吻合的收據 `reviewed-source-73848765bae2.tsv`：5 同、0 變。本輪 `REVIEW_REQUESTED` 當下引擎另會產生一份新收據，以那份為準。勾選依 HEAD 版回復（差異僅勾選字元）。
- 現況（實算）：21 勾／0 未勾。
