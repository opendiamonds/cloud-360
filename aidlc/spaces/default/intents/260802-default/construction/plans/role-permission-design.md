# Cloud-360 Role & Permission Design

> Branch: `luojingting/feat/role-permission-redesign`  
> Status: **APPROVED — implemented (core)**  
> 粒度：Pillar **A–H／J** × 角色 ×（檢視／編輯／審核）  
> Sources: `personas.md` · `stories.md` · SRS Pillar J  
> 實作對照：`role-permission-construction-plan.md` · `schema_rbac.sql` · `services/rbac.py`

### 1. 設計目標

1. 依 Persona 與 Stories，對功能標定 **檢視／編輯／審核**
2. 前後端同一套檢查（防 bypass）
3. 圖表 ACL（分享）與平台角色分離、再疊加
4. 角色命名統一（見 §2.1）
5. **A1／A2／A4 視為同一功能「架構圖生成」**（見 §3.1、§4）

### 2. 正式角色

| 縮寫 | Role handle | Persona |
|---|---|---|
| Arch | `Project_Architect` | Alex |
| Dev | `Developer` | Ian（平台開發者；非外部 End User） |
| Edit | `Project_Editor` | Hannah |
| PAdm | `Project_Admin` | Catherine |
| Fin | `FinOps_Analyst` | David |
| SRE | `SRE` | Ben |
| Ops | `Ops_Lead` | George |
| PEng | `Platform_Engineer` | Elena |
| Sec | `Security_Reviewer` | Fiona |
| Plat | `Platform_Admin` | Jack |
| Own | `Platform_Owner` | Karen |

#### 2.1 命名對齊

| Stories 別名 | 正式 handle |
|---|---|
| `Security_Admin` | → `Security_Reviewer` |
| `Engineering_Manager` | → `Project_Editor` |

### 3. 動作圖例

| 符號 | 中文 | 含義 |
|---|---|---|
| `-` | 無 | 選單隱藏 + API 403 |
| `V` | **檢視** | 可看資料／報告／被授權資源 |
| `VE` | **檢視 + 編輯** | 可建立修改、AI 產製、送審等（不含審核核定） |
| `VR` | **檢視 + 審核** | 可看＋通過／拒絕；**不可編輯** |
| `VER` | **檢視 + 編輯 + 審核** | 三者皆可 |

通用規則：

- 勾選 **編輯** 或 **審核** 時，實作視為可 **檢視**（`can_view` 自動為真）
- 三者旗標在 DB 獨立儲存；可出現 VR（有審核無編輯）
- Admin UI 與文件一律用中文：**檢視／編輯／審核**（對應 V／E／R）

#### 3.1 架構圖生成（A1／A2／A4）專用語意

A1、A2、A4 在產品上是**同一個功能**（架構圖生成／協作／聊天持久化），權限**以 A1 為準**，寫入時 **A1＝A2＝A4 同步**。

| 權限組合 | 行為 |
|---|---|
| **僅檢視（V）** | 只能開啟**別人分享給自己**的架構圖；**不可**編輯畫布、**不可**與 AI 對話、**不可**新建／儲存／分享／清空對話 |
| **編輯（含 VE／VER 的 E）** | 除「審核核定」外皆可：新建、儲存、分享、AI 產圖、畫布編輯、聊天持久化、重置 |
| **審核（含 VR／VER 的 R，且無 E）** | 可檢視被分享的圖 + 審核動作；**不可**編輯畫布、**不可** AI 對話 |

> 說明：僅檢視／僅審核時，**自己擁有的圖也不出現在列表**（避免「有擁有權卻不能編」的混淆）；必須由具備編輯權的使用者分享後才能開啟。

執行期：

```text
require_arch(action):
  # 讀 A1；A2／A4 與 A1 綁定
  return role_permissions[role][A1].can_{view|edit|review}

list_visible_diagrams:
  if can_edit:  owned ∪ shared_to_me
  elif can_view: shared_to_me only
  else:          []
```

---

### 4. Pillar A — 架構設計

Admin／文件顯示名：**架構設計**

| Story | 功能（中文） | 備註 | Arch | Dev | Edit | PAdm | Fin | SRE | Ops | PEng | Sec | Plat | Own |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A1／A2／A4** | **架構圖生成** | 三 story 同步；語意見 §3.1 | VE | VE | VE | V | V | V | V | V | V | V | V |
| **A3** | Well-Architected 評核 | 獨立能力 | VE | V | VE | V | - | V | V | V | **VER** | V | V |

底層仍保留三列 seed（與 stories 對齊），但 UI 合併為一欄「架構圖生成（A1／A2／A4）」：

| Story ID | 對應能力（實作綁定） |
|---|---|
| A1 | 自然語言轉架構與草圖／AI 產圖 API |
| A2 | draw.io 協同編輯／畫布寫入 |
| A4 | 聊天與上次開啟圖持久化 |

---

### 5. Pillar B — 跨雲選型

Admin／文件顯示名：**跨雲選型**

| Story | 功能 | Arch | Dev | Edit | PAdm | Fin | SRE | Ops | PEng | Sec | Plat | Own |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **B1** | AI 單一雲端評選決策 | V | V | V | VE | VE | V | V | V | V | V | V |
| **B2** | 技術生態與相容性掃描 | VE | V | V | V | V | V | VE | V | V | V | V |
| **B3** | 地緣合規與存取延遲優化 | V | V | V | VE | V | V | V | V | VE | V | V |

---

### 6. Pillar C — 成本與 FinOps

Admin／文件顯示名：**成本與 FinOps**

| Story | 功能 | Arch | Dev | Edit | PAdm | Fin | SRE | Ops | PEng | Sec | Plat | Own |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **C1** | TCO 與流量預算預測 | V | - | V | V | VE | V | V | - | - | V | V |
| **C2** | 資源優化與定價對比 | V | - | V | V | VE | VE | V | - | - | V | V |
| **C3** | Data Egress 隱性成本 | VE | - | V | V | VE | V | V | - | - | V | V |

> J2：`Developer` 對 C1–C3 全為 `-`。

---

### 7. Pillar D — 基礎建設即程式碼（IaC）

Admin／文件顯示名：**基礎建設即程式碼**

| Story | 功能 | Arch | Dev | Edit | PAdm | Fin | SRE | Ops | PEng | Sec | Plat | Own |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **D1** | Terraform／OpenTofu 產出 | VE | VE | V | V | - | V | V | VE | V | V | V |
| **D2** | IaC 安全靜態掃描 | V | V | V | V | - | V | V | VE | VE | V | V |
| **D3** | Secret Manager／敏感值 | V | VE | V | V | - | V | V | V | VE | V | V |

---

### 8. Pillar E — 維運優化

Admin／文件顯示名：**維運優化**

| Story | 功能 | Arch | Dev | Edit | PAdm | Fin | SRE | Ops | PEng | Sec | Plat | Own |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **E1** | Right-sizing | V | - | VE | V | V | V | VE | V | V | V | V |
| **E2** | 架構現代化引導 | VE | V | V | VE | V | V | V | V | V | V | V |
| **E3** | Runbooks 生成 | V | - | V | V | V | VE | VE | V | V | V | V |

---

### 9. Pillar F — AI 多雲維運

Admin／文件顯示名：**AI 多雲維運**

| Story | 功能 | Arch | Dev | Edit | PAdm | Fin | SRE | Ops | PEng | Sec | Plat | Own |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **F1** | 自然語言跨雲健康查詢 | V | - | V | V | - | VE | VE | V | V | V | V |
| **F2** | 變更計畫與回滾策略 | V | - | V | V | - | VE | V | VE | V | V | V |
| **F3** | 高風險操作審批閘門 | V | - | - | V | - | VE | V | - | VR | V | **VR** |

> F3：SRE **編輯送審**；Owner／Sec **審核**（不編）。

---

### 10. Pillar G — 安全與合規

Admin／文件顯示名：**安全與合規**

| Story | 功能 | Arch | Dev | Edit | PAdm | Fin | SRE | Ops | PEng | Sec | Plat | Own |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **G1** | CSPM 與持續合規 | V | V | V | V | - | V | V | V | **VER** | V | V |
| **G2** | IAM／最小權限 | V | VE | V | V | - | V | V | V | **VER** | V | V |
| **G3** | Policy-as-Code 防護網 | V | V | V | V | - | V | V | VE | **VER** | V | V |

---

### 11. Pillar H — MCP 與 Skill

Admin／文件顯示名：**MCP 與 Skill**

| Story | 功能 | Arch | Dev | Edit | PAdm | Fin | SRE | Ops | PEng | Sec | Plat | Own |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **H1** | 內部 API 工具註冊 | V | V | V | V | - | V | V | VE | V | **VER** | V |
| **H2** | Agent 存取邊界審核 | V | V | V | V | - | VE | V | V | V | **VER** | VR |
| **H3** | MCP／Skill 生命週期 | V | V | V | V | - | V | V | VE | V | **VER** | V |

---

### 12. Admin 兩個頁面（必做）

| 頁面 | 路由 | 用途 | 對應能力 |
|---|---|---|---|
| **① 使用者角色指派** | `/admin/users` | 指定「哪個使用者是哪個角色」 | J3a |
| **② 角色細項權限** | `/admin/role-permissions` | 指定「哪個角色對各功能有檢視／編輯／審核」 | J3b |

誰能進：`Project_Admin`、`Platform_Admin` = **VER**；`Platform_Owner` = **V**；其餘 `-`。

#### 12.1 頁面① — 使用者 ↔ 角色

- 列表：username、目前 role（含**待授權／Pending**）、啟用狀態、（下期）待處理授權申請  
- 動作：下拉改為 11 個正式 role → 儲存；啟停用；**下期**：核准／拒絕角色申請、**刪除使用者**  
- 防護：不可移除最後一位具 J3a.edit 的管理員；正式 role ∈ allowlist；Pending 不在生效 allowlist  
- Audit：`actor / target / old_role / new_role / time`（刪除／核准亦需記錄）

#### 12.1.1 註冊與授權申請（stories J5 — 目標語意；現況尚未實作）

| 項目 | 語意 |
|---|---|
| 註冊 | **不得**預設 `Developer` 或其他正式角色；建立帳號為 Pending |
| 註冊 UI | 必選「申請角色」；展示 11 角色介紹 + 可使用功能摘要 |
| 申請單 | applicant、requested_role、created_at、status∈{pending,approved,rejected} |
| 登入後 | Pending 僅「等待授權」+ 登出；業務 API 403 |
| 核准 | 寫入正式 `role`，關閉申請；之後走 §12.2 矩陣可見性 |
| 刪除 | Admin 可刪使用者（硬／軟刪與圖表歸屬 → Functional Design） |
| **授權申請佇列** | 路由 `/admin/authorization-requests`；J3a.view 可看列表；J3a.edit 可核准／拒絕；預設篩 pending |

> **As-built gap**：現行 `/api/auth/register` 直接指派 `Developer` 且立即生效，與 J5 衝突，實作時必須改掉。

#### 12.1.2 Admin 授權申請頁（Functional Design 2026-07-17）

| 項目 | 語意 |
|---|---|
| 路由 | `/admin/authorization-requests` |
| Sidebar | 「使用者設定」下方 **授權申請**（可選 pending 筆數 badge） |
| 列表 | username、requested_role、申請時間、狀態；篩選 pending／approved／rejected |
| 核准 | BR-04 角色邊界；寫入 role + approved |
| 拒絕 | 刪除帳號 + audit |

#### 12.2 頁面② — 角色 ↔ 細項權限

- Pillar 分頁標籤用**功能中文名**（非 Pillar A）：

  | 代碼 | 顯示名 |
  |---|---|
  | A | 架構設計 |
  | B | 跨雲選型 |
  | C | 成本與 FinOps |
  | D | 基礎建設即程式碼 |
  | E | 維運優化 |
  | F | AI 多雲維運 |
  | G | 安全與合規 |
  | H | MCP 與 Skill |
  | J | 身分與權限 |

> Pillar **J** 在細項矩陣只顯示兩欄：**使用者設定（J3a）**、**細項設定（J3b）**；**不含 J1 登入**（登入能力仍由 seed 維護）。

- 每一格勾選：**檢視／編輯／審核**（中文；對應 can_view／can_edit／can_review）  
- **架構設計**分頁：A1／A2／A4 **合併為一欄「架構圖生成」**；儲存時寫入三列相同旗標  
- A3 仍為獨立欄「Well-Architected 評核」  
- **Pillar J**：僅 **使用者設定（J3a）**、**細項設定（J3b）**；J1 不出現在 UI  
- 某功能三旗標皆未勾選 → 該角色 Sidebar **不顯示**對應選單（並無法進入路由）  
- 預設值 = §4–§11／§12.3 矩陣（seed）；儲存即時生效；「還原設計預設」需 J3b.review  

```text
users.role                         → 頁面①
role_permissions(role, story_id,
  can_view, can_edit, can_review)  → 頁面②
```

```text
require(user, story_id, action):
  if story_id in {A1, A2, A4}:
    story_id = A1
  return role_permissions[user.role][story_id].can_{view|edit|review}
```

#### 12.3 Pillar J — 身分與權限

Admin／文件顯示名：**身分與權限**

| Story | 功能（矩陣 UI 顯示名） | Arch | Dev | Edit | PAdm | Fin | SRE | Ops | PEng | Sec | Plat | Own |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **J1** | 登入／憑證（**不在細項 UI**；seed 維護） | VE* | VE* | VE* | VE* | VE* | VE* | VE* | VE* | VE* | VER | VE* |
| **J3a** | **使用者設定**（頁①） | - | - | - | **VER** | - | - | - | - | - | **VER** | V |
| **J3b** | **細項設定**（頁②） | - | - | - | **VER** | - | - | - | - | - | **VER** | V |

\*J1 `VE*` = 僅自己的登入相關。選單可見性依 `role_permissions` 動態計算。

#### 12.4 環境移轉 SQL

```bash
psql "$DATABASE_URL" -f schema_rbac.sql
```

| 區塊 | 說明 |
|---|---|
| A | `users`／`user_diagrams`／`diagram_shares` |
| B | `user_diagram_chats` + `last_opened_diagram_id` |
| C | `role_permissions` + 預設矩陣（含 A1／A2／A4 三列相同預設） |
| D | 預設帳號 `admin` / `admin123`（`Platform_Admin`） |

⚠ 重跑會 `DELETE` 後重播 `role_permissions`；已用 Admin UI 調過請先備份。

### 13. 資源 ACL（與平台 RBAC 疊加）

對「架構圖生成」：

| 平台權限 | 可見圖範圍 | 可寫（XML／AI／聊天） | 可分享 |
|---|---|---|---|
| 僅檢視 | 僅 `shared_to_me` | 否 | 否 |
| 僅審核（VR） | 僅 `shared_to_me` | 否 | 否 |
| 有編輯 | `owned ∪ shared_to_me` | 是（另受 Owner／sharee 規則） | 僅 Owner |

分享關係（`diagram_shares`）與角色矩陣正交：即使有編輯權，未擁有且未被分享的圖仍 403。

### 14. 與現況差異

| 項目 | 設計／實作 |
|---|---|
| Admin | `/admin/users` + `/admin/role-permissions` |
| 矩陣 | DB `role_permissions`；Admin 可改；seed = 本文件 |
| 架構圖 | A1／A2／A4 合併語意 + 僅檢視＝只看被分享圖 |
| UI 文案 | Pillar／VER 皆中文 |

### 15. 狀態

設計已批准並進入實作；核心 RBAC、Admin 兩頁、架構圖語意已落地。後續可補：WebSocket JWT、架構圖審核流程完整 UI。
