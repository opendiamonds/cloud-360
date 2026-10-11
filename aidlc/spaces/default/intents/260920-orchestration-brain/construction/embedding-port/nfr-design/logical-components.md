# Logical Components — `U6 embedding-port`（`library`）

<!-- Stage: nfr-design（Construction 3.3）· Unit: embedding-port · kind: library -->

> 本檔是 NFR 設計與 `infrastructure-design`（3.4）之間的橋：它給出**元件層級**的視圖
> ——邊界在哪、失敗域有幾個、爆炸半徑多大、誰和誰共用資源。

**本單元是 `library`，沒有自己的行程、容器或端點。** 所以下面的「元件」是
**模組邊界**，不是部署單位；而「失敗域」討論的是**它依賴的東西壞掉時會怎樣**，
不是它自己會不會掛。

## 一、邏輯元件清單

| 元件 | 性質 | 責任 | 執行位置 |
|---|---|---|---|
| `ProviderResolver` | 啟動期函式 | 讀四個環境變數 → 驗證（`BR1.1`／`BR1.3`／`NFR7.1`）→ 回傳 `ProviderSelection` 或拋。**冪等、無副作用、不建連線、不載模型**（`D-2`） | backend 行程，startup hook 內（`D-1`） |
| `EmbeddingPort`（介面） | 介面 | 兩個方法 `embed`／`model_id`（K-06） | — |
| `OllamaAdapter` | 實作 | 以既有 `httpx` 對 `OLLAMA_BASE_URL` 發請求，帶具名常數 timeout（`D-6`） | backend 行程；**外部呼叫** |
| `FastembedAdapter` | 實作 | 行程內 ONNX 推論，lazy import（`BR6.1`） | **backend 行程內**；無外部呼叫 |
| `StubAdapter` | 實作 | `hashlib` 決定性展開為 1024 float（`D-3`） | backend 行程；純函式 |
| （無 `FulltextAdapter`） | — | `fulltext` ⇒ 選擇器回空（`D-10`），不存在對應實作 | — |

## 二、失敗域

| 失敗域 | 範圍 | 誰在裡面 | 本單元的位置 |
|---|---|---|---|
| **F1：ollama 容器** | compose 內部網路的第 6 個服務 | 只有 ollama 自己 | 本單元是它的**唯一消費端**（K-01 的四個變數 `consumed_by: [U6]`）。它掛了只影響經本 Port 的呼叫 |
| **F2：backend 行程** | 整個 backend 容器 | 全部 router、service、本 Port | `FastembedAdapter` 在**這個域內**做推論——見第四節的共用資源 |
| **F3：模型快取 volume** | ollama 的模型存放 | ollama | 間接：模型未就位時 `ollama` 的呼叫會失敗，表現為 `EmbeddingProviderUnavailable` |

**本單元自己不構成一個失敗域**——它沒有行程、沒有連線池、沒有背景工作。
它的失敗一律是上面三者之一的轉譯。

## 三、爆炸半徑

| 事件 | 直接後果 | 波及範圍 | 不會波及 |
|---|---|---|---|
| ollama 服務掛掉（`EMBEDDING_PROVIDER=ollama`） | 每次 `embed` 在 timeout（預設 10 秒）後拋 `EmbeddingProviderUnavailable` | `U8` 的記憶寫入與相似度檢索；間接波及 `U11` 的意圖判定（它讀記憶輔助判定）→ **首字回應路徑**（`NFR3.1`／`RR-4`） | 不影響任何非記憶路徑：既有的 A1／A3／Lens／RBAC／架構圖全部無感——本 Port 不在它們的呼叫鏈上 |
| `EMBEDDING_PROVIDER` 設錯 | **backend 拒絕啟動**（`D-1`、`BR1.6`） | 整個服務 | —（這是刻意的：大聲失敗優於靜默降級，ADR-008） |
| `fastembed` 未安裝但被選中 | 首次 `embed` 拋 `EmbeddingProviderUnavailable`，訊息含安裝指令（`BR4.3`） | 同第一列 | 僅本機開發；三個環境中只有「本機且無 Ollama」會選它 |
| 輸入超長 | **不是失敗**——截斷 ＋ WARN（`D-4`） | 該筆記憶的檢索品質靜默下降 | 不中斷任何流程 |

**爆炸半徑的上界是「記憶相關的一切」，下界是零。** 這條界線成立的理由是
`SEC-1`：本 Port 不讀 DB、不碰授權、無 HTTP 入口，所以它沒有任何方式影響
它的呼叫鏈之外的東西。

## 四、共用資源與噪音鄰居

| 資源 | 共用者 | 風險 | 處置 |
|---|---|---|---|
| **backend 行程的 CPU／RAM** | 全部 router 與 service，**＋ `FastembedAdapter` 的行程內推論** | **`fastembed` 做的是 ONNX 推論，會在 backend 行程內吃 CPU 與記憶體**，與請求處理競爭。這是本檔新指出的一項 | **只影響本機開發**——`deploy/.env.example:116` 為 `ollama`、`docker-compose.test.yml:18` 為 `stub`，兩者都不在行程內推論。已具名為本機限定的取捨，不新增機制 |
| **ollama 容器的 CPU／RAM** | 只有 ollama | 模型載入約需 2GB RAM（`K-01` 註記「此兩數字為一般認知，domain-design 已標明**未在 staging 主機實測**，且 `DEPLOY.md`／`LOCAL-DEV.md` 未記載該主機餘裕」） | **不在本單元**——容量屬 `U1` 與 `infrastructure-design`（3.4）。本檔只把「未實測」這個狀態如實轉述，不假裝它已被驗證 |
| **模型快取 volume** | ollama | 首次部署需 `ollama pull`（`deploy/.env.example:123` 逐字「模型**不會**因為容器啟動就出現」） | `U1` 已交付；本單元的 `BR1.5`（啟動不探測）正是為了不與這個順序衝突 |

## 五、隔離策略

| 隔離手段 | 有／無 | 理由 |
|---|---|---|
| Timeout | **有**（`D-6`，預設 10 秒） | 唯一的外部呼叫是 `ollama`；無 timeout 會讓記憶路徑無限期掛住 |
| Retry | **無**（`BR2.6`） | K-06 逐字「本 Port 自身不重試，重試次數上限由呼叫方依 `[C9]` 的上限設定」 |
| Circuit breaker | **無** | **刻意不加**：本 repo 零 circuit breaker 前例，加一個等於引入一套新的狀態機與其設定；而 `U8` 已持有重試上限，連續失敗時由它決定降級。若日後 ollama 的不穩定成為實測問題，落點是 `U8` 或 `observability-setup`，不是一個 library 單元 |
| Bulkhead／連線池隔離 | **無** | `httpx` 的預設連線池即可；本 Port 是唯一使用 `ollama` 的呼叫者，沒有第二個競爭者需要隔離 |
| 降級（fallback） | **明文禁止** | ADR-008 Decision 逐字「不得靜默降級為全文檢索」。這是本單元**唯一一條禁止彈性模式**的地方，理由是降級會讓「為什麼找不到我的記憶」變成無法除錯的問題 |

**「無」的四項都是決定，不是遺漏**——每一項都有理由，且理由都指向
「本 repo 沒有該機制的前例，引入它是基礎設施決策」或「上游契約已指定由呼叫方承擔」。

## 六、交給 `infrastructure-design`（3.4）的事

| # | 事項 | 為什麼不在本站 |
|---|---|---|
| 1 | ollama 容器的 CPU／RAM 配額與 staging 主機餘裕的**實測** | 容量規劃屬基礎設施層；`K-01` 已標明那兩個數字未實測 |
| 2 | 模型快取 volume 的大小與保存策略 | 同上 |
| 3 | `H-N2`：telemetry 基礎設施（`/metrics`） | 見 `security-design.md §五`；該站為 `observability-setup`（4.4，**CONDITIONAL**），被 skip 時判定者須重新提交使用者 |
