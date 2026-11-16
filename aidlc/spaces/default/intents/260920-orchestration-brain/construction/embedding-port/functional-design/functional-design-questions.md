# Functional Design 問題檔 — `U6 embedding-port`

> Stage：`functional-design`（3.1）　Unit：`U6 embedding-port`（`library`，M）
> Depth：**Minimal**　Test Strategy：Standard　Review：advisory（1 輪）
> 建立時間：2026-10-04　作答完成：2026-10-04T14:58:59Z（`date -u` 取值）

---

## 〇、已由上游定案、**不重問**的事項

每一項都能引用具體出處；引用不出來的就不在這張清單上（依 `scope-definition:260822-c5`）。

| 已定案 | 出處（逐字可查） |
|---|---|
| 四個實作及其名稱：`ollama`（bge-m3，staging）／`fastembed`（multilingual-e5-large，本機無 Ollama 時）／`fulltext`（退回 PostgreSQL 全文檢索）／`stub`（決定性替身，CI 用） | `decisions.md` ADR-008 Decision；`components.md:189-193` |
| 由 `EMBEDDING_PROVIDER` 環境變數切換，**刻意無預設** | `contract-summary.md` K-01 `EMBEDDING_PROVIDER` 的 `default: null` |
| 偵測不到選定提供者時**大聲失敗並列出可選值，不得靜默降級為全文檢索** | ADR-008 Decision（並註明「這一條是 domain-design 自行加上的約束」） |
| 向量欄位 `vector(1024)`；兩個向量提供者同維度故共用 | ADR-008 Decision；`components.md:194` |
| 每列記憶存 `embeddingModel`；相似度檢索**只比對同一 `embeddingModel` 的列** | ADR-008 Decision |
| `fulltext` 模式建立的列其向量為 `NULL`，之後不被向量檢索看到除非重新 embed | ADR-008 Consequences（負面）；`components.md:195-196` |
| 公開介面只有兩個方法：`embed(texts: Sequence[str]) -> list[list[float]]`（每個長度 1024）與 `model_id() -> str`，皆 `sync` | `contract-summary.md` K-06 `public_interface` |
| 本 Port **不碰授權、不讀 DB** | K-06 `behaviour_semantics.authorization_responsibility` 逐字「無——本 Port 不碰授權，亦不讀 DB」 |
| `embed` 為純函式語意（同輸入同輸出）；**本 Port 自身不重試**，重試上限由呼叫方依 `[C9]` 設定 | K-06 `retry_and_idempotency` |
| 四個實作的向量**不可互相比較**（同 1024 維但不同向量空間） | K-06 `vector_space`；ADR-008 Context 的「關鍵風險」 |
| property-based 測試是本單元的 ADR-0006 hard constraint 落點 | K-06 `pbt_note` 逐字「ADR-0006 的 property-based hard constraint 落點之一」；`unit-of-work.md:261` |
| 唯一指派的故事是 `US4.1`（`U6` 與 `U5`／`U8` 共享它） | `unit-of-work-story-map.md:52`、`:111` |

## 〇·二、出題前的唯讀查證（**非來源**，供題幹與選項引用）

- `grep -rn 'EMBEDDING_PROVIDER' backend --include='*.py'` → 只命中 `tests/test_render_env_redis.py` 的註解與常數名，**零個執行期讀取點**。`backend/env_bootstrap.py` 只做 `load_dotenv`，不驗任何變數。
- `deploy/.env.example:96` 逐字：「`EMBEDDING_PROVIDER` 缺值會讓 backend 拒絕啟動」（**現在式**）。`:114` 逐字：「required、**無預設**：偵測不到選定提供者時須大聲失敗，不得靜默降級。」
- `backend/.env.example:119` 本機預設為 `EMBEDDING_PROVIDER=fulltext`；`deploy/.env.example:116` 部署為 `ollama`；`deploy/docker-compose.test.yml:18` 逐字「NO ollama. EMBEDDING_PROVIDER is `stub` instead」。
- `backend/requirements.txt`：**無** `fastembed`、無 `ollama` 客戶端。`httpx` 已在（`ollama` 實作所需）。`fastapi`／`pydantic` 精確釘選，其餘未 pin、無 lockfile。
- `backend/database.py:199-231` `_ensure_vector_extension()` 已由 `U1` 交付：`CREATE EXTENSION IF NOT EXISTS vector`，**失敗只記 warning**，刻意把大聲失敗留給下游 `create_all()`。
- `components.md:432-434` 把「`embeddingModel` 合法值集合（2 個）與四個實作名稱（4 個）的一致性需要一個測試鎖住」逐字**指派本站**。

---

## Q1 `fulltext` 在 `EmbeddingPort` 介面裡的位置

K-06 宣告 `embed` 回傳「`list[list[float]]`，每個長度 1024」，而 ADR-008 同時說 `fulltext`
**不算向量**、其列的向量為 `NULL`。兩句話在型別層互斥：一個不產生向量的實作無法回傳
1024 維向量。這個落差必須在本站定案，否則 `U8` 會對一個它不知道會不會拋例外的方法寫呼叫碼。

- **A（建議）— `fulltext` 不是 `EmbeddingPort` 的實作，而是「沒有 Port」這個狀態。**
  `EMBEDDING_PROVIDER=fulltext` 時，選擇器回傳 `None`（或空 Optional），`U8` 以
  `if port is None` 走全文檢索分支。`embed` 的型別契約維持純粹（永遠回 1024 維），
  `model_id` 也不需要為它編一個值。代價：選擇器的回傳型別是 Optional，`U8` 多一個分支；
  且「四個實作」這個說法在型別上變成「三個實作 ＋ 一個停用狀態」，與 ADR-008 的用詞有落差
  （需在產出內明記這是用詞對齊，非推翻決定）。
- **B — `fulltext` 是實作，`embed` 對它一律拋 `EmbeddingNotApplicable`。**
  四個實作在型別上齊平，選擇器永不回 `None`。代價：`U8` 必須以 try/except 判斷模式，
  而「用例外表達正常的設定狀態」是本 repo `team.md` 明文要防的形狀
  （`try/except` 只用在外部依賴邊界）；且 PBT 對它無性質可驗。
- **C — `fulltext` 是實作，`embed` 回空 list（`[]`）表示「無向量」。**
  不拋例外、不回 `None`。代價：`[]` 與「真的沒有輸入文字」不可區分，而 `embed([])` 本身
  是合法呼叫——這正是 `domain-design:b43f793` 記過的「兩種 `null` 有語意差卻無區分者」。
- **D — `fulltext` 的 `embed` 回 1024 維全零向量。** 型別最單純。代價：全零向量會被
  pgvector 當成合法向量寫進欄位，於是「`fulltext` 模式的列向量為 `NULL`」這條
  已核可決定被違反，且全零向量與任何向量的 cosine 距離未定義／為 0，檢索會回垃圾而不報錯
  ——正是 ADR-008 存在的全部理由。

[Answer]: A

## Q2 `model_id()` 的值域，與「兩份清單」的一致性怎麼鎖

`components.md:432-434` 逐字把這件事指派本站：`embeddingModel` 的合法值集合是
**2 個模型名**（`bge-m3`／`multilingual-e5-large`），而實作名稱是 **4 個**
（`ollama`／`fastembed`／`fulltext`／`stub`）。K-06 說 `model_id` 回傳「寫入
`memory_records.embeddingModel` 的值」。於是 `stub` 要回什麼？若回 `bge-m3`，
CI 寫入的列與 staging 寫入的列在資料上**不可區分**——而那正是 ADR-008 要防的跨向量空間污染。

- **A（建議）— `model_id` 的值域是 4 個**：`bge-m3`、`multilingual-e5-large`、
  `stub-v1`、以及 `fulltext` 不參與（依 Q1=A 它沒有 `model_id`）。`embeddingModel`
  欄位的合法值集合**擴為 3 個**（含 `stub-v1`）且可為 `NULL`（`fulltext` 的列）。
  鎖法：一個測試斷言「每個實作的 `model_id()` 都在 `embeddingModel` 的合法值集合內」
  **且**「該集合沒有任何值對應不到實作」——雙向，兩份清單任一側漂移即紅燈。
  代價：`embeddingModel` 的合法值集合是 `U5 memory-data` 的 schema 範圍，本站擴充它
  屬跨單元影響，須具名交接。
- **B — `model_id` 回實作名稱而非模型名稱**（`ollama`／`fastembed`／`stub`）。
  兩份清單**合併為一份**，一致性不需測試鎖，因為只有一份。代價：同一個 `ollama`
  實作換模型（`bge-m3` → 別的 1024 維模型）時 `model_id` 不變，於是兩個不同向量空間
  的列帶同一個 `embeddingModel`——ADR-008 的核心防線失效，且失效方式無聲。
- **C — `model_id` 回「實作名稱＋模型名稱」的複合值**（如 `ollama:bge-m3`、`stub:v1`）。
  同時保有可區分性與單一清單。代價：值變長且需定分隔符與長度上限；`embeddingModel`
  欄位既有的 2 個值在資料上需要遷移，而 `U5` 的 schema 尚未落地故成本為零（本站須確認此前提）。
- **D — `stub` 回 `bge-m3`，刻意讓 CI 與 staging 的列同構。** 好處是 CI 能驗到
  「同 `embeddingModel` 分群」這條邏輯的 happy path。代價：見上，污染不可區分。

[Answer]: A

> **Q2 的作答經過一次更正，如實記載。** 初答為 **B**（`model_id` 回實作名稱）。
> 依 `project.md`「使用者選的選項會製造新的正確性問題時，說出具體理由並請其重選」，
> 我指名了兩件會壞掉的事：① `OLLAMA_EMBED_MODEL`／`FASTEMBED_MODEL` 在 K-01 是
> **可設定變數**（`type: string`、各有預設、validation 只管「維度須為 1024」、
> **不管模型身分**），故 B 之下換模型前後寫入的列都帶 `embeddingModel=ollama`，
> 「只比對同一 `embeddingModel` 的列」會把兩個不同向量空間的列判定為可比較
> ——回垃圾且不報錯，正是 ADR-008 Context 的「關鍵風險」逐字所指；
> ② `bge-m3`／`multilingual-e5-large` 是 `components.md:432` **已核可**的
> `embeddingModel` 值域，欄位名本身就是 embedding**Model**，B 是整組換成提供者名稱
> ——屬推翻已核可決定而非細化。重選後為 **A**。原選項本文不改寫（依
> `functional-design:c22`：只修理由不改決定的反向——此處是決定本身被更正，
> 故保留初答紀錄讓「B 曾被選過」可追溯，依 `scope-definition:21af5820`）。

---

## Q3 「大聲失敗」的時機與判準

ADR-008 要求「偵測不到選定提供者時必須大聲失敗並列出可選值」。但「偵測不到」有兩種：
**設定值不在允許集合內**（純字串比對，啟動時即可知）與**選定的提供者連不上**
（`ollama` 服務未起、`fastembed` 模型未下載——只有實際嘗試才知道）。
查證顯示目前**沒有任何 Python 讀取點**，而 `deploy/.env.example:96` 已以現在式宣稱
「缺值會讓 backend 拒絕啟動」——那道驗證是本單元要造的。

- **A（建議）— 兩段分開：設定值在啟動時驗（缺值或不在允許集合內即拒絕啟動並列出四個可選值）；
  可連線性在首次 `embed` 時驗（失敗拋 `EmbeddingProviderUnavailable`，訊息含選定提供者、
  其位址與四個可選值）。** 理由：啟動時探測 `ollama` 會讓 backend 的啟動依賴第 6 個服務
  （`docker-compose.test.yml` 逐字沒有 ollama，用 `stub`），而 `deploy.yml` 是在
  `up -d` **之後**才 `ollama pull` 模型——啟動探測會讓部署在模型就位前就紅燈。
  代價：記憶寫入路徑可能在執行期才首次失敗，故需一條明確的錯誤訊息契約。
- **B — 全部在啟動時驗，含對選定提供者發一次探測請求。** 「跑起來就是能用」最強。
  代價：見上，會與既有部署順序（先 `up -d` 後 `ollama pull`）衝突，且 test stack 無 ollama。
- **C — 全部在首次呼叫時驗。** 啟動路徑零新增依賴。代價：一個打錯字的
  `EMBEDDING_PROVIDER=ollamaa` 要到第一次寫記憶才被發現，而 `deploy/.env.example` 的
  現在式宣稱在這個選項下永遠為假，須回頭改那兩個檔的文字（跨單元）。
- **D — 啟動時驗設定值，並且**對 `ollama` 做一次**非阻斷**的探測（失敗只記 WARN）。
  代價：WARN 等於靜默降級的近親——`project.md` 反覆記載本 repo 的主要受害形式正是
  「只記 warning 的檢查」（實例就在 `database.py:230`）。

[Answer]: A

## Q4 `fastembed` 依賴的安裝策略

`fastembed` 是**行程內** ONNX 推論（`deploy/.env.example:126` 逐字「行程內 ONNX，不另起服務」）。
`backend/requirements.txt` 現在沒有它。把它無條件加進去，會讓 CI、兩個 Docker image
與 staging 都安裝一個只有「本機無 Ollama 的開發者」會用到的推論套件。

- **A（建議）— 列為選用：`requirements.txt` 不加，改在 `LOCAL-DEV.md` 寫明
  「要用 `fastembed` 時自行 `pip install fastembed`」，而 `fastembed` 實作的 import
  放在函式內（lazy import），未安裝時拋 `EmbeddingProviderUnavailable` 並在訊息裡寫出安裝指令。**
  理由：三個環境裡只有「本機且無 Ollama」會選它（`.env.example` 預設 `fulltext`、
  部署 `ollama`、test stack `stub`）。代價：`LOCAL-DEV.md` 的隱性前置條件由 2 個變 3 個
  ——而 `project.md` 的 blocking 規則要求異動 `.env.example` 時同步更新 `LOCAL-DEV.md`，
  本單元本來就會觸發它，故增量成本低。
- **B — 無條件加進 `requirements.txt`。** 任何環境切過去就能用，零文件負擔。
  代價：ONNX runtime 與模型載入器進了每個 image；`project.md` 已記載 backend 依賴
  多數未 pin、無 lockfile，再加一個重依賴會放大「CI／Docker／staging 三處各自解析最新版」
  的既有風險。
- **C — 加進 `requirements.txt` 但以 extras 區隔**（如 `requirements-dev.txt`）。
  折衷。代價：本 repo **目前只有一份** `requirements.txt`，引入第二份是工具鏈決策，
  不該由一個 library 單元夾帶（與 `team.md` 拒絕 D 項（前端測試框架）的理由同形）。
- **D — 放棄 `fastembed`，本機一律用 `fulltext` 或自行裝 Ollama。** 依賴最少。
  代價：直接推翻 ADR-008 的 Alternatives Rejected——該節逐字記「使用者亦明確要求保留
  fastembed 這條路」。選此項需使用者推翻自己先前的定案。

[Answer]: A
