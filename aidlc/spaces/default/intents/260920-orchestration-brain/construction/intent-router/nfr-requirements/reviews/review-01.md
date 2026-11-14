## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-09T23:46:07Z
**Iteration:** 1
**Review class:** advisory（單輪，兩種 verdict 皆為終局；本審查為決策支援，不擋閘門）
**覆蓋聲明：** 七個受審檔與全部必讀上游皆已開檔逐字核對；對 `build-and-test.md`、
`backend/services/memory_router.py`、`backend/services/memory_facade.py`、
`backend/services/langgraph_runtime.py` 做了獨立的 repo 實測。未執行機械
sensor 的 `upstream-coverage` 子指令（CLI 參數與本檔目錄結構不合，改以
`grep` 手動核對五個上游來源的引用覆蓋，結果與作者自報一致）；`traceability`
sensor 已重跑並確認 `pass:true, findings_count:0`。深度為 full，非 skimmed。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | `<R>/construction/intent-router/nfr-requirements/performance-requirements.md` 檔頭「已查 … `.60` 全部未用，故無碰撞」；`reliability-requirements.md:21` 的 `NFR4.60` | **ID 帶碰撞是真的，作者自稱已查但查錯。** `NFR4.60` 同時被本單元（`reliability-requirements.md:21`：「本單元無狀態，重啟後無任何需要還原的東西」）與已通過審查的 `session-store` 單元（`construction/session-store/nfr-requirements/observability-requirements.md:35`：「Redis 記憶體使用率須有一個應用端可讀的訊號」）各自宣告，兩者語意完全不同。獨立重跑 `grep -rhoE "NFR[0-9]+\.6[0-9]" <R>/construction/*/nfr-requirements/*.md` 按單元分組比對，確認 `.60–.69` 帶內**唯一**碰撞即此一項。**可構造的失敗情境**：`build-and-test`（3.6）彙整 `Target Verification Matrix` 時以 `NFR4.60` 為鍵查詢兩個單元的量測結果，會把「本單元結構性無狀態」的斷言與「Redis 記憶體訊號可讀」的斷言合併成同一列，其中一個驗證結果會覆蓋或錯配另一個；下游任何工具（`cross-unit-traceability.md`、追溯報表）以 ID 做 join 時同樣會產生交叉污染 | 本單元的 `NFR4.60` 改號（例如 `NFR4.65` 或更高），同步修正 `reliability-requirements.md:21`／`:36`、`traceability.json` 的對應 `target`、以及任何引用它的交叉段落；改號後重跑碰撞檢查確認 `.60+` 帶內無第二個重複 | New |
| R-02 | Critical | `security-requirements.md` §三（`NFR7.62` 的可達性）；對照 `backend/services/memory_router.py:181`（`POST /api/memory/records` 呼叫 `facade.write(...)`，`kind` 不限制）與 `backend/services/memory_types.py:41`（`MEMORY_KINDS = ("semantic","procedure","episodic")`） | **§三整節建立在一個已被現實推翻的前提上。** 本檔逐字宣稱「`MemoryFacade.write` 沒有任何呼叫者……`NFR7.62` 現在擋不到任何真實資料」，並據此把它定性為「前置護欄而非現行防護」。獨立查證：`memory_router.py`（`U8` 的 HTTP 層，未受版控的新檔，`stat` 顯示其 mtime 為 2026-10-09T10:25:57（本地），早於 `security-requirements.md` 本身的 mtime 2026-10-09T23:36:06（本地））已存在，其 `create_memory` handler 直接呼叫 `facade.write(mint_principal(current_user), kind=payload.kind, content=payload.content)`，且 `payload.kind` **不限制**於非 episodic（docstring 逐字「本端點不限制 kind，因為 `[FD4]`=A 逐字『kind 由使用者指定且限於封閉集合』」，封閉集合含 `episodic`）。**可構造的失敗情境**：任何使用者今天即可呼叫 `POST /api/memory/records` 帶 `kind=episodic` 建立一筆情節記憶；若本單元的指涉詞解析在 `search` 呼叫中未真正排除 `episodic`（`NFR7.62` 要驗的正是這一點），該記憶即可被 `U11` 的指涉詞解析讀到——這正是 `NFR7.62` 要防的洩漏路徑，且**現在就可達**，不是「`OQ-N3` 關閉那一刻才變成可達」。本檔把一條現行必要的防護誤記為前置護欄，會讓實作者誤判優先序（例如把它排到 `OQ-N3` 正式關閉之後才做） | 更新 §三：撤回「死碼」判定，改為「`MemoryFacade.write` 已有一個真實呼叫者（`U8` 的手動建立端點），`NFR7.62` 是現行防護，須在 `code-generation` 第一輪就實作斷言，不得遞延」。`OQ-N3`（U13／U12 的同進程寫入端缺口）是另一個獨立問題，不影響 `NFR7.62` 現在是否可達 | New |
| R-03 | Major | `security-requirements.md` §二之零（「兩條沒有 inception `NFR` 親代的需求」）與 §一的 Audit logging 列（「落為 `NFR7.60`」） | **方法不一致：IAM／Network 面給了孤兒 ID，Audit logging 面卻硬掛 `NFR7` 當親代，而理由同樣站不住。** `NFR7` 的逐字主體是「episodic memory 的**保存 90 天**與**刪除稽核**……其靜態儲存與傳輸的加密要求」——完全不提日誌內容限制。本檔自己在 §二之零論證 `SEC-1`／`SEC-2` 不得掛在 `NFR6` 之下，理由是「硬掛會製造一個錯誤的親代」；但 `NFR7.60`／`.61`／`.63`（日誌欄位白名單、`prompt_guard` 命中紀錄禁令）的真正來源同樣是 `project.md` 的 public-repo 輸出禁令與 ADR-0006 的 Audit logging 面，不是 `NFR7`——這與 `SEC-1`／`SEC-2` 的情形在結構上完全相同，卻被套用了相反的處置。**可構造的失敗情境**：下游若依 `NFR7` 的字面（保存與刪除稽核）去理解 `NFR7.60`／`.61`／`.63` 的適用範圍，可能誤以為它們只在涉及 episodic memory 的路徑才生效，而遺漏 `prompt_guard` 命中（與記憶無關的輸入）也要套用同一條日誌禁令——事實上本檔 §四 STRIDE 的 Information Disclosure 行已把它們一併列入，顯示它們的實際適用範圍比 `NFR7` 的字面寬 | 把 `NFR7.60`／`.61`／`.63` 改為第三個孤兒 ID（如 `SEC-3`），比照 `SEC-1`／`SEC-2` 的處置方式記在 §二之零，來源欄標注「`project.md` 的公開 repo 輸出禁令 ＋ ADR-0006 Audit logging 面」；或在 §二之零解釋為何 Audit logging 面與 IAM／Network 面的判準不同（若有正當理由） | New |
| R-04 | Major | `reliability-requirements.md`「不設 circuit breaker」段（約第 25–38 行） | **「加斷路器＝加回行程內狀態，與 `NFR3.67` 直接衝突」這個論證是錯的。** `NFR3.67`（本檔自己定義）逐字只禁止「行程內的共享可變狀態（快取、計數器、連線池）」，並明文開放「需要跨行程共享的狀態一律走 `U10` 的 Redis」。斷路器的狀態（失敗計數、半開/全開時鐘）完全可以放在 Redis——這正是 `NFR3.67` 自己給的逃生門，不是本單元新發明的。**可構造的失敗情境**：若日後 `OpenRouter` 出現持續性故障（非本檔已排除的「單請求放大」情境，而是跨多個不同使用者、不同請求的系統性中斷），每一個請求仍會各自等滿 5 秒逾時才失敗——本檔自己承認這是「真實」的代價，卻用一個不成立的「直接衝突」論證把 Redis-backed 斷路器這個選項排除掉，而不是誠實地說「這一輪選擇不做，留給 `langgraph_runtime` 共用層」。若實作者讀到「直接衝突」會誤以為斷路器在架構上不可能，而真正的理由只是「這一輪不在本單元做」 | 改寫理由：刪除或修正「與 `NFR3.67` 直接衝突」這句（Redis-backed 斷路器不違反 `NFR3.67`），改為「本單元選擇不建，因為重試=0／逾時=5s／單輪 1 次呼叫已覆蓋大部分場景，剩餘的『供應商系統性故障時避免逐請求等滿 5 秒』留給共用的 `langgraph_runtime` 出站層評估是否值得用 Redis 狀態實作」 | New |
| R-05 | Major | `performance-requirements.md`「預算切分的算式」段（約第 28–46 行）；對照 `requirements.md:482-498`（`NFR3` 的量測邊界）與 `contract-summary.md` `X-01`（約 1100–1150 行，C1 成本能力的 `x-streaming-rule`：「不得對成本做 token 級巢狀串流轉送……C1 的『串流』是每秒輪詢 DB 的狀態事件」） | **800 + 1200 = 2000 這個算式至少有兩段時間沒有被分配到，而且作者要求我檢查的正是這一點。** (1) `NFR3.60` 的量測邊界是「從進入 `classify` 到回傳 `IntentDecision`」，`NFR3` 的量測邊界是「送出 → WebSocket 收到第一個內容 token」；兩者之間還有：`U13` 收到 WS 訊息到呼叫 `classify` 之前的處理、`classify` 回傳後 `U13` 轉交 `U12` 建立工作項、`U12` 分派到實際能力 agent 的開銷——這段「交接膠水時間」沒有被算進 800ms（本單元自己的範圍），也沒有被算進「下游能力 agent 首字 1200ms」（本檔自陳「本站不擁有，記為對下游的預算宣告」），它懸在兩個預算之間。(2) 更具體地，已核可的 `contract-summary.md` 明文規定 C1 成本能力**不是**逐 token 串流，而是**每秒輪詢 DB 的狀態事件**——對這條路徑，使用者看到的第一個「內容」在架構上就有約 0–1000ms 的輪詢粒度延遲，與 Jev 的實際運算時間無關。本檔的 1200ms 下游預算假設的是一個能產出「第一個 token」的串流下游，但至少一個已核可的下游能力（C1）結構上不是這樣。**可構造的失敗情境**：`build-and-test` 實測 `NFR3`（端到端 P50）時，即使 `classify` 穩定在 800ms 內、C1 的 LLM 呼叫本身也夠快，整條鏈仍可能因輪詢粒度與交接開銷逼近甚至超過 2000ms，而本檔的 Target Verification Matrix 會顯示 `NFR3.60`（本單元的 800ms）`Met`，卻無法解釋為什麼端到端的 `NFR3` 仍 `Not Met`——預算切分沒有提供可歸因的診斷力 | 在「與下游的三項交互」或新增一節裡明確記載：(a) 交接開銷（`U13`→`U12`→能力分派）目前無預算歸屬，建議明確劃入某一段或獨立列為第三段；(b) 對於輪詢型下游（C1 等），1200ms 預算的適用性須重新定義「首字」在輪詢語意下的等價事件（例如第一個 `progress` 事件抵達 WS 的時間），否則該預算對這類下游沒有意義。本檔已有的「量測機制落點全部落 `build-and-test`」仍可維持，但須把這個歸因缺口寫明，供 `build-and-test` 設計測量點時能正確拆解延遲來源 | New |
| R-06 | Major | `nfr-requirements-questions.md` `[N3]` 選項 A 本文與 `traceability.json` 的 `reverse` 區塊 `OQ-10` 列（「本站解掉了它」） | **「解掉了上游標的『無自然承接站』」這句話把『保證會被嘗試』和『保證會產出』混為一談，而承接它的前提條件至今未滿足。** `build-and-test`（3.6）確實是 `execution: ALWAYS`（已讀 `.claude/aidlc-common/stages/construction/build-and-test.md` 確認），且其 Step 1 確實會讀取 `nfr-requirements/` 下的全部產出並建立 Target Verification Matrix——這部分 `[N3]`=A 的機制性宣稱是對的。但 `NFR1`／`NFR10` 要用真實 Jev 回應填入 `Actual` 欄，前提是 `OPENROUTER_API_KEY` 已配置；獨立查證 `construction/brain-infra/nfr-requirements/nfr-requirements-questions.md` 的 `N14`（「金鑰就緒確認」）**`[Answer]:` 欄仍為空**，且本檔自己的 `V4g` 已查過 `backend/.env` 仍不存在、`OPENROUTER_API_KEY` 未設——這與 `project.md` 記過的「approval-handoff:5d0af04b 反面教材」（填一個看起來合理的轉移目標但其實是死指派）同形：差別只在於這次轉移目標的 `execution` 真的是 `ALWAYS`，但目標站能否**實際產出**該指標，還卡在一個完全不受本單元或 `build-and-test` 控制的外部前提（人工把金鑰寫進 `.env`）。`build-and-test.md` Step 9 的失敗判準明文：若目標在那一刻仍不可執行且沒有更下游的 owning stage，它的結果是「`Unverified`，不是『deferred 成功』」，並觸發失敗升級，不是乾淨地產出基準。**可構造的失敗情境**：`build-and-test` 執行當天金鑰仍未配置（目前沒有任何機制強制在那之前補上），`NFR1`／`NFR10` 的目標被標 `Unverified`，觸發該站的失敗升級梯（最終可能 halt-and-ask），而不是如 `[N3]` 所宣稱的「跑標註集的那一刻必然會看到 Jev 的真實回傳」 | 把「金鑰須在 `build-and-test` 之前配置」列為本站明確的交接前置條件（而不是只存在於一份已經過期的 sibling 問題檔裡），並在 `traceability.json` 或 `tech-stack-decisions.md` 標注為 blocking 依賴；`[N3]`／`traceability.json` 的措辭改為「`build-and-test` 提供了執行路徑，但其成功仍依賴 `N14` 這個外部前置條件尚未滿足」，不要宣稱「已解掉」 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `aidlc-sensor-traceability.ts --stage nfr-requirements` | `pass:true, findings_count:0` | 獨立重跑，與作者自報一致。11 條 `upstream_ids` 與 `coverage`／`reverse` 的 `target` 格式通過機械檢查；**但本審查的 R-01 顯示機械檢查看不到跨單元 ID 碰撞**（它只驗本檔內部一致性），不構成對 R-01 的反證 |
| 手動 `grep -rhoE "NFR[0-9]+\.6[0-9]"` 按單元分組比對 | `.60–.69` 帶內發現 1 處跨單元碰撞（`NFR4.60`） | 證實 R-01；作者檔頭「已查……故無碰撞」的宣稱不成立 |
| 手動核對五個必讀上游（`functional-spec`／`rules.md`／`requirements.md`／`contract-summary`／`technology-stack`）在六個受審檔內皆有引用 | 全部 ≥1 處命中 | 與作者自報的 `upstream-coverage` 結果一致，CLI 旗標格式問題未獨立重跑該 sensor，以手動核對替代 |
| `backend/services/memory_router.py` 與 `memory_facade.py` 實讀 | 確認 `POST /api/memory/records` 呼叫 `facade.write()`，`kind` 含 `episodic`，檔案 mtime 早於受審產出 | 證實 R-02；`NFR7.62`「死碼」判定與現狀不符 |
| `backend/services/langgraph_runtime.py` 實讀 | `temperature: float = 0.0` 為函式簽章預設值，無條件傳入 `ChatOpenAI` | 證實 `TS-3a`（作者自查屬實，非本審查發現） |
| `grep` `with_structured_output`／`response_format`／`JsonOutputParser`／`logprobs` 於 `backend/` | 0 命中 | 證實 `V3`（作者自查屬實） |

### Summary

**發現分類計數**：新引入 1（R-01）、既存漏審 0、新設計問題 5（R-02、R-03、R-04、R-05、R-06）。

本站的查證紀律本身值得肯定——問題檔的 `V4` 更正紀錄、`[N3]` 的揭露式選項文字、
§三對 `NFR7.62` 可達性的主動檢查，都示範了 `project.md` 要求的自我查核精神。
但主要缺陷集中在**同一類失誤**：作者在文件內做的「已查證」宣稱，有兩處（ID
碰撞、`MemoryFacade.write` 無呼叫者）在獨立重查下並不成立——不是判斷錯誤，是
查證的時間點或範圍不夠（分別是：只查了自己熟悉的帶位區間、沒有在撰寫當下重新
確認一個會隨旁支單元並行推進而變動的事實）。另外三項（`NFR7` 的親代歸屬、斷路器
拒絕理由、預算切分的歸因缺口）是論證本身的邏輯缺口，不是查證缺口。兩個 Critical
都是可低成本修正的機械性問題（改號、改一節文字的定性），不影響本站其餘設計的
合理性；Major 項則會讓下游（`code-generation`、`build-and-test`）在實作與診斷
時走錯方向或誤判優先序。

VERDICT: NOT-READY
