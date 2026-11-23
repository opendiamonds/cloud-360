# 自動化測試計畫 — 261116-brain-create-diagram（大腦直接建立新架構圖）

> 本 intent 未執行 user-stories（bugfix scope），盤點以 `requirements.md` 的 FR／NFR 為單位。來源：
> `requirements.md`、`construction/build-and-test/build-and-test-summary.md` 與同目錄的測試說明、
> 三個單元的 `code-generation/code-summary.md`。

## 1. 覆蓋盤點

每一項外部可觀察行為只落在一個桶。「已自動化」欄的測試名稱皆可在 repo 中找到（`tcms_validate.py` 已核對）。

| # | 外部可觀察行為 | 桶 | 承載（檔案::類別::方法） |
|---|---|---|---|
| 1 | 系統下沒有圖時說要畫圖 → 建一張草稿、作業對象切到它、交辦架構設計（FR1.1、FR1.2、FR1.3） | 已自動化 | `backend/tests/test_brain_diagram_creation_flow.py::CreateFlowTest::test_system_without_diagrams_creates_one_draft_switches_and_dispatches` |
| 2 | 同一工作項重試、復原掃描、再說一次都不建第二張（FR1.4、FR6.3、NFR3） | 已自動化 | 同檔 `::CreateFlowTest::test_saying_it_again_continues_the_same_draft`、`::OrchestratorFinalizeTest::test_successful_store_back_sends_finalize_and_never_creates` |
| 3 | 判定表（新建／修改／反問）與四項性質（互斥、不明必反問、對 p 單調、決定性）（FR2.2、FR2.3） | 已自動化 | `backend/tests/test_brain_diagram_creation.py::DecideTableTest`、`::DecidePropertiesTest`（hypothesis） |
| 4 | 「是否要新的一張」併入同一次路由請求（FR2.2、NFR2 結構前提） | 已自動化 | `test_brain_diagram_creation_flow.py::RoutingTest::test_new_question_rides_on_the_single_routing_request` |
| 5 | 沒有圖卻要修改 → 回覆並反問是否新建（FR2.4） | 已自動化 | `test_brain_diagram_creation.py::DecideTableTest::test_system_without_diagrams` |
| 6 | 意圖反問選定後保留「新的一張」機率（修訂 1 Step 22） | 已自動化 | `test_brain_diagram_creation_flow.py::ClarifyFlowTest::test_intent_clarify_keeps_the_new_diagram_probability` |
| 7 | 沒有作業對象或只有專案 → 反問挑系統，點選後建立（FR3.1、FR3.4） | 已自動化 | `::ClarifyFlowTest::test_pick_system_lists_owned_systems_and_selection_creates`；前端 `frontend/tests/e2e/diagram-drafts.spec.ts` › `lets the user pick a system from the brain clarify` |
| 8 | 多張圖要修改 → 反問哪一張；失效候選被拒並重列（FR3.2、FR3.5） | 已自動化 | `::ClarifyFlowTest::test_pick_diagram_for_modify_and_a_stale_candidate_is_relisted` |
| 9 | 名下沒有系統 → 回覆專案頁路徑（FR3.3） | 已自動化 | `::ClarifyFlowTest::test_no_systems_replies_with_project_page_path` |
| 10 | 候選超過 10 筆只列 10 筆並說明；排序新到舊再依 id（FR3.6） | 已自動化 | `::ClarifyFlowTest::test_more_than_ten_candidates_lists_ten_with_a_note`；`test_diagram_drafts_hierarchy.py::ListDiagramsOfSystemDraftsTest::test_order_is_newest_first_with_id_descending_tie_break`、`::test_diagrams_without_updated_at_sort_last_on_every_dialect` |
| 11 | 有草稿時先反問接續哪張或新建（FR6.3a） | 已自動化 | `::ClarifyFlowTest::test_resume_draft_or_new_comes_first_when_a_draft_exists` |
| 12 | 判定不明 → 反問新建或修改，選新建即建立（FR2.1） | 已自動化 | `::ClarifyFlowTest::test_new_or_modify_when_unclear_and_create_choice_creates` |
| 13 | 無架構編輯權 → 不建、回說明（FR4.1、NFR5 deny）；有權 → 建立（NFR5 allow） | 已自動化 | `::CreateFlowTest::test_without_arch_edit_nothing_is_created`；`test_diagram_drafts_api.py::CreatePermissionTest::test_arch_edit_allows_and_k1_only_is_denied` |
| 14 | 403 依來源分流文字；404 回永久性失敗文字（FR4.1） | 已自動化 | `::CreateFlowTest::test_forbidden_403_text_depends_on_its_source`、`::test_create_404_is_reported_as_permanent_not_retry_later`；`::CapabilityClientTest::test_forbidden_is_classified_by_its_source` |
| 15 | 建圖逾時不重試、不交辦，連線仍可處理下一則（契約 C5） | 已自動化 | `::CreateFlowTest::test_create_timeout_is_not_retried_and_not_dispatched`、`::test_create_that_hangs_times_out_and_the_connection_keeps_working` |
| 16 | 取名：去指令詞、長度與 code point 上限、不切組合字元、重名加序號、空主題用系統名（FR5.1～FR5.4） | 已自動化 | `test_brain_diagram_creation.py::MakeTitleTest`（含 hypothesis 性質） |
| 17 | 建圖端點 `as_draft`、存檔 `finalize`、四支端點回 `diagram_status` 與契約欄位集合（FR6.1、FR6.2、C1～C3） | 已自動化 | `test_diagram_drafts_api.py::CreateAndReadTest`、`::FinalizeTest` |
| 18 | 草稿被拒：評核、寫回評核、WA 共編、分享、估價綁自己的草稿皆 409 且資料不變（FR6.4a、C4） | 已自動化 | `test_diagram_drafts_api.py::DraftRejectedTest`、`::EstimateBindingTest` |
| 19 | 上述五個端點在 OpenAPI 宣告 409（C4） | **待自動化 → 本站已寫** | `test_diagram_drafts_api.py::DraftRejectionIsDeclaredInOpenApiTest::test_every_draft_rejecting_endpoint_declares_409` |
| 20 | 大腦產圖存回帶 `finalize=true` 轉正式；產圖失敗維持草稿（FR6.2、FR6.3） | 已自動化 | `test_brain_diagram_creation_flow.py::OrchestratorFinalizeTest`（兩案）、`::CapabilityClientTest::test_create_draft_then_finalize_turns_it_ready` |
| 21 | `draft_rejected` 只在常數 409 時為真；`PHRASES` 與常數相等（C4） | 已自動化 | `::CapabilityClientTest::test_draft_rejected_is_true_only_for_the_constant_409`、`::PhrasesTest::test_draft_rejected_phrase_equals_the_endpoint_constant` |
| 22 | 判斷「底下有沒有圖」時包含草稿：刪系統、清預設專案（FR6.4b、FR6.4c） | 已自動化 | `test_diagram_drafts_hierarchy.py::DraftsCountAsDiagramsTest`（兩案）、`::ListDiagramsOfSystemDraftsTest::test_include_drafts_is_required_at_both_layers` |
| 23 | 前端：專案頁、掛圖下拉、評核頁標示草稿；計數排除草稿；只有「儲存架構圖」轉正式；評核頁顯示 409 文字（FR6.2、FR6.4、FR6.4a） | 已自動化 | `frontend/tests/e2e/diagram-drafts.spec.ts` 五案 |
| 24 | 經大腦建立寫一筆變更紀錄，失敗只記 log（FR7.1） | 已自動化 | `test_brain_diagram_creation.py::RecordCreationTest`（兩案） |
| 25 | 判定類別入日誌、不含原文與圖名（NFR4） | 已自動化 | `test_brain_diagram_creation_flow.py::CreateFlowTest::test_decision_is_logged_by_category_without_utterance_or_title` |
| 26 | 欄位遷移：既有圖為 ready、可重跑、CHECK 生效；啟動補丁只補一欄、失敗即讓啟動失敗（FR6.5） | 已自動化 | `test_diagram_drafts_schema.py::TestDiagramStatusMigration`、`::TestDiagramStatusStartupPatch`（含兩個失敗傳遞案） |
| 27 | `_reread_target` 比對圖目標（C7） | 已自動化 | `test_brain_diagram_creation_flow.py::RereadTargetTest::test_reread_compares_the_diagram` |
| 28 | 真實模型下主路徑：沒有圖的系統說要畫圖 → 草稿 → 產圖 → 轉正式 | 只能手動 | `manual-test-cases.md` 第 1 案（每跑一次花模型用量） |
| 29 | 真實模型對新建／修改／不明句子的判定落在對的區間（FR2.1；NFR1 的抽樣） | 只能手動 | `manual-test-cases.md` 第 2 案（同上） |
| 30 | 舊 PostgreSQL volume ＋ 新 backend 啟動自行補欄（FR6.5） | 只能手動 | `manual-test-cases.md` 第 3 案（需要已有歷史資料的真實環境） |
| 31 | NFR1 判定準確率 ≥ 80%、NFR2 首字 P50 ≤ 2 秒 | 只能手動 | 合併部署後於 staging 量測（`build-and-test/performance-test-instructions.md` §2）；觸發量測執行須另取得使用者同意 |

**計數**：已自動化 26、待自動化 1（本站已寫出並跑綠）、只能手動 4（其中 3 項寫成手動案例，第 31 項是部署後的量測程序，不是可重複執行的測案）。未分類 0。

**不是行為、未列入盤點**：大腦建立草稿後，頂部作業對象列的架構圖層不顯示「草稿」標示——這是**尚未實作**的呈現（需在 WS 作業對象訊框加欄位，屬契約變更），沒有可測的行為；於關卡請使用者決定。

## 2. 本站寫出的腳本

| 落點 | 測試 | 斷言 | 突變 | 結果 |
|---|---|---|---|---|
| Backend HTTP 契約（`team.md` 規則 B） | `backend/tests/test_diagram_drafts_api.py::DraftRejectionIsDeclaredInOpenApiTest::test_every_draft_rejecting_endpoint_declares_409` | 五個拒收草稿的端點在 `app.openapi()` 的 `responses` 皆含 `"409"` | 拿掉 `POST /api/architecture/reviews` 的 `responses=DRAFT_REJECTED_RESPONSE` | 紅（`path='/api/architecture/reviews'`）；還原後綠 |

伴隨的原始碼變更：`models.DRAFT_REJECTED_RESPONSE`，並在 `review_router.py`（兩支）、`agent_router.py`、`collab_router.py`（分享）、`cost/estimate_intake_router.py` 宣告；重產 `openapi.json` 與 `frontend/src/types/api.d.ts`。起因是 `tcms_validate.py` 對 `diagram-drafts.spec.ts` 報 WARN「`POST /api/architecture/reviews` 的 OpenAPI 未宣告 409」——依撰寫標準 §6，這是真實的文件落差，不得無視。

## 3. 前一站（build-and-test）寫出、本站沿用的腳本與突變結果

| 測試 | 突變 | 結果 |
|---|---|---|
| `test_diagram_drafts_schema.py::TestDiagramStatusStartupPatch::test_startup_patch_failure_propagates_instead_of_being_swallowed` | 拿掉 `raise` | 紅；還原綠 |
| `::TestDiagramStatusStartupPatch::test_init_db_fails_when_the_status_patch_fails` | `init_db` 以 `try/except: pass` 包住補丁 | 紅；還原綠 |
| `test_brain_diagram_creation_flow.py::CreateFlowTest::test_create_404_is_reported_as_permanent_not_retry_later` | 拿掉 404 分支 | 紅；還原綠 |
| `test_diagram_drafts_hierarchy.py::ListDiagramsOfSystemDraftsTest::test_diagrams_without_updated_at_sort_last_on_every_dialect` | 拿掉 `.nulls_last()` | 紅；還原綠 |
| `test_brain_diagram_creation_flow.py::CreateFlowTest::test_decision_is_logged_by_category_without_utterance_or_title` | 日誌寫入原文；拿掉 `category` | 兩次皆紅；還原綠 |

code-generation 修訂 1 的突變表見 `construction/code-generation/code-summary.md`。

## 4. 規格註解

本站與前一站新增的測試皆帶 `@purpose`／`@given`／`@step`／`@pass`／`@story`；`diagram-drafts.spec.ts` 的五案帶 `@api`／`@ui`。`python3 scripts/tcms_validate.py --spec frontend/tests/e2e/diagram-drafts.spec.ts` → `通過 5/5 ERROR 0 WARN 0`。

## 5. 未寫出腳本的項目

無。第 28～31 項屬「只能手動」，理由見盤點表。

## 6. 執行

```
cd backend && .venv/bin/python -m unittest discover -s tests
cd frontend && npm run build && npx vite preview --port 4173 --strictPort
BASE_URL=http://localhost:4173 npx playwright test tests/e2e/diagram-drafts.spec.ts
```

Playwright 僅在本機替身版跑過，**未在 CI stack 上跑**；這五案進 TCMS 要等它們第一次在 CI 的 `ui-regression` 執行之後（見 `tcms-sync-report.md`）。

## 7. 本站結束時的全套結果

- 後端：`Ran 1619 tests in 140.816s` — `OK (skipped=3)`（build-and-test 結束時為 1618，本站新增 1）。
- 前端：`npm run lint` 0 errors（2 個既存警告）；`npm run build` 成功；`npm run check:types` 一致；`dump_openapi.py --check` 一致。
- `validate_repo_contract.py`、`validate_env_contract.py`：passed。
