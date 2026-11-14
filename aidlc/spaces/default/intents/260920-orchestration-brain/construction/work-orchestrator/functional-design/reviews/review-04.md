## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本單元的設計主體自洽：狀態機、比對後寫入、孤兒等待復原、停掉前提項依能力分流、ADR-0006 四面向各有落點，規則數 45（8+7+4+1+7+8+5+5）與 traceability 一致。凍結的產出仍帶著前次 review-03 提出但未回寫的兩項 Major（在途存檔收尾不可達、並發復原未限定只有寫入成功者才啟動），以及四項 Minor。已落地的程式（work_orchestrator.py、update_work_item.lua）在這幾處都已修對，因此這些發現的正確一邊是程式，設計文件是過期的。Critical 0、Major 2，依規則判 READY；兩項 Major 建議在契約追認時一併回寫設計，避免下一位讀設計的人照字面實作出已知缺陷。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/work-orchestrator/functional-design/rules.md BR55.7、BR56.6；functional-spec.md 3.2 步驟 3 | 前次 review-03 R-10 已提：設計在同進程下自相矛盾。3.2 步驟 3 規定 correct 取消本行程內該項的背景 task，BR56.6 以 asyncio.wait_for 包住整條執行，逾時同樣取消；兩者都會讓 dispatchStage 為 persisting 時 PUT 的回應處理（寫變更紀錄、更新 sideEffect）不可達，圖被改寫而稽核漏寫，正是 BR55.7 要防的後果（ADR-0006 稽核面）。凍結的產出未修。哪一邊是對的：程式。work_orchestrator.py 的 _execute_architecture 以 asyncio.shield 包住 _finish_persist（約 672 行），收尾自建獨立 client 並有 60 秒 PUT 上限（模組 docstring「在途存檔」一節），_run 的看門迴圈在 deadline 越過時先重讀、已離開處理中者不取消內層（約 559 至 565 行）；也不用 asyncio.wait_for，改以注入的 clock 自行判定 deadlineAt，與設計文字不同但更可測。 | 回寫設計：3.2 步驟 3 與 BR56.6 改為 dispatchStage 為 persisting 時不取消存檔收尾（shield），逾時於此階段同樣不中斷收尾；BR56.6 的 wait_for 改述為以 clock 判定 deadlineAt；BR55.7 補一句與取消的關係 | New |
| R-02 | Major | rules.md BR52.7、BR53.2、BR53.4、BR56.7；functional-spec.md 3.1 步驟 6、3.4 | 前次 review-03 R-11 已提：規則沒有寫出「只有比對後寫入回傳成功者才啟動背景執行與送訊息」。BR56.7、BR53.2 寫「推進為處理中並啟動背景執行」，BR52.7 只規定回傳是否寫入，推進者比對失敗該怎麼辦沒有任何一條說。復原掃描在 dispatch、correct、list_items 三個入口都會跑，U13 在同一工作階段並發呼叫是常態；兩個呼叫讀到同一個孤兒等待項時，依字面兩邊都啟動，同一個 A1 或 A3 請求送出兩次（重複存圖、重複建檢視紀錄）。哪一邊是對的：程式。模組 docstring 明寫「寫入成功者才有副作用（NFR12.13）」，_advance_waiter 把啟動與送訊息放進 then 回呼，經 _advance 只在比對後寫入回 True 時執行（約 467 至 522 行）。 | 回寫設計：BR52.7 或 BR56.7 增通則，任何由狀態轉換觸發的後續動作（啟動、sink 送出、推進等待者、寫記憶）只由該次比對後寫入成功者執行，失敗者重讀後依新狀態處理；BR53.2、BR53.4、BR56.7 的推進句引用此通則 | New |
| R-03 | Minor | rules.md BR56.1、BR56.2、BR55.1；functional-spec.md 3.3 | 前次 review-03 R-12 已提：設計沒有明寫「先把 dispatchStage 寫成 request_sent 並確認寫入成功，才送出 HTTP 請求」的順序。BR56.1 寫「POST A1（dispatchStage=request_sent）」可讀成送出後才寫入；若如此，緩衝期間（最長 300 秒）儲存值仍是 not_dispatched，correct 會算出 sideEffect=none，與 BR55.1 要求的 unknown 相反，比對也不會失敗。persisting 與 PUT 同理。程式正確：docstring 的「先記錄、再送出（NFR12.21）」。 | 在 BR55.3 或 BR56.1 明寫先寫入成功再送出，寫入失敗即中止，PUT 同理 | New |
| R-04 | Minor | rules.md BR52.7；functional-spec.md 2.3；entities.md 約束 | 前次 review-03 R-13 已提：兩處 CAS 精度。(1) 設計的 update_work_item 簽名收整個 item，比對只含 status 與 dispatchStage，過期物件可把另一個寫入者剛寫的 estimateSetId 或 targetDiagramId 覆寫回 null，與 BR52.7 自述的「其他欄位不被過期值覆蓋」不符。(2) 規格未指定 eval_script 的 idempotent 旗標，連線錯誤重試會讓第二次比對失敗而被誤判為被搶先。程式正確：update_work_item.lua 收補丁並以讀到的當前值為底合併，session_store.py 的兩個寫入方法皆 idempotent=False（約 441、476 行），連線錯誤後由 _cas 重讀確認。 | 設計改為補丁語意並明寫兩個寫入方法一律 idempotent=False、結果未知時重讀確認 | New |
| R-05 | Minor | rules.md BR51.7、BR51.4、BR51.5 | 前次 review-03 R-14 已提：BR51.7 規定使用者不存在或停用即依 BR51.3 失敗，套用於所有背景 facade 呼叫；但 BR51.4（變更紀錄）與 BR51.5（procedure 記憶）在存回成功後執行，且各自規定不改狀態。使用者在 PUT 與寫紀錄之間被停用時兩條規則給出相反結果，轉失敗會對圖已存回的項目宣稱失敗。 | BR51.7 明寫優先順序：存回之前的 facade 呼叫失敗依 BR51.3，存回之後的 BR51.4 與 BR51.5 依各自的 violation_behaviour，不改 status | New |
| R-06 | Minor | rules.md BR53.2、BR53.3、BR53.4、BR55.1、BR56.6、BR56.7、BR58.1；entities.md entity_constraints | 前次 review-03 R-15 已提：欄位清空與寫入未逐條寫明。(1) 實體約束「處理中且 deadlineAt 非 null」「waitingOn 與 dependsOn 僅等待中非 null」，但 BR53.3、BR55.1、BR56.6、BR56.7 第 1 步未寫清空，BR53.2 與 BR53.4 的成本分支未寫入 deadlineAt。(2) BR56.7 第 1 步的 sideEffect 只分 not_dispatched 與其他，與 BR56.6 所說「同 BR55.1 對照表」對同一情境答案不同。(3) BR53.4 的跳過訊息不在 BR58.1 句型表內。程式已涵蓋：_advance_waiter 的 patch 三個分支都清空 waitingOn、dependsOn，推進為處理中時寫 deadlineAt，失敗與已停掉分支把 deadlineAt 設 null；跳過句型在 R.PHRASES 的 skipped。 | 設計補寫通則（進入終態清空三欄、進入處理中必寫 deadlineAt）、BR56.7 第 1 步改引用 BR55.1 對照表、BR58.1 補列跳過句型 | New |
| R-07 | Minor | functional-spec.md 第八節 OPEN-WO12-6、OPEN-WO12-7；traceability.json AC1.3.2、AC5.1.3、AC10.2.4 | 三條上游 AC 以 Deferred 帶進關卡，尚未有裁決：AC10.2.4 的可觀察結果（C1 讀取端點寫稽核事件）在現行 C1 不存在，AC1.3.2 與 AC5.1.3 的「不受影響」在停掉前提項時不字面成立。設計誠實揭露，非設計缺陷，但它們是 ADR-0006 稽核面與使用者可見行為的待決項，不能被讀成已滿足。 | 在關卡上請使用者裁決：改寫三條 AC 的 Then，或指定其他處置；裁決前不得把這三條計入已覆蓋 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 規則數與 traceability 手算（rules.md 與 traceability.json） | 規則 45 條（8+7+4+1+7+8+5+5），與規格第五節一致；Deferred 為 AC1.3.2、AC5.1.3、AC10.2.4，皆有 OPEN 指向 | PASS，編號與覆蓋一致 |
| 設計與程式對照（work_orchestrator.py、session_scripts/update_work_item.lua、put_work_item.lua、session_store.py） | shield 保護在途存檔收尾、寫入成功者才有副作用、補丁式 CAS、兩個寫入方法 idempotent=False、key 不存在不建 key，皆已落地 | 支持 R-01 至 R-06 的結論：程式正確、設計過期 |
| 專案測試與 lint | 未執行 | 依指示不執行任何會寫檔或產生快取的指令 |
