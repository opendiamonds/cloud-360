# Security Design — `brain-infra`（U1）

## 這份檔在做什麼

`brain-infra` 是 `kind: packaging`：它交付的是**部署形狀**（**三份** compose——
`deploy/docker-compose.deploy.yml`、`deploy/docker-compose.test.yml`、repo 根的
`docker-compose.yml`（本機 dev）——加上 `render-env.sh`、**`.github/workflows/deploy.yml`**
（`NFR8.1` 逐字要求本單元維持它的「兩處同步」；本站另新增一個部署後步驟，見 `§〇` 的
`S-6`）、`DEPLOY.md`、`LOCAL-DEV.md`），
不是任何執行期程式碼。**三份**這個數字來自已核可的 `NFR6.1`：它的落點 1–4 涵蓋四處
image 宣告，其中落點 4 逐字就是 repo 根的 `docker-compose.yml`。D-3 只適用於前兩份，
理由見該節的適用性表。所以本檔是
「這個部署包的安全設計」，而不是應用層的認證授權設計——後者屬 `U10 session-store`、
`U13 brain-gateway` 等 `service` 單元。

引擎解析 `produces_kinds` 後，本站對本單元只產本檔與 `traceability.json`。
`performance-design`／`scalability-design`／`reliability-design`／
`observability-design`／`logical-components` 五項的 `produces_kinds` 皆不含
`packaging`，是**設計上的缺席，不是漏寫**。這一點的後果寫在 `§五`。

本檔的上游是 `construction/brain-infra/nfr-requirements/` 的 20 條編號需求
（`NFR4.1`–`NFR9.1`）與 `tech-stack-decisions.md`。**本檔不重述那些需求**，只設計
它們沒有決定的事，並在 `traceability.json` 對每一條給出對應關係。

---

## 〇、本階段新增、已核可 scope 尚未涵蓋（**需回補**）

| # | 項目 | 由來 | 為何它不是既有範圍的自然延伸 |
|---|---|---|---|
| **S-6** | **把 `/api` 探測加進 `deploy.yml`——`deploy` job 的獨立新步驟 ＋ `rollback` job 的健康檢查迴圈**（失敗讓 job 紅燈） | 審查 R-16（Major）＋ `[G6]`=A；rollback 那一半為審查 R-22 ＋ `[G7]`=A | 本單元對 `deploy.yml` 的既有義務是 `NFR8.1` 逐字要求的「**兩處同步**」——而那指的是**兩個 job 的 `env:` 對照表**（該條的表格逐字列出 `deploy` → `:90–104`、`rollback` → `Restore the last-good deployment` 步驟的 `env:`，並明寫「兩個 job 的改動不對稱」、`rollback` **沒有**等價的 required-secrets 守門）。**新增驗證步驟是改它的部署流程**，性質不同：它會在部署失敗時觸發既有的 `rollback` job，因此是一個**新的自動回滾觸發條件**。這不在 `G1`–`G5` 五題的任何一題裡，使用者在被揭露此後果後於 `[G6]`／`[G7]` 裁決採用。（初版把 `NFR8.1` 轉述為「deploy 與 rollback 兩個 job 都要呼叫 `render-env.sh`」——那是 `project.md ## Mandated` 的**另一條**規則，不是 `NFR8.1`；審查 R-21 更正） |
| **S-7** | **`DEPLOY.md` 的前置條件新增全碟加密與其四個掛載點檢查、解鎖方式的記載** | `[G1]`=A ＋ `[G5]`=A ＋ 審查 R-05／R-06 | `NFR8.5` 的既有八項都是「部署時要知道的事」；本項是**部署環境必須先具備的條件**（一次重裝或資料遷移），而且它與斷電自動回復有張力（`§三`）。已核可的 scope-document 沒有任何一項涉及主機層的磁碟配置 |

**兩項都需要回補進 scope。** 依 `project.md`：本階段新增或推翻的項目須逐處明標而非當作
既有 CAP 的自然延伸吸收。`S-6` 的後果已在提問當下（`[G6]` 的選項說明）向使用者揭露。

---

## 一、四個設計決定，來自五題（`G5` 為一致性追問）

問題檔實際有**五題**：`G1`–`G4` 是原始出題，`G5` 是收齊答案後的矛盾偵測觸發的一致性
追問（`[G1]`=A 與 `[G4]`=A 合起來出現承載性缺口——dump 檔不在 Docker volume 內）。四個
**決定**由五個**答案**支撐，D-1 那一列即由 `[G1]` ＋ `[G5]` 兩個答案共同決定。

五題全部落在 ADR-0006 的 **encryption** 與 **network exposure** 兩個面向，因為逐一比對
20 條需求與 `§五` 的六項明文轉交之後，真正還開著且屬本單元的只有這些。

| # | 決定 | 來源 |
|---|---|---|
| **D-1** | 靜態加密由**主機層**承載（全碟加密），應用層不加密 | `[G1]`=A ＋ `[G5]`=A |
| **D-2** | 容器間傳輸**維持明文**，信任邊界是 compose network 本身 | `[G2]`=A |
| **D-3** | 引入 compose `networks:` **分段**，internal 網段只有 `backend` ＋ 資料面三個容器 | `[G3]`=A |
| **D-4** | 升版 dump 檔立**三條硬要求**（權限、位置、刪除） | `[G4]`=A |

### D-1 — 靜態加密：主機層全碟加密

**設計**：`192.168.10.10` 的系統碟啟用全碟加密（LUKS 或等價機制）。這是**部署環境的
前置條件**，不是 compose 或應用程式的設定。本站的交付是把它寫進 `DEPLOY.md` 的前置
條件章節並給出驗證指令。

**為什麼是全碟，而不是只加密 Docker 資料目錄**：後者需要在 `DEPLOY.md` 維護一張
「哪些目錄在加密範圍內」的清單，而那張清單每新增一個服務、每新增一個落地檔就會漏一
項，**且本 repo 沒有任何機械閘門會發現漏項**（`validate_env_contract.py` 只解析環境
變數，`validate_repo_contract.py` 只讀 contract 檔清單）。全碟是唯一不需要維護清單的
形狀。

**一條前置條件實際涵蓋的範圍**（這是選它的具體理由，不是附帶好處）：

| 落地物 | 內容敏感度 | 在 Docker volume 內？ |
|---|---|---|
| Redis AOF volume（`NFR4.2`） | 完整 session 上下文 | 是 |
| 資料庫 volume：**改名後的新 volume ＋ 保留期內的舊 `cloud360_db`**（`NFR6.1` 落點 5 定案必須改名，`deploy/docker-compose.deploy.yml:20` 與 `:96` 兩處同步；`NFR6.3` 步驟 7 承諾舊 volume 保留至驗證通過） | 各含一份 `users` 全表（含 `password_hash`）、全部 RBAC 權限矩陣、三種記憶 | 是（兩者皆是） |
| Ollama 模型快取 volume（`NFR4.3`） | 模型權重，非機密 | 是 |
| **`NFR6.3` 的升版 dump 檔** | **全庫明文** | **否**（在 `$HOME` 下，見 D-4） |
| **`deploy/.env`** | `POSTGRES_PASSWORD`、`JWT_SECRET`、`OPENROUTER_API_KEY`、`REDIS_PASSWORD` | **否**——但暴露窗口有界，見下 |
| **cloudflared 憑證 JSON** | tunnel 憑證 | **否**（host bind mount） |

下面三列是「只加密 Docker 目錄」會漏掉的東西，而其中兩列（dump 檔、`deploy/.env`）
比 volume 內的任何東西都更集中、更容易被整份帶走。

**升版窗口內資料庫的明文副本數是三份，不是一份**：新 volume、保留中的舊 volume、以及
D-4 的 dump 檔。全碟加密涵蓋三者；D-4 的刪除要求只管 dump，**舊 volume 的最終處置由
`NFR6.3` 步驟 7 的回退窗口決定**，本站不縮短它（回退能力優先），但 `DEPLOY.md` 應在
回退窗口結束時要求 `docker volume rm` 舊 volume 並記錄——否則它會無限期留著。

**`deploy/.env` 的窗口是有界的，這一點要說準確**：`contract-summary.md` 的 `K-01`
`behaviour_semantics.observable_side_effects` 逐字記載「`render-env.sh` 會**覆寫**
`deploy/.env`（部署後該檔會被清理，避免機敏檔留在 runner 上）」。所以它不是長期躺在
磁碟上，而是每次部署期間短暫存在。但**自架 runner 就是 `192.168.10.10` 本身**（
`deploy.yml` 的 `runs-on: [self-hosted, linux, x64, cloud360]`），所以那個窗口內它就在
這台要加密的機器上；而 `deploy.yml` 若在清理步驟之前失敗（例如部署失敗轉進 rollback
job），該檔會留存到下一次成功部署為止。全碟加密涵蓋這兩種情況，「只加密 Docker 目錄」
都不涵蓋。

**驗證方式**（可二元判定，寫進 `DEPLOY.md`）。**注意 `lsblk` 的輸出形狀**：LUKS 之下，
掛載點所在裝置的 `FSTYPE` 是 `ext4`／`xfs`（那是解密後的映射裝置），`crypto_LUKS` 出現
在它的**父裝置**上。所以不能斷言「掛載點的 FSTYPE 為 `crypto_LUKS`」——那永遠不成立。
正確的判準是：

1. **祖先鏈中存在** `FSTYPE` 為 `crypto_LUKS` 的裝置——不是「上一層就是」。
   `lsblk -s -o NAME,FSTYPE <承載該掛載點的裝置>` 反向列出祖先鏈，斷言鏈中出現
   `crypto_LUKS` 即通過。**寫成「上一層」會在正確加密的主機上判成失敗**：三大發行版
   引導式 FDE 產生的是 **LVM-on-LUKS**，`/` 在 LV 上 → VG → PV 落在
   `/dev/mapper/<luks>` → `crypto_LUKS` 的分割在兩層以上之外，直接父層的 `FSTYPE` 是
   `LVM2_member`。
2. `cryptsetup status <映射裝置名>` 回報 `type: LUKS1`／`LUKS2` 且 `active`。
3. **ZFS 原生加密是合格但不會出現 `crypto_LUKS` 的情形**，須改以
   `zfs get -H -o value encryption <dataset>` 判定其值不為 `off`。第 1、2 點對它不
   適用，不得因此判為未加密。
4. **欄位名相容性**：`MOUNTPOINTS`（複數）需 util-linux ≥ 2.37；較舊主機只有
   `MOUNTPOINT`。`DEPLOY.md` 應同時給兩種寫法，或改用 `findmnt -no SOURCE <path>` 先
   取得裝置再餵給 `lsblk -s`。

**要逐一檢查的掛載點，不只 `/`**（下列任一若為獨立掛載，就對它重複第 1–3 點）：

| 掛載點 | 為什麼它在清單上 |
|---|---|
| `/` | 基準 |
| `/var/lib/docker` | 三個具名 volume 的實體位置。搬到獨立的未加密資料碟是常見做法 |
| **`/home`（或 `$HOME` 所在掛載點）** | **D-4 的全庫明文 dump 就放在 `$HOME/cloud360-upgrade/`**，而 D-4 的「與 D-1 的關係」正是靠「它在 `$HOME` 下、系統碟加密」來主張離線面已涵蓋。`/home` 獨立掛載至少與 Docker 目錄獨立掛載一樣常見 |
| **自架 runner 的工作目錄** | `deploy/.env` 在部署窗口內落在這裡（`deploy.yml:27` 的 `runs-on: [self-hosted, linux, x64, cloud360]`），且部署失敗時會留存到下一次成功部署 |

這張表不是形式主義：漏掉其中任一項，都會讓「系統碟已加密」與「那份最集中的明文資料
其實沒加密」同時為真——而這正是選全碟加密（`[G5]`=A）要避免的形狀。`DEPLOY.md` 的前置
條件必須**逐一列出**這四個檢查對象，不得只寫「系統碟須加密」。

**這個決定的邊界，必須寫清楚，否則會被讀成比實際更強的保證**：

- **保護的是**：磁碟離線曝露——磁碟遭竊、主機報廢未清碟、備份介質外流、雲端快照
  被複製。
- **不保護的是**：**任何在主機執行中時的曝露**。作業系統一旦掛載，加密對執行中的
  行程完全透明。取得主機 root、或取得任一容器執行權並能讀取 volume 掛載點的人，讀到
  的是明文。
- 所以 D-1 與 D-2 是**互補而非重疊**：D-1 管離線，D-2 明文接受的正是線上這一面，而
  D-3 是縮小線上那一面的唯一措施。三者必須一起讀。

**已接受的代價（使用者在知情下選擇）**：

1. 對既有主機而言這是**一次重裝或資料遷移**，不是改一個設定。全碟加密無法對已在使用
   的未加密根檔案系統就地啟用。
2. **開機需要解鎖**（passphrase 或 TPM），這與斷電後的自動回復產生張力——見 `§三`。
3. 本 repo 的 CI **完全驗不到**它。這是純運維前置條件，沒有機械閘門。

### D-2 — 傳輸加密：維持明文，信任邊界是 compose network

**設計**：compose **內部**的三條連線（`backend`→`db`、`backend`→`redis`、
`backend`→`ollama`）一律明文。不引入 TLS、不引入憑證管理。

**範圍限定：本決定只涵蓋容器之間，不涵蓋任何對外的一段。** 這一句必須在最前面說，
否則「維持明文」會被讀成整個系統是明文，而那是錯的。對外的兩段都已加密，且都由別的
單元擁有：

| 對外邊界 | 傳輸 | 擁有者 | 出處 |
|---|---|---|---|
| 瀏覽器 ↔ 大腦（WebSocket） | **`wss`**，經 Cloudflare Tunnel；token 走**標頭**而非 query string（避免進 nginx 與 cloudflared 的 access log） | `U13 brain-gateway` | `contract-summary.md` `K-12`；ADR-0006 判定表的 Encryption 列 |
| 大腦 ↔ OpenRouter | HTTPS，`base_url` 受一致性斷言鎖定、**不得**指向其他服務 | `U11 intent-router` | `contract-summary.md` `X-03` |

`contract-summary.md` 的 ADR-0006 判定表逐字寫「`K-12` 是本 intent **唯一**新增的對外
網路面」。本單元不新增任何對外網路面（`NFR8.7`／`NFR8.8` 要求兩個新服務暴露面為零），
所以 D-2 的明文範圍與那兩段加密邊界之間沒有重疊、也沒有縫隙。

**現況基線（查證結果，非推測）**：`deploy/docker-compose.deploy.yml:36` 逐字為
`DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}`
——沒有 `sslmode`。全 repo（`deploy/`、`DEPLOY.md`、`LOCAL-DEV.md`）唯一的 TLS 字樣是
`deploy/cloudflared/config.yml:15` 的 `noTLSVerify: false`，那是**邊緣到源**，不是容器
之間。所以本單元不是「把加密拿掉」，是「新增的兩條連線沿用既有基線」。

**成立的前提，缺一則本決定不成立**：

1. 全部容器在**同一台主機**，流量不離開 Docker 的虛擬網橋，不經過任何實體網段。
2. 沒有跨主機、跨機房的服務呼叫（本部署形狀下為真：唯一對外的出口是 `cloudflared`）。
3. **compose network 真的是一個有意義的邊界**——這一條在 D-3 之前**不成立**，見下。

**為什麼不上 TLS**：三條連線都要憑證，而憑證需要簽發、分發與輪替。本 repo 零既有承載
者（無 PKI、無 cert-manager、無自簽腳本），且 `deploy/docker-compose.test.yml` 每個 PR
重建一次短生命週期 stack——憑證要嘛內嵌進 repo（等於把憑證放進 public repo），要嘛
每次自簽（`ui-regression` 會成為憑證問題的第一個受害者）。引入 PKI 會讓本單元從
「部署打包」變成「引入一個新的機密生命週期」，那不是這個單元該承擔的。

**明文接受的代價，不是省略。信任邊界內有兩類主體，第二類必須被寫出來**：

1. **同一 `internal` 網段上的容器——成員集合就是 `internal` 的全部成員**
   （`backend`／`db`／`redis`／`ollama`），因為 user-defined bridge 預設 ICC 開啟、成員
   彼此可達全部端口。可讀 Redis 的 session 內容與 Postgres 的查詢流量（含以明文傳遞的
   憑證）。**D-3 把這一類由 5 個縮到 3 個**（移除 `frontend` 與 `cloudflared`），不是縮到
   1 個——數字與 D-3 的 blast radius 表一致，見該表的計數規則。
2. **`192.168.10.10` 上的任何 host-local 行程——包含自架 runner。** Docker bridge 網段的
   subnet 從 host 直接可路由，所以 host 上的任何行程都能以容器 IP 直連
   `redis:6379` 與 `ollama:11434`，**完全不需要 `ports:`**。D-3 對這一類**毫無作用**
   （分段只隔離容器之間，不隔離 host 與容器）。而 `deploy.yml:27` 的
   `runs-on: [self-hosted, linux, x64, cloud360]` 表示 GitHub Actions 的步驟就在這台
   主機上執行——**任何能讓該 runner 跑任意步驟的人（例如能合併進 `ut` 的人）都在信任
   邊界之內**，而 `NFR8.8` 已記載 Ollama 零認證。

第 2 類不是學術問題，也不是本設計新增的——它是 Docker bridge 網路的既有語意，本站的
交付是**把它寫出來**。既有的 `db` 一直有同樣的性質；本單元新增的 Redis（存全部 session）
與 Ollama（零認證）使它的後果變重。緩解它需要離開 compose 網路模型（例如改用 Unix
socket 或 host 防火牆規則），**不在本單元範圍**，且會與 `NFR8.7`／`NFR8.8` 的既有形狀
衝突；如實記載為已接受的代價。

### D-3 — 網段分段：`internal` 只有 `backend` ＋ 資料面

**這一項的起因是一個查證結果與已核可需求逐字衝突。** `NFR8.8` 寫 Ollama「其存取控制
**只有這一層**」，意指「沒有 host port，只能從 compose 網段內連」。但實查
`deploy/docker-compose.deploy.yml` 全檔 96 行，`grep -n 'networks:'` **只命中 `:33` 與
`:70` 的 `build.network: host`**（那是建置期設定，不是執行期網段）——**deploy 與 CI test
兩份 compose 都沒有任何 `networks:` 宣告**（repo 根那份也沒有，但它不在 D-3 範圍內）。
故該 stack 的四個服務全在 compose 的**隱含 `default` bridge**上，
彼此可互相到達。而 `cloudflared`（同檔 `:80–93`）正是本 stack **唯一對網際網路持續開著
連線的容器**。

所以分段之前，`NFR8.8` 那句話描述的那一層**並不區分任何容器**：`cloudflared` 被突破
即可直連無認證的 Ollama 與存著全部 session 的 Redis。**這也使 D-2 的理由在分段前是
空的**——「信任邊界就是 compose network」這句話，在邊界內含一個對外開著的容器時不成立。

**同一個措辭缺口也在契約層**：`contract-summary.md` 的 `K-01` `images_and_services`
對 `redis` 與 `ollama` 兩個服務的 `exposure` 逐字都是「compose 內部網路 only；**不得
publish port**」，而 ADR-0006 判定表的 Network exposure 列原樣引用了它。那句話管的是
**入向**（host 端口映射），完全沒有管**橫向**（同網段內誰連得到誰）——與 `NFR8.8` 是
同一個形狀。D-3 補的正是橫向那一半。**本站不回改已核可的 `K-01` 或 `NFR8.8`**；以本節
向下游傳遞，並由 `traceability.json` 的 `NFR8.8` 列記明更正依據。

#### ⚠ 本站在此推翻一個已核可的決定（審查 R-02，經使用者裁決保留 D-3）

**這不是修正措辭，是反轉。** 已核可的 `nfr-requirements/security-requirements.md`
`### NFR8.8` 的「未採用的替代方案與其代價」**逐字**列出：

> 反向代理加 basic auth（多一個容器與一組憑證）；**另切一個只含 `db`／`backend`／
> `ollama` 的內部 network（比 basic auth 輕，但 compose 網路設定變複雜）**。

而同節上方逐字寫「**這是刻意決定，不是遺漏（`[N4]`=A 定案）**」。**D-3 採用的正是被排除
的第二個方案**（本站的版本是 `db`／`redis`／`ollama` ＋ `backend`，形狀相同、多含 redis）。

**處置**：使用者在被明確告知此為反轉後裁決**保留 D-3 並明寫反轉**，不回改已核可的上游
文件（依 `project.md` 的既有規則：下游經人工確認的變更不回改已核可的上游 artifact，以
本站的紀錄向下游傳遞）。

**反轉的理由，以及上游當時為何排除它**：上游排除它的理由逐字是「compose 網路設定變
複雜」——那是成本評估，不是安全判斷。而上游寫那句話時**並不知道扁平網段上有
`cloudflared`**（那是本站的 V1／V2 查證才發現的）。所以反轉的依據是新事實，不是重新
權衡同一組事實。方向是**加強防守**、不移除任何既有控制。

**代價（誠實記載）**：已核可的 `NFR8.8` 文字與本站設計自此並存矛盾——它說內部 network
分段「未採用」，本站說要用。靠這一段交叉引用維持可讀性；下一次觸及 `NFR8.8` 的人
（或後續的 practices-discovery）應把它就地標為已被本站反轉。

**本 repo 有三份 compose，D-3 只適用於其中兩份**（審查 R-07：初版寫「兩份」並在
`NFR8.4` 的判定裡寫「本機 dev 無 compose」，兩者皆錯）：

| compose | 路徑 | D-3 適用？ | 理由 |
|---|---|---|---|
| deploy | `deploy/docker-compose.deploy.yml` | ✅ | 線上 stack，`cloudflared` 在此，是 D-3 全部安全理由的所在 |
| CI test | `deploy/docker-compose.test.yml` | ✅ | 見下方「test stack 為何也要，但理由不同」 |
| **本機 dev** | **repo 根 `docker-compose.yml`** | **❌** | 它**刻意**publish 端口（`db` 的 `5432:5432`、`adminer` 的 `8080:8080`）供開發者以 GUI 與 psql 直連——那是它存在的目的。對它分段會破壞既有開發工具，且它上面沒有 `cloudflared`、沒有 Redis、沒有 Ollama，沒有任何要擋的威脅。**已核可的 `NFR6.1` 落點 4 逐字要求改它的 db 映像**，所以它確實在本單元的範圍內，只是不在 D-3 的範圍內 |

**設計**（deploy 與 CI test 兩份）：

```yaml
networks:
  edge:       # 對外側：tunnel 與 nginx
  internal:   # 資料面：只有 backend 與它依賴的後端服務
```

服務歸屬——**按 compose 檔分開列，因為兩份的服務集合不同**：

`deploy/docker-compose.deploy.yml`（六個服務）：

| 服務 | `edge` | `internal` | 理由 |
|---|---|---|---|
| `cloudflared` | ✅ | ❌ | 只需到達 `frontend`；它是唯一對網際網路開著的容器，**必須**被排除在資料面之外 |
| `frontend`（nginx） | ✅ | ❌ | 對外被 tunnel 到達，對內只 proxy 到 `backend` |
| `backend` | ✅ | ✅ | 兩側都需要：被 `frontend` 呼叫、呼叫三個後端服務。**它是唯一的橋** |
| `db` | ❌ | ✅ | 只有 `backend` 連它 |
| `redis`（新增） | ❌ | ✅ | 只有 `backend` 連它（`NFR8.7` 已要求無 host port） |
| `ollama`（新增） | ❌ | ✅ | 只有 `backend` 連它（`NFR8.8` 已要求無 host port） |

`deploy/docker-compose.test.yml`（**沒有 `cloudflared`**——`db`／`backend`／`frontend`
三個，加上本單元新增的服務）：

| 服務 | `edge` | `internal` | 理由 |
|---|---|---|---|
| `frontend` | ✅ | ❌ | Playwright 從 host 經 published port 打它 |
| `backend` | ✅ | ✅ | 同 deploy：唯一的橋 |
| `db` | ❌ | ✅ | 只有 `backend` 連它 |
| `redis`（新增） | ❌ | ✅ | 同 deploy |
| `ollama`（新增，**若該 stack 需要**） | ❌ | ✅ | 是否需要取決於 `U5`／`U6` 的 CI 驗證形狀，仍是待決事項（`nfr-requirements` 的 Assumptions 已記載） |

**test stack 為何也要，但理由不同——這一點必須說清楚**：deploy stack 分段是為了擋一個
**現存的威脅**（`cloudflared` 在資料面上）。test stack **沒有 `cloudflared`**，所以那個
理由在它身上是空的。它要分段的理由只有一個：**避免兩份 compose 的形狀漂移**——兩份若
一份有網段一份沒有，下一個改它們的人必須每次判斷「這個差異是故意的嗎」，而本 repo 已
有多起「兩份 compose 不一致導致無聲失敗」的前例（`NFR8.1a`／`NFR8.1b` 就是審查查出來
的兩處）。初版把理由寫成類比 `NFR4.1(c)` 的「兩份 compose 都必須有」是錯的引用——那一條
講的是 **ACL 設定資產**，不是網段。

**`frontend` 為何不進 `internal`**：它是 nginx，只做反向代理；`frontend/nginx.conf:17`
逐字為 `proxy_pass http://backend:8000;`，而 `backend` 在 `edge` 上，故服務名解析在
`edge` 內即可完成。把 `frontend` 排除在 `internal` 之外，使「nginx 設定被誤改或被注入」
不會直接變成資料面可達。

（附帶查證結果，非本站交付：`project.md` `## Mandated` 的 `LOCAL-DEV.md` 同步規則
逐字寫的是 `deploy/nginx.conf`，而該路徑**不存在**——實際檔案在
`frontend/nginx.conf`，由 `frontend/Dockerfile` 烘進映像。這是規則層的路徑誤植，不是
本單元的問題，但任何依那條規則去找檔案的人會找不到。已記入 stage diary 的 Open
questions 以便後續 practices-discovery 更正。）

**不得設 `internal: true`（本站定案，不留給實作時判斷）**：Docker 的
`networks.<name>.internal: true` 會斷開該網段的**對外出口**。若對 `internal` 設它：

- `ollama` 首次啟動需要**下載模型**（`NFR4.3` 的模型快取 volume 正是為此存在），
  斷開出口後模型永遠拉不下來，而失敗形式是啟動時的網路錯誤——不是設定錯誤訊息。
- **只影響 internal-only 的服務。** `backend` 同時掛在 `edge`（普通 bridge、有 NAT 與
  預設路由），所以它對 **OpenRouter**、**n8n webhook**、ADR-0018 目錄價端點的出向**不受
  影響**——Docker 不會把預設路由指向 internal 網段。**初版把 `backend` 的出向也列為
  會壞，那是錯的**（審查 R-03），且該錯誤本節原本要求抄進 compose 註解，會變成長期
  誤導，故就地更正。真正會壞的只有 **只掛 `internal` 的服務**：目前是 `ollama`，以及
  未來任何只掛 internal 的新服務。

**而 `internal: true` 並不是達成分段所必需的**：一個普通的 user-defined bridge 網段
**沒有 host 端口映射**（沒有 `ports:` 就沒有），且**跨 bridge 網段被 Docker 的隔離規則
阻擋**，出向則經 NAT 正常。D-3 要的是「縮小哪些容器彼此可達」，那由網段成員資格達成，
與 `internal: true` 無關。

**但「沒有入向可達性」這句話不能寫得更強**（審查 R-04）：bridge 網段的 subnet 從
host 直接可路由，所以**同一台主機上的行程**不需要 `ports:` 就能以容器 IP 直連
`redis:6379` 與 `ollama:11434`。D-3 隔離的是容器之間，**不隔離 host 與容器**。這一點已
寫進 D-2 的「信任邊界內有兩類主體」——self-hosted runner 就是第二類。

**所以兩份 compose 的 `networks:` 宣告一律不帶 `internal: true`，且這一句要寫進 compose
的註解**——否則下一個讀到網段名叫 `internal` 的人很可能「順手補上」那個旗標，而它會在
下一次部署的 Ollama 模型下載時才爆。註解只寫 internal-only 服務會失去出向這一個理由，
**不要抄「backend 出向會壞」那句錯的**。

**blast radius 的實際變化。先講清楚 D-3 隔離什麼、不隔離什麼**（審查 R-14 更正了初版
的數字，而初版的錯誤方向讓 D-3 看起來比實際有效）：

> **D-3 隔離的是 `edge` ↔ `internal`，它不隔離 `internal` 內部。** user-defined bridge
> 預設 `com.docker.network.bridge.enable_icc` 為 true——**同一網段的成員彼此可達全部
> 端口**。所以分段後 `internal` 上的 `db` 若被攻陷，它**仍然**碰得到 Redis 的全部
> session 與零認證的 Ollama。初版寫「分段後 = 1（`backend`）」是錯的，且錯在讓下游
> 以為碰不到。

計數規則：對每一列的目標服務，計算**除它自己以外**還有幾個容器能連到它的端口。

| | 分段前（全部六個在隱含 `default` 上） | 分段後（`internal` = `backend`／`db`／`redis`／`ollama`） |
|---|---|---|
| 可直連 Ollama `11434`（零認證）的容器 | **5**（`db`／`backend`／`frontend`／`cloudflared`／`redis`） | **3**（`backend`／`db`／`redis`） |
| 可直連 Redis `6379`（有 ACL，但 ACL 只是憑證層）的容器 | **5**（`db`／`backend`／`frontend`／`cloudflared`／`ollama`） | **3**（`backend`／`db`／`ollama`） |
| 突破 `cloudflared` 後可直接到達的資料面服務 | 3（`db`／`redis`／`ollama`） | **0** |

**所以 D-3 買到的是什麼**：前兩列是 **5 → 3**（移除 `frontend` 與 `cloudflared`），
不是 5 → 1。**第三列才是 D-3 的真正價值**：它把「唯一對網際網路持續開著連線的容器」
完全移出資料面，3 → **0**。

**要把前兩列壓到 1，只有一個可行手段，另一個看起來像手段但其實不是**（審查 R-23 更正
初版把兩者並列為「可行但未採用」）：

| 手段 | 可行？ | 說明 |
|---|---|---|
| `internal` 內部**再分段**（每個資料面服務各一個只含它與 `backend` 的網段） | **可行，但不在本站範圍** | 成本是 compose 的網段數由 **2 變成 4**（`edge` ＋ 三個 per-service 網段），且每新增一個資料面服務就再多一個。記為已知的未採用選項 |
| **關閉 ICC**（`com.docker.network.bridge.enable_icc=false`） | **不可行——不是「未採用」** | 它對 user-defined bridge 的語意是**該網段內全部容器間流量一律 DROP**，沒有 per-pair 例外（`--link` 的放行只存在於舊的 default bridge）。所以它會連 `backend`→`db`／`redis`／`ollama` 一起切斷——**不是把數字壓到 1，是壓到 0 並讓整個 stack 失能**。「2 → 4 個網段」那個成本說明也只對上一列成立 |

**本決定會動到既有的 `db` 服務**，不只新容器。把 `db` 移進 `internal` 本身零功能風險
（只有 `backend` 連它，服務名解析在同一網段內不變），但它是對**既有服務**的設定變更。

#### ⚠ 若分段打斷 `backend`→`db`，現有的閘門一個都不會發現（審查 R-01，Critical）

**初版在此宣稱「已由既有的 healthcheck 與 8090 健康檢查覆蓋，不需新機制」——那是錯的，
而且方向正好相反。** 逐一查證：

| 既有機制 | 實際打到哪裡 | 會不會發現 `backend`→`db` 斷掉 |
|---|---|---|
| `deploy.yml:116` `curl -fsS -o /dev/null http://127.0.0.1:8090/` | 路徑是 `/` → `frontend/nginx.conf:35–37` 的 `location /` → `try_files $uri $uri/ /index.html` → **回靜態檔** | **不會**。不經 `location /api/`、不碰 `backend`、更不碰 `db` |
| `deploy.yml:131` `curl -fsS -o /dev/null https://cloud360.danniel.cc/` | 同上，只是走 tunnel | **不會** |
| `db` 的 healthcheck（`docker-compose.deploy.yml:25` 的 `pg_isready`） | 在 **db 容器內部**執行 | **不會**。它證明 db 活著，不證明 `backend` 連得到它 |
| `depends_on: service_healthy`（同檔 `:63–65`） | 只管**啟動順序** | **不會** |

`deploy.yml` 全檔對 `/api` 的命中數是 **0**。所以若 D-3 的網段歸屬打錯，deploy job 會
**綠燈通過**，而 rollback 路徑也會印出「rolled back and healthy on 8090」——站台首頁正常、
所有需要資料庫的功能全壞。**這正是本 repo 已寫進規則層的「既有閘門對此變更路徑無效」
那個形狀，而初版反向宣稱它已被覆蓋。**

**處置：本站新增一個驗證項，而它必須落在兩個地方**（`[G6]`=A，見下方「為何 `DEPLOY.md`
一個人不夠」）：一個**真的穿過 `location /api/` 且會查 Postgres** 的探測。

**受測對象**：`POST /api/auth/login`，送一組**刻意錯誤**的憑證，預期 **401**。

**本節不給可執行的 shell，只給實作必須滿足的契約**（這是本輪的一項刻意改變，理由見下方
「為何這裡不寫 shell」）。

#### 探測的實作契約（`PROBE-CONTRACT`，七條）

| # | 契約 | 為什麼（若違反會怎樣） |
|---|---|---|
| **P-1** | 請求必須命中 `location /api/`（`frontend/nginx.conf:16`），不得打 `/` | `/` 由 `:35–37` 的 `try_files` 回靜態檔，不經 `backend`、不碰 `db`——那正是既有兩道檢查的盲點 |
| **P-2** | 受測端點的處理必須**在任何憑證比對之前查資料庫**；目前滿足此性質的是 `POST /api/auth/login`（`backend/services/user_router.py:386` 的 `db.query(...)` 在 `:389` 的 `verify_password` 之前） | 若換成不查 DB 的端點，探測只證明 `frontend`→`backend`，`backend`→`db` 仍無覆蓋 |
| **P-3** | 通過條件是 **HTTP 401**；使用者名稱必須是一個**不存在**的固定值 | 存在的帳號會走到密碼比對，且可能留下稽核列。不存在者在 `:387–388` 直接 401，**不產生任何狀態、不需要任何 secret** |
| **P-4** | 每次請求必須有**連線逾時與總逾時上限** | Docker 跨網段隔離是 **DROP 而非 reject**，故網段打錯時連線是掛住而非被拒；無上限時會撞上 `frontend/nginx.conf:30` 的 `proxy_read_timeout 600s`，單次請求就耗十分鐘 |
| **P-5** | 必須有**有界重試**，且**不得因單次請求的連線層失敗而中止整個步驟** | 見下方「有界重試與 `set -e`」——這一條是本 repo 的 shell 慣例造成的硬要求，不是風格偏好 |
| **P-6** | 結果的表達方式**必須沿用該 job 既有的機制**：`deploy` job 以**步驟結束碼**（失敗即紅燈），`rollback` job 以 **`$GITHUB_OUTPUT` 的 `restored`**（該步驟今天不因健康檢查紅燈） | 見下方「`rollback` 那一半的形狀」 |
| **P-7** | 若為 `rollback` 引入新的狀態值，**同一個 PR 必須補上 `deploy.yml:381–386` 的 `case` 分支** | 該 `case` 只認 `healthy`／`unhealthy`／`none`，其餘落到 wildcard 印「回滾: 結果未知」——探測的結論會就此遺失 |

#### 為何這裡不寫 shell（本輪的刻意改變）

stage 檔明文要求設計階段的產出是架構模式與決策、**不是可實作的程式碼**，片段限 15 行內
示意。前一版寫了兩段具體 shell，而**它們立刻成為缺陷的來源**：未收據驗證的五項發現有三項
（R-24／R-25／R-28）出在那幾行上，而那些行在 `code-generation` 之前不會被執行、不會被
測試。**把 shell 抽掉、改以契約表述，消掉的是整類缺陷，不是四個實例。** shell 的正確落點
是 `code-generation`，那裡它會真的跑。

**唯一保留的實作級細節是那些「不寫就一定會踩」的**——下面兩小節即是。它們不是示範寫法，
是對 shell 行為的事實陳述。

#### 為何 `DEPLOY.md` 一個人不夠（審查 R-16，`[G6]`=A）

**R-01 要防的失敗是無人值守的，而 `DEPLOY.md` 只在人手動升版時被讀。** `deploy.yml` 的
觸發逐字是 `pull_request: types: [closed] / branches: - ut`（`:10–14`）——**D-3 這次網段
變更本身就是經由一次普通合併自動部署的**，與 PG 16→18 的手動升版程序是兩條不同路徑。
若探測只寫進 `DEPLOY.md`，則照本設計實作之後 `deploy.yml` 對 `/api` 的命中數**仍然是
0**，而引入分段的那一次部署仍會綠燈通過——R-01 的盲點原樣留著。

**所以探測有三個落點，缺一不可**：

| 落點 | 承載什麼 | 為什麼需要它 |
|---|---|---|
| `deploy.yml` 的**獨立新步驟**（在 `Wait for the frontend to answer locally` 步驟**之後**，**不是**加進該步驟的迴圈內） | 每一次**自動**部署都跑，含引入分段的那一次 | 這是唯一真的關上 R-01 的做法 |
| `deploy.yml` 的 **`rollback` job 健康檢查迴圈**（`:229–236`，`[G7]`=A 定案；**形狀見下方專節，與 `deploy` job 不同**） | 回滾後的資料面連通性 | 該迴圈目前只 `curl -fsS -o /dev/null http://127.0.0.1:8090/`，所以「rolled back and healthy on 8090」這句話在資料面上未被驗證——而本節開頭正是拿這句話當 R-01 的證據。只修 deploy job 等於自己指出問題卻只修一半；且 rollback **是探測失敗後的必經路徑**，那時最需要知道資料面真的回來了 |
| `DEPLOY.md` 的**升版步驟** | 手動升版路徑（PG 16→18 的七步程序）中，`up db` 之後的驗證 | 手動路徑不經 `deploy.yml`，且升版時 backend 是被停掉的，時序與自動部署不同 |

#### ⚠ 探測必須有有界重試，否則它會把好的部署判成壞的（審查 R-18，Major）

**這是本輪唯一的真設計問題，而它是初版造成的。** 把單發斷言接在 8090 檢查之後不可行，
因為那個檢查**不證明 backend 已就緒**：

| 環節 | 逐字事實 | 後果 |
|---|---|---|
| `deploy/docker-compose.deploy.yml:77–78` | `depends_on:` ／ `- backend`——**沒有 `condition:`** | 只保證啟動順序，不是就緒條件。nginx 可在 backend 尚未監聽時就服務 |
| `.github/workflows/deploy.yml:112–125` | 30 × 5s 迴圈 `curl -fsS -o /dev/null http://127.0.0.1:8090/`，**第一次成功即 `exit 0`**（`:118`） | 打的是 `/`，由 `try_files` 回靜態檔。**完全不等 backend** |
| `backend/main.py:46–50` | `@app.on_event("startup")` **同步**呼叫 `init_db()` | 這段完成前 uvicorn 不服務，`/api/*` 一律 **502** |
| `backend/database.py:74–83` | `Base.metadata.create_all()` ＋ **六個** `_ensure_*_schema` DDL 補丁 | 502 窗口的長度來源，且會隨補丁增加而變長 |

所以單發探測會落在一個**真實的 502 窗口**內。誤判的後果不只是紅燈：`deploy.yml:169–175`
的 `rollback` job 觸發條件含 `failure() && needs.deploy.result == 'failure'`，它會還原
last-good、**對一個其實沒問題的合併開 revert PR**、並 dispatch Deploy Doctor。

**另外，落點的寫法本身也錯過一次**：初版寫「接在現有 8090 健康檢查之後，即 `:116` 那一段
之下」，而 `:116` 在迴圈內、`:118` 就 `exit 0`——照字面加在那裡是**永不執行的死碼**，正是
`project.md` 已記載的「不可達規則」形狀。上表已改為「獨立新步驟」。

#### 有界重試與 `set -e`（P-5 的由來，這一條不寫就一定會踩）

**`deploy.yml` 的三個同類步驟（`:114`、`:129`、`:208`）逐字都以 `set -euo pipefail`
開頭**，而在那之下：

- **把 `curl` 的輸出賦值給變數會讓整個步驟中止。** `code=$(curl …)` 的結束狀態就是命令
  替換的結束狀態，所以 `curl` 因逾時（28）或連線被拒（7）回非零時，`set -e` **立即終止
  步驟**——不重試、不印任何診斷、步驟結束碼是 `28`／`7` 而非 1。
- **既有兩道檢查沒有這個問題，是因為它們把 `curl` 放在 `if curl …; then` 的條件位置**
  （`:116`、`:130`），那個位置被 `set -e` 豁免。

**實測複驗**（本站以等價腳本實跑）：賦值形在第一次 `curl` 失敗即結束、`exit=7`，連一次
迭代訊息都沒印；條件位置形安然跑完全部迭代、`exit=0`。**所以「與既有兩道檢查同形」這句話
只在「有界重試」這一點成立，在「怎麼取值」這一點不成立**——初版寫成同形是錯的（審查 R-24）。

**契約層的要求（P-5）**：取值必須以不觸發 `set -e` 的形式進行（條件位置判定，或顯式
容錯取值），**不得讓單次請求的連線層失敗終止步驟**。具體寫法留 `code-generation`。

#### 重試窗口的長度與它的牆鐘上界

窗口存在的理由是**區分「backend 還在跑 `init_db()`」與「資料面真的斷掉」**——不是防禦性
冗餘，所以不能為了讓部署快一點而調短。

| | 值 | 依據 |
|---|---|---|
| 重試次數 × 間隔 | **30 次 × 5 秒** | 與既有兩道檢查同形（`deploy.yml:115`／`:130` 的 `seq 1 30` ＋ `sleep 5`） |
| 每次請求的逾時上限 | 連線與總時長各一（P-4） | 見上一節 |
| **牆鐘上界** | **≈ 10 分鐘**（30 ×（請求逾時 ＋ 間隔）） | **審查 R-25 更正**：初版只寫「30 × 5s」，把每次請求的逾時忘在預算外。成功路徑通常數秒內結束；**10 分鐘是「真斷線時紅燈延遲」的上界** |
| 與 job 逾時的關係 | `deploy` job `timeout-minutes: 30`（`:28`）、`rollback` job **`20`**（`:177`） | `rollback` job 內還有 `up -d`＋8090 迴圈（≤150s）＋tunnel 迴圈（≤120s）。10 分鐘的探測放進 20 分鐘的 job **可行但餘裕不大**，實作時須實測並在 `DEPLOY.md` 記錄實際耗時 |

**`init_db()` 的最壞時間評估**（未收據驗證的獨立分析，本站採納）：六個 `_ensure_*_schema`
全是 `IF NOT EXISTS` 的 ALTER／CREATE ＋ 四組 RENAME ＋ 一條小表 UPDATE，屬目錄層級操作、
毫秒級；唯一有成本的是**首次開機**的 bcrypt 雜湊與 RBAC seed（數秒）。且
`depends_on: db / condition: service_healthy`（`docker-compose.deploy.yml:63–65`）保證
backend 不先於 `pg_isready` 啟動。**結論：30 × 5s 對目前的 `init_db()` 足夠且寬裕。**

**窗口重評的承載者（審查 R-26）**：「每新增一個 `_ensure_*_schema` 補丁就要重評窗口」
不是一條沒有承載者的宣稱——`local-dev-drift` agentic workflow 的觸發路徑**已含
`backend/database.py`**，且 `project.md ## Mandated` 對該檔的 schema 補丁已有 blocking
同步條款。本條掛在那條既有路徑上（**提醒性質、非阻擋**），如實記載其強度。

#### `rollback` 那一半的形狀——**不可原樣搬 `deploy` job 的寫法**（P-6／P-7，審查 R-28）

`[G7]`=A 只定了「加進 `:229–236` 的健康檢查迴圈」，但**沒有定形狀，而那是一個實作者必然
要猜的空白，且四種猜法的可觀察後果各不相同**。本節把它補上。

`rollback` 的既有結構與 `deploy` job **不同類**：

| | `deploy` job（`:112–125`） | `rollback` job（`:208–237`） |
|---|---|---|
| 結果如何表達 | **步驟結束碼**：成功 `exit 0`、逾時 `exit 1` → job 紅燈 | **`$GITHUB_OUTPUT`**：`RESTORED=unhealthy` → 成功則 `RESTORED=healthy; break` → **迴圈之後**在 `:237` 寫 `echo "restored=${RESTORED}" >> "$GITHUB_OUTPUT"` |
| 健康檢查失敗會紅燈嗎 | 會 | **不會**——它把結果放在 output 裡，不放在結束碼裡 |
| 下游消費者 | job 結果本身 | `notify` 的 `case "${RESTORED}"`（`:381–386`），**只認 `healthy`／`unhealthy`／`none`**，其餘落 wildcard 印「回滾: 結果未知」 |

**所以照 `deploy` 的寫法搬過去會壞掉兩件事**：(1) 在 `set -e` 下第一次連線層失敗即中止
步驟 → `:237` **永遠不執行** → `restored` 為空 → Slack 印「回滾: 結果未知」，**探測的真實
結論就此遺失**；(2) 即使加了容錯取值，用 `exit 1` 表達失敗仍會讓該步驟提前結束、同樣跳過
`:237`。

**本站定案（採 (a)，並寫明為何不採 (b)）**：

- **(a) 併入既有迴圈的成功條件**：`/` 與 `/api/auth/login` **兩者皆通**才
  `RESTORED=healthy; break`；**不使用 `exit`**；`:237` 照舊是唯一的寫入點；`notify` 的
  `case` **不需改動**。代價是 granularity 較粗——資料面壞掉時報的是既有的
  「回滾: 已嘗試還原，但服務仍未恢復」，看不出壞在資料面還是前端。
- **(b) 新增第三種狀態**（如 `unhealthy-dataplane`）：granularity 較好，但依 **P-7** 同一個
  PR 必須補 `:381–386` 的 `case` 分支，否則反而退化成「結果未知」——比 (a) 更糟。

**選 (a) 的理由**：`rollback` 走到這裡時，站台已經在回滾後的 last-good 設定上，**當下最需要
的資訊是「恢復了沒有」這個二元答案**，不是壞在哪一層（那由該步驟已有的 `docker compose
logs` 與 Deploy Doctor 承擔）。且 (a) 不動既有輸出契約，是兩者中唯一不會因為漏改一處而
靜默退化的。

**`deploy` 那一半：失敗時讓 job 紅燈。** 不採「只記 warning」——本 repo 已有實證的對照：
`ui-regression` 是真閘門因為它 `exit 1`，而 `local-dev-drift` 只提問所以沒有強制力。
一個不擋的探測實質上等於沒有探測。

**⚠ 這一項擴大了本單元的範圍。** 見 `§〇`。

**為什麼這個探測是對的**（三段路徑各自被證明，且結果二元可判）：

1. 路徑 `/api/auth/login` 命中 `frontend/nginx.conf:16` 的 `location /api/` →
   `proxy_pass http://backend:8000`。**證明 `frontend`→`backend` 通。**
2. `backend/services/user_router.py:386` 的
   `db.query(User).filter(User.username == request.username.lower()).first()`
   **在任何密碼比對之前執行**。**證明 `backend`→`db` 通。**
3. 該使用者不存在 → 同檔 `:387–388` raise 401（`detail: "帳號或密碼錯誤"`）。
   **`401` 是「兩段都通」的唯一結果。** 失敗分類經兩輪更正（R-17 先指出初版把
   `502`／`504` 一律歸因為「`backend` 不可達」會指錯方向；**R-27 再指出我的第一次更正把
   `backend`→`db` 與 `backend`→`redis`／`ollama` 混為 504**，而兩者在外部是不同的代碼——
   前者在 startup 路徑上、表現為持續 502，後者不在、表現為 500／504／逾時）：

   | 回應 | 診斷 |
   |---|---|
   | `401` | 兩段都通 |
   | **`502`（持續整個重試窗口）** | **最可能是 `backend`→`db` 斷掉**。`backend/database.py:76` 的 `Base.metadata.create_all()` 與 `:78–83` 的六個補丁**全在 `:86` 的 `try:` 之外**，故 db 不可達時例外會往上拋 → `backend/main.py:46–50` 的 startup 失敗 → uvicorn 不進入服務狀態 → `restart: unless-stopped`（`docker-compose.deploy.yml:34`）反覆重啟 → nginx 始終取不到上游。**次要可能**：`backend` 映像本身起不來 |
   | **`500`、`504`，或 `curl` 逾時（`000`）** | **`backend`→`redis`／`ollama` 斷掉**——這兩段**不在** startup 路徑上，所以 backend 會正常服務、在請求處理中才失敗或掛住。DROP 型隔離的表現是掛住後逾時，與行程內例外的 500 在外部無法區分，故同一類 |
   | `200` 且回 HTML | `/api/` 路由或 `frontend`→`backend` 斷（落到 `try_files`） |

   **這張表的用途是診斷指向，不是通過條件**——通過條件只有一個：`401`。上表的價值在於
   **502 與 504 指向不同的網段歸屬錯誤**，而初版把 502 一律歸因為「`backend` 容器不可達
   或未監聽」，會讓人去查容器而不是查 `networks:`。

**它不產生任何狀態**：使用者不存在，在任何寫入之前就 401 返回，不留稽核列、不建帳號。
**它不需要憑證**，所以可以放進 workflow 而不新增任何 secret。

**這條沒有機械閘門**：`scripts/validate_env_contract.py` 只解析環境變數，對 compose 的
`networks:`／`ports:`／`volumes:` 宣告完全無感。`NFR8.7`／`NFR8.8` 的「暴露面為零」與本
項的分段都只能靠 code review。已列入 `§四`。

### D-4 — 升版 dump 檔的三條硬要求

**問題**：`NFR6.3(a)` 收斂為只走 dump/restore，而 dump 是**全庫明文**——`users` 全表含
`password_hash`、全部 RBAC 權限矩陣、三種記憶的全部內容。`NFR6.3(c)` 的七步程序對它的
**權限、存放位置、刪除時機一條都沒有**。

且本 repo 的兩道掃描對它**結構上無效**：

- `scripts/validate_repo_contract.py` 的 `validate_no_obvious_secrets()` 只讀
  `contract_files()`（repo 層必要檔 ＋ baseline record 必要檔 ＋ audit shard）。工作區
  裡的任意 `.sql` 不在其中（`team.md` `## Deployment` 已逐字記載此落差）。
- `validate_no_production_config_added()` 做 path-part 精確比對 `prod`／`production`／
  `secrets`；`cloud360-dump-20260927.sql` 三者皆不命中。

所以一份放在 repo 工作區的 dump 檔，`git add -A` 會把它撈進去，**兩道檢查都不會響**，
而本 repo 是 public。

**設計（三條，缺一不可，寫進 `DEPLOY.md` 的升版章節）**：

| # | 要求 | 具體做法 | 通過條件 |
|---|---|---|---|
| 1 | 建立時即 owner-only | `umask 077` 後才執行 `pg_dump`（不是事後 `chmod`——事後改之前存在一個 world-readable 的時間窗） | `stat -c '%a %U' <dump>` 回 `600` ＋ 執行者帳號 |
| 2 | 只准放 `$HOME` 下的專用目錄 | 例如 `$HOME/cloud360-upgrade/`，該目錄本身 `700`。**不得放在 repo 工作區或其任何子目錄** | `realpath <dump>` 的前綴為該目錄；且 `git -C <repo> status --porcelain` 在 dump 存在期間**不出現任何 `.sql`** |
| 3 | 驗證通過後立即刪除，並記錄該動作 | 七步程序的最後一步刪除 dump，`DEPLOY.md` 要求在升版紀錄寫下刪除時間 | 該目錄下無殘留 `.sql`；升版紀錄有刪除時間 |

**既有先例，所以第 1 條不是新發明**：`deploy/docker-compose.deploy.yml:83–87` 逐字記載
cloudflared 憑證檔「on the host is 0400, owned by uid 1000」，並說明刻意不放寬為
world-read。以檔案權限保護敏感檔在本 repo 已是既有實務。

**與 D-1 的關係**：`[G5]`=A（全碟加密）使 dump 檔在**離線**面被涵蓋（它在 `$HOME`
下，而系統碟加密）。D-4 管的是**線上**面——主機執行中時誰讀得到它、它會不會被誤推進
版控。兩者不可互相替代。

**為何不加密 dump 檔本身**（`[G4]` 選項 C 未採）：多一個金鑰要管，而升版窗口正是最
不該增加失敗模式的時候；`NFR6.3(b)` 的回退路徑就是那份 dump，金鑰遺失等於備份等於
沒有。

---

## 二、ADR-0006 四面向在本單元的處置

`project.md` 要求「對每一項變更檢查 ADR-0006 的四個面向」，且「不得僅以『已有
ADR-0006』帶過」。逐項判定，**不適用者附理由、不留空白**：

| 面向 | 本單元的處置 | 判定 |
|---|---|---|
| **IAM** | 見下方「IAM 的誠實現況」 | **部分處置**（不是 compliant，也不是 N/A） |
| **Encryption** | at rest → D-1（主機層全碟）；in transit → D-2（明文，附前提與代價）；dump 檔 → D-4 | **已處置** |
| **Network exposure** | D-3（`networks:` 分段）＋ 既有的 `NFR8.7`／`NFR8.8`（無 host port） | **已處置** |
| **Audit logging** | 見下方「Audit 的缺口與承接單元」 | **部分處置** |

### ADR-0006 的另一項：property-based testing hard constraint

ADR-0006 逐字點名 **IaC generator**、**cost calculator**、**agent routing** 三個模組須有
property-based 測試。**對 `brain-infra` 判定為 N/A，理由是這個單元沒有任何計算核心**：
它交付三份 compose 的宣告、`render-env.sh` 的變數寫入、`DEPLOY.md` 與 `LOCAL-DEV.md` 的
文件同步，沒有一行純函式可被 property 約束。

**N/A 不等於這個 intent 豁免**：`contract-summary.md` 的 PBT 段已把落點釘在 `K-10`
（`IntentRouter` 的**門檻比較純函式**，對應 ADR-0006 的 agent routing）與 `K-06`
（`EmbeddingPort` 的 `verification` 含 property-based）。兩者皆屬 `U11`／`U6`，不在本
單元。且該段逐字警告 `K-10` 的 property 建立在 `OQ-10` 未定案的前提上——若結論為「無
可用信心訊號」，該純函式的輸入型態會變、property 須重寫。**本站不碰 `OQ-10`。**

（這一項寫在這裡是因為 `project.md` 的自檢第七項要求「逐項對照 ADR-0006 四面向 ＋ PBT
hard constraint」，而該規則本身的由來是我在 `units-generation` 明知規則存在卻仍讓
`ADR-0006` 零命中。）

### IAM 的誠實現況

- **Redis**：`NFR4.1` 已要求 ACL 專用使用者、值不得為 `default`。確切的指令集與 key
  pattern 由 `U10 session-store` 決定（`nfr-requirements` `§五` 明文轉交）。本站不重
  決定。
- **Ollama**：零認證，且 `NFR8.8`／`NFR8.9` 已把它記為**已接受的代價**。D-3 把可達者
  由 5 個容器縮到 3 個（不是 1 個——`internal` 內部不隔離，見 D-3 的 blast radius 表），
  但那是網段控制、**不是身分控制**——`backend`（以及同網段的 `db`／`redis`）對 Ollama 仍是
  無限制存取。如實記載，不寫成已處置。
- **契約層已明文界定過這件事，本站沿用而非重新推導**：`contract-summary.md` 的 `K-01`
  `behaviour_semantics.authorization_responsibility` 逐字為「**無**——環境變數不含授權
  判定。Redis／Ollama 的憑證是**連線憑證，不是使用者授權**」。所以 `NFR4.1` 的 Redis
  ACL 與 D-3 的網段分段都不是 IAM 意義上的授權控制；本 intent 的**使用者授權**落在
  `K-07`（`HierarchyFacade` 為受保護操作的唯一授權入口）與 `K-08`（擁有者 ＋ 可見範圍
  的第二套模型），兩者皆屬 service 單元、**不在本單元**。契約層並記載那兩者的「facade
  是唯一入口」**無機械強制、靠 code review**——本站不改變該現況，只在此指出本單元的
  任何措施都不補那個缺口。
- **PostgreSQL**：**至今以單一 superuser（`POSTGRES_USER`）連線，沒有任何最小權限
  拆分**。`deploy/docker-compose.deploy.yml:36` 的 `DATABASE_URL` 與 `:16` 的
  `POSTGRES_USER` 是同一個帳號，該帳號即 initdb 建立的 superuser。這是**既有基線，
  不是本單元引入**，但它落在 ADR-0006 的 IAM 面向上，所以必須在此記載而不是略過。
  縮窄它（為應用建立非 superuser 角色、只授與必要表的權限）**不在本單元範圍**：它會
  改變 `schema_rbac.sql` 的擁有者語意與 `_ensure_*_schema` 的 DDL 權限需求，屬
  `U5 memory-data` 或一個獨立的安全強化 intent。**本站的交付是把它標出來，不是修它。**

### Audit 的缺口與承接單元

- **已處置**：`NFR8.9` 覆蓋兩個新容器的記錄承載（docker `json-file` ＋
  `max-size`／`max-file`，具體值由部署者定並記入 `DEPLOY.md`）。
- **缺口**：**correlation ID 的傳遞在本單元沒有任何落點**。stage 檔的 observability
  focus 列了它，但 `observability-design` 的 `produces_kinds` 不含 `packaging`，所以本
  站沒有承載它的產出檔。
- **承接單元**：`U13 brain-gateway`（請求入口，correlation ID 的產生點）與
  `U12 work-orchestrator`（跨 agent 呼叫的傳遞點）的 `nfr-design` 迭代。
- **必須注意的風險**：`nfr-design` 是 `CONDITIONAL` 且 `for_each: unit-of-work`，其
  `condition` 為連言（`NFR Requirements was executed` **and** `NFR patterns need
  design`）。`brain-infra` 跑過本站**完全不保證** `U12`／`U13` 會跑。依 `project.md`
  既有規則：**屆時判定 skip 的執行者須重新提交使用者裁決，不得由實作者當場決定。**

---

## 三、本設計引入的一項新張力：全碟加密 vs 斷電自動回復

**這不是選項的附帶說明，是一個必須被下游處理的真實衝突。**

- `deploy/docker-compose.deploy.yml:34` 等處的 `restart: unless-stopped`，以及
  `.github/workflows/deploy.yml` 的自癒設計（自架 runner ＋ `~/.cloud360/last-good-sha`
  回滾），**都預設主機在斷電或重開之後會自己回到可服務狀態**。
- 全碟加密使開機需要解鎖。以 passphrase 承載 → **斷電後主機不會自己回來**，需要人到
  現場或有帶外管理；以 TPM 承載 → 可自動解鎖，但保護強度降為「磁碟離開這台機器才
  有效」（磁碟遭竊仍有效，整機被搬走則無效）。
- **本站不替使用者選這兩者之一**：它是主機層的運維決策，且兩者的威脅模型不同。
  **本站的交付是要求 `DEPLOY.md` 明寫採用哪一種、以及該選擇對自動回復的後果**，並在
  升版章節提醒：升版窗口內若主機重開，解鎖是第一步、且它早於任何 compose 動作。

---

## 四、本設計中沒有機械閘門的項目（誠實記載）

下列全部只能靠 code review 或運維紀律，**沒有任何 CI 檢查會發現違反**。

**一項本輪由無閘門變成有閘門**（審查 R-16 ＋ R-22）：`backend`→`db`／`redis`／`ollama` 的
實際連通性，現由 `deploy.yml` 的探測（`S-6`）在**每一次自動部署**與**每一次回滾之後**都
把關，失敗讓 job 紅燈。它原本屬於下列清單——初版把探測只放進 `DEPLOY.md`，而那份文件只在
人手動升版時被讀，於是引入分段的那一次自動部署仍無閘門；第二版只加進 `deploy` job，於是
回滾後那句「rolled back and healthy on 8090」在資料面上仍未被驗證。

剩下真的沒有閘門的：

1. **`networks:` 分段本身**（D-3）——`validate_env_contract.py` 只解析環境變數，不解析
   compose 的 `networks:` 宣告。新增服務時若忘記指定網段，它會落到 compose 的預設
   行為而非 `internal`，且無人會被通知。
2. **服務的網段歸屬正確性**（D-3）——即使 `networks:` 存在，把 `cloudflared` 誤加進
   `internal` 不會被任何檢查擋下，而那一個字就讓 D-3 的全部價值歸零。
3. **全碟加密的存在**（D-1）——純部署環境前置條件，CI 在 GitHub runner 上跑，對
   `192.168.10.10` 的磁碟一無所知。
4. **dump 檔的三條要求**（D-4）——純程序。且如上所述，本 repo 的 secret 掃描器結構上
   看不到工作區裡的 `.sql`，禁止路徑檢查也擋不到它的檔名。
5. **`DEPLOY.md` 是否真的寫了全碟解鎖方式**（`§三`）——文件內容無 contract 檢查。

**補閘門的具體做法（不列為本單元交付，供後續 intent 參考）**：把
`validate_env_contract.py` 擴充為解析 **deploy 與 CI test 兩份** compose 的
`networks:`／`ports:`／`volumes:` 宣告（**repo 根那份必須排除**——它刻意 publish `5432`
與 `8080`，把它納入會讓 (c) 永遠紅燈），並斷言 (a) 每個服務都顯式指定網段、
(b) `cloudflared` 與 `frontend` 不在 `internal`、(c) 資料面三個服務沒有 `ports:`。
這一支 validator 已在 CI 的 `repo-contract` job 內執行，擴充它不需新增 job；且它已有
`DEPLOY_COMPOSE` 這個單一路徑常數（`validate_env_contract.py:40`），擴充時要把它改成
一組路徑而非沿用單一值。

---

## 五、`produces_kinds` 缺席的五項對下游的意義

本站對本單元**沒有**產出下列五份檔，這是 kind 判定的結果而非漏寫。但缺席不等於那些
主題不存在，所以逐項寫明它們的實際承接點：

| 缺席的產出 | 該主題在本單元是否真的不存在 | 承接點 |
|---|---|---|
| `performance-design` | **不是**——Redis 往返、Ollama embedding 延遲都是真的效能面 | `NFR3` 已在 `nfr-requirements` 判定「Redis 往返約 1ms 可忽略」；`NFR4.2` 已約束 `appendfsync` 選值不得使 `NFR3` 的 P50 預算失守。實際設計屬 `U10`／`U6` |
| `scalability-design` | 是——單主機、單副本，無水平擴展設計可言 | 若未來離開單主機，需新 intent |
| `reliability-design` | **部分不是**——`NFR6.3(b)` 的三條排序不變量與窗口內 rollback 失效就是可靠性設計，只是它寫在需求層 | 已由 `NFR6.3(b)` 承載；容器層的 healthcheck／`depends_on` 為既有設計，本單元不改 |
| `observability-design` | **不是**——見 `§二` 的 correlation ID 缺口 | `U13`／`U12` 的 `nfr-design` 迭代（注意該站可能 skip） |
| `logical-components` | **部分不是**——D-3 的網段分段本身就是 failure domain 的劃分 | 本檔 D-3 的 blast radius 表即為其等價內容；`infrastructure-design` 會再收一次 |

---

## 六、與 `contract-summary.md` 的對應

本節存在的理由值得記下來：**`upstream-coverage` sensor 在本站第一次真的驗到東西。**
它在 `brain-infra` 的 `nfr-requirements` 連兩輪回 `reason: "no upstream"`、`consumes: []`
（什麼都沒檢查），本站則回 `unreferenced: ["contract-summary"]` 並判定 failed——而那是
真缺口：stage 檔 Step 1 明文要求讀 `contract-summary.md`（「the integration mechanism
and failure behaviour at each boundary drive the resilience and scalability patterns
designed here」），我第一版沒讀。讀進來之後它改掉了本檔三處敘述，不是補一句引用。

| 契約 | 對本設計的實際輸入 | 落點 |
|---|---|---|
| `K-01`（`U1` → `U5`／`U6`／`U10`，`env`） | `exposure` 的「compose 內部網路 only；不得 publish port」只管入向、不管橫向——與 `NFR8.8` 同一個措辭缺口 | D-3 |
| `K-01` `observable_side_effects` | `render-env.sh` **覆寫** `deploy/.env`、部署後清理該檔——使 D-1 的涵蓋範圍表由「長期躺在磁碟上」更正為「窗口有界，但 runner 就是這台主機，且部署失敗時會留存」 | D-1 |
| `K-01` `authorization_responsibility` | 逐字「**無**」：Redis／Ollama 憑證是連線憑證、不是使用者授權 | `§二` IAM |
| `K-05`（`U5` → `U8`／`U9`，`schema`） | 記憶列的靜態儲存加密即 `OQ-3`，契約層指派 `nfr-design` 且明寫「本站不預選手段」 | D-1，見下方「`OQ-3` 在本站收斂」 |
| `K-12`（`U13` → 瀏覽器，`ws`） | 對外為 **`wss`**、token 走標頭不走 query string；且契約層逐字寫它是本 intent **唯一**新增的對外網路面 | D-2 的範圍限定表 |
| `X-03`（`U11` → OpenRouter） | 對外呼叫面存在且 `base_url` 受一致性斷言鎖定 | D-2 的範圍限定表；並支撐 D-3「不得設 `internal: true`」的理由（`backend` 需要出向） |

### `OQ-3` 在本站收斂，而不是下推——這移除了契約層記載的一條風險

`contract-summary.md` 的 ADR-0006 判定表 Encryption 列逐字寫：`K-05` 的記憶列靜態儲存
加密要求為 `OQ-3`，「指派 `nfr-design`（CONDITIONAL，其條件依賴 `nfr-requirements` 是否
執行——與 `OQ-4`／`OQ-10` **同一條風險鏈**）」。而 `brain-infra` 的 `NFR7.1` 把落點寫成
`U5`／`U8` 的 `nfr-design` 迭代，並警告那兩站不保證會跑。

**`OQ-3` 有兩個半邊，本站兩個都答了——這一點必須寫全**（審查 R-12）。
`contract-summary.md:1424` 逐字把 `OQ-3` 定義為「episodic memory 的加密手段（**靜態與
傳輸**）」：

| `OQ-3` 的半邊 | 本站的答案 | 落點 |
|---|---|---|
| **靜態** | 主機層全碟加密涵蓋承載記憶列的資料庫 volume，即 `K-05` 的全部資料範圍 | D-1 |
| **傳輸** | **容器間明文，已接受**（前提：全部容器同主機、無跨主機流量；代價：信任邊界含同網段容器**與 host-local 行程**） | D-2，見其「明文接受的代價」段 |

所以 `OQ-3` 不再依賴 `U5`／`U8` 的 `nfr-design` 是否執行——**那條風險鏈上的 `OQ-3` 這一
環斷開了，兩個半邊都斷開**。初版只寫了靜態那一半，會讓 `U5`／`U8` 的讀者以為傳輸面另有
設計待補。

**但兩件事不因此成立，必須分清**：

1. **`OQ-4` 與 `OQ-10` 仍在那條風險鏈上**，落點是 `U11 intent-router` 的迭代。本站沒有
   碰它們。
2. **`OQ-3` 的收斂是「以主機層手段回答」，不是「以 `K-05` 原本設想的欄位級加密回答」。**
   若後續有人要求「即使主機在執行中、即使容器被攻陷，記憶列仍不可讀」，那個需求
   **D-1 不滿足**（見 D-1 的邊界說明），需要新的決定——而 `[G1]` 的選項 B／C 正是那條
   路，使用者在知情下選了 A。

---

## Assumptions & Open Questions

- **全碟加密的實際落地方式（passphrase vs TPM）未定**，本站刻意不選（見 `§三`）。
  `DEPLOY.md` 必須寫明採用哪一種與其對自動回復的後果 [assumption]
- **`192.168.10.10` 目前沒有任何被記載的磁碟加密**（`LUKS`／`encrypt` 在 `deploy/`、
  `DEPLOY.md`、`LOCAL-DEV.md` 全無命中），所以 D-1 是**新增的運維工作**，且對既有主機
  是一次重裝或資料遷移。本站未實地確認該主機的分割配置是否允許就地遷移 [assumption]
- **D-3 的網段名稱（`edge`／`internal`）為本站提議**，名稱本身可由實作調整；但
  「不得設 `internal: true`」與各服務的網段歸屬是本站的定案，不是建議（見 D-3）
- **PostgreSQL 單一 superuser 的縮窄不在本單元範圍**，已在 `§二` 標明理由與可能的承接
  單元，但**尚未有任何單元正式承接它** [assumption]
- **`U12`／`U13` 的 `nfr-design` 是否會執行未定**，而 correlation ID 的承接點在那裡。
  屆時判定 skip 的執行者須重新提交使用者裁決 [assumption]
