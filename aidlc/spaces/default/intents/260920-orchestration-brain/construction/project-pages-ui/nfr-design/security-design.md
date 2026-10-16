# 安全設計 — `U23 project-pages-ui`

> 撰寫時間 2026-10-15T23:26:04Z（`date -u` 取值）。本檔為本站的審查標的（`review_artifact: security-design`）。
>
> 承接 `../nfr-requirements/security-requirements.md` 的 `PPN-11`–`PPN-18`，並把 `../carried-review-items.md` 的兩項使用者裁決
> （functional-design `R-01`：三條寫入路徑套用 `[PP3]`=A 判準；nfr-requirements `R-01`：不含 id 的固定訊息）與其餘 Minor
> 落成**具體設計**——code-generation 照本檔做即可，不需再做設計選擇。§九 為 11 項帶入項的逐一落點表。
> 本站未執行任何程式或測試；行號皆於撰寫當下以 `sed -n`／`grep -n` 實讀。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `../nfr-requirements/security-requirements.md` | `PPN-11`–`PPN-18`；§三之二 的四案、`PPN-14a` 的可達性；§五 的稽核處置；§六 的 ADR-0006 表 |
| `../carried-review-items.md` | functional-design `R-01`（使用者裁決）、`R-03`；nfr-requirements `R-01`（使用者裁決）、`R-03`、`R-04`、`R-06` |
| `../functional-design/rules.md` | `BR87.1`–`BR87.7`（列舉端點的放寬、K2 先行、呼叫方向、ast 鎖） |
| `inception/contract-design/contract-summary.md` | `K-16`（per-project 授權判定的唯一來源） |
| repo 實測 | `backend/services/hierarchy_service.py:70`／`:77`／`:89`／`:180`／`:199`／`:381`／`:388`（七處 `HierarchyNotFound` f-string，其中六處含專案或系統 id）、`:192`／`:214`（既有的刪除 INFO log）；`hierarchy_facade.py:47`（logger）、`:78`（`HierarchyNotFound` 定義處）、`:169`（`_authorize`）、`:213`／`:224`／`:234`（三個寫入方法）；`hierarchy_router.py:129-143`（`_translate`）、`:243`／`:267`／`:287`（三個寫入呼叫點）；`membership_facade.py:113-136`（`_assert_project_exists`）；`requirement_field_facade.py:251-256`（`U20` 把 `HierarchyNotFound` 改包成自己的例外） |

## 一、固定訊息（帶入項 nfr-requirements `R-01`，使用者裁決；`PPN-13`）

### 一之一、兩個常數，定義在例外旁邊

```text
# hierarchy_facade.py，緊接 class HierarchyNotFound（:78）之後
PROJECT_NOT_FOUND_DETAIL = "查不到專案"
SYSTEM_NOT_FOUND_DETAIL = "查不到系統"
```

放在 `hierarchy_facade.py` 而非 `hierarchy_service.py`：例外型別定義在這裡，`hierarchy_service` 已從本檔取得例外
（`hierarchy_facade.py` 檔頭說明兩者的匯入順序），`membership_facade` 也已從本檔匯入（`membership_facade.py:55`）——
**不新增任何匯入方向**。

**改寫範圍**：`hierarchy_service.py` 中帶 id 的六處專案／系統 f-string（`:70`、`:77`、`:180`、`:199`、`:381`、`:388`）一律改用
常數。`:89`（「查不到架構圖 {diagram_id}」）**不改**：架構圖不在本單元的五條路徑內。

| 被改到的回應面 | 影響 |
|---|---|
| `U7` 的建立系統、刪除專案、刪除系統、變更紀錄查詢等經 `assert_*_owned_by` 的 404 | `detail` 由「查不到專案 12」變為「查不到專案」——狀態碼不變 |
| `U20` 需求欄位端點（經 `get_project_of_system`） | **無**：`requirement_field_facade.py:255-256` 把 `HierarchyNotFound` 改包成 `RequirementFieldNotFound`，訊息不外漏 |
| 既有測試 | 對兩句訊息的斷言：`grep -rn "查不到專案\|查不到系統" backend/tests frontend/src` 實查 **0** 處，無測試需改 |

**刻意不改**：`membership_facade.py:132`／`:134`／`:136` 與 `membership_service.py:194`／`:431` 的「查不到專案 {id}」——那是
`U19`／`U24` 成員頁自己的路徑，不在使用者裁決的「各守門路徑」內。記為殘留（§八 第 4 項）。

### 一之二、逐路徑的例外型別與訊息範本

所有 404 由 `hierarchy_router._translate`（`:129-143`）以 `str(exc)` 轉成 `detail`，故「同一個例外型別 ＋ 同一個常數」即保證
`response.content` 逐位元相同。

| 路徑 | 分支 | 例外 | `detail` | 狀態 |
|---|---|---|---|---|
| `GET /projects/{pid}/systems` | 缺 `K2 view` | `HierarchyForbidden`（既有訊息） | 既有 | 403 |
| 〃 | 專案不存在 | `MembershipNotFound(PROJECT_NOT_FOUND_DETAIL)` | 查不到專案 | 404 |
| 〃 | 存在但不可見 | `MembershipNotFound(PROJECT_NOT_FOUND_DETAIL)` | 查不到專案 | 404 |
| `POST /projects/{pid}/systems` | 缺 `K2 edit` | `HierarchyForbidden` | 既有 | 403 |
| 〃 | 不存在**或**不可見（守門判定為假） | `HierarchyNotFound(PROJECT_NOT_FOUND_DETAIL)` | 查不到專案 | 404 |
| 〃 | 可見但非擁有者（成員） | `HierarchyNotFound(PROJECT_NOT_FOUND_DETAIL)`（既有 `:70`，改常數後） | 查不到專案 | 404 |
| `DELETE /projects/{pid}` | 缺 `K2 edit` | `HierarchyForbidden` | 既有 | 403 |
| 〃 | 不存在或不可見 | `HierarchyNotFound(PROJECT_NOT_FOUND_DETAIL)` | 查不到專案 | 404 |
| 〃 | 可見但非擁有者 | 同上（`:70`） | 查不到專案 | 404 |
| 〃 | 擁有者、預設專案或底下仍有系統 | `HierarchyConflictError`（既有，帶剩餘數） | 既有 | 409 |
| `DELETE /systems/{sid}` | 缺 `K2 edit` | `HierarchyForbidden` | 既有 | 403 |
| 〃 | 系統不存在 | `HierarchyNotFound(SYSTEM_NOT_FOUND_DETAIL)`（`get_project_of_system`，`:388` 改常數後） | 查不到系統 | 404 |
| 〃 | 系統存在、所屬專案不可見 | `HierarchyNotFound(SYSTEM_NOT_FOUND_DETAIL)`——**系統句，不是專案句** | 查不到系統 | 404 |
| 〃 | 可見但非擁有者（成員） | `HierarchyNotFound(PROJECT_NOT_FOUND_DETAIL)`（既有 `assert_system_owned_by` → `:70`） | 查不到專案 | 404 |

**`DELETE /systems/{sid}` 最後一列為何允許是專案句**：走到該分支的請求者已通過守門，即**是該專案的成員**，本來就能在畫面上
看到這個系統；回應句不同不構成存在性預言機。改成系統句需另包一層例外轉換，收益為零，故沿用既有。

### 一之三、測法（`PPN-13`、`PPN-14c`）

因訊息不再含 id，「不存在」與「不可見」可用**不同 id** 直接比較：對從未存在的 id（取 `max(id)+1000`）打一次、對請求者不可見的
既有 id 打一次，斷言 `status_code` 相等**且** `response.content` 逐位元相等（比 `response.json()` 更嚴：連序列化細節都相同）。
五條路徑各一案（系統清單、建立系統、刪除專案、刪除系統的「系統不存在 vs 專案不可見」）。

| 必須紅的突變 | 哪一案紅 |
|---|---|
| 某一處改回 `f"查不到專案 {project_id}"` | 該路徑的比較案 |
| 刪除系統的守門改拋 `PROJECT_NOT_FOUND_DETAIL` | 刪除系統的比較案（不存在為系統句、不可見為專案句） |
| 系統清單的「不可見」改拋 `MembershipForbidden`（403） | 系統清單的比較案 |

## 二、三條寫入路徑的可見性守門（帶入項 functional-design `R-01`，使用者裁決；nfr-requirements `R-03`、`R-04`；`PPN-14`–`PPN-14c`）

### 二之一、注入形狀：必填、無預設、keyword-only

上游 `PPN-14a` 給的非強制形狀，本站**定為強制**，並把 `R-03` 的兩個選項都做（必填無預設 ＋ ast 鎖）：

```text
# hierarchy_facade.py（簽章層）
def create_system(self, principal, *, project_id: int, name: str,
                  project_visible: Callable[[int], bool]) -> System
def delete_project(self, principal, *, project_id: int,
                   project_visible: Callable[[int], bool]) -> None
def delete_system(self, principal, *, system_id: int,
                  project_visible: Callable[[int], bool]) -> None
# membership_facade.py
def project_visibility(self, principal) -> Callable[[int], bool]
    # 回傳 lambda pid: membership_service.is_project_visible(db, project_id=pid, user_id=principal.user_id)
```

**為什麼必填無預設**：漏傳時 Python 在呼叫當下拋 `TypeError`——**fail-closed**，不依賴任何測試；若給 `None` 預設並在方法內
「為 `None` 就略過守門」，任何未來的呼叫端漏傳即靜默繞過，而那正是 `R-03` 點名的風險。`HierarchyFacade` 只知道一個
`Callable[[int], bool]`，**不 import 任何 membership 符號**（`BR87.3`、`PPN-14b`）。

**代價（如實揭露）**：既有測試中直接呼叫這三個 facade 方法的共 **15** 處需補參數（`test_hierarchy_service.py` 11 處、
`test_work_orchestrator_store.py` 2 處、`test_requirement_field_facade.py` 1 處、`test_mcp_bridge_e2e.py` 1 處；以
`grep -n "\.create_system(\|\.delete_project(\|\.delete_system("` 逐檔實數，已排除 `test_hierarchy_service.py:77` 那一處
對 `hierarchy_service.create_system` 的 service 層呼叫）。這些測試驗的是擁有者檢查等其他行為，補上的參數一律為
`tests/helpers.py` 新增的 `ALWAYS_VISIBLE = lambda _pid: True`，語意與修改前完全相同。**非測試程式的呼叫端只有
`hierarchy_router.py` 三處**（`:243`、`:267`、`:287`；`grep` 全 `backend/` 非 `tests/` 實查）。

### 二之二、每個方法內的順序（`PPN-14a`、`R-04`：守門早於 409）

| 步 | `create_system` | `delete_project` | `delete_system` |
|---|---|---|---|
| 1 | `_authorize(principal, "edit")`（403） | 同左 | 同左 |
| 2 | — | — | `project_id = get_project_of_system(system_id)`；不存在 → 404 系統句 |
| 3 | `project_visible(project_id)` 為假 → 404 專案句 | 同左 | 為假 → **404 系統句** |
| 4 | `assert_project_owned_by`（既有，404 專案句） | 同左 | `assert_system_owned_by`（既有，404 專案句） |
| 5 | `hierarchy_service.create_system` | `hierarchy_service.delete_project`（**409 在此**：預設專案、仍有系統） | `hierarchy_service.delete_system`（409：預設系統、仍有架構圖） |

`K2 edit` 判定只在第 1 步、只有一份（`BR87.3`）；守門在第 3 步，**同時早於擁有者檢查與一切 409**，故被移出的擁有者對
「底下仍有系統」的專案只能得到 404，無法以 409 的剩餘系統數探測內容（`R-04`）。步驟 2 的 `get_project_of_system` 在
facade 內直呼 service 層（不再經 `self.get_project_of_system`，避免第二次 `K2 view` 判定；`K2 edit` 已涵蓋讀取）。

**守門判定為什麼在擁有者檢查之前而非之後**：兩者都回 404，順序不影響外部結果；放在前面是讓「守門擋下」的語意不依賴擁有者
檢查的存在——日後若有人放寬擁有者檢查（例如 `OPEN-PP23-6` 第 ② 項的「非擁有者管理者可建立系統」），守門仍在。

### 二之三、測試矩陣（`PPN-14`–`PPN-14c`；帶入項 functional-design `R-03` 見 §三）

新檔 `backend/tests/test_project_write_guard.py`，`TestClient(app)` ＋ `dependency_overrides`（`team.md` B 規則）。

**構造「被移出的擁有者」**：以 facade 建專案（`U19` 的組合路徑會寫入建立者的成員列）→ 以 ORM 為第二位使用者寫一筆
`project_admin` 成員列 → 以 ORM 刪除建立者的成員列。結果：`owner_user_id` 仍是建立者、該專案有成員列而建立者不在其中——
與真實的「另一位管理者把他移出」同一資料狀態（`functional-spec.md` §四之二：只有擁有者被移出能產生此狀態）。

| 案 | 請求者（角色皆具 `K2 edit`，如 `Project_Editor`，除 (f)） | 三條路徑的期待 |
|---|---|---|
| (a) | 擁有者且為成員 | 201／204 |
| (b) | **被移出的擁有者** | 404，且 `projects`、`systems`、`project_members`、`system_requirement_fields` 四表列數前後相等 |
| (c) | 零成員列專案的擁有者 | 201／204 |
| (d) | 成員但非擁有者 | 404（既有擁有者檢查） |
| (e) | 被移出的擁有者，對**底下仍有系統**的專案刪除 | **404，不是 409**（`R-04`） |
| (f) | `Developer`（`K2` view 有、edit 無）的非成員 | **403，不是 404**（`PPN-14a`） |
| (g) | 不存在的 id vs (b) 的同一請求者 | `response.content` 逐位元相等（§一之三） |

### 二之四、靜態鎖（擴充 `BR87.7` 的 `test_project_visibility_static.py`）

除了 `BR87.7` 原有的「兩個 unscoped 方法只被 `MembershipFacade` 呼叫」，同一支測試加三條 `ast` 斷言：

1. `HierarchyFacade` 的三個寫入方法的 `FunctionDef` 中，`project_visible` 為 keyword-only 且 `kw_defaults` 對應項為 `None`
   （即**無預設值**）。
2. `backend/` 內（排除 `tests/`）對屬性名 `create_system`／`delete_project`／`delete_system` 的每一個呼叫，若接收者不是
   `hierarchy_service` 模組名，必須帶 `project_visible=` 關鍵字，且其值是一個對屬性 `project_visibility` 的呼叫——
   **不得是 `Lambda`、`Name` 或 `Constant`**（擋住 router 傳 `lambda _: True`）。
3. `project_visibility` 的定義只出現在 `MembershipFacade` 類別內。

### 二之五、突變清單（code-generation 逐一執行並記入 code-summary 與 `automation-test-plan.md`）

| 代號 | 突變 | 必須紅的案 |
|---|---|---|
| `G1` | 拿掉第 3 步守門 | (b)：回 201／204 且列數改變 |
| `G2` | 把守門移到 `_authorize` 之前（或在 router／`MembershipFacade` 先判可見性） | (f)：得 404 |
| `G3` | 把守門移到 service 呼叫之後（等同在 409 之後） | (e)：得 409 |
| `G4` | 給 `project_visible` 預設 `None` 並在為 `None` 時略過 | 靜態鎖第 1 條 |
| `G5` | router 改傳 `lambda _pid: True` | 靜態鎖第 2 條 |
| `G6` | `delete_system` 的守門拋專案句 | (g) 的刪除系統案 |
| `G7` | `hierarchy_service` 內另寫一份成員查詢供守門使用 | `PPN-14b` 的 grep（§四）非 0 |

## 三、兩支列舉端點的身分矩陣（`PPN-11`、`PPN-12`；帶入項 functional-design `R-03`）

新檔 `backend/tests/test_project_visibility_endpoints.py`（`BR87.5` 的落點）。五身分 × 兩端點 ＋ 缺 `K2`：

| 身分 | 構造 | 專案清單 | 系統清單（對目標專案） |
|---|---|---|---|
| ① 擁有者且有成員列 | facade 建立 | 含目標 | 200 |
| ② 成員 | ORM 加成員列 | 含目標 | 200 |
| ③ **另一專案的成員**（`R-03`） | 該使用者是**另一個**專案的成員、不是目標專案的成員 | **不含**目標 | 404 |
| ④ 被移出的擁有者 | §二之三 的構造 | 不含目標 | 404 |
| ⑤ 零成員列專案的擁有者 | ORM 建專案不寫成員列 | 含目標 | 200 |
| 缺 `K2` | 非 canonical role | 403 | 403（對存在與不存在的 id 皆是） |

③ 的構造使「可見性子句漏寫 `project_id` 條件（有任何成員列即可見）」這個缺陷變紅——若 ③ 只是「完全沒有成員列的使用者」，
該缺陷下他仍看不到，測試會綠。

| 代號 | 突變 | 必須紅的案 |
|---|---|---|
| `M1`–`M4` | `BR87.5` 原列（不重述） | 同 `BR87.5` |
| `M5`（`R-03`） | 拿掉 `list_projects_by_ids` 或 `list_systems_unscoped` 第一行的 `K2` 判定 | 缺 `K2` 案；**另構造可見集合為空的缺 `K2` 使用者**，專案清單須仍為 403 而非 200 `[]` |
| `M6` | 可見性子句的成員那一半漏寫與外層專案的關聯（`is_project_visible` 退化為「該使用者有任何成員列」） | ③ 的系統清單得 200 |

## 四、可見性謂詞只有一份（`PPN-12`、`PPN-14b`）

唯一定義為 `membership_service._visible_project_ids_select(user_id)`（查詢形狀見 `performance-design.md` §二之一）；
`visible_project_ids` 與 `is_project_visible` 都由它組出；`MembershipFacade.project_visibility` 與 `list_visible_*` 都只呼叫這兩支。

| 可判定檢查 | 期待值 |
|---|---|
| `grep -n "import.*membership" backend/services/hierarchy_facade.py backend/services/hierarchy_service.py` | 0（撰寫時實查為 0） |
| `grep -c "NOT EXISTS\|project_members\|ProjectMember" backend/services/hierarchy_facade.py backend/services/hierarchy_service.py` | 皆 0（上游 `PPN-14b` 的 grep 加上 ORM 類別名，以免以 ORM 寫法繞過字串比對） |
| `grep -c "def _visible_project_ids_select" backend/services/membership_service.py` | 1 |
| `grep -rn "owner_user_id" backend/services/membership_service.py` 的新增命中 | 只在 `_visible_project_ids_select` 內（逐筆判讀寫進 code-summary；既有的 `project_ids_owned_by` 不計） |

## 五、Audit logging（帶入項 nfr-requirements `R-06`；`[PPD1]`=A）

### 五之一、上游敘述的一處更正（事實，非新決定）

上游 §五 寫「刪除不記稽核」。實讀：`hierarchy_service.py:192` 有 `logger.info("刪除專案 %s", project_id)`、`:214` 有
`logger.info("刪除系統 %s", system_id)`——**成功的刪除已有一行 INFO log，含 id 與時間戳，但不含是誰刪的**；不存在任何稽核表
紀錄。所以真正缺的是「誰」與「連帶刪掉了什麼」，不是「有沒有刪」。

### 五之二、連帶刪除的殘留（`R-06` 要求如實列出）

| 成功的動作 | 連帶永久消失 | 現有痕跡 |
|---|---|---|
| 擁有者刪除專案 | 該專案**全部**成員列（含其他管理者）——`project_members.project_id` 為 `ON DELETE CASCADE`（`schema_rbac.sql:596`） | 一行 INFO：專案 id、時間 |
| 擁有者刪除系統 | 該系統的全部需求欄位值（含其他成員所填）——`system_requirement_fields.system_id` 為 `ON DELETE CASCADE` | 一行 INFO：系統 id、時間 |

守門（§二）使**被移出者**不再能觸發這兩條；**仍是成員的擁有者**觸發它們是 `U7` 的既有合法行為，本單元不改。

### 五之三、`[PPD1]`=A 的設計（定案）

- **定案**：`HierarchyFacade.delete_project`／`delete_system` 在 service 呼叫**成功返回後**各記一行
  `logger.info("刪除專案 project_id=%s actor_user_id=%s", …)`（系統同形），使用既有但未使用的 logger（`hierarchy_facade.py:47`）。
  只記 id，不記專案名、系統名（後端 log 不公開，但沿用 `PPN-18` 的最小化精神）。**不記連帶筆數**：計數需讀
  `project_members` 與 `system_requirement_fields`，那會讓 hierarchy 側碰 membership 與需求欄位的資料，違反 §四 的
  grep 檢查與 `BR87.3` 的方向。檢查：`TestClient` 成功刪除一案，`assertLogs("cloud360.hierarchy_facade", "INFO")` 含
  `actor_user_id=<請求者 id>`；突變「拿掉該行」→ 紅。
- 拒絕不記 log（上游 §五 已定、本站不重開）。

## 六、前端（`PPN-16`–`PPN-18`）

沿用上游的三條可判定檢查，不新增設計：`owner_user_id` 只出現在 `[+ 建立系統]` 的渲染條件（`BR82.4`）；本單元新增前端檔對
`localStorage`／`sessionStorage`／`indexedDB` 的 grep 為 0；`console.` 只允許固定字串。`fanoutQueue.ts`（`performance-design.md`
§一）**不得**有任何 `console.` 呼叫——取消屬正常流程，不是錯誤。

## 七、ADR-0006 四面向（逐格對照上游 `security-requirements.md` §六）

| 面向 | 上游判定 | 本站判定 | 差異與理由 |
|---|---|---|---|
| **IAM** | 適用（擴充） | **適用（擴充）**——相同 | 本站把上游的判準落成設計：§一（固定訊息）、§二（注入守門、順序、靜態鎖）、§三（身分矩陣與 ③ 構造）。判定不變 |
| **Encryption** | 相同（落點 `U21`） | **相同** | 零新傳輸、零新儲存；新索引不含新資料；佇列不落地 |
| **Network exposure** | 相同（落點 `U21`） | **相同** | 零新端點、零新埠；五條路徑皆在既有 `/api/hierarchy/` 下、需驗證身分。固定訊息使 id 枚舉只得到同一句 404 |
| **Audit logging** | 相同（沿用既有） | **適用（擴充）**——依 `[PPD1]`=A，成功刪除加記刪除者 `actor_user_id`（§五之三） | 判定與上游不同的理由：範圍變了（使用者作答新增一行帶 actor 的 log），不是重判。另：上游「刪除不記稽核」的字面需更正為「有 INFO log、無 actor」（§五之一）；`R-06` 要求的連帶刪除殘留已列於 §五之二 |

## 八、殘留（如實記載，供核可關卡知情接受）

1. **守門與寫入之間未加鎖**（上游 §三之二 殘留，不變）。
2. **連帶刪除無筆數紀錄**（§五之二）；`[PPD1]`=A 只補上「誰」。
3. **`OPEN-PP23-6` 第 ③ 項**（大腦對象目錄仍為擁有者範圍）照舊。
4. **成員頁的 404 訊息仍含 id**（`membership_facade.py:132-136`、`membership_service.py:194`／`:431`）——`U19`／`U24` 的路徑，
   不在裁決範圍；其「不存在 vs 不可見」是否可區分由那兩個單元自己的規則管。
5. **`DELETE /systems/{sid}` 對成員非擁有者回專案句**（§一之二 末段），已論證不構成預言機。

## 九、帶入項 11 項的逐一落點

| 帶入項 | 落點 | 狀態 |
|---|---|---|
| functional-design `R-01`（Major，使用者裁決） | 本檔 §二（三條路徑守門、順序、矩陣、突變 `G1`–`G7`）、§五之二（級聯重新揭露）；`logical-components.md` §一 | 已設計 |
| functional-design `R-02`（`BR86.2` 空態與標示文字） | `logical-components.md` §一之二 的 `RecentChanges` 列（逐字文案） | 已設計 |
| functional-design `R-03`（③ 構造與 `M5`） | 本檔 §三（③、`M5`、另加 `M6`） | 已設計 |
| functional-design `R-04`（佇列優先序、重讀是否進佇列） | `performance-design.md` §一之一 | 已設計 |
| functional-design `R-05`（`functional-spec.md` §十之一 空表） | **留 code-generation**：設計檔不回改（`team.md ## Corrections`），只在 code-summary 記明「該空表為格式缺陷，以散文後的單一表格為準」 | 留下游（理由：無設計內容） |
| nfr-requirements `R-01`（Major，使用者裁決） | 本檔 §一（常數、改寫範圍、逐路徑表、測法） | 已設計 |
| nfr-requirements `R-02`（Major，使用者裁決） | `logical-components.md` §三（DDL、ORM、遷移腳本、DEPLOY.md 逐項） | 已設計 |
| nfr-requirements `R-03`（參數必填、`delete_system` 順序） | 本檔 §二之一、§二之二、§二之四 | 已設計 |
| nfr-requirements `R-04`（守門早於 409） | 本檔 §二之二、§二之三 (e)、突變 `G3` | 已設計 |
| nfr-requirements `R-05`（上限 4 的說服力） | `performance-design.md` §三 | 已設計 |
| nfr-requirements `R-06`（成功級聯刪除無稽核） | 本檔 §五（更正、殘留表、`[PPD1]`=A 的 actor log） | 已設計 |

## 十、送審前自檢（八項；全部產出寫完後實算，數字由 grep／jq 取得，未執行任何測試或 Python）

| # | 自檢 | 結果 |
|---|---|---|
| 1 | **可達性** | (b)／(e)／④ 的「被移出的擁有者」以 ORM 三步構造（§二之三），與真實移出同一資料狀態；(f) 的 `Developer` 為 `K2` view 有、edit 無（上游以 `rbac_seed_data.py:327-337` 實數 7 個角色）；③ 需「另一專案的成員」，以 ORM 加一筆即可；`M5` 的「可見集合為空的缺 `K2` 使用者」即非 canonical role 的新使用者。**本站查出一處上游未寫的順序陷阱**：若 `delete_system` 沿用既有 `assert_system_owned_by` 來載入系統（它同時做擁有者檢查），守門只能排在它之後；此時「非成員、非擁有者」對既有系統會先被擁有者檢查以**專案句**擋下，而不存在的系統回**系統句**——兩者可區分，`PPN-14c` 必紅，且構成存在性預言機。已以 §二之二 第 2 步（先只以 `get_project_of_system` 取 `project_id`、不做擁有者檢查，守門在第 3 步）排除 |
| 2 | **契約端點三問**（全站四份 ＋ 問題檔） | `project_visible` 參數：產生＝`MembershipFacade.project_visibility`；傳遞＝`hierarchy_router` 三處；呼叫＝三個寫入方法第 3 步；清＝無（請求內閉包）。兩個訊息常數：寫＝`hierarchy_facade.py`；讀＝`hierarchy_service` 六處、`MembershipFacade.list_visible_systems`；清＝無。`_visible_project_ids_select`：唯一呼叫者為 `visible_project_ids`、`is_project_visible`。`ALWAYS_VISIBLE`：定義＝`tests/helpers.py`；使用＝15 處既有測試；靜態鎖第 2 條禁止非測試程式使用。佇列：寫＝兩頁 effect 入列；讀＝佇列；清＝cleanup `cancel()`。索引：見 `logical-components.md` §三。語句計數監聽器：`tearDown` 卸除。出現在少於兩份產出的方法逐一判定：`get_project_of_system` 只在本檔與 `logical-components.md`，為既有方法，非孤兒 |
| 3 | **引用逐字核對（事實與定位分開驗）** | 以 `sed -n`／`grep -n` 逐一印出：`hierarchy_service.py:70/77/89/180/199/381/388`（七處 f-string，`:89` 為架構圖）、`:192/:214`（刪除 INFO）、`hierarchy_facade.py:47/78/169/213/224/234`、`hierarchy_router.py:129`（`_translate` 起）／`:143`（`raise exc`）、`:243/:267/:287`、`membership_facade.py:55/113/132/134/136`、`requirement_field_facade.py:251-256`、`schema_rbac.sql:353/594/596`、`database.py:37`、`run_meta_schema_migration.py:155-170`／`:584`、`DEPLOY.md:660/:674/:867`、`backfill_project_members.py:18-21`、`test_membership_data.py:74-80/:139`。**查出上游三處定位偏差**：`_translate` 實為 `:129-143`（上游寫 `:129-139` 與 `:129-136`）；刪除 INFO 在 `:192`／`:214`；`DEPLOY.md:674` 的「7 個索引」與腳本實際 `EXPECTED_INDEXES` 的 **8** 筆不符（既存漂移，見 `logical-components.md` §三） |
| 4 | **檔案集合一致性** | 對照同為 `ui` 的 `member-pages-ui/nfr-design/`（不計 `reviews/`）：問題檔、performance、security、logical-components、traceability **五份相同**。對照 `mcp-bridge`（`service`）多 scalability／reliability／observability：本單元為 `ui`，`produces_kinds` 不含；與本單元 nfr-requirements `tech-stack-decisions.md` §三 的判定一致（未產出 scalability／reliability／observability requirements，故本站無承接對象） |
| 5 | **跨檔傳播（按事實）** | ①「並行上限 4」：performance §一之一 常數、§三；traceability `PPN-01`——值一致。②「固定訊息兩句」：文字只在本檔 §一之一 定義一次；logical §一之一 以常數名引用、traceability `PPN-13` 以「兩個無 id 常數」描述——無第二份字面。③「既有測試 15 處補參數」：本檔 §二之一、logical §一之一 與 §四、問題檔 §一 第 1 項——數字一致。④「索引數 8 → 9（`DEPLOY.md` 的 7 為既存漂移）」：logical §三 #5／#7、traceability `PPN-07`、問題檔 §一 第 7 項——一致。⑤「`[PPD1]`=A 定案」：本檔 §五之三、§七、§九；logical §一之一 的 log 列；traceability `PPN-18` 與帶入項 `R-06` 的 note——作答後皆定稿為 A，殘留暫定字樣以 grep 掃為 0 |
| 6 | **可算的數字先算再寫** | 測試呼叫點：`grep -c` 逐檔 11＋2＋1＋1＝**15**（`test_hierarchy_service.py` 的 12 次命中減去 `:77` 的 service 呼叫）；非測試呼叫點 **3**；`EXPECTED_INDEXES` 以 `awk 'NR>=155&&NR<=171' \| grep -c '^    ("'` 實數 **8**，加 1 為 **9**；六處改寫 f-string（七處減 `:89`）；`traceability.json` 的 `upstream_ids`＝**27**（`jq length`），與 nfr-requirements 的 `coverage` 4 個繼承子條 ＋ `reverse` 23 條相等 |
| 7 | **ADR-0006 四面向 ＋ PBT** | §七 逐格對照上游：IAM、Encryption、Network exposure 三格**相同**；Audit logging **擴充**（`[PPD1]`=A），並更正上游一處事實敘述。PBT：不適用（非三個 hard-constraint 落點；可見性兩分支以五身分 ＋ 七案 example-based 窮舉），與上游 §七 一致 |
| 8 | **帶入項 11 項落點** | §九：10 項已設計、1 項（functional-design `R-05`）留 code-generation 並附理由；`R-06` 依 `[PPD1]`=A 定案 |
