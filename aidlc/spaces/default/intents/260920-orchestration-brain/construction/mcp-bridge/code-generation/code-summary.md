# Code Summary — `U21 mcp-bridge`

> 依 `code-generation-plan.md`（Testing Contract `sha256:1f0b6822…`，`test-after`、`standard`）Step 1–14 完成，撰寫於 2026-10-15T01:50Z（`date -u`）。
> 路線 **A**（`mcp==2.3.0`，`MCP_ROUTE = "same-interpreter"`）、**17-A**、**16-A**，使用者於 Step 1 中途關卡核可，並採納四點調整（第二節）。
> 契約變更紀錄 `ADR-0021` 已於 Step 1 移入 `inception/decisions/0021-mcp-bridge-x04-contract-increments.md`（Status 改 Accepted；草案檔依派工保留）。
> 帶入的 37 項（`../carried-review-items.md`）逐項落點見第四節：**37 項全數處置，0 項拒絕**。
> 本單元測試 **147 案**（11 支檔）全綠，連同就緒檢查 `tests.test_requirement_field_http` 共 154 案；突變驗證 **51 列全紅**（第五節 38 列＋第十三節程式審查新增 13 列）。
> 程式審查 `reviews/review-01.md`（READY）的 R-01..R-10 已依使用者裁決「這批一起修」全數處置，見第十三節。

## 一、交付檔案

### 新建

| 檔案 | 計畫 # | 內容 |
|---|---|---|
| `inception/decisions/0021-mcp-bridge-x04-contract-increments.md` | 1 | 由草案原樣移入，只改標題與 Status |
| `backend/mcp_bridge/__init__.py` | 2 | 空檔 |
| `backend/mcp_bridge/__main__.py` | 3 | 兩行 import ＋ `raise SystemExit(main(sys.argv[1:]))` |
| `backend/mcp_bridge/cli.py` | 4 | `parse_args`（`--backend-url` 必填、`--host` 預設 `127.0.0.1`、`--port` 8080、`--max-concurrency` 16）；`main(argv, *, config_dir)`，驗證通過後才 import `server` |
| `backend/mcp_bridge/startup.py` | 5 | `load_and_validate(config_dir)` 讀三份 JSON；I/O、編碼、JSON、結構與 `validate_tool_specs` 的違規一律包成 `StartupConfigError(subject)` |
| `backend/mcp_bridge/observability.py` | 6 | `configure_logging`、`BridgeFormatter`（單行化）、`normalize_tool`；`tool_call`／`request_rejected`／`internal_failure`／`startup`／`startup_failed` 五種事件 |
| `backend/mcp_bridge/limits.py` | 7 | 七個具名常數、`BridgeLimits`、`derive_allowed_hosts` |
| `backend/mcp_bridge/guards.py` | 8 | `PathRouter`、`MethodGuard`、`ConcurrencyGate`、`WallClock`、`BodyLimit`、`ExactPath`、`CredentialContext`、`CREDENTIALS` |
| `backend/mcp_bridge/dispatch.py` | 9 | `run_tool_call`：總攔截、`tool_call` 唯一寫出點 |
| `backend/mcp_bridge/executor.py` | 10 | 全單元唯一 import `httpx`：`build_backend_client`、`exchange`、`read_bounded`、`classify_transport_error` |
| `backend/mcp_bridge/{generator,calls,outcomes,credentials,agents}.py` | 11 | 五個純函式模組；`outcomes.py` 含封閉聯集 `ExchangeResult` 與四值 `TransportKind` |
| `backend/mcp_bridge/app.py` | 12 | `create_app(*, backend_client, registry, tool_specs, allowed_hosts, limits=BridgeLimits())` 回 `BridgeApp`；全單元唯一 import `mcp` 的模組 |
| `backend/mcp_bridge/server.py` | 13 | `bind_socket`、`build_uvicorn_server`（`access_log=False`、`log_config=None`）、`serve_until_stopped`、`serve` |
| `backend/mcp_bridge/{allowlist,generated_tools,agents}.json` | 14 | 三份進版控檔 |
| `backend/scripts/gen_mcp_tools.py` | 15 | 寫出與 `--check`；只 import `mcp_bridge.generator` |
| `backend/tests/mcp_topology.py` | 16 | `MCP_ROUTE`、`assert_prerequisites`、`bounded`（每案 30 秒）、`LogSource`、`RecordingBackend`（含請求本體擷取）、`CallHookBarrier`（程式審查 R-01，取代原本掛在 backend 包裝內的 `Barrier`）、`BridgeTopology`、`preserve_logging` |
| `backend/tests/mcp_test_client.py` | 17 | `BR78.1`：`SdkClientPort(url, mode)`，`mode` ∈ {`legacy`, `auto`} |
| `backend/tests/test_mcp_bridge_*.py` | 19 | 11 支：generator 11 案、pure 25、guards 12、dispatch 13、app 10、startup 19、topology 5、artifacts 8、e2e 15、static 17、deploy 12（合計 147；程式審查前為 137） |
| `code-generation/{code-summary.md, traceability.json, source-manifest.json}` | 21 | 本檔與追溯 |

路線 A 下**不建** `backend/tests/mcp_wire_client.py`（計畫 #18）與 `backend/requirements-mcp.txt`（#20）。

### 修改

| 檔案 | 計畫 # | 內容 |
|---|---|---|
| `backend/requirements.txt` | 22 | 新增一行 `mcp==2.3.0`，註解寫明精確釘選的理由、backend 行程不 import、升版須重跑 K-1–K-11、Python 3.14 的衝突 |
| `deploy/docker-compose.deploy.yml` | 23 | 新增服務 `mcp-bridge`；新增頂層網段 `mcp`（`internal: true`）；`backend` 改為 `[edge, internal, mcp]`；註解：檔頭服務清單、`50m x 5 x 7 = 1.75GB`、backend 網段說明、「seven」、`networks:` 的 `internal: true` 禁令限縮到 `edge`／`internal` 並說明 `mcp` 的例外、host 可達清單 |
| `backend/Dockerfile` | 24 | **不改**（路線 A） |
| `.github/workflows/ci.yml` | 25 | `backend` job 加 `timeout-minutes: 15`；在 `WS contract spec drift` 之後、`Run unit tests` 之前加 `MCP tool spec drift`（不帶 `env:`） |
| `.github/workflows/deploy.yml` | 26 | 在 tunnel 等待步驟之後、Redis 重啟驗證之前加 `Record mcp-bridge health (non-blocking)` |
| `DEPLOY.md` | 27 | §5.6、§5.9.1、§5.11 同步；新增 §5.12。「其餘六個 brain-infra 變數不要加成 secret」與「其餘六個 brain-infra 變數不是 secret」兩句（與服務數無關）未動 |
| `LOCAL-DEV.md` | 28 | port 迴圈加 8080；新增「本機啟動 MCP bridge」一小節 |

**不改的檔**：`deploy/render-env.sh`、`deploy/.env.example`、`backend/.env.example`、`deploy/docker-compose.test.yml`、`frontend/nginx.conf`、`deploy/cloudflared/config.yml`、根目錄 `docker-compose.yml`、`schema_rbac.sql`、`backend/main.py` 與全部 router、`openapi.json`。**零新環境變數、零 secret、零對外埠、零 DDL、零 volume**——`validate_env_contract.py` 與 `validate_repo_contract.py` 皆通過。

## 二、中途關卡核可的四點調整：落實

| # | 調整 | 落點 |
|---|---|---|
| 1 | legacy 與 auto 兩種協定版本的端到端都測 | `mcp_test_client.MODES = ("legacy", "auto")`；`test_mcp_bridge_e2e.py` 的 AC11.4.1／AC11.4.2／AC11.4.3、T-1 讀取、T-2、T-4 皆在同一個案例內跑兩種模式；`test_mcp_bridge_app.py` 以原始 JSON-RPC 對 `2025-06-18`（或不帶版本標頭）與 `2026-07-28` 各送一次；`test_mcp_bridge_topology.py` 斷言兩種模式協商出的版本分別為 `2025-11-25` 與 `2026-07-28` |
| 2 | T-2 至少一個 legacy 外洩案例 | `test_mcp_bridge_app.test_no_exception_reaches_the_sdk` 與 `test_mcp_bridge_e2e.NoLeakTest.test_transport_failures_and_internal_crash_leak_nothing`：令 `build_backend_call` 拋出內含 token 的 `RuntimeError`，兩種協定版本都斷言回應與 log 不含它。突變 M10（總攔截改回 `str(exc)`）使兩者皆紅 |
| 3 | SDK 2.x 設定項 | `app.py`：`Server(..., get_tool_input_schema=...)`（S-13）、`StreamableHTTPSessionManager(max_request_body_size=limits.max_request_body_bytes)`（S-12，與 `BodyLimit` 同值，超量一律先由 `BodyLimit` 回 413 並留紀錄）；`observability.THIRD_PARTY_LEVELS` 把 `mcp`、`httpx`、`httpcore` 設為 WARNING（S-11）。另 `json_response=True` 由 app 測試的 `content-type` 斷言鎖住（突變 M32 紅） |
| 4 | Python 3.14 註解 | `backend/requirements.txt` 的 `mcp==2.3.0` 註解 |
| — | CI 最壞時間依案例數重算 | 見第七節 |

## 三、與計畫不符或偏離之處（取代紀錄）

| # | 計畫字面 | 實作 | 理由 |
|---|---|---|---|
| D-1 | §三 Step 3 層序：`ConcurrencyGate` → `BodyLimit` → 牆鐘 → 精確路徑 | `ConcurrencyGate` → **`WallClock` → `BodyLimit`** → 精確路徑 | 牆鐘在 `BodyLimit` 之內時，最壞時間是本體期限 2 秒＋牆鐘 12 秒＝14 秒，`stop_grace_period` 的關係式不成立。改排在外層，牆鐘涵蓋本體讀取與 backend 交換全程。**程式審查 R-02 另把牆鐘由 12 秒調為 13 秒**（2 ＋ 10 ＋ 1 秒餘裕），關係式為 13 ＋ 1 ＝ 14 < 15；`test_mcp_bridge_pure.LimitsTest` 改為嚴格大於 |
| D-2 | 「只有 `app.py` 與 `server.py` import `mcp`」 | 實際**只有 `app.py`**；`server.py` 經 `app` 間接使用 | `server.py` 不需要 SDK 符號。靜態測試斷言 import 集合 ⊆ {`app.py`, `server.py`} 且含 `app.py` |
| D-3 | `run_tool_call(spec_or_none, arguments, credential, agent_header, exchange)` | 另加關鍵字參數 `registry` 與 `requested_name` | `registry` 是 `resolve_agent` 的必要輸入；`requested_name` 讓「呼叫端送來的工具名只以正規化結果入 log」在真實路徑上可被測試（突變 M23 使 app 與 dispatch 測試紅） |
| D-4 | 未預期例外「log 只記例外型別名」 | 另寫一行 `internal_failure exc_type=<型別名>`（WARNING） | `tool_call` 的欄位是封閉白名單，不能塞型別名；`tool_call` 行數恰 1 的判準不受影響 |
| D-5 | `NFR21.33` 的 `mcp.server.lowlevel.server` 設 ERROR | 不設 | 2.x 的處理函式例外由 `mcp.shared.jsonrpc_dispatcher`／`mcp.server.runner` 記錄（S-10）；17-A 與總攔截使它們不會被觸發。`mcp` 整體為 WARNING |
| D-6 | `DisconnectTest` 的「慢速 backend 加斷線迴圈」原寫「20 行 `tool_call`」 | 判準改為「抵達 backend 的請求數＝`tool_call` 行數、名額歸零、之後的正常呼叫成功」；**程式審查 R-03 另加壓力前提**：24 條連線、backend 慢 0.5 秒，並行閘峰值必須等於上限 16、抵達 backend 的請求數 ≥ 16、至少一筆 `over_concurrency` | 連線在 uvicorn 把請求交給 app 之前就關閉者不會產生工具呼叫（實測 20 條中只有部分抵達），這是正確行為；原判準會把正確行為判為紅燈 |
| D-7 | 派工指示「以 `pip install mcp==2.3.0` 安裝到本機 backend 開發環境」 | **未安裝到本機的全域 `python3`**；全部測試以 scratchpad 的 Python 3.12 venv（`requirements.txt` 全裝＋`mcp==2.3.0`）執行 | 本機全域 Python 3.13 已裝 `mcp 1.29.0`，由 `claude-agent-sdk 0.2.135` 以 `mcp<2.0.0` 要求；且已裝的 `sse-starlette 3.4.8` 要求 `starlette>=0.49.1`（與 `fastapi==0.111.0` 衝突，`pip check` 已報）。`pip install mcp==2.3.0` 的 dry-run 會把 Starlette 升到 1.8.0（打壞 FastAPI 釘選）；鎖住 Starlette 時則降 `sse-starlette` 並違反 `claude-agent-sdk` 的約束——兩種都會破壞本 repo 之外的工具。scratchpad venv 與 Dockerfile、CI 同為 3.12，結果對 CI 更具代表性。**全域 `python3` 跑本單元時**：147 案全部載入執行，不需要 SDK 的 119 案照常通過，需要 SDK 的 28 案以 `AssertionError: mcp 版本為 1.29.0，本單元釘選 2.3.0。請在 backend/ 執行：pip install -r requirements.txt` 失敗（不是 skip，也不會讓整個執行中止）。`LOCAL-DEV.md` 已建議在 venv 內安裝 |

## 四、帶入的 37 項：落點

| # | 站別 | ID | 處置 | 落點 | 狀態 |
|---|---|---|---|---|---|
| 1 | functional-design | R-11 | 路線 A：`mcp` 進 `requirements.txt`，同直譯器拓樸；非 SDK 模組不 import `mcp`、`__init__.py` 為空；skip 禁令 | `mcp_topology.py`、`test_mcp_bridge_static.py`（import 邊界、skip 為 0）、第十二節 | 完成 |
| 2 | functional-design | R-12 | 擇 (a)：啟動載入 `allowlist.json` 作為獨立參考 | `startup.py`、`generator.validate_tool_specs`；T-8「`inputSchema` 多一個未宣告屬性」案 | 完成 |
| 3 | functional-design | R-13 | 一律 `.fullmatch()`；`"cost\n"` 等換行案例 | `calls.py`；`test_mcp_bridge_pure`；突變 M08 | 完成 |
| 4 | functional-design | R-14 | 八個類別各一個 `@given`、`derandomize=True`、`database=None` | `test_mcp_bridge_generator.py` | 完成 |
| 5 | functional-design | R-15 | 屏障在記錄包裝內；「token 改存模組變數 → 紅燈」為完成條件 | `mcp_topology.Barrier`；`IdentityIsolationTest`；突變 M09 連跑 4 次皆紅 | 完成 |
| 6 | functional-design | R-16 | C-5 補漏落點與 `U21 → U19` 邊的移除 | ADR-0021 C-5（已核可、已移入） | 紀錄 |
| 7 | functional-design | R-17 | 統一簽名；具名入口 `cli.main`／`startup.load_and_validate` | `app.create_app`、`cli.py`、`startup.py`；startup 測試以 AST 檢查 `__main__.py` | 完成 |
| 8 | functional-design | R-18 | `--host` 預設 `127.0.0.1`；compose 明列 `--host 0.0.0.0` | `cli.py`；compose；突變 M28 | 完成 |
| 9 | functional-design | R-19 | 17-A：直接註冊 `on_call_tool`，SDK 不預先驗證（K-5）；T-2／T-4 斷言 `BR76.1` 形狀、不回顯、恰一行 log | `app.py`；app 測試、e2e `NoLeakTest`／`PathInjectionTest`、dispatch 每分支恰一行 | 完成 |
| 10 | functional-design | R-20 | (1) 四值 `TransportKind`＋封閉聯集，由 `executor.classify_transport_error` 歸類；(2) 擇 (b)：拒收一切 cookie 的 jar | `outcomes.py`、`executor.py`；dispatch 測試；突變 M25 | 完成 |
| 11 | functional-design | R-21 | 問題檔不回改；更正照錄 | 第十節 | 紀錄 |
| 12 | nfr-requirements | R-01 | 自己的 `ConcurrencyGate`、`/healthz` 豁免；判準 ①–⑤；503 非 `BR76.1` 形狀（揭露） | `guards.py`；`ConcurrencyGateTest`；突變 M17、M18 | 完成 |
| 13 | nfr-requirements | R-02 | 同 #1；`NFR21.38` 依路線 A 口徑 | `test_mcp_bridge_static.DependencyRouteTest` | 完成 |
| 14 | nfr-requirements | R-03 | 明文 JWT 由使用者接受；改走專屬網段後同網段竊聽面收窄 | 第十一節第 1 點、`DEPLOY.md` §5.12 | 紀錄 |
| 15 | nfr-requirements | R-04 | `derive_allowed_hosts(port)` 純函式；端到端以實際埠推導；措辭改寫進 §5.12 | `limits.py`；pure 兩案、topology（421）；`DEPLOY.md` §5.12 | 完成 |
| 16 | nfr-requirements | R-05 | 算式已由 nfr-design 更正，不改程式 | — | 紀錄 |
| 17 | nfr-requirements | R-06 | `tool` 只取已宣告名或 `unknown`；413／503／405／408 各恰一行 `request_rejected`；換行注入兩案 | `observability.normalize_tool`、`guards.py`；guards 與 dispatch 測試；突變 M23 | 完成 |
| 18 | nfr-requirements | R-07 | `NFR21.3` 改為「超過時必須留裁決紀錄」，交 build-and-test | 第七節 | 紀錄 |
| 19 | nfr-requirements | R-08 | (1) 簽名同 #7；(2) 枚舉恰四值，`entities.md` 增補寫進第六節；(3) `ResponseTooLarge` → `internal_error`、`retryable: false` | `outcomes.py`；pure `MapOutcomeTest`；第六節 | 完成 |
| 20 | nfr-requirements | R-09 | `stop_grace_period: 15s` 與關係式註解；寫入速率無上限（揭露） | compose；第十一節第 9 點 | 完成 |
| 21 | nfr-requirements | R-10 | `NFR4` 對本單元讀為 N/A（不承擔還原義務） | 第八節 | 紀錄 |
| 22 | nfr-design | R-01 | 405 在閘門之前；`BODY_READ_TIMEOUT_S = 2.0`（408）、`REQUEST_WALL_TIMEOUT_S = 12.0`（503）；名額 `finally` 歸還；三種新 `reason`；GET SSE 與 16 條慢速上傳兩案 | `guards.py`、`limits.py`；guards 測試；突變 M20、M21、M34 | 完成（層序見 D-1） |
| 23 | nfr-design | R-02 | 16-A：不用 shield；判準「行數恰 1」與「慢速 backend 加斷線迴圈後連線池未滿」 | `dispatch.py`；e2e `DisconnectTest` 兩案 | 完成 |
| 24 | nfr-design | R-03 | 17-A 成立，`BR76.3` 字面保住 | `app.py`；app 測試；突變 M26 | 完成 |
| 25 | nfr-design | R-04 | SDK 行為假設總表 | 第十二節（S-1–S-18） | 紀錄 |
| 26 | nfr-design | R-05 | Encryption 改寫為「經使用者接受的例外」 | 第八節、`DEPLOY.md` §5.12 | 完成 |
| 27 | nfr-design | R-06 | `/healthz` 精確比對；`/mcp/*` 先經閘門與本體上限、再 404、不到 SDK | `guards.PathRouter`／`ExactPath`；guards 測試；突變 M22 | 完成 |
| 28 | nfr-design | R-07 | 檔案缺失、非 JSON、編碼錯誤一律 `StartupConfigError` | `startup.py`；startup 三案；突變 M27 | 完成 |
| 29 | nfr-design | R-08 | 17 MiB 稱「緩衝位元組上界」；`512m` 交 build-and-test 以 `docker stats` 量測 | compose 註解、`DEPLOY.md` §5.6；第七節 | 紀錄 |
| 30 | nfr-design | R-09 | 每案 30 秒上限，逾時 `AssertionError`；子進程規定只在路線 C | `mcp_topology.bounded`；topology 測試 | 完成 |
| 31 | infrastructure-design | R-01 | 專屬網段 `mcp`（`internal: true`），成員只有 `backend` 與 `mcp-bridge` | compose；`DEPLOY.md` §5.11、§5.12；`ComposeTest`；突變 M29a／b | 完成 |
| 32 | infrastructure-design | R-02 | 健康步驟不擋部署；改為阻擋的觸發條件機械化；60 秒計入預算 | `deploy.yml`；`DeployWorkflowTest`；`DEPLOY.md` §5.9.1、§5.12；突變 M30、M31 | 完成 |
| 33 | infrastructure-design | R-03 | `DEPLOY.md` 逐行清單＋十→十一；「其餘六個 brain-infra 變數不要加成 secret」與「其餘六個 brain-infra 變數不是 secret」兩句不動（程式審查 R-08：改以句子引用，不寫會隨編修漂移的行號） | `DEPLOY.md`；`DocumentationTest` | 完成 |
| 34 | infrastructure-design | R-04 | 只在路線 C | — | 不適用（路線 A） |
| 35 | infrastructure-design | R-05 | (1) 只在路線 C；(2) 最壞算式見第七節；(3) CC-2 擴及 `__init__.py` 與產生器的傳遞 import | `test_mcp_bridge_static`（`__init__` 為空、純函式與產生腳本的 import 禁令） | 完成 |
| 36 | infrastructure-design | R-06 | `stop` 不持久，持久止損要開 PR | `DEPLOY.md` §5.12 | 完成 |
| 37 | infrastructure-design | R-07 | 預期的 client 路徑、`backend` 不加 `depends_on: mcp-bridge`、呼叫環不構成啟動依賴、host 可達改為部署後實測 | `DEPLOY.md` §5.12；compose `backend` 網段註解 | 完成 |

**計數**（以腳本數本表狀態欄）：37 項，0 項拒絕；「完成」28 項、「紀錄」8 項、「不適用（路線 A）」1 項。

## 五、測試與突變驗證

**執行指令**（`backend/`；直譯器見 D-7）：`PYTHONDONTWRITEBYTECODE=1 python -B -m unittest tests.test_mcp_bridge_generator tests.test_mcp_bridge_pure tests.test_mcp_bridge_guards tests.test_mcp_bridge_dispatch tests.test_mcp_bridge_app tests.test_mcp_bridge_startup tests.test_mcp_bridge_topology tests.test_mcp_bridge_artifacts tests.test_mcp_bridge_e2e tests.test_mcp_bridge_static tests.test_mcp_bridge_deploy` → **Ran 147 tests、OK（約 25 秒；程式審查前為 137 案、約 13 秒）**。加上就緒檢查 `tests.test_requirement_field_http` 為 154 案、OK。`python3 scripts/gen_mcp_tools.py --check`、`python3 scripts/dump_openapi.py --check`（全域與 venv 兩種直譯器）、repo 根目錄的 `validate_repo_contract.py` 與 `validate_env_contract.py` 皆通過。本單元測試結束時還原 logging 狀態（`preserve_logging`），實測執行前後根 logger 與三個 logger 的層級、handler 完全相同。

**突變驗證**（`HYPOTHESIS_NO_SHRINK=1`；腳本在 scratchpad 套用 → 執行指定測試 → 還原；**38 列全紅**）：

| # | 突變 | 對應 | 紅燈的測試 |
|---|---|---|---|
| M01 | 拿掉 `BR72.7` 黑名單檢查 | 性質一 | `test_credential_injected`、`test_renamed_dirty` |
| M02 | 拿掉 `BR72.6` 白名單相等 | 性質五 | `test_whitelist_drift` |
| M03 | `BR72.7` 移到 rename 之前 | 性質一 | `test_renamed_clean`、`test_renamed_dirty`、`test_credential_injected`、repo example 兩案 |
| M04 | `BR72.6` 移到 `BR72.7` 之前 | 性質一 | `test_credential_injected`（只寫進 openapi 的子變體） |
| M05 | 拿掉 `BR72.10` | 性質七 | `test_agent_mismatch` |
| M06 | 拿掉 `BR72.11` | 性質二 | `test_out_of_scope` |
| M07 | `BR75.4` 只用 `quote`、不驗字元集 | 性質六、T-4 | `test_property_six`、`test_required_dot_segment_inputs_rejected`、e2e `test_dot_segments_never_reach_backend` |
| M08 | `.fullmatch()` → `.match()` | R-13 | `test_required_dot_segment_inputs_rejected`（`"cost\n"`） |
| M09 | token 改存模組層變數（**完成條件**） | T-1 | `test_interleaved_reads_keep_identity`（連跑 4 次皆紅） |
| M10 | 錯誤 message 改用 `str(exc)` | T-2 | app `test_no_exception_reaches_the_sdk`、dispatch `test_secret_marker_not_in_result_or_log`、e2e crash 分支 |
| M11 | log 加入參數與標頭 | T-2 | e2e `test_every_branch_and_success_leak_nothing` 等 4 案 |
| M12 | `allowlist.json` 與產物同時加一個屬性 | T-5 | `test_generated_properties_equal_literal_whitelist` |
| M13 | 腳本多讀 `.mcp.json` | T-6 | 讀取封閉兩案 |
| M14 | allowlist 的 `property_patterns` 改一個字元 | T-7 | `test_allowlist_property_patterns_equal_constant` |
| M15 | `calls.SEGMENT_PATTERN` 改一個字元 | T-7 | 兩案 |
| M16a | `validate_tool_specs` 拿掉路徑前綴檢查 | T-8 | `test_membership_path_added` |
| M16b | 拿掉 `requires_agent` 檢查 | T-8 | `test_write_tool_without_requires_agent` |
| M16c | 拿掉黑名單檢查（連同白名單，否則被它擋下） | T-8 | `test_api_key_property_added` 等 2 案 |
| M16d | 拿掉白名單相等 | T-8 | `test_undeclared_input_schema_property` |
| M17 | `ConcurrencyGate` 套在整個應用 | 判準 ③ | `test_healthz_exempt_when_saturated` 等 2 案 |
| M18 | 並行計數改為模組全域 | 判準 ⑤ | `test_instances_independent` |
| M19 | `BodyLimit` 只看 `Content-Length` | `NFR21.20` | `test_chunked_over_limit` |
| M20 | 拿掉本體讀取期限 | nfr-design R-01 | `test_slow_uploads_time_out_and_release_slots` |
| M21 | 拿掉 405 守門 | nfr-design R-01 | `test_get_sse_is_405_without_slot` |
| M22 | 精確路徑改為前綴 | nfr-design R-06 | `test_mcp_subpaths_are_404_and_never_reach_inner` |
| M23 | `tool` 欄寫原值 | nfr-requirements R-06 | app 與 dispatch 共 3 案 |
| M24 | 拿掉 `CredentialContext` 的 `finally` 重設 | `NFR21.28` | `test_reset_after_inner_exception` |
| M25 | cookie jar 改回預設政策 | R-20 | `test_set_cookie_never_stored_or_sent` |
| M26 | （17-A）未知工具改回 `isError` | nfr-design R-03 | `test_unknown_tool_is_protocol_error_without_echo` |
| M27 | `load_and_validate` 不包 JSON 解析錯誤 | nfr-design R-07 | `test_non_json_file` |
| M28 | `--host` 預設改 `0.0.0.0` | R-18 | `test_defaults` |
| M29a | compose 加 `ports:` | infrastructure-design R-01 | `test_no_exposure_and_no_environment` |
| M29b | `networks` 加入 `internal` | 同上 | `test_network_membership` |
| M30 | 健康步驟改用裸露的 `$(docker inspect …)` 指派 | CC-7 | `test_tolerant_shape` |
| M31 | `backend/services/` 出現 `mcp-bridge:8080` 而步驟不改 | infrastructure-design R-02 | `test_blocking_once_a_real_client_exists` |
| M32 | `json_response=False`（16-A 的前提，S-6） | 調整 3 | app 6 案 |
| M33 | `MCP_ROUTE` 改為未實作的路線 | R-11／R-02 | topology 4 案 |
| M34 | 拿掉牆鐘上限 | nfr-design R-01 | `test_wall_clock_timeout` |

計畫表中的「（16-B）名額在取消時就歸還；外層 `finally` 也寫一行」不適用（16-A，沒有 shield 與外層寫出點）；改以 M32 鎖住 16-A 的前提。

**突變過程查出並已修正的兩個測試缺口**：(1) M16a 首輪存活——手改產物加入成員管理項時，`allowlist.json` 的獨立參考先以 `whitelist_mismatch` 擋下，路徑前綴檢查被掩蓋；T-8 該案改為產物與 allowlist **同時**加入，只有前綴檢查擋得下。(2) M16b 首輪使驗證意外通過、真的起了 uvicorn 而卡住；startup 測試改以替身 `server` 模組承接，驗證若意外通過即以「進到了 serve」紅燈。

**已知限制（已由程式審查 R-01 解除）**：原本 M09 只被讀取交錯案抓到、寫入案仍綠，偵測靠排程機率。現改為確定性的交錯點（第十三節 R-01），讀取與寫入兩案在 M09 與新增的 M35 下皆紅，連跑 5 次 15／15 紅。

## 六、設計文字回補（不回改已凍結的設計檔）

| 設計檔 | 原文 | 實作後應讀為 |
|---|---|---|
| `entities.md` | 無 `TransportFailure` | 增列 `ExchangeResult = Received(status, body) \| TransportFailure(kind) \| ResponseTooLarge \| InternalFailure`；`TransportKind` 恰為 `refused`、`timeout`、`dns`、`protocol`（nfr-requirements R-08 (2)） |
| `entities.md` `RequestCredential` | `authorization`、`declared_agent` 兩欄 | 分為 `guards.RawHeaders`（兩個標頭的**全部原值**，放在 `ContextVar`）與 `credentials.RequestCredential`（通過格式檢查的單一值），兩者 `repr` 皆為 `<redacted>` |
| `functional-spec.md` 2.5 | `configure_logging()` 在 `app.py` | 在 `observability.py`（nfr-design 已記） |
| `logical-components.md` §一 | `app.py`「以 `validate_input=False` 註冊工具函式」 | 2.x 無此開關；以 `Server(on_call_tool=…)` 註冊（17-A） |
| `logical-components.md` §一 | `dispatch.py`「`asyncio.shield` 保護 backend 交換」 | 16-A：不用 shield |
| `logical-components.md` §二 | 層序 `ConcurrencyGate` → `BodyLimit` → `CredentialContext` | `MethodGuard` → `ConcurrencyGate` → `WallClock` → `BodyLimit` → `ExactPath` → `CredentialContext`（D-1） |
| `observability-design.md` §一 | `request_rejected.reason` 為 `over_concurrency`／`body_too_large` | 另加 `body_timeout`（408）、`request_timeout`（503）、`method_not_allowed`（405）；另有 `internal_failure` 事件（D-4） |

**取代關係表**（計畫 §五 5.2 ＋ `logical-components.md` §六 ＋ `infrastructure-specification.md`）：

| 已核可字面 | 取代為 | 依據 |
|---|---|---|
| `BR71.2`「只在 internal 網段」 | 只在專屬網段 `mcp`（`internal: true`，成員 `backend`、`mcp-bridge`） | 使用者 2026-10-15T00:38:42Z 對 infrastructure-design R-01 的裁決 |
| `BR71.6`「允許清單只含 `mcp-bridge:8080` 與本機迴環」 | `derive_allowed_hosts(port)`，預設埠時恰為這三項 | nfr-requirements R-04 |
| `BR78.3` 三參數 | 四個必填加 `limits` | functional-design R-17 |
| `BR78.1`／`BR78.2` 第二退路字面 | 不適用（路線 A，原文成立） | Step 1 |
| `BR76.3`（17-B 退路） | 不適用（17-A，原文成立）；補記：未知工具的 HTTP 狀態碼舊式協定版本 200、現代 400 | Step 1 S-3 |
| `NFR21.21`「由 uvicorn 回 503」 | `ConcurrencyGate` 回 503 並記一行 WARNING | nfr-design（已核可） |
| `NFR21.33`「`mcp.server.lowlevel.server` 為 ERROR」 | `mcp` 整體 WARNING（D-5） | Step 1 S-10 |
| `infrastructure-specification.md` §二之一 `networks: [internal]` | `networks: [mcp]` | infrastructure-design R-01 裁決 |
| `infrastructure-specification.md` §四 blast radius（`internal` 成員 4 → 5、`redis`／`ollama`／`db` 可達來源 3 → 4） | `internal` 成員**不變**（4）；`mcp-bridge:8080` 的可達來源只有 `backend`（host 行程待實測） | 同上 |

## 七、交給 build-and-test 的事項

1. **`NFR21.3` 附加時間 P50 ≤ 50 ms**：以 `AC11.4.1`／`AC11.4.3` 的成對呼叫形狀擴充為 50 組量測；超過時必須留裁決紀錄（nfr-requirements R-07）。
2. **記憶體上限 `512m`**：16 個 1 MiB 回應下以 `docker stats` 取峰值（nfr-design R-08）；部署後依 `DEPLOY.md` §5.6 複量。
3. **CI 最壞時間（infrastructure-design R-05 (2)，依案例數重算；程式審查後更新）**：帶 30 秒上限的端到端案例 17 個（e2e 15 ＋ topology 2；兩種協定版本在同一個案例內跑，不使案例數加倍）→ 17 × 30 ＝ 510 秒；`backend` job 既有部分（安裝依賴、既有測試）沿用實測 82–107 秒。最壞合計約 510 ＋ 107 ＝ 617 秒 ≤ 900 秒（`timeout-minutes: 15`），餘裕約 283 秒。實測：本單元 147 案在本機約 25 秒完成。
6. **依賴的可重現性（程式審查 R-07）**：見第十三節 R-07；請在 build-and-test 以 `docker-build` 的實際映像核對 `pip freeze` 中 `mcp`、`mcp-types`、`sse-starlette`、`starlette` 的版本與 Step 1 實測環境一致。
4. **host 可達性**：部署後依 `DEPLOY.md` §5.12 第 4 條指令實測並填寫。
5. **部署後健康步驟的 60 秒**已計入 §5.9.1；兩個無界項剩餘 480 秒仍待實測。

## 八、ADR-0006 四面向

逐格對照上游 `requirements.md:617-620` 與本單元 nfr-design `security-design.md` §九：四格皆「適用」，**無一格相反**。

| 面向 | 判定 | 本單元的處置 |
|---|---|---|
| **IAM** | 適用 | 不新增身分、服務帳號、secret 或 GitHub variable；每次工具呼叫以使用者 token 呼叫既有 API，授權全在 facade（靜態測試：授權函式為 0）；身分只來自每請求的標頭並以 `ContextVar` 隔離（T-1，突變 M09）；拒收 cookie 的 jar（M25）；啟動以獨立參考集合驗證工具宣告（T-8） |
| **Encryption** | 適用——**內容為經使用者接受的例外，不是符合** | 上游要求「本機迴環或加密」，本單元兩者皆非：使用者 JWT 以明文在 `mcp` 網段上往返（使用者 2026-10-14T23:02:07Z 接受）。改走專屬網段後，能在同網段竊聽的容器由 `internal` 的四個成員縮為 `backend` 一個；主機或 `backend` 被攻破時仍可截取。不可逆面（token 進 LLM context）由白名單與底線、手改產物不得啟動、結果與 log 不外洩承擔。靜態：無 volume，不落地任何 token、參數或結果 |
| **Network exposure** | 適用 | 對外（`edge`、host 埠）零新增；新增專屬網段 `mcp`（`internal: true`，斷開 bridge 的出站），bridge 不在 `internal`，`db`／`redis`／`ollama` 不可達它；`--host` 程式預設迴環；Host 允許清單隨實際埠推導（SDK 拒絕為 421）；並行閘、本體上限、本體期限、牆鐘上限、405 守門 |
| **Audit logging** | 適用 | 寫入與清空的稽核主體為使用者本人（e2e 斷言 `updated_by`）；每次工具呼叫恰一行、HTTP 層拒絕各一行、全部單行防注入；成功的讀取無帶使用者身分的紀錄（`OPEN-MB21-14`，已接受）；bridge 與 backend log 無關聯鍵（`OPEN-MB21-9`） |

**PBT hard constraint**：產生器八個類別各一個 `@given`、七條性質，突變 M01–M06 全紅；純函式模組不 import SDK，於 CI 主直譯器執行。

**`NFR4`**：對本單元讀為 **N/A**——bridge 不持有狀態、不承擔還原義務；上游 `traceability.json` 不改（nfr-requirements R-10）。

## 九、ADR-0021 契約增量（C-1..C-5）的落實

| # | 落實 |
|---|---|
| C-1 | `allowlist.json` 宣告 `clear_requirement_field`（`DELETE`、無本體）；e2e 斷言記錄包裝方法為 `DELETE`、`cleared_at` 非空 |
| C-2 | `rename: {field_key: field}`；repo example 斷言工具屬性為 `field`、`binding` 反向映射回 `field_key` |
| C-3 | token 只取自每次請求的 `Authorization`、原樣轉遞；無狀態 streamable HTTP；`X-Cloud360-Agent` 依登錄表填 `on_behalf_of`；bridge 不做授權判定 |
| C-4 | allowlist 恰三個 operation；`ALLOWED_PATH_PREFIXES = ("/api/requirements/",)` |
| C-5 | 程式層無對 `U19` 的任何依賴（靜態測試：不 import `services`、無 `resolve_project_role`）；上游檔的字面以 ADR-0021 為準、不回改 |

## 十、R-21 更正（問題檔由 conductor 擁有、已核可，不回改）

| 位置 | 原文 | 更正 |
|---|---|---|
| `functional-design-questions.md:21` | 引 `stories.md:732` 為「本故事的 Given 今天不可構造」 | 實際位置為 **`stories.md:731`** |
| `functional-design-questions.md:5` | 「故出五題」 | 實際為**六題**（`MB1`–`MB6`） |
| `MB6` 選項 A 標「本站設計預設」 | — | 已作答定案（`[MB6]`=A，2026-10-13T23:08:40Z） |

## 十一、核可關卡須揭露的事項

1. **使用者 JWT 以明文傳輸**（經接受的例外）；同網段竊聽面已收窄為 `backend` 一個容器。
2. **成功的讀取沒有帶使用者身分的紀錄**（`OPEN-MB21-14`）。
3. **記憶體上限 `512m` 是估計**，交 build-and-test 量測。
4. **部署後的 bridge 健康檢查不擋部署**，沒有通知；第一個實際 MCP client 合併時必須改為阻擋，`test_mcp_bridge_deploy` 會在忘記時紅燈。
5. **deploy job 的預算**：新增有界 60 秒，兩個無界項剩 **480 秒**，皆未實測；這 60 秒屬於會觸發 rollback 的預算。
6. **`OPEN-MB21-15`**：`mcp` 與 11 個傳遞依賴（含原生 wheel `cryptography`、`cffi`、`rpds-py`）進入 backend 執行期映像；backend 行程不 import 它們。
7. **兩種協定版本的錯誤語意不同**：未知工具在舊式協定版本是 HTTP 200、現代是 HTTP 400（兩者都是 JSON-RPC `-32602`）；若有未攔截的例外，舊式協定版本會把例外字串原樣送回——本單元以總攔截防住，T-2 兩種版本都測。
8. **HTTP 層拒絕不是 `BR76.1` 形狀**：405、408、413、503 發生在 MCP 協定層之外，各記一行 `request_rejected`。
9. **寫入速率沒有上限**：持有有效 token 的呼叫端在並行 16 之內可不限速率呼叫寫入工具。
10. **止損不持久**：`docker compose stop mcp-bridge` 在下一次部署失效。
11. **host 行程可達性未知**，部署後實測。
12. **bridge log 與 backend log 沒有關聯鍵**（`OPEN-MB21-9`）。
13. **本版沒有實際 client**（`OPEN-MB21-1`）：三條 AC 由測試 client 驗證。
14. **本機全域 Python 未安裝 `mcp==2.3.0`**（D-7）：以全域 `python3` 跑本單元時，需要 SDK 的 28 案以 `AssertionError` 失敗並指出安裝指令（其餘 119 案通過；程式審查前為 23／114）；CI 安裝 `requirements.txt` 不受影響。
15. **牆鐘逾時的語意**（程式審查 R-06，以真實 SDK 實測）：逾時時處理函式與 backend 交換一併被取消、名額同時歸還，client 拿到裸 503（不是 `BR76.1` 形狀），`tool_call` 記為 `internal_error`；已送到 backend 的請求可能在 backend 端照常完成。
16. **傳遞依賴未釘**（程式審查 R-07）：只有 `mcp` 精確釘選；`sse-starlette` 等由 FastAPI 釘選間接約束，其餘仍隨各環境解析。linux amd64 的 wheel 可得性已以乾跑確認（第十三節）。
17. **Python 3.14**：升到 3.14 時 `mcp==2.3.0` 與 `fastapi==0.111.0` 的 Starlette 範圍衝突，路線 A 需重新判定。

## 十二、Step 1 實測紀錄

- 實測時間：2026-10-15（UTC，本節寫入時刻 `2026-10-15T01:06:34Z`）
- 實測環境：一次性 venv，位於 session scratchpad 的 `u21-probe/venv/`（`/opt/homebrew/bin/python3.12` 建立，對齊 `backend/Dockerfile:5` 的 `python:3.12-slim` 與 `ci.yml:255` 的 `python-version: '3.12'`）。安裝內容為 `backend/requirements.txt` 全部加 `mcp==2.3.0`。**未寫入 repo、未裝進本機主環境**。探測腳本 `probe_server.py`、`probe_modern.py`、`probe_k10.py`、`probe_exc.py` 同在該目錄，不進版控。
- 證據強度標記：**實跑**＝實際執行並觀察輸出；**讀碼**＝讀 SDK 原始碼得出、未另行執行。

### 1a. ADR 移入

`adr-0021-draft.md` 已原樣寫成 `inception/decisions/0021-mcp-bridge-x04-contract-increments.md`。以 `diff` 確認只有兩行不同：標題去掉「（草案）」，Status 改為 `Accepted（2026-10-15 隨 U21 code-generation Plan Approval 核可）`。草案檔保留。

### 1b. K-1–K-11 結果

| # | 判定項 | 結果 | 通過 | 強度 |
|---|---|---|---|---|
| K-1 | 解析相容 | 候選版從最新穩定版 `2.3.0` 起試，`pip install --dry-run --ignore-installed --report` 對 `-r backend/requirements.txt mcp==2.3.0` 有解。報告中 `fastapi==0.111.0`、`pydantic==2.13.4` 不變；`starlette==0.37.2`，落在 FastAPI 0.111.0 要求的 `>=0.37.2,<0.38.0` 內；mcp 2.3.0 對 Python < 3.14 只要求 `starlette>=0.27`。與不加 mcp 的基線報告逐套件比對：**既有 87 個套件版本零變動、零移除**，新增 11 個（見下方傳遞依賴清單）。實裝後 `pip check` 回 `No broken requirements found` | 是 | 實跑 |
| K-2 | 無狀態 streamable HTTP | `StreamableHTTPSessionManager(stateless=True, json_response=True)`。`initialize`、`tools/list`（未先 initialize 也可）皆回 `200`、`content-type: application/json`，**全部回應都沒有 `Mcp-Session-Id`**。現代 era（`MCP-Protocol-Version: 2026-07-28`）同樣沒有 | 是 | 實跑 |
| K-3 | Host 檢查 | `TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=[...])`：`Host: evil.example` 回 **421** `Invalid Host header`（兩個 era 都是）；`127.0.0.1:<埠>` 與 `mcp-bridge:8080` 通過 | 是 | 實跑 |
| K-4 | `OPEN-MB21-17` | 2.x 的 lowlevel `Server` 以建構子參數 `on_call_tool=` 直接註冊 `tools/call` 處理函式，沒有裝飾器。處理函式拋 `MCPError(code=-32602, message="Unknown tool")` 時，回應是 **JSON-RPC error，不是 `isError` 結果**，`message` 只有固定字串、不含工具名（測試時刻意用了 `nope_SECRETNAME`）。兩個 era 都成立；HTTP 狀態碼不同：舊式 era **200**、現代 era **400**。官方 SDK client 在兩種模式下都把它當成 `MCPError` 拋出 | 是 | 實跑 |
| K-5 | 預先驗證 | 2.x **沒有 `validate_input` 這個開關**（全 SDK 原始碼零命中），lowlevel 也**不依 `inputSchema` 驗證參數**：`{"system_id": "1\n", "extra": 1}`（違反 pattern 與 `additionalProperties: false`）原樣進到處理函式，兩個 era 都是。SDK 只做信封層檢查：`arguments` 不是物件時，在處理函式之前回 `-32602 "Invalid request parameters"`、`data: ""`，不回顯輸入。17-A 成立，本項不需要 | 不適用（17-A） | 實跑 |
| K-6 | `OPEN-MB21-16` | 處理函式 `await asyncio.sleep(2)`，client 以原始 socket 送出後 0.3 秒關閉連線。**舊式 era**：處理函式未收到 `CancelledError`，正常跑完（`handler_start` 2.111 → `client_closed` 2.412 → `handler_done` 4.112）；內層 ASGI 呼叫 `handle_request` 在處理函式完成之後才返回（`inner_return` 4.112）。**現代 era**：同樣未取消（`handler_start` 0.078 → `client_closed` 0.379 → `handler_done` 2.080 → `inner_return` 2.080） | 觀察值兩項皆記錄 → 16-A | 實跑 |
| K-7 | contextvar 傳遞 | 外層 ASGI 包裝在呼叫 `handle_request` 前設定 `ContextVar`，處理函式讀到本請求的值（`Bearer TOK-K7`、`Bearer SDK-auto`、`Bearer SDK-legacy`、`Bearer MOD`，各案互不混用）。舊式 era 的處理函式跑在 session manager 的 task group 裡，值仍正確傳入；現代 era 的處理函式跑在請求 task 內 | 是 | 實跑 |
| K-8 | GET／DELETE `/mcp` | 舊式 era：`GET` 帶 `Accept: text/event-stream` 回 **200 `text/event-stream`，串流一直不結束**（2 秒內沒有完成，探測端逾時才斷）；`DELETE` 回 405（JSON-RPC 本體 `Session termination not supported`）；`PUT` 回 405。現代 era 的 `GET` 回 405、空本體。**結論：SDK 原生行為會讓一個 GET 長期佔住連線**，本設計在 `ConcurrencyGate` 之前擋 405 是必要的，不是多餘的防禦 | 已記錄 | 實跑 |
| K-9 | lifespan | 沒有進入 `session_manager.run()` 時，`handle_request` 拋 `RuntimeError: Task group is not initialized. Make sure to use run().`，回 500。`create_app` 必須在 ASGI lifespan 內以 `async with session_manager.run():` 包住服務期間；`run()` 一個實例只能進一次 | 已記錄 | 實跑＋讀碼 |
| K-10 | dns 例外鏈 | `httpx` 0.28.1 連 `backend.invalid`：`httpx.ConnectError` → `httpcore.ConnectError` → **`socket.gaierror`**（經 `__cause__`／`__context__` 可達）。對照組連 `127.0.0.1:1`：鏈上是 `ConnectionRefusedError`，沒有 `gaierror`。`classify_transport_error` 以「沿 `__cause__`／`__context__` 走訪是否有 `socket.gaierror`」判定 `dns` 可行 | 是 | 實跑 |
| K-11 | 路徑遮蔽 | 在 `backend/` 以 probe venv 的直譯器 `import tests.helpers`（其 `:27-31` 把 `backend/services` 與 `backend/` 插到 `sys.path` 最前），之後 `import mcp`、`mcp.server.lowlevel`、`mcp.server.streamable_http_manager`、`mcp_types`、`from mcp import Client` 全部解析到 site-packages。另以腳本比對 `backend/` 與 `backend/services/` 的頂層模組名和 venv 的全部頂層模組名，**交集為空** | 是 | 實跑 |

### 選定版本與路線

| 項目 | 結論 |
|---|---|
| 依賴路線 | **A**（最新候選版 `2.3.0` 通過 K-1–K-3） |
| 版本 | `mcp==2.3.0`（`2.2.0`、`1.30.0` 也有解，但 A 的條件是最新候選版通過，故不往下找） |
| `MCP_ROUTE` | `"same-interpreter"` |
| 需要使用者同意 | **否**（不是 C／D，也不是 17-B） |

後續差異（照計畫依賴路線分支表）：Step 9 不改 Dockerfile；Step 10 只做 S-1、S-2；不建 `mcp_wire_client.py`、不建 `requirements-mcp.txt`。

### 傳遞依賴清單（`OPEN-MB21-15` 的供應鏈面）

以 `pip --dry-run --report` 的兩份報告（基線、加 `mcp==2.3.0`）逐套件比對得出：

| 新增套件 | 版本 | 授權 | 備註 |
|---|---|---|---|
| `mcp` | 2.3.0 | MIT | 本體 |
| `mcp-types` | 2.3.0 | MIT | 2.x 拆出的型別套件，`mcp` 以 `==` 綁定同版 |
| `sse-starlette` | 3.0.3 | BSD-3-Clause | |
| `jsonschema` | 4.26.0 | MIT | |
| `jsonschema-specifications` | 2025.9.1 | MIT | |
| `referencing` | 0.37.0 | MIT | |
| `rpds-py` | 2026.9.1 | MIT | 原生 wheel（Rust） |
| `attrs` | 26.1.0 | MIT | |
| `cryptography` | 50.0.2 | Apache-2.0 OR BSD-3-Clause | 原生 wheel；由 `mcp` 要求的 `pyjwt[crypto]` extra 帶入 |
| `cffi` | 2.1.1 | MIT-0 | 原生 wheel；`cryptography` 的依賴 |
| `pycparser` | 3.11 | BSD-3-Clause | |

- **既有套件版本零變動**。`mcp` 另外要求的 `httpx2`、`opentelemetry-api`、`python-multipart`、`uvicorn`、`pydantic`、`anyio`、`pyjwt`、`starlette` 都已經在基線裡（`httpx2` 由 `anthropic`、`openai`、`langsmith` 帶入），不算新增。
- 新增套件只出現在 backend 映像的 site-packages；backend 進程本身不 import 它們（由 Step 10 的靜態測試鎖住）。

### `OPEN-MB21-17` 分支：**17-A**

依據 K-4：以 `Server(..., on_call_tool=...)` 直接註冊處理函式，未知工具拋 `MCPError(code=-32602, message=<固定訊息>)`，兩個 era 都回 JSON-RPC 協定錯誤，`BR76.3` 字面保住。計畫列的三個繞路一起取消：

1. 不用 `validate_input`（2.x 本來就沒有）。
2. 處理函式只呼叫總攔截過的 `run_tool_call`。**這一點在 2.x 是承重的，不是保險**：見下方假設總表 S-9，舊式 era 下未攔截的例外會把 `str(exc)` 原樣送上線。
3. 計畫寫的 `mcp.server.lowlevel.server` logger 在 2.x 不是記錄處理函式例外的那一個；實際是 `mcp.shared.jsonrpc_dispatcher`（舊式 era）與 `mcp.server.runner`（現代 era）。17-A 之下不需另設 ERROR，但注入案例仍須通過（見 S-10）。

### `OPEN-MB21-16` 分支：**16-A**

依據 K-6：兩個 era 下，處理函式都不會因 client 斷線而被取消，且內層 `handle_request` 都等處理函式完成才返回。照計畫：不用 `asyncio.shield`；閘門在 `finally` 歸還名額時交換已結束，CC-6 自然成立；`tool_call` 那一行照常由 `run_tool_call` 的 `finally` 寫出。

**前提**：此結論只在 `json_response=True` 下實測。讀碼可見現代 era 在**非** JSON 模式會另起 `watch_disconnect`，收到 `http.disconnect` 即取消處理函式（`mcp/server/_streamable_http_modern.py` 的 SSE 分支）。所以 `json_response=True` 是 16-A 成立的前提，應由 Step 4 的測試鎖住（見假設總表 S-6）。

### SDK 行為假設總表（#25，nfr-design R-04）

所釘版本：`mcp==2.3.0`／`mcp-types==2.3.0`，`starlette==0.37.2`，Python 3.12。升 `mcp` 任一版都要重跑 K-1–K-11。

| # | 假設 | 所釘版本的實測結果 | 判準 | 所走退路／對應處置 |
|---|---|---|---|---|
| S-1 | 無狀態模式不發 `Mcp-Session-Id` | 兩個 era 都沒有 | K-2、`BR71.2` | 無需退路 |
| S-2 | Host 檢查可由設定開啟並拒絕不在清單的 Host | 拒絕，狀態碼 **421** | K-3、`BR71.6` | 測試斷言 421（不是 400／403） |
| S-3 | 可直接註冊 `tools/call` 處理函式，未知工具回協定錯誤 | 成立；舊式 200、現代 **400** | K-4、`BR76.3` | 17-A；測試不得以 HTTP 200 判定 `BR76.3` |
| S-4 | SDK 不依 `inputSchema` 預先驗證參數 | 成立（不合格參數原樣進處理函式） | K-5、R-19 | 驗證完全由 `calls.py` 承擔；T-2／T-4 的不合格案例會實際到達 `run_tool_call` |
| S-5 | 處理函式讀得到外層設定的 `ContextVar` | 兩個 era 都成立 | K-7 | 無需退路；R-15 的屏障測試照計畫 |
| S-6 | client 斷線不取消處理函式，內層等處理函式完成才返回 | 兩個 era 都成立，**僅限 `json_response=True`** | K-6、`OPEN-MB21-16` | 16-A；`json_response=True` 由 Step 4 測試斷言 |
| S-7 | 非 POST 的 `/mcp` 方法由本設計在閘門前擋掉 | SDK 原生：舊式 era 的 GET（SSE）**串流不結束**；DELETE／PUT 405 | K-8、nfr-design R-01 | `MethodGuard` 必須在 `ConcurrencyGate` 之前，否則一個 GET 會永久佔一個名額 |
| S-8 | session manager 需在 lifespan 內 `run()`，且只能一次 | 未 `run()` 時 500 `RuntimeError` | K-9 | `create_app` 以 ASGI lifespan 包 `run()`；每個 `create_app` 建新的 manager |
| S-9 | 處理函式拋出的非 `MCPError` 例外不外洩 | **不成立**：舊式 era 回 `{"code": 0, "message": str(exc)}`，**原樣回顯例外字串**（實測 `SECRET-{"x": "INJ\nECT"}` 上線）；現代 era 回 `-32603 "Internal server error"` | R-19、T-2 | `run_tool_call` 的 `except Exception` 總攔截是唯一防線；T-2 必須在**舊式 era** 斷言 message 不回顯 |
| S-10 | SDK 的 log 不寫入未跳脫的使用者內容 | 處理函式例外時，`mcp.shared.jsonrpc_dispatcher`／`mcp.server.runner` 以 `logger.exception` 寫多行 traceback（含例外字串）；`mcp.server.transport_security` 的 WARNING 含原始 Host 值 | `NFR21.8`、R-06 | 總攔截使前兩者不觸發；`BridgeFormatter` 掛在 root handler，對 SDK logger 一樣生效 |
| S-11 | SDK 每請求的 INFO log 不干擾行數判準 | 舊式 era 每請求有 `mcp.server.streamable_http` 的 `Terminating session: None`（INFO）；啟停時 `mcp.server.streamable_http_manager` 各一行 INFO | 「`tool_call` 行數恰 1」 | `configure_logging` 把 `mcp` logger 設為 WARNING；行數判準只計本單元 logger |
| S-12 | SDK 自帶的本體上限與 Content-Type 檢查不搶在本設計之前 | SDK 自帶 4 MiB 上限（413）與 POST 必須 `application/json`（400）；兩者都在 `handle_request` 內，位於本設計的 `BodyLimit` 之後 | `NFR21` 本體上限、R-06 | 建 manager 時 `max_request_body_size` 設為不小於本設計的上限，讓 413 一律由 `BodyLimit` 判定並留 `request_rejected` |
| S-13 | 現代 era 的 `tools/call` 不額外呼叫業務邏輯 | **讀碼**：參數非空時，SDK 為驗證 `Mcp-Param-*` 標頭會先查工具 schema；沒提供 `get_tool_input_schema` 時就**呼叫 `tools/list` 處理函式**一次 | 效能、`tools/list` 呼叫次數 | `Server(..., get_tool_input_schema=...)` 以 `tool_specs` 的純查表提供 |
| S-14 | 官方 client 的預設模式會走到本設計 | `Client(mode="auto")` 協商到 **`2026-07-28`（現代 era）**；`mode="legacy"` 協商到 `2025-11-25`。兩者經 `streamable_http_client(url, http_client=httpx2.AsyncClient(headers=...))` 都能帶 `Authorization` 與 `X-Cloud360-Agent` | `BR78.1` | 測試 client 兩個模式都要跑（見下方「與計畫不符處」第 1 點） |
| S-15 | SDK 預設中介層不產生副作用 | **讀碼**：`Server.middleware` 預設含 `OpenTelemetryMiddleware`，沒有 exporter 時為 no-op；`opentelemetry-api` 已在基線 | `NFR21.40` | 不處理；不安裝 exporter |
| S-16 | `socket.gaierror` 在 httpx 例外鏈上可達 | 成立 | K-10 | `classify_transport_error` 沿 `__cause__`／`__context__` 走訪 |
| S-17 | 同直譯器下 `mcp` 不被遮蔽、不影響 backend | K-11 成立；probe venv 下 `tests.test_requirement_field_http` 7 案 OK，`scripts/dump_openapi.py --check` 回「規格檔與後端程式碼一致」 | K-11、CC-1 | 無需退路 |
| S-18 | 解析結果不受 Python 小版本影響 | **讀碼**：`mcp` 在 Python ≥ 3.14 要求 `starlette>=0.48.0`，與 `fastapi==0.111.0` 的 `<0.38.0` 衝突 | K-1 | 目前 Dockerfile 與 CI 都是 3.12，本機 3.13 也 < 3.14，不受影響；**日後升 Python 到 3.14 時路線 A 會失效**，寫進 `requirements.txt` 的註解 |

### 執行的驗證

- `backend/` 下 `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_requirement_field_http -v`（本機主環境 Python 3.13.7）：`Ran 7 tests … OK`。
- 同一指令以 probe venv（3.12＋全部依賴＋`mcp==2.3.0`）再跑一次：`OK`。
- 同一 venv 執行 `scripts/dump_openapi.py --check`：一致、exit 0。
- 前後以 `git status --porcelain --untracked-files=all backend/` 比對：**repo 內沒有新增或改動任何檔**。

### 與計畫不符、已於中途關卡核可的事項

計畫是按 SDK 1.x 的命名寫的；實測版本是 2.x。使用者於中途關卡核可路線 A、17-A、16-A，並採納下列四點調整（落實見第二節）：

1. **兩個協定 era**：2.x 的 `handle_request` 依 `MCP-Protocol-Version` 標頭分流，現代 era（`2026-07-28`）走另一條程式路徑，而官方 client 的預設模式就是它。兩條路徑都在本設計的外層包裝之內，所以閘門、本體上限、Host 檢查、`ContextVar` 都對兩者生效（K-3、K-7 實測）。但錯誤的 HTTP 狀態碼不同（S-3），未攔截例外的外洩行為也不同（S-9）。**建議**：`BR78.1` 的測試 client 與 T-2、T-4、`AC11.4.1`／`AC11.4.3` 的端到端案例，在 `mode="legacy"` 與 `mode="auto"` 下各跑一次；T-2 的「message 不回顯輸入」至少要有舊式 era 的案例。這會讓端到端案例數加倍，影響 infrastructure-design R-05 的 CI 最壞算式。
2. **計畫字面的 SDK 名稱**：`call_tool` 裝飾器、`validate_input`、`mcp.server.lowlevel.server` logger 在 2.x 都不存在或不是同一個東西。17-A 之下前兩者本來就不用；第三者改為 S-10、S-11 列的 logger。程式照實際名稱寫，code-summary 照錄，不回改計畫。
3. **Step 4 增列兩項接線**：`Server(..., get_tool_input_schema=...)`（S-13）與 manager 的 `max_request_body_size` 不小於本設計上限（S-12）；`configure_logging` 增列 `mcp` logger 設 WARNING（S-11）。
4. **`team.md` 的過期記載**：`team.md` 的 Code Style 寫 `fastapi[standard]==0.141.1`，但 `backend/requirements.txt:8` 實為 `fastapi==0.111.0`（本分支與 `origin/ut` 相同）。K-1 以實際檔案為準。本單元不改 `team.md`。

## 十三、程式審查處置（`reviews/review-01.md`，使用者裁決「這批一起修」）

十項全部照 Required action 處置，0 項拒絕；R-04 的前提有一處與實測不符，處置方式不變（見該列）。

| ID | 處置 | 落點 | 驗證 |
|---|---|---|---|
| R-01（Major） | (1) **確定性交錯點**：`create_app` 增加只供測試的 `call_hook` 參數（正式啟動不傳、為 `None` 時無作用），在工具處理函式**讀取身分材料之前** await；`CallHookBarrier` 讓 owner 的每個呼叫等到 outsider 有一個**新**的呼叫抵達同一點才放行——那時 outsider 的 contextvar 已設定好，若身分材料存在模組變數，owner 這一回合必定讀到 outsider 的值。測試斷言成功安排的回合數 ≥ 10，不再依賴排程機率。原本掛在 backend 包裝內的單發 `Barrier` 移除。(2) **寫入變體**改用同一個交錯點、兩種協定版本都跑。(3) **agent 隔離**：owner 宣告 `cost`、outsider 宣告 `architecture`；記錄包裝擷取每個請求的本體，逐筆斷言 `PUT` 的 `on_behalf_of` 屬於該使用者宣告的 agent，持久列的 `updated_by`／`updated_on_behalf_of` 也逐一斷言 | `app.py`（`call_hook`）、`tests/mcp_topology.py`（`CallHookBarrier`、`RecordingBackend.bodies`）、`test_mcp_bridge_e2e.IdentityIsolationTest` | 突變 M09（讀取）、**M09w**（寫入）、**M35**（agent 改存模組變數）皆紅，三者連跑 5 次共 15／15 紅，每次兩種協定版本都紅 |
| R-02 | `REQUEST_WALL_TIMEOUT_S` 由 12 秒改為 **13 秒**：本體期限 2 ＋ backend 整體上限 10 ＋ 1 秒餘裕；`stop_grace_period` 關係式改為 13 ＋ 1 ＝ 14 < 15（compose 註解、`DEPLOY.md` §5.12 同步）；pure 測試改為嚴格大於，另斷言 ≥ 2 ＋ 10 ＋ 1 | `limits.py`、compose、`DEPLOY.md`、`test_mcp_bridge_pure` | 突變 **M38**（改回 12 秒）紅 |
| R-03 | 斷線迴圈改為 24 條連線、backend 慢 0.5 秒、送出後 0.2 秒斷線；`ConcurrencyGate` 增加只供觀測的 `peak`；斷言峰值＝上限 16、抵達 backend 的請求數 ≥ 16、`tool_call` 行數＝抵達數、名額歸零、至少一筆 `over_concurrency`、之後的正常呼叫成功 | `guards.py`（`peak`）、`DisconnectTest` | 突變 **M36**（名額從不歸還）、**M37**（名額在交換結束前就歸還）皆紅 |
| R-04 | (a) `serve_until_stopped` 回傳是否曾啟動，失敗時記一行 `startup_failed subject="lifespan"`，`_run` 回傳 1。**前提更正**：審查寫「uvicorn 在 lifespan 啟動失敗時正常返回、退出碼 0」——所釘環境的 uvicorn 0.54 實際是在 `serve` 內 `sys.exit(3)`（`uvicorn/server.py:118`），而且從 asyncio task 拋出的 `SystemExit` 會讓整個事件迴圈中止。uvicorn 未釘版，兩種形狀都在 task 的協程內收斂。(b) `cli.main` 檢查 `--port`（1–65535）與 `--max-concurrency`（≥ 1），範圍外走單行 `startup_failed` 並回傳 1 | `server.py`、`cli.py`；`test_mcp_bridge_app.LifespanFailureTest` 兩案、`test_mcp_bridge_startup` 三案 | 突變 **M39**（失敗仍回報成功）、**M40**（不檢查 `--port`）皆紅 |
| R-05 | 兩層：`dispatch._execute` 在總攔截之內先以與 app 相同的參數 `json.dumps` 成功本體（失敗即 `internal_error`，log 與回應一致）；`app.on_call_tool` 以 `try` 包住 `to_call_tool_result`，例外時記 `internal_failure` 並回一個不經該函式組出的固定 `internal_error` 結果 | `dispatch.py`、`app.py`；`test_result_serialization_failure_is_internal_error`（兩種協定版本，斷言回應與 log 不含例外字串） | 突變 **M41**（拿掉 app 層的攔截）紅 |
| R-06 | 以真實 SDK 拓樸實測牆鐘逾時：**兩種協定版本下，處理函式與 backend 交換都隨外層呼叫被取消**；回應 503 時名額已歸零、恰一行 `tool_call`（`internal_error`、`http_status` 為 `null`），等過 backend 延遲後沒有第二行、記錄包裝只有 1 筆。所以名額歸還時沒有仍在跑的處理函式，閘門上限不會被逾時的處理函式突破。**揭露**：已送到 backend 的請求可能在 backend 端照常完成（寫入與清空皆冪等），只是結果送不回去 | `test_mcp_bridge_e2e.TransportBehaviourTest.test_wall_clock_timeout_cancels_handler_with_real_sdk` | 測試綠；此為觀察型判準，未另設突變（行為由 SDK 決定，本單元沒有可改壞的對應程式） |
| R-07 | **不建 constraints 檔**（依派工：揭露並交 build-and-test 驗證）。實測：在 scratchpad 以 `pip install --dry-run --only-binary=:all: --platform manylinux_2_28_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux2014_x86_64 --python-version 3.12 --implementation cp --abi cp312 -r backend/requirements.txt` 對 linux amd64 解析，**98 個套件全部取得 wheel**、退出碼 0，版本與 Step 1 的 macOS 報告逐一相同；原生套件為 `cryptography-50.0.2-cp311-abi3-manylinux_2_28_x86_64`、`cffi-2.1.1-cp312-cp312-manylinux2014_x86_64`、`rpds_py-2026.9.1-cp312-cp312-manylinux2014_x86_64`。`manylinux_2_28` 需要 glibc ≥ 2.28，`python:3.12-slim`（Debian bookworm，glibc 2.36）滿足——這一點是依映像基底推論，未在容器內執行。**仍存在的漂移面**：`mcp-types` 由 `mcp` 以 `==2.3.0` 綁定，不會漂；`sse-starlette` 只要求 `>=3.0.0`，目前解析為 3.0.3 是因為較新版要求 `starlette>=0.49.1` 而被 `fastapi==0.111.0` 擋下——FastAPI 釘選間接約束了它，但其餘傳遞依賴仍隨 CI／Docker／staging 各自解析。升版仍須重跑 K-1–K-11 | 本節；第七節第 6 點 | — |
| R-08 | 第一節與第四節第 33 列改以句子引用（「其餘六個 brain-infra 變數不要加成 secret」「其餘六個 brain-infra 變數不是 secret」），不寫行號。現況兩句位於 `DEPLOY.md:1336` 與 `:1915` | 本檔 | — |
| R-09 | 觸發條件掃描放寬：範圍為 `backend/`（`mcp_bridge/` 與測試除外）、`frontend/`（`node_modules` 等除外）、根目錄 `scripts/`、`deploy/`（定義服務本身的 compose 檔除外）；檔型含程式、JSON、YAML、shell、設定與 `.env*`；比對形狀為服務名 `mcp-bridge`（任何埠）或 `:8080/mcp`，以 lookbehind 排除單元名稱敘述「U21 mcp-bridge」。`DEPLOY.md` §5.12 增加人工檢查項（掃描比對不到的寫法，例如以變數拼出服務名） | `test_mcp_bridge_deploy.scan_for_mcp_clients`、`DEPLOY.md` §5.12 | 突變 M31（backend `.py`）、**M45**（frontend `.ts`、非 8080 埠）、**M46**（`deploy/` 的 `.env`、`:8080/mcp`）皆紅 |
| R-10 | `validate_tool_specs` 增加三項比對：binding 內每個映射的 API 名稱等於由 allowlist 的 `rename` 反推的值、且不得是被剝除的欄位；`inject` 等於 allowlist 的 `inject`；屬性 `pattern` 等於 allowlist 的 `property_patterns` | `generator.py`；`test_mcp_bridge_startup` 四案（inject 被移除、`body_params` 值改成 `on_behalf_of`、`path_params` 映射被改、pattern 被移除） | 突變 **M42**（不比 inject）、**M43**（不比映射）、**M44**（不比 pattern）皆紅 |

**新增突變列（13 列，全紅）**：M09w、M35、M36、M37、M38、M39、M40、M41、M42、M43、M44、M45、M46——其中 M09w 為 M09 在寫入案例的對應列。以腳本計數，合計突變 51 列、51 列紅；既有 38 列在本輪修改後重跑仍全紅。

**測試數變化**：137 → 147（app ＋3：序列化攔截、lifespan 失敗兩案；startup ＋6：R-10 四案、`--port`、`--max-concurrency`；e2e ＋1：牆鐘取消；T-1 寫入案名稱改為 `test_interleaved_writes_keep_identity_and_agent`）。

## 十四、合併前必修第 7、8 項（計畫 §八 Step 15–17，2026-10-24）

來源：`construction/functional-design/merge-blockers.md` 第 7、8 列（皆屬 ADR-0006）。使用者 2026-10-24 於本站逐項裁決。

### 兩項裁決

| 項 | 裁決 | 程式變更 |
|---|---|---|
| 第 7 項（Encryption） | **沿用 2026-10-14T23:02:07Z 的裁決結案**（`nfr-design/security-design.md:83-84`）。bridge 只在專屬網段 `mcp`（`deploy/docker-compose.deploy.yml:446` 的 `networks: [mcp]`；`:485-486` 的 `mcp:`／`internal: true`），成員只有 `backend` 與 `mcp-bridge`，無 `ports:`；backend 目前沒有程式呼叫 bridge（`OPEN-MB21-1`）。這是對 `requirements.md:618`「本機迴環或加密」的**例外**，不是符合；殘餘風險：同主機上被入侵且位於 `mcp` 網段內的容器（目前只有 `backend`）可竊聽 token。第十一節第 1 項的揭露維持 | 無 |
| 第 8 項（Audit logging） | **推翻 `[MBN1]`=A**：成功讀取補一行帶使用者身分的 log，使 `requirements.md:620` ③「稽核主體必須是使用者本人」在讀取面也成立 | 見下 |

**取代**：第八節 Audit logging 列中「成功的讀取無帶使用者身分的紀錄（`OPEN-MB21-14`，已接受）」、第十一節第 2 項，以及計畫 §六 第 2 項與 `OPEN-MB21-14` 的結案理由，自本節起由下面的實作取代。上述原文不回改。

### Step 15 — 實作（跨單元，`U20` 已交付檔）

- `backend/services/requirement_field_facade.py`：`read_fields` 在 `_authorize` 通過、`fetch_rows` 與 `compose_field_set` 之後呼叫新增的 `_log_read(principal, known_id)`；`_log_read` 記一行 INFO `requirement_field.read system_id=%s user_id=%s on_behalf=%s`，`extra` 帶 `story_id`（`K4`）、`action="view"`、`system_id`、`user_id`、`on_behalf`。`read_fields` 簽章沒有代寫參數，故 `on_behalf` 固定 `False`。
- `system_id` 取授權後的 `known_id`（整數），不是輸入原值；不記欄位值、欄位 key 清單、使用者原句、token。被拒讀取維持只有 `_deny` 那一行。logger 沿用模組既有的 `"cloud360.requirement_fields"`。模組 docstring 的 log 段同步列入 `.read`。
- 不改回傳、不改授權、零 DDL、零新環境變數。`git diff --stat` 該檔：`27 +++++++++-`。

### Step 16 — 測試

| 案例 | 落點 | 斷言 |
|---|---|---|
| R1 | `tests/test_requirement_field_facade.py::test_R1_successful_read_logs_reader_identity_once` | `system_id` 以字串傳入；恰一筆 `requirement_field.read`，(`story_id`, `action`, `system_id`, `user_id`, `on_behalf`) ＝ (`K4`, `view`, 整數系統 id, editor, False) |
| R2 | `…::test_R2_read_log_never_carries_field_values` | 以 `uuid4()` 標記寫入後讀取：回傳含標記；讀取期間所有 record 的訊息與 `__dict__` 不含標記 |
| R3 | `…::test_R3_denied_read_logs_only_the_denial` | outsider（非成員）讀取：log 恰為 `["requirement_field.denied"]`（reason＝`not_member`），`requirement_field.read` 0 筆 |
| R4 | `tests/test_mcp_bridge_e2e.py::AcceptanceTest.test_ac11_4_3_member_read_equals_direct_get` | 兩種協定版本（`MODES`）經 MCP 讀取期間，backend 端的 `requirement_field.read` 為 `[(owner.id, system.id)] × len(MODES)` |

**前置**：在 `backend/` 執行 `python3 -m pip install -r requirements.txt`，`mcp` 由 1.6.0 升為 2.3.0（`python3 -m pip show mcp`）。pip 回報一項與本 repo 無關的全域衝突：`claude-agent-sdk 0.2.135 requires mcp<2.0.0,>=1.23.0`。R4 因此**已實際執行**，不是未驗證。

**執行結果**（皆在 `backend/`，`HYPOTHESIS_STORAGE_DIRECTORY` 指向 scratchpad、`PYTHONDONTWRITEBYTECODE=1 python3 -B`）：

| 指令 | 結果 |
|---|---|
| `-m unittest tests.test_requirement_field_facade -v` | `Ran 11 tests`、`OK` |
| `-m unittest tests.test_requirement_field_facade tests.test_mcp_bridge_e2e` | `Ran 26 tests`、`OK` |
| 本單元全部 11 個 `test_mcp_bridge_*` 模組（`unit-test-instructions.md` 第二節「全單元」指令） | `Ran 147 tests`、`OK` |
| `-m unittest discover -s tests` | `Ran 1313 tests`、`OK (skipped=3)`；`grep -cE "^(FAIL\|ERROR): test"` 為 0 |
| `scripts/dump_openapi.py --check` | `規格檔與後端程式碼一致。`（不漂移） |
| `scripts/gen_mcp_tools.py --check` | `MCP 工具宣告與輸入一致。` |
| repo 根目錄 `python3 scripts/validate_repo_contract.py` | `Cloud-360 repository contract validation passed.` |
| repo 根目錄 `python3 scripts/validate_env_contract.py` | `Cloud-360 environment configuration contract validation passed.` |

`skipped=3` 不在本單元測試檔內（`test_mcp_bridge_static` 斷言本單元 skip 為 0，且在上表 147 案中為綠）。

### 突變驗證（scratchpad 腳本 `mb_mutate.py`，`HYPOTHESIS_NO_SHRINK=1`；每項：套用 → 跑 R1–R4 → 還原 → sha256 對照基線）

基線 sha256（`shasum -a 256 services/requirement_field_facade.py`）：`f3900ca36f4aa59d743a8f7eb3b6225c2ef59f2a763d2cf7d434fabb5c1c9cf6`。

| 突變 | 內容 | R1 | R2 | R3 | R4 | 預期紅燈是否命中 | 還原後 sha256 ＝ 基線 |
|---|---|---|---|---|---|---|---|
| M-A | 拿掉 `read_fields` 中的 `_log_read` 呼叫 | 紅 | 紅 | 綠 | 紅 | 是（預期 R1、R4） | 是 |
| M-B | `_log_read` 的 `extra` 加入 `values=[r.value for r in rows]` | 綠 | 紅 | 綠 | 綠 | 是（預期 R2） | 是 |
| M-C | 改在 `_authorize` 之前以輸入原值記 log | 紅 | 綠 | 紅 | 紅 | 是（預期 R3） | 是 |

還原後 R1–R4 一次重跑：`OK`、退出碼 0。M-A 下 R2 也紅，是因為 R2 先斷言恰一筆讀取 log；M-C 下 R1／R4 也紅，是因為 log 的 `system_id` 變成輸入的字串而非授權後的整數。

### Step 17 — 文件與追溯

- `merge-blockers.md` 第 7、8 列的處置欄由「待處置」改為本節的裁決與落點（只改該儲存格）。
- `source-manifest.json`：`writes` 由 39 筆增為 41 筆，加入 `backend/services/requirement_field_facade.py`、`backend/tests/test_requirement_field_facade.py`（`backend/tests/test_mcp_bridge_e2e.py` 原已在列）。
- `traceability.json`：`upstream_ids` 與 `coverage` 由 89 筆增為 90 筆，新增 `FR11.6`（note 限定為 `requirements.md:620` ③ 的讀取面，target 為 facade 測試檔）；`reverse` 由 10 筆增為 11 筆，新增 `CG-READ-AUDIT`（target 為 facade）。

## 重做（Code Generation 自頭重來，2026-10-25）

<!-- 寫入時間：2026-10-26T01:31:10Z -->

以既有實作逐步查驗已核可計畫，未修改任何程式碼。計畫的 17 步為 `### Step N` 標題、無勾選框，故計畫檔不變，逐步判定記於此。

- **逐步判定**：Step 1、2、4–13、15、16 符合；Step 3、14、17 部分符合：
  - Step 3：層序為 PathRouter → MethodGuard → Gate → WallClock → BodyLimit → ExactPath → CredentialContext（牆鐘與本體上限對調為既記 D-1）。**「MethodGuard 排在並行閘門之前」（計畫 #22）沒有測試鎖住**：在 scratchpad 副本把 MethodGuard 移到閘門之內，guards 12 案與 app／e2e／topology／static 47 案全綠——`test_get_sse_is_405_without_slot` 只在回應結束後斷言 `in_flight == 0`，名額於 `finally` 歸還，順序對調後仍成立；M21 測的是拿掉 405 守門而非順序。
  - Step 14：本摘要有過時處（見下）。
  - Step 17：merge-blockers 第 7、8 列為整格替換「待處置」，非計畫字面的純 append；內容正確。
- **Step 1 中途關卡**：路線 A（`mcp==2.3.0`、`MCP_ROUTE="same-interpreter"`）、17-A、16-A，均不需另取同意；16-A 只在 `json_response=True` 下實測。ADR-0021 已移入 `inception/decisions/0021-mcp-bridge-x04-contract-increments.md`，Status Accepted，與草案只差兩行。
- **測試**（`backend/`，快取導向 scratchpad；前後比對 repo 內 583 個快取檔 mtime 無變化）：
  - 全套 1319 OK（skipped=3）。
  - 本單元 11 支共 147 OK（generator 11、pure 25、guards 12、dispatch 13、app 10、startup 19、topology 5、artifacts 8、e2e 15、static 17、deploy 12），零 skip。
  - `test_requirement_field_facade`＋`_http` 21 OK；`gen_mcp_tools.py --check`、`dump_openapi.py --check`、`validate_repo_contract.py`、`validate_env_contract.py` 皆通過。
  - 突變抽驗（scratchpad 副本，未寫回）：#12 閘門永不拒絕、#31 改掛 `internal`、#32 拿掉 `continue-on-error` 皆紅→還原綠；#22 順序對調**未轉紅**（見上）。
- **合併前必修第 7、8 項**：第 7 項裁決結案、現況與敘述一致；第 8 項 `_log_read` 已實作（授權後、用授權後的 `known_id`、不記值），R1–R3、R5 與 e2e R4 皆綠。
- **第 14 項對本單元的影響**：非成員經 MCP 讀取現為 `not_found`；e2e AC11.4.1 已改斷言，`forbidden` 分支改由缺 K4 的成員承擔。本輪已就地更正 `traceability.json` 的 AC11.4.1 note；計畫 §四 仍寫 `forbidden`（已核可，不改）。
- **PBT**：`test_mcp_bridge_generator.py` 八個類別各一個 `@given`（第 191–294 行），pure 另 1 個（性質六）。
- **ADR-0006 四面向**：與第八節一致；Audit logging 格的「成功讀取無帶使用者身分的紀錄（已接受）」已由第十四節取代。
- **grep 判準**：`mcp` 只在 `app.py` import（`server.py` 經 `app` 間接，D-2）；`httpx` 只在 `executor.py`；`main.py`／`services/` 引用 `mcp_bridge` 零命中；`os.environ`／`getenv` 零；`jwt`／`jose`／`base64` 零 import；`__init__.py` 0 位元組；本單元測試零 skip。
- **本摘要既有文字的過時處（如實記載，原文不回改）**：
  1. 未記 review-02 的 R-11–R-13 處置、R5 測試、e2e 竄改 token 的偶發修正（改簽章首字元）、AC11.4.1 改為 `not_found`；這些處置以 merge-blockers 第 7、8、14 列為準。
  2. 第十四節 facade 測試 11 案（現 12）、全套 1313（現 1319）；facade sha256 基線 `f3900ca3…` 與「diff 27 行」已因第 14 項再改同檔而失效（現 `0d7e4f37…`、+51 行）。
  3. ADR-0021 未列入 `source-manifest.json`（record 內檔案，manifest 只收工作區程式）。
  4. D-7 寫「未安裝到本機全域 python3」，第十四節前置卻寫已 `pip install -r requirements.txt`；實查本機全域 `python3` 的 `mcp` 現為 2.3.0，與 repo 外工具 `claude-agent-sdk` 要求的 `mcp<2.0.0` 衝突。
  5. `backend/.venv` 為 Python 3.13.7，Dockerfile 與 CI 為 3.12。
