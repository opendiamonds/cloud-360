# 測試結果

- 執行時間：2026-11-23T16:41:55Z（`date -u`）
- 基準：分支 `danniel/fix/brain-routing-followup-context`，HEAD `2ad499a` 加未 commit 的工作樹變更
- 執行者：本 stage 於主工作階段直接執行（不是轉引 code-generation 的回報）

## Build

| 檢查 | 指令（自 `backend/`） | 結果 | 輸出 |
|---|---|---|---|
| import smoke | `DATABASE_URL=… JWT_SECRET=… python3 -c "import main; print('app:', main.app.title)"` | 成功 | `app: Cloud-360 API` |
| OpenAPI 漂移 | `DATABASE_URL=… JWT_SECRET=… python3 scripts/dump_openapi.py --check` | 成功 | `規格檔與後端程式碼一致。` |
| WS 契約漂移 | `python3 scripts/dump_ws_contract.py --check` | 成功 | `WS 契約規格檔與後端程式碼一致。` |
| repo contract | `python3 scripts/validate_repo_contract.py`（repo 根） | 成功 | `Cloud-360 repository contract validation passed.` |
| env contract | `python3 scripts/validate_env_contract.py`（repo 根） | 成功 | `Cloud-360 environment configuration contract validation passed.` |

## 單元測試

stage 層 `unit-test-instructions.md` 只有一條範圍指令（本 intent 無 per-unit 目錄），執行一次：

| 指令 | 總數 | 通過 | 失敗 | 略過 |
|---|---|---|---|---|
| `cd backend && python3 -m unittest tests.test_intent_routing_decisions tests.test_intent_routing_context tests.test_work_orchestrator_capabilities tests.test_work_orchestrator_flow tests.test_work_orchestrator_rules` | 124 | 124 | 0 | 0 |

## 後端全套回歸（NFR3）

| 指令 | 總數 | 通過 | 失敗 | 略過 |
|---|---|---|---|---|
| `cd backend && python3 -m unittest discover -s tests -t .` | 1631 | 1628 | 0 | 3 |

基準為 1624 個測試、3 個略過；本 intent 新增 7 個，增減相符。

## 整合／效能／資安

Minimal 策略未產生額外測試指令，沒有其他可執行的指令。理由見各指引檔。

## 失敗明細

無。

## 覆蓋率

本 repo 的後端 `unittest` 未接覆蓋率工具，CI 也不量測，所以沒有覆蓋率報告。bugfix scope 的測試底線是「針對該缺陷的回歸測試＋既有套件維持綠燈」，不含行覆蓋率門檻。

## Target Verification Matrix

| Target ID | Source | Expected | Actual | Evidence | Owning Stage | Verdict |
|---|---|---|---|---|---|---|
| TC-REG | code-generation-plan.md > Testing Contract > obligations.scope_floor[0] | 每個缺陷各有針對性回歸測試 | 缺陷 1（Decisions 不帶歷程）：`test_follow_up_answer_carries_the_recent_conversation_into_state`；缺陷 2（只回提問判失敗）：`test_a1_question_without_xml_awaits_reply_instead_of_failing`、`ArchitectureAwaitingReplyTest` 兩案；皆在 124 個範圍測試內通過 | 上方「單元測試」表；突變 M6、M8 紅燈（code-summary.md） | build-and-test | Met |
| TC-GREEN | Testing Contract > obligations.scope_floor[1] | 既有後端套件全綠 | 1631 個，0 失敗、3 略過 | 上方「後端全套回歸」表 | build-and-test | Met |
| TC-REQ | Testing Contract > obligations.strategy_volume[0] | 每項需求至少一個可驗證測試 | FR1.1–FR2.5、NFR2、NFR4、NFR5 均有對應測試；FR3.1、FR3.2 為文件需求，以檔案存在與內容核對 | `cross-unit-traceability.md` | build-and-test | Met |
| TC-COMP | Testing Contract > obligations.strategy_volume[1] | 每個被改元件至少一個 happy-path 單元測試 | `intent_routing_decisions`、`intent_routing_context`、`intent_routing_port`（經 `DecisionsEndToEndTest`）、`work_orchestrator_capabilities`、`work_orchestrator`、`work_orchestrator_rules` 均有 | 上方「單元測試」表涵蓋的五個測試檔 | build-and-test | Met |
| TC-PBT | Testing Contract > applicable_notes[project]（ADR-0006 PBT hard constraint，agent routing） | agent routing 須有 property-based 測試 | `BuildStatePropertyTest.test_history_is_bounded_ordered_tail_truncated_and_after_the_user_sentence`（Hypothesis 300 例）通過 | 上方「單元測試」表；突變 M1、M4、M5 紅燈 | build-and-test | Met |
