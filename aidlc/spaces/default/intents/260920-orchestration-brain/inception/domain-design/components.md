# Components — 統一入口大腦

<!-- Stage: domain-design（Inception 2.6）· Record: 260920-orchestration-brain
     lead: aidlc-architect-agent · support: aidlc-aws-platform-agent, aidlc-design-agent -->

## 這份檔在做什麼

識別本 intent 要**寫程式**的邏輯建構塊。依 stage 檔的定義：元件是「有自己商業邏輯、
實體與生命週期的一段軟體」；**資料庫、快取、佇列、第三方服務是元件的依賴，不是元件**
——它們一律列在 `external_dependencies`。

本站**不決定**部署拓樸（那是 `units-generation` 的事）、**不選**技術棧或 NFR 手法
（那是 NFR 與 infrastructure 階段的事）。實體只記到**歸屬與形狀**層級——哪個元件擁有它、
識別欄位、屬性名稱、跨元件參照；**不記**資料型別、驗證約束、允許值與關係基數，
那份完整 schema 屬 functional-design。

**規模**：6 個元件、7 個實體、8 條 `depends_on` 邊、
13 項外部依賴。以上四個數字皆由下方 YAML 實算，非目測。

---

## Part A — 機讀目錄（本檔的真實來源）

下方 YAML 是這份檔的**單一真實來源**，Part B 的所有表格與圖皆由它以腳本衍生，
不是手抄。

```yaml
components:
  - name: BrainGateway
    summary: 大腦對外的唯一 WebSocket 端點；訊息封包的編解與串流
    behaviour: >
      掛在 /api/ 之下（nginx 的 location /api/ 是唯一帶 Upgrade 標頭者，location /
      走 try_files 會回 HTML）。握手認證的 token 走 Sec-WebSocket-Protocol 標頭或
      握手後首則訊息，不得放 query string。握手時以 record=True 呼叫既有的
      get_user_from_token，使 users.last_activity_at 照常更新（既有 WS 前例用
      record=False，照抄會讓帳號活動稽核對大腦使用者靜默失效）。每一則進入的使用者
      文字先過既有 prompt_guard，命中即不呼叫任何 LLM 並回固定拒絕訊息。
      對外訊息型別至少含 clarify、work_items、cost_card、token、done、error；
      clarify 的候選帶 id/label/capability，信心值為選填且不得列為必填。
      不得在事件迴圈上做同步 LLM 呼叫。
    responsibilities:
      - WebSocket 連線生命週期與握手認證
      - 訊息封包的型別契約（前後端共用來源，CI 一致性檢查的受檢對象）
      - 大腦回覆的 token 串流轉送
      - 每則輸入的 prompt_guard 預檢
    depends_on:
      - component: IntentRouter
        interaction: 把使用者輸入交給它判定意圖與信心值
        style: sync
      - component: SessionContext
        interaction: 取出與更新該連線的作業對象與共享狀態
        style: sync
      - component: WorkOrchestrator
        interaction: 取工作項集合以推送 work_items 訊息；轉送使用者的逐項更正
        style: sync
    dependents: []
    external_dependencies:
      - name: nginx
        kind: other
        purpose: 反向代理；WS 路徑受其 location /api/ 限制
      - name: Cloudflare Tunnel
        kind: other
        purpose: 對外暴露；已為 WS 設 tcpKeepAlive 30s
    entities: []

  - name: IntentRouter
    summary: 把一句自然語言判定為意圖類別並輸出可與門檻比較的信心值
    behaviour: >
      必須輸出 0–1 的信心值（這是獨立需求，不是門檻判定的前提句——若實作出不輸出
      信心值的路由層，反問路徑會靜默永不觸發而文件上看起來已解決）。信心值 < 0.7
      即不交辦、不產生任何結果，改產生 clarify 候選。一句含 N 個可分離意圖者輸出
      N 個意圖。若最終模型無法提供可用信心訊號，觸發條件改以「候選並列且無單一
      最高分」表達，畫面不變、本元件對外介面不變。
    responsibilities:
      - 意圖分類與信心值輸出
      - 多意圖拆解
      - 信心不足時產生候選判讀清單
      - 多輪對話的指涉詞解析（第 N 輪指向第 N−1 輪產出）
    depends_on:
      - component: SessionContext
        interaction: 讀當前作業對象與對話歷程以解析指涉詞
        style: sync
      - component: MemoryStore
        interaction: 讀該使用者的語意與程序記憶以輔助判定
        style: sync
    dependents:
      - component: BrainGateway
        interaction: 把使用者輸入交給它判定
    external_dependencies:
      - name: OpenRouter
        kind: third-party-api
        purpose: 路由層 LLM 呼叫（模型定案為 nfr-requirements 的待辦）
    entities: []

  - name: SessionContext
    summary: 作業對象、共享↔獨立狀態與對話歷程的單一來源，外部化於 Redis
    behaviour: >
      一律放 Redis，不得放行程記憶體——重啟 backend 後既有對話的脈絡與作業對象
      須完整還原。作業對象、共享／獨立狀態、工作項集合放在同一個 session key 之下，
      TTL 24 小時、每次互動續期；TTL 到期三者一起消失，下次進入即為全新 session
      且作業對象回到未選定。共享工作階段涵蓋統一入口、/workspace、/assessment 三處，
      不含 /admin/* 與 /cost。子功能頁得開啟不共享訊息歷程但沿用當前作業對象的
      獨立對話。
    responsibilities:
      - 作業對象（專案／系統／架構圖三層）的持有與切換
      - 共享↔獨立對話的狀態
      - 對話歷程的暫存與跨頁面延續
      - session 的存活期與清除（TTL 續期）
    depends_on:
      - component: ProjectHierarchy
        interaction: 驗證並解析作業對象的三層識別
        style: sync
    dependents:
      - component: BrainGateway
        interaction: 取出與更新該連線的作業對象
      - component: IntentRouter
        interaction: 讀作業對象與歷程以解析指涉詞
      - component: WorkOrchestrator
        interaction: 工作項集合隨 session 存放與清除
    external_dependencies:
      - name: Redis
        kind: cache
        purpose: session 狀態外部化；第 5 個部署服務
    entities:
      - name: BrainSession
        identifier: sessionKey
        attributes: [sessionKey, userId, currentProjectId, currentSystemId, currentDiagramId, sharingMode, messageHistory, expiresAt]
        references:
          - entity: Project
            owned_by: ProjectHierarchy
            relationship: 每個 session 最多指向一個目前專案
          - entity: System
            owned_by: ProjectHierarchy
            relationship: 每個 session 最多指向一個目前系統

  - name: WorkOrchestrator
    summary: 工作項的狀態機、多意圖的依序交辦、逐項更正，以及對既有能力的呼叫
    behaviour: >
      每個工作項帶一個狀態，狀態值集合不得少於五個：處理中／等待中／完成／失敗／
      已停掉。等待中用於依賴前一項結果者；已停掉用於使用者更正後的終止狀態，
      且該項必須帶 sideEffect 欄位（none／unknown／說明文字）讓畫面能誠實說出
      有沒有留下東西——unknown 是合法值，因為系統不承諾停掉時不留半成品。
      更正為逐項，其餘工作項不受影響。呼叫既有成本能力一律走 HTTP 並帶使用者
      token，使既有的 require_story_action("C1", …) 照常執行，不得同進程直呼
      service 層繞過授權。把成本 job 的五種狀態事件轉譯進自己的訊息流，不等 job
      完成才開始回覆，且不做 token 級巢狀串流轉送（來源端沒有逐字可轉）。
    responsibilities:
      - 工作項集合與其狀態轉換
      - 多意圖的拆解結果落為 N 個工作項並決定交辦順序
      - 逐項更正（停掉某項並改交辦）
      - 呼叫既有 A1／A3／C1 能力並轉譯其回應與狀態事件
    depends_on:
      - component: SessionContext
        interaction: 工作項集合隨 session 存放；讀作業對象決定交辦目標
        style: sync
      - component: ProjectHierarchy
        interaction: 架構圖被異動時寫入變更紀錄
        style: sync
    dependents:
      - component: BrainGateway
        interaction: 取工作項集合以推送；轉送逐項更正
    external_dependencies:
      - name: 既有 A1／A3 端點
        kind: other
        purpose: 架構圖生成與 Well-Architected 檢視，經 HTTP 呼叫
      - name: 既有 C1 端點 /api/cost/v1
        kind: other
        purpose: 成本估價；HTTP 帶使用者 token 以保留既有授權
    entities:
      - name: WorkItem
        identifier: workItemId
        attributes: [workItemId, sessionKey, label, status, capability, waitingOn, failureReason, sideEffect, createdAt]
        references:
          - entity: BrainSession
            owned_by: SessionContext
            relationship: 每個工作項屬於一個 session

  - name: MemoryStore
    summary: 語意／程序／情節三種記憶的持有、授權、檢索與稽核
    behaviour: >
      三種記憶落在同一個 PostgreSQL database 的獨立 schema，以保留原生跨 schema
      join 能力；資料庫層的邊界以「grant 只開放記憶 schema」承載。每一列記憶帶
      擁有者與可見範圍欄位，讀取一律經過該模型。擁有者由本元件在寫入時依呼叫者的
      已驗證身分設定，不得由呼叫方自行指定。可見範圍預設為最窄（僅擁有者可見）；
      放寬可見範圍是一個獨立的、需授權的操作，僅 Platform_Admin 與 Platform_Owner
      得為之，且每次變更須留稽核紀錄（誰、何時、由什麼範圍改為什麼範圍）。
      使用者得刪除自己的記憶，刪除動作本身須留稽核紀錄。情節記憶保存 90 天，
      逾期自動刪除由 gh-aw／GitHub Actions workflow 承載，不得是 backend 內的
      排程程式；清除動作亦須留稽核。檢索以 pgvector 的向量相似度進行，向量由 EmbeddingPort 產生。該 Port 有四個
      實作並由設定切換：ollama（bge-m3，1024 維，staging 用）、fastembed
      （multilingual-e5-large，1024 維，行程內，本機無 Ollama 時用）、fulltext
      （不算向量，退回 PostgreSQL 全文檢索）、stub（決定性替身，CI 用）。
      向量欄位為 vector(1024)，兩個向量提供者同維度故可共用。每列記憶存
      embeddingModel；相似度檢索只比對同一 embeddingModel 的列——同維度不等於同
      向量空間，不加這道過濾會讓跨模型的檢索回垃圾且不報錯。fulltext 模式下建立的
      列其向量為 NULL，之後不會被向量檢索看到，除非重新 embed。偵測不到選定的
      提供者時必須大聲失敗並列出可選值，不得靜默降級為全文檢索。
    responsibilities:
      - 三種記憶的讀寫與其獨立 schema
      - 擁有者與可見範圍的寫入端強制（最小權限）
      - 可見範圍放寬的授權與稽核
      - 使用者自行刪除與其稽核
      - 語意相似度檢索（經 EmbeddingPort 取得向量，依 embeddingModel 分群比對）
      - EmbeddingPort 的提供者選擇與其不可用時的大聲失敗
    depends_on: []
    dependents:
      - component: IntentRouter
        interaction: 讀語意與程序記憶以輔助意圖判定
    external_dependencies:
      - name: PostgreSQL（記憶 schema）
        kind: database
        purpose: 三種記憶的持久化；獨立 schema ＋ grant 邊界
      - name: pgvector
        kind: database
        purpose: 向量欄位與相似度索引；需 pgvector/pgvector:pg16 image
      - name: Ollama（bge-m3）
        kind: other
        purpose: staging 的 embedding 運算；第 6 個部署服務，零 API 費用
      - name: fastembed（multilingual-e5-large）
        kind: other
        purpose: 本機無 Ollama 時的行程內 embedding；ONNX、不拉 torch、不加服務
      - name: gh-aw／GitHub Actions workflow
        kind: other
        purpose: 90 天逾期清除的承載形式
    entities:
      - name: MemoryRecord
        identifier: memoryId
        attributes: [memoryId, kind, ownerUserId, visibilityScope, content, embedding, embeddingModel, createdAt, expiresAt]
        references: []
      - name: MemoryAuditEvent
        identifier: auditEventId
        attributes: [auditEventId, memoryId, actorUserId, action, previousScope, newScope, occurredAt]
        references:
          - entity: MemoryRecord
            owned_by: MemoryStore
            relationship: 每筆稽核事件指向一列記憶

  - name: ProjectHierarchy
    summary: 專案 → 系統 → 架構圖 的三層資料模型、建立路徑、既有圖遷移與變更紀錄
    behaviour: >
      一個專案有多個系統、一個系統對應一份架構圖檔與其中多張圖。讀、建立、修改、
      刪除一律經 require_story_action（story id K2），不得有任何繞過該 dependency
      的路徑，含同進程直呼 service 層。建立路徑有兩個使用者入口（脈絡列選單的
      表單、對話式建立的確認卡）但共用同一條寫入路徑，授權檢查、稽核紀錄與錯誤
      訊息各只有一份。既有架構圖的遷移為每個持有圖的使用者建立「預設專案／預設
      系統」並把其現有圖掛入；user_diagrams.user_id 保留為「誰建的」，新增
      nullable 的 system_id 作為「屬於哪個系統」，並明訂 system_id 為歸屬的權威
      來源。遷移後架構圖表中 system_id IS NULL 的列數必須為 0，不為 0 時遷移程序
      須大聲失敗，不得以警告帶過。架構圖每次被異動時寫入一列變更紀錄，帶來源需求
      的摘要與一個輕量標籤（不建 Requirement 實體、不建多對多關聯表）。
    responsibilities:
      - 專案與系統的資料模型與生命週期
      - 架構圖對系統的歸屬
      - 既有圖的遷移與其回復方式
      - 建立路徑的單一寫入端與授權
      - 架構圖變更紀錄（來源需求摘要與標籤）
    depends_on: []
    dependents:
      - component: SessionContext
        interaction: 驗證並解析作業對象的三層識別
      - component: WorkOrchestrator
        interaction: 架構圖被異動時寫入變更紀錄
    external_dependencies:
      - name: PostgreSQL（主 schema）
        kind: database
        purpose: projects／systems／變更紀錄的持久化
      - name: 既有 user_diagrams 表
        kind: database
        purpose: 遷移的對象；新增 nullable system_id
    entities:
      - name: Project
        identifier: projectId
        attributes: [projectId, name, ownerUserId, createdAt]
        references: []
      - name: System
        identifier: systemId
        attributes: [systemId, projectId, name, createdAt]
        references:
          - entity: Project
            owned_by: ProjectHierarchy
            relationship: 每個系統屬於一個專案
      - name: DiagramChangeRecord
        identifier: changeRecordId
        attributes: [changeRecordId, diagramId, actorUserId, requirementSummary, requirementLabel, occurredAt]
        references:
          - entity: System
            owned_by: ProjectHierarchy
            relationship: 每筆變更紀錄經架構圖上溯到一個系統
```

### Well-formedness 驗證結果

stage 檔列了 8 條規則，本站以腳本逐條驗證（非目測）：

| 規則 | 結果 |
|---|---|
| 元件名稱唯一 | ✓ 6 個名稱無重複 |
| 每個 `component:`／`owned_by` 都指向已宣告元件 | ✓ |
| 無元件依賴自己 | ✓ |
| `depends_on`／`dependents` 對稱 | ✓ 正向 8 邊、由 `dependents` 反推 8 邊，對稱差集為空 |
| 每個實體恰由一個元件擁有且有 identifier | ✓ 7 個實體 |
| 每個 `references.entity` 在其 `owned_by` 下已宣告 | ✓ |
| 依賴圖無環 | ✓ （DFS 三色法實測，無刻意保留的環） |
| 基礎設施不作為元件 | ✓ PostgreSQL／pgvector／Redis／Ollama／fastembed／nginx／Cloudflare Tunnel／既有端點皆列於 `external_dependencies` |

---

## Part B — 人讀視圖（由 Part A 衍生）

### Component Diagram

```mermaid
graph TD
    BrainGateway["BrainGateway"]
    IntentRouter["IntentRouter"]
    SessionContext["SessionContext"]
    WorkOrchestrator["WorkOrchestrator"]
    MemoryStore["MemoryStore"]
    ProjectHierarchy["ProjectHierarchy"]
    BrainGateway -->|"把使用者輸入交給它判定意圖與信心值"| IntentRouter
    BrainGateway -->|"取出與更新該連線的作業對象與共享狀態"| SessionContext
    BrainGateway -->|"取工作項集合以推送 work_items…"| WorkOrchestrator
    IntentRouter -->|"讀當前作業對象與對話歷程以解析指涉詞"| SessionContext
    IntentRouter -->|"讀該使用者的語意與程序記憶以輔助判定"| MemoryStore
    SessionContext -->|"驗證並解析作業對象的三層識別"| ProjectHierarchy
    WorkOrchestrator -->|"工作項集合隨 session 存放；讀作…"| SessionContext
    WorkOrchestrator -->|"架構圖被異動時寫入變更紀錄"| ProjectHierarchy
```

<!-- Text fallback: BrainGateway 依賴 IntentRouter（判定意圖）、SessionContext
（取用作業對象）與 WorkOrchestrator（取工作項、轉送更正）。IntentRouter 依賴
SessionContext（解析指涉詞）與 MemoryStore（讀語意與程序記憶）。SessionContext
依賴 ProjectHierarchy（解析三層識別）。WorkOrchestrator 依賴 SessionContext
（工作項隨 session 存放）與 ProjectHierarchy（寫變更紀錄）。MemoryStore 與
ProjectHierarchy 不依賴任何元件，是兩個葉節點。 -->

### Component Summary

| Component | Purpose | Depends On | Dependents | Entities Owned |
|---|---|---|---|---|
| `BrainGateway` | 大腦對外的唯一 WebSocket 端點；訊息封包的編解與串流 | IntentRouter、SessionContext、WorkOrchestrator | — | — |
| `IntentRouter` | 把一句自然語言判定為意圖類別並輸出可與門檻比較的信心值 | SessionContext、MemoryStore | BrainGateway | — |
| `SessionContext` | 作業對象、共享↔獨立狀態與對話歷程的單一來源，外部化於 Redis | ProjectHierarchy | BrainGateway、IntentRouter、WorkOrchestrator | BrainSession |
| `WorkOrchestrator` | 工作項的狀態機、多意圖的依序交辦、逐項更正，以及對既有能力的呼叫 | SessionContext、ProjectHierarchy | BrainGateway | WorkItem |
| `MemoryStore` | 語意／程序／情節三種記憶的持有、授權、檢索與稽核 | — | IntentRouter | MemoryRecord、MemoryAuditEvent |
| `ProjectHierarchy` | 專案 → 系統 → 架構圖 的三層資料模型、建立路徑、既有圖遷移與變更紀錄 | — | SessionContext、WorkOrchestrator | Project、System、DiagramChangeRecord |

### Entity Ownership

| Entity | Owning Component | Identifier | Attributes | References |
|---|---|---|---|---|
| `BrainSession` | `SessionContext` | `sessionKey` | `sessionKey`、`userId`、`currentProjectId`、`currentSystemId`、`currentDiagramId`、`sharingMode`、`messageHistory`、`expiresAt` | Project（ProjectHierarchy）；System（ProjectHierarchy） |
| `WorkItem` | `WorkOrchestrator` | `workItemId` | `workItemId`、`sessionKey`、`label`、`status`、`capability`、`waitingOn`、`failureReason`、`sideEffect`、`createdAt` | BrainSession（SessionContext） |
| `MemoryRecord` | `MemoryStore` | `memoryId` | `memoryId`、`kind`、`ownerUserId`、`visibilityScope`、`content`、`embedding`、`embeddingModel`、`createdAt`、`expiresAt` | — |
| `MemoryAuditEvent` | `MemoryStore` | `auditEventId` | `auditEventId`、`memoryId`、`actorUserId`、`action`、`previousScope`、`newScope`、`occurredAt` | MemoryRecord（MemoryStore） |
| `Project` | `ProjectHierarchy` | `projectId` | `projectId`、`name`、`ownerUserId`、`createdAt` | — |
| `System` | `ProjectHierarchy` | `systemId` | `systemId`、`projectId`、`name`、`createdAt` | Project（ProjectHierarchy） |
| `DiagramChangeRecord` | `ProjectHierarchy` | `changeRecordId` | `changeRecordId`、`diagramId`、`actorUserId`、`requirementSummary`、`requirementLabel`、`occurredAt` | System（ProjectHierarchy） |

### External Dependencies

| Component | Dependency | Kind | Purpose |
|---|---|---|---|
| `BrainGateway` | nginx | `other` | 反向代理；WS 路徑受其 location /api/ 限制 |
| `BrainGateway` | Cloudflare Tunnel | `other` | 對外暴露；已為 WS 設 tcpKeepAlive 30s |
| `IntentRouter` | OpenRouter | `third-party-api` | 路由層 LLM 呼叫（模型定案為 nfr-requirements 的待辦） |
| `SessionContext` | Redis | `cache` | session 狀態外部化；第 5 個部署服務 |
| `WorkOrchestrator` | 既有 A1／A3 端點 | `other` | 架構圖生成與 Well-Architected 檢視，經 HTTP 呼叫 |
| `WorkOrchestrator` | 既有 C1 端點 /api/cost/v1 | `other` | 成本估價；HTTP 帶使用者 token 以保留既有授權 |
| `MemoryStore` | PostgreSQL（記憶 schema） | `database` | 三種記憶的持久化；獨立 schema ＋ grant 邊界 |
| `MemoryStore` | pgvector | `database` | 向量欄位與相似度索引；需 pgvector/pgvector:pg16 image |
| `MemoryStore` | Ollama（bge-m3） | `other` | staging 的 embedding 運算；第 6 個部署服務，零 API 費用 |
| `MemoryStore` | fastembed（multilingual-e5-large） | `other` | 本機無 Ollama 時的行程內 embedding；ONNX、不拉 torch、不加服務 |
| `MemoryStore` | gh-aw／GitHub Actions workflow | `other` | 90 天逾期清除的承載形式 |
| `ProjectHierarchy` | PostgreSQL（主 schema） | `database` | projects／systems／變更紀錄的持久化 |
| `ProjectHierarchy` | 既有 user_diagrams 表 | `database` | 遷移的對象；新增 nullable system_id |

### Rationale — 為什麼每個都是獨立的建構塊

| Component | 獨立的理由 | 判準 |
|---|---|---|
| `BrainGateway` | 它是**協定層**：WebSocket 生命週期、訊息封包型別、串流轉送。這些會因為傳輸協定變更而改，與商業邏輯的變更理由完全不同；且它是 NFR5／N-1 要求的契約閘門的唯一受檢對象 | distinct concern、distinct change rate |
| `IntentRouter` | 它是唯一呼叫路由層 LLM 的地方，而模型選型尚未定案（`OQ-4`／`OQ-10` 指派 `nfr-requirements`）。模型換掉時只有它要改 | distinct change rate、distinct concern |
| `SessionContext` | 它是唯一持有 Redis 的元件，且 session 的存活期與清除是它一個人的責任（`[DD:E6]`=A 的單一 key ＋ TTL）。其資料完全不落 PostgreSQL | distinct data ownership、distinct lifecycle |
| `WorkOrchestrator` | 它擁有工作項的狀態機，並且是唯一對外呼叫既有 A1／A3／C1 能力的地方。既有能力的契約改變時只有它要改 | distinct concern、distinct data ownership |
| `MemoryStore` | 它擁有一個**獨立的 PostgreSQL schema** 與其 grant 邊界，這是全 repo 零前例的結構（`[kb:architecture]` 約束七）。它的授權模型（擁有者 ＋ 可見範圍）與 RBAC 的 story-action 模型是兩套不同的東西 | distinct data ownership、distinct concern |
| `ProjectHierarchy` | 它擁有本 intent 新建的核心資料模型，且是唯一碰既有 `user_diagrams` 表的元件。遷移與回復是它一個人的責任 | distinct data ownership、distinct lifecycle |

### Alternatives Rejected

`[DD:E1]` 提了四個切分方案，使用者選 A（六個元件）。被拒方案與理由記於
`decisions.md` 的 **ADR-001**。

---

## 上游覆蓋——10 個 FR 群組落在哪裡

| FR 群組 | 能力 | 落點元件 |
|---|---|---|
| FR1 意圖識別與工作交辦 | 1 | `IntentRouter`（判定、信心值、多意圖）＋ `WorkOrchestrator`（交辦、逐項更正）＋ `BrainGateway`（入口頁權限與 prompt_guard） |
| FR2 跨功能共享脈絡 | 2 | `SessionContext` |
| FR3 子功能頁另開新對話 | 3 | `SessionContext` |
| FR4 長短期記憶 | 4 | `MemoryStore` |
| FR5 多意圖識別 | 5 | `IntentRouter`（拆解）＋ `WorkOrchestrator`（N 個工作項） |
| FR6 多輪對話 | 6 | `IntentRouter`（指涉詞解析）＋ `SessionContext`（歷程） |
| FR7 主動通知推播（**Should**） | 7 | `BrainGateway`（推播通道即其 WebSocket）；本 intent 未必交付 |
| FR8 串流式互動 | 8 | `BrainGateway` |
| FR9 專案→系統→架構圖 階層 | 9 | `ProjectHierarchy` |
| FR10 成本能力編排 | 10 | `WorkOrchestrator` |

---

## `team-practices` 對這六個元件的約束

本 stage 宣告消費 `team-practices`（`required: false`）。本 intent 沒有該檔
（`practices-discovery` 只在 `260819-cost-finops` 與 `260802-last-login-column`
兩個 intent 跑過），其內容已 promote 至 **`aidlc/spaces/default/memory/team.md`**。
該層有四條規則**直接約束本站的元件設計**，逐條列出——其中第 1 條約束每個元件的
**內部形狀**，不是風格建議：

| # | `team.md` 的規則 | 出處段 | 對本站六個元件的意義 |
|---|---|---|---|
| 1 | **新模組／新業務邏輯一律走三層形狀**（router → service → 純函式），純運算下沉到不讀 DB 的函式；**不得在 `user_router.py`／`collab_router.py` 之外新建「router 直寫商業邏輯」的模組** | `## Code Style`「後端分層」 | 六個元件**全部是新模組**，故全部適用。具體落點：`BrainGateway` 是協定層（相當於 router，不放商業邏輯）；`IntentRouter` 的門檻判定（信心值 < 0.7）與 `WorkOrchestrator` 的狀態轉換是**純運算**，必須下沉到不讀 DB 的函式——這也讓它們成為 property-based 測試的實際落點 |
| 2 | 新模組的 logger 一律 `logging.getLogger("cloud360.<module>")`，不用 `__name__` | `## Code Style`「命名慣例」 | 六個元件的 logger 命名照此；`__name__` 形式是 5 支既有模組的已知不一致，不再擴散 |
| 3 | **授權矩陣變更需 allow/deny 雙向測試**（該角色做得到 ＋ 其他角色做不到） | `## Testing Posture`「本輪新增規則 A」 | `[DD:E4]`=A 新增 `K1`／`K2` 兩個 story id ＝ `role_permissions` seed 變更，故兩者都要雙向測試 |
| 4 | **新增或修改 HTTP 端點需 `TestClient` 測試**，斷言 status code 與 `response_model` 的欄位集合 | `## Testing Posture`「本輪新增規則 B」 | `ProjectHierarchy` 的建立／修改／刪除端點與 `MemoryStore` 的記憶讀寫端點皆適用。注意 `BrainGateway` 是 **WebSocket** 而非 HTTP，`TestClient.websocket_connect` 是其對應形式（`[US:AC8.1.1]` 已定此形） |

**另一條相關規則（非約束，但決定了風險歸屬）**：`team.md` 的
`## Code Style`「單一真實來源」要求——同一份事實已存在於程式中時，新增第二份
物化前必須先確認是否有既有常數可用；若確實無法避免，新增副本的**同一個 PR**
必須一併新增鎖住兩者一致的測試。本站有一處觸及它：`MemoryRecord.embeddingModel`
的合法值集合（`bge-m3`／`multilingual-e5-large`）與 `EmbeddingPort` 的四個實作名稱
（`ollama`／`fastembed`／`fulltext`／`stub`）是**兩份相關但不同的清單**，
其一致性需要一個測試鎖住——列為 `functional-design` 的注意事項。

## 本站新增、已核可 scope 尚未涵蓋的項目（**需回補**）

既有 **N-1 至 N-9** 已用（N-1–N-7 於 `requirements.md`、N-8 於 `stories.md`、
N-9 於 `mockups.md`）。本站新增 **兩項**：

| # | 新增項 | 來源 | 為什麼不是既有能力的延伸 |
|---|---|---|---|
| **N-10** | **一張架構圖變更紀錄表**（`DiagramChangeRecord`，帶來源需求摘要與輕量標籤） | `[DD:E8]`=C | `[實測]`：`models.py` 的 13 個模型**沒有任何變更歷程表**，`UserDiagram` 只有會被覆寫的 `updated_at`——一次異動一列的紀錄放不進既有結構。而 `scope-document.md:60` 的能力 9 逐字只有「專案 → 系統 → 架構圖 階層」，不含變更溯源 |
| **N-11** | **pgvector image 變更（deploy ＋ test 兩個 compose）＋ Ollama 服務（第 6 個）＋ 模型快取 volume ＋ `EmbeddingPort` 的四個實作與其設定變數** | `[DD:E7]`=B ＋ `[DD:E9]`=D | 能力 4 是「長短期記憶」；向量檢索的基礎設施是實現它的手段，不在 10 項能力內。DB image 由 `postgres:16-alpine` 換為 `pgvector/pgvector:pg16`、新增第 6 個服務、新增 `.env.example` 變數——後者連帶觸發 `LOCAL-DEV.md` 的 blocking 同步 |

---

## 契約端點三問的結果（本站自檢 2）

依 `project.md` 的送審前自檢第 2 項——每個宣告的欄位（誰寫、誰讀、誰清）與方法
（誰擁有、誰呼叫）都要能指名，缺一即缺口，且**檢查範圍是整個 stage 的全部產出**。
本站對 7 個實體的 45 個欄位逐一跑過。**大多數有交代，但查出三處缺口，全部在
「誰清」與「誰讀」兩問上**——與 requirements-analysis 那一輪的「寫入端最容易漏」
剛好相反，本站漏的是**刪除端與讀取端**。

### 有交代的部分（摘要）

| 實體 | 誰寫 | 誰讀 | 誰清 |
|---|---|---|---|
| `BrainSession` | `SessionContext`（每次互動） | `BrainGateway`、`IntentRouter`、`WorkOrchestrator` | TTL 24 小時到期（ADR-005） |
| `WorkItem` | `WorkOrchestrator`（交辦、狀態轉換） | `BrainGateway`（推送兩個視圖） | 隨 session key 一起消失（ADR-005） |
| `MemoryRecord` | `MemoryStore`（擁有者依已驗證身分設定） | `MemoryStore`（檢索）、`IntentRouter`（輔助判定） | 使用者自行刪除 ＋ 90 天 workflow |
| `Project`／`System` | `ObjectCreateAction`（唯一寫入路徑，兩個入口共用） | `SessionContext`、`ObjectPicker` | 經 `K2` 權限刪除 |
| `DiagramChangeRecord` | `WorkOrchestrator`（架構圖被異動時） | **缺口 DG-3** | 隨架構圖刪除（未明訂，含於 DG-2） |
| `MemoryAuditEvent` | `MemoryStore`（刪除、可見範圍變更時） | `US4.3` 的稽核查詢面（回補項 N-8） | **缺口 DG-1** |

### 三處缺口（本站查出，**不自行定案**）

| # | 缺口 | 為什麼它不是實作細節 |
|---|---|---|
| **DG-1** | **`MemoryAuditEvent` 在其 `MemoryRecord` 被 90 天清除之後的去向未定。** `[RA:FR4.5]` 定案情節記憶保存 90 天逾期自動刪除，而 `[RA:FR4.7]` 要求刪除動作本身留稽核——於是清除動作會**產生**一筆稽核事件，同時讓既有稽核事件的 `memoryId` 指向一列已不存在的記憶 | 這是兩條已核可需求交會處的直接矛盾：若稽核事件也一併刪除，「刪除留稽核」就失去意義；若保留，`memoryId` 成為懸空參照而稽核查詢面會顯示指不到內容的紀錄。**兩種都不是實作偏好，是語意選擇** |
| **DG-2** | **`Project`／`System` 被刪除時的 cascade 行為未定。** 刪一個 `System` 會讓 `user_diagrams.system_id` 與 `DiagramChangeRecord` 同時懸空；刪一個 `Project` 會讓其下所有 `System` 懸空 | `functional-design-guide.md` 逐字要求「Always define cascade behaviour: what happens to children when parent is deleted?」。而 ADR-002 已定 `system_id` 為歸屬的**權威來源**——它懸空等於那張圖失去歸屬，而 `[US:AC9.1.4]` 要求 `system_id IS NULL` 計數為 0 且不為 0 須大聲失敗。**刪除若不處理，會讓一條已核可的不變量在執行期被打破** |
| **DG-3** | **`DiagramChangeRecord` 沒有指名的讀取端。** 本站為它寫了寫入端（`WorkOrchestrator`）與欄位，但沒有任何元件、故事或畫面讀它 | 使用者定案 `[DD:E8]`=C 的理由逐字是「可用同一標籤搜尋它影響過哪些圖」——**那句話描述的就是一個讀取端**，而它在本站產出中不存在。沒有讀取端的表是 `project.md` 的 `functional-design:c10` 警告的形狀：文件上看起來已解決，實際是只寫不讀（本 repo 已有同型前例——`estimate_audit_events` 只寫不讀，見 `[US]` 審查的 R-06 證據） |

三項皆列入下方交接事項 **H-7**，指派 `functional-design`（3.1）並附轉移目標。
**本站不自行定案**：DG-1 與 DG-2 都是兩條已核可需求交會處的語意選擇，DG-3 則需要
一個新的使用者可見面或查詢端點——三者都超出「元件邊界與實體歸屬」的範圍。

## 交接事項

| # | 事項 | 落點 | execution（本站查 `stage-graph.json` 所得） |
|---|---|---|---|
| H-1 | 全部實體的完整 schema（型別、約束、允許值、關係基數） | `functional-design`（3.1） | CONDITIONAL、per-unit；skip 則轉 `code-generation`（3.5，ALWAYS） |
| H-2 | 切回共享對話時，獨立那段的內容如何處置（`OQ-1`，本站**未定案**——見 Assumptions） | `units-generation`（2.7） | **ALWAYS** |
| H-3 | `等待中` 狀態的可達性：何謂「一個意圖依賴另一個意圖的結果」（承 `[US]` R-02、`mockups.md` H-4） | `functional-design`（3.1） | CONDITIONAL；skip 則轉 `code-generation`（3.5，ALWAYS） |
| H-4 | WS 訊息封包的正式型別契約與其 CI 一致性檢查（NFR5／N-1） | `contract-design`（2.8） | CONDITIONAL；skip 則轉 `tcms-test-cases`（3.8，ALWAYS）——**但該站跑在 code 寫完之後，屆時契約已被實作定死**，此風險如實記載 |
| H-5 | Redis／Ollama／pgvector 三項的部署設定與 `render-env.sh`／`.env.example`／`LOCAL-DEV.md` 同步 | `infrastructure-design`（3.4） | CONDITIONAL；skip 則轉 `deployment-pipeline`（4.1，亦 CONDITIONAL）——**兩者皆 CONDITIONAL，若都 skip 須重新提交使用者** |
| H-7 | **三處契約缺口 DG-1（稽核事件在其記憶被 90 天清除後的去向）、DG-2（`Project`／`System` 刪除的 cascade，會使 `AC9.1.4` 的不變量在執行期被打破）、DG-3（`DiagramChangeRecord` 無讀取端）** | `functional-design`（3.1） | CONDITIONAL、per-unit；skip 則轉 `code-generation`（3.5，**ALWAYS**）。注意 DG-3 若要以查詢端點承載，該端點須經 `require_story_action` 且依 `team.md` 規則 B 補 `TestClient` 測試 |
| H-6 | 記憶 schema 的 grant 邊界如何在**測試路徑**上被驗證（`[kb:architecture]` 約束七：SQLite 無 schema 概念）；N-2 的真實 PostgreSQL CI job 是其載體 | `build-and-test`（3.6） | **ALWAYS** |

---

## Assumptions & Open Questions

- **`OQ-1`（切回共享時獨立那段的處置）本站未定案**。它被指派給本站，但它是
  **對話歷程的保留語意**而非元件邊界問題，且 `[DD:E6]`=A 的單一 session key ＋ TTL
  已決定了「兩段對話都活在同一個 key 之下、TTL 到期一起消失」這個外框。剩下的
  「切回時獨立那段是保留、捨棄還是可回溯」需要與 `functional-design` 的歷程 schema
  一併決定，故轉移至 `units-generation`（ALWAYS，見交接事項 H-2）。**這是本站
  未完成的指派，不是已解決** [assumption]
- `MemoryRecord.embedding` 的維度定為 **1024**，依據是 bge-m3 的 dense 維度與
  fastembed `multilingual-e5-large` 相同（兩者皆已查證）。若日後更換模型且維度不同，
  欄位需遷移 [assumption]
- Ollama 的 RAM 需求約 2GB、bge-m3 模型約 1.2GB——這兩個數字取自模型與 runtime 的
  一般認知，**本站未在 staging 主機上實測**，且 `DEPLOY.md`／`LOCAL-DEV.md`
  **未記載該主機的 RAM／CPU 餘裕** [assumption]
- `WorkItem` 存在 Redis（隨 session）而非 PostgreSQL，故它**不會**出現在
  `schema_rbac.sql`；`BrainSession` 同理。兩者是本檔 7 個實體中唯二不落 PostgreSQL 的 [assumption]
- 三個直接服務對象的 persona 與 `FinOps_Analyst` 等 11 個既有角色的對應關係，
  本站未重新檢視——`[DD:E4]`=A 只新增 `K1`／`K2` 兩個 story id，各角色的預設值
  （11 × 2 ＝ 22 列）留給 `functional-design` 與 `schema_rbac.sql` 的同步一併定案 [assumption]
- `IntentRouter` 讀記憶以輔助判定，這條依賴使「首字回應時間 P50 ≤ 2 秒」的預算
  又多一段（記憶檢索 ＋ embedding）。`[RA:NFR3]` 明寫該預算幾乎全被路由層 LLM 吃掉，
  本站**未重新估算**加入記憶檢索後是否仍可達 [assumption]

---

# 修訂 1（2026-10-02T23:09:30Z）— 能力 11／12／13 的四個新元件

既有六個元件（`BrainGateway`／`IntentRouter`／`SessionContext`／`WorkOrchestrator`／
`MemoryStore`／`ProjectHierarchy`）與其實體**全部有效、不回改**。本修訂新增四個元件，
元件總數 **6 → 10**。

**上游狀態（如實記載，不假裝乾淨）**：本站消費的 `requirements.md` 為 `directly stale`
（`FR12.4c` 的橫幅落點更正尚未經 requirements-analysis 的關卡重新核可）、`stories.md`
為 `Revalidate`。本站以更正後的 `FR12.4c`（落地頁）為準；若該站重跑並改變落點，
`ReselectionEvent` 的相關設計須一併重審。

## Part A' — 修訂 1 新增的機讀目錄（接續 Part A，同一真實來源）

```yaml
components:
  - name: ProjectMembership
    summary: 專案成員關係、角色、自動改選，以及 per-project 授權判定的唯一來源
    behaviour: >
      成員資格與全域功能權限為兩層串聯，任一層不過即拒（FR12.6）；本元件只回答
      「這個人在這個專案是什麼角色」，全域那一層仍由既有的 require_story_action
      承載，本元件不得重新實作它。建立專案者自動成為該專案的 project_admin
      （FR12.1），且該寫入與專案建立在同一個交易內——否則會出現沒有管理者的專案。
      一個專案可同時有多位 project_admin（FR12.3），角色不互斥、指定第二位不得
      覆寫第一位。專案不得失去最後一位管理者：停用帳號、自我降級、自我移出三條
      路徑必須經過同一個守門判定（AC12.3.1–.3），該判定位於三者的共同上游，
      不是三處各寫一次。project_owner 的帳號被停用時自動改選該專案最早加入的成員
      為 project_admin（FR12.4），挑選必須對同一組成員資料恆定且與資料庫回傳順序
      無關——平手時以 (joinedAt, userId) 做決定性 tie-break，形狀沿用 repo 既有的
      best_clouds（backend/cost/estimate_readers.py:247-251，key=lambda item: (-item[1], item[0])，
      即 (-score, cloud)——本站已開檔核對，非轉引）。自動改選須留稽核（誰、何時、對誰、舊角色、
      新角色），且該稽核必須是 UI 讀得到的持久層而非 logger（既有 _audit_append
      寫的是 logger.info，UI 讀不到）。缺少對應全域功能權限者不得被邀請（FR12.6a）；
      邀請被拒絕時不得留下半套狀態（AC12.5.3）。
      per-project 授權判定的結論由伺服器產生並交給前端，前端不得自行推導（I-5）。
    responsibilities:
      - 專案成員關係與角色的資料模型與生命週期
      - per-project 授權判定（「我在這個專案是什麼角色」）的單一真實來源
      - 「專案不得失去最後一位管理者」的守門（三條路徑的共同上游）
      - project_owner 帳號被停用時的自動改選與其稽核
      - 邀請的前置條件檢查（全域功能權限）
    depends_on:
      - component: ProjectHierarchy
        interaction: 驗證專案存在、讀取 ownerUserId
        style: sync
    dependents:
      - component: BrainGateway
        interaction: 取得 per-project 角色以決定對外訊息中可用的動作
      - component: RequirementRegistry
        interaction: 寫入需求欄位前確認呼叫者在該專案有權限
      - component: McpBridge
        interaction: agent 代使用者讀寫欄位時的 per-project 判定
    external_dependencies:
      - name: PostgreSQL（主 schema）
        kind: database
        purpose: project_members 與自動改選稽核的持久化
      - name: 既有 users 表
        kind: database
        purpose: 成員指向的使用者；停用狀態為自動改選的觸發來源
      - name: 既有 role_permissions 與 require_story_action
        kind: other
        purpose: 兩層串聯的全域那一層，本元件不重新實作
    entities:
      - name: ProjectMember
        identifier: projectMemberId
        attributes: [projectMemberId, projectId, userId, role, joinedAt, invitedBy]
        references:
          - entity: Project
            owned_by: ProjectHierarchy
            relationship: 每一列成員資格屬於一個專案
      - name: ReselectionEvent
        identifier: reselectionEventId
        attributes: [reselectionEventId, projectId, promotedUserId, previousOwnerUserId, previousRole, newRole, occurredAt, acknowledgedAt]
        references:
          - entity: ProjectMember
            owned_by: ProjectMembership
            relationship: 每次自動改選把一位成員的角色升為 project_admin
          - entity: Project
            owned_by: ProjectHierarchy
            relationship: 每次自動改選發生在一個專案內

  - name: RequirementRegistry
    summary: 系統層的需求欄位（按 agent 分組的固定欄位）、其未填計數與寫入者溯源
    behaviour: >
      欄位集合為**固定且按 agent 分組**，不是自由鍵值對（[R12]=D；自由欄位會讓
      同一個概念出現多個名字而畫面無從分辨）。欄位定義隨新 agent 上線而擴充，
      故定義與值分離：定義是程式內的常數，值是本元件的實體。
      **「從未填過」與「填過後被清空」必須可區分**（ADR-015）：從未填過＝無該列；
      清空＝該列存在而 value 為 null 且 clearedAt 有值。此區分是畫面 M12 的要求，
      也是「誰清」那一腿的落點。
      總覽籤的未填計數與需求籤各組的 x/y **必須由同一次查詢的結果推導**，不得各自
      發一次請求（不變量 I-4）。每次寫入都記下 updatedBy（實際發起者）與
      updatedOnBehalfOf（代哪個 agent 寫，由大腦代寫時才有值）——若不區分，使用者
      無法分辨哪些值是自己填的、哪些是對話中被記下的。
      本元件**不是** ADR-009 的「需求」：那是架構圖變更的溯源摘要，兩者同名不同義
      （ADR-011）。
    responsibilities:
      - 需求欄位值的資料模型與生命週期（含清空語意）
      - 未填計數的單一查詢來源
      - 寫入者與代寫對象的溯源
    depends_on:
      - component: ProjectHierarchy
        interaction: 驗證系統存在、取得其所屬專案
        style: sync
      - component: ProjectMembership
        interaction: 寫入前的 per-project 授權判定
        style: sync
    dependents:
      - component: McpBridge
        interaction: agent 代使用者讀寫需求欄位
      - component: BrainGateway
        interaction: 對話中被記下的值經大腦寫回
    external_dependencies:
      - name: PostgreSQL（主 schema）
        kind: database
        purpose: 需求欄位值的持久化
    entities:
      - name: SystemRequirementField
        identifier: systemRequirementFieldId
        attributes: [systemRequirementFieldId, systemId, agentGroup, fieldKey, value, updatedAt, updatedBy, updatedOnBehalfOf, clearedAt]
        references:
          - entity: System
            owned_by: ProjectHierarchy
            relationship: 每一列需求欄位值屬於一個系統

  - name: McpBridge
    summary: agent 取用需求欄位的 MCP 通道；跑獨立進程、僅供同主機連接
    behaviour: >
      跑**獨立進程**（[F16]=B，取代 [S13]=A 的同進程封裝），對外帶使用者 token
      呼叫既有 API。**不得對外暴露，僅供同主機的大腦進程連接**
      （requirements.md:614）；它是本 intent 的第二個新增進程邊界，第一個是 Redis。
      **使用者 token 不得以工具參數傳遞**：工具的 JSON schema 的 properties 不得
      出現任何名稱匹配 token／key／secret／authorization（不分大小寫）的欄位
      （FR11.5、C-T11）。理由是不可逆——token 一旦進入 LLM context 就會被
      LangGraph checkpointer 持久化並出現在任何 tool_calls log。
      每次呼叫都以使用者身分受權限檢查，agent 不得做使用者不能做的事（FR11.6）；
      FR10.2 禁止同進程繞過 require_story_action 的規定在此仍然適用。
      傳輸形式（stdio 或本機 HTTP／SSE）與認證機制本元件不預選，屬設計階段
      （OQ-15／OQ-16）。
    responsibilities:
      - MCP 工具的宣告與其 schema 的憑證欄位白名單
      - 代使用者呼叫既有 API 的 token 轉遞路徑（不經工具參數）
      - agent 身分與使用者身分的對應（稽核主體必須是使用者本人）
    depends_on:
      - component: RequirementRegistry
        interaction: 讀寫需求欄位
        style: sync
      - component: ProjectMembership
        interaction: per-project 授權判定
        style: sync
    dependents: []
    external_dependencies:
      - name: 既有 FastAPI API（經 HTTP）
        kind: third-party-api
        purpose: 對外帶使用者 token 呼叫；不走同進程直呼
      - name: MCP 協定的 client（agent 側）
        kind: other
        purpose: 本元件的消費者是 agent 而非人
    entities: []

  - name: ProgressChannel
    summary: 既有 agent 進度事件的 per-request 隔離通道，含其清除端
    behaviour: >
      取代 design_agent.py 的模組層全域 _progress_queue（FR13.1）。鍵必須是
      **per-request**，不得用 thread_id（per-user）或不存在的「session」（[V-01]）；
      形狀沿用 backend/cost/advice_orchestrator.py:23-24 的 per-key dict
      （`_progress: dict[int, dict[str, Any]] = {}`）——**但不照抄它的 threading.Lock**：
      那支檔案用 Lock 是因為它有 ThreadPoolExecutor，而本元件在單執行緒的 asyncio
      事件迴圈上跑，threading.Lock 在那裡是 cargo cult。鍵的型別亦不同（它是 set_id
      的 int，本元件是 per-request 的識別字）。
      **請求結束時必須移除該鍵**（ADR-014）——只寫不刪會把跨使用者錯送換成無上界的
      記憶體成長，即修掉一個失敗模式換來另一個。
      兩個併發請求各自只收到自己產生的事件，且各自的事件集合**非空**（FR13.2）；
      非空那一半是必要的，否則空集合會讓互斥斷言真空成立。
      通道不存在時的讀取**不得崩潰**（FR13.3）：現狀是 _drain_progress 對 None 呼叫
      get_nowait() 拋 AttributeError，且**該例外原文被送進 SSE 給使用者**——內部例外
      文字外洩是獨立的 ADR-0006 面，故本元件對外的錯誤一律為固定訊息，不含例外原文。
    responsibilities:
      - per-request 進度事件的隔離與投遞
      - 通道的建立與**清除**（請求結束即移除）
      - 讀取不存在通道時的安全行為（不崩潰、不外洩例外原文）
    depends_on: []
    dependents:
      - component: BrainGateway
        interaction: 取得該請求的進度事件以串流給使用者
      - component: WorkOrchestrator
        interaction: 交辦給既有 agent 時建立通道並於結束時移除
    external_dependencies:
      - name: 既有 design_agent.py 與 wa_collab_orchestrator.py
        kind: other
        purpose: 本元件取代其模組層全域狀態；wa_collab_orchestrator.py:79 須補傳 per-request 的鍵
    entities: []
```

### Part A'' — 既有元件的邊補充（**YAML，非散文**；2026-10-02T23:27:18Z 依 `review-02` 的 `R-01` 改寫）

`review-02` 的 `R-01`（Major）指出：本檔第 0 節自稱「下方 YAML 是這份檔的**單一真實
來源**」，而修訂 1 原本把六條缺的對稱邊寫在一張**散文表**裡。機械解析證實那會讓
`depends_on` 與 `dependents` 的邊數不相等（**13 vs 15**），於是**任何照字面只解析
`components:` YAML 區塊的下游工具或 sensor，都會在這六條邊上得到不對稱的圖**——
而它看不到散文表的存在。這不是對稱性被違反（聯集後無環、無矛盾），是**單一真實來源
的契約被打破**。

處置：補一個只含**缺少的邊**的 YAML 區塊。它不觸碰 Part A 既有元件的任何其他欄位
（依 `refined-mockups:c3` 不回改已核可內容），但使 **Part A ＋ Part A' ＋ Part A''
的 YAML 聯集本身對稱**，讀者與工具都不需要先讀一張 Markdown 表才能重建真正的圖。

```yaml
# 本區塊只宣告「既有元件缺少的那幾條邊」，與 Part A 的同名元件合併讀取。
# 合併規則：同名元件的 depends_on／dependents 取聯集；其餘欄位一律以 Part A 為準。
component_edge_supplement:
  - name: ProjectHierarchy
    dependents:
      - component: ProjectMembership
        interaction: 驗證專案存在、讀取 ownerUserId
      - component: RequirementRegistry
        interaction: 驗證系統存在、取得其所屬專案
  - name: BrainGateway
    depends_on:
      - component: ProjectMembership
        interaction: 取得 per-project 角色以決定對外訊息中可用的動作
        style: sync
      - component: RequirementRegistry
        interaction: 對話中被記下的值經大腦寫回
        style: sync
      - component: ProgressChannel
        interaction: 取得該請求的進度事件以串流給使用者
        style: sync
  - name: WorkOrchestrator
    depends_on:
      - component: ProgressChannel
        interaction: 交辦給既有 agent 時建立通道並於結束時移除
        style: sync
```

**對稱性實算（合併 Part A ＋ A' ＋ A'' 之後）**：`depends_on` 的邊數與 `dependents`
的邊數相等，且每一條 `A → B` 都在 B 的 `dependents` 裡有對應項——驗算腳本與結果見
下方自檢第 6 項。

### 既有元件的邊補充（上表的人讀對照）

機讀目錄的 `depends_on`／`dependents` 必須對稱。本修訂新增的邊使三個既有元件
各需補一筆 `dependents`，列於此處（**既有的 Part A 區塊不回改**，依
`refined-mockups:c3`；下游以 Part A ＋ 本節的聯集為準）：

| 既有元件 | 需補的 `dependents` 項 | 來源邊 |
|---|---|---|
| `ProjectHierarchy` | `ProjectMembership`（驗證專案存在、讀 ownerUserId）、`RequirementRegistry`（驗證系統存在） | 兩條新 `depends_on` |
| `BrainGateway` | — | 它是新增邊的**來源**（`depends_on` `ProjectMembership`／`RequirementRegistry`／`ProgressChannel`），故需補的是它的 `depends_on`，見下 |
| `WorkOrchestrator` | — | 同上，需補 `depends_on` `ProgressChannel` |

| 既有元件 | 需補的 `depends_on` 項 | 理由 |
|---|---|---|
| `BrainGateway` | `ProjectMembership`（取 per-project 角色）、`RequirementRegistry`（對話中被記下的值寫回）、`ProgressChannel`（取進度事件） | 三者皆為 `sync` |
| `WorkOrchestrator` | `ProgressChannel`（交辦時建立通道、結束時移除） | `sync` |

**無環驗證**：新增的邊為 `ProjectMembership → ProjectHierarchy`、
`RequirementRegistry → {ProjectHierarchy, ProjectMembership}`、
`McpBridge → {RequirementRegistry, ProjectMembership}`、
`BrainGateway → {ProjectMembership, RequirementRegistry, ProgressChannel}`、
`WorkOrchestrator → ProgressChannel`。四個新元件中 `ProgressChannel` 與
`ProjectHierarchy` 皆為**無出邊的葉**，`McpBridge` 為**無入邊的根**，
拓樸排序存在故**無環**——**17 條邊、10 個節點、`depends_on` 與 `dependents` 兩集合完全相等**，實算見下方自檢第 6 項。

## Part B' — 修訂 1 的人讀視圖

### 新增元件的 Component Diagram

```mermaid
graph TD
    McpBridge -->|讀寫需求欄位| RequirementRegistry
    McpBridge -->|per-project 授權| ProjectMembership
    BrainGateway -->|取 per-project 角色| ProjectMembership
    BrainGateway -->|對話中的值寫回| RequirementRegistry
    BrainGateway -->|取進度事件| ProgressChannel
    WorkOrchestrator -->|建立與移除通道| ProgressChannel
    RequirementRegistry -->|寫入前授權| ProjectMembership
    RequirementRegistry -->|驗證系統存在| ProjectHierarchy
    ProjectMembership -->|驗證專案存在| ProjectHierarchy
```

文字 fallback：`McpBridge` 是本次新增的唯一無入邊根，它呼叫 `RequirementRegistry`
與 `ProjectMembership`。`BrainGateway`（既有）新增三條出邊，分別指向
`ProjectMembership`、`RequirementRegistry`、`ProgressChannel`。`WorkOrchestrator`
（既有）新增一條出邊指向 `ProgressChannel`。`RequirementRegistry` 指向
`ProjectMembership` 與 `ProjectHierarchy`；`ProjectMembership` 指向 `ProjectHierarchy`。
`ProgressChannel` 與 `ProjectHierarchy` 皆無出邊。

### 新增元件的 Component Summary

| Component | Purpose | Depends On | Dependents | Entities Owned |
|---|---|---|---|---|
| `ProjectMembership` | 成員關係、角色、自動改選、per-project 授權判定 | `ProjectHierarchy` | `BrainGateway`、`RequirementRegistry`、`McpBridge` | `ProjectMember`、`ReselectionEvent` |
| `RequirementRegistry` | 系統層需求欄位、未填計數、寫入者溯源 | `ProjectHierarchy`、`ProjectMembership` | `McpBridge`、`BrainGateway` | `SystemRequirementField` |
| `McpBridge` | agent 取用欄位的 MCP 通道（獨立進程、僅同主機） | `RequirementRegistry`、`ProjectMembership` | （無） | （無） |
| `ProgressChannel` | 既有 agent 進度事件的 per-request 隔離與清除 | （無） | `BrainGateway`、`WorkOrchestrator` | （無） |

### 新增實體的 Entity Ownership

| Entity | Owning Component | Identifier | Attributes | References |
|---|---|---|---|---|
| `ProjectMember` | `ProjectMembership` | `projectMemberId` | `projectId`、`userId`、`role`、`joinedAt`、`invitedBy` | `Project`（ProjectHierarchy） |
| `ReselectionEvent` | `ProjectMembership` | `reselectionEventId` | `projectId`、`promotedUserId`、`previousOwnerUserId`、`previousRole`、`newRole`、`occurredAt`、`acknowledgedAt` | `ProjectMember`、`Project` |
| `SystemRequirementField` | `RequirementRegistry` | `systemRequirementFieldId` | `systemId`、`agentGroup`、`fieldKey`、`value`、`updatedAt`、`updatedBy`、`updatedOnBehalfOf`、`clearedAt` | `System`（ProjectHierarchy） |

**兩個元件擁有零實體，這是刻意的**：`McpBridge` 是通道與契約宣告，沒有自己的
持久狀態（工具 schema 是程式內的宣告，不是資料）；`ProgressChannel` 的進度佇列是
**per-request 的行程內狀態**，生命週期短於一次請求，`ADR-014` 明訂它必須在請求結束
時被移除——把它寫成實體會暗示它該被持久化，而那正是要避免的。

### 新增的 External Dependencies

| Component | Dependency | Kind | Purpose |
|---|---|---|---|
| `ProjectMembership` | PostgreSQL（主 schema） | database | `project_members` 與改選稽核的持久化 |
| `ProjectMembership` | 既有 `users` 表 | database | 成員指向的使用者；停用為改選觸發來源 |
| `ProjectMembership` | 既有 `role_permissions` ／ `require_story_action` | other | 兩層串聯的全域那一層，不重新實作 |
| `RequirementRegistry` | PostgreSQL（主 schema） | database | 需求欄位值的持久化 |
| `McpBridge` | 既有 FastAPI API（經 HTTP） | third-party-api | 代使用者呼叫；不走同進程直呼 |
| `McpBridge` | MCP 協定的 client（agent 側） | other | 消費者是 agent 而非人 |
| `ProgressChannel` | 既有 `design_agent.py`／`wa_collab_orchestrator.py` | other | 取代其模組層全域狀態 |

### Rationale — 為什麼這四個各自是獨立的建構塊

| 元件 | 判準 | 具體理由 |
|---|---|---|
| `ProjectMembership` | **不同變更率 ＋ 不同資料擁有** | 成員變更的理由（人員進出、授權調整）與階層變更的理由（新系統、新架構圖）無關。`ddd-patterns.md` 逐字：因不同理由而改變即屬不同 bounded context。`[E11]`＝A |
| `RequirementRegistry` | **不同變更率 ＋ 不同關注** | 欄位定義隨新 agent 上線而擴充（線框 §17 明寫），`System` 的形狀不會。併入 `ProjectHierarchy` 會讓它同時擁有階層、變更紀錄與 agent 契約三種職責。`[E12]`＝A 否決了「掛在 System 實體上」那一案 |
| `McpBridge` | **不同消費者 ＋ 不同失敗模式** | 消費者是 agent 而非人；認證主體（代使用者的 token）、暴露範圍（僅同主機）與失敗模式都與 `BrainGateway` 的 WebSocket 不同。`C-T11` 的硬約束需要一個明確的斷言落點。`[E14]`＝A |
| `ProgressChannel` | **明確的清除端擁有者** | 它是本 intent 要寫的新程式，而「誰清」這一腿在 US13 的 DoD 裡**無人負責**（DoD 只要求鍵是 per-request）。獨立元件讓清除端有擁有者。`[E15]`＝A |

### Alternatives Rejected（修訂 1）

逐案理由見 `domain-design-questions.md` 的 E11–E15 與 `decisions.md` 的
`ADR-010`–`ADR-016`。最要緊的一項：**`[E12]` 的選項 B（取代 `ADR-009`）被否決**，
因為 `ADR-009` 是使用者在 `[DD:E2]` 重新框定後自己定案的，且兩者基數不同
（一次架構圖變更可能由多個需求驅動，而需求欄位是每個系統一組固定欄位），硬接會
製造一個 `ADR-009` 明文拒絕的多對多關聯表。

## 修訂 1 的 ADR-0006 四面向與 PBT 逐項判定（2026-10-02T23:14:58Z）

`project.md` 記著一條本站自己造成的教訓：**`domain-design` 上一輪兩份產出對
`ADR-0006` 的命中數是 0**，而它是 hard constraint；該缺口被升格為自檢第七項。
本節是它的落點。已核可的 `requirements.md:617` 逐字結論為「**四面向皆適用，無不適用
項**」，本站**不重判適用性**，只判「本站新增的四個元件有沒有新落點」。

| 面向 | 適用性（承上游） | 本站新增的落點 |
|---|---|---|
| **IAM** | 適用 | **三處，且這是本修訂最重的一面**。① `ADR-012`：per-project 授權判定由 `ProjectMembership` 單一提供，判定結論由伺服器產生、前端不得推導。② `ProjectMembership.behaviour`：「專案不得失去最後一位管理者」的守門必須位於三條路徑（停用、自我降級、自我移出）的**共同上游**，不是三處各寫一次——`functional-design:c34` 記過的同形缺陷。③ `McpBridge`：每次呼叫以使用者身分受權限檢查，`FR10.2` 禁止同進程繞過 `require_story_action` 的規定在此仍適用 |
| **encryption** | 適用（承 `requirements.md:613` 的 `FR11.5`／`C-T11`） | **一處**：`McpBridge` 的工具 schema 不得出現任何名稱匹配 `token`／`key`／`secret`／`authorization`（不分大小寫）的欄位。**理由是不可逆**——token 一旦進入 LLM context 就會被 LangGraph checkpointer 持久化並出現在任何 `tool_calls` log。本站把它寫進 `McpBridge.behaviour` 而非只記在 AC 上，因為它是**元件的硬約束**而非某一條驗收 |
| **network exposure** | 適用（承 `requirements.md:614`） | **一處**：`McpBridge` 是本 intent 的**第二個**新增進程邊界（第一個是 Redis），**不得對外暴露、僅供同主機的大腦進程連接**。本站**不預選**傳輸形式（`OQ-16`）與認證機制（`OQ-15`），但暴露範圍**不是**未定項——上游已鎖 |
| **audit logging** | 適用 | **兩處**。① `FR12.4b`：自動改選須留稽核（誰、何時、對誰、舊角色、新角色），且該稽核**必須是 UI 讀得到的持久層而非 logger**——`user_router.py:213` 的 `_audit_append` 寫的是 `logger.info`，UI 讀不到（`[Q-11]` 查出）。本站把它實體化為 `ReselectionEvent`，使「誰讀」那一腿有東西可讀。② `ADR-015`：需求欄位的清空留下 `clearedAt` 與 `updatedBy`，使「誰清」可被稽核 |

### PBT hard constraint 的逐項判定

| 標的 | 判定 | 依據 |
|---|---|---|
| **自動改選的挑選邏輯**（`FR12.4`／`FR12.4a`） | **適用，且本站是它第一次有明確落點的地方** | 它要求「挑選結果對同一組成員資料恆定」，而真正可失敗的性質是**排列不變性**（`ORDER BY joined_at` 在時間戳相同時沒有穩定順序，`[Q-05]`）。本站把它寫進 `ProjectMembership.behaviour` 的硬約束：平手時以 `(joinedAt, userId)` 做決定性 tie-break。**前例已開檔核對**：`backend/cost/estimate_readers.py:247-251` 的 `best_clouds` 用 `key=lambda item: (-item[1], item[0])`。挑選函式應為**不讀 DB 的純函式**（輸入為成員集合、輸出為被選中者），這是 PBT 能作用的結構前提 |
| **未填計數**（`FR11.3`） | **不適用** | 它是對欄位集合的直接計算，不存在值域廣到需要生成器的性質；兩處一致性由 e2e 的相等斷言承接（不變量 `I-4`） |
| **併發隔離**（`FR13.2`） | **不適用（但有不變量）** | 它的不變量是「A 與 B 的事件集合互斥且各自非空」，驗證手段是 `asyncio.Event` barrier 釘住交錯順序，不是 Hypothesis 生成器 |
| **agent routing** | **本站無新落點，缺口仍在上游** | `project.md` 把 routing 列為 PBT hard constraint 落點，而 `requirements.md` 的 PBT 表未涵蓋它（`[Q-13]`，已指派 `units-generation`＋`build-and-test`）。本站的 `IntentRouter` 是既有元件、本修訂未動它，故**不在本站範圍**——但它仍是一個未關閉的 hard-constraint 缺口，在此重申以免它被當成已解決 |

## 修訂 1 的七項自檢逐項結果

本站審查額度為 **1 輪**，故這一節的誠實度直接決定交付品質。

| 自檢 | 結果 |
|---|---|
| **1 可達性** | **2 處**。① `SystemRequirementField` 的「清空」態（`value` 為 `null` 且 `clearedAt` 有值）**今天不可達**——它需要 `ADR-015` 的清除端先實作；在那之前畫面只有「無列」一種未填。② `ReselectionEvent.acknowledgedAt` 的非 null 狀態需要橫幅的「知道了」先落地；而**同一人第二次被改選**這個情境（`I-6` 要求的）需要兩次事件，資料前提是兩個專案的 owner 先後被停用——可達但需要刻意構造，驗證層只能是後端 `TestClient` |
| **2 契約端點三問** | **對三個新實體逐個入口跑**（依 `project.md` 的要求，入口清單取自已核可的 user-flow 與線框，不憑印象）：`ProjectMember`（寫＝建立專案時的自動寫入 ＋ 邀請成功／讀＝成員頁、授權判定／**清＝移出專案**；硬刪除帳號的路徑仍為 `OQ-H1`，上游未定）；`ReselectionEvent`（寫＝自動改選／讀＝橫幅、成員詳情的變更紀錄／**清＝`acknowledgedAt`，事件列本身不刪**——這是刻意的，刪了就失去稽核）；`SystemRequirementField`（寫＝使用者或大腦代 agent／讀＝各 agent、總覽計數、MCP／**清＝`ADR-015` 本站定案**）。**三個實體的「誰清」全部有答案**，這是本站與前兩站最大的差別 |
| **3 引用逐字核對** | **查出我自己的兩處**。① US13 的 DoD 與 `stories.md` 寫的 `cost/advice_orchestrator.py:23-24` **路徑前綴錯了**，真實路徑是 `backend/cost/advice_orchestrator.py`（行號與樣式本身正確，已開檔核對）——我原樣複製了那個路徑。② 更要緊的是：**該檔用 `threading.Lock` 是因為它有 `ThreadPoolExecutor`**，而 `ProgressChannel` 跑在單執行緒 asyncio 事件迴圈上，照抄等於 cargo cult——`application-design:c15` 逐字要求「指定沿用既有機制之前，先寫下該既有機制的副作用是否與新需求的意圖相容」。另 `best_clouds` 的前例**是真的**（`backend/cost/estimate_readers.py:247-251`，`key=lambda item: (-item[1], item[0])`），我補上了路徑與行號使它可複驗；`design_agent.py:163` 的 `get_nowait()` 於 `_drain_progress`（`:160`）內、呼叫點 `:203`／`:211` 傳入 `| None` 的 `_progress_queue`，**引用準確** |
| **4 檔案集合一致性** | 三份產出齊備（`components.md`／`decisions.md`／`traceability.json`） |
| **5 跨檔傳播** | 本輪改動的兩個事實（`advice_orchestrator` 路徑、`best_clouds` 的可複驗引用）各以多種形式 grep，`components.md` 與 `decisions.md` 兩處皆已同步 |
| **6 可算的數字先算再寫** | **全部以腳本實算**：元件 **6 → 10**（Part A 六個 ＋ Part A' 四個，以 `^  - name:` 計數）、實體 **7 → 10**（逐段解析 `entities:` 之下的 `- name:`，非整檔 grep——整檔 grep 會把 `external_dependencies` 的名字一起算進來，實測會得到 30 這個錯數字）、ADR **9 → 16**、追溯表 **20 → 31** 筆（`OK` 31、GAP 0）、**對稱且無環**——`depends_on` 與 `dependents` 各 **17** 條邊、兩集合**完全相等**，10 個節點、DFS 三色法確認無環（以腳本解析本檔**全部三個** `yaml` 區塊的聯集實算）。**2026-10-02T23:28:04Z 更正（`review-02` 的 `R-02`）**：原文寫「對 **14** 條邊實算」——13、15、17 都不等於 14，**沒有任何一種合理的計數方式會得出 14**，那代表這一項我是**手寫了一組邊清單**而不是從 YAML 解析出來的（9 條新邊 ＋ 8 條舊邊 ＝ 17）。結論（無環）是對的，但支撐它的數字是手寫的，故那句「已實算」不可信。已改為由腳本解析 YAML 聯集後輸出，並連帶修好 `R-01` 的不對稱（13 vs 15 → 17 vs 17） |
| **7 ADR-0006 ＋ PBT** | 見上一節。**本站刻意不重判適用性**（`requirements.md:617` 已定四面向皆適用），只判新落點：IAM 三處、encryption 一處、network exposure 一處、audit logging 兩處；PBT 的唯一適用標的是自動改選的挑選邏輯，且本站是它第一次有明確落點的地方。**agent routing 的 PBT 缺口仍在上游未關閉**，在此重申 |

## 修訂 1 的交接事項

| # | 事項 | 承接站 | execution |
|---|---|---|---|
| DG-9 | **三張新表觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步**（`review-02` 的 `R-03`）：`project_members`、`reselection_events`、`system_requirement_fields`。`project.md ## Mandated` 逐字為 blocking——未完成不得標示相關 Construction／部署階段為完成。`ADR-015` 的清空語意須反映在 `system_requirement_fields` 的 DDL 上（`value` 可為 null ＋ 獨立的 `clearedAt`），否則「從未填過」與「清空」在資料層不可區分 | `code-generation`（3.5） | **ALWAYS** |
| DG-4 | **`ADR-015` 的後續**：欄位定義被移除後（新 agent 下線），其既有值列如何處置 | `units-generation`（2.7） | **ALWAYS** |
| DG-5 | **`ADR-016` 的數值**：對話歷史的保存期限與筆數上限 | `nfr-requirements`（CONDITIONAL）→ 轉移 `units-generation`（2.7，**ALWAYS**） | — |
| DG-6 | **`ProgressChannel` 的完成條件橫跨新舊程式**：它要改 `design_agent.py` 與 `wa_collab_orchestrator.py:79` 兩支既有檔案，而兩者在本站是 `external_dependencies` 而非元件 | `units-generation`（2.7） | **ALWAYS** |
| DG-7 | **`A-7` 仍未實測**：「MCP 生態可在本 repo 運作」是 `McpBridge` 的前提，而 repo 內零 MCP 基礎設施 | `contract-design`（2.8，CONDITIONAL）→ 轉移 `code-generation`（3.5，**ALWAYS**） | — |
| DG-8 | **上游 stale 的傳遞**：本站以更正後的 `FR12.4c`（落地頁）為準，而該更正尚未經 requirements-analysis 的關卡重新核可；若該站重跑並改變落點，`ReselectionEvent` 的相關設計須重審 | `units-generation`（2.7） | **ALWAYS** |
