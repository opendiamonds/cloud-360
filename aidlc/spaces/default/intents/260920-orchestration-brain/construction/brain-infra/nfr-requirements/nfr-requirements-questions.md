# NFR Requirements 問題 — `brain-infra`（U1，`kind: packaging`）

<!-- Stage: nfr-requirements（Construction 3.2）· Unit: brain-infra · Record: 260920-orchestration-brain -->

## 這一輪只問五題，以及為什麼

本單元是 `kind: packaging`——它交付的是 compose 服務定義、環境變數與部署資產，
不是程式碼。依 stage 檔的 `produces_kinds`，`performance-requirements`／
`scalability-requirements`／`reliability-requirements`／`observability-requirements`
四項**對 `packaging` 不適用**（它們限 `service`／`ui`），故本單元只產出
`security-requirements.md`、`tech-stack-decisions.md` 與 `traceability.json`。

Construction 階段的提問應是**例外而非常規**（stage-protocol §3）。下列事項已由上游
定案，本輪**不重問**，每一項都能指出定案處：

| 已定案事項 | 定案處（可引用） |
|---|---|
| Redis 為第 5 個服務、Ollama 為第 6 個，兩者**皆不得 publish port**、僅限 compose 內部網路 | `contract-summary.md` K-01 `images_and_services`（`exposure: "compose 內部網路only；不得 publish port"`）＋ `requirements.md` ADR-0006 Network exposure 列 |
| 六個環境變數的名稱、型別、必填性、預設值與驗證規則（`REDIS_URL`、`REDIS_PASSWORD`、`EMBEDDING_PROVIDER`、`OLLAMA_BASE_URL`、`OLLAMA_EMBED_MODEL`、`FASTEMBED_MODEL`） | `contract-summary.md` K-01 `variables`（逐欄已列） |
| 三處同步義務：`deploy/render-env.sh`、`deploy/.env.example`、`LOCAL-DEV.md`，缺一即違反 | K-01 `sync_obligations` ＋ `requirements.md` NFR8 ＋ `C-O1`（blocking） |
| 憑證值不得含 `$`，改用 `openssl rand -hex 32` | `project.md ## Mandated` ＋ K-01 `REDIS_PASSWORD.validation` |
| ~~db image 由 `postgres:16-alpine` 改為 `pgvector/pgvector:pg16`，兩份 compose 都要改~~ **已由 `[N8]`=B 推翻**：改為 PostgreSQL 18 ＋ pgvector，落點由兩處擴為五處（見產出的 `NFR6.1`）。本列保留供追溯 | K-01 `images_and_services[0].scope`（已被本站推翻） |
| 驗證載體為 `python3 scripts/validate_env_contract.py` | K-01 `verification` |
| 無外部法規框架適用（只部署至自有 staging） | `requirements.md` `C-R1` |
| 本平台自身 LLM 花費上限由 OpenRouter 後台承載，本 intent 不建計量機制 | `requirements.md` NFR9（承 `[F13]`） |
| `EmbeddingPort` 有四個實作，`ollama` 與 `fastembed` **同為 1024 維** | `domain-design` ADR-008 ＋ `external-dependency-map.md` E2 |

下列五題是上游**確實沒有答案**、而本單元不能不決定的事。每一題的事實欄都是本輪
實讀 repo 得到的，不是推論。

---

## N1 — `pgvector` 換版對既有 staging data volume 的處置

**本輪查到的事實**：

- `deploy/docker-compose.deploy.yml:13` 是 `postgres:16-alpine`，且第 19–20 行掛
  **具名 volume `cloud360_db:/var/lib/postgresql/data`**——staging 上有既存資料。
- `deploy/docker-compose.test.yml:15` 同樣是 `postgres:16-alpine`，但**沒有具名
  volume**（檔內註解逐字：`No host port and no named volume: isolated and disposable`）
  ——那一側換版無風險。
- 現用 image 是 **Alpine 基底（musl）**，`pgvector/pgvector:pg16` 是 **Debian 基底
  （glibc）**。同一 PostgreSQL 主版本的 PGDATA 格式相容，但 libc／collation
  provider 不同，**text 欄位的索引排序有可能受影響**。
- `schema_rbac.sql` 掛在 `/docker-entrypoint-initdb.d/`，**只在空 data volume 執行**
  （檔內註解與 `C-T6` 皆如此記載）。

這一題問的是：既有 staging 的資料庫容器換 image 時，要不要做索引重建。

- A. 先備份 → 換 image → 對 text 欄位 `REINDEX` → 以查詢驗證，並把這串步驟寫進 `DEPLOY.md`
- B. 直接換 image，只做備份與 `pg_isready` 驗證，不做 `REINDEX`
- C. 不換 image，改用 `EmbeddingPort` 的 `fulltext` 實作，把 `pgvector` 推遲到後續 intent
- D. 換 image 並同時重建 volume（接受既有 staging 資料被清空、`schema_rbac.sql` 重跑）
- X. Other (please specify)

[Answer]: A  <!-- answered 2026-09-26T12:15:24Z via picker -->

> **A 的兩個成分已被取代**（`[N8]`=B ＋ `NFR6.3(a)`／`(c)`）：「就地換 image」改為還原到乾淨叢集、「對 text 欄位 `REINDEX`」在 dump/restore 路徑上不需要。**備份與以查詢比對筆數的部分仍然有效**，已成為升版程序的步驟 2／3／6。原答案保留供追溯。

---

## N2 — `CREATE EXTENSION vector` 由什麼承載

**本輪查到的事實**：

- 全樹 `CREATE EXTENSION` 命中數為 **0**（`schema_rbac.sql`、`schema.sql`、`backend/`
  三處皆搜過）。
- 換 image **只讓 pgvector 可用**，不會自動把擴充建進資料庫；`CREATE EXTENSION vector`
  必須有人執行。
- `schema_rbac.sql` 在既有 staging 的非空 volume 上**不會重跑**（見 N1 的事實）。
- `backend/database.py` 已有 **6 支啟動補丁**的既成形狀（`:78–83` 依序呼叫
  `_ensure_a4_schema`、`_ensure_j5_schema`、`_ensure_a3_schema`、`_ensure_cost_schema`、
  `_ensure_estimate_intake_schema`、`_ensure_last_activity_schema`），每次開機都跑，
  這是唯一在非空 volume 上有效的既有機制。

這一題問的是：由誰負責讓擴充真的存在。**它同時是 `brain-infra`（U1）與
`memory-data`（U5）的邊界**——不釘死，兩邊都會以為是對方的事。

- A. 新增 `_ensure_vector_extension()` 啟動補丁，沿用既有 6 支的形狀，由 `brain-infra` 交付
- B. 寫進 `schema_rbac.sql`（只對新環境有效；既有 staging 需手動執行一次並記入 `DEPLOY.md`）
- C. 由 `U5 memory-data` 的遷移程序承載，`brain-infra` 只負責換 image
- D. 在 compose 的 db service 加 init 指令
- X. Other (please specify)

[Answer]: A  <!-- answered 2026-09-26T12:15:24Z via picker -->

---

## N3 — Ollama 主機餘裕實測不足時的處置

**本輪查到的事實**：

- `bge-m3` 模型約 1.2GB、Ollama runtime RAM 需求約 2GB——`domain-design` 的
  Assumptions **逐字記明這兩個數字取自一般認知、未在 `192.168.10.10` 實測**，
  且 `DEPLOY.md`／`LOCAL-DEV.md` **未記載該主機的 RAM／CPU 餘裕**。
- `external-dependency-map.md` 的 E2 把這件事列為 **B1 的第一件事**。
- 退路存在且同維度：`fastembed`（`multilingual-e5-large`，ONNX、**行程內**、不拉
  torch、不加服務）與 `ollama` 同為 1024 維。
- 但退到 `fastembed` 的代價是 embedding 在 FastAPI 行程內算，**吃的是同一台主機的
  CPU 與記憶體，不是省下來**——只在「多一個容器裝不下、但行程內多一點記憶體放得下」
  時才成立。

- A. 實測不足時自動退到 `fastembed`，並把這個判定寫成 B1 的完成判準（`EMBEDDING_PROVIDER` 改值即可，無需改碼）
- B. 實測不足時停下 B1 並回報，由人決定退路或加主機資源
- C. 一律用 `fastembed`，本 intent 不部署 Ollama（第 6 個服務不新增）
- X. Other (please specify)

[Answer]: A  <!-- answered 2026-09-26T12:15:24Z via picker -->

---

## N4 — Ollama 的認證面（僅當 N3 的答案會讓 Ollama 真的部署）

**本輪查到的事實**：

- K-01 為 Redis 定了 `REDIS_PASSWORD`（`required: true`、不得含 `$`），但
  **Ollama 沒有任何憑證變數**——`OLLAMA_BASE_URL` 與 `OLLAMA_EMBED_MODEL` 都不是憑證。
- Ollama 的 HTTP API **原生沒有認證機制**。
- `requirements.md` 的 ADR-0006 IAM 列只寫了「Redis 連線憑證須最小權限」，
  **未提 Ollama**。Network exposure 列也只點名 Redis 容器。

這一題問的是：Ollama 的存取控制要不要有第二層，還是「無認證 ＋ 網路隔離」就是全部。

- A. 接受「無認證 ＋ compose 內部網路隔離」為唯一控制，並在 `security-requirements.md` 明寫這是刻意決定、其前提是「不得 publish port」，以及該前提一旦被破壞的後果
- B. 在 Ollama 前擺一層反向代理加 basic auth（新增一個容器與一組憑證）
- C. 綁 compose 內部網路 ＋ 另建一個只含 db／backend／ollama 的獨立 network，縮小同網段可達範圍
- X. Other (please specify)

[Answer]: A  <!-- answered 2026-09-26T12:15:24Z via picker -->

---

## N5 — Redis 自身重啟時 session 的處置

**本輪查到的事實**：

- `requirements.md` NFR4 的可測不變量**逐字**是：「重啟 **backend** 後，既有對話的
  脈絡與作業對象仍可完整還原。」
- 那句話**沒有涵蓋 Redis 容器自己重啟**。若 Redis 無持久化，Redis 重啟會清掉全部
  session，而 **NFR4 的字面條件仍然通過**——這是一個上游沒有指名的缺口。
- `deploy/docker-compose.deploy.yml` 現有唯一具名 volume 是 `cloud360_db`；
  K-01 的 `images_and_services` 只為 **Ollama** 指定了模型快取 volume，**沒有為
  Redis 指定任何 volume**。

- A. Redis 開 AOF ＋ 具名 volume，並把不變量擴充為「重啟 Redis 後亦可還原」
- B. 不持久化（session 視為可丟棄），並在 `security-requirements.md` 與本單元的交付中**明寫**「Redis 重啟 ＝ 全體使用者的對話脈絡與作業對象歸零」是已接受的行為
- C. 只開 RDB 快照（較弱：崩潰時可能丟失最近幾分鐘的 session）
- X. Other (please specify)

[Answer]: A  <!-- answered 2026-09-26T12:37:07Z via picker -->

---

## 本站新查出、需下游注意的事項

- **N2 是 U1／U5 的邊界缺口**：`contract-summary.md` K-01 的 `images_and_services`
  只寫了「db image 改為 `pgvector/pgvector:pg16`，reason: `vector(1024)` 欄位需要
  pgvector 擴充」，**沒有指名誰執行 `CREATE EXTENSION`**。這是契約端點三問裡的
  「誰寫」缺一。依 `project.md` 的既有規則，本站**不回改已通過審查的上游產出**，
  而是標出缺口、寫明它讓哪一條需求目前不可滿足（`FR4.2` 的向量檢索），並由 N2
  指派具體落點。
- **N5 揭露的是已核可 NFR4 的字面範圍不足**，不是本站新增的需求。處置同上：
  就地標明，由本題定案後寫進本單元的 `security-requirements.md`，不回改
  `requirements.md`。

---

## N6 — 審查迴圈的停止判準（reviewer findings 觸發的追問）

**本輪查到的事實**：

- 審查輪次上限為 2，已用罄。iteration 2 的結果是 11 項 Resolved、1 項 Unresolved、
  6 項 New，其中 1 項 Critical。
- reviewer 給出的三類計數：**(a) 由 iteration 1 的修正新引入 = 5、(b) 既存漏審 = 1、
  (c) 真正的新設計問題 = 0**。自我製造佔比 83%。
- `project.md` 有兩條規則同時適用且方向相反：`application-design:c4`
  （自己製造的 Critical 不得以「輪次用罄」放行，驗證輪不計入上限）與
  `functional-design:c18`（自我製造佔比不降時應停迴圈、轉 open items）。

- A. 修完七項（Critical R-13、未解的 R-02、以及 R-14–R-18）再跑**一輪驗證**；
  停止判準事先講定：該輪若再出現任何自己製造的 Critical，就停、轉 open items 進閘門
- B. 只修 Critical R-13，其餘六項連證據與修法登錄為 open items 帶進閘門
- C. 不再修，七項全部轉 open items 進閘門
- X. Other (please specify)

[Answer]: A  <!-- answered 2026-09-26T13:30:29Z via picker -->

---

## N7 — R-13 的修法：本機 dev 的 db 映像

**本輪查到的事實**：

- `schema_rbac.sql` 是**單一交易**：`:24` `BEGIN;` → `:633` `COMMIT;`（全檔 644 行）。
- `LOCAL-DEV.md:102` 與 `:120` 要開發者對 repo 根 `docker-compose.yml` 的 db 跑
  `psql … -f schema_rbac.sql`；`:105` 說明它建立「全部資料表、308 列 RBAC 預設矩陣，
  以及預設帳號 `admin`」。
- repo 根 `docker-compose.yml:3` 是 `postgres:15-alpine`——**不含 pgvector，
  且主版本與部署的 16 不同**。
- **把 `CREATE EXTENSION` 移出交易不夠**：`U5` 的記憶表依 `project.md` 的 blocking
  規則必須寫進 `schema_rbac.sql`，而那些表帶 `vector(1024)` 欄位，在無 pgvector 的
  伺服器上照樣讓整個交易中止。

- A. repo 根 `docker-compose.yml` 的 db 改為 `pgvector/pgvector:pg16`，與部署及 CI 一致；
  連帶修掉「本機 PG 15、部署 PG 16」這個既存落差。代價：開發者的本機 data volume
  需重建（跨主版本），須寫進 `LOCAL-DEV.md`
- B. 不改映像，`CREATE EXTENSION` 以可捕捉例外的形式包裝且 `U5` 的向量欄位在本機退化
- C. 改為 `pgvector/pgvector:pg15`，保持主版本不變、volume 不用重建
- X. Other (please specify)

[Answer]: A  <!-- answered 2026-09-26T13:30:29Z via picker -->

> **本答案已由 N8 取代**（同一輪內，使用者主動提出 PostgreSQL 18）。A 的內容（改為 `pgvector/pgvector:pg16`）不再適用；原答案保留供追溯，實際定案見 N8。

---

## N8 — PostgreSQL 主版本：是否三處一起升到 18（使用者主動提出）

**觸發**：使用者於本輪指出 PostgreSQL 已發布至 18（16 為 2023、17 為 2024、18 為 2025）。

**本輪查到的事實**：

- repo 現況：部署與 CI 皆 `postgres:16-alpine`，repo 根本機 dev db 為 `postgres:15-alpine`。
- PG 16 仍在支援期內（每個 major 支援五年），故「必須升」不是技術壓力，是選擇。
- N7=A 已經讓本機跨了一次主版本（15→16），volume 本來就要重建；但若只把本機升到 18，
  會重新製造「本機與部署主版本不同」這個 N7 正要修掉的落差。故只有「都 16」或
  「三處都 18」兩種自洽解。
- **staging 的 `cloud360_db` 有現存資料**，16→18 需 `pg_upgrade` 或 dump/restore，
  不是換 tag 就好。

- A. 維持 16，升版另開 intent（記為候選項）
- B. **三處一起升到 18**（本機、`docker-compose.test.yml`、`docker-compose.deploy.yml`）
- C. 先查證 pgvector 的 tag 發布狀況與升版路徑再決定
- X. Other (please specify)

[Answer]: B  <!-- answered 2026-09-26T13:34:58Z via picker -->

### 本階段新增、已核可 scope 尚未涵蓋（**需回補**）

**「資料庫主版本升級」不在 `scope-document.md` 的任何能力項內。** 本單元原本的範圍是
「加 pgvector 擴充」，B 選項把它擴為「對有現存資料的 staging 資料庫做 major upgrade」。
後果已於提問當下向使用者揭露：

1. `NFR6.3` 由「collation 判定 ＋ 必要時 `REINDEX`」換成 major upgrade 程序
   （版本與擴充相容性、回退窗口）。
2. 上游 `requirements.md` NFR6 與 `contract-summary.md` K-05 **兩處**逐字釘選的
   `postgres:16-alpine` 由「變體不同」升級為「**主版本不同**」的衝突。
3. `risk-and-sequencing-rationale.md` 的 **R7（B1 裝不下）**加重：B1 再多一項
   資料庫主版本升級。

依 `project.md` 的規則，本站**不回改**已核可的上游，而是在此與產出中逐處標明並要求回補。

---

## N9 — R-19（自製 Critical）出現後的處置：停迴圈還是補完（使用者主動指定）

**觸發**：驗證輪（實質第三輪）出現 `R-19`——**`[N8]`=B 的 PG 18 決定製造的 Critical**。
`N6`=A 事先講定的停止條件因此觸發。

**本輪查到的事實（逐行核對過）**：

- `deploy.yml:10–15` 於 merged PR 進 `ut` **自動**部署；`:108` 自動 `docker compose … up -d --build`。
- `rollback` job（`:169`，`if: failure()`）自動讀 `~/.cloud360/last-good-sha`（`:209`）、
  `git checkout --quiet "${LAST}"`（`:220`）後再 `docker compose … up -d --build`（`:222`）。
- `last-good-sha` **只在部署成功時推進**（`:148`）。
- `cloud360_db` 是**容器外部的具名 volume**（`deploy/docker-compose.deploy.yml:19–20`）。
- 兩個可達的壞狀態：①映像行先合併、volume 未轉換 → PG 18 拒掛 PG 16 PGDATA；
  ②volume 已轉換但 `last-good-sha` 仍指向升版前 commit（或升版 PR 因任何其他原因失敗）
  → **自動 rollback 拿 PG 16 映像去掛 PG 18 PGDATA，同樣拒絕啟動**。
- 另三項新 Major（`R-20`／`R-21`／`R-24`）**也只因主版本升級而存在**。

- A. 改回 PG 16 ＋ pgvector（只換變體不升主版本），`R-19`／`R-20`／`R-21`／`R-24` 四項於源頭消失
- B. **維持 PG 18，並把升級與相關調整補到最完整**——新增排序不變量、升版窗口內
  自動 rollback 的明文處置（列為 `S-4`），並一併修完 `R-20`–`R-27`
- C. 維持 PG 18，九項全轉 open items 不再修
- X. Other (please specify)

[Answer]: B  <!-- answered 2026-09-26T14:21:25Z via picker；使用者原話：「我要選維持PG 18，要求升級及調整到最完整」 -->

### 本題對 `[N6]` 停止條件的效力

`[N6]`=A 講定「驗證輪若再出現自己製造的 Critical 就停、轉 open items」。**本題以
使用者明示裁決取代該條件**：改為補完而非停止。此處記明，避免日後把它讀成規則被違反
而無人裁決——它是被裁決過的。

---

## N10 — 第四輪之後：本站修到底，還是把結構類交給正確的站（使用者裁決）

**觸發**：第四輪 5 項 Resolved、4 項只修一半、7 項新發現，其中 **6 項（86%）由上一輪
修正製造**，真正的新設計問題 **0**。另有一項是我寫錯的事實論證（`R-29`）。

**本輪查到的事實**：

- `schema_rbac.sql:11` 逐字「**不建立固定密碼管理員；bootstrap admin 由後端依環境變數
  建立**」，全檔唯一 `INSERT INTO` 是 `:321` 的 `role_permissions`。我據
  `LOCAL-DEV.md:105`（該檔逐字寫它建立「預設帳號 admin / admin123」）寫進產出的論證
  因此是錯的——**`LOCAL-DEV.md` 與 SQL 不符，屬 repo 既有的文件漂移**。
- `deploy/docker-compose.deploy.yml:9` 為 `name: cloud360`，故具名 volume 實際是
  `cloud360_cloud360_db`。
- `deploy.yml:172–175` 的 `rollback.if` 含 `github.event_name == 'pull_request'`
  ——**`workflow_dispatch` 觸發的部署本來就不會啟動 rollback**，是零改動的既有槓桿。
- `deploy/docker-compose.deploy.yml:40–41` 的註解逐字：「No fallback on purpose:
  this makes scripts/validate_env_contract.py require render-env.sh and
  deploy/.env.example to keep writing it」——**repo 自己記載了兩道閘門的前提**，
  而本單元三份產出對它零字。

- A. 修機械／事實類七項，四項結構類寫成具體交接項交給 `infrastructure-design` 與
  `deployment-pipeline`（那兩站才改得動 `deploy.yml`）
- B. **本站全部修到底（含在需求裡寫死 `deploy.yml` 要怎麼改），再跑一輪**
- C. 先把 PG 18 升版拆出去，本單元只做 pgvector
- X. Other (please specify)

[Answer]: B  <!-- answered 2026-09-26T14:48:59Z via picker；使用者原話：「本站全部修到底，再跑一輪」 -->

### 已向使用者揭露、使用者在知情下仍選 B 的兩件事

1. 依前四輪實測趨勢，再一輪的期望是「修好 N 項、新增約 0.7N 項」
   （`project.md` `functional-design:c18` 的逐字預測）。
2. **本站只能寫需求文字，改不動 `deploy.yml` 本身**——`NFR6.3(b)` 的不變量 3
   若要成為真的檢查，落點只能是 `deployment-pipeline`。本站會把「要改成什麼」
   寫到可直接實作的程度，但那仍是需求而非改動。

---

## 收齊答案後的矛盾與覆蓋檢查

**矛盾偵測**：五題皆為明確選項，無「差不多」「看情況」類模糊作答。逐對核對：

- N3=A（餘裕不足時退到 `fastembed`）與 N4=A（Ollama 的唯一控制是網路隔離）**不衝突**
  ——N4 敘述的是 Ollama 若部署時的姿態，不要求它必然部署。
- N1=A（`REINDEX`）與 N2=A（啟動補丁）**互補**〔**`REINDEX` 成分已由 `[N8]`=B ＋
  `NFR6.3(a)` 取代，見 `:58`**〕：補丁每次開機都跑，既涵蓋換 image
  後的既有 staging，也涵蓋全新環境。
- N5=A（Redis 具名 volume）與 N1=A（備份與查詢驗證步驟；**`REINDEX` 成分已取代，見
  `:58`**）都落在 `DEPLOY.md`，
  同一份文件的兩處新增，無衝突。

**覆蓋檢查**（把已定案的驗證方式對照本單元最高風險的失敗模式）：

- `risk-and-sequencing-rationale.md` 的 **R4「部署設定的無聲降級」**是本單元最高風險。
  本輪五題**沒有一題碰到它**——但那不是缺口：它由 K-01 `sync_obligations` ＋ NFR8
  ＋ `C-O1`（blocking）約束，驗證載體是 `validate_env_contract.py`（會檢查「compose
  無 fallback 的變數必須真的被寫入」）。**已由上游覆蓋，本站不重複。**
- **但本輪定案新增了兩項沒有機械閘門的事**，必須在產出中誠實記載，不得讓它們看起來
  像被自動化守住：
  1. **N5 的 Redis 具名 volume**：`validate_env_contract.py` 管的是環境變數設定，
     **不檢查 compose 的 volume 宣告**。漏掉 volume 不會紅燈。
  2. **N1 的備份 ＋ 驗證步驟**（`REINDEX` 成分已取代，見 `:58`）：那是 `DEPLOY.md` 上由人執行的程序，
     **沒有任何 CI 檢查會驗證它被執行過**。

---

## Revision 2 — 因 `functional-design` 誤標 `[S]` 而回跳，本輪順帶修 R-50

**起因不是需求變更，是路由修復。** 先前一次前跳把 `functional-design`（3.1）標成 `[S]`，audit 逐字為 `Skipped by jump to nfr-requirements (forward)`——那是路由副作用，不是計畫決定。它影響 17 個工作單元中的 14 個（三個 `packaging` 單元本來就 kind-vacuous），而 `nfr-design` 把 `functional-spec` 列為 **`required: true`**，所以下一個單元 `brain-ws-contract`（`kind: spec`）一走到 3.3 就會撞到真缺口。

修復路徑經使用者裁決（兩次提問）：

1. 第一次選「直接把 checkbox 改回待辦」——**該路不存在**。`state-transition-guard` hook 無條件攔截 `aidlc-state.ts checkbox`，逐字為「Stage status cannot be changed with aidlc-state.ts checkbox because that bypasses the workflow's completion and approval checks」，且無任何旗標可放行。我把它列為選項是查證不足，已向使用者更正。
2. 第二次選「**往回跳，順便修 R-50**」。`jump execute --target functional-design --direction backward` 實際只重設兩個 stage（`functional-design`、`nfr-requirements`），其餘十個本來就是 `[ ]`、不在 RESETTABLE 集合內。三份 artifact 全部留在磁碟上。

**本輪因此多做一件事**：上一輪審查（iteration 3）給了 READY，但留下 **R-50（Minor）** 未修——因為當時 attempt 僅有的一次 stale-receipt 補救審查已用在 R-46…R-49 上。回跳給了全新的審查預算，故 R-50 在本輪當場修掉，不再帶到寫 `DEPLOY.md` 那一次。

**R-50 的三個落點與修法**（同一個錯誤量詞）：

| 落點 | 原文（錯） | 改為 |
|---|---|---|
| `security-requirements.md:35`（`§〇` `S-5` 名稱欄） | `REDIS_USER` ＋ **一份**掛載的 Redis 設定 | `REDIS_USER` ＋ **每個 stack 各自的** Redis 設定承載者 |
| 同上（`S-5` 理由欄） | 需要多**一份**設定資產與多一個變數 | 需要**多一個設定資產承載者**與多一個變數 |
| `security-requirements.md:80`（`NFR4.1(c)` 承載者欄） | **一份**掛載的 Redis 設定資產……**且必須掛進兩份 compose** | **掛載的 Redis 設定資產**（**兩份 compose 各自一份**），或 compose 的 `command:` 覆寫（由 compose 逐 stack 內插）——**兩份 compose 都必須有** |

**為什麼「一份」是錯的**（同檔 `:95` 已有完整論證，本輪只是讓上游兩處與它一致）：Redis 的 ACL 把密碼綁在 user 那一行（`user <name> on >pass ~... +@...`），而 `redis.conf`／`aclfile` **不內插環境變數**；兩個 stack 的 `REDIS_PASSWORD` 來源不同（deploy 由 `render-env.sh` 以 `openssl rand -hex 32` 產生、test 內嵌測試用預設值）。共用一份檔只有兩種收法——把 deploy 憑證改成 repo 內的字面值（**等於把部署憑證放進 public repo**），或讓 test 用 deploy 的真憑證。兩者都不可接受。

**沒有任何已核可的答案被改動。** `[N1]`–`[N10]` 的作答與其後果全部原樣有效，三份 artifact 的實質內容除上表三處量詞外不變。

---

## Revision 3 — 修 R-51（`§六` 主旨已反轉），以 redo jump 取得新 attempt

**Revision 2 修好了 `functional-design` 的狀態，卻沒把這件事傳播到那個以轉交此缺口為全部內容的章節。** `security-requirements.md` `§六` 仍逐字宣稱「`functional-design` 已被整站標為跳過（`[S]`），但它對其餘 14 個單元是適用的」並引 `aidlc-state.md:87`。實查：該缺口已於回跳後關閉（同檔 `:89` 現為 `- [-] functional-design — EXECUTE`、`:31` 為 `- **In Progress**: functional-design`），而 `:87` 現在是 `### CONSTRUCTION PHASE`——**狀態主張、逐字引用、行號三者同時失效**。由審查 R-51（Major）查出。

這不是錯字，是一整節的主旨反了：讀到它的下游會去修一個已經修好的東西。`nfr-design`／`infrastructure-design`／`code-generation` 都以 `security-requirements.md` 為 consumes，所以它會真的被讀到。

**取得寫入權的路徑（重要，因為 guard 給的那條是壞的）**：`review-freeze` 只提供一條補救「Restart this stage with `/aidlc --stage nfr-requirements`」。但 `Current Stage` 當時是 `functional-design`，故該指令會解析為 **forward** jump，而 `aidlc-jump.ts` 的 forward 分支會把「當前 in-flight 的 stage」標成 `[S]`——**照做會把 Revision 2 剛修好的東西再弄壞一次**。`jump resolve` 回報 `affected_stages: []` 看不出這點，因為它只計算 current 與 target *之間*的範圍，不計算 current 自己。

改採 **`jump execute --target functional-design --direction redo`**：`redo` 分支只重設 target 自己再標回 `[-]`，`stages_skipped` 為 `[]`。執行後對 state 檔做全檔 diff，**唯一差異是 `Last Updated` 時間戳**——`functional-design` 仍是 `[-]`，沒有任何 stage 被標 `[S]`。這一步本身即為本輪取得新 attempt 與新審查預算的方式。

**本輪唯一的實質改動**：重寫 `§六`，把它由「待處理的缺口轉交」改為「已於 2026-09-26 修復的結案紀錄」，並換上可複驗的現況引用。保留全文而不刪除該節，是為了讓下游看得出這個缺口存在過、怎麼被發現、怎麼被關掉。新內容另補一項獨立證據：backward jump 事件的 `Changed Upstream Artifacts` 欄由引擎自行列出 **14 個單元目錄**下的 functional-design 產出路徑，故「14」不再只是本檔自行推算。

**沒有任何已核可的答案被改動。** `[N1]`–`[N10]` 的作答與後果全部原樣有效；三份 artifact 除 `§六` 外不變。

---

## Consolidated Summary Confirmation

- Looks correct
- Request changes

[Answer]: Looks correct  <!-- answered 2026-09-27T06:36:56Z via picker；重取：為取得 infrastructure-design 的新審查預算而執行的 redo jump 重設了整個 construction 區塊的 attempt floor。本站內容未改動（git status 對該目錄為空，已 commit） -->
