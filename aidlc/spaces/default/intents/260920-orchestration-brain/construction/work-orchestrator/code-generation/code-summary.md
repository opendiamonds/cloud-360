# Code Summary — `U12 work-orchestrator`

> 依 `code-generation-plan.md`（Testing Contract `sha256:1f0b6822…`，`test-after`、`standard`）Step 1–12 完成；之後依使用者 2026-10-12 裁決一併修正 F1。
> 跨單元修改（`U10`／`U7`）**只做新增**：五個既有檔合計 `+227 −0`（`git diff --stat`；含 F1 修正的 `redis_gateway.py` `+13`）。
> **重大發現 F1**（`U10` 的 Lua 冷啟動在 redis-py 8.x 下必然失敗）：**本批已修（使用者 2026-10-12 裁決）**，見第五節。

## 一、交付檔案

### 新建

| 檔案 | 交付 # | 內容 |
|---|---|---|
| `backend/services/session_scripts/put_work_item.lua` | 1 | key 不存在即回 0、`HSETNX`；不改 TTL |
| `backend/services/session_scripts/update_work_item.lua` | 1 | 比對 status ＋ `dispatchStage` 後以**補丁**合併；`null` 即設 null；`decode_array_with_array_mt` 暫開並以 `pcall` 保證還原 |
| `backend/services/work_orchestrator_rules.py` | 5 | `transition`、`plan_waits`、`side_effect_on_stop`、`on_dependency_stopped`、目標圖判定、`PHRASES`（32 個句型） |
| `backend/services/work_orchestrator_capabilities.py` | 6 | `CapabilityClient`（ASGITransport ＋使用者 token）、`parse_sse`／`judge_a1`／`judge_a3`／`judge_advice_snapshot`、`CapabilityError`（只帶類別、狀態碼、例外類別名） |
| `backend/services/work_orchestrator.py` | 7 | `WorkOrchestrator`：`dispatch`／`correct`／`list_items`、`_run`（看門迴圈）、`_finish_persist`、`_recover`、`_advance`、`_cas`、`_emit` |
| `backend/tests/work_orchestrator_fakes.py` | 8 | 共用替身（非測試模組）：工作項 Lua 替身、一次回傳完整本體的 ASGI app、可推進時鐘、只收契約模型的 sink |
| `backend/tests/test_work_orchestrator_store.py` | 8 | 資料模型層 15 案 |
| `backend/tests/test_work_orchestrator_capabilities.py` | 8 | 資料存取層 13 案 |
| `backend/tests/test_work_orchestrator_rules.py` | 8 | 純函式 PBT 與句型 12 案 |
| `backend/tests/test_work_orchestrator_model.py` | 8 | `RuleBasedStateMachine`（60 例 × 25 步） |
| `backend/tests/test_work_orchestrator_flow.py` | 8 | 流程 36 案（含審查修正新增的 `CancellationTest` 3 案） |
| `backend/tests/test_work_orchestrator_boundaries.py` | 8 | 邊界 6 案 |
| `backend/tests/test_work_orchestrator_authz.py` | 8 | 經真實 app 的 allow／deny 5 案 |
| `backend/tests_redis/__init__.py` | 8 | opt-in 測試根：skip 條件與原因 |
| `backend/tests/test_redis_gateway_noscript.py` | F1 | CI 可見的回歸測試：替身於冷快取丟 redis-py 8.x 形狀（`NoScriptError`、無 `NOSCRIPT` 前綴）（3 案） |
| `backend/tests_redis/test_work_item_lua.py` | 8 | 兩支 Lua 在真實 Redis 上與參考實作逐案比對（4 案）＋ `U10` 冷啟動（`NoScriptError`）的回歸測試（1 案；原為 `expectedFailure`，F1 修正後改為一般測試） |

### 修改（跨單元，只新增）

| 檔案 | 單元 | 新增 |
|---|---|---|
| `backend/services/session_types.py` | `U10` | `WORK_ITEM_FIELD_PREFIX`、`work_item_field`、`decode_work_items`、`ref_put_work_item`、`ref_update_work_item`（`+91`） |
| `backend/services/session_store.py` | `U10` | `SCRIPT_PUT_WORK_ITEM`／`SCRIPT_UPDATE_WORK_ITEM`、`load_work_items`、`put_work_item`、`update_work_item`（`+80`） |
| `backend/services/hierarchy_facade.py` | `U7` | `HierarchyFacade.list_diagrams_of_system`（`+20`） |
| `backend/services/hierarchy_service.py` | `U7` | `list_diagrams_of_system`（`+23`）——**計畫未列的檔**，見第五節 D1 |
| `backend/services/redis_gateway.py` | `U10` | **計畫外的跨單元修正（F1）**：`RedisErrorTypes.noscript`（預設空）、`is_noscript_error` 先認該型別、`redis_py_error_types` 以 `getattr` 取 `NoScriptError`（`+13 −0`） |

零新依賴、零新環境變數、零新 HTTP 端點、零 DDL（不觸發 `schema_rbac.sql`／`DEPLOY.md` 同步）。

## 二、各步驟的測試結果

所有指令在 `backend/` 執行。

| Step | 指令 | 結果 |
|---|---|---|
| 2 就緒檢查 | `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_session_store_behaviour` | 44 OK |
| 2 兄弟測試基線（修改前） | `… -m unittest tests.test_session_store_behaviour tests.test_session_types tests.test_session_contract tests.test_hierarchy_service` | 110 OK |
| 4 資料模型 | `… -m unittest tests.test_work_orchestrator_store` | 15 OK |
| 4 Lua 真實 Redis（opt-in） | `REDIS_URL=redis://localhost:6391/15 … -m unittest tests_redis.test_work_item_lua`（本機 Redis 8.8.0、redis-py 8.1.0，scratchpad venv） | F1 修正前：5 tests，`OK (expected failures=1)`；**F1 修正後：5 tests，`OK`**（Redis 8.8.0 重新啟動、腳本快取為空） |
| 4 Lua 未設定 `REDIS_URL` | `… -m unittest tests_redis.test_work_item_lua` | `OK (skipped=5)`，skip 訊息寫明原因 |
| 6 資料存取 | `… -m unittest tests.test_work_orchestrator_capabilities` | 13 OK |
| 8 業務邏輯 | `rules` 12、`model` 1（60 例）、`flow` 36、`boundaries` 6、`authz` 5 | 全 OK |
| 8 本單元合計 | `unit-test-instructions.md §二` 的本單元指令（七個模組） | 初版 85 OK；**審查修正後 88 OK**（sink 改為每次 emit 讓出事件迴圈） |
| 8 兄弟測試（修改後） | 同 Step 2 基線指令 | **110 OK**（與基線相同） |
| F1 回歸 | `… -m unittest tests.test_redis_gateway_noscript` | 3 OK（修正後）；本單元 85、兄弟 110 於修正後重跑皆 OK |
| 9 OpenAPI 漂移 | `JWT_SECRET=test python3 scripts/dump_openapi.py --check` | 「規格檔與後端程式碼一致。」 |
| 11 環境 contract | `python3 scripts/validate_env_contract.py`（repo 根） | passed |
| 11 repo contract | `python3 scripts/validate_repo_contract.py`（repo 根） | passed |
| 參考 全套 | `JWT_SECRET=test … -m unittest discover -s tests` | 854 tests，4 failures——**全部**是 `test_progress_channel_contract` 掃到 repo 根 `.kilo/worktrees/secret-deposit/`（`git status --ignored` 為 `!!`，本機已忽略目錄、不在 CI）；與本單元無關，見第五節 F2 |

## 三、突變驗證

`HYPOTHESIS_NO_SHRINK=1`；以 scratchpad 的腳本逐項「套用 → 跑 → 還原 → 再跑」，每項都斷言突變字串在檔內恰出現一次。
還原後以 `cmp`／`grep` 確認原始碼與突變前相同；**無殘留突變**。

| # | 突變（`unit-test-instructions.md §四`） | 套用位置 | 紅燈的測試 | 還原後 |
|---|---|---|---|---|
| M1 | Lua 只比對 status | `session_types.ref_update_work_item`（替身與 CI 的載體） | `test_work_orchestrator_model`（不變量 (a)：已停掉、`request_sent`、sideEffect 為 none）；`CorrectTest.test_correct_interleaved_with_background_advance_reports_the_real_stage` | 綠 |
| M1-Lua | 同上 | `update_work_item.lua`（真實 Redis） | `tests_redis` 的 `stage_mismatch` 案 | 綠 |
| M2 | 整個物件覆寫 | `ref_update_work_item` | `UpdateWorkItemTest` 的補丁、null 兩案；模型測試以 `KeyError: 'status'` 中止（不是以不變量 (c) 的斷言失敗——覆寫後連 status 都不見了） | 綠 |
| M3 | `_advance` 不看寫入結果即啟動 | `work_orchestrator._advance` | `RecoveryTest.test_orphan_waiter_is_advanced_once_even_with_two_concurrent_scans`（列估價表被呼叫 2 次） | 綠 |
| M4 | `_finish_persist` 不用 shield | `_execute_architecture` | `InFlightPersistTest` 三案（停掉後與逾時後的變更紀錄遺失） | 綠 |
| M5 | 先送請求後記 `request_sent` | `_execute_architecture` | `CorrectTest.test_write_failure_before_request_means_nothing_is_sent` | 綠 |
| M6 | Authorization 改固定管理者 token | `CapabilityClient.__aenter__` | `authz` 的 A1 deny、C1 deny、token 過期三案 | 綠 |
| M7 | 停用判定沿用握手快照（不重查 `is_active`） | `_facade_sync` | `RobustnessTest` 停用兩案（存回前、PUT 後） | 綠 |
| M8 | `BR53.4` 一律照常開始 | `rules.on_dependency_stopped` | `WaitingTest.test_stopping_the_dependency_starts_cost_but_skips_review` | 綠 |
| M9 | log 帶入 `requestText` | `_log_transition` | `RobustnessTest.test_token_and_request_text_never_reach_logs_and_token_never_reaches_redis` | 綠 |
| M10 | `_fail_item` 取消條件改為無條件，且回到副作用之前（審查 R-01 的原形） | `_fail_item` | `CancellationTest.test_cost_timeout_still_pushes_and_says_so`、`CostPollingTest.test_polling_is_bounded_and_ends_in_cost_timeout` | 綠 |
| M10b | `_fail_item` 取消條件改為無條件（位置不變：所有副作用之後） | `_fail_item` | **存活**（流程 36 案全綠）——見下方說明 | 綠 |
| M11 | 看門迴圈越過 deadline 不重讀 status 即取消內層（審查 R-03 的原形） | `_run` | `CancellationTest.test_watchdog_does_not_cut_off_completion_after_the_deadline` | 綠 |

M1–M11 於審查修正後（sink 讓出版本）**全部重跑**，結果同上。

**M10b 存活是預期的，不是測試缺口**：修正把取消移到所有副作用（推送、失敗訊息、推進等待者）**之後**，
此時取消外層 `_run` 只會截斷一條已經沒有工作要做的執行鏈，沒有可觀察的後果，故任何測試都不會因它變紅。
真正會造成 R-01 的是「在副作用之前取消」，那就是 M10，已轉紅。

**一次突變第一次存活，已補強測試**：M3 起初未紅——第二個掃描啟動的重複 task 在 `estimateSetId` 的比對後寫入就中止，
建議快照仍只讀一次。原測試只數快照讀取，數錯了對象；改為同時數「列估價表」（能力呼叫的第一步）之後轉紅。
sink 改為讓出事件迴圈之後 M3 **再次存活**：第一個掃描啟動的 task 在第二個掃描期間就跑起來，讀到被替換成舊快照的
`load_work_items` 而提早結束。現改為只讓第二個掃描所屬的 task 讀舊快照、背景 task 一律讀真實值，並讓成本 task
停在第一個能力呼叫上計數，之後 M3 轉紅。

## 四、計畫 §二 的 26 項逐項落點

| # | 處置的落點 | 驗證 |
|---|---|---|
| 1、11、18、23 | `_finish_persist`：`asyncio.shield` 保護；`_put_with_timeout` **自建** `CapabilityClient`；自有最外層 `except`；PUT 上限 60 秒以注入時鐘判定；`_settle_persisted`／`_settle_put_failed`／`_settle_put_unknown` 依當下 status 分流（含「逾時判失敗後 PUT 才成功」） | `InFlightPersistTest` 四案；M4 |
| 2 | 所有推進經 `_advance`，寫入回 True 才執行 `then`（建 task、送訊息） | `RecoveryTest` 併發案；M3 |
| 3、12 | `_step`：`request_sent`／`persisting` 先寫成功才送 A1／A3／PUT | `test_write_failure_before_request_means_nothing_is_sent`；M5 |
| 4、7、24 | Lua 收補丁、腳本內合併；`null` 設 null；`decode_array_with_array_mt` 保留空陣列；`idempotent=False`；`correct` 比對失敗重讀重算 ≤ 5 次，超過記 WARNING 並回現況 | store ⑤⑥、`test_scripts_are_not_retried_on_a_connection_error`、`tests_redis`；M1、M2 |
| 19 | `_cas` 第三分支：`SessionBackendUnavailable` → 重讀，補丁每欄皆為目標值才視為成功；讀不到不做副作用、記 WARNING | `test_unknown_write_result_is_confirmed_by_rereading` |
| 5、10 | `_facade_sync` 自寫 `is_active` 判定；存回前停用 → 失敗（含存回前一次身分重查，見 D4）；存回後 → `BR51.4`／`BR51.5` 的 violation_behaviour；案例在 PUT 之後停用 | 停用兩案；M7 |
| 6、8 | 推進為處理中的補丁寫 `deadlineAt`、清 `waitingOn`／`dependsOn`；離開處理中的補丁含 `deadlineAt=None`；`side_effect_on_stop` 為唯一對照（`correct`、逾時、逾期掃描三處皆呼叫）；`PHRASES` 收齊 32 句型含「沒有執行：前一項…已停掉」，每句一案 | 模型不變量 (d)(e)；`PhraseTest`；rules PBT |
| 9 | `tests_redis/test_work_item_lua.py`（opt-in；未設定即 skip 並印原因）；**不在 CI** | 第二節 |
| 13、20 | 建構子注入 `clock`／`sleep`；三種能力的上限一律 `clock() >= deadlineAt`；看門迴圈以 `sleep` 切片，不用 `asyncio.wait_for`；每次快照 GET 計一次輪詢 | `TimeoutTest`、`test_polling_is_bounded_and_ends_in_cost_timeout` |
| 14、21 | AST 掃三個模組的 `import`／`from…import`（含函式內）；禁止清單含 `main` 與既有能力的 service／router、LLM 套件、`importlib`／`__import__`；patch `httpx.AsyncClient.send` 斷言 transport 皆為 `ASGITransport` | `test_work_orchestrator_boundaries.py` |
| 15 | 不實作加密；承接鏈見第五節 | — |
| 16 | `_emit`：每則訊息須為契約模型並再 `model_validate`；測試 sink 拒絕非模型輸入 | `test_every_message_is_a_contract_model`（以及所有流程案例） |
| 17 | token 出現在例外訊息的案例；401／403 不重試；輪詢 404 | `NoLeakTest`、`test_capability_failures_are_not_retried`、`test_cost_failures_are_distinguishable` |
| 22 | 建構子注入 `session_factory`（未注入時延遲取 `database.SessionLocal`）；交付 #4 | `FacadeThreadTest`、`ListDiagramsOfSystemTest` |
| 25 | 第五節揭露 | — |
| 26 | `traceability.json` 以 `NFR12.x` 對到實際測試檔 | 本站 `traceability.json` |
| — | `OPEN-WO12-6`／`-7`／`-9` | 第六節 |

## 五、偏離與揭露

### 重大發現

- **F1（`U10` 既存缺陷；本批已修，使用者 2026-10-12 裁決）**：`redis_gateway.is_noscript_error` 原以
  `"NOSCRIPT" in str(exc)` 判定冷啟動，但 redis-py 8.x 把 `NOSCRIPT` 回覆轉成 `NoScriptError`，訊息為
  `No matching script. Please use EVAL.`（**前綴被剝掉**；redis-py 8.1.0 實測）。於是 Redis 腳本快取為空時（每次 Redis
  重啟後），`EVALSHA` 被分類成 `redis_command_error`、不退回 `EVAL`——**所有** Lua 方法（`U10` 的 `append_message`、
  切換為獨立對話，以及本單元兩支）都拋 `SessionBackendUnavailable`，且不會自行恢復。替身的訊息帶 `NOSCRIPT` 前綴，
  故 CI 原本看不到；本單元的 `tests_redis` 第一次對真實 Redis 執行即查出。
  - **修正（計畫外的跨單元修正，`backend/services/redis_gateway.py`，`+13 −0`）**：`RedisErrorTypes` 新增欄位
    `noscript`（預設空 tuple，舊版客戶端與既有替身不受影響）；`is_noscript_error` 先以 `isinstance(exc, types.noscript)`
    判定，**原本的 `"NOSCRIPT" in str(exc)` 判斷保留**為退路；`redis_py_error_types` 以
    `getattr(redis_exceptions, "NoScriptError", None)` 取得型別（舊版沒有該類別時不 import 失敗）。其他語意不變。
  - **測試**：新增 `backend/tests/test_redis_gateway_noscript.py`（CI 可見；替身於冷快取丟新版形狀）3 案——冷快取
    `EVALSHA` 改以 `EVAL` 重送成功且第二次命中快取、兩種形狀皆認得而其他錯誤不認、未宣告 `noscript` 時仍以前綴判定。
    `tests_redis.test_work_item_lua.GatewayColdStartTest` 由 `expectedFailure` 改為一般測試，真實 Redis 上通過。
  - **突變驗證**：把修正中的 `isinstance(exc, types.noscript)` 分支拿掉（＝原本的判定語意）→
    `test_cold_cache_evalsha_falls_back_to_eval_and_succeeds` **ERROR**（`SessionBackendUnavailable`）、
    `test_both_shapes_are_recognised_and_other_errors_are_not` **FAIL**；還原後 3 案 OK、`cmp` 確認與修正版相同。
    另：修正前 `tests_redis` 的冷啟動案為 expected failure，修正後同一案在真實 Redis 上轉為 unexpected success
    （隨即移除 `expectedFailure`）。
  - 修正後重跑：本單元 85 OK、兄弟測試 110 OK（含 `test_session_contract` 對 `redis_gateway` 的靜態斷言）、
    `validate_repo_contract.py` passed。
- **F2（環境）**：全套 `discover` 的 4 個失敗來自本機已忽略目錄 `.kilo/worktrees/secret-deposit/` 被
  `test_progress_channel_contract` 掃到，與本單元無關、CI 的乾淨 checkout 不會有它。

### 偏離（對計畫或 functional-design 文字）

| # | 偏離 | 理由 |
|---|---|---|
| D1 | 多改一個 `U7` 檔 `hierarchy_service.py`（計畫只列 `hierarchy_facade.py`） | facade 一律委派 service 層（`U7` 的分層）；把查詢寫在 facade 會破壞該單元的形狀。只新增一個函式 |
| D2 | 工作項多三個伺服器內部欄位：`targetDiagramTitle`、`targetDisplay`、`dispatchIndex`（`entities.md` 未列） | sideEffect 的〈名稱〉在 `correct` 時無 DB 可查（`targetDiagramTitle` 於寫 `request_sent` 時一併寫入）；建立句型的作業對象；同一 `createdAt` 下依原句順序排序。皆不送前端（`_public` 只取契約七欄） |
| D3 | 作業對象名稱以「架構圖 #12」「系統 #3」呈現 | session 只存識別碼；取名稱要在**回覆之前**讀 DB，與 `NFR12.1` 的先回覆衝突。label 仍為固定句型且不含原句 |
| D4 | 存回之前多一次身分重查（不做 facade 操作的 `_call_facade`） | 目標為圖時，存回前沒有任何 facade 呼叫；為使 `NFR12.9` 第一案在 HTTP 路徑之外也成立（停用即失敗、不 PUT） |
| D5 | 完成的架構設計 sideEffect 寫「已存回架構圖〈名稱〉」；檢視完成寫「已建立一份檢視紀錄」 | 設計未定完成時的 sideEffect；`BR51.4` 要求在其上註明「變更紀錄未寫入」，需要一個如實的基底 |
| D6 | 架構檢視以**一次**比對後寫入同時完成 `request_sent → result_persisted` 與 處理中 → 完成 | 兩步之間沒有副作用，合併不改可觀察行為 |
| D7 | `BR56.6` 原文「以 `asyncio.wait_for` 包住」改為注入時鐘自行判定 | 計畫 §二 第 13、20 項已核可；在此對 functional-design 文字揭露 |
| D8 | PUT 遇傳輸層錯誤與 60 秒逾時同列為「結果未知」 | ASGI 傳輸下 PUT 在 threadpool，取消等待不代表沒寫入；處理中 → 失敗（sideEffect 為「可能已存回…」），已停掉／已失敗 → sideEffect 維持「可能已存回…」 |
| D9 | `ASGITransport(raise_app_exceptions=False)` | app 內未處理例外落成 500 → 「〈能力〉暫時無法使用」，例外原文不進本單元 |
| D10 | 成本完成句型固定附「依既有的估價表與已產生的建議，不會因改圖而重算」 | `BR57.5`；不分是否曾等待 |
| D11 | procedure 記憶內容為「〈能力名稱〉（〈label〉）」 | `BR51.5` 為「能力名稱＋label」，未定格式 |

### 計畫要求的揭露

- **`tests_redis` 不在 CI**：`ci.yml` 的 backend job 沒有 Redis service，`discover -s tests` 也看不到它。真實 Redis 上的
  一致性只由本機 opt-in 與 code review 承擔；本輪本機實跑（Redis 8.8.0）結果見第二節。CI 驗的是替身與參考實作。
- **`BR55.7` 延伸至逾時失敗項**：被牆鐘上限或復原掃描判為失敗後 PUT 才成功，同樣寫變更紀錄、sideEffect 改「已存回…」、
  status 維持失敗（`test_timed_out_before_put_returns_still_records_the_change`）。
- **重啟後 `persisting` 孤兒的稽核缺口**：PUT 在途時行程重啟，收尾協程隨行程消失；之後的逾期掃描只能把它轉為失敗、
  sideEffect 為「可能已存回架構圖〈名稱〉」——**若 PUT 其實已成功，圖已被改寫而沒有變更紀錄**。本單元沒有可靠方法事後
  得知 PUT 結果（對照 `updated_at` 無法區分是誰改的），故如實揭露、不補寫。
- **`requestText` 靜態加密的承接鏈**：本單元不實作加密（併入上游 `OQ-3`）。承接順序 `nfr-design`（CONDITIONAL，本單元
  未定手段）→ `infrastructure-design`（Redis 部署面；本單元該站判定無新資源）→ `code-generation`（ALWAYS；本站亦未定）。
  **三站都沒有落地手段，`OQ-3` 仍開著**，需上游或使用者指定承接。
- **functional-spec 第六節交互 1 未測**：「背景 A1 與 `U11` 併發時 `configure_provider_env()` 不改錯供應商設定」的測試
  不在計畫的 26 項與測試清單內，本站未做；列為開放項。
- **`SessionStore` 在事件迴圈上同步呼叫（審查 R-05）**：`WorkOrchestrator` 對 `self._store.*`（`load_work_items`、
  `put_work_item`、`update_work_item`）一律在事件迴圈上**同步**呼叫——設計只要求 facade 呼叫走 `to_thread`，未涵蓋
  store，故不違反計畫，但風險要寫下：`load_work_items` 為冪等讀取，連線錯誤時 `RedisGateway` 以 `time.sleep` 退避重試
  （最壞約 3.3 秒，`redis_gateway.MAX_RETRIES`），Redis 抖動期間**同一進程的所有 WebSocket 連線**都會被阻塞。本站不改
  程式；是否把 store 呼叫包進 `asyncio.to_thread`（代價是替身測試的交錯不再可決定、需重驗 `NFR12.13` 的併發案）交由
  `U13`（實際的事件迴圈擁有者）或 `build-and-test`（可量測阻塞時間）決定。

## 審查修正（`reviews/review-01-unreceipted.md`，NOT-READY：Major 2、Minor 3）

審查有效、收據缺失（引擎因 `.hypothesis` 快取改變工作區指紋而拒收 `REVIEW_COMPLETED`；`project.md` 已記的同類死結）。
本站審查額度為 1，使用者裁決修好後完成本站。逐項：

| ID | 改了什麼 | 測試 |
|---|---|---|
| R-01（Major） | `_fail_item` 不再依失敗類別（timeout）取消本條執行鏈的 `_run`；新增參數 `cancel_run`（預設 False），**只有外部呼叫者**（`_recover` 的逾期掃描）傳 True，且取消移到推送、失敗訊息、推進等待者**全部完成之後** | 新增 `CancellationTest.test_cost_timeout_still_pushes_and_says_so`（`_Failed(timeout)` 後 work_items 推送為失敗、失敗訊息送達）、`test_persist_timeout_still_advances_the_waiter`（存檔逾時後等待者被推進為失敗並收到訊息；`_Failed(timeout)` 只出現在成本輪詢與存檔收尾，會有等待者的只有架構設計，故以存檔收尾驗證）；突變 M10 轉紅 |
| R-02（Major） | `RecordingSink` 每次 emit 先 `await asyncio.sleep(0)`，並加 `on_emit` 掛勾供測試注入交錯；`CostListApp` 的列估價表路徑也遵守 `hang`。流程 36 案在讓出版本下全綠 | 新增突變 M10（轉紅）、M10b（預期存活，見第三節）、M11；M1–M9 於讓出版本重跑全數轉紅；M3 因讓出而再次存活，已補強測試（第三節） |
| R-03（Minor） | `_run` 看門迴圈越過 deadline 時**先重讀**該項：已離開處理中（完成或失敗的寫入已成功）就不再設 deadline、不取消內層，等收尾自行結束 | 新增 `CancellationTest.test_watchdog_does_not_cut_off_completion_after_the_deadline`（架構檢視在送完成訊息時時鐘越過舊 deadline，訊息仍送達、狀態完成）；突變 M11 轉紅 |
| R-04（Minor） | `test_logger_name` 對 `work_orchestrator.py` 無條件斷言 `logger = logging.getLogger("cloud360.work_orchestrator")`，另兩個模組若出現 `getLogger(` 也須同名；`_emit` 的往返重驗加註解：只確認實例未被改動，**不是**額外的契約防線 | `ImportBoundaryTest.test_logger_name` |
| R-05（Minor） | 只揭露（第五節最末一條），不改程式 | — |

修正後重跑：本單元 88 OK、兄弟測試 110 OK、`tests.test_redis_gateway_noscript` 3 OK；突變 M1–M11 全數套用並還原，以
`cmp` 確認四個原始碼檔與修正版完全相同、無殘留。跑完後刪除 `backend/.hypothesis/` 下 mtime 為 2026-10-12 的 25 個快取檔
（與 2 個本日新建的空目錄），既有的 223 個檔未動。

## 六、開放項

| # | 事項 | 承接 |
|---|---|---|
| `OPEN-WO12-6` | `AC10.2.4` 的可觀察結果不存在（C1 讀取端點不寫稽核） | 使用者裁決（traceability 維持 Deferred） |
| `OPEN-WO12-7` | `AC1.3.2`／`AC5.1.3` 在停掉前提項時不字面成立；行為依 `BR53.4` 實作並有測試 | 使用者裁決（Deferred） |
| `OPEN-WO12-9` | functional-design 待回補三處文字：`BR56.7` 的 sideEffect 改引 `side_effect_on_stop`（`persisting` 為「可能已存回…」，不是 unknown）；第七節「三個純函式」應為四個；`BR58.1` 增「〈label〉沒有執行：前一項〈label〉已停掉」 | functional-design 下一次修訂（程式已依此實作） |
| F1 | `U10` 的 `is_noscript_error` 與 redis-py 8.x 不相容 | **已關閉**：本批已修（使用者 2026-10-12 裁決） |
| — | `configure_provider_env()` 併發耦合的測試 | 下一個觸及 `U11`／A1 的單元或 `build-and-test` |

## 七、交接給 `U13`（`OPEN-WO12-3`）

`U13 brain-gateway` 必須：

1. 握手時保留使用者 bearer token（只在記憶體），呼叫三個方法時以 `bearer_token=` 傳入；**不得**寫入任何持久層或 log。
2. 以 `WorkOrchestrator(app=websocket.app, session_store=…)` 建構（每進程一個實例）；本單元不 import `main`。
3. 呼叫 `dispatch` 時傳入 `utterance`（本輪原句）、`segment_id`（本輪訊息所屬的段）、`turn_id`（本輪 turnId）與 `sink`；
   **呼叫之前**依 `IntentDecision.intents[*].referent` 更新該段的作業對象——本單元只讀作業對象、不解析 `referent`。
4. 實作 `sink` 的三個方法（同步或 async 皆可）：`emit_session(WorkItemsPayload)`（turnId 為 null）、
   `emit_in_turn(turn_id, [TokenPayload…])`（本輪）、`emit_turn([TokenPayload|CostCardPayload…])`（產生新 turnId、依序送出、
   最後送 `done`）。收到的都是 `brain_ws_contract` 模型實例，由 `U13` 包成 `WsEnvelope`。
5. `dispatch` 回傳後送本輪的 `done`；`dispatch` 拋 `ValueError`（工作階段已到期或段不存在）時走既有的失效路徑。
6. 連線與重連時呼叫 `list_items`（它先做復原掃描，可能啟動等待項的背景執行，故需要 token 與 sink）。
7. 收到 `correct_work_item` 時呼叫 `correct`；`WorkItemNotFound` 對應 `INVALID_REQUEST`。
8. `CapabilityCallFailed` **不會**被拋出（能力失敗一律落成工作項的失敗狀態）。

## 八、Request Changes 修訂（2026-10-23）：合併前必修第 18 項的工作項那一半（計畫 §六 Step 13–17）

### 使用者裁決（逐字保存）

計畫核可流程覆寫了本站問題檔，裁決原文因此不在 `code-generation-questions.md` 內，保存於此：

> **[WO-MB18]** 同一個工作階段裡，工作項的筆數目前沒有上限……要怎麼處理？
>
> - **A. 限筆數＋完成後瘦身（Recommended）**
> - B. 只限總筆數 30 筆（最壞約 225 KB，承諾降到約 260 個工作階段）
> - C. 記為已接受風險、不改程式（repo 無告警管道）
>
> **[Answer]: A**（2026-10-23，以選單作答）

### 交付

| 檔案 | 變更 |
|---|---|
| `backend/services/work_orchestrator_rules.py` | 新常數 `MAX_ACTIVE_WORK_ITEMS = 5`、`MAX_TERMINAL_WORK_ITEMS = 20`（模組常數，非環境變數）；`PHRASES` 增 `capacity_exceeded`（「同時進行中的工作已達上限，這一項沒有開始」） |
| `backend/services/session_scripts/put_work_item.lua` | 增 `ARGV[3]`（進行中上限）、`ARGV[4]`（終態集合 JSON）；同一支腳本內 `HGETALL` 計算非終態筆數，已達上限回 `-1` 不寫入；key 不存在或欄位已存在仍回 `0`（欄位存在的判定在上限之前） |
| `backend/services/session_scripts/update_work_item.lua` | 增 `ARGV[5]`（已結束保留數）、`ARGV[6]`（終態集合）；補丁使該項**由非終態轉為終態**時，依 `(createdAt, 欄位名)` `HDEL` 最舊的**其他**終態項直到 ≤ 20；只刪終態項 |
| `backend/services/session_types.py` | `ref_put_work_item`／`ref_update_work_item` 同語意（新增引數與 ARGV 逐一對應） |
| `backend/services/session_store.py` | `put_work_item` 改回 `WorkItemPutResult`（`WRITTEN`／`REJECTED`／`CAPACITY_EXCEEDED`；`bool` 只在已寫入時為真，既有 `if not put_work_item(...)` 語意不變）；兩個方法把上限與終態集合經 `ARGV` 交給 Lua，正本取自 `work_orchestrator_rules`（Lua 不抄第二份） |
| `backend/services/work_orchestrator.py` | 新例外 `WorkCapacityExceeded`；`dispatch` 整批預檢；`_abandon_batch`（併發越線時本批已寫入項轉失敗）；`_cas` 對所有轉終態補丁帶 `requestText[:CHANGE_SUMMARY_MAX_CHARS]` |
| `backend/services/brain_gateway_rules.py`（跨單元 `U13`） | `error_for`：`WorkCapacityExceeded` → 既有 `INVALID_REQUEST`，`ERROR_MESSAGES["work_capacity"]`＝「目前進行中的工作已達 5 項，請等其中一項完成後再交辦。」；**不改 WS 契約**，經 `brain_gateway.py` 既有的 `_fail_turn_exc` 送出 |
| 測試替身與既有測試 | `tests/work_orchestrator_fakes.py`（替身改以 `*argv` 轉交、新增 `UPDATE_CAPACITY_ARGS`）；`test_work_orchestrator_flow.py`、`test_work_orchestrator_model.py` 兩處直接呼叫 `ref_update_work_item` 補上新引數 |
| 文件 | `DEPLOY.md`（容量表）、`LOCAL-DEV.md`、`deploy/.env.example`、`backend/.env.example`、`deploy/docker-compose.deploy.yml` 註解、`session_store.py` 的容量註解 |

### 與計畫文字的偏離（逐項揭露）

1. **剛轉終態的這一項不列入刪除候選。** 計畫寫「依 `createdAt` 刪除超出 20 筆的最舊終態欄位」。`createdAt` 是建立時間而非結束
   時間：一個執行很久的項可能比 20 筆已結束的項都舊，照字面它會在自己完成的那一刻就被刪掉，使用者在清單上永遠看不到結果。
   排除它之後候選仍至少 20 筆，終態總數照樣收斂到 ≤ 20，故「終態 ≤ 20」不受影響。有專屬測試
   （`test_the_item_that_just_ended_is_never_its_own_victim`）。
2. **Lua 多收一個 ARGV（終態集合）。** 計畫只點名上限值。終態集合若寫死在 Lua 內就是 `TERMINAL_STATUSES` 的第二份物化
   （`team.md`「單一真實來源」），故改由 `SessionStore` 從 `work_orchestrator_rules` 傳入。
3. **`requestText` 截斷的落點是 `_cas`，不是逐個呼叫點。** 所有轉終態（完成、失敗、停掉、復原掃描、等待者被跳過、併發收尾）都經
   `_cas`，放在這裡是唯一落點；計畫的「`WorkOrchestrator` 送出轉終態的補丁時一併帶」語意相同。
4. **`session_store` 匯入 `work_orchestrator_rules`。** `U10` 匯入 `U12` 的純函式層（零 I/O、只依賴 `intent_routing_types`）以取常數；
   `test_session_contract.py`（`NFR4.46` 的 import 禁令）仍綠。
5. **容量數字與計畫不同（已實測）。** 見下節。

### 容量重算（以程式量測最壞值，不沿用計畫估計）

以 `json.dumps(..., ensure_ascii=False, separators=(",", ":"))` 序列化一筆每個欄位都取最長可能值的工作項：`requestText` 2000 個中文字
（進行中）或 200 字（已結束）、圖名 200 字（`collab_router.MAX_DIAGRAM_TITLE_CHARS`，同時出現在 `targetDiagramTitle` 與
`sideEffect` 的「可能已存回架構圖〈…〉（變更紀錄未寫入）」）、`failureReason` 取最長句、識別碼取 int32 上限；欄位名 `wi:<uuid4>` 39 B。

| 項目 | 值 |
|---|---|
| 一筆進行中最壞 | 8023 B ＋ 39 B ＝ 8062 B ≈ 7.9 KiB |
| 一筆已結束最壞 | 2623 B ＋ 39 B ＝ 2662 B ≈ 2.6 KiB |
| 工作項最壞 | 5 × 8062 ＋ 20 × 2662 ＝ 40,310 ＋ 53,240 ＝ 93,550 B ≈ 91.4 KiB |
| 對話最壞 | 3 × 200 × 1024 ＝ 614,400 B ＝ 600 KiB |
| 合計／工作階段 | 707,950 B ≈ 691.4 KiB |
| 256 MiB × 80% ＝ 204.8 MiB ÷ 707,950 B | ≈ 303.3 個（承諾 ≥ 300 成立） |
| 300 個 | 212,385,000 B ≈ 202.5 MiB ≈ `maxmemory` 的 79.1% |

計畫估「工作項 80 KiB；300 個 ≈ 199 MiB ≈ 78%」，把其他欄位算成約 1.5 KB，沒算到 200 字圖名出現兩次。實測後承諾仍成立，但餘裕只剩約
1%（303 對 300）；計畫的「每工作階段可用約 99 KiB」（699 − 600）仍大於 91.4 KiB。已寫進 `DEPLOY.md`：調高任何上限前先重算該表。
不含 Redis 每個 hash 欄位的配置開銷（歷程那一列同樣不含）。

### 測試結果（`backend/.venv`、`PYTHONDONTWRITEBYTECODE=1`）

| 範圍 | 結果 |
|---|---|
| `tests.test_work_orchestrator_store`（新增 `WorkItemCapacityTest` 10 案＋`WorkItemCapacityPropertyTest` 1 條 `@given`） | 26 OK |
| 本單元 7 檔＋兄弟測試（`session_store_behaviour`／`session_types`／`session_contract`／`hierarchy_service`）＋`test_brain_gateway_rules`＋`test_brain_gateway_turn` | 295 OK（skipped 3） |
| `tests_redis.test_work_item_lua`（本機臨時 `redis-server` 8.8.0，`REDIS_URL=redis://localhost:6391/15`，跑完即關閉） | 7 OK（新增 2 案：容量的 put／修剪逐案與參考實作一致） |
| 全 backend `python -m unittest discover -s tests` | 1288 OK（skipped 3） |
| `backend/scripts/dump_openapi.py --check` | 一致（無漂移） |
| `scripts/validate_env_contract.py`、`scripts/validate_repo_contract.py` | 皆通過 |

新增案例：`test_work_orchestrator_flow.py` 的 `WorkCapacityFlowTest` 6 案（4＋2 整批拒絕且 Redis 無新欄位、3＋2 邊界照常建立、
終態不佔名額、併發越線同批已寫入項轉失敗、停掉後 `requestText` 為原句前 200 字而進行中項保留全文、逾時失敗同樣截斷）；
`test_brain_gateway_rules.py` 的 `WorkCapacityErrorTest`、`test_brain_gateway_turn.py` 的 `WorkCapacityTurnTest`（端到端經 WS 收到
`INVALID_REQUEST`＋固定句）。

### 突變驗證（套用 → 紅 → 還原 → 綠；還原後以 sha256 比對基線）

基線 sha256：`put_work_item.lua` `4672aed4…59f3`、`update_work_item.lua` `bace7e85…e5a`、`session_types.py` `853bc671…f0`、
`work_orchestrator.py` `dc958e36…615a`。每項還原後四檔 sha256 皆與基線相同，重跑轉綠。

| # | 突變 | 紅燈 |
|---|---|---|
| MB1a | 拿掉 Lua 上限檢查（`put_work_item.lua`） | `tests_redis`：`test_put_capacity_cases_match_the_reference`（sixth_active_rejected） |
| MB1b | 拿掉參考實作上限檢查 | store：sixth、terminal_not_counted、`@given`；flow：concurrent（4 紅） |
| MB2 | 拿掉 `dispatch` 預檢 | flow：`test_batch_over_the_limit_is_rejected_whole_and_writes_nothing` |
| MB3a | 拿掉 Lua 終態修剪 | `tests_redis`：`test_update_prune_cases_match_the_reference` 三個子案 |
| MB3b | 拿掉參考實作終態修剪 | store：prune、self_not_victim、tie、`@given`（4 紅） |
| MB4a | Lua 修剪對象改為所有工作項（含進行中） | `tests_redis`：prune_oldest 子案 |
| MB4b | 參考實作修剪對象改為所有工作項 | store：prune、`@given`（2 紅） |
| MB5 | 拿掉 `requestText` 截斷（`_cas`） | flow：truncated（停掉）、truncated（逾時）、concurrent（3 紅） |

**突變驗證抓到一個測試盲點並已補上**：第一次跑 MB3b／MB4b 時，`@given` 性質**沒有**轉紅——hypothesis 產生的短序列很少累積到
20 筆終態，性質形同只驗上限。已在性質測試開頭先放 18 筆終態，重跑後 MB3b、MB4b 的性質皆轉紅（上表為補強後結果）。
Lua 端（MB1a／MB3a／MB4a）**只有** `tests_redis` 會紅：CI 的替身跑的是參考實作，不跑 Lua。這與 §二 第 9 項的既有揭露同一件事——
`tests_redis` 不在 CI，Lua 與參考實作的一致性由本機 opt-in 執行承擔。

### 已知限制（如實記載）

- **被等待者被修剪時，等待者會被判為失敗。** 復原掃描找不到 `dependsOn` 指向的項時視為失敗（既有行為）。只有「被等待者已結束、
  等待者卻尚未被推進」（推進前行程中斷）且其後又累積 20 筆較新的已結束項時才會發生；結果是等待者以「前一項沒有完成」失敗，
  不會誤執行。未另加保護（加保護會使已結束項可超過 20 筆，破壞容量承諾）。
- **`requestText` 靜態加密**仍不在範圍（§二 第 15 項，併入上游 `OQ-3`）。

### 交接給 `U14`（工作清單 UI）

工作清單現在**只會顯示最近 20 筆已結束的工作項**（以建立時間由新到舊保留；某一筆結束的那一刻它本身不會被刪，之後若再累積更新的已結束項，它照建立時間排序可能被刪）。更舊的已結束項已從 Redis
刪除，`list_items` 不會再回傳它們，WS 推送的 `work_items` 亦同。`U14` 若要提示使用者「只保留最近 20 筆」，文字與位置由 `U14`
決定；本單元不改 WS 契約。交辦超過 5 筆進行中時，使用者會在本輪收到 `error`（`INVALID_REQUEST`）與固定句
「目前進行中的工作已達 5 項，請等其中一項完成後再交辦。」——`U14` 不需另做判斷。

### 其他

- 合併前必修清單 `construction/functional-design/merge-blockers.md` 第 18 列：已於原儲存格**附加** `work-orchestrator` 那一半的處置，
  原內容未刪。
- 本機臨時 Redis 以 `--save "" --appendonly no` 起在 scratchpad，跑完以 `shutdown nosave` 關閉。

## 重做（Code Generation 自頭重來，2026-10-25）

<!-- 寫入時間：2026-10-26T00:46:47Z -->

以既有實作逐步查驗已核可計畫，未修改任何程式碼。

- **計畫勾選**：16／17。未勾 Step 17（追溯文件更新）：review-01 R-01（每筆工作項的位元組上界）的修正落地於本摘要第八節寫成之後，第八節容量表與全套測試數因而過時，且 `source-manifest.json` 漏列 `backend/tests/test_work_orchestrator_capacity.py`。本段已更正數字、manifest 已補列該檔；`traceability.json` 未新增對應條目（該檔 8 個測試承接的需求識別字已由其他測試檔條目覆蓋，未逐一核對）。另注意該測試檔在 git 中仍為未追蹤，commit 時須一併加入。
- **第八節的更正數字**（以 `DEPLOY.md`、`LOCAL-DEV.md` 與兩份 `.env.example` 為準，與程式常數 `WORK_ITEM_ACTIVE_MAX_BYTES = 7_800`、`WORK_ITEM_TERMINAL_MAX_BYTES = 2_100` 一致）：對話 600 KiB ＋ 工作項 ≈ 79.1 KiB／工作階段，300 個工作階段 ≈ 199.0 MiB ≈ 77.7%。第八節的 91.4 KiB、303 個、79.1% 與 1288 個測試皆已過時。
- **測試**（`backend/`，快取導向 scratchpad）：
  - 全套 `unittest discover -s tests`：1319 OK（skipped=3，未設 `REDIS_URL` 的三案）。
  - 本單元 113 OK（authz 5、boundaries 6、capabilities 13、capacity 8、flow 42、model 1、rules 12、store 26）；`test_session_store_behaviour` 59 OK；閘道 `test_brain_gateway_rules`／`_turn` 61 OK。
  - 真 Redis（一次性本機 8.8.0，只綁 127.0.0.1，不存檔，用完 `shutdown nosave` 並刪目錄；未連任何共享服務）：`tests_redis.test_work_item_lua` 7 OK（含容量上限與終態修剪），Lua 與參考實作逐案一致。
  - `dump_openapi.py --check`、`validate_env_contract.py`、`validate_repo_contract.py`：皆通過。
  - 突變驗證未重跑，沿用第三節 M1–M11 與第八節 MB1a–MB5 的紀錄。
- **合併前必修第 18 項**：本單元那一半確認已修正且有測試（Lua 同腳本計數上限、終態修剪、`CAPACITY_EXCEEDED` 三態、`dispatch` 預檢與 `_abandon_batch`、終態 `requestText` 截斷、閘道對應 `INVALID_REQUEST`）。其他列不影響本單元。
- **PBT**：非 ADR-0006 點名模組，但純函式層有 `@given`（rules 8、store 4、capacity 5、flow 3）與一個 `RuleBasedStateMachine`。
- **ADR-0006 四面向**（本摘要先前無逐項表，以下為本輪逐面查證）：IAM 成立（能力呼叫帶使用者 token 經既有授權 dependency，authz 5 案雙向）；network exposure 成立（無新端點、`openapi.json` 未變）；encryption 為已揭露缺口（`requestText` 在 Redis 為明文，併入上游 `OQ-3`）；audit logging 部分成立（存回成功寫變更紀錄；重啟後 `persisting` 孤兒無法補寫、`AC10.2.4` Deferred 為 `OPEN-WO12-6`；token 與原句不入 log 有測試）。
- **grep 判準**：禁止 import 清單 0 筆；`asyncio.wait_for` 只在 docstring；logger 僅 `"cloud360.work_orchestrator"` 一處；log 帶 token／requestText／utterance 0 筆；rules 模組只 import 兩個型別模組。
- **與計畫字面不同處**：Step 15 的固定訊息措辭依 review-01 R-03 改為「同時進行中的工作最多 5 項，這次交辦會超過上限，請等其中一項完成後再交辦。」（已於第 18 列揭露）；`_cas` 結果未知時比對補丁全部欄位，比計畫更嚴。
