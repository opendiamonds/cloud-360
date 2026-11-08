# Code Generation Plan — `U4 hierarchy-data`（`spec`）

<!-- Stage: code-generation（Construction 3.5）· Unit: hierarchy-data · kind: spec -->

## 〇、這個單元要交付什麼

資料模型與一次性遷移程序。**零端點、零畫面、零外部呼叫**（`SEC-1`／`SEC-3`）。

| 交付物 | 落點 |
|---|---|
| 三張新表的 DDL ＋ `user_diagrams.system_id` ＋ 兩個部分唯一約束 ＋ `created_at` 索引 | `schema_rbac.sql`（repo 根） |
| 可被 `unittest` 匯入呼叫的遷移入口，逐使用者交易、回傳計數、失敗大聲 | `backend/services/hierarchy_migration.py`（新檔） |
| 遷移的獨立執行指令 | `backend/scripts/run_hierarchy_migration.py`（新檔） |
| 單元測試 | `backend/tests/test_hierarchy_migration.py`（新檔） |
| 部署文件：前進步驟、回復程序、部分狀態、靜止前置 | `DEPLOY.md`（repo 根） |
| 可攜 schema（建議，非 blocking） | `schema.sql`（repo 根） |

**明確不做**：任何 `APIRouter`、任何 service 層讀寫函式、任何前端檔案、任何新環境變數、
任何新 Python 套件、任何 migration 框架（`D-4`）。

---

## 一、Testing Contract

下列區塊由 `bun .claude/tools/aidlc-testing-posture.ts render` 產生，原樣貼入未改。

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

### 本單元對 `plan_profile.steps` 的採用與省略

方法論是 **test-after**（每層先實作、再寫並跑該層的測試），順序原樣保留。
`steps` 的 14 步中，兩層**真正不適用**故省略，其餘依序保留：

| `plan_profile` 的層 | 本單元 | 理由 |
|---|---|---|
| Project structure / production config skeleton | 合併進步 1 | brownfield，結構已存在 |
| 測試執行器就緒 | **步 1** | 契約要求它在第一個可執行測試步之前 |
| Data model / database behavior | **步 2–3** | `schema_rbac.sql` 的 DDL |
| Repository / data access | **步 4–5** | 遷移的資料讀寫 |
| Business logic | **步 6–7** | 逐使用者交易、計數、不變量終檢 |
| **API / endpoint** | **省略** | 本單元交付零端點（`SEC-1`／`SEC-3`）。這不是偷懶——`SEC-3` 的機械檢查就是斷言這一層不存在 |
| **Frontend behavior** | **省略** | 本單元交付零畫面 |
| Environment/build configuration | **步 8** | `DEPLOY.md`、`schema.sql` |
| Documentation and traceability | **步 9** | `code-summary.md`、`traceability.json`、`source-manifest.json` |

---

## 二、實作步驟

### 步 1 — 測試執行器就緒（契約要求先於第一個測試步）

- [x] 確認 `python -m unittest discover -s tests -v` 在 `backend/` 下可執行（brownfield 既有）
- [x] 確認 `backend/tests/helpers.py` 的 `psycopg2` MagicMock ＋ in-memory SQLite 策略可承載本單元
- [x] **本單元的精確指令**寫進 `unit-test-instructions.md`（不得用裸的 `python -m unittest`）

**故事追溯**：無（基礎設施步）

### 步 2 — 資料模型：`schema_rbac.sql` 的 DDL（實作）

- [x] `projects`：`id`、`name`（非空白）、`owner_user_id`（FK → `users.id`）、`is_default`、`created_at`
- [x] `systems`：`id`、`project_id`（FK → `projects.id`）、`name`、`is_default`、`created_at`
- [x] `diagram_change_records`：`id`、`diagram_id`（FK → `user_diagrams.id`）、`source`（封閉列舉，本輪唯一值 `brain_orchestration`）、`actor_user_id`（FK → `users.id`，**必填**）、`requirement_summary`、`requirement_label`、`created_at`
- [x] `user_diagrams.system_id`：**可為空**，FK → `systems.id`，`ON DELETE RESTRICT`（`BR1.2`）
- [x] `projects` 的 FK ← `systems.project_id` 亦為 `ON DELETE RESTRICT`（`BR1.1`）
- [x] **兩個部分唯一約束，各自只引用自己表內的欄位**（`BR1.3`）：
      `projects` 以 `(owner_user_id)` WHERE `is_default`；`systems` 以 `(project_id)` WHERE `is_default`
- [x] `diagram_change_records.created_at` 索引（`U4-R1`：清除查詢否則全表掃描）
- [x] 全部使用 `IF NOT EXISTS` 等可重跑安全寫法
- [x] `COMMENT ON` 標註：`system_id` 為歸屬權威來源、`source` 的涵蓋面、`is_default` 是遷移冪等承載
- [x] 更新檔頭涵蓋清單

**故事追溯**：`US9.1`（`AC9.1.1` 三層可被表達、`AC9.1.4` 不變量的資料面）

### 步 3 — 資料模型的測試（實作後）

- [x] 兩個部分唯一約束各自可建且真的擋住第二筆
- [x] `ON DELETE RESTRICT` 在兩層都擋住（刪 `systems` 其下有圖、刪 `projects` 其下有 `systems`）
- [x] `system_id` 可為空（**這是 `U4-V2` 夾具的前提，也是 `OQ-H2`／`S-7` 牽制的那一點**）
- [x] `actor_user_id` 必填（缺值即失敗）
- [x] `source` 的封閉列舉拒絕未定義值

**故事追溯**：`AC9.1.4`

### 步 4 — 遷移的資料讀寫（實作）

- [x] `backend/services/hierarchy_migration.py`：模組層函式 `migrate_hierarchy(db) -> MigrationCounts`
- [x] 取得「持有至少一張架構圖的使用者」清單
- [x] 每位使用者：取得或建立預設 `project`／`system`（`BR2.5`），**先解析預設 project，再以其 id 為範圍找 system**（`rules.md §三` 的獨佔寫入紀律）
- [x] 把該使用者 `system_id` 為空的圖掛入其預設 system
- [x] **不修改任何既有欄位**（`BR2.3`／`AC9.1.3`）

**故事追溯**：`AC9.1.2`、`AC9.1.3`

### 步 5 — 遷移資料讀寫的測試（實作後）

- [x] 兩位使用者、各有數張 `system_id` 為空的圖 → 遷移後各自掛入自己的預設 system
- [x] 不持有圖的使用者**不**被建立預設專案（`BR2.5` 的收窄）
- [x] 遷移前後，架構圖的 `owner_user_id`／`title`／`xml_data`／`updated_at` 逐欄未變（`BR2.3`）

**故事追溯**：`AC9.1.2`、`AC9.1.3`

### 步 6 — 業務邏輯：交易邊界、計數、終檢（實作）

- [x] **逐使用者一個交易**（`S-8`）：該使用者的建立與改寫要麼全成要麼全不成
- [x] 回傳計數：處理幾位使用者、建立幾組預設專案／系統、改寫幾張圖（`BR2.6`）
- [x] 終檢：`system_id IS NULL` 的列數為 0，**不為 0 即 raise，不得 `logger.warning`**（`BR2.1`／`AC9.1.4`）
- [x] 冪等：`system_id` 已非空即跳過；預設專案／系統「存在就取用」（`BR2.2`）
- [x] **唯一約束拒絕寫入時必須往外拋**，不得被 `except Exception` 吞掉（`U4-V4`）
- [x] `backend/scripts/run_hierarchy_migration.py`：獨立指令，呼叫同一個入口，失敗以非零結束碼收場（`Q2=A`）
- [x] logger 名稱用 `"cloud360.hierarchy_migration"`（`team.md` 的既成慣例）

**故事追溯**：`AC9.1.4`

### 步 7 — 業務邏輯的測試（實作後）

- [x] 終檢在有殘留空值時 **raise**（不是 warning）
- [x] 計數三個欄位的值正確
- [x] **重跑一次**：沒有第二組預設專案／系統、已掛好的圖沒有被重新指派（`U4-V5`）
- [x] 部分失敗後重跑可補完（逐使用者交易的直接後果，`S-8`）
- [x] 獨立指令在終檢失敗時以非零結束碼收場

**故事追溯**：`AC9.1.4`

### 步 8 — 部署設定（`U4-D1`，blocking）

- [x] `DEPLOY.md`：表／欄位清單更新
- [x] `DEPLOY.md`：**前進步驟**——遷移指令怎麼跑、預期輸出（三個計數）
- [x] `DEPLOY.md`：**回復程序**——清空 `system_id` 並刪除新建的 `projects`／`systems` 列（`decisions.md:90`／`:126` 逐字）
- [x] `DEPLOY.md`：**部分狀態**——「部分使用者已遷移」是合法可恢復狀態，重跑即補完（`S-8`）
- [x] `DEPLOY.md`：**靜止前置**——遷移期間應用不得接流量（`U4-V6`）；並註明現行 `deploy.yml` 尚無有序步驟（`S-9`）
- [x] `schema.sql`（建議，非 blocking）

**故事追溯**：無（部署義務）

### 步 9 — 文件與追溯

- [x] `code-summary.md`
- [x] `traceability.json`
- [x] `source-manifest.json`：逐一列出本單元建立／修改的每一個應用原始碼路徑

**故事追溯**：無

### 步 10 — 合併前必修第 3 項：刪除使用者不得回 500（Request Changes 修訂）

**來源**：`construction/functional-design/merge-blockers.md` 第 3 項（`functional-design/reviews/review-06.md` R-04）。`OQ-H1`（刪使用者時的專案處置）由使用者於 2026-10-20 裁決：**空的預設專案一併清掉，其餘改回 409**。

**缺陷**：`projects.owner_user_id`（`schema_rbac.sql:348`）無 `ON DELETE`，而預設專案由遷移／首次建圖自動建立，所以 `user_router.py:308-324` 的 `_hard_delete_user` 在 `db.delete(user)` 的 commit 時拋 `IntegrityError` → 500。同形狀的無 `ON DELETE` 參照還有：`diagram_change_records.actor_user_id`（:415）、`project_members.user_id`／`invited_by`（:600／:603）、`reselection_events.promoted_user_id`／`previous_owner_user_id`（:649／:650）、`system_requirement_fields.updated_by`（:701）、`memory.memory_records.owner_user_id`（:456）、`memory.memory_audit_events.actor_user_id`（:517）、`estimate_audit_events.actor_user_id`（:312）、`architecture_reviews.created_by`（:143）、`wa_lenses.updated_by`（:183）。

**裁決後的規則**：
1. **自動清除（同一交易）**：該使用者擁有、`is_default = TRUE`、其下所有 system 皆無架構圖、且除他本人外沒有其他成員列的專案——刪其 `systems`，再刪 `project`（`project_members` 經 `ON DELETE CASCADE` 隨之消失）。
2. **其餘一律 409，不回 500**：刪除前以一次預檢列舉所有仍指向該使用者、且不在規則 1 清除範圍內的參照（上列各欄），有任何一筆即 `HTTPException(409)`，回應本體列出「哪一類資料、幾筆」（例：非空或非預設專案、其他專案的成員資格、記憶、稽核操作者紀錄）。**稽核類紀錄不刪**。
3. **保底**：commit 時若仍拋 `IntegrityError`（預檢漏列的新表），rollback 並回 409（通用訊息＋記 log），不得回 500。
4. 既有「仍擁有架構圖 → 403」（`user_router.py:314-319`）**維持不變**，不在本項範圍內改狀態碼。
5. 兩個呼叫點（`DELETE /{user_id}` `:794` 與拒絕授權申請並刪除 `:641`）共用同一函式，行為一致。

**與第三節「不做任何 APIRouter」的關係**：本步修改既有 `user_router.py` 的刪除路徑，是第三節的**明文例外**——`merge-blockers.md` 把第 3 項劃給本單元，且缺陷的根源是本單元建立的 `projects` 表。不新增 router、不新增端點；依 `team.md` 的 `user_router.py` 規則就地沿用既有形狀，不抽 service 層。

- [x] `backend/services/user_router.py`：`_hard_delete_user` 加規則 1 的空預設專案清除、規則 2 的預檢與 409、規則 3 的 `IntegrityError` 保底；兩個端點的 `responses=` 宣告 409（讓 `openapi.json` 與前端型別看得到，比照 `:662-671` 的既有寫法）
- [x] 重產 `openapi.json`（`backend/scripts/dump_openapi.py`），`--check` 綠；前端 `npm run check:types` 綠
- [x] `backend/tests/test_user_delete_hierarchy.py`（新檔，TestClient，`team.md` B 規則）：(a) 只有空預設專案的使用者 → 200，且其預設 project／system／成員列皆已刪除；(b) 預設專案下有架構圖的使用者 → 不回 500（既有 403 或 409，斷言不是 500 且使用者仍在）；(c) 是他人專案成員的使用者 → 409，回應列出成員資格，使用者與成員列皆仍在；(d) 有 `diagram_change_records` 操作者紀錄的使用者 → 409，紀錄仍在；(e) 擁有非預設專案 → 409；(f) 拒絕授權申請並刪除的路徑對只有空預設專案的待審帳號 → 200；(g) 模擬預檢未涵蓋的外鍵於 commit 拋 `IntegrityError` → 409 而非 500
- [x] 突變驗證 M-D1：拿掉規則 1 的清除 → (a) 紅；M-D2：拿掉預檢 → (c)(d) 紅（應落到保底 409 或 500，斷言回應本體列出資料類別即可紅）；M-D3：拿掉 `IntegrityError` 保底 → (g) 紅
- [x] 完整後端套件以 `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest discover -s tests`（在 `backend/`）跑綠
- [x] `schema_rbac.sql` 的 `projects.owner_user_id`、`project_members.user_id` 兩處 COMMENT 由「deliberately NOT decided (OQ-H1)」改為記載本裁決與落點（**COMMENT 文字變更，非 DDL 結構變更**；仍依 `project.md ## Mandated` 同步 `DEPLOY.md` 說明刪除使用者的新行為）
- [x] `code-summary.md` append「合併前必修第 3 項」一節；`traceability.json` 補 `MB-3` 列；`source-manifest.json` 補新路徑

**故事追溯**：`merge-blockers.md` #3、`review-06` R-04、`OQ-H1`

---

## 三、明列不做的事（避免下游誤補）

| 不做 | 依據 |
|---|---|
| 任何 `APIRouter`、任何 service 層讀寫函式 | `SEC-1`；`K-07` 的 facade 屬 `U7` |
| 任何前端檔案 | 本單元 `kind: spec` |
| 任何新環境變數或憑證 | `SEC-2` |
| 任何新 Python 套件、Alembic 等 migration 框架 | `D-4` |
| 欄位級加密、`sslmode` | `U4-R4`（判定為不做任何加密） |
| 90 天清除的實作 | `S-5`（必須走 gh-aw 或 Actions，非 repo 內程式） |
| 把 `system_id` 收成 `NOT NULL` | `OQ-H2` 未定案；且會讓 `U4-V2` 的 CI 夾具不可構造（`S-7`） |
| 修改 `deploy.yml` 加有序靜止步驟 | `S-9`，落點 `ci-pipeline`／`deployment-pipeline` |

---

## 四、帶進本站的未解項（不在本站處置，僅提醒實作者）

`S-5`（清除機制）、`S-6`（CI job 範圍）、`S-7`（夾具與 `NOT NULL` 的牽制）、
`S-9`（部署序列的靜止步驟）、`S-10`（`U5` 的加密未綁定）、`S-11`（`U12` 的行動者前置）、
`OQ-H1`（刪使用者時的專案處置）、`OQ-H2`、`OQ-H3`。

**其中 `S-9` 與本站直接相關**：步 8 會把靜止前置寫進 `DEPLOY.md`，但**管線本身還做不到**
——`deploy.yml:121–124` 用單一 `up -d --build` 一次拉起整座 stack。實作者不得因此
認為靜止已經生效。

---

## 五、共用檔異動後的重新驗證與補審（2026-10-29 使用者裁決：一次重開 15 個審查失效的單元）

**來源**：整站送審被擋（`REQUIRED_SOURCE_WORK_MISSING`）。比對本單元最新審查收據（`reviewed-source-*.tsv`）與現況，對不上的清單內檔案為：`DEPLOY.md`。這是合併前必修第 22–26 項在其他單元所做的修正。本節**不改程式**，只重新驗證並補審。

- [x] **重新驗證**：以收據比對與 `git diff` 逐 hunk 確認 `DEPLOY.md` 的變動來源（哪一項合併前必修、改了哪幾行），判定是否觸及本單元的段落（2.2.7 遷移、回復程序、刪除使用者的行為）；其餘清單內檔案與收據逐位元相同（以 `shasum -a 256` 逐檔比對）。
- [x] **回歸**：在暫存區副本（`PYTHONDONTWRITEBYTECODE=1`、`-B`，不在工作樹產生快取）跑本單元兩支測試檔與全套；`code-summary.md` 末尾追加「共用檔異動後重新驗證」一段（`date -u` 時間戳、逐檔結論、測試結果）。
- 追溯：`merge-blockers.md` #22–#26。

## 六、前輪審查（review-03）未處理的 Minor 一併處置（2026-10-29）

**來源**：`reviews/review-03.md` READY，但 R-03～R-08、R-10～R-13 共 10 項 Minor 為 Unresolved。**處置原則**：本輪**不改任何程式碼與共用檔**——`DEPLOY.md`、`user_router.py` 等檔在多個單元的審查收據內，改動會讓其他單元的審查再次失效（本次 15 個單元重開的成因）。因此需要動程式或共用文件的項目，改為在 `code-summary.md` 如實記載為已知限制並指派落點；只動本單元紀錄檔即可解決的項目直接修。

- [x] **R-03**：`code-summary.md §六.3` 補「一致性測試鎖不到什麼」清單（型別與長度、`NOT NULL`、`PRIMARY KEY`、外鍵目標與 `ON DELETE`、`CHECK` 內容含 `source` 列舉、預設值、欄位順序、`uq_*` 是否仍為 `UNIQUE` 與其 `WHERE is_default` 條件），並寫明這些只由尚未存在的真實 PG CI job（`U4-V1`）承接。
- [x] **R-04**：`code-summary.md §六.3` 標題與內文改為 DDL 存在**三處**，寫明 `schema.sql` 是刻意不加鎖的參考副本，列出它目前與 `schema_rbac.sql` 的差異（以讀檔逐項實查，不憑 review 轉述）。
- [x] **R-05**：`traceability.json` 的 `SEC-4` 列 note 補：刪圖時 `diagram_id ON DELETE CASCADE` 會一併刪除變更紀錄，是與未實作的 90 天清除並列的第二條無稽核消失路徑；接受的補救依 `code-summary.md §七.2` 為獨立保留表或軟刪除，不得改回 `NO ACTION`。
- [x] **R-06**：`traceability.json` 的 `BR2.4` 列改為實數（以 `grep -c 'def test_'` 計 `test_hierarchy_migration.py`，並寫明其中哪一個案例不呼叫 `migrate_hierarchy`）。
- [x] **R-07**：`code-summary.md` 記載獨立指令的三個結束碼（0 成功、1 遷移失敗（進度保留，處理後重跑）、2 呼叫方式錯誤（未執行任何事））；並記為已知落差：`run_hierarchy_migration.py` 的 `main()` docstring 與 `DEPLOY.md` 2.2.7 尚未更新，落點為 build-and-test 前的文件同步（不在本輪改，理由見本節處置原則）。
- [x] **R-08**：`code-summary.md` 記載 `default_pairs_created` 只以專案是否新建計數，在「預設專案在、預設系統缺」的人工介入狀態會低報；docstring 補註留待同一次文件同步。
- [x] **R-10**：`code-summary.md` 記載刪除使用者的成功路徑稽核訊息不含被清除的專案／系統／需求欄位筆數，屬 ADR-0006 audit logging 面向的已知缺口，落點為合併前或 build-and-test（需改 `user_router.py`）；`unit-test-instructions.md` 已補註需求欄位屬清除範圍（conductor 於核可前完成，開發者核對）。
- [x] **R-11**：`code-summary.md` 記載 409 `detail` 尚無下一步提示（`DEPLOY.md` 已列 11 類阻擋類別並建議停用），落點同 R-10。
- [x] **R-12**：在暫存區副本做突變：把 `reject_authorization_request` 的 `requested_role` 改回 commit 後才讀，確認 `test_user_delete_hierarchy` 的 (f) 轉紅，還原後複綠；結果寫入 `code-summary.md` 突變表。**只在副本上改，不改工作樹。**
- [x] **R-13**：`code-summary.md` 記載預檢到 commit 之間無鎖的已知競態（低頻手動動作，PostgreSQL 預設隔離層級不擋），docstring／`DEPLOY.md` 記載留待同一次文件同步。
- [x] **勾選重設**：若重開使本計畫既有勾選被重設，逐步核對全部步驟在 repo 現況下仍成立後勾回；在 `code-summary.md` 記錄勾回數與未勾數（`grep -c` 實算）及未勾理由。
- [x] **收尾**：`python3 scripts/validate_repo_contract.py` 綠；`traceability.json` 以 `python3 -I` 的 `json.load` 驗證；`code-summary.md` 末尾記一行處置紀錄（`date -u`）。
- 追溯：review-03 R-03～R-08、R-10～R-13。

## 七、合併前必修第 28 列的剩餘部分（2026-11-01，2026-10-31 Request Changes）

**來源**：2026-10-31 的 Request Changes 要求合併前必修清單各列在所屬單元修正並附測試。共用檔已集中於 `brain-infra` 修正（`merge-blockers.md` 第 41 列）：第 28 列 (c) 409 `detail` 下一步提示、(d) 無鎖競態的記載，以及 `DEPLOY.md` §2.2.7 的結束碼 2，皆已由 `brain-infra` A4 完成。留在本單元的只有兩處非共用檔的 docstring（`brain-infra/code-generation/code-summary.md` A13 交接清單）。本節只改 `backend/scripts/run_hierarchy_migration.py` 與新測試檔，不改其他程式或共用檔；偏離與理由只寫進 `code-summary.md`，**不得改動本計畫既有內文**（只勾選格子）。

- [x] **(a) `main()` docstring 補結束碼**：寫明三個結束碼——0 成功、1 遷移失敗（進度保留，處理後重跑）、2 呼叫方式錯誤（未執行任何事）——與程式實際行為逐一核對（附行號），並與 `DEPLOY.md` §2.2.7 的現行敘述一致。
- [x] **(b) `MigrationCounts` docstring 補低報說明**：寫明 `default_pairs_created` 只以預設專案是否新建計數，在「預設專案在、預設系統缺」時會低報（系統被補建但計數為 0）。
- [x] **新測試（新檔 `backend/tests/test_hierarchy_migration_exit_codes.py`）**：先查既有 `test_hierarchy_migration.py` 是否已涵蓋，不重複既有案例；至少斷言 (1) 呼叫方式錯誤時 `main()` 回 2 且未呼叫 `migrate_hierarchy`；(2) 「預設專案在、預設系統缺」時補建系統但 `default_pairs_created` 為 0（把 docstring 所述的低報行為鎖住）；(3) 兩處 docstring 含上述說明（防止文件再度落後程式）。沿用 `tests/helpers.py` 的 SQLite 慣例、首行 `import tests.helpers`。
- [x] **突變驗證**（只在副本）：把結束碼 2 改為 1、把低報改為「補建系統也計數」、刪除 docstring 的結束碼 2 說明，各自確認新測試轉紅；還原後與原檔 sha256 相同且全綠。突變內容與結果寫進 `code-summary.md`。
- [x] **共用檔重驗與回歸（副本）**：以最新收據逐檔 `shasum -a 256` 比對，對變動檔讀收據之後的改動並判定是否觸及本單元（`schema_rbac.sql` 三表 DDL、遷移腳本、`DEPLOY.md` §2.2.7、刪除使用者路徑），結論附行號；在副本跑本單元測試檔（含新檔）與後端全套須綠，記下實跑數。
- [x] **前輪審查**：最新一份審查（`reviews/review-04.md`）的每一項，逐項附行號確認現況；只需改紀錄者在 `code-summary.md` 就地補記，需改共用檔者記為已知限制交 conductor。
- [x] **勾選重設與收尾**：對本計畫既有各格逐格重勾（證據不成立者維持未勾並寫明理由），以 `grep -c` 實算已勾／未勾寫進 `code-summary.md`；`traceability.json` 補第 28 列 (a)(b) 的落點並保持合法 JSON；`source-manifest.json` 補新測試檔；`validate_repo_contract.py`、`validate_env_contract.py` 綠；`code-summary.md` append 本輪一節（`date -u` 時間戳）。
- 追溯：`merge-blockers.md` #28 (a)(b)；review-03 R-07、R-08。
