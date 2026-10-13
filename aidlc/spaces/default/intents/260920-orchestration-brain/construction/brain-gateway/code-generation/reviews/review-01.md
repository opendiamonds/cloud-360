## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-13T15:56:40Z
**Iteration:** 1

### Scope and method

唯讀審查：只用讀檔、grep 與 `git diff`，未執行任何測試、dump 或腳本。`code-summary.md` 記錄的測試結果（95 案、15 項突變、全套 949 案）**未獨立執行**，以下僅引用不複驗。已逐段讀完 `backend/services/brain_gateway.py`（1572 行）與 `backend/services/brain_gateway_rules.py`（700 行），並核對 `main.py`、契約、`ws-contract.json`、`deploy.yml`、`DEPLOY.md`、`LOCAL-DEV.md`、`.env.example`、DEMO 移除的殘留，以及記憶、扇出、握手測試的實際斷言形狀。

### Findings

| ID | Severity | Status | Location | Finding | Required action |
|---|---|---|---|---|---|
| R-01 | Major | New | backend/services/brain_gateway_rules.py:436-466（scan_targets_in_utterance）；呼叫點 backend/services/brain_gateway.py:1233；測試 backend/tests/test_brain_gateway_rules.py:338 | 原句掃描在事件迴圈上同步執行，且複雜度為全部出現區間數的平方：_occurrences 允許重疊（rules.py:432 的 start = idx + 1），dominated 對每個區間掃過 all_spans（rules.py:459-462）。訊息上限是 4000 字（session_store.py:113）。已認證的使用者自建兩個系統「aa」「aaa」，再送由 a 組成的 4000 字句子，區間數約 8000，比較次數數量級 2×10^7（我推導，未執行），單次足以讓整個行程的所有 WebSocket、協作廣播與 SSE 停擺數秒；每分鐘 20 則的頻率上限擋不住持續停擺。掃描只在反問選定意圖後觸發，使用者要讓分類落到低信心才走得到，這是前提但不難。PBT 的句長只到 12 字（test_brain_gateway_rules.py:338），沒有任何上界測試。違反本檔禁令 2（事件迴圈上沒有同步重負載）的精神。 | 擇一或並用：把掃描放進 asyncio.to_thread；對區間數設上限（例如每個條目至多取前 N 個不重疊出現，或總區間數超限即視為零命中並走反問）；或改為排序後單次掃描線使複雜度降為 O(S log S)。並補一個最壞輸入（重複字元句子加前綴同名系統）的耗時或區間數上界測試。 |
| R-02 | Minor | New | backend/services/brain_gateway.py:813-831（_handshake_and_serve） | 載入中佇列溢位的檢查不完整：conn.overflowed 只在送 ready 之前（:813）與排空迴圈每次送出之後（:828）檢查。若溢位發生在 ready 與快照各訊框的 await 期間，deliver 已 unregister 並清空 pending（:665-667），迴圈因 pending 為空而直接跳過，之後無檢查就 conn.phase = Phase.READY（:831）。結果是一條已移出登錄卻仍在服務的連線，永遠收不到扇出，且無任何訊號。需 256 則在送約 6 至 10 個快照訊框之間到達，實務上極難觸發，但行為是靜默失效而非關閉。 | 在設定 Phase.READY 之前加一次 overflowed 檢查並以 1011 關閉；補一案讓溢位發生在快照送出期間。 |
| R-03 | Minor | New | backend/services/brain_gateway.py:954（_receive_loop 對 _dispatch_client_message 的呼叫）；:820（_snapshot_envelopes 無 try） | 接收迴圈與握手快照沒有最外層的例外保護。任何未預期例外（例如快照的 WorkItemsPayload 驗證失敗，或 _dispatch_client_message 某分支未被個別 try 包住）會一路穿出 handle()（只捕 WebSocketDisconnect，:749），由 ASGI 層以非結構化方式終止連線並記含 traceback 的 ERROR，而非 error(INTERNAL_ERROR) 加連線保留。finally 的清理本身正確（:751-772），不會洩漏佔位，所以只是行為與可觀測性問題。 | 在 _receive_loop 內對單則訊息的處理加 except Exception，轉成 error_for 的封閉表錯誤並繼續；握手階段的同類例外轉為 1011 關閉。補一案注入未預期例外，確認連線保留且 log 不含例外原文。 |
| R-04 | Minor | New | backend/services/brain_gateway.py:778-785（hello 的 ws.receive） | 首則 hello 訊框不受 MAX_FRAME_BYTES（64 KiB）與頻率限制約束：大小檢查與 rate.admit 只在 _receive_loop 內。已認證的使用者可在 10 秒內送出 uvicorn 允許的最大訊框（預設 16 MiB，NFR13.19 明言不動 ws_max_size）再 json.loads，每使用者最多 10 條、全域 200 條。需要有效 token，風險有限，但與 NFR13.19 宣稱的入站單一訊框上限不一致。 | 在 hello 路徑套用同一個位元組上限（超過即 4400 或 1011）；或在 code-summary.md 揭露此例外。 |
| R-05 | Minor | New | backend/services/brain_gateway.py:672-675（fanout）、:554-558（emit_turn）、:99（SEND_TIMEOUT_SEC） | 扇出對同一使用者的各連線依序 await，且每次送出最長等 10 秒。同一 key 下某個分頁卡住（未失敗、只是慢）會讓其他分頁的狀態訊息與推播延遲至多 10 秒乘以前面卡住的分頁數（上限 10 條連線）。M7 只驗證失敗不影響其他連線，沒有驗證變慢。範圍僅限同一使用者，且 U12 的 dispatch 也在等這個 sink。 | 在 code-summary.md 揭露此行為；或以 asyncio.gather 並行送出（每連線順序由 send_lock 保證）。補一案：一條連線的 send_text 卡住時，第二條連線仍在秒級收到訊息。 |
| R-06 | Minor | New | backend/services/brain_gateway.py:1237-1240；code-summary.md 偏離 D6 | 偏離 D6 如實揭露且理由合理，但它確實讓帶入項 28 的字面要求（掃描零命中不得靜默交辦舊對象）在專案 > 50 且已選定專案時失效：使用者點名了另一個專案的系統，因目錄截斷而不在候選內，掃描零命中，直接交辦給目前選定的專案。高信心路徑（:1261）對同一情境回專案太多，兩條路徑行為不一致。code-summary.md 自己寫請核可，本次審查不代替人工核可。 | 閘門上請使用者明確核可或否決 D6；若核可，在 U14 交接表與 functional-spec.md 回補註明這個殘留，並補一案鎖住已選定專案、截斷、零命中則交辦的行為，使其成為有意的決定而非巧合。 |
| R-07 | Minor | New | deploy/render-env.sh:21；.github/workflows/deploy.yml:76-83、91-93 | render-env.sh 檔頭仍寫 OPENROUTER_API_KEY optional（empty disables generation），而同一個 PR 已讓 deploy.yml 的必要 secret 檢查把它列為必要，DEPLOY.md:24 與 deploy/.env.example 也已改。該腳本刻意不檢查（讓回滾可 render）是對的，但檔頭註解現在與 workflow 矛盾，下一位維護者讀 render-env.sh 會得到相反結論。code-summary.md 的取代關係表也未列這一處。 | 在 render-env.sh 檔頭該行補註 staging 部署由 deploy.yml 強制必要、此腳本接受空值僅為讓 rollback 可 render，並同步 code-summary.md。 |

### Verification of the 37 carried items (read from code, not from test names)

- 項 1、2、11（最長完整名稱、系統吸收專案、同名互不支配）：已做到，效能缺口見 R-01。證據 brain_gateway_rules.py:436-466、:386-397；掃描命中一律走 _clarify_target（brain_gateway.py:1234-1236）。
- 項 3（取空佇列到 ready 無 await）：已做到，溢位例外見 R-02。證據 brain_gateway.py:824-831。
- 項 4、13、28（專案 > 50）：已做到，D6 為已揭露的窄化（R-06）。證據 brain_gateway.py:1237、1244-1246、1261。
- 項 5、8（熔斷只認逾時與連線類且走例外鏈）：已做到。證據 rules.py:483-515（__cause__ 與 __context__ 廣度走訪，深度 5）、BreakerState.on_failure rules.py:561-568。
- 項 18（Critical，半開試探在所有未執行出口清 probing）：已做到。證據 brain_gateway.py:399-403（BUSY_SKIPPED）、:423-424（submit 失敗）、:433-436（取消）；失敗路徑由 on_failure 清除（rules.py:563）。
- 項 19（CancelledError 重拋）：已做到。證據 brain_gateway.py:432-436。
- 項 15、22（號誌在工作執行緒 finally 歸還、實例屬性）：已做到；未開始即取消的洩漏已自行修正。證據 brain_gateway.py:388-389、:407-428；done callback 僅在 cancelled() 時歸還，與 _job 的 finally 互斥，不會雙重歸還。
- 項 7（全域佔位在第一個敘述、每 key 在認證後 accept 前、finally 釋放）：已做到。證據 brain_gateway.py:695、:732-737、:762-764。
- 項 20（頻率窗跨重連保留、握手納入限流）：已做到。證據 rules.py:590-661（forget_connection 只刪每連線窗與被拒窗）、brain_gateway.py:728。
- 項 21（送出失敗 close 1011）：已做到。證據 brain_gateway.py:244-249。
- 項 29（被拒訊框計入關閉門檻）：已做到。證據 brain_gateway.py:914、918、928 到 _reject :956-966。
- 項 9（時間只經 GatewayTiming）：已做到。證據 brain_gateway.py:164-170；AST 測試在 test_brain_gateway_limits.py。
- 項 16（單行程守門）：Dockerfile 的 CMD 無 worker 旗標（backend/Dockerfile:30）；測試 test_brain_gateway_startup.py:148。
- 項 30、32、35（部署與文件）：已做到，唯 R-07 的註解漂移。證據 deploy.yml、DEPLOY.md:24、deploy/.env.example、backend/requirements.txt。
- 項 31、33（DEMO 移除）：已做到。在 backend/services、backend/main.py、backend/tests、frontend/src、frontend/tests 內 grep brain_router、BrainPage、DEMO SCOPE 只剩註解與兩支已刪除斷言；/brain 無路由殘留；source-manifest.json 的 30 筆與 git 狀態一致。
- 項 10、12、14、17、23、26、34、36、37（文件類）：已寫入 code-summary.md 第五至八節；項 34（合併前確認 secret）正確地留給使用者。

### Security check

- token 不入 log：_log 以白名單限定欄位（brain_gateway.py:130-156），白名單內無 token、文字、回覆；Connection.token 與 principal 皆 repr=False（:216-217）。
- 回應標頭只回送協定名：ws.accept(subprotocol=rules.PROTOCOL_NAME)（:737），解析以第一個 . 切分（rules.py:114）。
- 每則訊息重驗 record=True（:933），背景重驗 record=False（:885），K1 於握手與每則重驗皆判定（:685）。
- prompt_guard 先於預取與分類（:1084-1086）；錯誤訊息只取自封閉表（rules.py:285-304，不含 str(exc)）。
- 殘留風險已由 D2 揭露：認證本身的 DB 成本在握手頻率限制之前（brain_gateway.py:713 對 :728）。

### Deviations and test adequacy

D1 至 D13 皆有理由，D2、D3、D5、D6 已明確要求核可。未發現完全未揭露的偏離；R-04、R-05 屬設計宣稱與實作範圍有落差但未列入揭露，已列為 Minor。D5（PREFETCH_WAIT_SEC 暫定 3.0）與 D12、D13（部分斷言由程式結構保證）為誠實的缺口紀錄，不構成阻擋。

測試抽查（只讀未跑）：記憶與熔斷測試使用真實 MemoryWorker、BreakerState 與 FakeTiming，不是只驗替身；test_breaker_opens_on_wrapped_timeout_only_and_recovers 以 raise from httpx.ReadTimeout 構造實際例外鏈並斷言預取次數 1、2、2、3；另有 test_real_ollama_adapter_preserves_httpx_cause 鎖住真實包裝形狀。突變表 M1-M10 與 X1-X5 的設計對應到各 Critical 與 Major 項目，形狀合理。唯一明顯缺口是效能最壞情況（R-01）。

### Summary

37 項帶入、契約增量 C-1 至 C-7（ws-contract.json 與模型一致）、DEMO 移除與三環境設定都實作得紮實，Critical 項目（熔斷活性、取消、號誌、佔位時序）在程式上都成立。阻擋原因只有一項：R-01 的原句掃描在單一事件迴圈上有平方級的最壞情況，已認證使用者可用它讓整個行程停擺。計數：Critical 0、Major 1、Minor 6。測試結果引用 code-summary.md，未獨立執行。
