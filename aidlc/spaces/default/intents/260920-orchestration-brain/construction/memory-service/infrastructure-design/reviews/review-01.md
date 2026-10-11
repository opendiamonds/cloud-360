## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-09T09:17:27Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | `cicd-pipeline.md §三`（「本單元不新增任何 CI job」表，`tests_pg` 行）＋ §五（分桶） | 檢索/脈絡組裝路徑（`functional-spec.md §1.2`＋`rules.md BR2.2／BR3.1／BR3.2`，由 `U11` 同進程消費）照 `nfr-design/performance-design.md §一` 的設計是**一次 SQL**：`WHERE`（可見範圍＋`embeddingModel`）與 `ORDER BY`（pgvector 距離運算子，走新增的 HNSW 索引）必須在**同一個查詢內**。SQLite 沒有向量型別、沒有 `<->` 距離運算子，這整條組合查詢在 SQLite 上**無法執行**（不是語意不同、是編不出這條 SQL），故不可能用既有 `backend` job 的 `TestClient＋SQLite` 驗。`search` 本身也沒有 HTTP 端點（§0 表第 2 列：「—（同進程，`U11` 消費）」），不在 `cicd-pipeline.md §五` 列出的「四條端點 allow/deny」裡。結果是：這條查詢「過濾＋排序必須同查詢」這個 `nfr-design` 自己強調的正確性不變量（錯了會導致 `LIMIT` 作用在未過濾集合上、回傳筆數錯、甚至洩漏不可見列進程），**在本單元的 CI 計畫裡完全沒有任何測試覆蓋**——不在「已自動化」、不在「待自動化」、也不在「只能手動」。`S14` 只斷言「索引可用且 opclass 相符」（`cicd-pipeline.md §二之一` 自己承認），不驗過濾條件與排序是否正確組合在同一查詢。§三「本單元沒有同類的語意落差——...只有向量索引不是，而它由 S14 以 psql 覆蓋」這句話因此是錯的：語意落差不只在索引，整條檢索查詢的可測性都不同於 PostgreSQL，而 S14 沒有覆蓋到查詢本身的正確性。 | 在既有 `memory-schema` job（已有真實 PG＋`schema_rbac.sql`，零新 service container）新增一條針對 `search`／脈絡組裝的斷言或測試步驟，直接驗證「可見範圍＋`embeddingModel` 過濾與相似度排序組合在同一查詢、`LIMIT` 作用於已過濾集合」這個不變量；或在 `cicd-pipeline.md §三` 如實記載此缺口而非宣稱「沒有語意落差」。兩者至少做一項。 | New |
| R-02 | Major | `cicd-pipeline.md §〇` | 「`ci.yml` 有 6 個 job；除 `gate` 外的 5 個全部且僅 `needs: gate`」與實際 `.github/workflows/ci.yml` 不符——目前共 7 個 job key（`gate`、`repo-contract`、`frontend`、`backend`、`memory-schema`、`concurrency`、`docker-build`），非 `gate` 的有 6 個不是 5 個。本檔聲稱「沿用前站實測，不重新推導」並指向 `construction/membership-service/infrastructure-design/cicd-pipeline.md §一之二`；但那份文件記載的「6 個 job」是 `U19`／membership-service **自己提案新增 `concurrency` job 之前**的基準數，而該提案已落地於目前的 `ci.yml`（本檔 §三 自己也列出「本單元不觸發：... concurrency job（`U19` 的 `FOR UPDATE` 情形不適用於這裡）」，證明作者知道這個 job 存在）。同一份文件的 §〇 與 §三 因此互相矛盾——§〇 的機械事實未對照目前真實的 `ci.yml` 重新驗證，只是原樣轉抄了一個已被自己後續段落推翻的舊數字。 | 重新對照目前的 `ci.yml` 核實 job 總數（7 個，含 `gate`；非 gate 6 個），更正 §〇 的敘述，並在引用其他單元「前站實測」時加一句「本站已重新核對仍成立／已有變動」的判定，而不是逐字複製。 | New |
| R-03 | Minor | `monitoring-design.md §四`「候選 SLI（待承載機制，`N8-10` 承接）」 | `N8-10` 在本站四份產出與上游 `nfr-requirements/`、`nfr-design/` 任一檔中都只作為一個 id 出現，查無其定義來源（可能是更早期 intent 或另一單元的待追蹤 id，但本檔未給出可追溯的出處），讀者無法判斷它是否真的存在一個會承接此事項的機制。 | 補一個可核對的來源（檔案＋章節，或明確標註「本站新開的待追蹤項，尚無承接站」），不要讓一個查無出處的 id 看起來像已有人接手。 | New |

### 摘要
- `new-design-problem`: 2（R-01、R-02）
- `pre-existing-unreviewed`: 0
- `propagated-from-upstream`: 1（R-03，`N8-10` 可能源自更早的站，但本站引用時未核實其可追溯性，故記在本站）

### 覆蓋範圍

**已查證**：
- 「零基礎設施」四項零（容器／監聽埠／環境變數／secret／依賴）：逐項對照 `backend/requirements.txt`（diff 為空，且確認無 `pgvector`／`vector` python 套件，與「索引全走原生 SQL、不走 ORM 向量型別」的設計一致）、`deploy/`、`.env.example` 未被本單元提及改動；新 `POST`／`DELETE` 回應變化／分頁參數三項契約變更逐一核對 `functional-spec.md`（`[FD4]`=A 新增端點）、`nfr-design/security-design.md`（`[D1]`=A 收斂 404/403）、`nfr-design/scalability-design.md`（分頁）三份上游，確認屬實。
- `I)` 區塊歸屬與既有環境取得路徑：核對 `schema_rbac.sql:440`（`-- I) U5 memory-data`）與 `backend/scripts/run_meta_schema_migration.py`（`BLOCKS_TO_RUN = ("X", "I", "J")`、`EXPECTED_INDEXES`、`verify_postconditions` 在同一交易內執行並於缺項時 `raise RuntimeError` 觸發 `engine.begin()` 回滾）——「加清單不加 SQL 會 rollback、加 SQL 不加清單會悄悄不被驗證」兩個方向的機制性斷言皆查證為真。
- `verify_memory_schema.sql` 現有斷言到 `S13`（U9 的保留系統 actor）屬實，`S14` 編號正確；該檔頭「12 條斷言 S1–S12」加 U9 的 `S13` 與本檔敘述一致。
- `S14` 落點（既有 `memory-schema` job，不新開 job）與 `ci.yml:308-407` 實際步驟結構一致；OpenAPI drift 步驟確在 `backend` job 的 `:289`（經核對行內容，非僅行號）。
- `I8-1`～`I8-4` 四項誠實限定逐一核對：均為「本站不建、寫下判準即可」形式的已承認限制，未發現需要指派但未指派給任何下游站的死指派；`code-generation`（§1.1 的 blocking 檢查項）與 `tcms-test-cases`（§五）兩個轉交目標都是 `ALWAYS` 且確認在本單元尚未執行（`construction/memory-service/` 目前只有 `functional-design`／`nfr-requirements`／`nfr-design`／`infrastructure-design` 四個目錄），落在游標之後，無 CONDITIONAL 轉移目標問題。
- 審查優先序 (b)：`run_meta_schema_migration.py` 的 `K-15` 不塞資料的契約論證（索引是 DDL 非資料，故可放 `I)`）查證成立。
- 審查優先序 (g) 的抽樣：`schema_rbac.sql:440`、`ci.yml:289`、`ci.yml:308-320` 三處引用內容與行號皆核對一致。
- 本站四份產出的 `ARTIFACT_CREATED`／`ARTIFACT_UPDATED` 稽核事件確實存在（audit shard 可查到 4 個檔案的寫入事件，皆經 `Write` 工具），**不是**上游 `nfr-design` 站那種漏記審計事件的失敗模式——此點特別核對過，結果是乾淨的。
- NFR 覆蓋面核對：`infrastructure-design/traceability.json` 的 30 個 upstream_ids 恰為 `nfr-design/traceability.json` 35 個 ids 減去 5 個明確標記「N/A，擁有者為 U9」的 id（`NFR6.10`／`NFR7.10`／`NFR7.15`／`NFR7.2`／`NFR8.10`），排除理由逐一查證成立（這些確實是 U9 memory-purge 已交付的需求）。

**未深入查證**：
- `tcms-test-cases` 分桶預判（§五）中「待自動化」各項是否真的都能在不新增任何基礎設施下被 `TestClient`／`hypothesis` 驗到，只核對了結構性論證，未逐條模擬每個測項的可構造性（例如 `NFR7.29` 的 limit 上限測試是否真能用 `TestClient` 在 SQLite 下重現）。
- `DEPLOY.md`／`schema_rbac.sql` 的 `I)` 區塊目前尚未真的新增該 HNSW 索引（這是預期的——屬 `code-generation` 的工作），故四項 blocking 連帶義務的「漏做後果」只核對了機制推理，未能核對未來實際落地時是否真的逐一完成（這本來就不是本站該驗的）。
- `monitoring-design.md §三` 的枚舉偵測判準（`I8-1`）與 `observability-design.md` 的欄位白名單是否完整一致，僅讀了本站引用的段落，未重新核對 `nfr-design/observability-design.md` 全文。
- CI 的 `concurrency` job 與 `docker-build` job 的 `if` 條件、`needs` 細節未逐行核對，僅確認其 job key 存在。

VERDICT: NOT-READY
