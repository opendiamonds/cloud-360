**Collaborator:** aidlc-developer-agent

## Contribution

本檔的每一項事實都是本輪實際開檔讀出的（`[讀]`），不轉引 codekb 的 `[簽]`／`[未驗]`
標記。計數類（308 列、49 條 FR、12 個 `path=`）皆以腳本或 `grep -c` 實算，不目測。

---

### 1. 回答問題一：AC9.1.2／AC9.1.3 目前在每個自動化環境都不可達，在 staging 上的失敗是靜默的

**兩個環境走的是不同的 schema 路徑，而 CI 驗的那一條 staging 永遠不走。**

- `deploy/docker-compose.test.yml:20–22` 把 `schema_rbac.sql` 掛成 initdb 腳本，且檔頭
  第 5 行逐字寫「The database is created fresh every run (no volume)」、第 22 行
  「No host port and no named volume: isolated and disposable」。所以 `ui-regression`
  每個 PR 跑的是 **`schema_rbac.sql` 那條路**。
- staging 有具名 volume，`schema_rbac.sql` 只在空 volume 執行，既有環境的唯一演進路徑
  是 `backend/database.py` 的 `init_db()` → 6 支 `_ensure_*` 補丁（`:74–83`）。
- backend unittest **完全不執行** `_ensure_*`：`backend/tests/helpers.py:29–38` 以
  `Base.metadata.create_all` 直接在 in-memory SQLite 建表。
- 這個失敗模式 repo 自己已經寫下來了。`backend/database.py:504–511` 的
  `_ensure_last_activity_schema` docstring **逐字**：「**不補則 staging 上每個已認證的
  請求都會失敗，而 CI 全綠** —— 測試以 in-memory SQLite 直接建表、從不經過本流程。」

**AC9.1.2 的 Given 在自動化層不可達。** 「我有一張在本 intent 之前建立的架構圖」需要
帶既有資料的資料庫：`ui-regression` 的 DB 每次重建、`APP_ENV=test` 的 seed 只建
admin／admin123（`docker-compose.test.yml:5–7`）、零 diagram；unittest 的 SQLite 每個
test 自建自毀。所以 AC9.1.2 現在的形狀是「在新環境恆真、在 staging 才第一次被驗」。

**遷移的機械形狀，以及它為什麼會靜默失敗。** `backend/models.py:95` 的
`user_diagrams.user_id` 為 `nullable=False`。新增 `system_id` 若要 NOT NULL，PostgreSQL
在非空表上不能一步完成。本 repo 的**唯一**前例在
`backend/database.py:403–415`（`_ensure_estimate_intake_schema`）：

1. `ALTER TABLE estimate_sets ADD COLUMN IF NOT EXISTS is_saved BOOLEAN`
2. `UPDATE estimate_sets SET is_saved = TRUE WHERE is_saved IS NULL`
3. `ALTER TABLE estimate_sets ALTER COLUMN is_saved SET NOT NULL`

三句在同一個 `statements` 清單裡，逐句 `except Exception as e: logger.warning(...)`
（`:497–501`）。因此第 2 步（回填）失敗 → 第 3 步跟著失敗 → 欄位留在 nullable 且含
NULL → 服務照常啟動、healthcheck 綠、AC9.1.2 靜默不成立。注意 `create_all`（`:76`）
在 try 之外，**建新表失敗會大聲**；只有 ALTER／回填是靜默的。

**給 lead 的三條具體修法（可直接折入 US9.1）**

- **US9.1 增一條 AC（建議 AC9.1.4）**：遷移執行後，`user_diagrams` 中
  `system_id IS NULL` 的列數為 **0**，且該不變量在啟動時被檢查、不成立時**大聲失敗**
  （不是 `logger.warning`）。這把 AC9.1.2 從「逐圖人工觀察」改成單一查詢即可判定。
- **AC9.1.2 就地註明它的 Given 只在帶既有資料的環境可達**，並在 DoD 指明唯一驗證路徑
  是部署後人工核對。形狀直接沿用 `backend/database.py:536–599`
  的 `_apply_security_reviewer_j3a_view`——它是本 repo **唯一**的「既有環境一次性資料
  遷移」前例，帶識別字（`J3A_PATCH_MARKER`，`:534`）與四態日誌，其 docstring 逐字寫
  「部署後人工核對是本變更唯一的驗證方式」。US9.1 的遷移應沿用它，不要新造一套。
- **若決定 `system_id` 可為 NULL**，AC9.1.2 的「歸屬於某個系統」在 schema 層就沒有強制
  力，必須由上述不變量承載——不能兩者都不要。這個選擇由 `domain-design` 做，但
  **AC9.1.2 的可驗證性取決於它**，所以本站要把這個相依性寫進故事旁邊。

---

### 2. 回答問題二：AC8.1.4 的「不變」不是免費的——四個共用機制，其中兩個會真的咬到

**(a) nginx 只有一個 `location /api/`。** `frontend/nginx.conf:16–32` 是唯一帶
`proxy_set_header Upgrade` 與 `Connection $connection_upgrade` 的 block，而它同時服務
5 個 SSE 端點、既有 collab WS 與新 WS，共用同一組 `proxy_read_timeout 600s`／
`proxy_send_timeout 600s`／`proxy_buffering off`。US7.1 的推播連線可能長時間無流量；
若新 WS 需要不同的 idle 上限，改的是**所有** SSE 端點也吃到的那一行。替代做法是加一個
更長前綴的 `location /api/<brain>/`（nginx 取最長前綴），但該 block 必須逐項重抄
`Upgrade`／`Connection`／三個 `X-Forwarded-*`／`proxy_buffering off`——漏抄任一項都是
無聲降級。**兩條路都不是「不變」。** → 建議 US8 的 DoD 增一條：WS 落點選定時須同時
說明它落在哪個 nginx location，以及該選擇對既有 5 個 SSE 的影響為零的理由。

**(b) 單行程單事件迴圈——這一項會讓 AC8.1.4 在沒人動過 `collab_router.py` 的情況下失敗。**
`backend/Dockerfile:36` 的 `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]`
無 `--workers`。WebSocket handler 必為 `async def`，跑在與 5 個 SSE generator、既有
collab WS 同一個 event loop 上。本 repo 唯一的 LangGraph 前例是**同步**的：
`backend/services/langgraph_runtime.py` 的 `invoke_graph` 直呼 `graph.invoke`，消費者
`backend/cost/cost_advice_agent.py:156`——而它之所以不卡 loop，只因為
`advice_orchestrator` 把它丟進 `ThreadPoolExecutor`。若大腦照抄這個同步 `invoke` 而直接
寫在 WS coroutine 裡，NFR3 的「首字 2 秒」就等於**每則訊息 2 秒的 loop 阻塞**：
`collab_router.py:283` 的 `manager.broadcast` 與 5 個 SSE 的心跳在那段時間全部停住。
附帶修正一個容易走錯的方向：codekb 約束五說的 `astream_graph` 確實存在
（`langgraph_runtime.py:133–149`）但**零消費者**，所以「照既有前例做」在這一點上恰好
是錯的那條路。 → 建議 US8 增 DoD：大腦的 LLM 呼叫不得在 event loop 上同步執行，且
須有可觀察的驗收（大腦處理中時 collab 廣播的延遲不變）。

**(c) `advice_orchestrator` 的 2 槽池，US10.1 讓大腦成為它的第二個生產者。**
`backend/cost/advice_orchestrator.py:20` 的 `_MAX_WORKERS = 2` 是模組層全域，而 NFR4
明確把它排除在外部化之外。更關鍵的是：`started_at` 在 **submit 當下**就寫入
（`:311`、`:341`，緊接 `:347` 的 `_get_executor().submit(_job, ...)`），而
`reclaim_stale_generating` 以 `started_at` 比 `TIMEOUT = timedelta(minutes=5)`
（`:19`、`:125`、`:266`）——**排在佇列裡的 job 時鐘已經在跑**。兩件大腦發起的成本工作
佔滿池子超過 5 分鐘，第三件（很可能來自直接使用 `/cost` 頁的人）會在**從未執行**的
情況下被標成逾時。AC10.2.1／AC10.2.2 會「通過」（訊息確實可見、確實可區分），但它報的
是錯的事。這是既有使用者行為被本 intent 改變，而 US10 沒有任何 AC 或依賴涵蓋它。
→ 建議 US10.2 增一條 AC 或 US10 的 DoD：大腦發起的成本工作不得使直接由 `/cost` 頁
發起的工作進入「未執行即逾時」的狀態。

**(d) `configure_provider_env()` 的行程級改寫——實際風險比 codekb 暗示的低，但判準必須寫下來。**
我實讀了變數清單：`backend/services/llm_provider.py:56–70` 的
`_CLI_CONFLICTING_VARS` 只含 `ANTHROPIC_BASE_URL`／`ANTHROPIC_AUTH_TOKEN`／
`ANTHROPIC_API_KEY` 與三個 `ANTHROPIC_DEFAULT_*_MODEL`，**不含 `OPENROUTER_API_KEY`**；
而 `langgraph_runtime.openrouter_chat_model()`（`:73–99`）把 `api_key` 顯式傳進
`ChatOpenAI`、不讀行程環境。所以只要大腦的第三份客戶端沿用「顯式傳 key」的形狀，
這條耦合不會咬到它。**會咬到的只有一種寫法**：大腦改走 `claude-agent-sdk`（路徑 A）或
任何讀 `ANTHROPIC_*` 的客戶端——那時每一個 A1／A3 請求
（`backend/services/agent_router.py:73–77` 的 `_ensure_llm_keys()`，在 `:120` 與 `:152`
各呼叫一次）都會在大腦跑到一半時改寫它的環境，且 `_configure_openrouter_env` 會把
`ANTHROPIC_API_KEY` 設成空字串（`:138`）。 → 建議把這個**判準**寫進 US8 的 DoD 一行，
而不是原樣轉抄 codekb 的耦合警告：**大腦的 LLM 客戶端必須顯式傳入認證，不得讀行程
環境**；符合此條則 AC8.1.4 對這一項成立。

---

### 3. 依賴表：一條列錯、三條缺席，且全表未區分「同批次」

`project.md` 的 `delivery-planning:c6` 明寫 deploy-on-merge 之下存在一條「比 DAG 邊更強」
的同批次約束。現表逐列都標「技術依賴」，沒有任何一列標同批次，而下面兩處實際是同批次。

**(a) 列錯：US6.1 → US4.1 不是真依賴。** AC6.1.1 講的是「第一輪產出 → 第二輪用指涉詞」
——同一段對話內的**第 N−1 輪**。那份歷程依 NFR4 逐字「大腦的 session 與工作狀態一律放
Redis」，屬 session 狀態；而 US4.1 承載的是 FR4.1／FR4.2 的三種記憶（episodic 為
by-user、落在 PostgreSQL 的獨立 schema）。把 US6.1 掛在 US4.1 之後，等於讓多輪指涉
去等一整個 epic 級的記憶層，而它只需要 Redis session。 → 建議把這條邊改為
US6.1 → US2.1（session／脈絡的載體）或 US8.1，並在該列註明理由。

**(b) 缺席且最嚴重：US1.4 全表無列，US1.1 的 INVEST 還逐字寫「Independent（不依賴其他
US1.* 故事）」。US1.4 單獨上線會產生空白畫面。** `frontend/src/App.tsx:18–28` 的
`DefaultRedirect` 是一串 `<Navigate>`；`/`（`:126`）與 `*`（`:134`）**都**渲染它。
US1.4 單獨交付＝seed 多一個 story id、`DefaultRedirect` 多一條分支把持有者導向一個
**沒有對應 `<Route>` 的路徑** → 落到 `*` → 再渲染 `DefaultRedirect` → 再導向同一個
路徑。使用者看到空白，而 AC1.4.3 要保護的 `/403` 那條根本到不了。
→ 依賴表要加「US1.4 依賴 US1.1（入口頁本體與其 `<Route>`）」，**並標為同批次**。
同時 US1.1 的 INVEST 那句「不依賴其他 US1.* 故事」要改寫——它現在是雙向錯：US1.4 依賴
它，而它自己也依賴 US8.1（見下）。

**(c) 缺席：US9.2 → US9.1 在 NOT NULL 下是同批次，不只是排序。** 遷移會為既有圖回填
系統，既有使用者不受影響；但**遷移之後才註冊的新帳號沒有任何專案／系統**，在 US9.2
上線前無法建立第一張圖（`user_diagrams` 需要一個 `system_id`）。兩者分兩個 Bolt 上線
＝新帳號在中間那段時間完全不能用 `/workspace`。 → 該列補註「若 `system_id` 為 NOT NULL
則為同批次約束」。

**(d) 缺席：US1.1／US1.3／US5.1 → US8.1 三條邊。** 工作項的狀態**怎麼到瀏覽器**，全檔
沒有任何 AC 或依賴指定。AC1.1.1（工作項出現且為 `處理中`）、AC1.1.2（五個狀態值）、
AC5.1.2（`等待中` 並說明在等什麼）、AC1.3.1（轉為 `已停掉`）全都是**推送**才看得到的
狀態變化；而 FR7.2 逐字說推播通道即 FR8 的 WebSocket、NFR4 說工作狀態在 Redis。表裡
卻只有 US7.1 → US8.1 這一條 WS 邊——同一個事實（WS 是通道）套用到 US7 而沒套用到
US1／US5。 → 要嘛補這三條邊，要嘛在 US1 就地寫明工作項狀態的取得方式是輪詢（那就得
說明它與 NFR3 的關係）。兩者皆可，但不能留空。

---

### 4. 故事尺寸：US4.1 是 epic，且 US4 的切分軸與 US1 用的不是同一把尺

U4 的定案理由是「FR1 的 8 條子需求塞一則必然超過 3–6 條 AC 上限」→ 拆四則。用同一把尺
量 FR4：實算子需求為 **10 條**（FR4.1、4.2、4.3、4.3a、4.3b、4.4、4.5、4.5a、4.6、4.7），
只拆成 **3 則、共 10 條 AC**。

US4.1 那一則獨佔本 intent **最沒有前例**的三件事：

- FR4.2 的「同一 DB、獨立 schema」：全樹零 `CREATE SCHEMA`、零 `search_path`
  （我實算複驗成立），而 `backend/tests/helpers.py:29–38` 的測試路徑是 in-memory
  SQLite，**SQLite 沒有 schema 概念**——這條在現有測試基礎設施上零驗證路徑，NFR6 因此
  要求一支全新的真 PostgreSQL CI job。
- FR4.4 的 grant 邊界（見下，目前**零承載**）。
- FR4.3／4.3a／4.3b 的寫入端授權語意。

再加上 AC4.1.1「系統的回覆反映出它取得了那項先前資訊」**本身就是一整套檢索子系統**。
這不是 1–5 天；對照 US9.2（建立專案與系統，約 1–2 天）差了一個量級。AC 數在這裡
**遮住**了尺寸而不是揭露它——困難集中在單一條 AC 的內部，沒有攤成多條。

→ 建議拆成三則，理由是它們的**驗證方式與失敗模式不同類**（`project.md`
`units-generation:c6` 的判準）：

| 建議故事 | 承載 | 驗收面／落點 |
|---|---|---|
| US4.1a 記憶的儲存與隔離 | FR4.1、FR4.2、FR4.4 | schema 建立、grant 邊界、跨 schema 查詢；落點即 NFR6 的 PG CI job |
| US4.1b 記憶的寫入端授權語意 | FR4.3、FR4.3a、FR4.3b | 擁有者不可由呼叫方指定、預設最窄、放寬須授權且留稽核（現 AC4.1.2／4.1.3／4.1.4 原樣移入） |
| US4.1c 記憶的檢索與脈絡組裝 | FR4.1 的消費面 | 回覆反映先前資訊 ＋ 只取得有權讀的部分（現 AC4.1.1 移入） |

拆後 US4 為 5 則，全群 AC 數不變，但「這一則完成了嗎」對每一則都變成單一判準。

---

### 5. 四條 FR 在 `stories.md` 零引用（機械核對，非目測）

以 `requirements.md` 定義的 **49 條 FR 子需求**對 `stories.md` 做全檔 regex 比對，
四條零命中：**FR4.4、FR8.3、FR9.4、FR10.3**。

- **FR9.4**（跨雲分析不納入）合理無故事，是排除項——但建議在 US9 就地註明，否則
  traceability 會讀成漏。
- **FR8.3**（WS 必須掛 `/api/` 之下）是機制約束，落點應是 DoD——但**US8 全群沒有
  Definition of Done 段落**（US1 與 US4.2 有）。FR8.3 目前沒有任何容器。
- **FR10.3**（稽核的行為主體是使用者本人，不是大腦）**是外部可觀察的**，而且是
  ADR-0006 audit logging 面向在 US10 的唯一落點。一個把大腦記成行為主體的實作會通過
  US10 現有全部 8 條 AC。 → 建議 US10.1 增一條 AC：大腦代為呼叫成本能力之後，
  `estimate_audit_events` 記錄的行為主體是該使用者本人，不是大腦或服務帳號。
- **FR4.4**（grant 只開放記憶 schema）是 ADR-0006 IAM 面向；NFR6 的 PG CI job 已逐字
  涵蓋「grant 邊界」，所以它**有**驗證路徑、只是沒有故事或 DoD 容器。 → 掛進上面
  拆出的 US4.1a 的 DoD。

另：**NFR3／5／6／7／8／9／10 七條在 `stories.md` 零引用**。U5＝A 定的「逐條判定、
三種狀態並用」要落在 `traceability.json`，而本 stage 目錄下目前沒有那個檔。其中
NFR7 實際上已被 AC4.2.2／AC4.2.3 涵蓋（90 天 ＋ 刪除稽核）卻沒掛 id，會被讀成未覆蓋。

---

### 6. US1 的 DoD 有一項是已解決的、少一項是真的沒機制

**(a) 可以刪掉一項顧慮：`ensure_role_permissions_seeded(force=False)` 的 no-op 陷阱已有
機制。** `project.md` 的 `application-design:c21` 教訓要求「另做只插入缺失的 ensure」
——那支**已經存在並且已經接在啟動路徑上**：`backend/services/rbac.py:84` 的
`ensure_missing_role_permissions()`（docstring 逐字「只 INSERT 缺失的 (role, story_id)；
不 UPDATE／DELETE 既有列」），由 `backend/database.py:168–172` 在 `init_db()` 內
**無條件**呼叫。所以 US1.4 新增一個 story id 在既有 staging 上會自動補齊 11 列
（11 個角色）。DoD 不必再列這一項，列了會讓人重做已有的東西。

**(b) 但 DoD 少了一項真的沒有機制的：`schema_rbac.sql` 的 seed 是 308 列逐字硬寫的
副本，且沒有任何測試鎖住它。** `schema_rbac.sql:320` 是裸的
`DELETE FROM role_permissions;`，`:322` 起的 `INSERT` 我實算為 **308 列**；
`backend/services/rbac_seed_data.py` 的 `DEFAULT_ROLE_PERMISSIONS` 我實算同為 **308 列
＝ 11 角色 × 28 story**。`backend/tests/` 中唯一提到 `schema_rbac.sql` 的是
`test_j3a_view_permission.py`，而它只在 docstring 提及、**不解析該檔**。而
`backend/tests/helpers.py:38` 用 `ensure_role_permissions_seeded(db, force=True)`，
也就是**全部測試看到的都是 Python 那一份**。

結論（建議逐字寫進 US1 的 DoD）：US1.4 的 allow/deny 雙向測試（`team.md` A 規則）
**不構成** `schema_rbac.sql` 已同步的證據，兩者是互相獨立的義務；新增 story id 需在
該 SQL 手寫 11 列（308 → 319）。並建議同一個 PR 補一支比對兩份 seed 的測試——
`team.md` 的「單一真實來源」規則對新增副本要求鎖一致性的測試，這裡是**既有**副本，
但我們正要動它。

---

### 7. 三條可以現在就補精確度的 AC（低成本、高回報）

**(a) AC8.1.2 目前可以用「只在握手時記一次」滿足，而那正好是它要修的病。**
既有前例 `backend/services/collab_router.py:257` 用 `record=False` 跳過記錄；改成
`record=True` 後，WS 的**握手**會走 `get_user_from_token` → `record_activity`
（`backend/services/auth.py:80–83`、`backend/services/activity.py:112`，5 分鐘節流），
但握手之後同一條連線上的每一則訊息**不會**再經過那條路徑。一個開著大腦連線工作三小時
的人，`users.last_activity_at` 停在三小時前。AC8.1.2 寫「經由大腦互動過 → 已更新」，
握手即滿足，而它要防的無聲失效原樣留著。
→ 改寫為：大腦連線上的**每一則使用者訊息**都觸發一次活動記錄判定（仍受既有 5 分鐘
節流）；可觀察的 Then 為「連線已開啟超過節流視窗後再送一則訊息，該時間會前進」。

**(b) AC8.1.3 可以用「握手後首則訊息認證」滿足，而那條路會產生既有前例沒有的暴露面。**
瀏覽器 `WebSocket` API 不能設任意標頭，能設的只有 subprotocol；`requirements.md` 的
A-1 已登記「nginx／cloudflared 是否透傳 `Sec-WebSocket-Protocol` 本輪未查證」（我本輪
也只確認 `nginx.conf:21–22` 設了 `Upgrade`／`Connection`，未涵蓋其他握手標頭）。若改走
首則訊息，`websocket.accept()` 必須發生在認證**之前**——而既有前例的形狀恰好相反：
`collab_router.py:267–275` 先認證，失敗就以 1008／1003 `close`，**從不 accept**。於是
未認證的客戶端可以開著連線不送訊息。
→ US8 增一條 AC 或 DoD：若採握手後認證，未在 N 秒內完成認證的連線必須被關閉；並在
AC8.1.3 就地寫明兩種實作各自的可觀察結果。

**(c) AC1.1.3（prompt_guard）在多輪對話下會靜默弱化。** 既有呼叫點傳的是
`latest_user_text(payload)`，而該函式（`backend/services/prompt_guard.py:51–63`）串接
**最近三則** user 訊息（`return "\n".join(parts[-3:])`）——既有防護本來就有一個三輪
視窗。大腦的訊息歷程在 Redis 而不在請求 body 裡（NFR4），若實作只把當下那一則 WS
訊息餵給 guard，視窗就從 3 縮成 1，而 AC1.1.3 只測單則輸入、照樣通過。這與 codekb
約束三（照抄 `record=False`）是**同一個形狀**的錯誤：沿用既有機制時副作用沒被寫下來。
→ AC1.1.3 補上「檢查的輸入為與既有路徑相同的至少三輪 user 訊息窗」，或寫進 US1 的 DoD。

---

### 8. 兩項可以順手收掉的小事

- **AC2.1.3 的排除必須是 Layout 內的路由感知抑制，不是「不放進 Layout」。**
  `frontend/src/components/Layout.tsx` 包住**全部 6 個內容頁**（`App.tsx:47–122`），
  含 `/cost` 與三個 `/admin/*`。好消息是前例已存在：`Layout.tsx:16` 有
  `<div data-slot="cost-banner" />`，搭配 `frontend/src/cost/slotRegistry.tsx` 的
  slot 機制（`type SlotName = 'cost-overspend' | 'cost-banner'`）。脈絡列沿用該 slot
  形狀即可，不需新抽象。這條寫進 US2 的 DoD 比留給實作猜好。
- **M-3 的基準值有兩個問題。** 其一：`frontend/src/App.tsx` 實際有 **12 個 `path=`**，
  其中 1 個是 `*` catch-all（`:134`）、1 個是純轉址（`:124`，`/admin` → `/admin/users`）。
  `requirements.md` 與 M-3 寫的「現行 11 條路由」等於「12 減去 catch-all」——排除規則
  沒寫下來，兩個人清點會得到不同的數字。其二：基準必須在**第一個新增路由的 Bolt 合併
  之前**取得——deploy-on-merge 之下 `ut` 上就不再有「現行 UI」可清點。建議 M-3 就地
  記下取基準的 commit sha 與排除規則。

## Positions

- AGREE: US1 拆四則的接縫正確 — 四則各自對應不同的失敗模式（交辦成功／判不出來／判錯／權限落點），而 U4 選項 D 被否決也是對的：`frontend/src/App.tsx:18–28` 的 `DefaultRedirect` 確認「無權限的入口頁」在機制上不可達。
- AGREE: AC1.2.4 獨立成條與 AC6.1.3 的負向驗收是本檔最有價值的兩處設計 — 兩者都把「靜默永不觸發」與「邊界由實作自行決定」變成可失敗的斷言。
- AGREE: M-1／M-2／M-3 不寫成故事 — 它們沒有 persona，硬套 `As a [persona]` 會產生反樣式，而給非 `US` id 讓 `delivery-planning` 看得到工作量是對的取捨。
- AGREE: FR8.2 引用的「既有 5 個 SSE 端點」數字正確 — 我實數為 5（`/generate`、`/generate-wa-collab`、`POST /reviews`、`POST /reviews/{id}/retry-suggestions`、`/sets/{id}/advice/stream`），AC8.1.4 的範圍陳述沒有問題。
- OBJECT: US4.1 是 epic，且 US4 沒有套用 US1 用的同一把尺 — FR4 的 10 條子需求只拆 3 則（FR1 的 8 條拆 4 則），而 US4.1 獨佔獨立 schema、grant 邊界與整套檢索，AC 數在這裡遮住了尺寸；建議拆為 US4.1a／4.1b／4.1c，判準是驗證方式與失敗模式不同類。
- OBJECT: AC9.1.2／AC9.1.3 不可驗證 — Given 在每個自動化環境都不可達（CI 走 `schema_rbac.sql`、DB 每次重建、零既有 diagram），而 staging 走的 `_ensure_*` 路徑逐句 `logger.warning` 吞掉失敗；需要一條二元可判的遷移不變量（`system_id IS NULL` 列數為 0）並在不成立時大聲失敗。
- OBJECT: AC8.1.4 寫成無條件斷言，但它依賴四個未被任何 AC 或 DoD 約束的共用機制 — 至少「LLM 呼叫不得在 event loop 上同步執行」與「nginx location 的選擇及其對 5 個 SSE 的影響」兩項必須升為顯性交付條件，否則既有共編會在沒人動過 `collab_router.py` 的情況下退化。
- OBJECT: 依賴表一條列錯、三條缺席、全表未區分同批次 — US6.1 → US4.1 不是真依賴（多輪指涉要的是 Redis session，不是 PostgreSQL 記憶層）；US1.4 全表無列卻會在單獨上線時產生空白畫面；US9.2 → US9.1 在 NOT NULL 下是同批次；US1.1／US1.3／US5.1 → US8.1 三條邊缺席。
- OBJECT: FR10.3 與 FR4.4 零承載 — 兩者都是 ADR-0006 的具名面向（audit logging／IAM）、都可驗證（前者外部可觀察、後者已在 NFR6 的 PG CI job 範圍內），不能只靠 traceability 記 Deferred 帶過；FR8.3 也無容器，因為 US8 全群沒有 Definition of Done 段落。
- OBJECT: US10 完全沒有涵蓋大腦對 2 槽 job 池的擠壓 — `_MAX_WORKERS = 2` 且 `started_at` 在 submit 當下就寫入、5 分鐘逾時據此計算，因此大腦成為第二個生產者後，直接由 `/cost` 頁發起的工作可能在從未執行的情況下被標成逾時；AC10.2.1／AC10.2.2 會通過但報的是錯的事。
- OBJECT（不在本席 lane，僅點出）: US1 的 DoD 有一項是已解決的顧慮（`ensure_missing_role_permissions` 已存在且已接在 `init_db()` 上），卻少了一項真的沒有機制的（`schema_rbac.sql` 的 308 列 seed 與 `rbac_seed_data.py` 的副本無任何測試鎖住，而 allow/deny 測試因 `force=True` 只看得到 Python 那一份）。
