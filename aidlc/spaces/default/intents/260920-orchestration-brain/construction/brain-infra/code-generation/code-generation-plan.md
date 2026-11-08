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

## 共用檔異動後的重新驗證與補審（2026-10-29 使用者裁決：一次重開 15 個審查失效的單元）

**來源**：整站送審被擋（`REQUIRED_SOURCE_WORK_MISSING`）。比對本單元最新審查收據（`reviewed-source-*.tsv`）與現況，對不上的清單內檔案為：`.github/workflows/deploy.yml`、`DEPLOY.md`。這些是合併前必修第 22–26 項在其他單元所做的修正。本節**不改程式**，只重新驗證並補審。

- [x] **重新驗證**：以收據比對與 `git diff` 逐檔確認上列檔案的變動來源（哪一項合併前必修、改了哪幾行），並判定是否觸及本單元的段落或行為；其餘清單內檔案與收據逐位元相同。
- [x] **回歸**：在暫存區副本（設 `PYTHONDONTWRITEBYTECODE=1`，不在工作樹產生快取）跑本單元的測試；`code-summary.md` 末尾追加「共用檔異動後重新驗證」一段（`date -u` 時間戳、逐檔結論、測試結果）。
- 追溯：`merge-blockers.md` #22–#26。

## 重新驗證審查（review-03）的五項文件修正（2026-10-29：重開本單元一併處理）

**來源**：review-03 判 NOT-READY，五項皆為前輪既有、文件陳述過期，**不涉及程式**。R-01 已在 Step 6 就地標註。本節**不改程式、不改部署資產**。

- [x] **R-02**：`traceability.json` 的 AC2.1.4、S-8、S-9 三列 note 末尾追加「截至 HEAD：policy 為 `noeviction`；deploy 為 7 個服務、記憶體上限共 11 項（含 `mcp-bridge`）」（先實查 compose 確認數字再寫）。
- [x] **R-03**：`unit-test-instructions.md` 本單元命令改為 `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -B -m unittest …`，`test_vector_extension_bootstrap.py` 的測試數更正為實數（先數 `def test_`）。〔2026-10-29 更正，review-04 新發現 Major：上一輪此格被勾選，但當時該檔**並未修改**——改檔會使計畫核可失效，故改採替代做法記在 `code-summary.md`，勾選與事實不符。本輪重開時，由 conductor 在計畫修訂階段（核可之前）直接修改該檔：兩處命令改用 `.venv/bin/python -B` 並加 `PYTHONDONTWRITEBYTECODE=1`、補直譯器說明段、第四節標題改為「規劃 6／實作 7」「規劃 5／實作 9」、第五節補實作合計 16。本格由開發者以 `grep` 核對該檔現況屬實後才勾。〕
- [x] **R-04**：`code-summary.md`「19 項合併前必修與本單元的關係」補一張「跨單元落點」表：#15、#16、#18、#19 各會改到本單元哪個檔、由哪個單元負責、改完是否需回頭重驗本單元勾選；#19 註明 `deploy.yml` 的 required-secret 檢查已存在（附實際行號）。
- [x] **R-05**：`code-summary.md` 後續變更第 3 點補一句「`mcp` 網段的明文往返屬合併前必修 #7，本單元的網路分段不處理 encryption」。
- [x] **收尾**：`validate_repo_contract.py` 綠；`code-summary.md` 末尾記一行處置紀錄（`date -u`）。
- 追溯：review-03 R-01–R-05。

## 審查 review-04 的四項修正（2026-10-29：第三次重開本單元）

**來源**：review-04 判 NOT-READY。R-01、R-02、R-04、R-05 已 Fixed；新發現 1 Major ＋ 3 Minor，全為文件陳述，**不涉及程式**。

- [x] **Major（R-03 勾選不實）**：見上一節 R-03 格的更正註記；核對 `unit-test-instructions.md` 現況（`grep -n '.venv/bin/python -B'` 兩處、`實作 7`、`實作 9`），屬實後勾上一節 R-03 格。
- [x] **Minor（R-03 理由不一致）**：改寫 `code-summary.md` 末節「五項文件修正的處置」的 R-03 條：說明說明檔現已直接修正，並寫明上一輪不改的真正原因——核可綁定的是計畫、測試說明與 Testing Contract 三者的內容，核可之後改其中任一份都會讓核可失效；`traceability.json` 與 `code-summary.md` 不在綁定範圍內，計畫的勾選也不計入。正確做法是在核可**之前**的計畫修訂階段改，本輪即如此。
- [x] **Minor（I2 note 漏改）**：`traceability.json` 的 I2 列 note 末尾追加與 S-8 相同的「截至 HEAD 實查」標註（deploy 7 個服務、記憶體上限共 11 項）；之後 `grep` 全檔「六個 deploy」「6 個服務」「十個服務」等舊形式，確認無其他殘留。
- [x] **Minor（勾選數與摘要矛盾）**：本單元重開時引擎會重設計畫的勾選。開發者逐步核對本計畫**全部**步驟仍成立後重新勾回（「本計畫刻意不做的事」等非步驟格除外），並在 `code-summary.md` 末尾記一段：重開會重設勾選、本輪勾回的數量（以 `grep -c '^- \[x\]'` 實算）、仍未勾的格與理由。
- [x] **收尾**：`python3 scripts/validate_repo_contract.py` 綠；`code-summary.md` 末尾記一行處置紀錄（`date -u`）。
- 追溯：review-04 新發現 1–4。

## 合併前必修：共用檔集中修正（2026-10-31 Request Changes）

**來源**：使用者送出 Request Changes，要求修正 `construction/functional-design/merge-blockers.md` 第 2 列剩餘部分、第 20／29、21、25、27、28、30–40 列，各在所屬單元修正並附測試。2026-10-31 使用者另裁決（`date -u` 2026-10-31T15:57:57Z 前後逐題取得）：**凡改到「出現在 ≥2 個單元審查收據」的共用檔者，集中在本單元一次改完**，只屬單一單元的程式與測試留在所屬單元；新測試**另開新檔**，不加進共用測試檔。理由：引擎依序重審 24 個單元，本單元第一個；共用檔若分散在後面的單元改，每改一次就讓前面已審完的單元收據失效。

**本節做完後，後續 23 個單元一律不得再改下列共用檔**：`DEPLOY.md`、`LOCAL-DEV.md`、`schema_rbac.sql`、`.github/workflows/ci.yml`、`.github/workflows/deploy.yml`、`deploy/*`、`openapi.json`、`frontend/src/types/api.d.ts`、`backend/requirements.txt`、`backend/scripts/run_meta_schema_migration.py`、`backend/scripts/verify_meta_schema.sql`、`backend/scripts/verify_memory_schema.sql`、`backend/services/{user_router,hierarchy_facade,membership_facade,membership_service,memory_errors,memory_facade,memory_router,session_store}.py`、`backend/tests/{test_membership_endpoints,test_membership_facade,test_mcp_bridge_e2e}.py`、`frontend/src/components/Sidebar.tsx`、`frontend/src/components/brain/ContextBar.tsx`、`frontend/src/pages/MemberDetailPage.tsx`、`frontend/tests/e2e/{a11y,memory-page}.spec.ts`。若後續單元發現非改不可，停下回報 conductor。

**使用者裁決（逐題，皆選建議項）**：第 25 列＝刪除專案／系統時同時要求呼叫者為該專案 `project_admin`；第 31 列 (a)(e)＝自我降級／移出的管理者計數與升任管理者都套合格判定；第 31 列 (g)＝只寫進文件、SQL 不變；第 31 列 (f)＝加固（全域檢查加看核准狀態、橫幅兩方法補授權）；第 33 列 (a)＝改走 `MemoryFacade`；(b)＝`MemoryError` 更名為 `MemoryServiceError`；(e)＝`content`、`query` 上限皆 4000 字元，超過回 422；第 34 列 (a)＝`role` 限 32 字元；(b)＝記進文件不優化；第 36 列 (a)＝補取捨註解（Lua 檔歸 work-orchestrator，本節只改 `DEPLOY.md` 部分）；第 38 列 (a)＝`sse-starlette`、`mcp-types` 精確釘進 `requirements.txt`（版本取 `.venv` 現裝）；第 40 列 (a)＝補齊 `@note`、第 21／22 點保留 `US9.2`；(i)＝做；測試落點＝新檔；第 20 列記憶角色預設名 `cloud360_memory`、密碼變數 `MEMORY_DB_PASSWORD`（GitHub secret，由使用者新增；本單元只核對名稱落在 secrets，不讀值）。

- [x] **A1 第 20／29 列（記憶專用資料庫角色）**：`schema_rbac.sql` 建立登入角色 `cloud360_memory`（密碼以 `psql -v` 變數由部署端帶入，不寫進 SQL），只授與 `memory` schema 的 USAGE 與所需表權限，`REVOKE` 其對 `public` schema 的權限；`backend/database.py` 新增記憶專用 engine／session（由新變數組成；未設定時的本機與 SQLite 測試行為須寫明，不得靜默退回擁有者帳號而宣稱邊界生效）；`deploy/render-env.sh` 寫入、`deploy/.env.example` 列出、`deploy/docker-compose.deploy.yml` 消費、`deploy/docker-compose.test.yml` 給測試值；`deploy.yml` 的必要 secret 檢查加入 `MEMORY_DB_PASSWORD`；`backend/.env.example`、`LOCAL-DEV.md`、`DEPLOY.md:535` 與 `schema_rbac.sql` 說明同步、改成與實際一致；CI `memory-schema` job 以該角色連線，斷言讀不到 `public` 任一表、寫得進 `memory` 的表。記憶表的實際存取改用新 session 屬 memory-service 單元（`memory_service.py`），本格只提供連線並在 `code-summary.md` 寫明交接點。設計卡住（例如角色建立與既有 `schema_rbac.sql` 重跑語意衝突）即停下回報。
- [x] **A2 第 21 列**：`membership_service.py:573-636` `projects_losing_last_admin`：除被停用者外沒有任何成員時放行，有其他成員但都不合格時照舊擋；docstring 與 `DEPLOY.md` 刪除使用者小節同步；既有 `test_membership_endpoints.py` `test_E6` 前半段依新規則修改；新增 `backend/tests/test_membership_lone_owner.py`：停用 200 再刪除 200、另有一位不合格成員時仍 409，各做一次突變。
- [x] **A3 第 25 列**：先查證建立者能否被降為一般成員（`membership_facade.change_role`、自動改選、邀請等所有改寫建立者成員列的入口），結論附檔名行號寫進 `code-summary.md`；`hierarchy_facade.py:295-321` 刪除專案與系統改為同時要求呼叫者為該專案 `project_admin`；新增 `backend/tests/test_project_delete_requires_admin.py`：被降級的建立者 → 拒絕且資料不變、仍為管理者的建立者 → 成功，附突變。
- [x] **A4 第 27、28 列（`user_router.py` 與 `DEPLOY.md` 部分）**：`_hard_delete_user`（`:581`）回傳清除摘要，兩處 `_audit_append`（`:992`、`:1206`）寫入清除的專案／系統／需求欄位筆數；409 `detail` 加下一步提示；docstring 與 `DEPLOY.md` 記載「預檢到 commit 之間無鎖」的競態；`DEPLOY.md` §2.2.7 補結束碼 2。新增 `backend/tests/test_user_delete_audit_counts.py` 斷言稽核內容含筆數與 409 `detail`，附突變。
- [x] **A5 第 30 列**：`system_requirement_fields` 恰為 9 欄的斷言；`run_meta_schema_migration.py:195-199` 7 條外鍵全核、鍵值帶欄名（分得出 `user_id` 與 `invited_by`）；`verify_meta_schema.sql:99`、`ci.yml:328`、`:383`、`DEPLOY.md:801` 的條數與歸屬更正。
- [x] **A6 第 31 列（共用檔部分）**：(a) `admin_count_after`（`membership_service.py:430-465`）只數合格管理者並更新 docstring；(e) `change_role`（`membership_facade.py:339-402`）升為 `project_admin` 時要求對象合格；(f) `_authorize_global`（`:101-119`）加看 `authorization_status`，重選橫幅兩方法補授權檢查；(b)(c)(g) `DEPLOY.md` §2.2.10 拿掉「孤兒擁有者」歸因、記載守門依賴後端至少啟動一次與回填不看 `is_active`，`schema_rbac.sql` 說明同步。新增 `backend/tests/test_membership_eligibility_guards.py` 涵蓋 (a)(e)(f) allow／deny，附突變。
- [x] **A7 第 32 列 (d)(f)、第 34 列 (b)(g)、第 36 列 (c)、第 37 列 (c)（`DEPLOY.md` 文字）**：§2.2.11 寫明假的「清除逾期」issue 的辨識方式與併入後以 `dry_run=true` 首次煙霧測試、失敗即停用排程；`:1824` 標明序列化位元組下界與配置器前提、staging 首次部署量一次 `MEMORY USAGE`；容量表記追加時重新編碼整段的成本（每次最多約 200 KB）；`:1829`、`:1833` 註明 Redis 大版本升級後須重跑；`:2239` 懸空引用改掉。
- [x] **A8 第 33 列（共用檔部分）**：(a) `MemoryFacade` 新增計數方法，`user_router.py:29-30`、`:512`、`:517` 改呼叫它；(b) `MemoryError` 更名為 `MemoryServiceError`（`memory_errors.py:51`、`memory_facade.py:88`、`:508` 及全 repo 引用，含 intent-router 與 memory-page-ui 所屬檔），以既有測試鎖住；(e) `memory_router.py` 的 `content`、`query` 上限 4000 字元、超過 422，重 dump `openapi.json` 並重產 `frontend/src/types/api.d.ts`；(g) `ci.yml:625` 步驟名改成與實際測試一致。新增 `backend/tests/test_memory_input_limits.py`（4000 過、4001 回 422）與計數走門面的測試，附突變。
- [x] **A9 第 34 列（共用檔部分）**：(a) `session_store.py:309` `role` 超過 32 字元拒寫；(h) `:619` docstring 改正（不會補 `userId`）；(d)(e)(f)(i) `deploy.yml:452-455` 「placed LAST」說法改正、`:508`／`:553` 的 `hgetall | sort` 改成能抓到欄位值互換的比對、`:238`／`:479` 的 `--pass` 改用 `REDISCLI_AUTH` 並 mask、`:520` 引用行號改為 `:309-314`。新增 `backend/tests/test_session_role_limit.py`，附突變。
- [x] **A10 第 35 列 (c)、第 40 列 (a)(d)(i)（前端共用檔）**：`Sidebar.tsx:247` `<nav>` 補 `aria-label="我的記憶"`；`MemberDetailPage.tsx:289` 改 `aria-labelledby` 指向標題、`ContextBar.tsx:109` 骨架改 `role="status"`；`a11y.spec.ts` 為 27 個 test 補齊 `@note`（第 21／22 點保留 `@story US9.2`）、新增成員詳情頁 `projectId` 非數字固定句的掃描點；第 35 列 (c) 的 e2e 斷言放新檔 `frontend/tests/e2e/sidebar-landmarks.spec.ts`。`a11y-baseline.json` 不得新增條目。
- [ ] **A11 第 38 列 (a)**：`backend/requirements.txt` 精確釘選 `sse-starlette`、`mcp-types`（版本以 `backend/.venv/bin/pip show` 取得），CI 安裝驗證。
- [x] **A12 驗證（實體副本）**：依 `unit-test-instructions.md` 現況註記，在 scratchpad 實體副本跑後端全套 `unittest discover`、`dump_openapi.py --check`、`npm run lint`、`npm run check:types`、`npm run build`，以及受影響 e2e（`a11y`、`memory-page`、`member-pages`、`project-pages`、新 `sidebar-landmarks`）；本單元自身測試；`validate_repo_contract.py`、`validate_env_contract.py`。CI 的 PostgreSQL job（`memory-schema` 等）本機無法跑者寫明，不宣稱已驗。各格突變結果與實跑數寫進 `code-summary.md`。
- [x] **A13 收尾**：`code-summary.md` append 本節一段（`date -u`）：逐格改動檔與行號、查證結論（A3）、交接給各所屬單元的事項（memory-service 改用記憶 session、各單元自己的單檔修正）；`source-manifest.json` 加入本節新寫的檔；`traceability.json` 補列號追溯並保持合法 JSON。
- 追溯：`merge-blockers.md` 第 20、21、25、27、28、29、30–38、40 列的共用檔部分。第 2 列 (b) 已由 entry-page-ui 修畢、第 17 列已以期限處置，兩列只由 conductor 更正狀態字。

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

- [x] 確認 `python -m unittest` 可在 `backend/` 下執行（既有，`ci.yml` 已在用）
- [x] 把本單元專屬（非全專案）的測試命令寫進 `unit-test-instructions.md`
- [x] 確認 `python3 scripts/validate_env_contract.py` 與 `python3 scripts/validate_repo_contract.py` 可執行

**依據**：Testing Contract `runner_ready_before_first_test: true`。本單元為 brownfield，
執行器已存在，本步驟是**驗證**而非 bootstrap。

### Step 2 — Data model / database behavior：實作

- [x] `schema_rbac.sql` 加 `CREATE EXTENSION IF NOT EXISTS vector;`（清單第 11 項，**blocking**）
- [x] `backend/database.py` 新增 `_ensure_vector_extension()`，**呼叫點在 `Base.metadata.create_all()`（`:76`）之前**（清單第 12 項）

**這一步最容易做錯的地方**：既有六支 `_ensure_*_schema()` 全在 `create_all()` **之後**
（`:78–83`），新的這一支方向相反。判準二元：呼叫必須出現在 `create_all()` 那一行**之前**。

### Step 3 — Data model / database behavior：寫測試並執行（test-after）

- [x] `backend/tests/test_vector_extension_bootstrap.py`（新檔，5–8 個測試）

涵蓋：(1) `_ensure_vector_extension` 存在且可呼叫；(2) 以 `unittest.mock` 斷言
`init_db()` 內的**呼叫順序**——`_ensure_vector_extension` 先於 `create_all`；(3) 該函式對
已存在的 extension 為冪等（`IF NOT EXISTS`）；(4) 該函式在 SQLite 測試環境下不炸
（沿用 `backend/tests/helpers.py` 的 psycopg2 mock 策略）；(5) `schema_rbac.sql` 含
`CREATE EXTENSION IF NOT EXISTS vector;`；(6) **blocking 同步斷言**——`schema_rbac.sql` 提到
vector extension 時，`DEPLOY.md` 也必須提到（把 `project.md ## Mandated` 的同步規則變成
可執行的檢查，而不是只靠人記得）。

- [x] 執行並確認綠燈，記錄輸出

### Step 4 — Environment/build configuration A：`deploy/render-env.sh`

- [x] `:44–49` 把 `REDIS_PASSWORD` 加入必填值檢查（清單第 4a 項）
- [x] `:59` 把 `REDIS_PASSWORD` 加入 `$` 擋阻名單（清單第 4b 項）
- [x] heredoc 寫出七個變數：六個字面值 ＋ `REDIS_PASSWORD` 走 `${REDIS_PASSWORD}`（清單第 4c 項）

### Step 5 — `render-env.sh` 的測試（test-after）

- [x] `backend/tests/test_render_env_redis.py`（新檔，5–8 個測試）

以 `subprocess` 在暫存目錄執行 `bash deploy/render-env.sh`，沿用
`test_repo_contract_production_paths.py` 的既有形狀（零新依賴）。涵蓋：(1) 空的
`REDIS_PASSWORD` → **非零退出**（4a 的可測判準）；(2) 含 `$` 的 `REDIS_PASSWORD` → **非零退出**
（4b 的可測判準，`project.md ## Forbidden` 的硬規則）；(3) 正常值 → 零退出且
`deploy/.env` 含七個變數名；(4) 六個非機敏變數在輸出中為**字面值**，不是空字串
（這正是審查 R-40 指出的失敗模式）；(5) `REDIS_PASSWORD` 的值等於傳入的 env 值。

- [x] 執行並確認綠燈，記錄輸出

### Step 6 — Environment/build configuration B：`deploy/docker-compose.deploy.yml`

- [x] `backend.environment:` 七個變數，**不得帶 `:-` fallback**（清單第 6 項）
- [x] 新增 `redis`／`ollama` 服務、`networks:` 分段、三個 volume（含 PG volume 改名）、
      全部服務的 `logging:` 與記憶體上限、兩個新 `healthcheck`（清單第 7 項）
- [x] 兩者的 `restart: unless-stopped` ＋ 兩條 `depends_on`（清單第 16a 項）
- [x] `redis` 的 `command:`：`--appendonly yes` ＋ `--maxmemory <值>` ＋
      `--maxmemory-policy allkeys-lru`（清單第 17a 項）
      **〔2026-10-29 就地標註，review-03 R-01〕** policy 值已依 NFR4.50／`[N3]=A` 由後續單元改為 `noeviction`（`deploy/docker-compose.deploy.yml` 約 :273-274，提交 `c2e5687a`）；本格的勾選只代表 `--appendonly yes`、`--maxmemory` 與 policy 旗標存在，**不代表** `allkeys-lru` 仍成立。
- [x] `redis` 的 ACL 設定資產，deploy 側那一份（清單第 17b 項）
- [x] **`cloudflared` 必須排除在 `internal` 之外**（D-3 的核心理由）

**記憶體上限的值**：依 `[I2b]` 的鬆綁定案，先以 `infrastructure-specification.md` `§二` 的
公開基準設值，並在 `DEPLOY.md` 記為**暫定值 ＋ 複量期限**（Step 12）。**不得猜一個沒有依據的數字**。

### Step 7 — Environment/build configuration C：`deploy/docker-compose.test.yml`

- [x] 清單第 8 項全部（`backend.environment:` Redis 三者 ＋ `EMBEDDING_PROVIDER: stub`、
      `redis` 服務、`networks:` 分段、全部服務的 `logging:` 與記憶體上限、`redis` healthcheck、
      db 映像改 PG 18 ＋ pgvector、**`redis` 的 ACL 設定資產**）
- [x] 清單第 16b 項（**只有** `redis` 的 `restart: unless-stopped` ＋ **只有一條** `depends_on`）

**這個 stack 沒有 `ollama`**（`[I5]`=A）。**不設 `maxmemory`**、**不開 AOF**、**不用具名 volume**。
ACL 資產**必須有，且不得與 deploy 共用同一份檔**。

### Step 8 — Environment/build configuration D：repo 根 `docker-compose.yml`

- [x] **只改 db 映像**為 PG 18 ＋ pgvector（清單第 9 項）。現值 `postgres:15-alpine`（`:3`）
- [x] **不套用** D-3／`S-8`／`S-9`（它 publish 端口是刻意的）

`postgres_data` volume 與 PG 18 不相容的處置寫進 `LOCAL-DEV.md`（Step 13），不在這裡處理。

### Step 9 — Environment/build configuration E：兩份 `.env.example`

- [x] `deploy/.env.example` 列出七個新變數（清單第 5 項）
- [x] `backend/.env.example` 列出 backend 讀得到的新變數（清單第 10 項）

### Step 10 — Environment/build configuration F：`.github/workflows/deploy.yml`

- [x] `deploy` job 新增獨立探測步驟，結束碼表達結果（清單第 1 項）
- [x] `rollback` job 的健康檢查迴圈併入探測，`$GITHUB_OUTPUT` 表達結果、**不用 `exit`**（清單第 2 項）
- [x] 兩個 job 的 `env:` **只新增 `REDIS_PASSWORD` 一項**（清單第 3 項）
- [x] 部署後執行一次 `ollama pull bge-m3`，含 `docker compose exec -T`、兩情形判定（清單第 15 項）

**三條硬約束**：(a) 探測的兩個判定命令**不得觸發 `set -e`**，最終結束碼由判定邏輯決定；
(b) `/api/auth/login` 的「通」是 **HTTP 401** 不是 2xx；(c) `N`／`T` 須滿足
`N × (T + 5) ≤ 1200 − 其餘實測消費`，且 `up -d --build` 是無界項**必須實測**。

### Step 11 — Environment/build configuration：驗證

- [x] `python3 scripts/validate_env_contract.py` 綠
- [x] `python3 scripts/validate_repo_contract.py` 綠
- [x] `python -m unittest discover -s tests -v`（在 `backend/`）全綠——既有套件保持綠是
      Testing Contract 的 `scope_floor` 要求

**不新增** `infrastructure-specification.md` `§六` 的補閘門 (a)–(d)——該節已明文列為
不屬本單元交付。

### Step 12 — 文件：`DEPLOY.md`

- [x] 十一項必寫內容，寫進**中文半部**（清單第 13 項）
- [x] **例外**：第 11 項的 vector extension 屬「這支 SQL 會建立的物件」，
      **中文 `### 2.` 與英文 `### Database` 兩處都要補**（blocking 規則的字面要求）
- [x] **不擴大**英文半部的其他落差，也**不宣稱**它是同步的

### Step 13 — 文件：`LOCAL-DEV.md`（blocking）

- [x] 因 `database.py` schema 補丁與兩份 `.env.example` 而同步（清單第 14 項）
- [x] 本機 PostgreSQL 必須先裝 pgvector，附可執行前置檢查
- [x] `postgres_data` volume 在 PG 15 → 18 不相容的處置

### Step 14 — 新增 secret 後的複查（清單第 4d 項，非檔案改動）

- [x] `gh api repos/<owner>/<repo>/actions/secrets` 與 `/variables` **各查一次**
- [x] 判準二元：`REDIS_PASSWORD` 須在 secrets、**不得**在 variables
- [x] 若曾誤存為 variable：**必須重新產生金鑰**，搬移不足以結案

**這一步需要 repo 寫入權與 `gh` 認證**。若本次執行環境無法查，**記為未完成項並在完成摘要
明說**，不得靜默跳過——本 repo 為 public、Actions log 公開可讀。

### Step 15 — 追溯與清單

- [x] `source-manifest.json`：列出本單元建立／修改／刪除的每一個應用來源路徑
- [x] `traceability.json`：枚舉每個指派的 AC 與 `NFRx.y`，每個 `OK` 指向一個實際存在的檔
- [x] `code-summary.md`

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
