# Developer Code Scan Results

> Pipeline link 1 scratchpad（architect 合成用）｜intent `260819-cost-finops`｜mode **Modify**  
> Repo `cloud` HEAD `c3de2c8`（`c3de2c8baa72120ca09e27d12dd57833446a6f5c`）｜branch `luojingting/feat/cost-estimation-finops`  
> Baseline codekb：`aidlc/spaces/default/codekb/cloud/` @ `8c90f40`（2026-08-06、intent `260806-a1-a3-ux`）  
> 掃描時刻：2026-08-19；**未修改應用程式原始碼**；**未覆寫 9 份 space-level codekb**。

本檔為 brownfield **delta scan**：先確認 baseline 仍成立的部分，再深掃舊 codekb 未涵蓋的 C1（TCO）面。識別字、路徑、API、表名維持 English。

---

## Developer Code Scan Results

### Packages Found

- `backend/` — application — Python — FastAPI API（認證／RBAC、agent 產圖、collab 圖庫、WA review／lens）
- `frontend/` — application — TypeScript / React — SPA（Workspace A1、Assessment A3、Admin／J 權限）
- `deploy/` — ops — Docker Compose — staging 部署資產
- `scripts/` — tooling — Python — repo contract、env contract、OpenAPI dump、TCMS
- `aidlc/` — method workspace — Markdown／JSON — memory、intents、codekb（非執行時）
- `.claude/` — upstream AI-DLC 框架 — TypeScript（bun）— 升級時覆蓋；規則不寫於此

### Build System

- **Type**：雙套件（pip + npm/Vite）＋ Docker 映像＋ GitHub Actions CI
- **Config Files**：
  - `backend/requirements.txt`（`fastapi[standard]==0.141.1`、`pydantic==2.13.4` 精確釘選）
  - `frontend/package.json`、`frontend/package-lock.json`、`frontend/tsconfig*.json`、`frontend/vite.config.ts`
  - `deploy/docker-compose.deploy.yml`、`deploy/docker-compose.test.yml`
  - `.github/workflows/ci.yml`（contract → lint／build → OpenAPI drift → unittest → Docker build）
- **Build Dependencies**：frontend `tsc -b && vite build` 不依賴 backend 執行；`openapi.json` 由 `backend/scripts/dump_openapi.py` 產出，前端 `npm run gen:types` 寫入 `frontend/src/types/api.d.ts`。CI 以 `--check` 擋漂移。

### APIs Discovered

- REST（FastAPI）— `backend/main.py` 掛五組 router，**無第六組、無 `/api/cost*`**：
  - `/api/architecture` — `agent_router`（2 POST generate）、`review_router`（reviews／detect-provider／PNG）、`lens_router`（5 端點）
  - `/api/collab` — 圖 CRUD／chat／share／bootstrap + WS `/ws/{workspace_id}`
  - `/api/auth` — login／register／me／users list／authorization-requests／role-permissions
  - `GET /` — 健康檢查
- 公開契約清冊：`openapi.json`（HEAD 路徑集合與 2026-08-06 相同前綴；新增欄位在 `/api/auth/list` 的 `last_activity_at`／分頁，**不是**成本端點）。
- **Cost／pricing／TCO 端點：ABSENT**（見 C1 Delta §7）。

### Frameworks & Libraries

- FastAPI `0.141.1` + Pydantic `2.13.4` + Uvicorn — HTTP API
- SQLAlchemy + psycopg2-binary — PostgreSQL ORM
- passlib／bcrypt／PyJWT — 認證
- claude-agent-sdk — LLM agent 編排（`LLM_PROVIDER` 可改 CLI）
- httpx — **僅** n8n 圖示 webhook 與 diagrams.net PNG export（非價目表）
- hypothesis — 既有 PBT（產圖／規則／auth／activity；**無** cost calculator）
- React `^19.2.6` + react-router-dom `^6.22.0` + Vite `^8.0.12` + Tailwind `^4.3.0`
- Playwright `^1.56.0` — `frontend/tests/e2e/regression.spec.ts`
- embed.diagrams.net — 畫布 iframe

### Test Coverage

- **Test Directories**：`backend/tests/`（21 個 `test_*.py`）、`frontend/tests/e2e/`（單一 `regression.spec.ts`）
- **Test Frameworks**：`unittest` + Hypothesis；前端無 Jest／Vitest 元件單元測試；e2e 為 Playwright
- **Coverage Config**：ABSENT（無 `pytest.ini`／coverage 門檻；CI 跑 `python -m unittest discover -s tests -v`）
- **TestClient**：PRESENT — `backend/tests/test_user_list_endpoint.py` 使用 `starlette.testclient.TestClient`（本 repo 第一支 HTTP 層測試，針對 `/api/auth/list` 分頁欄位，**非**成本）
- **Property-based**：7 檔共 13 個 `@given`（`test_design_agent` 2、`test_wa_rule_engine` 2、`test_diagram_builder` 2、`test_diagram_icons` 1、`test_collab` 1、`test_auth` 1、`test_activity` 4）。**cost calculator PBT：ABSENT**（無模組可測）。
- **C1／pricing 測試**：ABSENT。`backend/tests/` 內 `'C1'`／`"C1"` 零命中。FinOps 僅作為 RBAC 角色出現（`test_review_authz.test_finops_no_a3_edit`、`test_collab` viewer、`test_j3a_view_permission` deny 側）。WA `COST-*` finding codes **零測試**（僅定義於 `wa_rule_engine.py`）。

### Code Quality Indicators

- **Linting**：frontend ESLint 10 + `tsc -b`；backend 依 CI unittest（無獨立 ruff／mypy job 於 `ci.yml` 前段）
- **CI/CD**：`.github/workflows/ci.yml`；`ut` 觸發 deploy；OpenAPI／generated types 漂移檢查（post-`8c90f40`）
- **Documentation**：`CLAUDE.md`、`LOCAL-DEV.md`、`DEPLOY.md`、`TESTING.md`、AIDLC artifacts；schema 雙源 `schema.sql` + `schema_rbac.sql`，異動須同步 `DEPLOY.md`（project Mandated）

### Technical Debt Signals

- C1 產品面尚未實作，但 RBAC 矩陣與權限頁已露出「C1 TCO 與流量預算」欄（權限種子與 UI 標籤領先實作）。
- WA 規則引擎有 `cost_optimization` 啟發式 findings，與 TCO 計算無關，易被誤認為「已有成本能力」。
- 圖節點契約只有 `id`／`name`／座標，無 SKU／規格／時數；C1 若要從圖抽資源，必須擴充 extract 或另存 overlay。
- 無 inbox／持久化通知；超支警告若要做，沒有現成 primitive 可接。
- ADR-0006 要求 cost calculator 走 property-based testing，但模組本身不存在 → 本 round 屬 **greenfield 缺口**，不是覆蓋不足。

---

## 仍成立的 baseline（相對 `8c90f40` codekb）

下列與 space-level codekb 一致，本 round 可 Keep：

| 斷言 | 證據 |
|---|---|
| 模組化單體：React SPA + FastAPI + PostgreSQL + diagrams.net embed | `frontend/`、`backend/main.py`、`schema_rbac.sql` |
| 五組 router 前綴：`/api/architecture`、`/api/collab`、`/api/auth` | `backend/main.py:47-51` |
| 可運行故事集中在 A1 Workspace、A3 Assessment、J Admin | `frontend/src/App.tsx` 路由表；pages 僅 8 個 |
| `user_diagrams` 存 draw.io XML blob，無結構化資源列 | `schema_rbac.sql:49-55` 與 `8c90f40` 欄位相同 |
| RBAC 為 role × story × {view,edit,review}；11 canonical roles 含 `FinOps_Analyst` | `backend/services/rbac.py:23-35`、`rbac_seed_data.py` 308 列 |
| Staging／production 雲端帳號仍 out of scope | `aidlc/spaces/default/memory/project.md` Scope Overrides |

---

## C1 Delta

Hunt 項逐條：**PRESENT** 或 **ABSENT**（缺席必附搜尋證明）。未發明任何 SKU。

### 1. 圖資源擷取（diagram extract）

**結論：有「WA 用的精簡 mxCell 摘要」，沒有「可定價的資源清單」。SKU 欄位 ABSENT。**

#### `parse_diagram_summary`（`backend/services/wa_rule_engine.py:125-164`）

從 mxGraph XML iterate `mxCell`，產出：

```
{ "nodes": [{ "id", "label", "style" }], "edges": [{ "id", "source", "target" }], "node_count", "edge_count" }
```

- **有**：`id`、`label`（來自 `value`，經 `_cell_text`）、`style`（lowercase，截斷 200 字元）
- **無**：SKU、instance type、provider 欄位、hourly、region、count／hours
- `style` 僅供關鍵字匹配（如 `mxgraph.aws`）；不是機器可讀的服務目錄
- 檔案開頭 docstring（L1–6）明示：「不連 AWS API；不讀 DB」
- 消費者：`review_orchestrator`、`review_router`、`wa_score_service`、`wa_lens_engine`、`wa_collab_orchestrator`、`evaluate()` — 全部是 A3 評核路徑，不是計價

#### `detect_provider`（同檔 `:874-950`）

對 `label + style` blob 計分 `aws|gcp|azure`，回傳 `{ provider, scores }`。註解寫「manual override OK」——這是 **A3 雲端供應商覆寫**，不是成本 Manual Override。呼叫端：

- `POST /api/architecture/reviews/detect-provider`（`review_router.py:93-101`）
- `POST /api/architecture/reviews`：`auto_detect_provider=true` 時覆蓋 body；`false` 時用 `body.provider`（`:155-158`）
- 前端 `AssessmentPage.tsx:1318-1328` 有 AWS／GCP／Azure `<select>`，送審時 `auto_detect_provider: false`（約 `:893-894`）

#### `diagram_builder`／`design_agent` 產出契約

`DRAW_INPUT_SCHEMA`（`backend/services/design_agent.py:102-183`）nodes **required**：`id`, `name`, `x`, `y`。groups 另有 `type` enum（`aws_cloud`／`vpc`／`az`／…／`azure_subnet`）。**無 sku／size／hours。**

`build_mxgraph_xml`（`diagram_builder.py:1672-1818`）寫入 mxCell：

| 角色 | XML 欄位 |
|---|---|
| group | `id`, `value`（name）, `style`（`GROUP_STYLES[type]`）, `vertex=1`, `parent`, geometry |
| node | `id`, `value`（`comp.upper()` 即 name）, `style`（`shape=image;image=data:image/svg+xml,...`）, `parent`, 80×80 geometry |
| edge | `id`, `edge=1`, `parent="1"`, `source`, `target`, `style`（含 `exitX/Y` `entryX/Y` 與 waypoints） |

Provider 由 group `type` 推斷 AWS／GCP／Azure，**只拿去跟 n8n 要 SVG**（`:1696-1704`、`:1774`），不查價。

`sku`／`instance_type`／`machineType`／`vm_size` 在 `backend/`：`rg` **0 命中**。

#### Collab 持久化 XML

`user_diagrams.xml_data` 即上述 mxGraph 字串（或使用者在 embed 裡改過的版本）。沒有平行的資源表。

#### `user_diagrams` schema 欄位

`schema.sql:18-26`、`schema_rbac.sql:49-55`、`backend/models.py:80-89`：

| 欄 | 型別 | 用途 |
|---|---|---|
| `id` | SERIAL PK | |
| `user_id` | INTEGER FK → `users` | 擁有者 |
| `title` | VARCHAR | 顯示名，預設「未命名架構圖」 |
| `xml_data` | TEXT NOT NULL | draw.io XML |
| `updated_at` | TIMESTAMPTZ | |

**無** sku、provider、cost、budget 欄。HEAD 與 `8c90f40` DDL **位元相同**。相關表：`diagram_shares`、`user_diagram_chats`、`architecture_reviews.diagram_id` — 皆非計價。

---

### 2. Cost calculator／定價客戶端／價目表 HTTP／硬編碼價格

**ABSENT（對抗式搜尋）。**

| 搜尋 | 範圍 | 結果 |
|---|---|---|
| 檔名 `*cost*`／`*pricing*`／`*tco*`／`*finops*` | `backend/` `frontend/` | **0** 檔 |
| `cost_calculator` \| `pricing_client` \| `PriceList` \| `GetProducts` \| `cloudbilling` \| `retailprices` | `backend/` `frontend/src/` `openapi.json` `schema*.sql` | **0** 命中 |
| `usd/hour` \| `on.demand` \| `hourly_rate` \| `price_usd` \| `spot_price` \| `reserved_instance` | `backend/` `frontend/src/` | **0** 命中 |
| `pricing.amazonaws` \| `cloudbilling` \| `retailprices` \| `price.?api` | `backend/**/*.py` | **0** 命中 |
| `boto3` \| `google.cloud` \| `azure.mgmt` | `backend/**/*.py` | **0** 命中 |
| `httpx.(get\|post)` 實際呼叫 | `backend/` | **2 處，皆非價目**：① `diagram_builder.py:1609-1614` `POST` `N8N_WEBHOOK_URL` 取 SVG；② `review_router.py:425-428` `POST` `convert.diagrams.net`／`exp.draw.io` 出 PNG |

**最接近、但不是 C1 的東西**：`wa_rule_engine.py` 的 `cost_optimization` findings（關鍵字啟發式，無金額）：

| code | 條件（label/style 關鍵字） | 位置 |
|---|---|---|
| `COST-OVERSIZE-HINT` | `xlarge`／`4xlarge`／`metal` | `:308-317` |
| `COST-NO-LIFECYCLE` | 有 s3/ebs/efs 無 lifecycle | `:319-329` |
| `COST-NAT-HINT` | `nat` | `:336-345` |
| `GCP-COST-NO-COMMIT` | GCE 無 CUD／Spot | `:606-617` |
| `AZ-COST-NO-COMMIT` | VM 無 Reserved／Spot | `:836-847` |

這些 findings **沒有對應測試**（`COST-*` 僅出現在 `wa_rule_engine.py`）。

**Public pricing vs Manual Override（設計所需事實）**：

- Public price list client：**ABSENT**
- 成本 Manual Override（時數／單價覆寫）：**ABSENT**（無 API、無表、無 UI）
- 易混淆的「override」：**PRESENT** — A3 `provider` 下拉 + `auto_detect_provider: false`（雲別，不是價錢）

---

### 3. Frontend：Sidebar 分組、`App.tsx` 路由、Workspace 成功卡、Cost 頁

#### Sidebar 分組 — PRESENT（架構／系統管理）；**Cost／FinOps 組 ABSENT**

`frontend/src/components/Sidebar.tsx`：

- 可見條件只看 `canArch('view')`、`can('A3','view')`、`can('J3a'|'J3b','view')`（`:17-22`）。**無** `can('C1', …)`。
- 展開時兩組：
  1. **架構**（`:126-168`）：`/workspace`「架構圖生成」、`/assessment`「評估儀表板」
  2. **系統管理**（`:182-237`）：`/admin/users`、`/admin/authorization-requests`、`/admin/role-permissions`
- 收合：`NavChromeContext` + `localStorage` key `cloud360.nav.sidebarCollapsed`（見非 C1 delta）
- 「成本」「FinOps」「TCO」字串在 `Sidebar.tsx`：**0** 命中

#### `App.tsx` 路由 — PRESENT；**`/cost` ABSENT**

| path | 守衛 | 頁面 |
|---|---|---|
| `/login` | 公開 | `LoginPage` |
| `/403` | 公開 | `ForbiddenPage` |
| `/waiting-approval` | `ProtectedRoute` | `WaitingApprovalPage` |
| `/workspace` | `CapabilityRoute storyId="A1"` | `WorkspacePage` |
| `/assessment` | `CapabilityRoute storyId="A3"` | `AssessmentPage` |
| `/admin/users` | `J3a` | `AdminPage` |
| `/admin/authorization-requests` | `J3a` | `AuthorizationRequestsPage` |
| `/admin/role-permissions` | `J3b` | `RolePermissionsPage` |
| `/`、`*` | `DefaultRedirect` | 依 A1→A3→J3a→J3b，**無 C1 分支**（`:17-25`） |

`frontend/src/pages/` 僅 8 檔；**無** `CostPage.tsx`。`path="/cost`｜`CostPage`｜`FinOpsPage`｜`TcoPage`：`rg` **0**。`CapabilityRoute` 從未以 `C1` 呼叫（`backend/` `require_story_action("C` 亦 0）。

#### Workspace 成功卡 CTAs（`WorkspacePage.tsx` ~931+）

成功 toast（`:931-988`）在 `toast.showCtas` 時三顆鈕：

1. 「繼續對話編輯」→ `setToast(null)`
2. 「生成 IaC 代碼」→ `showComingSoon('IaC 代碼生成')`（`:258-264` 假成功卡「即將推出」）
3. 「Well-Architected」／「儲存並評核」→ `goWellArchitected()`（真導向 A3，`:407+`）

錯誤卡另有「聯絡架構師（即將推出）」。**無「估算成本／開啟 TCO」CTA。** 全檔 `cost|TCO|FinOps|預算`：**0** 命中。

#### Cost 頁 — ABSENT

`RolePermissionsPage.tsx:16-40` **僅標籤**：pillar `C: '成本與 FinOps'`、`C1: 'TCO 與流量預算'`、`C2: '資源優化定價'`、`C3: 'Egress 隱性成本'`。這是權限矩陣欄名，不是產品頁。

---

### 4. In-app notification／banner／inbox

**持久化 inbox／通知中心：ABSENT。** 只有頁面級 toast 與畫布橫幅。

| Primitive | 位置 | 行為 |
|---|---|---|
| `toast` state | `WorkspacePage`、`AdminPage`、`RolePermissionsPage`、`AuthorizationRequestsPage` | 行程內、不入 DB |
| `showComingSoon` | `WorkspacePage.tsx:258-264` | 假成功 toast |
| `headerBanner` | `DrawioCanvas.tsx:26,297`；Workspace 注入 `:1035-1042` | 僅檢視／審核模式琥珀橫幅 |
| WebSocket | `collab_router.py:221-232` `/api/collab/ws/{workspace_id}` | 圖協作 broadcast，非通知 inbox |

`frontend/src`：`inbox`｜`NotificationCenter`｜`notification_` → **0**。  
`schema.sql`／`schema_rbac.sql`／`models.py`／`database.py`：`CREATE TABLE.*notif`｜`inbox`｜`overspend`｜`budget` → **0**。  
`backend/` `smtp`／`sendgrid`／`slack`（應用碼）→ 無寄信／推播客戶端（`ses` 僅 n8n 圖示別名 `simple email service`）。

**Budget／overspend：ABSENT**（應用碼 0 表、0 API、0 UI）。`detect_provider` 註解的「manual override」不可當成超支覆寫。

---

### 5. RBAC：FinOps／C1 種子（PRESENT）vs 執行期執法（ABSENT）

角色 **PRESENT**：`CANONICAL_ROLES` 含 `FinOps_Analyst`、`Project_Architect`、`Project_Editor`（`rbac.py:23-35`）。別名 `Engineering_Manager` → `Project_Editor`（`:44-47`）。種子帳號 `david`／`alex`／`hannah`（`database.py:54-65`）。

`user_can(db, role, "C1", action)` **通用函式可用**（`:103-128`），但 **沒有任何 router 以 C1 守衛**。

#### C1 預設矩陣（`rbac_seed_data.py:82-92` ≡ `schema_rbac.sql:266-276`）

| role | view | edit | review |
|---|---|---|---|
| `FinOps_Analyst` | true | **true** | false |
| `Project_Architect` | true | false | false |
| `Project_Editor` | true | false | false |
| `Project_Admin` | true | false | false |
| `SRE` | true | false | false |
| `Ops_Lead` | true | false | false |
| `Platform_Admin` | true | false | false |
| `Platform_Owner` | true | false | false |
| `Developer` | **false** | false | false |
| `Platform_Engineer` | **false** | false | false |
| `Security_Reviewer` | **false** | false | false |

設計含義（現況）：只有 `FinOps_Analyst` 能 **edit** C1；架構師／編輯者僅 view。C1 頁面尚未存在，故這些旗標目前只出現在 `RolePermissionsPage` 矩陣。`test_rbac.py` **不覆蓋 C1**（檔內無 `C1|C2|C3`）。

C2／C3 同樣有種子（本 round 範圍外）；C3 上 `Project_Architect` 為 view+edit（`rbac_seed_data.py:104`），與 C1 不同。

Schema／deploy 同步：C1 **沒有新表**，故目前無 schema 增量義務。若本 intent 新增 cost／budget 表，必須同步 `schema_rbac.sql` + `DEPLOY.md` + `database.py` `_ensure_*`（既有模式：`_ensure_a4_schema`／`_ensure_j5_schema`／`_ensure_a3_schema`／`_ensure_last_activity_schema`）。

---

### 6. Tests

| 題 | 判定 | 證明 |
|---|---|---|
| cost／pricing 單元測試 | **ABSENT** | 無 `test_cost*`；`'C1'` 在 tests 0 命中 |
| WA `COST-*` findings 測試 | **ABSENT** | codes 只在 `wa_rule_engine.py` |
| cost calculator PBT | **ABSENT** | 無 calculator；13 個 `@given` 皆非計價 |
| `TestClient` | **PRESENT（他域）** | `test_user_list_endpoint.py`；樣板在 `tests/helpers.py` |
| FinOps 角色測試 | 僅 A3／J3a／collab | `test_review_authz.py:20`、`test_collab.py:32`、`test_j3a_view_permission.py:58` |
| e2e 成本頁 | **ABSENT** | `regression.spec.ts`：登入、RBAC 側欄、Admin 最後活動／分頁 |

---

### 7. `openapi.json`／generated types

**Cost 端點 ABSENT。** `openapi.json` 對 `cost|pricing|tco|finops|budget` 的命中只有 schema 名 `CommitCollabReviewBody`（false positive）。

HEAD `/api/*` 路徑（無任何 cost）：

- architecture：`/generate`、`/generate-wa-collab`、`/diagrams/render-png`、`/lens/*`、`/reviews`、`/reviews/commit-collab`、`/reviews/detect-provider`、`/reviews/{review_id}`、`persist-diagram`、`retry-suggestions`
- auth：`/login` `/register` `/me` `/list` `/roles` `/role-permissions` `/authorization-requests*` `/{user_id}*`
- collab：`/diagrams*` `/users` `/workspace/bootstrap` `/workspace/last-opened`

`frontend/src/types/api.d.ts` 對 `cost|pricing|tco|finops|budget`：**0**（`types/` 目錄）。新增型別是 `last_activity_at`（`:977`）等 auth 欄位。

---

### 8. HEAD vs 2026-08-06 codekb：非 C1 但會讓舊結論變假

舊 `code-quality-assessment.md`／`architecture.md` 的 A1／A3 **hotspots 多已在 `9d69bc1` 之後被修**。Architect 更新 codekb 時應修正，勿照抄 8c90f40 債項。

| 舊 codekb 斷言 | HEAD 事實 | 證據 |
|---|---|---|
| Sidebar 固定 `w-64`、不可收合 | **已可收合**（icon rail `w-14`） | `NavChromeContext.tsx`（**NEW** since 8c90f40）、`Sidebar.tsx:9,45-84,98-114` |
| Sidebar 扁平 IA、缺 A／J grouping | **已有**可收放「架構」「系統管理」；仍**無 C 組** | HEAD `Sidebar.tsx:126,182`；`8c90f40` 僅有「系統管理」靜態標題、無「架構」group header |
| Edges 缺 exit／entry ports | **已有** `compute_edge_waypoints` + `exitX/Y` `entryX/Y`；edge `parent` 仍 `"1"` | `diagram_builder.py:1786-1811`；`8c90f40` 對 `exitX` **0 命中** |
| Draw.io save／exit 未處理 | **已處理** `data.event === 'save'|'exit'` | `DrawioCanvas.tsx:184-192,279+` |
| 無 prompt refusal | **已有** `prompt_guard.py`（**NEW**） | `8c90f40` 無此檔 |
| Undo 因 autosave→load 損壞 | 程式註解稱已避免 echo load | `DrawioCanvas.tsx:159-183`（本 scan 未重跑 UX 驗證） |
| 無新 router | **仍五組**；無 cost router | `main.py` 與 8c90f40 相同 `include_router` |
| 無新頁／新路由 | **App.tsx 路徑集合相同** | 8c90f40 已含 AuthorizationRequests／Assessment |
| （未寫入舊 codekb）最後活動時間 | **NEW**：`users.last_activity_at`、Admin 欄、分頁、`TestClient` 測試 | `database.py:_ensure_last_activity_schema`、`LastActivityCell.tsx`、`PaginationControl.tsx`（皆 NEW） |
| fastapi 未釘選 | **NEW**：`fastapi==0.141.1` `pydantic==2.13.4` + OpenAPI drift job | `requirements.txt:8-9`、`ci.yml` OpenAPI spec drift |
| `LLM_PROVIDER`／claude CLI | **NEW** | 提交 `c683c1f` |
| n8n Basic Auth | **NEW** | `diagram_builder.py:1604-1613` |

**仍真、舊 codekb 可 Keep**：無獨立微服務、無 cost API、production 雲帳號 out of scope、RBAC 矩陣含 C 支柱但無產品面。

**會讓「業務總覽 in-scope 只有 A1／A3／J」過時的？** 執行時能力仍是 A1／A3／J；C1 仍是種子＋標籤。Admin 最後活動／分頁是 J 域增量，不是 C1。

---

## 給後續設計的事實摘要（C1 TCO only）

1. **Extract**：最多能用 `parse_diagram_summary.nodes[].label|style` 做關鍵字對應；沒有 SKU。要精準 TCO 需擴充 `DRAW_INPUT_SCHEMA`／mxCell 或另存 overlay 表（今日 `user_diagrams` 只有 XML blob）。
2. **Pricing**：必須新寫 client 或靜態表；repo 內零價目 HTTP、零硬編碼 USD。不要把 WA `COST-*` 或 A3 provider select 當成定價／Override。
3. **UI 掛點**：Sidebar 無 C 組；`DefaultRedirect` 無 C1；成功卡無成本 CTA（現有 CTA 是 IaC coming-soon + WA）。權限頁已顯示 C1 欄名。
4. **RBAC**：種子已定 — `FinOps_Analyst` 唯一 C1 edit；`Project_Architect`／`Project_Editor` 僅 view。Intent 若讓架構師改時數，屬 **seed 變更**，需 allow/deny 雙向測試（現無 C1 測試）。
5. **通知／預算**：無 inbox、無 budget 表；超支警告從零開始。
6. **測試／PBT**：calculator 屬新模組，ADR-0006 將要求 Hypothesis；`TestClient` 樣板可仿 `test_user_list_endpoint.py`。
7. **OpenAPI**：無 cost paths；落地時必 `dump_openapi.py` + `gen:types`，否則 CI drift 紅燈。
8. **Schema/deploy**：今日無 C1 DDL；若加表，blocking 同步 `schema_rbac.sql`、`DEPLOY.md`、`database.py` `_ensure_*`。

---

## 掃描方法備註

- 應用碼搜尋排除 `.claude/`、`node_modules`、intent 文件，避免 session-cost／aidlc 工具假陽性。
- 未執行完整 unittest／e2e（scan-only）；未讀 secret、未連雲端價目 API。
- 未發明 SKU 或價格數字。
