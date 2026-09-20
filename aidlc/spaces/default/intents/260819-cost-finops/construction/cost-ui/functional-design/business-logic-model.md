# Business Logic Model — cost-ui

> Unit: `cost-ui` · Q1–Q4=A

## 頁面狀態機

```
forbidden-route (CapabilityRoute) ──► /403
empty (no diagrams) ──► 空狀態 CTA
loading ──► spinner/skeleton，無 cost-total
error ──► 重試按鈕
ready ──► 依 snapshot 渲染
  ├─ region_required: 提示填 region
  ├─ total non-null: 顯示 cost-total + pie
  └─ total null: M5b 說明，cost-total 0 命中
```

## 資料流

```
AuthContext.can(story, action)
GET /diagrams → DiagramSelect options
GET /diagrams/{id} → snapshot state
PUT * → optimistic 可選；本輪採「2xx 後 merge 回 snapshot 欄位」
```

切圖：abort 進行中 fetch；新 id 走 loading。

## 校驗（送出前）

| 控件 | 規則 |
|---|---|
| HoursInput | 整數 0–24 |
| RegionField | 非空字串 |
| Override 價 | 非負數、最多兩位小數 |

非法：列旁錯誤；**不**發 PUT。

## 可見性與錯誤

- GET 404：視為「圖不可見」→ **empty 狀態**（不顯示 error）
- GET 403：不應在已過 CapabilityRoute 後發生；若發生顯示 error
- PUT 422：列級錯誤訊息；還原輸入為上次合法 snapshot 值

## Deep link

`/cost?diagram=42`：CostPage mount 時若 42 不在 items → **empty 狀態**（不顯示 error／重試；避免 security-404 誤導）。

## B2 掛點（B1 只留空 slot）

`data-slot="cost-overspend"`、`data-slot="cost-banner"` 常駐 DOM；B1 不 import `cost-budget-banner` 元件。

### Slot Registry API（B2 注入契約）

`frontend/src/cost/slotRegistry.tsx`（由 **cost-ui** 擁有並 export）：

```tsx
export function mountCostSlot(
  slot: "cost-overspend" | "cost-banner",
  node: React.ReactNode
): () => void;
```

實作：`document.querySelector('[data-slot="'+slot+'"]')` + `createRoot(...).render(node)`；回傳 unmount。B2 `registerCostBudgetBanner()` **只**從此模組 import，不直接操作 DOM。

## 不在本 unit

`OverspendBanner` 行為、預算 PUT、Playwright 腳本本體、OpenAPI 生成。
