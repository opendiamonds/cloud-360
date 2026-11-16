# 業務規則 — `U5 memory-data`

> 本檔的 ```yaml 區塊是**規則的單一真實來源**。
> **計數一律由 parser 解析本區塊的 `rules[].id` 實算**，不以各群相加、不以 grep
> ——理由是 `U7` 的實測教訓：群組欄若漏列一群，相加仍會自洽。

```yaml
rules:
  # ---- BR1.x schema 隔離與 grant 邊界 ----
  - id: BR1.1
    statement: >
      記憶的兩張表必須位於**獨立 schema**，而非 `public`。
    category: constraint
    applies_to: memory.memory_records、memory.memory_audit_events
    trigger: 建立 schema 與表時
    logic: >
      `CREATE SCHEMA IF NOT EXISTS memory`；兩張表皆以 `memory.` 前綴建立。
      形式為「同一個 PostgreSQL database 內的獨立 schema」，**不是獨立 database**
      ——刻意保留原生跨 schema join 能力（契約 K-05 的 `schema_isolation.form` 逐字）。
    violation_behaviour: >
      表落在 `public` 時，`BR1.2` 的 grant 邊界**完全失效**——它的整個作用方式
      是「只開放 memory schema」。落在 `public` 則該 grant 不構成任何限制，
      而這在功能上看不出來：讀寫一切正常，只是邊界不存在。
    source: >
      `FR4.4` 逐字「資料庫層的邊界以『grant 只開放記憶 schema』承載」；
      契約 K-05 的 `schema_isolation`。**本 repo 零前例**
      （全樹無 `CREATE SCHEMA`、無 `search_path`），故無既有形狀可照抄。

  - id: BR1.2
    statement: >
      grant **只開放記憶 schema**，不開放 `public` 的寫入。
    category: authorization
    applies_to: 記憶層使用的資料庫角色
    trigger: 設定 grant 時
    logic: >
      對記憶層角色授予 `memory` schema 的 USAGE 與兩表的 DML；
      **不授予** `public` schema 的寫入權。跨 schema 讀取 `public.users`
      所需的最小權限單獨授予。
    violation_behaviour: >
      邊界消失。這是**資料庫層**的唯一邊界——列層級的擁有者與可見範圍授權
      由契約 `K-08` 的 facade 承擔（K-05 的 `authorization_responsibility` 逐字），
      兩者不可互相替代：facade 擋應用層呼叫，grant 擋「繞過應用層直連資料庫」。
    source: FR4.4、契約 K-05 的 `behaviour_semantics.authorization_responsibility`

  - id: BR1.3
    statement: >
      全部 DDL 與 grant 必須可重跑（idempotent）。
    category: constraint
    applies_to: 本單元的全部 DDL 與 grant 敘述
    trigger: CI job 或部署路徑重跑時
    logic: >
      `CREATE SCHEMA IF NOT EXISTS`／`CREATE TABLE IF NOT EXISTS`／
      `CREATE INDEX IF NOT EXISTS`；重複 GRANT 無害。
    violation_behaviour: >
      CI job 與部署路徑皆可能重跑，不可重跑的敘述會讓第二次執行失敗。
    source: >
      契約 K-05 的 `retry_and_idempotency` 逐字。**附帶一個與 `U4` 的重要差別**：
      本單元**無資料遷移**，故無 `K-04` 那類的重跑風險（同處逐字）。

  # ---- BR2.x 稽核軌跡（DG-1 的處置）----
  - id: BR2.1
    statement: >
      `memory_audit_events` **不對 `memory_records` 設外鍵**，稽核獨立於記憶存活。
    category: constraint
    applies_to: memory_audit_events.memoryId
    trigger: 建表時
    trigger_detail: 以及每一次 90 天清除
    logic: >
      `memoryId` 存為不透明識別值，無 FOREIGN KEY 子句。
      記憶被清除後，其稽核事件**原樣保留且仍可查**。
    violation_behaviour: >
      設了外鍵就必須在兩個壞結果中選一個，而**兩者都違反已核可需求**：
      `ON DELETE CASCADE` 使 `FR4.7`（刪除動作留稽核）在 90 天後實質失效
      ——記錄與被記錄的對象一起消失；
      `ON DELETE RESTRICT` 則讓 `FR4.5`（逾期自動刪除）無法執行。
    source: >
      **`DG-1` 的處置**（契約 K-05 的具名缺口，`landing` 指名本站；
      並為 `bolt-plan.md:186` 的 **B1 進入條件**）。
      使用者裁決 `[M1]`=A（2026-10-06）。

  - id: BR2.2
    statement: >
      稽核表**不得含記憶內容**（`content`、`embedding`）。
    category: constraint
    applies_to: memory_audit_events
    trigger: 建表時與任何後續欄位擴充
    logic: >
      表定義只含識別碼、行為者、動作、範圍轉換與時間戳。
    violation_behaviour: >
      **這是 `BR2.1` 能成立的前提，不是獨立的潔癖。** 稽核事件比記憶本體活得久
      （`BR2.1`），所以若它含記憶內容，「保留稽核」就等於「保留被刪除的
      使用者資料」，`FR4.5` 的 90 天刪除形同虛設——**使用者會以為資料刪了，
      而它還在稽核表裡**。
    source: >
      契約 K-05 的 `key_columns` 本來就沒有這兩欄；本站確認並寫明它與
      `BR2.1` 的依存關係。

  - id: BR2.3
    statement: >
      `action` 必須區分 `deleted_by_user` 與 `purged_by_retention`。
    category: constraint
    applies_to: memory_audit_events.action
    trigger: 寫入稽核事件時
    logic: >
      封閉列舉 `[deleted_by_user, purged_by_retention, scope_changed]`，
      以 CHECK 約束承載。
    violation_behaviour: >
      合併成單一「deleted」會讓**使用者主動刪除**（`FR4.6`）與
      **系統逾期清除**（`FR4.5`）在稽核上不可分辨，而兩者的法遵意義不同
      ——前者是使用者行使刪除權，後者是保存期到期。
      調查時無法回答「這筆是他自己刪的還是系統清的」。
    source: FR4.5、FR4.6、FR4.7 三者併讀

  - id: BR2.4
    statement: >
      90 天清除產生的稽核事件，其 `actorUserId` 為**系統行為者**。
    category: constraint
    applies_to: memory_audit_events.actorUserId
    trigger: 清除作業寫入稽核事件時
    logic: >
      清除是排程觸發、無人在迴圈內（`FR4.5a`），故**沒有自然的使用者**。
      以一個保留的系統行為者識別值承載，且 `action` 必為
      `purged_by_retention`（與 `BR2.3` 互相印證）。
    violation_behaviour: >
      兩種錯誤做法都有害：填記憶的擁有者，會讓稽核**謊稱是使用者刪的**
      （與 `BR2.3` 的區分互相矛盾）；留 NULL 則讓欄位可空，
      而 `actorUserId` 可空會讓「誰做的」這個稽核核心問題在**所有**事件上
      都失去強制力。
    source: >
      `FR4.5a` 逐字「排程觸發、無人在迴圈內」。
      **本條與 `U7 hierarchy-service` 那條「變更紀錄的行為者取值」規則是同一個
      問題的兩面**（刻意不寫該規則的編號——跨單元的 `BR` 編號會被本單元的
      traceability sensor 判為孤兒規則）：那裡要求「不得預設為
      session 擁有者」，這裡要求「不得假裝有使用者」。

  # ---- BR3.x 向量與 embeddingModel（最重要的不變量）----
  - id: BR3.1
    statement: >
      每列記憶必帶 `embeddingModel`，且**相似度檢索只比對同一 `embeddingModel`
      的列**。
    category: constraint
    applies_to: memory_records.embeddingModel、全部向量檢索查詢
    trigger: 寫入記憶時；每一次相似度檢索
    logic: >
      欄位為 NOT NULL；檢索查詢必須含 `WHERE embedding_model = :model` 條件。
    violation_behaviour: >
      **這是本單元最危險的失敗模式，因為它是靜默的。**
      契約 K-05 的 `invariants` 逐字：「**同維度不等於同向量空間**，
      不加這道過濾會讓跨模型的檢索回垃圾**且不報錯**」（decisions.md ADR-008）。
      兩個不同模型都產生 1024 維向量，所以型別、維度、索引全部正常，
      查詢成功回傳結果——**只是結果在語意上毫無意義**。
      沒有任何錯誤訊息、沒有任何例外、沒有任何監控會發現。
    source: 契約 K-05 的 `invariants` 第一條；decisions.md ADR-008

  - id: BR3.2
    statement: >
      向量維度固定為 **1024**。
    category: constraint
    applies_to: memory_records.embedding
    trigger: 建表時
    logic: >
      `vector(1024)`。與 `OLLAMA_EMBED_MODEL` 預設 `bge-m3` 的 dense 維度一致。
    violation_behaviour: >
      維度不符會在寫入時被 pgvector 擋下（這一項**不是**靜默的），
      但換模型時若新模型維度不同，整欄需要重建而非改設定。
    source: >
      契約 K-01 對 `OLLAMA_EMBED_MODEL` 的 validation 逐字
      「其 dense 維度須為 1024（與 `vector(1024)` 欄位一致）」。

  - id: BR3.3
    statement: >
      `embedding` 為 NULL 是**有意義的狀態**，不是缺漏。
    category: policy
    applies_to: memory_records.embedding
    trigger: fulltext 模式下建立記憶時
    logic: >
      欄位可為空。`fulltext` 模式下建立的列其 `embedding` 為 NULL，
      之後**不會被向量檢索看到，除非重新 embed**。
      `embeddingModel` 在此情況下**仍然必填**（記錄這列是以何種方式產生的）。
    violation_behaviour: >
      不適用——本條是**誠實宣告**。寫下它的理由：把 NULL 當成資料缺陷而去
      「修補」它（例如回填一個預設模型名、或把欄位改成 NOT NULL），
      會破壞 `fulltext` 模式；而把它當成「已 embed」則會讓那些列
      永遠查不到卻無人知道原因。
    source: 契約 K-05 的 `invariants` 第二條逐字

  # ---- BR4.x 保存期 ----
  - id: BR4.1
    statement: >
      **只有 `kind = episodic` 受 90 天保存期約束。**
    category: constraint
    applies_to: memory_records.kind、memory_records.expiresAt
    trigger: 寫入記憶時；清除作業選列時
    logic: >
      `kind` 為 `episodic` 時 `expiresAt` 必填（`createdAt` ＋ 90 天）；
      另兩種 kind 的 `expiresAt` 為 NULL。以 CHECK 約束承載這個條件必填。
    violation_behaviour: >
      `FR4.5` 逐字只約束「episodic memory」。把 90 天套到 semantic／procedure
      會**刪掉不該刪的長期記憶**；反之，若 `expiresAt` 因漏填而為 NULL，
      那列 episodic 記憶會**永久留存且沒有任何跡象**——清除作業是依
      `expiresAt` 選列的，NULL 永遠不會被選中。故這個條件必填要寫進資料層，
      不能只靠寫入端自律。
    source: FR4.5 逐字限定 episodic；本站補 CHECK 的理由為上述靜默失敗

  - id: BR4.2
    statement: >
      清除作業**不得**由 `backend/` 內的排程程式承載。
    category: constraint
    applies_to: 90 天清除的承載形式
    trigger: 實作清除機制時
    logic: >
      必須以 gh-aw 或 GitHub Actions workflow 承載（交付物 `N-6`）。
      **決定性的映射邏輯**（算出哪些列逾期、發出刪除）應放在**純 Actions 步驟**，
      不交給 gh-aw 的 LLM 路徑。
    violation_behaviour: >
      違反 `project.md ## Forbidden` 的明文禁令——該條的邊界判準逐字為
      「由事件或排程觸發、無人在迴圈內的屬本條禁止範圍」，而 90 天清除正落在其中。
      交給 LLM 路徑則落入本 repo 三塊結構性盲區之一（「所有 LLM 路徑」）。
    source: >
      `FR4.5a` 逐字；`project.md ## Forbidden`。
      **本單元不實作它**——本單元是 `spec`，交付 schema。
      清除機制是 `U9 memory-purge` ＋ `N-6`，落點不在本站（`OPEN-M3`）。

  - id: BR4.3
    statement: >
      清除動作本身必須留稽核紀錄。
    category: constraint
    applies_to: 清除作業
    trigger: 每一次清除
    logic: >
      每刪除一列 episodic 記憶，寫入一筆 `action = purged_by_retention`
      的稽核事件（`BR2.3`），行為者為系統（`BR2.4`）。
    violation_behaviour: >
      `FR4.7` 失效。而因為 `BR2.1` 已讓稽核獨立於記憶存活，
      這筆事件在記憶被刪後**仍然可查**——這正是 `DG-1` 處置的目的。
    source: FR4.5a 的子項逐字「清除動作本身仍須留稽核紀錄（承 FR4.7）」、FR4.7
```

## 本檔的範圍（先說不管什麼，避免下游誤讀）

本單元是 `spec`：交付 **schema ＋ grant ＋ 向量欄位**。下列 13 條規則**全部是
資料層與其不變量**，沒有一條是應用層行為——本單元沒有函式、沒有端點、沒有畫面。

**不在本檔的三件事**（詳見 `functional-spec.md` §四）：列層級的擁有者與可見範圍
授權（屬契約 `K-08` 的 facade）、embedding 的產生（屬 `U6`）、
90 天清除的執行（屬 `U9` ＋ 交付物 `N-6`）。

## 規則摘要（衍生檢視）

| 群組 | 條數 | 管什麼 | 其中「誠實宣告」而非禁令 |
|---|---|---|---|
| `BR1.x` | 3 | schema 隔離、grant 邊界、可重跑 | — |
| `BR2.x` | 4 | 稽核軌跡（`DG-1` 的處置）、不含內容、動作分類、系統行為者 | — |
| `BR3.x` | 3 | `embeddingModel` 過濾、維度、NULL 的語意 | `BR3.3` |
| `BR4.x` | 3 | 只有 episodic 受保存期、承載形式、清除留稽核 | — |

合計 **13 條**（由 `yaml.safe_load` 解析本檔 yaml 區塊、取 `rules[].id` 實算；
逐群 3＋4＋3＋3＝13，兩者相符）。

### 本單元最危險的一條

`BR3.1`（`embeddingModel` 過濾）。其餘 12 條的違反都會產生錯誤、擋下寫入或
留下可見痕跡；**只有 `BR3.1` 的違反是完全靜默的**——查詢成功、型別正確、
維度相符，回傳的結果在語意上是垃圾而沒有任何跡象。
故它的驗證不能只靠「有沒有寫 WHERE 條件」的程式碼審查，而需要一個
以兩種 `embeddingModel` 寫入、斷言檢索不跨模型的測試（落點 `N-2` 的真實 PG job）。
