# 實體模型 — `U18 project-meta-data`

> 本檔的 ```yaml 區塊是**實體的單一真實來源**。
> **本單元擁有 DDL**，故 `project.md` 的 blocking 同步規則觸發
> （`schema_rbac.sql` ＋ `DEPLOY.md`，在 `code-generation` 完成）。
>
> **與 `U4` 的關鍵差別**：契約 `K-15` 的 `observable_side_effects` 逐字
> 「**不含任何資料寫入**（與 `K-04` 不同，本契約沒有遷移步驟：三張表皆為全新，
> 沒有既有資料要搬）」——故無遷移、無冪等性風險。

## 實體定義（單一真實來源）

```yaml
entities:
  - name: ProjectMember
    table: project_members
    description: 某使用者在某專案中的成員身分與角色（per-project 授權的資料基礎）。
    attributes:
      - name: projectId
        logical_type: reference
        required: true
        references: projects.id（`K-04` 的表，已由 `U4` 交付）
      - name: userId
        logical_type: reference
        required: true
        references: users.id（既有表）
      - name: role
        logical_type: enumeration
        required: true
        constraints:
          - >
            per-project 角色。**與全域角色同名不同義**——`project.md` 已記過
            `project_admin` 與既有全域 `Project_Admin`（`rbac.py:33`／`:288`）
            同名不同義的教訓。本表的 role 是**專案內**的身分。
      - name: joinedAt
        logical_type: timestamp
        required: true
        constraints:
          - >
            **不得可為 null。** 契約 `K-15` 逐字：`FR12.4` 的挑選規則（最早加入）
            **直接讀它**；平手時與 `userId` 組成決定性 tie-break 的鍵。
            可為 null 會讓挑選**在空值上無序**——而「自動改選」的結果不穩定
            是靜默的錯誤（每次選出不同人而無人察覺）。
      - name: invitedBy
        logical_type: reference
        required: false
        references: users.id
        constraints:
          - 可為空：遷移或系統建立的成員列沒有邀請者
    entity_constraints:
      - 同一專案內同一使用者至多一列（唯一約束）

  - name: ReselectionEvent
    table: reselection_events
    description: >
      `project_owner` 帳號被停用時自動改選的事件紀錄，兼橫幅已讀狀態的載體。
    attributes:
      - name: projectId
        logical_type: reference
        required: true
        references: projects.id
      - name: acknowledgedAt
        logical_type: timestamp
        required: false
        constraints:
          - >
            **以事件為鍵，不是 per-user 布林值。** 契約 `K-15` 逐字說明理由：
            per-user 布林值「會讓同一人**第二次**被改選時看不到橫幅，
            而那正是 `FR12.4c` 要防的情境」。
          - 為空＝尚未確認（橫幅應顯示）；有值＝已確認
    entity_constraints:
      - 一個專案可以有多筆改選事件（每次改選一筆），故不可用專案做唯一鍵

  - name: SystemRequirementField
    table: system_requirement_fields
    description: >
      某系統的某個需求欄位的值（agent 需要的架構假設，如 SLA／TPS／預算）。
    attributes:
      - name: systemId
        logical_type: reference
        required: true
        references: systems.id（`K-04` 的表）
      - name: value
        logical_type: text
        required: false
        constraints:
          - >
            **必須可為 null。** 契約 `K-15` ＋ `ADR-015`：
            「**從未填過**」＝**無列**；「**清空**」＝**有列而 `value` 為 null
            且 `clearedAt` 有值」。
            設為 NOT NULL 會讓兩種狀態在資料層**不可區分**，而畫面 `M12`
            要求區分它們。
      - name: clearedAt
        logical_type: timestamp
        required: false
        constraints:
          - >
            **獨立於 `value` 的欄位**，使清空動作可被稽核（誰清、何時清）。
            與 `value` 合起來構成三種可區分的狀態（見下方摘要表）。
      - name: updatedOnBehalfOf
        logical_type: reference
        required: false
        references: users.id 或 agent 識別
        constraints:
          - >
            由大腦**代某個 agent** 寫入時才有值；使用者得以分辨哪些值是
            自己填的、哪些是代寫的。為空＝使用者本人填的。
    entity_constraints:
      - 同一系統內同一欄位名至多一列
```

## 人類可讀摘要

### `system_requirement_fields` 的三種狀態（本單元最容易被實作錯的地方）

| 狀態 | 列是否存在 | `value` | `clearedAt` | 畫面行為 |
|---|---|---|---|---|
| **從未填過** | **無列** | — | — | 顯示空白輸入框，計入「未填」 |
| **已填** | 有列 | 有值 | NULL | 顯示該值 |
| **曾填後清空** | **有列** | **NULL** | **有值** | 顯示空白，計入「未填」，但**清空動作有稽核** |

「從未填過」與「清空」在**畫面上看起來一樣**，但在**資料層必須可區分**
——後者有稽核軌跡。把 `value` 設成 NOT NULL 會讓第三種狀態無法表達。

### `[UG:G9]`=A 的後果必須寫進 DDL COMMENT

契約 `K-15` 的 `ddl_comment_requirement` 逐字要求 COMMENT 寫明：
欄位定義被移除後其值列**保留**、畫面不渲染該組、未填計數只統計當前已宣告的欄位。

**理由同樣逐字**：「不寫下來的話，『資料庫裡有、畫面上看不到』的列會被下一個人
當成髒資料清掉」。這是一條**寫給未來維護者的防呆**，不是文件義務。
