# Business Rules — `U6 embedding-port`（`library`）

## 〇、本單元的規則來自哪裡

本單元**沒有使用者可見的業務邏輯**——它是一個 Port。所以下面的規則分成兩類，
而我把類別標在每一條上，因為混在一起會讓「這條是誰定的」說不清楚：

- **承載上游已核可決定**的規則（`source` 指向 K-01／K-06／ADR-008／`components.md`）
  ——它們不是本站的新決定，是把已定案的事寫成可斷言的形式。
- **本站定案**的規則（`source` 指向 `[Q1]`–`[Q4]`）——四題的後果。

`category` 用 stage 檔宣告的五個值：`validation`／`authorization`／`constraint`／
`calculation`／`policy`。**`authorization` 一條也沒有**，這不是漏寫：K-06 的
`behaviour_semantics.authorization_responsibility` 逐字「無——本 Port 不碰授權，
亦不讀 DB」。

## 一、source of truth

```yaml
rules:
  # ---- BR1.x 提供者選擇與啟動驗證 ----
  - id: BR1.1
    statement: "`EMBEDDING_PROVIDER` 必填，且值須在 {ollama, fastembed, fulltext, stub} 內；否則啟動失敗"
    category: validation
    applies_to: ProviderSelection
    trigger: "行程啟動時的設定解析"
    logic: >
      IF `EMBEDDING_PROVIDER` 未設定 OR 為空字串 OR 不在四個合法值內
      THEN 終止啟動，錯誤訊息須含（a）讀到的值（空值時明寫「未設定」）
      與（b）四個合法值逐字。
    violation_behaviour: "啟動失敗（行程不進入可服務狀態）。**不得**記 WARN 後繼續（見 BR1.6）"
    source: "[Q3]=A；K-01 `EMBEDDING_PROVIDER` 的 `required: true` ＋ `default: null`"
  - id: BR1.2
    statement: "設定解析在啟動時執行一次，其結果不可變；不支援執行期切換提供者"
    category: constraint
    applies_to: ProviderSelection
    trigger: "啟動時解析完成之後的任何時刻"
    logic: >
      IF 任何程式路徑試圖重新解析或替換已解析的 ProviderSelection
      THEN 該路徑不存在（設計上不提供該操作）。
    violation_behaviour: "不適用——以「不提供該操作」實現，而非執行期檢查"
    source: >
      K-06 `retry_and_idempotency` 逐字「embed 為純函式語意（同輸入同輸出）」
      ——執行期切換提供者會讓同一行程先後落在兩個向量空間，純函式語意隨之不成立
  - id: BR1.3
    statement: "`EMBEDDING_PROVIDER=ollama` 時 `OLLAMA_BASE_URL` 必填；缺值即啟動失敗"
    category: validation
    applies_to: ProviderSelection
    trigger: "啟動時的設定解析，在 BR1.1 通過之後"
    logic: >
      IF providerName == ollama AND `OLLAMA_BASE_URL` 未設定或為空
      THEN 終止啟動。
      `OLLAMA_EMBED_MODEL`（預設 `bge-m3`）與 `FASTEMBED_MODEL`
      （預設 `multilingual-e5-large`）**有預設故不必填**。
    violation_behaviour: "啟動失敗"
    source: "K-01：`OLLAMA_BASE_URL` 的 `required: 僅當 EMBEDDING_PROVIDER=ollama`、`default: null`"
  - id: BR1.4
    statement: "`EMBEDDING_PROVIDER=fulltext` 時選擇器回傳「無 Port」；呼叫方不得取得 Port 物件"
    category: constraint
    applies_to: "ProviderSelection → EmbeddingPort"
    trigger: "啟動時的 Port 建構"
    logic: >
      IF providerName == fulltext
      THEN portPresent = false AND 選擇器回傳空值（Optional 的空側）
      AND modelId = null。
      ELSE portPresent = true AND 回傳該提供者的 EmbeddingPort 實例。
    violation_behaviour: >
      不適用——以型別實現（回傳 Optional）。但**可機械斷言**：
      `fulltext` 設定下選擇器的回傳為空、其餘三者為非空。
    source: "[Q1]=A"
  - id: BR1.5
    statement: "啟動時不得對選定提供者發出任何探測請求"
    category: policy
    applies_to: ProviderSelection
    trigger: "啟動時的 Port 建構"
    logic: >
      IF 建構 ollama 或 fastembed 的 Port
      THEN 只建構物件、只讀設定，**不**發 HTTP、**不**載入模型。
      可用性留到首次 `embed`（BR4.2）。
    violation_behaviour: "不適用——以「不實作探測」實現"
    source: >
      [Q3]=A。理由已查證且是兩條硬事實：（a）`deploy/docker-compose.test.yml:18`
      逐字「NO ollama. EMBEDDING_PROVIDER is `stub` instead」——test stack 沒有
      ollama 服務；（b）`deploy.yml` 在 `up -d` **之後**才跑一次 `ollama pull`
      （`deploy/.env.example:123` 逐字「模型**不會**因為容器啟動就出現」）
      ——啟動探測會讓部署在模型就位前就紅燈
  - id: BR1.6
    statement: "啟動驗證失敗一律終止啟動，不得降級為 WARN 後繼續"
    category: policy
    applies_to: "BR1.1、BR1.3"
    trigger: "任一啟動驗證不通過"
    logic: "IF 啟動驗證不通過 THEN raise 並終止；不得只 log.warning。"
    violation_behaviour: "本條即是違反行為的禁令本身"
    source: >
      ADR-008 Decision 逐字「不得靜默降級」；`phases/construction.md` 逐字
      「Errors must be surfaced」。**本 repo 已有同形的反例在相鄰程式裡**：
      `backend/database.py:230` 的 `_ensure_vector_extension()` 失敗只
      `logger.warning`——那是 `U1` 的**刻意**選擇（它把大聲失敗留給下游的
      `create_all()`，`:214-217` 寫明理由），不是本條要效法的對象

  # ---- BR2.x embed 的契約 ----
  - id: BR2.1
    statement: "`embed(texts)` 回傳 list 的長度等於 `len(texts)`，且第 i 個向量對應第 i 個輸入"
    category: constraint
    applies_to: EmbeddingPort.embed
    trigger: "每次 embed 呼叫"
    logic: "IF 呼叫 embed(texts) 且未拋例外 THEN len(result) == len(texts) AND result[i] 是 texts[i] 的向量。"
    violation_behaviour: "實作缺陷；由 property-based 測試 `P1` 攔下"
    source: "K-06 `public_interface.embed` 的 `params`／`returns`"
  - id: BR2.2
    statement: "每個回傳向量的長度恰為 1024"
    category: constraint
    applies_to: EmbeddingVector
    trigger: "每次 embed 呼叫"
    logic: "IF 回傳向量 v THEN len(v) == 1024（不是 ≥、不是 ≤）。"
    violation_behaviour: >
      實作缺陷；由 `P2` 攔下。**在執行期它會是 `U8` 寫入 `vector(1024)` 時的
      資料庫錯誤**——本條存在的理由是讓它在本單元的測試裡就紅，而不是等到寫入時
    source: "K-06 `returns` 逐字「每個長度 1024」；ADR-008 的 `vector(1024)`"
  - id: BR2.3
    statement: "`embed` 為純函式語意：同一 ProviderSelection 下，同輸入必同輸出"
    category: calculation
    applies_to: EmbeddingPort.embed
    trigger: "同一輸入的重複呼叫"
    logic: "IF embed(t) 呼叫兩次且皆未拋例外 THEN 兩次結果完全相等。"
    violation_behaviour: >
      對 `stub` 是實作缺陷（由 `P3` 攔下）。
      **對 `ollama`／`fastembed` 本條不可在 CI 驗證**——需要服務或模型在位；
      如實記載於 §三，不以「已驗證」記錄
    source: "K-06 `retry_and_idempotency` 逐字「embed 為純函式語意（同輸入同輸出）」"
  - id: BR2.4
    statement: "`embed([])` 回傳 `[]`，不呼叫外部服務、不拋例外"
    category: constraint
    applies_to: EmbeddingPort.embed
    trigger: "以空序列呼叫 embed"
    logic: "IF texts 為空 THEN 回傳 [] 且不發出任何外部呼叫。"
    violation_behaviour: "實作缺陷；由 `P6` 攔下"
    source: >
      本站補入。理由：`BR2.1`（長度相等）在空輸入時的唯一解就是 `[]`，
      但若不明寫，一個「空輸入時探測服務」的實作也符合 BR2.1 字面
      ——而那會讓 `fulltext` 之外的空呼叫產生不必要的外部依賴
  - id: BR2.5
    statement: "`embed` 為全有或全無：任一元素失敗則整批拋例外，不得回傳部分結果"
    category: policy
    applies_to: EmbeddingPort.embed
    trigger: "批次中任一元素的向量化失敗"
    logic: >
      IF 批次中任一元素失敗
      THEN 拋 `EmbeddingProviderUnavailable`，不回傳任何向量。
      **不得**以 null 或零向量填補失敗的位置。
    violation_behaviour: >
      部分結果會違反 `BR2.1`（長度對應），且以零向量填補會重現 `[Q1]` 選項 D
      被拒的那個失敗模式（全零向量被當成合法向量寫入，檢索回垃圾不報錯）
    source: "本站補入；[Q1] 選項 D 的拒絕理由同源"
  - id: BR2.6
    statement: "本 Port 自身不重試；重試次數上限由呼叫方設定"
    category: policy
    applies_to: EmbeddingPort.embed
    trigger: "外部呼叫失敗"
    logic: "IF ollama 的 HTTP 呼叫失敗 THEN 直接拋例外，不在本 Port 內重試。"
    violation_behaviour: "不適用——以「不實作重試」實現"
    source: "K-06 `retry_and_idempotency` 逐字「本 Port 自身不重試，重試次數上限由呼叫方依 [C9] 的上限設定」"
  - id: BR2.7
    statement: "`embed` 與 `model_id` 皆不讀資料庫、不做授權判定"
    category: constraint
    applies_to: EmbeddingPort
    trigger: "任何呼叫"
    logic: >
      IF 本單元的任何模組 THEN 不得 import DB session 型別、不得 import
      `require_story_action` 或任何 RBAC 判定函式。
    violation_behaviour: >
      **可機械斷言**：本單元模組的 import 清單中，DB session 型別與 RBAC
      判定函式的 grep 結果須為零（與 `project.md` 對 cost 純函式層的
      可執行檢查同形）
    source: "K-06 `authorization_responsibility` 逐字「無——本 Port 不碰授權，亦不讀 DB」"

  # ---- BR3.x model_id 與兩份清單的一致性 ----
  - id: BR3.1
    statement: "`model_id()` 的值編碼**向量空間身分**；其預設值域為 {bge-m3, multilingual-e5-large, stub-v1}，`fulltext` 不參與"
    category: constraint
    applies_to: ModelId
    trigger: "每次 model_id 呼叫"
    logic: >
      ollama → `OLLAMA_EMBED_MODEL` 的值（預設 `bge-m3`）；
      fastembed → `FASTEMBED_MODEL` 的值（預設 `multilingual-e5-large`）；
      stub → 固定 `stub-v1`；
      fulltext → 無 Port 故無此方法。
    violation_behaviour: "實作缺陷；由 `P5` 攔下"
    source: "[Q2]=A；`components.md:432` 已核可的兩個值 ＋ 本站新增 `stub-v1`"
  - id: BR3.2
    statement: "`model_id()` 在同一 ProviderSelection 下恆定"
    category: constraint
    applies_to: ModelId
    trigger: "同一行程內的重複呼叫"
    logic: "IF 同一行程內呼叫 model_id() 兩次 THEN 兩次相等。"
    violation_behaviour: "實作缺陷；由 `P5` 的恆定性子性質攔下"
    source: "BR1.2（解析結果不可變）的直接後果"
  - id: BR3.3
    statement: "**雙向一致性**：每個實作的 `model_id()` 都在 `embeddingModel` 的合法值集合內，且該集合除 `NULL` 外沒有值對應不到任何實作"
    category: constraint
    applies_to: "ModelId ↔ memory_records.embeddingModel"
    trigger: "測試時（這條是測試斷言，不是執行期檢查）"
    logic: >
      令 I = {每個 portPresent 實作的 model_id() 在其預設設定下的值}，
      令 S = `embeddingModel` 的合法值集合 ＼ {NULL}。
      THEN I ⊆ S **且** S ⊆ I（即 I == S）。
      單向（只驗 I ⊆ S）不足：那會讓 S 裡多出一個沒有實作產生的值而不被發現。
    violation_behaviour: "測試紅燈。兩份清單任一側漂移即觸發"
    source: >
      **`components.md:432-434` 逐字指派本站**：「`MemoryRecord.embeddingModel`
      的合法值集合（`bge-m3`／`multilingual-e5-large`）與 `EmbeddingPort` 的四個
      實作名稱（`ollama`／`fastembed`／`fulltext`／`stub`）是**兩份相關但不同的
      清單**，其一致性需要一個測試鎖住——列為 `functional-design` 的注意事項」
  - id: BR3.4
    statement: "`memory_records.embeddingModel` 可為 `NULL`，且 `NULL` 的唯一意義是「該列在無 Port（fulltext）模式下建立」"
    category: constraint
    applies_to: memory_records.embeddingModel
    trigger: "U8 寫入記憶時"
    logic: >
      IF portPresent == false THEN 該列的 embeddingModel = NULL
      AND 其向量欄位 = NULL。
      兩個 NULL 必須同時出現——只有其中一個為 NULL 是不一致狀態。
    violation_behaviour: >
      **本條的執行落點是 `U5`（schema）與 `U8`（寫入端），不是本單元**
      （本 Port 不讀 DB）。本站只宣告它，見交接事項 `H-E1`／`H-E2`
    source: "ADR-008 Consequences 逐字「`fulltext` 模式下建立的列其向量為 `NULL`」；[Q1]=A ＋ [Q2]=A"
  - id: BR3.5
    statement: "提供者名稱**不得**作為 `model_id`"
    category: policy
    applies_to: ModelId
    trigger: "實作 model_id 時"
    logic: >
      IF model_id() 回傳值 ∈ {ollama, fastembed, fulltext, stub}
      THEN 違反本條。
    violation_behaviour: >
      **可機械斷言**，且這是 `[Q2]` 由 B 更正為 A 所要防的具體失敗：
      `OLLAMA_EMBED_MODEL` 在 K-01 是可設定變數（`type: string`、
      validation 只管「dense 維度須為 1024」、**不管模型身分**），
      故提供者名稱在換模型之後會同時指向兩個向量空間，而
      「只比對同一 `embeddingModel` 的列」會把它們判定為可比較
      ——回垃圾且不報錯，正是 ADR-008 Context 的「關鍵風險」逐字所指
    source: "[Q2]=A（初答 B，經指名具體壞法後重選）"
  - id: BR3.6
    statement: "`stub` 的 `model_id()` 不得與任何真實模型名相同"
    category: constraint
    applies_to: ModelId
    trigger: "實作 stub 時"
    logic: "IF stub 的 model_id() ∈ {bge-m3, multilingual-e5-large, 或任何真實模型名} THEN 違反本條。固定值為 `stub-v1`。"
    violation_behaviour: >
      若 `stub` 回 `bge-m3`，CI 寫入的列與 staging 寫入的列在資料上
      **不可區分**——那正是 ADR-008 要防的跨向量空間污染，且 CI 的
      短生命週期 stack（`docker-compose.test.yml`）每個 PR 都會寫入
    source: "[Q2]=A；[Q2] 選項 D 的拒絕理由"

  # ---- BR4.x 大聲失敗 ----
  - id: BR4.1
    statement: "偵測不到選定提供者時拋 `EmbeddingProviderUnavailable`，訊息須含選定提供者、其目標、與四個可選值；不得靜默降級為全文檢索"
    category: policy
    applies_to: EmbeddingProviderUnavailable
    trigger: "首次 embed 時發現提供者不可用"
    logic: >
      IF 選定提供者不可用
      THEN raise EmbeddingProviderUnavailable(selectedProvider, target, availableOptions)
      AND **不得**改用 fulltext、**不得**回傳零向量、**不得**只記 log。
      「訊息含四個可選值」可機械斷言（四個字串都在訊息中）。
    violation_behaviour: >
      靜默降級會讓「為什麼找不到我的記憶」變成無法除錯的問題
      ——ADR-008 Decision 逐字如此，且它明記這條是 domain-design 自行加上的約束
    source: "ADR-008 Decision；K-06 `raises` 逐字"
  - id: BR4.2
    statement: "`EmbeddingProviderUnavailable` 只在首次（或後續）`embed` 呼叫時拋出；設定層錯誤在啟動時以啟動失敗表達"
    category: policy
    applies_to: "EmbeddingProviderUnavailable ↔ BR1.1"
    trigger: "區分兩類失敗"
    logic: >
      IF 錯誤屬「設定值缺失或不在允許集合內」THEN 啟動失敗（BR1.1／BR1.3），
      **不**走本例外。
      IF 錯誤屬「選定提供者連不上／模型未就緒／套件未安裝」THEN 本例外。
    violation_behaviour: "兩類混用會讓啟動失敗的訊息與執行期例外無法分辨肇因"
    source: "[Q3]=A"
  - id: BR4.3
    statement: "`fastembed` 未安裝時拋 `EmbeddingProviderUnavailable`，訊息須含安裝指令"
    category: policy
    applies_to: EmbeddingProviderUnavailable
    trigger: "首次 embed 且 fastembed 的 lazy import 失敗"
    logic: >
      IF import fastembed 失敗（ImportError）
      THEN raise EmbeddingProviderUnavailable，target 欄位含模型名與
      `pip install fastembed`。**不得**讓 ImportError 原文直接傳出
      （它不會告訴使用者該裝什麼）。
    violation_behaviour: "實作缺陷"
    source: "[Q4]=A"
  - id: BR4.4
    statement: "本 Port 不吞例外；但其例外訊息不得含憑證或密碼"
    category: policy
    applies_to: EmbeddingProviderUnavailable
    trigger: "建構例外訊息時"
    logic: >
      IF 訊息要帶 endpoint THEN 帶主機與埠，**不得**帶任何 userinfo 區段
      （`http://user:pass@host` 形式的密碼部分）。
    violation_behaviour: >
      `team.md ## Forbidden` 逐字「不得把敏感資料寫進任何 log 或決議紀錄」。
      本單元的 `OLLAMA_BASE_URL` 目前形式為 `http://ollama:11434`（無 userinfo），
      故這是防範而非修補
    source: "team.md ## Forbidden；ADR-0006 的 audit logging 面"

  # ---- BR5.x 向量空間隔離：本 Port 保證什麼、不保證什麼 ----
  - id: BR5.1
    statement: "本 Port **不**保證不同 `model_id` 的向量不被互相比較——那是呼叫方的責任"
    category: policy
    applies_to: "EmbeddingPort ↔ U8 memory-service"
    trigger: "設計邊界的宣告"
    logic: >
      本 Port 的保證只有兩條：（a）同一 ProviderSelection 下 `model_id()` 恆定
      （BR3.2）；（b）`model_id()` 隨向量空間改變而改變（BR3.5）。
      「檢索只比對同一 `embeddingModel` 的列」這條過濾**在 `U8`**。
    violation_behaviour: >
      不適用——本條是**誠實宣告**而非禁令。寫下它的理由：若不寫，
      下游會以為「有了 Port 就安全了」，而 ADR-008 的風險是在檢索端成真的
    source: "ADR-008 Decision 逐字「相似度檢索只比對同一 `embeddingModel` 的列」——該句的主詞是檢索，不是 Port"
  - id: BR5.2
    statement: "`embed` 回傳的向量不攜帶 `model_id`；配對是呼叫方的責任"
    category: constraint
    applies_to: EmbeddingVector
    trigger: "每次 embed 呼叫"
    logic: >
      回傳型別為 `list[list[float]]`（K-06 逐字），無包裝型別。
      呼叫方必須以**同一次** ProviderSelection 的 `model_id()` 配對該批結果，
      不得分兩次取（兩次之間若行程重啟且設定已變，配對即錯）。
    violation_behaviour: "錯誤配對會讓一列記憶的向量與其 embeddingModel 不一致——而該不一致在資料上不可偵測"
    source: "K-06 `public_interface.embed` 的 `returns`；交接事項 `H-E2`"

  # ---- BR6.x 依賴策略 ----
  - id: BR6.1
    statement: "`fastembed` 為選用依賴：不列入 `requirements.txt`，其 import 置於函式內"
    category: policy
    applies_to: "fastembed 實作"
    trigger: "實作與依賴宣告"
    logic: >
      IF 實作 fastembed THEN import 語句在函式內（lazy），
      AND `backend/requirements.txt` 不新增 `fastembed`。
      **可機械斷言**：`grep -c '^fastembed' backend/requirements.txt` == 0，
      且該模組的頂層 import 不含 fastembed。
    violation_behaviour: >
      無條件安裝會把 ONNX runtime 與模型載入器放進每個 image，而三個環境中
      只有「本機且無 Ollama」會選它（`backend/.env.example:119` 預設 `fulltext`、
      `deploy/.env.example:116` 為 `ollama`、`docker-compose.test.yml:18` 為 `stub`）。
      `project.md` 已記載 backend 依賴多數未 pin、無 lockfile，再加重依賴會
      放大「CI／Docker／staging 三處各自解析最新版」的既有風險
    source: "[Q4]=A"
  - id: BR6.2
    statement: "`ollama` 實作只用既有的 `httpx`，不新增 HTTP 客戶端依賴"
    category: constraint
    applies_to: "ollama 實作"
    trigger: "實作與依賴宣告"
    logic: "IF 實作 ollama 的 HTTP 呼叫 THEN 使用 `httpx`（已在 `backend/requirements.txt`）。"
    violation_behaviour: "新增同類依賴違反 `team.md` 的既有形狀沿用原則"
    source: >
      **已實測**：`backend/requirements.txt` 含 `httpx`、**不含** `fastembed`、
      不含任何 ollama 客戶端。另 `project.md ## Forbidden` 逐字禁止
      「在既有 n8n／PNG 呼叫點用 httpx 直接打雲端 Pricing API」——那條的範圍是
      雲端計價 API，與本單元的同主機 Ollama 無關，**不適用**（逐項判讀，非一律套用）
  - id: BR6.3
    statement: "本單元若異動任一 `.env.example`，同一個 PR 須更新 `LOCAL-DEV.md`"
    category: policy
    applies_to: "交付物"
    trigger: "code-generation 實作時"
    logic: >
      IF 異動 `backend/.env.example` OR `deploy/.env.example`
      THEN 同步更新 `LOCAL-DEV.md`。
      本單元至少會觸發一次：`[Q4]`=A 讓隱性硬依賴由 2 個變 3 個。
    violation_behaviour: "`project.md ## Mandated` 第三條為 **blocking**"
    source: "project.md ## Mandated；[Q4]=A"

  # ---- BR7.x 可觀測性 ----
  - id: BR7.1
    statement: "啟動時須記一條 INFO，內容含 providerName、modelId（或「無 Port」）與 endpoint 主機"
    category: policy
    applies_to: ProviderSelection
    trigger: "設定解析完成"
    logic: >
      IF 解析成功 THEN log INFO 一條，含 providerName、modelId（null 時寫
      「無 Port（fulltext）」）、endpoint 的主機與埠。
      logger 名稱依 `team.md` 的既成慣例為 `cloud360.<module>` 形式。
    violation_behaviour: >
      少了它，「這個行程跑的是哪個模型」只能靠讀設定推斷——而那正是
      `embeddingModel` 分群出問題時第一個要問的事
    source: "ADR-0006 的 audit logging 面；team.md 的 logger 命名慣例"
  - id: BR7.2
    statement: "任何 log 與例外訊息不得含憑證"
    category: policy
    applies_to: "BR4.4、BR7.1"
    trigger: "建構 log 或例外訊息"
    logic: "IF 訊息含 endpoint THEN 不得帶 userinfo 區段。"
    violation_behaviour: "team.md ## Forbidden 逐字"
    source: "team.md ## Forbidden；ADR-0006 encryption／audit logging 面"
```

## 二、規則摘要表

| id | 類別 | 一句話 | 誰定的 |
|---|---|---|---|
| `BR1.1` | validation | `EMBEDDING_PROVIDER` 必填且在四值內，否則啟動失敗 | `[Q3]`＋K-01 |
| `BR1.2` | constraint | 解析一次、不可變，不支援執行期切換 | K-06 |
| `BR1.3` | validation | `ollama` 時 `OLLAMA_BASE_URL` 必填 | K-01 |
| `BR1.4` | constraint | `fulltext` ⇒ 無 Port，呼叫方拿不到物件 | **`[Q1]`** |
| `BR1.5` | policy | 啟動時不探測 | **`[Q3]`** |
| `BR1.6` | policy | 啟動驗證失敗即終止，不得只記 WARN | ADR-008 |
| `BR2.1` | constraint | 長度相等、順序一一對應 | K-06 |
| `BR2.2` | constraint | 每個向量恰 1024 維 | K-06／ADR-008 |
| `BR2.3` | calculation | 純函式語意（同輸入同輸出） | K-06 |
| `BR2.4` | constraint | `embed([])` 回 `[]` 且不呼叫外部 | 本站補入 |
| `BR2.5` | policy | 全有或全無，不回部分結果 | 本站補入 |
| `BR2.6` | policy | 本 Port 不重試 | K-06 |
| `BR2.7` | constraint | 不讀 DB、不做授權（可 grep 斷言） | K-06 |
| `BR3.1` | constraint | `model_id` 編碼向量空間身分，三個預設值 | **`[Q2]`** |
| `BR3.2` | constraint | 同一行程內恆定 | `BR1.2` 的後果 |
| `BR3.3` | constraint | **雙向一致性**，兩份清單任一側漂移即紅燈 | **`components.md:434` 指派** |
| `BR3.4` | constraint | `embeddingModel` 可為 `NULL`，意義唯一 | ADR-008＋`[Q1]`＋`[Q2]` |
| `BR3.5` | policy | 提供者名稱不得作為 `model_id` | **`[Q2]`（重選後）** |
| `BR3.6` | constraint | `stub` 的值不得與真實模型名相同 | **`[Q2]`** |
| `BR4.1` | policy | 大聲失敗，訊息含四個可選值，不得靜默降級 | ADR-008／K-06 |
| `BR4.2` | policy | 設定錯誤走啟動失敗、可用性錯誤走例外 | **`[Q3]`** |
| `BR4.3` | policy | `fastembed` 未安裝時訊息含安裝指令 | **`[Q4]`** |
| `BR4.4` | policy | 例外訊息不得含憑證 | `team.md` |
| `BR5.1` | policy | 本 Port **不**保證跨模型不被比較——誠實宣告 | ADR-008 的句子主詞 |
| `BR5.2` | constraint | 向量不攜帶 `model_id`，配對是呼叫方的責任 | K-06 |
| `BR6.1` | policy | `fastembed` 選用、lazy import | **`[Q4]`** |
| `BR6.2` | constraint | `ollama` 只用既有 `httpx` | 實測 |
| `BR6.3` | policy | 異動 `.env.example` 須同步 `LOCAL-DEV.md`（blocking） | `project.md` |
| `BR7.1` | policy | 啟動時記一條含 provider／model 的 INFO | ADR-0006 |
| `BR7.2` | policy | log 與例外不得含憑證 | `team.md` |

類別分佈與總數見 `functional-spec.md` §六（**由腳本實算後寫入，不手寫**）。

## 三、本站不保證、且不假裝保證的事

| 事項 | 為什麼本單元驗不到 | 落點 |
|---|---|---|
| `BR2.3`（純函式語意）對 `ollama`／`fastembed` | 需要 Ollama 服務在位或模型已下載。CI 的 test stack 逐字「NO ollama」且用 `stub` | 無自動化落點。**如實記為覆蓋缺口**，不列為已驗證 |
| `BR3.4`（`embeddingModel` 與向量同時為 `NULL`） | 本 Port 不讀 DB | `U5`（schema）／`U8`（寫入端），見 `H-E1`／`H-E2` |
| `BR5.1`（跨模型不被比較） | 過濾在檢索端 | `U8` |
| `OLLAMA_EMBED_MODEL` 的「dense 維度須為 1024」 | 要確認一個模型的維度必須真的載入它 | `code-generation` 可在 `ollama` 實作首次 `embed` 時斷言回傳長度（`BR2.2`），那是**執行期**而非設定期的保證。設定期無法驗——如實記載 |
