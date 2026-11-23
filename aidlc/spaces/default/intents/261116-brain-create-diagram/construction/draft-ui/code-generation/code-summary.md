# Code Summary — U3 draft-ui

> 全部單元的總覽、完整測試結果與部署前置見 `../../code-generation/code-summary.md`。分支 `danniel/feat/brain-create-diagram`，未 commit。

## 檔案

| 檔案 | 改動 |
|---|---|
| `frontend/src/projects/projectsApi.ts` | `MyDiagram` 改由產生型別推導；`isDraft` |
| `frontend/src/components/DraftBadge.tsx`（新） | 「草稿」標示 |
| `frontend/src/components/projects/SystemDiagrams.tsx`、`OverviewTab.tsx` | 草稿標示；計數排除草稿 |
| `frontend/src/pages/WorkspacePage.tsx`、`components/DrawioCanvas.tsx` | 「儲存架構圖」送 `finalize: true`（自動存檔與評核前寫回不送）；歷史選單標示「（草稿）」；`data-testid` |
| `frontend/src/components/brain/ClarifyCandidates.tsx` | 四種新反問的提示文字（契約 C6 的 Open Question 於本站定案） |
| `frontend/src/brain/testing/wsFrames.ts` | `clarifyFrame` 補新欄位（產生型別將其列為必填 nullable） |

## 本單元的測試

- 3 個 Playwright 案例（diagram-drafts.spec.ts）＋ lint 與 build；執行指令見 `unit-test-instructions.md`。
- 後端全套變更後 `Ran 1601 tests … OK (skipped=3)`（stage 層級實跑結果）。

## 與計畫的偏差

- **「切換對象選單」沒有可標示的地方**：`ObjectPicker` 只列專案與系統、不列圖；可切到圖的選單是工作區歷史選單，已標示。

## 修訂 1（2026-11-19 核可關卡要求修改；計畫 Step 26–27）

來源：本單元審查 `reviews/review-01.md` R-04～R-08；整體審查 R-04。

| 檔案 | 改動 |
|---|---|
| `frontend/src/components/projects/SystemDiagrams.tsx` | 「把架構圖掛到…」下拉的選項加「（草稿）」、`data-draft`、`data-testid="attach-candidate-<id>"`（R-05） |
| `frontend/src/pages/AssessmentPage.tsx` | `DiagramItem.diagram_status`（型別取自產生的 `MyDiagramItem`）；下拉選項標示「（草稿）」、`data-draft`、`data-testid="assessment-diagram-option-<id>"`；新增 `readErrorDetail()`，發起評核失敗時顯示 `detail` 句子而非原始 JSON（R-04） |
| `frontend/src/pages/WorkspacePage.tsx` | `Diagram` 改由 `MyDiagramItem` 推導（`id`／`title`／`is_owner`／`diagram_status` 必填），`xml_data`／`shared_user_ids` 取自 `DiagramDetail` 型別（R-06） |
| `frontend/src/components/brain/ClarifyCandidates.tsx` | 群組 `aria-label` 依 kind 給（`GROUP_LABELS`）；`new_or_modify`／`resume_draft_or_new` 的回絕按鈕改為「都不要」（R-08） |
| `frontend/tests/e2e/diagram-drafts.spec.ts` | `DiagramStub` 改為 `components['schemas']['MyDiagramItem']`（R-06）；新增 2 案（掛圖下拉、評核頁標示與 409 可讀訊息）；pick_system 案加 `aria-label` 斷言 |
| `traceability.json` | 補 `FR3.4`、`FR6.2`、`FR6.4a`（R-07） |

測試：`diagram-drafts.spec.ts` 5 passed（本機 `vite preview` ＋ 全樁化，**未在 CI 的 `ui-regression` stack 上執行**）；`npm run lint` 0 errors／2 個既存 warning；`npm run build`、`check:types` 通過。突變：拿掉掛圖下拉的「（草稿）」→ 掛圖案紅；`readErrorDetail` 改回傳原文 → 評核案紅（`{"detail"` 出現）；還原後 5 passed。

未處理：`WorkspacePage.goWellArchitected` 對草稿仍照常導向評核頁（在下一頁被 409 擋下並顯示可讀訊息）；`ShareModal` 已確認以 `alert(data.detail)` 呈現，不需改。
