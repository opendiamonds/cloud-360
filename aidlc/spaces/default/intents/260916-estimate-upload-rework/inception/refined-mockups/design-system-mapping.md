# Design System Mapping：C1 估價表上傳

把 `mockups.md` 的每個視覺元素對應到**本 repo 既有的**樣式語彙。本專案無第三方元件庫（無 antd／MUI），設計系統實質上是 Tailwind v4 的 `@theme` token 加上散落在既有元件中的重複樣式組合。

---

## 1. 既有 token（`frontend/src/index.css`）

Tailwind v4 的 `@theme` 區塊定義了單一自訂色階：

| Token | 值 | 語義 |
|---|---|---|
| `--color-brand-50` | `#eff6ff` | 極淡底，hover 用 |
| `--color-brand-100` | `#dbeafe` | 淡邊框 |
| `--color-brand-500` | `#3b82f6` | 圖示 |
| `--color-brand-600` | `#2563eb` | 主要按鈕底 |
| `--color-brand-700` | `#1d4ed8` | 主要按鈕 hover |

`brand-*` 是藍色階（與 Tailwind `blue-*` 同值）。`50`–`900` 十階齊全，但既有元件實際只用到 `50`、`100`、`500`、`600`、`700` 五階。

**語義色（成功／警告／錯誤）沒有 token。** 既有元件直接用 Tailwind 內建的 `red-*`、`green-*` 等。本站沿用此做法，不新增 token——為了三個狀態新增一套語義層，與現況的距離太大且沒有第二個消費者。

---

## 2. 既有樣式組合（取自 `ShareModal.tsx`）

`ShareModal` 是本 repo 樣式語彙最完整的單一檔案，也是 FR6.6 指定沿用的模型。下列組合視為事實上的設計系統：

| 用途 | class 組合 |
|---|---|
| Modal 遮罩 | `fixed inset-0 z-[9999] bg-black/40 backdrop-blur-sm flex items-center justify-center` |
| Modal 容器 | `bg-white w-full max-w-md rounded-2xl shadow-xl overflow-hidden` |
| 區段標題列 | `p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50` |
| 標題文字 | `text-xl font-bold text-gray-800 flex items-center gap-2` |
| 主要按鈕 | `px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-bold rounded-xl shadow-md hover:shadow-lg hover:shadow-brand-500/30 transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:hover:translate-y-0` |
| 次要按鈕 | `px-5 py-2.5 text-sm font-bold text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-xl transition-all` |
| 清單項（可點） | `flex items-center gap-3 p-3 rounded-xl border border-gray-100 hover:bg-brand-50 hover:border-brand-100 cursor-pointer transition-colors` |
| 圖示關閉鈕 | `text-gray-400 hover:text-gray-600 hover:bg-gray-100 p-1.5 rounded-lg transition-colors` |
| 底部動作列 | `p-6 border-t border-gray-100 bg-gray-50/50 flex justify-end gap-3` |

圓角語彙為 **`rounded-2xl` 容器 / `rounded-xl` 控制項 / `rounded-lg` 圖示鈕** 三階。本站全數遵循。

---

## 3. 逐元素對應

### 3.1 可直接沿用（零新樣式）

| `mockups.md` 元素 | 對應 |
|---|---|
| 分享 modal（M7） | `ShareModal.tsx` 整檔，僅換資料來源 |
| 頁首「歷史」「分享」按鈕 | 次要按鈕組合 |
| 抽屜內的版本清單項（M6） | 清單項組合 |
| 抽屜關閉鈕 | 圖示關閉鈕組合 |
| 「檢視」「刪除」按鈕 | 次要按鈕，刪除加 `text-red-600 hover:bg-red-50` |
| 錯誤卡與紅字提示（M8） | Tailwind 內建 `red-*`，無既有組合可循，但屬單純用法 |

### 3.2 由既有組合改造

| 元素 | 基底 | 改動 |
|---|---|---|
| 雲別卡片（M3／M4） | Modal 容器 `bg-white rounded-2xl shadow-xl` | 降為 `shadow-sm border border-gray-100`——卡片在頁面流內，不該有 modal 等級的陰影 |
| 卡片標頭（摺疊態） | 區段標題列 | 去掉 `border-b`（摺疊時無下方內容），展開時才加回 |
| 判定列（M2） | 清單項組合 | 去掉 `cursor-pointer` 與 `hover:bg-brand-50`——整列不可點，只有內部控制項可互動 |
| 檢查結果／AI 建議區段 | Modal 容器 | 同雲別卡片的陰影降級 |

### 3.3 需要新樣式

| 元素 | 說明 | 建議 |
|---|---|---|
| **抽屜（M6）** | 程式庫中無此元件型別 | 遮罩沿用 modal 的 `bg-black/40 backdrop-blur-sm`；容器改為 `fixed right-0 inset-y-0 w-full sm:w-[400px] bg-white shadow-2xl`，圓角僅左側 `rounded-l-2xl` |
| **明細表格** | 既有元件中**沒有任何 `<table>`** | 表頭 `bg-gray-50/50 text-xs font-bold text-gray-500 uppercase`；列 `border-b border-gray-100`；數值欄 `text-right tabular-nums` |
| **無法辨識列** | 無先例 | `bg-amber-50/60` + 金額欄 `text-amber-700 font-medium`，文字「無法辨識」 |
| **骨架載入（M5）** | 既有為文字「載入中…」，無骨架 | `animate-pulse bg-gray-100 rounded h-4`，寬度交錯以避免整齊的假象 |
| **拖放區** | 無先例 | `border-2 border-dashed border-gray-300 rounded-2xl`；dragover 時 `border-brand-500 bg-brand-50` |
| **狀態徽章**（✓ 通過／⚠ 有問題） | 無先例 | `inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-xs font-bold`，配 `bg-green-50 text-green-700` 或 `bg-amber-50 text-amber-700` |

`tabular-nums` 是金額欄的硬要求。比例字距下的數字對不齊，讓使用者無法目視比對兩列金額的量級——而目視比對正是他發現解析出錯的主要手段。

---

## 4. 與退場程式碼的關係

`frontend/src/cost/` 目前只有兩支檔案：

| 檔案 | 處置 |
|---|---|
| `supportedRegions.ts`（48 行） | **刪除**。它服務的是 C1r 的區域選擇，隨自動估價一同退場（FR9） |
| `slotRegistry.tsx`（18 行） | 由 functional-design 判定。它是通用的插槽機制，未必與估價綁定 |

`CostPage.tsx`（964 行）整檔重寫。其中值得保留的只有**金額格式化與雲別顯示名稱**兩類純函式（`cloudDisplayName` 等），其餘皆為自動估價路徑的專用邏輯。

---

## 5. 不引入的東西

| 項目 | 理由 |
|---|---|
| 元件庫（antd／MUI／shadcn） | 本 intent 需要的元件不超過七個，其中四個可由既有組合改造。引入元件庫的成本遠大於收益，且會與既有頁面產生兩套視覺語彙 |
| 語義色 token | 見 §1 |
| 圖表函式庫 | 既有 `CostPage` 有圓餅圖（`PIE_LABELS`），但本 intent 的需求（FR3.1 逐項明細＋總額）未要求任何圖表。不主動加 |
| 深色模式 | 既有頁面全無深色支援，單獨為此頁做會產生不一致 |

圖表這條值得記一筆：舊 `CostPage` 有圓餅圖，新畫面沒有。這是**能力的淨減少**，不是疏漏——需求未要求，且三雲併陳時圓餅圖的資訊密度低於摺疊卡片的總額列。若使用者事後覺得少了東西，這裡是查證的依據。

---

## Assumptions & Open Questions

**假設**

- **A-D1**：`index.css` 的 `@theme` 是唯一的 token 來源。`App.css` 未逐行檢查，若其中另有全域樣式可能與本對應衝突。
- **A-D2**：`ShareModal` 的樣式組合代表全 repo 的共識。它是最完整的單一樣本，但未與 `Sidebar`、`ChatBox` 等交叉驗證是否存在第二套語彙。

**待決**

- **OQ-D1**：`slotRegistry.tsx` 的去留（見 §4）。
- **OQ-D2**：表格是本 repo 第一個 `<table>`，其樣式將成為後續頁面的先例。是否要抽成共用元件而非寫死在估價頁內，交由 functional-design。
