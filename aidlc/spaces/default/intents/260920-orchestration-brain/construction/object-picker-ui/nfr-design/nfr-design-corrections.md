# 更正附錄 — `object-picker-ui` 的 NFR Design

> 撰寫時間 2026-10-18T02:23:48Z（`date -u` 取值）。

## 這份附錄是什麼

本站審查（`reviews/review-01.md`）判 **READY**：0 Critical、2 Major、5 Minor。收據記下後四份產出凍結；比照本 intent 既有處置，原檔不動，本附錄逐條處置，
**衝突時以本附錄為準**。下游（`infrastructure-design`、`code-generation`）必須逐條綁定 `D-01`–`D-07`，並同時綁定上游的
`functional-spec-corrections.md`（`F-01`–`F-08`）與 `nfr-requirements-corrections.md`（`N-01`–`N-07`）。本附錄**未經審查**。

## 逐條處置

### D-01 — `ensureSystems` 的冪等不能讀 state（審查 `R-01`，Major）

**問題屬實**：搜尋補抓入列的工作閉包住入列當下的 state，佇列後段的工作稍後才執行；其間按下同一群組的展開鈕，兩條路徑都讀到 `idle`，同一專案抓兩次，違反 `N-02` 第 5 點。
這與 `performance-design.md` §三為單發鎖所做的推理是同一件事，我沒有套用到這裡。

**更正（取代 `performance-design.md` §一之一、§一之二的對應敘述）**：
- 冪等登記簿改為 `useRef<Map<number, 'loading' | 'loaded' | 'error'>>`，`ensureSystems(p)` 在發出請求**之前同步**寫入 `'loading'`；只有登記簿無此鍵、或值為 `'error'` 且由重試鈕呼叫時才發請求。`systemsByProject` state 只負責畫面。
- `cancelled` 改為每次掛載一個 `mountedRef`（掛載 effect 設真、清理設假），事件處理函式與 effect 的非同步回呼都在寫 state 前檢查它。
- 新增 e2e：搜尋補抓進行中（以 `page.route` 延遲前 4 個系統請求，使第 5 個以後仍在佇列），對尚未發出的群組按展開鈕，斷言該群組 `listSystems` 恰 **1** 次。新增突變 **M12**：`ensureSystems` 改讀 state 的 `idle` → 該案紅。
- 請求計數類 e2e 一律對 `vite preview`（正式建置）執行，避免開發模式 `StrictMode`（`main.tsx:7`）的雙掛載使 `listProjects` 計為 2。

### D-02 — M9 的測法對突變恆綠（審查 `R-02`，Major）

**更正（取代 `security-design.md` §六 M9 的觸發方式）**：在**同一個 JS 任務內**連續觸發兩次送出——`locator.evaluate((el) => { el.click(); el.click(); })` 與 `form.requestSubmit()` 連呼兩次各一案——並以 `page.route` 延遲 POST 回應；斷言 POST 恰 **1** 次。
`code-generation` 的突變驗證必須**實際看到 M9 紅燈**；看不到就改測法，不得記為通過。

### D-03 — 觸發點表與 `F-06` 的細部落點（審查 `R-03`，Minor）

補進 `performance-design.md` §一之三的觸發表：

| 觸發 | 動作 | 請求數 | 是否計入 `N-02` 上界 |
|---|---|---|---|
| 專案清單 `error` 的重試鈕 | 清空登記簿與 `systemsByProject`，重跑掛載流程 | 1～2 | 否（使用者觸發的重試，與系統清單重試同類例外） |
| `setWorkTarget` 回 `false`（`BR14.5` 第三種重抓） | **不重抓**：顯示 `switchError`，選單不關；清單資料未失效 | 0 | — |
| 建立成功 | 切換作業對象並關閉選單（`BR14.5`），**不重抓**；下次開啟為新的掛載 | 0 | — |

因此 `reloadKey` **只**由專案清單重試鈕遞增（`F-06` 原列的「建立成功後」遞增不再需要）。`switchError` 的三問：寫＝`setWorkTarget` 回 `false`；讀＝選單內播報區與錯誤列；
清＝下一次選取開始時、選單關閉時（卸載）。版面：選單為錨定在鈕下方的 dialog；寬度在 `md:` 以下為全寬（`w-full`），`md:` 以上為固定寬度，斷點沿用
`ContextBar` 周邊既有的 Tailwind `md:` 慣例。以上補進 `logical-components.md` §一 `ObjectPicker` 列的責任欄。

### D-04 — `identity` 必須是衍生值（審查 `R-04`，Minor）

**更正（取代 `performance-design.md` §四的 state 形狀）**：`identity` 於渲染時衍生——`typeof user?.id === 'number' ? 'ok' : attempted ? 'failed' : 'resolving'`。`attempted` 為 state，
在 `refreshMe()` 的 `.finally` 回呼（非同步，非 effect 本文）內設真；`useRef` 只用來防止 effect 重複呼叫 `refreshMe`，**不參與渲染**（避開 `react-hooks/refs`）。
重試鈕：先 `setAttempted(false)` 再呼叫 `refreshMe()`，同樣在 `.finally` 設回真。

### D-05 — 斷線關閉寫法定案、播報重複字串（審查 `R-05`，Minor）

- **定案首選寫法**：依前值調整 state（`prevStatus` 比較後才 `setPickerOpen(false)`）。審查讀 `eslint-plugin-react-hooks` 原始碼確認 `set-state-in-render` 只報無條件區塊內的 setState，條件式會通過。
  **刪除備案**（卸載清理函式呼叫 `onConnectionLost()`）：清理函式在使用者主動關閉與開發模式 `StrictMode` 的模擬卸載時都會跑，後者會讓選單一開就關。`security-design.md` §九 S-3 因此結案。
- **重複播報**：`announce` 的實作是 `setAnnouncement(text)`（`useBrainConnection.ts:337`），相同字串不改 state、`LiveRegion` 不變，第二次斷線不會被唸出。處置：`ContextBar` 的斷線播報先呼叫 `announce('')` 再呼叫 `announce('連線中斷，已關閉作業對象選單')`——兩次 setState 若在同一個任務內會被 React 自動批次合併為最後一個值而失效，故以 `setTimeout(…, 0)` 把第二次延到下一個任務（微任務仍可能落在同一批次內，不採用）。e2e 加一案「同一頁連續兩次斷線，`window.__announcements` 中該文字出現 2 次」。

### D-06 — lint 區塊補齊（審查 `R-06`，Minor）

- `OBJECT_PICKER_RESTRICTIONS` 程式碼區塊**加入**：`{ selector: "MemberExpression[object.name='window'][property.name=/^(localStorage|sessionStorage|indexedDB|caches)$/]", message: 'OPN-15' }`（原只寫在注意事項的文字裡）。
- `security-design.md` §九 S-1 補兩項殘留：`el['innerHTML'] = …`（computed 屬性）不被 `MemberExpression.left[property.name=…]` 命中；`no-restricted-imports` 以匯入字串精確比對，`'../projects/projectsApi.ts'` 或日後的路徑別名可繞過。皆屬「擋無心之失、擋不住刻意繞過」。
- §九新增 S-4：`ContextBar.tsx`（`U14` 的檔）不在 lint 檔案集合內，其新增程式碼（鈕、`pickerOpen`、斷線處置）不受 `no-console`／儲存禁令約束；以 code review 與 e2e 主控台計數覆蓋。

### D-07 — 補四條突變、修正 M8（審查 `R-07`，Minor）

| # | 突變 | 預期紅燈（既有斷言） |
|---|---|---|
| M8（修正） | `setWorkTarget` 以 `as never` 傳數字 id（直接傳數字會先被 `tsc -b` 擋下） | e2e：送出訊框的 `projectId` 不是字串、「目前」不出現 |
| M13 | 移除 `backfillStarted`，每次輸入都補抓 | e2e：再輸入 10 字元後請求數由 31 增加（`N-02` 第 6 點） |
| M14 | 身分未決時不限次數呼叫 `refreshMe` | e2e：`/me` 多於 1 次（`N-01`） |
| M15 | `normalize` 拿掉 `NFKC` | e2e：以全形字 `ＡＢＣ` 搜尋半形名稱 `abc` 不命中 |
| M16 | 斷線時不移焦點或不播報 | e2e：`document.activeElement` 不是脈絡列、`window.__announcements` 長度為 0 |

加上 `D-01` 的 M12，突變總數由 11 增為 **16**。

## 本附錄不改動的部分

需求 id 集合與 `traceability.json` 的 25 條判定不變；ADR-0006 四面向與 PBT 判定不變。
