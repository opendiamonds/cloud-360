# NFR Design 問題檔 — `U6 embedding-port`

> Stage：`nfr-design`（3.3）　Unit：`U6 embedding-port`（`library`，M）
> Depth：**Minimal**　Review：advisory（1 輪）　建立時間：2026-10-04　作答完成：2026-10-04T22:25:22Z（`date -u` 取值）
>
> `produces_kinds` 把 performance／scalability／reliability／observability 四項 design
> 排除在 `library` 之外，故本站只產出 `security-design.md`、`logical-components.md`、
> `traceability.json` 三件。

---

## 〇、已定案、**不重問**

| 已定案 | 出處 |
|---|---|
| 四個提供者、無預設、大聲失敗、`fulltext` ⇒ 無 Port | ADR-008；`functional-design [Q1]`／`[Q3]` |
| `model_id` 回模型身分；雙向一致性測試 | `functional-design [Q2]` |
| `fastembed` 選用、lazy import | `functional-design [Q4]` |
| 設定在啟動時驗、連線性在首次 `embed` 驗、**啟動時不探測** | `functional-design [Q3]`=A（`BR1.5`） |
| 明文 HTTP 為具名殘餘風險；主機名須為 compose 內部服務名 | `nfr-requirements [Q1]`=A（`NFR7.1`–`NFR7.3`） |
| timeout 具名常數、預設 10 秒、可覆寫 | `nfr-requirements [Q3]`=A（`NFR3.2`） |
| 換模型偵測落點在 `U8`，不在本單元 | `nfr-requirements [Q2]`=A（`U8-1`） |

## 〇·二、出題前的唯讀查證（**非來源**）

- `backend/main.py:48-52`：`@app.on_event("startup")` 依序呼叫 `configure_provider_env()`
  與 `init_db()`。
- `backend/services/llm_provider.py:90-98` `configure_provider_env()` 的 docstring 逐字：
  「Safe to call repeatedly; both the startup hook and each request call it.
  Calling `get_provider()` here (rather than ignoring it) is what makes a retired or
  invalid setting visible **in the logs** at startup.」——**它記 log，不讓啟動失敗**。
  這是本 repo 唯一的「provider 設定解析」前例，而本單元的 `BR1.6` 要求**失敗即終止啟動**，
  兩者形狀不同（`BR1.6` 已核可，本站不重開；但落點選擇要知道這個前例）。
- `backend/tests/helpers.py:43` 的註解指出 **`TestClient` 在另一個執行緒裡跑 app**；
  既有測試以 in-memory SQLite 運作，**不設定任何 embedding 環境變數**。
- **零 telemetry 基礎設施**：全樹無 `prometheus`／`statsd`／`opentelemetry`。
  可觀測性目前只有 `logging`。
- `backend/database.py:199-231` `_ensure_vector_extension()` 失敗只 `logger.warning`
  （`:214-217` 寫明那是刻意的，把大聲失敗留給下游 `create_all()`）。

---

## Q1 啟動驗證放在哪裡、什麼時候跑

`BR1.1`／`BR1.3`／`NFR7.1` 都在啟動時驗證設定並在不通過時**終止啟動**（`BR1.6`）。
但「啟動時」在這個 codebase 有四個不同的落點，而它們對**測試基礎設施**的影響差很多
——既有 `backend/tests/` 完全不設定 embedding 環境變數。

- **A（建議）— 新增一個與 `configure_provider_env()` 並列的函式，由 `main.py` 的
  startup hook 呼叫。** 形式沿用既有前例的位置（`main.py:48-52` 那個 hook），
  但行為依 `BR1.6` 為**失敗即拋**而非只記 log——此差異在 `security-design.md` 明記。
  好處：`TestClient(app)` **不觸發** startup hook（`team.md` 的既成事實），
  所以既有測試不需要設定任何 embedding 變數即可繼續跑；而真實啟動會驗。
  代價：`main.py` 多一行；且「驗證有沒有真的跑」只能靠啟動測試，不能靠單元測試。
- **B — 放在 Port 模組的 import 時（module-level）。** 最不可能被漏跑。
  代價：**會打斷既有測試**——任何 import 到該模組的測試都需要合法的 embedding 環境變數，
  而 `backend/tests/` 目前一個都沒設。這是 **49** 個測試檔的連帶改動（實算；問卷初稿寫「21」是沿用 `team.md` 的過時數字，**已於作答後更正**——選項 B 的代價因此比提問當下所述更大，而定案為 A，結論不受影響）。
- **C — 放在選擇器首次被呼叫時（lazy）。** 零啟動路徑改動。
  代價：**與 `BR1.6`「終止啟動」直接矛盾**——沒有被呼叫就不會驗，一個打錯字的
  `EMBEDDING_PROVIDER` 可以讓服務一直跑到第一次用記憶才爆。
- **D — 直接寫在 `main.py` 的 startup hook 內聯。** 少一層間接。
  代價：驗證邏輯離它所屬的模組很遠，且無法被單元測試直接呼叫；
  `team.md` 的三層形狀偏好把邏輯放在模組內、入口只負責呼叫。

[Answer]: A

## Q2 `stub` 的向量怎麼產生

`stub` 要「決定性」（`BR2.3`）且「恰 1024 維」（`BR2.2`），但**沒有任何已核可文件
說它的向量之間要不要可區分**。這不是美學問題：若所有輸入都映射到同一個向量，
`P1`–`P3`、`P6` 全部會過，而 `U8` 用 `stub` 寫的任何「相似度檢索」測試都會變成恆真
——每一列的距離都相同。

- **A（建議）— 由輸入文字的雜湊決定性展開，使不同輸入得到不同向量。**
  形式：`hashlib` 的摘要擴展為 1024 個 float。保證 (i) 同輸入同輸出（`P3`）、
  (ii) **不同輸入幾乎必然不同向量**，使 `U8` 能寫出有意義的相似度測試。
  明記**它不具語意**——相近的句子不會得到相近的向量，所以 `stub` 不能用來驗
  「語意相似度排序正確」，只能驗「分群與過濾的機制正確」。
  代價：需要在 `security-design.md` 寫明這條界線，否則下游會拿 `stub` 驗語意。
- **B — 固定常數向量（例如全 0.1）。** 最簡單。
  代價：見上——`U8` 的相似度測試全部恆真，而那正是 `construction.md` 禁止的
  「無論實作對錯都會通過」的測試。
- **C — 以固定種子的偽隨機產生，與輸入無關。** 決定性但與輸入脫鉤。
  代價：同 B，不同輸入得到同一個向量。
- **D — 讓 `stub` 產生**語意上**近似的向量（例如以字元重疊度為基礎）。
  能驗語意排序。代價：那等於在測試替身裡重新實作一個簡易 embedding 模型
  ——替身的複雜度超過它要替代的東西，且它自己會需要測試。

[Answer]: A

## Q3 `U8` 怎麼分辨「提供者不可用」與「這批輸入有問題」

K-06 的 `raises` 只宣告一個例外 `EmbeddingProviderUnavailable`。但失敗有兩種性質
完全不同的來源：**提供者掛了**（重試有意義）與**這批輸入本身有問題**
（例如超過模型的 context 長度——重試一萬次也一樣）。`BR2.6` 說本 Port 不重試、
重試上限由呼叫方設定——而呼叫方若無法分辨這兩者，就只能一律重試或一律不重試。

- **A（建議）— 本 Port 負責讓超長輸入不成為錯誤：在送出前截斷到模型上限，
  並在截斷發生時記一條 WARN（含被截掉的字元數），不拋例外。**
  其餘失敗一律 `EmbeddingProviderUnavailable`，維持 K-06 的單一例外契約不變。
  理由：截斷是 embedding 層的標準做法，而「要不要截斷」不該是每個呼叫端各自決定的事；
  且這讓 K-06 的契約不需要修訂。代價：截斷會**靜默降低**該筆記憶的檢索品質
  ——WARN 是唯一的可見訊號，必須在 `security-design.md` 明記它是具名的取捨。
- **B — 新增第二個例外型別（如 `EmbeddingInputRejected`）。** 語意最清楚。
  代價：**修改 K-06 已核可的 `raises` 清單**——那是契約變更，須回 `contract-design`，
  不該由本站逕自做（`functional-design` 的 `H-E3` 已有一個同形的待決項）。
- **C — 不處理，超長輸入就讓它變成 `EmbeddingProviderUnavailable`。**
  零新增。代價：`U8` 會對一個永遠不會成功的輸入一直重試到上限，
  而錯誤訊息會說「提供者不可用」——那是假的，提供者好好的。
- **D — 把長度檢查推給 `U8`**，由呼叫方保證輸入不超長。
  代價：模型的 context 上限是**提供者的屬性**（`bge-m3` 與 `multilingual-e5-large`
  不同），而 `U8` 看不到提供者細節——它只拿到一個 Port。這會逼 `U8` 去知道
  它不該知道的事。

[Answer]: A

## Q4 本單元要吐什麼可觀測性訊號

**實測：本 repo 零 telemetry 基礎設施**（全樹無 `prometheus`／`statsd`／`opentelemetry`），
可觀測性目前只有 `logging`。`BR7.1` 已定「啟動時記一條含 provider／model 的 INFO」。
問題是 design 層要不要再加。

- **A（建議）— 只用 `logging`，但把「什麼情況記什麼等級」定死。**
  啟動解析 INFO（`BR7.1`）；截斷 WARN（Q3=A）；`EmbeddingProviderUnavailable`
  由**呼叫方**記 ERROR（本 Port 只拋，不自己記 ERROR——否則同一個失敗會被記兩次）；
  **不**記每次 `embed` 的成功（那會在每次記憶寫入都產生一行）。
  理由：零基礎設施之下，引入 metrics 是基礎設施決策，不該由一個 library 單元夾帶
  （與 `team.md` 拒絕前端測試框架的理由同形）。代價：**無法回答「embed 的 P50 延遲是多少」**
  ——而 `RR-4` 正好說 `NFR3` 的這一段沒有自動化斷言。此缺口維持具名開放。
- **B — 加一個行程內的計數器／計時器（純 Python，不新增依賴），由既有端點暴露。**
  能回答延遲問題。代價：需要一個暴露端點，而本單元 `SEC-1` 明文「不得新增任何 HTTP 入口」
  ——這會與本單元自己的安全需求衝突。
- **C — 引入 `prometheus-client` 並加 `/metrics` 端點。** 最完整。
  代價：新依賴 ＋ 新端點 ＋ 新暴露面，三者都超出一個 library 單元的範圍，
  且 `SEC-1` 同樣禁止新端點。這是 `observability-setup`（4.4）的工作。
- **D — 連啟動的那條 INFO 都省掉。** 代價：直接違反已核可的 `BR7.1`，
  且「這個行程跑的是哪個模型」會變成只能靠讀設定推斷——那正是 `embeddingModel`
  分群出問題時第一個要問的事。

[Answer]: A（修訂，見下方註記）

> **Q4 的作答經過一次更正，如實記載。** 初答為 **C**（引入 `prometheus-client` 與 `/metrics`）。
> 依 `project.md`「使用者選的選項會製造新的正確性問題時，說出具體理由並請其重選」，
> 我指名了四件會壞掉的事：
> ① **直接違反本單元上一站已核可、且通過審查的 `SEC-1`**（逐字「不得新增任何 HTTP 入口」，
>    其驗證方式是「FastAPI router 裝飾器 grep 結果須為零」）；
> ② `/metrics` 慣例上**無認證**，而本 app 經 Cloudflare Tunnel 對外為 `cloud360.danniel.cc`
>    ——會把運維內部狀態推上公開網際網路。本 repo 已有同形前例（`U3` 查出 `/roles/catalog`
>    是無認證的公開端點）；
> ③ 新增依賴與同單元已核可的 `tech-stack-decisions.md` 逐字「`backend/requirements.txt` 的
>    淨變更：零」矛盾；
> ④ ADR-0006 的 **network exposure** 面會由「本單元不新增對外端點」整個翻轉，須重判。
>
> **但選 C 背後的需求是對的**——目標是能回答 `embed` 的延遲，而那正是 `RR-4` 標為缺口的東西。
> 重選後的答案是**原選項 A 加上一處實質強化**，故記為「A（修訂）」而非單純的 A：
>
> | | 原選項 A | 實際定案（A 修訂） |
> |---|---|---|
> | 啟動解析 | INFO（`BR7.1`） | 同 |
> | 截斷 | WARN（Q3=A） | 同 |
> | `EmbeddingProviderUnavailable` | 由呼叫方記 ERROR，本 Port 只拋 | 同 |
> | **每次 `embed`** | **不記**（原文逐字「**不**記每次 `embed` 的成功」） | **改為必記一條結構化 INFO**：`provider`、`model_id`、批次大小、耗時毫秒 |
> | metrics／端點 | 無 | 無（維持零端點、零依賴） |
>
> 這一處改動是整個重選的實質內容：延遲變成可從 log 事後統計（一條 `awk` 即可得 P50／P95），
> 而不需要任何端點或依賴。代價是每次記憶寫入都會多一行 log——比原 A 寬，已明記。

