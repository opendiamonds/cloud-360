## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

memory-service 在本站的基礎設施增量確實只有一個 HNSW 索引，已落地的程式與設計一致：schema_rbac.sql 第 503-504 行有 ix_memory_records_embedding_hnsw（vector_cosine_ops），run_meta_schema_migration.py 第 168 行已列入 EXPECTED_INDEXES，DEPLOY.md 第 2.2.12 節已同步，verify_memory_schema.sql 已有 S14 與 S15。ci.yml 的 7 個 job key 與「除 gate 外 6 個皆 needs gate」經核對屬實。未發現 Critical。主要缺口有二：對外 404 收斂（D1=A）之後日誌成為枚舉偵測的唯一面，但設計沒有寫明日誌保留期；S15 的「單一 SQL」不變量，設計文件的說法比實際保護力強。其餘為引用與完整性上的 Minor。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/memory-service/infrastructure-design/monitoring-design.md 第三節與 §3.1 | D1=A 讓「帶 reason=owner 的 404 日誌」成為枚舉探測的唯一可見面（ADR-0006 audit logging 面向），文件卻只說「零新保留規則」，沒有寫日誌實際保留多久。deploy/docker-compose.deploy.yml 第 62-67 行是 json-file 且 max-size 50m 的輪替，也就是證據會被滾動覆寫，保留期取決於流量而非政策。文件對該面向的判定「零基礎設施增量」因此忽略了「唯一偵測面的保存期是隱性的」。 | 在 monitoring-design.md 寫明現行日誌輪替參數（max-size 與 max-file）與推估的保存期，並明說此保存期對 D1=A 的偵測意義；若不足，記為有編號的待辦並指派承接站，或寫「無自然承接站」。 | New |
| R-02 | Major | construction/memory-service/infrastructure-design/cicd-pipeline.md 第三節 §3.2 與 infrastructure-specification.md §2.3 | 文件把 S15 描述為「檢索查詢組合正確性」的覆蓋，但 verify_memory_schema.sql 第 388-403 行自己承認：S15 驗的是「這樣寫的 SQL」在真實 PG 上正確，不是 memory_service.search_records 真的這樣查；Python 側的另一半在 tests/test_memory_contract.py 的 C6。設計文件完全沒有指名 C6，也沒有寫「兩者缺一則只驗一半」。「LIMIT 作用在已過濾集合」這個本單元核心不變量，其保護力因此被文件高估；若有人刪掉 C6，S15 仍綠。 | 在 cicd-pipeline.md §3.2 與桶分類表補上 Python 側對應測試（C6）與兩者的分工，明寫 S15 是 SQL 形狀的驗證而非實作的驗證；並列出 search_records 的實際查詢（memory_service.py 第 90-96 行附近）與 S15 fixture 查詢必須保持一致的機制（誰改一邊誰改另一邊）。 | New |
| R-03 | Minor | construction/memory-service/infrastructure-design/cicd-pipeline.md 第一節（觸發閘門表）與「本單元不觸發」段 | 文件逐項列出會觸發與不觸發的閘門，並說明不觸發 WS contract drift，但漏列 ci.yml 第 313-314 行的 MCP tool drift（gen_mcp_tools.py --check），它由已提交的 openapi.json 重新產生。本單元新增 POST /api/memory/records 並改動 DELETE 與 GET 的 OpenAPI，必然改 openapi.json，所以該閘門是否被觸發必須交代。經查 backend/mcp_bridge/allowlist.json 對 memory 無命中，故多半不受影響，但文件沒有寫出這個結論。 | 補一列：MCP tool drift 閘門在 openapi.json 變更時會重跑，因 allowlist 未含 memory 端點而預期不變；並註明若日後允許清單納入，需重跑產生器。 | New |
| R-04 | Minor | construction/memory-service/infrastructure-design/cicd-pipeline.md 第一節第 2 項與 infrastructure-specification.md 第〇節 | 引用定位不準：文件多處寫 OpenAPI drift 在 backend job 的 :289，實際 ci.yml 的步驟是第 286-294 行（第 289 行落在 env 的註解中，指令在第 294 行）。另外文件內部章節引用（例如「§二之一」「§三之一」「§三之二」）與實際標題編號（2.1、3.1、3.2）不一致，讀者照字面找不到。事實正確、定位錯誤，屬 project.md 已記過的「事實對而定位錯」形狀。 | 把 :289 改為 :286-294（指令在 :294），並統一章節引用的寫法。 | New |
| R-05 | Minor | construction/memory-service/infrastructure-design/infrastructure-specification.md 第二節與第五節 | 在既有環境新增 HNSW 索引時沒有交代建索引成本：CREATE INDEX 非 CONCURRENTLY 會取得寫入鎖、記憶體與耗時隨列數成長；文件只說「空表可建」，卻沒有說明既有 192.168.10.10 環境的 memory_records 在執行第 2 步時是否仍為空（U8 之前沒有寫入端，但文件未查證），也沒有任何容量或成本估計。上游 N8-9（備份缺口）在「上游依據」表出現一次，本文件主體沒有任何 DR 或重建索引的說明。 | 加一段：既有環境執行時的預期列數與鎖影響；索引可由資料重建（無備份依賴）的說明；N8-9 的處置或承接。 | New |
| R-06 | Minor | construction/memory-service/infrastructure-design/monitoring-design.md I8-1、I8-2 與 cicd-pipeline.md I8-3、I8-4 | 四個本站待追蹤項（I8-1 至 I8-4）只有編號與理由，沒有指名承接站或「無自然承接站」；僅 N8-10 有如實記載「沒有承接站」。project.md 要求缺承接者要明寫，否則交接表看起來完整而實為死指派。 | 為每個 I8-n 補一欄承接站（附 execution 值）或明寫「無自然承接站」。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀取 ci.yml 與列出 job key | 7 個 job key（gate、repo-contract、frontend、backend、memory-schema、concurrency、docker-build） | 與設計「7 個 job、非 gate 共 6 個」一致；OpenAPI drift 實際在第 286-294 行（見 R-04） |
| 比對 schema_rbac.sql、run_meta_schema_migration.py、DEPLOY.md、verify_memory_schema.sql | 索引、EXPECTED_INDEXES、DEPLOY.md 2.2.12、S14 與 S15 皆已落地 | 設計的四項連帶義務已全部在程式與文件中兌現，設計與實作無矛盾 |
| deploy/docker-compose.deploy.yml 日誌設定 | json-file 且 max-size 50m | 支持 R-01：保存期為隱性 |
| backend/mcp_bridge/allowlist.json 搜尋 memory | 無命中 | 支持 R-03：多半不受影響，但文件未交代 |
