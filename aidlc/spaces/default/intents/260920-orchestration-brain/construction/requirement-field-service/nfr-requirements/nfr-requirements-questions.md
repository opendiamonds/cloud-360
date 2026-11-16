# NFR Requirements 問題檔 — `U20 requirement-field-service`

> Depth 為 `Minimal`。本單元是 `service`，故五個 NFR 類別**全部適用**。
>
> **本站出題數為 0。** 逐類查過之後，每一類的關鍵取捨若不是上游已定案，就是可由
> repo 現況直接查證，沒有一項是「預設錯了會造成真實重工、且只有使用者能決定」的。
> 先例為 `U15 memory-page-ui` 的同一站（同樣 0 題）。下表逐項寫出「為什麼不問」，
> 不留空白。

## 〇、不重問的事（上游已定案或可查證，附出處）

| 類別 | 事項 | 定案處 |
|---|---|---|
| 安全 | 授權順序、兩層串聯、待核准先拒、拒絕形式 | 本單元 `BR41.1`–`BR41.6`（functional-design，`review-02` READY） |
| 安全 | 輸入驗證（組與 key 白名單、長度上限、代寫路徑空值） | `BR42.1`–`BR42.5` |
| 安全 | 錯誤不回顯原文與值（含框架 422） | `BR46.3`／`BR46.4`；`review-02` 的 R-04 帶進 code-generation |
| 效能 | 讀取為單一查詢、計數與明細同源 | `BR44.4`；不變量 `I-4` |
| 效能 | 不加快取 | 同 `U19` 不加快取的理由（見其 `performance-requirements.md` 第一節）：讀的是授權結論與使用者剛寫的值，快取會引入「已改未見」的窗口 |
| 可靠性 | 單一交易、失敗回滾 | `BR46.2` |
| 可靠性 | 寫入冪等（upsert）、清空冪等（no-op） | `BR43.4`／`BR43.5`；`K-17` `retry_and_idempotency` |
| 可靠性 | 同欄併發寫入為最後寫入者勝，不做樂觀並行控制 | `BR43.5`；`OPEN-RF20-2`（已揭露的已知限制） |
| 可靠性 | 資料表收斂敘述的前置條件與重跑安全 | `BR47.2`；`review-02` 的 R-01／R-02 帶進 code-generation（使用者 2026-10-12 裁決） |
| 擴展 | 資料量上界 | 可算：每系統的已宣告欄位數為 7（`entities.md` 的 `field_definitions_v1`，腳本實算） |
| 觀測 | 拒絕 log 欄位、logger 命名 | `BR41.6`；`team.md ## Code Style` 的 `"cloud360.<module>"` 慣例 |
| 技術棧 | FastAPI／SQLAlchemy 2.x／PostgreSQL；測試為 `unittest`，**非 pytest** | `codekb/chiton/technology-stack.md`、`team.md ## Testing Posture` |
| 部署 | 零新進程、零新監聽埠 | `unit-of-work.md:308`（embedded，同一 process 的新 router） |

## 一、刻意不出成題目的兩件事（附理由）

1. **絕對延遲目標（如 p95 ≤ N ms）**：本 repo 沒有任何延遲量測機制（`U19` 的
   `performance-requirements.md` 第三節已查證並記載）；出題請使用者選一個數字，
   選完也無法驗證，是假選擇。改以可二元判定的查詢次數作為效能需求。
2. **欄位值的歷史保留**：`ADR-015` 已定「只保留最新值、列不刪」，`domain-design`
   核可；在本站重問等於重開已核可的上游決定。

## 二、問題

（無）
