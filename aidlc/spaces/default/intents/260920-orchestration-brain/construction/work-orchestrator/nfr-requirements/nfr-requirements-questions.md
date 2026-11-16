# NFR Requirements 問題檔 — `U12 work-orchestrator`

> Depth 為 `Minimal`。本單元是 `service`，五個 NFR 類別**全部適用**。
>
> **本站出題數為 0。** 逐類查過之後，每一類的關鍵取捨若不是上游或本單元 functional-design 已定案，就是可由
> repo 現況直接查證，沒有一項是「預設錯了會造成真實重工、且只有使用者能決定」的。先例為 `U15`、`U20` 的同一站。
> 下表逐項寫出「為什麼不問」。

## 〇、不重問的事（已定案或可查證，附出處）

| 類別 | 事項 | 定案處 |
|---|---|---|
| 安全 | 呼叫既有能力走 HTTP 帶使用者 token、不同進程直呼 service | `X-01`／`X-02`；`BR51.1` |
| 安全 | token 不落地、訊息不洩內部錯誤 | `BR51.2`、`BR58.4` |
| 安全 | `requestText` 與變更摘要的靜態加密 | 併入上游 `OQ-3`（指派 `nfr-design`），不在單元層定 |
| 效能 | 先回覆後執行；不呼叫 LLM | `BR58.2`；`[WO1]`=A |
| 效能 | 成本輪詢間隔與上限 | `BR57.1`、`BR56.6`（2 秒、360 秒） |
| 可靠性 | 工作項存 Redis、比對後寫入、復原掃描、牆鐘上限、不重試 | `BR52.4`、`BR52.7`、`BR56.4`、`BR56.6`、`BR56.7`；`[WO3]`=A |
| 可靠性 | `review-03` 的 6 項 | 使用者 2026-10-12 裁決帶入 code-generation；本站轉為可驗證的 NFR（`reliability-requirements.md` 第三節） |
| 觀測 | logger 命名 | `team.md ## Code Style` 的 `"cloud360.<module>"` 慣例 |
| 技術棧 | 零新套件；`unittest`＋`hypothesis`，非 pytest | `codekb/chiton/technology-stack.md`、`team.md ## Testing Posture` |
| 部署 | 零新進程、零新監聽埠、零新環境變數 | `unit-of-work.md:48`（embedded）；functional-spec 2.2 |

## 一、刻意不出成題目的事（附理由）

1. **絕對延遲目標**：本 repo 沒有延遲量測機制；出題請使用者選一個數字，選完也無法驗證，是假選擇。以「不等待能力」
   （`NFR12.1`）代替。
2. **是否改用任務佇列**：新增依賴與新進程，而上游已定案零新進程（embedded）；重啟由復原掃描處理。
3. **`AC10.2.4`／`AC1.3.2`／`AC5.1.3` 的裁決**：已在 functional-design 交使用者（`OPEN-WO12-6`／`OPEN-WO12-7`），
   非 NFR 題，本站不重問。

## 二、問題

（無）
