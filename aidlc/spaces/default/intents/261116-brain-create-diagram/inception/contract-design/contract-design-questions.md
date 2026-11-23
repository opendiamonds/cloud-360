# Contract Design — 問題檔

> 上游已定案、不重問：需求（修訂 2）、領域設計（修訂 1，ADR-001～009）、工作單元（修訂 1：U1 diagram-drafts、U2 brain-create-flow、U3 draft-ui，同一批合入）。
> 由 repo 事實定案、不重問：**整合機制**——U1↔U2、U1↔U3 為同一個 backend 內的 HTTP API（經 `CapabilityClient` 同行程 ASGI 呼叫或前端 fetch），U2↔U3 為既有 `/api/brain/ws` 的 WebSocket 訊息；**契約擁有者**——提供端單元擁有其規格（U1 擁有架構圖 API、U2 擁有反問訊息）；**版本政策**——沿用 repo 既有作法：不加版號，以 `openapi.json` 與 `dump_ws_contract` 的漂移檢查把關，新增欄位一律選填、消費端忽略未知欄位。本 intent 沒有對外（系統外）API。

## 出題前查證（唯讀；檔:行為 2026-11-17 `origin/ut`）

- 存檔 API：`PUT /api/collab/diagrams/{diagram_id}`（`backend/services/collab_router.py:581`），請求為 `SaveDiagramRequest{xml_data, title}`（`:317-319`）；建圖 `POST /api/collab/diagrams`（`:553`），請求 `CreateDiagramRequest` 繼承它並多 `system_id`（`:322-329`）。標題上限 200 字（`:43`）。
- 前端反問元件 `ClarifyCandidates.tsx:14` 只對 `kind === 'intent'` 特別處理，其餘種類都把候選列成按鈕、點選只送 `candidateId`——所以**新增的反問種類若沿用既有候選形狀，舊前端仍能列出並點選**。
- 既有變更紀錄：摘要取使用者原句（截長），標籤取工作項標籤（`backend/services/work_orchestrator.py:848-857`）。

## Q1. 新反問種類的線上形狀？

- A. **純新增**：`ClarifyPayload.kind` 增加新值（選系統、選圖、接著畫哪張草稿或新建、新建或修改）；候選沿用既有形狀（必有 `id`、`label`），另加選填的 `systemId`、`diagramId`、`action`（新建）供前端呈現。點選仍只送 `candidateId`，伺服器以連線上保存的對照解析並重新驗證。舊前端不認得新種類時仍會列出按鈕、可點選（退路）
- B. 點選時由前端直接送 `systemId`／`diagramId`，伺服器據以重新驗證（不靠連線上的對照）
- C. Not yet defined
- X. Other（請說明）

[Answer]: A <!-- 2026-11-17T06:25:32Z 使用者以選單選定 -->

## Q2. 存檔怎麼區分「手動存檔轉為正式」與「只寫內容」？預設是哪一個？

- A. 既有 `PUT /api/collab/diagrams/{id}` 加選填欄位 `finalize`，**預設 false＝只寫內容、不改狀態**；只有工作區「儲存架構圖」按鈕與大腦產圖成功時送 `finalize: true`。預設 false 讓 U3 上線前的舊前端自動存檔與手動存檔都不會把草稿轉正式
- B. 另開 `POST /api/collab/diagrams/{id}/finalize` 專門轉正式；既有 PUT 不改狀態
- C. Not yet defined
- X. Other（請說明）

[Answer]: A <!-- 2026-11-17T06:25:32Z 使用者以選單選定 -->

## Q3. 評核、估價、分享、WA 共編遇到草稿時，HTTP 回什麼？

- A. HTTP 409，`detail` 為「這張圖還是草稿，請先完成產圖」；大腦工作項以此訊息結束
- B. HTTP 400，同樣的 `detail`
- C. Not yet defined
- X. Other（請說明）

[Answer]: A <!-- 2026-11-17T06:25:32Z 使用者以選單選定 -->

## Q4. 反問候選最多列幾筆？新圖名稱的主題最多幾個字？

- A. 候選最多 10 筆（超過請改用「切換對象」）；主題最多 30 個可見字元（再補「架構圖」與序號，遠低於標題上限 200）
- B. 候選最多 20 筆；主題最多 50 個可見字元
- C. Not yet defined
- X. Other（請說明）

[Answer]: A <!-- 2026-11-17T06:25:32Z 使用者以選單選定 -->
