# 建置與測試摘要（261116-brain-create-diagram）

> 撰寫時間 2026-11-22T14:21:37Z。測試策略 Standard、方法 test-after（Testing Contract）。執行結果與指令輸出見 `test-results.md`。

## 整體狀態

- **建置：成功。** 前端 lint（0 errors）、build（含 `tsc -b`）、型別一致檢查、OpenAPI／WS 契約 `--check`、repo 與環境 contract 全部通過。
- **測試：全部通過。** 後端全套、Playwright（本機替身版）、本機一次性 PostgreSQL 17 的遷移驗證皆綠。
- **本站判定：失敗（依 stage 定義）。** NFR1 與 NFR2 為 `Unverified`：需要部署到 staging 的這版程式與真實路由模型，本機無法量測，且本計畫在本站之後沒有承接量測的 stage。依 stage 規則，任何 `Unverified` 目標都讓本站不算成功，交由使用者在關卡決定。

## 測試類型清單

| 類型 | 檔案 | 產生原因 |
|---|---|---|
| 建置 | `build-instructions.md` | 必產 |
| 整合 | `integration-test-instructions.md` | Standard 策略必產；含 PostgreSQL 遷移驗證 |
| 效能／準確率 | `performance-test-instructions.md` | requirements 有 NFR1／NFR2 量化目標 |
| 安全 | `security-test-instructions.md` | ADR-0006 四面向逐項對照（`project.md` 強制） |
| 跨單元追溯 | `cross-unit-traceability.md` | 必產 |

## 各單元覆蓋期望

| 單元 | 承載測試 | 期望 |
|---|---|---|
| `diagram-drafts` | `test_diagram_drafts_{schema,hierarchy,api}.py`、`test_diagram_system_attach.py`、`test_work_orchestrator_store.py` | 回應 `response_model` 欄位集合、409 四入口、遷移與啟動補丁、`include_drafts` 必填與排序 |
| `brain-create-flow` | `test_brain_diagram_creation.py`（PBT）、`test_brain_diagram_creation_flow.py`、`test_intent_routing_decisions.py`、`test_work_orchestrator_{rules,flow}.py`、`test_brain_gateway_startup.py` | 判定表與四項性質（ADR-0006 agent routing PBT）、取名性質、冪等三案、權限雙向、四種反問 |
| `draft-ui` | `frontend/tests/e2e/diagram-drafts.spec.ts` | 草稿標示、計數排除、手動存檔轉正式、`pick_system` 可點選、評核頁 409 顯示文字 |

## Target Verification Matrix

| Target ID | Source | Expected | Actual | Evidence | Owning Stage | Verdict |
|---|---|---|---|---|---|---|
| TC-SUITE | `code-generation-plan.md` `## Testing Contract`（bugfix：既有測試保持綠燈＋回歸測試） | 後端全套 0 失敗 | 見 `test-results.md` §2 | `backend/.venv/bin/python -m unittest discover -s tests` | build-and-test | Met |
| TC-FE | 同上；`team.md` 前端 lint 結構約束 | lint 0 errors、build 成功、型別一致 | 0 errors／成功／一致 | `test-results.md` §1 | build-and-test | Met |
| NFR1 | `requirements.md` NFR1 | 60 句標註集＋≥10 句新標註，準確率 ≥ 80% | 未量測 | 需 staging；`performance-test-instructions.md` §2 | 無（本計畫無承接 stage） | Unverified |
| NFR2 | `requirements.md` NFR2 | 首字 P50 ≤ 2000 ms（伺服器端） | 未量測（結構前提：路由請求只發一次，已測） | 需 staging；`performance-test-instructions.md` §2 | 無（本計畫無承接 stage） | Unverified |
| NFR3 | `requirements.md` NFR3 | 重試、復原掃描、再說一次三案皆不建第二張 | 三案皆綠 | `test_brain_diagram_creation_flow.py`（`@story NFR3` 四案） | build-and-test | Met |
| NFR4 | `requirements.md` NFR4 | 判定類別入日誌、不含原文與圖名 | 綠；兩項突變（寫入原文、拿掉類別）皆紅 | `test_decision_is_logged_by_category_without_utterance_or_title`（本站新增） | build-and-test | Met |
| NFR5 | `requirements.md` NFR5（`team.md` A／B／C） | TestClient 回應欄位、Playwright 草稿標示、權限 allow／deny | 皆有且綠 | `test_diagram_drafts_api.py`、`diagram-drafts.spec.ts`、`test_without_arch_edit_nothing_is_created` | build-and-test | Met |
| FR6.5-PG | `requirements.md` FR6.5；code-generation 移交「PostgreSQL 遷移未驗證」 | 既有列補成 ready、可重跑、空 volume 可建、CHECK 生效 | 全部成立 | `test-results.md` §3 | build-and-test | Met |

## 準備度評估

- **可建置：是。**
- **可測試：是**（本機能跑的全部通過）。
- **可部署：有條件。** 程式與遷移已驗證；NFR1／NFR2 只能在部署到 staging 之後量測。本 repo 為 deploy-on-merge，合併進 `ut` 即上 staging。

## 本站依 code-generation 關卡裁決帶入的修正

使用者在 code-generation 關卡核可時指示帶到本站處理；以下為**原始碼變更**，不只是測試：

1. 新增「補欄位失敗必須讓啟動失敗」的兩個測試（函式層與 `init_db` 層），各做一次突變驗證。
2. 非架構權的 403 文字改為指向平台管理者檢查角色權限（使用者裁決）；同步改測試斷言。
3. 建圖回 404 改用永久性失敗的文字（新增 `CREATE_NOT_FOUND_MESSAGE`）並補測試與突變驗證。
4. 逾時後 INSERT 可能晚到落地的已知限制，寫進 `brain_gateway.py` 註解。
5. `DEPLOY.md` 的啟動補丁計數（三處）與一處「全部吞成警告」的敘述；`models.py`、`schema_rbac.sql`、`hierarchy_migration.py`、`run_hierarchy_migration.py` 的過期註解。
6. `WorkspacePage.tsx` 的 `updated_at` 與 `AssessmentPage.tsx` 的 `diagram_status` 改由產生型別推導。
7. **另加（非裁決清單內）**：PostgreSQL 實測發現 `ORDER BY updated_at DESC` 在 PostgreSQL 與 SQLite 排 NULL 的位置相反，改為 `NULLS LAST` 並補測試（含突變驗證）。
8. **另加**：NFR4 原本只有實作沒有斷言，補測試。

**未處理**：頂部作業對象列的草稿標示——需要在 WS 作業對象訊框加欄位，是契約變更，不在本站做；於關卡請使用者決定。

## 已知限制與待辦

- NFR1／NFR2 未量測（見上）。
- Playwright 只在本機替身版跑過，**未在 CI stack 上跑**。
- 建圖逾時後 INSERT 可能晚到落地：多一張草稿或缺一筆變更紀錄的窗口存在，未以真實 threadpool 路徑測試。
- 兩個分頁同時說要畫圖，可能各建一張草稿。
- FR3.5 的說明句因契約無文字欄位而未呈現。
- 系統挑選反問不排除使用者無專案編輯權的系統。
- PostgreSQL 驗證未跑完整 `schema_rbac.sql`（本機無 pgvector、無 psycopg2）。
