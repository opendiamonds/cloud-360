# Scalability Design — cost-budget-banner

> Unit: `cost-budget-banner` · B2 · 承接 `../nfr-requirements/scalability-requirements.md`

## 1. 聚合複雜度

- `banner_for`：**O(N)**，N = 使用者可見 diagram 數（通常 ≪ 100）
- 每圖一次 lightweight total（≤50 列/圖）
- Worst：N×50 列 CPU + cache lookup — MVP 可接受

## 2. 橫幅 UX 上界（SCL-B-1）

- 多圖超支 → **單一**橫幅
- `count` 欄位承載數量；CTA 導向 `sample.id`

## 3. 不引入

| 元件 | 理由 |
|---|---|
| 背景 job 預計算超支 | out of scope |
| Push notification | out of scope |
| Banner 專用 cache | 依賴 cost-api DB + pricing_cache |

## 4. 未來擴展

N>100 或頻繁 poll → ETag / 增量 — 需新 intent。

## 5. Code Gen 檢查清單

- [ ] 單回應 `{active, count, sample?}`
- [ ] 無 N 次 HTTP 自呼
