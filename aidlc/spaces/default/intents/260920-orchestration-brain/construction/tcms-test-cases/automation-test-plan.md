# 自動化測試計畫與覆蓋盤點 — 260920-orchestration-brain

- 撰寫時間（`date -u`）：開工 `2026-11-14T05:00:36Z`，本檔定稿 `2026-11-14T05:19:23Z` 之後
- 受測對象：分支 `danniel/docs/orchestration-brain-ideation`，HEAD `50a6900`（PR #650 的 CI 實跑基準為 head `48f6349`）＋ 本站新增／改動的測試檔
- 執行位置：scratchpad 副本（rsync 排除 `.git`、`node_modules`、`.venv`、`__pycache__`、`.hypothesis`、`.env`；前端 `node_modules` 以 `cp -Rc` 複製）；Python 一律 repo 的 `backend/.venv/bin/python -B`、`PYTHONDONTWRITEBYTECODE=1`、`HYPOTHESIS_STORAGE_DIRECTORY` 指向 scratchpad
- 臨時服務：`pgvector/pgvector:pg18`（容器 `tcms-pg`，只綁 `127.0.0.1:55487`，密碼 `[REDACTED]`，存於 scratchpad 0600 檔），用完已 `docker rm -f` 並刪除密碼檔。未碰本機驗證服務（8010、5173、55433、56379）、未連 staging 或共用 DB／Redis

## 一、覆蓋盤點（三桶計數，由腳本輸出）

盤點腳本讀 `inception/user-stories/stories.md` 的全部 AC 識別字（`AC<n>.<n>.<n>` 與 `AC-A11Y.<n>`），對照 24 個單元的 `code-generation/traceability.json`；再加上 build-and-test 新增、`stories.md` 沒有 AC 的行為，以及只有真實模型或真實環境才碰得到的行為。腳本逐字輸出：

```
AC 項：108（含 AC-A11Y 2 項）；AC 各桶：{'待自動化': 1, '已自動化': 107}
其他行為項：25
總計 133 項：已自動化 120、待自動化 3、只能手動 7、未分類 3
```

| 桶 | 數量 | 落點 |
|---|---|---|
| 已自動化 | 120 | 既有的 backend `unittest`、`tests_pg`、Playwright e2e（見下方兩表） |
| 待自動化 | 3 | **本站寫出腳本並跑綠**（第二節）：`AC-A11Y.1`、`TA-01`、`TA-02` |
| 只能手動 | 7 | `manual-test-cases.md` 的 7 案（`MT-01`–`MT-07`） |
| 未分類 | 3 | `UC-01`–`UC-03`，理由見下表；**不預設丟給手動** |

### 1.1 AC（106 條故事 AC ＋ 2 條 `AC-A11Y`）

分類規則：某 AC 在任一單元的 `traceability.json` 有 `status: OK` 的條目 → 已自動化；原本沒有、由本站寫出腳本者 → 待自動化。逐故事的 AC 數（腳本計數，合計 106）：

| 故事 | AC 數 | 桶 | 主要自動化落點 |
|---|---|---|---|
| US1.1–US1.4 | 5／4／3／4 | 已自動化 | `backend/tests/test_work_orchestrator_flow.py`、`test_brain_gateway_turn.py`、`frontend/tests/e2e/entry-page.spec.ts`、`entry-page-live.spec.ts` |
| US2.1、US2.2、US3.1 | 4／3／4 | 已自動化 | `frontend/tests/e2e/entry-page.spec.ts` |
| US4.1–US4.5 | 各 3 | 已自動化 | memory-service 的 unittest、`backend/tests_pg/test_memory_service_pg.py`、`test_memory_role_ws_pg.py`、`memory-page.spec.ts` |
| US5.1、US6.1 | 3／3 | 已自動化 | `test_work_orchestrator_flow.py`、`test_followup_same_diagram.py`、`test_intent_routing_predicate.py` |
| US7.1、US8.1 | 3／4 | 已自動化 | `test_brain_gateway_fanout.py`、`test_brain_gateway_handshake.py`、`entry-page.spec.ts`、`regression.spec.ts` |
| US9.1、US9.2 | 4／3 | 已自動化 | `test_hierarchy_migration.py`、`test_describe_work_target.py`、`test_hierarchy_service.py` |
| US10.1、US10.2 | 5／4 | 已自動化 | `test_work_orchestrator_flow.py`、`test_work_orchestrator_authz.py`、`entry-page.spec.ts`（`AC10.2.4` 依 `deferred-ac-rulings.md` 的改寫後 Then 驗收） |
| US11.1–US11.4 | 各 3 | 已自動化 | `test_requirement_field_facade.py`、`test_requirement_field_http.py`、`test_mcp_bridge_e2e.py`、`project-pages.spec.ts` |
| US12.1–US12.6 | 3／4／3／4／3／3 | 已自動化 | `test_membership_endpoints.py`、`test_membership_facade.py`、`test_project_visibility_endpoints.py`、`member-pages.spec.ts` |
| US13.1 | 3 | 已自動化 | `test_progress_channel.py` |
| `AC-A11Y.2` | 1 | 已自動化 | `frontend/tests/e2e/a11y.spec.ts`（手機寬度無橫向捲動） |
| `AC-A11Y.1` | 1 | **待自動化（本站寫出）** | `frontend/tests/e2e/entry-page.spec.ts` 的「只用鍵盤即可在入口頁輸入並送出」 |

**如實揭露（分類的證據強度）**：已自動化的判定**沿用各單元 traceability 的 `OK`**，本站沒有逐條重跑每條 AC 的對應測試（全套已跑，見第三節）。其中 20 條 AC 的 `OK` 條目 `target` 指向實作檔而非測試檔（`AC1.2.4`、`AC4.1.1`–`AC4.1.3`、`AC4.2.1`–`AC4.2.3`、`AC4.3.1`–`AC4.3.3`、`AC4.4.1`–`AC4.4.3`、`AC6.1.3`、`AC12.2.2`、`AC12.2.3`、`AC12.4.3`、`AC12.4.4`、`AC12.5.1`、`AC13.1.3`）；其中 10 條（`AC1.2.4`、`AC4.1.1`–`AC4.1.3`、`AC4.2.2`、`AC4.3.1`–`AC4.3.3`、`AC4.4.2`、`AC12.4.4`）的 note 也沒有點名測試名稱。這 10 條本站**未逐條查證**其測試落點，列為第五節 open item 3。

AC 的「已自動化」只涵蓋**系統在模型回了 X 之後怎麼做**：路由層一律是替身（`FakeRouter`），`ui-regression` 的 stack 沒有任何模型金鑰。模型判斷本身的品質另列為下表的 `MT-*`，兩者不互相替代（`stories.md`「目前沒有自動化承載層的 AC」一節）。

### 1.2 其他外部可觀察行為（build-and-test 新增、LLM 與環境路徑）

| 項目 | 行為 | 桶 | 落點／理由 |
|---|---|---|---|
| `BT-01` | 存檔時帶 system_id 把新圖掛到系統；不合格系統 403／404 且不建檔（F1） | 已自動化 | `backend/tests/test_diagram_system_attach.py` |
| `BT-02` | 系統頁掛圖／改掛／取消掛載（F1） | 已自動化 | `frontend/tests/e2e/project-pages.spec.ts` |
| `BT-03` | 工作區存新圖時帶作業對象的 system_id（F1） | 已自動化 | `frontend/tests/e2e/object-picker.spec.ts` |
| `BT-04` | referent 為目前作業對象的任一表達形式時依目前對象交辦；指名不存在者仍回找不到（F2） | 已自動化 | `backend/tests/test_referent_current_target.py` |
| `BT-05` | 「那」系列指示詞（那張圖）視同目前對象（AC6.1.1 缺口） | 已自動化 | `backend/tests/test_followup_same_diagram.py` |
| `BT-06` | 失敗工作卡不再釘在對話最底（F4） | 已自動化 | `frontend/tests/e2e/entry-page.spec.ts` |
| `BT-07` | 「請記住…」確認後才寫入語意記憶；取消／取代不寫；疑似憑證／個資拒寫；fulltext 明確回錯 | 已自動化 | `backend/tests/test_brain_gateway_semantic_memory.py` |
| `BT-08` | 語意記憶寫入後本人下一輪預取讀得到、他人讀不到（真實 PG） | 已自動化 | `backend/tests_pg/test_semantic_memory_prefetch_pg.py` |
| `BT-09` | WS／編排／刪帳號的記憶存取改走 cloud360_memory 連線（MB-48） | 已自動化 | `backend/tests_pg/test_memory_role_ws_pg.py` |
| `BT-10` | 非本機未設 MEMORY_DB_PASSWORD 時刪帳號回 503 且不刪 | 已自動化 | `backend/tests/test_memory_db_session_ws.py` |
| `BT-11` | Sidebar 三個可收合群組的 nav 有可存取名稱 | 已自動化 | `frontend/tests/e2e/sidebar-landmarks.spec.ts` |
| `BT-12` | review_agent 備援句改為 provider 中立、不再只教 OPENROUTER_API_KEY | 已自動化 | `backend/tests/test_review_agent.py` |
| `BT-13` | LLM_PROVIDER=claude-code 只在 APP_ENV=local 生效；子行程不帶憑證 | 已自動化 | `backend/tests/test_claude_code_chat.py` |
| `TA-01` | 全新庫啟動時 C1 退場 rename 不記 InFailedSqlTransaction WARNING（待修 9） | 待自動化（本站寫出） | `backend/tests_pg/test_cost_schema_startup_pg.py` |
| `TA-02` | A3 review_agent 串流與 lens JSON 擷取在 claude-code 下可用（待修 4） | 待自動化（本站寫出） | `backend/tests/test_claude_code_call_sites.py` |
| `MT-01` | 真實模型把單一意圖句交給正確能力（架構設計／架構檢視／成本分析） | 只能手動 | 每跑一次花模型用量；需人判斷 |
| `MT-02` | 真實模型面對模糊句改為反問、候選合理、未答前不建工作項 | 只能手動 | 同上；候選是否合理需人判斷 |
| `MT-03` | 真實模型把一句兩件事拆成兩個工作項 | 只能手動 | 每跑一次花模型用量 |
| `MT-04` | 回歸 F2：真實模型下「這個系統」「那張圖」交辦到目前對象 | 只能手動 | 模型實際會填出哪種 referent 只有真實模型能回答 |
| `MT-05` | 回歸 F1：A1 產圖存檔後掛到系統，大腦評核找得到 | 只能手動 | A1 產圖是 LLM 路徑；e2e 樁掉 draw.io 內嵌 |
| `MT-06` | 本機 claude-code provider 以真實已登入 CLI 產出 A3 建議、APP_ENV 閘門、PATH 缺 CLI 時降級 | 只能手動 | 需登入的 `claude` CLI 與本機 `.env`（CI 永遠不會有） |
| `MT-07` | staging 部署後記憶 API 以 cloud360_memory 運作、不回 503 | 只能手動 | 部署環境狀態（secret `MEMORY_DB_PASSWORD` 是否已設） |
| `UC-01` | F8 程序記憶同內容重複寫入（兩則完全相同） | 未分類 | 預期行為未定義：需求未定「同內容合併或並存」，寫不出二元通過條件。卡在 requirements |
| `UC-02` | NFR1 意圖準確率（≥ 50 筆標註集 `M-1`） | 未分類 | `M-1` 標註集尚未產出；`MT-01` 只是抽樣，不能代替準確率量測。卡在標註集這個交付物 |
| `UC-03` | 14 個延遲數字目標（`NFR13.1` 等） | 未分類 | repo 無延遲量測機制，build-and-test 已記為 Unverified；不是手動案例能二元判定的形狀。卡在量測工具 |

## 二、本站寫出的自動化腳本（待自動化桶）

每支測試前都有 §4.4 規格註解（`@purpose`／`@given`／`@step`／`@pass`／`@story`／`@note`）。後端兩支直接呼叫服務函式或資料庫、不經 HTTP 端點也不碰頁面，依 `tcms-test-cases:c20`，`@api`／`@ui` 寧缺不造。

| 項目 | 落點與測試名稱 | 層與理由 | 斷言（缺陷回來時哪一條紅） |
|---|---|---|---|
| `AC-A11Y.1` | `frontend/tests/e2e/entry-page.spec.ts` › `U14 entry page › 只用鍵盤即可在入口頁輸入並送出` | Playwright：唯一碰得到 UI、且送真實鍵盤事件的層；axe 判不到操作性缺陷 | 從頁面起點按 Tab ≤ 60 次焦點到 `brain-input`；再 Tab 焦點到 `brain-send` 且可用；Enter 後假伺服器恰收到 1 則 `user_message` 且 `text` 等於輸入；回覆後原句與回覆可見、輸入框清空。全程不呼叫 `click()` |
| `TA-01` | `backend/tests_pg/test_cost_schema_startup_pg.py` › `CostSchemaStartupPostgresTest.test_fresh_schema_startup_logs_no_cost_rename_warning` | 真實 PostgreSQL：SQLite 的失敗敘述不會讓交易進入 aborted，放 `backend/tests/` 會得到無鑑別力的綠燈 | 前提：`pg_constraint` 恰有 `archive_cost_audit_event_pkey`、無 `cost_audit_event_pkey`；呼叫 `database._ensure_cost_schema()` 後 `cloud360.database` 的 log 中含「Cost schema」的 WARNING 為 0 筆，且完成訊息恰 1 筆 |
| `TA-02` | `backend/tests/test_claude_code_call_sites.py` › `ReviewAgentUnderClaudeCode.test_review_agent_streams_cli_text_as_suggestions`、`LensAgentUnderClaudeCode.test_lens_agent_reads_fenced_json_from_cli` | backend `unittest`，沿用 `test_claude_code_chat.FakeCliCase` 的假 `claude`（暫存目錄前置到 `PATH`、不連外） | review：串起來的 chunk 等於假 CLI 回覆、stdin 含 finding code `SEC-01`；lens：CLI 以 ```json 圍欄回覆時回傳值恰為 `{第一題: [第一個 choice]}`，不存在的題號被丟棄 |

另：既有 e2e 規格註解的機械修正（見第四節），**只改註解**，不改測試名稱與測試內容（`git diff` 中非註解行 0 行），所以 TCMS 上的既有自動化案例不會變孤兒。

## 三、實跑結果

| 套件 | 指令（副本內） | 結果 |
|---|---|---|
| 新檔 `TA-02` | `python -m unittest tests.test_claude_code_call_sites -v` | `Ran 2 tests in 1.045s` → `OK` |
| 新檔 `TA-01`（真實 PG，已套 `schema_rbac.sql`，exit 0） | `DATABASE_URL=… python -m unittest tests_pg.test_cost_schema_startup_pg -v` | `Ran 1 test in 0.043s` → `OK` |
| 後端全套 | `python -m unittest discover -s tests` | `Ran 1482 tests in 123.261s` → `OK (skipped=3)`（build-and-test 第三輪為 1480，＋本站 2） |
| e2e 新案 | `BASE_URL=http://127.0.0.1:4183 playwright test tests/e2e/entry-page.spec.ts -g '只用鍵盤'`（`vite preview` 對副本建置） | `1 passed (1.6s)` |
| e2e 受影響四支 | `entry-page`、`sidebar-landmarks`、`member-pages`、`project-pages`（`vite preview` 於 `127.0.0.1:4185`） | `111 passed (1.4m)` |
| ESLint（改動的 5 支 spec） | `eslint tests/e2e/…` | exit 0 |
| 前端建置 | `npm run build` | exit 0（既存 chunk 大小提示） |

`tests_pg` 只跑了本站新檔，未跑整個目錄（`test_memory_role_ws_pg` 需另設記憶角色密碼）；新檔只呼叫一個在已套 schema 的庫上每句皆為 no-op 的函式，不影響同目錄其他檔。

## 四、突變驗證（副本內；改回錯 → 紅 → 以 repo 檔還原 → sha256 比對）

腳本 `scratchpad/tcms-mutate.py`（後端）與 `scratchpad/tcms-mutate-e2e.py`（e2e，每次突變重建並重起 `vite preview`）。每項先斷言副本檔與 repo 檔 sha256 相同、斷言錨點字串出現次數、斷言突變後 sha256 已改變（防「突變沒生效」），還原後再比對並複跑。

| 突變 | 內容 | 結果（紅的是預期的那一條） | 還原 sha256（＝repo） | 還原後複跑 |
|---|---|---|---|---|
| MA1 | `review_agent.py`：`stream_mode="messages"` → `"values"`（只吐 state、不吐訊息） | `FAILED (errors=1)`：`RuntimeError: ReviewAgent 未產出 suggestions（模型未回覆文字）` | `10c36e1f6249296c5bbcbcbf29ac0c42d6db5993a7a499c61884bbb5e24e93f5` | `OK` |
| MA2 | `wa_lens_engine.py`：`_extract_json_payload(text)` → `json.loads(text)`（只認裸 JSON） | `FAILED (errors=1)`：`json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)` | `cd86b8a9448fd15fc050b11405beef625029c70b86ad2634a68f6598761f6557` | `OK` |
| MB1 | `database.py`：4 處 `with conn.begin_nested():` → `if True:`（回到修正前沒有 savepoint） | `FAILED (failures=1)`：`AssertionError: Lists differ: ['Cost schema index rename 略過/失敗: (psycopg…'] != []` | `7b2d0604b4b574ece57ce5eaa9ae7becbcec1a3ed9f148a7d35423703daf9495` | `OK` |
| MC1 | `BrainInput.tsx`：輸入框加 `tabIndex={-1}` | `1 failed`：`按了 60 次 Tab 仍未到達輸入框`（Received 60） | `8f2427349f9298a6ddc08a23e832f8355990f9322cb0bc69f09e74cfa4b2b321` | — |
| MC2 | `BrainInput.tsx`：送出鈕 `type="submit"` → `type="button"`（Enter 不再送出） | `1 failed`：`framesOf('user_message').length` Expected 1、Received 0 | `8f2427349f9298a6ddc08a23e832f8355990f9322cb0bc69f09e74cfa4b2b321` | 重建後 `1 passed (1.3s)` |

規格註解的修正（第五節驗證關卡的 16 項 ERROR）只改註解文字，沒有行為可突變，故不做突變驗證。

## 五、驗證關卡（`/tcms-verify`）

### 5.1 第 1 層：機械檢查

| 對象 | 指令 | 結果 |
|---|---|---|
| 本 intent 手動案例 | `python3 -B scripts/tcms_validate.py --file …/manual-test-cases.md` | `通過 7/7　ERROR 0　WARN 1` |
| 本 intent 的 10 支 e2e spec（修正前） | `--spec frontend/tests/e2e/<f>.spec.ts` 逐支 | ERROR 16（entry-page 7、entry-page-live 3、sidebar-landmarks 3、project-pages 2、member-pages 1）、WARN 8 |
| 同上（修正後） | 同上 | a11y 28/28、entry-page 63/63、entry-page-live 5/5、estimate-workspace 2/2、member-pages 20/20、memory-page 22/22、object-picker 34/34、project-pages 25/25、regression 14/14、sidebar-landmarks 3/3；**ERROR 0**、WARN 8 |
| `--all`（工具寫死的預設對象：intent `260802-last-login-column` 的手動案例 ＋ `regression.spec.ts`） | `python3 -B scripts/tcms_validate.py --all` | `通過 26/27　ERROR 1　WARN 0`——**本站無權修正，見下** |

**16 項 ERROR 的處置**：全部是既有 e2e 規格註解的「所有步驟的預期結果都沒有具體證據」或「步驟沒有預期結果」。處置是把**原本已寫出的同一個主張**改成可判定的寫法（識別字加 backtick、「沒有／不含」改「不得」、「一條／一列」改數字、補上 sidebar 第 1 步缺的預期結果「3 個名稱皆非空且互不相同」，與該案 `@pass` 及程式中的兩條 `expect` 一致），沒有新增任何測試沒有斷言的主張。

**`--all` 剩下的 1 項 ERROR（未修，阻擋，交主 session）**：`backend/.env 殘留 OpenRouter 變數時，cli 模式仍可正常取得模型回應`（intent `260802-last-login-column` 的手動案例）的追溯指向 `backend/tests/test_llm_provider.py::CliModeClearsConflictingVars`，該類別在 `origin/ut` 上存在，但被**本分支**的 commit `9781a97a`（「修正(llm): 移除已退役的 LLM_PROVIDER=cli 模式」，不在 `origin/ut`）刪除。這不是「目標在尚未合併的分支上」那一類可豁免的 ERROR，而是**本分支合併後，另一個 intent 的兩個 TCMS 手動案例（同檔第 17 行「LLM_PROVIDER=cli 時 A1 產圖可用…」與第 111 行）測的是已退役的功能**。修正需要改另一個 intent 的 record，並在 TCMS 停用那兩個案例（改標題會產生孤兒），超出本站可寫範圍。

**WARN 逐項判讀（9 項）**：

| WARN | 處置 |
|---|---|
| 手動案例「本機 LLM_PROVIDER=claude-code…」：追溯沒有標註 User story | **接受**：該功能確實沒有使用者故事（build-and-test 範圍新增 S-3，requirements 待回補 NFR）；寫一個假的故事 id 讓 WARN 消失正是這道檢查要防的事。回補後改指新 id |
| member-pages 2 項、memory-page 1 項、project-pages 3 項：OpenAPI 未宣告 500 | **接受**：這 6 個案例以攔截層讓端點回 500 模擬伺服器故障，驗的是前端的失敗呈現；未處理的 500 本來就不會出現在 OpenAPI。不是文件落差 |
| member-pages 2 項：`GET /api/membership/reselections/pending` 未宣告 403 | **真實文件落差**：端點缺 `responses=` 的 403 宣告，與合併前必修第 47 列 (c)「A3 新增的 403 未宣告於 OpenAPI」同類。列為 open item 4，不在本站改產品程式 |

### 5.2 第 2 層：語意審查（逐案七點）

七點：①目的指向會失敗的行為 ②回歸背景（症狀、錯誤逐字、自動化為何沒抓到） ③外人可執行 ④受測介面涵蓋 ⑤通過條件二元 ⑥不與自動化重複 ⑦與 AC 一致。

| 案例 | ① | ② | ③ | ④ | ⑤ | ⑥ | ⑦ |
|---|---|---|---|---|---|---|---|
| MT-01 單一意圖交辦 | 通過：失敗模式為「交錯能力或改為反問」 | 非回歸，有背景說明 CI 為何碰不到 | 通過：前置建專案／系統／掛圖步驟可照做 | 有條件通過：大腦走 `/api/brain/ws`，該 WS 不在 `openapi.json`，機械層無法列；以 UI 行承載 | 通過：三個前綴全對、log ERROR 0 筆 | 通過：自動化以替身驗「模型回了 X 之後」，本案驗「模型會不會回 X」 | 審查中修正：`AC1.1.1` 要求建立時狀態為「處理中」，已補進第 1 步 |
| MT-02 模糊句反問 | 通過 | 非回歸 | 通過 | 同 MT-01 | 有條件通過：第 2 步「候選是否重複／相關」需人判斷，已在通過條件明寫是本案唯一的判斷步驟 | 通過 | 審查中修正：`AC1.2.3` 要求「脈絡列與作業對象不變」，已補進第 4 步；`AC1.2.2` 未在本案驗，追溯改為註明由自動化承擔 |
| MT-03 多意圖拆分 | 通過 | 非回歸 | 通過 | 同 MT-01 | 審查中修正：第 2 步原寫「等待文字，或已開始處理」兩者皆可，不是二元；改為「等待中」且含「會在」「完成後開始」，並寫入通過條件 | 通過 | 修正後與 `AC5.1.1`（兩個工作項各自狀態）、`AC5.1.2`（等待中且說明在等什麼）一致 |
| MT-04 回歸 F2 | 通過：失敗模式為回「找不到名為」 | 通過：症狀、`找不到名為「系統 #1」的系統或專案。…` 逐字（取自 `brain_gateway.py:129` 的句型）、替身只回測試者心中「合理」的 referent | 通過 | 通過：UI ＋ 系統清單 API | 通過 | 通過：自動化已收錄觀察到的寫法，本案驗「模型還會填出什麼」 | 通過：`AC1.1.5`、`AC6.1.1`（第 4 步「那張圖」） |
| MT-05 回歸 F1 | 通過 | 通過：症狀、`這個系統下沒有掛上的架構圖，請在脈絡列選定圖` 逐字、fixture 直接建出已掛圖且 e2e 樁掉 draw.io | 通過 | 通過：存檔 POST 與清單 GET 皆列 | 通過 | 通過：自動化未覆蓋「真實產圖 → 存檔 → 大腦讀」整條鏈與成功提示 | 有條件通過：F1 屬 build-and-test 範圍新增，暫掛 `US9.1`，待回補新 AC |
| MT-06 本機 claude-code | 通過 | 非回歸 | 通過：含清理段 | 通過：`/assessment` ＋ 外部相依 | 通過：三項 log／畫面皆二元 | 通過：自動化用假 CLI，本案用真 CLI 與真 `.env` | 無故事（如實 WARN） |
| MT-07 部署後記憶角色 | 通過：失敗模式為部署漏設 secret 而全部降級 | 非回歸 | 有條件通過：需 staging 主機 shell 權限，已寫在前置條件 | 通過 | 通過：`1`／200／0 筆 | 通過：自動化驗程式行為，本案驗部署狀態 | 通過：`AC4.5.1`、`AC4.5.3` 的部署面 |

**結論：通過**（機械層本 intent 範圍 ERROR 0；語意層三處問題已在審查中修正並重跑機械檢查 7/7）。`--all` 的 1 項 ERROR 屬另一 intent 的案例、由本分支引起，**阻擋其中那兩個 260802 案例的現狀，不阻擋本 intent 的 7 案同步**——是否以此為由暫緩整體同步，交主 session 與使用者裁決。

## 六、open item

1. **260802 的兩個 cli 模式手動案例已失效**（見 5.1）：需在 TCMS 停用，並在該 intent 的 record 註記；本站無權修改。
2. **`ci.yml` 的 tests_pg 步驟名稱與註解未列入新檔**：`.github/workflows/ci.yml` 的步驟名稱逐項列出 tests_pg 內容（合併前必修第 33 列 (g) 要求一致），本站新增 `test_cost_schema_startup_pg.py` 後該名稱漏列一項。檔案會被 `discover -s tests_pg` 自動執行，只是名稱不一致；`ci.yml` 不在本站可寫範圍。
3. **10 條 AC 的 traceability `OK` 未指名測試**（見 1.1）：本站沿用判定、未逐條查證。
4. **`GET /api/membership/reselections/pending` 缺 403 的 OpenAPI 宣告**（見 5.1 WARN）。
5. **`TA-01`、`TA-02` 未登錄進單元 traceability**：兩者對應的是 build-and-test 待修 9 與待修 4，不屬任何既有 AC；本站只把 `AC-A11Y.1` 補進 `a11y-gate/code-generation/traceability.json`（由 `Deferred` 改 `OK`，原註記保留）。
6. **未分類 3 項**（`UC-01`–`UC-03`）：需要 requirements 決定 F8 的預期、產出 `M-1` 標註集、或引入延遲量測工具，才能落桶。
7. **新 e2e 案尚未在 CI 跑過**：TCMS 上沒有對應的自動化案例，`--spec` 同步會把它列為「找不到」（見 `tcms-sync-report.md`），需在下一次 `ui-regression` 實跑後才會由 junit plugin 建立。

## 七、repo 內快取檔數（開工 vs 收尾）

| 項目 | 開工（`2026-11-14T05:02:31Z`） | 收尾（`2026-11-14T05:21:35Z`） |
|---|---|---|
| `*.pyc`（排除 `.venv`、`node_modules`、`.git`） | 243 | 243 |
| `.hypothesis` 檔數 | 352 | 352 |

收尾另跑 `python3 -B scripts/validate_repo_contract.py` → `Cloud-360 repository contract validation passed.`；`python3 -B scripts/validate_env_contract.py` → `Cloud-360 environment configuration contract validation passed.`
