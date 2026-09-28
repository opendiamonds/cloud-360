# Phase Check — Inception → Construction

> delivery-planning Step 6 · Intent: `260819-cost-finops` · 2026-08-20

## 判定

**PASS**。需求、故事、元件、unit、Bolt 無斷鏈。已知缺口已標承載 Bolt，不擋進入 Construction。

## 追溯檢查

| # | 檢查 | 結果 |
|---|---|---|
| ① | FR 有故事承載 | FR-1→C1-1／C1-5；FR-2→C1-2／C1-5；FR-3→C1-2／C1-4；FR-4→C1-1／C1-4；FR-5→C1-1／C1-3／C1-7；FR-6→C1-6／C1-7；FR-7→C1-1／C1-2／C1-4／C1-6；FR-8→C1-1／C1-4／C1-5／C1-6。**8／8** |
| ② | NFR 有承載 | NFR-1／2→B1+B2 UI；NFR-3→`cost-calculator`；NFR-4→B1 快取／stub；NFR-5→RBAC 403。**5／5** |
| ③ | 故事有 unit | C1-1～C1-7 皆有主責（`unit-of-work-story-map.md`）。**7／7** |
| ④ | AC 有歸屬 | `stories.md` `**AC-` 標題 **47** 條；story-map 加總 13+5+2+9+9+4+5=47 |
| ⑤ | 設計元件有 unit | router／service／extractor／mapper／pricing_client／price_cache→`cost-api`；calculator 元件→`cost-calculator`；四表＋新種子→`cost-schema-rbac`；CostPage／Hours／Pie／CTA／Sidebar→`cost-ui`；OverspendBanner→`cost-budget-banner`（`components.md`） |
| ⑥ | Bolt 涵蓋全部 unit | 5 unit 皆在 B1 或 B2（`bolt-plan.md`） |
| ⑦ | 無幻影故事 id | yaml 與 story-map 只用 C1-1～C1-7；無 C2／C3 unit |

## 規模

| 層 | 數量 |
|---|---|
| FR | 8 組（FR-1～FR-8） |
| NFR | 5 |
| 故事／AC | 7 則／47 條 |
| ADR-C1 | 8（01–08） |
| unit／邊 | 5／5（無環） |
| Bolt | 2，序列 B1 → B2 |

## 追溯鏈

```
requirements（FR-1～8／NFR-1～5）
  → stories（C1-1～C1-7） ↔ mockups（/cost、test-id、橫幅位置）
  → components + decisions
  → units（五 unit DAG）
  → bolts（B1 第一段四 unit；B2 banner）
```

## 帶入 Construction 的缺口（不擋）

| 缺口 | 承載 |
|---|---|
| 公開價目真實 URL（OQ-3） | B1 infrastructure-design；B1 可以 stub 合閘 |
| 跨 unit DOM 擴充機制 | B2 functional-design |
| `coverage` 細部／捨入模式 | B1 functional-design（application-design reviewer Minor） |
| 對比與窄視窗 | 人工；B1／B2 e2e 不取代 |
| 超支 LLM 建議 | 後續 intent，本輪 Won't Have |

## 對齊修正註記

上游 C1-6 AC 編號為 6.1／6.2／6.3／6.5（無 6.4 標題）。units-generation story-map 已註明，**不回改** `stories.md`。
