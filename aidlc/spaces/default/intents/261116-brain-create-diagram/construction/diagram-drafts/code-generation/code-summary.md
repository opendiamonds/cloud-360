# Code Summary — U1 diagram-drafts

> 全部單元的總覽、完整測試結果與部署前置見 `../../code-generation/code-summary.md`。分支 `danniel/feat/brain-create-diagram`，未 commit。

## 檔案

| 檔案 | 改動 |
|---|---|
| `backend/models.py` | `UserDiagram.status`（`draft`／`ready`、非空、預設 `ready`、`ck_user_diagrams_status`）；常數 `DIAGRAM_STATUS_*`、`DRAFT_REJECTED_DETAIL` |
| `backend/services/hierarchy_migration.py` | `_ensure_diagram_status_column`（由 `_ensure_hierarchy_schema` 呼叫；inspector 判斷、同一條敘述加欄＋CHECK） |
| `schema_rbac.sql` | `ADD COLUMN IF NOT EXISTS status` ＋ `pg_constraint` 守門的 CHECK ＋ COMMENT ＋ 驗證範例、檔頭清單 |
| `DEPLOY.md` | 表格加列、2.2.7 加欄位說明與「草稿狀態欄位」小節（升級順序、驗證、回復） |
| `backend/services/hierarchy_service.py` | `list_diagrams_of_system(include_drafts=…)` 必填、回四元組、新到舊；刪除系統檢查註明含草稿 |
| `backend/services/hierarchy_facade.py` | facade 同步；`record_diagram_change` docstring 修訂 K-07 並寫明出處（契約 C5） |
| `backend/services/work_orchestrator.py` | 呼叫端改 `include_drafts=True`；存回送 `finalize=True`；`failure_for_status` 帶 `draft_rejected` |
| `backend/services/user_router.py` | 清除預設專案、刪除使用者兩處註明含草稿（行為不變） |
| `backend/services/collab_router.py` | `as_draft`、`finalize`、四支端點的 `response_model`（`DiagramCreated`／`DiagramSaved`／`MyDiagramItem`／`DiagramDetail`）、`diagram_status`、`reject_if_draft`、分享回 409 |
| `backend/services/review_router.py`、`agent_router.py` | 評核（兩處）與 WA 共編拒絕草稿 |
| `backend/cost/estimate_intake_router.py` | 估價綁圖：圖存在、屬於呼叫者且為草稿才回 409（擁有權優先） |
| `openapi.json`、`frontend/src/types/api.d.ts` | 重新產生 |

## 本單元的測試

- 22 個後端測試（schema 5、hierarchy 5、API 12）＋ 同步既有測試；執行指令見 `unit-test-instructions.md`。
- 後端全套變更後 `Ran 1601 tests … OK (skipped=3)`（stage 層級實跑結果）。

## 與計畫的偏差

- **遷移不用 `ADD COLUMN IF NOT EXISTS`**：SQLite 不支援；改以 inspector 判斷、同一條敘述加欄＋CHECK（與 `system_id` 同形）。`schema_rbac.sql`（PostgreSQL）仍用 `IF NOT EXISTS`。
- **`DRAFT_REJECTED_DETAIL` 放在 `models.py`**：`work_orchestrator_rules` 為純函式層、不得 import `models`（AST 測試鎖住），故 `PHRASES` 存同字串並以測試鎖相等。

## 修訂 1（2026-11-19 核可關卡要求修改；計畫 Step 20）

來源：本單元審查 `reviews/review-01.md` 的 R-01（Major）與 R-03；整體審查 R-01。使用者裁決：backend 啟動時只補該欄位。

| 檔案 | 改動 |
|---|---|
| `backend/database.py` | 新增 `_ensure_diagram_status_schema()`，由 `init_db()` 在 `_ensure_last_activity_schema()` 之後呼叫：inspector 判斷，欄位已在即不動；缺欄時只借用 `hierarchy_migration._ensure_diagram_status_column()` 補這一欄（同一條敘述含 `NOT NULL DEFAULT 'ready'` 與 CHECK），**不跑整套階層遷移**。與其他 `_ensure_*` 不同，失敗會往外拋讓啟動失敗（缺欄位時讀圖必然 500） |
| `backend/services/hierarchy_migration.py` | `_ensure_diagram_status_column` docstring 註明兩個呼叫端（啟動補丁是本模組「不掛啟動路徑」的唯一例外） |
| `DEPLOY.md` | 表格 H 列與「草稿狀態欄位」小節改寫：不再要求手動跑 `run_hierarchy_migration.py`，改述啟動補丁與其失敗行為；回復段補「舊版 backend 看不到草稿狀態、沒有任何 409 檢查」與回退前的處置查詢（審查 R-03） |
| `LOCAL-DEV.md` | `_ensure_*` 由七支改為八支並說明第八支；「啟動時該看到什麼」加一行（`project.md` 規則：動到 `database.py` 啟動補丁須同步） |
| `backend/tests/test_diagram_drafts_schema.py` | `TestDiagramStatusStartupPatch` 4 案：舊表補成 ready、重跑冪等且保留草稿、不改寫 `system_id` 也不建專案（證明沒跑整套遷移）、`init_db` 確實呼叫補丁 |

突變：拿掉 `init_db` 內的呼叫 → `test_init_db_calls_the_status_patch` 紅；還原後 9 tests OK。

未處理（不在 Step 20 範圍）：審查 R-02（PostgreSQL 實跑遷移）留給 build-and-test；R-04（`updated_at` 為 NULL 的排序在兩種方言不同）未改。
