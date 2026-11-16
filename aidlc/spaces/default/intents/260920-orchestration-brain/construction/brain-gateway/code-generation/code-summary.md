# Code Summary — `U13 brain-gateway`

> 依 `code-generation-plan.md`（Testing Contract `sha256:1f0b6822…`，`test-after`、`standard`）Step 1–12 完成，撰寫於 2026-10-13T15:43Z（`date -u`）。
> 契約變更紀錄 `ADR-0020` 已於 Step 1 原樣移入 `inception/decisions/0020-brain-ws-contract-page-scope-fields.md`（Status 改 Accepted），草案檔已刪除。
> 帶入的 37 項（`../carried-review-items.md`）逐項落點見第四節；`AC8.1.1` 維持 Deferred（`OPEN-GW13-15`），**未新增任何 LLM 呼叫**。

## 一、交付檔案

### 新建

| 檔案 | 交付 # | 內容 |
|---|---|---|
| `inception/decisions/0020-brain-ws-contract-page-scope-fields.md` | 1 | 由草案原樣移入；只改標題「（草案）」與 Status 行 |
| `backend/services/brain_gateway_rules.py` | 3 | 純函式與純狀態機：`parse_subprotocol_offer`、`session_key_for`／`user_id_from_session_key`、`resolve_segment`、`TurnLedger`、`error_for`、`match_referent`、`scan_targets_in_utterance`、`is_transient_memory_failure`、`BreakerState`、`RateLimiter`、`hello_version`；協定名與 bearer 前綴**由契約模型的字面型別取值** |
| `backend/services/brain_gateway.py` | 4 | `/api/brain/ws` handler、`ConnectionRegistry`（全域／每 key 佔位＋登錄）、`Connection`（送出序列化、失敗即 1011）、`GatewaySink`、`MemoryPrefetchAdapter`（`ContextVar`，無 I/O）、`MemoryWorker`（實例層級執行器＋`BoundedSemaphore`＋熔斷）、`GatewayTiming`、`build_brain_gateway` |
| `backend/tests/brain_gateway_fakes.py` | 10 | 共用替身與組裝（非測試模組）：可跨執行緒推進的 `FakeTiming`、`FakeRouter`、`FakeOrchestrator`（工作項寫進同一個 Redis 替身）、`FakeHierarchy`、`FakeMemory`、`Harness`（含 `rebuild()` 模擬重啟）；`recv_json` 對每則送出訊息做 `WsEnvelope.model_validate`（`NFR13.40`） |
| `backend/tests/test_brain_gateway_rules.py` | 10 | 19 案（五個 PBT 性質 ＋ 熔斷／限流的狀態性質 ＋ example） |
| `backend/tests/test_brain_gateway_handshake.py` | 10 | 12 案 |
| `backend/tests/test_brain_gateway_turn.py` | 10 | 18 案 |
| `backend/tests/test_brain_gateway_fanout.py` | 10 | 8 案 |
| `backend/tests/test_brain_gateway_memory.py` | 10 | 12 案 |
| `backend/tests/test_brain_gateway_limits.py` | 10 | 12 案（含 AST 結構禁令 4 案） |
| `backend/tests/test_brain_gateway_startup.py` | 10 | 5 案 |

### 修改

| 檔案 | 單元 | 內容 |
|---|---|---|
| `backend/services/brain_ws_contract.py` | `U2` | C-1～C-7 七個必填欄位（皆有 `description`）；模組 docstring 與 `WsSubprotocol` docstring 的握手形狀同步 |
| `backend/scripts/dump_ws_contract.py` | `U2` | `CLIENT_FIELD_WHITELIST` 三列：`UserMessagePayload` ＋`page`、`SetSharingModePayload` ＋`scope`、`SetWorkTargetPayload` ＋`segment` |
| `ws-contract.json`、`frontend/src/types/ws-contract.d.ts` | `U2` | 重產（`python3 scripts/dump_ws_contract.py`、`npm run gen:ws-types`） |
| `backend/tests/test_ws_contract.py` | `U2` | §十一之二第 5 點的五處（`CLARIFY`＋`kind`、`SHARING_MODE`＋`scope`、`WORK_TARGET`＋`segment`、`WsSubprotocol` 三處補 `protocolName`）＋`protocolName` 錯值與缺欄位負向案例；新增 `Adr0020FieldIncrementTest` 2 案（七欄各自的全部合法值、錯值、缺欄位、必填、有 description） |
| `backend/main.py` | — | 移除 `brain_router` import 與 DEMO 三行；startup hook 在 `configure_intent_routing_env()` 之後、`init_db()` 之前 `app.state.brain_gateway = build_brain_gateway(app)`；新增 shutdown hook；以 `prefix="/api/brain"` 掛閘道 router |
| `backend/services/intent_routing_types.py` | `U11` | 只改註解（`ROUTABLE_CAPABILITIES` 不再有 DEMO 副本） |
| `backend/tests/test_intent_routing_structure.py` | `U11` | `:62` 改為兩個閘道模組路徑；`:315-345` 改為鎖住「正式閘道不得再長出能力 id 副本」（`team.md` 單一真實來源） |
| `backend/requirements.txt` | — | 明列 `websockets`（不 pin，附理由；帶入項 35） |
| `.github/workflows/deploy.yml` | — | 必要 secret 檢查加 `OPENROUTER_API_KEY`（不動 `render-env.sh`，回滾仍可執行；帶入項 30、32） |
| `deploy/.env.example` | — | `OPENROUTER_API_KEY=` 上方補說明（值仍為空） |
| `deploy/render-env.sh` | — | 只改檔頭註解（審查 R-07） |
| `DEPLOY.md` | — | `:24` 的 `OPENROUTER_API_KEY` 列補「入口頁每一輪失敗」與「staging 部署必要」 |
| `LOCAL-DEV.md` | — | `infrastructure-specification.md` §6.3 的六處：功能表加入口頁列、`:23` Redis 列改為啟動必要條件、補「後端啟動本身（U13 起）」列、嵌入列補 `fulltext` 的 WARNING 揭露、`:79` 註解、疑難排解拆成兩列 |
| `frontend/src/App.tsx`、`frontend/src/components/Sidebar.tsx` | `U14` 前身 | 移除 DEMO 的 `/brain` 路由、import 與 Sidebar「大腦（示範）」區塊 |
| `frontend/eslint.config.js` | — | 只改註解：正確寫法改為帶 `protocolName`，指向 `U14` |
| `frontend/tests/e2e/member-pages.spec.ts` | `U24` | 8 處 `/brain` 落地頁改為 `NEUTRAL_LANDING = '/memory'`（`setupApp` 一併以空清單攔截 `/api/memory/**`）；3 處 `@ui` 同步 |
| `frontend/tests/e2e/memory-page.spec.ts` | `U15` | 2 處 `/brain`：第一案直接開 `/memory`；第二案改以 SPA 導覽（`history.pushState`＋`popstate` 到 `/403`、`goBack()` 回來）離開與回來 |

### 刪除

| 檔案 | 理由 |
|---|---|
| `backend/services/brain_router.py` | DEMO 閘道（`[IG2]`=A；會把 token 回送進回應標頭） |
| `frontend/src/pages/BrainPage.tsx` | DEMO 前端（只帶 bearer 一個子協定、`user_message` 缺 `page`，`tsc -b` 與握手皆不相容） |

**零新環境變數、零新服務、零新監聽埠、零 DDL**（不觸發 `schema_rbac.sql`／`DEPLOY.md` 的 schema 同步規則）。既有 5 個 SSE 端點的五支 router（`agent_router`、`review_router`、`lens_router`、`collab_router`、`advice_stream_router`）`git diff --stat` 為 0 行（`AC8.1.4`、`BR67.9`）。

## 二、各步驟的測試指令與結果

全部在 `backend/` 以 `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest …` 執行（本機 Python 3.13.7、starlette 0.37.2、hypothesis 6.165.2）。

| Step | 指令（限定本單元） | 結果 |
|---|---|---|
| 1 | ADR 移入；兩個模組檔建立 | — |
| 2 | `tests.test_ws_contract tests.test_session_store_behaviour` | 修改前 51 案 OK；`TestClient.websocket_connect` 可用 |
| 3–4 | `python3 scripts/dump_ws_contract.py` → `--check`；`npm run gen:ws-types` → `npm run check:ws-types`；`tests.test_ws_contract tests.test_dump_ws_contract`；`tests.test_brain_gateway_rules` | 兩道閘門綠；15 案 OK；19 案 OK |
| 5–6 | `tests.test_brain_gateway_handshake tests.test_brain_gateway_turn tests.test_brain_gateway_fanout tests.test_brain_gateway_memory tests.test_brain_gateway_limits` | 12＋18＋8＋12＋12＝62 案 OK |
| 7–8 | `tests.test_brain_gateway_startup tests.test_intent_routing_structure`；`python3 scripts/dump_openapi.py --check` | 5 案 OK（**本機未裝 redis-py 時 1 案 skip**；以 `pip install --target <scratch> redis` 加入 `PYTHONPATH` 後 5 案全過、0 skip）；20 案 OK；OpenAPI 未漂移（WebSocket 路由不入 OpenAPI） |
| 9 | `frontend/`：`npm run lint`、`npx tsc -b`；兩支改過的 e2e 以 `tsc --noEmit --strict` 單獨型別檢查 | lint 0 errors（2 個既存 `exhaustive-deps` warning）；`tsc -b` 綠；e2e 型別檢查綠。**e2e 本身由 CI `ui-regression` 執行，本機未跑** |
| 10 | `scratchpad/mutate.py`（不進 repo）：每項「套用 → 跑 → 還原 → 跑」 | 第三節 15 項皆「紅 → 綠」 |
| 11 | `python3 scripts/validate_env_contract.py`、`python3 scripts/validate_repo_contract.py` | 皆 passed |
| 12（初版） | 本單元全部 8 支：`tests.test_ws_contract tests.test_brain_gateway_rules tests.test_brain_gateway_handshake tests.test_brain_gateway_turn tests.test_brain_gateway_fanout tests.test_brain_gateway_memory tests.test_brain_gateway_limits tests.test_brain_gateway_startup` | 95 案 OK（審查修正後為 103 案，見第十二節） |
| 受影響的既有測試 | `tests.test_dump_ws_contract tests.test_intent_routing_structure tests.test_work_orchestrator_flow tests.test_session_store_behaviour` | 106 案 OK |
| 全套 | `python3 -B -m unittest discover -s tests` | 見第九節（4 個失敗皆來自工作樹內被 git 忽略的 `.kilo/worktrees/secret-deposit/` 他人副本，與本單元無關） |

**一次修正的缺陷（實作中自行查出）**：`MemoryWorker` 若沿用設計虛擬碼的 `run_in_executor`，等待上限在工作**尚未開始**前就到時，執行器的 future 會被成功取消、工作函式永遠不跑，號誌永久少一格——第一版的「佔滿位子」測試因此卡死而查出。改為 `executor.submit` ＋ `asyncio.wrap_future` ＋「被取消即歸還」的 done callback（已開始的工作取消不了，仍由工作函式的 `finally` 歸還，恰一次），並新增 `test_slot_is_returned_when_wait_expires_before_job_starts`。

## 三、突變驗證（`HYPOTHESIS_NO_SHRINK=1`）

| # | 突變 | 對應帶入項／需求 | 跑的測試 | 突變後 | 還原後 |
|---|---|---|---|---|---|
| M1 | 句中掃描改回子字串（`dominated = False`） | 1 | `ScanTargetsTest`（2 案）＋`test_scan_after_select_uses_longest_name_and_always_asks` | 紅（failures=2） | 綠 |
| M2 | 全域佔位移到 accept 之後 | 7 | `test_concurrent_handshakes_cannot_exceed_global_limit` | 紅 | 綠 |
| M3 | 熔斷只看頂層例外、不走例外鏈 | 8 | `test_breaker_opens_on_wrapped_timeout_only_and_recovers` | 紅 | 綠 |
| M4 | `BUSY_SKIPPED` 出口不清 probing | 18（Critical） | `test_half_open_probe_skipped_when_busy_is_released_and_breaker_recovers` | 紅 | 綠 |
| M5 | `run` 以 `except BaseException` 吞取消 | 19 | `test_cancellation_is_reraised_and_probe_cleared` | 紅 | 綠 |
| M6 | 最後一條連線關閉時刪除頻率視窗 | 20 | `test_per_user_message_limit_spans_tabs_and_survives_reconnect` | 紅（errors=1） | 綠 |
| M7 | 送出失敗只取消登錄、不 close | 21 | `test_failed_send_unregisters_and_closes_1011_without_affecting_others` | 紅 | 綠 |
| M8 | 執行器改回類別層級共用 | 22 | `test_executors_are_per_instance` | 紅 | 綠 |
| M9 | 回送 `bearer.<jwt>` 子協定 | GW1／`NFR13.7` | `test_accepts_with_protocol_name_only_and_never_echoes_token` | 紅 | 綠 |
| M10 | 握手 `record=False` | `AC8.1.2` | `test_handshake_records_last_activity` | 紅 | 綠 |
| X1 | 取空佇列與改 ready 之間插入 `await asyncio.sleep(0)` | 3／`NFR13.26` | `test_message_arriving_while_draining_is_delivered_once_and_last` | 紅 | 綠 |
| X2 | 等待逾時即歸還位子（非執行緒結束） | 15 | `test_busy_skip_does_not_open_breaker_and_timed_out_jobs_keep_their_slot` | 紅 | 綠 |
| X3 | `K1` 判定恆真 | `NFR13.10` | `test_k1_allow_deny_and_disabled_account` | 紅 | 綠 |
| X4 | 被拒訊框不計入關閉門檻 | 29 | `test_oversized_frame_rejected_before_parsing_and_rejections_close_connection` | 紅 | 綠 |
| X5 | 背景重驗直呼 `asyncio.sleep` | 9 | `test_no_direct_clock_or_sleep_outside_gateway_timing` | 紅 | 綠 |
| — | 只改模型不重產 `ws-contract.json`（`page` 刪一值） | `NFR13.41` ④ | `python3 scripts/dump_ws_contract.py --check` | 紅（exit 1） | 綠 |

`unit-test-instructions.md §四` 的 10 項（M1–M10）全數完成；X1–X5 與最後一列為加做。

## 四、計畫 §二（帶入 37 項）逐項落點

| # | 處置 | 程式落點 | 驗證 |
|---|---|---|---|
| 1 | 最長完整名稱；被較長名稱完全覆蓋者剔除；掃描命中一律 `clarify(kind="target")` | `brain_gateway_rules.scan_targets_in_utterance`；`BrainGateway._resolve_and_dispatch`（`scan=True`） | rules 性質五 (a)(b)(c)、turn `test_scan_after_select…`、`test_generic_single_hit_still_asks…`；M1 |
| 2 | 性質五可失敗版本；系統命中吸收所屬專案（`match_referent` 與掃描共用 `_absorb_projects`） | `_absorb_projects`、`match_referent` | rules `test_project_and_its_own_same_named_system_are_one_target`、性質五 (b) |
| 3 | 取空與改 ready 在同一個無 `await` 區段 | `_handshake_and_serve` 的 drain 迴圈 | fanout `test_message_arriving_while_draining…`；X1 |
| 4 | 專案 > 50 且句中確實指名、零筆相符 → 「專案太多，請先在脈絡列選定專案」 | `_resolve_and_dispatch`；`TOO_MANY_PROJECTS_MESSAGE` | turn `test_more_than_fifty_projects` |
| 5 | 熔斷全域鍵、只認暫時性；執行器滿即跳過 | `is_transient_memory_failure`、`BreakerState`、`MemoryWorker.run` | memory 3 案、rules 2 案 |
| 6 | `LOCAL-DEV.md` 同步 | 見第一節 | 「session 相關功能不可用」0 次、含 `REDIS_USER=default` 2 次（`grep -c`） |
| 7 | 全域佔位在 handler 第一個敘述、每 key 佔位在認證後 accept 前、`finally` 釋放；併發 N+1 | `BrainGateway.handle` | handshake 併發案與每 key 案；M2 |
| 8 | 熔斷認 `EmbeddingProviderUnavailable` 包住的 httpx 逾時／連線類；寫入等待 `EMBEDDING_TIMEOUT_SEC + 5` | `is_transient_memory_failure`；`EPISODIC_WAIT_SEC` | memory 熔斷案、`OllamaChainContractTest`；M3 |
| 9 | `GatewayTiming` 建構子注入；AST 禁直呼 | `GatewayTiming` | limits `test_no_direct_clock_or_sleep_outside_gateway_timing`；X5 |
| 10 | `U14` 退避重試至少 60 秒、4401 重取 token | 第七節交接表 | — |
| 11 | 不同專案同名對象區間相同、互不支配 | `scan_targets_in_utterance` 第 3 步 | rules example 第三案 |
| 12 | 取代關係表 | 第五節 | — |
| 13 | 未指名對象且已有作業對象時照常交辦 | `_resolve_and_dispatch`（referent 皆為 null） | turn `test_more_than_fifty_projects` 第三步 |
| 14 | 三段預算各自獨立、不相加；`NFR13.1` 量測落 `build-and-test` | `turn_end` log 的分段欄位 | turn `test_turn_end_log_attributes_time_to_each_segment` |
| 15 | 號誌於工作執行緒 `finally` 歸還，計實際佔用 | `MemoryWorker.run` | memory `test_busy_skip…`；X2 |
| 16 | 單行程守門：Dockerfile／兩份 compose／範本與 `render-env.sh` 不含 `WEB_CONCURRENCY`／`UVICORN_WORKERS`，compose 無 `command`、無 `env_file` | 測試 | startup `test_dockerfile_compose_and_templates_keep_a_single_worker` |
| 17 | `[GWND1]`=A：第 11 條拒絕、`U14` 退避至少 60 秒 | `ConnectionRegistry.try_reserve_key`；第七節 | handshake 每 key 案 |
| 18 | 半開試探在任何未執行出口清除 probing（含 `BUSY_SKIPPED`、submit 失敗、取消） | `MemoryWorker.run` | rules 熔斷活性 PBT、memory 半開案；M4 |
| 19 | `CancelledError` 一律重拋 | `MemoryWorker.run` | memory 取消案；M5 |
| 20 | 頻率窗以使用者為鍵、時間到才清；握手納入限流 | `RateLimiter`（`admit_handshake`、`sweep`）；`handle` | limits 重連案、handshake 握手頻率案；M6 |
| 21 | 送出失敗或逾時：取消登錄並主動 `close(1011)` | `Connection._on_send_failure` | fanout 送出失敗案；M7 |
| 22 | 執行器與號誌為實例屬性 | `MemoryWorker.__init__` | memory 兩實例案；M8 |
| 23 | 「待裁決」殘字 → `[GWND1]`=A；60 秒退避列為 `U14` 義務 | 第七節 | — |
| 24 | 引用行號更正 `embedding_port.py:617-621` | 本檔與 `brain_gateway_rules.py` docstring | — |
| 25 | `send_direct` 不用 AST 規則禁止的變數名 | 送出路徑變數名為 `frame_json`；AST 禁 `Name` 為 `text`、禁自 `sqlalchemy` 匯入 `text`（偏離 D9） | limits `test_forbidden_imports_names_and_hand_built_messages` |
| 26 | 揭露 `U12` 事件迴圈上的同步 Redis 與共用預設執行緒池 | 第八節 | — |
| 27 | episodic 跳過以 WARNING 計數 | `MemoryWorker._note_busy`（第 1 次與每 100 次一筆 WARNING，含累計） | — |
| 28 | 專案 > 50、掃描零命中不得靜默交辦舊對象 | `_resolve_and_dispatch`（`scan=True`）；偏離 D6 | — |
| 29 | 被拒訊框計入關閉門檻 | `BrainGateway._reject`；`REJECTED_FRAMES_CLOSE_THRESHOLD = 20` | limits 過大訊框案；X4 |
| 30 | `OPENROUTER_API_KEY` 進 `deploy.yml` 必要檢查 | `deploy.yml` | 第六節的合併前確認 |
| 31 | 第一次進 `ut` 時 DEMO 後端已移除 | 刪 `brain_router.py`、`main.py` 三行 | startup `test_exactly_one_brain_websocket_route_and_demo_is_gone` |
| 32 | 四份文件反映 IG1／IG2 | `deploy.yml`、`deploy/.env.example`、`DEPLOY.md:24`、`LOCAL-DEV.md` | `validate_env_contract.py` 綠 |
| 33 | DEMO 全部觸點同一 PR | 第一節「修改／刪除」 | repo（排除 `aidlc/`）內 `brain_router`／`BrainPage` 只剩兩處註解與兩支測試的「已刪除」斷言 |
| 34 | 合併前確認 secret | **由使用者執行**（第六節） | — |
| 35 | `requirements.txt` 明列 `websockets` | `requirements.txt` | — |
| 36 | L2 回退改寫 | 第六節 | — |
| 37 | token 不經 argv、輸出遮罩 | 第六節 | — |

## 五、偏離與取代關係

### 5.1 取代關係表（上游已核可文字被本單元實作改寫之處）

| 上游 | 本單元 | 性質 | 依據 |
|---|---|---|---|
| `BR64.13`「以 casefold 判定子字串」「同一專案下系統命中時專案名不另計」 | 最長完整名稱（區間支配）；系統命中吸收所屬專案（不論同名與否）；**命中一律以對象反問確認** | 取代 | `NFR13.27`／`NFR13.28`；帶入項 1、2、11 |
| `BR64.9` 第 2 步把「專案與其自己的系統同名」算成兩筆 | 吸收為一筆（該系統） | 取代 | `NFR13.28`；帶入項 2 |
| `NFR13.27`（掃描命中一律反問）與 `BR64.9`（高信心唯一相符即更新） | **兩者處置不同，刻意保留**：高信心路徑的 referent 是 `U11` 與意圖一併判讀的語意指涉；掃描是對原句的字面啟發式，證據強度較低，故需使用者確認 | 一致性說明 | 帶入項 1、12 |
| `BR67.12`「任一次預取或寫入逾時或拋例外 → 開啟」 | 只認暫時性（逾時、連線類，含例外鏈） | 收窄 | `NFR13.25`；帶入項 5、8 |
| `BR67.12` episodic 等待 15 秒 | `EMBEDDING_TIMEOUT_SEC + 5.0`（預設仍 15） | 推廣 | 帶入項 8 |
| `BR67.12` 執行器（設計虛擬碼為類別屬性、以 `wait_for` 逾時計數） | 實例屬性＋`BoundedSemaphore`，以執行緒實際結束計數；未開始即取消也歸還 | 取代 | 帶入項 15、22；第二節的自查缺陷 |
| `BR64.11` (b)「找不到名為…」 | 目錄被截斷（專案 > 50）時改回「專案太多，請先在脈絡列選定專案」 | 取代 | `NFR13.21`；帶入項 4、13 |
| `reliability-design.md` §7.5 末列（截斷、掃描零命中 → 依當前作業對象交辦） | 未選定專案時回「專案太多…」；已選定專案時照常交辦（偏離 D6） | 取代 | 帶入項 28 |
| `NFR13.5`「執行器滿 → 記 WARNING 計數」與 `observability-design.md` §三 `memory_busy` 為 INFO | WARNING，第 1 次與每 100 次一筆（含累計值），不逐則記 | 統一 | 帶入項 27；`NFR13.37` |
| `NFR13.17` 計數對象「登錄連線數」 | 佔位數（含正在認證的握手） | 擴大 | 帶入項 7；`logical-components.md` §六 |
| `NFR13.1` 預算表的加總算式 | 三段各自獨立的 P50 預算，不主張相加；本單元無法判定是否達成，量測落 `build-and-test` | 表述更正 | 帶入項 14 |
| `tech-stack-decisions.md`「該 key 的最後一條連線移出登錄時刪除 key 的 deque」 | 不刪；修剪後為空才移除，視窗生命週期由時間決定；另加握手頻率窗 | 取代 | 帶入項 20 |
| `NFR13.20`「超過 → error，連線保留」 | 同左，另加「視窗內被拒達 20 次 → 1011 關閉」 | 補強 | 帶入項 29 |
| `NFR13.39`「`requirements.txt` 無新增依賴行」 | 新增一行 `websockets`（既有的傳遞依賴明列，非新套件） | 取代 | 帶入項 35；計畫交付 #9 |
| `cicd-pipeline.md`「不改 `ci.yml` 與 `deploy.yml`」 | `deploy.yml` 必要 secret 檢查加一項 | 取代 | `[IG1]`=A；帶入項 30、32 |
| `functional-spec.md` GW-W7「不新增環境變數，故無 `LOCAL-DEV.md` 同步義務」 | 必須同步（Redis 由降級依賴變成啟動必要條件） | 取代 | `NFR13.43`；帶入項 6 |
| `infrastructure-specification.md` 4.5 的 L2 回退 `proxy_set_header Sec-WebSocket-Protocol …` | 刪除（nginx 預設即轉送，該指令為 no-op），改寫為第六節的實際處置 | 取代 | 帶入項 36 |
| `deploy/render-env.sh:21` 檔頭「`OPENROUTER_API_KEY` optional」 | 改為「staging 部署必要，由 `deploy.yml` 強制；本腳本接受空值只為讓 rollback 可 render」 | 同步 | 審查 R-07；帶入項 30 |
| `reliability-design.md` §7.2「`find` 迴圈為 O(條目數 × 原句長)，不需更巧的結構」 | 區間剔除改為排序後單趟掃描（O(S log S)），句長上界沿用 4000 字 | 取代 | 審查 R-01 |
| `NFR13.19` 的訊框上限只在接收迴圈 | hello 也套用（超過即 4400）並計入每連線頻率窗 | 補強 | 審查 R-04 |
| `scalability-design.md` §四「扇出採依序而非 `gather`」 | 連線之間並行、同一連線依序 | 取代 | 審查 R-05 |
| `security-design.md` §六檢查 2「禁 `Name`／`Attribute` 為 `text`」 | 禁 `Name` 為 `text` 與自 `sqlalchemy` 匯入 `text`；**允許**屬性 `.text`（契約欄位 `TokenPayload.text`／`UserMessagePayload.text`） | 收窄 | 帶入項 25（審查 R-08 的第一個選項） |

### 5.2 偏離（對計畫或設計文字；皆為最貼近計畫的可行做法）

| # | 偏離 | 理由 |
|---|---|---|
| D1 | `RateLimiter` 放在 `brain_gateway_rules.py`（`logical-components.md` 寫在 `brain_gateway.py`） | 它是純資料結構（`now` 由參數傳入），放在純函式模組才能不匯入 FastAPI 就跑 PBT |
| D2 | 握手頻率上限 **30 次／60 秒／session key**，在**認證之後**、accept 之前判定 | 帶入項 20 要求「握手納入限流」但未給數值；key 由 user id 推導，認證前無法以使用者為鍵。**殘留**：認證本身的 DB 成本在認證前不受限（全域佔位 200 為唯一上界），以來源 IP 限流屬部署層，列為開放項 |
| D3 | 被拒訊框門檻 20 次／60 秒，關閉碼用既有的 **1011** | 審查 R-12 建議 1008 或 1011；1008 是新關閉碼＝契約增量（須擴大 `ADR-0020`），故用 1011 |
| D4 | `MemoryWorker` 改用 `executor.submit`＋`wrap_future`＋done callback | 第二節：設計虛擬碼的 `run_in_executor` 會在「未開始即取消」時洩漏位子 |
| D5 | `PREFETCH_WAIT_SEC` **維持 3.0（暫定）**，未依公式改值 | 見第十節：本機無 Ollama、未裝 fastembed，只能量 `stub`；公式套在 `stub` 得 0.5 秒，但 `stub` 是行程內雜湊、不代表任何經網路的嵌入，採用它會讓部署端每次冷載都開熔斷。實測轉 `build-and-test` |
| D6 | 帶入項 28 的適用前提：截斷且掃描零命中時，**未選定專案**才回「專案太多」；**已選定專案**時照常交辦。**使用者 2026-10-14 核可**；已知殘留（審查 R-06）：此時若句中點名的是**其他專案**的系統，它因目錄截斷不在掃描範圍內，同樣交辦給目前選定的專案（高信心路徑在同一情境回「專案太多」，兩路徑不一致）。由 `test_selected_project_truncated_scan_without_hit_dispatches_current_target` 鎖住 | 已選定時目錄含該專案的系統且已被掃描；若一律回「專案太多…請先選定專案」，已照做的使用者將永遠無法經反問路徑交辦 |
| D7 | `TurnLedger` 方法名：`reopen()`（設計表為 `open()`）、另加 `fail()`；`finish()` 在終態回 `None` | 建構即為 open；`fail()` 是「失敗 → error」的轉移，設計狀態機有此邊而方法表未列 |
| D8 | 空白訊息回「訊息格式不正確」；超長回「訊息太長」 | `BR64.3` 只定 code（`INVALID_REQUEST`）未定句子；取封閉表既有兩句 |
| D9 | 見 5.1 最後一列 | — |
| D10 | `memory-page.spec.ts` 第二案改用 SPA 歷史導覽離開到 `/403` 再 `goBack()` | DEMO 頁移除後，無 story 權限的使用者沒有其他被 Layout 包覆的頁面可經 Sidebar 前往；仍保留「不重新載入頁面」這個案例的本意 |
| D11 | `functional-design/traceability.json` 的 `AC1.1.5` 註記**未回改** | 依計畫「不回改已凍結設計檔」，文字回補列在本檔第十一節 |
| D12 | `NFR13.24` 的六類「不寫」只有三類有直接斷言（攔截、`BR64.11` (b)(c)、零交辦的反問）；`error` 結束、推播輪次、熔斷開啟三類由程式結構保證（只在 `finish()=="done"` 且 `dispatched` 時才 spawn；`emit_turn` 不呼叫寫入；熔斷開啟時 `run` 回 `BREAKER_OPEN`） | 時間內優先完成 Critical／Major 的突變；列為 `build-and-test` 可補的案例 |
| D13 | `NFR13.21` ③（恰 50 個專案時 `list_systems` 50 次）未單獨成案 | 同上；邊界 51 已覆蓋 |

## 六、部署後實測清單（取代 `infrastructure-specification.md` 4.4／4.5 的對應段落）與合併前 secret 確認

### 6.1 合併前（**由使用者執行**，本計畫不自動執行；帶入項 34）

含 `OPENROUTER_API_KEY` 必要檢查的 `deploy.yml` 一旦進 `ut`，secret 未設即部署失敗並觸發整分支回滾。合併前請執行：

```bash
gh api repos/opendiamonds/cloud-360/actions/secrets   --jq '.secrets[].name'   | grep -x OPENROUTER_API_KEY   # 必須印出一行
gh api repos/opendiamonds/cloud-360/actions/variables --jq '.variables[].name' | grep -x OPENROUTER_API_KEY   # 必須沒有輸出
```

第二行若有輸出（曾誤存為 variable），依 `project.md` 規則：搬到 secret 不足以結案，**必須重新產生金鑰**。

### 6.2 部署後三層實測（維運者在 `192.168.10.10` 手動執行，不進任何 workflow）

1. **取 token 不經 argv、不進 shell history**：`read -rs BRAIN_PROBE_TOKEN && export BRAIN_PROBE_TOKEN`（`read` 是 shell 內建，不產生子行程；`-s` 不回顯）。做完 `unset BRAIN_PROBE_TOKEN`。
2. `probe.py` 沿用 4.4 的版本（只印訊息型別），但**送 hello 前先確認 `ws.subprotocol`**；`docker exec -i -e BRAIN_PROBE_TOKEN -e BRAIN_WS_URL=… cloud360-backend-1 python - < probe.py`——`-e NAME` 只帶名稱，值由環境傳入，不出現在 `docker exec` 的 argv。
3. 三層（L1 後端直連、L2 經 nginx、L3 經 tunnel）的通過條件不變：`negotiated: cloud360.brain.v1` 後 `got: ready`。
4. **標頭層補充檢查**（改寫：token 不經 curl 的 argv、輸出遮罩）：

```bash
umask 077; hdr="$(mktemp)"
printf 'Sec-WebSocket-Protocol: cloud360.brain.v1, bearer.%s\n' "$BRAIN_PROBE_TOKEN" > "$hdr"   # printf 為 shell 內建
curl -sS -o /dev/null -D - --http1.1 --max-time 5 \
  -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' \
  -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' -H @"$hdr" \
  https://cloud360.danniel.cc/api/brain/ws \
  | grep -iE '^(HTTP/|sec-websocket-protocol:)' | sed -E 's/bearer\.[^,[:space:]]*/bearer.[REDACTED]/Ig'
rm -f "$hdr"
```

預期：`HTTP/1.1 101` 與一行 `sec-websocket-protocol: cloud360.brain.v1`；遮罩後不應出現 `[REDACTED]`（出現即代表回應帶了 bearer 項——`NFR13.7` 在部署面失敗）。負向對照：`hdr` 改為只寫 `bearer.…` 一項 → `HTTP/1.1 403`。

5. **L2 失敗、L1 通過時的實際處置**（取代原文的 `proxy_set_header` 回退——nginx 預設即轉送全部請求標頭，該指令為 no-op）：
   - 以 `docker exec cloud360-frontend-1 nginx -T` 確認執行中的設定就是 repo 的 `frontend/nginx.conf`（映像可能是舊版）；
   - 在輸出中找會影響該路徑的三種東西：`proxy_hide_header Sec-WebSocket-Protocol`（回應方向被剝）、`proxy_pass_request_headers off` 或以固定值覆寫 `Sec-WebSocket-Protocol`（請求方向被剝）、另一個比 `location /api/` 更精確而攔走 `/api/brain/` 的 location；
   - 以上一步的 curl 對 L1（`http://127.0.0.1:8000`）與 L2（`http://frontend:80`，於 backend 容器內執行）各跑一次，比較遮罩後的兩行，定位是請求方向還是回應方向；
   - 修法是改 `frontend/nginx.conf` 的那一處並同一 PR 同步 `LOCAL-DEV.md`；協作 WS 走同一 location，須一併回歸。修好前以 revert PR 回滾。
6. 結果寫進 `build-and-test` 的產出；**未實測不得宣稱 `OPEN-GW13-6` 結案**。另一次性複核：`docker top cloud360-backend-1` 只見一個 uvicorn 行程（`NFR13.33` 的部署面）。

## 七、交接給 `U14 entry-page-ui`（`functional-spec.md` §十一之四的回補；帶入項 10、17、23）

| # | 義務 | 來源 | 不做會怎樣 |
|---|---|---|---|
| 1 | 建立連線時帶**兩個**子協定，且**以型別取值**：`Sub['protocolName']`、`Sub['scheme']`、`Sub['separator']`（`ADR-0019 §5` 的 lint 規則禁止字面量） | `ADR-0020` C-1 | 伺服器不 accept（真實環境 HTTP 403） |
| 2 | 每則 `user_message` 帶 `page`（`entry`／`workspace`／`assessment`） | C-2 | `error(INVALID_REQUEST)`；不得預設為 entry |
| 3 | 依 `sharing_mode.scope` 與 `work_target.segment` 過濾狀態訊息，只套用到對應的頁／段 | C-3／C-4 | 獨立對話的脈絡列顯示共享段的值 |
| 4 | `set_work_target` 帶 `segment`、`set_sharing_mode` 帶 `scope` | C-5／C-6 | `error(INVALID_REQUEST)` |
| 5 | 依 `clarify.kind` 呈現反問：`intent` 依候選的 label 與 capability；**`target` 只顯示 label**（capability 不表達意圖） | C-7 | 對象反問被誤畫成意圖選單 |
| 6 | **`kind=="target"` 的反問必須提供回絕操作**（送 `candidateId: null`）——原句掃描**單一命中也會反問**，只有一個候選 | `OPEN-GW13-17`；帶入項 1 | 使用者只能選唯一候選，無法說「不是這個」 |
| 7 | 收到 **4401** 時以重新登入或新 token 重連（JWT 8 小時到期、停用即 4401；閒置連線由背景重驗在 60 秒內關閉） | D-1；`BR62.6` | 停在已關閉的連線上 |
| 8 | 連線被拒（未 accept）或斷線時**以有上限的退避重試，且重試至少持續 60 秒**才放棄 | `[GWND1]`=A；帶入項 10、17 | 網路抖動後舊登錄約 40 秒才釋放，被擋的分頁永遠連不上；無退避則額滿時形成重試風暴 |
| 9 | 依 `ready.protocolVersion` 核對版本（`BR3.5`）；`error.message` 原樣顯示（已為封閉表的人話） | `U2` 的規則 3.5 | — |
| 10 | e2e 計畫須寫明：CI 測試 stack 的 `OPENROUTER_API_KEY` 為空，走到分類的每一輪都是 `error(INTERNAL_ERROR)`——**能斷言握手、ready、狀態訊息、攔截（在分類之前）與錯誤呈現，不能斷言交辦成功** | `cicd-pipeline.md` 第七節（C-d） | e2e 失敗後才發現 |
| 11a | 偏離 D6 的殘留（使用者 2026-10-14 核可）：專案 > 50、已選定專案、反問選定後的原句只點名**其他專案**的系統時，會交辦給目前選定的專案；呈現交辦結果時應讓使用者看得到作業對象 | 審查 R-06 | 使用者以為交辦給了句中點名的系統 |
| 11 | 部署順序：`U14` 與本單元同一次合併進 `ut`（B6）；本分支第一次進 `ut` 時 DEMO 已移除（本單元已刪），在 `U14` 落地前 `/brain` 無頁面 | `OPEN-GW13-10`；`[IG2]`=A | — |

## 八、揭露事項

| 事項 | 內容 |
|---|---|
| 替身的限制 | Redis 替身（`WorkItemFakeRedis`）證明不了真實原子性與真實網路逾時；`TestClient` 下「不 accept」為關閉碼 1000，真實 uvicorn 為 HTTP 403；嵌入替身拋實際例外型別但不經真 httpx 與 Ollama——Ollama 冷載時實際拋出哪一種 httpx 例外須在部署 stack 以 log 的例外類別名複核（兩種候選皆在暫時性清單內，結論不受影響）；測試 DB 為單一連線的 in-memory SQLite，併發握手案在認證內以鎖序列化 DB 存取（只序列化 DB，「三條同時進入認證」的斷言不受影響） |
| `U12` 事件迴圈上的同步 Redis（`OPEN-GW13-4`） | `WorkOrchestrator` 對 `SessionStore` 的呼叫是同步的且在事件迴圈上（替身亦同形）；Redis 不可用時單次最壞約 3.3 秒（`COMMAND_TIMEOUT_SECONDS=1.0` × 重試 2 次＋退避），期間整個行程的全部 WebSocket、協作廣播與 SSE 一起停。本單元不包裝（不改 `U12` 做不到），`NFR13.4` 的執行緒斷言因此排除 `U12` 替身的呼叫 |
| 共用預設執行緒池與撤權 | 認證、重驗、session 讀寫走 `asyncio.to_thread` 的預設池（`min(32, CPU+4)`），與全後端共用。Redis 故障期間每次 `load` 佔一條執行緒約 3.3 秒，60 秒背景重驗與新握手可能排在其後——**故障期間撤權外洩窗的「≤ 60 秒」不成立**，上界由頻率與連線上限間接給出 |
| Cloudflare 透傳未實測（`OPEN-GW13-6`） | 子協定標頭在 Cloudflare edge／`cloudflared` 兩跳的請求與回應方向是否透傳，只能部署後實測（第六節）；兩方向任一被剝即入口頁不可用，且沒有不改契約的修法 |
| `meta.userId` 無寫入端（`OPEN-GW13-3`） | `K-09` 沒有寫它的方法；本單元以 `user_id_from_session_key` 推導，全樹無讀取端 |
| `AC8.1.1` Deferred（`OPEN-GW13-15`） | 本輪沒有逐字的內容來源（`U12` 交辦當下只送一則固定句型）；傳輸層保留逐則送出的能力（`emit_in_turn` 每則一個訊框、收到即送，`NFR13.2` 已驗）。**未新增任何 LLM 呼叫**；待使用者二擇一 |
| 本機 `fulltext` 的 WARNING（`OPEN-GW13-18`） | 本機預設 `EMBEDDING_PROVIDER=fulltext` 下，每個有交辦的輪次都會記一筆 `episodic_write_failed`（`fulltext` 寫不了記憶；它不開熔斷） |
| 握手前的認證成本（D2） | 認證前無法以使用者為鍵限流；全域佔位 200 是唯一上界 |
| 載入期暫存佇列的最壞記憶體（`OPEN-GW13-19`） | 未量化；單則 `work_items` 大小由 `U12` 的工作項數決定 |
| `ADR-0006` 四面向 | **IAM**：accept 前認證＋`K1` 雙向（`NFR13.10`）、逐則與 60 秒重驗、身分只來自連線、只經 facade（AST）。**Encryption**：token 只在請求標頭、不回送、不進 URL；本單元無新的持久化落點。**Network exposure**：唯一新增的對外面；佔位 200／每人 10、訊框 64 KiB、頻率 20／120、握手頻率 30、被拒 20 次關閉；殘留見上。**Audit logging**：握手與每則訊息 `record=True`、背景重驗 `record=False`（`AC8.1.2`，M10 驗證）；log 白名單與無洩漏測試（`NFR13.15`） |

## 九、全套測試

`python3 -B -m unittest discover -s tests`（本機，2026-10-13 實跑）：**949 案，4 個失敗、1 個 skip**（skip 為本機未裝 redis-py 的那一案）。4 個失敗全部來自 `test_progress_channel_contract` 掃到工作樹內 `.kilo/worktrees/secret-deposit/backend/services/…`——該目錄是另一工具於 2026-10-11 建立的工作樹副本，`git status --ignored` 顯示為被忽略（`!! .kilo/`），CI 的乾淨 checkout 不會有它；與本單元的改動無關。

## 十、`NFR13.3` 預取等待上限的量測表（**暫定**）

| 嵌入提供者 | 樣本數 | 暖機 P50 | 暖機 P95 | 冷載首呼叫 | 公式 `min(3.0, max(0.5, round(P95×1.5, 1)))` | 選定值 |
|---|---|---|---|---|---|---|
| `stub`（`StubAdapter.embed`，行程內 SHA-256 展開） | 30（另 1 次冷載） | 0.304 ms | 0.322 ms | 0.376 ms | 0.5 秒 | **未採用**（D5） |
| `fastembed` | — | — | — | — | — | 本機未安裝 |
| `ollama`（部署） | — | — | — | — | — | 只在部署 stack 存在 |

**現值 3.0 秒為暫定**：`stub` 的數字只證明量測程序可跑，不代表任何經網路或模型推論的嵌入。Ollama 的暖機 P50／P95 與冷載首呼叫轉 `build-and-test` 在部署主機量測，依同一公式定值；冷載超過選定值時接受該輪不帶記憶（熔斷因此開 30 秒，`NFR13.25` ③ 已揭露的設計成本）。

## 十一、functional-design 的文字回補（不回改已凍結的設計檔）

| 位置 | 回補 |
|---|---|
| `functional-design/traceability.json` 的 `AC1.1.5` | 主情境的成立條件：「專案數 ≤ 50，或脈絡列已選定專案」（`NFR13.21`；帶入項 4） |
| `functional-spec.md` §十一之四 | 本檔第七節的第 6–8 列（回絕操作、4401 重取 token、退避至少 60 秒） |
| `functional-spec.md` GW-W7 | 「無 `LOCAL-DEV.md` 同步義務」不成立（第五節） |
| `functional-spec.md` GW-W3／`rules.md` `BR64.13` | 偏離 D6 已核可（2026-10-14）及其殘留（第七節 11a） |
| `rules.md` `BR67.12` 引用的 `embedding_port.py` 行號 | `raise … from exc` 在 `:617-621`（帶入項 24） |

## 十二、審查修正（`reviews/review-01.md`，NOT-READY：Major 1、Minor 6；修正完成於 2026-10-13T22:42Z，`date -u`）

| ID | 處置 | 程式落點 | 新增／改動的測試 | 突變 |
|---|---|---|---|---|
| R-01（Major） | 原句掃描的區間剔除改為**排序後單趟掃描線**（O(S log S)），不再兩兩比較；句長上界沿用既有的單則訊息上限（`SCAN_MAX_CHARS = DEFAULT_MESSAGE_MAX_CHARS` = 4000，不另立數值）。等價性推導寫在函式 docstring | `brain_gateway_rules.scan_targets_in_utterance` | rules `test_worst_case_input_is_bounded`（4000 個 a＋「aa」「aaa」「aaaa」，1 秒內且只命中最長者）、`test_only_the_first_scan_max_chars_are_scanned`；性質五 (a)(b)(c) 不變且仍綠 | R01：改回雙迴圈 → 紅（耗時 6.4 秒、上界案失敗）；還原 → 綠。M1（每個區間都不被支配＝子字串語意）依新寫法重做 → 紅（failures=3）→ 綠 |
| R-02 | 改 ready 前再檢查一次 `overflowed`（同步判斷，不破壞「取空與改 ready 之間無 await」） | `_handshake_and_serve` | fanout `test_overflow_during_snapshot_send_closes_1011`（送出 ready 時注入 257 則） | X6：拿掉該檢查 → 紅 → 綠 |
| R-03 | 握手快照與排空包最外層 `except Exception` → 移出登錄、1011；接收迴圈對單則處理包 `except Exception` → 封閉表 `error`、連線保留；log 只記例外類別名 | `_handshake_and_serve`、`_receive_loop` | handshake `test_unexpected_error_during_snapshot_closes_1011`、turn `test_unexpected_error_in_a_message_keeps_connection`（皆斷言 log 不含標記字串） | X8：接收迴圈的保護改為只捕 `ZeroDivisionError` → 紅 → 綠 |
| R-04 | hello 訊框套用 64 KiB 上限（超過即 4400 `received=invalid`）並計入每連線頻率窗 | `_handshake_and_serve` | handshake `test_oversized_hello_is_rejected`；limits `test_per_connection_frame_limit` 改為 hello ＋119 則（hello 計入第 1 個訊框） | — |
| R-05 | **擇「並行送出」**：`fanout_many` 對各連線以 `asyncio.gather` 並行、同一連線依序（`send_lock`）；只有一條連線時直接送、不建 task。`set_sharing_mode` 的兩則改為同一次扇出。理由：揭露加縮短逾時仍讓延遲隨卡住的分頁數線性成長，並行則每次扇出的上界固定為一個 `SEND_TIMEOUT_SEC`。**殘留（揭露）**：同一呼叫端**先後兩次**扇出時，第二次仍等第一次的 `gather` 完成——卡住的分頁對每次扇出最多拖慢 10 秒（不再乘以分頁數）；要完全消除需每連線的送出佇列，屬新設計 | `BrainGateway.fanout_many`、`GatewaySink.emit_turn`、`_on_set_sharing_mode` | fanout `test_slow_tab_does_not_delay_other_tabs`（扇出順序在前的分頁卡住，另一條 1 秒內收到兩則） | X7：改回逐連線依序 → 紅 → 綠 |
| R-06 | 使用者 2026-10-14 核可偏離 D6；殘留寫進第五節 D6、第七節 11a、第十一節 | — | turn `test_selected_project_truncated_scan_without_hit_dispatches_current_target` | — |
| R-07 | `deploy/render-env.sh` 檔頭改為與 `deploy.yml` 一致 | `deploy/render-env.sh:21-25`（只改註解；`bash -n` 通過） | `test_render_env_redis` 仍綠 | — |

**測試結果（2026-10-13T22:42Z 前後實跑）**：本單元 8 支 **103 案 OK**（rules 21、handshake 14、turn 20、fanout 10、memory 12、limits 12、startup 5、ws_contract 9；連跑 3 次皆綠；本機無 redis-py 時 skip 1，以暫存目錄的 redis-py 加入 `PYTHONPATH` 後 103 案全過、0 skip）。受影響的既有測試 `tests.test_dump_ws_contract tests.test_intent_routing_structure tests.test_work_orchestrator_flow tests.test_session_store_behaviour tests.test_render_env_redis` 115 案 OK。`validate_env_contract.py`、`validate_repo_contract.py` passed。

**突變全表重跑**：第三節的 15 項加 R01、X6、X7、X8 共 19 項，皆「紅 → 綠」；X7 第一版未抓到（卡住的分頁在扇出順序上排在後面，依序送出也不影響前者），已把卡住的改為順序在前的那條後重跑為紅。突變還原後以 `git diff` 確認兩個模組只含本節的修正。

## 十三、合併前必修第 2 項(a) 與第 19 項（計畫 §六 Step 13–17；完成於 2026-10-24T03:11Z，`date -u`）

### 13.1 BR2.8 錯誤 `turnId` 規則表（落地版）

本表**取代** functional-design `rules.md:144`（重驗其他例外「以新 turnId 送 error」）、`:302`（ready 後再收到 hello「以新 turnId 送出」）、`:382`（無 PendingClarify「新 turnId 送 error」）三處。已凍結的設計檔不回改，以本節為準。依據：契約 `ErrorPayload.turnId` 為「必填鍵、值可為 null」，且逐字要求伺服器不得為非輪次錯誤捏造 turnId（`brain_ws_contract.py:371-380`，契約層由 `brain-ws-contract` 完成，本單元未改契約）；`[GW-MB2]`=A（2026-10-24）。

| # | 錯誤來源（`brain_gateway.py`，本輪修改後的行號） | 代碼 | `turnId` | 測試 |
|---|---|---|---|---|
| T1 | 二進位訊框、訊框過大、頻率超限（`_reject` → `_send_single_error`） | `INVALID_REQUEST` | `null` | limits `NonTurnErrorTurnIdTest.test_rejected_frames_carry_null_turn_id`（三種各一次） |
| T2 | 每則重驗拋非認證例外（`_receive_loop`，`:1113`） | `INTERNAL_ERROR` | `null` | limits `NonTurnErrorTurnIdTest.test_revalidation_exception_carries_null_turn_id` |
| T3 | 信封驗證失敗，含反問等待中格式錯誤的選擇（`:1131`）；**不碰 `pending_clarify`** | `INVALID_REQUEST` | `null`，反問保留 | turn `ErrorTurnIdTest.test_malformed_select_while_clarifying_keeps_the_clarify` |
| T4 | ready 之後再收到 `hello`（`_dispatch_client_message`） | `INVALID_REQUEST` | `null` | handshake `VersionTest.test_second_hello_after_ready_is_a_non_turn_error` |
| T5 | `select_clarify_candidate` 時沒有待選反問（`_on_select`） | `INVALID_REQUEST` | `null` | turn `ErrorTurnIdTest.test_select_without_pending_clarify_has_null_turn_id` |
| T6 | 選擇格式正確但 id 不在候選內（`_on_select` → `_fail_turn_exc`，現行不變） | `INVALID_REQUEST` | 該輪 `T` | turn `ClarifyTest.test_none_stays_silent_and_a_foreign_id_is_invalid_request`（**新增**斷言 envelope 與 payload 的 turnId 等於 clarify 的 turnId；方法名未改） |
| T7 | `set_work_target`／`set_sharing_mode`／`correct_work_item` 失敗；`_error_for_request` 的 `turn is None` 分支 | 依 `error_for` | `null` | fanout `NonTurnRequestErrorTest` 三案（id 非十進位 → `INVALID_REQUEST`；`set_sharing_mode` 拋 `RuntimeError` → `INTERNAL_ERROR`；找不到工作項 → `INVALID_REQUEST`） |
| T8 | 輪內失敗、`EMPTY_RESPONSE`、`emit_turn` 推播（`_fail_turn`、`_end_turn`、`GatewaySink.emit_turn`） | 原規則 | 該輪 `T`（現行不變） | 既有案例 |
| T9 | `_dispatch_client_message` 拋未預期例外（`_on_unexpected`，`:1142`） | `INTERNAL_ERROR` | 開啟中且未終止的輪 → 該輪 `T` 並結束；否則 `null` | turn `ErrorTurnIdTest` 三案（見下） |

**實作要點**：

- `_send_single_error(conn, code, message)` 拿掉 `turn_id` 參數與 `_mint_turn_id()`，envelope 與 payload 的 `turnId` 皆為 `None`。呼叫點 13 處（`grep -c "_send_single_error(conn" services/brain_gateway.py` → 13，不含定義行）。
- `Connection.open_turn`（`:233`）：`_on_user_message` 建立 `Turn` 後設定（`:1276`）、`_on_select` 取出待選反問後設定（`:1562`）；`_receive_loop` 在每則訊息處理前清空、`finally` 再清空（`:1133`、`:1140`），故參照不跨訊息殘留。
- `_on_unexpected`：`open_turn` 存在且 `ledger.is_terminal` 為假 → `_fail_turn_exc`（帶 `T`）；若 `pending_clarify` 指向同一輪則一併清除，使之後的選擇走 T5 而不是接續一個已終止的輪。否則送 `null` 錯誤。
- `_mint_turn_id()` 呼叫點只剩 `BrainGateway._on_user_message` 與 `GatewaySink.emit_turn`，由 limits `StructuralTest.test_mint_turn_id_only_where_a_turn_really_opens`（AST，含別名式引用的計數）鎖住。
- log：非輪次錯誤原本就沒有 log 使用捏造編號，未新增欄位。
- 既有測試中**沒有**斷言非輪次錯誤帶非 null `turnId` 的案例（`grep -n "turnId" tests/test_brain_gateway_*.py` 逐一檢視），故無需改寫既有斷言；只在 T6 既有案例加強斷言。
- 新增共用斷言 `tests/brain_gateway_fakes.py::assert_non_turn_error`：`WsEnvelope.model_validate` ＋ envelope 與 payload 的 `turnId` 鍵存在且為 `None` ＋ 代碼。

**T9 的三案**：(1) `test_unexpected_exception_inside_a_turn_ends_that_turn`：交辦前的 `_resolve_and_dispatch` 拋 `RuntimeError` → 最後一則為 `error(INTERNAL_ERROR)`，turnId 非 null 且等於 classify 收到的 `turn_id`；之後 0.3 秒內無訊息；恢復後下一句以不同 turnId 正常 `done`。(2) `test_unexpected_exception_after_select_ends_the_clarified_turn`：選定反問候選後同一例外 → 以 clarify 的 turnId 結束；再送選擇 → T5 `null`。(3) `test_unexpected_exception_in_a_non_turn_request_is_null_and_keeps_the_clarify`：反問等待中 `set_sharing_mode` 拋未預期例外 → `null`，反問保留，之後選 c1 以原 turnId 交辦完成。

### 13.2 測試結果（2026-10-24 實跑；指令皆在 `backend/`）

| 指令 | 結果 |
|---|---|
| `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_ws_contract tests.test_brain_gateway_rules tests.test_brain_gateway_handshake tests.test_brain_gateway_turn tests.test_brain_gateway_fanout tests.test_brain_gateway_memory tests.test_brain_gateway_limits tests.test_brain_gateway_startup` | 修改前 129 案 OK（skip 1）；修改後 **141 案 OK（skip 1）**，新增 12 案（limits 3、handshake 1、fanout 3、turn 5） |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_dump_ws_contract tests.test_intent_routing_structure tests.test_work_orchestrator_flow tests.test_session_store_behaviour` | 127 案 OK（skip 3） |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests` | 1308 案，**28 失敗**（skip 4），全部在 `test_mcp_bridge_app`（10）、`test_mcp_bridge_e2e`（16，其中一案兩個 subTest）、`test_mcp_bridge_topology`（2）：`mcp_topology.assert_prerequisites` 逐字「mcp 版本為 1.29.0，本單元釘選 2.3.0。請在 backend/ 執行：pip install -r requirements.txt」——**本機環境未依 `requirements.txt` 安裝**，與本單元無關；本輪未安裝套件（計畫未指名），未在正確環境複驗 |
| `python3 scripts/dump_ws_contract.py --check` | 一致（exit 0） |
| `python3 scripts/dump_openapi.py --check` | 一致（exit 0） |
| `python3 scripts/validate_env_contract.py`（repo 根） | passed |
| `python3 scripts/validate_repo_contract.py`（repo 根） | passed |

### 13.3 突變（`HYPOTHESIS_NO_SHRINK=1`；套用 → 紅 → 還原 → sha256 對照 → 綠）

修改後基線：`shasum -a 256 services/brain_gateway.py` = `49748a714ad32a1194682aae90e3a2a6d79103a4aa1d11ba4af2d74e402c13b3`。每項還原後實測 sha256 與基線相同。突變執行的指令為上表第一列去掉 `tests.test_ws_contract`（124 案）。

| 突變 | 結果 |
|---|---|
| M1 `_send_single_error` 還原為 `tid = _mint_turn_id()`、envelope 與 payload 共用 | 紅：failures=11——T1、T2、T3、T4、T5、T7×3、T9 的兩個 null 分支案（after_select 的第二次選擇、non_turn_request）、結構測試 |
| M2 信封驗證失敗時 `conn.pending_clarify = None` | 紅：failures=1——`test_malformed_select_while_clarifying_keeps_the_clarify` |
| M3 `_on_unexpected` 一律送 `null`（條件前加 `False and`） | 紅：failures=2——T9 的 inside_a_turn、after_select |
| M4 `_on_set_work_target` 開頭加回 `_mint_turn_id()` | 紅：failures=1——`test_mint_turn_id_only_where_a_turn_really_opens` |
| M5（計畫外加做）拿掉每則訊息前後的 `open_turn = None` | 紅：failures=1——`test_unexpected_exception_in_a_non_turn_request_is_null_and_keeps_the_clarify` |

還原後同一指令 141 案 OK（skip 1）。

### 13.4 第 19 項查證（唯讀，只列名稱）

- `gh api repos/opendiamonds/cloud-360/actions/secrets --jq '[.total_count, (.secrets[].name)]'` → 13 個名稱，**含 `OPENROUTER_API_KEY`**。
- `gh api repos/opendiamonds/cloud-360/actions/variables --jq '[.total_count, (.variables[].name)]'` → 2 個名稱（`APP_ID`、`GH_AW_DEFAULT_MODEL_COPILOT`），**不含 `OPENROUTER_API_KEY`**。
- 結論：現況符合 `project.md ## Mandated`（在 secrets、不在 variables），第 19 項不構成合併前阻擋。**限制**：API 只能證明現況，無法證明它過去從未存為 variable；若使用者知道曾誤存，依同條規則仍須重新產生金鑰。未讀取任何值。

### 13.5 交接 `entry-page-ui`（第 2 項(b)，不在本單元範圍）

伺服器自本輪起對 T1–T5、T7 與 T9 的非輪內分支送 `turnId=null` 的 `error`。前端（`useBrainConnection.ts:173` 目前以 `?? ''` 讓型別成立）須把 `turnId=null` 的錯誤呈現為**不屬於任何輪次**：不得歸入任何輪次、不得以空字串當輪次鍵（第二則會覆寫第一則），也不得因它 `setAwaitingReply(false)`／`clearPending` 而解除另一個進行中輪次的等待；並附 e2e。帶 `turnId` 的 `error`（T6、T8、T9 輪內分支）仍是該輪的終止事件。

### 13.6 追溯與清單

- `traceability.json`：新增 reverse `CG-MB2A-ERROR-TURNID`、`CG-MB19-OPENROUTER-SECRET`；`NFR13.23`、`NFR13.40` 的 note 補記本輪案例。
- `source-manifest.json`：本輪動到的 6 個檔（`backend/services/brain_gateway.py`、`backend/tests/brain_gateway_fakes.py`、`backend/tests/test_brain_gateway_{limits,handshake,fanout,turn}.py`）皆已在清單內，未新增項目。
- `construction/functional-design/merge-blockers.md` 第 2、19 列的處置欄末尾已追加本輪結果。

## 重做（Code Generation 自頭重來，2026-10-25）

<!-- 寫入時間：2026-10-26T01:09:04Z -->

以既有實作逐步查驗已核可計畫，未修改任何程式碼。

- **計畫勾選**：17／17。
- **測試**（`backend/`，快取導向 scratchpad）：
  - 全套 `unittest discover -s tests`：1319 OK（skipped=3）。
  - 本單元 8 支共 143 OK、0 skip（ws_contract 17、rules 22、handshake 18、turn 39、fanout 13、memory 13、limits 15、startup 6）。§13.2 的 141 案（skip 1）與 §十二各檔數字已過時，部分增量來自其他單元加進同批檔案。
  - `dump_ws_contract.py --check`、`dump_openapi.py --check`、`validate_env_contract.py`、`validate_repo_contract.py`、前端 `check:ws-types`、`tsc -b --noEmit`：皆通過；`eslint .` 0 errors（2 個既存 `exhaustive-deps` warning）。e2e 依計畫由 CI `ui-regression` 執行，本輪未跑。
  - 突變抽驗 4 項（只在 scratchpad 副本，未寫回 repo）：第 18 項 `BUSY_SKIPPED` 不清 probe、§13 M1 捏造編號、M3 T9 一律 `null`、`terminal_sent` 判準改回 `ledger.is_terminal`——皆紅→還原→綠；其餘先前記載的突變未逐一重跑。
- **合併前必修第 19 項**：`deploy.yml` 必要 secret 檢查含 `OPENROUTER_API_KEY`，`render-env.sh`、`DEPLOY.md`、`deploy/.env.example`、`LOCAL-DEV.md` 已同步。本輪唯讀列名：secrets 含 `OPENROUTER_API_KEY`，variables 不含（API 只證明現況）。**缺口**：沒有測試斷言 `deploy.yml` 的必要檢查含該名稱；merge-blockers 第 19 列狀態欄開頭仍寫「待處置」，與其後「已查證、不構成阻擋」不一致。
- **第 2 列**：(a) 後端已落地；(b) 屬 `entry-page-ui` 尚未做，在此之前伺服器送出的 `turnId=null` 錯誤在前端會被當成空字串輪次，「反問保留、可重選」目前只在後端成立。
- **示範大腦網關**：`backend/services/brain_router.py` 與 `frontend/src/pages/BrainPage.tsx` 已由本分支 `fa8ce42` 刪除，舊示範 commit 不是 `origin/ut` 的祖先，從未進過 `ut`；剩下的引用只有註解與兩處「必須已刪除」的斷言。
- **PBT**：`test_brain_gateway_rules.py` 有 7 個 `@given`，落在純函式。
- **ADR-0006 四面向**：與 §八 一致（認證先於 accept＋逐則重驗＋60 秒背景重驗；token 只在 subprotocol 標頭；連線、訊框、頻率、握手上限皆有測試；握手與每則訊息記稽核）。
- **grep 判準**：時間原語只在 `GatewayTiming` 預設值；logger 僅 `"cloud360.brain_gateway"`；`_mint_turn_id` 兩個呼叫點；`_send_single_error(conn` 13 處、`turnId` 皆 `None`。`brain_gateway_rules.py` 無 httpx／sqlalchemy／DB session，但匯入 `work_orchestrator`、`session_store` 的例外與常數，並非完全零依賴（不違反計畫判準）。
- **與本摘要既有文字不符處**：§13.1 寫 T9 以 `ledger.is_terminal` 判斷，現行程式為 `turn.terminal_sent`（review-02 R-08 的修正，處置見 merge-blockers 第 2 列）；計畫 §六規則表行號為修改前的值。

## 共用檔異動後的重新驗證與補審（計畫 §六之二；2026-10-31T03:00:03Z，`date -u`）

本輪未修改任何程式碼、測試或共用檔；只寫本節與計畫的勾選格。`traceability.json` 未更新（無新程式或測試，無追溯變動）。

### 一、共用檔重驗（收據 `reviewed-source-9c426874efea.tsv`，2026-10-26 09:10）

逐列 `shasum -a 256`（腳本讀收據每列與工作樹比對）：29 檔中 **26 檔逐位元相同、3 檔變動、0 檔缺失**。本單元的程式與測試（`brain_gateway.py`、`brain_gateway_rules.py`、`brain_ws_contract.py`、`main.py`、全部 `test_brain_gateway_*.py`、`brain_gateway_fakes.py`、`test_ws_contract.py`、`dump_ws_contract.py`、`ws-contract.json`、`ws-contract.d.ts`、`deploy/render-env.sh`、`deploy/.env.example`、`LOCAL-DEV.md` 等）全在相同的 26 檔內。

| 變動檔 | 收據 sha256 前 12 碼 | 現行 | 收據之後的改動來源 |
|---|---|---|---|
| `.github/workflows/deploy.yml` | `e121cf70c0da` | `3b6d08cd508b` | `7a50a40`（2026-10-27，合併前必修清單各單元修正；本檔改動屬第 26 列 `entry-page-ui`） |
| `DEPLOY.md` | `2608a131203c` | `d9b0571c5688` | 同上（第 26 列 ＋ 其他單元的修正，例如第 3 列「刪除使用者的行為」新段、U20 欄位轉型說明；未逐列歸因） |
| `frontend/tests/e2e/member-pages.spec.ts` | `1fe3a86b7e08` | `444d668dbd19` | 同上（`member-pages-ui` 第 9、14、23 列） |

**收據版本無法由 git 重建**：三檔的收據 sha256 不等於 `7a50a40^`（＝`624c170`，2026-10-19）、`7a50a40`、`HEAD`，也不等於往前的 `8677b7d`、`763a45a`、`fa8ce42`、`6dff4d4`、`2852790` 任一版本（逐一以 `git show <rev>:<path>` 算 sha256 比對）。收據當時的內容是未提交的工作樹狀態，故**無法證明收據之後的改動是 `7a50a40^..7a50a40` 這段 diff 的子集**；以下改為讀完涵蓋它的整段 diff，並對本單元負責或引用的部分逐行重讀現行檔補強。

**判定：三檔的改動皆未碰到本單元負責或引用的部分。**

- `deploy.yml`（diff 共 7 個 hunk：`@@ -32`、`-508`、`-584`、`-643`、`-784`、`-870`、`-924`）：全部是第 26 列的 6a「只回滾、不開 revert PR」（`:43` 新 output `brain_ws_probe_failed`、`:596` 6a 加 `id: brain_ws_probe`、`:805` revert 步驟的 `if`、`:889`／Slack 文字）與一處註解行號更新（`:517` 段）。逐行重讀現行檔：必要 secret 檢查 `OPENROUTER_API_KEY` 仍在 `:85`（env）、`:92`（缺值判斷）、`:100`（錯誤說明），render 步驟傳遞在 `:123`，rollback job 傳遞在 `:695`；內容與收據時相同，只因 `:32` hunk 新增 9 行而整體下移（review-03 R-07 引用的 `:76-83`、`:91-93` 現為 `:85-92`、`:100` 附近）。6a 的 `BRAIN_WS_URL: https://cloud360.danniel.cc/api/brain/ws`（`:599`）與探測內容未變；WS 路徑與啟動檢查未被改動。
- `DEPLOY.md`：本單元引用的 `OPENROUTER_API_KEY` 必要性在 `:24`，未在 diff 範圍（第一個 hunk 起於 `:248`）。§5.13 的 6a 段（現行 `:2229`、`:2238`）改為「自動流程只還原 last-good、不開 revert PR」；`/api/brain/ws`、協定名 `cloud360.brain.v1`、4401 原理（`:2230`）、本機驗證（`:2240`）與 U13 三層實測引用（`:2244`，指向本摘要 §6.2）皆未改。附帶觀察（**既存、非本次改動引入**）：`:2238` 前後兩版都寫「`U13` code-summary 第 4.5 節」，本摘要沒有 4.5 節（§四 是帶入項落點、4.4／4.5 是 `infrastructure-specification.md` 的節號），屬懸空引用；本單元不改共用檔，記為已知限制 L3。本摘要 §6.2 第 5 項「修好前以 revert PR 回滾」是**手動** L2 處置，與 6a 自動流程不開 revert PR 不衝突，`DEPLOY.md:2238` 也寫明人工 revert 屬使用者裁決。
- `member-pages.spec.ts`：本單元寫入的部分是 `NEUTRAL_LANDING = '/memory'`（現行 `:92`，說明註解 `:88-89`）、`setupApp` 內 `/api/memory/**` 空清單攔截（`:134`）、8 處 `goto(NEUTRAL_LANDING)`（`:323`、`:337`、`:597`、`:604`、`:663`、`:681`、`:726`、`:741`）與 3 處 `@ui /memory`（`:295`、`:650`、`:701`）。diff（`-U0`）的 hunk 在舊檔 `:64`、`:167`、`:210-241`、`:741` 之後新增，內容是 `membersErrorBody`、成員分頁、404／403 固定句、非數字專案編號、對話框焦點等 U24 案例，**沒有一行涉及上列任何一處**；現行檔 `'/brain'` 零命中。

### 二、回歸（副本）

副本：`/private/tmp/claude-501/-Users-jiangzhengdao-orca-workspaces-cloud-360-chiton/fbf7495c-cf60-4d5a-a3fe-9200f9902279/scratchpad/u13-reverify-20261031T025253Z/`（以 `rsync` 複製整個 repo，排除 `.git`、`node_modules`、`.venv`、`__pycache__`、`.hypothesis`、`aidlc`、`.claude`、`dist`、`*.tsbuildinfo`；`frontend/node_modules` 以 symlink 指向 repo）。複製後再以同一支比對腳本確認副本與 repo 現況一致（同樣 26 同、3 變動）。後端一律 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<副本>/backend backend/.venv/bin/python -B -P`，由一支小腳本在直譯器內 `os.chdir(<副本>/backend)` 後執行 unittest。

| 指令 | 結果 |
|---|---|
| 計畫指定的 12 支模組（本單元 8 支 ＋ `test_dump_ws_contract`、`test_intent_routing_structure`、`test_work_orchestrator_flow`、`test_session_store_behaviour`） | **Ran 270，OK（skipped=3）** |
| 其中本單元 8 支單獨跑 | **Ran 143，OK（skipped=0）**；與重做段的 143 案相同，故兄弟 4 支為 127 案（skip 3），與 §13.2 第二列相同 |
| 全套 `unittest discover -s tests`（副本，計畫 Step 16 的範圍） | **Ran 1326，OK（skipped=3）**（重做段為 1319，增量來自其他單元，未逐一歸因） |
| `backend/scripts/dump_ws_contract.py --check`（副本） | 「WS 契約規格檔與後端程式碼一致。」 |
| `backend/scripts/dump_openapi.py --check`（副本） | 「規格檔與後端程式碼一致。」 |
| `npm --prefix <副本>/frontend run check:ws-types` | 一致（含 BR4.4 哨兵說明檢查） |
| `npm --prefix <副本>/frontend run lint` | 0 errors、2 warnings（`AssessmentPage.tsx:395`、`WorkspacePage.tsx:344` 的 `exhaustive-deps`，既存） |
| `tsc -b <副本>/frontend/tsconfig.json`（以 repo 的 `node_modules/.bin/tsc` 執行） | exit 0 |

**偏離（如實記載）**：`tsc -b` 的 `tsBuildInfoFile` 設為 `./node_modules/.tmp/*.tsbuildinfo`，而副本的 `node_modules` 是指向 repo 的 symlink，所以 `tsc -b` **改寫了 repo 內既有的** `frontend/node_modules/.tmp/tsconfig.app.tsbuildinfo` 與 `tsconfig.node.tsbuildinfo`（兩檔建立於 2026-09-30，本輪只更新 mtime 與內容，未新增檔案）。兩檔在 `node_modules` 之下、為 git 忽略的建置快取，不影響任何受版控檔；但與「不在 repo 內留下建置產物」的要求不符。之後重跑時應把 `node_modules` 改為實體複製，或以 `--tsBuildInfoFile` 指到副本。另以 `find -newer` 確認：`backend/`、`frontend/`（不含 `node_modules`）、`scripts/` 內本輪沒有任何新寫入的檔（無 `.pyc`、無 `.hypothesis/`）。未連任何 DB、Redis 或網路（唯讀 `gh api` 列名除外）。突變未重跑：相關程式與測試自收據後逐位元相同，沿用重做段與 §13.3 的紀錄。

### 三、review-03 逐項現況（R-01–R-09 為 Resolved，R-10–R-12 Unresolved，R-13 New）

R-01–R-09：其修正點所在的 `brain_gateway.py`、`brain_gateway_rules.py`、`test_brain_gateway_*.py`、`deploy/render-env.sh` 自收據後逐位元相同，審查員的複驗結論沿用；抽查 R-08 判準 `terminal_sent` 仍在 `brain_gateway.py:506`（欄位）、`:1238`（送達後設定）、`:1158`（`_on_unexpected` 判斷）。

| ID | 現況 | 處置 |
|---|---|---|
| R-10 計畫 §六 規則表行號過期 | **仍成立**：計畫 T1–T9 仍是修改前行號（計畫第 105–113 行）。**另查出本摘要 §13.1 的行號也已過期**（審查員 10-26 核對時正確，其後 R-01–R-08 修正改動行數）：現行 T2 的錯誤送出在 `:1116`（§13.1 寫 `:1113`，該行現為 `try:`）、T3 的信封驗證在 `:1131`／送出在 `:1135`、`open_turn` 清空在 `:1137` 與 `:1144`（§13.1 寫 `:1133`、`:1140`）、`open_turn` 設定在 `:1309`（`_on_user_message`）與 `:1597`（`_on_select`）（§13.1 寫 `:1276`、`:1562`）；`:233`（欄位）、`:1142`（`_on_unexpected` 呼叫）仍正確。`_on_unexpected` 定義在 `:1146`、`_send_single_error` 定義在 `:1188`、`_on_select` 在 `:1590` | 只需改紀錄：以本列為準；計畫凍結不改。merge-blockers 第 2 列「發現 3」已記計畫行號過期 |
| R-11 T6 與 T3 的結局不同 | **行為仍成立**：T6 在 `_on_select` 先清 `pending_clarify`（`:1595`）再於 id 不在候選內時 `_fail_turn_exc`（`:1603-1605`），使用者不能重選；T3 在 `:1133-1136` 不碰 `pending_clarify`。**是刻意的**：使用者已於 2026-10-24 裁決「維持行為、記理由」，理由已寫在 merge-blockers 第 2 列「發現 4」——差在「能否判讀出選擇」（T6 選了一個可判定的值，該輪據此終止；T3 的壞訊框無法判讀，不算輪內）。本摘要 §13.1 先前只寫「現行不變」，以本列補記 | 只需改紀錄（本列即補記） |
| R-12 前端 (b) 的同批合併約束 | **已不成立**：merge-blockers 第 2 列「發現 5」與「(b) 已修正」段已寫明 (a)(b) 必須同批合併並說明兩個方向的過渡行為；(b) 已由 `entry-page-ui` 完成 | 無需處置 |
| R-13 第 19 列狀態矛盾、`deploy.yml` 必要 secret 檢查無測試 | **兩點皆仍成立**：(1) merge-blockers 第 19 列（第 28 行）處置欄開頭仍為「待處置」，其後為「已查證…不構成合併前阻擋」；(2) `backend/tests`、`scripts` 中提到 `OPENROUTER_API_KEY` 的 8 個檔都不斷言 `deploy.yml` 的必要檢查含該名稱（`test_render_env_redis.py:81` 只是清除環境變數；讀 `deploy.yml` 的 `test_brain_ws_deploy_probe.py`、`test_mcp_bridge_deploy.py` 檢查的是 6a 與 mcp-bridge）。**更精確地說**：不是「完全沒有部署相關測試」，而是缺「必要 secret 檢查含 `OPENROUTER_API_KEY`」這一情境的專屬案例 | 需改共用文件與新增測試 → 已知限制 L1、L2 |

**Step 15 名稱查證（本輪重做，唯讀、只列名稱、未讀值）**：`gh api repos/opendiamonds/cloud-360/actions/secrets --jq '.secrets[].name'` → 13 個，含 `OPENROUTER_API_KEY`；`.../actions/variables --jq '.variables[].name'` → 2 個（`APP_ID`、`GH_AW_DEFAULT_MODEL_COPILOT`），不含。與 §13.4 相同；限制不變（API 只證明現況）。

### 四、已知限制（需 conductor 併入 `merge-blockers.md`）

| # | 限制 | 需改的是 | 既有列是否涵蓋 |
|---|---|---|---|
| L1 | merge-blockers 第 19 列處置欄開頭「待處置」與其後「已查證、不構成阻擋」矛盾（review-03 R-13 (1)） | `merge-blockers.md` 本身 | 第 19 列就是該處，但未有處置；需 conductor 更正狀態字 |
| L2 | 沒有測試鎖住 `deploy.yml` 必要 secret 檢查（`:85`、`:92`）含 `OPENROUTER_API_KEY`；刪掉該行不會紅燈，而後果是缺金鑰時大腦每輪內部錯誤卻不擋部署（review-03 R-13 (2)） | 新增測試（例如讀 `deploy.yml` 斷言 `Require the secrets that must not default` 步驟同時有 env 與缺值判斷兩處） | **無既有列涵蓋**（第 19 列只涵蓋 secret 是否存在；第 26 列的 `test_brain_ws_deploy_probe.py` 只鎖 6a） |
| L3 | `DEPLOY.md:2238` 引用「`U13` code-summary 第 4.5 節」，本摘要無此節（既存懸空引用，非本次改動引入） | `DEPLOY.md` | 無既有列涵蓋；第 26 列改過該段落但未涉及此引用 |

### 五、勾選重設

以重做段（17／17）為基準逐格判定：Step 1–8、10、12–14、17 的證據檔自收據後逐位元相同（ADR-0020 檔仍在 `inception/decisions/0020-brain-ws-contract-page-scope-fields.md`）且本輪已重跑相關測試；Step 9（e2e 落地頁改寫）與 Step 11（環境與部署設定）的證據檔有變動，本輪已依第一節逐行重驗並重跑 lint、`tsc -b`、兩支 validator；Step 15 本輪重做；Step 16 本輪在副本重跑全套與兩道 drift 檢查。§六之二 五格依本節完成。Step 10 的突變本輪未重跑，以「被突變的程式與測試逐位元相同」為勾選依據，不是本輪重驗。

實算（收尾格勾選後，`grep -c -E "^\s*- \[x\]"` 與 `grep -c -E "^\s*- \[ \]"` 於計畫檔）：**已勾 22、未勾 0**（Step 1–17 共 17 格 ＋ §六之二 5 格）。

### 六、收尾

- `python3 scripts/validate_repo_contract.py`：passed；`python3 scripts/validate_env_contract.py`：passed（皆於寫入本節後執行）。
- `traceability.json`：未改動，以 `json.load` 確認仍為合法 JSON。

## 合併前必修第 37 列（計畫 §六之三 Step 18–24；2026-11-08T01:21:18Z，`date -u`）

範圍依使用者 2026-11-08 裁決：**只修第 37 列**。第 54 列兩項（`MemoryWorker.run` 授權被拒記成成功、UNAUTHORIZED 前寫歷史）與 `_prefetch`／`_write_episodic` 走主連線未動，維持已知限制。本輪新增一支測試、改本單元紀錄檔與 merge-blockers 第 37 列；**未改任何程式碼**，`brain_gateway.py` 等本單元程式與既有測試皆與收據逐位元相同（見第三點）。

### 一、Step 18 — (a)(c) 現況確認

| 項 | 現況（`grep -n`） | 落地者 |
|---|---|---|
| (a) 第 19 列狀態字 | **未落地**：`merge-blockers.md:28`（第 19 列）處置欄開頭仍為「待處置。**已查證**（2026-10-24…）…不構成合併前阻擋」，矛盾仍在 | 無。`brain-infra` code-summary :560 寫「brain-gateway：第 37 列 (a) merge-blockers 第 19 列狀態字（conductor）」——指派給 conductor；計畫 Step 18 假設「皆由他單元落地」對 (a) 不成立。本單元依「不擴大範圍」不改第 19 列，交 conductor |
| (c) `DEPLOY.md` 懸空引用 | **已更正**：現行 `DEPLOY.md:2340`「…交使用者裁決（`U13 brain-gateway` 的 code-summary 第八節「揭露事項」`OPEN-GW13-6` 那一列；先前寫的「第 4.5 節」不存在，合併前必修第 37 列 (c)）」；`HEAD` 版為 `:2239`「第 4.5 節」。被指向的落點確實存在：本摘要第八節表列 `Cloudflare 透傳未實測（OPEN-GW13-6）`（:252） | `brain-infra` A7（其計畫 :84 已勾、code-summary :490「A7…完成」）；變更尚未 commit（工作樹相對 `HEAD` 的 diff） |

### 二、Step 19 — (b) 部署 secret 檢查的專屬測試

新增 `backend/tests/test_deploy_required_secrets.py`（新建而非併入 `test_brain_gateway_startup.py`：後者在收據內且會匯入 `main` 觸發大量依賴，新建可讓收據內檔案逐位元不變；形狀比照 `test_brain_ws_deploy_probe.py`）。`DeployRequiredSecretsTest` 以 `yaml.safe_load` 讀 `deploy.yml` 的 deploy job，`setUp` 斷言「Require the secrets that must not default」步驟恰一個：

| 案 | 鎖住 | 現行落點 |
|---|---|---|
| `test_env_injects_openrouter_key_from_a_secret` | `env.OPENROUTER_API_KEY` 逐字為 `${{ secrets.OPENROUTER_API_KEY }}`（不是 `vars.`） | `deploy.yml:86` |
| `test_run_counts_an_empty_openrouter_key_as_missing_before_the_guard` | 缺值判斷恰一行、行序在 `if [ -n "${missing}" ]; then` 之前、其後有 `exit 1`、腳本有 `set -euo pipefail` | `:94`、`:95`、`:108` 附近 |
| `test_missing_branch_explains_what_an_absent_openrouter_key_breaks` | 缺值分支有 `echo "OPENROUTER_API_KEY: …" >&2` 且說明含 `INTERNAL_ERROR` | `:104`–`:105` |

三案皆有 `@purpose`／`@given`／`@step`／`@pass`／`@story US8.1` docstring；受測對象是 workflow 檔、無 HTTP 端點，故不寫 `@api`。只讀檔：不執行 workflow、不觸發 CI、未讀任何 secret 值、未用 `gh`。

### 三、Step 20 — (d) 補審節三處引用更正（不刪原文）

以下更正上方「共用檔異動後的重新驗證與補審」節（review-04 R-14），原文保留：

1. **懸空引用的行號**：該節第一點 `DEPLOY.md` 段與第四節 L3 寫 `DEPLOY.md:2238`——應為 **`:2239`**（`git show HEAD:DEPLOY.md | grep -n "第 4.5 節"` → 2239；`:2238` 是表格之後的空行）。該引用現已由 brain-infra 更正並位移至現行 **`:2340`**（見本節第一點）。
2. **T2 錯誤送出的行號**：該節 R-10 列寫「現行 T2 的錯誤送出在 `:1116`」——應為 **`brain_gateway.py:1117`**（`grep -n '"revalidate_failed"' -A1` → `:1116` 是 `_log(...revalidate_failed...)`、`:1117` 是 `await self._send_single_error(conn, *rules.error_for(exc))`）。`brain_gateway.py` 自收據後逐位元相同，此值現行有效。
3. **`7a50a40^` 的身分**：該節寫「`7a50a40^`（＝`624c170`，2026-10-19）」——`git rev-parse --short 7a50a40^` 為 **`fa51564`**。逐一以 `git show <rev>:<path> | shasum -a 256` 比對，`fa51564` 與 `624c170` 對 `deploy.yml`（`e7a2c51099a2`）、`DEPLOY.md`（`d499fb4824a1`）、`member-pages.spec.ts`（`eee56d09903e`）三檔內容相同，故該節「收據版本不等於 `7a50a40^`」的結論不受影響。

### 四、Step 21 — (e) 前端檢查的寫檔注意（**未完成，偏離**）

依計畫把下段 append 進 `unit-test-instructions.md` 第二節現況註記之後，下一個 Bash 指令即被 plan-approval guard 擋下（逐字：「Code generation cannot modify workspace paths for unit brain-gateway because the plan, unit-test instructions, and current Testing Contract do not have a current matching approval」）——該檔屬 Plan Approval 綁定的內容，改它等於使核可失效，之後連寫 scratchpad 都被擋。我以 Edit 把該段**逐位元還原**（還原後 guard 立即放行，證明位元組與核可時相同），其餘 Step 照常完成。**待 conductor 決定**：重錄 Plan Approval 後寫入，或改以本節為落點。原擬 append 的全文：

> 現況註記（2026-11-08，合併前必修第 37 列 (e)；review-04 R-15）：前端檢查在副本執行時，**副本的 `frontend/node_modules` 不得是指回 repo 的 symlink**。`tsconfig` 的 `tsBuildInfoFile` 寫在 `./node_modules/.tmp/*.tsbuildinfo`，經 symlink 執行 `tsc -b` 會改寫 repo 內 git 已忽略的 `frontend/node_modules/.tmp/tsconfig.{app,node}.tsbuildinfo`（2026-10-31 重驗時發生過一次，不觸及版控檔）。二擇一：(1) 副本的 `node_modules` 以實體複製（`cp -R` 或在副本 `npm ci`）；(2) 保留 symlink 時一律以 `tsc -b --tsBuildInfoFile <scratchpad 路徑>`（或 `tsc -p <tsconfig> --noEmit --incremental false`）把建置資訊導到副本外的 scratchpad——**本輪依指示未跑任何前端指令，未實測 build 模式（`-b`）是否接受 `--tsBuildInfoFile`**；若不接受，改用 (1) 或 `-p … --noEmit --incremental false`，不得退回經 symlink 的 `tsc -b`。執行後以 `find frontend/node_modules/.tmp -newer <開工前建立的標記檔>` 確認 repo 內無新寫入。另：本單元測試清單新增 `tests.test_deploy_required_secrets`（第 37 列 (b)，靜態讀 `.github/workflows/deploy.yml`，不需 Redis／DB），跑本單元模組時一併列入。

### 五、Step 22 — 突變驗證（只在 scratchpad 副本 `…/scratchpad/bg-copy/`；repo 內 `deploy.yml` 未動）

副本 `deploy.yml` 與 repo 同為 `daa226c7cb49…`；每項自備份還原後套用一處字串替換（`replaced 1`），跑 `tests.test_deploy_required_secrets`：

| 突變 | 結果 |
|---|---|
| D1 刪缺值判斷行（`[ -n "${OPENROUTER_API_KEY}" ] \|\| missing=…`） | **紅**：`test_run_counts_…` FAIL |
| D2 只刪 `env` 的 `OPENROUTER_API_KEY:` 行 | **紅**：`test_env_injects_…` FAIL |
| D3 `env` 改為 `${{ vars.OPENROUTER_API_KEY }}` | **紅**：`test_env_injects_…` FAIL |
| D4 缺值判斷移到 `if [ -n "${missing}" ]` 之後 | **紅**：`test_run_counts_…` FAIL |
| D5 刪 `echo "OPENROUTER_API_KEY: without it …"` 說明行 | **紅**：`test_missing_branch_…` FAIL |
| 還原（sha256 回到 `daa226c7cb49`） | **綠**：Ran 3，OK |

計畫要求的兩項為 D1、D2；D3–D5 為附加。副本已於收尾刪除。

### 六、Step 23 — 回歸

副本：`rsync` 整個 repo 至 `…/scratchpad/bg-copy/`（排除 `.git`、`node_modules`、`.venv`、`__pycache__`、`.hypothesis`、`aidlc`、`.claude`、`dist`、`*.tsbuildinfo`）；後端一律 `cd <副本>/backend && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. HYPOTHESIS_STORAGE_DIRECTORY=<scratchpad>/hyp <repo>/backend/.venv/bin/python -B -m unittest …`，`REDIS_URL` 先 unset。

| 指令 | 結果 |
|---|---|
| 本單元 8 支（含 `tests.test_ws_contract`） | **Ran 143，OK** |
| 本單元 8 支 ＋ `test_deploy_required_secrets` ＋ 兄弟 4 支 | **Ran 274，OK（skipped=3）**——143 ＋ 3 ＋ 128；兄弟 4 支由 127 增為 128，增量來自其他單元對 `test_session_store_behaviour.py`／`test_work_orchestrator_flow.py` 的未提交修改，未逐一歸因 |
| 三個 skip 以一次性 Redis 補跑：`redis-server --bind 127.0.0.1 --port 56391 --save '' --appendonly no`，`REDIS_URL=redis://127.0.0.1:56391/15` 跑 `test_session_store_behaviour.RealRedisParityTest` | **Ran 3，OK**；另順跑 `tests_redis.test_work_item_lua` **Ran 8，OK**（計畫未要求）。之後 `shutdown nosave` 並刪除其工作目錄，`ping` 確認已拒連 |
| 全套 `unittest discover -s tests`（計畫 Step 16 範圍） | **Ran 1395，OK（skipped=3）**（10-31 為 1326；增量來自其他單元） |
| `dump_ws_contract.py --check`（副本） | 「WS 契約規格檔與後端程式碼一致。」 |
| `dump_openapi.py --check`（副本） | 「規格檔與後端程式碼一致。」 |
| `validate_repo_contract.py`、`validate_env_contract.py` | passed／passed——**在 repo 以 `python3 -B` 執行**（偏離：副本不含 `.git` 與 `aidlc/`，`git ls-files` 掃描與 record 必要檔檢查無法在副本進行；兩支皆唯讀） |

本輪未跑任何前端指令。未連 staging、共用 DB／Redis 或網路；未用 `gh`。

**收據重驗（最新收據 `reviewed-source-e58f40332768.tsv`，29 檔）**：21 檔逐位元相同（本單元全部程式、測試、契約產物、`main.py`、`App.tsx`、`member-pages.spec.ts` 等），8 檔變動。8 檔的收據版本皆等於 `HEAD`（`git show HEAD:<path>` 的 sha256 與收據相同），故收據後改動恰為工作樹相對 `HEAD` 的未提交 diff，逐檔讀完：

| 變動檔 | 改動內容（他單元） | 是否碰到本單元負責或引用的部分 |
|---|---|---|
| `.github/workflows/deploy.yml` | `MEMORY_DB_PASSWORD` 加入必要檢查與 render／rollback 傳遞、新步驟「Set the memory-only database role password」、Redis 密碼改走 `REDISCLI_AUTH`、快照逐欄比對、6a 位置註解更正 | 否：`OPENROUTER_API_KEY` 三處（`:86`、`:94`、`:104`）與 render（`:128`）、rollback（`:757`）傳遞內容未變，只因上方插行而位移；6a 步驟內容未變 |
| `DEPLOY.md` | 記憶角色小節、多列合併前必修文字、`:2340` 懸空引用更正 | 只有 `:2340`（即第 37 列 (c)，指向本摘要，正確）；`:24` 的 `OPENROUTER_API_KEY` 必要性未在 diff 內 |
| `LOCAL-DEV.md` | `:273` 起新增 29 行（成員回填 dry-run） | 否（diff 內 `brain`／`OPENROUTER`／`REDIS` 0 命中） |
| `backend/requirements.txt` | 新增 `sse-starlette==3.0.3`、`mcp-types==2.3.0`（第 38 列 (a)） | 否：本單元的 `websockets`（`:56`）仍在 |
| `deploy/.env.example`、`deploy/render-env.sh` | `MEMORY_DB_PASSWORD` | 否 |
| `frontend/src/components/Sidebar.tsx` | 記憶 `<nav>` 加 `aria-label`（第 35 列 (c)） | 否：`/brain`、`大腦（示範）` 0 命中，DEMO 移除仍成立 |
| `frontend/tests/e2e/memory-page.spec.ts` | 檔尾新增 136 行 U15 案例、0 行刪除 | 否：本單元改寫的 `/memory` 落地頁（`:232`、`:283`）未動 |

### 七、Step 24 — 收尾與勾選重判

- `traceability.json`：`reverse` 加 `MB-37`；`source-manifest.json`：補列 `backend/tests/test_deploy_required_secrets.py`；兩檔 `json.load` 通過。
- `merge-blockers.md` 第 37 列處置欄：就地 append 本輪結論（原文保留），結論為「待重審 brain-gateway」。
- **勾選重判**（以收據比對與本輪回歸為準；只改勾選字元，改前存副本、改後 diff 確認）：
  - 勾：Step 1–8、10–14、16、17；§六之二 五格；§六之三 Step 18、19、20、22、23、24。
  - **不勾 Step 9**（DEMO 前端移除，以 `lint`／`tsc -b` 驗證）：其證據檔 `Sidebar.tsx`、`memory-page.spec.ts` 自收據後已變動，而本輪依指示不跑前端指令，`lint`／`tsc -b` 未重驗；DEMO 移除的內容以 grep 確認仍成立，但計畫的驗證手段未重跑。
  - **不勾 Step 15**（secrets／variables 名稱查證）：證據是 GitHub 的外部狀態，不是可逐位元比對的檔；本輪指示 `gh` 一律不用，無法重驗。10-31 的結果（secrets 含、variables 不含）仍是最近一次紀錄。
  - **不勾 Step 21**：見本節第四點。
  - Step 10：被突變的程式與測試自收據後逐位元相同，沿用先前紀錄（非本輪重跑）；Step 11：變動的部署／環境檔已逐檔判定未碰本單元部分，兩支 validator 本輪通過；§六之二 五格：該輪紀錄仍在（上方一節，未改），其引用誤差已由本節第三點更正。
  - 實算見本節末行。
- 勾選前存副本（scratchpad `bg-plan-before-mb37.md`），勾選後以「把 `[x]` 換回 `[ ]` 再 diff 副本」確認**只有勾選字元變動**（26 行）；實算（`grep -c -E "^\s*- \[x\]"`／`"^\s*- \[ \]"` 於計畫檔）：**已勾 26、未勾 3**（Step 9、15、21；全檔 29 格＝Step 1–17 共 17 ＋ §六之二 5 ＋ §六之三 7）。
- `validate_repo_contract.py`、`validate_env_contract.py`：寫入本節前執行皆 passed，寫入本節後重跑見回報。

## 整站重跑後的勾選回復（2026-11-08T22:44:56Z）

- 背景：2026-11-08T06:40:14Z 使用者決定重跑整個 code-generation 階段（整站關卡因審查收據失效卡死，唯一出路）。引擎把本計畫勾選全部重設為未勾。
- 依據：以 Python `hashlib` 重算上一次審查留下、與現況最吻合的收據 `reviewed-source-f0f6ecd79388.tsv`：29 同、1 變（`LOCAL-DEV.md`，交審查員判定是否碰到本單元）。本輪 `REVIEW_REQUESTED` 當下引擎另會產生一份新收據，以那份為準。既有勾選依 HEAD 版回復（差異僅勾選字元）。
- 現況（實算）：26 勾／3 未勾；未勾格沿用 HEAD 的未勾理由：
  - - [ ] **Step 9 — Frontend**：本單元不新建頁面（屬 `U14`）；只做 DEMO 前端移除與兩支 e2e 落地頁改寫，以 `npm run lint`、`tsc -b` 驗證；e2e 由 CI `ui-regression` 執行。
  - - [ ] **Step 15 — 第 19 項查證**：以 `gh api repos/opendiamonds/cloud-360/actions/secrets` 與 `.../actions/variables` 各查一次名稱（唯讀，只列名稱、不讀值），確認 `OPENROUTER_API_KEY` 在 sec
  - - [ ] **Step 21 — (e) 前端檢查的寫檔注意**：在 `unit-test-instructions.md` 的現況註記 append 一段：往後前端檢查改用實體 `node_modules` 副本或 `tsc -b --tsBuildInfoFile` 指向 scratchpad，避免經 symli
