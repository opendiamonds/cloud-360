# Code Summary 更正附錄：`object-picker-ui`（U16）

<!-- Stage: code-generation（Construction 3.5）· Unit: object-picker-ui · Record: 260920-orchestration-brain -->

> 撰寫時間 2026-10-18T08:37:58Z（取自 `date -u`）。本檔處置 `reviews/review-01.md`（NOT-READY；R-01 Major、R-02–R-07 Minor）的全部 7 項。
> **本檔取代 `code-summary.md` 與 `traceability.json` 中和下文衝突的部分**。那兩份檔、`code-generation-plan.md`、`unit-test-instructions.md`、`source-manifest.json` 都已凍結，本輪沒有改動。
> 未 commit、未 push、未改 `.claude/`。後端、`deploy/`、`.github/`、`package.json`、`package-lock.json`、`ws-contract.json`、`playwright.config.ts`、`eslint.config.js`、`a11y.spec.ts` 本輪零變更。

## 一、本輪改動的檔案

| 檔案 | 改動 |
|---|---|
| `frontend/src/components/brain/ObjectPicker.tsx` | R-01 補抓觸發、R-04 根節點可聚焦、R-05 捲動／縮放即關閉、R-06 清除 `switchError`、R-07 補抓收尾比對佇列；檔頭契約補述 |
| `frontend/src/components/brain/ObjectPickerCreateForm.tsx` | R-06：`onFailure` 型別改為 `string \| null`，每輪送出先 `onFailure(null)` |
| `frontend/src/brain/objectPickerModel.ts` | R-05：新增唯一定義處 `PICKER_WIDTH_PX = 384` |
| `frontend/src/components/brain/ContextBar.tsx` | R-05：刪除手寫的 `PICKER_WIDTH`，改匯入 `PICKER_WIDTH_PX`；補註解。五態判定、名稱節點、徽章與切換沒有動到 |
| `frontend/tests/e2e/object-picker.spec.ts` | 新增 6 個 test（26 → 32）；改寫「關閉後晚到的舊回應永不出現」的規格註解（test 名稱不變，TCMS 名稱穩定） |

## 二、逐條處置

### R-01（Major）：清單載入前輸入的搜尋永不補抓

- **改了什麼**：新增 `queryRef`，在 `onSearch` 裡同步寫入。`startBackfill` 改為 `useCallback((list) => …, [ensureSystems])`，專案清單由參數傳入，不再讀 render 閉包。專案清單的 `.then` 在 `setProjectsState` 和「目前所在專案預設展開」之後，加一行判斷：`!backfillStartedRef.current && normalize(queryRef.current) !== ''` 成立時呼叫 `startBackfill(projects)`。這樣「清單已載入」和「搜尋字非空」兩個條件不論誰後成立，補抓都在那一刻開始：清單先到時由輸入事件觸發，使用者先輸入時由 `.then` 觸發。目前所在專案的 `ensureSystems` 先執行，因此補抓不會再抓它一次（仍是一次開啟每個專案至多 1 次）。`setProjectsState` 與 `setBackfillBusy(true)` 在同一次批次更新裡，畫面不會先閃一下「沒有符合的對象」。
- **新增 e2e**：`清單載入前輸入的搜尋在清單回來後即補抓`。以 `projectsHook` 擋住專案清單，在 `data-state=loading` 時輸入「zeta」，名稱裡只有專案 5 的系統含這個字串。斷言放行前只有 1 個專案清單請求；放行後不再輸入，系統 50 可見、群組展開、`data-state=default`，六個專案的系統各請求恰 1 次。
- **新突變 M17**：刪除 `.then` 內的補抓觸發那一行。**實際看到紅燈**：`brain-object-item-50` 的 `toBeVisible()` 失敗，`element(s) not found`。
- **殘留**：無。

### R-02（Minor）：「關閉即取消補抓」與「點選單外即關閉」沒有任何會變紅的測試

- **改了什麼**：產品程式不需要改，兩項行為原本就已實作。本項只補測試。
- **新增 e2e（2 個）**：
  - `補抓進行中關閉後不再發出系統請求`：12 個專案，系統清單一律擋住。輸入一個字後在途請求為 4，按 Escape，放行後等 800ms，系統請求總數仍為 4，專案 5–12 都是 0。
  - `點選單外關閉且焦點不留在已卸載節點`：焦點在搜尋框時，以 `page.mouse.click` 點視窗左下角 (8, 高度−8)。斷言選單數量為 0、切換鈕 `aria-expanded="false"`，`document.activeElement` 為 `{ exists: true, connected: true, inPicker: false }`。
- **新突變**：
  - **M18**：`holder.queue?.cancel();` 改為 `void holder;`。**紅燈**：系統請求 Expected 4 / Received 12。
  - **M19**：`document.addEventListener('mousedown', onPointerDown);` 改為 `void onPointerDown;`。**紅燈**：選單 `toHaveCount(0)` Expected 0 / Received 1。
- **殘留**：點外部之後，焦點落點由瀏覽器對該次 mousedown 的預設行為決定（例如 body）。`closePicker` 雖然先把焦點交給切換鈕，但隨後被預設行為蓋過。本案只斷言焦點仍在文件內、不在已卸載節點上，**不斷言焦點回到切換鈕**。F-06 的定義是「點外部等同取消」，並不要求返還焦點，所以不算缺陷，記在這裡供 `build-and-test` 判讀。

### R-03（Minor）：「晚到舊回應」案宣稱了它證明不了的事

- **改了什麼**：改寫 `關閉後晚到的舊回應永不出現` 的 `@purpose`／`@step`／`@pass`／`@note`（test 名稱不變）。新的 `@purpose` 只宣稱這個案例能證明的內容：關閉期間不發出任何新的 `/api/hierarchy` 請求；再開啟是一次新掛載，只發一個專案清單請求。`@note` 明寫：移除 `mountedRef`／`cancelled` 守衛時本案仍綠，「舊名稱從未出現」只是附帶觀察，不能當證據。斷言程式碼沒有改。
- **證據改指**：見 §四 traceability 更正。BR12.4 改指 R-02 新增的 `補抓進行中關閉後不再發出系統請求`（M18 紅燈）。OPN-02 的守衛**改為由程式碼審查承載**。
- **殘留**：`mountedRef`／`cancelled` 守衛（OPN-02）**至今沒有任何會變紅的自動化測試**。卸載後 React 不渲染 setState，前端又沒有 unit 測試框架（`team.md` D 不採），e2e 層無法觀察守衛失效。這是誠實的覆蓋缺口，沒有用恆綠斷言遮掩。

### R-04（Minor）：點到選單內的非控件區域後，Escape 與焦點陷阱失效

- **改了什麼**：
  1. dialog 根節點加上 `tabIndex={-1}` 與 `focus:outline-none`。
  2. 新增 `onRootMouseDown`：mousedown 落在選單內、但不在控件上時（以 `closest('button, input, textarea, select, a[href], label, [tabindex]')` 判斷，排除根節點本身），`preventDefault()` 並 `root.focus()`。落在控件上則不干預。
  3. Tab 陷阱把「焦點在根節點本身」視同不在任何控件上：Tab 跳到第一個控件，Shift+Tab 跳到最後一個。沒有這一步，從根節點按 Shift+Tab 會離開選單。
- **新增 e2e**：`點選單標題後按 Escape 仍關閉`。點標題後 activeElement 為 `brain-object-picker`；按 Tab 後焦點到 `brain-object-search`；再點標題按 Escape，選單關閉，焦點回到 `brain-context-switch-object`。
- **新突變 M20**：拿掉根節點的 `tabIndex={-1}`，並把 `onMouseDown={onRootMouseDown}` 改為 `onMouseDown={void onRootMouseDown}`。兩者要同時拿掉，原因見殘留。**紅燈**：第 1269 行 activeElement Expected `"brain-object-picker"` / Received `"brain-context-bar"`，焦點正好落到審查指出的祖先 `<section tabIndex=-1>`。
- **殘留**：瀏覽器原本就會把焦點交給 `tabIndex=-1` 的最近祖先，所以只留 `tabIndex` 時行為已正確，`onRootMouseDown` 是為了不依賴預設行為而加的。也因此，**單獨刪除 `onRootMouseDown` 不會變紅**，這段處理函式沒有獨立的突變證據。

### R-05（Minor）：`fixed` 定位只量測一次，捲動或縮放後選單與脈絡列脫離；寬度有兩份手寫副本

- **改了什麼**：
  1. `ObjectPicker` 新增一個 effect，掛載時記下切換鈕的 `getBoundingClientRect()` 與視窗寬高：
     - **捲動**：在 `document` 以 capture、passive 監聽 `scroll`，任何捲動容器（含 `/assessment` 內層的 `h-full overflow-y-auto`）都能收到。事件來源在選單內就忽略，選單自己的 `overflow-y-auto` 捲動不算。其餘情況只在切換鈕位置位移超過 1px 時呼叫 `onClose()`，未移位的捲動事件不會關閉選單。
     - **縮放**：`window` 的 `resize` 在寬或高與掛載時不同時呼叫 `onClose()`。
     - 只做關閉，不做重定位。
  2. 寬度只保留一個定義處：`objectPickerModel.ts` 的 `PICKER_WIDTH_PX = 384`。`ContextBar` 用它夾住左緣；`ObjectPicker` 用它產生 CSS 變數 `--picker-width`，class 由 `md:w-96` 改為 `md:w-(--picker-width)`，寫法與既有的 `md:left-(--picker-left)` 相同。
- **新增 e2e**：`開啟後視窗縮放或錨點捲動即關閉選單`。40 個專案讓選單可以捲動。選單自身 scrollTop 設為 200 後斷言 > 0，200ms 後選單仍可見。視窗由 1280×720 改為 1100×700 後選單關閉。重新開啟，從脈絡列往外找第一個加高後真的能捲的 `overflow-y` 祖先，捲 200px（斷言容器 scrollTop > 0）後選單關閉。
- **新突變**：
  - **M21a**：`window.addEventListener('resize', onResize);` 改為 `void onResize;`。**紅燈**：第 1303 行選單 Expected 0 / Received 1。
  - **M21b**：`document.addEventListener('scroll', …)` 改為 `void onScroll;`。**紅燈**：第 1322 行選單 Expected 0 / Received 1，縮放那一步已通過，紅在捲動那一步。
- **殘留（新增為關卡事項 G-7）**：
  1. `maxHeight = Math.max(240, innerHeight - top - 16)` 的下限 240 沒有處理。切換鈕靠近視窗底部時，選單仍會超出視窗、捲不到底。本輪依 brief 只做最小成本的「脫離即關閉」，沒有做往上展開或重定位。
  2. 部分行動瀏覽器的虛擬鍵盤會改變 `innerHeight`。若在那類瀏覽器上點搜尋框叫出鍵盤，選單可能立刻關閉。**本輪未在實機驗證**，交給 `build-and-test` 的手機實機操作，見 `code-summary.md` §十一。
  3. 捲動時的關閉判定以切換鈕位移為準。若頁面結構使選單的定位基準與切換鈕不同步（目前沒有這種情形），需要另外處理。

### R-06（Minor）：相同的建立錯誤連續兩次不重唸；`switchError` 遮蔽結果數播報

- **改了什麼**：
  1. `ObjectPickerCreateForm.submit` 在 `setError(null)` 的同時呼叫 `onFailure(null)`（型別放寬為 `string | null`）。父層的 `formFailure` 因此每輪先清空，失敗時再寫入；相同文案的第二次失敗也會讓選單內播報區的文字「先變、再回來」。
  2. `ObjectPicker` 的 `onSearch` 與 `toggleExpand` 開頭 `setSwitchError(null)`：使用者再次輸入或展開時清除切換錯誤，`listText` 的結果數播報不再被遮蔽。
- **新增 e2e**：`連續兩次同樣的建立失敗都被播報`。POST 一律回 409，不改名稱連送兩次。斷言 POST 為 2 次，`brain-object-picker-live` 對「已有同名的專案，請換一個名稱」的播報累計 2 次。
- **新突變 M22**：刪除 `onFailure(null);`。**紅燈**：播報次數 Expected 2 / Received 1。
- **殘留**：`switchError` 在輸入或展開時清除這一點**沒有專屬 e2e 與突變**，只由程式碼審查承載。既有的 `切換送不出時就地顯示且不重抓清單` 只走「點專案 → 開建立表單」，不經過輸入或展開，因此不受影響，仍為綠。

### R-07（Minor）：被取消的舊補抓輪可能清掉新一輪的忙碌旗標

- **改了什麼**：`startBackfill` 收尾改為 `if (mountedRef.current && queueHolder.current.queue === queue) setBackfillBusy(false);`。`retryProjects` 原本就把 `queueHolder.current.queue` 設為 `null`，舊輪的收尾因此比對失敗、不會清掉旗標。
- **新增 e2e**：無。審查已指出這條路徑今天走不到：重試鈕只在首次載入失敗的 error 態出現，那時補抓還沒發生過。
- **新突變**：無。
- **殘留**：由程式碼審查承載。日後若新增其他重跑掛載流程的途徑，應一併補上能構造「舊輪收尾晚於新輪開始」的 e2e。

## 三、突變表增補（接續 `code-summary.md` §五的 M1–M16）

方法與 §五相同：腳本以字串替換套用突變，先確認內容與備份不同，再 `npm run build`（含 `tsc -b`），以 `-g` 和 `--retries=0` 只跑對應 test，最後從備份還原。全部做完後重建，以乾淨原始碼重跑三個 spec，結果為 105 passed；並 grep 確認突變字串（`void holder`、`void onPointerDown`、`void onResize`、`void onScroll`、`void onRootMouseDown`）在原始碼中 0 命中，`onFailure(null)` 仍在。

| # | 突變 | 紅燈位置 |
|---|---|---|
| M17 | 刪除專案清單 `.then` 內的補抓觸發 | `清單載入前輸入的搜尋在清單回來後即補抓`：`brain-object-item-50` not found |
| M18 | `holder.queue?.cancel()` 改為 `void holder` | `補抓進行中關閉後不再發出系統請求`：Expected 4 / Received 12 |
| M19 | 不註冊 document `mousedown` 監聽 | `點選單外關閉且焦點不留在已卸載節點`：選單 Expected 0 / Received 1 |
| M20 | 拿掉根節點 `tabIndex={-1}` 與 `onMouseDown` | `點選單標題後按 Escape 仍關閉`：activeElement Expected `brain-object-picker` / Received `brain-context-bar` |
| M21a | 不註冊 `resize` 監聽 | `開啟後視窗縮放或錨點捲動即關閉選單`（第 1303 行）：Expected 0 / Received 1 |
| M21b | 不註冊 `scroll` 監聽 | 同上（第 1322 行）：Expected 0 / Received 1 |
| M22 | 刪除送出時的 `onFailure(null)` | `連續兩次同樣的建立失敗都被播報`：Expected 2 / Received 1 |

**M13 複驗**：本輪改寫了 `onSearch` 那一行，所以以新的字串重套 M13（刪除 `onSearch` 的 `!backfillStartedRef.current` 條件），仍然紅燈：`maxInFlightSystems` Expected ≤ 4 / Received 8。其餘 M1–M12、M14–M16 套用的程式行本輪沒有改動，**未重跑**。

**M20 的套用細節**：原本把 `onMouseDown` 改為 `undefined && onRootMouseDown`，`tsc` 回報 TS2873（運算式恆為 falsy），建置失敗，該次不算數。改用 `void onRootMouseDown` 後建置通過，看到上表的紅燈。

## 四、更正 `code-summary.md` 中失效的敘述

| 位置 | 原敘述 | 更正 |
|---|---|---|
| §一 交付檔案，`object-picker.spec.ts` | 「26 個 test」 | **32 個 test** |
| §一，`objectPickerModel.ts` | 純函式清單 | 另有常數 `PICKER_WIDTH_PX`（唯一定義處） |
| §五 標題與方法段 | 「M1–M16」「17 道」 | 本輪增補 M17–M22（M21 拆 a／b），共 **7 道新突變全部紅燈**，見本檔 §三 |
| §六 `object-picker.spec.ts` | 「26 passed / 0 failed」 | **32 passed / 0 failed**（本輪實跑） |
| §六 `tcms_validate.py --spec object-picker.spec.ts` | 「26/26 通過」 | **32/32 通過**。初跑 3 個 ERROR「預期結果無具體證據」，出在 R-02b、R-04、R-05 三個新案；補上 backtick 與具體值後重跑通過，只改註解 |
| §八 偏離 1 的殘留句 | 「選單開啟期間若外層捲動，選單不跟隨（不關閉）；視窗縮放時不重算」；class `md:w-96` | 開啟期間切換鈕因捲動移位或視窗尺寸改變時**選單關閉**（R-05）；class 改為 `md:w-(--picker-width)`。仍不重算位置，`maxHeight` 下限的殘留見 G-7 |
| §九 C 規則對應 e2e | 「全部 26 案」 | **全部 32 案** |
| §十一 `OPN-25` 段 | 「已記錄 M1–M16」 | `tcms-test-cases` 轉錄時須一併收錄本檔 §三的 M17–M22 |
| §十二 關卡事項 | G-1–G-6 | 新增 **G-7**，見本檔 §六 |

## 五、更正 `traceability.json`（不改原檔，以本表為準）

| id | 原 note | 更正後的證據指向 |
|---|---|---|
| `BR12.4` | 「卸載時 cancel 佇列、mountedRef 丟棄在途結果；e2e『關閉後晚到的舊回應永不出現』」 | **取消扇出**的證據改為 e2e `補抓進行中關閉後不再發出系統請求`（M18 紅燈）。「關閉後晚到的舊回應永不出現」只證明關閉期間零新請求、再開只有一個新請求。「mountedRef 丟棄在途結果」由**程式碼審查**承載，無會變紅的自動化測試 |
| `OPN-02` | 「mountedRef／cancelled 丟棄晚到結果；e2e 晚到舊回應案」 | **由程式碼審查承載**（`ObjectPicker.tsx` 的 `mountedRef` 與專案清單 effect 的 `cancelled`），不再以 e2e 晚到舊回應案為證據。status 仍為 OK，但證據類型是審查，不是自動化 |
| `BR15.2`（補充） | 「Tab 焦點陷阱、Escape、各關閉路徑焦點返還」 | 另加 e2e `點選單標題後按 Escape 仍關閉`（M20 紅燈）與 `點選單外關閉且焦點不留在已卸載節點`（M19 紅燈） |
| `OPN-06`／`BR12.1`（補充） | 「第一次輸入後補抓」 | 補抓的觸發改為對齊「清單已載入」與「搜尋非空」兩條件的成立時點；另加 e2e `清單載入前輸入的搜尋在清單回來後即補抓`（M17 紅燈） |
| `OPN-24`（補充） | fanoutQueue 只用於搜尋補抓 | 關閉即取消佇列的證據為 e2e `補抓進行中關閉後不再發出系統請求`（M18） |
| `BR14.4`／`BR15.4`（補充） | 失敗就地文案；開啟中寫選單內播報區 | 另加 e2e `連續兩次同樣的建立失敗都被播報`（M22 紅燈） |

## 六、關卡事項增補

| # | 事項 | 來源 |
|---|---|---|
| G-7 | 選單座標只量測一次，本輪採「錨點移位或視窗縮放即關閉」而非重定位。殘留兩點：(1) `maxHeight` 下限 240，切換鈕靠近視窗底部時選單超出視窗；(2) 行動瀏覽器虛擬鍵盤若改變 `innerHeight`，選單可能在叫出鍵盤時關閉，未經實機驗證。若不接受，需另做往上展開或重定位 | `review-01` R-05 |

## 七、本輪實跑的指令與結果

| 指令 | 結果 |
|---|---|
| `npm run build`（含 `tsc -b`） | 通過 |
| `npx vite preview --port 4173 --strictPort`（背景） | 結束時以 `pkill -f "vite preview --port 4173"` 停止 |
| `BASE_URL=http://localhost:4173 npx playwright test tests/e2e/object-picker.spec.ts tests/e2e/a11y.spec.ts tests/e2e/entry-page.spec.ts --reporter=list` | **105 passed / 0 failed**（object-picker 32、a11y 24、entry-page 49，依 `--list` 計數） |
| `npm run lint` | **0 errors、2 warnings**（`AssessmentPage.tsx`、`WorkspacePage.tsx` 的 `exhaustive-deps`，動工前即存在；warning 數未增） |
| `python3 scripts/tcms_validate.py --spec frontend/tests/e2e/object-picker.spec.ts` | **32/32 通過、ERROR 0、WARN 0** |
| 突變 M17–M22（7 道）與 M13 複驗 | 全部紅燈、全部還原（§三） |

未在本輪重跑：`memory-page`／`project-pages`／`member-pages` 三個 spec（本輪沒有改動它們讀取的檔案）、`validate_repo_contract.py`、`validate_env_contract.py`。

## 八、第二輪修正（review-02 R-08、R-09；2026-10-19T14:46:52Z）

第 2 輪審查的結果檔未能落地，該輪依引擎對未完成審查的處置記為 NOT-READY；使用者裁決「退回修改並修 R-08、R-09」，原文：「更正 traceability.json 中 BR12.4、OPN-02 的證據指向與 OPN-26 的案例數；收窄選單關閉條件：視窗大小變化只看寬度，對話框加 overscroll-contain。」

| 發現 | 處置 | 改動位置 |
|---|---|---|
| R-08 | `traceability.json` 直接更正三列（使用者明示要改該檔，故本輪不再沿用 §五「不改原檔」的做法）：`BR12.4` 的 e2e 證據改指「補抓進行中關閉後不再發出系統請求」；`OPN-02` 改為「守衛由程式碼審查承載」，並寫明「關閉後晚到的舊回應永不出現」移除守衛仍綠、不算證據（review-01 R-03）；`OPN-26` 由 26 案改為 32 案（`grep -c "^  test('"` 實算 32） | `traceability.json` |
| R-09 | `resize` 只比對 `innerWidth`，不再比對 `innerHeight`（虛擬鍵盤升起會改高度）；對話框加 `overscroll-contain`，選單捲到底不外溢到頁面 | `ObjectPicker.tsx` 第 321–342 行、對話框 `className` |
| R-09 測試 | `開啟後視窗縮放或錨點捲動即關閉選單` 增一步：只改高度（1280×720 → 1280×500）後選單仍可見；寬度改變（→ 1100×500）才關閉。案例名稱不變，TCMS 案例不會變孤兒 | `object-picker.spec.ts` |

**G-7 更新**：殘留 (2)「虛擬鍵盤改變 `innerHeight` 使選單關閉」已由本輪消除；殘留 (1)「`maxHeight` 下限 240」不變。`overscroll-contain` 未經實機驗證，仍交 `build-and-test` 的手機實機操作。

**突變增補**

| 突變 | 內容 | 結果 |
|---|---|---|
| M21c | `onResize` 恢復比對 `innerHeight`（寬或高任一改變即關閉） | **紅燈**：第 1305 行「只改高度後選單仍可見」Expected visible；還原後複驗綠 |

**本輪實跑**

| 指令 | 結果 |
|---|---|
| `npm run build`（含 `tsc -b`） | 通過 |
| `npm run lint` | 0 errors、2 warnings（與 §七 相同，未增） |
| `BASE_URL=http://localhost:4173 npx playwright test tests/e2e/object-picker.spec.ts --reporter=list` | **32 passed** |
| 同上加 `tests/e2e/a11y.spec.ts`（還原後複驗） | **56 passed**（32＋24） |
| `python3 scripts/tcms_validate.py --spec frontend/tests/e2e/object-picker.spec.ts` | **32/32、ERROR 0、WARN 0** |

## 九、Request Changes 後的回歸驗證（計畫 §八 Step 15；2026-10-24T14:14:23Z）

本輪不改程式。目的是確認其他單元在上一輪改到的畫面（`entry-page-ui` 的對話系統提示與 `ConversationView.tsx` 的顏色、`a11y-gate` 新增的三個掃描點）沒有讓本單元的案例或選單掃描點變紅。

| 指令 | 結果 |
|---|---|
| `npm --prefix frontend run build`（含 `tsc -b`） | 通過（`vite build` 轉換 324 個模組；只有既有的 chunk 大於 500 kB 警告） |
| `npm --prefix frontend run preview -- --port 4173 --strictPort`（背景） | 4173 動工前無人監聽；`curl` 回 200；測完以背景任務停止指令關閉，`lsof -iTCP:4173 -sTCP:LISTEN` 複查無監聽 |
| `BASE_URL=http://localhost:4173 frontend/node_modules/.bin/playwright test --config frontend/playwright.config.ts tests/e2e/object-picker.spec.ts tests/e2e/a11y.spec.ts --retries=0 --reporter=list` | **59 passed / 0 failed**（49.3s）：`U16 object picker` **32**、`U17 a11y gate` **27**（含本單元的「21 切換對象選單預設態」「22 切換對象選單建立錯誤態」兩個掃描點） |
| `npm --prefix frontend run lint` | **0 errors、2 warnings**（`AssessmentPage.tsx:395`、`WorkspacePage.tsx:344` 的 `exhaustive-deps`，與 §七、§八同兩檔；數量未增，行號隨他單元改動位移） |
| `python3 scripts/validate_repo_contract.py` | 通過（「Cloud-360 repository contract validation passed.」） |

`a11y.spec.ts` 由 §八 的 24 案增為 27 案，增加的 3 案來自 `a11y-gate` 本輪新增的掃描點（23 入口頁對話系統提示列、24 入口頁原句未送達、25 成員清單查不到專案），不屬本單元。

`source-manifest.json`、`traceability.json` 本輪無變更，未改動。未在本輪重跑：`entry-page.spec.ts`、`entry-page-live.spec.ts` 與其他 spec（不在 Step 15 範圍）、`validate_env_contract.py`、`tcms_validate.py`。

## 十、review-02（READY）兩項 Minor 的處置（使用者 2026-10-24 裁決「兩項都現在修」；記於 2026-10-24T15:01:48Z）

審查 `reviews/review-02.md` 的 R-08、R-09。凍結文件（本目錄與 `entry-page-ui/code-generation/` 的 `code-generation-plan.md`、`code-summary.md`、`unit-test-instructions.md`、`traceability.json`、`source-manifest.json`）一律未改，處置只記於本節與 `functional-design/merge-blockers.md` 第 2 列。

### 修正 1（R-08）：非輪次請求不覆寫待決的原句／反問選擇標記

- **跨單元揭露**：本修正改的是 `frontend/src/brain/useBrainConnection.ts`，該檔歸 `entry-page-ui` 所有（列於其 `source-manifest.json`），並**細化**其 `[EP-R2]` 規則（`merge-blockers.md` 第 2 列最後一段）。
- **改動**：新增純函式 `afterNonTurnSend(last)`——標記為「尚未收到任何輪次訊息」（`answered=false`）的 `user_message` 或 `select_clarify_candidate` 時原樣保留，否則回 `NOTHING_SENT`。`setWorkTarget`、`setSharingMode`、`correctWorkItem` 三個送出點由「一律重設為 `NOTHING_SENT`」改為經它判定。其餘規則不變：標記只在該請求收到第一則輪次訊息（`markAnswered`）或被一次非輪次錯誤的判定用掉時解除，連線重建時歸零。檔頭 `LastSent` 註解補上依據。
- **依據（逐行查證）**：閘道 `backend/services/brain_gateway.py` 的 `_receive_loop`（第 1082 行起）逐則 `await self._dispatch_client_message(...)`，`_on_user_message`（第 1307 行起）在同一個 await 內跑完整輪；所以被拒原句的 turnId=null error 必先於後送 `set_work_target` 的任何回應，受理的原句則先送出該輪訊息。
- **對既有案例的影響（揭露）**：`entry-page.spec.ts` 既有案「反問等待中作業對象切換失敗不重開反問」（名稱不變）原前置是「反問選擇未獲任何回應就送 `set_work_target`，之後的 null 錯誤不得重開反問」。依上述依序處理，那個時點到達的 null 錯誤**只可能是反問選擇被拒**，新規則下應重開，原斷言與本修正直接衝突（實跑紅：`data-state` 期望 picking）。處置：前置改為伺服器先以 `t-mb6` 的 token 與 done 受理該選擇（反問轉 `resolved`），再切換對象並收到 null 錯誤，斷言反問仍為 `resolved`（非 `default`）、候選 target-2 仍停用、原句不標未送達；`@purpose`／`@step`／`@note` 同步改寫。曾試「斷線重連後在新連線切換」的寫法，實跑不可行：重連快照的 `work_items` 會把 picking 收成 `resolved`。**副作用**：舊突變 M-R2（不論最後送出種類一律重開反問）在本規則下已無任何依序處理可達的情境能區分（存在 picking 的反問 ⇔ 標記正是那次待決的反問選擇），即等價突變，本案不再對它變紅；此點如實記載，非遺漏。
- **新增 e2e（`entry-page.spec.ts`，沿用既有寫法與規格註解區塊）**：
  - 「送出原句後切換對象再被非輪次錯誤拒絕時原句標為未送達」：送出原句 → 選單點專案 7（送出 1 則 `set_work_target`，伺服器不回推）→ 伺服器送 turnId=null 的 `INVALID_REQUEST` → 1 則系統提示、原句 `data-pending=false` 且含「這句沒有送達」、重試鈕可按、輸入列填字後送出鈕可按。
  - 「反問選擇送出後切換對象再被非輪次錯誤拒絕時反問可重選」（反問選擇一側，同一修正）：按候選 target-1（picking）→ 選單點專案 7 → null 錯誤 → 反問 `data-state=default`、target-2 可按。

### 修正 2（R-09）：重試建立時播報區不退回清單狀態文字

- **改動**：`ObjectPickerCreateForm.submit` 移除每輪送出前的 `onFailure(null)`，`onFailure` 型別收窄為 `(message: string) => void`。`ObjectPicker` 新增 `reportFormFailure`：與目前 `formFailure` 相同時附一個零寬空白（`REANNOUNCE_MARK`＝U+200B，再相同就拿掉），兩個表單（專案、系統）都改傳它。與 `useBrainConnection` 的 `announceFresh` 同一做法；更新式為純函式，不用 `RegExp`（U16 lint 區塊）。開表單、取消、建立成功時清空 `formFailure` 的既有行為不變。
- **既有案例調整**：「連續兩次同樣的建立失敗都被播報」（名稱不變）的比對改為去掉零寬空白後比對（新增共用 `stripMark`），`@purpose`／`@note` 改述重唸機制。
- **新增 e2e（`object-picker.spec.ts`）**：「重試建立時播報區不在兩次失敗之間退回清單狀態」：清單有 1 個自有專案、POST 一律 409；播報區先為「已載入 1 個專案」；自第一次送出起連送兩次，斷言 POST 2 次、去掉零寬空白後等於「已有同名的專案，請換一個名稱」的播報恰 2 次、且這段期間播報區沒有任何一次含「已載入」。

### 實跑（皆對 `vite preview` 生產建置，port 4811，跑完已停止 preview）

| 指令 | 結果 |
|---|---|
| `npm --prefix frontend run build` | 通過（324 個模組；只有既有的 chunk 大於 500 kB 警告） |
| `BASE_URL=http://localhost:4811 frontend/node_modules/.bin/playwright test --config frontend/playwright.config.ts tests/e2e/entry-page.spec.ts tests/e2e/object-picker.spec.ts tests/e2e/a11y.spec.ts --retries=0` | **120 passed / 0 failed**：`U14 entry page` **60**（58＋2 新）、`U16 object picker` **33**（32＋1 新）、`U17 a11y gate` **27**（數字取自 `--list` 輸出 `Total: 120 tests in 3 files`） |
| `npm --prefix frontend run lint` | **0 errors、2 warnings**（`AssessmentPage.tsx:395`、`WorkspacePage.tsx:344` 的 `exhaustive-deps`，既存） |
| `tsc -b frontend` | exit 0 |
| `python3 scripts/validate_repo_contract.py` | 通過 |

### 突變（每項：套用 → 重建 → `--retries=0` 跑該 spec → 以檔案編輯還原 → sha256 與基線相同；未用 git checkout）

基線（`shasum -a 256`）：`useBrainConnection.ts` `512878183e24fc5c4a63b920a834758eec188eac426e761387627afde5a80619`、`ObjectPickerCreateForm.tsx` `127b366ead16a5e14c2d2a1118d7abe4d4a933b8ddfbb7d1d2eecc9813379e2d`、`ObjectPicker.tsx` `28477cc2a5c4ee9593d1c422a80f4a3d56aeed8cc7c1cdba5737fafc7b568fa9`。

| 編號 | 突變 | 結果 |
|---|---|---|
| M-R8 | `afterNonTurnSend` 一律回 `NOTHING_SENT`（等同還原三個送出點的覆寫） | `entry-page.spec.ts` **58 passed / 2 failed**：「送出原句後切換對象…原句標為未送達」紅（`data-pending` 期望 false 收到 true）、「反問選擇送出後切換對象…反問可重選」紅（`data-state` 期望 default 收到 picking） |
| M-R9 | `submit` 內還原 `onFailure(null)`（以型別斷言呼叫，使建置通過） | `object-picker.spec.ts` **32 passed / 1 failed**：「重試建立時播報區不在兩次失敗之間退回清單狀態」紅（期間播報區出現「已載入 1 個專案」） |

兩項還原後三檔 sha256 皆與基線相同；重建後上表三個 spec 合計 120 passed。

**未做**：`tcms_validate.py`、`validate_env_contract.py`、`check:ws-types` 本輪未跑（未改契約與環境設定）；`entry-page-live.spec.ts` 未跑。
