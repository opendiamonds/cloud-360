# Reverse Engineering 時間戳

> Freshness marker for space-level codekb｜repo `cloud`｜mode **Focused merge（STALE）**

## 掃描元資料

| 欄位 | 值 |
|---|---|
| 執行時刻（UTC） | `2026-11-05T15:10:57Z`（architect 合成寫入；developer 掃描 `2026-11-05T15:03:59Z`） |
| Commit（full） | `0bffc82d01cfe01edb1f3f5a8931290d5f885501` |
| Commit（short） | `0bffc82` |
| 工作樹狀態 | 有未提交變更：`aidlc/` 之 `intents.json`、`memory/project.md`、本 intent record 等（均為 aidlc 工作區檔，非應用程式碼；`git status --short` 抽查） |
| 來源 fingerprint | `84ff69b31e88149bb65d0a72ba826aa452de62a5`（對本輪 `analyzed.paths` 以 `codekb-scope-diff --mint` 取得） |
| Intent | `261105-d-iac-generation`（Story D：D1 Terraform 產出／D2 IaC 安全掃描／D3 Secret 處理） |
| 模式 | **Focused merge（STALE）**：更新 Story D／Workspace／RBAC 矩陣／A1 agent router／`langgraph_runtime`／`main.py`／OpenAPI 區塊；保留先前其餘散文；先前 `analyzed.*` demote 為 shallow |
| Active space | `default` |
| Codekb 目錄（最終發布處） | `aidlc/spaces/default/codekb/cloud/`（本輪僅寫入 staging `<record>/.aidlc-engine/codekb-stage-cloud/`） |
| 專案類型 | brownfield |
| Pipeline | reverse-engineering link 2／FINAL（architect synthesis） |
| 上游輸入 | `<record>/inception/reverse-engineering/developer-scan.md` |
| 前一輪 intent | `261001-a2-langgraph`（STALE 判定：其 22 條 analyzed path 自建置後已變動，`codekb-scope-diff` 逐條列出） |
| Depth | Standard（developer brief）；breadth FOCUSED |

### 關於 fingerprint

Scope 區塊的 `fingerprint:` 為 `codekb-scope-diff --repo cloud --mint --paths <本輪 analyzed.paths>` 的 verbatim 輸出，對應本輪 9 條深讀路徑。

## 與前一版 codekb 的關係

前一版（`261001-a2-langgraph`，掃描 2026-10-01、commit `5fd8f14`）為 `kind: partial`。本輪因 store **STALE**，依 stage 規則：

- `analyzed.paths`／`analyzed.components` **僅本輪**；
- 前一版 `analyzed.paths` 中本輪未再深讀的 17 條 **demote** 進 `shallow.paths`（`agent_router.py`、`langgraph_runtime.py`、`main.py`、`App.tsx`、`openapi.json` 5 條因本輪重新深讀而回到 analyzed）；
- 其餘散文保留，但**不得再視為已驗證 deep**。

**重要**：前一版內容與 HEAD 已有重大漂移（見下節），故「保留散文」不等於「仍然正確」。

## 深度分佈（誠實紀錄）

**Deep（本輪，developer 實讀）**：`frontend/src/pages/WorkspacePage.tsx`、`frontend/src/pages/RolePermissionsPage.tsx`、`frontend/src/App.tsx`、`backend/services/user_router.py`（D／RBAC 相關區段）、`backend/services/langgraph_runtime.py`、`backend/services/agent_router.py`、`backend/services/rbac_seed_data.py`、`backend/main.py`、`openapi.json`（path／operation 盤點）。

**Architect 抽查（不計入 analyzed.paths）**：`backend/requirements.txt`（全文）、`backend/Dockerfile`（頭 ~35 行）、`backend/services/rbac.py`（L250–300）、`backend/services/llm_provider.py`（頭 30 行）、`design_agent.py`／`review_agent.py`／`wa_lens_engine.py`／`cost_advice_agent.py`（框架符號 grep）、`backend/cost/` 與 `backend/tests/` 目錄列表、`LOCAL-DEV.md`／`.env.example`／`render-env.sh`（`rg claude`）。這些**只支撐「前一輪散文已漂移」的警示**，不構成深讀宣稱。

**Skimmed／demoted**：`backend/cost/`（含 `cost_advice_agent`、`advice_*`）、`backend/services/` 其餘模組、`backend/tests/`、CI／deploy／schema 文件、`frontend/src/pages/` 其餘頁、`frontend/src/cost/` 等（含前一輪 partial 覆蓋宣告）。

## 本輪重點發現索引

| 發現 | 所在 artifact |
|---|---|
| Story D＝矩陣領先實作：零 router／OpenAPI／模組／頁／測試；僅 Workspace Coming Soon stub＋D 種子＋標籤 | `business-overview.md`、`component-inventory.md`（`iac-d-pillar-surface`）、`api-documentation.md` |
| IaC CTA 不檢查 `D1`、不呼叫 API（`WorkspacePage` L259–265／L964–970） | `architecture.md` 交易三、`code-structure.md` |
| D1／D2／D3 edit 種子分佈；FinOps_Analyst 全 false | `business-overview.md` |
| **前一輪「Review／Lens＝Claude Agent SDK」已被 HEAD 取代**（LangGraph＋`openrouter_chat_model`；後端 SDK import 為零） | `architecture.md`、`component-inventory.md`（`wa-review`／`lens-management`）、`business-overview.md` |
| **前一輪 cost 全節已漂移**（cost 檔案集合、`/api/cost` 9 ops → `/api/cost/v1` 10 ops、C1＝上傳估價表） | `business-overview.md`、`component-inventory.md`（`cost-domain`）、`dependencies.md` |
| Dockerfile 已無 Node／claude CLI；`langchain-openai` 已列入 requirements（前一輪兩項債已修復） | `technology-stack.md`、`code-quality-assessment.md` |
| 文件漂移：`agent_router` docstring、`llm_provider` 頂註仍稱 SDK；`fastapi` 版本與 `team.md` 不一致 | `code-quality-assessment.md` |
| 可複用底座：`langgraph_runtime`、`require_story_action`、SSE 形狀；首個 generator 觸發 ADR-0006 PBT | `architecture.md`、`dependencies.md` |
| OpenAPI 42 paths／55 operations；SSE 200 schema 為空物件 | `api-documentation.md` |

## Scope of Analysis

```yaml
scope_version: 1
kind: partial
intent: 261105-d-iac-generation
fingerprint: 84ff69b31e88149bb65d0a72ba826aa452de62a5
analyzed:
  paths:
    - frontend/src/pages/WorkspacePage.tsx
    - frontend/src/pages/RolePermissionsPage.tsx
    - frontend/src/App.tsx
    - backend/services/user_router.py
    - backend/services/langgraph_runtime.py
    - backend/services/agent_router.py
    - backend/services/rbac_seed_data.py
    - backend/main.py
    - openapi.json
  components:
    - backend-app-shell
    - architecture-generation
    - langgraph-runtime
    - identity-and-rbac
    - openapi-contract
    - iac-d-pillar-surface
    - frontend-routing
    - workspace-page
    - role-permissions-page
shallow:
  paths:
    - ./
    - backend/cost/
    - backend/models.py
    - backend/database.py
    - .github/workflows/ci.yml
    - scripts/validate_repo_contract.py
    - scripts/validate_env_contract.py
    - scripts/validate_cost_calculator_boundary.py
    - deploy/docker-compose.deploy.yml
    - frontend/package.json
    - frontend/src/cost/
    - backend/services/
    - backend/tests/
    - backend/prompts/
    - backend/lenses/
    - backend/scripts/
    - backend/.env.example
    - frontend/src/pages/
    - frontend/src/components/
    - frontend/src/utils/
    - frontend/tests/e2e/
    - deploy/render-env.sh
    - deploy/.env.example
    - deploy/docker-compose.test.yml
    - .github/workflows/
    - schema.sql
    - schema_rbac.sql
    - .claude/
    - aidlc/
    - README.md
    - DEPLOY.md
    - LOCAL-DEV.md
    - TESTING.md
    - CLAUDE.md
    - AGENTS.md
    - backend/services/lens_router.py
    - backend/services/collab_router.py
    - backend/services/diagram_builder.py
    - backend/tests/test_llm_provider.py
    - backend/services/design_agent.py
    - backend/services/review_agent.py
    - backend/services/review_orchestrator.py
    - backend/services/review_router.py
    - backend/services/wa_score_service.py
    - backend/services/wa_collab_orchestrator.py
    - backend/services/wa_lens_engine.py
    - backend/services/wa_rule_engine.py
    - backend/services/llm_provider.py
    - backend/services/llm_limits.py
    - backend/Dockerfile
    - backend/tests/test_langgraph_runtime.py
    - backend/tests/test_langgraph_migration.py
    - backend/test_agent.py
    - backend/requirements.txt
    - frontend/src/pages/AssessmentPage.tsx
    - scripts/smoke_langgraph_openrouter.py
    - backend/services/rbac.py
    - backend/cost/cost_advice_agent.py
    - backend/cost/advice_stream_router.py
    - backend/cost/advice_orchestrator.py
    - frontend/src/config/api.ts
    - frontend/src/context/auth-context.ts
```
