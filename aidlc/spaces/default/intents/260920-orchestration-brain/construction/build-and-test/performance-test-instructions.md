# 效能測試說明（build-and-test）

- 撰寫時間（`date -u`）：`2026-11-14T02:19:24Z`
- 測試策略為 **Standard**，stage 檔只在 Comprehensive 下要求本檔；本站仍依 brief 產出，因為本 intent 的 `nfr-requirements` 有**數值型延遲目標**，而它們在本站的判定全部是 `Unverified`——這件事必須有一份檔把「為什麼量不到、要怎麼量」寫清楚，而不是在矩陣裡只留一個結論。

## 現況：本 repo 沒有延遲量測機制

- 無負載工具（無 k6／Locust／JMeter 設定）、無 APM、無 metrics 匯出端點、無 dashboard 平台（`project.md` 的 `infrastructure-design` 學習：「repo 沒有可掛的監控平台時，不要產出 dashboard 規格」）。
- 本站**未執行任何負載或計時量測**；矩陣中所有延遲目標因此為 `Unverified`，計畫中也**沒有** `performance-validation` 之類可承接的後續 stage。
- 已在設計階段改以**可二元判定的代理指標**取代延遲數字者（例如 `requirement-field-service` 的 NFR20.1／20.2／20.4 查詢次數、`work-orchestrator` NFR12.3 的輪詢次數上界），本站已由後端全套實跑判為 `Met`。

## 本 intent 的數值延遲目標（全部 Unverified）

| Target ID | 目標 | 量測點 | 相關但不量時間的測試 |
|---|---|---|---|
| `requirements:NFR3` | 首字回應 **P50 ≤ 2 秒**（伺服器端：送出 → WS 收到第一個內容 token） | 閘道 | — |
| `brain-gateway:NFR13.1` | (a) 分類前段 P50 ≤ 400 ms；(b) 分類後到第一則內容 P50 ≤ 300 ms | 閘道 | `test_brain_gateway_turn.py` |
| `brain-gateway:NFR13.3` | 記憶預取等待上限依實測嵌入 P95 定值 | 閘道 | `test_brain_gateway_memory.py` |
| `embedding-port:NFR3.1` | `embed` 在首字路徑上、須有上界（逾時常數） | embedding | `test_embedding_port.py`（上界存在已測，耗時未量） |
| `intent-router:NFR3.60`／`NFR3.66`／`NFR3.72` | `classify` 伺服器端 P50 ≤ 800 ms，併發下仍成立；耗時分佈可量測 | 路由 | — |
| `mcp-bridge:NFR21.3` | bridge 自身附加時間 P50 ≤ 50 ms（預算，非預測） | MCP bridge | — |
| `memory-service:NFR3.20`／`NFR3.23` | `search` 本體 P95 ≤ 150 ms；列表 P95 ≤ 300 ms | 記憶層 | — |
| `session-store:NFR3.40`／`3.41`／`3.42`／`NFR2.40` | `load`／`append_message` P95 ≤ 20 ms；`set_work_target` P95 ≤ 150 ms；狀態扇出 P95 ≤ 200 ms | session | — |

## 建議的量測方法（供承接者使用；本站未執行）

1. **環境**：`deploy/docker-compose.test.yml` 起的短生命週期 stack（真 PG＋Redis＋nginx），LLM 以固定延遲的假 provider 取代，避免把模型延遲算進平台延遲；只綁 `127.0.0.1`。
2. **計時**：依各目標的「伺服器端、不含使用者網路往返」定義，在方法進出點以 `time.perf_counter()` 記錄並輸出到 log 白名單欄位（各單元 `observability-design.md` 已定義的事件），再以腳本彙總 P50／P95。
3. **負載**：入口頁的併發送出數作為母體（`intent-router:NFR3.66`）；以 Playwright 或 `websockets` 腳本開 N 條 WS 連線同時送出。
4. **基準與回歸**：首次量測結果寫進該單元 `code-summary.md` 作為基準，之後每次量測與基準比對；超出目標即 `Not Met`，不得以放寬目標處理。
5. **承接者**：計畫中無 `performance-validation` stage，故承接需由 conductor／使用者指定（建議為合併後在 staging 由 operations 側執行，或新開一個效能驗證 intent）。

## 覆蓋期望

Standard 策略不要求效能測試；本檔的存在是為了讓 14 個數值目標（矩陣中 13 個單元層延遲列＋requirements 的 `NFR3`）的 `Unverified` 有可追溯的原因與量測方法，**不代表這些目標已達成**。
