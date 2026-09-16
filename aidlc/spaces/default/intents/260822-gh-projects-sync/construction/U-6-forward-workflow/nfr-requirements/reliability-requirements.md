# Reliability Requirements — U-6 正向同步 workflow

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-6-forward-workflow · kind: service -->

## 本單元的可靠度來自「可重跑」，不是「不失敗」

本設計零常駐程序、零資料庫（[req:NFR-S4]）。每一輪都是短生命週期的 workflow run，跑完即消失。因此可靠度的問題不是「怎麼不失敗」，而是**「失敗之後下一輪能不能自己補回來」**。

**答案是能，且原因是結構性的**：選取為 **registry 驅動 ＋ 漂移判定**（[ad:services.md] S-A）。任何一輪的失敗、取消或跳過，都只是讓「該寫而沒寫」的漂移留在原地——下一次事件或隔日對帳會重新算出同樣的漂移並補上。

## 四種中斷各自的復原路徑

| 中斷 | 復原 | 是否留痕 |
| --- | --- | --- |
| run 被取消（同分支高頻 push 的 pending 淘汰） | 下一輪自然涵蓋 | 否——**這是唯一無痕的一種** |
| 防線②整輪 skip（HEAD commit 含 `[aidlc-sync]`） | 下一次事件或隔日對帳 | workflow log |
| `reverse_pending` 查詢失敗 → 整輪中止 | 下一輪 | **紅燈 ＋ 通報**（R-2.5） |
| 單一 intent 失敗 | 下一輪對該 intent 重算 | 依 `reason_code`；`ExternalError`／`Rejected` 紅燈 |

**第一列值得特別記**：pending 被淘汰時**沒有任何紀錄說它發生過**——GitHub 不會為被取消的 pending run 留下明顯訊號。它不造成遺漏（下一輪涵蓋），但它也不可觀測。這是 `cancel-in-progress: false` 之下 GitHub 平台行為的既有限制，不是本設計引入的。

## 冪等性

**一輪執行對同一個 record 重跑，結果相同。** 三個機制各自保障一段：

| 機制 | 保障 | 出處 |
| --- | --- | --- |
| 首建前檢查已有綁定編號 | 重跑不產生第二則 issue | U-3 的 R-3.1（[US:S-1 AC 6]） |
| 寫入前回讀比對 | 重跑不覆寫他人的改動 | U-3 的 R-2.1（[req:FR-C1]） |
| 有漂移才寫 | 重跑在無變化時不產生任何寫入 | [ad:services.md] S-A |

**三者缺一都會讓重跑產生副作用**，而重跑在本設計中是**常態**（每次 push 一輪）。

## 沒有 SLO，且此為誠實記載

`phases/operation.md` 要求「SLO 須以具體百分比與時間窗量化」。**本 intent 沒有定義任何 SLO**——`requirements.md` 只有 NFR-P1 的 5 分鐘延遲上限，那是單次的上限值，不是「99.x% 的執行在 5 分鐘內」的統計目標。

**本站不自行發明一個 SLO。** 上游沒有要求，且發明一個沒有量測機制支撐的百分比，與 `team.md` 記載的「80% 覆蓋率是宣告而非閘門」是同一種問題。[req:NFR-O1]／[req:NFR-O2] 定義的可觀測指標（對帳補平次數、一致率）落在 **U-7**，那才是本機制實際可量測的東西。

## 與上游的對應

零常駐與零資料庫引自 [req:NFR-S4] 與 [ad:services.md]；registry 驅動的選取、漂移判定、兩道防線與排隊殘留引自 [ad:services.md] 的 S-A 與擴縮特性表；`reverse_pending` 的 fail-closed 引自本單元的 `business-rules.md` R-2.5，一輪序列見 `business-logic-model.md`；冪等三機制引自 U-3 的 `business-rules.md` R-2／R-3 群；[req:FR-C1]／[req:NFR-O1]／[req:NFR-O2] 與 [US:S-1 AC 6] 引自 `requirements.md` 與 `stories.md`；SLO 的要求引自 `phases/operation.md`；單元邊界引自 [ug:unit-of-work.md] 的 U-6。
