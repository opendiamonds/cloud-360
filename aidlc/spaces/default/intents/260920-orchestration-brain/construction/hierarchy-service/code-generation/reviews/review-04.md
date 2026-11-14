## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-02 | Still applies | Minor | source-manifest.json 的 writes 仍只列 7 檔，沒有 backend/tests/test_hierarchy_migration.py；code-summary.md 第 196 行已如實記載「以已接受風險進入紀錄」，且該檔不在本輪收據範圍內。manifest 與 code-summary 第 8 列仍不一致，嚴重度不變。 |
| R-05 | Still applies | Minor | 已部分修復：code-summary.md 第 287–307 行「5. 突變驗證」在現行程式上重跑 13 項（M1–M11 加 A3-o1／A3-o2），全數 RED，涵蓋擁有者檢查（M3、M4）與守門順序（A3-o1、A3-o2）。但原發現點名的三處中，_authorize 的 is_approved 核准檢查（M-H1）與 project_visible 守門的拿掉突變不在這 13 項內；M-H1 只在較早一節（第 209 行）有一次性紀錄，未隨現況重跑。第 6 項已勾，勾選理由只涵蓋 13 項。範圍縮小為兩處，仍為已宣告的缺口。 |
| R-06 | Still applies | Minor | backend/tests/test_hierarchy_service.py 的 T2c（第 160–195 行）仍只涵蓋列舉專案、建立專案、建立系統、刪除專案、變更紀錄五個 path；GET /api/hierarchy/projects/{id}/systems 與 DELETE /api/hierarchy/systems/{id} 對待核准帳號沒有 403 斷言（T2b 只對非 canonical 角色涵蓋這兩條）。讀碼確認目前 list_systems 與 delete_system 在 hierarchy_facade.py 第 144 行與第 370 行附近都先呼叫 _authorize，故無現行缺陷，僅是回歸網缺口。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-service/code-generation/code-summary.md > 「整站重跑後的勾選回復」第 2 項 | 該節稱最新收據是 reviewed-source-7867815dfd2c.tsv 且 openapi.json 為「1 變」。但目錄下還有更新的 reviewed-source-0620ea0d37f0.tsv（mtime 2026-11-08 19:13，晚於 7867815dfd2c 的 14:23，尚未入版控）。我獨立以 shasum -a 256 重算：該新收據的 7 個檔全部與現況相同，與 7867815dfd2c 的唯一差異正是 openapi.json（e26c3a60 變為 a4c17964）。所以以最新收據為準時為 7 同 0 變，該節的「1 變」是對舊收據的比較結果，敘述過時。 | 把該節的依據改為以 0620ea0d37f0 為基準的 7 同 0 變，並註明與 7867815dfd2c 的差異只有 openapi.json（來源見驗證結果表）。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| shasum -a 256 對 reviewed-source-7867815dfd2c.tsv 逐列重算（awk -F tab 取欄位） | 6 同、1 變：backend/main.py、models.py、hierarchy_facade.py、hierarchy_router.py、hierarchy_service.py、tests/test_hierarchy_service.py 相同；openapi.json 現況為 a4c17964，收據為 e26c3a60 | 與 conductor 重算一致 |
| shasum 對 reviewed-source-0620ea0d37f0.tsv 重算 | 7 同、0 變 | 最新收據與現況完全一致，本單元來源自該收據起無任何變動 |
| openapi.json 變動來源（git log 與 git show，唯讀） | 現況 a4c17964 等於 ff537a7 提交內容；e26c3a60 不是任何已提交版本，應為 7a50a40 與 ff537a7 之間或之前的工作樹中間態。已提交的 8677b7d 到 ff537a7 之間共 29 個 hunk：7a50a40 加入 DeleteUserBlockingReference、DeleteUserConflict、failed_project_ids 等（刪除使用者 409 與成員端點 503／404 描述，屬 auth／membership-service 單元）；ff537a7 加記憶 maxLength 4000 與數個 503 描述（屬記憶單元） | 兩個來源都不是本單元 |
| openapi.json 是否碰到本單元宣告 | 本單元五個 path 位於現況第 4561–4823 行（/api/hierarchy/projects、projects/{project_id}、projects/{project_id}/systems、systems/{system_id}，加 diagram-changes 另段）；8677b7d 到 ff537a7 的 hunk 起點（新檔行號）為 331–3526 與 4852 以後，落在 4561–4823 內的為零 | 未碰到本單元的 hierarchy 端點宣告。附註：兩個 DELETE 端點在 spec 中只宣告 204／409／422，沒有 403／404，這是既存狀態，不屬本輪變動 |
| git diff HEAD 對 code-generation-plan.md | 零差異；git status 顯示該檔未修改。勾選數實算 12 勾、1 未勾 | 計畫與 HEAD 版一致，conductor 的回復正確 |
| 未勾格理由 | 「git diff --stat 不含不動的檔案」仍不可勾：本單元沒有獨立提交（首見於批次提交 c2e5687），計畫第七節規定的 git show --stat 判定方式無法執行；CI run 42454550208 不產生此判定 | 理由仍成立；CI 已實跑的項目（unittest、validators、dump_openapi --check）早已勾選 |
| code-summary.md 新節（git diff HEAD） | 檔尾加 7 行，內容如實：重跑背景、勾選 12／1、未勾項引用 HEAD 理由。唯一不實處即新發現列的收據版本過時 | 除收據版本外屬實 |
| 讀碼檢查授權路徑 | hierarchy_facade.py：_authorize 第 219–235 行含 is_approved 檢查；delete_project 與 delete_system 先 _authorize 再 project_visible 再擁有者檢查再 project_admin（第 334–381 行附近）；hierarchy_router.py 兩個 DELETE 注入 project_admin_check | 與 code-summary 第 2 項描述一致，未見授權繞過或順序倒置 |
| 測試／validators | 依限制未執行 | CI 於 PR 650 head ff537a7 除已知的 membership-service C3 外全綠，以此為執行面證據 |

### Summary

本單元程式與測試自上次 READY 審查後確無改動：最新收據 0620ea0d37f0 顯示 7 個檔全部相同，openapi.json 的差異來自刪除使用者 409 與記憶單元的契約變動，完全沒有觸及本單元五個 hierarchy 端點的宣告，計畫檔與 HEAD 零差異。三項既有 Minor（manifest 漏列、突變重跑未涵蓋核准檢查與可見性守門、T2c 少兩個 path）仍在但皆為已宣告的低風險缺口，另有一項新 Minor 是 code-summary 引用了過時的收據版本；無 Critical 或 Major，判定 READY。

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
