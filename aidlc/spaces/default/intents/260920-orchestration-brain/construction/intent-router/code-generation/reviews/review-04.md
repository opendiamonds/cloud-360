## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

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

> R-01 Reviewer note: `OPEN-MB5-1`（兩個以上槽位都需澄清時，其餘槽位不交辦也不告知）已登記在 `merge-blockers.md` 第 5 列並由 `[EP-MB5]`=A 裁決交後續 intent 承接；重做節也如實寫出殘留。`traceability.json` 的 MB-5 仍標 `OK`，但 note 已寫明殘留，可接受。

> R-02 Reviewer note: `IntentDecision.resolution` 對 `K-10` 欄位集合的偏離，仍只寫「下一輪契約修訂時追認」，沒有指名由哪一站追認。不影響行為（`ws-contract.json` 未動，`resolution` 為 `compare=False`、`repr=False`、不序列化）。

> R-03 Reviewer note: 契約文字「連線建立後的 UNAUTHORIZED 其 turnId 為 null」與本路徑「輪內授權錯誤經 `_fail_turn` 帶該輪 turnId」的兩種讀法，仍未在 `code-summary.md` 明寫判讀。前端只分類錯誤碼，不依賴 turnId，今天不壞。

> R-04 Reviewer note: `test_brain_gateway_turn.py` 的 #5 測試現在經 `_routed` 呼叫真的 `decide` 產生澄清判定，再餵給閘道，候選 id 與 `resolution` 的配對走過整條線，不再只靠手寫替身。

> R-05 Reviewer note: `_prefetch` 把 `_PrefetchForbidden` 當作「成功回傳」通過 `MemoryWorker.run`，熔斷器會記成一次成功；半開狀態下被拒絕身分的探測可能讓熔斷關閉。仍無說明，後果輕微（見下方摘要）。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `unittest`：predicate、context、brain_gateway_turn、brain_gateway_memory、brain_gateway_rules（5 模組，未呼叫真實 LLM） | Ran 101 tests，OK | 本單元與其閘道接點的測試現況為綠。 |
| 人工逐行核對 #5 | `_clarify_id` 為候選 id 唯一產生點，`clarify_resolution_for` 與 `clarify_candidates_for` 同一迴圈形狀；`intents_after_choice` 以槽位序合併已確定槽位與被選候選；對照缺失回 `INTERNAL_ERROR`，不退回舊形狀 | #5 修正成立。測試斷言 dispatch 收到的 `Intent` 含 `referent` 與第二槽位，若還原為 `Intent(capability, None)` 會失敗，測試能紅。 |
| 人工逐行核對 #13 | `_memory_notes` 對 `MemoryForbidden` 記不含輸入的 WARN 後上拋；`_prefetch` 攔下並以 `forbidden_reason` 帶回，不計入熔斷；轉接器對同一 `user_id` 重拋；`error_for` 映射既有 `UNAUTHORIZED`；`MemoryFacade` 只有 `_authorize_approved`（帳號未核准）會對 `search` 拋拒絕，不會因角色缺 U15 而讓所有輪次被擋 | #13 修正成立，且正式接線（閘道預取）也涵蓋，不只是單元測試成立。閘道測試用真的 `IntentRouter` 並讓模型 factory 一被呼叫即失敗，若預取不攔會落成 `INTERNAL_ERROR` 而非 `UNAUTHORIZED`，測試能紅。 |
| 日誌檢查 | `_memory_notes`、`memory_forbidden`、`RoutingObservation` 皆只記白名單欄位（turnId、reason 代碼、能力 id），不含使用者原文或記憶內容；測試以含 `hunter2` 的原文斷言所有日誌不含它 | 符合「日誌不含使用者文字」。 |
| 平台自我竄改預檢 | 閘道 `_on_user_message` 先於一切呼叫 `is_platform_self_modification`；`IntentRouter.classify` 在 `fetch_routing_context` 與任何模型呼叫之前再檢一次，命中即拋 `PlatformSelfModificationRefused` | 縱深雙層，符合專案 Mandated 規則。 |
| ADR-0006 PBT | `test_intent_routing_predicate.py` 有 8 條 `@given`（P1–P7 與澄清還原性質），另有各分支可達性斷言 | agent routing 的 PBT hard constraint 成立。 |
| ADR-0006 四面向 | IAM：授權拒絕改為以 `UNAUTHORIZED` 結束且不降級；encryption：prompt 僅帶最少上下文，`recent` 與記憶長度有上界；network exposure：本單元無新增進程邊界；audit logging：`memory_forbidden` 安全日誌只含 turnId 與 reason | 四面向皆有處置，無缺項。 |

### Summary

#5 與 #13 都是真的修好了：#5 的還原對照由同一個 id 產生點支撐，測試走真的 `decide`，還原舊形狀會讓測試變紅；#13 同時修了 L0 與正式會經過的閘道預取，授權拒絕不降級、不計熔斷、日誌不含輸入，且測試能分辨兩處各自被還原。三個候選皆為 Minor：選定後 `referent` 不參與對象解析（現行設計如此，但沒有被記錄或鎖住）、拒絕前先寫歷程（`BR64.6` 既有順序，窗口很窄）、重建判定的 `confidence` 與 `below_threshold` 不一致（無讀取端）。沒有 Critical 或 Major，判 READY。
