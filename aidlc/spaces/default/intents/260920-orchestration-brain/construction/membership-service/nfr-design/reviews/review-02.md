## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本站的鎖、交易邊界與回填設計大體紮實，且與已落地程式一致（`create_project_with_owner` 以 `create_project_nocommit` 同交易；`membership.*` 四個事件名；`sorted(set(...))`）。但有四項 Major：(1) `reselection_events.project_id` 外鍵矛盾自上游審查以來仍未裁決，本站依賴它卻保持沉默；(2) 用來支撐「CI 漂移閘門對 path 變更有效」的狀態碼計數與現有 `openapi.json` 相反；(3) 設計對自動改選自相矛盾——§一的死鎖軌跡需要同時持有多把鎖，§二與已落地程式卻是逐專案單鎖交易，該死鎖不可達，排序函式成為未被呼叫的死碼；(4) 逐專案獨立交易的「重跑可收斂」沒有任何呼叫者，部分失敗後專案會永久無管理者。Major 超過 2 項，判 NOT-READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | `construction/membership-service/nfr-design/scalability-design.md` §三、`reliability-design.md` §四 | 前次 `nfr-design/reviews/review-01` 的 R-01 已提，本次複查仍成立。共享契約 `inception/contract-design/contract-summary.md:1570` 逐字宣告 `reselection_events.project_id → projects.id`，無例外；`schema_rbac.sql:638` 註解卻寫「刻意不對 projects 設外鍵」。本站 `NFR12.14`（只增不減、永久保留）與「不設計歸檔」都建立在無外鍵之上，但六份產出對「外鍵／FK／cascade」零揭露。若以契約為準且帶 CASCADE，刪專案會連帶抹除稽核事件，永久保留即不成立；若無外鍵，專案刪除後事件列成為孤兒，`AC12.2.2` 的變更紀錄與橫幅行為本站亦未交代。實作（DDL）一邊對，契約一邊錯，但裁決從未被記錄。 | 在 `scalability-design.md` 或 `traceability.json` 明寫 `NFR12.14` 依賴「無外鍵」，並說明專案刪除後事件列的歸宿；同時要求以變更單修正 `contract-summary.md` `K-15` 的該行，或記錄為何以契約為準。 | New |
| R-02 | Major | `construction/membership-service/nfr-design/security-design.md` §三之二（行 107-108）；`nfr-design-questions.md` 行 81-82 | 本站主張漂移閘門對狀態碼變更無效，依據是「55 個 operation 宣告的狀態碼只有 `{200, 422, 201, 204}`」。實算現行 `openapi.json`（遍歷 `paths` 各 operation 的 `responses`）：`200`=65、`422`=64、`403`=12、`404`=11、`409`=7、`204`=6、`201`=5、`503`=1。其中 `409` 與 `404` 就在宣稱不存在的集合之外，建立專案端點自身即宣告 `409`。「只有四種狀態碼」是假的；前次 review-01 的 R-02 已提且未修。核心論點（未在 `responses=` 宣告的 raise 不會被全文比對抓到）可能成立，但被一個可算而未算的數字支撐。 | 重算並更正計數；若要保留「漂移閘門抓不到新增狀態碼」的論點，改以可驗證的例證（某個確實 raise 卻未宣告的狀態碼）支撐，或刪去該數字。 | New |
| R-03 | Major | `security-design.md` §一（死鎖軌跡 T1/T2、「多專案操作…逐一取鎖」）對 `scalability-design.md` §二（「逐專案獨立交易…每個專案各自取鎖、各自釋放」）；程式 `backend/services/membership_service.py:197-215`（`lock_projects_in_id_order`）與 `:815-858`（`run_auto_reselection`） | 設計自相矛盾。死鎖軌跡要求 T1 持有專案 7 的鎖再等 9，即同一交易同時持有多把鎖；但 `scalability-design.md` §二明定每個專案各自交易、各自釋放，同一時刻只持有一把鎖，不存在「持一等一」，死鎖不可達。已落地程式照後者實作：`run_auto_reselection` 逐專案 `lock_project` 並 `commit`，從不呼叫 `lock_projects_in_id_order`（全檔僅定義與 `__all__` 出現），該函式及其「一律按 id 遞增」的防線是死碼。結果：`security-design.md` §五與 `OPEN-ND19-2` 所列殘餘風險、`logical-components.md` §二之二「死鎖」列都在管理一個不可達的失效模式，同時未說明哪些路徑真會同時持有多鎖。同型規則見 `project.md` 的「先驗 X 可達」。設計與程式一致的一邊是逐專案單鎖，那一邊是對的。 | 擇一收斂：①刪去或改寫 §一的死鎖軌跡與排序要求，明寫「逐專案單鎖交易故無死鎖，排序僅為防禦」，並移除或標註未使用的 `lock_projects_in_id_order`；或②指出實際會同時持多鎖的路徑並改為呼叫該函式。同步更新 `OPEN-ND19-2` 與 blast radius 表。 | New |
| R-04 | Major | `construction/membership-service/nfr-design/scalability-design.md` §二（代價段「中間狀態是可觀察的…重跑可收斂」）；`reliability-design.md` §四（「唯一需要重試的是死鎖後的中止…屬 code-generation」）；程式 `backend/services/user_router.py:744-753`、`membership_service.py:844-858` | 契約端點三問缺口：「誰重跑」。設計以 `BR4.3` 冪等性主張部分失敗後可重跑收斂，並接受「專案 7 成功、專案 9 失敗」。但唯一呼叫點是停用端點在 `is_active` 已 commit 之後呼叫一次 `run_auto_reselection`；失敗只被 `logger.exception` 吞掉並回傳 200。帳號已停用，再次停用走不到 `deactivating` 分支（或無事可做），沒有排程、重試端點、回填腳本或告警負責補跑。結果是專案 9 永久沒有管理者，正是 `BR2.1` 與 `[ND1]` 要消除的狀態，且只留一行 log。設計把此風險標為「刻意接受」，卻未寫出補救的擁有者，也未列入 `OPEN-ND19-*`。 | 指名重跑的擁有者與觸發方式（例如可重入的修復端點、啟動時掃描零管理者專案，或把回填腳本擴為涵蓋此情境），或明寫為已知缺口並指派承接站；將 §二的「重跑可收斂」改為有呼叫者的主張。 | New |
| R-05 | Minor | `construction/membership-service/nfr-design/logical-components.md` §三之一 | 表格宣稱列出 `U7` 操作與鎖的互動，但僅列 `list_projects`／`create_project`／`delete_project`，漏 `assert_project_owned_by`／`project_exists`／`get_project_owner` 等唯讀查詢。結論同 `list_projects`，不影響設計，惟前次 review-01 R-03 已提。 | 加一行概括其餘唯讀查詢不受 `FOR UPDATE` 影響。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 直讀 `contract-summary.md:1570` 與 `schema_rbac.sql:636-650` | 契約有外鍵、DDL 無外鍵且註解刻意無 | 確認 R-01 矛盾仍在 |
| python 遍歷 `openapi.json` `paths.*.responses` 計數 | 200:65 422:64 403:12 404:11 409:7 204:6 201:5 503:1 | 確認 R-02，設計所稱 `{200,422,201,204}` 為假 |
| 直讀 `membership_service.py:197-215、815-858`，grep `lock_projects_in_id_order` | 僅定義與 `__all__`，無呼叫者；`run_auto_reselection` 逐專案 lock+commit | 確認 R-03，設計與程式一致的是逐專案單鎖 |
| 直讀 `user_router.py:738-753` | 停用 commit 後單次呼叫 `run_auto_reselection`，失敗僅 log | 確認 R-04 無重跑擁有者 |
| 直讀 `membership_facade.py:431-470` | 同交易建立專案與成員列，與 `reliability-design.md` §二一致 | 設計主張與落地相符，無發現 |
| 驗證工具（stage 定義） | 本次派工未列 | 未執行 |
