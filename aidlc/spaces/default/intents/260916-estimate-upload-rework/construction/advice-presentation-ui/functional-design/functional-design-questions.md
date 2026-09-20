# Functional Design 問答：U9 `advice-presentation-ui`

本 Unit 是 **ui**：啟用 U8 `advice-slot`——SSE 訂閱、進度／骨架、三類建議呈現與 AI 免責標註。不含上傳／明細核心改動（盡量只新增元件）。

## Sources
- U9 unit-of-work；mockups M5／interaction-spec AdviceSection；C3 SSE；U7 FD；U8 `advice-slot` 佔位

---

## Q1 元件落點
- **A.** 新增 `frontend/src/components/cost/EstimateAdvicePanel.tsx`（＋必要 hook／types），掛進 `CostPage` 的 `advice-slot`；不另開路由（建議）
- **B.** 獨立 `/cost/advice` 頁
[Answer]: A — EstimateAdvicePanel 掛入 CostPage advice-slot

## Q2 SSE 傳輸
- **A.** 沿用 Workspace／Assessment：`fetch`＋`Authorization`＋`ReadableStream` 解析 `data:` JSON（EventSource 無法帶 JWT）（建議）
- **B.** `EventSource`＋query token
[Answer]: A — fetch＋stream reader＋JWT header

## Q3 訂閱時機
- **A.** 當 `detail` 載入且 `advice_status` ∈ {`none`,`generating`}（或缺省）時訂閱 `/advice/stream`；`completed`／`failed` 改 `GET /advice` 快照；切換 estimate 時關閉舊串流（建議）
- **B.** 一律只輪詢 REST，不訂閱 SSE
[Answer]: A — generating／none 訂閱 SSE；終態走 REST

## Q4 三態與三類子標題
- **A.** 對齊 M5：pending 骨架＋「正在產生建議…」；complete 固定三子標題（省錢／跨雲／品質），缺內容顯示「本期未提供」或 `unavailable_reasons`／資料不足；failed／timeout 顯示錯誤＋重試語意（建議）
- **B.** 僅顯示單一文字區塊
[Answer]: A — M5 三態＋三子標題恆常

## Q5 失敗「重試」
- **A.** 重試鈕＝重新訂閱／再 `GET /advice`；若仍 `failed` 提示「請重新上傳以再產生建議」（U7：completed／failed 不自動重跑；本 Unit **不**新增 regenerate API）（建議）
- **B.** 本 Unit 新增 `POST .../advice/regenerate`（擴 U7）
[Answer]: A — 不新增 API；重試＝重連／提示重新上傳

## Q6 a11y／e2e
- **A.** `section aria-labelledby`、「由 AI 產生，請自行核對」、完成時 `aria-live="polite"` 不搶焦點；至少 1 條 Playwright（上傳後建議區進入產生中或完成／失敗可辨）（建議）
- **B.** 本 Unit 不做 a11y／e2e
[Answer]: A — a11y＋≥1 e2e

## Consolidated Summary Confirmation
| 項 | 定案 |
|---|---|
| 元件 | EstimateAdvicePanel→CostPage（Q1=A） |
| 傳輸 | fetch＋JWT stream（Q2=A） |
| 訂閱 | generating／none→SSE；終態 REST（Q3=A） |
| 呈現 | M5 三態＋三子標題（Q4=A） |
| 重試 | 無新 API（Q5=A） |
| a11y／e2e | 要（Q6=A） |

[Answer]: Looks correct
