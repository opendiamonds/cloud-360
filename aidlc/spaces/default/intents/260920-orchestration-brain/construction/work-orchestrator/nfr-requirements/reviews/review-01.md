## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-12T06:04:16Z
**Iteration:** 1

### Findings

| ID | Severity | Status | Location | Finding | Required action |
|---|---|---|---|---|---|
| R-01 | Major | New | nfr-requirements/reliability-requirements.md 第三節對照表「4」；scalability-requirements.md NFR12.12 性質 (c) | review-03 帶入項 4（R-13）有兩個子點，只承載了一半。(1) 子點二「update_work_item、put_work_item 的 eval_script 一律 idempotent=False」在七份產出中零命中（grep idempotent 全無）；backend/services/redis_gateway.py:460-489 的 eval_script 要求呼叫端明傳 idempotent，並由 _call 依此重試，重試時第一次已成功、第二次比對失敗回 False，呼叫端誤判為被搶先而中止。(2) 子點一以 NFR12.12 性質 (c)「estimateSetId 不被清為 null」承載，但該 NFR 的操作字母表只有「背景推進 dispatchStage」「correct」「復原掃描」三串；BR56.3 寫入 estimateSetId 時 status 與 dispatchStage 皆不變（rules.md BR56.3、BR52.7 的比對條件只含這兩者），這個寫入不在字母表內，性質 (c) 在該測試中恆真，無法失敗。 | 新增一條 NFR：兩支 Lua 的呼叫一律 idempotent=False，判準為注入「寫入成功但回應連線錯誤」的替身，斷言只呼叫一次且呼叫端以重讀確認而非盲目判定被搶先。NFR12.12 的字母表加入「寫入 estimateSetId／targetDiagramId」操作，並指明防過期覆寫的機制（欄位補丁或版本號）；對照表第 4 列改指向新條款。 |
| R-02 | Major | New | reliability-requirements.md 第三節「6」與 NFR12.14；functional-design/reviews/review-03.md R-15 | 帶入項 6（R-15 三個子點）承載不足。(1) 終態與離開處理中時清空 waitingOn／dependsOn／deadlineAt、以及等待中到處理中必寫 deadlineAt：NFR12.14 只斷言「進入處理中者 deadlineAt 非 null」，沒有「離開處理中或終態時三欄為 null」的判準；且其稱「PBT 的 transition 性質涵蓋」不成立——functional-spec.md:244 的 transition(status, event) -> status 或拒絕，只吃 status 與 event，看不到 deadlineAt 與 waitingOn，NFR12.12 的 (a)(b)(c) 也不含此不變量。(2) BR56.7 第 1 步的 sideEffect（not_dispatched 為 none、其餘 unknown）與 BR55.1 對照表（persisting 為可能已存回、result_persisted 為說明文字）矛盾，任何 NFR 都沒提。(3) BR58.1 缺跳過句型，僅以「由 code-generation 的單元測試承載」帶過，沒有 NFR 編號與二元判準，也未列句型清單。對照表把三個子點壓成一句，讓閘門讀者以為已承載。 | 新增 NFR 並逐子點列判準：stateful 模型測試加不變量「status 為處理中 若且唯若 deadlineAt 非 null；status 為等待中 若且唯若 waitingOn、dependsOn 非 null；終態三欄全為 null」；逾期路徑與 correct 以同一純函式（side_effect_on_stop）產生 sideEffect 並以測試鎖住；BR58.1 固定句型清單（含跳過句型）列為表格，判準為「sink 收到的每則文字皆屬清單」。對照表第 6 列改為逐子點對應。 |
| R-03 | Major | New | scalability-requirements.md NFR12.12／NFR12.13；reliability-requirements.md NFR12.18；tech-stack-decisions.md 第〇節 | 這三條的證明力被高估且未揭露限制。repo 的 Redis 替身只「呼叫 session_types 的參考實作」模擬 Lua（backend/tests/test_session_store_behaviour.py 檔頭自述：替身證明不了 Lua 的原子性，真實驗證點是 [I1]=B 的部署後步驟，不是 CI）。本單元新增的 put_work_item.lua 與 update_work_item.lua 之 CAS 與「key 不存在即拒絕」，正是 NFR12.12、12.13、12.18 的承重點，但這些判準在替身上跑，只驗呼叫端邏輯；Lua 原始碼與參考實作若漂移（或腳本寫錯），全部仍綠燈。產出沒有要求新增參考實作、沒有要求兩者一致的測試，也沒寫出此限制與真實 Redis 的驗證點，與前例 U10 明寫限制的做法不一致。 | 在 scalability 與 reliability 檔明寫替身限制；新增 NFR：兩支 Lua 在 session_types 有對應參考實作，並有測試鎖住兩者一致（例如同一組案例表同時驅動參考實作並對照 Lua 行為，或在可用時對真實 Redis 跑同一組案例）；真實 Redis 的 CAS 與 EXISTS 驗證列為部署後步驟並指名承接處。 |
| R-04 | Major | New | security-requirements.md NFR12.9 第一個案例 | 「A1 回應之前把使用者 is_active 設為假，工作項失敗且未 PUT」無法分辨 BR51.7 的重鑄是否實作。A1 回應與 PUT 之間沒有 facade 呼叫；PUT 與先前讀圖都走 HTTP，backend/services/auth.py:75 的 get_user_from_token 對停用者回 403，工作項因此依 BR51.3 失敗，與 facade 是否重鑄無關。且 backend/services/hierarchy_facade.py:145-158 的 mint_principal 本身不檢查 is_active，停用判定必須由本單元自寫，這正是需要被測的部分。快照角色的錯誤實作在此案例仍是綠燈。僅第二案例（PUT 之後停用、變更紀錄呼叫重鑄）能區分。 | 第一案例改為停用發生在會呼叫 facade 的點之前（例如 list_diagrams_of_system 或記憶寫入之前，且該點之前沒有任何 HTTP 呼叫會先 403），可觀察結果為「facade 路徑的失敗」；補突變：把重鑄改為沿用握手快照時此案例變紅。 |
| R-05 | Major | New | reliability-requirements.md NFR12.19、NFR12.20、第三節「1」；functional-design/reviews/review-03.md R-10 | 帶入項 1（R-10）的第二半未承載。R-10 明指 BR56.6 的 wait_for 逾時在 dispatchStage=persisting 時同樣取消 PUT 收尾，PUT 若成功則圖已改寫而沒有變更紀錄（BR55.7 只涵蓋已停掉，不涵蓋逾時失敗）。NFR12.19 只測「永不返回的 A1 替身」（request_sent 階段），NFR12.20 只測 correct 的取消；tech-stack 的 asyncio.shield 也只寫「在途存檔的收尾」。persisting 階段逾時、PUT 成功後的處置（是否補寫變更紀錄、sideEffect 為何、比對條件的預期 status 為失敗）在規則與 NFR 皆無，屬 ADR-0006 稽核面缺口。 | 新增 NFR：persisting 階段逾時、PUT 成功，變更紀錄恰 1 列且 sideEffect 如實；判準以 PUT 延遲超過牆鐘上限的替身驗證。並要求 BR55.7 的比對預期狀態涵蓋「失敗（逾時）」。 |
| R-06 | Minor | New | reliability-requirements.md NFR12.21；review-03 R-12 | 帶入項 3 只覆蓋 request_sent。R-12 同時要求 persisting 在送 PUT 之前先以比對後寫入推進；NFR12.21 判準只有「讓該次寫入回 False，能力替身被呼叫 0 次」。 | 判準加一案：persisting 寫入回 False，PUT 呼叫 0 次。 |
| R-07 | Minor | New | performance-requirements.md NFR12.3；reliability-requirements.md NFR12.17、NFR12.19 | 判準依賴「假時鐘」，但 backend/requirements.txt 無 freezegun 類工具；asyncio.wait_for 用事件迴圈時間、deadlineAt 用牆鐘，是兩種時鐘；產出沒有要求可注入的時間來源與逾時常數。照字面實作者只能真等 300 或 360 秒，或自行發明。另 NFR12.3 的「至多 180 次」邊界不明（t=0 立即輪詢會是 181 次）。 | 加一條要求：時間來源、三個牆鐘常數與輪詢間隔可由建構參數注入；明寫次數計法（含或不含首次）。 |
| R-08 | Minor | New | performance-requirements.md NFR12.5；security-requirements.md NFR12.8 | 兩條 grep 判準有繞過路徑。NFR12.5 只數 llm_provider、openai、langchain、langgraph 的 import，但本單元合法持有 httpx，直接以 httpx 打 LLM 端點不被偵測；NFR12.8 的清單缺 main（BR51.1 明禁本單元 import main），且兩者都未定義「本單元新增模組」的檔案集合。 | NFR12.5 加行為判準：測試中 AsyncClient 的唯一傳輸為 ASGITransport，任何其他出站請求使測試失敗；NFR12.8 補 main 並列出檔案集合。 |
| R-09 | Minor | New | security-requirements.md 第一節 requestText 列與第四節；functional-design/functional-spec.md:238 | requestText（Redis 24 小時）與變更摘要的靜態加密併入上游 OQ-3，但 requirements.md:784 的 OQ-3 範圍是 episodic memory（NFR7），承接站 nfr-design 為 CONDITIONAL；且本站判 NFR7 為 N/A（理由：保存與稽核由 U8 承擔），卻把本單元的落地內容併入由 NFR7 衍生的 OQ-3，兩者不一致。也沒寫 nfr-design 被 skip 時的轉移目標（project.md 已有多次指派落空的前例）。 | 在 security 檔明寫 OQ-3 的範圍因本單元而擴大，並指名 nfr-design 被 skip 時的承接者（保險起見為 code-generation，ALWAYS）。 |
| R-10 | Minor | New | tech-stack-decisions.md NFR12.27／NFR12.28；functional-design/functional-spec.md:242-244 | 兩處不一致或名實落差。(1) functional-spec 第七節寫 PBT 受測對象「三個」純函式，同節列了四個（含 on_dependency_stopped），NFR12.28 取「四個」，應以四為準並回報 FD 修正。(2) NFR5 判 OK 靠 NFR12.27：該條由測試替身 sink 驗證，只約束測試路徑，生產路徑的訊息是否經模型建構無機械保障；NFR5 要的 CI 檢查歸契約單元，本單元較準確的說法是「消費契約模型」，不是承接閘門。 | 回報 FD「三個」的筆誤；traceability 的 NFR5 note 改寫為依賴 U2 的閘門加本單元以模型建構，並加一條 grep 判準：本單元模組不得出現手組的訊息 dict。 |
| R-11 | Minor | New | security-requirements.md NFR12.6；reliability-requirements.md NFR12.23 | 判準覆蓋不全。NFR12.6 檢查 Redis 欄位與 log，沒檢查經 sink 推送的訊息與 work_items 內容；NFR12.23 只測「輪詢失敗 2 次後成功」，缺「連續 3 次即失敗」的另一側邊界，以及 401／403 不計入連續失敗。 | 補 sink 訊息到 NFR12.6；NFR12.23 補 3 次失敗案與 401／403 案。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| grep idempotent、freezegun、fakeredis（nfr-requirements 與 backend/requirements.txt） | 產出 0 命中；requirements.txt 僅有 redis，無 fakeredis、freezegun | 支持 R-01、R-07；測試只能用 U10 式的手寫替身 |
| 讀 backend/services/redis_gateway.py:460-489、tests/test_session_store_behaviour.py 檔頭 | eval_script 要求明傳 idempotent；替身以參考實作模擬 Lua，檔頭自述證明不了原子性 | 支持 R-01、R-03 |
| 讀 backend/services/auth.py:58-75、hierarchy_facade.py:145-158 | 停用者於 HTTP 路徑回 403；mint_principal 不檢查 is_active | 支持 R-04 |
| 比對 rules.md BR51-BR58、functional-spec.md 第七節與 NFR 引用的規則編號 | 引用的 BR 編號皆存在；360／2＝180、300／360 秒與規則一致 | 規則編號與數字無矛盾；缺口集中在承載範圍（R-01、R-02、R-05） |
| 上游 NFR 判定（requirements.md NFR1-NFR11 對 traceability.json） | NFR3／4／5／9 OK、其餘 N/A，N/A 理由大致合理（NFR7 見 R-09）；七份產出沒有一張明列 NFR1-11 判定與理由的表，僅在 traceability.json | 判定本身可接受，建議在檔頭補表 |
| 專案測試 | 未執行 | 本站為需求文件，無程式可跑 |

### Summary

Critical 0；Major 5（R-01 至 R-05），Minor 6（R-06 至 R-11）。多數 NFR 判準能以 unittest、hypothesis、ASGITransport 實作且會失敗，問題集中在 review-03 六個帶入項的承載：項 4、6 各只承載一半，項 1 的逾時半邊與項 3 的 persisting 半邊未承載，加上 NFR12.9 首案不能區分重鑄、Lua 相關判準在替身上跑卻未揭露限制。上述發現皆為既存漏審，非前輪修正所引入。
