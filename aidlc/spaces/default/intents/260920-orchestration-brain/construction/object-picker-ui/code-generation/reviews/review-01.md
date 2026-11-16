## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

程式整體貼近三份更正附錄：冪等登記簿（D-01）、`useRef` 單發鎖（OPN-03／D-02）、衍生 `identity`（D-04）、依前值調整 state 與播報分工（D-05／F-04）、id 字串邊界集中於 `objectPickerModel.ts`（OPN-21）、不本地改脈絡列（NFR2.160）、lint 區塊保住 `WS_SUBPROTOCOL_RESTRICTIONS`，`ContextBar.tsx` 的五態判定與名稱節點未被動到，XSS／正規表示式／儲存／直接建立的面向沒有找到破口。唯一會讓功能實際出錯的是搜尋補抓的觸發條件：使用者在專案清單回來之前輸入，補抓永遠不會發生，畫面把「只比對了部分資料」的結果當成完整結果呈現（R-01，Major）。其餘為測試縫隙與無障礙／定位的 Minor。本審查依規定只用唯讀指令，未重跑 lint、tsc 與 Playwright；code-summary 所列的實跑結果以其自述為準，本審查只就原始碼與測試文字推演。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | frontend/src/components/brain/ObjectPicker.tsx > onSearch 與 startBackfill（約第 188–205 行） | 補抓只在 onSearch 內判斷 `projectsState.status === 'loaded'` 時才起。搜尋框在掛載時即取得焦點且於載入中就已渲染（資料 loading 態仍顯示輸入框），使用者開啟後立即輸入、專案清單尚未回來時，`startBackfill` 不會執行，`backfillStartedRef` 仍為 false；清單載入完成後沒有任何 effect 或回呼以目前的 query 補觸發。結果：除目前所在專案外，所有群組的系統名都不在比對範圍，畫面可能直接顯示「沒有符合的對象」（`noMatch` 在 `backfillBusy` 為 false 時成立），要等使用者再多打一個字才會補抓。這違反 N-02 第 3 點（第一次輸入非空字元即補抓）並把部分比對當成完整結果呈現。e2e 全部先等清單載入、再輸入，沒有任何案例涵蓋此時序，16 道突變也不涵蓋。 | 讓補抓的觸發與「清單已載入」和「query 非空」兩個條件的成立時點對齊，而非只掛在輸入事件上，例如在專案清單 `.then` 內、`setProjectsState` 之後，若 query 非空且尚未補抓即呼叫補抓（需讀 ref 或最新 query）。新增 e2e：以 `projectsHook` 延遲專案清單、清單回來前輸入某個只存在於系統名的字串，斷言不需再輸入即補抓並命中；補一道突變（移除該觸發）並記入 code-summary。 | New |
| R-02 | Minor | frontend/tests/e2e/object-picker.spec.ts（整檔）；ObjectPicker.tsx 卸載清理與 mousedown 監聽 | 兩項已實作的行為沒有任何會紅的測試：(a) BR12.4／OPN-24「關閉即取消補抓佇列」——沒有案例在補抓進行中關閉選單並斷言之後不再有系統請求，移除 `holder.queue?.cancel()` 所有測試仍綠，而這正是 fanoutQueue 檔頭點名的連線池壓力來源；(b) F-06「點選單外等同取消」——spec 內無 `page.mouse.click` 或類似操作，移除整個 mousedown effect 仍全綠。突變清單 M1–M16 同樣沒有對應條目。 | 補兩個 e2e 與對應突變：補抓中按 Escape 後等待並斷言系統請求數不再增加；點選單外的頁面區域後選單關閉、焦點不被留在已卸載的節點。結果記入 code-summary 的突變表。 | New |
| R-03 | Minor | frontend/tests/e2e/object-picker.spec.ts > 「關閉後晚到的舊回應永不出現」；code-generation/traceability.json > BR12.4、OPN-02 | 此案無法對守衛失效變紅：元件卸載後 React 不會把 setState 渲染出來，`__sawOld` 的 MutationObserver 與「新名稱」斷言在移除 `mountedRef`／`cancelled` 檢查時仍然成立，案內自己也承認不能用主控台警告判定。它實際只驗證「關閉期間沒有新請求」。traceability 卻把它列為 BR12.4 與 OPN-02 的證據（status OK）。 | 把該案的 `@purpose` 與 traceability note 改成它實際能證明的內容（關閉期間零新請求），並把 BR12.4 的取消扇出證據改指向 R-02 補上的案例；或誠實標為由程式碼審查承載，不要以恆綠斷言當證據。 | New |
| R-04 | Minor | frontend/src/components/brain/ObjectPicker.tsx > 根節點與 onKeyDown；ContextBar.tsx > section tabIndex={-1} | 鍵盤處理只掛在 dialog 根節點的 `onKeyDown`，根節點本身不可聚焦。使用者點到選單內的標題或留白時，焦點會落到祖先 `<section tabIndex=-1>`（dialog 的父層）或 body，之後 Escape 與 Tab 事件都不經過 dialog，Escape 失效、焦點陷阱失效（onKeyDown 內 `!root.contains(activeEl)` 分支因此永遠到不了）。BR15.2 要求 Escape 關閉與焦點陷阱；現有鍵盤案只走純鍵盤路徑。 | 讓 dialog 根節點 `tabIndex={-1}` 並在 mousedown 落於選單內非控件區域時把焦點收回根節點，或在選單開啟期間改掛 document 層級的 keydown；補一個 e2e：點標題後按 Escape 仍關閉。 | New |
| R-05 | Minor | frontend/src/components/brain/ContextBar.tsx > togglePicker、PICKER_WIDTH；code-summary.md > 第八節偏離 1 | `fixed` 定位在點擊當下量測一次：頁面或 `/assessment` 的內層捲動容器（`h-full overflow-y-auto`）捲動後選單與脈絡列脫離，視窗縮放或旋轉不重算，`maxHeight` 的下限 240 在鈕靠近視窗底部時會使選單超出視窗且無法捲到；`PICKER_WIDTH = 384` 與 ObjectPicker 的 `md:w-96` 是同一事實的兩份手寫副本，只靠註解約束。偏離已在 code-summary 揭露，但未列入關卡事項，使用者核可時看不到它是已知殘留。 | 開啟期間監聽 resize 與捲動並關閉選單（最小成本，不需重定位邏輯），或改以脈絡列容器為定位上下文；寬度改由單一常數同時產生 style 與 class，或在 PickerPlacement 內傳入。若維持現狀，至少把此殘留加進關卡事項。 | New |
| R-06 | Minor | frontend/src/components/brain/ObjectPicker.tsx > liveText；ObjectPickerCreateForm.tsx > onFailure | 選單內播報區沿用 D-05 已發現的「相同字串不改 state 就不重唸」問題但只修了斷線那一處：同一種建立錯誤連續發生兩次（例如連續兩次 409）時 `formFailure` 值不變，播報區不重唸；`switchError` 在下一次選取前一直存在，會遮蔽 `listText` 的結果數播報（`switchError ?? formFailure ?? listText`）。現有案例用的是不同文案，測不到。 | 送出新一輪建立時先清空 `formFailure`（與 `setError(null)` 同時），再寫入；`switchError` 在使用者再次輸入或展開時清除，並補一個連續兩次同樣失敗仍被播報的 e2e。 | New |
| R-07 | Minor | frontend/src/components/brain/ObjectPicker.tsx > retryProjects 與 startBackfill 的 allSettled 收尾 | 專案清單重試時舊佇列被取消，但其 `Promise.allSettled(...).then(() => setBackfillBusy(false))` 仍會在已起跑的舊任務完成後執行，會把之後新一輪補抓的忙碌旗標提前清掉。目前重試鈕只在首次載入失敗的 error 態出現，補抓尚未發生過，所以這條路徑今天走不到；一旦日後有其他途徑重跑掛載流程就會成為真缺陷。 | 以每一輪補抓的世代編號或佇列物件比對（`if (queueHolder.current.queue === queue)`）再清旗標。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| traceability.json 結構檢查（唯讀腳本：upstream_ids 與 coverage 的 id 集合、OK 項目的 target 是否為存在的單一檔案） | 50 條 id 與 coverage 完全一致；所有 OK 項目的 target 都是存在的單一檔案；AC9.2.3 與 OPN-25 為 Deferred 且有理由 | 結構成立。內容層面 BR12.4／OPN-02 的證據見 R-03；NFR8.160 與 OPN-22 的 target 指向「本單元未修改」的負面主張，不是承載者，只是比較基準，已由 code-summary 第七節的雜湊對照補強，不另列發現 |
| 原始碼 grep（`console.`、儲存、`innerHTML`、`RegExp`、`dangerouslySetInnerHTML`，限選單檔案集合的非註解行） | 0 命中 | 與 lint 區塊的目標一致；`.match()`／`.search()` 以字串引數會隱含編譯成正規表示式，lint 規則未涵蓋但目前程式未使用，屬已記載的「擋無心之失」範圍 |
| eslint.config.js 差異閱讀 | 末端區塊展開 `WS_SUBPROTOCOL_RESTRICTIONS`；新增六條選擇器含 `window.<storage>`；`no-restricted-imports` 只比對兩種相對路徑 | D-06 與 N-03 的承諾成立；路徑別名繞過為已記載殘留 |
| 未執行項 | lint、tsc、Playwright、突變重放均未執行（審查規則禁止寫檔與產生快取） | code-summary 第五、六節的綠燈與紅燈紀錄為作者自述，本審查未獨立重現 |

### 對提示的逐項回應

1. 附錄對照：D-01（同步 ref 登記簿、工作執行時查登記簿）、OPN-03（`submittingRef` 在呼叫前同步設真）、D-04（衍生 identity）、D-05（依前值調整 state、`announce('')` 後 `setTimeout`）、N-02（補抓只一次、經 `fanoutQueue` 並行 4）、OPN-21（`String()` 集中於 model）、F-04（開啟中寫選單內播報區、關閉後寫頁面 LiveRegion）、NFR2.160（`pick` 不改脈絡列）皆與程式一致；唯一偏差是 N-02 第 3 點的觸發時點（R-01）。
2. 第八節偏離：偏離 1 見 R-05；偏離 2（M13 改以並行上限斷言承接）合理，但「請求數 31」斷言對 M13 恆綠，只有 ≤4 斷言有效，且依賴第二個字落在補抓進行中的時序；偏離 3（工作在執行時才查登記簿）合理且與 D-01 一致；偏離 5（重試鈕移焦點）合理。
3. 測試強度：列於 R-02、R-03；其餘案例（M1、M2、M8、M9、M11、M12、M14、M15 對應者）的斷言都檢查具體值，未發現只驗存在的恆真斷言。
4. ContextBar：五態判定、`brain-context-name-*`、`brain-context-none`、共享徽章與切換未被改動；`pickerVisible` 衍生值與依前值調整 state 正確；lint 區塊保住 `WS_SUBPROTOCOL_RESTRICTIONS`。
5. 安全：名稱一律文字節點；搜尋為 `includes`；無主控台、無瀏覽器儲存；建立只經 `objectCreateAction`；擁有者判定僅決定是否渲染，伺服器仍是授權點，未被誤當授權。
6. traceability：見驗證表與 R-03。
7. 無障礙：見 R-04、R-06；其餘（aria-modal、aria-labelledby、`aria-expanded`／`aria-controls`、`aria-disabled` 搭配 `aria-describedby`、`aria-current`、roving tabIndex、焦點返還）與規則一致。
