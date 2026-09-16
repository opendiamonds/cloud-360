# Scalability Requirements — U-6 正向同步 workflow

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-6-forward-workflow · kind: service -->

## 三個會成長的維度，各自的行為

| 維度 | 現況 | 成長時的行為 |
| --- | --- | --- |
| **intent 數** | 6 個 record（5 個可解析） | **線性**——registry 驅動的選取每輪掃全部。第 4 段延遲隨之成長 |
| **Project 的 item 總數** | 與 intent 數同量級 | **常數**——[Q1=A] 以 `Issue.projectItems` 反查，不列舉整個 Project |
| **事件頻率** | 每次 push 一輪，`danniel/**` 為主 | 見下方「排隊行為」 |

**第二列是設計上的主要成果**：若當初選了「列舉整個 Project 建索引」（U-3 的 [Q1=B]），這一列會變成線性，且會與 [req:FR-I4] 的單次操作上限（**已知未定值**，PRE-1 第 2 項）相撞。

## 排隊行為與其已知殘留

concurrency group 以**分支**為界（[ad:services.md] S-A），不同分支互不排隊。**同分支**高頻 push 時：

- GitHub 只保留**一個** pending run。
- 第三個以後到達的會**取消先前的 pending**——即使 `cancel-in-progress: false`。

**這不造成遺漏，只造成延遲**：選取是漂移驅動的，被取消 run 的工作由下一次執行涵蓋。[ad:services.md] 已如實記載此殘留，本站**不弱化亦不補救**——補救需要一個佇列，而本設計刻意零新增基礎設施（[req:NFR-S4]）。

## 沒有上限機制，且這是刻意的

[req:FR-D3]／[req:NFR-P4] 的單次處理量上限落在 **U-7（對帳）**，不在本單元。

理由：對帳掃**全部** intent 且每日一次，撞上 [req:FR-I4] 上限的風險高；本單元由事件觸發，一輪只處理 registry 內的 intent，且第 4 段的呼叫次數與 intent 數同量級。**在 6 個 record 的現況下距離任何上限都很遠。**

**但這是一個依賴現況的判斷，不是結構性保證。** 若 intent 數成長到數十個，本單元也需要一個上限——屆時的落點與 U-7 相同（`reconcile_batch_size` 的同族設定）。**記明此為現況判斷，以免下游把它讀成「本單元不需要上限」。**

## 與上游的對應

intent 數與事件頻率的現況引自 [ad:services.md] 的擴縮特性表；排隊殘留逐字引自同表；[Q1=A] 的 item 查找路徑引自 U-3 的 `domain-entities.md`；[req:FR-D3]／[req:FR-I4]／[req:NFR-P4]／[req:NFR-S4] 引自 `requirements.md`；concurrency 規則見本單元的 `business-rules.md` R-1 群，一輪執行的序列見 `business-logic-model.md`；單元邊界引自 [ug:unit-of-work.md] 的 U-6。
