# Business Rules — cost-calculator

> Unit: `cost-calculator` · Q1–Q3=A  
> 上游：`unit-of-work.md`、`unit-of-work-story-map.md`、`requirements.md`、`components.md`、`component-methods.md`、`services.md`。

## 不變量

| ID | 規則 | 違反 |
|---|---|---|
| BR-C-1 | 模組內不得 import `httpx`、SQLAlchemy `Session`、`HTTPException` | 靜態檢查失敗（NFR-3） |
| BR-C-2 | 所有出口金額為 `Decimal` 量化到小數兩位、`ROUND_HALF_UP` | PBT 失敗 |
| BR-C-3 | `total_priced` 與 `pie_buckets` 納入 `priced` **與** `manual_override`；不含 `unpriced`、`price_fetch_failed` | 覆寫列被漏加或未定價被灌水 |
| BR-C-4 | `hours == 0` ⇒ 小計 `0.00`；負 `hours`／`hourly` ⇒ `ValueError` | Q3=A |
| BR-C-5 | `budget is None` 或 `total == budget` ⇒ 未超支 | C1-7／AC-7.2 |
| BR-C-6 | 未知 pie category 歸 `other`，不丟例外 | Q2=A |
| BR-C-7 | 覆寫小時價與官方價用同一 `line_subtotal` | C1-5 AC-5.3 |
| BR-C-8 | 量化後 `pie_buckets` 四鍵之和 == `total_priced`（最大餘數法） | FR-3.4 |

## 驗證（PBT 性質，寫進測試檔而非 AC 本文）

對齊 `requirements.md` NFR-3 與 `stories.md` C1-2／C1-4 DoD：

- 未定價／`price_fetch_failed` 列加入前後 `total_priced` 與各 pie 桶不變
- **覆寫優先**：僅 `manual_override` 的列，`total_priced` 等於其精確小計再量化；官方 `hourly` 若同時存在仍以覆寫 hourly 計算（呼叫端應只傳覆寫單價）
- `priced` 與 `manual_override` 混合清單的 `total_priced` 等於兩類精確小計之和再量化
- **加總恆等**：`sum(pie_buckets.values()) == total_priced(lines)`（同一輸入）
- `line_subtotal` 對 `hourly, hours` 在合法域單調（hours 增加則小計不減）
- `hourly_from_monthly(730) == 1.00`（量化後）
- `is_overspent(t, None)` 恒 False
- `is_overspent(t, t)` 恒 False；`is_overspent(t, t - 0.01)` True（t>0）

## 錯誤政策

`ValueError` 字串含欄位名（`hours`／`hourly`／`monthly`）。`cost_service` **不得**把這例外直接當 422；API 應在進 library 前擋 0–24。PBT 的非法域單獨 `@given` 期望 `ValueError`。

## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-20T01:30:23Z
**Iteration:** 2

### 前次 Findings 狀態

| # | Iter-1 Severity | 狀態 | 說明 |
|---|---|---|---|
| M1 | Major | **已解決** | `business-rules.md` 新增「覆寫優先」PBT 兩條：單純 `manual_override` 清單的正確加總、`priced` 與 `manual_override` 混合清單的加總恆等。符合 NFR-3 DoD item 1 要求。 |
| M2 | Major | **已解決** | `business-logic-model.md` 明訂 `pie_buckets` 最大餘數法四步驟：用未量化精確值按桶累加 → 量化得 `total_q`（與 `total_priced` 同結果）→ 各桶獨立量化後以最大餘數法補差額 → 確保 `sum == total_q`。FR-3.4 正確性保證現已可驗證。 |
| M3 | Major | **已解決** | `business-rules.md` 新增「加總恆等」PBT 性質：`sum(pie_buckets.values()) == total_priced(lines)`（同一輸入）。與 BR-C-8 不變量互相印證。 |
| Minor-4 | Minor | **已解決** | `domain-entities.md` 明確宣告「**不**帶 `subtotal` 欄」，`business-logic-model.md` 的 `total_priced` 改為以「`hourly` 非空」作篩選依據，兩份文件一致。 |
| Minor-5 | Minor | **已解決** | 常數改名為 `DAYS_PER_MONTH = 30`，附注「日數因子，不是『每月工時』」，與 `HOURS_PER_MONTH_LIST = 730` 語意明確區隔。 |

### Findings

| # | Severity | Location | Finding | Recommendation |
|---|---|---|---|---|
| 1 | Minor | `business-rules.md` § PBT 性質「覆寫優先」（M1 修復引入） | 性質描述夾帶 service 層關注點。「官方 `hourly` 若同時存在仍以覆寫 hourly 計算（呼叫端應只傳覆寫單價）」描述的是 `cost_service` 如何組裝 `LineForCalc` 的職責，而非 library 的可測試行為。`domain-entities.md` 確認 `LineForCalc` 僅有單一 `hourly` 欄，library 層不存在「兩種 hourly 同時存在」的情境，實作者撰寫 Hypothesis `@given` 時可能因此困惑（是否須產生兩個不同 hourly 值？）。 | 將括號內的服務層說明移至 `business-logic-model.md`「不在本 unit」段，使 PBT 性質保持純粹的輸入→輸出斷言語意。 |
| 2 | Minor | `business-logic-model.md` § `pie_buckets` 步驟 3（M2 修復引入） | 最大餘數法描述「依各桶量化前小數部分由大到小…分配差額（分）」未指定**平局排序規則**：當兩桶的小數部分相等時，哪桶優先取得差額分無定義。不影響「加總恆等」PBT 性質（sum 必然等於 total_q 無論哪桶取差額），但若 PBT 測試斷言個別桶值（如 compute 桶確切金額），不同實作可能產出不同結果，造成測試脆弱。 | 補充平局規則，例如：「小數部分相同者按固定順序（compute → database → network → other）排列」；或明示「個別桶值不作 PBT 斷言，僅斷言加總恆等」。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 簽名比對（`component-methods.md`） | PASS | `hourly_from_monthly`、`line_subtotal`、`total_priced`、`pie_buckets`、`is_overspent` 五個函式簽名與 `component-methods.md` 完全吻合；BR-C-1 禁用 import 規則文字亦與上游一致。 |
| BR-C-8 vs. business-logic-model 比對 | PASS | BR-C-8「量化後 `pie_buckets` 四鍵之和 == `total_priced`（最大餘數法）」與 `business-logic-model.md` 四步驟算法完全對應；`total_q` 推導與 `total_priced` 同路徑，加總恆等保證成立。 |
| pie_buckets 量化策略 | PASS（含注意事項） | M2 修復明確定義最大餘數法四步驟，最大誤差 ≤ 0.02（4 桶 × 0.005），算法必然終止。平局排序未定義（Finding #2），不影響加總正確性，影響個別桶確切值的可重現性。 |
| PBT 覆蓋度對比 NFR-3 / DoD | PASS | 「覆寫優先」（兩條）、「加總恆等」、未定價排除、時數公式單調性均已列入；覆蓋 NFR-3 全部明訂項目。 |
| BR-C-4 vs. business-logic-model 比對 | 部分 PASS | `business-logic-model.md` `line_subtotal` 段仍未明寫「負 hours → ValueError」，但 BR-C-4 不變量表為主文，低重要性不一致；此問題已存在於 Iter-1 且未因本次修復引入，不重新列出。 |

### Summary

三項 Iter-1 Major（覆寫優先 PBT、`pie_buckets` 量化策略、加總恆等 PBT）及兩項 Minor 均已解決。本輪從兩項修復中各發現一個新 Minor：M1 修復的 PBT 性質描述混入服務層關注點，M2 修復的最大餘數法平局排序未定義。兩者均不影響核心正確性與加總恆等性質，不阻擋實作。判定 **READY**。
