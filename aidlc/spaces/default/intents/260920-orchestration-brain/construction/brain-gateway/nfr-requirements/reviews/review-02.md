## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本補審以舊審查 review-01（NOT-READY，2 Major、9 Minor）為基準，確認凍結的 nfr-requirements 產出對這 11 項的處置。產出本身自洽：NFR13.1 至 NFR13.44 皆有二元判準與突變驗證，預算算式 400+800+300+500=2000 正確，帶入項 1 至 6 皆有承載，ADR-0006 四面向各有落點。凍結的產出文字沒有修改，舊的 11 項發現在文字上仍然存在；但已落地的程式（brain_gateway.py、brain_gateway_rules.py、test_brain_gateway_startup.py）對其中最嚴重的幾項已經用更強的做法處理（先預留名額、依 __cause__ 鏈分類熔斷、掃 WEB_CONCURRENCY）。因此現況是「設計文字落後於程式」，程式那一邊才是對的。Major 共 2 項、Critical 0 項，依規則判 READY；這兩項 Major 的實際風險已被程式消除，剩下的工作是讓凍結文字不誤導下游。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/brain-gateway/nfr-requirements/scalability-requirements.md > NFR13.17 與 NFR13.18（前次 review-01 R-01 已提） | 兩條上限仍寫成「以登錄連線數為準、認證之前／accept 之前檢查」，判準只有序列情境（先建 200／10 條再試下一條），抓不到並發握手的 check-then-register 競態。程式端已不同：brain_gateway.py:274 與 :283 的 try_reserve_total／try_reserve_key 先預留名額，:749 註明預留之前無 await，:816-817 在失敗路徑釋放，所以程式這一邊是對的、設計文字是錯的。凍結文字沒有並發案例，也沒有預留與釋放的要求，下游或後續維護者照文字重寫會退回有競態的做法 | 在承載處補一條取代說明：NFR13.17、NFR13.18 以「無 await 的預留名額、涵蓋 accept 到登錄、所有關閉路徑釋放」為準，並補並發判準（認證替身讓出事件迴圈、同時 N 條握手、hello 逾時 4400 也釋放）。確認 test_brain_gateway 系列測試已含此並發案例，若無則補 | New |
| R-02 | Major | construction/brain-gateway/nfr-requirements/reliability-requirements.md > NFR13.25（連帶 NFR13.24、NFR13.37 與 tech-stack-decisions.md NFR13.44；前次 review-01 R-02 已提） | 熔斷開啟條件仍列 TimeoutError、httpx.TimeoutException、httpx.ConnectError、ConnectionError，判準用替身直接拋這些型別。真實嵌入路徑把 httpx 錯誤統一包成 EmbeddingProviderUnavailable（embedding_port.py 的 K-06 單一例外），照條文字面，Ollama 停擺的主要失敗形式不開熔斷，且測試因替身拋清單內型別而全綠。程式端 brain_gateway_rules.py:490 已改為沿 __cause__／__context__ 鏈（深度 ≤ 5）找逾時或連線類，:567-574 的 on_failure 以 is_transient_memory_failure 判定，程式這一邊是對的。凍結文字與程式不一致，且未揭露替身與真實例外分類不同 | 以取代說明把 NFR13.25 的開啟條件改為「依 __cause__ 鏈判定的暫時性失敗」，判準改用真實 EmbeddingProviderUnavailable（httpx.MockTransport 造逾時與連線被拒）；寫明寫入等待上限與 EMBEDDING_TIMEOUT_SEC 的關係（15 秒大於 10 秒僅在預設值成立） | New |
| R-03 | Minor | construction/brain-gateway/nfr-requirements/reliability-requirements.md > NFR13.27、NFR13.28、NFR13.25、NFR13.5（對照 functional-design/rules.md 的 BR64.13、BR64.9、BR67.12；前次 review-01 R-06 已提） | 四條 NFR 實質改寫已核可的 BR 文字（掃描命中一律反問、同名吸收、熔斷只開暫時性、在途至多 4），functional-design 凍結，檔內沒有優先順序記錄，下游會同時讀到兩套互斥文字。另 NFR13.27 以「不得靜默改動作業對象」為由要求反問，NFR13.28 卻在高信心路徑把專案與其同名系統靜默收斂成系統，兩者內在張力未說明 | 補一張「NFR 取代 FD 文字」對照表（BR 編號、被取代句、取代它的 NFR），並說明高信心同名收斂為何不反問 | New |
| R-04 | Minor | construction/brain-gateway/nfr-requirements/reliability-requirements.md > NFR13.28 性質 (c)（前次 review-01 R-05 已提） | 性質 (c)「任兩個對象的名稱區間互不完全覆蓋」未限定嚴格覆蓋；同條又規定不同專案的同名對象仍為多筆，兩者區間相同、互相完全覆蓋，正確實作會讓 (c) 紅燈 | (c) 改為「不存在區間嚴格長於且完全覆蓋另一對象區間的結果對」，並加入跨專案同名的 example | New |
| R-05 | Minor | construction/brain-gateway/nfr-requirements/scalability-requirements.md > NFR13.21（前次 review-01 R-07 已提） | 專案數超過 50 時「referent 或原句零筆相符」改回「專案太多」，但原句掃描零筆是常態（句中沒點名對象，依當前作業對象交辦），照字面會拒絕合法交辦；判準只測 referent 分支 | 拆開兩個分支：已有作業對象時零筆照常交辦，只有 referent 非空而目錄因超限無法比對時才回「專案太多」，補原句分支判準 | New |
| R-06 | Minor | construction/brain-gateway/nfr-requirements/performance-requirements.md > 第一節預算圖與 NFR13.1（前次 review-01 R-08 已提） | 三段各為 P50 預算，P50 不可相加；保留的 500 ms 才承擔尾部。NFR13.1 在本階段只驗計時欄位存在，實際門檻依賴 requirements.md:716 的 N-3 量測機制，該機制尚未存在，也未指定承接者與缺席時的處置 | 預算圖加一句「各段為 P50 預算、非可加量」，指明 N-3 缺席時由 build-and-test 誰補 | New |
| R-07 | Minor | construction/brain-gateway/nfr-requirements/performance-requirements.md > NFR13.5（前次 review-01 R-09 已提） | 「同時在途至多 4 件、不排隊」以 ThreadPoolExecutor(max_workers=4) 實作時，executor 佇列無界，必須另有計數器；asyncio.wait_for 逾時後執行緒仍佔工作者，若計數在逾時就遞減，新工作會在 executor 內排隊，判準沒涵蓋逾時放棄後的計數 | 明寫計數以執行緒實際結束為準（done callback 遞減），加一案：預取逾時放棄後立即再送訊息 | New |
| R-08 | Minor | construction/brain-gateway/nfr-requirements/reliability-requirements.md > NFR13.33（前次 review-01 R-10 已提） | 條文只讀 Dockerfile 的 CMD 與兩份 compose 的 command，沒有涵蓋 WEB_CONCURRENCY 與 UVICORN_WORKERS 環境變數。程式端的 test_brain_gateway_startup.py:172-177 已掃這兩個名稱、env_file 與 environment，程式這一邊較完整；凍結文字落後 | 以取代說明把判準擴充為涵蓋兩個環境變數名稱、env_file 與 backend/.env.example | New |
| R-09 | Minor | construction/brain-gateway/nfr-requirements/scalability-requirements.md > 第一節數值理由「拒絕形狀選不 accept」（前次 review-01 R-04 已提） | 文中稱 U14 重連須有上限退避「已列入 functional-spec.md 十一之四的同一清單」，前次審查實查該節只有四項配合事項，無退避條目；凍結文字敘述了不存在的記錄。同段「10（若採用）」仍是草稿措辭，且 10 的算式剛好等於上限、零餘裕，未討論伺服器端尚未偵測斷線的殘留連線（前次 R-11） | 把退避要求寫進 U14 讀得到的承載處（carried-review-items.md 對 U14 的事項），更正該句的指稱；刪除「若採用」並補殘留連線窗口估算 | New |
| R-10 | Minor | construction/brain-gateway/nfr-requirements/reliability-requirements.md、security-requirements.md、scalability-requirements.md、observability-requirements.md > 各條「假時鐘推進」判準（前次 review-01 R-03 已提） | 重驗 60 秒、滑動窗 60 秒、熔斷 30 秒的判準都依賴假時鐘，NFR 未規定時鐘與睡眠的注入點。程式端已有 GatewayTiming（brain_gateway.py:388 起 breaker 使用 self._timing.monotonic()）與 RateLimiter 由呼叫端傳入 now，這一項在程式端已落實，只是設計文字沒有記錄 | 在 tech-stack-decisions.md 補一條注入點說明與「改 60 秒常數必紅燈」的突變驗證 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 算術重算（預算圖） | 400+800+300+500=2000 | 與文中一致，無誤 |
| NFR13.x 編號連續性（讀 review-01 的驗證結果並抽查檔內） | NFR13.1 至 NFR13.44 | 無重複或遺漏，上次審查已核對，凍結文字未變動 |
| 程式抽查：連線預留 | brain_gateway.py:274、:283、:749、:786、:816 | 以預留取代先檢查後登錄，證實 R-01 的風險在程式端已消除，設計文字落後 |
| 程式抽查：熔斷分類 | brain_gateway_rules.py:490-518、:567-574 | 沿 __cause__ 鏈判定，證實 R-02 的風險在程式端已消除，設計文字落後 |
| 程式抽查：單一行程守門 | test_brain_gateway_startup.py:172-177 | 已掃 WEB_CONCURRENCY、UVICORN_WORKERS，優於設計文字 |
| 未執行測試 | 依指示不跑測試，不寫快取 | 判準是否可失敗以讀碼推演；兄弟單元檔案被範圍限制，U11 的 NFR3.60 與 U10 的 NFR2.41 引用未獨立核對 |
