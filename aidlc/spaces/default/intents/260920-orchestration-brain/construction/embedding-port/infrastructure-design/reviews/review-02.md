## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U6 embedding-port 是 library 單元，本站只產出 cicd-pipeline 與 traceability，範圍界定正確。修訂 1 已處置前次 review-01 的 R-01 至 R-05（Q2 反轉為遵守 NFR8.1、七道環境檢查逐條判定、job 圖重寫、H-I3 以呼叫既有驗證函式關閉缺口），且已落地的程式與設計一致：deploy compose 的 EMBEDDING_TIMEOUT_SEC 為無 fallback 形式，render-env.sh 與兩份 .env.example 皆有此變數，repo-contract 已有 validate_embedding_provider_value.py step，deploy.yml 有部署後的資料面健康檢查（會讓啟動失敗變成部署紅燈）。唯一較實質的問題是 traceability.json 的 NFR3.2 列仍描述被反轉前的 Q2=A，與修訂後的 NFR8.1 列和 cicd-pipeline 第二節互相矛盾；其餘為 Minor。無 Critical，Major 1 項，判 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/embedding-port/infrastructure-design/traceability.json 的 NFR3.2 列 target | 修訂 1 已把 Q2 反轉（timeout 變數進部署 compose、render-env.sh、deploy/.env.example、backend/.env.example 皆要改，七道檢查中觸發三道），同檔 NFR8.1 列與 cicd-pipeline.md 第二節都已更新；但 NFR3.2 列仍寫「timeout 變數只進 backend/.env.example、不進部署 compose（[Q2]=A），故觸發 validate_local_dev_template_is_complete() 而不觸發另外三條環境檢查」。這正是前次 review-01 R-01 指出的「設計文字與追溯表各說各話」同一形狀，在修訂時漏改一列。下游若讀此列會得出與 NFR8.1 逐字相反的同步範圍。此處的設計主張是錯的，cicd-pipeline.md 與已落地程式（compose 第 124 行、render-env.sh 第 138 行）才是對的。 | 把 NFR3.2 列 target 改為與第二節一致（timeout 變數進部署 compose 無 fallback、觸發 #2、#3、#6 三道檢查、名稱落地為 EMBEDDING_TIMEOUT_SEC，對應 H-N4）。並依既有規則掃描全部產出，確認再無其他列殘留 Q2=A 的舊敘述。 | New |
| R-02 | Minor | construction/embedding-port/infrastructure-design/cicd-pipeline.md 第一節 job 圖與各處行號引用 | 本檔引用的 ci.yml 行號（gate :55、repo-contract :141、frontend :169、backend :233、docker-build :299、OpenAPI :280、WS :291）與現況不符（現為 frontend :178、backend :242、OpenAPI :294、WS :305、docker-build :628），且 job 圖只列四個下游 job，現況另有 memory-schema 與 tests_pg 相關 job（:322、:565）。render-env.sh 的 :124-127 現為 :134-138。這些是設計後其他單元合併造成的漂移，不是設計當時的錯，但產出自稱「逐一核對」，行號已無法機械複驗。 | 在檔頭註明引用行號對應的是撰寫當時的版本與日期，或改以 step 名稱而非行號引用。不需重寫結論，結論（四個 job 平行 needs: gate、本單元只觸發 repo-contract 與 backend 單元測試）仍成立。 | New |
| R-03 | Minor | construction/embedding-port/infrastructure-design/cicd-pipeline.md 全檔 | ADR-0006 四個面向（IAM、encryption、network exposure、audit logging）在本檔零命中（grep ADR-0006 為 0）。實際內容涵蓋 network exposure（ollama 無 ports:、零新增暴露面）與 secrets（第五節零 secret），但 encryption 的殘餘風險（明文傳輸 RR-1）只在 traceability NFR7.3 一句帶過，IAM 與 audit logging 完全沒有判定。library 單元零基礎設施，多數面向判為不適用是合理的，但 project.md 要求以逐項判定表呈現並附不適用理由，不得留空白。 | 在 cicd-pipeline.md 補一張四面向判定表：IAM 不適用（無新身分與權限）、encryption 沿用 nfr-design 的 RR-1、network exposure 引用第一節 docker-build 列、audit logging 指向 nfr-design 的 logging 設計與 startup INFO，各附理由。 | New |
| R-04 | Minor | construction/embedding-port/infrastructure-design/cicd-pipeline.md 第六節 H-I3 與 traceability.json 的 NFR7.1 列 | NFR7.1 是主機名驗證，但 H-I3 只規定驗 EMBEDDING_PROVIDER 的值在允許集合內，未涵蓋 OLLAMA_BASE_URL 等其餘三個變數，也沒說 CI 如何從 render-env.sh（bash heredoc 內的字面值）取出待驗的值。已落地的 scripts/validate_embedding_provider_value.py 確實走 resolve_provider_selection 並涵蓋更多變數，所以實作比設計完整；問題是設計把 NFR7.1 標 OK 的依據窄於它宣稱的範圍。 | 在 H-I3 或 NFR7.1 列補一句：step 驗的是 D-1 驗證的全部變數（不只 provider 名），並註明取值方式留給 code-generation。設計窄、程式寬，以程式為準。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 比對 deploy/docker-compose.deploy.yml、deploy/render-env.sh、deploy/.env.example、backend/.env.example 的 EMBEDDING_TIMEOUT_SEC | PASS | 四處皆已落地，與修訂 1 的 Q2 反轉一致，R-01 的錯誤只在 traceability 的 NFR3.2 列 |
| 比對 ci.yml 的 repo-contract step 與 validate_embedding_provider_value.py | PASS | H-I3 已落地，腳本不自行列舉允許值，import 同一份 ALLOWED_PROVIDERS，符合禁止第二份清單的要求 |
| 比對 deploy.yml 的部署後健康檢查 | PASS | 有資料面 401 健康檢查與 rollback，啟動期設定錯誤會成為部署紅燈，cicd-pipeline 第四節的失敗路徑描述成立 |
| 比對 ci.yml 行號與 job 圖 | 漂移 | 見 R-02，為後續單元合併造成，結論未受影響 |
| grep ADR-0006 於 cicd-pipeline.md | 0 命中 | 見 R-03 |
