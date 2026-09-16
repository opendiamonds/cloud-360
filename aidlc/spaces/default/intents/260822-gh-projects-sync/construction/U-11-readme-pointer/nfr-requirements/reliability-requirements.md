# Reliability Requirements — U-11 README 指路段落

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-11-readme-pointer
     `kind` 依 [ug:unit-of-work.md] 刻意留空，故解析出**全部五份**產出。 -->

## 適用性判定

**不適用。** 可靠度談的是「失敗時會怎樣、怎麼復原」，而本單元**沒有執行期可以失敗**。

一段已合併的 markdown 文字不會逾時、不會 rate limit、不會部分寫入、不需重試、不需降級。它唯一的「失敗模式」是**根本沒被寫進去**，而那不是可靠度問題，是 [US:S-11 AC 1] 的驗收條件沒過——由 `business-rules.md` 的 R-1（文字比對）在 PR 上直接判定。

`requirements.md` 的可靠度相關需求（NFR-S6 稽核記錄、FR-E3 的三要素）落在會產生 Status 變更的路徑上，本單元不產生任何 Status 變更。

> 同前兩份：`produces_kinds` 把本項限於 `kind: [service]`，U-11 因 `kind` 留空而觸發全矩陣。

## 與上游的對應

可靠度需求的落點引自 `requirements.md`；AC 引自 `stories.md` 的 S-11；驗證方式與完成判準引自 [ug:unit-of-work.md] 的 U-11；R-1 的定義見同輪的 `business-rules.md`，無執行序的判定見 `business-logic-model.md`；[kb:technology-stack.md] 記載 `README.md` 不經建置。
