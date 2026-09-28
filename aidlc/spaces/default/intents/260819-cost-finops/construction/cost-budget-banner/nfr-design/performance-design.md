# Performance Design — cost-budget-banner

> Unit: `cost-budget-banner` · B2 · 承接 `../nfr-requirements/performance-requirements.md`

## 1. 延遲目標

| 路徑 | 目標 | 備註 |
|---|---|---|
| GET `/api/cost/banner` | Layout mount 後 **≤ 3s**（staging 手動） | **非** NFR-4 |
| PUT budget | p95 **< 500ms** 非正式 | 單列 UPSERT |
| session dismiss | 即時 DOM | 無 API |

## 2. `banner_for` 設計（Q1=A）

```
for d in visible_diagrams(user):          # O(N), N = 可見圖數
  if budget is None: continue
  total = lightweight_total(d)            # 無 HTTP；無完整 LineOut 組裝
  if is_overspent(total, budget): append
return BannerDto
```

| 優化 | 說明 |
|---|---|
| 跳過無 budget 圖 | 不跑 total |
| 重用 cache | 與 snapshot 同 `pricing_cache` |
| 不 serializing pie | banner 只需 total |

## 3. 前端（PERF-B-2）

```text
Layout mount ─┬─ GET /banner (async)
              └─ CostPage fetch (parallel, 若在同一 session)
```

- 橫幅 **不** block CostPage 首屏
- dismiss：CSS `display:none`；reload 再 GET

## 4. 量測

- Staging：DevTools 量 GET /banner
- CI：TestClient 功能；不量 3s

## 5. Code Gen 檢查清單

- [ ] `lightweight_total` 不觸發 N× full snapshot
- [ ] B1 路由 404 / 0 test-id 命中
