# Unit Test Instructions — `U21 mcp-bridge`

## 一、框架與設定

- **後端測試框架**：Python 內建 `unittest` ＋ `unittest.mock` ＋ `hypothesis`，**不是 pytest**。非同步案例用 `unittest.IsolatedAsyncioTestCase`。
- **PBT 閘門是決定性的**：產生器的八個類別各寫一個 `@given`（`consistent`、`renamed_clean`、`credential_injected`、`renamed_dirty`、`whitelist_drift`、`missing_op`、`out_of_scope`、`agent_mismatch`）。每個測試只生成自己的類別，所以不設比例下限，成功分支本身就是 `consistent`／`renamed_clean` 兩個測試的生成目標。策略先產生一致的 (openapi, allowlist) 配對，再施加且只施加一種破壞，allowlist 一律由 openapi 衍生。
- **兩條依賴路線**：路線由 `backend/tests/mcp_topology.py` 的常數 `MCP_ROUTE` 決定（Step 1 設定一次，不讀環境變數）。
  - `same-interpreter`（路線 A／B）：官方 SDK client 經真實 HTTP 連到 `create_app` 加 `uvicorn.Server`，bridge 起在 `127.0.0.1` 的預先綁定 socket；bridge 以 `httpx.ASGITransport` 直達「記錄包裝(`main.app`)」；資料庫用 `tests/helpers.py:41-56` 的 SQLite（`StaticPool`）。
  - `isolated-venv`（路線 C）：手寫的最小 JSON-RPC client 連到跑在 `.mcp-venv/` 子進程內的 bridge；backend 以 `uvicorn.Server` 起在測試的事件迴圈內。子進程一律用 `asyncio.create_subprocess_exec`，測試端不阻塞事件迴圈。另有一案 SDK 互通，至少涵蓋一次 `isError` 與一次成功。
  - 兩條路線共用同一份斷言程式，只換 `McpClientPort` 與 `LogSource` 的實作。
- **非 SDK 的檢查在主直譯器跑，兩條路線相同**：純函式、PBT、三個閘門（以假內層應用驅動）、`dispatch`／`executor`、`startup`／`cli`，以及產物、靜態、部署檔的斷言。這些模組都不 import `mcp`，`__init__.py` 為空。
- **屏障**：記錄包裝內的 `asyncio.Event`，與測試在同一個事件迴圈內（兩條路線皆然），用來決定交錯順序。不靠 `asyncio.gather` 的機率。
- **時限**：每個端到端案例以 `asyncio.timeout(30)` 包住；子進程就緒的上限 10 秒；逾時以 `AssertionError` 失敗並終止子進程。
- **skip 禁令**：本單元所有測試檔中，`skipTest`／`skipUnless`／`skipIf`／`SkipTest` 出現 0 次。缺 `mcp` 或缺 venv 時一律 `AssertionError`，訊息指出建立指令。
- **授權不 mock**：backend 走真實的 `get_current_user`、facade、`ensure_role_permissions_seeded`；bridge 不做授權判定。
- **前端**：本單元沒有前端變更。

## 二、本單元的執行指令（都限定本單元的檔案）

在 `backend/` 目錄執行：

```bash
# 就緒檢查（Step 1）：執行器與端到端會重用的需求欄位 HTTP 測試
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_requirement_field_http -v

# 純函式與 PBT（Step 2）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_generator tests.test_mcp_bridge_pure -v

# 中介層、dispatch、executor（Step 3）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_guards tests.test_mcp_bridge_dispatch -v

# create_app（Step 4）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_app -v

# 啟動入口（Step 5）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_startup -v

# 拓樸自測（Step 6）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_topology -v

# 產物與完整端到端（Step 7）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_artifacts tests.test_mcp_bridge_e2e -v

# 靜態與部署檔斷言（Step 8–13）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_static tests.test_mcp_bridge_deploy -v

# 全單元（Step 14）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_mcp_bridge_generator tests.test_mcp_bridge_pure tests.test_mcp_bridge_guards tests.test_mcp_bridge_dispatch tests.test_mcp_bridge_app tests.test_mcp_bridge_startup tests.test_mcp_bridge_topology tests.test_mcp_bridge_artifacts tests.test_mcp_bridge_e2e tests.test_mcp_bridge_static tests.test_mcp_bridge_deploy -v

# 漂移閘門
python3 scripts/gen_mcp_tools.py --check
```

在 repo 根目錄執行（IC-11）：

```bash
python3 scripts/validate_repo_contract.py
python3 scripts/validate_env_contract.py
```

**只在路線 C**，跑上面任一指令之前，先在 repo 根目錄建 `.mcp-venv/`：`python3 -m venv .mcp-venv && .mcp-venv/bin/pip install -r backend/requirements-mcp.txt`。這個目錄由 `.gitignore:38` 的 `*venv/` 排除，也不在 backend 映像的 build context 內。

## 三、測試清單與數量（standard：每元件 5–8 案；純函式含 PBT）

| 檔案 | 元件 | 案例 |
|---|---|---|
| `test_mcp_bridge_generator.py` | 產生器 | 八個類別各一個 `@given`；性質一（含任何深度、大小寫變體、只寫進 openapi 的子變體）、二、三、四（打亂鍵順序結果不變）、五、七；example：以 repo 的 `openapi.json` 加 `allowlist.json` 產生成功（證明黑名單檢查在 rename 之後）；`validate_tool_specs` 拒絕手改產物 |
| `test_mcp_bridge_pure.py` | `calls`／`outcomes`／`credentials`／`agents`／`limits` | 性質六（策略含 `"."`、`".."`、`"/"`、`"%2e%2e"`、`"?"`、`"#"`、空白、非 ASCII、結尾換行、內嵌換行；判準是 `build_request` 組出的 URL）；`map_outcome` 封閉表逐列，`TransportFailure` 四值逐值，`ResponseTooLarge`／`InternalFailure` 映射為 `internal_error`、`retryable: false`；`detail` 過濾（多鍵、非字串、超長、控制字元）；`parse_credential`（缺漏、非 Bearer、多值、超過 8192 位元組）；`resolve_agent`（讀取不要求、未宣告、未登錄）；`derive_allowed_hosts(8080)` 恰為三項、`(18080)` 為對應三項；`BR74.6` 空白值 |
| `test_mcp_bridge_guards.py` | 三個中介層與路由 | 判準 ①–⑤（超額 503 加 `Retry-After` 且恰一筆 `request_rejected`、放行後同一連線恢復、`/healthz` 在 16 格滿時仍 200、預設 16、實例獨立）；`Content-Length` 超量與 chunked 超量都是 413；16 條每秒 1 位元組的慢速上傳在期限到後 408、名額歸還、`/healthz` 全程 200；GET 帶 `Accept: text/event-stream` 立即 405 且不佔名額；`/mcp/` 與 `/mcp/x` 回 404、超量本體仍 413、內層未被呼叫；`CredentialContext` 遇內層例外後，下一個請求讀到空值（`NFR21.28` 單元層） |
| `test_mcp_bridge_dispatch.py` | `run_tool_call`／`executor` | `ConnectError`→`refused`、`.invalid`→`dns`（依 K-10）、`ReadTimeout`／`PoolTimeout`→`timeout`、`RemoteProtocolError`→`protocol`、其他例外→`InternalFailure`；`read_bounded` 對 2 MiB 串流停止讀取；`Set-Cookie` 不進 jar、下一個請求沒有 `Cookie`；`SECRET-MARKER` 不進結果與 log（`NFR21.29`）；每個分支恰一行 `tool_call`；`tool="evil\nINJECTED"` 記成 `tool=unknown`；`agent` 換行注入；16-B 時取消路徑只寫一行 |
| `test_mcp_bridge_app.py` | `create_app` | `initialize`／`tools/list` 不需認證，且不含 `binding`；`tools/call` 沒有 `Authorization` 時得到 `unauthenticated`、記錄包裝 0 筆；Host `evil.example` 被拒；未知工具（17-A 協定錯誤；17-B 為 `invalid_argument`），訊息不回顯；處理函式不讓任何例外流進 SDK；`/healthz` 回固定本體 |
| `test_mcp_bridge_startup.py` | `cli`／`startup`／`__main__` | T-8 六案（拿掉 `requires_agent`、加入 `/api/membership/`、加入 `api_key`、`inputSchema` 多一個屬性、檔案缺失、非 JSON），全部回傳 1、恰一行 ERROR、沒有 traceback；`--host` 預設 `127.0.0.1`；`--max-concurrency` 預設 16；`__main__.py` 的 AST 形狀；驗證通過前不 import `server` |
| `test_mcp_bridge_topology.py` | 驗證拓樸 | 拓樸可起；`list_tools` 有回應；Host 依實際埠推導；`LogSource` 讀得到 `startup port=<埠>`；`MCP_ROUTE` 的前置條件缺失時是 `AssertionError`；逾時會終止子進程（路線 C）；路線 C 的 SDK 互通涵蓋一次 `isError` 與一次成功 |
| `test_mcp_bridge_artifacts.py` | 三份產物與腳本 | T-5：期望白名單為測試檔內字面值，不讀 `allowlist.json`；T-6：攔截 `open`，兩種模式都只開 `openapi.json`、`allowlist.json`（加寫出的 `generated_tools.json`）；T-7：`SEGMENT_PATTERN.pattern == KEY_PATTERN.pattern ==` allowlist 的 `property_patterns`，`agents.json` 的值 ⊆ `GROUPS_BY_KEY`；`--check` 一致時綠燈、手改後紅燈 |
| `test_mcp_bridge_e2e.py` | 端到端 | T-1：屏障交錯，讀與寫各 ≥ 20 次，backend 收到的 `Authorization` 等於發起者，`updated_by` 各自正確；T-2：`BR76.1` 每一列（本地與 backend 兩種來源）加成功的讀與寫，結果全文與全部 log 都不含完整 token、簽章段、`"Bearer "`＋token；T-4：`"."`、`".."`、`"a/b"`、`"%2e%2e"`、`"cost\n"` 都得到 `invalid_argument` 且記錄包裝 0 筆；`AC11.4.1`、`AC11.4.3`；寫入的 `on_behalf_of` 由登錄表填入；清空走 `DELETE`；backend 回 503、連線拒絕、逾時都得到 `backend_unavailable` 且進程存活；`Mcp-Session-Id` 不出現；5 次 `/healthz` 不產生存取紀錄；斷線案例（16 分支）的行數恰 1；慢速 backend 加斷線迴圈後連線池未滿 |
| `test_mcp_bridge_static.py` | 結構規則 | import `mcp` 的檔案集合恰為 `{app.py, server.py}`；import `httpx` 的恰為 `{executor.py}`；`__init__.py` 為空；`main.py` 與 router 不 import `mcp_bridge`；無環境變數讀取；logger 名稱唯一；七個常數各定義恰一次；`jwt`／`jose`／`base64` 的 import 為 0；授權函式為 0；skip 為 0；`NFR21.38` 依路線斷言 |
| `test_mcp_bridge_deploy.py` | compose、CI、deploy、文件 | CC-5 全部斷言（含 `networks == ["mcp"]`、`mcp.internal is True`、成員恰為兩個、既有網段不帶 `internal: true`）；Dockerfile 依路線；`ci.yml` 的 `backend` job 含閘門與 `timeout-minutes`；`deploy.yml` 健康步驟的位置、容錯形狀、`continue-on-error`，以及「出現 client 即須阻擋」的觸發檢查；`DEPLOY.md` 的機械斷言 |

## 四、突變驗證（每項：套用 → 確認紅 → 還原 → 確認綠）

執行突變時設 `HYPOTHESIS_NO_SHRINK=1`（測試設定讀它以關閉 shrinking）。結果記入 `code-summary.md`。

| 突變 | 對應 | 預期紅燈 |
|---|---|---|
| 拿掉 `BR72.7` 的黑名單檢查 | 性質一 | `credential_injected`、`renamed_dirty` |
| 拿掉 `BR72.6` 的白名單相等檢查 | 性質五 | `whitelist_drift` |
| 把 `BR72.7` 移到 rename 之前 | 性質一 | `renamed_clean`、`renamed_dirty`，以及 repo 產物的 example |
| 把 `BR72.6` 移到 `BR72.7` 之前 | 性質一 | `credential_injected` 中只寫進 openapi 的子變體 |
| 拿掉 `BR72.10` | 性質七 | `agent_mismatch` |
| 拿掉 `BR72.11` | 性質二 | `out_of_scope` |
| `BR75.4` 退回只用 `quote`、不驗字元集 | 性質六、T-4 | `".."` 段數少一 |
| `.fullmatch()` 改成 `.match()` | functional-design R-13 | `"cost\n"` 案例 |
| token 改存模組層變數 | T-1（**完成條件**） | 屏障交錯案例 |
| 錯誤 `message` 改用 `str(exc)`；log 加入參數或標頭 | T-2 | 逐分支不外洩 |
| 在 `allowlist.json` 與產物同時加一個屬性 | T-5 | 字面白名單 |
| 腳本多讀 `.mcp.json` | T-6 | 讀取封閉 |
| 任一份樣式副本改一個字元 | T-7 | 一致性 |
| 拿掉 `validate_tool_specs` 中任一檢查 | T-8 | 對應案例 |
| `ConcurrencyGate` 套在整個應用（含 `/healthz`） | nfr-requirements R-01 | 判準 ③ |
| 並行計數改為模組全域 | nfr-requirements R-01 | 判準 ⑤ |
| `BodyLimit` 只看 `Content-Length` | `NFR21.20` | chunked 案例 |
| 拿掉本體讀取期限 | nfr-design R-01 | 慢速上傳案例 |
| 拿掉 405 守門 | nfr-design R-01 | GET SSE 案例 |
| 精確路徑改為前綴掛載 | nfr-design R-06 | `/mcp/x` 案例 |
| `tool` 欄改寫原值 | nfr-requirements R-06 | 注入案例 |
| 拿掉 `CredentialContext` 的 `finally` 重設 | `NFR21.28` | 單元層與端到端 |
| jar 改回預設政策 | functional-design R-20 | cookie 案例 |
| （16-B）名額在取消時就歸還；外層 `finally` 也寫一行 | nfr-design R-02 | 連線池案例；行數恰 1 |
| （17-A）未知工具改回 `isError` | nfr-design R-03 | 協定錯誤案例 |
| `load_and_validate` 不包 `JSONDecodeError` | nfr-design R-07 | 非 JSON 案例 |
| `--host` 預設改為 `0.0.0.0` | functional-design R-18 | `NFR21.16` ① |
| compose 加 `ports:`；或 `networks` 加入 `internal` | infrastructure-design R-01 | CC-5 |
| 健康步驟改用裸露的 `$(docker inspect …)` 指派 | CC-7 | deploy 斷言 |
| 在 `backend/services/` 加一行 `mcp-bridge:8080` 而健康步驟不改 | infrastructure-design R-02 | 觸發條件檢查 |

## 五、覆蓋率

repo 沒有覆蓋率量測機制（`team.md`）。實際門檻是：每元件 5–8 案、產生器的八類 PBT 加七條性質、必測 T-1–T-8，以及上表的突變驗證。不宣稱百分比。

## 六、Mock 與測試資料

- **身分**：測試建立 `User`，以既有方式簽發 JWT；角色經 `ensure_role_permissions_seeded(db, force=True)` 播種。至少兩位使用者，一位是專案成員、一位不是。
- **專案、系統、成員**：經既有 facade 建立，形狀比照 `tests/test_requirement_field_http.py`，不直接插表。
- **backend**：真實的 `main.app` 外面包一層記錄包裝（記下每個請求的 method、path、`Authorization`，並提供屏障）。錯誤分支以包裝回 418、非 JSON 的 200、503、2 MiB 串流、中途斷線來構造。
- **傳輸失敗**：`httpx.MockTransport` 拋出實際的例外類型；dns 用 `.invalid` 網域（判定方式依 Step 1 的 K-10）。
- **唯一標記字串**：token、agent 名、欄位值各以 `uuid4()` 產生，斷言工具結果、log、回應標頭都不含它。
- **產物**：T-8 在暫存目錄放手改的副本，不改正式檔。
- **限制揭露**：路線 A／B 的 backend 經 `ASGITransport`，沒有真實 TCP；路線 C 下，SDK client 專有的行為只由互通案例保證。
