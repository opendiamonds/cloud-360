# 效能需求 — `U8 memory-service`

> 本單元在 `NFR3`（首字回應時間 P50 ≤ 2 秒）的關鍵路徑上，但**不是主要消耗者**
> ——`NFR3` 逐字說明該預算「幾乎全部被路由層的 LLM 呼叫吃掉」。
> 本檔給本單元自己的切片，因為上游沒有給（見問題檔 `[N1]`）。

## 〇、上游依據

| 上游 | 本檔用到它的什麼 |
|---|---|
| `inception/requirements-analysis/requirements.md` `NFR3` | P50 ≤ 2 秒、伺服器端計時、不含使用者網路往返、量測落點 `build-and-test` |
| `construction/memory-service/functional-design/functional-spec.md` | §1.2 檢索流程的七個步驟（本檔的量測邊界即其步 1 到步 7） |
| `construction/memory-service/functional-design/rules.md` | `BR3.1`（三種皆可取）、`BR3.2`（`embeddingModel` 分群）、`BR2.2`（可見範圍過濾） |
| `inception/contract-design/contract-summary.md` | `K-08` 的 `MemoryFacade.search`；`K-10`（`U11` 在分類時讀記憶）；`K-06`（EmbeddingPort） |
| `schema_rbac.sql`（版控） | `memory_records` 的三個既有索引與**向量索引的缺席** |
| 本站問題檔 `[N1]`=B、`[N2]`=B | 延遲切片的定義與向量索引的決定 |

## 一、效能需求

| id | 需求 | 二元判準 | 來源 |
|---|---|---|---|
| **`NFR3.20`** | `MemoryFacade.search` **本體**的 P95 ≤ **150ms**，**不含**經 `U6 EmbeddingPort` 產生查詢向量的時間 | 伺服器端計時「取得查詢向量之後 → 回傳」的 P95；量測落點 `build-and-test` | `[N1]`=**A**（修訂，見 §二） |
| **`NFR3.21`** | `NFR3.20` 的門檻在被宣稱達成之前，必須有一次**實測**，且該量測須記錄當時的 `memory_records` **列數** | 量測報告同時含兩者：P95 數值、列數。缺任一項則該門檻視為**未驗證**。**不再要求記錄提供者**——向量產生已切出 `NFR3.20` 的範圍 | 本站（見 §二） |
| **`NFR3.22`** | 相似度檢索必須實際**使用**向量索引，不得退化為循序掃描 | 對代表性查詢取 `EXPLAIN`，計畫中出現該 HNSW 索引的掃描節點；出現 `Seq Scan` 即不通過 | `[N2]`=B（見 §三） |
| **`NFR3.23`** | 列出路徑（`GET /api/memory/records`，三區分頁）的 P95 ≤ **300ms** | 伺服器端計時；該路徑**不做相似度**（`BR3.2` 不適用，見 `functional-spec.md §1.3`），故不含向量產生 | 本站 |
| **`NFR3.24`** | 相似度排序在**分數相同**時必須有決定性的次級排序鍵 | 同一組輸入連續兩次呼叫回**完全相同的順序**；可以兩筆人造的同分列直接斷言 | 本站（見 §五） |

### 1.1 `NFR3.24` 本質是正確性而非效能，列在本檔是因為它屬排序行為

分數相同時若無次級鍵，同一組輸入在兩次呼叫之間可能回不同順序，
而**那在畫面上與「功能壞了」無法區分**——使用者看到記憶順序跳動，
而沒有任何錯誤訊息。

repo 內已有正解可抄：`backend/cost/estimate_readers.py:247-251` 的
`key=lambda item: (-item[1], item[0])`（先分數遞減、再以識別字遞增）。
它同時是本單元**唯一**適合 property-based 測試的落點
（見 `security-requirements.md` 的 PBT 判定與 `N8-7`）。

## 二、`[N1]` 由 B 改為 A（2026-10-09T08:39:06Z）：審查 `R-01` 查出 B 結構性不可驗

### 2.1 原本選 B，而 B 的全部理由被證明在本 repo 無法實現

`[N1]` 原答為 B（端到端 ≤ 500ms，**含**向量產生）。
選 B 的理由是把 `ollama` 的跨容器延遲含進門檻，故 `NFR3.21` 原本要求
**記錄使用中的提供者**。

審查 `R-01`（Major）查出：**所有測試場地都沒有 `ollama`。**

| 查證項 | 逐字內容 |
|---|---|
| `deploy/docker-compose.test.yml:18` | 「**NO ollama. EMBEDDING_PROVIDER is `stub`** instead」 |
| `deploy/docker-compose.test.yml:102` | `EMBEDDING_PROVIDER: ${EMBEDDING_PROVIDER:-stub}` |
| `backend/.env.example:120` | `EMBEDDING_PROVIDER=fulltext`——該模式**不產生向量**（`BR3.3`） |
| 同檔上方註解 | 逐字「要真的驗記憶檢索時改成 fastembed（**不是 ollama**）」 |
| `.github/workflows/ci.yml` 的 `ollama` 命中數 | **0** |
| `.github/workflows/deploy.yml` 的 `ollama` 命中數 | 12——**只在部署後的 staging 路徑** |

**後果**：B 之下 `build-and-test` 會以 `stub`／`fulltext` 量出近乎 0 的 P95、
`NFR3.20` 穩定通過，而 `NFR3.21` 忠實記錄「提供者＝stub」並視為已驗證。
**那是一個結構性的橡皮章**——門檻永遠不會測到它存在的那個延遲。

### 2.2 使用者裁決：改回 A，並把 Ollama 的延遲交給 `U6`

| 項目 | 改後 |
|---|---|
| `NFR3.20` 的量測邊界 | **取得查詢向量之後 → 回傳**（資料庫查詢 ＋ 兩道過濾 ＋ 排序） |
| 為什麼這段可驗 | 它在 `stub` 之下**就是真實行為**——`stub` 只替換向量來源，不替換資料庫查詢、可見範圍過濾（`BR2.2`）、`embeddingModel` 分群（`BR3.2`）或排序 |
| Ollama 的 embedding 延遲 | **移出本單元**，成為 `U6 EmbeddingPort` 的義務。記為 `N8-11` |
| 150ms 的依據 | 仍是工程判斷而非實測，故 `NFR3.21` 的實測要求保留（但不再需要記錄提供者） |

### 2.3 本單元**不**負責的那一段

`NFR3` 的 2 秒預算中，路由層的 LLM 呼叫是主要消耗者（屬 `U11 intent-router`），
而向量產生自本次修訂起屬 `U6`。本檔的任何數字**都不構成對 `NFR3` 整體的保證**。
`NFR3` 與 `NFR10` 的連動見問題檔 §〇之一（`N8-1`）。

## 三、向量索引（`[N2]`=B）

### 3.1 本站查出的缺口

`memory_records` 有三個索引（`owner_user_id`、`expires_at`、`embedding_model`），
**沒有任何向量索引**（全檔 `ivfflat`／`hnsw` 命中數為 0）。
後果是相似度檢索對候選集合**逐列**計算距離。

正確性不受影響（無索引的 pgvector 回精確最近鄰），**退化的是效能**，
且隨列數線性成長——而列數由 `U13` 每輪對話寫 episodic 決定（`BR7.1`），
上界是 90 天的累積量。

### 3.2 `[N2]`=B 的決定與其連帶義務（**全部 blocking**）

決定：**本輪新增 HNSW 索引**。選 HNSW 而非 ivfflat 的理由已查證——
ivfflat 的 `lists` 參數依列數決定，而 `memory_records` **目前是空表**，
在空表上建的 ivfflat 品質差且需重建。

| # | 連帶義務 | 為什麼 blocking |
|---|---|---|
| 1 | `schema_rbac.sql` 的 `I)` 區塊新增該索引 | `project.md ## Mandated`：索引變更屬觸發條件 |
| 2 | `DEPLOY.md` 同步（新索引寫進「這支 SQL 會建立的表／欄位」區 ＋ 驗證指令） | 同上，blocking |
| 3 | `backend/scripts/run_meta_schema_migration.py` 的 `EXPECTED_INDEXES` 新增該索引 | 該腳本是既有環境取得 `I)` 區塊的唯一路徑；**它解析 `schema_rbac.sql` 的 `I)` 區塊**，故索引會被建立——但不加進後條件清單則**不會被驗證**（結束碼 0 的語意變窄而無人察覺） |
| 4 | `backend/scripts/verify_memory_schema.sql` 新增一條 `S` 斷言該索引存在且為 HNSW | `memory-schema` job 是記憶 schema 的唯一驗證載體 |

**本站不執行這四項**（它們是程式與結構變更，屬 `code-generation`）；
逐項列為交接事項 `N8-3`，承接站 `code-generation`（3.5，**ALWAYS**，在游標之後）。

### 3.3 `NFR3.22` 是本輪最容易無聲失效的一條

HNSW 索引的 **operator class 必須與查詢使用的距離運算子相符**，否則
**PostgreSQL 不會使用該索引**——查詢仍然正確、仍然回精確最近鄰，
只是退化為循序掃描，而**沒有任何錯誤或警告**。

| 若索引建為 | 則查詢必須用 |
|---|---|
| `vector_cosine_ops` | 餘弦距離運算子 |
| `vector_l2_ops` | L2（歐氏）距離運算子 |
| `vector_ip_ops` | 內積運算子 |

**故 `NFR3.22` 的判準是 `EXPLAIN` 計畫而非延遲數字**：延遲數字在空表或
小資料量下看起來一樣好，索引沒被用到要到資料長大之後才顯現。
這與 `BR3.2`（`embeddingModel` 分群）是同一個失敗家族——
型別、維度、查詢全部合法，結果或效能卻錯，且不報錯。

**opclass 與距離運算子的選定本站不預選**（它屬實作決定），
但要求兩者**在同一個 PR 內一致**並由 `NFR3.22` 的 `EXPLAIN` 斷言鎖住。
記為 `N8-4`。

### 3.4 `NFR3.22` 的判準前提（承審查 `R-02`，Major）

審查指出本站把「小資料量下看起來一樣好」這個現象**只用在警告延遲數字**，
卻沒有套用到自己選的 `EXPLAIN` 判準上：

**PostgreSQL 的 planner 是 cost-based 的，在候選列數很小時幾乎必定選
`Seq Scan`——即使 HNSW 索引建得完全正確。** 而 `memory_records` 目前是空表，
任何單元測試或 CI fixture 通常也只有個位數到幾十列。

故 `NFR3.22` 若直接在測試資料量下斷言「計畫中不得出現 `Seq Scan`」，
會產生**假性失敗**：索引正確卻判不通過。

**判準前提（`code-generation` 必須擇一實作）**：

| 做法 | 內容 |
|---|---|
| **A** | 斷言前把候選集合灌到足以讓 planner 傾向使用索引的規模（數百至數千列），再取 `EXPLAIN` |
| **B** | 以 `SET enable_seqscan = off` 隔離**opclass 正確性**這單一變數——此時若計畫仍不使用該索引，即證明 opclass 不符 |

**B 更貼近 `NFR3.22` 真正要防的事**（opclass 不符導致索引被靜默忽略），
且不需要大量 fixture；A 額外驗證了「planner 真的會選它」。
本站不預選，記為 `N8-12`。

## 四、資源與容量（非門檻，如實記載）

| 項目 | 現況 |
|---|---|
| 本單元新增的進程 | **零**——它是既有 FastAPI 進程內的 router ＋ service ＋ facade |
| 本單元新增的容器 | **零** |
| HNSW 索引的記憶體成本 | **未評估**。staging 的 RAM 餘裕在 `U5` 引入 Ollama（第 6 個服務）後已被動用過一次，而本站沒有該主機的可用記憶體數字。記為 `N8-5` |
| `memory_records` 的列數上界 | 由 90 天保存期（`FR4.5`）與每輪對話一筆 episodic（`BR7.1`）決定；**實際值取決於使用量，本站無基準** |
