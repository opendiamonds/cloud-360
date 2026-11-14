# Scalability Requirements — `U10 session-store`

> 編號自 `.40` 起。本檔的每一個數字都附**算式與其輸入的出處**；輸入若是假設而非
> 量測，逐條標明。

## 本檔的上游

| 上游 | 它給了什麼 |
|---|---|
| `requirements.md:430-445`（`NFR2`） | 跨頁面上下文保留率的量測母體是**頁面切換事件**，三處之間 |
| `requirements.md:500-508`（`NFR4`） | 狀態一律放 Redis |
| `rules.md`（本單元） | `BR3.4` 每段筆數上限、`BR1.4` TTL 到期整體消失、`EC4` 段數上界 3 |
| `functional-spec.md`（本單元） | `W1`／`W7` 決定 session 的建立與消失時機 |
| `contract-summary.md:916-925`（`x-concurrent-connections`） | 同一 key **允許多條並存連線**（三個頁面、多個分頁），伺服器不以連線為狀態單位 |
| `deploy/docker-compose.deploy.yml:232-235` | `--maxmemory 256mb`（實讀） |
| `codekb/chiton/technology-stack.md:167`／`:169` | staging 實為 **6 個服務**（`db`／`backend`／`redis`／`ollama`／`frontend`／`cloudflared`，該檔註明「**兩份 store 皆記 4**」為過期）與 **3 個 volume**（含 `redis_aof`）。**本檔的 256MB 不是整台主機的記憶體**——它與其餘五個服務共用同一台 `192.168.10.10`，其中 `ollama` 是記憶體大戶。容量餘裕的判斷必須放在這個脈絡下讀 |

## 容量算式（輸入全部標明出處）

| 輸入 | 值 | 來源 |
|---|---|---|
| Redis 記憶體上限 | **256 MB** | `deploy/docker-compose.deploy.yml:233` **實讀** |
| 每個 session 的段數上界 | **3** | `entities.md` 的 `EC4`（封閉集合 `shared`／`workspace`／`assessment`） |
| 每段訊息筆數上限 | **200** | `[N2]`=A 本站定案 |
| 每則訊息平均位元組 | **500 B** | **假設，非量測**。含中文訊息文字與 `sequence`／`role`／`createdAt` 中繼欄位。下游若取得實測值須重算本節 |

```
單一 session 的歷程上界 = 3 段 × 200 則 × 500 B = 300 KB
可同時存活的 session 數  = 256 MB ÷ 300 KB      ≈ 850
```

**這個 850 是上界而非穩態**：實際上絕大多數 session 不會有三段、也不會填滿 200 則。
它的用途是回答「最壞情況下會不會撞上 `maxmemory`」，不是容量規劃的預測值。

## 需求

| ID | 需求 | 判定方式 | 來源 |
|---|---|---|---|
| **NFR4.40** | 系統須能同時持有 **≥ 300 個** 已填滿上界的 session 而不觸及 `maxmemory` | `300 × 300 KB = 90 MB`，為 256 MB 的 **35%**。選 300 的理由：自有 staging（`192.168.10.10`）的實際使用者數遠低於此，留 2.8 倍餘裕給 AOF 緩衝與 Redis 自身開銷 | `[N2]`=A 的算式；`ADR-0007` 的 staging 範圍 |
| **NFR4.41** | 每個 session 的記憶體佔用須有**可計算的硬上界**，不得有任何無上界成長的欄位 | 逐欄檢查：`segments` 上界 3（`EC4`）、每段 `messageHistory` 上界 200（`BR3.4`）、`pageModes` 固定 2 鍵（`EC2`）、其餘皆為純量。**工作項集合（`K-11`，`U12` 擁有）共用同一個 key 但不在本單元的上界之內**——這是真實的缺口，見下方 | `BR3.4`；`BR3.5` |
| **NFR2.41** | 同一 session key 的並存連線數**不設上限**，且連線數成長**不改變狀態的記憶體佔用** | 由構造滿足：伺服器不以連線為狀態單位（`x-concurrent-connections` 逐字），狀態一律在 Redis 的該 key 之下。連線登錄為行程內（`K-12` 的 `fanout_mechanism_and_its_assumption.registry`），屬 `U13` | `x-concurrent-connections.multiple_allowed` |
| **NFR2.42** | 狀態扇出的成本與該 key 的存活連線數**線性**相關，不得為二次 | 一次狀態變更 ⇒ 一次 Redis 寫入 ＋ N 次送出。禁止「為每條連線各讀一次狀態」的形狀 | `BR2.7`；`NFR2.40`（效能面的上界） |

## 成長模型與觸發點

| 維度 | 現況 | 成長驅動 | 觸及上限時的徵兆 | 處置 |
|---|---|---|---|---|
| 同時存活 session 數 | 0（本單元尚未實作） | 使用者數 × 24h 內的活躍比例 | 寫入開始失敗（`[N3]`=A 的 `noeviction`） | 提高 `maxmemory`，**並同步提高容器上限**（`U1` 的註解逐字 `container memory limit >= maxmemory × 1.5 + 256MB`） |
| 單一 session 大小 | — | 對話輪數 | 不會成長——`BR3.4` 的上限封住它 | 無 |
| 段數 | — | 使用者在兩個子頁面各開一段 | 不會成長——`EC4` 的封閉集合封住它（上界 3） | 無 |
| 並存連線數 | — | 分頁數 | 行程內登錄的記憶體，屬 `U13` | `U13` 的範圍 |

**三個維度裡有兩個是封閉的**，這是 `[S1]`=A 選擇「段識別就是頁面名」的附帶收益：
段數不可能因使用者行為而成長，所以容量只剩「有多少人在用」這一個自由度。

## 具名缺口

### `OPEN-N10-3`：工作項集合共用同一個 key，但不在本單元的記憶體上界之內

`K-09.data_shape` 的 note 逐字「工作項集合亦放在同一個 session key 之下（見 `K-11`）」，
而 `K-11` 的 `WorkItem` 由 `U12 work-orchestrator` 擁有。本檔的 300 KB 上界
**只涵蓋本單元擁有的欄位**；工作項集合**沒有任何已定的數量上限**。

**後果**：`NFR4.40` 的 300 個 session 餘裕是在「工作項集合佔用可忽略」的前提下算的，
而那個前提**沒有人保證過**。若 `U12` 讓工作項無上界累積，本檔的容量算式就失效，
而失效的方式是 `[N3]`=A 之下的**寫入失敗**——會被發現，但會被誤判為本單元的問題。

**承接**：`U12 work-orchestrator` 的 `nfr-requirements`（3.2，CONDITIONAL、per-unit）；
轉移目標為 `U12` 的 `code-generation`（3.5，**ALWAYS**）。**已查證 `U12` 在游標之後**
（`construction/` 下無 `work-orchestrator/`）。**具體修法**：`U12` 須為工作項集合
定一個每 session 的數量上限，並把它納入同一個 key 的記憶體上界。
