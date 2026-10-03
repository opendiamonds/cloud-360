# Contract Summary — 統一入口大腦

<!-- Stage: contract-design（Inception 2.8）· Record: 260920-orchestration-brain
     lead: aidlc-architect-agent · support: aidlc-aws-platform-agent -->

## 這份檔在做什麼，以及它明確不做什麼

`units-generation` 定出 **17 個工作單元、25 條依賴邊**。本檔把每一條邊上的**正式
契約**釘死——什麼資料過邊界、什麼形狀、走什麼機制、出錯時怎麼辦——使多個單元能
平行開工而不在整合時翻車。

**本檔不做的**：不重新切單元、不改依賴拓樸（那是 `units-generation` 已核可的產出）、
不挑施工順序（那是 2.9）、不寫完整的資料庫 schema（型別、約束、允許值屬
`functional-design`）、不選 NFR 實作手法。

**上游輸入**：`units-generation` 的 `unit-of-work.md`（單元定義與 kind）與
`unit-of-work-dependency.md`（機讀依賴邊塊），`domain-design` 的 `components.md`
（實體形狀），`requirements-analysis` 的 `requirements.md`（NFR 與其量測形狀）。

**契約數的推導（實算，非目測）**：`unit-of-work-dependency.md` 的 25 條邊依「被依賴方」
歸併——同一個單元對多個消費端提供的是同一份契約——得 **14 個 provider**，即 14 條
跨單元契約。另加 **3 條不在 DAG 內**的邊界，共 **17 條契約**。三條各自的理由**不同**，
修訂 1（審查 R-01）起逐條寫明，不再以一句「消費對象是既有模組或第三方」概括：
`X-01` 的被依賴方是**既有 C1 模組**、`X-02` 是**既有 A1／A3 端點**（兩者皆非本 intent
待建單元，故不在 DAG）；`X-03` 的消費端是 **`U11` 自己**，其邊界在對外的
**OpenRouter**（第三方），故亦不在 DAG。
三個葉節點 `U9 memory-purge`／`U16 object-picker-ui`／`U17 a11y-gate` 沒有消費端，
只以消費方身分出現。

---

## 契約形式的總則（`[C7]` 定案）

使用者在 `[C7]` 給的規格逐字如下，本檔全部依它撰寫：

> 同進程邊界以「公開介面、資料形狀、必要行為語意」定義契約。每條邊列出被依賴方的
> 公開函式名稱、參數、回傳型別、同步／非同步形式，以及呼叫方必須處理的例外；
> 跨邊界資料結構以 shared-schema 區塊承載。必要行為語意包含授權責任、可觀察副作用，
> 以及重試或冪等性限制；不限定內部實作細節。C1 的授權門面明訂為受保護操作的唯一
> 授權入口，並定義身分與資源上下文如何傳入、拒絕時如何回報，以及授權未通過時不得
> 執行受保護操作。各類邊界使用符合實際機制的描述：HTTP 使用 OpenAPI；WS 沿用 C2 的
> Pydantic → JSON 契約 → TS 型別與兩道 CI gate；資料庫使用 DDL／migration；環境變數
> 列出名稱、型別、必填性、預設值與驗證規則。同進程介面不轉成 HTTP。

**一處看似矛盾、實為不同邊界的說明**（避免下游誤讀為衝突）：`[C7]` 末句「同進程介面
不轉成 HTTP」與 `[RA:FR10.2]`「呼叫既有成本能力一律走 HTTP 並帶使用者 token」並不
牴觸。前者管**本 intent 新建單元之間**的邊界（授權由 `[C1]` 的 facade 承擔）；後者管
**對既有 C1 模組**的邊界，其理由是 `estimate_intake_service` 內**無第二道角色檢查**，
不走 HTTP 就會繞過 `require_story_action("C1", …)`。兩條規則各管各的邊界，皆有效。

---

## 契約表

`機制` 欄的值：`facade`（同進程、經授權門面）、`in-process`（同進程、無受保護操作）、
`ws`（WebSocket）、`http`（跨模組 HTTP ＋ token）、`schema`（DDL／遷移）、
`types`（型別來源 ＋ CI 閘門）、`env`（環境變數）、`seed`（資料種子 ＋ 常數）、
`dom`（前端元件掛載點）、`test-target`（測試標的）、
**`mcp`（MCP 協定的工具宣告；修訂 1 新增第 11 個值，見 `X-04`。傳輸形式與認證機制
為未定項 `OQ-16`／`OQ-15`）**。

| # | Provider Unit | Consumer | 機制 | Owner |
|---|---|---|---|---|
| K-01 | `U1` `brain-infra` | `U5`、`U6`、`U10` | `env` | `U1` |
| K-02 | `U2` `brain-ws-contract` | `U13`、`U14` | `types` | `U2` |
| K-03 | `U3` `rbac-story-ids` | `U7`、`U14` | `seed` | `U3` |
| K-04 | `U4` `hierarchy-data` | `U7` | `schema` | `U4` |
| K-05 | `U5` `memory-data` | `U8`、`U9` | `schema` | `U5` |
| K-06 | `U6` `embedding-port` | `U8` | `in-process` | `U6` |
| K-07 | `U7` `hierarchy-service` | `U10`、`U12`、`U16` | `facade` ＋ `http` | `U7` |
| K-08 | `U8` `memory-service` | `U11`、`U15` | `facade` ＋ `http` | `U8` |
| K-09 | `U10` `session-store` | `U11`、`U12`、`U13` | `in-process` | `U10` |
| K-10 | `U11` `intent-router` | `U13` | `in-process` | `U11` |
| K-11 | `U12` `work-orchestrator` | `U13` | `in-process` | `U12` |
| K-12 | `U13` `brain-gateway` | `U14`、**External: 瀏覽器（對外網路面）** | `ws` | `U13` |
| K-13 | `U14` `entry-page-ui` | `U16`、`U17` | `dom` ＋ `test-target` | `U14` |
| K-14 | `U15` `memory-page-ui` | `U17` | `test-target` | `U15` |
| X-01 | **既有 C1** `/api/cost/v1` | `U12` | `http` | 既有模組（本 intent 不改） |
| X-02 | **既有 A1／A3** 端點 | `U12` | `http` | 既有模組（本 intent 不改） |
| X-03 | `U11` 的 **LLM provider adapter** | **External: OpenRouter**（單元內部 Port，無跨單元消費端） | `in-process` ＋ External | `U11` |

**17 條。** `K-07`／`K-08` 兼具兩種機制：對同進程消費端走 facade，對 HTTP 消費端
（前端 `U16`／`U15`）走 OpenAPI；兩者**共用同一個 facade 作為唯一授權入口**（`[C1]`=C）。

---

## 逐條契約規格

### K-01 `U1 brain-infra` → `U5`、`U6`、`U10`（`env`）

`[C7]` 要求環境變數契約列出「名稱、型別、必填性、預設值與驗證規則」。
`project.md ## Mandated` 另要求：新增 compose 消費的變數時，**同一個 PR** 必須讓
`deploy/render-env.sh` 寫它、`deploy/.env.example` 列它；憑證值**不得含 `$`**
（compose 會對 `--env-file` 的值內插，`ab$cd` 會被無聲截斷成 `ab`）。

```yaml shared-schema
contract: brain-infra-env
owner: U1
consumers: [U5 memory-data, U6 embedding-port, U10 session-store]
# 失敗模式是無聲的：無 fallback 的變數缺值時只會變成空字串，服務照常啟動但功能降級。
# 既有實例：N8N_USER／N8N_PASSWORD 從未被寫入，導致每次部署的架構圖 icons
# 靜默退回灰底佔位圖。故每一個變數都必須被 render-env.sh 寫入。
variables:
  - name: REDIS_URL
    type: string(uri)
    required: true
    default: null                      # 無 fallback——缺值即為錯誤，不得以空字串啟動
    validation: "須為 redis:// 開頭；主機名須為 compose 內部服務名，不得為 localhost"
    consumed_by: [U10]
    written_by: deploy/render-env.sh
    listed_in: deploy/.env.example
  - name: REDIS_PASSWORD
    type: string(secret)
    required: true
    default: null
    validation: "不得含 `$`；以 openssl rand -hex 32 產生"
    consumed_by: [U10]
  - name: EMBEDDING_PROVIDER
    type: enum
    allowed: [ollama, fastembed, fulltext, stub]
    required: true
    default: null                      # 刻意無預設：偵測不到選定提供者時須大聲失敗
    validation: "值不在 allowed 內即啟動失敗並列出可選值（decisions.md ADR-008）"
    consumed_by: [U6]
  - name: OLLAMA_BASE_URL
    type: string(uri)
    required: "僅當 EMBEDDING_PROVIDER=ollama"
    default: null
    validation: "主機名須為 compose 內部服務名；對外暴露面必須為零"
    consumed_by: [U6]
  - name: OLLAMA_EMBED_MODEL
    type: string
    required: "僅當 EMBEDDING_PROVIDER=ollama"
    default: "bge-m3"
    validation: "其 dense 維度須為 1024（與 vector(1024) 欄位一致）"
    consumed_by: [U6]
  - name: FASTEMBED_MODEL
    type: string
    required: "僅當 EMBEDDING_PROVIDER=fastembed"
    default: "multilingual-e5-large"
    validation: "維度須為 1024"
    consumed_by: [U6]
images_and_services:
  - change: "db image 由 postgres:16-alpine 改為 pgvector/pgvector:pg16"
    consumed_by: [U5]
    reason: "vector(1024) 欄位需要 pgvector 擴充"
    scope: "deploy/docker-compose.deploy.yml 與 deploy/docker-compose.test.yml 兩處"
  - service: redis
    ordinal: 5
    exposure: "compose 內部網路only；不得 publish port"
  - service: ollama
    ordinal: 6
    exposure: "compose 內部網路only；不得 publish port"
    volume: "模型快取 volume（bge-m3 約 1.2GB；RAM 需求約 2GB——此兩數字為一般認知，
             domain-design 已標明未在 staging 主機實測，且 DEPLOY.md／LOCAL-DEV.md
             未記載該主機餘裕）"
sync_obligations:                      # 三處，缺一即違反 project.md ## Mandated
  - deploy/render-env.sh
  - deploy/.env.example
  - LOCAL-DEV.md
behaviour_semantics:
  authorization_responsibility: "**無**——環境變數不含授權判定。Redis／Ollama 的憑證
                                 是連線憑證，不是使用者授權"
  observable_side_effects: "變更任一變數須重新部署才生效；`render-env.sh` 會**覆寫**
                            `deploy/.env`（部署後該檔會被清理，避免機敏檔留在 runner 上）"
  retry_and_idempotency: "`render-env.sh` **必須冪等**——`deploy.yml` 的 deploy 與
                          rollback **兩個 job 都呼叫它**（此規則的由來：兩個 job 原本
                          各有一份逐字重複的 heredoc）。變數讀取為啟動時一次性，
                          重讀冪等；缺值時**不得**以空字串繼續啟動（見上方的無聲失敗說明）"
verification: "python3 scripts/validate_env_contract.py（CI 的 repo-contract job 亦執行）"
```

### K-02 `U2 brain-ws-contract` → `U13`、`U14`（`types`）

`[C2]`=A 定案：**後端 Pydantic 模型為唯一真實來源**，鏡射既有 OpenAPI 的兩道 gate。
這是 `components.md` H-4／`[RA:NFR5]`／回補項 N-1 的落點。

`[C4]`=B 的 `v` 欄位屬於本契約，故自動受兩道 gate 保護。

```yaml shared-schema
contract: brain-ws-message-types
owner: U2
consumers: [U13 brain-gateway, U14 entry-page-ui]
source_of_truth: "backend 的 Pydantic 模型（人手改的那一份）"
derived_artifacts:                     # 皆 commit 進版控供 CI 比對，但不得手改
  - path: ws-contract.json
    generated_by: "python scripts/dump_ws_contract.py"
    note: "形狀比照 scripts/dump_openapi.py：json.dumps(..., indent=2, sort_keys=True,
           ensure_ascii=False) + 尾端換行，使輸出與 dict 插入順序無關"
  - path: frontend/src/types/ws-contract.d.ts
    generated_by: "由 ws-contract.json 產生；產生器版本須與 package.json 釘同一版"
ci_gates:                              # 兩道，職責分工與既有那組逐字相同
  - job: backend
    command: "python scripts/dump_ws_contract.py --check"
    asserts: "規格檔 == 後端程式碼"
    on_drift: "exit 1"
  - job: frontend
    command: "npm run check:ws-types"
    asserts: "committed 的型別檔 == 由規格檔重產的型別檔"
    on_drift: "exit 1"
    why: "只有第一道時，若開發者重新 dump 了規格卻忘了重產型別檔，型別檔仍宣告舊
           形狀，而 tsc -b 檢查的是「用法是否符合型別檔」、不是「型別檔是否符合
           規格檔」——那條路徑會靜默通過，前端在執行期拿到未定義值。
           此段為既有 frontend/scripts/check-api-types.mjs 註解所載，本契約沿用同一理由"
why_new_gate_is_needed: "WebSocket 不在 openapi.json 的 42 個 path 內（FastAPI 不登錄
  websocket route），故 dump_openapi.py --check 與 npm run check:types 兩道既有閘門
  對它完全無效。本契約要建的就是那道缺失的閘門"
behaviour_semantics:                   # [C7] 要求逐條寫；本契約是型別來源，故三項皆為「無」＋理由
  authorization_responsibility: "**無**——本契約只提供型別與 CI 閘門，不含任何受保護操作。
                                 授權發生在 K-12 的握手與 K-07／K-08 的 facade"
  observable_side_effects: "**無執行期副作用**——它的『副作用』全在建置期：dump 與
                            型別重產會改動兩個 committed 的衍生物"
  retry_and_idempotency: "dump 與型別產生皆**冪等**（同一份後端模型必產生同一份輸出，
                          因 sort_keys=True 使結果與 dict 插入順序無關），故 CI 可重跑"

envelope:
  direction: server_to_client
  required_fields:
    v: { type: integer, required: true, note: "協定版本，見 K-12 的版本協商" }
    type: { type: string, required: true }
    turnId: { type: string, required: true, note: "同一輪回覆的所有訊息共用；終止事件亦帶它" }
  types:                               # components.md 逐字列舉的六種為下限，不得更少
    - type: token
      payload: { text: "string（非空白）" }
      note: "內容 token。零內容不得以 done 結束，見 K-12 的終止語意"
    - type: clarify
      payload:
        candidates:
          - { id: "string", label: "string", capability: "string", confidence: "number|null" }
      note: "confidence 為選填且不得列為必填（components.md 逐字、mockups.md H-2）"
    - type: work_items
      payload:
        items:
          - workItemId: string
            label: string
            status: "enum: 處理中|等待中|完成|失敗|已停掉"
            capability: string
            waitingOn: "string|null"
            failureReason: "string|null"
            sideEffect: "enum: none|unknown|string"
      note: "status 五值為下限（[RA:FR1.2]）；sideEffect 的 unknown 是合法值——
             系統不承諾停掉時不留半成品（components.md 逐字）"
    - type: cost_card
      payload:
        estimateSetId: { type: integer, required: true }
        savingText: "string|null"
        comparisonText: "string|null"
        qualityText: "string|null"
        unavailableReasons: "object|null"
        costPageUrl: string
      note: "estimateSetId 為 required 是本契約的不變量，見 X-01 的說明"
    - type: sharing_mode
      payload:
        mode: "enum: shared|isolated"
      note: "**修訂 3 新增（審查 R-10）**——`set_sharing_mode` 的回應，亦於連線建立時
             推送當前模式。非終止事件。**同一 session key 的其他連線亦收到此訊息**
             （見 K-12 的 x-concurrent-connections）"
    - type: work_target
      payload:
        projectId: "string|null"
        systemId: "string|null"
        diagramId: "string|null"
      note: "**修訂 2 新增（審查 R-07）**——`set_work_target` 的成功回應，亦用於連線
             建立時推送當前作業對象（使脈絡列在重連後立即正確，滿足 `[RA:NFR4]`）。
             不是終止事件，不計入 K-12 的『每輪至多一個終止事件』"
    - type: done
      payload: { turnId: string }
      note: "終止事件。語意見 K-12"
    - type: error
      payload: { code: string, message: string, turnId: string }
      note: "終止事件。code 的集合見 K-12"
  client_to_server:
    - type: hello
      payload: { v: integer }
      note: "握手後首則訊息，承載版本；token 不在此處（走 Sec-WebSocket-Protocol）"
    - type: user_message
      payload: { text: string }
    - type: correct_work_item
      payload: { workItemId: string }
      note: "逐項更正（[RA:FR1.4]）；其餘工作項不受影響"
    - type: set_sharing_mode
      payload:
        mode: "enum: shared|isolated"
      note: "**修訂 3 新增（審查 R-10）**——`ContextBar` 的「改為獨立對話」控件由此傳到
             伺服器。原版缺它，使 `[RA:FR3.1]`（子功能頁另開新對話）與 `[RA:FR3.3]`
             兩條 **Must** 需求沒有任何機制。
             **這是我引用 `components.md:321` 時只讀了半句的後果**：那句話逐字是
             「取出與更新該連線的作業對象與**共享狀態**」，我用前半（作業對象）補了
             `set_work_target`，後半（共享狀態）卻沒補。同一句話支撐兩則訊息"
      server_response: "成功回一則 `sharing_mode` 訊息帶新模式；失敗回 `error`"
      authorization: "`U13` 以該連線的 principal 呼叫 `K-09.set_sharing_mode`；
                      本操作不涉及 `K-07`／`K-08` 的受保護資源，故不經 facade"
    - type: set_work_target
      payload:
        projectId: "string|null"
        systemId: "string|null"
        diagramId: "string|null"
      note: "**修訂 2 新增（審查 R-07）**——選定的作業對象由此傳到伺服器。
             原版整組契約沒有任何一條定義這條傳輸，而 `[RA:FR2.2]` 要求同一個作業對象
             跨三頁顯示、`[RA:NFR4]` 要求它撐過後端重啟，兩者都需要伺服器端寫入。
             選這條路徑的依據（非本站新造）：`unit-of-work-dependency.md` 給
             `entry-page-ui.depends_on: [brain-ws-contract, brain-gateway,
             rbac-story-ids]`，故 `U14` 的**唯一**後端通道是 `U13` 的 WS；而
             `components.md` 給 `BrainGateway → SessionContext` 的 interaction 逐字是
             「取出與**更新**該連線的作業對象與共享狀態」，`SessionContext` 的責任首項
             逐字是「作業對象（專案／系統／架構圖三層）的持有與**切換**」——即由
             `U13` 收訊息、再呼叫 `K-09.set_work_target` 正是上游已宣告的形狀。
             **不新增任何依賴邊**：`U14 → U13 → U10` 全在既有 DAG 上"
      server_response: "成功回一則 `work_target` 訊息帶解析後的三層識別；
                        授權或解析失敗回 `error`，code 見 K-12"
      authorization: "`U13` 收到後以該連線的 principal 呼叫 `K-09.set_work_target`，
                      後者再經 `K-07` 的 `HierarchyFacade.resolve_work_target` 驗證
                      ——授權仍只有 facade 這一個入口（[C1]=C）"

```

### K-03 `U3 rbac-story-ids` → `U7`、`U14`（`seed`）

```yaml shared-schema
contract: brain-rbac-story-ids
owner: U3
consumers: [U7 hierarchy-service, U14 entry-page-ui]
provides:
  story_ids:
    - id: K1
      purpose: "統一入口頁的存取權；置於 DefaultRedirect 權限瀑布之首（[RA:FR1.8]）"
      consumed_by: [U14]
    - id: K2
      purpose: "projects／systems／DiagramChangeRecord 的讀建改刪（[RA:FR9.5]）"
      consumed_by: [U7]
  seed_rows: "11 個既有角色 × 2 個 story id = 22 列；矩陣由 308 增為 330 列"
  writer: "ensure_missing_role_permissions（只 INSERT 缺失的 (role, story_id) 列）"
forbidden:
  - "不可依賴 ensure_role_permissions_seeded(force=False)——該函式在表非空時整段 no-op
     （decisions.md ADR-004），既有環境的新 story id 永遠不會被插入"
behaviour_semantics:
  authorization_responsibility: "本單元只保證 story id 存在；判定由 require_story_action 承擔"
  observable_side_effects: "向 role_permissions 插入缺失列（22 列）；不刪除、不更新既有列"
  retry_and_idempotency: "`ensure_missing_role_permissions` **必須可重複執行且不覆寫
                          既有列**，故啟動時每次呼叫皆安全。對比：既有的
                          `ensure_role_permissions_seeded(force=False)` 在表非空時**整段
                          no-op**，看似冪等實為失效——那是本契約禁止依賴它的理由"
sync_obligations:                      # blocking，project.md ## Mandated
  - schema_rbac.sql
  - DEPLOY.md
verification:
  - "allow/deny 雙向 TestClient：有該權限 → 2xx／導入口頁；無該權限 → 不得到達且落地順序正確"
  - "各角色預設值待 OQ-11／OQ-14 定案（指派 domain-design，已 skip 轉 units-generation）"
```

### K-04 `U4 hierarchy-data` → `U7`（`schema`）

```yaml shared-schema
contract: hierarchy-schema
owner: U4
consumers: [U7 hierarchy-service]
tables: [projects, systems, diagram_change_records]
column_added: "user_diagrams.system_id（nullable；為歸屬的權威來源，decisions.md ADR-002）"
migration:
  action: "為每個持有圖的使用者建立『預設專案／預設系統』並把其現有圖掛入"
  invariant: "遷移後 user_diagrams 中 system_id IS NULL 的列數必須為 0"
  on_violation: "遷移程序必須**大聲失敗**，不得以警告帶過（[US:AC9.1.4]）"
  entrypoint: "必須提供可被 unittest 匯入並呼叫的入口——不得只存在於 init_db() 的
               副作用或只在空 volume 執行的 SQL 檔中，否則 AC9.1.2 只能手動
               （user-stories 的 quality-agent 貢獻檔 §9 逐字）"
known_threat_to_the_invariant:
  id: DG-2
  statement: "Project／System 刪除的 cascade 行為未定，會讓 system_id 懸空，
              使該不變量在**遷移之後**被打破——遷移當下滿足不等於持續滿足"
  landing: "functional-design（3.1，CONDITIONAL、per-unit；skip 轉 code-generation，ALWAYS）"
  note: "本站不定案；此為 domain-design 的交接事項 H-7，原樣傳遞"
context_why_migration_is_the_only_path:
  - "schema_rbac.sql 只在**空 volume** 執行，且含裸的 DELETE FROM role_permissions;"
  - "既有環境的唯一演進路徑是 database.py 的 _ensure_* 補丁，而它們**全部吞掉失敗**"
behaviour_semantics:
  authorization_responsibility: "**無**——DDL 與遷移在部署／啟動路徑執行，不經使用者授權。
                                 資料的存取授權由 K-07 的 facade 承擔"
  observable_side_effects: "建三表、為 user_diagrams 加欄、為每個持有圖的使用者建立
                            預設專案／預設系統並改寫其圖的 system_id——**這是資料寫入，
                            不只是 schema 變更**"
  retry_and_idempotency: "DDL 以 `IF NOT EXISTS` 等可重跑安全寫法撰寫。
                          **遷移本身必須冪等**：重跑時已掛好的圖不得被重新指派，
                          否則部分失敗後的重跑會產生第二組預設專案／系統。
                          不變量檢查（`system_id IS NULL` 計數為 0）為唯讀冪等，
                          違反時**大聲失敗**而非警告"
verification: "真實 PostgreSQL CI job ＋ 不變量查詢"
```

### K-05 `U5 memory-data` → `U8`、`U9`（`schema`）

```yaml shared-schema
contract: memory-schema
owner: U5
consumers: [U8 memory-service, U9 memory-purge]
schema_isolation:
  form: "同一個 PostgreSQL database 內的獨立 schema（保留原生跨 schema join 能力）"
  boundary: "grant 只開放記憶 schema"
  precedent: "**本 repo 零前例**——全樹無 CREATE SCHEMA、無 search_path"
tables:
  - name: memory_records
    key_columns: [memoryId, kind, ownerUserId, visibilityScope, content, embedding, embeddingModel, createdAt, expiresAt]
    vector_column: "embedding vector(1024)"
    note: "完整型別與約束屬 functional-design"
  - name: memory_audit_events
    key_columns: [auditEventId, memoryId, actorUserId, action, previousScope, newScope, occurredAt]
invariants:
  - "每列記憶帶 embeddingModel；相似度檢索只比對同一 embeddingModel 的列——
     同維度不等於同向量空間，不加這道過濾會讓跨模型的檢索回垃圾**且不報錯**
     （decisions.md ADR-008）"
  - "fulltext 模式下建立的列其 embedding 為 NULL，之後不會被向量檢索看到，除非重新 embed"
known_gap:
  id: DG-1
  statement: "memory_audit_events 在其 memory_records 列被 90 天清除之後的去向未定。
              [RA:FR4.5] 要 90 天刪除、[RA:FR4.7] 要刪除留稽核——清除動作會**產生**一筆
              稽核事件，同時讓既有稽核事件的 memoryId 指向一列已不存在的記憶。
              一併刪除則「刪除留稽核」失去意義；保留則成為懸空參照"
  landing: "functional-design（CONDITIONAL；skip 轉 code-generation，ALWAYS）"
behaviour_semantics:
  authorization_responsibility: "資料庫層以 **grant 只開放記憶 schema** 承載邊界；
                                 列層級的擁有者／可見範圍授權由 K-08 的 facade 承擔"
  observable_side_effects: "建 schema、建兩表、建向量索引、設 grant"
  retry_and_idempotency: "全部 DDL 與 grant 以可重跑安全寫法撰寫（`CREATE SCHEMA
                          IF NOT EXISTS`／`CREATE TABLE IF NOT EXISTS`／重複 GRANT 無害），
                          故 CI job 與部署路徑皆可重跑。**無資料遷移**，故無 K-04 那類
                          的重跑風險"
verification:
  carrier: "真實 PostgreSQL CI job（postgres:16-alpine service container）"
  why_not_existing_tests: "既有測試在 tests/helpers.py 以
    sys.modules.setdefault('psycopg2', MagicMock()) 換掉驅動、改走 in-memory SQLite，
    而 **SQLite 沒有 schema 概念**——現有測試基礎設施對本契約沒有任何驗證路徑"
  scope: "schema 建立、grant 邊界、跨 schema 查詢（[RA:NFR6]）"
```

### K-06 `U6 embedding-port` → `U8`（`in-process`）

```yaml shared-schema
contract: embedding-port
owner: U6
consumers: [U8 memory-service]
public_interface:
  - name: EmbeddingPort.embed
    params: "texts: Sequence[str]"
    returns: "list[list[float]]（每個長度 1024）"
    form: sync
    raises:
      - "EmbeddingProviderUnavailable — 偵測不到選定提供者時。**必須大聲失敗並列出
         可選值，不得靜默降級為全文檢索**（decisions.md ADR-008）"
  - name: EmbeddingPort.model_id
    params: "（無）"
    returns: "str — 寫入 memory_records.embeddingModel 的值"
    form: sync
    raises: []
implementations: [ollama, fastembed, fulltext, stub]
selected_by: "EMBEDDING_PROVIDER 環境變數（見 K-01）"
behaviour_semantics:
  authorization_responsibility: "無——本 Port 不碰授權，亦不讀 DB"
  observable_side_effects: "ollama 實作發出對 Ollama 服務的 HTTP 呼叫；其餘無"
  retry_and_idempotency: "embed 為純函式語意（同輸入同輸出），呼叫方得安全重試；
                          本 Port 自身不重試，重試次數上限由呼叫方依 [C9] 的上限設定"
  vector_space: "四個實作的向量**不可互相比較**（同為 1024 維但不同向量空間）"
verification: "property-based（純函式性質）＋ 單元測試（stub 實作）"
pbt_note: "ADR-0006 的 property-based hard constraint 落點之一"
```

### K-07 `U7 hierarchy-service` → `U10`、`U12`、`U16`（`facade` ＋ `http`）

**`[C1]`=C 的落點。** 本契約是本站最重要的一條：它同時服務兩種消費端，而授權入口
只有一個。

```yaml shared-schema
contract: hierarchy-authorized-facade
owner: U7
consumers:
  in_process: [U10 session-store, U12 work-orchestrator]
  http: [U16 object-picker-ui]
authorization_model:
  sole_entry: "HierarchyFacade —— 受保護操作的**唯一**授權入口"
  rule: "FastAPI router 與同進程呼叫端**共用這一個入口**，故 require_story_action 的
         判定只有一份呼叫點"
  identity_passing: "每個 facade 方法的第一個參數為 principal（已驗證的身分 ＋ 其角色），
                     由呼叫端傳入；facade 不自行從 request 取身分"
  resource_context: "受保護資源的識別（projectId／systemId／diagramId）為具名參數，
                     不得藏在 payload 內"
  on_denied: "raise HierarchyForbidden(story_id='K2', action=<action>) —— **不是**
              HTTPException。router 層把它轉成 403 ＋ detail 前綴；同進程呼叫端自行處置"
  hard_rule: "授權未通過時**不得執行受保護操作**——判定與執行不得交錯，判定先於任何
              讀寫，且失敗即中止"
  residual_gap: "『facade 是唯一入口』**無機械強制**——繞過它直呼底層 service 只能靠
                 code review 擋下。本站如實記載此缺口，不宣稱已解決"
public_interface:
  - name: HierarchyFacade.list_projects
    params: "principal"
    returns: "list[ProjectView]"
    form: sync
    raises: [HierarchyForbidden]
  - name: HierarchyFacade.create_project
    params: "principal, name: str"
    returns: "ProjectView"
    form: sync
    raises: [HierarchyForbidden, HierarchyValidationError]
  - name: HierarchyFacade.create_system
    params: "principal, project_id: str, name: str"
    returns: "SystemView"
    form: sync
    raises: [HierarchyForbidden, HierarchyValidationError, HierarchyNotFound]
  - name: HierarchyFacade.resolve_work_target
    params: "principal, project_id: str|None, system_id: str|None, diagram_id: str|None"
    returns: "ResolvedTarget（三層識別驗證與解析的結果）"
    form: sync
    raises: [HierarchyForbidden, HierarchyNotFound]
    consumed_by: [U10]
  - name: HierarchyFacade.record_diagram_change
    params: "principal, diagram_id: str, requirement_summary: str, requirement_label: str"
    returns: "None"
    form: sync
    raises: [HierarchyForbidden, HierarchyNotFound]
    consumed_by: [U12]
    note: "**U12 是 DiagramChangeRecord 的唯一寫入端**（components.md 宣告
           WorkOrchestrator --sync--> ProjectHierarchy）"
  - name: HierarchyFacade.delete_project / delete_system
    params: "principal, <id>: str"
    returns: "None"
    form: sync
    raises: [HierarchyForbidden, HierarchyNotFound]
    note: "cascade 行為未定（DG-2），見 K-04"
behaviour_semantics:
  authorization_responsibility: "**見本契約的 `authorization_model` 區塊**（內容較此處
                                 豐富：唯一入口、principal 傳遞、資源上下文、拒絕回報、
                                 授權未過不得執行、殘留缺口）。此鍵為修訂 3 補
                                 （審查 R-13）——原本 17 條中只有本條沒有字面
                                 `authorization_responsibility`，使 `[C7]` 的嚴格掃查
                                 報 16/17 而非 17/17"
  observable_side_effects:
    - "create_* 寫入 projects／systems 並留稽核"
    - "record_diagram_change 寫入一列 diagram_change_records"
  retry_and_idempotency:
    - "create_project／create_system **非冪等**——重複呼叫會建立第二個同名物件。
       呼叫端不得自動重試建立類操作"
    - "resolve_work_target 為唯讀且冪等，可安全重試"
    - "record_diagram_change **非冪等**（一次異動一列），不得重試"
  single_write_path: "兩個使用者入口（脈絡列選單的表單、對話式建立的確認卡）共用
                      create_* 這一條寫入路徑，授權檢查、稽核紀錄與錯誤訊息各只有一份
                      （interaction-spec.md INV-2）"
known_gap:
  id: DG-3
  statement: "DiagramChangeRecord 有寫入端（U12）與 schema 保管（U4），但**沒有讀取端**。
              使用者定案 [DD:E8]=C 的理由逐字是「可用同一標籤搜尋它影響過哪些圖」——
              那句話描述的就是一個讀取端"
  landing: "本單元 U7（讀取端屬服務層）；經 functional-design（CONDITIONAL，skip 轉
            code-generation，ALWAYS）"
  if_implemented: "該查詢端點須經 require_story_action 並依 team.md 規則 B 補 TestClient 測試"
```

其 HTTP 那一半（消費端 `U16`）的規格：

```yaml OpenAPI
openapi: 3.1.0
info: { title: Hierarchy API, version: "1.0.0" }
# 這些 path 進 openapi.json，故自動受既有兩道漂移閘門保護
paths:
  /api/hierarchy/projects:
    get:
      summary: 列出使用者可見的專案
      security: [{ bearerAuth: [] }]
      responses:
        "200": { description: OK }
        "403": { description: "無 K2 權限；detail 帶授權來源前綴" }
    post:
      summary: 建立專案（非冪等）
      security: [{ bearerAuth: [] }]
      responses:
        "201": { description: Created }
        "403": { description: 無 K2 權限 }
        "422": { description: 驗證失敗 }
  /api/hierarchy/projects/{projectId}/systems:
    get: { summary: 列出該專案下的系統, responses: { "200": {}, "403": {}, "404": {} } }
    post: { summary: 建立系統（非冪等）, responses: { "201": {}, "403": {}, "404": {}, "422": {} } }
  /api/hierarchy/projects/{projectId}:
    delete: { summary: 刪除專案, responses: { "204": {}, "403": {}, "404": {} } }
  /api/hierarchy/systems/{systemId}:
    delete: { summary: 刪除系統, responses: { "204": {}, "403": {}, "404": {} } }
components:
  securitySchemes:
    bearerAuth: { type: http, scheme: bearer }
# 實作注意：每個 router handler 只做「取身分 → 呼叫 facade → 轉譯例外」，
# 不得自行呼叫底層 service（否則 facade 不再是唯一授權入口）
```

### K-08 `U8 memory-service` → `U11`、`U15`（`facade` ＋ `http`）

形狀同 `K-07`，但授權模型是**第二套**——擁有者 ＋ 可見範圍，與 story-action 模型不同。

```yaml shared-schema
contract: memory-authorized-facade
owner: U8
consumers:
  in_process: [U11 intent-router]
  http: [U15 memory-page-ui]
authorization_model:
  sole_entry: "MemoryFacade"
  model: "擁有者（ownerUserId）＋ 可見範圍（visibilityScope），非 story-action"
  write_side_enforcement: "擁有者由本單元在寫入時依**呼叫者的已驗證身分**設定，
                           **不得由呼叫方自行指定**"
  default_scope: "最窄（僅擁有者可見）"
  scope_widening: "是一個獨立的、需授權的操作，僅 Platform_Admin 與 Platform_Owner
                   得為之，且每次變更須留稽核（誰、何時、由什麼範圍改為什麼範圍）"
  identity_passing: "principal 為第一個參數，同 K-07"
  on_denied: "raise MemoryForbidden(reason=<owner|scope>)；router 轉 403 ＋ detail 前綴"
  hard_rule: "授權未通過時不得執行受保護操作"
public_interface:
  - name: MemoryFacade.write
    params: "principal, kind: str, content: str"
    returns: "MemoryView"
    form: sync
    raises: [MemoryForbidden, EmbeddingProviderUnavailable]
    note: "ownerUserId 由 principal 決定；embeddingModel 由 K-06 的 model_id 決定"
  - name: MemoryFacade.search
    params: "principal, query: str, kinds: Sequence[str], limit: int"
    returns: "list[MemoryView]"
    form: sync
    raises: [MemoryForbidden, EmbeddingProviderUnavailable]
    consumed_by: [U11]
    note: "只回該 principal 可見的列；只比對同一 embeddingModel 的列"
  - name: MemoryFacade.delete
    params: "principal, memory_id: str"
    returns: "None"
    form: sync
    raises: [MemoryForbidden, MemoryNotFound]
    note: "使用者得刪除自己的記憶；刪除動作本身須留稽核"
  - name: MemoryFacade.widen_scope
    params: "principal, memory_id: str, new_scope: str"
    returns: "MemoryView"
    form: sync
    raises: [MemoryForbidden, MemoryNotFound]
    note: "僅 Platform_Admin／Platform_Owner；須留稽核（previousScope → newScope）"
  - name: MemoryFacade.list_audit_events
    params: "principal, memory_id: str|None"
    returns: "list[MemoryAuditEventView]"
    form: sync
    raises: [MemoryForbidden]
    note: "[US4.3] 的稽核查詢面（回補項 N-8）；DG-1 未解決時可能回到指不到內容的列"
behaviour_semantics:
  observable_side_effects: "write／delete／widen_scope 皆寫稽核事件"
  retry_and_idempotency:
    - "write **非冪等**（重複呼叫產生第二列記憶），呼叫端不得自動重試"
    - "search 唯讀冪等，可重試"
    - "delete 冪等（已刪除者再刪為 MemoryNotFound，不視為錯誤狀態的改變）"
  authorization_responsibility: "可見範圍的過濾在 facade 內完成，呼叫端不得自行過濾"
```

其 HTTP 那一半：

```yaml OpenAPI
openapi: 3.1.0
info: { title: Memory API, version: "1.0.0" }
paths:
  /api/memory/records:
    get:
      summary: 列出當前使用者可見的記憶（三種 kind 分區）
      security: [{ bearerAuth: [] }]
      responses: { "200": {}, "403": {} }
  /api/memory/records/{memoryId}:
    delete:
      summary: 刪除一則記憶（留稽核）
      security: [{ bearerAuth: [] }]
      responses: { "204": {}, "403": {}, "404": {} }
  /api/memory/records/{memoryId}/scope:
    put:
      summary: 放寬可見範圍（僅 Platform_Admin／Platform_Owner；留稽核）
      security: [{ bearerAuth: [] }]
      responses: { "200": {}, "403": {}, "404": {} }
  /api/memory/audit-events:
    get:
      summary: 稽核事件查詢
      security: [{ bearerAuth: [] }]
      responses: { "200": {}, "403": {} }
components:
  securitySchemes:
    bearerAuth: { type: http, scheme: bearer }
# 路由守衛：/memory 走 ProtectedRoute 但**不包** CapabilityRoute（前例 App.tsx:37–44），
# 把關的是擁有者欄位而非角色，故不需新 story id（[DM:D1]=C 的查證）
```

### K-09 `U10 session-store` → `U11`、`U12`、`U13`（`in-process`）

```yaml shared-schema
contract: session-context
owner: U10
consumers: [U11 intent-router, U12 work-orchestrator, U13 brain-gateway]
storage: "Redis，單一 session key；TTL 24 小時、每次互動續期（[DD:E6]=A）"
hard_rule: "一律放 Redis，**不得放行程記憶體**——重啟 backend 後既有對話的脈絡與
            作業對象須完整還原（[RA:NFR4]）"
out_of_scope: "三處既有行程內狀態容器（collab_router 連線字典、advice_orchestrator 的
               _executor／_progress／_inflight、pricing_client 磁碟快取）維持原狀"
public_interface:
  - name: SessionStore.load
    params: "session_key: str"
    returns: "BrainSession | None"
    form: sync
    raises: [SessionBackendUnavailable]
  - name: SessionStore.set_work_target
    params: "session_key: str, principal, project_id, system_id, diagram_id"
    returns: "BrainSession"
    form: sync
    raises: [SessionBackendUnavailable, HierarchyForbidden, HierarchyNotFound]
    note: "**經 K-07 的 HierarchyFacade.resolve_work_target 驗證三層識別**——
           這是 [C1]=C 在本邊界的落點；HierarchyForbidden 原樣向上傳遞"
  - name: SessionStore.append_message
    params: "session_key: str, role: str, text: str"
    returns: "None"
    form: sync
    raises: [SessionBackendUnavailable]
  - name: SessionStore.set_sharing_mode
    params: "session_key: str, mode: 'shared'|'isolated'"
    returns: "BrainSession"
    form: sync
    raises: [SessionBackendUnavailable]
  - name: SessionStore.touch
    params: "session_key: str"
    returns: "None"
    form: sync
    raises: [SessionBackendUnavailable]
    note: "TTL 續期"
data_shape:
  BrainSession:
    fields: [sessionKey, userId, currentProjectId, currentSystemId, currentDiagramId, sharingMode, messageHistory, expiresAt]
    note: "工作項集合亦放在同一個 session key 之下（見 K-11）"
behaviour_semantics:
  authorization_responsibility: "本單元不自行判權；set_work_target 的授權由 K-07 承擔"
  observable_side_effects: "全部方法都會續期 TTL"
  retry_and_idempotency: "load／touch／set_* 皆冪等，可安全重試；append_message **非冪等**"
  expiry: "TTL 到期時作業對象、共享狀態、對話歷程、工作項集合**一起消失**，
           下次進入即為全新 session 且作業對象回到未選定"
shared_scope: "共享工作階段涵蓋統一入口、/workspace、/assessment 三處，
               不含 /admin/* 與 /cost（[RA:FR2.1]）"
open_question:
  id: OQ-1
  statement: "切回共享對話時，獨立那段的內容如何處置（保留／捨棄／可回溯）"
  status: "domain-design 未定案並轉移 units-generation；units-generation 亦未定案。
           **本站不定案**——它是對話歷程的保留語意，須與 functional-design 的歷程
           schema 一併決定"
verification: "重啟還原測試 ＋ TestClient"
```

### K-10 `U11 intent-router` → `U13`（`in-process`）

```yaml shared-schema
contract: intent-router
owner: U11
consumers: [U13 brain-gateway]
public_interface:
  - name: IntentRouter.classify
    params: "principal, session: BrainSession, text: str"
    returns: "IntentDecision"
    form: async
    raises: [LlmUnavailable, LlmBudgetExceeded]
data_shape:
  IntentDecision:
    fields:
      intents: "list[Intent]（一句含 N 個可分離意圖者輸出 N 個）"
      confidence: "float，定義域 0–1"
      below_threshold: "bool —— confidence < threshold"
      candidates: "list[ClarifyCandidate]|None —— below_threshold 時必為非空"
    Intent: { capability: str, referent: "str|None（指涉詞解析後的作用對象）" }
    ClarifyCandidate: { id: str, label: str, capability: str, confidence: "float|None" }
hard_rules:
  - "**每一次入口頁輸入一律先過分類並產生信心值**（[C10]=C）。不存在跳過分類的快路徑
     ——`[RA:FR1.6]` 逐字：若實作出一個不輸出信心值的路由層，`FR1.3` 會**靜默永不
     觸發**，而文件上看起來已解決"
  - "below_threshold 為真時**不得交辦、不得產生任何結果**（[RA:FR1.3]），
     改回 clarify 候選"
  - "判定意圖前先過既有 prompt_guard；命中則**不呼叫任何 LLM**，回固定拒絕訊息
     （[RA:FR1.5]）。該固定訊息**是有內容的有效回覆**，正常以 done 結束（[C6]）"
threshold:
  initial_value: 0.7
  form: "設定值而非常數；得依 [RA:NFR1] 的校正程序調整"
  coupling: "調整 NFR1 的 80% 時**必須同時處理**這個 0.7，兩者不得分開調
             ——調高門檻會讓系統多反問、少交辦，準確率的帳面數字因此上升，
             但那不是識別變準了"
cost_discipline:                       # [C9] 保留部分 ＋ [C10]=C
  - "分類器僅接收決策所需的**最少上下文**"
  - "同一狀態下互不相依的判斷**合併請求**"
  - "限制文字模型的上下文與輸出長度"
  - "設定每輪模型呼叫次數、重試次數與用量上限（機制必須存在且可設定；
     **具體數值不在本站定案**，見回補項 N-18）"
behaviour_semantics:
  authorization_responsibility: "無受保護操作；讀記憶時經 K-08 的 MemoryFacade，授權由它承擔"
  observable_side_effects: "一次 LLM 呼叫（可計費）；讀記憶（唯讀）"
  retry_and_idempotency: "classify **非冪等**（LLM 輸出可變），重試次數受上述上限約束"
open_question:
  id: "OQ-10（須與 OQ-4 一併決定，不得分開處理）"
  statement: "路由層是否能產出可比較的信心值。若不能，`FR1.3` 的觸發條件須改以
              『候選意圖並列且無單一最高分』表達，`FR1.7` 的 0.7 隨之不適用——
              本契約的 confidence／below_threshold 兩個欄位語意都要改寫"
  landing: "nfr-requirements（3.2，CONDITIONAL，**無自然承接站**，skip 時須重新提交使用者）"
verification: "純函式 PBT（門檻比較）＋ 可注入替身（見 X-03）"
pbt_note: "ADR-0006 逐字點名 agent routing 須有 property-based 測試；受測對象是
           門檻比較這個純函式。若 OQ-10 結論為『無可用信心訊號』，該純函式的輸入
           型態會改變，PBT 的 property 須重寫"
```

### K-11 `U12 work-orchestrator` → `U13`（`in-process`）

```yaml shared-schema
contract: work-orchestrator
owner: U12
consumers: [U13 brain-gateway]
public_interface:
  - name: WorkOrchestrator.dispatch
    params: "principal, session: BrainSession, decision: IntentDecision"
    returns: "list[WorkItem]"
    form: async
    raises: [SessionBackendUnavailable, CapabilityCallFailed]
  - name: WorkOrchestrator.correct
    params: "principal, session_key: str, work_item_id: str"
    returns: "WorkItem"
    form: async
    raises: [WorkItemNotFound]
    note: "逐項更正；其餘工作項不受影響（[RA:FR1.4]）"
  - name: WorkOrchestrator.list_items
    params: "session_key: str"
    returns: "list[WorkItem]"
    form: sync
    raises: [SessionBackendUnavailable]
data_shape:
  WorkItem:
    fields: [workItemId, sessionKey, label, status, capability, waitingOn, failureReason, sideEffect, createdAt, estimateSetId]
    status_values: [處理中, 等待中, 完成, 失敗, 已停掉]
    notes:
      - "狀態值集合**不得少於**這五個（[RA:FR1.2]）"
      - "等待中 用於依賴前一項結果者；已停掉 用於使用者更正後的終止狀態"
      - "sideEffect ∈ {none, unknown, <說明文字>}；**unknown 是合法值**，因為系統
         不承諾停掉時不留半成品"
      - "estimateSetId 為成本類工作項專用，見 X-01 的不變量"
storage: "隨 session key 存放於 Redis（見 K-09）；TTL 到期一起消失"
behaviour_semantics:
  authorization_responsibility:
    - "寫 DiagramChangeRecord 經 K-07 的 HierarchyFacade.record_diagram_change"
    - "呼叫既有 C1 走 HTTP 帶使用者 token（見 X-01），**不得**同進程直呼
       estimate_intake_service——其內無第二道角色檢查"
  observable_side_effects: "對既有 A1／A3／C1 的 HTTP 呼叫；寫 DiagramChangeRecord；寫 session"
  retry_and_idempotency:
    - "dispatch **非冪等**（會建立新工作項並呼叫既有能力）"
    - "list_items 唯讀冪等"
    - "correct 冪等（已停掉者再更正為 no-op）"
  streaming: "把成本 job 的五種狀態事件轉譯進大腦訊息流；**不等 job 完成才開始回覆**；
              **不做 token 級巢狀串流轉送**——來源端沒有逐字可轉（[RA:FR10.8]）"
open_question:
  id: "H-3（承 user-stories R-02、mockups H-4）"
  statement: "等待中 狀態的可達性：何謂『一個意圖依賴另一個意圖的結果』"
  landing: "functional-design（CONDITIONAL；skip 轉 code-generation，ALWAYS）"
verification: "純函式 PBT（狀態轉換）＋ TestClient"
```

### K-12 `U13 brain-gateway` → `U14`、**External: 瀏覽器**（`ws`）

**本 intent 唯一新增的對外網路面。** 訊息型別由 `K-02` 定義；本契約定端點、握手、
版本協商、終止語意與關閉碼。

```yaml AsyncAPI
asyncapi: 3.0.0
info: { title: Brain Gateway, version: "1.0.0" }
servers:
  staging:
    host: cloud360.danniel.cc
    protocol: wss
channels:
  brain:
    address: /api/brain/ws
    description: 大腦的唯一 WebSocket 端點
# --- 三項硬約束（皆為機械事實，非偏好）---
x-hard-constraints:
  path_prefix:
    rule: "必須掛在 /api/ 之下"
    why: "nginx 的 location /api/ 是唯一帶 Upgrade 標頭者；location / 走
          try_files … /index.html，握手落那裡會拿到 HTML"
  token_transport:
    rule: "token 走 Sec-WebSocket-Protocol 標頭，**不得放 query string**"
    why: "query string 會讓 token 進 nginx 與 cloudflared 的 access log。
          既有前例 collab_router.py:270 正是 websocket.query_params.get('token')，
          **本契約不得照抄**"
  activity_record:
    rule: "握手須以 record=True 呼叫既有 get_user_from_token"
    why: "既有 WS 前例用 record=False，照抄會讓 users.last_activity_at 的帳號活動
          稽核對大腦使用者**靜默失效**（[RA:FR8.4]）；節流仍為既有的 5 分鐘"
x-session-key-derivation:              # [C7]／審查 R-11：原版沒有任何一句說 session_key 由誰產生
  producer: "`U13` 在握手成功後產生（見 step_2b）。它是 `K-09` 每個方法的第一個參數、
             `BrainSession` 與 `WorkItem` 的欄位、以及工作項集合的儲存鍵——原版三處都用它
             卻沒有來源，這是把本站自檢 2（每個宣告的欄位誰寫／誰讀／誰清）**沒有跑到
             的那個欄位**補上"
  derived_from: "已驗證使用者的 id。**一個使用者一個大腦 session**"
  why_one_key:
    upstream_basis: "`[DD:E6]`=A 定案**單一 session key ＋ TTL 24 小時續期**；
                     `components.md:99` 逐字「作業對象、共享／獨立狀態、工作項集合放在
                     **同一個 session key 之下**，TTL 24 小時、每次互動續期；TTL 到期
                     三者一起消失」；`domain-design-questions.md:324` 逐字「兩段都在
                     同一 key 下、一起到期」"
    therefore: "`sharingMode` 是**那一個** session 的欄位，**不是第二個 session**。
                故 `[RA:FR3.2]` 的**作業對象那一半**（獨立對話帶著當前作業對象過去）
                由構造滿足：同一個 key、同一組 `currentProjectId`／`currentSystemId`／
                `currentDiagramId`。
                **修訂 4 收窄（審查 R-15）**：原版寫成「`[RA:FR3.2]` 由構造滿足」，
                那是**過度宣稱**——`[RA:FR3.2]` 還有「新對話**不共享任何訊息歷程**」
                那一半，而 `BrainSession` 只有一個 `messageHistory`、`append_message`
                沒有分段參數，**那一半並未滿足**，見 `OQ-N4`。本句只對作業對象成立"
    correction_to_the_finding: "審查 R-11 推論「有 `sharingMode` 就可能有多個 session，
                                故不隱含由使用者推導」——**該前提與上游相反**，上游明文
                                單一 key。但它的核心成立：原版確實沒說 key 由誰產生。
                                本項只修那個缺口，不採其兩-key 的推論"
x-concurrent-connections:             # 審查 R-12：原版對「同一 session 多條連線」完全沒說
  which_routes_connect: "共享工作階段涵蓋的**三處**——入口頁、`/workspace`、`/assessment`
                         （`[RA:FR2.1]`）——**皆持有一條本端點的連線**。
                         `K-13` 把 `ContextBar` 掛在這三處且 `U14` 擁有兩個子頁面掛載
                         （`unit-of-work.md:180`），而 `unit-of-work-dependency.md` 給
                         `entry-page-ui.depends_on: [brain-ws-contract, brain-gateway,
                         rbac-story-ids]`——`U14` 的**唯一**後端通道是本端點。
                         **為何不改用 HTTP**：那需要 `U14 → U7` 這條邊，而 DAG 沒有它
                         ——加它就是審查 R-01／R-07 的同型錯誤第四次"
  multiple_allowed: "同一個 session key **允許多條並存連線**（三個頁面、多個分頁）。
                     伺服器不以連線為狀態單位，狀態一律在 Redis 的該 key 之下"
  state_change_fanout: "`work_target`、`sharing_mode`、`work_items` 三類**狀態訊息**，
                       在該 session key 的狀態改變時**推送給該 key 的**全部存活連線****，
                       不只推給觸發那一條。這是 `[RA:FR2.2]`（同一作業對象跨三頁顯示）
                       與 `[RA:NFR2]`（跨頁面上下文保留率 ≥ 95%）的承載機制"
  fanout_vs_no_replay: "**這與 `x-retry-and-idempotency.server_side` 的「伺服器不重送
                        已送出的訊息；不緩衝、不重播」不衝突**——那條管的是
                        **對重連的客戶端重播歷史訊息**（不做）；本條管的是
                        **狀態改變時對當下存活的連線扇出**（要做）。兩者是不同的事，
                        原版沒有區分，審查 R-12 正是據此指出 NFR2 建立在未定義行為上"
  on_connect: "新連線建立時推送當前 `work_target` 與 `sharing_mode`（見 K-02），
               使該頁的脈絡列立即正確，無需額外讀取端點"
  fanout_mechanism_and_its_assumption:   # 修訂 4 補（審查 R-16）
    registry: "扇出需要一份「該 session key 目前有哪些存活 socket」的登錄。本契約指定它為
               **行程內**的連線登錄（既有前例：`collab_router` 的連線字典）。
               `K-09` 的 Redis 狀態**不提供**這份登錄——它存的是 session 狀態，不是 socket"
    assumption: "**本契約因此假設單一後端行程。** 依據：`backend/Dockerfile:37` 為
                 `uvicorn main:app --host 0.0.0.0 --port 8000`，**無 `--workers`**，
                 且部署為單一容器"
    why_written_down: "這個假設的失效模式是**靜默的**——加一個 worker 或一個 replica 之後，
                       跨連線扇出會在不報任何錯的情況下失效，`[RA:NFR2]` 隨之默默降級。
                       明寫它，使未來任何擴容變更會撞到這一句而不是撞到使用者"
    if_scaled: "若日後需要多行程，跨行程扇出需要一個 pub/sub（Redis 已在位可承載），
                但本站**不預選手段**，亦不列為本 intent 的回補項——它是擴容時才存在的需求"

x-handshake:
  step_1: "HTTP Upgrade；token 於 Sec-WebSocket-Protocol"
  step_2b: "認證成功後 `U13` 由已驗證使用者 id 推導 session key（見
            x-session-key-derivation），載入或建立該 session"
  step_2: "客戶端送 hello { v: <integer> } 作為握手後首則訊息"
  step_3: "伺服器比對 v；相容則回 ready，不相容則以 4400 關閉並帶原因"
  version_note: "[C4]=B 選『訊息帶 v 欄位、握手時比對』且**未**選『版本走
                 Sec-WebSocket-Protocol』；與 [RA:FR8.5]（token 走該標頭）相加後，
                 唯一自洽的形狀是版本走**首則訊息**。故『握手時比對』在本契約中指
                 **首則訊息的比對**，不是 HTTP upgrade 階段。此為兩個已定案相加後的
                 唯一解，非本站另作選擇"
x-termination-semantics:               # [C6] 使用者自訂規格的落點
  done:
    meaning: "已成功產出**可呈現**的回覆"
    precondition: "純文字回覆必須包含**非空白文字**；內部推理、控制事件與空白不算內容"
  empty_upstream:
    rule: "上游結束但未產出有效回覆時，後端**必須**送 error(code: EMPTY_RESPONSE)，
           **不得**送 done"
  at_most_one:
    rule: "每次回覆（同一 turnId）最多只能有**一個**終止事件（done 或 error）；
           終止後不得再送內容"
  no_terminal_received:
    rule: "若連線中斷而未收到終止事件，依 [C5] 標為未完成，**不自動重試**"
  client_obligations:
    - "收到 EMPTY_RESPONSE 時顯示明確錯誤提示"
    - "收到**零內容的 done** 時，視為**契約違規**：顯示備援提示並記錄異常，
       **不呈現空白成功態**"
  client_obligations_note: "契約上零內容 done 不可能發生，但前端不假設對方守約——
           這是『契約保證』與『防禦性實作』兩件事分開，比單純刪掉那個狀態更強"
  prompt_guard_case: "prompt_guard 命中的固定訊息**屬於有效回覆**，正常以 done 結束"
x-disconnect-behaviour:                # [C5]=B
  on_drop: "重連即為**新的一輪**；未完成的那則明確標示為未完成、不自動重試，
            使用者自行重問"
  session_survives: "session 狀態在 Redis、TTL 24 小時，故作業對象與歷程仍在"
  rationale: "與 domain-design 已定的 sideEffect: unknown 誠實立場一致——系統不承諾
              停掉時不留半成品，也就不該假裝能完美接續"
x-retry-and-idempotency:               # [C7] 要求逐條寫
  handshake: "握手**冪等**——重連建立新連線但沿用同一個 session key（session 在 Redis、
              TTL 24h），故作業對象與歷程不因重連改變"
  user_message: "**非冪等**——每則 user_message 觸發一輪分類與可能的交辦。客戶端
                 **不得**自動重送未收到終止事件的那一則（[C5]=B）"
  correct_work_item: "**冪等**——已停掉者再更正為 no-op（見 K-11）"
  server_side: "伺服器不重送已送出的訊息；不緩衝、不重播（[C5]=B 排除選項 C）"
x-close-codes:
  4401: "握手認證失敗（token 無效或缺失）"
  4403: "無 K1 權限"
  4400: "協定版本不相容（帶 expected 與 received）"
  1011: "伺服器內部錯誤"
x-authorization-responsibility:        # [C7] 要求逐條寫（修訂 2 補，審查 R-08）
  handshake: "以 `Sec-WebSocket-Protocol` 的 token 呼叫既有 `get_user_from_token`
              （`record=True`）；失敗以 4401 關閉。無 `K1` 權限以 4403 關閉"
  per_connection_principal: "連線建立後該 principal 綁定此連線；每一則客戶端訊息都以它
                             為身分，客戶端**不得**在訊息內自帶身分"
  delegation: "受保護操作的授權**不在本契約**——`set_work_target` 經 `K-09` 再經 `K-07`
               的 facade；記憶相關經 `K-08` 的 facade。本層只負責認證與 `K1` 的可達性"
x-observable-side-effects:             # [C7] 要求逐條寫（修訂 2 補，審查 R-08）
  on_handshake: "`record=True` 使 `users.last_activity_at` 更新（節流 5 分鐘）
                 ——這是本契約對既有資料的寫入，不是唯讀"
  on_user_message: "**`U13` 會寫入 session 的對話歷程**（呼叫 `K-09.append_message`，
                    該方法本檔自己標為**非冪等**）。修訂 2 補記（審查 R-08）：原版沒有
                    任何一句說出這個寫入，而執行它的單元是 `U13`"
  on_set_work_target: "寫入 session 的作業對象（見上方 client_to_server）"
  on_llm_call: "`U11` 的分類會產生一次可計費的對外 LLM 呼叫（見 X-03）"
x-per-message-guard:
  rule: "每一則進入的使用者文字先過既有 prompt_guard；命中即不呼叫任何 LLM 並回固定
         拒絕訊息"
x-event-loop:
  rule: "不得在事件迴圈上做同步 LLM 呼叫"
verification: "TestClient.websocket_connect；以 token 置於 query string 的握手須被
               **拒絕**，不只是『我們不那樣寫』（user-stories 的 quality-agent 貢獻檔 §US8）"
```

### K-13 `U14 entry-page-ui` → `U16`、`U17`（`dom` ＋ `test-target`）

```yaml shared-schema
contract: entry-page-mount-points
owner: U14
consumers: [U16 object-picker-ui, U17 a11y-gate]
provides_to_U16:
  mount: "ContextBar —— 對象選單掛載於此"
  scope: "ContextBar 同時掛在入口頁、/workspace、/assessment 三處（[RA:FR2.1]）"
  ownership_note: "ContextBar 內的『改為獨立對話』控件屬 **U14**，不屬 U16
                   （units-generation 修訂 1 的 R-01 更正）"
  props_contract:
    - "onObjectSelected(target: ResolvedTarget) —— U16 選定後回呼"
    - "currentTarget: ResolvedTarget | null —— U14 傳入當前作業對象"
provides_to_U17:
  route: "/"
  testids: "brain-* 前綴（team.md ## Code Style 與 design-system-mapping.md）"
behaviour_semantics:
  authorization_responsibility: "K1 置於 DefaultRedirect 瀑布之首；**不存在
                                『無權限的入口頁』畫面**，該狀態不可達（[RA:FR1.8]）"
  observable_side_effects: "`onObjectSelected` 是**SPA 內的前端回呼**，U14 收到後
                            **送出 K-02 的 `set_work_target` WebSocket 訊息**；
                            伺服器端的 session 寫入由 `U13` 執行（見 K-12）。
                            **修訂 2 更正（審查 R-07）**：原版寫「U14 呼叫 K-09 的
                            `set_work_target`」，那是錯的——`K-09` 是 `in-process`、
                            消費端為 `[U11, U12, U13]`，而 `U14` 在瀏覽器裡，
                            同進程呼叫跨不過行程邊界；且 DAG 沒有 `U14 → U10` 這條邊。
                            這與審查 R-01 是同型錯誤，在另一節又犯了一次。
                            對 `U16` 的意義不變：選一次就是一次**伺服器端持久化**，
                            不是純 UI 狀態"
  retry_and_idempotency: "以相同 target 重複選取**冪等**（伺服器端的
                          `K-09.set_work_target` 冪等，見 K-09）；`U16` 不需去重，
                          但也不得倚賴回呼只被呼叫一次。訊息送出失敗時由 `K-12` 的
                          斷線語意處理（[C5]=B：重連即新一輪，不自動重送）"
  data_fetch_shape: "前端新增資料來源必須走 AdminPage.tsx 的兩層抓取形狀
                     ——react-hooks/set-state-in-effect 為 **error** 級，違反即 CI 紅燈"
  url_building: "沿用 wsUrl()／apiUrl()，不自造 URL 組裝"
  immutability: "state 更新一律回傳新物件（react-hooks/immutability 為 error 級）"
verification: "Playwright e2e"
```

### K-14 `U15 memory-page-ui` → `U17`（`test-target`）

```yaml shared-schema
contract: memory-page-test-target
owner: U15
consumers: [U17 a11y-gate]
provides:
  route: "/memory"
  guard: "ProtectedRoute，**不包** CapabilityRoute（前例 App.tsx:**37–44** 的
          /waiting-approval——上游記為 38–41，本站第一版精修為 37–42 仍短兩行，
          修訂 1（審查 R-06）更正為 37–44：37 `<Route`、38 `path=`、39 `element={`、
          40 `<ProtectedRoute>`、41 頁面、42 `</ProtectedRoute>`、43 `}`、44 `/>`）；把關的是擁有者欄位而非角色，故**不需新 story id**"
  regions: "三區（語意／程序／情節）＋ 逐則刪除"
  entries: "Sidebar 項 ＋ 入口頁捷徑（兩入口一個顯示條件）"
behaviour_semantics:                   # [C7] 要求逐條寫
  authorization_responsibility: "路由層的 ProtectedRoute（登入即可）；**頁內**的授權由
                                 K-08 的 MemoryFacade 以擁有者欄位承擔，前端不自行過濾"
  observable_side_effects: "逐則刪除會呼叫 K-08 的 delete 並產生一筆稽核事件——
                            這是使用者可見的不可逆操作，畫面須有確認"
  retry_and_idempotency: "檢視唯讀冪等；刪除在 K-08 側冪等（已刪除者再刪為 404），
                          故前端重試安全。axe 掃描本身唯讀冪等"
verification: "Playwright e2e ＋ axe 掃描（U17 的兩個目標之二）"
```

### X-01 既有 C1 `/api/cost/v1` → `U12`（`http`）

**消費既有模組，本 intent 不改它。** 本契約的作用是把「既有 API 實際回什麼」釘死，
使 `U12` 的轉譯不建立在猜測上。**下列欄位集合為實讀 `advice_stream_router.py` 所得。**

```yaml OpenAPI
openapi: 3.1.0
info: { title: 既有 C1 Cost API（消費契約，不修改）, version: "1.0.0" }
paths:
  /api/cost/v1/sets/{set_id}/advice/stream:
    get:
      summary: 成本建議的狀態事件串流（SSE）
      security: [{ bearerAuth: [] }]
      x-must-carry-user-token: true
      x-why: "[RA:FR10.2] —— 使既有的 require_story_action('C1', …) dependency
              照常執行；estimate_intake_service 內**無第二道角色檢查**，
              同進程直呼會完整繞過授權"
      x-audit-subject: "使用者本人，不是大腦（[RA:FR10.3]）"
x-authorization-responsibility:        # [C7] 要求逐條寫；本契約的授權全在既有模組側
  where: "既有的 require_story_action('C1', …) dependency（U12 不新增授權層）"
  obligation: "U12 **必須**帶使用者的 token；不帶即等於繞過該 dependency"
  why_cannot_bypass: "estimate_intake_service 內**無第二道角色檢查**，同進程直呼會完整
                      繞過授權（[RA:FR10.2]／[C-S5]）"
  audit_subject: "使用者本人，不是大腦（[RA:FR10.3]）"
x-event-types:                         # 實讀所得，五種，與 [RA:FR10.4] 列舉相符
  - progress                           # 三處分支皆為此型
  - completed
  - timeout
  - failed
  - heartbeat
x-completed-payload:                   # _snapshot()，實讀
  advice:
    status: string
    saving_text: "string|null"
    comparison_text: "string|null"
    quality_text: "string|null"
    unavailable_reasons: "object|null"
    started_at: "string(iso)|null"
    completed_at: "string(iso)|null"
x-invariant-this-contract-adds:
  statement: "**completed 事件從來不帶估價 id**——set_id 是路徑參數，呼叫端本來就持有。
              故 U12 **必須**在發起 job 時把 set_id 存入該工作項的 estimateSetId 欄位
              （見 K-11 的 WorkItem），cost_card 的 estimateSetId 由它填、連結由它組出"
  resolves: "mockups.md 的 H-6 —— CostAnswerCard 的 no-estimate-id 狀態，其可達性
             **完全由大腦自己是否保存 set_id 決定**，不受外部 API 影響。本契約把
             『工作項必須保存 set_id』定為不變量，使該狀態不可達"
x-streaming-rule:
  rule: "不得對成本做 token 級巢狀串流轉送"
  why: "C1 的『串流』是每秒輪詢 DB 的**狀態事件**，真正的 LLM 呼叫是同步 invoke
        ——來源端沒有逐字可轉（[RA:FR10.8]）"
x-terminal-states:
  rule: "timeout 與 failed 兩種終態各須有可見訊息，使用者能分辨『還在跑』與『已失敗』
         （[RA:FR10.5]）"
x-observable-side-effects:              # [C7] 要求逐條寫（修訂 2 補，審查 R-08）
  start_job: "在既有 C1 側建立或推進一個 advice 列——**改動既有模組的資料**，
              本 intent 不擁有該資料但會使它變動"
  llm_cost: "該 job 內部會呼叫 LLM（同步 `invoke`），故發起一次即產生一次可計費工作，
             而計費主體是平台自己"
  audit: "既有 C1 的稽核以**使用者本人**為行為主體記錄（見下方 x-authorization-responsibility）"
  brain_side: "`U12` 把 `set_id` 寫入該工作項的 `estimateSetId`（見 K-11 的不變量）"
x-retry-and-idempotency:               # [C7] 要求逐條寫
  start_job: "發起成本 job **非冪等**（會建立第二個 advice 列或撞上 already-generating
              的既有處理）。U12 **不得自動重試**發起動作；重試次數上限見 K-10 的
              cost_discipline"
  stream_read: "讀取事件串流唯讀冪等——斷線後可重新開啟同一個 set_id 的串流並從當前
                狀態接續（來源端是每秒輪詢 DB 的狀態，不是不可重播的事件流）。
                **注意這與 K-12 的 [C5]=B 不衝突**：C1 這一側可重讀，而大腦對**使用者**
                的那一則回覆仍依 C5 標為未完成、不自動重試"
  heartbeat: "heartbeat 無狀態意義，收到即忽略，不得據以改變工作項狀態"
x-presentation:
  progress: "以**單一則就地更新**的訊息呈現"
  completed: "該則訊息被**結構化卡片**取代，卡片附連往成本頁的連結（[RA:FR10.6]）"
  location: "就地在入口頁呈現，使用者不需離開入口頁（[RA:FR10.7]）"
```

### X-02 既有 A1／A3 端點 → `U12`（`http`）

```yaml OpenAPI
openapi: 3.1.0
info: { title: 既有 A1／A3 端點（消費契約，不修改）, version: "1.0.0" }
# 這些 path 已在 openapi.json 的 42 個之內，故其形狀已受既有兩道漂移閘門保護；
# 本契約只釘 U12 的呼叫義務，不重述其 schema
x-public-interface:                    # [C7] 要求列出被依賴方的公開介面
  note: "這些 path 已在 openapi.json 的 42 個之內，其 request／response schema 由既有
         兩道漂移閘門保護，故本契約**只具名端點**、不重述 schema——重述一份不受閘門
         保護的副本反而會過期"
  endpoints:
    - "A1（架構圖生成）：`agent_router` 之下的端點，由 U12 依意圖交辦"
    - "A3（Well-Architected 檢視）：`review_router` 之下的端點"
  resolution_obligation: "U12 實作時須以 openapi.json 的實際 path 為準，**不得憑本檔
                          的概述推斷**；若兩者不符，是本契約記錯"
x-authorization-responsibility:        # [C7] 要求逐條寫（修訂 2 補，審查 R-08）
  where: "既有 A1／A3 端點自身的 FastAPI dependency（本 intent 不新增授權層）"
  obligation: "`U12` **必須**帶使用者的 token；不帶即繞過那些端點的既有授權"
  audit_subject: "使用者本人，不是大腦（與 X-01 同一原則，`[RA:FR10.3]` 的延伸）"
  not_verified_here: "本站**未實讀** A1／A3 各自掛的是哪一個 story id 的
                      `require_story_action`；`U12` 實作時須以那些端點的實際 dependency
                      為準，不得假設與 C1 相同"
x-call-obligations:
  transport: "HTTP 帶使用者 token（同 X-01 的理由：保留既有授權）"
  retry_and_idempotency: "A1 的產生／修改架構圖**非冪等**（會改動圖並產生一列變更紀錄），
                          U12 不得自動重試；A3 的檢視若為唯讀則冪等，但本站**未實讀
                          該端點**確認，故保守視為非冪等、不自動重試"
  agents: "design_agent（A1）與 review_agent（A3）走 **Anthropic Agent SDK**，
           與 LangGraph 無關；其 LLM 設定經 llm_provider.configure_provider_env()，
           該函式**改寫整個行程的環境變數**且在每個 A1／A3 請求都被呼叫"
  coupling_warning: "上述行程級 env 改寫是既有耦合。大腦的路由層**不走這條路徑**
                     （見 X-03），但 U12 呼叫 A1／A3 時會間接觸發它——此耦合須被明寫，
                     不得假設無副作用"
x-observable-side-effects:             # [C7] 要求逐條寫
  a1: "產生或修改架構圖——**改動使用者資料的不可逆操作**"
  a3: "Well-Architected 檢視；本站未實讀其是否寫入，保守視為可能寫入"
  downstream_obligation: "A1 產生或修改架構圖後，U12 須經 K-07 的
                          `HierarchyFacade.record_diagram_change` 寫入一列變更紀錄"
  process_env: "呼叫 A1／A3 會間接觸發 llm_provider.configure_provider_env()，
                它**改寫整個行程的環境變數**（見下方 coupling_warning）"
```

### X-03 `U11` 的 LLM provider adapter → **External: OpenRouter**（`in-process` ＋ External）

**`[C3]`=B ＋ `[C8]` ＋ `[C11]`=B 的共同落點。** 這是本站第二重要的契約。

```yaml shared-schema
contract: brain-llm-provider-adapter
owner: U11
consumers: [U11 intent-router]        # **修訂 1（審查 R-01）**：原列 U12，已移除，理由見下
external_boundary: "OpenRouter —— 本契約的真正邊界是對外第三方，不是跨單元"
why_u12_removed:
  finding: "原版把 `U12 work-orchestrator` 列為消費端，等於引入一條 `U11 → U12` 的
            依賴邊。而 `unit-of-work-dependency.md` 的機讀邊塊逐字為
            `work-orchestrator.depends_on: [session-store, hierarchy-service]`
            ——**沒有這條邊**。本檔前言自己寫「不改依賴拓樸」，原版違反了它"
  upstream_basis: "`unit-of-work.md` 的 `U11` 注意事項逐字寫「這是**第三個** OpenRouter
                   家族客戶端」，把該客戶端只給 `U11`；`U12` 的『擁有與交付』逐字為
                   「工作項五狀態機、逐項導回與 sideEffect、多意圖 N 個工作項、
                   呼叫既有 A1／A3／C1（HTTP 帶 token）、成本狀態事件轉譯」
                   ——**沒有任何 LLM 呼叫**。`U12` 呼叫的既有能力各自做自己的 LLM 工作"
  consequence_of_the_fix: "消費端只剩 `U11` 自己，故本契約**不是跨單元邊界**，而是
                           `U11` 的單元內部 Port 對外部第三方（OpenRouter）的邊界。
                           『14 條跨單元 ＋ 3 條不在 DAG 內』的推導因此仍成立，但 `X-03`
                           不在 DAG 內的**理由**由「消費對象是既有模組」更正為
                           「消費端是 `U11` 自己，邊界在對外的 OpenRouter」"
  gap_this_exposed:        # 修 R-01 時翻出來的真缺口，見 Open Questions 的 OQ-N1
    statement: "**沒有任何單元或元件擁有『產生自然語言回覆』這件事。** `components.md`
                的 `BrainGateway` 只做「大腦回覆的 token 串流**轉送**」（`:44` 逐字）、
                `IntentRouter` 只做分類、`WorkOrchestrator` 只做編排與呼叫既有能力。
                但 `[RA:FR8.1]` 要求「大腦的回覆應逐步顯示」，而 `[C9]`／`[C10]` 逐字
                提到「只有需要生成自然語言回答時才呼叫文字 LLM」——那個呼叫者未被指名"
    not_decided_here: "本站**不自行指派**。若逕自把它掛回 `U12`，就是我原版犯的錯的
                       另一種形式（憑推論新增拓樸）。列為 `OQ-N1` 並附落點"

why_separate_from_existing:
  finding: "既有 stream_graph（langgraph_runtime.py:130）與 astream_graph（:149）
            把 StreamEvent 的 kind **硬寫為 \"updates\"**，不隨 stream_mode 改變；
            既有測試 test_langgraph_runtime.py:90,105 亦逐字斷言 kind == 'updates'"
  consequence: "大腦要做 [RA:FR8.1] 的逐字串流須傳 stream_mode='messages'，屆時
                payload 是訊息 token 而事件仍標為 updates——**標籤與內容不符**"
  premise_corrected_in_revision_1:   # 審查 R-04，本站複驗後確認它說得對
    what_was_wrong: "原版逐字寫「要重用既有 helper 必須改動它與其已 commit 的斷言，
                     **會動到既有成本路徑**」。後半句與 repo 不符"
    verified_facts: "`grep -rn stream_mode backend/` 在該模組之外**零命中**；唯一的生產
                     呼叫端 `cost_advice_agent.py:134` 只 import `InvokeOutcome`／
                     `invoke_graph`／`openrouter_chat_model`，**從不呼叫**
                     `stream_graph`／`astream_graph`；兩個 committed 斷言
                     （`test_langgraph_runtime.py:90`／`:105`）都**不傳** `stream_mode`"
    therefore: "改 stream helpers **不會動到既有成本路徑**，且
                `kind = stream_mode or \"updates\"` 這種向後相容的一行改法會讓兩個
                斷言保持綠燈。**當初存在一條更便宜的重用路徑而我沒有考慮到它**"
    why_the_decision_still_stands: "理由改掛 `[C8]`（而非成本路徑）：使用者的規格要求
                                    **per-instance／per-test 作用域的可替換執行介面**，
                                    並明訂輸入、串流事件型別、完成、**錯誤與取消**語意。
                                    既有 helper 沒有取消語意、沒有注入接縫、其
                                    `StreamEvent(kind, data)` 也表達不了四種事件種類
                                    ——這些是它沒有的**形狀**，不是一行可以補的。
                                    使用者在 `[C11]`=B 亦是在知道「常數各有兩份」的
                                    代價下選的"

  premise_correction: "上游 [RA:C-S7]／OQ-7／R-8 逐字寫『大腦自建 LangGraph 執行層，
                       與既有 langgraph_runtime.py **並行**』，風險為『兩份 OpenRouter
                       客戶端／兩套串流事件語意漂移』。本站實讀後更正三處前提：
                       (1) langgraph_runtime 不是擁有圖的 runtime，是接受呼叫端自編圖的
                           泛用 helper；
                       (2) 生產程式碼中只有一個呼叫端（cost_advice_agent），
                           A1／A3 走 Anthropic Agent SDK、全樹不 import 它；
                       (3) OQ-7 點名的 configure_provider_env 行程級 env 改寫對
                           openrouter_chat_model 這條路徑**不適用**（其 docstring 逐字
                           寫 'Does not mutate llm_provider environment semantics.'）"
replaceable_execution_interface:       # [C8] 使用者自訂規格
  requirement: "大腦 runtime **必須提供可替換的 LLM 執行介面**，列入內部契約，
                明訂輸入、串流事件型別、完成、錯誤與取消語意"
  assembly: "正式環境組裝真實實作；測試可在 **runtime 建立處**注入替身，不呼叫外部 LLM"
  scope_rule: "替換作用域以 **runtime 實例或單次測試**為限，**避免共享可變全域狀態**"
  naming_rule: "契約承諾**替換能力與行為語意**，**不固定** _run_agent／_session_factory
                等私有名稱，**也不要求以 None 表示真實路徑**"
  transitional: "既有模組層鉤子（advice_orchestrator.py:28–30 的形狀）**可作為過渡實作**，
                 但測試必須可靠還原，並避免並行測試互相污染。
                 註：模組層變數本身就是共享可變全域狀態，故它是過渡形狀而非目標形狀"
  session_dependency: "若 session 建立涉及外部依賴，也應提供**獨立的**替換介面"
  double_must_simulate:                # 四種，皆須確定性
    - "正常串流"
    - "零內容（用於驗證 K-12 的 EMPTY_RESPONSE 路徑）"
    - "部分輸出後失敗（用於驗證 K-12 的 no_terminal_received 與 [C5] 的斷線處置）"
    - "延遲／取消"
public_interface:
  - name: BrainLlmPort.stream
    params: "prompt: BrainPrompt, *, cancel_token"
    returns: "AsyncIterator[BrainStreamEvent]"
    form: async
    raises: [LlmUnavailable, LlmBudgetExceeded, LlmCancelled]
  - name: BrainLlmPort.invoke
    params: "prompt: BrainPrompt"
    returns: "BrainInvokeResult"
    form: async
    raises: [LlmUnavailable, LlmBudgetExceeded]
data_shape:
  BrainStreamEvent:
    kind: "enum: token|status|done|error"
    data: "依 kind 而定"
    note: "與既有 StreamEvent(kind='updates', data) **刻意不同**——那正是分家的理由"
three_openrouter_entrances:            # 審查 R-03：OQ-7 的字面主題是「**三份**」，原版只比對兩份
  requirement_verbatim: "`requirements.md:486` 逐字：「大腦自建 runtime 後實際是**第三個**
                         OpenRouter 入口，不是第二個」，且「`C-S7` 的一致性驗證範圍
                         **應涵蓋它**」"
  entrance_1:
    module: "backend/services/llm_provider.py"
    constant: "OPENROUTER_BASE_URL = \"https://openrouter.ai/api\"（`:52`）"
    used_by: "A1 `design_agent`／A3 `review_agent`（Anthropic Agent SDK）"
    how: "`configure_provider_env()` 把它 setdefault 給 **ANTHROPIC_BASE_URL**（`:131`）
          並改寫整個行程的環境變數；在每個 A1／A3 請求都被呼叫"
  entrance_2:
    module: "backend/services/langgraph_runtime.py"
    constant: "DEFAULT_OPENROUTER_BASE_URL = \"https://openrouter.ai/api/v1\"（`:16`）"
    used_by: "`cost_advice_agent`（OpenAI 相容路徑，經 langchain 的 ChatOpenAI）"
  entrance_3: "本契約的大腦 adapter（第三個）"
  why_the_two_existing_values_differ:
    finding: "兩個既有常數**確實不同**（`.../api` vs `.../api/v1`），本站實讀確認"
    but: "**這不是漂移，是不同的協定面**——`llm_provider` 的值餵給 Anthropic SDK 相容
          端點（`ANTHROPIC_BASE_URL`），`langgraph_runtime` 的值餵給 OpenAI 相容端點。
          兩者本該不同"
    therefore: "**斷言它們相等會是錯的修法**。正確形狀：大腦 adapter 走 OpenAI 相容路徑，
                故只對 `entrance_2` 的 `/api/v1` 斷言相等（見下方斷言 #1），
                並另加一條斷言確認大腦**不受** `configure_provider_env` 影響（#7）"
consistency_assertions:                # [C11]=B —— 七項（修訂 1 新增 #7），皆可機械判定
  - "adapter 的 base_url == DEFAULT_OPENROUTER_BASE_URL（langgraph_runtime.py:16）"
  - "憑證環境變數名 == OPENROUTER_API_KEY_ENV（:19）"
  - "預設逾時 == DEFAULT_TIMEOUT_SECONDS（:18）"
  - "max_retries == 0（openrouter_chat_model 內逐字，:96）"
  - "憑證缺失時拋出的錯誤帶同一個 code（RuntimeAuthError.code，
     預設 'missing_openrouter_api_key'，:22–34）"
  - "**事件語彙對照表**涵蓋雙方**全部**事件種類；任一方新增事件而對照表未更新即紅燈"
  - "**（修訂 1 新增，審查 R-03）** 大腦 adapter **不讀** `ANTHROPIC_BASE_URL`、
     不呼叫 `llm_provider.configure_provider_env()`，也不因該函式被呼叫而改變行為
     ——即第三個入口與第一個入口在**行程級 env** 這一面是隔離的。這條把 `OQ-7` 點名的
     耦合變成可機械斷言的項目，而非只是散文警告"
deliberately_not_asserted:
  - item: "預設 model"
    why: "[RA:NFR10] 明文要求路由層得與功能 agent 用不同模型，故 model 必須可以不同
           ——鎖它會與 NFR10 衝突。openrouter_chat_model(model=...) 支援逐次覆寫，
           預設常數為 google/gemini-3.7-flash（:17）"
not_used_as_locking_vehicle:
  - item: "OpenRouterSettings dataclass（:52）"
    why: "**全樹無人建構或讀取**——只出現於自身定義與 __all__（:158），是死碼。
           openrouter_chat_model 直接讀模組層常數（:85–98）。鎖它等於鎖一個沒有效力
           的物件"
behaviour_semantics:
  authorization_responsibility: "**無使用者授權**——本 Port 不碰受保護資源。
                                 它持有的是**平台自己的** OpenRouter 憑證"
  observable_side_effects: "一次對外 LLM 呼叫（**可計費**）；`cancel_token` 取消後
                            上游可能已產生部分計費"
  retry_and_idempotency: "`stream` 與 `invoke` 皆**非冪等**（LLM 輸出可變、且每次呼叫
                          計費）。重試次數受 K-10 的上限約束；`max_retries == 0` 是
                          一致性斷言之一，故**底層 client 不自行重試**，重試決策一律
                          在呼叫端且受上限管制——這是避免無限升級或重試的結構前提"
settings_management: "client 設定**各自**在 provider adapter 集中管理（[C9] 逐字）"
scope_limit: "本階段**不建通用多模型框架**，**也不因可擴充性預先加入額外模型**（[C9] 逐字）"
cost_discipline: "見 K-10 的 cost_discipline；一般 CI 使用可注入替身、**不呼叫付費模型**
                  ——這同時解決 quality-agent 指出的『build-and-test 跑 ci.yml 的 backend
                  job，那裡沒有金鑰』缺口。真實模型品質以**獨立、有預算上限**的評估驗證
                  （與 [RA:NFR1] 的 ≥ 50 筆標註集相容——50 筆即小樣本）"
model_selection_still_open:
  id: "OQ-4（須與 OQ-10 一併決定）"
  statement: "路由層模型定案：typesafe/jev-1.13 vs gemini-3.7-flash"
  user_preference_recorded: "使用者在 [C9] 點名 **Jev** 作為分類器。[C10]=C 只決定
                             『一律先分類』，**不決定用哪個模型**。本站把該偏好如實
                             記入供 nfr-requirements 權衡——**記錄偏好不等於定案**"
  landing: "nfr-requirements（3.2，CONDITIONAL，**無自然承接站**，skip 時須重新提交使用者）"
```

---

## ADR-0006 Security Baseline 四面向逐項判定

`project.md ## Mandated` 要求對每一項變更逐項檢查 ADR-0006 的四個面向，並以**逐項
判定表**呈現（`requirements-analysis:c4`），判定為不適用者亦須附理由、不留空白。

**這張表是自檢第七項查出後補的。** 本站第一版產出對 ADR-0006 有處置卻**沒有判定表**
——與 domain-design 的 `R-03`、units-generation 的 `R-04` 是同型缺口，而那條規則是我
在 domain-design 的閘門上寫進 `project.md` 的。第三次了；本輪由自檢 7 自行查出。

| 面向 | 判定 | 哪些契約觸及，以及各自的處置 |
|---|---|---|
| **IAM** | **適用** | `K-03`：新增 `K1`／`K2` 兩個 story id、矩陣 308 → 330 列，走 `ensure_missing_role_permissions`（不得依賴 `force=False` 的種子，那在表非空時整段 no-op），觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步與 allow/deny 雙向測試。`K-07`：`HierarchyFacade` 為受保護操作的**唯一授權入口**，principal 為第一個參數、資源識別為具名參數、拒絕時 raise `HierarchyForbidden`、**授權未通過不得執行受保護操作**——這是 `[C1]`=C 對 domain-design `R-01`（`ProjectHierarchy.behaviour` 禁同進程繞過 vs 兩條 `sync` 入邊）的收斂。`K-08`：**第二套**授權模型（擁有者 ＋ 可見範圍），擁有者由寫入端依已驗證身分設定、**不得由呼叫方指定**，放寬範圍僅 `Platform_Admin`／`Platform_Owner`。`X-01`／`X-02`：對既有 C1／A1／A3 一律帶使用者 token，使既有 dependency 照常執行。**殘留缺口**：`K-07`／`K-08` 的「facade 是唯一入口」**無機械強制**，靠 code review——已如實記載於契約與 Assumptions |
| **Encryption** | **適用** | `K-05`：記憶列的靜態儲存加密要求為 `OQ-3`，指派 `nfr-design`（CONDITIONAL，其條件依賴 `nfr-requirements` 是否執行——與 `OQ-4`／`OQ-10` 同一條風險鏈）。本站**不預選手段**，只把它對應到 `K-05` 的資料範圍並列入 Open Questions。`K-01`：Redis 與 Ollama 的連線憑證為 `required: true` 且**無預設值**（缺值不得以空字串啟動），驗證規則明訂**不得含 `$`**（compose 會內插並無聲截斷，使資料庫以遠弱於預期的密碼運行且無任何錯誤）。`K-12`：對外傳輸為 `wss`（經 Cloudflare Tunnel），token 走標頭而非 query string，避免進 nginx 與 cloudflared 的 access log |
| **Network exposure** | **適用** | `K-12` 是本 intent **唯一**新增的對外網路面，三項硬約束皆為機械事實而非偏好：必須掛 `/api/` 之下（`location /` 走 `try_files … /index.html`，握手落那裡會拿到 HTML）；token **不得放 query string**（既有前例 `collab_router.py:270` 正是如此，本契約明文不得照抄）；握手須以 `record=True` 呼叫 `get_user_from_token`（既有前例用 `record=False`，照抄會讓帳號活動稽核對大腦使用者**靜默失效**）。另定四個關閉碼與版本協商的 4400 路徑。`K-01`：Redis 與 Ollama 兩個新服務的 `exposure` 逐字為「compose 內部網路 only；**不得 publish port**」。`X-03`：對外呼叫面為 OpenRouter，`base_url` 受一致性斷言鎖定，**不得**指向其他服務 |
| **Audit logging** | **適用** | `K-08`：`delete` 與 `widen_scope` 皆寫稽核事件（誰、何時、由什麼範圍改為什麼範圍），並提供 `list_audit_events` 查詢面。`K-07`：`record_diagram_change` 為 `DiagramChangeRecord` 的**唯一寫入端**（來源為 `U12`）。`K-12`：`record=True` 使既有的 `users.last_activity_at` 帳號活動稽核對大腦使用者**不會**靜默失效。`X-01`：稽核的行為主體為**使用者本人**，不是大腦。**兩處已知未決**：`DG-1`（稽核事件在其記憶被 90 天清除後的去向——一併刪則「刪除留稽核」失去意義，保留則 `memoryId` 懸空，`K-08` 的 `list_audit_events` 會回指不到內容的列）與 `DG-3`（`DiagramChangeRecord` 無讀取端，落點 `K-07`），皆已在 Open Questions 指派落點 |

**四面向皆適用，無不適用項。** 每個面向各有一項已知未決（IAM 的 facade 無機械強制、
Encryption 的 `OQ-3`、Network 的 `OQ-8`（`Sec-WebSocket-Protocol` 透傳未實測，是 `K-12`
token 傳輸的前提）、Audit 的 `DG-1` 與 `DG-3`）——全部已列入 Open Questions 並附落點，
本站不新增判斷，只把它們對應到具體契約。

### Property-based testing hard constraint（ADR-0006 的另一項）

ADR-0006 逐字點名 **agent routing** 須有 property-based 測試。本檔的落點：
`K-10`（`IntentRouter`）的 `pbt_note` 明寫受測對象是**門檻比較這個純函式**；
`K-06`（`EmbeddingPort`）的 `verification` 含 property-based。
**此項 compliant**——但 `K-10` 的 property 建立在 `OQ-10` 尚未定案的前提上：若結論為
「無可用信心訊號」，該純函式的輸入型態會改變，property 須重寫（已寫在該契約內）。

---

## 契約所有權規則

| 規則 | 內容 |
|---|---|
| **誰擁有規格** | 契約表的 `Owner` 欄。Provider 單元擁有其契約；消費端不得單方面修改 |
| **破壞性變更如何議定** | `[C4]`=B：WS 契約帶 `v` 欄位，不相容即以 4400 關閉。其餘契約的破壞性變更須由 provider 與**全部**消費端在同一個 PR 內一起改——`K-07`／`K-09`／`K-12` 各有 3 個消費端，是最容易漏的三條 |
| **additive 變更如何保持安全** | 消費端**忽略未知欄位**。新增欄位一律為選填或帶預設值；`K-02` 的兩道 CI gate 會擋住「只改一邊」 |
| **既有模組的契約不由本 intent 修改** | `X-01`／`X-02` 是消費契約：本 intent 只記載既有 API 實際回什麼並據以實作，不改它們。若發現既有 API 的形狀與本契約所載不符，是本契約記錯，須更正本契約 |
| **授權入口的唯一性** | `K-07`／`K-08` 的 facade 是受保護操作的唯一授權入口。此規則**無機械強制**，靠 code review——本站如實記載，不宣稱已解決 |
| **契約與實作不一致時誰對** | 契約對。但 `X-01`／`X-02` 例外（見上），以及 `K-02` 的真實來源是後端 Pydantic（契約檔本身是衍生物） |

---

## Open Questions

| 契約 | 未決事項 | 阻擋誰 | 落點 |
|---|---|---|---|
| `K-04` | `DG-2`：`Project`／`System` 刪除的 cascade；會讓 `[US:AC9.1.4]` 的不變量在**執行期**被打破 | `U4`、`U7`（`delete_*` 方法的語意） | `functional-design`（CONDITIONAL；skip 轉 `code-generation`，ALWAYS） |
| `K-05` | `DG-1`：稽核事件在其記憶被 90 天清除後的去向 | `U5`、`U9`、`U8`（`list_audit_events` 可能回指不到內容的列） | 同上 |
| `K-07` | `DG-3`：`DiagramChangeRecord` 無讀取端 | `U7` | 同上 |
| `K-09` | `OQ-1`：切回共享對話時獨立那段的處置 | `U10` | **無站承接**——`domain-design` 未定案並轉移 `units-generation`，該站亦未定案。須與 `functional-design` 的歷程 schema 一併決定 |
| `K-10`／`X-03` | `OQ-10`：路由層能否產出可比較的信心值。**須與 `OQ-4` 一併決定，不得分開處理** | `U11`（`confidence`／`below_threshold` 兩個欄位語意、PBT 的 property） | `nfr-requirements`（CONDITIONAL，**無自然承接站**，skip 時須重新提交使用者） |
| `X-03` | `OQ-4`：路由層模型定案。使用者偏好 Jev，**本站不定案** | `U11` | 同上 |
| `K-05` | `OQ-3`：episodic memory 的加密手段（靜態與傳輸） | `U5` | `nfr-design`（CONDITIONAL；其條件依賴 `nfr-requirements` 是否執行——與 `OQ-4`／`OQ-10` 同一條風險鏈） |
| `K-01` | `OQ-13`：90 天清除 workflow 如何取得資料庫連線（它跑在 GitHub Actions 上，資料庫在自架 staging 主機後面） | `U9`（**單元層級阻塞**，未定案前無法完成） | `infrastructure-design`（CONDITIONAL；skip 轉 `deployment-pipeline`，**亦 CONDITIONAL**——若都 skip 須重新提交使用者） |
| `K-11` | `H-3`：`等待中` 狀態的可達性——何謂「一個意圖依賴另一個意圖的結果」 | `U12` | `functional-design`（CONDITIONAL；skip 轉 `code-generation`，ALWAYS） |
| `K-01` | `OQ-8`：nginx／cloudflared 是否透傳 `Sec-WebSocket-Protocol`（`K-12` 的 token 傳輸依賴它） | `U13` | `infrastructure-design`（CONDITIONAL） |
| `K-12` | `OQ-5`：兩種串流機制並存的邊界（哪些路徑走 WebSocket、哪些維持 SSE） | `U13` | 上游未細分落點 |
| `X-03` | **`OQ-N1`（修訂 1 新增，修 R-01 時翻出）**：**沒有任何單元或元件擁有「產生自然語言回覆」**。`components.md:44` 的 `BrainGateway` 只做 token 串流**轉送**、`IntentRouter` 只做分類、`WorkOrchestrator` 只做編排與呼叫既有能力；但 `[RA:FR8.1]` 要求回覆逐步顯示，`[C9]`／`[C10]` 提到「需要生成自然語言回答時才呼叫文字 LLM」——那個呼叫者未被指名。本站**不自行指派**（逕自掛給 `U12` 就是 R-01 的另一種形式） | `U11`／`U12` 皆可能；未定前 `X-03` 的消費端只能是 `U11` | `functional-design`（3.1，CONDITIONAL；skip 轉 `code-generation`，ALWAYS）。**若它落在 `U12`，`delivery-planning` 需要一條 `U11 → U12` 的新邊**，故亦須通知 2.9 |
| `K-08` | **`OQ-N3`（修訂 4 新增，審查 R-14，Critical）**：**`MemoryFacade.write` 沒有任何呼叫者。** 該方法名全檔只出現一次（自己的宣告）、無 `consumed_by`；`K-08` 的 HTTP 半邊只有 `GET /records`／`DELETE /records/{memoryId}`／`PUT .../scope`／`GET /audit-events`，**無建立路徑**；唯一的同進程消費端 `U11` 依 `K-10` 自己的契約是**唯讀**（「讀記憶時經 K-08 的 MemoryFacade」，唯一方法 `classify`）。根源在上游：`components.md:199` 給 `MemoryStore` 的責任是「三種記憶的**讀寫**」，而 `:324` 宣告的唯一互動只有讀那一半——**又是半句話被實作**。**本站不以推論指派**：可能的寫入端（`U13`，或 `OQ-N1` 屆時指派「產生自然語言回覆」的那個單元）在 DAG 裡沒有 `→ U8` 的邊（`brain-gateway.depends_on: [brain-ws-contract, intent-router, work-orchestrator, session-store]`），自行加一條就是審查 R-01／R-07／R-10 的同型錯誤第四次 | **阻擋四個單元變成惰性**：無寫入端則 `memory_records` 永不被填，`MemoryFacade.search` 永遠回空、`U15` 的三區永遠空白、`U9` 的 90 天清除沒有東西可清。`[RA:FR4.1]`／`[RA:FR4.5]`／`[RA:FR4.6]`／`[RA:FR4.7]` 全部失去機制；受阻單元 `U5`、`U8`、`U9`、`U15` | `domain-design`（2.6，**CONDITIONAL**，已執行過——故實務落點為 `functional-design`（3.1，CONDITIONAL；skip 轉 `code-generation`，ALWAYS））。**若結論需要一條新的 `→ U8` 邊（例如 `U13 → U8`），該邊必須送到 `delivery-planning`（2.9，ALWAYS）**，否則 2.9 排出的 Bolt 序會缺這條約束 |
| `K-09` | **`OQ-N4`（修訂 4 新增，審查 R-15）**：**`BrainSession` 的形狀撐不起 `[DD:E6]`=A 自己要求的「兩段」。** 該定案逐字為「兩段都在同一 key 下、一起到期」，而 `BrainSession.fields` 只有**一個** `messageHistory`、`append_message(session_key, role, text)` **沒有任何參數說這則訊息屬於哪一段**。於是切到獨立模式後只有兩種結果：附加進同一份歷程 → `[RA:FR3.2]`「新對話**不共享任何訊息歷程**」在切回時被違反；或覆寫 → `[RA:FR3.3]`「使用者得隨時切回共享對話」沒有東西可回。**`OQ-1` 不涵蓋它**——`OQ-1` 問的是切回時獨立那段**如何處置**，那預設了兩段已存在。**本站不自行改上游的實體形狀**：`BrainSession` 的欄位集合是 `components.md` 已核可的產出 | `U10`（其 `public_interface` 與 `data_shape` 皆需改）；`[RA:FR3.2]`／`[RA:FR3.3]` 兩條 **Must** | `functional-design`（3.1，CONDITIONAL、per-unit；skip 轉 `code-generation`，ALWAYS）。**與 `OQ-1` 必須一併決定**——分段的表達方式與切回時的處置是同一個設計 |
| `K-07`／`K-08` | **`OQ-N2`（修訂 1 新增，審查 R-05）**：facade 唯一性的**強制手段**——是否加一道 lint／import 檢查（禁止 facade 之外的模組 import 底層 service），或接受只由 code review 擋 | `U7`、`U8`（此為 ADR-0006 IAM 面向的殘留缺口） | `functional-design`（3.1，CONDITIONAL、per-unit；skip 轉 `code-generation`，ALWAYS）。**決定不加機制是可以的，不追蹤它不行** |

---

## 本階段新增、已核可 scope 尚未涵蓋的項目（**需回補**）

既有 **N-1 至 N-11** 已用（N-1–N-7 `requirements.md`、N-8 `stories.md`、N-9
`mockups.md`、N-10–N-11 `components.md`）。本站新增 **九項**（修訂 1 由八項增為九項）：

| # | 新增項 | 來源 | 為什麼不是既有能力的延伸 |
|---|---|---|---|
| **N-12** | `ws-contract.json` ＋ `scripts/dump_ws_contract.py` ＋ 前端 WS 型別漂移檢查——**兩道新 CI gate** | `[C2]`=A | 既有兩道閘門對 WebSocket **完全無效**（WS 不在 `openapi.json` 的 42 個 path 內）。這不是擴充既有檢查，是建一道全新的 |
| **N-13** | 協定版本 `v` 欄位 ＋ 握手版本協商 ＋ 4400 關閉路徑 | `[C4]`=B | `[RA:FR8.2–8.5]` 定了傳輸、路徑、token 與活動記錄，**沒有任何一條提到版本**。版本協商是本站新增的機制 |
| **N-14** | `error(code: EMPTY_RESPONSE)` ＋ 前端對零內容 `done` 的**契約違規**處置（備援提示 ＋ 記錄異常） | `[C6]` | `components.md` 只列了 `error` 這個型別，未定義任何 code；「零內容 `done` 視為契約違規並記錄異常」是本站新增的防禦層。**`mockups.md` 的 H-7 須依此改寫**為描述這兩種情境——本站不回改已核可的 `mockups.md`，指派下游 |
| **N-15** | `HierarchyFacade` 與 `MemoryFacade` **兩個新的門面模組層** | `[C1]`=C | `components.md` 只說「不得繞過 `require_story_action`」，未指定承載形式；domain-design 把它記為已接受風險並指派 `functional-design`。本站選定 facade，即新增一層模組 |
| **N-16** | 大腦自己的 provider adapter ＋ `langgraph-consistency` 測試（六項斷言）＋ **事件語彙對照表** | `[C3]`=B、`[C11]`=B | 上游 R-8 只說「須有鎖住兩者一致性的驗證」，未定範圍；本站定為六項斷言 ＋ 一份對照表，對照表是新產物 |
| **N-17** | 可替換的 LLM 執行介面（`BrainLlmPort`）＋ **per-instance／per-test 作用域** ＋ 四種確定性替身 | `[C8]` | quality-agent 只建議抄模組層鉤子；使用者的規格明確否掉共享可變全域狀態，要求**實例級**替換——這是不同的機制，不是既有前例的沿用 |
| **N-18** | 每輪模型呼叫次數、重試次數與用量上限的**機制**（必須存在且可設定） | `[C9]` 保留部分 | `[RA:NFR9]` 逐字「此為設計原則，**非可量測的門檻**」。本站要的是實際強制的上限機制。**具體數值不在本站定案** |
| **N-19** | 14 條 AC（B3 的 12 條 ＋ B1 依賴接縫的 2 條）**依驗證範圍分配**至單元／WS 整合／前端，及其 CI 執行項目 | `[C8]` 末句 | quality-agent 的貢獻檔逐字假設「可以在 backend `unittest` 決定性地測」；使用者明確要求依驗證範圍分配、**不一律歸 backend unittest**。逐條分配表尚不存在 |
| **N-20** | **（修訂 1 補，審查 R-03）** 一條斷言大腦 adapter 與 `llm_provider` 的**行程級 env 隔離**的測試（不讀 `ANTHROPIC_BASE_URL`、不受 `configure_provider_env` 影響） | 審查 R-03 ＋ `requirements.md:486` | `OQ-7` 逐字要求驗證範圍涵蓋**第三個**入口，而原版只比對兩份；把該耦合從散文警告變成可機械斷言的項目是新工作，不是既有六項斷言的延伸 |

**逐條列出 N-19 的 14 條 AC**（本站不分配，只把清單固定下來以免遺漏）：
B3 的 12 條——`AC1.1.1`、`AC1.1.4`、`AC1.3.2`、`AC1.3.3`、`AC2.2.2`、`AC3.1.3`、
`AC5.1.1`、`AC5.1.3`、`AC6.1.1`、`AC6.1.2`、`AC6.1.3`、`AC10.1.1`；
B1 中依賴接縫的 2 條——`AC1.1.2`、`AC1.2.2`。

---

## 交接事項

| # | 事項 | 落點 | execution（本站查 `stage-graph.json` 所得） |
|---|---|---|---|
| J-1 | 全部實體的完整 schema（型別、約束、允許值、關係基數）——本檔只到介面與資料形狀 | `functional-design`（3.1） | CONDITIONAL、per-unit；skip 轉 `code-generation`（3.5，**ALWAYS**） |
| J-2 | `DG-1`／`DG-2`／`DG-3` 三處契約缺口（承 domain-design 的 H-7，本站原樣傳遞並對應到具體契約） | `functional-design`（3.1） | 同上 |
| J-3 | `H-3` `等待中` 狀態的可達性 | `functional-design`（3.1） | 同上 |
| J-4 | **N-19 的 14 條 AC 逐條分配**至單元／WS 整合／前端測試，及其 CI 執行項目 | `tcms-test-cases`（3.8） | **ALWAYS** |
| J-5 | `OQ-4`（路由層模型定案，使用者偏好 Jev）與 `OQ-10`（信心值能否成立）——**兩者須一併決定** | `nfr-requirements`（3.2） | CONDITIONAL，**無自然承接站**；skip 時判定者須重新提交使用者 |
| J-6 | `OQ-3` episodic memory 的加密手段 | `nfr-design`（3.3） | CONDITIONAL；其條件依賴 `nfr-requirements` 是否執行——與 J-5 同一條風險鏈，兩站可能一併 skip |
| J-7 | `OQ-13`（90 天清除 workflow 的 DB 連線）與 `OQ-8`（`Sec-WebSocket-Protocol` 透傳實測）——後者是 `K-12` token 傳輸的前提 | `infrastructure-design`（3.4） | CONDITIONAL；skip 轉 `deployment-pipeline`（4.1，**亦 CONDITIONAL**）——若都 skip 須重新提交使用者 |
| J-8 | `K-01` 三處部署設定同步（`render-env.sh`／`.env.example`／`LOCAL-DEV.md`）與 Redis／Ollama／pgvector 的實際資源需求（domain-design 標明 RAM／模型大小未在 staging 實測） | `infrastructure-design`（3.4） | 同 J-7 |
| J-9 | `N-18` 呼叫上限的**具體數值** | `nfr-requirements`（3.2） | CONDITIONAL，無自然承接站（同 J-5）；亦可由 `build-and-test`（3.6，**ALWAYS**）在有實測基準後定 |
| J-10 | `mockups.md` H-7 依 `N-14` 改寫為描述 `EMPTY_RESPONSE` 與「零內容 `done` ＝契約違規」兩種情境 | `refined-mockups` 已核可，**本站不回改**；改寫落點 `functional-design`（3.1） | CONDITIONAL；skip 轉 `code-generation`（3.5，ALWAYS） |
| J-11 | `OQ-1`（切回共享時獨立那段的處置）——`domain-design` 與 `units-generation` 皆未定案，**本站亦不定案** | `functional-design`（3.1） | CONDITIONAL；skip 轉 `code-generation`（3.5，ALWAYS）。**注意這是第三次轉手**，若再落空須重新提交使用者 |
| **J-12** | **`OQ-N2` facade 唯一性的強制手段**（修訂 1 補，審查 R-05：原本只活在一個 `[assumption]` bullet，既無 J-row 也無回補項，而其他每一項 open item 都有 J-row。這正是我自己寫進 `project.md` 的「CONDITIONAL 不附轉移目標會無聲落空」） | `functional-design`（3.1） | CONDITIONAL、per-unit；skip 轉 `code-generation`（3.5，**ALWAYS**）。**兩站皆 skip 的情況不存在**（後者 ALWAYS），故不需重新提交使用者；但 `code-generation` 屆時是由寫 code 的人決定一個授權繞過面的強制手段，此風險如實記載 |
| **J-14** | **`OQ-N3`（Critical）記憶寫入端無人呼叫**——`MemoryFacade.write` 沒有呼叫者，使 `U5`／`U8`／`U9`／`U15` 四個單元惰性、四條 `FR4.*` 失去機制。**與 `J-13`（`OQ-N1`）很可能是同一個答案**：若「產生自然語言回覆」與「寫記憶」落在同一個單元，兩者一併解決 | `functional-design`（3.1）＋ **`delivery-planning`（2.9）** | 前者 CONDITIONAL（skip 轉 `code-generation`，ALWAYS）；後者 **ALWAYS**。**2.9 必須先知道可能出現一條新的 `→ U8` 邊**，理由同 `J-13`：2.9 排在 3.1 之前，它排好的 Bolt 序在 3.1 定案後可能失效 |
| **J-15** | **`OQ-N4` `BrainSession` 撐不起「兩段」對話歷程**——需為 `BrainSession` 表達分段並為 `append_message` 增加分段參數。**與 `J-11`（`OQ-1`）必須一併決定**：分段的表達方式與切回時的處置是同一個設計，分開決定會得出不自洽的兩半 | `functional-design`（3.1） | CONDITIONAL、per-unit；skip 轉 `code-generation`（3.5，**ALWAYS**）。注意 `J-11` 已是 `OQ-1` 的**第三次轉手**，本項與它綁在一起，若再落空須重新提交使用者 |
| **J-13** | **`OQ-N1` 誰擁有「產生自然語言回覆」**（修訂 1 補，修 R-01 時翻出）。**兩個落點**：`functional-design`（3.1）定它屬哪個元件；若結論為 `U12`，則 `delivery-planning`（2.9）需要一條 `U11 → U12` 的新依賴邊 | `functional-design`（3.1）＋ `delivery-planning`（2.9） | 前者 CONDITIONAL（skip 轉 `code-generation`，ALWAYS）；後者 **ALWAYS**。因 2.9 為 ALWAYS 且排在 3.1 之前，**2.9 必須先知道這條邊可能出現**，否則它排好的 Bolt 序在 3.1 定案後可能失效 |

---

## Assumptions & Open Questions

- 契約數 **17**（14 條跨單元 ＋ 3 條既有／外部）由 25 條邊依 provider 歸併實算得出；
  「同一個 provider 對多個消費端是同一份契約」這個歸併假設對 `K-07`／`K-08` 需要
  附註——它們對同進程與 HTTP 兩種消費端各有一半規格，但**共用同一個授權入口**，
  故仍計為一條 [assumption]
- `K-12` 的「版本走握手後首則訊息」是 `[C4]`=B 與 `[RA:FR8.5]` 相加後的**唯一自洽解**，
  非本站另作選擇。若下游認為版本應走 HTTP upgrade 階段，那需要推翻 `[C4]` 未選 C
  這個事實 [assumption]
- `X-01` 的 `completed` payload 欄位集合為**實讀 `advice_stream_router._snapshot()`
  所得**。若該既有函式日後改動，本契約記載即過期——本 intent **不改**它，但也
  **沒有任何機制**擋住它被改（它的 path 在 `openapi.json` 內，但 SSE 事件的 payload
  形狀不在 OpenAPI 的 schema 裡）。這是一個真實的未防護面 [assumption]
- `K-07`／`K-08` 的「facade 是唯一授權入口」**無機械強制**。此項於修訂 1 已升格為
  **`OQ-N2`** 並取得交接列 `J-12`（審查 R-05 指出它原本只活在本 bullet 裡）。
  以下保留原始記載：可能的補強是一道 lint／
  import 檢查（禁止 facade 之外的模組 import 底層 service），本站**不預選手段**，
  亦未把它列為回補項——它是 `N-15` 的實作細節還是獨立機制，留 `functional-design` 判 [assumption]
- `X-03` 的事件語彙對照表**尚未撰寫內容**——本站定的是「它必須存在且涵蓋雙方全部
  事件種類，任一方新增而未更新即紅燈」。對照表本身需要大腦的事件集合定稿才能寫，
  故落在 `N-16` 的實作 [assumption]
- `[RA:NFR3]`（首字 P50 ≤ 2 秒）在 `[C10]`=C 之下**仍有風險且本站未重新估算**：
  該預算幾乎全被路由層 LLM 吃掉，而 `K-10` 的分類一律執行、且 `IntentRouter` 還要
  讀記憶（`components.md` 的 Assumptions 已標明「加入記憶檢索後是否仍可達」未重估）。
  `[C9]` 的「最少上下文 ＋ 合併請求」是緩解方向，不是已驗證的達成 [assumption]

---

# 修訂 1（2026-10-03）— 能力 11／12／13 的七條新契約

**`C1`–`C11` 的十一題定案與既有 17 條契約全部有效、不回改。** 本修訂新增 7 條
（6 條 K ＋ 1 條 X）並擴充 4 條既有契約的消費端，契約總數 **17 → 24**。

## 觸發與實測基準

`units-generation` 修訂 4 把單元由 17 增為 24、邊由 25 增為 **46**（新增 21 條），
而本站產出早於它。以腳本掃 25 個關鍵詞（三個能力名、`US11`–`US13`、`FR11.`–`FR13.`、
四個新元件名、三張新表名、七個新單元名、`需求籤`、`自動改選`）：**全部 0 命中**。

**21 條新邊的歸屬實算**：`K-15` 2 ＋ `K-16` 4 ＋ `K-17` 3 ＋ `K-18` 2 ＋ `K-19` 1 ＋
`K-20` 1 ＋ `K-03` 擴充 3 ＋ `K-04` 擴充 1 ＋ `K-07` 擴充 3 ＋ `K-08` 擴充 1 ＝ **21**，
與上游邊數一致。`X-04` 不涵蓋單元邊（它是對外面）。

## `機制` 欄新增第 11 個值（`[CD1]`=A）

既有十個值（`facade`／`in-process`／`ws`／`http`／`schema`／`types`／`env`／`seed`／
`dom`／`test-target`）無一適用於 MCP：`[C7]` 的形式清單沒有它，而它的傳輸形式是未定項
（`OQ-16`）。新增 **`mcp`**（MCP 協定的工具宣告；傳輸形式與認證機制未定，見 `X-04`）。

## 修訂 1 的契約表（新增與擴充）

| # | Provider Unit | Consumer | 機制 | Owner |
|---|---|---|---|---|
| K-15 | `U18` `project-meta-data` | `U19`、`U20` | `schema` | `U18` |
| K-16 | `U19` `membership-service` | `U20`、`U21`、`U13`、`U24`、**既有停用端點的消費端 `AdminPage.tsx`** | `facade` ＋ `http` | `U19` |
| K-17 | `U20` `requirement-field-service` | `U21`、`U13`、`U23` | `facade` ＋ `http` | `U20` |
| K-18 | `U22` `progress-channel` | `U13`、`U12` | `in-process` | `U22` |
| K-19 | `U23` `project-pages-ui` | `U17` | `test-target` | `U23` |
| K-20 | `U24` `member-pages-ui` | `U17` | `test-target` | `U24` |
| X-04 | `U21` `mcp-bridge` | **External: agent 側的 MCP client** | `mcp` | `U21` |

**既有四條的消費端擴充**（原列不回改，擴充列於此）：

| # | 原消費端 | 新增消費端 | 理由 |
|---|---|---|---|
| K-03 `U3 rbac-story-ids` | `U7`、`U14` | `U19`、`U23`、`U24` | `[UG:G8]`=C 新增 `K3`（成員管理）與 `K4`（需求欄位）兩個 story id；矩陣 330 → 352 |
| K-04 `U4 hierarchy-data` | `U7` | `U18` | 三張新表的 FK 指向 `projects`／`systems` |
| K-07 `U7 hierarchy-service` | `U10`、`U12`、`U16` | `U19`、`U20`、`U23` | `ProjectMembership`／`RequirementRegistry` 驗證專案／系統存在；專案頁的清單與建立 |
| K-08 `U8 memory-service` | `U11`、`U15` | `U23` | 專案詳情頁的「記憶摘要籤」 |

**修訂 1 後共 24 條**（K 類 20、X 類 4）。

---

## 逐條契約規格（修訂 1）

### K-15 `U18 project-meta-data` → `U19`、`U20`（`schema`）

```yaml shared-schema
contract: project-meta-schema
owner: U18
consumers: [U19 membership-service, U20 requirement-field-service]
tables: [project_members, reselection_events, system_requirement_fields]
foreign_keys:
  - "project_members.project_id → projects.id（K-04 的表）"
  - "project_members.user_id → users.id（既有表）"
  - "reselection_events.project_id → projects.id"
  - "system_requirement_fields.system_id → systems.id（K-04 的表）"
columns_that_carry_semantics:
  - name: "project_members.joined_at"
    why: "FR12.4 的挑選規則（最早加入）直接讀它；平手時與 user_id 組成決定性
           tie-break 的鍵。**不得可為 null**，否則挑選在空值上無序"
  - name: "reselection_events.acknowledged_at"
    why: "橫幅已讀狀態。**以事件為鍵、不是 per-user 布林值**——後者會讓同一人
           第二次被改選時看不到橫幅，而那正是 FR12.4c 要防的情境"
  - name: "system_requirement_fields.value"
    why: "**必須可為 null**。ADR-015：『從未填過』＝無列、『清空』＝有列而 value 為
           null 且 clearedAt 有值。若設為 NOT NULL，兩種狀態在資料層不可區分，
           而畫面 M12 要求區分"
  - name: "system_requirement_fields.cleared_at"
    why: "獨立於 value 的欄位，使清空動作可被稽核（誰清、何時清）"
  - name: "system_requirement_fields.updated_on_behalf_of"
    why: "由大腦代某個 agent 寫入時才有值；使用者得以分辨哪些值是自己填的"
ddl_comment_requirement:
  rule: "`system_requirement_fields` 的 DDL COMMENT 必須寫明 `[UG:G9]`=A 的行為：
         欄位定義被移除後其值列**保留**、畫面不渲染該組、未填計數只統計當前已宣告
         的欄位"
  why: "不寫下來的話，『資料庫裡有、畫面上看不到』的列會被下一個人當成髒資料清掉"
blocking_sync:
  rule: "新增三張表即觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步
         （`project.md ## Mandated`）——未完成不得標示相關 Construction／部署階段為完成"
  note: "與 `K-03` 的 seed 語意變更各觸發一次，**兩者不可互相替代**"
behaviour_semantics:
  authorization_responsibility: "**無**——DDL 在部署／啟動路徑執行，不經使用者授權。
                                 資料的存取授權由 `K-16`／`K-17` 的 facade 承擔"
  observable_side_effects: "建三表 ＋ 其索引與外鍵。**不含任何資料寫入**
                            （與 `K-04` 不同，本契約沒有遷移步驟：三張表皆為全新，
                            沒有既有資料要搬）"
  retry_and_idempotency: "全部 DDL 以 `IF NOT EXISTS` 撰寫，可重跑安全。
                          無資料寫入故無冪等性風險"
known_constraint_inherited_from_K04:
  statement: "`schema_rbac.sql` 只在**空 volume** 執行；既有環境的唯一演進路徑是
              `database.py` 的 `_ensure_*` 補丁，而它們**全部吞掉失敗**"
  consequence: "本契約的三張表若走該路徑建立，失敗必須**大聲失敗**而非被吞掉"
verification: "真實 PostgreSQL CI job"
```

### K-16 `U19 membership-service` → `U20`、`U21`、`U13`、`U24` ＋ 既有停用端點（`facade` ＋ `http`）

**`[CD2]`=A 與 `[CD3]`=A 的落點。** 本契約是修訂 1 最重要的一條：它同時是 per-project
授權判定的唯一來源、四個消費端的 facade、以及一處**既有端點的契約擴充**。

```yaml shared-schema
contract: membership-authorized-facade
owner: U19
consumers:
  in_process: [U20 requirement-field-service, U13 brain-gateway]
  http: [U24 member-pages-ui]
  separate_process: [U21 mcp-bridge]
authorization_model:
  sole_entry: "MembershipFacade —— 受保護操作的**唯一**授權入口，**且同時是
               per-project 授權判定的唯一提供者**（ADR-012）"
  two_layer_rule: "FR12.6 的兩層串聯：全域那一層仍由既有 require_story_action 承載
                   （本元件**不重新實作它**），per-project 那一層由本 facade 判定。
                   任一層不過即拒"
  forbidden_bypass: "禁止的是**跳過本 facade 直接讀 `project_members` 表**。
                     `sync` 入邊本身是**預期且允許**的呼叫方式——ADR-012 明記這兩件事
                     不同，而 `ProjectHierarchy` 上一輪正是把它們寫成同一句話而自相矛盾"
  two_facade_layers:
    statement: "`U20` 自己也有 facade（K-17），於是出現 facade 呼叫 facade 的兩層。
                兩層的責任切分如下，**不得互相假設對方已檢查**"
    U19_layer: "判定『這個 principal 在這個 project 是什麼角色』，以及成員關係本身的
                受保護操作（邀請／移出／角色變更／自動改選）"
    U20_layer: "判定『這個 principal 能不能寫這個 system 的需求欄位』——它呼叫 U19 取得
                per-project 角色，但**自己負責**把角色映射到欄位操作的許可"
    anti_double_check: "`U20` 不得重複呼叫 require_story_action 做全域層檢查
                        （它的 router 已經做了）；`U19` 不得假設呼叫端已做 per-project 判定"
  identity_passing: "每個 facade 方法的第一個參數為 principal（已驗證的身分 ＋ 其全域角色），
                     由呼叫端傳入；facade 不自行從 request 取身分。
                     **`U13 brain-gateway` 的特殊性**：它是 WebSocket，握手之後每則訊息
                     都在同一個連線裡、**不經 FastAPI 的 dependency 鏈**，故它必須把握手時
                     取得的 principal 自行保存並逐次傳入"
  resource_context: "projectId 為具名參數，不得藏在 payload 內"
  on_denied: "raise MembershipForbidden(story_id='K3', action=<action>, project_id=<id>)
              —— **不是** HTTPException。router 層轉 403；同進程呼叫端自行處置"
  hard_rule: "授權未通過時**不得執行受保護操作**；判定先於任何讀寫，失敗即中止"
  residual_gap: "『facade 是唯一入口』**無機械強制**（同 K-07 的 OQ-N2）。
                 本契約額外的殘留缺口：per-project 判定結論由伺服器產生、前端不得推導
                 （I-5），但**沒有機制擋住前端自己猜**"
public_interface:
  - name: MembershipFacade.resolve_project_role
    params: "principal, project_id: str"
    returns: "ProjectRole（project_admin | member）| None（非成員）"
    form: sync
    raises: [MembershipNotFound]
    consumed_by: [U20, U13, U21]
    note: "**這是 per-project 判定的唯一入口。** 回 None 代表非成員——呼叫端須把它
           當成拒絕，不是當成預設角色"
  - name: MembershipFacade.list_members
    params: "principal, project_id: str"
    returns: "list[MemberView]（userId, displayName, role, joinedAt）"
    form: sync
    raises: [MembershipForbidden, MembershipNotFound]
    consumed_by: [U24]
  - name: MembershipFacade.invite_member
    params: "principal, project_id: str, user_id: str, role: ProjectRole"
    returns: "MemberView"
    form: sync
    raises: [MembershipForbidden, MembershipNotFound, MissingGlobalPermission]
    consumed_by: [U24]
    note: "**成功邀請是一級行為**（US12.6 的上游缺口指派 units-generation 已處置）：
           成功時成員清單必然多一列。`MissingGlobalPermission` 對應 FR12.6a，
           且**被拒時不得留下半套狀態**（AC12.5.3）——整個操作在單一交易內"
  - name: MembershipFacade.remove_member
    params: "principal, project_id: str, user_id: str"
    returns: "None"
    form: sync
    raises: [MembershipForbidden, MembershipNotFound, LastAdminGuard]
    consumed_by: [U24]
    note: "**成功移出是一級行為**：成功時清單必然少一列，且該成員其後讀取本專案資料
           被拒。`LastAdminGuard` 見下方 last_admin_guard 區塊"
  - name: MembershipFacade.change_role
    params: "principal, project_id: str, user_id: str, role: ProjectRole"
    returns: "MemberView"
    form: sync
    raises: [MembershipForbidden, MembershipNotFound, LastAdminGuard]
    consumed_by: [U24]
    note: "一個專案可同時有**多位** project_admin（FR12.3）；指定第二位**不得覆寫**
           第一位。AC12.2.4 斷言兩位都能執行管理動作"
  - name: MembershipFacade.assert_can_deactivate
    params: "principal, target_user_id: str"
    returns: "None（通過）"
    form: sync
    raises: [LastAdminGuard]
    consumed_by: ["既有停用端點 user_router.py:673"]
    note: "**這是既有端點的契約擴充，見下方 existing_endpoint_extension**"
  - name: MembershipFacade.select_successor
    params: "members: list[MemberSnapshot]"
    returns: "MemberSnapshot（被選中者）"
    form: sync
    raises: []
    note: "**純函式，不讀 DB**——這是 ADR-0006 PBT hard constraint 能作用的結構前提。
           輸入為成員集合、輸出為被選中者。平手時以 (joinedAt, userId) 做決定性
           tie-break，形狀沿用 backend/cost/estimate_readers.py:247-251 的
           best_clouds（key=lambda item: (-item[1], item[0])）"
last_admin_guard:
  rule: "專案不得失去最後一位管理者。守門判定**位於三條路徑的共同上游**，
         不是三處各寫一次"
  three_paths:
    - "既有停用端點（`assert_can_deactivate`）"
    - "自我降級（`change_role` 把自己改為 member）"
    - "自我移出（`remove_member` 移除自己）"
  why_common_upstream: "[US:D-06] 的 Critical；`functional-design:c34` 記過同形缺陷
                        ——修在單一入口會把違規從一個位置挪到另一個位置而不是消除它"
  on_violation: "raise LastAdminGuard(projects=[<專案清單>])"
existing_endpoint_extension:
  endpoint: "既有的停用使用者端點（`user_router.py:673`）"
  change: "在執行 `target_user.is_active = request.is_active` **之前**呼叫
           `assert_can_deactivate`；命中則回 **409** 並於回應中列出那些專案"
  response_model_requirement:
    rule: "route decorator 必須**顯式**宣告 `responses={409: {\"model\": <列出專案的回應模型>}}`"
    why: "實測 `openapi.json` 的 55 個 operation 宣告的狀態碼只有
          `{200:53, 422:45, 201:1, 204:1}`，**非 2xx/422 的宣告數為 0**。
          不顯式宣告則該契約不會進入 spec、前端也產不出型別——
          `dump_openapi.py --check` 會保持綠燈（[RA:FR12.5b]／[US:V-08]）"
  no_database_backstop:
    statement: "**這個檢查是唯一防線。** 停用端點做的是 UPDATE，外鍵對 UPDATE 零效力；
                而 `schema_rbac.sql` 對 `projects.owner_user_id` 的 COMMENT 逐字為
                『deletion behaviour ... **deliberately NOT decided**』——那是刻意留的
                未決項，不是既有的保護"
  existing_consumer: "AdminPage.tsx（既有）"
  batch_constraint:
    rule: "**不可分批**：本變更改既有端點的回應契約，而 `AdminPage.tsx` 是既有消費端，
           兩者必須同批部署"
    basis: "`delivery-planning:c6` 只適用於**既有**端點的回應形狀變更——這一條正是，
            故該約束在此**成立**（與 `U2` 那次判為不適用的理由正好相反）"
    note: "本站只陳述約束，Bolt 切分仍是 2.9 的決定"
  preserved_existing_protections:
    statement: "該端點（`update_user_active`，`user_router.py:636`）既有的**兩道**保護
                **不得被本變更削弱**。兩道的位置本站已開檔逐一核對："
    guards:
      - "`:645-646` —— `if target_user.id == admin_user.id and not request.is_active:`
         → `raise HTTPException(400, detail=\"無法停用自己的帳號\")`（自我停用守門）"
      - "`:667-671` —— `if admin_edit_count <= 1:`
         → `raise HTTPException(400, detail=\"無法停用：系統必須保留至少一位可編輯使用者角色的管理員\")`
         （最後一位可編輯角色的全域管理員守門）"
    line_number_correction_history:
      first_attempt: "`:651` 與 `:668-671` —— **兩者皆錯**（審查 `R-01`，Major）"
      what_was_wrong:
        - "`:651` 是**算錯的**：我以 `awk NR>=630` 的切片序號回推而多算 6 行，實為 `:645`"
        - "`:668-671` 指到的是 `raise HTTPException(...)` 的**本體**，把條件判斷那一行
           （`:667`）排除在引用範圍外——守門是那個 `if`，不是它的 raise"
      how_corrected: "改以 `grep -n 'target_user.id == admin_user.id\\|admin_edit_count <= 1'`
                      直接取行號，不再從切片回推"
      why_recorded: "本輪自檢 3 曾宣稱這兩個行號是『因核對而改寫』的結果——**而改寫後仍是錯的**。
                     保留這段歷史是因為『重新核對也會錯』這件事本身是下游判斷可信度的依據"
    note: "新的 409 檢查與這兩道是**不同層級**：既有兩道管的是**全域**管理員與自我停用，
           新的管的是**per-project** 的唯一成員。三者都在 `:673` 的
           `target_user.is_active = request.is_active` 之前執行"
    failure_mode_to_avoid: "沒有成員關係表時『某專案的唯一成員』等於每一位使用者
                            （`hierarchy_migration.py:411` 為每位持圖使用者建預設專案並設為
                            owner），照字面實作會讓 409 命中**每一個**停用請求、
                            使該端點整支失效——這正是 `FR12.0` 補那張表的真正急迫性"
auditing:
  rule: "角色變更與自動改選皆須留稽核（誰、何時、對誰、舊角色、新角色）"
  hard_constraint: "**不得只沿用 `user_router.py:213` 的 `_audit_append`**——它寫
                    `logger.info`，**UI 讀不到**，而 AC12.2.2 斷言的是使用者可見的
                    變更紀錄。自動改選的稽核實體化為 `reselection_events`（K-15）"
behaviour_semantics:
  authorization_responsibility: "見本契約的 `authorization_model` 區塊
                                 （唯一入口、兩層串聯、兩層 facade 的責任切分、
                                 principal 傳遞、資源上下文、拒絕回報、授權未過不得執行、
                                 殘留缺口）"
  observable_side_effects:
    - "invite_member／remove_member／change_role 寫入 `project_members` 並留稽核"
    - "自動改選寫入 `project_members`（角色升級）＋ 一列 `reselection_events`"
    - "`assert_can_deactivate` **唯讀**，無副作用"
  retry_and_idempotency:
    - "invite_member **非冪等**——重複呼叫同一 (project, user) 必須被拒（已是成員），
       而不是建立第二列。呼叫端不得自動重試"
    - "remove_member 冪等（已不是成員時視為成功還是 NotFound，由實作定但須一致）"
    - "resolve_project_role／assert_can_deactivate 唯讀且冪等，可安全重試"
    - "自動改選**必須冪等**：owner 已被停用且已有新管理者時重跑不得再選一次，
       否則部分失敗後的重跑會產生第二次改選事件"
verification: "TestClient HTTP ＋ allow/deny 雙向 ＋ 純函式 PBT（select_successor 的
               排列不變性）＋ 既有停用端點的回應契約測試（含 409 的欄位集合）"
```

### K-17 `U20 requirement-field-service` → `U21`、`U13`、`U23`（`facade` ＋ `http`）

```yaml shared-schema
contract: requirement-field-authorized-facade
owner: U20
consumers:
  in_process: [U13 brain-gateway]
  http: [U23 project-pages-ui]
  separate_process: [U21 mcp-bridge]
authorization_model:
  sole_entry: "RequirementFieldFacade"
  delegation: "per-project 判定**委由 `K-16` 的 `resolve_project_role`**，本 facade
               不自行實作它（ADR-012：判定只有一份）"
  own_responsibility: "把 per-project 角色映射到欄位操作的許可，並檢查 K4 的全域層
                       （由其 router 的 require_story_action 承擔）"
  anti_double_check: "**不得**重複呼叫 require_story_action 做全域層檢查；
                      **不得**假設呼叫端已做 per-project 判定"
  identity_passing: "principal 為第一個參數；systemId 為具名參數"
  on_denied: "raise RequirementFieldForbidden(story_id='K4', action=<action>, system_id=<id>)"
  hard_rule: "授權未通過時不得讀寫任何欄位值"
public_interface:
  - name: RequirementFieldFacade.read_fields
    params: "principal, system_id: str"
    returns: "FieldSetView（按 agentGroup 分組；每組含 fieldKey、value|null、
              filledState: never_filled|filled|cleared、updatedBy、updatedOnBehalfOf）
              ＋ unfilled_count: int"
    form: sync
    raises: [RequirementFieldForbidden, RequirementFieldNotFound]
    consumed_by: [U23, U13, U21]
    note: "**`unfilled_count` 與分組明細由同一次查詢的結果推導、在同一個回應內回傳。**
           這是不變量 I-4 的落點：總覽籤與需求籤**不得各發一次請求**。
           e2e 只驗得出『兩個數字相等』，驗不出『同一份來源』，故此約束必須在契約層
           （回應同時帶計數與明細）而非前端（[US:V-12]／[US:Q-14]）"
  - name: RequirementFieldFacade.write_field
    params: "principal, system_id: str, agent_group: str, field_key: str, value: str,
             on_behalf_of: str|None"
    returns: "FieldView"
    form: sync
    raises: [RequirementFieldForbidden, RequirementFieldNotFound, UnknownFieldKey]
    consumed_by: [U23, U13, U21]
    note: "`on_behalf_of` 僅在由大腦代某個 agent 寫入時有值。
           `UnknownFieldKey` 對應 AC11.2.2：欄位錯綁到別組即紅燈"
  - name: RequirementFieldFacade.clear_field
    params: "principal, system_id: str, agent_group: str, field_key: str"
    returns: "FieldView（value 為 null、clearedAt 有值）"
    form: sync
    raises: [RequirementFieldForbidden, RequirementFieldNotFound, UnknownFieldKey]
    note: "**ADR-015 的清空語意**：保留列、value 設 null、記 clearedAt 與 updatedBy。
           **`U23` 本輪不提供觸發它的控件**——已核可線框 §15–§18 沒有清空控件
           （[US:D-15] 的畫面缺口），故本方法目前的呼叫端只有 `U13`／`U21`"
field_definition_source:
  rule: "欄位定義（agentGroup → fieldKey 集合）是**程式內的常數**，不是資料"
  removal_semantics: "[UG:G9]=A：定義被移除後其值列**保留**、畫面不渲染該組、
                      `unfilled_count` 只統計**當前已宣告**的欄位"
  consequence: "移除定義會讓計數下降而非留下幽靈欄位；表的列數只增不減（ADR-015 已接受）"
behaviour_semantics:
  authorization_responsibility: "見 `authorization_model`。**關鍵是委派邊界**：
                                 per-project 判定在 `K-16`，欄位層許可在本契約"
  observable_side_effects:
    - "write_field／clear_field 寫入 `system_requirement_fields`（含 updatedBy 與
       updatedOnBehalfOf 的溯源）"
    - "read_fields 唯讀"
  retry_and_idempotency:
    - "write_field **冪等**（同一 (system, group, key) 的重複寫入覆寫同一列），
       可安全重試"
    - "clear_field 冪等（已清空的列重複清空不改變狀態，但 clearedAt 是否更新須一致）"
    - "read_fields 唯讀且冪等"
verification: "TestClient HTTP（含『同一次查詢推導兩處計數』的欄位集合斷言）＋
               allow/deny 雙向"
```

### K-18 `U22 progress-channel` → `U13`、`U12`（`in-process`）

**`[CD4]`=A 的落點**：契約同時描述新介面與**被取代的既有符號**，使 `DG-6`
（完成條件橫跨新舊程式）在契約層可見。

```yaml shared-schema
contract: progress-channel
owner: U22
consumers: [U13 brain-gateway, U12 work-orchestrator]
public_interface:
  - name: ProgressChannel.open
    params: "request_key: str"
    returns: "None"
    form: sync
    raises: [DuplicateChannelKey]
    consumed_by: [U12]
    note: "`request_key` 為 **per-request** 的識別字，由入口端產生（[UG:G7]=A）"
  - name: ProgressChannel.publish
    params: "request_key: str, event: ProgressEvent"
    returns: "None"
    form: async
    raises: []
    note: "通道不存在時**不得崩潰**，亦不得靜默成功——記 log 並丟棄該事件"
  - name: ProgressChannel.drain
    params: "request_key: str"
    returns: "AsyncIterator[ProgressEvent]"
    form: async
    raises: []
    consumed_by: [U13]
    note: "通道不存在時回**空迭代器**，不拋例外。
           對外的錯誤一律為**固定訊息、不含例外原文**——現狀是 `_drain_progress`
           對 None 呼叫 `get_nowait()` 拋 `AttributeError`，**且該例外原文被送進 SSE
           給使用者**（AC13.1.3，獨立的 ADR-0006 面）"
  - name: ProgressChannel.close
    params: "request_key: str"
    returns: "None"
    form: sync
    raises: []
    consumed_by: [U12]
    note: "**請求結束時必須呼叫**（ADR-014）。只寫不刪會把跨使用者錯送換成
           無上界的記憶體成長——修掉一個失敗模式換來另一個"
key_contract:
  rule: "鍵必須是 **per-request**，由入口端產生並一路傳遞"
  forbidden_keys:
    - "`thread_id`：`agent_router.py:125` 為 `f\"user-{current_user.id}-design\"`，
       是 **per-user**；且 `design_agent.py:198` 的
       `config = {\"configurable\": {\"thread_id\": thread_id}}` 證實它**就是**
       LangGraph checkpointer 的 thread 鍵——改成 per-request 等於關掉對話記憶"
    - "「session」：`run_design_agent` 的簽章裡**不存在**這個參數（[US:V-01]）"
  passing: "`run_design_agent` 新增一個參數承載它，與 `thread_id` **並存且語意分離**
            ——`thread_id` 繼續承載對話記憶的分區，新鍵只承載進度通道"
shape_precedent:
  follow: "per-key dict，形狀沿用 `backend/cost/advice_orchestrator.py:23-24`
           （`_progress: dict[int, dict[str, Any]] = {}`）"
  do_not_follow: "**不照抄它的 `threading.Lock`**（`:24`）。那支檔案用 Lock 是因為它有
                  `ThreadPoolExecutor`（`:21` 的 `_executor`），而本單元跑在**單執行緒的
                  asyncio 事件迴圈**上——在那裡 `threading.Lock` 是 cargo cult，
                  且會在 `await` 邊界給出錯誤的安全感"
  upstream_citation_correction: "`stories.md` 的 US13 DoD 寫的路徑前綴
                                 `cost/advice_orchestrator.py` **是錯的**，真實路徑為
                                 `backend/cost/advice_orchestrator.py`（行號與內容正確）"
replaced_existing_symbols:
  why_listed_here: "[CD4]=A。這兩支既有檔在 domain-design 是 `external_dependencies`
                    而非元件；若本站也不列，就**沒有任何一份契約文件說得出哪些既有符號
                    會消失**——而那是 `U22` 完成與否的一半（DG-6）"
  symbols:
    - path: "backend/services/design_agent.py:31"
      symbol: "_progress_queue: asyncio.Queue[dict[str, str]] | None = None"
      disposition: "**刪除**，由本契約取代"
    - path: "backend/services/design_agent.py:32"
      symbol: "_last_xml: str | None = None"
      disposition: "**刪除**——先前查證它從未被讀取（死狀態），故不構成第二個外洩路徑，
                     但 US13 DoD 要求一併清理，避免下一個人沿用同一形狀"
    - path: "backend/services/design_agent.py:169"
      symbol: "memory = MemorySaver()"
      disposition: "**保留**——它是 LangGraph checkpointer 的模組層單例，不是外洩路徑。
                     列在此處是因為它使對話記憶綁在單一行程內，改 `thread_id` 語意時
                     必須把它一起看。**本契約不改它**"
    - path: "backend/services/design_agent.py:160"
      symbol: "_drain_progress（內部函式；:163 的 get_nowait() 是崩潰點）"
      disposition: "**改寫**為呼叫 `ProgressChannel.drain`"
    - path: "backend/services/design_agent.py:218"
      symbol: "把全域 _progress_queue 設為 None"
      disposition: "**刪除**——現狀使另一請求其後的 progress／xml／error 事件被靜默
                     丟棄（FR13.3）；改為 `ProgressChannel.close(request_key)`"
    - path: "backend/services/wa_collab_orchestrator.py:79"
      symbol: "run_design_agent(messages, current_xml) —— 不傳 thread_id"
      disposition: "**補傳** per-request 的鍵。順帶：它不傳 `thread_id` 使所有 A4 共編
                     使用者共用 `\"default-thread\"`（FR13.4，已由上游兩位 agent 獨立複驗
                     為真），該缺陷是 US13 的第二個修復對象，**與進度通道是兩回事**"
  completion_criterion: "本契約完成的判準含『上列五個 disposition 為刪除或改寫的符號
                         在 repo 中不再以舊形式存在』——這是一個可 grep 的條件"
behaviour_semantics:
  authorization_responsibility: "**無受保護操作**——進度事件的可見性由 `request_key` 的
                                 不可猜性保證，不由授權判定。
                                 **但這正是它要修的缺陷所在**：現狀的模組層全域使
                                 一個使用者收到另一個使用者產生的架構圖 XML，那是
                                 跨帳號內容外洩（ADR-0006 IAM 面），而修法是**隔離**
                                 而非加授權"
  observable_side_effects: "行程內狀態的建立與移除；無持久化、無跨行程可見性"
  retry_and_idempotency:
    - "open 對同一鍵重複呼叫須拋 `DuplicateChannelKey`，不得靜默覆寫
       （覆寫會讓前一個請求的事件憑空消失）"
    - "close 冪等（已關閉的鍵重複關閉視為成功）"
    - "drain 可被重複呼叫但**不保證重放**——事件一經取出即消耗"
verification: "以 `asyncio.Event` barrier 釘住交錯順序的併發測試，斷言兩個重疊請求的
               事件集合**互斥且各自非空**。**不得以 `sleep` 製造交錯**——
               `frontend/playwright.config.ts:17` 與 `ui-regression` 都容忍 flaky，
               一個 flaky 的併發測試等於沒有測試（[US:Q-07]）。
               前例：`backend/tests/test_langgraph_migration.py`
               （`IsolatedAsyncioTestCase` ＋ patch），**不需新 seam**"
```

### K-19 `U23 project-pages-ui` → `U17`（`test-target`）

```yaml shared-schema
contract: project-pages-test-target
owner: U23
consumers: [U17 a11y-gate]
test_target_surface:
  routes: ["專案／系統清單頁", "建立頁", "專案詳情頁（總覽／需求／記憶摘要三籤）"]
  note: "精確 path 由 `functional-design`／`code-generation` 定；本契約定的是
         『這些畫面必須存在且可被 axe 掃描』"
  data_testid_prefix: "brain-* （沿用 `U14` 的既有慣例）"
axe_scan_obligation:
  rule: "`U17 a11y-gate` 的掃描範圍由兩頁擴為**四頁**（入口頁、/memory、本契約的專案頁、
         `K-20` 的成員頁）"
  basis: "[US:D-10]（Critical，轉移至 units-generation 後已處置）：無障礙清單的範圍表
          無任何一列涵蓋線框 §15–§18 與 §22–§26"
  still_out_of_scope: "§27 所在的 `/admin/*` **仍被明文列為不管**，該判定本輪不翻案
                       ——交接事項 `UG-5`"
required_accessible_behaviour:
  - "未填欄位須以**文字**標示『未填』，不得只靠顏色（AC11.2.1）"
  - "載入態與錯誤態須有 live region；**不得**沿用 `AdminPage.tsx:104` 的 4 秒 toast
     形狀（無 `role`／`aria-live`），亦不得沿用 `:299-302` 的整塊純文字（[US:D-08]）"
  - "首次使用時清單頁為**空狀態**（說明 ＋ 建立按鈕），不得是一張空表（AC11.1.2）"
  - "儲存失敗時**輸入值不消失**（AC11.2.3）"
behaviour_semantics:
  authorization_responsibility: "**無**——本契約是測試標的的存在性約定。
                                 頁面自身的可見性把關由 `K-03` 的 `K4` story id 承擔"
  observable_side_effects: "無（測試標的契約）"
  retry_and_idempotency: "axe 掃描唯讀且冪等"
verification: "Playwright e2e ＋ axe 掃描（違規即 CI 紅燈）"
```

### K-20 `U24 member-pages-ui` → `U17`（`test-target`）

```yaml shared-schema
contract: member-pages-test-target
owner: U24
consumers: [U17 a11y-gate]
test_target_surface:
  routes: ["成員頁（清單）", "成員詳情頁（角色下拉、移出專案、變更紀錄）", "邀請對話框"]
  cross_page_component:
    name: "交棒橫幅（ReselectBanner）"
    mount_point: "使用者**自己的落地頁**（不限入口頁）"
    why: "`FR1.8`／Flow 4 的 `DefaultRedirect` 把使用者送到他自己的落地頁，
           而只有具 `C1 view` 的成員才會落在入口頁——照『入口頁』實作會讓一個只有
           `C1 view` 的合法成員**永遠看不到**這則通知，而通知的全部目的就是讓他知道
           自己成了管理者（[US:D-17] 的 Critical）"
  data_testid_prefix: "brain-*"
required_accessible_behaviour:
  - "橫幅須**在落地時即存在於 DOM**，或改用等價的 `role=\"status\"` 機制——
     `aria-live=\"polite\"` 在其自述前提下不會被朗讀（[US:D-11]）"
  - "成員清單上**沒有**可直接改角色的控件（AC12.2.3）；角色只在成員詳情頁變更"
  - "移出專案為破壞性動作，須二次確認對話框（線框 §25）"
  - "邀請對話框須有**拒絕態**——§24 的既有 `(i)` 文案在 `FR12.6a` 之後變成假的
     （現在是『缺權限者根本不能被邀請』）。依 `refined-mockups:c3` 不回改已核可線框，
     在此明記為對齊修正"
  - "載入態與錯誤態的 live region 要求同 `K-19`"
banner_dismissal:
  rule: "『知道了』與『查看成員』兩個動作各有定義的效果：按下任一後該橫幅不再出現，
         且該已讀狀態**伺服器持久化**（換裝置重新登入亦不再出現，AC12.4.4）"
  key: "以該次改選**事件**的識別字為鍵（`reselection_events.acknowledged_at`），
        **不是 per-user 布林值**——後者會讓同一人第二次被改選時看不到橫幅"
behaviour_semantics:
  authorization_responsibility: "**無**——可見性把關由 `K-03` 的 `K3` story id ＋
                                 `K-16` 的 per-project 判定承擔。
                                 **前端不得自行推導 per-project 判定結論**（I-5）"
  observable_side_effects: "無（測試標的契約）；頁面的寫入動作一律經 `K-16` 的 facade"
  retry_and_idempotency: "axe 掃描唯讀且冪等"
verification: "Playwright e2e ＋ axe 掃描。
               **`I-6` 的『同一人第二次被改選』情境需要兩個專案的 owner 先後被停用**
               ——可達但需刻意構造，驗證層只能是後端 `TestClient` 而非 Playwright"
```

### X-04 `U21 mcp-bridge` → **External: agent 側的 MCP client**（`mcp`）

**`[CD1]`=A 的落點。** 本契約**刻意是部分的**：工具 schema 與憑證欄位白名單現在就定，
傳輸形式與認證機制明記為未定。不假裝完整。

```yaml shared-schema
contract: mcp-tool-surface
owner: U21
consumers: ["External: agent 側的 MCP client（消費者是 agent 而非人）"]
mechanism: mcp
process_boundary:
  statement: "跑**獨立進程**（[F16]=B，取代 [S13]=A 的同進程封裝）。
              本 intent 的**第二個**新增進程邊界，第一個是 Redis"
  exposure: "**不得對外暴露，僅供同主機的大腦進程連接**（requirements.md:619）。
             暴露範圍**不是**未定項——上游已鎖"
credential_whitelist:
  rule: "每一個工具的 `inputSchema.properties` 採**白名單**：宣告允許的欄位集合，
         其餘皆不得出現"
  blacklist_floor: "白名單之外另設底線斷言——不得出現任何名稱匹配
                    `token`／`key`／`secret`／`authorization`（**不分大小寫**）的欄位"
  why_whitelist_not_blacklist: "[US:V-11]：黑名單必要但不充分"
  scope_exclusion: "斷言**必須排除**根目錄的 `.mcp.json`——那是 AI-DLC 框架自己的
                    client 設定（`context7`／`aws-*`／`mermaid`），不是本單元的產出；
                    不排除會讓測試去檢查框架的設定檔"
  why_irreversible: "token 一旦進入 LLM context 就會被 LangGraph checkpointer **持久化**
                     並出現在任何 `tool_calls` log。這是 ADR-0006 encryption 面
                     **唯一**的新落點，且它**不依賴傳輸形式**——故現在就寫成斷言"
tools:
  - name: read_requirement_fields
    inputSchema_properties_allowed: [system_id]
    returns: "FieldSetView（同 K-17 的 read_fields 回傳形狀）"
    note: "經 `K-17` 的 facade，不直接讀表"
  - name: write_requirement_field
    inputSchema_properties_allowed: [system_id, agent_group, field_key, value]
    returns: "FieldView"
    note: "`on_behalf_of` **不是**工具參數——它由本 bridge 依 agent 身分填入，
           否則 agent 可以冒充別的 agent"
token_forwarding:
  rule: "使用者 token **不經工具參數**傳遞"
  path: "本 bridge 代使用者以 HTTP 呼叫既有 API 並帶該 token，使
         `require_story_action` 照常執行（FR11.6；`FR10.2` 禁止同進程繞過的規定
         在改為獨立進程後**仍然適用**）"
  audit_subject: "稽核主體必須是**使用者本人**而非大腦服務帳號"
  how_token_reaches_this_process: "**未定（`OQ-15`）**——token 由誰注入該進程、
                                   生命週期多長、如何隨使用者切換，皆未定案。
                                   落點：`contract-design`（本站，CONDITIONAL）→
                                   已轉移 `code-generation`（3.5，ALWAYS），見 `UG-6`"
deliberately_incomplete:
  transport: "**未定（`OQ-16`）**：stdio 或本機 HTTP／SSE。落點
              `infrastructure-design`（3.4，CONDITIONAL）→ `code-generation`（ALWAYS）"
  consequence_of_the_gap:
    - "**傳輸層的錯誤語意寫不出來**——連線中斷、逾時、半開連線的行為本契約未定義"
    - "**Encryption 面的實際要求隨它而定**：stdio 不過網路；HTTP／SSE 須為本機迴環
       或加密。本契約只鎖『不得對外暴露』這一層"
  not_a_substitute: "以上兩項**不得**被下游讀成『本契約已涵蓋』。
                     本站選擇寫一條部分契約而非留白，理由是 `C-T11` 可以現在就斷言；
                     但部分就是部分"
untested_premise:
  id: A-7
  statement: "『MCP 生態可在本 repo 運作』**本 intent 全程未實測**——repo 內零 MCP
              基礎設施（`backend/` 對 `mcp` 僅一處命中，是 `user_router.py:85` 的
              RBAC story 標籤）"
  landing: "`contract-design`（本站）→ 已轉移 `code-generation`（3.5，ALWAYS），見 `UG-1`"
  honest_note: "本契約的工具形狀是依 MCP 協定的一般形式寫的，**沒有在本 repo 跑過**"
behaviour_semantics:
  authorization_responsibility: "**每次呼叫都以使用者身分受權限檢查**，agent 不得做
                                 使用者不能做的事（FR11.6）。per-project 判定委由
                                 `K-16` 的 `resolve_project_role`；全域層由被呼叫的
                                 既有 API 的 `require_story_action` 承擔"
  observable_side_effects: "`write_requirement_field` 經 `K-17` 寫入一列，
                            並記 `updatedOnBehalfOf`"
  retry_and_idempotency: "`read_*` 唯讀冪等；`write_requirement_field` 冪等
                          （同一 (system, group, key) 覆寫同一列）"
verification: "工具 schema 的**結構斷言**（白名單 ＋ 憑證名稱底線，排除 `.mcp.json`）
               ＋ 代使用者呼叫的 allow/deny 雙向"
```

---

## 修訂 1 的 ADR-0006 四面向逐項判定

承已核可的 `requirements.md:622`「四面向皆適用，無不適用項」，本節**不重判適用性**，
只判「修訂 1 的七條新契約有沒有新落點」。

| 面向 | 判定 | 修訂 1 的新落點 |
|---|---|---|
| **IAM** | **適用（四處，本修訂最重的一面）** | ① `K-16` 是 per-project 授權判定的唯一來源，且「專案不得失去最後一位管理者」的守門位在**三條路徑的共同上游**。② `K-16`／`K-17` 的**兩層 facade 責任切分**明訂不得互相假設對方已檢查——這是本修訂新引入的結構風險，故寫進契約而非注意事項。③ `K-03` 擴充的 `K3`／`K4` 是 `role_permissions` seed 語意變更，須走 `ensure_missing_role_permissions` 並補 allow/deny 雙向。④ `X-04` 每次呼叫以使用者身分受檢，稽核主體為使用者本人 |
| **Encryption** | **適用（一處）** | `X-04` 的工具 schema 白名單 ＋ 憑證名稱底線斷言，排除 `.mcp.json`。**理由是不可逆**：token 進入 LLM context 即被 checkpointer 持久化。傳輸層的加密要求隨 `OQ-16` 而定，本契約**未涵蓋**（已明記為 `deliberately_incomplete`） |
| **Network exposure** | **適用（一處）** | `X-04` 的 `process_boundary`：第二個新增進程邊界，**不得對外暴露、僅供同主機**。暴露範圍已鎖，未定的只有傳輸形式 |
| **Audit logging** | **適用（三處）** | ① `K-16` 的角色變更與自動改選稽核，**不得只沿用 `_audit_append`**（它寫 `logger.info`，UI 讀不到），改選實體化為 `reselection_events`。② `K-17` 的 `clear_field` 留 `clearedAt` ＋ `updatedBy`，使「誰清」可稽核。③ `K-15` 的 `updated_on_behalf_of` 使「誰代誰寫」可稽核 |

**四面向皆有新落點，無不適用項。**

### Property-based testing hard constraint 的逐項判定（修訂 1）

| 標的 | 判定 | 依據 |
|---|---|---|
| `K-16` 的 `select_successor` | **適用，且本契約是它第一次有介面層落點的地方** | 契約明訂它是**不讀 DB 的純函式**（輸入成員集合、輸出被選中者），這是 PBT 能作用的結構前提。可失敗的性質是**排列不變性**，不是「同一組輸入選出同一人」（後者對純函式恆真，`user-stories:c4` 警告的形狀） |
| `K-17` 的 `unfilled_count` | **不適用** | 對欄位集合的直接計算；兩處一致性由回應同時帶計數與明細的欄位集合斷言承接 |
| `K-18` 的併發隔離 | **不適用（但有不變量）** | `asyncio.Event` barrier 釘住交錯順序，不是輸入空間探索 |
| `X-04` 的 schema 白名單 | **不適用，但可機械斷言** | 對 schema 的結構斷言 |
| agent routing（既有 `K-10`） | **本修訂無新落點，缺口的另一半仍開著** | `[US:Q-13]` 指派的 `build-and-test` 那一半尚未關閉（`units-generation` 的 `UG-4`） |

## 修訂 1 的七項送審前自檢逐項結果

| 自檢 | 結果 |
|---|---|
| **1 可達性** | **2 處**。① `K-17` 的 `clear_field` **今天沒有使用者可觸發的入口**——已核可線框 §15–§18 無清空控件（`[US:D-15]`），故 `system_requirement_fields` 的「清空」態（`value` 為 null ＋ `clearedAt` 有值）在使用者路徑上**不可達**；呼叫端只有 `U13`／`U21`。已列為 `J-20`。② `K-20` 的「同一人第二次被改選」（`I-6`）需要兩個專案的 owner 先後被停用，可達但需刻意構造，驗證層只能是後端 `TestClient` |
| **2 契約端點三問** | **對七條新契約的每個宣告方法與每個共享欄位逐一跑**。`K-16` 的 10 個方法全部有具名 `consumed_by`（`resolve_project_role` 有三個消費端、`assert_can_deactivate` 的消費端是**既有端點**、`select_successor` 為內部純函式且已註明）。`K-17` 的 3 個方法有具名消費端，其中 `clear_field` 的消費端**少於兩個**——逐一判定後確認是真缺口（畫面沒有入口）而非內部方法，已列 `J-20`。`K-18` 的 4 個方法：`open`／`close` 消費端 `U12`、`publish` 無具名消費端（由 agent 內部呼叫）、`drain` 消費端 `U13`——**清除端有擁有者**（`close`，ADR-014）。`K-15` 的五個帶語意欄位各寫明「誰寫、誰讀、為什麼不能是 null」 |
| **3 引用逐字核對（第二版，審查 `R-01`／`R-02` 之後重做）** | **第一版不可靠，這是如實記載。** 第一版只核對「本輪新寫的五處」，而審查查出**四處錯誤**：兩處是我在第一版**特意重新核對並改寫過**的（既有兩道守門的 `:651`／`:668-671`，實為 `:645`／`:667`——前者是切片序號回推多算 6 行，後者指到 `raise` 本體而非條件判斷），另兩處（`requirements.md:617`／`:614`，實為 `:622`／`:619`，各差 5 行）**根本不在那五處清單內**。第二版改為**以腳本列舉修訂 1 區段裡每一個 `<file>:<n>` 形式的引用並逐一開檔印出該行內容**，共 **20 處**；結果：18 處正確、2 處（上述 `requirements.md`）錯誤已改，另自查出第 5 處同型錯誤 **`playwright.config.ts:17` 的路徑前綴少了 `frontend/`**（內容正確、路徑錯，與 `advice_orchestrator` 那次同形，審查未提）。**兩道守門的行號改以 `grep -n` 直接取值，不再從切片回推。** 第一版的核對結果如下，全部仍然正確：`design_agent.py:218` → `_progress_queue = None`（在 `finally` 內）✓；`hierarchy_migration.py:411` → `owner_user_id=user_id`（在 `_PROJECTS.insert().values(...)` 內，`:408-413`）✓；`user_router.py:213` → `def _audit_append(...)`，其 docstring 確認寫的是應用程式日誌 ✓；`user_router.py:673` → `target_user.is_active = request.is_active` ✓；`.mcp.json` 的 server 清單實為 `context7`／`aws-mcp`／`aws-pricing`／`aws-iac`／`aws-serverless`／`mermaid`，與契約寫的「`context7`／`aws-*`／`mermaid`」相符 ✓。**一處因核對而改寫**：原文寫「既有兩道保護（見 `:673` 上方……）」，實測兩道分別在 **`:651`**（自我停用）與 **`:668-671`**（最後一位可編輯角色的全域管理員），`:673` 是 UPDATE 那一行而非守門——已改為逐道列出行號，並明寫新的 409 與它們是**不同層級**（全域 vs per-project） |
| **4 檔案集合一致性** | 本站 `produces` 只有 `contract-summary.md` 一份，已更新；問題檔同步 |
| **5 跨檔傳播** | **以腳本從 `unit-of-work-dependency.md` 的 yaml 邊塊解析 21 條新邊，逐邊映射到 provider 單元後比對本檔**：10 個 provider 全部有涵蓋——6 個由新契約（`K-15`–`K-20`）、4 個由擴充列（`K-03`／`K-04`／`K-07`／`K-08`）。**無缺邊、無發明邊。** 另：`機制` 欄由 10 個值增為 11 個（新增 `mcp`），已在本檔前段明寫 |
| **6 可算的數字先算再寫** | **全部由腳本從本檔解析後輸出**：契約標題 `K-01`–`K-20`（**20** 條）＋ `X-01`–`X-04`（**4** 條）＝ **24**；fenced spec 區塊 **26**（21 個 `yaml shared-schema` ＋ 4 個 `yaml OpenAPI` ＋ 1 個 `yaml AsyncAPI`），**26/26 皆為合法 YAML**；`[C7]` 的三個 behaviour 鍵（`authorization_responsibility`／`observable_side_effects`／`retry_and_idempotency`）在 21 個 `shared-schema` 區塊中**無一缺漏**；新邊 21 條與上游一致。腳本是**收尾動作**，在最後一次內容改動（自檢 3 的行號更正）之後才跑 |
| **7 ADR-0006 ＋ PBT 逐項對照** | 見上方兩節。**不重判適用性**（`requirements.md:622` 已定四面向皆適用），只判新落點：IAM 四處、Encryption 一處、Network exposure 一處、Audit logging 三處；PBT 的唯一新適用標的是 `K-16` 的 `select_successor`，且本契約是它第一次有**介面層**落點的地方（明訂為不讀 DB 的純函式）。填表時逐格比對上游同名表格的判定欄，**無一格與上游相反** |

## 審查 iteration 1 的四項發現，逐項處置（2026-10-03）

iteration 1 判 **NOT-READY**（3 Major ＋ 1 Minor）。**四項全部是引用與命名的事實錯誤，
沒有一項是架構或授權模型的分歧**——審查逐項驗過的部分（21 條新邊的對映無缺無多、
26 個 fenced YAML 全部合法、21 個 `shared-schema` 區塊的三個 `[C7]` behaviour 鍵無一缺漏、
24 條契約計數、46 條邊無環、兩層 facade 的概念、`X-04` 的部分契約取捨誠實、未侵入 2.9 的
排序決定）皆維持不變。產出當時已被終局審查凍結，故經使用者送 **Request Changes**
（理由逐字記於 `GATE_REJECTED`）解鎖後修訂。

| # | 嚴重度 | 處置 | 我自己的複驗 |
|---|---|---|---|
| R-01 | Major | 兩道既有守門的行號由 `:651`／`:668-671` 改為 **`:645-646`**／**`:667-671`**，並在 `line_number_correction_history` 保留第一版錯在哪裡 | `grep -n 'target_user.id == admin_user.id\|admin_edit_count <= 1'` 實得 **645** 與 **667**，審查正確 |
| R-02 | Major | `requirements.md:617` → **`:622`**（2 處）、`:614` → **`:619`**（1 處） | 實測 `:614` 是**空行**、`:617` 是四面向表的 IAM 列；`四面向皆適用，無不適用項。` 逐字在 `:622`、`不得對外暴露，僅供同主機` 在 `:619`。審查正確 |
| R-03 | Major | `U17_layer` → **`U20_layer`**，與 `U19_layer` 對稱 | `U17` 在全檔其他每一處都是 `a11y-gate`，審查正確。已 grep 全檔確認無其他同型單元編號誤植 |
| R-04 | Minor | 契約表上方的「`機制` 欄的值」清單補上 **`mcp`**，並註明它是修訂 1 新增的第 11 個值、傳輸與認證為 `OQ-16`／`OQ-15` | 實測該清單原本只列 10 個值，而自檢 5 宣稱「已在本檔前段明寫」——那句是不實的，審查正確 |
| （自查，審查未提） | — | `playwright.config.ts:17` → **`frontend/playwright.config.ts:17`** | 內容正確（`retries: process.env.CI ? 1 : 0`）、路徑前綴錯，與 `advice_orchestrator` 那次同形 |

**修訂後的機械複驗**：以腳本重新列舉修訂 1 區段的 **22 處** `<file>:<n>` 引用並逐一開檔
印出該行內容，全部相符（`:617` 的殘留命中位於自檢 3 的敘述句內，是在描述那個錯誤本身，
非活引用）。

## 修訂 1 的交接事項

| # | 事項 | 承接站 | execution |
|---|---|---|---|
| J-16 | **`OQ-15`（token 如何進入 MCP 進程）未定**，使 `X-04` 的 `token_forwarding` 只有規則沒有機制 | `code-generation`（3.5） | **ALWAYS** |
| J-17 | **`OQ-16`（MCP 傳輸形式）未定**，使 `X-04` 的傳輸層錯誤語意與 Encryption 面的實際要求寫不出來 | `infrastructure-design`（3.4，CONDITIONAL）→ 轉移 `code-generation`（3.5，**ALWAYS**） | — |
| J-18 | **`A-7`（MCP 生態可在本 repo 運作）仍未實測**，而 `X-04` 的工具形狀沒有在本 repo 跑過 | `code-generation`（3.5） | **ALWAYS** |
| J-19 | **`K-16`／`K-17` 的兩層 facade 責任切分無機械強制**（同 `OQ-N2` 的形狀）：契約寫明了不得互相假設對方已檢查，但只有 code review 擋得住 | `functional-design`（3.1，CONDITIONAL，per-unit）→ 轉移 `code-generation`（3.5，**ALWAYS**） | — |
| J-20 | **`K-17` 的 `clear_field` 目前沒有使用者可觸發的入口**：已核可線框 §15–§18 無清空控件（`[US:D-15]`），故呼叫端只有 `U13`／`U21`。畫面缺口不在本站補 | `refined-mockups`（2.5，CONDITIONAL）→ 轉移 `code-generation`（3.5，**ALWAYS**） | — |

## 修訂 1 的 Assumptions & Open Questions

- `X-04` 是本站唯一一條**自述為部分**的契約。這是刻意的取捨（`[CD1]`=A）：
  `C-T11` 可以現在就斷言，而傳輸層不能。下游**不得**把它讀成已涵蓋傳輸層 [assumption]
- `K-16` 的 `assert_can_deactivate` 與 `AdminPage.tsx` 的**同批部署約束**是本站
  第一次對**既有**端點宣告 `delivery-planning:c6`。Bolt 切分仍是 2.9 的決定；
  本站只陳述約束 [assumption]
- `K-19`／`K-20` 的精確 route path 未定——本契約定的是「這些畫面必須存在且可被 axe
  掃描」。path 落在 `functional-design`／`code-generation` [assumption]
- `K-18` 的 `completion_criterion`（五個被取代符號在 repo 中不再以舊形式存在）是一個
  **可 grep 的條件**，但本站**沒有**為它建立機械閘門——它是契約文字而非 CI 檢查
  [assumption]
- `K-15` 的三張表與 `K-03` 的 seed 變更**各觸發一次** `schema_rbac.sql` ＋ `DEPLOY.md`
  的 blocking 同步，兩者不可互相替代 [assumption]
- 修訂 1 後契約總數 **24**（K 類 20、X 類 4）、fenced spec 區塊由 19 增為 **26**
  （新增 7 條各一個）。以上為逐條計數，非估計 [assumption]
