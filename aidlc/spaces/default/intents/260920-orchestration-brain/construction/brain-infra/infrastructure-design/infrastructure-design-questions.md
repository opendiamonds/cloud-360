# Infrastructure Design 問題 — `brain-infra`（U1）

## 這一輪問五題，以及為什麼

`brain-infra` 是 `kind: packaging`，本站的 `produces_kinds` 對它**四項全適用**
（`infrastructure-specification`、`monitoring-design`、`cicd-pipeline`、`traceability`）
——與前兩站不同，這裡沒有 kind-vacuous 的缺席。

上游已鎖掉大量事情，本站**不重問**：

| 已定案、本站不重問 | 落點 |
|---|---|
| 部署模型為單主機 docker compose、deploy-on-merge 至 `192.168.10.10` | ADR-0007／ADR-0008 |
| PG 18 ＋ pgvector 五個映像落點、升版只走 dump/restore 的七步程序 | `NFR6.1`／`NFR6.3` |
| Redis 具名 volume ＋ AOF（僅 deploy stack）、ACL 專用使用者 | `NFR4.1`／`NFR4.2` |
| session 存活期：單一 key ＋ TTL **24 小時**、每次互動續期 | domain-design ADR-005 |
| Redis／Ollama 對外暴露面為零（無 host port） | `NFR8.7`／`NFR8.8` |
| compose `networks:` 分段（`edge`／`internal`），不得設 `internal: true` | nfr-design D-3 |
| 靜態加密由主機層全碟加密承載 ＋ 四個掛載點檢查 | nfr-design D-1 |
| 容器間傳輸維持明文，信任邊界含 host-local 行程 | nfr-design D-2 |
| 部署後探測（`PROBE-CONTRACT` 七條）的三個落點與形狀 | nfr-design D-3 |
| 七個環境變數由 `render-env.sh` 寫入、九處同步點 | `NFR8.1`／`NFR8.1a`／`NFR8.1b` |
| 兩個新容器必須指定 `max-size`／`max-file`，**具體值由部署者定** | `NFR8.9` |

也不重問已明文轉交的：`appendfsync` 具體值（`U10`）、Redis ACL 的確切指令與 key
pattern（`U10`）、ACL 採 `command:` 覆寫還是掛載檔（`U10`）、真實 PostgreSQL 的 CI job
（`U5`，`NFR6.1` 落點 3 的上游逐字衝突）、correlation ID（`U12`／`U13`）。

剩下五題是**本單元交付面上、上游沒有任何一條碰到**的基礎設施決定。

---

## 出題前的唯讀查證（**非來源登錄**，供題幹與選項引用）

- **V1 — 三份 compose 完全沒有資源限制。** `grep -n 'deploy:\|resources:\|limits:\|mem_limit\|cpus'`
  對 `deploy/docker-compose.deploy.yml`、`deploy/docker-compose.test.yml`、repo 根
  `docker-compose.yml` 三者**零命中**。所以「為容器設上限」在本 repo 是新模式。
- **V2 — 三份 compose 完全沒有 `logging:` 區塊。** 同樣零命中。故今日全部服務走 Docker
  預設的 `json-file` 且**無大小上限**，而 `NFR8.9` 要求兩個新容器必須指定
  `max-size`／`max-file`——那是**新增**的設定，不是既有慣例的延伸。
- **V3 — repo 內沒有任何監控堆疊。** `prometheus`／`grafana`／`datadog`／
  `opentelemetry`／`otel`／`sentry` 在 `deploy/`、`backend/`、`.github/` 的命中只有三處，
  且全部是**關鍵字清單**：`backend/services/wa_lens_engine.py:415–416` 與
  `wa_rule_engine.py:375` 用它們偵測「使用者提交的架構有沒有提到監控」。**不是實際堆疊。**
- **V4 — 今日的可觀測面只有兩樣**：`docker compose logs`（`deploy.yml` 在失敗路徑印
  `--tail=80`）與 `notify` job 的 Slack 通知（`:302`–`:410`，`SLACK_BOT_TOKEN` 未設時
  只印 warning 並跳過）。**沒有任何 metrics 收集、沒有告警規則、沒有 SLI／SLO。**
- **V5 — CI test stack 已有「刻意停用昂貴外部路徑」的先例。**
  `deploy/docker-compose.test.yml:35–37` 逐字：
  `# A1 generation is out of scope for these tests; leave the key empty so`
  `# the app boots but the LLM path stays untouched.` ＋ `OPENROUTER_API_KEY: ""`。
- **V6 — `EMBEDDING_PROVIDER` 的 enum 已含 `stub`。** `contract-summary.md` 的 `K-01`
  逐字 `allowed: [ollama, fastembed, fulltext, stub]`，且 `required: true`、無預設值
  （「偵測不到選定提供者時須大聲失敗」）。
- **V7 — Ollama 的資源數字未在主機上實測。** `bge-m3` 約 1.2GB、runtime 約 2GB 取自
  一般認知，`nfr-requirements` 的 Assumptions 已逐字記載「未在 `192.168.10.10` 實測」，
  且 `DEPLOY.md`／`LOCAL-DEV.md` 未記載該主機餘裕。`NFR9.1` 的退路依賴該實測。
- **V8 — Redis 的 TTL 是 24 小時、每次互動續期**（ADR-005）。所以 key 有自然到期路徑，
  但**沒有任何記憶體上限或淘汰策略的決定**。

---

## I1 — Redis 的記憶體上限與淘汰策略

`NFR4.2` 定了具名 volume ＋ AOF，ADR-005 定了 TTL 24 小時續期，但**沒有任何一條決定
`maxmemory` 與 `maxmemory-policy`**。這在單主機上是真實的失敗模式，而且兩種極端各有一個
無聲面：

- **不設 `maxmemory`**：Redis 一直長到主機 OOM。OOM killer 挑誰不可預測——可能是
  Postgres，那會連帶觸發 `restart: unless-stopped` 的重啟迴圈。
- **設了 `maxmemory` 但沿用預設的 `noeviction`**：滿了之後**寫入開始失敗**而讀取照常。
  後果是「新 session 建不起來、舊 session 照常運作」，而本 repo 沒有任何告警會說這件事。

- **A** — 設 `maxmemory` ＋ `allkeys-lru`，值寫進 `DEPLOY.md` 由部署者依主機餘裕定。
- **B** — 設 `maxmemory` ＋ 維持 `noeviction`，並要求 backend 在 Redis 寫入失敗時以
  明確錯誤回應使用者（不靜默降級）。
- **C** — 不設 `maxmemory`，依賴 ADR-005 的 24 小時 TTL 自然回收，並在 `§無閘門` 明記
  「無上限，主機 OOM 風險由部署者的容量規劃承擔」。
- **D** — 設 `maxmemory` ＋ `volatile-lru`（只淘汰有 TTL 的 key；本單元的 session key
  全部有 TTL，所以實際效果近似 `allkeys-lru`，但若未來有無 TTL 的 key 會退化成
  `noeviction`）。

  <!-- 審查 R-12：括號內的最後一句技術上不成立，就地更正、不改 [Answer]: A（依
  project.md 的「只修理由不改決定」形狀）。`volatile-lru` **不是**「有無 TTL 的 key
  就退化成 noeviction」——它只在**沒有任何可淘汰的 volatile key**時才以 OOM 錯誤回應
  寫入；存在部分無 TTL 的 key 只代表那些 key 不會被選中，策略本身照常運作。
  **決定本身仍正確，且理由比選項文字寫得更強**：依 domain-design/decisions.md 的
  ADR-005（`:209–211` 逐字「全部放在同一個 Redis key 之下，TTL 24 小時、每次互動
  續期」），今日所有 key 皆有 TTL，故 A ≡ D；而「每次互動續期」使 LRU 的最近度與
  session 活躍度相關，`allkeys-lru` 挑中的正是**最不活躍的 session**。 -->

[Answer]: A  <!-- answered 2026-09-27T04:12:55Z via picker -->

---

## I2 — Ollama 與其他容器的資源上限

參考 V1：三份 compose 目前**完全沒有資源限制**。參考 V7：Ollama 的 RAM 需求未在主機實測。
Ollama 是本單元新增的最大記憶體消費者，而它與 Postgres、backend 共用同一台主機。

- **A** — 只為 Ollama 設 `deploy.resources.limits`（記憶體），值寫進 `DEPLOY.md`；其餘服務
  維持無限制（沿用既有形狀）。
- **B** — 為 Ollama 與 Redis 兩個新服務都設上限，既有四個服務不動。
- **C** — 六個服務全部設上限（一次把這個模式建立起來）。
- **D** — 都不設，改為在 `DEPLOY.md` 要求部署前實測主機餘裕並記錄，不足時走 `NFR9.1`
  的退路（`EMBEDDING_PROVIDER` 換非 `ollama` 值）。

[Answer]: C  <!-- answered 2026-09-27T04:12:55Z via picker -->

---

## I3 — `monitoring-design.md` 的誠實範圍

參考 V3／V4：repo 內**沒有任何監控堆疊**，今日的可觀測面只有 `docker compose logs` 與
deploy workflow 的 Slack 通知。而 stage 檔要求 `monitoring-design.md` 產出 metrics／
alerts／SLI-SLO 三張表。`project.md` 另記載 observability 是 Operations 階段尚未落地的
真實待辦。

這一題決定本站是**引入監控**，還是**誠實記載沒有監控並指名承接站**。

- **A** — 不引入任何新堆疊。`monitoring-design.md` 如實記載現況（logs ＋ Slack），三張表
  以「本單元可觀測的項目」填寫（例如容器重啟次數可由 `docker ps` 觀察、但無自動告警），
  並明確指名 metrics／alerts／SLI-SLO 的承接站為 Operations 的 `observability-setup`，
  附「該站可能 skip」的風險。
- **B** — 引入最小 metrics 收集（例如在 compose 加 `prometheus` ＋ `node-exporter`），
  本單元交付。
- **C** — 不引入堆疊，但為兩個新容器加 compose `healthcheck:`（Redis 用 `redis-cli ping`、
  Ollama 用 `/api/tags`），使「容器活著但服務不通」至少在 `docker compose ps` 上可見。
- **D** — A ＋ C：不引入堆疊、但加 healthcheck，並指名承接站。

[Answer]: D  <!-- answered 2026-09-27T04:12:55Z via picker -->

---

## I4 — `logging:` 設定的適用範圍

參考 V2：三份 compose 目前都沒有 `logging:` 區塊，所以全部服務的 json-file **無大小
上限**。`NFR8.9` 只要求**兩個新容器**必須指定 `max-size`／`max-file`。

照字面只加新容器會產生一個奇怪的不對稱：新增的兩個有界、既有四個無界——而既有四個裡
包含 backend（本 repo 最多日誌的服務）。

- **A** — 加在全部服務上（deploy 與 CI test 兩份 compose），一次消除不對稱。
- **B** — 只加在兩個新容器上，嚴格照 `NFR8.9` 的字面，並在產出明記既有四個仍無界、
  屬既有狀態非本單元引入。
- **C** — 加在全部服務上，但只改 deploy stack；CI test stack 每次重建、日誌隨 stack 消失，
  故不需要。

[Answer]: A  <!-- answered 2026-09-27T04:12:55Z via picker -->

---

## I5 — CI test stack 是否需要 Ollama

`nfr-requirements` 的 Assumptions 把這一項留為待決（「取決於 `U5`／`U6` 的 CI 驗證形狀」），
而它落在本站的 `cicd-pipeline.md` 範圍內。

參考 V5：test stack **已有刻意停用昂貴外部路徑的先例**（`OPENROUTER_API_KEY: ""` ＋
「leave the key empty so the app boots but the LLM path stays untouched」）。參考 V6：
`EMBEDDING_PROVIDER` 的 enum **已含 `stub`**。

參考 V7：若在 CI 起 Ollama，每個 PR 的 `ui-regression` 都要拉 1.2GB 模型（或維護一個快取
機制），而 `ui-regression` 目前是每個 PR 都跑的真閘門。

- **A** — 不在 CI test stack 起 Ollama，改設 `EMBEDDING_PROVIDER=stub`，沿用 `OPENROUTER_API_KEY: ""`
  的既有先例。embedding 的真實行為由 `U6` 的單元測試覆蓋，不由 e2e 覆蓋。
- **B** — 在 CI test stack 起 Ollama，並加模型快取機制（Actions cache 或預先烘進映像）。
- **C** — 不起 Ollama 也不設 `stub`，維持 `EMBEDDING_PROVIDER` 不填——**注意這會讓 backend
  依 `K-01` 的「偵測不到選定提供者時須大聲失敗」而啟動失敗**，等於讓 `ui-regression` 全紅。
- **D** — 設 `EMBEDDING_PROVIDER=fulltext`（enum 內另一個不需外部服務的值），讓 CI 走
  真實的非向量路徑而非 stub。

[Answer]: A  <!-- answered 2026-09-27T04:12:55Z via picker -->

---


### `I2` 的追問（`I2b`）：六個服務全設，但值不能猜

**為何加開這一題。** `[I2]`=C 保留了「六個服務全部設上限」，但本 repo **沒有任何監控堆疊**
（V3／V4），所以 `db` 與 `backend` 的實際用量沒有數字。已向使用者指名會壞掉的東西：`db`
的上限猜低 → 容器被 OOM kill → `restart: unless-stopped` → 重啟迴圈 → 站台掛掉，而全碟
加密（D-1）的主機重開還需要解鎖；`backend` 跑 LLM 呼叫與架構圖建構，用量本身是變動的。
另有一個 **`I1` × `I2` 的交互作用**：Redis 的**容器層**上限必須明顯高於 `maxmemory` ＋
額外開銷，否則容器會在 Redis 有機會淘汰之前就被 OOM kill——把優雅的 LRU 淘汰換成硬重啟，
而那是比淘汰更難診斷的失敗模式。

- **A** — 本站不寫任何具體數字，改定每一個服務的上限**要怎麼推導出來**（以現行 stack 跑
  `docker stats` 量測穩態用量、乘安全係數），且 `DEPLOY.md` 把「量測並記錄數字」列為設上限的
  **前置條件**（沒量過就不得設）。Redis 另定硬約束：容器上限 > `maxmemory` ＋ 開銷。
- **B** — 新服務寫值、舊服務列為「量測後再設」的待辦。
- **C** — 六個全部寫上寬鬆的值（估值的二到三倍）。

[Answer]: A  <!-- answered 2026-09-27T04:12:55Z via picker；理由：保留「六個都設」，但把「猜數字」這個唯一的危險抽掉 -->

#### ⚠ `I2b` 的反轉紀錄（審查 R-21，Critical——conductor 的流程失誤，本輪補正）

**這一節存在的理由是：整份 R-01 修法的唯一依據是一項使用者裁決，而它原本在任何正式來源裡
都沒有紀錄。** 審查 R-21 逐項查出：本節的 `[Answer]: A` 與選項 A 的原文（「`DEPLOY.md` 把
『量測並記錄數字』列為設上限的**前置條件**（沒量過就不得設）」）**原樣未動、零就地註解**，
而 audit shard 在 `REVIEW_COMPLETED`（`04:38:44Z`）與 `REVIEW_REQUESTED`（`04:44:02Z`）之間
只有一個 `HUMAN_TURN`、**沒有 `DECISION_RECORDED` 也沒有答案記錄**；且 Consolidated Summary
Confirmation 早在 `04:14:29Z` 就是 `Looks correct`，此後推翻一項已確認的答案而未重取確認。
三份產出與 `traceability.json` 卻已四處以上宣稱「經使用者裁決」。

`project.md` 三條規則全中：「人工裁決一取得，就在同一個動作內寫回問題檔並執行
`aidlc-log.ts answer`」、「修訂新增的項目必須另行取得確認」、「若第三方只憑 artifact 與
audit 無法重建該授權，可驗證性即已損壞」。**底層事實為真（使用者確實做了那個決定），但從
紀錄上看不出來——依同一份規則，正確處置是重新取得一次可驗證的裁決，不是堅持既有說法。**

**本輪重取，並在此逐字記錄：**

| 項 | 內容 |
|---|---|
| **反轉的確切範圍** | **只及於「值的來源」**，不動 `[I2]`=C 的「六個服務全部設上限」，也不動「值硬寫在 compose、不走環境變數」 |
| **選項 A 的哪一句不再適用** | 「`DEPLOY.md` 把『量測並記錄數字』列為設上限的**前置條件**（沒量過就不得設）」——**這一句作廢** |
| **改成什麼** | **先以公開基準設寬鬆值**；`DEPLOY.md` 標記為「未量測、暫定值」並訂下**複量期限**；複量完成後改 PR 更新數字與日期 |
| **為何反轉** | 三條並存（六個全設 ＋ 沒量過不得設 ＋ 值硬寫）使 `code-generation` **不存在任何合規輸出**——被禁止猜、又必須產出 deploy 六個 ＋ CI test 四個數字，而量測的執行者、時點、通過判準三者皆無 |
| **已揭露的代價** | `DEPLOY.md` 會有一組標明為暫定的數字；**複量期限本身沒有擁有者**（見 Assumptions），若無人指定日期，「限期複量」會退化成「永遠暫定」 |
| **裁決取得方式** | 本輪以 picker 重新提問並取得，時間戳為 `date -u` 實測值 |

[Answer]（反轉後）: 先以公開基準設值、限期複量  <!-- answered 2026-09-27T06:06:19Z via picker；重取，因初次裁決未被記錄於任何正式來源（審查 R-21） -->

### `[I3]`=D 的對應說明

picker 上呈現為「不引入堆疊 ＋ 加 healthcheck」，對應本檔選項 **D**（= A ＋ C）：如實記載
現況（logs ＋ Slack）、指名 metrics／alerts／SLI-SLO 的承接站為 Operations 的
`observability-setup` 並附「該站可能 skip」的風險，**同時**為兩個新容器加 compose
`healthcheck:`（Redis 用 `redis-cli ping`、Ollama 用 `/api/tags`）。

---
## I6 — `OQ-16`：MCP 的傳輸形式，亦即 `brain-infra` 是否需要第七個 compose 服務

> 置於 Consolidated Summary Confirmation **之前**，避免在該區塊之後新增可見標題。
> 本題是 `requirements.md:797` 把 `OQ-16` **逐字指派給本站**（`infrastructure-design`
> 3.4）的那一題，也是 `unit-of-work.md` 修訂 4 Assumptions 逐字指派給本站的
> 「`U1 brain-infra` 是否需要為 `U21 mcp-bridge` 新增第七個 compose 服務」。
> **兩者是同一個問題**：傳輸形式一旦定了，服務數就跟著定。

### 出題前的唯讀查證（非來源登錄）

- `requirements.md:797` 逐字：`OQ-16` =「MCP 的傳輸形式（stdio 或 HTTP／SSE）——決定
  Encryption 面的實際要求（stdio 不過網路；HTTP／SSE 須本機迴環或加密）」，承接站
  `infrastructure-design`（3.4），skip 則轉 `code-generation`。
- `unit-of-work.md` `U21` 逐字：「跑**獨立進程**的 MCP server」、部署模型
  「**standalone（獨立進程，不在 FastAPI process 內；僅供同主機連接）**」。
- `requirements.md:796` 的 `OQ-15` 未定：token 由誰注入該進程、生命週期多長、
  **如何隨使用者切換**；上限是 `C-T11`「token 不得走工具參數」。
- **`backend/services/llm_provider.py:5`、`:17` 逐字**：「There is no subprocess in
  this path.」／「After the migration nothing spawns a subprocess
  (`create_subprocess_exec` and `Popen` have zero occurrences under `backend/`)」。
  該移除是 A3 migration（`ut` commit `b4f0cdc`，2026-10-01）的**刻意結果**，且其
  前身機制曾造成一次無聲失敗（記為該 intent 的 RAID `R-11`）。實測複驗：
  `create_subprocess_exec`／`Popen` 在 `backend/` 的非測試檔命中數為 **0**。
- `mcp` 套件**不在** `backend/requirements.txt`。根目錄 `.mcp.json` 列的六個 server
  （`context7`／`aws-mcp`／`aws-pricing`／`aws-iac`／`aws-serverless`／`mermaid`）是
  **AI-DLC 框架自己的 client 設定**，與本單元無關——`U21` 的驗證方式逐字要求斷言
  「須**排除**根目錄的 `.mcp.json`」。
- 既有先例：`redis`／`ollama` 兩個服務已在 `internal` 網段、**不發佈 `ports:`**，
  其「對外暴露面為零」由 `NFR8.7`／`NFR8.8` 承載，並由 `nfr-design` 的 `D-3`
  （`edge`／`internal` 分段）建立。該模式已實際上線（HEAD 的
  `deploy/docker-compose.deploy.yml` 有 `edge`／`internal` 兩個網段）。

### 選項

**A（建議）— HTTP／SSE，作為 `internal` 網段上的第七個 compose 服務，不發佈 `ports:`。**
理由（平台工程視角）：(1) 它與本單元**已經做過兩次**的形狀完全相同（`redis`、`ollama`
都在 `internal`、都無 `ports:`、都已上線），模式已驗證、已寫進 `DEPLOY.md`；
(2) 它乾淨地解掉 `OQ-15` 最難的那一半——**隨使用者切換**：一個長駐進程，token 走每次
請求的 `Authorization` 標頭，不進工具參數，稽核主體自然是該請求的使用者；
(3) 不需要把 subprocess 重新帶回 backend 的執行期路徑。
代價（逐項，不美化）：新增一個服務會讓 `NFR8` 的九處部署資產同步清單再長一截
（`render-env.sh`、`deploy/.env.example`、兩份 compose 的 `environment:`、`deploy.yml`
兩個 job 的 `env:` 對照表）；且它加入 `internal` 後，`nfr-design` 的 blast-radius 表
必須重算（審查 `R-30` 已點名這件事）。

**B — stdio，由 backend 按 session spawn 子進程，token 走子進程環境變數。**
好處：**零**新網路暴露面、不需要第七個服務、Encryption 面依 `OQ-16` 逐字為不適用
（不過網路）。代價：**它反轉一個兩天前才刻意做完的決定**——`llm_provider.py` 把
「nothing spawns a subprocess」寫成模組契約的一部分，而被移除的那個機制正是上次無聲
失敗（RAID `R-11`）的來源；另外容器內的子進程生命週期（殭屍回收、SIGTERM 時的優雅
關閉、per-child 資源上限）目前完全沒有設置，而 `infrastructure-guide` 的容器檢查表
把這幾項都列為必要。

**C — 本站不定，依 `OQ-16` 的轉移目標交給 `code-generation`（3.5，ALWAYS）。**
好處：不在資訊不足時押一個方向。代價：本站**正是** `OQ-16` 的指派承接站且本站**沒有
被 skip**，不定案等於把一個有明確落點的決定變成無落點；且 `code-generation` 要同時決
定傳輸形式、服務數、env 變數與 blast-radius 影響，那是設計決定而非實作決定。

**D — 讓 MCP 跑在 backend 進程內（掛成 FastAPI 的 SSE 端點），完全不新增服務。**
**這會推翻一個已核可的決定**：`unit-of-work.md` 的 `U21` 逐字寫「獨立進程，**不在
FastAPI process 內**」。若要走這條，須先確認是否接受推翻該決定，以及它對
「agent 身分與使用者身分的對應」與憑證白名單斷言的影響。

X. Other (please specify)

[Answer]: A  <!-- answered 2026-10-03T12:47:03Z via picker；使用者選「A HTTP/SSE，第七個服務（建議）」 -->

### 本題定案的效力

- **`OQ-16` 定案**：MCP 傳輸形式 = **HTTP／SSE**。Encryption 面依 `OQ-16` 逐字
  「HTTP／SSE 須本機迴環或加密」→ 本案以 **`internal` 網段、不發佈 `ports:`** 滿足，
  與 `redis`／`ollama` 同一模式（`NFR8.7`／`NFR8.8` 的「對外暴露面為零」形狀）。
- **`brain-infra` 需要第七個 compose 服務**（`unit-of-work.md` 修訂 4 Assumptions
  指派給本站的那一題，至此定案為「需要」）。
- **對 `OQ-15` 的影響（不是定案，是收窄）**：長駐進程 ＋ 每次請求帶
  `Authorization` 標頭的形狀，使「token 不得走工具參數」（`C-T11`）與「隨使用者
  切換」同時成立。`OQ-15` 的其餘部分（token 由誰注入、生命週期多長）仍未定，
  承接站不變（`contract-design` → `code-generation`）。
- **已知的連帶後果，本站必須寫進產出**：新服務加入 `internal` 後，`nfr-design` 的
  blast-radius 表（`security-design.md` 的 `D-3`）必須重算。**該檔已被本 attempt 的
  終局審查收據凍結，本站不得回改**；故前向指標寫在本站產出內，由 `D-3` 的下一個
  觸及者執行（審查 `R-30` 要求的正是這個前向指標）。

## I7 — 「平台功能轉 MCP，一律用 REST→MCP 的概念做」的範圍（使用者於本站中途提出）

> **本題標示為「本階段新增、已核可 scope 尚未涵蓋（需回補）」**：使用者原話逐字為
> 「平台功能轉mcp，一率使用rest to mcp的概念做」。它改變 `U21 mcp-bridge` 的**形狀**
> （由手寫工具宣告改為自 OpenAPI 產生的轉接層），並可能改變它的**暴露範圍**。
> 依 `project.md`，不得當成既有 `U21` 的自然延伸吸收，須在此明標並回補上游。

### 出題前的唯讀查證（非來源登錄，皆本站實測）

- `openapi.json`（repo 根目錄）：**42 個 path、55 個 operation**；其中
  **51 個宣告 security**，且 `components.securitySchemes` 只有**一個**：`HTTPBearer`。
- CI 已有漂移閘門：`.github/workflows/ci.yml:280` 跑 `scripts/dump_openapi.py --check`。
- 「自 OpenAPI 產生產物」在本 repo 已有先例：`frontend/package.json:12` 的
  `gen:types` = `openapi-typescript ../openapi.json -o src/types/api.d.ts`
  （產物 `frontend/src/types/api.d.ts` 已進版控）。
- `unit-of-work.md` 的 `U21` 逐字交付物包含「工具宣告與其 schema 的**憑證欄位白名單**
  （宣告允許的欄位集合，**其餘皆不得出現**）」與「代使用者呼叫既有 API 的 token
  轉遞路徑（**不經工具參數**）」；其依賴逐字為 `U20 requirement-field-service` 與
  `U19 membership-service`——亦即**已核可的暴露範圍是這兩塊，不是整個 `/api/*`**。
- `C-T11`（`requirements.md`）：token 不得走工具參數。**單一 securityScheme 使這條
  成為產生器裡的一條規則，而不是 51 個特例**——這是 REST→MCP 相較手寫宣告的實質優勢。

### 選項

**A（建議）— 機制一律 REST→MCP，暴露範圍用 allowlist 治理，起點為 `U21` 已核可的範圍。**
一支產生器自 `openapi.json` 產出工具宣告（故工具面與 API 由建構方式保持同步，並受既有
漂移閘門保護）；產生時**剝除**單一 `HTTPBearer` scheme、改由轉接層自請求上下文注入
（滿足 `C-T11`）；暴露哪些 operation 由一份 allowlist 決定，**初始值等於 `U21` 的
`U19`／`U20` 兩塊**，之後逐能力以明示決定擴充。
這樣「一律用 REST→MCP」在**機制層**完全成立（不手寫任何工具宣告），而**暴露面**仍受治理。
代價：要維護一份 allowlist（但它正是 `U21` 已核可的「憑證欄位白名單」的同一個東西往上
一層，不是新增概念）；且每次擴充需要一次明示決定，不是自動跟著 API 長。

**B — 機制與範圍都一律：55 個 operation 全部產生為 MCP 工具。**
最貼近原話的字面。好處：零維護清單，API 長出什麼就自動有工具。
代價（逐項）：(1) 它**反轉** `U21` 已核可的「白名單、其餘皆不得出現」——白名單的語意是
預設拒絕，全量產生是預設允許；(2) 55 個 operation 含帳號停用、RBAC 變更一類的管理端點，
把它們變成 LLM 驅動 agent 可呼叫的工具，是 ADR-0006 的 **IAM ＋ audit logging** 問題，
而**沒有任何已核可產出涵蓋它**；(3) 暴露面會隨 API 自動成長，沒有任何關卡。

**C — 只對 `U21` 已核可的兩塊做，且維持手寫工具宣告（即不採 REST→MCP）。**
維持現狀最小變更。代價：不執行你剛下的指示；且手寫宣告與 API 之間沒有漂移保護，
`openapi.json` 的閘門幫不上忙。

**D — 機制一律 REST→MCP，範圍先全量產生但以「讀取類（GET）優先」分階段開放。**
介於 A 與 B。好處：`/api/*` 的 55 個 operation 中，讀取類的風險明顯低於變更類，先開讀取
可以讓「平台功能轉 MCP」很快有實感。代價：仍需要分級清單（與 A 的 allowlist 成本相同），
而且 GET 也可能洩漏跨專案資料——per-project 授權正是能力 12 才剛建立的東西，尚未上線。

X. Other (please specify)

[Answer]: A  <!-- answered 2026-10-03T12:50:07Z via picker；使用者選「A 機制一律＋ allowlist 治理（建議）」 -->

### 本題定案的效力

- **機制定案**：`U21 mcp-bridge` 的工具宣告**一律自 `openapi.json` 產生**，不手寫任何
  一條。產生時剝除單一 `HTTPBearer` scheme，由轉接層自請求上下文注入 token
  （滿足 `C-T11`「token 不得走工具參數」）。
- **範圍定案**：暴露哪些 operation 由一份 **allowlist** 決定，**初始值 = `U21` 已核可
  的 `U19 membership-service` ＋ `U20 requirement-field-service` 兩塊**；之後逐能力以
  明示決定擴充，不隨 API 自動成長。
- **`U21` 的「憑證欄位白名單」語意不變**（預設拒絕）；allowlist 是它往上一層的同一個
  概念，不是新增概念，亦非放寬。
- **本題為本階段新增、已核可 scope 尚未涵蓋，須回補**：`U21` 原交付物寫的是「工具宣告
  與其 schema 的憑證欄位白名單」，未涵蓋「自 OpenAPI 產生」這個**機制**，亦未涵蓋
  產生器本身作為交付物。回補落點見本站產出的 `§〇`。

## Consolidated Summary Confirmation

- Looks correct
- Request changes

[Answer]: Looks correct  <!-- answered 2026-09-27T11:14:15Z via picker；第二次取得：第二輪審查的 14 項發現（含 2 個 Critical）已全部修訂，且 I2b 的反轉已在本檔就地記錄（審查 R-21）。檔案在 log 之前已確認定稿 -->
