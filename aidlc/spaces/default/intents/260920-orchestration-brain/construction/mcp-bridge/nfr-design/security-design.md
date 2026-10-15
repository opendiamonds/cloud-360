# 安全設計 — `U21 mcp-bridge`

> 承接 `../nfr-requirements/security-requirements.md` 的 `NFR21.4`–`NFR21.19`。本站對這十六條的工作是把「判準」變成「做法」：每一條寫出
> 它落在哪個模組、在哪個時點、以什麼結構承載，以及哪一個檢查會在被改壞時失敗。模組名以 `logical-components.md` §一 為準；
> 「靜態讀」的定義見 `performance-design.md` 檔頭。規則內容以 `../functional-design/rules.md` 為準，本檔不重開規則。

## 一、token 的生命週期（`NFR21.7`、`NFR21.8`、`NFR21.13`、`NFR21.14`、`NFR21.18`）

| 時點 | 位置 | 做法 |
|---|---|---|
| 取得 | `guards.CredentialContext`（ASGI 中介層，`/mcp` 才經過） | 從 ASGI `scope["headers"]` 取 `authorization` 的**全部**值（多值時保留為多值，交 `credentials.parse_credential` 判為 `unauthenticated`，`NFR21.11`），連同 `x-cloud360-agent` 放入 `ContextVar` |
| 持有 | `ContextVar` 的值（只存在於該請求的 context） | 不寫進任何物件的 `repr`；`RequestCredential` 以 `@dataclass(repr=False)` 的欄位持有原值 |
| 使用 | `executor.exchange` | `client.build_request(..., headers={"Authorization": credential.raw})`——**唯一**把 token 放進對外請求的點；client 本身不設預設 `Authorization`（`BR73.3`） |
| 回應 | 不回送 | 工具結果只含 backend 本體或 `BR76.1` 的固定訊息（`BR73.4`、`BR76.4`） |
| 釋放 | `CredentialContext` 的 `finally` | `ContextVar.reset(token)`，任何結束路徑皆執行（`NFR21.28`） |

**cookie（`NFR21.14`；帶入項 `R-20` 第 2 點，擇 (b)）**：靜讀 `httpx 0.28.1` 的 `_client.py:1022`／`:1737`：`send` 會把回應的
`Set-Cookie` 寫入 client 共用的 jar，之後的請求自動帶上——這正是 `R-20` 指出的跨使用者外洩路徑。設計：`build_backend_client` 傳入一個
以 `http.cookiejar.DefaultCookiePolicy(allowed_domains=[])` 建立的 jar（允許網域為空集合 → 拒收一切 cookie）。jar 永遠為空，**不需要在
請求之間清空**，因此沒有並發下「清空不是原子操作」的問題。不擇 (a)（見 `Set-Cookie` 即失敗）的理由：backend 日後任何一個 cookie 都會使
全部工具呼叫失敗。httpx 是否完全遵守此政策**未實測**，`NFR21.14` 的判準（含屏障並發版本）即為其驗證。

**身分隔離的屏障（`NFR21.7`；帶入項 functional-design `R-15`）**：屏障放在 backend 外層的記錄包裝內（`asyncio.Event`），兩條依賴路線的
backend 都在測試自己的事件迴圈內（`reliability-design.md` §6.2），故屏障不跨進程。扣住使用者 A 的第一個 backend 請求，直到記錄包裝
**已收到**使用者 B 的請求再同時放行——「B 已進入 bridge 並設定其 contextvar」的可觀察代理是「B 的請求已抵達 backend」。突變（token 改存
模組層變數）在有屏障時必定紅燈，為 `code-generation` 的完成條件。

## 二、請求前置閘的層序與網路面（`NFR21.16`、`NFR21.19`、`NFR21.20`、`NFR21.21`；帶入項 `R-04`、`R-18`）

層序見 `logical-components.md` §二：`/healthz` 在全部閘門之外；`/mcp` 依序經 `ConcurrencyGate` → `BodyLimit` → `CredentialContext` → SDK
（Host 檢查）→ 工具函式。

| 面 | 做法 | 判準落點 |
|---|---|---|
| 設定來源 | 全部設定只經 `cli.parse_args` 的命令列參數與 `limits.py` 的常數；`backend/mcp_bridge/` 與 `gen_mcp_tools.py` 內無任何環境變數讀取（`BR71.1`）。測試的路線宣告是 `mcp_topology.py` 的常數、venv 位置是固定路徑，也不讀環境變數——不是因為掃描器（`validate_env_contract.py:245-246` 排除路徑含 `tests` 者），而是讓路線在 CI 與開發機上由同一行程式決定，不隨環境漂移 | `NFR21.17` |
| 監聽位址 | `cli.parse_args` 的 `--host` 預設 `127.0.0.1`（`R-18`）；compose `command` 明列 `--host 0.0.0.0` | `NFR21.16` ①② |
| Host 允許清單 | `limits.derive_allowed_hosts(port) -> tuple[str, ...]` 為純函式：`(f"mcp-bridge:{port}", f"localhost:{port}", f"127.0.0.1:{port}")`；`cli` 以 `--port` 推導後傳給 `create_app`，再交給 SDK 的傳輸安全設定（靜讀 `mcp 1.29.0` 的 `transport_security.py:24`、`:52-57` 有 `allowed_hosts`） | `NFR21.16` ③ 改為：(i) 單元測試 `derive_allowed_hosts(8080)` 恰為三項；(ii) 單元測試非預設埠（例如 18080）恰為對應三項；(iii) 端到端以測試的實際埠推導、`Host: evil.example` 被拒、`Host: 127.0.0.1:<埠>` 通過（`R-04` 第 1 點） |
| 對外暴露 | 無 `ports:`、只在 `internal` | `NFR21.16` ②、`NFR21.32` |
| 免認證面 | `/healthz` 回模組常數 `{"status":"ok"}`；`tools/list` 由 SDK 以 `tool_specs` 的 `name`／`description`／`inputSchema` 產生，`binding` 不交給 SDK | `NFR21.19` |
| 濫用上限 | 並行閘、本體上限（`scalability-design.md` §一、§二） | `NFR21.20`、`NFR21.21` |

**措辭更正（`R-04` 第 2 點）**：nfr-requirements 的「網路暴露面零新增」改讀為「**對外（`edge`、host）**暴露面零新增」。`internal` 網段內
是**新增**了一個可達端點：`deploy/docker-compose.deploy.yml:416` 的 `internal` 是一般 bridge 網路（非 `internal: true`），`db`、`redis`、
`ollama` 所在的容器都能連到 `mcp-bridge:8080/mcp`。沒有任何機制限制「僅供大腦連接」；這是 `[G2]`=A 已接受的信任邊界，與上游
`requirements.md:619`「第二個新增進程邊界…不得對外暴露，僅供同主機的大腦進程連接」的「適用（新增一處）」方向一致。

## 三、工具函式與 SDK 的交界（`NFR21.8`、`NFR21.29`；帶入項 functional-design `R-19`）

| SDK 行為（靜讀 `mcp 1.29.0`） | 風險 | 設計 |
|---|---|---|
| `call_tool(validate_input=True)` 預設先以 `jsonschema` 驗證，失敗回 `"Input validation error: {e.message}"`（`server.py:498-537`） | 訊息引用不合格的值 → 違反不回顯；不經封閉表與 log | `validate_input=False`；驗證全由 `calls.validate_arguments`（`observability-design.md` §二） |
| 工具函式拋出的任何例外被轉成 `_make_error_result(str(e))`（`server.py:589-590`） | 例外文字原樣回給 agent | `dispatch.run_tool_call` 以 `except Exception` 總攔截，一律回 `internal_error`；`app.py` 的工具函式本身不含可拋例外的邏輯（`reliability-design.md` §3.2） |
| 未列出的工具名以 WARNING 原值記錄（`server.py:494`） | log 注入 | 該 logger 設 ERROR；formatter 單行化（`observability-design.md` §一） |

以上三點都以「所釘版本**若同樣如此**」為前提；code-generation 第一步確認所釘版本後，`NFR21.8`、`NFR21.34` 的端到端判準即為其驗證。

## 四、輸入驗證（`NFR21.9`、`NFR21.11`、`NFR21.15`；帶入項 functional-design `R-13`）

- `calls.py` 定義兩個編譯後的模組常數：`SEGMENT_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")`（字串與 `KEY_PATTERN.pattern` **逐字相同**，
  `requirement_field_definitions.py:33`，使 `NFR21.10` 的相等斷言原樣成立）、`SYSTEM_ID_PATTERN = re.compile(r"^[0-9]{1,18}$")`，一律以
  `.fullmatch()` 判定。`$` 在結尾換行之前也能匹配，但 `fullmatch` 要求匹配範圍等於整個字串，故 `"cost\n"` 不通過；突變「改用 `.match()`」
  時 `$` 放行結尾換行，`NFR21.9` 的換行案例必然紅燈（`R-13`）。
- 驗證順序固定（MB-W3）：憑證（`parse_credential`）→ agent（`resolve_agent`）→ 參數（`validate_arguments`）→ 組請求；前三步任一失敗都
  不建立 `BackendCall`，故「記錄包裝 0 筆」由結構保證。
- `Authorization` 的 8192 位元組上限（`NFR21.11`）在 `parse_credential` 判定；`BodyLimit` 管的是本體，兩者不重疊。

## 五、宣告面與啟動驗證（`NFR21.4`–`NFR21.6`、`NFR21.10`）

- 啟動讀三份檔（`R-12` 擇 (a)，`reliability-design.md` §五）：`generated_tools.json`、`agents.json`、`allowlist.json`。
  `validate_tool_specs(specs, allowlist)` 以 `allowlist.json` 為獨立參考，並重跑底線、`requires_agent` 綁定與路徑前綴白名單。
- `NFR21.4` 的期望集合為測試檔字面值、不讀 `allowlist.json`——與啟動的參考集合**刻意不同源**，使「同改 allowlist 與產物」的自證被擋下。
- `NFR21.5`：`gen_mcp_tools.py` 的讀取集合封閉，與啟動讀三份檔無關（兩者是不同的進入點）。

## 六、授權（`NFR21.12`、`NFR21.13`）

bridge 不做任何授權判定：`dispatch` 與純函式模組只決定「要不要送、送什麼」，「准不准」完全由 backend 的 facade 判定（`BR75.1`）。
可執行檢查沿用 `NFR21.12` 原文的 grep（`require_story_action`、`user_can`、`resolve_project_role` 為 0；import 不含 `services.`），範圍為
`backend/mcp_bridge/` 全部模組。`follow_redirects=False` 設在 `build_backend_client`（`NFR21.13`），且 `exchange` 不另行處理 3xx——
3xx 落入 `BR76.1` 的「其他狀態碼」→ `internal_error`。

## 七、Encryption（`OPEN-MB21-13`；帶入項 `R-03`）

**已由使用者確認**：2026-10-14T23:02:07Z，使用者經選單確認**接受**以明文在 `internal` 網段攜帶使用者 JWT，沿用 `[G2]`=A 的信任邊界
（殘留：同主機任一容器被攻破即可竊聽 token）。`OPEN-MB21-13` 依此結案（`../carried-review-items.md:25`）。本站不新增傳輸加密。

靜態：bridge 不落地任何 token、工具參數或結果（`security-requirements.md` 第一節）；`BridgeFormatter` 與 log 禁令使 token 不進 stderr。
不可逆面（token 進 LLM context）由 `NFR21.4`、`NFR21.6`、`NFR21.8` 承擔，與傳輸形式無關。

## 八、讀取稽核（`OPEN-MB21-14`，`[MBN1]`=A）

沿用 nfr-requirements 第五節：成功讀取不新增帶使用者身分的紀錄，bridge 不解碼 JWT（`NFR21.18`：`jwt`、`jose`、`base64` 的 import 為 0）。
本站另確認：第二退路下 `mcp` 會傳遞帶入 `pyjwt`（靜讀其 `METADATA`），但 bridge 模組**不 import** 它——`NFR21.18` 的 grep 對象是 import
陳述，不受依賴樹影響。

## 九、ADR-0006 四面向（逐格對照上游，無一格相反）

逐格對照 `../nfr-requirements/security-requirements.md` 第六節（四格皆「適用」）與上游 `requirements.md:617-620`（四格皆「適用」）：

| 面向 | 判定 | 本站的做法落點 |
|---|---|---|
| **IAM** | **適用** | 不新增身分、服務帳號或 secret；授權只在 facade（§六）；身分只來自每請求的標頭、`ContextVar` 隔離並以屏障驗證（§一）；拒收 cookie 堵住跨使用者的隱性身分（§一）；啟動以獨立參考集合驗證工具宣告（§五） |
| **Encryption** | **適用** | 傳輸：明文於 `internal` 網段，使用者已確認接受（§七，`R-03`）。不可逆面：schema 白名單與底線、手改產物不得啟動、結果與 log 不外洩、SDK 預先驗證的回顯路徑關閉（§三、§五）。靜態：無落地 |
| **Network exposure** | **適用** | **對外**（`edge`、host）零新增；`internal` 網段內新增一個任意同網段容器可達的 `/mcp`（§二，`R-04` 措辭更正）；`--host` 預設迴環、Host 允許清單隨埠推導；並行閘與本體上限、`/healthz` 不受閘門影響（`scalability-design.md` §一、§二） |
| **Audit logging** | **適用** | 寫入與清空的主體為使用者本人（`BR77.3`，`NFR21.12` ①）；每次工具呼叫恰一行、HTTP 層拒絕亦留一行、全部單行防注入（`observability-design.md`）；讀取面依 `[MBN1]`=A（§八）；關聯鍵本版不設、後果揭露（`observability-design.md` §六） |

**PBT hard constraint**：`project.md` 點名的三個落點不含本單元，但產生器是 `functional-spec.md` §六 判定的**必須**標的；本站把閘門定為
決定性（`R-14` 擇 (a)，`logical-components.md` §四），突變表七列仍為必做。不以 N/A 處理。

## 十、送審前自檢（七項；全部產出寫完後實算，數字皆由 grep／jq／shell 取得，未執行任何測試或 Python 程式）

| # | 項目 | 結果 |
|---|---|---|
| 1 | **可達性** | 每條「偵測 X」逐一可構造：超額 503 以記錄包裝的屏障扣住進行中請求構造（閘門計到回應送完為止）；飽和下 `/healthz` 200 因其在全部閘門之外；chunked 超量由 `BodyLimit` 累計位元組；`ResponseTooLarge` 由記錄包裝串流 2 MiB；`dns` 以 `.invalid` 網域；contextvar 殘留以「內層拋例外＋下一請求無標頭」；未知工具名可達本單元的工具函式（靜讀 `server.py:531-541`：工具定義為 `None` 時跳過驗證、照常呼叫工具函式）；第二退路的前置條件缺失以 `AssertionError` 呈現（不是 skip）。**依賴未實測外部行為者如實標註**：`dns` 與 `refused` 的區分（`reliability-design.md` §1.2，兩者對外行為相同）、httpx 對拒收政策的遵守（§一）、SDK 是否於 client 斷線時取消工具 task（`OPEN-MB21-16`）、所釘 SDK 能否產生協定錯誤（`OPEN-MB21-17`）——皆有對應的二元判準由 code-generation 實測 |
| 2 | **契約端點三問**（全部產出） | 以 `for` 迴圈逐詞 `grep -cF` 掃七份產出 30 個本站新增的識別字：29 個出現在 ≥ 2 個檔；唯一只出現在 1 個檔的是 `in_flight`，判定為 `ConcurrencyGate` 的**內部**狀態（寫＝判定通過後 `+= 1`、讀＝與上限比較、清＝`finally` 的 `-= 1`，三者皆在 `scalability-design.md` §1.2），非孤兒。其餘新欄位：`ContextVar` 值 寫＝`CredentialContext`、讀＝`dispatch`／`executor`、清＝`finally` 的 `reset`；cookie jar 寫＝httpx（被政策拒收）、讀＝`build_request`、清＝不需要（永遠為空）；`MCP_ROUTE` 寫＝code-generation 一次、讀＝`mcp_topology` 輔助；`request_rejected` 行 寫＝兩個閘門、讀＝測試與 `build-and-test`；`stop_grace_period` 寫＝`infrastructure-design`（→ `code-generation`）、讀＝compose。方法：`run_tool_call` 擁有＝`dispatch`、呼叫＝`app.py` 工具函式與單元測試；`load_and_validate`／`main` 擁有＝`startup`／`cli`、呼叫＝`__main__` 與 `NFR21.6` 測試；`serve` 擁有＝`server`、呼叫＝`cli.main`；`derive_allowed_hosts` 擁有＝`limits`、呼叫＝`cli` 與單元測試。**本項查出並修正 1 處**：初稿把 `tool_call` 那一行的寫出點放在 `app.py`（含 `mcp`），使第二退路下 `NFR21.29` 的 log 斷言無法在主直譯器驗證；已改為 `dispatch` 的 `finally`（`observability-design.md` §二、`reliability-design.md` §3.2） |
| 3 | **引用逐字核對**（事實與定位分開驗） | 本站全部 `檔名:行號` 以 `sed -n` 逐一印出核對：`requirement_field_definitions.py:33`（`KEY_PATTERN` 含 `^`／`$`）／`:36`、`backend/requirements.txt:10`（未釘版的 `uvicorn`）、`backend/tests/helpers.py:42-48`（`StaticPool`＋`check_same_thread=False`）、`deploy/docker-compose.deploy.yml:416`（`internal:`）、`.gitignore:38`（`*venv/`）、`backend/Dockerfile:14`（`WORKDIR /app`）、`requirements.md:617-620`／`:619`、`validate_env_contract.py:245-246`、`../carried-review-items.md:25`／`:26`；另一 clone 的套件原始碼：`uvicorn/config.py:229`／`:231`、`uvicorn/server.py:76-77`、`httpx/_client.py:1022`／`:1737`、`mcp/server/lowlevel/server.py:494`／`:498-537`／`:531-541`／`:589-590`、`streamable_http_manager.py:58`、`transport_security.py:24`／`:52-57`、`mcp-1.29.0` 的 `METADATA` `Requires-Dist`。**更正 3 處**：(a) 初稿寫 `validate_env_contract.py` 掃描「含測試」，實讀 `:245-246` 是**排除**路徑含 `tests` 者——已改寫理由（§二）；(b) `uvicorn/server.py:76` 是 `run`，`serve(sockets=…)` 的呼叫在 `:77`，改為 `:76-77`；(c) 初稿設計以「去錨後比對」做 `NFR21.10` 的一致性斷言，實讀 `:33` 後改為與 `KEY_PATTERN.pattern` 逐字相同、以 `fullmatch` 判定，使 `NFR21.10` 原判準不需改寫（§四） |
| 4 | **檔案集合一致性** | 本站 `ls`：六份 `.md` 產出＋問題檔＋`traceability.json`，共 8 個檔；與前例 `brain-gateway/nfr-design/` 的檔名集合以 `diff` 比對**相同**（前例另有審查產生的 `reviews/`，本站尚未送審） |
| 5 | **跨檔傳播**（按事實、逐種表達 grep；計數**不含本節 §十 自身**） | 逐事實以 `grep -cF` 掃七份產出：「由 uvicorn」4 行命中，3 行為「原文／被取代」語境（`logical-components.md` §六、問題檔 #1、`scalability-design.md` §1.4），1 行為 keep-alive 由 uvicorn 關閉（`scalability-design.md` §1.2，無關並行上限）；`limit_concurrency` 只以「不設定」出現；`R-12`／`R-14`／`R-20` 的擇定（`擇 (a)` 10 處、`擇 (b)` 3 處）方向一致；`17825792`／`17 MiB` 在 `scalability-design.md` §六 與 `logical-components.md` §三 一致；`15s` 在問題檔、`reliability-design.md` §八、`logical-components.md` §五 一致；「零新增」只出現於 §二 的措辭更正與 §九；`validate_input=False` 在 `observability-design.md`、本檔、`logical-components.md` 一致；`configure_logging` 的位置只在 `logical-components.md` §六 以「被取代」出現 `app.py`。**本項查出並修正 1 處**：兩處對 `infrastructure-design`（CONDITIONAL）的交接（`stop_grace_period`、記憶體上限）未寫轉移目標，已補「若被 skip 轉 `code-generation`」（`reliability-design.md` §八、`scalability-design.md` §六）。他單元規則字面：`BR` 識別字不屬 `BR71`–`BR78` 者 0；`NFR13.` 0；引用的 `BR7x.y` 對 `rules.md` 的 `id:` 列比對，未定義者為空 |
| 6 | **可算的數字先算再寫** | `traceability.json` 以 `jq` 實算：`upstream_ids` **41**、`coverage` **41**、`OK` **41**、兩向集合差為空；與 `../nfr-requirements/` 以 `grep -ohE '\*\*\`NFR21\.[0-9]+\`\*\*'` 抽出的定義集合（**41**）以 `comm` 比對無差。target 分佈：performance 3、security 15、scalability 5、reliability 9、observability 4、logical-components 5，合計 41。帶入項 **21** ＝ 以設計收斂 17 ＋ 使用者已確認 1 ＋ 維持帶入 3（`logical-components.md` §五 末行）。算式（shell 整數運算與 `bc`）：24876、25900、65536／25900 ≈ 2.53、65536／24876 ≈ 2.63、1048576／84000 ≈ 12.48、16 ×（65536＋1048576）＝ 17825792。標為**估計**而非實算者：JSON-RPC 外殼 1024 位元組、1 MiB JSON 解碼的毫秒級耗時、`initialize`／`tools/list` 的毫秒級佔用 |
| 7 | **ADR-0006 四面向 ＋ PBT hard constraint** | §九 逐格對照 `../nfr-requirements/security-requirements.md` 第六節與上游 `requirements.md:617-620`：上游四格「適用」、nfr-requirements 四格「適用」、本表四格「適用」，**無一格相反**。Network exposure 一格**刻意與 nfr-requirements 的措辭不同**：該站寫「零新增」，本站依 `R-04` 改為「對外零新增、`internal` 網段內新增一處」，理由是上游 `requirements.md:619` 的判定為「適用（新增一處）」——本站的寫法與上游一致、與 nfr-requirements 的舊措辭不一致，屬更正而非覆蓋。Encryption 一格引用使用者 2026-10-14T23:02:07Z 的確認，不改判。PBT：落 `NFR21.39`，閘門擇 (a) 為結構性決定，突變表七列必做；`project.md` 點名的三個落點不含本單元，不以 N/A 處理 |
