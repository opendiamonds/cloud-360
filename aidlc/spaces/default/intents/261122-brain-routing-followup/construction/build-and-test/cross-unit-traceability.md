# 跨單元追溯檢查

- 來源：`inception/requirements-analysis/requirements.md` 的全部 FR 與 NFR。本 intent 沒有跑 user-stories，沒有 AC 要列舉。
- 證據：stage 層 `construction/code-generation/traceability.json`。本 intent 沒有 per-unit 目錄。
- 判準：每個 ID 至少一筆 `status: OK`，且 target 檔存在。

## 判定：**未全數覆蓋（1 項未覆蓋）**

18 個 ID 中 17 個為 OK，1 個（NFR1）為 Deferred。

## 逐項

| ID | 狀態 | 承接 | Target | Target 存在 |
|---|---|---|---|---|
| FR1.1 | OK | code-generation | `backend/services/intent_routing_decisions.py` | 是 |
| FR1.2 | OK | code-generation | `backend/services/intent_routing_decisions.py` | 是 |
| FR1.3 | OK | code-generation | `backend/services/intent_routing_context.py` | 是 |
| FR1.4 | OK | code-generation | `backend/services/intent_routing_decisions.py` | 是 |
| FR2.1 | OK | code-generation | `backend/services/work_orchestrator_capabilities.py` | 是 |
| FR2.2 | OK | code-generation | `backend/services/work_orchestrator.py` | 是 |
| FR2.3 | OK | code-generation | `backend/services/work_orchestrator_rules.py` | 是 |
| FR2.4 | OK | code-generation | `backend/services/work_orchestrator.py` | 是 |
| FR2.5 | OK | code-generation | `backend/services/work_orchestrator.py` | 是 |
| FR3.1 | OK | code-generation | `inception/decisions/0025-decisions-routing-carries-conversation-history.md` | 是 |
| FR3.2 | OK | code-generation | `backend/services/intent_routing_decisions.py` | 是 |
| NFR1 | **Deferred** | 部署後驗證（deployment-execution 之後） | `inception/decisions/0025-…md`（記為待辦） | 是 |
| NFR2 | OK | code-generation | `backend/tests/test_intent_routing_decisions.py` | 是 |
| NFR3 | OK | code-generation／build-and-test | `construction/code-generation/code-summary.md`，本 stage 複驗見 `test-results.md` | 是 |
| NFR4 | OK | code-generation | `construction/code-generation/code-summary.md` | 是 |
| NFR5 | OK | code-generation | `backend/services/intent_routing_decisions.py` | 是 |

群組標題 FR1、FR2、FR3 在 traceability.json 也各有一筆 OK，由上表子項落地，不另計。

## 未覆蓋項

- **NFR1 staging 路由重新量測**：需要真實 OpenRouter 呼叫，本機沒有金鑰；requirements OQ1 已指定由部署後的驗證承接。量測輸入是 ADR-0024 的六句，加上「架構設計提問後只回 A」，這一句要用真實歷程形狀，也就是提問與提示依序為最後兩則（requirements 審查 R-01）。通過條件寫在 requirements NFR1。**在這項完成前，ADR-0025 維持 Proposed**。
