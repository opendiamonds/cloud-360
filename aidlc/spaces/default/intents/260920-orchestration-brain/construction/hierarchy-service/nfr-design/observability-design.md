# 可觀測性設計 — `U7 hierarchy-service`

## 一、無待設計的觀測 pattern，但有一項沿用義務

本節承接上游的 `observability-requirements.md`（檔名逐字）：該檔判定本單元
不新增監控目標、告警或健康檢查端點；整體觀測設計屬 `U1 brain-infra` 的
`infrastructure-design`（`monitoring-design.md` 已交付）。

該檔另有一項**本站須設計**的需求：`NFR7.1`——變更紀錄的查詢回應不得被呈現為
完整變更歷史，涵蓋範圍須由 `source` 宣告。它屬**稽核**面而非觀測面，
設計落點見下方「稽核不等於觀測」那一段。

**沿用義務（非新設計）**：logger 命名一律
`logging.getLogger("cloud360.<module>")`。`team.md ## Code Style` 已記載現況為
11 支模組用該形式、**5 支用 `__name__` 屬已知不一致**，並明訂新模組一律用前者。
本單元是新模組，故用 `"cloud360.hierarchy_service"` 等形式。

**稽核不等於觀測，刻意分開**：本單元的稽核面（變更紀錄）屬 ADR-0006 的
audit logging，已於 `functional-spec.md` §七之三 判定並查出三項減損
（級聯刪除、90 天保存期且清除機制不在本 repo、來源欄位只容納一條路徑）。
稽核是對使用者行為的記錄，觀測是對系統健康的量測；本單元有前者、無後者。

## 二、判定的依據與失效條件

本站的每一項判定都綁在上游 `nfr-requirements` 的對應判定上，不是獨立產生的：
該站把本面向判為**不適用且無新增需求**，故本站**沒有待設計的 pattern**。
`nfr-design` 的 condition 逐字為「NFR Requirements was executed and
**NFR patterns need design**」——前半成立（上游已執行，非 skip），後半不成立。

失效條件同上游：把本單元拆成獨立進程、引入任何外部呼叫、
或列舉端點的資料規模由「單一使用者自有的專案數」變成「全體使用者的專案數」。
任一成立時本站須重開。
