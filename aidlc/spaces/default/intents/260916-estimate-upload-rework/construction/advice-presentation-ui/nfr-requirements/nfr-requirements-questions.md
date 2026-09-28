# NFR Requirements — 釐清問題（advice-presentation-ui）

> Unit: U9 · kind: **ui** · 產物：performance／security／tech-stack／traceability

## 已定案
| 決策 | 來源 |
|---|---|
| EstimateAdvicePanel＋fetch SSE＋M5 三態 | FD Q1–Q4=A |
| 失敗重試不新增 API；a11y＋≥1 e2e | FD Q5–Q6=A |
| NFR7 TCMS 本 stage 不手寫 | 慣例 |

## Q1 建議產生進度（NFR2）
A. **pending 骨架＋可選 progress 文案**（來自 SSE `progress`）；完成前不顯示假建議文字。**（建議）**
B. 無進度指示
[Answer]: A

## Q2 串流錯誤與安全
A. **JWT 僅放 Authorization header**；錯誤只顯示固定短語／`unavailable_reasons` 鍵對照；不 dump stream raw／stack。**（建議）**
B. 在 UI 顯示原始 SSE payload
[Answer]: A

## Q3 無障礙
A. **section＋aria-labelledby、免責標註、aria-live=polite 播報完成、不搶焦點**（對齊 interaction-spec）。**（建議）**
B. 僅視覺
[Answer]: A

## Q4 Tech stack
A. **既有 React／Vite／Tailwind／Playwright**；SSE 用 fetch＋ReadableStream（與 Workspace 同形）；不新依賴。**（建議）**
B. 引入 EventSource polyfill 套件
[Answer]: A

## Q5 TCMS
A. **否**——歸 tcms-test-cases
B. 是
[Answer]: A

## Consolidated Summary Confirmation
| 項 | 定案 |
|---|---|
| 進度 | 骨架＋progress（Q1=A） |
| 安全／錯誤 | header JWT；短語／reasons（Q2=A） |
| a11y | live polite／不搶焦（Q3=A） |
| stack | 既有＋fetch stream（Q4=A） |
| TCMS | 本 stage 不寫（Q5=A） |

[Answer]: Looks correct
