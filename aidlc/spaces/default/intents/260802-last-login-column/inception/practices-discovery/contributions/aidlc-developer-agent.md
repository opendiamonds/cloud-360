**Collaborator:** aidlc-developer-agent

## Contribution

開發者視角的獨立審視。所有主張皆以本輪對 repo 的直接讀取為據（非轉引 codekb），
與 codekb 或 lead 草稿不一致處已標注。行號基準為 branch `ut` 的工作樹現況。

---

### 一、先修正三處事實錯誤（會影響規則措辭）

lead 草稿與 codekb 的下列數字／位置經實測不成立。規則若建立在錯誤事實上，
訪談會問錯題、規則會寫錯範圍。

**E1 — 前端 `fetch()` 是 52 處、10 支檔，不是「32 處、8 支」**

```
AssessmentPage.tsx 16   WorkspacePage.tsx 13   RolePermissionsPage.tsx 4
AdminPage.tsx       4   LensCriteriaEditor 4   AuthorizationRequestsPage 3
ShareModal.tsx      3   WaitingApprovalPage 2  LoginPage.tsx 2
AuthContext.tsx     1                          ── 合計 52
```

（`grep -rnE '(^|[^A-Za-z0-9_.])fetch\(' frontend/src`，已排除 `fetchUsers(` 等同名前綴。）
另有 40 處手寫 `Authorization` header。

更關鍵的是**框架描述有誤**：不是「無集中抽象」。`frontend/src/config/api.ts` 提供
`API_BASE_URL`／`WS_BASE_URL`／`apiUrl()`／`wsUrl()`，且 52 處呼叫**一致地**經 `apiUrl()` 組 URL。
真正未集中的是**認證標頭、401 處理、錯誤解包、回應型別**四項。
正確表述為「**URL 組裝已集中，認證與錯誤處理未集中**」——這決定了未來若要收斂，
成本落在 header/error 而非 URL，也決定了現在該不該寫規則（見第三節）。

**E2 — 角色清單是 5 份以上物化，且已經漂移**

brief 給的三處（`rbac.py` / `schema_rbac.sql` / `AdminPage.tsx`）與 codekb 給的三處
（`rbac.py` / `user_router.py::ROLE_DISPLAY_NAMES` / `AdminPage.tsx`）都不完整：

| 位置 | 形式 | 性質 |
|---|---|---|
| `backend/services/rbac.py:23-34` `CANONICAL_ROLES` | 11 元素 list | **正本** |
| `backend/services/auth.py:82-86` `require_any_user` | 11 個字串手寫 allowlist | **手寫副本（brief 與 codekb 皆未發現）** |
| `backend/services/user_router.py:44-56` `ROLE_DISPLAY_NAMES` | 11 個 key 的 dict | key set 副本 |
| `frontend/src/pages/AdminPage.tsx:15-27` `AVAILABLE_ROLES` | 11 元素 array | 跨語言手寫副本 |
| `schema_rbac.sql:180-308` | INSERT 字面值（11 角色 × 28 story） | seed 副本 |
| `backend/services/rbac_seed_data.py` `DEFAULT_ROLE_PERMISSIONS` | 資料常數 | seed 正本 |

`user_router.py:26` 是 `from services.rbac import CANONICAL_ROLES`——它**不是**手寫副本，
codekb 把 import 誤記為副本。真正沒被記到的是 `auth.py::require_any_user`。

**漂移已經發生（非假設性風險）**：`AVAILABLE_ROLES` 與 `CANONICAL_ROLES` **集合相同、順序不同**
（正本首項 `Project_Architect`，前端首項 `Project_Admin`）。兩份副本已經開始各走各的。

**E3 — 模組 docstring 的品質沒有草稿說的那麼齊**

草稿寫「18 支 service 模組中 16 支已載明**職責／安全邊界／契約**」。實測 `user_router.py:1-3`
的 docstring 是單行清單（`user_router — 登入／註冊／使用者角色／角色權限矩陣／J5 授權申請 API`），
沒有安全邊界、沒有契約段。codekb 原文是「**多數**明確載明」，草稿把「多數」升格成「16 支」。
建議措辭改為「模組級 docstring 覆蓋率 16/18；其中 router 類多為單行摘要，
`agent_router.py` 的『契約（前端依賴，請勿變更）』是最完整的樣板」。

---

### 二、問題 1：分層不一致該怎麼寫進 `## Code Style`

**兩個提案都不採用。宣告「應有 service 層」與「並列記載兩種模式」各有致命傷：**

- 宣告應有 service 層 → 1,358 LOC（`user_router.py` 831＋`collab_router.py` 527）當場違規。
  更硬的反證是：codekb 自己的修復順序把「T9 `user_router.py` 拆分」排在第 11 位，
  且明寫「**建議在 T10 有測試保護之後才做**」。此刻宣告該規則，等於讓每個碰 `user_router.py`
  的 PR 在「違規」與「無測試保護的重構」之間二選一——而 `user_router.py` 目前
  **零 HTTP 層測試**（全 repo `TestClient` 使用數為 0）。規則會逼出風險最高的那個選項。
- 純並列記載 → 沒有方向性。新模組可以合法地選擇較差的那個形狀，規則等於沒寫。

**建議採用「依落點分流」的寫法**，可直接貼進 `## Code Style`：

```markdown
### 後端分層

分層成熟度**依模組家族而異**，這是已知且刻意保留的現況，不是待修的違規：

- `review` / `lens` / `wa_*` 家族：router → orchestrator/service → 純函式引擎 → model，
  三層清楚。純函式引擎層（`wa_rule_engine.py`／`wa_lens_engine.py`／`diagram_builder.py`）
  不讀 DB、不連外，是 property-based 測試的實際落點。
- `user` / `collab` 家族：無 service 層，商業邏輯直寫 handler
  （`user_router.py` 831 LOC、`collab_router.py` 527 LOC）。

規則依**改動落點**分流：

- **新模組／新業務邏輯** → 一律走三層形狀，純運算下沉到不讀 DB 的函式。
- **修改 `user_router.py`／`collab_router.py`** → **就地沿用既有形狀**，不趁機夾帶
  service 層抽取。理由是這兩支目前無 HTTP 層測試保護，重構與功能變更混在同一個 PR
  不可驗證。抽 service 層是獨立任務，前置條件是先有端點測試。
- **禁止擴大**：不得在這兩支之外新建「router 直寫商業邏輯」的模組。
```

這個寫法同時滿足三件事：誠實（記載兩種模式都存在）、有方向（新碼有唯一正解）、
可執行（現存碼不會因為規則而立刻變成技術債待辦）。

---

### 三、問題 2：ESLint 副產物該不該明文化

**該寫，但草稿低估了範圍，而且必須帶版本出處。**

**先修正範圍**：草稿只提 `react-refresh` 與 `react-hooks/set-state-in-effect` 兩條。
實測 `eslint-plugin-react-hooks@7.1.1` 的 `flat.recommended` 開了 **16 條 error 級規則**：

```
rules-of-hooks, static-components, use-memo, preserve-manual-memoization,
immutability, globals, refs, set-state-in-effect, error-boundaries, purity,
set-state-in-render, config, gating          ← 以上 error
exhaustive-deps, incompatible-library, unsupported-syntax  ← warn
```

也就是說 `immutability`（不得就地改 props／state 物件）、`purity`、`static-components`
同樣是 CI 紅燈條件，遠不只 `set-state-in-effect`。只寫兩條會讓人誤以為其餘可放行。

**`exhaustive-deps` 只是 warn，而且 CI 不擋**：`ci.yml` 的 Lint step 跑
`npm run lint` = `eslint .`，**沒有 `--max-warnings 0`**。實測現況為
`0 errors, 3 warnings`（`AssessmentPage.tsx:365`、`LoginPage.tsx:36`、`WorkspacePage.tsx:279`
的 `exhaustive-deps`），exit 0。這個「error 擋、warning 不擋」的分界必須寫明，
否則新人會把 3 個既存 warning 讀成「lint 沒在跑」。

**回應「會不會把工具的偶然約束固化成團隊規則」**：會，如果只寫形狀不寫來源。
緩解手段是**寫明出處與重審條件**，不是省略不寫。一條「違反即 CI 紅燈」卻只存在於
tribal knowledge 的規則，代價是每個新人（與每個 AI agent）各撞一次紅燈才學會——
這正是 codekb 對本 repo 的核心診斷（「規則寫在文件裡而不是寫在檢查器裡」）的鏡像問題：
這裡是**規則寫在檢查器裡但沒寫進文件**，方向相反、成本一樣。

建議寫法：

```markdown
### 前端：lint 規則造成的結構約束

以下形狀**不是團隊的美學選擇，而是 lint 規則的直接後果**，違反即 CI 紅燈。
出處為 `eslint-plugin-react-hooks@7` 與 `eslint-plugin-react-refresh@0.5`
的 flat recommended（`frontend/eslint.config.js`）。**升級或更換 lint 套件時本節同步重審。**

- **Context 拆兩檔**（`react-refresh/only-export-components`）：Provider 元件放 `.tsx`，
  型別與 hook 放同名 `.ts`。現例 `AuthContext.tsx` + `auth-context.ts`。
- **資料抓取拆兩層**（`react-hooks/set-state-in-effect`，error）：該規則做過程間分析，
  effect 同步呼叫的函式內只要有 setState 就被擋。因此拆成
  ①純抓取函式（不碰 state，回傳資料）②呼叫端在 `.then/.catch/.finally` 更新 state
  ③`useEffect` 內用 `cancelled` flag 防卸載後 setState。
  現例 `AdminPage.tsx:40-70` 的 `fetchUserList` / `fetchUsers` / `useEffect`。
- **不可就地修改物件**（`react-hooks/immutability`，error）：state 更新一律回傳新物件
  （現例 `setUsers((prev) => prev.map(...))`）。
- CI 只擋 **error**：`npm run lint` 未加 `--max-warnings 0`，
  `exhaustive-deps`（warn）不擋，現有 3 個 warning 為已知既存狀態。
```

---

### 四、問題 3：前端無集中 API client → 「現況」，且**本 intent 不新增呼叫點**

**列為現況，不列為應改進。** 兩個理由：

1. `team.md` 是已affirm 的實踐，不是待辦清單。T13 已在 `code-quality-assessment.md`
   以 P2 登記，重複登記在 `team.md` 只會讓兩份清單開始漂移——正是本 repo 的主症狀。
2. 收斂 52 處呼叫點是獨立的重構任務，寫進 `team.md` 會讓每個碰 `fetch` 的 PR 帶著違規標籤。

**同時要更正 brief 的一個前提**：「本 intent 會再加一處使用」**不成立**。
`AdminPage.tsx` 已經有 `fetchUserList` 打 `/api/auth/list`（L41），本 intent 是
**擴充該端點既有回應的欄位**，前端不新增 `fetch` 呼叫點、不新增 header 手寫處。
若後續設計改成獨立端點，這個前提才會成立，屆時應回頭重評。

現況段落建議這樣寫（描述性、不帶規範語氣）：

```markdown
### 前端 API 呼叫現況

URL 組裝已集中於 `src/config/api.ts`（`apiUrl()` / `wsUrl()`），52 處 `fetch()` 一致沿用。
未集中的是認證標頭（40 處手寫 `Authorization: Bearer`）、401 處理、錯誤解包與回應型別。
新增呼叫點時沿用現有形狀（`apiUrl()` + 手寫 header + `res.ok` 判斷 + `data.detail` 取錯誤訊息），
不要單點自創抽象——半套抽象比沒有抽象更難收斂。
```

---

### 五、問題 4：重複真實來源該用什麼形式的規則約束

**不要用「禁止重複」這種無法驗證的規則。**（本 repo 的 20 項技術債裡，
C3 叢集的診斷就是「沒有機制發現分歧」；再加一條無檢查器的禁令只會複製同一個失敗模式。）

建議三段式，**其中兩段今天就能落地、零新工具**：

**(1) 消除可消除的副本。** `AdminPage.tsx::AVAILABLE_ROLES` 是**多餘**的——
後端已有現成端點 `GET /api/auth/roles`（`user_router.py:430-434`，回傳
`{"roles": CANONICAL_ROLES, "stories": STORY_IDS}`）。前端硬編一份 11 元素陣列
沒有任何理由，且已經與正本順序不同。這不是「規則」問題，是「有 API 沒用」。

**(2) 把剩下的副本變成可失敗的斷言。** Python 側三份現在就可以用一個 5 行 unittest 鎖住，
且會被既有 CI（`python -m unittest discover -s tests -v`）直接執行、無需任何新依賴：

```python
# backend/tests/test_rbac.py 追加
def test_role_lists_stay_in_sync(self):
    from services.rbac import CANONICAL_ROLES
    from services.auth import require_any_user
    from services.user_router import ROLE_DISPLAY_NAMES
    self.assertEqual(set(ROLE_DISPLAY_NAMES), set(CANONICAL_ROLES))
    self.assertEqual(set(require_any_user.allowed_roles), set(CANONICAL_ROLES))
```

**(3) 規則措辭寫成「新增副本前的義務」，而非「不得重複」：**

```markdown
### 單一真實來源

當同一份事實已存在於程式中（角色清單、權限矩陣、schema 欄位），新增第二份物化前
必須先確認是否有既有常數或 API 可直接使用。若確實無法避免（如跨語言邊界），
**新增副本的同一個 PR 必須一併新增鎖住兩者一致的測試**；無法寫測試的副本不新增。

已知既有副本與正本：
- 角色清單正本 `services/rbac.py::CANONICAL_ROLES`；
  副本 `services/auth.py::require_any_user`、`services/user_router.py::ROLE_DISPLAY_NAMES`、
  `frontend/src/pages/AdminPage.tsx::AVAILABLE_ROLES`、`schema_rbac.sql` seed。
- 密碼雜湊正本 `services/auth.py::get_password_hash`；
  副本 `database.py::hash_password`（L26-29，逐字相同）。
```

密碼雜湊那份（T15）我實測確認**逐字相同**（`auth.py:24-27` vs `database.py:26-29`），
且 `database.py` 已 `import bcrypt` 自己做。這是安全相關邏輯的副本，
就算不在本輪處理，也應該在規則裡點名，因為兩份不同步是靜默的安全事故。

---

### 六、問題 5：命名與慣例——草稿漏掉／誤述的部分

草稿的 `## Code Style` 完全沒有涵蓋命名。以下五項為實測，建議補入：

| 項目 | 實測現況 | 建議措辭 |
|---|---|---|
| Python 檔名／router | `snake_case.py`；router 一律 `*_router.py`（5/5）；WA 引擎一律 `wa_*` 前綴 | 一致，直接追認 |
| React 命名 | 元件與頁面 `PascalCase.tsx`；頁面一律 `*Page.tsx`（8/8） | 一致，直接追認 |
| 非元件 TS 檔名 | **不一致**：`auth-context.ts`（kebab）vs `useCollaboration.ts`（camel）vs `diagramViewer.ts`（camel） | 記為已知不一致；hook 檔沿用 `use*.ts`，其餘 camelCase，`auth-context.ts` 為既存例外不改名 |
| logger 命名 | **不一致**：11 支用 `logging.getLogger("cloud360.<module>")`，5 支用 `__name__`（`collab_router`、`design_agent`、`agent_router`、`diagram_builder`） | 新模組一律 `"cloud360.<module>"`；本 intent 觸及的 `user_router.py` 已是此形式 |
| `HTTPException` 呼叫風格 | **同檔混用**：`user_router.py` 內 12 處 `status_code=` 具名、17 處位置引數（`HTTPException(404, detail=...)`） | 記為已知不一致，不強制統一（改動屬純格式，收益低於 diff 噪音）；新程式碼沿用所在函式鄰近寫法 |

另外兩項既有紀律，草稿有提到但值得升格為明文保護條款：

- **零 `TODO`／`FIXME`／`HACK`／`XXX`**（全 repo）——建議寫成「未完成工作追到 issue／spec，
  不留在程式碼裡」，這是可被 grep 驗證的規則。
- **錯誤處理形狀**：`user_router.py` 有 **0 個 `try/except`**，全部靠 `raise HTTPException` 快速失敗
  （`review_router.py` 4 個、`collab_router.py` 5 個，都用在外部呼叫邊界）。
  建議明文：「DB／驗證錯誤直接 `raise HTTPException`，不 try/except 吞掉；
  `try/except` 只用在外部依賴邊界（LLM、webhook、檔案）且必須降級或記 log，不得靜默」。
  這與 `construction.md` 的「Errors must be surfaced」一致，且描述的是既有事實。

---

### 七、問題 6：本 intent 實作時**必須遵守**的既有慣例（否則破壞一致性或 CI 紅燈）

改動面：`users` 加欄、改 `UserSchema` 與 `list_users`、改 `AdminPage.tsx` 的 `DbUser` 與表格。

**D1 —（最高風險）`UserSchema` 有三個構造點，而且現在就已經在靜默漏欄位**

`user_router.py` 內 `UserSchema` 以**具名引數逐欄構造**三次：

| 位置 | 函式 | 傳入欄位 |
|---|---|---|
| L451-458 | `list_users` | 6 欄（含 `requested_role`） |
| L602-608 | `update_user_active` | **5 欄，漏 `requested_role`** |
| L705-711 | `update_user_role` | **5 欄，漏 `requested_role`** |

後兩者靠 `requested_role: Optional[str] = None` 的預設值靜默填 `None`——
也就是說兩個 PUT 的回應**現在就在回報錯誤的 `requested_role`**，沒有任何工具會報錯。

**新欄位若只加進 `UserSchema` 而沒有同步三個構造點，會完全複製這個失敗模式**：
`/api/auth/list` 有值，但 `PUT /{id}/role`、`PUT /{id}/active` 回 `null`，
而前端 `handleRoleChange` 正是用 PUT 的回應更新列（`AdminPage.tsx:89`
`setUsers(prev => prev.map(...))`）——結果是**改完角色後該列的最後活動時間會變空白**，
重新整理才會回來。這是使用者可見的 bug，且 e2e 不會抓到（`regression.spec.ts` 未斷言表格內容）。

**必做**：三個構造點全部補；或把三處收斂成一個 `_serialize_user(u, requested=None)` helper
（`user_router.py` 已有 `_serialize_auth_request` 這個 helper 先例，L250-261，形狀可直接套）。

**D2 — 不能靠 ORM 自動填值**

`UserSchema` 用的是 `class Config: orm_mode = True`（L119-120），這是 **Pydantic v1 語法**；
`requirements.txt` 的 `pydantic` **未 pin**，實際解析到 v2（v2 已改名 `from_attributes`）。
這行設定目前是**死設定**。全部三個構造點都是手寫具名引數，並非偶然——
不要在新欄位上嘗試 `UserSchema.from_orm(u)` 或 `model_validate(u)`。

**D3 — 加欄位到 `users` 有兩次現成先例，照抄即可**

`database.py` 的 `_ensure_<story>_schema()` 是既有機制，且**兩次都是加 `users` 欄位**：

- `_ensure_a4_schema()`（L123-）：`ALTER TABLE users ADD COLUMN IF NOT EXISTS last_opened_diagram_id INTEGER`
- `_ensure_j5_schema()`（L151-）：`ALTER TABLE users ADD COLUMN IF NOT EXISTS authorization_status VARCHAR(32) DEFAULT 'approved'`

三者由 `init_db()`（L38-44）在 `Base.metadata.create_all()` 之後依序呼叫。
本 intent 應新增同形狀的 `_ensure_<story>_schema()` 並掛進 `init_db()`，
配合 `models.py` 的 `Column` 宣告、`schema_rbac.sql`、`DEPLOY.md`（後兩者由 `project.md`
的 schema↔deploy blocking 規則強制）。

**注意 `User.to_dict()`（`models.py:42-50`）是死碼**——全 repo `to_dict()` 呼叫數為 0。
**不要**為了「一致」把新欄位加進去，那只是多一份要維護的副本。

**D4 — 時間欄位的既有型別與序列化慣例**

- 資料庫欄位：`DateTime(timezone=True)`（`models.py` 的 `RoleAuthorizationRequest.created_at` 等）。
- 產生時間：`datetime.now(timezone.utc)`——`user_router.py` 已有三處（L424、L511、L549），
  且 L7 已 `from datetime import datetime, timezone`。
  **不要抄 `auth.py:32,34` 的 `datetime.utcnow()`**，那是 T14 已登記的 deprecated 用法。
- Schema 型別：`Optional[datetime]`（`AuthorizationRequestSchema` L177-180），交給 Pydantic 序列化，
  不手動 `isoformat()`。

**D5 — 前端時間欄位有現成樣板，直接沿用**

`AuthorizationRequestsPage.tsx` 已經是「admin 表格＋時間欄」的完整先例：

- interface 欄位型別是 **`string`** 不是 `Date`：`created_at?: string;`（L12）
- 儲存格：`{row.created_at ? new Date(row.created_at).toLocaleString() : '—'}`（L163）

`toLocaleString()` 是全 repo 一致做法（另見 `WorkspacePage.tsx:1038`、
`AssessmentPage.tsx:1610`、`exportReviewPdf.ts:220`），且**沒有引入任何日期函式庫**
（`package.json` 無 dayjs／date-fns）——不要為此 intent 新增依賴。

空值以 `'—'`（em dash）表示，與 `AdminPage.tsx:201` 的 `{u.role || '—'}` 一致。

`DbUser` 新欄位應宣告為 `欄位名?: string | null;`——比照既有的
`requested_role?: string | null`（L12），因為既有使用者該欄為 NULL。

**D6 — `AdminPage.tsx` 表格改動的具體落點**

- `<thead>`：5 個 `<th>` → 6 個（L170-174），沿用 `className="px-6 py-5"`。
- `<tbody>`：對應加 `<td>`，沿用 `className="px-6 py-4"`；時間類文字沿用
  `AuthorizationRequestsPage` 的 `text-slate-400 text-xs` 色階。
- 表格**無 colspan、無空狀態列**，不需要同步調整跨欄數。
- **載入／錯誤態不動**：`isLoading ? '載入中…' : error ? {error} : <table>`（L161-165）
  是整塊替換，加欄不影響——與 `project.md` 已學到的「加欄型 feature 沿用既有狀態呈現」一致。

**D7 — 抓取形狀不得更動**

本 intent 不改變抓取邏輯，`fetchUserList`（純抓取，`useCallback` deps `[token]`）／
`fetchUsers`（呼叫端更新 state）／`useEffect` 的 `cancelled` flag 三段結構必須原樣保留。
把新欄位的取得塞進 `useEffect` 或在 `fetchUserList` 內 setState 會觸發
`react-hooks/set-state-in-effect`（error 級）→ CI 紅燈。

**D8 — 測試的現實限制（給 quality 視角的交接資訊，非我的建議）**

`user_router.py` 目前無任何測試可觸及（全 repo `TestClient` 使用數 0），
`backend/tests/` 14 個測試檔皆為模組級單元測試。D1 描述的三構造點漏欄位屬於
**現有測試架構抓不到**的缺陷類型。是否要為此 intent 引入第一個 `TestClient` 測試，
屬於訪談決策（lead 已列為第 4 題），我在此只提供一個事實：`fastapi[standard]` 已含
`httpx`／`starlette.testclient`，`requirements.txt` 也已直接列 `httpx`，
**引入 `TestClient` 不需要新增任何依賴**。

---

### 八、給訪談的補充題（lead 的 8 題未涵蓋）

- **Q-dev-1**：角色清單的 5 份物化，是否同意在本輪順手做兩件低成本的事——
  (a) `AdminPage.tsx` 改用既有的 `GET /api/auth/roles`；(b) 加一個 5 行的
  Python 側一致性 unittest？兩者都零新依賴、零新工具，且直接命中 codekb 判定
  「投報率最高」的 C3 根因。
- **Q-dev-2**：`UserSchema` 的三個構造點是否要在本輪收斂成單一 `_serialize_user()` helper？
  不收斂的話，本 intent 的新欄位會有 2/3 機率在 PUT 回應中靜默為 null（D1）。
- **Q-dev-3**：`## Code Style` 是否採用「依落點分流」的分層寫法（第二節），
  而不是宣告式的「應有 service 層」？

## Positions

- AGREE: 「Backend 完全沒有 linter／formatter／type checker」與「Frontend ESLint 已實質影響程式碼結構形狀而非僅風格」——我以 `find` 掃遍 repo 確認無 `pyproject.toml`／`ruff.toml`／`.flake8`／`mypy.ini`／`.prettierrc`，並實跑 `npx eslint .` 得到 `0 errors, 3 warnings`，草稿這兩項如實記載了落差而未美化，判斷正確。
- AGREE: 把「零 TODO／FIXME／HACK／XXX」列為應保護的既有紀律——這是少數可被 grep 直接驗證的規則，寫進 `team.md` 有實際執行力，不是裝飾。
- AGREE: `discovered-rules.md` 本輪不捏造新的 `ALWAYS`／`NEVER`，並明列檢視範圍與判定理由——把技術債觀察（T4）與人類明述的硬約束分開，符合 stage 對 discovered-rules 的定義。
- OBJECT: 草稿的 `## Code Style` **完全沒有命名慣例段落**，而 `org.md` 的 `## Code Style` 明文以「Naming conventions」為其中一項——本輪實測到四項可追認的一致慣例（`*_router.py`、`wa_*`、`*Page.tsx`、`PascalCase.tsx`）與三項已知不一致（非元件 TS 檔名 kebab/camel 混用、logger 命名 `cloud360.*` 與 `__name__` 混用 11:5、`HTTPException` 具名與位置引數同檔混用 12:17），全數缺席（詳見第六節）。
- OBJECT: 草稿把 ESLint 的結構約束縮小為 `react-refresh` 與 `set-state-in-effect` 兩條——實測 `eslint-plugin-react-hooks@7.1.1` 的 flat recommended 開了 16 條 error 級規則（含 `immutability`、`purity`、`static-components`、`preserve-manual-memoization`），只寫兩條會讓讀者誤判其餘可放行；且草稿未指出 CI 的 `npm run lint` **沒有** `--max-warnings 0`，導致「error 擋、warning 不擋」這個關鍵分界沒有被記錄。
- OBJECT: 草稿主張「模組級 docstring 慣例：18 支中 16 支已載明**職責／安全邊界／契約**」——codekb 原文是「**多數**明確載明」，草稿把限定詞升格為全稱。實測本 intent 主戰場 `user_router.py` 的 docstring 只有單行功能清單，無安全邊界、無契約段；照草稿的措辭追認，等於宣告一個現況未達標的規則。
- OBJECT: 草稿的 `evidence.md` 未複核 codekb 的兩處量化錯誤即引用——前端 `fetch()` 實為 52 處／10 檔（非 32 處／8 檔），角色清單副本實為 5 份以上且 codekb 把 `user_router.py:26` 的 `import CANONICAL_ROLES` 誤記為手寫副本、同時漏記真正的手寫副本 `auth.py:82-86 require_any_user`。`evidence.md` 開宗明義寫「所有主張皆有 codekb 或 repo 檔案路徑支撐」，但轉引 codekb 的結論而未回到 repo 核對，等同把上游誤差原樣傳遞到 `team.md`。
- OBJECT: 草稿（與 brief 的前提）認為本 intent 會「再加一處 `fetch()` 使用」——不成立。`AdminPage.tsx:41` 的 `fetchUserList` 已在打 `/api/auth/list`，本 intent 只擴充該端點的回應欄位，前端不新增呼叫點、不新增 `Authorization` 手寫處。以錯誤前提出的訪談題（T13 是否要在本輪處理）會誤導決策。
- OBJECT: 草稿列了 8 題訪談草案，卻**漏掉本 intent 唯一會產生使用者可見 bug 的實作事實**：`UserSchema` 在 `user_router.py` 有三個具名構造點（L451／L602／L705），後兩者已經在靜默漏傳 `requested_role`。新欄位若比照辦理，改角色後該列的時間欄會變空白且無任何工具報錯（e2e 未斷言表格內容）。這比草稿第 6 題（`schema_rbac.sql` 重跑安全性）更貼近本 intent 的實際失敗面。
