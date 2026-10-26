## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
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
| R-08 | Minor | frontend/src/brain/useBrainConnection.ts > setWorkTarget（第 414–417 行）與 error 分支的 `lastSentRef` 判定（第 231–245 行） | 選單送出 `set_work_target` 成功時會把 `lastSentRef` 重設為 `NOTHING_SENT`（第 416 行）。若使用者剛送出一句 `user_message`、尚未收到任何輪次訊息，就在選單切換了對象，之後伺服器以非輪次錯誤（例如頻率超限）拒絕那句原句，前端已無法判定被拒的是誰：只會插入系統提示，原句不會標為「這句沒有送達」，`awaitingReply` 也不會解除。`[EP-R2]` 的「最後送出的請求」判定被選單的切換動作蓋掉。`set_work_target` 自身被拒時則只出系統提示（對話區），選單此時已關閉，選單內的 `switchError` 與對話區的提示不會重複播報，這一點沒有問題。 | 這個設計可以接受：窗口只有伺服器回覆前的短暫期間，且切換本身有被拒時的系統提示。若要消除，`setWorkTarget` 不要重設 `lastSentRef`（它不屬輪次請求，不應影響原句的受理判定），並補一個 e2e：送出原句後立刻切換對象，再回非輪次錯誤，斷言原句標為未送達。 | Resolved (reviewer) |
| R-09 | Minor | frontend/src/components/brain/ObjectPicker.tsx > liveText（第 375 行）；ObjectPickerCreateForm.tsx > submit 的 `onFailure(null)` | 為了讓相同錯誤能重唸，每輪送出先把 `formFailure` 清成 `null`，此時 `liveText` 會退回 `listText`（例如「已載入 N 個專案」）。播報區因此在每次送出時先唸一次清單狀態，再唸錯誤。螢幕報讀器使用者每次重試都會聽到與建立無關的一句雜訊。e2e 只計錯誤文案累計次數，測不到這句雜訊。 | 清空 `formFailure` 時不要退回 `listText`：例如送出期間讓 `liveText` 保持空字串（用「建立中」狀態旗標），或把重唸機制改為與 `useBrainConnection` 的 `announceFresh` 相同的零寬字元做法。 | Resolved (reviewer) |
| R-10 | Minor | frontend/src/brain/useBrainConnection.ts > afterNonTurnSend 與 error 分支的 undeliveredUserId 判定 | R-08 的修法保留待決的 user_message 標記，但 set_work_target 自身被閘道拒絕時（閘道對它只回 turnId 為 null 的單一錯誤）也會落到同一分支。若原句已被受理、尚未收到任何該輪訊息（等第一個 token 的數秒內），這則錯誤會被誤算成原句被拒：原句被標為「這句沒有送達」並顯示重試鈕、awaitingReply 被解除，之後該輪回覆仍會到達，使用者按重試會造成重複送出。這是原本重設標記的缺陷的對稱面，沒有測試覆蓋。 | 在 entry-page.spec.ts 補一案：送出原句、切換對象、閘道只回 set_work_target 的非輪次錯誤，並記錄選擇的取捨。若要消除，需要請求對應機制（例如帶請求編號的錯誤）；若維持現狀，在 code-summary 登記為已知取捨並寫明誤判情境。 | New |
| R-11 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/object-picker-ui/code-generation/source-manifest.json > writes | 本單元的 R-08 修正與守護測試落在 frontend/src/brain/useBrainConnection.ts 與 frontend/tests/e2e/entry-page.spec.ts，這兩個檔不在 manifest 的 writes 清單，traceability.json 也未提到 useBrainConnection。兩檔目前是未提交狀態，並與其他單元的變更（含合併前必修第 2 項的 error.turnId 可為 null）混在同一份差異裡，code-summary 自己寫明「兩單元合併時不可拆開」。 | 把這兩檔加入 manifest 與 traceability 的 R-08 追溯，並在合併前必修清單登記此耦合，確保 R-08 的修正與測試不會隨 entry-page-ui 的變更被拆開或遺漏。 | New |
| R-12 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/object-picker-ui/code-generation/code-generation-plan.md > Step 10、Step 12 未勾；code-summary.md > 過期數字 | 計畫 15 步勾 13 步。Step 10 的 entry-page-live.spec.ts 本機無法跑（需 docker-compose.test.yml），Step 12 的 ws-contract 比較基準因其他單元變更而不同、git diff --stat 的零變更檢查無法照字面驗證。兩項皆有如實說明，但未指派誰在何時確認。另外 Step 15 與 code-summary-corrections.md 仍寫 32 案或 59 passed，實測為 33 案（本次 object-picker 加 entry-page 共 93 案全過）。 | 把 Step 10 指派給 CI 的 ui-regression 並在合併前必修清單登記，Step 12 改寫成可驗證的條件（例如只比對本單元 manifest 檔案），並更正 32 與 59 這兩個過期數字。 | New |

> R-08 Reviewer note: useBrainConnection.ts 新增 afterNonTurnSend（第 84-86 行），setWorkTarget、correctWorkItem、setSharingMode 改用它，待決的 user_message 或反問選擇不再被切換動作蓋掉。守護測試 entry-page.spec.ts 第 2090、2124 行在正式建置（vite preview）實跑通過。副作用見新發現第一項。

> R-09 Reviewer note: 建立表單 submit 已不再清空 formFailure；ObjectPicker.tsx 的 reportFormFailure 以零寬空白讓相同錯誤可重唸，播報區不在兩次失敗之間退回清單狀態。object-picker.spec.ts 第 1342、1371 行兩案實跑通過。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| eslint（src/components/brain、src/brain、兩支 spec） | 無輸出（0 errors） | 通過，U16 的 lint 約束區塊未被觸犯 |
| tsc -p tsconfig.app.json --noEmit | 通過 | 型別檢查乾淨 |
| vite build 至暫存目錄後 vite preview 跑 Playwright（object-picker 33 案加 entry-page 60 案） | 93 passed | R-08、R-09 的守護測試在正式建置下實跑為綠 |

### Summary

R-08 與 R-09 的修正內容正確且有測試守護，lint、型別與 93 個 e2e 全過。剩餘三項皆為 Minor：R-08 修法對 set_work_target 自身被拒的對稱誤判、manifest 與追溯未涵蓋跨單元檔案，以及兩個未勾步驟與過期數字。
