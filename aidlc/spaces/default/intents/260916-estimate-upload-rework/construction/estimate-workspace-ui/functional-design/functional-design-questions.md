# Functional Design 問答：U8 `estimate-workspace-ui`

本 Unit 是 **ui**：`/cost` 上傳、明細、機械檢查、歷史、分享、隱私徽章。**不含** SSE／建議呈現（U9）。

## Sources
- U8 unit-of-work；refined-mockups M1–M4、M6–M8；C2 HTTP；U3+U8 同批

---

## Q1 頁面落點
- **A.** 重寫既有 `frontend/src/pages/CostPage.tsx` 為估價工作區；子元件拆 `frontend/src/components/cost/`（建議）
- **B.** 新建 `/estimates` 路由
[Answer]: A — 重寫 CostPage＋components/cost/

## Q2 歷史 UI（OQ-M2）
- **A.** 右側 **drawer** 承載歷史清單（mockups Q6=A）（建議）
- **B.** 用既有 Modal
[Answer]: A — drawer

## Q3 建議區占位
- **A.** 留骨架殼＋「建議區由 U9 啟用」／`data-testid` 錨點；**不**訂閱 SSE（建議）
- **B.** 完全不渲染建議區
[Answer]: A — 骨架殼＋testid，無 SSE

## Q4 雲別更正
- **A.** 上傳前／ambiguous 以 `cloud_overrides` 隨 multipart 送出；主畫面就地更正 → 重新上傳該檔（建議；對齊 C2）
- **B.** 另開 PATCH 雲別 API（U2 未提供）
[Answer]: A — cloud_overrides 隨上傳

## Q5 ShareModal a11y
- **A.** 本 Unit 修 focus trap／標籤（OQ-M1）（建議）
- **B.** 另開 chore
[Answer]: A — 本 Unit 修

## Q6 e2e 範圍（team 底線 C）
- **A.** 至少 1 條 Playwright：空態→上傳成功→明細／檢查可見（建議）
- **B.** 本 Unit 不做 e2e
[Answer]: A — 至少 1 條 e2e

## Consolidated Summary Confirmation
| 項 | 定案 |
|---|---|
| 頁面 | CostPage＋components/cost（Q1=A） |
| 歷史 | drawer（Q2=A） |
| 建議區 | 占位無 SSE（Q3=A） |
| 雲別 | cloud_overrides（Q4=A） |
| Share a11y | 本 Unit（Q5=A） |
| e2e | ≥1（Q6=A） |

[Answer]: Looks correct
