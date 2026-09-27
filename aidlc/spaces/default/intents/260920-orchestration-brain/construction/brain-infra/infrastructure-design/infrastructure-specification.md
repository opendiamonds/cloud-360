# Infrastructure Specification — `brain-infra`（U1）

## 這份檔在做什麼

`brain-infra` 是 `kind: packaging`。與前兩站不同，本站的 `produces_kinds` 對 `packaging`
**四項全適用**，所以本單元交付 `infrastructure-specification.md`、`monitoring-design.md`、
`cicd-pipeline.md` 與 `traceability.json`，沒有 kind-vacuous 的缺席。

本檔只寫**需要什麼基礎設施與為什麼**，不寫可實作的 IaC 或 compose 片段——完整的 compose
宣告屬 `code-generation`。上一站（`nfr-design`）的教訓已套用於此：**設計文件裡的可執行程式
碼會成為缺陷來源**（那裡有三項發現出在兩段 bash 上），所以本檔的資源上限、`logging:` 與
`healthcheck` 都以**契約與推導方式**表述，不給具體 YAML。

本檔不重述上游已鎖定的決定（見問題檔前言的十一項對照表），只設計它們沒有碰到的部分。

---

## 〇、本階段新增、已核可 scope 尚未涵蓋（**需回補**）

| # | 項目 | 由來 | 為何不是既有範圍的自然延伸 |
|---|---|---|---|
| **S-8** | **記憶體上限：deploy stack 六個服務 ＋ CI test stack 四個服務，共十個服務項、兩份檔**（審查 R-13a：初版標題只寫「六個」，低報了 CI 側那四個） | `[I2]`=C ＋ `[I2b]`（本輪經使用者裁決改為「先以公開基準設值、限期複量」，見 `§二`） | 三份 compose 今日**完全沒有資源限制**（`deploy:`／`resources:`／`limits:`／`mem_limit`／`cpus` 零命中），所以這是本 repo 的**新模式**，不是既有形狀的延伸。且它為既有四個服務引入一條今天不存在的失敗路徑（容器被 OOM kill → `restart: unless-stopped` → 重啟迴圈） |
| **S-9** | **`logging:` 的 `max-size`／`max-file` 加在兩份 compose 的全部服務** | `[I4]`=A | `NFR8.9` 只要求**兩個新容器**。加到全部服務是刻意超出上游字面，理由見 §三 |
| **S-10** | **`DEPLOY.md` 新增磁碟空間前置條件** | 本站的覆蓋檢查查出（無對應上游 id、無對應問題） | 本單元新增 Ollama 模型（約 1.2GB）＋ Redis AOF，而 `NFR6.3` 的升版窗口內**同時存在三份全庫明文副本**（新 volume、保留中的舊 volume、dump 檔，見 `nfr-design` D-1 的涵蓋範圍表）。**沒有任何一處檢查過主機有沒有空間**，而空間不足的失敗發生在升版中途——最糟的時點 |
| **S-11** | **收窄 `nfr-requirements` `§五` 交給 `U10` 的決定範圍**：`appendonly`／`maxmemory`／`maxmemory-policy` 三項改為 compose `command:` 獨佔，`U10` 的 Redis 設定資產**不得包含**它們 | 本輪送審前自檢第 2 項查出 `appendonly` 無寫者後的連帶結果（審查 R-44 要求顯性化） | 上游 `security-requirements.md:756–757` 逐字把「`command:` 覆寫還是掛載設定檔」**整件事**交給 `U10`，並要求該資產承載 `NFR4.1(b)` 與 `NFR4.2` 的設定；把 `NFR4.2` 的核心設定從該資產拿走是**縮小已核可的指派**，不是實作細節。技術理由成立（`redis-server` 的 CLI 旗標會讓檔內同名值靜默失效），但需 `U10` 的 `functional-design` 明示接受或反對——**本站不代它決定** |

四項都需回補進 scope。`S-8`／`S-9` 的後果已在提問當下揭露；`S-10` 是本站覆蓋檢查的產物，
不是選項之一；`S-11` 是本輪送審前自檢與審查 R-44 的產物，**它的回補對象不只 scope，還包括
`U10` 的指派範圍**——若 `U10` 反對這個收窄，處置是回到「`appendonly` 住在哪裡」重新定案，
而不是讓兩份文件各自宣稱擁有它。

---

## 一、Deployment

| Facet | Choice | Rationale |
|---|---|---|
| **運算模型** | 單主機 **Docker Compose**，六個服務（`db`／`backend`／`frontend`／`cloudflared` ＋ 新增 `redis`／`ollama`） | ADR-0007 已定案的既有形狀。本單元只增服務、不改模型。**「第 5、6 個服務」有上游依據**：`components.md` 的 External Dependencies 表逐字寫 `SessionContext` → Redis「session 狀態外部化；**第 5 個部署服務**」、`MemoryStore` → Ollama「staging 的 embedding 運算；**第 6 個部署服務**，零 API 費用」 |
| **網路拓樸** | **兩個 user-defined bridge**：`edge`（`cloudflared`／`frontend`／`backend`）、`internal`（`backend`／`db`／`redis`／`ollama`）。**不得設 `internal: true`** | `nfr-design` D-3。唯一對外入口仍是 `cloudflared` 的 tunnel；`frontend` 的 host port 供 CI 的 Playwright 與部署後探測使用 |
| **儲存策略** | 三個具名 volume：PG 資料（本輪**改名**，`NFR6.1` 落點 5）、Redis AOF、Ollama 模型快取。CI test stack **不用具名 volume**（每次重建） | `NFR4.2`／`NFR4.3`。改名的理由是 `NFR6.3` 步驟 4 要求以新 volume 起 PG 18 |
| **環境佈局** | 三個範圍、**互不共用設定**：本機 dev（repo 根 `docker-compose.yml`）、CI test（`deploy/docker-compose.test.yml`，內嵌值）、部署（`deploy/docker-compose.deploy.yml` ＋ `deploy/.env`） | `project.md ## Mandated` 的三環境分離條款。**production 不在範圍**（ADR-0001／ADR-0002） |
| **IaC 取徑** | **沒有 IaC**——compose 檔本身即宣告，由 `deploy.yml` 在自架 runner 上 `up -d --build` | 既有形狀。ADR-0001／ADR-0002 把 direct production IaC 列為 out of scope，而 staging 是單主機，引入 Terraform／CDK 沒有承載對象 |
| **資源配置** | 六個服務全部設記憶體上限（CI test stack 另四個，共十個服務項）；**值以公開基準設暫定值**，`DEPLOY.md` 標記未量測並訂複量期限（見 §二） | `[I2]`=C ＋ `[I2b]` 的**反轉後版本**（問題檔 `I2b` 有逐字的反轉紀錄；審查 R-21） |
| **磁碟空間** | `DEPLOY.md` 新增前置條件，與全碟加密（`nfr-design` D-1）並列 | `S-10`，見 §四 |

---

## 二、Infrastructure Services

| Service | Role | Configuration | Notes |
|---|---|---|---|
| `db` | database | PostgreSQL **18** ＋ pgvector（`NFR6.1` 五個映像落點）。單一實例、**無複寫**。具名 volume（本輪改名）。`healthcheck` 沿用既有 `pg_isready` | 單一 superuser 連線是**既有基線**，最小權限拆分不在本單元範圍（`nfr-design` `§二` 的 `IAM-PG-SUPERUSER`） |
| `redis` | cache／session store | **AOF 開啟**（僅 deploy stack，`NFR4.2`；承載為 `command:` 的 `--appendonly yes`，見下方「AOF 的承載」專節——映像預設是 `appendonly no`）。**`maxmemory` ＋ `maxmemory-policy allkeys-lru`**（**僅 deploy stack**，比照同列 AOF 的範圍——審查 R-31：初版把它寫成無條件，而承載它的改動清單第 17a 項只列 deploy compose，兩種讀法後果不同），以 compose 的 `command:` 覆寫承載（`[I1]`=A ＋ 審查 R-05）。**CI test stack 不設 `maxmemory`**：該 stack 每次重建、session 不跨 run 累積，淘汰策略沒有作用對象。**ACL 專用使用者**（值不得為 `default`，`NFR4.1`）——**承載者為兩份 compose 各自的 ACL 設定資產或各自的 `command:` `ACL SETUSER`，見 `cicd-pipeline.md` `§五` 第 17b 項**（審查 R-38：初版只寫要求、沒寫承載者，與 `appendonly` 同一個「有讀者無寫者」形狀，而上游 `security-requirements.md:95` 逐字寫明 test stack 缺它的後果是每個 PR 的 `ui-regression` 都紅）。`restart: unless-stopped`。新增 `healthcheck`（`redis-cli ping`） | `appendfsync` 的具體值屬 `U10`，但受 `NFR4.2` 的兩條約束（所選值不得使 `NFR3` 的 P50 預算失守） |
| `ollama` | embedding provider | 模型 `bge-m3`（dense 維度須為 1024，與 `vector(1024)` 一致）。模型快取具名 volume。**記憶體上限必設**（它是本單元新增的最大消費者）。`restart: unless-stopped`。新增 `healthcheck`（`/api/tags`）。**模型取得機制必設，見下方專節** | 零認證，存取控制只有網段分段那一層（`NFR8.8` ＋ D-3）。資源數字**未在主機實測**，`NFR9.1` 的退路依賴該實測 |
| `frontend` | reverse proxy／static | nginx，唯一有 host port 的服務（`${FRONTEND_HOST_PORT}:80`）。`location /api/` → `backend:8000`，`location /` → `try_files` | 本單元不改它的設定，但部署後探測依賴 `location /api/` 的存在（`PROBE-CONTRACT` P-1） |
| `cloudflared` | tunnel | 既有。以 uid 1000 執行、憑證檔 0400。**ingress 已為串流與 WebSocket 調過**：`connectTimeout: 30s`（`deploy/cloudflared/config.yml:16`，註解逐字「The A1 design agent streams; don't let the tunnel cut it short.」）、`tcpKeepAlive: 30s`（同檔 `:18`，註解「WebSocket at `/api/collab/ws/{workspace_id}` must survive idle periods.」） | **必須排除在 `internal` 之外**（D-3 的核心理由）。**本單元不改 ingress 設定**，但上述兩項是 `U13 brain-gateway` 的 WS 端點能運作的既有前提——`components.md` 的 External Dependencies 表逐字記載「`BrainGateway` → Cloudflare Tunnel：對外暴露；**已為 WS 設 tcpKeepAlive 30s**」，本站實地複驗成立 |
| `backend` | application | FastAPI／uvicorn。**唯一橫跨 `edge` 與 `internal` 的服務** | startup 事件同步跑 `init_db()`，含 `create_all` ＋ 六個 `_ensure_*_schema`；這段是部署後探測重試窗口的長度來源 |

### ⚠ `bge-m3` 是怎麼進到模型 volume 的（審查 R-02，Critical——初版完全沒有這一項）

**初版的三處主張同時建立在一個不存在的機制上。** 官方 `ollama/ollama` 映像的 entrypoint
是 `ollama serve`——**它不會自動拉任何模型**。必須有人執行一次 pull。初版的 `§四` 寫
「首次啟動下載後常駐」、`monitoring-design.md` `§六` 寫「首次啟動要拉約 1.2GB，期間
`/api/tags` 會回一個空清單」、`cicd-pipeline.md` `§五` 的改動清單對 `ollama` 只寫「新增服務、volume、
healthcheck」——**三處都假設了一個沒有被設計的下載動作**。

**若照初版實作，後果是三件事同時成立且全部靜默**：

1. `/api/tags` **永久**回空清單（而非過渡態），所以那個 `healthcheck` **恆為健康且恆無
   模型**——它會通過，而服務其實不可用。
2. `NFR9.1`（本機 embedding 對外部花費的貢獻為零）在**執行期**失守：embedding 呼叫失敗後
   若有退路就走外部 API、沒有退路就整條功能壞掉。
3. 模型快取 volume（`NFR4.3`）永遠是空的，而它的存在理由就是快取模型。

**本站定案：部署後步驟，由 `deploy.yml` 承載。**

| 候選機制 | 採用？ | 理由 |
|---|---|---|
| **部署後步驟**（`deploy.yml` 在 `up -d` 之後執行一次 `ollama pull bge-m3`） | **採用** | 與本單元既有的交付面一致（`S-6` 已經在改 `deploy.yml`）；每次部署都能跑；不需要自建映像、不需要 entrypoint 覆寫。**兩點本輪更正（審查 R-28）**：(1) 它**不是無條件 no-op**——模型已存在時 `ollama pull` 仍會連 registry 比對 manifest；(2) **失敗不一律紅燈**——判定分兩種情形，以 `cicd-pipeline.md` 的「`ollama pull` 的『冪等』宣稱過寬」專節為準（模型不在 volume 且 pull 失敗 → 紅燈；模型已在 volume 但 registry 不可達 → 記 warning）。初版此格的「冪等——已存在時是 no-op」與「失敗會讓部署紅燈」兩句與該節直接對撞 |
| 覆寫 entrypoint（`serve` ＋ 背景 pull） | 不採用 | 要在容器內寫一段啟動腳本，等於把 shell 塞進 compose；且失敗只會出現在容器日誌裡、不會讓部署紅燈 |
| init 容器 | 不採用 | compose 沒有原生的 init container 概念，要用 `depends_on: condition: service_completed_successfully` 模擬，多一個服務項 |
| 自建映像（把模型烘進去） | 不採用 | 映像會變大約 1.2GB，而 `deploy.yml` 是在主機上 `up -d --build`——每次部署都要重建那一層 |

**與 `healthcheck` 的關係，必須寫清楚**：`/api/tags` **不足以**作為「模型已就緒」的判準
（它在無模型時回空清單而非錯誤）。所以：

- `healthcheck` 的職責限於**「Ollama HTTP 服務在回應」**，不宣稱模型就緒。
- **「模型就緒」由部署後的 pull 步驟自己保證**——它成功結束即代表模型在 volume 裡。
- 因此 **`ollama` 的 `healthcheck` 不需要長 `start_period` 去等下載**（下載不在啟動路徑
  上，而在部署後步驟裡）。這一點推翻了初版在 `monitoring-design.md` `§六` 的說法，該處
  已同步更正。

### 兩個新服務的 `depends_on` 拓樸（審查 R-04 查出初版從未設計）

**實測現況**：`deploy/docker-compose.deploy.yml` 只有三條 `depends_on`——`:63–65`
`backend` → `db`（`condition: service_healthy`）、`:77–78` `frontend` → `backend`、
`:92–93` `cloudflared` → `frontend`。**沒有任何服務 `depends_on` `redis` 或 `ollama`**，
因為它們還不存在。初版卻在 `monitoring-design.md` 引用了一個依賴它的因果。

**本站定案**：

| 邊 | `condition` | 理由 |
|---|---|---|
| `backend` → `redis` | **`service_healthy`** | **理由本輪更正（審查 R-26）**：初版寫「`redis-cli ping` 不涉及長時間初始化、數秒內就緒」，而 deploy stack 依 `NFR4.2` **開啟 AOF**，容器啟動要重播 AOF——資料量大時不是數秒。但**這不會讓 `backend` 卡住**：`PING` 在 Redis 的載入期間即可回應，所以 healthcheck 會先通過、`service_healthy` **不阻塞啟動**。代價是它**也不保證資料集已載入**——那段時間內其他指令會回 `LOADING` 錯誤（已併入 `§六` 第 4 項）。選它的淨理由是：它保證容器已起且行程在回應，比 `service_started` 強，而不引入阻塞風險 |
| `backend` → `ollama` | **`service_started`（不是 `service_healthy`）** | **這一條是刻意的。** 等 `service_healthy` 沒有壞處（healthcheck 不等下載，見上），但也沒有好處——真正決定 embedding 可用性的是模型是否在 volume 裡，而那由部署後步驟保證、時序上**晚於** `up -d`。所以用 `service_started` 表達「只要容器起來」，避免製造一個看起來在等就緒、實際上等不到正確東西的邊 |

**`backend` → `ollama` 為何不完全省略**：省略的話 compose 不保證兩者的啟動順序，而
`EMBEDDING_PROVIDER=ollama` 之下 backend 啟動期就可能打它。`service_started` 是最弱但非零
的保證，成本為零。

### `maxmemory` 住在哪裡（審查 R-05 查出未定案）

`[I1]`=A 的選項原文寫「值寫進 `DEPLOY.md` 由部署者依主機餘裕定」，而 `[I2b]` 的硬寫理由
**明文反對新增任何 compose 消費的環境變數**——兩者指向相反方向，而初版的 `§二` redis 列
只寫「`maxmemory` ＋ `allkeys-lru`」，沒說它是什麼承載。**本輪定案並與 `[I2b]` 對齊**：

| 選項 | 採用？ | 理由 |
|---|---|---|
| compose 的 **`command:` 覆寫**（`redis-server --maxmemory <值> --maxmemory-policy allkeys-lru`） | **採用** | 與記憶體上限同一個承載形狀（硬寫在 compose、改值要走 PR），所以兩個數字的關係在**同一個檔案的同一個服務區塊內**可被一眼核對——這是 R-05 要求「可二元判定」的前提 |
| 掛載 `redis.conf` | **不採用，且 `maxmemory` 一律不得移入該檔** | `nfr-requirements` `§五` 把「ACL 設定資產採 `command:` 覆寫還是掛載檔」留給 `U10`，**本站不綁死那個決定**——但 `maxmemory` 是另一回事：**它一律留在 compose 的 `command:`**，即使 `U10` 後來選了掛載檔。**初版寫「可隨之移入該檔」是自相矛盾（審查 R-18）**：移入掛載檔後它就不在 compose 裡，而同一格的後半句「必須在同一份 compose 裡可對照」隨即被自己違反，`§六` 的閘門 (d)（「兩個數字都在同一個服務區塊內，所以可機械比對」）也一併失效 |
| 環境變數 | **不採用** | 牴觸 `[I2b]`：會讓同步點由九處增加 |

**兩者並存時的優先順序，必須寫下來否則會靜默失效（審查 R-18 的第二個缺口）**：
`redis-server` **只有在設定檔作為第一個位置引數時才讀它**，而 **CLI 旗標會覆寫檔內同名
指令**。所以若 `U10` 選了掛載 `redis.conf` 而 `command:` 仍帶 `--maxmemory`，**檔內的
`maxmemory`（若有）會被靜默忽略**。處置：`U10` 若採掛載檔，該檔**不得包含 `maxmemory` 或
`maxmemory-policy`**，兩者由 `command:` 獨佔——這樣兩條路徑都不會互相覆寫，且關係式的
可機械比對性得以保留。

**所以「由部署者定」在硬寫前提下的實際語意是「改 PR」**——這一點必須明說，否則
`DEPLOY.md` 會寫成「部署者可調」而實際上調不了。

#### AOF 的承載（本輪送審前自檢第 2 項查出：`appendonly` 在本站三份產出中一次都沒出現）

`NFR4.2` 要求 deploy stack 開 AOF，而本站在上方的服務表只寫「**AOF 開啟**」——**有讀者、
無寫者**。這不是措辭問題：官方 `redis` 映像的預設是 **`appendonly no`**，沒有任何機制會自己
把它打開，所以「AOF 開啟」若沒有承載，落地結果是 **AOF 不開而畫面上看不出來**——`redis-cli
ping` 照樣回 `PONG`、healthcheck 照樣過、`NFR4.2` 在執行期靜默失守。

**承載與 `maxmemory` 同一條 `command:`**：`redis-server --appendonly yes --maxmemory <值>
--maxmemory-policy allkeys-lru`。理由與 `maxmemory` 相同——`[I2b]` 不得新增 compose 消費的環境變數。

**⚠ 這是對已核可上游指派範圍的收窄，必須顯性（審查 R-44）**：`nfr-requirements` `§五`（`security-requirements.md:756–757`）
逐字把「**Redis 設定資產採 compose `command:` 覆寫還是掛載設定檔**」交給 `U10` 決定，並要求該資產「存在且承載
`NFR4.1(b)` 與 `NFR4.2` 的設定」——而 `appendonly` 正是 `NFR4.2` 的核心設定。**本站就 `appendonly`、`maxmemory`、
`maxmemory-policy` 這三項收窄該選擇**（歸 `command:` 獨佔），理由是 `redis-server` 的覆寫語意會讓檔內同名值**靜默失效**
（見下一段）。初版把這個收窄寫成「掛載檔的歸屬權在 `U10`，本站不綁死它」的附帶結果，而緊接的表格正是在綁死——
**同節三行之隔自相矛盾**。`U10` 對該資產的形式選擇（`command:` 還是掛載檔）與其餘設定的歸屬**不受本收窄影響**，
ACL 使用者的建立仍在該資產內（見 `cicd-pipeline.md` `§五` 第 17b 項）。**誰確認**：此收窄需 `U10` 的
`functional-design` 在其產出中明示接受或提出反對；本站不代它決定，並已在 `§〇` 列為本階段新增項。

**歸屬切分（沿用上一段的覆寫語意，避免同一個陷阱）**：

| 指令 | 歸屬 | 掛載檔（若 `U10` 選它）可否包含 |
|---|---|---|
| `appendonly` | **`command:` 獨佔** | **不得包含**（否則檔內值被 CLI 靜默覆寫） |
| `maxmemory`／`maxmemory-policy` | **`command:` 獨佔** | **不得包含**（同上，見上一段） |
| `appendfsync` | `U10` 決定值**與位置** | **可以**，但此時 `command:` **不得**帶 `--appendfsync`；兩處都寫則檔內失效 |
| `auto-aof-rewrite-percentage`／`auto-aof-rewrite-min-size` | `U10` 決定值**與位置**，但 **`NFR4.2` 要求不得關閉**（或須另行指定等效的容量上界，`security-requirements.md:155–157`） | **可以**，同 `appendfsync` 的規則。**沒有靜默失敗路徑**：Redis 的預設即為開啟，「不得關閉」在什麼都不寫時自動滿足——所以本列是為了讓這張表完整，不是為了補漏（審查 R-47）。但**關掉它的後果不輕**：AOF 檔的回收靠 rewrite 而非 TTL，關閉會在單機 staging 把磁碟寫爆，而該層**沒有機械閘門** |

**CI test stack 的 AOF 豁免，依據是 `NFR4.2` 的適用範圍條款**（`security-requirements.md:96`）：該列逐字判 test stack
**豁免**，理由是 `deploy/docker-compose.test.yml:22` 的註解逐字為 `No host port and no named volume: isolated and
disposable`——該 stack 刻意無持久化，而 `NFR4.2` 的不變量（重啟 Redis 後可還原）對一個每次重建的 stack 沒有意義。

**本輪更正兩處（審查 R-49）**：(1) 初版引 `[I5]` 作為依據，而逐字核對 `infrastructure-design-questions.md` 的 `I5`
（`:153–172`），題幹與四個選項**全部**只談「CI test stack 是否需要 Ollama／`EMBEDDING_PROVIDER` 取哪個值」，
沒有一個字涉及 AOF 或持久化——引錯題，而引對的那一份（`NFR4.2` 的範圍表）**正是同時記載 ACL 不豁免的地方**，
繞過它正是 R-38 那個缺口能成立的路徑。(2) 「與 `maxmemory` 同一個排除理由」不精確：`maxmemory` 的理由是
**淘汰策略沒有作用對象**，AOF 的理由是**不需持久化**，兩者同結論不同依據。

**⚠ 同一張範圍表的 ACL 列不豁免**：`security-requirements.md:95` 對 test stack 逐字寫「**必須有，但不會是同一份檔**」。
AOF 豁免**不得**被讀成「test stack 的 redis 什麼都不必設」——ACL 是兩份 compose 都必須有的（見 `cicd-pipeline.md`
`§五` 第 17b 項）。

### 容器上限與 `maxmemory` 的關係式（審查 R-05：原本「必須明顯高於」不可判定）

初版寫「容器層上限必須明顯高於 `maxmemory` ＋ Redis 自身開銷」——**沒有比例、沒有計算式、
沒有驗證方式，而 `§六` 第 1 項自己承認沒有閘門會檢查它。一個不可判定的成立條件等於沒有
條件。** 本輪給出可判定的形式：

> **`redis` 容器的記憶體上限 ≥ `maxmemory` × 1.5 ＋ 256MB**

| 項 | 依據 |
|---|---|
| **× 1.5** | Redis 的 `used_memory` 之外還有 allocator 碎片（`mem_fragmentation_ratio` 一般在 1.0–1.5）與複製／輸出緩衝。1.5 是一般實務的保守下界，不是精確值——**它的作用是讓關係式可被檢查，而非精確預測** |
| **＋ 256MB** | AOF 重寫期間的 copy-on-write 與 `aof_rewrite_buffer`。AOF 由 `NFR4.2` 要求開啟，所以這一項必存在 |

**為什麼關係式必須成立**：若容器上限低於這個下界，容器會在 Redis 有機會執行 `allkeys-lru`
淘汰之前就被 OOM kill——**把一個優雅的淘汰換成硬重啟**，而硬重啟在 `restart:
unless-stopped` 之下變成反覆重啟，且它比淘汰難診斷得多（淘汰在 Redis 的 `INFO` 有
`evicted_keys` 計數，OOM kill 只在核心日誌裡）。

**可驗證性**：因為兩個數字都硬寫在同一份 compose 的同一個服務區塊，這條關係式**可以被人
目視核對，也可以被腳本檢查**——已列入 `§六` 補閘門做法的具體項目。

### 兩個新服務的 `restart` 政策（審查 R-13b 查出從未指定）

| 服務 | `restart` | 理由 |
|---|---|---|
| `redis` | **`unless-stopped`** | 與既有四個服務一致。**上方的硬約束論證明文依賴它對 `redis` 生效**（「硬重啟會變成反覆重啟」），而初版從未指定過它——那個論證原本建立在一個沒寫下來的假設上 |
| `ollama` | **`unless-stopped`** | 同上。另有一個本站特有的理由：模型取得機制（見下）若採部署後步驟，容器重啟不得讓已下載的模型消失——這由具名 volume 保證，與 `restart` 政策無關，但兩者要一起想 |

### 記憶體上限的值怎麼來（審查 R-01，Critical——`[I2b]`=A 已被推翻）

**初版的三條並存製造了一個死結**：`[I2]`=C（六個全設）＋ `[I2b]`=A（沒量過就不得設）＋
值硬寫在 compose，使 `code-generation` **不存在任何合規輸出**——它被禁止猜，又必須產出
deploy 六個 ＋ CI test 四個數字，而量測的**執行者、時點、通過判準三者皆無**（初版的
Assumptions 自承「量測本身尚未有執行者與時程」）。「不得靜默填一個猜測值」是**禁令，不是
路徑**。

**使用者在被揭露此死結後裁決：鬆開 `[I2b]`=A，改為「先以公開基準設值、限期複量」。**

#### 兩套推導方式，依承載環境分流（審查 R-01 的第二半）

初版把同一條「沒量過就不得設」套在兩份 compose 上，**那對 CI 側是錯的**：實測起 test
compose 的是 `.github/workflows/ui-regression.lock.yml:384` 的 job，`runs-on:
ubuntu-latest`——**GitHub-hosted runner 的規格是公開文件化的固定值**，不需要量測；而
`docker stats` 在一次性 runner 上也取不到穩態。

| 承載環境 | 上限的來源 | 誰負責 |
|---|---|---|
| **deploy stack**（`192.168.10.10`） | **現在**以下表的公開基準設寬鬆值；`DEPLOY.md` 標記為**暫定、未量測**並記下複量期限 | 部署者在複量期限內以 `docker stats` 取穩態峰值後改 PR 更新 |
| **CI test stack**（`ubuntu-latest`） | **由 runner 的公開規格推導，不適用主機量測程序**。標準 GitHub-hosted runner 的記憶體是固定且文件化的，上限只需保證四個服務的總和不超過它並留餘裕 | 無需量測；規格變更時（GitHub 調整 runner）隨之調整 |

#### deploy stack 的暫定值依據（公開基準，非量測）

| 服務 | 依據 | 風險 |
|---|---|---|
| `db`（PostgreSQL 18） | `shared_buffers` 預設 128MB ＋ `work_mem` × 連線數 ＋ OS 快取需求。**升版窗口另有例外，見下** | 中——正常負載可推，但 dump/restore 期間異常 |
| `backend`（FastAPI／uvicorn） | **推導方式本輪更正（審查 R-20）**：初版引 `LLM_MAX_OUTPUT_TOKENS`=12000／`LLM_XML_CONTEXT_MAX_CHARS`=32000 作為量級來源，而那兩個值**確實逐字正確**（`backend/.env.example`／`render-env.sh`／compose 的 `:-` 預設三處一致）——但它們是 **KB 量級**（32000 字元 = 32KB），對一個 Python／uvicorn 行程的常駐記憶體**不構成任何上界**，而該行程的解譯器 ＋ 相依套件本身就是數百 MB。正確的基準是**行程基線**：以 **`backend/Dockerfile` 在任一機器本機建置**後啟動容器、`docker stats` 讀其 idle 常駐（不需要 `192.168.10.10`、不需要正式流量）。**不得指涉 `ci.yml` 的 `docker-build` 產物**——那個 job 是 `push: false`、無 registry，映像只存在於當次 runner 內並隨之消失，取不到（審查 R-37），再乘併發假設的係數。**併發假設本站給定：單主機 staging、單一 uvicorn worker、同時處理的 LLM 請求數上限為個位數**——這是**本設計的兩項給定假設之一（其一：併發上限）**，可被 `DEPLOY.md` 記載與日後複量 | **最高**——用量最變動 |
| `redis` | 由 `maxmemory` 反推：**≥ `maxmemory` × 1.5 ＋ 256MB**（見上方關係式）。**而 `maxmemory` 自己的暫定依據本輪補上（審查 R-20）**：見下方獨立段落 | 低——有明確可判定的下界，**前提是 `maxmemory` 本身有值** |
| `ollama` | 模型 ＋ runtime 常駐（`bge-m3` 約 1.2GB ＋ 約 2GB，**取自一般認知、未在本主機實測**）× 安全係數 | 中 |
| `frontend`（nginx） | nginx 的常駐極小，可設寬鬆固定值 | 低 |
| `cloudflared` | tunnel client 的常駐極小，同上 | 低 |

#### `maxmemory` 自己的暫定值依據（審查 R-20(b)：這條鏈原本的根是懸空的）

`redis` 的容器上限由 `maxmemory` 反推，而**初版三份產出裡 `maxmemory` 沒有任何值、也沒有
任何推導依據**——`[I1]`=A 的「由部署者定」已被本輪重新解釋為「改 PR」，所以它不是一個會自己
出現的數字。**R-01 鬆開的是六個容器上限，沒有鬆開 `maxmemory`。**

**暫定依據（與六個上限同一形狀：公開基準 ＋ 限期複量）**：

| 輸入 | 來源 | 為何可推 |
|---|---|---|
| 單一 session 的 key 大小上界 | `BrainSession` 的欄位集合（`components.md` 的 Entity Ownership 表：`sessionKey`／`userId`／三個 current id／`sharingMode`／**`messageHistory`**／`expiresAt`） | 除 `messageHistory` 外全部是識別碼與短字串，**量級由 `messageHistory` 決定** |
| 同時活躍的 session 數上界 | **本設計的兩項給定假設之二（其二：活躍 session 數）**：單主機 staging、使用者數為個位數到低兩位數 | 與 `backend` 的併發假設**同源但不同項**（一個約束併發請求數、一個約束活躍 session 數），兩項一併記入 `DEPLOY.md`；另見 Assumptions 的未量測項清單 |
| 保留窗口 | **TTL 24 小時、每次互動續期**（domain-design ADR-005，`decisions.md:209–211`） | 上界是「24 小時內活躍過的 session 數」而非全部歷史 |

**所以 `maxmemory` 的暫定值 = 單一 session 上界 × 24 小時內活躍 session 數上界 × 安全
係數**，三個輸入都有來源。**`messageHistory` 的上界是唯一需要 `U10` 確認的一項**（它有沒有
截斷策略？若無，單一 session 可無限成長，那 `maxmemory` 的推導就不成立而必須改為「以
`maxmemory` 反過來約束 `messageHistory`」）——已列入 Assumptions。

**`DEPLOY.md` 必須記的三件事**（取代初版的「沒量過不得設」）：
(1) 這組值是**暫定、依公開基準而非量測**；(2) **複量期限**；(3) 複量完成後的數字與日期。

#### `db` 的上限在升版窗口內必須另行處置（審查 R-07）

初版正確地指出**磁碟**不足的最糟時點是 `NFR6.3` 的升版窗口，卻**沒有對記憶體做同一個
推導**。`db` 的容器記憶體上限在升版窗口內同樣生效，而 **dump/restore 是該容器生命週期中
記憶體用量最異常的一段**（大批 `COPY`、索引重建、`maintenance_work_mem`）。以「正常使用下
的穩態峰值」得到的值，正是**最可能在還原中途被突破**的那一個——而突破的後果是 OOM kill
＋ `restart: unless-stopped` 的重啟迴圈，發生在 `NFR6.3(b)` 的回退**依賴 dump 完整性**的
那個窗口裡。

**處置（寫進 `DEPLOY.md` 的升版程序，與磁碟空間前置條件並列）**：升版期間**暫時提高到一個
明確的值**（不是移除），還原與驗證通過後恢復原值，並在升版紀錄寫下「已恢復」。

**為何是「提高到明確值」而不是「移除」（審查 R-27——初版只寫了權衡的一面）**：移除上限之後，
升版期的 `db` 若吃光主機記憶體，受害者是**同一台主機上的其他五個容器**，而 D-1 的全碟加密
使主機重開需要解鎖——**這正是 `I2b` 題幹自己用來論證「不能猜低」的那條失敗鏈，方向相反而
後果同級**。所以升版期的值應該是「明顯高於還原峰值、但仍低於主機總量減去其餘服務所需」。

**為何不採「把上限設到足以涵蓋還原峰值」作為常設值**：那會讓正常運行期間的上限失去保護
意義——上限的目的就是擋住失控的那一個容器。

### 上限的值為何硬寫在 compose 而不走環境變數（本站定案，非選項）

**定案：硬寫在兩份 compose。**

- **不走環境變數的理由**：那會讓同步點由**九處變十五處**（`render-env.sh` ＋
  `deploy/.env.example` ＋ 兩份 compose 的引用），而「新增 compose 消費的變數」在本 repo
  是有 blocking 規則與**無聲失敗前例**的高風險動作——`N8N_USER`／`N8N_PASSWORD` 從未被
  寫入，導致每次部署的架構圖 icons 靜默退回灰底佔位圖。為容量數字承擔那個風險不值得。
- **硬寫的代價，也是它的優點**：改上限要走 PR ＋ 部署。對**容量決策**而言這是對的——它
  變成可審查、有版本、有 reviewer 的變更，而不是一個沒人知道誰改過的環境變數。
- **與 `maxmemory` 的一致性**：`maxmemory` 也採 compose 的 `command:` 覆寫（見上），所以
  兩個數字在**同一個服務區塊內**可對照，關係式因此可被檢查。
- **`code-generation` 不再被阻塞**（這是本輪改動的要點）：它依上表的公開基準產出可部署的
  值，並在 compose 註解與 `DEPLOY.md` 標記為暫定。**它不需要等量測。**

---

## 三、`logging:` 的適用範圍（`[I4]`=A）

**現況**：三份 compose 都沒有 `logging:` 區塊，所以**全部服務**走 Docker 預設的
`json-file` 且**無大小上限**。`NFR8.9` 只要求兩個新容器必須指定 `max-size`／`max-file`。

**本站定案：加在 deploy 與 CI test 兩份 compose 的全部服務上。**

**為何超出上游字面**：照字面只加新容器會讓 `backend`（本 repo 最多日誌的服務）維持無界，
而磁碟寫滿對一台**全碟加密**的主機是實際風險——`S-10` 已把磁碟空間列為前置條件，而無界
日誌會讓那個前置條件在運行中被慢慢吃掉。且設日誌上限**不需要任何用量資料**，沒有 §二 那個
猜數字的問題，所以成本與風險都遠低於資源上限。

**具體值**：依 `NFR8.9`，由部署者定並記入 `DEPLOY.md`。本檔不指定個別值，**但必須給總量的
上界**（審查 R-06(d)）：

> **`max-size` × `max-file` × 服務數 的總量不得超過 2GB。**

**為什麼這個上界不是可有可無的**：`§四` 的磁碟公式把「日誌預算」列為一項輸入，而若這兩個
值完全自由，該項就是一個**無界的自由變數**——`100m × 5 × 6` 就是 3GB，單這一項吃掉整個
餘裕，於是 `§四` 的公式失去定義。合規的組合例如 `max-size: 50m`、`max-file: 5`、六個服務
= 1.5GB。

**兩份 compose 的服務數不同**（deploy 六個、CI test 四個），所以同一組 `max-size`／
`max-file` 在兩份的總量不同；上界只約束 deploy stack，CI test 的日誌隨 stack 消失。

**CI test stack 為何也加**：它每次重建、日誌隨 stack 消失，所以*效果*上不需要。加它的理由
只有一個——**避免兩份 compose 的形狀漂移**。本 session 已因「兩份 compose 不一致」抓到兩項
發現（`NFR8.1a`／`NFR8.1b`），每一項差異都讓下一個改它們的人必須判斷「這是故意的嗎」。

---

## 四、磁碟空間前置條件（`S-10`，本站覆蓋檢查的產物）

**沒有任何一處檢查過主機的磁碟空間，而本單元同時增加了三個消費者。**

| 消費者 | 量級 | 何時佔用 |
|---|---|---|
| Ollama 模型快取 volume | `bge-m3` 約 **1.2GB**（未在本主機實測） | **由 `deploy.yml` 的部署後 `ollama pull` 步驟取得後常駐**——**不在容器啟動路徑上**。初版此格寫「首次啟動下載後常駐」，而 `§二` 同一份檔已指名該句為錯（官方映像不會自動拉模型）；**本輪補正（審查 R-17：`§二` 指名三處、初版只改了兩處）** |
| Redis AOF volume | 隨 session 量成長，受 `maxmemory`（`[I1]`=A）間接約束 | 常駐 |
| **升版窗口內的 PG 資料：三份全庫明文副本** | 現有資料庫大小 × **3**（新 volume ＋ 保留中的舊 volume ＋ dump 檔） | **只在 `NFR6.3` 的升版窗口內** |
| 各服務的 `json-file` 日誌 | 受 `§三` 的 `max-size` × `max-file` 約束（本輪起有界） | 常駐 |

### 要求：**逐掛載點**的門檻（審查 R-06 指出初版的單一公式算不出來）

**初版的錯在把一個公式套在「承載 Docker volume 的檔案系統」上，而三份副本之一的 dump
依 `nfr-design` D-4 第 2 條必須放 `$HOME`**——於是那個數字對 volume 那個檔案系統**高估**
（多算一份 dump），對 `$HOME` 那個檔案系統**完全沒有要求**。而初版的要求 2 只說「檢查對象
是那同一組四個掛載點」卻沒給任一掛載點的個別門檻，部署者無法執行。

**先定義兩個量，否則門檻寫不出來**：

| 量 | 定義與量測方式 | 為何必須定義 |
|---|---|---|
| **`DBSIZE`** | **PGDATA 目錄的實際大小**：`sudo du -sb /var/lib/docker/volumes/cloud360_db/_data`。**不是** `pg_database_size()`。**兩個前提本輪補上（審查 R-24）**：(1) **需 root**——`/var/lib/docker` 預設 `0710 root:root`；(2) **升版前要量的是舊 volume**，其現名為 `cloud360_db`（`deploy/docker-compose.deploy.yml:20`／`:96`），而本輪會把它改名，所以量測必須在改名前或針對舊名進行 | 兩者可差數倍——後者不含索引膨脹、不含 WAL、不含其他 database。空間規劃要用前者 |
| **`DUMPSIZE`** | 假設 `pg_dump` 的**預設 plain 格式、未壓縮**（`nfr-design` D-4 的範例檔名逐字是 `cloud360-dump-20260927.sql`，即 plain）。以 `DBSIZE` 為上界估算（plain dump 通常小於 PGDATA，因為不含索引，但**本站不假設它小**——無壓縮的文字輸出對寬表可能更大） | dump 的格式決定量級，而初版完全沒提 |

**逐掛載點門檻（寫進 `DEPLOY.md`，與全碟加密前置條件並列）**：

| 掛載點 | 升版前所需可用空間 | 涵蓋什麼 |
|---|---|---|
| **承載 Docker volume 的檔案系統**（通常 `/var/lib/docker`） | **≥ `DBSIZE` × 2 ＋ `max(DBSIZE × 0.5, max_wal_size 的生效值)`（還原期 WAL）＋ 1.5GB（模型 volume，含餘裕）＋ 2GB（日誌預算上界，見 `§三`）** | 新 volume ＋ 保留中的舊 volume（**兩份，不是三份**）。**「還原期 WAL 餘裕」取兩者中的大者（審查 R-24 給值、R-36 更正形式）**：`pg_restore`／`psql` 匯入期間 WAL 的產生量與匯入資料量同級，但 checkpoint 會回收，故比例式餘裕取 `DBSIZE × 0.5`。**但 `max_wal_size` 的預設值就是 1GB**，所以在 `DBSIZE` 小於 2GB 時比例式會低於 WAL 實際可累積的量——**故取大者，小型資料庫的下界即 1GB 而非比例值**。初版寫「調高才加計」有兩個錯：觸發條件在預設情況下永不成立，且「加計」會與比例式重複計算 |
| **`$HOME` 所在檔案系統** | **≥ `DUMPSIZE`** | dump **一份**（D-4 要求它放這裡） |
| **自架 runner 的工作目錄所在檔案系統** | 既有需求 ＋ 無新增 | `deploy/.env` 極小；`up -d --build` 的建置快取是既有消費 |
| **`/`（若上列任一未獨立掛載）** | 取該掛載點所涵蓋各項之和 | — |

### 日誌預算必須是這個公式的**顯式輸入**，不能藏在「＋2GB」裡（審查 R-06(d)）

初版寫「＋2GB 涵蓋 Ollama 模型與其他新增項」，而 `§四` 的表把 `json-file` 日誌列為第四個
消費者——**它的總量是 `max-size × max-file × 服務數`，而 `§三` 把那兩個值完全交給部署者
且未設上限**。`100m × 5 × 6` 就是 **3GB**，單這一項就吃掉整個餘裕。**一個公式的項由另一節
的自由變數決定，等於公式沒有定義。**

**處置**：`§三` 新增一條上界——**`max-size × max-file × 服務數` 的總量不得超過 2GB**
（例如 `max-size: 50m`、`max-file: 5`、六個服務 = 1.5GB）。這個上界是上表「日誌預算」那一項
的值，使磁碟公式的每一項都有來源。

**空間不足時不得開始升版。** 理由：`NFR6.3` 的七步程序在中途耗盡空間，會同時失去「新
volume 建好」與「dump 檔完整」兩者，而 `NFR6.3(b)` 的回退路徑**就是那份 dump**。

**這一條沒有機械閘門**——它是部署環境的前置條件，CI 在 GitHub runner 上跑，對
`192.168.10.10` 的磁碟一無所知。已列入 §六。

---

## 五、ADR-0006 Security Baseline 四面向逐項判定（＋ PBT）

`project.md ## Mandated` 要求對每一項變更逐項檢查四個面向，並以**逐項判定表**呈現，
判定為不適用者亦須附理由、不留空白。**這張表是自檢第七項查出後補的——本 record 同型缺口
已第三次**（`domain-design` R-03、`units-generation` R-04，以及我在 `nfr-design` 的閘門上
把它寫進 `project.md` 之後又在本站漏掉）。

| 面向 | 本站的處置 | 判定 |
|---|---|---|
| **IAM** | 本站**不新增任何身分或權限**。三個新增設定（資源上限、`logging:`、`healthcheck`）都不涉及身分。既有缺口原樣承接並如實記載：PostgreSQL 單一 superuser（`§二` 的 db 列）、Ollama 零認證（`§二` 的 ollama 列）。**新增一項界限說明**：`redis-cli ping` healthcheck **不證明 ACL 使用者可用**——`ping` 在 `default` 下也會過，而 `NFR4.1` 要求連線必須用非 `default` 的使用者（`monitoring-design.md` `§六`） | **無新增，既有缺口已記載** |
| **Encryption** | at rest → `nfr-design` D-1 的主機層全碟加密，本站**不改變手段，但把它的檢查對象與 `§四` 的磁碟空間檢查綁成同一組四個掛載點**（理由：dump 在 `$HOME`、volume 在 `/var/lib/docker`，可能在不同檔案系統上）。in transit → D-2 的容器間明文，本站不改變。**本站新增的三項設定都不涉及機敏資料**（上限值、日誌大小、healthcheck 指令皆非機密） | **已處置** |
| **Network exposure** | 本站**不新增任何對外暴露面**。`networks:` 分段沿用 D-3；兩個新 `healthcheck` 在**容器內**執行、不需 host port（`§二`）；探測打的是**既有的** `frontend` host port，不新增端口。唯一有 host port 的服務仍是 `frontend` | **無新增** |
| **Audit logging** | **本站在此面向有實質新增。** 新增：`logging:` 的 `max-size`／`max-file` 加到兩份 compose 的**全部服務**（`§三`／`S-9`），使日誌從無界變為有界。**淨效果是中性偏正面，方向必須寫對**（審查 R-11）：今日的無界 `json-file` 並非「保留無限」，而是「保留到**磁碟寫滿**、然後全站與全部日誌一起失去」——由無界改為有界**移除了一條會摧毀全部證據的路徑**，代價只落在長回溯調查。**度量單位也要寫對**：`max-size` × `max-file` 的乘積是**容量**上限，不是保留**期**；保留期 = 容量 ÷ 寫入速率，而**速率未知且逐服務不同**（`backend` 遠高於 `cloudflared`）。`§三` 另給了總量 2GB 的上界。**界限**：本站不新增任何 metrics、告警或 SLI／SLO（`[I3]`=D），承接站為 Operations 的 `observability-setup`，**若該站被 skip 則本 intent 完全沒有 metrics 與告警** | **部分處置** |

**四面向皆適用，無不適用項。**

### Property-based testing hard constraint（ADR-0006 的另一項）

ADR-0006 逐字點名 **IaC generator**、**cost calculator**、**agent routing** 三個模組須有
property-based 測試。**對 `brain-infra` 判定為 N/A**：本單元交付的是三份 compose 宣告、
`render-env.sh` 的變數寫入、`deploy.yml` 的兩個步驟、以及兩份文件的同步——**沒有一行純函式
可被 property 約束**。

**N/A 不等於本 intent 豁免**：`contract-summary.md` 的 PBT 段已把落點釘在 `K-10`
（`IntentRouter` 的**門檻比較純函式**，對應 ADR-0006 的 agent routing）與 `K-06`
（`EmbeddingPort` 的 `verification` 含 property-based）。兩者皆屬 `U11`／`U6`，不在本單元。

**而本站的 `[I5]`=A 讓這一項變得更重要**：CI 走 `stub`，所以 **e2e 層完全不碰任何
embedding 路徑**，`EmbeddingPort` 的四個實作與切換邏輯**只由 `U6` 的單元測試覆蓋**。
若 `U6` 的 property-based 測試被削弱，**沒有第二道防線**（見 `cicd-pipeline.md` `§三`）。

---

## 六、本設計中沒有機械閘門的項目

承接 `nfr-design` `§四` 的清單。**本站新增四項（下列 1–4），另延續該站的五項（下列第 5
列一併點名）——合計九項，全部只能靠 code review 或運維紀律，沒有任何 CI 檢查會發現違反**：

1. **資源上限的存在與其值是否來自量測**（`S-8`／`[I2b]`）——`validate_env_contract.py`
   只解析環境變數，不解析 compose 的 `deploy.resources`。而因為值硬寫在 compose，
   「這個數字是量測來的還是猜的」在檔案上看不出來；`DEPLOY.md` 的量測紀錄是唯一線索。
2. **`logging:` 是否加在全部服務上**（`S-9`）——同一支 validator 也不解析 `logging:`。
   新增服務時忘記加，它就是無界的，而無人會被通知。
3. **磁碟空間前置條件**（`S-10`）——純部署環境條件，CI 看不到該主機。
4. **`healthcheck` 是否真的反映服務可用**（`[I3]`=D）——三項具名的盲點：
   (a) `redis-cli ping` **不證明 ACL 使用者可用**（`ping` 在 `default` 下也會過）；
   (b) `/api/tags` **不證明模型存在**（無模型時回空清單而非錯誤，見 `§二` 的模型取得專節）；
   (c) **`ping` 在 Redis 的 AOF 載入期間即可回應**，所以 `service_healthy` 通過之後、
   資料集載入完成之前，其他指令會回 **`LOADING`** 錯誤（審查 R-26 補入）。三者都是刻意
   接受的：更深的檢查需要憑證（Redis）、觸發一次真實推論（Ollama），或輪詢 `INFO
   persistence` 的 `loading` 欄（那會讓 healthcheck 自己變成一個要維護的判斷式）。
5. 延續自 `nfr-design` 的五項（`networks:` 分段本身、服務的網段歸屬正確性、全碟加密的
   存在、dump 檔的三條要求、`DEPLOY.md` 是否真的寫了解鎖方式）。

**補閘門的具體做法（不列為本單元交付）**：`nfr-design` `§四` 已提議把
`validate_env_contract.py` 擴充為解析 deploy 與 CI test 兩份 compose 的
`networks:`／`ports:`／`volumes:`。本站再加三項可一併納入同一次擴充：
(a) 每個服務都有 `deploy.resources.limits.memory`、(b) 每個服務都有 `logging.options`
的 `max-size` 與 `max-file`（**兩份 compose 皆檢查存在性**）**且其總量不超過 2GB**（`§三` 的上界，**該總量上界只適用 deploy stack**——`§三` 逐字「上界只約束 deploy stack，CI test 的日誌隨 stack 消失」；比照下方 (d) 的寫法，審查 R-48 補入）、(c) **兩份 compose 的
服務集合差集僅得為 `{cloudflared, ollama}`**、(d) `redis` 的容器上限 ≥ `maxmemory` × 1.5
＋ 256MB（`§二` 的關係式——兩個數字都在同一個服務區塊內，所以可機械比對）。**(d) 只適用
deploy stack**——CI test stack 不設 `maxmemory`（見 `§二` 的 redis 列），該處只檢查容器上限
本身存在。

**(c) 的措辭本輪更正（審查 R-03，Critical）**：初版寫「差異只有 `cloudflared`」，而那與本站
自己的 `[I5]`=A **直接矛盾**。實測：`deploy/docker-compose.test.yml` 今日服務為
`db`（`:14`）／`backend`（`:29`）／`frontend`（`:44`）三個，本輪加 `redis` 後為**四個**；
`deploy/docker-compose.deploy.yml` 為 `db`（`:12`）／`backend`（`:30`）／
`frontend`（`:67`）／`cloudflared`（`:80`）四個，本輪加 `redis` ＋ `ollama` 後為**六個**。
差集是 **{`cloudflared`, `ollama`} 兩個**。`ollama` 的排除依據是 `[I5]`=A（CI 走 `stub`、
不起 Ollama）。**照初版那條實作，閘門會在落地第一天紅燈。**

---

## Assumptions & Open Questions

- **`db` 與 `backend` 的記憶體用量未量測**，而 `[I2]`=C 要求為它們設上限。**`[I2b]` 已反轉**
  （問題檔 `I2b` 有逐字紀錄），所以本檔的處置不再是「量測是前置條件」而是「以公開基準設
  暫定值 ＋ 限期複量」——`code-generation` 不被阻塞。**真實的剩餘不確定性有兩項**：
  (1) 暫定值未經量測，其準確度未知；(2) **複量期限本身沒有擁有者**——`DEPLOY.md` 由
  `code-generation` 寫，若那時沒有人指定一個日期，「限期複量」會退化成「永遠暫定」
  [assumption]
- **`maxmemory` 推導鏈的根有一項需 `U10` 確認**：`BrainSession.messageHistory` 有沒有截斷
  策略。若沒有，單一 session 可無限成長，`§二` 的 `maxmemory` 推導不成立，必須反過來以
  `maxmemory` 約束 `messageHistory` [assumption]
- **Ollama 的 1.2GB／2GB 與主機餘裕皆未在 `192.168.10.10` 實測**（承接自
  `nfr-requirements` 的同一項）。`NFR9.1` 的退路依賴該實測 [assumption]
- **現有資料庫的實際大小未知**，而 `S-10` 的空間要求是它的三倍。升版前必須先量它
  [assumption]
- **`NFR6.1` 落點 3 的上游逐字衝突仍未解**：`requirements.md` NFR6 與 `contract-summary.md`
  `K-05` 兩處把 CI job 的 service container 釘成 `postgres:16-alpine`，而 `K-05` 的
  `vector(1024)` 欄位在該映像上必然失敗。該 job 是 **`U5 memory-data` 的交付**，本站不回改
  已核可的上游 [assumption]
- **`pg16` 的陳舊引用逐處清單（本站查出，審查 R-10 補完）**。這一項的目的是「供後續統一
  更正時不漏」，所以必須逐處給行號而不是只說「三份檔」——**初版自己就漏了一處**：

  **複驗方式必須用兩個 pattern**：`grep -rn 'pg16\|postgres:16' inception/`。**初版只寫
  `grep -n pg16`，而清單裡的 `requirements.md` 那一列不含 `pg16` 字串**（它寫的是
  `postgres:16-alpine`），所以照初版的指令複驗反而對不上（審查 R-22）。

  | 檔案 | 逐處行號 | 內容 |
  |---|---|---|
  | `domain-design/components.md` | `:215`、`:371`、`:444` | 前兩處「需 `pgvector/pgvector:pg16` image」；`:444` 是 `N-11` 列 |
  | **`domain-design/decisions.md`** | **`:269`、`:292`** | `:269`「DB image 為 `postgres:16-alpine`（不含 pgvector）」；`:292`「換為 `pgvector/pgvector:pg16`（Debian 基底）」——**初版漏列**（審查 R-22） |
  | **`units-generation/unit-of-work-dependency.md`** | **`:136`** | `U5` → `U1` 的依賴說明含該映像——**初版漏列** |
  | **`delivery-planning/external-dependency-map.md`** | **`:76`** | `E4` 列逐字「資料庫 image 由 `postgres:16-alpine` 換為 `pgvector/pgvector:pg16`」——**初版漏列** |
  | `contract-design/contract-summary.md` | `:142`（`K-01` 的 `images_and_services`）、`:425`（`K-05` 的 `verification.carrier`） | 初版只寫欄位名、未給行號 |
  | `requirements-analysis/requirements.md` | `:377`、`:472` | `:377` CI service container；`:472` 的 `C-T5` 逐字「現用 `postgres:16-alpine` 不含 pgvector」 |

  **另有五處在問題檔與審查紀錄內**（`domain-design-questions.md:205`、
  `units-generation-questions.md:74`、`delivery-planning-questions.md:81`、
  `domain-design/reviews/review-01.md:13`、**`requirements-analysis-questions.md:211`**
  ——最後一處為審查 R-35 補入）——那些是**歷史紀錄**，記載當時的決定，**不應更正**。
  本表只列需要更正的實質釘選。**`grep -rn 'pg16\|postgres:16' inception/` 的總命中為
  16 行 = 11 處實質釘選 ＋ 5 處歷史紀錄**，兩類相加即為全部，可機械複驗。

  本站不回改任何已核可產出 [assumption]
- **`[I3]`=D 指名的承接站是 Operations 的 `observability-setup`**，而 metrics／alerts／
  SLI-SLO 全部落在那裡。該站在本工作流程中的執行條件須屆時確認；**若被 skip，本 intent
  將完全沒有 metrics 與告警** [assumption]
