# Frontend Components — A3 Assessment（零行為變更）

> Intent `261001-a2-langgraph`｜FD-Q5 = A  
> 本輪**不改**元件行為；本文件凍結既有契約供驗證，避免施工時誤改前端。

## 元件層級（現況凍結）

- `App.tsx`：路由含 `/assessment`（不改）。
- `AssessmentPage.tsx`：**唯一**評核 UI 表面；本 intent 變更集不得修改其事件處理或 API URL。

## 必須保持的互動（不得改）

| 項目 | 約束 |
|---|---|
| SSE `suggestion_delta` | 繼續以 `data.type === 'suggestion_delta'` 累積建議文字 |
| 建議欄位 | 繼續消費 `suggestions_text`（及現況已用的相關欄位） |
| Model | 前端**不傳** LLM model 名 |
| Provider | 僅傳既有雲 `provider`（若現況已傳） |
| Retry | 既有 `retry-suggestions` URL 與處理流程不變 |

## Props／State

不新増 props／state 需求。現況 `suggestionsLive`、`phase`、`active` review 等本地 state 維持。

## API 整合點

僅後端替换 Review／Lens 實作；前端整合點清單視為**凍結清單**（路徑集合見 FR3.1）。若 OpenAPI 有更新，限非破壞性文件化。

## 驗證暗示

前端自動化非本輪地板（Q7 未要求 Playwright）；契約驗證以後端 mock／遷移測試為主（BR5.1）。手動僅覆蓋無法自動化的 SSE 觀察面（FR5.3）。
