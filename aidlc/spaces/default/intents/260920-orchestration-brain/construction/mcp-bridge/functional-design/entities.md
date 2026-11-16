# Entities — `U21 mcp-bridge`

> 本單元**不擁有任何持久實體**，也不擁有任何資料表（`components.md` 的 `McpBridge.entities: []`）。需求欄位的持久狀態在 `U20`
> （`system_requirement_fields`，經 `K-17` 的 facade）；成員關係在 `U19`（`K-16`）。本單元擁有的是三份**進版控的設定產物**
> （allowlist、產生出的工具宣告、agent 登錄表）、幾個**純值物件**，以及一個**只活在單一 HTTP 請求內**的憑證容器。
>
> 本單元**沒有任何跨請求的執行期狀態**：傳輸採無狀態模式（`BR71.2`），token 與 agent 宣告逐請求帶入、請求結束即重設
> （`BR73.3`）。唯一長駐的物件是共用的 HTTP client（連線池），它刻意不帶任何身分（`BR73.3`）。

```yaml
entities:
  - name: AllowlistEntry
    kind: value_object
    description: >
      allowlist.json 的一項：決定某個 OpenAPI operation 是否、以何種形狀成為 MCP 工具。進版控、預設拒絕（BR72.2）。
      擴充它是人的決定，刻意不自動化（cicd-pipeline.md 第 24 項）。
    attributes:
      - name: method
        type: enum[GET, PUT, DELETE, POST, PATCH]
        required: true
        constraints: 與 openapi 的 operation 精確對應
      - name: path
        type: string
        required: true
        constraints: OpenAPI path 的精確字串（含 {param} 樣板）
      - name: name
        type: string
        required: true
        constraints: 工具名，snake_case，在 allowlist 內唯一；第一版三個見 BR72.2
      - name: description
        type: string
        required: true
        constraints: 繁體中文；不得提及被剝除的屬性（BR72.8）
      - name: properties
        type: list[string]
        required: true
        constraints: 白名單——產生結果的屬性鍵集合必須等於它（BR72.6）
      - name: property_descriptions
        type: map[string, string]
        required: true
        constraints: 鍵集合等於 properties
      - name: strip_body_fields
        type: list[string]
        required: false
        constraints: 本體屬性名；被剝除者不進 schema、不進 required（BR72.4）
      - name: inject
        type: map[string, enum[agent_group_of_declared_agent]]
        required: false
        constraints: 鍵必須 ∈ strip_body_fields；第一版唯一的來源種類是「已宣告 agent 對應的代寫組」
      - name: rename
        type: map[string, string]
        required: false
        constraints: api_name → tool_name；第一版 field_key → field（BR72.5，[MB6]=A 已裁決）
      - name: property_patterns
        type: map[string, string]
        required: false
        constraints: >
          工具屬性名 → 正規式；產生器寫進 inputSchema 的 pattern。第一版 write／clear 的 agent_group 與 field 為
          ^[a-z0-9_]{1,64}$，必須等於 calls.py 的驗證常數與 U20 的 KEY_PATTERN（BR75.4，以測試鎖住）
      - name: requires_agent
        type: boolean
        required: true
        constraints: >
          write／clear 為 true，read 為 false（BR74.3）。**不變量而非約定**：method != GET 或 inject 非空時必須為 true，
          否則 GeneratorError("agent_requirement_mismatch")（BR72.10）
    invariants:
      - "(method, path) 在 allowlist 內唯一；name 在 allowlist 內唯一"
      - "改名後的 properties 不得命中黑名單底線（BR72.7）——allowlist 本身也要過底線"
      - "(method != GET or inject) ⇒ requires_agent（BR72.10，產生與啟動皆檢查）"
      - "path 以 ALLOWED_PATH_PREFIXES 之一開頭；第一版只有 /api/requirements/（BR72.11）"

  - name: Allowlist
    kind: value_object
    description: allowlist.json 的整體；第一版恰三項（[MB4]=A）。
    attributes:
      - name: entries
        type: list[AllowlistEntry]
        required: true
        constraints: 第一版 = read_requirement_fields、write_requirement_field、clear_requirement_field
    invariants:
      - "不含 U19 成員管理類 operation（[MB4]=A；ADR-0004 高風險工具需核准）——以 BR72.11 的路徑前綴白名單落實（成員端點皆在 /api/membership/ 之下），產生與啟動皆檢查，並納入 PBT 的 out_of_scope 類別"

  - name: ToolSpec
    kind: value_object
    description: >
      generate_tools 的輸出元素（BR72.1），序列化為 generated_tools.json 的一項，執行期由 bridge 載入並註冊為 MCP 工具。
    attributes:
      - name: name
        type: string
        required: true
        constraints: 取自 AllowlistEntry.name
      - name: description
        type: string
        required: true
        constraints: 取自 AllowlistEntry.description
      - name: inputSchema
        type: JSON Schema object
        required: true
        constraints: >
          type: object；additionalProperties: false；properties 鍵集合 = 白名單；全部屬性為 string；
          value 屬性加 minLength: 1；agent_group 與 field 帶 pattern ^[a-z0-9_]{1,64}$（BR75.4）；遞迴任何深度的屬性名不得命中 token|key|secret|authorization（不分大小寫，子字串）
      - name: requires_agent
        type: boolean
        required: true
        constraints: 取自 AllowlistEntry；啟動時以 BR72.10 重驗；不出現在 tools/list 回應
      - name: binding
        type: object {method, path, path_params: map[tool_name→api_name], query_params: map, body_params: map, inject: map}
        required: true
        constraints: >
          bridge 組請求所需的映射；**不屬於工具宣告**——tools/list 回應中不出現（它描述的是 bridge 內部如何轉成 HTTP，不是給 agent 的介面）
    invariants:
      - "inputSchema 內不出現 on_behalf_of、任何 security 衍生參數、任何 header／cookie 參數（BR72.3、BR72.4）"
      - "binding.inject 的鍵不出現在 inputSchema.properties"

  - name: AgentRegistry
    kind: value_object
    description: >
      agents.json：已登錄 agent 名 → 代寫組（on_behalf_of 值）。是已宣告代寫組的白名單（BR74.2）。進版控。
    attributes:
      - name: agents
        type: map[string, string]
        required: true
        constraints: >
          鍵：^[a-z0-9-]{1,64}$；值 ⊆ U20 的 GROUPS_BY_KEY（requirement_field_definitions.py:119），以測試鎖住。
          第一版 {"cost": "cost", "architecture": "architecture"}
    invariants:
      - "值集合 ⊆ backend 宣告的代寫組集合（team.md 單一真實來源：跨進程副本必須有一致性測試）"

  - name: RequestCredential
    kind: value_object
    description: >
      單一 MCP HTTP 請求內的身分材料，由 ASGI middleware 放入 contextvar、請求結束於 finally 重設（BR73.3）。
      **這是本單元唯一接觸 token 的物件。**
    attributes:
      - name: authorization
        type: string | null
        required: false
        constraints: >
          Authorization 標頭原值；只在通過 BR73.1 的格式檢查後才被使用；**不得**被 repr、str、log、序列化
          （實作上其 __repr__ 回傳固定字串 "<redacted>"）
      - name: declared_agent
        type: string | null
        required: false
        constraints: X-Cloud360-Agent 原值；只用於查 AgentRegistry，不寫入 log（BR77.1 以 undeclared／unregistered 取代）
    invariants:
      - "生命週期 ⊆ 一次 HTTP 請求；跨請求不可見"
      - "不轉送給 backend 以外的任何目的地；declared_agent 不轉送給 backend（BR73.2）"

  - name: BackendCall
    kind: value_object
    description: >
      純函式 build_backend_call(tool_spec, arguments, agent_group) 的輸出：一次對 backend 的請求計畫（BR75.4、BR74.4）。
      不含 Authorization——token 由執行層自 RequestCredential 加上，使純函式永遠看不到 token。
    attributes:
      - name: method
        type: enum[GET, PUT, DELETE]
        required: true
      - name: path
        type: string
        required: true
        constraints: >
          只由通過 BR75.4 白名單的段組成（system_id 為數字、agent_group/field 為 ^[a-z0-9_]{1,64}$），再以 quote(s, safe="") 編碼作縱深防禦；
          開頭固定為 allowlist 的 path 前綴。百分比編碼本身不保證安全：quote 不編碼句點，httpx 會正規化 dot-segment（審查 review-01 R-01 實測）
      - name: json_body
        type: object | null
        required: false
        constraints: 寫入時恰為 {value, on_behalf_of}；讀與清空為 null
    invariants:
      - "以執行層實際使用的 httpx client.build_request 組出的請求 URL 為判準：path 段數等於樣板段數、前綴等於 allowlist 前綴、不含 . 或 .. 段、解碼後各段等於參數值（PBT 性質六）；計畫字串本身不是判準"

  - name: ToolOutcome
    kind: value_object
    description: 純函式 map_outcome 的輸出，對應 BR76.1 的封閉表。
    attributes:
      - name: ok
        type: boolean
        required: true
      - name: payload
        type: object | null
        required: false
        constraints: ok 時為 backend 200 本體的 JSON
      - name: error
        type: enum[unauthenticated, agent_not_declared, invalid_argument, forbidden, not_found, backend_unavailable, internal_error] | null
        required: false
      - name: message
        type: string | null
        required: false
        constraints: 固定文字或經 BR76.2 過濾的 backend detail；不含 token、不含例外原文
      - name: retryable
        type: boolean
        required: true
        constraints: 只有 backend_unavailable 為 true
    invariants:
      - "ok 與 error 恰一者成立"

  - name: GeneratorError
    kind: value_object
    description: generate_tools 的唯一失敗形式；產生腳本收到即 exit(1)，啟動自我驗證收到即 exit(1)（BR71.5）。
    attributes:
      - name: code
        type: enum[path_outside_scope, missing_operation, unsupported_parameter_location, unsupported_body, name_collision, inject_without_strip, agent_requirement_mismatch, credential_like_property, whitelist_mismatch]
        constraints: 九種；依 BR72.1 檢查順序中首次出現的位置排列（unsupported_body 在第 4 與第 10 步各出現一次），每一類違反恰得一個碼
        required: true
      - name: tool_name
        type: string
        required: true
    invariants:
      - "訊息只含 code 與 tool_name，不含 openapi 片段"

  - name: BridgeLogRecord
    kind: value_object
    description: 每次 tools/call 的一行 INFO（BR77.1）。
    attributes:
      - name: tool
        type: string
        required: true
      - name: agent
        type: string
        required: true
        constraints: 已登錄名、undeclared 或 unregistered
      - name: outcome
        type: string
        required: true
        constraints: ok 或 ToolOutcome.error 之一
      - name: http_status
        type: integer | null
        required: false
      - name: duration_ms
        type: integer
        required: true
    invariants:
      - "不含 token、參數、本體、例外文字（BR77.2）"
```

## 摘要

| 物件 | 種類 | 生命週期 | 寫 | 讀 | 清 |
|---|---|---|---|---|---|
| `AllowlistEntry`／`Allowlist` | 進版控設定 | 版本 | 人（PR） | `gen_mcp_tools.py` | 人（PR） |
| `ToolSpec`（`generated_tools.json`） | 進版控產物 | 版本 | `gen_mcp_tools.py` | bridge 啟動（`BR71.5`）、漂移閘門（`BR72.9`） | 重產覆寫 |
| `AgentRegistry`（`agents.json`） | 進版控設定 | 版本 | 人（PR） | bridge 啟動、`BR74.3`／`BR74.4` | 人（PR） |
| `RequestCredential` | contextvar | 一次請求 | ASGI middleware | 工具處理函式 | middleware 的 `finally` |
| `BackendCall`／`ToolOutcome`／`BridgeLogRecord` | 純值 | 一次呼叫 | 純函式 | 執行層 | 隨呼叫結束 |
| `GeneratorError` | 純值 | 一次產生 | `generate_tools` | 產生腳本、啟動 | — |
