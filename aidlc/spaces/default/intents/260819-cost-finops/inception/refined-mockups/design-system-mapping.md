# Design System Mapping — 成本估算與 FinOps（C1 第一輪）

<!-- Stage: refined-mockups。Q5=A：不新開 Cost 品牌色；沿用現有 Tailwind 與控件。 -->

## 上游輸入

- **mockups**、**interaction-spec**
- **code**：`frontend/src/components/Sidebar.tsx`、`Layout.tsx`、`pages/WorkspacePage.tsx`、`pages/AssessmentPage.tsx`、`pages/ForbiddenPage.tsx`

## 原則

Cost 頁是新路由，不是新設計系統。能復用的 class 與互動一律復用；只允許三項特化：表格數字右對齊、總額字級大於列、超支危險色＋「已超支」文字。

## Token／class 對照

| 用途 | 採用（HEAD 已有） | 不採用 |
|---|---|---|
| 頁面底 | `Layout`：`bg-gray-50 font-sans` | 新背景圖、深色主題 |
| 側欄分組 | 現有 `groupHeaderClass`、`NavLink` | 新 icon 套件 |
| 主按鈕 | Workspace：`rounded-xl`、`font-bold`、`bg-brand-50 text-brand-700` | 新圓角系統 |
| 成功卡 CTA | 與「繼續對話編輯」同級次要鈕 | 做成 Coming soon 灰鈕 |
| 表單欄 | Assessment：`border border-gray-200 rounded-xl px-3 py-2 text-sm` | 自訂 input 元件庫 |
| 警告／超支 | Assessment 危險：`text-red-700 bg-red-50 border-red-100` | 只改顏色不給文字 |
| 橫幅 | 主區頂一條 `bg-red-50 border-b border-red-100 text-red-800` | toast、inbox、可永久關閉的 chip |
| 空狀態主文 | `text-sm text-gray-600` | 插畫系統 |
| 總額 | `text-3xl font-bold tabular-nums text-gray-900`；超支時加 `text-red-700` | 儀表板卡片網格 |
| 列數字 | `text-right tabular-nums` | 等寬自訂字型檔 |
| 圓餅色點 | 四色須在圖例文字旁重複；對比 ≥ 3:1 | 新增 chart npm |

## 元件映射

| Mockup 塊 | 現有對標 | 新建 |
|---|---|---|
| Sidebar「成本」 | `Sidebar` 架構／系統管理組 | 一組 `showCostSection` + NavLink `/cost` |
| 圖下拉 | Assessment 頁首 `<select className="border ... rounded-xl">` | `DiagramSelect` 薄包裝 |
| 資源表 | Admin／權限表的 `<table>` 密度 | `CostResourceTable`（無現成 Cost 表） |
| 時數／SKU／預算輸入 | Assessment input | 列內 input，不新 library |
| SVG 圓餅 | 無 | `PieBreakdown` 本頁內聯 SVG |
| 超支橫幅 | 無全域 banner | `OverspendBanner` 放進 `Layout` 主欄頂 |
| 無權 | `ForbiddenPage` `/403` | 不新 403 |
| 產圖 CTA | `WorkspacePage` 成功卡按鈕列 | 多一顆 button |

## 響應式

| Breakpoint | 行為 |
|---|---|
| &lt;768px | 單欄；表可橫向捲動或折欄但仍能讀完資源名與小計；不另做卡片佈局 |
| 768–1024px | 與桌面相同資訊層級，圓餅與清單可並排 |
| &gt;1024px | mockups M2 預設：總額全寬 → 圓餅＋清單 → 表 |

## 明確不做

- 新 Cost 色票、暗色儀表板、圖表套件（Q1／Q5）。
- 通知中心、未讀數（AC-7.5）。
- 第一段用 CSS `hidden` 藏預算——必須不掛元件。
