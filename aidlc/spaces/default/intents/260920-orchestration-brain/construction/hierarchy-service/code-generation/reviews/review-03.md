## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|----|-----|----------|------|
| R-02 | Still applies | Minor | source-manifest.json 的 writes 仍只有 7 檔，沒有 backend/tests/test_hierarchy_migration.py，而 code-summary 第 8 列與 OPEN-CG7-1 仍承認本單元改過它；回歸節也未處理。屬已知、已接受的 Minor，不阻擋。 |
| R-05 | Resolved | Minor | 我在 rsync 副本的現行程式上自行重跑三項突變，皆紅燈：(1) delete_project 的 project_admin 判定移到擁有者檢查之前，test_project_write_guard 紅（failures=1）；(2) 拿掉兩處 project_admin 判定，test_project_write_guard 與 test_project_delete_requires_admin 紅（failures=2）；(3) 把 _authorize 的 is_approved 檢查短路（M-H1），test_hierarchy_service 紅（failures=1）。三項涵蓋 R-05 點名的核准檢查、守門順序與擁有者檢查，且是在 A3 之後的現況上重做，不是沿用舊紀錄。 |
| R-06 | Still applies | Minor | test_T2c 仍只涵蓋列舉專案、建專案、建系統、刪專案、變更紀錄五個 path（backend/tests/test_hierarchy_service.py:160-198），沒有 GET /projects/{id}/systems 與 DELETE /systems/{id} 對待核准帳號的 403 斷言。本輪未動，仍是回歸保護的缺口，不阻擋。 |

### New Findings

| Severity | Location | Finding | Required action |
|----------|----------|---------|-----------------|
| Minor | backend/services/hierarchy_router.py > delete_project 與 delete_system 的 responses 宣告 | A3 新增的 403（HierarchyProjectAdminRequired）沒有在 OpenAPI 宣告，兩個端點仍只顯式宣告 409。回歸節已自述為觀察。端點既有的 403（K2 角色不足）本來也未顯式宣告，所以不構成新的契約破口，但前端或 agent 讀 openapi.json 看不到這條新的拒絕路徑。 | 可在後續把兩個刪除端點的 403 與其固定訊息補進 responses 並重 dump openapi.json；不阻擋合併。 |
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-service/code-generation/code-summary.md > 2026-11-01 回歸 第 1 節 | 回歸節的 hunk 歸屬表正確，但基準是 reviewed-source-3de30f2719de.tsv 加上 git HEAD；HEAD 尚未包含 A3 的未提交修改，所以第 1 節說「git diff HEAD 即為審查後的全部變動」只在 HEAD 等於審查基準時成立（我已實測：facade、router、test 檔、openapi.json 在 HEAD 的 sha256 都等於 tsv，成立）。這個前提沒寫進回歸節，日後 HEAD 前進後這句話會變成不可複驗。 | 在回歸節補一句「此結論以 HEAD 等於審查基準為前提，基準 tsv 為 3de30f2719de」，或附上被比對的 HEAD commit。 |

### Validation Tool Results

- 守門順序（自讀 backend/services/hierarchy_facade.py）：delete_project 為 _authorize（:334）、project_visible（:335-336，不可見回 404 專案句）、assert_project_owned_by（:339-341）、project_admin（:342-343，回 403）、刪除；delete_system 為 _authorize、取所屬專案、project_visible（回系統句 404）、assert_system_owned_by、project_admin、刪除。可見性與擁有者檢查都先於 project_admin，BR6.1／BR6.5 不洩漏存在性成立：新的 403 只可能發生在呼叫者已通過可見性與擁有者檢查之後，對他而言專案存在本就不是祕密；不存在、不可見、非擁有者仍同一句 404。突變 (1) 由測試實證順序被鎖住。
- BR1.4：_MINT 與 Principal.__post_init__ 的檢查未改；A3 沒有新增任何建構 Principal 的路徑，project_admin 是注入的 Callable[[int], bool]，不是 Principal 欄位。
- 例外轉譯點：HierarchyProjectAdminRequired 繼承 HierarchyForbidden（不是 HTTPException），router 的 _translate 唯一轉譯點未改即轉 403；hierarchy_facade.py 沒有新增成員關係 import（BR87.3）。
- 其他呼叫端：全 backend（排除 .venv）grep delete_project／delete_system，除 test_hierarchy_service 與 test_project_write_guard 的 HTTP 呼叫外，沒有其他直呼 facade 的地方，必填新參數不會讓未改的呼叫端壞掉。
- hunk 歸屬：git diff HEAD 的 facade +34、router +8、test_hierarchy_service +8 −8 都只含 A3 的改動（新常數與例外類、兩方法的新參數與判定、router 兩處注入、8 處測試跟進補 project_admin=ALWAYS_VISIBLE，斷言未改）。openapi.json 的 +2 −1 只是記憶 content 的 maxLength 4000 與描述，不屬本單元，歸 brain-infra A8，歸屬正確。models.py、hierarchy_service.py、main.py 的 sha256 與審查基準逐字相同。
- 測試（rsync 副本，backend/.venv/bin/python -B，hypothesis 存放於 scratchpad）：tests.test_hierarchy_service 加 tests.test_project_write_guard 合跑 Ran 58 tests，OK。突變三項如上，副本的 facade 每次還原；跑完已刪除副本與 hypothesis 目錄。我沒有重跑全套 1372 項、validator 與 dump_openapi --check，這三項引用開發者的宣稱，未獨立複驗。
- 回歸節數字：36 個測試與 22 個測試等數字，我實測合跑為 58，與 36 加 22 一致；A3 新檔 4 個測試我跑的第三輪合計 62，亦一致。其餘（1372、skipped=3、634 筆 pyc 列表比對）未獨立複驗。

### Summary

A3 的改動乾淨地疊在本單元的授權之上：守門順序（可見性、擁有者、project_admin）正確且由測試鎖住，不洩漏專案存在性，Principal 不可偽造與唯一轉譯點都未動，hunk 歸屬正確。R-05 已在現行程式上由我獨立重跑三項突變全紅而結案；R-02 與 R-06 仍是已知的 Minor，加上兩項新的 Minor（403 未宣告於 OpenAPI、回歸節缺基準前提），無 Critical 或 Major，判為 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | backend/services/hierarchy_facade.py > `HierarchyFacade._authorize`（`user_can(self._db, principal.role, "K2", action)`） | K2 判定沒有帶 `authorization_status`，而 `rbac.user_can` 只有在傳入該參數時才擋未核准帳號。`auth.get_user_from_token` 只擋 `is_active`，所以自行註冊、仍是 pending 的帳號已持有 token，只要角色在 K2 矩陣內，就能通過 K2 並建立、刪除專案與系統，也能列舉階層。`Principal.is_approved` 已由 `mint_principal` 填入，`memory_facade` 已據此補洞，但 `hierarchy_facade.py` 的註解寫明「HierarchyFacade 尚未讀它，同類缺口已記為交接事項」。本單元是授權列範圍的核心，這是 ADR-0006 IAM 面向的缺口，與合併前必修第 4 項（待核准帳號）同形。code-summary §六 的 IAM 列沒有提到它。 | 在 `_authorize` 加入 `principal.is_approved` 檢查（拒絕時走 `HierarchyForbidden`），並補 allow／deny 雙向測試（待核准帳號對五個 path 皆被拒）。若要延後，須在 code-summary §七 登記為開放項並指明承接單元，不可只留在原始碼註解。 | Resolved (reviewer) |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-service/code-generation/source-manifest.json > `writes` | 補寫的 manifest 列了 7 檔，漏列 `backend/tests/test_hierarchy_migration.py`。code-summary §一 第 8 列與 §五 第 3 項（OPEN-CG7-1）都承認本單元修改了這個計畫外的 U4 測試 fixture（該檔最近的單元提交是 `9e14145` hierarchy-data，本單元的改動落在批次提交 `c2e5687`）。manifest 因此少報一個實際寫入的檔，而這個檔正是尚待關卡裁決的項目。 | 把 `backend/tests/test_hierarchy_migration.py` 補進 `writes`，並在 manifest 旁註明該項屬 OPEN-CG7-1，與 code-summary 一致。 | Unresolved |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-service/code-generation/code-generation-plan.md > §三 表第 7 列 | 計畫寫 `backend/openapi.json`，實際檔案在 repo 根目錄 `openapi.json`（`backend/openapi.json` 不存在）。補寫的 manifest 用的是正確路徑，與計畫 §三 不一致，照計畫逐字對照會得出「虛列」。 | 更正計畫 §三 第 7 列路徑，或在 manifest 註明依實際路徑為準。 | Resolved (reviewer) |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-service/code-generation/code-summary.md > 末節「重新查驗」第 7 項 | 本單元三支新檔的內容已被 U12（be945a4）、U23（8677b7d）、U14（624c170）改寫：facade 新增 280 行、service 135 行、router 52 行。manifest 與 reviewed-source 雜湊反映的是現況，而 code-summary §一 仍寫「約 330／320／270 行」「12 個方法」，測試數也從 28 變成 34。第 7 項據實不勾沒有問題，但摘要沒有說明檔案內容已含其他單元的修改。我查證時，`BR6.1`、`BR6.4` 三道約束（router 不呼叫判定支援方法，只在 docstring 提到名稱）、`BR6.5` 與 409 宣告（兩個 DELETE 的 responses 含 409）在現況仍成立。 | 在重新查驗節加一句：現況檔案含 U12／U23／U14 的後續修改，BR6.x 判定依現況檔案複驗，不代表本單元原始提交。 | Resolved (reviewer) |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-service/code-generation/code-summary.md > 重做節「計畫 §六 的七個勾選框」第 6 項 | 突變驗證沒有在現行程式碼上重跑，而本單元的核心授權判定（`_authorize`、`assert_project_owned_by`、`project_visible` 守門）在後續 U12／U14／U23 之後已改動。第 6 項留給 build-and-test，但審查後新增的 `_authorize` 核准檢查（M-H1）只有一次性的突變紀錄，沒有隨現況再驗。這是 IAM 面向，屬宣告的缺口而非隱藏的缺口。 | 在 build-and-test 前，至少對 `_authorize` 的核准檢查、擁有者檢查、`project_visible` 守門三處在現況重跑突變並登記結果，或把第 6 項登記為有承接單元的開放項。 | New |
| R-06 | Minor | backend/tests/test_hierarchy_service.py > `test_T2c_pending_account_is_denied_even_with_an_edit_role` | T2c 的「五個 path」只涵蓋列舉專案、建專案、建系統、刪專案、變更紀錄，沒有碰 `GET /projects/{id}/systems` 與 `DELETE /systems/{id}`。目前這兩條都經 `project_exists`／`_authorize` 而被擋住，但缺測試時，日後有人在這兩條前面加讀取就不會被這個回歸測試抓到。 | 補上這兩個 path 對待核准帳號的 403 斷言。 | New |

> R-02 Not re-checked this round

> R-05 Not re-checked this round

> R-06 Not re-checked this round
