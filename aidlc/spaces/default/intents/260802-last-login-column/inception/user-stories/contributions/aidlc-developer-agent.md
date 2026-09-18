**Collaborator:** aidlc-developer-agent

## Contribution

開發者視角（可實作性、故事尺寸、技術依賴）的獨立盲審。所有主張以本輪對 repo 的
直接讀取與**實際執行**為據，非轉引 codekb 或 lead 草稿；與上游敘述不一致處逐項標注。
行號基準為 branch `ut` 的工作樹現況。

本輪實測（非閱讀推斷）的項目：
- 以 `npx eslint` 對兩支臨時探針檔實跑 lint，確認 `react-hooks/purity` 對逾期判定寫法的實際判定（探針檔已刪除）。
- 以 `grep` 全域列舉 `get_current_user` / `require_story_action` 的相依落點，確認認證入口的收斂程度。
- 逐字讀 `AdminPage.tsx` 的三個 handler，核對 PUT 回應是否真的被用於更新列。
- 讀 `schema_rbac.sql`、`DEPLOY.md`、`deploy/docker-compose.test.yml`、`rbac_seed_data.py`，
  確認權限預設值在**已 seed 的既有資料庫**上的實際套用路徑。

---

### 一、先更正一項會影響兩條 AC 的上游事實

`practices-discovery/evidence.md`（L100）主張：

> 前端 `handleRoleChange`（`AdminPage.tsx:89`）**正是用 PUT 的回應更新列** ——
> 結果是使用者改完角色後該列的最後活動時間會變空白

**此前提與實碼不符。** `AdminPage.tsx:89` 的實際內容是：

```
setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u)));
```

它以**既有列** `...u` 為基底、只覆寫本地已知的 `newRole`；`data`（PUT 回應）
只被用在第 90 行的 toast 文字（`data.username`）。三個 handler 的實際行為是：

| handler | 對回應的使用 | 列如何更新 |
| --- | --- | --- |
| `handleRoleChange`（L77-95） | 僅 `data.username` 供 toast | 本地 spread 合併，**不吃回應** |
| `handleToggleActive`（L97-117） | 僅 `data.is_active`／`data.username` 供 toast | `fetchUsers()` 全表重抓 `GET /list` |
| `handleDelete`（L119-133） | 僅 `data.deleted_username` | `fetchUsers()` 全表重抓 |

推論結果與 evidence.md 相反：`update_user_active`（L603-609）與 `update_user_role`
（L705-711）兩個 `UserSchema` 構造點漏欄位，**今天不會、加了新欄位後也不會**產生
「操作後該列變空白」的畫面。既有 `requested_role` 漏傳同理不可見（該欄只在
`authorization_status === 'pending'` 時渲染，而改角色對 pending 帳號直接 400 擋掉）。

這不推翻 FR-2.5 —— 三個構造點確實存在、其中兩個確實漏欄位、API 契約確實在說謊。
它推翻的是**把這個缺陷寫成使用者可見 AC** 的做法。詳見下方對 AC-1.5／AC-3.3 的改寫建議。

---

### 二、依賴圖：區分 build-order 與 acceptance-order，並補一條缺漏的交付約束

lead 的圖（`stories.md` L20-29）在**驗收順序**上成立，在**開發順序**上不成立，
且與 US-4 自己的註記（L194「無技術依賴，可與 US-1 平行開發」）互相矛盾。

實作事實逐條：

| lead 的邊 | 實作視角判定 | 依據 |
| --- | --- | --- |
| US-4 → US-1 | **不是 build 依賴** | US-1 全部落點（`models.py`、`database.py`、`auth.py`、`user_router.py`、`AdminPage.tsx`）與 `role_permissions` 的 `Security_Reviewer/J3a` 值完全無關；`Platform_Admin`（P-2）本來就有 J3a:view，US-1 可獨立開發、合併、部署並由 P-2 驗收 |
| US-1 → US-2 | **成立** | US-2 疊在同一個 `<td>` 上，需要 `DbUser` 已有該欄位 |
| US-2 → US-5 | **成立** | US-5 重寫的正是 US-1／US-2 落筆的 `<table>` 區塊 |
| US-3 → US-1 | **成立且為零實作**（見第七節） | — |

建議把總覽圖改成兩層敘述：

```
Build order（可平行）：
  US-4 ──────────────┐（獨立分支：權限值 + 套用路徑 + 雙向測試）
  US-1 → US-2 → US-5 ┘（單一序列：同一個檔案的同一段 JSX）

Acceptance order（誰能簽收）：
  US-1／US-2／US-5 由 Platform_Admin(P-2) 即可驗收；
  以 Security_Reviewer(P-1) 身分驗收則需 US-4 先落地。
```

<!-- Text fallback：US-4 與 US-1→US-2→US-5 這條序列可平行開發，兩者無程式相依。
     US-1、US-2、US-5 三者相依是因為它們改的是 AdminPage.tsx 內同一段表格 JSX。
     US-4 只在「要用 Security_Reviewer 這個身分做驗收」時才是前提。 -->

**新增一條 lead 未列的交付約束**：US-1、US-2、US-5 三者的變更集中在
`AdminPage.tsx`（269 行）的**同一段 JSX**（L166-264）。三者若拆成三條平行分支，
合併衝突是必然而非偶然。這在 `org.md` 的 trunk-based／短生命週期分支模型下，
應明確要求三者**序列進 trunk**（或合為同一條分支），列為 delivery-planning 的輸入。

---

### 三、US-1 的真實尺寸：INVEST 的 Estimable 註記低估了落點數

lead 寫「範圍明確（一個欄位、一處顯示、一個節流機制）」（L88）。實測落點如下：

| # | 落點 | 內容 | 是否 blocking |
| --- | --- | --- | --- |
| 1 | `backend/models.py` `User`（L22-51） | 新增欄位；`to_dict()` 同步 | — |
| 2 | `backend/database.py` | 新增 `ALTER TABLE users ADD COLUMN IF NOT EXISTS …` 並掛進 `init_db()`（L38-44 的 `_ensure_*_schema` 家族） | **是**（見第四節） |
| 3 | `schema_rbac.sql` `users` DDL（L29-36）＋檔頭涵蓋清單 | 可攜來源同步 | **是**（`project.md ## Mandated`） |
| 4 | `DEPLOY.md` 的「會建立的表／欄位」表（L178 起） | 部署資產同步 | **是**（同上） |
| 5 | `backend/services/auth.py::get_current_user`（L39-65） | 寫入點 | — |
| 6 | `backend/services/user_router.py` | `UserSchema`（L111-120）**＋三個構造點**（L451、L603、L705） | — |
| 7 | `backend/tests/` | 首個 `TestClient` 測試（見第八節）＋節流測試 | — |
| 8 | `frontend/src/pages/AdminPage.tsx` | `DbUser` interface（L6-13）＋`<th>`（L173 前）＋`<td>`（L202 後） | — |
| 9 | `frontend/tests/e2e/regression.spec.ts` | 表頭與值的斷言（AC-5.5 掛在 US-5，但實作上會與 US-1 同時發生） | — |

即：**6 個原始碼檔 + 2 個 blocking 部署資產**，其中「序列化」是 **3 處**不是 1 處，
「schema」是 **3 處**（ORM／runtime patch／可攜 SQL）不是 1 處。建議 Estimable 欄改為：
「範圍明確但落點分散：6 個原始碼檔、2 個 blocking 部署資產、3 個序列化構造點、
3 處 schema 來源；不確定性低（無未知技術），工作量中等」。

**是否切分？建議不切分**，並直接在本階段給出理由而非留給 delivery-planning：

- 唯一自然的切法是「US-1a 後端記錄／US-1b 前端顯示」。US-1a 對任何 persona 都不可見 ——
  這正是本 stage Q2=A 明確拒絕的「無 persona 偽故事」形狀，切分等於推翻已定案的答案。
- 上表 9 個落點對單一開發者是一條短生命週期分支的量，落在 `org.md`
  「typically resolved within 1-2 days」的範圍內，不需要用切故事來控制分支壽命。
- 後端先行、前端後跟是**部署序**問題（新增欄位是加性變更，後端先上不破壞前端），
  用同一分支內的 commit 順序即可表達，不需要拆成兩則故事。

---

### 四、遺漏的實作面向：兩則故事都缺「變更在既有環境實際生效」的完成條件

這是本輪最重要的發現。US-1 與 US-4 各自的 AC 全部滿足時，**功能在 staging 上仍然是壞的**。

**（1）US-1 —— 只改 `models.py` 會讓 staging 每一個已認證請求 500，而 CI 全綠**

- `init_db()`（`database.py` L38-44）只呼叫 `Base.metadata.create_all`，
  註解逐字寫著「create_all 不會 ALTER 舊表」；既有欄位是靠
  `_ensure_a4_schema()`／`_ensure_j5_schema()`／`_ensure_a3_schema()` 逐句
  `ALTER TABLE … ADD COLUMN IF NOT EXISTS` 補上的。
- staging 的 `users` 表已存在 → 新欄位不會自動出現 → SQLAlchemy 對 `User`
  的每一次查詢都會 SELECT 一個不存在的欄位 → 而 `get_current_user` 正是
  **每一個已認證請求**的必經路徑（實測：`review_router` 9 處、`lens_router` 5 處、
  `user_router` 11 處、`agent_router` 2 處全部經由 `require_story_action`／
  `require_arch_action`／`get_current_user` 收斂到同一個函式）。
- CI 不會發現：`backend/tests/helpers.py`（L25-34）走 in-memory SQLite ＋
  `Base.metadata.create_all`，新欄位**必定存在**；六道 CI 閘門沒有一道會跑到真實 Postgres 的既有表。

  → 建議新增 **AC-1.7（既有環境的結構落地）**：
  *Given* 一個已存在 `users` 表且無新欄位的資料庫，
  *When* 服務啟動完成一次，
  *Then* 該欄位存在且既有列的值為空（無紀錄態），
  *And* 既有帳號的登入與清單查詢不因此失敗。
  （承 requirements C-2；具體手段沿用 `database.py` 既有的 `_ensure_*_schema` 形狀。）

**（2）US-4 —— 「兩處預設值來源同步」在已 seed 的資料庫上完全不生效**

AC-4.3 只要求兩處**預設值來源**一致。實測兩處現值皆為
`('Security_Reviewer', 'J3a', False, False, False)`
（`backend/services/rbac_seed_data.py` L299；`schema_rbac.sql` L475）。把兩處都翻成
`True` 之後，在 staging 的實際生效路徑是：

| 路徑 | 是否生效 | 依據 |
| --- | --- | --- |
| 後端啟動時 seed | **否** | `ensure_role_permissions_seeded(db, force=False)`（`rbac.py` L58-65）在 `count > 0` 時直接 `return 0`；staging 的矩陣已有約 308 列 |
| 重跑 `schema_rbac.sql` | **生效但被禁止** | 該檔 L178 是 `DELETE FROM role_permissions;` 後全量重播 —— 會抹掉 Admin UI 的既有調整；requirements C-3 已明確排除此手段 |
| `POST /role-permissions/reset-defaults` | **同上，等價破壞** | `user_router.py` L824 走 `force=True` → 同樣先 `DELETE` 全表 |
| Admin UI（`/admin/role-permissions`，J3b） | 生效 | 但這是**人工操作**，不是可版控、可重放、可測試的交付物 |
| 針對性 SQL `UPDATE` | 生效 | 但 `DEPLOY.md` 目前**沒有**任何針對性更新 `role_permissions` 的段落 |

也就是說：US-4 的 AC 全綠、PR 合併、部署成功之後，`Security_Reviewer` 在 staging
**依然進不去頁面**，而沒有任何自動化會指出這件事。

  → 建議新增 **AC-4.5（既有環境的權限落地）**：
  *Given* 一個 `role_permissions` 已有既有列（含人工調整）的資料庫，
  *When* 本次變更的部署程序執行完成，
  *Then* `Security_Reviewer` 的 `J3a` 檢視旗標為啟用，
  *And* 其餘角色與其餘 story 的既有值**未被覆寫**（排除整表重播作為手段，承 C-3），
  *And* 該套用程序已寫入 `DEPLOY.md`（`project.md ## Mandated` 對 seed 語意變更為 blocking）。

（回滾面附帶說明：新增欄位是加性變更，`deploy.yml` 的 rollback job 還原舊 image
後舊程式不 SELECT 該欄，資料庫不需回滾 —— 這點對 US-1 有利，可寫進交付說明。）

---

### 五、AC-1.3 的節流：可實作，但 AC 的**措辭**不可驗

**可實作性：是，且不需要任何新元件。** 逾期常被擔心的三件事在此皆不成立：

- 不需要背景 worker：`get_current_user`（`auth.py` L57）本來就已經把整列 `User`
  查出來，`last_activity_at` 的上一次寫入時刻**在手邊就有**，判斷
  `now - 該值 >= 5 分鐘` 是零額外查詢。
- 不需要快取層：滑動視窗的基準值本身就持久化在該欄位裡。
- 不需要處理多 process：`backend/Dockerfile` L37 是
  `uvicorn main:app --host 0.0.0.0 --port 8000`（未帶 `--workers`），但即使日後加了
  worker，以欄位值為基準的判定天然跨 process 正確，且重啟後不失憶。

因此我**不主張**把 OQ-1 從 application-design 收回 —— 只是提供一個「零新增元件的
可行手段確實存在」的存在性證明，讓 application-design 有下限可比較，不預選手段。

**AC 措辭問題（這一項要改）**：AC-1.3 的 *Then* 是「**資料庫寫入次數為 1**」。
本 repo 沒有任何可觀測「資料庫寫入次數」的機制 —— 無 coverage 工具、無 metrics、
無 query log、無 APM（`team.md` 的 Deployment／Testing Posture 段已如實記載）。
這條 AC 因此沒有可執行的 pass/fail 判準，違反 `phases/inception.md` 的
「Requirements must be testable and verifiable」。

  → 建議改寫為以**可觀測狀態**表述（語意等價、實作手段中立）：
  **AC-1.3 寫入節流**
  - *Given* 一個帳號剛完成一次活動時間寫入，其值為 T
  - *When* 該帳號在 T 之後 5 分鐘內連續發出多個需認證的請求
  - *Then* 透過使用者清單端點讀到的該帳號最後活動時間**仍為 T**（不變）
  - *And* 在 T + 5 分鐘（含）之後的下一個請求，該值更新為新的時刻

  這個形狀可以直接用第八節的 `TestClient` 測試斷言（凍結時間或注入時鐘由
  application-design 決定），不需要任何觀測基礎設施。

**附帶語意缺口（記載，不主張改 AC）**：AC-1.1 寫「任何以有效憑證發出的請求」。
`collab_router.py` L221-232 的 WebSocket 端點 `/ws/{workspace_id}`
**完全沒有認證**（不經 `get_current_user`），因此純 WebSocket 共編活動不會被記錄。
AC 措辭本身沒說錯（WS 連線不帶憑證），但「最後活動」的產品語意與此有落差，
建議在 US-1 的 assumption 中如實記一筆，避免下游把它當成缺陷。

---

### 六、AC-1.5／AC-3.3：改寫為 API 契約層，否則兩條 AC 無法失敗

承第一節的事實更正。以現行前端行為，這兩條 AC 在
「`UserSchema` 加了欄位但兩個 PUT 構造點沒補」的情況下**一樣會通過**：

- 改角色 → 列用 `{...u, role}` 本地合併，舊值原地保留，不會空白。
- 啟停用 → `fetchUsers()` 重抓 `GET /list`（唯一補齊的構造點），拿到正確值。

一條永遠不會紅的 AC 對 FR-2.5 是零保護。而 FR-2.5 的原文本來就是 API 層的：
「**所有回傳使用者物件的端點都必須包含此欄位**」。

  → 建議把 AC-1.5 改寫為（AC-3.3 直接刪除，或改為引用 AC-1.5 的 persona 註記，
  不再獨立成一條可驗收項）：

  **AC-1.5 欄位在所有回傳使用者物件的端點一致存在**（防禦性，源自既有缺陷的教訓）
  - *Given* 使用者清單端點與角色調整、啟停用兩個端點都回傳使用者物件
  - *When* CI 執行後端測試
  - *Then* 三個端點的回應皆包含該欄位
  - *And* 對同一帳號，三個端點回傳的值一致（不得其一為空）

  這條可由 `TestClient` 直接斷言，且**會**在漏補構造點時變紅 —— 這才是 FR-2.5 要的保護。
  （實作建議：`user_router.py` 已有 `_serialize_auth_request`（L250-261）的 helper 先例，
  把 `UserSchema` 三處構造收斂成單一 `_serialize_user(u, requested=None)` 可從結構上
  消除這類漏欄位；此為 construction 的判斷，不寫進 AC。）

  同時建議 AC-1.6 的措辭由「使用者清單端點」放寬為「本次變更觸及的端點」，
  否則 AC-1.6 與改寫後的 AC-1.5 會出現覆蓋面不一致。

---

### 七、US-3「不含獨立實作」的判定：**正確**，實碼核實

逐項核對 US-3 的三條 AC 對應的實作落點：

- AC-3.1（同列視野內取得資訊）：`AdminPage.tsx` 的 `<tr>`（L179-260）本來就把
  使用者、授權狀態、角色、操作、啟用放在同一列；US-1 加的 `<td>` 落在同一個 `<tr>` 內。**零落點**。
- AC-3.2（既有操作不受影響）：三個 handler（L77-133）不因加欄而改動。**零落點**。
- AC-3.3（操作後資訊完整）：與 AC-1.5 同源，已建議上移到 API 契約層。**零落點**。

判定成立。lead 在 L183 的處理（保留為獨立故事、把是否併入 US-1 留給
delivery-planning）我同意，只補一點：若 delivery-planning 決定併入 US-1，
AC-3.1 應保留為 US-1 的一條 AC（它是唯一驗證「欄位位置在同一列可視範圍內」的條款），
不要隨故事一起消失。

---

### 八、測試面的兩個前置成本，故事群目前看不見

**（1）AC-1.6／AC-4.2 需要先建立 repo 內第一個 HTTP 測試骨架**

實測 `grep -rn "TestClient" backend/` → **零結果**。`team-practices.md` 已論證
前置條件齊備（`fastapi[standard]`、`httpx` 已在 `requirements.txt`；
`get_db`／`get_current_user` 可用 `app.dependency_overrides` 覆寫），
但「前置條件齊備」不等於「零工作量」：仍需寫出第一份
`app.dependency_overrides` + in-memory SQLite session 的 fixture 形狀
（`tests/helpers.py` 的 `make_session()` 可直接接上）。這筆一次性成本會落在
US-1 或 US-4 中**先進 trunk 的那一則**，建議在該則的交付說明中明記，
避免估算時被當成既有能力。

**（2）AC-4.1 目前沒有 e2e 可驗路徑：測試環境沒有 `Security_Reviewer` 帳號**

`deploy/docker-compose.test.yml` 把 `schema_rbac.sql` 掛成
`docker-entrypoint-initdb.d`，而該檔只 seed 一個帳號 `admin`（Platform_Admin，L497）；
因為 `users` 表非空，`init_db()` 的 11 位 persona（含 `fiona` / `Security_Reviewer`）
**不會**被建立。`regression.spec.ts` 的註解也逐字寫著
「one user, admin / admin123, role Platform_Admin」。

因此 AC-4.1 的 *Given*（`Security_Reviewer` 角色的使用者已登入）在現行 e2e stack
無法成立，除非（a）在測試資料中加一個該角色的帳號，或（b）在測試內走
註冊 → admin 核准的多步流程。這是 US-4 的隱含前置工作，建議在 AC-4.2 之外
補一句交付說明（不必升格為 AC，因為 AC-4.2 的後端雙向測試已能證明授權邏輯本身）。

---

### 九、C-6 之外的前端 lint 陷阱：US-2 的逾期判定會 CI 紅燈（已實跑驗證）

requirements C-6 只涵蓋「資料抓取形狀」（`react-hooks/set-state-in-effect`）。
US-1 不新增資料源、沿用 `GET /api/auth/list`，故與 C-6 **無衝突**。

但 **AC-2.1 的逾期判定會踩到另一條 error 級規則**。實測（`npx eslint`，
`eslint-plugin-react-hooks@7.1.1`，`flat.recommended` 內 `react-hooks/purity=error`）：

| 寫法 | 實測結果 |
| --- | --- |
| render 內 `const cutoff = Date.now() - 90*86400000` | **error**：`Cannot call impure function during render` |
| `useMemo(() => Date.now() - 90*86400000, [])` | **error**（同上，`useMemo` 內一樣被擋） |
| `useState(() => Date.now() - 90*86400000)` 惰性初始 | 通過 |
| render 內 `new Date()` | 目前通過（規則只列 `Date.now`；可通過但不可依賴） |

也就是說「在 `users.map()` 裡即時算 90 天差」這個最直覺的寫法會讓
`npm run lint` 直接失敗（CI 第二道關卡 `frontend` job 只擋 error，這正是 error）。
可行落點是把「當下時刻」在**資料抵達時**取得（`fetchUserList().then(...)` 內或
`useState` 惰性初始），再往下傳給渲染。

  → 建議在 US-2 的故事註記中補一行既有約束（不必升格為 AC，因為它是實作路徑
  而非驗收條件），並把它交給 application-design 作為 AC-2.1 的實作限制；
  同時建議把 requirements C-6 的描述在下游擴充為
  「前端**渲染與資料抓取**形狀受 lint 規則約束」，而不只是抓取形狀。

---

### 十、其餘經實測的小幅事實校正

- **AC-4.1 的入口文字**：實碼中側邊導覽的連結文字是 **「使用者角色」**
  （`Sidebar.tsx` L100），頁面 `<h1>` 是「使用者角色指派」（`AdminPage.tsx` L150）；
  repo 內不存在「使用者管理」這個字串。AC-4.1 若被直接轉成 Playwright 的
  `getByRole('link', { name: '使用者管理' })` 會失敗（現有 e2e L53 用的正是「使用者角色」）。
  建議 AC 改寫為「導覽的『系統管理』區出現使用者管理相關入口（現行文字為『使用者角色』）」。
- **AC-4.4 的範圍事實：正確且可再精確一級**。J3a:view 同時開通的是
  `/admin/users` 與 `/admin/authorization-requests` 兩條路由（`App.tsx` L74、L87）
  **以及側邊導覽的兩個連結**（`Sidebar.tsx` L90、L103），亦即使用者會看到兩個新入口而非一個。
- **一項經實測**排除**的潛在回歸（提供給 lead 作為風險已清項）**：
  `App.tsx` 的 `DefaultRedirect`（L17-26）依序判定
  `canArch('view')` → `can('A3','view')` → `can('J3a','view')`。
  `Security_Reviewer` 的 `A1` 預設為 `(true, false, false)`
  （`rbac_seed_data.py` L13），第一條就命中 → 登入落地頁仍是 `/workspace`。
  **US-4 不會改變該角色的登入落地行為**，此風險不存在，不需要為它寫 AC。
- **AC-1.4 的欄位位置**在實碼中可無歧義落實，但有一項既有命名怪異值得下游知道：
  現行表頭順序是「使用者｜授權狀態｜角色｜操作｜啟用」，其中**「操作」欄裝的是角色下拉選單**、
  「啟用」欄才裝啟停用與刪除按鈕。把新欄插在「角色」與「操作」之間，等於插在
  「角色顯示」與「角色編輯器」中間。實作上無礙，但是否為預期的視覺分組屬設計判斷，
  提請 lead 轉交 design 視角確認。
- **AC-5.3 的 44x44**：現行操作按鈕是 `px-2 py-1 text-[10px]`（`AdminPage.tsx` L243、L251），
  實際高度遠小於 44px。AC 的 *Given* 限定「小螢幕的卡片佈局下」，故僅需響應式尺寸而非全面放大 —— 
  此讀法若與 design 的意圖不同，需在本階段釐清，否則會變成桌面版的既有樣式變更（範圍擴大）。

## Positions

- AGREE: Q2=A 的價值導向拆分在實作視角同樣正確 —— FR-1 的落點（`models.py`／`database.py`／`auth.py`／序列化）沒有任何一項對使用者可見，一對一拆法必然產出無 persona 的技術任務。
- AGREE: 「US-5 風險最高」判定正確 —— 它重寫的是 `AdminPage.tsx` 唯一一段 269 行檔案內的 100 行 JSX，而該頁**目前零自動化覆蓋**（6 個 Playwright case 無一導覽至 `/admin/users`，前端無 unit／component 框架），改壞了沒有任何閘門會擋。
- AGREE: US-3「不含獨立實作」判定正確 —— 三條 AC 逐條核對實碼，零額外落點（第七節）。
- AGREE: FR-2.5 這條防禦性需求本身正確且必要 —— `UserSchema` 三個具名構造點確實存在（L451／L603／L705），其中兩處確實漏欄位，API 契約確實在說謊。我反對的是它的 AC 位置，不是它本身。
- AGREE: AC-4.4 的已知範圍事實正確 —— 實碼核實 `App.tsx` L87 與 `Sidebar.tsx` L103 皆以 J3a:view 開通授權申請頁。
- AGREE: 依賴序中「US-1／US-2 先於 US-5」的方向正確 —— 反序會讓卡片與表格兩套佈局都要補欄位，產生真實返工。

- OBJECT（事實／專業可裁決）: **AC-1.5 與 AC-3.3 是無法失敗的 AC，對 FR-2.5 零保護。** 上游 `evidence.md` 的前提「`handleRoleChange` 用 PUT 回應更新列」與 `AdminPage.tsx:89` 實碼不符（該行只做 `{...u, role: newRole}` 本地合併，回應僅供 toast；`handleToggleActive` 走 `fetchUsers()` 全表重抓），因此兩個 PUT 構造點漏補新欄位**不會**產生「操作後變空白」的畫面，兩條 AC 照樣通過。建議依第六節改寫為 API 契約層 AC（三端點皆含該欄位且值一致），AC-3.3 併入或刪除。
- OBJECT（事實／專業可裁決）: **US-1 與 US-4 都缺少「變更在既有環境實際生效」的完成條件，兩則故事的 AC 全綠時 staging 仍是壞的。** US-1：只改 `models.py` 而不補 `_ensure_*_schema` 的 `ALTER`，既有 Postgres 不會長出欄位，而 `get_current_user` 是每個已認證請求的必經路徑 → 全面 500；CI 因走 SQLite `create_all` 而全綠。US-4：兩處**預設值來源**同步在已 seed 的 DB 上完全不生效（`ensure_role_permissions_seeded` 只在空表 seed；整表重播已被 C-3 排除），`Security_Reviewer` 依舊進不去頁面。建議新增 AC-1.7 與 AC-4.5（第四節）。
- OBJECT（事實／專業可裁決）: **AC-1.3 的 *Then*「資料庫寫入次數為 1」在本 repo 沒有任何可觀測手段**（無 coverage、無 metrics、無 query log），違反 `phases/inception.md` 的「每條需求須有明確 pass/fail 準則」。建議改為以可觀測狀態表述（「該值在 5 分鐘內維持不變，之後的下一個請求才更新」），語意等價且對實作手段中立，不侵犯 application-design 的 OQ-1。
- OBJECT（事實／專業可裁決）: **依賴圖的 `US-4 → US-1` 是 acceptance 依賴而非 build 依賴，且與 US-4 自述「無技術依賴，可與 US-1 平行開發」自相矛盾。** 建議依第二節拆成 build-order 與 acceptance-order 兩層敘述，並補上 lead 未列的交付約束：US-1／US-2／US-5 動的是 `AdminPage.tsx` 同一段 JSX，必須序列進 trunk。
- OBJECT（事實／專業可裁決）: **US-1 的 INVEST Estimable 註記「一個欄位、一處顯示、一個節流機制」低估實際範圍** —— 實測為 6 個原始碼檔 + 2 個 blocking 部署資產，序列化 3 處、schema 來源 3 處。低估的估算會直接影響 delivery-planning 的排程可信度，建議改用第三節的落點表措辭。
- OBJECT（事實／專業可裁決）: **故事群未涵蓋 AC-2.1 在現行 lint 規則下必然 CI 紅燈的既知路徑。** 實跑驗證：render 或 `useMemo` 內呼叫 `Date.now()` 觸發 `react-hooks/purity`（error 級，`eslint-plugin-react-hooks@7.1.1`）→ `npm run lint` 失敗。requirements C-6 只寫「資料抓取形狀」，未涵蓋渲染純度。建議在 US-2 補實作限制註記，並在下游把 C-6 擴充為「渲染與資料抓取形狀」。
- OBJECT（事實／專業可裁決）: **AC-4.1 引用了一個 repo 內不存在的介面文字。** 導覽連結實際文字為「使用者角色」（`Sidebar.tsx` L100），無「使用者管理」字串；AC 若被直接轉成 e2e 斷言必然失敗。另 e2e stack 的測試資料只有 `admin`（`schema_rbac.sql` 只 seed 一個帳號，`users` 非空使 `init_db()` 的 11 位 persona 不被建立），AC-4.1 的 *Given* 目前無 e2e 可驗路徑。
- OBJECT（**判斷題**，兩種立場都合理，需人類裁決）: **「US-1 是否切分」不應原封留給 delivery-planning。** lead 的立場（本階段不預作決定）是合理的分工；但本階段已握有判斷所需的全部事實 —— 唯一自然的切法會產出無 persona 的後端半段（正是 Q2=A 拒絕的形狀），且 9 個落點落在 `org.md` 的 1–2 天短分支範圍內。建議把 assumption 改成帶理由的**建議不切分**，delivery-planning 若不同意仍可推翻，但不必重做同一輪分析。

---

## Revision 1 輪次（2026-08-11）— US-5 分頁

開發者視角（可實作性、可驗證性、技術依賴）對 **US-5 與其依賴／追溯表改動**的獨立盲審。
只審 Revision 1 新增內容；US-1〜US-4 已於 2026-08-09 核可，除非 US-5 與其矛盾否則不重審。
所有主張為本輪對 branch `ut` 工作樹的**直接讀取與實際執行**，逐一函式核對並附行號
（承 `project.md ## Corrections` `cid:requirements-analysis:c3`：不作「這幾個操作都是 X」的合併陳述）。

**本輪實測（非閱讀推斷）的項目**：

1. 以 `python3` + `sqlite3` 實跑負值 `LIMIT`／`OFFSET`，量測測試用 DB 的實際容忍度（輸出見 OBJECT 3）。
2. 逐行讀 `AdminPage.tsx` L77-133 三個 handler 的**成功路徑與失敗路徑**，分別記錄。
3. `grep` 全 repo 列舉 `/api/auth/list` 的消費端與 `TestClient` 使用處。
4. 讀 `docker-compose.test.yml`、`schema_rbac.sql` seed 區塊、`database.py::init_db()`、
   `regression.spec.ts`，核對短生命週期 stack 的實際帳號數與 e2e 既有的建帳號手段。
5. 讀 `user_router.py::register` 的相依鏈，確認其是否需要認證。
6. `grep -rl "md:hidden" frontend/src/` 確認小螢幕卡片佈局在今日是否存在。

---

### 一、先確認 US-5 三項既有行為主張（brief 指定逐項核對）

| US-5 的主張 | 核對結果 | 依據 |
| --- | --- | --- |
| 「清單端點為既有功能，無技術依賴」 | **屬實** | `user_router.py:437-461` `@router.get("/list", response_model=List[UserSchema])`；`:442` `db.query(User).order_by(User.id).all()`，無 `.limit()`／`.offset()`／分頁查詢參數 |
| 「US-5 與 US-1 動同一個清單端點的回應形狀」 | **屬實** | US-1 改的是元素型別 `UserSchema`（`user_router.py:111-120`），US-5 改的是容器（`:437` 的 `response_model=List[UserSchema]`）。兩者同屬 `/api/auth/list` 的回應形狀，且**消費端只有一個**：`AdminPage.tsx:41`（全 repo `grep "auth/list"` 僅此一處程式碼命中） |
| AC-5.6 對三個操作的現況判定 | **INVEST 註記正確，AC 本文的合併措辭有風險**（見 OBJECT 7） | 逐一函式：`handleRoleChange` L77-95，成功路徑 `:89` `setUsers((prev) => prev.map(...))` 就地更新；`handleToggleActive` L97-117，成功路徑 `:113` `fetchUsers()` 整份重抓；`handleDelete` L119-133，成功路徑 `:129` `fetchUsers()` 整份重抓。INVEST 表「要求修改既有的啟停用與刪除行為（現行為整份重抓）」與實碼相符 |

### 二、AC-5.3 的排序穩定性（brief 指定項）

**排序足夠穩定，AC-5.3 不是 flaky 斷言。** `list_users`（`user_router.py:442`）為
`order_by(User.id)`，`id` 是 `models.py:25` 的 primary key（`schema_rbac.sql:39` 另有
`ix_users_id`），是唯一且全序的欄位，不存在同鍵並列導致跨頁順序漂移的可能。
以此為基礎的 offset 分頁在「查詢期間資料集不變」的前提下，切頁不重複、不遺漏成立。

**但這個前提被 AC-5.6 破壞** —— 見 OBJECT 1。問題不在排序，在同一份故事的另一條 AC。

### 三、AC-5.1 的可測性（brief 指定項）

**可測，且成本接近零。** `backend/tests/helpers.py:25-35` 的 `make_session()` 以
in-memory SQLite ＋ `Base.metadata.create_all` 建表，`:46-65` 的 `make_user()` 直接
`db.add(User(...))`，`password_hash` 預設 `"unused"`（不走 bcrypt），
迴圈建立「每頁筆數 + 1」個帳號是 O(N) 次 insert，無 I/O 成本。
`TestClient` 的前置條件（`app.dependency_overrides` 覆寫 `get_db`／`get_current_user`）
已由 `team-practices.md` 測試底線 B 論證齊備。AC-5.1 的 Given「帳號總數大於每頁筆數」
在後端測試層完全可構造。

### 四、US-5 會不會弄壞現有東西（brief 指定項）

實測清點，**無既有自動化測試會被 US-5 弄壞**，因為根本沒有相關測試存在：

- `grep -rn "TestClient" backend/` → **0 命中**（與 Round 1 的實測一致，本輪複驗仍為 0）。
- `grep -rn "list_users\|UserSchema" backend/tests/` → **0 命中**；`test_j5_authz.py:13` 只
  import `_build_role_catalog` 與 `_hard_delete_user` 兩個私有 helper，不觸及清單回應形狀。
- `MeResponse`（`user_router.py:123-131`）與 `/me`（`:380`）**不受影響**：它回傳單一使用者物件，
  不是清單，分頁不觸及它。（US-1 的 AC-1.5「任一會回傳使用者物件的端點」才涵蓋它，那是 US-1 的事。）
- 前端唯一消費端 `AdminPage.tsx:41`。但 `:44-48` 是
  `const data = await res.json(); … return data;`，回傳型別靠手寫 `DbUser[]` 宣告承接 —— envelope 化後
  `users.map`（`:178`）會在執行期炸掉，而 **`tsc -b` 完全不會發現**（`team.md ## Deployment` 已如實記載此落差）。
  這是 OBJECT 6 的由來。

---

## Positions

- AGREE: 「清單端點為既有功能，無技術依賴」屬實 —— `user_router.py:437-461` 為既有端點，US-5 不新增端點、不新增服務、不新增依賴。
- AGREE: 「US-5 與 US-1 動同一個清單端點的回應形狀，須同一次決定」屬實且理由紮實 —— 兩者都改 `/api/auth/list` 的 `response_model`，消費端只有 `AdminPage.tsx:41` 一處，分兩次改等於讓同一個消費端改兩次。把它標為「避免重工、可覆寫」而非技術依賴，性質判定正確。
- AGREE: AC-5.3 的「切頁不重複、無遺漏」在排序層面是有意義的斷言，不是 flaky —— `order_by(User.id)`（`user_router.py:442`）以唯一 PK 為全序鍵，無同鍵並列漂移的可能。
- AGREE: AC-5.1 在現有測試骨架下可構造 —— `helpers.py:46-65` 的 `make_user()` 可零成本建出超過一頁的帳號數。
- AGREE: INVEST 表「要求修改既有的啟停用與刪除行為（現行為整份重抓）」與實碼逐行相符（`AdminPage.tsx:113`／`:129`），這一句沒有重蹈 requirements Revision 1 Critical 的合併陳述覆轍。
- AGREE: US-5 不會弄壞任何既有後端測試 —— 全 repo 無 `TestClient`、`backend/tests/` 無任何檔案斷言清單回應形狀（本輪 `grep` 複驗）。
- AGREE: `MeResponse` 與 `/me` 不在 US-5 的影響面內 —— 它回傳單一物件而非清單。

- OBJECT（事實／專業可裁決）: **AC-5.3（切頁無遺漏）與 AC-5.6（刪除就地移除、不重抓、不遞補）在 offset 分頁下互相矛盾，實際會讓稽核者每刪一個帳號就靜默漏看一個帳號。** | 證據：`user_router.py:442` 為 `order_by(User.id)` 的 offset 分頁（無 keyset）；`AdminPage.tsx:119-133` 的刪除路徑在 US-5 後必須改為就地移除（AC-5.6 明訂「未整份重抓清單」）。推演（每頁 P 筆，總數 N）：使用者在第 1 頁刪掉第 k 筆（k ≤ P）→ 本地移除、不重抓 → 伺服器端現有 N-1 筆，原本位於索引 P 的 `u_{P+1}` 左移到索引 P-1，也就是**第 1 頁的最後一格**，而第 1 頁沒有重抓 → 使用者點第 2 頁（`OFFSET P`）拿到的是 `u_{P+2}` 起 → **`u_{P+1}` 從未被任何一頁渲染過**。每一次刪除都精確漏掉一個帳號，且畫面上沒有任何跡象。第二個同源後果：就地刪除後未重抓，AC-5.2 要求的「總筆數」在前端仍是刪除前的值，總頁數連帶失準，而 AC-5.6 只把「該頁暫時少一列」列為預期行為，沒有涵蓋總筆數。本 intent 的上游價值是**逐帳號**取得稽核證據，靜默漏掉一個帳號不是外觀瑕疵。 | 建議修正：(1) AC-5.3 的 Then 加上適用範圍限定（「在本次瀏覽期間未發生刪除的前提下」），使它成為可判定且不與 AC-5.6 打架的條款；(2) 為「刪除後的跨頁一致性」另立一條 AC 或明記為已知取捨（兩個可行方向：刪除後就地移除但同步遞減總筆數並標記該頁為 stale，或把「刪除後換頁需重抓」列為 AC-5.6「不整份重抓」的例外）；(3) 把「offset 分頁 + 就地刪除的跨頁一致性策略」登錄為 application-design 的開放決策 —— 現行 OQ-6 只涵蓋每頁筆數與 envelope 形式，不含這一項。`phases/inception.md` 明訂「Never carry forward unresolved contradictions between requirements」，兩條 AC 同時為 Must 且同屬一則故事，不能留給實作者臨場裁決。

- OBJECT（事實）: **US-5 DoD 宣稱 AC-5.3「在 e2e 層無可執行驗收路徑」，此結論不成立 —— 建立第二頁的路徑存在、公開、而且既有測試套件已經在用它。** | 證據：DoD 的**前提**屬實（`deploy/docker-compose.test.yml:21` 把 `schema_rbac.sql` 掛成 `docker-entrypoint-initdb.d`；`schema_rbac.sql:497-505` 只 `INSERT` 一個 `admin`；`database.py:49-50` 的 11 位 persona seed 有 `if user_count == 0` 閘門，因 `admin` 已存在而跳過 → boot 後確實只有 1 個帳號）。但**結論**錯：①`POST /api/auth/register`（`user_router.py:290-291`，簽章為 `def register(request: RegisterRequest, db: Session = Depends(get_db))`）**沒有任何認證依賴，是公開端點**；②註冊出來的帳號 `authorization_status="pending"`、`role=None`，而 `list_users`（`:442`）回傳**全部** `User` 列、不做任何狀態過濾，因此這些帳號會出現在清單裡並計入分頁；③既有 e2e **已經在做這件事**：`regression.spec.ts:56-74` 的「Developer 看不到系統管理區」就是走 UI 註冊流程即席建帳號。以 Playwright 的 `request` fixture 直接打 API 建立「每頁筆數 + 1」個帳號，是前置步驟成本（每次註冊一次 bcrypt 雜湊），不是「無路徑」。 | 建議修正：把該條 DoD 由「無可執行驗收路徑／由端點測試承接」改為「需在 e2e 前置步驟以公開註冊端點建立超過一頁的帳號數；成本為 N 次 API 呼叫，N 取決於 application-design 定案的每頁筆數（OQ-6），需連同 `playwright.config.ts:12` 的 30 秒單案逾時一併評估」。這項更正會改變下游判斷：AC-5.3 目前被歸類為「只能靠端點測試」，而端點測試跑的是 SQLite（見下一條），兩層一起放掉會讓 AC-5.3 完全沒有真實資料庫上的驗證。另注意此條與 US-3 的 AC-3.1a 缺口**不同型**：AC-3.1a 缺的是「特定角色的帳號」（註冊只能拿到 pending／無角色，確實補不出 `Security_Reviewer`），AC-5.3 缺的只是「帳號數量」，而數量是註冊端點直接能給的。把兩者並稱「與 AC-3.1a 同型」（stories.md Assumptions 該條）是誤判。

- OBJECT（事實／專業可裁決）: **AC-5.5 的 Then「不產生未處理的例外」太弱，而它唯一被規劃的自動化落點在結構上看不到要防的失敗。** | 證據：DoD 指定以 `TestClient` 承接 AC-5.5，而 `backend/tests/helpers.py:26-29` 的測試 DB 是 in-memory SQLite。本輪實跑量測 SQLite 對非法分頁值的容忍度：<br>指令：`python3 -c` 以 `sqlite3` 建 10 列表後逐一執行 `select id from t order by id limit L offset O`<br>輸出：`LIMIT 5 OFFSET -5 -> 5 rows [1,2,3,4,5]`／`LIMIT 5 OFFSET -1 -> 5 rows [1,2,3,4,5]`／`LIMIT -1 OFFSET 3 -> 7 rows [4,5,6,7,8,9,10]`／`LIMIT 0 -> 0 rows`<br>亦即：**SQLite 對負 OFFSET 靜默當成 0，對負 LIMIT 靜默當成「不限筆數」**。後果有二：(a) 若實作把非法值原樣送進查詢層，SQLite 上的 `TestClient` 測試會回 200、不拋例外，斷言「不產生未處理的例外」**照樣通過**；(b) `LIMIT -1` 這一格更糟 —— 端點回傳**整張表**且測試全綠，而這正是 requirements.md:139 記載 NFR-8 存在的理由（「導入分頁使單次回應的資料量與查詢成本有界，降低資源耗盡與大量資料一次外洩的暴露面」）。staging 用的是 PostgreSQL（`project.md ## Tech Stack`、`docker-compose.test.yml:15`），與測試環境對負值的處置是否一致，本輪無可用的 PG 實例可實測，故不作斷言 —— 但正因為不確定，AC 更不能只斷言「不拋例外」。 | 建議修正：AC-5.5 的 Then 增列一條與資料庫方言無關、且**在 SQLite 上就會紅**的可觀測斷言：「無論參數為何，單次回應的帳號筆數不得超過每頁筆數上限」。這一條在 `LIMIT -1` 洩漏全表時必定失敗，把 NFR-8 真正要防的東西變成可執行的判準。

- OBJECT（事實／專業可裁決）: **AC-5.5 的「被拒絕／參數被夾到合法範圍」二選一措辭，讓兩種互斥的可觀測結果都算通過，而這個選擇沒有被指派給任何階段定案。** | 證據：AC-5.5 Then 原文為「請求被拒絕或參數被夾到合法範圍」。以 FastAPI 現行寫法兩者都做得到、也都只需既有能力（`user_router.py:10` 已 import `Query`，`:465` 已有 `Query("pending", alias="status")` 的用法先例；加 `ge=1` 會走 422 拒絕路徑，不加而自行 `max(1, page)` 則是夾取路徑；`grep "ge=\|le=\|gt=\|lt="` 全 backend → 0 命中，即本 repo 尚無任何數值約束先例，兩條路都是新寫法，沒有既有慣例可依）。問題不在能不能做，在**兩條路對前端是不同契約**：走 422 時 `AdminPage.tsx:45-47` 的 `if (!res.ok) throw new Error(data.detail ...)` 會把整個表格換成錯誤畫面，走夾取時前端什麼都不用做。QA 也無法只憑 AC 寫出斷言（`assert status == 422` 與 `assert status == 200` 互斥，兩者都「符合」AC）。而 OQ-6（requirements.md:196）只涵蓋「每頁筆數與回應 envelope 的具體形式」，不涵蓋這一項；上游 NFR-8 用同樣的「或」，本 stage 沿用不算誤讀，但故事層的 AC 是要被轉成測試的那一層，模糊在這裡才真正產生成本（`phases/inception.md`：每條需求須有明確 pass/fail 準則）。 | 建議修正：AC-5.5 只保留與選擇無關的不變量（不得產生未處理例外 ＋ 回應筆數有界，見上一條），並把「非法參數採 4xx 拒絕 vs 夾到合法範圍」明列為 application-design 的開放決策（比照 OQ-6 的處理方式登錄），不在故事層並列兩個結果。

- OBJECT（事實）: **US-5 的驗收依賴漏列 US-4，而 AC-5.7 在 US-4 之前不可能被驗收；這與同一份文件的排序約束（US-5 須在 US-4 之前定案）方向相反，構成內部矛盾。** | 證據：AC-5.7 的 When 是「分別在桌面寬度與斷點以下的小螢幕檢視」，Then 要求「兩種佈局皆有可用的分頁控制」。小螢幕卡片佈局**今日不存在**：`AdminPage.tsx:135-268` 全頁只有單一 `<table>`（`:167`），無任何佈局切換；`grep -rl "md:hidden" frontend/src/` → **0 命中**（全前端無此模式）。該佈局由 US-4 產出（US-4 AC-4.1）。因此 AC-5.7 的 Given 在 US-5 自身的驗收時點無法成立。而依賴總覽同時寫著「US-5(分頁) 的互動須在 US-4(卡片) 之前定案」，即 US-4 在 US-5 之後 —— 兩句合起來 US-5 帶著一條永遠驗不了的 AC。US-5 的「驗收依賴」目前只列 US-3。 | 建議修正：在 US-5 的**驗收依賴**加上 US-4（限 AC-5.7、及 AC-5.8 的小螢幕面向），並在依賴總覽的驗收依賴區塊補一條 `US-4 ..> US-5`；或明記 AC-5.7 的小螢幕半邊與 US-4 合併驗收。兩者擇一即可，但不能兩邊都不寫 —— `phases/inception.md` 對未解決矛盾的規定與 US-4 自身「建置依賴 US-1、US-2」的既有寫法都要求把這類關係寫明。

- OBJECT（事實）: **追溯表宣稱 C-9 由 AC-5.1、AC-5.6 承載，但 C-9 明文要求的「型別契約同步」在 US-5 的九條 AC 與四條 DoD 中沒有任何落點。** | 證據：requirements.md:154 的 C-9 原文為「…所有既有消費端都會看到新形狀，**型別契約與各消費端的呈現皆須同步**」；stories.md 追溯表該列（第 452 行）填的是「US-5（AC-5.1、AC-5.6）」，但 AC-5.1 講的是每頁筆數、AC-5.6 講的是頁次保留，兩條都不涉及型別契約；US-5 的 DoD 四條分別是端點測試、e2e、每頁筆數留 application-design、前端抓取形狀，同樣沒有。這不是形式問題：`AdminPage.tsx:44-48` 是 `const data = await res.json(); … return data;`，回傳型別純靠手寫 `DbUser[]` 宣告承接，envelope 化後 `users.map`（`:178`）會在執行期炸掉而 `tsc -b` 一聲不吭（`team.md ## Deployment` 已把這條落差記為既知事實）。亦即在這條變更路徑上，型別契約是**唯一**可能存在的編譯期護欄，而它現在無人認領。補充脈絡（不作為依賴主張）：下游 `units-generation/unit-of-work.md:32` 已規劃 `api-type-contract` 單元（committed 規格檔 ＋ 型別檔 ＋ 兩道 CI 漂移檢查），同檔 `:107` 記明「使用者物件型別採用該單元產生的型別，不再手寫」；US-5 同時新增查詢參數與新的 envelope schema，會改動該規格檔的內容，而 repo 今日尚無規格檔、`ci.yml` 亦無漂移檢查 job（本輪 `ls` 與讀 `ci.yml` 四個 job 複驗）。 | 建議修正：US-5 的 DoD 增列一條「回應契約變更須同步型別契約／API 規格產出物（若該機制屆時已落地則同步重 dump，否則明記前端型別宣告的手動同步落點）」，或把追溯表 C-9 該列的涵蓋範圍如實縮為「AC-5.1、AC-5.6 覆蓋回應形狀與消費端呈現；**型別契約同步無 AC 落點**」，比照本檔既有處理 FR-1.4／FR-6.7 的誠實記載方式，不讓它悄悄計入已涵蓋。

- OBJECT（事實／專業可裁決，較輕）: **AC-5.6 的「對該頁的某個帳號執行停用（角色調整、刪除同理）」是合併陳述，正是 requirements Revision 1 花掉一個 Critical 才更正的形狀；且它只涵蓋成功路徑，遺漏了會把使用者丟回第 1 頁的失敗路徑。** | 證據：合併面 —— 逐一函式核對，三個操作對本 AC 的現況並不同等：`handleRoleChange`（`AdminPage.tsx:89`）今日已就地更新，本 AC 對它**恆真、零改動**；`handleToggleActive`（`:113`）與 `handleDelete`（`:129`）今日皆 `fetchUsers()` 整份重抓，是真正的行為變更。INVEST 表已寫對，AC 本文卻用「同理」把三者拉平，讀者無從分辨哪一個要動。requirements.md:99 已為同一組操作留下逐操作陳述的範本，AC 這裡沒有沿用。失敗路徑面 —— `AdminPage.tsx:91-94` 的 `catch` 區塊在角色調整失敗時呼叫 `fetchUsers()`；US-5 之後若 `fetchUsers()` 不帶頁次，任何一次操作失敗都會把稽核者從第 2 頁彈回第 1 頁，而 AC-5.6 的 When 只寫「執行停用」（成功語境），涵蓋不到。 | 建議修正：(1) AC-5.6 的括號改為逐操作註記現況（例如「角色調整今日已就地更新，本條對它為既有行為；啟停用與刪除今日為整份重抓，本條要求改為就地更新」），沿用 requirements.md:99 已建立的體例；(2) 加一條 And：「操作失敗時亦維持目前頁次」，或明記錯誤路徑的頁次行為由 application-design 定案 —— `AdminPage.tsx:93` 是 US-5 之後**唯一**殘留的整份重抓呼叫點，不寫明必然被漏改。
