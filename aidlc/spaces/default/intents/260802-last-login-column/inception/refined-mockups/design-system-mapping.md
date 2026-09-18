# Design System Mapping — 最後活動時間欄位

<!-- Stage: refined-mockups（Inception 2.5）· 所有既有值皆為對 frontend/src/pages/AdminPage.tsx 的唯讀實測，
     非發明的設計語彙。來源標籤定義見 refined-mockups-questions.md 的 ## Sources。 -->

## 上游輸入

- **wireframes**（`../../ideation/rough-mockups/wireframes.md`）：欄位位置與標示形式的既定決策，本檔將其對應到既有的實際樣式類別。
- **user-flow**（`../../ideation/rough-mockups/user-flow.md`）：三條流程確認本欄位不新增頁面與導覽節點，故不需新增版面層級的設計語彙。
- **stories**（`../user-stories/stories.md`）：AC-1.4（欄位位置）、AC-2.1（逾期樣式）為本對應的驗收依據。
- **requirements**（`../requirements-analysis/requirements.md`）：C-6 界定前端既有約束，FR-2.1 界定欄位位置。
- **team-practices**（`../practices-discovery/team-practices.md`）：Code Style 一節記載的既有慣例與 lint 規則。

## 核心原則：全部沿用，零新增

本 feature 是**在既有表格加一欄**，不是改版。因此設計系統的對應原則是：

> **不引入任何既有頁面沒有的設計語彙。** 每個樣式決策都必須指向 `AdminPage.tsx` 中已存在的用法。

下表的「既有出處」欄若為空，代表該項是新增的設計決策 —— 全表僅有一項（逾期色的用途），且它沿用既有色階、只是用在新語意上。

## 版面與容器

| 元素 | 採用的既有樣式 | 既有出處 |
|---|---|---|
| 頁面容器 | `bg-white/5 backdrop-blur-2xl border border-white/10 rounded-[2rem] shadow-2xl overflow-hidden` | 使用者管理頁的表格外框，不變更 |
| 捲動容器 | `overflow-auto max-h-[min(70vh,720px)]` | 同上，**新增第 6 欄後仍沿用**（不改捲動策略） |
| 表頭列 | `sticky top-0 z-20`，`bg-slate-950 border-b border-white/10` | 既有 `thead`，新欄位的 `th` 直接加入 |

## 新欄位的樣式對應

| 元素 | 樣式 | 既有出處 |
|---|---|---|
| 表頭儲存格 `th` | `px-6 py-5` ＋ 繼承 `text-xs font-bold text-slate-400 tracking-wider uppercase` | 與其餘 5 個 `th` **完全一致** |
| 資料儲存格 `td` | `px-6 py-4` | 與其餘 `td` **完全一致** |
| 時間值（正常態） | `text-xs text-slate-300` | 與「角色」欄的值同樣式 |
| 時間值（逾期態） | `text-xs text-amber-300` | **色階既有**（「待授權」用同一個 `amber-300`）；用於逾期是新語意 [Q4] |
| 無紀錄態的 `—` | `text-xs text-slate-300` ＋ `tabIndex={0}` ＋ `aria-label` | 字元與色階同「角色」欄的空值；可聚焦是新增行為 [Q2] |

## 語意色盤

| 語意 | 色階 | 既有用途 | 本 feature 的用途 |
|---|---|---|---|
| 需要注意、非錯誤 | `amber-300` | 「待授權」狀態 | **逾期未活動**（新用途，同語意類別） |
| 正常、已完成 | `emerald-300` | 「已核准」狀態 | 不使用 |
| 錯誤 | `red-300` | 載入失敗訊息 | 不使用（逾期不是錯誤） |
| 一般文字 | `slate-300` | 角色值、一般儲存格內容 | 正常態時間值、無紀錄破折號 |
| 次要文字 | `slate-400` | 表頭、載入訊息 | 不新增用途 |

`amber-300` 用於逾期的理由：逾期與待授權在**語意類別上相同** —— 都是「需要人處理但系統沒有故障」。共用色階讓使用者的既有色彩認知直接遷移，不需學習新的色彩語言 [Q4]。

## 響應式

| 斷點 | 佈局 | 依據 |
|---|---|---|
| `< 768px`（Tailwind `md` 以下） | 卡片式，一帳號一卡片 | [Q3]，回答 requirements OQ-2 |
| `≥ 768px` | 表格，6 欄 | 同上 |

專案的 Tailwind 設定**未自訂斷點**，沿用預設值（`sm` 640 / `md` 768 / `lg` 1024）。本決策因此不需新增設定，直接用 `md:` 前綴即可。

選 768px 而非 1024px 的理由：1024px 的寬度實際放得下 6 欄，過早切換為卡片會讓稽核者失去表格的**縱向比較效率** —— 而批次掃讀正是主要 persona 的核心使用方式 [st]。

## 字體與排版

| 項目 | 值 | 既有出處 |
|---|---|---|
| 字族 | `Inter, system-ui, sans-serif` | Tailwind 設定的 `fontFamily.sans`，全站一致 |
| 時間值字級 | `text-xs` | 與角色、授權狀態等資料欄一致 |
| 表頭字級 | `text-xs font-bold uppercase tracking-wider` | 既有 `thead` 樣式 |

時間格式 `YYYY-MM-DD HH:MM` 為**等寬對齊友善**的格式，但既有頁面未使用等寬字體。本設計**不引入等寬字體** —— 那是新的排版語彙，且在 `text-xs` 的字級下，Inter 的數字已足夠對齊掃讀。

## 與既有元件的關係

| 既有元件／樣式 | 本 feature 的影響 |
|---|---|
| 表格結構（`thead` / `tbody`） | 新增一組 `th` / `td`，結構不變 |
| 角色欄的空值 `—` | **完全不動**（本 intent 範圍外）；新欄位的破折號在可及性上與其區分 [Q2] |
| 授權狀態欄的 amber | 不動；新欄位共用同一色階但用於不同語意 |
| 載入／錯誤訊息 | **完全不動**（stories AC-1.9） |
| 角色調整下拉、啟停用切換 | 不動；卡片佈局下位置調整但行為一致 |

## Assumptions & Open Questions

- [assumption] `amber-300` 在既有深色背景（`bg-white/5` 疊在深色底上）的對比度未實測，須於實作時驗證達 WCAG AA 的 4.5:1（已列入 accessibility-checklist）
- [assumption] 卡片佈局的具體樣式（圓角、間距、分隔）沿用既有容器語彙即可，本檔不逐項規定 —— 卡片是既有表格的響應式變體，不是新的設計元件
- [assumption] （開放問題）逾期圖示若改用 SVG 而非文字 `(!)`，其尺寸與色彩需與 `amber-300` 的文字視覺重量相稱；具體圖示資產的選擇留給實作

---

## Revision 1（2026-08-11）— 分頁控制的樣式對應

**核心原則不變：全部沿用，零新增。** 分頁控制不引入任何新的設計代幣、新的色票或新的元件庫；它由既有頁面已在使用的類別組合而成。

| 元素 | 沿用的既有樣式 | 出處（既有程式碼） |
|---|---|---|
| 控制列容器 | `flex items-center gap-2 px-6 py-4` | 與 `AdminPage.tsx` 表格儲存格同一組間距尺度 |
| 頁碼／前後頁按鈕（可用） | `px-2 py-1 text-[10px] font-bold rounded-lg bg-slate-800 border border-slate-700` | 逐字沿用既有的「停用／啟用」小按鈕（`AdminPage.tsx:243`） |
| 目前頁碼 | 上述基礎 ＋ **方括號包覆字樣 `[2]`**（非色彩線索，逐字沿用已核可線框的表達）＋ `font-extrabold`（字重，第二個非色彩線索）＋ `bg-blue-500/20 text-blue-300`（顏色為**輔助**訊號） | 方括號：`wireframes.md:140,154`；顏色：`AdminPage.tsx:184` |
| 停用態（邊界／單頁） | 上述基礎 ＋ `disabled:opacity-50` | 逐字沿用既有角色下拉的停用樣式（`AdminPage.tsx:209`） |
| 總筆數文字 | `text-xs text-slate-300` | 與既有的角色欄／狀態文字同級（`AdminPage.tsx:201`） |
| 空清單訊息 | `p-20 text-center text-slate-400 text-sm` | **逐字沿用**既有的載入態容器（`AdminPage.tsx:162`）—— 空態與載入態是同一種「容器內單一置中訊息」的版式 |
| 「回到第 1 頁」連結 | `text-blue-400 hover:underline` | 逐字沿用既有的頁內連結（`AdminPage.tsx:153`、`:220`） |

**為何目前頁碼必須有非色彩線索**（reviewer Revision 1 Finding 1｜Major）：AC-5.9 與 NFR-2 皆逐字要求「目前頁次不僅以顏色表達」，而 `accessibility-checklist.md` 的 P-6 把它列為**必須**。只給 `bg-blue-500/20 text-blue-300` 是純色彩表達，照字面實作會讓本文件自己的 P-6 直接失敗。方括號 `[2]` 是**已核可線框本來就在用的表達**（`wireframes.md:140` 的 `1 [2] 3 4 ... 9`、`:154` 的 `1 [2] 3 ...`），採用它同時滿足非色彩要求與「零新增」原則，不需發明新的視覺語彙。`font-extrabold` 為第二重線索，沿用既有 `AdminPage.tsx:184` 標籤的字重層級。

**目前頁碼的顏色為何用 `blue-500/20 + blue-300` 而非 `amber`**：`amber` 在本頁已被「待授權」與「逾期」兩個語意佔用（見上方語意色盤）。分頁的「你在這裡」不是警示，把它塗成 amber 會稀釋這兩個真正需要注意的訊號。`blue` 在本頁的既有語意是「當前／自身」（「目前登入」標籤），與「目前頁次」語意同構。

**44x44 觸控目標的達成方式**：既有小按鈕的 `px-2 py-1 text-[10px]` 在小螢幕不足 44x44。**小螢幕以 `md:` 前綴分岔**：`min-w-11 min-h-11 md:min-w-0 md:min-h-0`（Tailwind `11` = 2.75rem = 44px），桌面維持既有密度。這不是新代幣，是既有間距尺度的既有值。

## 響應式（Revision 1 追加）

| 斷點 | 分頁控制 |
|---|---|
| `< 768px` | 簡化：箭頭無文字標籤、頁碼序列較短、總筆數為「N 筆」；每個目標 ≥ 44x44 |
| `≥ 768px` | 完整：含「上一頁／下一頁」文字、較長頁碼序列、「共 N 筆」；沿用既有按鈕密度 |

斷點值沿用既有定案的 768px（`md`），不新增斷點。

## Assumptions & Open Questions（Revision 1 追加）

- [assumption] 上表的類別組合是**對應關係的宣告**，不是逐字的實作程式碼；Construction 可在保持同一組視覺結果的前提下調整寫法
- [已查證，取代原假設] `min-w-11 min-h-11` **＝ 44px，已實測確認**。查證方法更正（reviewer Revision 1 Finding 3）：本專案為 **Tailwind v4**（`package.json` 的 `tailwindcss: ^4.3.0` ＋ `@tailwindcss/postcss`），實際生效的設定是 `src/index.css` 的 CSS-first `@theme` 區塊；**`frontend/tailwind.config.js` 未被任何 `@config` 指令載入，是死碼**（全樹 grep `@config` 零命中）。以專案自身的 Tailwind 實際編譯 `min-w-11` 得 `min-width: calc(var(--spacing) * 11)`，而 `--spacing: 0.25rem`（`@theme` 未覆寫）→ 2.75rem ＝ **44px**。數字結論成立，但前一版（與本檔更早的 Q3 查證）引用的是不生效的檔案，此處一併更正查證依據
- [assumption] 斷點值 768px（`md`）沿用既有定案；v4 的預設斷點同為 `md: 48rem`，`@theme` 未覆寫，故既有定案在 v4 下仍然成立
