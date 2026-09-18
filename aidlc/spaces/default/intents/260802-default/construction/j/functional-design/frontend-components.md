# J5 Frontend Components


### 路由

| 路徑 | 元件 | 誰可進 |
|---|---|---|
| `/login` | `LoginPage`（擴充註冊） | 公開 |
| `/waiting-approval` | `WaitingApprovalPage` | JWT + `authorization_status=pending` |
| `/admin/users` | `AdminPage`（擴充） | J3a.view+ |
| `/admin/authorization-requests` | **`AuthorizationRequestsPage`（新）** | J3a.view+；核准／拒絕需 J3a.edit |

`App.tsx`：`HomeRedirect` 若 pending → `/waiting-approval`；approved 邏輯不變。

### LoginPage（註冊模式擴充）

**狀態**

- `requestedRole: string | null`
- `roleCatalog: RoleCatalogEntry[]`（來自 `GET /roles/catalog`）

**UI**

1. 帳號／密碼（既有）
2. **角色選擇器**：卡片或下拉，每項顯示 handle、一句介紹、**動態功能列表**（來自 catalog）
3. 未選角色不可 submit
4. 成功 → 存 token → `navigate('/waiting-approval')`

**API**：`POST /api/auth/register` body `{ username, password, requested_role }`

### WaitingApprovalPage（新）

**顯示**

- 標題：「等待管理員授權」
- 目前申請角色、申請時間
- 說明：核准後將開通對應功能

**動作**

- **更改申請角色**（Q8=A）：再次載入 catalog → 選擇 → `PATCH /me/authorization-request`
- **登出**

**守衛**：`authorization_status !== pending` 時導向 `/` 或工作區。

### AuthorizationRequestsPage（新 — 管理員看申請）

> 滿足「admin 要有地方可以看到使用者的申請」。

**位置**：Sidebar「身分與權限」區塊，在「使用者設定」下方新增 **「授權申請」**；pending 筆數 badge（選做）。

**列表欄位**

| 欄 | 說明 |
|---|---|
| username | 申請人 |
| requested_role | 申請角色（中文標籤） |
| features_preview | catalog 摘要（可折疊） |
| created_at / updated_at | 申請／最後改選時間 |
| status | pending 列才顯示操作鈕 |

**操作**（`can('J3a','edit')`）

- **核准**：確認對話框 → `POST .../approve`；若 Project_Admin 對 Plat/Owner 申請 → 按鈕 disabled + tooltip
- **拒絕**：確認「將刪除帳號」→ `POST .../reject`

**篩選**：Tab 或下拉 — 待處理／已核准／已拒絕（歷史唯讀）。

**空狀態**：「目前沒有待處理的授權申請」。

### AdminPage（擴充）

1. 使用者表加欄：`authorization_status`、pending 時顯示 `requested_role`（來自 list API 嵌套）。
2. 角色下拉：僅 **approved** 使用者可改 role。
3. **停用** → `is_active=false`。
4. **刪除**：僅 `!is_active` 且無 owned diagrams（API 403 時 toast 提示先處理圖表）。
5. 連結：「查看授權申請」→ `/admin/authorization-requests`。

### AuthContext（擴充）

```typescript
authorization_status: 'pending' | 'approved' | 'rejected' | null;
isPending: boolean;  // status === 'pending'
```

- `refreshMe` 後若 `isPending`，全域路由守衛導向 waiting 頁。
- `can()` / `canArch()`：pending 時一律 false。

### Sidebar（擴充）

在 J3a 區塊：

```text
使用者設定      → /admin/users
授權申請 (N)    → /admin/authorization-requests   ← 新增
細項設定        → /admin/role-permissions
```

### 表單驗證

| 欄位 | 規則 |
|---|---|
| username | 3–20、英數底線（與 BE 一致） |
| password | 6–30 |
| requested_role | 必填 ∈ catalog |
