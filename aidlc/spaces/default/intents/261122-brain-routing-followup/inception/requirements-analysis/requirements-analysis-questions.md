# Requirements Analysis 問題

本 intent 為事後補走流程：修正已在分支 `danniel/fix/brain-routing-followup-context` 實作（未 commit）。以下只問修正中尚未定案、且 Reverse Engineering 掃描點出風險的事項。

已由對話定案、不重問：
- 兩個問題一起修（使用者原話：「兩個一起修」）。
- 「架構設計只回提問、沒產圖」不判失敗，工作項以既有狀態集合的「完成」結束並提示「等你回覆」；不新增狀態（狀態集合為前後端共用契約）。

## 查證紀錄（非來源，供題幹引用）
- `backend/services/work_orchestrator.py:526-535`（`_recover` 第二輪）：等待中的工作項只看被等待項的 `status`，為終態且非失敗就以該狀態推進；「完成」會讓等待者開始執行。
- `backend/services/intent_routing_context.py:50`：`DEFAULT_MESSAGE_CHARS = 400`；修正後 `build_state` 每則歷程取**前** 400 字。
- `backend/services/intent_routing_decisions.py:66-67`：`PRIMARY_CRITERIA` 的註解「逐字沿用實測時的文字：換字就要重新量測（NFR1）」；修正把延續規則接在 `primary` 與 `wants_*` 的 `instructions` 之後（criteria 未動）。
- ADR-0024（`260920-orchestration-brain/inception/decisions/0024-intent-routing-via-jev-decisions-api.md`）記載 Decisions 路徑的設計；修正前 `build_state` docstring 明寫「不帶對話歷程」。

## Question 1
架構設計回了提問、工作項記為「完成」之後，程式若剛好在「把等待中的檢視／成本標為不執行」之前中止，重啟後的復原會看到被等待項是「完成」，於是讓檢視或成本在**舊圖**上執行。這個時間窗很窄，但結果是使用者看到一份對錯圖做的檢視或估價。要怎麼處理？

A) 這次一起修：復原時若被等待的是架構設計、狀態為「完成」但沒有存回圖（`dispatchStage` 不是 `result_persisted`），視同「還在等你回覆」，等待者以不執行結束；補一個復原測試
B) 這次一起修，但改在工作項上加一個明確標記（例如 `awaitingReply: true`）讓復原判斷，不用 `dispatchStage` 推論
C) 不修，記為已知風險與 open question
X) Other (please specify)

[Answer]: A

## Question 2
路由判讀「延續回答」時，每則對話歷程只取**前** 400 字。架構設計的提問常是「說明＋選項 A/B/C/D」，選項放在最後；提問一長，選項就被截掉，模型看不到使用者回的「A」對應什麼。要怎麼截？

A) 改成保留每則訊息的**結尾** 400 字（選項通常在最後），其餘不變
B) 保留開頭與結尾各 200 字，中間以「…」連接
C) 把上限提高到 1200 字、仍取開頭
D) 維持現狀（前 400 字）
X) Other (please specify)

[Answer]: A

## Question 3
Decisions 題目的指示文字多接了一句延續規則，按程式註解，ADR-0024 量出的機率與門檻（反問門檻 0.7、指名下限 0.8）對新文字不再有保證。要怎麼驗？

A) 部署到 staging 後，用 ADR-0024 實測表的六句再量一次，另加「架構設計提問後只回 A」一句，結果記錄在本 intent；量不過就回頭調整
B) 拿掉指示文字裡的延續規則，只靠 `state` 帶歷程，讓題目文字維持與實測時逐字相同
C) 不另外量，靠上線後觀察
X) Other (please specify)

[Answer]: A

## Question 4
ADR-0024 與修正前的程式都寫明「Decisions 路徑不帶對話歷程」，這次改成會帶最近 6 則。這個設計變更要怎麼記錄？

A) 在本 intent 新開一份 ADR，記錄改帶歷程的理由與取捨，並註明它修訂 ADR-0024 的該項決定（ADR-0024 本文不改）
B) 直接在 ADR-0024 加一段修訂註記
C) 不另立 ADR，只在本 intent 的 requirements 與程式註解記錄
X) Other (please specify)

[Answer]: A
