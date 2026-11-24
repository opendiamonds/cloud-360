# 單元測試指引

## 測試框架

- Python 標準 `unittest`（本機無 pytest），Hypothesis 已在 `backend/requirements.txt`。
- 測試檔一律先 `import tests.helpers`（處理 `sys.path` 與 psycopg stub），沿用既有慣例。
- 不需資料庫、Redis 或網路：路由測試以 `FakeHttp` transport 攔截 Decisions 請求；編排測試以 `tests/work_orchestrator_fakes.py` 的 `Harness`／`FakeCapabilityApp`／`WorkItemFakeRedis`。

## 執行本 intent 的測試（範圍限定）

從 `backend/` 目錄執行：

```bash
cd backend && python3 -m unittest tests.test_intent_routing_decisions tests.test_intent_routing_context tests.test_work_orchestrator_capabilities tests.test_work_orchestrator_flow tests.test_work_orchestrator_rules
```

修正前基準（2026-11-22 實測）：上述五檔中前四檔加 rules 檔共 109 個以上測試，全綠。

## 預期覆蓋

| 需求 | 測試 |
|---|---|
| FR1.1、FR1.2、FR1.4 | `test_intent_routing_decisions.DecisionsEndToEndTest.test_follow_up_answer_carries_the_recent_conversation_into_state` |
| FR1.3（Decisions） | `test_intent_routing_decisions` 新增：長提問保留結尾選項 |
| FR1.3（工具呼叫） | `test_intent_routing_context` 新增：長提問保留結尾選項 |
| NFR2 | `test_intent_routing_decisions` 新增 Hypothesis 性質測試（最多 6 則、保序、結尾 400 字、使用者句在最前） |
| FR2.1 | `test_work_orchestrator_capabilities.A1JudgementTest` 兩案 |
| FR2.2、FR2.3 | `test_work_orchestrator_flow.ArchitectureAwaitingReplyTest.test_question_without_diagram_completes_without_failure_or_persist` |
| FR2.4 | `test_work_orchestrator_flow.ArchitectureAwaitingReplyTest.test_waiters_do_not_run_on_the_unchanged_diagram` |
| FR2.5 | `test_work_orchestrator_flow.RecoveryTest` 新增兩案（未存回圖 → 等待者結束；已存回圖 → 照常開始） |
| 文字樣板 | `test_work_orchestrator_rules.PhraseTest` |

既有後端全套須維持綠燈：

```bash
cd backend && python3 -m unittest discover -s tests -t .
```

（全套執行僅用於 Step 10 回歸，不作為本 intent 的單元測試指令。）

## 替身與資料

- Decisions 回應以測試檔內的 `body(...)` 產生，形狀照 ADR-0024 實測；不得連外。
- 復原測試以「先 hang 住 A1、`stop_all()` 模擬重啟、直接改 Redis hash 內工作項欄位」的既有手法構造狀態（見 `RecoveryTest`）。
- 新增的自動化測試在 docstring 寫 `@purpose`／`@given`／`@step`／`@pass`（tcms 撰寫標準 §4.4，Python 以 docstring 承載）；這些測試沒有 HTTP 端點或 UI 頁面，`@api`／`@ui` 不填，不得捏造。

## 突變驗證

每項修正逐一改回錯誤行為（例：結尾截斷改回 `[:400]`、復原規則移除 `dispatchStage` 判斷、`judge_a1` 移除 `awaiting_reply` 分支），以上方指令確認對應測試變紅，還原後再跑綠。結果記入 `code-summary.md`。
