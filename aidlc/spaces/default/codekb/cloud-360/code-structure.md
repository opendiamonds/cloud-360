# Code Structure — Cloud-360

> 逆向工程產出。基準 commit `c3de2c8`（branch `danniel/fix/production-path-check-noop`，2026-08-17）。
> 本檔描述程式碼「放在哪、怎麼分類、寫成什麼形狀」。元件職責見 `component-inventory.md`。

## 倉庫頂層結構

```
cloud-360/
├── backend/              FastAPI 應用（單一 process monolith）
├── frontend/             Vite + React SPA
├── scripts/              驗證與同步腳本（4 支）
├── deploy/               staging 部署資產（compose、render-env.sh、cloudflared）
├── .github/              CI/CD 與 11 組 gh-aw agentic workflows
├── .claude/              AIDLC v2 upstream 框架（非應用程式碼，升級時整批覆蓋）
├── aidlc/                AIDLC 工作區（memory、knowledge、codekb、intents）
├── openapi.json          OpenAPI 3.1.0 規格（2,709 行）— 跨語言契約鏈的中樞
├── schema.sql            精簡核心 DDL 參考（78 行，已落後）
├── schema_rbac.sql       宣稱的完整部署腳本（531 行）
├── docker-compose.yml    本機開發（postgres 15 + adminer）
├── DEPLOY.md             部署手冊（450 行）
├── LOCAL-DEV.md          本機開發（361 行）— 唯一記載兩個隱性硬依賴之處
├── TESTING.md            測試案例格式的唯一真實來源（242 行）
├── CLAUDE.md             AI agent 專案指引
├── AGENTS.md             其他 harness 的入口
└── README.md
```

**`openapi.json` 的地位**：它不是產物殘留，而是**建置期契約鏈的中樞**
（後端 → 規格 → 前端型別），且兩端各有 CI gate。見 `architecture.md` 的「型別契約鏈」。
CI 另有一道檢查確保它**不會被靜態服務出去**（`find dist -name 'openapi*'` 非空即 fail）。

## Backend 模組組織

`backend/` 共 **8,775 LOC 產品碼 + 3,199 LOC 測試**（git-tracked），Python 3.12。

```
backend/
├── main.py                  55 LOC   entry point：app 建立、CORS、掛 5 router、startup
├── models.py               175 LOC   SQLAlchemy declarative Base，7 實體 + 1 association table
├── database.py             366 LOC   engine／SessionLocal／get_db；init_db；4 支啟動期 schema 補丁
├── Dockerfile                        python:3.12-slim + Node 22 + 全域 Claude Code CLI
├── requirements.txt                  12 條依賴（2 條精確釘選）
├── services/                         22 支模組（全部業務邏輯）
├── scripts/dump_openapi.py  90 LOC   由程式碼 dump OpenAPI 規格；--check 供 CI 比對
├── lenses/                           3 個 JSON 資料資產（AWS／GCP／Azure）
├── prompts/                          6 個資料資產（3 system prompt + 3 draw.io 模板）
└── tests/                            21 測試檔 + helpers.py + __init__.py
```

### `backend/services/` 的四種模組類型

22 支模組可依「與外界的耦合程度」分成四類。這個分類直接對應可測試性：

**類型 A — Router（HTTP 邊界層，5 支）**

| 檔案 | LOC | 掛載前綴 |
|---|---|---|
| `user_router.py` | 884 | `/api/auth` |
| `collab_router.py` | 527 | `/api/collab` |
| `review_router.py` | 484 | `/api/architecture` |
| `agent_router.py` | 186 | `/api/architecture` |
| `lens_router.py` | 108 | `/api/architecture` |

**類型 B — 編排器與服務（讀寫 DB 或跨行程，7 支）**：`wa_collab_orchestrator.py`(551)、
`review_orchestrator.py`(510)、`rbac.py`(272)、`llm_provider.py`(223)、`lens_service.py`(203)、
`wa_score_service.py`(104)、`auth.py`(91)

**類型 C — 純函式引擎（不讀 DB、不連外，7 支）**：`diagram_builder.py`(1,818，
**全 repo 最大模組**，唯一例外是可選的 n8n webhook 呼叫)、`wa_rule_engine.py`(973)、
`wa_lens_engine.py`(556)、`collab_suggestions.py`(147)、`activity.py`(104，純判定函式
加一支寫入器)、`llm_limits.py`(64)、`prompt_guard.py`(63)

**類型 D — LLM agent 與資料常數（3 支）**：`design_agent.py`(328)、`review_agent.py`(174)
（皆跨行程邊界）、`rbac_seed_data.py`(315，純資料常數)

**結構意涵**：類型 C 是最容易測試也實際被 property-based 測試涵蓋的部分。
本輪新增的三支模組（`activity`、`prompt_guard`、`llm_provider`）**全部落在 C 或 B**，
沒有一支新增到 router 內 —— 這與 `team.md` 記載的「新業務邏輯走三層形狀」一致。

### 分層一致性不是全域的

分層在不同模組家族有**不同的成熟度**：

| 家族 | 分層形狀 | 評價 |
|---|---|---|
| `review` / `lens` / `wa_*` | router → orchestrator/service → 純函式引擎 → model | 乾淨，三層清楚 |
| `agent` | router → prompt_guard → agent → 引擎 | 薄 router（186 LOC），職責只有 SSE 轉換與前置檢查 |
| `user` | router 直接寫商業邏輯 → model | **無 service 層**，884 LOC 全在 handler |
| `collab` | router 直接寫商業邏輯 + WebSocket 狀態 → model | **無 service 層** |

**既有規則（`team.md`）對此的分流**：新模組／新業務邏輯一律走三層形狀；
修改 `user_router.py`／`collab_router.py` 就地沿用既有形狀，不趁機夾帶 service 層抽取
（前置條件是先有端點測試）；不得在這兩支之外新建「router 直寫商業邏輯」的模組。

## Frontend 模組組織

`frontend/src/` 共 **10,539 LOC TS/TSX**（40 個 git-tracked 檔），TypeScript 6 + React 19。

```
frontend/
├── src/
│   ├── App.tsx              132 LOC  路由表與 guard 組合
│   ├── types/api.d.ts     2,385 LOC  由 openapi.json 產生（勿手改）
│   ├── pages/               8 支頁面
│   ├── components/         12 支元件
│   ├── context/             2 支（AuthContext.tsx 142 + auth-context.ts 63）
│   ├── config/api.ts         34 LOC  API_BASE_URL／WS_BASE_URL／apiUrl()／wsUrl()
│   ├── hooks/               1 支：useCollaboration.ts（64 LOC，WebSocket）
│   ├── utils/               6 支工具（877 LOC）
│   └── lib/plainText.ts      20 LOC
├── scripts/check-api-types.mjs        型別漂移 gate（CI）
├── tests/e2e/               1 個檔：regression.spec.ts（490 LOC）
├── Dockerfile               多階段：node:22-alpine build → nginx:alpine
├── nginx.conf               /api/ 反向代理 + WS upgrade + SPA fallback
├── package.json             + package-lock.json（已 commit）
├── vite.config.ts           僅掛 @vitejs/plugin-react
├── tsconfig.json            project references 三分檔（+ .app.json／.node.json）
├── eslint.config.js         flat config
├── tailwind.config.js       ⚠️ 死碼 — Tailwind v4 下未被載入，實際生效的是 src/index.css 的 @theme
├── postcss.config.js
└── playwright.config.ts     testDir ./tests/e2e
```

### 頁面清單與規模

| 頁面 | LOC | 對應 story |
|---|---|---|
| `AssessmentPage.tsx` | **1,861（全前端最大檔）** | `A3` |
| `WorkspacePage.tsx` | **1,193** | `A1`／`A2`／`A4` |
| `RolePermissionsPage.tsx` | 427 | `J3b` |
| `AdminPage.tsx` | 426 | `J3a` |
| `LoginPage.tsx` | 289 | 公開 |
| `AuthorizationRequestsPage.tsx` | 202 | `J3a` |
| `WaitingApprovalPage.tsx` | 120 | pending 使用者 |
| `ForbiddenPage.tsx` | 35 | 403 落點 |

### 元件清單（12 支）

| 元件 | LOC | 備註 |
|---|---|---|
| `LensCriteriaEditor.tsx` | 473 | |
| `ChatBox.tsx` | 385 | |
| `DrawioCanvas.tsx` | 343 | |
| `Sidebar.tsx` | 285 | |
| `SuggestionRichText.tsx` | 210 | |
| `PaginationControl.tsx` | 138 | **本輪新增**（使用者清單分頁） |
| `ShareModal.tsx` | 136 | |
| `LastActivityCell.tsx` | 73 | **本輪新增**（最後活動時間 + 逾期標示） |
| `NavChromeContext.tsx` | 68 | |
| `RouteGuard.tsx` | 62 | `ProtectedRoute` + `CapabilityRoute` |
| `DiagramPreviewPanel.tsx` | 53 | |
| `Layout.tsx` | 21 | |

## 程式碼模式

### 後端模式

**模式 1 — Guard 工廠（Dependency Injection）**

授權一律以工廠函式產生 FastAPI `Depends`：

- `require_story_action("A3", "edit")` — 指定 story 與 action
- `require_arch_action("edit")` — 架構圖三合一（`A1`／`A2`／`A4`）專用捷徑

工廠內部的判定順序固定為：`authorization_status` 閘門 → canonical role 檢查 →
查 `role_permissions`。**新端點一律沿用此模式**，不要自寫檢查。

**模式 2 — Async Generator 串流**

SSE 端點的形狀高度一致：

```python
async def event_generator():
    async for event in <orchestrator或agent>(...):
        chunk = json.dumps(event, ensure_ascii=False)
        yield f"data: {chunk}\n\n"
return StreamingResponse(event_generator(), media_type="text/event-stream")
```

事件一律是 `{"type": ..., ...}` 的 dict，`ensure_ascii=False`（中文不轉義）。
編排器本身也是 async generator，逐事件 yield —— 這讓「降級」得以自然表達：
逾時時改 yield 一個不同 type 的事件，而不是拋例外中斷串流。

**事件 type 一律是字面字串**（本次實測：全 `services/` 無變數化的 `"type": <var>` 寫法）。
這對可讀性有利，但也意味著**前後端的事件名一致性只能靠人工比對** —— 已實測出一個雙向皆死的
契約（`unsupported`），詳見 `architecture.md`。

**模式 3 — 啟動時的 Runtime DDL 補丁**

`database.py` 有**四個** `_ensure_*_schema()`（a4／j5／a3／last_activity）加一支
`_apply_security_reviewer_j3a_view()`，在 `init_db()` 內於 `Base.metadata.create_all()`
之後依序執行，用 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` 等可重跑寫法補上 `.sql` 檔
沒有的欄位。**這不是 migration 工具**（無 Alembic、無版本表、無 down 路徑），
是冪等的 DDL 補丁函式，每次啟動全跑一遍。

自行管理交易邊界：`_apply_security_reviewer_j3a_view` 的 docstring 明寫
「不提交則寫入被靜默丟棄」。

**模式 4 — Fallback 而非失敗（且必須留下訊號）**

外部依賴失敗一律降級：圖示 SVG 取不到用灰底、LLM 逾時落 `rules_only` 狀態、
DB 無 lens 資料回退到 `backend/lenses/` 的 JSON。

**降級必須記 log** 是本輪確立的形狀：`fetch_icon_from_n8n()` 的每條降級路徑
（非 200、查無對應、無 SVG 內容、解析失敗、請求失敗）都有 `logger.warning`，
原始碼註解逐字寫明「這條路徑原本靜默 return，是最難查的一種降級」。
與 `construction.md` 的「Errors must be surfaced」一致。

**模式 5 — 政策常數與純判定函式分離**

新模組一致採用「模組層常數 + 純函式判定 + 薄寫入器」的形狀：

```python
ACTIVITY_WRITE_THROTTLE = timedelta(minutes=5)   # 政策
OVERDUE_THRESHOLD = timedelta(days=90)           # 政策
def should_record_activity(...) -> bool: ...     # 純判定，可直接測
def is_overdue(...) -> bool: ...                 # 純判定，可直接測
def record_activity(db, user, now=None) -> bool: # 唯一碰 DB 的函式
```

`llm_limits.py`、`prompt_guard.py` 亦循此形狀。**新增政策性行為時沿用此分離**，
它是這些模組能有 property-based 測試的直接原因。

**模式 6 — 高密度模組級 docstring**

25 支後端模組中 **22 支有模組級 docstring**（缺 `main.py`、`database.py`、`auth.py`），
多數明確載明「職責／安全邊界／契約」三段。深度最完整的樣板是：

- `agent_router.py` —— 含「契約（前端依賴，請勿變更）」段並列出 request/response 形狀
- `llm_provider.py` —— 40+ 行，逐項解釋為何 `cli` 模式必須 **delete** 而非清空環境變數

**修改這些模組時應同步維護 docstring 內的契約描述。** 新模組沿用
`agent_router.py` 的樣板深度。

**模式 7 — 腳本註解解釋「為什麼」**

`check-api-types.mjs`、`dump_openapi.py`、`requirements.txt` 檔頭、`ci.yml` 步驟註解都寫明
「這道檢查在防什麼、為何別的檢查防不住」。例如 `requirements.txt` 檔頭解釋為何
`fastapi`／`pydantic` 用 `==` 而非 `~=`（相容釋出形式仍會在次版本線上浮動，選錯等於沒釘）。
**這是本 repo 的顯著正面特徵，應保護。**

### 前端模式

**模式 1 — `fetch()` 直呼，URL 組裝集中、其餘未集中**

**52 處 `fetch()` 呼叫點，分布於 10 個檔**：`AssessmentPage`(16)、`WorkspacePage`(13)、
`RolePermissionsPage`(4)、`AdminPage`(4)、`LensCriteriaEditor`(4)、
`AuthorizationRequestsPage`(3)、`ShareModal`(3)、`WaitingApprovalPage`(2)、`LoginPage`(2)、
`AuthContext`(1)。

- **已集中**：URL 組裝走 `config/api.ts` 的 `apiUrl()` / `wsUrl()`，52 處一致沿用。
- **未集中**：認證標頭（手寫 `Authorization: Bearer`）、401 處理、錯誤解包（`data.detail`）、回應型別。

**新增呼叫點時沿用現有形狀**（`apiUrl()` + 手寫 header + `res.ok` 判斷 + `data.detail` 取錯誤
訊息），不要單點自創抽象。

**模式 2 — 型別有兩種形狀，取決於檔案**

| 形狀 | 檔案 | 說明 |
|---|---|---|
| **產生型別**（新形狀） | `AdminPage.tsx` **僅此一支** | `import type { components } from '../types/api'`，再 `type DbUser = components['schemas']['UserSchema']`。原始碼註解寫明「手寫的本地 interface 與後端回應形狀之間沒有任何編譯期連結」 |
| **手寫 interface**（舊形狀） | 其餘 9 支做 `fetch()` 的檔 | 與後端 `response_model` 無編譯期連結 |

**新增或修改資料形狀時，優先採用產生型別**：基礎設施（產生器、兩道 CI gate）已就位，
邊際成本低。

**模式 3 — Context 拆兩檔（被 lint 規則強制）**

`AuthContext.tsx`（Provider component）與 `auth-context.ts`（型別 + `useAuth` hook）
必須分檔，因為 `react-refresh/only-export-components` 要求單一 component 匯出。

**模式 4 — 資料抓取拆兩層（被 lint 規則強制）**

`react-hooks/set-state-in-effect`（error 級）使 `AdminPage` 的抓取被迫拆成：

- `fetchUserList` — 純抓取，**不碰任何 state**，回傳資料
- `fetchUsers` — 呼叫端，在 `.then/.catch/.finally` 內更新 state
- `useEffect` 內另用 `cancelled` flag 防止卸載後 setState

**新增資料來源必須沿用此形狀，否則 CI lint 紅燈。**

**模式 5 — 不可就地修改物件（被 lint 規則強制）**

`react-hooks/immutability`（error 級）：state 更新一律回傳新物件
（現例 `setUsers((prev) => prev.map(...))`）。

**模式 6 — 兩層 Route Guard**

`ProtectedRoute`（登入與否）與 `CapabilityRoute storyId=... action=...`（能力）
組合使用；`DefaultRedirect` 依序試 pending → `canArch('view')` → `A3` → `J3a` → `J3b` → `/403`。

## 命名與檔案分類慣例

| 慣例 | 規則 | 例外／備註 |
|---|---|---|
| Python 檔名 | `snake_case.py` | 一致 |
| Python router | 一律 `*_router.py` | 5 支全部符合 |
| Python 引擎 | Well-Architected 相關一律 `wa_*` 前綴 | `wa_rule_engine`／`wa_lens_engine`／`wa_score_service`／`wa_collab_orchestrator` |
| React 元件與頁面 | `PascalCase.tsx` | 一致（12 元件 + 8 頁面全部符合） |
| React 頁面 | 一律 `*Page.tsx` | 8 支全部符合 |
| 非元件 TS | hook 檔 `use*.ts`，其餘 camelCase | `auth-context.ts` 為既存 kebab-case 例外，不強制改名 |
| 測試檔 | `test_*.py`（backend）／`*.spec.ts`（frontend） | 一致 |
| logger 命名 | 新模組一律 `logging.getLogger("cloud360.<module>")` | 已知不一致：部分模組仍用 `__name__` |
| `HTTPException` 呼叫風格 | 已知不一致（具名 vs 位置引數混用） | 不強制統一；新程式碼沿用所在函式鄰近寫法 |
| 註解與 docstring 語言 | 繁體中文為主 | 與 ADR-0009 一致 |

## `scripts/` 目錄（4 支，1,595 LOC）

| 腳本 | LOC | 職責 | CI 中執行？ |
|---|---|---|---|
| `tcms_sync.py` | 515 | 手動案例（`--file`，建立＋更新）／自動化案例（`--spec`，只更新）同步進 Kiwi TCMS | ✗ 人工（`/tcms-verify` 流程） |
| `validate_repo_contract.py` | 405 | REQUIRED_FILES／REQUIRED_TEXT、record 層 baseline、文件語言、禁止路徑、禁止內容 | ✓ `repo-contract` job |
| `tcms_validate.py` | 360 | 四類機械檢查：必填欄位、空洞預期結果、追溯目標存在、API/UI 比對 `openapi.json` 與 `App.tsx` | ✗ 人工（`/tcms-verify` gate） |
| `validate_env_contract.py` | 315 | 三環境設定分離與完整性（六項檢查） | ✓ `repo-contract` job |

**跨分支註記**：ADR-0012 的 `aidlc_sync_push.py`／`aidlc_sync_pull.py`／
`aidlc_sync_buglist.py` **實作已完成但在 PR #508 待合併**，不在本基準分支上。
合併後本目錄將由 4 支增為 7 支。詳見 `reverse-engineering-timestamp.md`。

## 結構性風險

1. **三個超大檔**：`diagram_builder.py`(1,818)、`AssessmentPage.tsx`(1,861)、
   `WorkspacePage.tsx`(1,193)，加上 `wa_rule_engine.py`(973) 與 `user_router.py`(884)。
   **性質不同**：`diagram_builder` 與 `wa_rule_engine` 大但高內聚（單一演算法，純函式，
   有測試保護），是可接受的；`user_router` 大且低內聚（缺 service 層），是最值得拆的，
   但前置條件是先有端點測試；兩個前端頁面是完整功能 UI，拆分收益需權衡。
   **`diagram_builder` 由 288 成長為 1,818 LOC（六倍）**，值得在下次變更時檢視內部分層。
2. **同一份資料的手寫副本**：角色清單正本 `rbac.py::CANONICAL_ROLES`，
   副本在 `auth.py::require_any_user`、`user_router.py::ROLE_DISPLAY_NAMES`、
   `AdminPage.tsx::AVAILABLE_ROLES`（已與正本順序漂移）、`schema_rbac.sql` seed。
   密碼雜湊正本 `auth.py::get_password_hash`，副本 `database.py::hash_password`（逐字相同）。
   **彼此無同步機制。**
3. **Python 側零靜態檢查**：無 linter、formatter、type checker 設定檔。前端有 ESLint + `tsc`
   且 CI 強制，後端完全沒有對等物。
4. **`tailwind.config.js` 是死碼**：Tailwind v4 下未被任何 `@config` 指令載入，
   實際生效的是 `src/index.css` 的 `@theme`。檔案仍存在會誤導讀者以為它是設定來源。
   **引用 Tailwind 尺度前要先確認哪一份設定真的生效。**
5. **無 monorepo 工具**：無 workspace／turborepo／nx／Makefile。前後端各自建置，由 CI 分 job
   執行。**唯一的跨側一致性機制是 `openapi.json` 契約鏈**，而它目前只覆蓋 1/10 的前端呼叫檔。
