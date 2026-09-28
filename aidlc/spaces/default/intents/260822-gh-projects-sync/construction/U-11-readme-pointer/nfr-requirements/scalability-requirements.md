# Scalability Requirements — U-11 README 指路段落

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-11-readme-pointer
     `kind` 依 [ug:unit-of-work.md] 刻意留空，故解析出**全部五份**產出。 -->

## 適用性判定

**不適用。** 擴縮性談的是「量增加時行為如何」，而本單元的量**恆為 1**——`README.md` 只有一份，那段文字只寫一次。

沒有隨 intent 數、record 數、看板 item 數或事件頻率而變化的維度。`requirements.md` 中與量相關的需求（NFR-P4 的單次處理量上限、FR-D3 的對帳批次）全部落在 U-7，不在此。

> 同 `performance-requirements.md`：`produces_kinds` 把本項限於 `kind: [service]`，U-11 因 `kind` 留空而觸發全矩陣。

## 與上游的對應

量相關需求的落點引自 `requirements.md` 與 [ug:unit-of-work.md]（U-7 的完成判準）；本單元的交付與驗證方式引自 [ug:unit-of-work.md] 的 U-11；無商業邏輯的判定見 `business-logic-model.md`，規則清單見 `business-rules.md`；執行環境事實見 [kb:technology-stack.md]。
