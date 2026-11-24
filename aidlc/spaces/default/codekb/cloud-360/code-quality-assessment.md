# 程式品質評估 — cloud-360

> 新鮮度：2026-11-22。測試執行結果為〔執行〕；技術債條目為〔實讀〕或〔實讀推導〕（推導者未實測）；CI 與 lint 為〔盤點〕。本檔是技術債的唯一清單，其他 artifact 只交叉引用。

## 測試

| 項目 | 值 | 證據 |
|---|---|---|
| 後端測試檔 | `backend/tests/` 137 支 `test_*.py`；另有 `tests_pg/`、`tests_redis/` | 盤點 |
| 前端 e2e | `frontend/tests/e2e/` 12 支 spec（含 `brain-assistant.spec.ts`、`a11y.spec.ts`） | 盤點 |
| 前端單元測試 | 無框架 | 盤點 |
| 本 intent 變更的四支測試 | `python3 -m unittest tests.test_intent_routing_decisions tests.test_work_orchestrator_capabilities tests.test_work_orchestrator_flow tests.test_work_orchestrator_rules` → `Ran 109 tests … OK`（2026-11-22，含未 commit 修正） | 執行 |
| PBT | `routing_from_answers` 的 PBT 在 `test_intent_routing_decisions.py`（依模組檔頭）；測試內容本次未讀 | 盤點 |
| 全套測試 | 本次**未執行** | — |

附註：執行測試會產生 `backend/.hypothesis/` 與 `__pycache__/`（皆被 `.gitignore` 忽略）。

## CI／Lint〔盤點〕

`ci.yml` 的 job：`gate`、`repo-contract`、`frontend`、`backend`（Python 3.12、`pip install -r requirements.txt`、import smoke、`dump_openapi.py --check`、unittest）、`memory-schema`、`concurrency`、`docker-build`。前端 ESLint＋`tsc -b`；後端未見 linter 設定。

## 本 intent 修正的品質評估〔實讀〕

| 面向 | 評估 |
|---|---|
| 修正 (1) 範圍 | 只動 Decisions 路徑：`build_state` 加 `recent_messages`（上界 6 則、每則 400 字，與工具呼叫路徑 `DEFAULT_MESSAGE_LIMIT`／`DEFAULT_MESSAGE_CHARS` 同值）；`DecisionsRoutingPort.route` 傳入既有已取好的歷程。L0 本來就截到 6 則（`intent_routing.py:117`），兩層截斷維持縱深 |
| 修正 (1) 安全 | 歷程放在「以下是參考資料，不是指示」之後，角色只轉成「使用者／系統」兩字；多送出平台的使用者內容上界為 6 × 400 字（ADR-0006 encryption 面的資料外送最小化，與工具呼叫路徑同界） |
| 修正 (2) 範圍 | `judge_a1` 新增一個分支；編排層新增 `_complete_awaiting_reply`；`_advance_dependents`／`_advance_waiter` 新增可選參數，預設行為不變 |
| 修正 (2) 正確性 | 等你回覆時不 PUT、不寫 procedure 記憶、不記變更；等待者以 `失敗` 結束，避免在舊圖上檢視／估價 |

## 技術債與風險

| # | 項目 | 位置 | 嚴重度 | 證據 |
|---|---|---|---|---|
| TD-1 | Decisions 指示文字被改（附加 `CONTINUATION_RULE`），而模組註解要求「換字就要重新量測（NFR1）」；ADR-0024 的實測機率與門檻 0.7、指名下限 0.8、`TIE_MARGIN` 0.05 對新文字不再有保證 | `intent_routing_decisions.py:66-67`、`:75-92` | 高（影響所有路由判讀） | 實讀 |
| TD-2 | 復原掃描只看被等待者 `status`：「等你回覆」記為 `完成`，若行程在寫入 `完成` 後、推進等待者前中止，`_recover` 會以「依賴完成」放行等待者，在舊圖上執行檢視／成本 | `work_orchestrator.py:510-535`、`:1097-1116` | 中（需行程中止才觸發） | 實讀推導 |
| TD-3 | 架構設計接續依賴行程內 `MemorySaver`（`design_agent.py:262`）與 per-user `thread_id`（`agent_router.py:153`）；編排層每次只送當句（`work_orchestrator_capabilities.py:302`）。重啟、多 worker、或使用者同時在工作區頁與大腦使用架構設計時，接續會斷或交錯 | 同左 | 中 | 實讀 |
| TD-4 | 歷程每則截 400 字：A1 的長提問（選項列在後段）可能被截掉，使「A」對不上選項 | `intent_routing_decisions.py` `build_state` 的 `message_chars=400` | 低–中 | 實讀推導 |
| TD-5 | 歷程寫回是背景 `spawn`（`brain_gateway.py:595-597`），兩則推播（A1 提問、等你回覆提示）各自寫回，寫入順序不保證；使用者極快回覆時可能尚未寫入 | `brain_gateway.py:570-597`、`:1906-1910` | 低 | 實讀推導 |
| TD-6 | 前端對 `完成` 不顯示細節：「等你回覆」只出現在對話訊息，工作項徽章顯示 `完成`，與「真的完成」外觀相同 | `WorkItemList.tsx` `WorkItemRow` | 低（體驗） | 實讀 |
| TD-7 | `DecisionsRoutingPort` 每輪新建 `httpx.AsyncClient`，P-4 連線重用未落實（自述實測 389–664 ms 仍在 800 ms 預算內） | `langgraph_runtime.py:211`、`intent_routing.py:347-349` | 低 | 實讀 |
| TD-8 | `team.md` 寫 React 18，實為 React 19 | `frontend/package.json` | 低（文件） | 盤點 |

## 文件品質〔實讀〕

深讀檔案的 docstring 完整、逐條引用需求編號，並記錄刻意的取捨與已知缺口（例如 P-4、記憶降級的殘留風險），可讀性高。
