# Functional Spec — `U21 mcp-bridge`

> 單元類型 `service`（L），部署模型 standalone：獨立進程、僅供同主機連接（`unit-of-work.md:309`）。承載故事 `US11.4`
> （`AC11.4.1`–`AC11.4.3`）。六題定案皆 A（`functional-design-questions.md`，`MB1`–`MB6`）。規則的正式來源是 `rules.md` 的 YAML；
> 本檔寫介面、流程、交接、決定、開放項與自檢。規則數 **45**（`BR71`×6、`BR72`×11、`BR73`×5、`BR74`×6、`BR75`×4、`BR76`×4、
> `BR77`×4、`BR78`×5；修訂 1 以 grep 計 `rules.md` 的 `- id: BR` 列實算，見 §十三「修訂 1」第 6 項）。

## 一、單元邊界

| 在本單元內 | 不在本單元內 |
|---|---|
| MCP server 進程（`backend/mcp_bridge/`）、`/mcp` 與 `/healthz` 兩個端點 | 大腦側 MCP client（`U11`／`U12` 的 agent 實際取用欄位）——`OPEN-MB21-1` |
| REST→MCP 產生器（純函式）、產生腳本與 `--check` 漂移模式 | 需求欄位的授權與持久化（`U20` 的 facade，經 HTTP 呼叫） |
| `allowlist.json`、`generated_tools.json`、`agents.json` 三份進版控檔 | 成員管理類工具（`[MB4]`=A 不開放） |
| token 逐請求轉遞、agent 宣告對照與 `on_behalf_of` 注入 | 任何新的簽發機制、委派憑證或服務帳號（`[MB2]`／`[MB3]` 的 B 未採） |
| 錯誤封閉表、bridge 自己的 log | compose／CI／`DEPLOY.md` 的實際編修（交接，§八） |
| 最小測試 client 與驗證拓樸（只在 `backend/tests/`） | 把 bridge 加進 CI test stack（`cicd-pipeline.md:351` 第 26 項） |

## 二、介面

### 2.1 MCP 端點（對 agent 側）

- 傳輸：MCP streamable HTTP，`POST /mcp`（SDK 的標準形狀；需要串流回應時以 SSE 回送），無狀態模式（`BR71.2`）。
- 位址：`http://mcp-bridge:8080/mcp`（compose 服務名，僅 `internal` 網段可達）；本機開發與測試為 `http://127.0.0.1:8080/mcp`。
- 請求標頭（連線層契約，**不是工具參數**）：

| 標頭 | 必填 | 用途 | 規則 |
|---|---|---|---|
| `Authorization: Bearer <使用者 JWT>` | `tools/call` 必填；`initialize`／`tools/list` 不需要 | 原樣轉給 backend | `BR73.1`–`BR73.4` |
| `X-Cloud360-Agent: <agent 名>` | 寫入與清空必填；讀取可省 | 對照 `agents.json` 決定 `on_behalf_of` | `BR74.1`–`BR74.3` |

### 2.2 工具（第一版，`[MB4]`=A）

| 工具 | backend 呼叫 | `inputSchema.properties`（白名單） | 成功回傳 | 需 agent 宣告 |
|---|---|---|---|---|
| `read_requirement_fields` | `GET /api/requirements/systems/{system_id}/fields` | `system_id` | `FieldSetView` | 否 |
| `write_requirement_field` | `PUT …/fields/{agent_group}/{field_key}`，本體 `{value, on_behalf_of}` | `system_id`、`agent_group`、`field`、`value` | `FieldView` | 是 |
| `clear_requirement_field` | `DELETE …/fields/{agent_group}/{field_key}` | `system_id`、`agent_group`、`field` | `FieldView` | 是 |

- 三個 operation 位於 `openapi.json:5329`（GET）與 `:5397`（PUT／DELETE），`operationId` 見 F-4。
- `field` ↔ `field_key` 的改名由 `BR72.5` 規定，`[MB6]`=A 已裁決（§十一）。
- 全部屬性皆為 string；`additionalProperties: false`；`value` 另帶 `minLength: 1`；`agent_group` 與 `field` 另帶 `pattern: ^[a-z0-9_]{1,64}$`（`BR75.4`）。
- 錯誤以 `isError: true` 的工具結果回傳，內容 `{error, message, retryable}`（`BR76.1`–`BR76.3`）。

### 2.3 Liveness

`GET /healthz` → 200 `{"status":"ok"}`，不需認證、不呼叫 backend、不回傳工具資訊（`BR71.3`）。路徑與埠需由 `infrastructure-design`
回寫 `monitoring-design.md:177`（H-2）。

### 2.4 啟動指令

`python -m mcp_bridge --backend-url http://backend:8000 --port 8080 [--host 0.0.0.0]`。**全部以命令列參數**，模組不讀環境變數（`BR71.1`）。

### 2.5 純函式（PBT 與 example-based 的落點）

| 函式 | 模組 | 輸入 → 輸出 | 規則 |
|---|---|---|---|
| `generate_tools(openapi, allowlist)` | `generator.py` | dict × `Allowlist` → `tuple[ToolSpec, ...]`／`GeneratorError` | `BR72.1`–`BR72.8`、`BR72.10`、`BR72.11` |
| `validate_tool_specs(specs, allowlist)` | `generator.py` | 啟動時重驗白名單、底線、`requires_agent` 綁定與路徑前綴 | `BR71.5`、`BR72.10`、`BR72.11` |
| `parse_credential(headers)` | `credentials.py` | 標頭 → `RequestCredential`／`unauthenticated` | `BR73.1` |
| `resolve_agent(declared, registry, requires_agent)` | `agents.py` | → 代寫組／`None`／`agent_not_declared` | `BR74.3` |
| `validate_arguments(spec, args)` | `calls.py` | → 正規化參數／`invalid_argument` | `BR75.4`、`BR74.6` |
| `build_backend_call(spec, args, agent_group)` | `calls.py` | → `BackendCall`（**不含 token**） | `BR74.4`、`BR75.4` |
| `map_outcome(status, body \| transport_error)` | `outcomes.py` | → `ToolOutcome` | `BR76.1`–`BR76.4` |

模組內禁止 import `httpx`（`calls.py` 只產生計畫，送出在執行層）、DB session 型別、`HTTPException`；可執行檢查為 grep 結果為零。

**執行層的組裝點（非純函式，修訂 1 增列，`BR78.3`）**：

| 函式 | 模組 | 輸入 → 輸出 | 規則 |
|---|---|---|---|
| `create_app(*, backend_client, registry, tool_specs, allowed_hosts)` | `app.py` | `httpx.AsyncClient` × `AgentRegistry` × `tuple[ToolSpec, ...]` × `tuple[str, ...]` → ASGI 應用 | `BR78.3`、`BR71.2`、`BR71.3`、`BR71.6`、`BR73.3` |
| `configure_logging()` | `app.py` | 設定 `cloud360.mcp_bridge` 與 `httpx`／`mcp` 的層級 | `BR77.1`、`BR77.2` |

`create_app` 是 bridge ASGI 應用**唯一**的建立方式：正式啟動（`__main__`）與全部測試都經它建立，差別只在傳入的 `backend_client`
（正式為 TCP 連 `--backend-url`；測試為 `httpx.ASGITransport(app=backend 的 FastAPI app)`）與 `registry`。它掛 `/healthz`、`/mcp`、
credential middleware、工具處理函式與 Host 允許清單；**不**讀檔、不解析命令列、不建立 client、不設定 logging。執行層送出請求一律為
`backend_client.build_request(...)` 後 `backend_client.send(...)`，使 PBT 性質六（以 `build_request` 的 URL 為判準）與正式路徑同形。

### 2.6 進版控檔案

| 檔 | 寫者 | 讀者 |
|---|---|---|
| `backend/mcp_bridge/allowlist.json` | 人（PR） | `backend/scripts/gen_mcp_tools.py` |
| `backend/mcp_bridge/generated_tools.json` | `gen_mcp_tools.py` | bridge 啟動、`gen_mcp_tools.py --check` |
| `backend/mcp_bridge/agents.json` | 人（PR） | bridge 啟動、一致性測試（`BR74.2`） |

`generated_tools.json` 內的 `binding` 段含 API 名稱（例如路徑樣板中的 `field_key`）；結構斷言的對象是每一項的
`inputSchema.properties`，**不是**整份檔案的文字。

## 三、工作流程（正式來源）

### MB-W1 啟動

1. 解析命令列參數；呼叫 `configure_logging()`：logger `cloud360.mcp_bridge`，`httpx` 與 `mcp` 的 logger 設為 WARNING（`BR77.2`）。
2. 載入 `generated_tools.json`、`agents.json`；`validate_tool_specs`（含 `BR72.6`、`BR72.7`、`BR72.10`、`BR72.11`）與登錄表檢查。任一失敗 → ERROR 一行（只含工具名或 agent 名）→ `exit(1)`（`BR71.5`）。
3. 建立共用 `httpx.AsyncClient`：`base_url=--backend-url`、`follow_redirects=False`、連線逾時 3 秒、整體 10 秒、無預設 Authorization（`BR73.2`、`BR73.3`）。
4. `create_app(backend_client=…, registry=…, tool_specs=…, allowed_hosts=…)` 建立 ASGI 應用（`BR78.3`）：`/healthz`、`/mcp`（無狀態 streamable HTTP）、credential middleware、Host 允許清單（`BR71.6`，視 SDK 而定）。測試以同一個函式建立，只換 `backend_client` 與 `registry`。
5. uvicorn 監聽 `--host:--port`。**不呼叫 backend**（`BR71.4`）。

### MB-W2 `initialize`／`tools/list`

不檢查 Authorization（`BR73.1`）。`tools/list` 回傳三個工具的 `name`、`description`、`inputSchema`，不含 `binding`。

### MB-W3 `tools/call`（共同骨架）

1. middleware 取 `Authorization`、`X-Cloud360-Agent` 放入 contextvar（`BR73.3`）。
2. 工具名不在載入的清單 → MCP 協定錯誤（未知工具，`BR76.3`）。
3. `parse_credential` → 不過即 `unauthenticated`，**不呼叫 backend**（`BR73.1`）。
4. `resolve_agent` → 寫入與清空未宣告或未登錄即 `agent_not_declared`，不呼叫 backend（`BR74.3`）。
5. `validate_arguments` → 不過即 `invalid_argument`，不呼叫 backend（`BR75.4` 的字元集白名單：`"."`、`".."`、`"/"` 等在此被擋；寫入另含 `BR74.6`）。
6. `build_backend_call` → 執行層以 `backend_client.build_request` 組請求、加上 `Authorization` 原值、`send` 一次（`BR75.1`、`BR73.2`、`BR78.3`）。
7. `map_outcome` → 工具結果（`BR76.1`–`BR76.4`）。
8. log 一行（`BR77.1`）；middleware 的 `finally` 重設 contextvar。

### MB-W4 寫入的差異點

第 6 步的本體為 `{"value": <value>, "on_behalf_of": agents[agent]}`（`BR74.4`）。backend 端 facade 依序判定待核准、`K4.edit`、系統所屬、
per-project 成員（`requirement_field_facade.py:11-28`），再驗代寫組（`:352-356`）。

### MB-W5 清空的差異點

`DELETE`、無本體。持久列只記使用者為清空者；代寫溯源只在 bridge log 的 `agent` 欄（`BR77.4`、`OPEN-MB21-4`）。

### MB-W6 backend 不可用

連線拒絕、逾時、DNS 失敗或 5xx → `backend_unavailable`、`retryable: true`，進程不受影響（`BR71.4`）。bridge 直連 `backend:8000`
不經 nginx，故啟動初期實際觀察到的多為連線拒絕而非 502（`monitoring-design.md:184-188` 要求的「不得死掉」同樣成立）。

## 四、上游交接逐條判定

| # | 上游交接（問題檔第一節與 `U20` 交接） | 本單元的落點 | 判定 |
|---|---|---|---|
| H-1 | 傳輸 HTTP／SSE、第七服務、`internal`、無 `ports:`（`[I6]`=A） | `BR71.1`、`BR71.2`；§八 H-1 | 遵守；streamable HTTP 的選擇理由見 D-8 |
| H-2 | 工具自 `openapi.json` 產生、allowlist、產生器為 PBT 標的、漂移閘門（`[I7]`=A） | `BR72.1`–`BR72.11`；§六 PBT | 遵守；allowlist 初始值收窄為三項（C-4） |
| H-3 | 憑證白名單＋黑名單底線＋排除 `.mcp.json`（`X-04`） | `BR72.6`、`BR72.7`、`BR72.9` | 遵守；`X-04` 內部牴觸以 `BR72.5` 處置，`[MB6]`=A 已裁決（C-2 的 `X-04` 字面仍需追認） |
| H-4 | 每次以使用者身分呼叫既有 API（`FR11.6`） | `BR75.1`、`BR73.2` | 遵守 |
| H-5 | 稽核主體為使用者本人 | `BR77.3` | 遵守（token 轉遞自然達成；bridge 無服務帳號） |
| H-6 | 不需認證的 liveness；啟動初期 backend 502 不得死掉 | `BR71.3`、`BR71.4` | 遵守 |
| H-7 | 代寫一律帶 `on_behalf_of`（`code-summary.md:147-149`） | `BR74.3`、`BR74.4` | 遵守；寫入工具無宣告即拒 |
| H-8 | 清空走 `DELETE`、不以空值 `PUT`（`:150`） | `BR74.6`、`BR77.4` | 遵守；並揭露清空的溯源缺口 |
| H-9 | 不得繞過 facade（`:151`） | `BR75.1`、`BR75.3` | 遵守；bridge 只經 HTTP，結構上無法直讀表 |
| H-10 | 代寫標示可自填，真偽需 `U21` 的身分機制（`:152`，`OPEN-RF20-1`） | `BR74.5` | **未解，合併追蹤**（`[MB3]`=A 的揭露；`OPEN-MB21-2`） |
| H-11 | `K-16` `anti_double_check` 字面與實作相反（`code-summary.md:134-136`） | `BR75.2` | 依 facade 實作為準；`X-04` 的 `authorization_responsibility`（`contract-summary.md:2114-2117`）有同一錯誤字面，一併列入 C-5 |

## 五、已查證事實（逐一開檔核對，2026-10-14）

| # | 事實 | 出處 |
|---|---|---|
| F-1 | 三條路由的 dependency 只有 `get_current_user`；本層不做授權判定 | `backend/services/requirement_field_router.py:21-22`、`:148`、`:171`、`:200` |
| F-2 | `system_id`／`agent_group`／`field_key` 以字串接收，非整數 `system_id` 在授權之後判 404 | `requirement_field_router.py:36-37` |
| F-3 | 4xx 的 `detail` 為 `str(exc)`；`RequirementFieldErrorOut` 描述「`detail` 為固定文字，不含任何輸入值」 | `requirement_field_router.py:138`；`openapi.json:1370` |
| F-4 | 三個 operationId：`read_requirement_fields_…_get`、`write_requirement_field_…_put`、`clear_requirement_field_…_delete` | `openapi.json:5332`、`:5484`、`:5400` |
| F-5 | PUT 本體 schema `additionalProperties: false`，屬性 `on_behalf_of`（`string \| null`）與 `value`（必填） | `openapi.json:5518`、`:5521`、`:5537`–`:5542` 一帶 |
| F-6 | 唯一的 security scheme 為 `HTTPBearer` | `openapi.json:2033-2037` |
| F-7 | facade 授權四步；全域 `K4` 在 facade 內評估、router 不掛 `require_story_action` | `requirement_field_facade.py:11-28`（`:16-22`） |
| F-8 | `on_behalf_of` 必須 ∈ `GROUPS_BY_KEY`；代寫路徑空值 → 驗證錯誤 | `requirement_field_facade.py:352-365`（空值檢查 `:360-365`，`raise` 在 `:365`） |
| F-9 | 代寫組僅 `cost`、`architecture` | `requirement_field_definitions.py:69`、`:81`、`:119` |
| F-10 | facade 的變更 log 記 `user_id` 與 `on_behalf` | `requirement_field_facade.py:444-464` |
| F-11 | `HTTPBearer()` 為 `get_current_user` 的 dependency；token 有效 8 小時；無效 token → 401 | `backend/services/auth.py:33`、`:35`、`:87-91`、`get_user_from_token` 的 401 |
| F-12 | FastAPI 釘在 `0.111.0`；該版 `HTTPBearer` 缺標頭回 **403** "Not authenticated"（本機已安裝套件實讀） | `backend/requirements.txt:8`；`fastapi/security/http.py` 的 `HTTPBearer.__call__` |
| F-13 | backend 映像的 `HEALTHCHECK` 探 `127.0.0.1:8000/` | `backend/Dockerfile:28` |
| F-14 | backend 的 compose build context 為 `../backend` | `deploy/docker-compose.deploy.yml:79-81` |
| F-15 | env 合約以 `rglob` 掃 `backend/` 全部 `.py` 的環境變數讀取 | `scripts/validate_env_contract.py:245` |
| F-16 | 根目錄 `.mcp.json` 列六個框架 server：`context7`、`aws-mcp`、`aws-pricing`、`aws-iac`、`aws-serverless`、`mermaid` | `.mcp.json`（以 `json.load` 列鍵） |
| F-17 | repo 內無任何 `mcp` 依賴 | `backend/requirements.txt`（零命中） |
| F-18 | `K-16` 的 `anti_double_check` 字面；`resolve_project_role` 的 `consumed_by` 含 `U21` | `contract-summary.md:1639-1640`、`:1659` |
| F-19 | `K-17` 的 `clear_field` 參數不含 `on_behalf_of` | `contract-summary.md:1834-1835` |
| F-20 | `X-04` 允許清單含 `field_key`，黑名單底線含 `key` | `contract-summary.md:2067-2068`、`:2081-2082` |
| F-21 | 漂移閘門落點依 runtime 擇 job；CI test stack 不含 bridge；`render-env` 不改為條件式 | `cicd-pipeline.md:337`、`:351`、第 27 項 |
| F-22 | backend 的 CI 漂移檢查 `dump_openapi.py --check` | `.github/workflows/ci.yml:289` |

## 六、ADR-0006 四面向與 PBT

**逐格對照上游 `requirements.md:617-620`（修訂 1 的 FR11／FR12／FR13 表）**：上游四格皆「適用」，本表四格皆「適用」，**無一格相反**。
另對照 `brain-infra` 的 `infrastructure-specification.md` 7.3（僅第七服務），本表為其「細節屬 `U21`」各格的落點。

| 面向 | 判定 | 本單元的處置 |
|---|---|---|
| **IAM** | **適用** | 不新增任何身分、服務帳號或 secret；每次工具呼叫以使用者 token 呼叫既有 API，授權全在 facade（`BR75.1`、`BR75.2`）；bridge 不做第二份授權、不呼叫成員層（`BR75.3`，C-5 移除該邊）。新增的授權面只有 allowlist（預設拒絕、三項，`BR72.2`；路徑前綴白名單使成員管理類結構上無法加入，`BR72.11`）與代寫組登錄表（`BR74.2`）；寫入類工具必須要求 agent 宣告由 `BR72.10` 機械保證。跨請求身分隔離由 `BR73.3` 規定、`BR78.4` 必測。**殘留**：agent 宣告為自報（`BR74.5`、`OPEN-MB21-2`）；agent 可代寫任一已登錄組（`OPEN-MB21-5`）。兩者皆只影響溯源標示、不影響授權 |
| **Encryption** | **適用** | **以詮釋滿足，殘留明文**。上游要求「HTTP／SSE 則須為本機迴環或加密」（`requirements.md:618`）。本設計的 bridge 與 backend 之間、未來的大腦 client 與 bridge 之間，都走 compose `internal` 橋接網段上的**明文 HTTP**；`internal` 網段、無 `ports:` 使流量**不離開本主機**，本站把這**詮釋**為滿足「本機迴環」的意圖——但 docker 橋接網段**不是**迴環介面：使用者 JWT（有效 8 小時，`auth.py:33`）以明文在與 `redis`、`ollama` 共用的網段上往返，同網段上任何被攻破的容器都能被動截取。此詮釋**需使用者確認**，殘留列 `OPEN-MB21-13`，於本站核可關卡呈現。C-T11 的不可逆面：token 不進工具參數、結果、錯誤或 log（`BR72.3`、`BR72.7`、`BR73.4`、`BR77.2`；結果與 log 兩面由 `BR78.5` 必測），且啟動時自我驗證（`BR71.5`）。at rest：不落地任何 token 或工具結果 |
| **Network exposure** | **適用** | 對外暴露面零新增（`BR71.2`）；`internal` 新成員使 D-3 blast radius 由 3 增為 4（`infrastructure-specification.md` 7.4，§八 H-11 的前向指標）。`/healthz` 免認證但不回傳任何資訊；`tools/list` 免認證但只回公開工具宣告（D-13）。不跟隨重導（`BR73.2`）、路徑段字元集白名單防路徑注入（`BR75.4`；百分比編碼只作縱深防禦）、Host 允許清單（`BR71.6`）。殘留：無頻率與並發上限（`OPEN-MB21-10`） |
| **Audit logging** | **適用** | 寫入與清空的稽核主體為使用者本人（`BR77.3`，`requirements.md:620`）；寫入另由 `updated_on_behalf_of` 留代寫組。bridge 的工具呼叫層稽核為一行 INFO、欄位白名單（`BR77.1`），禁含 token、參數、本體（`BR77.2`）。**殘留三項**：(1) **成功的讀取沒有任何帶使用者身分的紀錄**——facade 只記被拒的讀取（`requirement_field_facade.py:272-276`），成功的 `read_fields`（`:301-305`）不記，bridge 不解碼 JWT（`BR73.5`），故「agent 經 MCP 讀了誰可見的哪個系統」事後無主體可查；`requirements.md:620` 的「稽核主體為使用者本人」在讀取面**不成立**，列 `OPEN-MB21-14`，於本站核可關卡呈現；(2) 清空無持久溯源（`BR77.4`、`OPEN-MB21-4`）；(3) bridge log 與 backend log 無關聯鍵（`OPEN-MB21-9`） |

**PBT 判定**：`brain-infra` 的 `S-15` 已把**產生器**判為本單元的 PBT 適用標的（`infrastructure-specification.md` 7.3：「有輸入空間的轉換函式」），
本站沿用並視為**必須**；`unit-of-work.md:507` 對「工具 schema 白名單」的「不適用，但可機械斷言」判定**不推翻**（受測對象不同），回補該表屬
`OPEN-MB21-11`。

**策略（修訂 1，審查 `R-04`）**：hypothesis 策略**先產生一份一致的 (openapi, allowlist) 配對，再依抽到的類別施加一種且僅一種破壞**——
allowlist 一律由抽到的 openapi **衍生**（從 operations 中抽子集、properties 取該 operation 的 path／query 參數與本體頂層屬性在 strip
與 rename 之後的集合、`requires_agent` 依 `BR72.10` 設定、path 落在 `/api/requirements/` 之下），不得獨立產生兩者。否則絕大多數
抽樣會落在 `missing_operation` 或 `whitelist_mismatch`，成功分支近乎空集合，性質一與五形同恆真。類別以 `st.sampled_from` 抽出：

| 類別 | 施加的破壞 | 唯一期望結果 |
|---|---|---|
| `consistent` | 無（所有名稱取自不含 `token`／`key`／`secret`／`authorization` 子字串的乾淨字母表） | 成功 |
| `renamed_clean` | 某屬性的 API 名命中黑名單（如 `api_key`），allowlist 以 rename 改成乾淨名並列入白名單 | 成功（證明檢查在改名**之後**） |
| `credential_injected` | 在 openapi 某 operation 加一個命中黑名單的屬性（含 `token`／`Key`／`client_secret`／`Authorization` 等大小寫變體，頂層或巢狀於本體 object 內），**同時**把它寫進該項白名單（巢狀時寫其頂層名）；子變體：只加進 openapi、不寫進白名單 | `credential_like_property`（兩個子變體皆然：`BR72.1` 的順序使底線先於白名單） |
| `renamed_dirty` | 乾淨的 API 名經 rename 改成命中黑名單的工具名，並列入白名單 | `credential_like_property` |
| `whitelist_drift` | 白名單多一個或少一個名稱（名稱取自乾淨字母表） | `whitelist_mismatch` |
| `missing_op` | allowlist 加一項指向 openapi 不存在的 (method, path)（path 仍在前綴內） | `missing_operation` |
| `out_of_scope` | allowlist 加一項 path 在 `/api/requirements/` 之外（含 `/api/membership/` 形狀）的 operation，且 openapi 確有該 operation | `path_outside_scope` |
| `agent_mismatch` | 某非 GET 或有 inject 的項目 `requires_agent` 設為 false | `agent_requirement_mismatch` |

每個類別以 `hypothesis.event(類別)` 標記；成功分支另以 `hypothesis.target(1.0 if 成功 else 0.0)` 引導。**下限以計數器強制**（`event`
的統計只在 pytest 的 `--hypothesis-show-statistics` 顯示，本 repo 用 `unittest`，故不以它為閘門）：測試類別以類別屬性累計每類別的
執行次數，`tearDownClass` 斷言 `@settings(max_examples=300)` 下 `consistent` 與 `renamed_clean` 合計成功次數 ≥ 60（20%）、其餘每一類
各 ≥ 15。下限不過即紅燈——它擋的是「策略被改壞、成功分支消失而性質恆真」。

**性質（每一條在其類別內斷言單一結果，不接受「任一碼皆可」）**：

| # | 性質 | 類別 | 函式 |
|---|---|---|---|
| 一 | `consistent`／`renamed_clean`：成功，且所有工具 `inputSchema` 中**任何深度**的屬性名都不命中黑名單；`credential_injected`／`renamed_dirty`：**恰為** `GeneratorError("credential_like_property")` | 四類 | `generate_tools` |
| 二 | 成功時工具對應的 (method, path) ⊆ allowlist；`missing_op`：**恰為** `missing_operation`；`out_of_scope`：**恰為** `path_outside_scope`（成員管理類的結構性排除，`BR72.11`） | 三類 | `generate_tools` |
| 三 | 成功時 `strip_body_fields` 與 `inject` 的鍵、security scheme 名稱、header／cookie 參數名，永不出現在任何 `inputSchema.properties` | `consistent` | `generate_tools` |
| 四 | 決定性：同一輸入兩次結果相等；打亂 `paths` 與 `properties` 的鍵順序結果不變（含失敗時的錯誤碼與 tool_name） | 全部 | `generate_tools` |
| 五 | 成功時每個工具的屬性鍵集合 = allowlist 宣告集合（改名後）；`whitelist_drift`：**恰為** `whitelist_mismatch` | 兩類 | `generate_tools` |
| 六 | 對任意字串參數（策略含 `"."`、`".."`、`"/"`、`"%2e%2e"`、`"?"`、`"#"`、空白、非 ASCII）：`validate_arguments` 拒絕（`invalid_argument`），**或**以 `httpx.AsyncClient(base_url="http://backend:8000").build_request(call.method, call.path)` 實際組出的請求 URL 滿足——`url.raw_path` 以 `/` 切出的段數等於樣板段數、前綴等於 allowlist 的路徑前綴、不含 `.` 或 `..` 段、各段解碼後等於對應參數值。判準是 httpx 實際組出的 URL，**不是** `build_backend_call` 的計畫字串（審查實測 httpx 0.28.1 會正規化 dot-segment） | — | `validate_arguments` ＋ `build_backend_call` |
| 七 | `agent_mismatch`：**恰為** `agent_requirement_mismatch`；成功時每個 `method != GET` 或有 inject 的工具 `requires_agent` 為 true（`BR72.10`） | 兩類 | `generate_tools` |
| （example） | 封閉表每一列；`detail` 過濾的通過與退回（多鍵、非字串、超長、控制字元）；標頭格式的邊界；登錄表 ⊆ `GROUPS_BY_KEY`；bridge 的鍵樣式 = `KEY_PATTERN.pattern`；**`BR75.4` 必測輸入**：`agent_group` 與 `field` 各為 `"."`、`".."`、`"a/b"`、`"%2e%2e"` → `invalid_argument` 且 backend 未收到任何請求；`validate_tool_specs` 對手改的產物（拿掉 `requires_agent`、加入 `/api/membership/` 項）→ 啟動 `exit(1)` | — | `map_outcome`、`parse_credential`、`resolve_agent`、`validate_arguments`、`validate_tool_specs` |

**突變驗證（必做，寫入 `code-generation` 的 `automation-test-plan`）**：

| 突變 | 預期紅燈的性質（類別） |
|---|---|
| 拿掉 `BR72.7` 的黑名單檢查 | 性質一（`credential_injected`、`renamed_dirty`：得到成功而非 `credential_like_property`） |
| 拿掉 `BR72.6` 的白名單相等檢查 | 性質五（`whitelist_drift`：得到成功） |
| 把 `BR72.7` 移到 rename **之前** | 性質一（`renamed_clean` 得到 `credential_like_property` 而非成功；`renamed_dirty` 得到成功）；另 example：以 repo 的 `openapi.json` ＋ `allowlist.json` 產生失敗（`field_key` 命中 `key`） |
| 把 `BR72.6` 移到 `BR72.7` **之前** | 性質一（`credential_injected` 中白名單未同步的變體得到 `whitelist_mismatch`）——策略須含「只寫進 openapi、未寫進白名單」的子變體，期望仍為 `credential_like_property` |
| 拿掉 `BR72.10` | 性質七（`agent_mismatch` 得到成功） |
| 拿掉 `BR72.11` | 性質二（`out_of_scope` 得到成功） |
| `BR75.4` 退回只用 `quote` 編碼、不驗字元集 | 性質六（`".."` 使段數少一）與 example 必測輸入 |

**AC11.4.2 的白名單期望值獨立於產生器輸入**：AC11.4.2 的結構斷言以**寫在測試檔內的字面值**為期望集合——
`{"read_requirement_fields": {"system_id"}, "write_requirement_field": {"system_id", "agent_group", "field", "value"},
"clear_requirement_field": {"system_id", "agent_group", "field"}}`——**不讀 `allowlist.json`**。`allowlist.json` 是產生器的輸入，
同一個 PR 可同時改它與產物；以它為期望值等於自證。擴充工具時測試檔的字面值必須同 PR 修改，使白名單變動在 diff 上顯式可見。

`project.md` 的 hard constraint 落點（IaC generator、cost calculator、agent routing）不含本單元，但產生器的形狀與「IaC generator」同類
（宣告式輸入 → 產物），加上 `S-15` 的判定，故不以 N/A 處理。

## 七、偏離、決定與開放項

### 7.1 本站做的決定（MB1–MB6 作答之外者揭露供核可；D-2 已由 `[MB6]`=A 裁決）

| # | 決定 | 理由 |
|---|---|---|
| D-1 | agent 身分以請求標頭 `X-Cloud360-Agent` 宣告，不用 `clientInfo`（`BR74.1`） | 無狀態傳輸下沒有可綁定 `clientInfo` 的 session；與 token 同層同生命週期；`clientInfo` 描述的是 client 實作 |
| D-2 | 工具屬性 `field_key` 改名為 `field`（`BR72.5`） | `X-04` 的白名單（含 `field_key`）與底線（含 `key`）在子字串讀法下互相牴觸；採較嚴讀法並以改名消解。**已裁決**：`[MB6]`=A（問題檔 `[Answer]: A`，2026-10-13T23:08:40Z）；`X-04` 字面仍需追認（C-2） |
| D-3 | 工具名、描述、屬性描述取自 allowlist（`BR72.8`） | openapi 的 PUT 描述提及 `on_behalf_of`（`openapi.json:5483`），沿用會誤導 agent |
| D-4 | bridge 端參數驗證；`agent_group`／`field` 以字元集白名單 `^[a-z0-9_]{1,64}$` 驗證，百分比編碼只作縱深防禦（`BR75.4`） | 不依賴 client 遵守 schema；百分比編碼擋不住 `..`（`quote` 不編碼句點、httpx 正規化 dot-segment，審查 `R-01` 實測），只有白名單能保證段不改變目標路徑 |
| D-5 | 工具層錯誤用 `isError` 結果，不用 JSON-RPC 錯誤（`BR76.3`） | agent 才讀得到並決策 |
| D-6 | Host 允許清單（`BR71.6`） | DNS rebinding 防護不以關閉代替 |
| D-7 | log 的 agent 欄正規化為已登錄名／`undeclared`／`unregistered`（`BR77.1`） | 防 log 注入 |
| D-8 | streamable HTTP、無狀態（`BR71.2`） | 舊 HTTP＋SSE 需長駐連線與 session 對應，與逐請求身分相反；streamable HTTP 仍以 SSE 串流，符合 `[I6]`=A |
| D-9 | `/mcp`、`/healthz`、埠 8080 | `monitoring-design.md:177` 刻意留給本單元決定 |
| D-10 | 零環境變數、設定全走命令列參數（`BR71.1`） | 使 `[I6]` 的「零新部署變數」在程式層成立，避開 `validate_env_contract.py:245` 的掃描與三處同步義務 |
| D-11 | 讀取不要求 agent 宣告（`BR74.3`） | 讀取無代寫標示可填；宣告不是授權 |
| D-12 | 不重試；逾時 3 秒／10 秒（`BR75.1`、`BR76.1`） | 重試會在 backend log 留多筆；重試決策交給 agent（`retryable`） |
| D-13 | `initialize`／`tools/list` 不需 Authorization（`BR73.1`） | 只回公開工具宣告；把認證錯誤留在工具層才能以 MCP 語意回報；不實作 MCP 的 OAuth 授權流程（HTTP 401 會觸發 client 的授權探索） |
| D-14 | 403／404／422 的 `detail` 過濾後原樣轉送（`BR76.2`） | `AC11.4.1`「理由與我直接存取時相同」 |
| D-15 | 本地擋缺漏 Authorization（`BR73.1`） | FastAPI 0.111.0 對缺漏標頭回 403（F-12），轉送會被誤判為 forbidden |
| D-16 | 字元集白名單而非 `enum`（`BR75.4`） | `enum` 會把七個欄位鍵寫進工具 schema，成為鍵集合在 backend 之外的另一份物化，且每次 `U20` 新增欄位都要重產與追認；白名單與 `KEY_PATTERN` 逐字相同，以一致性測試鎖住，已足以排除 dot-segment |
| D-17 | `generate_tools` 的檢查順序固定，黑名單底線先於白名單（`BR72.1`） | 使每類違反恰得一個錯誤碼，PBT 可逐類斷言、突變驗證不會被另一道檢查的碼掩蓋（審查 `R-04`） |
| D-18 | `requires_agent` 與 method／inject 綁定為不變量；路徑前綴白名單為程式常數（`BR72.10`、`BR72.11`） | 把「人記得填對」與「成員管理類不開放」從敘述變成產生與啟動都會擋的機制；擴充前綴須改程式、經程式碼審查（審查 `R-05`） |
| D-19 | 唯一組裝點 `create_app`（`BR78.3`） | 正式啟動與測試走同一條組裝路徑，只換 `backend_client` 與 `registry`（審查 `R-10`） |

### 7.2 開放項

| # | 事項 | 承接 |
|---|---|---|
| `OPEN-MB21-1` | **大腦側 MCP client 不存在**（`[MB1]`=A）：能力 11 的「agent 取用需求欄位」本版無實際使用者；`[F16]`=B 寫的「在大腦側加 MCP client」無單元承接（`U13` 的 `NFR13.16` 禁止呼叫需求欄位 facade；`U11`／`U12` 對 MCP 命中為 0）。`AC11.4.1`／`AC11.4.3` 以測試 client 驗證（§traceability） | **本 intent 內無自然承接站**——交回範圍定義（後續 intent 的 `scope-definition`）；本站核可關卡的 conductor 須向使用者揭露 |
| `OPEN-MB21-2` | agent 宣告為 client 自報、真偽無法驗證（`BR74.5`）；與 `U20` 的 `OPEN-RF20-1` 同一缺口，合併追蹤 | 新 ADR（每個 agent 可驗證憑證，`[MB3]` 選項 B）——有 client 簽章機制時收緊 |
| `OPEN-MB21-3` | **已關閉**（修訂 1）：`field_key` 改名（`BR72.5`）已由 `[MB6]`=A 裁決（問題檔 `[Answer]: A`，2026-10-13T23:08:40Z）；剩下的 `X-04` 字面修改併入 `OPEN-MB21-6` 的 C-2 | — |
| `OPEN-MB21-4` | agent 清空欄位無持久溯源：`K-17` 的 `clear_field` 不收 `on_behalf_of`（F-19） | `K-17` 增量（`clear_field` 增 `on_behalf_of`，`U20` 修訂）；本版揭露 |
| `OPEN-MB21-5` | agent 可代寫任一已登錄組（例如 `cost` agent 寫 `architecture` 組的欄位）：上游無「agent 只寫自己的組」的規則，本站不自創 | 使用者／產品決定（非阻擋） |
| `OPEN-MB21-6` | **契約追認 C-1～C-5**（§九） | `U21` 的 `code-generation`（3.5，**ALWAYS**，位於游標之後）的 conductor 於提交計畫核可**之前**呈使用者追認；C-2 內容已由 `[MB6]`=A 定案，追認的是 `X-04` 字面，追認時點與其餘四項相同 |
| `OPEN-MB21-7` | **`A-7` 實測**：`mcp` SDK 精確版本、與 `fastapi==0.111.0` 的 Starlette 版本範圍相容、無狀態 streamable HTTP、工具處理函式取得請求標頭的方式（本設計以 middleware ＋ contextvar 自行取得，不依賴 SDK 的請求上下文 API）、Host 檢查設定；工具處理函式是否在另一個 task 內執行而仍取得本請求的 contextvar——由 `BR78.4` 的並發交錯測試**偵測**，不再只是未實測項。判定與退路順序見 §十二 第 1 步 | `U21` 的 `code-generation`（ALWAYS），**第一個步驟** |
| `OPEN-MB21-8` | 部署與 CI 交接 H-1～H-11（§八） | `U21` 的 `infrastructure-design`（3.4，CONDITIONAL）；若被 skip 轉 `code-generation`（ALWAYS），判定 skip 者須重新提交使用者 |
| `OPEN-MB21-9` | bridge log 與 backend log 無關聯鍵（只能依時間對照）；加一個請求 id 需 backend 也記錄它 | `U21` 的 `nfr-design`（CONDITIONAL）→ 轉 `code-generation` |
| `OPEN-MB21-10` | bridge 無請求頻率、並發與本體大小上限 | `U21` 的 `nfr-requirements`（CONDITIONAL）→ 轉 `code-generation` |
| `OPEN-MB21-11` | `unit-of-work.md:507` 的 PBT 逐項判定表需回補「產生器」為第二個 PBT 標的（`S-15`）；本站不回改上游 | 下一次 `units-generation` 修訂（非阻擋） |
| `OPEN-MB21-12` | `D-3` blast radius 重算（`infrastructure-specification.md` 7.4 的前向指標） | `U21` 的 `infrastructure-design` → 轉 `code-generation` |
| `OPEN-MB21-13` | **Encryption 以詮釋滿足、殘留明文 JWT**（審查 `R-08`）：`requirements.md:618` 要求 HTTP／SSE「須為本機迴環或加密」，本設計把「`internal` 橋接網段、無 `ports:`、不離開本主機」詮釋為滿足；但橋接網段不是迴環，使用者 JWT（8 小時有效）以明文在與 `redis`、`ollama` 共用的網段上往返。收斂手段（bridge 與 client 改走 TLS，或 bridge 與 backend 同網路命名空間經 `127.0.0.1`）皆越出本單元 | **使用者於本站核可關卡確認此詮釋**（接受殘留，或指派收斂手段給 `infrastructure-design` → 轉 `code-generation`） |
| `OPEN-MB21-14` | **成功的讀取無帶使用者身分的稽核紀錄**（審查 `R-08`，`BR77.3`）：facade 只記被拒的讀取，bridge 不解碼 JWT；`requirements.md:620` 的「稽核主體為使用者本人」在讀取面不成立 | **使用者於本站核可關卡裁決**是否接受；若不接受，補法為 `U20` 的 `read_fields` 增一行帶 `user_id` 的 INFO（`U20` 修訂），不由本單元自行補 |
| `OPEN-MB21-15` | **`mcp` 依賴與 backend 的 FastAPI 釘選耦合**（審查 `R-09`）：`[MB5]`=A 使 bridge 與 backend 共用一份 `requirements.txt` 與 site-packages；`mcp` 的 Starlette 範圍若與 `fastapi==0.111.0` 衝突，第一直覺「升 FastAPI」會連動 `openapi.json` 重 dump 與前端型別重產（`backend/requirements.txt` 檔頭的釘選紀律），代價與一個尚無 client 的 bridge 不成比例；且第一順位下 `mcp` 會進入 backend 執行期映像（backend 進程不 import 它，但多一份供應鏈面）。問題檔 `MB5` 的代價說明只寫「新增一個 Python 依賴」，未揭露此耦合 | 退路順序寫進 §十二 第 1 步（`code-generation` 第一個動作）；**本站核可關卡揭露此代價** |

## 八、部署與 CI 交接（給 `nfr-requirements`／`nfr-design`／`infrastructure-design`）

| # | 項目 | 內容 | 依據 |
|---|---|---|---|
| H-1 | compose 服務 `mcp-bridge` | `build: {context: ../backend}`（同 backend）、`command: ["python","-m","mcp_bridge","--backend-url","http://backend:8000","--port","8080"]`、`networks: [internal]`、**無 `ports:`**、`restart: unless-stopped`、`logging: *json_file_bounded`、記憶體上限（暫定值＋`DEPLOY.md` 標記未量測）、`depends_on: [backend]`（無 `condition`，`BR71.4` 已承受） | `cicd-pipeline.md` 第 25 項；`BR71.1`–`BR71.4` |
| H-2 | healthcheck | `python -c` 以 `urllib` 探 `http://127.0.0.1:8080/healthz`；回寫 `monitoring-design.md:177` 的路徑欄 | `BR71.3` |
| H-3 | 覆寫映像 HEALTHCHECK | 沿用 backend 映像時其 `HEALTHCHECK`（`Dockerfile:28`）探 8000，**compose 必須以 H-2 覆寫**，否則容器恆為 unhealthy | F-13 |
| H-4 | 漂移閘門 | `python scripts/gen_mcp_tools.py --check` 加在 `backend` job，緊鄰 `ci.yml:289`；回寫 `cicd-pipeline.md` 第 22 項的「擇一」為 backend | `BR72.9` |
| H-5 | 依賴 | 依 §十二 第 1 步的判定擇一：**第一順位**——`backend/requirements.txt` 新增 `mcp==<精確版本>`（比照 `fastapi`／`pydantic` 的 `==`），條件是該版本的 Starlette 範圍涵蓋 `fastapi==0.111.0` 所解析的 Starlette；代價：`mcp` 進入 backend 執行期映像（backend 進程不 import 它）。**第二順位**——同一映像內獨立的 `backend/requirements-mcp.txt`，於 Dockerfile 建置階段裝進獨立的 virtualenv（例如 `/opt/mcp-venv`），compose 的 `command` 改用該 venv 的 `python`；**不碰 FastAPI 釘選**；代價：Dockerfile 改動、映像變大、`BR78.2` 的同直譯器拓樸改為子進程拓樸。**最後手段**——升 FastAPI（連動 `openapi.json` 重 dump 與前端型別重產，`backend/requirements.txt:1-7`），須另開題請使用者裁決。耦合代價見 `OPEN-MB21-15` | `[MB5]`=A；審查 `R-09` |
| H-6 | env 合約 | **不觸發**：零環境變數（`BR71.1`），`render-env.sh`、`deploy/.env.example`、`backend/.env.example` 皆不改；`cicd-pipeline.md` 第 27 項的條件不成立。若實作發現需要任何環境變數，`project.md` 的三處同步規則與 `LOCAL-DEV.md` 同步規則**完整適用** | F-15 |
| H-7 | `DEPLOY.md` | 第七服務說明、記憶體暫定值、「沒有對外端口」的驗證指令 | `cicd-pipeline.md` 第 28 項 |
| H-8 | `deploy.yml` | env 對照表不改；部署後若有硬編服務數的檢查須同步 | `cicd-pipeline.md` 第 29 項 |
| H-9 | CI test stack | 不加入；本單元驗證以 `BR78.2` 的拓樸在 `unittest` 內完成。回寫 `cicd-pipeline.md` 第 26 項 | `BR78.2` |
| H-10 | `LOCAL-DEV.md` | 規則不觸發（無 `.env.example` 變動）；建議（非 blocking）補一節「本機啟動 bridge：`python -m mcp_bridge --backend-url http://127.0.0.1:8000`」 | `project.md ## Mandated` |
| H-11 | `D-3` blast radius | `internal` 成員 4 → 5；`redis`／`ollama` 的可達來源 3 → 4 | `infrastructure-specification.md` 7.4 |
| H-12 | schema 同步規則 | **不觸發**：本單元無 DDL、無 seed 變更 | `project.md ## Mandated` |

## 九、契約增量（追認內容草案，`OPEN-MB21-6`）

| # | 契約 | 增量 | 來源 |
|---|---|---|---|
| C-1 | `X-04` `tools` | 新增 `clear_requirement_field`，`inputSchema_properties_allowed: [system_id, agent_group, field]`，回傳 `FieldView`，經 `K-17` 的 `clear_field` | `[MB4]`=A；`K-17` 已把 `U21` 列為 `clear_field` 呼叫端（`contract-summary.md:1839-1841`） |
| C-2 | `X-04` `tools.write_requirement_field` | `field_key` → `field`（並套用於 C-1）——**已定**：`[MB6]`=A；追認的是 `X-04` 字面，時點同其餘四項（`OPEN-MB21-6`） | `BR72.5`、`[MB6]`=A |
| C-3 | `X-04` 未定項 | `how_token_reaches_this_process` 定案為「每次 MCP 請求的 `Authorization: Bearer` 原樣轉遞、用完即棄」（`OQ-15`）；`transport` 定案為 streamable HTTP（`OQ-16`，`[I6]`=A）；連線層新增 `X-Cloud360-Agent` 標頭；`authorization_responsibility` 的「全域層由被呼叫的既有 API 的 `require_story_action` 承擔」改為「全域層由 `K-17` facade 承擔」 | `[MB2]`=A、`[MB3]`=A；F-7 |
| C-4 | `[I7]`／`cicd-pipeline.md` 第 24 項 | allowlist 初始值由「`U19` ＋ `U20` 兩塊」收窄為 `U20` 的三個 operation | `[MB4]`=A（**對已核可範圍的收窄**，非擴充） |
| C-5 | `K-16` | `resolve_project_role` 的 `consumed_by` 移除 `U21`（`contract-summary.md:1659`）；`anti_double_check` 字面改為與實作一致（與 `U20` 的 `OPEN-RF20-5` 同批）；同時從 `consumers.separate_process`（`:1622`）與 K-16 標題的消費者清單（`:1611`）移除 `U21`。**`components.md`：移除 `McpBridge → ProjectMembership` 這條邊，不是加註保留**——刪 `McpBridge.depends_on` 的 `ProjectMembership` 項（`:664-666`）、`ProjectMembership.dependents` 的 `McpBridge` 項（`:567-568`）、Part B' 圖的對應箭頭（`:788`）、無環驗證的邊清單（`:775`，邊數 17 → 16）與兩張摘要表（`:809`、`:811`）。理由：per-project 判定是 `RequirementRegistry` 內部對 `ProjectMembership` 的依賴，對 bridge 只是傳遞依賴；保留該邊會讓下游讀 `depends_on` 時認定 bridge 直接依賴成員層（審查 `R-07`）。剩下的 `McpBridge → RequirementRegistry` 之 `style: sync` 註明為「經 HTTP 的同步請求」 | `BR75.2`、`BR75.3` |

## 十、Assumptions

- **A-1** 官方 Python `mcp` SDK 提供無狀態 streamable HTTP 伺服器並可掛為 ASGI 應用（`A-7` 未實測，`OPEN-MB21-7`）。不成立時退回：同 SDK 的低階 server ＋ 自建 ASGI 包裝，規則不變。
- **A-2** `mcp` SDK 的 Starlette 版本範圍與 `fastapi==0.111.0` 相容（同一映像共用一份 site-packages）。**判定與退路順序是 `code-generation` 的第一個步驟**（§十二 第 1 步）：不成立時先找相容的較舊 `mcp` 版本；仍不成立走第二退路（同一映像內獨立的 requirements 檔裝進獨立 virtualenv，不碰 FastAPI 釘選）；升 FastAPI（連動 OpenAPI 重 dump 與前端型別重產，`backend/requirements.txt:1-7` 的釘選紀律）只作最後手段且須另開題。耦合代價見 `OPEN-MB21-15`。
- **A-3** 單一使用者 token 在一次工具呼叫期間有效；token 在呼叫中途過期時 backend 回 401 → `unauthenticated`，不重試。
- **A-4** 大腦側 client 未來會與 bridge 同主機、經 `internal` 連線並自行持有使用者 token 與 agent 名；這是 `OPEN-MB21-1` 的前提，本版不驗證。

## 十一、`MB6` 裁決紀錄（設計中途追加題，已作答）

**題目**：`X-04` 的寫入工具允許清單逐字含 `field_key`（`contract-summary.md:2081-2082`），而黑名單底線與 `AC11.4.2` 逐字要求屬性名「不含任何名稱匹配
`token`／`key`／`secret`／`authorization`（不分大小寫）」（`stories.md:728`）。以子字串比對時 `field_key` 命中 `key`，兩條已核可的約束不能同時成立。

**裁決**：`[MB6]`=A——工具屬性改名為 `field`，黑名單底線維持不分大小寫的子字串比對。出處：`functional-design-questions.md` 的 `MB6`，
`[Answer]: A`（2026-10-13T23:08:40Z，使用者經選單作答，選項順序與問題檔一致）。未採的 B（切段比對＋`field_key` 單一豁免）與 C（完整名稱相等）
保留於問題檔原文。

**落點**：`BR72.5`（規則本身，不再是設計預設）、`BR72.6`（白名單宣告用 `field`）、`BR75.4`（反向映射回 `field_key`）、`entities.md`
`AllowlistEntry.rename`、§2.2、D-2、C-2（`X-04` 字面仍需追認，時點同其餘契約增量）、`traceability.json` 的 `AC11.4.2`。`OPEN-MB21-3` 隨之關閉。

## 十二、交給 `code-generation` 的第一步與必測清單（修訂 1）

`code-generation`（3.5，**ALWAYS**）是本單元下一個必經站；以下兩項是本站對它的硬性交接，conductor 須寫進其計畫並在計畫核可時呈現。

**第 1 步（任何程式之前）——`A-2`／`A-7` 判定與依賴路線**（`OPEN-MB21-7`、`OPEN-MB21-15`，審查 `R-09`）：

1. 選定 `mcp` 的精確版本，讀其套件中繼資料的 Starlette／anyio 版本範圍，與 `fastapi==0.111.0` 解析出的版本比對；並確認該版本提供無狀態 streamable HTTP 與 Host 檢查設定（`BR71.2`、`BR71.6`）。
2. 相容 → **第一順位**：`backend/requirements.txt` 加 `mcp==<版本>`（H-5）。
3. 不相容 → 先找相容的較舊 `mcp` 版本（仍須滿足 1 的功能條件）。
4. 仍不相容 → **第二退路**：`backend/requirements-mcp.txt` ＋ Dockerfile 建置階段裝進獨立 virtualenv，bridge 以該 venv 執行；**不碰 FastAPI 釘選**；`BR78.2` 改用子進程拓樸並在計畫中記錄。
5. 只有第二退路也不可行時，才把「升 FastAPI」（連動 `openapi.json` 重 dump 與前端型別重產）另開題交使用者裁決；不得自行升版。
6. 判定結果與所選路線寫進 `code-generation` 的計畫，作為 H-5 的落點。

**必測清單（未完成不得標示 `code-generation` 完成）**：

| # | 測試 | 規則 | 驗的失敗模式 | 必做突變 |
|---|---|---|---|---|
| T-1 | 並發身分隔離：≥ 2 個 client、不同使用者 token、交錯 ≥ 20 次讀（另一組交錯寫），backend 端每個請求的 `Authorization` = 發起者的 token；寫入的 `updated_by` 為各自的使用者 | `BR78.4`（驗 `BR73.3`） | 下一位使用者以前一位的身分執行 | token 改存模組變數 → 紅 |
| T-2 | 逐分支不外洩：`BR76.1` 每一列（含本地與 backend 兩種來源）與成功的讀寫，工具結果全文與全部 logger 輸出不含完整 token、簽章段、`"Bearer "`＋token | `BR78.5`（驗 `BR73.4`、`BR77.2`） | token 經錯誤訊息、例外文字或 log 外流 | `message` 改用 `str(exc)` → 紅；log 加參數或標頭 → 紅 |
| T-3 | 產生器 PBT：§六 的八個類別、七條性質、成功分支計數下限 | `BR72.1`–`BR72.11` | 黑名單或白名單違反在 PBT 中被恆真性質放過 | §六 突變表全部七列 |
| T-4 | 路徑段必測輸入：`agent_group`／`field` 為 `"."`、`".."`、`"a/b"`、`"%2e%2e"` → `invalid_argument` 且 backend 未收到請求 | `BR75.4` | dot-segment 正規化把請求送往 allowlist 以外 | 退回只用 `quote` → 紅 |
| T-5 | `AC11.4.2` 結構斷言：期望白名單為測試檔內字面值，不讀 `allowlist.json` | `BR72.6`、`BR72.7` | 同一個 PR 同改 allowlist 與產物而自證 | 在 `allowlist.json` 與產物同時加一個屬性 → 紅 |
| T-6 | 讀取輸入封閉：攔截 `gen_mcp_tools.py` 兩種模式開啟的路徑 | `BR72.9` | 腳本讀到 `.mcp.json` 或其他設定 | 腳本多讀 `.mcp.json` → 紅 |
| T-7 | 鍵樣式一致：bridge 樣式 = `KEY_PATTERN.pattern` = allowlist 的 `property_patterns`；`agents.json` 值 ⊆ `GROUPS_BY_KEY` | `BR75.4`、`BR74.2` | 跨進程副本漂移 | 改任一副本 → 紅 |
| T-8 | 啟動自我驗證：手改產物（拿掉寫入工具的 `requires_agent`、加入 `/api/membership/` 項、加入 `api_key` 屬性）→ `exit(1)` | `BR71.5`、`BR72.10`、`BR72.11` | 繞過產生器的手改產物帶病上線 | 拿掉 `validate_tool_specs` 中任一檢查 → 對應案例紅 |

## 十三、送審前自檢（七項）

### 13.1 初版自檢（iteration 1 送審前；表內數字與敘述皆為當時值，現值以 13.2 為準）

| # | 項目 | 結果 |
|---|---|---|
| 1 | **可達性** | 每條「偵測 X」的規則皆可構造：缺 Authorization／格式錯（測試 client 不帶或帶壞標頭）；backend 401（過期 token）；403（非成員、待核准、缺 `K4`）；404（不存在的 `system_id`）；422（未知 `agent_group`、超長 `value`）；`backend_unavailable`（bridge 指向未啟動的埠）；`agent_not_declared`（缺標頭、未登錄名）；`invalid_argument`（多一個參數、`system_id="1/../2"`、純空白 `value`）；`internal_error`（替身回 418 或非 JSON 的 200）；`BR71.5`（以含 `api_key` 屬性的產物啟動）；`BR72.2` 的 `missing_operation`（allowlist 指向不存在的路徑）。`BR73.1` 的 403 誤判情境以 F-12 實讀確認可達 |
| 2 | **契約端點三問** | 欄位：`on_behalf_of` 寫＝bridge（`BR74.4`）、讀＝facade 與 `FieldView.updated_on_behalf_of`、清＝不適用（`clear_field` 不寫它，即 `OPEN-MB21-4` 的缺口）；`RequestCredential` 寫＝middleware、讀＝工具處理、清＝middleware 的 `finally`；`allowlist.json`／`agents.json` 寫＝人、讀＝產生腳本與啟動、清＝人；`generated_tools.json` 寫＝產生腳本、讀＝啟動與 `--check`、清＝重產覆寫。方法：`generate_tools` 擁有＝本單元、呼叫＝產生腳本與 `validate_tool_specs`；`parse_credential`／`resolve_agent`／`validate_arguments`／`build_backend_call`／`map_outcome` 擁有＝本單元、呼叫＝MB-W3；`clear_field`（`K-17`）呼叫＝本單元經 HTTP——**`K-17` 的「呼叫端只有 `U13`／`U21`」中 `U13` 已由 `U13` 的設計判為不呼叫，故本單元是 `clear_field` 目前唯一的非 UI 呼叫端**；`resolve_project_role`（`K-16`）列本單元為消費者但本設計不呼叫 → C-5。孤兒契約：無 |
| 3 | **引用逐字核對** | 全部 `檔名:行號` 以腳本逐行印出核對；首稿錯 19 種、23 處已更正（例：`X-04` 的 `why_irreversible` 首稿寫 `:2076-2078`，實為 `:2073-2075`；`resolve_project_role` 的 `consumed_by` 首稿寫 `:1653`，實為 `:1659`；`cicd-pipeline.md` 第 22 項首稿寫 `:330`，實為 `:337`；`requirements.md` 的 FR11.5／FR11.6 首稿各差一行）。事實與定位分開驗：`X-04` 的 `authorization_responsibility`（`:2114-2117`）核對時另發現其字面與 `K-16` 同錯，已併入 C-3／C-5 |
| 4 | **檔案集合一致性** | 四份產出＋問題檔齊備，與前例 `brain-gateway/functional-design/` 的檔案集合相同。問題檔已含 `MB6`（conductor 追加並經選單取得 `[Answer]: A`，2026-10-13T23:08:40Z），共六題；本檔 §十一 改為裁決紀錄。本站作者不編輯問題檔 |
| 5 | **跨檔傳播**（按事實） | `field_key`→`field`：`rules.md` `BR72.5`／`BR72.6`／`BR75.4`、`entities.md` `AllowlistEntry.rename`、本檔 §2.2／D-2／C-2／§十一、`traceability.json` 的 `AC11.4.2`——一致；三個工具：`rules.md` `BR72.2`／`BR72.6`、`entities.md` `Allowlist`、本檔 §2.2／C-1——一致；零環境變數：`BR71.1`、D-10、H-6——一致；錯誤碼七種：`BR76.1`、`entities.md` `ToolOutcome.error`、本檔 MB-W3——七種一致；他單元規則字面：四檔以 `BR[0-9]+\.` 且非 `BR7[1-8]` 掃描為 0 命中 |
| 6 | **可算的數字先算再寫** | 規則數以 YAML 解析實算 **40**（`BR71`×6、`BR72`×9、`BR73`×5、`BR74`×6、`BR75`×4、`BR76`×4、`BR77`×4、`BR78`×2）；traceability 交叉檢查（腳本實算）：OK 列 target 涵蓋 15 條、N/A 列 25 條、兩者無重疊、聯集 40、無懸空 id；上游 AC 3 條（`AC11.4.1`–`AC11.4.3`，`stories.md:727-729`）；錯誤碼 7 種；開放項 12 項；決定 15 項 |
| 7 | **ADR-0006 四面向 ＋ PBT** | 四面向皆「適用」，逐格對照 `requirements.md:617-620` 無一格相反（§六）；PBT：產生器為必須標的（`S-15`），六條性質 |

### 13.2 修訂 1（回應審查 `reviews/review-01.md`，iteration 1 判 NOT-READY；使用者裁決「重開、修進設計再審」）

**逐項落點**（十項全部照 Required action 處置，無拒絕項）：

| 發現 | 處置 | 落點 |
|---|---|---|
| `R-01` | 路徑段安全改由字元集白名單保證：`agent_group`／`field` 必須符合 `^[a-z0-9_]{1,64}$`（與 `U20` 的 `KEY_PATTERN` 逐字相同，一致性測試鎖住），純句點段一律 `invalid_argument`；百分比編碼降為縱深防禦並寫明其不足（`quote` 不編碼句點、httpx 正規化 dot-segment，引審查員 httpx 0.28.1 實測）。schema 帶 `pattern`，不採 `enum`（D-16）。性質六改以 `httpx` `build_request` 實際組出的 URL 為判準（段數、前綴、無 `.`／`..` 段）；`"."`、`".."`、`"a/b"`、`"%2e%2e"` 列為 example 必測 | `rules.md` `BR75.4`；`entities.md` `ToolSpec.inputSchema`、`AllowlistEntry.property_patterns`、`BackendCall.path` 與其不變量；本檔 §2.2、MB-W3 第 5／6 步、§六 性質六與 example 列、D-4、D-16、§十二 T-4／T-7；`traceability.json` `BR75.4` |
| `R-02` | 新增兩條必測規則：並發多 client 不同 token 交錯、backend 端 `Authorization` 各自正確（驗 `BR73.3`）；`BR76.1` 每列錯誤分支與成功分支的工具結果全文與全部 logger 輸出不含 token（驗 `BR73.4`、`BR77.2`）。兩者列入 `code-generation` 必測清單並附必做突變 | `rules.md` `BR78.4`、`BR78.5`；本檔 §十二 T-1／T-2、`OPEN-MB21-7`；`traceability.json` `BR73.3`、`BR73.4`、`BR77.2`、`BR78.4`、`BR78.5` |
| `R-03` | 依 `[MB6]`=A 全檔同步：題數改六題、移除「待裁決／未作答／設計預設」字樣、`OPEN-MB21-3` 關閉、C-2 改為已定（`X-04` 字面仍需追認，時點不變）、13.1 第 4 項更新、`traceability` `AC11.4.2` 刪條件句；§十一 改為裁決紀錄 | `rules.md` 第一節前言與 `BR72.5`；`entities.md` `AllowlistEntry.rename`；本檔開頭、§2.2、H-3、D-2、7.1 標題、`OPEN-MB21-3`／`-6`、C-2、§十一、13.1 第 4 項；`traceability.json` `AC11.4.2` |
| `R-04` | (1) 策略由 openapi **衍生** allowlist，以八個類別各施加單一破壞，`event` 標記、`target` 引導，`tearDownClass` 以計數器強制成功分支 ≥ 60／300、其餘類別各 ≥ 15；(2) 性質一、二、五、七逐類斷言**單一**錯誤碼，並以 `BR72.1` 固定檢查順序（底線先於白名單）使其可行；(3) 突變驗證七列列為必做並寫明預期紅燈的性質；(4) `AC11.4.2` 期望白名單為測試檔內字面值、不讀 `allowlist.json`；(5) `BR72.9` 改述為讀取輸入集合封閉、輸出為 `generated_tools.json` | `rules.md` `BR72.1`、`BR72.6`、`BR72.9`；`entities.md` `GeneratorError.code`；本檔 §六（策略、類別表、性質表、突變表、字面白名單段）、D-17、§十二 T-3／T-5／T-6；`traceability.json` `AC11.4.2` |
| `R-05` | 不變量：`method != GET` 或有 `inject` ⇒ `requires_agent`，否則 `GeneratorError("agent_requirement_mismatch")`；成員管理類以路徑前綴白名單（程式常數，第一版只有 `/api/requirements/`）落實，否則 `path_outside_scope`；產生與啟動（`BR71.5`）皆檢查；納入 PBT 性質二、七 | `rules.md` `BR72.10`、`BR72.11`、`BR71.5`、`BR74.3`；`entities.md` `AllowlistEntry.requires_agent` 與不變量、`Allowlist` 不變量、`ToolSpec.requires_agent`、`GeneratorError.code`；本檔 §2.5、MB-W1、§六、D-18、§十二 T-8；`traceability.json` `BR72.10`、`BR72.11` |
| `R-06` | facade 代寫空值檢查定位改為 `:360-365`（`raise` 在 `:365`），F-8 改為 `:352-365`。`stories.md` 的「Given 今天不可構造」實在 `:731`：本站四份產出不含 `:732`（`grep` 0 命中）；錯誤定位只在 `functional-design-questions.md` 第二節，**本站不得編輯問題檔**，故在此記錄正確定位為 `:731`。另依審查要求以 `sed -n` 重驗本輪全部新增與修改的定位，見下方第 3 項 | `rules.md` `BR74.6`；本檔 F-8 |
| `R-07` | C-5 改為**移除** `McpBridge → ProjectMembership` 邊（逐處列出 `components.md` 的六個落點，邊數 17 → 16），並同步移除 `K-16` `consumed_by`、`consumers.separate_process` 與標題消費者清單中的 `U21`；寫明是移除而非註記 | `rules.md` `BR75.3`；本檔 C-5、IAM 格；`traceability.json` `BR75.3` |
| `R-08` | Encryption 格改寫為「以詮釋滿足、殘留明文」，新增 `OPEN-MB21-13`；Audit 格揭露成功讀取無帶使用者身分的紀錄，新增 `OPEN-MB21-14`；兩者標明於本站核可關卡呈現 | `rules.md` `BR71.2`、`BR77.3`；本檔 §六 Encryption／Audit 兩格、7.2 |
| `R-09` | 補第二退路（同一映像內獨立 requirements 檔裝進獨立 virtualenv，不碰 FastAPI 釘選），升 FastAPI 降為最後手段且須另開題；A-2 判定與退路順序寫成 `code-generation` 的第一步；揭露耦合代價（含 `mcp` 進入 backend 執行期映像）為 `OPEN-MB21-15` | `rules.md` `BR78.2`；本檔 H-5、A-2、`OPEN-MB21-7`、`OPEN-MB21-15`、§十二 第 1 步 |
| `R-10` | 增列唯一組裝點 `create_app(backend_client, registry, tool_specs, allowed_hosts)` 與 `configure_logging()`，規定正式啟動與測試皆經它建立；執行層以 `build_request`＋`send` 送出 | `rules.md` `BR78.3`、`BR78.2`；本檔 §2.5、MB-W1 第 1／4 步、MB-W3 第 6 步、D-19 |

**本站核可關卡須呈現的開放項**：`OPEN-MB21-1`（既有）、`OPEN-MB21-13`（Encryption 詮釋）、`OPEN-MB21-14`（讀取無主體稽核）、`OPEN-MB21-15`（`mcp` 與 FastAPI 釘選耦合）。

**七項自檢（修訂 1 後重跑）**：

| # | 項目 | 結果 |
|---|---|---|
| 1 | **可達性** | 新增的偵測規則逐一可構造：`agent_requirement_mismatch`（allowlist 寫入項設 `requires_agent: false`）；`path_outside_scope`（allowlist 加 `/api/membership/projects/{project_id}/members`，該 operation 確在 `openapi.json:4669`）；`BR75.4` 的 dot-segment（工具參數 `agent_group=".."`）；`BR71.5` 的手改產物（拿掉 `requires_agent`、加入 membership 項）；`BR78.4` 要偵測的「contextvar 串號」以突變（token 改存模組變數）構造；`BR78.5` 每一列錯誤分支的觸發方式逐列寫在規則內（`backend_unavailable` 以拋 `httpx.ConnectError` 的傳輸與回 503 的包裝構造，`internal_error` 以回 418 與非 JSON 的 200 構造）。`BR72.1` 的固定順序使每個 PBT 類別在到達其目標檢查之前不會被較早的檢查攔下（類別的破壞只觸及該檢查的條件；`missing_op` 的 path 刻意留在前綴內） |
| 2 | **契約端點三問**（全部產出，不只本輪動過的） | 新增欄位：`AllowlistEntry.property_patterns` 寫＝人（PR）、讀＝`generate_tools` 與 T-7、清＝人；`ToolSpec.requires_agent` 寫＝`generate_tools`、讀＝`resolve_agent` 與 `validate_tool_specs`、清＝重產覆寫；`ALLOWED_PATH_PREFIXES` 寫＝程式常數、讀＝`generate_tools` 與 `validate_tool_specs`、清＝改程式。新增方法：`create_app` 擁有＝本單元、呼叫＝`__main__` 與全部整合測試；`configure_logging` 擁有＝本單元、呼叫＝`__main__` 與 T-2；`validate_tool_specs` 呼叫＝MB-W1 第 2 步與 T-8。既有項重跑：`RequestCredential`、`on_behalf_of`、三份進版控檔與 13.1 第 2 項相同。C-5 之後 `resolve_project_role` 不再列本單元為消費者，三問不再懸空。**同檔內 behaviour 與依賴宣告互斥檢查**：`BR75.3` 宣告「不呼叫成員層」，C-5 已移除對應的 `depends_on` 邊，兩者不再對撞。孤兒契約：無 |
| 3 | **引用逐字核對（定位）** | 本輪新增或修改的定位全部以 `sed -n` 印出逐一重驗：`requirement_field_definitions.py:33`（`KEY_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")`）；`requirement_field_facade.py:272-276`（被拒讀取的 `logger.warning`）、`:301-305`（`read_fields` 無 log）、`:360-365`（`stripped = value.strip()` 至 `raise ... "blank_on_behalf"`）；`openapi.json:4669`、`:4776`、`:4917`、`:4945`（四個 `/api/membership/` 路徑）；`components.md:567-568`（`ProjectMembership.dependents` 的 `McpBridge` 項）、`:664-666`（`McpBridge.depends_on` 的 `ProjectMembership` 項——首稿寫 `:663-665`，重驗後更正）、`:775`、`:788`、`:809`、`:811`；`contract-summary.md:1611`、`:1622`、`:1659`、`:1834-1835`、`:2081-2082`；`auth.py:33`（8 小時）、`:47`（`create_access_token`）；`requirements.md:618`、`:620`；`backend/requirements.txt:1-7`（釘選紀律）、`:8`（`fastapi==0.111.0`）；`stories.md:728`、`:731`。httpx 的 dot-segment 行為**未由本站實測**（依派工不得執行程式），引用的是審查員 httpx 0.28.1 的實測結果 |
| 4 | **檔案集合一致性** | 四份產出（`entities.md`、`rules.md`、`functional-spec.md`、`traceability.json`）＋問題檔＋`reviews/review-01.md`，與前例 `brain-gateway/functional-design/` 同形；本輪未新增或刪除檔案。問題檔共六題（`MB1`–`MB6`），本站未編輯；審查檔未編輯 |
| 5 | **跨檔傳播**（按事實，逐種表達形式 grep 四檔；計數皆**不含本節 13.2** 自身的引述，`grep -c` 以行計） | **`MB6` 狀態**：「待裁決」「未作答」「待 `MB6`」「依 `MB6` 結果」「五題」「`MB1–MB5`」皆 0 命中；「設計預設」僅剩兩處「不再是設計預設」的歷史敘述；「待追認」0 命中（統一為「`X-04` 字面仍需追認」）。**`field_key`→`field`**：四檔 27 行命中（`entities.md` 1、`rules.md` 10、本檔 15、`traceability.json` 1）逐一判讀，API 名（路徑樣板、`binding`、反向映射、上游引文）與工具名（白名單、schema）用法一致。**路徑安全機制**：「路徑段編碼」「路徑段百分比編碼」「無法改變目標路徑」0 命中；樣式字串 `^[a-z0-9_]{1,64}$` 於 `entities.md` 3 行、`rules.md` 1 行、本檔 2 行，`build_request` 判準於四檔皆有。**移除邊**：`BR75.3`、C-5、IAM 格、`traceability` `BR75.3` 一致寫「移除」。**`requires_agent` 不變量**：`entities.md` 3、`rules.md` 7、本檔 8、`traceability` 1 行。**錯誤碼**：`ToolOutcome` 7 種不變；`GeneratorError` 9 種，`BR72.1` 順序、`entities.md` 列舉、§六 類別表三處一致。**字面期望白名單**：`rules.md` `BR72.6`、本檔 §六／T-5、`traceability` `AC11.4.2` 一致，`traceability` 原「等於 allowlist 宣告」已改。**範圍字面**：`BR72.1`–`BR72.9`／`BR78.1`–`BR78.2` 等舊範圍 0 殘留（H-2、§2.5、摘要表已改為含 `BR72.10`／`BR72.11`／`BR78.5`）。**他單元規則字面**：四檔擷取全部 `BR\d+\.\d+`，非 `BR71`–`BR78` 者 0；引用的 `BR7x` 識別字全部在 `rules.md` 有定義 |
| 6 | **可算的數字先算再寫** | 規則總數以 `grep '^  - id: BR' rules.md` 實算 **45**（`BR71`×6、`BR72`×11、`BR73`×5、`BR74`×6、`BR75`×4、`BR76`×4、`BR77`×4、`BR78`×5）。`traceability.json` 以 `jq` 實算：coverage **33** 列＝`OK` **3** 列（`AC11.4.1`–`AC11.4.3`）＋`N/A` **30** 列；`OK` 列 target 涵蓋規則 **15** 條、`N/A` 列 **30** 條、交集 **0**、聯集 **45**＝規則總數、無懸空 id、無遺漏；`upstream_ids` 3。決定 **19** 項（D-1–D-19）；開放項列 **15** 列（`OPEN-MB21-3` 已關閉，未結 14）；`GeneratorError` 碼 9 種；PBT 類別 8、性質 7、突變 7 列；必測 T-1–T-8 共 8 項 |
| 7 | **ADR-0006 四面向 ＋ PBT** | 逐格對照 `requirements.md:617-620`：上游 IAM「適用（三處）」、Encryption「適用（新增一處）」、Network exposure「適用（新增一處）」、Audit logging「適用（兩處）」；本表四格皆「適用」，**無一格相反**。差異只在處置的誠實度：Encryption 由「滿足」改為「以詮釋滿足、殘留明文」（`OPEN-MB21-13`），Audit 揭露讀取面不成立（`OPEN-MB21-14`）——兩者是把上游要求與本設計的落差寫出來，不是改判定。PBT：產生器仍為必須標的（`S-15`），性質由六條增為七條，並補上「策略衍生一致配對＋成功分支下限＋逐類單一錯誤碼＋必做突變」使性質不至恆真 |
