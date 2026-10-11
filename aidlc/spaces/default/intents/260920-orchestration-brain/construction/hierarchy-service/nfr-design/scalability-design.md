# 擴展性設計 — `U7 hierarchy-service`

## 一、無待設計的擴展 pattern

上游判定本單元**不是可獨立擴展的單位**（`embedded` router，
水平擴展對象是承載它的 process，設計屬 `U1 brain-infra`）。
本單元**進程內零狀態**——三個實體全部持久化於 PostgreSQL，
故多副本部署無 session affinity 或狀態同步需求。本站無 pattern 可設計。

## 一之二、上游依據

本節的判定直接承接 `scalability-requirements.md`（本單元非獨立擴展單位、
進程內零狀態）與 `tech-stack-decisions.md`（執行形態為 `embedded`，
`unit-of-work.md:43` 逐字）。`NFR8.1`（不得新增任何部署設定）亦落在此面向：
判準為 `validate_env_contract.py` 綠燈且 diff 不含 `deploy/`、`render-env.sh`、
任一 `.env.example`。

## 二、判定的依據與失效條件

本站的每一項判定都綁在上游 `nfr-requirements` 的對應判定上，不是獨立產生的：
該站把本面向判為**不適用且無新增需求**，故本站**沒有待設計的 pattern**。
`nfr-design` 的 condition 逐字為「NFR Requirements was executed and
**NFR patterns need design**」——前半成立（上游已執行，非 skip），後半不成立。

失效條件同上游：把本單元拆成獨立進程、引入任何外部呼叫、
或列舉端點的資料規模由「單一使用者自有的專案數」變成「全體使用者的專案數」。
任一成立時本站須重開。
