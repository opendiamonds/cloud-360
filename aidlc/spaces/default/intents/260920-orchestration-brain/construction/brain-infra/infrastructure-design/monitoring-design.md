# Monitoring Design — `brain-infra`（U1）

## 這份檔在做什麼，以及它誠實地不做什麼

stage 檔要求本檔產出 metrics／alerts／SLI-SLO 三張表。**本 repo 沒有任何監控堆疊**，所以
如果照樣式填滿三張表，產出的會是一份看起來完備、實際上一項都不存在的文件。

`[I3]`=D 的定案是：**不引入任何新堆疊**，如實記載今日的可觀測面，指名承接站，**並**為兩個
新容器加 `healthcheck` ——因為那是零新依賴、且能讓「容器活著但服務不通」至少變成可見的
唯一手段。

**查證依據（本站實查，非推測）**：`prometheus`／`grafana`／`datadog`／`opentelemetry`／
`otel`／`sentry` 在 `deploy/`、`backend/`、`.github/` 的命中只有三處，且全部是**關鍵字
清單**——`backend/services/wa_lens_engine.py:415–416` 與 `wa_rule_engine.py:375` 用它們偵測
「使用者提交的架構有沒有提到監控」。**不是實際堆疊。**

---

## 一、今日的可觀測面（完整清單，只有三項）

| 機制 | 涵蓋什麼 | 觸發／查看方式 | 限制 |
|---|---|---|---|
| **`docker compose logs`** | 六個容器的 stdout／stderr | 人工登入主機；`deploy.yml` 在**失敗路徑**自動印 `--tail=80` | 無聚合、無保留政策（本輪起由 `infrastructure-specification.md` `§三` 的 `logging:` 給出容量上限；本檔的對應敘述在 `§五`。**審查 R-23：初版此處的 `§三` 在本檔是 Alerts，指錯了節**）、無搜尋、無告警 |
| **`docker compose ps` ＋ `healthcheck`** | 容器存活；`db` 有 `pg_isready`，**本輪新增 `redis` 與 `ollama` 的** | 人工查看。**`depends_on: condition: service_healthy` 只消費其中一部分**：今日僅 `backend` → `db` 一條（`deploy/docker-compose.deploy.yml:63–65`）；本輪之後 `backend` → `redis` 也是 `service_healthy`，而 `backend` → `ollama` 刻意用 **`service_started`**（理由見 `§六`） | `frontend`／`backend`／`cloudflared` **仍無 healthcheck**（既有狀態）。**`ollama` 的 healthcheck 不被任何 `depends_on` 當成就緒條件**——它只供人工查看 |
| **`notify` job 的 Slack 通知** | 部署結果、回滾結果、revert PR 連結 | 每次 `deploy.yml` 執行後（`SLACK_BOT_TOKEN` 未設時只印 warning 並跳過） | 只在**部署事件**時發。運行中的異常完全不通知 |

**所以今日的實際狀態是：部署會通知，運行不會。** 站台在兩次部署之間壞掉，沒有任何機制會
主動告知。這是既有狀態，不是本單元引入的。

---

## 二、Metrics & KPIs — **本單元不交付任何 metrics 收集**

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| — | — | — | **本單元不交付。** 見下方承接站 |

**承接站：Operations 階段的 `observability-setup`。**

**必須明說的風險**：該站在本工作流程中是否執行**尚未確認**。若它被 skip，**本 intent 將
完全沒有 metrics**——而 `project.md` 已逐字記載 observability 是 Operations 中「尚未落地的
真實待辦」。依 `project.md` 的既有規則：**屆時判定 skip 的執行者須重新提交使用者裁決，
不得由實作者當場決定。**

**下列項目是本單元新增、但目前只能人工觀察的**，列出來是為了讓承接站知道該收什麼：

| 項目 | 為什麼它值得被收 | 目前只能怎麼看 |
|---|---|---|
| Redis 的 `evicted_keys` | `[I1]`=A 採 `allkeys-lru`，淘汰發生即代表 session 在不足 24 小時就被回收——使用者會失去脈絡而無人知道 | `redis-cli INFO stats` 人工查 |
| Redis 的 `used_memory` vs `maxmemory` | 接近上限是淘汰即將開始的前兆 | `redis-cli INFO memory` |
| 容器重啟次數 | `restart: unless-stopped` 之下，反覆重啟（例如 OOM kill）在外部完全靜默 | `docker compose ps` 的 `STATUS` 欄 |
| Ollama 的記憶體常駐量 | `[I2]` 的上限值是否設對，唯一的事後證據 | `docker stats` |
| 承載 volume 的檔案系統可用空間 | `S-10` 的前置條件會在運行中被慢慢吃掉 | `df -h` |

---

## 三、Alerts — **本單元不交付任何告警規則**

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| — | — | — | **本單元不交付。** 承接站同本檔 `§二` |

**唯一接近告警的既有機制是 `notify` job 的 Slack 通知，而它只在部署事件時發。**

**本單元新增了兩個在記錄上不可辨識的失敗模式，必須如實記載**：

1. **未授權的 Ollama 呼叫**——`NFR8.9` 已把「零認證前提下未授權呼叫在記錄上不可辨識」記為
   **已接受的代價**。`nfr-design` D-3 的網段分段把可達者由 5 縮到 3，但那是網段控制、
   不是身分控制，也不產生任何記錄。
2. **Redis 開始淘汰**——`[I1]`=A 之下，淘汰是靜默的：使用者只會感覺到「脈絡不見了」，
   而那與 24 小時 TTL 正常到期**在使用者端無法區分**。`evicted_keys` 是唯一的區分依據，
   而沒有任何機制在收它。

---

## 四、SLIs／SLOs — **本單元不交付**

| SLI | SLO target | Measurement window |
|---|---|---|
| — | — | — |

**理由不只是「沒有監控堆疊」，還有一個更基本的**：SLO 需要量測機制才有意義，而
`operation.md` 的護欄逐字要求「SLO 必須以具體百分比與時間窗量化」。在沒有任何 metrics
收集的情況下寫下數字，會產出一個無法被驗證、也無法被違反的 SLO——那比沒有 SLO 更糟，因為
它看起來像已經有了。

**承接站同本檔 `§二`。** 上游 `requirements.md` 的 `NFR1`（意圖識別準確率）、`NFR2`（跨頁面上下文
保留率）、`NFR11`（頁面切換次數）都是**產品層**的量測目標，落點在 `build-and-test`，
**不是本單元**，也不是基礎設施層的 SLI。

---

## 五、Logs & Tracing

### 日誌聚合策略

**沒有聚合。** 六個容器各自寫 Docker 的 `json-file`，人工以 `docker compose logs` 查看。

**本輪的唯一改變（`[I4]`=A，`S-9`）**：為兩份 compose 的**全部服務**加上
`logging.options` 的 `max-size` 與 `max-file`。具體值依 `NFR8.9` 由部署者定並記入
`DEPLOY.md`；本檔不指定個別值，**但總量有上界**：`max-size` × `max-file` × 服務數
**不得超過 2GB**（`infrastructure-specification.md` `§三`）。那個上界不是可有可無的——
`infrastructure-specification.md` `§四` 的磁碟公式把「日誌預算」列為一項輸入，若這兩個值完全自由，該項就是無界的自由變數。

**為何超出 `NFR8.9` 的字面（它只要求兩個新容器）**：照字面做會讓 `backend`（本 repo 最多
日誌的服務）維持無界，而磁碟寫滿對一台全碟加密的主機是實際風險——`S-10` 已把磁碟空間列為
前置條件，無界日誌會讓它在運行中被慢慢吃掉。且設日誌上限**不需要任何用量資料**，成本與
風險都遠低於資源上限。

### 分散式追蹤

**沒有。** 而且這一項有一個已知的、指名了承接單元的缺口：

**correlation ID 的產生與跨 agent 傳遞在本單元沒有落點**（`nfr-design` 的
`AUDIT-CORRELATION-ID` 已記載）。承接點是 **`U13 brain-gateway`（請求入口、產生點）與
`U12 work-orchestrator`（跨 agent 呼叫的傳遞點）的 `nfr-design` 迭代**。

**風險**：`nfr-design` 是 `CONDITIONAL` 且 `for_each: unit-of-work`，其 `condition` 為連言
（`NFR Requirements was executed` **and** `NFR patterns need design`）——`brain-infra` 跑過
那一站**完全不保證** `U12`／`U13` 會跑。屆時判定 skip 的執行者須重新提交使用者裁決。

### Dashboard 規格

**沒有 dashboard。** 承接站同本檔 `§二`。

---

## 六、本輪唯一的實質新增：兩個 `healthcheck`

`[I3]`=D 的 `C` 半邊。這是本單元在監控面**唯一**的交付。

| 服務 | 檢查方式 | 它證明什麼 | **它不證明什麼** |
|---|---|---|---|
| `redis` | `redis-cli ping` | Redis 行程在回應 | **不證明 ACL 專用使用者可用**——`ping` 在 `default` 使用者下也會過，而 `NFR4.1` 要求連線必須用非 `default` 的 ACL 使用者。憑證錯誤會在 backend 連線時才以 `WRONGPASS` 出現 |
| `ollama` | `/api/tags`（列出已載入模型） | HTTP 服務在回應 | **不證明 `bge-m3` 存在**——而這比「下載期間的過渡態」嚴重得多：官方 `ollama/ollama` 映像啟動**不會**自動拉任何模型（審查 R-02，Critical），所以若沒有一個明確的 pull 動作，`/api/tags` 會**永久**回空清單、這個 healthcheck **恆為健康且恆無模型**。**模型就緒由部署後的 `ollama pull` 步驟保證**，不由 healthcheck 保證 |

**「不證明什麼」那一欄是刻意接受的，不是疏漏**：更深的檢查需要憑證（Redis 的 ACL 使用者
密碼要進 healthcheck 指令，那等於把它寫進 compose 的 `test:` 陣列）或觸發一次真實推論
（Ollama），兩者都不適合放在每 N 秒執行一次的 healthcheck 裡。

**與部署後探測的分工，必須寫清楚**：`healthcheck` 管**容器層存活**，
`nfr-design` 的 `PROBE-CONTRACT` 管**跨服務的實際連通性**。兩者不可互相替代——而本單元
初版的教訓正是「健康檢查看不到資料面」（`nfr-design` 的審查 R-01，Critical）。

**具體的 `interval`／`timeout`／`retries` 值**：沿用 `db` 既有的形狀為基準
（deploy stack 的 `db` 用 `interval: 10s`／`timeout: 5s`／`retries: 5`）。具體值留
`code-generation`。

**初版在此寫錯了一個約束，本輪更正（審查 R-04）**：初版寫「Ollama 的 `start_period` 必須
足夠涵蓋一次模型下載，否則 `depends_on: condition: service_healthy` 會讓首次部署失敗」。
**兩處不成立**：

1. **沒有任何服務 `depends_on` `ollama` 並用 `service_healthy`。** 實測現況的三條
   `depends_on` 是 `deploy/docker-compose.deploy.yml:63–65`（`backend` → `db`，
   `condition: service_healthy`）、`:77–78`（`frontend` → `backend`）、`:92–93`
   （`cloudflared` → `frontend`）。初版引用了一個它自己沒有設計的前提。
   **本輪已補上拓樸定案**：`backend` → `ollama` 用 **`service_started`**，正是為了避免
   製造一個「看起來在等就緒、實際等不到正確東西」的邊（見
   `infrastructure-specification.md` `§二`）。
2. **模型下載不在啟動路徑上。** `[R-02]` 的定案是**部署後步驟**（`ollama pull`），時序上
   晚於 `up -d`。所以 `start_period` 不需要涵蓋下載——它只需涵蓋 `ollama serve` 自身的
   啟動，那是秒級的。

**同樣更正 `§一` 第 2 列的措辭**：該處把「`depends_on: condition: service_healthy` 會消費
它」寫成既有事實，而實際上**今日只對 `db` 成立**；本輪之後對 `redis` 也成立
（`service_healthy`），對 `ollama` 不成立（`service_started`）。

---

## Assumptions & Open Questions

- **Ollama 的首次模型下載時間未實測**。**但它不決定 `healthcheck` 的 `start_period`**——
  初版此處逐字寫「若 `start_period` 設得不足，首次部署會因 `depends_on` 而失敗」，而同檔
  `§六` 已以兩個理由推翻它（沒有服務以 `service_healthy` 依賴 `ollama`；下載由部署後步驟
  承載、不在啟動路徑上）。**審查 R-15 指出這兩句相互對撞，本輪更正。** 未實測的下載時間
  實際影響的是**部署步驟的耗時**與 `deploy` job 的 30 分鐘逾時餘裕 [assumption]
- **`observability-setup` 是否執行未確認**，而本檔的 metrics／alerts／SLI-SLO 三張表全部
  指向它。若被 skip，本 intent 完全沒有 metrics 與告警 [assumption]
- **`U12`／`U13` 的 `nfr-design` 是否執行未確認**，而 correlation ID 的承接點在那裡
  [assumption]
- **Redis 淘汰與 TTL 正常到期在使用者端無法區分**，而沒有任何機制在收 `evicted_keys`。
  這是 `[I1]`=A 的已接受代價，但它使「使用者抱怨脈絡不見了」這類回報**無法被診斷**
  [assumption]
