## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

session-store 的 NFR 產出整體自洽，且大致已落地：`noeviction` 已改入 `deploy/docker-compose.deploy.yml:276`，`BRAIN_SESSION_HISTORY_MAX=200` 已寫入 `render-env.sh:139` 與兩份 `.env.example`，Redis 客戶端依賴已列入 `requirements.txt:49`，ADR-0006 四面向逐項有落點。有兩項 Major：一是容量模型與「單則訊息長度無上界」不相容（前次 review-01 R-02 已提，凍結產出中仍未處置，程式碼自己也承認不滿足 NFR4.40）；二是 NFR4 核心不變量「重啟還原」的驗證程序定義與其要證明的持久化層不對位。兩項合計未超過 2 項 Major，故判 READY，請在關卡上由人裁決是否接受。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/session-store/nfr-requirements/scalability-requirements.md 容量算式與 NFR4.40／NFR4.41；對照 backend/services/session_store.py:113 `DEFAULT_MESSAGE_MAX_CHARS = 4000` 及其上方註解 | 前次 review-01 R-02 已提。NFR4.41 宣稱「每個 session 有可計算的硬上界」，但算式只以「每則 500 B 的假設平均」計算，全文（nfr-requirements 五份）沒有任何單則訊息長度上限。已落地的程式碼自行加了 4000 字元上限，其註解逐字承認「最壞情況 3 段 × 200 則 × 4000 字元遠大於 300 KB／session，故 NFR4.40 的 300 個同時存活只在平均假設下成立」。以 4000 個中文字元約 12 KB（UTF-8 三位元組）估，單 session 最壞約 7 MB，256 MB 之下最壞僅約 35 個 session，與承諾的 300 差一個數量級；而 noeviction 下超額的結果是寫入失敗。就是說設計的硬上界主張為假，正確的一邊是程式碼的註解，且該 4000 的上限在任何 NFR 檔內都沒有對應條文（也未列入 FR/AC）。 | 在 NFR 檔新增「單則訊息長度上限」需求（值 4000 字元，並註明以 UTF-8 位元組計的最壞值），以最壞值重算 NFR4.40，或明示將 NFR4.40 降級為「平均假設下的目標」並把最壞情況寫成已接受風險；NFR4.41 的判定方式須改為逐欄含字串長度。 | New |
| R-02 | Major | construction/session-store/nfr-requirements/reliability-requirements.md NFR4.52–NFR4.57 與 observability-requirements.md NFR4.64；對照 code-generation/unit-test-instructions.md「AOF 與重啟還原」段 | NFR4.64 要求「重啟還原」須是可重複執行的腳本或測試，並逐字寫成「重啟 backend 容器、逐項讀回」。但 session 狀態存在 Redis，重啟 backend 容器完全不經過持久化層；真正能讓 NFR4.52（appendonly 維持 yes）與 NFR4.57（剩餘 TTL 不重設）成立或不成立的是重啟 Redis 容器（AOF 重播）。產出把兩種重啟混為一談，使該測試即使通過也證明不了 AOF 設定有效。下游的 unit-test-instructions 也明寫替身不支援 AOF，並把驗證點推給「部署後步驟」，即 NFR4.64 要求的「可重跑腳本」沒有被任何 NFR 條文落成可執行的形狀（誰跑、在哪跑、是否在 CI）。 | NFR4.64 須明確拆成兩個重啟情境：backend 重啟（證明無行程內狀態，BR1.2）與 Redis 重啟（證明 AOF 與 TTL 還原，NFR4.52／NFR4.57），並指名承載機制（腳本路徑或部署後步驟的編號）與誰負責執行。 | New |
| R-03 | Minor | construction/session-store/nfr-requirements/reliability-requirements.md NFR4.51；對照 backend/services/session_store.py:199-222（load 先 hgetall 再 expire） | NFR4.51 斷言 OOM 時「讀取（load）須仍然可用」，但同檔與 BR1.3 都說每個方法含 load 都發 EXPIRE，performance-requirements.md 更寫「每一次呼叫都是一次寫入」。EXPIRE 在 Redis 是否會被 noeviction 拒絕、Lua 腳本（append_message.lua 等）在 OOM 下的行為，產出都未查證；測試替身亦明寫不支援 OOM 真實行為。降級形狀「既有 session 仍讀得到」因此是未驗證主張。 | 在 NFR4.51 補註「load 內的 EXPIRE 在 OOM 下的行為待部署後驗證」，或要求 load 在 EXPIRE 失敗時仍回傳已讀到的資料（並分類為 redis_oom 記錄）。 | New |
| R-04 | Minor | construction/session-store/nfr-requirements/scalability-requirements.md NFR4.40「2.8 倍餘裕給 AOF 緩衝與 Redis 自身開銷」 | 前次 review-01 R-03 已提：2.8 倍是 850÷300 的算術結果，不是 AOF 重寫（BGREWRITEAOF 的 fork 與寫入緩衝）或 Redis 每 key 開銷的推導或實測；產出自己對 500 B 有標明「假設」，對此處卻沒有。容器上限 768m（docker-compose.deploy.yml:310）高於 U1 規則 maxmemory×1.5+256MB=640MB，實際有餘，故風險低。 | 將該句改為「假設足夠、未實測」，或引用 U1 的容器上限規則作為依據。 | New |
| R-05 | Minor | construction/session-store/nfr-requirements/security-requirements.md OPEN-N10-1／OPEN-N10-2；observability-requirements.md OPEN-N10-4 | 三項缺口均如實標為「無自然承接站」（承接站皆已在游標之前），符合 project.md 規則，但它們的後果是真實的：已核可線框的「7 天內／30 天內」分組在 24 小時 TTL 下永不可達，且 RecentConversations 無任何單元、FR、AC 擁有。我未開啟 sibling 單元驗證 U14 交付清單，僅依產出自述。 | 在關卡上明確請人裁決這三項（接受為已知缺口，或回跳上游修訂），不要讓其隨 READY 被默認吸收。 | New |
| R-06 | Minor | construction/session-store/nfr-requirements/ 編號空缺（NFR4.49、NFR4.58、NFR4.59） | 產出編號使用 NFR4.40–.48、.50–.57、.60–.64；grep 僅見上述編號有定義，.49／.58／.59 沒有條文也沒有「保留」說明。若是刻意保留，應註明；若是刪除遺留，下游追溯可能指向不存在的 ID。 | 補註保留原因，或確認 traceability.json 沒有引用這三個編號。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 人工比對 deploy/docker-compose.deploy.yml:255-276 | PASS | `appendonly yes` 與 `maxmemory-policy noeviction` 已落地，與 NFR4.50／NFR4.52 一致 |
| 人工比對 render-env.sh:139、deploy/.env.example:147、backend/.env.example:153 | PASS | NFR8.40 的環境變數三處同步，值為 200 |
| 人工比對 backend/requirements.txt:49 | PASS | NFR8.41 的 Redis 客戶端依賴已加入 |
| 人工比對 session_store.py 與 NFR4.40／4.41 | FAIL | 單則長度上限 4000 在 NFR 無條文，且使容量承諾在最壞情況下不成立（R-01） |
| 未執行測試或建置 | N/A | 依 brief 禁止產生快取或寫檔，故僅做靜態閱讀 |
