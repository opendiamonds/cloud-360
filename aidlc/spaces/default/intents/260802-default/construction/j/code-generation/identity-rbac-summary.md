# Pillar J Identity & RBAC — Implementation Summary (U-J)

> J1–J4 core + **J5 code generated 2026-07-17**.  
> FD：`construction/j/functional-design/` · Plan：`construction/plans/j5-code-generation-plan.md`


### 結果

JWT 登入、11 角色矩陣、Admin 兩頁（使用者／細項）已有。**J5 已實作**：註冊無預設角色、動態角色目錄、等待授權頁、**授權申請專頁**、核准／拒絕（拒絕刪帳）、停用後刪除。

### J5 實作摘要

| 項目 | 實作 |
|---|---|
| 待授權 | `users.authorization_status=pending`，`role=NULL` |
| 註冊 | `POST /register` + `requested_role`；JWT + 空 permissions |
| 目錄 | `GET /roles/catalog`（公開，來自矩陣） |
| 等待頁 | `/waiting-approval`；可 PATCH 改申請角色 |
| 管理員佇列 | `/admin/authorization-requests` + Sidebar「授權申請」 |
| 核准權 | Plat 全部；PAdm 不可核准 Plat/Owner |
| 拒絕 | 刪除帳號 |
| 刪除 | 須先停用；有擁有圖 → 403 |

### 主要檔案

| 層 | 路徑 |
|---|---|
| BE | `models.py`、`database.py`（`_ensure_j5_schema`）、`rbac.py`、`user_router.py` |
| FE | `AuthContext`、`LoginPage`、`WaitingApprovalPage`、`AuthorizationRequestsPage`、`AdminPage`、`App`、`Sidebar`、`RouteGuard` |
| Test | `tests/test_j5_authz.py` |

### AC 對照

| Story | 狀態 |
|---|---|
| J1–J4 | ✅／⏳（見既有） |
| J5 註冊閘門 | ✅ |
| J5 授權申請頁 | ✅ |
| WS JWT | ⏳ |

### 手動驗收

1. 註冊選 SRE → 進等待授權頁，無 Sidebar 業務選單  
2. admin 開「授權申請」→ 核准 → 使用者重新整理後有選單  
3. Project_Admin 無法核准 Platform_Admin 申請  
4. 停用後才可刪除；有圖則刪除失敗  
