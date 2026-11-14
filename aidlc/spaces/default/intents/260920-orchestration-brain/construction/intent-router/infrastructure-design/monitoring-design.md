# Monitoring Design — `U11 intent-router`

> 把 `nfr-design/observability-design.md` 的**策略**落成**平台上的具體位置**。
> 該檔已確立最重要的指標是**反問率**，且本 intent **沒有任何告警通道**
> （`U10` 的 `OPEN-N10-4`）。本檔不假裝有。

## 一、Metrics & KPIs

全部來自單一結構化事件 `RoutingObservation`（欄位集合即日誌白名單，`SEC-3`／`SEC-5`）。

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| **反問率** | `can_single_out == False` ÷ 總輪次 | **無固定門檻**；與 `NFR1` 準確率**同圖呈現** | `NFR1` 逐字：調高門檻會讓系統多反問、少交辦，準確率的帳面數字因此上升，**但那不是識別變準了**。單看任一個都會被另一個騙 |
| `classify` 耗時 P50 | `elapsed_ms` 分位數 | **P50 ≤ 800 ms**（`NFR3.60`） | `NFR3` 的 2 秒端到端預算中，路由層佔 800 ms |
| `classify` 耗時 P95 | 同上 | 無門檻，觀測用 | 區分「普遍慢」與「長尾慢」；長尾由 5 秒硬逾時截斷 |
| **槽位數分佈** | `slot_count` 直方圖 | **線上長期恆為 1 即為異常訊號** | `BR4.1`／`BR4.4`／`BR4.5`（多意圖整組）**在線上永遠是 1 個槽位時就是死碼**，而沒有這個分佈沒有人會發現。另：它的**尾端**是 `D-7`（上界 4）的覆核依據 |
| **分類失敗率（按型別）** | `error_kind` 分組 | `MalformedRouting` **任何一次**即值得看 | 四型別（`LlmUnavailable`／`LlmBudgetExceeded`／`EmptyCandidates`／`MalformedRouting`）混計會讓「供應商掛了」與「我們的 prompt／schema 壞了」看起來一樣 |
| **記憶降級率** | `memory_degraded` ÷ 總輪次；另記**連續降級次數** | 連續降級即為異常 | **這是 `D-1`（記憶降級而非失敗）唯一的保險**。沒有它，「記憶永遠取不到」是無聲的——`N8N_USER` 那類失敗的形狀 |
| `prompt_guard` 命中數 | `error_kind == "prompt_guard_hit"` | 單一 principal 短時間多次即值得看 | 安全事件的量；**紀錄不得含觸發輸入**（`SEC-4`） |

## 二、Alerts

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| 路由層供應商不可用 | `LlmUnavailable` 率 5 分鐘內 > 5% | P2（ticket） | **無通道** |
| schema／prompt 壞了 | `MalformedRouting` 任何一次 | P2 | **無通道** |
| 反問率異常 | 偏離基準 ±50% 持續 15 分鐘 | P3（dashboard） | **無通道** |
| 記憶持續降級 | `memory_degraded` 連續 N 輪 | P3 | **無通道** |
| `prompt_guard` 命中突增 | 單一 principal 短時間多次 | P2 | **無通道** |

**`Routes to` 欄全部是「無通道」，而這是如實記載不是待辦清單的佔位。**
本 repo 無 Prometheus、無 CloudWatch、無任何告警管道（`U10` 的 `OPEN-N10-4`
已查證並登記）。本站**不自行發明一個**——那會是憑推論加的基礎設施，而
`project.md` 記過憑推論加拓樸的失誤形狀。

**在 `OPEN-N10-4` 關閉之前，這五條的實際消費方式是人工查詢結構化日誌。**
**不把「有指標」寫成「有監控」。**

## 三、SLIs / SLOs

| SLI | SLO target | Measurement window |
|---|---|---|
| 意圖識別準確率 | **≥ 80%**（`NFR1`，**無實證基礎的初版值**，依校正程序裁決） | ≥50 筆人工標註集，**離線**，每次模型或 prompt 變更後重跑 |
| 路由層首段延遲 | **P50 ≤ 800 ms**（`NFR3.60`） | 線上滾動；`build-and-test` 的基準量測為離線 |
| 分類成功率（非失敗） | **無 SLO**，只觀測 | 本單元的失敗多為供應商側，設一個我們控制不了的 SLO 沒有意義 |

**三列裡有兩列是「無實證基礎」或「無 SLO」，這是刻意的。** `NFR1` 的校正程序
（`requirements.md:400-428`）逐字涵蓋四個無實證基礎的數值，並規定**首次實測
未達標時不得自動改寫門檻**，由決策者在 `build-and-test` 的核可關卡三選一。
本站不預先宣告一個看起來專業的 SLO 數字去取代那個程序。

## 四、Logs & Tracing

| 面向 | 設計 |
|---|---|
| **聚合** | 既有的容器 stdout → Docker log driver。**零新增**（無 ELK、無 Loki） |
| **格式** | 單一結構化事件 `RoutingObservation`，欄位白名單即型別（`SEC-3`） |
| **禁止欄位** | `text`、`label`、**`referent`**、記憶內容、prompt 全文、模型原始回應 |
| **Tracing** | **不引入任何套件**。`turn_id`（來自 `K-02`，`U2` 已定）貫穿 `U13` → `U11` → `U12` → 能力 agent，而**該鏈四跳全部同進程**（審查已複驗：C1 經 `ThreadPoolExecutor` 跑在同一個 backend 行程）。分散式 tracing 要解的是跨網路多服務的問題，本鏈不是 |
| **Tracing 的重審觸發** | 鏈路若變成跨進程（例如 `TS-3c` 提到的 `OQ-N1` 回覆單元獨立部署），此判斷要重做 |
| **保留** | 沿用既有容器 log 保留策略，**本站不另訂**——訂一個沒有機制執行的保留期是宣告而非控制 |

### `referent` 在禁止清單裡的理由（容易被漏，故重述）

它**看起來像識別碼**，實際上是解析使用者句子得到的系統名或圖名——那是使用者的
內容。`capability` 可以記（封閉列舉），`referent` 不行。
**本 repo 為 public、Actions log 公開可讀。**

## 五、Dashboards

**本站不產出 dashboard 規格。** 理由與 §二 相同：沒有 dashboard 平台可以掛
（無 Grafana、無 CloudWatch）。七個指標（§一）的定義已足以在平台到位時直接建，
而**先畫一份沒有地方可放的 dashboard 規格，是把「有設計」誤當成「有監控」**。

**承接**：`observability-setup`（4.x）——與 `OPEN-N10-4` 同一站。
