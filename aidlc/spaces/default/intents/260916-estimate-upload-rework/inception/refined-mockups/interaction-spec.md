# Interaction Specification：C1 估價表上傳

元件級規格，格式依 `.claude/knowledge/aidlc-design-agent/component-spec-template.md`。版面依據見 `mockups.md`，樣式對應見 `design-system-mapping.md`。

斷點沿用 Tailwind 預設：mobile `<768px`、tablet `768–1024px`、desktop `>1024px`（Q8=B）。

---

## 1. 頁面狀態機

`/cost` 的整體狀態由「檔案集合」與「建議工作」兩條獨立軸決定——Q3=A 的漸進式呈現正是把這兩條軸解耦的結果。

```
                  ┌─────────┐
                  │  empty  │  無任何估價表 → M1
                  └────┬────┘
                       │ 檔案落地
                  ┌────▼────────┐
                  │ classifying │  判定雲別 → M2
                  └────┬────────┘
                       │ 雲別確定（自動或使用者指定）
                  ┌────▼────────┐
                  │  parsing    │  解析中 → M2
                  └────┬────────┘
                       │ 解析完成（含部分失敗）
                  ┌────▼────────────────────────────┐
                  │  ready                          │  明細＋機械檢查可用 → M3／M4
                  │  ├─ advice: pending   → 骨架    │
                  │  ├─ advice: complete  → 內容    │
                  │  └─ advice: failed    → 逾時重試 │
                  └─────────────────────────────────┘
```

`ready` 一旦進入就**不因建議失敗而退出**。M8 最後一列的行為由此保證。

---

## 2. EstimateDropzone

| Field | Value |
|---|---|
| Component | `EstimateDropzone` |
| Description | 接收一至三個估價表檔案的拖放區 |
| Category | input |

### States

| State | Description | Trigger |
|---|---|---|
| default | 虛線邊框，顯示限制文字 | page load |
| compact | 已有檔案時收合為單行「＋ 再上傳一份估價表」 | 檔案數 ≥ 1 |
| dragover | 邊框與底色轉為 brand 色 | dragenter |
| disabled | 不接收拖放與點擊 | 檔案數 = 3 |
| error | 紅色提示帶，說明被拒原因 | 超限／副檔名不符 |

### Props / Inputs

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| `files` | `UploadEntry[]` | yes | `[]` | 目前的檔案集合，決定 compact／disabled |
| `maxFiles` | `number` | no | `3` | FR1.3 |
| `maxSizeBytes` | `number` | no | `5 * 1024 * 1024` | FR1.3 |
| `accept` | `string[]` | no | `['.csv', '.xlsx']` | FR1.3 |
| `onFilesAdded` | `(files: File[]) => void` | yes | — | 交給上層做前端校驗與送出 |

前端校驗只擋副檔名與大小；**內容與副檔名是否相符（FR1.4 魔術位元組）一律由後端判定**，前端不做，否則會出現前後端兩套判準。

### Responsive Behaviour

| Breakpoint | Behaviour |
|---|---|
| mobile | 拖放語意在觸控裝置無效，整區退化為單一「選擇檔案」按鈕，限制文字保留 |
| tablet | 同 desktop，高度縮減 |
| desktop | 完整拖放區 |

### Accessibility

| Requirement | Implementation |
|---|---|
| ARIA role | 包一個真實的 `<input type="file">`，拖放區為其 `<label>`；不自造 `role="button"` |
| Keyboard interaction | Tab 聚焦到 file input，Enter／Space 開啟檔案選擇器（瀏覽器原生行為） |
| Label | 可見文字即為 label，透過 `<label for>` 關聯 |
| Contrast ratio | 虛線邊框對背景 ≥ 3:1；限制說明文字 ≥ 4.5:1 |
| Screen reader | 限制文字放在 label 內而非 `title`，確保被讀出 |
| Focus management | 檔案加入後焦點移至新增的第一列判定列 |

---

## 3. CloudDetectionRow

| Field | Value |
|---|---|
| Component | `CloudDetectionRow` |
| Description | 單一上傳檔的雲別判定結果與就地更正（Q1=C） |
| Category | input |

### States

| State | Description | Trigger |
|---|---|---|
| detected | 下拉已預選判定出的雲別 | 後端回傳判定結果 |
| ambiguous | 下拉未選，⚠ 與說明文字，該檔不送解析 | 判定失敗（FR1.5） |
| parsing | 顯示「解析中…」，下拉鎖定 | 雲別確定後 |
| parsed | 顯示「已解析 N 列」 | 解析完成 |
| rejected | 紅字說明被拒原因 | 超限／格式不符／魔術位元組不符 |

### Props / Inputs

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| `filename` | `string` | yes | — | 顯示用 |
| `detectedCloud` | `'aws' \| 'azure' \| 'gcp' \| null` | yes | — | `null` 即 ambiguous |
| `status` | `'detected' \| 'parsing' \| 'parsed' \| 'rejected'` | yes | — | 驅動右側文字 |
| `lineCount` | `number \| null` | no | `null` | parsed 時顯示 |
| `onCloudChange` | `(cloud) => void` | yes | — | 就地更正，觸發或重觸發解析 |
| `onRemove` | `() => void` | yes | — | 移除檔案與其卡片 |

**雲別下拉在任何狀態下都存在**，差別只在是否預選與是否鎖定。這是 Q1=C 的核心——讓「判錯」與「判不出來」共用同一個修正動作。

### Responsive Behaviour

| Breakpoint | Behaviour |
|---|---|
| mobile | 由單列轉為兩行：檔名一行，雲別下拉與狀態一行 |
| tablet | 單列，檔名以 `text-ellipsis` 截斷 |
| desktop | 單列完整 |

### Accessibility

| Requirement | Implementation |
|---|---|
| ARIA role | 原生 `<select>`；⚠ 圖示為裝飾，`aria-hidden="true"` |
| Keyboard interaction | Tab 進入下拉，方向鍵選擇；✕ 為原生 `<button>`，Enter／Space 觸發 |
| Label | `<select>` 以 `aria-label="{檔名} 的雲別"` 標示，避免三個下拉同名 |
| Contrast ratio | ⚠ 狀態不只用顏色，必帶文字「無法判定」（WCAG 1.4.1） |
| Screen reader | 狀態變化（解析中 → 已解析 N 列）由 `aria-live="polite"` 播報 |
| Focus management | 移除某列後焦點移至下一列；若為最後一列則回到拖放區 |

---

## 4. CloudEstimateCard

| Field | Value |
|---|---|
| Component | `CloudEstimateCard` |
| Description | 單一雲別的摺疊式明細卡片（Q2=C） |
| Category | display |

### States

| State | Description | Trigger |
|---|---|---|
| collapsed | 預設。僅標頭：雲別、項數、總額、檢查摘要 | 解析完成 |
| expanded | 標頭 + 完整明細表 + 表尾對帳三行 | 點擊標頭 |
| error | 整份解析不出任何一列，卡片替換為錯誤卡 | 解析結果為空（FR2.3） |

### Props / Inputs

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| `cloud` | `'aws' \| 'azure' \| 'gcp'` | yes | — | 標頭與圖示 |
| `lineItems` | `LineItem[]` | yes | — | 含已解析與無法辨識兩種 |
| `statedTotal` | `Money \| null` | yes | — | 估價表上的總額 |
| `checkResult` | `MechanicalCheck` | yes | — | FR4 的機械檢查結果 |
| `defaultExpanded` | `boolean` | no | `false` | Q2=C |

### 標頭的強制內容

摺疊態標頭**必須**顯示檢查摘要，包含無法辨識的列數。`mockups.md` §4 說明了原因：這是 FR3.2 在摺疊版面下成立的唯一依據。實作上這條不可被「標頭太擠」的理由裁掉——擠的話裁項數，不裁檢查摘要。

### Responsive Behaviour

| Breakpoint | Behaviour |
|---|---|
| mobile | 展開後明細表**每列轉為一張卡片**（Q8=B）：品項為卡片標題，規格／數量／金額為標籤-值配對 |
| tablet | 表格保留，規格欄截斷並可 hover 看全文 |
| desktop | 完整四欄表格 |

mobile 的卡片化是 Q8=B 的實質內容。四欄寬表在 375px 上水平捲動會讓金額欄長期不可見，而金額是這張表的主要資訊。

### Accessibility

| Requirement | Implementation |
|---|---|
| ARIA role | 標頭為 `<button aria-expanded>`；明細為真實 `<table>` 含 `<th scope="col">` |
| Keyboard interaction | Enter／Space 切換展開；表格內 Tab 只停在可互動元素（原始文字展開鈕） |
| Label | `aria-controls` 指向明細容器 id |
| Contrast ratio | 無法辨識列的淡色底對文字仍須 ≥ 4.5:1 |
| Screen reader | 展開／摺疊由 `aria-expanded` 傳達；mobile 卡片化後仍用 `<table>` 語意（CSS 改變視覺、不改變 DOM 語意） |
| Focus management | 摺疊時焦點留在標頭按鈕 |

mobile 卡片化**不得**用 `display: block` 打掉 `<table>` 的語意——那會讓螢幕閱讀器失去列與欄的關聯。改用 grid 重排並保留 `role` 的隱含語意。

---

## 5. UnparsedLineRow

| Field | Value |
|---|---|
| Component | `UnparsedLineRow` |
| Description | 明細表中無法辨識的列（Q5=A、FR2.2、FR3.2） |
| Category | display |

### States

| State | Description | Trigger |
|---|---|---|
| default | 淡色底，金額欄顯示「無法辨識」 | render |
| expanded | 下方展開一列，顯示保留的原始文字 | 點擊 ▸ |

### Props / Inputs

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| `rawText` | `string` | yes | — | FR2.2 要求保留的原始內容 |
| `partialFields` | `Partial<LineItem>` | no | `{}` | 能解析出來的欄位照常顯示 |

**位置固定在原始順序上**，不排序、不抽離（`mockups.md` §5）。

### Accessibility

| Requirement | Implementation |
|---|---|
| ARIA role | `<tr>`；展開鈕為 `<button aria-expanded>` |
| Keyboard interaction | Tab 到展開鈕，Enter／Space 展開 |
| Contrast ratio | 淡色底（`bg-amber-50` 量級）對深色文字 ≥ 4.5:1 |
| Screen reader | 該列以 `<td>` 內的文字「無法辨識」傳達，**不倚賴底色**（WCAG 1.4.1） |
| Focus management | 展開後焦點留在按鈕，新內容以 `aria-live` 無須播報（使用者主動觸發） |

---

## 6. AdviceSection

| Field | Value |
|---|---|
| Component | `AdviceSection` |
| Description | AI 建議區塊，三類子標題固定存在（Q3=A、Q4=A、FR5） |
| Category | feedback |

### States

| State | Description | Trigger |
|---|---|---|
| pending | 骨架載入 + 「正在產生建議…（通常需要 1–3 分鐘）」 | 解析完成、建議未回 |
| complete | 三類子標題與內容 | 建議回傳 |
| partial | 某類顯示「資料不足」或「本期未提供」 | FR5.2、FR5.3 |
| failed | 逾時或錯誤，提供重試；明細不受影響 | >5 分鐘（NFR1） |

### Props / Inputs

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| `status` | `'pending' \| 'complete' \| 'failed'` | yes | — | 驅動整區 |
| `advice` | `{ saving, comparison, quality }` | yes | — | 每類可為內容或 unavailable-reason |
| `onRetry` | `() => void` | yes | — | failed 時 |

三類子標題**恆常渲染**。缺內容顯示原因而非隱藏——隱藏會讓使用者無從分辨「沒建議」與「壞了」。

### Accessibility

| Requirement | Implementation |
|---|---|
| ARIA role | 區段為 `<section aria-labelledby>`，標題含「AI 建議」字樣 |
| Keyboard interaction | 建議內若有連結／重試鈕，皆為原生互動元素 |
| Label | 「由 AI 產生，請自行核對」置於 `<section>` 開頭，在標題之後立即被讀出 |
| Contrast ratio | 骨架動畫的對比不受 AA 約束（非資訊性），但「正在產生」文字須 ≥ 4.5:1 |
| Screen reader | pending → complete 的轉換以 `aria-live="polite"` 播報「建議已產生」；**不得用 `assertive`**，使用者可能正在讀明細 |
| Focus management | 建議填入時**不搶焦點** |

`aria-live="polite"` 與不搶焦點這兩條是 Q3=A 漸進式呈現的無障礙代價：內容在使用者閱讀過程中變動，必須以最不打斷的方式通知。

---

## 7. HistoryDrawer

| Field | Value |
|---|---|
| Component | `HistoryDrawer` |
| Description | 歷史上傳清單，自右側滑入（Q6=A、FR6.2–FR6.4） |
| Category | navigation |

**程式庫中不存在抽屜元件**，此為新增元件型別（`mockups.md` OQ-M2）。

### States

| State | Description | Trigger |
|---|---|---|
| closed | 不渲染 | default |
| open | 自右滑入，遮罩其餘畫面 | 點擊頁首「歷史」 |
| empty | 只有一次上傳時顯示「尚無歷史版本」 | 版本數 = 1 |
| confirming-delete | 二次確認 | 點擊「刪除」 |

### Props / Inputs

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| `versions` | `EstimateVersion[]` | yes | — | 依時間倒序 |
| `currentVersionId` | `string` | yes | — | 標示「目前檢視」 |
| `onSelect` | `(id) => void` | yes | — | 關閉抽屜並切換主畫面 |
| `onDelete` | `(id) => void` | yes | — | FR6.4 |

### 不得提供的能力

**沒有勾選框，沒有多選，沒有「比較選取的版本」。** FR6.3 明訂不得並排比較，而並排比較的標準入場方式就是清單多選。不放勾選框是這條界線在 UI 上的落實，不是樣式偏好。

### Responsive Behaviour

| Breakpoint | Behaviour |
|---|---|
| mobile | 抽屜佔滿寬度（全屏） |
| tablet / desktop | 右側 400px |

### Accessibility

| Requirement | Implementation |
|---|---|
| ARIA role | `role="dialog"` + `aria-modal="true"` + `aria-labelledby` 指向「歷史上傳」標題 |
| Keyboard interaction | Escape 關閉；Tab 在抽屜內循環（focus trap） |
| Contrast ratio | 遮罩不得降低抽屜內文字對比 |
| Screen reader | 開啟時播報標題；背景內容以 `inert` 或 `aria-hidden` 隔離 |
| Focus management | 開啟時焦點移至關閉鈕；關閉時**回到觸發它的「歷史」按鈕** |

---

## 7b. PrivacyBadge

| Field | Value |
|---|---|
| Component | `PrivacyBadge` |
| Description | 頁首的可見性狀態指示（FR6.5）。**純展示，不可點** |
| Category | display |

### States

| State | Description | Trigger |
|---|---|---|
| private | 「僅自己可見」，中性灰 | 未分享（預設） |
| shared | 「已與 N 人分享」，brand 色 | 分享名單非空 |

### Props / Inputs

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| `sharedCount` | `number` | yes | `0` | `0` 即 private |

**沒有 `onClick`。** 徽章說出現況，頁首的「分享」按鈕改變現況，職責不重疊。兩者都能開 modal 會形成語意不明的雙入口。

徽章為**純文字**，不只用鎖頭圖示——圖示為裝飾並標 `aria-hidden`。這是 A4 不倚賴單一感官的要求。

### Accessibility

| Requirement | Implementation |
|---|---|
| ARIA role | 無（純文字 `<span>`），**不進 Tab 序** |
| Keyboard interaction | 不適用 |
| Label | 可見文字即為內容 |
| Contrast ratio | 兩種狀態的文字對其底皆 ≥ 4.5:1 |
| Screen reader | 分享名單變動後以 `aria-live="polite"` 播報新狀態 |
| Focus management | 不適用 |

---

## 8. ShareModal（沿用並修補）

| Field | Value |
|---|---|
| Component | `ShareModal`（既有，`frontend/src/components/ShareModal.tsx`） |
| Description | 分享給指定使用者（FR6.5、FR6.6） |
| Category | feedback |

**版面與樣式原樣沿用，資料來源由架構圖改為估價表。**

### 必須補上的行為（Q7=A）

既有實作缺少下列全部，沿用即繼承缺口：

| 缺口 | 修補 |
|---|---|
| 無 `role="dialog"` / `aria-modal="true"` | 補於最外層容器 |
| 無 `aria-labelledby` | 指向既有的 `<h2>與團隊分享` |
| 無 focus trap | Tab 在 modal 內循環 |
| 無 Escape 關閉 | `keydown` 監聽 |
| 焦點不回歸 | 關閉時回到觸發按鈕 |
| 背景未隔離 | `inert` 或 `aria-hidden` |

既有的成功／失敗回饋使用 `alert()`，非無障礙且體驗粗糙。**本站不要求改**——它超出估價表上傳的範圍，且會動到架構圖分享的行為。列此備忘，交由後續 intent。

---

## 9. 全域鍵盤導覽順序

Tab 順序遵循視覺順序，不使用正值 `tabindex`：

```
頁首標題（非互動）
隱私狀態徽章（非互動，不進 Tab 序）
  → 歷史按鈕 → 分享按鈕
  → 拖放區 file input
  → 判定列 1（雲別下拉 → 移除鈕）→ 判定列 2 → …
  → AWS 卡片標頭 →（展開時）明細內的展開鈕
  → Azure 卡片標頭 → …
  → 檢查結果區段（純文字，不進 Tab）
  → AI 建議區段（重試鈕，若有）
```

抽屜或 modal 開啟時，上述順序整段被 focus trap 取代。
