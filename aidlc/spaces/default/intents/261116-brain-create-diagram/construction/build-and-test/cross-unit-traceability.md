# 跨單元追溯（261116-brain-create-diagram）

> 由腳本自 `inception/requirements-analysis/requirements.md` 列舉 FR／NFR，並讀取 `construction/{diagram-drafts,brain-create-flow,draft-ui,code-generation}/code-generation/traceability.json` 比對；`user-stories` 本 intent 未執行（bugfix scope），故無 AC 可列。產生時間 2026-11-22T14:21:37Z。

**判定：未通過（FAIL）**——39 個識別碼中 37 個有 `OK` 且目標檔存在；2 個未覆蓋：NFR1、NFR2。

## 逐項覆蓋

| ID | 覆蓋 | 擁有者 | 狀態 | 目標 |
|---|---|---|---|---|
| FR1.1 | 是 | brain-create-flow | OK | `backend/services/brain_gateway.py` |
| FR1.2 | 是 | brain-create-flow | OK | `backend/services/brain_diagram_creation.py` |
| FR1.3 | 是 | brain-create-flow | OK | `backend/services/brain_gateway.py` |
| FR1.3a | 是 | diagram-drafts | OK | `backend/services/collab_router.py` |
| FR1.4 | 是 | brain-create-flow | OK | `backend/tests/test_brain_diagram_creation_flow.py` |
| FR1.5 | 是 | brain-create-flow | OK | `backend/tests/test_brain_diagram_creation_flow.py` |
| FR2.1 | 是 | brain-create-flow | OK | `backend/services/brain_diagram_creation.py` |
| FR2.2 | 是 | brain-create-flow | OK | `backend/services/intent_routing_decisions.py` |
| FR2.3 | 是 | brain-create-flow | OK | `backend/tests/test_brain_diagram_creation.py` |
| FR2.4 | 是 | brain-create-flow | OK | `backend/services/brain_diagram_creation.py` |
| FR3.1 | 是 | brain-create-flow | OK | `backend/services/brain_gateway.py` |
| FR3.2 | 是 | brain-create-flow | OK | `backend/services/brain_gateway.py` |
| FR3.3 | 是 | brain-create-flow | OK | `backend/services/brain_gateway.py` |
| FR3.4 | 是 | brain-create-flow | OK | `backend/services/brain_ws_contract.py` |
|  |  | draft-ui | OK | `frontend/src/components/brain/ClarifyCandidates.tsx` |
| FR3.5 | 是 | brain-create-flow | OK | `backend/services/brain_gateway.py` |
| FR3.6 | 是 | brain-create-flow | OK | `backend/services/brain_diagram_creation.py` |
| FR4.1 | 是 | brain-create-flow | OK | `backend/services/brain_diagram_creation.py` |
| FR4.2 | 是 | diagram-drafts | OK | `backend/services/collab_router.py` |
| FR4.3 | 是 | brain-create-flow | OK | `backend/services/work_orchestrator_capabilities.py` |
| FR5.1 | 是 | brain-create-flow | OK | `backend/services/brain_diagram_creation.py` |
| FR5.2 | 是 | brain-create-flow | OK | `backend/services/brain_diagram_creation.py` |
| FR5.3 | 是 | brain-create-flow | OK | `backend/services/brain_diagram_creation.py` |
| FR5.4 | 是 | brain-create-flow | OK | `backend/services/brain_diagram_creation.py` |
| FR6.1 | 是 | diagram-drafts | OK | `backend/models.py` |
| FR6.2 | 是 | diagram-drafts | OK | `backend/services/collab_router.py` |
|  |  | draft-ui | OK | `frontend/src/pages/WorkspacePage.tsx` |
| FR6.3 | 是 | brain-create-flow | OK | `backend/services/work_orchestrator.py` |
| FR6.3a | 是 | brain-create-flow | OK | `backend/services/brain_diagram_creation.py` |
| FR6.3b | 是 | brain-create-flow | OK | `backend/tests/test_brain_diagram_creation_flow.py` |
| FR6.4 | 是 | draft-ui | OK | `frontend/src/components/projects/SystemDiagrams.tsx` |
| FR6.4a | 是 | diagram-drafts | OK | `backend/services/collab_router.py` |
|  |  | draft-ui | OK | `frontend/src/components/projects/OverviewTab.tsx` |
| FR6.4b | 是 | diagram-drafts | OK | `backend/services/hierarchy_service.py` |
| FR6.4c | 是 | diagram-drafts | OK | `backend/services/hierarchy_service.py` |
| FR6.5 | 是 | diagram-drafts | OK | `backend/services/hierarchy_migration.py` |
| FR7.1 | 是 | diagram-drafts | OK | `backend/services/brain_diagram_creation.py` |
| NFR1 | **否** | brain-create-flow | Deferred | `build-and-test`（非檔案） |
| NFR2 | **否** | brain-create-flow | Deferred | `build-and-test`（非檔案） |
| NFR3 | 是 | brain-create-flow | OK | `backend/tests/test_brain_diagram_creation_flow.py` |
| NFR4 | 是 | brain-create-flow | OK | `backend/services/brain_gateway.py` |
| NFR5 | 是 | diagram-drafts | OK | `backend/tests/test_diagram_drafts_api.py` |

## 未覆蓋項目

- **NFR1（判定準確率）**、**NFR2（首字 P50）**：`brain-create-flow` 追溯標為 `Deferred → build-and-test`。兩者需要部署到 staging 的這版程式與真實路由模型，本站無法在本機量測（見 `performance-test-instructions.md`）；本計畫中 build-and-test 之後只剩 `tcms-test-cases`，沒有承接量測的 stage。判定為 `Unverified`，於核可關卡揭露。

## 判讀備註

- **FR6.4**（草稿在切換對象選單、專案頁、工作區歷史清單標示「草稿」）：追溯為 `OK`。專案頁與工作區歷史清單已標示；切換對象選單（`ObjectPicker`）本來就不列出架構圖，沒有可標示之處。審查另指出：大腦建立草稿後，頂部作業對象列的架構圖層**不顯示**草稿標示——FR6.4 未點名該處，故不影響覆蓋判定，但列為已知限制（補上需在 WS 作業對象訊框加欄位，屬契約變更）。
- **FR3.5**（點選時伺服器重新驗證）：追溯為 `OK`；FR3.5 要求的「回覆說明」因契約 `ClarifyPayload` 沒有文字欄位而只以重新列出候選呈現，code-generation 已記為偏差。
