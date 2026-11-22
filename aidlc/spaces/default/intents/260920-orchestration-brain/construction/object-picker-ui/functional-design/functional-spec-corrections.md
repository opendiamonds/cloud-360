# 更正附錄 — `object-picker-ui` 的 Functional Design

<!-- Stage: functional-design（Construction 3.1）· Unit: object-picker-ui -->

## 這份附錄是什麼

功能設計的審查（`reviews/review-01.md`）判 **READY**，另有 2 Major ＋ 6 Minor。審查收據記下後 `functional-spec.md`／`frontend-components.md`／`traceability.json` 凍結；比照本 intent 已用過兩次的處置（`a11y-gate` 的 nfr-requirements 與 nfr-design），原檔不動，本附錄逐條處置，**衝突時以本附錄為準**。下游（`nfr-requirements` 起至 `code-generation`）必須逐條綁定 `F-01`–`F-08`。本附錄**未經審查**。

## 逐條處置

### F-01 — `AC9.2.3` 是上游文字與 `U7` 實作的矛盾，不是 `OK`（審查 `R-01`，Major）

**事實（本站重新核對）**：`stories.md:468` 的 `AC9.2.3` Then 逐字為「拒絕經由既有的 `require_story_action` 路徑」；而 `backend/services/hierarchy_router.py:14-17` 與 `hierarchy_facade.py:204-209` 逐字寫明**刻意不走** `require_story_action`，改在 facade 以 `user_can(self._db, principal.role, "K2", action)` 判定並 raise `HierarchyForbidden`。審查另指出：非擁有者在別人的專案下建系統，伺服器回的是 404 而非 403，`objectCreateAction` 會把它映射成「其他錯誤」文案而非「沒有權限」。

**更正**：
- `traceability.json` 中 `AC9.2.3` 的狀態應讀為 **`Deferred`**（不是 `OK`）：本單元的前端部分（無權限者不渲染建立入口、伺服器拒絕時顯示錯誤文案）成立；但 AC 字面要求的「經由 `require_story_action`」與已交付的 `U7` 實作直接矛盾，本單元無權裁決。
- **本站不改 `U7`、不改 AC**。處置為交 conductor 在關卡提交使用者裁決：「AC9.2.3 的字面改為『經由伺服器端的 K2 授權判定（facade `user_can`）』」或「要求 `U7` 改走 `require_story_action`」。依 `team.md ## Corrections`（下游經人工確認的語意變更不回改上游），前者較可能。
- **404 文案**：`code-generation` 須在 `objectCreateAction` 的消費端把「在別人的專案下建系統被 404」辨識為權限類失敗並顯示權限文案；若 `objectCreateAction` 無法區分，則以本單元的前端判定（`BR13`／`BR14` 的擁有者條件）保證該路徑不可達，並在 e2e 以 404 stub 驗證文案。實作時二擇一並記入 `code-summary.md`。

### F-02 — 選單開啟中連線離開 `ready`（審查 `R-02`，Major）

**問題屬實**：「切換對象」鈕只在 `status === 'ready'` 渲染（`BR11.1`），`pickerOpen` 是獨立 state；連線在選單開啟中中斷時鈕被卸載，`BR11.3`／`BR15.2` 的焦點返還目標消失，焦點落到 `body`。

**更正（追加為 `BR11.5`）**：
- `status` 離開 `ready` 時，**選單自動關閉**（`pickerOpen = false`），任何未送出的表單內容捨棄。
- 焦點返還目標改為「鈕若存在則回鈕；鈕不存在則回 `ContextBar` 的容器節點（設 `tabIndex={-1}` 以可程式聚焦）」。
- 同時以大腦頁面既有的 `LiveRegion` 播報一句「連線中斷，已關閉作業對象選單」——此時 dialog 已關，modal 外的播報可被唸出（見 F-04）。
- 狀態機補一條轉移：任何選單狀態 —`status ≠ ready`→ 關閉。
- e2e 補一案：開選單後讓攔截的 WebSocket 關閉，斷言選單消失、焦點在 `ContextBar` 容器、播報文字出現。

### F-03 — `user.id` 永久未決（審查 `R-03`，Minor）

`AuthContext.tsx` 的 `login()` 在 `/api/auth/me` 失敗時靜默保留無 id 的 user；`BR12.3` 會讓選單永遠骨架列。**更正（`BR12.3` 追加）**：選單開啟時若 `user.id` 不是數字，呼叫一次既有的 `refreshMe()`；仍不是數字即轉 **`error`** 態，文案「無法確認你的身分，請重新整理頁面」，附重試鈕（重試＝再呼叫一次 `refreshMe()`）。不得無限 `loading`。

### F-04 — 播報落點與 `aria-modal`（審查 `R-04`，Minor）

**更正（取代 `BR15.4`）**：dialog **內**放一個專屬的 `aria-live="polite"` 區，承載選單開啟期間的播報（`no-match` 結果數、建立失敗、切換失敗）；只有**關閉之後**才發生的訊息（「已建立並切換到 X」、F-02 的斷線關閉）寫入頁面層級的大腦 `LiveRegion`。兩者在時間上不重疊，故不會重複唸出——這是原 `BR15.4` 要防的事，以時間分工而非單一區域達成。

### F-05 — 每次開啟的 1 + P 請求（審查 `R-05`，Minor）

**更正（`BR12.1` 追加取捨）**：維持「每次開啟重抓」（資料新鮮度：剛建立的專案必須立即可選，`AC9.2.1`），但改為**延後抓系統**：開啟時只抓專案清單（1 個請求）；某專案的系統清單在使用者**展開該專案群組時**才抓，同一次開啟內不重抓。單一專案的系統清單失敗只讓該群組顯示錯誤與重試，不讓整個選單失敗（取代 `BR12.2` 的全有或全無）。`fanoutQueue.ts` 的連線池警告因此不再適用於本選單。

### F-06 — 狀態正交性與三問補漏（審查 `R-06`，Minor）

- 清單面（`loading`／`default`／`empty`／`error`／`no-match`，加上 F-05 的每群組系統載入狀態）與表單面（`openForm`：無／新增專案／新增系統於 P）是**正交**的兩個 state；清單重抓**不得**關閉已開啟的表單，表單取消後清單維持其當下狀態。
- 三問補漏：`switchError`——寫：`setWorkTarget` 回失敗時；讀：選單內 live region 與錯誤列；清：下一次選取開始時、選單關閉時。`reloadKey`——寫：重試鈕、建立成功後；讀：抓取 effect 的依賴；清：不需清（單調遞增）。`BR14.5` 的「`setWorkTarget` 回 false 時重抓清單」列為第三種重抓觸發，與 `BR12.1`（開啟）、重試鈕並列。
- 版面形態：選單為**錨定在「切換對象」鈕下方的 dialog**（`role="dialog"` ＋ `aria-modal="true"`），無全頁背景遮罩；點擊外部等同取消。手機寬度下改為全寬下拉；斷點沿用專案既有的 Tailwind `md:` 慣例，`code-generation` 實作時以 `ContextBar` 周邊實際使用的斷點為準（本站未逐一查證）。

### F-07 — 追溯與範圍縮減的下游影響（審查 `R-07`，Minor）

- `AC9.2.1`／`AC9.2.2` 的「可被選為作業對象」由 **`BR13.1`（可選性）＋ `BR11.2`（選取送出 `set_work_target`）** 共同承接；`traceability.json` 的 `BR11.2` reverse `N/A` 應讀為「承接 AC9.2.1／AC9.2.2 的選取動作」。
- `OPEN-OP16-1`（`CreateConfirmCard` 不實作）影響的下游文件，本站不回改，列於此供關卡一併決定：`unit-of-work.md:196` 的 U16 交付清單、`delivery-planning/bolt-plan.md:354`、`refined-mockups/accessibility-checklist.md` 中列 `CreateConfirmCard` 為受管元件的 O-1／R-2 列、`U17 a11y-gate` 的掃描面（`CreateConfirmCard` 不存在，故無須掃描；`U17` 的 18＋1 個掃描點本來就未含它）。

### F-08 — D-4 的理由更正（審查 `R-08`，Minor）

原文暗示專案頁已有刪除路徑。**實際**：`frontend/src` 內無任何 `deleteProject`／`deleteSystem` 或 `DELETE` 呼叫，`hierarchy_router.py` 的兩支 DELETE 端點目前**沒有任何前端消費者**。D-4（刪除被拒的訊息）的畫面面前提不成立——不是落點誤指，是整條刪除使用者路徑尚不存在。處置不變（無自然承接站、交關卡），但關卡上應以「是否另開 intent 建立刪除入口」提出。

## 交關卡的事項彙整

| # | 事項 | 來源 |
|---|---|---|
| G-1 | `CreateConfirmCard` 不實作（範圍縮減）與其下游文件 | `OPEN-OP16-1`、F-07 |
| G-2 | `AC9.2.3` 字面與 `U7` 實作矛盾，請裁決改 AC 或改 `U7` | F-01 |
| G-3 | 刪除使用者路徑不存在，是否另開 intent | D-4、F-08 |
| G-4 | 新建架構圖的系統歸屬無端點 | D-5 |
| G-5 | 受邀成員看得到但選不了自己的非擁有專案 | `OPEN-OP16-5`（即 `OPEN-PP23-6` ③） |
