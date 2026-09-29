# Reverse Engineering Timestamp — Cloud-360

> 本檔是 `aidlc/spaces/default/codekb/cloud-360/` 這份程式碼知識庫的**新鮮度標記**。
> 使用本 codekb 的任何 stage 都應**先讀本檔**，確認基準是否仍然有效，
> 並確認你要引用的那一節屬於哪一種新鮮度等級。

## 掃描基準

| 項目 | 值 |
|---|---|
| **日期** | 2026-08-23 |
| **Commit** | `9307dbc` |
| **Commit 訊息** | `修正(api): /me 回應補上規格要求的 last_opened_diagram_id` |
| **Branch** | `danniel/fix/me-last-opened-diagram-id` |
| **前一基準** | `c3de2c8`（2026-08-17，branch `danniel/fix/production-path-check-noop`） |
| **Repository** | `opendiamonds/cloud-360`（本 clone 的目錄名為 `chiton`，見「關於 codekb 目錄名」） |
| **AIDLC stage** | `reverse-engineering`（inception 2.1，`mode: pipeline`） |
| **執行方式** | 兩環 pipeline：link 1 developer agent 掃描、link 2 architect agent 綜整與寫檔 |

### 本輪是**兩區定向掃描 ＋ 差異標註**，不是完整重掃

這是本檔最重要的一句話。**approval-handoff Q3 選了 A**，把本 stage 的範圍界定為兩區；
完整全 repo 重掃已被提出並**明確否決**。因此：

| 範圍 | 處理方式 |
|---|---|
| **Area 1 — AI-DLC 狀態表徵**（`intents.json`、6 個 `aidlc-state.md`、state 模板、`getField`／`setField` 語意、`.gitignore` 邊界、audit shard） | **實掃並全新撰寫** |
| **Area 2 — gh-aw workflow 語料**（11 組 `.md` + `.lock.yml`、`agentics-maintenance.yml`、`ci.yml`／`deploy.yml` 共存面） | **實掃並全新撰寫** |
| **其餘全部**（backend、frontend、schema、部署、測試、技術債……） | **未重新推導**。內容仍為 `c3de2c8` 的結論，逐節加上過期標註 |

**新鮮度標記的讀法**（各 artifact 的節標題後會出現其中之一）：

| 標記 | 意義 | 可信度 |
|---|---|---|
| **［本輪重寫］** | 本輪在 `9307dbc` 上實掃並改寫 | 高 |
| **［本輪機械複驗］** | 本輪未做深度掃描，但以 grep／解析器等機械方式重新量測過該節引用的數字 | 高（僅限被複驗的那個數字） |
| **［差異標註］** | 本輪**未重新推導**，只依 `c3de2c8..9307dbc` 的 diff 指出哪裡已過期 | 中：指出的過期點可信，未指出處不代表沒過期 |
| **［沿用 `c3de2c8`］** | 本輪完全未觸及 | 以 `c3de2c8` 為準，可能已漂移 |

**差異標註的證據強度分兩級，artifact 內會註明**：

- **已讀 diff**：link 1 實際看過該檔的逐行 diff。
- **僅 diffstat**：link 1 只看了 `--stat` 與 commit 訊息，一行級描述是推得的。
  下列檔案屬此級，**引用其描述時不得當成已核對過的事實**：`LOCAL-DEV.md`、`DEPLOY.md`、
  `CLAUDE.md`、`useCollaboration.ts`、`LoginPage.tsx`、`WorkspacePage.tsx`、
  `LastActivityCell.tsx`、`regression.spec.ts`、7 個後端測試檔。

## 差異總覽（`c3de2c8..9307dbc`）

20 個 commit、71 個檔案。分為三類。

### (a) 落在兩個掃描區內 —— 已完整重掃

`intents.json`（新增 `260816-production-path-check` 一列）、
`260816-production-path-check/aidlc-state.md`（走完 8 個 EXECUTE stage、`Status` 翻為 `Completed`）、
兩個 audit shard、`ui-regression.md` 與其 `.lock.yml`（新增 `timeout-minutes` 警告註解、
Playwright 瀏覽器快取 step、四處 `timeout(1)` 包裹）、`.github/aw/actions-lock.json`
（新增 `actions/cache@v4`）、`deploy.yml`（兩個 job 的 `render-env.sh` 呼叫各補
`CLOUD360_BOOTSTRAP_ADMIN_PASSWORD`）。

### (b) 掃描區外，但會使既有 codekb 內容過期

**下表只指出過期點，本輪沒有重新推導這些 artifact 的內容。**

| 變更 | 過期的 artifact 與節 | 證據強度 |
|---|---|---|
| `backend/services/auth.py` —— `JWT_SECRET` 硬編 fallback 改為僅 `APP_ENV ∈ {local,test,ci}` 允許、否則 `RuntimeError`；`datetime.utcnow()` → `datetime.now(timezone.utc)`；抽出 `get_user_from_token()` | `architecture.md` 橫切關注點、`component-inventory.md`、`code-quality-assessment.md` T-14／T-20、`dependencies.md` R-2 | 已讀 diff **＋ 本輪複驗** |
| `backend/services/collab_router.py` —— WebSocket 由**無認證**改為必須帶 `?token=`（`_authorize_ws_user()`，失敗以 close code 1008／1003 斷線）；新增 payload 上限驗證 | `api-documentation.md` WebSocket 契約、`architecture.md` 張力四、`code-quality-assessment.md` T-16 | 已讀 diff **＋ 本輪複驗** |
| `backend/database.py` —— 新增 `_allow_insecure_default_users()`／`_allow_insecure_default_personas()`／`_bootstrap_admin_password()`；persona demo 帳號只在 `APP_ENV=local` 建立；固定密碼僅 local/test/ci 或明確 opt-in | `architecture.md`、`dependencies.md`、`code-quality-assessment.md` T-15 | 已讀 diff **＋ 本輪複驗** |
| `frontend/src/context/AuthContext.tsx` —— token 由 `localStorage` 改存 `sessionStorage`，並新增 `clearLegacyAuthStorage()` | `architecture.md`、`component-inventory.md`、`api-documentation.md` 認證契約 | 已讀 diff **＋ 本輪複驗** |
| `schema_rbac.sql` —— **刪除整個 D) 區塊**（固定密碼 admin 的 INSERT／UPDATE）；531 → **510 行** | `architecture.md` 張力一、`dependencies.md` 三份 schema 來源、`code-quality-assessment.md` T-15 | 已讀 diff **＋ 本輪複驗** |
| `backend/env_bootstrap.py`（**新檔**，36 行）＋ `main.py` —— `backend/.env` 的單一載入點，路徑釘死 `Path(__file__).resolve().parent / ".env"` | `code-structure.md` Backend 模組組織、`component-inventory.md`、`dependencies.md` | 已讀 diff **＋ 本輪複驗** |
| `openapi.json` ＋ `user_router.py` ＋ `api.d.ts` —— `MeResponse` 新增 `last_opened_diagram_id`；request schema 加上 `maxItems`／`minLength`／`maxLength`；pydantic v1 `orm_mode` 改為 v2 `ConfigDict(from_attributes=True)`；`login()` 新增 `record_activity` | `api-documentation.md` 資料契約、`technology-stack.md` deprecated 清單 | 已讀 diff **＋ 本輪複驗** |
| `scripts/validate_repo_contract.py` —— production 路徑檢查由 `git diff` 基準改為 `git ls-files` 全域掃描（issue #509） | `code-quality-assessment.md` T-13、`code-structure.md` | 已讀 diff |
| `frontend/package.json` —— `react-router-dom` `^6.22.0` → **`^7.18.2`**（major bump）；移除 `@types/react-router-dom` | `technology-stack.md`、`dependencies.md`、`code-quality-assessment.md` T-23 | 已讀 diff **＋ 本輪複驗** |
| `backend/tests/` —— 新增 4 檔（`test_dotenv_path.py`、`test_me_endpoint.py`、`test_database_security.py`、`test_repo_contract_production_paths.py`） | `code-quality-assessment.md` 測試現況、`component-inventory.md`、`api-documentation.md` 缺口 1 | 僅 diffstat **＋ 本輪機械複驗** |
| `frontend/.env.example`、`vite-env.d.ts`、`LoginPage.tsx` —— 新增 `VITE_ENABLE_DEMO_QUICK_USERS` | `technology-stack.md`、`dependencies.md` | 已讀 diff（前二）／僅 diffstat（後一） |
| `deploy/*`、`backend/.env.example` —— 三環境全部加入 `CLOUD360_BOOTSTRAP_ADMIN_PASSWORD`；另加兩個 `ALLOW_INSECURE_*` 註解式 opt-in | `dependencies.md` 環境變數、`technology-stack.md` | 已讀 diff |
| `CLAUDE.md`、`DEPLOY.md`、`LOCAL-DEV.md` | `business-overview.md`、`code-quality-assessment.md` 文件品質 | **僅 diffstat** |
| `frontend/src/hooks/useCollaboration.ts`、`LastActivityCell.tsx`、`WorkspacePage.tsx`、`tests/e2e/regression.spec.ts` | `api-documentation.md`、`component-inventory.md`、`code-quality-assessment.md` | **僅 diffstat** |

**橫切主線**：這 20 個 commit 的主線是 **PR #526「強化認證與部署預設值」的安全硬化**
（`b8d69a6`）加四個後續 fix，再加 `7cb6703`（`.env` 路徑）與 `9307dbc`（`/me` 補欄位）。
**codekb 中所有描述「預設帳號 admin/admin123」「WebSocket 無認證」「token 存 localStorage」
「`JWT_SECRET` 有硬編 fallback」的段落都已過期，本輪已逐處更正。**

### (c) 不相關

30 個 `aidlc/` 路徑（9 個 codekb 檔本身 ＋ 另一個 intent 的 stage artifact ＋ audit shard）。
本 intent（`260822-gh-projects-sync`）今天寫的檔**完全不在這個 diff 內**，因為整個 record
目錄仍未追蹤（見下）。

## 跨分支狀態（本基準的重大限制）

**本 codekb 的基準 `9307dbc` 已落後 `origin/ut`。** 本輪以 `git fetch origin ut` 實測，
`origin/ut` 現為 `be73385`，含**三項本基準看不到的變更**，其中兩項直接影響本 codekb 的結論：

| # | `origin/ut` 上的變更 | 對本 codekb 的影響 |
|---|---|---|
| 1 | `f4047a1`／PR #532 —— **gh-aw 由 `v0.81.6` 升級至 `v0.86.2`**，11 組 workflow 全部重新編譯；`copilot` engine `1.0.65` → **`1.0.79`**；`actions-lock.json` 由 5 筆減為 **4 筆**（`github/gh-aw-actions/setup-cli@v0.81.6` 消失、`setup@v0.86.2` 換新 SHA） | **Area 2 的每一項版本相關事實只對 `9307dbc` 成立**。尤其 `ui-regression.md` 記載的「gh-aw v0.81.6 會靜默丟棄 `pre-agent-steps` 內的 `timeout-minutes`」是**對 v0.81.6 的實測**，在 v0.86.2 上未複驗 |
| 2 | `be73385`／PR #508 —— `scripts/` 由 4 支增為 **7 支**：`aidlc_sync_push.py`／`aidlc_sync_pull.py`／`aidlc_sync_buglist.py`（ADR-0012 階段 1／2／2.5） | `code-structure.md` 與 `component-inventory.md` 的 `scripts/` 清單在 `ut` 上已不正確。**且與 ADR-0013 及 `project.md ## Forbidden` 的新規則構成待解衝突**（見下） |
| 3 | `fe798d3`／PR #533 —— 本分支自身的合併 | 無 |

> **前一版 codekb 記載「PR #508 待合併（`state: OPEN`）」，該記載已過期。**
> 本輪以 `gh pr view 508` 實測為 `state: MERGED`、`mergedAt: 2026-08-22T06:23:18Z`。
> 三支腳本確實存在於 `origin/ut`（`git ls-tree origin/ut scripts/` 實測），
> 只是不在本基準 commit 上。

**升級 gh-aw 對 `.md` 雜湊的實測結論（新發現）**：`pr-reviewer.lock.yml` 在 v0.81.6 與
v0.86.2 兩個版本下的 `frontmatter_hash` 與 `body_hash` **逐字相同**
（`0a2a0f6e…` / `08111765…`），只有 `compiler_version` 與 `engine_versions` 改變。
這證實兩件事：雜湊涵蓋的是 `.md` 的兩半而非編譯輸出，因此**可用來偵測 `.md` 漂移，
但偵測不到「該用新編譯器重編了」**。

## 工作目錄狀態（本輪的掃描對象包含未追蹤內容）

掃描當下工作樹**非乾淨**：

```
 M .claude/tools/data/scope-grid.json
 M aidlc/spaces/default/intents/260802-default/inception/decisions/0012-*.md
 M aidlc/spaces/default/intents/intents.json
 M aidlc/spaces/default/memory/project.md
?? .claude/scopes/aidlc-aidlc-github-projects-sync.md
?? aidlc/spaces/default/intents/260822-gh-projects-sync/
```

**判定（本 stage 作出，link 1 留給 link 2 決定）**：`260822-gh-projects-sync` 這個 record
**納入 Area 1 的掃描對象**，因為它是六個 record 中**唯一**處於 `[-] in progress` 的實例，
對狀態詞彙的分析不可或缺。但 `architecture.md` 對它的每一處引用都標註為
**「工作樹狀態、尚未進版控」**，任何只看已提交內容的機制（例如跑在 GitHub Actions 上的
同步 workflow）**看不到它**。

同理，`intents.json` 的 `260822` 那一列與 `project.md` 的最新規則（2026-08-23 新增的
`## Forbidden` 條款）目前也只存在於工作樹。

## 本輪額外讀入的兩份 ADR（超出 link 1 的掃描邊界）

link 1 依界線正確地未讀這兩份；link 2 讀了，因為它們是本 intent 的直接前案。
**兩者已寫入 `architecture.md` 的「開發流程層架構」。**

| ADR | 狀態 | 要點 |
|---|---|---|
| `260802-default/inception/decisions/0012-github-issues-projects-wiki-sync.md` | **Accepted 2026-08-16，部分經 ADR-0013 修訂** | AI-DLC ↔ GitHub Issues／Projects／Wiki 雙向同步；逐欄位切分真實來源；防迴圈三道防線；與主流程零耦合 |
| `260822-gh-projects-sync/inception/decisions/0013-aidlc-projects-sync-scoping.md` | **Accepted 2026-08-23** | 修訂 0012 的第 1、5 點與階段表：映射改為 intent → Project #16 的一則 issue；承載改為 gh-aw safe-outputs、移除 `scripts/aidlc_sync_*.py`；階段順序重排 |

**ADR-0012 不可獨立閱讀，必須與 ADR-0013 併讀。** ADR-0012 的 Status 行已加註修訂指標。

**由此浮現的一項待解衝突（本 stage 只記載，不裁定）**：ADR-0013 把
`scripts/aidlc_sync_*.py` 從設計中**移除**，且 `project.md ## Forbidden` 於 2026-08-23
新增「不得以 repo 內新增的實作程式承載流程自動化與外部系統同步」；
而 PR #508 已於 **2026-08-22**（規則生效前一天）把這三支腳本合併進 `ut`。
規則字面寫「**新增**的實作程式」，這三支在規則生效時已存在，因此「既有豁免／遷移到
gh-aw／收窄規則」三者之間需要一個明確決定。

## 本輪實測方法與限制

### 本輪**實際執行**並取得結果的檢查

| 指令／方法 | 結果 |
|---|---|
| `git fetch origin ut` ＋ `git merge-base --is-ancestor` | 確認基準落後 `ut` 三個 commit，PR #508 已合併 |
| `gh pr view 508 --json state,mergedAt` | `MERGED` / `2026-08-22T06:23:18Z` |
| `python3` 解析 `openapi.json` | **36 paths / 45 operations / 29 schemas**（與前一基準相同，未變） |
| `git ls-files` ＋ `wc -l` 於 `schema_rbac.sql` | **510 行**（前一基準 531） |
| `grep -c` 於 `backend/tests/` | **25 個 `test_*.py`**（前一基準 21）、**247 個 `def test_`**、**14 個 `@given`**（8 檔） |
| `grep -rl TestClient backend/tests/` | 4 檔（`helpers.py`、`test_auth.py`、`test_user_list_endpoint.py`、`test_me_endpoint.py`） |
| `grep -c` 於 `regression.spec.ts` | **3 describe / 14 `test()`**（未變） |
| `python3` 解析 `frontend/package.json` | `react-router-dom@^7.18.2`；`@types/react-router-dom` 已移除 |
| 直接閱讀 `auth.py` / `collab_router.py` / `database.py` / `AuthContext.tsx` / `env_bootstrap.py` 的相關段落 | 逐一確認 PR #526 的四項硬化 |

**測試數字仍為靜態計數，不是執行結果。** 本輪**未執行** `python -m unittest`、
未執行 Playwright、未執行 `docker build`、未執行 `validate_repo_contract.py`
與 `validate_env_contract.py`、未執行 `eslint`。前一基準記載的
「`0 errors, 3 warnings`」與兩支 validator「passed」**本輪未複驗**，屬 ［沿用 `c3de2c8`］。

### 未讀清單（link 1 的邊界，link 2 未補上者原樣保留）

**下游不得假設下列任何一項已被涵蓋。**

1. **11 個 `.lock.yml` 沒有任何一個被全讀**（各 1,500–1,700 行、101–111 KB 的生成檔）。
   讀的是：`daily-digest.lock.yml` 前 70 行、`pr-reviewer.lock.yml` 的 per-job permissions、
   11 檔的 `name`／`on`／`permissions`／`concurrency`／`jobs`／`runs-on` 結構 grep、
   `ui-regression.lock.yml` 的 diff。**agent job 內部的 prompt 組裝、firewall 設定、
   MCP server 啟動、safe-output 收集腳本，一行都沒看。**
2. **gh-aw 的完整 `safe-outputs` 型別目錄未由本 stage 直接查證。** 本 repo 語料只用過 5 種
   （`add-comment`／`create-issue`／`push-to-pull-request-branch`／`add-labels`／`close-issue`）。
   **這 5 種是本 repo 的用量，不是框架的目錄。** ADR-0013 於 2026-08-23 查證官方文件確認框架
   另有 `update-project`／`create-project`／`create-project-status-update` 與 `projects` toolset
   ——**該事實的來源是 ADR-0013，不是本次掃描**，且是對 v0.86.2 世代文件的查證。
3. **`agentics-maintenance.yml`（26,686 B）只讀了前 60 行**；**`copilot-setup-steps.yml`
   （772 B）完全未讀**；**`.github/agents/agentic-workflows.md` 只 grep 了 safe-outputs 段落**，
   未通讀（它含 gh-aw CLI 用法與 Dependabot 處理規則，對實作可能有用）。
4. **`aidlc-state.ts`（3,503 行）未通讀。** `park`／`unpark` 對 `Parked` 欄位的完整寫入語意、
   gate-start／approve／reject／revise 對 checkbox 的轉換規則，**只從欄位名與呼叫點推斷，
   未逐行驗證**。
5. **audit shard 內容未精讀。** 只做了事件型別統計（44 種）與一個 shard 的前 40 行取樣。
   **每種事件帶哪些 `**Key**:` 欄位，未盤點。**
6. **codekb 自身的 9 個 artifact，link 1 只讀了 H2 清單**（不含本檔前 40 行）。
   (b) 表的「會使哪個 artifact 過期」是依 H2 標題對映的；link 2 已補上全文閱讀並逐節標註。
7. **全 repo 巡覽未做**（Q3=A 明確排除）。`backend/services/` 的 ~20 支模組、
   `frontend/src/pages/` 的其餘頁面、`scripts/` 的其他 3 支、`schema.sql`、`plugins/`、
   `.claude/skills/` 全部未掃。
8. **執行期行為未觀察**：未啟動系統、未實測 API、未查詢資料庫、未連線 `192.168.10.10`。
9. **`origin/ut` 上的 v0.86.2 世代 workflow 未掃描**，只比對了 metadata 標頭與
   `actions-lock.json`。

## 產出清單

本輪共更新 **9 份 artifacts**，全部位於 `aidlc/spaces/default/codekb/cloud-360/`：

| # | 檔案 | 本輪處理 |
|---|---|---|
| 1 | `business-overview.md` | 開發流程層資產一節［本輪重寫］；其餘［沿用］加標註 |
| 2 | `architecture.md` | **新增「開發流程層架構」兩大節（Area 1 + Area 2）與兩份 ADR 的落點**［本輪重寫］；安全硬化四處更正；其餘［差異標註］ |
| 3 | `code-structure.md` | `.github/workflows/` 佈局與 `scripts/` 跨分支狀態［本輪重寫］；`env_bootstrap.py`、測試檔數［本輪機械複驗］ |
| 4 | `api-documentation.md` | WebSocket 契約［本輪重寫］；`MeResponse`／請求約束／HTTP 層覆蓋［本輪機械複驗］；端點清單［差異標註］ |
| 5 | `component-inventory.md` | gh-aw workflow 表［本輪重寫］；認證與 WebSocket 元件、`env_bootstrap`［本輪機械複驗］ |
| 6 | `technology-stack.md` | gh-aw 版本與 runner［本輪重寫］；前端依賴［本輪機械複驗］；其餘［差異標註］ |
| 7 | `dependencies.md` | GitHub 平台依賴與環境變數［本輪重寫／複驗］；R-2 已解除；其餘［差異標註］ |
| 8 | `code-quality-assessment.md` | 安全叢集 C4 大幅改寫、T-13／T-23 已解決、新增 gh-aw 編譯漂移債［本輪重寫］；其餘［差異標註］ |
| 9 | `reverse-engineering-timestamp.md` | 本檔，全面重寫 |

**codekb 的層級**：本目錄位於 **space 層級**（`aidlc/spaces/default/codekb/`），
是 `memory/`、`knowledge/`、`intents/` 的同層兄弟，**跨 intent 共用**。

### 關於 codekb 目錄名（本輪的裁定，與前一版不同）

`aidlc/spaces/default/codekb/` 下有兩份 codekb：`cloud-360/`（本目錄，3,000+ 行，最完整）
與 `cloud/`（582 行，基準 `8c90f40`／2026-08-06，**已過期**）。

**本輪的 clone 目錄名是 `chiton`**，而引擎的 `codekbRepoName` 由 `basename(projectDir)`
推導，若照預設會為**同一個 repo** 開出**第三份** codekb（`codekb/chiton/`）。
本 stage 已由人工裁定：**就地更新 `cloud-360/`，不建立 `chiton/`。**
引擎的完成檢查對 `codekb/*/` 做 ANY-exists 判定，寫進 `cloud-360/` 即滿足。

**刻意不去手改 `intents.json` 補上 repo 名**：一旦寫入 repo 名，swarm `prepare` 會去找
一個不存在的同名兄弟目錄。兩份（潛在三份）codekb 的收斂仍是**未定案的待處理項**。

## 新鮮度與失效條件

### 本 codekb 目前已知的失效面（讀者必須先知道）

1. **基準落後 `origin/ut` 三個 commit**，其中 gh-aw v0.86.2 升級與 PR #508 合併都會改變
   本 codekb 的結論（見「跨分支狀態」）。**下一輪 reverse-engineering 應以 `ut` 為基準。**
2. **本輪只重掃兩區**，其餘七成內容的實際新鮮度是 `c3de2c8`（2026-08-17）。

### 觸發完整重跑

- `backend/services/` 新增或刪除模組（`c3de2c8` 時為 22 支，本輪未複驗）
- API operation 數改變（**本輪複驗仍為 45**；以 `openapi.json` 為準，非人工計數）
- 資料表新增或刪除（`c3de2c8` 時為 7 實體 + 1 association table）
- 架構風格改變（拆出獨立服務、引入訊息佇列或快取層）
- 權限矩陣維度改變（角色數不再是 11 或 story 數不再是 28）
- **合併 `origin/ut`**（gh-aw v0.86.2 ＋ `scripts/` 4→7 兩項同時生效）

### 觸發局部更新

| 變更 | 應更新的檔案 |
|---|---|
| gh-aw 版本升級或新增／刪除 workflow | `architecture.md`（開發流程層）、`component-inventory.md`、`technology-stack.md`、`dependencies.md` |
| `aidlc-state.md` 模板或 stage graph 改變 | `architecture.md`（AI-DLC 狀態表徵）、`business-overview.md` |
| `intents.json` 的 schema 或 `status` 值域改變 | `architecture.md`（AI-DLC 狀態表徵） |
| `users` 表欄位變更 | `component-inventory.md`、`api-documentation.md`、`architecture.md` |
| 依賴釘選範圍變更或引入 lockfile | `technology-stack.md`、`dependencies.md`、`code-quality-assessment.md` |
| `api.d.ts` 採用率變化（`c3de2c8` 時 1/10） | `architecture.md`、`code-quality-assessment.md`、`code-structure.md` |
| 新增 HTTP 層測試（**本輪複驗為 5/45 operation**） | `code-quality-assessment.md`、`api-documentation.md` |
| CI 步驟增減 | `code-quality-assessment.md`、`technology-stack.md` |
| 部署拓撲變更（新容器、新環境） | `architecture.md`、`technology-stack.md`、`dependencies.md` |
| 新 story 或新角色 | `business-overview.md`、`api-documentation.md` |
| WebSocket／SSE 契約變更 | `api-documentation.md`、`architecture.md`（機械檢查盲區一節） |
