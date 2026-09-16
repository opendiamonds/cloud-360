# Scalability Requirements — U-7 對帳 workflow 與編排器

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-7-reconcile-workflow · kind: service -->

## 本單元是全機制中**唯一必然線性**的部分

U-6 由事件觸發，一輪只需處理有變化的分支；本單元**每日掃過全部 intent**，成本必然隨 intent 數線性成長。

| 維度 | 成長行為 |
| --- | --- |
| **intent 數** | **線性**——每個約 4 次 API 呼叫（見 `performance-requirements.md`） |
| **Project item 總數** | **常數**——[Q1=A] 的反查路徑 |
| 通報 issue 數 | **常數**——[Q2=A] 於 U-5 定案的一次列舉 |

**因此批次上限（`reconcile_batch_size`）是本單元唯一的擴縮控制**，也是它存在的理由。

## 批次上限與一致率分母的交界（R-3.4）

`business-rules.md` 的 R-3.4 記載了一個上游沒寫的問題：

**若批次上限真的被觸發，而報告無法區分「本輪未處理」與「已處理且一致」，一致率會失真**——分母把未處理的也算進去，分子卻不含它們，比率因此偏高（看起來比實際更一致）。

**這比「比率偏低」危險**：偏低會促使人去查，偏高會讓人以為沒事。

**本站不裁定具體形式**（取決於 PRE-1 第 2 項後批次上限是否真會被觸發），但列出兩個候選供下游：報告加 `deferred: [intent_id]` 欄位；或分母改為「本輪**實際處理**的已綁定 intent」。**後者會改動 NFR-O2 的分母定義，屬對已核可指標的變更，需回上游。**

## 六個 record 的現況離上限很遠，但那是現況

`services.md` 的擴縮特性表記載現況為 6 個 record（5 個可解析）。以每個 4 次呼叫計，一輪 26 次。

**若 intent 數成長到數十個**，批次上限會開始生效，R-3.4 的交界也會從理論變成實際。**本站把它寫成規則而非備註，正是因為那一天不會有任何訊號提醒。**

## 與上游的對應

intent 數現況引自 [ad:services.md] 的擴縮特性表；批次上限引自 [ad:component-methods.md] §C-7 與 [US:S-7 AC 3]；一致率分母定義引自 [req:NFR-O2] 與 [ad:decisions.md] ADR-A5；[Q1=A] 的查找路徑引自 U-3 的 `domain-entities.md`，[Q2=A] 的一次列舉引自 U-5 的 `business-rules.md` R-3 群；R-3.4 的交界見本單元的 `business-rules.md`，呼叫成本拆解見 `performance-requirements.md`，一輪序列見 `business-logic-model.md`；FR-D3／FR-I4 引自 `requirements.md`；單元邊界引自 [ug:unit-of-work.md] 的 U-7。
