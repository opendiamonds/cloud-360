# U-J / J5 — Code Generation Plan

> Status: **COMPLETE** (user chose Continue to Next Stage after FD)  
> FD: `construction/j/functional-design/`  
> Stories: J5 + J3 AC6–7

## 中文版

### Context

Brownfield：修改既有 `backend/`、`frontend/`，不另起服務。

### Steps

- [x] Step 1 — Models：`User.authorization_status`、`role` nullable；`RoleAuthorizationRequest` 表；`database._ensure_j5_schema`
- [x] Step 2 — RBAC：`authorization_status != approved` → `user_can` 全否
- [x] Step 3 — API：register／catalog／me／patch request／list requests／approve／reject／deactivate／delete
- [x] Step 4 — FE AuthContext + RouteGuard pending 導向
- [x] Step 5 — LoginPage 角色目錄；WaitingApprovalPage；AuthorizationRequestsPage；AdminPage 停用／刪除；Sidebar
- [x] Step 6 — Unit tests（register pending、approve gate、user_can）
- [x] Step 7 — Summary + audit + aidlc-state

### English Version

Brownfield code gen for J5 registration gate and admin authorization queue; steps above.
