# Rules — `U21 mcp-bridge`

## 一、識別字區段：`BR71.x`–`BR78.x`

已佔用：`BR1`–`BR8`、`BR21`–`BR28`、`BR31`–`BR35`、`BR41`–`BR47`、`BR51`–`BR58`、`BR61`–`BR67`。本單元取
**`BR71`–`BR78`**。引用他單元的規則一律寫成「`U<n>` 的規則 x.y」，不寫出他單元識別字的字面形式。

六題定案（出處：`functional-design-questions.md`）：`[MB1]`=A（本單元交付 server ＋ 最小測試 client；大腦側 client 列開放項）、
`[MB2]`=A（每次 MCP 請求的 `Authorization: Bearer` 原樣轉給既有 API、用完即棄）、`[MB3]`=A（產生器剝除
`on_behalf_of`；agent 身分在連線層宣告，bridge 對照白名單後自行填入；自報不可驗證，揭露為已知限制）、`[MB4]`=A（只開需求欄位的
讀、寫、清空三個工具）、`[MB5]`=A（Python ＋ 官方 `mcp` SDK，沿用 backend 映像另起 compose 服務）、`[MB6]`=A（工具屬性
`field_key` 改名為 `field`，黑名單底線維持不分大小寫的子字串比對；問題檔 `[Answer]: A`，2026-10-13T23:08:40Z 經選單作答）。

上游已定案、本單元逐條遵守者（問題檔第一節）：`[I6]`=A 的 HTTP／SSE 第七服務、`[I7]`=A 的 REST→MCP 產生器 ＋ allowlist、`X-04` 的
憑證白名單與黑名單底線、`FR11.6` 的「每次以使用者身分呼叫既有 API」、稽核主體為使用者本人、不需認證的 liveness、`U20` 交接的
「代寫一律帶 `on_behalf_of`、清空走 `DELETE`、不得繞過 facade」。

> **`BR72.5` 已由使用者裁決**：工具參數 `field_key` 改名為 `field`，是為了讓 `X-04` 自身的白名單與黑名單底線不互相牴觸，
> `[MB6]`=A 採納（裁決紀錄見 `functional-spec.md` §十一）。`X-04` 的對應字面仍需在 `code-generation` 計畫核可前追認（C-2，
> 追認時點與 C-1、C-3～C-5 相同），但規則本身已定，不再是設計預設。

## 二、規則（source of truth）

```yaml
rules:
  # ---- BR71：進程、傳輸與生命週期 ---------------------------------------------
  - id: BR71.1
    statement: "bridge 是獨立進程：compose 第七個服務 mcp-bridge，沿用 backend 映像、以不同的啟動指令執行；不在 FastAPI 進程內"
    category: constraint
    applies_to: 部署形狀
    trigger: 部署
    logic: >
      程式落在 backend/mcp_bridge/（使映像不需改 build context：backend 的 compose build context 為 ../backend，
      docker-compose.deploy.yml:79-81）。啟動指令為 python -m mcp_bridge --backend-url http://backend:8000 --port 8080。
      設定一律以**命令列參數**傳入，模組內**不得**呼叫 os.getenv／os.environ.get——validate_env_contract.py:245 以 rglob
      掃 backend/ 下全部 .py 的環境變數讀取並要求記載於 backend/.env.example；零環境變數使 [I6] 的「零新部署變數」
      在程式層也成立，不觸發 project.md 的 env-contract 與 LOCAL-DEV.md 同步規則（條件見 functional-spec.md §八）。
      backend 進程不 import mcp_bridge（main.py 不掛任何 MCP 路由）。
    violation_behaviour: "掛進 FastAPI 進程 → 推翻 unit-of-work.md 的『不在 FastAPI process 內』；讀環境變數 → validate_env_contract 紅燈，且觸發三處同步義務"
    source: "[MB5]=A；[I6]=A；unit-of-work.md:309；scripts/validate_env_contract.py:245"

  - id: BR71.2
    statement: "傳輸為 MCP streamable HTTP，端點 /mcp；無狀態模式、回應以 JSON 為主；只在 internal 網段，不發佈 ports"
    category: constraint
    applies_to: 傳輸層
    trigger: 啟動
    logic: >
      採官方 SDK 的 streamable HTTP 傳輸（MCP 規格 2025-03-26 起取代舊的 HTTP＋SSE 雙端點傳輸；streamable HTTP 在需要時
      仍以 SSE 串流回應，故與 [I6]=A 的「HTTP／SSE」一致）。啟用無狀態模式（每個請求獨立、不建立伺服器端 session 對應），
      理由：使用者 token 與 agent 宣告都是**逐請求**帶入（BR73.1、BR74.1），伺服器不需要、也不得保存任何跨請求的身分狀態。
      容器內綁 0.0.0.0:8080；compose 的服務只列 networks: [internal]、**無 ports:**。
      不選舊 HTTP＋SSE 雙端點的理由：它需要長駐 SSE 連線與伺服器端 session 對應，與「逐請求身分、不存狀態」相反。
      傳輸為 internal 橋接網段上的明文 HTTP：把「不離開本主機」視為滿足 requirements.md:618「本機迴環或加密」是**詮釋**，
      橋接網段不是迴環，使用者 JWT 以明文在與 redis、ollama 共用的網段上往返——殘留列 OPEN-MB21-13，待使用者於核可關卡確認。
    violation_behaviour: "發佈 ports 或加入 edge → 違反 requirements.md:619『不得對外暴露』；有狀態 session 綁定身分 → 使用者切換時身分錯綁"
    source: "[I6]=A（infrastructure-design-questions.md:297）；requirements.md:619；infrastructure-specification.md 7.1"

  - id: BR71.3
    statement: "liveness 端點 GET /healthz：不需認證、不呼叫 backend、不回傳任何工具資訊，恆回 200"
    category: constraint
    applies_to: 健康檢查
    trigger: 容器 healthcheck
    logic: >
      與 /mcp 同一個 ASGI 應用、同一個埠。回應本體固定為 {"status":"ok"}。它只證明 HTTP server 在接受連線
      （monitoring-design.md:177 的「不證明」欄原樣成立）。compose 的 healthcheck 必須覆寫映像內建的
      HEALTHCHECK（backend/Dockerfile:28 探 127.0.0.1:8000/，bridge 不聽該埠），見 functional-spec.md §八 H-3。
    violation_behaviour: "用需認證端點當 healthcheck → 容器內要放長期 token（monitoring-design.md:181）；探 backend → backend 啟動慢時 bridge 被判不健康"
    source: "monitoring-design.md:177、:181；backend/Dockerfile:28"

  - id: BR71.4
    statement: "啟動不依賴 backend；backend 不可達或回 5xx 只讓該次工具呼叫失敗，進程不退出"
    category: constraint
    applies_to: 啟動與執行期
    trigger: backend 連線拒絕、逾時、5xx
    logic: >
      工具宣告於建置期產生並進版控（BR72.9），執行期**不**向 backend 取 openapi.json，故啟動流程不含任何對 backend 的呼叫。
      執行期對 backend 的連線錯誤（拒絕、DNS 失敗、逾時）與 5xx（含經代理時的 502／503／504）一律映射為 backend_unavailable
      （BR76.1），不拋出到 ASGI 層、不終止進程。注意：bridge 直連 backend:8000（uvicorn），不經 nginx，
      故啟動初期實際看到的多半是**連線拒絕**而非 502——兩者同一處置。
    violation_behaviour: "啟動時探 backend 失敗即退出 → restart: unless-stopped 形成重啟迴圈（monitoring-design.md:188）"
    source: "monitoring-design.md:184-188；[I6]=A"

  - id: BR71.5
    statement: "啟動時自我驗證工具宣告與 agent 登錄；不合格即以非零碼退出（設定錯誤是致命錯誤）"
    category: validation
    applies_to: 啟動
    trigger: 進程啟動
    logic: >
      載入 generated_tools.json 與 agents.json 後，重跑 BR72.6（白名單相等）、BR72.7（黑名單底線）、BR72.10（requires_agent
      與 method／inject 綁定）與 BR72.11（路徑前綴白名單）的檢查、並檢查
      agents.json 的每個值都屬於宣告的代寫組集合（BR74.2）。任一不過 → 記一行 ERROR（只含違規的工具名或 agent 名，不含其他內容）
      並 exit(1)。這與 BR71.4 刻意不同：backend 暫時不可用是可恢復的；工具宣告含憑證欄位是**不得帶病上線**的。
    violation_behaviour: "帶著含憑證欄位的工具宣告啟動 → C-T11 的不可逆失敗（token 進 LLM context）"
    source: "X-04 credential_whitelist.why_irreversible（contract-summary.md:2073-2075）；construction.md Error Handling（recoverable vs fatal）"

  - id: BR71.6
    statement: "若所釘版本的 SDK 啟用 Host 標頭檢查（DNS rebinding 防護），允許清單只含 mcp-bridge:8080 與本機迴環"
    category: constraint
    applies_to: 傳輸層
    trigger: 啟動
    logic: >
      允許的 Host：mcp-bridge:8080、localhost:8080、127.0.0.1:8080（後兩者供本機開發與測試）。不得以關閉檢查代替設定。
      SDK 是否具備此設定屬 A-7 的實測範圍（functional-spec.md OPEN-MB21-7）；不具備時本規則不適用，並在 code-generation 記錄。
    violation_behaviour: "關閉檢查 → 任何能把瀏覽器導向 internal 位址的頁面都可對 bridge 發請求（雖仍需使用者 token）"
    source: "本站決定 D-6；requirements.md:619"

  # ---- BR72：REST→MCP 產生器（PBT 標的） --------------------------------------
  - id: BR72.1
    statement: "產生器是純函式 generate_tools(openapi, allowlist) -> tuple[ToolSpec, ...]：無 I/O、決定性、依工具名排序"
    category: constraint
    applies_to: backend/mcp_bridge/generator.py
    trigger: 產生工具宣告
    logic: >
      輸入為已解析的 openapi dict 與已解析的 Allowlist 物件；讀檔與寫檔由外層腳本 backend/scripts/gen_mcp_tools.py 負責。
      模組內禁止 import httpx、DB session 型別、HTTPException、mcp 的伺服器物件（可執行檢查：grep 結果須為零）。
      任何違反 BR72.2–BR72.7、BR72.10、BR72.11 的情形一律 raise GeneratorError(code, tool_name)，不部分產出、不略過。
      輸出依 tool name 排序；同一輸入兩次呼叫結果相等，且與 openapi paths 的鍵順序無關。
      **檢查順序固定**（使每一類違反對應恰好一個錯誤碼，PBT 可逐類斷言單一碼，見 functional-spec.md §六）：
      對每一項 allowlist entry 依序——(1) path_outside_scope（BR72.11）→ (2) missing_operation（BR72.2）→
      (3) unsupported_parameter_location（BR72.3）→ (4) unsupported_body（BR72.3 的媒體型別與非 object）→
      (5) name_collision（BR72.3）→ (6) inject_without_strip（BR72.4）→ (7) agent_requirement_mismatch（BR72.10）→
      套用 strip 與 rename（BR72.4、BR72.5）→ (8) credential_like_property（BR72.7，遞迴，**在改名之後、白名單比對之前**）→
      (9) whitelist_mismatch（BR72.6）→ (10) unsupported_body（任一工具屬性型別不是 string）。
      黑名單底線排在白名單之前，是為了讓「審核者把憑證欄位同時寫進 API 與白名單」與「白名單漂移」兩種違反
      分別只得到各自的碼，拿掉任一道檢查都會讓對應的 PBT 類別紅燈，而不會被另一道檢查的碼掩蓋。
    violation_behaviour: "產生器做 I/O 或非決定性 → 漂移閘門會在無關 PR 上紅燈，且 PBT 無法施作"
    source: "[I7]=A；infrastructure-specification.md 7.3（PBT 標的）；S-15"

  - id: BR72.2
    statement: "只有 allowlist 列出的 (method, path) 會產生工具；allowlist 指向不存在的 operation 即產生失敗"
    category: validation
    applies_to: generate_tools
    trigger: 產生工具宣告
    logic: >
      allowlist 的鍵為 (HTTP method, OpenAPI path) 的精確字串對；預設拒絕。openapi 中找不到該 operation → GeneratorError("missing_operation")，
      不得靜默略過（否則 API 改名會讓工具無聲消失，而漂移閘門看到的是「產物一致」）。
      第一版 allowlist 恰為三項（[MB4]=A）：
      GET  /api/requirements/systems/{system_id}/fields                          → read_requirement_fields
      PUT  /api/requirements/systems/{system_id}/fields/{agent_group}/{field_key} → write_requirement_field
      DELETE 同上路徑                                                             → clear_requirement_field
      這比 [I7]=A 寫的初始值（U19＋U20 兩塊）窄：成員管理類不開放（ADR-0004 高風險工具需核准），屬已核可範圍的收窄，見 functional-spec.md 契約增量 C-4。
    violation_behaviour: "預設允許或靜默略過 → 暴露面隨 API 自動成長或無聲縮水"
    source: "[MB4]=A；[I7]=A（infrastructure-design-questions.md:366）；openapi.json:5329、:5397"

  - id: BR72.3
    statement: "只有 path、query 參數與 JSON 本體的頂層屬性會成為工具屬性；security 需求一律不產生任何屬性；header／cookie 參數使產生失敗"
    category: validation
    applies_to: generate_tools
    trigger: 產生工具宣告
    logic: >
      operation 的 security（本 repo 唯一的 scheme 是 HTTPBearer，openapi.json:2033-2037）**不轉成任何輸入屬性**——token 由 BR73 的路徑注入。
      in: header 或 in: cookie 的參數 → GeneratorError("unsupported_parameter_location")：它們最可能承載憑證，且本版三個 operation 皆沒有。
      requestBody 只接受 application/json 且 schema 為 object；其他媒體型別 → GeneratorError。
      path／query 參數與本體屬性同名 → GeneratorError("name_collision")。
    violation_behaviour: "把 HTTPBearer 轉成一個 authorization 屬性 → token 以工具參數傳遞，違反 FR11.5"
    source: "[I7]=A 的『剝除 HTTPBearer』；FR11.5（requirements.md:265-269）"

  - id: BR72.4
    statement: "allowlist 的 strip_body_fields 指定的本體屬性從工具 schema 剝除；第一版對寫入工具剝除 on_behalf_of，並宣告由 bridge 依 agent 身分注入"
    category: constraint
    applies_to: generate_tools
    trigger: 產生工具宣告
    logic: >
      allowlist 每項可宣告 strip_body_fields: [name...] 與 inject: {name: "agent_group_of_declared_agent"}。被剝除的屬性
      也從 required 移除。inject 的鍵必須是某個被剝除的屬性，否則 GeneratorError("inject_without_strip")。
      write_requirement_field：strip_body_fields=[on_behalf_of]、inject={on_behalf_of: agent}（openapi.json:5521 起的 on_behalf_of 屬性）。
    violation_behaviour: "on_behalf_of 留在 schema → agent 可自填任何代寫組（X-04 contract-summary.md:2083-2084 明文禁止）"
    source: "[MB3]=A；X-04 tools.write_requirement_field.note（contract-summary.md:2083-2084）"

  - id: BR72.5
    statement: "allowlist 的 rename 把 API 名稱映射為工具屬性名稱；第一版把 field_key 改名為 field（[MB6]=A 已裁決）"
    category: constraint
    applies_to: generate_tools
    trigger: 產生工具宣告
    logic: >
      rename: {api_name: tool_name}。產生時以 tool_name 宣告屬性；BR75.4 組請求時反向映射回 api_name。
      第一版：write／clear 兩個工具的 field_key → field。理由：AC11.4.2 與 X-04 的黑名單底線為「名稱匹配 key（不分大小寫）」，
      以子字串比對時 field_key 命中 key，而 X-04 自己的允許清單又列了 field_key——同一份契約的兩處互相牴觸。
      採較嚴的讀法（子字串）並以改名消解，不放寬底線——使用者以 [MB6]=A 裁決採納（問題檔 MB6 的 [Answer]: A，
      2026-10-13T23:08:40Z）；裁決紀錄見 functional-spec.md §十一。X-04 字面的對應修改為契約追認 C-2（已定，仍需追認）。
    violation_behaviour: "保留 field_key 且採子字串比對 → BR72.7 使產生失敗；改採完整名稱比對 → access_token、api_key 之類名稱可通過底線"
    source: "[MB6]=A；AC11.4.2（stories.md:728）；X-04 credential_whitelist 與 tools（contract-summary.md:2064-2085）；本站決定 D-2"

  - id: BR72.6
    statement: "每個產生的工具，其 inputSchema.properties 的鍵集合必須**等於** allowlist 宣告的 properties，否則產生失敗"
    category: validation
    applies_to: generate_tools
    trigger: 產生工具宣告
    logic: >
      allowlist 每項必填 properties: [...]（白名單）。產生結果的鍵集合 ≠ 宣告集合 → GeneratorError("whitelist_mismatch")。
      inputSchema 一律帶 additionalProperties: false。第一版的宣告：
      read_requirement_fields: [system_id]；write_requirement_field: [system_id, agent_group, field, value]；
      clear_requirement_field: [system_id, agent_group, field]。
      與 X-04 的差異只在 field_key → field（BR72.5）與新增清空工具（[MB4]=A），列為契約增量 C-1、C-2。
      注意：本規則是**產生器**以 allowlist 為準的一致性檢查；AC11.4.2 的驗收測試另以**寫在測試檔內的字面值**為期望白名單、
      不讀 allowlist.json（functional-spec.md §六、§十二 T-5），否則同一個 PR 同改 allowlist 與產物即可自證通過。
    violation_behaviour: "API 新增本體欄位時工具自動多出一個屬性，無人審核"
    source: "X-04 credential_whitelist.rule（contract-summary.md:2064-2066）；stories.md:737-739（白名單已採納）"

  - id: BR72.7
    statement: "黑名單底線：任何深度的屬性名稱，以不分大小寫的子字串比對命中 token／key／secret／authorization 即產生失敗"
    category: validation
    applies_to: generate_tools
    trigger: 產生工具宣告（改名之後）
    logic: >
      以 re.compile(r"token|key|secret|authorization", re.IGNORECASE).search(name) 對 inputSchema 內**遞迴**每一層 properties 的鍵檢查，
      含 items、anyOf／oneOf／allOf 內的 object。比對發生在 BR72.5 改名之後。命中 → GeneratorError("credential_like_property")。
      本檢查獨立於 BR72.6 的白名單：白名單防「多出未審核的欄位」，底線防「審核者把憑證欄位寫進白名單」。
    violation_behaviour: "token 進入工具參數 → 進入 LLM context，被 checkpointer 持久化且不可逆"
    source: "AC11.4.2（stories.md:728）；FR11.5；X-04 blacklist_floor（contract-summary.md:2067-2068）"

  - id: BR72.8
    statement: "工具名稱與描述取自 allowlist，不取 openapi 的 summary／description"
    category: constraint
    applies_to: generate_tools
    trigger: 產生工具宣告
    logic: >
      openapi 的 PUT 描述逐字提到本體的 on_behalf_of（openapi.json:5483 的 description），直接沿用會讓 agent 以為可以自填。
      allowlist 每項必填 name 與 description；description 以繁體中文寫明用途與限制（寫入工具註明「清空請用 clear_requirement_field」）。
      屬性的 description 亦由 allowlist 給定，不沿用 openapi。
    violation_behaviour: "描述與 schema 不一致 → agent 嘗試傳 on_behalf_of，被 additionalProperties 拒絕而反覆失敗"
    source: "openapi.json PUT description；本站決定 D-3"

  - id: BR72.9
    statement: "產物 backend/mcp_bridge/generated_tools.json 進版控；漂移檢查在 CI 的 backend job；產生腳本讀取的輸入集合封閉為 openapi.json 與 allowlist.json，輸出為 generated_tools.json"
    category: constraint
    applies_to: backend/scripts/gen_mcp_tools.py
    trigger: CI、開發者重產
    logic: >
      gen_mcp_tools.py 讀 repo 根目錄的 openapi.json 與 backend/mcp_bridge/allowlist.json，呼叫 generate_tools，寫出
      generated_tools.json（排序鍵、固定縮排、結尾換行）。--check 模式重產並逐位元比對，不同即 exit 1。
      runtime 為 Python，故落在 backend job（cicd-pipeline.md:337 第 22 項「若以 python 實作則入 backend job」），
      緊鄰 ci.yml:289 的 dump_openapi.py --check，兩者互不排序（cicd-pipeline.md 第 23 項）。
      **讀取的輸入集合是封閉的**：作為 generate_tools 輸入而讀取的檔案恰為 openapi.json 與 allowlist.json；
      generated_tools.json 是**輸出**——寫出模式以寫入開啟它，--check 模式以讀取開啟它僅為與重產結果逐位元比對，
      其內容不回流成產生器的輸入。腳本在任何模式下都不得開啟 repo 根目錄的 .mcp.json 或任何其他 MCP 設定檔。
      測試落實 X-04 的 scope_exclusion：攔截腳本兩種模式下開啟的全部路徑，斷言 (a) 讀取開啟的路徑 ⊆
      {openapi.json, allowlist.json, generated_tools.json}，(b) generated_tools.json 只在 --check 模式被讀取，
      (c) .mcp.json 從未被開啟，(d) 傳入 generate_tools 的兩個引數分別由 openapi.json 與 allowlist.json 解析而來。
    violation_behaviour: "openapi.json 改了而產物未重產 → 工具與 API 不一致，而 dump_openapi --check 看不到（cicd-pipeline.md:341-344）"
    source: "[I7]=A；cicd-pipeline.md:337-344；X-04 scope_exclusion（contract-summary.md:2070-2073）"

  - id: BR72.10
    statement: "requires_agent 與 operation 綁定：method 不是 GET、或該項有任何 inject 時，requires_agent 必須為 true，否則產生失敗；啟動時重驗"
    category: validation
    applies_to: generate_tools、validate_tool_specs（BR71.5）
    trigger: 產生工具宣告、bridge 啟動
    logic: >
      requires_agent 是 allowlist.json 內手寫的布林值，本規則把它從「人記得填對」改成「機械不變量」：
      (method != "GET" or entry.inject 非空) and not entry.requires_agent → GeneratorError("agent_requirement_mismatch")。
      反方向（GET 且無 inject 卻設 true）允許：那只是更嚴，不會讓寫入少帶溯源。ToolSpec 保留 requires_agent 欄位，
      validate_tool_specs 在啟動時對載入的 generated_tools.json 重跑同一檢查（防止有人手改產物繞過產生器），失敗 → exit(1)。
    violation_behaviour: "寫入類 operation 被誤設為 false → BR74.3 的宣告檢查被略過，寫入不帶 on_behalf_of，空值會被 backend 當成使用者本人清空（U20 交接，code-summary.md:147-149）"
    source: "審查 review-01 R-05；BR74.3；requirement-field-service code-summary.md:147-149"

  - id: BR72.11
    statement: "allowlist 的 path 必須落在路徑前綴白名單內；第一版前綴白名單只有 /api/requirements/，成員管理類（/api/membership/）結構上無法進入 allowlist"
    category: validation
    applies_to: generate_tools、validate_tool_specs（BR71.5）
    trigger: 產生工具宣告、bridge 啟動
    logic: >
      generator.py 內以常數 ALLOWED_PATH_PREFIXES = ("/api/requirements/",) 宣告；entry.path 不以其中任一前綴開頭 →
      GeneratorError("path_outside_scope")。這是 [MB4]=A「成員管理類不開放」與 Allowlist 不變量的落實機制——U19 的成員
      端點皆在 /api/membership/ 之下（openapi.json:4669、:4776、:4917、:4945），故即使有人把它們寫進 allowlist.json，
      產生與啟動都會失敗。擴充前綴是**修改程式常數**而非修改設定檔，使開放新的端點家族必然經過程式碼審查，
      且須先補 ADR-0004 的高風險工具核准流程（問題檔 MB4 選項 B 的前提）。
    violation_behaviour: "只靠敘述「不含成員管理類」 → allowlist.json 的一行 PR 就能讓 agent 以使用者身分邀請、移出成員或改角色"
    source: "[MB4]=A；審查 review-01 R-05；ADR-0004（高風險工具需核准）；openapi.json:4669、:4776"

  # ---- BR73：使用者 token 的轉遞 ----------------------------------------------
  - id: BR73.1
    statement: "token 的唯一來源是該次 MCP HTTP 請求的 Authorization 標頭；缺漏或格式不符 → unauthenticated，且不呼叫 backend"
    category: authorization
    applies_to: tools/call
    trigger: 每次工具呼叫
    logic: >
      格式：^Bearer [A-Za-z0-9._~+/=-]+$，長度上限 8192 位元組。缺漏、多個值、空 token、超長 → unauthenticated（BR76.1）。
      **必須在 bridge 本地擋**：FastAPI 0.111.0（backend/requirements.txt:8）的 HTTPBearer 對缺漏標頭回 **403** "Not authenticated"
      （fastapi/security/http.py 的 HTTPBearer.__call__），若轉給 backend 會被映射成 forbidden，與真正的授權拒絕不可區分。
      initialize 與 tools/list 不要求 Authorization（只回公開的工具宣告）；認證檢查只在 tools/call。
    violation_behaviour: "缺 token 也轉發 → agent 看到『無權限』而非『未認證』，誤導使用者去申請權限"
    source: "[MB2]=A；backend/services/auth.py:35、:87-91；本站實測 FastAPI 0.111.0 行為"

  - id: BR73.2
    statement: "Authorization 標頭值原樣轉給 backend；除 Authorization、Content-Type、Accept 外，不轉送任何呼叫端標頭"
    category: constraint
    applies_to: 對 backend 的 HTTP 請求
    trigger: 每次工具呼叫
    logic: >
      bridge 不改寫、不重組 token；X-Cloud360-Agent（BR74.1）不轉給 backend——代寫標示改以本體的 on_behalf_of 表達（BR74.4）。
      對 backend 的請求只指向啟動參數給定的固定 base URL（BR71.1），follow_redirects=False，使 token 不會被帶往重導目標。
    violation_behaviour: "跟隨重導 → token 被送往非 backend 的位址"
    source: "[MB2]=A；FR11.6"

  - id: BR73.3
    statement: "token 只存在於該次請求的 contextvar；不得存於模組變數、快取、session 或 HTTP client 的預設標頭／cookie jar"
    category: constraint
    applies_to: 執行期狀態
    trigger: 每次工具呼叫
    logic: >
      ASGI middleware 在請求進入時把 Authorization 與 X-Cloud360-Agent 取出放入 contextvar RequestCredential，請求結束（含例外）於
      finally 重設。工具處理函式只從 contextvar 讀。共用的 httpx.AsyncClient 不設 auth／預設 Authorization 標頭；
      每次呼叫以該次請求的 headers 參數帶入；client 以不持久 cookie 的設定建立（每次回應後清空 cookies）。
      生命週期等於一次 MCP HTTP 請求；token 的有效期仍由 backend 決定（8 小時，auth.py:33）。
    violation_behaviour: "token 留在跨請求狀態 → 下一個使用者的工具呼叫以前一位使用者身分執行"
    source: "[MB2]=A（問題檔 MB2 選項 A：用完即棄、不儲存）；OQ-15（requirements.md:796）的『如何隨使用者切換』"

  - id: BR73.4
    statement: "token 不得出現在 log、工具參數、工具結果、錯誤訊息或例外文字中"
    category: constraint
    applies_to: 全部輸出面
    trigger: 恆成立
    logic: >
      工具結果只含 backend 200 回應的 JSON 本體（BR76.4）；錯誤訊息只用 BR76.1 的固定文字或經 BR76.2 過濾的 backend detail；
      log 欄位白名單見 BR77.1。httpx 例外一律不 str() 進任何輸出（其 repr 可能含請求物件）。
    violation_behaviour: "token 進工具結果 → 同樣進入 LLM context（C-T11 的不可逆面）"
    source: "FR11.5；X-04 why_irreversible；[MB2]=A"

  - id: BR73.5
    statement: "bridge 不解碼 JWT、不判斷身分；使用者是誰只由 backend 決定"
    category: constraint
    applies_to: 身分
    trigger: 恆成立
    logic: >
      bridge 不持有 JWT_SECRET（零 secret，infrastructure-specification.md 7.1），也不做未驗證的解碼取 sub——
      未驗證的 sub 寫進 log 會讓偽造 token 的人決定 log 內容。
    violation_behaviour: "bridge 讀 JWT 內容做判斷 → 出現第二個身分來源，與 backend 不一致時無從裁決"
    source: "infrastructure-specification.md 7.1『新部署變數／secret：零』；ADR-0006 IAM"

  # ---- BR74：agent 身分（[MB3]=A） ---------------------------------------------
  - id: BR74.1
    statement: "agent 身分以每次 MCP HTTP 請求的 X-Cloud360-Agent 標頭宣告，不用 MCP initialize 的 clientInfo"
    category: constraint
    applies_to: 連線層
    trigger: 每次工具呼叫
    logic: >
      值為 agents.json 的鍵（小寫英數與連字號，長度 ≤ 64）。選標頭而非 clientInfo 的理由：(1) 無狀態傳輸（BR71.2）下沒有
      跨請求的 session 可把 initialize 時的 clientInfo 綁到後續 tools/call；(2) 與 token 同層、同生命週期，避免「session 層的 agent ＋
      請求層的使用者」兩種生命週期混搭；(3) clientInfo 在 MCP 規格中描述的是 client 的**實作**（名稱與版本），不是代誰行事。
    violation_behaviour: "用 clientInfo 並保存 session → 需伺服器端狀態，違反 BR71.2；且同一 client 實作服務多個 agent 時無法區分"
    source: "[MB3]=A；本站決定 D-1"

  - id: BR74.2
    statement: "agents.json 是已宣告代寫組的白名單：agent 名 → on_behalf_of 值；值必須 ⊆ U20 宣告的代寫組集合，由測試鎖住"
    category: validation
    applies_to: backend/mcp_bridge/agents.json
    trigger: 啟動（BR71.5）與 CI
    logic: >
      第一版：{"cost": "cost", "architecture": "architecture"}——與 requirement_field_definitions.py:69、:81 的兩個 group_key 對應。
      這是跨進程的第二份物化（正本為 GROUPS_BY_KEY，requirement_field_definitions.py:119），依 team.md「單一真實來源」，同一個 PR 必須
      新增一支測試斷言 set(agents.json 的值) ⊆ set(GROUPS_BY_KEY)。bridge 執行期不 import 該模組（避免把 backend 的服務層拉進
      bridge 進程）；一致性由測試與 facade 的再驗證（U20 的規則：未知代寫組 → 422）雙重保證。
    violation_behaviour: "登錄一個 backend 不認得的組 → 每次寫入 422；或刪了 backend 的組而登錄未改 → 同上，但 CI 已先紅燈"
    source: "[MB3]=A；requirement_field_facade.py:352-356；team.md Code Style 單一真實來源"

  - id: BR74.3
    statement: "寫入與清空工具要求已登錄的 agent 宣告，否則 agent_not_declared 且不呼叫 backend；讀取工具不要求"
    category: authorization
    applies_to: write_requirement_field、clear_requirement_field
    trigger: tools/call
    logic: >
      缺標頭或值不在 agents.json → agent_not_declared（BR76.1）。檢查順序：BR73.1（token）→ BR74.3（agent）→ BR75.4（參數）→ 呼叫 backend。
      讀取不改變狀態、也沒有代寫標示可填，故不要求；log 記 agent=undeclared（BR77.1）。
      **這不是授權**：它只決定代寫標示填什麼，授權完全在 backend（BR75.1）。
      「哪些工具要求宣告」由 ToolSpec.requires_agent 決定，而它與 method／inject 的綁定由 BR72.10 機械保證，不依賴人填對。
    violation_behaviour: "未宣告也放行寫入 → 寫入不帶 on_behalf_of，空值會被 backend 當成使用者清空並記為本人清空（U20 交接，code-summary.md:147-149）"
    source: "requirement-field-service code-summary.md:147-149；[MB3]=A"

  - id: BR74.4
    statement: "寫入時 bridge 以登錄的代寫組填入本體的 on_behalf_of；工具參數無法影響它"
    category: constraint
    applies_to: write_requirement_field
    trigger: tools/call
    logic: >
      對 backend 的本體恆為 {"value": <value>, "on_behalf_of": agents[agent]}。工具 schema 不含 on_behalf_of（BR72.4）且
      additionalProperties: false；BR75.4 另在 bridge 端拒絕任何未宣告的參數，不依賴 client 遵守 schema。
      清空工具走 DELETE，本體為空——backend 的 clear_field 沒有 on_behalf_of 參數（contract-summary.md:1835），
      故清空的代寫溯源只留在 bridge 的 log（BR77.4，OPEN-MB21-4）。
    violation_behaviour: "接受參數裡的 on_behalf_of → agent 冒充別的 agent"
    source: "[MB3]=A；X-04（contract-summary.md:2083-2084）；requirement-field-service code-summary.md:147-150"

  - id: BR74.5
    statement: "agent 宣告是 client 自報、真偽無法驗證；揭露為已知限制，與 U20 的 OPEN-RF20-1 合併追蹤"
    category: constraint
    applies_to: 身分模型
    trigger: 恆成立
    logic: >
      能送出 X-Cloud360-Agent 的任何呼叫端都能宣稱自己是任一已登錄 agent。殘留影響僅限**溯源標示**：授權不受影響
      （代寫標示不授予任何權限，openapi.json 的 on_behalf_of 描述逐字「只是標示，不授予任何權限」），且呼叫仍需使用者本人的 token。
      收緊手段（每個 agent 一組可驗證的憑證）屬新 IAM 面，需新 ADR（問題檔 MB3 選項 B 未採）。
    violation_behaviour: "把代寫標示當成『確實是某 agent 寫的』的證據 → 稽核結論錯誤"
    source: "[MB3]=A（問題檔 MB3 選項 A 的揭露）；requirement-field-service functional-spec.md:198（OPEN-RF20-1）"

  - id: BR74.6
    statement: "寫入工具的 value 去除首尾空白後為空 → invalid_argument（提示改用清空工具），不呼叫 backend"
    category: validation
    applies_to: write_requirement_field
    trigger: tools/call
    logic: >
      backend 對帶 on_behalf_of 的空值本來就回 422（requirement_field_facade.py:360-365），本規則在 bridge 端提前擋下並給出可行動的訊息
      「value 不得為空；要清空欄位請用 clear_requirement_field」。這是 U20 交接「在工具 schema 層直接拒絕空值」的落點；
      schema 本身另加 minLength: 1，但 minLength 擋不住純空白，故仍需本規則。
    violation_behaviour: "只靠 backend 的 422 → agent 收到不具體的 invalid_argument，傾向重試同一個空值"
    source: "requirement-field-service code-summary.md:147-149；requirement_field_facade.py:360-365"

  # ---- BR75：授權與請求組裝 ---------------------------------------------------
  - id: BR75.1
    statement: "每次工具呼叫恰好對 backend 發一次 HTTP 請求，以使用者 token 執行；bridge 自己不做任何授權判定"
    category: authorization
    applies_to: tools/call
    trigger: 每次工具呼叫
    logic: >
      讀 → GET、寫 → PUT、清空 → DELETE，路徑與 allowlist 的 operation 相同。授權（待核准、K4 全域層、系統所屬、per-project 成員）全部由
      backend 的 RequirementFieldFacade 判定（requirement_field_facade.py:11-28 的四步順序）。bridge 的 BR73.1／BR74.3／BR75.4 是
      **前置格式與溯源檢查**，任一通過都不代表授權通過。不重試（PUT／DELETE 雖冪等，重試仍會讓一次工具呼叫在 backend log 出現多次）。
    violation_behaviour: "bridge 自行判定權限 → 出現第二份授權邏輯，與 facade 不一致時 agent 能做使用者不能做的事，或反之"
    source: "FR11.6（requirements.md:270-273）；X-04 behaviour_semantics.authorization_responsibility（contract-summary.md:2114-2117）"

  - id: BR75.2
    statement: "不依賴 router 的 require_story_action，也不做第二次全域檢查；以 facade 的實作為準"
    category: authorization
    applies_to: 授權模型
    trigger: 恆成立
    logic: >
      K-16 two_facade_layers.anti_double_check 字面寫「U20 不得重複呼叫 require_story_action（它的 router 已經做了）」
      （contract-summary.md:1639-1640），**與實作相反**：requirement_field_router.py 三條路由的 dependency 只有 get_current_user
      （:148、:171、:200），全域 K4 在 facade 內以 user_can 評估（requirement_field_facade.py:16-22）。U20 已記錄此偏離
      （code-summary.md:134-136）。本單元的安全性只依賴「facade 是唯一授權入口」這一個事實，不依賴 router 是否掛檢查；
      FR11.6 要求的「帶 token 使授權照常執行」以 get_current_user ＋ facade 成立。
    violation_behaviour: "照 K-16 字面以為 router 已檢查而在 bridge 補一道 → 兩份判定；或以為無需 token → 繞過"
    source: "contract-summary.md:1639-1640；requirement_field_router.py:21-22、:24-28、:148；requirement_field_facade.py:16-22；requirement-field-service code-summary.md:134-136"

  - id: BR75.3
    statement: "bridge 不直接呼叫 U19 的任何端點，也不呼叫 resolve_project_role；per-project 判定由 facade 在 backend 內完成"
    category: constraint
    applies_to: 依賴
    trigger: 恆成立
    logic: >
      K-16 的 resolve_project_role consumed_by 列有 U21（contract-summary.md:1659），本設計不呼叫它（[MB4]=A 不開成員工具；
      per-project 判定在 facade 第 4 步）。因此 components.md 的 McpBridge → ProjectMembership 這條邊**不成立**：
      per-project 判定是 RequirementRegistry 內部對 ProjectMembership 的依賴，對 bridge 而言只是**傳遞依賴**，不是直接邊。
      契約追認 C-5 的處置是**移除**該邊（McpBridge.depends_on 的 ProjectMembership 項、ProjectMembership.dependents 的
      McpBridge 項、Part B' 圖與文字中的對應敘述）並同步移除 K-16 consumed_by 與 consumers.separate_process 中的 U21——
      不是加註解保留它；保留的邊會讓下游讀 depends_on 時仍認定 bridge 直接依賴成員層。
      僅存的 McpBridge → RequirementRegistry 邊的 style: sync 指**經 HTTP 的同步請求回應**（bridge 是獨立進程，BR71.1）。
    violation_behaviour: "bridge 自行查成員 → 第二份 per-project 判定（ADR-012 的唯一入口被破壞）"
    source: "[MB4]=A；contract-summary.md:1622、:1659；components.md:567-568、:664-666、:775、:788、:809、:811；審查 review-01 R-07"

  - id: BR75.4
    statement: "bridge 端依工具 schema 驗證參數；未宣告的參數、型別不符、system_id 非十進位整數字串、或 agent_group／field 不符字元集白名單 → invalid_argument；路徑只由通過白名單的段組成"
    category: validation
    applies_to: tools/call
    trigger: tools/call
    logic: >
      不依賴 client 遵守 inputSchema。參數鍵集合必須 ⊆ 宣告集合，且 required 全在；型別皆為 string。
      system_id 必須符合 ^[0-9]{1,18}$（backend 以字串接收、facade 收斂為 int，非整數在授權**之後**判 404——bridge 提前擋可避免
      對 backend 發出必然 404 的請求；這是格式檢查，不改變授權順序，因為格式錯的請求在 backend 也不會進到存取）。
      **agent_group 與 field 必須符合 ^[a-z0-9_]{1,64}$**——與 U20 的鍵格式正本 KEY_PATTERN（requirement_field_definitions.py:33）
      逐字相同；因此純句點段（"."、".."）、"/"、"%"、"?"、"#"、空白與任何非 ASCII 字元一律 invalid_argument，且不呼叫 backend。
      **百分比編碼不是安全保證**：urllib.parse.quote 不編碼句點，而 httpx 建立請求時會對路徑做 dot-segment 正規化——審查
      review-01 以 httpx 0.28.1 實測，agent_group 為 ".." 時請求被送往 /api/requirements/systems/1/x，field 為 ".." 時被送往
      /api/requirements/systems/1/fields。故安全性來自白名單（只有不可能構成 dot-segment 或分隔符的字元能進入路徑），
      組路徑時仍以 quote(s, safe="") 編碼作為縱深防禦，但不依賴它。
      這個樣式是跨進程的第二份物化（bridge 不 import backend 的服務層，BR74.2），依 team.md「單一真實來源」，同一個 PR 必須
      新增測試斷言 bridge 的樣式字串等於 KEY_PATTERN.pattern。allowlist 以 property_patterns 為 agent_group 與 field 宣告
      同一樣式，產生器把它寫進 inputSchema 的 pattern，讓 client 端也看得到約束（bridge 端的驗證仍以 calls.py 的常數為準，
      測試另斷言 allowlist 宣告的樣式與該常數相等）；不採 enum（把七個欄位鍵寫進 schema 會成為鍵集合在 backend 之外的另一份物化，
      且每次 U20 新增欄位都要重產並追認）。
      rename 的反向映射（field → field_key）在此執行。
      驗證標準（functional-spec.md §六 性質六）：以執行層實際使用的 httpx client.build_request 組出的請求 URL 為判準，
      不以 build_backend_call 回傳的計畫字串為判準。
    violation_behaviour: "只靠百分比編碼 → agent_group 或 field 為 '..' 時請求被正規化到 allowlist 以外的路徑，以使用者身分執行 PUT 或 DELETE"
    source: "requirement_field_router.py:36-37（字串接收、授權後判 404）；requirement_field_definitions.py:33（KEY_PATTERN）；審查 review-01 R-01 的 httpx 0.28.1 實測；本站決定 D-4"

  # ---- BR76：錯誤映射（封閉表） -------------------------------------------------
  - id: BR76.1
    statement: "工具呼叫的結果只有成功與七種錯誤碼，以封閉表映射，不得新增未登錄的分支"
    category: constraint
    applies_to: map_outcome（純函式）
    trigger: 每次工具呼叫結束
    logic: >
      | 情形 | 錯誤碼 | 訊息 | retryable |
      | Authorization 缺漏或格式不符（BR73.1，本地） | unauthenticated | 固定：「需要使用者登入憑證」 | false |
      | backend 401 | unauthenticated | 固定：「使用者憑證無效或已過期」 | false |
      | 未宣告或未登錄的 agent（BR74.3，本地） | agent_not_declared | 固定：「呼叫端未宣告已登錄的 agent 身分」 | false |
      | 參數不合格（BR75.4、BR74.6，本地） | invalid_argument | 固定，指出參數名，不回顯值 | false |
      | backend 403 | forbidden | BR76.2 | false |
      | backend 404 | not_found | BR76.2 | false |
      | backend 422 | invalid_argument | BR76.2 | false |
      | 連線拒絕、逾時、DNS 失敗、backend 5xx | backend_unavailable | 固定：「後端暫時無法使用」 | true |
      | 其他狀態碼、200 但本體非 JSON、bridge 內部未預期例外 | internal_error | 固定：「轉接層內部錯誤」 | false |
      逾時：連線 3 秒、整體 10 秒。
    violation_behaviour: "未登錄的分支回傳例外原文 → 可能洩漏內部位址、堆疊或請求物件"
    source: "問題檔 brief 的封閉表要求；construction.md Error Handling；U13 的規則 67.1 的同形先例"

  - id: BR76.2
    statement: "403／404／422 時，backend 的 detail 只在本體恰為 {detail: string} 且通過過濾時原樣轉給 agent；否則用固定文字"
    category: constraint
    applies_to: map_outcome
    trigger: backend 403／404／422
    logic: >
      過濾：本體為 JSON object、鍵集合恰為 {"detail"}、值為字串、長度 ≤ 200、不含控制字元。通過 → message = detail。
      否則 → 固定文字（forbidden「沒有存取此資源的權限」、not_found「找不到指定的資源」、invalid_argument「參數不被接受」）。
      依據：openapi 的 RequirementFieldErrorOut 描述逐字「detail 為固定文字，不含任何輸入值」（openapi.json:1370），
      故原樣轉送不回顯輸入；而 AC11.4.1 要求「理由與我直接存取時相同」，原樣轉送正是讓兩者相同的方式。
    violation_behaviour: "一律改寫成 bridge 的固定文字 → AC11.4.1 的『理由相同』不成立；不過濾就轉送 → 未來的 FastAPI 預設 422 會回顯輸入值"
    source: "AC11.4.1（stories.md:727）；openapi.json:1369-1382；requirement_field_router.py:138"

  - id: BR76.3
    statement: "錯誤以 MCP 工具結果的 isError: true 回傳，內容為 JSON {error, message, retryable}；不以 JSON-RPC 協定錯誤回傳"
    category: constraint
    applies_to: tools/call 回應
    trigger: 任一錯誤
    logic: >
      協定錯誤（JSON-RPC error）保留給 MCP 層本身的錯誤（未知工具、格式錯誤的 JSON-RPC）。工具執行層的錯誤讓 agent 讀得到並決策。
      bridge 端例外的 str()／repr() 一律不進入 message。
    violation_behaviour: "以協定錯誤回傳 → 多數 client 會把它當成連線問題而非可處理的業務拒絕"
    source: "本站決定 D-5；FR11.6"

  - id: BR76.4
    statement: "成功時工具結果為 backend 200 回應本體的 JSON（read 為 FieldSetView、write／clear 為 FieldView），不加任何欄位"
    category: constraint
    applies_to: tools/call 回應
    trigger: backend 200
    logic: >
      以 structured content 回傳該 JSON，並附一段同內容的文字（相容不讀 structured content 的 client）。不附請求標頭、不附 agent 宣告。
      FieldView 的欄位見 requirement_field_types.py:40-56（含 updated_by 使用者 id 與 updated_on_behalf_of 代寫組，皆非憑證）。
    violation_behaviour: "附上請求資訊 → token 有機會進入結果"
    source: "X-04 tools.returns（contract-summary.md:2076-2085）；requirement_field_types.py:40-56"

  # ---- BR77：log 與稽核 ---------------------------------------------------------
  - id: BR77.1
    statement: "logger cloud360.mcp_bridge；每次 tools/call 一行 INFO，欄位白名單：tool、agent、outcome、http_status、duration_ms"
    category: constraint
    applies_to: log
    trigger: 每次工具呼叫結束
    logic: >
      agent 取值：已登錄名、"undeclared"（缺標頭）或 "unregistered"（有標頭但不在 agents.json；**不寫原值**，防 log 注入）。
      outcome 為 ok 或 BR76.1 的錯誤碼；http_status 為 backend 狀態碼或 null（本地拒絕或連線失敗）。
      logger 命名依 team.md「新模組一律 cloud360.<module>」。啟動、BR71.5 的失敗另各一行。
    violation_behaviour: "記錄 agent 原值 → 呼叫端可寫入任意字串到 log"
    source: "team.md Code Style（logger 命名）；本站決定 D-7"

  - id: BR77.2
    statement: "log 禁含：Authorization 與 token、工具參數（含 system_id 與欄位值）、backend 回應本體、例外文字"
    category: constraint
    applies_to: log
    trigger: 恆成立
    logic: >
      httpx 與 mcp SDK 的 logger 層級設為 WARNING 以上（httpx 在 INFO 會記錄請求 URL，URL 含 system_id 等參數）。
      未預期例外只記例外**型別名稱**，不記訊息與堆疊中的區域變數。
    violation_behaviour: "記參數或本體 → 需求欄位內容（使用者的架構資訊）外流到容器 log"
    source: "team.md Forbidden（不得把敏感資料寫進任何 log）；FR11.5"

  - id: BR77.3
    statement: "稽核主體是使用者本人：由 token 轉遞自然達成，持久稽核以 backend 的欄位與 log 為準，bridge 的 log 為補充"
    category: constraint
    applies_to: 稽核
    trigger: 恆成立
    logic: >
      寫入與清空的 updated_by 由 facade 取自已驗證的 principal（使用者 id），寫入另記 updated_on_behalf_of；facade 的 _log_change 記
      user_id 與 on_behalf（requirement_field_facade.py:444-464）。bridge 沒有服務帳號、不持有任何身分，故不可能以 bridge 身分出現在稽核中。
      bridge log 與 backend log 之間沒有關聯鍵（OPEN-MB21-9），只能依時間對照。
      **成功的讀取沒有任何帶使用者身分的紀錄**：facade 只對**被拒**的讀取記一行帶 user_id 的 WARNING
      （requirement_field_facade.py:272-276），成功的 read_fields（:301-305）不記錄（既有行為，非本單元引入），而 bridge 刻意不解碼
      JWT（BR73.5），其 log 只有 tool／agent／outcome（BR77.1），故 agent 經 MCP 讀了哪位使用者可見的哪個系統的欄位，
      事後無從得知主體。requirements.md:620 要求的「稽核主體為使用者本人」在寫入與清空成立、在讀取**不成立**——揭露為
      OPEN-MB21-14，於本站核可關卡呈現；本單元不自行補（補法需 backend 記讀取，或 bridge 取得已驗證的身分，兩者皆越出本單元）。
    violation_behaviour: "以服務帳號呼叫 backend → 稽核主體變成大腦服務帳號（requirements.md:620 明文禁止）"
    source: "requirements.md:620；X-04 audit_subject（contract-summary.md:2091）；requirement_field_facade.py:272-276、:301-305、:444-464；審查 review-01 R-08"

  - id: BR77.4
    statement: "agent 清空欄位時，持久列只記使用者為清空者，代寫溯源只在 bridge log；揭露為缺口"
    category: constraint
    applies_to: clear_requirement_field
    trigger: tools/call
    logic: >
      K-17 的 clear_field 不收 on_behalf_of（contract-summary.md:1835），DELETE 無本體。bridge 不得以「改用空值 PUT」繞過——
      U20 交接逐字「要清空用 DELETE／clear_field，不要以空值 PUT」（code-summary.md:150），且空值 PUT 帶 on_behalf_of 會被 422。
      收斂需要 K-17 增量（clear_field 增 on_behalf_of），列為 OPEN-MB21-4。
    violation_behaviour: "為了留溯源改走空值 PUT → 違反 U20 交接且必 422"
    source: "contract-summary.md:1834-1840；requirement-field-service code-summary.md:150"

  # ---- BR78：最小測試 client 與驗證拓樸（[MB1]=A） ---------------------------------
  - id: BR78.1
    statement: "本單元交付一支最小測試 client：以官方 SDK 的 streamable HTTP client 連 /mcp，帶 Authorization 與 X-Cloud360-Agent，提供 list_tools 與 call_tool 兩個操作"
    category: constraint
    applies_to: backend/tests 下的測試輔助
    trigger: 測試
    logic: >
      只存在於 backend/tests/（不進 bridge 的執行期程式、不是產品元件）。它扮演「agent 側的 MCP client」，用來以真實 HTTP 驗證
      AC11.4.1–AC11.4.3。大腦側 client（讓 U11／U12 的 agent 真的取用欄位）不在本單元，列 OPEN-MB21-1。
    violation_behaviour: "把測試 client 放進產品程式 → 形成一個無人擁有、無授權設計的呼叫端"
    source: "[MB1]=A"

  - id: BR78.2
    statement: "驗證拓樸：bridge 以 uvicorn 啟在 127.0.0.1 的隨機埠；bridge 對 backend 的呼叫經 httpx.ASGITransport 直達真實的 FastAPI app（SQLite 測試資料庫）"
    category: constraint
    applies_to: 整合測試
    trigger: 測試
    logic: >
      client → bridge 走真實 HTTP（覆蓋傳輸層與標頭取得）；bridge → backend 走真實 FastAPI 路由、get_current_user、facade 授權
      （覆蓋 FR11.6 的授權照常執行），只把 TCP 換成 ASGI 傳輸以免在 CI 起資料庫與第二個服務。測試資料庫沿用 backend/tests/helpers.py。
      不把 bridge 加進 deploy/docker-compose.test.yml（cicd-pipeline.md 第 26 項）。
      AC11.4.1 的「理由相同」以同一個 token 直接呼叫 backend GET 的 detail 與工具結果的 message 比對相等來斷言。
      bridge 應用一律經 BR78.3 的 create_app 建立：測試傳入以 httpx.ASGITransport(app=backend 的 FastAPI app) 建立的
      backend_client，正式啟動傳入以 TCP 連 --backend-url 的 backend_client，其餘組裝路徑完全相同。
      前提：bridge 與 backend 在同一個 Python 直譯器內可同時 import（同一份 site-packages）。若 A-2 走第二退路
      （mcp 裝在獨立的 virtualenv，functional-spec.md §十二 第 1 步），此前提不成立，拓樸改為「bridge 以子進程跑在
      該 venv、backend 以 uvicorn 起在 127.0.0.1 隨機埠」，斷言不變；此變更由 code-generation 記錄（OPEN-MB21-15）。
    violation_behaviour: "以 mock 取代 backend → allow／deny 驗的是 mock，不是 facade"
    source: "[MB1]=A；cicd-pipeline.md:351（第 26 項）；team.md Testing Posture（TestClient 與 helpers）"

  - id: BR78.3
    statement: "bridge 的 ASGI 應用只有一個組裝點 create_app(backend_client, registry, tool_specs)；正式啟動與全部測試都經它建立"
    category: constraint
    applies_to: backend/mcp_bridge/app.py
    trigger: 啟動、測試
    logic: >
      create_app(*, backend_client: httpx.AsyncClient, registry: AgentRegistry, tool_specs: tuple[ToolSpec, ...],
      allowed_hosts: tuple[str, ...]) -> ASGI 應用。它負責：掛 /healthz 與 /mcp（無狀態 streamable HTTP）、掛 credential
      middleware（BR73.3）、以 tool_specs 註冊工具處理函式、把 backend_client 交給執行層、設定 Host 允許清單（BR71.6）。
      它**不**讀檔、不解析命令列、不建立 backend_client、不設定 logging——那些屬 __main__（MB-W1），使測試能注入
      ASGITransport 與自訂登錄表而不另走一條組裝路徑。執行層送出請求一律為 backend_client.build_request(...) 後
      backend_client.send(...)，使 BR75.4 的驗證（以 build_request 的結果為判準）與正式路徑同形。
      logging 設定以 configure_logging() 單獨提供，正式啟動與 BR78.5 的測試呼叫同一支。
    violation_behaviour: "測試自行組一個與正式啟動不同的 app → middleware、工具註冊或 client 設定的差異只在正式環境出現"
    source: "審查 review-01 R-10；BR78.2"

  - id: BR78.4
    statement: "必測（身分隔離）：兩個以上並發 client 帶不同使用者 token 交錯呼叫，backend 端每個請求收到的 Authorization 必須等於發起該工具呼叫的 client 的 token"
    category: validation
    applies_to: backend/tests 的整合測試
    trigger: 測試
    logic: >
      驗的是 BR73.3：無狀態 streamable HTTP 下 SDK 可能在另一個 task 內執行工具處理函式（OPEN-MB21-7 的未實測項），
      contextvar 是否確實隨請求傳遞，只有並發交錯能證明。做法：使用者 A、B 各擁有一個系統（system_id 不同）；
      以 asyncio.gather 讓 A、B 兩個 client 各發 ≥ 20 次 read_requirement_fields（各讀自己的系統），交錯排程；
      在 backend app 外包一層只記錄 (path, Authorization) 的 ASGI 包裝。斷言：(1) 每一筆紀錄的 Authorization 等於
      其 path 中 system_id 擁有者的 token；(2) 全部工具結果皆非 isError；(3) 紀錄筆數等於工具呼叫次數。
      再加一個寫入變體（A、B 交錯 write_requirement_field），斷言持久列的 updated_by 為各自的使用者 id。
      突變驗證：把 token 改存模組層變數 → 本測試紅燈。
    violation_behaviour: "未驗證 → contextvar 在 SDK 的 task 邊界遺失或串號時，下一位使用者以前一位的身分執行，而單一 client 的測試全綠"
    source: "審查 review-01 R-02；BR73.3；OPEN-MB21-7"

  - id: BR78.5
    statement: "必測（不外洩）：BR76.1 每一列錯誤分支與成功分支，工具結果的全文與 bridge 進程內全部 logger 的輸出都不含 token 子字串與 Authorization 值"
    category: validation
    applies_to: backend/tests 的整合測試
    trigger: 測試
    logic: >
      驗的是 BR73.4 與 BR77.2。token 為測試以 backend 的簽發函式（auth.py:47 的 create_access_token）產生的有效 JWT；比對用的「秘密子字串」取完整 token 與其第三段（簽章段，長度數十字元且由內容決定，不會偶然出現在其他文字中）。
      以正式啟動相同的 configure_logging()（BR78.3）設定層級，在根 logger 掛一個收集 handler、**不調整任何 logger 的層級**，
      收集 cloud360.mcp_bridge、httpx、mcp 與其餘全部紀錄的格式化結果。逐分支觸發：本地 unauthenticated（缺標頭、格式錯）、
      backend 401（把有效 token 的簽章段改掉一字元，比對時改用這個被改過的 token）、agent_not_declared、本地 invalid_argument（多餘參數、".."、純空白 value）、
      forbidden、not_found、backend 422、backend_unavailable（以拋出 httpx.ConnectError 的傳輸取代、及包裝層回 503）、
      internal_error（包裝層回 418、回非 JSON 的 200）、成功的讀與寫。每一分支斷言：工具結果序列化後的全文（含 structured
      content 與文字內容）與收集到的全部 log 文字，皆不含完整 token、不含其簽章段、不含 "Bearer " 加 token。
      突變驗證：message 改用 str(exc) → internal_error／backend_unavailable 分支紅燈；log 加入參數或標頭 → 紅燈。
    violation_behaviour: "只有 schema 面斷言（AC11.4.2）→ token 經錯誤訊息或 log 外流時沒有任何測試紅燈"
    source: "審查 review-01 R-02；BR73.4；BR77.2；FR11.5"
```

## 三、規則摘要

| 群 | 規則 | 一句話 |
|---|---|---|
| 進程與傳輸 | `BR71.1`–`BR71.6` | 獨立進程、沿用映像、零環境變數；streamable HTTP 無狀態於 `/mcp`；`/healthz` 免認證；啟動不依賴 backend；設定錯誤即退出；Host 允許清單 |
| 產生器 | `BR72.1`–`BR72.11` | 純函式、決定性、檢查順序固定；allowlist 預設拒絕且三項；不產生憑證參數；剝除並注入 `on_behalf_of`；`field_key` 改名為 `field`（`[MB6]`=A）；白名單相等；黑名單子字串底線；名稱描述取自 allowlist；產物進版控、漂移閘門在 backend job、讀取輸入封閉；`requires_agent` 與 method／inject 綁定；路徑前綴白名單 |
| token 轉遞 | `BR73.1`–`BR73.5` | 只取請求標頭、本地擋缺漏；原樣轉送、不跟隨重導；只在 contextvar；不進任何輸出；不解碼 |
| agent 身分 | `BR74.1`–`BR74.6` | 請求標頭宣告；登錄表鎖在代寫組集合內；寫與清空必須宣告；bridge 填 `on_behalf_of`；自報限制揭露；空值寫入本地擋 |
| 授權 | `BR75.1`–`BR75.4` | 一次呼叫一次請求、不自行授權；以 facade 實作為準；不呼叫成員層（移除該邊）；參數驗證與路徑段字元集白名單 |
| 錯誤 | `BR76.1`–`BR76.4` | 封閉表；403／404／422 過濾後轉送 detail；`isError` 結果；成功即 backend 本體 |
| log 與稽核 | `BR77.1`–`BR77.4` | 欄位白名單；禁止項；主體是使用者（讀取無主體紀錄，揭露）；清空的溯源缺口 |
| 測試 client 與必測 | `BR78.1`–`BR78.5` | 最小 client 只在測試；真實 HTTP ＋ 真實 FastAPI 的驗證拓樸；唯一組裝點 `create_app`；並發身分隔離必測；逐分支不外洩必測 |
