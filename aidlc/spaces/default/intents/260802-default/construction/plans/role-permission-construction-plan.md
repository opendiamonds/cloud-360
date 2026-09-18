# Role & Permission Redesign — Construction Plan

> Branch: `luojingting/feat/role-permission-redesign`  
> Design: `role-permission-design.md`（已批准；含架構圖語意／Sidebar／細項 UI 規則）  
> Status: **CORE DONE**（WebSocket JWT、手動 E2E 待補）

### 範圍

依設計文件落地：DB 矩陣、`require(story, action)`、Admin 兩頁、前後端同一套權限，以及後續產品語意調整。

### Checklist

| # | 項目 | 狀態 |
|---|---|---|
| 1 | `schema_rbac.sql` + `RolePermission` model + seed data | ✅ |
| 2 | `services/rbac.py` + `require_story_action`／`require_arch_action` | ✅ |
| 3 | `/me` 回傳 permissions；role allowlist；J3a/J3b API | ✅ |
| 4 | 架構圖 API（generate／CRUD／chat）套用架構圖權限 | ✅ |
| 5 | 啟動時空表 seed；確保 `admin` 帳號 | ✅ |
| 6 | FE：`/admin/users` + `/admin/role-permissions` | ✅ |
| 7 | FE：AuthContext `can()`／`canArch()`、CapabilityRoute | ✅ |
| 8 | **A1／A2／A4 =「架構圖生成」**：權限以 A1 為準、寫入三者同步 | ✅ |
| 9 | **僅檢視**：只看被分享的圖；不可編輯／AI；**編輯**＝除審核外皆可；**審核**＝可看＋審核、不可編輯 | ✅ |
| 10 | Admin 矩陣：Pillar 中文名；勾選「檢視／編輯／審核」；A1／A2／A4 合併一欄 | ✅ |
| 11 | **細項 UI 含 Pillar J**：僅「使用者設定」(J3a)、「細項設定」(J3b)；不含 J1 | ✅ |
| 12 | **三旗標皆未勾選 → Sidebar 不顯示該功能**；首頁導向第一個有權限頁 | ✅ |
| 13 | API base／WS／CORS 環境變數（前後端分服務） | ✅ |
| 14 | WebSocket JWT + diagram ACL 強化 | ⏳ 後續 |
| 15 | 手動 E2E（admin 僅檢視／alex 編輯／Developer 無 Admin） | ⏳ |

### 關鍵行為摘要（對齊 design §3.1、§12.2）

```text
架構圖生成 (A1=A2=A4):
  V only  → Sidebar 顯示；列表僅 shared_to_me；畫布／AI 唯讀
  Edit    → 新建／儲存／分享／AI／聊天皆可（審核另計）
  Review  → 可看分享圖 + 審核；不可編輯／AI
  全不勾  → Sidebar 隱藏「架構圖生成」；直連 /workspace → 403

Admin 細項矩陣:
  顯示 Pillar A–H＋J（中文名）
  Pillar J 僅兩欄：使用者設定(J3a)、細項設定(J3b)；不含 J1
  儲存後 refreshMe → Sidebar 即時更新
```
### 主要產物

| 層 | 路徑 |
|---|---|
| Design | `aidlc-docs/construction/plans/role-permission-design.md` |
| Schema | `schema_rbac.sql`、`schema-rbac-notes.md` |
| Backend | `backend/services/rbac.py`、`rbac_seed_data.py`、`user_router.py`、`collab_router.py`、`agent_router.py` |
| Frontend | `config/api.ts`、`AuthContext`、`Sidebar`、`AdminPage`、`RolePermissionsPage`、`WorkspacePage` |
| Env | `frontend/.env.example`（`VITE_API_BASE_URL`）、`backend/.env.example`（`CORS_ORIGINS`） |

### 驗證指令

```bash
# 若 DB 尚無矩陣
psql "$DATABASE_URL" -f schema_rbac.sql
# 或重啟後端（空表會自動 seed）

curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
# 用 token 打 GET /api/auth/me 、 /api/auth/role-permissions

# 手動：在角色細項把某角色「架構圖生成」三旗標全清 → 該角色登入後 Sidebar 無「架構圖生成」
# 手動：確認細項「身分與權限」僅有「使用者設定」「細項設定」兩欄
```
### Extension compliance

| Extension | 狀態 | 理由 |
|---|---|---|
| security/baseline | compliant | 權限以 DB + API 強制；role allowlist；audit 寫入 |
| testing/property-based | N/A | 本階段未新增 PBT 目標模組 |
| bilingual-docs | compliant | plan／design／notes 皆雙語 |
