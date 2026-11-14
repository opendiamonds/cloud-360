# 效能設計 — `U7 hierarchy-service`

## 一、無待設計的效能 pattern

上游 `nfr-requirements` 的 `performance-requirements.md` 判定本單元**無新增效能
需求**（既有 process 內的同步 CRUD router，無新延遲預算、無新吞吐目標；
`NFR3` 的首字延遲屬 `U13 brain-gateway` 的串流路徑）。故本站無 pattern 可設計。

**唯一與效能相關的結構決定已在 `functional-design` 做完**，且它是授權決定而非
效能決定：`BR6.1` 把列舉範圍限在 `ownerUserId` 等於請求者的列，
使查詢量級為個位數。本站不另設快取、不另設分頁、不另設索引設計
——後兩者若日後需要，索引屬 `U4`（DDL 擁有者）、分頁屬契約變更。

## 二、判定的依據與失效條件

本站的每一項判定都綁在上游 `nfr-requirements` 的對應判定上，不是獨立產生的：
該站把本面向判為**不適用且無新增需求**，故本站**沒有待設計的 pattern**。
`nfr-design` 的 condition 逐字為「NFR Requirements was executed and
**NFR patterns need design**」——前半成立（上游已執行，非 skip），後半不成立。

失效條件同上游：把本單元拆成獨立進程、引入任何外部呼叫、
或列舉端點的資料規模由「單一使用者自有的專案數」變成「全體使用者的專案數」。
任一成立時本站須重開。
