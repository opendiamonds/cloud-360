# 實體模型 — `U19 membership-service`

> 本檔的 ```yaml 區塊是**實體的單一真實來源**。
>
> **本單元不擁有 DDL。** `ProjectMember` 與 `ReselectionEvent` 兩張表的 DDL 由
> `U18 project-meta-data` 交付（契約 `K-15`），本單元是它們的**唯一寫入端與
> 授權讀取端**。故 `project.md` 的 blocking 同步規則（`schema_rbac.sql` ＋
> `DEPLOY.md`）在本單元**只因 `[FD3]`=A 的加欄而觸發一次**，見 §三的指派。
>
> 本檔另定義四個**值物件**（value object）：它們沒有自己的表，是 facade 的
> 輸入輸出形狀，而把它們寫下來的理由是 `K-16` 的方法簽章引用了它們
> （`MemberView`／`MemberSnapshot`／`ProjectRole`），而 `AC12.3.3` 的 409 回應
> 需要第四個（`LastAdminGuardReport`）。

## 實體定義（單一真實來源）

```yaml
entities:
  - name: ProjectMember
    table: project_members
    owned_ddl_by: U18 project-meta-data（契約 K-15）
    description: >
      某使用者在某專案中的成員身分與角色。per-project 授權判定的唯一資料來源。
    attributes:
      - name: projectId
        logical_type: reference
        required: true
        references: projects.id
      - name: userId
        logical_type: reference
        required: true
        references: users.id
      - name: role
        logical_type: enumeration
        required: true
        allowed_values: [project_admin, member]
        constraints:
          - >
            per-project 角色，**與全域角色同名不同義**（`project.md` 記過
            `project_admin` 與既有全域 `Project_Admin` 的教訓）。本元件回答的是
            **專案內**的身分，全域那一層由既有 `require_story_action` 承載。
      - name: joinedAt
        logical_type: timestamp
        required: true
        constraints:
          - >
            **不得可為 null。** 自動改選的挑選規則直接讀它，平手時與 `userId`
            組成決定性 tie-break 的鍵。
      - name: invitedBy
        logical_type: reference
        required: false
        references: users.id
        constraints:
          - 可為空：建立專案時自動寫入的那一列沒有邀請者
          - >
            **本輪有寫入端而無讀取端。** `inviteMember` 寫它（§2.3），
            而 `MemberView` 的四個欄位不含它，`AC12.2.2` 的變更紀錄只涵蓋
            **角色**變更。故它是一個宣告了卻沒人讀的欄位——仍然寫入的理由是
            它在 `U18` 已核可的 DDL 與 `entities.md` 裡。誰讀它見 `OPEN-FD19-6`。
    entity_constraints:
      - 同一專案內同一使用者至多一列
      - >
        **每個專案在任何時刻至少有一列 role 為 project_admin。**
        這是 `[FD1]`=A 的不變量，由 `BR2.1` 的守門在三條路徑的共同上游維持；
        資料層**無法**強制它（它是跨列的條件），故守門是唯一防線。

  - name: ReselectionEvent
    table: reselection_events
    owned_ddl_by: U18 project-meta-data（契約 K-15）
    description: >
      一次 per-project 角色變更的稽核事件，兼橫幅已讀狀態的載體。
      **`[FD3]`=A 後涵蓋兩種來源**：系統發起的自動改選，與管理者發起的人工角色變更。
    attributes:
      - name: projectId
        logical_type: reference
        required: true
        references: projects.id
        constraints:
          - >
            **該表對 `projects` 刻意不設外鍵**（`U18` 的 `[ND1]`=A），使稽核在專案
            被刪除後獨立存活。本元件寫入時**不得**假設有參照完整性保護。
      - name: cause
        logical_type: enumeration
        required: true
        allowed_values: [auto_reselection, manual_role_change]
        constraints:
          - >
            **`[FD3]`=A 新增的欄位。** 本單元是它的唯一寫入端。
            新增此欄屬 `U18` 的 DDL 變更，為跨單元回補（見 §三）。
      - name: promotedUserId
        logical_type: reference
        required: true
        references: users.id
        constraints:
          - 角色被改變的那個人。`cause` 為 `auto_reselection` 時即被選中者
      - name: previousOwnerUserId
        logical_type: reference
        required: false
        references: users.id
        constraints:
          - >
            `cause` 為 `auto_reselection` 時為被停用的 owner；
            `manual_role_change` 時為**執行變更的管理者**（`AC12.2.2` 的「誰」）
      - name: previousRole
        logical_type: enumeration
        required: false
        allowed_values: [project_admin, member]
        constraints:
          - >
            **DDL 刻意不加 CHECK**（`U18` 的決定，逐字理由是「封閉列舉會替
            `OPEN-ND18-3` 先下結論」）。本檔的 `allowed_values` 是**應用層**約束，
            由 `BR5.4` 承載。
      - name: newRole
        logical_type: enumeration
        required: true
        allowed_values: [project_admin, member]
      - name: occurredAt
        logical_type: timestamp
        required: true
        constraints:
          - 稽核自身的時鐘（不是被變更成員的加入時間）
      - name: acknowledgedAt
        logical_type: timestamp
        required: false
        constraints:
          - >
            以**事件**為鍵，不是 per-user 布林值——後者會讓同一人第二次被改選時
            看不到橫幅，而那正是 `FR12.4c` 要防的情境。
          - >
            **只對 `cause = 'auto_reselection'` 有意義。** 橫幅只為自動改選而發
            （`FR12.4c` 的 Given 是「我因此被自動改選」）。`manual_role_change`
            的列永遠為空，見 `BR5.5`。
    entity_constraints:
      - 一個專案可以有多筆事件（每次變更一筆），故不可用專案做唯一鍵

value_objects:
  - name: ProjectRole
    description: per-project 角色的封閉列舉。
    allowed_values: [project_admin, member]
    constraints:
      - >
        **不含 `project_owner`。** `owner` 是 `projects.owner_user_id` 承載的
        **專案屬性**，不是成員角色；建立者同時是 owner 且是 `project_admin`
        （`FR12.1`），兩者是不同的事實。混為一談會讓「改某人的角色」意外改到
        專案的擁有權。

  - name: MemberSnapshot
    description: >
      `selectSuccessor` 這個**純函式**的輸入元素。刻意只含挑選所需的三個欄位
      ——多帶欄位會讓它看起來需要 DB。
    attributes:
      - name: userId
        logical_type: reference
        required: true
      - name: joinedAt
        logical_type: timestamp
        required: true
      - name: role
        logical_type: enumeration
        required: true
        allowed_values: [project_admin, member]

  - name: MemberView
    description: facade 對外回傳的成員檢視（`listMembers`／`inviteMember`／`changeRole`）。
    attributes:
      - name: userId
        logical_type: reference
        required: true
      - name: displayName
        logical_type: string
        required: true
      - name: role
        logical_type: enumeration
        required: true
        allowed_values: [project_admin, member]
      - name: joinedAt
        logical_type: timestamp
        required: true
    constraints:
      - >
        **不含 per-project 判定以外的授權結論**，也不含全域角色——前端不得自行
        推導 per-project 權限（不變量 `I-5`），它只讀本元件給的結論。

  - name: LastAdminGuardReport
    description: >
      守門命中時的回報酬載。`AC12.3.3` 的 Then 要求停用被拒時**列出那些專案**，
      故這個形狀是 409 回應模型的來源。
    attributes:
      - name: projects
        logical_type: list
        required: true
        constraints:
          - 每一項含 projectId 與專案名稱——只給 id 的話畫面無法告知使用者是哪個專案
    constraints:
      - >
        **它必須成為顯式宣告的 409 response model**（`FR12.5b` 的 DoD）：
        實測 `openapi.json` 的 55 個 operation 宣告的狀態碼只有
        `{200:53, 422:45, 201:1, 204:1}`，非 2xx/422 的宣告數為 **0**，
        故不顯式宣告則此契約不進 spec、前端也產不出型別，而
        `dump_openapi.py --check` 會保持綠燈。

relationships:
  - from: ProjectMember
    to: Project
    cardinality: many-to-one
    note: Project 由 ProjectHierarchy（U7／K-07）擁有；本元件只讀它以驗證存在與取 ownerUserId
  - from: ReselectionEvent
    to: Project
    cardinality: many-to-one
    note: "**無外鍵**（見上）；關聯是邏輯上的，不是資料庫強制的"
  - from: ProjectMember
    to: User
    cardinality: many-to-one
```

## 人類可讀摘要

### 兩張表、四個值物件，而本單元一張表都不擁有

| 實體 | 誰擁有 DDL | 本單元的角色 |
|---|---|---|
| `ProjectMember` | `U18`（`K-15`） | **唯一寫入端**（邀請／移出／角色變更／自動改選）＋ 授權讀取端 |
| `ReselectionEvent` | `U18`（`K-15`） | **唯一寫入端**；`[FD3]`=A 的 `cause` 欄由本站定義、由 `U18` 加上 |
| `ProjectRole`／`MemberSnapshot`／`MemberView`／`LastAdminGuardReport` | 本單元 | 值物件，無表 |

### `[FD1]`=A 的不變量無法由資料層強制

「每個專案至少有一位 `project_admin`」是**跨列條件**，PostgreSQL 的 CHECK 作用於
單列、UNIQUE 作用於鍵的唯一性，兩者都表達不了它。這使 `BR2.1` 的守門成為**唯一
防線**——與 `U18` 記過的同形結論一致（停用端點做的是 UPDATE，外鍵對 UPDATE 零效力）。

### `cause` 讓兩種角色變更共用一張表，而 `acknowledgedAt` 只對其中一種有意義

| `cause` | `previousOwnerUserId` 的語意 | `acknowledgedAt` |
|---|---|---|
| `auto_reselection` | 被停用的 owner | 有意義（橫幅已讀狀態） |
| `manual_role_change` | **執行變更的管理者**（`AC12.2.2` 的「誰」） | **永遠為空** |

同一個欄位在兩種 `cause` 下指不同的人，這是刻意的：兩者都回答「這次變更是誰造成的」。
**若下一個人覺得該拆成兩欄**，請先讀 `BR5.4` 的理由再決定。
