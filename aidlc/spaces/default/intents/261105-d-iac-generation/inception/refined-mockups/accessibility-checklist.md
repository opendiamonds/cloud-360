# Accessibility Checklist — Story D IaC 工作區

<!-- Stage: refined-mockups。目標 WCAG 2.1 AA（Q6=A；stories AC1.1.3；req NFR5）。 -->

## 上游輸入

- **mockups**、**interaction-spec**、**design-system-mapping**
- **stories** AC1.1.2–1.1.3、AC1.3.1、AC3.2.2、AC5.1.5–5.1.6
- **requirements** NFR5

## 範圍

Workspace 入口、IaC 三步驟殼、選圖／上傳、執行與進行中態、findings、Secrets 警告、下載 modal、複製回饋。不含代 apply、獨立 `/iac` 品牌殼、WCAG AAA。

## 檢查表

| # | 準則 | 落點 | 通過條件 | 故事 |
|---|---|---|---|---|
| A1 | 2.4.1／2.4.6 標題 | h1「IaC 生成」；各步 h2（生成／掃描／Secrets） | 步驟與主區有明確標題階層 | US1.1 |
| A2 | 1.3.1 結構 | 步驟 `nav`；草稿 `main`；右欄 `complementary` | landmark 可導覽 | Q5／線框 |
| A3 | 1.4.1 不只靠顏色 | findings 嚴重度文字；切圖／錯誤／警告皆有文字 | 關閉顏色仍可區分 HIGH／CRITICAL | US3.2 AC3.2.2 |
| A4 | 1.4.3 對比 | 正文與錯誤 ≥ 4.5:1；大字／UI ≥ 3:1 | 人工對照 brand／red token | Q6／NFR5 |
| A5 | 2.1.1 鍵盤 | 步驟、下拉、上傳、執行、findings 列、下載／複製、modal 鈕 | 均可 Tab 聚焦並啟動（disabled 可聚焦或具名說明） | AC1.1.3 |
| A6 | 2.4.7 焦點可見 | 不裸用 `outline-none`；沿用既有 ring | 焦點環可見 | NFR5 |
| A7 | 3.3.1／3.3.2 錯誤 | 上傳失敗、執行失敗：可見文字＋關聯控件 | 脈絡不變（上傳）；可重試（執行） | US1.4／US2.3／US3.1／US4.1 |
| A8 | 4.1.3 狀態 | `iac-agent-status`、切圖清空提示 `aria-live=polite` | AT 能得知進行中／已清空 | US1.3／Q3 |
| A9 | 4.1.2 名稱角色值 | 下載確認 `role=dialog`＋`aria-modal`；Secrets 警告 status／alert | 與 interaction-spec 一致 | US5.1／US4.2 |
| A10 | 2.4.3 焦點順序 | 開 modal 焦點入內；Esc／取消關閉回下載鈕；不觸發下載 | 取消支可證偽 | AC5.1.6 |
| A11 | 無權入口 | disabled＋說明，非從 DOM 移除致無法發現 | 說明含缺權故事 | AC1.1.2 |
| A12 | 空狀態 | 無圖／無草稿掃描／無 D2 改寫皆有可見說明 | 不空白主區／右欄 | US1.2／US3.1／US4.2 |
| A13 | 進行中 | 執行鈕 busy；不重複送出 | 主區骨架／淡出可選但狀態文字必備 | AC2.1.3 等 |
| A14 | 複製 | 未選檔 disabled；成功有「已複製」文字 | 不靜默成功 | US5.1 |
| A15 | 無 apply | UI 無 apply／destroy 控件文案 | 靜態盤點 0 命中 | US5.1 AC5.1.1 |

## 不做本輪

- WCAG AAA
- 深色 HCL 主題對比雙軌（Q6≠B）
- ShareModal 既有 a11y 債的全域修復（僅要求新 dialog 達標，不複製缺口）
- 行動端另做手勢／底片導覽

## 驗收掛點

- Playwright：Tab 至步驟與下載；有 HIGH 時下載先出 `iac-download-confirm`；取消後無 download 事件。
- 人工：對比、焦點環、讀屏讀出嚴重度文字與「已清空」提示。
