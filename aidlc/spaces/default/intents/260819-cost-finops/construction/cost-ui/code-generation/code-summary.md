# Code Summary — cost-ui

## 實際產出

| 檔案 | 變更 |
|---|---|
| `frontend/src/pages/CostPage.tsx` | **新增** |
| `frontend/src/cost/supportedRegions.ts` | **新增** |
| `frontend/src/cost/slotRegistry.tsx` | **新增**（B1 空） |
| `frontend/src/App.tsx` | `/cost` 路由 |
| `frontend/src/components/Sidebar.tsx` | 成本導覽 |
| `frontend/src/components/Layout.tsx` | banner slot |
| `frontend/tests/e2e/regression.spec.ts` | **+5** B1 cases |

## 關鍵決定

- **RegionField**：選項依 snapshot `allowed_regions`（依圖雲過濾）；TS／YAML 仍須同 PR 同步；無 `GET /regions`。
- **定價假設文案**：三雲皆「走官方價」（ADR-C1-09）；首次查價提示依雲別。
- **B1 禁止 DOM**：budget／banner／overspend-flag test-id 不渲染；slot 容器可常駐。
- **總額不重算**：pie 與 total 皆來自 GET snapshot。

## 驗證結果

| 項目 | 結果 |
|---|---|
| `npm run build` | 通過 |
| Playwright e2e（B1 五 case） | **5/5 通過**（test stack `localhost:8090`） |

## Review

**Verdict:** READY  
**Reviewer:** aidlc-architecture-reviewer-agent  
**Date:** 2026-08-20T02:30:00Z  
**Iteration:** 1

### 摘要

B1 成本頁、導覽與 e2e 規格已交付；B2 控件刻意缺席。無 Critical／Major。
