# Code Generation Plan — admin-page-column（U3）

> Unit: `admin-page-column`（C-5、C-6 ＋ C-9 前端）· 上游：本單元的 `../functional-design/{business-logic-model,frontend-components}.md`、`../nfr-requirements/*`、`../../../inception/refined-mockups/interaction-spec.md`（`LastActivityCell`／`PaginationControl` 的規格單一來源）、AD-2／AD-12。

## 落點

| 元件 | 檔案 | 性質 |
|---|---|---|
| C-5 最後活動時間儲存格 | `frontend/src/components/LastActivityCell.tsx` | **新檔** |
| C-9 前端（分頁控制） | `frontend/src/components/PaginationControl.tsx` | **新檔** |
| C-6 管理頁資料傳遞 ＋ 卡片佈局 | `frontend/src/pages/AdminPage.tsx` | 既有檔案改寫 |
| e2e | `frontend/tests/e2e/regression.spec.ts` | 既有檔案追加 |

兩個展示元件獨立成檔，符合既有慣例（`src/components/` 已有 9 個元件、`PascalCase.tsx`）。

## 實作順序（三則故事動同一段 JSX，須序列）

1. 型別切換為產生的型別（先做，否則後續改動都在錯的型別上）
2. `LastActivityCell` ＋ 表格加欄（US-1、US-2）
3. 分頁狀態、三種抓取路徑、`PaginationControl`（US-5）
4. 卡片佈局（US-4）
5. e2e

## 必須遵守的既有 lint 形狀（違反即 CI 紅燈）

- 資料抓取拆兩層：純抓取函式不碰 state，state 更新留在呼叫端的 `.then/.catch/.finally`
- state 更新回傳新物件（不可就地修改）
- 逾期判定與忙碌判定**由呼叫端傳入**，元件不自行計算（渲染純度）

## 測試計畫

Playwright（前端**唯一**的自動化驗證層 —— 無 unit／component 測試框架，且 team-practices 明確不採納引入）。需要多頁的 case 以公開註冊端點自行建立 21 個帳號。
