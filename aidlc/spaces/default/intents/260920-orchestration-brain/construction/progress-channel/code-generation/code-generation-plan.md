# 程式產生計畫 — `U22` `progress-channel`

> Stage：`code-generation`（3.5）　Unit：`U22` `progress-channel`（`library`，M）
> Mode：`subagent`（lead `aidlc-developer-agent`）　Depth：`Minimal`　Test strategy：`standard`
>
> **本計畫尚未核可。** Step 4（產生程式）在 Plan Approval 之後才開始；
> `plan-approval-guard` 現正擋下所有 workspace 變更。

---

## §〇 核可前請先看這一節：本計畫要替你做一個設計決定

**`U22` 的三個設計站都已有終局收據，而它們留下一個沒有設計的出口。** 這個決定無法
回到設計站做，所以它落在本計畫裡——**你在核可本計畫時就是在核可它**。

### 待決項 `B-1`：`DuplicateChannelKey` 在哪裡被接住？

`BR1.2` 要求 `open()` 對已存在的鍵拋 `DuplicateChannelKey`。`nfr-design §二` 寫它
「會被 `design_agent.py:214` 的 `except Exception` 接住」——**那是假設，不是設計**。
實測 `agent_router.py:124-128`：

```python
async def event_generator():                       # :124
    async for event in run_design_agent(...):      # :125  ← 沒有 try/except
        chunk = json.dumps(event, ensure_ascii=False)
        yield f"data: {chunk}\n\n"
return StreamingResponse(event_generator(), media_type="text/event-stream")   # :129
```

而 `functional-spec.md:34` 把 `open` 指派給**入口端**。所以該例外**不經** `:214`
——使用者得到的是一個**無聲中止的 SSE 串流**，連 `error` 事件都沒有。

**本計畫的決定（Step 7）**：在入口端把 `open()` 包進
`try/except DuplicateChannelKey`，並 yield 一個**固定訊息**的 `error` 事件後結束該請求。

| 為什麼這樣 | 依據 |
|---|---|
| 是最小的封口——不改契約、不改 `BR1.2`、不新增型別 | `K-18` 的 `public_interface` 不動 |
| 固定訊息而非例外原文 | `BR3.1`／`SEC-2`／`AC13.1.3` 的既有要求，無新決定 |
| handler 的**存在性**可 grep，故可被閘門擋 | `infrastructure-design` 審查 `R-05` 的收窄 |
| 不處理的後果是出貨一個無聲中止的串流 | 本單元存在的理由就是修三個安靜的失敗模式 |

**若你不同意這個處置**，在核可關卡選 Request Changes 並說明；它是本計畫唯一一個
「設計站沒做、由計畫代做」的決定。其餘步驟全部只是把已核可的設計與需求落地。

### 一併帶入本計畫的四項閘門發現（都是上游留下的空隙，本計畫逐一封住）

| 來源 | 空隙 | 本計畫的封法 |
|---|---|---|
| `infrastructure-design` `R-02`（`B-2`） | 閘門 1e 沒指定「呼叫點總數從哪裡來」，硬寫路徑清單則第四個呼叫點靜默逃掉 | Step 10 的測試 9：**先枚舉後逐點斷言**，不得硬寫清單；以突變 M2 驗證 |
| `infrastructure-design` `R-04`（`B-3`） | `U22-V7` 只覆蓋 2／3 呼叫點，漏 `test_agent.py:41` | Step 10 的測試 10 覆蓋**全部三個** |
| `infrastructure-design` `R-07`（`C-5`） | 我宣稱「只有 AST 層才能完整」——假的 | Step 10 的測試 12 加第二子句：`except ... as` 綁定數等於 2 且皆綁 `e`；以突變 M6 驗證 |
| `nfr-requirements` `R-01`（`C-1`） | `SEC-2` 寫 `:216` 是「唯一」洩漏點，實為兩處 | Step 6 同時改 `:103` 與 `:216`；測試 12 以形狀級檢查涵蓋 |

完整的跨單元發現清單見同目錄的 `gate-findings-consolidated.md`。

---

## §一 Testing Contract（逐字貼入，未修改）

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

### 本單元如何對應 `plan_profile.steps`

契約的 14 步是**基準排序**，允許「省略真正不適用的層而不改變 methodology」。本單元是
`library`，故逐層判定：

| 契約層 | 本單元 | 理由 |
|---|---|---|
| Project structure / production configuration skeleton | **適用**（Step 1） | 一支新模組 |
| Verify test runner ＋ 記錄 unit-scoped 指令 | **適用**（Step 2） | brownfield，驗證而非建置 |
| Data model / database behavior | **省略** | 無資料表、無持久化（`SEC-4`） |
| Repository / data access | **省略** | 不碰 DB |
| Business logic | **適用**（Steps 3–5 實作、Step 10 測試） | 通道的四個操作就是本單元的全部邏輯 |
| API / endpoint | **省略為「無新端點」**，但**既有端點的呼叫點要改**（Steps 6–8） | 本單元不新增端點；`agent_router.py` 等三處是呼叫點修改而非端點設計 |
| Frontend behavior | **省略** | 不碰前端 |
| Environment / build configuration | **省略** | 零新依賴、零環境變數、零 CI 設定變更 |
| Documentation and traceability | **適用**（Steps 11–12） | |

**methodology 未被改變**：`test-after` 的形狀是「實作該層 → 寫並跑該層的測試」，
本計畫的 Steps 3–9 實作、Step 10 寫並跑測試，順序一致。

---

## §二 計畫步驟

- [x] **Step 1 — 建立 `backend/services/progress_channel.py` 的骨架**
  模組 docstring 寫明三件事：(a) 它取代 `design_agent.py:31` 的模組層全域；
  (b) **單執行緒 asyncio 事件迴圈的前提**（`A-P2`，`nfr-design` `S-4`）；
  (c) `_admit` 是同步函式，`await` 在其中是 `SyntaxError`。
  logger 為 `logging.getLogger("cloud360.progress_channel")`（`U22-D2`，**不沿用**
  `design_agent.py:27` 的 `__name__`）。
  追溯：`U22-D1`／`U22-D2`／`U22-D3`。

- [x] **Step 2 — 驗證 runner 並記錄精確指令**
  跑 `cd backend && python -m unittest discover -s tests -v` 確認現狀全綠（這是改動前的
  基準，`scope_floor` 要求保持綠燈）。精確的 unit-scoped 指令已記於
  `unit-test-instructions.md §一`。**本步在第一個可執行測試步驟之前**（契約要求）。

- [x] **Step 3 — 實作 `ProgressEvent` 與 `RequestKey` 的形狀**
  `ProgressEvent`：`type` 限 `progress`／`xml`／`message`／`error`（沿用既有四種，
  **不改名**——改名會讓 `wa_collab_orchestrator.py:80-90` 的 remap 失效）、`content` 文字。
  `RequestKey` 為不透明字串，**本模組不鑄造它**（`U22-V5`）。
  追溯：`entities.md` 的 yaml 來源真實。

- [x] **Step 4 — 實作 `_Channel` 與私有同步 `_admit`**
  `buffer: deque[ProgressEvent]`，有限上界。`_admit(channel, event) -> None` 為
  **同步 `def`**，內含容量檢查 ＋ 丟棄 ＋ 寫入三件事，整段無 `await`
  （`[Q1]`=A／`U22-V4`／`S-4`）。
  丟棄優先序：滿載時自最舊端找第一則 `progress` 丟棄；`xml` 與 `error` **永不丟棄**；
  已無 `progress` 可丟時拒絕寫入新的 `progress` 但仍寫入 `xml`／`error`（`BR4.1`）。
  丟棄記 **WARN** log，含鍵、類別、累計丟棄數，**不含 `content`**（`BR4.2`／`SEC-3`）。
  **上界數值（`S-1`／`B-4`）**：本步**先實測**——跑一次典型產圖、記下 `progress` 實際
  則數，上界取該數的倍數，**並把測量值與倍數寫進程式註解**（`[Q1]`=A，`nfr-requirements`）。

- [x] **Step 5 — 實作 `ProgressChannelRegistry` 的四個操作**
  `open(key)`：鍵已存在即 `raise DuplicateChannelKey`，**不覆寫**（`BR1.2`）。
  `publish(key, event)`：`async def`，查表後呼叫 `_admit`；鍵不存在則記 **ERROR** log
  並丟棄該事件，**不崩潰、不靜默成功**（`BR3.2`／`U22-D6`）。
  `drain(key)`：`async def`，純同步的 `deque` 取出迴圈，**無 I/O、無 `await`**
  （`U22-V6`／`NFR3`）；鍵不存在或已關閉回**空迭代器**（`BR2.4`）。
  `close(key)`：同步、**冪等**（`BR2.2`）。
  追溯：`K-18` 的 `public_interface` 四個方法、`BR1.1`–`BR2.4`。

- [x] **Step 6 — 改 `design_agent.py`：退場五個符號並封住兩個洩漏點**
  刪除 `:31` 的 `_progress_queue`、`:32` 的 `_last_xml`、`:218` 的設 `None`；
  `:160` 的 `_drain_progress` 改寫為呼叫 `ProgressChannel.drain`；
  `run_design_agent` 新增一個承載 `request_key` 的參數，與 `thread_id` **並存且語意分離**。
  **兩個洩漏點同時改為固定字串**：`:103` 的 `return f"產圖失敗：{e}"` 與 `:216` 的
  `yield ... f"發生未預期錯誤：{e}"`；例外原文只進既有的 `logger.exception`
  （`C-1`／`SEC-2`／`AC13.1.3`）。
  **`:169` 的 `memory = MemorySaver()` 保留，本步不動它。**

- [x] **Step 7 — 改三個呼叫點，並封住 `B-1` 的出口**
  三處（`agent_router.py`、`wa_collab_orchestrator.py`、`backend/test_agent.py`）全部
  鑄造並傳入 `request_key`；鑄造用 `uuid4()` 或 `secrets.token_urlsafe()`，**禁止**遞增
  計數器／時間戳／`random`／由使用者 id 推導（`SEC-1`）。
  **並且（§〇 的決定）**：在入口端把 `open()` 包進 `try/except DuplicateChannelKey`，
  yield 一個固定訊息的 `error` 事件後結束該請求，使該例外不再造成無聲中止的串流。
  `close()` 置於 `finally`（`BR2.1`），使被中途放棄的請求也會清除鍵（`BR2.3`）。
  追溯：`U22-V3`（1e）／`U22-V7`／`S-2`／`B-1`／`B-3`。

- [x] **Step 8 — 確認 `wa_collab_orchestrator.py:80-90` 的 remap 未受影響**
  本單元不改 `ProgressEvent` 的四種 `type`，故 remap 應原樣可用；**實地確認而非假設**。
  `FR13.4`（`thread_id` 共用 `"default-thread"`）**不在本步範圍**——它是對話記憶的共用，
  與進度通道是兩回事（`OQ-P2`），本計畫刻意不夾帶那個決定。

- [x] **Step 9 — 跑一次全套測試，確認改動後既有測試仍綠**
  `cd backend && python -m unittest discover -s tests -v`，與 Step 2 的基準比對。
  **特別注意** `backend/tests/test_design_agent.py` 的既有 `@given` 測試。

- [x] **Step 10 — 寫並跑兩支測試檔（12 個測試）＋ 六項突變驗證**
  `backend/tests/test_progress_channel.py`（7 個行為測試）與
  `backend/tests/test_progress_channel_contract.py`（5 個契約閘門）。
  清單、斷言、追溯與六項突變（M1–M6）逐項見 `unit-test-instructions.md §二`／`§三`。
  **測試 9 必須先枚舉呼叫點再逐點斷言**（不得硬寫路徑清單，`B-2`）；
  **測試 12 必須含第二子句**（`except ... as` 綁定數等於 2 且皆綁 `e`，`C-5`）。
  突變驗證結果（含突變內容與紅燈訊息）寫進 `code-summary.md`。

- [x] **Step 11 — 寫 `code-summary.md`**
  含：改動檔清單、12 個測試的執行結果、六項突變的結果、以及**誠實記載本單元未能關閉的
  項目**（`S-10` 形狀級檢查對未來不完整、`U4` 那類 CI 承載者缺口不適用於本單元）。

- [x] **Step 12 — 寫 `traceability.json`**
  枚舉 `AC13.1.1`–`AC13.1.3`、`BR1.1`–`BR5.2`、`SEC-1`–`SEC-4`、`U22-V1`–`U22-V7`，
  各自對應到具體的程式位置與測試。

---

## §三 故事 ↔ 程式步驟追溯

| 使用者故事／AC | 計畫步驟 |
|---|---|
| `US13.1` — 我的架構圖只給我 | Steps 3–7（全部實作） |
| `AC13.1.1` 兩請求事件互斥且各自非空 | Steps 4–5（隔離結構）、Step 10 測試 1 |
| `AC13.1.2` 先結束者不得使另一個失去通道 | Step 5（`close` 只移除自己的鍵）、Step 10 測試 2／6 |
| `AC13.1.3` 回應不含內部例外原文 | Step 6（兩個洩漏點）、Step 7（`B-1` 的固定訊息）、Step 10 測試 12 |
| US13 DoD — 鍵必須 per-request | Step 7（三處鑄造） |
| US13 DoD — `asyncio.Event` barrier，不得用 `sleep` | Step 10 測試 1／2 |
| US13 DoD — 三個模組層可變狀態一併清理 | Step 6 |
| US13 DoD — `wa_collab_orchestrator` 補傳鍵 | Step 7 |

---

## §四 不在本計畫範圍（如實記載）

| 項 | 理由 |
|---|---|
| `FR13.4` 的 `thread_id` 分區語意與 `MemorySaver()` 單例 | 與進度通道是兩回事（`OQ-P2`）；本計畫刻意不夾帶 |
| SSE／WebSocket 的重連與補事件協定 | `[Q3]`=A 已定 `drain` 為破壞性、不重播；對外協定屬 `U13` |
| `A-1`（`DEPLOY.md` 遷移程序連不上資料庫） | 是 `hierarchy-data` 的缺陷，非本單元 |
| `A-2`（77 處失效行號） | 跨單元文件缺陷，非本單元的程式工作 |
| `C-2`／`C-7`／`C-9`–`C-17` | 其他單元的凍結產出缺陷，見 `gate-findings-consolidated.md` |

---

## §四之一 code-generation Request Changes（2026-10-20）的對照結果

使用者對整站送出 Request Changes，要求修正 `construction/functional-design/merge-blockers.md` 的 19 項合併前必修，各在所屬單元修正並附測試。逐項對照該表「單元」欄：**19 項中沒有一項劃給 `progress-channel`**（第 18 項的單元欄為 `session-store／work-orchestrator`，與本單元無關）。另以本單元交付的檔案（`backend/services/progress_channel.py` 等，見 `source-manifest.json`）反查各項的修法落點，亦無一項需要改動本單元的檔案。

因此本計畫**不新增步驟**；既有 12 格步驟維持原樣（已全部完成）。本輪的工作是：依現況重新查驗 12 格仍成立、以 `backend/.venv` 跑本單元測試與完整後端套件，結果附加於 `code-summary.md`。

---

## §五 Plan Approval

本計畫 ＋ 其中逐字貼入的 Testing Contract ＋ `unit-test-instructions.md` 三者一併送核。

**核可即同時核可 §〇 的 `B-1` 設計決定**（入口端 `try/except DuplicateChannelKey`
＋ 固定訊息的 `error` 事件）。

核可的作答落在 `code-generation-questions.md` 的 Plan Approval 區塊，不在本檔。
