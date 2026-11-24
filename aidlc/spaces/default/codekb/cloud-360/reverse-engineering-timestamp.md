# Reverse Engineering Timestamp

## Run Record

- Date: 2026-11-22（`date -u` 取值 `2026-11-22T14:15:13Z`）
- Commit: `2ad499aab0e32a034a3d0c034a3b0a3f844556bb`（`2ad499a`）＋ 工作樹中未 commit 的修正（10 檔、+207／−18；分支 `danniel/fix/brain-routing-followup-context`）
- Intent：`brain-routing-followup`（record `261122-brain-routing-followup`，scope bugfix，depth Minimal）
- 執行方式：lead-only pipeline，developer agent 同時負責掃描與合成；掃描結果見 `<record>/inception/reverse-engineering/developer-scan-cloud-360.md`

## 新鮮度與深度分佈（請先讀這段）

本輪是 **Full rescan（廣度：9 份 artifact 整份重建）＋ partial（深度）**。「Full rescan」指輸出被整份取代的範圍，**不是**「處處都讀過」。

| 等級 | 範圍 | 意義 |
|---|---|---|
| **深讀**（`analyzed.paths`） | 下方 YAML 列出的 10 支檔，整檔逐行讀過 | 可直接引用 |
| **部分實讀** | `brain_gateway.py`（1–127、499–606、1294–1660、1900–2010 行）、`work_orchestrator_rules.py`（常數、`plan_waits`、`event_for_dependency_terminal`、`PHRASES` diff）、`agent_router.py:153` | 只對標明的行成立；整檔列為 shallow |
| **盤點** | 其餘全 repo（目錄、檔名、`grep` 輪廓、版本清單、`openapi.json` 計數） | 只是索引，引用前須回原始碼核對 |
| **執行** | 四支變更測試 `Ran 109 tests … OK`；`openapi.json` 68 個 path | 2026-11-22 的實際結果 |

各 artifact 在檔頭與段落內以〔實讀〕／〔盤點〕／〔執行〕標註證據強度。被部分實讀的檔案依規則**不**放進 `analyzed.paths`（粒度表達不了行區間）。測試檔只有執行結果、未讀內容，同樣列為 shallow。

## Scope of Analysis

```yaml
scope_version: 1
kind: partial
intent: brain-routing-followup
fingerprint: 68be63e911c0ce5a670076ac235029a44d44c876
analyzed:
  paths:
    - backend/services/intent_routing.py
    - backend/services/intent_routing_decisions.py
    - backend/services/intent_routing_port.py
    - backend/services/intent_routing_context.py
    - backend/services/work_orchestrator.py
    - backend/services/work_orchestrator_capabilities.py
    - backend/services/design_agent.py
    - backend/services/langgraph_runtime.py
    - frontend/src/components/brain/WorkItemList.tsx
    - frontend/src/components/brain/ClarifyCandidates.tsx
  components:
    - intent-router
    - routing-decisions
    - routing-ports
    - routing-context
    - work-orchestrator
    - capability-client
    - design-agent
    - langgraph-runtime
    - brain-ui-work-items
    - brain-ui-clarify
shallow:
  paths:
    - backend/services/brain_gateway.py
    - backend/services/brain_gateway_rules.py
    - backend/services/work_orchestrator_rules.py
    - backend/services/intent_routing_types.py
    - backend/services/intent_routing_predicate.py
    - backend/services/intent_routing_parser.py
    - backend/services/intent_routing_config.py
    - backend/services/intent_routing_errors.py
    - backend/services/session_store.py
    - backend/services/session_types.py
    - backend/services/session_errors.py
    - backend/services/session_scripts/
    - backend/services/agent_router.py
    - backend/services/
    - backend/cost/
    - backend/iac/
    - backend/mcp_bridge/
    - backend/scripts/
    - backend/prompts/
    - backend/lenses/
    - backend/tests/
    - backend/tests_pg/
    - backend/tests_redis/
    - backend/main.py
    - backend/models.py
    - backend/database.py
    - backend/requirements.txt
    - frontend/src/components/brain/
    - frontend/src/
    - frontend/tests/
    - frontend/package.json
    - deploy/
    - scripts/
    - .github/workflows/
    - schema.sql
    - schema_rbac.sql
    - openapi.json
    - ws-contract.json
```
