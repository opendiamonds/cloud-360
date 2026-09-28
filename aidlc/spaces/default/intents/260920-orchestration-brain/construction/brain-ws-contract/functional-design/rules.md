# Business Rules — `U2 brain-ws-contract`（`spec`）

## 〇、這個單元的「業務規則」是什麼

本單元沒有業務邏輯——它是型別來源。所以下面的規則分兩類，**兩類都是真的規則，不是為了
填表**：

1. **契約不變量**（`BR1.*`、`BR2.*`）：訊息形狀必須成立的性質。違反者是**契約被違反**，
   不是使用者輸入錯誤。這些是後端 Pydantic 模型必須強制、CI 閘門必須保護的東西。
2. **消費端義務**（`BR3.*`）：契約保證之外，消費端仍必須自我防衛的行為。
   它們存在的理由是「契約保證」與「防禦性實作」是兩件事——`K-12` 逐字寫過這個立場。
3. **建置期規則**（`BR4.*`）：dump 與型別產生的流程約束。本單元的「副作用」全在建置期
   （`K-02` `behaviour_semantics` 逐字），所以這一類才是它真正的可執行面。

## 一、source of truth

```yaml
rules:
  # === BR1.* 封包層的契約不變量 ===
  - id: BR1.1
    statement: 每一則訊息的 v 必須恰為當前協定版本的字面值
    category: validation
    applies_to: WsEnvelope.v／WsClientEnvelope.v（皆字面 1）；WsUnvalidatedEnvelope.v 為例外
    trigger: 任何一則訊息的序列化或反序列化
    logic: >
      IF 出站或已驗證訊息的 v 不等於 1 THEN 該訊息不符合本版契約。
      **WsUnvalidatedEnvelope.v 是本規則的明文例外**（審查 R-18）：它的存在目的就是
      表示不符本版的值，以便取得 K-12 的 4400 所需的 received。
      伺服器對 hello 的不相容以關閉碼 4400 處置（該處置屬 K-12／U13，不屬本單元）；
      本單元的責任是讓「不等於 1」在**型別層**就無法構造。
    violation_behaviour: >
      型別檢查失敗（`tsc -b` 紅燈）。這是刻意的：升版時把字面值改為 2 會讓所有仍寫 1 的
      消費端立即紅燈，而不是在執行期拿到未定義值。
    source: Q2=A ＋ Q6=A；機制來自 K-12 x-handshake

  - id: BR1.2
    statement: 封包的 payload 形狀必須由 type 唯一決定
    category: constraint
    applies_to: WsEnvelope 與 WsClientEnvelope（兩個方向各自的判別 union）
    trigger: 任何一則訊息的處理
    logic: >
      IF 已知 type THEN payload 的形狀唯一確定（discriminated union，判別欄位為 type）。
      不得存在同一個 type 對應兩種 payload 形狀的情形。
    violation_behaviour: 型別無法產生（聯集無法判別），dump 階段即失敗
    source: K-02 envelope；本站明文化

  - id: BR1.3
    statement: turnId 在同一輪回覆的所有訊息中必須相同，終止事件亦帶它
    category: constraint
    applies_to: WsEnvelope.turnId（**只有伺服器方向**——客戶端封包已無此欄位，見 R-20）
    trigger: 一輪回覆的任何一則訊息
    logic: >
      IF 兩則訊息屬同一輪 THEN 它們的 turnId 相等。
      IF 訊息是終止事件（done 或 error）THEN 它仍帶 turnId。
    violation_behaviour: >
      消費端無法把訊息歸到正確的一輪。**本單元只能在型別層強制「turnId 必填」，
      無法強制「同一輪相同」**——後者是執行期性質，屬 U13。此處如實記載這個界線。
    source: >
      K-02 envelope.required_fields 逐字。
      **適用範圍（審查 R-05 收窄）**：本規則只適用 WsEnvelope（伺服器方向）。
      WsClientEnvelope 的 turnId 是**選填**——hello 發生在任何一輪之前，
      set_sharing_mode 與 set_work_target 是狀態訊息、依 BR2.7 不屬任何一輪，
      三者都無法給出有意義的值；且 turnId 由伺服器產生（U13），客戶端本來就沒有它。
      把它對客戶端定為必填會要求客戶端捏造一個值。

  - id: BR1.4
    statement: 兩個 type 列舉的成員數必須等於對應方向 payload 實體的個數
    category: constraint
    applies_to: WsServerMessageType／WsClientMessageType 與 entities.md 的 payload 集合
    trigger: 契約變更（新增或移除訊息型別）
    logic: >
      IF WsServerMessageType 有 n 個值 THEN 恰有 n 個 server→client payload 實體，且一一對應。
      客戶端方向同理。**目前 n=9（含 ready）與 m=6（含 select_clarify_candidate）。**
      **可實作判定式（審查 R-11 補；初版只說「同名」而那在實際命名下不成立）**：
      (1) payload 實體的判定式為「名稱以 `Payload` 結尾者」——此式**排除**
      ClarifyCandidate 與 WorkItem 兩個被組成的子實體，也排除三個 Envelope 與兩個列舉；
      (2) 對應關係為 snake_case→PascalCase 再加 `Payload` 後綴，例如
      `work_items` → `WorkItemsPayload`、`cost_card` → `CostCardPayload`、
      `select_clarify_candidate` → `SelectClarifyCandidatePayload`；
      (3) 斷言三件事：每個 type 正規化後存在同名 payload、每個 payload 反推回某個 type、
      兩集合等勢。
    violation_behaviour: >
      有 type 沒有 payload 形狀（消費端無從處理），或有 payload 沒有 type（永不可達的死碼）。
      **這是可機械驗證的**，判定式見上；dump 腳本可直接實作。
    source: >
      本站新增（實算 entities.md 的實體時發現這個不變量沒有被任何地方寫下來）。
      **審查 R-01／R-02 新增兩個 type 後，本規則立刻起了作用**：它要求同時新增
      ReadyPayload 與 SelectClarifyCandidatePayload，否則兩個新 type 會成為沒有形狀的死值。

  - id: BR1.5
    statement: 終止事件 payload 的 turnId 必須等於其 envelope 的 turnId
    category: constraint
    applies_to: DonePayload.turnId／ErrorPayload.turnId 與 WsEnvelope.turnId
    trigger: 伺服器送出 done 或 error
    logic: >
      IF 訊息為 done 或 error THEN payload.turnId == envelope.turnId。
    violation_behaviour: >
      消費端可讀到兩個不同值而無人察覺——它會把終止事件歸到錯誤的一輪。
    source: >
      **審查 R-12 新增。** turnId 在終止事件上有**兩份物化**（envelope 一份、payload 一份），
      這是沿用 K-02:267／:269 的原形狀，但上游與本站初版都沒有任何規則要求兩者相等
      ——BR1.3 只談 envelope 的 turnId。team.md `## Code Style` 的「單一真實來源」逐字要求：
      確實無法避免的副本，其同一個 PR 必須一併新增鎖住兩者一致的測試。
      **為何保留兩份而不刪 payload 那份**：K-02 是已核可契約且該形狀在它的 types 區塊內逐字寫明，
      刪它屬修改上游；補一條可機械斷言的一致性規則成本更低且不動上游。
      **可機械驗證**：後端模型的 validator 可直接斷言，建議在 code-generation 實作。

  - id: BR1.6
    statement: 伺服器訊息的 turnId 必為非 null（輪次訊息）或必為 null（非輪次訊息），二者互斥且窮盡
    category: constraint
    applies_to: WsEnvelope.turnId 與 WsServerMessageType 的九個值
    trigger: 伺服器構造任何一則訊息
    logic: >
      IF type 在 {token, clarify, cost_card, done, error} THEN turnId 非 null。
      IF type 在 {ready, sharing_mode, work_target, work_items} THEN turnId 為 null。
      兩個集合互斥且聯集等於九個 type 的全部——**可機械斷言**（集合運算）。
    violation_behaviour: >
      非輪次訊息帶了一個沒有意義的 turnId（消費端會把狀態訊息誤歸到某一輪），
      或輪次訊息缺 turnId（消費端無法歸輪）。
    source: >
      **審查 R-14（Critical）新增。** 初版把 WsEnvelope.turnId 定為不可 null 的必填，
      而本站自己明文宣告四種伺服器訊息不屬任何一輪（ReadyPayload 的 entity_constraints
      逐字「它在任何一輪之前送出」、functional-spec.md §二 逐字「它們不屬於任何一輪」）
      ——那四者被要求攜帶一個它們沒有的值。
      **審查 R-05 只修了一半**：它為客戶端封包開了例外，對這四個伺服器訊息一字未提。

  # === BR2.* payload 層的契約不變量 ===
  - id: BR2.1
    statement: token 的 text 必須是非空白字串
    category: validation
    applies_to: TokenPayload.text
    trigger: 伺服器送出 token
    logic: IF text 去除空白後為空 THEN 不得送出該 token
    violation_behaviour: >
      送出空白 token 會讓「已產出內容」的判定失真，進而使 BR2.6（零內容不得以 done 結束）
      被繞過。
    source: K-02 逐字「非空白」＋ K-12 x-termination-semantics.done.precondition

  - id: BR2.2
    statement: clarify 的 candidates 不得為空陣列
    category: validation
    applies_to: ClarifyPayload.candidates
    trigger: 伺服器送出 clarify
    logic: IF 沒有候選判讀 THEN 不送 clarify（改送 error 或依 U11 的規格處置）
    violation_behaviour: 使用者看到「請選一個」但沒有可選項
    source: 本站新增（K-02 未規定最小長度；空陣列在語意上無意義）

  - id: BR2.3
    statement: confidence 必須是選填，且不得被改為必填
    category: constraint
    applies_to: ClarifyCandidate.confidence
    trigger: 契約變更
    logic: >
      IF 有人把 confidence 改為必填 THEN 違反上游。
      理由不只是 components.md 逐字要求——OQ-10 質疑路由層能否產出可比較的信心值，
      容許 null 使該 OQ 若收斂為「不能」時本型別不需改動。
    violation_behaviour: 若路由層無法產出信心值，必填會讓整個 clarify 路徑無法構造
    source: components.md 逐字、mockups.md H-2；OQ-10 的風險由 stories.md:655–657 記載

  - id: BR2.4
    statement: confidence 若非 null，其值必須落在 0 到 1（含端點）
    category: validation
    applies_to: ClarifyCandidate.confidence
    trigger: 伺服器構造 clarify 候選
    logic: IF confidence 非 null 且（< 0 或 > 1）THEN 違反契約
    violation_behaviour: >
      門檻比較（AC1.2.1 的 `< 0.7`）失去意義。**門檻判斷本身在 U11**，本規則只保證
      傳輸的值在可比較的定義域內。
    source: AC1.2.4 逐字「定義域 0–1 的信心值可與門檻比較」

  - id: BR2.5
    statement: work_item 的 status 為「等待中」時 waitingOn 應非 null；為「失敗」時 failureReason 應非 null
    category: constraint
    applies_to: WorkItem
    trigger: 伺服器構造 work_items
    logic: >
      IF status == "等待中" THEN waitingOn 非 null。
      IF status == "失敗" THEN failureReason 非 null。
    violation_behaviour: >
      畫面顯示「等待中」卻不說在等什麼、「失敗」卻不說原因。
      **本規則在型別層無法強制**（需要相依型別），故它是後端模型的驗證責任；
      如實記載這個限制而不假裝型別能擋住它。
    source: >
      本站新增（K-02 定義了三個欄位但未定義它們之間的關係）。
      **⚠ 前半句的觸發條件依賴一個未解的開放問題（審查 R-10）**：「等待中」狀態的
      **可達性本身**是 H-3——domain-design/components.md:485 逐字「`等待中` 狀態的可達性：
      何謂『一個意圖依賴另一個意圖的結果』」，contract-summary.md:1426 把它掛在 K-11／U12、
      :1466（J-3）指派 functional-design。依 project.md 的自檢 1（每條「偵測 X 狀態」的規則
      先驗 X 可達），若 H-3 收斂為「不可達」，本規則的前半句即為死碼而在文件上看起來已解決。
      **這個結論不影響本站的型別形狀**：waitingOn 欄位無論如何都要存在（K-02 逐字列它），
      改變的只是它是否有非 null 的實際取值。落點 U12／K-11。

  - id: BR2.6
    statement: 零內容不得以 done 結束；上游無有效回覆時必須送 error(EMPTY_RESPONSE)
    category: policy
    applies_to: DonePayload／ErrorPayload
    trigger: 一輪回覆結束
    logic: >
      IF 本輪未產出任何非空白內容 THEN 送 error(code: EMPTY_RESPONSE)，**不得**送 done。
      內部推理、控制事件與空白不算內容。
    violation_behaviour: 使用者看到空白的成功態——比看到錯誤更糟，因為它不可診斷
    source: K-12 x-termination-semantics.empty_upstream 逐字；N-14

  - id: BR2.7
    statement: 每一輪（同一 turnId）最多只能有一個終止事件，終止後不得再送內容
    category: constraint
    applies_to: WsEnvelope（done／error）
    trigger: 一輪回覆的訊息序列
    logic: >
      IF 已送出 done 或 error THEN 該 turnId 不得再有任何訊息。
      **work_target 與 sharing_mode 不是終止事件**，不計入此上限（K-02 逐字）。
    violation_behaviour: 消費端的狀態機無法判定一輪是否結束
    source: K-12 x-termination-semantics.at_most_one 逐字

  - id: BR2.8
    statement: error 的 code 必須取自封閉列舉；新增成員必須改契約
    category: validation
    applies_to: ErrorPayload.code
    trigger: 伺服器送出 error
    logic: >
      IF code 不在 {EMPTY_RESPONSE, INTERNAL_ERROR, UNAUTHORIZED, INVALID_REQUEST} THEN 違反契約。
      **各 code 的判準（審查 R-04 補；初版只列值未給判準）**：
      EMPTY_RESPONSE ＝ 上游結束但無有效回覆；
      INVALID_REQUEST ＝ **客戶端請求本身不合法**（作業對象三層解析不出、階層不一致、
      candidateId 格式錯誤等）——**不得**把使用者輸入問題報成 INTERNAL_ERROR；
      UNAUTHORIZED ＝ 有權限問題但連線仍在（連線建立期的無權限走 4403 關閉，不走這裡）；
      INTERNAL_ERROR ＝ 以上皆非的伺服器端失敗。
      新增一個 code 必須改後端 Pydantic 模型、重跑 dump、重產型別檔、兩道 gate 通過。
    violation_behaviour: >
      前端的窮盡 switch 收到未知 code。封閉列舉的價值就在這裡：漏處理會被 tsc 抓到。
    source: >
      Q1=A（本站定義）＋ 審查 R-04（補 INVALID_REQUEST 與判準）。
      **K-02 有兩處指向 K-12 的懸空 code 引用，而 K-12 未定義它**：:269（error 型別的
      note）與 :308（work_target 失敗回應）。K-12 的 x-close-codes 是 WebSocket 關閉碼
      （4401／4403／4400／1011），不是 error 訊息的 code。初版只處理了 :269 那一處。
      **INVALID_REQUEST 的由來**：contract-summary.md:288 逐字「失敗回 error」、
      :308 逐字「授權或**解析**失敗回 error」——「解析失敗」在三值下無處可歸。

  - id: BR2.9
    statement: error 的 message 不得包含內部實作細節
    category: policy
    applies_to: ErrorPayload.message
    trigger: 伺服器構造 error
    logic: IF message 含堆疊、SQL、內部路徑或模組名 THEN 違反
    violation_behaviour: 對外洩漏實作細節；`construction.md` 護欄逐字要求不得如此
    source: >
      `.claude/knowledge/aidlc-developer-agent/code-generation-patterns.md` 的錯誤訊息規則
      ＋ `phases/construction.md` `## Security`

  - id: BR2.10
    statement: sideEffect 的兩個哨兵值語意不得被合併或省略
    category: constraint
    applies_to: WorkItem.sideEffect
    trigger: 型別產生與消費端處理
    logic: >
      IF sideEffect == "none" THEN 確定沒有副作用。
      IF sideEffect == "unknown" THEN 系統誠實地不知道（**不是「還沒填」**）。
      ELSE 該字串是副作用的描述。
    violation_behaviour: >
      把 unknown 當成 none 處理，等於對使用者宣稱「停掉不留半成品」——而
      components.md 逐字說系統不承諾這件事。
      **型別層無法保護這個語意**（TS 會把聯集塌縮為 string），故產生的型別檔
      **必須**在該欄位保留說明註解。這是 BR4.4 的由來。
    source: Q3=A；components.md 逐字

  - id: BR2.11
    statement: cost_card 的 estimateSetId 必須為必填整數
    category: constraint
    applies_to: CostCardPayload.estimateSetId
    trigger: 契約變更
    logic: IF 有人把它改為選填 THEN 違反 K-02 X-01 的不變量
    violation_behaviour: 成本卡片無法連回估價集合
    source: K-02 X-01 逐字

  - id: BR2.12
    statement: 客戶端訊息不得攜帶身分
    category: authorization
    applies_to: 全部 client→server payload
    trigger: 契約變更（新增客戶端訊息或欄位）
    logic: >
      IF 任何 client→server payload 含使用者 id、角色、token 或等價欄位 THEN 違反。
      principal 綁在連線上（握手時由 Sec-WebSocket-Protocol 的 token 建立）。
    violation_behaviour: >
      客戶端可自稱任何身分——一個授權繞過。**本規則是本單元唯一的授權相關規則**，
      且它是**否定式**的（不得有某種欄位），因為本契約本身不含任何受保護操作
      （K-02 behaviour_semantics.authorization_responsibility 逐字「無」）。
    source: K-12 x-authorization-responsibility.per_connection_principal 逐字

  - id: BR2.13
    statement: 客戶端訊息不得攜帶 turnId；伺服器收到即視為協定違規
    category: validation
    applies_to: WsClientEnvelope 與六個 client payload
    trigger: 伺服器收到任何客戶端訊息
    logic: >
      IF 客戶端訊息含 turnId 欄位 THEN 協定違規：伺服器**拒絕該訊息**並回
      error(code: INVALID_REQUEST)，不得靜默忽略。
    violation_behaviour: >
      客戶端可指定它不該持有的伺服器端識別。靜默忽略比拒絕更糟——客戶端會以為自己
      成功指定了輪次。
    source: >
      **審查 R-20（Major）新增。** 初版把 turnId 定為客戶端封包的選填欄位，同時宣告
      「turnId 由伺服器產生（U13），客戶端沒有它」——客戶端沒有合法理由寫它卻被允許寫，
      且無任何規則要求伺服器忽略或拒絕（BR2.12 只禁止攜帶「身分」）。
      本規則與 entities.md 的欄位移除兩者合起來才關閉這個缺口：型別上不可構造 ＋
      執行期明確拒絕。

  - id: BR2.14
    statement: select_clarify_candidate 的 candidateId 為 null 時伺服器結束該輪且不送任何狀態訊息
    category: policy
    applies_to: SelectClarifyCandidatePayload.candidateId
    trigger: 伺服器收到 select_clarify_candidate
    logic: >
      IF candidateId 非 null THEN 依該候選交辦（AC1.2.2），流程回到 US1.1 第一步。
      IF candidateId 為 null THEN 該輪結束：**不送 work_target、不送 work_items、
      不送任何終止事件**（AC1.2.3 的「脈絡列與作業對象不變」）；客戶端據此自行回到輸入狀態。
      **前提**：客戶端**不得**在使用者未做選擇時送出本訊息。
    violation_behaviour: >
      送 work_target 會違反 AC1.2.3 的「不變」；送終止事件（done 會是零內容、
      違反 BR2.6；error 會讓使用者以為出錯）；不定義則實作者無從選擇。
    source: >
      **審查 R-19（Major）＋ R-15（Critical）新增。** 採審查給的選項 (b)：保留一欄兩義，
      但把伺服器處置與客戶端前提寫成規則。
      **必須如實記載的限制**：一欄兩義使「使用者按了都不是」與「客戶端把欄位序列化成 null」
      在傳輸上**完全不可區分**——本契約無法區分它們，而 null 在本契約其他各處一貫表示
      「沒有值／尚未設定」（WorkTargetPayload 三個 null、waitingOn、failureReason、
      confidence），此處卻被賦予肯定性使用者動作的語意。
      **不改為明確判別欄位（審查建議的 (a)）的理由**：那會再次改動 payload 形狀，
      而本輪已因 R-01／R-02 兩次擴充 K-02；把第三次擴充留給上游追認時一併裁決，
      並在此明記本形狀的可區分性缺陷。**這一項應列入核可關卡的 open items。**

  # === BR3.* 消費端義務（契約保證之外的防禦）===
  - id: BR3.1
    statement: 前端對 error.code 必須窮盡處理
    category: policy
    applies_to: 消費端（U14）
    trigger: 收到 error
    logic: IF 收到 error THEN 對**四個** code（EMPTY_RESPONSE／INTERNAL_ERROR／UNAUTHORIZED／INVALID_REQUEST）各有明確處置；EMPTY_RESPONSE 須顯示明確錯誤提示
    violation_behaviour: 使用者看到未處理的錯誤或空白畫面
    source: K-12 x-termination-semantics.client_obligations 逐字

  - id: BR3.2
    statement: 前端對未知的 type 必須安全忽略而非崩潰
    category: policy
    applies_to: 消費端（U14）
    trigger: 收到 type 不在已知列舉內的訊息
    logic: >
      IF type 未知 THEN 忽略該訊息並記錄異常，**不得**崩潰、不得中斷該輪的其餘訊息。
      這種情況在契約上不可能（版本相等即型別相同），但防禦性實作不假設對方守約。
    violation_behaviour: 一則未知訊息讓整個連線失效
    source: >
      本站新增（與 BR3.3 同一個立場：契約保證與防禦性實作分開）。
      **型別上的承載（審查 R-03 的連帶）**：WsUnvalidatedEnvelope 的 type 刻意定為寬鬆字串
      而非列舉——若收窄為列舉，「未知 type」在型別層就不可表示，本規則將無從實作。

  - id: BR3.3
    statement: 前端收到零內容的 done 必須視為契約違規，顯示備援提示並記錄異常
    category: policy
    applies_to: 消費端（U14）
    trigger: 收到 done 而本輪未收到任何非空白 token
    logic: >
      IF done 到達且本輪內容為空 THEN 視為**契約違規**：顯示備援提示、記錄異常，
      **不得呈現空白成功態**。
    violation_behaviour: >
      呈現空白成功態——使用者以為系統回答了但什麼都沒有，且無任何診斷線索。
    source: >
      K-12 x-termination-semantics.client_obligations 逐字；N-14。
      **這是 J-10 指派的兩種情境之一**，實質內容在 functional-spec.md §四。

  - id: BR3.4
    statement: 前端不得自動重送未收到終止事件的 user_message
    category: policy
    applies_to: 消費端（U14）
    trigger: 連線中斷且該輪未收到 done 或 error
    logic: >
      IF 未收到終止事件 THEN 該輪標為未完成，**不自動重試**；使用者自行重問。
      user_message 是**非冪等**的——每則觸發一輪分類與可能的交辦。
    violation_behaviour: 重複交辦同一個需求，可能產生重複的工作項與重複的副作用
    source: K-12 x-retry-and-idempotency.user_message ＋ x-disconnect-behaviour（[C5]=B）

  - id: BR3.5
    statement: 前端收到 ready 後必須驗證 protocolVersion 等於本版，不符即視為協商失敗
    category: policy
    applies_to: 消費端（U14）／ReadyPayload.protocolVersion
    trigger: 收到 ready 訊息
    logic: >
      IF ready.protocolVersion != 1 THEN 視為協商失敗：停止送出任何後續訊息並提示重新載入。
      IF 相等 THEN 握手完成，可開始送 user_message。
    violation_behaviour: >
      protocolVersion 成為無讀取端的欄位——伺服器宣告了接受的版本而沒有人核對，
      於是「伺服器接受了 v=1」與「伺服器回了一則 ready」無法區分。
    source: >
      **本輪送審前自檢第 2 項查出並補入。** ReadyPayload.protocolVersion 在補入時全域
      命中數為 1（只有自己的宣告），**與審查 R-02 在 ClarifyCandidate.id 上抓到的
      懸空欄位是同一形狀**——我在修 R-01 的同一個動作裡新造了一個。
      補這條規則即為它指定讀取端；替代方案是把 ReadyPayload 改為空 payload，
      但那會讓「ready 到了」與「ready 的內容正確」無法區分。

  # === BR4.* 建置期規則（本單元真正的可執行面）===
  - id: BR4.1
    statement: 規格檔與型別檔皆為衍生物，不得手改
    category: constraint
    applies_to: ws-contract.json／frontend/src/types/ws-contract.d.ts
    trigger: 任何人編輯這兩個檔
    logic: >
      IF 有人手改衍生物 THEN 下一次 CI 的對應閘門紅燈。
      唯一真實來源是後端 Pydantic 模型（人手改的那一份）。
    violation_behaviour: >
      手改能讓型別看起來對而後端行為不對——這正是兩道閘門要消除的失敗模式。
    source: K-02 derived_artifacts 逐字「皆 commit 進版控供 CI 比對，但不得手改」

  - id: BR4.2
    statement: dump 的輸出必須與 dict 插入順序無關
    category: constraint
    applies_to: ws-contract.json
    trigger: 執行 dump
    logic: >
      IF dump 的序列化未固定鍵序 THEN 同一份模型可能產生不同位元，閘門變成假紅燈。
      形狀比照既有的 openapi dump：indent=2、sort_keys=True、ensure_ascii=False、尾端換行。
    violation_behaviour: CI 在程式碼沒變時紅燈，閘門失去信任並被繞過
    source: K-02 derived_artifacts.note 逐字

  - id: BR4.3
    statement: 兩道閘門必須都存在，缺第二道時型別檔可以靜默過期
    category: constraint
    applies_to: CI（backend job 與 frontend job）
    trigger: CI 執行
    logic: >
      第一道（backend）驗「規格檔 == 後端程式碼」；第二道（frontend）驗
      「committed 的型別檔 == 由規格檔重產的型別檔」。
      IF 只有第一道 THEN 開發者重新 dump 了規格卻忘了重產型別檔時，型別檔仍宣告舊形狀，
      而 `tsc -b` 檢查的是「用法是否符合型別檔」、**不是**「型別檔是否符合規格檔」
      ——那條路徑會靜默通過，前端在執行期拿到未定義值。
    violation_behaviour: 見上（靜默通過）
    source: K-02 ci_gates.why 逐字；理由沿用既有 frontend/scripts/check-api-types.mjs 註解

  - id: BR4.4
    statement: 產生的型別檔必須保留 sideEffect 兩個哨兵值的說明註解
    category: constraint
    applies_to: frontend/src/types/ws-contract.d.ts
    trigger: 型別產生
    logic: >
      IF 型別產生器丟掉註解 THEN "none" 與 "unknown" 的語意在消費端完全消失
      （因為 TS 把 `"none" | "unknown" | string` 塌縮為 `string`，IDE 不提示字面值）。
      故產生器必須把 entities.md 對該欄位的說明帶進型別檔。
    violation_behaviour: 見 BR2.10——把 unknown 當 none 處理是對使用者的錯誤承諾
    source: Q3=A 的直接後果；本站新增

  - id: BR4.5
    statement: 型別產生器的版本必須與 package.json 釘同一版
    category: constraint
    applies_to: 型別產生流程
    trigger: 依賴升級
    logic: >
      IF 產生器版本未釘 THEN 不同機器可能產生不同型別檔，第二道閘門變成假紅燈。
    violation_behaviour: 同 BR4.2 的失敗模式（閘門失去信任）
    source: K-02 derived_artifacts 逐字「產生器版本須與 package.json 釘同一版」

  - id: BR4.6
    statement: dump 與型別產生必須冪等
    category: constraint
    applies_to: 兩個衍生物的產生流程
    trigger: CI 重跑
    logic: IF 同一份後端模型 THEN 必產生同一份輸出（sort_keys=True 使結果與插入順序無關）
    violation_behaviour: CI 無法重跑，閘門不可靠
    source: K-02 behaviour_semantics.retry_and_idempotency 逐字
```

## 二、規則摘要表（由上方 yaml 衍生）

| 類別 | 規則數 | 規則 id |
|---|---|---|
| 封包層契約不變量 | 6 | `BR1.1`–`BR1.6` |
| payload 層契約不變量 | 14 | `BR2.1`–`BR2.14` |
| 消費端義務 | 5 | `BR3.1`–`BR3.5` |
| 建置期規則 | 6 | `BR4.1`–`BR4.6` |
| **合計** | **31** | — |

依 category 分佈（腳本解析上方 yaml 的 `category:` 欄位實算；清單與數字由同一次解析產生，
**不再分開手寫**——審查 R-21 指出上一版數字對而清單漏了一個 id）：

| category | 規則數 | 規則 id |
|---|---|---|
| `validation` | 6 | `BR1.1`、`BR2.1`、`BR2.2`、`BR2.4`、`BR2.8`、`BR2.13` |
| `constraint` | 16 | `BR1.2`、`BR1.3`、`BR1.4`、`BR1.5`、`BR1.6`、`BR2.3`、`BR2.5`、`BR2.7`、`BR2.10`、`BR2.11`、`BR4.1`、`BR4.2`、`BR4.3`、`BR4.4`、`BR4.5`、`BR4.6` |
| `policy` | 8 | `BR2.6`、`BR2.9`、`BR2.14`、`BR3.1`、`BR3.2`、`BR3.3`、`BR3.4`、`BR3.5` |
| `authorization` | 1 | `BR2.12` |
| `calculation` | 0 | 本單元無計算類規則——它是型別來源，不做任何運算 |
| **合計** | **31** | 與上表的分組合計相符 |

## 三、本站新增的 10 條規則（上游沒有的）

`BR1.4`（兩個列舉與 payload 集合等勢同名）、**`BR1.5`（終止事件 payload 的 turnId 必須等於
envelope 的 turnId——審查 R-12 新增）**、`BR2.2`（clarify 不得空陣列）、
`BR2.5`（status 與 waitingOn／failureReason 的相依）、`BR3.2`（未知 type 安全忽略）、
`BR4.4`（型別檔必須保留 sideEffect 註解）。

**其中三條可機械驗證**，建議在 `code-generation` 時實作為斷言：

| 規則 | 斷言落點 | 判定式 |
|---|---|---|
| `BR1.4` | `dump_ws_contract.py` | 見該規則的 `logic`（`Payload` 後綴 ＋ snake→Pascal 正規化 ＋ 排除子實體） |
| `BR1.5` | 後端模型的 validator | `payload.turnId == envelope.turnId` |
| `BR4.4` | 型別產生後的檢查 | 產生的型別檔在 `sideEffect` 欄位上方存在說明註解 |

`BR2.5` **無法在型別層強制**（需要相依型別），是後端模型的驗證責任；且它的觸發條件
（「等待中」狀態的可達性）本身是未解的 H-3——如實記載，不假裝型別能擋住它。

## 四、三條規則的落點不在本單元（如實標示）

| 規則 | 為何本單元無法強制 | 落點 |
|---|---|---|
| `BR1.3` 的「同一輪 turnId 相同」 | 執行期性質，型別只能強制「必填」 | `U13` |
| `BR2.5` 的欄位相依 | 需要相依型別，TS／Pydantic 皆不便表達 | 後端模型驗證（`U13`） |
| `BR3.1`–`BR3.4` 的消費端義務 | 它們是前端行為，本單元只提供型別 | `U14` |
