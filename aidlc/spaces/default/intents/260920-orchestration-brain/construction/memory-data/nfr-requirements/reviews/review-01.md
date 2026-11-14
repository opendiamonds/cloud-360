## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

三份產出（security-requirements.md、tech-stack-decisions.md、traceability.json）精簡，但以引用上游代替重寫是足夠的：13 條規則由 functional-design 承載，本站只處理三項新定案（NFR6.1、NFR6.2、NFR7.2）。這三項各有二元判準，且 NFR7.2 的 90 天自身時鐘、清除稽核不留稽核的無終止遞迴論證、OPEN-N5-2 的雙資料清除，均與已落地的 schema_rbac.sql:513-533 與 memory-retention-purge.yml 一致。主要問題有兩項：pgvector 可用性「未查證」的前提，在 repo 一次 grep 即可答覆且實際為真；以及全部效能與容量類 NFR 被標 N/A，理由與後續落地的向量索引不符。兩者皆為 Major，未超過 2 項，故判 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/memory-data/nfr-requirements/tech-stack-decisions.md 第一節末段與第三節；traceability.json open_items OPEN-N5-3 與 coverage NFR8 | 設計稱「既有 PG image 是否含 vector 擴充未查證，標準 postgres:\*-alpine 不含它」，並把它列為部署層風險、讓 NFR8 的 N/A 附帶條件成立。實際上 deploy/docker-compose.deploy.yml:40 與 deploy/docker-compose.test.yml:51 皆為 pgvector/pgvector:pg18，ci.yml:343 的 memory-schema job 也用同一 image（該處註解已寫明理由）。本檔自己引用 compose:52 的 db_pg18 卻漏看 :40 的 image 行。另第三節寫 N-2 用 postgres:16-alpine「且須含 pgvector」，與 volume 為 PG 18 系互相矛盾（16-alpine 不可能含 pgvector）。設計是錯的一邊，已落地的 compose 與 CI 是對的。 | 在 OPEN-N5-3 加註已由 compose:40、test.yml:51、ci.yml:343 解決，NFR8 的條件式 N/A 一併更正；把 N-2 的 image 改寫為 pgvector/pgvector:pg18。這是一次 grep 即可查出的事實，不應留成開放缺口。 | New |
| R-02 | Major | construction/memory-data/nfr-requirements/traceability.json coverage NFR3、NFR4 與 security-requirements.md 第五節 | 本單元零量化的效能、容量或可用性 NFR。NFR3（首字回應時間）以「本單元是 DDL，不在串流路徑上」標 N/A，但 memory.memory_records 是每回合記憶檢索的讀取目標；後來 schema_rbac.sql:503 新增 ix_memory_records_embedding_hnsw（vector_cosine_ops）就是檢索延遲的承載，卻沒有任何本站 NFR 作為依據：沒有每使用者記憶列數上限、檢索延遲目標、索引建置與重嵌入（embedding_model 更換）成本、episodic 90 天清除窗口下的表增長估計。第五節 ADR-0006 表也未量化。 | 補一條簡短的資料面容量與檢索延遲 NFR（可引用 NFR3 的目標，數字至少給量級與驗證方式），或明確記錄「量化延遲 NFR 由 U8 承擔」並指名該單元的 NFR 條號；更正 NFR3 的 N/A 理由。 | New |
| R-03 | Minor | construction/memory-data/nfr-requirements/security-requirements.md 第一節 NFR6.2 判準 | 判準「DATABASE_URL 主機名非 localhost」只對部署範圍成立：ci.yml:275 等處的 CI 與本機 dev 皆為 localhost，且 validate_env_contract.py 只擋 deploy 範本的 localhost 滲透，並不驗證「主機名等於 db」。判準未限定範圍，字面上被 CI 自己違反。證據支撐面（db 無 host port）是對的，deploy/docker-compose.deploy.yml 的 db 服務未發布埠，但本檔未將它列為判準。 | 判準限定為部署範圍，並補上「db 服務不發布 host port」作為第二個可檢查事實。 | New |
| R-04 | Minor | construction/memory-data/nfr-requirements/security-requirements.md 第三節與 traceability.json OPEN-N5-1 | 靜態加密為運維承諾，設計誠實揭露其不可驗證，這點正確。承接鏈寫「infrastructure-design（CONDITIONAL）轉 code-generation」，已由 DEPLOY.md 約 :571-:580 與 :1455-:1497 的 LUKS 判定步驟落地（含 lsblk 判定指令），故承接成立；但本站 traceability 仍把 NFR6.1 標 status OK，與「運維承諾而非閘門」的自述略有落差。 | 將 NFR6.1 的 coverage status 改為指向 DEPLOY.md 的實際落點，或標為 accepted-gap，避免被讀成已驗證。 | New |

### Validation Tool Results
| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀取 compose、ci.yml、schema_rbac.sql、purge workflow、DEPLOY.md 的對照抽查 | NFR7.2、OPEN-N5-1、OPEN-N5-2 已落地一致；OPEN-N5-3 的前提不成立 | 支持 R-01、R-04；未執行任何測試或會寫檔的指令 |
