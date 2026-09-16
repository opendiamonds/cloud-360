# Reliability Requirements — U-7 對帳 workflow 與編排器

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-7-reconcile-workflow · kind: service -->

## 本單元是其他單元的可靠度來源

U-1～U-6 的可靠度論證幾乎都以同一句收尾：「下一輪或**隔日對帳**會補上」。**那個隔日對帳就是本單元。**

| 誰的復原路徑指向這裡 | 情形 |
| --- | --- |
| U-6 | 防線②整輪 skip、pending run 被淘汰、`reverse_pending` 中止 |
| U-4 | `Rejected` 後的回寫未完成 |
| U-3 | `Aborted` 後看板值與 record 不一致 |

**因此本單元自身的失敗是唯一沒有下游兜底的失敗**——它失敗就只能等明天。這是它與其他單元在可靠度上的結構差異，必須被寫下來。

## 部分完成是正常狀態，不是失敗

[ad:component-methods.md] §C-7 逐字：「單一 intent 失敗不中止整輪；計入報告後續跑」。

**一輪對帳的「成功」不等於「全部補平」**——它等於「掃過了、該補的補了、補不了的列進清單了」。報告本身就是那一輪的完整結果，含失敗的部分。

**這與 U-6 不同**：U-6 的一輪要嘛寫要嘛不寫，本單元的一輪永遠有部分成功。

## 冪等性

**重跑一輪對帳，結果相同**（在期間無外部變化的前提下）。三個機制：

| 機制 | 保障 | 出處 |
| --- | --- | --- |
| 寫入前回讀比對 | 補平不覆寫他人改動 | U-3 的 R-2.1 |
| 有落差才補 | 無落差時零寫入 | R-1 群 |
| 清單成員身分由 `reason_code` 決定 | 同樣輸入必得同樣清單 | R-1 群（`map()` 是純函式） |

**`backfilled_count` 不冪等，且這是正確的**——它記的是「**本輪**補了幾筆」，重跑一輪自然是 0（因為上一輪已經補完）。[req:FR-D4] 要的正是這個語意。

## 唯一的 fail-closed 路徑

`reverse_pending` 查不到 → **整輪中止**（R-4.2，同 U-6）。

**這是本單元唯一會整輪中止的情形。** 其餘任何單一 intent 的失敗都不中止。分界是**影響範圍**：`reverse_pending` 決定 `awaiting_human` 清單，而該清單直接決定一致率的分母——算錯它，整份報告的核心數字就是錯的。

**發布一份分母算錯的報告，比不發布更糟**：P4 會據以判斷「機制健康嗎」，而錯的比率會給出錯的答案。

## 沒有 SLO，同 U-6

`phases/operation.md` 要求 SLO 量化。本 intent 未定義任何 SLO；[req:NFR-O2] 的「一致率目標為 **0**」是**目標值**（分子為 0）而非可用性百分比。

**本站不發明 SLO**，但記明：本單元產出的一致率**是本機制唯一可長期追蹤的健康指標**。若未來要定 SLO，它是唯一有量測基礎的候選。

## 與上游的對應

`reconcile` 的錯誤處理引自 [ad:component-methods.md] §C-7；S-B 的生命週期引自 [ad:services.md]；[req:FR-C1]／[FR-D4]／[NFR-O1]／[NFR-O2] 引自 `requirements.md`；[US:S-7]／[US:S-9] 引自 `stories.md`；ADR-A5 的兩類排除引自 [ad:decisions.md]；U-6 的復原路徑引自其 `reliability-requirements.md`，U-4 的 `Rejected` 引自其 `business-rules.md` R-3 群，U-3 的回讀比對引自其 `business-rules.md` R-2 群；本單元的規則見 `business-rules.md`，一輪序列見 `business-logic-model.md`，欄位表見 `domain-entities.md`；SLO 的要求引自 `phases/operation.md`；單元邊界引自 [ug:unit-of-work.md] 的 U-7。
