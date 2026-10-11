# 效能需求 — `U7 hierarchy-service`

## 一、判定：不適用（無新增效能需求）

**逐項對照 `nfr-requirements` 的 condition 後判為不適用**，理由如下，不留空白
（依 `project.md` 的 `requirements-analysis:c4`：判定為不適用的項目一律附理由）。

本單元是既有 process 內的同步 CRUD router，**沒有新的延遲預算、沒有新的吞吐目標**。
intent 級的 `NFR3`（首字回應時間）量測的是 WebSocket 串流路徑的首字延遲，
本單元不在該路徑上（落點 `U13 brain-gateway`）。

唯一可量的是列舉端點（`W7`）的查詢成本，而其規模由**單一使用者自有的專案與
系統數**決定——`BR6.1` 的列過濾把範圍限在 `ownerUserId` 等於請求者的列，
量級為個位數，不構成效能需求。

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
