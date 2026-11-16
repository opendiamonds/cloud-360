# 可靠性需求 — `U7 hierarchy-service`

## 一、判定：不適用（無外部依賴邊界，且冪等語意已由契約定案）

**逐項對照 condition 後判為不適用**，理由分兩層，不留空白。

**第一層——無外部依賴邊界**：本單元不呼叫 LLM、不呼叫 webhook、不讀檔、
不連任何外部服務，故**沒有需要重試、降級或熔斷的邊界**。
`construction.md` 的「Always include error handling at integration boundaries」
對本單元的適用面是 DB 操作，而既有慣例已定：DB／驗證錯誤直接 raise，
不以 `try/except` 吞掉（`team.md ## Code Style` 的錯誤處理形狀）。

**第二層——冪等語意已由契約定案，本站不得另開一份**：契約 `K-07` 的
`retry_and_idempotency` 逐字定下三種語意（`create_*` 非冪等、
`resolve_work_target` 唯讀且冪等可安全重試、`record_diagram_change` 非冪等
不得重試），已落為 `rules.md` 的 `BR2.4`。本站若再寫一份可靠性需求，
就是製造第二份真實來源——`team.md` 的「單一真實來源」規則禁止它。

## 一之二、一項可驗證的 NFR

| id | 專精的 intent NFR | 需求 | 二元判準 |
|---|---|---|---|
| **`NFR4.1`** | `NFR4`（狀態外部化與重啟還原） | 本單元**不得持有任何進程內狀態** | 模組層無可變的模組級變數承載請求間資料；三個實體全部經 DB 讀寫。判準為程式審查 ＋ 重啟後行為不變 |

本項對本單元**自動滿足**（三個實體全部持久化於 PostgreSQL），
但仍給 id——因為它是一個**容易在實作時被破壞**的性質：
加一個模組級 dict 當快取就違反它，而那樣做不會有任何錯誤訊息。
驗證落點：本單元的 `code-generation`。

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
