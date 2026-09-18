# U-J / J5 — Functional Design Plan

> Unit: `U-J` (Identity & RBAC)  
> Stories: **J5**（主）＋ **J3** AC6–7（核准申請、刪除使用者）  
> Status: **COMPLETE**（2026-07-17；含管理員「授權申請」佇列 UI）


### Checklist

- [x] 釐清問題全部作答（見下方 Questions）
- [x] 產出 `construction/j/functional-design/domain-entities.md`
- [x] 產出 `construction/j/functional-design/business-rules.md`
- [x] 產出 `construction/j/functional-design/business-logic-model.md`
- [x] 產出 `construction/j/functional-design/frontend-components.md`
- [x] 更新 `role-permission-design.md`／`identity-rbac-summary.md` 對齊 FD
- [x] Stage completion + audit

### 決策摘要

| Q | 答案 |
|---|---|
| 1 | C — `authorization_status` 為準 |
| 2 | C — Plat 可核准全部；PAdm 不可核准 Plat/Owner |
| 3 | C — 硬刪；有圖則 403 |
| 4 | C — 須先停用才顯示刪除 |
| 5 | C — JWT + 空權限 + Waiting 頁 |
| 6 | C — 拒絕＝刪帳號 |
| 7 | B — catalog 動態來自矩陣 |
| 8 | A — Pending 可改選申請角色 |
| + | 管理員專頁 **`/admin/authorization-requests`** 檢視待處理申請 |

### 範圍摘要（暫定，待答案鎖定）

```text
Register → Pending user + RoleAuthorizationRequest(pending)
        → Login → WaitingForApproval page only
Admin (J3a.edit) → approve | reject | delete user
Approve → write formal role → J2 visibility applies
```

現況衝突：`POST /register` 直接 `role=Developer` —— FD 確認後 Construction 必須改掉。

---

## Questions

### Question 1
待授權帳號的「無正式角色」在資料模型怎麼表示？

A) `users.role` 存字串 `"Pending"`（不在 11 角色 allowlist；`user_can` 全否）

B) `users.role` 改為 **nullable**（`NULL` = 待授權）

C) `users.role` 仍暫時占位，另加 `authorization_status` 欄（pending／approved／rejected）為準

X) Other (please describe after [Answer]: tag below)

[Answer]:Ｃ

---

### Question 2
誰可以**核准／拒絕**角色授權申請？

A) 僅 `Platform_Admin`（Jack）

B) 具 **J3a.edit** 者（目前：`Project_Admin` + `Platform_Admin`）

C) `Platform_Admin` 可核准任何角色；`Project_Admin` 不可核准申請 `Platform_Admin`／`Platform_Owner`

X) Other (please describe after [Answer]: tag below)

[Answer]:Ｃ

---

### Question 3
誰可以**刪除使用者**？刪除語意？

A) J3a.edit；**硬刪**使用者列（圖表／分享／聊天 cascade 或禁止刪除仍有圖的帳號）

B) J3a.edit；**軟刪**（`is_active=false` + `deleted_at`；列表可篩「已刪除」；登入拒絕）——與「停用」合併或分開見下一題

C) J3a.edit；硬刪，但若使用者仍擁有架構圖 → **403 並要求先轉移／刪圖**

X) Other (please describe after [Answer]: tag below)

[Answer]:Ｃ

---

### Question 4
「停用」與「刪除」的關係？

A) 分開：停用＝暫時無法登入；刪除＝永久移除（或軟刪不可還原）

B) 刪除＝停用的別名（只做 `is_active=false`，不做真刪）

C) 刪除前必須先停用；已停用才顯示「刪除」按鈕

X) Other (please describe after [Answer]: tag below)

[Answer]:Ｃ

---

### Question 5
註冊成功後流程？

A) 立即簽發 JWT 並進入「等待授權」頁（現有 register 回 token 模式）

B) 不簽發 JWT；只顯示「請等待核准後再登入」；核准後才能 login

C) 簽發 JWT，但任何業務 API（含 `/me` permissions）對 Pending 一律空權限 + 前端強制 Waiting 頁

X) Other (please describe after [Answer]: tag below)

[Answer]:Ｃ

---

### Question 6
管理員**拒絕**申請時怎麼處理帳號？

A) 申請 status=rejected；帳號維持 Pending，可再次改選角色重送申請

B) 申請 rejected + 帳號自動停用（需管理員重新啟用才能再申請）

C) 申請 rejected + **刪除帳號**（等同註冊失敗清理）

X) Other (please describe after [Answer]: tag below)

[Answer]:Ｃ

---

### Question 7
註冊頁「角色介紹＋可使用功能」內容來源？

A) **靜態目錄**：從 personas 摘要 + 固定功能清單（FE 常數或 BE `/roles/catalog`）

B) **動態**：依預設 `role_permissions` 矩陣產生「有 view/edit/review 的 story 列表」

C) 靜態介紹 + 動態功能摘要（介紹手寫、功能從矩陣算）

X) Other (please describe after [Answer]: tag below)

[Answer]:Ｂ

---

### Question 8
Pending 期間使用者可否**更改申請角色**？

A) 可以：更新同一筆 pending 申請的 `requested_role`

B) 不可以：只能等管理員處理；拒絕後才能重申請

C) 可以，但一天限改 N 次（請在 Answer 寫 N）

X) Other (please describe after [Answer]: tag below)

[Answer]:Ａ
