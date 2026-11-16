# NFR 驗證矩陣（目標 vs 實測）

> 實測數字出處：`test-results.md`（run 43887439909／43888107820 的 artifact）。判定欄只用「通過／未達標／待裁決／未量測」四種；未量測者寫明原因，**不推論為已通過**。
> 未達標的處置依 [Q6]=A 由使用者在本站核可關卡逐項裁決（`requirements.md` NFR1 校正程序：不得自動改寫門檻）。

## 一、延遲與準確率（本站量測）

| ID | 目標 | 實測 | 判定 |
|---|---|---|---|
| `NFR1` 意圖識別準確率 | ≥ 80%（≥ 50 筆標註） | 逐筆 **79.4%**（54／68）、5 併發 **82.4%**（56／68）、合計 **80.9%**（110／136） | **未達標（裁決 (b)：維持 80%、改善後重測，見 §三）**：逐筆一輪低於門檻、合計略高；未命中全部是「該交辦卻反問」，0 筆交辦錯（`test-results.md` §一） |
| `intent-router:NFR1.60` 反問率與準確率並列 | 必須可量測且同時呈現 | 30.0%／28.3% | 通過（已量測並並列） |
| `NFR3` 首字 P50 | ≤ 2 秒（伺服器端） | **621 ms**（P95 2456 ms，P95 無目標） | 通過 |
| `intent-router:NFR3.60` `classify` P50 | ≤ 800 ms | 逐筆 **411.8 ms**；完整對話中 418 ms | 通過 |
| `intent-router:NFR3.66` 併發下 NFR3.60 仍成立 | P50 ≤ 800 ms | 5 併發 **449.1 ms**（P95 578.0 ms） | 通過 |
| `brain-gateway:NFR13.1(a)` 分類前段 P50 | ≤ 400 ms | **123 ms** | 通過 |
| `brain-gateway:NFR13.1(b)` 分類後到首則內容 P50 | ≤ 300 ms | **12 ms** | 通過 |
| `brain-gateway:NFR13.3` 記憶預取等待上限依實測定值 | 取 ≥ 暖機 P95 × 1.5 且 ≤ 3000 ms | 未單獨量測嵌入耗時；首字 P95 2456 ms 的長尾落在分類前段，與記憶預取一致 | 未量測（需在預取處加計時才能定值） |
| `memory-service:NFR3.20`／`NFR3.23` | search P95 ≤ 150 ms；列表 P95 ≤ 300 ms | — | 未量測（日誌無耗時欄位） |
| `session-store:NFR3.40`／`3.41`／`3.42`、`NFR2.40` | P95 ≤ 20／20／150／200 ms | — | 未量測（同上） |
| `mcp-bridge:NFR21.3` | bridge 附加時間 P50 ≤ 50 ms | — | 未量測（對話主路徑不經 bridge） |

## 二、擴展性（`scalability-requirements.md`）

這些是**結構性上限與正確性約束**（連線數、訊框大小、頻率、原子寫入、無共享狀態），不是負載下的延遲指標。staging 單機、無自動擴展（[Q1]=A），本站**不以負載重驗**；下表照實標出 build-and-test 是否已把它列為未驗證。

| 單元 | ID | 內容（摘要） | build-and-test 狀態 | 本站 |
|---|---|---|---|---|
| brain-gateway | `NFR13.17`／`13.18` | 每行程 200、每 session 10 條連線上限 | 未列入未驗證清單 | 未量測 |
| brain-gateway | `NFR13.19` | 入站訊框上限 64 KiB | 未列入 | 未量測 |
| brain-gateway | `NFR13.20` | 每 session 60 秒至多 20 則 `user_message` | 未列入 | **實際觸及**：量測 B 依此放慢為每句 3.2 秒；`test_brain_gateway_limits` 為其單元測試（本 intent 曾修正其機率性失敗） |
| intent-router | `NFR3.67` | 不引入行程內共享可變狀態 | 未列入 | 未量測 |
| intent-router | `NFR9.61`／`NFR9.62` | 每輪成本與歷程線性；不設本層速率限制 | 未列入 | 未量測；量測 A 5 併發 0 錯誤，未觸及供應商限流 |
| mcp-bridge | `NFR21.20`–`21.23` | 請求／回應本體上限、併發 16、無狀態 | 未列入 | 未量測 |
| membership-service | `NFR12.13`／`NFR12.14` | 鎖限單一專案；`reselection_events` 不設保存期 | `NFR12.14` 為 Unverified | 未量測 |
| memory-service | `NFR7.27`–`7.29` | 成長上界、列表分頁、檢索 limit 上限 | `NFR7.27` 為 Unverified | 未量測 |
| requirement-field-service | `NFR20.15`–`20.18` | 列數上界、只增不減、併發寫入收斂 | `NFR20.16` 為 Unverified | 未量測 |
| session-store | `NFR4.40`／`4.41`、`NFR2.41`／`2.42` | ≥ 300 個滿載 session 不觸及 maxmemory；扇出線性 | `NFR4.41`、`NFR2.41`、`NFR2.42` 為 Unverified | 未量測 |
| work-orchestrator | `NFR12.12`–`12.15` | 原子寫入、復原只推進一次、背景執行數＝處理中項數 | 未列入 | 未量測 |

「未列入」只表示 build-and-test 的未驗證清單（83 項，`construction/build-and-test/test-results.md`）沒有它，**不代表已被驗證**——本站沒有逐條查證它們的測試落點。

## 三、需要使用者裁決的項目

| ID | 選項（`requirements.md` NFR1 校正程序） | 連動 |
|---|---|---|
| `NFR1` | (a) 接受實測值為新門檻並記錄理由；(b) 維持 80% 並要求改善後重測；(c) 判定門檻本身設錯並重定 | 調整 NFR1 時必須同時處理 FR1.7 的信心門檻 0.7——本次未命中全部是「多反問」，降低 0.7 是最直接的改善方向，但會增加交辦錯的風險；兩者的新舊值必須同時記錄 |

**裁決（2026-11-16，使用者於本站核可關卡以選單選定）：(b) 維持原值、改善後重測。**

| 項目 | 舊值 | 新值 |
|---|---|---|
| NFR1 準確率門檻 | 80% | 80%（不變） |
| FR1.7 信心門檻 | 0.7 | 0.7（不變，待改善工作決定） |

- 本次實測判定為**首次未穩定達標**（逐筆一輪 79.4% 低於門檻）。
- 後續工作：調整信心門檻 0.7（例如試 0.6）或 Decisions 問題設計，以**同一份**標註集（`load-test-plan.md` §三）重測，並同時報告準確率、反問率與「交辦錯」筆數——後者是降低門檻的代價，本次為 0。
- 依連動條款，任何一方改值時都要在此表補上新舊對照。

上游涵蓋：`construction/*/nfr-requirements/performance-requirements.md`、`scalability-requirements.md`；`construction/*/nfr-design/performance-design.md`、`scalability-design.md`；`operation/observability-setup/dashboards.md`（無 dashboard，量測以日誌與排程計數承載）。
