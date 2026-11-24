# 自動化測試計畫 — 大腦路由延續回答與架構設計提問狀態

> Intent：`261122-brain-routing-followup`（bugfix，Test Strategy：Minimal）
> 分桶與盤點見 `manual-test-cases.md` 的「覆蓋盤點」。本檔涵蓋「已自動化」12 項的落點與突變證據、「待自動化」的 open item，以及本 stage 對規格註解所做的補齊。

## 1. 落點與理由

全部落在 **Backend 單元／行為**層（`backend/tests/test_*.py`，stdlib `unittest`，性質測試用 `hypothesis`）：

- 本 intent 只改後端的路由層（`intent_routing_*`）與工作編排層（`work_orchestrator*`），不改 HTTP 端點、不改前端、不改 WebSocket 契約（`ws-contract.json`）、不改資料庫——所以 `team.md` 的規則 B（`TestClient`）與規則 C（e2e）都不觸發，規則 A（`role_permissions`）也不觸發。
- agent routing 屬 ADR-0006 的 PBT hard constraint，歷程截斷以 Hypothesis 性質測試驗證（NFR2）。
- Playwright e2e 刻意不觸及 LLM 路徑；本 intent 兩個缺陷的最後一段（真實模型回什麼）落在那條邊界之外，由手動案例承接。

## 2. 已自動化的落點（12 項）

範圍指令（本 stage 實跑，`Ran 124 tests … OK`）：

```
cd backend && python3 -m unittest tests.test_intent_routing_decisions tests.test_intent_routing_context tests.test_work_orchestrator_capabilities tests.test_work_orchestrator_flow tests.test_work_orchestrator_rules
```

| # | 行為 | 測試（檔案::類別::方法） | 具體斷言 | 突變 |
|---|---|---|---|---|
| A-1 | Decisions `state` 帶最後至多 6 則歷程、標發言者、置於參考資料區段 | `backend/tests/test_intent_routing_decisions.py::DecisionsEndToEndTest::test_follow_up_answer_carries_the_recent_conversation_into_state` | `state` 以「使用者這一句：\nA\n」開頭；含 `- 系統：您的應用程式要用哪種方式運行？A. 虛擬機器 (VM) B. 容器服務`；7 則中最舊的「很久以前的訊息0」不在、「很久以前的訊息」恰 4 次 | M6、M4（M4 只由 A-7 抓到，見 §4） |
| A-2 | `primary` 與 `wants_*` 指示附延續規則 | 同上 | `CONTINUATION_RULE` 出現在 `questions.primary.instructions` 與 `questions.wants_design.instructions` | M7 |
| A-3 | Decisions 路徑保留每則結尾 400 字 | `backend/tests/test_intent_routing_decisions.py::StateHistoryTruncationTest::test_a_long_question_keeps_its_trailing_options` | 含結尾選項、不含 `HEAD-MARKER`、含 `- 系統：{question[-400:]}` | M1 |
| A-4 | 工具呼叫路徑保留每則結尾 | `backend/tests/test_intent_routing_context.py::MinimalContextTest::test_a_long_question_keeps_its_trailing_options` | `prompt.user` 含結尾選項、不含 `HEAD-MARKER`、含 `- assistant：{question[-DEFAULT_MESSAGE_CHARS:]}\n` | M2 |
| A-5 | 上限 ≤ 0 時本文為空 | `backend/tests/test_intent_routing_context.py::MinimalContextTest::test_keep_tail_with_a_zero_limit_keeps_nothing` | `keep_tail(text, 0) == ""`、`keep_tail(text, -1) == ""`、`keep_tail(text, 3) == "ABC"` | M3 |
| A-6 | 使用者這一句在最前；無歷程時無歷程區段 | `backend/tests/test_intent_routing_decisions.py::StateHistoryTruncationTest::test_no_history_means_no_history_section`、`DecisionsEndToEndTest::test_request_shape_keeps_user_text_in_state_only`（既有）、A-7 | 不含「這一段對話的最後」；`state` 以「使用者這一句：\n幫我評核架構\n」開頭 | M5 |
| A-7 | 截斷性質（≤ 6 則、保序、每則 ≤ 400 字且為結尾、使用者句在最前） | `backend/tests/test_intent_routing_decisions.py::BuildStatePropertyTest::test_history_is_bounded_ordered_tail_truncated_and_after_the_user_sentence`（Hypothesis 300 例） | `state` 前綴後的內容逐字等於「參考資料標頭 ＋ 最後 min(6, n) 則、各取結尾 400 字」；上限 6／400 在測試內寫死 | M1、M4、M5 |
| A-8 | A1 判定四分支 | `backend/tests/test_work_orchestrator_capabilities.py::A1JudgementTest::test_a1_question_without_xml_awaits_reply_instead_of_failing`、`::test_a1_error_or_missing_xml_is_a_failure_even_with_http_200` | 提問＋complete → `failure is None`、`awaiting_reply is True`、保留提問；提問＋error → `a1_failed`；空白＋complete → `a1_no_xml` 且 `awaiting_reply is False` | M8 |
| A-9 | 等使用者回覆的工作項完成、無副作用、送提問與提示 | `backend/tests/test_work_orchestrator_flow.py::ArchitectureAwaitingReplyTest::test_question_without_diagram_completes_without_failure_or_persist`、`backend/tests/test_work_orchestrator_rules.py::PhraseTest::test_each_phrase_renders_exactly` | 狀態「完成」、`sideEffect == "none"`、無 `failureReason`；送出文字含提問與「架構設計：架構圖 #12：架構設計在等你回覆上面的問題，直接回答即可」、不含「沒有產出圖」；PUT 0 次、變更紀錄與 procedure 記憶皆空 | M8 |
| A-10 | 等待者不在舊圖上執行 | `backend/tests/test_work_orchestrator_flow.py::ArchitectureAwaitingReplyTest::test_waiters_do_not_run_on_the_unchanged_diagram` | 成本分析 `("失敗", "前一項架構設計：架構圖 #12還在等你回覆，這一項沒有執行")`；`GET /api/cost` 0 次 | M9 |
| A-11 | 復原掃描套用同一規則；已存回圖照常放行 | `backend/tests/test_work_orchestrator_flow.py::RecoveryTest::test_recovery_does_not_run_waiters_on_an_architecture_still_awaiting_reply`、`::test_recovery_starts_waiters_once_the_architecture_was_persisted`、`::test_orphan_waiter_is_advanced_once_even_with_two_concurrent_scans`（測資補 `dispatchStage`） | `request_sent` → 成本分析失敗、原因逐字、成本 API 0 次；`result_persisted` → 成本 API ≥ 1 次、成本分析「完成」 | M10、M11 |
| A-12 | 既有套件維持綠燈 | `cd backend && python3 -m unittest discover -s tests -t .` | code-generation 實跑 `Ran 1631 tests … OK (skipped=3)` | —（回歸基準，不適用突變） |

## 3. 本 stage 對規格註解的補齊（只改 docstring，不改行為）

`project.md` 必做 3b 要求每個**新增或改動**的自動化測試都有 `@purpose`／`@given`／`@step`／`@pass`／`@story`。code-generation 交付時有 15 個新增或改動的測試，檢查結果與處置：

| 測試 | 交付時的狀態 | 本 stage 處置 |
|---|---|---|
| `A1JudgementTest::test_a1_question_without_xml_awaits_reply_instead_of_failing`（新） | 只有一行說明，**五個標記全缺** | 補齊五標記與 `@note` |
| `A1JudgementTest::test_a1_error_or_missing_xml_is_a_failure_even_with_http_200`（斷言改動） | 只有一行說明，且說明仍寫「無 xml → a1_no_xml 並保留說明」，與改動後的斷言不符 | 首行改為「無 xml 也無文字 → a1_no_xml」，補齊五標記與 `@note` |
| `PhraseTest::test_every_phrase_has_a_case`、`::test_each_phrase_renders_exactly`（期望表新增兩個句型） | 無 docstring | 補齊五標記 |
| `RecoveryTest::test_orphan_waiter_is_advanced_once_even_with_two_concurrent_scans`（測資改動） | 只有原 NFR12.13 的說明 | 保留原說明，補齊五標記與 `@note`（說明為何補 `dispatchStage`） |
| `ArchitectureAwaitingReplyTest` 兩案 | 有五標記，但 `@step` 沒有 `操作 \| 預期結果` 的分隔，渲染後預期欄為空 | 拆成帶 `\|` 的步驟 |
| 本 intent 全部 15 案 | `@story` 寫 `US1.1` 或 `US3.1`。本 intent 沒有 user-stories 站；`US3.1` 在 `260920-orchestration-brain` 是「在子頁面開一段不相干的新對話」，與工作項的等你回覆**無關**，是錯的追溯 | 改為本 intent 的需求編號（如 `FR2.4（intent 261122-brain-routing-followup）`）；路由類保留「上層故事 US1.1」（`260920` 的「說出需求就被交辦」，確實是路由的上層故事） |
| 直接守住兩個缺陷或其防護邊界的 8 案（A-1 的 1 案、A-8 的 2 案、A-9／A-10 的 2 案、A-11 的 3 案） | 無 `@note` | 補 `@note`：寫出缺陷原貌或它防的錯誤實作，以及對應突變編號 |

補齊後以 `ast` 逐一取出 15 個測試的 docstring 機械核對：15 案五標記全數存在、所有 `@step` 都含 `|`。改完重跑範圍指令：`Ran 124 tests … OK`（與修改前相同，證明沒有改到行為）。

**規格註解目前到不了 TCMS**（見 `tcms-sync-report.md` §3）：`tcms_sync.py --spec` 只解析 Playwright 的 `/** */` 區塊與 `test.describe(`／`test(`，不解析 Python docstring；而且 CI 只有 `ui-regression` 會把 junit 回寫到 Kiwi，後端 `unittest` 的結果從未進 TCMS，所以這些測試在 TCMS 上沒有可更新的案例。規格註解仍照標準寫齊——它是 code 旁唯一的規格來源，日後後端 junit 接上 Kiwi、工具支援 Python 時即可直接同步。

## 4. 突變驗證

### code-generation 已做的 11 項（NFR4）

完整表格在 `construction/code-generation/code-summary.md` 第四節，摘要：

| # | 對象 | 突變 | 變紅的測試 |
|---|---|---|---|
| M1 | FR1.3（Decisions） | `build_state` 歷程改回取開頭 | A-3、A-7 |
| M2 | FR1.3（工具呼叫） | `build_routing_prompt` 歷程改回取開頭 | A-4 |
| M3 | FR1.3 上限 0 | `keep_tail` 移除 `limit <= 0` 防護 | A-5 |
| M4 | FR1.1 保序 | `build_state` 取前 6 則 | A-7（端到端 A-1 仍綠：上游 `fetch_routing_context` 已先截，`build_state` 的截斷是縱深防護） |
| M5 | FR1.4 | 使用者這一句截為 `[:20]` | A-7、`test_request_shape_keeps_user_text_in_state_only` |
| M6 | FR1.1 | `DecisionsRoutingPort.route` 不傳 `recent_messages` | A-1 |
| M7 | FR1.2 | `PRIMARY_INSTRUCTIONS` 移除 `CONTINUATION_RULE` | A-1／A-2 |
| M8 | FR2.1 | `judge_a1` 移除 `awaiting_reply` 分支 | A-8、A-9（兩案） |
| M9 | FR2.4 | `_complete_awaiting_reply` 以工作項本身狀態推進等待者 | A-10 |
| M10 | FR2.5 | `_recover` 停用 `_awaiting_reply` 分支 | A-11（request_sent 案） |
| M11 | FR2.5 過擋 | `_awaiting_reply` 不看 `dispatchStage` | A-11（result_persisted 案、orphan 案） |

code-generation 的突變驗證另抓到一個測試缺陷並已修正：M1 第一次跑時性質測試沒紅，因為 `st.text(max_size=1200)` 幾乎不產生超過 400 字的字串；策略改為「短文或 401–1200 字長文」後才紅。

### 本 stage 自行重跑的兩項（各對應一個缺陷）

兩項都以 Edit 工具改碼、先 `grep` 確認突變標記確實在檔案裡、跑範圍指令、再以 Edit 還原。

| # | 突變內容 | 結果 |
|---|---|---|
| M8（缺陷 2） | `work_orchestrator_capabilities.py` 第 158 行改為 `if False and xml is None and text.strip():` | **紅 3 項**：`A1JudgementTest.test_a1_question_without_xml_awaits_reply_instead_of_failing`、`ArchitectureAwaitingReplyTest.test_question_without_diagram_completes_without_failure_or_persist`、`ArchitectureAwaitingReplyTest.test_waiters_do_not_run_on_the_unchanged_diagram`（`Ran 124 tests … FAILED (failures=3)`），與 code-summary 記載相同 |
| M6（缺陷 1） | `intent_routing_port.py` 第 565 行 `recent_messages=tuple(recent_messages or ())` 改為 `recent_messages=()` | **紅 1 項**：`DecisionsEndToEndTest.test_follow_up_answer_carries_the_recent_conversation_into_state`（`FAILED (failures=1)`），與 code-summary 記載相同 |

還原後：`grep -rn MUTATION backend/services/` 0 筆、`git diff --stat backend/services/` 與突變前相同（6 檔 132＋／16−）、範圍指令 `Ran 124 tests … OK`。

## 5. 待自動化 —— open item

| # | 行為 | 狀態 | 理由 |
|---|---|---|---|
| O-1 | 平台竄改預檢的固定拒絕語「此需求毫無相關，請重新輸入」被 FR2.1 判成「等使用者回覆」 | **未寫腳本** | requirements 審查 R-02，以 Accepted risk 核可、本 intent 不處置。正確行為尚未定案，現在寫測試只能把錯的行為鎖住或寫一支必紅的測試。`judge_a1` 是純函式，可以自動化；待另開 intent 決定正確行為（例如閘道把預檢拒絕語標成另一種事件）時一併寫進 `A1JudgementTest`。 |

## 6. 不自動化（手動案例承接）

| # | 行為 | 手動案例 |
|---|---|---|
| M-1 | staging 真實 A1 只回提問時的畫面 | 架構設計只回提問時工作項顯示完成與等你回覆提示，不標為沒有產出圖 |
| M-2 | staging 真實 Decisions 對「A」的判讀（含 R-01 的歷程形狀） | 回答架構設計的選擇題只打 A 時直接交給架構設計，不出現反問卡 |
| M-3 | NFR1 六句重測 | NFR1 延續規則上線後 ADR-0024 實測六句的路由結果不變 |

理由皆為「呼叫真實 LLM、每跑一次花錢、且缺陷只在 staging 的 Decisions 路徑出現」，見 `manual-test-cases.md` 的「只能手動」表。
