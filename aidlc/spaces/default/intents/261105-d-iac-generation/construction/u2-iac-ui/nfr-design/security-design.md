# Security Design — u2-iac-ui

> Q2=A／Q3=A · NFR3.UI／NFR5。

## 錯誤與密文

- 單一 `mapIacErrorCode(code) → 文案`；toast／inline 只顯示短語。
- **禁止** `console.log`／debug 傾印 HCL、改寫前後明文、完整 axios／fetch body（含 DEV）。
- 下載：`blob`＋物件 URL；revoke 於完成／unmount；無密文 query。

## 授權 UX

- 403 → 缺權說明；入口 disabled 不發請求（可選探針除外且不得洩漏產物）。

## a11y（WCAG 2.1 AA 目標 · Q3=A）

- 下載確認：`role="dialog"`（或既有 Dialog）、focus trap、Esc／取消、**關閉後 focus 回到觸發下載的控制項**（若已卸載則回步驟區主要 CTA）。
- Findings 嚴重度：文字標籤＋（可選）色；不單靠色。
- 步驟與主要 CTA 可鍵盤到達。

## 不做

- Apply UI；把 JWT 寫进 localStorage 新鍵（沿用既有 auth 機制）。

<!-- confirmed: Looks correct -->
