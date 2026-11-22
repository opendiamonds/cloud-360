## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-08 | Fixed | Minor | frontend/src/components/Sidebar.tsx 第 248 行現為 nav 且帶 aria-label="我的記憶"（git diff --numstat 為 2 1，只加註解與屬性）。frontend/tests/e2e/sidebar-landmarks.spec.ts 第 70 行的 memory nav landmark is named 以 getByRole navigation 加名稱斷言鎖住。補充：該 spec 為未追蹤檔，Sidebar 改動亦未提交，必須與 brain-infra 同批提交，否則鎖定不存在。 |
| R-09 | Fixed | Minor | merge-blockers.md 第 35 列已逐項列出 (a) 焦點條件化、(b) 列暫接焦點、(c) aria-label、(d) 結清 L4 至 L6 的登錄，處置欄行號與現檔逐一核對相符（MemoryZone 87 與 269、MemoryItem 81 至 88、119、122、memory-page.spec.ts 1003、1028、1062、1096、sidebar-landmarks.spec.ts 70）。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|
| Minor | frontend/tests/e2e/memory-page.spec.ts > MB35 四案；frontend/src/components/memory/MemoryItem.tsx 第 106 至 112 行 | 第 35 列要求的失敗路徑焦點（刪除失敗後焦點回到刪除鍵，由 restoreFocusToEntry 負責）沒有任何斷言。既有的 404 仍列出、重讀失敗兩案只檢查文字與列保留，不檢查焦點。若把失敗分支的 restoreFocusToEntry 拿掉，li 的 tabIndex 隨 deleting 結束而移除，焦點會落到 body，四個新案與既有案全部仍綠。另外，失敗時 restoreFocusToEntry 無條件把焦點拉回刪除鍵，即使使用者在 DELETE 在途時已移到別處，這與 (a) 的不搶焦點原則不一致，但屬既有行為且不在第 35 列文字內。 | 在既有的 404 重讀失敗案加一行 memory-item-1-delete 為焦點的斷言，或新增一案；是否也比照不搶焦點可另列為後續。 |
| Minor | frontend/src/components/memory/MemoryZone.tsx 第 88 行 | focusIsOnRowOrLost 的 body 或 null 分支沒有獨立測試。若只刪掉該分支而保留 MemoryItem 的列焦點，a1 與 b 仍綠（焦點在 li 內，由 closest 判定成立）。使用者在 DELETE 在途時點空白處使焦點落到 body，完成後是否仍移到區標題，目前無案例守住。 | 補一案：DELETE 延遲期間 blur 目前焦點元素，放行後斷言區標題取得焦點。 |
| Minor | frontend/tests/e2e/a11y.spec.ts 第 77 行 | 註解仍寫我的記憶的 nav 無 aria-label，已與 Sidebar 第 248 行不符（code-summary 第八節已自記）。 | 由 a11y-gate 或 brain-infra 順手更正註解。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 讀碼推演（未執行任何測試或建置指令） | 時序成立：handleRemoved 內 setItems 只排程，React 19 非同步回呼內不同步 commit，故 focusIsOnRowOrLost 呼叫時被刪列仍在 DOM；列 li 在 deleting 時 tabIndex 為 -1 且 closest li 判定歸到該列。 | (a) 與 (b) 的判定邏輯成立；情節區分支未改（只動 !isEpisodic 區塊）。 |
| 突變推演 | 無條件移焦點使 a2、a3 紅；拿掉 row.focus 使 b 紅；從不移焦點使 a1、b 紅。 | 與 code-summary 的三個突變結果一致；上述兩個 Minor 為突變覆蓋缺口。 |
| 規格註解與案名 | 四案皆有 @purpose、@given、@step、@pass、@story、@api、@ui；git diff -U0 對 memory-page.spec.ts 無任何被刪除行；總案數 22，其中既有 18。 | 既有案名未改，TCMS 對應不會孤兒化。 |
| 行號與宣稱核對 | code-summary、traceability MB-35、merge-blockers 第 35 列引用的行號與檔案現況逐一相符。 | 宣稱與程式一致。 |

### Summary

第 35 列 (a)(b) 的焦點邏輯與時序成立，情節區分支未被破壞，四個新 e2e 案能對無條件移焦點與拿掉列焦點兩種突變變紅，紀錄與行號如實；僅有失敗路徑焦點與落到 body 分支未被測試守住兩項 Minor，以及 R-08 的鎖定檔尚未提交的提醒。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-00 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/code-generation/code-generation-plan.md > review findings table | The reviewer's findings table could not be read, so its rows are not listed here: aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/code-generation/code-generation-plan.md: findings table header declares ID, Severity, Location, Finding, Status. Expected columns: ID, Severity, Location, Finding, Required action, Status. Missing: Required action | Address the reviewer's findings as written below this table. | Resolved (reviewer) |
| R-01 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/code-generation/code-summary.md > 六、偏離與未驗項 第 2 列 | 該列寫「`unit-test-instructions.md` 為已核可內容，未改」，但工作樹 diff 顯示該檔新增了 §四之三（+12 行）。同一節還把案例編為 E11–E13，spec 註解與 traceability.json 卻用 `MB6-E11`–`MB6-E13`，同一組案例在兩份文件叫不同名字。 | 更正該列的陳述（檔案有改，改了什麼），並讓 unit-test-instructions §四之三 的案例標號與 spec／traceability 一致（改用 `MB6-` 前綴，或在表內註明對照）。 | Resolved (reviewer) |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/code-generation/code-summary.md > 五、已接受風險；frontend/src/components/memory/MemoryZone.tsx > deleteRecord 註解 | 風險描述只涵蓋「更早的記憶被刪除使該則滑到前一頁」。實作其實是以 id 比對（`data.some(r => r.memory_id === memoryId)`），所以誤判的條件是該則離開了被重讀的那一頁。另一個方向沒寫：情節區在兩次請求之間若有 2 筆以上的新記憶寫入（agent 會寫入），該則會被推到探測列 limit=21 以外，同樣被判為已刪除。誤判仍需「404 本身是假的」同時發生，機率低，嚴重度如實，但描述不完整。 | 把「往後位移超過探測列」補進已接受風險；選擇性的低成本強化是情節區重讀未命中時再讀相鄰頁（或從 offset 0 重讀）再下結論。 | Resolved (reviewer) |
| R-03 | Minor | frontend/tests/e2e/memory-page.spec.ts > MB6-E11–E13；code-summary.md > 六 第 1 列 | 偏離說明「以按下確認那一刻的頁重讀，而非 404 到達時的頁」是刻意的設計選擇，但三支新案例都沒有覆蓋「DELETE 在途時翻頁」。若日後把 rowPage 改回讀目前頁，三案都仍綠。 | 加一個 e2e（DELETE 延遲、期間翻頁、404 後斷言重讀的 offset 為原頁），或在偏離說明中明記此選擇未被測試鎖住。 | Resolved (reviewer) |
| R-04 | Minor | frontend/tests/e2e/memory-page.spec.ts > MB6-E13 的 `@api GET ... -> 500` | 500 不在 OpenAPI 宣告集合，產生 tcms_validate WARN。保留 WARN 並說明理由是可接受的處置；但確認重讀失敗用 `route.abort()` 模擬網路失敗可以完全避開這個 WARN，且前端的 `catch` 路徑相同。 | 可選：改用連線失敗模擬，或維持現狀並在 stage 閘門上逐項呈現此 WARN。 | Resolved (reviewer) |
| R-05 | Minor | code-summary.md > 六 第 5 列 | §二、§六 兩處已被其他單元的修正推翻（`HierarchyFacade` 缺口已修、`MemoryForbidden` 不再降級），但只在表內註記「原文不回改」，文件頭沒有提示，讀者從上往下會先讀到過期內容。本單元的 code-summary 是本單元自己的產出，不是已核可上游。 | 在過期段落旁加一行就地標註（保留原文、標明已被推翻及依據），或更新該段。 | Resolved (reviewer) |
| R-06 | Minor | frontend/src/components/memory/MemoryZone.tsx > handleRemoved 的語意／程序區分支（`headingRef.current?.focus()`） | 語意與程序區的刪除完成後，不論焦點目前在哪裡，一律把焦點拉回區標題。情節區已有「只在被刪列就在畫面上那一頁才搬焦點」的判斷，這兩區沒有。若使用者在第一則的 DELETE 在途時，已對另一則按下刪除並停在它的確認鍵上，第一則完成時焦點會被搶走。DELETE 在途時間通常很短，影響小。 | 語意與程序區也只在焦點仍落在該列內或落在 `body` 時才搬焦點，或在 code-summary 明記這是已知取捨。 | Resolved (reviewer) |
| R-07 | Minor | frontend/src/components/memory/MemoryItem.tsx > handleConfirm 與 DeleteConfirmRow 卸載 | 按下確認鍵後，`itemState` 立即變成 `deleting`，確認列卸載，刪除入口重新出現但是 `disabled`。這段期間焦點落在 `body`。成功時由區塊移到區標題，失敗時回到刪除鍵，所以最終落點都正確，中間只有一小段焦點遺失。這是 code-summary 列出的候選 (1)，我判為 Minor，不是 Major。 | 可在 `deleting` 期間讓列本身（`li`）暫時接焦點，或在 code-summary 記為已知。不阻擋。 | Resolved (reviewer) |
| R-08 | Minor | frontend/src/components/Sidebar.tsx > 「我的記憶」的 `<nav>`（約 :247） | 這個 `<nav>` 沒有 `aria-label`，而「入口」「專案」的有。同一側欄裡另有兩個既有的無標籤 `<nav>`（架構與成本群組）。axe 的 `landmark-unique` 屬於 best-practice 規則，`a11y.spec.ts` 的 WCAG 標籤集合不執行它，所以閘門不會紅。這是 code-summary 列出的候選 (2)，我判為 Minor，不是 Major。 | 為此 `<nav>` 加上 `aria-label="我的記憶"`，成本為零。 | Unresolved |
| R-09 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/code-generation/code-summary.md > 共用檔異動後的重新驗證與補審 > 四 | 限制 L4 至 L6 標示為需新增，但 merge-blockers.md 第 6 列只含 (a) 至 (d)，不含焦點兩項與 aria-label 項；在 conductor 併入前，這三項只存在於本單元紀錄中 | 由 conductor 把 L4 至 L6 併入 merge-blockers.md，或直接為 Sidebar 加上 aria-label 並於下輪處理 L4、L5 | New |

> R-08 Not re-checked this round

> R-09 Not re-checked this round
