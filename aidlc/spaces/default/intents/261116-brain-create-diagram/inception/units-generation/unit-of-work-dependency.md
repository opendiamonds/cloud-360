# Unit Dependencies — 讓大腦直接建立新的架構圖（修訂 1）

> 本檔只描述拓樸（誰依賴誰），不建議實作順序。

## 依賴關係

| 單元 | 依賴 | 為什麼依賴（依賴的性質） |
|---|---|---|
| U1 diagram-drafts | — | 只改既有的架構圖資料與其使用端 |
| U2 brain-create-flow | U1 | **技術依賴**：交辦前建草稿要用 U1 的「建立為草稿」；產圖成功轉正式要用 U1 的「手動存檔，轉為正式」；候選與重名判斷要用 U1 的「含不含草稿」參數 |
| U3 draft-ui | U1、U2 | **技術依賴**：草稿標示與計數排除要用 U1 清單回傳的狀態、手動存檔要用 U1 的轉正式；呈現新反問種類要用 U2 定義的 WebSocket 契約——依賴的是契約**形狀**，不是 U2 的實作 |

```mermaid
graph LR
  U2["brain-create-flow"] --> U1["diagram-drafts"]
  U3["draft-ui"] --> U1
  U3 --> U2
```

文字版：brain-create-flow 依賴 diagram-drafts；draft-ui 依賴 diagram-drafts 與 brain-create-flow。沒有循環。

## 整合點

| 介面 | 提供者 | 使用者 | 形式 |
|---|---|---|---|
| 建立為草稿、手動存檔轉為正式 | U1（`collab_router` 的建圖與存檔 API） | U2（經 `CapabilityClient`）、U3（工作區存檔） | HTTP API（OpenAPI） |
| 「我的架構圖」清單回傳狀態 | U1 | U3 | HTTP API（OpenAPI） |
| `list_diagrams_of_system` 含不含草稿 | U1（HierarchyService；U1 同時修改現行呼叫端 `work_orchestrator.py:967`） | U2（閘道候選、大腦建圖的重名判斷等新呼叫端） | 同行程函式呼叫 |
| 「經大腦建立」的變更紀錄 | U1（HierarchyService 的紀錄能力） | U2（大腦建圖元件寫入） | 同行程函式呼叫 |
| 評核、估價對草稿的拒絕訊息 | U1（AssessmentConsumers） | U2（工作項以該訊息結束） | HTTP API 錯誤回應 |
| 新反問種類與候選 | U2（BrainGateway） | U3 | WebSocket 訊息契約 |

## 可平行開發的組合

- U1 沒有依賴單元。
- U2 與 U3 都依賴 U1；U3 另依賴 U2 的 WebSocket 契約**形狀**。契約形狀在 contract-design 定案後，U2 與 U3 的實作彼此獨立，可並行。

## 機讀依賴（下游以此為準）

```yaml
units:
  - name: diagram-drafts
    kind: service
    depends_on: []
  - name: brain-create-flow
    kind: service
    depends_on: [diagram-drafts]
  - name: draft-ui
    kind: ui
    depends_on: [diagram-drafts, brain-create-flow]
```
