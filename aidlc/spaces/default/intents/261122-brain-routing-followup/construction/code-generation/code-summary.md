# Code Generation 摘要：大腦路由延續回答與架構設計提問狀態

依核可計畫 `code-generation-plan.md` 的 Step 1–12 執行完畢。本檔記錄變更檔案、各需求狀態、測試數字、突變驗證結果與未完成項。所有數字皆為本輪實際執行指令的輸出，指令寫在各節。

## 一、變更檔案

| 檔案 | 變更 | 本輪或先前 |
|---|---|---|
| `backend/services/intent_routing_context.py` | 新增純函式 `keep_tail(text, limit)`（保留結尾、`limit ≤ 0` 回空字串）；`build_routing_prompt` 的歷程改用它（FR1.3） | 本輪 |
| `backend/services/intent_routing_decisions.py` | `build_state` 帶最後 6 則歷程、`CONTINUATION_RULE`、docstring 改寫（先前）；歷程改用 `keep_tail` 取結尾、docstring 補結尾截斷理由（本輪） | 先前＋本輪 |
| `backend/services/intent_routing_port.py` | `DecisionsRoutingPort.route` 傳入 `recent_messages` | 先前 |
| `backend/services/work_orchestrator_capabilities.py` | `A1Result.awaiting_reply` 與 `judge_a1` 分支 | 先前 |
| `backend/services/work_orchestrator.py` | `_complete_awaiting_reply`、`_advance_dependents`／`_advance_waiter` 的 `as_status`／`failure_phrase`（先前）；模組函式 `_awaiting_reply` 與 `_recover` 第二輪套用（FR2.5，本輪） | 先前＋本輪 |
| `backend/services/work_orchestrator_rules.py` | `PHRASES` 新增 `awaiting_reply`、`dependency_awaiting_reply` | 先前 |
| `backend/tests/test_intent_routing_decisions.py` | 新增 `StateHistoryTruncationTest`（2 案）、`BuildStatePropertyTest`（Hypothesis 1 案） | 先前＋本輪 |
| `backend/tests/test_intent_routing_context.py` | `MinimalContextTest` 新增 2 案 | 本輪 |
| `backend/tests/test_work_orchestrator_flow.py` | `RecoveryTest` 新增 2 案；既有 `test_orphan_waiter_is_advanced_once_even_with_two_concurrent_scans` 測資補 `"dispatchStage": "result_persisted"`（斷言不變） | 先前＋本輪 |
| `backend/tests/test_work_orchestrator_capabilities.py`、`test_work_orchestrator_rules.py` | 先前已新增的 A1 判定與文字樣板測試 | 先前 |
| `aidlc/spaces/default/intents/261122-brain-routing-followup/inception/decisions/0025-decisions-routing-carries-conversation-history.md` | 新 ADR（FR3.1） | 本輪 |

未碰：前端、`ws-contract.json`、OpenAPI、資料庫 schema、環境變數、`.claude/`、audit shard、`PRIMARY_CRITERIA`（`git diff backend/services/intent_routing_decisions.py` 中 `PRIMARY_CRITERIA` 區塊無變更）。因此不觸發 `schema_rbac.sql`／`DEPLOY.md`／`LOCAL-DEV.md` 同步義務。

## 二、需求狀態

| 需求 | 狀態 | 證據 |
|---|---|---|
| FR1.1 | 完成 | `DecisionsEndToEndTest.test_follow_up_answer_carries_the_recent_conversation_into_state`、`BuildStatePropertyTest` |
| FR1.2 | 完成 | `test_follow_up_answer_carries_the_recent_conversation_into_state`（斷言 `primary` 與 `wants_design` 指示含 `CONTINUATION_RULE`） |
| FR1.3 | 完成（本輪） | 兩條路徑共用 `keep_tail`；`StateHistoryTruncationTest.test_a_long_question_keeps_its_trailing_options`、`MinimalContextTest.test_a_long_question_keeps_its_trailing_options`、`MinimalContextTest.test_keep_tail_with_a_zero_limit_keeps_nothing` |
| FR1.4 | 完成 | `BuildStatePropertyTest`（性質 a）、`test_no_history_means_no_history_section`、`test_request_shape_keeps_user_text_in_state_only` |
| FR2.1 | 完成 | `A1JudgementTest` 兩案 |
| FR2.2、FR2.3 | 完成 | `ArchitectureAwaitingReplyTest.test_question_without_diagram_completes_without_failure_or_persist`、`PhraseTest` |
| FR2.4 | 完成 | `ArchitectureAwaitingReplyTest.test_waiters_do_not_run_on_the_unchanged_diagram` |
| FR2.5 | 完成（本輪） | `RecoveryTest.test_recovery_does_not_run_waiters_on_an_architecture_still_awaiting_reply`、`RecoveryTest.test_recovery_starts_waiters_once_the_architecture_was_persisted` |
| FR3.1 | 完成（本輪） | ADR-0025；Status 為 Proposed，待 NFR1 後轉 Accepted（比照 ADR-0024） |
| FR3.2 | 完成 | `build_state` docstring |
| NFR1 | **待辦** | 需部署到 staging 後量測，見第五節 |
| NFR2 | 完成（本輪） | `BuildStatePropertyTest.test_history_is_bounded_ordered_tail_truncated_and_after_the_user_sentence` |
| NFR3 | 完成 | 第三節 |
| NFR4 | 完成 | 第四節 |
| NFR5 | 完成 | `build_state` 預設 `message_limit=6`、`message_chars=400`，由性質測試以寫死的 6／400 驗證 |

**FR2.5 判準的依據**：架構設計正常完成的路徑是 `_settle_persisted` 先寫 `dispatchStage=result_persisted` 再呼叫 `_complete`（`work_orchestrator.py` 的 `_settle_persisted`），而 `_complete_awaiting_reply` 不改 `dispatchStage`（停在 `request_sent`）。所以「能力為架構設計（`R.CAP_ARCHITECTURE`）、狀態為完成（`R.STATUS_DONE`）、`dispatchStage` 不是 `result_persisted`」只會由「等你回覆」產生。能力欄位以工作項的 `capability` 判斷，與 `_run` 內 `if capability == R.CAP_ARCHITECTURE` 同一判法。

## 三、測試數字

範圍測試（`unit-test-instructions.md` 的指令）：

```
cd backend && python3 -m unittest tests.test_intent_routing_decisions tests.test_intent_routing_context tests.test_work_orchestrator_capabilities tests.test_work_orchestrator_flow tests.test_work_orchestrator_rules
```

| 時點 | 結果 |
|---|---|
| Step 2 修改前基準 | Ran 117 tests，OK |
| 全部完成、突變還原後 | Ran 124 tests，OK（＋7） |

全套（Step 10）：`cd backend && python3 -m unittest discover -s tests -t .` → **Ran 1631 tests，OK (skipped=3)**，0 失敗、0 錯誤（基準 1624＋本輪新增 7）。輸出中的 `ERROR:` 開頭行是既有測試刻意觸發的 log，不是測試錯誤。

驗證腳本：

- `python3 scripts/validate_repo_contract.py` → `Cloud-360 repository contract validation passed.`
- `python3 scripts/validate_env_contract.py` → `Cloud-360 environment configuration contract validation passed.`

本輪新增的 7 個測試：

1. `tests.test_intent_routing_decisions.StateHistoryTruncationTest.test_a_long_question_keeps_its_trailing_options`
2. `tests.test_intent_routing_decisions.StateHistoryTruncationTest.test_no_history_means_no_history_section`
3. `tests.test_intent_routing_decisions.BuildStatePropertyTest.test_history_is_bounded_ordered_tail_truncated_and_after_the_user_sentence`（Hypothesis，300 例）
4. `tests.test_intent_routing_context.MinimalContextTest.test_a_long_question_keeps_its_trailing_options`
5. `tests.test_intent_routing_context.MinimalContextTest.test_keep_tail_with_a_zero_limit_keeps_nothing`
6. `tests.test_work_orchestrator_flow.RecoveryTest.test_recovery_does_not_run_waiters_on_an_architecture_still_awaiting_reply`
7. `tests.test_work_orchestrator_flow.RecoveryTest.test_recovery_starts_waiters_once_the_architecture_was_persisted`

每個新測試的 docstring 皆有 `@purpose`／`@given`／`@step`／`@pass`／`@story`；這些測試沒有 HTTP 端點或 UI 頁面，`@api`／`@ui` 刻意不填。

## 四、突變驗證（NFR4）

每項突變以 Edit 工具改回錯誤行為、跑第三節的範圍測試指令、再以 Edit 還原。全部還原後範圍測試 124 個 OK，並以 `git diff backend/services/` 逐段確認沒有殘留突變。

| # | 對象 | 突變內容 | 變紅的測試 | 結果 |
|---|---|---|---|---|
| M1 | FR1.3（Decisions） | `build_state` 歷程改回 `str(text)[:message_chars]`（取開頭） | `StateHistoryTruncationTest.test_a_long_question_keeps_its_trailing_options`、`BuildStatePropertyTest` | 紅 → 還原後綠 |
| M2 | FR1.3（工具呼叫） | `build_routing_prompt` 歷程改回 `str(text)[:message_chars]` | `MinimalContextTest.test_a_long_question_keeps_its_trailing_options` | 紅 → 還原後綠 |
| M3 | FR1.3 上限 0 | `keep_tail` 移除 `limit <= 0` 防護（`[-0:]` 回全文） | `MinimalContextTest.test_keep_tail_with_a_zero_limit_keeps_nothing` | 紅 → 還原後綠 |
| M4 | FR1.1／NFR2 保序 | `build_state` 取前 6 則（`[:message_limit]`）而非最後 6 則 | `BuildStatePropertyTest` | 紅 → 還原後綠 |
| M5 | FR1.4 | 使用者這一句改截為 `[:20]` | `BuildStatePropertyTest`、`DecisionsEndToEndTest.test_request_shape_keeps_user_text_in_state_only` | 紅 → 還原後綠 |
| M6 | FR1.1 | `DecisionsRoutingPort.route` 不傳 `recent_messages` | `DecisionsEndToEndTest.test_follow_up_answer_carries_the_recent_conversation_into_state` | 紅 → 還原後綠 |
| M7 | FR1.2 | `PRIMARY_INSTRUCTIONS` 移除 `CONTINUATION_RULE` | `test_follow_up_answer_carries_the_recent_conversation_into_state` | 紅 → 還原後綠 |
| M8 | FR2.1 | `judge_a1` 移除 `awaiting_reply` 分支 | `A1JudgementTest.test_a1_question_without_xml_awaits_reply_instead_of_failing`、`ArchitectureAwaitingReplyTest` 兩案 | 紅 → 還原後綠 |
| M9 | FR2.4 | `_complete_awaiting_reply` 以工作項本身的狀態（完成）推進等待者 | `ArchitectureAwaitingReplyTest.test_waiters_do_not_run_on_the_unchanged_diagram` | 紅 → 還原後綠 |
| M10 | FR2.5 | `_recover` 停用 `_awaiting_reply` 分支（`if False and …`） | `RecoveryTest.test_recovery_does_not_run_waiters_on_an_architecture_still_awaiting_reply` | 紅 → 還原後綠 |
| M11 | FR2.5 過擋 | `_awaiting_reply` 移除 `dispatchStage` 判斷 | `RecoveryTest.test_recovery_starts_waiters_once_the_architecture_was_persisted`、`RecoveryTest.test_orphan_waiter_is_advanced_once_even_with_two_concurrent_scans` | 紅 → 還原後綠 |

**突變驗證抓到的測試缺陷（已修正）**：M1 第一次執行時，`BuildStatePropertyTest` **沒有變紅**——歷程文字的產生策略原為 `st.text(max_size=1200)`，Hypothesis 實際幾乎只產生短字串，300 例中沒有任何一則超過 400 字，「取開頭」與「取結尾」無從區分。已把策略改為「短文（≤ 60 字）或長文（401–1200 字）」兩類來源，重跑 M1 後性質測試即變紅。策略旁有註解說明此事。

**M4 的觀察**：取前 6 則的突變只被性質測試抓到，端到端的 `test_follow_up_answer_carries_the_recent_conversation_into_state` 仍為綠——上游 `intent_routing.fetch_routing_context` 已先截成最後 6 則，`build_state` 的截斷是縱深防護，只有直接呼叫 `build_state` 的性質測試碰得到它。這符合 FR1.4「截斷在路由層無條件發生、不依賴呼叫端先截」的意圖，也說明了該性質測試不是重複。

## 五、未完成項與已接受風險

1. **NFR1 staging 重新量測：待辦。** 本機無 OpenRouter 金鑰，所有路由測試以替身驗證請求形狀，沒有打真實 Decisions API。部署到 staging 後須以 ADR-0024 實測表六句＋「架構設計提問後只回 A」重新量測；通過條件見 requirements NFR1。任一句不通過回頭調整 `CONTINUATION_RULE` 文字，不得以調低門檻代替（requirements OQ1）。ADR-0025 的 Status 因此維持 Proposed。
2. **審查 R-01（Accepted risk，`requirements-analysis/reviews/review-01.md`）**：提問與「等你回覆」提示是兩次 `_emit("turn")`，閘道各存一則 assistant 訊息，所以使用者回 A 時歷程最後兩則依序為「提問」「提示」，「上一則系統訊息」是提示而非提問。延續規則寫的是「上一則系統提問」；實際影響待 NFR1「只回 A」案例以真實歷程形狀（提問、提示依序為最後兩則）驗證。本輪未改動。
3. **審查 R-02（Accepted risk，同檔）**：FR2.1 把「沒有 xml 但有非空白文字」一律判為等使用者回覆，而 A1 回純文字不一定是提問——例如 `agent_router.py` 的平台自我竄改預檢只回固定的「此需求毫無相關，請重新輸入」加 complete，此時畫面會顯示「架構設計在等你回覆上面的問題」，等待者也會以「還在等你回覆」失敗，兩句皆不實。依計畫「不在本計畫」一節不另行擴大範圍，本輪未處置，亦無測試覆蓋此角落。
4. 架構設計 agent 的對話記憶（`MemorySaver`）在重啟或多 worker 時遺失，屬既有限制（requirements OQ2），本輪未處置。

## 六、與計畫的差異

1. **`keep_tail` 的落點**：計畫寫兩處各自改成取結尾；實作改為在 `intent_routing_context.py` 新增一個共用純函式，`intent_routing_decisions.py` 從那裡 import（`intent_routing_context` 只依賴 `intent_routing_types`，不形成循環匯入）。理由：FR1.3 要求兩條路徑行為一致，一個實作比兩份同樣的切片更能保證一致，也讓 `limit == 0` 的防護只寫一次。突變 M1／M2 改的是兩處呼叫點，仍能分別驗證兩條路徑。
2. **多出兩個計畫未列的測試**：`test_no_history_means_no_history_section`（FR1 驗收第 4 條「沒有任何訊息時不含歷程區段」原本沒有直接斷言）與 `test_keep_tail_with_a_zero_limit_keeps_nothing`（dispatch 指示提到的 `[-0:]` 陷阱，沒有測試時突變 M3 不會被抓到）。
3. **性質測試的策略在突變驗證後修改**（見第四節）。
4. Step 6 的既有測試在 Step 2 基準（117 個）與最終範圍測試（124 個）中皆為綠，未另行單獨執行。
