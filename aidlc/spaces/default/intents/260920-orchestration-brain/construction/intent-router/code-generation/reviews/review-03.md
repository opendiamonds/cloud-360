## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-23T11:05:59Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/intent-router/code-generation/traceability.json > MB-5 (status OK)；code-summary.md > 重新查驗與合併前必修第 5、13 項 > 二、殘留 | 兩個以上槽位都需澄清時，選定其一只交辦該槽位與已確定槽位，其餘不確定槽位不交辦且使用者不被告知（`intents_after_choice` 只取被選槽位）。這個殘留只寫在 §二 與 MB-5 的 note，沒進 §七 偏離與未驗項，MB-5 還標 `OK`。專案自己的規則說過：把有缺口的 AC 記成 OK 會讓追溯表看起來已覆蓋。靜默丟掉一件使用者說過的事，與「錯誤須浮出」的原則也有張力。 | 把它登記為指名承接站的 open item（產品取捨：逐槽位多輪反問，或交辦後明示「另一件事尚未處理」），放進 §七；MB-5 改為標示殘留的狀態，或拆出一列 GAP。 | New |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/intent-router/code-generation/code-summary.md > 二、對 `K-10` 欄位集合的對齊紀錄 | `IntentDecision` 多了行程內欄位 `resolution`。我查證它不進任何序列化路徑：全 `backend/services` 無 `asdict`/`pickle` 用在判定物件，`PendingClarify` 只存在連線記憶體，`ClarifyCandidate` 仍逐欄組裝，`ws-contract.json` 未動。偏離如實記載，但只寫「下一輪契約修訂時追認」，沒有承接站。 | 在 §七 指名由哪一站在 `contract-summary.md` 的 `K-10` 追認「行程內附帶資料」，避免下一個讀契約的人以為欄位集合仍是四個。 | New |
| R-03 | Minor | backend/services/brain_gateway.py > `_on_user_message` 的 `memory_forbidden` 錯誤路徑；backend/ws-contract.json 與 frontend/src/types/ws-contract.d.ts > `turnId` 欄位說明 | 契約文字寫「連線建立後的 UNAUTHORIZED（BR2.8）turnId 為 null」，而本路徑的 UNAUTHORIZED 屬於某一輪、經 `_fail_turn` 帶該輪 turnId。程式合理，但契約的字面句子兩種讀法都成立；前端 `errorCategory` 只分類不依賴 turnId，所以今天不壞。 | 在 `code-summary.md` 明寫判讀（輪內授權錯誤帶 turnId），並交由 brain-gateway 單元於處理 #2 時一併把契約句子釐清，避免與 `_send_single_error` 的修法互相打架。 | New |
| R-04 | Minor | backend/tests/brain_gateway_fakes.py > `low_confidence`；backend/tests/test_brain_gateway_turn.py > #5 三個測試 | 閘道層的 #5 測試用手寫的 `resolution`，沒有經過真的 `decide`。候選 id 與對照 id 的配對，由 predicate 的 `@given` 測試單獨證明。兩段合起來成立，但沒有任何測試走過「真 `IntentRouter` 產生澄清判定、閘道選定、交辦意圖含 referent」整條線，將來有人改動 `_clarify_id` 或閘道取 id 的方式時，兩邊各自綠燈。 | 補一條以真 `decide` 結果餵給閘道的選定測試，或把配對責任寫成明確的結構性斷言；不阻擋。 | New |
| R-05 | Minor | backend/services/brain_gateway.py > `_prefetch` 回傳 `_PrefetchForbidden` 的 OK 路徑；`MemoryWorker.run` | 授權拒絕以工作「成功回傳」的形式通過 `MemoryWorker`，所以熔斷器把它當成一次成功。這是想要的（不計入失敗），但副作用是：在熔斷半開狀態下，一個被拒絕的身分的探測會讓熔斷關閉，而實際上 facade 的資料庫可能仍不健康。 | 在 code-summary 補一句判斷與理由；若不想讓授權結果影響熔斷狀態，可在 `MemoryWorker` 對此型別不記成功。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 依指示不執行任何測試、lint、build | N/A | 靜態審查：讀取 `git diff`（`brain_gateway.py`、`brain_gateway_rules.py`、`intent_routing.py`、`intent_routing_predicate.py`、fakes）、`code-summary.md` 末節、plan Step 13–15、`traceability.json` 的 MB-5／MB-13，並 grep 序列化路徑。測試數字與突變結果取自單元自己的紀錄，未獨立重跑。 |

**逐項回應審查重點**

- (a) 序列化：`resolution` 標 `compare=False, repr=False`，未見任何 `asdict`/`replace`/`pickle` 用於 `IntentDecision`，不進 WebSocket、日誌、Redis。槽位順序：`intents_after_choice` 以槽位序排序，單元測試與 `@given` 驗證兩種排列。
- (b) 授權與降級：`MemoryForbidden` 在預取工作內被攔下、不計入熔斷失敗、不降級；`forbidden_reason` 只是封閉的代碼值（`scope`/`owner`/`pending`），不含記憶或使用者資料，日誌測試也斷言輸入原文不出現。`forbidden_memory` 是伺服器訊息字串，不在 ws-contract 的封閉列舉內（只有 `code` 是），錯誤碼沿用 `UNAUTHORIZED`，前端窮盡 switch 不受影響。熔斷開啟或逾時時 facade 沒被呼叫，結果只是沒有記憶（降級），沒有任何記憶資料流出，不構成授權繞過。
- (c) 範圍：`brain_gateway.py` 的改動集中在 `PendingClarify.decision` 的填入、`_on_select`、`_prefetch`、轉接器與一筆日誌；未碰 `_send_single_error`，與 #2 無直接交互，唯一的銜接點是上表第三列的契約措辭。
- (d) 測試與突變：#5 兩側（產生端、消費端）各有突變紅燈；#13 兩個位置各有突變。真 `IntentRouter` 加「模型 factory 一被呼叫即失敗」的設計，確實能抓到降級回歸。替身同步後與真 `U11` 同形，未讓既有測試變弱。
- (e) Steps 1–12：抽查 `PendingClarify`、`intents_after_choice` 的 `__all__`、`MB-5`／`MB-13` 追溯列、Step 13–15 勾選與程式一致；八個模組存在與否未逐一開檔重驗。
- (f) ADR-0006：IAM 面向由 `MemoryFacade` 授權拒絕轉為輪終止，方向正確；audit logging 面向的 WARN 只帶 turnId 與 reason 代碼。

### Summary

本單元對 #5、#13 的修法站得住：行程內對照不外漏、授權拒絕不降級也不污染熔斷、日誌不帶輸入。需要人處理的是一個被標為 OK 的殘留（多槽位澄清只交辦一件）與幾處契約措辭、測試銜接的小缺口，皆不阻擋。
