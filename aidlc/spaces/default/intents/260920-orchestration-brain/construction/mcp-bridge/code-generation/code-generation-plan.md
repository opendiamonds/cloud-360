# Code Generation Plan — `U21 mcp-bridge`

> 本計畫把四站設計（functional-design 修訂 1、nfr-requirements、nfr-design、infrastructure-design）落成程式、設定與文件，**並一併處置四站審查帶下來的 37 項**（`../carried-review-items.md`：functional-design 11、nfr-requirements 10、nfr-design 9、infrastructure-design 7，見 §二）。使用者在四個關卡的裁決優先於設計產出中對應的段落：明文 JWT 接受（2026-10-14T23:02:07Z）；`OPEN-MB21-17` 由 Step 1 實測決定，優先保 `BR76.3` 字面（2026-10-14T23:34:57Z）；bridge 改掛只與 `backend` 共用的專屬網段、不進 `internal`；部署後健康檢查不擋部署，第一個 client 落地時改為阻擋（2026-10-15T00:38:42Z）。方法論為 `test-after`：每一層先實作，再補該層測試並執行。
>
> **核可本計畫，等於同時核可契約變更紀錄 `ADR-0021`**（草案在同目錄 `adr-0021-draft.md`）。核可後，Step 1 把它原樣移入 `inception/decisions/0021-mcp-bridge-x04-contract-increments.md`，只把 Status 改成 Accepted。
>
> **Step 1 結束後設一道中途關卡**：依賴路線、`OPEN-MB21-16`、`OPEN-MB21-17` 的結果要等實測才知道，而核可前不能執行任何會改變系統狀態的指令。Step 1 跑完後先暫停，把結果與選定的路線交給使用者看，確認後才進 Step 2。結果若落在路線 C 或 D，或 `OPEN-MB21-17` 落在 17-B，都要使用者明確同意才能繼續。

## 一、交付範圍

**新檔**

| # | 路徑 | 內容 |
|---|---|---|
| 1 | `inception/decisions/0021-mcp-bridge-x04-contract-increments.md` | ADR-0021，記 C-1..C-5（從草案移入） |
| 2 | `backend/mcp_bridge/__init__.py` | 空檔 |
| 3 | `backend/mcp_bridge/__main__.py` | 只有 `raise SystemExit(main(sys.argv[1:]))` 與兩行 import |
| 4 | `backend/mcp_bridge/cli.py` | `parse_args`（`--backend-url`；`--host` 預設 `127.0.0.1`；`--port` 預設 8080；`--max-concurrency` 預設 16）、`main(argv, *, config_dir)` |
| 5 | `backend/mcp_bridge/startup.py` | `load_and_validate(config_dir) -> LoadedConfig` 讀三份 JSON；`StartupConfigError(subject)` 包住全部 I/O 與解析錯誤 |
| 6 | `backend/mcp_bridge/observability.py` | `configure_logging`、`BridgeFormatter`（單行化）、`normalize_agent`／`normalize_tool`、四種事件的記錄函式 |
| 7 | `backend/mcp_bridge/limits.py` | 具名常數、`BridgeLimits`、`derive_allowed_hosts(port)` |
| 8 | `backend/mcp_bridge/guards.py` | `PathRouter`（精確路徑）、`MethodGuard`（非 POST 回 405）、`ConcurrencyGate`、`BodyLimit`（含讀取期限）、`CredentialContext`、`ContextVar` 定義 |
| 9 | `backend/mcp_bridge/dispatch.py` | `run_tool_call`：MB-W3 第 2–7 步、總攔截、`tool_call` 那一行的唯一寫出點 |
| 10 | `backend/mcp_bridge/executor.py` | `build_backend_client`（拒收 cookie 的 jar、`Limits`、`Timeout`、`follow_redirects=False`）、`exchange`、`read_bounded`、`classify_transport_error`；全單元唯一 import `httpx` 的模組 |
| 11 | `backend/mcp_bridge/{generator,calls,outcomes,credentials,agents}.py` | 五個純函式模組（`functional-spec.md` 2.5），`outcomes.py` 另含封閉聯集 `ExchangeResult` 與四值的 `TransportFailure` |
| 12 | `backend/mcp_bridge/app.py` | `create_app(*, backend_client, registry, tool_specs, allowed_hosts, limits=BridgeLimits())`；只有它與 `server.py` import `mcp` |
| 13 | `backend/mcp_bridge/server.py` | `serve(loaded, args)`：建 client、呼叫 `create_app`、以 `uvicorn.Config(access_log=False, log_config=None)` 起服務 |
| 14 | `backend/mcp_bridge/allowlist.json`、`generated_tools.json`、`agents.json` | 三份進版控檔（`functional-spec.md` 2.6） |
| 15 | `backend/scripts/gen_mcp_tools.py` | 寫出模式與 `--check` 模式；只 import `mcp_bridge.generator` |
| 16 | `backend/tests/mcp_topology.py` | `MCP_ROUTE` 常數、驗證拓樸、記錄包裝與屏障、`McpClientPort`、`LogSource` |
| 17 | `backend/tests/mcp_test_client.py` | `BR78.1` 的最小測試 client（官方 SDK 的 streamable HTTP client） |
| 18 | `backend/tests/mcp_wire_client.py` | **只在路線 C**：手寫的最小 JSON-RPC client，另附一支 SDK 互通腳本 |
| 19 | `backend/tests/test_mcp_bridge_{generator,pure,guards,dispatch,app,startup,topology,artifacts,e2e,static,deploy}.py` | 本單元的 11 支測試檔（見 `unit-test-instructions.md` §三） |
| 20 | `backend/requirements-mcp.txt` | **只在路線 C**：非註解行恰為 `mcp==<版本>` |
| 21 | `construction/mcp-bridge/code-generation/{code-summary.md, traceability.json, source-manifest.json}` | 紀錄與追溯 |

**改檔**

| # | 路徑 | 改什麼 |
|---|---|---|
| 22 | `backend/requirements.txt` | 路線 A／B：新增一行 `mcp==<精確版本>`，附註解比照檔頭 `:1-7` 的釘選紀律寫明理由。路線 C 不改 |
| 23 | `deploy/docker-compose.deploy.yml` | 新增服務 `mcp-bridge`。新增頂層網段 `mcp`（`internal: true`），只有 `backend` 與 `mcp-bridge` 掛上，`backend` 由 `[edge, internal]`（`:169`）改為 `[edge, internal, mcp]`。同步註解：`:4-6`、`:65`、`:167-168`、`:177`、`:397-414` |
| 24 | `backend/Dockerfile` | 路線 A／B 不改。路線 C 在 `COPY . .`（`:19`）**之前**單獨 COPY `requirements-mcp.txt` 並建 `/opt/mcp-venv`，位置仍在 `USER appuser`（`:23`）之前 |
| 25 | `.github/workflows/ci.yml` | `backend` job（`:242-306`）加 `timeout-minutes: 15`；在 `:300` 之後、`:302` 之前加 `MCP tool spec drift` 步驟。路線 C 另加建 venv 的步驟與 `cache-dependency-path` |
| 26 | `.github/workflows/deploy.yml` | `deploy` job 在 tunnel 等待步驟（`:358-370`）之後、Redis 重啟驗證的註解（`:372` 起）之前，新增非阻擋的 `mcp-bridge` 健康紀錄步驟 |
| 27 | `DEPLOY.md` | §5.6（`:1581`、`:1589-1596` 表、`:1613`、`:1616`、`:1625`、`:1653`、`:1729`）；§5.9.1（表、`:1861-1862`、`:1868`、`:1871`）；§5.11（`:1920-1924`、`:1928-1932`、`:1934-1940`）；新增 §5.12。`:1336`、`:1913`、`:1914` 的「六」與服務數無關，**不得更動** |
| 28 | `LOCAL-DEV.md` | `:112` 的 port 迴圈加 8080；在 `:420` 一帶補一小節「本機啟動 bridge」。路線 C 另加必做的 `.mcp-venv/` 建立指令 |

**跨單元修改**：**沒有程式層的跨單元修改**。`backend/main.py` 與所有 router 都不 import `mcp_bridge`（CC-1）；`requirement_field_*` 不改；`openapi.json` 不因本單元變動。以下已凍結的上游檔**一律不回改**，以 ADR-0021 為準：`contract-summary.md`、`components.md`、`unit-of-work.md`、`unit-of-work-dependency.md`、`brain-infra` 的 `cicd-pipeline.md`／`monitoring-design.md`、本單元 functional-design 的問題檔。

**不改的檔**（IC-8 原樣保留）：`deploy/render-env.sh`、`deploy/.env.example`、`backend/.env.example`、`deploy/docker-compose.test.yml`、`frontend/nginx.conf`、`deploy/cloudflared/config.yml`、根目錄的 `docker-compose.yml`、`schema_rbac.sql`。

**零新環境變數、零 secret、零對外埠、零 DDL、零 volume。**

## 二、併入本計畫的審查殘留（`../carried-review-items.md` 全部 37 項）

類型欄：「程式」＝改程式並配測試；「設定」＝compose／CI／Dockerfile；「文件」＝`DEPLOY.md`／`LOCAL-DEV.md`；「紀錄」＝只在 code-summary 記明落點或理由。

| # | 站別 | ID | 處置 | 類型 | 步驟 |
|---|---|---|---|---|---|
| 1 | functional-design | R-11 | Step 1 判定依賴路線。路線 C 下：(1) 測試直譯器經 `.mcp-venv/` 取得 `mcp`；(2) `mcp` 只准出現在 `app.py`／`server.py`，`__init__.py` 為空；(3) ci.yml 加建 venv 的步驟；(4) `BR78.1`／`BR78.2` 改為手寫 client 加子進程拓樸。選路結果在 Step 1 中途關卡呈現 | 程式／設定 | 1、6、10 |
| 2 | functional-design | R-12 | 擇 (a)：啟動時載入 `allowlist.json` 作為 `validate_tool_specs(specs, allowlist)` 的獨立參考。T-8 增列「`inputSchema` 多一個未宣告屬性」案例 | 程式 | 5 |
| 3 | functional-design | R-13 | `SEGMENT_PATTERN`／`SYSTEM_ID_PATTERN` 一律用 `.fullmatch()`。性質六的策略與 T-4 加入結尾換行、內嵌換行案例，期望 `invalid_argument` | 程式 | 2 |
| 4 | functional-design | R-14 | 八個類別各寫一個 `@given`（決定性），不用比例下限 | 程式 | 2 |
| 5 | functional-design | R-15 | 屏障放在 backend 外層記錄包裝內的 `asyncio.Event`：扣住 A 的請求，等 B 的請求抵達才同時放行。「token 改存模組變數 → 紅燈」列為完成條件 | 程式 | 6、7 |
| 6 | functional-design | R-16 | ADR-0021 的 C-5 補入漏列的落點，另補本計畫查出的兩處漏點（§五）。`U21 → U19` 的單元邊一併移除 | 紀錄 | 1 |
| 7 | functional-design | R-17 | 簽名統一為 `create_app(*, backend_client, registry, tool_specs, allowed_hosts, limits=BridgeLimits())`。具名入口為 `cli.main` 與 `startup.load_and_validate`，`__main__` 只呼叫 `main`，T-8 也走同一個入口 | 程式 | 4、5 |
| 8 | functional-design | R-18 | `--host` 預設 `127.0.0.1`；compose 的 `command` 明列 `--host 0.0.0.0` | 程式／設定 | 5、8 |
| 9 | functional-design | R-19 | 依 Step 1 的 17 分支：17-A 直接註冊 `CallToolRequest` 處理函式，SDK 不會預先驗證；17-B 用 `validate_input=False`。兩種情況下 T-2／T-4 都斷言：結果恰為 `BR76.1` 形狀、message 不回顯輸入、且有一行 log | 程式 | 1、4、7 |
| 10 | functional-design | R-20 | (1) `TransportFailure.kind` 為恰四值的封閉枚舉，`ExchangeResult` 為封閉聯集，由 `executor.classify_transport_error` 歸類；(2) 擇 (b)：jar 用 `DefaultCookiePolicy(allowed_domains=[])` 拒收一切 cookie，由 T-1 的並發版本涵蓋 | 程式 | 2、3 |
| 11 | functional-design | R-21 | 問題檔由 conductor 擁有、已核可，不回改。更正寫在 §五 5.3，code-summary 照錄 | 紀錄 | 14 |
| 12 | nfr-requirements | R-01 | 不設 uvicorn 的 `limit_concurrency`，改用 bridge 自己的 `ConcurrencyGate` 計進行中的 `/mcp` 請求，`/healthz` 豁免；判準 ①–⑤。503 不是 `BR76.1` 形狀，於 §六 揭露 | 程式 | 3 |
| 13 | nfr-requirements | R-02 | 同 #1。路線 C 的可構造拓樸為：backend 以 `uvicorn.Server` 跑在測試事件迴圈內，bridge 跑在 venv 子進程。skip 禁令擴及本單元全部測試；`NFR21.38` 依路線改口徑 | 程式／設定 | 1、6、10、13 |
| 14 | nfr-requirements | R-03 | 使用者已接受明文 JWT（2026-10-14T23:02:07Z），`OPEN-MB21-13` 結案。不改程式；§六 揭露，並註明改走專屬網段後同網段的竊聽面已收窄 | 紀錄 | 14 |
| 15 | nfr-requirements | R-04 | `derive_allowed_hosts(port)` 是純函式，預設埠時恰三項，另測一個非預設埠；端到端用實際埠推導。「對外暴露面零新增」的措辭與網段殘留改寫進 `DEPLOY.md` §5.12 | 程式／文件 | 2、7、12 |
| 16 | nfr-requirements | R-05 | 算式已由 nfr-design（`scalability-design.md` §2.2、§3.3）更正，結論不變、不需改程式 | 紀錄 | 14 |
| 17 | nfr-requirements | R-06 | `tool` 欄只取已宣告的名稱，其餘記 `unknown`。413、503、405、408 各記恰一行 `request_rejected` WARNING。補換行注入兩案 | 程式 | 3 |
| 18 | nfr-requirements | R-07 | `NFR21.3` 的二元條件改為「超過 50 ms 時必須留下裁決紀錄」，量測交給 build-and-test，本站不量測 | 紀錄 | 14 |
| 19 | nfr-requirements | R-08 | (1) 簽名同 #7；(2) 枚舉恰四值，`entities.md` 的增補寫進 code-summary 的「設計文字回補」表（不回改已凍結的設計檔）；(3) `ResponseTooLarge` 經 `map_outcome` 映射為 `internal_error`、`retryable: false` | 程式／紀錄 | 2、14 |
| 20 | nfr-requirements | R-09 | `stop_grace_period: 15s`，關係式寫在 compose 註解。寫入速率沒有上限（只受並行 16 約束），於 §六 揭露 | 設定 | 8 |
| 21 | nfr-requirements | R-10 | `NFR4` 對本單元讀為 N/A（不承擔還原義務），寫進 code-summary；上游的 `traceability.json` 不改 | 紀錄 | 14 |
| 22 | nfr-design | R-01 | 在 `ConcurrencyGate` 之前，`/mcp` 的非 POST 方法一律回 405（不佔名額）。本體讀取期限 `BODY_READ_TIMEOUT_S = 2.0`（逾時 408）、整體牆鐘 `REQUEST_WALL_TIMEOUT_S = 12.0`（逾時 503）；名額在 `finally` 歸還。新增三種 `reason`。增列 GET 帶 SSE `Accept` 與 16 條慢速上傳兩案，並配突變 | 程式 | 3 |
| 23 | nfr-design | R-02 | 依 Step 1 的 16 分支：16-A 移除 shield；16-B 保留 shield，名額要等 backend 交換結束才歸還，`tool_call` 那一行只由被保護的內層寫出。判準增列「行數恰 1」與「慢速 backend 加斷線迴圈後連線池未滿」 | 程式 | 1、3、7 |
| 24 | nfr-design | R-03 | 使用者裁決：優先 17-A 保住 `BR76.3` 字面；只有確實做不到才走 17-B，並在 code-summary 追認 | 程式 | 1、4 |
| 25 | nfr-design | R-04 | Step 1 產出「SDK 行為假設總表」，每列寫：假設、所釘版本的實測結果、判準編號、所走退路。寫進 code-summary | 紀錄 | 1、14 |
| 26 | nfr-design | R-05 | Encryption 一格改寫為「上游要求本機迴環或加密；本單元兩者皆非，屬使用者接受的例外」，寫進 code-summary 的 ADR-0006 表與 `DEPLOY.md` §5.12 | 文件／紀錄 | 12、14 |
| 27 | nfr-design | R-06 | `PathRouter`：`/healthz` 精確比對；`/mcp` 與 `/mcp/*` 都先經閘門與本體上限，再做精確路徑判斷，不等於 `/mcp` 的回 404、不到達 SDK。增列 `/mcp/`、`/mcp/x` 兩案（超量本體仍是 413） | 程式 | 3、4 |
| 28 | nfr-design | R-07 | `load_and_validate` 把檔案缺失、非 JSON、編碼錯誤一律包成 `StartupConfigError(subject=<檔名常數>)`。增列兩案：回傳 1、stderr 恰一行 ERROR、無 traceback | 程式 | 5 |
| 29 | nfr-design | R-08 | infrastructure-design 已依放大係數上緣 10 倍定為 `512m`。code-summary 把 17 MiB 改稱「緩衝位元組上界」，交 build-and-test 以 `docker stats` 量測 | 紀錄 | 14 |
| 30 | nfr-design | R-09 | 子進程一律用 `asyncio.create_subprocess_exec`；互通案例至少含一次 `isError` 與一次成功；每案 30 秒上限（兩條路線都套），逾時以 `AssertionError` 失敗並終止子進程 | 程式 | 6 |
| 31 | infrastructure-design | R-01 | **使用者裁決：改走專屬網段**。新網段 `mcp`（`internal: true`），成員只有 `backend` 與 `mcp-bridge`，bridge 不進 `internal`。同步：CC-5 斷言、IC-6 驗證指令、compose 檔頭註解、`DEPLOY.md` §5.11 第 1 點的禁令限縮為只適用既有網段。`infrastructure-specification.md` 的 §二之一 networks 列與 §四 blast radius 由 code-summary 記為「取代」 | 設定／文件 | 8、12、14 |
| 32 | infrastructure-design | R-02 | **使用者裁決：不擋部署**。部署後健康步驟維持 warning，寫明觸發條件「第一個實際 MCP client 合併時改為阻擋」，並以靜態測試機械化。60 秒計入會觸發 rollback 的 deploy job 預算 | 設定／文件 | 11、12 |
| 33 | infrastructure-design | R-03 | `DEPLOY.md` 逐行清單照 IC-6 ②，另補本計畫查出的 `:1616`「十個記憶體上限」→ 十一。`:1336`、`:1913`、`:1914` 不動 | 文件 | 12 |
| 34 | infrastructure-design | R-04 | 只在路線 C：Dockerfile 在 `COPY . .` 之前單獨 COPY `requirements-mcp.txt` 並建 venv | 設定 | 9 |
| 35 | infrastructure-design | R-05 | (1) 建 venv 的步驟帶 `working-directory: .`，venv 建在 repo 根目錄的 `.mcp-venv/`；(2) code-summary 寫變更後的最壞算式（端到端案例數 × 30 秒 ＋ pip 時間 ≤ 900 秒）；(3) CC-2 擴及 `__init__.py` 與 generator 的全部傳遞 import，由靜態測試鎖住 | 設定／程式 | 2、10、14 |
| 36 | infrastructure-design | R-06 | `DEPLOY.md` §5.12 註明 `docker compose stop mcp-bridge` 不持久，下一次 `up -d` 會把服務拉回來。持久止損要開 PR 移除服務區塊 | 文件 | 12 |
| 37 | infrastructure-design | R-07 | 寫明預期的 client 路徑：`backend` 容器經 `mcp` 網段以 `Host: mcp-bridge:8080` 連線。`backend` 不加 `depends_on: mcp-bridge`（惰性連線）。執行期的呼叫環（backend → bridge → backend）分屬不同請求，不構成啟動依賴。host 行程是否可達改為部署後實測 | 文件 | 12 |

**計數**：37 項，**0 項拒絕**。改程式、設定或文件者 29 項，只做紀錄者 8 項（#6、#11、#14、#16、#18、#21、#25、#29）。

**Major 項的突變驗證**：#1／#13、#12、#22、#23、#31、#32 各配「套用 → 紅 → 還原 → 綠」（`unit-test-instructions.md` §四）。

## 三、步驟（`test-after`：逐層先實作、再寫並執行該層測試）

所有驗證指令都在 `backend/` 目錄下執行，**只跑本單元的模組，不跑全套**。

### Step 1 — SDK 與依賴路線實測、ADR 移入

**1a. ADR**：把 `adr-0021-draft.md` 原樣移入 `inception/decisions/0021-mcp-bridge-x04-contract-increments.md`，只改 Status 與標題中的「草案」字樣。

**1b. 實測**：在 scratchpad 建一個一次性的 venv，探測腳本也放在 scratchpad。**不寫入 repo、不碰本機主環境。**

| # | 判定項 | 方法 | 通過條件 |
|---|---|---|---|
| K-1 | 解析相容（A-2） | 在一次性 venv 執行 `pip install --dry-run --report <檔> -r backend/requirements.txt mcp==<候選版>`，候選版從最新穩定版往下找 | 報告中 FastAPI 與 `pydantic` 的釘選版本都不變；Starlette 落在 FastAPI 所要求的範圍；傳遞依賴有解 |
| K-2 | 無狀態 streamable HTTP（`BR71.2`） | 以 `stateless=True`、`json_response=True` 起 session manager，用原始 JSON-RPC 打 `initialize`、`tools/list` | 回 JSON 回應，且沒有 `Mcp-Session-Id` |
| K-3 | Host 檢查（`BR71.6`） | 傳入 `allowed_hosts` 的傳輸安全設定，送 `Host: evil.example` | 被拒；`127.0.0.1:<埠>` 通過 |
| K-4 | `OPEN-MB21-17` | 不用 `call_tool` 裝飾器，直接為 `CallToolRequest` 註冊處理函式；對未知工具拋協定錯誤（`-32602`，固定訊息） | 回應為 JSON-RPC error，不是 `isError` 結果；訊息不含工具名 |
| K-5 | 預先驗證（R-19） | 17-B 時才需要：`validate_input=False` 是否存在 | 開關存在，且不合格參數會進到處理函式 |
| K-6 | `OPEN-MB21-16` | 處理函式等 2 秒並記錄是否收到 `CancelledError`；client 送出後立刻關閉連線；同時量測內層 ASGI 呼叫是否在處理函式完成之前就返回 | 兩個觀察值都要記錄 |
| K-7 | contextvar 傳遞 | 處理函式讀中介層設定的 `ContextVar` | 讀到本請求的值 |
| K-8 | GET／DELETE `/mcp` 的行為 | 帶 `Accept: text/event-stream` 的 GET | 記錄 SDK 原生行為（本設計無論結果如何都在前面擋 405） |
| K-9 | lifespan | session manager 是否需要在 lifespan 內執行 `run()` | 記錄 `create_app` 的接線方式 |
| K-10 | dns 例外鏈 | 以 httpx 連 `.invalid` 網域 | `__cause__`／`__context__` 中是否有 `socket.gaierror` |
| K-11 | 路徑遮蔽 | 在 `tests/helpers.py:27-31` 把 `backend/` 與 `backend/services` 插到 `sys.path` 前端之後，`import mcp` 是否被同名模組遮蔽 | 正常 import |

**依賴路線分支表**

| 分支 | 條件 | 路線 | `MCP_ROUTE` | 後續差異 |
|---|---|---|---|---|
| A | 最新候選版通過 K-1–K-3 | 第一順位：`requirements.txt` 加 `mcp==<版本>` | `"same-interpreter"` | Step 9 不改 Dockerfile；Step 10 只做 S-1、S-2；不建 `mcp_wire_client.py` |
| B | A 卡在 K-1，但找到一個較舊版本通過 K-1–K-3 | 第一順位，釘該舊版 | 同 A | 同 A；code-summary 記下較新版本被拒的原因 |
| C | 沒有任何版本同時通過 K-1–K-3 | 第二退路：`requirements-mcp.txt`、`/opt/mcp-venv`、`.mcp-venv/` | `"isolated-venv"` | Step 6 加手寫 client 與子進程拓樸；Step 9 改 Dockerfile；Step 10 加 S-3、S-4；`LOCAL-DEV.md` 升為必做。**需使用者在中途關卡同意** |
| D | 路線 C 也不可行 | **停止**。把「升 FastAPI」（連動 `openapi.json` 重 dump 與前端型別重產）另開題請使用者裁決，不得自行升版 | — | 計畫中止，等待裁決 |

此外，K-4 與 K-5 都不成立時，`NFR21.8` 不能完成（`observability-design.md` §二），同樣停止並回報。

**`OPEN-MB21-17` 分支**

| 分支 | 條件 | 走法 |
|---|---|---|
| 17-A（優先） | K-4 成立 | 直接註冊 `CallToolRequest` 處理函式，未知工具回 JSON-RPC 協定錯誤（保住 `BR76.3` 字面）。三個繞路一起取消：不用 `validate_input`；處理函式只呼叫總攔截過的 `run_tool_call`，不會進到 SDK 的例外轉換（以 T-2 鎖住）；`mcp.server.lowlevel.server` 不需另設 ERROR，注入案例仍必須通過 |
| 17-B | K-4 不成立 | 用 `call_tool(validate_input=False)`，未知工具回 `BR76.1` 形狀的 `invalid_argument`（固定訊息）；`mcp.server.lowlevel.server` 設為 ERROR。code-summary 記為對 `BR76.3` 的追認，**並在中途關卡呈現** |

**`OPEN-MB21-16` 分支**

| 分支 | K-6 的觀察 | 走法 |
|---|---|---|
| 16-A | 處理函式不被取消，且內層 ASGI 呼叫等處理函式完成才返回 | 不用 `asyncio.shield`。閘門在 `finally` 歸還名額時交換已結束，CC-6 自然成立；`tool_call` 那一行照常由 `run_tool_call` 的 `finally` 寫出 |
| 16-B | 其他任一種情況 | 保留 shield。`ConcurrencyGate` 為每個請求建一個 `RequestSlot` 放進 `ContextVar`，`dispatch` 把被保護的交換 task 登記上去；名額要等「內層已返回」且「已登記的 task 全部完成」才歸還（CC-6）。`tool_call` 那一行只由被保護的內層寫出，外層收到 `CancelledError` 時不寫 |

**1c. 記錄**：把 K-1–K-11 的結果、選定的版本與路線、`MCP_ROUTE` 的值、傳遞依賴清單（`OPEN-MB21-15` 的供應鏈面），以及「SDK 行為假設總表」（#25）寫進 `code-summary.md` 的「Step 1 實測紀錄」。**然後暫停，進中途關卡。**

**驗證**：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_requirement_field_http -v`（確認測試執行器與端到端會重用的需求欄位 HTTP 測試可跑）

### Step 2 — 純函式：產生器、`calls`、`outcomes`、`credentials`、`agents`、`limits`

- **實作**：
  - `generator.py`：`generate_tools`、`validate_tool_specs`、`ALLOWED_PATH_PREFIXES`；檢查順序依 `BR72.1` 固定。
  - `calls.py`：`SEGMENT_PATTERN` 的字串與 `KEY_PATTERN.pattern`（`requirement_field_definitions.py:33`）逐字相同；`SYSTEM_ID_PATTERN`；一律 `.fullmatch()`。
  - `outcomes.py`：`ExchangeResult`、四值 `TransportFailure`、`ResponseTooLarge`、`InternalFailure`；`map_outcome` 是 `BR76.1` 封閉表的唯一實作點。
  - `credentials.py`：`RequestCredential` 為 `@dataclass(repr=False)`，`Authorization` 上限 8192 位元組，多值即判 `unauthenticated`。
  - `agents.py`：`resolve_agent`。
  - `limits.py`：七個具名常數（設計的五個，加上 #22 新增的 `BODY_READ_TIMEOUT_S`、`REQUEST_WALL_TIMEOUT_S`）、`BridgeLimits`、`derive_allowed_hosts`。
  - 六個模組都不 import `mcp`、`httpx`、`sqlalchemy`、`fastapi`（`NFR21.40`）。
- **測試**：`test_mcp_bridge_generator.py`（八個 `@given`、七條性質、`AC11.4.2` 的 example）；`test_mcp_bridge_pure.py`（其餘純函式，含性質六，以 `httpx` 的 `build_request` 實際組出的 URL 為判準）。
- **突變**：`unit-test-instructions.md` §四 的產生器七列加 R-13 的 `.match()`。
- **落實**：#3、#4、#10(1)、#15、#19(2)(3)、#35(3)。
- **驗證**：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_generator tests.test_mcp_bridge_pure -v`

### Step 3 — 中介層、`dispatch`、`executor`、`observability`

- **實作**：
  - `guards.py` 層序：`PathRouter` → `MethodGuard`（405）→ `ConcurrencyGate`（503，名額屬於實例）→ `BodyLimit`（413；期限 408）→ 牆鐘上限（503）→ 精確路徑判斷（404）→ `CredentialContext`（`finally` 重設）→ 內層。
  - `dispatch.run_tool_call(spec_or_none, arguments, credential, agent_header, exchange)`：以 `except Exception` 總攔截；`CancelledError` 不攔；依 16 分支決定 shield 與唯一寫出者。
  - `executor.py`：拒收 cookie 的 jar；`httpx.Limits` 的連線上限等於並行上限；`Timeout(connect=3, total=10)`；`read_bounded`；`classify_transport_error`（`dns` 的判定方式依 K-10）。
  - `observability.py`：`BridgeFormatter` 把 `\r`、`\n` 跳脫；`tool` 與 `agent` 正規化；`request_rejected` 的 `reason` 集合為 `over_concurrency`、`body_too_large`、`body_timeout`、`request_timeout`、`method_not_allowed`。
- **測試**：`test_mcp_bridge_guards.py`、`test_mcp_bridge_dispatch.py`（案例見 `unit-test-instructions.md` §三）。
- **落實**：#10(2)、#12、#17、#22、#23（單元層）、#27。
- **驗證**：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_guards tests.test_mcp_bridge_dispatch -v`

### Step 4 — `create_app`（`app.py`）

- **實作**：`create_app(*, backend_client, registry, tool_specs, allowed_hosts, limits=BridgeLimits())` 依 K-9 接上 lifespan。`/healthz` 回模組常數，位於全部閘門之外。`/mcp` 由 Step 3 的層序包住 SDK 的無狀態 session manager（`json_response=True`、Host 檢查）。`tools/list` 只交 `name`、`description`、`inputSchema`，不交 `binding`。`tools/call` 依 17 分支接線。函式內不讀檔、不解析命令列、不建 client、不設 logging。
- **測試**：`test_mcp_bridge_app.py`：以 `httpx.ASGITransport` 直接驅動 `create_app`，配一個回固定內容的 backend 替身。
- **落實**：#7、#9、#24、#27。
- **驗證**：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_app -v`

### Step 5 — server 入口：`cli`、`startup`、`__main__`、`server`

- **實作**：照 `reliability-design.md` §五。`main` 在驗證通過**之後**才 import `server`；`load_and_validate` 讀三份檔，所有 I/O 與解析錯誤都包成 `StartupConfigError`；`serve` 以 `uvicorn.Config(access_log=False, log_config=None)` 起服務，綁定後記 `startup port=<實際埠> tools=3`。
- **測試**：`test_mcp_bridge_startup.py`（T-8 六案，全部在主直譯器以 `main(argv, config_dir=暫存目錄)` 呼叫；另驗 `--host`、`--max-concurrency` 預設與 `__main__.py` 的 AST 形狀）。
- **落實**：#2、#7、#8、#28。
- **驗證**：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_startup -v`

### Step 6 — 測試 client 與驗證拓樸

- **實作**：
  - `mcp_topology.py`：`MCP_ROUTE` 由 Step 1 設定一次；記錄包裝與 `asyncio.Event` 屏障；`LogSource`；每案以 `asyncio.timeout(30)` 包住。
  - `mcp_test_client.py`：`BR78.1`，路線 A／B 的 `McpClientPort` 實作。
  - 路線 A／B 的拓樸：`create_app` 加 `uvicorn.Server.serve(sockets=[預先綁定的 socket])`；backend 側為 `ASGITransport(記錄包裝(main.app))`，資料庫用 `tests/helpers.py:41-56` 的 SQLite。
  - 路線 C 另加：`mcp_wire_client.py`；bridge 以 `asyncio.create_subprocess_exec` 起在子進程，就緒以輪詢 `/healthz` 判定（上限 10 秒）；backend 以 `uvicorn.Server` 跑在測試事件迴圈內；SDK 互通腳本至少涵蓋一次 `isError` 與一次成功。
  - 前置條件不成立時一律 `AssertionError`，**不准 skip**。
- **測試**：`test_mcp_bridge_topology.py`（以替身工具宣告自測，不依賴 Step 7 的正式三份檔）。
- **落實**：#1、#5（屏障機制）、#13、#30。
- **驗證**：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_topology -v`

### Step 7 — 三份 JSON、漂移閘門腳本、完整端到端

- **實作**：
  - `allowlist.json`：三個 operation，`rename` 為 `{field_key: field}`，`strip_body_fields` 為 `[on_behalf_of]`，含 `inject`、`requires_agent`、`property_patterns`。
  - `agents.json`：agent 名依 `entities.md` 的 `AgentRegistry`，值域 ⊆ 可代寫組（`GROUPS_BY_KEY`，`requirement_field_definitions.py:119`）。
  - `gen_mcp_tools.py`：讀取輸入封閉為 repo 根目錄的 `openapi.json` 與 `allowlist.json`；`--check` 不一致時 `exit 1`；不讀環境變數、不 import `main`／`mcp`／`httpx`（CC-2）。
  - 寫出 `generated_tools.json`。
- **測試**：`test_mcp_bridge_artifacts.py`（T-5、T-6、T-7、`--check` 綠與紅）；`test_mcp_bridge_e2e.py`（T-1、T-2、T-4、`AC11.4.1`／`AC11.4.3`、端到端 NFR 判準、16 分支的斷線案例、慢速 backend 加斷線迴圈）。
- **落實**：#5、#9、#15、#23。
- **驗證**：
  `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_artifacts tests.test_mcp_bridge_e2e -v`
  `python3 scripts/gen_mcp_tools.py --check`

### Step 8 — compose 服務（專屬網段）

- **實作**：服務區塊照 `infrastructure-specification.md` §二之一，兩處取代：`networks: [mcp]`（不是 `[internal]`）；`command` 含 `--host 0.0.0.0`。另外：
  - `stop_grace_period: 15s`，旁邊寫關係式註解：`REQUEST_WALL_TIMEOUT_S` 12 秒 ＋ 1 秒 ≤ 13 秒 < 15 秒。
  - healthcheck 覆寫映像內建的 `HEALTHCHECK`（`backend/Dockerfile:27-28`）。
  - `512m`；`*json_file_bounded`；`depends_on: [backend]` 不帶 `condition`；不寫 `environment`／`env_file`／`ports`。
  - 頂層新增 `mcp: {internal: true}`；`backend` 加掛 `mcp`。
  - 改寫註解：`:4-6`、`:65`（`50m x 5 x 7 services`）、`:167-168`、`:177`、`:397-406`（`internal: true` 的禁令限縮到 `edge`／`internal`，`mcp` 刻意設定，理由是斷開 bridge 的出站）、`:408-414`。
- **測試**：`test_mcp_bridge_deploy.py` 以 `yaml.safe_load` 解析（CC-5）：`mcp-bridge.networks == ["mcp"]`；`networks.mcp.internal is True`；`mcp` 成員恰為 `{backend, mcp-bridge}`；`edge` 與 `internal` 仍不帶 `internal: true`；沒有 `ports`、`environment`、`env_file`、`${`；`stop_grace_period == "15s"`；`command` 內容；healthcheck、`restart`、`logging`、記憶體上限。
- **落實**：#8、#20、#31。
- **驗證**：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_deploy -v`

### Step 9 — Dockerfile

- **路線 A／B**：不改。`test_mcp_bridge_deploy.py` 斷言 Dockerfile 裡沒有 `mcp`。
- **路線 C**：在 `:16-17` 之後、`:19` 之前加 `COPY requirements-mcp.txt .` 與建 `/opt/mcp-venv` 的 `RUN`（在 `USER appuser` 之前）；compose 的 `command` 首項改為 `/opt/mcp-venv/bin/python`。斷言 venv 段位於 `COPY . .` 之前。
- **落實**：#34。
- **驗證**：同 Step 8；映像建置交給 CI 的 `docker-build` job。

### Step 10 — `ci.yml`

- **實作**：S-1 `MCP tool spec drift`（`run: python scripts/gen_mcp_tools.py --check`，不帶 `env:`，放在 `:300` 之後）；S-2 job 層 `timeout-minutes: 15`。路線 C 另加 S-3 `Create isolated MCP venv`（`working-directory: .`，建 `.mcp-venv/`，放在 `Run unit tests` 之前）、S-4 `cache-dependency-path` 改為多行。
- **測試**：`test_mcp_bridge_deploy.py`（`backend` job 含閘門與 `timeout-minutes`）；`test_mcp_bridge_static.py`（skip 為 0；import `mcp` 的檔案集合恰為 `{app.py, server.py}`；import `httpx` 的恰為 `{executor.py}`；`main.py` 與 router 不 import `mcp_bridge`；無 `os.environ`／`os.getenv`；logger 名稱唯一；七個常數各定義恰一次；`jwt`／`jose`／`base64` 不被 import；授權函式為 0）。
- **落實**：#1、#13、#35。
- **驗證**：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_static tests.test_mcp_bridge_deploy -v`

### Step 11 — `deploy.yml` 的非阻擋健康步驟

- **實作**：新步驟 `Record mcp-bridge health (non-blocking)`：以 `ps -q mcp-bridge` 取容器 id，輪詢 `docker inspect` 的 Health 狀態，至多 12 次、每次 5 秒；讀不到 `healthy` 時印 `::warning::`、`RestartCount` 與 `logs --tail=40`，並寫一行到 `$GITHUB_STEP_SUMMARY`。取值命令都放在 `if` 條件位置，比照 `:331-334` 的 P-5 形狀，步驟結束碼恆為 0（CC-7）；另加 `continue-on-error: true`。不呼叫 `/mcp`、不使用 token。註解寫明：「第一個實際 MCP client 合併進 `ut` 的那個 PR 內，必須改為失敗即 `exit 1` 並拿掉 `continue-on-error`」；本步的 60 秒屬於會觸發 rollback 的 30 分鐘預算（`:28`）。
- **測試**：`test_mcp_bridge_deploy.py`：步驟位置；沒有裸露的 `$(docker inspect …)` 指派；`continue-on-error: true`；**觸發條件的機械化**——若 `backend/` 中（排除 `mcp_bridge/` 與 `tests/`）出現 `mcp-bridge:8080`，該步驟必須是阻擋形狀，否則紅燈。
- **落實**：#32。
- **驗證**：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_deploy -v`

### Step 12 — `DEPLOY.md`／`LOCAL-DEV.md` 同步

- **`DEPLOY.md`**：
  - §5.6：`:1581` 六→七；`:1589-1596` 表加一列 `mcp-bridge` `512m`（依據：緩衝位元組上界 × 10 倍放大 ＋ 常駐估計，皆未量測）；`:1613`、`:1625` 六→七；`:1616` 十→十一；`:1653` 六→七；`:1729` 改為 `50m × 5 × 7 = 1.75GB`。
  - §5.9.1：表加一列（`mcp-bridge` 健康紀錄，12 × 5 ＝ 60 秒，有界，非阻擋但計入預算）；`:1861-1862` 改為有界 1320 秒、無界剩餘 480 秒；`:1868`、`:1871` 的 540 改為 480。
  - §5.11：`:1920-1924` 的禁令限縮為只適用 `edge`／`internal`，`mcp` 網段刻意 `internal: true`；`:1928-1932` 補上 bridge 不在 `internal` 上；`:1934-1940` 表加一列「`/healthz` 不證明工具宣告正確、allowlist 生效，也不證明能呼叫 backend」。
  - 新增 §5.12「MCP bridge（第七個服務）」：角色；零對外埠；零變數；與 `backend` 同映像；網段 `mcp`；驗證指令；host 可達性的實測欄位；Encryption 為經接受的例外；止損不持久；預期的 client 路徑；健康步驟改為阻擋的觸發條件。
- **`LOCAL-DEV.md`**：`:112` 的 port 迴圈加 8080；在 `:420` 一帶補 `cd backend && python -m mcp_bridge --backend-url http://127.0.0.1:8010`（預設監聽 `127.0.0.1:8080`）。路線 C 另加 `.mcp-venv/` 的建立指令，並說明缺 venv 時本單元測試以 `AssertionError` 失敗，不是 skip。
- **落實**：#15、#26、#31、#32、#33、#36、#37。
- **驗證**：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_deploy -v`（含 `DEPLOY.md` 的機械斷言）

### Step 13 — `requirements.txt` 釘版

- **實作**：路線 A／B：`backend/requirements.txt` 新增 `mcp==<Step 1 版本>`，附註解寫明精確釘選的理由、backend 進程不 import 它、升版要重跑 Step 1 的 K-1–K-11。路線 C：新檔 `requirements-mcp.txt`。
- **測試**：`test_mcp_bridge_static.py` 的 `NFR21.38` 依路線斷言（A／B：新增非註解行恰為 1，FastAPI 與 `pydantic` 釘選不變；C：`requirements.txt` 無 diff，新檔非註解行恰為 1）。
- **驗證**：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_static -v`；repo 根目錄 `python3 scripts/validate_repo_contract.py`、`python3 scripts/validate_env_contract.py`

### Step 14 — code-summary 與追溯

- **`code-summary.md`**：Step 1 實測紀錄與 SDK 行為假設總表；§二 全部 37 項的落點；取代關係表（`logical-components.md` §六、本計畫 §五 5.2、`infrastructure-specification.md` §二之一 networks 列與 §四 blast radius）；設計文字回補表；突變結果；ADR-0006 四面向（Encryption 為例外）；`NFR4` 讀為 N/A；交給 build-and-test 的事項；R-21 更正；§六 揭露清單。
- **`traceability.json`**、**`source-manifest.json`**。
- **全單元重跑**：見 `unit-test-instructions.md` §二「全單元」指令。

## 四、步驟 ↔ 故事追溯

| 故事／AC | 驗證 | 步驟 |
|---|---|---|
| `AC11.4.1`：無權專案經 MCP 讀取被拒，理由與直接存取相同 | 端到端：非成員以 `read_requirement_fields` 讀取，得到 `forbidden`；`message` 等於同一使用者直接 `GET` 時 backend 的 `detail`（過濾後）；記錄包裝恰 1 筆，帶該使用者的 token | 3、4、7 |
| `AC11.4.2`：每個工具 schema 的 `properties` 不含 `token`／`key`／`secret`／`authorization` | 性質一（PBT）；T-5 對正式產物以字面白名單斷言；`tools/list` 端到端逐工具檢查任何深度的屬性名；T-8 的 `api_key` 啟動拒絕；排除根目錄 `.mcp.json`（T-6） | 2、5、7 |
| `AC11.4.3`：有權專案經 MCP 讀取成功並回傳欄位值 | 端到端：成員以 `read_requirement_fields` 讀取，結果等於直接 `GET` 的 `FieldSetView`（`BR76.4`） | 4、7 |

本版沒有大腦側 client（`OPEN-MB21-1`），三條 AC 都以 `BR78.1` 的測試 client 驗證。

## 五、契約追認事項

### 5.1 契約增量 C-1..C-5（內容見 `adr-0021-draft.md`，隨本計畫一併核可）

| # | 契約 | 增量 | 性質 |
|---|---|---|---|
| C-1 | `X-04` `tools` | 新增 `clear_requirement_field`（`system_id`、`agent_group`、`field`），經 `K-17` 的 `clear_field` | 擴充（`[MB4]`=A）；`K-17` 已把 `U21` 列為 `clear_field` 呼叫端 |
| C-2 | `X-04` `tools.write_requirement_field` | 屬性 `field_key` 改名為 `field`（C-1 同樣適用） | **已依 `[MB6]`=A 定案**，這裡追認的是 `X-04` 的字面 |
| C-3 | `X-04` 的未定項與授權責任 | token 每請求以 `Authorization: Bearer` 原樣轉遞、用完即棄；傳輸為無狀態 streamable HTTP；連線層新增 `X-Cloud360-Agent`；授權責任更正為「全域層與 per-project 判定都由 `K-17` facade 承擔」 | 定案加更正 |
| C-4 | `[I7]`／`brain-infra` `cicd-pipeline.md` 第 24 項 | allowlist 初始值由「`U19` ＋ `U20` 兩塊」收窄為 `U20` 的三個 operation | **對已核可範圍的收窄**，不是擴充 |
| C-5 | `K-16`、`components.md`、單元依賴 | **移除邊**：`McpBridge → ProjectMembership` 與 `U21 → U19`；`resolve_project_role.consumed_by` 移除 `U21` | 移除邊。含 review R-16 的補漏落點與本計畫另查出的 `contract-summary.md:1538`、`unit-of-work.md:369`；Bolt 排序不受影響 |

ADR-0020 已把 `U13` 從 `K-16` 的 `consumed_by` 移除，加上 ADR-0021，`resolve_project_role.consumed_by` 實際為 `[U20]`。

### 5.2 規則字面的取代（不屬契約增量，寫進 code-summary 的取代關係表）

| 已核可字面 | 取代為 | 依據 |
|---|---|---|
| `BR71.2`「只在 internal 網段」 | 只在專屬網段 `mcp`（`internal: true`，成員為 `backend` 與 `mcp-bridge`） | 使用者 2026-10-15T00:38:42Z 對 infrastructure-design R-01 的裁決；屬 ADR-0006 network exposure 的收窄 |
| `BR71.6`「允許清單只含 `mcp-bridge:8080` 與本機迴環」 | 由 `derive_allowed_hosts(port)` 推導，預設埠時恰為這三項 | nfr-requirements R-04 |
| `BR78.3` 三參數的 statement | 四個必填加 `limits`（純關鍵字） | functional-design R-17 |
| `BR78.1`／`BR78.2`（只在路線 C） | 手寫的最小 JSON-RPC client 加子進程拓樸，另加一案 SDK 互通 | functional-design R-11 |
| `BR76.3`（只在 17-B） | 未知工具以 `isError` 的 `invalid_argument` 回傳 | 使用者 2026-10-14T23:34:57Z 裁決的退路 |

### 5.3 R-21 更正（問題檔由 conductor 擁有、已核可，不回改）

| 位置 | 原文 | 更正 |
|---|---|---|
| `functional-design-questions.md:21` | 引用 `stories.md:732` 為「本故事的 Given 今天不可構造」 | 實際位置為 **`stories.md:731`** |
| `functional-design-questions.md:5` | 「故出五題」 | 實際為**六題**（`MB1`–`MB6`） |
| `MB6` 選項 A 標「本站設計預設」 | — | 已作答定案（`[MB6]`=A，2026-10-13T23:08:40Z），不再是預設 |

## 六、核可關卡需揭露事項

1. **使用者 JWT 以明文傳輸**：使用者 2026-10-14T23:02:07Z 接受。上游要求「本機迴環或加密」，本單元兩者都不是，這是例外，不是符合。改走專屬網段後，能在同網段竊聽的容器由 `internal` 的四個成員縮為 `backend` 一個。
2. **成功的讀取沒有帶使用者身分的紀錄**（`OPEN-MB21-14`，`[MBN1]`=A）。
3. **記憶體上限 `512m` 是估計**：交給 build-and-test 以 `docker stats` 量測。
4. **部署後的 bridge 健康檢查不擋部署**：bridge 壞了部署仍綠燈，只留 warning 與 step summary 一行，沒有通知。第一個實際 MCP client 合併時要改為阻擋，觸發條件由 Step 11 的靜態測試機械化。
5. **deploy job 的預算**：新增有界 60 秒，兩個無界項（`up -d --build`、`ollama pull`）剩下 **480 秒**，都還沒實測。這 60 秒屬於會觸發 rollback 與 revert PR 的那份預算。
6. **`OPEN-MB21-15`**：路線 A／B 下，`mcp` 及其傳遞依賴會進入 backend 的執行期映像，backend 進程本身不 import 它們。路線 C 下 `/opt/mcp-venv` 同樣會出現在 backend 映像內，且本機跑測試多一個前置條件。
7. **`OPEN-MB21-16`**：client 中途斷線時 SDK 是否取消工具 task，要等 Step 1 實測，結果在中途關卡呈現。
8. **`OPEN-MB21-17`**：能否保住 `BR76.3` 字面，要等 Step 1 實測；若走 17-B，在中途關卡呈現。
9. **bridge log 與 backend log 沒有關聯鍵**（`OPEN-MB21-9`）：只能依時間對照。
10. **本版沒有實際 client**（`OPEN-MB21-1`）：三條 AC 都由測試 client 驗證。
11. **host 行程可達性未知**：`internal: true` 網段的 host 路由行為因引擎版本而異，部署後依 `DEPLOY.md` §5.12 實測並填入。
12. **HTTP 層拒絕不是 `BR76.1` 形狀**：405、408、413、503 發生在 MCP 協定層之外，各自記一行 `request_rejected`。
13. **寫入速率沒有上限**：持有有效 token 的呼叫端，在並行 16 之內可以不限速率地呼叫寫入工具。
14. **止損不持久**：`docker compose stop mcp-bridge` 在下一次部署時會失效。
15. **Step 1 中途關卡**：結果落在路線 C／D 或 17-B 時，需使用者另行同意才能進 Step 2。

## 七、方法論與 contract 基線的對應

`test-after` 的五個可測層在本單元的落點：**Data model / database behavior** 不新增（零 DDL）；**Repository / data access** 不新增（經既有 `U20` facade，以 HTTP 呼叫）；**Business logic** 為 Step 2–3 的純函式與 `dispatch`；**API / endpoint** 為 Step 4–7 的 `create_app`、server 入口與端到端；**Frontend behavior** 本單元無變更。Environment/build configuration 為 Step 8–11、13；Documentation and traceability 為 Step 12、14。方法論未改。

## Testing Contract

```json
{
  "version": 1,
  "methodology": "test-after",
  "source": "fallback",
  "ordering": "Implement each testable layer, then write and run that layer's tests.",
  "scope": "agent-orchestration-brain",
  "test_strategy": "standard",
  "project_type": "brownfield",
  "applicable_notes": [
    {
      "layer": "org",
      "text": "We treat tests as a first-class deliverable in every Bolt. Specific\nmethodology — TDD, BDD, ATDD, or classic test-after — is captured by the\ntesting-strategy stage when it ships.\n\nUntil then, our default per scope is:\n- `mvp`, `enterprise`, `feature`, `infra` → tests written alongside\n  code; minimum 80% line coverage; tests run in CI before merge.\n- `bugfix`, `security-patch` → regression test for the specific\n  bug/vulnerability; existing test suite must remain green.\n- `poc`, `refactor`, `workshop` → existing test suite remains green;\n  no new test floor required.\n\nAffirm a stricter posture in `team.md` if the team commits to one."
    },
    {
      "layer": "team",
      "text": "### 既成事實\n\n- **Backend 測試框架**為 Python 內建 `unittest` + `hypothesis` + `unittest.mock`，**未使用 pytest**。CI 以 `python -m unittest discover -s tests -v` 執行（`ci.yml`）。測試 DB 策略見 `backend/tests/helpers.py`：在任何 DB import 前 `sys.modules.setdefault(\"psycopg2\", MagicMock())`，改走 in-memory SQLite，每 session `ensure_role_permissions_seeded(db, force=True)`。規模：`backend/tests/` 21 個測試檔（HEAD `c3de2c8`；2026-08-06 版「14 個」已過時）。\n- **Frontend e2e** 為 Playwright（chromium 單一 project），涵蓋登入與 RBAC 可視性；`ui-regression` gh-aw workflow 每 PR 對短生命週期 stack 執行並回報 Kiwi TCMS。**這是真閘門**：`post-steps` 讀 `pw-report.json` 的 `.stats.unexpected`，非 0 即 `exit 1`；容忍 `stats.flaky`，`retries: 1`。HEAD 現有 e2e 涵蓋 Admin 最後活動與分頁，**無成本頁 e2e**。\n- **Frontend 完全沒有 unit／component 測試框架**：`frontend/package.json` 的 `devDependencies` 只有 `@playwright/test`，無 vitest、無 jest、無 `@testing-library/*`；`scripts` 只有 `test:e2e`。前端的唯一自動化驗證層就是 Playwright e2e。\n- **Property-based testing**：7 個檔共 13 個 `@given`（HEAD `c3de2c8`；覆蓋 `test_design_agent`、`test_wa_rule_engine`、`test_diagram_builder`、`test_diagram_icons`、`test_collab`、`test_auth`、`test_activity`），皆落在純函式模組，屬自發良好實踐。`project.md` ADR-0006 點名的三個 hard-constraint 落點（IaC generator、cost calculator、agent routing）中，**cost calculator 在本 repo 尚無對應實作模組**，故該約束目前對 repo 現況為 N/A（非豁免、非違反）。本 intent 若新建 calculator 模組，ADR-0006 PBT 約束隨即由 N/A 轉為 blocking。\n- **HTTP 層 TestClient 現況**：`backend/tests/test_user_list_endpoint.py` 用 `starlette.testclient.TestClient` 測 `/api/auth/list` 分頁欄位（樣板在 `tests/helpers.py`）。此為現行唯一 TestClient 使用例；**無 cost router 可測**。\n- **C1 / pricing 測試完全缺席**：無 `test_cost*`；`'C1'`／`\"C1\"` 在 `backend/tests/` 0 命中；`test_rbac.py` 不覆蓋 C1／C2／C3。WA `COST-*` findings 連 example-based 測試都沒有。\n- **完全沒有覆蓋率量測機制**（無 `.coveragerc`、無 `coverage`／`pytest-cov`、CI 無 coverage step）。`org.md` 宣告的「最低 80% line coverage」目前**既無法量測也無法強制，是宣告而非閘門**。\n- **既有授權測試皆在 service 層**：`test_rbac.py`、`test_j5_authz.py`、`test_review_authz.py` 皆非 HTTP 層測試。\n\n### 本輪新增規則（Q4 定案：A + B + C，D 不採）\n\n依據：本 intent 的六道現有 CI 閘門（`repo-contract`、frontend lint、`tsc -b`、backend import smoke、backend `unittest`、`ui-regression`）逐一查證後，**對「後端漏欄位、序列化成 null、前端渲染成空白」這條失敗路徑全部無效**——不是覆蓋率不足的程度問題，是這條變更路徑上沒有任何自動化斷言存在的有無問題。三項零新依賴的測試底線本輪起生效：\n\n- **A — 授權矩陣變更需 allow/deny 雙向測試**：任何 `role_permissions` 預設值變更，必須有測試同時驗證「該角色能做到」與「其他角色做不到」。零新依賴，直接擴充既有 `test_rbac.py`／`test_j5_authz.py` 形狀。C1 的 RBAC seed 種子已存在（`FinOps_Analyst` 與 C1 相關欄位）；若本 intent 改動 C1 預設值（例如讓架構師 edit 時數），屬 seed 變更，須 A 規則測試。\n- **B — 新增或修改 HTTP 端點需 `TestClient` 測試**：斷言其 status code 與 `response_model` 的欄位集合。採用成本為零——`backend/requirements.txt` 已含 `fastapi[standard]` 與 `httpx`，`starlette.testclient.TestClient` 前置條件已滿足；新測試檔放進 `backend/tests/` 即被現有 `python -m unittest discover -s tests` 撿到；`get_db`（`database.py:31`）與 `get_current_user`（`services/auth.py:39`）為穩定的模組層函式，可用 `app.dependency_overrides` 覆寫；以 `TestClient(app)` 直接使用不觸發 `@app.on_event(\"startup\")` 的 `init_db()`，不需要真實 DB。C1 若新增 `/api/cost*` 端點，須依 B 規則補 TestClient 測試，且 CI 的 OpenAPI drift 檢查會要求同步更新 `openapi.json`。\n- **C — 前端資料形狀變更需 e2e 斷言**：例如本次 Admin 表格加欄，須新增至少一個 Playwright case 斷言表頭出現該欄位、且至少一列顯示值或既定的「從未」佔位。用既有 Playwright，不需新依賴，且是目前**唯一**能碰到前端頁面的自動化層。C1 若新建 Cost 頁，資料形狀為全新，須 C 規則 e2e 斷言。\n- **D（不採用）— 引入前端 unit／component 測試框架**：需新增依賴（Vitest 或類似），成本明顯較高，且屬獨立的工具鏈決策，不由本次加欄 feature 夾帶。C 項的 e2e 斷言已覆蓋本 intent 的加欄驗證需求。\n\n- **Q3 定案（A）— C1 HTTP 消費者的最小授權測試義務**：即使 `role_permissions` seed 資料未修改（C1 種子已存在於 `rbac_seed_data.py`），第一個 C1 HTTP 端點落地時仍須補 allow/deny 雙向 TestClient 測試——「具 C1 權限的角色應收到 2xx」與「無 C1 權限的角色應收到 403」兩個案例缺一不可。此為 A 規則與 B 規則的交叉要求，適用於本 intent 新增的任何 `/api/cost*` 端點。\n\n### 80% 覆蓋率門檻的定位\n\n**維持 `org.md` 原文，不在本檔弱化或改寫其宣稱**（把「80% 是目標不是閘門」寫進 `team.md` 會構成 `team.md` 弱化 `org.md` 的矛盾，屬 §13 learning admission 應擋下的形狀）。如實記載目前無法量測、無法強制的現況（見上），並以上述 A/B/C 三項變更範圍內、二元可判、零工具成本的規則作為現階段的實際門檻。導入 `coverage.py` 量測工具列為待補承載機制（見 `discovered-rules.md`）。\n\n---"
    },
    {
      "layer": "project",
      "text": "**Property-based testing 為 hard constraint**（ADR-0006）。下列核心模組的測試必須包含 property-based 測試，不得只有 example-based：IaC generator、cost calculator、agent routing。其餘模組沿用 `org.md` 的預設門檻。"
    }
  ],
  "obligations": {
    "strategy": "standard",
    "strategy_volume": [
      "Five to eight tests per component.",
      "Unit tests plus integration tests for key boundaries.",
      "Add E2E, performance, or security tests when requirements demand them."
    ],
    "scope_floor": [
      "Keep the existing test suite green.",
      "This scope adds no extra new-test floor beyond the selected test strategy."
    ],
    "combination_rule": "Apply every selected-strategy obligation and every scope-floor obligation; neither replaces the other, and a targeted scope regression may add the narrowest necessary test type beyond the strategy default."
  },
  "plan_profile": {
    "methodology": "test-after",
    "runner_step": "Verify the existing test runner/configuration and record the exact unit-scoped command.",
    "runner_ready_before_first_test": true,
    "testable_layers": [
      "Data model / database behavior",
      "Repository / data access",
      "Business logic",
      "API / endpoint",
      "Frontend behavior"
    ],
    "steps": [
      "Project structure and production configuration skeleton.",
      "Verify the existing test runner/configuration and record the exact unit-scoped command.",
      "Data model / database behavior - implement.",
      "Data model / database behavior - write and run its tests after implementation.",
      "Repository / data access - implement.",
      "Repository / data access - write and run its tests after implementation.",
      "Business logic - implement.",
      "Business logic - write and run its tests after implementation.",
      "API / endpoint - implement.",
      "API / endpoint - write and run its tests after implementation.",
      "Frontend behavior - implement.",
      "Frontend behavior - write and run its tests after implementation.",
      "Environment/build configuration.",
      "Documentation and traceability."
    ]
  },
  "input_sha256": "sha256:1aedc10dd7de9a19bd06fecb49cbcb5f27456db7ce4b18e81d500355d460bea6",
  "contract_sha256": "sha256:1f0b6822601f52ff3e71a9bd20a949c9e106f87999f78c986398d5e1963f2f77"
}
```
