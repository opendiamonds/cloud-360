# Tech Stack Decisions — `U10 session-store`

> 編號 `NFR5.40`、`NFR8.40`–`.42`。本檔只記**本單元引入或改動**的技術選擇，
> 不重述既有技術棧。

## 本檔的上游

| 上游 | 它給了什麼 |
|---|---|
| `requirements.md:537-545`（`NFR8`） | 新增元件的部署設定完整性，與「失敗模式**無聲**」的逐字理由 |
| `requirements.md:510-518`（`NFR5`） | WebSocket 契約閘門：新 WS 須有前後端共用的型別契約來源與 CI 一致性檢查 |
| `contract-summary.md:89-150`（`K-01`） | `REDIS_URL`／`REDIS_PASSWORD` 的型別、必填性與驗證規則 |
| `codekb/chiton/technology-stack.md` | 既有技術棧（本單元不改動其中任何一項） |
| `functional-spec.md` §六（本單元） | `D-S10-1`：`K-02` 的四個 payload 需加識別欄位 |
| `backend/requirements.txt`（實讀） | **無任何 Redis 客戶端** |
| `rules.md`（本單元） | `BR3.5`（上限參數缺值時服務不得啟動）是 `NFR8.40` 的「無預設值」要求的直接來源；`BR6.1`（Redis 不可用大聲失敗）是 `NFR8.41` 第一項硬條件的來源 |
| `codekb/chiton/technology-stack.md:35`／`:206` | `:35` 以程式解析得出「**18 項宣告 ＝ 3 支精確 pin ＋ 1 支下限 ＋ 14 支完全浮動，無 lockfile**」；`:206` 逐字「剩下的是**新增 Python 套件依賴 ＋ 寫客戶端**。注意**新增依賴會放大「無 lockfile」的曝光面**」——`NFR8.41` 的選型條件二即據此而來。**另注意該檔 `:63` 指出 `team.md` 記載的 `fastapi[standard]==0.141.1` 已與實際的 `fastapi==0.111.0` 不符**，故本檔引用釘選紀律時以 `requirements.txt` 檔頭與該 codekb 的實測為準，不引 `team.md` 的數字 |

## 既有技術棧：本單元不改動的部分

| 層 | 選擇 | 本單元的關係 |
|---|---|---|
| 語言／框架 | Python ＋ FastAPI | 沿用，不改 |
| 資料庫 | PostgreSQL（`psycopg` v3） | **本單元完全不碰**——`[N1]`=A 之後對話歷史不落 PostgreSQL |
| Session 儲存 | **Redis 8（`redis:8-alpine`）** | 由 `U1` 引入為第 5 個服務；**本單元是它的第一個真實消費者** |
| 測試 | `unittest` ＋ `hypothesis` ＋ `TestClient` | 沿用，不引入 pytest |
| 依賴釘選 | `fastapi`／`pydantic` 精確釘選，其餘未釘 | 見 `NFR8.41` |

## 需求

| ID | 需求 | 判定方式 | 來源 |
|---|---|---|---|
| **NFR8.40** | 每段訊息筆數上限須以**具名環境變數**承載，且**無預設值**；同一個 PR 內 `deploy/render-env.sh` 必須寫它、`deploy/.env.example` 與 `backend/.env.example` 必須列它 | `python3 scripts/validate_env_contract.py`（CI 的 `repo-contract` job 亦執行）。**值為 200**（`[N2]`=A）。無預設值的理由見 `BR3.5`：把缺值讀成「無上限」會讓單一 key 無上界成長，而那是無聲的 | `NFR8` 逐字；`project.md ## Mandated` 的環境設定 contract；`BR3.5` |
| **NFR8.41** | 本單元**必須**新增一個 Python Redis 客戶端依賴；**具體套件與版本由 `code-generation` 選定**，但選型須滿足兩項硬條件 | 條件一：能把 `noeviction` 的 `OOM command not allowed` 與連線失敗**區分**為可判別的錯誤（`NFR4.62`／`OPEN-N10-5`）。條件二：遵循 `requirements.txt` 檔頭的釘選紀律——該檔逐字說明 `fastapi`／`pydantic` 用 `==` 的理由是 OpenAPI 輸出的位元決定性；本依賴不影響 OpenAPI，故**不強制 `==`**，但須在同一個 PR 內說明選擇 | **實讀 `backend/requirements.txt`：無任何 Redis 客戶端**；`backend/` 全樹僅 `.env.example` 與 `test_render_env_redis.py` 兩處提及 `REDIS_*` |
| **NFR8.42** | `[N3]`=A 的 `maxmemory-policy` 由 `allkeys-lru` 改為 `noeviction`，須走與其他部署設定相同的同步紀律 | 改動 `deploy/docker-compose.deploy.yml` 的 `command:`；**並檢查 `deploy/docker-compose.test.yml` 的 redis 服務是否需要同步**（該檔逐字自述「NO maxmemory / NO AOF / NO named volume on redis。This stack is rebuilt…」——若測試 stack 本就不設 `maxmemory`，則 `noeviction` 對它無意義，**但這一點必須被確認而不是假設**） | `[N3]`=A；`project.md ## Mandated` 的三環境分離規則 |
| **NFR5.40** | `D-S10-1` 對 `K-02` 四個 payload 的欄位新增，須通過 `NFR5` 的前後端契約閘門 | `NFR5` 逐字要求「一份前後端共用的訊息型別契約來源，並有一個 CI 檢查斷言兩端一致」。本單元**不擁有**該閘門（`U2 brain-ws-contract` 擁有），本條只確立：本單元造成的契約變更**不得繞過它** | `NFR5`；`functional-spec.md` §六 |

## `NFR8` 的「無聲失敗」在本單元的具體形狀

`NFR8` 的理由逐字是：「無 fallback 的變數缺值時只會變成空字串，服務照常啟動但
功能降級（既有實例：`N8N_USER`／`N8N_PASSWORD` 從未被寫入，導致每次部署的架構圖
icons 靜默退回灰底佔位圖）」。

本單元有**兩個**同形的風險點，且兩者的處置相反：

| 變數 | 缺值時 | 處置 |
|---|---|---|
| `REDIS_URL`／`REDIS_PASSWORD` | 連不上 Redis ⇒ `BR6.1` 大聲失敗 | **已經是大聲的**——`K-01` 已定 `required: true, default: null`，且 `render-env.sh:65` 實讀有 `REDIS_PASSWORD` 的缺值檢查 |
| 訊息筆數上限 | **若實作給它一個預設值，就是無聲的**——服務正常啟動、功能正常、記憶體慢慢漲 | `NFR8.40` ＋ `BR3.5`：**無預設值，缺值時服務不得啟動** |

**第二列正是 `N8N_PASSWORD` 那個教訓的同形**，差別只在這次是在設計時就認出來。

## 不採用的技術選項（附理由）

| 選項 | 否決理由 |
|---|---|
| 把對話歷史存進 PostgreSQL | `[N1]`=A 已定案不做。理由見 `security-requirements.md` 的 `OPEN-N10-1`／`OPEN-N10-2`：消費端元件本身無人擁有、無 FR、無 AC |
| 為 session 另起第二個 Redis 實例或第二個 key | `ADR-005` 的 Alternatives Rejected 逐字拒絕「分成兩個 key」（會出現「常駐區空了但脈絡列還在」的中間態） |
| 以 Redis Hash／Stream 等專用結構取代單一序列化值 | **本站不預選儲存結構**——那是 `code-generation` 的實作決定，只要滿足 `BR1.4`（整體到期）與 `BR3.4`（每段獨立修剪）即可。先驗地釘死結構會讓實作無法在兩者之間取捨 |
| 引入 APM／metrics 套件 | 超出本單元範圍。`observability-requirements.md` 的 `OPEN-N10-4` 已把它記為無自然承接站的缺口，不由本單元夾帶 |
