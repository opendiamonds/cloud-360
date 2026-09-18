# Reverse Engineering Timestamp — Cloud-360

> 本檔是 `aidlc/spaces/default/codekb/cloud-360/` 這份程式碼知識庫的**新鮮度標記**。
> 使用本 codekb 的任何 stage 都應先讀本檔，確認基準是否仍然有效。

## 掃描基準

| 項目 | 值 |
|---|---|
| **日期** | 2026-08-17 |
| **Commit** | `c3de2c8` |
| **Commit 訊息** | `Merge pull request #502 from opendiamonds/danniel/docs/github-sync-adr` |
| **Branch** | `danniel/fix/production-path-check-noop`（基於 `ut`） |
| **Repository** | `cloud-360` |
| **AIDLC stage** | `reverse-engineering`（inception 2.1，pipeline mode） |
| **執行方式** | 兩環 pipeline：第一環 developer agent 掃描，第二環 architect agent 綜整 |

### 本次為完整重掃（非新鮮度驗證）

前一版 codekb 的基準為 commit `8c90f40`（2026-08-08，branch `ut`），並已於
2026-08-11 自行標記為**過期**。本次是該標記後的首次完整重掃，**整份取代**前一版內容。

觸發重掃的既有條件命中情形（對照前一版自訂的「觸發完整重跑」清單）：

| 觸發條件 | 命中情形 |
|---|---|
| `backend/services/` 新增或刪除模組 | **命中** —— 由 18 支增為 **22 支**（新增 `llm_provider.py`、`activity.py`、`prompt_guard.py`、`wa_score_service.py` 等） |
| 新增或刪除 API 端點 | **命中** —— 前一版記載 46 個「端點」，本次以 `openapi.json` 精確計為 **36 paths / 45 operations**（另加 1 個不在規格內的 WebSocket） |
| 資料表新增或刪除 | 未命中（仍為 7 實體 + 1 association table），但 `users` 表**新增 `last_activity_at` 欄位** |
| 架構風格改變 | 未命中（仍為 Modular Monolith + SPA） |
| 權限矩陣維度改變 | 未命中（仍為 11 角色 × 28 story = 308 列，已以 AST 實測確認） |

### 工作目錄狀態註記

掃描當下工作樹除 `aidlc/.../audit/` shard 外乾淨。**本 codekb 描述的是 commit `c3de2c8`
於 branch `danniel/fix/production-path-check-noop` 的狀態。**

## 跨分支狀態（本次基準的重要限制）

本 codekb 的基準分支**不含**下列已完成但尚未合併的工作。下游 stage 若在其他分支上作業，
必須自行確認差異：

| 項目 | 狀態 | 所在分支 |
|---|---|---|
| `scripts/aidlc_sync_push.py`／`aidlc_sync_pull.py`／`aidlc_sync_buglist.py`（ADR-0012 階段 1／2／2.5） | **實作已完成，PR #508 待合併**（`state: OPEN`，base `ut`，`mergedAt: null`） | `danniel/feat/github-sync-phase1` |

**這不是「規格與實作脫節」**。三支腳本的存在已用 `git log --all` 與
`git branch --contains` 逐一確認（`aidlc_sync_push.py` 最新 commit `6438ffb`、
`aidlc_sync_pull.py` `d2e40d5`、`aidlc_sync_buglist.py` `6295c69`，三者皆僅存在於
`danniel/feat/github-sync-phase1` 與其 remote）。本基準分支看不到它們，純粹是分支拓撲的
結果 —— `git merge-base --is-ancestor` 確認 `origin/ut` 尚未包含。

`aidlc/.../operation/github-sync-design.md` 與
`aidlc/.../inception/decisions/0012-*.md` 對這三支腳本的引用因此是**正確的前瞻引用**，
不是需要修補的文件漂移。

## 分析範圍

### 已掃描

| 範圍 | 內容 |
|---|---|
| `backend/` | 全部：`main.py`、`models.py`、`database.py`、`services/`(22 支)、`lenses/`(3)、`prompts/`(6)、`tests/`(21 測試檔 + `helpers.py` + `__init__.py`)、`scripts/dump_openapi.py`、`Dockerfile`、`requirements.txt` |
| `frontend/` | 全部：`src/`（8 頁面、12 元件、`types/api.d.ts`、context、config、hooks、utils）、`tests/e2e/`、`scripts/check-api-types.mjs`、`Dockerfile`、`nginx.conf`、全部設定檔 |
| `scripts/` | 4 支：`validate_repo_contract.py`(405)、`tcms_sync.py`(515)、`tcms_validate.py`(360)、`validate_env_contract.py`(315) |
| `deploy/` | `docker-compose.deploy.yml`、`docker-compose.test.yml`、`render-env.sh`、`cloudflared/config.yml` |
| `.github/` | `workflows/ci.yml`、`workflows/deploy.yml`、11 組 gh-aw workflow、`agentics-maintenance.yml`、`copilot-setup-steps.yml` |
| repo 根目錄 | `openapi.json`、`schema.sql`、`schema_rbac.sql`、`DEPLOY.md`、`LOCAL-DEV.md`、`TESTING.md`、`docker-compose.yml`、`CLAUDE.md`、`README.md`、`AGENTS.md` |
| 規則層 | `aidlc/spaces/default/memory/` 的 `org.md`、`team.md`、`project.md`、`phases/inception.md` |

### 量化結果

所有數字皆為本次實測。**測試數字為靜態計數，非執行結果** —— 見下方「實測方法與限制」。

| 指標 | 數值 | 取得方式 |
|---|---|---|
| Backend 產品碼 | 8,775 LOC（git-tracked，排除 `tests/`） | `git ls-files` + `wc -l` |
| Backend 測試碼 | 3,199 LOC（21 測試檔 + `helpers.py` + `__init__.py`） | 同上 |
| Frontend `src/` | 10,539 LOC TS/TSX（40 檔） | 同上 |
| Backend `services/` 模組 | **22** | `git ls-files` |
| API paths / operations | **36 / 45** | `python3` 解析 `openapi.json` |
| OpenAPI schemas | **29** | 同上 |
| 非 REST 介面 | 1 WebSocket + 7 種 SSE 事件型別（**皆不在 `openapi.json`**） | 原始碼 grep |
| 資料表 | 7 實體 + 1 association table | `models.py` |
| 權限矩陣 | 11 角色 × 28 story = **308 列** | `ast.literal_eval` 解析 `rbac_seed_data.py` |
| 前端頁面／元件 | 8／12 | `git ls-files` |
| 前端 `fetch()` 呼叫點 | 52（10 支檔） | grep |
| **產生型別檔採用率** | **1/10**（`api.d.ts` 2,385 行，僅 `AdminPage.tsx` import） | grep |
| Backend 測試（靜態計數） | **212 個 `def test_`**，21 檔 | `grep -c` |
| Property-based（`@given`，靜態計數） | **13 處**，7 檔 | `grep -c` |
| E2E case（靜態計數） | **14 個 `test()`**，3 個 `describe()` | `grep -c` |
| **HTTP 層測試涵蓋的 operation** | **3 / 45** | 逐一核對 `TestClient` 呼叫點 |
| 模組級 docstring 覆蓋 | **22 / 25** | `ast.get_docstring` |
| `ci.yml` job 數 | **4**（11 個實質檢查步驟） | 解析 `jobs:` 區塊 |
| gh-aw agentic workflows | **11** | `ls .github/workflows/*.md` |
| `TODO`／`FIXME`／`HACK`／`XXX` 標記 | **0** | grep |

## 實測方法與限制

### 本次**實際執行**並取得結果的檢查（可作為執行結果引用）

| 指令 | 結果 |
|---|---|
| `python3 scripts/validate_repo_contract.py` | **passed**（exit 0） |
| `python3 scripts/validate_env_contract.py` | **passed**（exit 0） |
| `npx eslint .`（於 `frontend/`） | **0 errors, 3 warnings** |

三個 warning 皆為 `react-hooks/exhaustive-deps`：`AssessmentPage.tsx:365`、
`LoginPage.tsx:36`、`WorkspacePage.tsx:301`。

### 本次**未執行**的檢查（數字為靜態計數，不得被引用為「通過」）

| 項目 | 未執行原因 | 因此哪些數字是靜態計數 |
|---|---|---|
| `python -m unittest discover -s tests` | 掃描環境的 `.venv` 與系統 python3 皆缺 `fastapi`／`hypothesis`（17 個 import error）。**這是掃描環境限制，不是 repo 問題** —— CI 的 `backend` job 會安裝完整依賴 | **212 個 test、13 個 `@given`** 皆由 `grep -c "def test_"` 與 `grep -c "@given"` 得出。**不得寫成「212 個測試通過」** |
| `npx playwright test` | 需 `docker-compose.test.yml` 起完整 stack | **14 個 e2e case** 為 `grep -c` 靜態計數 |
| `docker build` | 未執行 | Dockerfile 分析為靜態閱讀 |

### 範圍外項目

以下項目**未被分析**，使用本 codekb 時不應假設它們已被涵蓋：

| 項目 | 原因 |
|---|---|
| `.claude/` | AIDLC v2 upstream 框架檔，非本專案應用程式碼；僅做結構清點，未逐檔精讀 |
| `aidlc/spaces/default/intents/` | AIDLC 工作產出（5 個 intent、數百檔），非程式碼；僅在需佐證跨分支狀態時 grep 引用 |
| **執行期行為** | 本次為**靜態分析**。未啟動系統、未實測 API、未查詢資料庫 |
| **staging 環境的實際 schema** | 未連線 `192.168.10.10` 查證；schema 描述來自 ORM／SQL 檔／DDL 補丁的靜態比對 |
| **LLM agent 的實際輸出品質** | prompt 內容已讀，但未評估產圖或評核建議的品質 |
| 效能與負載特性 | 未量測 |
| 安全滲透測試 | 未執行；安全發現純由靜態閱讀得出 |
| `danniel/feat/github-sync-phase1`（PR #508） | 不在本次基準分支上（見「跨分支狀態」） |

## 與規則層記載的落差（如實記載，不逕行修改規則層）

本次實測發現 `aidlc/spaces/default/memory/team.md` 的「既成事實」段落有數項已被推翻。
**本 codekb 記載實測到的現況；規則層的修訂須走 practices-discovery 的 affirmation gate，
不由 reverse-engineering stage 逕行變更。** 逐項對照見
`code-quality-assessment.md` 的「與 `team.md` 現行記載的落差」與 `dependencies.md` 的
「依賴釘選現況」。

摘要（四項）：

| # | `team.md` 現行記載 | 本次實測 |
|---|---|---|
| 1 | 「Backend 依賴 100% 未 pin、無 lockfile」 | `fastapi[standard]==0.141.1`、`pydantic==2.13.4` **已精確釘選**（12 條中 2 條） |
| 2 | 「`tsc -b` 對前後端 schema 落差無效；`AdminPage.tsx` 的 `DbUser` 是手寫本地 interface」 | `AdminPage.tsx` 已改用產生型別；存在 `openapi.json → openapi-typescript → api.d.ts` 建置期契約鏈與**兩道 CI gate** |
| 3 | 「零 HTTP 層測試，全 repo 無 `TestClient` 使用」 | `test_user_list_endpoint.py` 有 17 個 test、2 個 `TestClient(app)` 建構點 |
| 4 | 「CI（`ci.yml`）四道關卡」 | job 數確實仍是 **4**，但**步驟清單已過時** —— 現為 11 個實質檢查步驟，新增 `validate_env_contract.py`、`check:types`、`dump_openapi.py --check`、spec-not-served 四道 |

## 產出清單

本次逆向工程共產出 **9 份 artifacts**，全部位於
`aidlc/spaces/default/codekb/cloud-360/`：

| # | 檔案 | 內容 | 主要下游消費者 |
|---|---|---|---|
| 1 | `business-overview.md` | 業務領域、11 角色、28 story 能力表、四條業務主線、詞彙表 | requirements-analysis、user-stories |
| 2 | `architecture.md` | 架構風格判定與替代方案、系統脈絡、分層、橫切關注點、**型別契約鏈**、**機械檢查盲區**、Interaction Diagrams、架構約束清單 | application-design、functional-design |
| 3 | `code-structure.md` | 倉庫佈局、模組組織、程式碼模式、命名慣例 | code-generation |
| 4 | `api-documentation.md` | 45 operation 完整清單、認證授權契約、SSE／WebSocket 契約、資料契約 | application-design、code-generation |
| 5 | `component-inventory.md` | 全元件清單與職責、依賴摘要、`users` 表詳解 | application-design、units-generation |
| 6 | `technology-stack.md` | 語言與框架版本、建置系統、版本治理現況 | infrastructure-design、code-generation |
| 7 | `dependencies.md` | 外部依賴、外部服務、隱性硬依賴、內部依賴、schema 來源、風險登記 | application-design、infrastructure-design |
| 8 | `code-quality-assessment.md` | 測試／lint／CI 現況、技術債叢集與分級、修復順序 | delivery-planning、requirements-analysis |
| 9 | `reverse-engineering-timestamp.md` | 本檔 | 全部（先讀本檔確認新鮮度） |

**codekb 的層級**：本目錄位於 **space 層級**（`aidlc/spaces/default/codekb/`），
是 `memory/`、`knowledge/`、`intents/` 的同層兄弟，**跨 intent 共用**。

### 關於 `codekb/cloud/` 的裁定

`aidlc/spaces/default/codekb/` 下同時存在 `cloud-360/`（本目錄）與 `cloud/` 兩份 codekb，
成因是 repo 名解析出兩個不同的 key。**本次 stage 的 `codekb-path` 解析結果為 `cloud-360`，
故本次只更新本目錄，`cloud/` 未被觸碰。**

`cloud/` 是另一個 intent（`260806-a1-a3-ux`）的產出，基準為 commit `8c90f40`
（UTC 2026-08-06），**已過期**。下游 stage 應以本目錄為準；讀到 `cloud/` 時須先確認其
基準日期。兩份 codekb 的收斂（合併或廢止其一）尚未定案，列為待處理項。

## 新鮮度與失效條件

本 codekb 在下列任一情況發生時應重新產出或局部更新。

### 觸發完整重跑

- `backend/services/` 新增或刪除模組（目前 **22** 支）
- API operation 數改變（目前 **45**；以 `openapi.json` 為準，非人工計數）
- 資料表新增或刪除（目前 7 實體 + 1 association table）
- 架構風格改變（例如拆出獨立服務、引入訊息佇列或快取層）
- 權限矩陣維度改變（角色數不再是 11 或 story 數不再是 28）
- **PR #508 合併** —— `scripts/` 由 4 支增為 7 支，且引入 GitHub Issues／Projects／Wiki
  這條全新的對外整合面（見「跨分支狀態」）

### 觸發局部更新

| 變更 | 應更新的檔案 |
|---|---|
| `users` 表欄位變更 | `component-inventory.md`、`api-documentation.md`、`architecture.md` |
| 依賴釘選範圍變更或引入 lockfile | `technology-stack.md`、`dependencies.md`、`code-quality-assessment.md` |
| `api.d.ts` 採用率變化（目前 1/10） | `architecture.md`、`code-quality-assessment.md`、`code-structure.md` |
| 新增 HTTP 層測試（目前涵蓋 3/45 operation） | `code-quality-assessment.md`、`api-documentation.md` |
| CI 步驟增減 | `code-quality-assessment.md`、`technology-stack.md` |
| 部署拓撲變更（新容器、新環境） | `architecture.md`、`technology-stack.md`、`dependencies.md` |
| 新 story 或新角色 | `business-overview.md`、`api-documentation.md` |
| WebSocket／SSE 契約變更 | `api-documentation.md`、`architecture.md`（機械檢查盲區一節） |
