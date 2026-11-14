# Business Rules — `U11 intent-router`

> 本檔是本單元**決策邏輯**的唯一真實來源。實體形狀在 `entities.md`；
> 工作流程在 `functional-spec.md`。下方摘要表由腳本自 YAML 產生，不手寫數字。

## 本檔的上游

| 上游 | 它決定了哪些規則 |
|---|---|
| `requirements.md` 的 `FR1.5` | `BR1.1`–`BR1.3`（`prompt_guard` 前置與固定拒絕訊息） |
| `requirements.md` 的 `FR1.1`／`FR1.3`／`FR1.6`／`FR1.7` | `BR2.x`（分類與排序）與 `BR3.x`（反問述詞） |
| `requirements.md` 的 `FR5.1`／`FR5.2` | `BR4.x`（多意圖拆解） |
| `requirements.md` 的 `FR6.1` | `BR5.x`（指涉詞解析） |
| `components.md` 的 `IntentRouter` 宣告 | `BR7.x`（依賴邊界：`SessionContext`、`MemoryStore`） |
| `unit-of-work.md:141`／`:143-154` | 本單元的交付（`:141`）與其**自附的阻塞警語**（`:143-154`） |
| `unit-of-work-story-map.md:116` | 四則故事的範圍界定 |
| `contract-summary.md:745-800`（`K-10`） | `BR6.x`（成本紀律）、`BR8.x`（冪等）、`hard_rules` 的三條轉錄 |

## Source of truth

```yaml
rules_version: 1
unit: intent-router

rules:
  # ── 群組 1：輸入前置與固定拒絕 ──────────────────────────────────────────
  - id: BR1.1
    statement: "每一次入口頁輸入，在呼叫任何 LLM 之前先過既有的 prompt_guard。"
    category: constraint
    applies_to: "分類入口"
    trigger: "收到使用者輸入"
    logic: "IF 輸入到達 THEN 先執行 prompt_guard，再決定是否呼叫模型"
    violation_behaviour: "先呼叫模型再檢查，等於已經把惡意輸入送進去了"
    source: "FR1.5；K-10 的 hard_rules 第三條；project.md ## Mandated 的平台自我竄改預檢"
  - id: BR1.2
    statement: "prompt_guard 命中時不呼叫任何 LLM，回固定拒絕訊息。"
    category: policy
    applies_to: "分類入口"
    trigger: "prompt_guard 命中"
    logic: "IF 命中 THEN 回固定訊息並結束該輪；不產生候選、不建立工作項"
    violation_behaviour: "呼叫了模型即違反——這條的價值正在於省下那次呼叫與其風險"
    source: "FR1.5；AC1.1.3 逐字「系統不呼叫 LLM，並回覆固定的拒絕訊息」"
  - id: BR1.3
    statement: "固定拒絕訊息是一個**有內容的有效回覆**，該輪正常以終止事件結束，不是錯誤。"
    category: policy
    applies_to: "與 U13 的邊界"
    trigger: "BR1.2 觸發後"
    logic: "IF 回固定拒絕訊息 THEN 該輪以 done 結束，不以 error 結束"
    violation_behaviour: "以 error 結束會讓畫面呈現成系統故障，而它其實是系統正確地拒絕了"
    source: "K-10 的 hard_rules 逐字「該固定訊息**是有內容的有效回覆**，正常以 done 結束（[C6]）」"

  # ── 群組 2：分類與候選排序 ──────────────────────────────────────────────
  - id: BR2.1
    statement: "每一次入口頁輸入一律先過分類；不存在跳過分類的快路徑。"
    category: constraint
    applies_to: "分類入口"
    trigger: "任何通過 BR1 的輸入"
    logic: "IF 輸入通過 prompt_guard THEN 必定進入分類，無論它看起來多明確"
    violation_behaviour: "任何快路徑都會讓該路徑上的輸入永遠不產生候選，使 FR1.3 對它靜默永不觸發"
    source: "K-10 的 hard_rules 第一條逐字（[C10]=C），含其理由"
  - id: BR2.2
    statement: "分類的產出是一張**帶排序的候選清單**，不是單一答案。"
    category: constraint
    applies_to: CandidateRanking
    trigger: "分類完成"
    logic: "IF 分類完成 THEN 產出 CandidateRanking，其 candidates 依 rank 遞增"
    violation_behaviour: "只回單一答案會讓 FR1.3 的「列出候選判讀」無料可列"
    source: "[IR1]=A；FR1.3 逐字要求列出候選"
  - id: BR2.3
    statement: "分數是選用的，排序是必須的。"
    category: constraint
    applies_to: CandidateIntent
    trigger: "建立候選"
    logic: "IF 建立候選 THEN rank 必填；score 得為 null"
    violation_behaviour: "要求 score 必填會讓 OQ-10 結論為『無信心訊號』時整個模型失效"
    source: "[IR1]=A；entities.md 的 EC2；OQ-10 的兩種可能結論"
  - id: BR2.4
    statement: "分類器回空候選清單是**失敗**，不是「判不出來」。"
    category: validation
    applies_to: CandidateRanking
    trigger: "分類回傳"
    logic: "IF candidates 為空 THEN 視為分類失敗並走失效路徑；**不得**當作 below_threshold 處理"
    violation_behaviour: "把失敗當成反問，會讓一個壞掉的分類器看起來像在謹慎發問"
    source: "entities.md 的 EC1"
  - id: BR2.5
    statement: "部分候選帶分數時，整張清單視為無分數。"
    category: calculation
    applies_to: "CandidateRanking.scoresAvailable"
    trigger: "建立 ranking"
    logic: "IF 任一候選的 score 為 null THEN scoresAvailable = false"
    violation_behaviour: "對混合清單只拿有分數的那幾個比門檻，會讓判定依賴模型當下給了幾個分數"
    source: "entities.md 的 EC2"

  # ── 群組 3：反問述詞（[IR1]=A 的核心） ─────────────────────────────────
  - id: BR3.1
    statement: "反問與否由單一述詞 `can_single_out(ranking)` 決定，不由任何欄位直接決定。"
    category: calculation
    applies_to: "IntentDecision.below_threshold"
    trigger: "ranking 建立後"
    logic: "below_threshold = NOT can_single_out(ranking)"
    violation_behaviour: "在述詞之外另有一條判定路徑，就會有兩個真實來源"
    source: "[IR1]=A"
  - id: BR3.2
    statement: "`scoresAvailable` 為真時，述詞的求值為「該槽位最高分 ≥ 門檻」。"
    category: calculation
    applies_to: "can_single_out（作用於**一個槽位**的 ranking，修訂 1 釐清）"
    trigger: "對某一槽位求值且該槽位 scoresAvailable 為真"
    logic: "can_single_out(slot) = (slot.candidates[0].score >= threshold)"
    violation_behaviour: "與 FR1.7 的二元判定不一致"
    source: "FR1.7 逐字「判定為二元：信心值 < 0.7 即進入 FR1.3 的反問路徑」——本條是它在規則層的位置"
  - id: BR3.3
    statement: "`scoresAvailable` 為假時，述詞的求值為「該槽位第一名與第二名不並列」。"
    category: calculation
    applies_to: "can_single_out（作用於**一個槽位**的 ranking，修訂 1 釐清）"
    trigger: "對某一槽位求值且該槽位 scoresAvailable 為假"
    logic: "can_single_out(slot) = (slot 候選數 == 1) OR (rank 1 與 rank 2 之間存在分類器宣告的嚴格優先)"
    violation_behaviour: "無分數時若直接當作可單選，FR1.3 會靜默永不觸發——正是 FR1.6 逐字警告的那個後果"
    source: "FR1.6 的替代表達逐字「候選意圖並列且無單一最高分」；OQ-10"
  - id: BR3.4
    statement: "門檻是**設定值**不是常數，初版 0.7。"
    category: policy
    applies_to: "BR3.2 的 threshold"
    trigger: "求值"
    logic: "IF 需要門檻 THEN 由設定讀取；缺值不得以預設值靜默啟動"
    violation_behaviour: "寫死會讓 NFR1 的校正程序無處可施"
    source: "FR1.7 逐字「門檻為設定值而非常數，得依 NFR1 的校正程序調整」；K-10 的 threshold.form"
  - id: BR3.5
    statement: "整句判定為假時，`intents` 必為空且 `candidates` 必非空；為真時反之。"
    category: constraint
    applies_to: IntentDecision
    trigger: "填入 IntentDecision"
    logic: "IF NOT BR4.2 的整句聚合 THEN intents = [] AND candidates 非空（來源見 BR4.5）；ELSE intents 非空（基數見 BR4.4）AND candidates 為空"
    violation_behaviour: "同時給出工作項與候選清單，會讓畫面同時呈現交辦與反問"
    source: "entities.md 的 EC4／EC5；FR1.3 逐字「不得交辦、不得產生任何結果」。**修訂 1（審查 R-01）**：原文只說「非空」，而「非空後幾個」沒有規則——基數移交 BR4.4、候選來源移交 BR4.5
  - id: BR3.6
    statement: "述詞是**純函式**：輸入只有 ranking 與門檻，無 I/O、無模型呼叫、無時間相依。"
    category: constraint
    applies_to: can_single_out
    trigger: "任何時刻"
    logic: "IF 述詞需要任何外部狀態 THEN 設計錯誤"
    violation_behaviour: "不純就無法做 property-based 測試，而 ADR-0006 對 agent routing 是 hard constraint"
    source: "ADR-0006；contract-summary.md:797-799 的 pbt_note 逐字「受測對象是門檻比較這個純函式」"

  # ── 群組 4：多意圖拆解 ─────────────────────────────────────────────────
  - id: BR4.1
    statement: "一句含 N 個可分離意圖者，分類產出 **N 個槽位**（每個槽位一張自己的候選清單）。"
    category: calculation
    applies_to: "ClassificationResult.slots"
    trigger: "分類一句輸入"
    logic: "IF 可分離意圖數為 N THEN len(slots) == N；單意圖是 N==1 的特例，不是另一條路徑"
    violation_behaviour: "**修訂 1（審查 R-01）**：原文寫的是「輸出 N 個 Intent」，而當時只有一張扁平候選清單可裝——同槽位候選互斥、跨槽位候選並存，兩個軸壓在一起時「輸出幾個」無規則可循，最直覺的實作會靜默丟掉第二個意圖"
    source: "FR5.1，含其可測不變量（requirements.md:176 逐字：改圖＋估成本 ⇒ 2 個）；AC5.1.1；entities.md 的 EC6"
  - id: BR4.2
    statement: "整句可交辦 ⟺ **每一個**槽位都可單選（對槽位的 AND 聚合）。"
    category: policy
    applies_to: "BR3.1 與 BR4.1 的交界"
    trigger: "一句含多個槽位"
    logic: "整句聚合 = ALL(can_single_out(slot) for slot in slots)；任一為假則整句走反問，不產生任何 Intent——即使其中某個槽位本身很明確"
    violation_behaviour: "逐槽位反問會讓畫面同時出現工作項與反問，違反 BR3.5"
    source: "FR1.3 逐字「不得交辦、不得產生任何結果」——「任何」涵蓋多意圖情境。**修訂 1**：述詞本身仍只作用於一個槽位（BR3.2／BR3.3），整句層是這條 AND，兩層分開才讓述詞維持純函式與其 PBT property
  - id: BR4.3
    statement: "本單元只決定拆成幾個與各自的能力，**不決定交辦順序與依賴**。"
    category: constraint
    applies_to: "與 U12 的邊界"
    trigger: "輸出多個 Intent"
    logic: "IF 輸出 N 個 Intent THEN 不附帶順序或依賴標記"
    violation_behaviour: "順序與依賴屬 WorkOrchestrator 的狀態機，兩處各判一次必定分歧"
    source: "components.md 的 WorkOrchestrator responsibilities 逐字「多意圖的拆解結果落為 N 個工作項並決定交辦順序」"
  - id: BR4.4
    statement: "整句可交辦時，`len(intents)` **恰等於** `len(slots)`，第 i 個 Intent 取第 i 個槽位 `rank == 1` 的候選。"
    category: calculation
    applies_to: "IntentDecision.intents"
    trigger: "整句聚合為真"
    logic: "intents = [slot.candidates[0] 轉成 Intent for slot in slots]；capability 與 referent 逐欄複製"
    violation_behaviour: "**這是 R-01 的直接修補**。少了這條等式，`BR3.5` 只說 intents 非空，於是 FR5.1 的官方可測不變量（改圖＋估成本 ⇒ 2 個）在規則字面下可以用 1 個滿足——使用者只看到一個工作項，第二個請求被靜默丟棄，而 US5.1 在追溯表上仍標 OK"
    source: "本站修訂 1 新定（審查 R-01）；entities.md 的 EC7；FR5.1 的可測不變量"
  - id: BR4.5
    statement: "整句不可交辦時，`candidates` 是**所有不可單選槽位**的候選攤平後的清單，且每個 `label` 必須寫出它屬於哪一件事。"
    category: constraint
    applies_to: "IntentDecision.candidates"
    trigger: "整句聚合為假且槽位數大於 1"
    logic: "candidates = flatten(slot.candidates for slot in slots if NOT can_single_out(slot))；label 內含槽位的人話描述"
    violation_behaviour: "K-10 的 ClarifyCandidate 沒有槽位欄位，攤平後若 label 不帶來源，使用者會看到一串來源不明的候選而不知道系統在問哪件事"
    source: "本站修訂 1 新定（審查 R-01）；entities.md 的 EC8；K-10 的 ClarifyCandidate 欄位集合（本站無改它的授權，故在既有形狀內解決）"

  # ── 群組 5：指涉詞解析 ─────────────────────────────────────────────────
  - id: BR5.1
    statement: "指涉詞解析讀 SessionContext 的當前作業對象與該段歷程。"
    category: calculation
    applies_to: "CandidateIntent.referent"
    trigger: "輸入含指涉詞"
    logic: "IF 輸入含指涉詞 THEN 以該 session 該段的作業對象與訊息歷程解析"
    violation_behaviour: "讀錯段會讓獨立對話解析到共享對話的產出，違反 AC6.1.3"
    source: "FR6.1；K-10 的 classify(principal, session, text)；U10 的段隔離規則（讀取視圖只含本段）"
  - id: BR5.2
    statement: "指涉詞無法判定指哪一個時，走反問路徑，**不擅自挑一個**。"
    category: policy
    applies_to: "BR3.1"
    trigger: "指涉詞有多個可能對象"
    logic: "IF 指涉詞不可唯一解析 THEN can_single_out 為假"
    violation_behaviour: "挑一個就是 FR1.3 要防的「擅自做出我沒要的東西」"
    source: "AC6.1.2 逐字「系統走 US1.2 的反問路徑，不擅自挑一個」"
  - id: BR5.3
    statement: "輸入中直接點名的對象，優先於 session 當前的作業對象。"
    category: calculation
    applies_to: "CandidateIntent.referent"
    trigger: "輸入內含對象名稱"
    logic: "IF 輸入含可解析的對象名稱 THEN 以它為 referent。**寫回 session 作業對象的端點本站不指派**——見 functional-spec.md 的 OPEN-IR11-4"
    violation_behaviour: "忽略句中對象會讓 AC1.1.5（脈絡列為「尚未選定」時說出對象名）失敗"
    source: "AC1.1.5；user-flow Flow 1 第 3 步逐字「並從敘述中認出作業對象」"
  - id: BR5.4
    statement: "「沒有指涉詞」與「有指涉詞但解析不出來」必須可區分。"
    category: validation
    applies_to: "CandidateIntent.referent"
    trigger: "referent 為 null"
    logic: "IF referent 為 null THEN 必須能判定是哪一種"
    violation_behaviour: "兩者都用 null 表達會讓 AC6.1.2 的觸發條件不可構造"
    source: "entities.md 的 EC3"

  - id: BR5.5
    statement: "指涉詞解析**只能**用該段的作業對象與訊息歷程；**不得**用記憶記錄決定指涉對象。"
    category: constraint
    applies_to: "CandidateIntent.referent"
    trigger: "輸入含指涉詞"
    logic: "IF 解析指涉詞 THEN 只讀 SessionContext 的該段；記憶（K-08）得用於理解偏好與術語，不得用於決定 referent 指誰"
    logic_executable: "呼叫 MemoryFacade.search 時 kinds 參數**不得含「情節」記憶**，只傳語意／程序（contract-summary.md:617-618 的簽章 `search(principal, query, kinds: Sequence[str], limit)`；三種記憶見 components.md:179）。這是本條唯一的可檢查形式，可由一個斷言 kinds 實際傳值的測試擋住（修訂 1，審查 R-03）"
    reachability: "**目前不可達，刻意保留為前置護欄。** MemoryFacade.write 沒有任何呼叫者（contract-summary.md:1432 的 OQ-N3，Critical，仍開著），所以 memory_records 永不被填、search 永遠回空——本條現在擋不到任何真實資料。它的理由是 OQ-N3 關閉（補上寫入端）的那一刻這條路徑就會變成可達，而屆時沒有人會回頭想起這條負向 AC。**OQ-N3 定案時 AC6.1.3 必須重新檢視。**"
    residual_gap: "kinds 排除只關掉情節記憶這個入口。語意記憶是「事實」，原則上仍可能載有產出物名稱，而「用記憶理解術語」與「用記憶決定 referent」在**模型內部**不可區分——這一半無機械強制，比照 contract-summary.md:1434 的 OQ-N2 形狀如實記載（決定不加機制是可以的，不追蹤它不行）"
    violation_behaviour: "AC6.1.3 的保證建立在「獨立段不共享訊息歷程」上，而**記憶不分段**（它是長期、跨 session 的）。若解析可查記憶，獨立段就能解析到共享段的產出——這條負向 AC 會靜默失效，而 BR5.1 的字面擋不住它（它只說讀哪裡，沒說不准讀別處）"
    source: "本站新定。AC6.1.3 的**第二個違反入口**；第一個（讀錯段）由 U10 的兩條段隔離規則結構性擋下（讀取視圖只含本段、禁止任何合併路徑；**刻意不寫它們的編號**——U10 的 BR 編號與本單元同名不同義，且追溯 sensor 會把它們當成本單元的規則而誤報 orphan）"

  # ── 群組 6：成本紀律 ───────────────────────────────────────────────────
  - id: BR6.1
    statement: "分類器只接收決策所需的最少上下文。"
    category: policy
    applies_to: "模型呼叫"
    trigger: "準備分類請求"
    logic: "IF 組裝請求 THEN 只帶判定意圖所需者；不整段附上完整歷程"
    violation_behaviour: "每輪成本與歷程長度線性相關，而歷程上限是 200 則"
    source: "K-10 的 cost_discipline 第一條"
  - id: BR6.2
    statement: "同一狀態下互不相依的判斷合併為一次請求。"
    category: policy
    applies_to: "模型呼叫"
    trigger: "一輪內需要多個判斷"
    logic: "IF 多個判斷互不相依 THEN 合併"
    violation_behaviour: "拆開呼叫是成本與延遲的雙重浪費"
    source: "K-10 的 cost_discipline 第二條"
  - id: BR6.3
    statement: "每輪的模型呼叫次數、重試次數與用量上限必須**存在且可設定**。"
    category: constraint
    applies_to: "模型呼叫"
    trigger: "服務啟動"
    logic: "IF 機制不存在 THEN 違反；**具體數值不在本站定案**"
    violation_behaviour: "沒有上限的重試會把一次模型異常放大成一次帳單事件"
    source: "K-10 的 cost_discipline 第四條逐字「機制必須存在且可設定；具體數值不在本站定案，見回補項 N-18」"

  # ── 群組 7：授權與邊界 ─────────────────────────────────────────────────
  - id: BR7.1
    statement: "本單元不自行判權。"
    category: authorization
    applies_to: "整個單元"
    trigger: "任何呼叫"
    logic: "IF 需要授權判定 THEN 不在本單元做；讀記憶經 K-08 的 MemoryFacade，由它承擔"
    violation_behaviour: "自建第二套判定會與既有授權層分歧"
    source: "K-10 的 behaviour_semantics.authorization_responsibility 逐字"
  - id: BR7.2
    statement: "本單元不暴露任何對外端點，也不自行從請求取身分。"
    category: constraint
    applies_to: "整個單元"
    trigger: "任何時刻"
    logic: "IF 需要 principal THEN 由參數傳入（K-10 的 classify 第一個參數）"
    violation_behaviour: "自取身分會讓同進程呼叫者得以用別人的身分分類與讀記憶"
    source: "K-10 的 in-process 宣告與 classify 簽章"
  - id: BR7.3
    statement: "本單元不建立工作項、不決定狀態、不呼叫既有能力。"
    category: constraint
    applies_to: "與 U12 的邊界"
    trigger: "述詞為真"
    logic: "IF 判定完成 THEN 只回 IntentDecision；建立工作項與呼叫能力屬 WorkOrchestrator"
    violation_behaviour: "兩個單元都能建工作項，會讓 FR1.2 的狀態機有兩個寫入端"
    source: "components.md 的 WorkOrchestrator responsibilities；K-10 的 consumers 只有 U13"
  - id: BR7.4
    statement: "本單元**不得呼叫 `SessionStore` 的任何寫入方法**（`set_work_target`／`append_message`／`set_sharing_mode`／`touch`）——對 `SessionContext` 唯讀。"
    category: constraint
    applies_to: "與 U10 的邊界"
    trigger: "任何時刻"
    logic: "IF 需要寫 SessionContext THEN 不在本單元做"
    violation_behaviour: "**修訂 1（審查 R-05）**：AC1.2.3「脈絡列與作業對象不變」的保證原本被歸因於 BR7.3，但 BR7.3 的字面只講工作項、狀態與能力呼叫，**完全沒提 SessionContext**；而 K-09 的 consumers 是 [U11, U12, U13]（contract-summary.md:688，**未按方法分拆**）、本單元對 U10 已有 DAG 邊。於是沒有任何規則擋得住一個好意的實作者為了補 OPEN-IR11-4 的缺口，直接在 classify() 裡呼叫 set_work_target——那會製造第二個作業對象寫入端，並讓 AC1.2.3 的「不變」失去唯一的機制基礎"
    source: "components.md:323 逐字把 IntentRouter → SessionContext 標為「**讀**當前作業對象與對話歷程以解析指涉詞」（唯讀邊）；本站修訂 1 把該邊宣告升為可檢查的禁令"

  # ── 群組 8：冪等與失效 ─────────────────────────────────────────────────
  - id: BR8.1
    statement: "`classify` **非冪等**——同一句輸入可能得到不同的候選清單。"
    category: constraint
    applies_to: "K-10 的 classify"
    trigger: "重試"
    logic: "IF 重試 classify THEN 結果可能不同；重試次數受 BR6.3 的上限約束"
    violation_behaviour: "把它當成冪等會讓重試被誤用為「再試一次就會一樣」"
    source: "K-10 的 behaviour_semantics.retry_and_idempotency 逐字「classify 非冪等（LLM 輸出可變）」"
  - id: BR8.2
    statement: "模型不可用或超出用量上限時，大聲失敗，不降級為「隨便挑一個意圖」。"
    category: policy
    applies_to: "模型呼叫"
    trigger: "LlmUnavailable／LlmBudgetExceeded"
    logic: "IF 模型失效 THEN raise 對應例外向上傳遞；不回一個猜測的 Intent"
    violation_behaviour: "降級猜測是 FR1.3 要防的那件事的最壞版本——它連候選都不給使用者看"
    source: "K-10 的 raises: [LlmUnavailable, LlmBudgetExceeded]；construction.md 逐字「Errors must be surfaced」"
  - id: BR8.3
    statement: "述詞本身永不失敗——它對任何合法的 ranking 都有定義。"
    category: constraint
    applies_to: can_single_out
    trigger: "求值"
    logic: "IF ranking 合法（EC1／EC2 成立）THEN 述詞回傳布林值，不 raise"
    violation_behaviour: "述詞會 raise 就不是純函式，PBT 的 property 也無法表述"
    source: "BR3.6；ADR-0006 的 PBT hard constraint"
```

## 規則摘要（**由腳本自上方 YAML 區塊實算產生**）

> 以 `^  - id: (BR\d+\.\d+)$` 與 `^    category: (\w+)$` 兩條 regex 自同一份檔案解析；
> 群組計數為分組大小，總數為解析結果長度。**本表無手寫數字。**

| 群組 | 主題 | 條數 | 類別 |
|---|---|---|---|
| `BR1.x` | 輸入前置與固定拒絕 | **3** | constraint／policy |
| `BR2.x` | 分類與候選排序 | **5** | calculation／constraint／validation |
| `BR3.x` | 反問述詞 | **6** | calculation／constraint／policy |
| `BR4.x` | 多意圖拆解 | **5** | calculation／constraint／policy |
| `BR5.x` | 指涉詞解析 | **5** | calculation／constraint／policy／validation |
| `BR6.x` | 成本紀律 | **3** | constraint／policy |
| `BR7.x` | 授權與邊界 | **4** | authorization／constraint |
| `BR8.x` | 冪等與失效 | **3** | constraint／policy |
| | **合計** | **34** | |

### 類別分佈

| 類別 | 條數 |
|---|---|
| constraint | **15** |
| policy | **8** |
| calculation | **8** |
| validation | **2** |
| authorization | **1** |

### 全部規則識別碼

`BR1.1`、`BR1.2`、`BR1.3`、`BR2.1`、`BR2.2`、`BR2.3`、`BR2.4`、`BR2.5`、`BR3.1`、`BR3.2`、`BR3.3`、`BR3.4`、`BR3.5`、`BR3.6`、`BR4.1`、`BR4.2`、`BR4.3`、`BR4.4`、`BR4.5`、`BR5.1`、`BR5.2`、`BR5.3`、`BR5.4`、`BR5.5`、`BR6.1`、`BR6.2`、`BR6.3`、`BR7.1`、`BR7.2`、`BR7.3`、`BR7.4`、`BR8.1`、`BR8.2`、`BR8.3`

## 修訂 1 新增的五條（審查 `review-01.md`）

| 規則 | 處置的發現 | 它擋住什麼 |
|---|---|---|
| `BR4.4` | `R-01`（Critical） | `intents` 的基數等式——少了它，`FR5.1` 的官方可測不變量可以用 1 個 Intent「滿足」，第二個意圖被靜默丟棄 |
| `BR4.5` | `R-01` | 多槽位同時不可單選時，候選攤平後 `label` 必須帶來源（`K-10` 的 `ClarifyCandidate` 沒有槽位欄位，而本站無權加） |
| `BR7.4` | `R-05`（Major） | 本單元對 `SessionContext` 唯讀。原先 `AC1.2.3` 的「不變」被歸因於 `BR7.3`，而那條字面完全沒提 `SessionContext` |
| `BR3.2`／`BR3.3` 的 `applies_to` 釐清 | `R-01` | 述詞作用於**一個槽位**，整句層是 `BR4.2` 的 AND——兩層分開才讓述詞維持純函式 |
| `BR5.5` 的三個新欄位 | `R-03`（Major） | `logic_executable`（`kinds` 排除情節記憶）給它唯一的可檢查形式；`reachability` 誠實記下它**目前不可達**（`OQ-N3`：記憶無寫入端）；`residual_gap` 比照 `OQ-N2` 記下模型內部不可區分的那一半 |

**`BR5.5` 的 `reachability` 欄是本輪自己補的，不在審查要求裡。** `project.md` 逐字
要求「新增任何『偵測 X 狀態』的規則之前，先推導 X 是否可達——不可達的規則是死碼，
卻在文件上長得像已解決」。`BR5.5` 守的正是一條目前不可達的路徑（記憶沒有寫入端），
所以它**現在是死碼**。保留它的理由是 `OQ-N3` 關閉的那一刻路徑就變成可達，
而屆時沒有人會回頭想起這條負向 AC——但這件事必須寫明，不能讓它看起來像現行防護。

## 讀法：`[IR1]`=A 影響了哪幾條

| 性質 | 規則 | 說明 |
|---|---|---|
| **`[IR1]`=A 的直接產物** | `BR2.2`／`BR2.3`／`BR2.5`／`BR3.1`–`BR3.3`／`BR3.6` | 候選清單取代單一答案；分數選用、排序必須；述詞取代直接比較；述詞必須是純函式 |
| **本站新定（上游未涵蓋的缺口）** | `BR2.4`／`BR3.5`／`BR4.2`／**`BR4.4`**／**`BR4.5`**／`BR5.4`／**`BR5.5`**／**`BR7.4`**／`BR8.3` | 空清單是失敗不是反問；`EC4`／`EC5` 的雙向不變量；整句聚合為對槽位的 AND；**`intents` 的基數等式**與**候選攤平的來源規則**（修訂 1，審查 `R-01`）；兩種 `null` 必須可區分；**記憶不得用於解析指涉對象**（`AC6.1.3` 的第二個違反入口）；**對 `SessionContext` 唯讀**（修訂 1，審查 `R-05`）；述詞永不失敗 |
| **轉錄上游** | `BR1.1`–`BR1.3`／`BR2.1`／`BR3.4`／`BR4.1`／`BR4.3`／`BR5.1`–`BR5.3`／`BR6.1`–`BR6.3`／`BR7.1`–`BR7.3`／`BR8.1`／`BR8.2` | 每條的 `source` 欄指向逐字出處 |

**`BR3.3` 是整組裡最容易被略過、而後果最嚴重的一條。** 它處理的是
`scoresAvailable` 為假的分支——而那個分支在 `OQ-10` 定案之前**沒有人知道會不會
用到**。少了它，無分數時述詞會退化成「永遠可單選」，`FR1.3` 於是**靜默永不觸發**。
`FR1.6` 逐字警告的正是這個後果：「若實作出一個不輸出信心值的路由層，`FR1.3` 會
靜默永不觸發，而文件上看起來已解決。」

**`BR4.2` 是第二容易漏的**：`FR1.3` 說「不得交辦、不得產生任何結果」，
而多意圖情境下很自然會想「那就把確定的那幾個先交辦」。那會讓畫面同時出現
工作項與反問，而沒有任何一條上游規則的字面擋得住它——`BR4.2` 是為此而寫。
