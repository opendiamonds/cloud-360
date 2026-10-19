## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

前次 review-01／review-02 的六項發現（NFR4.60 碰撞、NFR7.62 可達性、SEC-3/4/5 親代、斷路器論證、預算歸因、OPENROUTER_API_KEY 前置條件）在凍結產出中皆已處置，ADR-0006 四面向逐格有落點。剩下的缺口集中在「成本紀律三個旋鈕」彼此不自洽：重試是否算一次呼叫、用量上限的數值與觸發條件無人定義，以及 800 ms 預算沒有說明 classify 內的記憶讀取成本由誰吃。這三項已由 code-generation 在落地時自行遇到（code-summary 第五節 #4、#11），代表它們是 nfr-requirements 該定而未定的事項，而非實作偏差。另有數項 Minor 的自洽與量測性問題。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/intent-router/nfr-requirements/performance-requirements.md > NFR3.62、NFR3.63、NFR3.64；tech-stack-decisions.md > TS-4 | NFR3.62 說每輪最多 1 次模型呼叫，NFR3.63 說重試 0 次，NFR3.64 又說兩者皆可由環境變數設定（TS-4 的 BRAIN_ROUTER_MAX_CALLS_PER_TURN 與 BRAIN_ROUTER_MAX_RETRIES）。全檔沒有一處定義「重試算不算一次呼叫」。code-generation 已實際踩到：code-summary.md 第五節 #11 記載 MAX_RETRIES=3 時一輪實際發出最多 4 次 HTTP 請求，而 CallBudget 仍只看到 1 次，NFR3.62 的替身測試仍為綠。此外 MAX_CALLS_PER_TURN 可設為大於 1 本身就與 NFR3.62 的「最多 1 次」字面矛盾（可設定的上限等於不是上限）。code-generation 已明白把此事指回 nfr-requirements，故為本站未定案的事項。 | 在本站（或以 corrections 檔）定案：(a) 重試是否計入每輪呼叫上限；(b) MAX_CALLS_PER_TURN 與 MAX_RETRIES 的合法值域（例如啟動期拒絕 MAX_RETRIES 大於 0，或把合併上限寫成單一不變量「HTTP 請求數 ≤ N」）；(c) NFR3.62 的驗證方式改為斷言實際 HTTP 層請求數而非圖呼叫數。 | New |
| R-02 | Major | construction/intent-router/nfr-requirements/performance-requirements.md > 上游表第二列（K-10 cost_discipline 第四條，N-18）；reliability-requirements.md > NFR3.68；scalability-requirements.md > NFR9.62 | 本站自稱是 N-18 的落點，N-18 要求「每輪呼叫次數、重試次數與用量上限」三項數值。本站只定了前兩項；「用量上限」沒有數值、沒有單位（token？金額？每分鐘請求數？）、沒有觸發方。NFR3.68 要求「超出用量上限」時 raise LlmBudgetExceeded，但 NFR9.62 又寫「不設本單元層級的速率限制」且帳戶花費上限由 OpenRouter 後台承載，因此 LlmBudgetExceeded 在本單元內的唯一觸發來源是供應商回報（或本地呼叫次數超限）。code-summary.md 第五節 #4 顯示實作自行把本地次數超限也塞進 LlmBudgetExceeded，且與 reliability-design 的定義不一致。NFR3.68 的驗證方式（模擬連線失敗、5xx、429、逾時）也沒有任何一種情境對應「用量上限」。 | 明確寫出 N-18 第三項的處置：要嘛定義用量上限的度量與數值並指定觸發方，要嘛正式記為「本 intent 不設本地用量上限，LlmBudgetExceeded 僅對應供應商的某個具體回應碼」並回頭向 contract-summary 的 N-18 回報此縮減；同時修正 NFR3.68 的驗證情境使其涵蓋 LlmBudgetExceeded 的實際觸發。 | New |
| R-03 | Major | construction/intent-router/nfr-requirements/performance-requirements.md > NFR3.60、NFR3.65、預算切分算式 | NFR3.60 的量測區間是「進入 classify 到回傳 IntentDecision」共 800 ms，NFR3.65 卻宣稱除模型呼叫外只有純函式述詞耗時、不列入預算。但依 security-requirements.md 與 BR5.5，classify 內還會讀 SessionContext（Redis）並呼叫 MemoryFacade.search（K-08，簽章見 contract-summary.md:617-618）做指涉詞解析，該呼叫涉及 PostgreSQL 查詢，若 search 內部需要嵌入向量則另有一次外部嵌入呼叫。這些成本落在 800 ms 窗口內，卻沒有被 NFR3.65 承認、沒有預算、也不在 NFR3.62「每輪最多 1 次模型呼叫」是否包含嵌入呼叫的討論裡。前次 review-02 的 R-05 已指出此預算切分缺乏歸因力，本次的缺口是同形：classify 窗口內部的非 LLM 耗時被當成零。（本單元不得開啟 U8 的檔案，故嵌入呼叫是否存在請 U8 的 K-08 契約確認；本項成立與否不取決於它，因為 Redis 與 DB 讀取本身就非零。） | 在 NFR3.65 補列 classify 窗口內的非 LLM 步驟（session 讀取、MemoryFacade.search、prompt_guard），為其定預算或明確指定量測點使 build-and-test 能把 800 ms 拆成「讀取」與「模型呼叫」兩段歸因；並寫明 NFR3.62 的「模型呼叫」是否包含嵌入呼叫。 | New |
| R-04 | Minor | construction/intent-router/nfr-requirements/performance-requirements.md > NFR3.64 | NFR3.64 說「上述四個數值全部可由環境變數設定」，四個數值指 800 ms P50、5 秒逾時、1 次呼叫、0 次重試。但 TS-4 的環境變數表只有逾時、呼叫上限、重試、模型、門檻五項，沒有 P50 目標值的變數；P50 是驗收目標而非執行期參數，不應被列為可設定。字面上 NFR3.64 無法被其驗證方式（設定值改動後行為隨之改變）對 P50 滿足。 | 把 NFR3.64 改為三個執行期參數（逾時、呼叫上限、重試），P50 目標明確排除。 | New |
| R-05 | Minor | construction/intent-router/nfr-requirements/scalability-requirements.md > NFR3.67 之後的「對齊修正」區塊與 NFR9.61、NFR9.62 | 對齊修正的引用區塊插在需求表中間，把表格切斷，NFR9.61 與 NFR9.62 兩列落在區塊之後而不屬於任何表格，渲染成純文字，機器解析需求表時也會漏掉這兩條。 | 把對齊修正區塊移到表格之後，使 NFR9.61、NFR9.62 回到同一張表。 | New |
| R-06 | Minor | construction/intent-router/nfr-requirements/security-requirements.md > NFR9.60；scalability-requirements.md > NFR9.61 | NFR9.60 要求「只帶判定意圖所需的最少上下文」，但「最少」沒有數值上界（例如歷程取最近幾則、記憶取前幾筆）。NFR9.61 的驗證方式「斷言 prompt 字元數不隨歷程長度線性成長」只能擋住整段附上，擋不住「附上一半」，也沒有給 Jev 的 32000 context 設安全餘量。兩條的可測性只是二元的「有沒有整段附上」。 | 為歷程視窗與記憶筆數各定一個可設定的上界，並把 NFR9.61 的驗證改成對該上界的斷言。 | New |
| R-07 | Minor | construction/intent-router/nfr-requirements/performance-requirements.md > NFR3.63（引用 langgraph_runtime.py:94） | NFR3.63 引用 `langgraph_runtime.py:94` 為現行 max_retries=0 的出處。code-summary.md 記載 code-generation 已改動該檔的 openrouter_chat_model（temperature 型別與 kwargs 組裝），行號很可能已漂移；security 與 tech-stack 另引用 `langgraph_runtime.py:95`、`:16`。我未開啟該檔核對（審查範圍限制），請在落地後重驗行號。 | 以符號名（openrouter_chat_model 的 max_retries 參數）取代行號引用，或重驗並更新所有 langgraph_runtime.py 行號。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 逐列 pipe 計數 | 每個 Findings 資料列恰 7 個未跳脫的 pipe | 格式符合引擎要求 |
| 前次發現複驗（review-01、review-02 的 R-01 至 R-06） | 凍結產出中皆已有對應修訂段落 | 前次發現已處置，本次不再重列 |
