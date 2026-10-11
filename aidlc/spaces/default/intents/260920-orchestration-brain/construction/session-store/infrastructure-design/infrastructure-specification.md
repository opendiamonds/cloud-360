# Infrastructure Specification — `U10 session-store`

> 設計階段產出：說明**需要什麼基礎設施與為什麼**，不是 IaC 實作。
> 內容以表格為主，散文只放理由。

## 本檔的上游

| 上游 | 它給了什麼 |
|---|---|
| `performance-design.md` | Hash ＋ Lua 的結構、連線池 min 5／max 20 與其算式 |
| `security-design.md` | ACL 連線身分、Lua 的 ACL 前提、日誌禁令 |
| `scalability-design.md` | 256 MB 的容量門檻表與「先壞什麼」 |
| `reliability-design.md` | `noeviction`、逾時／重試參數、還原五項與 AOF 的角色 |
| `observability-design.md` | `MEMORY STATS` 採集設計；三個原因碼 |
| `logical-components.md` | 模組分解、失敗域、共用資源與 `OPEN-N10-7` |
| `components.md`（`inception/domain-design`） | `SessionContext` 的 `external_dependencies` 逐字把 Redis 列為 `kind: cache`、`purpose: session 狀態外部化；第 5 個部署服務` |
| `functional-spec.md` | `W1`–`W8`；`EC3` 的不變量 |
| `contract-summary.md`（`K-01`／`K-09`／`K-11`） | 環境變數契約；同一個 session key 的共用 |

## 一、本單元的基礎設施增量只有三項

**Redis 服務本身已由 `U1 brain-infra` 佈建完成**——`codekb/chiton/technology-stack.md:206`
逐字「**服務已佈建**（`redis:8-alpine`、AOF volume、ACL、healthcheck）；
`REDIS_URL`／`REDIS_USER`／`REDIS_PASSWORD` 已由 `render-env.sh:121` 等寫入並列於
兩份 `.env.example`……**env contract 的 blocking 工作已完成**」。

**本單元不重做那件事。** 增量是三項，逐項列出其確切落點：

| # | 變更 | 落點 | 來源 |
|---|---|---|---|
| 1 | `--maxmemory-policy` 由 `allkeys-lru` 改為 **`noeviction`** | `deploy/docker-compose.deploy.yml` 的 redis `command:`（現值在 `:234-235`） | `[N3]`=A；`NFR4.50`／`NFR8.42` |
| 2 | 新增訊息筆數上限的環境變數（值 **200**，**無預設值**） | `deploy/render-env.sh`（寫入）＋ `deploy/.env.example`（列出）＋ `backend/.env.example`（列出）＋ `deploy/docker-compose.deploy.yml`（傳入 backend）＋ `deploy/docker-compose.test.yml`（內嵌含預設，CI 契約要求的形狀） | `[N2]`=A；`NFR8.40` |
| 3 | 新增 Python Redis 客戶端依賴 | `backend/requirements.txt` | `NFR8.41`；實讀確認該檔**無任何 Redis 客戶端** |

**第 2 項是 blocking**：`project.md ## Mandated` 逐字要求「新增 compose 消費的變數時，
**同一個 PR** 必須讓 `render-env.sh` 寫它、`deploy/.env.example` 列它」，
且 `scripts/validate_env_contract.py` 在 CI 的 `repo-contract` job 執行。

**第 1 項不需要同步到 CI 測試 stack**（`[I1]` 問題檔已實讀確認）：
`deploy/docker-compose.test.yml:120-121` 逐字「NO `--appendonly`, **NO `--maxmemory`**」，
而 `maxmemory-policy` 只在觸及 `maxmemory` 時生效。`nfr-requirements` 審查 `R-04`
指派的「須確認而非假設」就此關閉。

## 二、Deployment

| Facet | Choice | Rationale |
|---|---|---|
| **Compute model** | 容器（Docker Compose），單一自有主機 `192.168.10.10` | `ADR-0007`；production 不在範圍（`ADR-0001`／`ADR-0002`）。本單元不引入新的計算模型 |
| **Networking topology** | 僅 compose 內部網路；Redis **無 `ports:`** | `K-01` 逐字 `exposure: compose 內部網路only；不得 publish port`。本單元為 `in-process` 契約（`BR5.3`），**不新增任何對外面** |
| **Storage strategy** | Redis AOF 寫入 named volume `redis_aof` | `NFR4.52`。**該 volume 是為重啟還原而存在，不是備份**（`reliability-design.md` §六）——這句話寫在這裡，因為「有 volume」最容易被誤讀成「有備份」 |
| **Environments** | 本機 dev／CI 測試／staging **三個**；**無 production** | `project.md ## Mandated` 的三環境契約。三者的 Redis 設定**刻意不同**（見下表），這不是漂移 |
| **IaC approach** | **Docker Compose ＋ `render-env.sh`**，無 CDK／Terraform／CloudFormation | 如實記載。`infrastructure-guide.md` 的 IaC 工具表把 Docker Compose 列為「Local development, simple multi-container apps / **Not for production orchestration**」——本專案 production 不在範圍，故此限制不構成問題，但**必須寫下來**而不是假裝有 IaC |
| **Resource sizing** | Redis `maxmemory 256mb`、容器上限 `768m` | `U1` 的註解逐字定下 `container memory limit >= maxmemory × 1.5 + 256MB`（`256 × 1.5 + 256 = 640 ≤ 768`）。**改任一邊都要重算**（`scalability-design.md` §擴展手段） |

### 三個環境的 Redis 設定差異（刻意的，非漂移）

| 設定 | 本機 dev | CI 測試 | staging |
|---|---|---|---|
| `appendonly` | 未設 | **未設**（檔頭逐字「no persistence by design」） | `yes` |
| `maxmemory` | 未設 | **未設** | `256mb` |
| `maxmemory-policy` | 未設 | 未設（無 `maxmemory` 故無意義） | **`noeviction`**（本單元的變更 1） |
| named volume | 無 | **無**（全檔零 top-level `volumes:`，實測 `grep -c` 回 `0`） | `redis_aof` |
| ACL app 使用者 | 同形 | `+@all -@admin -@dangerous` | `+@all -@admin -@dangerous` |

**最後一列是本單元最依賴的一致性**：`[D1]`=A 的 Lua 需要 `EVAL`，而兩個 stack 的
ACL 規則**逐字相同**，故 CI 與 staging 在這一點上不會分歧。
（`nfr-design` 審查已實地裝 Redis 8.8.0 跑過該規則，`EVAL`／`EVALSHA`／`SCRIPT LOAD` 皆通過。）

**前四列的差異是刻意的，而它的代價是 `[I1]`**：CI 沒有持久化，所以重啟還原驗證
在那裡跑不出意義，這正是 `[I1]`=B 把它放到部署後的理由。

## 三、Infrastructure Services

| Service | Role | Configuration | Notes |
|---|---|---|---|
| **Redis 8** | cache／session store | `appendonly yes`、`maxmemory 256mb`、**`maxmemory-policy noeviction`**（本單元變更）、ACL 雙使用者、healthcheck `redis-cli ping` | 由 `U1` 佈建，本單元是**第一個真實消費者**（`technology-stack.md:206` 實測：`backend/` 應用程式碼零 Redis import）。healthcheck 的已知限制：`U1` 註解逐字自承它「does NOT prove the ACL user works」且「passes during AOF loading」 |
| **PostgreSQL（pgvector pg18）** | database | 不由本單元設定 | 本單元**只經 `K-07` 唯讀**；不持有連線、不建 schema、不寫任何表 |
| 其餘四個服務（backend／frontend／ollama／cloudflared） | — | 不由本單元設定 | 列出是為了說明 256 MB 的脈絡：六個服務共用同一台主機，`ollama` 是記憶體大戶（`technology-stack.md:167`） |

## 四、Shared Infrastructure

| Shared Resource | Owner Unit | Consumer Units | Access Boundary |
|---|---|---|---|
| Redis 實例 | `U1 brain-infra` | `U10`（session 狀態）、`U12`（工作項集合，同一個 session key） | 同一個 ACL 使用者；**無資料隔離**——兩者在同一個 key 的同一個 Hash 之下 |
| 同一個 session key 的 Hash 欄位 | `U10`（本單元） | `U12` | **命名空間約束**：本單元用 `seg:`／`tgt:`／`meta` 三個前綴；`U12` 的前綴不得衝突。見 `OPEN-N10-7` |
| `redis_aof` volume | `U1` | 全部 Redis 使用者 | 單一 volume，無隔離 |
| PostgreSQL | `U4`／`U5` 等 | `U10` 經 `K-07` 唯讀 | `K-07` 的 `BR6.1` 負責擁有者範圍檢查 |

### 兩項共用帶來的具名風險（承 `nfr-requirements`／`nfr-design` 的記載）

- **`OPEN-N10-3`**：工作項集合共用同一個 key，但**不在**本單元的 300 KB／session
  記憶體上界之內。`NFR4.40` 的 300 session 承諾因此建立在一個沒人保證過的前提上。
  承接 `U12`（游標之後）。
- **`OPEN-N10-7`**：Hash 欄位的命名空間。**這個風險在 `[D1]`=A 之前不存在**
  （值的結構未定時談不上欄位衝突），是本單元的結構決定製造出來的，故由本單元記。
  承接 `U12`（游標之後）。

## 五、本單元**不**需要的基礎設施（逐項附理由）

| 不需要 | 理由 |
|---|---|
| 新的容器／服務 | Redis 已存在；本單元是 backend 行程內的模組 |
| 對外埠、ingress、負載平衡 | `BR5.3`：不暴露端點 |
| Redis 副本／Cluster | `reliability-requirements.md` 已明寫接受單點；`scalability-design.md` 已否決分片 |
| 備份排程 | RPO 已定為「24 小時內的 session 可接受全失」 |
| 新的 CI job | `[I1]`=B 選擇部署後驗證，正是為了不新增 job |
| Secrets 管理機制 | `REDIS_PASSWORD` 已由 `U1` 的 `render-env.sh` 路徑承載；本單元不新增任何憑證型 secret |
