# 業務規則 — `U18 project-meta-data`

> 計數一律由 parser 解析本檔 yaml 區塊的 `rules[].id` 實算。
> 規則 id 前綴為 **`BR`**（框架的 `ID_PATTERNS.BR` 為 `/\bBR\d+\.\d+\b/`
> ——`U5` 那輪用 `BM` 前綴導致 13 條規則對 sensor 全部不存在，本檔不重犯）。

## 本檔的範圍

本單元是 `spec`：交付**三張表的 DDL**。下列規則**全部是資料層約束**，
沒有一條是應用層行為——本單元零程式碼、零端點、零畫面。

**不在本檔**：成員的邀請／移出／改選行為（契約 `K-16`，屬 `U19`）、
需求欄位的讀寫與清空行為（契約 `K-17`，屬 `U20`）。
契約 `K-15` 的 `authorization_responsibility` 逐字「**無**——DDL 在部署／啟動路徑
執行，不經使用者授權」。

```yaml
rules:
  # ---- BR1.x 三張表的語意承載欄位 ----
  - id: BR1.1
    statement: >
      `project_members.joined_at` **不得可為 null**。
    category: constraint
    applies_to: project_members.joined_at
    trigger: 建表時
    logic: NOT NULL，無預設值由寫入端提供（或 DEFAULT now()）。
    violation_behaviour: >
      `FR12.4` 的自動改選規則（挑最早加入者）**直接讀它**，平手時與 `user_id`
      組成決定性 tie-break。可為 null 會讓挑選**在空值上無序**
      ——每次改選可能選出不同人，而這是**靜默的**：沒有錯誤，只有不穩定的結果。
    source: 契約 `K-15` 的 `columns_that_carry_semantics` 逐字

  - id: BR1.2
    statement: >
      `reselection_events.acknowledged_at` 以**事件**為鍵，不是 per-user 布林值。
    category: constraint
    applies_to: reselection_events
    trigger: 建表時
    logic: >
      每次改選插入一列；`acknowledged_at` 為該**事件**的確認時間。
      **不得**以 (project_id, user_id) 的布林旗標取代。
    violation_behaviour: >
      per-user 布林值會讓同一人**第二次**被改選時看不到橫幅
      ——而那正是 `FR12.4c` 要防的情境（契約 `K-15` 逐字）。
    source: 契約 `K-15`

  - id: BR1.3
    statement: >
      `system_requirement_fields.value` **必須可為 null**。
    category: constraint
    applies_to: system_requirement_fields.value
    trigger: 建表時
    logic: >
      nullable。三種狀態：**從未填過**＝無列；**已填**＝有列且 `value` 有值；
      **清空**＝有列、`value` 為 NULL、`cleared_at` 有值。
    violation_behaviour: >
      設為 NOT NULL 會讓「從未填過」與「清空」在資料層**不可區分**，
      而畫面 `M12` 要求區分（`ADR-015`）。後果是清空動作失去稽核軌跡。
    source: 契約 `K-15` ＋ `ADR-015`

  - id: BR1.4
    statement: >
      `cleared_at` 是**獨立於 `value`** 的欄位。
    category: constraint
    applies_to: system_requirement_fields.cleared_at
    trigger: 清空動作寫入時
    logic: 清空時 `value` 設 NULL **且** `cleared_at` 設時間戳，兩者一併。
    violation_behaviour: >
      只把 `value` 設 NULL 而不記 `cleared_at`，則該列與「從未填過」
      在語意上退化為同一種狀態，清空動作不可稽核。
    source: 契約 `K-15`

  - id: BR1.5
    statement: >
      `updated_on_behalf_of` 僅在**大腦代 agent 寫入**時有值。
    category: constraint
    applies_to: system_requirement_fields.updated_on_behalf_of
    trigger: 寫入需求欄位值時
    logic: >
      使用者本人填寫時為 NULL；由大腦代某個 agent 寫入時填入該 agent 的識別。
    violation_behaviour: >
      一律填值或一律留空，都會讓使用者**無法分辨哪些值是自己填的**
      ——而這是該欄位存在的唯一理由（契約 `K-15` 逐字）。
    source: 契約 `K-15`

  # ---- BR2.x DDL 的形狀與 COMMENT 義務 ----
  - id: BR2.1
    statement: >
      全部 DDL 以 `IF NOT EXISTS` 撰寫，可重跑安全。
    category: constraint
    applies_to: 三張表及其索引與外鍵
    trigger: CI job 或部署路徑重跑時
    logic: "`CREATE TABLE IF NOT EXISTS`／`CREATE INDEX IF NOT EXISTS`。"
    violation_behaviour: >
      第二次執行失敗。**與 `U4` 的重要差別**：本契約的
      `retry_and_idempotency` 逐字「**無資料寫入故無冪等性風險**」
      ——三張表皆為全新，沒有既有資料要搬，故只需 DDL 層的可重跑。
    source: 契約 `K-15` 的 `retry_and_idempotency`

  - id: BR2.2
    statement: >
      `system_requirement_fields` 的 DDL COMMENT **必須**寫明 `[UG:G9]`=A 的行為。
    category: constraint
    applies_to: system_requirement_fields 的 COMMENT
    trigger: 建表時
    logic: >
      COMMENT 須寫明三件事：欄位定義被移除後其值列**保留**、
      畫面不渲染該組、未填計數只統計**當前已宣告**的欄位。
    violation_behaviour: >
      契約 `K-15` 的 `ddl_comment_requirement.why` 逐字：
      「不寫下來的話，『資料庫裡有、畫面上看不到』的列會被下一個人
      **當成髒資料清掉**」。這是寫給未來維護者的防呆，不是文件義務
      ——被清掉的是使用者曾經填過的值。
    source: 契約 `K-15` 的 `ddl_comment_requirement`

  - id: BR2.3
    statement: >
      四條外鍵必須存在且指向正確的表。
    category: constraint
    applies_to: 三張表的外鍵
    trigger: 建表時
    logic: >
      `project_members.project_id → projects.id`、
      `project_members.user_id → users.id`、
      `reselection_events.project_id → projects.id`、
      `system_requirement_fields.system_id → systems.id`。
      前者兩個 `projects`／`systems` 是 `K-04` 的表（已由 `U4` 交付）。
    violation_behaviour: >
      少了外鍵則可寫入指向不存在專案或系統的列，而這類列
      **不會被任何應用層檢查發現**（`U19`／`U20` 的 facade 檢查的是授權，
      不是參照完整性）。
    source: 契約 `K-15` 的 `foreign_keys`

  # ---- BR3.x 既有環境的建立路徑（繼承自 K-04 的已知約束）----
  - id: BR3.1
    statement: >
      若三張表經 `database.py` 的啟動補丁建立，**失敗必須大聲失敗**。
    category: constraint
    applies_to: 既有非空 volume 的建立路徑
    trigger: 既有環境啟動時
    logic: >
      不得沿用既有 `_ensure_*_schema()` 的錯誤處理形狀。
    violation_behaviour: >
      **本站已實地查證既有形狀**：`database.py` 的 `_ensure_*` 補丁一律
      `except Exception` ＋ `logger.warning("... 略過/失敗: %s")` 後**繼續**
      （`:257`／`:304` 等），而 `init_db()` 自身的 `except`（`:192`）也只是
      `logger.error` ＋ `rollback()` 後**不 re-raise**。
      故照抄既有形狀的後果是：**三張表沒建起來而服務照常啟動**，
      之後 `U19`／`U20` 的每一次查詢都會失敗，而**根因在啟動時只留了一行 warning**。
    source: >
      `unit-of-work.md:444`（繼承 `U4` 的既有注意事項、`[kb:architecture]` 約束六）
      ＋ 本站對 `backend/database.py` 的實讀。

  - id: BR3.2
    statement: >
      `schema_rbac.sql` 只在**空 volume** 執行——這不是本單元可改的。
    category: policy
    applies_to: schema_rbac.sql 的執行條件
    trigger: 部署到既有環境時
    logic: >
      兩份 compose 都把它掛在 `/docker-entrypoint-initdb.d/`，
      故既有的 `192.168.10.10` 不會重跑它。
    violation_behaviour: >
      不適用——本條是**誠實宣告**。寫下它的理由：把 DDL 寫進
      `schema_rbac.sql` 就以為既有環境會拿到它，是一個會在部署當天才發現的誤解。
      三張表在既有環境的建立路徑**本站不預選**（見 `functional-spec.md` §四）。
    source: 契約 `K-15` 的 `known_constraint_inherited_from_K04`

  - id: BR3.3
    statement: >
      本單元的 blocking 同步與 `K-03` 的 seed 語意變更**各觸發一次，不可互相替代**。
    category: constraint
    applies_to: schema_rbac.sql ＋ DEPLOY.md
    trigger: code-generation
    logic: >
      新增三張表觸發一次 blocking 同步；`K-03` 的 `role_permissions` seed
      語意變更（`U3`）另觸發一次。
    violation_behaviour: >
      契約 `K-15` 的 `blocking_sync.note` 逐字「兩者不可互相替代」。
      以「`U3` 已經同步過了」為由跳過本單元的同步，會讓三張表
      不出現在 `DEPLOY.md` 的表清單裡——而那份清單是部署時的檢查依據。
    source: 契約 `K-15` 的 `blocking_sync`
```

## 規則摘要（衍生檢視）

| 群組 | 條數 | 管什麼 | 誠實宣告 |
|---|---|---|---|
| `BR1.x` | 5 | 五個承載語意的欄位（`joined_at` 非空、事件為鍵、`value` 可空、`cleared_at` 獨立、代寫溯源） | — |
| `BR2.x` | 3 | DDL 可重跑、COMMENT 義務、四條外鍵 | — |
| `BR3.x` | 3 | 既有環境的建立路徑必須大聲失敗、空 volume 限制、兩次 blocking 同步 | `BR3.2` |

合計 **11 條**（由 `yaml.safe_load` 解析本檔 yaml 區塊實算；逐群 5＋3＋3＝11，相符）。

### 本單元最危險的一條

**`BR3.1`**。其餘十條的違反都會在建表時或寫入時報錯；
`BR3.1` 的違反讓**三張表根本沒建起來而服務照常啟動**，
而根因在啟動時只留了一行 `warning`。
這是本 repo 既有形狀的直接後果，故它不是「記得要寫對」，
而是**必須刻意偏離既有形狀**。
