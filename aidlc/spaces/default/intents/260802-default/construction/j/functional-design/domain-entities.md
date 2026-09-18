# J5 Domain Entities — Registration & Authorization Gate

> Unit `U-J` · Stories J5 + J3 (approve / delete)  
> Decisions: `j5-functional-design-plan.md` (2026-07-17) + admin **授權申請佇列** UI


### 實體關係

```text
User 1 ──* RoleAuthorizationRequest
     │
     └── (optional) owned UserDiagrams → blocks hard delete
```

### User（擴充）

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | PK | 既有 |
| `username` | string | 既有；唯一 |
| `password_hash` | string | 既有 |
| `role` | string \| null | **僅 `authorization_status=approved` 時**為 11 正式角色之一；pending 期間為 `NULL` 或占位（不參與 `user_can`） |
| `is_active` | bool | 既有；`false` = 停用，不可登入 |
| `authorization_status` | enum | **`pending` \| `approved` \| `rejected`**（Q1=C）；執行期以本欄為準 |
| `last_opened_diagram_id` | FK? | 既有；approved 後才使用 |

**語意**

| authorization_status | role | 可登入？ | 業務權限 |
|---|---|---|---|
| `pending` | null | ✅（JWT） | 無；僅等待授權頁 |
| `approved` | canonical | ✅ | 依 `role_permissions` |
| `rejected` | — | ❌ | 帳號應已刪除（Q6=C） |

既有 seed `admin`：`authorization_status=approved`，`role=Platform_Admin`。

### RoleAuthorizationRequest（新表）

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | PK | |
| `user_id` | FK → users | 申請人 |
| `requested_role` | string | 11 正式角色之一 |
| `status` | enum | `pending` \| `approved` \| `rejected` |
| `created_at` | timestamp | |
| `updated_at` | timestamp | Pending 改選角色時更新（Q8=A） |
| `decided_by` | string? | 管理員 username |
| `decided_at` | timestamp? | |
| `note` | string? | 拒絕／備註（選填） |

**不變量**

- 每位使用者同時最多 **一筆** `status=pending` 的申請。
- `approve`：寫入 `users.role`、`authorization_status=approved`、關閉申請。
- `reject`（Q6=C）：**刪除使用者列**（及 cascade 策略見 business-rules）；申請標 `rejected` 後隨帳號刪除或僅留 audit。

### RoleCatalogEntry（虛擬／API DTO，不另建表）

由 `role_permissions` 預設矩陣動態產生（Q7=B）：

| 欄位 | 說明 |
|---|---|
| `role` | handle |
| `display_name` | 中文顯示名（personas 對照） |
| `features` | 有 view/edit/review 的 story 列表（合併 A1/A2/A4 為「架構圖生成」） |
