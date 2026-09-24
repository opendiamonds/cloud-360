# Reverse Engineering Timestamp — Cloud-360

> 本檔是 `aidlc/spaces/default/codekb/cloud-360/` 這份程式碼知識庫的**新鮮度與覆蓋標記**。
> 使用本 codekb 的任何 stage 都應**先讀本檔**，再決定要不要相信你要引用的那一節。

## 掃描基準

| 項目 | 值 |
|---|---|
| **日期** | 2026-09-24 |
| **Commit** | `dc4b687` |
| **Branch** | `danniel/docs/orchestration-brain-ideation` |
| **Repository** | `opendiamonds/cloud-360`（本 clone 的工作目錄名為 `chiton`，**不是 repo 名**） |
| **AIDLC stage** | `reverse-engineering`（inception 2.1，`mode: pipeline`） |
| **執行方式** | 兩環 pipeline：link 1 developer agent 掃描、link 2 architect agent 綜整與寫檔 |
| **作用中 intent** | `260920-orchestration-brain` |
| **前一基準** | `9307dbc`（2026-08-23），該版為兩區定向掃描，覆蓋宣稱為 `UNKNOWN_SCOPE` |

## 本輪是 **Full rescan（廣度）＋ partial（深度）**

這是本檔最重要的一段，請不要略過。

- **廣度**：人工選擇 Full rescan，故 9 份 artifact **全部重寫**，不與舊 store 合併散文。
  舊 store（基準 `9307dbc`）的守門判定為 `UNKNOWN_SCOPE`——它早於覆蓋追蹤機制，
  其中任何一句話在本輪都**不算已驗證**。
- **深度**：本輪**沒有**深讀整個 repo。33 個路徑實讀或以程式完整解析，
  其餘取簽章、計數或檔頭。因此 `## Scope of Analysis` 的 `kind` 為 **`partial`**，
  且**不含 `./`**。

**「Full rescan」指的是輸出被整份取代，不是指每個檔都被讀過。** 兩者是不同的事。

### 深度分佈（`kind` 的判定依據）

| 深度 | 範圍 | 可信度 |
|---|---|---|
| **深讀 `[讀]`** | 33 個路徑（逐一列於下方 `analyzed.paths`），對應 `component-inventory.md` 的 23 個「深讀元件」 | 高 |
| **程式完整解析 `[算]`** | `openapi.json`：全部 42 path／55 operation／32 schema 由程式解析，非逐行閱讀 | 高（僅限被解析出的結構事實） |
| **部分實讀** | `review_router.py` 的 SSE 區段（L55–115、L460–484）、`collab_router.py` 的 WS 區段（L245–300）、`design_agent.py` L1–45、`pricing_client.py` L1–120、`CostPage.tsx` 前 80 行、`Sidebar.tsx` 前 140 行、`schema_rbac.sql` L1–29／L160–330、兩支 cost validator 的檔頭 | 中：**只有被標 `[讀]` 的那幾句**可信，該檔其餘部分未驗證 |
| **僅簽章 `[簽]`** | `backend/services/` 另 15 支、`backend/cost/` 另 12 支、`frontend/src/pages/`、`components/`、`hooks/`、`utils/`、`types/` | 低：存在性與簽章可信，**內部行為不構成已驗證事實** |
| **僅計數 `[算]`** | `backend/tests/`（37 支，**未讀任何一支內容**）、`frontend/tests/`、`scripts/`、11 支 gh-aw `.md`（只取 `engine:` 統計） | 低 |
| **未開啟 `[未驗]`** | `backend/prompts/`、`backend/lenses/`、`deploy.yml` 的 step 實作、`schema.sql`、`.github/` 的 `aidlc-sync-*.yml` | 無 |
| **刻意不掃描** | `.claude/`、`aidlc/`——AI-DLC 框架殼與工作區，非應用程式碼 | 不適用 |

### 為什麼「部分讀過的檔」沒有被升格為深讀元件

`analyzed.paths` 的表達粒度是**檔案或目錄**，無法表達行區間。把
`collab_router.py`（只讀了 WS 區段）宣告為深讀，會讓下一輪的守門員誤以為整支
892／593 行的 router 都已驗證。專案規則要求「深度切分跨越元件邊界時拆分元件、
不放寬覆蓋宣稱」——此處無法以路徑拆分，故採取等效處置：
**該元件整體留在 `component-inventory.md` 的「淺掃元件」區、不進 `analyzed.components`，
實讀的那幾行在散文中以 `[讀]` 就地標註。**

## 本輪未執行的事項（誠實記錄，不得被讀成已驗證）

- 未執行 `python -m unittest`
- 未執行 `npm run lint`
- 未執行 `scripts/validate_env_contract.py`、`validate_cost_calculator_boundary.py`、
  `validate_pricing_lookup_boundary.py`（`validate_repo_contract.py` 僅於寫檔後跑過一次
  做落檔安全檢查，不構成對程式碼品質的判斷）
- 未啟動任何 compose stack
- 未讀任何一支測試檔的內容
- 未讀 `backend/prompts/` 與 `backend/lenses/` 的資料資產
- 未讀 11 支 gh-aw `*.md` 的內容（僅計數與 `engine:` 統計）
- 未讀 `deploy.yml` 的 step 實作（僅 job／step 骨架）

**因此本 codekb 全篇不出現任何關於程式碼品質的「通過／全綠／紅燈」類當下狀態宣稱。**

## 本輪取代的既有數字（下游引用 codekb 或 `team.md` 時以本輪為準）`[算]`

| 事實 | 既有記載 | 本輪實測 |
|---|---|---|
| backend 測試檔數 | 21 | **37** |
| `@given` 處數／檔數 | 13／7 | **17／10** |
| `TestClient` 使用 | 唯一使用例 `test_user_list_endpoint` | **6 支測試檔 ＋ `helpers.py`** |
| backend 精確釘選套件 | 2 支 | **5 支 ＋ 1 支下限 ＋ 11 支未 pin** |
| 前端 `fetch(` | 52 處／10 檔 | **62 處／15 檔** |
| 前端手寫 `Authorization: Bearer` | — | **36 處** |
| `user_router.py` 行數 | 831 | **892** |
| `collab_router.py` 行數 | 527 | **593** |
| CI 閘門 | 「六道閘門」 | **5 job／11 步驟**；`repo-contract` 已擴為 **4 支 validator** |
| OpenAPI 規模 | `ci.yml:204` 註解寫 36 paths／29 schemas | **42 path／55 operation／32 schema** |
| SSE 端點數 | 「3 個」 | **5 個**（3 是**前端消費點**數，不是端點數） |
| API operation 總數 | 舊 store 記 45 | **55** |
| 成本能力 | 舊 store 無 C1 實作 | C1 已實作（10 個 operation、6 張 `estimate_*`／`advice` 表）；舊 `*_cost*` 四表已 **RETIRED** 改名 `archive_*` |

## 觸發完整重跑的條件

- `backend/services/` 或 `backend/cost/` 新增或刪除模組（本輪為 23／21 支）
- API operation 數改變（以 `openapi.json` 為準，本輪 55）
- 資料表新增或刪除（本輪 13 ORM 模型 ＋ 1 association table）
- 架構風格改變（拆出獨立服務、引入訊息佇列或快取層——**本 intent 的 Redis 即屬此類**）
- 權限矩陣維度改變（角色數不再是 11 或 story 數不再是 28）
- 部署服務數改變（本輪 4 個）

## 觸發局部更新

| 變更 | 應更新的檔案 |
|---|---|
| 新增／變更 REST 端點 | `api-documentation.md`、`architecture.md` |
| 新增／變更 WebSocket 或 SSE 契約 | `api-documentation.md`、`architecture.md`（約束二／三） |
| `database.py` 的 `_ensure_*` 或 `schema_rbac.sql` 變動 | `architecture.md`（約束六）、`component-inventory.md`、`code-quality-assessment.md`（T-1／T-2） |
| 依賴釘選範圍變更或引入 lockfile | `technology-stack.md`、`dependencies.md`、`code-quality-assessment.md` |
| CI 步驟或 validator 增減 | `code-quality-assessment.md`、`technology-stack.md` |
| 部署拓撲變更（新容器、新環境變數） | `architecture.md`（約束八）、`technology-stack.md`、`dependencies.md` |
| 新 story id 或新角色 | `business-overview.md`、`api-documentation.md`、`component-inventory.md` |
| 新增 LLM 客戶端棧 | `dependencies.md`、`architecture.md`（約束九） |

## codekb 目錄名的處置（沿用前一輪的人工裁定）

`aidlc/spaces/default/codekb/` 下有兩份：`cloud-360/`（本目錄，正本）與
`cloud/`（基準 `8c90f40`／2026-08-06，**已過期**）。引擎的 `codekbRepoName` 由
`basename(projectDir)` 推導，在名為 `chiton` 的 worktree 會為**同一個 repo** 開出第三份。
**本輪維持裁定：就地更新 `cloud-360/`，不建立 `chiton/`。** 引擎的完成檢查對
`codekb/*/` 做 ANY-exists 判定，寫進 `cloud-360/` 即滿足。**不得**手改 `intents.json`
補 repo 名來繞開——那會讓 swarm `prepare` 去找一個不存在的兄弟目錄。
兩份（潛在三份）codekb 的收斂仍是**未定案的待處理項**。

## Scope of Analysis

```yaml
scope_version: 1
kind: partial
intent: 260920-orchestration-brain
fingerprint: 61a368281b017f1cd568981d04bc7cbfce9eb9ee
analyzed:
  paths:
    - backend/main.py
    - backend/models.py
    - backend/database.py
    - backend/requirements.txt
    - backend/services/agent_router.py
    - backend/services/rbac.py
    - backend/services/rbac_seed_data.py
    - backend/services/auth.py
    - backend/services/activity.py
    - backend/services/langgraph_runtime.py
    - backend/services/llm_provider.py
    - backend/services/prompt_guard.py
    - backend/cost/estimate_intake_router.py
    - backend/cost/advice_stream_router.py
    - backend/cost/advice_orchestrator.py
    - backend/cost/cost_advice_agent.py
    - backend/Dockerfile
    - frontend/src/App.tsx
    - frontend/src/config/api.ts
    - frontend/src/context/AuthContext.tsx
    - frontend/src/context/auth-context.ts
    - frontend/src/cost/slotRegistry.tsx
    - frontend/nginx.conf
    - frontend/Dockerfile
    - frontend/package.json
    - deploy/docker-compose.deploy.yml
    - deploy/docker-compose.test.yml
    - deploy/render-env.sh
    - deploy/.env.example
    - deploy/cloudflared/config.yml
    - docker-compose.yml
    - .github/workflows/ci.yml
    - openapi.json
  components:
    - App Bootstrap
    - ORM 資料模型
    - 資料庫連線與啟動補丁
    - 認證核心
    - RBAC 授權核心
    - 帳號活動記錄
    - 提示防護
    - LLM 供應商環境調教
    - LangGraph Runtime
    - A1 產圖 Router
    - C1 估價 HTTP 入口
    - C1 建議 SSE Router
    - C1 建議 Job 編排器
    - C1 建議 Agent
    - 前端應用殼與路由
    - 前端 API URL 組裝
    - 前端認證 Context
    - 前端成本插槽註冊
    - 後端容器映像
    - 前端交付鏈
    - 部署堆疊
    - CI 管線
    - OpenAPI 契約
shallow:
  paths:
    - backend/services/
    - backend/cost/
    - backend/tests/
    - backend/scripts/
    - backend/prompts/
    - backend/lenses/
    - backend/env_bootstrap.py
    - frontend/src/pages/
    - frontend/src/components/
    - frontend/src/hooks/
    - frontend/src/utils/
    - frontend/src/types/
    - frontend/src/cost/supportedRegions.ts
    - frontend/tests/
    - scripts/
    - schema_rbac.sql
    - schema.sql
    - .github/workflows/
```
