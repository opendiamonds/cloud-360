# 可靠性設計 — `U7 hierarchy-service`

## 一、無待設計的可靠性 pattern，且冪等語意已由契約定案

上游判定本單元**無外部依賴邊界**（不呼叫 LLM／webhook／檔案／外部服務），
故無重試、降級或熔斷可設計。

冪等語意**已由契約 `K-07` 的 `retry_and_idempotency` 定案**並落為 `BR2.4`：
`create_*` 非冪等不得自動重試、`resolve_work_target` 唯讀且冪等可安全重試、
`record_diagram_change` 非冪等不得重試。本站不另開一份。

錯誤處理形狀亦已定：DB／驗證錯誤直接 raise 對應的 facade 層例外
（`HierarchyNotFound`／`HierarchyValidationError`／`HierarchyConflictError`），
由 router 轉譯；不以 `try/except` 吞掉（`team.md ## Code Style` 的既有慣例，
與 `construction.md` 的「Errors must be surfaced」一致）。

## 一之二、上游依據與 `NFR4.1`

本節承接 `reliability-requirements.md`：無外部依賴邊界，且該檔的 `NFR4.1`
要求本單元**不得持有任何進程內狀態**。**三層形狀本身就是這項的設計保證**
——`hierarchy_service` 負責 DB 讀寫、`HierarchyFacade` 只做判定、
`hierarchy_router` 只做轉譯，三者都沒有持有請求間狀態的位置。
它容易被無聲破壞（加一個模組級 dict 當快取即違反，且不會有錯誤訊息），
故列為 `code-generation` 的程式審查項。

契約來源：`contract-summary.md` 的 `K-07` `retry_and_idempotency` 逐字定下三種
冪等語意，已落為 `BR2.4`，本站不另開一份。

## 二、判定的依據與失效條件

本站的每一項判定都綁在上游 `nfr-requirements` 的對應判定上，不是獨立產生的：
該站把本面向判為**不適用且無新增需求**，故本站**沒有待設計的 pattern**。
`nfr-design` 的 condition 逐字為「NFR Requirements was executed and
**NFR patterns need design**」——前半成立（上游已執行，非 skip），後半不成立。

失效條件同上游：把本單元拆成獨立進程、引入任何外部呼叫、
或列舉端點的資料規模由「單一使用者自有的專案數」變成「全體使用者的專案數」。
任一成立時本站須重開。
