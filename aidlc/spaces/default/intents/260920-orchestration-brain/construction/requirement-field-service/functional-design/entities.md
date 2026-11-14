# Entities — `U20 requirement-field-service`

> 本單元**擁有**一個持久實體（`SystemRequirementField`，表已由 `U18` 交付）與兩個
> 程式內常數實體（欄位定義）。`System`／`Project`／`ProjectMember` 屬上游單元，
> 本檔只以參照出現。
>
> **對 `U18` 已交付 DDL 的一處變更（`[FD1]`=A）**：`updated_on_behalf_of` 由
> `INTEGER REFERENCES users (id)` 改為**不帶外鍵的 agent 組識別字**。這是本單元的
> 設計決定，落地在本單元的 code-generation（觸發 `schema_rbac.sql` ＋ `DEPLOY.md`
> 的 blocking 同步）；`U18` 已核可的產出**不回改**（`refined-mockups:c3`），張力
> 來源為 `U18` 的 `OPEN-CG18-6`，該項由本站結案。

```yaml
entities:
  - name: SystemRequirementField
    description: >
      某個系統的某個需求欄位的「值」。欄位本身（屬於哪組、叫什麼）由程式內常數
      AgentFieldGroup 定義；本實體只存值與其溯源。三態以列的有無與欄位組合表達
      （ADR-015）：從未填過＝無列；已填＝有列且 value 非 null；已清空＝有列、
      value 為 null 且 clearedAt 有值。
    owner: U20 requirement-field-service
    storage: system_requirement_fields（U18 交付；本單元變更一欄，見 updatedOnBehalfOf）
    attributes:
      - name: systemRequirementFieldId
        type: integer
        required: true
        unique: true
        constraints: 代理鍵，由資料庫產生；不對外作為定址鍵（對外以 systemId＋agentGroup＋fieldKey 定址）
      - name: systemId
        type: integer
        required: true
        references: System.systemId（ProjectHierarchy／U7）
        constraints: 系統刪除時本列一併刪除（U18 的 ON DELETE CASCADE，[ND1]=A）
      - name: agentGroup
        type: string
        required: true
        max: 64
        constraints: 寫入時必須是當前已宣告的 AgentFieldGroup.groupKey；讀取時允許出現已不再宣告的值（[UG:G9]=A 的保留列）
      - name: fieldKey
        type: string
        required: true
        max: 64
        constraints: 寫入時必須是該 agentGroup 底下已宣告的 AgentFieldDefinition.fieldKey
      - name: value
        type: text
        required: false
        max: 2000
        constraints: >
          null 只在「已清空」態出現。非 null 時為去除首尾空白後的非空字串
          （BR43.1）；空字串永不落地，改走清空語意（BR43.2）。
      - name: clearedAt
        type: timestamp
        required: false
        constraints: 只在已清空態有值；與 value 互斥（U18 的 ck_system_requirement_fields_cleared_has_null_value）
      - name: updatedAt
        type: timestamp
        required: true
        default: 寫入當下
        constraints: 每次有效寫入或清空都更新；no-op 不更新（BR45.5）
      - name: updatedBy
        type: integer
        required: true
        references: User.userId（既有 users 表）
        constraints: 實際發起者＝已驗證的 principal；由大腦代寫時仍為「該使用者本人」，不是大腦（BR45.1）
      - name: updatedOnBehalfOf
        type: string
        required: false
        max: 64
        allowed_values: 當前已宣告的 AgentFieldGroup.groupKey 之一，或 null
        constraints: >
          [FD1]=A：不帶外鍵的 agent 組識別字。null＝使用者自己填的；非 null＝
          大腦代該 agent 寫入。清空動作一律寫 null（BR45.3）。
    entity_constraints:
      - "唯一：(systemId, agentGroup, fieldKey)——同一個 fieldKey 字串在不同組底下是不同欄位（U18 已交付的三欄唯一鍵）"
      - "互斥：clearedAt 非 null ⇒ value 為 null"
      - "不刪列：本單元沒有任何刪除列的操作；清空以更新表達，列數只增不減（ADR-015 已接受）"
    relationships:
      - target: System
        cardinality: many-to-one
        direction: SystemRequirementField → System
      - target: User（updatedBy）
        cardinality: many-to-one
        direction: SystemRequirementField → User

  - name: AgentFieldGroup
    description: >
      程式內常數：一個 agent 需要的一組固定欄位。不是資料庫實體；新 agent 上線要
      新增一組定義（[R12]=D 的代價，線框 §17 已寫明）。
    owner: U20 requirement-field-service
    storage: 程式內常數（不落地）
    attributes:
      - name: groupKey
        type: string
        required: true
        unique: true
        max: 64
        constraints: 小寫英數與底線；作為 agentGroup 與 updatedOnBehalfOf 的合法值來源
      - name: title
        type: string
        required: true
        constraints: 畫面上的組標題，即 agent 名稱（AC11.2.2 的「每一組的標題為該 agent 名稱」）
      - name: displayOrder
        type: integer
        required: true
        constraints: 組在回應中的順序；決定性，不依賴字典序
      - name: fields
        type: list<AgentFieldDefinition>
        required: true
        min: 1
        constraints: 組內 fieldKey 不得重複；順序即畫面順序
    relationships:
      - target: AgentFieldDefinition
        cardinality: one-to-many
        direction: AgentFieldGroup → AgentFieldDefinition

  - name: AgentFieldDefinition
    description: 程式內常數：組內的一個欄位
    owner: U20 requirement-field-service
    storage: 程式內常數（不落地）
    attributes:
      - name: fieldKey
        type: string
        required: true
        max: 64
        constraints: 小寫英數與底線；在所屬組內唯一
      - name: label
        type: string
        required: true
        constraints: 畫面上的欄位標籤

field_definitions_v1:   # [FD2]=A：照線框 §17 的兩組七欄
  - groupKey: cost
    title: 成本 agent
    displayOrder: 1
    fields:
      - { fieldKey: sla, label: SLA }
      - { fieldKey: peak_tps, label: 尖峰 TPS }
      - { fieldKey: user_base, label: 使用客群 }
      - { fieldKey: monthly_budget_cap, label: 月預算上限 }
      - { fieldKey: billing_region, label: 計費區域 }
  - groupKey: architecture
    title: 架構 agent
    displayOrder: 2
    fields:
      - { fieldKey: availability_target, label: 可用性目標 }
      - { fieldKey: data_retention, label: 資料保存年限 }

value_objects:
  - name: FilledState
    allowed_values: [never_filled, filled, cleared]
    derivation: "value 非 null → filled；value 為 null 且 clearedAt 非 null → cleared；其餘（無列，或有列而 value 與 clearedAt 皆為 null）→ never_filled（BR44.1，涵蓋 U18 交下的第四種列）"
  - name: FieldSetView
    description: read_fields 的回傳；分組明細與 unfilledCount 由同一次查詢推導（不變量 I-4）
    attributes: [systemId, groups（每組：groupKey、title、filledCount、totalCount、fields）, unfilledCount]
  - name: FieldView
    description: 單一欄位的檢視；含 clearedAt，與 K-17 clear_field 的回傳字面一致（review-01 R-03）
    attributes: [groupKey, fieldKey, label, value|null, filledState, clearedAt|null, updatedAt|null, updatedBy|null, updatedOnBehalfOf|null]
```

## 摘要

- **一個持久實體**：`SystemRequirementField`，三態由列的有無與 `value`／`clearedAt`
  的組合表達。表由 `U18` 交付，本單元只變更一欄（`updatedOnBehalfOf`，`[FD1]`=A）。
- **兩個程式內常數實體**：`AgentFieldGroup` 與 `AgentFieldDefinition`。第一版宣告
  兩組七欄（`[FD2]`=A，取自線框 §17）。
- **三個值物件**：`FilledState`（三態的推導）、`FieldSetView`（`read_fields` 的回傳，
  計數與明細同源）、`FieldView`（單欄）。
- 列數只增不減：本單元沒有刪除列的操作；定義被移除時值列保留但不顯示、不計數
  （`[UG:G9]`=A）。
