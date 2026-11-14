# Performance Design — `U15 memory-page-ui`

> 把 `nfr-requirements/performance-requirements.md` 的 `UIP-1`～`UIP-6` 逐條落到
> 設計形狀。程式片段僅為介面層示意，實作屬 code-generation。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `nfr-requirements/performance-requirements.md` | `UIP-1`～`UIP-6` |
| `nfr-requirements/tech-stack-decisions.md` | `TS-U15-2`、`TS-U15-4`、`TS-U15-6` |
| `functional-design/functional-spec.md` | `W1`、`W3`、`W4` |
| `functional-design/frontend-components.md` | §四、§五 |
| 出貨程式 | `frontend/src/pages/AdminPage.tsx:198-203`（補償重抓先例） |

## 一、開頁：三區並行、各自結束（`UIP-1`）

- `MemoryPage` 在 `user.id` 成為 number 後一次掛載三個 `MemoryZone`；每個
  `MemoryZone` 在自己的 `useEffect` 內發出自己的請求，三者天然並行，**不需要**
  `Promise.all`——用 `Promise.all` 反而會讓最慢的一區拖住另外兩區的渲染，與
  `BR32.2`「每區各自結束」衝突。
- 每區的 `useEffect` 依賴為 `[kind, page]`（語意／程序區的 `page` 恆為 1），
  故開頁恰觸發 3 次請求。
- **驗證**：e2e 以路由攔截讓情節記憶區延遲 2 秒回應，斷言此期間語意區已渲染
  `default` 或 `empty` 態——這同時證明並行與各自結束。

## 二、刪除後的補償重抓（`UIP-3`；處置審查 `R-01`）

沿用 `AdminPage.tsx:198-203` 的形狀，不另起語意：

1. `DELETE` 回 204／404 → 以 `filter` 回傳新陣列移除該列（`BR34.4`）。
2. **僅情節記憶區**：接著以背景方式重抓**目前頁**（同 `offset`、同 `limit=21`）。
   - 背景重抓期間該區**不**切換為 `loading`（`BR34.3`）；回應到達後整頁以新陣列
     替換，`hasNext` 與「第 N–M 則」一併重算。
   - 重抓失敗：保留就地移除後的畫面，**不**轉 `error`——使用者剛完成的刪除是成功的，
     不應被一次補償失敗蓋掉；下一次翻頁會自然拿到正確資料。
   - 重抓回來的頁面為空且 `page > 1` → 套用 `BR34.6` 退回前一頁（此時才觸發第二次
     `GET`，但那是頁次改變造成的，不計入單次刪除的預算——`UIP-3` 的「至多 1 次」
     指同頁補償）。
3. **語意／程序區不重抓**：兩區不分頁，沒有 offset 位移可補；滿 200 則時的計數標示
   問題（nfr-requirements 審查的 R-08）由 code-generation 決定是否在移除後保留「+」。

```ts
// 介面示意，非實作
function onRemoved(id: string): void;            // filter 移除，回傳新陣列
function resyncEpisodicPageInBackground(page: number): void; // 不切 loading，失敗靜默保留
```

## 三、翻頁的競態（`UIP-4`）

- 只有情節記憶區的 `page` 改變，故只有該區的 `useEffect` 重跑（`UIP-4` 的
  「恰 1 次」由依賴陣列保證，而非由額外邏輯保證）。
- 使用者連按兩次「下一頁」時，第一次的回應可能晚於第二次到達。沿用 `team.md` 的
  `cancelled` flag：`page` 改變時前一次 effect 的 cleanup 把 flag 設為 true，晚到的
  回應被丟棄，**不會**以舊頁覆蓋新頁。

## 四、筆數上限（`UIP-2`、`UIP-5`）

- 常數集中於 `memoryPaging.ts`：`EPISODIC_PAGE_SIZE = 20`、`FULL_ZONE_LIMIT = 200`。
  請求參數由常數推導（`limit = EPISODIC_PAGE_SIZE + 1`），不在呼叫點寫死 21。
- 改變每頁筆數只需改一個常數，無契約影響——與 nfr-requirements 的「可逆決定」一致。

## 五、刪除進行中的互動（`UIP-6`）

- `deleting` 是 `MemoryItem` 自己的 state，不是 `MemoryZone` 的；故一則刪除中時，
  其他條目的刪除入口不受影響。這是由 state 落點保證，不需要額外的鎖或佇列。
- 同一區內兩則同時刪除：兩次 `filter` 各自以 `prev` 為基礎，不會互相覆蓋；
  兩次背景重抓由 `cancelled` flag 保留最後一次。

## 六、不做的效能手段

| 不做 | 理由 |
|---|---|
| 跨頁或跨工作階段快取 | 與 `NFR7.90` 衝突（記憶內容只存在於元件 state） |
| 虛擬滾動 | 上限 200 則，`TS-U15-1` 零新依賴 |
| 預先抓取下一頁 | 每頁多一次請求，違反 `UIP-4` 的「恰 1 次」 |
| 毫秒級延遲預算 | 延遲由 `U8` 決定（`performance-requirements.md §三之二`） |
