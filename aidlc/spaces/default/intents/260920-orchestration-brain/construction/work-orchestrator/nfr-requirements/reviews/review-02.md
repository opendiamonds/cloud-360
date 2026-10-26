## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本站七份需求檔（NFR12.1 至 NFR12.29）的規則編號、數字（360 秒除以 2 秒等於 180 次）與上游引用大致無誤，多數判準可用 unittest、hypothesis 與 ASGITransport 實作並會失敗。但產出已凍結，前次 review-01 提出的五項 Major 與六項 Minor 在產出中仍原樣存在，主要缺口集中在 functional-design review-03 六個帶入項的承載不足（項 1、3、4、6 只承載一半）、NFR12.9 首案無法分辨重鑄是否實作、Lua 相關判準在替身上跑卻未揭露限制。已落地的程式在多處已補上這些行為（session_store.py 的 Lua 寫入為 idempotent=False；work_orchestrator.py:1024 自寫停用判定；work_orchestrator.py:672 以 asyncio.shield 保護存檔；牆鐘改為 sleep 切片而非 wait_for），所以對程式而言是需求文件落後於實作，但需求文件作為驗收來源仍有缺口。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/work-orchestrator/nfr-requirements/reliability-requirements.md 第三節對照表第 4 列；scalability-requirements.md NFR12.12 性質 (c) | 前次 review-01 已提 R-01，產出未改。帶入項 4（review-03 R-13）兩個子點只承載一半：(1) 兩支 Lua 的 eval_script 一律 idempotent=False 在七份產出零命中，若傳輸層重送，第一次已成功、第二次比對失敗回 False，呼叫端會誤判被搶先而中止；程式已做對（backend/services/session_store.py:441、:476 為 idempotent=False），但需求無判準可驗。(2) NFR12.12 的操作字母表只有背景推進、correct、復原掃描三串，BR56.3 寫入 estimateSetId 時 status 與 dispatchStage 皆不變，不在字母表內，性質 (c) estimateSetId 不被清為 null 在該模型測試中恆真。 | 新增一條 NFR：兩支 Lua 呼叫一律 idempotent=False，判準為注入寫入成功但回應連線錯誤的替身，斷言只呼叫一次且以重讀確認。NFR12.12 字母表加入寫入 estimateSetId 與 targetDiagramId 的操作並指明防過期覆寫機制；對照表第 4 列改指向新條款。 | New |
| R-02 | Major | construction/work-orchestrator/nfr-requirements/reliability-requirements.md 第三節第 6 列與 NFR12.14；functional-design/rules.md BR56.7、BR55.1、BR58.1 | 前次 review-01 已提 R-02，產出未改。帶入項 6 三個子點被壓成一句：(1) NFR12.14 只斷言進入處理中者 deadlineAt 非 null，沒有離開處理中或終態時 waitingOn、dependsOn、deadlineAt 皆為 null 的判準，且稱 PBT 的 transition 性質涵蓋不成立，transition 只吃 status 與 event，看不到這三欄。(2) BR56.7 第 1 步的 sideEffect（not_dispatched 為 none、其餘 unknown）與 BR55.1 對照表（persisting、result_persisted 的處置）不一致，任何 NFR 都未要求兩條路徑共用同一純函式。(3) BR58.1 的固定句型含跳過句型，僅以由 code-generation 的單元測試承載帶過，無 NFR 編號、無句型清單、無二元判準。 | 新增 NFR 逐子點列判準：stateful 模型測試加不變量（處理中若且唯若 deadlineAt 非 null；等待中若且唯若 waitingOn 與 dependsOn 非 null；終態三欄全為 null）；逾期路徑與 correct 共用 side_effect_on_stop 並以測試鎖住；BR58.1 句型列表格，判準為 sink 收到的每則文字皆屬清單。對照表第 6 列改為逐子點對應。 | New |
| R-03 | Major | construction/work-orchestrator/nfr-requirements/scalability-requirements.md NFR12.12 與 NFR12.13；reliability-requirements.md NFR12.18；tech-stack-decisions.md 第〇節 | 前次 review-01 已提 R-03，產出未改。這三條的承重點是 put_work_item.lua 與 update_work_item.lua 的比對後寫入與 key 不存在即拒絕，但 repo 的 Redis 測試替身只呼叫 session_types 的參考實作模擬 Lua（backend/tests/test_session_store_behaviour.py 檔頭自述證明不了原子性）。判準在替身上跑只驗呼叫端邏輯，Lua 原始碼與參考實作漂移時全部仍綠燈。產出沒有要求新增參考實作、沒有要求兩者一致的測試，也沒寫出此限制與真實 Redis 的驗證點，與前例 U10 明寫限制的做法不一致。 | 在 scalability 與 reliability 檔明寫替身限制；新增 NFR 要求兩支 Lua 有參考實作並有測試鎖住兩者一致（同一組案例表同時驅動兩者）；真實 Redis 的 CAS 與 EXISTS 驗證列為部署後步驟並指名承接處。 | New |
| R-04 | Major | construction/work-orchestrator/nfr-requirements/security-requirements.md NFR12.9 第一個案例 | 前次 review-01 已提 R-04，產出未改。案例為 A1 回應之前把使用者 is_active 設為假，期望工作項失敗且未 PUT，但 A1 回應與 PUT 之間沒有 facade 呼叫，讀圖與 PUT 都走 HTTP，backend/services/auth.py 的 get_user_from_token 對停用者回 403，工作項依 BR51.3 失敗，與 BR51.7 的 facade 重鑄是否實作無關；快照角色的錯誤實作在此案例仍綠燈。而 hierarchy_facade.py 的 mint_principal 本身不檢查 is_active，停用判定必須由本單元自寫（程式已寫於 work_orchestrator.py:1024），這正是需要被測的部分。僅第二案例（PUT 之後停用）能區分。 | 第一案例改為停用發生在會呼叫 facade 的點之前（例如 list_diagrams_of_system 或記憶寫入之前，且該點之前沒有任何 HTTP 呼叫會先 403），可觀察結果為 facade 路徑的失敗；補突變：把重鑄改為沿用握手快照時此案例變紅。 | New |
| R-05 | Major | construction/work-orchestrator/nfr-requirements/reliability-requirements.md NFR12.19、NFR12.20、第三節第 1 列；functional-design/rules.md BR55.7、BR56.6 | 前次 review-01 已提 R-05，產出未改。帶入項 1 的第二半未承載：dispatchStage 為 persisting 時牆鐘逾時，PUT 若仍成功則圖已改寫，但 BR55.7 只涵蓋已停掉，不涵蓋逾時失敗；NFR12.19 只測永不返回的 A1 替身（request_sent 階段），NFR12.20 只測 correct 的取消。persisting 階段逾時且 PUT 成功時變更紀錄是否補寫、sideEffect 為何、比對預期 status 為何，規則與 NFR 皆無，屬 ADR-0006 audit logging 面缺口。另設計與程式有出入：NFR12.19 與 tech-stack 假設 asyncio.wait_for，程式（work_orchestrator.py:44）改為 sleep 切片檢查，程式一側較合理，因 wait_for 會取消存檔。 | 新增 NFR：persisting 階段逾時且 PUT 成功，變更紀錄恰 1 列且 sideEffect 如實，判準以 PUT 延遲超過牆鐘上限的替身驗證；BR55.7 的比對預期狀態納入失敗（逾時）；tech-stack 的背景執行列改以實作的 sleep 切片為準並註明理由。 | New |
| R-06 | Minor | construction/work-orchestrator/nfr-requirements/reliability-requirements.md NFR12.21 | 前次 review-01 已提 R-06。review-03 R-12 同時要求 persisting 在送 PUT 之前先以比對後寫入推進；NFR12.21 判準只有 request_sent 寫入回 False 時能力替身被呼叫 0 次。 | 判準加一案：persisting 寫入回 False，PUT 呼叫 0 次。 | New |
| R-07 | Minor | construction/work-orchestrator/nfr-requirements/performance-requirements.md NFR12.3；reliability-requirements.md NFR12.17、NFR12.19 | 前次 review-01 已提 R-07。判準依賴假時鐘，但 backend/requirements.txt 無 freezegun 類工具；事件迴圈時間與牆鐘 deadlineAt 是兩種時鐘；產出沒有要求時間來源、牆鐘常數與輪詢間隔可注入。NFR12.3 的至多 180 次未定義是否含 t=0 首次（含則為 181）。 | 加一條要求時間來源、三個牆鐘常數與輪詢間隔可由建構參數注入；明寫次數計法。 | New |
| R-08 | Minor | construction/work-orchestrator/nfr-requirements/performance-requirements.md NFR12.5；security-requirements.md NFR12.8 | 前次 review-01 已提 R-08。NFR12.5 只數 llm_provider、openai、langchain、langgraph 的 import，本單元合法持有 httpx，直接以 httpx 打 LLM 端點不被偵測；NFR12.8 清單缺 main（BR51.1 明禁），兩者都未定義本單元新增模組的檔案集合（實際為 work_orchestrator.py、work_orchestrator_rules.py、work_orchestrator_capabilities.py）。 | NFR12.5 加行為判準：測試中 AsyncClient 的唯一傳輸為 ASGITransport，任何其他出站請求使測試失敗；NFR12.8 補 main 並列出檔案集合。 | New |
| R-09 | Minor | construction/work-orchestrator/nfr-requirements/security-requirements.md 第一節 requestText 列與第四節 | 前次 review-01 已提 R-09。requestText 與變更摘要的靜態加密併入上游 OQ-3，但 OQ-3 範圍源自 episodic memory（NFR7），承接站 nfr-design 為 CONDITIONAL，且本站判 NFR7 為 N/A；也未寫 nfr-design 被 skip 時的轉移目標。 | 明寫 OQ-3 範圍因本單元擴大，並指名 nfr-design 被 skip 時的承接者（建議 code-generation，ALWAYS）。 | New |
| R-10 | Minor | construction/work-orchestrator/nfr-requirements/tech-stack-decisions.md NFR12.27、NFR12.28；traceability.json NFR5 列 | 前次 review-01 已提 R-10。functional-spec 第七節稱三個純函式而同節列四個，NFR12.28 取四個，應回報 FD 筆誤。NFR12.27 由測試替身 sink 驗證，只約束測試路徑，生產路徑是否皆經模型建構無機械保障，traceability 將 NFR5 標 OK 的說法過強。 | traceability 的 NFR5 note 改為依賴 U2 的閘門加本單元以模型建構，並加 grep 判準：本單元模組不得出現手組的訊息 dict。 | New |
| R-11 | Minor | construction/work-orchestrator/nfr-requirements/security-requirements.md NFR12.6；reliability-requirements.md NFR12.23 | 前次 review-01 已提 R-11。NFR12.6 檢查 Redis 欄位與 log，未檢查經 sink 推送的訊息；NFR12.23 缺連續 3 次失敗即判斷線的另一側邊界，以及 401、403 不計入連續失敗。 | NFR12.6 補 sink 訊息；NFR12.23 補 3 次失敗案與 401、403 案。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| grep idempotent 於 nfr-requirements 七份產出 | 0 命中 | 支持 R-01；程式 session_store.py:441、:476 已為 idempotent=False，是需求落後於實作 |
| 讀 session_store.py、work_orchestrator.py 抽查 | 停用判定自寫（:1024）、shield（:672）、牆鐘改 sleep 切片（:44） | 支持 R-04、R-05；設計文字與落地有出入，程式一側較對 |
| 規則編號與數字核對（BR51 至 BR58、360 除以 2 等於 180、300、360 秒） | 引用的 BR 編號皆存在，數字與規則一致 | 無編號或算術錯誤；缺口在承載範圍 |
| 上游 NFR1 至 NFR11 判定（traceability.json） | NFR3、4、5、9 為 OK，其餘 N/A，理由大致合理 | 可接受，NFR5 說法過強見 R-10 |
| 專案測試 | 未執行 | 本審查規定不得執行會寫檔的指令 |
