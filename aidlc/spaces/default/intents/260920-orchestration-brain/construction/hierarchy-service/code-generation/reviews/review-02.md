## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-25T05:53:26Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | backend/services/hierarchy_facade.py > `HierarchyFacade._authorize`（`user_can(self._db, principal.role, "K2", action)`） | K2 判定沒有帶 `authorization_status`，而 `rbac.user_can` 只有在傳入該參數時才擋未核准帳號。`auth.get_user_from_token` 只擋 `is_active`，所以自行註冊、仍是 pending 的帳號已持有 token，只要角色在 K2 矩陣內，就能通過 K2 並建立、刪除專案與系統，也能列舉階層。`Principal.is_approved` 已由 `mint_principal` 填入，`memory_facade` 已據此補洞，但 `hierarchy_facade.py` 的註解寫明「HierarchyFacade 尚未讀它，同類缺口已記為交接事項」。本單元是授權列範圍的核心，這是 ADR-0006 IAM 面向的缺口，與合併前必修第 4 項（待核准帳號）同形。code-summary §六 的 IAM 列沒有提到它。 | 在 `_authorize` 加入 `principal.is_approved` 檢查（拒絕時走 `HierarchyForbidden`），並補 allow／deny 雙向測試（待核准帳號對五個 path 皆被拒）。若要延後，須在 code-summary §七 登記為開放項並指明承接單元，不可只留在原始碼註解。 | Resolved (reviewer) |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-service/code-generation/source-manifest.json > `writes` | 補寫的 manifest 列了 7 檔，漏列 `backend/tests/test_hierarchy_migration.py`。code-summary §一 第 8 列與 §五 第 3 項（OPEN-CG7-1）都承認本單元修改了這個計畫外的 U4 測試 fixture（該檔最近的單元提交是 `9e14145` hierarchy-data，本單元的改動落在批次提交 `c2e5687`）。manifest 因此少報一個實際寫入的檔，而這個檔正是尚待關卡裁決的項目。 | 把 `backend/tests/test_hierarchy_migration.py` 補進 `writes`，並在 manifest 旁註明該項屬 OPEN-CG7-1，與 code-summary 一致。 | Unresolved |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-service/code-generation/code-generation-plan.md > §三 表第 7 列 | 計畫寫 `backend/openapi.json`，實際檔案在 repo 根目錄 `openapi.json`（`backend/openapi.json` 不存在）。補寫的 manifest 用的是正確路徑，與計畫 §三 不一致，照計畫逐字對照會得出「虛列」。 | 更正計畫 §三 第 7 列路徑，或在 manifest 註明依實際路徑為準。 | Resolved (reviewer) |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-service/code-generation/code-summary.md > 末節「重新查驗」第 7 項 | 本單元三支新檔的內容已被 U12（be945a4）、U23（8677b7d）、U14（624c170）改寫：facade 新增 280 行、service 135 行、router 52 行。manifest 與 reviewed-source 雜湊反映的是現況，而 code-summary §一 仍寫「約 330／320／270 行」「12 個方法」，測試數也從 28 變成 34。第 7 項據實不勾沒有問題，但摘要沒有說明檔案內容已含其他單元的修改。我查證時，`BR6.1`、`BR6.4` 三道約束（router 不呼叫判定支援方法，只在 docstring 提到名稱）、`BR6.5` 與 409 宣告（兩個 DELETE 的 responses 含 409）在現況仍成立。 | 在重新查驗節加一句：現況檔案含 U12／U23／U14 的後續修改，BR6.x 判定依現況檔案複驗，不代表本單元原始提交。 | Resolved (reviewer) |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-service/code-generation/code-summary.md > 重做節「計畫 §六 的七個勾選框」第 6 項 | 突變驗證沒有在現行程式碼上重跑，而本單元的核心授權判定（`_authorize`、`assert_project_owned_by`、`project_visible` 守門）在後續 U12／U14／U23 之後已改動。第 6 項留給 build-and-test，但審查後新增的 `_authorize` 核准檢查（M-H1）只有一次性的突變紀錄，沒有隨現況再驗。這是 IAM 面向，屬宣告的缺口而非隱藏的缺口。 | 在 build-and-test 前，至少對 `_authorize` 的核准檢查、擁有者檢查、`project_visible` 守門三處在現況重跑突變並登記結果，或把第 6 項登記為有承接單元的開放項。 | New |
| R-06 | Minor | backend/tests/test_hierarchy_service.py > `test_T2c_pending_account_is_denied_even_with_an_edit_role` | T2c 的「五個 path」只涵蓋列舉專案、建專案、建系統、刪專案、變更紀錄，沒有碰 `GET /projects/{id}/systems` 與 `DELETE /systems/{id}`。目前這兩條都經 `project_exists`／`_authorize` 而被擋住，但缺測試時，日後有人在這兩條前面加讀取就不會被這個回歸測試抓到。 | 補上這兩個 path 對待核准帳號的 403 斷言。 | New |

> R-01 Reviewer note: `hierarchy_facade.py:214-217` 的 `_authorize` 先檢查 `principal.is_approved`，再查 `K2`；拒絕走 `HierarchyForbidden`。所有受保護方法都經 `_authorize`，包含 `create_project_nocommit`（U19 組合寫入）與 `list_projects_by_ids`（`MembershipFacade.list_visible_projects` 的唯一資料來源），故不存在繞過。`T2c`（待核准帳號對列舉、建專案、建系統、刪專案、變更紀錄皆 403，且資料未變）與對照組 `T2d` 存在。實跑 `tests.test_hierarchy_service`：`Ran 36 tests`、`OK`。code-summary 的修正節如實記載「在收據登記後進行、未經審查」，本輪即補審。

> R-02 Reviewer note: `source-manifest.json` 仍只列 7 檔，未含 `backend/tests/test_hierarchy_migration.py`；code-summary §一 第 8 列與 OPEN-CG7-1 仍承認本單元改過它，重做節也沒有處置。

> R-03 Reviewer note: 凍結的計畫 §三 第 7 列仍寫 `backend/openapi.json`，但 code-summary 重做節「與已核可計畫的落差」第一項已明記實際路徑為根目錄 `openapi.json`（我驗證 `../openapi.json` 存在、`backend/openapi.json` 不存在），manifest 用的也是正確路徑。

> R-04 Reviewer note: 重做節的落差清單列出後續單元新增的 5 個 facade 方法、`list_projects` 的 `project_visible` 必填參數與成員範圍可見性、36 個測試，並說明 BR6.4 第 1 道約束依現況複驗。§一 的「約 330 行／12 個方法／28 個測試」仍是舊值，但已被重做節明確取代。我另行驗證 router 未 import `hierarchy_service`，也未呼叫 `project_exists`／`get_project_owner`／`get_project_of_system`。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `tests.test_hierarchy_service`（`backend/.venv`） | 36 tests、OK | 與 code-summary 一致，含 T2c／T2d。 |

### Summary

審查後新增的待核准帳號檢查已落地、測試存在且實跑通過，我沒找到繞過它的入口；後續單元對共用檔的修改沒有破壞 BR6.4、facade 的授權邊界或 `list_projects` 的可見範圍。剩餘為 1 個 Minor 前案（manifest 漏列）與 2 個新 Minor（突變未在現況重跑、T2c 少兩個 path）；0 Critical、0 Major。
