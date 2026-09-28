# Security Requirements — cost-ui

> Unit: `cost-ui` · NFR-5 前端

## ADR-0006（前端角度）

| 面向 | 判定 |
|---|---|
| IAM | **適用** — `CapabilityRoute`、控件 `can()` 唯讀 gating |
| Encryption | **沿用** — HTTPS SPA；不存 secret in localStorage |
| Network | 只呼叫同源 `/api/cost*` |
| Audit | 不寫 audit；顯示 GET audit 只讀 |

## SEC-U-1 授權 UI

- 無 C1.view：**不渲染**成本 Sidebar（BR-U-1）
- 無 edit story：控件 readOnly；仍可能被 API 403（不 crash）

## SEC-U-2 XSS

- 列 label 來自 API 須 **React 預設 escape**；禁止 `dangerouslySetInnerHTML` on label

## SEC-U-3 客戶端校驗

- 輔助 UX；**不以**前端為安全邊界（403 為準）

## SEC-U-4 B1 DOM

- budget/banner test-id **0 命中**（AC-1.16）
