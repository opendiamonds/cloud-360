# NFR Design 問題檔 — `U3 rbac-story-ids`（`spec`）

<!-- Stage: nfr-design（Construction 3.3）· Unit: rbac-story-ids · kind: spec -->

## 前言

`produces_kinds` 把 `performance-design`／`scalability-design`／`reliability-design`／
`observability-design`／`logical-components` 全部限定在 `service`／`ui`／`library` kind，
故本 `spec` 單元只產 **`security-design.md`** 與 **`traceability.json`**
——與 `U2`／`U4` 兩個 `spec` 單元相同（`U22` 多一份 `logical-components.md`，因為它是 `library`）。

`traceability.json` 的 `upstream_ids` 依本單元 `nfr-requirements` 實際產出的 id
（`SEC-1`–`SEC-6`、`U3-V1`–`U3-V5`、`U3-A1`–`U3-A3`、`U3-D1`），
**不是** `NFRx.y`——本單元的 11 條 inception NFR 全部判定 N/A，沒有父項可編子號。
此形狀沿用 `U4` 的既有先例（它的 `upstream_ids` 同樣是 `SEC-*` ＋ `U4-*`）。

### 已由上游定案、本站不重問

| 事項 | 定案 | 來源 |
|---|---|---|
| 四個 story id 的預設值與三條可達性保證 | 已定案 | `functional-design` 修訂 1 的 `BR5`／`BR6` |
| `SEC-4` 要記錄「哪些 `(role, story_id)`」而非只記列數 | 已定案 | `nfr-requirements` `[Q2]`=A |
| `RR-1`（`/roles/catalog` 的 DoS 面）接受並指派 `operation` | 已定案 | `nfr-requirements` `[Q1]`=A |
| 本單元自驗 seed 不變量、授權判定對 `U19` 具名 | 已定案 | `nfr-requirements` `[Q3]`=A |
| 零新依賴、零新容器、零新環境變數 | 已定案 | `tech-stack-decisions.md §一` |
| 加密面不適用、網路暴露面適用（一處） | 已定案 | `security-requirements.md §五` |

### 本站查證到的三件事實（供題幹與選項引用，非上游來源）

1. **`schema_rbac.sql` 只有一個 `INSERT INTO role_permissions` 區塊**，位於第 **445** 行、
   以第 **755** 行的 `;` 結束，其前第 **443** 行為 `DELETE FROM role_permissions;`。
   **沒有**被註解掉的 `INSERT`、**沒有** `ON CONFLICT` 子句、**沒有**第二個區塊
   ——我原先擔心的解析陷阱（C1 退役表的 `INSERT` 混入）實測不存在。
2. **`U4` 已有解析 `schema_rbac.sql` 的測試樣板**：
   `backend/tests/test_hierarchy_migration.py:454` 的
   `test_schema_rbac_sql_matches_migration_ddl`，其 `@note` 逐字說明它
   「不比對型別與約束——那需要一個真的 PostgreSQL」，只鎖「加了欄位卻只改一邊」。
3. **本 record 剛發生過「log 無斷言」的審查發現**：`U22 progress-channel` 的審查
   把「`code-summary.md` 自己寫接線斷掉的生產症狀是每則事件被記 ERROR 並丟棄，
   **所以那行 log 是清除契約被違反時唯一的痕跡**，而沒有任何斷言」列為實質發現。
   `SEC-4` 的 log 形狀與它同類。

---

## Q1. `SEC-4` 的 log 要不要有測試斷言？形狀為何？

`[Q2]`=A 已定「要記錄哪些 `(role, story_id)`」，但**沒有定它要不要被測試斷言**。
上方事實 3 的先例顯示：一行沒有斷言的 log，在契約被違反時不會讓任何東西紅燈。

- **A（建議）：要斷言，且與 `U3-V*` 同一支測試檔，用 `assertLogs`。**
  形狀：一行彙總（例如 `inserted 44 rows: Project_Architect/K1, Developer/K1, …`），
  層級 `INFO`（沿用既有的 `logger.info`）；測試以 `assertLogs` 捕捉並斷言
  **四個新 story id 的字串都在該行裡**。
  **理由**：`SEC-4` 的全部價值在於「既有環境補列後能驗證補對了什麼」——
  沒有斷言的話，日後有人把 log 改回只記列數，ADR-0006 的 audit 面會靜默退回缺口狀態。
  斷言成本為零（`assertLogs` 是標準庫，測試檔已存在）。
  **代價**：log 的**文字格式**自此成為受測契約，改格式會紅燈。這是刻意的
  ——但須在 `security-design.md` 明寫，否則下一個改 log 文案的人會以為測試壞了。
- **B：要記錄但不斷言。** 只在 `security-design.md` 寫明要求。
  **代價**：與 `U22` 審查抓到的形狀完全相同——`SEC-4` 會變成一句沒有任何機制保護的話。
- **C：改為逐列一行 log（44 行），並斷言行數。**
  **代價**：既有環境首次啟動刷 44 行 `INFO`；而斷言「44 行」會讓日後矩陣再成長時
  必須同步改測試——把一個會變的數字變成受測契約。
- **D：改記到稽核表而非 log，再斷言表的列數。**
  **代價**：本單元明文不建表（`functional-spec.md §八`），且使用者域目前沒有可讀的
  稽核表（`[US:Q-11]` 的 Critical）。這是 `nfr-requirements` `[Q2]` 的選項 D，已被否決。

[Answer]: A — 要斷言，與 `U3-V*` 同一支測試檔，用 `assertLogs`  <!-- 2026-10-04T12:30:15Z | Mode: guided -->

**作答後果**：`SEC-4` 由「一句要求」升為**受測契約**。設計面須明訂三件事：
(1) log 一行彙總、層級 `INFO`、內容含四個新 story id 的字串；
(2) 測試以 `assertLogs` 捕捉並斷言那四個字串都在；
(3) **log 的文字格式自此成為受測契約**——改格式會紅燈，這是刻意的，
須在 `security-design.md` 明寫，否則下一個改 log 文案的人會以為測試壞了。
斷言的突變驗證：把 log 改回只記列數 → 測試必須紅。

---

## Q2. `SEC-5` 的兩份副本比對，失敗時要輸出什麼？

解析本身不難（事實 1：單一區塊、無陷阱）。真正的設計問題是**失敗訊息**：
352 列的「兩個集合不相等」對讀測試輸出的人沒有任何幫助。

- **A（建議）：比對 tuple 集合，失敗時輸出三段 diff——只在 SQL 的列、只在 Python 的列、
  兩邊都有但旗標不同的列。**
  每段最多列出前 N 筆（例如 10）並附總數。
  **理由**：這個測試要防的失敗模式是**環境相依的無聲漂移**（新環境拿 SQL 那份、
  既有環境拿 Python 那份），而三段 diff 正好對應三種漂移原因
  （漏加、多加、值不同）。只說「不相等」會讓人從 352 列裡用肉眼找。
  **代價**：測試碼多約 15 行。
- **B：只斷言兩個集合相等，用 `assertEqual` 的預設輸出。**
  **代價**：`unittest` 對 352 元素的集合會印出完整的兩個集合，實務上無法判讀；
  而這支測試紅燈的時機正是最需要快速定位的時候。
- **C：只比對列數與 story id 集合，不比對旗標。**
  **代價**：漏掉最危險的那一類——**列在、但旗標不同**，也就是「同一個角色在不同環境
  有不同權限」。那正是 `SEC-5` 存在的理由。
- **D：比對整份檔案的雜湊。**
  **代價**：任何空白或註解改動都會紅燈，而兩份是不同語言的檔案、雜湊必然不同
  ——這條在形式上不成立。

[Answer]: A — 比對 tuple 集合，失敗時輸出三段 diff  <!-- 2026-10-04T12:30:15Z | Mode: guided -->

**作答後果**：三段分別為「只在 SQL 的列」、「只在 Python 的列」、
「兩邊都有但旗標不同的列」，各最多列前 10 筆並附總數。
三段對應三種漂移原因（漏加、多加、值不同），而第三種正是 `SEC-5` 存在的理由
——「同一個角色在不同環境有不同權限」。
解析範圍已實測固定：`schema_rbac.sql` 第 **445–755** 行的單一 `INSERT` 區塊，
無註解掉的 `INSERT`、無 `ON CONFLICT`、無第二個區塊。

---

## Q3. `U3-A1`–`U3-A3` 對 `U19` 的具名義務，要不要機械強制？

`SEC-6` 明載本單元對授權**判定**無可自驗的機械檢查。而 `H-10` 已記載
`unit-of-work-story-map.md` 沒有把 `US12` 任何一則指給 `U3`
——也就是說這三條義務在追溯上沒有第二個支點。

- **A（建議）：不機械強制，但在三處留下可追溯的錨點。**
  `security-design.md` 的具名交接段、`traceability.json` 的 `reverse` 列、
  以及 `U3-D1` 旁的一句指向——並明寫「若 `U19` 的 `nfr-requirements`／
  `functional-design` 沒有承接這三條，那是 `U19` 的缺口而非 `U3` 的」。
  **理由**：`U19` 是獨立單元、有自己的 stage 鏈與自己的審查；在 `U3` 寫一個
  「斷言 `U19` 的測試存在」的測試，會在 `U19` 還沒施工時就紅燈，
  而那是**依賴順序**而非缺陷。
  **代價**：這三條確實可能落空——與 `H-10` 同形的風險，已具名。
- **B：在 `U3` 寫一支測試，斷言 `backend/tests/` 內存在指定名稱的 `U19` 測試。**
  **代價**：`U19` 施工之前它必定紅燈，而 CI 是每個 PR 都跑的
  ——等於讓本單元的 PR 無法合併，除非 `U19` 先做完。那會把一條交接義務
  變成一條**反向的依賴邊**，與 `unit-of-work-dependency.md` 的 DAG 矛盾。
- **C：把這三條寫進 `contract-summary.md` 的 `K-03`。**
  **代價**：`K-03` 已核可（`contract-design` 的修訂 1 只擴充了它的消費端清單）。
  依 `refined-mockups:c3` 不回改已核可上游；且本站不是 contract 的所有者。
- **D：指派 `code-generation` 時再決定。**
  **代價**：`code-generation` 是本單元的最後一站，到那時 `U19` 的設計站可能都還沒跑
  ——決定權在那裡並不會比現在更充分，而延後只是讓錨點更晚落地。

[Answer]: A — 不機械強制，在三處留下可追溯的錨點  <!-- 2026-10-04T12:30:15Z | Mode: guided -->

**作答後果**：三處錨點為 `security-design.md` 的具名交接段、
`traceability.json` 的 `reverse` 列、以及 `U3-D1` 旁的指向；
並明寫「若 `U19` 的設計站沒有承接這三條，那是 `U19` 的缺口而非 `U3` 的」。
**選項 B 被否決的理由要寫進設計**：在 `U3` 斷言 `U19` 的測試存在，會在 `U19`
施工之前就讓每個 PR 紅燈——那把一條交接義務變成一條**反向依賴邊**，
與 `unit-of-work-dependency.md` 的 DAG 矛盾。
**殘餘風險照實記載**：這三條確實可能落空，與 `H-10` 同形，已具名。
