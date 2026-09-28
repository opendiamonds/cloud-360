# Business Rules — cost-api

> Unit: `cost-api` · Q1–Q5=A  
> 上游：`unit-of-work.md`、`requirements.md`、`component-methods.md`、`team-practices.md`、`decisions.md`。

## 不變量

| ID | 規則 | 違反 |
|---|---|---|
| BR-A-1 | Router 不含公式、httpx；calculator 不含 Session | 分層塌縮 |
| BR-A-2 | 可見性：非 owner 且未分享 → **404**；可見無 `C1.view` → **403**。**GET snapshot 的 C1.view 在 service 內檢查**，不用 router Depends，避免 404/403 順序反轉 | 洩漏／錯誤碼 |
| BR-A-3 | 時數非法 → **422**；DB 列不變 | C1-4 AC |
| BR-A-4 | 各 PUT 用對應 story edit（C1h/r/o）；無權 **403** | RBAC 測試 |
| BR-A-5 | 無 region 時不呼叫 `pricing_client`；`region_required=true` | FR-4.1 |
| BR-A-6 | `PriceUnsupported` → `unpriced`；`PriceMiss` → `price_fetch_failed` | FR-2.2／2.3 |
| BR-A-7 | 列 status 優先序見 Q3=A（override 最高） | 覆寫被官方價蓋掉 |
| BR-A-8 | 未定價／失敗列不進 `total`／`pie` | FR-3.1、calculator BR-C-3 |
| BR-A-9 | 快取命中 TTL<24h 不打外網；`PriceHit` 才寫 cache | ADR-C1-04 |
| BR-A-10 | 第一段 `budget=null`、`overspent=false`；budget/banner 路由 **404** | ADR-C1-08、AC-1.16 |
| BR-A-11 | 禁止 `parse_diagram_summary`、Cost Explorer 路徑字串 | FR-1、FR-2.5 |
| BR-A-12 | OpenAPI 與 `api.d.ts` 同步；**Construction 須同步更新** `component-methods.md` GET audit 形狀，加入 `mxcell_id`（nullable），與 `cost-schema-rbac` 一致 | 契約 drift |

## HTTP 對照（第一段）

| 端點 | 授權 | 2xx | 4xx |
|---|---|---|---|
| GET `/diagrams` | C1.view | items | 403 |
| GET `/diagrams/{id}` | C1.view | 快照 | 404/403 |
| PUT region/hours/sku/override | 各 edit story | 契約 body | 404/403/422 |
| GET audit | C1.view | items | 404/403 |
| PUT budget、GET banner | — | — | **404**（未註冊） |

## 驗證（TestClient／屬性）

- Alex：hours/region 2xx；David/Hannah：403
- David：override/sku 2xx；Alex：403
- hours -1/25 → 422
- 無權 diagram id → 404（非 403）
- stub client：`PriceUnsupported` 雲別 0 次 HTTP
- snapshot：`sum(pie)==total` 當 total 非 null（delegates calculator）

## 錯誤政策

- DB 錯誤：500 + log；不部分 commit align
- `ValueError` from calculator：視為 service bug（輸入應已驗）；不暴露給 client

## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-20T01:44:17Z
**Iteration:** 1

### Findings

| # | Severity | Location | Finding | Recommendation |
|---|---|---|---|---|
| 1 | Major | `business-logic-model.md` § `get_snapshot` 步驟 1–2 | Pseudocode 把「1. load UserDiagram → missing/不可見 → 404」列在「2. require C1.view (router Depends) → 403」之前，意圖符合 Q2=A（404 先於 403）。但 FastAPI Depends 在 route handler body **之前**執行。若開發者把 `require_story_action("C1")` 實作成 FastAPI `Depends`，在「使用者無 C1.view 且 diagram 不存在」的邊界情境，Depends 先觸發 → 回傳 403，而非設計要求的 404。設計文件未明確說明：應在 service 函式**內部**（可見性確認後）呼叫 `require_story_action`，還是用 FastAPI Depends（會反轉順序）。這項模糊性足以讓開發者在正確性上做出錯誤選擇。 | 在 `business-logic-model.md` 補充說明：「`require C1.view` 在 service 函式**內部**、可見性確認後執行，不作為路由層 FastAPI `Depends`，以確保 Q2=A 的 404-先-403 順序成立。」對應的 `apply_*` 方法亦需相同說明。 |
| 2 | Major | `domain-entities.md` § AuditItem + BR-A-12 vs. `component-methods.md` GET audit | BR-A-12 要求「audit items 含 `mxcell_id`」；`domain-entities.md` AuditItem 也含此欄（列級必填，預算 null）；`cost-schema-rbac` FD 的 `CostAuditEvent` 同樣標注「Construction 須同步擴充 OpenAPI 回應形狀」。但上游**共享契約** `component-methods.md` GET `/diagrams/{id}/audit` 回應形狀 `{ items: [{ at, actor, diagram_id, field, old_value, new_value }] }` **不含** `mxcell_id`。`cost-ui` 依 generated `api.d.ts`（Q5=A）消費 API，若共享契約未更新，前端開發者得到的型別定義缺欄，稽核 UI 無法識別哪個 cell 被異動。本 unit FD 把修補寫成「Construction 動作」而非設計修正，不足以封閉契約缺口。 | 在 `component-methods.md` GET audit 回應形狀補入 `mxcell_id?`（nullable，預算類型為 null），使共享契約與 `domain-entities.md` / BR-A-12 一致；或在 `domain-entities.md` 明訂「`mxcell_id` 本輪僅儲存，不在 GET audit 回應中」並同步移除 BR-A-12 的對應要求。兩者擇一在設計層確認，Construction 開始前需解決。 |
| 3 | Minor | `business-logic-model.md` § `get_snapshot` 步驟 1–14 | 步驟中未出現 `unpriced_count` 的計算方式。`domain-entities.md` 定義「`status ∈ {unpriced, price_fetch_failed}` 的列數」，但 pseudocode 在組 Snapshot 時未明文寫出此計數步驟，開發者須跨文件推敲，影響 pseudocode 完整性。 | 在步驟 8 之後（或組 Snapshot 段）補一行：「`unpriced_count = count of lines where status ∈ {unpriced, price_fetch_failed}`」。 |
| 4 | Minor | `business-logic-model.md` § `get_snapshot` 步驟 8 與步驟 13 | Q4=A 明定 `pricing_coverage.yaml` **啟動時**載入（靜態）。步驟 8 使用 `cloud mode official_list` 做判斷，但步驟 13 才寫 `coverage = load_static_coverage_yaml()`。若依 pseudocode 字面順序在步驟 13 才載入，步驟 8 的 `cloud mode` 無來源；若為啟動時全域載入，步驟 13 應改寫為「讀取已快取的 coverage」。現行描述會誤導開發者認為 YAML 在每次請求中於步驟 13 動態載入。 | 步驟 8 前補「`coverage_map = startup_coverage_cache`（啟動時從 YAML 載入）」，步驟 13 改為「`coverage = list(coverage_map.values())`」，明確與 Q4=A 啟動載入語意一致。 |
| 5 | Minor | `business-logic-model.md` § `record_audit` | 在 `record_audit` 使用方清單中列入「（第二段）`apply_budget`」，但 `apply_budget` 明確屬於 `cost-budget-banner` 範疇，本 unit 不實作。對施工者略造成困惑，可能誤以為本 unit 也需實作 `apply_budget` 的稽核路徑。 | 將「（第二段）`apply_budget`」移至 §「不在本 unit」段，或在現行位置更醒目地標注「本 unit 不實作；B2 時由 `cost-budget-banner` 補充」。 |

### Validation Tool Results

| 工具 | 結果 | 說明 |
|---|---|---|
| B1 bolt plan 路由對齊（ADR-C1-08） | PASS | `business-logic-model.md` 路由表明文標注「PUT .../budget、GET /banner → 404（未註冊）」；BR-A-10 一致；`unit-of-work.md`、`services.md`、`functional-design-questions.md` Q5=A 全部一致。 |
| PriceUnsupported 語意比對 | PASS | BR-A-6「PriceUnsupported → unpriced；PriceMiss → price_fetch_failed」與 `component-methods.md` pricing_client 定義一致；`pricing_client.fetch_hourly` pseudocode 在 `manual_override_only` 模式直接 return PriceUnsupported 且不發 HTTP，符合 FR-2.2、BR-A-5。 |
| Calculator 整合契約比對 | PASS | `LineForCalc` 形狀（status、hourly、hours、category）、五函式簽名（`line_subtotal`、`total_priced`、`pie_buckets`、`is_overspent`、`hourly_from_monthly`）與 `cost-calculator` FD（READY）的 `component-methods.md` 及 domain-entities 完全吻合；BR-A-8「未定價／失敗列不進 total／pie」與 calculator BR-C-3 一致。 |
| 404/403 順序宣告 | PARTIAL（見 M1） | Q2=A、BR-A-2、HTTP 對照表三者均宣告「404 先於 403」；`business-logic-model.md` pseudocode 步驟編號也是此順序。但「router Depends」實作路徑與 FastAPI 執行模型矛盾（M1），文件宣告正確、實作路徑未明確界定。 |
| Audit mxcell_id 契約一致性 | FAIL（見 M2） | BR-A-12 與 domain-entities.md 要求 audit items 含 `mxcell_id`；但共享契約 `component-methods.md` GET audit 回應不含此欄。`cost-schema-rbac` 審查 Minor #1 亦識別此缺口，但至今未在共享契約層修正。 |
| BR-A-1 分層隔離（calculator 無 Session；router 無公式） | PASS | `domain-entities.md` §邊界明文禁止；`business-logic-model.md` 步驟及模組邊界圖均遵循；與 `components.md` 責任欄一致；cost-calculator FD BR-C-1 互相呼應。 |
| budget=null / overspent=false 快照不變量 | PASS | domain-entities.md Snapshot 表明「budget: null（第一段恒 null）、overspent: false（第一段恒 false）」；BR-A-10 明文；與 `component-methods.md` 快照欄位定義一致。 |
| Coverage YAML 載入語意 | PARTIAL（見 Minor #4） | Q4=A 明定啟動靜態載入；步驟 8 使用 cloud mode 但步驟 13 才寫 load，順序矛盾（Minor）。 |

### Summary

`cost-api` functional design 整體結構清晰，B1 bolt plan（不掛 budget/banner 路由）、PriceUnsupported 語意、calculator 整合契約（五函式簽名與 LineForCalc 形狀）均與上游共享契約逐項吻合，404/403 設計意圖（Q2=A）在規則層一致。發現兩項 Major：M1 為 FastAPI Depends 執行順序與 pseudocode 步驟標注的矛盾，未明確指定 `require_story_action` 應在 service 函式**內部**可見性確認後呼叫；M2 為 GET audit 回應中 `mxcell_id` 的共享契約缺口，`component-methods.md` 未更新，`cost-ui` 型別會遺漏此欄。兩項 Major 均可一行修正設計文件或補一句說明解決，不需更動邏輯；三項 Minor 不阻擋實作。判定 **READY**。
