# Code Quality Assessment — Cloud-360

> **基準**：`34aeef3`（2026-10-02）。**新鮮度等級與證據標記的定義在 `reverse-engineering-timestamp.md`**。
> 本檔由 `codekb/cloud-360@2026-09-22`（T-1～T-13 ＋ 紀律清單）與 `codekb/cloud@2026-10-01`
> 合併，並新增 T-14～T-18。**無任何技術債項目被丟棄。**
>
> ⚠️ **本輪確實有執行結果，但只有下列四項**（`[跑:link1]`，由 link 1 實跑）：
> `python3 -m unittest discover -s tests`、`npm run lint`、
> `validate_cost_calculator_boundary.py`、`validate_pricing_lookup_boundary.py`。
> **其餘任何「通過／全綠」字樣都不是本輪驗證的**，完整的跑了／沒跑清單在時間戳檔。

---

## 測試現況

| 面向 | 本輪數字 | 取得方式 | 對既有記載的更正 |
|---|---|---|---|
| **測試執行結果** | **Ran 419 tests, OK**（28.557s） | `[跑:link1]` `python3 -m unittest discover -s tests` | 兩份 store **都沒有**執行結果（皆自我限制為靜態計數） |
| backend 測試檔 | **46 支 `test_*.py`**（目錄內 `.py` 共 48，另有 `helpers.py`、`__init__.py`） | `[跑]` 本輪程式計數 | `team.md` 的「21 支」、`cloud-360/` 的「37 支」、link 1 的「48 支測試檔」**三者皆不準** |
| `@given`（property-based） | **48 處，分佈 16 支檔** | `[跑]` `grep -rl` ／ `grep -rh` | `team.md` 的「13 處／7 支」、`cloud-360/` 的「17 處／10 支」皆過時 |
| `TestClient` 使用 | **6 支測試檔 ＋ `helpers.py`** | `[跑]` `grep -rl` | `team.md` 的「唯一使用例是 `test_user_list_endpoint`」已過時 |
| frontend e2e | **2 支 spec** | `[算]` | — |
| 覆蓋率量測 | **完全不存在** | `[跑:link1]`／`[算]` | 沿用（仍成立） |

**`@given` 的 16 支檔** `[跑]`：`test_a3_langgraph_migration`、`test_activity`、`test_auth`、
`test_collab`、`test_design_agent`、`test_diagram_builder`、`test_diagram_icons`、
**`test_dump_ws_contract`**、`test_estimate_parser`、`test_estimate_validator`、
**`test_hierarchy_migration`**、`test_llm_provider`、`test_repo_contract_production_paths`、
`test_sku_catalog`、`test_wa_rule_engine`、**`test_ws_contract`**（粗體為本輪新增的 WS／階層相關）。

**`TestClient` 的 6 支檔** `[跑]`：`test_auth`、`test_cost_advice_agent`、
`test_estimate_intake_api`、`test_legacy_cost_retirement`、`test_me_endpoint`、`test_user_list_endpoint`。

### 測試框架與基礎設施 〔B〕

- Backend：Python 內建 `unittest` ＋ `hypothesis` ＋ `unittest.mock`。**未使用 pytest** `[算]`。
  CI 指令 `python -m unittest discover -s tests -v`（`ci.yml:297` `[算]`）。
- Frontend：Playwright，單一 `chromium` project、`retries: process.env.CI ? 1 : 0`
  `[承:cloud-360@2026-09-22]`。**前端無 unit／component 測試框架** `[讀]`
  （`package.json` 的 `devDependencies` 逐項核對，無 vitest／jest／`@testing-library/*`）。
- **測試 DB 策略（本輪實讀，已變更）** 〔A〕 `[讀]` `backend/tests/helpers.py:1–25`：

  ```
  if importlib.util.find_spec("psycopg") is None:
      _psycopg_stub = MagicMock()
      _psycopg_stub.__version__ = "3.2.0"   # dialect 建構時會對它跑 re.match 取版號
      sys.modules.setdefault("psycopg", _psycopg_stub)
  ```

  即：**改 mock `psycopg`（v3）而非 `psycopg2`，且改為條件式**（只在真的沒裝時才樁）。
  仍走 **in-memory SQLite**。
  > **`team.md` 的 Testing Posture 逐字記載「在任何 DB import 前
  > `sys.modules.setdefault("psycopg2", MagicMock())`」——該句已過時**，
  > 因為 `psycopg2` 已不在相依裡（`psycopg[binary]` 取代之）。
  > 本 codekb 只記載落差，**不改規則檔**。

- **本輪未讀 45 支測試檔的內容** 〔E〕。唯一例外是 `test_llmic_provider` 的類別／測試名稱列
  （見 T-19 的 `RetiredCliMode` 一節）與 `helpers.py:1–25`。

### 覆蓋率門檻的定位（誠實記載）〔A〕

`org.md` 宣告「最低 80% line coverage」。實際狀態 `[跑:link1]`：
`ls .coveragerc` → No such file；`ls pyproject.toml setup.cfg .ruff.toml ruff.toml mypy.ini backend/pyproject.toml`
→ **六個全部 No such file**；`requirements.txt` 無 `coverage`／`pytest-cov`；`ci.yml` 無 coverage step。

**此門檻目前既無法量測也無法強制，是宣告而非閘門。**
不在本檔弱化 `org.md` 的原文，只如實記載承載機制缺席。

---

## Lint、格式與型別檢查

| 面向 | Frontend | Backend |
|---|---|---|
| Linter | ESLint 10 flat config；CI 跑 `npm run lint` = `eslint .`，**未加 `--max-warnings 0`**，故只擋 error `[讀]` `package.json` | **完全沒有** `[跑:link1]` |
| Formatter | **無**（repo 根無 `.prettierrc`——`org.md` 預設的 Prettier 從未被引入，非「引入後又拿掉」）`[跑:link1]` | **無**（無 Black）`[跑:link1]` |
| Type checker | `tsc -b`（隨 `npm run build`）`[讀]` | **無**（無 mypy／pyright）`[跑:link1]` |
| 依賴鎖定 | `package-lock.json` 已 commit `[算]` | **無 lockfile** `[跑]` |

### ESLint 的實際狀態（本輪有執行結果）〔A〕

`[跑:link1]` 從 `frontend/` 執行 `npm run lint`，exit 0，輸出逐字：

```
src/pages/AssessmentPage.tsx
  365:6  warning  React Hook useEffect has a missing dependency: 'detectProviderFromXml'. ...  react-hooks/exhaustive-deps

src/pages/WorkspacePage.tsx
  302:6  warning  React Hook useEffect has a missing dependency: 'fetchDiagrams'. ...  react-hooks/exhaustive-deps

✖ 2 problems (0 errors, 2 warnings)
```

**與 `team.md` 的記載比對**（`team.md` 記 3 個 warning）：

| 項 | `team.md` | HEAD `[跑:link1]` | 變化 |
|---|---|---|---|
| `AssessmentPage.tsx:365` | 有 | **有（行號相同）** | 不變 |
| `LoginPage.tsx:36` | 有 | **無** | **已修掉** |
| `WorkspacePage.tsx:279` | 有 | **`:302`** | **行號位移 23 行**（同一個 `fetchDiagrams` 警告） |

> `cloud-360/` 與 `cloud/` 兩份 store 都寫「本輪未執行 lint，故不重述計數」
> ——本輪**有**執行結果，故上表是 HEAD 的實況。

### `tsc -b` 的既知盲區 〔C〕

前端存在手寫本地 interface 的形狀（例如 `const data = await res.json(); return data;`
把 `any` 直接放行），與後端 Pydantic schema 無編譯期連結。
OpenAPI 漂移閘門縮窄了此缺口但**未歸零**——`api.d.ts` 只在被實際採用的呼叫點才起作用。
**本輪未複驗採用率** 〔E〕。

---

## CI/CD

### `ci.yml`：5 個 job，14 條可讓 CI 紅燈的步驟 〔B〕

**不以「N 道閘門」的概括數字代替清單**——那個數字的定義會漂移，而清單不會。
本輪 `[算]` 逐條讀出 `run:` 行：

| Job（行） | 步驟（行） | 擋什麼 |
|---|---|---|
| `gate`（`:55`） | `:82` 判斷是否來自 `[aidlc-sync]` 回寫；命中則 skip 其餘四者（`:92` 有註解解釋 `set +e` 為何必要） | — |
| `repo-contract`（`:141`） | `:154` `validate_repo_contract.py` | repo 必要文件／必要文字／文件語言／禁止路徑／禁止內容 |
| | `:159` `validate_env_contract.py` | 三個環境設定不得互相混用或漏接 |
| | `:162` `validate_cost_calculator_boundary.py` | 純函式三支及其遞移 import 不得碰 I/O |
| | `:167` `validate_pricing_lookup_boundary.py` | intake 不得 import 計價 Port；全 `backend/` 不得硬編計價 host |
| `frontend`（`:169`） | `:186` `npm ci` | 依賴安裝 |
| | `:189` `npm run lint` | **只擋 error**（無 `--max-warnings 0`） |
| | `:198` `npm run check:types` | OpenAPI → `api.d.ts` 漂移 |
| | `:210` `npm run check:ws-types` | **WS 契約 → `ws-contract.d.ts` 漂移（新增）** |
| | `:214` `npm run build`（= `tsc -b && vite build`） | 型別檢查 ＋ 建置 |
| | `:224` Spec must not be served statically | `dist/` 內不得出現 `openapi*` 檔 |
| `backend`（`:233`） | `:250` `pip install -r requirements.txt` | 依賴安裝 |
| | `:263` import smoke（`python -c "import main; print('app:', main.app.title)"`） | 任何 import 失敗 |
| | `:280` `dump_openapi.py --check` | OpenAPI 規格漂移 |
| | `:291` `dump_ws_contract.py --check` | **WS 契約規格漂移（新增）** |
| | `:297` `python -m unittest discover -s tests -v` | 419 個測試 |
| `docker-build`（`:299`） | — | 建兩個 image，`push: false` |

> **基數更正**：`team.md` 論證用的「六道現有 CI 閘門」已不完整。新增的是四支之中的後兩支
> （`validate_cost_calculator_boundary`、`validate_pricing_lookup_boundary`）與 **WS 契約的兩端**
> （`check:ws-types` ＋ `dump_ws_contract.py --check`）。
> **`team.md` 那段「六道全綠仍放行三類缺陷」的論證，結論不一定變，但基數必須更新。**
> 而且本輪新發現的 T-14（`_progress_queue` 併發）**正是第四塊這 14 條全都碰不到的盲區**。

### `ci.yml` 的 WS 註解值得逐字傳下去 〔A〕

`[讀]` `ci.yml:200–208`（`WS contract type drift` 步驟上方）逐字說明了為何 WS 需要自己的一對閘門：

> 「WebSocket needs its own pair because FastAPI does not register websocket routes:
> `/api/collab/ws/...` is absent from `openapi.json`'s 42 paths, so the two gates above are
> **structurally blind** to it — not under-covered, but **with no assertion at all** on that
> change path (ADR-0019 / NFR5.1).」

同段另載一條本輪新發現的斷言（`BR4.4`）：**產生出的 `.d.ts` 必須保留解釋
`WorkItem.sideEffect` 兩個 sentinel 值的 JSDoc**，因為 TypeScript 會把
`"none" | "unknown" | string` 收斂成 `string`，那兩個 sentinel 的語意**在別處無處存活**。
——這對 `U2`／`U13` 是直接可用的約束。

### `deploy.yml` 〔E〕

`deploy`（self-hosted `[self-hosted, linux, x64, cloud360]`、30 分逾時、
`concurrency: deploy-10-10` 且 `cancel-in-progress: false`）→ `rollback`（20 分逾時，
還原 last-good、開 revert PR、dispatch Deploy Doctor）→ `notify`（Slack）；
部署後 `Remove the generated env file`（`if: always()`）。`[承:cloud-360@2026-09-22]`
**兩輪都未讀任何 step 的實作。**

### Agentic workflows 〔C〕

**11 支 gh-aw**（`.md` ＋ 對應 `.lock.yml`），**全部 `engine: copilot`**
`[承:cloud-360@2026-09-22]`：`code-drift-alert`、`contract-guard`、`daily-digest`、
`deploy-doctor`、`issue-triage`、`lint-fix`、`local-dev-drift`、`pr-reviewer`、
`release-watch`、`spec-sync`、`ui-regression`。`.github/workflows/` 共 33 檔。
**兩輪都未讀任何一支的內容。**

---

## 文件品質

### 模組級 docstring 偏向「寫下為什麼」，品質高於一般水準 〔B〕

本輪新增的樣板級實例（都是**本輪實讀**的）：

| 位置 | 它寫下了什麼 |
|---|---|
| `backend/scripts/dump_ws_contract.py:1–40` | 為何需要這一支而 `dump_openapi.py` 不夠；為何刻意不 import `main`（三個具體差別）；為何規格檔放 repo 根而非 `frontend/public/`（會把訊息地圖對未認證訪客公開）；為何 fail-closed 且**刻意不**以 try/except 包住契約 import |
| `backend/services/brain_router.py:1–31` | 自述是 DEMO SCOPE、不屬任何已核可單元、逐項列出做了什麼／沒做什麼／指派給哪個單元／如何移除 |
| `backend/database.py:200–217` | `_ensure_vector_extension` 為何必須早於 `create_all`、為何失敗不在此拋出 |
| `backend/services/llm_provider.py:60–63`、`:69–77` | 退役值記 ERROR、打錯字記 WARNING、兩者都不 raise；並逐字點名 RAID R-11 的機制 |
| `backend/services/review_agent.py:1–6` | 框架（LangGraph + OpenRouter）、快速路徑、串流到 SSE 的對應 |
| `backend/requirements.txt` 檔頭、`:14–22` | 為何用 `==` 而非 `~=`；`psycopg` 與 `psycopg2-binary` 是兩個不同套件；為何顯式指定 driver 之後不設版本上限 |
| `backend/Dockerfile:1–4` | LLM 路徑已全走 LangGraph + OpenRouter HTTP，**映像內無 Claude Code CLI／Node runtime** |
| `.github/workflows/ci.yml:200–208` | WS 為何需要自己一對閘門；`BR4.4` 的 JSDoc 斷言為何必要 |
| `deploy/docker-compose.deploy.yml` redis 區塊註解 | `maxmemory`／policy 為何留在 CLI 旗標而非掛載的 `redis.conf`；healthcheck 為何需要 `@connection` 而非只 `+ping` |

〔C〕既有實例：`activity.py:1–9`、`database.py:536–552`（`_apply_security_reviewer_j3a_view`
的四條契約）、`agent_router.py:10–17`（「契約（前端依賴，請勿變更）」，**本 repo docstring 深度的樣板**）。

### 文件漂移（本輪實查，兩份 store 的記載都要更新）

| 文件 | `cloud/` 或 `cloud-360/` 說 | HEAD 實況 | 等級 |
|---|---|---|---|
| `backend/Dockerfile` 檔頭 | 「仍寫 Design 由 `ClaudeSDKClient` 驅動——**過時**」`[承:cloud@2026-10-01]` | **已修正**：檔頭逐字「no Claude Code CLI / Node runtime in the image」`[讀]` | A |
| `llm_provider.py` 檔頭 | 「寫『Every LLM feature … claude-agent-sdk』——**過時**」`[承:cloud@2026-10-01]` | **已重寫**：`:8` 的提及改為歷史敘述（「(before 2026-10-01) the LLM features ran through `claude-agent-sdk`…」）`[讀]` | A |
| `llm_limits.py:52` | — | docstring 仍提 `"CLI subprocesses"`，**措辭已過時**（無子行程了）`[算:link1]` | A |
| `ci.yml`（註解） | `cloud-360/` 記「`:204` 寫 36 paths, 29 schemas，實測 42／32」 | 註解現在 **`:216`**，逐字仍為「(36 paths, 29 schemas)」；**實測為 42 paths／39 schemas** `[讀]`＋`[跑]` | A |
| `main.py:62` | — | 註解寫「移除下面**兩行**」但 `:63` 之後只有一行 `include_router`；第二處是 `:7` 的 import `[讀]` | A |
| `LOCAL-DEV.md` | link 1 列為「是否已隨 `.env.example` 的 `LLM_PROVIDER` 變更同步」待查 | **已同步** `[讀]`：`:38–39` 標 `cli` 為「已退役（2026-10-02，RAID R-11）」、`:219–223` 逐字提醒「舊的 `backend/.env.example` 預設值就是 `cli`，若你的 `.env` 是在 2026-10-01 之前複製的，把那一行改成 openrouter」、`:81` 寫「映像與 A3 不再需要 Node／claude CLI」、`:23`／`:78` 把 Redis 列為硬依賴 | A |
| `DEPLOY.md` | link 1 列為「與 `schema_rbac.sql` 的階層三表是否已同步」待查 | **已同步** `[讀]` `:224`、`:303–419`（含三表說明、`psql` 驗證指令、回復程序） | A |

> **兩條 blocking 規則本輪都已被遵守。** `project.md` 要求「異動 schema／seed 時同步
> `schema_rbac.sql` ＋ `DEPLOY.md`」與「異動 `.env.example` 時同步 `LOCAL-DEV.md`」
> ——階層三表與 `LLM_PROVIDER` 退役這兩次變更都做到了。這是值得記下的正面事實，不只是沒違規。

---

## 技術債清單

### T-1 `schema_rbac.sql` 無法作為既有環境的遷移手段（結構性）〔B〕

只在空 data volume 上執行（`deploy/docker-compose.deploy.yml:21–22` 的註解逐字說明）；
**裸的 `DELETE FROM role_permissions;` 在 `:443`** `[跑]`（`cloud-360/` 記的 L319 已位移），
檔頭逐字警告「`role_permissions` 會 DELETE 後重播預設（Admin UI 調過請先備份）」
`[承:cloud-360@2026-09-22]`——對既有 staging 重跑會抹掉管理者的人工調整。
線上演進路徑是 `database.py` 的 **7 支** `_ensure_*` 補丁（`:85–96` `[讀]`）。
**但階層三表走了第三條路**（獨立的 `run_hierarchy_migration.py`，見 T-17），
所以「唯一的線上演進路徑」這句話在 HEAD 上已不精確。

### T-2 `_ensure_*` 補丁全部吞掉失敗 〔B〕

形狀為 `except Exception as e: logger.warning(...)`，補丁失敗只留一行 warning，應用照常啟動。
**本輪重新定位行號** `[算]`：`database.py` 共 12 處 `except Exception`，在
`:192`、`:228`、`:257`、`:304`、`:374`、`:402`、`:406`、`:421`、`:430`、`:556`、`:582`、`:654`；
其中 `:193` 是 `logger.error`，`:229` 的註解逐字「**不靜默**：留下可搜尋的 warning。
真正的阻斷由 `create_all()` 承擔」。
> `cloud-360/` 記的 `:204–209`／`:251–256`／`:321–326`／`:493–500`／`:519–526` **行號已全部位移**。

`_ensure_last_activity_schema` 的 docstring 自己寫明了代價 `[承:cloud-360@2026-09-22]`：
「不補則 staging 上每個已認證的請求都會失敗，而 **CI 全綠**——測試以 in-memory SQLite
直接建表、從不經過本流程」。**這句話是本 repo「CI 全綠不等於沒問題」最精準的既有自述。**

### T-3 單行程假設散佈在多處狀態容器（多 worker 才壞）〔B〕

見 `architecture.md` 約束四的表。這些目前成立**只因為** `backend/Dockerfile` 的 `CMD` 無 `--workers`。
任何多 worker／多副本化會同時打破它們；最具體的症狀是同一個 estimate set 的 SSE 連線
落在沒有該 job 進度的行程上，畫面停在 `progress` 永不 `completed`。

> **T-3 與 T-14 是兩件事，不要合併。** T-3 是「水平擴充時會壞」；
> T-14 是「**單一行程內兩個並行請求就會壞**」。

### T-4 兩個 OpenRouter 入口，base URL 與預設模型名稱各兩份物化 〔A／B〕

**框架已改**：技術棧已統一（`claude_agent_sdk` 全樹零 import，見 T-19），
剩下的分歧**不是框架，是設定值**——`llm_provider.py:49` 的
`https://openrouter.ai/api`（Anthropic 相容）vs `langgraph_runtime.py:16` 的
`https://openrouter.ai/api/v1`（OpenAI 相容）；預設模型名稱在 `llm_provider.py:52–54`
與 `langgraph_runtime.py:17` 各一份。**無任何測試鎖住兩者一致** `[讀:link1]`。
這正是 `team.md`「單一真實來源」規則關切的形狀。

### T-5 `advice_stream_router.py:83` 使用未 import 的 `Any` 〔A，本輪複驗仍在〕

`[讀]` `:9` 只 `from typing import AsyncIterator`，但 `:83` 寫
`last_progress_key: tuple[Any, ...] | None = None`。目前不炸是因為 `:3` 有
`from __future__ import annotations`（PEP 526 的區域變數註解本就不求值）。
**移除那行 future import 即為 `NameError`**，而 backend 沒有任何 type checker 會提前發現。
**T-13 的具體後果。**

### T-6 `ci.yml` 的 OpenAPI 規模註解與事實不符（且已更偏離）〔A〕

註解現在在 **`:216`**，逐字寫「The OpenAPI spec is a complete API map (36 paths, 29 schemas)」；
**本輪實測為 42 paths、39 schemas** `[跑]`。不影響該 step 行為，
但它是既有文件已對不上現況的實例，**且偏離量比 `cloud-360@2026-09-22` 當時記的（42／32）更大**。

### T-7 `role_permissions` 的 seed 有兩條語意不同的路徑 〔C〕

`ensure_role_permissions_seeded(db, force=False)` 在表**非空時整段 no-op**（`rbac.py:63–65`）
——改了 `DEFAULT_ROLE_PERMISSIONS` 對既有環境不生效。補救是
`ensure_missing_role_permissions(db)`（只 INSERT 缺失的 `(role, story_id)`，不 UPDATE／DELETE），
在 `database.py:168–172` 被呼叫。**任何新增 story id 必須走後者。**
此外 `database.py:536–597` 的 `_apply_security_reviewer_j3a_view` 是針對**單一列**的目標式補丁，
用四態日誌代替測試——docstring 自述「部署後人工核對是本變更唯一的驗證方式」。
`[承:cloud-360@2026-09-22]`（本輪只複驗 seed 列數為 308 `[跑]`）

### T-8 權限清單多份物化，無一致性測試 〔C〕

正本 `rbac.py:23–35` 的 `CANONICAL_ROLES`（11 角色，本輪 `[跑]` 複驗數量）；
副本 1 為 `auth.py:108–112` 的 11 個手寫字串 allowlist；
副本 2 為 `schema_rbac.sql` 的 308 列 INSERT（與 `rbac_seed_data.py` 的
`DEFAULT_ROLE_PERMISSIONS` 互為兩份，本輪 `[跑]` 複驗後者為 308 列）；
副本 3 為 `user_router.py::ROLE_DISPLAY_NAMES`；
副本 4 為 `frontend/src/pages/AdminPage.tsx::AVAILABLE_ROLES`（`team.md` 記已與正本順序漂移）。
`rbac_seed_data.py` 檔頭自述「由 `schema_rbac.sql` 產生（勿手改；改 SQL 後重跑產生腳本）」，
而**該產生腳本不在 `scripts/` 內**——本輪 `[跑]` 複驗 `scripts/` 的 10 支 `.py` 清單，
確認**仍無**該產生腳本。**此宣稱目前無對應檔案。**

### T-9 `user_router.py` 與 `collab_router.py` 無 service 層 〔A〕

**892 行與 593 行**（本輪 `[算]` `wc -l`；`team.md` 記的 831／527 已過時），商業邏輯直寫 handler。
此為既成事實而非待修違規；兩支目前**無 HTTP 層測試保護**，故抽 service 層是獨立任務，
前置條件是先有端點測試。

### T-10 `openapi.json` 涵蓋不到 WebSocket——但 WS 不再是零閘門 〔A，整段改寫〕

**仍然成立的部分** `[跑]`：兩條 WS（`/api/collab/ws/{workspace_id}`、`/api/brain/ws`）
都不在 `openapi.json` 的 42 個 path 內，故 `dump_openapi.py --check` 與
`npm run check:types` **對 WebSocket 完全無效**。

**已不成立的部分**：`cloud-360/` 據此論證「本 intent 規劃的新 WebSocket **一道契約閘門都不過**
——新 REST 端點要過兩道，新 WS 過零道」`[承:cloud-360@2026-09-22]`。
**那在 HEAD 上不正確**：另有獨立的 WS 契約鏈（`brain_ws_contract.py` → `ws-contract.json`
→ `ws-contract.d.ts`）與**兩道 CI 閘門**（`ci.yml:291`／`:210`），
加上 `test_dump_ws_contract.py`／`test_ws_contract.py` 兩支測試。

**剩下的真實缺口** `[跑]` `grep -c "collab" ws-contract.json` → **0**：
**`ws-contract.json` 只涵蓋大腦，不涵蓋既有的共編 WS。**
即新債是「既有那條 WS 仍零契約」，而不是「WS 一律零契約」。
完整說明在 `architecture.md` 約束二。

### T-11 WebSocket 可能靜默停止更新 `users.last_activity_at` 〔B〕

`collab_router.py:257` 呼叫 `get_user_from_token(..., record=False)`，跳過
`auth.py:80–83` 的 `record_activity` `[承:cloud-360@2026-09-22]`。若以 WS 為主要互動通道
且照抄此形狀，**「最後活動時間」這個既有能力會對該通道的使用者無聲失效**
——沒有錯誤訊息、沒有紅燈。另：token 放在 query string 會進 nginx／cloudflared 的 access log
（對應 ADR-0006 的 audit logging 與 network exposure）。

**本輪更新** 〔A〕：大腦的 demo gateway **兩個都避開了**（token 走 `Sec-WebSocket-Protocol`、
`record=True`）`[讀]` `brain_router.py:1–31`。但 demo gateway 會被 `U13` 整支取代，
而 `collab_router` 那條**仍是舊形狀**——**此債未解，只是新的那條暫時沒有踩到。**

### T-12 獨立 schema 零前例且在現有測試基礎設施上不可驗證 〔B〕

全樹無 `CREATE SCHEMA`、無 `search_path`、無 `__table_args__ = {"schema": ...}`
`[承:cloud-360@2026-09-22]`；測試走 in-memory SQLite（`tests/helpers.py`，本輪 `[讀]` 複驗仍是
SQLite，只是驅動樁已改為 `psycopg` v3 條件式），而 **SQLite 沒有 PostgreSQL 的 schema 概念**。
這是下游必須正面處理的**驗證缺口**，不是實作細節。

### T-13 backend 無 linter／formatter／type checker、無 lockfile 〔A〕

`[跑:link1]` 六個設定檔全部不存在；`[跑]` `requirements.txt` 18 項中 14 項未 pin 且無 lockfile。
**CI／Docker build／staging 部署三處各自解析當下最新版，可能彼此不同。**
T-5 正是此缺口的具體後果。
**本 intent 要新增 MCP 套件與 `redis` 客戶端，會把這個缺口的曝光面擴大。**

### T-14 `design_agent._progress_queue` 的併發缺陷——**單一行程內兩個請求就會壞**〔A，新增〕

**這是本輪最嚴重的新發現。** 完整的逐行證據、兩種危害、兩個生產呼叫點、
`thread_id` 為何不是解法、以及 **repo 內已有的正解**（`advice_orchestrator.py:22–26,61–82`）
都寫在 `architecture.md` 約束四。摘要：

- `design_agent.py:31`／`:32` 的 `_progress_queue`／`_last_xml` 是**模組層單槽全域**；
  工具端（`:81–102` 的 4 處寫入）與入口端（`:203`／`:211` 的讀取）**都解析當下的模組全域**。
- **危害一**：兩個重疊請求 → **使用者 A 收到使用者 B 產生的架構圖 XML**。
  不是「看不到進度」，是**跨使用者內容錯送**。
- **危害二**：先結束者在 `:218` 的 `finally` 把全域設成 `None` → 另一個請求的寫入全部撞上
  `if ... is not None:` 守衛 → **沒有例外、沒有 log、沒有任何痕跡**，
  `progress`／`xml`／`error` 三類一律消失（**`error` 也在內**）。
- **`ci.yml` 的 14 條步驟沒有任何一條能抓到它**——它需要並行請求才顯現，而測試是序列的。
  這是 `team.md` 記載的「三塊結構性盲區」之外的**第四塊**。
- 登錄為上游約束 `C-R3`，是能力 1 與能力 8 的實作前置條件。

**附帶**：`wa_collab_orchestrator.py:79` 呼叫 `run_design_agent` **未傳 `thread_id`**
→ 落回預設 `"default-thread"`，即 **A4 共編路徑的所有使用者共用同一個 LangGraph
checkpointer thread** `[讀:link1]`。這是同一支模組的第二個隔離缺口（機制不同）。

**`_last_xml` 的外部可觀察後果本輪未實測**（需找出讀取端）〔E〕，但**結構與
`_progress_queue` 完全同型**。列為待查。

### T-15 production 路徑上有一支不屬於任何工作單元的 demo 程式 〔A，新增〕

`backend/services/brain_router.py`（455 LOC）已 `include_router` 進 `main.py:63`，
即**它在任何部署裡都是可達的 HTTP 表面**（`/api/brain/ws`），而它的 docstring 逐字自述
「DEMO SCOPE，**不屬於任何已核可的 AI-DLC 工作單元**」`[讀]`。

**為什麼這是債而不只是中性事實**：

1. **它用行程內 dict 做 session**，重啟即失憶——若有人在 staging 上實際用它，
   行為會是不可解釋的間歇性失憶。
2. **它的 `_classify` 是關鍵詞計分，不是信心值模型**——而 `OQ-10` 質疑的正是
  「路由層能不能產出可比較的信心值」。**把它當成雛形會讓那個開放問題看起來已被回答。**
3. **它不受 WS 契約的兩道閘門約束**（閘門管的是 `brain_ws_contract.py` 的型別定義與衍生檔），
   所以它的訊息形狀可以與契約漂移而 CI 不紅。
4. 移除它要動**兩處**（`main.py:7` 的 import ＋ `:63` 的 `include_router`），
   而註解寫「下面兩行」會讓人只找 `:63` 之後。

**正確處置是 `U13` 落地時整支取代**（docstring 自述的替代方式），不是逐段改寫。

### T-16 基礎設施已佈建但應用零消費（Redis／Ollama／pgvector）〔A，新增〕

commit `7ce1bee`（2026-09-27）把 `redis:8-alpine`、`ollama/ollama:latest` 加進部署堆疊、
把 `db` 升為 `pgvector/pgvector:pg18`、讓 `render-env.sh` 寫 `REDIS_URL`／`OLLAMA_*`、
在兩份 `.env.example` 列出它們、並在 `LOCAL-DEV.md` 記為硬依賴。

**但** `[跑]`：`backend/requirements.txt` **無 `redis` 套件**；
backend 應用程式碼對 `redis`／`REDIS_URL`／`OLLAMA_*` **零 import**
（唯一命中是 `backend/tests/test_render_env_redis.py`，那是**部署設定的契約測試**，不是客戶端）；
`database.py:199–231` 的 `_ensure_vector_extension` 已建好 pgvector 擴充，
但**全樹尚無任何 `vector` 欄位**（該函式 docstring 自述真正的大聲失敗留給 `U5` 落地之後）。

**為什麼這是債**：三個服務在每次部署都會起來、佔資源、進 healthcheck、要維護憑證
（`REDIS_PASSWORD` 是真憑證），而**沒有任何功能在用它們**。
它同時是一個**誤讀風險**：下一個人看到 compose 裡有 redis 就會以為 session 持久化已實作。

**它也是一個正面事實**：`U10` 的起點是「接線」而非「建服務」，
env contract 的 blocking 工作**已完成**。
**不要照 `cloud-360/` 約束八的原文去重做一遍「加第 5 個服務」。**

### T-17 階層三表有三條互不相同的 DDL 真相源 〔A，新增〕

`projects`／`systems`／`diagram_change_records` 的 DDL 同時存在於：

1. `schema_rbac.sql:327`／`:349`／`:393`（**只在空 volume 上執行**）`[跑]`
2. `hierarchy_migration.py:269` 的 `_ensure_hierarchy_schema(db)`（既有環境的路徑）`[算]`
3. **而 `backend/models.py` 完全沒有它們** `[跑]`（13 個 `__tablename__` 不含三表）
   ——所以 `Base.metadata.create_all` 不會建它們，ORM 也查不到它們。

**後果**：任何 router／service 要讀這三表，得先決定是補 ORM model 還是走 raw SQL；
兩者都要處理「測試走 in-memory SQLite」這一層。另：`diagram_change_records`
**本輪只寫不讀**（`DEPLOY.md:310` 逐字），保存期 90 天，
**而清除機制尚未落地——這張表實際上不會被清除**（同處逐字）。
`project.md` 禁止以 repo 內程式承載無人值守排程，**故承載形式本身是個待決設計問題，不是待寫的程式。**

### T-18 ADR-0006 的 PBT hard constraint 有一處實際缺口 〔A，新增〕

ADR-0017 §1–§2 把 PBT hard constraint 由 `cost_calculator` 移錨到**估價表解析器**，
而 `[跑:link1]` `validate_cost_calculator_boundary.py` 確認那個純函式層的實際範圍是三支：
`estimate_parser.py`、`estimate_readers.py`、`estimate_validator.py`。

**本輪逐支核對 `@given` 覆蓋** `[跑]`：

| 純函式模組 | 專屬測試檔 | `@given` 數 |
|---|---|---|
| `estimate_parser.py` | `test_estimate_parser.py` | **2** ✅ |
| `estimate_validator.py` | `test_estimate_validator.py` | **1** ✅ |
| **`estimate_readers.py`** | **不存在** | **0** ❌ |

`estimate_readers.py`（**384 LOC**，三支中最大的一支）**沒有專屬測試檔**；
它只被 `test_estimate_parser.py` 間接 import `[跑]` `grep -rln "estimate_readers" backend/tests/`。

**指派落點（2026-10-02T00:11:46Z 由 intent `260920-orchestration-brain` 的 reverse-engineering 關卡定案）**

使用者裁決：**納入該 intent 範圍，指派 `tcms-test-cases`**（已查 `.claude/tools/data/stage-graph.json`：
`execution: ALWAYS`、`phase: construction`，故**不需轉移目標**）。

**為什麼要有指派而不是只記在本清單裡**：`project.md` 逐字寫「純函式層由 `cost_calculator`
改錨至估價表解析器，ADR-0006 的 PBT hard constraint 隨之移轉——**不是豁免**」。所以這不是
「還沒寫測試」而是**一條 hard constraint 目前處於違反狀態**。而本檔的技術債清單沒有任何
機制會讓下游非讀不可——只有寫在有 execution 值的 stage 指派上才會被接到。

`tcms-test-cases` 的規則本身即要求為「待自動化」桶**實際寫出腳本並做突變驗證**
（把修正改回錯的行為、確認紅燈、還原複驗），這正好是這個缺口需要的形狀。

**本輪未做的部分，如實記載**：缺口的**成因**未查（`estimate_readers.py` 是哪個 intent／
分支落地、當時為何未補測試）。使用者在裁決時選擇直接納入而非先查成因，故本輪不追。


**這是 hard constraint 的實際違反，不是記載落差。** `project.md` 逐字要求
「下列核心模組的測試必須包含 property-based 測試，不得只有 example-based」，
而 ADR-0017 把落點移到解析器三支。**第三支目前既無 PBT 也無專屬的 example-based 測試。**
（link 1 把這一項列為待查；本輪已查證，結論是缺口真實存在。）

### T-19 `LLM_PROVIDER=cli` 的退役是一次修復，但範本的歷史預設值仍是陷阱 〔A，新增〕

**修掉的是什麼**（`llm_provider.py` 重寫，237 → 178 行）：

| 環節 | 本輪查證 | 結論 |
|---|---|---|
| 舊 cli 模式會刪四個環境變數 | `[讀:link1]` `:10–14` 的 docstring 自述（舊程式已不在檔內） | **僅文件自述**，無法以現碼複驗 |
| 遷移後無子行程 | `[跑:link1]` `grep -rn "create_subprocess_exec\|Popen\|subprocess" backend/` | **零個實際呼叫**；5 處命中全是 docstring／註解字串。**查證成立** |
| `design_agent.py` 直接讀那些變數 | `[讀:link1]` `:118–119` | 逐字為 `os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("OPENROUTER_API_KEY") or ""`。**成立** |
| 空金鑰如何表現 | `[讀:link1]` `:118` 的 `or ""` 兜底 | 金鑰為空字串仍把 `ChatAnthropic` 建起來（`:121`），失敗落在呼叫時。**機制成立** |

**失敗模式是「健康檢查說 ready，呼叫時才空金鑰」**，即**靜默失敗**，登錄為 RAID R-11。

**測試是這次修正的規格**（`test_llm_provider.py`，222 行／23 個 test）`[算:link1]`。
新增的 `RetiredCliMode` 類別（`:88`）五個測試名稱**逐字值得引用**：
`test_resolves_to_openrouter`（`:91`）、`test_logs_at_error_not_as_a_typo`（`:95`）、
`test_no_longer_deletes_credentials`（`:105`）、`test_auth_ready_no_longer_lies`（`:122`）、
`test_alias_model_family_survives`（`:129`）。

**仍是陷阱的部分** 〔A〕：`backend/.env.example:18` 的註解逐字承認
**本檔原本的預設值就是 `cli`** `[算:link1]`，故凡在 2026-10-01 之前照範本複製 `.env` 的人
都會撞上。`LOCAL-DEV.md:219–223` **已寫下這個提醒**（本輪 `[讀]` 確認），
但它靠的是人去讀文件，不是機制。

### 前一版保留債（未重驗）〔D〕

`cloud@2026-10-01` 另記：部署缺 Playwright 瀏覽器二進位、cost 跨模組私有函式、
雙層價目快取、`C1b` 死種子、slot 死碼、rollback job 權限提升（`contents: write` ＋
`pull-requests: write` ＋ `actions: write`）未經評估可否縮窄。
**本輪皆未重驗**，不得視為已解決或已確認。

---

## 值得保護的既有紀律（不是債）

### 零 TODO／FIXME／HACK／XXX 標記 〔A，本輪複驗仍成立〕

`[跑]` `grep -rn "TODO\|FIXME\|HACK\|XXX" backend/services backend/cost backend/*.py frontend/src scripts deploy`
→ **僅 1 命中**，且那一處是 `scripts/validate_env_contract.py:82` 把 `"TODO"`
**當成偵測用的佔位字串樣式**（與 `"your_openrouter_api_key_here"`、`"changeme"`、
`"<your-token>"` 並列）——**它是偵測器本身，不是技術債**。
**零標記紀律是真的，不是假陽性，後續規範不應弱化它。**

### 註解承載決策理由 〔A〕

見「文件品質」。本輪新增的樣板級實例有 9 處，其中 `dump_ws_contract.py:1–40` 與
`brain_router.py:1–31` 的深度**高於** `agent_router.py:10–17`
（`cloud-360/` 原本指定的樣板）。新模組建議沿用這兩支的深度。

### CI 已有 AST／字串層級的 import 邊界 validator 〔A〕

`validate_cost_calculator_boundary.py`（AST 遞移追 import）與
`validate_pricing_lookup_boundary.py`（掃全 `backend/` 的字串）把「純函式層不得碰 IO」
與「計價只能走 Port」這兩條設計規則變成**可機械判定的閘門**，是本 repo 少見的
「規則有承載機制」的實例。兩者本輪實跑皆 exit 0 `[跑:link1]`。
大腦在 `backend/` 內新增模組時須先確認不會誤觸（第二支掃全 `backend/`）。

### WS 契約鏈的三項設計決定 〔A，新增〕

`dump_ws_contract.py:1–40` 的 docstring 把三件事寫成可檢驗的理由而非偏好：
**刻意不 import `main`**（閘門紅燈只代表契約漂移，且不需要 DB 樁）、
**規格檔刻意放 repo 根**（放 `frontend/public/` 等於把訊息地圖對未認證訪客公開，
連帶禁止把它 import 進前端程式碼）、**fail-closed 且刻意不以 try/except 包住契約 import**
（`construction.md` 的 `## Error Handling` 逐字禁止吞例外後回報「無漂移」的形狀）。
**這是「把規則寫進會失敗的程式」的好例子，不是只寫進文件。**

### 遷移有終檢斷言 〔A，新增〕

`hierarchy_migration.py:477` 的 `_assert_no_unassigned_diagrams(db)` 讓一次性遷移
**自己驗證自己的後置條件**，而且斷言的是一條編號 AC（`AC9.1.4`）。
`[跑:link1]` 測試輸出印出遷移計數與「終檢通過」。
`DEPLOY.md:303–419` 另附 `psql` 驗證指令與完整回復程序。
**這是本 repo 第一個這個形狀的遷移，應作為後續資料遷移的樣板。**

### 兩條 blocking 同步規則本輪都被遵守 〔A，新增〕

階層三表 → `schema_rbac.sql` ＋ `DEPLOY.md` 已同步；
`LLM_PROVIDER` 退役 → `.env.example` ＋ `LOCAL-DEV.md` 已同步。
**規則被遵守本身是值得記下的事實**，否則 codekb 只會累積違規清單而看不到紀律在生效。

---

## 安全基線（ADR-0006 四面向，本輪逐項狀態）

> ADR-0006 是 hard constraint，四個面向**缺一不可**。本表只記 codekb 觀察到的現況，
> **不是對本 intent 變更的合規判定**（那屬各 stage 的產出義務）。

| 面向 | 本輪觀察 | 等級 |
|---|---|---|
| **IAM／授權** | 授權全掛 FastAPI dependency 層，service 層無第二道檢查 → **同進程直呼會完整繞過 RBAC**（`architecture.md` 約束十一）。權限清單多份物化無一致性測試（T-8）。`collab_router` 的 WS 不用 `Depends`、自建 Session | B／C |
| **Encryption** | `REDIS_PASSWORD` 為真憑證且由 `render-env.sh` 產生；`render-env.sh:59–69` 拒絕含 `$` 的值（compose 內插會無聲截斷，使 DB 以遠弱於預期的密碼運行）。**本輪未查 TLS／at-rest 加密現況** | B／E |
| **Network exposure** | compose 檔頭 `:4` 逐字「Only nginx is reachable from outside. backend, db, redis and ollama have no ...」`[讀]`——**redis 與 ollama 皆無 `ports:`**。WS 的 token 在 query string 會進 access log（T-11）。`ws-contract.json` 刻意不放 `frontend/public/` 以免訊息地圖外洩 | A |
| **Audit logging** | `[跑:link1]` 測試輸出顯示權限稽核 log 實際運作（`INFO:cloud360.user_router:【權限稽核】User Privilege Re-assignment \| ...`）。`users.last_activity_at` 有 5 分鐘節流，但 WS 路徑可能繞過（T-11）。`diagram_change_records` 是新的稽核表但**只寫不讀且不會被清除**（T-17） | A／B |

### Secret 掃描的作用域小於規則所宣稱 〔D〕

`validate_no_obvious_secrets()`（`scripts/validate_repo_contract.py`）只讀 `contract_files()`
（repo 層必要檔 ＋ baseline record 必要檔 ＋ audit shard）——`backend/`、`frontend/`、`deploy/`、
`schema_rbac.sql`、任何 `.env.example` **都不在其中**。
`[承:cloud@2026-10-01]`／`[承:cloud-360@2026-09-22]`，**本輪未複驗**。
這不是「缺工具」，是既有機制的實際作用域小於規則所宣稱。

---

## 本 intent 相關的測試底線（`team.md` 的 A／B／C 三規則在 HEAD 的可行性）

| 規則 | 前置條件現況 | 等級 |
|---|---|---|
| **A — 授權矩陣變更需 allow/deny 雙向測試** | 可行。`test_rbac.py` 形狀已存在；`CANONICAL_ROLES` 11 角色、seed 308 列皆可直接引用 | A |
| **B — 新增或修改 HTTP 端點需 `TestClient` 測試** | 可行且**已有 6 支先例**（`team.md` 記的「唯一使用例」已過時）。`[跑:link1]` 測試輸出顯示 `TestClient` 確實在用（`INFO:httpx:HTTP Request: GET http://testserver/api/auth/list "HTTP/1.1 200 OK"` 等）。**但 `team.md` 的理由句要改**：`fastapi[standard]` extra 已不在（現為 `fastapi==0.111.0`），而 `httpx` 仍獨立宣告，而 `httpx` 才是 `starlette.testclient` 的實際前置——**結論仍成立、理由要改寫** | A |
| **C — 前端資料形狀變更需 e2e 斷言** | 可行但唯一的自動化層仍是 Playwright 2 支 spec；**前端無 unit／component 測試框架**（本輪複驗仍成立）。`BrainPage.tsx` 403 LOC **無任何 e2e 覆蓋**（本輪未讀 spec 內容，但 `/brain` 是新路由） | B |
| **WebSocket 的測試落點** | **`TestClient` 支援 `websocket_connect`，而 repo 內已有 WS 契約測試兩支**（`test_ws_contract.py`、`test_dump_ws_contract.py`，兩者含 `@given`）。但**本輪未讀其內容**，不確定它們測的是型別定義還是連線行為 | E |
