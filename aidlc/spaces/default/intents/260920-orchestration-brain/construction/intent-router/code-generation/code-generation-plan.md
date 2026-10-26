# Code Generation Plan — `U11 intent-router`

> 方法論 **test-after**、策略 **standard**（每元件 5–8 測試）、專案型態 **brownfield**。
> 三者皆來自本檔末尾的 Testing Contract（由 `aidlc-testing-posture.ts render`
> **原樣貼入，未經編輯**）——**Part 2 以它為準，subagent 不得重新解讀 memory 層**。

## 零、這個單元要做什麼（一段話）

把一句使用者自然語言變成 `IntentDecision`：先過 `prompt_guard`，讀該段的作業對象
與歷程（＋語意／程序記憶），組出最少上下文的 prompt，對 `typesafe/jev-1.13` 發出
**恰一次** tool call 取得**扁平的候選陣列 ＋ `slot` 索引**，在我方還原成槽位兩層
結構並跑五道驗證，最後對每個槽位求 `can_single_out`、以 AND 聚合成整句判定。

**本單元不建立任何 HTTP 端點、不寫任何持久層、不建立工作項。**

## 一、模組配置（七個新檔，全部在 `backend/services/`）

| 模組 | 層 | 純度 | 職責 |
|---|---|---|---|
| `intent_routing_types.py` | — | 純（frozen dataclass） | `CandidateIntent`／`CandidateRanking`／`ClassificationResult`／`Intent`／`ClarifyCandidate`／`IntentDecision`／`RoutingObservation` |
| `intent_routing_errors.py` | — | 純 | `LlmUnavailable`／`LlmBudgetExceeded`／`EmptyCandidates`／`MalformedRouting` |
| `intent_routing_config.py` | — | 純（讀 env） | 五個 `BRAIN_ROUTER_*` 變數；`CONFIDENCE_THRESHOLD` **required-no-default** |
| `intent_routing_predicate.py` | **L5** | **純** | `can_single_out`、`BR4.2` AND 聚合、`EC7` 基數、`EC8` 攤平 ← **ADR-0006 PBT 落點** |
| `intent_routing_parser.py` | **L4** | **純** | 扁平 → 兩層；`V-1`～`V-5` |
| `intent_routing_context.py` | **L2** | **純** | prompt 組裝；**簽章不接受 `BrainSession`** |
| `intent_routing_port.py` | **L3** | 不純 | `router_chat_model` factory ＋ 單節點 `StateGraph` ＋ tool schema |
| `intent_routing.py` | **L0＋L1 編排** | 不純 | `IntentRouter.classify(principal, session, text)`；L0 的讀取 I/O 在此 |

**檔名刻意不用 `_router.py` 字尾**（審查 `R-10`）：`team.md` 的既成慣例裡該字尾
專指「建立 `APIRouter` 並被 `main.py` include」的 HTTP 路由模組，而本單元的 `SEC-2`
明寫它**沒有** `APIRouter`。類別名 `IntentRouter` 維持不變（`K-10` 契約）。

## 二、實作步驟（test-after：每層實作完成後，寫並跑該層的測試）

### Step 1 — 專案結構與設定骨架

- [x] 建 `intent_routing_types.py`：七個 frozen dataclass。`RoutingObservation` 的
      欄位集合即日誌白名單（`SEC-3`／`SEC-5`），**必須含 `memory_degraded: bool`**
      （`D-1` 的唯一保險，審查 `R-02`），**不得含** `text`／`label`／`referent`
- [x] 建 `intent_routing_errors.py`：四個具名例外（`NFR3.74` 的分型計數前提）
- [x] 建 `intent_routing_config.py`：五個環境變數。`BRAIN_ROUTER_CONFIDENCE_THRESHOLD`
      **缺值即 raise**（`BR3.4` 逐字「缺值不得以預設值靜默啟動」）；其餘四個取預設並記 log

### Step 2 — 驗證既有 test runner（**在第一個測試步驟之前**）

- [x] 跑 `cd backend` → `python3 -m unittest -v tests.test_langgraph_runtime`，確認全綠
- [x] 確認本單元的 scoped 指令形狀（見 `unit-test-instructions.md` §二）可執行
- [x] brownfield：runner 已存在，本步是**驗證**不是建立

### Step 3 — Data model / database behavior：**不適用**

- [x] 本單元**不碰資料模型、不改 schema、不寫任何持久層**（`NFR4.70` 無狀態）。
      明確記為不適用，不跳過——`schema_rbac.sql`／`DEPLOY.md` 的 blocking 同步規則
      因此**不觸發**（`project.md` 的觸發條件逐字為 DDL 或 seed 語意變更，兩者皆無）

### Step 4 — Repository / data access：實作 L0 的讀取

- [x] 在 `intent_routing.py` 實作 L0：經 `SessionStore` 讀該段作業對象與歷程、
      經 `MemoryFacade.search` 讀記憶
- [x] `_REFERENT_MEMORY_KINDS: Final = ("semantic", "procedure")` ——
      **模組層常數，不是預設參數值**（預設值可被覆寫，常數不行；`NFR7.62`）
- [x] `U8` 不可用 → **降級**（不帶記憶繼續）並設 `memory_degraded=True`；
      `U10` 不可用 → **失敗**（向上傳遞）。兩者差別待遇見 `D-1`
- [x] **不得**呼叫 `SessionStore` 的任何寫入方法（`BR7.4`）

### Step 5 — Repository / data access：寫並跑其測試

- [x] `test_intent_routing_structure.py` 的禁 import 與 `kinds` 斷言
- [x] `U8` 降級、`U10` 失敗兩條路徑各一個測試

### Step 6 — Business logic：實作 L2／L4／L5（三個純函式層）

- [x] `intent_routing_context.py`（L2）：prompt 組裝。**簽章只收**（作業對象名稱、
      最後 K 則歷程、能力清單、使用者文字），**不收 `BrainSession`**（`NFR9.60`）
- [x] `intent_routing_parser.py`（L4）：扁平 → 兩層，`V-1`～`V-5`。
      `V-3` 的槽位上界 **4（暫定，`D-7`）**、每槽位候選 `maxItems` **8**；
      **超界即 `MalformedRouting`，不截斷**（審查 `R-04`：不是 `BR2.4`）
- [x] `intent_routing_predicate.py`（L5）：`can_single_out(ranking, threshold)` 純函式；
      `BR3.2` 有分數分支、`BR3.3` 無分數分支；`BR4.2` 的 AND 聚合；
      `EC7` 基數等式；`EC8` 攤平時**以程式**把槽位任務描述前綴到 `label`
      （**不依賴模型自己寫**——那是無法驗證的要求，審查 `R-06`）

### Step 7 — Business logic：寫並跑其測試

- [x] `test_intent_routing_predicate.py`：**七條 property 全部 `@given`**
      （`P1`–`P7`），生成策略**顯式驅動** `scoresAvailable` 與 `len(slots)`
      （審查 `R-06`／`nfr-design` §五）← **ADR-0006 hard constraint**
- [x] `test_intent_routing_parser.py`：`V-1`～`V-5` 各一個 negative ＋ happy path。
      **`V-5` 必須斷言它是降級不是失敗**
- [x] `test_intent_routing_context.py`：五個，**零 mock**

### Step 8 — API / endpoint：**不適用**（但要有斷言）

- [x] 本單元**不建立任何端點**（`SEC-2`）。這不是「沒做」，是設計決定——
      故 `test_intent_routing_structure.py` 要有**斷言它確實沒有**
      （無 `APIRouter`、未被 `main.py` include）
- [x] `openapi.json` **不需重 dump**（無端點變更，CI 的 drift 閘門不會動）

### Step 9 — API / endpoint：實作 L3 model-port ＋ 寫測試

- [x] `intent_routing_port.py`：`router_chat_model()` factory —— **不沿用
      `openrouter_chat_model` 的現行簽章**，因為它無條件傳 `temperature=0.0`
      而 Jev 的 `supported_parameters` 為空陣列（`TS-3a`）
- [x] 若 `openrouter_chat_model` 需要改成 `temperature: float | None = 0.0`
      （`None` 時不放進 kwargs）：**驗收條件是不改變既有呼叫者 A1／A3／C1 的行為**
      （預設仍 `0.0`，只多一個 `None` 的語意）。`D-3`
- [x] 單節點 `StateGraph`，沿用 `review_agent.py:146` 的**具名 TypedDict state**
      形狀（`StateGraph(_RouterState)`）——**不要用 `StateGraph(dict)`**，
      那是 `test_a3_langgraph_migration.py:188` 釘住的已知 bug
- [x] tool schema：**扁平 `candidates` 陣列 ＋ `slot` 整數索引 ＋ 平行的
      `slot_labels`**（`[D1]`=A；`slot_labels` 供 `EC8` 的 `label` 前綴使用）
- [x] `test_intent_routing_port.py`：七個測試（四種失敗、零重試、單次呼叫、
      `temperature` 省略）

### Step 10 — Frontend behavior：**不適用**

- [x] 本單元無前端（`U14 entry-page-ui` 才有）。明確記為不適用

### Step 11 — 環境／建置設定

- [x] **三處同步**五個 `BRAIN_ROUTER_*` 變數（`NFR8.61`，`validate_env_contract.py` 會擋）：
      `deploy/render-env.sh`（**字面值**，比照 `BRAIN_SESSION_HISTORY_MAX=200`）、
      `deploy/.env.example`、`deploy/docker-compose.deploy.yml`
- [x] `backend/.env.example` 也要列這五個
- [x] **`LOCAL-DEV.md` 必須同步更新**（`project.md` blocking 規則：異動任一
      `.env.example` 或 `render-env.sh` 時）
- [x] `BRAIN_ROUTER_CONFIDENCE_THRESHOLD=0.7` 寫字面值，**不加進兩道 secret 守衛**（`[I2]`=A）
- [x] 跑 `python3 scripts/validate_env_contract.py` 與 `python3 scripts/validate_repo_contract.py`

### Step 12 — 文件與追溯

- [x] `source-manifest.json`（嚴格 schema：`stage`／`unit`／`version`／`writes`）
- [x] `code-summary.md`
- [x] `traceability.json`

## 三、故事 → 步驟追溯

| 故事 | 由哪些步驟實作 |
|---|---|
| `US1.1`（一句話交辦，認出要做什麼、對誰做） | Step 4（L0 讀作業對象）、Step 6（L2 組裝、L4 解析、L5 判定）、Step 9（L3 呼叫） |
| `US1.2`（判不出來先問我，不要亂做） | Step 6 的 `can_single_out` ＋ `EC8` 攤平；Step 7 的 `P1`／`P2`／`P7` |
| `US5.1`（一句話兩件事，分別做） | Step 6 的槽位還原與 `EC7` 基數等式；Step 7 的 `P6`（**多槽位必須被生成策略涵蓋**） |
| `US6.1`（第二輪用指涉詞接著講） | Step 4 的 L0 讀該段歷程 ＋ `kinds` 排除情節記憶；Step 5 的降級／失敗測試 |

## 四、本計畫刻意不做的事（避免 subagent 擴張範圍）

| 不做 | 理由 |
|---|---|
| 不建 HTTP 端點 | `SEC-2`；`K-10` 是 `in-process` |
| 不寫 `SessionContext` | `BR7.4`；`AC1.1.5` 的寫入端缺口是 `OPEN-IR11-4`，已指派 `U12` |
| 不建工作項、不決定狀態機 | `BR7.3`；屬 `U12` |
| 不改 `schema_rbac.sql`／`DEPLOY.md` | 無 DDL、無 seed 語意變更，blocking 規則不觸發 |
| 不建 circuit breaker、不設 fallback 模型 | `nfr-design/reliability-design.md` §三 已定案 |
| 不引入 tracing 套件、不建 dashboard | `nfr-design/observability-design.md` §三／`monitoring-design.md` §五 |
| 不新增任何套件 | `TS-5`：零新依賴 |
| 不建 `workflow_dispatch` 的量測 job | `[I1]`=A 定案它存在，但**它屬 `build-and-test` 的交付**，不是本單元的程式碼 |

## 五、品質目標（**輸入，不是建議**）

stage 檔 Critical Rules 逐字：NFR 的可量測目標與 Testing Contract 的覆蓋下限
**是輸入不是建議**，**不得**為了讓某一步過關而調低、放寬或停用任何目標
（含測試或建置設定裡的門檻值）——**有缺口就寫出來**。

| 目標 | 值 | 來源 |
|---|---|---|
| `classify` P50 | ≤ 800 ms | `NFR3.60` |
| 硬逾時 | 5 秒 | `NFR3.61` |
| 每輪模型呼叫 | **恰 1 次** | `NFR3.62` |
| 重試 | **0 次** | `NFR3.63` |
| L5 的 PBT | **七條 property，`@given`** | `ADR-0006` hard constraint |
| 每元件測試數 | **5–8** | Testing Contract `obligations.strategy_volume` |
| 既有測試套件 | **保持全綠** | Testing Contract `obligations.scope_floor` |

## 五之一、合併前必修第 5、13 項（code-generation Request Changes 修訂，2026-10-23）

**來源**：`construction/functional-design/merge-blockers.md` 第 5 項（`review-03` R-04）與第 13 項（`nfr-design` `review-03` R-03），皆劃給本單元。第 13 項由使用者於 2026-10-23 裁決；第 5 項的修法不涉產品取捨（恢復既有設計意圖），conductor 已向使用者說明。

### Step 13 — 第 5 項：選定澄清選項後保留 `referent` 與其他槽位的意圖

**缺陷**：`brain_gateway.py:1525-1530` 的 `_on_select` 只以被選候選的 `capability` 重建 `IntentDecision(intents=(Intent(chosen.capability, None),), ...)`。被選槽位原本解析出的 `referent` 與同一句話中其他**已確定**槽位的意圖全部遺失（例：「改這張圖，順便估成本」澄清其一，另一件被丟棄）。`ClarifyCandidate`（`K-10`）只帶 `id`／`label`／`capability`／`confidence`，不足以還原。

- [x] 路由器產生澄清判定時，於**行程內**同時提供「候選 id → 該候選代表的完整 `Intent`（含 `referent`）與它所屬的槽位」以及「其他已確定槽位的 `Intent`」，供閘道還原；**不改 `ClarifyCandidate` 的線上欄位與 `ws-contract.json`**（`K-10`／`K-02` 的線上形狀不動）。若必須在 `IntentDecision` 上加欄位，該欄位標明「行程內、不序列化」，並在 `code-summary.md` 記為對 `K-10` 欄位集合的對齊紀錄（已核可上游不回改）。L5 純函式層仍不得引入隨機值（`BR3.6`），對照資料以決定性方式產生。
- [x] `brain_gateway.py` 的 `_on_select`（屬 `brain-gateway` 單元的檔，因第 5 項劃給本單元而在此修，於該單元的重新查驗時註明）：`PendingClarify` 保存上述對照，選定後以「被選候選的完整 `Intent` ＋ 其他已確定槽位的 `Intent`」重建判定，再走既有的 `_resolve_and_dispatch`。
- [x] 測試：單槽位澄清選定後 `referent` 被保留；多槽位（一個不確定、一個確定）選定後兩個意圖都進入派送，順序與原句一致；「都不是」（`candidateId=None`）仍安靜結束（`AC1.2.3` 不變）；不在候選集合內的 id 仍回 `INVALID_REQUEST`。突變：還原為只帶 `capability`／`None` → `referent` 與多槽位案例紅。

### Step 14 — 第 13 項：記憶被拒絕存取時，本輪以授權錯誤結束（裁決：授權錯誤結束）

**缺陷**：`intent_routing.py:216-228` 的 `_memory_notes` 以 `except Exception` 把所有記憶讀取錯誤都當成「`U8` 不可用、降級繼續」，連授權拒絕（`MemoryForbidden`，實際發生於待核准帳號——`MemoryFacade._authorize_approved` 在取列之前擋下）也被吞掉。

- [x] `_memory_notes`：`MemoryForbidden` **不降級**，向上傳遞；其餘例外照舊降級並記 WARN（`D-1` 不變）。`MemoryNotFound` 若可能出現於 `search`，判定其語意後在 `code-summary.md` 寫明處置。
- [x] 呼叫鏈（`fetch_routing_context` → `classify` → 閘道）把它轉為本輪的授權錯誤：閘道以既有錯誤碼（`UNAUTHORIZED` 或 `rules.error_for` 對應的授權類代碼，沿用既有封閉表，不新增碼）結束本輪，並記一筆 WARN 級安全日誌（不含記憶內容、不含使用者輸入原文）。
- [x] 測試：facade 拋 `MemoryForbidden` → 分類不被呼叫（或本輪不派送）、閘道送出授權錯誤；facade 拋一般例外 → 仍降級繼續（`memory_degraded` 為真）；日誌不含輸入原文。突變：把 `MemoryForbidden` 併回 `except Exception` → 授權案例紅。

### Step 15 — 驗證與紀錄

- [x] 本單元五個測試模組、`brain-gateway` 受影響的既有測試、完整套件（`backend/.venv`）全綠；L5 的七條 PBT 仍綠。
- [x] `merge-blockers.md` 第 5、13 列回填處置；`code-summary.md` append 本節紀錄（改動檔:行、測試、突變、對 `K-10` 的對齊紀錄若有）；`source-manifest.json`（含 `brain_gateway.py`）、`traceability.json`（加 `MB-5`／`MB-13`）更新。
- 追溯：`merge-blockers.md` #5／#13；`BR3.6`、`BR5.1`、`BR5.5`、`D-1`、`AC1.2.3`。

## 六、核可關卡

本計畫與 `unit-test-instructions.md` 的核可題目在
`code-generation-questions.md` 的 `## Plan Approval` 段（含內容綁定的兩行 tag）。
**本檔不放 tag**——tag 的值是對本檔內容的雜湊，寫進本檔會自我指涉而永不收斂。

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
