# Entities — `U3 rbac-story-ids`（`spec`）

<!-- Stage: functional-design（Construction 3.1）· Unit: rbac-story-ids · kind: spec -->

## 本單元不新增任何實體

先把界線講清楚，因為這會決定下游怎麼讀這份檔：**本單元不建表、不加欄、不改任何
既有欄位的型別或約束**。它交付的是**既有實體 `RolePermission` 的 22 個新實例**，
以及兩個新的 `StoryId` 值。

下方 YAML 區塊是本檔的 source of truth。既有實體以 `existing: true` 標示，
其屬性清單為**本單元讀寫到的欄位**，不是該實體的完整欄位表——完整定義在
`schema_rbac.sql` 的 RBAC 區塊與 `backend/models.py`。

```yaml
entities:

  - name: StoryId
    existing: true
    kind: value_object
    description: >
      功能能力的識別字串。既有 28 個，本單元新增 2 個（K1、K2），共 30 個。
      字首字母為功能域分組：A 架構、B 跨雲選型、C 成本、D IaC、E 維運、
      F 多雲維運、G 安全、H MCP/Skill、J 管理，本單元啟用全新字首 K。
    attributes:
      - name: value
        type: string
        required: true
        unique: true
        allowed_values_added_by_this_unit: [K1, K2]
        constraint: >
          新增值不得與既有 28 個重複，且不得沿用既有字首——ADR-004 的
          Alternatives Rejected 逐字拒絕了併入 A 字首。
    notes:
      - id: N-1
        text: >
          K1 與 K2 沒有對應的 STORY_FEATURE_LABELS 項目時，
          user_router.py:242 的 _feature_label 會回 None。本單元必須一併補上
          兩個標籤，否則權限頁與註冊功能摘要會出現無名稱的列。
          這是本站查證 user_router.py:60–88 得到的、上游未記載的相依。

  - name: Role
    existing: true
    kind: value_object
    description: >
      正式角色。正本為 services/rbac.py 的 CANONICAL_ROLES，共 11 個。
      本單元不新增、不刪除、不更名任何角色。
    attributes:
      - name: value
        type: string
        required: true
        unique: true
        allowed_values:
          - Project_Architect
          - Developer
          - Project_Editor
          - Project_Admin
          - FinOps_Analyst
          - SRE
          - Ops_Lead
          - Platform_Engineer
          - Security_Reviewer
          - Platform_Admin
          - Platform_Owner

  - name: RolePermission
    existing: true
    kind: entity
    description: >
      權限矩陣的一列：一個角色對一個 story id 的三個動作旗標。
      本單元新增 22 個實例（11 角色 × 2 個新 story id），不修改既有 308 個。
    attributes:
      - name: role
        type: Role
        required: true
        references: Role.value
      - name: story_id
        type: StoryId
        required: true
        references: StoryId.value
      - name: can_view
        type: boolean
        required: true
        default: false
      - name: can_edit
        type: boolean
        required: true
        default: false
      - name: can_review
        type: boolean
        required: true
        default: false
      - name: updated_by
        type: string
        required: true
        constraint: >
          由 seed 寫入的列其值為字串 "system_seed"（rbac.py:77、:105）。
          本單元新增的 22 列皆為此值。人工於權限頁調整過的列會被改寫為該操作者，
          這是「哪些列還是預設值」的唯一可判斷依據。
    entity_constraints:
      - id: EC-1
        statement: (role, story_id) 唯一。
        existing: true
      - id: EC-2
        statement: >
          矩陣完整性：對每一個 (role, story_id) 組合恰有一列。本單元後為
          11 × 30 = 330 列。
        note: >
          「不持有某能力」的表達方式是**列存在、三個旗標皆 false**，
          不是「列不存在」。既有前例為 ('FinOps_Analyst','A3',false,false,false)。
          這點是本單元 K1 三列與 K2 七列的表達形式，見 rules.md BR1.1／BR2.2。
      - id: EC-3
        statement: >
          旗標之間沒有資料庫層的蘊含關係，但**讀取端有**：
          rbac.py:152–153 的 user_can(view) 回傳 can_view OR can_edit OR can_review。
        note: >
          後果是「給 edit 不給 view」無法表達，而「完全不持有」必須三個旗標皆 false。
          本單元的 K1 設計（view-only）與 K2 設計（edit 蘊含 view）都建立在這條上。

relationships:
  - from: RolePermission
    to: Role
    cardinality: many-to-one
    direction: RolePermission → Role
  - from: RolePermission
    to: StoryId
    cardinality: many-to-one
    direction: RolePermission → StoryId
```

## 實體集合的人話摘要

這個單元的實體圖小到可以一句話講完：**權限矩陣是一張
`(角色 × 能力) → 三個布林旗標` 的完整表格，本單元往右邊加兩個能力欄，
於是表格從 11 × 28 長成 11 × 30。**

要注意的只有三件事，而三件都不在直覺上：

1. **「沒有權限」不是「沒有那一列」**，是「那一列的三個旗標都是 false」。
   矩陣必須保持完整（`EC-2`），否則權限頁會出現破洞。
2. **`view` 的讀取是 OR，不是欄位本身**（`EC-3`）。所以給了 `edit` 就等於給了
   `view`，反過來不成立。這條決定了 `K1` 為什麼做成 view-only、
   `K2` 為什麼只需要決定「誰有 edit」而不必再決定「誰有 view」。
3. **`updated_by` 是唯一能分辨「這列還是預設值」與「有人改過」的欄位。**
   本單元的寫入端只插入缺失列、絕不覆寫（`rules.md` `BR3.3`），
   而它之所以能安全地每次啟動都跑，靠的就是這個不覆寫的性質。

**本單元沒有新的生命週期實體**，故沒有狀態機——狀態轉移的描述在
`functional-spec.md`，那裡談的是 seed 寫入的流程而非實體狀態。
