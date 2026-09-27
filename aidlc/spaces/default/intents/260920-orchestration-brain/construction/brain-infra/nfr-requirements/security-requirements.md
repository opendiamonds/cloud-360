# Security Requirements — `brain-infra`（U1）

<!-- Stage: nfr-requirements（Construction 3.2）· Unit: brain-infra · kind: packaging -->

## 這份檔在做什麼

`brain-infra` 交付的是**基礎設施設定**：Redis 第 5 服務、Ollama 第 6 服務、
PostgreSQL 主版本升級至 18 並含 pgvector、模型快取與 session 持久化 volume，
以及**九處**部署資產同步。它不含業務邏輯，所以它的安全面全部落在**暴露面、憑證與
部署設定的完整性**上。

本檔可獨立閱讀。每一條需求都繼承 inception 的 `NFR{n}` 編號並附子號（stage 檔要求）。

**讀進來的上游**：`requirements.md`（NFR 與 ADR-0006 四面向判定表）、
`contract-summary.md`（K-01 `brain-infra-env` 的變數、映像與同步義務；K-05 的記憶
schema 與其驗證載體）、`decisions.md`（`domain-design` 的 ADR-005，session TTL）、
`technology-stack.md`（codekb，基準 `dc4b687`）。

stage 檔另列了 `functional-spec.md` 與 `rules.md` 兩項上游，**它們對本單元不存在**
——`functional-design` 的 `produces_kinds` 五項皆不含 `packaging`，故該 stage 對本
單元**整站 kind-vacuous**。這是設計上的缺席，不是漏讀。

---

## 〇、本階段新增、已核可 scope 尚未涵蓋（**需回補**）

依 `project.md` 的規則逐處標明，不當作既有能力項的自然延伸吸收。

| 項 | 新增了什麼 | 觸發 | 後果（已於提問當下向使用者揭露） |
|---|---|---|---|
| **S-1** | **PostgreSQL 主版本由 16 升至 18** | `[N8]`=B（使用者於本輪主動提出） | `scope-document.md` 無「資料庫主版本升級」能力項。本單元原本的範圍是「加 pgvector 擴充」，現擴為對**有現存資料的 staging volume** 做 major upgrade：`NFR6.3` 由「collation 判定 ＋ 必要時重建索引」換成完整的升版程序（含回退窗口）；上游 `requirements.md` NFR6 與 K-05 **兩處**逐字釘選的 `postgres:16-alpine` 由「變體不同」升級為**主版本不同**的衝突；`risk-and-sequencing-rationale.md` 的 **R7（B1 裝不下）**加重 |
| **S-2** | **repo 根 `docker-compose.yml` 的本機 dev db 由「不改」改為必須改** | `[N8]`=B ＋ 審查 R-13 | 開發者的本機 data volume 須重建（跨主版本 15→18）。**不改的後果是每位開發者的整個本機資料庫建不起來**，見 `NFR6.2a` 與 `NFR8.4` |
| **S-3** | **Redis 連線的最小權限（ACL 專用使用者）** | 審查 R-15 | `requirements.md:451` 的 ADR-0006 IAM 列**逐字**以「另：Redis 連線憑證須最小權限」結尾，但上游沒有任何 FR／NFR 承載它。本單元以 `NFR4.1` 的最小權限條款承接，屬新增工作量 |
| **S-4** | **升版窗口內自動 rollback 的失效處置**（排序不變量 ＋ 窗口內停用 rollback **＋ 窗口後的復原步驟** ＋ 相容性前置檢查） | 審查 R-19（Critical） | `deploy.yml` 的自動自癒是本 repo 唯一的自動還原路徑。`[N8]`=B 的主版本升級在窗口內讓它**不但失效、還會把站台繼續壓在中斷狀態**（它會拿 PG 16 映像去掛 PG 18 的 PGDATA）。`scope-document.md` 無此項；處置本身是新增的部署程序與（可能的）workflow 改動。見 `NFR6.3` §排序不變量 |
| **S-5** | **Redis 設定資產與連線身分變數**（`REDIS_USER` ＋ **每個 stack 各自的** Redis 設定承載者） | 審查 R-23 | `S-3` 只記了「要最小權限」，沒記它**需要多一個設定資產承載者與多一個變數**。K-01 的 `variables` 是封閉的六項、無 `REDIS_USER`；六處同步點裡也沒有任何 Redis 設定資產。ACL 使用者與 AOF 三組設定都只能由 compose `command:` 覆寫或掛載設定檔承載。落地後同步點由六處變**九處**（另兩處為審查 R-30／R-36 查出的兩份 compose 的 `backend.environment:`，見 `NFR8.1a`／`NFR8.1b`）。見 `NFR4.1(c)` |

---

## 一、ADR-0006 Security Baseline 四面向逐項判定

`project.md` 明列此為 hard constraint，**四面向缺一不可**；判定為不適用者亦須附理由。

| 面向 | 對 `brain-infra` 的判定 | 本單元的具體要求 |
|---|---|---|
| **IAM** | **適用** | `NFR4.1`：Redis 連線憑證須**最小權限**（以 ACL 專用使用者承載，不共用 `default`）且不得含 `$`。`NFR6.2` 的擴充建立需要 superuser——它在本 repo 能成立是因為**官方 postgres 映像把 `POSTGRES_USER` 建成 initdb 的 bootstrap superuser**，而非因為它是資料庫擁有者；若日後 backend 改以受限角色連線（`U5` 的 grant 邊界，K-05 逐字「grant 只開放記憶 schema」），`CREATE EXTENSION` 須改由具 superuser 權限的路徑執行。**本單元不含任何使用者授權判定**——K-01 `behaviour_semantics.authorization_responsibility` 逐字寫「**無**——環境變數不含授權判定」。使用者層授權落在 `U3 rbac-story-ids` 與各 service 單元 |
| **Encryption** | **適用，但手段留 `nfr-design`** | episodic memory 的靜態與傳輸加密手段是 `OQ-3`。本單元的相關交付是承載面（`NFR7.1`）。承接站的成立條件見 `NFR7.1`——**不是本站跑過就成立** |
| **Network exposure** | **適用（本單元的主要安全面）** | `NFR8.7`、`NFR8.8`：Redis 與 Ollama **兩個容器的對外暴露面必須為零**，不得 `publish port`，僅限 compose 內部網路。這是 Ollama 唯一的存取控制 |
| **Audit logging** | **適用** | `NFR8.9`：兩個新容器的記錄承載、保存期，以及**在零認證前提下，未授權的 Ollama 呼叫在記錄上是否可辨識**。判為適用的理由：`NFR8.8` 刻意放棄了 Ollama 的認證面，而認證被放棄時記錄就是唯一偵測面。把它判為不適用等於把「未授權呼叫是否留得下痕跡」從判定表上移除 |

**ADR-0006 property-based testing hard constraint 的判定**：**不適用，附理由。**
`project.md ## Testing Posture` 把 PBT 的落點指定為 IaC generator、cost calculator、
agent routing 三類**純計算模組**。`brain-infra` 的交付物是 compose YAML、環境變數、
一段 SQL 與一支執行它的啟動補丁——沒有值域可供性質測試的純函式。

---

## 二、安全需求（逐條，含可測判準）

### `NFR4.1` — Redis 憑證與最小權限（**待交付的擴充，不是既有保證**）

**(a) 憑證強度**：`REDIS_PASSWORD` 為 `required: true`、**無 fallback**（缺值即為錯誤，
不得以空字串啟動），**值不得含 `$`**，以 `openssl rand -hex 32` 產生。

**(b) 最小權限（本輪新增，承接 `S-3`）**：本應用**不得以 Redis 的預設 `default`
使用者連線**。須以 Redis ACL 建立專用使用者，其可用指令與 key pattern 限於本應用
所需。理由：以單一 `requirepass` 走 `default` 取得的是 full command access
（含 `FLUSHALL`／`CONFIG`／`KEYS`），那是最小權限的反面；而
`requirements.md:451` 的 ADR-0006 IAM 列**逐字**要求「Redis 連線憑證須最小權限」。

- **可測判準**：以該連線身分執行一個明確超出所需的指令（例如 `CONFIG GET *`），
  **必須被拒絕**。二元可判。

**(c) 這兩條的承載者（本輪補；承接 `S-5`）**——初版把 (b) 與 `NFR4.2` 的三組 AOF
設定寫成需求，卻**沒有指名它們由什麼承載**。那正是本單元對上游用的「契約端點三問」
裡的「誰寫」缺一，這次落在自己新增的需求上：

| 要承載什麼 | 承載者 | 為何非它不可 |
|---|---|---|
| **連線身分**（不得是 `default`） | **新增 `REDIS_USER` 變數** | K-01 的 `variables` 是**封閉的六項、沒有 `REDIS_USER`**，而 `REDIS_URL` 的 `validation` 逐字只要求「須為 `redis://` 開頭；主機名須為 compose 內部服務名」——整個變數契約裡沒有任何地方說明「以哪個身分連線」 |
| **ACL 使用者的建立**（`ACL SETUSER` 或 `aclfile`） | **掛載的 Redis 設定資產**（`redis.conf`／`users.acl`，**兩份 compose 各自一份**），或 compose 的 `command:` 覆寫（由 compose 逐 stack 內插）——**兩份 compose 都必須有**，見下方範圍說明 | ACL 使用者必須被**建立**，而 Redis 容器預設不讀任何專案設定 |
| **`appendonly`／`appendfsync`／`auto-aof-rewrite-*`** | 同上一列 | 同理：預設映像不會自己開 AOF |

- **落地後的連動**：`REDIS_USER` 使 `NFR8.1`–`NFR8.3` 的「六者」變**七者**；同步點
  由六處變**九處**——審查 R-30 查出 deploy compose 的 `backend.environment:`
  （`NFR8.1a`）、審查 R-36 查出 test compose 的 `backend.environment:`（`NFR8.1b`）、
  `S-5` 的 Redis 設定資產。序數以 `tech-stack-decisions.md` `§四` 的表為準。
- **三份產出對 `redis.conf`／`users.acl`／`ACL SETUSER`／`REDIS_USER`／`appendonly`／
  `command:` 的 grep 命中在本輪之前全部為 0**——這是本條存在的理由。
- **Redis 設定資產沒有機械閘門**，列入第四節。

**適用範圍必須指明，否則 CI 測試 stack 無解（本輪補，審查 R-44）**：

| 項目 | `deploy` stack | `test` stack |
|---|---|---|
| **ACL 設定資產**（`users.acl`／`redis.conf`） | **必須有** | **必須有，但不會是同一份檔**——`NFR8.1b` 已要求 `REDIS_USER` 進 test stack，而 `NFR4.1(c)` 的契約是 required、值不得為 `default`。**若該 stack 沒有 ACL 使用者，兩條路都死**：用非 `default` 使用者會 `WRONGPASS`、用 `default` 被 `NFR4.1(c)` 擋下，結果是**每個 PR 的 `ui-regression` 都紅**。<br>**為何不能是同一份檔**（本輪更正）：Redis 的 ACL 把密碼綁在 user 那一行（`user <name> on >pass ~... +@...`），而 `redis.conf`／`aclfile` **不內插環境變數**；兩個 stack 的 `REDIS_PASSWORD` 值不同來源（見本表第三列），共用一份檔只有兩種收法——把 deploy 的憑證改成 repo 內的字面值（**等於把部署憑證放進 public repo**，牴觸 `NFR4.1(a)` 與 `project.md ## Forbidden`），或讓 test 用 deploy 的真憑證。**兩者都不可接受**。故採掛載檔時**各自一份**，或採 compose 的 `command:` 覆寫由 compose 逐 stack 內插（見上方承載者欄） |
| **`NFR4.2` 的 AOF ＋ 具名 volume** | **必須** | **豁免**——`deploy/docker-compose.test.yml:22` 的註解逐字為 `No host port and no named volume: isolated and disposable`，該 stack 刻意無持久化，而 `NFR4.2` 的不變量（重啟 Redis 後可還原）對一個每次重建的 stack 沒有意義 |
| **`REDIS_USER`／`REDIS_PASSWORD` 的值** | 由 `render-env.sh` 產生 | 依該 stack 既有慣例**內嵌自帶測試用預設值**（與 `JWT_SECRET` 等同形） |

**這一格是本單元自己新增的需求缺「誰寫」的第二次**——第一次是 `NFR4.1(c)` 本身
（ACL 與 AOF 設定無承載者），這一次是承載者有了、但沒說它要掛在哪幾份 compose。

**`REDIS_USER` 的契約欄位（本輪補，審查 R-33）**——K-01 為每個變數列了「名稱、型別、
必填性、預設值與驗證規則」，而初版只說它「新增」，四欄皆缺：

| 欄位 | 值 |
|---|---|
| 型別 | `string` |
| 必填性 | **required**（無 fallback；缺值即為錯誤，與 `REDIS_PASSWORD` 同） |
| 預設值 | **無**——刻意不給，避免靜默落回 `default` |
| 驗證規則 | **值不得為 `default`**（與 `NFR4.1(b)` 的拒絕測試對齊）；且若 `REDIS_URL` 本身也攜帶使用者名稱，**以 `REDIS_USER` 為準**，兩者不一致時啟動即失敗 |
| 值的來源 | **`render-env.sh` 內的字面值，不進 `deploy.yml` 的 `env:` 對照表**。理由：它是使用者名稱不是機敏值；放進 repository secrets 會觸發 `project.md` 的 `gh api` 複查義務卻沒有對應的保護收益。**`NFR8.1` 的 `deploy.yml` 兩處同步因此只涉及 `REDIS_PASSWORD`，不涉及 `REDIS_USER`** |

**初版在 (a) 寫錯，本輪更正**：初版寫「`render-env.sh` 已對含 `$` 的憑證擋下
（`:59–69`）」，把既有機制說成已經涵蓋這個新憑證。實際上 `render-env.sh:59` 是一份
**固定名單**（`POSTGRES_PASSWORD`／`JWT_SECRET`／`N8N_PASSWORD`／`GCP_BILLING_API_KEY`／
`AWS_ACCESS_KEY_ID`／`AWS_SECRET_ACCESS_KEY`），`REDIS_PASSWORD` **不在其中**；
同檔 `:44–49` 的「必填值」檢查也是硬編碼 `POSTGRES_PASSWORD` 與 `JWT_SECRET` 兩個名字。

**本單元因此要交付三處 `render-env.sh` 的擴充**：

| 位置 | 要改什麼 |
|---|---|
| `render-env.sh:44–49` | 把 `REDIS_PASSWORD` 加入必填值檢查 |
| `render-env.sh:59` | 把 `REDIS_PASSWORD` 加入 `$` 擋阻名單 |
| `render-env.sh` 的 heredoc | 寫出**七個**變數（原六者 ＋ `REDIS_USER`，見 (c)） |

- **可測判準**：對一個含 `$` 的 `REDIS_PASSWORD` 執行 `render-env.sh`，**必須非零
  退出**；對空的 `REDIS_PASSWORD` 執行，**必須非零退出**。
- **另一項既有義務**（`project.md ## Mandated`）：新增任何憑證型 secret 後，須以
  `gh api repos/<owner>/<repo>/actions/secrets` 與同路徑的 `/variables` **各查一次**，
  確認它落在 secrets 而非 variables。本 repo 為 public、Actions log 公開可讀，
  一次意外 echo 即等同公開發布；若曾誤存為 variable，**僅搬移不足以結案，必須重新
  產生金鑰**。

### `NFR4.2` — session 在 Redis 重啟後仍可還原（**本單元擴充上游的不變量**）

Redis 啟用 **AOF 持久化**並掛**具名 volume**。

- **適用範圍：只限 `deploy` stack**（本輪補，審查 R-44）。`deploy/docker-compose.test.yml:22`
  的註解逐字為 `No host port and no named volume: isolated and disposable`——該 stack
  刻意無持久化且每次重建，「重啟 Redis 後可還原」這個不變量對它沒有意義。
  ACL 設定資產則**兩份 compose 都要掛**，見 `NFR4.1(c)`。

- **上游的不變量與其缺口**：`requirements.md` NFR4 逐字是「重啟 **backend** 後，
  既有對話的脈絡與作業對象仍可完整還原」——**它沒有涵蓋 Redis 容器自己重啟**。
  若 Redis 無持久化，Redis 重啟會清掉全部 session，而 **NFR4 的字面條件仍然通過**。
- **本單元的擴充判準**（`[N5]`=A 定案）：**重啟 `redis` 容器後**，既有對話的脈絡與
  作業對象仍可完整還原。
- **這是對已核可上游的字面範圍補足，不是新需求**：本站**不回改** `requirements.md`。
- **兩條交給 `U10`／`nfr-design` 的選值約束**（`§四` 該列一併涵蓋）：
  1. **`appendfsync`** 的選值**必須以不使 `NFR3` 的首字 P50 ≤ 2 秒預算失守為前提**。
     理由：`appendfsync always` 與 `everysec` 對每次 session 寫入的延遲差異是數量級的，
     而 `requirements.md` NFR3 逐字把「FR4 的 Redis 往返在同一個 compose 網路內約
     1ms，可忽略」算進了預算——那個「可忽略」的前提是**沒有同步 fsync**。
  2. **自動 AOF rewrite 不得關閉**（`auto-aof-rewrite-percentage`／
     `auto-aof-rewrite-min-size`），或須另行指定等效的容量上界。理由見 `NFR4.3`。
  兩者的所選值都須記錄在決定它的那一站。
- **沒有機械閘門**——見第四節。

### `NFR4.3` — 兩個新 volume 的「誰清」（**兩層**）

| volume | 誰寫 | 誰讀 | **誰清** |
|---|---|---|---|
| Redis AOF volume | `redis` 容器（session 寫入時） | `redis` 重啟時重播 | **兩層**：① **keyspace** 由 Redis 自身的 key TTL 回收——`domain-design` 的 **ADR-005** 已定案「作業對象、共享／獨立狀態、工作項集合**全部放在同一個 Redis key 之下**，TTL 24 小時、每次互動續期」。② **AOF 檔本身**由 **AOF rewrite** 回收，**不是** TTL |
| Ollama 模型快取 volume | `ollama` 容器（首次拉模型時） | `ollama` 啟動時 | **無需清理，但有界**：內容為單一模型（`bge-m3` 約 1.2GB），不隨使用量成長。若日後改為多模型，此判定失效 |

**初版兩處寫錯，本輪皆更正**：

1. 初版把 session TTL 寫成「`U10 session-store` 必須定出，若它到時沒有定，本條即為
   未滿足」。**TTL 已由 ADR-005 定案**（24 小時、每次互動續期），且該 ADR 逐字說明
   它「一個機制同時關掉 `OQ-9`（session 誰清、何時清）、`G-1`、`G-2` 三個缺口」；
   `contract-summary.md` 與 `unit-of-work.md` 皆原樣承接。把已定案的事寫成待決事項，
   會讓下游以為還有一個開放決策。
2. 初版據此寫「AOF volume 的成長有上界——單一 key、24 小時自然回收」。**機制上不成立**：
   TTL 管的是 keyspace，不是 append-only 檔。AOF 是**寫入指令的附加記錄**——每一次
   互動的續期與每一次到期刪除**都是新的附加**，過期不會讓既有的 AOF 內容縮小。
   真正把 AOF 壓回資料集大小的是 **rewrite**。故 `NFR4.2` 補上「自動 rewrite 不得
   關閉」這條約束；沒有它，一個把 rewrite 關掉的設定會在單機 staging 上把磁碟寫爆，
   而 `§四` 已記載這一層沒有機械閘門。

### `NFR6.1` — PostgreSQL 18 ＋ pgvector 的**全部**映像落點（`[N8]`=B）

| # | 落點 | 現值 | 本單元的要求 | 可測判準 |
|---|---|---|---|---|
| 1 | `deploy/docker-compose.deploy.yml:13` | `postgres:16-alpine` | 改為含 pgvector 的 **PG 18** 映像 | grep 該行為新值 |
| 2 | `deploy/docker-compose.test.yml:15` | `postgres:16-alpine` | 同上 | grep 該行為新值 |
| 3 | **N-2 的真實 PostgreSQL CI job** 的 service container | **尚未存在**；上游在**兩處**逐字釘成 `postgres:16-alpine` | 建立時須用同一個 PG 18 ＋ pgvector 映像 | 見下方衝突說明 |
| 4 | repo 根 `docker-compose.yml:3`（本機 dev db） | `postgres:15-alpine` | **必須改**（由初版的「不改」更正，見 `S-2` 與 `NFR6.2a`） | grep 該行為新值；四處 image 值相同 |
| 5 | **volume 宣告兩處**：`deploy/docker-compose.deploy.yml:20` 的掛載行與 `:96` 的頂層宣告行（本輪補，審查 R-24；行號於本輪更正——`:19` 與 `:95` 是 `volumes:` 鍵本身） | `cloud360_db` | **必須改名為新 volume**（兩處同步） | 新舊名稱不同；舊 volume 在保留期限內仍存在 |

**落點 1–4 的 image 值必須相同**——這是 `[N8]`=B 的核心好處：本機、CI 與部署不再有
主版本落差（初版狀態是本機 15、其餘 16）。

**落點 5 為何存在（審查 R-24）**：`NFR6.3` 步驟 4 要求「以**新 volume** 起 PG 18」，
步驟 7 又承諾「**舊 volume** 保留至驗證通過」。在單一 compose volume 名稱
（`cloud360_db`）下兩者不可能同時成立——不改名就必須先毀掉舊的，步驟 7 的回退面
就只剩備份檔一條腿。**本單元採「改名新 volume」**，使兩個步驟都真的成立；代價是
volume 宣告成為第五個落點，而它與四處 image 值一樣**沒有機械閘門**（第四節）。

**基底映像同時改變（本輪補，審查 R-22）**：現用 `postgres:16-alpine` 是
**Alpine 基底（musl）**，目標的 pgvector 映像是 **Debian 基底（glibc）**。
這不是附帶細節——**它就是 `NFR6.3` 需要處理 collation 的唯一理由**（libc 改變會讓
text 欄位的既有索引排序與新 libc 不一致）。初版把這項事實寫在問題檔裡，三份產出卻
一次都沒提。

**落點 3 的上游逐字衝突，必須指名而非默默改掉**：

- `requirements.md` NFR6 逐字：「應有一個對真實 PostgreSQL 執行的 CI job
  （**`postgres:16-alpine` 作為 service container**）驗證」。
- `contract-summary.md` K-05 的 `verification.carrier` 逐字：「真實 PostgreSQL CI job
  （**postgres:16-alpine** service container）」。
- 而 K-05 的 `tables[0].vector_column` 是 `embedding vector(1024)`——那個 job 一跑到
  這個欄位就會失敗，因為 `postgres:16-alpine` 不含 pgvector。
- **`[N8]`=B 之後衝突升級**：原本只是「同主版本、不同變體」，現在是**主版本不同**。

**處置**：本站不回改已核可的上游，而是標出衝突、寫明它讓哪一條需求目前不可滿足
（`NFR6` 的驗證本身），並指名落點：**該 job 是 `U5 memory-data` 的交付**，其 service
container 須與本單元的三處一致。`U5` 的迭代須就地確認此事。

**為何落點 2 特別重要**：`docker-compose.test.yml` 是 `ui-regression` 每個 PR 自動起
的短生命週期 stack。漏改它會讓每個 PR 的測試環境沒有 pgvector，而那不會以「設定
錯誤」的形式報錯。

### `NFR6.2` — `CREATE EXTENSION vector` 由**兩處**承載

`CREATE EXTENSION IF NOT EXISTS vector;` 必須同時出現在：

1. **`schema_rbac.sql`**，置於檔內 `BEGIN;` 之後的第一條敘述——涵蓋**空 data volume
   初始化路徑**與**本機 `psql` 路徑**。
2. **`_ensure_vector_extension()`**，且其呼叫點在 `backend/database.py` 的
   **`Base.metadata.create_all(bind=engine)` 之前**——涵蓋**既有非空 volume**。

**初版主張啟動補丁單獨承載，並以「`schema_rbac.sql` 只在空 volume 執行」為由排除
那條路。那個保證在三條真實路徑上都不成立**：

| 路徑 | 為何不成立 | 證據 |
|---|---|---|
| **ORM 路徑** | `init_db()` 的第一件事是 `Base.metadata.create_all(bind=engine)`（`:76`），它在六支 `_ensure_*`（`:78–83`）**之前** | `backend/database.py:74–83` |
| **空 volume 初始化路徑** | 兩份 compose 都把 `schema_rbac.sql` 掛進 `/docker-entrypoint-initdb.d/`，在 **db 容器 init 時**執行；backend 要等 db healthy 才啟動，啟動補丁**必然晚於它** | `deploy/docker-compose.deploy.yml:23`、`deploy/docker-compose.test.yml:21` |
| **本機 dev 路徑** | `LOCAL-DEV.md:102`／`:120` 要開發者手動 `psql … -f schema_rbac.sql`，同樣早於任何 backend 啟動 | 該檔 `:105` 說明它建立「全部資料表、308 列 RBAC 預設矩陣，以及預設帳號 `admin`」——**該句與 `schema_rbac.sql:11` 不符，見本檔 `NFR6.3(c)` 的更正與 `NFR8.4` 第 4 項** |

**`docker-compose.test.yml` 沒有具名 volume**，所以它**每一個 PR 都走空 volume
初始化路徑**——那條路徑上啟動補丁永遠來不及。

**兩個機制覆蓋的是不相交的環境集合，故互補而非二選一。**

#### `NFR6.2a` — 本機建庫路徑的硬依賴（**審查 R-13，Critical**）

**`schema_rbac.sql` 是單一交易**：`:24` `BEGIN;` → `:633` `COMMIT;`（全檔 644 行）。
`CREATE EXTENSION IF NOT EXISTS vector;` 的 `IF NOT EXISTS` **只抑制「擴充已存在」**；
伺服器**沒有安裝** pgvector 時是 `could not open extension control file` 這個**硬
ERROR**。交易一旦中止，psql 之後每一條敘述都以 `current transaction is aborted`
失敗、`COMMIT` 退化為 ROLLBACK，結果是**一張表都沒建**。

**故 `NFR6.1` 落點 4 必須改，不能維持現況。** 初版寫它「本輪不改」、並把後果縮在
`NFR8.4` 的「開發者要跑記憶功能必須自行處理」——**那少了一個數量級**：壞的不是
記憶功能，是**每一位開發者的整個本機資料庫**（全部資料表、308 列 RBAC 預設矩陣、
預設帳號），不論他碰不碰記憶。

**另一個更根本的理由（本站在核對審查發現時查出，超出審查所提）**：把
`CREATE EXTENSION` 移出交易**並不足以**解決這件事。`U5` 的記憶表依
`project.md ## Mandated` 的 blocking 規則**必須**寫進 `schema_rbac.sql`，而那些表帶
`vector(1024)` 欄位——在無 pgvector 的伺服器上，**那個欄位宣告本身**就會讓同一個
交易中止。所以本機 db 的映像非改不可，這是 `[N8]`=B 之外獨立成立的理由。

- **可測判準（三條皆可機械檢查）**：
  - `grep -c 'CREATE EXTENSION IF NOT EXISTS vector' schema_rbac.sql` ≥ 1，且其行號
    小於該檔任何 `vector(` 欄位宣告的行號。
  - `backend/database.py` 內 `_ensure_vector_extension()` 的呼叫行號 **小於**
    `Base.metadata.create_all` 的行號。
  - 對照 `NFR6.1` 的落點 1–4，image 值**四處相同**。
- **冪等性**：`IF NOT EXISTS` 使兩處各自重跑無副作用，兩處同時生效亦無副作用。
- **上游缺口**：`contract-summary.md` K-01 的 `images_and_services` **沒有指名誰執行
  `CREATE EXTENSION`**。這是契約端點三問裡「誰寫」缺一，由本單元承接。

### `NFR6.3` — PostgreSQL 16 → 18 的升版程序（`[N8]`=B）

**本條整體不在已核可 scope 內（`S-1`）。** 初版是「換基底映像後判定 collation 是否
需要重建索引」；`[N8]`=B 之後換形狀——major upgrade 的資料轉換遠大於 collation 一項。

#### (a) 路徑：**只走 dump/restore**（本輪收斂，審查 R-21）

初版把 `pg_upgrade` 與 dump/restore 並列為兩條路，由「部署者依停機窗口決定」。
**`pg_upgrade` 在本部署形狀下沒有承載者**，故本輪刪除該分支：

- `pg_upgrade` 需要**舊（16）與新（18）兩套 binaries** 連同舊 data directory
  同時在一台機器上；本 repo 的 db 服務是**一個 compose 對應一個映像**，沒有任何
  雙版本映像被指名（全樹 `pg_upgrade` 命中為 0）。
- 更硬的一層：舊 binaries 還必須是 **musl 建置**（現用是 Alpine 基底），要與
  **Debian 基底**的 PG 18 共存於同一鏡像——這個組合沒有可指名的來源。
- **連帶後果**：初版掛在 `pg_upgrade` 分支上的 `datcollversion`／`REINDEX`／
  `ALTER DATABASE … REFRESH COLLATION VERSION` 整段，在本路徑上**不需要**——
  還原會重建全部索引，Alpine（musl）→ Debian（glibc）的 collation 差異隨之消失。
  步驟 1 仍記錄 `datcollate`／`datcollversion`，但那是為了**事後比對**，不是為了
  決定要不要 `REINDEX`。

#### (b) 排序不變量（本輪新增，承接 `S-4`／審查 R-19）

**這是本條最重要的一段，也是 `[N8]`=B 製造出來的新風險。**

本 repo 的部署是全自動的：`.github/workflows/deploy.yml:10–15` 於 merged PR 進 `ut` 自動觸發，
`:108` 自動 `docker compose … up -d --build`；失敗時 `rollback` job（`:169`，
`if: failure()`）自動讀 `~/.cloud360/last-good-sha`（`:209`）、
`git checkout --quiet "${LAST}"`（`:220`）後再 `docker compose … up -d --build`
（`:222`）。而 `last-good-sha` **只在部署成功時推進**（`:148`），`cloud360_db` 是
**容器外部的具名 volume**。

**兩個可達的壞狀態**：

| 狀態 | 發生什麼 |
|---|---|
| **映像行先合併、volume 尚未轉換** | **不是拒絕啟動，是安靜的成功**（審查 R-28；初版在此寫錯）。落點 5 改名之後，compose 指向的是一個新名字，PG 18 **根本碰不到舊 PGDATA**：compose 自動建出該具名 volume（空的）→ PG 18 跑 initdb → 執行掛載的 `schema_rbac.sql`（`deploy/docker-compose.deploy.yml:23`）→ 建出全部資料表與 308 列矩陣 → `pg_isready` 過 → backend 起 → `.github/workflows/deploy.yml:112` 的 8090 健康檢查過 → 同檔 `:127` 的 tunnel 檢查過 → **deploy 成功**、同檔 `:148` 把這個 commit 寫成 `last-good-sha`、Slack 報成功。結果是 `cloud360.danniel.cc` 對外正常服務**一個完全空的資料庫**（舊資料仍在舊 volume，未毀），而**兩道既有健康檢查對它完全無效**——它們驗的是行程活著與端點回應，不是資料庫有列 |
| volume 已轉換，但 `last-good-sha` 仍指向升版前的 commit（或升版 PR 因**任何其他原因**失敗） | **自動 rollback 取出 PG 16 映像去掛升版前的 volume**——若舊 volume 仍存在則站台以舊資料復原（看似正常，實則已與新 volume 分岔）；若採同名替換則 PG 16 掛 PG 18 的 PGDATA、拒絕啟動、站台維持中斷。兩種都是本 repo **唯一**自動自癒路徑的失效 |

**三條不變量，缺一即有上述風險**：

1. **順序是指定的，不是開放選擇**（本輪由「先後必須明訂」收緊，審查 R-28）：
   **先完成 volume 轉換與驗證，再合併映像行**，且**兩者之間不得有任何其他 deploy**
   （合併 `ut` 即部署，故這是一條真正的排他窗口）。
   **反向順序的後果就是上表第一列**：deploy 會成功、健康檢查會過、`last-good-sha`
   會推進，而站台服務一個空資料庫——**沒有任何自動化會告訴你**。
2. **窗口內自動 rollback 不可用**。三個處置選項，**各自的覆蓋範圍必須標明**
   （本輪補，審查 R-31）：

   | 選項 | 覆蓋什麼 | 不覆蓋什麼 |
   |---|---|---|
   | 暫停其他合併 | 其他 PR 觸發的部署 | **不覆蓋升版 PR 自己的部署失敗**——`:112–125` 的 8090 檢查與 `:127–139` 的 tunnel 檢查都可能失敗，此時 rollback 照樣啟動。**故此項不得單獨使用** |
   | 為該次部署停用 `rollback` job | 全部 | 該改動要改 `.github/workflows/deploy.yml` 並**合併進 `ut`**——合併即部署，**直接違反不變量 1**。故它**必須在窗口開啟之前**先合併。**且窗口結束後必須復原**，見下方收尾步驟 |
   | 以 `workflow_dispatch` 重跑 | **只覆蓋「改動已在 `ut` 之後」的重跑** | **不覆蓋把改動送上 `ut` 的那一次合併部署**——而那一次才是承受風險的那一次 |

   **初版把第三項寫成「全部，且零改動」並推薦它，那是錯的（審查 R-35）**：

   - `.github/workflows/deploy.yml:38–41` 的 `deploy.if` 對**合併的 PR 與手動
     dispatch 兩者皆為真**；`:46–49` 的 checkout **硬釘 `ref: ut`**。
   - 所以映像行與 volume 改名**必須先出現在 `ut` 上，dispatch 才看得到它**；而把它
     送上 `ut` 的那一次合併**本身就是一次 `pull_request` 觸發的部署，`rollback`
     對它是武裝的**（`:172–175`）。
   - dispatch 那一次只是合併後的第二次重跑，**不是升版部署**。
   - 「不經 merge 路徑」在本 repo 只有一種實現方式——直接 push 到 `ut`，而那與
     `org.md` 的 trunk 規則牴觸，需要部署者知情裁決。

   **本單元改為建議第二項**（窗口開啟**之前**先合併停用 `rollback` job 的改動）
   ——依目前的機制，它是唯一能覆蓋「把改動送上 `ut` 的那一次合併」的選項。
   決定權仍在部署者；`DEPLOY.md` 必須寫明採用哪一項與其覆蓋範圍。

   **採第二項時的收尾步驟，缺它就是永久性的（本輪補，審查 R-42）**：
   窗口驗證通過後**必須以另一個 PR 把 `rollback` job 復原**，並確認**復原後的第一次
   部署有 rollback 武裝**。

   - **為何要獨立寫成一步**：第三項的賣點正是零改動、無需復原；改採第二項之後
     「誰把它改回來」是新長出來的義務，而初版三份產出對它零字。
   - **代價不在窗口內而在窗口之後**：`rollback` 是 `team.md` 與本檔都指名的
     **本 repo 唯一自動自癒路徑**。停用後不復原，等於此後每一次部署失敗都沒有
     自動還原——**而沒有任何 validator 看得到 workflow job 的存廢**（見第四節）。
3. **相容性前置檢查**：「rollback 取出的 commit，其 compose 映像的 PostgreSQL 主版本
   必須與當前 PGDATA 的主版本相容」。
   **這一條需要承載者，而本站給不出**（本輪誠實補記，審查 R-31）：要讓它成為真的
   檢查，落點只能是 `deploy.yml` 的 `rollback` job——例如 checkout 之後、
   `docker compose up` 之前，比對 compose 的 db image 主版本與 volume 內
   `PG_VERSION` 檔的內容，不符即中止並告警。**本站只能寫需求，改不動 workflow**；
   該改動列為 `S-4` 的一部分，落點 `deployment-pipeline`（4.1）。
   在它落地之前，本條**只是人工前置**，與第 2 項的選項一起由部署者執行。

- **`NFR8.5` 要求這三條全部寫進 `DEPLOY.md`。**
- **沒有機械閘門**——見第四節。

#### (c) 七步程序

| 步驟 | 動作 | 通過條件 |
|---|---|---|
| 1. 盤點 | 記錄現有 database 清單、`datcollate`／`datctype`／`datcollversion`、已安裝擴充清單 | 輸出留存 |
| 2. 基準查詢 | 對既有 text 索引的已知範圍做等值與範圍查詢並記下筆數；**留存 `role_permissions` 的內容指紋**（`(role, story_id, can_view, can_edit, can_review)` 全集的排序後雜湊，**不是列數**——理由見下）；記錄 `users` 表列數 | 三者皆留存 |
| 3. 完整備份 | 對現有 PG 16 執行 `pg_dumpall` | 備份檔可讀，且**已在別處還原驗證過一次** |
| 4. 還原到乾淨叢集 | 以**新 volume**（落點 5）起 PG 18 ＋ pgvector 並還原備份。**兩條硬條件缺一不可**：①還原目標**未掛載 `/docker-entrypoint-initdb.d/`**；②**backend 在還原與驗證完成前必須是停止的**——見下方說明 | PG 18 容器通過 healthcheck，**且 `docker compose ps backend` 顯示它未在執行** |
| 5. 擴充驗證 | 確認 `vector` 擴充存在且版本與應用需求相容 | `CREATE EXTENSION IF NOT EXISTS vector;` 成功（還原內容若已含它則為 no-op） |
| 6. 資料驗證 | 重跑步驟 2 的三項 | 索引查詢筆數逐項相同、**`role_permissions` 的內容指紋與步驟 2 相同**、`users` 列數相同 |
| 7. 回退窗口 | **舊 volume**（原 `cloud360_db`）與備份**同時**保留至驗證通過後的約定期限 | 保留期限寫進 `DEPLOY.md`；舊 volume 因落點 5 的改名而真的還在 |

**步驟 4 的「乾淨叢集」為何是必要條件（審查 R-20，理由於本輪更正）**：兩份 compose
都把 `../schema_rbac.sql` 掛進 `/docker-entrypoint-initdb.d/01-schema_rbac.sql`
（`deploy:23`、`test:21`）。新 volume 即空 volume，官方映像的 entrypoint 會**先跑
initdb 再執行該腳本**——於是在任何還原動作之前，資料庫已經有全部資料表與 **308 列
RBAC 預設矩陣**。之後灌入 `pg_dumpall` 的輸出時，`psql` 預設不因錯誤中止：
`CREATE TABLE` 報 already exists 被跳過；而 `COPY` **撞到主鍵就會中止整個 `COPY`**——
**該表還原的全部列都不會進去**，不是「相撞的那幾列被丟棄」（初版把後果寫得比真實情況輕）。

**初版在此的具體例子是錯的，本輪更正（審查 R-29）**：初版寫「最可能的後果是 `users`
的 `admin` 列保留種子的預設密碼」，並據此在步驟 2／6 加了 `password_hash` 斷言。
實查 `schema_rbac.sql`：`:11` 逐字為「**D) 不建立固定密碼管理員；bootstrap admin
由後端依環境變數建立**」，`:19` 逐字為「不覆寫既有 admin 密碼」，且**全檔唯一的
`INSERT INTO` 是 `:321` 的 `role_permissions`**。admin 實際由
`backend/database.py` 依 `CLOUD360_BOOTSTRAP_ADMIN_PASSWORD` 建立。所以 `users`
在 initdb 後是**空的**，`COPY` 不會撞主鍵，**還原的 admin 列會正確進去**——
被初版斷言的失敗模式經由被指名的機制**不可能發生**。

> **錯誤的來源值得記一筆**：初版依據的是 `LOCAL-DEV.md:105`，該檔逐字說
> `schema_rbac.sql` 建立「全部資料表、308 列 RBAC 預設矩陣，以及預設帳號
> **`admin` / `admin123`**」。**那份文件與 SQL 不符**，屬本 repo 既有的文件漂移，
> 與本 intent 無關，但下一個信它的人會再犯同一個錯。**承載者是 `NFR8.4`**
> （`LOCAL-DEV.md` 的待寫清單第 4 項）——初版寫「已列入第七節」而本檔沒有第七節，
> 等於這個缺陷沒有任何承載者（審查 R-38）。

**真正會被靜默壓掉的是 `role_permissions`**：`schema_rbac.sql:319` 有裸的
`DELETE FROM role_permissions;` 後重播預設矩陣，所以還原進去的矩陣會被種子覆蓋，
而**列數仍然是 308**——列數檢查抓不到它。故步驟 2／6 改為比對**內容指紋**。
`LOCAL-DEV.md:123` 已逐字記載這個風險：「重跑 `schema_rbac.sql` 會
`DELETE FROM role_permissions` 後重播預設矩陣 —— **在 Admin UI 上調過的權限會被蓋掉**」。

**「乾淨叢集」這個要求本身不變**——它的正當性來自 `role_permissions` 的覆蓋與
already-exists 噪音，不依賴那條錯誤的 admin 論證。

**預設矩陣有第二個寫入者，故「乾淨叢集」是兩條而不是一條（本輪補，審查 R-37）**：

`backend/database.py:157` 在 **`init_db()` 內、每次 backend 啟動**都呼叫
`ensure_role_permissions_seeded(db, force=False)`（`backend/services/rbac.py:58–81`），
它在 `role_permissions` 為空時寫入 `DEFAULT_ROLE_PERMISSIONS`。而
`backend/services/rbac_seed_data.py` 的那份種子與 `schema_rbac.sql:322–630`
**逐元組相同：皆 308 列、對稱差集為 0**。

所以「不掛 initdb 目錄」**不足以**避免種子落地——**啟動 backend 也會**。

**兩條條件，缺一即重現同一個失敗**：

1. 還原目標**未掛載 `/docker-entrypoint-initdb.d/`**；
2. **backend 在還原與驗證完成之前必須是停止的**——措辭是「必須是停止的」而不是
   「不得啟動」，因為在選項 (ii) 下它本來就在跑（`restart: unless-stopped`），
   「不啟動它」不會讓它停下來。

**故步驟 4 必須二選一並在 `DEPLOY.md` 寫明採用哪一種。兩者的代價不對稱（本輪補，
審查 R-43）——並列不等於等價**：

| | (i) 裸映像還原 | (ii) 暫移 initdb 掛載 |
|---|---|---|
| 做法 | 以 `docker run` 起裸映像（不掛 initdb 目錄、不起 backend）、還原、驗證，通過後才把 volume 交給 compose stack | 移除掛載後在**線上的 `cloud360` compose 專案裡**執行 |
| volume 命名 | 需自行確保是 `cloud360_<宣告名>`（見下方前置條件） | 由 compose 自動命名 |
| **線上站台的資料庫** | **不受影響**——整個還原在 compose 之外進行 | **在還原期間被換成空的**：`up db` 會以改過的設定重建線上的 `db` 容器 |
| backend 的處置 | 不會被帶起來 | **`up db` 擋不住已經在跑的 backend**——它是 `restart: unless-stopped`（`deploy/docker-compose.deploy.yml:34`），本來就在執行。必須**先 `docker compose stop backend`（或 `down`），並確認它在還原與驗證完成前保持停止** |

**初版只寫了「只能 `docker compose up db`，不得 `up -d` 全部服務」**，理由是
`deploy/docker-compose.deploy.yml:63–65` 的 `depends_on` 會把 backend 帶起來。
那句話擋住了 `depends_on` 這一條路，**沒擋住「backend 本來就在跑」這一條**。

**採 (i) 時的 volume 命名前置條件（本輪補，審查 R-28）**：`deploy/docker-compose.deploy.yml:9`
是 `name: cloud360`，故 compose 管理的具名 volume 實際名稱是
**`cloud360_<compose 宣告名>`**。手動還原時建出的 volume 若不是這個完整名稱，
compose 會**另建一個空的**並照常啟動成功——回到上表第一列那個安靜的失敗。

- **可測判準（交給 compose 之前必須通過）**：`docker volume ls` 命中該**完整名稱**；
  且以該 volume 起容器後，`role_permissions` 的內容指紋與步驟 2 留存值相同。
- **切到 compose stack 之後必須再驗一次**（步驟 6 的三項重跑）——手動還原驗過的是
  手動起的那個容器，不是 compose 起的那個。

步驟 2／6 的**內容指紋**就是為了讓這條路徑**可被偵測**——**列數驗不到它**：
`role_permissions` 被種子重播後列數仍然是 308，只有內容會變。

### `NFR7.1` — 加密承載面（手段留 `nfr-design`）

session（Redis AOF volume）與記憶資料（資料庫 volume）的**靜態加密手段**由
`OQ-3` 定案。本單元的責任是**不製造使其無法實作的結構**：兩者皆為具名 volume，
可由主機層或容器層加密承載，不寫入容器可寫層。

**初版推論錯誤，本輪更正**。初版寫「`nfr-design` 的執行條件依賴 `nfr-requirements`
已執行。本站已執行，故該條件成立」。**兩處不成立**：

1. **條件是連言**：`nfr-design` 的 `condition` 逐字是
   `NFR Requirements was executed **and** NFR patterns need design`。本站只滿足前半。
2. **跨單元不成立**：`nfr-design` 是 `for_each: unit-of-work`，而 `OQ-3` 的主題是
   episodic memory 的加密，屬 **`U5`／`U8` 的迭代**。`brain-infra` 跑過
   `nfr-requirements` 完全不保證 `U5`／`U8` 會跑。

**正確的處置**：`OQ-3` 的承接站是 **`U5`／`U8` 的 `nfr-design` 迭代**。依
`project.md` 的既有規則：**屆時判定 skip 的執行者須重新提交使用者裁決，不得由
實作者當場決定。**

### `NFR8.1` — 七個變數由 `render-env.sh` 寫入，且 `deploy.yml` 兩處同步

`REDIS_URL`、`REDIS_PASSWORD`、**`REDIS_USER`**、`EMBEDDING_PROVIDER`、
`OLLAMA_BASE_URL`、`OLLAMA_EMBED_MODEL`、`FASTEMBED_MODEL` **七者**，
**同一個 PR** 內必須由 `deploy/render-env.sh` 寫入。

**`REDIS_USER` 是本輪新增的第七個變數**（`NFR4.1(c)`／`S-5`）：K-01 的 `variables`
是封閉的六項，本單元的最小權限條款需要它才有落點。它**擴充了已核可的上游契約**，
故列入 `§〇` 而非當作既有六項的自然延伸。

**初版漏掉 `deploy.yml`，本輪補入**：`render-env.sh` 的機敏值**只從
`.github/workflows/deploy.yml` 的 `env:` 對照表進來**。新增 `REDIS_PASSWORD` 而不改
它，在 `render-env.sh` 的 `set -euo pipefail` 下 render 會直接中止。

**兩個 job 的改動不對稱（本輪更正初版的「兩個 job 都要改兩項」）**：

| job | `env:` 對照表 | required-secrets 步驟 |
|---|---|---|
| `deploy` | 要加（`:90–104`） | 要加（`:71–86`，硬編碼 `POSTGRES_PASSWORD`／`JWT_SECRET`） |
| `rollback` | 要加（`Restore the last-good deployment` 步驟，`env:` 在 `:193`、條目到 `:206`） | **不存在**——該 job 沒有等價的缺值守門 |

`grep -c "Require the secrets that must not default" .github/workflows/deploy.yml` 為
**1**。故 **rollback 路徑的缺值保護實際上落在 `NFR4.1` 為 `render-env.sh:44–49`
新增的必填檢查上**——這條依賴必須寫明，否則那條路徑的守門看起來像有而其實沒有。

- **可測判準**：`python3 scripts/validate_env_contract.py` 通過；且以空的
  `REDIS_PASSWORD` 觸發 workflow 時，deploy job 的 required-secrets 步驟**必須失敗**。
- **這道閘門的前提**：它只在該變數於 deploy compose 中被引用且**無 `:-` fallback**
  時才存在——見 `NFR8.1a`。

### `NFR8.1a` — `deploy/docker-compose.deploy.yml` 的 `backend.environment:`（**本輪補，審查 R-30**）

七個變數必須加進 `deploy/docker-compose.deploy.yml` 的 `backend.environment:` 區塊
（`:35–62`），且**引用時不得帶 `:-` fallback**。

**為何這是獨立的一條而非細節**：

1. **它是變數真正送進 backend 容器的唯一路徑**——`deploy/.env` 只是 compose 內插的
   來源，不會自動注入容器。漏加的後果是 `render-env.sh` 與兩份範本都正確，而 backend
   根本讀不到值。
2. **它同時是 `NFR8.1`／`NFR8.2` 那兩道閘門的成立前提**。
   `validate_env_contract.py:101–108` 的 `compose_variables()` 掃的是 deploy compose
   全文的 `${...}`，把**沒有 `:-` 預設**的視為 required；`:168–181` 與 `:184–196`
   只比對 `required - written`。所以那兩道閘門**只在變數於 deploy compose 中被引用
   且無 fallback 時才存在**——帶了 fallback 就靜默失去閘門。
3. **repo 自己記載了這件事**：`deploy/docker-compose.deploy.yml:39–40` 的註解逐字為
   「No fallback on purpose: this makes scripts/validate_env_contract.py require
   render-env.sh and deploy/.env.example to keep writing it」。三份產出在本輪之前
   對此零字。

- **可測判準**：七者在該檔中各有一處 `${...}` 引用，且**皆不含 `:-`**（`grep` 可判）。
- 該檔同時是 Redis／Ollama 兩個新服務區塊的所在，故它也是 `NFR8.7`／`NFR8.8`／
  `NFR8.9`／`NFR4.1(c)` 的落點。

### `NFR8.1b` — `deploy/docker-compose.test.yml` 的 `backend.environment:`（**本輪補，審查 R-36**）

CI 測試 stack 的 backend 同樣只從自己的 `environment:` 區塊（`:32–39`）收環境變數，
**且該 stack 的值全部內嵌自帶預設**（符合 `project.md` 對 CI 測試範圍的描述）。

**為何它非列不可**：本單元已在兩處**無條件承諾** Redis 要進那份 compose——
`§三` 的服務數表兩個「變更後」欄都寫「＋Redis（session 測試需要）」，
`NFR8.7` 的可測判準逐字是「**兩份** compose 的 `redis` service 區塊內 `ports:`
命中數為 0」。**Redis 進去了而 backend 收不到 `REDIS_URL`／`REDIS_PASSWORD`／
`REDIS_USER`，就是 `NFR8.1a` 第 1 點描述的同一個失敗模式**，而這一側連
`NFR8.1a` 那兩道閘門都沒有——`validate_env_contract.py:40` 的 `DEPLOY_COMPOSE`
是該檔**唯一**的 compose 路徑，`docker-compose.test.yml` 從頭到尾不在它的作用域內。

- **可測判準**：該檔 `backend.environment:` 內有 Redis 三者，且依該 stack 的既有
  慣例**自帶測試用預設值**（不從外部 `.env` 取）。
- **沒有機械閘門**——見第四節。

### `NFR8.2` — `deploy/.env.example` 列出七者

同一個 PR 內列出七者，且**不得**把 compose 自行推導的值（`DATABASE_URL`、
`VITE_API_BASE_URL`）或本機來源（`localhost`、`127.0.0.1`）寫進去。

- **這道閘門的前提與 `NFR8.1` 相同**：`validate_env_contract.py:186` 的
  `validate_deploy_template_is_complete()` 與 `:170` 共用同一個
  `compose_variables(DEPLOY_COMPOSE)` required 集合，故它同樣**只在該變數於 deploy
  compose 中被引用且無 `:-` fallback 時才存在**——見 `NFR8.1a`。

### `NFR8.3` — `backend/.env.example` 列出 backend 讀得到的變數

`validate_env_contract.py:242–261` 的 `validate_local_dev_template_is_complete()`
會掃 `backend/**/*.py` 的 `os.environ.get`／`os.getenv`，任何 backend 讀得到而
`backend/.env.example` 未記載的變數即紅燈。`U6` `embedding-port` 與 `U10`
`session-store` 讀這些變數時會觸發（七者中 backend 實際會讀的那幾個）。

- **兩個既有例外**（實作時須知）：`SDK_INTERNAL_KEYS`（`:69`）內的名稱不列入比對；
  路徑含 `tests` 或 `.venv` 的檔案不掃（`:246`）。
- **時序**：觸發點在 `U6`／`U10` 落地時，不在本單元。但**範本必須由本單元先補上**，
  否則那兩個單元的第一個 PR 必然紅燈。

### `NFR8.4` — `LOCAL-DEV.md` 同步

`project.md ## Mandated` 逐字要求：異動任一 `.env.example` 或 `render-env.sh` 時
必須同步 `LOCAL-DEV.md`——它是唯一寫下本機執行全部功能所需隱性前置條件的文件，
**過期即等於沒有**。

本單元要寫進去的新前置條件：

1. Redis 可達。
2. `EMBEDDING_PROVIDER` 的選值與各值的額外前置（`ollama` 需服務可達且模型已拉、
   `fastembed` 需首次下載模型）。
3. **本機 db 的主版本升級（強式敘述，本輪更正）**：repo 根 `docker-compose.yml` 的 db
   由 `postgres:15-alpine` 改為含 pgvector 的 PG 18。**開發者的本機 data volume 必須
   重建**（跨主版本）。**不做這一步的後果不是「記憶功能不可用」，而是
   `psql -f schema_rbac.sql` 整個交易中止、一張表都建不出來**——見 `NFR6.2a`。
   這一條必須寫在 `LOCAL-DEV.md` 的**必做前置**，不是附註。
4. **更正 `LOCAL-DEV.md:105` 的既有錯誤敘述（本輪新增，審查 R-38）**：該行逐字說
   `schema_rbac.sql` 建立「全部資料表、308 列 RBAC 預設矩陣，以及預設帳號
   **`admin` / `admin123`**」，而 `schema_rbac.sql:11` 逐字為「**不建立固定密碼
   管理員；bootstrap admin 由後端依環境變數建立**」，全檔唯一 `INSERT INTO` 是
   `:321` 的 `role_permissions`。**這是本 repo 既有的文件漂移，不是本 intent 造成的**
   ——但本單元在升版程序中依賴 `LOCAL-DEV.md` 的準確性，且本輪正是因為信了它而
   寫錯一整段論證（見 `NFR6.3(c)` 的更正）。順手更正它比留給下一個人再踩一次便宜。

### `NFR8.5` — `DEPLOY.md` 同步

**初版在此只列了三項，而 `NFR6.3(b)` 逐字宣告「`NFR8.5` 要求這三條全部寫進
`DEPLOY.md`」——宣告了承載者、承載者不承載（審查 R-19）。** 本輪逐項列全：

| # | 要寫進 `DEPLOY.md` 的 | 來源 |
|---|---|---|
| 1 | **三條排序不變量**：指定順序（先轉換、後合併）＋反向順序會靜默成功的後果；三個 rollback 處置選項與**各自的覆蓋範圍**，以及採用了哪一個；相容性前置檢查在 `deployment-pipeline` 落地前只是人工前置 | `NFR6.3(b)` |
| 2 | **七步升版程序**，走的是 **dump/restore**（本輪已收斂為唯一路徑，見 `NFR6.3(a)`） | `NFR6.3(c)` |
| 3 | **步驟 4 的兩條硬條件**（未掛 initdb 目錄、backend 必須是停止的）**與採用哪一種做法**（裸映像還原，或暫移 initdb 掛載），含兩者代價不對稱的說明 | `NFR6.3(c)` |
| 4 | **volume 命名的完整值**與交給 compose 的驗證方式（compose 專案名為 `cloud360`，故具名 volume 實際是 `cloud360_<宣告名>`） | `NFR6.3(c)` 步驟 4 |
| 5 | **回退窗口的保留期限**（舊 volume 與備份同時保留多久） | `NFR6.3(c)` 步驟 7 |
| 6 | `NFR6.2` 的擴充由兩處承載的說明 | `NFR6.2` |
| 7 | `NFR8.9` 的日誌 `max-size`／`max-file` 選值 | `NFR8.9` |
| 8 | **採第二項處置時的收尾步驟**：窗口驗證通過後以另一個 PR 復原 `rollback` job，並確認復原後的第一次部署有 rollback 武裝 | `NFR6.3(b)` 不變量 2 |

`DEPLOY.md` 不在 K-01 的 `sync_obligations` 三項內，但 `project.md ## Mandated` 的
schema 同步規則要求「部署必知的 schema／seed 行為」變更時同步它。

### `NFR8.6` — 憑證值不得含 `$`

docker compose 會對 `--env-file` 的值做內插，`ab$cd` 會被無聲截斷成 `ab`，
資料庫因此以**遠弱於預期的密碼**運行且無任何錯誤。**擋阻機制須由本單元擴充**，
不是既有保證——見 `NFR4.1`。

### `NFR8.7` — Redis 對外暴露面為零

Redis 容器**不得宣告 `ports:`**，僅以 compose 內部服務名被 `backend` 存取。

- **可測判準**：兩份 compose 的 `redis` service 區塊內 `ports:` 命中數為 **0**；
  `REDIS_URL` 的主機名為 compose 內部服務名而非 `localhost`／`127.0.0.1`。
- **初版宣稱過強，本輪更正**：初版寫「`localhost` 那一半有閘門」。實際上
  `validate_env_contract.py:212–240` 的 `validate_scopes_are_separated()` **只讀
  `deploy/.env.example` 與兩個 dev 範本，不掃 `render-env.sh`**——而真正進到 stack 的
  `REDIS_URL` 值是 `render-env.sh` 寫的。且依 `deploy/.env.example:22–27` 的既有慣例
  （機敏／示例值留空、例子寫進註解），一個留空的 `REDIS_URL=` 對那條掃描**完全不
  觸發**。故這一項實質上也沒有閘門。

### `NFR8.8` — Ollama 對外暴露面為零，且其存取控制只有這一層

Ollama 容器**不得宣告 `ports:`**，僅限 compose 內部網路。

- **編號**：本條掛在 `NFR8`（新增元件的**部署設定完整性**）而非 `NFR4`。
  「這個容器不得 publish port」是一項部署設定屬性，與 `NFR8.7` 同源；`NFR4` 的主題是
  狀態外部化，Ollama 與它無關。
- **這是刻意決定，不是遺漏**（`[N4]`=A 定案）。Ollama 的 HTTP API **原生沒有任何
  認證機制**，K-01 也沒有為它定義任何憑證變數。
- **前提**：「不得 `publish port`」。
- **前提被破壞時的後果**：任何人只要能到達那個 port，就能**無憑證**呼叫 Ollama 的
  完整 API——列出並下載模型、以任意輸入產生 embedding、耗盡該容器的 CPU 與記憶體。
  本單元沒有第二層控制攔得住它。
- **未採用的替代方案與其代價**：反向代理加 basic auth（多一個容器與一組憑證）；
  另切一個只含 `db`／`backend`／`ollama` 的內部 network（比 basic auth 輕，但 compose
  網路設定變複雜）。

### `NFR8.9` — 兩個新容器的記錄承載

- **承載**：兩個容器**不指定 `driver`**（沿用 docker 預設的 `json-file`），
  但**必須指定 `logging.options`**——預設 driver 無輪替上限，不設 `max-size` 與
  `max-file` 會讓單機 staging 的磁碟被日誌塞滿。具體值由部署者決定並記入 `DEPLOY.md`。
- **零認證前提下的可辨識性（誠實回答）**：Ollama 的記錄會留下請求的到達，
  但**不含任何呼叫者身分**——因為沒有認證，本來就沒有身分可記。所以「未授權的
  Ollama 呼叫在記錄上是否可辨識」的答案是**否**。
- **這是 `NFR8.8` 已接受代價的一部分**：網路隔離成立時，能到達它的只有同 compose
  網路的服務，身分問題不存在；隔離一旦被破壞，**既沒有認證擋、也沒有記錄可追**。
  兩層同時失效是這個決定的真實代價。
- **沒有機械閘門**——見第四節。

### `NFR9.1` — 本機 embedding 對外部花費的貢獻為零

`requirements.md` NFR9 逐字：本平台自身的 LLM 花費上限由 OpenRouter 後台承載，
編排層以「盡量省」為設計原則。

- **本單元的貢獻**：`ollama` 與 `fastembed` **兩個選項皆為本機執行**，對 OpenRouter
  的花費貢獻為零。本單元不為 embedding 新增任何外部 API 呼叫。
- **`[N3]`=A 的退路不改變這一點**，且退路同時是更小的攻擊面：`fastembed` 在 FastAPI
  行程內執行，不新增任何服務、暴露面或憑證。
- **代價不是省下來的**：embedding 改在同一台主機的 FastAPI 行程內算，吃的是同一份
  CPU 與記憶體。

---

## 三、上游 NFR 的覆蓋與不適用判定

| inception NFR | 對本單元 | 落點 |
|---|---|---|
| `NFR1` 意圖識別準確率 | **不適用** | `U11 intent-router`；量測機制落 `build-and-test` |
| `NFR2` 跨頁面上下文保留率 | **不適用** | `U10 session-store` ＋ `build-and-test` |
| `NFR3` 首字回應時間 | **不適用（理由本輪更正）** | `requirements.md` NFR3 **自己**把 Redis 往返算進預算並逐字判定「在同一個 compose 網路內約 1ms，可忽略」。本單元不新增任何請求處理。**但本輪新增的 AOF 會改變該路徑的寫入成本**，故已於 `NFR4.2` 補上 `appendfsync` 的選值約束 |
| `NFR4` 狀態外部化與重啟還原 | **適用** | `NFR4.1`、`NFR4.2`、`NFR4.3` |
| `NFR5` WebSocket 契約閘門 | **不適用** | `U2 brain-ws-contract` |
| `NFR6` 記憶層 schema 隔離與其驗證 | **適用（承載面），但其驗證面目前不可滿足** | `NFR6.1`、`NFR6.2`、`NFR6.2a`、`NFR6.3`。**驗證載體（真實 PG 的 CI job）被上游兩處逐字釘成 `postgres:16-alpine`，與本單元的 PG 18 ＋ pgvector 直接衝突**，見 `NFR6.1` 落點 3 |
| `NFR7` episodic memory 保存與刪除稽核 | **Deferred** | 承載面 `NFR7.1`；加密手段 `OQ-3` → **`U5`／`U8` 的 `nfr-design` 迭代**，非本單元跑過即成立 |
| `NFR8` 新增元件的部署設定完整性 | **適用（完全落在本單元）** | `NFR8.1`–`NFR8.9` |
| `NFR9` 成本原則 | **適用** | `NFR9.1` |
| `NFR10` 路由層模型可替換性 | **不適用** | `U11`；`OQ-4` 於 `U11` 的迭代定案，**尚未定案** |
| `NFR11` 跨功能任務的頁面切換次數 | **不適用** | UI 單元 ＋ `build-and-test` |

---

## 四、機械閘門的實際作用域（誠實記載）

### 真的有閘門的三項

初版寫「唯一真的有閘門的一項是 `NFR8.3`」——**那是錯的，而且與本檔 `NFR8.1` 自己
把 `validate_env_contract.py` 通過列為可測判準互相矛盾**。實際有三項：

| 需求 | 閘門 | 驗什麼 |
|---|---|---|
| `NFR8.1` | `validate_env_contract.py:168–182` `validate_deploy_stack_is_fully_supplied()` | `render-env.sh` heredoc 的**名稱**完整性（**不驗值**） |
| `NFR8.2` | 同檔 `:184–197` `validate_deploy_template_is_complete()` | `deploy/.env.example` 的**名稱**完整性（**不驗值**） |
| `NFR8.3` | 同檔 `:242–261` `validate_local_dev_template_is_complete()` | `backend/.env.example` 對照 backend 實際讀取；兩個例外見 `NFR8.3` |

三者皆在 CI 的 `repo-contract` job 跑，缺一即紅燈。

**但前兩者是有條件的**：它們的 required 集合來自 `compose_variables(DEPLOY_COMPOSE)`，
所以**只在該變數於 deploy compose 中被引用且無 `:-` fallback 時才存在**——
漏寫整個變數時，**兩道閘門會同時靜默**（見 `NFR8.1a`）。此外**前兩者只驗名稱不驗值**——
空值的守門是 `deploy.yml` 的 required-secrets 步驟與 `NFR4.1` 新增的
`render-env.sh` 必填檢查，不是這個 validator。

### 沒有閘門的九項

| 項 | 為什麼沒有閘門 | 目前唯一的守門機制 |
|---|---|---|
| `NFR8.7`／`NFR8.8` 的 **`ports:` 不得出現** | 該 validator 檢查變數，不解析 compose 的 `ports:` 宣告 | 人工審查 PR diff |
| `NFR4.2` 的 **Redis 具名 volume ＋ AOF ＋ 自動 rewrite 不得關閉** | 同上——不檢查 `volumes:` 或 Redis 設定 | 人工審查 ＋ 實際重啟驗證 |
| `NFR6.3` 的 **PG 16→18 升版程序** | 那是 `DEPLOY.md` 上由人執行的程序，沒有任何 CI 會驗證它被執行過 | 部署者遵循文件 |
| **`NFR6.1` 的四處 image 一致** | `validate_env_contract.py:40` 的 `DEPLOY_COMPOSE` **只開 `deploy/docker-compose.deploy.yml` 一個 compose 檔**；`docker-compose.test.yml` 與 repo 根的 compose 從頭到尾不在它的作用域內 | 人工審查 |
| **`NFR8.9` 的 compose `logging.options`** | 同上——validator 不解析 `logging:` 宣告 | 人工審查 |
| **`NFR4.1(c)` 的 Redis 設定資產**（ACL 使用者 ＋ AOF 三組設定的承載） | 同上——validator 不解析 `command:` 或掛載的設定檔 | 人工審查 ＋ 以 `NFR4.1(b)` 的拒絕測試間接驗證 |
| **`NFR8.1a` 本身**（七者進 deploy compose 的 `backend.environment:` 且不帶 fallback） | 漏寫整個變數時，上表前兩道閘門**同時靜默**——它們的 required 集合正是從這裡算出來的 | 人工審查 PR diff |
| **`NFR8.1b`**（三者進 test compose 的 `backend.environment:`） | `validate_env_contract.py:40` 的 `DEPLOY_COMPOSE` 是該檔唯一的 compose 路徑，test compose **完全不在作用域內** | 人工審查 ＋ `ui-regression` 實跑時的行為 |
| **`rollback` job 的存廢**（`NFR6.3(b)` 不變量 2 的停用與復原） | **沒有任何 validator 看得到 workflow job 的存廢**——停用後忘了復原，此後每次部署失敗都沒有自動還原，而沒有任何機制會提醒 | 部署者遵循 `DEPLOY.md` 的收尾步驟 |

**這九項不是「缺工具」的抱怨，是把宣稱強度對齊到機制的實際強度。**
`team.md` 已載明一例同型錯誤：`tsc -b` 看似有型別保護，實際對「後端加欄、前端漏接」
無效。

補上閘門的具體做法（非本單元交付，列為候選）：擴充 `validate_env_contract.py`
使其解析**三份** compose 的 `image:`、`ports:`、`volumes:` 與 `logging:` 宣告，
斷言「本 intent 新增的兩個服務無 `ports:`」「redis 有具名 volume」「**三份 compose**
的 db image 值相同」「兩個新服務皆設 `logging.options`」「redis 掛載了設定資產」。

**「三份 compose」與 `NFR6.1` 的「落點 1–4」不是同一個數**：`NFR6.1` 的落點 3 是
`N-2` CI job 的 service container，寫在 **workflow 檔**而非 compose 檔，解析 compose
的 validator 驗不到它；落點 5 是 volume 宣告。故 validator 能涵蓋的是三份 compose
的 image 加 volume 宣告，落點 3 只能靠人工審查與 `U5` 的迭代確認。

---

## 五、本站刻意不決定的事

- **episodic memory 的加密手段**：`OQ-3`，落點見 `NFR7.1`（**不是本站**）。
- **真實 PostgreSQL 的 CI job**：回補項 `N-2`，是 `U5 memory-data` 的交付。本單元
  只標出它與映像的上游逐字衝突（`NFR6.1` 落點 3）。
- **`appendfsync` 與 AOF rewrite 的具體值**：`U10`／`nfr-design`，但須受 `NFR4.2`
  的兩條約束。
- **Redis ACL 專用使用者的確切指令與 key pattern 集合**：`U10 session-store`
  最清楚它實際需要哪些指令；本站只定「不得共用 `default`」與其驗證方式。
- ~~**升版走 dump/restore 還是 `pg_upgrade`**~~：**本輪已收斂為只走 dump/restore**
  （`NFR6.3(a)`），`pg_upgrade` 在本部署形狀下沒有承載者。此處不再是開放選擇。
- **步驟 4 採「裸映像還原」還是「暫移 initdb 掛載」**：由部署者決定，但
  `NFR6.3(c)` 要求在 `DEPLOY.md` 寫明採用哪一種。
- **Redis 設定資產採 compose `command:` 覆寫還是掛載設定檔**：由 `U10` 決定；
  本站只要求它存在且承載 `NFR4.1(b)` 與 `NFR4.2` 的設定。
- **兩個容器的 `max-size`／`max-file` 具體值**：部署者決定，記入 `DEPLOY.md`。
- **`OQ-4`（路由層模型定案）**：落點雖是本 stage，但屬 **`U11 intent-router` 的
  迭代**。在此記下，避免它因為「本 stage 已跑過」而被當成已定案——**它還沒有。**

---

## 六、本單元查出並已當場修復的一項工作流程缺口（結案紀錄）

**`functional-design` 曾被整站誤標為跳過（`[S]`），影響其餘 14 個單元。缺口已於
2026-09-26 關閉，下游不需再處置。** 本節保留全文而非刪除，是為了讓下游看得出這個
缺口存在過、怎麼被發現、怎麼被關掉——而不是只看到一個乾淨的現況。

- **成因**：本單元在審查後為了解除 review-freeze 而重啟 stage，該復原動作執行的
  **forward** jump 把 `functional-design` 標為跳過。理由逐字
  `Skipped by jump to nfr-requirements (forward)` 在 audit shard 的 `:18550`。
- **影響範圍**：`functional-design` 的 `produces_kinds` 涵蓋 `service`／`spec`／`ui`／
  `library`，即 `U2`–`U8`、`U10`–`U16` 共 **14** 個單元的 `entities.md`、`rules.md`、
  `functional-spec.md`、各自的 `traceability.json` 與（UI 單元的）
  `frontend-components.md`。對 `brain-infra`（`packaging`）它本來就 kind-vacuous，
  所以**本單元不受影響，其餘 14 個單元受影響**。
- **為什麼它是 Major 而不是瑕疵**：`nfr-design` 把 `functional-spec` 列為
  **`required: true`**，所以 `U2 brain-ws-contract`（`kind: spec`）一走到 3.3 就會撞到
  真缺口，而缺口在依賴圖上看不出來——stage checkbox 是 `[S]` 這件事不在任何 artifact
  裡，只在 state 檔。
- **修復方式（已執行）**：`jump execute --target functional-design --direction
  backward`。事件在 audit shard 的 `:20661`（`**Event**: STAGE_JUMPED`）與 `:20662`
  （`**Direction**: BACKWARD`）。該事件的 `Changed Upstream Artifacts` 欄由引擎自行
  列出 **14 個單元目錄**下的 functional-design 產出路徑——這是「14」的獨立第二來源，
  不是本檔自行推算。
- **修復後的狀態（可複驗）**：`aidlc-state.md:89` 現為
  `- [-] functional-design — EXECUTE`，同檔 `:31` 為
  `- **In Progress**: functional-design`。`[S]` 已不存在。
- **修復的代價，已承擔完畢**：該 backward jump 重設 `functional-design` 與
  `nfr-requirements` 兩個 stage（其餘十個本來就是 `[ ]`、不在可重設集合內），並作廢
  本單元原有的結算與審查收據（同一事件的 `Invalidated Downstream Artifacts` 與
  `Invalidated Downstream Reviews` 兩欄逐字列出本單元三份產出）。三份 artifact 的
  檔案內容未被刪改；本單元在新 attempt 上重新結算，並利用新的審查預算把前一輪遺留
  的 R-50（Redis ACL 設定資產的量詞）一併修掉。

---

## Assumptions & Open Questions

- PG 16 → 18 的升版路徑（**本輪已收斂為 dump/restore 唯一路徑**）與 pgvector 在
  PG 18 的可用性**本輪未實地驗證**。`NFR6.3` 的步驟 3（備份須已在別處還原驗證過一次）與
  步驟 7（回退窗口）正是為此存在 [assumption]
- Ollama 的記憶體需求（runtime 約 2GB、`bge-m3` 約 1.2GB）取自一般認知，
  **未在 `192.168.10.10` 實測**。`NFR9.1` 的退路判定依賴該實測，而實測本身是 B1
  的第一件事 [assumption]
- `NFR6.1` 落點 3 的處置假設「該 CI job 尚未存在，故改的是尚未寫下的東西」。若
  `U5` 已依上游逐字把 `postgres:16-alpine` 寫進 workflow，處置就變成修改既有檔案
  並需要一次上游對齊的說明 [assumption]
- `NFR8.9` 的「Ollama 記錄會留下請求的到達」未實測 Ollama 的預設 log 等級，只依其為
  一般 HTTP 服務的通則。若實測發現它預設不記錄請求，則「可辨識性為否」的結論更強 [assumption]
- `NFR4.1(b)` 的 Redis ACL 條款是本站承接 `requirements.md:451` 的逐字義務而新增
  （`S-3`）。上游沒有任何 FR／NFR 承載它，故它是本階段新增的工作量，需回補進 scope [assumption]
- 本檔的四面向判定與 PBT 判定是本站對 `project.md` hard constraint 的逐項對照結果 [assumption]
