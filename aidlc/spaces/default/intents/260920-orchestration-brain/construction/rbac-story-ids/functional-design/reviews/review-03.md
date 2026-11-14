## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

`rbac-story-ids` 的資料面設計自洽，且與已落地的程式一致：我獨立解析 `backend/services/rbac_seed_data.py`，確認共 352 列，`K1`–`K4` 的 11 角色旗標與 `functional-spec.md` §一′ 的 44 列表格逐格相同；`user_router.py:101-104` 已補四個功能標籤；`schema_rbac.sql` 與 `DEPLOY.md` 已同步為 352；`tests/test_rbac_story_ids_seed.py` 已有 7 個案例，涵蓋兩份副本的一致性。主要缺口是 `BR7.1`–`BR7.3` 的全域層檢查只看角色，未納入執行期閘門實際使用的 J5 `authorization_status`，因此會放行「角色合格、帳號未核准」的被邀請者。此項為 Major（只有 1 項），不構成阻擋。其餘為 Minor：設計文字落後於程式、一條不變量缺執行期保護、一項已知的 AC 窄化尚未收斂。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | `construction/rbac-story-ids/functional-design/rules.md` > 修訂 1 `BR7.1`／`BR7.2`／`BR7.3` 的 `logic`；`functional-spec.md` > `W-4` 第 2 步、`W-5` 第 2 步 | 三條規則的判定式都寫成 `user_can(<role>, 'K3', ...)`，只以角色為輸入。執行期閘門並非如此：`rbac.py:148-153` 的 `user_can` 在 `authorization_status != "approved"` 時一律回 `False`，`require_story_action`（`rbac.py:271-277`）對未核准帳號直接回 403「帳號尚未通過管理員授權」。自助註冊的帳號預設為 `authorization_status="pending"` 且帶有角色（`user_router.py:361`、`:392`）。因此，一個角色為 `Developer`、帳號為 pending 的使用者會通過 `BR7.1`，被寫成專案成員，之後所有動作都被 J5 擋成 403。這正是 `FR12.6a` 要防的「成員列被寫入但進來什麼都看不到」。`BR7.3` 同樣有此問題：候選集合可能挑中 pending 或已停用（`is_active=false`）的成員，造成「系統自動把管理權交給你」對他為假；而 `W-5` 的情境本身就是在處理被停用者。`BR7.4` 要求旗標由呼叫端傳入，但規則沒有說明該旗標必須包含帳號狀態。已落地的 `services/membership_facade.py` 對 `authorization_status`／`is_active` 的 grep 為 0 命中，這顯示缺口已進入程式（程式屬 `U19`，此處僅作旁證，不展開）。正確的一邊是執行期閘門：資料面的角色檢查只是必要條件，不是充分條件。 | 在 `BR7.1`–`BR7.3` 的 `logic` 與 `W-4`／`W-5` 補上帳號狀態條件：被邀請者與自動改選的候選者都必須同時滿足「`authorization_status` 為 `approved`」、「`is_active` 為真」與「角色持有對應 `K3` 旗標」。`BR7.5` 的 `reason` 代碼補上第三種（帳號未核准或已停用），讓 `AC12.5.1` 的「說明他缺少什麼」可涵蓋。並將此條件寫入 `BR7.4`，說明傳入純函式的旗標即為合併後的結果。由於產出已凍結，請記為交接事項指給 `U19` 的實作與測試。 | New |
| R-02 | Minor | `functional-spec.md` > `§六` Audit logging 列、`§七` 的 `H-3`、`§八` 第四條 | 設計仍宣稱 `ensure_missing_role_permissions` 只記插入列數、不記是哪些列，並把它列為「無自然承接站」的未結案缺口，且 `§八` 明訂本單元不修改該函式。實際程式已不同：`rbac.py:84-120` 的 docstring 標示 `SEC-4`，並在插入時記錄 `inserted %d rows: %s`（逐列 `role/story_id` 的彙總），`test_the_seed_write_logs_which_rows_it_inserted` 也已鎖住此行為。哪一邊是對的：程式正確，設計文字已過期。ADR-0006 的 audit logging 面實際上已被履行，但設計記錄仍寫「僅部分履行、`H-3` 未結案」，日後引用本單元的人會得到相反的結論。 | 在交接記錄中將 `H-3` 標為已由程式處置（引用 `rbac.py:84-120` 與該測試案例），並更正 `§六′` Audit logging 列中「缺口擴大」的說法。產出已凍結，可在關卡備註處記明，不需回改原文。 | New |
| R-03 | Minor | `rules.md` > `BR5.4`；`functional-spec.md` > `W-3` 第 2 點 | `BR5.4`（持有 `K2.edit` 者必須持有 `K3.edit`）被寫成「預設矩陣被寫入或日後任何調整」都要成立，但沒有任何機制檢查它在執行期是否仍成立。`W-3` 只就 `BR1.3` 承認「管理者可在權限頁改壞，本單元只保證預設值」，對 `BR5.3`、`BR5.4`、`BR6.5` 沒有同樣的聲明。管理者在權限頁取消某角色的 `K3.edit` 後，該角色仍能建立專案卻管不動，現象即為 `BR5.4` 想避免的「我建的專案我管不動」，且權限頁不會標示原因。這不是 seed 缺陷，但規則文字的 `trigger` 讓讀者以為有持續保護。 | 在 `W-3` 與 `BR5.4` 的 `note` 明寫：這幾條不變量只對預設值與 seed 測試成立，執行期調整不受保護。若要保護，需另指派 `U19`／`U7` 在寫入端檢查，列為開放決策即可。 | New |
| R-04 | Minor | `rules.md` > `BR7.3` 的 `alignment_correction`；`functional-spec.md` > `H-11` | 前次 review-02 的 R-01 已提出：`BR7.3` 把已核可的 `AC12.4.1`（「被選中者為最早加入的成員」）窄化為「最早加入且持有 `K3.edit`」。目前處置是就地記為對齊修正並交接，`stories.md` 原文未改，因此 AC 的字面與 `BR7.3` 仍會給出不同結果。設計選擇本身有理由（避免被選中者管不動），不是缺陷。此處再列一次只為提醒：承接站 `code-generation` 需要在寫測試之前確定以哪邊為準，並更正 AC。 | 在 `code-generation` 開工前由人裁決並更正 `AC12.4.1` 原文；若不更正，測試應以 `BR7.3` 為準並在測試註解引用 `H-11`。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 手動解析 `backend/services/rbac_seed_data.py` | 352 列；`K1`–`K4` 的旗標與 `functional-spec.md` §一′ 逐格相同；`K3`、`K4` 各有 3 個角色全為 false | 設計的 44 列與已落地資料一致，`BR5.1`–`BR5.2`、`BR6.1`–`BR6.2` 成立 |
| 讀取 `rbac.py`、`database.py`、`user_router.py` | `ensure_missing_role_permissions` 在 `database.py:184` 被呼叫；`STORY_FEATURE_LABELS` 已含 `K1`–`K4`（`user_router.py:101-104`）；`CATALOG_EXCLUDED_STORIES` 仍只含 `J1` | 設計關於啟動路徑、標籤相依與 `BR4.5` 的主張屬實 |
| grep `schema_rbac.sql`、`DEPLOY.md` | `schema_rbac.sql` 有 44 筆 `K1`–`K4` 列，檔頭與驗證註解為 352；`DEPLOY.md` 五處皆已改為 352 | `BR4.1`、`BR4.2` 的 blocking 同步已履行 |
| 檢視 `tests/test_rbac_story_ids_seed.py` | 7 個案例，含 SQL 與 Python 副本逐列等值、`K2.edit` 蘊含 `K3.edit`、寫入日誌 | `BR4.4` 與 `BR5.4` 的預設值保護已落地；本審查未執行測試，以避免產生快取 |
