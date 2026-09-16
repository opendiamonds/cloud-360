# Performance Requirements — U-6 正向同步 workflow

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-6-forward-workflow · kind: service -->

> **本單元是 NFR-P1 的唯一責任落點。** U-1～U-5 的效能面全部判定為「不適用」（`produces_kinds` 限 `[service, ui]`），延遲的責任在此收斂。

## NFR-P1：自 record 被推送起算 5 分鐘內看板更新

`requirements.md` 的驗收準則逐字：「自觸發 push 完成到看板 Status 更新的間隔不超過 5 分鐘（**在無對帳並行的前提下**，見 NFR-P3）」。

### 延遲預算的逐段拆解（本站新增）

上游只給了總額，沒有拆解。一輪執行的時間由五段組成：

| # | 段落 | 可控性 | 說明 |
| --- | --- | --- | --- |
| 1 | 事件到 run 啟動 | **不可控** | GitHub 的排隊時間。尖峰時可達數十秒 |
| 2 | checkout ＋ 環境準備 | 低 | `actions/checkout` ＋ `gh` 已預裝；無 `npm ci`、無 Docker build |
| 3 | `reverse_pending` 查詢 | **可控** | **一次**查詢（`business-rules.md` R-2.1），與 intent 數無關 |
| 4 | 逐 intent 處理 | **可控且是主要變數** | 6 個 record；每個最多 `read_item` ＋ `write_status` ＋ `write_field` |
| 5 | 回寫 ＋ push | 中 | 一次 commit；非快轉時最多重試 3 次（U-4 的 R-3.5） |

**第 4 段是唯一會隨規模成長的**。[Q1=A] 於 U-3 定案以 `Issue.projectItems` 反查而非列舉整個 Project，使**單次同步的成本與 Project 的 item 總數無關**——這是 NFR-P1 在設計層的主要保障。

### 排隊帶來的延遲不計入預算，但要記明

`cancel-in-progress: false`（[req:NFR-P3]）意謂同分支的事件**排隊**。若前一輪還在跑，本輪的 5 分鐘從它啟動起算，而非從 push 起算。

**上游的驗收準則寫的是「自觸發 push 完成」**——嚴格讀，排隊時間**計入**。本站不改寫該準則，但記明：**高頻 push 時該準則可能不成立，而這是 `cancel-in-progress: false` 的直接後果**，兩者是同一個取捨的兩面（不取消換來不遺漏）。

## 不適用的三條

| # | 內容 | 對本單元 |
| --- | --- | --- |
| NFR-P2 | 對帳每日一次 | **不適用**——落在 U-7 |
| NFR-P4 | 對帳單次處理量上限 | **不適用**——落在 U-7 |
| NFR-P3 | 並行 | **適用但屬 concurrency 設定**，見 `business-rules.md` R-1 群與 `scalability-requirements.md` |

## 與上游的對應

NFR-P1～P4 引自 `requirements.md`；concurrency 設定與「不取消換不遺漏」的取捨引自 [ad:services.md] 的 S-A 與本單元的 `business-rules.md` R-1 群；`reverse_pending` 的一次查詢引自同檔 R-2 群；item 查找路徑引自 U-3 的 `domain-entities.md`（[Q1=A]）；回寫重試引自 U-4 的 `business-rules.md` R-3.5；一輪執行的序列見本單元的 `business-logic-model.md`；單元邊界引自 [ug:unit-of-work.md] 的 U-6。
