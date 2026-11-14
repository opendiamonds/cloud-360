# 擴展性需求 — `U7 hierarchy-service`

## 一、判定：不適用（無新增擴展單位）

**逐項對照 condition 後判為不適用**，理由如下，不留空白。

本單元**不是一個可獨立擴展的單位**：它是既有 FastAPI process 內的 router，
水平擴展的對象是承載它的那個 process，而該 process 的擴展設計屬
`U1 brain-infra`（其 `infrastructure-design` 已交付，含 compose 與監控）。

本單元不新增任何有狀態元件：三個實體全部持久化於 PostgreSQL
（DDL 屬已交付的 `U4 hierarchy-data`），**進程內零狀態**，故多副本部署時
無 session affinity 或狀態同步需求。

## 二、為什麼本單元沒有這一類需求

本單元的形態決定了這一點，不是省略：`unit-of-work.md:43` 逐字把它列為
**`embedded`（同一 FastAPI process 的新 router）**——不新增進程、不新增監聽埠、
不新增部署單位、不呼叫任何外部服務（無 LLM、無 webhook、無檔案 I/O）。
`functional-spec.md` §七之三 的 Network exposure 列逐字「不新增任何對外進程邊界、
不新增任何監聽埠」，而 `unit-of-work.md:249` 逐字把 `U13 brain-gateway` 的新
WebSocket 稱為「本 intent **唯一**新增的對外網路面」。

## 三、若日後本判定失效的觸發條件

本判定綁在「embedded 且無外部依賴」這個前提上。下列任一成立時須重開本站：
把本單元拆成獨立進程、引入任何外部呼叫（計價、LLM、webhook）、
或列舉端點的資料規模由「使用者自有的專案數」變成「全體使用者的專案數」
（後者會讓 `BR6.1` 的列過濾從常數成本變成需要索引設計的成本）。
