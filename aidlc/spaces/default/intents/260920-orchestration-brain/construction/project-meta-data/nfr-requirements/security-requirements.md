# 安全需求 — `U18 project-meta-data`

> 本站承接 `functional-design` 的 11 條規則（`BR1.1`–`BR3.3`）與 4 項開放缺口。
> **不複寫那 11 條**（`team.md` 的單一真實來源）。本檔只記**本站新定案**的事。

## 〇、上游依據

| 上游產出 | 本站用到它的什麼 |
|---|---|
| `rules.md`（本單元 functional-design） | `BR3.1`（既有環境須大聲失敗——**本站的定案直接處置它**）、`BR3.2`（空 volume 限制）、`BR3.3`（兩次 blocking 同步）、`BR2.2`（COMMENT 義務） |
| `functional-spec.md`（本單元） | §三 對 `database.py` 的實讀結果；`OPEN-P1`–`OPEN-P4` |
| `entities.md`（本單元） | 三張表的欄位與三態模型 |
| `contract-summary.md` | 契約 `K-15` 的 `authorization_responsibility`（「**無**——DDL 不經使用者授權」）、`blocking_sync`、`known_constraint_inherited_from_K04` |
| `requirements.md` | `NFR8`（新增元件的部署設定完整性）、`FR12.4`／`FR12.4c` |
| `unit-of-work.md` | `:443`／`:444` 的兩項注意事項；`:715` 的交付物清單 |
| `technology-stack` | 既有技術棧記載於 `project.md ## Tech Stack`（PostgreSQL）與 `team.md ## Testing Posture`；本單元零新技術 |

## 一、本站的核心定案：`OPEN-P1` 一次性解決（跨八張表）

**使用者裁決 `[P1]`=A（2026-10-06）：沿用 `U4` 先例——一支獨立腳本。**

### 為什麼在本站定案，而不是再記一次開放項

這個缺口**已經被記載兩次**（`U5` 的 `OPEN-M5`、`U18` 的 `OPEN-P1`），而本 intent
累積的新物件已達 **八張表 ＋ 一個 schema**：

| 單元 | 新物件 | 狀態 |
|---|---|---|
| `U4 hierarchy-data` | `projects`／`systems`／`diagram_change_records` | **已交付**，且已有獨立腳本 |
| `U5 memory-data` | `memory` schema ＋ `memory_records`／`memory_audit_events` | 已交付 DDL，**無既有環境路徑** |
| `U18 project-meta-data` | `project_members`／`reselection_events`／`system_requirement_fields` | 本單元，**無既有環境路徑** |

`schema_rbac.sql` 只掛在 `/docker-entrypoint-initdb.d/`，故既有的 `192.168.10.10`
**一張都拿不到**。「如實揭露」重複八次會退化成逐站免責——每個單元都說了，
而缺口一次都沒被處理。

### 定案內容

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR8.2`** | 一支獨立腳本建立 `U5` ＋ `U18` 的**全部**新物件（`memory` schema ＋ 五張表及其索引、約束、COMMENT、grant） | 腳本存在、可在 `backend/` 下以 `DATABASE_URL` 指向目標庫執行 |
| **`NFR8.3`** | 該腳本**大聲失敗**：任一 DDL 失敗即以非零碼結束 | 以 `sys.exit(非零)` 或未捕捉的例外結束；**不得**沿用 `_ensure_*` 的 warning-and-continue |
| **`NFR8.4`** | **不動啟動路徑**（`database.py` 不新增補丁） | `database.py` 的 diff 為空 |
| **`NFR8.5`** | `DEPLOY.md` 記載執行步驟與驗證指令 | 該節存在且含 `psql` 驗證 |

### 選 A 而非 B／C 的理由（逐項，非偏好）

1. **與已交付的 `U4` 完全同形。** 部署者已經要跑一支腳本
   （`run_hierarchy_migration.py`，`DEPLOY.md` 2.2.7），再跑一支是**同類動作**，
   不是新的運維概念。
2. **不動啟動路徑，故零重啟迴圈風險。** 選項 B（啟動補丁 re-raise）在
   `restart: unless-stopped` 之下會讓任何建表失敗變成**重啟迴圈**
   ——而 `DEPLOY.md` 已為 vector 擴充記過同形風險，且重啟迴圈比「少幾張表」更難診斷。
3. **無資料遷移，故不需要那個尚無承載者的靜止窗口。**
   `U4` 記過「應用不得在遷移期間接流量」（`U4-V6`／`S-9`），而該有序窗口
   在現行 `deploy.yml`（單一 `up -d --build`）下**尚無承載者**。
   `U5`／`U18` 的五張表加一個 schema **皆為全新、沒有既有資料要搬**
   （契約 `K-15` 的 `observable_side_effects` 逐字「**不含任何資料寫入**」），
   所以這個在 `U4` 時很棘手的前置條件**對本批不適用**。

### 誠實的代價

**仍是手動步驟——忘了跑就沒有表。** 但失敗很明顯：`U19`／`U20` 的任何查詢
立即報 `relation does not exist`，不是靜默降級。
相較之下選項 B 的失敗（重啟迴圈）更難診斷，選項 C 要維護兩套機制。

**`OPEN-P5`**：`deploy.yml` 不呼叫任何遷移腳本（`U4` 的也沒被呼叫），
故「部署後有沒有人去跑」沒有任何機械保證。這一點對 `U4` 已經成立，
本定案**沒有讓它變好也沒有變壞**，但累積的腳本數從一支變兩支。

## 二、ADR-0006 四面向：本站的增量

| 面向 | 本站的增量 |
|---|---|
| **IAM** | 無增量。契約 `K-15` 逐字「DDL 不經使用者授權」。**但須寫明**：本單元交付 per-project 授權的**資料基礎**，`BR1.1`（`joined_at` 非空）間接影響授權正確性——改選選錯人等於把專案管理權給錯人 |
| **Encryption** | **不適用**。三張表無憑證、無 token、無金鑰；`value` 是架構假設（SLA／TPS／預算），非個人機敏資料。**與 `U5` 的差別**：那裡的 episodic memory 是 by-user 對話歷程，故 encryption 適用；本單元不是 |
| **Network exposure** | **不適用**。零端點、零進程、零監聽埠。**本站的定案也不新增**——獨立腳本是手動執行的 CLI，不是服務 |
| **Audit logging** | **適用**。`cleared_at`（清空可稽核）、`updated_on_behalf_of`（代寫溯源）、`reselection_events`（改選事件本身即稽核）。**已知缺口**：拒絕事件不留痕跡（`OPEN-P4`，屬 `U19` 的 `H-8`） |

**PBT 判定：N/A（非豁免）**——本單元是 DDL，無函式。
**失效條件已指明**：`U19` 的自動改選挑選函式應為不讀 DB 的純函式
（`unit-of-work.md:448`），PBT 在**那裡**適用，真正可失敗的性質是**排列不變性**
（`ORDER BY joined_at` 在時間戳相同時無穩定順序）——而本單元的 `BR1.1`
正是讓那個性質可被驗證的資料層前提。
