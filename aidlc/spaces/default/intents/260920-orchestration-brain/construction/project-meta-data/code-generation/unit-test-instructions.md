# 測試指示 — `U18 project-meta-data`

> **本單元不寫 Python 測試。** 與 `U5` 同理：既有測試在
> `backend/tests/helpers.py` 換掉驅動、改走 in-memory SQLite，而本單元要驗的是
> **PostgreSQL 的約束、外鍵缺席、partial index 與 CASCADE 行為**——
> SQLite 對這些的語意不同（外鍵預設關閉、`ON DELETE` 行為需 `PRAGMA`、
> 無 partial index 的同等查詢計畫）。在 SQLite 上「通過」不構成任何保證。
>
> 驗證載體是 CI 的 `memory-schema` job（真實 `pgvector/pgvector:pg18`）
> 新增的一個步驟；斷言寫成**純 SQL**，不經 Python。

## 〇、確切的執行指令（本單元 only，contract 要求的 runner readiness）

```bash
psql -h localhost -U postgres -d cloud360 -v ON_ERROR_STOP=1 \
  -f backend/scripts/verify_meta_schema.sql
```

**這條指令必須在第一個測試步驟之前可執行**。brownfield 故只需驗證既有載體：
`memory-schema` job 已提供 PG service container 與已套用的 `schema_rbac.sql`，
前置條件已滿足，不需 bootstrap 任何新執行器。

**範圍只限本單元**：單一檔案路徑，不是全域指令。
`U5` 的 `verify_memory_schema.sql` 是另一個檔、另一條指令，兩者互不重跑。

## 一、斷言清單（`P1`–`P12`，全部純 SQL）

每條不成立即 `RAISE EXCEPTION`，使 psql 非零碼結束、job 紅燈。
`standard` 策略要求每個 component 5–8 個測試；本單元是三張表（三個 component），
12 條斷言分佈為 4／4／4，落在區間內。

### A 群——`project_members`（`BR1.1`／`BR2.1`／`[ND1]`=A）

| id | 斷言 | 規則 |
|---|---|---|
| `P1` | 表存在於 `public`，欄位集合**恰為** 6 欄 | `entities.md` ＋ §三之一 |
| `P2` | `joined_at` 為 **NOT NULL** | `BR1.1` |
| `P3` | `project_id` 的外鍵 `ON DELETE` 行為為 **CASCADE**（查 `pg_constraint.confdeltype = 'c'`） | `[ND1]`=A |
| `P4` | **行為面**：刪除一個 `projects` 列後，其 `project_members` 列**一併消失**，且 `delete_project` 路徑不會因外鍵而失敗 | `[ND1]`=A／`security-design.md §一之三` |

> `P2` 的失敗模式是**靜默**的：`joined_at` 可為 null 時自動改選在空值上無序，
> 每次選出不同人而沒有任何錯誤（`BR1.1` 的 `violation_behaviour` 逐字）。

### B 群——`reselection_events`（`BR1.2`／`[ND1]`=A／`FR12.4b`）

| id | 斷言 | 規則 |
|---|---|---|
| `P5` | 欄位集合**恰為** 8 欄，且 `promoted_user_id`／`previous_owner_user_id`／`previous_role`／`new_role`／`occurred_at` **都在其中** | `FR12.4b`（誰／何時／對誰／舊角色／新角色）＋ `AC12.2.2` |
| `P6` | **`P-FK0`**：本表對 `projects` **沒有任何外鍵** | `[ND1]`=A |
| `P7` | **`P-SURV`**：插入一列 → 刪除其 `projects` 列 → 該稽核列**仍然存在** | `[ND1]`=A（行為面） |
| `P8` | `ix_reselection_events_unack` 存在**且為 partial**（`pg_indexes.indexdef` 含 `WHERE`） | `security-design.md §四之二` |

> `P6` 與 `P7` **缺一不可**：`P6` 驗手段（沒有外鍵）、`P7` 驗目的（稽核存活）。
> 只有 `P6` 紅而 `P7` 綠表示 `P7` 寫錯了。
>
> **`P7` 的前置條件**：被刪的 `projects` 列必須是**非預設**專案且**底下無系統**，
> 否則紅燈的原因會是 `U4` 既有的兩道守門（`hierarchy_service.py:153`／`:156`）
> 而不是外鍵。斷言須自行構造符合條件的列。
>
> `P8` 若只驗「索引存在」會漏掉 partial 條件被拿掉的情形——而那會讓索引大小
> 由「目前未確認數」變成「歷來總數」，失敗模式是效能而非正確性，不會有人發現。

### C 群——`system_requirement_fields`（`BR1.3`／`BR1.4`／`BR2.2`）

| id | 斷言 | 規則 |
|---|---|---|
| `P9` | `value` 為 **nullable**；`updated_by` 為 **NOT NULL** | `BR1.3` ＋ `K-17` 的 `clear_field` |
| `P10` | **三態可區分**：插入「已填」（`value` 有值、`cleared_at` NULL）成功；插入「清空」（`value` NULL、`cleared_at` 有值）成功；插入「`value` 有值而 `cleared_at` 也有值」**被 CHECK 拒絕** | `BR1.4` |
| `P11` | `UNIQUE (system_id, agent_group, field_key)` 存在——插入重複三元組被拒 | `entity_constraints`（本站把它由兩欄擴為三欄，理由見下） |
| `P12` | `system_requirement_fields` 的 COMMENT **非空**且含 `[UG:G9]` 的三個關鍵詞 | `BR2.2` |

> **`P11` 的兩欄 vs 三欄**：`entities.md` 的 `entity_constraints` 寫
> 「同一系統內同一欄位名至多一列」（兩欄）。本單元採**三欄**
> （`system_id` ＋ `agent_group` ＋ `field_key`），理由：`K-17` 的 `read_fields`
> 回傳「按 `agentGroup` 分組；每組含 `fieldKey`」，故同一個 `fieldKey` 字串
> 在不同 agent 組下是**不同的欄位**；兩欄鍵會讓兩組共用的欄位名互相排擠。
> 這是 `nfr-design` 審查 `R-02`（Minor）要求說明的那一點，在此明寫為**刻意加寬**
> 而非筆誤，並指派 `entities.md` 的回補（與 `OPEN-ND18-1` 同一批）。
>
> `P12` 驗的是 `BR2.2`，而該條的 `violation_behaviour` 逐字說：不寫下來的話，
> 「資料庫裡有、畫面上看不到」的列會被下一個人**當成髒資料清掉**
> ——被清掉的是使用者曾經填過的值。故 COMMENT 是防呆機制，不是文件義務，
> 因此它需要一條斷言。

## 二、不寫的斷言（附理由，不留空白）

- **不為 `BR3.1`（既有環境建立須大聲失敗）寫 CI 斷言。** 它約束的是**腳本的
  錯誤處理**，而驗它需要在 CI 內刻意製造一個會失敗的 DDL 再確認退出碼非零。
  **本輪改以突變驗證涵蓋**（見 §三的 `N5`），不另立斷言。
- **不為 `BR3.2`（`schema_rbac.sql` 只在空 volume 執行）寫斷言。** 它是**誠實宣告**
  （`violation_behaviour` 逐字「不適用」），沒有可失敗的行為。
- **不為 `BR3.3`（兩次 blocking 同步）寫 SQL 斷言。** 它約束的是兩份文件的內容，
  不是資料庫狀態；由 `repo-contract` job 的既有檢查與人工核對承接。
- **不寫 property-based 測試。** ADR-0006 的 PBT 對本單元判 **N/A（非豁免）**
  ——本單元沒有任何函式。失效條件已指明：`U19` 的自動改選挑選函式應為不讀 DB
  的純函式（`unit-of-work.md:448`），PBT 在**那裡**適用，可失敗的性質是
  **排列不變性**；本單元的 `BR1.1` 是其資料層前提。
- **不寫 Python 測試、不建 ORM model。** 見檔頭與 `tech-stack-decisions.md §二`。

## 三、突變驗證

對 SQL 斷言的突變方式是**改 DDL 再重跑斷言**，確認紅燈後還原。

| # | 突變 | 應該紅的斷言 |
|---|---|---|
| `N1` | 把 `joined_at` 改為 nullable | `P2` |
| `N2` | 把 `project_members.project_id` 的 `ON DELETE CASCADE` 改為 `RESTRICT` | `P3` ＋ `P4` |
| `N3` | 為 `reselection_events.project_id` **加上**指向 `projects` 的外鍵 | `P6` ＋ `P7` |
| `N4` | 拿掉 `ix_reselection_events_unack` 的 `WHERE acknowledged_at IS NULL` | `P8` |
| `N5` | 在獨立腳本中讓某條 DDL 失敗（例如引用不存在的表） | **腳本退出碼非零**（`NFR8.3`；非斷言，驗的是腳本自身） |
| `N6` | 移除三態的 CHECK | `P10` |
| `N7` | 把唯一約束由三欄改為兩欄 | `P11` |
| `N8` | 刪掉 `system_requirement_fields` 的 COMMENT | `P12` |
| `N9` | 把 `reselection_events` 的 `promoted_user_id` 欄位移除 | `P5` |
| `N10` | 把某個 `CREATE TABLE IF NOT EXISTS` 改成 `CREATE TABLE` | 既有的「第二次套用」步驟 |

**`N2` 與 `N3` 要同時看兩條**：結構斷言與行為斷言必須一起紅。
只有結構紅而行為綠，表示行為斷言寫錯了（它應該在有外鍵時因級聯或拒絕而失敗）。

**每一項突變都要先確認 DDL 真的改變了。** `U5` 的 `M1` 突變本身曾是 no-op
（`SET search_path` 對已帶 `memory.` 前綴的敘述無效），使「測試沒抓到」
實際上是「突變沒發生」。本輪對每個突變都先以 `psql` 查一次改動後的
`information_schema` 狀態，確認與改動前不同，才判讀斷言結果。

## 四、覆蓋率

`org.md` 宣告的 80% line coverage 對本單元**無量測對象**——零 Python／TS 程式碼
（唯一的程式檔是遷移腳本，而它的驗證是執行它本身）。
如實記載：本單元以**斷言數 ÷ 可觀察行為數**替代，12 條斷言涵蓋
三張表的全部約束與兩條行為路徑（CASCADE 連帶刪除、稽核存活）。
`team.md` 已記載本 repo **完全沒有覆蓋率量測機制**，故此處不宣稱任何百分比。
