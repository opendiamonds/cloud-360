## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

hierarchy-data 的 nfr-design 產出（security-design.md、traceability.json、nfr-design-questions.md）已凍結，而前次 review-03 提出的 2 項 Critical 與多項 Major 在凍結的產出裡仍然存在，經本輪逐項重新核對：SEC-2 與 Encryption 判定的前提（遷移在容器內執行）與已交付的實際呼叫方式（宿主機手動指令）不符；問題檔仍保留已被設計檔自己判為過度宣稱的「把 SEC-4 變強了」；traceability 仍寫「該題在此結案」；「五個步驟」與實際 6 步不符。ADR-0006 四面向各有落點，這一點成立，但其中 IAM 特權操作與 Encryption 兩面的前提有缺口。因 Critical 與 Major 數量超過門檻，判 NOT-READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Critical | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-data/nfr-design/security-design.md > 一、IAM（特權操作）列與 Encryption 列 | 前次 review-03 R-01 已提，仍未處置。SEC-2 宣稱遷移沿用 compose 內插的 DATABASE_URL 而不新增設定面；但該值（deploy/docker-compose.deploy.yml:85）是 backend 容器的環境變數，主機名 db 只在 compose 內網解析。已交付的呼叫方式是宿主機手動指令（DEPLOY.md 的 cd backend && python scripts/run_hierarchy_migration.py）。操作者因此必須自備 DSN，這正是 SEC-2 宣稱不存在的設定面；若為了連線而發佈 db 的 port，則直接推翻 Encryption 判定自己寫下的界線（db 不對外且同主機）。ADR-0006 的 IAM 與 Encryption 兩面前提因此未建立。以已落地的呼叫方式為準，設計主張是錯的一方。 | 把 SEC-2 收窄為在 backend 容器內執行時才沿用該憑證，並指名宿主機路徑的 DSN 由誰供應、權限等級為何；或將遷移必須在容器內執行寫成具名的消費端義務並進殘餘風險表。Encryption 界線補一句：發佈 db port 即為該判定的失效事件。 | New |
| R-02 | Critical | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-data/nfr-design/nfr-design-questions.md > 收齊答案後的跨題矛盾檢查表，Q3=A × SEC-4 條件性列（約第 115 行） | 前次 review-03 R-02 已提，仍存在。該列逐字寫「把 SEC-4 變強了……要麼有可信的行動者，要麼這次異動根本沒發生」，而 security-design.md 一、Audit logging 列已明文判定那是過度宣稱，traceability 的 SEC-4 也已改為 Deferred。同一輪的正式作答紀錄與設計產出，在 ADR-0006 audit logging 的判定上直接對撞。 | 在該列就地加更正註解撤回判定，改寫為只關掉解不出行動者那一支，解出但指錯人與可信的定義仍屬 OQ-H3，SEC-4 第 (4) 項仍為 Deferred；不改 [Answer]: A 本身。 | New |
| R-03 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-data/nfr-design/traceability.json > coverage U4-R4 的 target | 前次 review-03 R-03 已提，仍存在（該字串在檔內命中 1 次）：target 仍寫「本站是 OQ-3／S-4 的落點，該題在此結案」，與 security-design.md 開頭已更正的說法（結案的是 S-4，OQ-3 本體屬 U5）矛盾。機讀追溯與敘述相反，下游會把 OQ-3 當成已結案。 | 將 target 改寫為本站結案的是 S-4，OQ-3 本體未結案，落點為 U5 的 nfr-design。 | New |
| R-04 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-data/nfr-design/security-design.md > 五、殘餘風險表「五個 CI 步驟目前沒有承載者」列；三、S-6 的處置段；traceability.json > S-6-disposition | 前次 review-03 R-04 已提，仍存在。文中斷言若 ci-pipeline 與 U5 都沒發生則 U4-V1 至 U4-V5 全部落空。已落地的程式不支持這句：backend/tests/test_hierarchy_migration.py（874 行、15 個案例，見 code-generation/code-summary.md）已隨交付存在，包含重跑與不變量案例，U4-V1 至 V5 的行為面並非沒有承載者，只是未接進共用的真實 PostgreSQL job。設計主張過度悲觀；已落地的測試是對的一方。 | 將殘餘風險改寫為已有 SQLite 層的單元測試承載行為面，缺的是真實 PostgreSQL job 這一層；並更新 S-6 的處置段與 traceability 的對應描述。 | New |
| R-05 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-data/nfr-design/security-design.md > 四、S-11 列；traceability.json > reverse S-11 的 target | 前次 review-03 R-05 已提，仍存在。上游 SEC-4 的條件含不得預設填工作階段擁有者；該句只出現在 一、Audit logging 的敘述格（全檔命中 1 次），S-11 列（對 U12 的消費端義務）命中 0 次。義務沒有進入指派給 U12 的契約，下游實作者只讀 S-11 時會漏掉最容易造成稽核錯指的約束。 | 把不得預設填工作階段擁有者併入 S-11 的義務文字與 traceability reverse S-11 的 target。 | New |
| R-06 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-data/nfr-design/security-design.md > 三之二，截止欄位與索引兩列 | 前次 review-03 R-06 已提，仍存在。兩列把 created_at 與其索引寫成本站現在才下、尚無實作的決定（「必須被指名，否則 S-5 的實作者得自己猜」）。實際上 schema_rbac.sql 已含 ix_diagram_change_records_created_at（約 430 行），決定已交付。設計與落地敘述矛盾，落地是對的一方。 | 改寫為已於 schema_rbac.sql 落地的決定，並寫明引用位置，或標示本段為追認而非待定。 | New |
| R-07 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-data/nfr-design/security-design.md > 三，準確的框架段與步 1 | 前次 review-03 R-07 已提，仍存在。步 1「建 schema」與 U5 建立共用 job 時 schema 由誰建、順序如何，依然零交代；U5 的迭代需要就地確認這件事，也未寫明。這是跨單元契約的一端懸空：步 1 的前提誰擁有無法指名。 | 寫明步 1 與 U5 schema 建立的所有權與順序，並把需要 U5 就地確認列為具名交接事項。 | New |
| R-08 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-data/nfr-design/security-design.md > 三 步驟表（共 6 列）對照第 85、88、161 行與 traceability 的 S-6-disposition | 前次 review-03 R-08 已提。步驟表有步 1 至步 6 共 6 列，三處散文與 traceability 都寫五個。被漏掉的是步 6（對應 SEC-4 的計數斷言）。 | 統一為六個步驟，並讓步 6 的 SEC-4 對應在散文中可見。 | New |
| R-09 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-data/nfr-design/security-design.md > 一、IAM 列「設計」欄 | 前次 review-03 R-09 已提。「projects／systems 的執行期存取一律經 K-07 的 facade」是對他人行為的斷言，與同格殘餘欄記載的繞過路徑矛盾。 | 收窄為本單元不提供任何存取路徑。 | New |
| R-10 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-data/nfr-design/security-design.md > 四，S-10 列「落點與風險」欄 | 前次 review-03 R-10 已提。U5 的 nfr-design 為 CONDITIONAL，被 skip 時 OQ-3 無承接站；現文只寫到被 skip 則無結案，未寫判定 skip 的人須重新提交給使用者。 | 明寫無承接站，判定 skip 的人須重新提交給使用者。 | New |
| R-11 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-data/nfr-design/security-design.md 第 14、20 行；nfr-design-questions.md 第 10 行 | 前次 review-03 R-11 已提。引用 requirements.md:597、:385 的行號在上游 requirements.md 成長後已指向別處（上游 622 行增至 813 行）。 | 重新核對並更新全部四個引用點的行號。 | New |
| R-12 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-data/nfr-design/security-design.md > 一、Audit logging 列 | 該格殘餘欄文字「從靜默指錯人縮到靜默指錯人與解不出就整體失敗的後者已被消除」前後兩端同詞，語意不通；S-9 也在第 110 行被引用（有序步驟），但本檔沒有定義 S-9，讀者無法解析。 | 重寫該句；為 S-9 補上定義或指向其來源。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| grep 逐項重核 review-03 的 R-01 至 R-11 | R-01、R-02、R-03、R-04、R-05、R-08 仍存在；R-06 的索引已落地於 schema_rbac.sql | 凍結的產出未處置前次發現，故逐項重列並註明前次 review-03 已提 |
| 步驟表列數統計 | 6 列，散文寫五個 | 確認 R-08 |
| 閱讀 code-generation/code-summary.md | 遷移模組 479 行、測試 874 行共 15 案例 | 作為 R-04、R-06 判斷哪一邊正確的依據 |
