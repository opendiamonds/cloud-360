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
