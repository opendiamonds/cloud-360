# Security Design — cost-ui

> Unit: `cost-ui` · ui · 承接 `../nfr-requirements/security-requirements.md`

## 1. 授權 UI 模式

```text
useAuth().can('C1', 'view')
  false → CostNavGroup 不渲染；/cost CapabilityRoute 擋下
  true  → 顯示導航 + 頁面

控件 readOnly：
  C1h.edit → HoursInput
  C1r.edit → RegionField
  C1o.edit → SKU / override 欄
```

**安全邊界在 API**：前端 gating 為 UX；403 不 crash（顯示錯誤態）。

## 2. XSS 防護（SEC-U-2）

| 資料 | 渲染 |
|---|---|
| `line.label` | React text node（預設 escape） |
| `coverage` 文案 | 常數模板 + 雲代碼白名單 |
| SVG pie | 數值 attr；無 user HTML |

**禁止** `dangerouslySetInnerHTML` on label 或 snapshot 字串。

## 3. 客戶端校驗（SEC-U-3）

- Hours 0–24：非法不 PUT
- 僅輔助；篡改請求仍由 backend 422/403

## 4. 儲存與 secret

- 不寫 JWT 至 localStorage（沿用既有 auth）
- 不 cache snapshot 含 PII 至 persistent storage

## 5. B1 DOM 契約（SEC-U-4）

| test-id | B1 |
|---|---|
| `cost-budget` | **0 命中** |
| `cost-banner` slot | 空 |
| `cost-overspend` slot | 空 |

Playwright AC-1.16 可機械驗證。

## 6. Code Gen 檢查清單

- [ ] CapabilityRoute story=`C1`
- [ ] label 無 raw HTML injection 路徑
- [ ] 403 顯示 error state 非白屏
