## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-11-22T13:29:57Z
**Iteration:** 1

**Prior findings**

| ID | Now | Severity | Note |
|----|-----|----------|------|

**New findings**

| Severity | Location | Finding | Required action |
|----------|----------|---------|-----------------|
| Major | backend/services/brain_gateway.py:1919（`self.timing.wait_for(create(), self.diagram_create_timeout_sec)`）、:228（`wait_for` 預設為 `asyncio.wait_for`）；backend/services/collab_router.py:632（`def create_diagram` 為同步端點）；backend/tests/test_brain_diagram_creation_flow.py:523-563 | 建圖逾時只對「非同步卡住」有效。建圖是同進程 ASGI 呼叫，端點是同步 `def`，資料庫寫入跑在執行緒池；Starlette 的 `run_in_threadpool` 預設不可被取消，`asyncio.wait_for` 在逾時後要等被取消的工作結束才返回。資料庫鎖等待或連線池耗盡這類真正的卡法，15 秒期限不會生效，該連線後續訊息仍被擋住（修訂 1 要防的正是這件事）。反過來，執行緒若在期限後才完成，草稿其實已寫入，使用者卻被告知「結果不確定」，且該草稿沒有變更紀錄。測試把 `wait_for` 換成自己的替身並以 `asyncio.sleep` 卡住，替身可被取消，因此測不到這條路徑，給出錯誤的安心感。這是靜態推論，未實測。 | 先用一個會在執行緒內阻塞（例如 `time.sleep`）的同步端點替身，加一個不替換 `wait_for` 的測試驗證逾時是否在期限內返回。若不成立，改成不等待被取消者結束的做法（例如以 `asyncio.wait` 逾時後放棄該工作），或在 DEPLOY.md／code-summary 如實寫明「期限只涵蓋非同步卡住，不涵蓋資料庫端阻塞」，並把逾時後可能留下「無變更紀錄的孤兒草稿」一併寫進錯誤表。 |
| Minor | backend/database.py:672-713（`_ensure_diagram_status_schema` 失敗時 `raise`）；backend/tests/test_diagram_drafts_schema.py:`TestDiagramStatusStartupPatch` | 本步驟與其他 `_ensure_*` 唯一的行為差異是「失敗即啟動失敗」，DEPLOY.md、LOCAL-DEV.md、code-summary 都以它為賣點，但四個測試沒有任何一個斷言「補丁失敗時 `init_db` 會往外拋」，突變表也沒有這一項。有人把 `raise` 改回 warning，全部測試仍綠，而這正是「讀圖端點全數 500、探針只打登入而不知道」的失敗模式。 | 補一個測試：以會拋例外的 bind 或替身讓 `_ensure_diagram_status_column` 失敗，斷言 `_ensure_diagram_status_schema` 與 `init_db` 都拋出；並把拿掉 `raise` 的突變與結果記入突變表。 |
| Minor | backend/services/hierarchy_migration.py:13-14、:86-87；backend/scripts/run_hierarchy_migration.py:2 | 模組說明仍寫「`init_db()` 不呼叫它」「不掛在啟動路徑上」，但修訂 1 起 `init_db()` 會匯入本模組並呼叫 `_ensure_diagram_status_column`。同檔 :387-389 已註明唯一例外，標頭與註解卻沒改，同一份檔內互相矛盾，下一位改遷移模組的人會被誤導。 | 在標頭、:86 註解與腳本說明補上「唯一例外：`_ensure_diagram_status_column` 由啟動補丁借用」，並指向 database.py 的補丁。 |

**Validation:** 靜態審查，未執行任何測試、建置或腳本。`git diff --check` 無輸出；三份 `source-manifest.json` 為合法 JSON，且工作樹所有變更檔（含未追蹤的新檔）都落在某單元的 `writes` 內；`draft-ui` 追溯已含 FR3.4、FR6.2、FR6.4、FR6.4a，目標檔皆存在。

### Notes

- **偏差 1（403 分流）判定正確。** `rbac.py:217` 與 `models.py:108` 的前綴同源，`require_arch_action` 是該前綴的唯一產生者；K2 的 403 來自 `HierarchyForbidden`，字首為「權限不足：需要 K2.edit」，不會誤判。`test_forbidden_is_classified_by_its_source` 走真實端點（`main_app`）驗證兩種 403，偵測可靠。`CapabilityError` 只存布林值，不洩漏 detail。新文字 `CREATE_FORBIDDEN_MESSAGE` 需要人確認（契約 C5 寫「沿用既有權限文字」，但 repo 內確實沒有 K2 的既有文字），已在偏差清單揭露。另提醒：`work_orchestrator_capabilities.py` 為了兩個字串常數匯入整個 `models`（ORM），而 `work_orchestrator_rules` 選擇複製常數並以測試鎖相等，兩個模組的作法不一致；邊界測試只鎖 rules 的純度，故不違規，僅記為觀察。
- **偏差 2（逾時後的重複）**：重說時閘道會重新讀取系統事實，已落地的草稿會走 `resume_draft_or_new`，不會再多建一張；重複的風險低，主要問題是上面 Major 所述的期限有效性與孤兒草稿。
- **屬性測試（Step 24／25）**：互斥、決定性兩條改寫後可以失敗（性質 4 由區域構造 p、浮點邊界我逐一檢查過，`t + u*(1-t) ≤ 1` 與 `(1-t)+(2t-1)=t` 皆精確，不會因進位而在 `decide` 內丟 `ValueError`）。取名上限推導正確：主題預算 184 碼位 ＋「 架構圖」4 ＋ 重名後綴預留 12 ＝ 200；單一超長可見字元會被排除並退回系統名。
- **前端（Step 26）**：資料抓取、`cancelled` 旗標與不可就地修改的結構未被動到；`Diagram`／`DiagramStub` 改由產生型別推導，欄位漂移會在 `tsc -b` 紅燈；評核 409 以 `readErrorDetail` 顯示 detail。
- **處理程序**：shell 腳本編輯沒有留下 diff 雜訊或遺失行，`work_orchestrator_capabilities.py`、`brain_diagram_creation.py` 與前端各檔讀起來一致。
- 結論：無 Critical，Major 一項（≤2），故為 READY；但建議在合併前處理逾時有效性那一項，因為它是修訂 1 的 Step 21 想解決的問題本身。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | DEPLOY.md > 2.2.7「草稿狀態欄位」；backend/models.py > UserDiagram.status；backend/services/hierarchy_migration.py > _ensure_diagram_status_column；.github/workflows/deploy.yml（部署後探針） | 部署順序只靠文件，沒有機制擋住。ORM 已映射 user_diagrams.status，所有讀圖查詢都會選取這一欄；既有 volume 若在新版 backend 上線前沒補欄位，工作區、專案頁、評核的讀圖端點全數 500。合併進 ut 會自動部署，而啟動路徑（database.py 的 _ensure 家族、main.py 的 ensure_project_members_on_startup）都不補這一欄。兩項證據讓它難以靠文件化解：(1) deploy.yml 部署後的 data plane 探針只打 POST /api/auth/login 並以 401 為通過（約 336–395 行，檔內註解寫明處理函式只查 users），完全不碰 user_diagrams，所以缺欄位的狀態會被判為部署健康，自動 rollback 不會觸發；(2) 新增的 DEPLOY.md 指令 cd backend 後執行 python scripts/run_hierarchy_migration.py 在部署主機上無法照寫執行：同檔 206 行寫明部署主機的 db 沒有 host port、要走 docker exec，而進入既有 backend 容器也不行（舊 image 沒有 _ensure_diagram_status_column）。另外該腳本是整套階層遷移（含把 system_id 為空的圖重新指派），DEPLOY.md 稱「可重跑：欄位已在就不動」只對加欄這一步成立。倉庫有先例可借：U19 以使用者裁決改為啟動時自動補齊。code-summary 已自陳此項需人裁決。 | 在關卡上由人裁決擇一：(a) 加一支只補 status 欄位與 CHECK 的啟動補丁（可重跑、失敗要大聲），並同步更新 LOCAL-DEV.md 與 DEPLOY.md；或 (b) 維持手動，但在 DEPLOY.md 改寫成部署主機可執行的 docker exec 加 psql 的單條 ALTER 指令，並把「合併前先補欄位」列為合併前檢查項。無論選哪個，都要更正「整支腳本可重跑且不動資料」的說法。 | New |
| R-02 | Minor | backend/services/hierarchy_migration.py > _ensure_diagram_status_column；backend/tests/test_diagram_drafts_schema.py | 補欄位那條敘述（同一條 ALTER TABLE 加欄、NOT NULL、DEFAULT ready、CHECK）只在 SQLite 上被測過（helpers.py 以記憶體 SQLite 取代 PostgreSQL）。這是 staging 唯一會用到的升級路徑，PostgreSQL 端語法與「既有列全為 ready」只有閱讀為據；test_schema_rbac_sql_declares_the_same_column_and_check 只是對 SQL 檔做字串比對，樣式出現（連註解中的也算）即通過，驗不到 DDL 可執行。 | 在 build-and-test 以舊 schema 的 PostgreSQL 副本實跑一次遷移，並執行 DEPLOY.md 的三條驗證查詢，把結果記入該階段紀錄；本單元不需改程式。 | New |
| R-03 | Minor | DEPLOY.md > 2.2.7「草稿狀態欄位」的回復段；backend/services/collab_router.py > reject_if_draft | 回復段只說舊版 backend 不讀這一欄、回退應用即可。但回退後已存在的 draft 列在舊版眼中就是一般架構圖：內容是空白骨架、舊版沒有 409 檢查，可被分享、評核、綁估價。部署失敗會自動 rollback，這不是假設情境。 | 在回復段補一句：回退前先把不要的草稿刪除或由擁有者存成正式，或明寫接受「回退後草稿等同正式圖」。 | New |
| R-04 | Minor | backend/services/hierarchy_service.py > list_diagrams_of_system（order_by updated_at desc） | 排序對 NULL 的位置在 PostgreSQL（DESC 時 NULL 排最前）與 SQLite（排最後）不同，而 schema_rbac.sql 的 user_diagrams.updated_at 可為空。FR3.6 要求決定性排序、契約 C5 要求新到舊；測試只在 SQLite 跑，抓不到。經 ORM 寫入的列都有 server_default，風險低，但手動匯入或舊資料的 NULL 列在 PostgreSQL 上會被當成最新而排在反問候選最前。 | 排序明確處理 NULL（例如 coalesce 或 nulls_last），並在 hierarchy 測試加一列 NULL updated_at 的案例。 | New |

> R-01 Not re-checked this round

> R-02 Not re-checked this round

> R-03 Not re-checked this round

> R-04 Not re-checked this round
