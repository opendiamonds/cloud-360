## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U8 memory-service 的 nfr-requirements 七份產出自洽度高，也如實承接了舊審查：舊 R-01（向量產生含進延遲門檻的橡皮章）已由 `[N1]` 改回 A 處置，舊 R-02（`EXPLAIN` 在小表上假性失敗）已由 §3.4 與 `N8-12` 處置，HNSW 索引的四項連帶義務也已在 `schema_rbac.sql:503`、`run_meta_schema_migration.py:168`、`verify_memory_schema.sql` S14 落地。引用抽查全部屬實：`estimate_readers.py:247-251`、`docker-compose.test.yml:18,102`、`.env.example:120`。仍有兩項 Major：一是 `NFR3.20`／`NFR3.21` 沒有指定量測場地，單元測試走 SQLite 時向量查詢根本不會執行，與舊 R-01 是同一類橡皮章；二是 `NFR7.24` 第 2 個案例與 `N8-6` 的建議修法，和已落地且更正確的 `[D1]`=A（非擁有者回 404）互相矛盾。Critical 為 0、Major 為 2，故判 READY，但 R-01 與 R-02 應在關卡上由人裁決是否補一份 corrections。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/memory-service/nfr-requirements/performance-requirements.md > 一、NFR3.20／NFR3.21 | 兩條只要求「記錄列數」與「P95 數值」，沒有指定量測場地。已落地的 `memory_service.py:36,326` 逐字說明向量查詢「在 SQLite 上編不出來」，`_supports_vector` 只在 dialect 為 postgresql 時才走向量路徑（`memory_service.py:254-262`）。`team.md` 記載 backend 單元測試預設是 in-memory SQLite，所以若 `build-and-test` 用既有單元測試基礎設施計時，量到的只是不含相似度查詢的路徑，P95 近乎 0，`NFR3.20` 穩定通過，`NFR3.21` 的兩個欄位也都填得出來。這與舊 review 的 R-01（量測場地不含真實提供者）是同一類結構性橡皮章，只是換了一個維度，本站只修了提供者那一維。另外 `NFR3.21` 只要求「記錄」列數、沒有要求最低規模，在近乎空表上量到的 150ms 對 `memory_records` 成長到 90 天累積量時沒有任何預測力。 | 在 `NFR3.20`／`NFR3.21` 的判準補上量測場地條件：必須在真實 PostgreSQL 加 pgvector 且 HNSW 索引已建立的環境（例如既有 `memory-schema` job 的 service container）量測，SQLite 上的計時不得作為驗證證據。並訂出最低列數門檻或要求量測至少兩個規模點，否則該門檻視為未驗證。 | New |
| R-02 | Major | construction/memory-service/nfr-requirements/security-requirements.md > 二、NFR7.24；六、N8-6；2.1 末段 | 設計與已落地程式矛盾。`NFR7.24` 判準第 2 項寫「他人（含 Platform_Admin）→ 403」，`N8-6` 又建議「實作時可就地把擁有者判定提到記憶取得之前」。已落地的 `memory_facade.py:364-409`（`[D1]`=A）則是非擁有者與不存在皆拋 `MemoryNotFound`、對外同為 404，只在日誌用 `reason="owner"` 區分，理由是 `id SERIAL PRIMARY KEY` 為連續整數，403／404 差異會讓任何已認證使用者枚舉整張表的存在性。程式這一邊是對的。反過來，`N8-6` 的建議修法本身不可實作：擁有者是記憶列的屬性，不先取列就無從判定，「提到取得之前」會變成永遠放行或永遠拒絕。凍結的 `NFR7.24` 若被當驗收判準，已交付程式會被判不通過；`NFR7.22` 的「角色先於存在性」仍成立，因為角色判定不需要取列。 | 以 corrections 追認：`NFR7.24` 第 2 項改為「非擁有者與不存在回相同的 404，且日誌可區分」，並把「帳號未核准」另列為 403 案例；`N8-6` 標為已由 `[D1]`=A 取代，刪除「提到取得之前」的建議。 | New |
| R-03 | Minor | construction/memory-service/nfr-requirements/reliability-requirements.md > 一、NFR4.21；〇、上游依據 | `NFR4.21` 寫「`write` 與 `delete`／`widen_scope` 的稽核寫入必須與資料變更同交易」，但 `NFR7.26` 與 `BR7.4` 明定建立不產生稽核事件，`ck_memory_audit_events_action` 也沒有任何可用於建立的值。同一單元的兩條判準對 `write` 的稽核說法相反；照 `NFR4.21` 字面實作會觸發 CHECK 違反。程式（`functional-spec.md` 第 11 行 `BR7.4` 無稽核）與 `NFR7.26` 一致，`NFR4.21` 的措辭是錯的一方。 | `NFR4.21` 移除 `write`，只保留 `delete`／`widen_scope`。 | New |
| R-04 | Minor | construction/memory-service/nfr-requirements/security-requirements.md > 前言「四條 HTTP 端點」與 五、Network exposure「第四條對外端點」；observability-requirements.md > NFR7.30 | 端點數不一致。`functional-spec.md` 第 11、13-16 行與 `memory_router.py` 的五個 `@router` 裝飾器（create、list、delete、put scope、audit-events）都是五條 HTTP 端點。`NFR7.30` 判準「以無權身分呼叫四條端點各一次 → 四筆日誌」不可執行：create 與 list 沒有授權拒絕路徑（擁有者由身分決定，`BR1.1`），真正會產生 `reason` 為 `owner` 或 `scope` 拒絕的只有 delete、widen、audit 三條。 | 把端點數更正為五，並在 `NFR7.30` 明列會產生拒絕日誌的端點與各自的 `reason`。 | New |
| R-05 | Minor | construction/memory-service/nfr-requirements/performance-requirements.md > NFR3.23 | 列出路徑 P95 ≤ 300ms 沒有像 `NFR3.20` 那樣標註「工程判斷而非實測」，也沒有套用 `NFR3.21` 的實測與列數記錄要求，驗證責任懸空。 | 標註其為未經實測的工程判斷，並納入 `NFR3.21` 的實測要求，或明寫無驗證要求的理由。 | New |
| R-06 | Minor | construction/memory-service/nfr-requirements/ 全部產出（`N8-` 編號） | 交接編號 `N8-1` 之後直接跳到 `N8-3`，全部產出中 `N8-2` 零命中，下游無法判斷是刪除、遺漏還是保留號。`N8-1` 也只轉述上游「無自然承接站」警告，未補上本站自己的覆核結論（前次 review-01 已提 R-03，凍結產出中仍留著）。 | 說明 `N8-2` 的去向；在 `N8-1` 補一句：若 `U11` 的 `nfr-requirements` 被判 skip，由哪個 conductor 或 gate 重新提交使用者裁決。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 引用逐字核對（`estimate_readers.py:247-251`、`docker-compose.test.yml:18,102`、`.env.example:120`、`schema_rbac.sql:503-504`） | 全部屬實；`best_clouds` 的 `key` 在第 250 行，落在引用範圍內 | 舊 review 與本檔引用定位正確 |
| HNSW 連帶義務四項落地檢查（`schema_rbac.sql`、`EXPECTED_INDEXES`、`verify_memory_schema.sql` S14／S14b） | 已落地，opclass 為 `vector_cosine_ops`，查詢運算子為 `<=>`（`memory_service.py:96`） | `NFR3.22` 的 opclass 與運算子一致性前提成立；`DEPLOY.md` 未命中 `hnsw`，未列為發現，因為全樹小寫搜尋可能漏，建議 code-generation 關卡複驗 |
| ID 唯一性與孤兒檢查（`N8-` 編號） | `N8-2` 零命中，`N8-11`、`N8-12` 各僅一處定義 | 對應 R-06 |
| 未執行測試或建置 | 依 brief 禁止產生快取與寫檔 | 設計對程式的比對僅靠讀碼，未實測 |
