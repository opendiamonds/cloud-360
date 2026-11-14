# 跨單元最終覆蓋閘門（build-and-test Step 10）

- 產出時間（`date -u`）：`2026-11-14T02:19:24Z`
- 產生方式：腳本 `<scratchpad>/bt-gen/gate.py`（輸出 `gate.tsv`），本檔的全部計數與逐列內容由該腳本輸出轉成表格，未手寫數字
- 列舉來源：`inception/requirements-analysis/requirements.md`（`### FRn —`／`### NFRn —` 標題 ＋ `- **FRx.y**` 定義列）、`inception/user-stories/stories.md`（以表格首欄或粗體定義的三段式 `ACx.y.z`）
- 覆蓋來源：24 份 `construction/<unit>/code-generation/traceability.json`；stage-level `construction/code-generation/traceability.json` **不存在**（該目錄只有 `memory.md`）
- 判定：某 ID 至少有一個單元條目 `status: OK`，且其 `target` 中可解析出的檔案路徑在 repo 內存在

## 結論

**FAIL**——206 個 ID 中 **91 個未覆蓋**（需求 87／100、AC 4／106）。依 stage 檔，每一個未覆蓋 ID 都是必須在核可關卡呈現的 build-and-test 發現。

| 類別 | 列舉數 | 覆蓋 | 未覆蓋 |
|---|---|---|---|
| 需求（13 個 FR 群組 ＋ 11 個 NFR ＋ 76 個 FR 子條） | 100 | 13 | 87 |
| 三段式 AC | 106 | 102 | 4 |
| **合計** | **206** | **115** | **91** |

### 未覆蓋的性質（如實區分，不改變 FAIL 判定）

1. **需求層 87 個的主因是追溯粒度**：各單元 `traceability.json` 的 `upstream_ids` 以 AC／BR／單元層 NFR 為主，幾乎不直接列 `FRx.y`。以 `inception/user-stories/traceability.json` 的 FR→US 對照做**傳遞推導**（該 FR 對應的故事是否有任一 AC 在單元層覆蓋）：
   - 72 個所對應的故事**全部**有已覆蓋的 AC；
   - 3 個**部分**：`FR4`（4/5）、`FR4.2`（1/2）、`FR4.4`（0/1）——缺口都來自 `US4.5`（`AC4.5.1`–`AC4.5.3`，見下）；
   - 12 個**沒有對應故事**：`NFR1`、`NFR2`、`NFR3`、`NFR5`、`NFR6`、`NFR8`、`NFR9`、`NFR10`、`NFR11`、`FR9.4`、`FR12.5c`、`FR12.6b`。
   傳遞推導**不是** stage 檔定義的覆蓋，只用來說明缺口的形狀；嚴格判定仍是未覆蓋。
2. **AC 層 4 個**：
   - `AC4.5.1`–`AC4.5.3`（記憶 schema 與資料庫角色邊界）：`memory-data` 標為 `N/A`。**本站實跑證據存在但未進 traceability**：`verify_memory_role.sql` R0–R3（以 `cloud360_memory` 連線：讀不到 `public`、可寫記憶兩表）與 `verify_memory_schema.sql` 於 pg18 通過（`bt-logs/pg-role.log`、`pg-verify_memory_schema.log`）。但 `AC4.5.1` 的「應用程式的資料庫角色」在 WS 路徑仍是主帳號（見 `security-test-instructions.md` IAM 列），故即使補追溯，`AC4.5.1` 也只在 HTTP 路徑成立。
   - `AC6.1.1`（第二輪「把那張圖的資料庫換成 Aurora」作用在該張圖）：`intent-router` 標為 `Deferred` → `work-orchestrator`，而 `work-orchestrator` 的 traceability 沒有 `OK` 條目——**指派落空**。
3. **本站新增能力沒有 ID 可追溯**：F1（架構圖掛系統）、對話寫入語意記憶、本機 Claude Code provider 三項在 requirements／stories 中**沒有 FR／AC**（範圍新增，見 `test-results.md`），所以本閘門的列舉看不到它們——它們的測試掛在暫時的 `@story US9.1`／`US4.1` 上。回補 FR／AC 後須重跑本閘門。

### 目標檔不存在

0 個。腳本以正規式自 `target` 抽出第一個檔案路徑（部分 `target` 帶說明文字，如 `backend/scripts/run_hierarchy_migration.py（既有環境的遷移指令）＋…`），所有被列舉 ID 的 `OK` 條目抽出的路徑皆存在。

## 逐 ID 覆蓋

| ID | 類別 | 覆蓋 | 擁有單元 | 目標檔（取第一個；另有 N 個） | 備註 |
|---|---|---|---|---|---|
| `FR1` | 需求 | **未覆蓋** | — | — | 跨 US 推導 6/6 |
| `FR2` | 需求 | **未覆蓋** | — | — | 跨 US 推導 2/2 |
| `FR3` | 需求 | **未覆蓋** | — | — | 跨 US 推導 2/2 |
| `FR4` | 需求 | **未覆蓋** | — | — | 跨 US 推導 4/5；單元狀態：session-store=N/A |
| `FR5` | 需求 | **未覆蓋** | — | — | 跨 US 推導 2/2 |
| `FR6` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR7` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR8` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR9` | 需求 | **未覆蓋** | — | — | 跨 US 推導 2/2 |
| `FR10` | 需求 | **未覆蓋** | — | — | 跨 US 推導 2/2 |
| `FR11` | 需求 | **未覆蓋** | — | — | 跨 US 推導 4/4 |
| `FR12` | 需求 | **未覆蓋** | — | — | 跨 US 推導 5/5 |
| `FR13` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `NFR1` | 需求 | **未覆蓋** | — | — | 跨 US 推導 no-US-map；單元狀態：rbac-story-ids=N/A;session-store=N/A |
| `NFR2` | 需求 | **未覆蓋** | — | — | 跨 US 推導 no-US-map；單元狀態：rbac-story-ids=N/A;session-store=N/A |
| `NFR3` | 需求 | **未覆蓋** | — | — | 跨 US 推導 no-US-map；單元狀態：rbac-story-ids=N/A;session-store=N/A |
| `NFR4` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1；單元狀態：rbac-story-ids=N/A;session-store=N/A |
| `NFR5` | 需求 | **未覆蓋** | — | — | 跨 US 推導 no-US-map；單元狀態：rbac-story-ids=N/A;session-store=N/A |
| `NFR6` | 需求 | **未覆蓋** | — | — | 跨 US 推導 no-US-map；單元狀態：rbac-story-ids=N/A;session-store=N/A |
| `NFR7` | 需求 | **未覆蓋** | — | — | 跨 US 推導 2/2；單元狀態：rbac-story-ids=N/A;session-store=N/A |
| `NFR8` | 需求 | **未覆蓋** | — | — | 跨 US 推導 no-US-map；單元狀態：rbac-story-ids=N/A;session-store=N/A |
| `NFR9` | 需求 | **未覆蓋** | — | — | 跨 US 推導 no-US-map；單元狀態：rbac-story-ids=N/A;session-store=N/A |
| `NFR10` | 需求 | **未覆蓋** | — | — | 跨 US 推導 no-US-map；單元狀態：rbac-story-ids=N/A;session-store=N/A |
| `NFR11` | 需求 | **未覆蓋** | — | — | 跨 US 推導 no-US-map；單元狀態：rbac-story-ids=N/A;session-store=N/A |
| `FR1.1` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1；單元狀態：session-store=N/A |
| `FR1.2` | 需求 | **未覆蓋** | — | — | 跨 US 推導 2/2 |
| `FR1.3` | 需求 | **未覆蓋** | — | — | 跨 US 推導 2/2 |
| `FR1.4` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR1.5` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR1.6` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR1.7` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR1.8` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR2.1` | 需求 | **未覆蓋** | — | — | 跨 US 推導 2/2；單元狀態：session-store=N/A |
| `FR2.2` | 需求 | **未覆蓋** | — | — | 跨 US 推導 2/2 |
| `FR2.3` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR3.1` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1；單元狀態：session-store=N/A |
| `FR3.2` | 需求 | **未覆蓋** | — | — | 跨 US 推導 2/2；單元狀態：session-store=N/A |
| `FR3.3` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1；單元狀態：session-store=N/A |
| `FR4.1` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR4.2` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/2 |
| `FR4.3` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR4.3a` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR4.3b` | 需求 | **未覆蓋** | — | — | 跨 US 推導 2/2 |
| `FR4.4` | 需求 | **未覆蓋** | — | — | 跨 US 推導 0/1 |
| `FR4.5` | 需求 | OK | memory-purge | `backend/scripts/purge_expired_memory.sql` |  |
| `FR4.5a` | 需求 | OK | memory-purge | `.github/workflows/memory-retention-purge.yml` |  |
| `FR4.6` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR4.7` | 需求 | OK | memory-purge | `backend/scripts/purge_expired_memory.sql` |  |
| `FR5.1` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR5.2` | 需求 | **未覆蓋** | — | — | 跨 US 推導 2/2 |
| `FR6.1` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1；單元狀態：session-store=N/A |
| `FR7.1` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR7.2` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR7.3` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR7.4` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR8.1` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR8.2` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR8.3` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR8.4` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR8.5` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR9.1` | 需求 | OK | hierarchy-data | `schema_rbac.sql` |  |
| `FR9.2` | 需求 | OK | hierarchy-data | `backend/scripts/run_hierarchy_migration.py` |  |
| `FR9.3` | 需求 | OK | hierarchy-data | `DEPLOY.md` |  |
| `FR9.4` | 需求 | **未覆蓋** | — | — | 跨 US 推導 no-US-map；單元狀態：hierarchy-data=N/A |
| `FR9.5` | 需求 | OK | rbac-story-ids | `backend/tests/test_rbac_story_ids_seed.py` |  |
| `FR10.1` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR10.2` | 需求 | **未覆蓋** | — | — | 跨 US 推導 2/2 |
| `FR10.3` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR10.4` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR10.5` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR10.6` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR10.7` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR10.8` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR11.1` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR11.2` | 需求 | **未覆蓋** | — | — | 跨 US 推導 2/2 |
| `FR11.3` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR11.4` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR11.5` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR11.6` | 需求 | OK | mcp-bridge | `backend/tests/test_requirement_field_facade.py` |  |
| `FR12.0` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR12.1` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR12.2` | 需求 | **未覆蓋** | — | — | 跨 US 推導 3/3；單元狀態：project-meta-data=N/A |
| `FR12.3` | 需求 | OK | project-meta-data | `schema_rbac.sql` |  |
| `FR12.4` | 需求 | OK | project-meta-data | `schema_rbac.sql` |  |
| `FR12.4a` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR12.4b` | 需求 | OK | project-meta-data | `schema_rbac.sql` |  |
| `FR12.4c` | 需求 | OK | project-meta-data | `schema_rbac.sql` |  |
| `FR12.4c-i` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR12.4d` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR12.5` | 需求 | **未覆蓋** | — | — | 跨 US 推導 2/2 |
| `FR12.5a` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR12.5b` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR12.5c` | 需求 | **未覆蓋** | — | — | 跨 US 推導 no-US-map |
| `FR12.6` | 需求 | OK | project-meta-data | `schema_rbac.sql` |  |
| `FR12.6a` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1；單元狀態：rbac-story-ids=Deferred |
| `FR12.6b` | 需求 | **未覆蓋** | — | — | 跨 US 推導 no-US-map |
| `FR13.1` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR13.2` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR13.3` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `FR13.4` | 需求 | **未覆蓋** | — | — | 跨 US 推導 1/1 |
| `AC1.1.1` | AC | OK | entry-page-ui,intent-router,work-orchestrator | `backend/services/intent_routing_parser.py`（另 2） |  |
| `AC1.1.2` | AC | OK | entry-page-ui,work-orchestrator | `backend/tests/test_work_orchestrator_rules.py`（另 1） |  |
| `AC1.1.3` | AC | OK | entry-page-ui,intent-router | `backend/services/intent_routing.py`（另 1） |  |
| `AC1.1.4` | AC | OK | entry-page-ui,work-orchestrator | `backend/tests/test_work_orchestrator_flow.py`（另 1） |  |
| `AC1.1.5` | AC | OK | brain-gateway,entry-page-ui | `backend/tests/test_brain_gateway_turn.py`（另 1） |  |
| `AC10.1.1` | AC | OK | entry-page-ui,work-orchestrator | `backend/tests/test_work_orchestrator_flow.py`（另 1） |  |
| `AC1.2.1` | AC | OK | brain-ws-contract,entry-page-ui,intent-router | `backend/services/brain_ws_contract.py`（另 2） |  |
| `AC1.2.2` | AC | OK | brain-ws-contract,entry-page-ui | `backend/services/brain_ws_contract.py`（另 1） |  |
| `AC1.2.3` | AC | OK | brain-ws-contract,entry-page-ui,intent-router | `backend/services/brain_ws_contract.py`（另 2） |  |
| `AC1.2.4` | AC | OK | brain-ws-contract | `backend/services/brain_ws_contract.py` |  |
| `AC1.3.1` | AC | OK | entry-page-ui,work-orchestrator | `backend/tests/test_work_orchestrator_flow.py`（另 1） |  |
| `AC1.3.2` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC1.3.3` | AC | OK | entry-page-ui,work-orchestrator | `backend/tests/test_work_orchestrator_flow.py`（另 1） |  |
| `AC1.4.1` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC1.4.2` | AC | OK | entry-page-ui,rbac-story-ids | `backend/services/rbac_seed_data.py`（另 1） |  |
| `AC1.4.3` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC1.4.4` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC2.1.1` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC2.1.2` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC2.1.3` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC2.1.4` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC2.2.1` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC2.2.2` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC2.2.3` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC3.1.1` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC3.1.2` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC3.1.3` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC3.1.4` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC4.1.1` | AC | OK | memory-service | `backend/services/memory_facade.py` |  |
| `AC4.1.2` | AC | OK | memory-service | `backend/services/memory_service.py` |  |
| `AC4.1.3` | AC | OK | memory-service | `backend/services/memory_router.py` |  |
| `AC4.4.1` | AC | OK | memory-page-ui,memory-service | `backend/services/memory_facade.py`（另 1） |  |
| `AC4.4.2` | AC | OK | memory-service | `backend/services/memory_router.py` |  |
| `AC4.4.3` | AC | OK | memory-page-ui,memory-service | `backend/services/memory_service.py`（另 1） |  |
| `AC4.5.1` | AC | **未覆蓋** | — | — | 單元狀態：memory-data=N/A |
| `AC4.5.2` | AC | **未覆蓋** | — | — | 單元狀態：memory-data=N/A |
| `AC4.5.3` | AC | **未覆蓋** | — | — | 單元狀態：memory-data=N/A |
| `AC4.2.1` | AC | OK | memory-page-ui,memory-service | `backend/services/memory_facade.py`（另 1） |  |
| `AC4.2.2` | AC | OK | memory-service | `backend/services/memory_service.py` |  |
| `AC4.2.3` | AC | OK | memory-purge,memory-service | `backend/scripts/purge_expired_memory.sql`（另 1） |  |
| `AC4.3.1` | AC | OK | memory-service | `backend/services/memory_service.py` |  |
| `AC4.3.2` | AC | OK | memory-service | `backend/services/memory_service.py` |  |
| `AC4.3.3` | AC | OK | memory-service | `backend/services/memory_facade.py` |  |
| `AC8.1.2` | AC | OK | brain-gateway | `backend/tests/test_brain_gateway_handshake.py` |  |
| `AC5.1.1` | AC | OK | entry-page-ui,intent-router,work-orchestrator | `backend/services/intent_routing_predicate.py`（另 2） |  |
| `AC5.1.2` | AC | OK | entry-page-ui,work-orchestrator | `backend/tests/test_work_orchestrator_flow.py`（另 1） |  |
| `AC5.1.3` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC6.1.1` | AC | **未覆蓋** | — | — | 單元狀態：intent-router=Deferred;session-store=N/A |
| `AC6.1.2` | AC | OK | intent-router | `backend/tests/test_intent_routing_predicate.py` |  |
| `AC6.1.3` | AC | OK | intent-router | `backend/services/intent_routing.py` |  |
| `AC7.1.1` | AC | OK | brain-gateway | `backend/tests/test_brain_gateway_fanout.py` |  |
| `AC7.1.2` | AC | OK | brain-gateway | `backend/tests/test_brain_gateway_fanout.py` |  |
| `AC7.1.3` | AC | OK | brain-gateway | `backend/tests/test_brain_gateway_fanout.py` |  |
| `AC8.1.1` | AC | OK | brain-ws-contract,entry-page-ui | `backend/services/brain_ws_contract.py`（另 1） |  |
| `AC8.1.3` | AC | OK | brain-gateway,entry-page-ui | `backend/tests/test_brain_gateway_handshake.py`（另 1） |  |
| `AC8.1.4` | AC | OK | brain-gateway,entry-page-ui | `backend/main.py`（另 1） |  |
| `AC9.1.1` | AC | OK | entry-page-ui | `backend/tests/test_describe_work_target.py` |  |
| `AC9.1.2` | AC | OK | hierarchy-data | `backend/services/hierarchy_migration.py` |  |
| `AC9.1.3` | AC | OK | entry-page-ui,hierarchy-data | `backend/tests/test_hierarchy_migration.py`（另 1） |  |
| `AC9.1.4` | AC | OK | hierarchy-data | `backend/services/hierarchy_migration.py` |  |
| `AC9.2.1` | AC | OK | hierarchy-service,object-picker-ui | `backend/tests/test_hierarchy_service.py`（另 1） |  |
| `AC9.2.2` | AC | OK | hierarchy-service,object-picker-ui | `backend/tests/test_hierarchy_service.py`（另 1） |  |
| `AC9.2.3` | AC | OK | hierarchy-service,rbac-story-ids | `backend/services/rbac_seed_data.py`（另 1） |  |
| `AC10.1.2` | AC | OK | entry-page-ui,work-orchestrator | `backend/tests/test_work_orchestrator_flow.py`（另 1） |  |
| `AC10.1.3` | AC | OK | entry-page-ui,work-orchestrator | `backend/tests/test_work_orchestrator_flow.py`（另 1） |  |
| `AC10.1.4` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC10.1.5` | AC | OK | entry-page-ui,work-orchestrator | `backend/tests/test_work_orchestrator_authz.py`（另 1） |  |
| `AC10.2.1` | AC | OK | entry-page-ui,work-orchestrator | `backend/tests/test_work_orchestrator_flow.py`（另 1） |  |
| `AC10.2.2` | AC | OK | entry-page-ui,work-orchestrator | `backend/tests/test_work_orchestrator_flow.py`（另 1） |  |
| `AC10.2.3` | AC | OK | entry-page-ui,work-orchestrator | `backend/tests/test_work_orchestrator_flow.py`（另 1） |  |
| `AC10.2.4` | AC | OK | entry-page-ui | `frontend/tests/e2e/entry-page.spec.ts` |  |
| `AC11.1.1` | AC | OK | project-pages-ui | `frontend/tests/e2e/project-pages.spec.ts` |  |
| `AC11.1.2` | AC | OK | project-pages-ui | `frontend/tests/e2e/project-pages.spec.ts` |  |
| `AC11.1.3` | AC | OK | hierarchy-service,project-pages-ui | `backend/services/hierarchy_router.py`（另 1） |  |
| `AC11.2.1` | AC | OK | project-pages-ui,requirement-field-service | `backend/tests/test_requirement_field_facade.py`（另 1） |  |
| `AC11.2.2` | AC | OK | project-meta-data,project-pages-ui,requirement-field-service | `backend/tests/test_requirement_field_facade.py`（另 2） |  |
| `AC11.2.3` | AC | OK | project-pages-ui,requirement-field-service | `backend/tests/test_requirement_field_facade.py`（另 1） |  |
| `AC11.3.1` | AC | OK | project-pages-ui,requirement-field-service | `backend/tests/test_requirement_field_facade.py`（另 1） |  |
| `AC11.3.2` | AC | OK | project-pages-ui,requirement-field-service | `backend/tests/test_requirement_field_facade.py`（另 1） |  |
| `AC11.3.3` | AC | OK | project-pages-ui,requirement-field-service | `backend/tests/test_requirement_field_http.py`（另 1） |  |
| `AC11.4.1` | AC | OK | mcp-bridge,project-pages-ui | `backend/tests/test_mcp_bridge_e2e.py`（另 1） |  |
| `AC11.4.2` | AC | OK | mcp-bridge | `backend/tests/test_mcp_bridge_artifacts.py` |  |
| `AC11.4.3` | AC | OK | mcp-bridge | `backend/tests/test_mcp_bridge_e2e.py` |  |
| `AC12.1.1` | AC | OK | member-pages-ui,membership-service | `backend/tests/test_membership_endpoints.py`（另 1） |  |
| `AC12.1.2` | AC | OK | membership-service | `backend/tests/test_membership_endpoints.py` |  |
| `AC12.1.3` | AC | OK | project-pages-ui | `backend/tests/test_project_visibility_endpoints.py` |  |
| `AC12.2.1` | AC | OK | member-pages-ui,membership-service | `backend/tests/test_membership_endpoints.py`（另 1） |  |
| `AC12.2.2` | AC | OK | project-meta-data | `schema_rbac.sql` |  |
| `AC12.2.3` | AC | OK | member-pages-ui,membership-service | `backend/services/membership_facade.py`（另 1） |  |
| `AC12.2.4` | AC | OK | membership-service | `backend/tests/test_membership_facade.py` |  |
| `AC12.3.1` | AC | OK | membership-service | `backend/tests/test_membership_facade.py` |  |
| `AC12.3.2` | AC | OK | membership-service | `backend/tests/test_membership_endpoints.py` |  |
| `AC12.3.3` | AC | OK | membership-service | `backend/tests/test_membership_endpoints.py` |  |
| `AC12.4.1` | AC | OK | membership-service | `backend/tests/test_membership_facade.py` |  |
| `AC12.4.2` | AC | OK | membership-service | `backend/tests/test_membership_facade.py` |  |
| `AC12.4.3` | AC | OK | member-pages-ui | `frontend/src/components/Layout.tsx` |  |
| `AC12.4.4` | AC | OK | member-pages-ui | `frontend/src/components/membership/ReselectionBanner.tsx` |  |
| `AC12.5.1` | AC | OK | member-pages-ui,membership-service | `backend/services/membership_errors.py`（另 1） |  |
| `AC12.5.2` | AC | OK | membership-service,project-pages-ui | `backend/tests/test_membership_endpoints.py`（另 2） |  |
| `AC12.5.3` | AC | OK | member-pages-ui,membership-service | `backend/tests/test_membership_facade.py`（另 1） |  |
| `AC12.6.2` | AC | OK | member-pages-ui,membership-service | `backend/tests/test_membership_facade.py`（另 1） |  |
| `AC12.6.1` | AC | OK | member-pages-ui,membership-service | `backend/tests/test_membership_facade.py`（另 1） |  |
| `AC12.6.3` | AC | OK | project-pages-ui | `backend/tests/test_project_visibility_endpoints.py` |  |
| `AC13.1.1` | AC | OK | progress-channel | `backend/tests/test_progress_channel.py` |  |
| `AC13.1.2` | AC | OK | progress-channel | `backend/tests/test_progress_channel.py` |  |
| `AC13.1.3` | AC | OK | progress-channel | `backend/services/design_agent.py` |  |

## 未覆蓋清單（91）

- `FR1`
- `FR2`
- `FR3`
- `FR4`
- `FR5`
- `FR6`
- `FR7`
- `FR8`
- `FR9`
- `FR10`
- `FR11`
- `FR12`
- `FR13`
- `NFR1`
- `NFR2`
- `NFR3`
- `NFR4`
- `NFR5`
- `NFR6`
- `NFR7`
- `NFR8`
- `NFR9`
- `NFR10`
- `NFR11`
- `FR1.1`
- `FR1.2`
- `FR1.3`
- `FR1.4`
- `FR1.5`
- `FR1.6`
- `FR1.7`
- `FR1.8`
- `FR2.1`
- `FR2.2`
- `FR2.3`
- `FR3.1`
- `FR3.2`
- `FR3.3`
- `FR4.1`
- `FR4.2`
- `FR4.3`
- `FR4.3a`
- `FR4.3b`
- `FR4.4`
- `FR4.6`
- `FR5.1`
- `FR5.2`
- `FR6.1`
- `FR7.1`
- `FR7.2`
- `FR7.3`
- `FR7.4`
- `FR8.1`
- `FR8.2`
- `FR8.3`
- `FR8.4`
- `FR8.5`
- `FR9.4`
- `FR10.1`
- `FR10.2`
- `FR10.3`
- `FR10.4`
- `FR10.5`
- `FR10.6`
- `FR10.7`
- `FR10.8`
- `FR11.1`
- `FR11.2`
- `FR11.3`
- `FR11.4`
- `FR11.5`
- `FR12.0`
- `FR12.1`
- `FR12.2`
- `FR12.4a`
- `FR12.4c-i`
- `FR12.4d`
- `FR12.5`
- `FR12.5a`
- `FR12.5b`
- `FR12.5c`
- `FR12.6a`
- `FR12.6b`
- `FR13.1`
- `FR13.2`
- `FR13.3`
- `FR13.4`
- `AC4.5.1`
- `AC4.5.2`
- `AC4.5.3`
- `AC6.1.1`
