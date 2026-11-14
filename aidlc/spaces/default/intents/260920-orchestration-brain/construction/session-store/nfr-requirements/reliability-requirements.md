# Reliability Requirements — `U10 session-store`

> 編號自 `.40` 起。本檔的核心是 `NFR4` 的可測不變量——而本站查出**它在今天的
> 基礎設施設定下並不成立**，`[N3]`=A 是對那一點的處置。

## 本檔的上游

| 上游 | 它給了什麼 |
|---|---|
| `requirements.md:500-508`（`NFR4`） | 可測不變量逐字：「**重啟 backend 後，既有對話的脈絡與作業對象仍可完整還原**」 |
| `rules.md`（本單元） | `BR1.2`（不得放行程記憶體）、`BR1.4`（到期整體消失）、`BR6.1`（Redis 不可用大聲失敗）、`BR7.1`（重啟還原的範圍） |
| `functional-spec.md`（本單元） | `W7`（TTL 到期後再次進入）、`W8`（Redis 不可用） |
| `deploy/docker-compose.deploy.yml:229-243` | `appendonly yes`、`maxmemory 256mb`、`maxmemory-policy`（實讀） |
| `codekb/chiton/technology-stack.md:169`／`:206` | `redis_aof` 為三個 volume 之一——**AOF 有持久化落點，不是寫進容器層**，這是 `NFR4.52`（`appendonly` 維持 `yes`）真的能在重啟後還原的前提。該檔並逐字記載服務已含「AOF volume、ACL、healthcheck」 |
| `contract-summary.md:684-742`（`K-09`） | 每個方法都列 `raises: [SessionBackendUnavailable]` |

## `[N3]`=A：淘汰策略由 `allkeys-lru` 改為 `noeviction`

**本站查出的問題（實讀 `deploy/docker-compose.deploy.yml:234-235`）**：現行設定為
`--maxmemory-policy allkeys-lru`，它在記憶體用滿時淘汰**任何** key，包含**尚未到期
的活躍 session**。於是 `NFR4` 的「完整還原」在容量壓力下不成立。

**而它是無聲的**。`U1` 自己在同一份 compose 的註解逐字記載：
「An eviction is countable —— **but NOT via `INFO evicted_keys`**（review R-01）：
`INFO` is @slow @dangerous, so **NEITHER configured identity can run it**」。
被淘汰的使用者看到的畫面，與 `W7` 的 TTL 正常到期**完全相同**。

| ID | 需求 | 判定方式 | 來源 |
|---|---|---|---|
| **NFR4.50** | Redis 的 `maxmemory-policy` 須為 **`noeviction`** | `deploy/docker-compose.deploy.yml` 的 `command:` 逐字比對。本設計的**每一個** key 都帶 TTL（`BR1.3`：五個方法全部續期；工作項集合同 key），故 `noeviction` 之下 session **只會因 TTL 消失、不會因容量消失** | `[N3]`=A；`NFR4` 的可測不變量 |
| **NFR4.51** | 記憶體耗盡時，**寫入**須大聲失敗並循 `SessionBackendUnavailable` 路徑向上傳遞；**讀取（`load`）須仍然可用** | `noeviction` 之下 Redis 對寫入回 `OOM command not allowed`，對讀取正常服務。本條要求本單元把該錯誤對應到 `SessionBackendUnavailable` 而非吞掉。**降級形狀明寫**：既有 session 仍讀得到，只是不能再寫——這比「少數人無聲失去整個 session」好得多，且是**可偵測的** | `BR6.1`；`[N3]`=A |
| **NFR4.52** | `appendonly` 須維持 `yes` | 已由 `U1` 設定（`:230-231` 實讀）。本條只要求**不得被改掉**——`U1` 的註解逐字說明不設它會讓重啟後 session 全失而健康檢查仍然通過 | `NFR4`；`U1` 的 `NFR4.2` |

## `NFR4` 可測不變量的逐項拆解

`NFR4` 只給了一句話。本單元把它拆成**可逐項驗證**的清單，否則「完整還原」會被
實作讀成「有東西還在就算還原」。

| ID | 重啟後須完整還原的項目 | 若漏掉會怎樣 |
|---|---|---|
| **NFR4.53** | 每一個存在的段（`shared` 必在，另兩個視是否建立過） | 使用者的獨立對話消失，`AC3.1.4` 的「切回時與離開時相同」失敗 |
| **NFR4.54** | 每一段的**完整**訊息歷程與其順序 | `U11` 的指涉詞解析失去依據（`BR3.3`） |
| **NFR4.55** | 每一段**各自**的三層作業對象（含為 `null` 的層） | `[S3]`=A 的整個設計失效；且把 `null` 寫成「未選定」以外的值會讓 `AC2.2.3` 失敗 |
| **NFR4.56** | `pageModes` 的兩個鍵 | 使用者回來時該頁讀到錯的段——**這一項最容易漏**，因為它不是「資料」而是「指標」 |
| **NFR4.57** | 剩餘 TTL（重啟不得重設為滿額，亦不得歸零） | 重設為滿額等於延長保存期，與 `ADR-005` 的 24 小時語意不符 |

**驗證方式**：單元定義逐字的「**重啟還原測試**」——寫入上述五類狀態、重啟 backend
容器、逐項讀回比對。**這不是 `BR7.1` 的重述**：`BR7.1` 說「要還原」，本節說「還原
的對象逐項是什麼」，而實作漏掉 `pageModes` 時 `BR7.1` 的字面仍然成立。

## 可用性與復原目標

| 項目 | 值 | 理由 |
|---|---|---|
| **可用性目標** | **不設 SLO** | 本 intent 的部署目標是**自有 staging**（`ADR-0007`／`ADR-0001`：雲端 production 不在範圍）。`nfr-requirements-guide.md` 逐字「99.9% 需要 auto-restart、health check、alerting」——本 repo 的 Redis 有 `restart: unless-stopped` 與 healthcheck，但**沒有告警管道**。訂一個無法量測也無人值守的數字是假精確 |
| **RPO** | **24 小時內的 session 資料可接受全失** | session 是暫存狀態不是記錄；`ADR-005` 已定它 24 小時就會自然消失。**不為它做備份**，這是刻意的 |
| **RTO** | 隨 backend 容器的重啟時間 | Redis `restart: unless-stopped`；AOF 載入時間與資料量線性相關，在 256 MB 上界之下為秒級 |
| **單點** | Redis 是**單一實例、無副本** | 明寫而非隱含：Redis 掛掉時全部 session 不可用，`BR6.1` 使它大聲失敗。在 staging 範圍內接受此單點；任何改變需新 ADR |

## 優雅降級

| 失效 | 本單元的行為 | 使用者看到什麼 |
|---|---|---|
| Redis 不可達 | `raise SessionBackendUnavailable`（`BR6.1`） | 由 `U13` 決定呈現；本單元**不**回空 session |
| Redis 記憶體耗盡 | 寫入失敗、讀取正常（`NFR4.51`） | 既有對話讀得到，新訊息送不出 |
| `K-07` 回 `HierarchyForbidden`／`HierarchyNotFound` | 原樣向上傳遞（`BR4.6`） | 選不到那個作業對象 |
| TTL 到期 | 全新 session，作業對象未選定（`W7`） | 脈絡列顯示「尚未選定」 |

**前兩列的區分是本檔最要緊的一點**：三種「session 不見了」的成因——故障、容量、
到期——在今天的 `allkeys-lru` 之下對使用者與對維運**完全相同**。`[N3]`=A 之後，
容量那一種變成寫入錯誤（可見），只剩故障與到期兩種，而它們的訊號不同
（例外 vs 正常的新 session）。
