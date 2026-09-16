# 效能需求 — U-8 反向同步 workflow

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-8-reverse-workflow · kind: service -->

## 缺口 P-2：NFR-P3 只指派了兩組 concurrency group，反向同步是**第三條路徑**

NFR-P3 逐字：「事件觸發的兩條路徑（PR、push）共用一個 concurrency group 且 `cancel-in-progress: false`；**排程對帳自成一組**」。

**反向同步也是排程觸發，但它不是對帳。** NFR-P3 的兩組劃分窮舉的是「事件 vs 排程對帳」，反向同步落在兩者之外——上游從未指派它。

| 路徑 | 觸發 | NFR-P3 指派的組 |
| --- | --- | --- |
| 正向（push／PR，U-6） | 事件 | 事件組 |
| 對帳（U-7） | 排程 | 對帳組 |
| **反向（本單元）** | **排程** | **未指派** |

**未指派不是無害的預設**。若實作者「順手」把它併進對帳組，兩者共用一組即互相排隊；若各自不宣告，同一支反向 workflow 的兩次排程執行可能重疊，而重疊的兩次執行會各自看到 `pending_reverse` 為空、各開一個 PR。

**處置**：**本單元自成第三組，`cancel-in-progress: false`**。理由：(1) 它與對帳都是排程但目的不同，共用一組會讓其中一個延後而無實益；(2) `cancel-in-progress: false` 是必須的——反向同步中途被取消會讓該輪的人為改動沒被送到任何人面前（見 `reliability-requirements.md` 的失敗視窗；`ut` 不受影響，但這一輪白跑）。此為**本站裁定**（未經人工提問），指派 U-8 的實作與 Bolt 3 的 gate 確認。

## 成本模型

| 量 | 值 |
| --- | --- |
| 觸發頻率 | 每日一次（與 NFR-P2 的對帳同頻但獨立） |
| 每輪 API 呼叫 | N 次 `read_item`（N ＝ 已綁定的 intent 數）＋ 每個偵測到變更的 intent 一次 commit-push-PR |
| 延遲要求 | **無**。NFR-P1 的 5 分鐘只約束正向路徑（「自 record 被推送起算」），反向路徑無等價需求 |

## 觀察 P-3：U-7 與 U-8 每日各掃一次全部已綁定 intent

兩者都對每個已綁定 intent 呼叫 `read_item`，合計每日 **2N** 次讀取。它們比較的東西不同（對帳比 record→看板，反向比看板雜湊→儲存雜湊），但**讀回來的 `ItemState` 是同一份**。

**這記為觀察，不是缺陷。** 合併兩者需要跨 Bolt 的設計變更（U-7 在 Bolt 2、U-8 在 Bolt 3），而 N 在可預見範圍內是數十量級，2N 次讀取距離任何速率上限都很遠。**列出它的理由是讓「N 變大時第一個該看哪裡」有紀錄**，而不是要現在改。C-T5 的上限值一旦確認（NFR-P4 追蹤中），這裡是重新評估的落點。

## 既有技術堆疊的承接

P-2 的三組 concurrency group 全部落在 gh-aw 編譯出的 `.lock.yml` 內。[ck:technology-stack.md] 記載 agent job 跑 `ubuntu-latest`、`activation`／`conclusion`／`safe_outputs` 跑 `ubuntu-slim`——**一支 gh-aw workflow 的一次「執行」其實是多個 job**，`concurrency` 宣告在哪一層會決定排隊行為，這一點在寫 `.md` 時看不出來，須以編譯後的 `.lock.yml` 複驗。

## 與上游的對應

NFR-P1～P4 引自 `requirements.md`；每輪的呼叫序列與「唯一失敗視窗」引自本單元的 `business-logic-model.md`；`read_item` 的歸屬與 R-4c 的方法對照引自本單元的 `business-rules.md`；本 repo 既有的 gh-aw／CI 堆疊事實引自 [ck:technology-stack.md]（`aidlc/spaces/default/codekb/cloud-360/technology-stack.md`）。
