# Interaction Spec — 成本估算與 FinOps（C1 第一輪）

<!-- Stage: refined-mockups。元件規格格式見 `.claude/knowledge/aidlc-design-agent/component-spec-template.md`。
     行為對齊 `../user-stories/stories.md`；視覺釘點見 `./mockups.md`。 -->

## 上游輸入

- **mockups**（本目錄）
- **stories**（`../user-stories/stories.md`）
- **wireframes**／**user-flow**
- **Q1–Q5=A**

## 全域規則

- 第一段不掛 `CostBudgetField`、`OverspendFlag`、`OverspendBanner`（DOM 不存在，不是 `hidden`）。
- 所有變更：前端先做可見校验，非法不送出；授權仍以 API 403 為準。
- 總額更新：`aria-live="polite"` 掛在 `cost-total` 的容器。
- 窄視窗（&lt;768px）：單欄捲動，不改成卡片堆疊（rough Q5）。

---

## CostPageShell

| Field | Value |
|---|---|
| Component | CostPageShell |
| Description | `/cost` 頁框：h1、圖下拉、主區狀態切換 |
| Category | layout |

### States

| State | Description | Trigger |
|---|---|---|
| empty | 無圖或未選圖；無 `cost-total` | AC-1.3 |
| loading | 已選圖、列未到達；無 `cost-total` | AC-1.13 |
| error | 請求失敗；「重試」可聚焦 | AC-1.13 |
| ready | 列已到；區域未填時仍 ready 但攔截官方價 | AC-1.8 |
| forbidden-route | 不進此頁，改 `/403` | AC-1.1b |

### Keyboard

圖下拉 Tab 可達；Enter 展開既有 `<select>` 行為。切圖後列集合換成所選圖（AC-1.11）。

---

## HoursInput

| Field | Value |
|---|---|
| Component | HoursInput |
| Description | 列上每日時數 |
| Category | input |

### States

| State | Description | Trigger |
|---|---|---|
| default | 值 24，可編（Alex） | 新擷取列 |
| readonly | 同一數字，不可編 | David／Hannah |
| invalid | 空白／非數字／非整數／&lt;0／&gt;24 | 失焦或 Enter |
| submitting | 合法值已送出、等待 2xx | Alex 送出 |
| error-403 | 不應出現在 UI 可編態；API 仍可能 403 | 被串改請求 |

### Behaviour

- `input type="text" inputMode="numeric"`（避免部分瀏覽器對 `type=number` 的 spinner 與空值）。
- 送出時機：blur 或 Enter。
- 非法：不打 API；列旁文字錯誤（例如「每日時數須為 0 到 24 的整數」）；先前合法值保留在資料層，輸入框可暫留非法字元直到改對。
- 合法 0 或 24：2xx 後該列小計與 `cost-total` 更新，不必整頁重載。

### Accessibility

| Requirement | Implementation |
|---|---|
| Label | 欄名「每日時數」；每列 `aria-labelledby` 指向資源名＋欄名 |
| Keyboard | Tab 進框、Enter 送出、錯誤時焦點留在框內 |
| Contrast | 4.5:1；錯誤文字不得只靠顏色 |
| Live | 總額容器 polite；錯誤用 `aria-describedby` |

---

## RegionField

| Field | Value |
|---|---|
| Component | RegionField |
| Description | 每圖估價區域 |
| Category | input |

- 可見標籤「估價區域」。**暫定** Alex 使用 `<select>`（選項為本輪支援的區域碼清單，application-design 可改成文字碼但須同步 e2e）。David／Hannah 唯讀同一碼，不是另一個可焦點的 select。
- 未填：主區必填提示；官方價請求次數 0。
- 寫入後 2xx，假設列與後續查價用同一區域碼。

---

## PriceOverrideFields

| Field | Value |
|---|---|
| Component | PriceOverrideFields |
| Description | 未定價 SKU 文字欄；失敗列小時價欄 |
| Category | input |

- 僅 David 可編。
- SKU 送出後：stub 回價 → 單價等於 stub；stub 失敗 → 「官方價取得失敗」。
- 小時價覆寫：量綱為小時 list price；小計 `O × h × 30`；列上改為「Manual Override」。
- 不使用 modal／accordion（Q4=A）。

---

## PieBreakdown

| Field | Value |
|---|---|
| Component | PieBreakdown |
| Description | SVG 圓餅＋四類清單 |
| Category | display |

- 無 npm 圖表套件。切片 `aria-hidden="true"`；清單為可讀來源。
- 四類：compute／database／network／other；金額之和等於已定價總額。
- 全未定價或零節點：不畫「假的 100% other」。

---

## OverspendBanner

| Field | Value |
|---|---|
| Component | OverspendBanner |
| Description | 受保護頁主區頂橫幅 |
| Category | feedback |

### States

| State | Description | Trigger |
|---|---|---|
| hidden | 第一段，或可見圖皆未超支，或無預算 | AC-1.16／AC-6.5／AC-7.2 |
| single | 一張超支圖：圖名、總額、預算、前往 | AC-7.3 |
| multiple | 一條橫幅：數量＋至少點名一張 | AC-7.4 |

- 掛在 `Layout` 主欄頂，`role="status"`。
- 「前往成本畫面」為 `<button>` 或 `<a>`，可鍵盤啟動；預選 id ∈ 超支集合。
- 禁止「永遠不要再顯示」控件。

---

## SuccessCostCta

| Field | Value |
|---|---|
| Component | SuccessCostCta |
| Description | 產圖成功卡「查看預估成本」 |
| Category | navigation |

- 有 id：可啟動，進 `/cost` 預選該圖。
- 無 id：`disabled` 且有可見理由（或先存檔）。
- 不取代既有三顆 CTA。

---

## 狀態機（成本頁）

```
empty --選圖--> loading --2xx--> ready
loading --失敗--> error --重試--> loading
ready --切圖--> loading
ready --改時數合法--> ready (total live)
ready --改時數非法--> ready (row error, no request)
```

<!-- Text fallback: 空狀態選圖後載入；成功進 ready；失敗可重試；切圖重新載入；合法時數就地更新總額；非法時數不送出。 -->
