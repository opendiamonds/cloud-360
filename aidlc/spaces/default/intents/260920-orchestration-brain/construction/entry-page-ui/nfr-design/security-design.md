# 安全設計 — `U14 entry-page-ui`

> 撰寫時間 2026-10-17T04:06:39Z（`date -u` 取值）。本檔為本站的審查主檔。
>
> 把 `../nfr-requirements/security-requirements.md` 的 `EPN-11`–`EPN-19` 落成具體形狀，並處置 `../carried-review-items.md`
> 的五項使用者裁決（functional-design `R-01`／`R-02`／`R-03`、nfr-requirements `R-01`／`R-02`）與其餘 Minor。
> 15 項帶入項的逐一落點見 §十一。直接設定作業對象的處置依 `[EPD1]`=A 定案（2026-10-17T04:22:24Z 使用者作答）。
> 本站未執行任何程式；行號皆於撰寫當下實讀。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `../nfr-requirements/security-requirements.md` | `EPN-11`–`EPN-19`、§六（ADR-0006 四面向）、§八（帶入項對照） |
| `../carried-review-items.md` | 15 項帶入項與五項裁決原文 |
| `../functional-design/functional-spec.md` §二之一、§九之一 | C-8 的方法與呼叫點；上游 IAM 列 |
| `../functional-design/rules.md` | `BR91.1`／`BR91.2`、`BR92.5`、`BR93.4`、`BR97.2`、`BR97.5`、`BR97.6`、`BR98.4` |
| `../../project-pages-ui/nfr-design/security-design.md` §二 | `U23` 寫入路徑的注入先例（必填、無預設、keyword-only；ast 鎖） |
| repo 實測（後端） | `hierarchy_facade.py:107-108`（兩個訊息常數）、`:194-202`（`_authorize`）、`:238-262`（寫入守門順序與 `project_visible`）、`:366-379`（`list_projects`／`list_systems`）、`:381-405`（`resolve_work_target`）；`hierarchy_service.py:73-96`（三個擁有者檢查）、`:291-323`（`resolve_work_target`，`:318-322` 由圖推導上層）；`membership_facade.py:518-532`（`project_visibility`）；`membership_service.py:367-379`；`brain_gateway.py:564-577`（`_HierarchyResolver`）、`:1226-1243`（`_build_catalog`）、`:1290-1293`（唯一命中）、`:1297-1298`（查無對象的固定句）、`:1301-1324`（`_set_target_confirmed`）、`:1403-1426`（`_on_set_work_target`）、`:1569-1598`（`build_brain_gateway`）、`:130-155`（log 白名單）；`brain_gateway_rules.py:296-299`（`HierarchyNotFound` → 固定句 `target_not_found`）；`session_store.py:387`；`main.py:84`；`tests/test_brain_gateway_limits.py:379-383`；`tests/test_project_visibility_static.py:1-20`、`:112-160`（`S2`／`S3`）、`:162`（`S4`）；`tests/brain_gateway_fakes.py:234-268`、`:343-356`；`tests/test_hierarchy_service.py:191`、`:199`、`:212-216`；`tests/test_brain_gateway_startup.py:60`；`tests/helpers.py:103` |
| repo 實測（前端） | `AuthContext.tsx:56-61`（`logout`）、`:63-68`（`refreshMe`）、`:71-80`（初始化失敗即 `logout`）、`:82-93`（`login`）；`auth-context.ts:29`（`id?: number`）、`:39-53`（`AuthContextType`）；`App.tsx:24-34`（`DefaultRedirect`；`:28` `canArch` → `/workspace`）；`WorkspacePage.tsx:116-129`（`handleCanvasExit` 的內聯判定）；`AssessmentPage.tsx:139-158`（`diagramOverride`、`uploadedXml`、`optimizeDraft`）、`:1262-1270`；`LoginPage.tsx:102-107`（無「已登入即導走」）；`eslint.config.js:42-66`；`frontend/tests/e2e/member-pages.spec.ts:573` |

## 一、可見性的注入形狀（`EPN-11a`、`EPN-11b`；帶入項 nfr-requirements `R-03`）

### 一之一、注入物是 factory，不是閉包

`U13` 不得 import `services.membership_facade`、`services.membership_service` 與 `main`（`test_brain_gateway_limits.py:380-382`），
而 `_HierarchyResolver`（`brain_gateway.py:564-577`）與 `_build_catalog`（`:1226-1243`）每次呼叫都**自開** DB session。
`MembershipFacade.project_visibility` 回傳的閉包綁著建立它的 session（`membership_facade.py:525-533`），所以注入的必須是
「給一個 session、回傳一個有 `project_visibility` 方法的物件」的 factory——即 `MembershipFacade` 類別本身。

```python
# brain_gateway.py（簽章層，示意）
class BrainGateway:
    def __init__(self, *, store, routers, orchestrator,
                 membership_facade_factory: Callable[[Any], Any],   # 必填、無預設
                 ...): ...

def build_brain_gateway(app: Any, *, membership_facade_factory: Callable[[Any], Any]) -> BrainGateway: ...

# main.py:84（唯一的組裝點）
app.state.brain_gateway = build_brain_gateway(app, membership_facade_factory=membership_facade.MembershipFacade)
```

- **必填、無預設**：漏傳即 `TypeError`，啟動失敗（fail-closed）——比照 `U23` 寫入路徑。`BrainGateway` 若給預設值，預設值只能是
  「恆可見」或「恆不可見」之一，前者是靜默繞過、後者使大腦對所有人失效，兩者都不可接受。
- 參數名稱含 `membership` 不構成 import：`U13` 的原始碼只看到一個 `Callable`。

### 一之二、每個受守門的呼叫點就地產生閉包

`U13` 內呼叫受守門的 facade 方法時，一律寫成

```python
facade.describe_work_target(principal, project_visible=vis.project_visibility(principal), project_id=..., system_id=..., diagram_id=...)
# 其中 vis = self.membership_facade_factory(db)，db 與 facade 為同一個 session
```

使 `test_project_visibility_static.py` 的 `S3`（每個呼叫點的值必須是對屬性 `project_visibility` 的呼叫）原樣成立——不得先存成區域變數
再傳入（那會是 `ast.Name`，`S3` 紅）。`project_visibility(principal)` 本身不發 SQL（`membership_facade.py:525-533` 只建閉包），
每個呼叫點多建一個閉包的成本可忽略。

## 二、名稱查詢（`EPN-11`、`EPN-12`；帶入項 functional-design `R-01`，使用者裁決）

### 二之一、`describe_work_target` 的步驟順序

```python
# hierarchy_facade.py（示意）
def describe_work_target(self, principal, *, project_visible: Callable[[int], bool],
                         project_id=None, system_id=None, diagram_id=None) -> dict:
    self._authorize(principal, "view")                        # ① K2 view；失敗拋 HierarchyForbidden
    found = hierarchy_service.describe_work_target(           # ② 擁有者範圍逐層查，查不到或不屬請求者該層 None
        self._db, owner_user_id=principal.user_id,
        project_id=project_id, system_id=system_id, diagram_id=diagram_id)
    if found.owning_project_id is not None and not project_visible(found.owning_project_id):
        return dict(_NO_NAMES)                                # ③ 不可見 → 三名稱皆 None（含自己的圖名）
    return found.names
```

| 步驟 | 規則 |
|---|---|
| ① | 與同檔其他方法相同，第一行授權（`hierarchy_facade.py:194-202`）；`HierarchyForbidden` 不在本方法內捕捉，由 `_names_for` 處置 |
| ② | 服務層新增純查詢函式 `describe_work_target`，回傳 `names`（三鍵）與 `owning_project_id`；三層各至多一條 SQL（系統層以 join 取所屬專案的擁有者，`performance-design.md` §三之一）。**不拋** `HierarchyNotFound`——顯示名稱不得使推送失敗 |
| 「所屬專案」 | 依序取第一個非 null：`project_id` 參數；系統列的 `project_id`；只有圖時，圖所屬系統的 `project_id`（多一條主鍵查詢）。孤兒圖無所屬專案，③ 不執行，回圖名 |
| ③ | 判定對象是**所屬專案**，不是「請求者擁有的專案」——被移出的建立者在 ② 仍通過擁有者範圍，只有 ③ 能擋下他（`EPN-11` (b)） |

擁有者範圍照舊有效（上游 §二之一第 2 點），可見性是**再加一道**（交集），不是取代（`security-requirements.md` §〇）。

### 二之二、`_names_for` 的失敗處置（`EPN-12`）

不存在、不屬請求者、不可見、查詢失敗四種情形，推送給前端的 `work_target` 都是「該層（或三層）名稱為 null、照常推送、不另送 `error`」，
序列化後逐位元相同。`_names_for` 捕捉**全部**例外（含 `HierarchyForbidden`）→ 該組三名稱 null ＋ 一筆 `work_target_names_failed`
（`connId`、`exc`），不往外拋（`performance-design.md` §三之二）。被拒絕不另記 log（上游 §九）。

### 二之三、測試矩陣

新檔 `backend/tests/test_describe_work_target.py`（facade 層，真實 SQLite，由 `unittest discover` 撿到）＋ `test_brain_gateway_turn.py`／
`test_brain_gateway_handshake.py` 各新增案例（假 facade）。

| # | 身分（以 ORM 直接構造，`tech-stack-decisions.md` §五第 1 項的可達性） | 期望 | 層 |
|---|---|---|---|
| (a) | 擁有者且為成員 | 三名稱 | facade |
| (b) | **被移出的建立者**（`owner_user_id`＝他、無他的成員列、專案另有一位成員） | 三名稱皆 null，**含他自己的圖名** | facade |
| (b') | 同 (b)，經 `_names_for` 推送 | `work_target` 三名稱 null，與 (g) 的序列化逐位元相同 | gateway |
| (c) | 建立者、專案零成員列 | 三名稱（擁有者那一半生效） | facade |
| (d) | 非擁有者的成員 | 專案、系統名 null（擁有者範圍不成立，`OPEN-EP14-9` 現況）；若圖為他自己的 → 圖名 | facade |
| (e) | 自有孤兒圖 | 只有 `diagramName` | facade |
| (f) | `K2 view` 撤銷 | `HierarchyForbidden`；經 `_names_for` → 三名稱 null ＋ 一筆 WARNING | facade ＋ gateway |
| (g) | 不存在的專案 id | 專案名 null | facade |
| (h) | 漏傳 `project_visible` | `TypeError` | facade |

雙向：(b) 與 (a)／(c) 為同一專案在兩種成員狀態下的對照，突變「拿掉 ③」只紅 (b)、(b')，證明測試不是恆真。

## 三、對象目錄與唯一命中（帶入項 nfr-requirements `R-01`，使用者裁決）

### 三之一、守門落點：`U7` 的 `list_projects`／`list_systems`

實查兩者在應用程式碼中**唯一**的呼叫端是 `_build_catalog`（`brain_gateway.py:1230`、`:1235`、`:1239`；另兩處在 `test_hierarchy_service.py:191`、`:199`）。
本站把可見性做成這兩個方法的必填參數，而不是在 `U13` 內自行過濾：

| 方法 | 新簽章 | 行為 |
|---|---|---|
| `list_projects` | `(principal, *, project_visible)` | ① 授權；② 擁有者範圍列舉（不變）；③ 只保留 `project_visible(p.id)` 為真者 |
| `list_systems` | `(principal, *, project_id, project_visible)` | ① 授權；② 擁有者檢查（不變）；③ `project_visible(project_id)` 為假 → `HierarchyNotFound(PROJECT_NOT_FOUND_DETAIL)`（與不屬請求者同一句，`hierarchy_facade.py:107`）；④ 列舉 |

理由：放在 facade 才能進 `S2`／`S3` 的機械鎖並 fail-closed；放在 `U13` 則下一個呼叫 `list_projects` 的人不會知道要過濾。
`_build_catalog` 依 §一之二 的形狀在三個呼叫點各傳 `project_visible=vis.project_visibility(principal)`。

**後果鏈**（逐條對照裁決的三個點名對象）：

1. 目錄：被移出建立者的前專案不在 `projects`，其系統不在 `systems`。
2. 反問標籤：`rules.target_label`（`brain_gateway_rules.py:475-479`）只從目錄取名，目錄沒有就不會出現在 `clarify` 候選。
3. 唯一命中：`match_referent` 在目錄裡找不到 → 走 `not_found_message`（`brain_gateway.py:1297-1298`），與「說出一個不存在的專案名」**同一句**，不洩漏存在性。
4. `selected_project_id`（session 中已存的專案，`:1236-1240`）若不可見：`any(pid == selected ...)` 以過濾後的目錄比對，不會進該分支。

### 三之二、測試

`test_brain_gateway_turn.py` 新增（假 facade ＋ 假可見性，見 `logical-components.md` §一之一）：被移出的建立者說出前專案名稱 →
回 `not_found_message`、0 則 `clarify`、0 次 `set_work_target`；對照：可見的同名專案 → 唯一命中並設定。`test_hierarchy_service.py`
新增：`list_projects` 對 (b) 身分不含該專案、對 (c) 身分含；`list_systems` 對 (b) 拋 `HierarchyNotFound`。

## 四、直接設定作業對象（`[EPD1]`=A）

裁決「也不能經大腦指定該專案／系統」逐字涵蓋第三條路：頁面送出的 `set_work_target`（`brain_gateway.py:1403-1426`）→
`SessionStore.set_work_target`（`session_store.py:387`）→ `_HierarchyResolver` → `HierarchyFacade.resolve_work_target`，目前只檢查擁有者。

**定案設計（`[EPD1]`=A）**：`resolve_work_target` 加必填 `project_visible`，在服務層解析之後判定：

```python
resolved = hierarchy_service.resolve_work_target(self._db, owner_user_id=principal.user_id, ...)   # 不變
pid = resolved["projectId"]
if pid is None or project_visible(pid):
    return resolved
if project_id is not None or system_id is not None:          # 明確指定 → 視同查不到
    raise HierarchyNotFound(PROJECT_NOT_FOUND_DETAIL if project_id is not None else SYSTEM_NOT_FOUND_DETAIL)
return {"projectId": None, "systemId": None, "diagramId": resolved["diagramId"]}   # 由自己的圖推導 → 只留圖
```

- 前端收到的錯誤由 `rules.error_for` 依例外**型別**轉成固定句 `target_not_found`（`brain_gateway_rules.py:298-299`），與今天指定別人的專案逐字相同。
- `_HierarchyResolver.__init__` 多收 `membership_facade_factory`，`resolve_work_target` 以 §一之二 的形狀傳入。
- 唯一命中（§三）呼叫 `_set_target_confirmed` 時，目錄已過濾，故不會觸發上面的拒絕分支。
- 測試：被移出者 ① 明確送前專案 id → `error` 一則、作業對象不變；② 送自己掛在前專案下的圖 → 作業對象為 `{null, null, 圖}`、
  無 `error`；③ 一般擁有者送同形狀 → 三層照常解析（雙向）。
- 移出**之前**已設好的作業對象不被追溯清除，列為 §十 殘留 2（`[EPD1]`=A 選項本文已揭露）。

## 五、靜態鎖（`EPN-11a`）

既有鎖**一條都不放寬**：`test_brain_gateway_limits.py:380-382` 的禁止清單、`S1`、`S4`（`project_visibility` 只定義在 `MembershipFacade`）、`S5` 不改。擴充：

| 鎖 | 擴充 |
|---|---|
| `S2`（keyword-only、無預設） | 檢查的方法集合由 `WRITE_METHODS` 擴為 `WRITE_METHODS ∪ GUARDED_READS`，`GUARDED_READS = {"describe_work_target", "list_projects", "list_systems", "resolve_work_target"}`（`resolve_work_target` 依 `[EPD1]`=A 納入） |
| `S3`（呼叫點注入 `project_visibility(...)`） | 同一集合；以 `node.func.attr` 判定（`ast.Attribute`），不以字串 grep——`intent_routing.py:155` 的 `_describe_work_target` 是 `ast.Name` 呼叫且名稱不同，不會誤中（`EPN-25`）。讀取方法的呼叫點下限 `checked ≥ 5`（`_names_for` 1、`_build_catalog` 3、`_HierarchyResolver` 1） |
| `S3` 的例外清單（新增，`R-03` 要求同步註明） | 只有一筆：`services/session_store.py` 對 `resolve_work_target` 的呼叫（`:387`）。理由：接收者是 `SessionStore` 建構時注入的 hierarchy 轉接器（`_HierarchyResolver`），由轉接器負責注入；`session_store.py` 依其模組 docstring 刻意不 import facade 與 DB 型別。例外以 `(檔案, 方法名)` 精確比對，不以目錄或前綴放行 |

`describe_work_target` 新增檔案一律放在 `services/hierarchy_facade.py` 與 `hierarchy_service.py`，不新增任何 import 成員關係符號的模組（`S4`／既有 grep 鎖維持綠燈）。

## 六、前端

### 六之一、對話清除綁登入／登出事件（`EPN-15`、`EPN-15a`；帶入項 functional-design `R-03`，使用者裁決）

| 位置 | 改動 |
|---|---|
| `auth-context.ts` `AuthContextType` | 新增 `subscribeAuthBoundary: (listener: () => void) => () => void` |
| `AuthContext.tsx` | 以 `useRef<Set<() => void>>` 保存訂閱者；`subscribeAuthBoundary` 為 `useCallback([])`（身分穩定）；新增內部 `notifyAuthBoundary()`，在 **`logout()` 與 `login()` 的第一行**同步呼叫（早於任何 `setUser`／`setToken`）。初始化失敗（`:78`）、`checkAuthSession` 失敗（`:98`、`:106`）都經 `logout()`，自然涵蓋。`refreshMe()` 與 `applyUser()` **不**通知（同一使用者的權限更新不清紀錄） |
| `BrainTranscriptContext.tsx` | `BrainTranscriptProvider` 內 `useEffect(() => subscribeAuthBoundary(() => dispatch({ type: 'reset' })), [subscribeAuthBoundary])`——setState 在訂閱回呼內，不在 effect body（`react-hooks/set-state-in-effect` 允許的形狀）；回傳值即退訂 |
| `App.tsx` 樹 | `AuthProvider` → `BrainTranscriptProvider` → `BrowserRouter`，**不帶 `key`**；`BrainTranscriptKeyed` 刪除（`frontend-components.md` §二的形狀由本節取代） |

- **不依賴 `User.id`**：清除訊號是事件，與 `user` 的任何欄位無關；`/me` 失敗使 `user.id` 缺值（`AuthContext.tsx:86`、`:90-92`）不影響。
- **不重掛路由樹**：沒有任何 `key` 在 `BrowserRouter` 之上，登入時的 `navigate`（`LoginPage.tsx:107`）不與重掛競賽。
- **訂閱時序**：React 先執行子元件的 effect，`BrainTranscriptProvider` 的訂閱早於 `AuthProvider` 自己的初始化 effect（`:71-80`），初始化失敗呼叫 `logout()` 時已有訂閱者。
- **測試**：e2e 兩案——(1) `EPN-15`：A 登入時以 `page.route('**/api/auth/me')` 回 500（user 無 id）→ 對話 → 經 Sidebar 登出 → B 經登入頁登入 →
  入口頁與兩子頁面的對話區皆空；(2) `EPN-15a`：A 登入並對話 → 以 `history.pushState` ＋ `popstate` 在**不重新載入**的情況下到 `/login`
  （`page.goto` 會重新載入、使記憶體自然清空，測不到本條）→ B 登入 → 對話區為空。不重掛的檢查改為靜態：`App.tsx` 與 `BrainTranscriptContext.tsx`
  內 `grep -c "key="` 為 0（取代上游「render 計數」的形狀待定項）。

### 六之二、4403 的落點（帶入項 nfr-requirements `R-05`；偏離 `BR92.5` 字面，揭露）

`BR92.5` 逐字「4403 → Navigate 到 `/`（`K1` 已被撤銷，由 `BR91.2` 重新決定落點）」。照字面實作有兩個正確性問題：

1. **子頁面無限迴圈**：`K1` 被撤銷而 `A1` 仍在時，`/` 經 `DefaultRedirect`（`App.tsx:28`）導回 `/workspace`，其大腦掛點再連、再 4403、再導 `/`。4403 在限流**之前**決定（`brain_gateway.py:738-741` 先於 `:743`），迴圈不會被握手限流擋住。
2. **權限快取陳舊**：`AuthContext` 只在登入與初始化打 `/me`，導到 `/` 時 `can('K1')` 仍為真 → 入口頁掛載 → 又被 4403 關閉。
3. 附帶：子頁面導航會丟掉未儲存的畫布，與 functional-design `R-02` 裁決的意圖相反。

**本站設計**（唯一正確解，不出成題目，問題檔 §一第 3 項）：

| 時點 | 行為 |
|---|---|
| 任何頁收到 4403 | `terminal = 'forbidden'`、不排退避（`EPN-03`）；每個頁面實例至多一次呼叫既有 `refreshMe()`（失敗吞下）。**不呼叫 `navigate`** |
| 入口頁 | `refreshMe()` 更新權限後 `DefaultRedirect` 重新渲染：`K1` 已失效 → 依既有瀑布導走（`BR91.2` 的意圖由此達成）；仍為真（伺服器與 `/me` 不一致）→ 停在入口頁，`brain-connection-notice` 顯示「你目前沒有使用大腦的權限」，無按鈕、不重連 |
| 子頁面 | 大腦掛點（脈絡列、同步提示、「問大腦」面板）只在 `can('K1','view')` 時掛載——補上 `BR91.2` 對子頁面未明寫的一格（違反行為正是其 `violation_behaviour`「無 `K1` 者……每次被 4403 關閉」）。`refreshMe()` 後 `K1` 失效 → 掛點卸載，頁面本身照常可用；仍為真 → 脈絡列進 `unavailable` 並顯示同一句 |

測試：e2e（`routeWebSocket` 以 4403 關閉 ＋ `page.route('/api/auth/me')` 控制回應）三案——入口頁 ＋ `/me` 無 `K1` → 落到 `/workspace` 且該頁大腦 WS 連線數 0；
`/workspace` ＋ `/me` 無 `K1` → pathname 不變、面板消失、畫布內容不變；`/workspace` ＋ `/me` 仍有 `K1` → 提示出現、快轉 20 秒新連線 0。

### 六之三、未儲存內容保護（`EPN-18`；帶入項 functional-design `R-02`（裁決）、nfr-requirements `R-06`）

**判定式只有一份**：新檔 `frontend/src/utils/unsavedWork.ts`（純函式、無 React 依賴，camelCase 檔名依 `team.md`）

| 函式 | 定義 | 使用者 |
|---|---|---|
| `isCanvasDirty(saveStatus: DiagramSaveStatus, xml: string): boolean` | `saveStatus === 'unsaved' \|\| saveStatus === 'saving' \|\| (saveStatus === 'no-file' && !!xml.trim())`——由 `WorkspacePage.tsx:118-121` **原樣抽出** | `handleCanvasExit`（改為呼叫它，行為不變）、`useWorkspaceTargetSync` |
| `hasUnsavedAssessmentWork(uploadedXml: string \| null, optimizeDraft: unknown): boolean` | `uploadedXml !== null \|\| optimizeDraft !== null`（理由見問題檔 §一第 7 項） | `useAssessmentTargetSync` |

**首次對齊 (2) 的前置條件**（`BR97.5` (2) 加條件，設計檔不回改）：目標圖自有、不等於目前開啟的圖、且**頁面無未儲存內容** → 自動開；
有未儲存內容 → **不開**（決定 `hold`），旗標照樣消耗、**不回寫**目前的圖（否則會用使用者沒選的圖覆蓋他在入口頁選的對象，同 `R-08`）；
`brain-sync-notice` 顯示「作業對象是「<名稱>」；目前畫布有未儲存的變更，沒有自動開啟」＋「開啟這張圖」。按下時若仍有未儲存內容，
先以既有形狀 `window.confirm('有未儲存的變更，確定要開啟另一張圖？')` 確認（同 `WorkspacePage.tsx:123`），再呼叫頁面既有開圖函式。
判定在決定當下讀取：`onmessage` 路徑讀同步掛點以 effect 更新的 ref；`onPageReady` 路徑用頁面傳入的值（`performance-design.md` §四）。

**e2e 與突變**：

| 案 | 構造 | 期望 | 必須紅燈的突變 |
|---|---|---|---|
| `/workspace` 晚到 | `routeWebSocket` 先拒握手 → 使用者在畫布新增一個圖形（`saveStatus` 變 `unsaved`）→ 接受握手並送首筆相符 `work_target`（目標為另一張自有圖） | 畫布 XML 不變、提示出現；按「開啟這張圖」並確認後才換圖 | 拿掉未儲存條件 → 畫布被取代 |
| `/workspace` 乾淨 | 同上但不編輯 | 自動開啟 | （對照組） |
| `/assessment` 晚到（`R-06` 第 (2) 點） | 先拒握手 → 上傳一個 `.drawio` 檔（`uploadedXml` 非 null）→ 送首筆相符 `work_target` | 「已上傳：<檔名>」仍在、`diagramOverride` 未變、提示出現 | 拿掉 `hasUnsavedAssessmentWork` → 上傳內容被清掉 |

### 六之四、回寫、回聲與 bootstrap（`EPN-17`、`EPN-17a`；帶入項 functional-design `R-05`、`R-06` 後半、`R-08`）

| 項 | 設計 |
|---|---|
| `EPN-17` | `DefaultRedirect` 的 `K1` 判斷在 `isPending` 之後（`BR91.1`），e2e 雙向沿用上游 |
| `EPN-17a` | 回寫前以本頁圖清單的 `is_owner` 判定；`listOk` 為假時兩個方向都不同步（`performance-design.md` §五） |
| 回聲（`R-05`） | 同步掛點以 ref 保存 `pendingEchoes: string[]`（本頁已送出、尚未收到回聲的 diagramId，上限 8，超出丟最舊）；收到 `work_target` 時若 diagramId 在其中 → 移除一筆、不提示；否則若等於目前開啟的圖 → 不提示；其餘提示。每次 `ready` 清空（斷線前送出的回聲可能永遠不到）。e2e：一個往返內連選 X、Y，X 的回聲到達時不出現「作業對象已改為 X」 |
| bootstrap 不回寫（`R-08`） | 同步掛點記錄目前開啟的圖的來源 `openedBy ∈ {'bootstrap','user','url','brain'}`（頁面在 bootstrap、下拉、網址參數處各標一次；首次對齊開的圖標 `brain`）。首次對齊 (3)：作業對象**有任何非 null 層級且 diagramId 為 null**、而目前的圖來源為 `bootstrap` → **不回寫**；之後使用者主動開圖才依 `BR97.6` ① 回寫。e2e：入口頁選定系統 S（diagramId null）→ 進 `/workspace`（bootstrap 開上次的圖）→ 作業對象仍為 S |
| 空字串名稱（`R-06` 後半） | `BR97.2` 補一格：名稱為 `""` 時顯示「（未命名）」，與 null 的「（無法顯示名稱）」區分；提示文字的 `<名稱>` 同規則 |

### 六之五、儲存、log 與 token（`EPN-13`、`EPN-14`、`EPN-16`）

設計沿用上游，不另立形狀：紀錄 store 只在 React state；新程式不出現 `localStorage`／`sessionStorage`／`indexedDB`／`caches.`（grep 為 0）；
`console.*` 只帶 `type`、`code`、關閉碼、turnId；後端只新增 `work_target_names_failed`（`connId`、`exc`），`_ALLOWED` 集合不變；
子協定由 `WsSubprotocol` 取值、網址不帶查詢字串。**一處需說明**：§六之二 的 `refreshMe()` 會經既有 `applyUser` 以**相同值**重寫
`sessionStorage` 的 token（`AuthContext.tsx:51`）——那是既有程式的行為，鍵集合與值皆不變，`EPN-13` 的 e2e 斷言（鍵集合前後相同、值不含測試原句）不受影響。

### 六之六、樁訊框（`EPN-19`；帶入項 functional-design `R-04`）

- `frontend/src/brain/testing/wsFrames.ts` 的建構器**只收原始型別引數**（如 `workTargetFrame(segment: string, projectId: string | null, ..., diagramName: string | null): WsEnvelope`）；
  函式內先 `const payload: components['schemas']['WorkTargetPayload'] = { ... }` 再放進 envelope，使欄位漂移在 `tsc -b` 紅燈（`WsEnvelope.payload`
  是無判別的聯集，直接放物件字面量可能被聯集中別的成員收下——`R-04` 第 (2) 點）。
- lint 機械化（`R-04` 第 (3) 點），`eslint.config.js` 新增一個 `files: ['tests/**/*.ts']` 區塊。兩個實查決定了選擇器的形狀：
  1. 只看 `type` 鍵會誤擋既有 `member-pages.spec.ts:573` 的 `{ loc, msg, type: 'enum' }`，故選擇器要求**同一個物件同時有 `type` 與 `payload` 鍵**：
     `ObjectExpression:has(> Property[key.name='type']):has(> Property[key.name='payload'])`，另一條以 `key.value` 涵蓋字串鍵寫法
     （`esquery` 1.7.0 支援 `:has(> …)`，`node_modules/esquery/package.json:3`）。
  2. flat config 對同一條規則**以後者取代前者**：新區塊若只列新選擇器，tests 目錄會失去 `:42-66` 的三條子協定規則。故把那三條抽成
     檔內常數 `WS_SUBPROTOCOL_RESTRICTIONS`，兩個區塊都展開它——規則只有一份。
- 突變：spec 內手寫 `{ type: 'work_target', payload: {...} }` → lint 紅；契約欄位改名重產型別 → `npm run build` 紅（`BR98.4`）。

## 七、突變清單（code-generation 逐一執行，結果記入 code-summary 與 `automation-test-plan.md`，`EPN-26`）

| # | 突變 | 必須紅的測試 |
|---|---|---|
| M1 | `describe_work_target` 拿掉 ③ | §二之三 (b)、(b') |
| M2 | `is_project_visible` 拿掉外層 `project_id` 條件（`membership_service.py:370-373` 的既有 `M6` 形狀） | (b)（「另一專案的成員」被當成可見） |
| M3 | `describe_work_target` 的 `project_visible` 改為 `=None` 並在 None 時略過 | (h) 與擴充後的 `S2` |
| M4 | `_build_catalog` 某呼叫點改傳 `lambda _: True` | 擴充後的 `S3` |
| M5 | `list_projects` 拿掉 ③ | §三之二 的被移出者說出前專案名稱案 |
| M6 | `brain_gateway.py` 加 `from services.membership_facade import MembershipFacade` | `test_brain_gateway_limits.py` 既有禁止清單 |
| M7 | 不可見時改回 `error(UNAUTHORIZED)` | (b') 的逐位元比對 |
| M8（`[EPD1]`=A） | `resolve_work_target` 拿掉可見性判定 | §四 測試 ①② |
| M9 | 紀錄 Provider 改回以 `user?.id ?? "anon"` 為 key、拿掉訂閱 | §六之一 (1) |
| M10 | 只在 `logout()` 通知、`login()` 不通知 | §六之一 (2) |
| M11 | 子頁面 4403 改為 `navigate('/')` | §六之二 第二案（pathname 改變、畫布遺失） |
| M12 | 拿掉未儲存條件（兩頁各一） | §六之三 兩個晚到案 |
| M13 | 拿掉 `is_owner` 條件 | `EPN-17a` |
| M14 | 回聲改回只比對最近一次送出值 | §六之四 連選 X、Y 案 |
| M15 | 移除 `openedBy === 'bootstrap'` 條件 | §六之四 bootstrap 案 |

## 八、ADR-0006 四面向（逐格對照上游 `security-requirements.md` §六）

| 面向 | 上游判定 | 本站判定 | 差異與理由 |
|---|---|---|---|
| **IAM** | 適用（擴充） | **適用（擴充）** | 上游只涵蓋名稱查詢；本站依 nfr-requirements `R-01` 裁決擴及目錄、反問與唯一命中（§三），並依 `[EPD1]`=A 擴及直接設定（§四）；前端補「無 `K1` 不掛子頁面大腦掛點」（§六之二）。判定方向與上游相同，範圍更大，來源為裁決 |
| **Encryption** | 適用（相同） | **適用（相同）** | 無新落點；`refreshMe()` 對 token 的重寫為既有行為、值不變（§六之五） |
| **Network exposure** | 適用（相同） | **適用（相同）** | 不新增端點、路由或對外連線；4403 不再造成重連或導航迴圈（§六之二），抖動與握手預算見 `performance-design.md` §一之三 |
| **Audit logging** | 適用（相同） | **適用（相同）** | 不新增稽核事件；只新增一筆白名單內的 WARNING；被拒絕的查詢不記（上游 §九） |

## 九、PBT hard constraint

**不適用**，與上游 `security-requirements.md` §七一致：`describe_work_target`、`list_*` 的守門與 `_names_for` 皆非 IaC generator、cost calculator、agent routing；
§二之三 以窮舉身分驗證，前端純函式（`decideInitialAlignment`、紀錄 reducer、`unsavedWork.ts`）無 unit 框架（`team.md` D 項不採），由 e2e 以例子驗證。

## 十、殘留（如實記載，供核可關卡知情接受）

| # | 殘留 | 理由 |
|---|---|---|
| 1 | 名稱陳舊（`OPEN-EP14-16`）：移出之後到下一次推送之前，**已在畫面上**的名稱不會消失 | 名稱只在推送時查；換頁、重新整理或對象變更即更新 |
| 2 | 移出**之前**已設好的作業對象不被追溯清除，交辦仍帶前專案，直到改選或工作階段閒置 24 小時（每次互動續期，`redis_gateway.py:102-103`） | 追溯清除需在每次載入 session 時重判可見性，屬 `U8`／`U13` 的 load 路徑，超出裁決點名的三個對象；名稱已為 null（§二） |
| 3 | 「成員看得到專案、大腦目錄看不到」（`U23` 已知限制第 ③ 項中「成員」那一半、`OPEN-EP14-9`） | 裁決明言不在本次範圍 |
| 4 | 目錄路徑語句數由 2 ＋ 3N 增為 2 ＋ 5N（`performance-design.md` §三之三） | 判定只有一份的代價 |
| 5 | `U12` 的 `list_diagrams_of_system`（作業對象只到系統時換成目標圖集合）仍只做擁有者範圍 | 該路徑以已存的作業對象為輸入，與殘留 2 同源；不在裁決點名範圍 |
| 6 | 持續 1011 時同一使用者第 4 個以後的分頁會有部分握手被拒（`performance-design.md` §一之三） | 被拒不累積、60 秒後照常放棄 |

## 十一、帶入項 15 項的逐一落點

| 帶入項 | 落點 | code-generation 要做的 |
|---|---|---|
| functional-design **R-01**（裁決） | §一、§二、§五；`logical-components.md` §一之一 | `describe_work_target` 三步、`_names_for`、`S2`／`S3` 擴充、§二之三 九案 |
| functional-design **R-02**（裁決） | §六之三；`performance-design.md` §四 | `unsavedWork.ts`、兩頁 `hold` 路徑、三個 e2e |
| functional-design **R-03**（裁決） | §六之一 | `subscribeAuthBoundary`、移除 `BrainTranscriptKeyed`、兩個 e2e、`key=` 靜態檢查 |
| functional-design R-04 | §六之六 | 建構器只收原始型別、lint 區塊與共用常數 |
| functional-design R-05 | §六之四 回聲 | `pendingEchoes` 與連選 e2e |
| functional-design R-06 | `performance-design.md` §五（清單成功旗標）；§六之四（空字串名稱） | `fetchDiagrams` 回傳 `{ ok, list }`；「（未命名）」 |
| functional-design R-07 | `logical-components.md` §五（合併前檢查，沿用上游 `NFR5.141`） | 合併前於分支執行三條檢查 |
| functional-design R-08 | §六之四 bootstrap | `openedBy` 與 e2e |
| nfr-requirements **R-01**（裁決） | §三；`[EPD1]`=A（§四） | `list_projects`／`list_systems` 加參數、目錄三呼叫點、被移出者雙向測試 |
| nfr-requirements **R-02**（裁決） | `performance-design.md` §三之一 | 計數測試上界 5／15 |
| nfr-requirements R-03 | §一、§五 | factory 注入、`main.py` 組裝、`S3` 例外清單一筆 |
| nfr-requirements R-04 | `performance-design.md` §一之一 | code review 三項檢查；vite dev 手動案交 `tcms-test-cases` |
| nfr-requirements R-05 | §六之二；`performance-design.md` §一之四 | 4403 不導航、`refreshMe()`、`K1` 掛載條件、三個 e2e |
| nfr-requirements R-06 | §六之三 | 抽出 `isCanvasDirty`；`/assessment` 晚到 e2e 與突變 |
| nfr-requirements R-07 | `performance-design.md` §一之三 | 不改範圍；code-summary 記「支援 3 個分頁完整重試」 |

## 十二、送審前自檢（七項；全部產出寫完後實算，數字由 grep／jq 取得，未執行任何測試）

見 `logical-components.md` §六（四份產出 ＋ 問題檔共用一張表，避免兩處各寫一份而漂移）。
