# Performance Requirements — U-11 README 指路段落

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-11-readme-pointer
     `kind` 依 [ug:unit-of-work.md] 刻意留空，故解析出**全部五份**產出。 -->

## 適用性判定

**不適用。** 本單元沒有執行期——它是一段靜態文字，不在任何 workflow、請求或排程路徑上。

`requirements.md` 的四條效能需求逐項對照：

| # | 內容 | 對 U-11 |
| --- | --- | --- |
| NFR-P1 | 同步延遲上限 5 分鐘，自 record 被推送起算 | **不適用**——本單元不參與同步 |
| NFR-P2 | 對帳每日一次 | **不適用**——落在 U-7 |
| NFR-P3 | 事件觸發兩條路徑共用 concurrency group | **不適用**——本單元不觸發任何 workflow |
| NFR-P4 | 對帳單次處理量上限 | **不適用**——落在 U-7 |

**四條全部不適用，且理由都是同一個**：本單元的交付物不執行。

> `produces_kinds` 把 `performance-requirements` 限於 `kind: [service, ui]`；U-11 的 `kind` 刻意留空而觸發全矩陣，本檔因此被要求產出。這是 [ug:unit-of-work.md] 已知並接受的選擇（「五類皆不合，收完整設計矩陣」），不是本站的判斷失誤。

## 與上游的對應

NFR 編號與內容引自 `requirements.md`；`kind` 留空的理由引自 [ug:unit-of-work.md] 的 U-11；本單元無商業邏輯的判定見 `business-logic-model.md`，唯二規則見 `business-rules.md`；技術面見同輪的 `tech-stack-decisions.md`（並引 [kb:technology-stack.md]）。
