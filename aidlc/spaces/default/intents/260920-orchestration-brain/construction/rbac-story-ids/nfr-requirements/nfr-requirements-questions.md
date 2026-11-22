# NFR Requirements 問題檔 — `U3 rbac-story-ids`（`spec`）

<!-- Stage: nfr-requirements（Construction 3.2）· Unit: rbac-story-ids · kind: spec -->

## 前言

本單元交付 **`K1`–`K4` 四個 story id 的 seed 語意**（矩陣 308 → 352 列），
零端點、零畫面、零容器、零環境變數。`produces_kinds` 把 `performance`／
`scalability`／`reliability`／`observability` 四份產出限定在 `service`／`ui`
kind，故本 `spec` 單元只產 `security-requirements.md`、`tech-stack-decisions.md`
與 `traceability.json`——與 `U2`／`U4` 兩個 `spec` 單元相同。

### 已由上游定案、本站不重問

| 事項 | 定案 | 來源（逐字核對過） |
|---|---|---|
| 四個 story id 的預設值（view 8／edit 4） | 已定案 | `functional-design` 修訂 1 Q5=A、Q6=A；`BR5.1`／`BR5.2`／`BR6.1`／`BR6.2` |
| `K4` 只把關需求籤 | 已定案 | 同上 Q6=A；`BR6.3`（對齊修正） |
| 邀請與自動改選的檢查對象 | 已定案 | 同上 Q7=A；`BR7.1`–`BR7.3` |
| 四個標籤**公開**於 `/roles/catalog` | 已定案 | `BR4.5`（照 `J3a`／`J3b` 既有先例不排除） |
| 兩份 seed 副本一致性測試的落點 | 已定案 | `team.md ## Code Style` 的「單一真實來源」逐字；`test-case-authoring.md` §4.1 指定 `backend/tests/`，由既有 `python -m unittest discover` 撿到 |
| `schema_rbac.sql` ＋ `DEPLOY.md` 同步為 blocking | 已定案 | `project.md ## Mandated`；`BR4.1`′／`BR4.2`′ |
| ADR-0006 的 PBT hard constraint 對本單元為 N/A | 已定案 | `rules.md` 修訂 1 的 PBT 判定段；`calculation` 類規則實算為 0，且 `BR7.4` 點名的純函式是 `U19` 的交付物 |

### 本站查證到的五件事實（供題幹與選項引用，非上游來源）

1. **矩陣成長對回應時間無影響，已查證**：`get_permission_row`
   （`backend/services/rbac.py:114`）是單筆 `filter(role==, story_id==).first()`，
   而 `schema_rbac.sql:434` 的 `PRIMARY KEY (role, story_id)` 正是該查詢的鍵。
   308 → 352 是 **+14%** 的列數，對 PK 查詢無實質差異。故 **NFR3（首字回應時間）
   對本單元判定 N/A，理由是實測的索引形狀而非印象**。
2. **`/roles/catalog` 是未驗證身分的端點，且每次呼叫發 11 次查詢**：
   `user_router.py:310` 無任何 `Depends(get_current_user)`，docstring 逐字
   「**公開**：註冊頁角色功能目錄」；`_build_role_catalog`（`:249`）對
   `CANONICAL_ROLES` 的 11 個角色各發一次 `db.query(RolePermission).filter(...)`。
3. **repo 內零 rate limiting 基礎設施**：`backend/requirements.txt` 無
   `slowapi`／任何 limiter；真正生效的 nginx 設定是 **`frontend/nginx.conf`**
   （`frontend/Dockerfile:25` 把它 COPY 成 `default.conf`），其中 `limit_req`
   與 `limit_conn` 的命中數為 **0**。
   **附帶**：`project.md ## Mandated` 與 `CLAUDE.md` 都指 `deploy/nginx.conf`，
   該檔**不存在**——這是規則層的既存失效引用，不是本單元造成的。
4. **seed 寫入的 log 只有一個數字**：`rbac.py:110` 與 `database.py:186` 都是
   `logger.info("ensure_missing_role_permissions: inserted %d rows", ...)`，
   **不記錄是哪些 (role, story_id)**。這就是 `functional-design` 的交接事項
   `H-3`，而本修訂把它涵蓋的列數由 22 變為 **44**。
5. **本單元沒有任何可自驗的授權機械檢查**：`BR7.1`–`BR7.3` 是本單元**定義**、
   `U19` **執行**的規則（`BR5.5`），而本單元交付零端點。

---

## Q1. `/roles/catalog` 的公開揭露，本站要怎麼處置？

`BR4.5` 已定案「照既有先例發布、不排除」，故**揭露本身不是本題**。本題問的是
**本站的安全需求要不要對該端點提出緩解要求**——它是未驗證身分、每次 11 次查詢、
且本單元讓它的回應多 4 列（事實 2、3）。STRIDE 上這是
Information Disclosure（已接受）＋ Denial of Service（未評估）。

- **A（建議）：列為具名的既存殘餘風險，本單元不新增緩解要求。**
  在 `security-requirements.md` 的殘餘風險表具名記載：該端點未驗證身分、
  每次呼叫 11 次查詢、無任何層級的 rate limiting（事實 3），並明寫本單元
  **只讓每次回應多 4 列、不改變它的可觸發性**。指派 `operation` 階段處置。
  **理由**：揭露類別未變（`J3a`／`J3b` 這兩個管理類標籤已公開）；DoS 面是該
  既有端點的既有性質，不是本單元引入的；要求加固等於把一個既有端點的改造
  夾帶進一個零程式的 seed 單元。
  **代價**：這個 DoS 面在本 intent 內不會被處理，只會被記下來。
- **B：把 rate limiting 列為本單元的交付條件。**
  **代價**：repo 內**零** rate limiting 基礎設施（事實 3），要新增依賴
  （`slowapi` 或同類）或改 `frontend/nginx.conf`——前者違反本單元
  `tech-stack-decisions.md` 的零新依賴立場，後者碰的是部署資產。
  且本單元原本交付零程式，這條會讓它開始碰中介層。
- **C：要求把 `K1`–`K4` 加進 `CATALOG_EXCLUDED_STORIES`，不公開。**
  **代價**：**推翻已核可的 `BR4.5`**（`functional-design` 修訂 1 的定案），
  且註冊頁的角色功能目錄看不到這四項新能力——而該頁的全部目的就是讓人知道
  各角色能做什麼。`J1` 之所以被排除是因為它是登入能力、不是功能。
- **D：本站不判，指派 `nfr-design`（3.3）。**
  **代價**：`nfr-design` 是 `CONDITIONAL`，本 record 已有兩次指派落空的實例；
  且本站**正是** NFR 的落點，往下推是本站該做而未做。

[Answer]: A — 列為具名的既存殘餘風險，本單元不新增緩解要求  <!-- 2026-10-04T11:55:27Z | Mode: guided -->

**作答後果**：`security-requirements.md` 的殘餘風險表須具名記載四件事實
（端點未驗證身分、每次 11 次查詢、repo 零 rate limiting、本單元只讓回應多 4 列
而不改變可觸發性），並指派 `operation` 階段。**本站不得宣稱 ADR-0006 的
network exposure 面已完全處置**——`functional-design` §六′ 已把它由「不適用」
改為「適用（一處）」，本站承接該判定並補上 DoS 面的殘餘風險登記。

---

## Q2. `H-3` 的稽核粒度缺口（seed 寫入只記列數、不記哪些列），44 列後要怎麼處置？

`functional-design` 把它記為「**無自然承接站**」，並明寫
「該面向在本 intent 內只被部分履行、`H-3` 未結案」。而 ADR-0006 的
audit logging 面是 `project.md` 的 hard constraint，**本站是 NFR 的落點**，
所以這一題不能再往下推。

- **A（建議）：列為本單元的安全需求，要求 `ensure_missing_role_permissions`
  記錄插入了哪些 `(role, story_id)`。**
  形式為既有 `logger.info` 擴充（彙總成一行清單即可，不必逐列一行）。
  **理由**：ADR-0006 是 hard constraint；該函式雖是既有的，但本單元正是讓它
  插入 44 列的那個變更；不記哪些列，既有環境補列後**無從驗證補對了什麼**
  ——現象是「日誌說插了 44 列」而沒有任何方式確認那 44 列是不是 `K1`–`K4` 的。
  **代價**：碰既有共用函式 `rbac.py`，超出「只改 seed 資料」的原始範圍
  （雖然改動在 2 行以內）。
- **B：維持缺口，列為殘餘風險並指派 `operation`。**
  **代價**：`H-3` 涵蓋的列數由 22 變 44，缺口變大而沒人處置；且 ADR-0006 的
  audit 面在本 intent 內持續只被部分履行——而那是 hard constraint，不是建議。
- **C：不改既有函式，改在啟動路徑（`database.py:184-186`）記錄。**
  該處已經記了列數，擴成列出 `(role, story_id)` 清單。
  **代價**：log 的產生點與插入點分離。若日後出現第二個呼叫
  `ensure_missing_role_permissions` 的地方，它不會記——而該函式目前只有一個
  呼叫端，所以今天成立、明天不保證。
- **D：要求把 seed 寫入記進一張稽核表。**
  **代價**：本單元 `functional-spec.md §八` 明文「不建表」；且使用者域目前
  **沒有**可讀的稽核表（`[US:Q-11]` 的 Critical 已記載此事）。

[Answer]: A — 要求 `ensure_missing_role_permissions` 記錄插入了哪些 `(role, story_id)`  <!-- 2026-10-04T11:55:27Z | Mode: guided -->

**作答後果**：`H-3` 由「無自然承接站的已知缺口」轉為**本單元的安全需求**
（具名 `SEC-4`）。形式為既有 `logger.info` 的擴充（彙總成一行清單，不逐列一行），
落點 `rbac.py:110`。這讓本單元的改動範圍由「只改 seed 資料」擴為
「seed 資料 ＋ 一處既有共用函式的 log 行為」——須在
`tech-stack-decisions.md` 的改動面清單明寫，否則 `code-generation` 會以為
`rbac.py` 不在範圍內。

---

## Q3. 本單元的驗證形式——`BR5.3`／`BR6.5`／`BR5.4` 三條可達性保證要不要有機械檢查？

本單元交付零端點，`BR7.1`–`BR7.3` 的授權判定由 `U19` 執行（事實 5）。
但 `functional-design` 另立了三條**對 seed 預設值本身**的結構約束：
`BR5.3`（至少一個有 `A1` view 的角色不得持有 `K3`）、`BR6.5`（至少一個角色
不得持有 `K4`）、`BR5.4`（持有 `K2.edit` 者必須持有 `K3.edit`）。
它們保護的是 `AC12.5.1`／`AC12.1.2`／`BR6.4` 不變成死碼。

- **A（建議）：兩者都要——本單元自驗 seed 不變量，授權判定對 `U19` 具名。**
  本單元的測試斷言三條可達性保證成立（純解析 `DEFAULT_ROLE_PERMISSIONS`，
  與 `BR4.4`′ 的兩份副本比對測試同一支檔、零新依賴）；`BR7.1`–`BR7.3` 的
  allow/deny 雙向則寫成對 `U19` 的具名交付條件（`U3-A1`–`U3-A3`），
  並在安全需求檔明載「本單元對授權判定無可自驗的機械檢查」。
  **理由**：那三條約束的全部價值在於「日後有人調 `K3`／`K4` 預設值時會紅燈」
  ——沒有機械檢查，它們就只是三句話。而本站已實作出該解析（用於複算 352），
  成本接近零。
- **B：只對 `U19` 具名，本單元不自驗。**
  **代價**：三條可達性保證沒有任何機械檢查。日後有人把 `K3` 給滿 11 個角色，
  `AC12.5.1` 會靜默變成死碼——**而那正是這三條存在的理由**，`AC1.4.2` 已經
  踩過一次同形的坑。
- **C：只本單元自驗，不對 `U19` 具名。**
  **代價**：`BR7.1`–`BR7.3` 沒有落點，形成與 `H-10` 同形的死指派。
- **D：把三條可達性保證改寫成「建議」而非約束，不要求檢查。**
  **代價**：等於撤回 `functional-design` 剛核可的決定，且不解決任何問題
  ——該站的審查 `R-01` 正是因為「窄化沒有被記下來」而判 Major。

[Answer]: A — 本單元自驗 seed 不變量，授權判定對 `U19` 具名  <!-- 2026-10-04T11:55:27Z | Mode: guided -->

**作答後果**：本單元的驗證需求分兩類。
**自驗（`U3-V*`）**：一支測試斷言 `BR5.3`／`BR6.5`／`BR5.4` 三條可達性保證
成立，與 `BR4.4`′ 的兩份副本比對測試同一支檔、零新依賴
（本站已實作該解析用於複算 352）。
**對 `U19` 具名（`U3-A1`–`U3-A3`）**：`BR7.1`–`BR7.3` 的 allow/deny 雙向
`TestClient` 覆蓋，並在安全需求檔明載「本單元對授權**判定**無可自驗的機械檢查，
只驗授權**資料**的結構前提」。兩者缺一都會留下已記載過的缺陷形狀
（前者＝三條保證變成三句話，後者＝與 `H-10` 同形的死指派）。
