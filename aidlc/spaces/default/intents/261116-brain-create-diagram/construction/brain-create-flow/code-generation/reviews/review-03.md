## Review
**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

**Prior findings**

| ID | Now | Severity | Note |
|----|-----|----------|------|

**New findings**

| Severity | Location | Finding | Required action |
|----------|----------|---------|-----------------|
| Minor | backend/services/brain_gateway.py:156-159（`CREATE_FORBIDDEN_MESSAGE`） | 非缺架構編輯權的 403 有兩個實際來源：K2 edit 不足（`hierarchy_facade._authorize`，是角色權限矩陣，不是專案層權限）與系統擁有權。文字寫「需要該專案的編輯權……請專案管理者協助」，對 K2 來源是錯的指引：專案管理者無法改角色矩陣，只有平台管理者可以。「帳號尚未授權」一句在此流程幾乎不可達（連線握手與 `facts.can_edit` 預檢已擋下）。 | 關卡上確認文字時，把 K2 與擁有權分開說明，或改成不指名誰能解決的中性文字（例如「你目前無法在這個系統下建立架構圖，請改選你名下的系統，或聯絡管理者」）；測試 `test_forbidden_403_text_depends_on_its_source` 的「不含『角色』」斷言隨之調整。 |
| Minor | backend/services/brain_gateway.py:1919-1923（逾時處置） | 建圖端點是同步 `def`，在執行緒池執行；`asyncio.wait_for` 取消的只是 ASGI 等待，執行緒仍會完成 INSERT。逾時後草稿仍可能落地。目前由兩點緩解：回覆要求使用者先到工作區確認，且下一句會因系統下已有草稿而走 `ASK_RESUME_DRAFT`，不會重複建圖（`decide`：系統、有草稿 → 反問）。但若草稿在下一句事實載入之後才落地，仍會出現第二張，且這個視窗沒有任何測試或文件記載；`test_create_that_hangs_times_out…` 的替身取消即不落地，沒有覆蓋這條路徑。 | 在 `_create_and_dispatch` 的逾時註解與 code-summary 偏差清單記下「逾時後草稿可能延後落地，由下一句的草稿優先反問兜底」，讓人在關卡上知情接受；不需改程式。 |

### Notes

審查範圍：單元 brain-create-flow 的修訂 1（Step 21、22、23、24、25），僅讀檔與 `git diff`，未執行任何測試或指令。

已逐項核對、確認無缺陷：

- **Step 23 分流**：`ARCH_FORBIDDEN_DETAIL_PREFIX`（models.py:108）與 `rbac.require_arch_action` 原文逐字相同（`git diff` 只替換為常數、文字不變），而 K2 的 detail 為「權限不足：需要 K2.edit」，前綴不重疊，偵測穩固。`_is_arch_forbidden` 只比對前綴、只存布林，`CapabilityError.__str__` 不含 detail。`models` 為既有的共用相依，沒有新增循環匯入。端點層級的分類測試（FinOps_Analyst 為真、撤掉 K2 edit 為假）真的打到端點，能失敗。
- **Step 21 逾時**：`timing.wait_for` 是既有的唯一計時注入點（符合檔頭禁令 1）；Python 3.12 下 `asyncio.TimeoutError` 即 `TimeoutError`；逾時不重試、不交辦、只記 turnId。`DIAGRAM_CREATE_TIMEOUT_SEC` 為模組常數，未新增環境變數，不觸發 `.env.example`／`validate_env_contract` 同步。
- **Step 22**：`_on_select` 重建 `IntentDecision` 時帶回 p（brain_gateway.py:2110），`compare=False, repr=False` 保持不進觀測。
- **Step 24／25 屬性測試**：性質 1 直接斷言結果並明確框住偏差 #2；性質 4 以區域構造兩個 p，邊界 `p == t`（u=0）會落在取樣內，`>=` 改成 `>` 的變異會使兩個同區 p 判定不同而紅燈。取名上限：主題預算 184 ＋「 架構圖」4 ＋ 重名預留 12 ＝ 200，與 `collab_router.MAX_DIAGRAM_TITLE_CHARS` 以測試鎖相等；`test_title_never_exceeds…` 含病態系統名與重名後綴，單一超長可見字元退回系統名有獨立案例。
- **Step 20**（database.py）：啟動失敗的處置有理由（缺欄位時讀圖必然 500），部署為單一 uvicorn 行程，沒有兩個行程同時 ALTER 的競態；DEPLOY.md、LOCAL-DEV.md、schema_rbac.sql 三處與程式一致（DDL 同一條敘述、`ck_user_diagrams_status` 同名、`_ensure_*` 計數改為八）。
- **程序備註（shell 腳本編輯）**：`work_orchestrator_capabilities.py` 的 diff 刪除行只有 4 行，皆為被取代的舊行（`put_diagram` 簽章與 json、錯誤建構、一行文件表），無遺失；`brain_diagram_creation.py` 為完整新檔、結構完整；三份 source-manifest 與實際變更檔案集合（排除 `aidlc/`）逐一比對，雙向皆為空差集，`models.py` 在 diagram-drafts 的 manifest 內。traceability.json 內所有檔案路徑都存在。
- 偏差 #2（草稿且 p ≥ t 接著畫同一張）與「啟動只補 `user_diagrams.status`」為使用者已決定，未重新檢討。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | backend/services/brain_gateway.py > BrainGateway._create_and_dispatch（`async with self.diagram_client_factory(conn.token)` 區塊）；backend/services/work_orchestrator_capabilities.py > CapabilityClient.__aenter__（`timeout=None`） | 契約 C5 錯誤表「建圖 POST 傳輸錯誤或逾時」的「逾時」沒有實作：建圖呼叫沒有任何期限。`CapabilityClient` 以 `timeout=None` 建立 client，閘道也沒有用 `self.timing.wait_for` 包住 `create_draft`（`brain_gateway.py` 檔頭規則要求計時一律走 `GatewayTiming`）。同一連線的訊息是依序處理的（`_dispatch_client_message` 以 await 呼叫 `_on_user_message`），建圖卡住時該連線後續訊息全被擋住，使用者收不到任何回覆。測試 `test_create_timeout_is_not_retried_and_not_dispatched` 是讓替身直接拋 `CapabilityError("transport")`，從沒有真的逾時，所以逾時分支從未被走到。實際上限可能由 DB 連線池逾時界定，但沒有任何程式或測試擔保。 | 為建圖呼叫加上期限（經 `self.timing.wait_for`，數值由人定，可參考工作編排存回的 `_persist_timeout`）；逾時視為結果未知：回 `CREATE_UNKNOWN_MESSAGE`、不重試、不交辦。補一個讓替身真的掛起、由注入時鐘觸發逾時的測試。 | New |
| R-02 | Major | DEPLOY.md > 2.2.7「草稿狀態欄位」；backend/models.py > UserDiagram.status；backend/database.py > init_db（階段一審查 R-01，仍然成立，屬 U1，需在合併前裁決） | `init_db` 依序呼叫的 `_ensure_*`（含 `_ensure_last_activity_schema`）沒有任何一支補 `user_diagrams.status`；`main.py`、`database.py`、`deploy.yml`、`deploy/` 都沒有引用 `hierarchy_migration`。合併進 `ut` 即自動部署，舊 volume 上所有讀圖查詢會因缺欄位而 500，目前只靠 DEPLOY.md 的人工步驟。DEPLOY.md 稱 `run_hierarchy_migration.py`「可重跑：欄位已在就不動」，只對加欄那一步成立，整支腳本仍會跑完整階層遷移。 | 由人擇一：在 `init_db` 加一支只補 `status` 欄位與 CHECK 的啟動補丁（可重跑、失敗要大聲，並同步 LOCAL-DEV.md 與 DEPLOY.md）；或維持手動，但在 DEPLOY.md 寫明只執行加欄那條 ALTER 的路徑，把「合併前先補欄位」列為合併前檢查項，並更正「整支腳本可重跑且不動資料」的說法。 | New |
| R-03 | Minor | backend/services/brain_gateway.py > BrainGateway._on_select（intent 反問分支，約 2079 行 `IntentDecision(intents=intents, confidence=..., below_threshold=False)`） | 使用者先回答「意圖」反問後，閘道另建一個新的 `IntentDecision`，沒有帶 `new_diagram_probability`，儘管 `pending.decision` 持有它。後果：p 變 None（視為不明）。系統下有正式圖時會多問一次「新建或修改」；系統下沒有圖且使用者原本明確要「改」時，會變成直接新建一張草稿並產圖，違反 FR2.4。測試沒有涵蓋此分支。 | 建構新決定時帶入 `pending.decision.new_diagram_probability`；補一個「意圖反問後仍保留 p」的閘道測試。 | New |
| R-04 | Minor | backend/services/brain_gateway.py > BrainGateway._create_and_dispatch（`exc.status_code == 403` 對應 `NEED_ARCH_EDIT_MESSAGE`）；backend/services/brain_diagram_creation.py > list_owned_systems | 建圖端點的 403 有兩個來源：架構編輯權，以及 `collab_router._attachable_system_or_raise` 的 K2 edit 與擁有權檢查。閘道預檢只檢查架構編輯權，之後任何 403 一律回「需要架構編輯權、請向平台管理者申請角色變更」，指向錯誤的原因。`pick_system` 候選列出所有擁有的系統，沒有過濾使用者實際可掛載者（契約 C6 寫「使用者可編輯的系統」），使用者可能點到必然 403 的系統。 | 403 改回不指定原因的說明，或依 detail 分流；候選依 K2 edit 過濾，或在交接紀錄記為已知限制。 | New |
| R-05 | Minor | backend/tests/test_brain_diagram_creation.py > DecidePropertiesTest.test_create_and_modify_are_mutually_exclusive_and_total、test_deterministic | 作為 ADR-0006 agent routing PBT 硬約束的落點，四項性質中有兩項不能失敗：性質 1 的 `assertFalse(p >= t and p <= 1.0 - t)` 只是對輸入數字的恆真式（t 大於 0.5 時永遠成立），與 `decide` 實作無關；性質 4 是對純函式連呼叫兩次比較。因此「互斥」沒有被測試鎖住，偏差 #2 的例外（草稿作業對象在 p 大於等於 t 時回 MODIFY）也沒有被性質框住。 | 改寫性質 1 直接斷言結果：p 大於等於 t 時，除了「作業對象是草稿」之外，結果不得為 MODIFY 或 NO_DIAGRAM_TO_MODIFY；p 小於等於 1−t 時結果不得為 CREATE。性質 4 可保留為冒煙測試，但不要列為已鎖住的性質。 | New |
| R-06 | Minor | backend/services/brain_gateway.py > BrainGateway._diagram_flow_applies、build_brain_gateway；backend/tests/test_brain_gateway_startup.py | 偏差 #8 以 `diagram_client_factory` 是否注入作為整個新建流程的開關，而正式環境的注入（`lambda token: CapabilityClient(app, token)`）沒有任何測試。若日後被移除，`_diagram_flow_applies` 靜默回 False，功能退回舊行為而所有測試仍綠。 | 在啟動測試加斷言 `build_brain_gateway(...).diagram_client_factory` 非 None，或讓正式組裝在缺少時大聲失敗。 | New |
| R-07 | Minor | backend/services/brain_diagram_creation.py > decide（TARGET_DIAGRAM 且 has_drafts 分支）；code-summary.md 偏差 #2（階段一審查 R-02） | 偏差 #2 我認為可接受（判定表第三列與 FR6.3b 直接衝突，較具體的 FR6.3b 勝出，`decide` 已標〔推導〕）。補充證據：草稿作業對象在 p 高與 p 低時都回 MODIFY，只有 p 落在不明區才反問，信心越高反而越沒有「新建」的選項；使用者在草稿上明說「另一張新的」也只會接著畫同一張。 | 關卡上由人確認接受，並在交接紀錄註明「FR2.2 第三列對草稿作業對象由 FR6.3b 取代」。 | New |
| R-08 | Minor | backend/services/brain_gateway.py > _on_diagram_select 內 relist；requirements-analysis/requirements.md FR3.5（階段一審查 R-03） | 偏差 #3 屬實：`relist` 直接重送 `_clarify_pick_system` 或 `_clarify_pick_diagram`，沒有任何說明句；測試只斷言重新列出。FR3.5 的「回覆說明」未滿足，源頭是 `ClarifyPayload` 沒有文字欄。 | 關卡上明確記為「FR3.5 說明句未滿足」由人接受或排入後續；tcms-test-cases 不得把該句標為已覆蓋。 | New |
| R-09 | Minor | backend/services/brain_diagram_creation.py > make_title、_truncate_graphemes（階段一審查 R-05） | 取名只限制可見字元數；`_is_extender` 讓單一可見字元可附加任意多個組合記號，總長仍可超過 `collab_router.MAX_DIAGRAM_TITLE_CHARS`（200），端點回 422，閘道只回 `CREATE_FAILED_MESSAGE`，重說同一句會同樣失敗。 | 在 `make_title` 加碼位總長上限（含「（n）」後綴），並在性質測試加一條總長斷言。 | New |
| R-10 | Minor | LOCAL-DEV.md；backend/services/intent_routing_port.py > RoutedClassification（階段一審查 R-06） | 工具呼叫路徑沒有 p 這一題而恆為 None；LOCAL-DEV.md 本輪未修改，仍未記載本機（claude-code）無法驗證 FR2 的落差。 | 在 LOCAL-DEV.md 註明本機新建或修改判定恆為不明，驗證 FR2 需用 openrouter。 | New |
| R-11 | Minor | backend/services/brain_gateway.py > _create_and_dispatch（階段一審查 R-07） | 兩個連線同時對沒有圖的系統說畫圖，各自讀到無草稿而各建一張，沒有跨連線去重；後果只是多一張可見草稿。 | 在已知限制記一行即可。 | New |

> R-01 Not re-checked this round

> R-02 Not re-checked this round

> R-03 Not re-checked this round

> R-04 Not re-checked this round

> R-05 Not re-checked this round

> R-06 Not re-checked this round

> R-07 Not re-checked this round

> R-08 Not re-checked this round

> R-09 Not re-checked this round

> R-10 Not re-checked this round

> R-11 Not re-checked this round
