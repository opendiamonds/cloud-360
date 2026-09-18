# NFR Requirements — 釐清問題 · U1 `backend-activity-policy`

> Stage: nfr-requirements（Construction 3.2）· Unit: `backend-activity-policy`（kind: service）· Depth: Standard
> **成本揭露**：本題組 3 題。本站有 reviewer（`reviewer_max_iterations: 2`）。
> **CONDITIONAL 判定**：**適用（EXECUTE）**。stage condition 為「有效能需求、安全考量、擴展性顧慮或技術選型需要」—— 本 intent 有 7 條 NFR，其中 NFR-1（效能）與 NFR-3（ADR-0006 四面向，hard constraint）直接落在本單元。

## 已由上游定案、不重問

| 事項 | 來源 |
|---|---|
| 節流門檻：同一帳號 5 分鐘內至多一次寫入 | requirements NFR-1／FR-1.3；門檻值與邊界（含等於）已由 3.1 定死 |
| 失敗處置：先復原再記錄，不影響請求 | `component-methods.md` C-2 的交易契約 |
| 不新增外部依賴 | `decisions.md` AD-5（C-8 為唯一具名例外，屬 U5） |
| 技術堆疊 | `project.md ## Tech Stack` 已定；本單元不引入新技術 |

## Sources（出題前的唯讀查證）

| # | 查證 | 結果 |
|---|---|---|
| S1 | 觀測性依賴 | `backend/requirements.txt` **無** prometheus／opentelemetry／statsd／psutil |
| S2 | 連線池設定 | `database.py:23` 為 `create_engine(DATABASE_URL)`，**未帶任何連線池參數**，採函式庫預設 |
| S3 | 部署資源限制 | `deploy/docker-compose.deploy.yml` **無** replicas／cpus／mem_limit 設定 |
| S4 | 帳號規模 | 啟動流程種入 **11** 個預設帳號；本專案為單一組織的內部工具 |
| S5 | CI 效能測試 | `ci.yml` 四道關卡皆無效能測試步驟 |

---

## Q1. 效能需求的表述方式

A. **以設計推導的上界表述** — **（建議）**
   - 寫「節流規則 ⇒ 每帳號每 5 分鐘至多一次寫入；N 個活躍帳號的寫入上界為 N/5min」，並**明記這是設計上界、非實測值**，以及 repo 無量測機制的事實（S1／S5）。
   - 此上界可由規則直接推得、無需儀表，且節流判定本身可被純函式測試驗證。
   - 代價：不是延遲保證。

B. **訂定具體延遲預算** — 代價：依 S1／S3／S5，**沒有任何機制能驗證它**，是虛假精確。

C. **標為不適用** — 代價：NFR-1 是上游已定案的需求，下游不得擅自推翻。

D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q2. ADR-0006 encryption 面向的判定

A. **不額外保護，但寫明判定理由** — **（建議）**
   - 沿用資料庫現有的傳輸與靜存保護層級，不加欄位級加密。
   - 理由：該欄位與同表已有的帳號、角色、啟用狀態同等敏感度，而後者現在就沒有欄位級加密；單獨加密新欄位不提升實際安全性，卻會讓查詢與排序失效。
   - **判定與理由都寫進 artifact**，不以「已有 ADR-0006」帶過（`project.md ## Mandated` 明文要求）。

B. **視為需保護，規劃欄位級措施** — 代價：repo 無此類先例；加密後逾期判定的比較必須搬到應用層逐列解密，與 U2 的清單端點直接衝突，且遠超本 intent 範圍。

C. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q3. 可靠性：寫入持續失敗時的可偵測性

A. **要求記錯誤級日誌，不要求告警** — **（建議）**
   - 需求：寫入失敗須以**錯誤級**記錄且包含例外型別，使其在日誌中可被搜尋到。
   - **不**要求告警或儀表 —— 那兩項屬 Operation 階段尚未落地的維運學科（`project.md` 已如實記載），在本 intent 強要會夾帶一個完整的觀測性專案。
   - 代價：持續失敗仍需人工看日誌才會發現。

B. **要求告警機制** — 代價：repo 無告警管道與指標收集，與 AD-5 衝突。

C. **不訂可靠性需求** — 代價：C-2 的契約只規定「不影響請求」，沒規定記錄的**級別與內容**；沿用既有補丁的警告單行形狀會讓失敗在日誌裡難以辨識。

D. Not yet defined
X. Other (please specify)

[Answer]: A
