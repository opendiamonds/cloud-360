# 建置與測試結果（build-and-test Step 9）

- 開工（`date -u`）：`2026-11-12T23:20:32Z`；收尾（`date -u`）：`2026-11-14T02:25:17Z`（session 時鐘有跳躍，非連續工時；`local-verify-fixes.md` 已記錄同一現象）
- 受測對象：HEAD `ff537a7` ＋ **未 commit 的工作樹**（全部改動，含本站的 F1／F2／F4／語意記憶與 code-generation 的本機 Claude Code provider）
- 執行位置：全部在 scratchpad 副本 `<scratchpad>/bt-copy`（rsync 排除 `.git`、`node_modules`、`.venv`、`__pycache__`、`.hypothesis`、`.env`；前端 `node_modules` 以 `cp -Rc` 複製）。Python 一律 repo 的 `backend/.venv/bin/python -B`，`PYTHONDONTWRITEBYTECODE=1`，`HYPOTHESIS_STORAGE_DIRECTORY=<scratchpad>/hyp-bt`
- 兩支 validator 因以 `git ls-files` 掃描，在 repo 內以 `python3 -B` 執行（唯讀）
- 臨時服務：`pgvector/pgvector:pg18`（只綁 `127.0.0.1:55499`，密碼 `[REDACTED]`）、`redis:7.4.8` 與 `redis:8-alpine`（只綁 `127.0.0.1:56499`），用完皆以 `docker rm -f` 刪除；未連 `$S/local-run` 的任何服務、未連 staging 或共用 DB／Redis
- 未 commit、未 push、未跑 `gh`、未觸發 CI；**未改任何產品程式碼**
- 原始輸出全部在 `<scratchpad>/bt-logs/`

## 本站內的程式修正（未經 loop-back）

**這是一項流程偏離，如實記載。** 2026-11-12 使用者在本機驗證（`$S/local-verify-findings.md`）後指示「修正好，然後盡快部署」，以下四項因而**在 build-and-test 站內直接修改產品程式**，**沒有**依 Step 9 的 failure ladder 退回 code-generation 重開單元與重審：

| 項目 | 性質 | 改動範圍（詳見紀錄） |
|---|---|---|
| F1 架構圖掛到系統 | **範圍新增**（見下節） | `hierarchy_service.py`、`hierarchy_facade.py`、`hierarchy_router.py`（新端點 `PUT /api/hierarchy/diagrams/{id}/system`）、`collab_router.py`、`openapi.json`、`api.d.ts`、`projectsApi.ts`、`SystemDiagrams.tsx`（新）、`OverviewTab.tsx`、`WorkspacePage.tsx`；新測試 11 案＋e2e 3 案 |
| F2 指涉對象解析 | 既有能力（FR1、BR64.9／BR64.11）的缺陷修正 | `intent_routing_context.py`、`intent_routing.py`、`brain_gateway_rules.py`、`brain_gateway.py`；新測試 8 案（含 2 個 Hypothesis 性質） |
| F4 失敗工作卡位置 | 既有能力（BR94.5）的呈現缺陷修正 | `ConversationView.tsx`（conductor 實作）；e2e 1 案 |
| 對話寫入語意記憶 | **範圍新增**（見下節） | `brain_gateway_rules.py`、`brain_gateway.py`；新測試 15 案＋`tests_pg` 1 案＋e2e 1 案；`ci.yml` 步驟名稱 |

- **依據**：使用者在本機驗證後的直接指示（記於 `local-verify-fixes.md` 兩輪的檔頭）。
- **紀錄位置**：`construction/build-and-test/local-verify-fixes.md`（設計決定、改動檔與行、ADR-0006 判定、突變 M1–M8 與還原 sha256）。
- **後果**：這些改動**沒有 code-generation 審查員複驗**——沒有 `REVIEW_COMPLETED`、沒有各單元 `code-summary.md`／`traceability.json` 的更新，所屬單元（hierarchy-service、brain-gateway、intent-router、entry-page-ui、memory-service）的 code-generation 收據不涵蓋這些位元組。本站的實跑（下方各節）證明它們**目前全綠、且未打破既有測試**，但不能取代獨立審查。
- **本檔沒有 `## Loop-Back Log`**：stage 檔規定該節只在 failure ladder 的 rung 3／4 觸發 loop-back 時才寫；本案不是 loop-back，故不捏造條目。

## 範圍新增（已核可 scope／requirements 尚未涵蓋，需回補）

下列三項**不得**讀成既有 FR 的自然延伸。它們在 `requirements.md` 與 `stories.md` 都沒有 FR／AC，所以 `cross-unit-traceability.md` 的列舉看不到它們：

| # | 能力 | 新增於 | 為何不是既有需求的延伸 | 回補項（requirements） | 回補項（user-stories） | 目前暫掛 |
|---|---|---|---|---|---|---|
| S-1 | **F1 架構圖掛到系統**（存檔時帶 `system_id` ＋ 系統頁掛圖／改掛／取消） | build-and-test（2026-11-12） | `FR9.1` 只說「系統對應架構圖檔」、`FR9.5` 只要求專案／系統的建立路徑；全 backend 原本唯一寫 `user_diagrams.system_id` 的是一次性遷移（`OPEN-H11`） | 新 FR：兩條寫入路徑、資格規則（`K2 edit`＋圖擁有者＋目標專案可見＋擁有者）、存檔帶不合格系統須明確回錯不建檔；歸屬變更是否需正式稽核列 | 新 AC：存檔掛載、系統頁掛圖／改掛／取消、拒絕態（403／404、不建檔） | `@story US9.1` |
| S-2 | **對話寫入語意記憶**（「請記住…」→ 確認 → 寫入 `semantic`） | build-and-test（2026-11-12） | `FR4.1` 要三種記憶，但 `OQ-N3` 只落地情節記憶的寫入端；本輪前全 backend 無任何 `write(…, "semantic", …)` | 新 FR：觸發句型、寫入前確認、擁有者／範圍沿用 `FR4.3a`／`FR4.3b`、拒寫條件（疑似憑證／個資、500 字上限）、`fulltext` 下明確回錯；「建立」是否需稽核 | 新 AC：確認後寫入、取消不寫、拒寫態、記憶頁可見可刪、下一輪預取讀得到 | `@story US4.1` |
| S-3 | **本機 Claude Code provider**（`LLM_PROVIDER=claude-code`，僅 `APP_ENV=local`） | code-generation（2026-11-08，intent-router） | `scope-document.md`、`requirements.md` 皆未涵蓋（`intent-router/code-generation/code-summary.md:476` 逐字揭露） | 新 NFR：「本機開發 LLM provider」——只限本機、不得進部署設定、非 local 自動退回 openrouter、逾時 kill 子行程；`LOCAL-DEV.md` H1 改寫 | 無使用者可見 AC（開發者工具）；如需，補開發者故事 | — |

另：程序記憶仍無「從對話」的寫入端，只有交辦完成後的自動寫入（`work_orchestrator.py:1077`）；F8 的重複即來自此路徑。

## 建置結果

| # | 指令 | 結果 | 證據 |
|---|---|---|---|
| B1 | import smoke（`import main`） | exit 0，`app: Cloud-360 API` | `bt-logs/gates.log` |
| B2 | `dump_openapi.py --check` | exit 0，「規格檔與後端程式碼一致」 | 同上 |
| B3 | `dump_ws_contract.py --check` | exit 0，「WS 契約規格檔與後端程式碼一致」 | 同上 |
| B4 | `gen_mcp_tools.py --check` | exit 0，「MCP 工具宣告與輸入一致」 | 同上 |
| B5 | `npm run lint` | exit 0，`✖ 2 problems (0 errors, 2 warnings)`（既存 `exhaustive-deps`：`AssessmentPage.tsx:395`、`WorkspacePage.tsx:344`） | `bt-logs/fe-lint.log` |
| B6 | `npm run check:types` | exit 0，「API 型別檔與規格檔一致」 | `bt-logs/fe-types.log` |
| B7 | `npm run check:ws-types` | exit 0，「WS 契約型別檔與規格檔一致，且 sideEffect 的哨兵值說明仍在（BR4.4）」 | `bt-logs/fe-wstypes.log` |
| B8 | `npm run build`（`tsc -b && vite build`） | exit 0，`✓ built in 1.50s`（既存 chunk 大小提示） | `bt-logs/fe-build.log` |
| B9 | `validate_repo_contract.py`（repo 內） | exit 0，「Cloud-360 repository contract validation passed.」 | `bt-logs/gates.log` |
| B10 | `validate_env_contract.py`（repo 內） | exit 0，「Cloud-360 environment configuration contract validation passed.」 | 同上 |
| B11 | Docker image build | **未執行**（本站不建 image；CI `docker-build` job 承擔） | — |

**建置狀態：成功**（B1–B10 全部 exit 0；B11 未執行）。

## 測試結果

| 套件 | 指令 | 總數 | 通過 | 失敗 | 略過 | 證據 |
|---|---|---|---|---|---|---|
| 後端全套（第 1 輪） | `python -m unittest discover -s tests -v` | 1467 | 1464 | 0 | 3 | `bt-logs/unit-run1.log`（`Ran 1467 tests in 112.036s` → `OK (skipped=3)`） |
| 後端全套（第 2 輪） | 同上（無 `-v`） | 1467 | 1464 | 0 | 3 | `unit-run2.log`（113.649s） |
| 後端全套（第 3 輪） | 同上 | 1467 | 1464 | 0 | 3 | `unit-run3.log`（116.009s） |
| 真實 PostgreSQL | `python -m unittest discover -s tests_pg -v` | 16 | 16 | 0 | 0 | `bt-logs/tests_pg.log`（8.736s） |
| schema 套用 ×2（BR1.3 可重跑） | `psql -f schema_rbac.sql` 兩次 | 2 | 2 | 0 | — | `bt-logs/pg-schema.log` |
| 記憶 schema 斷言 | `verify_memory_schema.sql` | S1、S3–S15 | 全部 | 0 | — | `bt-logs/pg-verify_memory_schema.log` |
| 專案中繼 schema 斷言 | `verify_meta_schema.sql` | P1–P17 | 全部 | 0 | — | `bt-logs/pg-verify_meta_schema.log` |
| 記憶清除行為 | `verify_purge_sql.sql` | R1–R10 | 全部 | 0 | — | `bt-logs/pg-verify_purge_sql.log`（「R1-R10 全綠，fixture 已清理」） |
| 記憶專用角色邊界 | `02-memory-role-password.sh` ＋ 以 `cloud360_memory` 跑 `verify_memory_role.sql` | R0–R3 | 全部 | 0 | — | `bt-logs/pg-role.log` |
| U20 收斂步驟 | ci.yml `memory-schema` 的步驟 A–E | 5 | 5 | 0 | — | `bt-logs/pg-u20.log`（重跑後代寫值仍為 `cost`；CASCADE 通過） |
| 真實 Redis Lua（redis 8.10.2） | `tests_redis.test_work_item_lua` | 8 | 8 | 0 | 0 | `bt-logs/subset-49-redis8.log` |
| 真實 Redis Lua（redis 7.4.8） | 同上 | 8 | 4 | 4（10 個 subTest） | 0 | `bt-logs/subset-49.log`——見「觀察」1 |
| 單元子集合（49 組，見下） | 各單元 unit-test-instructions 的模組集合，去重後各跑一次 | 2757（含重疊） | 48 組 OK | 1 組依環境 | — | `bt-logs/subsets.tsv`、`subset-<n>.log` |
| 前端 e2e（攔截層 7 支＋真實 stack 3 支） | `BASE_URL=http://127.0.0.1:4199 npx playwright test`（對 `vite preview`） | 214 | 194 | 20 | 0 | `bt-logs/e2e.log`（`20 failed`、`194 passed (5.4m)`） |

### e2e 逐檔

| spec | 通過 | 失敗 | 判讀 |
|---|---|---|---|
| `a11y.spec.ts` | 28 | 0 | 攔截層，最新 spec 全綠 |
| `entry-page.spec.ts` | 62 | 0 | 含 F4 與語意記憶確認 2 案 |
| `member-pages.spec.ts` | 20 | 0 | |
| `memory-page.spec.ts` | 22 | 0 | |
| `object-picker.spec.ts` | 34 | 0 | 含 F1 1 案 |
| `project-pages.spec.ts` | 25 | 0 | 含 F1 2 案 |
| `sidebar-landmarks.spec.ts` | 2 | 0 | |
| `regression.spec.ts` | 1 | 13 | **環境性**：打 nginx 後的真實 backend（登入），本站未起 stack；唯一通過的是「登入頁正常顯示」 |
| `entry-page-live.spec.ts` | 0 | 5 | **環境性**：真實 WS 握手 |
| `estimate-workspace.spec.ts` | 0 | 2 | **環境性**：真實上傳 |

20 個失敗全部落在三支需要 `deploy/docker-compose.test.yml` 真實 stack 的 spec，失敗點為登入後 `toHaveURL` 等待逾時（後端不存在）。依 brief 本站不起該 stack，由 CI `ui-regression` 承擔；它**不是** AIDLC 計畫中的後續 stage，故相關目標維持 `Unverified`。

### 單元 unit-test-instructions 指令的去重與執行

24 份 unit-test-instructions 的 fenced 區塊共解析出 248 行，分類後：

| 類別 | 行數 | 處置 |
|---|---|---|
| 全套 `discover -s tests`（各種寫法） | 6 | 去重為一個指令，即上方「後端全套」，跑 3 輪 |
| 模組子集合（`python -m unittest tests.X …`） | 53 | 以模組集合去重為 **49 組**，每組一次（`bt-logs/subset-plan.txt`）；48 組 `OK`，第 49 組 `tests_redis.test_work_item_lua` 依 Redis 版本（見觀察 1） |
| 建置／漂移閘門（lint、build、check:*、dump_*、validate_*、`tsc -b`） | 13 | 去重後即 B1–B10（`tsc -b` 含於 `npm run build`） |
| e2e（各 spec、`--list`、不同 `BASE_URL`） | 15 | 以一次全套 Playwright 涵蓋；`BASE_URL=…:8090`（真實 stack）者未執行 |
| psql（schema、verify_*） | 6 | 即上方 PG 各列 |
| 靜態 grep 類 | 4 | 不另執行（屬各單元審查證據，非測試） |
| 其他 | 151 | 經抽查為 fenced 區塊內的說明文字、表格與 `cd`／`vite preview`／`gen:ws-types` 等非測試行；`gen:*` 會改寫檔案，刻意不執行 |

### 間歇性 segfault（exit 139）觀察

**0 次重現。** 觀察面：後端全套 3 輪、49 組子集合（其中 6 組含 `test_brain_gateway_*`，涵蓋 `ws_ready` 附近的握手與回合測試）、`tests_pg` 1 輪、`tests_redis` 2 輪，皆以 repo `.venv` 的 Python 3.13.7、`-B` 執行，全部正常結束、無 exit 139。條件與先前回報者的差異：先前多在 repo 內直接跑（會寫 `.pyc`），本站一律副本＋`PYTHONDONTWRITEBYTECODE=1`。未能證明其根因已消失，只能記為「本站條件下未重現」。

### 覆蓋率

無。repo 沒有 coverage 工具（`team.md` 既成事實），`org.md` 的 80% 行覆蓋率在本站為 `Unverified`（矩陣 `TC-COV80`）。

### repo 內快取檔數（開工 vs 收尾）

| 項目 | 開工 | 收尾 |
|---|---|---|
| `*.pyc`（排除 `.venv`、`node_modules`） | 243 | 243 |
| `.hypothesis` 檔數 | 352 | 352 |

## 失敗明細

| # | 測試 | 斷言／錯誤 | 判讀 |
|---|---|---|---|
| 1 | `regression.spec.ts` 13 案、`entry-page-live.spec.ts` 5 案、`estimate-workspace.spec.ts` 2 案 | `expect(page).toHaveURL(expected) failed`（例：`regression.spec.ts:206` 的 `not.toHaveURL(/\/login$/)`），逾時 10.4s | 環境性：無真實 backend。非程式缺陷證據，亦非通過證據 |
| 2 | `tests_redis.test_work_item_lua`（僅 redis 7.4.8） | `test_update_cases_match_the_reference` 6 個 subTest：`'tags': {}` != `'tags': []`；`test_update_prune_cases_match_the_reference` 4 個 subTest | 見觀察 1；部署釘 `redis:8-alpine` 下全綠 |
| 3 | （本站執行器自身）`verify_purge_sql.sql` 首次以 stdin 餵入 | `backend/scripts/purge_expired_memory.sql: No such file or directory` | 執行方式錯誤（`\i` 相對路徑）；改以 `-f` 於同結構工作目錄重跑後全綠，非產品缺陷 |
| 4 | （本站執行器自身）在主機以 psql 14 跑角色密碼腳本 | `invalid command \getenv` | 主機 psql 版本過舊；改在 pg18 容器內執行後全綠 |

## 觀察

1. **Lua 空陣列在 Redis 7.x 退化為物件**：`update_work_item.lua` 依賴 `cjson.decode_array_with_array_mt` 保留空陣列；redis 7.4.8 下 `tags: []` 經腳本後變 `{}`，redis 8.10.2 下正確。兩份 compose 皆為 `redis:8-alpine`，故部署不受影響；但 `tests_redis` 不是 CI 閘門，任何人改用 Redis 7 的環境（含舊的本機 Redis）會靜默得到錯誤形狀。建議在 `tests_redis/__init__.py` 或 `LOCAL-DEV.md` 寫明最低 Redis 8。
2. **e2e 對正式建置執行的總時間 5.4 分鐘**（含 20 個逾時案約 3.5 分鐘），`ui-regression` 的 15 分鐘上限（`a11y-gate` 交接 `H-2`）目前不是問題。

## Target Verification Matrix（最終）

完整 508 列在 `build-and-test-summary.md` 的 `## Target Verification Matrix`（每列已是最終判定，無 `Pending`）。計數：

| Verdict | 列數 |
|---|---|
| Met | 342 |
| Not Met | 0 |
| Unverified | 166 |

以下為全部非 `Met` 列（166 列，逐列；欄位與 summary 相同）：

| Target ID | Source | Expected | Actual | Evidence | Owning Stage | Verdict |
|---|---|---|---|---|---|---|
| `TC-VOLUME` | 同上 `obligations.strategy_volume`（合併為一列） | Five to eight tests per component；unit＋key-boundary integration；需求要求時加 E2E／performance／security | 本站未逐元件計數；各單元 code-summary 自記數量與偏離理由（多數高於 8，理由為 PBT／SEC 明文要求） | 各單元 `code-summary.md`（未於本站複算） | 無後續擁有 stage | Unverified |
| `TC-COV80` | `code-generation-plan.md` Testing Contract `applicable_notes[org]` | minimum 80% line coverage（feature／mvp 類 scope） | 無法量測：repo 無 coverage 工具（team.md 既成事實） | `team.md` ## Testing Posture「完全沒有覆蓋率量測機制」 | 無；導入 coverage.py 列為待補承載機制 | Unverified |
| `a11y-gate:A11Y-S1` | a11y-gate/nfr-requirements/security-requirements.md:27 | `@axe-core/playwright` 只能出現在 `devDependencies`，且不得被 `frontend/src/` 任何檔案 import | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `frontend/package.json`（非測試檔） | — | Unverified |
| `a11y-gate:A11Y-S2` | a11y-gate/nfr-requirements/security-requirements.md:28 | 新套件以 `npm install --save-dev` 加入，`package-lock.json` 同一個 commit 更新並帶 `integrity` 雜湊；CI 一律 `npm ci` | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `frontend/package-lock.json`（非測試檔） | — | Unverified |
| `a11y-gate:A11Y-S3` | a11y-gate/nfr-requirements/security-requirements.md:29 | 選定的版本在選定當天已發布**至少 14 天**，且其 `peerDependencies` 涵蓋已安裝的 `@playwright/test`（目前 `1.61.1`） | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `frontend/package.json`（非測試檔） | — | Unverified |
| `a11y-gate:A11Y-S4` | a11y-gate/nfr-requirements/security-requirements.md:30 | 新增的套件樹（`@axe-core/playwright` 與其相依）在 `npm audit` 下不得有 high／critical | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `frontend/package-lock.json`（非測試檔） | — | Unverified |
| `brain-gateway:NFR13.1` | brain-gateway/nfr-requirements/performance-requirements.md:51 | (a) 分類前段 P50 ≤ 400 ms；(b) 分類後到第一則內容 P50 ≤ 300 ms。兩段皆以伺服器端計時、不含使用者網路往返（與 `NFR3` 的量測方式一致） | 未量測（本站未執行負載／計時量測） | 相關測試：backend/tests/test_brain_gateway_turn.py | 無後續擁有 stage（計畫無 performance-validation） | Unverified |
| `brain-gateway:NFR13.3` | brain-gateway/nfr-requirements/performance-requirements.md:53 | 記憶預取的等待上限（現值 3000 ms，`BR67.12`）**依實測定值並寫明理由**（帶入項 5）：在 code-generation 量測嵌入的暖機 P50／P95 與冷載首呼叫耗時，取「≥ 暖機 P95 × 1.5」且「≤ 3000 ms」的值；冷載超過上限時接受該輪不帶記憶分類（`U11` 既有降級） | 未量測（本站未執行負載／計時量測） | 相關測試：backend/tests/test_brain_gateway_memory.py | 無後續擁有 stage（計畫無 performance-validation） | Unverified |
| `brain-gateway:NFR13.39` | brain-gateway/nfr-requirements/tech-stack-decisions.md:21 | 本單元**不新增任何套件**（無 `fakeredis`、無 `pytest`、無限流套件、無 WebSocket 客戶端套件） | traceability 狀態 OK | backend/requirements.txt | — | Unverified |
| `brain-gateway:NFR13.43` | brain-gateway/nfr-requirements/tech-stack-decisions.md:25 | （帶入項 6；`project.md ## Mandated` 的 `LOCAL-DEV.md` 同步）本單元使 `REDIS_URL`／`REDIS_USER`／`REDIS_PASSWORD` 成為**後端啟動的必要條件**（`NFR13.32`），而 `LOCAL-DEV.md:23` 目前把 Redis 寫成「 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `LOCAL-DEV.md`（非測試檔） | — | Unverified |
| `brain-infra:S-1` | brain-infra/nfr-requirements/security-requirements.md:31 | **PostgreSQL 主版本由 16 升至 18** | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `brain-infra:S-2` | brain-infra/nfr-requirements/security-requirements.md:32 | **repo 根 `docker-compose.yml` 的本機 dev db 由「不改」改為必須改** | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `brain-infra:S-4` | brain-infra/nfr-requirements/security-requirements.md:34 | **升版窗口內自動 rollback 的失效處置**（排序不變量 ＋ 窗口內停用 rollback **＋ 窗口後的復原步驟** ＋ 相容性前置檢查） | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `brain-infra:S-5` | brain-infra/nfr-requirements/security-requirements.md:35 | **Redis 設定資產與連線身分變數**（`REDIS_USER` ＋ **每個 stack 各自的** Redis 設定承載者） | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `brain-infra:NFR8.1` | brain-infra/nfr-requirements/security-requirements.md:701 | `validate_env_contract.py:168–182` `validate_deploy_stack_is_fully_supplied()` | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `deploy/render-env.sh`（非測試檔） | — | Unverified |
| `brain-infra:NFR8.3` | brain-infra/nfr-requirements/security-requirements.md:703 | 同檔 `:242–261` `validate_local_dev_template_is_complete()` | traceability 狀態 OK | backend/.env.example | — | Unverified |
| `brain-infra:S-6` | brain-infra/nfr-design/security-design.md:31 | **把 `/api` 探測加進 `deploy.yml`——`deploy` job 的獨立新步驟 ＋ `rollback` job 的健康檢查迴圈**（失敗讓 job 紅燈） | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `.github/workflows/deploy.yml`（非測試檔） | — | Unverified |
| `brain-infra:P-1` | brain-infra/nfr-design/security-design.md:395 | 請求必須命中 `location /api/`（`frontend/nginx.conf:16`），不得打 `/` | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `brain-infra:P-2` | brain-infra/nfr-design/security-design.md:396 | 受測端點的處理必須**在任何憑證比對之前查資料庫**；目前滿足此性質的是 `POST /api/auth/login`（`backend/services/user_router.py:386` 的 `db.query(...)` 在 `:389` 的 `verify_password` 之前） | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `brain-infra:P-5` | brain-infra/nfr-design/security-design.md:399 | 必須有**有界重試**，且**不得因單次請求的連線層失敗而中止整個步驟** | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `brain-infra:P-6` | brain-infra/nfr-design/security-design.md:400 | 結果的表達方式**必須沿用該 job 既有的機制**：`deploy` job 以**步驟結束碼**（失敗即紅燈），`rollback` job 以 **`$GITHUB_OUTPUT` 的 `restored`**（該步驟今天不因健康檢查紅燈） | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `brain-infra:P-7` | brain-infra/nfr-design/security-design.md:401 | 若為 `rollback` 引入新的狀態值，**同一個 PR 必須補上 `deploy.yml:381–386` 的 `case` 分支** | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `brain-ws-contract:S-1` | brain-ws-contract/nfr-requirements/security-requirements.md:38 | **修改既有的 `frontend/scripts/check-api-types.mjs` 與 `frontend/package.json` 的 `gen:types`**：移除 `npx --yes`、改用 `package-lock.json` 鎖定的本地版本、刪掉重複的版本字串 | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `brain-ws-contract:S-2` | brain-ws-contract/nfr-requirements/security-requirements.md:39 | **`K-02` 的第三次擴充**：subprotocol 的名稱與格式納入契約 | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `brain-ws-contract:S-4` | brain-ws-contract/nfr-design/security-design.md:29 | **修改既有的 `frontend/eslint.config.js`**（新增一條 error 級自訂規則），並在**同一個 PR** 內處理 `frontend/src/pages/BrainPage.tsx:83` 現存的字串字面量 | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `brain-ws-contract:S-5` | brain-ws-contract/nfr-design/security-design.md:30 | **`U2` 的交付物開始含執行期程式碼**（`BR1.5` 的 Pydantic validator）及其測試與突變驗證 | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `brain-ws-contract:S-6` | brain-ws-contract/nfr-design/security-design.md:31 | **新增 `ADR-0019`** | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `embedding-port:NFR3.1` | embedding-port/nfr-requirements/security-requirements.md:24 | **`embed` 呼叫落在首字回應路徑上**——這是本站新發現的連動，`NFR3` 的分析未計入它（見第二節）。本單元的義務是把這個事實寫下來並交付一個有上界的呼叫；**達成 `NFR3` 的 P50 ≤ 2 秒不由本單元保證**。 | 未量測（本站未執行負載／計時量測） | 相關測試：backend/tests/test_embedding_port.py | 無後續擁有 stage（計畫無 performance-validation） | Unverified |
| `embedding-port:NFR8.1` | embedding-port/nfr-requirements/security-requirements.md:30 | `NFR3.2` 新增的 timeout 環境變數**必須在同一個 PR 內**讓 `deploy/render-env.sh` 寫它、`deploy/.env.example` 列它、`backend/.env.example` 列它，並同步更新 `LOCAL-DEV.md`。 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `deploy/render-env.sh`（非測試檔） | — | Unverified |
| `embedding-port:U8-1` | embedding-port/nfr-requirements/security-requirements.md:107 | **換模型的偵測**：啟動時比對「目前 `model_id`」與「記憶表中已存在的相異 `embeddingModel` 集合」；若目前這個不在其中且表非空，記一條 **WARN 以上**的訊息寫明「既有 N 列記憶以 `<舊 model>` 寫入，本次啟動為 `<新 model>`，那些記憶在重新 embed 之前不 | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `embedding-port:U8-2` | embedding-port/nfr-requirements/security-requirements.md:108 | 寫入記憶時，必須以**同一次** `ProviderSelection` 的 `model_id()` 配對該次 `embed` 的結果，不得分兩次取。 | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `embedding-port:U5-1` | embedding-port/nfr-requirements/security-requirements.md:109 | `memory_records.embeddingModel` 的值域由 2 擴為 3（新增 `stub-v1`）且須可為 `NULL`；schema 端**不應**寫成封閉 `CHECK`（會讓換模型變成資料庫錯誤）。 | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `entry-page-ui:EPN-07` | entry-page-ui/nfr-requirements/performance-requirements.md:44 | 名稱查詢**失敗不阻斷**握手、扇出與交辦 | traceability 狀態 OK | construction/entry-page-ui/nfr-design/performance-design.md | — | Unverified |
| `entry-page-ui:EPN-11a` | entry-page-ui/nfr-requirements/security-requirements.md:35 | ③ 的判定**只有一份**：非測試程式只能取自 `MembershipFacade.project_visibility`（`membership_facade.py:518`）；`HierarchyFacade` 與 `brain_gateway` **都不得** import 成員關係符號 | traceability 狀態 OK | construction/entry-page-ui/nfr-design/security-design.md | — | Unverified |
| `entry-page-ui:EPN-16` | entry-page-ui/nfr-requirements/security-requirements.md:63 | token 只出現在 `new WebSocket` 的子協定陣列；網址**不含**查詢字串（FR8.5、`AC8.1.3`）；子協定值以 `WsSubprotocol` 型別取值（ADR-0019 §5 的既有 lint 規則） | traceability 狀態 OK | construction/entry-page-ui/nfr-design/security-design.md | — | Unverified |
| `entry-page-ui:NFR5.140` | entry-page-ui/nfr-requirements/tech-stack-decisions.md:20 | C-8 的三個名稱欄位**只**加在 `U2` 的契約模組（`brain_ws_contract.py` 的 `WorkTargetPayload`），重 dump `ws-contract.json`、重產 `ws-contract.d.ts`；前端只經產生的型別讀它們，不另寫手寫 interface | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/brain_ws_contract.py`（非測試檔） | — | Unverified |
| `entry-page-ui:EPN-21` | entry-page-ui/nfr-requirements/tech-stack-decisions.md:23 | 前後端**零新依賴** | traceability 狀態 OK | construction/entry-page-ui/nfr-design/logical-components.md | — | Unverified |
| `entry-page-ui:EPN-22` | entry-page-ui/nfr-requirements/tech-stack-decisions.md:24 | 樁訊框建構器放 `frontend/src/brain/testing/wsFrames.ts`，由既有 `tsc -b` 檢查；不新增 tests 用 tsconfig；以 ESLint `no-restricted-syntax` 限定 `frontend/tests/**` 不得出現含 `type` 鍵的物件字面 | traceability 狀態 OK | construction/entry-page-ui/nfr-design/logical-components.md | — | Unverified |
| `entry-page-ui:EPN-24` | entry-page-ui/nfr-requirements/tech-stack-decisions.md:26 | 新增測試全部放在 `backend/tests/` 與既有 `frontend/tests/e2e/`，由既有 CI 指令撿到；e2e 分兩層：真實 stack（握手、ready、狀態推送、`prompt_guard`、錯誤呈現、`BR91` 落地、Sidebar）與 `routeWebSocket`（交辦類畫面、關閉 | 斷言在真實 stack e2e，本站未起 stack | `frontend/tests/e2e/entry-page-live.spec.ts` | CI `ui-regression`（非 AIDLC stage） | Unverified |
| `entry-page-ui:EPN-25` | entry-page-ui/nfr-requirements/tech-stack-decisions.md:27 | 新方法命名為 `HierarchyFacade.describe_work_target`，**與 `intent_routing.py:155` 的私有函式 `_describe_work_target` 同名不同義**（後者是 `U11` 把 segment 轉成提示字串）。不改名，但凡以名稱做的機械檢查（grep | traceability 狀態 OK | construction/entry-page-ui/nfr-design/security-design.md | — | Unverified |
| `entry-page-ui:EPN-26` | entry-page-ui/nfr-requirements/tech-stack-decisions.md:28 | `BR98.4` 的突變驗證與本站各條「必須紅燈的突變」在 `tcms-test-cases` 的 `automation-test-plan.md` 逐條記錄 | traceability 狀態 OK | construction/entry-page-ui/nfr-design/security-design.md | — | Unverified |
| `entry-page-ui:EPN-27` | entry-page-ui/nfr-requirements/tech-stack-decisions.md:29 | 前端**不寫死**使用者訊息的字數上限 | traceability 狀態 OK | construction/entry-page-ui/nfr-design/logical-components.md | — | Unverified |
| `hierarchy-data:U4-D1` | hierarchy-data/nfr-requirements/security-requirements.md:47 | `NFR8.1` | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `schema_rbac.sql`（非測試檔） | — | Unverified |
| `hierarchy-data:U4-R2` | hierarchy-data/nfr-requirements/security-requirements.md:87 | 清除機制**不得**以 repo 內的實作程式承載（`project.md ## Forbidden` 逐字禁止以 repo 內程式承載**無人值守**的流程自動化，並以觸發來源判定：由排程觸發、無人在迴圈內者屬禁止範圍）。它必須由 **gh-aw 或 GitHub Actions workflow** 承載。**這是 | 上游標為 Deferred | traceability：S-5（gh-aw 或 GitHub Actions workflow，形式未定，落點 ci-pipeline）。本單元刻意**不**在 scripts/ 放清除程式——proje | S-5（gh-aw 或 GitHub Actions workflow，形式未定，落點 ci-pipeline）。本單元 | Unverified |
| `hierarchy-data:U4-R3` | hierarchy-data/nfr-requirements/security-requirements.md:88 | 清除的每一次執行必須留下計數紀錄（刪了幾列、最舊保留到哪一天），形狀比照 `BR2.6`。**本條在 `S-5` 落地之前是前向義務**——它規範的機制尚不存在，不是死碼但確實空轉 | 上游標為 Deferred | traceability：同 U4-R2。它規範的機制尚不存在，本 intent 結束時這張表實際上不會被清除 | 同 U4-R2。它規範的機制尚不存在，本 intent 結束時這張表實際上不會被清除 | Unverified |
| `hierarchy-data:U4-R4` | hierarchy-data/nfr-requirements/security-requirements.md:89 | 見 `§一` Encryption 列：落點 `nfr-design`，具名 `S-4` | traceability 狀態 N/A | nfr-design §一 Encryption 判定為**不做任何加密**（欄位級與傳輸皆不做）。本單元據此不引入 pgcrypto、不引入金鑰、不設 sslmode。殘餘風險（ | — | Unverified |
| `hierarchy-data:U4-V3` | hierarchy-data/nfr-requirements/security-requirements.md:104 | 遷移後該 job 必須執行不變量查詢（`system_id IS NULL` 的列數為 0），並在不為 0 時讓 job 失敗 | 上游標為 Deferred | traceability：同 U4-V1（共用 job 已存在、U4 步驟未加）。不變量查詢已在本機真實 PG 上執行並回 0 | 同 U4-V1（共用 job 已存在、U4 步驟未加）。不變量查詢已在本機真實 PG 上執行並回 0 | Unverified |
| `hierarchy-data:S-5` | hierarchy-data/nfr-requirements/security-requirements.md:167 | 一個承載 90 天清除的 gh-aw 或 GitHub Actions workflow（形式未定），以及它的計數紀錄 | 上游標為 Deferred | traceability：ci-pipeline（CONDITIONAL）。本站不實作清除 | ci-pipeline（CONDITIONAL）。本站不實作清除 | Unverified |
| `hierarchy-data:S-6` | hierarchy-data/nfr-requirements/security-requirements.md:168 | `NFR6` 的 CI job 範圍需擴及 `U4` 的遷移、前置狀態寫入、不變量查詢與**重跑斷言**——`NFR6` 自身文字只涵蓋記憶層 schema。**但不含映像**——映像已由 `brain-infra` 的 `NFR6.1` 定為 `pgvector/pgvector:pg18` 並把本 CI job 列 | 上游標為 Deferred | traceability：同 U4-V1：共用 memory-schema job 已存在（ci.yml:322），缺的是 U4 專屬步驟（遷移連跑兩次、不變量查詢、ON DELETE 實測、兩份 DDL  | 同 U4-V1：共用 memory-schema job 已存在（ci.yml:322），缺的是 U4 專屬步驟（遷移連 | Unverified |
| `hierarchy-data:S-11` | hierarchy-data/nfr-design/security-design.md:146 | `U12` 在異動架構圖**之前**必須先解出行動者；解不出即中止整個異動。且改圖與寫變更紀錄**必須在同一個交易內**。另：該失敗要呈現成可理解的訊息（比照 `BR3.2`） | 上游標為 Deferred | traceability：U12 work-orchestrator（先解出行動者再異動、改圖與寫紀錄同交易）＋ U16（訊息呈現）。本單元的承載是 actor_user_id NOT NULL ＋ COM | U12 work-orchestrator（先解出行動者再異動、改圖與寫紀錄同交易）＋ U16（訊息呈現）。本單元的承載 | Unverified |
| `hierarchy-service:NFR5.2` | hierarchy-service/nfr-requirements/security-requirements.md:64 | `NFR5`（契約閘門） | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/hierarchy_router.py`（非測試檔） | — | Unverified |
| `hierarchy-service:NFR8.1` | hierarchy-service/nfr-requirements/security-requirements.md:66 | `NFR8`（部署設定完整性） | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/hierarchy_service.py`（非測試檔） | — | Unverified |
| `intent-router:NFR1.60` | intent-router/nfr-requirements/observability-requirements.md:22 | **反問率**（`below_threshold=true` 的輪次 ÷ 總輪次）必須可量測，且**與 `NFR1` 的準確率同時呈現**。只報其中一個即為無效的品質報告 | 上游標為 Deferred | traceability：backend/services/intent_routing.py | backend/services/intent_routing.py | Unverified |
| `intent-router:NFR3.72` | intent-router/nfr-requirements/observability-requirements.md:23 | `classify` 的**耗時分佈**（P50／P95）可量測，伺服器端計時 | 未量測（本站未執行負載／計時量測） | 無計時量測工具 | 無後續擁有 stage（計畫無 performance-validation） | Unverified |
| `intent-router:NFR8.60` | intent-router/nfr-requirements/observability-requirements.md:28 | 本單元新增的環境變數（見 `tech-stack-decisions.md` `TS-4`）**缺值時的行為必須是明確的**，不得靜默取預設而讓功能降級 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/intent_routing_config.py`（非測試檔） | — | Unverified |
| `intent-router:NFR3.60` | intent-router/nfr-requirements/performance-requirements.md:30 | `IntentRouter.classify` 的**伺服器端耗時 P50 ≤ 800 ms**（從進入 `classify` 到回傳 `IntentDecision`） | 未量測（本站未執行負載／計時量測） | 無計時量測工具 | 無後續擁有 stage（計畫無 performance-validation） | Unverified |
| `intent-router:NFR3.64` | intent-router/nfr-requirements/performance-requirements.md:34 | 上述四個數值**全部可由環境變數設定**，不得寫死 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/intent_routing_config.py`（非測試檔） | — | Unverified |
| `intent-router:NFR3.65` | intent-router/nfr-requirements/performance-requirements.md:35 | 本單元**除模型呼叫以外**的耗時不列入預算：述詞 `can_single_out` 是純函式（`BR3.6`），對 ≤ N 個槽位 × ≤ M 個候選做常數級比較 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/intent_routing_predicate.py`（非測試檔） | — | Unverified |
| `intent-router:NFR3.68` | intent-router/nfr-requirements/reliability-requirements.md:17 | 模型不可用／超出用量上限時，raise `LlmUnavailable`／`LlmBudgetExceeded` 向上傳遞；**不得**回一個猜測的 `Intent`、**不得**降級為「挑第一個」 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/intent_routing_port.py`（非測試檔） | — | Unverified |
| `intent-router:NFR3.69` | intent-router/nfr-requirements/reliability-requirements.md:18 | 分類器回**空候選清單**是**失敗**，不是「判不出來」——必須走失敗路徑，**不得**當成反問 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/intent_routing_parser.py`（非測試檔） | — | Unverified |
| `intent-router:NFR3.70` | intent-router/nfr-requirements/reliability-requirements.md:19 | 模型回了**不合 schema 的輸出**（JSON 不合法、`capability` 不在封閉列舉內、`rank` 缺漏）時，一律走 `NFR3.69` 的失敗路徑 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/intent_routing_parser.py`（非測試檔） | — | Unverified |
| `intent-router:NFR3.66` | intent-router/nfr-requirements/scalability-requirements.md:25 | `classify` 在**併發**下仍須滿足 `NFR3.60`（P50 ≤ 800 ms）。負載模型：以入口頁的實際併發送出數為母體 | 未量測（本站未執行負載／計時量測） | 無計時量測工具 | 無後續擁有 stage（計畫無 performance-validation） | Unverified |
| `intent-router:NFR10.61` | intent-router/nfr-requirements/tech-stack-decisions.md:42 | 換模型後**必須重跑 `NFR1` 的 ≥50 筆標註集**，準確率數字不得跨模型沿用 | 上游標為 Deferred | traceability：backend/services/intent_routing_config.py | backend/services/intent_routing_config.py | Unverified |
| `mcp-bridge:NFR21.1` | mcp-bridge/nfr-requirements/performance-requirements.md:27 | 一次工具呼叫從送出 backend 請求到取得工具結果，**最久 10 秒**（整體上限，不是每次讀取的上限）；連線建立最久 3 秒（`BR75.1`、`BR76.1`、MB-W1 第 3 步）。逾時一律映射為 `backend_unavailable`、`retryable: true`。**注意**：httpx 的 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/mcp_bridge/executor.py`（非測試檔） | — | Unverified |
| `mcp-bridge:NFR21.3` | mcp-bridge/nfr-requirements/performance-requirements.md:29 | bridge 自身附加時間（同一 token、同一系統下，「經 MCP 工具呼叫」減「直接呼叫 backend GET」）**P50 ≤ 50 ms**。**這是預算，不是預測**：本 repo 沒有延遲量測機制，且本版無實際 client | 未量測（本站未執行負載／計時量測） | 無計時量測工具 | 無後續擁有 stage（計畫無 performance-validation） | Unverified |
| `member-pages-ui:NFR11.80` | member-pages-ui/nfr-requirements/performance-requirements.md:25 | 改角色後**不得**發生頁面切換 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `frontend/src/pages/MemberDetailPage.tsx`（非測試檔） | — | Unverified |
| `member-pages-ui:NFR11.81` | member-pages-ui/nfr-requirements/performance-requirements.md:26 | 彙總橫幅的「查看成員」導向**被點選的**那一個專案 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `frontend/src/components/membership/ReselectionBanner.tsx`（非測試檔） | — | Unverified |
| `member-pages-ui:UIP-3` | member-pages-ui/nfr-requirements/performance-requirements.md:50 | 邀請／改角色／移出成功後**不得**整份重抓成員清單 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `frontend/src/pages/MembersListPage.tsx`（非測試檔） | — | Unverified |
| `member-pages-ui:NFR4.80` | member-pages-ui/nfr-requirements/security-requirements.md:33 | 本單元**不得**把任何狀態放進瀏覽器儲存（`localStorage`／`sessionStorage`／`IndexedDB`） | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `frontend/src/membership/membershipApi.ts`（非測試檔） | — | Unverified |
| `member-pages-ui:NFR8.80` | member-pages-ui/nfr-requirements/security-requirements.md:34 | 本單元**不新增任何環境變數**，故 `render-env.sh`／`deploy/.env.example` 的同步義務對本單元為**空集合** | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `aidlc/spaces/default/intents/260920-orchestration-brain/construction/member-pages-ui/code-generation/source-manifest.json`（非測試檔） | — | Unverified |
| `member-pages-ui:SEC-U24-2` | member-pages-ui/nfr-requirements/security-requirements.md:41 | 橫幅已讀狀態以**事件**為鍵寫在伺服器；**不得**為 per-user 布林值、**不得**放瀏覽器儲存 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `frontend/src/components/membership/ReselectionBanner.tsx`（非測試檔） | — | Unverified |
| `member-pages-ui:SEC-U24-3` | member-pages-ui/nfr-requirements/security-requirements.md:42 | 前端**不驗**受邀者的全域功能權限；一律交由伺服器回 422 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `frontend/src/components/membership/InviteMemberDialog.tsx`（非測試檔） | — | Unverified |
| `membership-service:NFR12.25` | membership-service/nfr-requirements/reliability-requirements.md:65 | 回填**必須先於**任何消費端上線 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `DEPLOY.md`（非測試檔） | — | Unverified |
| `membership-service:NFR12.14` | membership-service/nfr-requirements/scalability-requirements.md:47 | **不為 `reselection_events` 加保存期限或清除作業** | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/membership_service.py`（非測試檔） | — | Unverified |
| `memory-data:NFR6.1` | memory-data/nfr-requirements/security-requirements.md:22 | episodic memory 的**靜態加密**由**主機層**承載（磁碟／LUKS），不在應用層或資料庫欄位層 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `DEPLOY.md`（非測試檔） | — | Unverified |
| `memory-page-ui:NFR8.90` | memory-page-ui/nfr-requirements/security-requirements.md:29 | 零新環境變數 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `openapi.json`（非測試檔） | — | Unverified |
| `memory-page-ui:SEC-U15-3` | memory-page-ui/nfr-requirements/security-requirements.md:37 | 畫面**不提供**任何可見範圍的設定或放寬控件 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `frontend/src/pages/MemoryPage.tsx`（非測試檔） | — | Unverified |
| `memory-purge:NFR7.12` | memory-purge/nfr-requirements/security-requirements.md:66 | 連線路徑為**自架 runner ＋ `docker compose exec -T db psql`**；`db` **不得**取得 host port；**不得**新增任何 GitHub secret 或對外 tunnel | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `.github/workflows/memory-retention-purge.yml`（非測試檔） | — | Unverified |
| `memory-purge:NFR7.13` | memory-purge/nfr-requirements/security-requirements.md:67 | 自架 runner 離線導致排程**未執行**必須是**可偵測的**，不得靜默 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `.github/workflows/memory-retention-watchdog.yml`（非測試檔） | — | Unverified |
| `memory-purge:NFR7.15` | memory-purge/nfr-requirements/security-requirements.md:69 | 「清除稽核事件」這個動作本身**不留**稽核紀錄 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/scripts/purge_expired_memory.sql`（非測試檔） | — | Unverified |
| `memory-service:NFR7.32` | memory-service/nfr-requirements/observability-requirements.md:23 | embedding 提供者不可用時的日誌必須含**提供者名稱與可選值**，不得只寫「失敗」 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/memory_facade.py`（非測試檔） | — | Unverified |
| `memory-service:NFR7.34` | memory-service/nfr-requirements/observability-requirements.md:87 | `search` 回空集合時，日誌記錄兩道過濾各自之後的候選筆數 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/memory_service.py`（非測試檔） | — | Unverified |
| `memory-service:NFR3.20` | memory-service/nfr-requirements/performance-requirements.md:22 | `MemoryFacade.search` **本體**的 P95 ≤ **150ms**，**不含**經 `U6 EmbeddingPort` 產生查詢向量的時間 | 未量測（本站未執行負載／計時量測） | 無計時量測工具 | 無後續擁有 stage（計畫無 performance-validation） | Unverified |
| `memory-service:NFR3.21` | memory-service/nfr-requirements/performance-requirements.md:23 | `NFR3.20` 的門檻在被宣稱達成之前，必須有一次**實測**，且該量測須記錄當時的 `memory_records` **列數** | 上游標為 Deferred | traceability：aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-service/nfr-re | aidlc/spaces/default/intents/260920-orchestration-brain/cons | Unverified |
| `memory-service:NFR3.23` | memory-service/nfr-requirements/performance-requirements.md:25 | 列出路徑（`GET /api/memory/records`，三區分頁）的 P95 ≤ **300ms** | 未量測（本站未執行負載／計時量測） | 無計時量測工具 | 無後續擁有 stage（計畫無 performance-validation） | Unverified |
| `memory-service:NFR4.20` | memory-service/nfr-requirements/reliability-requirements.md:20 | 本單元**不持有任何行程內狀態**；重啟後所有記憶與稽核完整還原 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/memory_service.py`（非測試檔） | — | Unverified |
| `memory-service:NFR4.22` | memory-service/nfr-requirements/reliability-requirements.md:22 | embedding 提供者不可用時**大聲失敗並列出可選值**，不得靜默降級為其他提供者 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/memory_facade.py`（非測試檔） | — | Unverified |
| `memory-service:NFR4.23` | memory-service/nfr-requirements/reliability-requirements.md:23 | 本單元**不實作** retry／backoff／circuit breaker | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/memory_service.py`（非測試檔） | — | Unverified |
| `memory-service:NFR7.27` | memory-service/nfr-requirements/scalability-requirements.md:20 | `memory_records` 的成長必須有**可運作的**上界機制，且該機制漏跑時可被偵測 | traceability 狀態 N/A | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-purge/infrastr | — | Unverified |
| `memory-service:NFR7.23` | memory-service/nfr-requirements/security-requirements.md:46 | 稽核事件的讀取僅 `Platform_Admin`／`Platform_Owner` | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/memory_facade.py`（非測試檔） | — | Unverified |
| `memory-service:NFR7.24` | memory-service/nfr-requirements/security-requirements.md:47 | 刪除僅限擁有者本人；**角色不授予跨使用者的刪除權** | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/memory_facade.py`（非測試檔） | — | Unverified |
| `memory-service:NFR7.25` | memory-service/nfr-requirements/security-requirements.md:48 | 刪除與可見範圍放寬各留一筆稽核事件，且稽核寫入與資料變更**在同一交易邊界內** | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/memory_service.py`（非測試檔） | — | Unverified |
| `memory-service:NFR6.20` | memory-service/nfr-requirements/security-requirements.md:50 | 本單元**不新增**任何資料庫連線身分，亦不以 `-U` 或連線字串覆寫既有身分 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/memory_service.py`（非測試檔） | — | Unverified |
| `object-picker-ui:NFR5.160` | object-picker-ui/nfr-requirements/tech-stack-decisions.md:20 | 選單**不新增**任何 WebSocket 訊息型別；`set_work_target` 只經 `setWorkTarget` 送出，選單程式不直接操作 `WebSocket` 物件、不手寫訊框 | traceability 狀態 OK | frontend/eslint.config.js | — | Unverified |
| `object-picker-ui:OPN-22` | object-picker-ui/nfr-requirements/tech-stack-decisions.md:23 | 前後端**零新依賴** | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `frontend/package.json`（非測試檔） | — | Unverified |
| `object-picker-ui:OPN-25` | object-picker-ui/nfr-requirements/tech-stack-decisions.md:26 | 本站各條「必須紅燈的突變」在 `tcms-test-cases` 的 `automation-test-plan.md` 逐條記錄結果 | 上游標為 Deferred | traceability：automation-test-plan.md 屬 tcms-test-cases stage；突變與 lint 逐條結果已記於 code-summary.md §五供轉錄 | automation-test-plan.md 屬 tcms-test-cases stage；突變與 lint 逐條結 | Unverified |
| `object-picker-ui:S-1` | object-picker-ui/nfr-design/security-design.md:127 | lint 只以 AST 比對，擋不住經變數間接取得的儲存或主控台物件（例如 `const g = globalThis; g['local' + 'Storage']`） | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `object-picker-ui:S-2` | object-picker-ui/nfr-design/security-design.md:128 | 被移出的建立者看到「請稍後再試」 | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `progress-channel:U22-V4` | progress-channel/nfr-requirements/security-requirements.md:126 | `publish` 的容量檢查與 buffer 變動之間**無 `await`** | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/progress_channel.py`（非測試檔） | — | Unverified |
| `progress-channel:U22-V6` | progress-channel/nfr-requirements/security-requirements.md:128 | `drain` 不得成為首字延遲的來源 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/progress_channel.py`（非測試檔） | — | Unverified |
| `progress-channel:S-1` | progress-channel/nfr-requirements/security-requirements.md:157 | **buffer 上界的數值，以及「定值前必須先量」的義務。** `[Q1]`=A：`code-generation` 定值前須實跑一次典型產圖、記下 `progress` 事件的實際則數、上界取該數的某個倍數，**且測量值與倍數都要寫進程式註解**。 | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `progress-channel:S-2` | progress-channel/nfr-requirements/security-requirements.md:158 | **`run_design_agent` 的三個呼叫點**。`functional-design` 的 `BR5.1` 只列了 `wa_collab_orchestrator.py:79`，實測有三處：`agent_router.py:125`（**使用者路徑的真實 SSE 入口**）、`wa_collab_orche | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `progress-channel:S-4` | progress-channel/nfr-requirements/security-requirements.md:160 | **`U22-V4` 的 `await` 禁令靠人遵守，無自動化。** `[Q3]`=A 選的是「以需求規定並寫進函式本體註解」而非 `asyncio.Lock`。本站如實記載這個取捨：它防的是一個「只要不寫 `await` 就不存在」的問題，加鎖會讓熱路徑多一次 `await`，但代價是規則沒有機制保證。 | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `progress-channel:S-5` | progress-channel/nfr-requirements/security-requirements.md:161 | **`SEC-1` 的鑄造端半邊**：鍵由 `U13`／`U12` 鑄造，故「必須用密碼學安全隨機來源」這條需求的驗證落在那兩個單元，不在本單元。本站只驗「本單元不含鑄造函式」（`U22-V5`）。 | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `progress-channel:S-6` | progress-channel/nfr-requirements/security-requirements.md:162 | **`NFR4` 判定為不適用的三層理由**（見 §四）。若使用者認為該判定有誤（即認為 buffer 也該外部化到 Redis），它會改寫整個單元的形狀——不只是加一個 Redis 呼叫，而是讓一個 `library` 變成有外部依賴的元件，並直接損害 `NFR3`。 | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `progress-channel:U22-D1` | progress-channel/nfr-requirements/tech-stack-decisions.md:13 | 模組落點 `backend/services/progress_channel.py` | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `progress-channel:U22-D2` | progress-channel/nfr-requirements/tech-stack-decisions.md:14 | logger 名稱 `logging.getLogger("cloud360.progress_channel")` | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `progress-channel:U22-D3` | progress-channel/nfr-requirements/tech-stack-decisions.md:15 | **零新依賴**：`collections.deque` ＋ `dict`，皆標準庫 | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `progress-channel:U22-D4` | progress-channel/nfr-requirements/tech-stack-decisions.md:16 | **不加鎖** | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `progress-channel:U22-D5` | progress-channel/nfr-requirements/tech-stack-decisions.md:17 | buffer 上界**有**、數值在 `code-generation` 定，且定值前須先量 | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `progress-channel:U22-D6` | progress-channel/nfr-requirements/tech-stack-decisions.md:18 | log 分級：容量丟棄 WARN、通道不存在 ERROR | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `progress-channel:U22-D7` | progress-channel/nfr-requirements/tech-stack-decisions.md:19 | 鍵由密碼學安全隨機來源產生（`uuid4` 或 `secrets.token_urlsafe`） | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `progress-channel:U22-D8` | progress-channel/nfr-requirements/tech-stack-decisions.md:20 | 測試框架 Python 內建 `unittest`（**不是 pytest**），併發測試用 `IsolatedAsyncioTestCase` | 未找到可執行檢查 | ID 未出現在任何已執行的測試／檢查檔，亦無 traceability 列 | — | Unverified |
| `project-meta-data:NFR8.3` | project-meta-data/nfr-requirements/security-requirements.md:42 | 該腳本**大聲失敗**：任一 DDL 失敗即以非零碼結束 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/scripts/run_meta_schema_migration.py`（非測試檔） | — | Unverified |
| `project-meta-data:NFR8.4` | project-meta-data/nfr-requirements/security-requirements.md:43 | **不動啟動路徑**（`database.py` 不新增補丁） | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/database.py`（非測試檔） | — | Unverified |
| `project-meta-data:NFR8.5` | project-meta-data/nfr-requirements/security-requirements.md:44 | `DEPLOY.md` 記載執行步驟與驗證指令 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `DEPLOY.md`（非測試檔） | — | Unverified |
| `project-pages-ui:PPN-01` | project-pages-ui/nfr-requirements/performance-requirements.md:42 | 扇出請求的**並行上限**：清單頁（端點 2）一個佇列、詳情頁（端點 5 ＋ 端點 7）一個佇列，任一時刻在途請求數上限 | traceability 狀態 OK | construction/project-pages-ui/nfr-design/performance-design.md | — | Unverified |
| `project-pages-ui:PPN-02` | project-pages-ui/nfr-requirements/performance-requirements.md:43 | 佇列內的**發出順序** | traceability 狀態 OK | construction/project-pages-ui/nfr-design/performance-design.md | — | Unverified |
| `project-pages-ui:PPN-03` | project-pages-ui/nfr-requirements/performance-requirements.md:44 | **不截斷、不設總數硬上界**：清單頁發出 P 次端點 2、詳情頁發出 S 次端點 5 與 S 次端點 7，全部渲染 | traceability 狀態 OK | construction/project-pages-ui/nfr-design/performance-design.md | — | Unverified |
| `project-pages-ui:PPN-04` | project-pages-ui/nfr-requirements/performance-requirements.md:45 | 頁面卸載後，佇列中**尚未發出**的請求不再發出 | traceability 狀態 OK | construction/project-pages-ui/nfr-design/performance-design.md | — | Unverified |
| `project-pages-ui:PPN-05` | project-pages-ui/nfr-requirements/performance-requirements.md:46 | 切籤**不發請求**（`BR85.1`） | traceability 狀態 OK | construction/project-pages-ui/nfr-design/performance-design.md | — | Unverified |
| `project-pages-ui:PPN-12` | project-pages-ui/nfr-requirements/security-requirements.md:40 | 可見性謂詞只有一份（`membership_service` 的私有子句），兩支端點的五種身分結果如 `BR87.5` 所列 | traceability 狀態 OK | construction/project-pages-ui/nfr-design/security-design.md | — | Unverified |
| `project-pages-ui:PPN-15` | project-pages-ui/nfr-requirements/security-requirements.md:42 | 兩個不做擁有者檢查的 `HierarchyFacade` 方法只能被 `MembershipFacade` 呼叫（`BR87.7`） | traceability 狀態 OK | construction/project-pages-ui/nfr-design/security-design.md | — | Unverified |
| `project-pages-ui:PPN-14a` | project-pages-ui/nfr-requirements/security-requirements.md:62 | **`K2 edit` 判定先於可見性守門**：缺 `K2 edit` 者不論可見與否一律 **403**，與修改前相同 | traceability 狀態 OK | construction/project-pages-ui/nfr-design/security-design.md | — | Unverified |
| `project-pages-ui:PPN-14b` | project-pages-ui/nfr-requirements/security-requirements.md:63 | 守門使用的謂詞**就是** `PPN-12` 那一份（經 `membership_service.is_project_visible`），不在 hierarchy 側另寫；`HierarchyFacade` **仍不 import 任何 membership 符號**（`BR87.3`）；`K2` 判定仍只在 `Hi | traceability 狀態 OK | construction/project-pages-ui/nfr-design/security-design.md | — | Unverified |
| `project-pages-ui:PPN-16` | project-pages-ui/nfr-requirements/security-requirements.md:82 | 前端的 `K2`／`K4 view`／`K4 edit` 可見性**只是呈現**；伺服器照樣判定。前端**不得**以 `owner_user_id` 或任何回應欄位自行推斷「可見」 | traceability 狀態 OK | construction/project-pages-ui/nfr-design/security-design.md | — | Unverified |
| `project-pages-ui:PPN-17` | project-pages-ui/nfr-requirements/security-requirements.md:83 | 需求欄位草稿、`fieldsBySystem`、專案與系統清單**不寫瀏覽器儲存** | traceability 狀態 OK | construction/project-pages-ui/nfr-design/security-design.md | — | Unverified |
| `project-pages-ui:NFR8.100` | project-pages-ui/nfr-requirements/tech-stack-decisions.md:20 | 本單元**零新環境變數、零 compose 變更**；若 code-generation 發現需要任何環境變數，`NFR8` 與 `project.md` 的三處同步（`render-env.sh`、`deploy/.env.example`、`backend/.env.example`）完整適用 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `frontend/package.json`（非測試檔） | — | Unverified |
| `project-pages-ui:PPN-21` | project-pages-ui/nfr-requirements/tech-stack-decisions.md:21 | 前端並行佇列（`PPN-01`）**自寫**，不引入 `p-limit` 等套件 | traceability 狀態 OK | construction/project-pages-ui/nfr-design/logical-components.md | — | Unverified |
| `project-pages-ui:PPN-22` | project-pages-ui/nfr-requirements/tech-stack-decisions.md:22 | 伺服器 SQL 語句計數（`PPN-06`）用 SQLAlchemy 內建的 `event.listen(engine, "before_cursor_execute", …)` | traceability 狀態 OK | construction/project-pages-ui/nfr-design/performance-design.md | — | Unverified |
| `project-pages-ui:PPN-23` | project-pages-ui/nfr-requirements/tech-stack-decisions.md:23 | 新增測試全部放在 `backend/tests/` 與既有 Playwright 目錄，由既有 CI 指令撿到 | traceability 狀態 OK | construction/project-pages-ui/nfr-design/logical-components.md | — | Unverified |
| `project-pages-ui:PPN-24` | project-pages-ui/nfr-requirements/tech-stack-decisions.md:24 | `openapi.json` 與 `api.d.ts` 隨 docstring 改寫一併重產（`BR87.4`） | traceability 狀態 OK | construction/project-pages-ui/nfr-design/logical-components.md | — | Unverified |
| `project-pages-ui:PPN-07` | project-pages-ui/nfr-design/performance-design.md:164 | §二之一（查詢形狀使索引可被用到）；DDL／遷移落點見 `logical-components.md` §三 | traceability 狀態 OK | construction/project-pages-ui/nfr-design/logical-components.md | — | Unverified |
| `rbac-story-ids:SEC-6` | rbac-story-ids/nfr-requirements/security-requirements.md:24 | 本單元**對授權判定無可自驗的機械檢查**，只驗授權**資料**的結構前提。`BR7.1`–`BR7.3` 的 allow/deny 雙向覆蓋為對 `U19` 的具名交付條件（第四節）。 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `aidlc/spaces/default/intents/260920-orchestration-brain/construction/rbac-story-ids/code-generation/code-summary.md`（非測試檔） | — | Unverified |
| `rbac-story-ids:U3-A1` | rbac-story-ids/nfr-requirements/security-requirements.md:98 | 邀請一般成員：被邀請者持有 `K3.view` → 成功；不持有 → 拒絕且不寫入任何列。 | 上游標為 Deferred | traceability：U19 membership-service 的交付條件（邀請一般成員的 allow/deny 雙向）。本單元已交付其資料前提並在 aidlc/spaces/default/int | U19 membership-service 的交付條件（邀請一般成員的 allow/deny 雙向）。本單元已交付其資 | Unverified |
| `rbac-story-ids:U3-A2` | rbac-story-ids/nfr-requirements/security-requirements.md:99 | 邀請／改為專案管理者：目標持有 `K3.edit` → 成功；只持有 `K3.view` → 拒絕。 | 上游標為 Deferred | traceability：U19 的交付條件（邀請／改為專案管理者的 allow/deny 雙向）。同上 | U19 的交付條件（邀請／改為專案管理者的 allow/deny 雙向）。同上 | Unverified |
| `requirement-field-service:NFR20.30` | requirement-field-service/nfr-requirements/observability-requirements.md:33 | 新模組一律 `logging.getLogger("cloud360.requirement_fields")`，不用 `__name__` | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/requirement_field_facade.py`（非測試檔） | — | Unverified |
| `requirement-field-service:NFR20.5` | requirement-field-service/nfr-requirements/performance-requirements.md:31 | 寫入與清空的回應**不重算**整個系統的計數（只回單一 `FieldView`）；畫面所需的新計數由 `U23` 重讀 `GET` 取得（`OPEN-RF20-3`） | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/requirement_field_router.py`（非測試檔） | — | Unverified |
| `requirement-field-service:NFR20.6` | requirement-field-service/nfr-requirements/performance-requirements.md:37 | 本輪**不加**任何跨請求快取（欄位值、計數、授權結論皆然） | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/requirement_field_facade.py`（非測試檔） | — | Unverified |
| `requirement-field-service:NFR20.23` | requirement-field-service/nfr-requirements/reliability-requirements.md:26 | `updated_on_behalf_of` 的收斂敘述**只在欄位仍為舊型別（integer）時**才轉型並清值；**只在外鍵存在時**才移除（名稱以 `pg_constraint` 查，不寫死自動產生的名稱） | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `.github/workflows/ci.yml`（非測試檔） | — | Unverified |
| `requirement-field-service:NFR20.24` | requirement-field-service/nfr-requirements/reliability-requirements.md:27 | 收斂可由舊定義資料庫驗證，不只由全新資料庫驗證 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `.github/workflows/ci.yml`（非測試檔） | — | Unverified |
| `requirement-field-service:NFR20.25` | requirement-field-service/nfr-requirements/reliability-requirements.md:28 | 收斂失敗必須**大聲失敗**，不得被吞掉 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/scripts/run_meta_schema_migration.py`（非測試檔） | — | Unverified |
| `requirement-field-service:NFR20.16` | requirement-field-service/nfr-requirements/scalability-requirements.md:13 | 列數**只增不減**（`ADR-015` 已接受）：本單元沒有任何刪除列的操作；系統刪除時由 `U18` 的 `ON DELETE CASCADE` 一併移除 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `.github/workflows/ci.yml`（非測試檔） | — | Unverified |
| `requirement-field-service:NFR20.13` | requirement-field-service/nfr-requirements/security-requirements.md:51 | 所有資料存取經 ORM 參數化，不組字串 SQL | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/requirement_field_service.py`（非測試檔） | — | Unverified |
| `requirement-field-service:NFR8.120` | requirement-field-service/nfr-requirements/security-requirements.md:58 | 本單元**零新環境變數**；資料表變更（`BR47.1`）觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步，兩者在同一個 commit 內完成 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `DEPLOY.md`（非測試檔） | — | Unverified |
| `session-store:NFR4.60` | session-store/nfr-requirements/observability-requirements.md:35 | Redis 記憶體使用率須有一個**應用端可讀**的訊號 | traceability 狀態 GAP | 無承接站——OPEN-N10-4 記明無告警管道消費、無自然承接站；處置為閘門上重新提交使用者 | — | Unverified |
| `session-store:NFR4.64` | session-store/nfr-requirements/observability-requirements.md:39 | 重啟還原（`NFR4.53`–`NFR4.57` 五項）須有一次**可重複執行**的驗證程序 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `.github/workflows/deploy.yml`（非測試檔） | — | Unverified |
| `session-store:NFR3.40` | session-store/nfr-requirements/performance-requirements.md:26 | `SessionStore.load` 的伺服器端耗時 **P95 ≤ 20ms**（自方法進入到回傳，不含呼叫端處理） | 未量測（本站未執行負載／計時量測） | 無計時量測工具 | 無後續擁有 stage（計畫無 performance-validation） | Unverified |
| `session-store:NFR3.41` | session-store/nfr-requirements/performance-requirements.md:27 | `SessionStore.append_message` 的伺服器端耗時 **P95 ≤ 20ms**，含 `BR3.4` 的上限修剪 | 未量測（本站未執行負載／計時量測） | 無計時量測工具 | 無後續擁有 stage（計畫無 performance-validation） | Unverified |
| `session-store:NFR3.42` | session-store/nfr-requirements/performance-requirements.md:28 | `SessionStore.set_work_target` 的伺服器端耗時 **P95 ≤ 150ms**，**含** `K-07` 的 `resolve_work_target` | 未量測（本站未執行負載／計時量測） | 無計時量測工具 | 無後續擁有 stage（計畫無 performance-validation） | Unverified |
| `session-store:NFR3.43` | session-store/nfr-requirements/performance-requirements.md:29 | 上述三條的量測**必須排除**使用者網路往返 | traceability 狀態 N/A | 延遲預算的量測方式本身：本 repo 無 APM，承接 build-and-test | — | Unverified |
| `session-store:NFR2.40` | session-store/nfr-requirements/performance-requirements.md:30 | 狀態變更到該 session key 全部存活連線**送出**訊息，伺服器端耗時 **P95 ≤ 200ms** | 未量測（本站未執行負載／計時量測） | 無計時量測工具 | 無後續擁有 stage（計畫無 performance-validation） | Unverified |
| `session-store:NFR4.50` | session-store/nfr-requirements/reliability-requirements.md:30 | Redis 的 `maxmemory-policy` 須為 **`noeviction`** | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `deploy/docker-compose.deploy.yml`（非測試檔） | — | Unverified |
| `session-store:NFR4.51` | session-store/nfr-requirements/reliability-requirements.md:31 | 記憶體耗盡時，**寫入**須大聲失敗並循 `SessionBackendUnavailable` 路徑向上傳遞；**讀取（`load`）須仍然可用** | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/redis_gateway.py`（非測試檔） | — | Unverified |
| `session-store:NFR4.52` | session-store/nfr-requirements/reliability-requirements.md:32 | `appendonly` 須維持 `yes` | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `deploy/docker-compose.deploy.yml`（非測試檔） | — | Unverified |
| `session-store:NFR4.53` | session-store/nfr-requirements/reliability-requirements.md:41 | 每一個存在的段（`shared` 必在，另兩個視是否建立過） | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `.github/workflows/deploy.yml`（非測試檔） | — | Unverified |
| `session-store:NFR4.54` | session-store/nfr-requirements/reliability-requirements.md:42 | 每一段的**完整**訊息歷程與其順序 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `.github/workflows/deploy.yml`（非測試檔） | — | Unverified |
| `session-store:NFR4.55` | session-store/nfr-requirements/reliability-requirements.md:43 | 每一段**各自**的三層作業對象（含為 `null` 的層） | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `.github/workflows/deploy.yml`（非測試檔） | — | Unverified |
| `session-store:NFR4.41` | session-store/nfr-requirements/scalability-requirements.md:40 | 每個 session 的記憶體佔用須有**可計算的硬上界**，不得有任何無上界成長的欄位 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/session_store.py`（非測試檔） | — | Unverified |
| `session-store:NFR2.41` | session-store/nfr-requirements/scalability-requirements.md:41 | 同一 session key 的並存連線數**不設上限**，且連線數成長**不改變狀態的記憶體佔用** | traceability 狀態 N/A | 無狀態設計的性質：它是 BR1.2（狀態一律進 Redis）的後果而非獨立條款，承載在 BR1.2 那一列 | — | Unverified |
| `session-store:NFR2.42` | session-store/nfr-requirements/scalability-requirements.md:42 | 狀態扇出的成本與該 key 的存活連線數**線性**相關，不得為二次 | traceability 狀態 N/A | 扇出成本線性：屬 U13 的扇出演算法，本單元不扇出 | — | Unverified |
| `session-store:NFR4.44` | session-store/nfr-requirements/security-requirements.md:36 | 本單元**只能**以 `REDIS_USER` 指定的 ACL 使用者連線，不得以 `default` 連線 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/redis_gateway.py`（非測試檔） | — | Unverified |
| `session-store:NFR4.45` | session-store/nfr-requirements/security-requirements.md:37 | **任何** log、例外訊息或錯誤回應都不得包含 `SessionMessage.text`、整個 `ConversationSegment` 或整個 `BrainSession` 物件 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/redis_gateway.py`（非測試檔） | — | Unverified |
| `session-store:NFR4.48` | session-store/nfr-requirements/security-requirements.md:40 | 作業對象的驗證是**寫入時點**驗證；本單元**不做讀取時重驗**，此為明示的設計選擇而非遺漏 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `backend/services/session_store.py`（非測試檔） | — | Unverified |
| `session-store:NFR8.42` | session-store/nfr-requirements/tech-stack-decisions.md:35 | `[N3]`=A 的 `maxmemory-policy` 由 `allkeys-lru` 改為 `noeviction`，須走與其他部署設定相同的同步紀律 | 僅實作落點存在，無可執行檢查直接斷言 | traceability OK → `deploy/docker-compose.deploy.yml`（非測試檔） | — | Unverified |
| `session-store:NFR5.40` | session-store/nfr-requirements/tech-stack-decisions.md:36 | `D-S10-1` 對 `K-02` 四個 payload 的欄位新增，須通過 `NFR5` 的前後端契約閘門 | traceability 狀態 N/A | 該契約閘門由 U2 brain-ws-contract 擁有，本單元不擁有它 | — | Unverified |

## 失敗判定與後續（Step 9 failure ladder）

**依 stage 檔的 failure predicate，本次 Build and Test 為「失敗」**：(a) e2e 有 20 個失敗指令結果；(b) 166 個適用目標為 `Unverified`；(c) Step 10 跨單元閘門 FAIL（91 個未覆蓋，見 `cross-unit-traceability.md`）。沒有任何目標是 `Not Met`，沒有任何既有測試失敗。

逐 rung 的現況（本 agent 只做到 rung 2；rung 3／4 是否觸發由 conductor 與使用者決定）：

- **Rung 1（站內修正，上限 2 次）**：e2e 20 個失敗的根因是「本站不得起真實 stack」，不是測試設定錯誤，站內無可修之處；`Unverified` 的主因是「無可執行檢查」或「無量測工具」，不是本站的設定問題。本站兩次執行器自身錯誤（失敗明細 3、4）已站內修正並重跑。
- **Rung 2（分類與影響估計）**：見下方「待修」，每項附工作量、風險與建議落點。
- **Rung 3 條件**：`aidlc-state.md` 的 `Construction Autonomy Mode` 為 `autonomous`；本檔 `## Loop-Back Log` 目前 0 筆（< 3）；有影響已估計的修法（待修 1–9）。**是否以 loop-back 重開 code-generation，或在關卡上 halt-and-ask，交 conductor 決定**——本 agent 依 brief 不執行 report／路由。

## 待修（需要改程式或紀錄，本站未改）

工作量級距：XS（< 30 分）、S（半天內）、M（1–2 天）。風險指修正本身可能打破他處的機率。

| # | 項目 | 來源 | 建議落點 | 工作量 | 風險 | 合併前是否必要（本站建議） |
|---|---|---|---|---|---|---|
| 1 | **記憶專用資料庫角色只在 HTTP 路徑生效**：閘道 `_prefetch`（`brain_gateway.py:1755`）、`_write_episodic`（`:1875`）、本站新增的 `_write_semantic`（`:1834`）與 `work_orchestrator.py:1081` 的程序記憶寫入皆用主連線 | 合併前必修第 52 列（第 48 列 Major 的未完成半邊） | brain-gateway、work-orchestrator 的 code-generation：注入記憶專用 session factory（`database.get_memory_session`）；`work_orchestrator.py:1104` 同一 session 另讀 `users`，須拆兩個 session | M | 中（`cloud360_memory` 讀不到 `public`，任何混用的查詢會在執行期失敗，只在真實 PG 上出現） | 建議是（ADR-0006 IAM 第二道邊界；第 48 列原判 Major） |
| 2 | Sidebar 三個 `<nav>` 無可存取名稱：`Sidebar.tsx:162`、`:218`、`:280` | memory-page-ui 帶入 | memory-page-ui／a11y-gate：補 `aria-label`，並在 `sidebar-landmarks.spec.ts` 斷言 | XS | 低 | 否（axe 本站全綠，未觸發規則） |
| 3 | intent-router Minor (a)：`test_a3_langgraph_migration.py:35`、`:43` 斷言 `openrouter_chat_model` 在原始碼中——`review_agent.py` 只剩註解（`:181`）命中，斷言已恆真 | intent-router 帶入 | 改為斷言 `langgraph_runtime` 的 builder 呼叫，或刪除該字串斷言 | XS | 低 | 否 |
| 4 | intent-router Minor (b)：`review_agent` 串流與 `wa_lens_engine` JSON 擷取未對 `ClaudeCodeChatModel` 測 | intent-router 帶入 | 補兩支以假 CLI 驅動的測試 | S | 低 | 否（僅本機 provider） |
| 5 | intent-router Minor (c)：`claude_code_chat.py:413`、`:453` 以共用 `tempfile.gettempdir()` 為 cwd | 同上 | 每次呼叫 `TemporaryDirectory()` | XS | 低 | 否 |
| 6 | intent-router Minor (d)：`os.killpg`（`:320`）僅 POSIX | 同上 | 文件註明不支援 Windows，或加 `os.name` 分支 | XS | 低 | 否 |
| 7 | intent-router Minor (e)：非零結束一律說「可能尚未登入」（`:330`、`:342`） | 同上 | 依 stderr／exit code 分型訊息 | XS | 低 | 否 |
| 8 | intent-router Minor (f)：`review_agent.py:49` 錯誤句仍教設定 `OPENROUTER_API_KEY` | 同上 | 改走 `llm_provider.auth_error_message()` | XS | 低 | 否 |
| 9 | 啟動 WARNING `Cost schema index rename … InFailedSqlTransaction`（F7 第 3 點）：`database.py` 的 `RENAME CONSTRAINT` 失敗被 `except: pass` 吞掉，但 PostgreSQL 交易已中止，下一句 `ALTER INDEX` 因而失敗 | findings F7；**既存**，由 `e36d507`（2026-09-20，cost intent）引入，非本 intent 改動 | 各 `try` 改用 `conn.begin_nested()`（SAVEPOINT） | XS | 低（全新庫無可改名物件） | 否（本 intent 範圍外，建議另開 issue） |
| 10 | F8 程序記憶重複：`_write_procedure_memory` 每次完成即寫，無去重 | findings F8 | 需求先定「同內容是否合併／更新時間」再改 | S | 低 | 否 |
| 11 | F5 邀請成員須輸入數字使用者 ID | findings F5 | 需新增以帳號查詢的端點——**會引入使用者列舉面**，須先在 requirements 定授權（誰能查、回傳哪些欄位） | M | 中（安全面） | 否 |
| 12 | `brainTranscript.ts:93` 註解與 F4 後行為相反 | local-verify-fixes 任務二 | 改註解 | XS | 無 | 否 |
| 13 | `AC6.1.1` 指派落空（intent-router 標 Deferred → work-orchestrator，後者無 OK 條目） | cross-unit 閘門 | 先查 work-orchestrator 是否已實作「作用在上一輪產出的那張圖」；有則補 traceability，無則屬功能缺口 | S（查證）～M（若需實作） | 中 | 視查證結果 |
| 14 | 回補 requirements／stories（S-1、S-2、S-3）並把測試的 `@story` 改指新 AC；之後重跑 cross-unit 閘門 | 本站範圍新增 | 上游回補（文件） | S | 無 | 依使用者裁決（TCMS 同步前需要） |

### 不需改程式、只需判定或紀錄的帶入項

| 項目 | 現況判定 | 證據／承接 |
|---|---|---|
| intent-router Minor (g)：requirements 補 NFR | **仍開放** | 即上表 S-3 回補項 |
| F9 隔日作業對象回到「尚未選定」 | **符合現行設計** | `redis_gateway.py:105` `SESSION_TTL_SECONDS = 86400`；session 24 小時過期即清空作業對象。若要跨日保留屬需求變更 |
| findings F7 第 3 點的 WARNING | **仍開放（範圍外）** | 待修 9 |
| TCMS（`tcms-test-cases` stage） | **尚未做**；使用者已接受「整包合，TCMS 後補」的例外 | `project.md` ## Mandated 將其列為 blocking；本例外由使用者裁決，記於此。**後果**：e2e 新案（F1 3 案、F4 1 案、語意記憶 1 案）與既有案在 TCMS 上無對應、手動測案（真實滑鼠鍵盤互動等）未寫 |
| Chrome 擴充滑鼠事件 | **限制如實記載** | 本機 UI 驗證的滑鼠點擊送不進頁面，改以頁面腳本（原生 setter＋`click()`）操作；**真實滑鼠／鍵盤互動未驗**，交 `ui-regression` 的 Playwright（真實輸入事件）與 TCMS 手動測案 |

### 合併前必修清單的帶入列

| 列 | 清單上的狀態 | 本站判定 | 證據 |
|---|---|---|---|
| 第 33 列（memory-service (a)–(g)） | 「待修」（2026-10-30） | **狀態過時，實質已解決** | (a) `user_router.py:475` 改經 `MemoryFacade(db).count_references_to_user`；(b) `memory_errors.py:51` 已更名 `MemoryServiceError`；(c)(d)(f) 由第 52 列修畢（memory-service traceability `MB-33` OK）；(e) `memory_router.py:182` `MEMORY_CONTENT_MAX_CHARS = 4000` 並以 `max_length` 套用；(g) `ci.yml` 步驟名稱已同步（本站亦見該步驟列出五支檔）。**待辦**：清單本列改為已修正並指向第 52 列 |
| `MB-48`（第 48 列 Major） | 第 48 列「待修」；memory-service traceability `MB-48` 為 `OK` | **兩邊都不精確**：HTTP 路徑已解決（`memory_router.get_memory_db`），WS／編排路徑未解決（待修 1）。traceability 的 `OK` 是過度宣稱（第 52 列已自記此 Minor） | 本站讀碼：`brain_gateway.py:1755`、`:1834`、`:1875`、`work_orchestrator.py:1081` |
| 第 43 列（hierarchy-data (a)–(f)） | 「待修」，(a) `ci.yml` 承接者未定 | **仍開放，owner 未定** | (a) 本站確認 `ci.yml` 對 hierarchy 遷移仍無「連跑兩次」等真實 PG 步驟（本站以後端全套的 SQLite 版本驗過遷移，未在 pg18 跑 `run_hierarchy_migration.py`）。建議承接：brain-infra 下一次共用檔修正（清單原建議） |
| 第 46 列（embedding-port (a)–(c)） | 「待修」，(b) `LOCAL-DEV.md` 承接者未定 | **仍開放，owner 未定** | (a) docstring、(b) `LOCAL-DEV.md` 前置條件數目矛盾、(c) CI 無 fastembed 實載——本站未改。建議 (b) 由下一次碰 `LOCAL-DEV.md` 的單元承接 |
| 第 47 列（hierarchy-service (a)–(d)） | 「待修」，(c) `openapi.json` 承接者未定 | **仍開放，owner 未定** | (c) A3 新增的 403 仍未宣告於 OpenAPI；本站的 F1 改了 `openapi.json` 但未處理此項 |
| 第 48 列 (a)(b)(c) | 「待修」，共用檔承接者未定 | **仍開放，owner 未定** | (c) `ci.yml:376` 步驟名稱仍是 `Verify memory schema assertions (S1-S13)`，而腳本實為 S1、S3–S15（本站實跑輸出含 S15）；(a) R3 在 pg18 上無鑑別力、(b) R2 未以該角色做向量查詢——本站實跑 R0–R3 全綠，但這兩項是「綠燈不代表有驗到」的問題，綠燈本身不關閉它們。建議與第 43 列 (a) 同批由 brain-infra 共用檔修正承接 |

### 各單元計畫未勾格

| 單元：項目 | 本站可否以實跑關閉 | 證據或承接者 |
|---|---|---|
| session-store 12.4（全套回歸、`dump_openapi --check`、三檔 diff 為空） | **測試部分可關閉**；diff 為空部分不可 | 全套 1467 OK、`dump_openapi --check` OK；`openapi.json`／`api.d.ts` 已因 F1 改動、`database.py` 在分支上有他單元改動，「diff 為空」在分支層無法判定 → session-store 以單元 commit 範圍自判 |
| requirement-field-service Step 11 | **可關閉** | 兩支 validator、`check:types` 皆 exit 0 |
| requirement-field-service Step 17 | **測試部分可關閉** | 全套、`tests_pg`（含 G1–G4）、`dump_openapi`、兩支 validator 全綠；traceability／code-summary 紀錄部分 → 單元自理 |
| member-pages-ui Step 9／10（`MemberDetailPage`、路由與 Sidebar 入口） | **可關閉（實作已存在且受 e2e 斷言）** | `member-pages.spec.ts` 20 passed、`a11y.spec.ts` 掃描點 08–12、15 通過 |
| member-pages-ui Step 20／24 | **測試部分可關閉** | lint 0 errors、build（含 `tsc -b`）、`member-pages`＋`a11y` 全綠；code-summary 追加段 → 單元自理 |
| memory-purge 1.3／12.5（`database.py` diff 為空、validators、全套） | **validators 與全套可關閉；diff 為空不可** | 分支相對 `ut` 的 `database.py` 有 +121 行（他單元），無法在分支層證明本單元未動 → memory-purge 以單元 commit 範圍自判（清單第 51 列已記此 Minor） |
| memory-service 1.1／10.1／10.2（`database.py`、`requirements.txt` diff 為空） | **不可** | 同上；`requirements.txt` 分支 diff +56 行來自他單元釘選 → memory-service 自判 |
| memory-service 15.2（全套＋tests_pg＋validators） | **可關閉** | 全部全綠（`tests_pg` 含 V1／D1–D2） |
| brain-gateway Step 9（DEMO 前端移除、lint、`tsc -b`） | **可關閉** | lint 0 errors、build 通過；落地頁 e2e 在 `regression.spec.ts`（真實 stack）→ `ui-regression` |
| brain-gateway Step 15（`OPENROUTER_API_KEY` 在 secrets 不在 variables） | **本站不可**（brief 禁用 `gh`） | 清單第 19 列記載 2026-10-24 與 2026-11-08 已查證；計畫格未同步勾選 → brain-gateway 更新紀錄 |
| brain-gateway Step 21（unit-test-instructions 補前端寫檔注意） | **不可**（文件） | brain-gateway 自理 |
| a11y-gate Step 11（`M1`–`M12` 突變未在最新 spec 重跑） | **部分**：最新 `a11y.spec.ts` 28 案全綠；**突變未重跑** | 承接：a11y-gate code-generation，或 tcms-test-cases 的突變驗證 |
| entry-page-ui 第 291 行（對 test stack 跑 WS 探測＋突變 D1） | **不可**（需真實 stack） | CI／本機 compose stack；承接 entry-page-ui |
| entry-page-ui Step 23（一次 CI 實跑） | **不可** | PR 上的 CI |
| object-picker-ui Step 10 | **部分**：`entry-page.spec.ts` 62 案全綠；`entry-page-live` 需真實 stack | `ui-regression` |
| object-picker-ui Step 12 | **部分**：build、兩支 validator 通過；`N-05` 基準比對與「`backend/`、`deploy/`、`.github/` 零變更」不可（分支層有他單元改動） | 維持清單第 64 列的處置（不勾、不改寫已核可計畫） |

## 第三輪修正後的 CI 實跑證據（2026-11-14，conductor 追加）

本節為追加，不改上方已寫入的內容；上方矩陣的 verdict 是第三輪修正**之前**的判定。

- **推送**：PR #650 head `48f6349`，包含：
  - `2fa972e`：修正。
  - `a40f75e`：紀錄。
  - `e2ca1ac`：合併 `ut`（PR #717 U22），並解決 `design_agent.py` 衝突。
  - `48f6349`：selftest 修正。
- **衝突導致 PR 檢查未觸發**：PR 先前與 `ut` 衝突（`mergeable=CONFLICTING`），GitHub 因此**沒有觸發任何 pull_request workflow**，只有 push 事件的 CI 跑了。合併 `ut` 後才觸發。
- **全部 PR 檢查 `success`**：
  - CI（run 43556488824）
  - AI-DLC Sync Selftest（run 43556488890）
  - Contract Guard、Code Drift Alert、Local Dev Drift、Lint Fixer、PR Reviewer、AI-DLC Sync Forward
- **UI Regression Reporter（run 43556488900）**：在真實短生命週期 stack 上 `215 passed`，`unexpected=0 flaky=0`。本站先前因本機無法起 stack 而失敗的 20 個 e2e（`regression` 13、`entry-page-live` 5、`estimate-workspace` 2）因此有了通過證據。
- **矩陣中 owning stage 為 CI `ui-regression` 的 6 列**：`TC-VOLUME`、`a11y-gate:A11Y-S1`、`A11Y-S3`、`A11Y-S4`、`entry-page-ui:EPN-24`、`project-pages-ui:PPN-23`。這 6 列現有上列證據，但**是否每列都被該次執行完整覆蓋，本節未逐列複核**，故不在矩陣內改寫其 verdict。
- **仍為 `Unverified`**，本站與 CI 皆無法產生證據：
  - 14 個延遲數字目標（「無後續擁有 stage，計畫無 performance-validation」）。
  - 歸屬其他單元交付條件，或歸屬 `ci-pipeline`（CONDITIONAL）的少數列。

  依 stage 檔，只要這些列存在，本站在形式上仍判定為失敗；處置交核可關卡由使用者決定。
- **selftest 首次紅燈的兩個根因與修正**：
  - R-1.2：`scripts/validate_env_contract.py` 寫死本機限定 provider 名稱，被掃描器判為代理式字樣。改為自 `backend/services/llm_provider.py` 讀取。
  - COVERAGE-2：`ci.yml` 新增呼叫的 `deploy/initdb/02-memory-role-password.sh` 不在 selftest 觸發 allowlist，已補上。

  修正後本機三支檢查器結果：`93 tests, 392 checks, 0 failures`。
- **記憶專用角色本機實測**：
  - 以 `cloud360_memory` 讀 `public.users` 回 `permission denied`。
  - 設定後，後端啟動時沒有記憶連線 WARNING，也沒有 cost index rename WARNING。
  - 語意記憶經確認後寫入成功，情節記憶寫入也成功。
  - 資料庫上可見 `cloud360_memory` 的連線。
- **部署前置（未完成，需使用者處理）**：
  - GitHub secret `MEMORY_DB_PASSWORD` **尚未建立**。查證方式是以 `gh api` 只列名稱；`JWT_SECRET`、`OPENROUTER_API_KEY`、`POSTGRES_PASSWORD`、`REDIS_PASSWORD` 都在 secrets，variables 沒有同名項。
  - staging 須在部署前執行 `run_meta_schema_migration.py`（DEPLOY.md §2.2.8）。
  - compose 映像已改為 `pgvector/pgvector:pg18`：PG 16→18 需要手動 dump／restore 和維護窗口，自動回滾不會還原資料。
