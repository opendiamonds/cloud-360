# Code Structure — Cloud-360

> **基準**：`34aeef3`（2026-10-02）。**新鮮度等級與證據標記的定義在 `reverse-engineering-timestamp.md`**。
> **本檔所有計數與 LOC 皆為本輪實算** `[跑]`（Python 走訪檔案樹 ＋ 逐檔行數），
> 不沿用任何 store 的舊數字。散文慣例段落由兩份 store 合併。

---

## 倉庫頂層結構 〔B〕

| 路徑 | 內容 | 本輪深度 |
|---|---|---|
| `backend/` | FastAPI 單體 | 部分深讀（見下） |
| `frontend/` | Vite ＋ React SPA | **僅計數與路由表**；零元件內容 |
| `deploy/` | staging compose、env 產生器、Cloudflare tunnel（**5 檔** `[跑]`） | 區塊結構與 image 行 `[讀]`；其餘未讀 |
| `scripts/` | repo 層工具（**10 支 `.py`** `[跑]`） | 僅檔名；2 支 validator 的檔頭承自 `cloud-360` |
| `.github/workflows/` | **34 檔** `[跑]`（`ci.yml`、`deploy.yml`、11 組 gh-aw `.md`＋`.lock.yml`、aidlc-sync） | 僅 `ci.yml` 的 job／step 骨架 |
| `.claude/`、`aidlc/` | AI-DLC 框架殼與工作區 | **非應用程式碼，兩輪皆不掃描** |
| repo 根 | `schema.sql`、`schema_rbac.sql`、`openapi.json`、**`ws-contract.json`（新增）**、`docker-compose.yml`、`README.md`、`CLAUDE.md`、`AGENTS.md`、`DEPLOY.md`、`LOCAL-DEV.md`、`TESTING.md` | `openapi.json` 全解析；其餘部分 |

### 程式碼規模（本輪實算）〔A〕

| 範圍 | 檔數 | LOC |
|---|---|---|
| `backend/` 全部 `.py`（排除 `__pycache__`） | **103** | **25,023** |
| 其中非測試 | **55** | **16,849** |
| `frontend/src/` 全部檔案 | **57** | **14,645** |
| 其中自動產生的型別檔 | 2（`api.d.ts` **2,921** ＋ `ws-contract.d.ts` **470**） | **3,391** |

**最大單檔**：`backend/services/diagram_builder.py` **2,080 行**（repo 最大）、
`frontend/src/pages/AssessmentPage.tsx` **1,861 行**。

> **數字更正（對 `cloud-360@2026-09-22`）**：它記「backend Python 共 19,542 行
> （43 支非測試模組 ＋ 37 支測試）」、「frontend `src/` ＋ `tests/` 共 13,578 行
> （含 2,823 行 `api.d.ts`）」、最大單檔 `diagram_builder.py` 1,818 行
> `[承:cloud-360@2026-09-22]`——**全部已過時**。
> `api.d.ts` 由 2,823 → **2,921** 行，且**多了一個產生檔 `ws-contract.d.ts`（470 行）**。

---

## Backend 模組組織 〔B〕

```
backend/
├── main.py              # 67   FastAPI app、CORS、startup → init_db、8 個 include_router  [讀]
├── env_bootstrap.py     # 36   強制由 backend/.env 載入環境，不看行程 cwd                [簽]
├── models.py            # 348  13 個 ORM 模型 + 1 association table（diagram_shares）    [算]
├── database.py          # 656  engine / SessionLocal / get_db / init_db / 7 支 _ensure_*  [部分讀]
├── test_agent.py        # 62   手動 smoke 腳本（非 tests/ 內，非生產路徑）               [簽]
├── requirements.txt     #      18 項宣告                                                 [讀]
├── Dockerfile           #      31 行；python:3.12-slim，無 Node／無 claude CLI           [讀]
├── .env.example         #      含 LLM_PROVIDER / OPENROUTER / REDIS_* / OLLAMA_*         [部分讀]
├── services/            # 26 支 .py   10,936 LOC                                         [算]
├── cost/                # 21 支 .py    4,266 LOC                                         [算]
├── tests/               # 46 支 test_*.py + helpers.py + __init__.py                      [算]
├── scripts/             #  3 支：dump_openapi.py / dump_ws_contract.py /
│                        #         run_hierarchy_migration.py                              [算]
├── prompts/             #  .md system prompts                                   [未開啟]
└── lenses/              #  .yaml lens 定義                                      [未開啟]
```

> **`backend/services/` 由 23 支增為 26 支** 〔A〕 `[跑]`（`cloud-360/` 記 23）。
> 新增的三支是 **`brain_router.py`（455）、`brain_ws_contract.py`（783）、
> `hierarchy_migration.py`（496）**。
> **`backend/scripts/` 由 1 支增為 3 支**：新增 `dump_ws_contract.py`、`run_hierarchy_migration.py`。
> **`backend/tests/` 由 37 支增為 46 支 `test_*.py`。**
> `backend/` 為 flat module（無頂層 `__init__.py`）`[承:cloud@2026-10-01]`。

### `backend/services/` 的 26 支（LOC 全為本輪實算）〔A／B〕

| 類型 | 模組（LOC） | 本輪深度 |
|---|---|---|
| **HTTP／WS 邊界** | `user_router`(892)、`collab_router`(593)、`review_router`(484)、`agent_router`(186)、`lens_router`(108)、**`brain_router`(455)** | `agent_router` `:115–135` `[讀]`；`user_router` `:80–92` `[讀]`；`brain_router` docstring ＋ 骨架 `[讀]`／`[算]`；其餘 `[算]` |
| **授權與身分** | `rbac`(302)、`rbac_seed_data`(317)、`auth`(112)、`activity`(104) | 〔C〕承 `cloud-360`；本輪只以 import 複驗規模（11 角色／308 列） |
| **LLM 與編排** | `wa_collab_orchestrator`(563)、`review_orchestrator`(510)、`review_agent`(205)、`design_agent`(218)、`llm_provider`(178)、`langgraph_runtime`(165)、`llm_limits`(64)、`prompt_guard`(63) | `design_agent` ＋ `llm_provider` **全檔** `[讀]`；`review_agent` `:1–12`、`langgraph_runtime` `:1–25`、`wa_collab_orchestrator` `:70–90` `[讀]`；其餘 `[算]` |
| **純函式引擎（PBT 落點）** | `diagram_builder`(2080)、`wa_rule_engine`(973)、`wa_lens_engine`(631) | `[算]` |
| **服務層** | `lens_service`(203)、`wa_score_service`(104)、`collab_suggestions`(147) | `[算]` |
| **WS 契約（新增）** | **`brain_ws_contract`(783)** | **`[未掃]`** ——契約本體未讀，是 `U2`／`U13` 的待查項 |
| **資料遷移（新增）** | **`hierarchy_migration`(496)** | 骨架 `[算]` |

### `backend/cost/` 的 21 支（LOC 全為本輪實算，合計 4,266）〔B〕

| 類型 | 模組（LOC） | CI 邊界強制 |
|---|---|---|
| HTTP 邊界 | `estimate_intake_router`(235)、`advice_stream_router`(179) | — |
| 業務協調 | `estimate_intake_service`(686)、`advice_orchestrator`(358)、`estimate_access`(58)、`estimate_audit`(74) | — |
| **純函式解析核心** | **`estimate_readers`(384)、`estimate_parser`(322)、`estimate_validator`(122)** | ✅ `validate_cost_calculator_boundary.py` 禁 `httpx｜requests｜sqlalchemy｜fastapi`（AST 遞移） |
| LLM agent | `cost_advice_agent`(240) | — |
| 計價 Port | `pricing_client`(287)、`sku_catalog`(265)、`pricing_gcp`(236)、`pricing_azure`(219)、`pricing_sdk`(203)、`pricing_query_parser`(120)、`workload_context`(106)、`pricing_offer_parser`(83)、`pricing_units`(47)、`config`(41) | ✅ `validate_pricing_lookup_boundary.py`（白名單 8 支 `pricing_*` ＋ `config`） |
| — | `__init__`(1) | — |
| 設定資料 | `aws_region_locations.yaml`、`pricing_coverage.yaml`、`pricing_urls.yaml`、`supported_regions.yaml` | — |

**`sku_catalog.py:18` 的 `import httpx` 不違反邊界**——它不在純函式三支之內 `[算:link1]`。

> ⚠️ **三支純函式中 `estimate_readers.py`（384 LOC，最大的一支）沒有專屬測試檔** 〔A〕 `[跑]`
> ——這是 ADR-0006 PBT hard constraint 的實際缺口，見 `code-quality-assessment.md` T-18。

### 分層成熟度不是全域的（既成事實，非待修違規）〔A／B〕

- **三層清楚的家族** `review`／`lens`／`wa_*`／`cost`：router → service／orchestrator →
  純函式引擎 → model。純函式層不讀 DB、不連外，是 PBT 的實際落點。
  **`cost` 家族的邊界有 CI 以 AST 強制**，是 repo 內唯一被機械化的分層約束。
- **router 直寫商業邏輯的家族** `user`／`collab`：**無 service 層**。
  `user_router.py` **892 行**、`collab_router.py` **593 行** `[跑]`
  （`team.md` 記的 831／527 已過時）。
- **規則依改動落點分流**（`team.md` 的既有規則）：新模組／新業務邏輯一律走三層形狀；
  修改這兩支就地沿用既有形狀，**不趁機夾帶 service 層抽取**
  （兩支無 HTTP 層測試保護，重構與功能變更混在同一個 PR 不可驗證）；
  **不得在這兩支之外新建「router 直寫商業邏輯」的模組**。
- **本輪新增的三支落在哪**：`brain_router.py` 是 demo（自認不屬任何單元，整支待取代）；
  `brain_ws_contract.py` 是純型別宣告；`hierarchy_migration.py` 是 migration ＋ schema 保障
  ——**三支都不是「router 直寫商業邏輯」的新實例**，既有規則未被違反。

---

## Frontend 模組組織 〔B〕

```
frontend/src/                   57 檔，14,645 LOC（含 3,391 行產生檔）
├── App.tsx                 160  13 條 Route、RouteGuard、Layout           [讀路由表]
├── main.tsx                 10
├── App.css / index.css     184 / 50
├── vite-env.d.ts            14
├── pages/                  10 檔  5,376 LOC                              [未讀內容]
├── components/             24 檔  4,083 LOC（12 支 + cost/ 12 支）        [未讀內容]
├── types/                   2 檔  3,391 LOC —— 兩者皆為產生檔
│                                  api.d.ts(2,921) + ws-contract.d.ts(470)
├── utils/                   6 檔    877 LOC                              [未讀內容]
├── context/                 2 檔    213 LOC  AuthContext.tsx + auth-context.ts
├── assets/                  3 檔    100 LOC
├── hooks/                   1 檔     67 LOC  useCollaboration.ts（既有唯一 WS 客戶端）
├── cost/                    2 檔     66 LOC  slotRegistry.tsx + supportedRegions.ts
├── config/                  1 檔     34 LOC  api.ts（apiUrl() / wsUrl()）
└── lib/                     1 檔     20 LOC
```

**10 支頁面（LOC 本輪實算）** `[跑]`：`AssessmentPage` 1,861、`WorkspacePage` 1,194、
`RolePermissionsPage` 499、`AdminPage` 426、**`BrainPage` 403（新增）**、`CostPage` 344、
`LoginPage` 292、`AuthorizationRequestsPage` 202、`WaitingApprovalPage` 120、`ForbiddenPage` 35。

**`components/` 12 支** `[算]`：`ChatBox`、`DiagramPreviewPanel`、`DrawioCanvas`、
`LastActivityCell`、`Layout`、`LensCriteriaEditor`、`NavChromeContext`、`PaginationControl`、
`RouteGuard`、`ShareModal`、`Sidebar`、`SuggestionRichText`。

**`components/cost/` 12 支** `[算]`：`EstimateAdvicePanel`、`EstimateCalculatorGuideModal`、
`EstimateChecksPanel`、`EstimateCloudCard`、`EstimateHistoryDrawer`、
`EstimateOfficialCalculators`、`EstimateSaveModal`、`EstimateShareModal`、
`EstimateUploadZone`、`EstimateWorkloadForm`、`types.ts`、`workloadContext.ts`。

> **數字更正**：`cloud-360/` 記「9 支頁面」「`components/cost/` 9 支」「11 條路由」
> `[承:cloud-360@2026-09-22]`——**HEAD 是 10 支頁面、12 支 cost 元件、13 條路由**。
> **`types/` 由 1 支變 2 支**（多了 `ws-contract.d.ts`，兩者都是產生檔，**不得手改**）。

---

## 程式碼模式（本輪確認仍成立的部分）

### 後端 〔B〕

- **錯誤處理**：DB／驗證錯誤直接 `raise HTTPException` 快速失敗；`try/except`
  只用在外部依賴邊界（LLM、webhook、檔案）且必須降級或記 log `[承:cloud-360@2026-09-22]`。
  **兩個記錄下來的例外**：
  (1) `database.py` 的 `_ensure_*` 補丁一律 `except Exception → logger.warning`
  （刻意的，避免補丁失敗擋住啟動；代價見 `code-quality-assessment.md` T-2）；
  (2) **`dump_ws_contract.py` 刻意不以 try/except 包住契約 import** 〔A〕
  ——docstring 逐字說明「一個把例外吞掉後回報『無漂移』的檢查腳本，它的綠燈不構成任何證據」。
  **這兩個例外方向相反，而兩者都有寫下理由——這是本 repo 的好形狀。**
- **logger 命名不一致**（既成）：多數模組用 `logging.getLogger("cloud360.<module>")`，
  少數用 `__name__`（`team.md` 記 `collab_router`、`design_agent`、`agent_router`、
  `diagram_builder` 四支）。**新模組一律 `"cloud360.<module>"` 形式。** 〔C／D〕
- **零 TODO／FIXME／HACK／XXX 標記** 〔A〕 `[跑]`：全樹 grep **僅 1 命中**，
  且那一處是 `scripts/validate_env_contract.py:82` 把 `"TODO"`
  **當成偵測用的佔位字串樣式**（與 `"your_openrouter_api_key_here"`、`"changeme"`、
  `"<your-token>"` 並列）——**它是偵測器本身，不是技術債。**
  **這條紀律是真的，應予保護。**
- **`HTTPException` 呼叫風格已知不一致**（`user_router.py` 內同檔混用具名與位置引數）
  ——記為已知不一致，**不強制統一**；新程式碼沿用所在函式鄰近寫法。〔D〕

### 前端（由 lint 規則直接決定的結構約束，違反即 CI 紅燈）〔C〕

**這三條不是團隊的美學選擇，而是 lint 規則的直接後果**（`eslint-plugin-react-hooks@7.1.1`
的 16 條 error 級規則）。升級或更換 lint 套件時本節同步重審。

- **Context 拆兩檔**（`react-refresh/only-export-components`）：Provider 元件放 `.tsx`、
  型別與 hook 放同名 `.ts`。現例 `AuthContext.tsx` ＋ `auth-context.ts`。
- **資料抓取拆兩層**（`react-hooks/set-state-in-effect`，error）：
  ① 純抓取函式（不碰 state，回傳資料）② 呼叫端在 `.then/.catch/.finally` 更新 state
  ③ `useEffect` 內用 `cancelled` flag 防卸載後 setState。
  現例 `AdminPage.tsx` 的 `fetchUserList` / `fetchUsers` / `useEffect`。
  **任何新增前端資料來源都必須沿用此形狀**——包含大腦的 WS 客戶端。
- **不可就地修改物件**（`react-hooks/immutability`，error）：state 更新一律回傳新物件。

### 前端 API 呼叫形狀 〔A／C〕

`[跑]` 本輪實算：`fetch(` 共 **62 處、分佈 15 支檔**；手寫 `Authorization: Bearer` 共 **36 處**。
（`team.md` 記的「52 處／10 支」與「40 處」皆已過時。）

URL 一律經 `src/config/api.ts` 的 `apiUrl()` / `wsUrl()`；**未集中的是認證標頭、401 處理、
錯誤解包與回應型別**。新增呼叫點時沿用現有形狀（`apiUrl()` ＋ 手寫 header ＋ `res.ok` 判斷
＋ `data.detail` 取錯誤訊息），**不要單點自創抽象**。
大腦的 WebSocket 客戶端應沿用 `wsUrl()`。

---

## 命名慣例（既成事實）〔B〕

| 對象 | 慣例 | 本輪複驗 |
|---|---|---|
| Python 檔名 | `snake_case.py`；router 一律 `*_router.py`；WA 引擎一律 `wa_*` 前綴 | ✅ 26 支逐一核對，**`brain_router.py` 遵守**；`brain_ws_contract.py`／`hierarchy_migration.py` 非 router，不適用該後綴 |
| React 元件／頁面 | `PascalCase.tsx`；頁面一律 `*Page.tsx` | ✅ **`BrainPage.tsx` 遵守** |
| 非元件 TS 檔 | hook 用 `use*.ts`，其餘 camelCase；`auth-context.ts` 為既存 kebab-case 例外 | 〔C〕 |
| 成本前端元件 | `frontend/src/components/cost/Estimate*.tsx`（10 支 ＋ `types.ts` ＋ `workloadContext.ts`） | ✅ 本輪複驗 12 支 |
| 產生的型別檔 | `frontend/src/types/*.d.ts`，**兩支都是產生檔、不得手改** | ✅ 本輪新增 `ws-contract.d.ts` 遵守同一位置慣例 |
| dump 腳本 | `backend/scripts/dump_*.py`，輸出落 repo 根 | ✅ 本輪新增 `dump_ws_contract.py` 遵守 |

---

## 建置與產物鏈 〔A〕

**兩條契約鏈，形狀相同**（詳見 `api-documentation.md`「契約同步規則」）：

| 產物 | 來源 | 工具 | CI 守門 |
|---|---|---|---|
| `openapi.json`（repo 根） | FastAPI app | `backend/scripts/dump_openapi.py` | `ci.yml:280` `--check` |
| `frontend/src/types/api.d.ts`（2,921 行） | `openapi.json` | `npm run gen:types`（`openapi-typescript@7.13.0`） | `ci.yml:198` `check:types` |
| **`ws-contract.json`（repo 根，31,012 bytes）** | **`brain_ws_contract.py`** | **`backend/scripts/dump_ws_contract.py`** | **`ci.yml:291` `--check`** |
| **`frontend/src/types/ws-contract.d.ts`（470 行）** | **`ws-contract.json`** | **`npm run gen:ws-types`** | **`ci.yml:210` `check:ws-types`** |
| backend 映像 | `backend/Dockerfile` | docker buildx | `ci.yml:299`（`push: false`） |
| frontend 映像 | `frontend/Dockerfile` | docker buildx | 同上 |
| `deploy/.env` | `deploy/render-env.sh`（**唯一產生點**） | — | `ci.yml:159` `validate_env_contract.py` |
| DB 初始 schema | `schema_rbac.sql` | postgres initdb（**僅空 volume**） | — |

**三條獨立的建置管線，無 monorepo 建置工具**（無 Nx／Turborepo／Makefile）〔C〕：
backend 走 `pip install -r requirements.txt`（**無 lockfile、無 `pyproject.toml`**）；
frontend 走 `npm ci` ＋ `npm run build`（= `tsc -b && vite build`）；
Docker 為兩支獨立 Dockerfile。

---

## 結構性風險（給本 intent）〔A〕

1. **大腦若在 `backend/` 內新增模組，必須先確認不會誤觸兩支 import 邊界 validator**
   ——特別是 `validate_pricing_lookup_boundary.py`，它**掃全 `backend/`**，
   新模組若在任何字串裡提到三個計價 host 就會紅燈（`architecture.md` 約束十）。
2. **不得在 `user_router.py`／`collab_router.py` 之外新建「router 直寫商業邏輯」的模組**；
   新功能域一律走三層形狀。
3. **大腦的前端入口已存在**（`BrainPage.tsx`，403 LOC），命名與路由慣例都已遵守；
   但**前端沒有 unit／component 測試框架**可接住重構，唯一自動化層是 Playwright 2 支 spec，
   而 `/brain` 目前**無任何 e2e 覆蓋**（本輪未讀 spec 內容，但它是新路由）。
4. **`brain_ws_contract.py` 的 783 行是本輪最大的未讀區**，而它是 `U2`／`U13` 的直接輸入。
   在它被讀過之前，任何關於「九種伺服器訊息的 payload 欄位」的設計主張都沒有來源。
5. **產生檔不得手改**：`api.d.ts`（2,921 行）與 `ws-contract.d.ts`（470 行）各有一道
   CI 漂移閘門；手改會在下次 dump 時被覆寫並讓 CI 紅燈。
   **且 `ws-contract.d.ts` 另受 `BR4.4` 約束**（必須保留
   `WorkItem.sideEffect` 兩個 sentinel 值的 JSDoc，見 `api-documentation.md`）。
6. **新增 Python 依賴（MCP 套件、`redis` 客戶端）會放大「無 lockfile」的曝光面**
   ——CI／Docker build／staging 三處各自解析當下最新版（`code-quality-assessment.md` T-13）。
