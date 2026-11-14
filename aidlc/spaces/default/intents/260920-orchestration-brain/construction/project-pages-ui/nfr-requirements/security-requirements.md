# Security Requirements — `U23 project-pages-ui`

> 撰寫時間 2026-10-15T22:52:51Z（`date -u` 取值）。識別字規則同 `performance-requirements.md` 前言。
> 本站兼任 devsecops／compliance／quality 的視角；以下每一條都附「可二元判定的檢查」與「必須紅燈的突變」。

## 〇、上游依據

| 來源 | 內容 |
|---|---|
| `functional-design/rules.md` | `BR87.1`–`BR87.7`（兩支列舉端點的放寬、K2 先行、呼叫方向、雙向測試、ast 靜態鎖）、`BR84.7`（`K4 edit` 唯讀呈現）、`BR82.4`（建立系統只對擁有者渲染） |
| `functional-design/functional-spec.md` §九之一 | ADR-0006 四面向的本單元判定（本站逐格對照，見 §六） |
| `carried-review-items.md` | **R-01 使用者裁決**（2026-10-15T22:46:22Z）：`U7` 的建立系統、刪除專案、刪除系統三條寫入路徑套用 `[PP3]`=A 的同一判準；`OPEN-PP23-10` 於本單元關閉 |
| `inception/requirements-analysis/requirements.md` | `NFR1`–`NFR11`；`:610-622` 修訂 1 的 ADR-0006 補充判定（`:622` 逐字「四面向皆適用，無不適用項」） |
| `inception/contract-design/contract-summary.md` | `K-16`（per-project 授權判定的唯一來源）、`K-19`（本單元為 `U17` 的 axe 掃描標的） |

**一處與已核可設計檔的字面衝突（如實記載，設計檔不回改）**：`rules.md` 的 `BR87.6` 與 `functional-spec.md` 的
`OPEN-PP23-10` 寫「被移出的建立者在 API 層仍能建立系統、刪除專案與系統……本單元不改」。該句已被使用者 2026-10-15T22:46:22Z
的 R-01 裁決取代（`carried-review-items.md` 第一條逐字：「`functional-spec.md` 的 `OPEN-PP23-10`『無自然承接站』一句以本裁決為準
（設計檔不回改）」）。本站以裁決為準，寫成 `PPN-14`；`BR87.6` 的其餘內容（`HierarchyFacade` 既有 `list_projects`／`list_systems`
不變、變更紀錄仍只回自己的圖、大腦對象目錄仍為擁有者範圍）**照舊有效**。

**第二處字面取代**：`[PP3]` 選項 A 原文的「零 schema 變更」（`functional-design-questions.md:172`）由 `[PPN1]`=A（2026-10-15T22:59:34Z）
取代——本單元新增索引 `ix_project_members_user_id`，**觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步**（`performance-requirements.md`
的 `PPN-07`、`tech-stack-decisions.md` 的 `PPN-25`）。索引不含新資料，不影響本檔 §六 的 Encryption 判定。

## 一、資料分類

| 資料 | 分類 | 出現處 | 處置 |
|---|---|---|---|
| 專案名、系統名 | 業務資料（內部） | 端點 1–4 回應、畫面 | 只經授權後回傳；不寫 console、不寫瀏覽器儲存 |
| 需求欄位值（SLA、TPS、預算等架構假設） | 業務資料（內部） | 端點 5／6、需求籤草稿 | 草稿只在元件 state；伺服器為唯一正本 |
| `owner_user_id`、成員 `user_id` | 內部識別字 | 端點 1 回應（`ProjectOut.owner_user_id`，`hierarchy_router.py:76`） | 回應模型不變（`BR87.4`）；前端不以它做授權判定 |
| JWT | 憑證 | `Authorization` 標頭 | 沿用既有 `fetch` 形狀（`team.md` Code Style）；本單元不新增任何憑證處理 |

## 二、IAM：兩支列舉端點（`[PP1]`＋`[PP3]`）

| ID | 要求 | 二元檢查 | 必須紅燈的突變 |
|---|---|---|---|
| **`PPN-11`** | 缺 `K2 view` 者對兩支端點一律 **403**，與專案是否存在、是否可見無關（`BR87.2` ①） | `TestClient`：非 canonical role → 專案清單 403；系統清單對**存在**與**不存在**的 `project_id` 皆 403；既有 `tests/test_hierarchy_service.py:130-141`（T2b）維持綠燈 | 系統清單改經 `MembershipFacade._assert_project_exists`（`BR87.5` 的 M4）→ 缺 K2 案得 404 → 紅 |
| **`PPN-12`** | 可見性謂詞只有一份（`membership_service` 的私有子句），兩支端點的五種身分結果如 `BR87.5` 所列 | `TestClient` 五身分 × 兩支端點：① 擁有者且有成員列、② 成員、③ **另一專案的成員**（帶入項 R-03：構造須是別的專案的成員，使漏寫 `project_id` 條件時變紅）、④ 被移出的擁有者、⑤ 零成員列專案的擁有者 | `BR87.5` 的 M1–M3，另加 **M5**（帶入項 R-03）：拿掉 `list_projects_by_ids` 或 `list_systems_unscoped` 第一行的 K2 判定 → 缺 K2 案（含可見集合為空時）→ 紅 |
| **`PPN-13`** | **「不存在」與「不可見」不可區分**：系統清單與 §三 的三條寫入路徑，兩者回應的狀態碼**與 `detail` 字串**完全相同 | `TestClient`：對不存在的 id 與對非成員可見的既有 id 各打一次，斷言 `status_code` 與 `response.json()` 逐位元相等 | 讓「不可見」走一個帶專案 id 或不同訊息的例外 → `detail` 不等 → 紅 |
| **`PPN-15`** | 兩個不做擁有者檢查的 `HierarchyFacade` 方法只能被 `MembershipFacade` 呼叫（`BR87.7`） | `backend/tests/test_project_visibility_static.py` 以 `ast` 掃描 `backend/`（排除 `tests/`），呼叫位置集合恰為 `MembershipFacade` 類別內 | 在 `hierarchy_router.py` 直接呼叫 `list_systems_unscoped` → 紅 |

**突變紀錄的落點**：每一道突變的「改了什麼、哪一案紅、還原後複綠」寫進 code-generation 的 code-summary 與 tcms-test-cases 的
`automation-test-plan.md`（`project.md` 的 tcms 規則必做 3）。

## 三、IAM：`U7` 三條寫入路徑的可見性守門（R-01 使用者裁決）

### 三之一、為什麼這是授權面的真缺口（不只是「看不到的東西還能動」）

`hierarchy_facade.py:213-240` 的 `create_system`、`delete_project`、`delete_system` 只做 `_authorize(principal, "edit")` 與
擁有者檢查；**沒有任何程式路徑會改寫 `owner_user_id`**（`functional-spec.md` §四之二），所以被共同管理者移出的建立者仍通過
擁有者檢查。級聯（審查 R-01 實測）：刪專案時 `project_members.project_id` 為 `ON DELETE CASCADE`（`schema_rbac.sql:596`），
**整個專案的成員列一併消失**，含仍在的管理者；刪系統時 `system_requirement_fields` 隨之消失，**其他成員填的需求欄位資料
永久遺失**。被移出者在畫面上看不到入口，但 API 可直接呼叫。

### 三之二、要求

| ID | 要求 | 二元檢查 | 必須紅燈的突變 |
|---|---|---|---|
| **`PPN-14`** | 三條寫入路徑在既有擁有者檢查之外，加一道可見性守門：**該專案已有任何成員列時，請求者必須是該專案的成員**，否則 **404**（與「不存在」同一結果，`PPN-13`）；**零成員列**時維持只認擁有者 | `TestClient` 每條路徑至少四案，四案的請求者皆持**具 `K2 edit` 的角色**（如 `Project_Editor`，`rbac_seed_data.py:329`；否則會在 `PPN-14a` 的 403 先停下而測不到守門）：(a) 擁有者且為成員 → 201／204；(b) **被移出的擁有者**（另有管理者將其移出）→ 404，且**資料未變**：`projects`、`systems`、`project_members`、`system_requirement_fields` 的列數在請求前後相等；(c) 零成員列專案的擁有者 → 201／204；(d) 成員但非擁有者 → 404（既有擁有者檢查，維持不變） | 拿掉守門 → (b) 回 201／204 且列數改變 → 紅 |
| **`PPN-14a`** | **`K2 edit` 判定先於可見性守門**：缺 `K2 edit` 者不論可見與否一律 **403**，與修改前相同 | `TestClient`：`Developer`（`K2` view＝True、edit＝False，`rbac_seed_data.py:328`）以**非成員**身分對既有專案呼叫三條路徑 → 403（不是 404） | 守門放在 `_authorize(principal, "edit")` 之前（例如在 `MembershipFacade` 先判可見性再呼叫 `HierarchyFacade`）→ 該案得 404 → 紅 |
| **`PPN-14b`** | 守門使用的謂詞**就是** `PPN-12` 那一份（經 `membership_service.is_project_visible`），不在 hierarchy 側另寫；`HierarchyFacade` **仍不 import 任何 membership 符號**（`BR87.3`）；`K2` 判定仍只在 `HierarchyFacade` 內一份 | `grep -n "import.*membership" backend/services/hierarchy_facade.py backend/services/hierarchy_service.py` 為 0（`hierarchy_router.py:54-55` 已 import membership，屬 router、不受限）；`grep -c "NOT EXISTS\|project_members" backend/services/hierarchy_facade.py backend/services/hierarchy_service.py` 皆為 0（謂詞未被複製；撰寫時實測皆為 0。`hierarchy_migration.py` 的 2 處命中是遷移腳本既有內容，不在檢查範圍）；`PPN-15` 的 ast 鎖維持綠 | 在 `hierarchy_service` 內另寫一份成員查詢 → grep 非 0 → 紅（靜態檢查，寫進 code-summary） |
| **`PPN-14c`** | 刪除系統的守門以**該系統所屬專案**判定；系統不存在 → 404，與不可見同結果 | `TestClient`：不存在的 `system_id` 與被移出擁有者對既有系統，兩者 `status_code` 與 `detail` 相等 | 守門只在 `project_id` 路徑生效、漏掉 `delete_system` → (b) 案紅 |

**`PPN-14a` 為何會被違反（可達性）**：七個 canonical role 有 `K2 view` 而無 `K2 edit`（`rbac_seed_data.py:327-337` 中 edit 欄為
False 者：`Developer`、`FinOps_Analyst`、`SRE`、`Ops_Lead`、`Platform_Engineer`、`Security_Reviewer`、`Platform_Owner`）。
`BR87.3` 規定呼叫方向是 router → `MembershipFacade` → `HierarchyFacade`；**最直覺的實作**（在 `MembershipFacade` 先判可見性、
再呼叫 `HierarchyFacade` 的寫入方法）會讓這七個角色的非成員從 403 變成 404，靜默改變既有行為。滿足四條約束（`K2` 先行且只有
一份、謂詞只有一份、`HierarchyFacade` 不 import membership）的一個形狀是：`HierarchyFacade` 的三個寫入方法接受一個由呼叫端
注入的可見性判定（`Callable[[int], bool]`），在 `_authorize` 之後、擁有者檢查之前呼叫；router 經 `MembershipFacade` 取得該判定。
**此形狀非強制**，code-generation 可另選，但必須通過 `PPN-14`–`PPN-14c` 全部檢查。

**殘留（如實記載）**：守門的判定與寫入在同一個請求、同一個 DB session 內，但**未加鎖**：管理者移出建立者的交易若恰在守門判定之後、
寫入之前提交，該次寫入仍會成功。視窗與既有擁有者檢查相同（`U7` 的擁有者檢查同樣未鎖），本站不加鎖——要關掉這個視窗須對
`project_members` 取列鎖，那會讓一次刪除與並行的成員異動互相阻塞，而觸發條件是「管理者與被移出者在同一秒內動作」。

## 四、前端

| ID | 要求 | 二元檢查 |
|---|---|---|
| **`PPN-16`** | 前端的 `K2`／`K4 view`／`K4 edit` 可見性**只是呈現**；伺服器照樣判定。前端**不得**以 `owner_user_id` 或任何回應欄位自行推斷「可見」 | 本單元新增的前端檔中，`owner_user_id` 只出現在 `[+ 建立系統]` 的渲染條件（`BR82.4`），grep 逐筆判讀寫進 code-summary；伺服器側由 `PPN-11`–`PPN-14` 的 `TestClient` 覆蓋 |
| **`PPN-17`** | 需求欄位草稿、`fieldsBySystem`、專案與系統清單**不寫瀏覽器儲存** | 本單元新增的前端檔對 `localStorage`、`sessionStorage`、`indexedDB` 的 grep 為 0 |
| **`PPN-18`** | `console.*` 不得輸出專案名、系統名、需求欄位值或任何 id（本 repo 為 public；比照 `U24` 的 `BR28.1`） | 本單元新增的前端檔中 `console.` 的出現逐筆判讀：只允許固定字串；寫進 code-summary |

## 五、Audit logging 的處置

- **讀取不記稽核**：兩支列舉端點放寬前後皆不記（`functional-spec.md` §九之一 的既有判定），本站沿用。
- **成功的寫入**：建立系統沿用既有路徑；刪除不記稽核——與放寬前相同，本單元不改變 `U7` 的稽核形狀。
- **被拒絕的寫入不新增 log**：`U7`／`U19` 家族目前**零處**記拒絕（`hierarchy_facade.py`、`hierarchy_router.py`、`membership_facade.py`
  對 `logger.(info|warning|error|debug)` 的 grep 皆為 0；`hierarchy_facade.py:47` 宣告了 logger 但未使用），既有的「非擁有者
  試圖刪除他人專案」同樣不記。只為 `PPN-14` 這一道守門破例，會讓同一家族的拒絕有的記、有的不記。**對照**：`U20` 的需求欄位
  facade 有拒絕 WARNING（`requirement_field_facade.py:268-283`，`BR41.6`），那是該單元自己的規則，不外溢。
- **殘留**：被移出的建立者嘗試刪除，事後**查不到**；但 `PPN-14` 使該嘗試失敗且資料不變，故缺的是「嘗試」的紀錄，不是「破壞」的紀錄。

## 六、ADR-0006 四面向（逐格對照上游 `functional-spec.md` §九之一）

| 面向 | 上游判定 | 本站判定 | 差異與理由 |
|---|---|---|---|
| **IAM** | 適用（本單元新增的落點） | **適用（擴充）** | 上游列了兩支列舉端點的六點處置；本站新增 §三 的三條寫入守門（`PPN-14`–`PPN-14c`）——**範圍變了**（R-01 使用者裁決），不是重判。另補兩條上游未寫的可判定形式：`PPN-13`（`detail` 字串也須相同，上游只寫「同一結果」）與 `PPN-14a`（寫入路徑的 403 不得變 404）。上游殘留的 `OPEN-PP23-10` **關閉**；`OPEN-PP23-6` 第 ③ 項（大腦對象目錄仍為擁有者範圍）**照舊**為殘留 |
| **Encryption** | 適用，但不在本單元（落點 `U21`） | **相同** | 零新傳輸、零新儲存；`PPN-17` 使草稿不落地。`[PPN1]`=A 的索引不含任何新資料 |
| **Network exposure** | 適用，但不在本單元（落點 `U21`） | **相同** | 零新端點、零新進程、零新埠；兩支列舉端點與三條寫入路徑皆在既有 `/api/hierarchy/` 下且需驗證身分 |
| **Audit logging** | 適用（沿用既有） | **相同（沿用既有）** | §五：不新增讀取稽核、不新增拒絕 log，理由與殘留已寫 |

## 七、PBT hard constraint

| 候選 | 判定 | 理由 |
|---|---|---|
| `ADR-0006` 點名的三個落點（IaC generator、cost calculator、agent routing） | **不適用（非豁免）** | 皆非本單元 |
| 可見性謂詞 | 不適用 | 兩個分支（成員列；擁有者且零成員列）的全部組合由 `PPN-12` 的五身分與 `PPN-14` 的四案 example-based 窮舉；不是三個 hard-constraint 落點之一。與上游 `functional-spec.md` §九之二 一致 |
| 前端佇列（`PPN-01`–`PPN-04`） | 不適用 | 前端無 unit 測試框架（`team.md`，D 項不採），且非三個落點之一；以 e2e 的計數斷言約束 |

## 八、帶入項對照（`carried-review-items.md`）

| 帶入項 | 本站轉成的判準 | 未轉成判準的部分 |
|---|---|---|
| R-01（Major，使用者裁決） | `PPN-14`、`PPN-14a`、`PPN-14b`、`PPN-14c`；`PPN-13` 擴及寫入路徑 | 「在核可關卡重新揭露級聯」屬 code-generation 的關卡摘要，不是 NFR |
| R-02（Minor，`BR86.2` 空態文字） | 無——是畫面文字，非 NFR | 由 code-generation 處置 |
| R-03（Minor，`BR87.5` 的 ③ 構造與 M5） | `PPN-12` 的 ③ 改為「另一專案的成員」、新增 M5 | — |
| R-04（Minor，佇列優先序） | `performance-requirements.md` 的 `PPN-02` 與 §二之二 | — |
| R-05（Minor，空表） | 無——是設計檔的格式缺陷，設計檔不回改 | 由 code-generation 在 code-summary 記明 |

## 九、刻意不設的目標

| 不設 | 理由 |
|---|---|
| 對列舉讀取的速率限制 | 本 repo 無既有速率限制機制；兩支端點只回請求者可見的資料，枚舉 id 也只得到 404（`PPN-13`） |
| 對三條寫入路徑加列鎖 | 見 §三之二 的殘留 |
| 拒絕寫入的稽核 log | 見 §五 |
| CSRF 防護 | 既有 API 以 `Authorization: Bearer` 標頭認證、不用 cookie 會話，跨站請求帶不上該標頭；本單元不改認證方式 |

## 十、送審前自檢（七項；全部產出寫完後實算，數字皆由 grep／jq 取得，未執行任何測試）

見 `tech-stack-decisions.md` §五（四份產出共用一張自檢表，避免四處各寫一份而互相漂移）。
