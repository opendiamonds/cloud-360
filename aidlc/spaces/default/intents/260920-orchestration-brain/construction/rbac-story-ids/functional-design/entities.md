# Entities — `U3 rbac-story-ids`（`spec`）

<!-- Stage: functional-design（Construction 3.1）· Unit: rbac-story-ids · kind: spec -->

> **⚠ 本檔有修訂 1（2026-10-04）**：`K3`／`K4` 兩個 story id、矩陣 **352** 列。
> 下方 §「本單元不新增任何實體」至 §「實體集合的人話摘要」為**修訂前原文**，
> 其中 `StoryId` 的值數、`RolePermission` 的實例數與 `EC-2` 已被修訂 1 取代。
> **讀本檔請一併讀文末的「修訂 1」段**，該段的 YAML 與原文 YAML 合併讀取。

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

---

# 修訂 1（2026-10-04）— `K3`／`K4` 兩個新 story id

<!-- 本段為 append。上方原文**不回改**（`refined-mockups:c3`）：它在 `K1`／`K2` 的
     範圍內仍然有效。下方第二個 yaml 區塊與上方第一個**同格式、合併讀取**，
     合併規則明訂於區塊內——這是 `components.md` `Part A''` 的同一手法
     （`domain-design:c2043824` 的教訓：為了不回改已核可內容而採的變通，必須
     留在同一種格式裡，降格成散文會讓機讀契約無聲失效）。 -->

## 本修訂仍然不新增任何實體

`K3`（專案成員管理）與 `K4`（需求欄位）是 `StoryId` 的兩個新**值**，連帶
`RolePermission` 的 **44** 個新實例（11 角色 × 4 個新 id，含原本的 `K1`／`K2`）。
不建表、不加欄、不改任何既有欄位的型別或約束。

```yaml
# ── 修訂 1 的 source-of-truth 增補（與上方 entities 區塊合併讀取）────────
# 合併規則：同名實體的 attributes／entity_constraints／notes 取聯集；
#           同 id 的條目以**本區塊**為準（supersedes 欄位明寫被取代者）。
#           relationships 不變，故本區塊不重列。

entities_amended:

  - name: StoryId
    existing: true
    kind: value_object
    supersedes: "上方 StoryId 的 description 與 allowed_values_added_by_this_unit"
    description: >
      功能能力的識別字串。既有 28 個，本單元新增 4 個（K1、K2、K3、K4），共 32 個。
      字首字母為功能域分組：A 架構、B 跨雲選型、C 成本、D IaC、E 維運、
      F 多雲維運、G 安全、H MCP/Skill、J 管理，本單元啟用全新字首 K。
    attributes:
      - name: value
        type: string
        required: true
        unique: true
        allowed_values_added_by_this_unit: [K1, K2, K3, K4]
        constraint: >
          新增值不得與既有 28 個重複（本站實算：無交集），且不得沿用既有字首
          ——ADR-004 的 Alternatives Rejected 逐字拒絕了併入 A 字首。
    notes:
      - id: N-2
        supersedes: N-1
        text: >
          N-1 的內容原樣有效，但數量由 2 改為 4：K1–K4 都必須有對應的
          STORY_FEATURE_LABELS 項目，否則 user_router.py 的 _feature_label
          回 None，權限頁與註冊功能摘要會出現無名稱的列。本站實算該字典現有
          27 個鍵（A1／A2／A4 共用一個標籤值），加上 CATALOG_EXCLUDED_STORIES
          的 J1 恰覆蓋既有 28 個 id。見 rules.md BR4.3（修訂 1 已改為四個）。
      - id: N-3
        text: >
          K3 與 K4 是 `requirements.md` 的 FR12.6a（「缺少**對應全域功能權限**的
          使用者不得被邀請加入專案」）那個「對應全域功能權限」的所指——
          這在 [UG:G8]=C 之前沒有任何指涉對象（[US:V-13] 的缺口）。
          [UG:G8]=C 的作答註解逐字：「成員頁對應 K3、需求欄位對應 K4」。
          同檔的 FR12.6b 另明文記載其後果：入職順序被強制為「先全域權限、
          後專案成員」。

  - name: RolePermission
    existing: true
    kind: entity
    supersedes: "上方 RolePermission 的 description 與 entity_constraints EC-2"
    description: >
      權限矩陣的一列：一個角色對一個 story id 的三個動作旗標。
      本單元新增 44 個實例（11 角色 × 4 個新 story id），不修改既有 308 個。
    attributes_unchanged: true        # role／story_id／can_view／can_edit／can_review／updated_by 原樣
    entity_constraints:
      - id: EC-2
        supersedes: EC-2
        statement: >
          矩陣完整性：對每一個 (role, story_id) 組合恰有一列。本單元後為
          11 × 32 = 352 列。
        note: >
          「不持有某能力」的表達方式仍是**列存在、三個旗標皆 false**。
          本修訂新增三組這樣的列：SRE／Ops_Lead／Platform_Engineer 在
          K3 與 K4 上皆為全 false（見 rules.md BR5.1／BR6.1）。
        computed_by: >
          本站以腳本從 backend/services/rbac_seed_data.py 實際解析後複算，
          不照抄上游的算式：既有 308 列 ＝ 11 角色 × 28 story id（組合完整、
          無缺漏）；308 ＋ 11 × 4 ＝ 352。11 項不變量檢查全部 PASS。
      - id: EC-4
        statement: >
          四個新 id 的 can_review 在全部 44 列皆為 false。
        note: >
          與 K1／K2 的處置（BR1.2／BR2.4）一致。本修訂查證到 J3a／J3b
          （系統管理群）**確實**使用 can_review（Project_Admin 與
          Platform_Admin 為 ver），故「管理類 id 一律不用 can_review」
          並非既有通則；K3 不用它的理由是**沒有消費端**——K-16 的
          public_interface 沒有任何「審核」動作，邀請／移出／角色變更／
          自動改選全部是寫入。給一個沒有消費端的旗標等於寫入死資料。
```

## 修訂 1 更正一處既有事實陳述（決定不改，只修理由）

上方 `BR2.2` 的 note 與 Q3 的作答後果都寫「`Platform_Owner` 在既有 28 個 story id
上全為 `v--`（全域唯讀）」。**本站以腳本實算後確認該陳述不成立**：

| 實測 | 內容 |
|---|---|
| `Platform_Owner` 的 `can_edit` | **1 個**：`J1`（登入能力） |
| `Platform_Owner` 的 `can_review` | **2 個**：`F3`、`H2` |

依 `project.md` 的 `functional-design:c22`（下游查證推翻的是選項的理由而非決定
本身時，只修理由不改決定）：**Q3=A 的決定不改**，`K2`／`K3`／`K4` 皆不給
`Platform_Owner` 的 `edit`。更正後的理由是：**`Platform_Owner` 唯一的 `edit` 是
登入能力 `J1`，給它實質的寫入權會是第一次**，而非「它從來沒有任何非 view 旗標」。

## 修訂 1 的人話摘要

表格由 11 × 30 長成 **11 × 32**。新增的兩欄把全域邊界切得比 `[UG:G8]` 的
A 選項更細：

- **`K3` 專案成員管理**——誰能參與成員體系（`view`）、誰能管理成員（`edit`）。
- **`K4` 需求欄位**——誰能看需求籤（`view`）、誰能改架構假設（`edit`）。

兩欄的持有者集合與 `K1`（統一入口頁）**逐字相同**（八個角色），不持有者也相同
（`SRE`、`Ops_Lead`、`Platform_Engineer`）。這不是巧合而是刻意：它使「誰是這個
產品裡的專案參與者」在全域層只有一個答案，而那三個不持有者同時讓
`AC12.5.1`（邀請缺權限者被拒）與 `AC1.4.2`（不持有入口頁權限者）的 Given
都可構造。
