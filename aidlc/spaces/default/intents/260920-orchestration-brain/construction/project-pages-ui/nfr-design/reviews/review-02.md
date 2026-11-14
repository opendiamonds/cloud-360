## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本站三份產出（performance-design、security-design、logical-components）自洽，並與已落地程式吻合：固定訊息常數與寫入守門簽章（hierarchy_facade.py:114、:273-278、:292-302、:318-334，皆必填、無預設的 keyword-only 參數）、UNION 可見性定義（membership_service.py:336-378，一條 SQL）、索引九個落點（models.py:595、schema_rbac.sql:609、run_meta_schema_migration.py:118／:176）都對得上設計。主要風險是前次 review-01 的 Major 仍留在凍結的產出裡：其餘端點仍以 403 對 404 洩漏專案與系統的存在性，而 §八 第 4 項把它推給別的單元。這一項需要在關卡上由人知情接受。其餘為三項前次已提的 Minor，以及一項新的 Minor。Major 只有 1 項，依規則判 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/nfr-design/security-design.md > 八 殘留 第 4 項（:252-253）；七 ADR-0006 Network exposure 格 | 前次 review-01 已提 R-01，產出凍結後仍未處置。第 4 項寫「其『不存在 vs 不可見』是否可區分由那兩個單元自己的規則管」，Network exposure 格卻主張固定訊息使 id 枚舉只得到同一句 404。實讀 membership_facade.py：成員頁各方法先呼叫 _assert_project_exists（:118；:191、:204、:221、:248、:288 皆為入口），不存在回 404；存在但非成員則走 MembershipForbidden（:114／:162／:173），即 403。所以成員頁現況就能以 403 對 404 區分專案存在與否，本單元五條路徑的逐位元相同並未關閉整體存在性預言機。「由別的單元管」的措辭讓核可者誤以為已有規則在管，實際沒有。這一邊（現況可區分）是對的，設計的 Network exposure 判定在整體層級偏樂觀。 | 把第 4 項與 Network exposure 格改寫為已實查的事實：成員頁與需求欄位端點現況為 403 對 404 可區分，附行號；說明本單元裁決範圍只涵蓋五條路徑。在核可關卡明列為待使用者知情接受，或另開項目要求 U19／U24／U20 的非成員一律回 404。不得再用「由那兩個單元自己的規則管」帶過。 | New |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/nfr-design/security-design.md > 二之四 靜態鎖 第 2 條；二之五 突變 G5（:167） | 前次 review-01 已提 R-02，仍在。靜態鎖第 2 條豁免「接收者是 hierarchy_service 模組名」的呼叫，且只掃屬性呼叫。router 若直呼 hierarchy_service 的 delete_project，或以 from-import 裸名呼叫，既跳過 K2 又跳過守門，靜態鎖仍綠。G5 只涵蓋 router 傳 lambda，不涵蓋這條旁路。設計把靜態鎖寫成關閉繞過的機制，宣稱強度高於實際。 | 靜態鎖加一條：hierarchy_service 的 create_system／delete_project／delete_system 在 backend/ 非 tests/ 內只准出現在 hierarchy_facade.py（Attribute 與 Name 兩種形式皆掃），並加對應突變；或在 §八 如實列為殘留。 | New |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/nfr-design/security-design.md > 二之三 測試矩陣 (e)；二之五 突變 G3 | 前次 review-01 已提 R-03，仍在（全檔 grep 「(e')」為 0）。守門早於 409 的案例 (e) 只涵蓋 delete_project。delete_system 也有自己的 409（底下仍有 N 張架構圖，訊息帶張數），被移出的擁有者若守門被誤置於 service 之後，會由張數探測到內容；矩陣沒有 delete_system 版本，G3 也只點名 (e)。 | 補 (e') 被移出的擁有者對「底下仍有架構圖」的系統刪除須得 404 而非 409，並讓 G3 對 delete_system 也各自適用。 | New |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/nfr-design/logical-components.md > 三 索引與遷移的落點（九項） | 前次 review-01 已提 R-04，設計仍只列 9 項，未列 schema_rbac.sql 檔頭涵蓋說明與檔尾驗證註解。已落地的程式已補上（schema_rbac.sql:14 與 :1279），所以這邊是設計落後於程式，程式是對的。 | 在 §三 補第 10 項，記錄檔頭涵蓋說明與檔尾驗證註解，使設計與程式一致；已落地則於 code-summary 註明。 | New |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/nfr-design/performance-design.md > 一之一 FanoutQueue 介面；一之三 | 新發現。cancel() 使尚未發出的 task 的 Promise 以 FanoutCancelled 拒絕，文字說「呼叫端已有 cancelled 旗標，一律忽略」。但 enqueue 回傳的 Promise 若呼叫端只在 .then 處理而沒有 .catch，卸載時 P 或 2S 個拒絕會變成 unhandledrejection。本單元的 e2e 若監聽 pageerror 或 console，PPN-04 的情境可能因此變紅，而設計沒有規定呼叫端必須吞掉 FanoutCancelled。這是設計沒有指名「誰吞」的缺口。 | 在 §一之二 或 §一之三 明寫：呼叫端 .catch 必須辨識並吞掉 FanoutCancelled（其餘錯誤寫入 failed），並在 PPN-04 的測法加一條「卸載期間無 unhandledrejection」斷言與對應突變。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀取 hierarchy_facade.py、hierarchy_service.py、hierarchy_router.py | 常數 :114；三個寫入方法 project_visible 必填（:273、:292、:318）；router 三處傳入（:261、:291、:318） | 與 security-design 簽章與 logical-components 改動清單相符 |
| 讀取 membership_service.py:322-378 | UNION 的成員半與擁有者半（零成員列才生效）；is_project_visible 外層帶 project_id，一條 SQL | 與 performance-design 二之一逐字相符 |
| grep ix_project_members_user_id | models.py:595、schema_rbac.sql:609／:14／:615／:1279、run_meta_schema_migration.py:118／:176 | 索引九個落點已落地；R-04 的檔頭與檔尾兩處程式已做、設計未列 |
| 讀取 membership_facade.py 的 _assert_project_exists 與 MembershipForbidden | 成員頁不存在回 404、存在但非成員回 403 | 確認 R-01 屬實 |
| grep 「(e')」於 security-design.md | 0 命中 | 前次 R-03 的修正未進產出 |
| 未執行測試、python、npm | 依指示僅讀檔與 grep | UNION 索引選用屬 planner 行為，設計已明講不設 EXPLAIN 斷言 |
