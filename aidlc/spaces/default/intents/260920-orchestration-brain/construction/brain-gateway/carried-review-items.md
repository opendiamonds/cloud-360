# U13 brain-gateway — 帶入 code-generation 的必做項

## 來源：functional-design reviews/review-03.md（使用者 2026-10-13 裁決：停止送審，帶入 code-generation）

1. [Major R-01] BR64.13 句中名稱掃描不得用子字串比對：改為「最長完整名稱」比對（含邊界判斷），且命中後不得靜默改動作業對象——一律以反問請使用者確認（沿用 BR64.11 的 target 反問）；同專案下名稱互為子字串（「訂單」與「訂單系統」）時取最長者。高信心路徑與低信心路徑的處置一致性寫明理由或統一。
2. [Minor R-02] PBT 性質五與 BR64.13「專案名命中在系統命中時不另計」的矛盾：以程式為準統一，性質改寫成可失敗的版本；BR64.9 與 BR64.13 對「專案與其系統同名」的處置統一。
3. [Minor R-03] BR63.2 排序：佇列取空到 phase 改為 ready 之間不得有 await（或改成在同一個無 await 區段內完成），並以測試鎖住「送出暫存佇列期間新到的訊息」順序。
4. [Minor R-04] 專案數超過 50 時：不得回「找不到系統」的不實句型，改為「專案太多，請先在脈絡列選定專案」；traceability 的 AC1.1.5 註記列出此條件。
5. [Minor R-05] BR67.12 熔斷器：改為只在逾時／連線類錯誤開啟、或改為以使用者為鍵；3 秒等待依 Ollama 冷載實測調整並寫入理由；執行器佇列設上限，超出即跳過預取。
6. [Minor R-06] LOCAL-DEV.md 同步（project.md Mandated）：REDIS_URL／REDIS_USER／REDIS_PASSWORD 成為後端啟動必要條件，更新 LOCAL-DEV.md:23-24 的 Redis 描述與啟動拒絕條件清單。

另：AC8.1.1 Deferred（OPEN-GW13-15，交使用者裁決：改寫 AC 或追加串流 LLM 回覆）。

## 來源：nfr-requirements reviews/review-01.md（使用者 2026-10-13 裁決：帶入 code-generation）

7. [Major R-01] 連線上限（NFR13.17／13.18）改為握手一開始即佔位計數（accept 前），握手失敗或關閉即釋放；測試以併發握手（同時 N+1 條）驗證，不只循序。
8. [Major R-02] 記憶熔斷器（NFR13.25）的開啟條件改認實際例外 `EmbeddingProviderUnavailable`（`embedding_port.py:614-618`）及其包裝的逾時／連線類；寫入路徑等待 15 秒 > 嵌入預設 10 秒逾時的落差須處理；測試替身拋實際例外類型並揭露替身限制。
9. [Minor R-03] 建構子注入 clock／sleep，使 60 秒重驗、滑動視窗、30 秒熔斷可在測試中推進。
10. [Minor R-04] U14 的重連退避義務補進 functional-spec §十一之四（或交接表），不得宣稱已列。
11. [Minor R-05] NFR13.28 性質 (c) 排除不同專案下的同名對象（區間相同不算覆蓋）。
12. [Minor R-06] NFR13.25／13.27／13.28／13.5 對 BR64.13、BR64.9、BR67.12 的改寫須在 code-summary 列出取代關係；NFR13.27（掃描命中一律反問）與 NFR13.28（高信心路徑同名收斂為系統）的一致性寫明。
13. [Minor R-07] NFR13.21「專案太多」句型只在句中確實指名對象、且無法在 50 個以內解析時才出現；未指名對象且已有作業對象時照常交辦。
14. [Minor R-08] 預算 P50 不可相加——改述為各段獨立的預算，NFR13.1 的量測落點（build-and-test）明寫為本站無法判定。
15. [Minor R-09] NFR13.5「同時至多 4 個」以實際執行緒完成計數，非 wait_for 逾時。
16. [Minor R-10] 單行程守門（NFR13.33）另檢查 `WEB_CONCURRENCY`／`UVICORN_WORKERS`。
17. [Minor R-11]（**經 nfr-design `[GWND1]`=A 更正**）：維持 `[GWN1]`=A——第 11 條連線拒絕、已開分頁不受影響；U14 退避重試至少持續 60 秒以等待舊登錄釋放。原轉述「關閉最舊連線」多走一步、推翻 [GWN1]=A，已撤回。移除「（若採用）」殘字。

## 來源：nfr-design reviews/review-01.md（使用者 2026-10-13 裁決：帶入 code-generation；Critical／Major 各配一個先紅後綠的突變測試）

18. [Critical R-01] 熔斷器半開試探：`admit` 設 `probing=True` 後，任何未執行試探的出口（含執行器滿而 `BUSY_SKIPPED`）都必須清除 `probing`（或不在滿載時佔用試探名額）；加不變量「probing 不會在無進行中試探時維持為真」並以測試鎖住熔斷可恢復。
19. [Major R-02] `MemoryWorker.run` 不得以 `except BaseException` 吞掉 `CancelledError`——取消一律重新拋出（與 reliability-design §五一致）。
20. [Major R-03] 訊息頻率視窗不得因最後一條連線關閉而刪除（以使用者為鍵保留至視窗過期）；握手本身也納入速率限制。
21. [Major R-04] 送出失敗或逾時的連線：取消登錄的同時必須主動 close（附 1011），不得只移除登錄。
22. [Major R-05] `_executor`／`_slots` 不得為類別屬性；改為實例（隨 gateway 元件建立與關閉），shutdown 只關自己的執行器。
23. [Minor R-06] 各檔「待裁決」殘字更新為 [GWND1]=A；U14 退避重試至少 60 秒列為對 U14 的交接義務。
24. [Minor R-07] `embedding_port.py` 引用行號改為 `:617-621`。
25. [Minor R-08] AST 規則與 `send_direct` 內的變數名 `text` 衝突——擇一修正。
26. [Minor R-09] 揭露：U12 在事件迴圈上的同步 Redis 呼叫；auth／重驗與 Redis 共用預設執行緒池，Redis 故障可能延遲撤權。
27. [Minor R-10] episodic 跳過的觀測：與 NFR13.5 的 WARNING 計數一致，或在取代關係表列出改動。
28. [Minor R-11] 專案超過 50 個、句中名稱掃描零命中時不得靜默交辦給舊對象——回固定句請使用者先選定專案。
29. [Minor R-12] 被拒的訊框（過大、過頻）計入關閉連線的門檻。

## 來源：infrastructure-design 使用者裁決（2026-10-13）

30. [IG1=A] `OPENROUTER_API_KEY` 列入 `deploy.yml` 既有的「必要 secret 檢查」，不加進 `render-env.sh` 拒絕清單（rollback 仍可執行）。屬 CI/部署變更，在 U13 code-generation 計畫列出並同 PR 揭露。
31. [IG2=A] 本分支第一次合併進 `ut` 時就移除 DEMO 後端 `brain_router.py`（含 `main.py:7`、`:110-112`）或關掉回送 token 的寫法；若 U13 尚未完成，示範頁暫時不可用。

## 來源：infrastructure-design reviews/review-01.md（使用者 2026-10-13 裁決：帶入 code-generation；IG1／IG2 決定不變）

32. [Major R-01] 本站四份產出未反映 IG1=A／IG2=A：code-generation 以本清單第 30、31 項為準，須改 `deploy.yml:71-91`（必要 secret 檢查）、`deploy/.env.example`、`DEPLOY.md:24`，並依 project.md 規則同步 `LOCAL-DEV.md`；`render-env.sh` 不加入拒絕清單。
33. [Major R-02] 移除 DEMO 的完整觸點（同一 PR）：`backend/services/brain_router.py`、`main.py:7`、`main.py:110-112`、前端 `BrainPage.tsx`、`App.tsx:89-99`、`Sidebar.tsx:211-217`；e2e `member-pages.spec.ts`（8 處）與 `memory-page.spec.ts`（2 處）的 `page.goto('/brain')` 落地頁改為中性頁；`test_intent_routing_structure.py:62`、`:315-345` 對 brain_router 的讀取改寫；註解 `eslint.config.js:32`、`intent_routing_types.py:48` 更新。
34. [Major R-03] IG1 上線順序：合併前先以 `gh api repos/<owner>/<repo>/actions/secrets` 確認 `OPENROUTER_API_KEY` 存在且為 secret（非 variable）；未設定前不得合併含必要檢查的變更，避免部署失敗觸發整分支回滾。
35. [Minor R-04] 實測腳本與 WS keepalive 依賴的 `websockets` 未直接釘選（僅經 langgraph-sdk／langsmith 傳遞）；於 requirements.txt 明列或揭露。
36. [Minor R-05] L2 回退的 `proxy_set_header Sec-WebSocket-Protocol` 實為 no-op，刪除或改寫 L2 失敗時的真正處置。
37. [Minor R-06] 實測步驟的 token 處理：以 `read -s` 取得並 `export`、不經 argv（curl 改用 `-H @file` 或 stdin）、輸出只印必要標頭並遮罩。
