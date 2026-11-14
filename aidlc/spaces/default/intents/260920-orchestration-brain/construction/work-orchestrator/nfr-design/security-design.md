# 安全設計 — `U12 work-orchestrator`

> 承接 `NFR12.6`–`NFR12.11`。

## 一、token 的生命週期（`NFR12.6`）

- token 只以參數傳入 `dispatch`／`correct`／`list_items`，存在 `_run` 的區域變數與 `httpx` 請求標頭；不進
  `WorkItem`、不進 `_tasks` 以外的任何結構、不進 log 格式字串。
- 例外處理：捕捉 `httpx` 例外時只記例外**類別名**與 HTTP 狀態碼，不記 `str(exc)`（`httpx.HTTPStatusError` 的訊息含
  請求 URL 與部分標頭）。測試涵蓋「token 出現在例外訊息」的案例（帶入項 17）。

## 二、帶使用者本人的 token 呼叫（`NFR12.7`）

- 每次 `_run` 建一個 `httpx.AsyncClient(transport=ASGITransport(app=self._app), base_url="http://brain.internal",
  headers={"Authorization": f"Bearer {token}"})`，用完即關。不建全域共用 client（避免標頭在使用者間串用）。
- 401 → `BR51.6`；403 → `BR51.3`；兩者都不重試（`NFR12.23`）。

## 三、不得同進程直呼既有能力（`NFR12.8`、`NFR12.5`；帶入項 14）

- 以 import 圖檢查取代純字串 grep：測試載入本單元模組後，遞迴走訪其 `__dict__` 中的模組物件與 `sys.modules` 中由本模組
  觸發新載入的模組，斷言集合不含 `cost.estimate_intake_service`、`cost.advice_orchestrator`、`services.design_agent`、
  `services.review_orchestrator`、`services.collab_router`、`services.llm_provider`。並 grep `importlib`／`__import__`
  在本單元模組為 0。

## 四、Principal 重鑄與停用判定（`NFR12.9`；帶入項 5、10）

- `_call_facade` 內：`user = db.get(User, user_id)`；`user is None or not user.is_active` → 拋 `_UserDisabled`；否則
  `principal = mint_principal(user)`。**停用判定由本單元自寫**——`mint_principal` 不檢查 `is_active`。
- `_UserDisabled` 的處置依步驟分兩類：
  - **存回之前**（目標圖解析 `list_diagrams_of_system`）→ 工作項失敗，句型同 `BR51.3`。
  - **存回之後**（`record_diagram_change`、`MemoryFacade.write`）→ 不改 status，依 `BR51.4`／`BR51.5` 的
    violation_behaviour（sideEffect 註明「變更紀錄未寫入」、記憶寫入失敗只記 log）。
- 測試案例放在「PUT 成功之後、寫變更紀錄之前」停用使用者：有重鑄 → 變更紀錄未寫入且 sideEffect 有註明；沒重鑄（沿用
  握手快照）→ 變更紀錄照寫。這個案例才分辨得出有沒有重鑄。

## 五、輸出不洩漏（`NFR12.10`、`NFR12.11`）

- 所有使用者可見文字來自單一常數表 `_PHRASES`（`BR58.1` 的全部句型，含「〈label〉沒有執行：前一項〈label〉已停掉」；
  帶入項 8），失敗原因只能是表內的鍵。
- log 只記 workItemId、capability、狀態、dispatchStage、失敗類別；不記 `requestText`、label 以外的使用者內容。

## 六、ADR-0006 四面向

與 `../functional-design/functional-spec.md` 第七節一致（修訂 2）。Encryption 的兩處使用者內容落地（`requestText` 於
Redis、需求摘要於 DB）併入上游 `OQ-3`；`OQ-3` 的承接站 `nfr-design` 為 CONDITIONAL，被 skip 時轉 `infrastructure-design`
（Redis 部署面）與 `code-generation`（ALWAYS）（帶入項 15）。本單元**不另定**加密手段。
