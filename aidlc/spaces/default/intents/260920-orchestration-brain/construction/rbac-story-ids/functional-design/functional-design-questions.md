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
