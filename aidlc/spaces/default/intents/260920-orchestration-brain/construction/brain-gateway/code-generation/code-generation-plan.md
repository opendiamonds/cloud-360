# Code Generation Plan — `U13 brain-gateway`

> 本計畫把四站設計（functional-design 修訂 2、nfr-requirements、nfr-design、infrastructure-design）落成程式，
> **並一併處置四站審查與使用者裁決帶下來的 37 項**（`../carried-review-items.md`，§二）。
> 方法論依下方 Testing Contract 為 `test-after`。
>
> **本計畫的核可同時核可契約變更紀錄 `ADR-0020`**（草案：同目錄 `adr-0020-draft.md`）。核可後 Step 1 原樣移入
> `inception/decisions/0020-brain-ws-contract-page-scope-fields.md` 並改為 Accepted；契約增量 C-1..C-7 的程式修改都在它之後。

## 一、交付範圍

| # | 交付 | 位置 | 類型 |
|---|---|---|---|
| 1 | ADR-0020（契約增量 C-1..C-7、`consumed_by` 更正） | `inception/decisions/0020-brain-ws-contract-page-scope-fields.md` | 新建（由草案移入） |
| 2 | 契約增量 | `backend/services/brain_ws_contract.py`（六個模型）、`backend/scripts/dump_ws_contract.py`（白名單）、重產 `ws-contract.json`、`frontend/src/types/ws-contract.d.ts` | 修改（`U2` 跨單元） |
| 3 | 純函式 | `backend/services/brain_gateway_rules.py`：`parse_subprotocol_offer`、`session_key_for`／`user_id_from_session_key`、`resolve_segment`、`TurnLedger`、`error_for`、`match_referent`、`scan_targets_in_utterance` | 新建 |
| 4 | 閘道 | `backend/services/brain_gateway.py`：WebSocket handler（`/api/brain/ws`）、連線登錄與扇出（佔位計數、載入中佇列）、`GatewaySink`、記憶轉接器與 `MemoryWorker`（實例層級執行器、熔斷）、限流、重驗、`GatewayTiming` 注入 | 新建 |
| 5 | 啟動與掛載 | `backend/main.py`：startup hook 建立閘道元件（`configure_intent_routing_env` 之後、`init_db` 之前）、掛 router、shutdown 關閉自己的執行器；單行程守門 | 修改 |
| 6 | DEMO 移除（`[IG2]`=A） | 刪 `backend/services/brain_router.py`、`main.py:7`、`main.py:110-112`；刪或改寫 `frontend/src/pages/BrainPage.tsx`、`App.tsx:89-99`、`Sidebar.tsx:211-217`；e2e `member-pages.spec.ts`（8 處）與 `memory-page.spec.ts`（2 處）的 `/brain` 落地頁改中性頁；`test_intent_routing_structure.py:62`、`:315-345`；註解 `eslint.config.js:32`、`intent_routing_types.py:48` | 刪除／修改（跨單元） |
| 7 | 部署設定（`[IG1]`=A） | `.github/workflows/deploy.yml` 必要 secret 檢查加 `OPENROUTER_API_KEY`（不動 `render-env.sh`）；`deploy/.env.example`、`DEPLOY.md:24` | 修改 |
| 8 | 本機文件（Mandated 同步） | `LOCAL-DEV.md`：`REDIS_*` 成為啟動必要條件、`OPENROUTER_API_KEY` 部署必要（`:17-20`、`:23`、`:24-26`、`:79`、`:593`） | 修改 |
| 9 | 依賴 | `backend/requirements.txt` 明列 `websockets`（WS keepalive 與 TestClient 依賴，原僅經 langgraph 傳遞） | 修改 |
| 10 | 測試 | `backend/tests/test_brain_gateway_{rules,handshake,turn,fanout,memory,limits,startup}.py`；`backend/tests/test_ws_contract.py` 同步修改 | 新建／修改 |
| 11 | 文件與追溯 | `code-summary.md`、`traceability.json`、`source-manifest.json`；functional-design 的文字回補列在 code-summary（不回改已凍結設計檔） | 新建 |

**零新環境變數、零新服務、零新監聽埠、零 DDL**（`REDIS_*`、`OPENROUTER_API_KEY` 皆既有）。**不新增任何 LLM 呼叫**；`AC8.1.1` 為 Deferred（`OPEN-GW13-15`）。

**同批合併約束**（infrastructure-design §五）：ADR-0020 → 契約增量與重產物 → U13 → DEMO 前後端移除 → `U14`。本分支**第一次**進 `ut` 時 DEMO 後端必須已移除（`[IG2]`=A）；含 `OPENROUTER_API_KEY` 必要檢查的變更合併前，須先確認該 secret 已設定且為 secret（第 34 項，由使用者執行）。

## 二、併入本計畫的審查殘留（`../carried-review-items.md` 全 37 項）

| # | 來源 | 處置 | 步驟 |
|---|---|---|---|
| 1、2、11、12 | FD review-03 R-01、R-02；NR R-05、R-06 | `scan_targets_in_utterance` 以正規化（`strip().casefold()`）後的**最長完整名稱**比對，區間被較長名稱完全覆蓋者剔除；不同專案下同名對象不互相比較；系統命中吸收其所屬專案；**命中一律以 `clarify(kind="target")` 反問確認**，不靜默改動作業對象；高信心路徑依 BR64.9 解析唯一對象時自動更新，與掃描路徑的差異在 code-summary 寫明理由；PBT 性質五改寫為可失敗的 (a)(b)(c) | 3、4 |
| 3 | FD R-03 | 載入中佇列取空與改為 ready 在同一個無 `await` 區段；測試鎖住「送出暫存佇列期間新到的訊息」順序 | 5、6 |
| 4、13、28 | FD R-04；NR R-07；ND R-11 | 專案數 > 50：只在句中確實指名對象且無法解析時回「專案太多，請先在脈絡列選定專案」；掃描零命中時不得靜默交辦舊對象；未指名對象且已有作業對象時照常交辦；AC1.1.5 註記列條件 | 5、6 |
| 5、8、18 | FD R-05；NR R-02；ND R-01（Critical） | 熔斷全域鍵，只在例外鏈上含逾時／連線類（含 `EmbeddingProviderUnavailable` 包住的 httpx 例外，`embedding_port.py:617-621`）時開啟；寫入等待 `EMBEDDING_TIMEOUT_SEC + 5`；半開試探在任何未執行出口（含 `BUSY_SKIPPED`）清除 `probing`；不變量測試鎖住「熔斷可恢復」；替身拋實際例外類型並揭露限制；以真實 `OllamaAdapter` 包裝方式的契約測試鎖住 `raise … from` | 5、6、10 |
| 6、32 | FD R-06；ID R-01 | 交付 #7、#8 | 11 |
| 7、20 | NR R-01；ND R-03 | 全域佔位在 handler 一開始、每使用者佔位在認證後 accept 前、`finally` 釋放；併發握手 N+1 測試；頻率視窗以使用者為鍵保留至過期、握手納入限流 | 5、6 |
| 9 | NR R-03 | `GatewayTiming`（`monotonic`／`sleep`／`wait_for`）建構子注入，所有計時路徑逐條使用；AST 測試禁止直呼 `time.monotonic`／`asyncio.sleep`／`asyncio.wait_for`／`time.sleep` | 5、6 |
| 10、17、23 | NR R-04、R-11；ND R-06 | `[GWND1]`=A：第 11 條連線拒絕；U14 退避重試至少 60 秒、4401 重取 token——寫進 code-summary 的 U14 交接表 | 12 |
| 14 | NR R-08 | 三段預算各自獨立、不相加；NFR13.1 量測落點 build-and-test，本站無法判定 | 12 |
| 15 | NR R-09 | 記憶執行器以 `BoundedSemaphore` 於工作執行緒 `finally` 歸還，計實際佔用 | 5、6 |
| 16 | NR R-10 | 單行程守門檢查 `WEB_CONCURRENCY`／`UVICORN_WORKERS` 與 compose 無 `env_file` | 7、8 |
| 19 | ND R-02（Major） | `MemoryWorker.run` 不吞 `CancelledError`，一律重拋 | 5、6、10 |
| 21 | ND R-04（Major） | 送出失敗或逾時的連線：取消登錄並主動 `close(1011)` | 5、6、10 |
| 22 | ND R-05（Major） | `_executor`／`_slots` 為實例屬性，隨閘道元件建立與關閉 | 5、6、10 |
| 24、25 | ND R-07、R-08 | 引用行號更正記於 code-summary；`send_direct` 不使用 AST 規則禁止的變數名 | 5、12 |
| 26 | ND R-09 | 揭露 U12 事件迴圈上的同步 Redis 呼叫與共用預設執行緒池對撤權的影響 | 12 |
| 27 | ND R-10 | episodic 跳過以 WARNING 計數（與 NFR13.5 一致） | 5 |
| 29 | ND R-12 | 被拒訊框（過大、過頻）計入關閉連線門檻 | 5、6 |
| 30、34 | `[IG1]`=A；ID R-03 | 交付 #7；合併前以 `gh api repos/<owner>/<repo>/actions/secrets` 確認 `OPENROUTER_API_KEY` 存在且為 secret——**由使用者在合併前執行**，計畫不自動執行 | 11、12 |
| 31、33 | `[IG2]`=A；ID R-02 | 交付 #6（DEMO 全部觸點同一 PR） | 7、9 |
| 35 | ID R-04 | 交付 #9 | 11 |
| 36、37 | ID R-05、R-06 | 部署後實測步驟（infrastructure-design §四）的 L2 回退改寫、token 不經 argv／shell history、輸出遮罩——更新寫在 code-summary 的部署後實測清單 | 12 |

**Critical／Major 的突變驗證**：第 1、7、8、18、19、20、21、22 項各配一個「套用 → 紅 → 還原 → 綠」的突變（見 `unit-test-instructions.md §四`）。

## 三、步驟（`test-after`：逐層實作後補該層測試）

- [x] **Step 1 — 結構骨架與 ADR**：將 `adr-0020-draft.md` 原樣移入 `inception/decisions/0020-brain-ws-contract-page-scope-fields.md`、Status 改 Accepted；建立兩個新模組檔骨架（不建空實作）。
- [x] **Step 2 — 驗證執行器並記錄本單元指令**：執行 `unit-test-instructions.md §二` 的就緒檢查（`tests.test_ws_contract`、`tests.test_session_store_behaviour`），確認 `TestClient.websocket_connect` 可用。
- [x] **Step 3 — 資料模型（契約）：實作**：C-1..C-7、`dump_ws_contract.py` 白名單；重產 `ws-contract.json` 與 `ws-contract.d.ts`。
- [x] **Step 4 — 資料模型：測試**：`test_ws_contract.py` 依 functional-spec §十一之二 修改並新增 C-1..C-7 的正負案例；`dump_ws_contract.py --check` 與 `npm run check:ws-types` 通過；`brain_gateway_rules.py` 的五個 PBT 性質。
- [x] **Step 5 — 業務邏輯：實作**：`brain_gateway_rules.py` 與 `brain_gateway.py` 全部（`BR61`–`BR67`、§二 處置）；logger `"cloud360.brain_gateway"`。
- [x] **Step 6 — 業務邏輯：測試**：握手（雙子協定、只回送協定名、query string 拒絕、4401／4403／4400／1011、佔位計數併發）、輪次（prompt_guard、clarify 兩種 kind、referent 解析與目錄、終止語意、EMPTY_RESPONSE）、扇出（多連線、載入中佇列順序與溢位、推播只給本人）、記憶（預取、熔斷含半開與 `BUSY_SKIPPED`、取消重拋、episodic 背景寫入）、限流與訊框上限、重驗（每則與 60 秒）、Redis 不可用（GW3）。
- [x] **Step 7 — API（端點掛載與 DEMO 移除）：實作**：`main.py` 啟動與掛載、單行程守門；交付 #6。
- [x] **Step 8 — API：測試**：startup 順序與缺 `REDIS_*` 時啟動失敗；`/api/brain/ws` 恰一條 WebSocket 路由；`dump_openapi.py --check` 未漂移；`test_intent_routing_structure.py` 改寫後綠。
- [x] **Step 9 — Frontend**：本單元不新建頁面（屬 `U14`）；只做 DEMO 前端移除與兩支 e2e 落地頁改寫，以 `npm run lint`、`tsc -b` 驗證；e2e 由 CI `ui-regression` 執行。
- [x] **Step 10 — 突變驗證**：依 `unit-test-instructions.md §四` 逐項套用 → 紅 → 還原 → 綠，記入 code-summary。
- [x] **Step 11 — 環境／建置設定**：交付 #7、#8、#9；`python3 scripts/validate_env_contract.py`、`python3 scripts/validate_repo_contract.py` 通過。
- [x] **Step 12 — 文件與追溯**：`code-summary.md`（§二 處置、偏離與取代關係表、U14 交接、部署後實測清單與合併前 secret 確認、揭露事項）；`source-manifest.json`；`traceability.json`。

## 四、步驟 ↔ 故事追溯

| 故事／AC | 步驟 |
|---|---|
| `AC1.1.5`（句中指名系統更新作業對象） | 5、6 |
| `AC7.1.1`–`AC7.1.3`（推播只給本人、失敗與逾時可分辨） | 5、6 |
| `AC8.1.2`（`record=True` 更新最後活動） | 5、6 |
| `AC8.1.3`（token 不在 query string；兩案） | 5、6 |
| `AC8.1.4`（既有 SSE 端點不變） | 8 |
| `AC8.1.1` | Deferred（`OPEN-GW13-15`），不實作 |

## 五、方法論與 contract 基線的對應

**Data model**（Step 3–4，WebSocket 契約）、**Business logic**（Step 5–6）、**API / endpoint**（Step 7–8，掛載與移除）依序「實作 → 測試」；
**Repository / data access** 層本單元不新增（經既有 `SessionStore`／facade）；**Frontend** 只做 DEMO 移除與 e2e 落地頁改寫（Step 9）。方法論未改。

## 六、code-generation Request Changes（2026-10-20）：合併前必修第 2 項(a) 與第 19 項

使用者對整站送出 Request Changes，要求修正 `construction/functional-design/merge-blockers.md` 的 19 項。劃給本單元的是：

- **第 2 項(a)**：`brain-ws-contract` 已依使用者裁決把 `error` 的 `turnId` 改為「必填鍵、值可為 null」，契約說明逐字要求「伺服器**不得**為非輪次錯誤捏造一個 turnId」（`brain_ws_contract.py:371-380`）。閘道仍以 `_send_single_error`（`brain_gateway.py:1146-1150`）的 `tid = turn_id or _mint_turn_id()` 為每一則非輪次錯誤捏造編號。該列要求本單元訂出逐個錯誤來源的 `turnId` 規則表並附測試。
- **第 19 項**：合併前 `OPENROUTER_API_KEY` 必須已設為 GitHub secret。程式端已於 Step 11 完成（`deploy.yml:76`、`:83` 的必要檢查）；**未完成的是查證 secret 確實存在**。

**實測現況（以唯讀查證取得）**：`_send_single_error` 有 13 個呼叫點（`grep -n "_send_single_error" brain_gateway.py` 扣掉定義行），全部不帶 `turn_id` 參數，因此每一則都是捏造編號；另有一個既存缺口——`_dispatch_client_message` 拋出未預期例外時（`:1130-1132`），若該則訊息已開啟一輪（`user_message` 或對應反問的 `select_clarify_candidate`），錯誤以新編號送出，**原本那一輪永遠收不到終止事件**，前端會一直等。

**使用者裁決**（`[GW-MB2]`，2026-10-24）：反問等待中收到格式錯誤的選擇訊息（過不了 `WsClientEnvelope` 驗證，例如 `candidateId` 型別不對）→ **不算輪內**，以 `turnId=null` 送錯誤，**反問保留**，使用者可重選。

**BR2.8 錯誤 `turnId` 規則表**（本表取代 functional-design `rules.md:144`、`:302`、`:382` 的「以新 turnId 送出」三處；已凍結的設計檔不回改，取代關係記入 code-summary）：

| # | 錯誤來源（`brain_gateway.py`） | 代碼 | `turnId` |
|---|---|---|---|
| T1 | 二進位訊框、訊框過大、頻率超限（`_reject`，`:1088`／`:1092`／`:1102`） | `INVALID_REQUEST`／`RATE_LIMITED` | `null` |
| T2 | 每則重驗拋例外（`:1110`） | 依 `error_for` | `null` |
| T3 | 信封驗證失敗（非 JSON、非物件、未知 type、偷帶 turnId、缺必填欄位；**含反問等待中格式錯誤的選擇訊息**，`[GW-MB2]`=A，`:1126`） | `INVALID_REQUEST` | `null`；`pending_clarify` 不清除 |
| T4 | ready 之後再收到 `hello`（`:1166`） | `INVALID_REQUEST` | `null` |
| T5 | `select_clarify_candidate` 時沒有待選反問（`:1531`） | `INVALID_REQUEST` | `null` |
| T6 | `select_clarify_candidate` 格式正確但 id 不在候選內（`:1541`，現行不變） | `INVALID_REQUEST` | 該輪 `T`，並結束該輪 |
| T7 | `set_work_target`／`set_sharing_mode`／`correct_work_item` 失敗（`:1574`、`:1588`、`:1591`、`:1605`、`:1608`、`:1633`；`_error_for_request` 的 `turn is None` 分支 `:1500`） | 依 `error_for` | `null`（三者皆非輪次請求，BR1.6） |
| T8 | 輪內處理失敗、`EMPTY_RESPONSE`、`emit_turn` 推播（`_fail_turn`、`_end_turn`、`GatewaySink.emit_turn`） | 依原規則 | 該輪 `T`（現行不變） |
| T9 | `_dispatch_client_message` 拋未預期例外（`:1130-1132`） | `INTERNAL_ERROR` | 若該則訊息已開啟一輪且該輪尚未終止 → 以該輪 `T` 結束該輪；否則 `null` |

- [x] **Step 13 — 業務邏輯：實作**
  - `_send_single_error` 拿掉 `turn_id` 參數與 `_mint_turn_id()`，envelope 與 payload 的 `turnId` 一律為 `None`（T1–T5、T7）。
  - T9：連線記住「最近一則開啟的輪次」（`user_message` 建立 `Turn` 時、`select_clarify_candidate` 取出待選反問時設定）；`:1130` 的未預期例外分支若該輪尚未終止即走 `_fail_turn`（帶 `T`），否則送 `null` 錯誤。輪次終止後該參照不影響下一則訊息。
  - T3：信封驗證失敗的分支不碰 `pending_clarify`（現行已不碰；以測試鎖住）。
  - `_mint_turn_id()` 只留在兩個真正開啟一輪的位置：`_on_user_message` 建立 `Turn`、`GatewaySink.emit_turn`。
  - log 關聯：非輪次錯誤原本無 log 使用該捏造編號，不新增欄位。
- [x] **Step 14 — 業務邏輯：測試**
  - T1–T5、T7 每列至少一案：斷言收到的 `error` envelope 與 payload 的 `turnId` 皆為 `None`，且通過 `WsEnvelope.model_validate`。
  - T3：反問等待中送 `candidateId` 型別錯誤的選擇 → `null` 錯誤；再送合法 id → 以原輪 `T` 繼續交辦。
  - T6：維持既有案例（帶 `T`）。
  - T9：以替身讓輪內流程拋未預期例外 → 收到帶 `T` 的 `error(INTERNAL_ERROR)`、該輪不再收到任何訊息、下一則 `user_message` 正常開新輪；非輪次訊息拋未預期例外 → `null`。
  - 結構測試：AST 斷言 `_mint_turn_id` 的呼叫點恰為上述兩處。
  - 既有測試中斷言非輪次錯誤帶非 null `turnId` 者，依本表改寫（方法名不改，避免 TCMS 案例成孤兒）。
  - 突變（記入 `code-summary.md`）：M1 `_send_single_error` 還原為捏造編號 → T1–T5、T7 案紅；M2 信封驗證失敗時清除 `pending_clarify` → T3 案紅；M3 T9 分支不理會開啟中的輪次 → T9 案紅；M4 在 `_on_set_work_target` 加回 `_mint_turn_id()` → 結構測試紅。
- [x] **Step 15 — 第 19 項查證**：以 `gh api repos/opendiamonds/cloud-360/actions/secrets` 與 `.../actions/variables` 各查一次名稱（唯讀，只列名稱、不讀值），確認 `OPENROUTER_API_KEY` 在 secrets、不在 variables（`project.md ## Mandated`）。缺少或誤存為 variable → 不由我設定，記為合併前阻擋並回報使用者；若曾存為 variable，依同條規則須重新產生金鑰。
- [x] **Step 16 — 驗證**：本單元全部測試、`tests.test_ws_contract`、全套 `python -m unittest discover -s tests`、`dump_ws_contract.py --check`、`dump_openapi.py --check`、`validate_env_contract.py`、`validate_repo_contract.py`。
- [x] **Step 17 — 文件與追溯**：`code-summary.md` 新增一節（規則表、取代關係、突變結果、第 19 項查證結果、交接 `entry-page-ui` 的第 2 項(b)：前端須把 `turnId=null` 的錯誤呈現為不屬於任何輪次，不得歸入或解除進行中輪次的等待）；`merge-blockers.md` 第 2、19 列以純 append 方式更新處置；`traceability.json`、`source-manifest.json` 更新。

**不在本次範圍**：第 2 項(b)（`entry-page-ui` 的 `useBrainConnection.ts:173`），在該單元處理；`WsServerMessageType`／`ErrorPayload` 契約不再修改（第 2 項的契約層已完成）。

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
