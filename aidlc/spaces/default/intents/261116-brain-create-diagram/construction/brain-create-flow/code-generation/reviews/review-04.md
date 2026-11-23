## Review
**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

**Prior findings**

| ID | Now | Severity | Note |
|----|-----|----------|------|

**New findings**

| Severity | Location | Finding | Required action |
|----------|----------|---------|-----------------|
| Major | backend/database.py:672 `_ensure_diagram_status_schema()`（`except Exception: ... raise`）；backend/tests/test_diagram_drafts_schema.py `TestDiagramStatusStartupPatch` | 這支啟動補丁刻意「失敗就讓 backend 啟動失敗」，DEPLOY.md 與 LOCAL-DEV.md 都把這件事寫成部署 rollback 的觸發條件（缺欄位時讀圖端點全數 500、探針只打登入抓不到）。但四個測試只涵蓋補欄位成功、冪等、不跑階層遷移、`init_db` 有呼叫補丁，沒有任何一案斷言「補欄位失敗時例外會往外拋」。把 `raise` 改成只記 log（退回其他 `_ensure_*` 的吞例外形狀）全套仍會綠燈，而那正是這次要擋的「服務帶著壞狀態起來」。突變驗證也只做了「拿掉 init_db 內的呼叫」。 | 新增一案：讓 `_ensure_diagram_status_column`（或 DDL 執行）拋例外，斷言 `_ensure_diagram_status_schema` 重新拋出且 session 已 rollback；補做「把 raise 吞掉」的突變驗證並寫進 code-summary 的突變表。 |
| Minor | backend/services/brain_gateway.py:1992 `_create_and_dispatch`（`DIAGRAM_CREATE_TIMEOUT_SEC` 與 `timing.wait_for`）；backend/tests/test_brain_diagram_creation_flow.py `test_create_that_hangs_times_out_and_the_connection_keeps_working` | 逾時測試用的是會卡住的替身 `FakeDiagramClient`，真實路徑（同進程 ASGI 傳輸 → 同步端點在 threadpool 執行緒內 INSERT）沒有被測到：取消 `wait_for` 後該執行緒仍會跑完並提交，所以「逾時回覆結果不明」之後，草稿仍可能在閘道放棄之後才落地，成為沒有變更紀錄、作業對象沒切過去的孤兒草稿；使用者若在落地前重說，FR6.3a 的「先問接著畫哪張」也不會出現，可能多一張。這個殘留風險沒有寫進 code-summary 的「未處理」清單；另外，取消是否真的能在執行緒卡住時及時生效（期限是否真有界）只在替身上驗證過。 | 在 code-summary「修訂 1 的偏差與未處理」補上「逾時後草稿可能遲到落地」這一條並說明處置（使用者可在工作區看到並刪除）；若可行，加一案用真的 `CapabilityClient` ＋ 卡住的端點驗證逾時確實在期限內回覆。 |
| Minor | DEPLOY.md:313、DEPLOY.md:1772、DEPLOY.md:2150 | 新增第八支 `_ensure_*` 後，LOCAL-DEV.md 已改成「八支」，但 DEPLOY.md 仍寫「其餘六支 `_ensure_*_schema()`」（313）、「`create_all`＋七支 `_ensure_*`」（1772）、「`create_all` 與七支 `_ensure_*`」（2150）；313 的「那六支都在 create_all 之後」也已不成立（現在是七支）。維運人員照 DEPLOY.md 的 502 排錯表會少算一支，而新增的這支正是唯一會讓啟動失敗的。 | 把三處數字與 313 的敘述同步成八支（七支在 `create_all` 之後），並在 2150 的 502 排錯列補上「缺 `user_diagrams.status` 且補欄位失敗也會讓啟動失敗」。 |
| Minor | backend/services/brain_gateway.py:1983-2011（`CREATE_FORBIDDEN_MESSAGE`／`CREATE_FAILED_MESSAGE` 分流）；aidlc/spaces/default/intents/261116-brain-create-diagram/inception/contract-design/contract-summary.md:185 | 契約錯誤表寫「403 沿用既有權限文字」，實作改為新增一段文字（開發者已自陳需人確認）。該文字斷言「需要該專案的編輯權」，但同一分支也會接到擁有權與帳號狀態的 403；另外建圖回 404（系統已被刪）、401、422 都落入 `CREATE_FAILED_MESSAGE`「請稍後再試一次」，對永久性失敗是誤導，使用者會一直重試。 | 在關卡上請人確認 `CREATE_FORBIDDEN_MESSAGE` 的字句；把 404 分流成「找不到這個系統」之類的說明（或至少不叫使用者稍後重試），並把與契約 C5 的差異寫進 code-summary。 |
| Minor | frontend/src/pages/AssessmentPage.tsx:20-25 `DiagramItem`；frontend/src/pages/WorkspacePage.tsx:25-33 `Diagram` | Step 26 宣稱「改由產生型別推導，後端漏回欄位時 tsc 會紅燈」，只對一半成立：WorkspacePage 的 `Diagram` 仍手寫 `updated_at: string`（產生型別是 `string \| null`，null 會被 `new Date(null)` 顯示成 1970 年）；AssessmentPage 的 `diagram_status` 是選填，後端漏回該欄時「（草稿）」標示會靜默消失，正是 Workspace 那邊要避免的失敗型態。 | `AssessmentPage` 的 `DiagramItem.diagram_status` 改為必填（取自 `MyDiagramItem`）；`WorkspacePage` 的 `updated_at` 改取產生型別並處理 null。 |

### Notes

- 逐項攻擊結果（與上表對應）：Step 23 的分流本身正確——`ARCH_FORBIDDEN_DETAIL_PREFIX` 由 `rbac.require_arch_action` 與 `_is_arch_forbidden` 共用同一個常數，全樹沒有第二份字面值，且 `test_forbidden_is_classified_by_its_source` 以真實端點驗了兩種 403；唯一的結構疑慮是 `work_orchestrator_capabilities.py` 因此多匯入了 ORM 的 `models`（邊界測試未禁，但輕量客戶端模組變重）。Step 20 的「失敗即啟動失敗」有先例（`ensure_project_members_on_startup`）且 `init_db` 外層沒有 try/except，正當性成立，缺的只是測試（上表 Major）。Step 24／25 的性質測試我逐一代入突變（互斥性質對 M1／M4、決定性質對 M3／M5）判斷不是恆真；`make_title` 的 184 碼位預算加 4 字尾綴加 12 位數序號預留恰好等於 200，單一超長可見字元會退回系統名，推導無誤。Step 26 的前端改動符合 lint 結構約束（純函式 `readErrorDetail`、無就地修改、新增節點皆有 `data-testid`）。
- 程序備註核對：`git diff --check` 無問題、41 個檔案的增刪行與各 summary 相符，`work_orchestrator_capabilities.py`、`brain_gateway.py`、前端檔案沒有看到非預期的行遺失或雜訊；所有變動的原始檔都在三份 source-manifest 的 `writes` 內（無遺漏、無多列），`draft-ui` 追溯已含 FR3.4／FR6.2／FR6.4a 且目標檔案都存在。
- 本次依規定只做靜態審查，未執行任何測試；上述「測試能否失敗」的判斷來自閱讀斷言與突變推演，不是實際重跑。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | DEPLOY.md > 2.2.7「草稿狀態欄位」；backend/models.py > UserDiagram.status；backend/services/hierarchy_migration.py > _ensure_diagram_status_column；.github/workflows/deploy.yml（不呼叫任何遷移） | 部署順序風險沒有被機制擋住，只靠文件。ORM 已映射 `user_diagrams.status`，所有讀圖查詢都會選取這一欄；既有 volume 若在新版 backend 上線前沒補欄位，工作區、專案頁、評核的讀圖端點全數 500。合併進 `ut` 會自動部署，而 backend 啟動路徑（`database.py` 的 `_ensure_*` 家族、`main.py` 的 `ensure_project_members_on_startup`）都不補這一欄。唯一寫下的補法是 `run_hierarchy_migration.py`，它跑的是整套階層遷移（含把 `system_id IS NULL` 的圖重新指派到預設系統），不是只加欄位；DEPLOY.md 稱「可重跑：欄位已在就不動」只對加欄這一步成立，對整支腳本並不精確。倉庫已有兩個先例可借：`database.py::_ensure_last_activity_schema`（單純 `ADD COLUMN IF NOT EXISTS`）與 U19 以使用者裁決改為啟動時自動補齊。作者已在 code-summary 自陳此項需人裁決。 | 在關卡上由人裁決擇一：(a) 在 `database.py` 的 `init_db` 加一支只補 `status` 欄位與 CHECK 的啟動補丁（可重跑、失敗要大聲），並同步更新 LOCAL-DEV.md 與 DEPLOY.md；或 (b) 維持手動，但在 DEPLOY.md 明寫「改跑 `psql -f schema_rbac.sql` 或只執行加欄那條 ALTER」作為不帶資料遷移副作用的路徑，並把「合併前先補欄位」列為合併前檢查項。無論選哪個，都要在 DEPLOY.md 更正「整支腳本可重跑且不動資料」的說法。 | New |
| R-02 | Minor | backend/services/brain_diagram_creation.py > decide（TARGET_DIAGRAM 且 has_drafts 分支）；code-summary.md 偏差 #2 | 偏差 #2 的判斷有理有據（判定表第三列與 FR6.3b 直接衝突，作者標〔推導〕且 docstring 與測試 `test_draft_diagram_target_continues_the_same_draft` 鎖住），我認為方向合理。但它的代價沒有被寫出：作業對象是草稿時，使用者明說「另一張」「新的」（p ≥ t）也只會接著畫同一張，大腦路徑無法在選著草稿時新建第二張；而草稿可因自動存檔寫入使用者手繪內容（只有產圖存回或手動存檔才轉正式），此時會以 A1 覆寫使用者在草稿上的編輯。FR2.2 判定表與 FR6.3 兩處需求文字仍互相矛盾。 | 關卡上請人確認接受偏差 #2；若接受，在 requirements 或交接紀錄標明「FR2.2 第三列對草稿作業對象由 FR6.3b 取代」，並把「選著草稿時要新建須先切換作業對象」寫進使用說明或測案的已知限制。 | New |
| R-03 | Minor | backend/services/brain_gateway.py > _on_diagram_select 內 relist；code-summary.md 偏差 #3；requirements-analysis/requirements.md FR3.5 | FR3.5 要求候選失效時「回覆說明並重新列出」，目前只做到重新列出，沒有說明句：使用者看到的是同一個反問換了一組選項，不知道為什麼。安全面是對的（以連線上的對照解析、`set_work_target` 經 `resolve_work_target` 重新驗證擁有權、失效時不改由別的對象代替；測試 `test_pick_diagram_for_modify_and_a_stale_candidate_is_relisted` 覆蓋刪圖情境）。缺口源於契約 C6 寫「反問文字」而 `ClarifyPayload` 沒有文字欄，是契約本身的缺陷，不只是實作省略。FR3.6 的「其餘請用切換對象選取」也被迫附在最後一筆候選的標籤後，容易被讀成該項名稱的一部分。 | 在關卡上明確記為「FR3.5 說明句未滿足」並由人接受或排入後續；tcms-test-cases 不得把該 AC 標為已覆蓋。若要補，需先在 `ClarifyPayload` 加選填文字欄（走 ws-contract 漂移檢查），而不是繼續借用候選標籤。 | New |
| R-04 | Minor | frontend/src/pages/AssessmentPage.tsx > fetchDiagrams（約 190 行）與下拉清單（約 1319 行）、發起評核錯誤處理（約 943 行） | 評核頁的圖下拉清單來自 `GET /api/collab/diagrams`，該端點現在包含草稿，但此頁沒有標示或過濾（檔內 `diagram_status`／`isDraft` 零命中）。使用者選到草稿發起評核，後端正確回 409，但前端以 `res.text()` 直接顯示，畫面上是原始 JSON 字串 `{"detail":"這張圖還是草稿，請先完成產圖"}`。FR6.4 只要求三處標示，FR6.4a 只要求被拒並顯示訊息，所以未違反需求，但「顯示訊息」的實際呈現不是使用者可讀的句子；ShareModal 對分享 409 的呈現未見處理，可能同形。 | 評核頁下拉清單排除或標示草稿，並在評核與分享兩處把 409 的 `detail` 解出來顯示；或在 tcms-test-cases 把這兩處列為手動案例並寫明實際畫面。 | New |
| R-05 | Minor | backend/services/brain_diagram_creation.py > graphemes／_truncate_graphemes／make_title；backend/services/collab_router.py > MAX_DIAGRAM_TITLE_CHARS = 200 | 取名只以「可見字元」截到 30，沒有碼位上限；`_is_extender` 讓一個可見字元可附上無限個組合記號。含大量組合記號或 ZWJ 序列的句子（zalgo 文字、家庭 emoji）會產生遠超 200 字元的標題，`POST /api/collab/diagrams` 回 422，大腦只回「新圖沒有建立成功」，且每次重說都會同樣失敗。`test_title_properties` 只斷言可見字元數，沒有斷言總長。 | 在 `make_title` 加碼位總長上限（連同「（n）」後綴不超過端點上限），並在性質測試加一條總長斷言。 | New |
| R-06 | Minor | backend/services/intent_routing_port.py > select_routing_port；backend/services/brain_diagram_creation.py > decide（p 為 None）；LOCAL-DEV.md | 偏差 #5（缺題時 p 為 None 視為不明）在 `claude-code`（本機）走工具呼叫路徑時是恆定狀態，不是例外：該路徑沒有這一題。後果是本機上「系統沒有圖」時任何架構請求（含明確的修改句）都直接建一張空白草稿，FR2.4 走不到；「系統有圖」時每句畫圖都會反問新建或修改。部署環境（openrouter）走 Decisions 路徑不受影響，所以是本機行為落差。LOCAL-DEV.md 是唯一記載本機隱性前置條件的文件，未提這項差異。 | 在 LOCAL-DEV.md 的逐功能驗證步驟註明：本機工具呼叫路徑下新建或修改判定恆為「不明」，驗證 FR2 需用 openrouter；或讓工具呼叫路徑也能回 p。 | New |
| R-07 | Minor | backend/services/brain_gateway.py > _create_and_dispatch／_diagram_flow | 冪等性涵蓋了重說（系統下已有草稿即改問接著畫）、建圖逾時（不重試，下一句會看到草稿）、切換失敗（草稿保留）三種情境，且 `pending_clarify` 在選取時先清除，重複點選會被拒。未涵蓋的是同一使用者兩個連線（兩個分頁）同時對「沒有圖的系統」說畫圖：兩邊都讀到無草稿，各建一張，系統下出現兩張草稿。NFR3 只約定重試與復原，不含此情境，後果也只是多一張可見、可辨識的草稿。 | 在已知限制記一行即可；若要處理，需在建圖端以（使用者、系統、草稿）做軟性去重，不建議在本站做。 | New |

> R-01 Not re-checked this round

> R-02 Not re-checked this round

> R-03 Not re-checked this round

> R-04 Not re-checked this round

> R-05 Not re-checked this round

> R-06 Not re-checked this round

> R-07 Not re-checked this round
