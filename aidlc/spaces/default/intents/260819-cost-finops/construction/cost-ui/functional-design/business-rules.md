# Business Rules — cost-ui

> Unit: `cost-ui` · Q1–Q4=A

## 不變量

| ID | 規則 | 違反 |
|---|---|---|
| BR-U-1 | 無 `C1.view` 不渲染成本 Sidebar 組 | AC-1.1 |
| BR-U-2 | `/cost` 必包 `CapabilityRoute storyId="C1" action="view"` | 403 路由 |
| BR-U-3 | B1：`cost-budget`／`cost-overspend-flag`／`cost-banner` **0 命中** | AC-1.16 |
| BR-U-4 | 非法時數不 PUT；422 時列值以 snapshot 為準 | C1-4 |
| BR-U-5 | `cost-total` 僅在 `snapshot.total != null` 渲染 | M5b |
| BR-U-6 | 圓餅與總額共用 snapshot.pie；不前端重算 | FR-3.4 |
| BR-U-7 | 型別只來自 generated `api.d.ts` | OpenAPI drift |
| BR-U-8 | B2 slot 常駐但 B1 空 | UG 整合契約 |

## 角色與控件

| 控件 | can edit |
|---|---|
| HoursInput | C1h |
| RegionField | C1r |
| SKU／override 欄 | C1o |
| 預算欄 | C1b（B2；B1 無 DOM） |

## Playwright 對照（B1）

- Sidebar「成本 → 預估成本」可見（Alex）
- 列對到圖 label
- 改時數總額變
- `cost-pie-legend` 四類文字
- 無 budget／banner test-id

## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-20T01:48:46Z
**Iteration:** 1

### Findings

| # | 嚴重度 | 位置 | 發現 | 建議 |
|---|---|---|---|---|
| 1 | Major | `functional-design-questions.md` Q1=A / `interaction-spec.md` RegionField | `RegionField` 設計為 `<select>`，選項來源標注為「本輪支援的區域碼清單」，但整份功能設計（含 domain-entities、business-logic-model、frontend-components）均未說明此清單如何取得：無對應 API 端點（`component-methods.md` 無 `GET /regions`）、無靜態 YAML 參照、亦未從 `coverage` 欄位推導。developer 在實作時須自行決定架構（硬編碼 AWS 區域碼 vs. 新增 API endpoint vs. 改為文字輸入），任何決策若與 cost-api 契約不符均需補端點或改 OpenAPI，造成跨 unit 影響。 | 在 `frontend-components.md` 的 RegionField 規格補一行：說明選項清單來源（例：「前端靜態陣列 `SUPPORTED_REGIONS`，由 `backend/cost/sku_map.yaml` 所含 region 欄 derive，或直接 hardcode 本輪支援清單」），並於 `domain-entities.md` 記錄此清單型別。若改為 text input 須同步更新 `interaction-spec.md` 並通知 QA 調整 Playwright selectOption 斷言。 |
| 2 | Minor | `business-logic-model.md` 可見性與錯誤 | `GET 404` 在 deep link 情境下回應為「空狀態或錯誤（不暴露 id 存在）」，兩條路徑並列但未擇一。`interaction-spec.md` 的 CostPageShell States 中 `empty` 與 `error` 觸發條件各自對應 AC-1.3 與 AC-1.13，不包含「valid id 但 404」場景；mockups M3 對應無圖/未選圖，M4 對應請求失敗，均未明確涵蓋 deep-link 404。Playwright 測試若按 empty state 寫斷言（無重試按鈕）與按 error state 寫（有重試）實作後差異明顯。 | 在 `business-logic-model.md` 的「GET 404」處擇一：「顯示 error state（含重試）」或「顯示 empty state（不顯示 id 存在）」，並在 mockups / interaction-spec 補注（可在 M3 或 M4 追加一行 fallback 說明）。 |
| 3 | Minor | `frontend-components.md` TotalSection / `domain-entities.md` | `cost-unpriced-count` 渲染條件未說明 `unpriced_count == 0` 時是否保留 DOM 節點。mockups M2 僅示意 `unpriced_count > 0` 的案例（「1 項尚未定價」），M5b 示意 3 項。全部已定價時節點是否 0 命中、顯示「0 項尚未定價」或隱藏均無定義，可能影響 Playwright `expect(locator).toHaveCount(0)` 斷言穩定性。 | 在 `frontend-components.md` TotalSection 補注：「`unpriced_count == 0` 時 `cost-unpriced-count` 節點 **0 命中**（不渲染）」，或明確允許 0 命中以外的實作，並在 Playwright 測試規格備注。 |
| 4 | Minor | `domain-entities.md` / `frontend-components.md` API 整合 | `coverage` 與 `pricing_as_of` 標注「顯示於定價假設區（FR-3.5）」，但無對應渲染格式規則：`coverage` 型別為 `[{cloud, mode}]` 陣列，mockups M2 顯示「本輪：AWS 走官方價 · 其餘雲全 Manual Override」，但文字轉換規則（mode → 中文描述、多雲分隔符、排序）未於功能設計中定義。developer 的各自實作將產生難以比對的 Playwright text 斷言。 | 在 `frontend-components.md` 的定價假設區補 coverage 渲染規則表：`official_list` → 「走官方價」；`manual_override_only` → 「全 Manual Override」；多條以「·」分隔；雲名固定大寫（AWS / GCP / Azure）。或於 mockups M2 text fallback 中增補格式說明並標記為 e2e 比對字串。 |

### 驗證工具結果

| 工具 | 結果 | 說明 |
|---|---|---|
| BR → upstream 追溯（手動） | PASS | BR-U-1 ↔ AC-1.1；BR-U-2 ↔ CapabilityRoute（components.md）；BR-U-3 ↔ AC-1.16 + ADR-C1-08；BR-U-4 ↔ interaction-spec HoursInput；BR-U-5 ↔ M5b；BR-U-6 ↔ component-methods calculator；BR-U-7 ↔ unit-of-work Q5=A；BR-U-8 ↔ unit-of-work cost-budget-banner 定義。8 條全部可追溯，無懸空引用。 |
| B1 禁止渲染一致性（交叉比對） | PASS | ADR-C1-08 / AC-1.16 / interaction-spec 全域規則 / frontend-components.md B1 禁止渲染 / BR-U-3 四處一致：`cost-budget`、`cost-overspend-flag`、`cost-banner` 0 命中；slot 容器 DOM 可常駐（BR-U-8）。無矛盾。 |
| 元件 ID 引用解析 | PASS | `CostNavGroup`、`CostPage`、`HoursInput`、`RegionField`、`PieBreakdown`、`ResourceTable`、`SuccessCostCta`、`OverspendBanner` 均在 `components.md` 前端元件表或 `component-methods.md` 前端方法節有對應定義。無幽靈元件。 |
| API 端點引用（domain-entities 契約表） | PASS（1 gap） | `GET /diagrams`、`GET /diagrams/{id}`、`PUT .../region|hours|sku|override` 均在 `component-methods.md` `cost_router` 表中存在且形狀相符。Finding #1（無 `GET /regions`）已單獨記錄。 |
| test-id 完整性（mockups ↔ 功能設計） | PASS | mockups 定義的 8 個 test-id（`cost-total`、`cost-overspend-flag`、`cost-banner`、`cost-hours-input`、`cost-pie-legend`、`cost-unpriced-count`、`cost-region`、`cost-budget`）均在 frontend-components.md 或 BR-U-3 覆蓋；B1 禁止項（`cost-budget`、`cost-overspend-flag`、`cost-banner`）明確標注。 |
| 頁面狀態機可達性 | PASS | `forbidden-route → /403`、`empty`、`loading`、`error`、`ready`（含 region_required / total null / total non-null 子分支）全部可從 mount 到達，無死節點；`error → loading（重試）` 回邊存在。 |

### 摘要

**繁體中文摘要**：cost-ui 功能設計整體結構清晰。8 條不變量全部可追溯至上游契約，B1 禁止渲染條件在四份文件中一致，頁面狀態機無死節點，元件樹與 API 契約引用均可解析。主要缺口為 `RegionField` 選項清單來源未定義（1 項 Major）——developer 須自行決定是否新增 API endpoint，若決策偏差將牽動 cost-api 契約。3 項 Minor 均有對應上游參照但需補齊渲染細節，不阻擋本 unit 實作啟動。零 Critical，1 Major，判定 **READY**；建議在第一個 PR 送審前於 `frontend-components.md` 補 RegionField 選項來源說明，以避免 QA 階段改介面觸發 e2e 回歸。
