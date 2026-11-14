# Scalability Design — `U10 session-store`

> 設計階段產出。數字一律附算式與輸入出處；假設逐條標明。

## 本檔的上游

| 上游 | 它給了什麼 |
|---|---|
| `scalability-requirements.md` | `NFR4.40`（≥300 session）、`NFR4.41`（硬上界）、`NFR2.41`／`NFR2.42`（連線數不影響狀態、扇出線性） |
| `performance-requirements.md` | `NFR3.40`–`NFR3.43` 的延遲預算與連線池算式的輸入 |
| `reliability-requirements.md` | `NFR4.50` 的 `noeviction`——它決定「撞上上限時先壞什麼」 |
| `security-requirements.md` | DoS 面的兩道防線；`OPEN-N10-6` 的長度上限缺口 |
| `observability-requirements.md` | `NFR4.60` 的 `MEMORY STATS` 訊號——它是本檔門檻的唯一觀測面 |
| `tech-stack-decisions.md` | `NFR8.40` 的上限參數以環境變數承載 |
| `functional-spec.md` | `EC4` 的段數上界 3；`W3`／`W4` 的段建立時機 |
| `contract-summary.md`（`K-09`／`K-11`） | 工作項集合共用同一個 key |

## 擴展形狀：本單元**沒有**水平擴展問題，只有容量問題

`x-concurrent-connections` 逐字「伺服器**不以連線為狀態單位**，狀態一律在 Redis
的該 key 之下」。這句話的後果是：**backend 可以有 N 個 worker，本單元不需要任何
協調**——它是無狀態的（`architecture-guide.md` 的 Stateless services 形狀）。

所以本單元的擴展討論只剩**一個**自由度：Redis 的 256 MB 能裝多少 session。

## `[D1]`=A 的 Hash 結構對容量的影響（與單一 blob 的差別）

| 面向 | Hash（本案） | 單一 blob |
|---|---|---|
| 每個 session 的總量 | 相同（都是三段訊息的總和） | 相同 |
| **單次寫入的傳輸量** | 只有該段 | 整個 session |
| **Redis 的記憶體開銷** | Hash 有每欄位的額外開銷（小型 Hash 會被 ziplist 編碼，欄位變大後轉為 hashtable） | 單一字串，開銷最小 |
| 並發寫入 | 不同段零衝突 | 需要樂觀鎖或會掉訊息 |

**第三列是 Hash 的代價**，而本檔如實標它為**未量測**：Redis 的 `hash-max-listpack-entries`
預設 128、`hash-max-listpack-value` 預設 64 bytes；本案的 Hash 約 7 個欄位但**每個
欄位的值遠大於 64 bytes**，故它會以 hashtable 編碼，每欄位有指標與 dictEntry 開銷。
相對於欄位值本身（數十 KB）這個開銷可忽略，但**這是推理不是量測**——
`scalability-requirements.md` 的 300 KB／session 上界未含它。

## 容量門檻與「先壞什麼」

| 使用率 | 狀態 | 先發生什麼 |
|---|---|---|
| < 35%（90 MB，約 300 個滿載 session） | `NFR4.40` 的承諾區 | 正常 |
| 35%–100% | 餘裕區 | 正常，但 `NFR4.60` 的 `MEMORY STATS` 訊號應已上升 |
| 觸及 256 MB | **寫入失敗、讀取正常**（`NFR4.51`） | `append_message`／`set_*`／`touch` 全部回 `SessionBackendUnavailable`；`load` 仍然服務 |

**「先壞什麼」在 `[N3]`=A 之後是確定的，而在它之前是隨機的**：`allkeys-lru` 下
先壞的是「最久沒被碰的那個使用者的整個 session」，而那個人**不會收到任何錯誤**。
`noeviction` 下先壞的是「當下正在寫入的那個人的這一次寫入」，而他**會收到錯誤**。
這是本單元最重要的一次擴展性取捨，寫在這裡而不只在 reliability 檔，因為它
決定的是容量上限的**語意**。

## 成長維度（三個，其中兩個是封閉的）

| 維度 | 是否封閉 | 封閉者 |
|---|---|---|
| 每個 session 的段數 | **封閉，上界 3** | `EC4` 的封閉集合——段識別就是頁面名，使用者無法製造第四段 |
| 每段的訊息筆數 | **封閉，上界 200** | `BR3.4` ＋ `NFR8.40` 的環境變數（無預設值） |
| **每則訊息的長度** | **未封閉** | **沒有任何一層限制它**——見 `security-design.md` 的 `OPEN-N10-6` |
| 同時存活的 session 數 | 未封閉（＝使用者數 × 活躍比例） | 唯一真正的自由度；由 `maxmemory` 封頂 |

**第三列使第二列的封閉性失效**：200 則的上限只封住筆數，不封住位元組。
`NFR4.41` 宣稱「每個 session 的記憶體佔用須有可計算的硬上界」——**在
`OPEN-N10-6` 關閉之前，那個宣稱不成立**。本檔如實記載，不掩蓋。

## 擴展手段的評估（附否決理由）

| 手段 | 判定 |
|---|---|
| 提高 `maxmemory` | **可行且是第一順位**，但 `U1` 的註解逐字定下 `container memory limit >= maxmemory × 1.5 + 256MB`，故須連容器上限一起改。另注意同一台主機上還有 `ollama`（`codekb/chiton/technology-stack.md:167` 的六個服務之一），它是記憶體大戶 |
| Redis Cluster／分片 | **否決**。`ADR-0007` 的部署目標是單一自有主機，production 不在範圍；分片會引入 `ADR-005` 單一 key 語意之外的複雜度，而目前連 256 MB 的 35% 都用不到 |
| 副本（read replica） | **否決**。本單元的讀寫比不高（每輪互動 1 讀 2 寫量級），且 `reliability-requirements.md` 已明寫接受單點 |
| 把歷程移出 Redis | **已於 `[N1]` 否決**（維持 24 小時、不另建持久層） |
| 縮小 200 的上限 | **保留為旋鈕**。`NFR8.40` 已讓它成為環境變數，故容量吃緊時這是**不需改程式**的第一道調節手段 |
