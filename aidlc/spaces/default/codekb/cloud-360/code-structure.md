# Code Structure — Cloud-360

> **基準**：`dc4b687`（2026-09-22）。深度分佈見 `reverse-engineering-timestamp.md`。
> 證據標記慣例見 `business-overview.md` 檔頭。

## 倉庫頂層結構

| 路徑 | 內容 | 本輪深度 |
|---|---|---|
| `backend/` | FastAPI 單體 | 部分深讀（見下） |
| `frontend/` | Vite ＋ React SPA | 部分深讀 |
| `deploy/` | staging compose、env 產生器、Cloudflare tunnel（5 檔） | 全部 `[讀]` |
| `scripts/` | repo 層工具（10 支 `.py`） | 2 支讀檔頭、其餘僅檔名 `[算]` |
| `.github/workflows/` | 33 檔（`ci.yml`、`deploy.yml`、11 組 gh-aw `.md`＋`.lock.yml`、aidlc-sync） | 僅 `ci.yml` 全讀 |
| `.claude/`、`aidlc/` | AI-DLC 框架殼與工作區 | **非應用程式碼，本輪不掃描** |
| repo 根 | `schema.sql`、`schema_rbac.sql`、`openapi.json`、`docker-compose.yml`、`README.md`、`CLAUDE.md`、`AGENTS.md`、`DEPLOY.md`、`LOCAL-DEV.md`、`TESTING.md` | `openapi.json`／`docker-compose.yml` 深；schema 部分 |

**程式碼規模** `[算]`（`wc -l`）：backend Python 共 **19,542 行**
（43 支非測試模組 ＋ 37 支測試）；frontend `src/` ＋ `tests/` 共 **13,578 行**
（含 2,823 行自動產生的 `src/types/api.d.ts`）。最大單檔為
`backend/services/diagram_builder.py`（1,818 行）與
`frontend/src/pages/AssessmentPage.tsx`（1,861 行）。

## Backend 模組組織

```
backend/
├── main.py              # FastAPI app、CORS、7 個 include_router、startup → init_db  [讀]
├── env_bootstrap.py     # 強制由 backend/.env 載入環境，不看行程 cwd              [簽]
├── models.py            # 13 個 ORM 模型 + 1 association table                     [讀]
├── database.py          # engine / SessionLocal / get_db / init_db / 6 支 _ensure_* [讀]
├── requirements.txt     # 17 項宣告                                                [讀]
├── Dockerfile           # python:3.12-slim + Node 22 + claude CLI                  [讀]
├── services/            # 23 支 .py：router、agent、引擎、RBAC、認證              [算]
├── cost/                # 21 支 .py + 4 支 .yaml：C1 估價功能域                    [算]
├── tests/               # 37 支 test_*.py + helpers.py + fixtures/                 [算]
├── scripts/             # dump_openapi.py 等                                       [簽]
├── prompts/、lenses/    # 資料資產（Markdown／JSON／drawio XML）                   [未開啟]
```

### `backend/services/` 的模組類型（23 支）

| 類型 | 模組 | 本輪深度 |
|---|---|---|
| HTTP／WS 邊界 | `agent_router`、`review_router`、`lens_router`、`user_router`、`collab_router` | `agent_router` `[讀]`；`review_router` 僅 SSE 區段 L55–115／L460–484 `[讀]`；`collab_router` 僅 WS 區段 L245–300 `[讀]`；其餘 `[簽]` |
| 授權與身分 | `auth`、`rbac`、`rbac_seed_data`、`activity` | 全部 `[讀]` |
| LLM 與編排 | `design_agent`（檔頭 L1–45 `[讀]`）、`review_agent`、`review_orchestrator`、`wa_collab_orchestrator`、`llm_provider` `[讀]`、`llm_limits`、`langgraph_runtime` `[讀]`、`prompt_guard` `[讀]` | 混合 |
| 純函式引擎（PBT 落點） | `wa_rule_engine`、`wa_lens_engine`、`diagram_builder` | `[簽]` |
| 服務層 | `lens_service`、`wa_score_service`、`collab_suggestions` | `[簽]` |

### `backend/cost/` 的模組類型（21 支 ＋ 4 支 YAML）

| 類型 | 模組 | 本輪深度 |
|---|---|---|
| HTTP 邊界 | `estimate_intake_router`、`advice_stream_router` | `[讀]` |
| 業務協調 | `estimate_intake_service`、`advice_orchestrator` `[讀]`、`estimate_access`、`estimate_audit` | 混合 |
| 純函式解析核心 | `estimate_parser`、`estimate_readers`、`estimate_validator` | `[簽]` |
| LLM agent | `cost_advice_agent` | `[讀]` |
| 計價 Port | `pricing_client`（檔頭 L1–120 `[讀]`）、`pricing_sdk`、`pricing_gcp`、`pricing_azure`、`pricing_offer_parser`、`pricing_query_parser`、`pricing_units`、`config` | 混合 |
| 設定資料 | `aws_region_locations.yaml`、`pricing_coverage.yaml`、`pricing_urls.yaml`、`supported_regions.yaml` | `[算]` 僅檔名 |

### 分層成熟度不是全域的（既成事實，非待修違規）

- `review` / `lens` / `wa_*` 家族與 `cost` 家族：router → service／orchestrator →
  純函式引擎 → model，三層清楚；純函式層不讀 DB、不連外，是 PBT 的實際落點。
- `user` / `collab` 家族：**無 service 層**，商業邏輯直寫 handler。
  `user_router.py` **892 行**、`collab_router.py` **593 行** `[算]` `wc -l`
  （`team.md` 記載的 831／527 已過時）。

## Frontend 模組組織

```
frontend/src/
├── App.tsx              # 11 條 Route、RouteGuard、Layout                    [讀]
├── config/api.ts        # apiUrl() / wsUrl() 集中 URL 組裝                   [讀]
├── context/             # AuthContext.tsx（Provider）+ auth-context.ts（型別與 hook） [讀]
├── cost/                # slotRegistry.tsx [讀]、supportedRegions.ts [簽]
├── pages/               # 9 支 *Page.tsx                                      [簽]
├── components/          # 12 支 + components/cost/ 9 支                       [簽]
├── hooks/useCollaboration.ts、utils/（6 支）、types/api.d.ts（2,823 行自動產生） [簽]
```

**9 支頁面** `[算]`：`AdminPage`、`AssessmentPage`、`AuthorizationRequestsPage`、
`CostPage`、`ForbiddenPage`、`LoginPage`、`RolePermissionsPage`、
`WaitingApprovalPage`、`WorkspacePage`。

**11 條路由** `[讀]` `App.tsx:35–135`：`/login`、`/403`、`/waiting-approval`、
`/workspace`、`/assessment`、`/cost`、`/admin/users`、
`/admin/authorization-requests`、`/admin/role-permissions`、
`/admin`（導向 `/admin/users`）、`/`、`*`。

## 程式碼模式（本輪確認仍成立的部分）

### 後端
- **錯誤處理**：DB／驗證錯誤直接 `raise HTTPException` 快速失敗；`try/except`
  只用在外部依賴邊界（LLM、webhook、檔案）且必須降級或記 log `[簽]`。
  **例外**：`database.py` 的 6 支 `_ensure_*` 補丁一律 `except Exception → logger.warning`，
  這是刻意的（避免補丁失敗擋住啟動），代價見 `code-quality-assessment.md`。
- **logger 命名不一致**（既成）：多數模組用 `logging.getLogger("cloud360.<module>")`，
  少數用 `__name__` `[簽]`。新模組沿用前者。
- **零 TODO／FIXME／HACK／XXX 標記** `[算]`：全樹 grep 僅 1 命中，且那一處是
  `scripts/validate_env_contract.py:82` 把 `"TODO"` **當成偵測用的佔位字串樣式**——
  它是偵測器本身，不是技術債。**這條零標記紀律是真的，應予保護。**

### 前端（由 lint 規則直接決定的結構約束，違反即 CI 紅燈）
- **Context 拆兩檔**（`react-refresh/only-export-components`）：Provider 放 `.tsx`、
  型別與 hook 放同名 `.ts`。現例 `AuthContext.tsx` ＋ `auth-context.ts` `[讀]`。
- **資料抓取拆兩層**（`react-hooks/set-state-in-effect`，error）：純抓取函式不碰 state →
  呼叫端在 `.then/.catch/.finally` 更新 state → `useEffect` 內用 `cancelled` flag `[簽]`。
- **不可就地修改物件**（`react-hooks/immutability`，error）：state 更新一律回傳新物件 `[簽]`。
- **API 呼叫形狀**：`fetch(` 共 **62 處、分佈 15 支檔** `[算]`；手寫
  `Authorization: Bearer` 共 **36 處** `[算]`（`team.md` 記載的「52 處／10 支」已過時）。
  URL 一律經 `apiUrl()` / `wsUrl()`；未集中的是認證標頭、401 處理、錯誤解包與回應型別。

## 命名慣例（既成事實）

| 對象 | 慣例 |
|---|---|
| Python 檔名 | `snake_case.py`；router 一律 `*_router.py`；WA 引擎一律 `wa_*` |
| React 元件／頁面 | `PascalCase.tsx`；頁面一律 `*Page.tsx` |
| 非元件 TS 檔 | hook 用 `use*.ts`，其餘 camelCase；`auth-context.ts` 為既存 kebab-case 例外 |
| 成本前端元件 | `frontend/src/components/cost/Estimate*.tsx`（8 支 ＋ `types.ts`）`[算]` |

## 結構性風險（給本 intent）

1. **大腦若放進 `backend/`**，必須先確認不會誤觸兩支 import 邊界 validator
   （前者以 AST 遞移追 import、後者掃全 `backend/` 的計價 host 字串）——見
   `architecture.md` 約束十。
2. **不得在 `user_router.py`／`collab_router.py` 之外新建「router 直寫商業邏輯」的模組**；
   新功能域一律走三層形狀。
3. 大腦的前端入口若是新頁面，須沿用 `*Page.tsx` 命名、`apiUrl()`／`wsUrl()` 組裝與
   上述三條 lint 結構約束；前端**沒有 unit／component 測試框架**可接住重構。
