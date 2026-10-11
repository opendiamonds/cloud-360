# Security Requirements — `U3 rbac-story-ids`（`spec`）

<!-- Stage: nfr-requirements（Construction 3.2）· Unit: rbac-story-ids · kind: spec -->

本單元交付 `K1`–`K4` 四個 story id 的 seed 語意（矩陣 308 → **352** 列），
零端點、零畫面、零容器、零環境變數。它**定義授權資料**，不執行授權判定
（`functional-design/rules.md` 的 `BR5.5`；行為規格的正本為同目錄的
`functional-spec.md`，其 §三′ 的 `W-4`／`W-5` 兩條工作流程即本檔 `SEC-6` 與第四節
所指的授權判定落點）——但 `functional-design` 修訂 1 讓它同時
定義了一條**加入時的前置授權規則**（`BR7` 群，`authorization` 類別由 0 變為 3），
故本檔是本單元最重的一份產出。

**本檔消費的上游（逐一開檔核對）**：`functional-design/functional-spec.md`（§一′ 的 44 列、§三′ 的 `W-4`／`W-5`、§六′ 的四面向判定、§七／§七′ 的交接表）、`functional-design/rules.md`（`BR3.4`′／`BR4.1`′–`BR4.5`／`BR5.*`／`BR6.*`／`BR7.*`）、`inception/requirements-analysis/requirements.md`（`NFR1`–`NFR11` 與 `FR9.5`／`FR12.6`）、`inception/contract-design/contract-summary.md`（`K-03` 與修訂 1 的 `K-16`／`K-17`／`K-19`／`K-20`）。

## 一、本單元的安全需求（`SEC-*`）

| ID | 需求 | 對應 ADR-0006 面向 | 可驗證方式 |
|---|---|---|---|
| `SEC-1` | 本單元**不得新增**任何 router 檔、service 層讀寫函式或可從 HTTP 觸達的入口。**措辭已依審查 `R-05` 收窄**：初版寫「不得交付任何 service 層讀寫函式」，字面比它自己的可驗證條件寬，而本單元的改動面第 5 列**確實**動了既有 service 層函式 `rbac.py` 的 `ensure_missing_role_permissions`（`SEC-4` 的 2 行 log 擴充）。本條禁止的是**新增**入口，不是禁止碰任何既有函式——`SEC-4` 的改動是明文的例外。以交付面上不可構造的方式滿足 `[RA:FR9.5]` 的「不得有任何繞過 `require_story_action` 的路徑，含同進程直呼 service 層」。 | IAM | 交付檔案清單（`code-generation` 的 `source-manifest.json`）內不得出現 router／service 層新檔；`BR1.4`／`BR5.5` 的範圍邊界 |
| `SEC-2` | seed 寫入為**啟動期的特權操作**（跨角色的授權資料寫入），必須沿用啟動路徑既有的資料庫連線，**不得引入第二個憑證或任何新環境變數**。 | IAM | `python3 scripts/validate_env_contract.py` 通過；`deploy/render-env.sh` 與 `deploy/.env.example` 零新增 key |
| `SEC-3` | **零新增網路暴露面**，但本單元**改變了一個既有公開端點的回應內容**——見第三節的 `RR-1`。本需求因此**不是**「不適用」而是「適用且已具名殘餘風險」。 | network exposure | 無新 route decorator、無新 `app.include_router`；`RR-1` 的殘餘風險登記 |
| `SEC-4` | `ensure_missing_role_permissions` 插入列時**必須記錄是哪些 `(role, story_id)`**，不得只記列數。形式為既有 `logger.info`（`rbac.py:110`）擴充為一行彙總清單。 | audit logging | 既有環境啟動後的 log 含四個新 story id 的字串；不含任何角色以外的個人資料 |
| `SEC-5` | 兩份 seed 副本（`schema_rbac.sql` 的 `INSERT` 區塊與 `rbac_seed_data.py` 的 `DEFAULT_ROLE_PERMISSIONS`）**必須逐列等值**，由測試鎖住。 | IAM（完整性） | `BR4.4`′ 的測試；落點 `backend/tests/`，由既有 `python -m unittest discover -s tests` 撿到 |
| `SEC-6` | 本單元**對授權判定無可自驗的機械檢查**，只驗授權**資料**的結構前提。`BR7.1`–`BR7.3` 的 allow/deny 雙向覆蓋為對 `U19` 的具名交付條件（第四節）。 | IAM | 本檔第四節的具名指派；不得被讀成本單元已驗證授權行為 |

### `SEC-4` 的理由，與它擴大的改動範圍

`functional-design` 的交接事項 `H-3` 把這個缺口記為「**無自然承接站**」，並明寫
「該面向在本 intent 內只被部分履行、`H-3` 未結案」。本站是 NFR 的落點，
而 ADR-0006 的 audit logging 面是 `project.md` 的 hard constraint，
故本站 `[Q2]`=A 把它收為本單元的需求。

**實測現況**：`rbac.py:110` 與 `database.py:186` 都是
`logger.info("ensure_missing_role_permissions: inserted %d rows", ...)`，
**只有一個數字**。既有環境補進 44 列之後，日誌說「插了 44 列」，
而沒有任何方式確認那 44 列是不是 `K1`–`K4` 的——補錯了也看不出來。

**後果：本單元的改動範圍擴大。** 原本是「只改 seed 資料」，現在是
「seed 資料 ＋ 一處既有共用函式的 log 行為」。這一點必須同時寫在
`tech-stack-decisions.md` 的改動面清單裡，否則 `code-generation` 會以為
`rbac.py` 不在範圍內。改動量在 2 行以內。

**不得記錄的內容**：log 只寫 `(role, story_id)` 配對——那是角色與能力的對應，
不含任何使用者身分。`project.md` 的「不得把敏感資料寫進任何 log」在此不受影響。

## 二、STRIDE 逐項（本單元的攻擊面）

本單元的攻擊面極小（零端點），但**它寫入的資料是整個系統的授權依據**，
所以 Tampering 與 Elevation of Privilege 兩項的影響面遠大於它的程式量。

| 類別 | 本單元的曝險 | 處置 |
|---|---|---|
| **S** Spoofing | 不適用——本單元不驗證任何身分。 | — |
| **T** Tampering | **兩份 seed 副本無聲漂移**：從 `schema_rbac.sql` 建的新環境拿 SQL 那份的值，既有環境經 `ensure_missing_role_permissions` 拿 Python 那份的值。兩者不同時**沒有任何閘門會紅燈**，現象是「同一個角色在不同環境有不同權限」。 | `SEC-5`（`BR4.4`′ 的逐列等值測試）。本站查證：`backend/tests/` 目前**零**測試做這件事。 |
| **R** Repudiation | seed 寫入目前只留一個列數，無從事後確認補了什麼。 | `SEC-4` |
| **I** Information Disclosure | 四個新標籤經 `/roles/catalog` 對**未驗證身分**的訪客可讀。 | 已由 `BR4.5` 定案為**接受**（照 `J3a`／`J3b` 既有先例，揭露類別未變）；本站補登 `RR-1` 的 DoS 面。 |
| **D** Denial of Service | `/roles/catalog` 未驗證身分且每次呼叫發 **11 次**查詢（`_build_role_catalog` 對 `CANONICAL_ROLES` 逐角色一次 query）；repo 內**零** rate limiting。本單元讓每次回應多 4 列。 | `RR-1`（具名既存殘餘風險，`[Q1]`=A）。**本單元不改變它的可觸發性**，只讓回應稍大。 |
| **E** Elevation of Privilege | **預設值給錯等於直接給錯權限。** 兩個具體形狀：(a) `K3.edit` 少給任一個建立者角色 → 他管不動自己建的專案（`BR5.4`）；(b) `K3` 給滿 11 個角色 → `AC12.5.1` 的 Given 不可構造，該 AC 變成不會失敗的死碼（`BR5.3`）。 | `U3-V1`–`U3-V3` 的 seed 不變量測試（第四節）；`U3-A1`–`U3-A3` 的 allow/deny 雙向由 `U19` 承擔。 |

**本單元的 STRIDE 重心在 T 與 E，而兩者的失敗模式都是靜默的**——不會報錯，
只會讓某個角色擁有或缺少他不該擁有或缺少的權限。這是本單元全部驗證需求的
共同理由。

## 三、殘餘風險（具名，不得以「已處置」帶過）

| ID | 風險 | 為什麼接受 | 承接站 |
|---|---|---|---|
| `RR-1` | **`/roles/catalog` 是未驗證身分的端點，每次呼叫發 11 次資料庫查詢，而 repo 內零 rate limiting。** 實測依據：`user_router.py:310` 無任何 `Depends(get_current_user)`，docstring 逐字「**公開**：註冊頁角色功能目錄」；`_build_role_catalog`（`:249`）逐角色一次 query；`backend/requirements.txt` 無 `slowapi`／任何 limiter，而真正生效的 nginx 設定是 **`frontend/nginx.conf`**（由 `frontend/Dockerfile:25` COPY 成 `default.conf`），其 `limit_req`／`limit_conn` 命中數為 **0**。 | 這是該既有端點的**既有**性質，不是本單元引入的。本單元只讓每次回應多 4 列，**不改變它的可觸發性**。要求加固等於把一個既有端點的改造夾帶進一個零程式的 seed 單元，而 repo 內沒有任何 rate limiting 基礎設施可沿用。 | `operation` 階段（`[Q1]`=A 的指派） |
| `RR-2`（**資訊性，非本單元的風險**——依審查 `R-03` 標註） | **`project.md ## Mandated` 與 `CLAUDE.md` 都要求「異動 `deploy/nginx.conf` 時同步更新 `LOCAL-DEV.md`」，而該檔不存在。** 實測：`deploy/` 下只有 `cloudflared/`、`docker-compose.deploy.yml`、`docker-compose.test.yml`、`render-env.sh`；真正生效的是 `frontend/nginx.conf`。 | 這是**規則層的既存失效引用**，與本單元無關（本單元不碰任一者）。**審查 `R-03` 指出放在本表會被誤讀**：這張表的用途是追蹤**本單元交付物**的風險，而掃這張表找 `U3` 曝險的人會把它誤算進去。故本列明文標為**資訊性**——它不是 `U3` 接受的風險，是本站查證時撞到的跨領域文件缺陷。記在此處的理由不變（規則層沒有任何機制會告訴下一個人），但不得被計入 `U3` 的風險。 | 下一次 `practices-discovery`，或任何要動 nginx 設定的 intent |
| `RR-4` | **`schema_rbac.sql:761` 的驗證註解是既存漂移，且本單元會讓它碰巧變成正確。** 實測：該行現在寫 `-- SELECT count(*) FROM role_permissions;  -- 352`，而同檔 `INSERT` 區塊逐列實算為 **308**；`git blame` 指向 `6f9227d`（2026-08-23，C1 FinOps 的 commit），與本單元無關。本單元加完 44 列之後該行變成正確——**但那是副作用，不是有人修過它**。若日後總數再變，這一行仍需手動改。 | 接受：修一個與本單元同方向的既存錯誤不需要額外決定，但必須寫下來，否則下一個人會以為那一行一直是對的、因此可以信任它。由審查 `R-01` 逼出——本單元的 `functional-design` `BR4.1`′ 已把它記為陷阱，而本檔的改動面清單初版把它誤述成「第二處要改的數字」。 | 本單元（`code-generation` 時連帶正確），漂移本身無須另行處置 |
| `RR-3` | **`SEC-5` 的測試是兩份副本一致性的唯一防線，而副本本身不消除。** `team.md ## Code Style` 的「單一真實來源」允許跨語言邊界的副本，條件是同一個 PR 附上鎖住一致的測試。 | 兩份副本是既成事實（`rbac_seed_data.py` 的檔頭逐字說它由 `schema_rbac.sql` 產生），而**那支產生腳本不存在**（本站與 `functional-design` 各自查證：`backend/scripts/` 下只有 `dump_openapi.py`、`dump_ws_contract.py`、`run_hierarchy_migration.py`）。消除副本要先寫產生器，那是獨立任務。 | 未指派——`BR4.1`′ 的 note 已記載此事，消除副本不在本 intent 範圍 |

## 四、驗證需求（`[Q3]`=A 的兩類）

### 4.1 本單元自驗的 seed 不變量（`U3-V*`）

純解析 `DEFAULT_ROLE_PERMISSIONS`，零新依賴。與 `SEC-5` 的兩份副本比對測試
同一支檔（本站已實作該解析，用於複算 352 與 11 項不變量）。

| ID | 斷言 | 它保護的 AC | 違反時的現象 |
|---|---|---|---|
| `U3-V1` | `BR5.3`：存在至少一個角色，持有 `A1` view 但**不持有** `K3` 的任何旗標。 | `AC12.5.1`、`AC12.5.3` | 兩條 AC 的 Given 不可構造，測試綠燈但測不到東西 |
| `U3-V2` | `BR6.5`：存在至少一個角色不持有 `K4` 的任何旗標。 | `BR6.4`（本修訂新增的規則） | `BR6.4` 成為不可觸發的死碼 |
| `U3-V3` | `BR5.4`：對每一個持有 `K2.edit` 的角色，`K3.edit` 亦為 true。 | `AC12.1.2` | 「我建的專案，我管不動」，而權限頁看不出是哪一層擋的 |
| `U3-V4` | `BR3.4`′：`len(DEFAULT_ROLE_PERMISSIONS) == 352` **且**組合完整（每個 `(role, story_id)` 恰一列、無缺漏）。 | — | 列數對但組合有缺漏時，缺的那格在權限頁是破洞而總數看起來正常 |
| `U3-V5` | `EC-4`：四個新 id 的 `can_review` 在全部 44 列皆為 false。 | — | 挪用既有審核語意，而權限頁該欄的標籤對不同列代表不同意思 |

**這五條是本單元唯一可自驗的部分**，而它們驗的是**授權資料的結構前提**，
不是授權行為。

### 4.2 對 `U19` 的具名交付條件（`U3-A*`）

`BR7.1`–`BR7.3` 是本單元**定義**、`U19` **執行**的規則（`BR5.5`）。
本單元交付零端點，故這三條在本單元內**無法驗證**。

| ID | 要求 `U19` 覆蓋的行為 | 來源 |
|---|---|---|
| `U3-A1` | 邀請一般成員：被邀請者持有 `K3.view` → 成功；不持有 → 拒絕且不寫入任何列。 | `BR7.1`、`AC12.5.1`、`AC12.5.3` |
| `U3-A2` | 邀請／改為專案管理者：目標持有 `K3.edit` → 成功；只持有 `K3.view` → 拒絕。 | `BR7.2`、`AC12.2.1` |
| `U3-A3` | 自動改選：候選集合只含持有 `K3.edit` 的成員；無人符合時擋下停用並列出受影響專案。 | `BR7.3`、`AC12.4.x`、`[M3]`=A |

形式為 allow/deny 雙向 `TestClient`（`team.md ## Testing Posture` 的 A 規則與
B 規則交叉要求）。**`U3-A3` 另有一項不在 allow/deny 範圍內的約束**：
`BR7.4` 要求挑選純函式不讀 DB，故 `K3.edit` 旗標必須由呼叫端查好後傳入
——這改變了該函式的簽章，是 ADR-0006 的 PBT hard constraint 能在它身上
作用的結構前提。

## 五、ADR-0006 security baseline 四面向（本站逐項判定）

| 面向 | 判定 | 本站的處置 |
|---|---|---|
| **IAM** | **適用（核心）** | `SEC-1`、`SEC-2`、`SEC-5`、`SEC-6` ＋ 第 4 節的 `U3-V1`–`U3-V5` 與 `U3-A1`–`U3-A3`。最小權限的具體落點：`K3`／`K4` 皆不給三個純唯讀維運角色、`edit` 只給四個建立者角色而非全部。 |
| **Encryption** | **不適用** | 本單元不新增欄位、不儲存機密值；44 列仍是布林旗標與角色名。與 `functional-design` §六′ 的判定一致。 |
| **Network exposure** | **適用（一處，已具名殘餘風險）** | 承接 `functional-spec.md` §六′ 的更正（該檔把它由「不適用」改為「適用」，由其自檢 2 推翻自己的初版判定）。本站補上 DoS 面：`RR-1`。**本站不宣稱該面向已完全處置。** |
| **Audit logging** | **適用（本站收為需求，不再是缺口）** | `SEC-4`：`H-3` 由「無自然承接站的已知缺口」轉為本單元的需求（`[Q2]`=A）。**仍未處置的部分**：`H-3` 的原文在 `functional-spec.md` §七 的交接表。`BR7.1`–`BR7.3` 的**拒絕**事件是否留稽核，由同檔 §七′ 的 `H-8` 指派 `U19`，不在本單元。 |

## 六、PBT hard constraint（ADR-0006 的另一項）

**對本單元判定 N/A，且理由已於上游收斂**：`rules.md` 修訂 1 實算
`calculation` 類規則為 **0**；`BR7.4` 點名的挑選純函式**確實**是 PBT 的標的
（真正可失敗的性質是**排列不變性**，不是「同一組輸入選出同一人」那個恆真命題），
但它是 `U19` 的交付物。本站以 `U3-A3` 把該義務具名指派給 `U19`，
**不讓它在兩個單元之間掉落**。

`U3-V1`–`U3-V5` 全部是對固定資料集合的斷言，沒有值域可探索，
故不適用 PBT——這是形狀判定，不是豁免。

## 七、合規（compliance）

本專案無 PCI-DSS／HIPAA／GDPR 等外部框架的明文適用宣告，`requirements.md`
與 `contract-summary.md` 的 ADR-0006 表皆未提及任何法規框架。
本單元寫入的資料是**角色與能力的對應**，不含任何個人可識別資訊
（`updated_by` 在 seed 列為固定字串 `"system_seed"`）。
故本站不產生 compliance 需求，亦不宣稱任何框架已滿足。

`SEC-4` 的 log 擴充同樣只寫 `(role, story_id)`，不引入個人資料
——這是刻意的，見第一節該條的「不得記錄的內容」。
