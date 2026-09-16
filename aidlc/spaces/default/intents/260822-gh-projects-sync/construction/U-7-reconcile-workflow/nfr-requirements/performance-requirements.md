# Performance Requirements — U-7 對帳 workflow 與編排器

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-7-reconcile-workflow · kind: service -->

## 本單元同時是效能需求的**承載者**與**量測者**

| 角色 | 內容 |
| --- | --- |
| **承載** | NFR-P2（每日一次）、NFR-P4／FR-D3（單次處理量上限） |
| **量測** | `latency_samples` 是 **NFR-P1（U-6 的 5 分鐘延遲）** 的量測落點 |

**第二列值得單獨記**：U-6 的效能需求由本單元量測，而**兩者之間沒有 DAG 邊**。若本單元沒做出 `latency_samples`，NFR-P1 就沒有任何量測機制——它會變成一條無法證偽的宣稱。

## NFR-P2：每日一次

cron 觸發，須避開三個既有排程（`daily-digest` `0 23 * * 1-5`、`agentics-maintenance` `37 0 * * *`、`release-watch` `39 16 * * 1`）。此為 `stories.md` 全域 DoD 的建置期檢查項，非執行期行為。

## NFR-P4／FR-D3：單次處理量上限

以 workflow input `reconcile_batch_size` 宣告（[US:S-7 AC 3]）。

**上限的實際值待 PRE-1 第 2 項實測 C-T5（框架單次操作次數上限）後定。本站不臆測數字。**

### 每個 intent 的呼叫成本（本站拆解）

| 呼叫 | 次數／intent | 備註 |
| --- | --- | --- |
| `read_item` | 1 | [Q1=A] 的 `Issue.projectItems` 反查，與 Project item 總數無關 |
| `read_issue_state` | 1 | [US:S-9 AC 5] 的 issue 開關偵測 |
| `write_status` | 0 或 1 | 僅在有落差時 |
| `write_field` | 0 或 1 | 同上 |

**每輪另有兩次與 intent 數無關的固定呼叫**：`reverse_pending` 查詢（一次）、通報 issue 列舉（一次，若本輪有失敗）。

**現況 6 個 record 的上界**：6 × 4 ＋ 2 = **26 次**。距離任何合理的框架上限都很遠，但**這是現況判斷**——C-T5 的實際值未知（PRE-1 第 2 項），批次上限的必要性要等那個值才能判定。

## 與 U-6 的效能取捨不同

U-6 由事件觸發，延遲直接影響使用者感受（5 分鐘上限）。本單元每日一次，**延遲不敏感**——它的效能約束是**總量**（不撞上框架上限），不是**速度**。

因此本單元**不設自身的延遲上限**，也不需要。若一輪對帳跑十分鐘，沒有任何 AC 會失敗。

## 與上游的對應

NFR-P1／P2／P4 與 FR-D3／FR-D4／FR-I4 引自 `requirements.md`；[US:S-7 AC 3]／[US:S-9 AC 5] 與全域 DoD 的排程項引自 `stories.md`；`ReconcileReport` 的欄位與批次上限引自 [ad:component-methods.md] §C-7，S-B 的生命週期引自 [ad:services.md]；[Q1=A] 的 item 查找路徑引自 U-3 的 `domain-entities.md`；`reverse_pending` 的一次查詢引自 U-6 的 `business-rules.md` R-2 群；本單元的清單成員規則見 `business-rules.md` R-1 群，一輪序列見 `business-logic-model.md`，欄位表見 `domain-entities.md`；單元邊界引自 [ug:unit-of-work.md] 的 U-7。
