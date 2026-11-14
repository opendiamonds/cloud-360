# 業務規則 — `U8 memory-service`

> 22 條規則，七組。授權規則分成**兩套不同的模型**：
> `BR1`／`BR2` 是記憶列的擁有者 ＋ 可見範圍（本 repo 的第二套授權模型），
> `BR5`／`BR6` 是角色判定（`Platform_Admin`／`Platform_Owner`）。
> 兩者不可互相替代——混用是本單元最容易出的授權錯誤。

## 一、規則（機讀真實來源）

```yaml
rules:
  # ── BR1 擁有者的寫入端強制（FR4.3a）────────────────────────────
  - id: BR1.1
    statement: 記憶的擁有者一律為寫入時呼叫者的已驗證身分
    category: authorization
    applies_to: MemoryRecord.ownerUserId
    trigger: 任何記憶寫入
    logic: >
      IF 一則記憶被寫入
      THEN 其 ownerUserId 設為該次呼叫的已驗證 principal 的身分，
      且該值不來自任何請求酬載欄位
    violation_behaviour: 不適用——這是賦值規則而非驗證規則；它不會「違反」，只會被實作錯
    source: FR4.3a
    verified_by: AC4.4.1

  - id: BR1.2
    statement: 請求酬載中自行指定的擁有者一律被忽略
    category: validation
    applies_to: 寫入端的輸入
    trigger: 寫入請求的酬載含擁有者欄位
    logic: >
      IF 寫入請求的酬載含任何意圖指定擁有者的欄位
      THEN 忽略它，擁有者仍依 BR1.1 設定；**不回報錯誤**
    violation_behaviour: >
      靜默忽略（非拒絕）。選擇忽略而非回 422 的理由：回錯誤會讓呼叫端以為
      「換個欄位名就能指定」，而忽略使該能力不存在
    source: FR4.3a
    verified_by: AC4.4.2
    note: >
      **這條是 AC4.4.2 存在的全部理由**。只有 BR1.1 的話，一個從不檢查酬載的
      實作也能通過——因為它碰巧沒有讀那個欄位。BR1.2 要求的是「即使酬載有，
      也不生效」

  # ── BR2 可見範圍（FR4.3b、[FD3]=A）─────────────────────────────
  - id: BR2.1
    statement: 新記憶的可見範圍預設為最窄
    category: constraint
    applies_to: MemoryRecord.visibilityScope
    trigger: 任何記憶寫入
    logic: IF 一則記憶被寫入 THEN 其 visibilityScope 為 owner
    violation_behaviour: 不適用——賦值規則
    source: FR4.3b
    verified_by: AC4.4.3
    note: 寫入端**不接受** visibilityScope 作為輸入；放寬是獨立操作（BR5.*）

  - id: BR2.2
    statement: 讀取一律只回該呼叫者依可見範圍有權讀取的列
    category: authorization
    applies_to: 所有讀取路徑（列出、檢索）
    trigger: 任何記憶讀取
    logic: >
      IF 呼叫者為 principal P
      THEN 僅回 ownerUserId = P 或 visibilityScope = platform 的列
    violation_behaviour: >
      不回錯誤，**回較小的集合**。這是過濾而非拒絕——
      「看不到別人的記憶」不是一個錯誤狀態
    source: FR4.3、FR4.3b
    verified_by: AC4.1.2
    note: >
      **過濾必須在 facade 內完成，呼叫端不得自行過濾**（K-08 的
      authorization_responsibility 逐字）。這一條是 `U15` 前端不自行過濾的依據

  - id: BR2.3
    statement: 可見範圍的值限於封閉集合
    category: validation
    applies_to: MemoryRecord.visibilityScope、MemoryAuditEvent.previousScope／newScope
    trigger: 任何寫入或放寬
    logic: IF 值不在 {owner, platform} THEN 拒絕寫入
    violation_behaviour: 拒絕並回報不合法的值與合法集合
    source: "[FD3]=A"
    note: >
      **結構層不擋這個**（既有欄位無封閉約束），故本條是本單元的寫入端義務；
      漏做的後果是髒資料而非寫入失敗

  # ── BR3 檢索（FR4.1、MemoryStore.behaviour）─────────────────────
  - id: BR3.1
    statement: 脈絡組裝的結果包含呼叫者可見的先前記憶，且三種 kind 皆可被取得
    category: calculation
    applies_to: 檢索路徑
    trigger: 為一次對話組裝脈絡
    logic: >
      IF 為 principal P 組裝脈絡
      THEN 結果取自 P 依 BR2.2 可見的列，且不限於單一 kind——
      呼叫端得指定要哪幾種，未指定時三種皆納入候選
    violation_behaviour: 不適用——這是檢索語意
    source: FR4.1
    verified_by: AC4.1.1、AC4.1.3

  - id: BR3.2
    statement: 相似度比對只在同一個 embeddingModel 的列之間進行
    category: constraint
    applies_to: 向量檢索
    trigger: 以向量相似度檢索
    logic: >
      IF 以模型 M 產生的查詢向量檢索
      THEN 只比對 embeddingModel = M 的列
    violation_behaviour: >
      **這是本單元唯一完全靜默的失敗模式**：少了這道過濾，型別、維度、索引與
      查詢全部仍然合法，但結果是跨向量空間的垃圾且**不報錯**。
      故它是約束而非最佳化
    source: MemoryStore.behaviour
    note: 同維度不等於同向量空間——兩個提供者都是 1024 維，這正是陷阱所在

  - id: BR3.3
    statement: 無向量的列不被向量檢索看到，且這不是錯誤
    category: policy
    applies_to: 向量檢索
    trigger: 列的 embedding 為空
    logic: >
      IF 一列的 embedding 為空
      THEN 它不出現在向量檢索結果中，直到被重新 embed；不回報任何錯誤
    violation_behaviour: 不適用
    source: MemoryStore.behaviour
    note: >
      fulltext 提供者模式下建立的列即為此狀態。把它當缺陷去「補齊」或改成必填
      會破壞 fulltext 退路

  - id: BR3.4
    statement: 已刪除或已逾期清除的記憶不得出現在任何檢索結果中
    category: constraint
    applies_to: 所有讀取路徑
    trigger: 記憶已被刪除或已被清除
    logic: >
      IF 一則記憶已被使用者刪除（BR4.1）或已被保存期清除
      THEN 後續任何脈絡組裝與列出都不包含它
    violation_behaviour: 不適用
    source: FR4.6、FR4.5
    verified_by: AC4.2.1、AC4.2.3
    note: >
      本條在實作上由「列已不存在」自然滿足——兩種路徑都是實際刪除而非軟刪除。
      寫下來是因為 AC4.2.1／AC4.2.3 斷言的是**檢索結果**，而讀者會問
      「有沒有軟刪除」。答案是沒有

  - id: BR3.5
    statement: 選定的 embedding 提供者不可用時必須大聲失敗，不得靜默降級
    category: policy
    applies_to: 寫入與檢索
    trigger: 設定選定的提供者偵測不到
    logic: >
      IF 選定的提供者不可用
      THEN 拋 EmbeddingProviderUnavailable 並列出可選值；
      **不得**自動改用 fulltext 或任何其他提供者
    violation_behaviour: 操作失敗，呼叫端收到可辨識的錯誤
    source: MemoryStore.behaviour
    note: >
      靜默降級的後果是整批記憶以錯的提供者寫入而無人察覺，
      之後 BR3.2 的分群使它們永久不可被檢索到

  # ── BR4 使用者刪除與其稽核（FR4.6、FR4.7）───────────────────────
  - id: BR4.1
    statement: 使用者得刪除自己的記憶，不得刪除他人的
    category: authorization
    applies_to: 刪除路徑
    trigger: 刪除請求
    logic: >
      IF principal P 要求刪除記憶 M
      THEN 僅當 M.ownerUserId = P 時執行；否則拒絕
    violation_behaviour: MemoryForbidden(reason="owner") → 403 ＋ detail 前綴
    source: FR4.6
    verified_by: AC4.2.1
    note: >
      **以擁有者判定，不以角色判定**。`Platform_Admin` 不因其角色而能刪除他人的
      記憶——放寬可見範圍（BR5.1）是它被授予的唯一特權操作

  - id: BR4.2
    statement: 每一次使用者刪除都留下一筆稽核事件
    category: constraint
    applies_to: 刪除路徑
    trigger: 刪除成功
    logic: >
      IF 記憶 M 被 principal P 刪除
      THEN 產生一筆 action = deleted_by_user 的稽核事件，
      帶 memoryId = M、actorUserId = P、occurredAt = 當下
    violation_behaviour: >
      稽核寫入與刪除**必須在同一個交易邊界內**——否則會出現「記憶沒了但沒稽核」
      的半套狀態，直接違反 FR4.7。任一失敗則兩者皆不生效
    source: FR4.7
    verified_by: AC4.2.2

  - id: BR4.3
    statement: 重複刪除已不存在的記憶回報「找不到」，不視為狀態改變
    category: policy
    applies_to: 刪除路徑
    trigger: 刪除一個已不存在的 memoryId
    logic: IF M 不存在 THEN 拋 MemoryNotFound；不產生稽核事件
    violation_behaviour: MemoryNotFound → 404
    source: K-08 的 retry_and_idempotency
    note: >
      **不產生稽核事件這一半很重要**：若產生，一個重試迴圈會為同一次刪除
      製造多筆稽核，使 AC4.3.2 的查詢結果失真

  # ── BR5 放寬可見範圍（FR4.3b、K-08）─────────────────────────────
  - id: BR5.1
    statement: 僅 Platform_Admin 與 Platform_Owner 得放寬可見範圍
    category: authorization
    applies_to: 放寬路徑
    trigger: 放寬請求
    logic: >
      IF principal P 要求放寬記憶 M 的可見範圍
      THEN 僅當 P 的角色為 Platform_Admin 或 Platform_Owner 時執行；否則拒絕
    violation_behaviour: MemoryForbidden(reason="scope") → 403 ＋ detail 前綴
    source: FR4.3b、K-08 的 scope_widening
    note: >
      **這是角色判定，與 BR4.1 的擁有者判定是兩套不同的模型。**
      擁有者本人**不能**放寬自己記憶的可見範圍——那是刻意的：
      FR4.3b 把放寬定為「獨立的、需授權的操作」

  - id: BR5.2
    statement: 放寬只有一個合法方向
    category: validation
    applies_to: 放寬路徑
    trigger: 放寬請求指定了目標範圍
    logic: >
      IF 目標範圍不比現行範圍寬（即現行為 platform，或目標為 owner）
      THEN 拒絕
    violation_behaviour: 拒絕並說明現行範圍與可用的目標範圍
    source: "[FD3]=A ＋ FR4.3b 的「放寬」語意"
    note: >
      兩值集合使「哪個更寬」可判定（owner < platform）。
      **收窄不在本操作的語意內**——FR4.3b 說的是「放寬」，
      收窄是否允許、由誰允許，上游未定（見 FD8-4）

  - id: BR5.3
    statement: 每一次放寬都留下一筆帶前後範圍的稽核事件
    category: constraint
    applies_to: 放寬路徑
    trigger: 放寬成功
    logic: >
      IF 記憶 M 的可見範圍由 S1 被 principal P 改為 S2
      THEN 產生一筆 action = scope_changed 的稽核事件，
      帶 previousScope = S1、newScope = S2、actorUserId = P、occurredAt = 當下
    violation_behaviour: 與 BR4.2 同——稽核與變更須在同一交易邊界內
    source: FR4.3b
    verified_by: AC4.3.1

  - id: BR5.4
    statement: 範圍未實際改變時不產生稽核事件
    category: policy
    applies_to: 放寬路徑
    trigger: 目標範圍等於現行範圍
    logic: IF S1 = S2 THEN 不變更、不產生事件
    violation_behaviour: >
      依 BR5.2 已先被拒絕（目標不比現行寬）。本條獨立列出是為了讓
      EC4（前後範圍須不同）有對應的行為規則
    source: EC4

  # ── BR6 稽核查詢（[FD2]=A、AC4.3.3）────────────────────────────
  - id: BR6.1
    statement: 僅 Platform_Admin 與 Platform_Owner 得讀取稽核事件
    category: authorization
    applies_to: 稽核查詢路徑
    trigger: 稽核查詢請求
    logic: >
      IF principal P 要求讀取稽核事件
      THEN 僅當 P 的角色為 Platform_Admin 或 Platform_Owner 時執行；否則拒絕
    violation_behaviour: MemoryForbidden(reason="scope") → 403 ＋ detail 前綴
    source: "[FD2]=A"
    verified_by: AC4.3.3
    note: >
      **與 BR5.1 共用同一組角色判定，刻意只有一份實作。**
      擁有者**看不到**自己記憶的稽核事件——`[FD2]` 的選項 B 被否決的理由是
      它會讓同一個端點有兩種過濾語意，而 AC4.3.3 的「被拒絕」在擁有者身上
      會變成「回空集合」，兩者是不同的可觀察結果

  - id: BR6.2
    statement: 使用者刪除事件可被稽核查詢取得
    category: calculation
    applies_to: 稽核查詢路徑
    trigger: 稽核查詢
    logic: >
      IF 查詢者通過 BR6.1
      THEN 結果包含 action = deleted_by_user 的事件；
      得選擇性以 memoryId 收斂
    violation_behaviour: 不適用
    source: FR4.7
    verified_by: AC4.3.2

  - id: BR6.3
    statement: 稽核事件的 memoryId 指不到記憶時仍須回傳該事件
    category: policy
    applies_to: 稽核查詢路徑
    trigger: 事件所描述的記憶已被刪除或清除
    logic: >
      IF 一筆稽核事件的 memoryId 已無對應記憶
      THEN **仍回傳該事件**，並讓呼叫端可分辨「記憶已不存在」這個狀態；
      不得過濾掉它，也不得因此失敗
    violation_behaviour: 不適用
    source: FR4.7、U5 的結構決定（稽核刻意比記憶活得久）
    note: >
      **過濾掉它會讓 FR4.7 在 90 天後變成空話**——稽核存在的全部理由就是
      記憶消失之後還答得出「誰刪的」。這是 DG-1 的直接後果，而 DG-1 已由
      U5 的結構定案為「如此設計」，非未決項

  # ── BR7 寫入端歸屬（[FD1]=B、[FD4]=A）──────────────────────────
  - id: BR7.1
    statement: episodic 記憶由大腦入口在每輪對話結束時寫入
    category: policy
    applies_to: 寫入端
    trigger: 一輪對話結束
    logic: IF 一輪對話結束 THEN U13 brain-gateway 寫入一筆 kind = episodic 的記憶
    violation_behaviour: 不適用
    source: "[FD1]=B"
    note: 新增一條 U13 → U8 的依賴邊，須送 delivery-planning（FD8-1）

  - id: BR7.2
    statement: procedure 記憶由工作編排器在工作項完成時寫入
    category: policy
    applies_to: 寫入端
    trigger: 一個工作項完成
    logic: IF 一個工作項完成 THEN U12 work-orchestrator 寫入一筆 kind = procedure 的記憶
    violation_behaviour: 不適用
    source: "[FD1]=B"
    note: 新增一條 U12 → U8 的依賴邊，須送 delivery-planning（FD8-1）

  - id: BR7.3
    statement: semantic 記憶由使用者經記憶頁手動建立
    category: policy
    applies_to: 寫入端
    trigger: 使用者主動建立
    logic: >
      IF 使用者經記憶頁提交一筆記憶
      THEN 經新增的建立端點寫入，kind 由使用者指定且限於封閉集合
    violation_behaviour: kind 不在封閉集合時拒絕
    source: "[FD4]=A"
    note: >
      **這條是 AC4.1.3 得以成立的原因**：少了它，semantic 永遠沒有資料，
      該 AC 的 Given「三種記憶各有資料」對 semantic 那一份不可構造。
      需新增建立端點（觸發 OpenAPI drift 閘門）

  - id: BR7.4
    statement: 記憶的建立**不**產生稽核事件
    category: policy
    applies_to: 所有寫入端
    trigger: 任何記憶寫入
    logic: IF 一則記憶被寫入 THEN 不產生任何稽核事件
    violation_behaviour: >
      嘗試產生會違反 action 的封閉集合（無建立值）並中止整個交易——
      即「寫入記憶」會連帶失敗
    source: >
      FR4.7（逐字只約束刪除動作）＋ action 的封閉集合。
      **本條裁決 contract-summary.md 的內部矛盾**：`:643` 宣稱 write 也寫稽核，
      `:1386` 只列 delete 與 widen_scope；後者與結構一致，故採後者
    note: 詳見 entities.md §二之二
```

## 二、規則摘要（由上方 YAML 衍生）

| 組 | 條數 | 關注點 | 授權模型 |
|---|---|---|---|
| `BR1` | 2 | 擁有者的寫入端強制 | 已驗證身分（賦值，非判定） |
| `BR2` | 3 | 可見範圍：預設、讀取過濾、封閉集合 | **擁有者 ＋ 可見範圍** |
| `BR3` | 5 | 檢索：三種皆可取、模型分群、無向量、已刪除、提供者不可用 | 承 `BR2.2` |
| `BR4` | 3 | 使用者刪除與其稽核 | **擁有者** |
| `BR5` | 4 | 放寬可見範圍的授權、方向、稽核 | **角色**（`Platform_Admin`／`Owner`） |
| `BR6` | 3 | 稽核查詢的授權與懸空參照的處理 | **角色**（同上） |
| `BR7` | 4 | 三種 kind 各自的寫入端 ＋ 建立不留稽核 | 承 `BR1` |
| **合計** | **22** | | |

### 2.1 本單元有兩套授權模型，不可互換

| | 判定依據 | 適用規則 | 違反時 |
|---|---|---|---|
| **擁有者模型** | 列的 `ownerUserId` 與呼叫者是否相同 | `BR2.2`（讀）、`BR4.1`（刪） | `reason="owner"` |
| **角色模型** | 呼叫者的平台角色 | `BR5.1`（放寬）、`BR6.1`（稽核查詢） | `reason="scope"` |

**最容易出的錯是用角色模型去判讀寫**：`Platform_Admin` 不因其角色而能讀或刪
他人的記憶（`BR4.1` 的 note）。它被授予的只有兩件事——放寬可見範圍與查稽核。

### 2.2 三條規則的結構層不設防，是本單元的義務

`BR2.3`（可見範圍封閉集合）、`EC4`／`EC5`（前後範圍的必填與互斥）
在已交付的結構層**沒有對應約束**（既有欄位無封閉約束，沿用 `U18` 的先例）。
故它們是**應用層的寫入端義務**，漏做的後果是髒資料而非寫入失敗——
這一點必須在 `code-generation` 有對應測試，不能靠資料庫擋。

## 三、無對應 AC 的規則（10 條，逐條附理由）

`traceability.json` 的 `reverse` 陣列逐條登錄；此處為人話版本。

| 規則 | 為何沒有 AC |
|---|---|
| `BR2.3` | 封閉集合的驗證規則，由 `[FD3]`=A 定案而非由某條 AC 要求 |
| `BR3.2` | 技術性約束（向量空間分群）。上游無 AC，但它是本單元**唯一完全靜默**的失敗模式——`code-generation` 必須有測試 |
| `BR3.3` | 技術性政策（fulltext 退路的直接後果） |
| `BR3.5` | 技術性政策（提供者偵測），`U6 embedding-port` 的契約已定其行為 |
| `BR4.3` | 冪等語意，來自 `K-08` 的 `retry_and_idempotency` 而非 AC |
| `BR5.1` | **`FR4.3b` 要求、`K-08` 指定，但上游沒有任何 AC 斷言「非管理員不能放寬」**。這是上游的 AC 缺口，不是本站的——見 `FD8-5` |
| `BR5.2` | 方向性規則，由 `[FD3]`=A 的兩值集合逼出 |
| `BR5.4` | `EC4` 的行為對應 |
| `BR6.3` | `FR4.7` ＋ `U5` 結構決定的直接後果；`DG-1` 已關閉故無人為它寫 AC |
| `BR7.4` | 本站裁決上游矛盾的結果，非需求項 |
