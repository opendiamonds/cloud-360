# Requirement ↔ Unit Map — 讓大腦直接建立新的架構圖（需求與單元對應）

> 上游沒有 `stories.md`（user-stories 不在本 intent 的計畫內），故以 `requirements.md` 的 FR 為鍵；NFR 列為選填列，不進 traceability。每列的「主要單元」即 `traceability.json` 的 target。

## FR 對應

| FR | 主要單元 | 另涉單元（跨單元） |
|---|---|---|
| FR1 | U2 brain-create-flow | — |
| FR1.1 | U2 brain-create-flow | U1 diagram-drafts |
| FR1.2 | U2 brain-create-flow | — |
| FR1.3 | U2 brain-create-flow | — |
| FR1.3a | U1 diagram-drafts | — |
| FR1.4 | U2 brain-create-flow | — |
| FR1.5 | U2 brain-create-flow | — |
| FR2 | U2 brain-create-flow | — |
| FR2.1 | U2 brain-create-flow | — |
| FR2.2 | U2 brain-create-flow | — |
| FR2.3 | U2 brain-create-flow | — |
| FR2.4 | U2 brain-create-flow | — |
| FR3 | U2 brain-create-flow | — |
| FR3.1 | U2 brain-create-flow | — |
| FR3.2 | U2 brain-create-flow | — |
| FR3.3 | U2 brain-create-flow | — |
| FR3.4 | U2 brain-create-flow | U3 draft-ui |
| FR3.5 | U2 brain-create-flow | — |
| FR3.6 | U2 brain-create-flow | — |
| FR4 | U2 brain-create-flow | — |
| FR4.1 | U2 brain-create-flow | — |
| FR4.2 | U1 diagram-drafts | — |
| FR4.3 | U2 brain-create-flow | — |
| FR5 | U2 brain-create-flow | — |
| FR5.1 | U2 brain-create-flow | — |
| FR5.2 | U2 brain-create-flow | — |
| FR5.3 | U2 brain-create-flow | — |
| FR5.4 | U2 brain-create-flow | — |
| FR6 | U1 diagram-drafts | — |
| FR6.1 | U1 diagram-drafts | — |
| FR6.2 | U1 diagram-drafts | U3 draft-ui |
| FR6.3 | U2 brain-create-flow | U1 diagram-drafts |
| FR6.3a | U2 brain-create-flow | — |
| FR6.3b | U2 brain-create-flow | — |
| FR6.4 | U3 draft-ui | — |
| FR6.4a | U1 diagram-drafts | U3 draft-ui |
| FR6.4b | U1 diagram-drafts | — |
| FR6.4c | U1 diagram-drafts | — （參數與現行呼叫端都在 U1） |
| FR6.5 | U1 diagram-drafts | — |
| FR7 | U1 diagram-drafts | — |
| FR7.1 | U1 diagram-drafts | U2 brain-create-flow |

## NFR 對應

| NFR | 主要單元 | 另涉單元 |
|---|---|---|
| NFR1 | U2 brain-create-flow | — |
| NFR2 | U2 brain-create-flow | — |
| NFR3 | U2 brain-create-flow | — |
| NFR4 | U2 brain-create-flow | — |
| NFR5 | U1 diagram-drafts | U2 brain-create-flow、U3 draft-ui |

## 跨單元的項目

| 項目 | 說明 |
|---|---|
| FR1.1 | 建草稿的流程在 U2，「建立為草稿」的 API 在 U1 |
| FR3.4 | 新反問種類在 U2 定義，呈現在 U3 |
| FR6.2 | 存檔轉正式的 API 在 U1，手動存檔與自動存檔的區分在 U3 的工作區 |
| FR6.3 | 產圖失敗保留草稿的流程在 U2，草稿狀態本身在 U1 |
| FR6.4a | 評核、估價、分享的拒絕在 U1，專案頁計數排除在 U3 |
| FR7.1 | 變更紀錄能力在 U1，「經大腦建立」的寫入在 U2 |
| NFR5 | TestClient 測試在 U1／U2，Playwright 斷言在 U3 |

## 各單元內的實作順序

- **U1 diagram-drafts**：狀態欄位與遷移 → 建圖可指定草稿、存檔轉正式 → 清單回傳狀態 → 列圖參數與現行呼叫端 → 各使用端的排除與包含 → 變更紀錄。
- **U2 brain-create-flow**：大腦建圖元件的純函式（判定、取名）與 PBT → 路由多問一題 → 建草稿的 I/O → 閘道預檢、交辦前建草稿與切換 → 新反問種類與點選驗證 → 工作編排轉正式。
- **U3 draft-ui**：清單標示草稿 → 計數排除 → 手動存檔轉正式 → 新反問種類的呈現。

## 覆蓋驗證

- FR 共 41 個，全部有主要單元；U1 11 個、U2 29 個、U3 1 個（以上計數由產生本檔的腳本算出）。
- 每個單元都有對應的 FR。
- 修訂 1：FR7.1 補上 U2 為另涉單元；FR6.4c 註明參數與現行呼叫端同在 U1；主要單元未變，計數不變。
