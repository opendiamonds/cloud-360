# 測試指示 — `U5 memory-data`

> **本單元不寫 Python 測試。** 契約 `K-05` 的 `verification.why_not_existing_tests`
> 逐字：既有測試改走 in-memory SQLite，而 **SQLite 沒有 schema 概念**
> ——現有測試基礎設施**對本契約沒有任何驗證路徑**。
>
> 驗證載體是 `N-2`：一個對真實 PostgreSQL 執行的 CI job。斷言寫成**純 SQL**
> （`backend/scripts/verify_memory_schema.sql`），不經 Python，故也不受
> `tests/helpers.py` 的驅動替換影響。

## 一、斷言清單（`S1`–`S12`，全部為純 SQL）

每一條都以「不成立即 `RAISE EXCEPTION`」的形式撰寫，使 job 直接紅燈。

### A 群——schema 隔離與可重跑（`BR1.1`／`BR1.3`）

| id | 斷言 | 規則 |
|---|---|---|
| `S1` | `memory` schema 存在，且兩張表的 `table_schema` 皆為 `memory`（**不是** `public`） | `BR1.1` |
| `S2` | **第二次**套用 `schema_rbac.sql` 不報錯，且套用後兩表的欄位數不變 | `BR1.3` |
| `S3` | `vector` 擴充存在（`CREATE EXTENSION` 可用），且 `memory_records.embedding` 的型別為 `vector`、維度為 **1024** | `BR3.2` |

> `S2` 是本單元**唯一需要跑兩次**才驗得到的斷言——「可重跑」在只跑一次時
> 永遠是真的。job 因此必須套用兩次（見計畫 §四）。

### B 群——欄位與約束（`BR2.x`／`BR3.x`／`BR4.1`）

| id | 斷言 | 規則 |
|---|---|---|
| `S4` | `memory_records` 的欄位集合**恰為** 9 欄（`memoryId`／`kind`／`ownerUserId`／`visibilityScope`／`content`／`embedding`／`embeddingModel`／`createdAt`／`expiresAt`）——多一欄或少一欄皆紅 | `entities.md` |
| `S5` | `embeddingModel` 為 **NOT NULL**；`embedding` 為 **nullable** | `BR3.1`／`BR3.3` |
| `S6` | `kind` 的 CHECK 只允許 `semantic`／`procedure`／`episodic`——插入第四個值被拒 | `entities.md` |
| `S7` | **`kind = 'episodic'` 時 `expiresAt` 不得為 NULL**（條件必填 CHECK）：插入 `episodic` ＋ NULL 被拒；插入 `semantic` ＋ NULL 成功 | `BR4.1` |

> `S7` 是本群最重要的一條。`BR4.1` 的 `violation_behaviour` 已寫明失敗模式：
> 清除作業**依 `expiresAt` 選列**，NULL 永遠不會被選中，所以漏填的後果是
> **永久保留且沒有任何跡象**。這條 CHECK 是唯一能在資料層擋住它的機制。

### C 群——稽核表與 `DG-1` 的處置（`BR2.1`／`BR2.2`／`BR2.3`／`NFR7.2`）

| id | 斷言 | 規則 |
|---|---|---|
| `S8` | `memory_audit_events` **對 `memory_records` 沒有任何外鍵**（查 `information_schema.table_constraints`，`FOREIGN KEY` 中不得出現指向 `memory_records` 者） | `BR2.1`／`DG-1` |
| `S9` | 該表**不含** `content`、不含 `embedding` 欄位 | `BR2.2` |
| `S10` | `action` 的 CHECK 允許且僅允許 `deleted_by_user`／`purged_by_retention`／`scope_changed` | `BR2.3` |
| `S11` | **刪除一列 `memory_records` 之後，其 `memory_audit_events` 列仍然存在**（`DG-1` 處置的行為面斷言） | `BR2.1` |
| `S12` | `memory_audit_events` 有 **`occurredAt` 的索引**（查 `pg_indexes`） | `NFR7.2`／`OPEN-ND5-1` |

> `S11` 是把 `DG-1` 的決定寫成**可失敗的行為斷言**，而非只檢查 schema 形狀
> ——沒有外鍵只是手段，稽核存活才是目的。
>
> `S12` 的失敗模式是**效能而非正確性**（全表掃描），所以它是**唯一一條
> 若沒有這個斷言就永遠不會被發現**的項目。`U4` 對自己的變更紀錄表踩過同一個洞。

## 二、不寫的斷言（附理由，不留空白）

- **不為 `BR1.2`（grant 邊界）寫 CI 斷言。** grant 的驗證需要**第二個資料庫角色**
  並以該角色連線嘗試越界操作，而 `N-2` 的 service container 只有 superuser。
  做得到但需要在 job 內建角色與切換連線——**本輪不做**，記為 `OPEN-CG5-1`。
  **這是本單元最大的驗證缺口**：`BR1.2` 是資料庫層的唯一邊界，而它沒有被驗證。
- **不為 `BR3.1`（檢索只比對同一 `embeddingModel`）寫斷言。** 它約束的是**查詢**
  而非 schema，而本單元不交付任何查詢——落點 `U8`。
  但 `S5` 已確保 `embeddingModel` 為 NOT NULL，即該過濾所需的資料前提存在。
- **不為 `BR1.3` 以外的「誠實宣告」類規則寫斷言**（`BR3.3`／`BR4.2`）：
  `violation_behaviour` 為「不適用」者沒有可失敗的行為。
  （`BR3.3` 的資料面已由 `S5` 的 nullable 斷言覆蓋。）
- **不寫 property-based 測試。** ADR-0006 的 PBT 對本單元判 **N/A（非豁免）**
  ——本單元沒有任何函式。
- **不寫 Python 測試。** 見檔頭。

## 三、突變驗證

對 SQL 斷言的突變方式是**改 DDL 再重跑 `N-2`**，確認斷言紅燈後還原。

| # | 突變 | 應該紅的斷言 |
|---|---|---|
| `M1` | 把兩張表建在 `public` 而非 `memory` | `S1` |
| `M2` | 把 `vector(1024)` 改成 `vector(768)` | `S3` |
| `M3` | 把 `embeddingModel` 改為 nullable | `S5` |
| `M4` | 移除 `kind` 的 CHECK | `S6` |
| `M5` | 移除「`episodic` 則 `expiresAt` 必填」的 CHECK | `S7` |
| `M6` | 為 `memory_audit_events.memoryId` 加上指向 `memory_records` 的外鍵 | `S8` ＋ `S11` |
| `M7` | 在稽核表加一個 `content` 欄位 | `S9` |
| `M8` | 移除 `occurredAt` 的索引 | `S12` |
| `M9` | 把某個 `CREATE TABLE IF NOT EXISTS` 改成 `CREATE TABLE` | `S2` |

**`M6` 要同時看兩條**：`S8` 驗 schema 形狀、`S11` 驗行為。只有 `S8` 紅而
`S11` 綠會表示 `S11` 寫錯了（它應該在有外鍵時因級聯而失敗）。

**每一項突變都要先確認 DDL 真的改變了**（例如 `M9` 若該表已存在則
`CREATE TABLE` 會直接報錯而非讓 `S2` 紅——那是**不同的**失敗，要分辨）。
`embedding-port` 那輪有一個突變本身是 no-op，使「測試沒抓到」其實是
「突變沒發生」。
