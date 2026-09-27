# NFR Design 問題 — `brain-infra`（U1）

## 這一輪只問四題，以及為什麼

`brain-infra` 是 `kind: packaging`，引擎解析後本站只產 `security-design.md` 與
`traceability.json`——`performance-design`／`scalability-design`／
`reliability-design`／`observability-design`／`logical-components` 五項的
`produces_kinds` 皆不含 `packaging`，是**設計上的缺席，不是漏寫**。

本單元的 `nfr-requirements` 已鎖掉大量事情（20 條編號需求），所以本站**不重問**
下列已定案項，它們在 `security-requirements.md` 都有編號落點：

| 已定案、本站不重問 | 落點 |
|---|---|
| Redis 需 ACL 專用使用者、值不得為 `default` | `NFR4.1` |
| ACL 設定資產兩份 compose 各自一份（設定檔不內插環境變數） | `NFR4.1(c)` |
| Redis 具名 volume ＋ AOF，僅限 deploy stack | `NFR4.2` |
| PG 18 ＋ pgvector 五個落點、`CREATE EXTENSION` 兩處承載 | `NFR6.1`／`NFR6.2`／`NFR6.2a` |
| 升版只走 dump/restore、三條排序不變量、七步程序 | `NFR6.3` |
| 七個變數不得帶 `:-` fallback、九處同步點 | `NFR8.1`／`NFR8.1a`／`NFR8.1b` |
| Redis 與 Ollama 對外暴露面為零（無 host port） | `NFR8.7`／`NFR8.8` |
| 兩個新容器的記錄承載與保存期 | `NFR8.9` |
| 憑證值不得含 `$` | `NFR8.6` |

也**不重問**已明文交給別人的事（`security-requirements.md` `§五`）：episodic
memory 的加密**手段**（`OQ-3` → `U5`／`U8`）、`appendfsync` 具體值（`U10`）、Redis
ACL 的確切指令與 key pattern（`U10`）、ACL 採 `command:` 覆寫還是掛載檔（`U10`）、
`max-size`／`max-file` 具體值（部署者）、步驟 4 採哪一種做法（部署者）。

剩下的四題是**本單元自己的交付面上、requirement 沒有任何一條碰到**的事。四題全部
落在 ADR-0006 的 encryption 與 network exposure 兩個面向。

---

## 出題前的唯讀查證（**非來源登錄**，供題幹與選項引用）

以下每一項都逐字開檔核對過：

- **V1 — 兩份 compose 都沒有 `networks:` 宣告。** `deploy/docker-compose.deploy.yml`
  全檔 96 行，`grep -n networks:` 僅命中 `:33` 與 `:70` 的 `build.network: host`
  （建置期，非執行期網段）；`deploy/docker-compose.test.yml` 同樣無 `networks:`。
  故四個服務（`db`、`backend`、`frontend`、`cloudflared`）全在 compose 的**隱含
  `default` bridge 網段**上，彼此可互相到達。
- **V2 — `cloudflared` 就在那個扁平網段上。** 同檔 `:80–93`，它是本 stack 唯一
  對網際網路持續開著連線的容器（`tunnel ... run`）。
- **V3 — 內部連線一律明文。** 同檔 `:36` 逐字
  `DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}`
  ——無 `sslmode`。全 repo（`deploy/`、`DEPLOY.md`、`LOCAL-DEV.md`）唯一的 TLS 字樣是
  `deploy/cloudflared/config.yml:15` 的 `noTLSVerify: false`，那是**邊緣到源**，
  不是容器之間。
- **V4 — 靜態加密在 repo 內零痕跡。** `LUKS`／`encrypt`／`sslmode` 在 `deploy/`、
  `DEPLOY.md`、`LOCAL-DEV.md` 全無命中。`192.168.10.10` 目前沒有任何被記載的磁碟
  加密。
- **V5 — 檔案權限已有先例。** `deploy/docker-compose.deploy.yml:83–87` 逐字記載
  cloudflared 憑證檔「on the host is 0400, owned by uid 1000」，並說明刻意不放寬為
  world-read。故「以檔案權限保護敏感檔」在本 repo 已是既有實務，不是新發明。
- **V6 — dump 檔的內容。** `NFR6.3(a)` 收斂為只走 dump/restore；dump 會含 `users`
  全表（含 `password_hash`）與 308 列 RBAC 矩陣。`NFR6.3(c)` 的七步程序**沒有任何
  一步**規定 dump 檔的權限、存放位置或刪除時機。
- **V7 — secret 掃描器看不到那裡。** `scripts/validate_repo_contract.py` 的
  `validate_no_obvious_secrets()` 只讀 `contract_files()`（repo 層必要檔 ＋ baseline
  record 必要檔 ＋ audit shard），`deploy/` 與工作區內的任意 `.sql` 都不在其中
  （`team.md` `## Deployment` 的「已知的規則宣稱與機制落差」已逐字記載此事）。
- **V8 — 禁止路徑檢查擋不到 dump 檔名。** `validate_no_production_config_added()`
  做的是 path-part 精確比對 `prod`／`production`／`secrets`；
  `cloud360-dump-20260927.sql` 三者皆不命中。

---

## G1 — 靜態加密由哪一層承載

`NFR7.1` 只要求本單元「不製造使其無法實作的結構」（兩者皆為具名 volume），把**手段**
留給 `OQ-3` → `U5`／`U8`。但有一件事 `NFR7.1` 沒有決定，而它是本單元的：**加密要由
主機層還是應用層承載**。這決定了本站要不要在 `DEPLOY.md` 立一條運維前置條件。

參考 V4：`192.168.10.10` 目前沒有任何被記載的磁碟加密，所以不論選哪一條都是新增
工作，差別在新增在哪一層、誰驗。

- **A** — 主機層承載（全碟或 Docker volume 目錄所在檔案系統的加密），本站只在
  `DEPLOY.md` 立一條前置條件並給驗證指令；應用層不做任何加密。
- **B** — 應用層承載（只對 episodic memory 做欄位級加密），本站不立任何主機層要求。
- **C** — 兩層都要：主機層打底 ＋ 應用層對 episodic memory 再加一層。
- **D** — 本輪不立任何加密要求，明文記載為已接受的缺口，等 `U5`／`U8` 的 `nfr-design`
  一併決定。

[Answer]: A  <!-- answered 2026-09-27T00:39:01Z via picker -->

---

## G2 — 容器間的傳輸加密

參考 V3：現況是 compose 內部一律明文，`DATABASE_URL` 沒有 `sslmode`，全 repo 唯一
TLS 是邊緣到源。本單元要新增 Redis 與 Ollama 兩條內部連線，等於把明文連線由一條
（Postgres）變成三條。requirement 沒有任何一條碰到 in-transit，而 ADR-0006 的
encryption 面向涵蓋它，所以本站必須有落點。

- **A** — 沿用既有基線：compose 內部一律明文，信任邊界就是 compose network 本身；
  本站在 `security-design.md` 明文記載這個決定、它的前提（全部容器同主機、無跨主機
  流量）與它的代價。
- **B** — 只有 Redis 上 TLS（`rediss://`），Postgres 與 Ollama 維持明文。
- **C** — 三條連線全上 TLS。

[Answer]: A  <!-- answered 2026-09-27T00:39:01Z via picker -->

---

## G3 — Ollama 零認證在扁平網段上的處置

**這一題的起因是一個查證結果與 requirement 逐字衝突。** `NFR8.8` 寫 Ollama「其存取
控制**只有這一層**」，指的是「沒有 host port，只能從 compose 網段內連」。但參考 V1
與 V2：**那個網段是扁平的，而 `cloudflared` 就在上面**——它是本 stack 唯一對網際網路
持續開著連線的容器。所以現況不是「只有那一層」，而是**那一層並不區分任何容器**。

`NFR8.9` 已把「零認證前提下未授權的 Ollama 呼叫在記錄上不可辨識」記為**已接受的
代價**，所以本題不是要不要加認證，而是**要不要縮小誰碰得到**。

- **A** — 引入 compose `networks:` 分段：Ollama 與 Redis 只掛在一個 `internal` 網段，
  該網段上只有 `backend`（與 `db`）；`frontend` 與 `cloudflared` 不在其上。
- **B** — 不分段，接受扁平網段，並在 `security-design.md` 明文記載
  `cloudflared`／`frontend` 也能到達 Ollama 與 Redis；同時更正 `NFR8.8` 那句「只有
  這一層」的措辭，使設計文件不含與現實不符的陳述。
- **C** — 不分段，改在 Ollama 前面加一層最小認證（反向代理 ＋ 共享 token）。

[Answer]: A  <!-- answered 2026-09-27T00:39:01Z via picker -->

---

## G4 — 升版窗口內 dump 檔的處置

參考 V6／V7／V8：dump 是**全庫明文**（含 `password_hash`），而 `NFR6.3(c)` 的七步
程序對它的權限、位置、刪除時機**一條都沒有**；本 repo 的 secret 掃描器結構上看不到
它，禁止路徑檢查也擋不到它的檔名。V5 顯示「以檔案權限保護敏感檔」在本 repo 已是既有
實務（cloudflared 憑證 0400）。

- **A** — 立三條硬要求寫進 `DEPLOY.md`：建立時即 `umask 077`（0600、owner-only）、
  只准放在 `$HOME` 下的專用目錄（**不得放在 repo 工作區**，避免被 `git add -A` 撈
  進去）、升版驗證通過後立即刪除並在 `DEPLOY.md` 要求記錄該刪除動作。
- **B** — 只要求 0600 權限，存放位置與刪除時機交給執行者判斷。
- **C** — 要求 dump 檔先加密（`gpg` 或 `openssl enc`）才落地。
- **D** — 不立要求，記為已接受的缺口。

[Answer]: A  <!-- answered 2026-09-27T00:39:01Z via picker -->

---

## G5 — 一致性追問：G1 的主機層加密涵蓋範圍（收齊答案後的矛盾偵測觸發）

**為何加開這一題。** `G1`=A 與 `G4`=A 合起來出現一個承載性缺口：`G4` 要求 dump 檔放在
`$HOME` 下的專用目錄，**那不是 Docker volume**。若 `G1` 落地成「只加密 Docker volume
目錄所在的檔案系統」，dump 檔（全庫明文、含 `password_hash`）完全不在加密範圍內。兩個
答案本身不矛盾，但合起來不足——這正是 `project.md` 的 `feasibility:c5` 要求「寧可加開
一致性追問當場定錨」的形狀。

- **A** — 全碟加密：`DEPLOY.md` 的前置條件寫成「`192.168.10.10` 的系統碟須啟用全碟
  加密」。一條同時涵蓋兩個新 volume、既有 db volume、`G4` 的 dump 檔、`deploy/.env`
  與 cloudflared 憑證。
- **B** — 只加密 Docker 資料目錄（`/var/lib/docker/volumes` 或其所在分割區）。
- **C** — Docker volume 目錄 ＋ `G4` 指定的 `$HOME` dump 專用目錄兩者。

[Answer]: A  <!-- answered 2026-09-27T00:46:09Z via picker；此時間戳為 date -u 實測值，初稿曾誤填一個未實測的 00:41:30，已就地更正 -->

**定案後果**：`security-design.md` 的加密設計以「全碟加密」為單一前置條件，不維護
任何「哪些目錄有加密」的清單——理由是那張清單每加一個新服務就會漏一項，而本 repo
沒有任何機械閘門會發現漏項。代價已向使用者揭露並接受：對現有主機而言這是一次重裝或
資料遷移，不是改一個設定；且開機需要解鎖（passphrase 或 TPM），會影響斷電後的自動
回復——而 `deploy.yml` 的自動自癒（`restart: unless-stopped` ＋ 自架 runner）預設主機
會自己回來。**這一項必須寫進 `DEPLOY.md` 的前置條件，並在 `security-design.md` 明記
它與斷電自動回復的張力。**

---

## Revision 1 — 第二輪審查的四項新發現（R-14…R-17），含 `R-16` 的使用者裁決

第一輪審查 NOT-READY、13 項全修；第二輪 READY 但又查出四項。三項是機械可修，第四項
（`R-16`）會擴大本單元範圍，已向使用者揭露後果並取得裁決。

| # | 嚴重度 | 內容 | 處置 |
|---|---|---|---|
| `R-14` | Major | blast radius 的「分段後 = 1」不成立。user-defined bridge 預設 ICC 開啟，**同網段成員彼此可達全部端口**，故分段後 `internal` 上能直連 `redis:6379` 的是 `backend`／`db`／`ollama` 三個；分段前也少算（`redis` 與 `ollama` 彼此亦可達），應為 5。真實變化 **5 → 3** | 三處數字統一，並明寫 **D-3 隔離的是 `edge`↔`internal`、不隔離 `internal` 內部**——`db` 被攻陷後仍碰得到 Redis 的全部 session |
| `R-15` | Minor | 同檔自相矛盾：D-2 的「從四個縮到兩個」對撞 blast radius 表與 `§二` 的「4 → 1」，而前者正是為修 R-04 新寫的區塊 | 四處以 `R-14` 定案的數字統一 |
| `R-16` | Major | **R-01 那個 Critical 的洞沒關上。** 探測只落在 `DEPLOY.md` 的手動升版章節，而 R-01 要防的失敗是無人值守的：`deploy.yml:10–14` 觸發於合併進 `ut`，D-3 這次網段變更就走那條路。照原設計實作，`deploy.yml` 對 `/api` 的命中數仍是 0，引入分段的那一次部署仍綠燈通過 | **使用者裁決（下方 `G6`）** |
| `R-17` | Minor | 探測片段無 `--max-time`，而 `frontend/nginx.conf:30` 是 `proxy_read_timeout 600s`、Docker 跨網段隔離是 DROP（非 reject），故「網段打錯」的實際表現是逾時後回 504——而文中把 504 歸因為「backend 不可達」，會把診斷指向誤導 | 加 `--max-time`，並把失敗分類改為「500 與逾時同屬資料面不可達」 |

---

## G6 — R-16：探測要不要推進 `deploy.yml`（使用者裁決）

- **A** — 把探測列為 `deploy.yml` 的部署後步驟（接在現有 8090 健康檢查之後），由本單元
  交付。`NFR8.1` 已逐字要求本單元維持「`deploy.yml` 兩處同步」，故該檔本來就在範圍內；
  探測不需要任何 secret、不產生狀態。
- **B** — 不改 workflow，明文記載「引入分段的那一次自動部署仍無閘門」，加進 `§四` 的
  無閘門清單並指名承接站與「該站可能 skip」的風險。
- **C** — 推進 `deploy.yml` 但失敗只記 warning、不讓 job 紅燈。

[Answer]: A  <!-- answered 2026-09-27T02:01:48Z（實測值；初稿誤填未實測的 02:00:29，第三次同型失誤，已就地更正） via picker；推進 deploy.yml 做部署後步驟 -->

**定案後果（已向使用者揭露）**：本單元從「只改 `deploy.yml` 的環境變數同步」擴大到
「改它的部署流程」。這是五題原始定案（`G1`–`G5`）**沒有涵蓋**的新增工作量，依
`project.md` 規則須在產出內標為「本階段新增、已核可 scope 尚未涵蓋」並要求回補——
落點為 `security-design.md` 的 `§〇`（新增一節）與 `traceability.json` 的
`SCOPE-DEPLOY-YML-PROBE` 條目。

---

## Revision 2 — 第三輪審查的六項新發現（R-18…R-23），含 `R-22` 的使用者裁決

第三輪議決 READY、R-14…R-17 全部 Resolved，但又查出六項。三類切分：**修正動作新引入 4
項、既存漏審 2 項、真正的新設計問題 1 項**（`R-18`）。

| # | 嚴重度 | 內容 | 處置 |
|---|---|---|---|
| `R-18` | Major | **本輪唯一的真設計問題，且是我造成的。** 探測是單發斷言、無就緒重試，卻被接在一個只證明 nginx 活著的檢查之後。`deploy/docker-compose.deploy.yml:77–78` 的 `frontend.depends_on: - backend` **無 `condition:`**；`deploy.yml:118` 第一次 `curl /` 成功即 `exit 0`；而 `backend/main.py:46–50` 的 startup **同步**跑 `init_db()`，`backend/database.py:74–83` 含六個 `_ensure_*_schema` DDL 補丁——這段完成前 `/api/*` 一律 502。誤判會觸發 rollback、**對一個沒問題的合併開 revert PR**、dispatch Deploy Doctor。附帶：落點寫「即 `:116` 那一段之下」，照字面是 `exit 0` 之後的**死碼** | 改為 `deploy` job 的**獨立新步驟** ＋ 與既有兩道檢查同形的有界重試（30 × 5s，出現 401 即通過）；並寫明窗口的意義是區分「backend 還在跑 DDL 補丁」與「資料面真的斷掉」、每新增一個補丁要重評窗口 |
| `R-19` | Major | 被 `R-14` 判定為錯的「由 4 個縮到 1 個」在 `traceability.json` 的 `NFR4.1` **原樣存活**，與同檔 `NFR8.7` 的「5 → 3」直接對撞。上一輪列修正落點時只列了四處、漏了這第五種表達形式 | 改為與 `NFR8.7` 一致的「由 5 個縮到 3 個（`backend`／`db`／`ollama`）」，並補「`internal` 內部不隔離，故暴露面縮小而未縮到單一容器」 |
| `R-20` | Minor | `PROBE-API-DB` 欄位內先寫「失敗分類已更正」，其後的括號又原樣留著它自己指名為錯的「502／504 = backend 不可達」。`R-17` 的修正只落在 `security-design.md`、未傳播 | 改為與分類表一致 |
| `R-21` | Minor | 我把 `NFR8.1` 的「兩處同步」轉述為「deploy 與 rollback 兩個 job 都要呼叫 `render-env.sh`」，而上游逐字指的是**兩個 job 的 `env:` 對照表**；「都要呼叫 `render-env.sh`」是 `project.md ## Mandated` 的**另一條**規則。結論不受影響、反而更強，但引用不成立 | 改引 `NFR8.1` 的實際內容 |
| `R-22` | Minor | 本檔自己點名 rollback 路徑會印「rolled back and healthy on 8090」而資料面全壞（`deploy.yml:230` 仍只 `curl /`），但 `S-6` 只把閘門加進 `deploy` job——自己指出問題卻只修一半 | **使用者裁決（下方 `G7`）** |
| `R-23` | Minor | 我把「關閉 ICC」寫成「可行但未採用」。`enable_icc=false` 對 user-defined bridge 是**該網段內全部容器間流量一律 DROP**、無 per-pair 例外，故它會連 `backend` 的必要連線一起切斷——不是壓到 1，是壓到 0 並讓 stack 失能 | 兩個手段分開敘述，ICC 標為不可行；「2 → 4 個網段」的成本只掛在可行的那一個 |

---

## G7 — R-22：探測要不要也加進 `rollback` job（使用者裁決）

- **A** — 同一個探測加進 `rollback` job 的健康檢查迴圈（`deploy.yml:229–236`），使
  「rolled back and healthy on 8090」真的涵蓋資料面。
- **B** — rollback 不動，在 `§四` 明列「回滾後的資料面連通性仍無閘門」並寫明為何可接受
  （回滾目標是 last-good、先前驗證過的設定）。
- **C** — 設計上兩個 job 都要求，但實作留下游、改指名承接單元。

[Answer]: A  <!-- answered 2026-09-27T02:45:01Z via picker；理由：只修 deploy job 等於自己指出問題卻只修一半，而 rollback 正是探測失敗後的必經路徑 -->

**定案後果**：`S-6` 的範圍由「改 `deploy` job」擴為「改兩個 job」。`NFR8.1` 已記載兩個
job 的守門本來就不對稱（`rollback` 沒有等價的 required-secrets 步驟），本次會讓它在
**資料面驗證**這一項上對稱。仍屬 `§〇` 的 `S-6`，需回補進 scope。

---

## Consolidated Summary Confirmation

- Looks correct
- Request changes

[Answer]: Looks correct  <!-- answered 2026-09-27T02:45:46Z via picker；Revision 2（R-18…R-23，含 G7 裁決）之後重新取得 -->
