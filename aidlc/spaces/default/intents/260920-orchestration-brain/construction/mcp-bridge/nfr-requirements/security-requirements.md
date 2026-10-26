# 安全需求 — `U21 mcp-bridge`

> `NFR21` 的 parent id 理由、「驗證拓樸」與「記錄包裝」的定義見 `performance-requirements.md` 檔頭。本檔把 `functional-spec.md`
> §十二 的必測清單 `T-1`–`T-8`（`:352-359`）與帶入項中的安全相關者轉成可二元判定的需求；**不重開設計**——規則內容以
> `rules.md` 為準，本檔只寫「怎樣才算做到」。

## 〇、上游依據

| 依據 | 內容 |
|---|---|
| 本單元 functional-design | `BR71.1`–`BR71.6` 進程與傳輸、`BR72.1`–`BR72.11` 產生器、`BR73.1`–`BR73.5` token 轉遞、`BR74.1`–`BR74.6` agent 身分、`BR75.1`–`BR75.4` 授權與請求組裝、`BR76.1`–`BR76.4` 錯誤、`BR77.1`–`BR77.4` log 與稽核、`BR78.1`–`BR78.5` 驗證拓樸與必測；`functional-spec.md` §六（`:173`）ADR-0006 四面向 |
| `requirements.md:617-620` | 修訂 1 的 ADR-0006 判定表（FR11／FR12／FR13）：四面向皆「適用」 |
| `FR11.5`／`FR11.6`、`AC11.4.1`–`AC11.4.3` | token 不得進工具參數；每次以使用者身分呼叫既有 API |
| `X-04`（`contract-summary.md:2049` 起） | 憑證白名單、黑名單底線、排除 `.mcp.json`、稽核主體為使用者本人 |
| `team.md` 測試底線 A／B | 授權須 allow／deny 雙向；新增或修改 HTTP 端點需 `TestClient` 級測試。本單元**不新增 backend 端點**，新增的是獨立進程的 MCP 端點，其 allow／deny 以驗證拓樸經真實 facade 承載（`NFR21.12`） |
| `[G2]`=A、`[I6]`=A | 容器間明文、信任邊界為 compose network（`brain-infra` `nfr-design-questions.md:90`／`:103`）；`internal` 網段、無 `ports:` 滿足 `OQ-16` 的 Encryption 要求（`infrastructure-design-questions.md:299-303`） |
| `[MBN1]`=A | 成功讀取不新增帶使用者身分的紀錄（本站問題檔 `:74`） |

## 一、資料分類

| 資料 | 分類 | 落地 | 處置 |
|---|---|---|---|
| 使用者 JWT（`Authorization` 標頭，8 小時有效，`auth.py:33`） | **憑證** | 不落地；只在該次請求的 contextvar（`BR73.3`） | `NFR21.7`、`NFR21.8`、`NFR21.13`、`NFR21.14`、`NFR21.18` |
| agent 宣告（`X-Cloud360-Agent`） | 內部識別（自報、不可驗證，`BR74.5`） | 不落地；log 只記正規化值（`BR77.1`） | `NFR21.15`、`NFR21.34` |
| 工具參數（`system_id`、`agent_group`、`field`、`value`） | 內部（使用者的架構資訊） | 不落地；log 禁含（`BR77.2`） | `NFR21.8`、`NFR21.9` |
| backend 回應本體（`FieldSetView`／`FieldView`） | 內部 | 不落地；原樣成為工具結果（`BR76.4`） | `NFR21.8`、`NFR21.22` |
| `allowlist.json`、`generated_tools.json`、`agents.json` | 設定（進版控，公開 repo） | 映像內 | `NFR21.4`–`NFR21.6`、`NFR21.10` |

## 二、工具宣告面（憑證不進工具參數）

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR21.4`** | （`T-5`；`AC11.4.2`；`BR72.6`、`BR72.7`）載入的工具宣告恰為三個工具，每個工具 `inputSchema.properties` 的鍵集合**等於寫在測試檔內的字面期望集合**，且任何深度的屬性名都不以不分大小寫的子字串命中 `token`／`key`／`secret`／`authorization`；`additionalProperties` 為 `false` | 測試以字面值 `{"read_requirement_fields": {"system_id"}, "write_requirement_field": {"system_id","agent_group","field","value"}, "clear_requirement_field": {"system_id","agent_group","field"}}` 為期望，**不讀 `allowlist.json`**；以驗證拓樸的測試 client 呼叫 `tools/list` 取得實際宣告後比對相等，並遞迴掃描底線。突變驗證：在 `allowlist.json` 與 `generated_tools.json` 同時加一個屬性 → 紅燈 |
| **`NFR21.5`** | （`T-6`；`BR72.9`；`X-04` `scope_exclusion`）`gen_mcp_tools.py` 兩種模式讀取的輸入集合封閉：讀取開啟的路徑 ⊆ {`openapi.json`、`allowlist.json`、`generated_tools.json`}，`generated_tools.json` 只在 `--check` 模式被讀取，`.mcp.json` 從未被開啟 | 以替身攔截 `open` 與 `Path.read_text`／`read_bytes`，各跑一次寫出模式與 `--check` 模式，四項斷言（`BR72.9` logic 的 (a)–(d)）全成立。突變驗證：腳本多讀 `.mcp.json` → 紅燈 |
| **`NFR21.6`** | （`T-8`；`BR71.5`、`BR72.10`、`BR72.11`；帶入項 `R-17`、`R-12`）啟動自我驗證經**具名入口**執行：`__main__` 只呼叫具名的載入驗證函式與主函式，測試與正式啟動經同一個入口；手改產物不得啟動。白名單相等檢查的參考集合依 `R-12` 二擇一，**擇定者須在 code-summary 寫明**：(a) 啟動也載入 `allowlist.json` 作為獨立參考；或 (b) 啟動只做 `inputSchema.properties` 與 `binding` 映射鍵的內部一致性，獨立參考集合只存在於 CI 的 `--check` | 對具名入口餵入四份手改產物，各自得到非零退出且恰一行 ERROR（只含工具名或 agent 名）：① 寫入工具拿掉 `requires_agent`；② 加入 `/api/membership/` 項；③ 加入 `api_key` 屬性；④ 依 `R-12` 擇定者——選 (a) 則「`inputSchema` 多一個未在 `allowlist.json` 宣告的屬性」，選 (b) 則「`inputSchema` 多一個在 `binding` 中無映射的屬性」。另斷言 `__main__.py` 除了呼叫這兩個具名函式外無其他頂層邏輯（grep）。突變驗證：拿掉 `validate_tool_specs` 中任一檢查 → 對應案例紅燈 |
| **`NFR21.7`** | （`T-1`；`BR78.4` 驗 `BR73.3`；帶入項 `R-15`）跨請求身分隔離：兩個以上並發 client 帶不同使用者 token 交錯呼叫時，backend 收到的每一個請求的 `Authorization` 都等於發起該工具呼叫的 client 的 token；交錯必須是**決定性**的 | 記錄包裝內設 `asyncio.Event` 屏障：扣住使用者 A 的第一個 backend 請求，直到使用者 B 的請求已進入 bridge 並設定其 contextvar，再同時放行（`R-15` 的作法，比照 `progress-channel` 的 barrier）；之後再以 `asyncio.gather` 各跑 ≥ 20 次讀、另一組交錯寫。斷言：每筆紀錄的 `Authorization` 等於 path 中 `system_id` 擁有者的 token；寫入持久列的 `updated_by` 為各自的使用者 id；紀錄筆數等於工具呼叫次數。**突變驗證為 `code-generation` 的完成條件**：token 改存模組層變數 → 紅燈（有屏障後此突變必定紅燈，不靠排程運氣） |
| **`NFR21.8`** | （`T-2`；`BR78.5` 驗 `BR73.4`、`BR77.2`；帶入項 `R-19`）不外洩：`BR76.1` 每一列錯誤分支與成功的讀寫，工具結果全文（structured content 與文字內容）與 bridge 進程內全部 logger 的輸出，皆不含完整 token、其簽章段、`"Bearer "`＋token；且 `invalid_argument` 的訊息不回顯參數值。**含 SDK 預先驗證的分支**：若所釘版本的 `mcp` SDK 會在呼叫處理函式前依 `inputSchema` 自行驗證，該分支也必須產出 `BR76.1` 形狀的結果 | 依 `BR78.5` logic 逐分支觸發並斷言（根 logger 收集 handler、不調整層級、經 `configure_logging()`）。`R-19` 增列兩案：多餘參數、`agent_group` 不符 `pattern`——斷言結果恰為 `{error: "invalid_argument", message, retryable: false}`、`message` 不含送出的參數值（以標記字串檢查）、`NFR21.34` 的那一行 log 仍出現。突變驗證：`message` 改用 `str(exc)` → 紅燈；log 加入參數或標頭 → 紅燈 |
| **`NFR21.9`** | （`T-4`；`BR75.4`；帶入項 `R-13`）路徑段安全：`agent_group`／`field` 必須**整串**符合 `^[a-z0-9_]{1,64}$`，以 `fullmatch`（或樣式以 `\Z` 結尾）判定；`system_id` 整串符合 `^[0-9]{1,18}$`。不合格 → `invalid_argument` 且 backend 未收到任何請求 | 必測輸入各為一案：`"."`、`".."`、`"a/b"`、`"%2e%2e"`、`"cost\n"`（結尾換行）、`"co\nst"`（內嵌換行）、`"1\n"`（`system_id` 結尾換行）→ 皆 `invalid_argument`，記錄包裝筆數為 0。另以 PBT 性質六（`functional-spec.md` §六）以 `build_request` 實際組出的 URL 為判準。突變驗證：改用 `re.match` 搭配 `$` 結尾的樣式 → 換行案例紅燈；退回只用 `quote` → `".."` 案例紅燈 |
| **`NFR21.10`** | （`T-7`；`BR75.4`、`BR74.2`）跨進程副本一致：bridge 的鍵樣式字串 = `KEY_PATTERN.pattern`（`requirement_field_definitions.py:33`）= `allowlist.json` 的 `property_patterns`；`set(agents.json 的值) ⊆ set(GROUPS_BY_KEY)` | 一支測試、四個相等或包含斷言。突變驗證：改任一副本 → 紅燈 |

## 三、認證、授權與請求組裝

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR21.11`** | （`BR73.1`）缺漏、多值、空值、格式不符或超過 8192 位元組的 `Authorization` 在 bridge 本地判為 `unauthenticated`，**不呼叫 backend**——否則 FastAPI 0.111.0 對缺漏標頭回 403，會被誤報為 `forbidden` | 五案各一：記錄包裝筆數為 0，工具結果為 `unauthenticated`。另一案：有效格式但已失效的 token → backend 401 → `unauthenticated`（筆數 1） |
| **`NFR21.12`** | （`FR11.6`、`BR75.1`；`team.md` 規則 A 的形狀；`AC11.4.1`、`AC11.4.3`）授權完全由 backend 的 facade 判定，allow／deny **雙向**經真實 facade 驗證；被拒的理由與使用者直接呼叫時相同 | 驗證拓樸、測試資料庫四案：① 具全域 `K4` 且為該專案成員 → 讀、寫、清空皆成功；② 非成員 → `forbidden`；③ 無 `K4` → `forbidden`；④ 帳號未核准 → `forbidden`。② 與 ③ 另以同一 token 直接 `GET` backend，斷言其 `detail` 與工具結果的 `message` 相等。grep `backend/mcp_bridge/`：`require_story_action`、`user_can`、`resolve_project_role` 的出現次數為 0，且 import 陳述不含 `services.`（bridge 不 import backend 服務層、不自行授權、不呼叫成員層，`BR74.2`、`BR75.1`–`BR75.3`） |
| **`NFR21.13`** | （`BR73.2`）對 backend 只轉送 `Authorization`、`Content-Type`、`Accept`；`X-Cloud360-Agent` 與其他呼叫端標頭不轉送；**不跟隨重導**；請求只指向啟動參數給定的 base URL | 測試 client 額外帶 `X-Cloud360-Agent`、`Cookie`、`X-Forwarded-For` 與一個自訂標頭：記錄包裝收到的標頭鍵集合 ⊆ 上述三個加 httpx 自帶的 `Host`／`Content-Length`／`User-Agent`／`Accept-Encoding`／`Connection`。backend 包裝回 307 指向他址 → 工具結果為 `internal_error`，且他址未收到請求 |
| **`NFR21.14`** | （帶入項 `R-20` 第 2 點；`BR73.3`）bridge 共用的 `httpx.AsyncClient` **不得在請求之間攜帶 cookie**；擇一實作並在 code-summary 寫明：(a) backend 回應帶任何 `Set-Cookie` 即視為 `internal_error`；或 (b) 每次請求以不共享 cookie 的方式送出 | 記錄包裝在使用者 A 的回應加 `Set-Cookie: s=A`，隨後使用者 B 呼叫：B 的請求不含 `Cookie` 標頭（兩種實作皆須成立）；選 (a) 時 A 那一次的工具結果另需為 `internal_error`。此案以 `NFR21.7` 的屏障並發版本再跑一次 |
| **`NFR21.15`** | （`BR74.1`–`BR74.4`、`BR74.6`、`BR72.4`）寫入與清空要求已登錄的 agent 宣告；寫入本體的 `on_behalf_of` 恆為登錄表對應值，工具參數無法影響；純空白 `value` 本地拒絕 | 四案：① 寫入不帶 `X-Cloud360-Agent` → `agent_not_declared`，記錄包裝 0 筆；② 帶未登錄名 → 同上；③ 帶 `cost` 寫入 → 記錄包裝收到的本體恰為 `{"value": …, "on_behalf_of": "cost"}`；④ 工具參數多帶 `on_behalf_of: "architecture"` → `invalid_argument`，0 筆。另：`value` 為 `"   "` → `invalid_argument`，訊息含「clear_requirement_field」，0 筆 |
| **`NFR21.16`** | （`BR71.2`、`BR71.6`；帶入項 `R-18`；`requirements.md:619`）網路暴露面零新增：compose 服務只在 `internal`、無 `ports:`；`--host` 預設為 `127.0.0.1`，compose 的 `command` 明列 `--host 0.0.0.0`；若所釘 SDK 支援 Host 檢查，允許清單恰為 `mcp-bridge:8080`、`localhost:8080`、`127.0.0.1:8080` | ① 啟動參數解析器不給 `--host` 時值為 `127.0.0.1`（單元測試）。② compose 檔的 `mcp-bridge` 服務：`ports` 鍵不存在、`networks` 恰為 `[internal]`、`command` 含 `--host` 與 `0.0.0.0`（以 YAML 解析斷言，落 `infrastructure-design`／`code-generation`，見 `reliability-requirements.md` `NFR21.32`）。③ 若 SDK 支援：`Host: evil.example` 的 `/mcp` 請求被拒、`Host: 127.0.0.1:<埠>` 通過；不支援時依 `BR71.6` 在 code-summary 記錄，本項 ③ 不適用 |
| **`NFR21.17`** | （`BR71.1`；`NFR8`）零環境變數：bridge 不讀任何環境變數，設定全走命令列參數 | grep `backend/mcp_bridge/` 與 `backend/scripts/gen_mcp_tools.py`：`os.getenv`、`os.environ`、`getenv(` 皆 0；`python3 scripts/validate_env_contract.py` 在 CI 通過 |
| **`NFR21.18`** | （`BR73.5`；`[MBN1]`=A）bridge 不解碼 JWT、不產生任何使用者身分欄位——讀取稽核的處置依 `[MBN1]`=A **不**以 bridge 補身分 | grep `backend/mcp_bridge/`：`jwt`、`jose`、`base64`（解 token 用途）的 import 為 0；`NFR21.34` 的 log 欄位集合不含任何使用者識別欄位 |
| **`NFR21.19`** | （`BR71.3`、`BR73.1`；D-13）免認證的兩個面只回公開資訊：`/healthz` 恆回 `{"status":"ok"}`；`initialize`／`tools/list` 只回 `name`、`description`、`inputSchema`，不含 `binding`、backend 路徑或 `agents.json` 內容 | 不帶 `Authorization` 呼叫三者：`/healthz` 本體逐字相等；`tools/list` 每個工具的鍵集合 ⊆ {`name`、`description`、`inputSchema`、SDK 固定附加的 `annotations` 等無資料鍵}，全文不含 `/api/` 與 `binding`；記錄包裝 0 筆 |

## 四、Encryption 的處置（`OPEN-MB21-13`）

**結案依據，不是新決定**：bridge 與 backend 之間、未來大腦 client 與 bridge 之間，走 compose `internal` 橋接網段上的明文 HTTP。
使用者已於 `[G2]`=A 裁決「compose 內部一律明文，信任邊界就是 compose network 本身」（`brain-infra` `nfr-design-questions.md:90`，
作答 `:103`，2026-09-27T00:39:01Z），並於 `[I6]`=A 的「本題定案的效力」逐字定案「Encryption 面依 `OQ-16` 逐字『HTTP／SSE 須本機迴環
或加密』→ 本案以 **`internal` 網段、不發佈 `ports:`** 滿足」（`infrastructure-design-questions.md:299-303`，2026-10-03T12:47:03Z）。
functional-design 的 `OPEN-MB21-13` 是把同一決定的代價寫清楚，本站以上述兩項作答結案。

**殘留如實揭露（於核可關卡呈現）**：使用者 JWT（8 小時有效）以明文在 `internal` 網段往返，該網段另有 `db`、`redis`、`ollama`；
同網段任一被攻破的容器可被動截取。`[G2]` 的「明文接受的代價」已含「信任邊界含同網段容器與 host-local 行程」
（`brain-infra` `security-design.md` D-2，`:144`；摘要表 `:766` 逐字「信任邊界含同網段容器**與 host-local 行程**」）。同形的明文 JWT 傳輸今天已存在於主請求路徑（nginx 經 `edge` 網段反代至 `backend:8000`，
`deploy/docker-compose.deploy.yml:362-365`）。本版無實際 client（`OPEN-MB21-1`），正式環境經此網段的 JWT 流量目前為 0。
不可逆面（token 進 LLM context）與傳輸形式無關，由 `NFR21.4`、`NFR21.8` 承擔。

## 五、讀取稽核的處置（`OPEN-MB21-14`，`[MBN1]`=A）

使用者以 `[MBN1]`=A 裁決（本站問題檔 `:74`，2026-10-14T16:22:38Z 經選單）：**成功讀取不新增帶使用者身分的紀錄**，比照同 intent
的 `AC10.2.4` 裁決（`construction/deferred-ac-rulings.md:10`）。

**對 `requirements.md:620` ③ 的收窄解讀（引 `[MBN1]`=A，上游檔不回改）**：「MCP 工具呼叫的稽核主體必須是使用者本人而非大腦服務帳號」
讀為「**凡留下的紀錄，主體都是使用者而非服務帳號**」——bridge 沒有服務帳號（`NFR21.18`），寫入與清空的 `updated_by`、facade 的
變更 log 皆為使用者 id（`BR77.3`），此讀法下 ③ 成立。成功讀取的稽核程度與使用者直接開頁面讀**相同**（兩者皆不記，
`requirement_field_facade.py:301-305`），不另補。

**使用者會遇到的後果（作答時已揭露，原樣搬入）**：日後追查某次經 MCP 的讀取，只看得到 bridge log 的「某時刻、哪個工具、哪個 agent、
成功」，**不知道是哪位使用者、哪個系統**；需要時只能依時間對 backend 的存取紀錄（也沒有使用者欄位），實務上查不到人。
`OPEN-MB21-14` 依此**關閉**。被拒的讀取仍由 facade 記一行帶 `user_id` 的 WARNING（`requirement_field_facade.py:272`），不受影響。

## 六、ADR-0006 四面向（本站逐格對照）

**逐格對照上游 `requirements.md:617-620` 與本單元 `functional-spec.md` §六（`:173`）**：上游四格皆「適用」（IAM「適用（三處）」、
Encryption「適用（新增一處）」、Network exposure「適用（新增一處）」、Audit logging「適用（兩處）」），functional-design 四格皆「適用」，
本表四格皆「適用」，**無一格相反**。

| 面向 | 判定 | 本站的可驗證落點 |
|---|---|---|
| **IAM** | **適用** | 不新增身分、服務帳號或 secret；授權全在 facade，allow／deny 雙向經真實 facade 驗證（`NFR21.12`）；本地擋缺漏憑證（`NFR21.11`）；跨請求身分隔離以決定性屏障驗證（`NFR21.7`）；新增的授權面只有 allowlist 與代寫組登錄表（`NFR21.4`、`NFR21.6`、`NFR21.10`、`NFR21.15`）；不解碼 JWT（`NFR21.18`）。殘留不變：agent 宣告自報（`OPEN-MB21-2`）、agent 可代寫任一已登錄組（`OPEN-MB21-5`），兩者只影響溯源標示 |
| **Encryption** | **適用** | 傳輸：第四節，依 `[G2]`=A、`[I6]`=A 結案 `OPEN-MB21-13`，殘留於核可關卡揭露。不可逆面（token 進 LLM context）：`NFR21.4`（schema 白名單與底線）、`NFR21.8`（結果與 log 不外洩）、`NFR21.6`（手改產物不得啟動）。靜態：不落地任何 token 或工具結果 |
| **Network exposure** | **適用** | `NFR21.16`（無 `ports:`、只在 `internal`、`--host` 預設迴環、Host 允許清單）；`NFR21.13`（不跟隨重導、只打固定 base URL）；`NFR21.9`（路徑段字元集白名單）；`NFR21.19`（免認證面不回內部資訊）；`OPEN-MB21-10` 的上限在本站定值（`scalability-requirements.md` `NFR21.20`–`NFR21.22`）。D-3 blast radius 的重算（`OPEN-MB21-12`）屬 `infrastructure-design` |
| **Audit logging** | **適用** | 寫入與清空的主體為使用者本人（`BR77.3`，由 `NFR21.12` ① 的持久列 `updated_by` 斷言、`NFR21.7` 的寫入變體斷言）；每次工具呼叫恰一行 INFO（`NFR21.34`）；log 禁令（`NFR21.8`）。讀取面依 `[MBN1]`=A 收窄解讀（第五節），`OPEN-MB21-14` 關閉。殘留：清空無持久代寫溯源（`OPEN-MB21-4`）；bridge 與 backend log 無關聯鍵（`OPEN-MB21-9`，`nfr-design`） |

## 七、帶入項對照（`carried-review-items.md`，使用者 2026-10-14T16:16:10Z 裁決「核可，11 項帶進寫程式」）

本站只把**可驗證**者轉成判準；設計選擇仍由 `code-generation` 在計畫核可時呈現。

| 帶入項 | 本站的可驗證落點 | 說明 |
|---|---|---|
| `R-11`（第二退路下整合測試不可執行） | `NFR21.30`（可靠性）、`NFR21.40`（技術棧） | 不論依賴走哪條路，`T-1`／`T-2`／`T-4`／`T-8` 必須在 CI backend job 內實際執行；純函式模組禁止 import `mcp` |
| `R-12`（啟動是否讀 `allowlist.json`） | `NFR21.6` ④ | 二擇一，判準隨擇定者而定，兩者皆二元可判 |
| `R-13`（`re.match` 放行結尾換行） | `NFR21.9` | `fullmatch`；換行案例 |
| `R-14`（PBT 下限的統計誤判） | `NFR21.39`（技術棧） | 閘門必須決定性 |
| `R-15`（`T-1` 的交錯靠運氣） | `NFR21.7` | `asyncio.Event` 屏障；突變為完成條件 |
| `R-16`（C-5 落點漏三類） | 非 NFR | 契約追認事項，`code-generation` 計畫核可前由 conductor 處理（`OPEN-MB21-6`） |
| `R-17`（`create_app` 簽名不一、`T-8` 無具名入口） | `NFR21.6` | 具名入口；`__main__` 只呼叫它 |
| `R-18`（`--host` 預設值未定） | `NFR21.16` ① ② | 預設 `127.0.0.1`，compose 明列 `0.0.0.0` |
| `R-19`（SDK 預先驗證繞過封閉表） | `NFR21.8`、`NFR21.34` | 兩案斷言結果形狀、不回顯、仍有一行 log |
| `R-20`（`TransportFailure` 未定義；cookie jar 非原子） | `NFR21.26`（可靠性）、`NFR21.14` | 第 1 點為可靠性、第 2 點為安全 |
| `R-21`（問題檔殘留題數與行號） | 非 NFR | conductor 已於 `carried-review-items.md` 記明更正 |

## 八、刻意不設的目標

| 不設 | 理由 |
|---|---|
| bridge 與 backend／client 之間的 TLS | `[G2]`=A、`[I6]`=A 已定；見第四節 |
| bridge 端的權限判定或第二份授權 | `BR75.1`–`BR75.3`：facade 是唯一授權入口；第二份會與它不一致 |
| 讀取稽核事件 | `[MBN1]`=A；見第五節 |
| per-agent 可驗證憑證 | `[MB3]`=A 未採選項 B；新 IAM 面需新 ADR（`OPEN-MB21-2`） |
| token 撤銷清單 | JWT 無撤銷機制屬全專案認證設計（`auth.py`）；bridge 不持有任何 token 超過一次請求 |

## 九、送審前自檢（七項；全部產出寫完後實算，數字皆由 grep／jq 取得，未執行任何測試）

| # | 項目 | 結果 |
|---|---|---|
| 1 | **可達性** | 每條「偵測 X」的判準逐一可構造：逾時三案以 `asyncio.start_server` 的靜默／滴流／關閉埠構造（`NFR21.1`）；`Set-Cookie` 由記錄包裝加上（`NFR21.14`）；chunked 超量本體由測試 client 以產生器本體送出（`NFR21.20`）；串流 2 MiB 回應由記錄包裝產生（`NFR21.22`）；DNS 失敗以 RFC 6761 保留的 `.invalid` 網域構造（`NFR21.26`）；contextvar 殘留以「例外後接無憑證請求」構造（`NFR21.28`）；身分串號以屏障強制交錯（`NFR21.7`，不靠排程）；SDK 預先驗證兩案不論 SDK 是否預驗都可觸發，差別只在由誰拒絕，判準對兩者相同（`NFR21.8`）。**兩項依賴未實測的外部行為，如實標註**：`NFR21.21` 的 503 依賴 uvicorn `limit_concurrency` 的行為、`NFR21.16` ③ 依賴所釘 SDK 是否有 Host 檢查（後者已寫明不適用時的處置）；本站依派工不執行程式，兩者由 `code-generation` 實測 |
| 2 | **契約端點三問**（全部產出） | 本站新增的設定與型別：`--max-concurrency` 寫＝命令列（預設常數）、讀＝`__main__` 傳給 uvicorn、清＝進程生命週期；`TransportFailure` 寫＝執行層歸類、讀＝`map_outcome`、清＝該次呼叫結束即丟棄；本體上限與回應上限常數 寫＝程式常數、讀＝ASGI 層與執行層的讀取迴圈、清＝改程式；具名啟動入口（`R-17`）擁有＝本單元、呼叫＝`__main__` 與 `NFR21.6` 的測試；`access_log=False` 讀＝uvicorn。引用的 `NFR21.x` 以 `comm` 比對「被引用集合 − 有定義集合」為**空**；引用的 `BR7x.y` 比對 `rules.md` 的 `id:` 列，未定義者為**空**。孤兒：無 |
| 3 | **引用逐字核對**（事實與定位分開驗） | 本站全部 `檔名:行號` 以 `sed -n` 逐一印出核對：`requirements.md:617`／`:619`／`:620`、`nfr-design-questions.md:90`（`## G2`）／`:103`（`[Answer]: A`）、`infrastructure-design-questions.md:299`（「本題定案的效力」）–`:303`、`deferred-ac-rulings.md:10`（`AC10.2.4`）、`requirement_field_definitions.py:33`（`KEY_PATTERN`）／`:36`（`MAX_VALUE_LENGTH = 2000`）、`auth.py:33`（8 小時）、`backend/Dockerfile:5`（`FROM`）／`:27-28`（`HEALTHCHECK` 探 8000）／`:30`（`CMD`）、`requirement_field_router.py:146`／`:166`／`:196`（三條同步 `def`）、`requirement_field_facade.py:272`（被拒讀取的 `logger.warning`）／`:301-305`（`read_fields` 無 log）、`functional-spec.md:173`／`:282`／`:335`／`:352-359`、`backend/requirements.txt:1-9`／`:10`／`:11`／`:30`、`deploy/docker-compose.deploy.yml:362-365`、`security-design.md:144`／`:766`、`nfr-requirements-questions.md:74`。**更正 2 處**：`X-04` 首稿寫 `contract-summary.md:2050`（實為空行，標題在 `:2049`）；`backend/Dockerfile` 的 HEALTHCHECK 首稿寫 `:28`（指令始於 `:27`，探 8000 的 `CMD` 在 `:28`，改為 `:27-28`）。另：`anyio` 執行緒池預設 40 為套件預設值，**本站未實測**，已在 `NFR21.21` 的算式旁註明 |
| 4 | **檔案集合一致性** | 本站 `ls`：七份產出＋問題檔，共 8 個檔；與前例 `brain-gateway/nfr-requirements/` 的檔名集合相同（前例另有審查產生的 `reviews/`，本站尚未送審） |
| 5 | **跨檔傳播**（按事實逐種表達 grep；`grep -c` 以行計，計數皆**不含本節 §九 自身的引述**） | **`[MBN1]`=A**：問題檔 2、security 7、observability 2、performance 1、scalability 1、tech-stack 1 行命中，處置一致（不新增讀取身分紀錄、bridge 不解碼 JWT）。**`OPEN-MB21-13`／`-14`**：只在 security（各 3 行，第四、五節與帶入／表格）與問題檔（各 2 行）出現，皆寫「結案／關閉」。**`OPEN-MB21-10`**：scalability 4、security 1、問題檔 1，三項分項處置一致（本體、並發定值；頻率以理由關閉）。**數值**：65536 只在 scalability（3 行）、1048576 只在 scalability（3 行），其他檔以 id 引用而不重寫數字；「11 秒」在 performance 與 scalability 各 1 行，皆指 `NFR21.1` 的上限加 1 秒判定餘裕。**他單元規則字面**：`BR` 識別字非 `BR71`–`BR78` 者 0 命中；`NFR13.` 字面 0 命中 |
| 6 | **可算的數字先算再寫** | NFR 條數以 `grep -oE '\*\*\`NFR21\.[0-9]+\`\*\*'` 實算：**41**（全不重複；performance 3、security 16、scalability 5、reliability 8、observability 4、tech-stack 5）。`traceability.json` 以 `jq` 實算：`upstream_ids` **52**、`coverage` **52**＝`OK` **43**（`NFR4`、`NFR8` ＋ 41 條 `NFR21.x`）＋`N/A` **9**；`upstream_ids` 與 `coverage` 的 id 集合差集兩向皆空；41 條 `NFR21.x` 的 target 檔逐一 grep 確認確有其定義列。三個上限的算式：12000（2000×6）位元組 vs 65536；84000（7×2000×6）位元組 vs 1048576；16 vs 40 的 60% 餘裕——皆在各自段落列出算式 |
| 7 | **ADR-0006 四面向 ＋ PBT hard constraint** | 第六節逐格對照 `requirements.md:617-620`：上游四格「適用」、functional-design 四格「適用」、本表四格「適用」，**無一格相反**；判定欄皆附可驗證落點。Encryption 以 `[G2]`=A、`[I6]`=A 結案而非改判；Audit 的讀取面以 `[MBN1]`=A 收窄解讀並引出處。PBT：產生器為必須標的（`S-15`、`functional-spec.md` §六），落 `NFR21.39`，含決定性閘門（`R-14`）與必做突變七列；`project.md` 點名的三個落點不含本單元，不以 N/A 處理 |
