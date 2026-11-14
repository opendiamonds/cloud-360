# Entities — `U6 embedding-port`（`library`）

## 〇、這個單元的「實體」是什麼

本單元是 `library`（`unit-of-work.md:42` 逐字「embedded（library，無獨立執行期）」），
**沒有任何持久化實體**：K-06 的 `behaviour_semantics.authorization_responsibility`
逐字「無——本 Port 不碰授權，**亦不讀 DB**」。

所以下面的「實體」是**值物件與設定解析結果**——沒有主鍵、沒有生命週期事件、
沒有外鍵。`relationships` 欄位描述的是**組成與產生關係**，不是資料庫關聯。

唯一會被寫進資料庫的東西是 `ModelId` 的值（寫入 `memory_records.embeddingModel`），
而**那張表屬 `U5 memory-data`**。本檔對它只做值域宣告，不定 DDL——見 §三的交接事項 `H-E1`。

## 一、source of truth

```yaml
entities:
  - name: EmbeddingProviderName
    description: >
      `EMBEDDING_PROVIDER` 環境變數的合法值。四個值全部合法，但其中
      `fulltext` 的語意是「**不建立 Port**」而非「一個會算向量的實作」
      （`[Q1]`=A）。這是本站對 ADR-008 用詞的對齊，不是推翻它：
      ADR-008 說的「四個實作」在型別層是「三個實作 ＋ 一個停用狀態」。
      值域本身維持 K-01 的 `allowed` 四值，**未收窄**——`fulltext` 仍是
      一個合法的設定值。
    attributes:
      - name: value
        logical_type: string_enum
        required: true
        allowed_values: [ollama, fastembed, fulltext, stub]
        default: null
        constraints: >
          **刻意無預設**（K-01 的 `default: null` 逐字）。缺值或不在 allowed
          內一律啟動失敗並列出四個可選值，見 `BR1.1`。不得以空字串繼續啟動
          ——K-01 的註解逐字記載這條失敗模式是無聲的（既有實例：
          `N8N_USER`／`N8N_PASSWORD` 從未被寫入，導致架構圖 icons 靜默退回
          灰底佔位圖）。
    entity_constraints:
      - "值域與 `ProviderSelection.portPresent` 的對應是全函數且唯一：只有 `fulltext` 對應 false（`BR1.4`）"
    relationships:
      - target: ProviderSelection
        cardinality: "1 — 1"
        direction: "EmbeddingProviderName 決定 ProviderSelection"
        note: "一個設定值解析為恰好一個 ProviderSelection"

  - name: ProviderSelection
    description: >
      啟動時對設定做一次解析的結果。**不可變**（`BR1.2`）：本單元不支援
      執行期切換提供者，因為切換會讓同一個行程在兩個向量空間之間來回，
      而 `embed` 的純函式語意（K-06 `retry_and_idempotency` 逐字「同輸入同輸出」）
      在那之下不成立。
    attributes:
      - name: providerName
        logical_type: EmbeddingProviderName
        required: true
        constraints: "見上"
      - name: portPresent
        logical_type: boolean
        required: true
        constraints: >
          `providerName == fulltext` 時為 false，其餘三者為 true。
          false 時選擇器回傳「無 Port」，呼叫方**不得**取得 Port 物件
          （`BR1.4`，`[Q1]`=A）。
      - name: modelId
        logical_type: ModelId_or_null
        required: true
        constraints: >
          **欄位必存在，值可為 null**。`portPresent == false` 時為 null
          ——`fulltext` 不產生向量，故沒有向量空間身分可言。
          其餘三者為非 null，見 `ModelId`。
          （把「必存在」與「可為 null」分開寫，是因為
          `domain-design:b43f793` 記過「兩種 null 有語意差卻無區分者」
          這個形狀；此處只有一種 null，且它的意思被明確定義為「無 Port」。）
      - name: endpoint
        logical_type: string_uri_or_null
        required: true
        constraints: >
          僅 `providerName == ollama` 時為非 null，值取自 `OLLAMA_BASE_URL`。
          K-01 的 validation 逐字「主機名須為 compose 內部服務名；
          **對外暴露面必須為零**」。`fastembed` 為行程內推論故無端點；
          `stub`／`fulltext` 無外部依賴。
      - name: resolvedAt
        logical_type: timestamp
        required: true
        constraints: >
          解析發生的時刻。存在的理由是啟動日誌要能回答「這個行程跑的是哪個
          提供者、哪個模型」——見 `BR7.1`（ADR-0006 audit logging 面）。
    entity_constraints:
      - "`portPresent == false` ⟺ `modelId IS NULL` ⟺ `providerName == fulltext`（三者等價，`BR1.4` ＋ `BR3.1`）"
      - "`endpoint IS NOT NULL` ⟺ `providerName == ollama`（`BR1.3`）"
      - "解析後不可變（`BR1.2`）"
    relationships:
      - target: EmbeddingPort
        cardinality: "1 — 0..1"
        direction: "ProviderSelection 建構 0 或 1 個 EmbeddingPort"
        note: "**0 的那個情形就是 fulltext**（`[Q1]`=A）。這是本實體模型裡唯一的 0..1，而它承載的正是 Q1 的定案"
      - target: ModelId
        cardinality: "1 — 0..1"
        direction: "ProviderSelection 持有 0 或 1 個 ModelId"

  - name: EmbeddingPort
    description: >
      K-06 定義的介面本身。**它不是資料**，列在這裡是因為 `entities.md`
      是本站宣告「這個單元有哪些東西」的地方，而把介面藏進 `rules.md`
      會讓它的兩個方法沒有宣告落點。公開介面只有兩個方法，形式皆為 sync
      （K-06 `public_interface` 逐字）。
    attributes:
      - name: embed
        logical_type: method
        required: true
        constraints: >
          `embed(texts: Sequence[str]) -> list[list[float]]`。回傳 list 長度
          等於輸入長度且順序一一對應（`BR2.1`）；每個向量長度恰為 1024
          （`BR2.2`，K-06 逐字「每個長度 1024」）。純函式語意（`BR2.3`）。
          全有或全無（`BR2.5`）。不讀 DB、不做授權判定（`BR2.7`）。
      - name: model_id
        logical_type: method
        required: true
        constraints: >
          `model_id() -> str`。回傳**模型身分**而非提供者名稱（`BR3.5`，
          `[Q2]`=A）。同一 `ProviderSelection` 下恆定（`BR3.2`）。
    entity_constraints:
      - "介面只有這兩個方法；本單元不新增第三個（K-06 的 `public_interface` 是契約，擴充須回 contract-design）"
      - "三個實作（ollama／fastembed／stub）各自完整實作這兩個方法；沒有部分實作（`BR2.1`–`BR2.3` 對三者皆適用）"
    relationships:
      - target: EmbeddingVector
        cardinality: "1 — 0..N"
        direction: "EmbeddingPort.embed 產生 0..N 個 EmbeddingVector"
        note: "0 的情形是 `embed([])`（`BR2.4`）"
      - target: ModelId
        cardinality: "1 — 1"
        direction: "EmbeddingPort 回報恰好一個 ModelId"

  - name: ModelId
    description: >
      寫入 `memory_records.embeddingModel` 的值（K-06 `model_id` 的
      `returns` 逐字「str — 寫入 memory_records.embeddingModel 的值」）。
      它編碼的是**向量空間身分**，不是提供者身分——這是 `[Q2]` 由 B 更正為 A
      的全部理由：`OLLAMA_EMBED_MODEL` 在 K-01 是可設定變數
      （`type: string`、`default: "bge-m3"`、validation 只管「dense 維度須為 1024」、
      **不管模型身分**），所以提供者名稱在換模型之後會指向第二個向量空間，
      而「只比對同一 `embeddingModel` 的列」這道過濾會把它們判定為可比較
      ——回垃圾且不報錯，正是 ADR-008 Context 的「關鍵風險」逐字所指。
    attributes:
      - name: value
        logical_type: string_enum
        required: true
        allowed_values: [bge-m3, multilingual-e5-large, stub-v1]
        constraints: >
          三個值，**由 `components.md:432` 已核可的兩個擴充而來**：新增的只有
          `stub-v1`。`fulltext` 不參與（它沒有 Port，見 `[Q1]`=A）。
          `stub-v1` 刻意不與任何真實模型名相同（`BR3.6`）——若 `stub` 回
          `bge-m3`，CI 寫入的列與 staging 寫入的列在資料上不可區分，
          那正是 ADR-008 要防的跨向量空間污染。
      - name: appliesToProvider
        logical_type: EmbeddingProviderName
        required: true
        constraints: >
          `bge-m3` ← ollama（取自 `OLLAMA_EMBED_MODEL`，預設 `bge-m3`）；
          `multilingual-e5-large` ← fastembed（取自 `FASTEMBED_MODEL`，
          預設 `multilingual-e5-large`）；`stub-v1` ← stub（**不可設定**，
          由本單元固定）。
    entity_constraints:
      - "**雙向一致性（`BR3.3`，`components.md:434` 指派本站的那一項）**：每個實作的 `model_id()` 都在本值域內，且本值域除 `NULL` 外沒有值對應不到實作。兩份清單任一側漂移即紅燈"
      - "`ollama` 與 `fastembed` 的值由環境變數決定，故本值域在那兩格是**開放的**：設了別的 1024 維模型，`model_id()` 就該回那個新值（`BR3.5`）。本值域列的是三個**預設**值，不是封閉枚舉——這一點必須與 `U5` 的 schema 約束形式一併定（見 `H-E1`）"
    relationships:
      - target: ProviderSelection
        cardinality: "0..1 — 1"
        direction: "ModelId 隸屬於一個 ProviderSelection"

  - name: EmbeddingVector
    description: >
      `embed` 的單一回傳元素。**它不攜帶 `ModelId`**（`BR5.2`）——K-06 的
      `returns` 逐字只有 `list[list[float]]`，沒有包裝型別。
      配對向量與其模型身分是**呼叫方的責任**，本站把這個接縫明寫出來
      而不是假設它顯然（它不顯然：忘記配對就是 ADR-008 的風險成真的路徑）。
    attributes:
      - name: values
        logical_type: list_of_float
        required: true
        constraints: >
          長度**恰為** 1024（`BR2.2`）。1024 是 ADR-008 的定案
          （`vector(1024)`，兩個向量提供者同維度故可共用）。
          本單元不做正規化（L2 normalize）——K-06 未要求，
          且相似度的度量選擇屬 `U8` 的檢索設計。
      - name: position
        logical_type: integer
        required: true
        constraints: >
          在回傳 list 中的索引，等於它在輸入 `texts` 中的索引（`BR2.1`）。
          這條是**可機械斷言**的，而且它是分批不變性（`P4`）的前提。
    entity_constraints:
      - "不含 `ModelId`；配對由呼叫方負責（`BR5.2`）"
      - "`fulltext` 不產生此實體（無 Port）；其列的向量欄位為 `NULL`（ADR-008 Consequences 逐字）"
    relationships:
      - target: EmbeddingPort
        cardinality: "0..N — 1"
        direction: "EmbeddingVector 由一個 EmbeddingPort 產生"

  - name: EmbeddingProviderUnavailable
    description: >
      K-06 `raises` 宣告的唯一例外（逐字「偵測不到選定提供者時。**必須大聲失敗
      並列出可選值，不得靜默降級為全文檢索**」）。列為實體是因為它的**訊息內容
      是契約的一部分**——「列出可選值」是一條可機械斷言的要求，而沒有一個地方
      宣告它的欄位，那句話就只是期望。
    attributes:
      - name: selectedProvider
        logical_type: EmbeddingProviderName
        required: true
        constraints: "被選定但不可用的那一個"
      - name: target
        logical_type: string_or_null
        required: true
        constraints: >
          `ollama` → 其 `endpoint`；`fastembed` → 其模型名與安裝指令
          （`BR4.3`，`[Q4]`=A）；`stub` → null（`stub` 不可能不可用）。
          **不得含憑證**（`BR7.2`）。
      - name: availableOptions
        logical_type: list_of_string
        required: true
        constraints: >
          四個可選值，逐字。這是 ADR-008「列出可選值」的落點，
          且它可被測試斷言（四個字串都在訊息中）。
    entity_constraints:
      - "此例外**只能**在首次 `embed` 時被拋出（`BR4.2`，`[Q3]`=A）；設定層的錯誤在啟動時以啟動失敗表達，不走這個例外"
    relationships:
      - target: EmbeddingPort
        cardinality: "0..N — 1"
        direction: "由 EmbeddingPort.embed 拋出"
```

## 二、人類可讀摘要

六個值物件，零張表。

| 實體 | 是什麼 | 誰寫 | 誰讀 | 誰清 |
|---|---|---|---|---|
| `EmbeddingProviderName` | `EMBEDDING_PROVIDER` 的合法值（四個） | 部署設定（`render-env.sh`／`.env`，`U1` 已交付） | 本單元的選擇器 | 不適用（設定值，非狀態） |
| `ProviderSelection` | 啟動時解析一次的結果，不可變 | 本單元（啟動時） | 本單元；`U8` 透過「有無 Port」間接讀 | 行程結束 |
| `EmbeddingPort` | K-06 的介面（兩個方法） | 本單元（三個實作） | `U8 memory-service`（唯一消費端，K-06 `consumers`） | 行程結束 |
| `ModelId` | 寫進 `memory_records.embeddingModel` 的值 | 本單元產生值；**`U8` 負責寫入 DB** | `U8` 的相似度檢索（分群過濾） | 隨該列記憶被刪除（`U8`／`U9`） |
| `EmbeddingVector` | 1024 個 float | 本單元 | `U8`（寫入向量欄位、做距離比較） | 隨該列記憶被刪除 |
| `EmbeddingProviderUnavailable` | 大聲失敗的載體 | 本單元 | `U8` 的錯誤處理邊界 | 不適用（例外，非狀態） |

**三問的結果（自檢 2）**：六個實體的「誰寫／誰讀／誰清」全部可指名。
`ModelId` 那一列的「誰寫」刻意分成兩半——本單元產生值、`U8` 寫入 DB——因為
K-06 把 `model_id` 定義為「寫入 `memory_records.embeddingModel` 的值」，
而本 Port 不讀 DB，所以**本單元不可能是寫入端**。這不是缺口，是職責邊界；
但它意味著「`embeddingModel` 一定等於產生該向量的 `model_id()`」這條不變量
**不在本單元的驗證範圍內**，見 `BR5.1` 與交接事項 `H-E2`。

## 三、交接事項（**不回改已核可的上游產出**）

| # | 事項 | 落點 | 已查證的前提 |
|---|---|---|---|
| `H-E1` | **`memory_records.embeddingModel` 的值域由 2 擴為 3（新增 `stub-v1`）且須可為 `NULL`**；且 `ollama`／`fastembed` 兩格的值由環境變數決定，故 schema 端**不應寫成封閉枚舉**（寫成 `CHECK (embeddingModel IN (...))` 會讓換模型變成資料庫錯誤）。建議形式：非空字串約束 ＋ 應用層的 `BR3.3` 雙向測試 | `U5 memory-data` 的 `functional-design`／schema | **已實測**：`grep -rn 'memory_records\|embeddingModel' schema_rbac.sql schema.sql backend/models.py` → **零命中**；`construction/memory-data/` 不存在。故 schema 尚未落地，**遷移成本為零** |
| `H-E2` | **「`embeddingModel` 等於產生該向量的 `model_id()`」這條不變量的驗證落在 `U8`**，不在本單元（本 Port 不讀 DB）。`U8` 寫入記憶時必須以**同一次** `ProviderSelection` 的 `model_id()` 配對該次 `embed` 的結果，不得分兩次取 | `U8 memory-service` | K-06 `authorization_responsibility` 逐字「不讀 DB」；`BR5.2` |
| `H-E3` | **選擇器的回傳是 Optional**（`[Q1]`=A）。K-06 的 `implementations: [ollama, fastembed, fulltext, stub]` 在型別上應讀作「三個實作 ＋ 一個停用狀態」。**本站不回改 `contract-summary.md`**；若 contract 要維持四個齊平的實作，須回 `contract-design` 修訂而非在本站兩種讀法並存 | `U8` 的 `functional-design`（消費形狀）——**該站為 `CONDITIONAL`**，condition 逐字「Skip if simple logic changes with no new business logic」；**轉移目標 `U8` 的 `code-generation`（`ALWAYS`）**，且若前者被 skip，屆時判定 skip 的 conductor 須把本項重新提交使用者（審查 `R-02`）。必要時 `contract-design` | `refined-mockups:c3`（下游修正上游瑕疵須明記為對齊、上游檔不回改） |
| `H-E4` | **`fastembed` 列為選用依賴**（`[Q4]`=A）→ `LOCAL-DEV.md` 的隱性硬依賴由 2 個（`claude` CLI、n8n webhook）變 **3 個**。`project.md` 的 blocking 規則要求異動任一 `.env.example` 時同步更新 `LOCAL-DEV.md`——本單元本來就會觸發它 | `code-generation`（3.5，`ALWAYS`） | `project.md ## Mandated` 第三條逐字 |
| `H-E5` | **`deploy/.env.example:96` 與 `:114` 的現在式宣稱在本單元落地前為假。** 逐字：「`EMBEDDING_PROVIDER` 缺值會讓 backend 拒絕啟動」。`BR1.1` 就是它的實作；落地後該宣稱為真，**不需改那兩個檔** | `code-generation`（3.5） | **已實測**：`grep -rn 'EMBEDDING_PROVIDER' backend --include='*.py'` 只命中 `tests/test_render_env_redis.py` 的註解與常數名，零個執行期讀取點；`env_bootstrap.py` 只做 `load_dotenv` |
