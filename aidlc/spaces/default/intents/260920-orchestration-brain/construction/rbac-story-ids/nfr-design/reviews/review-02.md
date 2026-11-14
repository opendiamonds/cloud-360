## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U3 rbac-story-ids 的 nfr-design（`security-design.md`）自洽，並完整承接 nfr-requirements 的 SEC-1 至 SEC-6、U3-V1 至 U3-V5、U3-A1 至 U3-A3、U3-D1。D-1 至 D-16 都有可追溯的上游來源，也與已落地的程式一致。程式端的核對結果：`rbac.py:19` 的 logger 名為 `cloud360.rbac`；`rbac.py:114-121` 的 log 已列出 `role/story_id` 配對；`database.py:186` 的重複 log 仍在（D-9）；`test_rbac_story_ids_seed.py` 已有 352 列完整性測試、`assertLogs("cloud360.rbac")` 與 SQL 對 Python 的三段 diff（每段上限 10 筆）。前次 review-01 的 R-01、R-02 已在產出內以更正段處置。只剩三項不阻擋的 Minor：一項是設計中的行號引用因實作而過期，一項是對外揭露面的落點不在本站，一項是交接義務缺少第二個追溯支點。契約端點三問都有答案：矩陣由 U3 寫入，由 `user_can` 與 `/roles/catalog` 讀取，`force=True` 的重 seed 會清掉並重建。四個 ADR-0006 面向都有逐項判定。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Minor | construction/rbac-story-ids/nfr-design/security-design.md §二 2.1 表格與 D-4 的更正段 | 設計把「RETIRED 區塊標題在第 187 行」「INSERT 區塊第 445 行起、第 755 行結束」「DELETE 在第 443 行」寫成實測值。實作落地後，`schema_rbac.sql` 的 RETIRED 標題實為第 205 行，`DELETE FROM role_permissions;` 為第 885 行，`INSERT INTO role_permissions` 為第 887 行。設計本身已警告「不要寫死 445／755」，且實作的定位方式（以 `_SQL_INSERT_ANCHOR` 錨定，見 `test_rbac_story_ids_seed.py:322`）符合該警告，所以不影響實作。但這又是「事實對、行號過期」的引用。產出已凍結，作者不能改。 | 不需改設計。後續讀者若要複驗，以字串錨點（`INSERT INTO role_permissions`、`RETIRED`）定位，不用行號。建議在關卡紀錄中註明這些行號是設計當下的快照。 | New |
| R-02 | Minor | construction/rbac-story-ids/nfr-design/security-design.md §六（RR-1）與 §七 Network exposure 列 | §七 把 Network exposure 面向只落在 RR-1 的承接站（D-16）。但本單元的實際對外揭露面是另一件事：`user_router.py:327` 的 `/roles/catalog` 是未驗證端點，現在會多揭露 K1 至 K4 四個中文標籤，即「統一入口頁」「專案／系統階層」「專案成員管理」「需求欄位」。這個決定在程式端 `user_router.py:96-101` 的註解與 `BR4.5` 已有記錄（照 J3a／J3b 先例發布，不揭露類別的變化），但 nfr-design 的 Network exposure 列沒有引用它。D-16 寫「每次回應多 4 列；不改變可觸發性」，只談了 DoS，沒有談資訊揭露。 | 不阻擋。若日後重開本站，在 §七 Network exposure 列補一句指向 `BR4.5` 的揭露判定。否則在 `operation` 的 `observability-setup` 承接 RR-1 時，一併把「公開目錄的揭露內容」列進同一個觀測項。 | New |
| R-03 | Minor | construction/rbac-story-ids/nfr-design/security-design.md §五（D-13、D-14、U3-A1 至 U3-A3 與其殘餘風險） | 設計明寫 U3-A1 至 U3-A3 只有三個文件錨點，沒有機械強制。`unit-of-work-story-map.md` 只把 `US1.4`（第 48 行）與 `US9.2`（第 62 行）指給 U3，沒有任何 `US12.*`，所以這三條授權行為在 `U19` 端沒有第二個追溯支點。D-14 拒絕反向測試的理由正確：那會製造一條 U3 依賴 U19 的反向邊。「若 U19 設計站沒承接，那是 U19 的缺口」這句話也是誠實的。但這是已知會被忽略的路徑，`project.md` 已記過多次指派落空。 | 不阻擋。請 `U19` 的 functional-design 站開工時，把 `U3-A1` 至 `U3-A3` 與 `D-15`（`BR7.4` 的 PBT 義務）列為必讀的上游項，並由該站的審查者確認承接。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀取 `rbac.py`、`database.py`、`user_router.py` 的唯讀 grep | logger 名、log 格式、`database.py:186` 重複 log、K1 至 K4 標籤皆與設計一致 | 設計與落地沒有矛盾 |
| 讀取 `schema_rbac.sql` 的唯讀 grep | 單一 `INSERT INTO role_permissions` 區塊仍成立；行號已位移 | 見 R-01，錨點式定位仍有效 |
| 檢查 `aidlc-state.md` 的 Stages to Execute／Skip | 4.4 在執行清單內，4.7 在 skip 清單內 | D-16 的指派成立 |
| 檢查 `unit-of-work-story-map.md` | U3 只對應 `US1.4`、`US9.2` | R-03 的前提屬實 |
| 未執行測試與 lint | 依 brief 禁止產生快取 | 測試是否綠燈未獨立驗證，只確認測試檔存在且涵蓋設計所列斷言 |
