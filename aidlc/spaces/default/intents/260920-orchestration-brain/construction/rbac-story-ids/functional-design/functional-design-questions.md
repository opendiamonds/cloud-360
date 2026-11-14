# Functional Design 問題檔 — `U3 rbac-story-ids`（`spec`）

<!-- Stage: functional-design（Construction 3.1）· Unit: rbac-story-ids · kind: spec -->

## 前言

本單元交付的是 **`K1`／`K2` 兩個 story id 的 seed 語意**，不含任何端點與畫面
（端點在 `U7 hierarchy-service`，畫面在 `U14 entry-page-ui`／`U16 object-picker-ui`）。

### 已由上游定案、本站不重問

| 事項 | 定案 | 來源（逐字核對過） |
|---|---|---|
| story id 用 `K1`／`K2` 兩個、字首為 `K` | 已定案 | `decisions.md` ADR-004「Decision」段 |
| 不拆成三個 id（專案與系統分開） | 已拒絕 | ADR-004「Alternatives Rejected」第三項 |
| 不併入 `A` 字首 | 已拒絕 | ADR-004「Alternatives Rejected」第一項 |
| 寫入端為 `ensure_missing_role_permissions`，**不可**用 `ensure_role_permissions_seeded(force=False)` | 已定案 | `K-03` 的 `forbidden` 段；`rbac.py:63–65` 實證該函式在表非空時整段 no-op |
| 矩陣由 308 列增為 330 列 | 已定案 | ADR-004；本站實算複驗：`DEFAULT_ROLE_PERMISSIONS` 長度 308 ＝ 11 角色 × 28 story id |
| `schema_rbac.sql` ＋ `DEPLOY.md` 同步為 blocking | 已定案 | `project.md ## Mandated`；`K-03` 的 `sync_obligations` |
| allow/deny 雙向 TestClient 為交付條件 | 已定案 | `team.md ## Testing Posture` A 規則；`stories.md` US1 群 DoD |
| `/memory` 不需要 story id | 已定案 | ADR-004 Context 段引 `[DM:D1]`=C |

**本站唯一未定的是 22 列的預設值**——`components.md:510–511` 逐字把它留給
`functional-design`：「各角色的預設值（11 × 2 ＝ 22 列）留給 `functional-design`
與 `schema_rbac.sql` 的同步一併定案」。

### 本站查證到的三件事實（供題幹與選項引用，非上游來源）

1. **`user_can` 的 `view` 是 OR 語意**：`rbac.py:152–153` 為
   `if action == "view": return bool(row.can_view or row.can_edit or row.can_review)`。
   故「給 edit 不給 view」無法表達；而「完全不持有」＝三個旗標皆 `False`。
2. **全部 11 個角色都有 `A1` view**，這是 `AC1.4.4` 被改寫的原因（原 Given 在預設
   seed 下不可達）。同一個陷阱現在落在 `AC1.4.2` 上：它的 Given 是「**不**持有入口頁
   權限但持有架構圖權限」，**若 `K1` 給滿 11 個角色，這條 AC 立刻變成不可達的死碼**。
3. **既有 seed 已有「全 `False` 列」的前例**：`('FinOps_Analyst', 'A3', False, False, False)`。
   故「不持有」的表達方式是**列存在、旗標全 `False`**，矩陣仍為 330 列。

### 本輪新增的輸入：Figma 設計檔（`ecYwIVWjHESXzaQRyLphix`）

使用者於本站進行中提供。四個框架皆已實讀（非讀圖層名推斷）。與本單元相關的一項：
`首頁`（`53:2`）的副標逐字為「**目前處於唯讀分享模式。您可以點擊下方引導分類或
請求編輯權限解鎖完整 AI 互動能力。**」，右上另有「進入編輯模式」按鈕。

這使 `K1` 是否需要 `can_edit` 成為真實問題（見 Q1）。其餘四項落差
（脈絡列、工作項常駐區、八張能力卡、記憶入口）經人工裁決**不在本站處理**，
寫入 `functional-spec.md` 的交接事項交給 `U14 entry-page-ui`。

---

## Q1. `K1` 需不需要 `can_edit`？

`FR1.8` 與 `US1.4` 全部只談「持不持有入口頁權限」，沒有區分模式。Figma 的
「唯讀分享模式／請求編輯權限」有兩種讀法，指向不同設計。

- **A**：`K1` 雙態 — `can_view` ＝ 能開入口頁（讀對話、看候選卡），`can_edit` ＝ 能送出
  需求給大腦。與既有 `A1` 同形（view ＝ 看被分享的圖，edit ＝ 能改／能用 AI）。
- **B**：`K1` 只有 `can_view`，`can_edit` 恆 `False` — 唯讀模式是**per-object 的對話分享**
  （與 `diagram_shares` 同形），屬 `U10`／`U13` 的對話分享，不是角色層權限。
- **C**：唯讀模式 ＝ 既有的「授權申請」過渡態（Sidebar 已有該項）。
- **D**：本輪 `K1` 只做 `can_view`，雙態列為 `U14` 的開放決策。

[Answer]: Figma不一定是對的，可以重新設計（**重新框定，非選項之一**）

**作答後果**：使用者未選 A–D，而是**把 Figma 從約束降為參考**。依 `project.md`
的既有教訓（使用者以重新框定回覆時，先查證再決定採納或追問），本站的處置是：

1. **`K1` 設計為 view-only**——`can_edit`／`can_review` 於 11 列皆恆 `False`。
   理由**不是** Figma，而是上游本身：`FR1.8` 與 `US1.4` 四條 AC 全部只談「持不持有
   入口頁權限」，**沒有任何一處要求唯讀／編輯雙態**；且 `mockups.md:117` 逐字記載
   「無權限者看到的入口頁長什麼樣」該狀態**不可達**（`[R8]` 明寫不存在無權限的入口頁），
   與「唯讀入口頁」直接相斥。加一個沒有上游需求的旗標屬臆測性設計。
2. **`user_can` 的 OR 語意讓 `K1.can_edit` 沒有可表達的獨立語意**：`rbac.py:152–153`
   使 `edit=True` 必然蘊含 `view=True`，故 `K1.edit` 唯一的效果是在權限頁多一個
   對「能不能進頁」毫無意義的勾選框。
3. **Figma 的「唯讀分享模式／請求編輯權限」不採納為需求**，改記為 `U14
   entry-page-ui` 的開放決策 `OQ-K1`。若 `U14` 日後決定要雙態，`K1` 的 seed 要再改
   一次，並再觸發一次 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步——此代價
   已在提問時以選項 D 的形式揭露過。

---

## Q2. `K1` 的 11 列預設值

至少一個正式角色**不得**持有 `K1`，否則 `AC1.4.2` 成為死碼（見前言事實 2）。

- **A**：8 個持有（`Project_Architect`、`Developer`、`Project_Editor`、`Project_Admin`、
  `FinOps_Analyst`、`Security_Reviewer`、`Platform_Admin`、`Platform_Owner`）；
  3 個不持有（`SRE`、`Ops_Lead`、`Platform_Engineer`）。
- **B**：全部 11 個持有 → `AC1.4.2` 永久不可達。
- **C**：只有 4 個核心角色持有；其餘 7 個不持有。
- **D**：依 edit 能力推導 — 持有 `A1`／`A3`／`C1` 任一 edit 的 7 個角色持有，
  `Platform_Owner` 因全域唯讀而不在內。

[Answer]: A — 8 個持有；3 個不持有（`SRE`、`Ops_Lead`、`Platform_Engineer`）

**作答後果**：三個不持有的角色其 `K1` 列存在但旗標全 `False`（沿用
`('FinOps_Analyst','A3',False,False,False)` 的既有前例），矩陣仍為 330 列。
三者皆有 `A1` view，故 `AC1.4.2` 的 Given「不持有入口頁權限但持有架構圖權限」
可構造、該 AC 可達可測——這正是 `AC1.4.4` 當初被改寫要避免的缺陷類型。

---

## Q3. `K2` 的 `can_view` 與 `can_edit` 分配

`can_edit` 涵蓋建立／修改／刪除（見 Q4）。注意 `view` 的 OR 語意：給 edit 必然有 view。

- **A**：`can_view` 給全部 11（誰都要看得到自己的圖歸在哪，否則脈絡列無資料）；
  `can_edit` 給 4 個（`Project_Architect`、`Project_Editor`、`Project_Admin`、`Platform_Admin`）。
  `Platform_Owner` 維持既有矩陣裡「全域唯讀」的一致形狀。
- **B**：`can_view` 全部 11；`can_edit` 給持有 `A1` edit 的 3 個 ＋ `Platform_Admin`。
- **C**：`can_view` 與 `can_edit` 同一組，與 `K1` 的 8 個一致。
- **D**：`can_view` 全部 11；`can_edit` 只給 `Platform_Admin`、`Platform_Owner`。

[Answer]: A — `can_view` 給全部 11；`can_edit` 給 4 個（`Project_Architect`、`Project_Editor`、`Project_Admin`、`Platform_Admin`）

**作答後果**：`AC9.2.3`（不具權限者嘗試建立被拒）的 Given 可構造——7 個角色
不具 `K2.edit`。`Platform_Owner` 看得到階層但不能改，與它在既有 28 個 story id
上全為 `v--` 的形狀一致。`can_view` 給滿是因為脈絡列要顯示三元組，看不到歸屬
就顯示不出來。

---

## Q4. 刪除要不要與建立／修改分開閘門？

`U7` 交付讀／建／改／刪四種操作，全經 `require_story_action(K2)`。

- **A**：不分開，`K2.edit` 同時涵蓋建立、修改、刪除。
- **B**：用 `can_review` 當刪除閘門（三個旗標各對一組動作）。
- **C**：刪除另在 service 層限制為 `Platform_Admin`，不進矩陣。
- **D**：刪除要求「其下已無系統／架構圖」的結構前提，權限上不再細分。

[Answer]: A — 不分開，由 `K2.edit` 涵蓋建立／修改／刪除

**作答後果**：`can_review` 在 `K1`／`K2` 兩列皆恆 `False`，其既有語意
（`A3` 的 `Security_Reviewer` 審核）不被挪用。使用者**未**同時選「非空不可刪」
的結構前提，故本站**不**寫入該規則；刪除時既有資料的處置改記為 `U7` 的開放
決策 `OQ-K2`（`K-04` 的 `known_threat_to_the_invariant` `DG-2` 已在追蹤同一件事：
Project／System 刪除的 cascade 行為未定會讓 `system_id` 懸空）。

---

# 修訂 1（2026-10-04）— `K3`／`K4` 兩個新 story id，矩陣 330 → 352

<!-- 本段為 append。Q1–Q4 的題幹、選項與作答**一律不回改**（`refined-mockups:c3`）：
     它們在 `K1`／`K2` 的範圍內仍然有效，本修訂只擴充到新增的兩個 story id。 -->

## 觸發

2026-09-28T16:16:53Z 的回跳（`functional-design` → `scope-definition`）把本單元的
四份產出與其 `#Review` 一併標為 invalidated，並在其後的修訂鏈中擴大了本單元的責任：

| 來源 | 逐字內容 |
|---|---|
| `[UG:G8]`=C | 新增 `K3`（專案成員管理）＋ `K4`（需求欄位）；「`FR12.6a` 的『對應全域功能權限』自此有明確所指——**成員頁對應 `K3`、需求欄位對應 `K4`**」 |
| `unit-of-work.md` 修訂的「既有單元的四處變更」 | `U3` 責任由兩個 story id 擴為四個；矩陣由 330 增為 **352** 列（11 角色 × 32 story id），「此為算式結果，施工時須以 `rbac_seed_data.py` 的實際角色數複算，不得照抄」 |
| `contract-summary.md` 修訂 1 的「既有四條的消費端擴充」 | `K-03` 的消費端由 `U7`／`U14` 擴為再加 `U19`／`U23`／`U24` |

**本站已複算，不照抄**：`DEFAULT_ROLE_PERMISSIONS` 實測 **308** 列 ＝ 11 角色 ×
28 story id（組合完整，無缺漏）。故 308 ＋ 11×4 ＝ **352**，算式成立。

## 已由上游定案、本修訂不重問

| 事項 | 定案 | 來源（逐字核對過） |
|---|---|---|
| 新增兩個 id 而非一個或零個 | 已定案 | `[UG:G8]`=C（A 沿用 `K2`、B 只加 `K3` 皆已被否決） |
| `K3` 對應成員頁、`K4` 對應需求欄位 | 已定案 | `[UG:G8]`=C 作答註解逐字 |
| 不另開新單元、仍由 `U3` 擁有 | 已定案 | 同上 `(1)`：story id 的資料擁有者與驗證方式相同，另開會讓兩個單元同時改三份檔 |
| 缺全域權限者**不得**被邀請（非僅警示） | 已定案 | `[RA-2]`=C → `FR12.6a` |
| 寫入端、冪等、兩份 seed 同步、allow/deny 雙向 | 已定案 | `BR3.1`–`BR3.3`、`BR4.1`–`BR4.4`（Q1–Q4 已涵蓋，對新兩個 id 原樣適用） |

## 本修訂查證到的五件事實（供題幹與選項引用，非上游來源）

1. **`K2.edit` 的四個持有者就是「能建立專案」的集合**：`Project_Architect`、
   `Project_Editor`、`Project_Admin`、`Platform_Admin`（Q3=A）。而 `AC12.1.2` 逐字
   「**Given** 我剛建立一個專案，**When** 我嘗試邀請成員，**Then** 該動作可用——
   **不需任何額外授權步驟**」。在 `FR12.6` 的兩層串聯下，這四個角色**必須**持有
   `K3.edit`，否則該 AC 直接失敗。**這是推導出的硬約束，不是選項。**
2. **`J3a`／`J3b`（系統管理群）是既有唯一的「管理類」先例**，本站實算：`J3a` 持有者
   4 個（`Project_Admin`、`Security_Reviewer`、`Platform_Admin`、`Platform_Owner`）、
   `edit` 2 個（`Project_Admin`、`Platform_Admin`）；`J3b` 持有者 3、`edit` 2。
   它比 `K1`／`K2` 窄得多——但套到 `K3` 會違反事實 1。
3. **`Platform_Owner` 的 `edit` 只有一個：`J1`**（登入能力）。它另有 `can_review`
   於 `F3`／`H2`。**故 Q3 作答註解與 `BR2.2` note 逐字寫的「`Platform_Owner` 在既有
   28 個 story id 上全為 `v--`」不成立**——`J1` 是 `ve-`，`F3`／`H2` 是 `v-r`。
   依 `functional-design:c22`：**決定不改、只修理由**，更正後的理由是「`Platform_Owner`
   唯一的 `edit` 是登入能力 `J1`，給它實質的寫入權會是第一次」。
4. **`K-19` 與 `[UG:G8]` 對 `K4` 的範圍不一致**：`K-19` 的
   `authorization_responsibility` 逐字「頁面自身的可見性把關由 `K-03` 的 `K4`
   story id 承擔」，而它的 `test_target_surface.routes` 是「專案／系統清單頁、
   建立頁、專案詳情頁（總覽／需求／記憶摘要三籤）」——即**整個專案頁**；
   但 `[UG:G8]`=C 只說 `K4` 對應**需求欄位**。兩者都已核可，Q6 須定錨。
5. **`AC12.5.1` 的 Given 需要「一位沒有對應全域功能權限的使用者」**。若該權限在
   預設 seed 下由全部 11 個角色持有，這條 AC 立刻變成不可達的死碼——與 `BR1.3`
   要防的缺陷**完全同形**（`AC1.4.2` 的前例）。

---

## Q5. `K3`（專案成員管理）的 11 列預設值

硬約束（上方事實 1，不列為選項）：`Project_Architect`、`Project_Editor`、
`Project_Admin`、`Platform_Admin` **必須**持有 `K3.edit`。
硬約束（上方事實 5）：**至少一個角色必須完全不持有 `K3`**。

- **A（建議）：`view` 給 8 個、`edit` 給 4 個。**
  `view` ＝ `K1` 的同八個角色（`Project_Architect`、`Developer`、`Project_Editor`、
  `Project_Admin`、`FinOps_Analyst`、`Security_Reviewer`、`Platform_Admin`、
  `Platform_Owner`）；`edit` ＝ 四個建立者角色。`SRE`／`Ops_Lead`／
  `Platform_Engineer` 三旗標全 `false`。
  **理由**：與 `K1` 的持有者集合逐字相同，使「誰是這個產品裡的專案參與者」只有
  一個答案；三個不持有者同時滿足 `BR1.3`（他們都有 `A1` view）與事實 5。
  **代價**：`SRE`／`Ops_Lead`／`Platform_Engineer` 永遠無法被邀請進任何專案——
  `FR12.6b` 的入職順序限制對他們不是順序問題而是**永久排除**，除非管理者在權限頁
  手動給他們 `K3`。
- **B：`view` 給 11 個、`edit` 給 4 個。** 全員看得到成員清單，只有建立者角色能管。
  **代價**：**`AC12.5.1` 的 Given 不可構造**（事實 5）——沒有任何角色缺少 `K3`，
  該 AC 成為不會失敗的死碼。`AC1.4.2` 已經踩過這個坑一次。
- **C：跟 `J3a`／`J3b` 同形——`view` 給 4 個、`edit` 給 2 個。**
  `view` ＝ `Project_Admin`、`Security_Reviewer`、`Platform_Admin`、`Platform_Owner`；
  `edit` ＝ `Project_Admin`、`Platform_Admin`。
  **代價**：**違反事實 1 的硬約束**——`Project_Architect` 與 `Project_Editor` 能建立
  專案卻不能管理自己建的專案的成員，`AC12.1.2`（「不需任何額外授權步驟」）失敗。
- **D：`view` 給 8 個、`edit` 給 6 個**（四個建立者 ＋ `Security_Reviewer` ＋
  `Platform_Owner`）。
  **代價**：違反上方事實 3 的既有形狀——`Platform_Owner` 的唯一 `edit` 是 `J1`，
  而 `Security_Reviewer` 的 `edit` 全部落在審核面（`A3`／`B3`／`D2`／`D3`／`G*`），
  成員管理不在其中。多兩個例外而換不到任何 AC 的可構造性。

[Answer]: A — `view` 給 8 個（同 `K1` 持有者集合）、`edit` 給 4 個（建立者角色）  <!-- 2026-10-04T11:06:50Z | Mode: guided | 修訂 1 -->

**作答後果**：`SRE`／`Ops_Lead`／`Platform_Engineer` 三列三旗標全 `false`，使
`AC12.5.1` 的 Given（一位沒有對應全域功能權限的使用者）可構造——與 `BR1.3` 同一
形狀的可達性保證，落在 `K3` 上。四個建立者角色持有 `edit`，`AC12.1.2`
（建立者邀請成員「不需任何額外授權步驟」）成立。代價已向使用者揭露：那三個
維運角色在預設值下**永久**無法被邀請進任何專案，須管理者在權限頁手動授予。

---

## Q6. `K4`（需求欄位）的把關範圍與 11 列預設值

上方事實 4 的不一致必須在此定錨：`K4` 把關的是**整個專案頁**，還是**只有需求籤**？

- **A（建議）：只把關需求籤；`view` 給 8 個（同 `K1`／`K3`）、`edit` 給 4 個
  （建立者角色）。** 專案／系統清單頁、建立頁與總覽籤由 `K2` 把關（`K2.view`
  已給全部 11，Q3=A），需求籤與其欄位讀寫由 `K4` 把關。
  **理由**：貼合 `[UG:G8]`=C 的逐字（「需求欄位對應 `K4`」）與它選 C 的目的
  （「可以讓一個人能填需求欄位但完全看不到成員清單，或反之」）；需求欄位是
  **架構假設**（SLA／TPS／預算），`team.md` 的 C1 既有先例逐字「估價區域與每日
  時數同屬架構假設：由架構師設定／修改」，四個建立者角色正是架構編輯者集合。
  **代價**：`K-19` 的 `authorization_responsibility` 字面被收窄為「需求籤」，須在
  本站產出就地記明為對齊修正（不回改已核可的 `contract-summary.md`）。另：
  `AC11.3.1`／`AC11.3.2` 的未填計數顯示在**總覽籤**（`K2`），明細在需求籤（`K4`），
  故一位有 `K2` 無 `K4` 的人會看到計數卻看不到明細——須在本站明訂該情形下
  計數也不顯示。
- **B：把關整個專案頁；`view` 給 11 個、`edit` 給 4 個。** 照 `K-19` 的字面，
  `K4` 等於「專案頁可見性」，而為了不讓任何人看不到專案頁，`view` 給滿。
  **代價**：`K4` 與 `K2.view`（也給滿 11）在全域層**完全重複**，`[UG:G8]`=C 的
  「全域邊界最細」整個落空——新增 `K4` 只換到一個永不拒絕的旗標。
- **C：只把關需求籤；`view` 給 4 個、`edit` 給 1 個（`Project_Architect`）。**
  最小權限：只有架構編輯者看得到並改得動架構假設。
  **代價**：`Project_Editor`／`Project_Admin`／`Platform_Admin` 能建立系統卻看不到
  它的需求籤；且 `AC11.2.1`（未填須有文字標示）的 Given 對其餘七個角色不可構造，
  `U23` 的 e2e 只能用單一角色跑。
- **D：把關整個專案頁；`view` 給 8 個、`edit` 給 4 個。**
  **代價**：一位只有 `K2` 沒有 `K4` 的人（三個維運角色）看不到專案頁，但
  `K2.view` 已給他們「看得到階層」——`BR2.1` 的理由逐字是「不給 view 的角色看不到
  自己的架構圖歸屬於哪個專案／系統」，而專案頁正是看那件事的地方。兩條已核可的
  規則會在同一個畫面上互相抵消。

[Answer]: A — 只把關需求籤；`view` 給 8 個、`edit` 給 4 個  <!-- 2026-10-04T11:06:50Z | Mode: guided | 修訂 1 -->

**作答後果**：三件事隨之定案。(1) `K-19` 的 `authorization_responsibility`
（逐字「頁面自身的可見性把關由 `K-03` 的 `K4` story id 承擔」）在本站被收窄為
「需求籤」——依 `refined-mockups:c3` **不回改**已核可的 `contract-summary.md`，
就地記為對齊修正。(2) 清單頁、建立頁與總覽籤由 `K2` 把關（`K2.view` 已給全部 11）。
(3) 一位有 `K2` 無 `K4` 的使用者（三個維運角色）在總覽籤**不顯示**「未填需求欄位」
計數——否則他看得到數字卻看不到明細，`AC11.3.1`／`AC11.3.2` 的一致性斷言在他
身上無法驗證。這第三點是本站新增的明訂，寫成規則。

---

## Q7. 邀請與自動改選時，全域層要檢查什麼？

`[UG:G8]`=C 定了「成員頁對應 `K3`」，但沒定**邀請一個人時檢查他持有什麼**，
而 `AC12.5.1` 要求「畫面說明他缺少什麼」——這張清單必須有內容。
一併要定的是 `AC12.4.x` 的**自動改選**：它由系統發起、沒有邀請動作。

- **A（建議）：`K3.view` 為成員資格的前置、`K3.edit` 為「可成為專案管理者」的前置。**
  邀為一般成員 → 檢查 `K3.view`；邀為專案管理者 → 檢查 `K3.edit`；
  自動改選的候選集合**只含持有 `K3.edit` 的成員**，若無人符合則擋下停用並要求先
  指定接手人（沿用 `[M3]`=A 已核可的形狀）。
  **理由**：兩層串聯的全域層語意是「能不能用這個功能」，而「參與成員體系」與
  「管理成員」是不同強度的功能，`view`／`edit` 正好是矩陣既有的表達方式。
  **代價**：`AC12.4.2` 的純函式挑選要多一個輸入（候選者的全域 `K3.edit`），
  而該函式依 `units-generation` 的注意事項**不得讀 DB**——故該旗標必須由呼叫端
  查好後傳入，這一點要寫進本站產出給 `U19`。
- **B：只檢查「是否持有 `K3`」（`view`／`edit` 任一即算持有），不分角色。**
  **代價**：一位只有 `K3.view` 的人可被邀為專案管理者、或被自動改選為管理者，
  然後他的每一個管理動作都 403——`AC12.4.3` 的已核可文案「系統自動把管理權交給你」
  對他為假，而畫面上看不出原因。
- **C：檢查 `K3` 與 `K4` 兩者，缺任一即拒。**
  **代價**：`[UG:G8]`=C 想保留的細緻度（「能填需求欄位但看不到成員」或反之）在
  **邀請時**失效——兩個都要有才進得來；且仍未定「誰可以是管理者」那一面。
- **D：檢查 `K2`（專案／系統階層）。**
  **代價**：`K2.view` 已給全部 11（`BR2.1`，已核可），故**永不拒絕**——
  `AC12.5.1` 與 `AC12.5.3` 的 Given 皆不可構造，兩條 AC 一起變成死碼。

[Answer]: A — `K3.view` 為成員資格前置、`K3.edit` 為「可成為專案管理者」前置  <!-- 2026-10-04T11:06:50Z | Mode: guided | 修訂 1 -->

**作答後果**：邀為一般成員檢查 `K3.view`、邀為專案管理者檢查 `K3.edit`；
自動改選的候選集合只含持有 `K3.edit` 的成員，無人符合時擋下停用並要求先指定
接手人（沿用 `[M3]`=A）。`AC12.5.1` 的拒絕訊息要能分辨兩種情形（缺 `K3` 完全
不可加入 vs 有 `K3.view` 但不可當管理者）。**對 `U19` 的硬約束**：`AC12.4.2` 的
挑選函式依 `units-generation` 的注意事項不得讀 DB，故每個候選者的 `K3.edit`
旗標必須由呼叫端查好後作為輸入傳入——這會改變該純函式的簽章，寫進本站產出。
