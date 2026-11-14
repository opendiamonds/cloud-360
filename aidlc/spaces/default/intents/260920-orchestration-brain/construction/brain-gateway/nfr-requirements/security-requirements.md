# 安全需求 — `U13 brain-gateway`

> `NFR13` 的 parent id 理由與「替身」的定義見 `performance-requirements.md` 檔頭。

## 〇、上游依據

| 依據 | 內容 |
|---|---|
| 本單元 functional-design | `BR61.1`–`BR61.8` 握手與認證、`BR62.1`／`BR62.2`／`BR62.6` 身分與重驗、`BR64.2`／`BR64.5` 入站驗證與攔截、`BR67.1`／`BR67.3`／`BR67.4` 不洩漏；`functional-spec.md` §七（`:345-369`）ADR-0006 四面向 |
| `requirements.md:597-600` | ADR-0006 四面向：FR8.3（掛 `/api/`）、FR8.5（token 不進 query string）、FR8.4（WS 必須更新 `last_activity_at`）、FR10.2（不得同進程繞過授權） |
| `team.md` 測試底線 A／B | 授權須 allow／deny 雙向；本單元新增的是 **WebSocket 端點**（FastAPI 不登錄於 `openapi.json`），規則 B 的 `TestClient` 義務以 `TestClient.websocket_connect` 承載 |
| 他單元指派 | `progress-channel` `nfr-design/security-design.md:190`（`S-5`：`SEC-1` 的鑄造端驗證落在 `U13`／`U12`）；`requirement-field-service` `nfr-requirements/security-requirements.md:42`（代寫的承接者含 `U13`）——兩者本單元皆**不呼叫**（`H-24`、`H-32`、`OPEN-GW13-12`），以 `NFR13.16` 的機械斷言結案 |

## 一、資料分類

| 資料 | 分類 | 落地 | 處置 |
|---|---|---|---|
| 使用者 bearer token | **憑證** | 不落地；只在 `Connection` 物件的記憶體（`BR62.2`） | `NFR13.7`、`NFR13.8`、`NFR13.15` |
| `user_message.text`（≤ 4000 字） | 內部（使用者內容） | Redis 歷程（`U10`，24 小時）；episodic 記憶（`U8`，PostgreSQL） | 靜態加密併入上游 `OQ-3`（`requirements.md:784`，指派 `nfr-design`）；本單元不另定手段；log 禁含（`NFR13.15`） |
| 回覆文字、referent、反問候選標籤 | 內部 | 歷程（回覆）；僅記憶體（referent、候選） | log 禁含（`BR67.3`） |
| `turnId`、`connId`、`sessionKey` | 內部識別碼 | log | 允許記錄（`BR67.3` 的允許欄位） |

## 二、握手與身分

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR13.7`** | token 不出現在任何回應標頭：accept 一律只回送 `cloud360.brain.v1`（`BR61.4`，`[GW1]`=A） | `websocket_connect(subprotocols=["cloud360.brain.v1", "bearer.<標記 token>"])`：`accepted_subprotocol == "cloud360.brain.v1"`，且 `extra_headers` 的任何鍵值皆不含標記。突變驗證：改回 DEMO 的 `accept(subprotocol=f"bearer.{token}")`（`brain_router.py:275`）→ 紅燈 |
| **`NFR13.8`** | 本端點**從不讀 query string**；token 只放在 query string 的握手一定被拒，兩種形狀分別斷言（`BR61.5`） | ① 帶 `cloud360.brain.v1`、有效 token 只在 `?token=`：連上後收到關閉碼 4401。② 不帶 `cloud360.brain.v1`：`websocket_connect` 拋 `WebSocketDisconnect` 且從未 accept。③ 本單元模組對 `query_params` 的出現次數為 0（grep）。**限制**：② 在 `TestClient` 下表現為關閉碼 1000（starlette 0.46.2 實測），在真實 uvicorn 下為 HTTP 403；本判準只斷言「未 accept」，HTTP 403 的形狀屬 `OPEN-GW13-6` 的實環境驗證 |
| **`NFR13.9`** | 認證與 `K1` 判定在 accept 之前完成；未通過者**從未取得可讀寫的通道**——伺服器不讀任何訊框、不寫任何 session 狀態（`BR61.4` 的最小暴露面） | 無效 token 一案：收到 4401；`SessionStore.load`、`list_items`、`append_message` 替身呼叫次數皆 0；登錄（registry）為空 |
| **`NFR13.10`** | `K1` 授權 **allow／deny 雙向**（`team.md` 規則 A 的形狀；`BR61.6`）：① 角色有 `K1.view` 且已核准 → 收到 `ready`；② 角色無 `K1` → 4403；③ 帳號未核准（`authorization_status`）→ 4403；④ 帳號停用 → 4401 | 以測試資料庫（`tests/helpers.py` 的 SQLite ＋ `ensure_role_permissions_seeded(force=True)`）四案各至少一例且全綠。突變驗證：把 `user_can` 換成恆真 → ②③ 紅燈 |
| **`NFR13.11`** | 每則客戶端訊息（hello 除外）在同一 DB session 內重驗並重鑄 principal（`record=True`，使 `last_activity_at` 對長連線持續更新，FR8.4）；就緒的連線每 60 秒背景重驗（`record=False`）；非認證類例外**不關閉**連線（`BR62.1`、`BR62.6`） | ① 第一則訊息後把使用者 `is_active` 設為假，送第二則：收到 4401，`classify` 替身呼叫次數不增加。② 認證替身記錄 `record` 參數：每則訊息為 `True`、背景重驗為 `False`。③ 閒置連線、停用後以假時鐘推進 60 秒：收到 4401，期間未送出任何 `work_items`。④ 重驗替身拋非 `HTTPException` 例外：每則訊息路徑收到 `error(INTERNAL_ERROR)` 且連線仍開、背景路徑只記 WARNING 且連線仍開 |
| **`NFR13.12`** | 身分只來自連線：客戶端訊息不得帶任何身分欄位或 `turnId`（`WsClientEnvelope` 的 `extra="forbid"`，`BR64.2`；`H-27`） | 兩案：`user_message` 的 payload 夾帶 `userId`、envelope 夾帶 `turnId` → 各收到 `error(INVALID_REQUEST)`，`classify` 替身呼叫 0 次 |

## 三、攔截與輸出不洩漏

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR13.13`** | `prompt_guard` 先於一切 LLM、歷程與記憶（`BR64.5`；`project.md ## Mandated` 的平台自我竄改預檢） | 命中攔截的文字一案：客戶端依序收到 `token{text: REFUSAL_MESSAGE}` 與 `done`；`classify`、記憶預取、`append_message`、`MemoryFacade.write` 替身呼叫次數皆 0。另一案：`classify` 替身拋 `PlatformSelfModificationRefused` → 同一可觀察結果（縱深的第二層） |
| **`NFR13.14`** | 送給客戶端的 `error.message` 只取自 `BR67.1` 的封閉表（含本站新增的一句「訊息太頻繁，請稍候再送出」，見 `scalability-requirements.md` 的 `NFR13.20`；`NFR13.19` 沿用既有的「訊息太長」句）；關閉原因只用 ASCII、≤ 123 位元組、不含 token（`BR67.4`） | ① 對 `BR67.1` 列出的每一類例外各一案，例外訊息內含標記字串：收到的 `error.message` ∈ 封閉表且不含標記。② 列舉本單元全部關閉原因字串（4401、4403、4400、1011 各自的 reason）：皆 `isascii()`、`len(encode()) ≤ 123`、不含標記 token |
| **`NFR13.15`** | log 不含 token、query string、使用者文字、回覆文字、referent 與候選標籤（`BR67.3`；本 repo 為 public） | 以 `assertLogs(level="DEBUG")` 擷取**根 logger**（涵蓋所有傳播的 logger），走：帶標記 token 的握手、帶標記使用者文字的一輪交辦、一次 referent 多筆相符的對象反問（標記 referent 與專案名）、一次失敗路徑。擷取到的每筆紀錄皆不含任一標記 |

## 四、邊界（只經 facade；不碰不屬本單元的契約）

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR13.16`** | 本單元模組 (a) 不直讀表、不 import 他單元的 service 層：只經 `HierarchyFacade`、`MemoryFacade`、`SessionStore`、`IntentRouter`、`WorkOrchestrator` 的公開介面（`BR64.12`、`BR67.10`）；(b) 不鑄造 `request_key`、不呼叫 `ProgressChannel`（`BR67.8`，結案 `S-5`）；(c) 不呼叫需求欄位與成員角色的 facade（結案 `requirement-field-service` 的承接指派，`OPEN-GW13-12`） | `brain_gateway.py`、`brain_gateway_rules.py` 對下列名稱的 import 與出現次數皆為 0（grep）：`hierarchy_service`、`memory_service`、`membership_service`、`membership_facade`、`requirement_field_facade`、`requirement_field_service`、`progress_channel`、`request_key`、`SessionLocal().query`／`text(`（直寫 SQL） |

## 五、ADR-0006 四面向（本站逐格對照）

**逐格對照上游 `requirements.md:597-600` 與本單元 `functional-spec.md` §七**：上游四格皆「適用」，functional-design 四格皆「適用」，
本表四格皆「適用」，**無一格相反**。

| 面向 | 判定 | 本站的可驗證落點 |
|---|---|---|
| **IAM** | **適用** | `NFR13.9`（accept 前認證）、`NFR13.10`（`K1` 雙向）、`NFR13.11`（逐則與 60 秒重驗，撤權外洩窗 ≤ 60 秒）、`NFR13.12`（身分只來自連線）、`NFR13.16`（只經 facade）。殘留不變：`HierarchyFacade` 尚未讀 `is_approved`，以 `K1` 判定擋在前面（`functional-spec.md:352`） |
| **Encryption** | **適用** | 傳輸：對外 `wss` 經 Cloudflare Tunnel；token 不進 URL（`NFR13.8`）、不進回應標頭（`NFR13.7`）。tunnel 內主機明文 ws 與既有 SSE 同形，不新增。靜態：本單元不持久化；歷程與 episodic 的靜態加密屬 `OQ-3`（`nfr-design`），本站不新增手段 |
| **Network exposure** | **適用** | 本單元是本 intent 唯一新增的對外網路面（`K-12`）。`NFR13.8`（query string 不讀）、`NFR13.17`／`NFR13.18`（連線數上限）、`NFR13.19`（訊框大小）、`NFR13.20`（訊息頻率）——**`OPEN-GW13-13` 在本站定數字**。殘留：uvicorn 的全域 `ws_max_size` 不改（見 `NFR13.19` 的理由）；cloudflared／nginx 是否透傳子協定標頭仍屬 `OPEN-GW13-6` |
| **Audit logging** | **適用** | `NFR13.11` ②（逐則 `record=True`、背景 `record=False`，FR8.4）；`NFR13.15`（log 禁令）；`NFR13.36`（連線生命週期的計數 log，不含身分以外的內容） |

## 六、刻意不設的目標

| 不設 | 理由 |
|---|---|
| 新的加密手段 | 本單元不新增傳輸路徑（tunnel 之內沿用既有），使用者內容的靜態落地屬 `U10`／`U8`，加密統一由 `OQ-3`（`nfr-design`）決定 |
| 本單元自己的稽核事件表 | 帳號活動稽核以 `record=True` 承擔（`K-12` 的 `activity_record`）；session 狀態 24 小時即消失，不寫稽核列（與 `session-store` `security-requirements.md:48` 的宣告一致） |
| token 撤銷清單 | JWT 無撤銷機制屬全專案認證設計（`auth.py`）；本單元以「停用即 4401、撤權即 4403、閒置 ≤ 60 秒生效」收斂外洩窗 |
