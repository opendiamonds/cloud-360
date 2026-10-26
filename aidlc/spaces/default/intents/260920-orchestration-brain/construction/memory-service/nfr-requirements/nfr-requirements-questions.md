# NFR Requirements 問題檔 — `U8 memory-service`

> `service` kind，故七份產出全部適用（performance／security／scalability／
> reliability／observability ＋ tech-stack-decisions ＋ traceability）。
>
> **本站只問兩題**。其餘 NFR 面向已由上游定案或由本站就地查證後據實記載，
> 逐項列於 §〇。

## 〇、不重問的事（上游已定案，逐項附依據）

| 事項 | 定案處 |
|---|---|
| 記憶落在獨立 schema、grant 只開放該 schema | `FR4.2`／`FR4.4`；`NFR6`；`K-05` |
| `NFR6` 的驗證載體為真實 PostgreSQL 的 CI job | `NFR6` 逐字；`U5` 已交付 `memory-schema` job |
| episodic 的靜態加密（主機層）與傳輸加密（compose 內部） | `U5` 的 `NFR6.1`／`NFR6.2`——`NFR7` 逐字把它指派給設計階段，`U5` 已回答 |
| 稽核保存 90 天、以自身 `occurredAt` 為鍵 | `U5` 的 `NFR7.2`（已外溢到版控 SQL 的索引註解） |
| 90 天清除的承載形式與其漏跑偵測 | `U9` 已交付（`NFR7.10`–`NFR7.15`、`NFR8.10`） |
| 擁有者寫入端強制、可見範圍預設最窄、放寬需角色授權 | `FR4.3a`／`FR4.3b`；本單元 `functional-design` 的 `BR1`／`BR2`／`BR5` |
| 稽核查詢的授權（僅 `Platform_Admin`／`Platform_Owner`） | 本單元 `functional-design` 的 `[FD2]`=A（`BR6.1`） |
| `visibilityScope` 的兩值封閉集合 | 本單元 `functional-design` 的 `[FD3]`=A |
| 相似度檢索必須以 `embeddingModel` 分群 | `MemoryStore.behaviour`；`BR3.2` |
| EmbeddingPort 四實作與其不可用時大聲失敗 | `U6` 已交付（`K-06`） |
| `NFR9` 成本原則為設計原則、**非可量測門檻** | `NFR9` 逐字「此為設計原則，**非可量測的門檻**」 |

### 〇之一、`NFR10` 不是本單元的落點，但它的指派在 per-unit 世界裡是歧義的

`NFR10`（路由層模型可替換性／`typesafe/jev-1.13` 的選定）逐字把落點寫成
「於 `nfr-requirements`（3.2）在有實測準確率與延遲基準後決定」，並逐字警告
「若該站被 skip，本工作流程**沒有自然承接站**」。

**問題在於 `nfr-requirements` 是 `for_each: unit-of-work`**——本 intent 有 24 個
單元，所以「`nfr-requirements` 這一站」實際上是最多 24 個不同的站。
`NFR10` 的主題是**路由層的模型**，屬 `U11 intent-router`，不屬本單元。

**本站的處置**：如實記載此歧義，並指名真正的落點為
**`U11 intent-router` 的 `nfr-requirements`**。記為 `N8-1`。
本站不代為決定模型（那會是在錯的單元做一個會綁住另一個單元的決定），
亦不把它當成已解決。

### 〇之二、`NFR3` 與本單元的關係：本單元在它的預算內，但不是主要消耗者

`NFR3` 逐字：「**P50 ≤ 2 秒**（從使用者送出到畫面出現第一個字）」，
且逐字說明「這條預算幾乎全部被**路由層的 LLM 呼叫**吃掉。FR4 的 Redis 往返在
同一個 compose 網路內約 1ms，可忽略」。

**但 `NFR3` 的原文沒有提到記憶檢索**。而本單元的 `search` 確實在那條路徑上：
`K-10` 讓 `U11 intent-router` 在分類時讀語意與程序記憶。
故本單元需要一個自己的延遲預算，而上游沒有給——見 `[N1]`。

---

## 一、`[N1]` 記憶檢索在 `NFR3` 預算內的延遲切片是多少？

### 查證到的事實

| 查證項 | 結果 |
|---|---|
| `NFR3` 的門檻 | P50 ≤ 2 秒，伺服器端計時，不含使用者網路往返 |
| `NFR3` 原文是否提到記憶檢索 | **沒有**——只點名路由層 LLM 呼叫與 Redis 往返 |
| 本單元是否在該路徑上 | **是**：`K-10` 讓 `U11` 在分類時經 `MemoryFacade.search` 讀記憶 |
| 檢索的組成 | ① 經 `U6` 取查詢向量（Ollama HTTP 或 fastembed 行程內）② 一次資料庫相似度查詢 |
| `U6` 的向量產生延遲是否已有目標 | **未查到**；`K-06` 定的是介面與失敗行為，非延遲 |

**沒有這個切片，`NFR3` 在本單元是不可驗的**：量測落點（`build-and-test`）會
量到端到端 2 秒，但無法判定記憶檢索是否超出它應占的份額。

### 選項

| 選項 | 做法 | 代價與後果 |
|---|---|---|
| **A（建議）** | **給一個明確的伺服器端切片：`search` 的 P95 ≤ 150ms，且不含 `U6` 的向量產生時間**（後者單獨列為 `U6` 的義務並記為交接） | 二元可判、可在 `build-and-test` 以伺服器端計時驗證。切開向量產生是刻意的——它的延遲由提供者決定（Ollama 服務 vs 行程內 fastembed 差異大），把兩者綁在一個數字裡會讓這條需求在換提供者時無聲失效。150ms 是**工程判斷而非實測**，必須如實標記（同 `NFR1` 的 80% 與 `FR1.7` 的 0.7，上游已記載兩者「沒有實證基礎」） |
| **B** | **給整段切片（含向量產生）：端到端 P95 ≤ 500ms** | 單一數字，量測簡單。但它把兩個不同提供者的差異吃進同一個門檻：fastembed 行程內與 Ollama 跨容器的差距可能就占掉大半，於是這條需求實際在量的是「用了哪個提供者」而不是「檢索夠不夠快」 |
| **C** | **不設獨立切片**，只在 `NFR3` 的端到端門檻下量測 | 零新門檻、不製造無實證基礎的數字。但本單元因此**沒有任何可驗的效能需求**，而它在 `NFR3` 的關鍵路徑上；一旦 `NFR3` 超標，沒有機制能指出是不是記憶檢索造成的 |

[Answer]: B 端到端 P95 ≤ 500ms，含向量產生
<!-- 作答時間見下一行的原註記；本答案已於 2026-10-09T08:38:21Z 被 supersede，見下方 §一之一 -->
<!-- 作答時間 2026-10-08T23:46:29Z，以 `date -u` 取值 -->

### 1.1 `[N1]` 的作答已被取代為 **A**（2026-10-09T08:38:21Z）

**原作答 B 與選項本文皆不改寫**，保留以供追溯——「B 曾被選過」本身是下游判斷
可信度的依據（`project.md` 的既有教訓）。

**取代的原因是新證據，不是重新偏好**：審查 `R-01`（Major）查出
**所有測試場地都沒有 Ollama**，而 B 的全部理由就是要把 Ollama 的跨容器延遲
含進門檻：

| 查證 | 逐字內容 |
|---|---|
| `deploy/docker-compose.test.yml:18` | 「**NO ollama. EMBEDDING_PROVIDER is `stub`** instead」 |
| `deploy/docker-compose.test.yml:102` | `EMBEDDING_PROVIDER: ${EMBEDDING_PROVIDER:-stub}` |
| `backend/.env.example:120` | `EMBEDDING_PROVIDER=fulltext`（該模式**不產生向量**），且其上方註解逐字「要真的驗記憶檢索時改成 fastembed（**不是 ollama**）」 |
| `.github/workflows/ci.yml` 的 `ollama` 命中數 | **0** |
| `.github/workflows/deploy.yml` 的 `ollama` 命中數 | 12（**只在部署後的 staging 路徑**） |

**後果**：B 之下 `build-and-test` 會以 `stub`／`fulltext` 量出近乎 0 的 P95、
`NFR3.20` 穩定通過，而 `NFR3.21` 會忠實記錄「提供者＝stub」並視為已驗證
——**一個結構性的橡皮章**。這正是審查 `R-01` 的 required action 所指的情形，
其中逐字建議「改回選項 A，把向量產生時間切出去」。

**使用者裁決：改回 A。**

[Answer]（取代後）: A `search` 本體 P95 ≤ 150ms，不含向量產生
<!-- 作答時間 2026-10-09T08:38:21Z，以 `date -u` 取值；取代上方的 B -->

---

## 二、`[N2]` 相似度檢索沒有向量索引——要不要補，補哪一種？

### 查證到的事實（本站最重要的一項發現）

`U5` 已交付的 `memory_records` 有**三個**索引：`ix_memory_records_owner_user_id`、
`ix_memory_records_expires_at`、`ix_memory_records_embedding_model`。

**沒有任何向量索引。** 全檔 `ivfflat`／`hnsw` 命中數為 **0**。

| 後果 | 說明 |
|---|---|
| 每次相似度檢索 | 對候選集合**逐列**計算距離（sequential scan ＋ exact distance） |
| 正確性 | **不受影響**——沒有索引的 pgvector 查詢回的是精確最近鄰，不是近似解 |
| 效能 | 隨列數線性退化。而本單元的列數由 `U13` 每輪對話寫 episodic 決定（`BR7.1`），**會持續成長**，上界是 90 天的累積量 |
| 既有過濾是否幫得上 | 部分：`BR2.2`（可見範圍）與 `BR3.2`（`embeddingModel`）會先收斂候選集合，而 `ix_memory_records_embedding_model` 可用於後者 |
| 為什麼 `U5` 沒建 | `U5` 的索引註解逐字說明它為 `expires_at`（清除）與 `embedding_model`（`BR3.1` 的過濾）建索引；**向量索引不在它的 `BR` 清單內**，不是疏漏被記載過 |

**這是跨單元缺口**：索引屬 `U5` 的 schema（**已交付**），而需要它的是本單元。

### 選項

| 選項 | 做法 | 代價與後果 |
|---|---|---|
| **A（建議）** | **本站只定下可量測的效能需求與其退化門檻，不在本輪新增索引**：明定「在 N 列以下，`search` 滿足 `[N1]` 的延遲切片」，並把 N 實測出來寫進需求；超過 N 時才需要索引，且把「加索引」列為具名的、附觸發條件的交接項指向 `U5`／後續 intent | 不動已交付的 schema（避免 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步），而效能需求仍然可驗。**關鍵是 N 必須實測而非猜**——否則這條需求與沒有一樣。誠實記載：本輪不加索引是**接受一個會隨使用量成長的風險**，而非宣稱不需要 |
| **B** | **本輪要求加 HNSW 索引**，落點 `U5` 的 schema | 效能問題一次解決，且 HNSW 不需要訓練資料（可在空表上建立）。代價：改動**已交付**的 `schema_rbac.sql` → 觸發 blocking 的 `DEPLOY.md` 同步 ＋ `run_meta_schema_migration.py` 的後條件清單（`EXPECTED_INDEXES`）必須同步，否則該腳本會在一個其實正確的資料庫上 rollback。另：HNSW 建索引的記憶體與時間成本在 staging 的 RAM 餘裕下未經評估 |
| **C** | **要求加 ivfflat 索引** | 比 HNSW 省記憶體。但 ivfflat **需要先有資料才能有意義地建立**（`lists` 參數依列數決定，空表上建的索引品質差且需重建），而本輪的 `memory_records` 是空表——等於要求一個現在無法正確執行的動作 |

[Answer]: B 本輪加 HNSW 索引
<!-- 作答時間 2026-10-08T23:46:29Z，以 `date -u` 取值 -->
