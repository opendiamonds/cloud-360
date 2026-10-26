## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-24
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | backend/tests/test_mcp_bridge_e2e.py > IdentityIsolationTest.interleave（約 170-215 行）；backend/tests/mcp_topology.py > Barrier；code-summary.md 第五節「已知限制」 | 新設計問題。BR78.4（身分隔離，ADR-0006 IAM 面向）的測試靈敏度不足，有三處。(1) 屏障掛在 backend 記錄包裝內，此時 bridge 已讀完 Authorization 並組好請求，屏障只能證明「A 的請求抵達 backend 時 B 也已進入 bridge」，無法強迫「寫入 ContextVar 與讀取之間」的交錯窗口；M09 能轉紅靠的是 8 個 worker 的自然交錯（作者以連跑 4 次紅作證），不是屏障，與 unit-test-instructions 所稱「不靠 asyncio.gather 的機率」不符，且該屏障是單發（arrived 一旦設定就不再扣）。(2) 寫入變體在 M09 下仍綠（作者在已知限制中承認），而 BR78.4 明文要求寫入變體斷言 updated_by。(3) interleave 對兩位使用者傳入同一個 agent 值（兩組 worker 都用 agent="cost"），所以 X-Cloud360-Agent 的逐請求隔離（決定 on_behalf_of，BR74.4）完全沒有保護：把 RawHeaders.agent 改存模組變數，現有測試全綠。 | 讓 owner 與 outsider 的 worker 使用不同的已登錄 agent（cost 與 architecture），並在 backend 記錄包裝與持久列斷言各自的 on_behalf_of；補一個 agent 變數的突變（agent 改存模組變數）並記入突變表且須轉紅。為 M09 找一個確定性的窗口（例如 create_app 的測試縫或 exchange 前的可注入 await 屏障，或把交錯回合數與每回合最低重疊數寫進斷言），使寫入變體在 M09 下也轉紅；做不到時，在 code-summary 明寫「身分隔離的偵測是機率性的」並把連跑次數提高到足以支撐宣稱。 | New |
| R-02 | Minor | backend/mcp_bridge/limits.py > REQUEST_WALL_TIMEOUT_S 與 OVERALL_TIMEOUT_S、BODY_READ_TIMEOUT_S；backend/mcp_bridge/guards.py > WallClock（作者偏離 D-1） | 新引入。D-1 把牆鐘移到本體閘門外是正確的（否則最壞 14 秒、stop_grace_period 關係式不成立），但移動後牆鐘 12 秒恰等於本體期限 2 秒加 backend 整體期限 10 秒，零餘裕，pure 測試的斷言是 ≥（容許相等）。慢速上傳者在約 2 秒時送完本體、backend 又掛住時，backend 交換在約 12 秒逾時，再加 SDK 序列化的數十毫秒，牆鐘較可能先觸發，client 會得到非 BR76.1 形狀的裸 503 與 request_timeout，而不是 backend_unavailable 且 retryable: true；tool_call 那一行則因取消而記成 internal_error、http_status 為 null。 | 在 limits.py 的關係式加入餘裕（例如牆鐘 ≥ 本體期限 + 整體期限 + 1 秒，並同步 stop_grace_period 與 DEPLOY.md §5.12 的算式），或把本體讀取時間從整體期限中扣除；pure 測試改為嚴格大於。 | New |
| R-03 | Minor | backend/tests/test_mcp_bridge_e2e.py > DisconnectTest.test_slow_backend_with_drop_loop_does_not_exhaust_pool；code-summary.md 第三節 D-6 與第五節突變表 | 新引入。D-6 把判準由「20 行 tool_call」改為「抵達 backend 的請求數等於 tool_call 行數、名額歸零、之後呼叫成功」，方向合理，但只斷言 records ≥ 1：實際抵達 backend 的同時請求數不受保證，高於連線池與閘門上限（16）的壓力前提沒有被斷言，連線池耗盡這個 nfr-design R-02 要防的缺陷可能根本沒被施壓。0.05 秒斷線對 0.2 秒 backend 延遲的時序在慢速 CI 上也可能讓抵達數趨近 0，造成不穩定。突變表沒有任何一列針對 DisconnectTest（M32 鎖的是 json_response 前提）。 | 在迴圈中觀察並斷言峰值同時在途數（例如 gate.in_flight 峰值或 recorder 最大並行）達到上限附近，或調整時序使其確定；補一列突變（例如名額在交換結束前歸還，或名額從不歸還）並記入突變表。 | New |
| R-04 | Minor | backend/mcp_bridge/server.py > serve_until_stopped、_run；backend/mcp_bridge/cli.py > parse_args | 新設計問題。uvicorn 在 lifespan 啟動失敗時（BridgeApp._lifespan 送出 lifespan.startup.failed）只會讓 Server.serve 正常返回、server.started 維持 False，serve_until_stopped 不檢查，_run 回傳 0，容器以退出碼 0 結束並被 restart: unless-stopped 靜默重啟。另外 --max-concurrency 0 會讓 BridgeLimits 拋 ValueError、--port 超出範圍會拋 OverflowError，兩者都以 traceback 結束，而不是 startup_failed 單行 ERROR（OSError 才有被接住）。 | serve_until_stopped 在 server.started 為 False 時回報失敗並使 _run 回傳非零；cli 對 max-concurrency 與 port 做範圍驗證並走 log_startup_failed。補一個測試（替身 lifespan 失敗時退出碼非零）。 | New |
| R-05 | Minor | backend/mcp_bridge/app.py > on_call_tool 與 to_call_tool_result（115-126 行）；backend/mcp_bridge/dispatch.py > run_tool_call（57-63 行） | 新設計問題。總攔截只包住 _execute；run_tool_call 返回之後的 to_call_tool_result（json.dumps、CallToolResult 建構）發生在攔截之外，而 Step 1 的 S-9 實測舊式協定版本會把處理函式拋出的例外字串原樣送回 client。目前該路徑的例外文字不含 token，但可能含 backend 回應的內容片段（例如無法編碼的字元），且 tool_call 已經記為 ok，client 與 log 的結果不一致。 | 把結果序列化納入同一個總攔截（例如在 on_call_tool 以 try 包住並回 internal_error），或把 to_call_tool_result 移進 run_tool_call 的 try；補一個以 mock 讓 to_call_tool_result 拋例外的 legacy 案例，斷言回應不含例外字串。 | New |
| R-06 | Minor | backend/mcp_bridge/guards.py > WallClock、ConcurrencyGate；code-summary.md 第十二節 K-6 | 新設計問題。K-6 只實測了「client 斷線」不取消處理函式；WallClock 逾時是取消外層 ASGI 呼叫，這是另一條路徑。舊式協定版本的處理函式跑在 session manager 的 task group 裡，取消 handle_request 後處理函式可能繼續執行到整體期限，而名額已在 finally 歸還，使實際並行可短暫超過閘門上限。guards 測試用 FakeInner，沒有觸及真實 SDK。 | 以真實 SDK 拓樸補一個牆鐘逾時案例，觀察處理函式是否仍在執行與名額；若會超出，在文件揭露上限為「閘門值加上仍在跑的逾時處理函式」，或讓 exchange 能感知取消。 | New |
| R-07 | Minor | backend/requirements.txt > mcp==2.3.0；code-summary.md 第十二節 K-1 與 S-17 | 新設計問題。SDK 行為假設總表是在 mcp==2.3.0 加上一次解析出的傳遞依賴（sse-starlette 3.0.3、mcp-types 2.3.0 等）上實測的，但只有 mcp 本身精確釘選；其餘傳遞依賴沒有 pin 或 constraints，而 team.md 已記載 CI、Docker build、staging 三處各自解析最新版（D-7 實際撞到 sse-starlette 3.4.8 與 starlette 的衝突就是前兆）。K-1 的解析報告來自作者的開發機，沒有證明 python:3.12-slim（linux amd64、無編譯器）上 cryptography、cffi、rpds-py 都取得 manylinux wheel；Dockerfile 沒有 gcc，缺 wheel 時映像建置會失敗，而這個失敗只會出現在部署時。 | 加入 constraints 檔或釘住 sse-starlette 與 mcp-types 的解析結果；在 CI 的 docker-build 之外，以 pip install --only-binary=:all: 對 linux amd64 做一次乾跑，把結果記入 code-summary；升版仍須重跑 K-1 到 K-11。 | New |
| R-08 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/mcp-bridge/code-generation/code-summary.md > 第四節第 33 列 | 新引入。第 33 列寫「DEPLOY.md :1336、:1913、:1914 不動」，這是改動前的行號：改動後「其餘六個 brain-infra 變數不是 secret」在 1915 行，而 1914 行本來就不是這句（HEAD 版只有 1336 與 1913 兩處）。引用的內容正確、定位錯誤，照行號去讀的人會讀到別的內容。 | 把行號改為現況（1336 與 1915），或改以句子引用，不寫行號。 | New |
| R-09 | Minor | backend/tests/test_mcp_bridge_deploy.py > DeployWorkflowTest.test_blocking_once_a_real_client_exists；.github/workflows/deploy.yml > Record mcp-bridge health (non-blocking) | 新設計問題。把健康步驟改為阻擋的觸發條件只靠字面比對 backend 目錄下 .py 檔案內的 mcp-bridge:8080。client 若用組合字串、設定檔、或放在 backend/scripts 以外的位置（例如 frontend 或 TypeScript）就不會觸發，非阻擋狀態會悄悄延續。 | 放寬為比對 mcp-bridge（任何埠）與 8080 的組合並涵蓋 frontend、scripts 與 deploy 目錄；或在 DEPLOY.md §5.12 與 PR 範本明寫人工檢查項。 | New |
| R-10 | Minor | backend/mcp_bridge/generator.py > validate_tool_specs（447-484 行）；backend/tests/test_mcp_bridge_startup.py | 既存漏審。functional-design R-12 擇 (a) 的本意是以 allowlist.json 作為獨立參考重驗產物，但 validate_tool_specs 只比對工具集合、method、path、屬性名集合與綁定名集合；binding 內各映射的 API 名稱（body_params、path_params、query_params 的值）、inject 內容與屬性 pattern 沒有和 allowlist 比對。手改的產物若移除 inject，寫入會缺少 on_behalf_of（溯源遺失）；若把 body_params 的某個值改成 on_behalf_of，呼叫端可指定溯源標示。CI 漂移閘門會擋下已提交的手改，所以這是縱深防禦缺口，不是目前可利用的洞。 | 讓 validate_tool_specs 比對 binding 的映射與 inject 與 allowlist 推導值一致（可直接重算 allowlist 對應的預期 binding），並在 T-8 補兩案（inject 被移除、body_params 值被改成 on_behalf_of）。 | New |
| R-11 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/mcp-bridge/nfr-design/security-design.md > 第八節「讀取稽核」與第九節 Audit logging 列 | 兩處仍寫「成功讀取不新增帶使用者身分的紀錄」「讀取面依 `[MBN1]`=A」，與現在 `requirement_field_facade.py` 的 `requirement_field.read` 行為相反。code-summary 第十四節已宣告「取代、不回改」，但開發者只讀 NFR 設計時會以為讀取面不應有 log。 | 在 security-design.md 第八節與第九節 Audit 列各加一句指向 code-summary 第十四節的取代註記；或在下一輪修訂時改寫該兩處。 | New |
| R-12 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/functional-design/merge-blockers.md > 第 7 列「殘餘風險」；code-summary.md 第十四節「第 7 項」 | 殘餘風險只寫「`mcp` 網段內被入侵的容器」可竊聽 token。`deploy/docker-compose.deploy.yml` 約 477–483 行的註解自己寫明：主機上的行程（含自架 runner）是否能連到 `mcp-bridge:8080` 取決於 Docker 引擎版本，要部署後才量測（DEPLOY.md §5.12）。例外紀錄比 compose 的說法樂觀。結論（記為對 `requirements.md:618` 的例外而非符合）是誠實的，只有範圍描述偏窄。 | 在第 7 列補一句「主機本機行程是否可達待部署後量測（DEPLOY.md §5.12）」；同時說明 security-design.md:83-84 所稱的「`internal` 網段」已被專屬 `mcp` 網段取代，網段是收窄的，不是原樣沿用。 | New |
| R-13 | Minor | backend/tests/test_requirement_field_facade.py > 約 323 行 not-found 讀取案（R3 旁） | R3 只證明「被拒（forbidden）」不記 `.read`。系統不存在或專案不可見（`RequirementFieldNotFound`）的讀取沒有「不記 `.read`」的斷言。實作上 `_authorize` 會在 `_log_read` 之前拋出，行為正確，但屬未鎖定的路徑。 | 在既有 not-found 案加 `assertLogs` 或 `assertNoLogs`，斷言 `requirement_field.read` 為 0 筆。 | New |

> R-01 Not re-checked this round

> R-02 Not re-checked this round

> R-03 Not re-checked this round

> R-04 Not re-checked this round

> R-05 Not re-checked this round

> R-06 Not re-checked this round

> R-07 Not re-checked this round

> R-08 Not re-checked this round

> R-09 Not re-checked this round

> R-10 Not re-checked this round

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `unittest tests.test_requirement_field_facade tests.test_mcp_bridge_e2e` | 重跑 3 次得 `Ran 26 tests`、`OK` | 與 code-summary 的 26 案一致。我的第一次執行曾回報 2 個 `KeyError: 'error'` 錯誤（e2e），後續 3 次無法重現；另有一次輸出疑似重複，無法確認是否為偶發不穩，建議留意。 |
| 實作路徑核對 | `read_fields` 先 `_authorize`（拋 NotFound／Forbidden 時早退），再 `fetch_rows`、`compose_field_set`，最後 `_log_read(principal, known_id)` | 每次成功讀取恰記一行；被拒與不存在不記。`system_id` 是授權後的整數 `known_id`。 |
| 呼叫者盤點（`backend/` 下 `read_fields`） | 非測試呼叫者只有 `requirement_field_router.py:153` | HTTP 路徑與 MCP bridge 路徑（bridge 經 HTTP 帶使用者 token）都經此單一處，沒有 in-process 呼叫者能繞過，也不會重複記。 |
| 洩漏檢查 | log 訊息與 `extra` 只有 story_id、action、system_id、user_id、on_behalf | 不含欄位值、key、輸入或 token。R2 以 `uuid4` 標記驗證。`main.py:27` 為 `basicConfig(level=INFO)`，INFO 行實際會輸出。 |
| 數字重算 | `source-manifest.json` writes 為 41；`traceability.json` 的 upstream_ids＝coverage＝90、reverse＝11；facade 的 sha256 ＝ 文件所載基線 `f3900ca3…c9cf6`；facade 測試檔 11 案；diff 該檔 27 行 | 皆與 code-summary 第十四節相符。 |

### Summary

#8 的實作正確：成功讀取恰記一行、授權後才記、不洩漏值，測試與突變驗證可重現。#7 如實記為對 `requirements.md:618` 的例外，結論可接受。剩下三項都是文件與測試覆蓋的 Minor（NFR 文件未標註被取代、殘餘風險未提主機本機可達性、not-found 路徑缺斷言），不阻擋核可。
