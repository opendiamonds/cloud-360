# Code Generation 問題檔 — `U5 memory-data`

## 計畫摘要（供 Plan Approval 判讀）

本單元是 `spec`：交付 **記憶獨立 schema ＋ grant ＋ pgvector `vector(1024)`**。
**零應用程式碼、零端點、零畫面。**

### 開工前查證推翻了一項上游未決前提（好消息）

**`OPEN-N5-3` 已解決且已就緒**：`deploy/docker-compose.deploy.yml:40` 與
`docker-compose.test.yml:51` **皆為 `pgvector/pgvector:pg18`**；該檔 `:36-39`
的註解逐字「PG 18 + pgvector. The `vector` type must exist before any table
declaring a `vector(1024)` column is created」。
`U1 brain-infra` 已處理——**不需換 image、不需改任何部署設定**。

### 要寫的四個檔案

| # | 檔案 | 內容 |
|---|---|---|
| 1 | `schema_rbac.sql` | 新增一個區塊：`memory` schema ＋ 兩表 ＋ 四條 CHECK ＋ **`occurredAt` 索引** ＋ grant ＋ COMMENT |
| 2 | `DEPLOY.md` | 兩張新表的說明、`psql` 驗證指令、**主機磁碟加密狀態**（`NFR6.1`） |
| 3 | `.github/workflows/ci.yml` | **`N-2`**：新 job，`pgvector/pgvector:pg18` service container，套用 schema **兩次**後執行 SQL 斷言 |
| 4 | `backend/scripts/verify_memory_schema.sql` | 12 條純 SQL 斷言（`S1`–`S12`） |

### 兩個與 `U7` **相反**的決定

| # | 決定 | 理由 |
|---|---|---|
| 1 | **不建 ORM model** | `U7` 建了，因為 SQLite 測試路徑需要它。**本單元恰恰相反**：契約 `K-05` 逐字說 **SQLite 沒有 schema 概念**，那條路徑對本契約**根本不可用**。建 model 不會讓它可測，只會把兩表放進 `Base.metadata` 使**每個**既有測試都嘗試建立它們（SQLite 會把 `memory.memory_records` 當含點的表名），並重演 `U7` 踩過的「改變建表權威」那個洞——而這次沒有任何好處。讀寫屬 `U8`，**它**可以在需要時建 model |
| 2 | **不碰 `backend/tests/`，不寫任何 Python 測試** | 驗證全靠 `N-2` 對真實 PG 執行純 SQL 斷言。這是契約指定的載體，不是退讓 |

### 兩件要請你注意的事

1. **`N-2` 必須套用 `schema_rbac.sql` 兩次。** `BR1.3` 要求可重跑，而
   「可重跑」**只跑一次時永遠是真的**——不跑第二次就等於沒驗。
2. **`BR1.2`（grant 邊界）本輪不會被驗證**，這是本單元最大的驗證缺口。
   驗它需要第二個資料庫角色並以該角色嘗試越界，而 `N-2` 的 service container
   只有 superuser。**做得到但本輪不做**，會記為 `OPEN-CG5-1`。
   `BR1.2` 是資料庫層的**唯一**邊界，所以這個缺口值得你知道。

### 選項

| 選項 | 內容 |
|---|---|
| **Approve Plan** | 四個檔案與兩個決定如上，開始實作。 |
| **Request changes** | 某項要改。例如若你認為 `BR1.2` 的 grant 驗證本輪就該做（在 `N-2` 內建第二個角色並切換連線），告訴我，我把它加進計畫再重取核可。 |

## Plan Approval

[Approval Fingerprint]: sha256:v3:6f2eedefc7c24ee4f10762efedfe82435e719479806d05eb15fc12e0c357b357
[Planned Source]: 6e7201c6be748f4e819edcdfb068dced842086b01843847e43192749943ad5b3

[Answer]: Approve Plan
