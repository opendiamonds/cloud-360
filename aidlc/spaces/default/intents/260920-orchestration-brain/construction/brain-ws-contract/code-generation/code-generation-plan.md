# Code Generation Plan — `U2 brain-ws-contract`（`spec`）

<!-- Stage: code-generation（Construction 3.5）· Unit: brain-ws-contract · kind: spec -->

## 這個單元要交付什麼

`U2` 是本 intent 的**可平行根**（無依賴），被 `U13 brain-gateway` 與 `U14 entry-page-ui` 依賴。
它交付前後端共用的 WebSocket 訊息型別來源與保護它的閘門。經 `nfr-requirements` 與
`nfr-design` 兩站後，交付物比 `unit-of-work.md:69` 的字面（「型別來源 ＋ 一道 CI 檢查」）多了三項，
三項都已列為需回補 scope 的 S 項：

| 交付物 | 來源 |
|---|---|
| 後端 Pydantic 契約模組（唯一人手改的真實來源） | `K-02` `[C2]`=A |
| `ws-contract.json`（衍生物 1）＋ dump 腳本與其 `--check` | `K-02` `derived_artifacts`／`ci_gates` |
| `frontend/src/types/ws-contract.d.ts`（衍生物 2）＋ 第二道閘門 | 同上；`BR4.3` |
| **既有兩道型別閘門的供應鏈修補**（S-1） | `ADR-0019 §2` |
| **一條 ESLint error 規則**（S-4） | `ADR-0019 §5` |
| **一段執行期 validator**（S-5） | `ADR-0019`；`nfr-design §四` |
| **`REQUIRED_TEXT` 的 `ci.yml` 一鍵**（S-3） | `ADR-0019 §4` |

## 一個必須先裁決的衝突（**請在核可時一併決定**）

`ADR-0019 §5` 的 ESLint 規則**一開即會讓 `frontend/src/pages/BrainPage.tsx:83` 紅燈**——
該行現持有 `` [`bearer.${token}`] ``，正是規則要抓的形狀。那是本 session 為今晚展示加的
demo-scope 頁面。設計文件寫的處置是「同一個 PR 內二擇一」。

**本計畫採 (a)：把 `BrainPage.tsx` 改為由產生的型別取值**，不刪除它。

理由：(1) 今晚要展示，刪掉就沒得看；(2) 改動極小（三行）；
(3) **它會成為這套機制的第一個真實消費端**——`NFR5.4` 的整條保護第一次有人證明它真的會動，
而不是只寫在文件裡。代價是 demo 程式碼開始依賴產生的型別檔，
但 `U13`／`U14` 落地時本來就會整檔取代它。

> 若你要改採 (b)（先刪 demo 頁），請在核可時說，計畫的 Step 8 會改寫。

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

**方法論是 `test-after`**（`source: fallback`——團隊尚未在 memory 明示方法論，
故取 `org.md` 的預設）。每一個可測層**先實作、再寫並跑該層的測試**。

**兩個 `plan_profile` 層在本單元不適用**，逐項說明而非省略：

| 層 | 判定 | 理由 |
|---|---|---|
| Repository / data access | **不適用** | 本單元無資料存取。契約模組不 import 任何 DB session 型別 |
| API / endpoint | **不適用** | 本單元不新增任何 HTTP 或 WebSocket 端點。`/api/brain/ws` 是 `U13` 的交付 |

---

## 實作步驟

### Step 1 — 專案結構與建置設定（`ADR-0019 §2`，S-1）

- [x] `frontend/package.json`：`devDependencies` 新增 `"openapi-typescript": "7.13.0"`（**精確，不得用 `^`／`~`**）
- [x] `frontend/package.json`：`gen:types` 改為 `openapi-typescript ../openapi.json -o src/types/api.d.ts`（移除 `npx --yes` 與版本字串）
- [x] `frontend/package.json`：新增 `gen:ws-types` = `openapi-typescript ../ws-contract.json -o src/types/ws-contract.d.ts`
- [x] `frontend/package.json`：新增 `check:ws-types` = `node scripts/check-ws-types.mjs`
- [x] `frontend/scripts/check-api-types.mjs`：`GENERATOR` 常數與 `execFileSync('npx', ['--yes', …])` 改為本地解析；`:19–21` 那段「兩處若不一致」的註解**改寫成新的事實**（它已作廢）
- [x] `npm install` 產生 lockfile 變更，**一併 commit**
- [x] **重產 `frontend/src/types/api.d.ts` 並比對**：若與 committed 版本有差異，把新的一併 commit（`ADR-0019 §2` 的一次性複驗）

**追溯**：`NFR5.2`｜**故事**：本步驟無使用者故事，它是 `NFR5` 的承載

### Step 2 — 驗證測試 runner 並記錄本單元指令（contract 要求，先於任何測試步驟）

- [x] 確認 `cd backend && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_ws_contract tests.test_dump_ws_contract -v` 可執行（brownfield：runner 已存在，只需驗證）
- [x] 該指令已記錄於 `unit-test-instructions.md`

**注意**：此時兩個測試檔尚不存在，指令會回報 module not found——那是預期的。
本步驟驗的是 **runner 可執行**，不是測試存在。

### Step 3 — 資料模型層：實作契約模組

- [x] 建立 `backend/services/brain_ws_contract.py`（**純 Pydantic，無 router、無 FastAPI 依賴、不 import DB、不 import httpx、不 import `HTTPException`**）
- [x] 兩個列舉：`WsServerMessageType`（**9** 值：`ready`／`token`／`clarify`／`work_items`／`cost_card`／`sharing_mode`／`work_target`／`done`／`error`）、`WsClientMessageType`（**6** 值：`hello`／`user_message`／`select_clarify_candidate`／`correct_work_item`／`set_sharing_mode`／`set_work_target`）
- [x] 三個 envelope：`WsEnvelope`（`v: Literal[1]`、`type`、`turnId: str|None`、`payload`）、`WsClientEnvelope`（**不得有 `turnId` 欄位**——`BR2.13`）、`WsUnvalidatedEnvelope`（`v: int`、`type: str`，寬鬆；`BR1.1` 的明文例外）
- [x] 15 個 payload ＋ 2 個子實體（`ClarifyCandidate`、`WorkItem`），逐一照 `entities.md`
- [x] `WsSubprotocol`（`scheme: Literal["bearer"]`、`separator: Literal["."]`）——`ADR-0019 §3`
- [x] **`BR1.5` validator**：`done`／`error` 的 `payload.turnId == envelope.turnId`（S-5，本單元唯一的執行期程式碼）
- [x] **`BR1.6` validator**：`turnId` 在 `{token,clarify,cost_card,done,error}` 必為非 null、在 `{ready,sharing_mode,work_target,work_items}` 必為 null，**兩集合互斥且窮盡九個 type**
- [x] `BR2.4`：`ClarifyCandidate.confidence` 為 `float|None` 且值域 `[0,1]`
- [x] `BR2.1`：`TokenPayload.text` 非空白
- [x] `BR2.2`：`ClarifyPayload.candidates` 非空陣列
- [x] `BR2.11`：`CostCardPayload.estimateSetId` 必填整數
- [x] **`WorkItem.sideEffect` 必須帶 `description=`**，內容含 `"none"` 與 `"unknown"` 兩個哨兵值的語意（`BR4.4` 斷言的前提；缺了它註解會靜默消失）
- [x] logger 命名若需要，一律 `"cloud360.<module>"` 形式（`team.md` 命名慣例）

**追溯**：`BR1.1`–`BR1.6`、`BR2.1`–`BR2.14`、`NFR5.5`、`NFR5.7`｜**故事**：`US1.2`、`US8.1`（型別面）

### Step 4 — 資料模型層：寫測試並跑（test-after）

- [x] `backend/tests/test_ws_contract.py`，**7** 個測試（清單見 `unit-test-instructions.md`）
- [x] 跑 Step 2 的指令，確認綠燈
- [x] **突變驗證 M1／M2**，把突變內容與轉紅的斷言編號記下

**追溯**：同 Step 3

### Step 5 — 業務邏輯層：實作 dump 腳本與其斷言

- [x] 建立 `backend/scripts/dump_ws_contract.py`
- [x] **只 import 契約模組，不 import `main`**（`ADR-0019` D-4 的連帶；少一處 DB 樁，且閘門訊號只代表契約本身）
- [x] 產出最小 OpenAPI 3.1 外殼：`openapi`／`info`／`paths: {}`／`components.schemas`，以 `models_json_schema(..., ref_template="#/components/schemas/{model}")` 產生
- [x] 序列化：`json.dumps(..., indent=2, sort_keys=True, ensure_ascii=False)` ＋ 尾端換行（`BR4.2`）
- [x] `--check` 模式：比對 committed 的 `ws-contract.json`，不一致 exit 1
- [x] **`BR1.4` 斷言**：type 列舉與 payload 實體兩集合等勢且可對應（payload 判定式＝名稱以 `Payload` 結尾者，排除兩個子實體、三個 envelope、兩個列舉、`WsSubprotocol`；對應為 snake→Pascal ＋ `Payload` 後綴）
- [x] **`NFR5.7` 白名單斷言**：七個客戶端物件的欄位名集合**逐一等於**釘在本腳本內的預期集合
- [x] **白名單旁必須寫下 `ADR-0019 §6` 的適用前提註解**：本判定式只比對頂層 `properties` 鍵；巢狀物件需遞迴或明文排除
- [x] **fail-closed**：規格檔不存在、模組 import 失敗、斷言拋例外，三者皆 exit 非 0，**不得** try/except 吞掉後回報無漂移
- [x] 產生 repo 根的 `ws-contract.json` 並 commit（**不得**放 `frontend/public/`——`NFR5.6`）

**追溯**：`NFR5.1`、`NFR5.6`、`NFR5.7`、`BR1.4`、`BR4.1`、`BR4.2`、`BR4.6`

### Step 6 — 業務邏輯層：寫測試並跑（test-after）

- [x] `backend/tests/test_dump_ws_contract.py`，**6** 個測試
- [x] 測試用 `tempfile.TemporaryDirectory()`，**不得寫到 repo 根的真實規格檔**
- [x] 跑 Step 2 的指令，確認綠燈
- [x] **突變驗證 M3／M4／M5**

**追溯**：同 Step 5

### Step 7 — Repository／API 兩層：不適用（明文記載，不靜默略過）

- [x] 在 `code-summary.md` 逐項寫明兩層不適用的理由（見本檔 Testing Contract 下方的表）

### Step 8 — 前端行為層：實作第二道閘門、型別檔、lint 規則與第一個消費端

- [x] `npm run gen:ws-types` 產生 `frontend/src/types/ws-contract.d.ts` 並 commit
- [x] 建立 `frontend/scripts/check-ws-types.mjs`：重產到暫存檔並與 committed 比對，不一致 exit 1（形狀比照既有 `check-api-types.mjs`，但用本地解析的產生器）
- [x] **`BR4.4` 斷言**放在這支腳本內：產生的 `.d.ts` 在 `sideEffect` 欄位上方須存在含 `"none"` 與 `"unknown"` 語意的 `@description` 段
- [x] `frontend/eslint.config.js`：新增 **error 級** `no-restricted-syntax` 規則，禁止 `new WebSocket` 第二引數出現字串字面量或模板字面量（`ADR-0019 §5`）
- [x] **`frontend/src/pages/BrainPage.tsx:83` 改為由產生的型別取值**（見本檔開頭的衝突裁決）：
      宣告 `const SCHEME: Sub['scheme'] = 'bearer'`／`const SEP: Sub['separator'] = '.'`，以 `` `${SCHEME}${SEP}${token}` `` 組出 subprotocol
- [x] 跑 `npm run lint`，確認 **0 error**（既有 2 個 `exhaustive-deps` warning 不受影響）
- [x] 跑 `npm run build`（`tsc -b && vite build`），確認綠燈

**追溯**：`NFR5.1`、`NFR5.4`、`BR4.3`、`BR4.4`、`BR4.5`

### Step 9 — 前端行為層：驗證（test-after）

前端無 unit 測試框架，本單元亦不引入（`unit-test-instructions.md` 已說明）。
本層的「測試」是**閘門本身的突變驗證**：

- [x] 手改 `frontend/src/types/ws-contract.d.ts` 一個字元 → `npm run check:ws-types` 必須紅燈 → 還原 → 綠
- [x] 拿掉契約模組 `sideEffect` 的 `description=` → 重產 → `BR4.4` 斷言必須紅燈 → 還原 → 綠
- [x] 把 `BrainPage.tsx` 改回寫死字面量 → `npm run lint` 必須紅燈 → 還原 → 綠
- [x] 把 `WsSubprotocol.scheme` 改成 `Literal["brain"]` → 重產型別檔 → `npm run build` 必須因 `BrainPage.tsx` 的 `= 'bearer'` 而紅燈 → 還原（**這一項證明 `NFR5.4` 的整條保護真的成立**）

**追溯**：`NFR5.4`、`BR4.3`、`BR4.4`

### Step 10 — 環境／建置設定（`ADR-0019 §4`，S-3）

- [x] `.github/workflows/ci.yml` 的 backend job：在 `python scripts/dump_openapi.py --check` 之後新增 `python scripts/dump_ws_contract.py --check`
- [x] `.github/workflows/ci.yml` 的 frontend job：在 `npm run check:types` 之後新增 `npm run check:ws-types`
- [x] `scripts/validate_repo_contract.py` 的 `REQUIRED_TEXT` 新增 `.github/workflows/ci.yml` 一鍵，詞條涵蓋**四道**指令字串
- [x] 跑 `python3 scripts/validate_repo_contract.py` 與 `python3 scripts/validate_env_contract.py`，兩者皆須通過
- [x] **突變驗證**：把任一道閘門步驟從 `ci.yml` 刪掉 → `validate_repo_contract.py` 必須 exit 非 0 並指名缺哪一條 → 還原

**追溯**：`NFR5.3`

### Step 11 — 文件與追溯

- [x] 契約模組加模組級 docstring，深度比照 `agent_router.py` 的「契約（前端依賴，請勿變更）」樣板（`team.md` 追認的慣例）
- [x] dump 腳本加模組級 docstring，說明**為何不 import `main`**與**規格檔為何在 repo 根**
- [x] `source-manifest.json`：列出本單元建立／修改／刪除的**每一個**應用程式來源路徑
- [x] `traceability.json`：逐條覆蓋指派的 AC、`NFRx.y`、`BRx.y`，每個 `OK` 的 target 必須是**實際存在**的 workspace 相對檔案路徑
- [x] `code-summary.md`：檔案清單、關鍵決定、**五項突變驗證的逐項結果**、與計畫的任何偏離

**追溯**：本步驟承載整個單元的可稽核性

---

## 步驟 ↔ 故事追溯

| Step | 承載的故事／AC | 界線 |
|---|---|---|
| 3、4 | `US1.2`（`AC1.2.1`–`AC1.2.4`）、`US8.1`（`AC8.1.1`、`AC8.1.3`）的**型別面** | 行為面在 `U11`／`U13`／`U14`。`AC8.1.2`（活動記錄）與 `AC8.1.4`（既有 SSE 不變）本單元**無貢獻**，標 `Deferred` |
| 1、5、6、8、9、10 | 無直接使用者故事 | 它們承載 `NFR5`，而 `NFR5` 本身是機械事實驅動的（WebSocket 不在 `openapi.json` 的 42 個 path 內，既有兩道漂移閘門對它完全無效） |
| 11 | 全單元 | — |

## 不做的事（明文，避免下游誤讀為遺漏）

- **不新增任何前端測試框架**（Vitest／jest）——`team.md` 的 D 項已定案不採。
- **不引入覆蓋率量測工具**——獨立的工具鏈決策，不由本單元夾帶。
- **不實作 `/api/brain/ws` 端點**——那是 `U13`。
- **不碰 `K-02` 以外的任何契約**。
- **不改任何已核可的上游產出**；`functional-spec.md:11` 的「沒有執行期程式碼」已在
  `nfr-design §四` 標為過窄並更正，現行規格以該處為準。

## Plan Approval

核可關卡在 `code-generation-questions.md` 的 `## Plan Approval` 段
（兩個綁定 tag 與 `[Answer]:` 都在那裡）。**本檔不放 tag**——
指紋的投影涵蓋本檔全文，把指紋寫進本檔會讓它自我循環，每寫一次就換一個值。
