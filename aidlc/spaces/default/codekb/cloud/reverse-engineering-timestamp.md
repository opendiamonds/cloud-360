# Reverse Engineering 時間戳

> Freshness marker for space-level codekb｜repo `cloud`｜mode **Focused merge（STALE）**

## 掃描元資料

| 欄位 | 值 |
|---|---|
| 執行時刻（UTC） | `2026-10-01T07:06:31Z` |
| Commit（full） | `5fd8f14f8d1d4cdaa52ed89428574a0472fa2ae0` |
| Commit（short） | `5fd8f14` |
| 分支脈絡 | `luojingting/feat/c1-workspace-optimize` |
| 來源 fingerprint（snapshot） | `git:81c5a1600194da8a5429a3103e1bc84e396ef08b` |
| Intent | `261001-a2-langgraph`（Assessment／A3 agent 框架迁 LangGraph） |
| 模式 | **Focused merge（STALE）**：更新 A2／Assessment／agent／LangGraph／`llm_provider` 區塊；保留成本域等先前散文；先前 `analyzed.*` demote 為 shallow |
| Active space | `default` |
| Codekb 目錄 | `aidlc/spaces/default/codekb/cloud/` |
| 專案類型 | brownfield |
| Pipeline | reverse-engineering link 2／FINAL（architect synthesis） |
| 上游輸入 | `<record>/inception/reverse-engineering/developer-scan.md` |
| 前一 store_generation | `sha256:8c2194a60a24d3f2438fa78b3f6f2f625b0f2983aee2bd3199531bebef71f57d` |
| Depth | Minimal |

### 關於 fingerprint

Scope 區塊的 `fingerprint:` 為 `codekb-scope-diff --mint --paths <本輪 analyzed.paths>` 的 verbatim 輸出，對應本輪深讀路徑集合的來源指紋（與 snapshot `source_fingerprint` 同值 `81c5a160…`，因 snapshot paths 與本輪 deep 集合一致）。

## 與前一版 codekb 的關係

前一版（2026-09-16、intent `260916-estimate-upload-rework`）為 `kind: full`（`analyzed.paths` 含 `./`）。本輪因 store **STALE**，依 stage 規則：

- `analyzed.paths`／`analyzed.components` **僅本輪**深讀結果；
- 前一版 `analyzed.paths`（含 `./` 與 cost／CI／deploy 等）**demote** 進 `shallow.paths`；
- 成本域、CI、部署等散文**保留**，但不得再視為已驗證 deep。

預期 compare 為 **NARROWER**（verified deep 範圍小於先前 full store）。

## 深度分佈（誠實紀錄）

**Deep（本輪）**：見下方 Scope `analyzed.paths`——Assessment 評核 call graph、`llm_provider`／`llm_limits`、Design LangGraph、`langgraph_runtime`、相關測試／smoke、`main.py`／`Dockerfile`／`requirements.txt`、`AssessmentPage`／`App.tsx`、OpenAPI 評核相關 paths。

**Skimmed／demoted**：`backend/cost/`、多數 `backend/services/` 其餘模組、`backend/prompts/`、非 Assessment 前端頁、除兩支 langgraph 測試外的 tests、CI／deploy／schema 文件等（含前一版 full 覆蓋宣告）。

## 本輪重點發現索引

| 發現 | 所在 artifact |
|---|---|
| Design＝LangGraph；Review／Lens＝Claude Agent SDK | `architecture.md`、`business-overview.md` |
| `langgraph_runtime` 未接 Assessment；雙 OpenRouter 適配 | `architecture.md`、`dependencies.md` |
| `llm_provider` 模型預設與 env 契約 | `technology-stack.md`、`api-documentation.md` |
| Dockerfile／`llm_provider` 頂註過時 | `code-quality-assessment.md` |
| 缺 `langchain-openai`／`claude-agent-sdk` pin | `technology-stack.md`、`dependencies.md` |
| Assessment SSE 契約與互動圖 | `architecture.md`、`api-documentation.md` |
| 成本域散文保留但 shallow | `business-overview.md`、`dependencies.md` |

## Scope of Analysis

```yaml
scope_version: 1
kind: partial
intent: 261001-a2-langgraph
fingerprint: 81c5a1600194da8a5429a3103e1bc84e396ef08b
analyzed:
  paths:
    - backend/services/agent_router.py
    - backend/services/design_agent.py
    - backend/services/langgraph_runtime.py
    - backend/services/review_agent.py
    - backend/services/review_orchestrator.py
    - backend/services/review_router.py
    - backend/services/wa_score_service.py
    - backend/services/wa_collab_orchestrator.py
    - backend/services/wa_lens_engine.py
    - backend/services/wa_rule_engine.py
    - backend/services/llm_provider.py
    - backend/services/llm_limits.py
    - backend/main.py
    - backend/Dockerfile
    - backend/tests/test_langgraph_runtime.py
    - backend/tests/test_langgraph_migration.py
    - backend/test_agent.py
    - backend/requirements.txt
    - frontend/src/App.tsx
    - frontend/src/pages/AssessmentPage.tsx
    - scripts/smoke_langgraph_openrouter.py
    - openapi.json
  components:
    - backend-app-shell
    - architecture-generation
    - langgraph-runtime
    - wa-review
    - lens-management
    - llm-gateway
    - openapi-contract
    - frontend-routing
    - assessment-page
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
```
