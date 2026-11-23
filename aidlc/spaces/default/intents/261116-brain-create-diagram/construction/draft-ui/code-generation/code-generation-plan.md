# Code Generation Plan — U3 draft-ui

## Summary

- Builds: 前端草稿標示、專案頁計數排除草稿、「儲存架構圖」轉正式、四種新反問的呈現
- Touches: 新增 frontend/src/components/DraftBadge.tsx；frontend/src/{projects/projectsApi.ts,components/projects/*,pages/WorkspacePage.tsx,components/DrawioCanvas.tsx,components/brain/ClarifyCandidates.tsx,types/*}
- Tests: 3 個 Playwright 案例（diagram-drafts.spec.ts）＋ lint 與 build

> 本檔是已核可的 stage 層級計畫 `../../code-generation/code-generation-plan.md` 中屬於本單元的步驟，**逐字摘出、未改寫**（含完成勾選）；Testing Contract、準備步驟（Step 1～2）與收尾步驟（Step 18～19）見該檔。三個單元同一批合入 `ut`。

## Steps

### U3 draft-ui

- [x] **Step 16 — 前端（實作）**：`npm run gen:types` 更新 `src/types/api.d.ts`；`MyDiagram` 改由產生型別推導；專案頁「系統的架構圖」、工作區歷史清單、切換對象選單標示「草稿」並加 `data-testid`；`OverviewTab.tsx` 的 `attachedCount` 排除草稿；工作區「儲存架構圖」按鈕送 `finalize: true`，自動存檔與評核前寫回不送；`ClarifyCandidates.tsx` 依四種新 kind 呈現提示文字與按鈕（點選只送 `candidateId`）；遵守 lint 結構約束（資料抓取拆兩層、不就地修改）。〔FR6.2、FR6.4、FR6.4a、FR3.4〕
- [x] **Step 17 — 前端（測試）**：Playwright 三案——草稿在專案頁清單標示「草稿」且不計入計數；在工作區按「儲存架構圖」後標示消失；大腦送出 `pick_system` 反問時候選可點選並繼續。`npm run lint` 與 `npm run build`（含 `tsc -b`）綠燈。〔FR6.4、FR6.4a、FR6.2、FR3.4、NFR5〕
