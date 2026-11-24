## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-11-22T14:26:31Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/261122-brain-routing-followup/inception/requirements-analysis/requirements.md > FR1.1、FR1.2、FR2.3 與 FR1.1 驗收、NFR1 | 需求把「使用者回 A 時，歷程最後一則系統訊息是架構設計的提問」當成前提，但依程式現況不成立。FR2.3 要求在轉送提問之後再送「在等你回覆」提示；閘道的 `GatewaySink.emit_turn`（`backend/services/brain_gateway.py:599`）每次呼叫各存一則 assistant 訊息，提問與提示是兩次 `_emit("turn")`（`backend/services/work_orchestrator.py:1109-1113`），所以使用者回 A 時，「上一則系統訊息」是那句提示，提問在它之前。FR1.2 的延續規則寫「上一則系統提問」，FR1.1 的驗收只測「提問單獨作為最後一則」，NFR1 的第七句也沒說歷程長什麼樣，三處都沒涵蓋真實歷程形狀。 | 把真實歷程形狀（提問、提示依序為最後兩則）寫進 FR1.1 的驗收與 NFR1 第七句的量測輸入。FR1.2 的延續規則改成「最近的系統提問」之類不依賴「最後一則」的措辭，或明定提示文字如何不干擾判讀。 | New |
| R-02 | Major | aidlc/spaces/default/intents/261122-brain-routing-followup/inception/requirements-analysis/requirements.md > FR2.1、FR2.3 與 FR2 驗收 | FR2.1 把「沒有 xml 但有非空白文字」一律判為等使用者回覆，而 A1 回純文字不一定是在提問。實例：`backend/services/agent_router.py:88` 的平台自我竄改預檢，只送固定的 message「此需求毫無相關，請重新輸入」加 complete，沒有 xml、沒有 error；agent 說明「不需修改」或拒絕時也一樣。依 FR2.1／FR2.3，這些情況會顯示「架構設計在等你回覆上面的問題」，並讓等待它的檢視或成本以「前一項還在等你回覆」失敗，兩句話都不實。驗收只涵蓋「有提問」「只有空白」「有 error」三種，這個角落沒有被要求、也沒有被列為假設或範圍外。 | 在需求裡明確處置：要嘛定義如何區分「提問」與其他純文字（例如排除預檢的固定拒絕語），要嘛把提示與失敗原因改成不宣稱「在等你回覆」的中性措辭；並加一條驗收，覆蓋 A1 回固定拒絕語時的預期工作項狀態與畫面文字。 | New |
| R-03 | Minor | aidlc/spaces/default/intents/261122-brain-routing-followup/inception/requirements-analysis/requirements.md > FR1.1、ADR-0006 判定表的 Network exposure 列 | 歷程訊息內可能含換行與使用者自訂文字（先前使用者訊息、架構設計提問引用的專案名稱）。每則只以「- 使用者：」「- 系統：」作前綴，沒有要求處理訊息內的換行，使用者先前的訊息可偽造一行「- 系統：…」冒充系統提問，來影響延續判讀。判定表以「標為參考資料」當緩解，但本檔對使用者文字已有整理先例（`sanitize_target_name`），歷程沒有對應要求，也沒有列為假設或範圍外。 | 在 FR1.1 加一條：歷程訊息內的換行須折成空白或縮排，使它無法形成新的發言行；或把它明列為已知限制，並在判定表中據實調整緩解描述。 | New |
| R-04 | Minor | aidlc/spaces/default/intents/261122-brain-routing-followup/inception/requirements-analysis/requirements.md > NFR2、NFR1 | NFR2 的三項性質沒有涵蓋「保留的是最後 6 則、且保持舊→新順序」，也沒說明「使用者這一句永遠在最前面」與 `text_chars`（4000 字）截斷的關係。NFR1 沒有說前六句是以無歷程還是有歷程量測，且 ADR-0024 實測表第五句 primary 只有 0.68，貼近門檻 0.7，單次量測的「一致」沒有重複次數或容差，通過條件在模型有隨機性時不可二元判定。 | 為 NFR2 補上「最後 6 則且保序」性質，並寫明使用者一句超長時的預期。為 NFR1 寫明各句的歷程輸入、量測次數與可接受容差（或明說只比對路由結果而非機率）。 | New |
| R-05 | Minor | aidlc/spaces/default/intents/261122-brain-routing-followup/inception/requirements-analysis/requirements.md > 假設 A2 | A2 只處理「歷程寫入失敗」，但閘道是以背景 task 寫入 assistant 訊息（`backend/services/brain_gateway.py:599`，`gw.spawn(append_assistant_background…)`），推送已先送達。使用者極快回覆時，寫入可能尚未完成，歷程缺少提問，行為同樣退回修正前。這是「寫入尚未完成」而非「寫入失敗」，目前沒有被記載。 | 在 A2 補述背景寫入的競態，並寫明接受的理由（或指出可接受的退化行為）。 | New |

### Summary

需求目標清楚、驗收大多可測，與程式現況的事實（根因、復原規則、`PRIMARY_CRITERIA` 約束、ADR-0006 資料外送）大致一致。兩項 Major 是需求對真實歷程形狀與「純文字即提問」的假設不成立，建議在核准前修訂或明確接受；兩項皆有清楚的處置方式，所以不阻擋進入 code-generation。
