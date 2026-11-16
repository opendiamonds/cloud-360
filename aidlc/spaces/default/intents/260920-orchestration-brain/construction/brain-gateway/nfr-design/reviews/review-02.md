## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

nfr-design 的追溯與事實引用整體紮實，但凍結的產出仍保留前次 review-01 已提的五項狀態轉移與生命週期缺陷：熔斷半開探測者在執行器滿時不清除、run 吞掉取消、頻率窗隨連線刪除可被重連繞過、送出失敗只移出登錄而不關閉連線、執行器與號誌寫成類別屬性。已落地的程式（brain_gateway.py、brain_gateway_rules.py）與 code-summary.md 帶入項 18 到 22 已逐項修正，程式這一邊是對的；問題在於設計文字沒有回補，且 nfr-design 目錄下沒有任何 corrections 檔取代原文，所以下游或維護者照這份設計實作會重現缺陷。依規則（Major 超過 2 項）判 NOT-READY；若人在關卡上接受「以 code-summary 的取代關係為準」，這些項目可轉為接受風險。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/brain-gateway/nfr-design/reliability-design.md 第 3.2 節 BreakerState.admit；performance-design.md 第 3.2 節 MemoryWorker.run | 前次 review-01 已提（原標 Critical）。設計的 admit 在開啟期滿後把 probing 設為真並回 probe，run 隨後 acquire(blocking=False) 取不到位子就回 BUSY_SKIPPED 且明寫不呼叫 on_failure，probing 只在 on_success 與 on_failure 清除，故嵌入逾時使 4 條執行緒被佔滿的主要故障情境下，熔斷會永久卡在半開、全體使用者記憶停擺。三條 hypothesis 不變量沒有活性性質，抓不到。程式端已修：brain_gateway_rules.py 第 534 到 535 行與 release_probe，code-summary 帶入項 18 與突變 M4 皆有，程式是對的，設計文字是錯的。降為 Major 是因為程式已落地，缺陷只剩在凍結的設計文件裡 | 新增 nfr-design 的 corrections 檔（或回補原文），把 BUSY_SKIPPED、submit 失敗、取消三個出口必須 release_probe 寫成設計，並加入「無在途呼叫時 probing 必為假」的活性不變量 | New |
| R-02 | Major | construction/brain-gateway/nfr-design/scalability-design.md 第一節 release_key 與第三節清除端 | 前次 review-01 已提。設計規定 release_key 使某 key 計數歸 0 時同步刪除該 key 的頻率窗，使用者關閉全部連線再重連即重置每 key 每分鐘 20 則上限，而握手只付一次 DB 認證、設計無握手頻率限制，每則訊息都會觸發付費 classify，NFR13.20 要保護的成本路徑可被繞過。程式端已修：RateLimiter 以使用者為鍵、時間到才清、握手納入限流（admit_handshake、sweep，code-summary 帶入項 20 與突變 M6），程式是對的 | 回補設計：窗的生命週期由時間決定、不隨連線刪除；握手頻率上限寫成設計；補「連線一送滿 20 則後關閉、同使用者新連線立刻第 21 則被拒」的判準 | New |
| R-03 | Major | construction/brain-gateway/nfr-design/scalability-design.md 第四節 send_direct；reliability-design.md 第八節 | 前次 review-01 已提。送出失敗（含 10 秒逾時）只做 unregister 與 dead=True，不關閉 websocket、不喚醒卡在 receive_text 的 handler；客戶端仍以為已連線，之後所有扇出靜默收不到，也拿不到重連快照，佔位也要到 handler 結束才釋放，窗口約 40 秒（ping 逾時）。程式端已修：Connection._on_send_failure 取消登錄並主動 close(1011)（code-summary 帶入項 21、突變 M7） | 回補設計：送出失敗後除 unregister 與 dead 外，必須主動 close(1011) 或取消接收 task，並寫入判準（客戶端收到關閉、佔位歸零） | New |
| R-04 | Major | construction/brain-gateway/nfr-design/performance-design.md 第 3.2 節 class MemoryWorker；reliability-design.md 第九節 shutdown | 前次 review-01 已提。設計把 _executor 與 _slots 寫成類別屬性（import 時建立），shutdown hook 直接 MemoryWorker._executor.shutdown(...)；同一行程第二次 build（TestClient lifespan 重跑）會拿到已關閉的 executor，號誌也跨實例共用。第 3.2 節同時沿用 except BaseException 並 return breaker.on_failure(exc)，會吞掉 CancelledError，與 reliability-design.md 第五節宣稱「CancelledError 重拋」自相矛盾（前次 R-02）。程式端已修：實例屬性（brain_gateway.py 第 376 到 381 行，帶入項 22）、取消重拋（帶入項 19、突變 M5） | 回補設計：執行器與號誌為 MemoryWorker 實例屬性，由 build_brain_gateway 建立；run 對 CancelledError 單獨處理並重拋，on_failure 只收 Exception；shutdown 只關該實例 | New |
| R-05 | Minor | construction/brain-gateway/nfr-design/ 全目錄（缺 corrections 檔）；logical-components.md 第六節取代關係表 | 本站設計與落地程式有至少 11 處偏離（code-summary 帶入項 18 到 29，另有偏離 D6、D9），但 nfr-design 沒有 corrections 檔，取代關係只存在 code-summary.md。依本專案慣例，corrections 檔取代原產出並約束下游；缺它使 nfr-design 目錄單獨讀起來仍是錯的，這是 R-01 到 R-04 變成阻擋項的根因 | 新增 nfr-design-corrections.md，逐項列出 code-summary 帶入項 18 到 29 對 nfr-design 的取代，並在 logical-components.md 第六節取代表加指向 | New |
| R-06 | Minor | construction/brain-gateway/nfr-design/scalability-design.md 檔頭與第 1.5 節；logical-components.md 第五節第 17 列與第七節 OPEN-GW13-21；traceability.json 的 NFR13.18 note | 前次 review-01 R-06 已提。問題檔已記 [GWND1]=A，這幾處仍寫「出題待使用者裁決」「暫依」，且 U14 退避重試至少 60 秒的義務沒有登錄為 U14 配合事項。程式端與 code-summary 帶入項 17、23 已更新 | 同步更新為已裁決 A，並把 60 秒退避義務寫成與 OPEN-GW13-17 同批的 U14 配合事項 | New |
| R-07 | Minor | construction/brain-gateway/nfr-design/security-design.md 第六節檢查 2；scalability-design.md 第四節 send_direct | 前次 review-01 R-08 已提。AST 名稱檢查禁止名為 text 的 Name 或 Attribute，而設計自己的 send_direct 就寫 text = model.model_dump_json(...)，照設計實作第一天就紅燈。程式端已改用 frame_json 並限縮檢查（帶入項 25） | 設計回補：區域變數改名，或檢查只禁止自 sqlalchemy 匯入的 text | New |
| R-08 | Minor | construction/brain-gateway/nfr-design/reliability-design.md 第 3.1 節；logical-components.md OPEN-GW13-20 | 前次 review-01 R-07 已提。raise EmbeddingProviderUnavailable ... from exc 的定位寫 embedding_port.py:614-618，應為 :617-621。程式端已更正（帶入項 24），設計文字未改 | 更正行號 | New |
| R-09 | Minor | construction/brain-gateway/nfr-design/observability-design.md 第三節 memory_busy；reliability-design.md 第 7.5 節末列 | 前次 review-01 R-10 與 R-11 已提。memory_busy 設計為 INFO 每 100 次一筆，上游 NFR13.5 逐字要求 WARNING 計數，且取代表未列；專案數超過 50 且原句掃描零命中時靜默依舊對象交辦，BR64.11 要防的失敗沒有使用者可見提示。程式端已改 WARNING 與不得靜默交辦（帶入項 27、28，偏離 D6） | 兩處設計回補，並列入核可揭露 | New |
| R-10 | Minor | construction/brain-gateway/nfr-design/scalability-design.md 第三節；performance-design.md 第 3.1 節 #13 | 前次 review-01 R-09 與 R-12 已提。被拒訊框無累計關閉條件（程式端已加 REJECTED_FRAMES_CLOSE_THRESHOLD=20，帶入項 29）；U12 在事件迴圈上的同步 Redis 與共用預設執行緒池使撤權窗口在 Redis 故障時放寬，程式端已揭露（帶入項 26），設計文字未回補 | 設計回補被拒訊框關閉門檻，並於 OPEN-GW13-4 指定負責人 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 設計與程式對照（brain_gateway.py MemoryWorker 實例屬性、EPISODIC_WAIT_SEC 第 107 行與 import 第 74 行；brain_gateway_rules.py BreakerState 第 534 到 570 行、RateLimiter admit_handshake 第 642 行） | 程式端對 R-01 到 R-04 皆已修正，且與 code-summary 帶入項 18 到 22 一致 | 各項皆為設計文字過期，正確的一邊是程式；設計原文照做會重現缺陷 |
| 凍結產出核對（nfr-design 目錄無 corrections 檔；scalability-design.md、logical-components.md 仍有「待裁決」殘字） | review-01 的 12 項中，設計文字未回補者仍在 | 前次發現已處置於程式，未處置於設計文件 |
| 未執行項目 | 依指示未執行測試、lint 或建置（避免產生快取）；未開啟其他單元的檔案 | 測試結果引用 code-summary 的紀錄（103 案 OK），未自行複驗 |
