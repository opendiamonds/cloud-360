# Code Generation Plan — U1 diagram-drafts

## Summary

- Builds: 架構圖草稿狀態欄位與遷移、建圖可建草稿、存檔轉正式、四支端點的回應型別與 diagram_status、草稿被拒的 409、列圖的含不含草稿參數
- Touches: backend/models.py、services/{hierarchy_migration,hierarchy_service,hierarchy_facade,collab_router,review_router,agent_router,user_router,work_orchestrator}.py、cost/estimate_intake_router.py、schema_rbac.sql、DEPLOY.md、openapi.json
- Tests: 22 個後端測試（schema 5、hierarchy 5、API 12）＋ 同步既有測試

> 本檔是已核可的 stage 層級計畫 `../../code-generation/code-generation-plan.md` 中屬於本單元的步驟，**逐字摘出、未改寫**（含完成勾選）；Testing Contract、準備步驟（Step 1～2）與收尾步驟（Step 18～19）見該檔。三個單元同一批合入 `ut`。

## Steps

### U1 diagram-drafts

- [x] **Step 3 — 資料模型（實作）**：`models.py` 的 `UserDiagram` 加 `status`（`draft`／`ready`，非空、預設 `ready`）；`hierarchy_migration._ensure_hierarchy_schema()` 以 `ADD COLUMN IF NOT EXISTS status VARCHAR(16) NOT NULL DEFAULT 'ready'` ＋ CHECK 補欄位；`schema_rbac.sql` 同步 DDL 與 COMMENT；`DEPLOY.md` 更新欄位表與升級說明（blocking 同步）。〔FR6.1、FR6.5、C3〕
- [x] **Step 4 — 資料模型（測試）**：遷移在已有資料的 SQLite 上執行後既有圖皆為 `ready`；重跑遷移冪等；非法值被 CHECK 擋下。〔FR6.5〕
- [x] **Step 5 — 資料存取（實作）**：`hierarchy_service.list_diagrams_of_system` 與 facade 加必填 keyword-only `include_drafts`，回傳 `(diagram_id, title, diagram_status, updated_at)`、依 `updated_at` 降冪再 `id` 降冪；現行呼叫端 `work_orchestrator.py:967` 改為 `include_drafts=True` 並解構四元組；同步 `tests/test_work_orchestrator_store.py:416-426`、`tests/work_orchestrator_fakes.py:336` 與相關斷言；刪除系統（`hierarchy_service.py:212`）、清除預設專案（`user_router.py:438`）、刪除使用者（`user_router.py:651`）三處直接查詢確認不排除草稿；`record_diagram_change` 的 docstring 依 C5 修訂 K-07 並寫明出處。〔FR6.4b、FR6.4c、C5〕
- [x] **Step 6 — 資料存取（測試）**：不傳 `include_drafts` → `TypeError`；`True`／`False` 各自包含／排除草稿；排序（含同時間 tie-break）；系統下只有草稿時刪除系統被拒；預設專案下只有草稿時不被清除。〔FR6.4b、FR6.4c〕
- [x] **Step 7 — API（實作）**：`collab_router` 的建圖接受 `as_draft`、存檔接受 `finalize`（預設 false；只把草稿轉正式，不碰已正式的圖）；四支端點補 `response_model`（`DiagramCreated`／`DiagramSaved`／`MyDiagramItem`／`DiagramDetail`，欄位逐一照 C1～C3 的清單）並回 `diagram_status`；分享草稿回 409；定義常數 `DRAFT_REJECTED_DETAIL`，評核（`review_router.py:104`、`:176`）、WA 共編（`agent_router.py:167`）、估價綁圖（`estimate_intake_router.py:116`，**僅當**圖存在、屬於呼叫者且為草稿）共用。〔FR6.1、FR6.2、FR6.4a、C1～C4〕
- [x] **Step 8 — API（測試）**：TestClient 斷言四支端點的鍵集合等於契約清單（含既有測試 `test_diagram_system_attach.py:108` 改為加入 `diagram_status`）；`as_draft` 建立草稿、不傳則正式；`finalize` true／false／對正式圖無作用；四個 409 入口各一案且資料不變；估價綁他人的圖或不存在的圖維持現況（原樣存入、不回 409）；`require_arch_action("edit")` allow／deny 雙向（NFR5）。〔FR6.2、FR6.4a、NFR5〕
- [x] **Step 9 — 變更紀錄（實作＋測試）**：facade `record_diagram_change` 以 C5 的摘要「經大腦建立「<名稱>」」與標籤「大腦建立架構圖」寫入；測試斷言寫入一列、`source=brain_orchestration`、摘要非空。〔FR7.1〕
