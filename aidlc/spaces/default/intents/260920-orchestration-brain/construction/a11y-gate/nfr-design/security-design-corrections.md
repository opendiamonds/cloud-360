# 更正附錄 — `a11y-gate` 的 Security Design

<!-- Stage: nfr-design（Construction 3.3）· Unit: a11y-gate · 寫於 2026-10-17 -->

## 這份附錄是什麼

`security-design.md` 的審查（`reviews/review-01.md`）判 **READY**，另有 2 Major ＋ 6 Minor。審查收據記下後原檔凍結；與 `nfr-requirements` 同一個處置（使用者於 2026-10-17 核可的路徑）：原檔不動，本附錄逐條處置，**衝突時以本附錄為準**，`code-generation` 的計畫必須逐條綁定 `D-01`–`D-08`。本附錄**未經審查**。

## 逐條處置

### D-01 — 第 18 個掃描點的 `include` 目標（審查 `R-01`，Major）

**問題屬實**（實讀 `frontend/src/components/membership/ReselectionBanner.tsx`）：`:242` 的外層是 `<div data-slot="reselection-banner">`，`:247` 的 `reselection-banner-host` 只是其中一個 `role="status"` 的文字 `<div>`；確認（`:109`）、檢視成員（`:118`）、展開（`:130`）、專案清單（`:140`）都在 host **之外**的兄弟節點。限縮到 host 等於只掃一行摘要。

**取代為**：第 18 個掃描點以 `include('[data-slot="reselection-banner"]')` 限縮。**通則（追加為 `code-generation` 的完成條件）**：凡使用 `include()` 的掃描點，其就緒規格列出的每一個 test-id 都必須是 include 根節點的子孫——以一行斷言在掃描前檢查（`expect(root.getByTestId(id)).toBeVisible()`，而非 `page.getByTestId`）。

### D-02 — 互動步驟與定位器逐列寫定（審查 `R-02`，Major）

下表補足 `C-02` 表沒寫的部分，**以本表為準**：

| # | 掃描點 | 掃描前的互動 | 載入態排除定位器 | 其他 |
|---|---|---|---|---|
| 1 | 入口頁 | — | — | 排除方式改為斷言 `page.url()` 的 pathname 為 `/`（不是 `/login`、`/403`）——兩者都沒有 test-id，以路徑判定最直接 |
| 2 | `/memory` | — | — | 「至少一個區」改為固定片段：`memory-zone-semantic`、`memory-zone-procedural`、`memory-zone-episodic` 三者中至少一個可見；片段以 `memory-page-ui` 的映射表為準（`OPEN-MP15-4`），不用萬用字元 |
| 4–6 | 專案詳情三籤 | 點 `project-tab-<key>` 切換到該籤 | 文字「正在載入專案…」與（需求籤）「正在載入需求欄位…」皆 `toHaveCount(0)` | — |
| 8–9 | 成員清單 | — | 文字「載入中…」`toHaveCount(0)` | — |
| 10 | 成員詳情 | — | 文字「載入中…」`toHaveCount(0)` | — |
| 11–12 | 邀請對話框 | 點 `member-list-invite-button` 開啟 | — | denied 態依 `U24` 既有 e2e 的造法（攔截被邀請者缺全域權限） |
| 14 | 改選橫幅 multi-expanded | 點 `reselection-banner-expand` | — | 掃描前斷言其 `aria-expanded="true"` |
| 15 | 移出確認對話框 | 點 `member-detail-remove` | — | `remove-confirm-dialog` 只在點擊後渲染 |
| 16–17 | 專案清單空狀態／錯誤態 | — | `project-list-skeleton` `toHaveCount(0)` | — |

文字定位器使用 `page.getByText('<字串>', { exact: true })`。字串若在實作時已變，以程式為準並記入 `code-summary.md`——它變了而測試沒跟著改，結果是「載入態沒被排除」，就緒斷言仍會擋下大部分情形，但不是全部，所以必須同步。

### D-03 — 寫檔式過期檢查的兩個前提（審查 `R-03`，Minor）

- **掃描 test 必須在任何斷言之前先寫檔**（掃描完成、套用基準之前就寫「實際看到的條目」）。否則一個真實的新違規會讓該點沒寫檔，連帶讓過期檢查因檔案數不足而紅，紅燈原因被混淆。
- **重試排程未查證**：Playwright 在 worker 重啟後，失敗 test 的重試是否一定排在同檔後續 test 之前，本站與審查都沒有查證。處置：`code-generation` 以突變 `M10`（一次性失敗）實證；若重試排在過期檢查之後，把過期檢查移出 `a11y.spec.ts`，改為獨立的 `a11y-baseline.spec.ts`，並以 `playwright.config.ts` 的 project `dependencies` 讓它在掃描 spec 全部完成後才跑——這會改到 `playwright.config.ts`，須在計畫中揭露。

### D-04 — 無穩定選擇器的頁殼節點（審查 `R-04`，Minor）

- Playwright 沒有直接取得計算後可及名稱的 API；「role ＋ 可及名稱」改為**實作時以 axe 結果的 `target` 回到 DOM，讀該元素的 `aria-label`、`aria-labelledby` 指向的文字或其文字內容**作為名稱，與 role 組合。
- 四者皆取不到的頁殼節點：原設計說「不得進基準，只能修或停下回報」。**維持**，理由：沒有穩定選擇器的條目正是會在無關變更時位移、讓規則 2 誤紅的那一種。審查指出這可能迫使第一次實跑就去動 `Sidebar` 舊項——那是真實代價，**`code-generation` 若遇到，停下來回報筆數與位置**，由使用者決定是補屬性（改頁殼）還是接受該掃描點以 `exclude()` 排除該節點並記錄。

### D-05 — WebSocket 的兜底改為事前攔截（審查 `R-05`，Minor）

- 隔離層最先註冊 `page.routeWebSocket(/.*/, (ws) => { leakedWs.push(ws.url()); ws.close(); })`，再註冊兩個具體樣式（後註冊者優先，同 HTTP）。未被具體樣式接管的 WebSocket 會落進兜底、在連線前被關閉並記錄——**不會連到真實閘道**，`M2` 的說法因此成立。
- `page.on('websocket')` 對 `routeWebSocket` 接管的連線是否觸發**未查證**；改以兜底 handler 內的計數為證據，不依賴該事件。`code-generation` 可另做小實驗並記錄，但閘門不依賴它。

### D-06 — axe 規則分類未驗證（審查 `R-06`，Minor）

`C-03` 規則 5 對 `landmark-*`／`region`／`heading-order`／`page-has-heading-one` 屬 best-practice 的陳述，本站與審查都**未在本機驗證**（`node_modules` 無 `axe-core`）。處置不變：`code-generation` 裝好套件後以 `axe.getRules(['wcag2a','wcag2aa','wcag21a','wcag21aa'])` 列出實際執行的規則，與規則 5 清單交叉比對，結果記入 `code-summary.md`；不符時以實查為準。

### D-07 — 契約前綴落差的承接者（審查 `R-07`，Minor）

原文寫「`build-and-test` 或下一次修訂 `contract-summary.md`」太含糊。**改為**：承接者是 **`build-and-test`（ALWAYS）**，動作是把 `K-13`／`K-19`／`K-20` 的 `brain-*` 前綴宣稱與實際 test-id 的落差列為一項跨單元一致性發現，交使用者裁決「改契約文字」或「改程式 id」。本單元不改任何一方。

### D-08 — 補兩個突變（審查 `R-08`，Minor）

| # | 突變 | 必須紅在 |
|---|---|---|
| M11 | 第 18 個掃描點的 `include` 改回 `reselection-banner-host` | D-01 的「就緒 test-id 必須在 include 子樹內」斷言 |
| M12 | 任一掃描點的 `ready` 清單清空 | 一個靜態檢查：每個掃描點的 `ready` 至少一項（在基準清單檢查的同一個非瀏覽器 test 內一併檢查） |
