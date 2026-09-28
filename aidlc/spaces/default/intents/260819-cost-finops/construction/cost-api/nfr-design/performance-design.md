# Performance Design — cost-api

> Unit: `cost-api` · service · 承接 `../nfr-requirements/performance-requirements.md`

## 1. NFR-4 預算分配

| 階段 | 預算 | 設計手段 |
|---|---|---|
| DB：diagram + lines + overrides | ~200ms（設計假設） | 單次 query batch；≤50 列 |
| XML extract + align_lines | ~300ms | 純 CPU；禁 `parse_diagram_summary` |
| Cache lookup（全 hit） | ~50ms | indexed UK lookup |
| Calculator | 可忽略 | O(n) 純函式 |
| JSON serialize | ~100ms | Pydantic model |
| **合計（目標場景）** | **≤ 5s** | 快取命中或全 manual_override |

**排除場景**：冷查價 sequential HTTP（50×6s worst）— 不納入 NFR-4 驗收。

## 2. 定價 I/O 設計

```python
# pricing_client.fetch_hourly — 伪示意
httpx.Client(timeout=httpx.Timeout(3.0, connect=3.0))  # connect + read 各 3s
# 0 retry；失敗 → PriceMiss
```

| 決策 | 理由 |
|---|---|
| Sequential fetch | MVP 簡化；miss 列不阻塞其他列完成 |
| Cache before HTTP | NFR-4 依賴 hit 率 |
| `PriceUnsupported` 零 HTTP | FR-2.2；節省 RTT |

## 3. Cache 設計（Q3=A）

表 `pricing_cache`：

- 欄：`cloud`, `sku`, `region`, `hourly`, `fetched_at`
- 讀：miss 才 HTTP；hit 跳過
- 寫：僅 `PriceHit` 成功
- TTL：24h；讀時若過期視為 miss（懶刪除或忽略）

## 4. Router 薄層

- GET snapshot：**不**在 router 掛 `require_story_action(C1)`（FD Q2=A）
- PUT mutations：router 驗 Pydantic；hours 0–24 → 422
- OpenAPI 同 PR 更新（SEC-A-4）

## 5. 量測

| 環境 | 方法 |
|---|---|
| Staging | Playwright：選圖 → `cost-total` visible ≤5s |
| CI | TestClient 功能正確性；**不**量延遲 |
| 手動 | DevTools Network waterfall（選用） |

## 6. Code Gen 檢查清單

- [ ] 快取命中路徑無 N+1 query
- [ ] pricing timeout 常數集中一處
- [ ] `data-testid="cost-total"` 契約與 cost-ui 對齊
