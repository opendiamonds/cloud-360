## Review

**Verdict:** NOT-READY

**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-09T00:03:18Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | `performance-requirements.md` §一 `NFR3.20`／`NFR3.21`；`nfr-requirements-questions.md` `[N1]`=B | `[N1]`=B 刻意把向量產生時間含進 `NFR3.20`／`NFR3.21`，理由是「向量產生延遲由提供者決定，須記錄當時使用中的提供者」。但本站從未查過 CI／測試環境能不能實際跑出「使用 Ollama 時」的延遲：`deploy/docker-compose.test.yml:18,102` 明文「NO ollama. EMBEDDING_PROVIDER 是 `stub`」，`backend/.env.example:120` 本機預設是 `fulltext`（此模式下連向量都不產生，見 `performance-requirements.md` 自己的表）。`.github/workflows/ci.yml` 全檔不含 `ollama`；Ollama 只在 `deploy.yml`（post-deploy staging）出現。也就是說，若 `build-and-test`（3.6）沿用既有的任一測試基礎設施，NFR3.21 要求記錄的「使用中的提供者」只會是 `stub`／`fulltext`，量出來的 P95 會接近 0，`NFR3.20` 會穩定通過——但從未測過 `[N1]`=B 真正想捕捉的 Ollama 跨容器延遲。這條門檻因此有被無聲橡皮章通過的具體風險，而七份產出與 `N8-1`–`N8-10` 沒有任何一項點出「量測場地本身不含真實提供者」這個缺口。 | 在 `performance-requirements.md` 新增一個交接項（`N8-11` 或類似），明寫 `build-and-test` 若要驗證 `NFR3.20`／`NFR3.21`，必須有一個能啟動真實 `ollama` 服務的測試環境（現有 `docker-compose.test.yml` 不是），否則該門檻視為結構性不可驗，須回到 `[N1]` 重新裁決（例如改回選項 A，把向量產生時間切出去，只在 `U6` 自己的驗證裡量 Ollama 延遲）。 | New |
| R-02 | Major | `performance-requirements.md` §三之三 `NFR3.22` | `NFR3.22` 以「`EXPLAIN` 計畫出現 HNSW 掃描節點，出現 `Seq Scan` 即不通過」作為二元判準，理由是「opclass 不符時索引被靜默忽略」。但本站漏了同一類問題的另一個來源：PostgreSQL 的 cost-based planner 在候選列數很小時（本站自己證實 `memory_records` **目前是空表**，且任何單元測試／CI fixture 通常只塞入個位數到幾十列）幾乎必定選擇 Seq Scan，**即使索引建得完全正確**——這與延遲數字「在小資料量下看起來一樣好」是同一個現象的另一面，而本站只把這個現象用在警告「不能只看延遲數字」，沒有意識到它同樣會讓 `NFR3.22` 自己選用的 `EXPLAIN` 判準在測試資料量下產生假性失敗。這會讓 `NFR3.22` 在 `code-generation` 落地時難以通過（除非特別灌入數百至數千筆測試資料讓 planner 改變選擇），而七份產出沒有一處承認或處理這個落差。 | 在 `NFR3.22` 旁補一句判準前提：斷言前必須先把候選集合灌到足以讓 planner 傾向使用索引的規模（或在測試中以 `SET enable_seqscan = off` 等方式隔離 opclass 正確性這一個變數），否則判準在空表／小表環境下不可靜態視為可執行；並記為交接事項指向 `code-generation`。 | New |
| R-03 | Minor | `nfr-requirements-questions.md` §〇之一（`N8-1`） | `NFR10` 的落點歧義已如實記載並指名 `U11 intent-router` 的 `nfr-requirements` 為真正落點，但本站僅轉述上游「若該站被 skip，沒有自然承接站」的警告，未依 `project.md`（learned 2026-09-23）的要求自行給出一個具名的轉移目標（例如「屆時由判定 skip 的 conductor 重新提交給使用者」這句本是上游原文，本站沒有以自己的名義再確認一次這條路徑在 `U11` 被 skip 時仍然有效）。風險較低，因為 `U11` 是 `service` kind、幾乎必定不會被 skip，但處置上仍只是轉述而非獨立覆核。 | 在 `N8-1` 補一句本站自己的覆核結論：若 `U11` 的 `nfr-requirements` 因故被判 skip，由誰（哪個 conductor／哪個 gate）負責把 `NFR10` 重新提交使用者裁決。 | New |

### 摘要
- `new-design-problem`: 2（R-01、R-02 ——皆為本站新引入的驗證計畫本身的缺陷，不是上游遺留）
- `pre-existing-unreviewed`: 0
- `propagated-from-upstream`: 0（R-03 嚴格說是上游缺口的轉述方式不夠完整，介於兩者之間，計入 pre-existing 亦可；本站判為本站處置方式的 Minor 缺口）

### 覆蓋範圍
**已查證**：
- `[N1]`／`[N2]` 兩題的查證事實逐一開檔核對（`schema_rbac.sql` 的三個既有索引、`ivfflat`／`hnsw` 命中數為 0、`run_meta_schema_migration.py` 的 `EXPECTED_INDEXES` 確實不含向量索引、`I)` 區塊確實被該腳本解析執行）。
- ID 編號從 `.20` 起算的宣稱：以 `grep` 對整個 `construction/` 樹實算 `NFR3`／`NFR4`／`NFR6`／`NFR7`／`NFR8`／`NFR9` 各父項在其他單元（含 `U5 memory-data`、`U9 memory-purge`、`membership-service` 的 `NFR12` 家族）已佔用的子號，確認本單元 `.20`–`.34` 範圍**無實際碰撞**（`membership-service` 用的是完全不同的父項 `NFR12`）。
- `traceability.json` 的七個 `N/A` 判定逐一回查 `requirements.md` 原文（`NFR1`／`NFR2`／`NFR5`／`NFR9`／`NFR10`／`NFR11`），判定理由與上游文字一致，未發現誤判。
- `functional-spec.md §1.4`（刪除）／§1.5（放寬可見範圍）的步驟順序逐行核對，確認 `NFR7.22`／`NFR7.24` 對「存在性 oracle」已知不一致的處理方式誠實（兩條判準刻意不同形，且已掛 `N8-6` 交 `code-generation`，未試圖掩蓋）。
- `NFR7.28`（列出路徑缺分頁）對照 `contract-summary.md` 的 K-08 OpenAPI 區塊，確認 `GET /api/memory/records` 契約裡確實沒有任何分頁宣告——這項查證是真的。
- `backend/cost/estimate_readers.py:247-251` 的次級排序鍵前例引用逐字核對無誤。
- `pgvector/pgvector:pg18` 的技術選擇宣稱對照 `deploy/docker-compose.test.yml`／`deploy.yml` 確認屬實。
- `[N2]`=B 的四項 blocking 連帶義務（`schema_rbac.sql`／`DEPLOY.md`／`EXPECTED_INDEXES`／`verify_memory_schema.sql`）逐一核對現況，確認四者目前均未落地（本站正確地把它們列為交接而非自行執行）。

**未深入查證**：
- 未實地驗證 `NFR6.21`（日誌不得含記憶內容）在既有 logging 呼叫慣例下是否有具體的字串比對測試落點存在；僅核對了判準本身的可執行性，未查 `code-generation` 階段是否已有雷同的日誌測試樣板可抄。
- 未查核 `observability-requirements.md` `NFR7.34`（候選集合過濾後筆數記錄）在 `U6 EmbeddingPort` 契約（`K-06`）或 `memory_service.py` 的既有/計畫實作介面上是否有自然的掛點（本站只檢查了判準描述的邏輯自洽，未驗證對應的程式介面是否已能取得「過濾後筆數」這個中間值）。
- `N8-9`（90 天個人對話歷程缺備份策略記載）本身是否真的在 repo 全域查無任何 PostgreSQL 備份機制，僅信任本站的查證敘述，未自行重新搜尋 `deploy/`／`DEPLOY.md` 全文確認零命中。
- HNSW 索引建置的實際記憶體成本（`N8-5`）未嘗試估算或查證 staging 主機剩餘 RAM 的具體數字。
- `NFR3.20` 的 500ms 門檻在 `bge-m3`／1024 維、跨容器 HTTP 到 Ollama 之下是否量級合理，僅做了方向性判斷（未經實測、本站亦誠實標註為未經實證），未嘗試用已知的同類基準做更精確的可行性估算。

VERDICT: NOT-READY
