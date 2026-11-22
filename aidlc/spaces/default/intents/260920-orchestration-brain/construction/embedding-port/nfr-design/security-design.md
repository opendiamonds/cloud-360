# Security Design — `U6 embedding-port`（`library`）

<!-- Stage: nfr-design（Construction 3.3）· Unit: embedding-port · kind: library -->

本檔把 `nfr-requirements` 的九條 `NFRx.y` 與四條 `SEC-*` 轉成**具體的設計決定**。
`produces_kinds` 把 performance／scalability／reliability／observability 四項 design
排除在 `library` 之外，所以那四類的設計決定落在本檔與 `logical-components.md` 兩處。

**本檔消費的上游（逐一開檔核對）**：`../nfr-requirements/security-requirements.md`
（`NFR3.1`–`NFR9.1`、`SEC-1`–`SEC-4`、`RR-1`–`RR-4`、第六節的交接表）、
`../nfr-requirements/tech-stack-decisions.md`（技術選擇表、改動面清單）、
`../functional-design/functional-spec.md`（§一 W1／W2、§二 狀態機、§五 PBT）、
`inception/contract-design/contract-summary.md`（`K-01`／`K-06`）。

**本單元沒有認證、沒有授權、沒有加密金鑰**——`SEC-1` 逐字禁止 HTTP 入口、DB 讀取與
授權判定。所以本檔的 security design 不是「設計一套認證流程」，而是**設計那三個「沒有」
怎麼被機械保證**，加上唯一一條真正的資料外流路徑（`ollama` 的明文傳輸）怎麼被補償。

## 〇·二、八個宣告上游的實際狀態（**四個不存在，且那是設計使然**）

stage 檔的 `Upstream targets` 宣告八個上游，但本單元是 `library`，
`nfr-requirements` 的 `produces_kinds` 把其中四個限定為 `[service]`／`[service, ui]`
——**它們對本單元從未被產出**。引擎自己解析給本站的 `consumes` 也只有四個
（`security-requirements`、`tech-stack-decisions`、`functional-spec`、`contract-summary`），
且未回報 `consumes_absent`，表示這是預期中的缺席而非缺口。

| 宣告的上游 | 本單元是否存在 | 本檔如何處理 |
|---|---|---|
| `security-requirements` | **存在** | 第一節逐條承接其 `NFRx.y` 與 `SEC-*` |
| `tech-stack-decisions` | **存在** | `D-6` 指回其 §二 的三處同步義務；本站維持「`requirements.txt` 淨變更：零」 |
| `functional-spec` | **存在** | `D-2`／`D-10` 承接其 §一 W1／W2 與 §二 狀態機；`D-3` 承接其 §五 的 PBT |
| `contract-summary` | **存在** | `D-4`／`D-6`／`D-8` 皆以 K-06 的 `raises`／`retry_and_idempotency` 為界 |
| `performance-requirements` | **不存在**（`produces_kinds: [service, ui]`） | 其內容在本單元由 `NFR3.1`／`NFR3.2` 承載，設計落點為 `D-5`／`D-6` |
| `scalability-requirements` | **不存在**（`produces_kinds: [service]`） | 本單元無行程、無連線池、無背景工作；擴展性議題落在 `logical-components.md §四`（共用資源）與 `U1`／`infrastructure-design` |
| `reliability-requirements` | **不存在**（`produces_kinds: [service]`） | 韌性決定仍然做了，落在 `logical-components.md §五`（timeout 有、retry／circuit breaker／bulkhead 皆**刻意無**，各有理由） |
| `observability-requirements` | **不存在**（`produces_kinds: [service]`） | 其內容在本單元由 `NFR3.1` 與 `BR7.1`／`BR7.2` 承載，設計落點為本檔第二節的四條規格 |

> **`upstream-coverage` sensor 一度紅燈，而本節是它變綠的原因——這一點必須講白。**
> 它回報那四個 `unreferenced`，因為本檔原本一個字都沒提到它們。
> **綠燈來自「缺席被寫下來了」，不是來自檔案出現了。** 那四份產出至今仍不存在，
> 而且不該存在。若有人日後把本單元改為 `service`，這張表就是該回來重讀的地方。

## 一、設計決定

| ID | 決定 | 承載的需求 | 可驗證方式 |
|---|---|---|---|
| `D-1` | **啟動驗證落在一個與 `configure_provider_env()` 並列的模組層函式**，由 `backend/main.py` 的 `@app.on_event("startup")` 呼叫（該 hook 現為 `configure_provider_env()` → `init_db()`，本函式插在兩者之間）。**行為依 `BR1.6` 為失敗即拋**，與前例只記 log 不同——此差異刻意且明記。 | `NFR7.1`、`NFR8.2`、`BR1.1`／`BR1.3`／`BR1.6` | `TestClient(app)` 不觸發 startup hook，故既有 **49** 個測試檔（`ls backend/tests/test_*.py | wc -l` 實算；`team.md ## Testing Posture` 寫的「21 個」為 HEAD `c3de2c8` 當時的數字，**已過時**）**不需**設定 embedding 變數；驗證本身以直接呼叫該函式的單元測試覆蓋 |
| `D-2` | 該驗證函式**必須冪等且無副作用**（只讀環境變數、回傳 `ProviderSelection`、失敗時拋）。它**不**建立連線、**不**載入模型（`BR1.5`）。 | `BR1.2`、`BR1.5` | 連續呼叫兩次結果相等；呼叫後不產生任何 socket 或檔案存取 |
| `D-3` | **`stub` 的向量由輸入文字的 `hashlib` 摘要決定性展開為 1024 個 float。** 保證同輸入同輸出，且不同輸入幾乎必然得到不同向量。**它不具語意**——相近句子不會得到相近向量。 | `BR2.3`、`P3`、`SEC-4` | `P3`（決定性）＋ 一條新斷言：兩個不同輸入的向量不相等 |
| `D-4` | **超長輸入由本 Port 截斷**到選定提供者的 context 上限，截斷時記一條 WARN（含被截掉的字元數），**不拋例外**。其餘失敗一律 `EmbeddingProviderUnavailable`，**K-06 的單一例外契約不變**。 | `[Q3]`=A；K-06 `raises` | 以超長輸入呼叫：回傳正常向量 ＋ `assertLogs` 捕捉到 WARN ＋ 未拋例外 |
| `D-5` | **可觀測性只用 `logging`，四條規格定死**（見第二節）。**零 metrics 依賴、零新端點。** | `NFR3.1`、`BR7.1`、`BR7.2`、`SEC-1` | 四條各有 `assertLogs` 測試；`requirements.txt` 淨變更仍為零 |
| `D-6` | timeout 為模組層**具名常數**，值取自環境變數、預設 10（秒），沿用 `LENS_AGENT_TIMEOUT_SEC` 的既有形狀。模組內**不得出現裸數字 timeout**。 | `NFR3.2` | `grep` 該模組不得有 `timeout=<數字>` 的字面值 |
| `D-7` | `EmbeddingProviderUnavailable` 攜帶三個欄位（`selectedProvider`／`target`／`availableOptions`），`target` 在組裝前**剝除 URL 的 `userinfo` 區段**。 | `SEC-2`、`BR4.1`、`BR4.4` | 以含 `user:pass@` 的 `OLLAMA_BASE_URL` 構造，斷言訊息不含密碼 |
| `D-8` | **本 Port 不自己記 `ERROR`**——拋出即交給呼叫方。理由：同一個失敗被 Port 與 `U8` 各記一次，會讓 log 上的錯誤數是真實數的兩倍，而 `U8` 才有判斷「這次失敗要不要降級」的上下文。 | `D-5`、`BR2.6` | 例外路徑的 `assertLogs` 不得捕捉到 ERROR |
| `D-9` | **`SEC-1` 的三條禁令以 import 面機械保證**：模組內 `grep` 不得出現 DB session 型別、RBAC 判定函式、FastAPI router 裝飾器。這與 `project.md` 對 cost 純函式層的可執行檢查同形。 | `SEC-1`、`BR2.7` | 一個讀取模組原始碼並斷言三者皆零命中的測試 |
| `D-10` | **選擇器回傳 `Optional`**（`fulltext` ⇒ 空）。`U8` 以「有沒有拿到 Port」分流，**不以例外分流**。 | `BR1.4`、`functional-design` `[Q1]`=A | `fulltext` 設定下選擇器回空、其餘三者回非空 |

## 二、可觀測性設計（`D-5` 的四條規格）

`nfr-design` 的 `observability-design.md` 不在 `library` 的 `produces` 內，所以這一節
就是本單元可觀測性設計的全部。**實測：本 repo 零 telemetry 基礎設施**
（全樹無 `prometheus`／`statsd`／`opentelemetry`），可觀測性只有 `logging`。

| # | 時機 | 等級 | 內容 | 為什麼是這個等級 |
|---|---|---|---|---|
| 1 | 啟動解析完成 | **INFO** | `providerName`、`modelId`（無 Port 時寫「無 Port（fulltext）」）、`endpoint` 的主機與埠（**不含 userinfo**） | `BR7.1` 已核可。少了它，「這個行程跑的是哪個模型」只能靠讀設定推斷 |
| 2 | **每次 `embed` 完成** | **INFO** | `providerName`、`modelId`、批次大小、**耗時毫秒** | **這是 `[Q4]` 重選後的實質新增**（原選項 A 逐字「**不**記每次 `embed` 的成功」）。它讓 `embed` 的延遲可由 log 事後統計出 P50／P95——一條 `awk` 即可——而不需要任何端點或依賴 |
| 3 | 輸入被截斷 | **WARN** | 被截掉的字元數、該筆的原長度與上限 | `D-4` 的截斷會**靜默降低**該筆記憶的檢索品質；WARN 是唯一的可見訊號 |
| 4 | 提供者不可用 | **不由本 Port 記** | — | `D-8`：拋出即交給呼叫方，避免同一個失敗被記兩次 |

**logger 命名**：`logging.getLogger("cloud360.<module>")`，依 `team.md ## Code Style`
的既成慣例（新模組一律此形式；既有 5 支用 `__name__` 的屬已知不一致，不效法）。

**明確不記的事**：請求內容（待向量化的文字）、向量值本身、任何憑證。
前兩者是使用者的對話內容，記進 log 等於在另一個地方複製一份記憶——
而 `NFR7` 正是在管這份資料的流向。

### 這一節誠實的部分

第 2 條讓延遲**可被事後統計**，但它**不是**自動化斷言——沒有任何 CI 檢查會因為
`embed` 變慢而紅燈。`RR-4` 標的缺口因此**縮小但未關閉**：從「連數字都拿不到」
變成「數字拿得到，但要有人去看」。真正的關閉需要 `build-and-test`（3.6）的量測機制，
與 `NFR1`／`NFR2`／`NFR3` 的落點相同。

## 三、唯一的資料外流路徑及其補償控制

```
使用者的對話文字
   │  (1) U8 讀出記憶文字，呼叫 EmbeddingPort.embed
   ▼
EmbeddingPort（本單元，行程內）
   │
   ├── stub      → 無外流（純函式）
   ├── fastembed → 無外流（行程內 ONNX 推論）
   └── ollama    → ★ 明文 HTTP 送到 http://ollama:11434（零認證）
                       │
                       ▼
                  ollama 容器（compose 內部網路，無 host port）
```

**★ 是本單元唯一把資料送出 backend 行程的那一步。** 它的補償控制有三層，
全部是**網段與設定層**而非傳輸加密（`[Q1]`=A 的定案）：

| 層 | 控制 | 誰交付 | 失效會怎樣 |
|---|---|---|---|
| 1 | 啟動時驗 `OLLAMA_BASE_URL` 主機名為 compose 內部服務名，不得為 `localhost`／`127.0.0.1`／公開 IP（`NFR7.1`、`D-1`） | **本單元** | 文字會被送到 compose 網路外的位址，而傳輸無加密 |
| 2 | ollama 服務不得 publish host port（`NFR7.2`） | `U1 brain-infra` | 零認證的 HTTP API 暴露到主機網段 |
| 3 | 例外與 log 不得含 `userinfo`（`SEC-2`、`D-7`） | **本單元** | 憑證（若未來該端點加上認證）進入 log |

**第 2 層不是本單元交付的，但本單元是該服務的唯一消費端**——所以它在這裡被
具名為依賴前提而不是別人的事。`RR-1` 的失效條件逐字記著「ollama 移出本主機、
被 publish port、或 compose 網路被其他非本 stack 的容器加入」。

## 四、ADR-0006 四面向逐項判定（**自檢第七項**）

每一格已與上游 `../nfr-requirements/security-requirements.md §五` 與 K-06 逐字比對。

| 面向 | 判定 | 與上游是否一致 | 本站**新增**的設計決定 |
|---|---|---|---|
| **IAM** | **不適用** | **一致**（K-06 `authorization_responsibility` 逐字「無」；`nfr-requirements §五` 判不適用） | `D-9`：把 `SEC-1` 的三條禁令變成 import 面的機械檢查，而不是一句宣告 |
| **Encryption** | **適用（一處）** | **一致**（`nfr-requirements §五` 判「適用（一處，且為本單元最重的一面）」） | 第三節的三層補償控制圖；`D-7` 的 `userinfo` 剝除 |
| **Network exposure** | **適用** | **一致**（`nfr-requirements §五` 判「適用」） | `D-1` 把主機名驗證釘在啟動路徑上；**`[Q4]` 重選後本站維持零新端點**——若當初採 `/metrics`，這一格會由「不新增對外端點」翻轉為「新增一個無認證的對外端點」 |
| **Audit logging** | **適用（弱→中）** | **一致但本站加強**（`nfr-requirements §五` 判「適用（弱）」） | 第二節把它由一條 INFO 擴為四條定死的規格，並明列**不記**什麼（請求內容、向量值、憑證） |

**PBT hard constraint**：**適用，落點仍是本單元**。本站新增一條可被 property 化的
斷言：`D-3` 的「不同輸入得到不同向量」。六個既有性質見
`../functional-design/functional-spec.md §五`，本站不重複定義。

## 五、本站未決、具名交出的事

| # | 事項 | 落點 | 為什麼不在本站 |
|---|---|---|---|
| `H-N1` | `embed` 延遲的**自動化斷言**（第二節只做到「可事後統計」） | `build-and-test`（3.6），與 `NFR1`–`NFR3` 的量測落點相同 | 需要量測基準與門檻，而本單元沒有可比較的基準 |
| `H-N2` | `/metrics` 與 telemetry 基礎設施（`[Q4]` 初答 C 的方向） | `observability-setup`（4.4，**CONDITIONAL**） | 新依賴 ＋ 新端點 ＋ 新暴露面，三者都超出 library 單元範圍且與 `SEC-1` 衝突。**該站被 skip 時，判定者須把它重新提交使用者**——`RR-3` 已有同形前例 |
| `H-N3` | 各提供者的 context 上限**實際值**（`D-4` 的截斷門檻） | `code-generation`（3.5，`ALWAYS`） | 是模型的屬性，需查該模型的實際規格；本站只定「必須截斷且必須 WARN」這個形狀 |
| `H-N4` | **timeout 環境變數的確切名稱**，與 `NFR8.1` 的三處同步義務（`deploy/render-env.sh` 寫它、兩個 `.env.example` 列它、`LOCAL-DEV.md` 同步）。本站只定了命名**形狀**（具名常數，沿用 `LENS_AGENT_TIMEOUT_SEC` 的形式），**未定名稱**——審查 `R-02` 指出這會讓一條 `project.md` 的 **blocking** 規則沒有具體掛載對象。建議名稱 `EMBEDDING_TIMEOUT_SEC`，由 `code-generation` 定案 | `code-generation`（3.5，**`ALWAYS`**） | 變數名一旦寫進 `render-env.sh` 就是部署契約的一部分；本站若逕自定名，`U1` 已交付的 env 契約會多出一個沒有經過 `contract-design` 的 key。落點是 `ALWAYS` 站，故不會像 `H-N2` 那樣有被 skip 的風險 |
