## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-24T14:15:58Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | frontend/src/components/brain/ObjectPicker.tsx > onSearch 與 startBackfill（約第 188–205 行） | 補抓只在 onSearch 內判斷 `projectsState.status === 'loaded'` 時才起。搜尋框在掛載時即取得焦點且於載入中就已渲染（資料 loading 態仍顯示輸入框），使用者開啟後立即輸入、專案清單尚未回來時，`startBackfill` 不會執行，`backfillStartedRef` 仍為 false；清單載入完成後沒有任何 effect 或回呼以目前的 query 補觸發。結果：除目前所在專案外，所有群組的系統名都不在比對範圍，畫面可能直接顯示「沒有符合的對象」（`noMatch` 在 `backfillBusy` 為 false 時成立），要等使用者再多打一個字才會補抓。這違反 N-02 第 3 點（第一次輸入非空字元即補抓）並把部分比對當成完整結果呈現。e2e 全部先等清單載入、再輸入，沒有任何案例涵蓋此時序，16 道突變也不涵蓋。 | 讓補抓的觸發與「清單已載入」和「query 非空」兩個條件的成立時點對齊，而非只掛在輸入事件上，例如在專案清單 `.then` 內、`setProjectsState` 之後，若 query 非空且尚未補抓即呼叫補抓（需讀 ref 或最新 query）。新增 e2e：以 `projectsHook` 延遲專案清單、清單回來前輸入某個只存在於系統名的字串，斷言不需再輸入即補抓並命中；補一道突變（移除該觸發）並記入 code-summary。 | Resolved (reviewer) |
| R-02 | Minor | frontend/tests/e2e/object-picker.spec.ts（整檔）；ObjectPicker.tsx 卸載清理與 mousedown 監聽 | 兩項已實作的行為沒有任何會紅的測試：(a) BR12.4／OPN-24「關閉即取消補抓佇列」——沒有案例在補抓進行中關閉選單並斷言之後不再有系統請求，移除 `holder.queue?.cancel()` 所有測試仍綠，而這正是 fanoutQueue 檔頭點名的連線池壓力來源；(b) F-06「點選單外等同取消」——spec 內無 `page.mouse.click` 或類似操作，移除整個 mousedown effect 仍全綠。突變清單 M1–M16 同樣沒有對應條目。 | 補兩個 e2e 與對應突變：補抓中按 Escape 後等待並斷言系統請求數不再增加；點選單外的頁面區域後選單關閉、焦點不被留在已卸載的節點。結果記入 code-summary 的突變表。 | Resolved (reviewer) |
| R-03 | Minor | frontend/tests/e2e/object-picker.spec.ts > 「關閉後晚到的舊回應永不出現」；code-generation/traceability.json > BR12.4、OPN-02 | 此案無法對守衛失效變紅：元件卸載後 React 不會把 setState 渲染出來，`__sawOld` 的 MutationObserver 與「新名稱」斷言在移除 `mountedRef`／`cancelled` 檢查時仍然成立，案內自己也承認不能用主控台警告判定。它實際只驗證「關閉期間沒有新請求」。traceability 卻把它列為 BR12.4 與 OPN-02 的證據（status OK）。 | 把該案的 `@purpose` 與 traceability note 改成它實際能證明的內容（關閉期間零新請求），並把 BR12.4 的取消扇出證據改指向 R-02 補上的案例；或誠實標為由程式碼審查承載，不要以恆綠斷言當證據。 | Resolved (reviewer) |
| R-04 | Minor | frontend/src/components/brain/ObjectPicker.tsx > 根節點與 onKeyDown；ContextBar.tsx > section tabIndex={-1} | 鍵盤處理只掛在 dialog 根節點的 `onKeyDown`，根節點本身不可聚焦。使用者點到選單內的標題或留白時，焦點會落到祖先 `<section tabIndex=-1>`（dialog 的父層）或 body，之後 Escape 與 Tab 事件都不經過 dialog，Escape 失效、焦點陷阱失效（onKeyDown 內 `!root.contains(activeEl)` 分支因此永遠到不了）。BR15.2 要求 Escape 關閉與焦點陷阱；現有鍵盤案只走純鍵盤路徑。 | 讓 dialog 根節點 `tabIndex={-1}` 並在 mousedown 落於選單內非控件區域時把焦點收回根節點，或在選單開啟期間改掛 document 層級的 keydown；補一個 e2e：點標題後按 Escape 仍關閉。 | Resolved (reviewer) |
| R-05 | Minor | frontend/src/components/brain/ContextBar.tsx > togglePicker、PICKER_WIDTH；code-summary.md > 第八節偏離 1 | `fixed` 定位在點擊當下量測一次：頁面或 `/assessment` 的內層捲動容器（`h-full overflow-y-auto`）捲動後選單與脈絡列脫離，視窗縮放或旋轉不重算，`maxHeight` 的下限 240 在鈕靠近視窗底部時會使選單超出視窗且無法捲到；`PICKER_WIDTH = 384` 與 ObjectPicker 的 `md:w-96` 是同一事實的兩份手寫副本，只靠註解約束。偏離已在 code-summary 揭露，但未列入關卡事項，使用者核可時看不到它是已知殘留。 | 開啟期間監聽 resize 與捲動並關閉選單（最小成本，不需重定位邏輯），或改以脈絡列容器為定位上下文；寬度改由單一常數同時產生 style 與 class，或在 PickerPlacement 內傳入。若維持現狀，至少把此殘留加進關卡事項。 | Resolved (reviewer) |
| R-06 | Minor | frontend/src/components/brain/ObjectPicker.tsx > liveText；ObjectPickerCreateForm.tsx > onFailure | 選單內播報區沿用 D-05 已發現的「相同字串不改 state 就不重唸」問題但只修了斷線那一處：同一種建立錯誤連續發生兩次（例如連續兩次 409）時 `formFailure` 值不變，播報區不重唸；`switchError` 在下一次選取前一直存在，會遮蔽 `listText` 的結果數播報（`switchError ?? formFailure ?? listText`）。現有案例用的是不同文案，測不到。 | 送出新一輪建立時先清空 `formFailure`（與 `setError(null)` 同時），再寫入；`switchError` 在使用者再次輸入或展開時清除，並補一個連續兩次同樣失敗仍被播報的 e2e。 | Resolved (reviewer) |
| R-07 | Minor | frontend/src/components/brain/ObjectPicker.tsx > retryProjects 與 startBackfill 的 allSettled 收尾 | 專案清單重試時舊佇列被取消，但其 `Promise.allSettled(...).then(() => setBackfillBusy(false))` 仍會在已起跑的舊任務完成後執行，會把之後新一輪補抓的忙碌旗標提前清掉。目前重試鈕只在首次載入失敗的 error 態出現，補抓尚未發生過，所以這條路徑今天走不到；一旦日後有其他途徑重跑掛載流程就會成為真缺陷。 | 以每一輪補抓的世代編號或佇列物件比對（`if (queueHolder.current.queue === queue)`）再清旗標。 | Resolved (reviewer) |
| R-08 | Minor | frontend/src/brain/useBrainConnection.ts > setWorkTarget（第 414–417 行）與 error 分支的 `lastSentRef` 判定（第 231–245 行） | 選單送出 `set_work_target` 成功時會把 `lastSentRef` 重設為 `NOTHING_SENT`（第 416 行）。若使用者剛送出一句 `user_message`、尚未收到任何輪次訊息，就在選單切換了對象，之後伺服器以非輪次錯誤（例如頻率超限）拒絕那句原句，前端已無法判定被拒的是誰：只會插入系統提示，原句不會標為「這句沒有送達」，`awaitingReply` 也不會解除。`[EP-R2]` 的「最後送出的請求」判定被選單的切換動作蓋掉。`set_work_target` 自身被拒時則只出系統提示（對話區），選單此時已關閉，選單內的 `switchError` 與對話區的提示不會重複播報，這一點沒有問題。 | 這個設計可以接受：窗口只有伺服器回覆前的短暫期間，且切換本身有被拒時的系統提示。若要消除，`setWorkTarget` 不要重設 `lastSentRef`（它不屬輪次請求，不應影響原句的受理判定），並補一個 e2e：送出原句後立刻切換對象，再回非輪次錯誤，斷言原句標為未送達。 | New |
| R-09 | Minor | frontend/src/components/brain/ObjectPicker.tsx > liveText（第 375 行）；ObjectPickerCreateForm.tsx > submit 的 `onFailure(null)` | 為了讓相同錯誤能重唸，每輪送出先把 `formFailure` 清成 `null`，此時 `liveText` 會退回 `listText`（例如「已載入 N 個專案」）。播報區因此在每次送出時先唸一次清單狀態，再唸錯誤。螢幕報讀器使用者每次重試都會聽到與建立無關的一句雜訊。e2e 只計錯誤文案累計次數，測不到這句雜訊。 | 清空 `formFailure` 時不要退回 `listText`：例如送出期間讓 `liveText` 保持空字串（用「建立中」狀態旗標），或把重唸機制改為與 `useBrainConnection` 的 `announceFresh` 相同的零寬字元做法。 | New |

> R-01 Reviewer note: `ObjectPicker.tsx` 第 218 行：專案清單 `.then` 內，若 `!backfillStartedRef.current` 且 `normalize(queryRef.current) !== ''` 即呼叫 `startBackfill(projects)`；`onSearch`（第 244–249 行）同步寫 `queryRef`。兩個條件誰後成立，補抓就在那一刻起。目前所在專案的 `ensureSystems` 先於補抓執行，登記簿擋住重抓。spec 第 1164 行有對應案例，corrections 記有突變 M17 紅燈。

> R-02 Reviewer note: spec 已新增「補抓進行中關閉後不再發出系統請求」（第 1205 行，M18）與「點選單外關閉且焦點不留在已卸載節點」（第 1236 行，M19）。`mousedown` 監聽與 `holder.queue?.cancel()` 現在都有會變紅的案例。

> R-03 Reviewer note: 「關閉後晚到的舊回應永不出現」的規格註解已改為只宣稱關閉期間零新請求。`traceability.json` 的 BR12.4 改指 M18 案例；OPN-02 明寫「守衛由程式碼審查承載」，不再以恆綠案例為證據。`mountedRef`／`cancelled` 守衛仍無自動化證據，但已如實揭露，沒有遮掩。

> R-04 Reviewer note: 根節點 `tabIndex={-1}`（第 450 行）、`onRootMouseDown`（第 422–429 行）、Tab 陷阱把焦點在根節點視同不在任何控件上（第 397 行）。spec 第 1263 行覆蓋「點標題後 Escape」，M20 紅燈。單獨移除 `onRootMouseDown` 不會變紅，corrections 已誠實記載。

> R-05 Reviewer note: 開啟期間錨點因捲動移位或視窗寬度改變即關閉（第 325–344 行）；寬度只在 `objectPickerModel.ts` 的 `PICKER_WIDTH_PX` 一處定義，由 CSS 變數同時供 class 與 `ContextBar` 使用。殘留的 `maxHeight` 下限 240 已列為關卡事項 G-7。

> R-06 Reviewer note: `ObjectPickerCreateForm.submit` 每輪先 `onFailure(null)`；`onSearch` 與 `toggleExpand` 清 `switchError`；spec 第 1339 行覆蓋連續兩次相同失敗，M22 紅燈。修正帶來一個小副作用，見下方新發現。

> R-07 Reviewer note: 補抓收尾改為 `queueHolder.current.queue === queue` 才清忙碌旗標（第 195–197 行），`retryProjects` 先把 holder 設為 null。這條路徑今天走不到，由程式碼審查承載，與原審查結論一致。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 未執行任何建置、Playwright、vite（依指示避免寫入 repo） | N/A | 依 corrections §九 所載的 59 passed、lint 0 errors 與 `validate_repo_contract.py` 通過，僅以文件為準；我只核對了程式碼、spec 測試名稱與數量、`traceability.json` 內容，未獨立重跑。 |

### Summary

七項前次發現與 R-08／R-09 的修正都在程式碼中落實，並有對應案例與突變證據；僅剩兩項 Minor（選單切換蓋掉原句拒絕判定、重唸機制的雜訊播報），且 `mountedRef` 守衛無自動化證據與 G-7 的 `maxHeight` 殘留都已如實揭露，不構成阻擋。
