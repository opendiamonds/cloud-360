# Code Generation Plan — `U6 embedding-port`（`library`）

<!-- Stage: code-generation（Construction 3.5）· Unit: embedding-port · kind: library -->

> 本單元的設計已由四站定案：`functional-design`（`BR1.1`–`BR7.2`、`P1`–`P6`）、
> `nfr-requirements`（`NFR3.1`–`NFR9.1`、`SEC-1`–`SEC-4`）、
> `nfr-design`（`D-1`–`D-10`）、`infrastructure-design`（四個設定檔 ＋ `H-I3` 的 CI step）。
> **本計畫不新增設計決定**，只把它們排成可執行的順序。

## 〇、交付物清單（**應用程式碼一律在 workspace root，不在 record dir**）

| # | 檔 | 性質 | 承載 |
|---|---|---|---|
| 1 | `backend/services/embedding_port.py` | **新** | Port 介面、選擇器、三個實作、例外 |
| 2 | `backend/tests/test_embedding_port.py` | **新** | `P1`–`P6` ＋ 啟動驗證 ＋ 逾時 ＋ 遮罩 ＋ 截斷 |
| 3 | `backend/main.py` | 既有，加 1 行 | startup hook 掛上驗證（`D-1`） |
| 4 | `backend/.env.example` | 既有，加 1 行＋註解 | `EMBEDDING_TIMEOUT_SEC` |
| 5 | `deploy/.env.example` | 既有，加 1 行＋註解 | 同上 |
| 6 | `deploy/render-env.sh` | 既有，加 1 行 | 寫出該變數 |
| 7 | `deploy/docker-compose.deploy.yml` | 既有，加 1 行 | 無 fallback 形式傳入 backend |
| 8 | `scripts/validate_embedding_provider_value.py` | **新** | `H-I3`：**import** 本單元的驗證函式驗 `render-env.sh` 的值 |
| 9 | `.github/workflows/ci.yml` | 既有，加 1 step | 在 `repo-contract` job 跑第 8 項 |
| 10 | `LOCAL-DEV.md` | 既有 | **兩項**：timeout 變數 ＋ `fastembed` 安裝說明 |

**不得改動**：`backend/requirements.txt`（`tech-stack-decisions.md` 已核可「淨變更：零」）、
`schema_rbac.sql`、`DEPLOY.md`、`backend/database.py`、`backend/models.py`、
`deploy/docker-compose.test.yml`（其 `EMBEDDING_PROVIDER` 已有 `:-stub` fallback）。

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

**methodology 為 `test-after`**：每一個可測層先實作、再寫並跑該層的測試。
runner 就緒排在第一個可執行測試步驟之前。

### 刻意省略的 `plan_profile.steps` 層（各附理由）

| 省略的層 | 理由 |
|---|---|
| Data model / database behavior | 本單元**不讀 DB**（K-06 逐字、`SEC-1`、`BR2.7`）。零 schema、零 model |
| Repository / data access | 同上，無資料存取層 |
| API / endpoint | **零端點**（`SEC-1` 明文禁止新增 HTTP 入口） |
| Frontend behavior | 零前端改動 |

**保留的層**：Business logic（Port 本體）、啟動整合、環境／建置設定、文件與追溯。

## 二、實作步驟

### Step 1 — 專案結構與命名確認（不產生程式行為）

- [x] 確認落點 `backend/services/embedding_port.py`，命名沿用 `team.md ## Code Style` 的既成慣例：檔名 `snake_case.py`、logger 為 `logging.getLogger("cloud360.embedding_port")`
- [x] 確認 `backend/requirements.txt` **不需改動**（`httpx`、`hypothesis` 皆已在；`fastembed` 依 `[Q4]`=A 不加）

### Step 2 — Runner 就緒驗證（**第一個可執行測試步驟之前**）

- [x] 確認 `backend/tests/` 下的新檔會被既有 `python -m unittest discover -s tests` 自動撿到（brownfield，runner 已存在，本步是**驗證**不是建置）
- [x] 記錄精確的 unit-scoped 指令於 `unit-test-instructions.md`（已寫好，見該檔 §一）
- [x] 確認 `import tests.helpers  # noqa: F401` 的 psycopg2 stub 形狀——**本單元不讀 DB，但 `main.py` 的 import 鏈會碰到 DB 模組**，故啟動整合測試仍需它

### Step 3 — Business logic 實作

- [x] `EmbeddingProviderUnavailable` 例外：三個欄位 `selected_provider`／`target`／`available_options`（`entities.md`、`D-7`）。組裝 `target` 時**剝除 URL 的 `userinfo` 區段**（`SEC-2`、`BR7.2`）
- [x] `EmbeddingPort` 介面：`embed(texts) -> list[list[float]]`、`model_id() -> str`，皆 sync（K-06）
- [x] `resolve_provider_selection()`：讀四個環境變數 → 驗值域（`BR1.1`）→ 驗 `ollama` 的必填與主機名（`BR1.3`、`NFR7.1`：不得為 `localhost`／`127.0.0.1`／公開 IP）→ 回傳不可變的 `ProviderSelection`。**冪等、無副作用、不建連線、不載模型**（`D-2`、`BR1.5`）
- [x] `resolve_embedding_port() -> Optional[EmbeddingPort]`：`fulltext` 回 `None`（`BR1.4`、`D-10`），其餘三者回對應實作
- [x] `StubAdapter`：`hashlib` 摘要**決定性展開**為 1024 個 float，**不同輸入得不同向量**（`D-3`）；`model_id()` 固定 `stub-v1`（`BR3.6`）
- [x] `OllamaAdapter`：既有 `httpx`，帶模組層**具名常數** timeout（`D-6`、`NFR3.2`），值取自 `EMBEDDING_TIMEOUT_SEC`、預設 `10`。**模組內不得出現裸數字 timeout**
- [x] `FastembedAdapter`：**lazy import**（`BR6.1`、`[Q4]`=A）；`ImportError` → 拋 `EmbeddingProviderUnavailable` 且訊息含安裝指令（`BR4.3`）
- [x] 三個實作共通：`embed([])` 回 `[]` 且不碰外部（`BR2.4`）；長度與順序一一對應（`BR2.1`）；每個向量恰 1024 維（`BR2.2`）；**全有或全無**，任一失敗整批拋（`BR2.5`）；**不重試**（`BR2.6`）
- [x] **超長輸入截斷**到提供者 context 上限 ＋ 記 WARN 含被截字元數，**不拋例外**（`D-4`）
- [x] 四條 log 規格（`D-5`、`security-design.md §二`）：啟動 INFO、**每次 `embed` 一條含耗時毫秒的 INFO**、截斷 WARN、**例外不由本 Port 記 ERROR**（`D-8`）
- [x] **不記**：請求內容、向量值、任何憑證（`security-design.md §二`）
- [x] `SEC-1` 的三條禁令：模組內**不得** import DB session 型別、RBAC 判定函式、FastAPI router 裝飾器

### Step 4 — Business logic 的測試（**實作之後**）

- [x] `backend/tests/test_embedding_port.py`，形狀見 `unit-test-instructions.md §二`
- [x] 跑 unit-scoped 指令，全綠

### Step 5 — 啟動整合實作

- [x] `configure_embedding_env()`：模組層函式，呼叫 `resolve_provider_selection()` 並記啟動 INFO；**失敗即拋**（`BR1.6`，與 `configure_provider_env()` 只記 log 的前例**刻意不同**，`D-1` 已明記）
- [x] `backend/main.py` 的 `@app.on_event("startup")`：在 `configure_provider_env()` 與 `init_db()` **之間**插入一行呼叫

### Step 6 — 啟動整合的測試（**實作之後**）

- [x] 直接呼叫 `configure_embedding_env()` 的測試（**不經 startup hook**）：合法值通過、缺值／非法值／`localhost` 主機名各自拒絕
- [x] 確認 `TestClient(app)` **不觸發** startup hook，故既有測試檔不需設定 embedding 變數——以既有測試全綠為證

### Step 7 — 環境／建置設定

- [x] `backend/.env.example` 加 `EMBEDDING_TIMEOUT_SEC=10` ＋ 註解（**`validate_local_dev_template_is_complete()` 機械強制**）
- [x] `deploy/docker-compose.deploy.yml` 加 `EMBEDDING_TIMEOUT_SEC: ${EMBEDDING_TIMEOUT_SEC}`（**無 fallback**，比照 `:120-123`）
- [x] `deploy/render-env.sh` 加 `EMBEDDING_TIMEOUT_SEC=10`（比照 `:124-127` 的字面值形式）
- [x] `deploy/.env.example` 加同一行 ＋ 註解
- [x] `scripts/validate_embedding_provider_value.py`：**import** `backend.services.embedding_port` 的值域常數／驗證函式，驗 `render-env.sh` 寫出的 `EMBEDDING_PROVIDER` 值。**嚴禁在本腳本內自行列舉允許值**（`H-I3` 逐字）
- [x] `.github/workflows/ci.yml` 的 `repo-contract` job 加一個 step 跑上述腳本（該 job 已有 `actions/setup-python@v5` 與四支同形 validator）

### Step 8 — 環境／建置設定的測試（**實作之後**）

- [x] `python3 scripts/validate_env_contract.py` 通過（預期觸發三道：#2 `deploy_stack_is_fully_supplied`、#3 `deploy_template_is_complete`、#6 `local_dev_template_is_complete`）
- [x] `python3 scripts/validate_repo_contract.py` 通過
- [x] `python3 scripts/validate_embedding_provider_value.py` 通過；並以**暫時把 `render-env.sh` 改成非法值**驗證它會紅（改完還原）

### Step 9 — 文件

- [x] `LOCAL-DEV.md` **兩項**（`project.md` blocking）：(a) `EMBEDDING_TIMEOUT_SEC`；(b) `fastembed` 的**帶版本**安裝指令 ＋ HuggingFace 下載來源與快取位置 ＋「**此路徑不經 CI，供應鏈風險由使用它的開發者承擔**」（`SEC-3`）
- [x] 確認 `LOCAL-DEV.md` 的隱性硬依賴由 2 個變 **3** 個

### Step 10 — 突變驗證（**交付條件，不是選配**）

每一項都要：改回錯的行為 → 跑測試 → **確認紅燈** → 還原 → 複驗綠燈，
並把突變內容與紅燈訊息寫進 `code-summary.md`。**每次突變後先 `grep` 確認檔案真的變了**
（`test-case-authoring.md §5` 記過一次突變沒生效而被誤讀為「測試沒抓到」）。

| # | 突變 | 必須紅的測試 |
|---|---|---|
| `M1` | `StubAdapter` 改為對所有輸入回同一個向量 | 「不同輸入得不同向量」（`D-3`） |
| `M2` | 回傳向量長度改為 1023 | `P2` |
| `M3` | `embed` 回傳 list 少一個元素 | `P1` |
| `M4` | 分批與單筆走不同路徑（破壞批次不變性） | `P4` |
| `M5` | 移除 `localhost` 的主機名檢查 | 啟動驗證測試（`NFR7.1`） |
| `M6` | timeout 改為無限（移除參數） | 逾時測試（`NFR3.2`） |
| `M7` | 例外訊息不剝除 `userinfo` | 遮罩測試（`SEC-2`） |
| `M8` | 截斷改為拋例外 | 截斷測試（`D-4`） |
| `M9` | `stub` 的 `model_id` 改回 `bge-m3` | 雙向一致性 ＋ `BR3.6`（`P5`） |

**`M1` 與 `M4` 最重要**：若 `stub` 對所有輸入回同一向量，`P1`–`P3`、`P6` 全部會過，
而 `U8` 用 `stub` 寫的任何相似度測試都變恆真——那正是 `D-3` 存在的全部理由。

### Step 11 — 全套比對與追溯

- [x] `cd backend && python -m unittest discover -s tests` 在改動**前後各跑一次並比對**：新增數 == 本單元新增的測試數；**既有項零失敗**
- [x] 寫 `code-summary.md`（含突變表與其紅燈訊息）
- [x] 寫 `source-manifest.json`（嚴格 schema，列出全部 10 個應用程式檔）
- [x] 寫 `traceability.json`

## 三、故事 ↔ 步驟追溯

| 上游 | 步驟 | 備註 |
|---|---|---|
| `US4.1`（`AC4.1.1`–`AC4.1.3`） | Step 3、4 | **本單元無法單獨滿足任一條 AC**——`unit-of-work-story-map.md:52` 把 `US4.1` 指派給 `U5`／`U8`／`U6` 三個單元。本單元交付檢索所需的查詢向量與其向量空間身分 |
| `BR1.*`（提供者選擇與啟動驗證） | Step 3、5、6 | |
| `BR2.*`（`embed` 契約） | Step 3、4 | |
| `BR3.*`（`model_id` 與雙向一致性） | Step 3、4 | |
| `BR4.*`（大聲失敗） | Step 3、4 | |
| `BR5.*`（本 Port 保證什麼） | Step 3 | `BR5.1` 是誠實宣告，無程式落點 |
| `BR6.*`（依賴策略） | Step 1、3、9 | |
| `BR7.*`（可觀測性） | Step 3、4 | |
| `NFR3.1`／`NFR3.2` | Step 3、4、7 | |
| `NFR4.1` | Step 3、5 | |
| `NFR7.1`–`NFR7.3` | Step 3、5、6 | |
| `NFR8.1`／`NFR8.2` | Step 7、8、9 | |
| `NFR9.1` | Step 1 | 零新依賴即其落點 |
| `SEC-1`–`SEC-4` | Step 3、4、9 | |
| `D-1`–`D-10` | Step 3、5、7 | |
| `H-N4`／`H-I1`／`H-I3` | Step 7、9 | 三項交接事項在本站落地 |

## 四、ADR-0006 四面向落點

| 面向 | 落點 |
|---|---|
| **IAM** | **不適用**（K-06 逐字）。`SEC-1` 的三條禁令以 Step 3 的 import 面機械檢查保證 |
| **Encryption** | Step 3 的 `userinfo` 剝除（`D-7`）＋ Step 5 的主機名驗證（`NFR7.1`）。明文傳輸為 `RR-1` 具名殘餘風險，**不在本站處置** |
| **Network exposure** | 本單元零新增端點；Step 7 的 compose 改動**只加一個環境變數**，不碰服務定義 |
| **Audit logging** | Step 3 的四條 log 規格；**不記**請求內容、向量值、憑證 |

**PBT hard constraint（ADR-0006）**：**適用，本單元即落點**（K-06 `pbt_note`）。
`P1`–`P6` 六個性質已於 `functional-design/functional-spec.md §五` 寫死，
本站不重新定義，只負責實作它們。

## 五、品質目標不得放寬

`NFR3.2`（timeout 10 秒）、`BR2.2`（恰 1024 維）、`D-3`（不同輸入不同向量）、
`BR3.3`（雙向一致性）等皆為**輸入而非建議**。
**不得**為了讓某一步通過而調低、關閉或改寫任何門檻——有落差就把落差說出來。
