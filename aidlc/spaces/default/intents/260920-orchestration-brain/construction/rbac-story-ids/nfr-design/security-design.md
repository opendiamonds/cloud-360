# Security Design — `U3 rbac-story-ids`（`spec`）

<!-- Stage: nfr-design（Construction 3.3）· Unit: rbac-story-ids · kind: spec -->

本檔把 `nfr-requirements` 的 `SEC-1`–`SEC-6`、`U3-V1`–`U3-V5`、`U3-A1`–`U3-A3`、
`U3-D1` 轉成**具體的設計決定**。本單元交付零端點、零畫面，所以這裡沒有認證流程、
沒有加密設計、沒有安全標頭——有的是**授權資料的完整性設計**與**它的驗證機制設計**。

### 消費的上游，逐一列出狀態

stage 檔的 `consumes` 把**五種** NFR 需求產出都標為 `required: true`，
而 `produces_kinds` 把其中四種限定在 `service`／`ui` kind——**本 `spec` 單元的
上游根本沒有產出它們**。兩者是 stage 檔內部的結構不一致，不是本單元的缺口。
逐一列出，不留空白：

| `consumes` 項 | 狀態 | 說明 |
|---|---|---|
| `security-requirements` | **已讀** | 本單元 `nfr-requirements` 的產出：`SEC-1`–`SEC-6`、`RR-1`–`RR-4`、`U3-V1`–`U3-V5`、`U3-A1`–`U3-A3`、`U3-D1` |
| `tech-stack-decisions` | **已讀** | 同上；§二 的六列改動面（含 `[Q2]`=A 擴進來的 `rbac.py`） |
| `functional-spec` | **已讀** | `functional-design` 修訂 1：§一′ 的 44 列、§三′ 的 `W-4`／`W-5`、§六′ 的四面向、§七／§七′ 的交接表 |
| `contract-summary` | **已讀** | `K-03`（本單元擁有的契約）與修訂 1 的 `K-16`（`U19` 的 facade，`U3-A*` 的消費端） |
| `performance-requirements` | **不存在** | `produces_kinds` 限 `[service, ui]`，本單元為 `spec` |
| `scalability-requirements` | **不存在** | `produces_kinds` 限 `[service]` |
| `reliability-requirements` | **不存在** | `produces_kinds` 限 `[service]` |
| `observability-requirements` | **不存在** | `produces_kinds` 限 `[service]` |

**後四項的缺席是 by design 而非遺漏**，與 `U2`／`U4` 兩個 `spec` 單元相同。
依 stage-protocol 的 `consumes_absent` 處理方式，`expected: true` 的缺席不需要
當成缺口上報——但**必須列出來**，否則下一個讀本檔的人無法分辨「沒讀」與「不存在」。

**兩項 sensor 發現已知且為結構性，本站不以造假方式消除**（兩者皆 advisory）：

1. **`traceability` sensor 回報「本單元的 NFR 需求產出不含任何 `NFRx.y` ID」。**
   這是真的：本單元 11 條 inception NFR **全部**判定 N/A，沒有父項可編子號，
   故 `upstream_ids` 用的是 `SEC-*`／`U3-*`（沿用 `U4` 的既有先例）。
   要讓 sensor 通過就得**捏造**不適用的 `NFRx.y`，那比 sensor 紅燈更糟。
2. **`upstream-coverage` sensor 回報四項 unreferenced**，即上表後四項。
   本節把它們逐一具名後該 sensor 轉綠——但轉綠的原因是**文件把缺席寫清楚了**，
   不是四份檔案出現了。

---

## 一、授權模型設計（`SEC-1`／`SEC-6`）

### 1.1 本單元在授權鏈上的位置

```
         ┌─ 本單元：授權資料（352 列矩陣）
         │
         ▼
  role_permissions ──讀──> rbac.user_can() ──> require_story_action()
                                   ▲                      ▲
                                   │                      │
                      ARCH_DIAGRAM_STORIES            FastAPI
                      的 A1 正規化                    dependency
                                                          │
                                        ┌─────────────────┴─────────────────┐
                                        │                                   │
                                   U7／U14／U23             U19 的 MembershipFacade
                                   （既有形狀）              （K-16，per-project 第二層）
```

<!-- Text fallback：本單元只填 role_permissions 這張表。讀取端是既有的 user_can()，
它被既有的 require_story_action() FastAPI dependency 呼叫。下游有兩類消費者：
U7／U14／U23 走既有的單層 story-action 形狀；U19 走 K-16 的 MembershipFacade，
那是 FR12.6 兩層串聯的第二層。本單元不碰讀取端的任何一環。 -->

**設計決定 `D-1`：本單元不提供任何讀取端或判定函式。**
`SEC-1` 的可驗證條件（交付檔案清單不得出現 router／service 層**新檔**）由
`code-generation` 的 `source-manifest.json` 驗；本檔明訂它的設計理由：
多一條判定路徑就多一條繞過 `require_story_action` 的可能，而
`[RA:FR9.5]` 逐字禁止「任何繞過該 dependency 的路徑，含同進程直呼 service 層」。

**設計決定 `D-2`：`SEC-4` 的 log 擴充不構成 `SEC-1` 的例外。**
它改的是 `rbac.py::ensure_missing_role_permissions` 的**可觀察性**，
不是它的判定行為，也不新增任何入口。`SEC-1` 的措辭已於
`nfr-requirements` 依審查 `R-05` 收窄為「不得**新增**」，兩者一致。

### 1.2 兩層串聯中本單元負責的那一層

`FR12.6` 的兩層串聯（全域 `role_permissions` ＋ per-project 角色）之中，
**本單元只負責第一層的資料**。`BR7.1`–`BR7.3` 是本單元**定義**、`U19` **執行**
的規則（`BR5.5`）。

**設計決定 `D-3`：加入時的前置檢查（`W-4`）與執行期的兩層串聯，主體不同，不得混讀。**
`BR7.1`／`BR7.2` 檢查的是**被邀請者**的全域權限；`K-16` 的 per-project 判定
檢查的是**邀請者**在該專案的角色。把兩者讀成同一道檢查會讓其中一邊消失
——這一點已在 `functional-spec.md` 的 `W-4` 第 4 步寫明，本檔重申它是**設計約束**
而非敘述。

---

## 二、完整性設計（`SEC-5`）—— 兩份 seed 副本的比對

這是本單元**最重的一項設計**，因為它要防的失敗模式是**環境相依且無聲**的：
從 `schema_rbac.sql` 建的新環境拿 SQL 那份的值，既有環境經
`ensure_missing_role_permissions` 拿 Python 那份的值；兩者不同時
**沒有任何閘門會紅燈**，而現象是「同一個角色在不同環境有不同權限」。

### 2.1 解析範圍（已實測固定）

| 項目 | 實測值 |
|---|---|
| `INSERT INTO role_permissions` 區塊 | **唯一一個**，`schema_rbac.sql` 第 **445** 行起 |
| 區塊結束 | 第 **755** 行的 `;` |
| 其前一行 | 第 **443** 行 `DELETE FROM role_permissions;` |
| 被註解掉的 `INSERT` | **0 個** |
| `ON CONFLICT` 子句 | **0 個** |
| 第二個 `INSERT INTO role_permissions` | **不存在** |

**設計決定 `D-4`：解析不需要 SQL parser，正規表達式足夠，但範圍必須以區塊邊界限定。**
理由是上表：單一區塊、無註解陷阱、無衝突子句。

**限定範圍的真正理由是前瞻，不是現況**（審查 `R-02` 更正本條的初版）：
初版寫「該檔另有 C1 退役表等其他 `INSERT`，全檔掃會把無關的 tuple 撿進來」
——**那是錯的**。本站與審查各自實測：`schema_rbac.sql` 全檔的
`^\s*INSERT INTO` 命中數為 **1**，就是第 445 行那一個；C1 退役區塊只有
`CREATE TABLE`、**零個 `INSERT`**，沒有東西可以被誤撿。
正確的理由是：**限定範圍讓這支解析在日後有人加入第二個 `INSERT INTO` 區塊時
仍然正確**，而全檔掃在那一天會靜默地把新區塊的 tuple 併進比對集合。

**附帶更正（審查 `R-01`）**：初版引用的「第 166 行」不是那個區塊標題。
實測該標題在 **第 187 行**，逐字為
`-- C1 Cost / FinOps tables — RETIRED (U3 legacy-cost-retirement)`；
第 166 行是另一張表的 `created_at TIMESTAMPTZ DEFAULT now(),`。
**這個 166 是我從 `project.md` 的學習條目照抄的**——那條規則在寫下的當天是對的，
之後因上游修訂位移而失效。這是本 session 第三次撞到規則層的失效引用
（前兩次是 `codekb/chiton` 的分歧已被 symlink 修掉、`deploy/nginx.conf` 不存在）。

**實作指示（不受上述更正影響）**：以「`INSERT INTO role_permissions` 之後、
下一個裸 `;` 之前」定位，**不要寫死 445／755**——行號會隨本單元自己的 44 列
插入而位移。審查已複驗該指示正確且在行號漂移後仍成立。

### 2.2 比對粒度與失敗輸出（`[Q2]`=A）

**設計決定 `D-5`：比對 `(role, story_id, can_view, can_edit, can_review)` 的 tuple 集合，
失敗時輸出三段 diff。**

| 段 | 內容 | 它對應的漂移原因 |
|---|---|---|
| 1 | 只在 SQL 的列 | Python 那份漏加 |
| 2 | 只在 Python 的列 | SQL 那份漏加 |
| 3 | 兩邊都有但旗標不同的列 | **值不同——最危險的那一類** |

每段最多列前 **10** 筆並附該段總數。

**為什麼第三段不能省**（`[Q2]` 的選項 C 被否決的理由）：只比列數與 story id 集合
會讓「列在、但旗標不同」整類漏掉，而那正是「同一個角色在不同環境有不同權限」
的形狀——`SEC-5` 存在的全部理由。

**為什麼不用 `assertEqual` 的預設輸出**（選項 B）：352 個元素的集合不等時，
`unittest` 會印出完整的兩個集合。這支測試紅燈的時機正是最需要快速定位的時候，
而那個輸出實務上無法判讀。

### 2.3 既有樣板

`U4` 的 `backend/tests/test_hierarchy_migration.py:454`
（`test_schema_rbac_sql_matches_migration_ddl`）已有「解析 `schema_rbac.sql`
再與程式內定義比對」的形狀，其 `@note` 逐字說明它**不比對型別與約束**
（那需要真的 PostgreSQL）。本單元的比對對象是 seed **資料**而非 DDL，
故不需要資料庫——這是本單元與 `U4` 的差別，也是 `NFR6`（真實 PG CI job）
對本單元判定 N/A 的設計依據。

---

## 三、可稽核性設計（`SEC-4`）—— log 成為受測契約

### 3.1 現況與要改的

| | 現況（實測） |
|---|---|
| `rbac.py:110` | `logger.info("ensure_missing_role_permissions: inserted %d rows", inserted)` |
| `database.py:186` | 同一句話的第二次（呼叫端另外記一次） |
| 記錄內容 | **只有一個數字** |

既有環境補進 44 列之後，日誌說「插了 44 列」，而**沒有任何方式確認那 44 列
是不是 `K1`–`K4` 的**。

### 3.2 設計決定（`[Q1]`=A）

**設計決定 `D-6`：一行彙總、層級 `INFO`、內容含被插入的 `(role, story_id)` 配對。**
形狀示意（**非實作**，實際字串由 `code-generation` 定稿）：

```
ensure_missing_role_permissions: inserted 44 rows:
  Project_Architect/K1, Developer/K1, ..., Platform_Owner/K4
```

不採逐列一行（`[Q1]` 的選項 C）：既有環境首次啟動會刷 44 行 `INFO`，
而斷言「44 行」會把一個**會變的數字**變成受測契約——矩陣日後再成長就得改測試。

**設計決定 `D-7`：該 log 由測試以 `assertLogs` 斷言，斷言對象是四個新 story id 的字串。**
這是本站把 `SEC-4` 由「一句要求」升為**受測契約**的那一步。

| | 內容 |
|---|---|
| 斷言 | `assertLogs(logger="cloud360.rbac" 或實際 logger 名, level="INFO")` 捕捉後，斷言 `K1`／`K2`／`K3`／`K4` 四個字串都出現在捕捉到的訊息中 |
| **突變驗證** | 把 log 改回只記列數 → 該斷言必須紅。這是它存在的唯一證明方式 |
| 落點 | 與 `U3-V1`–`U3-V5` **同一支測試檔**（都只需要 `DEFAULT_ROLE_PERMISSIONS` 與一次 seed 呼叫） |

**設計決定 `D-8`（必須明寫，否則會被誤讀為測試壞了）：
log 的文字格式自此成為受測契約。** 改 log 文案會讓 `D-7` 的斷言紅燈。
這是刻意的——`SEC-4` 的價值在於那行字的**內容**，而不在於它存在。
斷言只綁四個 story id 的字串、不綁整句措辭，已是最寬鬆的綁法。

### 3.3 不收斂的既有重複

`database.py:186` 在呼叫之後**另外**記了一次裸列數。改完之後同一次 seed 事件會
同時出現「詳細清單」與「裸列數」。

**設計決定 `D-9`：不收斂它。** 動 `database.py` 的 log 超出 `[Q2]`=A 的範圍，
且不影響 `D-7` 的斷言（詳細字串仍在）。已在
`tech-stack-decisions.md §二` 第 5 列向實作者揭露，本檔重申它**不是**本單元造成的。

---

## 四、可達性保證的驗證設計（`U3-V1`–`U3-V5`）

五條都是對 `DEFAULT_ROLE_PERMISSIONS` 的純解析斷言，零新依賴、不需資料庫。

**設計決定 `D-10`：五條與 `SEC-5`、`D-7` 共用同一支測試檔。**
理由：三者都只需要「解析 `DEFAULT_ROLE_PERMISSIONS`」這一份邏輯，
分檔會把同一份解析寫三次——而 `team.md` 的「單一真實來源」正是本單元在防的東西，
在它自己的測試裡製造三份副本是自相矛盾。

| ID | 斷言 | 突變（驗它會紅） |
|---|---|---|
| `U3-V1` | 存在角色持有 `A1` view 但不持有 `K3` 任何旗標 | 把 `SRE` 的 `K3` 列改為 `(True, False, False)` |
| `U3-V2` | 存在角色不持有 `K4` 任何旗標 | 同上，改 `K4` |
| `U3-V3` | 每個持有 `K2.edit` 的角色，`K3.edit` 亦為 true | 把 `Project_Architect` 的 `K3` 改為 `(True, False, False)` |
| `U3-V4` | 長度 352 **且**組合完整 | **兩個突變都要驗**：刪一列（長度紅）／把一列的 `story_id` 由 `K4` 改成 `K3`（長度仍 352、組合紅） |
| `U3-V5` | 四個新 id 的 `can_review` 全為 false | 把任一列第三個旗標改為 `True` |

**設計決定 `D-11`：`U3-V4` 必須有兩個突變。** 只驗長度會漏掉「列數對但組合有缺漏」
——缺的那格在權限頁是破洞而總數看起來正常，而 `BR3.4`′ 逐字要求「同時驗總數**與**
組合完整性」。

**設計決定 `D-12`：五條的失敗訊息必須說出它保護的是哪一條 AC。**
理由：這五條是**結構約束**，它們紅燈時的現象（「某個角色的旗標跟預期不同」）
看起來像測試太嚴，而不是像缺陷。不寫出「這會讓 `AC12.5.1` 變成死碼」，
下一個人會把它當噪音刪掉——`U4` 的 `D-4-revisit` 記過同一個形狀
（「無 id 的旁述沒有人會回頭看」）。

---

## 五、對 `U19` 的具名交接（`U3-A1`–`U3-A3`，`[Q3]`=A）

**設計決定 `D-13`：不機械強制，在三處留下可追溯的錨點。**

| 錨點 | 位置 |
|---|---|
| 1 | 本節（`security-design.md` 的具名交接段） |
| 2 | `traceability.json` 的 `reverse` 列（`U3-A1`–`U3-A3` 各一列） |
| 3 | `U3-D1` 旁的指向（部署同步那一列附註「授權行為的驗證不在本單元」） |

| ID | 要求 `U19` 覆蓋的行為 | 來源 |
|---|---|---|
| `U3-A1` | 邀為一般成員：持有 `K3.view` → 成功；不持有 → 拒絕且不寫入任何列 | `BR7.1`、`AC12.5.1`、`AC12.5.3` |
| `U3-A2` | 邀／改為專案管理者：持有 `K3.edit` → 成功；只有 `K3.view` → 拒絕 | `BR7.2`、`AC12.2.1` |
| `U3-A3` | 自動改選候選集合只含 `K3.edit` 持有者；無人符合則擋下停用 | `BR7.3`、`AC12.4.x`、`[M3]`=A |

**`U3-A2` 的 deny 側可構造性已實算**：持有 `K3.view` 而無 `K3.edit` 的角色為
**4 個**（`Developer`／`FinOps_Analyst`／`Security_Reviewer`／`Platform_Owner`）。

**設計決定 `D-14`：不在 `U3` 寫「斷言 `U19` 的測試存在」的測試。**
`[Q3]` 的選項 B 被否決的理由要留在設計裡：那支測試在 `U19` 施工之前必定紅燈，
而 CI 每個 PR 都跑——等於讓本單元的 PR 無法合併，除非 `U19` 先做完。
那會把一條**交接義務**變成一條**反向的依賴邊**，與
`unit-of-work-dependency.md` 的 DAG 矛盾（`U19` 依賴 `U3`，不是反過來）。

**殘餘風險（照實記載）**：這三條確實可能落空。`H-10` 已記載
`unit-of-work-story-map.md` 沒有把 `US12` 任何一則指給 `U3`，所以它們在追溯上
**沒有第二個支點**。若 `U19` 的設計站沒有承接，那是 `U19` 的缺口而非 `U3` 的
——但「是誰的缺口」不影響「它會不會發生」。

**設計決定 `D-15`：`BR7.4` 的 PBT 義務一併交接，不得掉落。**
`AC12.4.2` 的挑選純函式不讀 DB、`K3.edit` 旗標由呼叫端傳入，
而真正可失敗的性質是**排列不變性**（`ORDER BY joined_at` 在時間戳相同時
沒有穩定順序），不是「同一組輸入選出同一人」那個恆真命題。
本單元的 `calculation` 類規則實算為 0，故 PBT 對 `U3` 判定 N/A
——但那個 N/A **不等於整個 intent 沒有 PBT 標的**，標的在 `U19`。

---

## 六、`RR-1` 的承接形式（`/roles/catalog` 的 DoS 面）

`nfr-requirements` `[Q1]`=A 把它指派 `operation` 階段。**本站補上一件事：
那個指派需要一個具體的落點，否則是死指派。**

| 項目 | 內容 |
|---|---|
| 風險 | 未驗證身分、每次 11 次查詢、零 rate limiting |
| 本單元的影響 | 每次回應多 4 列；**不改變可觸發性** |
| `operation` 階段的候選落點 | `observability-setup`（4.4）或 `feedback-optimization`（4.7） |
| **已查證**（`aidlc-state.md` ＋ 編譯後的 stage graph） | `4.4` = `observability-setup`，在 `Stages to Execute` 內；`4.7` = `feedback-optimization`，**已明文列在 `Stages to Skip`**。兩者的 `execution` 皆為 **`CONDITIONAL`** |

**設計決定 `D-16`：`RR-1` 的承接站指定為 `observability-setup`（4.4），
不指 `feedback-optimization`（4.7）。** 理由是後者已被本工作流程明文 skip
（`aidlc-state.md` 的 `Stages to Skip` 逐字含 `4.7 (feedback-optimization)`），
指它就是死指派——這是本 record 已記過三次的形狀。
承接形式：把「`/roles/catalog` 的呼叫率與延遲」列為一個有門檻的觀測項，
而不是要求它在本 intent 內被加固。

**但 `4.4` 自己也是 `CONDITIONAL`，所以這個指派仍可能落空**（本 record 已有三次
指派落空的實例）。故第二層承接：若 `observability-setup` 被 skip，
判定 skip 的執行者必須把 `RR-1` 重新提交給使用者裁決，**不得默認它已被處理**
——`project.md` 逐字要求「找不到誠實的轉移目標時寫『無自然承接站』並指定屆時
判定 skip 的 conductor 重新提交」。本項不是「無自然承接站」（4.4 存在且在執行清單內），
但它的 `CONDITIONAL` 使同一條補救規則適用。

---

## 七、ADR-0006 四面向（設計層的逐項落實）

| 面向 | `nfr-requirements` 的判定 | 本站的設計落實 |
|---|---|---|
| **IAM** | 適用（核心） | `D-1`（不提供讀取端）、`D-3`（兩層的主體不同）、`D-5`（完整性比對）、`D-10`–`D-12`（可達性保證的驗證）、`D-13`–`D-15`（授權行為的交接） |
| **Encryption** | 不適用 | 無設計——本單元不新增欄位、不儲存機密值。與 `functional-spec.md §六′` 一致 |
| **Network exposure** | **適用（一處）** | `D-16`（`RR-1` 的承接站由 `operation` 收窄為 `observability-setup`，並說明為何不指 4.7）。**本站不宣稱該面向已處置**，只讓它的指派不落空 |
| **Audit logging** | 適用（本站收為需求） | `D-6`–`D-9`（log 形狀、斷言、突變、不收斂既有重複）。**仍未處置**：`BR7.1`–`BR7.3` 的拒絕事件稽核由 `H-8` 指派 `U19` |

## 八、本站明確不做的事

- 不設計任何認證流程、加密方案、安全標頭、輸入驗證——本單元零端點零畫面。
- 不設計 rate limiting（`[Q1]`=A 已把 `RR-1` 定為接受；`D-16` 只處理它的承接）。
- 不回改 `contract-summary.md` 的 `K-03`（`[Q3]` 的選項 C 被否決）。
- 不在 `U3` 斷言 `U19` 的測試存在（`D-14`）。
- 不收斂 `database.py:186` 的重複 log（`D-9`）。
