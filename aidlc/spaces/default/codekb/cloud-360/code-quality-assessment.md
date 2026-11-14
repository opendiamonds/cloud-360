# Code Quality Assessment — Cloud-360

> **基準**：`dc4b687`（2026-09-22）。證據標記慣例見 `business-overview.md` 檔頭。
>
> ⚠️ **本輪未以任何測試、lint 或 CI validator 的執行結果作為本 codekb 的事實來源**（唯一的例外是寫檔後跑過一次 `validate_repo_contract.py` 做落檔安全檢查，那不是對程式碼品質的判斷）。
> 未跑 `python -m unittest`、未跑 `npm run lint`、未跑 `scripts/validate_env_contract.py`／
> `validate_cost_calculator_boundary.py`／`validate_pricing_lookup_boundary.py`、未啟動任何 compose stack。
> 本檔的所有測試與品質數字皆為**靜態計數**，**不是執行結果**。
> 任何「通過／全綠／紅燈」的判斷都必須自行重跑後才能下。

## 測試現況（全為靜態計數 `[算]`）

| 面向 | 數字 | 對既有記載的更正 |
|---|---|---|
| backend 測試檔 | **37 支** `test_*.py` | `team.md` 的「21 支」已過時 |
| `@given`（property-based） | **17 處，分佈 10 支檔** | `team.md` 的「13 處／7 支」已過時 |
| `TestClient` 使用 | **6 支測試檔 ＋ `helpers.py`** | `team.md` 的「唯一使用例是 `test_user_list_endpoint`」已過時 |
| frontend e2e | **2 支 spec**（`regression.spec.ts` 490 行、`estimate-workspace.spec.ts` 57 行） | — |
| 覆蓋率量測 | **完全不存在** | 沿用（仍成立） |

**PBT 落點的 10 支檔** `[算]`：`test_estimate_parser`、`test_collab`、`test_activity`、
`test_auth`、`test_diagram_builder`、`test_diagram_icons`、`test_design_agent`、
`test_wa_rule_engine`、`test_estimate_validator`、`test_repo_contract_production_paths`。

**`TestClient` 的 6 支檔** `[算]`：`test_auth`、`test_estimate_intake_api`、
`test_user_list_endpoint`、`test_me_endpoint`、`test_cost_advice_agent`、
`test_legacy_cost_retirement`。

### 測試框架與基礎設施

- Backend：Python 內建 `unittest`（CI 指令 `python -m unittest discover -s tests -v`
  `[讀]` `ci.yml:266`）＋ `hypothesis` ＋ `unittest.mock`。**未使用 pytest** `[算]`。
- Frontend：Playwright，單一 `chromium` project、`retries: process.env.CI ? 1 : 0`
  `[讀]` `playwright.config.ts:17,32–33`。**前端無 unit／component 測試框架** `[算]`。
- **測試 DB 策略**：`backend/tests/helpers.py` 在任何 DB import 前
  `sys.modules.setdefault("psycopg2", MagicMock())`，改走 **in-memory SQLite** `[簽]`。

> **本輪未讀任何一支測試檔的內容** `[未驗]`。上述皆為檔名清單與 grep 統計。

### 覆蓋率門檻的定位（誠實記載）

`org.md` 宣告「最低 80% line coverage」。實際狀態 `[算]`：全樹無 `.coveragerc`、
無 `pyproject.toml`、無 `setup.cfg`，`requirements.txt` 無 `coverage`／`pytest-cov`，
`ci.yml` 無任何 coverage step。**此門檻目前既無法量測也無法強制，是宣告而非閘門。**
不在本檔弱化 `org.md` 的原文，只如實記載承載機制缺席。

## Lint、格式與型別檢查

| 面向 | Frontend | Backend |
|---|---|---|
| Linter | ESLint 10 flat config `[讀]`；CI 跑 `npm run lint` = `eslint .`，**未加 `--max-warnings 0`**，故只擋 error `[讀]` `package.json`、`ci.yml:188–189` | **完全沒有** `[算]` |
| Formatter | **無**（repo 根無 `.prettierrc`——`org.md` 預設的 Prettier 從未被引入，非「引入後又拿掉」）`[算]` | **無**（無 Black）`[算]` |
| Type checker | `tsc -b`（隨 `npm run build`）`[讀]` | **無**（無 mypy／pyright）`[算]` |

**本輪未執行 lint**，故不重述任何 error／warning 基準 `[未驗]`。

> **`tsc -b` 的既知盲區**：前端存在手寫本地 interface 的形狀（例如
> `const data = await res.json(); return data;` 把 `any` 直接放行），與後端
> Pydantic schema 無編譯期連結。OpenAPI 漂移閘門縮窄了此缺口但**未歸零**
> ——`api.d.ts` 只在被實際採用的呼叫點才起作用。本輪未複驗採用率 `[未驗]`。

## CI/CD

### `ci.yml`（5 個 job）`[讀]`

`gate`（偵測 `[aidlc-sync]` 回寫，命中則 skip 其餘四者）
→ `repo-contract`、`frontend`、`backend`、`docker-build`（四者平行、皆 `needs: gate`）。

| Job | 步驟 |
|---|---|
| `repo-contract` | **4 支 validator**：`validate_repo_contract.py`、`validate_env_contract.py`、`validate_cost_calculator_boundary.py`、`validate_pricing_lookup_boundary.py` |
| `frontend` | `npm run lint`、`npm run check:types`（API 型別漂移）、`npm run build`（含 `tsc -b`）、`dist/` 不得含 openapi 規格檔 |
| `backend` | import smoke、`dump_openapi.py --check`（規格漂移）、`unittest discover` |
| `docker-build` | 建兩個 image，`push: false` |

> **更正**：後兩支 validator 為新增，`team.md` 的「六道閘門」描述已不完整；
> 現為 **5 個 job／11 個檢查步驟** `[算]`。

### `deploy.yml`（3 個 job）`[未驗，僅讀骨架]`

`deploy`（self-hosted `[self-hosted, linux, x64, cloud360]`、30 分逾時、
`concurrency: deploy-10-10` 且 `cancel-in-progress: false`）
→ `rollback`（20 分逾時，還原 last-good、開 revert PR、dispatch Deploy Doctor）
→ `notify`（Slack）。部署後 `Remove the generated env file`（`if: always()`）。
**本輪未讀任何 step 的實作。**

### Agentic workflows

**11 支 gh-aw**（`.md` ＋ 對應 `.lock.yml`），**全部 `engine: copilot`** `[算]`：
`code-drift-alert`、`contract-guard`、`daily-digest`、`deploy-doctor`、`issue-triage`、
`lint-fix`、`local-dev-drift`、`pr-reviewer`、`release-watch`、`spec-sync`、`ui-regression`。
`.github/workflows/` 共 **33 檔** `[算]`。**本輪未讀任何一支 gh-aw `.md` 的內容。**

## 文件品質

- repo 根有 `README.md`、`CLAUDE.md`、`AGENTS.md`、`DEPLOY.md`、`LOCAL-DEV.md`、`TESTING.md`。
- **模組級 docstring 品質高於一般水準且偏向「寫下為什麼」** `[讀]`。實例：
  `llm_provider.py:1–37`（37 行檔頭說明兩種 provider 的非對稱互斥）、`activity.py:1–9`、
  `database.py:536–552`（`_apply_security_reviewer_j3a_view` 的四條契約）、
  `agent_router.py:10–17`（「契約（前端依賴，請勿變更）」）。
- **設定檔註解同樣承載決策理由** `[讀]`：`ci.yml:32–44` 說明為何不把 `github.actor`
  放進 concurrency group；`requirements.txt:1–7` 說明為何用 `==` 而非 `~=`。

## 技術債清單

### T-1 `schema_rbac.sql` 無法作為既有環境的遷移手段（結構性）`[讀]`

只在空 data volume 上執行（`deploy/docker-compose.deploy.yml:21–23` 的註解逐字說明）；
L319 有裸的 `DELETE FROM role_permissions;`，檔頭 L18 逐字警告
「role_permissions 會 DELETE 後重播預設（Admin UI 調過請先備份）」——
對既有 staging 重跑會抹掉管理者的人工調整。唯一的線上演進路徑是
`database.py` 的 6 支 `_ensure_*` 補丁（`:78–83`）。

### T-2 `_ensure_*` 補丁全部吞掉失敗 `[讀]`

五處的形狀都是 `except Exception as e: logger.warning(...)`
（`database.py:204–209`、`:251–256`、`:321–326`、`:493–500`、`:519–526`），
補丁失敗只留一行 warning，應用照常啟動。`_ensure_last_activity_schema` 的 docstring
（`:504–510`）自己寫明了代價：「不補則 staging 上每個已認證的請求都會失敗，而 CI 全綠
——測試以 in-memory SQLite 直接建表、從不經過本流程」。

### T-3 單行程假設散佈在三處狀態容器 `[讀]`

見 `architecture.md` 約束四。三者目前成立**只因為** `backend/Dockerfile:36` 沒有
`--workers`。任何多 worker／多副本化會同時打破三者；最具體的症狀是
同一個 estimate set 的 SSE 連線落在沒有該 job 進度的行程上，畫面停在 `progress` 永不 `completed`。

### T-4 兩套 LLM 客戶端棧並存，預設模型名稱兩份物化 `[讀]`

見 `dependencies.md`。無任何測試鎖住兩者一致。

### T-5 `advice_stream_router.py:83` 使用未 import 的 `Any` `[讀]`

`:9` 只 `from typing import AsyncIterator`，但 `:83` 寫
`last_progress_key: tuple[Any, ...] | None = None`。目前不炸是因為 `:3` 有
`from __future__ import annotations`（PEP 526 的區域變數註解本就不求值）。
**移除那行 future import 即為 `NameError`**，而 backend 沒有任何 type checker 會提前發現。

### T-6 `ci.yml:204` 的註解與事實不符 `[算]`

註解逐字寫「The OpenAPI spec is a complete API map (36 paths, 29 schemas)」，
實測為 **42 paths、32 schemas**。不影響該 step 行為，但它是既有文件已對不上現況的實例。

### T-7 `role_permissions` 的 seed 有兩條語意不同的路徑 `[讀]`

`ensure_role_permissions_seeded(db, force=False)` 在表**非空時整段 no-op**（`rbac.py:63–65`）
——改了 `DEFAULT_ROLE_PERMISSIONS` 對既有環境不生效。補救是
`ensure_missing_role_permissions(db)`（只 INSERT 缺失的 `(role, story_id)`，不 UPDATE／DELETE），
在 `database.py:168–172` 被呼叫。**任何新增 story id 必須走後者。**
此外 `database.py:536–597` 的 `_apply_security_reviewer_j3a_view` 是針對**單一列**的
目標式補丁，用四態日誌代替測試——docstring 自述「部署後人工核對是本變更唯一的驗證方式」。

### T-8 權限清單三份物化，無一致性測試 `[讀]`

見 `dependencies.md`「依賴面的已知風險」第 3 項，含「產生腳本不在 `scripts/` 內」這一點。

### T-9 `user_router.py` 與 `collab_router.py` 無 service 層 `[算]`

892 行與 593 行（`team.md` 記的 831／527 已過時），商業邏輯直寫 handler。
此為既成事實而非待修違規；兩支目前**無 HTTP 層測試保護**，故抽 service 層是獨立任務，
前置條件是先有端點測試。

### T-10 `openapi.json` 涵蓋不到 WebSocket（**本輪標為新風險**）`[算]`

`/api/collab/ws/{workspace_id}` 存在於程式但不在 42 個 path 內。
**`dump_openapi.py --check` 與 `npm run check:types` 兩道漂移閘門對 WebSocket 完全無效。**
本 intent 規劃的新 WebSocket 因此**一道契約閘門都不過**——新 REST 端點要過兩道，新 WS 過零道。

### T-11 WebSocket 靜默停止更新 `users.last_activity_at`（**本輪標為新風險**）`[讀]`

`collab_router.py:257` 呼叫 `get_user_from_token(..., record=False)`，跳過
`auth.py:80–83` 的 `record_activity`。若大腦以 WS 為主要互動通道，
**「最後活動時間」這個既有能力會對大腦使用者無聲失效**——沒有錯誤訊息、沒有紅燈。
另：token 放在 query string 會進 nginx／cloudflared 的 access log
（對應 ADR-0006 的 audit logging 與 network exposure）。

### T-12 獨立 schema 零前例且在現有測試基礎設施上不可驗證（**本輪標為新風險**）`[算]`

全樹無 `CREATE SCHEMA`、無 `search_path`、無 `__table_args__ = {"schema": ...}`；
測試走 in-memory SQLite（`tests/helpers.py`），而 **SQLite 沒有 PostgreSQL 的 schema 概念**。
本 intent 的「同一資料庫、獨立 schema」因此既無前例也無測試路徑。
這是下游必須正面處理的**驗證缺口**，不是實作細節。

### T-13 backend 無 linter／formatter／type checker、無 lockfile `[算]`

見 `technology-stack.md`「工具鏈現況」。T-5 正是此缺口的具體後果。

## 值得保護的既有紀律（不是債）

### 零 TODO／FIXME／HACK／XXX 標記 `[算]`

`grep -rn "TODO\|FIXME\|HACK\|XXX" backend/services backend/cost backend/*.py frontend/src scripts deploy`
**僅 1 命中**，且那一處是 `scripts/validate_env_contract.py:82` 把 `"TODO"`
**當成偵測用的佔位字串樣式**——它是偵測器本身，不是技術債。
**零標記紀律是真的，不是假陽性，後續規範不應弱化它。**

### 註解承載決策理由

見「文件品質」。`agent_router.py:10–17` 的「契約」段是本 repo docstring 深度的樣板，
新模組建議沿用同等深度。

### CI 已有兩支 AST／字串層級的 import 邊界 validator

`validate_cost_calculator_boundary.py` 與 `validate_pricing_lookup_boundary.py`
把「純函式層不得碰 IO」這條設計規則變成可機械判定的閘門，是本 repo 少見的
「規則有承載機制」的實例。大腦在 `backend/` 內新增模組時須先確認不會誤觸（見 `dependencies.md`）。
