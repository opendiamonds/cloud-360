# Code Generation Plan — `U1 brain-infra`（`packaging`）

## 〇、這個單元在做什麼，以及它為什麼不長得像一般的 code-generation

`U1 brain-infra` 的交付**沒有一行應用程式邏輯**。它的產出是 compose YAML、shell、SQL、
GitHub Actions workflow 與兩份部署文件。`unit-of-work.md:63` 逐字寫它的驗證方式是
「`validate_env_contract.py` ＋ 實際部署」。

這對本計畫有三個具體後果，先寫在最前面，避免下游把它當成一般程式單元處理：

1. **Testing Contract 的五個 testable layer 只有一個適用。** `Repository / data access`、
   `Business logic`、`Frontend behavior` 三層在本單元**不存在受測對象**——不是省略，是沒有。
   適用的是 `Data model / database behavior`（`schema_rbac.sql` ＋ `backend/database.py`）
   與 `Environment/build configuration`。省略理由逐層寫在第四節。
2. **本單元的多數交付沒有既有的自動化斷言層。** compose 的服務集合、`networks:` 分段、
   記憶體上限、`logging:` 都只有 `validate_env_contract.py` 看得到一部分，而
   `infrastructure-specification.md` `§六` 已把補閘門 (a)–(d) 明文列為**不列為本單元交付**。
   本計畫**不夾帶**那四道閘門，但也**不宣稱**本單元的 compose 改動有自動化保護——
   `§六` 的九項無閘門項目原樣成立。
3. **兩項 blocking 規則落在本單元**：`schema_rbac.sql` ↔ `DEPLOY.md` 同步（`project.md
   ## Mandated`，由第 11 項改動觸發）、`LOCAL-DEV.md` 同步（`NFR8.4`，由 `database.py`
   schema 補丁與兩份 `.env.example` 觸發）。兩者未完成不得標示本站完成。

## 一、故事追溯（story → plan step）

本單元在 `unit-of-work-story-map.md:95` 只承載**一則**故事 `US2.1`（與 `U10 session-store`、
`U14 entry-page-ui` 共享）。**不虛構其他故事連結**——其餘改動追溯到 NFR id，逐項列在第三節。

| 故事／AC | 逐字內容 | 本計畫的落點 |
|---|---|---|
| `US2.1` `AC2.1.4` | **Given** backend 重啟過，**When** 我回到入口頁，**Then** 我的對話脈絡與作業對象**完整還原** `[NFR4]` | **Step 6**（deploy compose 的 `redis` 服務：`--appendonly yes` ＋ 具名 volume ＋ `maxmemory`／`allkeys-lru`）。這是本單元對使用者可見行為的**唯一**直接貢獻 |
| `AC2.1.1`／`AC2.1.2`／`AC2.1.3` | 跨頁脈絡列的顯示與排除 | **不在本單元**——落在 `U10` 與 `U14`。本單元只提供它們所需的 session store |

**一項必須誠實記下的界線**：`AC2.1.4` 的 Then 是「完整還原」，而本單元只交付**儲存層的持久化能力**。
還原是否真的完整，取決於 `U10 session-store` 寫了什麼、以及 `U14` 讀了什麼——本單元的任何測試
都**不能**宣稱驗證了 `AC2.1.4`。本計畫的測試只驗證「AOF 有開、volume 具名、重啟後 key 還在」。

## 二、Testing Contract（由 `aidlc-testing-posture.ts render` 產生，原樣貼入）

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

## 三、實作步驟

每一步對應 `cicd-pipeline.md` `§五` 改動清單（22 列）的一列或數列。**該清單是本計畫的正式輸入**，
步驟只重述落點與判準，不重述理由——理由在那份檔裡，改動時回去讀。

### Step 1 — 確認測試執行器，記下本單元專屬命令

- [ ] 確認 `python -m unittest` 可在 `backend/` 下執行（既有，`ci.yml` 已在用）
- [ ] 把本單元專屬（非全專案）的測試命令寫進 `unit-test-instructions.md`
- [ ] 確認 `python3 scripts/validate_env_contract.py` 與 `python3 scripts/validate_repo_contract.py` 可執行

**依據**：Testing Contract `runner_ready_before_first_test: true`。本單元為 brownfield，
執行器已存在，本步驟是**驗證**而非 bootstrap。

### Step 2 — Data model / database behavior：實作

- [ ] `schema_rbac.sql` 加 `CREATE EXTENSION IF NOT EXISTS vector;`（清單第 11 項，**blocking**）
- [ ] `backend/database.py` 新增 `_ensure_vector_extension()`，**呼叫點在 `Base.metadata.create_all()`（`:76`）之前**（清單第 12 項）

**這一步最容易做錯的地方**：既有六支 `_ensure_*_schema()` 全在 `create_all()` **之後**
（`:78–83`），新的這一支方向相反。判準二元：呼叫必須出現在 `create_all()` 那一行**之前**。

### Step 3 — Data model / database behavior：寫測試並執行（test-after）

- [ ] `backend/tests/test_vector_extension_bootstrap.py`（新檔，5–8 個測試）

涵蓋：(1) `_ensure_vector_extension` 存在且可呼叫；(2) 以 `unittest.mock` 斷言
`init_db()` 內的**呼叫順序**——`_ensure_vector_extension` 先於 `create_all`；(3) 該函式對
已存在的 extension 為冪等（`IF NOT EXISTS`）；(4) 該函式在 SQLite 測試環境下不炸
（沿用 `backend/tests/helpers.py` 的 psycopg2 mock 策略）；(5) `schema_rbac.sql` 含
`CREATE EXTENSION IF NOT EXISTS vector;`；(6) **blocking 同步斷言**——`schema_rbac.sql` 提到
vector extension 時，`DEPLOY.md` 也必須提到（把 `project.md ## Mandated` 的同步規則變成
可執行的檢查，而不是只靠人記得）。

- [ ] 執行並確認綠燈，記錄輸出

### Step 4 — Environment/build configuration A：`deploy/render-env.sh`

- [ ] `:44–49` 把 `REDIS_PASSWORD` 加入必填值檢查（清單第 4a 項）
- [ ] `:59` 把 `REDIS_PASSWORD` 加入 `$` 擋阻名單（清單第 4b 項）
- [ ] heredoc 寫出七個變數：六個字面值 ＋ `REDIS_PASSWORD` 走 `${REDIS_PASSWORD}`（清單第 4c 項）

### Step 5 — `render-env.sh` 的測試（test-after）

- [ ] `backend/tests/test_render_env_redis.py`（新檔，5–8 個測試）

以 `subprocess` 在暫存目錄執行 `bash deploy/render-env.sh`，沿用
`test_repo_contract_production_paths.py` 的既有形狀（零新依賴）。涵蓋：(1) 空的
`REDIS_PASSWORD` → **非零退出**（4a 的可測判準）；(2) 含 `$` 的 `REDIS_PASSWORD` → **非零退出**
（4b 的可測判準，`project.md ## Forbidden` 的硬規則）；(3) 正常值 → 零退出且
`deploy/.env` 含七個變數名；(4) 六個非機敏變數在輸出中為**字面值**，不是空字串
（這正是審查 R-40 指出的失敗模式）；(5) `REDIS_PASSWORD` 的值等於傳入的 env 值。

- [ ] 執行並確認綠燈，記錄輸出

### Step 6 — Environment/build configuration B：`deploy/docker-compose.deploy.yml`

- [ ] `backend.environment:` 七個變數，**不得帶 `:-` fallback**（清單第 6 項）
- [ ] 新增 `redis`／`ollama` 服務、`networks:` 分段、三個 volume（含 PG volume 改名）、
      全部服務的 `logging:` 與記憶體上限、兩個新 `healthcheck`（清單第 7 項）
- [ ] 兩者的 `restart: unless-stopped` ＋ 兩條 `depends_on`（清單第 16a 項）
- [ ] `redis` 的 `command:`：`--appendonly yes` ＋ `--maxmemory <值>` ＋
      `--maxmemory-policy allkeys-lru`（清單第 17a 項）
- [ ] `redis` 的 ACL 設定資產，deploy 側那一份（清單第 17b 項）
- [ ] **`cloudflared` 必須排除在 `internal` 之外**（D-3 的核心理由）

**記憶體上限的值**：依 `[I2b]` 的鬆綁定案，先以 `infrastructure-specification.md` `§二` 的
公開基準設值，並在 `DEPLOY.md` 記為**暫定值 ＋ 複量期限**（Step 12）。**不得猜一個沒有依據的數字**。

### Step 7 — Environment/build configuration C：`deploy/docker-compose.test.yml`

- [ ] 清單第 8 項全部（`backend.environment:` Redis 三者 ＋ `EMBEDDING_PROVIDER: stub`、
      `redis` 服務、`networks:` 分段、全部服務的 `logging:` 與記憶體上限、`redis` healthcheck、
      db 映像改 PG 18 ＋ pgvector、**`redis` 的 ACL 設定資產**）
- [ ] 清單第 16b 項（**只有** `redis` 的 `restart: unless-stopped` ＋ **只有一條** `depends_on`）

**這個 stack 沒有 `ollama`**（`[I5]`=A）。**不設 `maxmemory`**、**不開 AOF**、**不用具名 volume**。
ACL 資產**必須有，且不得與 deploy 共用同一份檔**。

### Step 8 — Environment/build configuration D：repo 根 `docker-compose.yml`

- [ ] **只改 db 映像**為 PG 18 ＋ pgvector（清單第 9 項）。現值 `postgres:15-alpine`（`:3`）
- [ ] **不套用** D-3／`S-8`／`S-9`（它 publish 端口是刻意的）

`postgres_data` volume 與 PG 18 不相容的處置寫進 `LOCAL-DEV.md`（Step 13），不在這裡處理。

### Step 9 — Environment/build configuration E：兩份 `.env.example`

- [ ] `deploy/.env.example` 列出七個新變數（清單第 5 項）
- [ ] `backend/.env.example` 列出 backend 讀得到的新變數（清單第 10 項）

### Step 10 — Environment/build configuration F：`.github/workflows/deploy.yml`

- [ ] `deploy` job 新增獨立探測步驟，結束碼表達結果（清單第 1 項）
- [ ] `rollback` job 的健康檢查迴圈併入探測，`$GITHUB_OUTPUT` 表達結果、**不用 `exit`**（清單第 2 項）
- [ ] 兩個 job 的 `env:` **只新增 `REDIS_PASSWORD` 一項**（清單第 3 項）
- [ ] 部署後執行一次 `ollama pull bge-m3`，含 `docker compose exec -T`、兩情形判定（清單第 15 項）

**三條硬約束**：(a) 探測的兩個判定命令**不得觸發 `set -e`**，最終結束碼由判定邏輯決定；
(b) `/api/auth/login` 的「通」是 **HTTP 401** 不是 2xx；(c) `N`／`T` 須滿足
`N × (T + 5) ≤ 1200 − 其餘實測消費`，且 `up -d --build` 是無界項**必須實測**。

### Step 11 — Environment/build configuration：驗證

- [ ] `python3 scripts/validate_env_contract.py` 綠
- [ ] `python3 scripts/validate_repo_contract.py` 綠
- [ ] `python -m unittest discover -s tests -v`（在 `backend/`）全綠——既有套件保持綠是
      Testing Contract 的 `scope_floor` 要求

**不新增** `infrastructure-specification.md` `§六` 的補閘門 (a)–(d)——該節已明文列為
不屬本單元交付。

### Step 12 — 文件：`DEPLOY.md`

- [ ] 十一項必寫內容，寫進**中文半部**（清單第 13 項）
- [ ] **例外**：第 11 項的 vector extension 屬「這支 SQL 會建立的物件」，
      **中文 `### 2.` 與英文 `### Database` 兩處都要補**（blocking 規則的字面要求）
- [ ] **不擴大**英文半部的其他落差，也**不宣稱**它是同步的

### Step 13 — 文件：`LOCAL-DEV.md`（blocking）

- [ ] 因 `database.py` schema 補丁與兩份 `.env.example` 而同步（清單第 14 項）
- [ ] 本機 PostgreSQL 必須先裝 pgvector，附可執行前置檢查
- [ ] `postgres_data` volume 在 PG 15 → 18 不相容的處置

### Step 14 — 新增 secret 後的複查（清單第 4d 項，非檔案改動）

- [ ] `gh api repos/<owner>/<repo>/actions/secrets` 與 `/variables` **各查一次**
- [ ] 判準二元：`REDIS_PASSWORD` 須在 secrets、**不得**在 variables
- [ ] 若曾誤存為 variable：**必須重新產生金鑰**，搬移不足以結案

**這一步需要 repo 寫入權與 `gh` 認證**。若本次執行環境無法查，**記為未完成項並在完成摘要
明說**，不得靜默跳過——本 repo 為 public、Actions log 公開可讀。

### Step 15 — 追溯與清單

- [ ] `source-manifest.json`：列出本單元建立／修改／刪除的每一個應用來源路徑
- [ ] `traceability.json`：枚舉每個指派的 AC 與 `NFRx.y`，每個 `OK` 指向一個實際存在的檔
- [ ] `code-summary.md`

## 四、Testing Contract 的逐層適用判定（省略必須附理由）

| 層 | 適用？ | 理由 |
|---|---|---|
| Data model / database behavior | **適用** | `schema_rbac.sql` 的 extension ＋ `database.py` 的呼叫順序。落點 Step 2／3 |
| Repository / data access | **不適用** | 本單元不新增也不修改任何 repository 或資料存取程式。無受測對象 |
| Business logic | **不適用** | 本單元不含商業邏輯。compose 與 shell 不是邏輯層 |
| API / endpoint | **不適用** | 本單元不新增也不修改任何 HTTP 端點。`deploy.yml` 的探測是**呼叫**既有端點，不是定義端點 |
| Frontend behavior | **不適用** | 本單元不碰 `frontend/`。前端唯一自動化層是 Playwright e2e，本單元無可斷言的畫面變更 |
| Environment/build configuration | **適用** | 本單元的主體。落點 Step 4–11 |
| Documentation and traceability | **適用** | 兩項 blocking 同步。落點 Step 12／13／15 |

**測試量**：Standard = 每個元件 5–8 個測試。本單元有兩個可測元件（vector extension bootstrap、
`render-env.sh`），各規劃 5–6 個，合計 10–12 個新測試，加上三支既有驗證器的執行。

**覆蓋率**：`org.md` 的 80% line coverage 在本 repo **無量測機制**（`team.md` 已逐字記載
「既無法量測也無法強制，是宣告而非閘門」）。本單元**不新增**覆蓋率工具——那是獨立的
工具鏈決策，不由本單元夾帶；亦**不宣稱**達成 80%。

**PBT**：ADR-0006 的 property-based hard constraint 點名 IaC generator、cost calculator、
agent routing 三個模組。本單元**不含其中任何一個**，故判定 **N/A**（非豁免、非違反）。

## 五、本計畫刻意不做的事

| 不做 | 理由 |
|---|---|
| `§六` 的補閘門 (a)–(d) | `infrastructure-specification.md` `§六` 明文列為不屬本單元交付 |
| 移除 `DEPLOY.md` 的英文半部 | repo 級文件決定，需 ADR 或使用者裁決，落點不在本 stage |
| 縮窄 `rollback` job 的三項寫入權限 | `team.md` 已記載「尚未被評估過」；本單元只是提高其觸發頻率，縮窄是獨立任務 |
| 引入前端 unit／component 測試框架 | `team.md` Q4 定案 D 不採 |
| 引入 `coverage.py` | 待補承載機制，不由本單元夾帶 |
| `U10` 的 session 讀寫、`U14` 的脈絡列 | 不同單元。本單元只交付它們所需的儲存層 |

## 六、Plan Approval

見 `code-generation-questions.md`。
