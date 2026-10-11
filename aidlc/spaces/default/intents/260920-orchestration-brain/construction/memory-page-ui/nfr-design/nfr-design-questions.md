# NFR Design 問題檔 — `U15 memory-page-ui`

> 單元類型 **`ui`**。`produces_kinds` 使本站產出 `performance-design`、
> `security-design`、`logical-components`、`traceability` 四份；
> **`scalability`／`reliability`／`observability` 三份為 `[service]`，不適用本單元**。
>
> stage condition 逐字「NFR Requirements was executed and NFR patterns need design」：
> 上一站已執行並產出 6 條 `UIP`、4 條 `NFR*.9x`、5 條 `SEC-U15`、9 條 `TS-U15`，
> 其中 `UIP-3`（刪除後的補償重抓）與 `NFR7.90`（不跨頁快取）需要設計落點，故適用。
>
> Depth **Minimal**。

## 一、上游已定案、本站不重問

| 事項 | 定案 | 出處 |
|---|---|---|
| 三區各一個請求、並行 | `[M2]`=A；`UIP-1` | functional-design、nfr-requirements |
| 刪除後的請求預算 | 至多 1 次同 kind 同頁 `GET`（`UIP-3`） | nfr-requirements |
| 審查 `R-01`／`R-02`／`R-03` 與後端 pending 帳號缺口 | 使用者裁決帶進 `U15` 的 code-generation 計畫 | nfr-requirements `security-requirements.md §四之一`；兩站 diary 的 Open questions |
| 記憶內容不落地、不打 log | `NFR4.90`、`NFR7.90`、`SEC-U15-5` | nfr-requirements |
| 驗證層 | 僅 Playwright e2e ＋ 後端 `TestClient` | `team.md` |

## 二、問題

**本站無待問題目。** 本站的設計選擇只有兩處存在多個可行形狀，兩者都由已落地的
repo 先例決定，而不是由偏好決定：

1. **`UIP-3` 的補償重抓形狀**：`AdminPage.tsx:198-203` 的
   `resyncCurrentPageInBackground(page)` 已是本 repo 對「就地移除 ＋ offset 分頁」
   的唯一既有解法，且其註解 `:198-199` 逐字說明它防的正是審查 `R-01` 的缺陷。
   沿用它不需要任何新判斷；另起一種形狀反而會在同一 repo 出現兩套補償語意。
2. **翻頁競態的處置**：`team.md` Code Style 已規定 `useEffect` 內以 `cancelled`
   flag 防卸載後 setState；同一個 flag 套在「頁次改變」上即可丟棄晚到的舊頁回應。

若審查或閘門認為上述任一項應交使用者裁決，處置是在本檔追加題目並重走作答。

## 三、歧義分析

| 檢查 | 結果 |
|---|---|
| 含糊答案 | 無（無作答） |
| 設計之間的矛盾 | **無**。背景重抓（`performance-design.md §二`）與 `BR34.3`「刪除中只有該則停用、該區不進入 `loading`」相容——重抓期間該區**不**切換為 `loading` 態，只在回應到達後以新陣列替換 |
| 缺少的細節 | 無 |
