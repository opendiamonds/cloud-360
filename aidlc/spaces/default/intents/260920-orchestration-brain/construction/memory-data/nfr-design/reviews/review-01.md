## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本站產出精簡（security-design.md 與 traceability.json 兩份），以引用上游代替重寫的形式本身可接受：NFR6.1、NFR6.2、NFR7.2 三項新定案各有落點，occurredAt 索引這個設計決定有據（entities.md 確實未為 occurredAt 建索引，U4 有同形先例）。但引用上游這件事本身有三處不成立：被引用的四份上游檔案與一份本站檔案不存在、本站自己的章節編號被引用到不存在的節、以及清除作業的連線路徑沒有設計而直接與 NFR6.2 的不變量衝突。另有索引設計只做了一半。三項 Major 超過門檻，判 NOT-READY。限制說明：reviewer-scope 守衛不允許開啟 schema_rbac.sql 與 workflow 檔，故設計與落地程式的矛盾只能以本單元 code-generation/code-summary.md 的自述為準，未獨立複驗。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/memory-data/nfr-design/security-design.md 第「一之二」節表格；nfr-design/traceability.json ND-IDX-U5 與 OPEN-N5-2；code-generation/code-summary.md 第 13 行 | 引用承載不足，因為被引用的檔案不存在。（a）「一之二」表以 performance-requirements.md、scalability-requirements.md、reliability-requirements.md、observability-requirements.md 為四個 N/A 判定的上游依據，但 nfr-requirements/ 目錄實際只有 security-requirements.md、tech-stack-decisions.md、traceability.json 與 reviews/，這四檔不存在；（b）code-summary.md 引用「performance-design.md（本單元 nfr-design）」，nfr-design/ 只有 security-design.md 與 traceability.json；（c）security-design.md 兩處引用「§四之二」，traceability.json 引用「§四之二」「§四之三」，但本檔只有 4.1、4.2、4.3 小節，不存在這些節名。這代表四個面向（效能、擴展、可靠性、觀測）的 N/A 判定沒有任何可查的落點，讀者無從複驗。 | 二擇一：補出被引用的檔案（可為各一段的簡短判定檔），或把引用改指向真實存在的 nfr-requirements/traceability.json 的 coverage 同 id 列；同時把 §四之二、§四之三 改成 4.2、4.3，並修正 code-summary 對 performance-design.md 的引用。 | New |
| R-02 | Major | construction/memory-data/nfr-design/security-design.md 第三節 NFR6.2 與第四節 4.3、第五節 Network exposure 列 | 清除作業的連線路徑沒有設計，且與 NFR6.2 的不變量衝突。第三節把 NFR6.2 設計成「DATABASE_URL 主機名必須是 compose 內部服務名」，第五節宣稱 Network exposure「本單元零端點、零進程」故無增量；但 4.3 同時指定清除由 GitHub Actions 或 gh-aw workflow 承載（BR4.2），該 workflow 必須連到 db 服務執行 DELETE。前次 nfr-requirements review-01 R-03 已指出 db 服務不發布 host port；那麼 Actions 步驟要經由什麼通道連線（自架 runner 上 docker exec、SSH、臨時發布埠，還是另一個進入 compose 網路的容器）、用哪個資料庫角色（BR1.2 的 grant 邊界是否包含兩表的 DELETE 權限）、憑證從哪來，本站全未設計。任何一條通道若是發布埠或使用 superuser，NFR6.2 的前提與 BR1.2 的邊界即被繞過，而連線照樣成功，正是本檔第三節自己點名的靜默失敗形狀。ADR-0006 的 IAM 與 network exposure 兩面因此各缺一個落點。 | 在 4.3 新增清除作業的連線與授權設計：指名通道（建議不發布 db 埠）、指名專用最小權限角色（僅限 memory schema 兩表的 SELECT 與 DELETE 以及稽核表的 INSERT）、憑證來源（secrets 而非 variables）；並把第五節 IAM 與 Network exposure 兩列的增量從「無」改為此項。若判定屬 U9 的設計範圍，須在本站明寫並指派，不得宣稱無增量。 | New |
| R-03 | Major | construction/memory-data/nfr-design/security-design.md 第 4.2 節與第「一之二」節 performance 列；nfr-design/traceability.json ND-IDX-U5 | 索引設計只做了一半，且邏輯前後不一致。4.2 以「清除查詢以 occurredAt 為截止鍵、無讀取端會順手建索引」為由要求為 memory_audit_events 建索引，這個推理對記憶表同樣成立：BR4.1/BR4.2 的清除作業是依 memory_records.expiresAt 選列（functional-spec.md 第 91 行也這樣寫），entities.md 與本站都沒有討論 expiresAt 索引（kind=episodic 的部分索引是自然形狀）；code-summary.md 自述落地有「五個索引」，但本站設計只點名一個，其餘四個的來源無設計依據。此外，向量欄位的近似檢索索引（落地為 HNSW，見前次 nfr-requirements review-01 R-02 所引 schema_rbac.sql:503）、其建置成本、embeddingModel 更換時的重嵌入與重建、episodic 90 天窗口下的資料增長，本站以「無新延遲預算」全數 N/A；但 embedding_model 過濾是正確性要求（entities.md 與 functional-spec.md），索引是否能與該過濾並用直接決定檢索是否退化為全表掃描。這項在前次 review-01 已提且未處置。 | 補一小節索引設計：表列 memory 兩表所有索引的用途與對應查詢；明寫 expiresAt（或 kind 部分索引）的決定；說明 HNSW 索引與 embeddingModel 過濾的並用方式與模型更換時的重建策略。若確定不設計，須記為具名開放項並指派承接站。 | New |
| R-04 | Minor | construction/memory-data/nfr-design/traceability.json open_items OPEN-N5-3 與 OPEN-ND5-1，security-design.md 第一節表格 | OPEN-N5-3 的前提（既有 PG image 是否含 pgvector 未查證）已被證偽：code-summary.md 第四節記載 deploy/docker-compose.deploy.yml:40 與 docker-compose.test.yml:51 皆為 pgvector/pgvector:pg18，且前次 nfr-requirements review-01 R-01 已提過同一點。本站凍結產出仍把它當開放缺口承接，且 OPEN-ND5-1 標 blocking-downstream 但實際已落地（M8 突變驗證證實 S12 會抓到索引被移除）。設計是錯的一邊，已落地的 compose 與 CI 是對的。 | 在 OPEN-N5-3 與 OPEN-ND5-1 加註「已由 code-generation 解決」及證據位置，避免下游被舊開放項誤導。 | New |
| R-05 | Minor | construction/memory-data/nfr-design/security-design.md 第三節表格 | 不變量的適用範圍未限定。DATABASE_URL 主機名為 compose 服務名這條不變量只對部署範圍成立；CI 與本機 dev 的 DATABASE_URL 本來就是 localhost。覆蓋範圍表只列兩個情境，沒有說明「db 服務不發布 host port」這個更能直接守住前提的可檢查事實。前次 review-01 R-03 已提。 | 把不變量限定為部署範圍，並補上「deploy compose 的 db 服務不發布 host port」作為第二個可檢查事實。 | New |
| R-06 | Minor | construction/memory-data/nfr-design/security-design.md 第 4.3 節 | 兩個小缺口：（a）「先清記憶、再清稽核」的順序理由寫成「反序實際上無害但寫明可避免困惑」，等於承認順序無約束力，卻又在 OPEN-N5-2 當作設計決定承接；（b）BR4.3 要求每刪一列 episodic 記憶就寫一筆稽核事件，但記憶 DELETE 與稽核 INSERT 是否同一交易、DELETE 稽核事件是否批次化以避免長鎖，本站都沒有說。交易不原子時，失敗會留下「記憶已刪但無稽核」，直接破壞 FR4.7。 | 改寫順序理由為真實約束或刪去；明寫記憶刪除與稽核寫入須在同一交易，並指定稽核過期刪除的批次大小原則，指派 U9 承接。 | New |

### Validation Tool Results
| Tool | Result | Interpretation |
|------|--------|----------------|
| ls nfr-requirements 與 nfr-design 目錄 | 僅有 security-requirements.md、tech-stack-decisions.md、traceability.json、security-design.md | 證實 R-01 所指四份 requirements 檔與 performance-design.md 不存在 |
| grep 章節標題與引用 | 本檔無「四之二」「四之三」節，traceability.json 與本檔皆引用 | 證實 R-01（c） |
| 讀取 code-summary.md、entities.md、rules.md、functional-spec.md | 五個索引與 pgvector image 的主張以 code-summary 自述為準 | 支持 R-03、R-04；schema_rbac.sql 與 workflow 受 reviewer-scope 守衛限制未能開啟，未獨立複驗 |
