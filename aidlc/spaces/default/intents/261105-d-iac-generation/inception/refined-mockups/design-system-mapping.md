# Design System Mapping — Story D IaC 工作區

<!-- Stage: refined-mockups。Q6=A：不新開 IaC 品牌色；沿用既有 Tailwind 與 Workspace／Cost 控件語彙。 -->

## 上游輸入

- **mockups**、**interaction-spec**
- **code**：`WorkspacePage.tsx`、`CostPage.tsx`、`ShareModal.tsx`、`Sidebar.tsx`、`Layout.tsx`、`index.css`（`brand-*`）

## 原則

IaC 工作區是 Workspace **內嵌步驟殼**，不是新設計系統。能復用的 class／modal／按鈕一律復用；只允許特化：步驟列、檔案樹＋HCL 預覽密度、右欄依步驟切換面板。

## Token／class 對照

| 用途 | 採用（HEAD 已有） | 不採用 |
|---|---|---|
| 頁面底 | `Layout`：`bg-gray-50 font-sans` | 獨立深色殼、新背景圖 |
| 主按鈕 | `rounded-xl bg-brand-600 text-white text-sm font-bold` | 新圓角／新主色 |
| 次按鈕 | `rounded-xl border border-gray-200 text-gray-700` | — |
| 危險／錯誤 | `text-red-700 bg-red-50 border-red-100` | 只改色不給文字 |
| 成功／完成提示 | `text-emerald-800 bg-emerald-50`（對齊 Cost） | — |
| 表單／下拉 | `border border-gray-200 rounded-xl px-3 py-2 text-sm` | 新 combobox 庫 |
| 空狀態 | `text-sm text-gray-600` | 插畫系統 |
| Modal | ShareModal 語彙：`rounded-2xl shadow-xl`＋主／次鈕 | 新 drawer 庫（Q4≠B） |
| HCL 預覽 | 淺底 `bg-white`＋等寬 `font-mono text-sm`；**非**深色主題（Q6≠B） | 獨立程式碼主題包 |
| Disabled | `disabled:opacity-40`＋可見說明文字 | 隱藏入口（與 AC1.1.2 衝突） |

## 元件映射

| Mockup 塊 | 現有對標 | 新建 |
|---|---|---|
| Workspace「生成 IaC」 | `WorkspacePage` 工具列 Coming Soon 鈕 | 改為可導航／開面板；`iac-entry` |
| 三欄殼 | Workspace 主區＋aside 密度 | `IacWorkspaceShell`（步驟＋草稿＋右欄） |
| 圖下拉／上傳 | Assessment／Workspace 選圖習慣 | `DiagramContextCard` |
| Agent 狀態 | `WorkspacePage` `progress`／agent 訊息 | `AgentStatusPanel` 复用語意 |
| Findings 表 | Admin／權限表密度 | `FindingsList` |
| 改寫清單 | 清單＋`rounded-xl border` | `RewriteList` |
| 下載確認 | `ShareModal`／Cost modal 焦點模式 | `DownloadConfirmDialog`（須補 focus trap／Esc；ShareModal 有 a11y 債，**不可**原樣複製缺口） |
| 無權 | 入口 disabled；API 403 | 不新 403 頁（除非整頁無 view） |

## 響應式

| Breakpoint | 行為 |
|---|---|
| &lt;768px | 步驟改頂部橫向捲動；主草稿與 aside **上下堆疊**（草稿在上） |
| 768–1024px | 可維持三欄或縮右欄寬；不另做資訊架構 |
| &gt;1024px | mockups M2 預設三欄 |

## 文案契約（產品字串，供 e2e）

| 情境 | 可見字串（可微調但需穩定 test） |
|---|---|
| 無草稿執行掃描 | 含「請先完成生成」或等價 |
| 無 D2 執行改寫 | 含「需先完成掃描」或等價 |
| 切圖清空 | 含「已清空」類文字 |
| 複製成功 | 含「已複製」 |
| 無 finding | 精確「無 finding」或產品凍結繁中等價 |
| 嚴重度 | 列上可見 `HIGH`／`CRITICAL`（或凍結繁中） |

## Non-goals

- 新 npm 圖示／元件庫
- IaC 專屬色票或深色預覽主題（本輪）
- 代 apply 按鈕樣式（禁止出現）
