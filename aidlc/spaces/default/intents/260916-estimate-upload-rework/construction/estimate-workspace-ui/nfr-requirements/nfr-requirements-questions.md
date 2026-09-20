# NFR Requirements — 釐清問題（estimate-workspace-ui）

> Unit: U8 · kind: **ui** · 產物：performance／security／tech-stack／traceability

## 已定案
| 決策 | 來源 |
|---|---|
| CostPage＋components/cost；建議區占位無 SSE | FD Q1–Q3=A |
| drawer 歷史；cloud_overrides；Share a11y；≥1 e2e | FD Q2／Q4–Q6=A |
| 與 U3 同批部署 | unit-of-work |
| NFR7 TCMS 本 stage 不手寫 | 慣例 |

## Q1 上傳進度 UI（NFR2 本 unit 面）
A. **上傳中顯示明確進度／忙碌態**（按鈕 disabled＋「上傳中…」）；解析完成前不假裝有明細。**（建議）**
B. 無進度，只等 Promise
[Answer]: A

## Q2 錯誤呈現（security／UX）
A. **只顯示後端 `detail` 固定短語**（中文 UI 可對照映射）；不 dump JSON／stack。**（建議）**
B. 顯示完整 response body
[Answer]: A

## Q3 無障礙底線
A. **WCAG 2.1 AA 目標**：drawer／Share 有 `role=dialog`、Esc 關閉、初始 focus；互動元件有 data-testid。**（建議）**
B. 僅視覺完成
[Answer]: A

## Q4 Tech stack
A. **既有 React／Vite／Tailwind／Playwright**；不新引入 UI 函式庫。**（建議）**
B. 引入新 component library
[Answer]: A

## Q5 TCMS
A. **否**——歸 tcms-test-cases
B. 是
[Answer]: A

## Consolidated Summary Confirmation
| 項 | 定案 |
|---|---|
| 進度 | 上傳忙碌態（Q1=A） |
| 錯誤 | 僅 detail 短語（Q2=A） |
| a11y | dialog／Esc／testid（Q3=A） |
| stack | 既有 React＋Playwright（Q4=A） |
| TCMS | 本 stage 不寫（Q5=A） |

[Answer]: Looks correct
