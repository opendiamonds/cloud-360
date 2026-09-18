# J5 Business Rules — Registration & Authorization Gate


### BR-01 註冊

1. 必填：username、password、**requested_role**（須 ∈ 11 正式角色）。
2. 建立 `User`：`authorization_status=pending`，`role=NULL`，`is_active=true`。
3. 建立 `RoleAuthorizationRequest`：`status=pending`。
4. **不得**指派預設 `Developer` 或任何正式角色。
5. 回應：JWT + `authorization_status=pending`（Q5=C）。

### BR-02 登入（Pending）

1. 憑證正確且 `is_active=true` 可簽發 JWT。
2. `GET /me`：`authorization_status=pending` 時 `permissions={}`（全空），`role=null`。
3. 所有需 `require_story_action`／`require_arch_action` 的業務 API → **403**（訊息：等待管理員授權）。
4. 前端：除 `/waiting-approval`、登出、`/me`、改申請角色外，強制導向等待頁。

### BR-03 Pending 改選申請角色（Q8=A）

1. 僅 `authorization_status=pending` 且申請 `status=pending` 可呼叫。
2. 更新同一筆申請的 `requested_role` + `updated_at`。
3. 不需管理員介入。

### BR-04 核准申請（Q2=C）

| 操作者 | 可核准的 requested_role |
|---|---|
| `Platform_Admin`（具 J3a.edit） | 全部 11 角色 |
| `Project_Admin`（具 J3a.edit） | 除 `Platform_Admin`、`Platform_Owner` 外 |

1. 核准：`users.role = requested_role`，`authorization_status=approved`，申請 `status=approved`，記錄 `decided_by`／`decided_at`。
2. 寫 audit。
3. 使用者重新整理後依 J2 矩陣顯示 Sidebar。

### BR-05 拒絕申請（Q6=C）

1. 僅具 J3a.edit 且符合 BR-04 角色邊界者可拒絕。
2. **硬刪除**使用者帳號（及關聯資料依 BR-07 cascade）。
3. 申請標 `rejected` 或隨刪除一併移除；audit 保留「拒絕並刪除」紀錄。

### BR-06 停用與刪除（Q3=C + Q4=C）

| 動作 | 條件 | 效果 |
|---|---|---|
| **停用** | J3a.edit | `is_active=false`；不可登入 |
| **刪除** | J3a.edit **且** `is_active=false` **且** 無擁有之架構圖 | 硬刪使用者 |
| **刪除阻擋** | 使用者仍擁有 `user_diagrams` | **403**：請先轉移擁有權或刪除圖表 |

UI：僅在 `is_active=false` 時顯示「刪除」按鈕。

### BR-07 關聯資料刪除（硬刪）

刪除使用者時 cascade（建議順序）：

1. `user_diagram_chats`（user_id）
2. `diagram_shares`（user_id）
3. `user_diagrams`（僅當 owner — 刪除前 BR-06 已擋有圖）
4. `role_authorization_requests`（user_id）
5. `users`

### BR-08 管理員檢視申請佇列（使用者追加需求）

1. 具 **J3a.view** 或 **J3a.edit** 者可進入 **「授權申請」** 管理畫面。
2. 預設列表：`status=pending`，欄位含 username、requested_role、申請時間、可選「上次更新」。
3. 支援篩選：`pending`／`approved`／`rejected`（歷史唯讀）。
4. 具 J3a.edit 者在列表列上可 **核准**／**拒絕**（依 BR-04／BR-05）。
5. Sidebar／Admin 導覽在「使用者設定」旁或子頁顯示 **授權申請**，pending 筆數 badge（選做）。

### BR-09 角色目錄（Q7=B）

1. `GET /api/auth/roles/catalog`：對每個 canonical role，掃描 seed／現行 `role_permissions`，列出至少一項 view/edit/review 為真的 story（A1/A2/A4 合併顯示）。
2. 註冊頁與 Pending 改選角色共用此 API。
3. 靜態 persona 一句介紹可併入 FE 常數或 BE 回傳 `summary` 欄（選做）。

### BR-10 與既有 RBAC 銜接

1. `is_canonical_role` **不**包含 pending 占位。
2. `user_can`：若 `authorization_status != approved` → 一律 false。
3. 最後一位 J3a.edit 管理員保護規則**沿用**（不可降級／刪除導致零管理員）。

### Testable Properties（PBT 對照）

| ID | 類別 | 性質 |
|---|---|---|
| P-J5-01 | Invariant | `authorization_status=pending` ⇒ `user_can(*)=false` |
| P-J5-02 | Idempotence | 重複核准同一 pending 申請第二次應 409 |
| P-J5-03 | Oracle | catalog features ⊆ stories with any flag in matrix |
| P-J5-04 | Round-trip | pending 改選 role → GET 申請反映新值 |
