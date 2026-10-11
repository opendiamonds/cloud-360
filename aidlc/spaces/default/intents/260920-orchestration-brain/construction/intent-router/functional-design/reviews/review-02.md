## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-09T22:49:37Z
**Iteration:** 1

**覆蓋聲明**：四個受審檔（`functional-spec.md`、`entities.md`、`rules.md`、
`traceability.json`）逐行讀完；必讀上游六份（`unit-of-work.md` U11 段、
`unit-of-work-story-map.md` 相關行、`contract-summary.md` 的 K-02／K-07／K-08／
K-09／K-10／K-11 片段、`requirements.md` 的 FR1.x／FR5.x／FR6.1／OQ-4／OQ-10、
`stories.md` 的四則故事與其 AC、`components.md` 的 IntentRouter 邊）皆開檔逐字
核對，非轉引。對照組 `session-store/functional-design/traceability.json` 已讀。
`rules.md` 的條數／類別統計已用 `grep -cE` 重算，與腳本輸出完全一致（31 條、
`BR1.x`–`BR8.x` 分組 3/5/6/3/5/3/3/3、類別 constraint 13／policy 8／
calculation 7／validation 2／authorization 1）。`traceability` sensor 已重跑，
結果與受審產出宣稱一致（`pass:false`，`gaps:["AC1.1.5"]`，僅此一項）。此為**完整
覆蓋**，非掠讀。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | `construction/intent-router/functional-design/rules.md` > `BR4.1`–`BR4.3`、`BR3.1`–`BR3.5`；`entities.md` > `CandidateRanking`／`CandidateIntent` | **多意圖與反問共用同一個 `CandidateRanking`／`can_single_out`，但沒有任何規則說明「N 個可分離意圖」要如何表達成這個單一扁平清單，也沒有規則說明 `can_single_out` 為真時 `IntentDecision.intents` 要填入清單中的幾個候選。** `entities.md` 把 `CandidateRanking` 定義為「一次分類的完整候選清單」，`CandidateIntent` 是「值物件——同能力、同指涉、同分數者不可區分」的**互斥候選**（即對同一個決策槽位的各種讀法），這與 `BR4.1` 要求的「N 個**可分離**（即並存，不互斥）意圖」在概念上矛盾。`BR3.2` 把 `can_single_out` 定義為「`candidates[0].score >= threshold`」——只看**排名第一**的候選；`BR3.5` 只說「為真 → `intents` 非空」，未定義非空後 `intents` 的長度與內容是取 `candidates[0]` 還是全部候選。**可構造的失敗情境**：取 `requirements.md:176` 給的 `FR5.1` 官方可測不變量本身——輸入「改架構圖加 Redis 快取，然後估一下成本差額」，分類器產出 2 個候選（架構設計、成本估價），皆有信心分數且皆高於門檻（`scoresAvailable=true`）。依 `BR3.2`，`can_single_out` 求值僅看 `candidates[0].score >= threshold`，結果為真；依現有規則字面，`intents` 填入「非空」即合規，實作者依最直覺的讀法（`intents=[candidates[0]]`，因為 `CandidateIntent` 被定義為互斥候選）只會輸出 1 個 Intent（架構設計），**成本估價請求被無聲丟棄**——使用者只看到一個工作項，`AC5.1.1`（「畫面出現兩個工作項」）失敗，而 `US5.1`／`BR4.1` 在追溯表上仍標 `OK`。這正是 `rules.md` 自己在 `BR4.2` 段落後警告的「某個意圖本身很明確」情境，但警告只處理了「要不要反問」，沒有處理「可單選時輸出幾個」。 | 在 `entities.md` 明確定義多意圖情境下 `CandidateRanking` 的結構（例如：是否拆成 N 個各自獨立求值的 ranking，每個最多 1 個候選即視為該意圖確定；或在 `CandidateIntent` 上加一個「意圖槓位」分組鍵，`can_single_out` 改為對每個槽位分別求值後再做 `BR4.2` 的整句聚合），並在 `BR3.5`／`BR4.1` 明文寫出 `can_single_out` 為真時 `intents` 的基數規則（全部候選，還是每槽位的勝出者）。沒有這條，`BR4.2`「述詞先對整句求值」無法被實作者正確落地。 | New |
| R-02 | Major | `construction/intent-router/functional-design/entities.md` > `IntentDecision.confidence`（`number\|null`） | **本站在未獲授權、且本站自己承認「目前沒有」授權的情況下，把 `K-10` 的 `IntentDecision.confidence` 欄位型別從契約宣告的 `float`（定義域 0–1，無 null）改為 `number\|null`。** `contract-summary.md:759` 的 `data_shape.IntentDecision.confidence` 逐字是「`float`，定義域 0–1」，沒有 nullable。`contract-summary.md:1424` 把 `confidence`／`below_threshold` 兩個欄位語意的**改寫權**明文指派給 `nfr-requirements`（`OQ-10` 的 landing station），不是 `functional-design`。`functional-spec.md` §六 `OPEN-IR11-2` 自己寫：「**該改寫需要像 `OQ-N4` 那樣的明文授權，而目前沒有**」——`OQ-N4` 是本 intent 內已有的真實先例（`contract-summary.md:1433` 明文授權 `U10` 的 `functional-design` 可改 `K-09` 的 `public_interface` 與 `data_shape`），本單元沒有對應的授權文字，卻仍在 `entities.md` 的「Source of truth」YAML（本檔宣告的本單元唯一真實來源）把型別定為 `number\|null`、`required: true`，不是標成待定或草案。**可構造的失敗情境**：`code-generation` 的實作者只讀 `entities.md`（它是本單元實體形狀的唯一真實來源，不會回頭讀 `contract-summary.md:1424`），依此把 `IntentDecision.confidence` 的 Pydantic 型別宣告為 `float \| None`；若 `nfr-requirements` 之後定案 `OQ-10` 為「可產出信心值」（`OQ-4` 選了帶分數的模型），`K-10` 的契約仍是 `float` 不可為 null，型別已經在程式碼與既有 OpenAPI/WS 契約（`K-02` 的 `clarify.candidates[].confidence` 已宣告為 `number\|null`，但那是 `ClarifyCandidate` 不是 `IntentDecision`）之間產生不一致，且因 `entities.md` 已寫死，回頭訂正的成本已經發生在程式碼而非文件。 | 把 `entities.md` 的 `confidence` 型別改標為待定（例如 `float`（暫定，依 `nfr-requirements` 的 `OQ-10` 決定是否為 `float\|null`）），不要在「Source of truth」YAML 裡寫成已定的 `number\|null`；或者明確走 `OQ-N4` 的先例，把這個型別變更正式記成一條新的 `OQ`／`J`，指派 `nfr-requirements` 連同 `OQ-10` 一併授權，並在 `functional-design` 階段不先行寫入具體型別。 | New |
| R-03 | Major | `construction/intent-router/functional-design/rules.md` > `BR5.5`；`entities.md` 未提及的 `MemoryFacade.search(kinds=...)` 參數 | **`BR5.5` 禁止「用記憶決定 `referent` 指誰」、允許「用記憶理解偏好與術語」，但沒有任何機制使這條界線可被實作或可被測試區分。** `contract-summary.md:613` 的 `MemoryFacade.search` 簽章是 `(principal, query, kinds: Sequence[str], limit)`——`kinds` 是本單元唯一能用來**結構性**限制讀取範圍的參數（記憶分「語意／程序／情節」三種，`components.md:179`），但 `rules.md`／`entities.md`／`functional-spec.md` 全文（已 grep 核對：`情節`／`episodic`／`kinds`／`語意記憶`／`程序記憶` 零命中）**沒有指定 `classify()` 呼叫 `search` 時該帶哪些 `kinds`**，也沒有規定「情節記憶」（最可能記錄『上次問了哪個系統』這類可用於推斷 referent 的內容）必須被排除。一旦記憶內容（不限 kind）被組進 `BR6.1` 的「最少上下文」請求送給模型，**模型本身無法被程式阻止用這段內容去猜 `referent`**——`BR5.5` 的禁令只能靠 code review 事後檢查模型輸出是否「看起來」用了記憶，這與 `K-07` 的 `residual_gap`（「facade 是唯一入口無機械強制」）是同一類缺口，但 `K-07` 誠實標註了 `residual_gap`，本站的 `BR5.5` 沒有。**可構造的失敗情境**：某使用者在獨立對話段問「訂單系統的圖加一個快取」，另一獨立段問「那張圖的資料庫換成 Aurora」——若 `classify()` 為了「理解術語」查了情節記憶且該記憶列恰好記載了上一段的系統名稱，LLM 很可能把兩段內容都納入判斷「那張圖」指的是哪張，而沒有人能證明它是透過「理解術語」還是「決定 referent」做到的——`AC6.1.3`（負向驗收：獨立段應解析不到）會**不可測地、隨機地**失敗，且 `traceability.json` 已把它標為 `OK`。 | 在 `BR5.5` 補一條可執行約束：`classify()` 呼叫 `MemoryFacade.search` 時 `kinds` 參數**不得含「情節」記憶**（只傳語意／程序），或等價地，把這個限制寫成 `entities.md`／`rules.md` 可被 code review 或 lint 檢查的具體判準；若兩種記憶的內容在資料層無法區分到這個粒度，明確承認這是 `residual_gap` 並記錄風險，不要讓 `AC6.1.3` 維持 `OK`。 | New |
| R-04 | Major | `construction/intent-router/functional-design/traceability.json` > `coverage[US6.1]`（`status: OK`），對照 `construction/session-store/functional-design/traceability.json` > `coverage[US6.1]`（`status: Deferred`） | **同一則故事 `US6.1` 在兩個單元的追溯表上狀態不一致，且不一致的方向正好違反 `session-store` 單元自己定下的規則。** `session-store` 的 `traceability.json:118` 逐字寫：「本單元提供機制……但不擁有寫入端，故**整則故事記為 Deferred 而非 OK**——**寫 OK 會讓一個真實缺口在追溯表上看起來已覆蓋**」。這與 `project.md` 記載的既有教訓（`requirements-analysis:c4`「缺一不可型 hard constraint 以逐項判定表呈現」、`units-generation:260822-ug-L2`「發現已核可上游的契約缺口時……標出缺口」）同一精神：故事層級的狀態應反映其**最弱**的那條 AC，而不是取多數。本單元 `traceability.json:48` 的理由（「缺的那一條已有 owner 且不在本單元……與 `U10` 把它記 `Deferred` 的理由不衝突：`U10` 擁有那個缺的寫入端所在的實體，本單元不擁有」）解釋的是**為什麼 `AC6.1.1` 這條 AC 在兩邊都標 `Deferred`（兩邊確實一致）**，但沒有解釋為什麼**故事層級**的彙總要不一樣——本單元自己的 `coverage` 表裡 `AC6.1.1` 本身就是 `Deferred`（非 `OK`），把母故事 `US6.1` 彙總成 `OK` 等於用了與對照組不同的彙總規則，而沒有寫明這條彙總規則本身。**可構造的失敗情境**：任何只讀 `U11` 這份追溯表、不比對 `U10` 那份的人（例如下一站 `nfr-requirements` 或某個自動化追溯彙總工具）會把 `US6.1` 當成**本單元視角下已完全覆蓋**，而實際上它依賴的 `AC6.1.1` 寫入端仍是開放缺口；兩份文件對同一故事給出矛盾訊號，而本站的「檢查 4：檔案集合一致性」自檢只比對了 produces 清單是否齊備，沒有比對共享故事的狀態是否一致。 | 把 `US6.1` 的故事層級狀態改為 `Deferred`（與 `U10` 一致），`target`／`note` 可保留現有文字說明「本單元視角下，本單元擁有的那一半（`AC6.1.2`／`AC6.1.3`）已覆蓋，缺口在 `AC6.1.1`，owner 為 `U12`」；或者如果要維持 `OK`，必須先在產出中明文定義「故事層級狀態 = 本單元視角下的覆蓋」這條彙總規則，並同時指出它與 `U10` 的彙總規則不同、說明為何這個差異是刻意的而非遺漏。 | New |
| R-05 | Major | `construction/intent-router/functional-design/functional-spec.md` > W5 第 3 步、`traceability.json` > `AC1.2.3.note`；對照 `rules.md` > `BR7.3` | **`AC1.2.3`（Must 故事 `US1.2` 的一條 AC）「脈絡列與作業對象不變」這個保證，被歸因於 `BR7.3`，但 `BR7.3` 的規則文字根本沒有提到 `SessionContext` 或作業對象。** `rules.md:256-263` 的 `BR7.3` 逐字是「本單元不建立工作項、不決定狀態、不呼叫既有能力」，`logic` 欄只講 `IntentDecision`／工作項／能力呼叫，`source` 欄引用 `components.md` 的 `WorkOrchestrator` 責任與 `K-10` 的 `consumers`——三處都與「是否寫 `SessionContext`」無關。`functional-spec.md:81` 寫「本單元從不寫 `SessionContext`」並標注依據為 `BR7.3`；`traceability.json:96` 對 `AC1.2.3` 的 `note` 同樣寫「因為本單元從不寫 `SessionContext`（`BR7.3` ＋ `OPEN-IR11-4` 的查證結果：本單元沒有任何寫入路徑）」。但 `OPEN-IR11-4` 的查證結果是一個**觀察**（目前沒有人指派這條寫入路徑給本單元），不是一條**禁令**——`contract-summary.md:697` 的 `K-09` 契約把 `U11` 列為 `SessionStore` 的**一般消費端**（`consumers: [U11 intent-router, U12 work-orchestrator, U13 brain-gateway]`，未按方法分拆），且本單元已經依 DAG 對 `U10` 有邊（`unit-of-work.md:160`）。`rules.md` 的 `BR7.x`（授權與邊界）群組裡沒有任何一條寫「本單元不得呼叫 `SessionStore` 的任何寫入方法」。**可構造的失敗情境**：`code-generation` 的實作者為了解 `OPEN-IR11-4`（脈絡列沒有寫入端）這個已知缺口，依本單元已有的 `U10` 依賴邊，直接讓 `classify()` 在解析出明確 `referent` 後呼叫 `SessionStore.set_work_target(...)`——`rules.md` 裡沒有任何一條規則禁止這個做法（`BR7.1`／`BR7.2`／`BR7.3` 都管別的事），而這會製造第二個作業對象寫入端，與 `components.md:323` 把 `IntentRouter → SessionContext` 明文標為「讀」（唯讀）的既定邊相違，且會讓 `AC1.2.3`「不變」的保證失去其唯一的機制基礎。 | 在 `rules.md` 的 `BR7.x` 群組新增一條明文規則（例如 `BR7.4`）：「本單元不得呼叫 `SessionStore` 的任何寫入方法（`set_work_target`／`append_message`／`set_sharing_mode`／`touch`）」，來源引用 `components.md:323` 的唯讀邊宣告；並把 `functional-spec.md` W5 第 3 步與 `traceability.json` 的 `AC1.2.3.note` 改引用這條新規則而非 `BR7.3`。 | New |
| R-06 | Minor | `construction/intent-router/functional-design/functional-spec.md` > §五 PBT property 表 `P4` | `P4`（「`scoresAvailable` 為真時，提高最高分不會使述詞由真變假」）正確地把前提限定在 `scoresAvailable=true` 的分支，邏輯本身不是空集合問題（已核對 `project.md` 自檢條目要求的那個疑慮不成立）。但 `rules.md`／`functional-spec.md` 都沒有提到 Hypothesis 的生成策略要如何保證**兩個分支都被實際抽到**（若策略預設傾向生成帶分數的候選，`BR3.3`／`P3` 對 `scoresAvailable=false` 的覆蓋可能在實作時長期掛零而沒有人注意，因為 Hypothesis 不會因為某個分支從未被抽到而報錯）。 | 在交接給 `code-generation` 的 PBT 落點說明里，補一句要求生成策略顯式覆蓋 `scoresAvailable` 的兩個布林值（例如用 `st.booleans()` 驅動而非讓分數是否存在隨機浮現），避免 `BR3.3` 長期零覆蓋而不自知。 | New |

### 對送審前自檢與「我已查出並處置的事項」的覆核結論（非缺陷列表，供人工參考）

- **自檢 2 ／ `OPEN-IR11-4`（事項 1）**：**維持**。已開 `contract-summary.md` 的
  `K-07`（`:465-540`）、`K-09`（`:684-744`）核對：`HierarchyFacade` 沒有任何
  「名稱→識別碼」查詢方法（`list_projects`／`create_*`／`resolve_work_target`／
  `record_diagram_change`／`delete_*` 七個方法全部要求已解析的 id，不接受名稱），
  `SessionStore.set_work_target` 同樣只收 id。`AC1.1.5` 記 `GAP` 的判定正確，
  未發現可推翻它的契約或 WS 訊息。
- **事項 2（`BR5.5` 第二入口）**：**(a) 成立**（`K-08.search` 不分段、本單元讀記憶
  為唯讀但內容會混進 LLM context）；**(b) 不成立——見本表 `R-03`**（界線在目前
  規格下不可判定，已列為 Major）。
- **事項 3（`AC1.2.4` 記 `Deferred`）**：**維持**。`VALID_STATUSES` 明確把
  `Deferred` 列為合法狀態且 sensor 不把它計入 `gaps`；`stories.md:1271` 本身即
  預告「屆時須改寫」，`Deferred` 的語意（有 owner、owner 是下一站）與此吻合，
  非規避。
- **事項 4（`US6.1` 記 `OK` 而非 `Deferred`）**：**攻擊成立——見本表 `R-04`**。
- **事項 5（`BR4.2` 整句求值）**：**攻擊成立且比自己設想的更嚴重——見本表
  `R-01`**（不只是「哪個情境會壞」，而是連 `FR5.1` 官方可測不變量本身都無法
  被現有規則正確實作）。
- **事項 6（W4 第 3 步、`BR2.1` 判讀）**：**維持**。`K-02` 把 `select_clarify_candidate`
  與 `user_message` 定義為兩個不同的 client→server type（`contract-summary.md:245`
  起），型別層面本就不會把候選選取送進 `classify(text)`，判讀有結構支撐。
- **事項 7（ADR-0006 四面向表）**：**維持**。已逐格核對 `requirements.md:595-604`、
  `:613-617`、`stories.md:1158-1200` 附近、`components.md:856-891` 附近的同名表格
  ——這些表格處理的是 FR1–FR10（基線）與 FR11–FR13（修訂 1，能力 11／12）兩個
  不同範圍，沒有任何一張表對 `IntentRouter`／`OpenRouter` 的 encryption 面做出
  與本站相反的判定；本站的「資料外送最小化」是真正的增量，非覆蓋。
- **事項 8（PBT P1–P5）**：**維持，附一個 Minor——見本表 `R-06`**。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `aidlc-sensor-traceability.ts --stage functional-design --output-path .../traceability.json` | `{"pass":false,"gaps":["AC1.1.5"],"orphans":[],"missing_from_table":[],"missing_from_upstream_ids":[],"invalid_entries":[],"invalid_targets":[],"findings_count":1}` | 與產出宣稱一致：唯一的 `gaps` 項是刻意記為 `GAP` 的 `AC1.1.5`，sensor 的機械檢查本身沒有查到本審查發現的任何一項（三問、多意圖資料模型、授權邊界、故事層級彙總一致性都在機械檢查的射程之外）。 |
| `grep -cE '^  - id: BR'`／逐群組計數／`category:` 計數 | 31 條；`BR1`–`BR8` 分組 3/5/6/3/5/3/3/3；類別 constraint 13／policy 8／calculation 7／validation 2／authorization 1 | 與 `rules.md` 規則摘要表逐格相符，§七自檢「6 可算的數字先算再寫」通過屬實。 |
| `sed -n` 對 `unit-of-work.md:141/143/154/156/158`、`contract-summary.md:745/797-800` 逐行核對 | 行號與引述文字完全相符 | §七自檢「3 引用逐字核對」的更正屬實，未發現殘留行號錯誤。 |

### Summary

**新引入**：2 項（R-01、R-02——皆由本站 `[IR1]`=A 與本站新寫的規則/實體直接
造成，上游沒有對應缺陷）。**既存漏審**：0 項（`BR5.5` 本身是本站新定的規則，
故 R-03 歸類為新引入而非既存漏審；`AC1.1.5` 的 GAP 判定已在本站之前被正確
揭露，不重複列為發現）。**新設計問題**：3 項（R-03、R-04、R-05——分別是規則
的可執行性、追溯表彙總規則的跨檔一致性、規則引用的語意正確性）。

核心問題：本站在「反問述詞如何求值」這個單一決策點上做得很扎實
（`[IR1]`=A、`BR3.x`、PBT property 都經得起查），但在**反問之外的三個相鄰面**
——多意圖如何與反問共用同一個資料結構（R-01，Critical）、本站自己新增的
記憶讀取邊界是否可執行（R-03）、本站對契約欄位的改動是否踩在授權線內
（R-02）——留下了會讓下一站或 `code-generation` 直接選錯方向的空白，且其中
R-01 直接命中 `requirements.md` 自己給的官方可測不變量，不是邊緣案例。

VERDICT: NOT-READY
