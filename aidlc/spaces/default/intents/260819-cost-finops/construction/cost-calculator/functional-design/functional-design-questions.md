# Functional Design — 釐清問題（cost-calculator）

> Stage: functional-design（Construction 3.1，inline）· Unit: `cost-calculator` · Kind: **library**
> 本 unit 不產 `frontend-components.md`（`produces_kinds` 僅 ui）。
> 上游：`unit-of-work.md`、`unit-of-work-story-map.md`、`requirements.md`、`components.md`、`component-methods.md`、`services.md`。
> **成本揭露**：3 題。答完產出 business-logic-model／business-rules／domain-entities。本 unit **gate: false**（五 unit 都寫完才開 Functional Design 總閘）。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 純函式；禁止 httpx／Session／`HTTPException` | `component-methods.md`、NFR-3、ADR-0006 |
| `hourly_from_monthly(M)=M/730`；`line_subtotal=hourly×hours×30`；覆寫 `O×h×30` | methods／C1-4／C1-5 |
| `total_priced` 只加 `priced` 與 `manual_override` | methods |
| 圓餅四類 compute／database／network／other | FR-3.4 |
| `is_overspent`：budget `None` → False；相等 False | methods、C1-7 |
| 出口 USD **兩位小數** | ADR-C1-07 |
| 時數區間 0–24 由 API 422；calculator 收到的是已合法整數 | C1-4 |

協作故事：C1-2、C1-4、C1-5、C1-7（`unit-of-work-story-map.md`）。

---

## Q1. 兩位小數怎麼捨入？

> ADR-C1-07 把銀行家捨入 vs 四捨五入留給本站。Hypothesis 必須用同一規則比。

A. **`ROUND_HALF_UP`（建議）**：人眼估價比較直覺；Pydantic／JSON number 也常這樣。在 calculator **出口一次**量化，內部用 `Decimal`。  
B. **銀行家捨入（`ROUND_HALF_EVEN`）**：統計較不偏，但 `1.225` → `1.22` 難跟產品說明。  
C. **先量化每列小計再加總**（仍 HALF_UP）。代價：多列 0.005 可能與「先加再開」差 1 分。  
D. Not yet defined  
X. Other (please specify)

[Answer]: A. **`ROUND_HALF_UP`（建議）**

---

## Q2. 圓餅四類誰決定？

> calculator 的 `pie_buckets` 需要每列已有 category。SKU 對照在 `sku_mapper`（`cost-api` unit）。

A. **呼叫端傳入已分好的 `category`；calculator 只加總四桶（建議）**。library 不讀 YAML、不猜 SKU。未知 category → `other`。  
B. **calculator 內建 SKU→類別表**。代價：與 `sku_map.yaml` 雙來源。  
C. Not yet defined  
X. Other (please specify)

[Answer]: A. **呼叫端傳入已分好的 `category`；calculator 只加總四桶（建議）**

---

## Q3. 非法輸入在 library 層怎麼處理？

> HTTP 422 屬於 `cost-api`。純函式仍可能被測試或誤用傳入負時數、負單價。

A. **契約前置條件：負數 `hours`／`hourly` 與非有限 Decimal 丟 `ValueError`（建議）**。0 時數小計為 `0.00`。不把例外翻成 HTTP。  
B. **clamp 到 0，不丟例外**。代價：默默吞掉 bug。  
C. **完全信任呼叫端，不檢查**。代價：PBT 無法標非法域。  
D. Not yet defined  
X. Other (please specify)

[Answer]: A. **契約前置條件：負數 `hours`／`hourly` 與非有限 Decimal 丟 `ValueError`（建議）**
