# U12 work-orchestrator — 帶入 code-generation 的必做項（來源：functional-design reviews/review-03.md）

使用者 2026-10-12 裁決：停止送審，以下 6 項在 U12 code-generation 計畫列為必做，並在該站審查 brief 點名複驗。

1. [Major R-10] BR55.7 與 correct 取消 task 矛盾：persisting 階段的 PUT 不得被 correct／BR56.6 逾時取消後失去回應。
   做法：PUT 與其後的「寫變更紀錄＋更新 sideEffect」包成 asyncio.shield 保護的收尾協程（或獨立 task），correct 只取消 persisting 之前的步驟。
2. [Major R-11] 復原掃描（BR56.7）與 BR53.2／BR53.4 推進：只有 update_work_item 回 True 的呼叫者才啟動背景執行、才送訊息；回 False 者不做任何副作用。逾期失敗訊息同理只送一次。
3. [Minor R-12] 背景執行順序：先以 CAS 寫 dispatchStage=request_sent 成功，才送出 A1／A3／PUT 請求；寫入失敗即中止不送。
4. [Minor R-13] CAS 的 new_item 一律由 Lua 讀到的當前值合併（腳本內只覆寫呼叫端指定的欄位），避免 estimateSetId 等被過期值覆寫；Lua 寫入重試時以「已是目標值」視為成功（冪等）。
5. [Minor R-14] BR51.7 停用判定只在「尚未存回」的步驟生效；存回之後（BR51.4／BR51.5）的 facade 失敗不改 status，沿用各自的 violation_behaviour。
6. [Minor R-15] 推進為處理中時寫 deadlineAt、清 waitingOn／dependsOn；離開處理中清 deadlineAt；BR56.7 與 BR56.6 的 sideEffect 統一引用 BR55.1 對照表；BR58.1 增「〈label〉沒有執行：前一項〈label〉已停掉」句型（BR53.4 已有字面，對齊到 BR58.1）。

另：AC1.3.2／AC5.1.3／AC10.2.4 為 Deferred，交使用者裁決（OPEN-WO12-6、OPEN-WO12-7）。

## 帶入項（來源：nfr-requirements reviews/review-01.md，使用者 2026-10-12 裁決帶入 code-generation）

7. [Major R-01] NFR12.12 模型測試的操作字母表加入「BR56.3 寫 estimateSetId」，性質 (c) 才能失敗；兩支 Lua 一律 idempotent=False（或腳本內以目標值判定冪等），並以測試鎖住。
8. [Major R-02] deadlineAt／waitingOn／dependsOn 的清理以實體不變量測試承載（不靠 transition）；統一 BR56.7 與 BR55.1 的 sideEffect 對照（persisting → 「可能已存回…」）；BR58.1 的全部句型（含檢視被跳過）列成常數並各有一案。
9. [Major R-03] Lua 原子性：新增對真實 Redis 的整合測試（或 Lua 與 Python 參考實作的一致性測試），並在測試計畫揭露 fakeredis／替身的限制。
10. [Major R-04] 停用判定由本單元自寫（mint_principal 不查 is_active）；NFR12.9 的案例改在「PUT 之後、記變更紀錄之前」停用，才能分辨有沒有重鑄。
11. [Major R-05] persisting 階段逾時：PUT 收尾以 shield 保護並在逾時後仍補寫變更紀錄＋sideEffect；需要一條規則與一個測試。
12. [Minor R-06] 「先記錄才送出」同樣適用 persisting（先寫 persisting 成功才 PUT）。
13. [Minor R-07] 時鐘：wait_for 與 deadlineAt 用同一個注入的 clock；測試以注入時鐘＋可控的 sleep 實作，不依賴不存在的假時鐘工具。
14. [Minor R-08] NFR12.5／12.8 的 grep 判準補 importlib／動態 import 與間接模組的檢查（或改為 import 圖檢查）。
15. [Minor R-09] requestText 靜態加密：OQ-3 的承接 nfr-design 為 CONDITIONAL，寫明 skip 時轉 code-generation／infrastructure-design；NFR7 的判定措辭對齊。
16. [Minor R-10] NFR5 承接改為「訊息由 brain_ws_contract 模型建構」的生產路徑檢查（非只測試 sink）；functional-spec 第七節「三個純函式」應為四個（回報）。
17. [Minor R-11] NFR12.6 補 token 出現在例外訊息／失敗路徑的案例；NFR12.23 補 401／403 不重試與輪詢 404 的邊界。

## 帶入項（來源：nfr-design reviews/review-01.md，使用者 2026-10-12 裁決帶入 code-generation）

18. [Major R-01] `_finish_persist` 自建獨立的 AsyncClient（不共用 `_run` 的 client），被 shield 保護的整段含 client 生命週期。
19. [Major R-02] 非冪等 Lua 遇連線錯誤（SessionBackendUnavailable）時結果未知：`_advance` 增第三分支「重讀確認」——重讀後以目標狀態判定是否已套用，無法讀取則不做副作用並記 WARNING。
20. [Major R-03] 時間注入涵蓋三種能力：牆鐘上限一律以注入的 clock＋sleep 自行判定（不用 asyncio.wait_for 的迴圈時鐘），NFR12.19 測試可推進注入時鐘；寫明輪詢計數規則（每次 GET 計一次）。
21. [Major R-04] 「不得直呼既有能力」檢查改為 AST 掃描本單元原始碼的 import／from-import（含 `main`），並加一個測試斷言對外只經 ASGITransport（攔截 httpx 其他 transport）。
22. [Minor R-05] SessionLocal 以建構子注入的 session factory 取得；`list_diagrams_of_system` 為 U7 的新增依賴，code-generation 時一併實作並標明跨單元修改。
23. [Minor R-06] `_finish_persist` 自有最外層例外處理與 PUT 逾時上限。
24. [Minor R-07] Lua 補丁合併：null 值語意（明確設 null）、cjson 空陣列處理、CAS 失敗後重試上限。
25. [Minor R-08] 回報 functional-design 的偏離：BR55.7 延伸至逾時失敗項；重啟後 persisting 孤兒的稽核缺口（無法補寫變更紀錄）如實揭露。
26. [Minor R-09] traceability 修正：NFR12.19 指向 reliability-design；NFR12.27／12.29 補設計內容；帶入項 7–17 的落點寫進 code-generation 計畫。
