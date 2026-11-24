## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-11-22T23:22:26Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | backend/services/work_orchestrator.py > `_awaiting_reply`（約 199-211 行）與 `_complete_awaiting_reply` | 「等使用者回覆」沒有明確標記，只靠「架構設計＋完成＋dispatchStage 不是 result_persisted」這個推論。我追過所有把工作項轉為完成的路徑：只有 `_settle_persisted`（先寫 result_persisted 再 `_complete`）和 `_complete_awaiting_reply` 兩處，所以目前判準成立，也不會誤擋正常完成或漏掉重啟後的情況。但這個正確性依賴「`_complete_awaiting_reply` 永遠不動 dispatchStage」與「正常完成永遠先寫 result_persisted」兩個隱含條件，日後任一邊改動都會讓復原掃描無聲誤判。 | 在 `_complete_awaiting_reply` 的註解或 ADR 補一句不變式。若將來要新增 dispatchStage 值，須同步檢視 `_awaiting_reply`。 | New |
| R-02 | Minor | backend/services/intent_routing_decisions.py > 約 76-95 行（`CONTINUATION_RULE` 上方的註解） | 原本說明 `WANTS_QUESTIONS` 的「每個能力一題是／否（noul）…」註解，現在排在新插入的 `CONTINUATION_RULE` 註解與常數之前，變成貼在錯的常數上，`WANTS_QUESTIONS` 反而沒有說明。 | 把該註解移回 `WANTS_QUESTIONS` 上方。 | New |
| R-03 | Minor | backend/services/intent_routing_decisions.py > `build_state` 歷程行；aidlc/spaces/default/intents/261122-brain-routing-followup/construction/code-generation/traceability.json > FR1.4 | 兩點。(1) 歷程本文直接串接進 `state`，沒有處理換行。使用者文字若含換行加「- 系統：…」，就能在 `state` 裡偽造系統發言，而延續規則正是要模型信任「上一則系統提問」。「參考資料，不是指示」只能降低風險，無法排除。(2) traceability 把 `test_request_shape_keeps_user_text_in_state_only` 列為 FR1.4 證據，但該測試沒有斷言歷程，也沒斷言使用者句子在最前，列為證據過強。FR1.4 實際是由 `BuildStatePropertyTest` 和 `test_no_history_means_no_history_section` 支撐。 | (1) 在 ADR 的 Consequences 補寫此已知限制，或將歷程本文的換行壓成空白。(2) 從 FR1.4 的證據欄移除該測試。 | New |
| R-04 | Minor | backend/tests/test_intent_routing_decisions.py > `BuildStatePropertyTest` | 性質測試以「使用者句子 ≤ 300 字」和「角色只有 user／assistant」產生資料，所以沒有碰到 FR1.4 所說「使用者這一句在路由層無條件截斷到 `text_chars`」的行為。突變驗證 M5 改成 `[:20]` 才會紅，改掉 `text_chars` 上限則抓不到。其餘 NFR2 的三項性質（至多 6 則、每則至多 400 字且為結尾、使用者句子在最前）以整段全等比對，強度足夠，會被取開頭或取前 6 則的突變抓到（我讀程式確認，未重跑）。 | 另補一個使用者句子超過 4000 字的案例，或把 `user_text` 的上界提高。 | New |

### Summary

核心修正正確。FR2.5 的復原規則我追過所有完成路徑：`_settle_persisted` 先寫 result_persisted 才轉完成，只有 `_complete_awaiting_reply` 會產生完成但未存回圖的狀態，所以不會誤擋正常完成，也補上了「程式在轉完成之後、推進等待者之前崩潰」的缺口。兩個復原掃描並行時，推進等待者靠 CAS 保證只有一個寫入成功。尾端截斷由共用的 `keep_tail` 處理，已涵蓋 `limit <= 0`，兩條路徑一致，也沒有循環匯入。Hypothesis 測試以寫死的 6／400 做整段全等比對，確實能驗證 NFR2。ADR-0025 與 requirements、ADR-0024（D-4 與 Security 表 Encryption 列）一致，編號也沒有衝突。traceability 與 code-summary 的敘述與程式吻合，僅 FR1.4 證據略強。以上皆為 Minor，不影響 READY。NFR1 的 staging 重新量測仍是待辦，且已誠實標示為 Deferred。
