## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-20T22:33:00Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | backend/services/hierarchy_facade.py > `HierarchyFacade._authorize`（`user_can(self._db, principal.role, "K2", action)`） | K2 判定沒有帶 `authorization_status`，而 `rbac.user_can` 只有在傳入該參數時才擋未核准帳號。`auth.get_user_from_token` 只擋 `is_active`，所以自行註冊、仍是 pending 的帳號已持有 token，只要角色在 K2 矩陣內，就能通過 K2 並建立、刪除專案與系統，也能列舉階層。`Principal.is_approved` 已由 `mint_principal` 填入，`memory_facade` 已據此補洞，但 `hierarchy_facade.py` 的註解寫明「HierarchyFacade 尚未讀它，同類缺口已記為交接事項」。本單元是授權列範圍的核心，這是 ADR-0006 IAM 面向的缺口，與合併前必修第 4 項（待核准帳號）同形。code-summary §六 的 IAM 列沒有提到它。 | 在 `_authorize` 加入 `principal.is_approved` 檢查（拒絕時走 `HierarchyForbidden`），並補 allow／deny 雙向測試（待核准帳號對五個 path 皆被拒）。若要延後，須在 code-summary §七 登記為開放項並指明承接單元，不可只留在原始碼註解。 | New |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-service/code-generation/source-manifest.json > `writes` | 補寫的 manifest 列了 7 檔，漏列 `backend/tests/test_hierarchy_migration.py`。code-summary §一 第 8 列與 §五 第 3 項（OPEN-CG7-1）都承認本單元修改了這個計畫外的 U4 測試 fixture（該檔最近的單元提交是 `9e14145` hierarchy-data，本單元的改動落在批次提交 `c2e5687`）。manifest 因此少報一個實際寫入的檔，而這個檔正是尚待關卡裁決的項目。 | 把 `backend/tests/test_hierarchy_migration.py` 補進 `writes`，並在 manifest 旁註明該項屬 OPEN-CG7-1，與 code-summary 一致。 | New |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-service/code-generation/code-generation-plan.md > §三 表第 7 列 | 計畫寫 `backend/openapi.json`，實際檔案在 repo 根目錄 `openapi.json`（`backend/openapi.json` 不存在）。補寫的 manifest 用的是正確路徑，與計畫 §三 不一致，照計畫逐字對照會得出「虛列」。 | 更正計畫 §三 第 7 列路徑，或在 manifest 註明依實際路徑為準。 | New |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-service/code-generation/code-summary.md > 末節「重新查驗」第 7 項 | 本單元三支新檔的內容已被 U12（be945a4）、U23（8677b7d）、U14（624c170）改寫：facade 新增 280 行、service 135 行、router 52 行。manifest 與 reviewed-source 雜湊反映的是現況，而 code-summary §一 仍寫「約 330／320／270 行」「12 個方法」，測試數也從 28 變成 34。第 7 項據實不勾沒有問題，但摘要沒有說明檔案內容已含其他單元的修改。我查證時，`BR6.1`、`BR6.4` 三道約束（router 不呼叫判定支援方法，只在 docstring 提到名稱）、`BR6.5` 與 409 宣告（兩個 DELETE 的 responses 含 409）在現況仍成立。 | 在重新查驗節加一句：現況檔案含 U12／U23／U14 的後續修改，BR6.x 判定依現況檔案複驗，不代表本單元原始提交。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 唯讀查證（grep、git log／diff） | 判定支援方法 `project_exists`／`get_project_owner`／`get_project_of_system` 的應用呼叫端只有 `membership_facade.py` 與 `requirement_field_facade.py`（同進程），router 無呼叫 | BR6.4 約束 (1) 仍成立；`list_projects_by_ids`／`list_systems_unscoped` 為 U23 新增的列舉來源，唯一呼叫端是 MembershipFacade |
| 19 項合併前必修對照 | 第 3 項改 `user_router.py`；第 14 項在 U23／U19 路徑，`hierarchy_router.py` 現已改走 `MembershipFacade` 的可見性；第 15、16 項屬 membership-service 與部署；第 1、4 項的改選路徑只經 `MembershipFacade`，不呼叫 `get_project_owner` | 19 項無一落在本單元，計畫 §七 的對照成立。第 4 項的待核准帳號缺口在精神上與上列 Major 同形，但那是另一條授權路徑，不改變 19 項的歸屬 |
| 六項完成判準抽查 | `openapi.json` 含五個 `/api/hierarchy` path，兩個 DELETE 的 responses 含 409；本輪未改應用程式碼，測試結果引用該次輪次輸出，審查者依規定未重跑 | 第 7 項不勾的理由成立，且無更好的替代驗證（提交歸屬不可得）；本單元範圍內以 `git diff c2e5687 HEAD` 查現況取代 |

### Summary

19 項合併前必修確實無一落在本單元，BR6.1／BR6.4／BR6.5 在後續單元修改後仍成立。主要的架構顧慮是 `HierarchyFacade._authorize` 沒有檢查帳號核准狀態（ADR-0006 IAM），目前只有一個 Major，其餘為簿記層級的 Minor，故判 READY，建議在關卡決定是否要求修補。
