# 商業規則 — `U22` `progress-channel`

> 單元：`U22` `progress-channel`（`library`，M）　Stage：`functional-design`（3.1）
> 本單元**無受保護操作**（`contract-summary.md` K-18
> `authorization_responsibility` 逐字「無受保護操作——進度事件的可見性由
> `request_key` 的不可猜性保證，不由授權判定」）。下列規則因此全為
> `constraint`／`validation`／`policy`，**無 `authorization` 類**。

---

## 來源真實（機讀）

```yaml
rules:
  - id: BR1.1
    statement: 進度通道的鍵必須是 per-request，由入口端鑄造並以顯式參數傳遞
    category: constraint
    applies_to: RequestKey
    trigger: 入口端建立通道之前
    logic: >
      IF 要開啟一個進度通道
      THEN 鍵由入口端（`U13 brain-gateway` 或 `U12 work-orchestrator`）產生一個
      不透明且不可猜的值，並以新增的顯式參數一路傳遞給 `run_design_agent`、
      寫入端與讀取端；本單元不自行推導鍵，也不從環境讀取它。
    violation_behaviour: >
      以 `thread_id` 為鍵即違反——它在 `agent_router.py:125` 是
      `f"user-{current_user.id}-design"`，per-user 而非 per-request，照字面實作完
      `AC13.1.1` **仍會紅燈**（`[US:V-01]` 的 Critical）。以「session」為鍵亦違反
      ——`run_design_agent` 的簽章裡不存在該參數。
    source: FR13.1、`[US:V-01]`、`contract-summary.md` K-18 `key_contract`、`[Q1]`=A

  - id: BR1.2
    statement: open 對已存在的鍵必須拋 DuplicateChannelKey，不得靜默覆寫
    category: validation
    applies_to: ProgressChannelRegistry
    trigger: ProgressChannel.open(request_key)
    logic: >
      IF 該 `request_key` 已有存活通道
      THEN 拋 `DuplicateChannelKey`，不建立、不覆寫。
    violation_behaviour: >
      靜默覆寫會讓前一個請求**已經寫入但還沒被讀走**的事件憑空消失——那正是現狀
      `design_agent.py:183` 的行為（直接指派 `_progress_queue = asyncio.Queue()`），
      也正是本單元要消除的失敗模式。覆寫是比錯送更難察覺的版本：使用者只是少收到
      東西，沒有任何錯誤。
    source: `contract-summary.md` K-18 `retry_and_idempotency` 第 1 項

  - id: BR1.3
    statement: 一則事件只能被寫入它的那個鍵的 drain 取得
    category: constraint
    applies_to: ProgressChannel
    trigger: ProgressChannel.drain(request_key)
    logic: >
      IF 以鍵 K 呼叫 drain
      THEN 回傳的事件集合是「經鍵 K 的 publish 寫入且尚未被取出」的那些，
      不含任何其他鍵寫入的事件。
    violation_behaviour: >
      違反即跨帳號內容外洩：現狀下請求 A 會收到請求 B 產生的架構圖 XML
      （不是「A 收不到」，是 A 拿到另一位使用者的圖）。這是 ADR-0006 的 IAM 面
      而非單純競態（`requirements.md:808` 的 IAM 列第 ④ 項逐字如此判定），
      而修法是**隔離**而非加授權。
    source: FR13.2、AC13.1.1

  - id: BR2.1
    statement: 請求結束時必須關閉通道，且關閉由呼叫端的 try/finally 擁有
    category: constraint
    applies_to: ProgressChannelRegistry
    trigger: 請求結束（正常或異常）
    logic: >
      IF 一個請求的生命週期結束
      THEN 呼叫端在 `finally` 區塊呼叫 `ProgressChannel.close(request_key)`，
      使該鍵自 registry 移除。
    violation_behaviour: >
      只寫不刪會把跨使用者錯送換成**無上界的記憶體成長**——修掉一個失敗模式
      換來另一個（ADR-014 逐字）。而後者更難發現：沒有錯誤訊息，只有緩慢的
      記憶體曲線。
    source: ADR-014、`contract-summary.md` K-18 `ProgressChannel.close`、`[Q2]`=A

  - id: BR2.2
    statement: close 必須冪等
    category: constraint
    applies_to: ProgressChannel
    trigger: ProgressChannel.close(request_key)
    logic: >
      IF 該鍵已不存在或已關閉
      THEN 視為成功，不拋例外。
    violation_behaviour: >
      非冪等會使 BR2.1 的 `finally` 在「正常路徑已關閉 ＋ 異常路徑再關一次」時
      拋出第二個例外，覆蓋掉原始失敗原因。
    source: `contract-summary.md` K-18 `retry_and_idempotency` 第 2 項

  - id: BR2.3
    statement: 被中途放棄的請求結束後，其鍵不得殘留
    category: constraint
    applies_to: ProgressChannelRegistry
    trigger: 客戶端斷線或請求被取消，使 SSE generator 未跑完即被關閉
    logic: >
      IF 一個請求的回應 generator 被關閉而非跑到結尾
      THEN 該請求的鍵在 generator 關閉後不得存在於 registry。
    violation_behaviour: >
      殘留即 BR2.1 要防的無上界成長，只是走的是異常路徑。
      **本規則必須以一條測試承載，不得只以推論成立**（`[Q2]`=A 的逐字理由）：
      Starlette 在客戶端斷線時會關閉回應 generator，`finally` 因此會跑，
      但「因此會跑」是推論而不是證據——若 generator 是被 GC 而非顯式 `aclose()`，
      `finally` 的執行時機不保證。
    source: `[Q2]`=A

  - id: BR2.4
    statement: drain 不存在的鍵必須回空迭代器，不得拋例外
    category: constraint
    applies_to: ProgressChannel
    trigger: ProgressChannel.drain(request_key) 且該鍵不存在或已關閉
    logic: >
      IF 鍵不存在或已關閉
      THEN 回傳空的 AsyncIterator。
      **已關閉與從未存在在對外行為上不可區分**——否則呼叫端能分辨「那個鍵曾經
      存在」，而鍵的不可猜性是本單元唯一的可見性機制。
    violation_behaviour: >
      現狀是崩潰：`_drain_progress` 在 `design_agent.py:163` 對 `None` 呼叫
      `get_nowait()` 拋 `AttributeError`。注意 `FR13.3` 原稿把這個失敗描述為
      「事件被**靜默丟棄**」——**那是錯的**，實測是另一個請求崩潰
      （`[Q-08]`／`[V-02]` 的共同發現）。一條斷言「沒有事件被靜默丟棄」的 AC
      會在修前與修後都通過，所以 `AC13.1.2` 改為斷言「**仍收到**自己的事件」。
    source: FR13.3、AC13.1.2、`contract-summary.md` K-18 `ProgressChannel.drain`

  - id: BR3.1
    statement: 對外的錯誤一律為固定訊息，不含內部例外原文
    category: constraint
    applies_to: ProgressEvent
    trigger: 本單元任一操作對外回報失敗
    logic: >
      IF 要把失敗回報給使用者
      THEN `content` 為預先定好的固定字串，不得由例外物件的字串表示拼接而成。
    violation_behaviour: >
      現狀的 `AttributeError` **原文被送進 SSE 給使用者**。內部例外文字外洩是
      獨立於錯送之外的第二個 ADR-0006 面，而 `FR13` 原稿完全沒提這件事
      （`AC13.1.3` 為本輪新發現）。
    source: AC13.1.3、`[Q-08]`、`[V-02]`

  - id: BR3.2
    statement: publish 到不存在的通道必須記 log 並丟棄該事件，不得崩潰也不得靜默成功
    category: constraint
    applies_to: ProgressChannel
    trigger: ProgressChannel.publish(request_key, event) 且該鍵不存在
    logic: >
      IF 鍵不存在或已關閉
      THEN 記一筆 log（含鍵與事件類別，**不含** `content`），丟棄該事件，正常返回。
    violation_behaviour: >
      崩潰會讓一個已經結束的請求把還在跑的請求弄壞；靜默成功則讓「事件寫去哪了」
      完全無跡可循，而這正是 `BR2.1` 違反後最可能的症狀，必須留得下痕跡才查得到。
      log 不含 `content` 是因為 `xml` 可能是使用者的架構圖內容。
    source: `contract-summary.md` K-18 `ProgressChannel.publish`、`project.md` 的
      「`try/except` 只用在外部依賴邊界且必須降級或記 log，不得靜默」

  - id: BR4.1
    statement: 單一通道的事件數有上界；滿載時丟棄最舊的 progress 事件，xml 與 error 永不丟棄
    category: constraint
    applies_to: ProgressChannel
    trigger: ProgressChannel.publish 且 buffer 已滿
    logic: >
      IF buffer 已達上界
      THEN 自最舊端起尋找第一則 `type` 為 `progress` 的事件並丟棄它，再寫入新事件；
      IF buffer 內已無 `progress` 類可丟
      THEN 不丟棄任何 `xml` 或 `error`，而是以 `BR4.2` 的方式記錄並拒絕寫入新的
      `progress`（新的 `xml`／`error` 仍須寫入——必要時 buffer 暫時超過上界）。
    violation_behaviour: >
      丟棄 `xml` 會讓使用者看到一次「成功但沒有圖」的產圖；丟棄 `error` 會讓一次
      失敗變成無聲無息。兩者都比丟掉一則進度訊息嚴重得多——進度訊息的價值是
      「還在動」，舊的那一則已無資訊。
      **阻塞生產者不是選項**（`[Q4]` 的選項 C）：生產者是 agent 的執行路徑，
      阻塞它等於讓一個慢的或已斷線的消費者拖住產圖，把記憶體問題換成可用性問題。
    source: `[Q4]`=A

  - id: BR4.2
    statement: 任何因容量而被丟棄的事件必須留下可觀察痕跡
    category: constraint
    applies_to: ProgressChannel
    trigger: 依 BR4.1 丟棄事件時
    logic: >
      IF 有事件因容量被丟棄
      THEN 記一筆 WARN 級 log（含鍵與被丟棄的事件類別、累計丟棄數，**不含**
      `content`）。
    violation_behaviour: >
      無聲丟棄使「使用者說少看到東西」這類回報無法被查證，與 `project.md` 的
      「Errors must be surfaced／不得靜默」同一條紀律。
    source: `[Q4]`=A 的連帶、`construction.md` 的「silent failures are not acceptable」

  - id: BR5.1
    statement: 被取代的五個既有符號不得以舊形式繼續存在於 repo
    category: policy
    applies_to: 既有程式（design_agent.py、wa_collab_orchestrator.py）
    trigger: 本單元宣告完成之前
    logic: >
      IF 要宣告 `U22` 完成
      THEN `design_agent.py:31` 的 `_progress_queue`、`:32` 的 `_last_xml`、
      `:218` 把全域設為 `None` 這三者已刪除；`:160` 的 `_drain_progress` 已改寫為
      呼叫 `ProgressChannel.drain`；`wa_collab_orchestrator.py:79` 已補傳 per-request
      的鍵。
    violation_behaviour: >
      舊符號留著即等於新通道只是多了一條路徑而非取代——錯送路徑仍然可達。
      本規則是**可 grep 的條件**，不需判斷。
    source: `contract-summary.md` K-18 `completion_criterion`、US13 DoD、`[CD4]`=A

  - id: BR5.2
    statement: 併發測試必須以 asyncio.Event barrier 釘住交錯順序，不得以 sleep 製造
    category: policy
    applies_to: 本單元的驗證
    trigger: 撰寫 AC13.1.1／AC13.1.2 的自動化測試時
    logic: >
      IF 要驗證兩個重疊請求的事件互斥
      THEN 以 `asyncio.Event` 釘住交錯點，並斷言兩個集合**互斥且各自非空**。
    violation_behaviour: >
      品質 agent 實測：`sleep` 版本**會通過**（假綠燈）；而
      `frontend/playwright.config.ts:17` 與 `ui-regression` 都容忍 flaky，
      所以一個 flaky 的併發測試等於沒有測試。
      「各自非空」那一半同樣不可省——開發者實跑顯示現狀下 A 的事件集合為**空**
      而 B 收到 A 的產出，於是「互斥」在壞碼上**真空成立**，只斷言互斥會通過。
    source: US13 DoD、`[Q-07]`、`[US:V-02]`
```

---

## 人讀摘要

**共 13 條規則。** 類別分佈：`constraint` **10**、`validation` **1**（`BR1.2`）、
`policy` **2**（`BR5.1`、`BR5.2`）、`authorization` **0**、`calculation` **0**。

> 這些數字由腳本解析上方 fenced yaml 區塊的 `- id:` 與 `category:` 兩欄算出
> （`13 | unique: 13`、`{'constraint': 10, 'validation': 1, 'policy': 2} | total: 13`），
> 不是目視。**初稿寫「11 條、constraint 9」，兩個都錯且加起來還是 12**——
> 這正是 `delivery-planning:dp-L1` 記的那條（任何可被計算的數字要先算再寫），
> 寫下來之前沒跑那段程式。`authorization` 為 0 的理由見檔頭：本單元無受保護操作。

| 群 | 規則 | 管什麼 |
|---|---|---|
| BR1 | `BR1.1`／`BR1.2`／`BR1.3` | 鍵的來源與隔離不變量 |
| BR2 | `BR2.1`／`BR2.2`／`BR2.3`／`BR2.4` | 生命週期：建立、關閉、異常關閉、讀不存在的鍵 |
| BR3 | `BR3.1`／`BR3.2` | 失敗時不外洩、不崩潰、不靜默 |
| BR4 | `BR4.1`／`BR4.2` | 容量上界與丟棄優先序 |
| BR5 | `BR5.1`／`BR5.2` | 舊符號退場、測試方法 |

### 哪幾條是「現狀會讓它紅燈」的

這很要緊，因為一條在修前與修後都通過的規則不保護任何東西：

| 規則 | 現狀 | 修後 |
|---|---|---|
| `BR1.3`（隔離） | **紅** —— A 收到 B 的 `xml` | 綠 |
| `BR2.4`（讀不存在的鍵不崩潰） | **紅** —— `AttributeError` | 綠 |
| `BR3.1`（不外洩例外原文） | **紅** —— 原文進 SSE | 綠 |
| `BR1.2`（不靜默覆寫） | **紅** —— `:183` 直接指派 | 綠 |
| `BR2.1`／`BR2.3`（清除） | 現狀的 `:218` 設 `None` 既非清除也非隔離——**不適用**（它沒有 per-key 可刪） | 綠 |
| `BR4.1`／`BR4.2`（容量） | 現狀 `asyncio.Queue()` 無上界——**紅**（但未被觀察到） | 綠 |
| `BR5.1`（舊符號退場） | **紅**（定義上） | 綠 |

`BR2.2`（`close` 冪等）與 `BR5.2`（測試方法）在現狀上沒有對應物可比——前者的
操作不存在，後者約束的是測試而非程式。兩者皆非恆真：`BR2.2` 可由一個「重複 close」
的測試驗，`BR5.2` 可由「把 barrier 換成 sleep 後測試仍綠」這個突變驗
（品質 agent 已實測該突變**會**通過，所以這條規則抓的是真的東西）。
