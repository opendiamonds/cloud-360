# Tech Stack Decisions — `brain-infra`（U1）

<!-- Stage: nfr-requirements（Construction 3.2）· Unit: brain-infra · kind: packaging -->

## 這份檔在做什麼

列出 `brain-infra` 要引入或更動的每一項技術選擇，以及**為什麼是它**。
既有堆疊不在此重述——它在 `aidlc/spaces/default/codekb/chiton/technology-stack.md`
（基準 `dc4b687`）。本檔只記**本單元改動的部分**與其理由。

本檔可獨立閱讀。

**讀進來的上游**：`technology-stack.md`（codekb，基準 `dc4b687`）、
`contract-summary.md`（K-01 的 `variables` 與 `images_and_services`）、
`requirements.md`（`C-T5`、`C-T6`、NFR4／NFR6／NFR8／NFR9）。

`functional-spec.md` 與 `rules.md` 對本單元**不存在**——`functional-design` 的
`produces_kinds` 不涵蓋 `packaging`，該 stage 對 `brain-infra` 整站 kind-vacuous、
未執行。理由與後果詳見 `security-requirements.md` 同名段落。

---

## 一、既有堆疊裡與本單元相關的事實（不重新決定）

| 項目 | 現值 | 證據 |
|---|---|---|
| Staging 服務數 | **4**（`db`／`backend`／`frontend`／`cloudflared`） | `deploy/docker-compose.deploy.yml:11–93` |
| db image | `postgres:16-alpine`，掛具名 volume `cloud360_db` | 同上 `:13`、`:19–20` |
| CI 測試 stack 的 db | `postgres:16-alpine`，**無具名 volume、無 host port** | `deploy/docker-compose.test.yml:15` 與其檔內註解 |
| **本機 dev db** | **`postgres:15-alpine`——與部署差一個主版本** | `[讀]` repo 根 `docker-compose.yml:3` |
| `schema_rbac.sql` 的交易邊界 | **單一交易**：`:24` `BEGIN;` → `:633` `COMMIT;`（全檔 644 行） | 本輪實查 |
| Python | 3.12（`python:3.12-slim`） | `backend/Dockerfile:6` |
| 部署設定唯一產生點 | `deploy/render-env.sh`（deploy 與 rollback 兩個 job 都呼叫） | `project.md ## Mandated` |
| Redis 在本 repo 的現況 | **零基礎設施用途**——13 個 `redis` 字串命中全部是 WA 規則文字、lens JSON、drawio 模板、prompt 內的服務清單 | `technology-stack.md`「本 intent 會引入的新技術面」 |
| 獨立 PostgreSQL schema 的現況 | **零前例**：全樹無 `CREATE SCHEMA`、無 `search_path`、無 `__table_args__ schema` | 同上 |
| `CREATE EXTENSION` 的現況 | 全樹命中 **0**（`schema_rbac.sql`、`schema.sql`、`backend/` 皆搜過） | 本輪實查 |

---

## 二、本單元的技術選擇

### 2.1 Redis（新增第 5 個服務）

| 欄位 | 值 |
|---|---|
| **選擇** | Redis 作為 compose 的第 5 個服務 |
| **為什麼需要它** | `NFR4` 逐字要求 session 與工作狀態「**一律放 Redis，不得放行程記憶體**」。這不是本站的選擇，是上游已核可的決定 |
| **暴露面** | 不得 `publish port`，僅限 compose 內部網路（`NFR8.7`） |
| **憑證** | `REDIS_PASSWORD`，`required: true`、無 fallback、不得含 `$`、以 `openssl rand -hex 32` 產生（`NFR4.1`）。**擋阻機制須由本單元擴充，不是既有保證**——`render-env.sh:59` 的 `$` 名單與 `:44–49` 的必填檢查都是固定名單，皆不含 `REDIS_PASSWORD` |
| **最小權限**（本輪新增，承接 `S-3`） | **不得以 Redis 的預設 `default` 使用者連線**；須以 ACL 建立專用使用者，指令與 key pattern 限於本應用所需。理由：單一 `requirepass` 走 `default` 取得的是 full command access（含 `FLUSHALL`／`CONFIG`／`KEYS`），而 `requirements.md:451` 逐字要求「Redis 連線憑證須最小權限」。可測判準見 `security-requirements.md` `NFR4.1(b)` |
| **持久化**（`[N5]`=A） | **AOF ＋ 具名 volume** |
| **為何選 AOF 而非不持久化** | 上游 `NFR4` 的可測不變量只寫了「重啟 **backend** 後可還原」。不持久化時，Redis 自己重啟會清掉全部 session，而**那句不變量仍然通過**——測試不會紅，使用者的對話卻沒了。AOF 把該不變量的真實含意補上 |
| **為何不選 RDB 快照** | RDB 在崩潰時可能丟失最近幾分鐘的 session，而「大部分情況下會還原」這種不變量**無法寫成二元可判的驗收條件**。本 repo 的測試底線要求可判定 |
| **代價** | 多一個具名 volume；AOF 寫入有微量 fsync 成本。具體 `appendfsync` 值本站不預選（屬 `U10 session-store` 與 `nfr-design`），**但受 `NFR4.2` 的兩條約束**：① `appendfsync` 的選值不得使 `NFR3` 的首字 P50 ≤ 2 秒預算失守；② **自動 AOF rewrite 不得關閉**——TTL 回收的是 keyspace，**AOF 檔本身要靠 rewrite 才會縮**，關掉它會在單機 staging 上把磁碟寫爆 |
| **版本策略** | 釘選到明確的 minor（如 `redis:<major>.<minor>-alpine`），**不使用 `latest`**。理由：本 repo 已有一個反例——`cloudflare/cloudflared:latest` 未釘選（`technology-stack.md` 明記），部署結果因此不可重現 |

### 2.2 Ollama（新增第 6 個服務，條件式）

| 欄位 | 值 |
|---|---|
| **選擇** | Ollama 作為第 6 個服務，執行 `bge-m3` 產生 1024 維 embedding |
| **為什麼需要它** | `EmbeddingPort` 的 `ollama` 實作（`domain-design` ADR-008）需要一個本機推論端點 |
| **暴露面** | 不得 `publish port`，僅限 compose 內部網路（`NFR8.8`） |
| **認證**（`[N4]`=A） | **無**。Ollama 的 HTTP API 原生無認證機制；網路隔離是唯一控制。此決定與其前提破壞後的後果逐字記於 `security-requirements.md` `NFR8.8` |
| **volume** | 模型快取 volume（`bge-m3` 約 1.2GB） |
| **條件式**（`[N3]`=A） | 記憶體餘裕實測不足時，改 `EMBEDDING_PROVIDER=fastembed`，**本服務不部署** |
| **為何這個退路成立** | `fastembed`（`multilingual-e5-large`，ONNX）與 `ollama`（`bge-m3`）**同為 1024 維**，與 `U5` 的 `vector(1024)` 欄位一致。切換只需改環境變數值，**不需改碼** |
| **為何退路不是免費的** | `fastembed` 在 FastAPI 行程內執行，吃的是**同一台主機**的 CPU 與記憶體。退路只在「多一個容器裝不下、但行程內多一點記憶體放得下」時成立 |
| **版本策略** | 同 2.1：釘選明確版本，不用 `latest` |

### 2.3 db image：`postgres:16-alpine` → **PostgreSQL 18 ＋ pgvector**（`[N8]`=B）

| 欄位 | 值 |
|---|---|
| **選擇** | 含 pgvector 的 **PostgreSQL 18** 映像 |
| **為什麼需要 pgvector** | `U5 memory-data` 的 `vector(1024)` 欄位需要它；現用映像不含（`C-T5`） |
| **為什麼順便升主版本（本輪由使用者提出，取代初版的「維持 16」）** | 初版寫「維持 16——不順便升版，理由是同時換基底映像與升主版本會讓『哪一個造成問題』無法區分」。**那個理由本身仍然成立**，`[N8]`=B 是在知道它的前提下接受的取捨。促成翻案的是另一項事實：`[N7]` 已經要讓**本機** db 跨一次主版本（15→16），volume 本來就要重建；若只把本機升到 18 會重新製造「本機與部署主版本不同」這個 `[N7]` 正要修掉的落差。故只有「都 16」或「三處都 18」兩種自洽解，使用者選後者 |
| **範圍（五個落點）** | image 四處必須全部一致：`deploy/docker-compose.deploy.yml:13`、`deploy/docker-compose.test.yml:15`、**repo 根 `docker-compose.yml:3`**（初版寫「不改」，本輪更正為必須改）、`N-2` 的真實 PG CI job service container。**第五個落點是 volume 宣告**（`deploy/docker-compose.deploy.yml:20` 的掛載行與 `:96` 的宣告行）——`cloud360_db` 必須改名，否則 `NFR6.3` 步驟 4 的「新 volume」與步驟 7 的「保留舊 volume」不可能並存（審查 R-24）。逐項與可測判準見 `security-requirements.md` `NFR6.1` |
| **上游逐字衝突（本輪升級）** | `requirements.md` NFR6 與 `contract-summary.md` K-05 `verification.carrier` **兩處**逐字釘成 `postgres:16-alpine`。原本只是「同主版本、不同變體」，`[N8]`=B 之後是**主版本不同**。該 job 是 `U5` 的交付；本站標出衝突並指名落點，不回改上游 |
| **基底映像同時改變（本輪補，審查 R-22）** | Alpine（musl）→ Debian（glibc）。**這是 collation 需要處置的唯一理由**，不是 pgvector 本身。初版把這項事實只寫在問題檔，三份產出一次都沒提 |
| **既有資料的處置**（`[N1]`=A ＋ `[N8]`=B） | 七步升版程序：盤點 → 基準查詢（含 `role_permissions` 的**內容指紋**）→ **完整備份且須已在別處還原驗證過一次** → **還原到乾淨叢集**（見下）→ 擴充驗證 → 資料驗證（三項逐項相同）→ **回退窗口**。逐步驟通過條件見 `security-requirements.md` `NFR6.3(c)` |
| **還原目標的硬條件（本輪補，審查 R-20／R-37）** | **兩條，缺一即重現**：①未掛載 `/docker-entrypoint-initdb.d/`；②**backend 在還原與驗證完成前必須是停止的**（措辭非「不得啟動」——選項 (ii) 下它本來就在跑，`deploy/docker-compose.deploy.yml:34` 是 `restart: unless-stopped`）——`backend/database.py:157` 每次啟動都呼叫 `ensure_role_permissions_seeded`，而 `rbac_seed_data.DEFAULT_ROLE_PERMISSIONS` 與 `schema_rbac.sql:322–630` **逐元組相同（皆 308 列、對稱差集 0）**，故它是第二個寫入者（審查 R-37）。兩份 compose 都把 `schema_rbac.sql` 掛進去，新 volume 即空 volume，entrypoint 會先 initdb 再跑該腳本——在任何還原之前資料庫已有全部資料表與 308 列 RBAC 矩陣；之後灌 dump 時 `psql` 預設不因錯誤中止。**初版在此舉的 admin 例子是錯的（審查 R-29）**：`schema_rbac.sql:11` 逐字「不建立固定密碼管理員」、全檔唯一 `INSERT INTO` 是 `:321` 的 `role_permissions`，admin 由 `backend/database.py` 依環境變數建立——`users` 在 initdb 後是空的，還原會正確進去。**真正會被靜默壓掉的是 `role_permissions`**（`:319` 的裸 `DELETE` 後重播，列數仍是 308），故步驟 2／6 改為比對**內容指紋**而非列數 |
| **升版窗口的排序不變量（本輪補，審查 R-19，Critical）** | `[N8]`=B 讓本 repo **唯一的自動自癒路徑**在窗口內失效並惡化：`deploy.yml` 自動部署（`:10–15`、`:108`），失敗時 `rollback` 自動取 `last-good-sha` 重跑 compose（`:209`／`:220`／`:222`），而 `last-good-sha` 只在成功時推進（`:148`）。於是 volume 已轉換而 `last-good-sha` 仍指向升版前 commit 時，**rollback 會拿 PG 16 映像去掛 PG 18 的 PGDATA**，站台維持中斷。三條不變量見 `security-requirements.md` `NFR6.3(b)`，全部須寫進 `DEPLOY.md` |
| **路徑：只走 dump/restore（本輪收斂，審查 R-21）** | 初版並列 `pg_upgrade` 並交給「部署者依停機窗口決定」。**`pg_upgrade` 在本部署形狀下沒有承載者**：它需要舊（16）與新（18）兩套 binaries 同機共存，而本 repo 是一個 compose 對應一個映像（全樹 `pg_upgrade` 命中 0）；更硬的一層是舊 binaries 還得是 **musl 建置**才能與 Debian 基底的 PG 18 共存，無可指名來源。**連帶**：`datcollversion`／`REINDEX`／`REFRESH COLLATION VERSION` 整段在 dump/restore 路徑上**不需要**（還原重建全部索引），故不再兩路並陳 |
| **訊號在哪裡（初版寫錯，本輪更正）** | 初版寫「這類錯誤不會報錯」。PostgreSQL 15 起有內建的 collation 版本追蹤（`pg_database.datcollversion`、啟動時的 mismatch WARNING），**訊號在啟動記錄裡，不在查詢結果裡**。查詢本身仍然靜默少回筆數，所以程序裡必須有一步專門去看那個記錄 |
| **未採用：維持 16，升版另開 intent** | 一次只改一個變數、B1 不加重。未採用的理由見上：本機側本來就要跨主版本，分兩次做等於讓「本機與部署主版本不同」這個落差多存在一段時間 |
| **未採用：不換 image、改用 `fulltext`** | 代價是 `FR4.6` 要的相似度檢索本輪不成立。`external-dependency-map.md` E4 逐字：「沒有退路——向量檢索是 `[RA:FR4]` 的承載方式」 |
| **未採用：重建 staging volume** | 最乾淨，但會清掉既有資料。`C-T6` 已記載 `schema_rbac.sql` L319 有裸的 `DELETE FROM role_permissions;`，重跑會抹掉管理者在權限頁的人工調整 |
| **本階段新增、scope 尚未涵蓋** | 見 `security-requirements.md` `§〇` 的 `S-1`（主版本升級）、`S-2`（本機 db 映像）、`S-4`（自動 rollback 的窗口處置） |

### 2.4 `CREATE EXTENSION vector` 由兩處承載（本輪更正）

**初版在此寫錯**：它主張啟動補丁單獨承載，並以「`schema_rbac.sql` 只在空 volume
執行」為由排除那條路。實際上那段論證證明的是**兩者互補**——各自覆蓋不相交的
環境集合。

| 欄位 | 值 |
|---|---|
| **選擇**（`[N2]`=A，本輪修正為兩處） | (1) `CREATE EXTENSION IF NOT EXISTS vector;` 置於 `schema_rbac.sql` 的 `BEGIN;` 之後第一條敘述；(2) `_ensure_vector_extension()` 於 `backend/database.py`，**呼叫點在 `Base.metadata.create_all(bind=engine)` 之前** |
| **為什麼需要它** | 換 image 只讓擴充**可用**，不會建進資料庫。`CREATE EXTENSION vector` 必須有人執行，而上游 K-01 **沒有指名誰** |
| **為何 `schema_rbac.sql` 那一處不可省** | 兩份 compose 都把它掛進 `/docker-entrypoint-initdb.d/`（`deploy:23`、`test:21`），在 **db 容器 init 時**執行；backend 要等 db healthy 才啟動。而 `docker-compose.test.yml` **沒有具名 volume**，所以 `ui-regression` 的每一個 PR 都走這條路——啟動補丁在那裡永遠來不及。本機 dev 也是 `psql -f schema_rbac.sql` 手動建庫，同樣早於 backend |
| **為何啟動補丁那一處不可省** | `schema_rbac.sql` 在**既有 staging 的非空 volume** 上不會重跑（`C-T6`）。那條路徑只有啟動補丁有效 |
| **為何呼叫點必須在 `create_all` 之前** | `init_db()` 的第一件事就是 `Base.metadata.create_all(bind=engine)`（`backend/database.py:76`），它在六支 `_ensure_*`（`:78–83`）**之前**。把新補丁加進 `:78–83` 仍然晚於 `create_all`——若 `U5` 以 ORM model 宣告向量欄位，`create_all` 會先跑而擴充還不存在 |
| **為何不用 compose init 指令** | 本 repo 已有三處 schema 定義處（`schema_rbac.sql`、`database.py` 補丁、ORM）。加第四處違反 `team.md` 的「單一真實來源」精神。本輪的兩處都落在既有的前兩處內，**不新增定義處** |
| **冪等性** | `IF NOT EXISTS` 使兩處各自重跑無副作用，兩處同時生效亦無副作用 |
| **可測判準** | `schema_rbac.sql` 內該敘述的行號 < 該檔任何 `vector(` 欄位宣告的行號；`database.py` 內 `_ensure_vector_extension()` 的呼叫行號 < `Base.metadata.create_all` 的行號。兩條皆可 grep |
| **權限（初版寫錯，本輪更正）** | 初版寫「以既有 `POSTGRES_USER`（即該資料庫擁有者）執行」。`CREATE EXTENSION` 在擴充未標記 trusted 時需要的是 **superuser**，不是擁有者。它在本 repo 能成立是因為**官方 postgres 映像把 `POSTGRES_USER` 建成 initdb 的 bootstrap superuser**——理由該寫這個 |
| **前提失效條件** | 若日後 backend 改以受限角色連線（`U5` 的 grant 邊界工作，K-05 逐字「grant 只開放記憶 schema」），`CREATE EXTENSION` 須改由具 superuser 權限的路徑執行，啟動補丁會失敗 |
| **落點須先確認的事** | `codekb` 記載 `backend/` 內新增模組可能誤觸兩支 import 邊界 validator。本項是**修改既有檔案**而非新增模組，故不觸發——但實作時仍需複驗 |

### 2.5 不引入的東西（明列，避免下游以為是遺漏）

| 未引入 | 理由 |
|---|---|
| 反向代理容器（為 Ollama 加 basic auth） | `[N4]`=A 定案採網路隔離；本輪已新增兩個服務 |
| 額外的 compose internal network | 同上，`[N4]` 的選項 C 未採用 |
| ~~PostgreSQL 主版本升級~~ | **本輪已改為採用**（`[N8]`=B）。初版列在此處，見 2.3 的翻案理由 |
| Redis Sentinel／Cluster | 單一 staging 主機，無高可用需求（`C-R1`：只部署至自有 staging） |
| 任何 LLM／embedding 的雲端 API | 兩個 embedding 選項皆為本機執行（`NFR9.1`）；本 intent 不為 embedding 新增任何外部花費 |
| 覆蓋率量測工具 | `technology-stack.md` 已記載 backend 無 coverage 機制。導入它是獨立的工具鏈決策，不由本單元夾帶 |

---

## 三、服務數的變化

| 範圍 | 變更前 | 變更後（Ollama 部署時） | 變更後（退到 `fastembed` 時） |
|---|---|---|---|
| `deploy/docker-compose.deploy.yml` | 4 | **6** | **5** |
| `deploy/docker-compose.test.yml` | 依 `ui-regression` 的短生命週期 stack | ＋Redis（session 測試需要） | ＋Redis |

**另有一處不在服務數內但必須同步**：repo 根 `docker-compose.yml` 的 db 映像（見 2.3 的五個落點）。

`docker-compose.test.yml` 是否需要 Ollama 取決於 `U5`／`U6` 的 CI 驗證是否要跑真實
embedding——**本單元不預設**，留 `U6 embedding-port` 與 `build-and-test` 決定；
本檔只確保 db image 兩處一致（`NFR6.1`）。

---

## 四、九處部署資產同步（`NFR8.1`–`NFR8.6` 的落點清單）

| # | 檔案 | 本單元要加什麼 | 有 CI 閘門？ |
|---|---|---|---|
| 1 | `deploy/render-env.sh` | 三處擴充：`:44–49` 必填值檢查加入 `REDIS_PASSWORD`、`:59` 的 `$` 擋阻名單加入它、heredoc 寫出**七個**變數（含本輪新增的 `REDIS_USER`） | **有條件的是**——**僅在該變數於 deploy compose 中被引用且無 `:-` fallback 時成立，見 `NFR8.1a`**（`validate_env_contract.py:168–182` `validate_deploy_stack_is_fully_supplied()`），且**只驗名稱不驗值** |
| 2 | `deploy/.env.example` | 列出同七者；**不得**寫入本機來源或 compose 自行推導的值 | **有條件的是**——**前提同 row 1，見 `NFR8.1a`**（同檔 `:184–197` `validate_deploy_template_is_complete()`；它與 row 1 共用同一個 required 集合），同樣**只驗名稱不驗值** |
| 3 | **`backend/.env.example`** | 列出 backend 讀得到的那幾個變數 | **是**（`validate_env_contract.py:242–261`，掃 `backend/**/*.py` 的 `os.environ.get`／`os.getenv` 並與範本比對）。兩個既有例外：`SDK_INTERNAL_KEYS`（`:69`）內的名稱不比對、路徑含 `tests` 或 `.venv` 的檔不掃（`:246`）。**初版在此寫「唯一有閘門的一項」是錯的**——同表 row 1、row 2 就各有一支閘門函式，見下方更正 |
| 4 | `LOCAL-DEV.md` | Redis 可達；`EMBEDDING_PROVIDER` 的選值與各值的額外前置；**本機 db 升至 PG 18 ＋ pgvector 且 data volume 必須重建**——寫進**必做前置**而非附註；**另更正 `:105` 對 `schema_rbac.sql` 建立 `admin` / `admin123` 的錯誤敘述**（審查 R-38，該句與 `schema_rbac.sql:11` 不符，屬 repo 既有文件漂移） | 否 |
| 5 | `DEPLOY.md` | **八項**（見 `security-requirements.md` `NFR8.5` 的逐項表；第 8 項為窗口後復原 `rollback` job 的收尾步驟）：三條排序不變量與採用的 rollback 處置選項、七步升版程序（**dump/restore 唯一路徑**）、步驟 4 的**兩條硬條件**與採用哪一種做法（含兩者代價不對稱的說明）、volume 的完整名稱與驗證、回退窗口保留期限、`CREATE EXTENSION` 由兩處承載的說明、`NFR8.9` 的日誌 `options` 選值 | 否 |
| 6 | **`.github/workflows/deploy.yml`** | **兩個 job 的改動不對稱**：`env:` 對照表 deploy（`:90–104`）與 rollback（`:193–206`）**都要加**；但「Require the secrets that must not default」步驟**只存在於 deploy job**（`:71–86`，全檔命中數為 1）。**rollback 路徑的缺值保護實際落在 `NFR4.1` 為 `render-env.sh:44–49` 新增的必填檢查上** | 否，但**漏改會讓 render 直接中止**（`set -euo pipefail` 下讀不到值） |
| 7 | **`deploy/docker-compose.deploy.yml` 的 `backend.environment:`**（本輪補，審查 R-30） | 七個變數必須加進 `:35–62` 且**不得帶 `:-` fallback**。它既是變數送進 backend 容器的**唯一**路徑，也是 row 1／row 2 那兩道閘門的**成立前提**——該檔 `:39–40` 的註解逐字記載了這件事 | 否（但它決定了 row 1／2 的閘門存不存在） |
| 8 | **`deploy/docker-compose.test.yml` 的 `backend.environment:`**（本輪補，審查 R-36） | Redis 三者必須加進 `:32–39`，依該 stack 既有慣例**自帶測試用預設值**。本單元已在兩處無條件承諾 Redis 要進那份 compose（`§三` 的服務數表、`NFR8.7` 的「兩份 compose」判準），Redis 進去而 backend 收不到變數就是同一個失敗模式 | 否——`validate_env_contract.py:40` 的 `DEPLOY_COMPOSE` 是該檔唯一的 compose 路徑，**test compose 完全不在作用域內** |
| 9 | **Redis 設定資產**（`redis.conf`／`users.acl`，或 compose 的 `command:` 覆寫）——**兩份 compose 都要掛**（`deploy` 與 `test`）；未掛進 test stack 會讓 `NFR8.1b` 的 `REDIS_USER` 無解、`ui-regression` 每個 PR 都紅（審查 R-44） | 承載 `NFR4.1(b)` 的 ACL 專用使用者與 `NFR4.2` 的 `appendonly`／`appendfsync`／`auto-aof-rewrite-*` 三組設定。**本輪新增**（`S-5`）——初版把這兩條寫成需求卻沒指名承載者 | 否（validator 不解析 `command:` 或掛載的設定檔） |

**初版漏掉第 3、第 6 項（本輪第一次補入）與第 7 項（本輪第二次補入）。** 初版特地論證「實際是四處同步，不是三處」，
但那個盤點只看了 K-01 的 `sync_obligations` 加上 `DEPLOY.md`，**沒有回頭看機敏值是
從哪裡進到 `render-env.sh` 的**（答案是 `deploy.yml` 的 `env:` 對照表），也**沒有看
backend 自己的範本**（**初版誤以為**那是唯一有 CI 閘門的一項；實際三項皆有，見 row 3 與 `security-requirements.md` `§四`）。

`DEPLOY.md` 不在 K-01 的 `sync_obligations` 三項內，但 `project.md ## Mandated` 的
schema 同步規則要求「部署必知的 schema／seed 行為」變更時同步它——`CREATE EXTENSION`
與資料庫映像換版兩者都落在該規則內。

---

## Assumptions & Open Questions

- Redis、Ollama 與 PostgreSQL 18 ＋ pgvector 的具體版本／tag 本檔未釘到 patch 級，
  只定「釘選明確版本、不用 `latest`」的策略。**pgvector 在 PG 18 的實際 tag 與可用性
  本輪未實地查證**，於實作時確認並記入 compose [assumption]
- `docker-compose.test.yml` **是否需要 Ollama**取決於 `U5`／`U6` 的 CI 驗證形狀，留下游。
  **Redis 則已定案要進去**（`§三` 的服務數表、`NFR8.7` 的「兩份 compose」判準、
  `§四` row 8 的 `NFR8.1b`），不再是待決事項 [assumption]
- 「九處同步而非三處」是本站的盤點結果：K-01 只列三處，`DEPLOY.md` 由 `project.md`
  的 schema 同步規則帶進來，`backend/.env.example` 與 `.github/workflows/deploy.yml`
  由本輪回頭追機敏值的來源與 CI 閘門的作用域查出。若下游認為某一處不在範圍內，
  本檔的論證在此供覆核 [assumption]
- `_ensure_vector_extension()` 不觸發兩支 import 邊界 validator 的判斷，基於「本項
  是修改既有檔案而非新增模組」。**本輪未實際執行那兩支 validator 複驗** [assumption]
