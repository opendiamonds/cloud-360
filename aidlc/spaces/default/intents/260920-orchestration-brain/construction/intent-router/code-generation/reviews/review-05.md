## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-02 | Resolved | Minor | 原要求是指名由哪一站追認 IntentDecision 的行程內欄位 resolution。code-summary 五之二第三節已指名 contract-design 修訂（並註明該站為 CONDITIONAL、可能被 skip），並給出備援落點為 brain-gateway 下一輪 code-generation 紀錄。intent_routing_types.py:260 的欄位仍為 compare=False、repr=False，ws-contract.json 未動，行為不受影響。承接站有名字、有風險註記，足以關閉這個紀錄型缺口。 |
| R-03 | Still applies | Minor | 契約句子未改：ws-contract.json:213 與 frontend/src/types/ws-contract.d.ts:132 仍寫「連線建立後的 UNAUTHORIZED（BR2.8）為 null」。程式行為經查證如開發者所述：輪內記憶授權拒絕經 _fail_turn_exc（brain_gateway.py:1364-1366）到 _fail_turn（:1241-1251），帶該輪 turnId。判讀已補記，改契約屬 brain-ws-contract 或 brain-gateway，記為已知限制是合理處置，但交接尚未落地到共用登錄（見新發現）。維持 Minor，不阻擋。 |
| R-05 | Still applies | Minor | 開發者的分析屬實且比原先更嚴重：MemoryFacade._authorize_approved（memory_facade.py:200-212）只讀 principal.is_approved，判定在任何取列之前，不碰資料庫；session_factory() 只建立 session 物件而不連線；_PrefetchForbidden 以正常回傳值通過 MemoryWorker.run，於 brain_gateway.py:466 呼叫 breaker.on_success()。所以半開探測由被拒身分承擔時，熔斷關閉沒有任何資料庫健康的實據。可達條件窄（半開期間恰由一個核准已被撤銷的身分探測），關閉後的下一次真實失敗會再計入。記錄型處置足夠；要根治須改 MemoryWorker 或 _prefetch，屬 brain-gateway。維持 Minor。 |
| R-06 | Still applies | Minor | 查證屬實：選定後走 _resolve_and_dispatch(scan=True)（brain_gateway.py:1629），scan 分支（:1488-1501）不讀 decision.intents 的 referent，唯一讀 referent 的是 scan=False 分支的 match_referent（:1503-1520）。test_brain_gateway_turn.py 的 test_select_keeps_the_referent_of_the_chosen_reading 只斷言 dispatch 收到的 Intent 含 referent，不斷言作業對象。已記為已知限制並指名由 brain-gateway 或後續 intent 決定；沒有新增固定現行行為的測試，這是要求的第二半，仍未做。維持 Minor。 |
| R-07 | Still applies | Minor | 查證屬實：memory_forbidden 記錄（brain_gateway.py:1355-1357）之後先 append_message 寫入原文（:1360），再 _fail_turn_exc（:1364-1366）。窗口窄，BR64.6 既有順序。已記為已知縱深缺口並建議後續處置，屬 brain-gateway。維持 Minor。 |
| R-08 | Still applies | Minor | 查證屬實：_on_select 重建判定 confidence 取被選候選分數或 0.0，below_threshold 固定為 False（brain_gateway.py:1621-1622），與 K-10 的字面關係不一致；全 backend 無讀取端。已補記為使用者確認後的判定、confidence 僅供觀測。維持 Minor。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/intent-router/code-generation/code-summary.md > 五之二 第三節「R-02、R-03、R-06、R-07、R-08 記為已知限制」；構造上對應 construction/functional-design/merge-blockers.md | 五項已知限制都寫著「由 conductor 併入 merge-blockers.md」，但目前該表中與 intent-router 有關的列只有第 5、13 列，沒有任何一列承接 R-02、R-03、R-05、R-06、R-07、R-08。除 code-summary 這一節之外，沒有別處登錄這些限制，若併入沒有發生，下一個讀共用表的人看不到它們。這是交接尚未完成而非本單元程式問題。 | 由 conductor 在關卡前於 merge-blockers.md 新增列登錄這六項（可合併為一列，標明單元為 intent-router、嚴重度 Minor、承接站如上），或在 code-summary 明寫「若未登錄則以本節為唯一紀錄」。 |
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/intent-router/code-generation/code-summary.md > 五之二 第一節「收據外、本單元依賴的介面」 | 此節只檢查了 memory_errors.py、memory_facade.py、database.py，漏列兩個 brain_gateway.py 實際 import 且自收據後已變動的檔：hierarchy_facade.py（brain_gateway.py:75；新增 project_admin 檢查與 HierarchyProjectAdminRequired）與 session_store.py（brain_gateway.py:86；append_message 新增 role 上限 32 字元）。我查證兩者不影響本單元：閘道只以字面 user 與 assistant 呼叫 append_message（brain_gateway.py:1360、:1758），也不呼叫 delete_project 或 delete_system；全套 1391 測試全綠。所以結論正確，但紀錄的「收據外介面」清單不完整。 | 在 code-summary 該節補上這兩個檔與上述判定，使「收據外依賴」的盤點完整。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 收據 reviewed-source-8a97526105f9.tsv 逐檔 shasum -a 256（27 檔） | 21 檔逐位元相同，6 檔不同：LOCAL-DEV.md、backend/.env.example、deploy/.env.example、deploy/docker-compose.deploy.yml、deploy/docker-compose.test.yml、deploy/render-env.sh | 與開發者宣稱完全一致 |
| git diff HEAD 讀六檔改動 | 只新增 MEMORY_DB_PASSWORD 相關行與 LOCAL-DEV.md 一節；render-env.sh 在 secret 迴圈與必填檢查各加一個名稱；BRAIN_ROUTER_ 計數 deploy compose 6、render-env.sh 6、deploy/.env.example 5、backend/.env.example 5、LOCAL-DEV.md 12，render-env.sh:152 仍為字面值 0.7 且不在 secret 迴圈內 | Step 11 重勾有實據支持 |
| 副本跑本單元五模組 | Ran 83，OK | 屬實 |
| 副本跑 test_brain_gateway_memory／rules／turn 加 test_langgraph_runtime | Ran 82，OK | 屬實 |
| 副本跑 discover -s tests（補 rsync repo 根目錄） | Ran 1391，OK（skipped=3） | 屬實；副本已刪除，repo 內未見 .pyc 或 .hypothesis |
| scripts/validate_env_contract.py、scripts/validate_repo_contract.py（python3 -B） | 兩者皆 passed | 屬實 |
| 計畫勾選計數 grep -c | 已勾 48、未勾 0 | 屬實 |

### Summary

開發者的宣稱全部經抽驗屬實：21／6 檔的雜湊分佈、六檔只新增 MEMORY_DB_PASSWORD、83／82／1391 的測試數，以及 R-05 比原先更嚴重（授權檢查不碰資料庫，半開探測關閉熔斷沒有健康實據）。重勾全部 48 格妥當，Step 11 的證據檔雖有變動，但改動只是新增項，BRAIN_ROUTER_ 五個變數與兩支 validator 我重跑仍成立。前輪 R-02 因承接站已指名而關閉，其餘 R-03、R-05、R-06、R-07、R-08 皆為 Minor 且需改 brain-gateway 或契約，記錄型處置足夠但仍適用；兩項新發現都是紀錄完整性的 Minor，不阻擋。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/intent-router/code-generation/traceability.json > MB-5 (status OK)；code-summary.md > 重新查驗與合併前必修第 5、13 項 > 二、殘留 | 兩個以上槽位都需澄清時，選定其一只交辦該槽位與已確定槽位，其餘不確定槽位不交辦且使用者不被告知（`intents_after_choice` 只取被選槽位）。這個殘留只寫在 §二 與 MB-5 的 note，沒進 §七 偏離與未驗項，MB-5 還標 `OK`。專案自己的規則說過：把有缺口的 AC 記成 OK 會讓追溯表看起來已覆蓋。靜默丟掉一件使用者說過的事，與「錯誤須浮出」的原則也有張力。 | 把它登記為指名承接站的 open item（產品取捨：逐槽位多輪反問，或交辦後明示「另一件事尚未處理」），放進 §七；MB-5 改為標示殘留的狀態，或拆出一列 GAP。 | Resolved (reviewer) |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/intent-router/code-generation/code-summary.md > 二、對 `K-10` 欄位集合的對齊紀錄 | `IntentDecision` 多了行程內欄位 `resolution`。我查證它不進任何序列化路徑：全 `backend/services` 無 `asdict`/`pickle` 用在判定物件，`PendingClarify` 只存在連線記憶體，`ClarifyCandidate` 仍逐欄組裝，`ws-contract.json` 未動。偏離如實記載，但只寫「下一輪契約修訂時追認」，沒有承接站。 | 在 §七 指名由哪一站在 `contract-summary.md` 的 `K-10` 追認「行程內附帶資料」，避免下一個讀契約的人以為欄位集合仍是四個。 | Unresolved |
| R-03 | Minor | backend/services/brain_gateway.py > `_on_user_message` 的 `memory_forbidden` 錯誤路徑；backend/ws-contract.json 與 frontend/src/types/ws-contract.d.ts > `turnId` 欄位說明 | 契約文字寫「連線建立後的 UNAUTHORIZED（BR2.8）turnId 為 null」，而本路徑的 UNAUTHORIZED 屬於某一輪、經 `_fail_turn` 帶該輪 turnId。程式合理，但契約的字面句子兩種讀法都成立；前端 `errorCategory` 只分類不依賴 turnId，所以今天不壞。 | 在 `code-summary.md` 明寫判讀（輪內授權錯誤帶 turnId），並交由 brain-gateway 單元於處理 #2 時一併把契約句子釐清，避免與 `_send_single_error` 的修法互相打架。 | Unresolved |
| R-04 | Minor | backend/tests/brain_gateway_fakes.py > `low_confidence`；backend/tests/test_brain_gateway_turn.py > #5 三個測試 | 閘道層的 #5 測試用手寫的 `resolution`，沒有經過真的 `decide`。候選 id 與對照 id 的配對，由 predicate 的 `@given` 測試單獨證明。兩段合起來成立，但沒有任何測試走過「真 `IntentRouter` 產生澄清判定、閘道選定、交辦意圖含 referent」整條線，將來有人改動 `_clarify_id` 或閘道取 id 的方式時，兩邊各自綠燈。 | 補一條以真 `decide` 結果餵給閘道的選定測試，或把配對責任寫成明確的結構性斷言；不阻擋。 | Resolved (reviewer) |
| R-05 | Minor | backend/services/brain_gateway.py > `_prefetch` 回傳 `_PrefetchForbidden` 的 OK 路徑；`MemoryWorker.run` | 授權拒絕以工作「成功回傳」的形式通過 `MemoryWorker`，所以熔斷器把它當成一次成功。這是想要的（不計入失敗），但副作用是：在熔斷半開狀態下，一個被拒絕的身分的探測會讓熔斷關閉，而實際上 facade 的資料庫可能仍不健康。 | 在 code-summary 補一句判斷與理由；若不想讓授權結果影響熔斷狀態，可在 `MemoryWorker` 對此型別不記成功。 | Unresolved |
| R-06 | Minor | backend/services/brain_gateway.py > `_on_select` 與 `_resolve_and_dispatch(scan=True)`（候選 3） | 第 5 項還原了被選候選的 `referent`，但選定後走的 `scan=True` 分支完全不讀 `decision.intents[*].referent`；全 backend 唯一讀 `referent` 的地方是 `scan=False` 分支的 `match_referent`（約 :1502-1520），`work_orchestrator` 也不讀。所以選定路徑上 `referent` 是只存在於 dispatch 參數裡的資料，不影響作業對象。若指涉詞是靠記憶解析出來的（原句不含目錄名稱，如 `test_select_keeps_the_referent_of_the_chosen_reading` 的情境），交辦會落在目前作業對象上，而高信心路徑會走 `match_referent` 設定或回報找不到對象。這不是本輪造成的退步（修前亦然），也符合 `BR64.13` 的原句掃描設計，但「#5 已解決」只在資料層成立，沒有行為層的測試鎖住「選定後對象如何決定」。 | 在 `code-summary.md` 或 open item 明寫「選定後 `referent` 不參與對象解析，僅靠原句掃描」，並指名由 `brain-gateway`／後續 intent 決定是否要對選定判定也跑 `match_referent`；補一條測試固定現行行為（記憶解析的 referent 不在原句 → 交辦於目前對象），避免日後誤以為已解析。 | New |
| R-07 | Minor | backend/services/brain_gateway.py > `_on_user_message`（候選 1） | 記憶授權被拒時，先 `append_message` 把使用者原文寫進該段歷程，再送 `UNAUTHORIZED`。若該段是共享段，一個已被撤銷核准的身分的原文會進入其他成員可見的歷程。此順序是 `BR64.6` 既有規則，本路徑只在核准於重驗與預取之間被撤銷時可達，窗口很窄，且握手與每則訊息重驗已先擋待核准帳號。 | 不阻擋；在 `code-summary.md` 記為已知縱深缺口，並建議後續讓「授權類錯誤」的輪次不寫入歷程，或至少不寫入共享段。 | New |
| R-08 | Minor | backend/services/brain_gateway.py:1621 `_on_select`（候選 2） | 選定後重建的 `IntentDecision` 為 `below_threshold=False`，但 `confidence` 取被選候選的分數（常低於門檻，無分數時為 `0.0`），與 `K-10`「`below_threshold` 等於 `confidence < threshold`」的關係不一致。全 backend 沒有任何程式讀 `decision.confidence` 或在 dispatch 前驗證該關係，故無實際影響；`IntentDecision` 也沒有執行期不變式檢查。 | 不阻擋。在 `code-summary.md` 註記這是「使用者確認後的判定」，`confidence` 僅供觀測；或改填門檻值以維持關係成立。 | New |

> R-02 Not re-checked this round

> R-03 Not re-checked this round

> R-05 Not re-checked this round

> R-06 Not re-checked this round

> R-07 Not re-checked this round

> R-08 Not re-checked this round
