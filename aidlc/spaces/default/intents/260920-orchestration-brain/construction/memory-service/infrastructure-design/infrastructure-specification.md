# 基礎設施規格 — `U8 memory-service`

> **本單元的基礎設施增量是一個索引。** 其餘全部為零：零新容器、零新服務、
> 零新監聽埠、零新環境變數、零新 secret、零新依賴。
>
> 這與 `U9 memory-purge` 相反（它的交付物**就是**基礎設施），
> 也與 `U5 memory-data`（引入 pgvector image 與 Ollama 第 6 個服務）相反。
> 本檔的價值在於**逐項證明那些零**，並把唯一的那一項連帶義務寫完整。

## 〇、上游依據

| 上游 | 本檔用到它的什麼 |
|---|---|
| `nfr-design/logical-components.md` | §四 的「NFR pattern ↔ 元件」對照表——它逐字指出本單元對本站的唯一實質輸入是 HNSW 索引的四項連帶義務 |
| `nfr-design/performance-design.md` | §二 的索引設計與 §二之一 的 `enable_seqscan = off` 斷言設計 |
| `nfr-design/security-design.md` | §六（不新增連線身分）、§二（`[D1]`=A 的 OpenAPI 後果） |
| `nfr-requirements/tech-stack-decisions.md` | `NFR8.20` 的四項二元判準 |
| `schema_rbac.sql`（版控） | `I)` 區塊的既有三個索引；`run_meta_schema_migration.py` 解析 `X)`／`I)`／`J)` |
| `nfr-design/scalability-design.md` | §一 的分頁形式（offset／limit，照 `/api/auth/list` 先例）——它決定本檔 `cicd-pipeline.md §一` 第 2 項的 OpenAPI 變更內容；§三 的「只有 episodic 有保存期上界」（`D8-5`） |
| `nfr-design/reliability-design.md` | §一 的交易邊界（本檔據此判定它可在既有 `backend` job 以 SQLite 驗，不需真實 PG）；§五 的備份缺口（`N8-9`） |
| `inception/domain-design/components.md` | `MemoryStore` 的 `external_dependencies`（PostgreSQL／pgvector／Ollama／fastembed）——本檔 §三 的服務表以它為對照，確認本單元對四者皆無變更 |
| `functional-design/functional-spec.md` | §〇 的四條端點 ＋ 本站新增的建立端點，決定 OpenAPI drift 的觸發範圍 |
| `inception/contract-design/contract-summary.md` | `K-08` 的 OpenAPI 半邊（本檔 §一 的三處契約變更皆相對於它） |
| `.github/workflows/ci.yml`（版控） | 六個 job 的實際組成；OpenAPI drift 步驟在 `backend` job 的 `:289` |

## 一、Deployment

| Facet | Choice | 是否新增 |
|---|---|---|
| 計算模型 | 既有單一 FastAPI 進程內的四個模組 | **零新進程** |
| 容器 | 不新增 | **零** |
| 網路拓樸 | 四條 HTTP 端點走既有 nginx ＋ Cloudflare Tunnel 路徑；`db` 無 host port | **零新監聽埠、零新 tunnel** |
| 儲存 | 既有 `memory.memory_records`／`memory_audit_events`（`U5` 交付） | **零新表** |
| 環境設定 | 不新增變數 | **零**；`deploy/render-env.sh` 與 `deploy/.env.example` 皆不動 |
| secret | 不新增 | **零** |
| 依賴 | `requirements.txt` diff 為空 | **零** |
| **索引** | **新增一個 HNSW 向量索引** | **這是本單元唯一的基礎設施增量** |

### 1.1 `NFR8.20` 的四項判準（可機械執行）

1. `backend/requirements.txt` 的 diff 為空；
2. 本單元 diff 不含 `deploy/`、`deploy/render-env.sh`、任一 `.env.example`、`deploy/docker-compose.*.yml`；
3. `python3 scripts/validate_env_contract.py` 綠燈；
4. `gh api repos/<owner>/<repo>/actions/secrets` 的名稱集合不變。

**`LOCAL-DEV.md` 的同步義務不觸發**：`project.md` 的觸發清單為
「異動 `backend/database.py` 的 schema 補丁、`deploy/nginx.conf`、任一
`.env.example` 或 `render-env.sh`」——本單元四者皆不動。

## 二、唯一的結構變更：HNSW 索引及其四項 blocking 連帶義務

### 2.1 落點與既有環境的取得路徑

| 項目 | 內容 |
|---|---|
| 索引落點 | `schema_rbac.sql` 的 **`I)` 區塊**（`U5` 擁有的區塊） |
| 空 volume 路徑 | 整支 `schema_rbac.sql` 經 `docker-entrypoint-initdb.d` 執行 |
| **既有環境路徑** | `backend/scripts/run_meta_schema_migration.py` **解析 `I)` 區塊並執行**（`BLOCKS_TO_RUN = ("X", "I", "J")`），故索引**會被建立**，不需新腳本 |
| CI 路徑 | `memory-schema` job 套用整支 `schema_rbac.sql`（並重跑一次驗可重跑性） |

**這與 `U9` 的 seed 形成對照，寫下來以免混淆**：`U9` 的系統 actor seed
**不能**放在 `I)`，因為 `run_meta_schema_migration.py` 的輸出逐字宣告
「也不塞任何資料（契約 `K-15` 的 `observable_side_effects`）」——
故 `U9` 需要一個新腳本。**索引是 DDL 而非資料**，所以放 `I)` 完全正確、
且自動走既有的既有環境路徑。

### 2.2 四項連帶義務（全部 blocking，漏做的後果各不相同）

| # | 義務 | 漏做的後果 |
|---|---|---|
| 1 | `schema_rbac.sql` 的 `I)` 區塊新增該索引（`IF NOT EXISTS` 形狀） | 索引不存在；`NFR3.22` 的 `EXPLAIN` 斷言紅燈 |
| 2 | `DEPLOY.md` 同步（新索引寫進「這支 SQL 會建立的表／欄位」區 ＋ 驗證指令） | 違反 `project.md ## Mandated` 的 blocking 規則 |
| 3 | `run_meta_schema_migration.py` 的 `EXPECTED_INDEXES` 新增該索引 | 索引**會被建立但不被驗證**——該腳本「結束碼 0」的語意悄悄變窄而無人察覺 |
| 4 | `verify_memory_schema.sql` 新增一條斷言（索引存在、為 HNSW、opclass 正確） | `memory-schema` job 不檢查它；索引被誤刪或 opclass 改錯時無人察覺 |

**第 3 項的方向要注意**：加進 `EXPECTED_INDEXES` 而**不**加進 SQL 會讓該腳本
在一個其實正確的資料庫上 rollback；只加 SQL 而不加清單則是「不被驗證」。
兩者都要做，順序無關。

### 2.3 新斷言的編號

`verify_memory_schema.sql` 目前的斷言到 **`S13`**（`U9` 的系統 actor 那一條）。
本單元新增 **`S14`**。

**`S14` 的內容依 `nfr-design/performance-design.md §二之一`**：
`SET enable_seqscan = off` 後取 `EXPLAIN`，斷言計畫使用該 HNSW 索引。
**它必須在真實 PostgreSQL 上跑**，故落點是 `memory-schema` job
（純 psql、已有真實 PG ＋ 已套用的 `schema_rbac.sql`），不另開 job。

## 三、Infrastructure Services

| Service | Role | 本單元的變更 |
|---|---|---|
| PostgreSQL ＋ pgvector | database | **新增一個索引**；不改隔離等級、不改連線池、不新增表 |
| 既有 FastAPI 進程 | application | 新增四個模組（router／facade／service／純函式）；**不新增進程** |
| Ollama（第 6 個服務） | embedding | **不變**——本單元經 `U6 EmbeddingPort` 消費它，不直接碰 |
| nginx ＋ Cloudflare Tunnel | ingress | **不變**——新端點走既有路徑 |
| GitHub Actions | CI | 既有 `memory-schema` job 新增一條斷言；**不新增 job** |

**本單元不新增的服務類別**：cache、queue、search engine、CDN、DNS、
load balancer、secrets store、容器、監聽埠。

## 四、Shared Infrastructure

| 共用資源 | 擁有者 | 本單元的使用 | 邊界 |
|---|---|---|---|
| `memory.memory_records` | `U5`（`K-05`） | 讀寫 ＋ **新增索引** | grant 只開放 `memory` schema；**該邊界目前不是真實邊界**（`U9` 的 `[ND2]`=A 實測 `POSTGRES_USER` 即 superuser） |
| `memory.memory_audit_events` | `U5` | 寫 ＋ 讀 | 同上。`U9` 是唯一 DELETE 端 |
| `public.users` | baseline | 唯讀 | 不改 |
| 既有 `database.py` 的 engine | baseline | 沿用 | **不建第二個 engine**（`NFR6.20`） |
| `I)` 區塊 ＋ `run_meta_schema_migration.py` | `U5`／`U18` | **本單元改動 `I)` 區塊與該腳本的後條件清單** | 這是本單元對他人資產的唯一寫入 |
| 既有 FastAPI 進程 | baseline | 新增四個模組 | **無隔離**——未攔截的例外會影響同進程的其他 router（`nfr-design/logical-components.md §三之一` 已記載） |

### 4.1 本單元改動了兩個不屬於它的檔案

`schema_rbac.sql` 的 `I)` 區塊屬 `U5`，`run_meta_schema_migration.py` 屬 `U5`／`U18`。
本單元為了一個索引而改它們，**這是刻意且不可避免的**——
索引必須與表在同一個可重跑的 DDL 路徑內，否則既有環境拿不到它。

**但它意味著 `U5` 的「結束碼 0 代表什麼」這個契約被本單元擴充了**，
故第 3、4 項義務不是形式工作：它們是讓那個契約**保持誠實**的部分。

## 五、既有環境的執行順序

| # | 動作 | 前置 | 跳過的後果 |
|---|---|---|---|
| 1 | `U4` 的 `run_hierarchy_migration.py` | — | `J)` 的外鍵指向的表不存在 |
| 2 | `U5`＋`U18` 的 `run_meta_schema_migration.py`（**含本單元的新索引**） | 第 1 步 | 索引不存在 → 檢索退化為循序掃描（**功能正確、效能退化、無錯誤**） |
| 3 | `U9` 的 `seed_retention_system_actor.py` | 第 2 步 | 清除的稽核 INSERT 全部失敗 |

**第 2 步的「跳過後果」是本單元最容易被忽略的一項**：
它不會讓任何東西紅燈，只會讓 `search` 隨資料成長而變慢。

## 六、ADR-0006 四面向：本站的增量

逐格對照 `nfr-design/security-design.md §八`。**本站不改任何一格的判定。**

| 面向 | 判定（與上游一致） | 本站的基礎設施增量 |
|---|---|---|
| **IAM** | 適用 | **零基礎設施增量**：不新增資料庫角色、不新增連線身分、不改 grant。應用層的兩套模型見 `nfr-design/security-design.md §一` |
| **Encryption** | 適用，無增量 | 索引不改變儲存位置，故靜態加密（主機層 LUKS）的前提不變；四條端點走既有 TLS 路徑 |
| **Network exposure** | 適用，零基礎設施增量 | 新端點**不新增監聽埠**（既有 FastAPI 進程的新路由）；`db` 維持無 host port |
| **Audit logging** | 適用 | **零基礎設施增量**——稽核寫入既有表，日誌走既有容器 stdout。但 `[D1]`=A 之後日誌是枚舉偵測的唯一面（見 `monitoring-design.md §三`） |

### PBT：**N/A（非豁免）**，與上游一致

ADR-0006 點名三個落點，本單元不是其中任何一個。
`NFR3.24` 的純函式有 PBT 落點但那不是 hard constraint 的對象（`D8-3`）。
