# Design System Mapping & Responsive Tokens — A1 混合雲繪圖功能

> Stage: refined-mockups (2.5) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游基準：
> - [wireframes](../../ideation/rough-mockups/wireframes.md)
> - [user-flow](../../ideation/rough-mockups/user-flow.md)
> - [stories](../user-stories/stories.md)
> - [requirements](../requirements-analysis/requirements.md)
> - [team-practices](../practices-discovery/team-practices.md)

---

## 1. 前端 UI 元件與 Design System 映射 (UI Component Mapping)

本專案前端基於 React 18 + Vite 與既有 UI 元件庫構建，所有混合雲新增控制項均精準對齊既有 Design Tokens：

| 功能需求 | UI 呈現元件 | 既有元件庫來源 | Tailwind / CSS Classes | 狀態樣式 |
| :--- | :--- | :--- | :--- | :--- |
| **Toolbar 選擇器** | `ProviderDropdown` | `components/ui/Dropdown` | `h-9 px-3 text-sm font-medium border rounded-md shadow-sm bg-white` | Active: `border-blue-500 ring-1 ring-blue-500` |
| **混合雲選中標籤** | `ProviderBadge` | `components/ui/Badge` | `inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800` | Compound 狀態常駐 |
| **Chat 意圖通知** | `ChatAlertNotice` | `components/chat/Notice` | `p-2.5 my-2 text-xs rounded-lg border bg-slate-50 border-slate-200 text-slate-700` | 自動折疊 / 淡入 |
| **畫布視角控制** | `ZoomControls` | `components/canvas/Zoom` | `flex items-center gap-1 bg-white border border-slate-200 rounded-lg p-1` | Hover: `bg-slate-100` |

---

## 2. 後端 mxGraph 群組樣式與色彩 Token 映射 (mxGraph Style Tokens)

後端 `backend/services/diagram_builder.py` 內建之 `GROUP_STYLES` 與視覺規範映射表：

| 雲端提供商 | 頂層群組容器名稱 | 邊框色彩 Token (`strokeColor`) | 背景色彩 Token (`fillColor`) | 尺寸規範 (Dimensions) |
| :--- | :--- | :--- | :--- | :--- |
| **AWS Cloud (Hub)** | `aws_cloud` | `#FF9900` (AWS Orange) | `#FFF7ED` (5% Opacity) | 預設寬度: 480px，高度動態計算 |
| **Azure Cloud (Spoke)** | `azure_cloud` | `#0078D4` (Azure Blue) | `#F0F9FF` (5% Opacity) | 預設寬度: 360px，高度動態計算 |
| **GCP Cloud (Spoke)** | `gcp_cloud` | `#4285F4` (Google Blue) | `#F8FAFC` (5% Opacity) | 預設寬度: 360px，高度動態計算 |
| **緩衝走廊 (Buffer)** | `corridor_spacer` | 透明 (`none`) | 透明 (`none`) | 寬度: 120px，橫向硬隔離走廊 |
| **跨雲直角折線** | `compound_edge` | `#475569` (Slate 600) | `none` (寬度 2px) | 直角路由 `orthogonalEdgeStyle` |
| **協議膠囊標籤** | `protocol_badge` | `#CBD5E1` (Slate 300) | `#FFFFFF` (純白) | 文字: `#1E293B`，圓角: 4px |
| **容錯圖示 SVG** | `fallback_svg` | `#94A3B8` (Slate 400) | `#F1F5F9` (Slate 100) | 40x40px，文字: `#475569` |

---

## 3. 響應式斷點與畫布適應行為 (Responsive Breakpoints & Layout Adaptations)

因混合雲架構畫布寬度顯著大於單一雲架構（總寬度 $\ge 360 + 120 + 480 + 120 + 360 = 1440\text{px}$），介面針對不同螢幕尺寸提供自適應策略：

| 螢幕斷點 (Breakpoint) | 解析度寬度 | Toolbar 佈局策略 | DrawioCanvas 適應策略 | ChatBox 側邊欄策略 |
| :--- | :--- | :--- | :--- | :--- |
| **Desktop XL (寬螢幕)** | $\ge 1920\text{px}$ | 完整展開所有控制項與即時統計 | Fit-to-Window 預設縮放 100%，居中完整呈現三雲全貌 | 固定展開於右側 (寬度 380px) |
| **Desktop LG (標準筆電)** | $1440\text{px} \sim 1919\text{px}$ | Provider 選單下拉收納，按鈕緊湊排版 | Fit-to-Window 自動縮放至 70% ~ 80%，留白 32px | 固定展開於右側 (寬度 320px) |
| **Tablet / Small (平板/小螢幕)** | $< 1440\text{px}$ | Toolbar 收納至漢堡選單或次選單 | Fit-to-Window 自動縮放至 50% ~ 60%，提供水平捲軸 | 收納為浮動懸浮抽屜 (Drawer) |

