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
## Consolidated Summary Confirmation

- Looks correct
- Request changes

[Answer]: Looks correct  <!-- answered 2026-09-27T11:14:15Z via picker；第二次取得：第二輪審查的 14 項發現（含 2 個 Critical）已全部修訂，且 I2b 的反轉已在本檔就地記錄（審查 R-21）。檔案在 log 之前已確認定稿 -->
