# Unit of Work — 統一入口大腦

<!-- Stage: units-generation（Inception 2.7）· Record: 260920-orchestration-brain
     lead: aidlc-architect-agent · support: aidlc-delivery-agent -->

## 這份檔在做什麼，以及它明確不做什麼

把 `components.md` 的 6 個元件與本 intent 的全部待建工作，切成 **17 個可實作的
工作單元**。切分軸為 `[UG:G1]`=A 定案的「**一種驗證方式 × 一個資料擁有者**」——
依 `project.md` 的 `units-generation:c6`，判準是「驗證方式與失敗模式是否同類」，
不是元件該怎麼分配。

**本檔不做的**（stage 檔明文禁止）：不推薦施工順序、不指認關鍵路徑。那是
**2.9 Delivery Planning** 的經濟決策。本檔與 `unit-of-work-dependency.md` 只描述
「什麼可以依賴什麼」與「哪些可以平行」。

**單元數為 17 而非我原本估的 12**：`[UG:G1]` 選項的標題寫「約 12 個」，
那是我**未實際枚舉就寫下的估計**；照該選項自己的軸誠實展開是 17 個。
此落差已於 Step 4 的計畫核可關卡向使用者揭露，使用者選擇接受 17 個。
**17 超出本專案既有實務的上界**（實測既有三個 intent 為 5／9／12 個單元）。

## 切分原則

| 原則 | 說明 |
|---|---|
| 驗證同類（`units-generation:c6`） | 每個單元的「完成了嗎」只指涉**一種**判準。本 intent 橫跨七種：DDL／真實 PostgreSQL、property-based 純函式、`TestClient` HTTP、`websocket_connect`、Playwright、env contract ＋ 實際部署、Actions workflow 實跑 |
| 部署模型 ＝ embedded | 既有架構是 modular monolith（單一 FastAPI `app`、`Dockerfile` 無 `--workers`）＋ 單一 SPA bundle。Unit 是**邏輯模組**，不是可獨立部署的服務。兩個例外為 `U9` 與 `U17`——它們跑在 GitHub Actions 而非 FastAPI process 內 |
| 契約先行（`[UG:G3]`=A） | WS 訊息型別與兩個 schema 皆獨立為 `spec` 類單元，是 `depends_on: []` 的可平行根：契約先定，前後端才能並行 |
| 基礎設施獨立（`[UG:G2]`=A） | `brain-infra` 獨立，因其驗證方式（`validate_env_contract.py` ＋ 實際部署）與所有程式碼單元不同類，且 `validate_env_contract.py` 是**一次驗全部**、無法分單元判定 |
| 前端按資料來源切（`[UG:G4]`=A） | 入口頁靠 WS、記憶頁靠 HTTP、對象選單靠階層 API——三者依賴不同後端單元，故可分別開工 |
| 既有模組不進單元集合 | 依 `units-generation:c22`，本檔與 yaml 邊塊**只列本 intent 待建單元**。既有的 `require_story_action`、`prompt_guard`、`get_user_from_token`、A1／A3／C1 端點、`UserDiagram`、`PaginationControl`、`apiUrl()`／`wsUrl()` 皆**已在產品內**，是前提而非單元 |

## 單元清單

| Unit ID | Unit | Directory | kind | 複雜度 | 部署模型 |
|---|---|---|---|---|---|
| `U1` | `brain-infra` | `construction/brain-infra/` | `packaging` | S | embedded（compose 服務定義；非程式碼） |
| `U2` | `brain-ws-contract` | `construction/brain-ws-contract/` | `spec` | S | embedded（就地消費的型別來源 ＋ CI 檢查） |
| `U3` | `rbac-story-ids` | `construction/rbac-story-ids/` | `spec` | S | embedded（seed ＋ SQL） |
| `U4` | `hierarchy-data` | `construction/hierarchy-data/` | `spec` | M | embedded（DDL ＋ 一次性遷移程序） |
| `U5` | `memory-data` | `construction/memory-data/` | `spec` | M | embedded（獨立 schema ＋ grant） |
| `U6` | `embedding-port` | `construction/embedding-port/` | `library` | M | embedded（library，無獨立執行期） |
| `U7` | `hierarchy-service` | `construction/hierarchy-service/` | `service` | M | embedded（同一 FastAPI process 的新 router） |
| `U8` | `memory-service` | `construction/memory-service/` | `service` | L | embedded（同一 FastAPI process 的新 router） |
| `U9` | `memory-purge` | `construction/memory-purge/` | `packaging` | S | standalone（GitHub Actions workflow，不在 FastAPI process 內） |
| `U10` | `session-store` | `construction/session-store/` | `service` | M | embedded（同一 process；狀態外部化於 Redis） |
| `U11` | `intent-router` | `construction/intent-router/` | `service` | L | embedded（同一 process） |
| `U12` | `work-orchestrator` | `construction/work-orchestrator/` | `service` | L | embedded（同一 process） |
| `U13` | `brain-gateway` | `construction/brain-gateway/` | `service` | M | embedded（同一 process 的 WebSocket route） |
| `U14` | `entry-page-ui` | `construction/entry-page-ui/` | `ui` | L | embedded（同一 SPA bundle） |
| `U15` | `memory-page-ui` | `construction/memory-page-ui/` | `ui` | M | embedded（同一 SPA bundle） |
| `U16` | `object-picker-ui` | `construction/object-picker-ui/` | `ui` | M | embedded（同一 SPA bundle） |
| `U17` | `a11y-gate` | `construction/a11y-gate/` | `packaging` | S | standalone（CI 步驟 ＋ devDependency） |

**規模分佈**：複雜度 S 5 個、M 8 個、L 4 個（`XL` 未使用）；kind `spec` 4、`service` 6、`ui` 3、`packaging` 3、`library` 1。以上由本檔清單實算。

## 各單元的責任、驗證與依賴

### `U1` `brain-infra`（`packaging`，S）

**擁有與交付**：Redis 第 5 服務 ＋ Ollama 第 6 服務 ＋ pgvector image（deploy/test 兩 compose）＋ 模型快取 volume ＋ render-env.sh／.env.example／LOCAL-DEV.md 三處同步

**驗證方式**：validate_env_contract.py ＋ 實際部署

**依賴**：（無——可平行根）　**被依賴**：`U5` `memory-data`、`U6` `embedding-port`、`U10` `session-store`

### `U2` `brain-ws-contract`（`spec`，S）

**擁有與交付**：前後端共用的 WS 訊息型別來源 ＋ 一道新的 CI 一致性檢查（N-1）

**驗證方式**：CI 規格漂移檢查

**依賴**：（無——可平行根）　**被依賴**：`U13` `brain-gateway`、`U14` `entry-page-ui`

### `U3` `rbac-story-ids`（`spec`，S）

**擁有與交付**：K1／K2 兩個 story id ＋ ensure_missing_role_permissions ＋ schema_rbac.sql／DEPLOY.md 同步

**驗證方式**：allow/deny 雙向 TestClient

**依賴**：（無——可平行根）　**被依賴**：`U7` `hierarchy-service`、`U14` `entry-page-ui`

### `U4` `hierarchy-data`（`spec`，M）

**擁有與交付**：projects／systems／DiagramChangeRecord 三表 DDL ＋ user_diagrams.system_id ＋ 遷移程序 ＋ system_id IS NULL 計數為 0 的大聲失敗

**驗證方式**：真實 PostgreSQL CI job ＋ 不變量查詢

**依賴**：（無——可平行根）　**被依賴**：`U7` `hierarchy-service`

### `U5` `memory-data`（`spec`，M）

**擁有與交付**：記憶獨立 schema ＋ grant 邊界 ＋ pgvector vector(1024) 欄位 ＋ embeddingModel 欄位（N-2 的真實 PG job 為其驗證載體）

**驗證方式**：真實 PostgreSQL CI job

**依賴**：`U1` `brain-infra`　**被依賴**：`U8` `memory-service`、`U9` `memory-purge`

### `U6` `embedding-port`（`library`，M）

**擁有與交付**：EmbeddingPort 四實作（ollama／fastembed／fulltext／stub）＋ 設定切換 ＋ 偵測不到時大聲失敗

**驗證方式**：property-based ＋ 單元測試（stub）

**依賴**：`U1` `brain-infra`　**被依賴**：`U8` `memory-service`

### `U7` `hierarchy-service`（`service`，M）

**擁有與交付**：ProjectHierarchy 的讀／建／改／刪 HTTP 端點，全經 require_story_action(K2)；建立路徑的單一寫入端（兩個入口共用）

**驗證方式**：TestClient HTTP ＋ allow/deny

**依賴**：`U4` `hierarchy-data`、`U3` `rbac-story-ids`　**被依賴**：`U10` `session-store`、`U12` `work-orchestrator`、`U16` `object-picker-ui`

### `U8` `memory-service`（`service`，L）

**擁有與交付**：記憶讀寫、擁有者與可見範圍的寫入端強制、放寬授權與稽核、相似度檢索（依 embeddingModel 分群）

**驗證方式**：TestClient HTTP

**依賴**：`U5` `memory-data`、`U6` `embedding-port`　**被依賴**：`U11` `intent-router`、`U15` `memory-page-ui`

### `U9` `memory-purge`（`packaging`，S）

**擁有與交付**：90 天逾期清除的 gh-aw／GitHub Actions workflow（決定性映射放純 Actions 步驟，不交給 LLM 路徑）

**驗證方式**：workflow 實跑

**依賴**：`U5` `memory-data`　**被依賴**：（無）

### `U10` `session-store`（`service`，M）

**擁有與交付**：SessionContext：作業對象三層、共享↔獨立、對話歷程、單一 Redis key ＋ TTL 24h 續期；獨立那段保留但不併入共享流

**驗證方式**：重啟還原測試 ＋ TestClient

**依賴**：`U1` `brain-infra`、`U7` `hierarchy-service`　**被依賴**：`U11` `intent-router`、`U12` `work-orchestrator`、`U13` `brain-gateway`

### `U11` `intent-router`（`service`，L）

**擁有與交付**：意圖分類、0–1 信心值、門檻 0.7 的反問路徑、多意圖拆解、指涉詞解析

> **單元層級的阻塞（審查 R-02 後補，比照 `U9`／`OQ-13` 的揭露形狀）**：上一行的
> 「0–1 信心值」與「門檻 0.7」**不是已定案的事實**。`requirements.md` 的 **`OQ-10`**
> 逐字問的正是「`FR1.6` 能否成立：路由層是否能產出可比較的信心值」，且須與 **`OQ-4`**
> （路由層模型定案）**一併決定，不得分開處理**。若結論為不能，`FR1.3` 的觸發條件
> 須改以「候選意圖並列且無單一最高分」表達，`FR1.7` 的 0.7 隨之不適用——本單元的
> 責任敘述與其 PBT 落點（門檻判定）都要改寫。
>
> **且這兩項比 `U9`／`OQ-13` 更急迫**：兩者皆指派 `nfr-requirements`（CONDITIONAL），
> 而 `requirements.md` 的 Open Questions 表**自己標注它們「無自然承接站」**
> （`nfr-design` 的執行條件依賴 `nfr-requirements` 已執行，故兩站會一併 skip），
> skip 時**須重新提交使用者**。`OQ-13` 至少還有 `infrastructure-design` →
> `deployment-pipeline` 的轉移鏈。

**驗證方式**：純函式 PBT（門檻判定）＋ LLM 替身。**PBT 的受測對象是門檻比較這個
純函式**，符合 ADR-0006 對 agent routing 的 property-based hard constraint；但若
`OQ-10` 結論為「無可用信心訊號」，該純函式的輸入型態會改變，PBT 的 property 須重寫

**依賴**：`U8` `memory-service`、`U10` `session-store`　**被依賴**：`U13` `brain-gateway`

### `U12` `work-orchestrator`（`service`，L）

**擁有與交付**：工作項五狀態機、逐項導回與 sideEffect、多意圖 N 個工作項、呼叫既有 A1／A3／C1（HTTP 帶 token）、成本狀態事件轉譯

**驗證方式**：純函式 PBT（狀態轉換）＋ TestClient

**依賴**：`U10` `session-store`、`U7` `hierarchy-service`　**被依賴**：`U13` `brain-gateway`

### `U13` `brain-gateway`（`service`，M）

**擁有與交付**：WebSocket 端點掛 /api/ 之下、Sec-WebSocket-Protocol 握手認證、record=True、每則輸入過 prompt_guard、token 串流

**驗證方式**：TestClient.websocket_connect

**依賴**：`U2` `brain-ws-contract`、`U11` `intent-router`、`U12` `work-orchestrator`、`U10` `session-store`　**被依賴**：`U14` `entry-page-ui`

### `U14` `entry-page-ui`（`ui`，L）

**擁有與交付**：入口頁：BrainChat／ContextBar／WorkItemDock／ClarifyCandidates／CostAnswerCard／StreamingMessage ＋ DefaultRedirect 的 K1 瀑布之首。**並含 `ContextBar` 在 `/workspace` 與 `/assessment` 兩個共享子頁面的掛載**（`[R3]` 定案子頁面與入口頁是**同一個**脈絡元件；`[RA:FR2.1]` 定案共享範圍為這三處）——`ContextBar` 內的「改為獨立對話」控件亦屬本單元，不屬 `U16`（審查 R-01 後補正）

**驗證方式**：Playwright e2e

**依賴**：`U2` `brain-ws-contract`、`U13` `brain-gateway`、`U3` `rbac-story-ids`　**被依賴**：`U16` `object-picker-ui`、`U17` `a11y-gate`

### `U15` `memory-page-ui`（`ui`，M）

**擁有與交付**：/memory 頁三區檢視與逐則刪除 ＋ Sidebar 項 ＋ 入口頁捷徑（兩入口一個顯示條件）

**驗證方式**：Playwright e2e

**依賴**：`U8` `memory-service`　**被依賴**：`U17` `a11y-gate`

### `U16` `object-picker-ui`（`ui`，M）

**擁有與交付**：切換對象選單 ＋ 就地建立表單 ＋ CreateConfirmCard（對話式建立的確認）

**驗證方式**：Playwright e2e

**依賴**：`U7` `hierarchy-service`、`U14` `entry-page-ui`　**被依賴**：（無）

### `U17` `a11y-gate`（`packaging`，S）

**擁有與交付**：@axe-core/playwright 導入 ＋ 對入口頁與記憶頁各一次掃描，違規即 CI 紅燈（N-9）

**驗證方式**：axe 掃描

**依賴**：`U14` `entry-page-ui`、`U15` `memory-page-ui`　**被依賴**：（無）

## 實作注意事項（逐單元，來自上游的硬約束）

| Unit | 注意事項 | 來源 |
|---|---|---|
| `U1` | 新增 compose 變數必須在**同一個 PR** 內由 `render-env.sh` 寫入並列於 `deploy/.env.example`；憑證值不得含 `$`（compose 會內插並無聲截斷）；異動任一 `.env.example` 須同步 `LOCAL-DEV.md` | `project.md ## Mandated`、`[kb:architecture]` 約束八 |
| `U2` | WebSocket **不在** `openapi.json` 的 42 個 path 內（FastAPI 不登錄 websocket route），故 `dump_openapi.py --check` 與 `npm run check:types` 兩道既有閘門對它**完全無效**——本單元要建的就是那道缺失的閘門 | `[kb:architecture]` 約束二 |
| `U3` | **不可依賴** `ensure_role_permissions_seeded(force=False)`——該函式在表非空時整段 no-op；必須走 `ensure_missing_role_permissions`（只 INSERT 缺失列）。矩陣由 308 列增為 330 | `decisions.md` ADR-004、`[kb:component-inventory]` |
| `U4` | `schema_rbac.sql` 只在**空 volume** 執行且含裸的 `DELETE FROM role_permissions;`；既有環境的唯一演進路徑是 `database.py` 的 `_ensure_*` 補丁，而它們**全部吞掉失敗**。遷移的不變量檢查必須**大聲失敗**而非警告。**⚠ 但那條不變量有一個已知的執行期威脅**：domain-design 自檢查出的 **`DG-2`**（`Project`／`System` 刪除的 cascade 行為**未定**）會讓 `system_id` 懸空，使「`system_id IS NULL` 計數為 0」在**遷移之後**被打破——遷移當下滿足不等於持續滿足。`DG-2` 尚未解決，落點為 `functional-design`（3.1，**CONDITIONAL**、per-unit；skip 則轉 `code-generation`（3.5，ALWAYS）），見 domain-design 的交接事項 `H-7` | `[kb:architecture]` 約束六、`[US:AC9.1.4]`、domain-design `DG-2`／`H-7` |
| `U5` | 獨立 schema 在本 repo **零前例**（全樹無 `CREATE SCHEMA`、無 `search_path`），且既有測試走 in-memory SQLite——**SQLite 沒有 schema 概念**。本單元的驗證載體是 N-2 的真實 PostgreSQL CI job，不是既有測試路徑 | `[kb:architecture]` 約束七 |
| `U6` | 四個實作的向量**不可互相比較**（同為 1024 維但不同向量空間），故每列記憶存 `embeddingModel`、檢索只比對同一 model id。偵測不到選定提供者時**大聲失敗**，不得靜默降級 | `decisions.md` ADR-008 |
| `U7` | **`DG-3` 尚未解決，其落點是本單元**。`DiagramChangeRecord` 的三個角色**分屬三個單元，修訂 2 起三處一致地這樣講**：**寫入端**是 `U12 work-orchestrator`（`components.md` 宣告 `WorkOrchestrator` 於架構圖被異動時寫入）、**schema 保管**是 `U4 hierarchy-data`（DDL 在那裡）、**讀取端**若要存在則落在**本單元 `U7`**（`ProjectHierarchy` 擁有該實體，查詢端點屬服務層）。`DG-3` 講的正是「**沒有讀取端**」，故其解決落點是 `U7`。domain-design 自檢查出**沒有任何元件、故事或畫面讀它**——而使用者定案 `[DD:E8]`=C 的理由逐字是「可用同一標籤搜尋它影響過哪些圖」，那句話描述的就是一個讀取端。本 repo 已有同型前例（`estimate_audit_events` 只寫不讀）。落點 `functional-design`（**CONDITIONAL**，skip 轉 `code-generation`，ALWAYS）；若以查詢端點承載，該端點須經 `require_story_action` 並依 `team.md` 規則 B 補 `TestClient` 測試 | domain-design `DG-3`／`H-7` |
| `U9` | **`DG-1` 尚未解決**：`[RA:FR4.5]` 要求 90 天清除、`[RA:FR4.7]` 要求刪除動作留稽核——於是本單元的清除動作會**產生**一筆稽核事件，同時讓既有稽核事件的 `memoryId` 指向一列已不存在的記憶。兩條已核可需求在此交會且互相拉扯：稽核事件一併刪除則「刪除留稽核」失去意義，保留則成為懸空參照。落點 `functional-design`（**CONDITIONAL**，skip 轉 `code-generation`，ALWAYS） | domain-design `DG-1`／`H-7` |
| `U7`／`U8` | 授權**只掛在 dependency 層**，service 層無第二道角色檢查——同進程直呼 service 函式會完整繞過 RBAC。（審查 R-01 指出本 intent 的 `U10`／`U12` → `U7` 兩條 `sync` 邊落在此風險上，已記為 Accepted risk 並指派 `functional-design`） | `[kb:architecture]` Key Design Decisions、domain-design 審查 R-01 |
| `U9` | 決定性的映射邏輯（算出哪些列逾期、發出刪除）應放**純 Actions 步驟**，不交給 gh-aw 的 LLM 路徑——LLM 路徑是本 repo 三塊結構性盲區之一 | `project.md ## Forbidden`、`[RA:FR4.5a]` |
| `U10` | 三處既有行程內狀態容器（`collab_router` 連線字典、`advice_orchestrator` 的 `_executor`／`_progress`／`_inflight`、`pricing_client` 磁碟快取）**不在本 intent 範圍**，維持原狀；本單元只保證大腦自己的 session 不落行程記憶體 | `[RA:NFR4]`、`[kb:architecture]` 約束四 |
| `U11` | 這是**第三個** OpenRouter 家族客戶端。`llm_provider.configure_provider_env()` 會改寫**整個行程**的環境變數且在每個 A1／A3 請求都被呼叫——此耦合須被明寫。（domain-design 審查 R-03 指出本項在該站未被處理，已記為 Accepted risk） | `[kb:architecture]` 約束九、domain-design 審查 R-03 |
| `U12` | **本單元是 `DiagramChangeRecord` 的寫入端**（`components.md` 宣告 `WorkOrchestrator --sync--> ProjectHierarchy`「架構圖被異動時寫入變更紀錄」），故 `U12 → U7` 這條邊於修訂 2 補入——修訂 1 的 yaml 缺它而散文卻引用了它。`DG-3`（無讀取端）的落點是 `U7` 不是本單元：本單元只寫不讀，而 `DG-3` 要的是讀。呼叫既有 C1 一律走 HTTP 帶使用者 token，**不得**同進程直呼 `estimate_intake_service`（其內無第二道角色檢查）。成本的「串流」是每秒輪詢 DB 的狀態事件，**沒有逐字可轉送** | `[RA:FR10.2]`／`[RA:FR10.8]`、`[kb:architecture]` 交易一 |
| `U13` | WS 必須掛在 `/api/` 之下（`location /` 走 `try_files … /index.html`，握手落那裡會拿到 HTML）；握手須以 `record=True` 呼叫 `get_user_from_token`（既有前例用 `record=False`，照抄會讓帳號活動稽核對大腦使用者**靜默失效**）；token 不得放 query string | `[kb:architecture]` 約束一／約束三、`[RA:FR8.3]`／`[RA:FR8.5]` |
| `U14` | 前端新增資料來源必須走 `AdminPage.tsx` 的兩層抓取形狀（`react-hooks/set-state-in-effect` 為 **error** 級，違反即 CI 紅燈）；沿用 `wsUrl()` 不自造 URL 組裝；`data-testid` 用 `brain-*` 前綴 | `team.md ## Code Style`、`design-system-mapping.md` |
| `U15` | `/memory` 走 `ProtectedRoute` **不包** `CapabilityRoute`（前例 `App.tsx:38–41` 的 `/waiting-approval`）；把關的是擁有者欄位而非角色，故**不需新 story id** | `[DM:D1]`=C 的查證 |
| `U16` | 兩個建立入口共用**同一條**寫入路徑（`ObjectCreateAction`），授權檢查、稽核紀錄與錯誤訊息各只有一份 | `interaction-spec.md` INV-2 |
| `U17` | `@axe-core/playwright` 是既有 Playwright 層的 plugin、不是新測試框架，故不落在 `[US:U9]`＝A 拒絕的範圍。`[人工]` 標記的 23 項**仍無自動化承載** | `accessibility-checklist.md`、`[DM:D6]`=A |

## ADR-0006 Security Baseline 四面向逐項判定

`project.md ## Mandated` 要求對每一項變更逐項檢查 ADR-0006 的四個面向，並以**逐項
判定表**呈現（`requirements-analysis:c4`），判定為不適用者亦須附理由、不留空白。

**這張表是補的。** domain-design 的審查以 `R-03` 記下同型缺口（該站兩份產出對
`ADR-0006` 零命中），而本站**原樣重現**了它——本站第一版的四份產出對 `ADR-0006`
同樣零命中，直到審查 `R-04` 指出。更難看的是：我在 domain-design 的閘門上才剛把
「逐一對照本專案的 hard constraint」寫進 `project.md ## Mandated`，該規則在本站是
**載入狀態**的，我仍然沒執行。根因是我實際跑的送審前自檢只有六項，而這一項不在
其中——規則被載入不等於被執行。本輪已把它定為**自檢第七項**。

| 面向 | 判定 | 本站哪些單元觸及，以及各自的處置 |
|---|---|---|
| **IAM** | **適用** | `U3 rbac-story-ids`：新增 `K1`／`K2` 兩個 story id，矩陣由 308 增為 330 列——這是 `role_permissions` **seed 語意變更**，須走 `ensure_missing_role_permissions`（不可依賴 `force=False` 的種子），並觸發 allow/deny 雙向 TestClient 與 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步。`U7 hierarchy-service`：讀建改刪一律經 `require_story_action(K2)`。`U8 memory-service`：記憶的擁有者與可見範圍為**第二套**授權模型（與 story-action 不同），放寬可見範圍僅 `Platform_Admin`／`Platform_Owner`。`U14`：`K1` 置於 `DefaultRedirect` 瀑布之首，皆不符者仍導 `/403`。**已知未決**：`U10`／`U12` → `U7` 兩條 `sync` 邊的授權語意（domain-design 審查 `R-01`，已接受風險，指派 `functional-design`） |
| **Encryption** | **適用** | `U5 memory-data`：episodic memory 是 by-user 的對話歷程，其靜態儲存與傳輸加密要求為 `requirements.md` 的 **`OQ-3`**，指派 `nfr-design`（3.3，CONDITIONAL——**其條件依賴 `nfr-requirements` 是否執行**，與 `OQ-4`／`OQ-10` 同一條風險鏈）。本站**不預選手段**，但點名它落在 `U5` 的資料範圍內。`U1 brain-infra`：Redis 與 Ollama 的連線憑證須最小權限，且憑證值不得含 `$`（compose 會內插並無聲截斷） |
| **Network exposure** | **適用** | `U13 brain-gateway`：新 WebSocket 是本 intent **唯一**新增的對外網路面。三項硬約束——必須掛在 `/api/` 之下（`location /` 走 `try_files` 會回 HTML）；token **不得放 query string**（既有前例 `useCollaboration.ts:24` 正是如此，會讓 token 進 nginx 與 cloudflared 的 access log）；握手須以 `record=True` 呼叫 `get_user_from_token`。`U1 brain-infra`：Redis 與 Ollama 兩個新服務的對外暴露面必須為**零**，僅限 compose 內部網路 |
| **Audit logging** | **適用** | `U8 memory-service`：記憶刪除與可見範圍變更皆須留稽核（`MemoryAuditEvent`，記誰、何時、由什麼範圍改為什麼範圍）。`U9 memory-purge`：90 天清除動作本身亦須留稽核——**但 `DG-1` 未解決**（清除會讓既有稽核事件的 `memoryId` 懸空，見上方 `U9` 的注意事項）。`U4 hierarchy-data`：持有 `DiagramChangeRecord` 的 schema（記錄架構圖每次異動的來源需求摘要），寫入端為 `U12 work-orchestrator`——**但 `DG-3` 未解決（無讀取端），其落點為 `U7 hierarchy-service`**，見該單元的注意事項。`U13 brain-gateway`：`record=True` 使既有的 `users.last_activity_at` 帳號活動稽核對大腦使用者**不會靜默失效**（既有 WS 前例用 `record=False`，照抄即失效） |

**四面向皆適用，無不適用項。** 四項各有一個**已知未決**的子項（IAM 的 `R-01`
兩條 sync 邊、Encryption 的 `OQ-3`、Audit 的 `DG-1`（落點 `U9`）與 `DG-3`（落點 `U7`））——全部已在上游被
記為已接受的風險或開放問題並指派落點，本站不新增判斷，只把它們對應到具體單元，
使 construction 階段知道哪個單元要處理哪一項。

### Property-based testing hard constraint（ADR-0006 的另一項）

ADR-0006 逐字點名 **agent routing** 須有 property-based 測試。本站的落點：
`U11 intent-router` 的驗證方式含「純函式 PBT（門檻判定）」、`U12 work-orchestrator`
含「純函式 PBT（狀態轉換）」、`U6 embedding-port` 含 property-based。
**此項 compliant**——但 `U11` 的 PBT property 建立在 `OQ-10` 尚未定案的前提上
（見該單元的阻塞說明）。

## Assumptions & Open Questions

- 複雜度欄（S／M／L）為**相對估計**，無工時基礎；`XL` 未使用 [assumption]
- `U6` 的 `depends_on: [brain-infra]` 取的是「ollama 與 fastembed 兩個實作要能被驗證」
  這個較嚴的判準。若只驗 `stub` 與 `fulltext` 兩個實作，本單元其實可為可平行根——
  此處刻意選較嚴的表達，代價是少一個可平行根 [assumption]
- `U9`（90 天清除 workflow）的**資料庫連線取得方式未定**——它跑在 GitHub Actions 上
  而資料庫在自架 staging 主機後面。這是 `requirements.md` 的 `OQ-13`，指派
  `infrastructure-design`，本站不定案 [assumption]
- 17 個單元的跨單元契約數量（**25 條邊**）未逐條展開為契約規格；那是
  `contract-design`（2.8，CONDITIONAL）的工作 [assumption]

---

# 修訂 4（2026-10-03）— 能力 11／12／13 的七個新單元

## 為什麼有這一輪，以及它的實測基準

`rough-mockups` 修訂 2／3、`user-stories` 修訂 1、`refined-mockups` 修訂 1、
`domain-design` 修訂 1 依序把**能力 11**（專案系統資訊需求頁）、**能力 12**（專案成員
管理）、**FR13**（既有 agent 的併發安全）補進上游，而本站原四份產出早於它們。
以腳本掃 22 個關鍵詞：**20 個在四份產出合計 0 命中**；`成員`／`專案` 的 4 處命中逐一
開檔確認**全部是無關用法**（「`depends_on` 成員皆為已宣告單元」、「該層成員」、
「本專案既有實務」）。另實算：`stories.md` 有 **31 則**故事，本站的 story map 只引用
**20 則**，`traceability.json` 兩個欄位各 **20** 筆——缺的 11 則為 `US11.1`–`US11.4`、
`US12.1`–`US12.6`、`US13.1`。

**既有 17 個單元全部有效、不改名、不插號、不回改。** 理由不是文件慣例而是磁碟現況：
`construction/` 下 `brain-infra`／`brain-ws-contract`／`hierarchy-data` 三個目錄各有
`code-generation` 的完整產出（含 `code-summary.md` 與 `reviewed-source-*.tsv`），
`rbac-story-ids` 有 `functional-design`；repo 內已有 `ws-contract.json`、
`backend/services/brain_ws_contract.py`、`backend/scripts/dump_ws_contract.py`、
`frontend/src/types/ws-contract.d.ts`、`backend/services/hierarchy_migration.py`、
`backend/services/brain_router.py`、`frontend/src/pages/BrainPage.tsx`。引擎的 per-unit
收據與 construction 目錄都以**單元名**為鍵，改名或插號會讓已完成的工作變成找不到歸屬
的孤兒。新單元一律附加為 `U18`–`U24`。

## 新增單元清單（`[UG:G6]`=A）

| Unit ID | Unit | Directory | kind | 複雜度 | 部署模型 |
|---|---|---|---|---|---|
| `U18` | `project-meta-data` | `construction/project-meta-data/` | `spec` | M | embedded（三張表 DDL ＋ 兩處 blocking 同步） |
| `U19` | `membership-service` | `construction/membership-service/` | `service` | L | embedded（同一 FastAPI process 的新 router ＋ 一處既有端點的前置檢查） |
| `U20` | `requirement-field-service` | `construction/requirement-field-service/` | `service` | M | embedded（同一 process 的新 router） |
| `U21` | `mcp-bridge` | `construction/mcp-bridge/` | `service` | L | **standalone（獨立進程，不在 FastAPI process 內；僅供同主機連接）** |
| `U22` | `progress-channel` | `construction/progress-channel/` | `library` | M | embedded（行程內狀態容器，無獨立執行期） |
| `U23` | `project-pages-ui` | `construction/project-pages-ui/` | `ui` | L | embedded（同一 SPA bundle） |
| `U24` | `member-pages-ui` | `construction/member-pages-ui/` | `ui` | L | embedded（同一 SPA bundle） |

> **Directory 欄的命名法在修訂 4 更正，且它與 stage 檔的字面指示衝突——衝突的處置寫在這裡，
> 以免下一個人把它改回去。** 本檔修訂 1–3 與修訂 4 原稿把全部 24 個單元的 Directory 寫成
> `construction/u<N>-<name>/`，而**磁碟現況與引擎的實際行為都是裸單元名**：
> `ls construction/` 實際為 `brain-infra`／`brain-ws-contract`／`hierarchy-data`／
> `rbac-story-ids`（**無 `u<N>-` 前綴**），且引擎三處獨立地以裸單元名組路徑——
> `aidlc-lib.ts:10032-10033` 的 `construction/${name}/${stage.slug}/...`、
> `aidlc-orchestrate.ts:2118` 與 `:2617` 的 `construction/${unit}/${slug}/...`、
> `aidlc-swarm.ts:746`／`:788` 的 `construction/${unit}/${stage.slug}/...`。
> 而 stage 檔 `units-generation.md:96` 逐字要求「construction directory name
> `u{n}-{description}`」——**那一句與引擎自己的路徑推導不一致**。
> **處置：以引擎與磁碟為準**（它們才是真正建立與讀取那些目錄的一方），91 處引用全部
> 改為 `construction/<name>/`，`Unit ID` 欄保留（stage 檔要求的 `U{n}` 短識別字仍在，
> 下游仍能用它 join story map）。**若照 stage 檔字面寫，對已交付的 `U1`／`U2`／`U3`／`U4`
> 四個單元就是在指一組不存在的新目錄**，正是本檔開頭警告要避免的孤兒化。
> 此衝突列為交接事項 `UG-7`。（來源：審查 `R-01`，Critical；本站已自行以上述三處引擎
> 程式與 `ls` 複驗。）

**修訂 4 之後的全域規模（以 `unit-of-work-dependency.md` 的 yaml 邊塊實算，腳本輸出）**：
單元 **24**（既有 17 ＋ 新增 7）、依賴邊 **46**（既有 25 ＋ 本輪新增 21）、**無環**（DFS
三色法）、可平行根 **5**（新增 `progress-channel`，故由 4 增為 5）、層數 **7**（不變）、
完全互相獨立的單元對 **146**。kind 分佈：`spec` 5、`service` 9、`ui` 5、`packaging` 3、
`library` 2。

**24 個單元再次超出本專案既有實務的上界**（實測既有三個 intent 為 5／9／12；本 intent
修訂 1 已是 17）。壓到更少的三個選項（6／5 個新單元）的代價已於 `[UG:G6]` 的選項本文
逐一寫出並由使用者裁決，此處不重述。

## 各新單元的責任、驗證與依賴

### `U18` `project-meta-data`（`spec`，M）

**擁有與交付**：三張新表的 DDL ——`project_members`（`projectId`／`userId`／`role`／
`joinedAt`／`invitedBy`）、`reselection_events`（含 `acknowledgedAt`）、
`system_requirement_fields`（`value` **可為 null** ＋ 獨立的 `clearedAt`，使「從未填過」
＝無列、「清空」＝有列而 `value` 為 null 可區分）＋ `schema_rbac.sql` 與 `DEPLOY.md` 的
**blocking 同步**

**驗證方式**：真實 PostgreSQL CI job ＋ 兩份部署資產的同步檢查

**依賴**：`U4` `hierarchy-data`（`projects`／`systems` 兩表須先存在；FK 的對象）
　**被依賴**：`U19` `membership-service`、`U20` `requirement-field-service`

### `U19` `membership-service`（`service`，L）

**擁有與交付**：邀請（含 `FR12.6a` 的全域權限前置檢查與「拒絕不留半套狀態」）、移出、
角色變更、**自動改選**（最早加入者，平手以 `(joinedAt, userId)` 決定性 tie-break）、
改選稽核的**UI 讀得到的持久層**（`ReselectionEvent`，不是 `logger.info`）、橫幅已讀狀態
（以改選事件識別字為鍵，不是 per-user 布林值）、**per-project 授權判定的唯一來源**、
以及「專案不得失去最後一位管理者」的**共同上游守門**——三條路徑（既有停用端點、
自我降級、自我移出）全部經過同一個判定

**驗證方式**：`TestClient` HTTP ＋ allow/deny 雙向 ＋ 純函式 PBT（挑選邏輯的排列不變性）
＋ 既有停用端點的回應契約測試（含顯式 409 response model）

**依賴**：`U18` `project-meta-data`、`U7` `hierarchy-service`、`U3` `rbac-story-ids`
　**被依賴**：`U20` `requirement-field-service`、`U21` `mcp-bridge`、
`U13` `brain-gateway`、`U24` `member-pages-ui`

### `U20` `requirement-field-service`（`service`，M）

**擁有與交付**：需求欄位的讀寫（按 agent 分組的固定欄位）、清空語意（保留列、
`value` 設 null、記 `clearedAt`）、**未填計數的單一查詢來源**（總覽籤與需求籤讀同一份
結果，不得各發一次請求）、寫入者溯源（`updatedBy` ＋ `updatedOnBehalfOf`）

**驗證方式**：`TestClient` HTTP（含「同一次查詢推導兩處計數」的欄位集合斷言）

**依賴**：`U18` `project-meta-data`、`U7` `hierarchy-service`、`U19` `membership-service`
　**被依賴**：`U21` `mcp-bridge`、`U13` `brain-gateway`、`U23` `project-pages-ui`

### `U21` `mcp-bridge`（`service`，L）

**擁有與交付**：跑**獨立進程**的 MCP server、工具宣告與其 schema 的**憑證欄位白名單**
（宣告允許的欄位集合，其餘皆不得出現；斷言須**排除**根目錄的 `.mcp.json`，那是
AI-DLC 框架自己的 client 設定）、代使用者呼叫既有 API 的 token 轉遞路徑（**不經工具
參數**）、agent 身分與使用者身分的對應（稽核主體必須是使用者本人）

**驗證方式**：工具 schema 的結構斷言（白名單）＋ 代使用者呼叫的 allow/deny 雙向

**依賴**：`U20` `requirement-field-service`、`U19` `membership-service`　**被依賴**：（無）

### `U22` `progress-channel`（`library`，M）

**擁有與交付**：per-request 的進度事件隔離通道**與其清除端**（請求結束即移除該鍵）、
取代 `design_agent.py` 的模組層全域 `_progress_queue`、讀取不存在通道時不崩潰且
**不外洩例外原文**、`wa_collab_orchestrator.py:79` 補傳 per-request 的鍵

**驗證方式**：以 `asyncio.Event` barrier 釘住交錯順序的併發測試（**不得以 `sleep` 製造**
——`playwright.config.ts:17` 與 `ui-regression` 都容忍 flaky，一個 flaky 的併發測試等於
沒有測試）；斷言兩個重疊請求的事件集合**互斥且各自非空**

**依賴**：（無——**本輪新增的唯一可平行根**，它修的是既有程式，不需要任何新東西先落地）
　**被依賴**：`U13` `brain-gateway`、`U12` `work-orchestrator`

### `U23` `project-pages-ui`（`ui`，L）

**擁有與交付**：專案／系統清單頁（首次使用為**空狀態**而非空表）、建立頁、專案詳情頁
的三籤（總覽／需求／記憶摘要）、未填欄位的**文字**標示（不依賴顏色）、儲存失敗時
輸入值不消失

**驗證方式**：Playwright e2e

**依賴**：`U20` `requirement-field-service`、`U7` `hierarchy-service`、
`U8` `memory-service`（記憶摘要籤）、`U3` `rbac-story-ids`（`K4` 的可見性把關）
　**被依賴**：`U17` `a11y-gate`

### `U24` `member-pages-ui`（`ui`，L）

**擁有與交付**：成員頁（清單）、成員詳情頁（角色下拉、`[移出專案]`、變更紀錄）、
邀請對話框（含拒絕態）、**交棒橫幅**——落點為使用者**自己的落地頁**（不限入口頁），
且「知道了」與「查看成員」兩個動作各有定義的效果

**驗證方式**：Playwright e2e

**依賴**：`U19` `membership-service`、`U3` `rbac-story-ids`（`K3` 的可見性把關）
　**被依賴**：`U17` `a11y-gate`

## 既有單元的四處變更（不新增單元，只擴責任或補邊）

| 既有單元 | 變更 | 來源與理由 |
|---|---|---|
| `U3` `rbac-story-ids` | 責任由 `K1`／`K2` **兩個** story id 擴為 **四個**（新增 `K3` 專案成員管理、`K4` 需求欄位）。`role_permissions` 矩陣由 330 增為 **352** 列（11 角色 × 32 story id；此為算式結果，施工時須以 `rbac_seed_data.py` 的實際角色數複算，不得照抄） | `[UG:G8]`=C。上游缺口來自 `[US:V-13]`：`FR12.6a` 的「對應全域功能權限」原本沒有所指，而 `domain-design` 對 `OQ-11`／`OQ-14` 的命中實測為 0（`ADR-004` 只定了 `K1`／`K2`）。**不另開新單元**：story id 的資料擁有者與驗證方式完全相同，另開會讓兩個單元同時改 `rbac_seed_data.py`／`schema_rbac.sql`／`DEPLOY.md` |
| `U2` `brain-ws-contract` | 責任敘述由「**建**一道缺失的閘門」改為「**納入既有**契約」。`:69`／`:215` 的原文保留不回改，於本節就地更正 | `[US:Q-02]`。實測該閘門**已交付**：`ws-contract.json`、`backend/services/brain_ws_contract.py`、`backend/scripts/dump_ws_contract.py`、`backend/tests/test_ws_contract.py`、`backend/tests/test_dump_ws_contract.py`、`frontend/src/types/ws-contract.d.ts` 全部存在，`inception/decisions/0019-ws-contract-gates-and-generator-supply-chain.md` 即 ADR-0019。**此事同時推翻 `delivery-planning` 的既有判定（它當時認定無 WS 機械閘門），依 `[US:Q-02]` 回報下游，本站不改已核可的 `delivery-planning`** |
| `U17` `a11y-gate` | 掃描範圍由入口頁 ＋ `/memory` **兩頁**擴為**四頁**（加專案／系統頁與成員頁）；`depends_on` 補 `project-pages-ui`、`member-pages-ui` | `[US:D-10]`（Critical，轉移至本站）：無障礙清單的範圍表無任何一列涵蓋線框 §15–§18 與 §22–§26。**§27 所在的 `/admin/*` 仍被明文列為「不管」，該判定本站不翻案**——它是已核可的範圍決定，見下方交接事項 `UG-5` |
| `U13` `brain-gateway`、`U12` `work-orchestrator` | 各補邊：`brain-gateway` 補 `membership-service`（取 per-project 角色以決定對外訊息中可用的動作）、`requirement-field-service`（對話中被記下的值寫回）、`progress-channel`（取該請求的進度事件）；`work-orchestrator` 補 `progress-channel`（交辦時建立通道、結束時移除） | `components.md` 的 **Part A''** 機讀邊補充逐條宣告。本站的 yaml 邊塊必須與它一致，否則契約有一端懸空 |

## 實作注意事項（逐新單元，來自上游的硬約束）

| Unit | 注意事項 | 來源 |
|---|---|---|
| `U18` | 三張表觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 **blocking 同步**（未完成不得標示相關 Construction／部署階段為完成）。`system_requirement_fields` 的 DDL 必須讓 `value` 可為 null 並有獨立的 `clearedAt`，否則「從未填過」與「清空」在資料層不可區分。**`[UG:G9]`=A 的後果須寫進 DDL COMMENT**：欄位定義被移除後其值列**保留**、畫面不渲染該組、未填計數只統計當前已宣告的欄位——不寫下來的話，「資料庫裡有、畫面上看不到」的列會被下一個人當成髒資料清掉 | `project.md ## Mandated`、domain-design `DG-9`、`ADR-015`、`[UG:G9]`=A |
| `U18` | `schema_rbac.sql` 只在**空 volume** 執行；既有環境的唯一演進路徑是 `database.py` 的 `_ensure_*` 補丁，而它們**全部吞掉失敗**。三張表的建立若走該路徑，失敗必須**大聲失敗** | `[kb:architecture]` 約束六（同 `U4` 的既有注意事項） |
| `U19` | **守門必須位在三條路徑的共同上游**（既有停用端點、自我降級、自我移出），不是三處各寫一次——`project.md` 的 `functional-design:c34` 記過同形缺陷。三條 AC（`AC12.3.1`–`.3`）在同一單元內一次驗完是本單元存在的理由之一 | `[US:D-06]`（Critical） |
| `U19` | 既有停用端點（`user_router.py:673`）**沒有任何資料庫層 backstop**：它做的是 `target_user.is_active = ...`，一個 **UPDATE**，外鍵對 UPDATE 零效力；而 `schema_rbac.sql` 對 `owner_user_id` 的 COMMENT 逐字為「deletion behaviour ... **deliberately NOT decided**」——那是刻意留的未決項，不是保護。本單元的檢查是**唯一**防線 | `[RA:FR12.5c]`（隔離單站補核已核可） |
| `U19` | 改既有端點的回應契約，而 **CI 的 OpenAPI 漂移閘門對此無效**：實測 `openapi.json` 的 55 個 operation 宣告的狀態碼只有 `{200:53, 422:45, 201:1, 204:1}`，非 2xx/422 的宣告數為 **0**。故 route decorator 必須**顯式**宣告 `responses={409: {...}}`，該契約才會進入 spec 與產生的型別檔 | `[RA:FR12.5b]`、`[US:V-08]` |
| `U19` | 自動改選的挑選函式應為**不讀 DB 的純函式**（輸入成員集合、輸出被選中者）——這是 PBT 能作用的結構前提。真正可失敗的性質是**排列不變性**（`ORDER BY joined_at` 在時間戳相同時沒有穩定順序），不是「同一組輸入選出同一人」那個恆真命題。前例已開檔核對：`backend/cost/estimate_readers.py:247-251` 的 `best_clouds` 用 `key=lambda item: (-item[1], item[0])` | `[US:AC12.4.2]`、`components.md` `ProjectMembership.behaviour` |
| `U19` | 改選稽核**不得只沿用 `user_router.py:213` 的 `_audit_append`**——它寫 `logger.info`，**UI 讀不到**，而 `AC12.2.2` 斷言的是使用者可見的變更紀錄。需要一個可讀的持久層（`ReselectionEvent`） | `[US:Q-11]`（Critical） |
| `U19` | 橫幅已讀狀態**不得做成 per-user 布林值**：同一人第二次被自動改選時就不會再看到橫幅，而那正是 `FR12.4c` 要防的情境。鍵為該次改選事件的識別字 | `[US:共同 DoD]`、`ADR-015` 旁的 `ReselectionEvent.acknowledgedAt` |
| `U19` | 「成功邀請」與「成功移出」必須當成**一級行為**，不是 `FR12.6a` 拒絕條款的反面。上游缺口：`requirements.md` 的 FR12.0–FR12.6b **沒有**它們自己的 FR，`US12.6` 的三條 AC 掛在相鄰的 `FR12.2`／`FR12.5`／`FR12.6` 上。**本注意事項即該缺口指派本站的處置** | `[US:US12.6]` 的指派（`units-generation`，ALWAYS） |
| `U20` | 未填計數的兩處（總覽籤與需求籤）**必須由同一次查詢的結果推導**，不得各發一次請求。e2e 只能驗「兩個數字相等」，驗不出「同一份」——故此項的落點是本單元的端點契約（回應同時帶計數與明細），不是前端 | `[US:V-12]`／`[US:Q-14]`、不變量 `I-4` |
| `U21` | **不得對外暴露，僅供同主機的大腦進程連接**；它是本 intent 的**第二個**新增進程邊界（第一個是 Redis）。傳輸形式（`OQ-16`）與認證機制（`OQ-15`）本站不預選 | `[RA:FR11.4]`、`components.md` `McpBridge.behaviour` |
| `U21` | token 進入 LLM context 是**不可逆**的（會被 LangGraph checkpointer 持久化並出現在任何 `tool_calls` log），故白名單斷言是元件的硬約束而非某一條驗收。斷言須排除根目錄的 `.mcp.json` | `[RA:FR11.5]`／`C-T11`、`[US:V-11]` |
| `U21` | **`A-7`（「MCP 生態可在本 repo 運作」）本 intent 全程未實測**，repo 內零 MCP 基礎設施（`backend/` 對 `mcp` 僅一處命中，是 `user_router.py:85` 的 RBAC story 標籤）。這是本單元能否完成的前提，見交接事項 `UG-1` | domain-design `DG-7` |
| `U22` | **鍵必須是 per-request**，由入口端產生並一路傳遞（`[UG:G7]`=A）。已實測三件事：`agent_router.py:125` 的 `thread_id=f"user-{current_user.id}-design"` 是 **per-user**；`wa_collab_orchestrator.py:79` 呼叫 `run_design_agent(messages, current_xml)` **不傳** `thread_id`，落回 `design_agent.py:174` 的預設 `"default-thread"`；`design_agent.py:198` 的 `config = {"configurable": {"thread_id": thread_id}}` 證實 `thread_id` **就是** LangGraph checkpointer 的 thread 鍵。故**不得**把 `thread_id` 改成 per-request（會關掉對話記憶） | `[UG:G7]`=A、`[US:V-01]`（Critical） |
| `U22` | **形狀沿用 `backend/cost/advice_orchestrator.py:23-24` 的 per-key dict，但不照抄它的 `threading.Lock`**：那支檔案用 Lock 是因為它有 `ThreadPoolExecutor`（`:21` 的 `_executor`），而本單元跑在單執行緒的 asyncio 事件迴圈上——在那裡 `threading.Lock` 是 cargo cult，且會在 `await` 邊界給出錯誤的安全感。注意上游 `stories.md` 的 DoD 寫的路徑前綴 `cost/advice_orchestrator.py` 是錯的，真實路徑為 `backend/cost/advice_orchestrator.py` | `ADR-014`、`application-design:c15` |
| `U22` | `design_agent.py` 的**三個**模組層可變狀態一併清理，已逐一核對：`:31` `_progress_queue`、`:32` `_last_xml`、`:169` `memory = MemorySaver()`。第三個是 LangGraph checkpointer 的模組層單例——它不是外洩路徑，但它使對話記憶綁在單一行程內，改 `thread_id` 語意時必須把它一起看 | `[US:V-04]`／`[US:Q-09]`、本輪開檔核對 |
| `U22` | 對外的錯誤一律為固定訊息、**不含例外原文**。現狀是 `_drain_progress`（`design_agent.py:160`）在 `:163` 對 `None` 呼叫 `get_nowait()` 拋 `AttributeError`，**且該例外原文被送進 SSE 給使用者**——那是獨立的 ADR-0006 面 | `[US:AC13.1.3]`、`ADR-014` |
| `U23`／`U24` | 前端新增資料來源必須走 `AdminPage.tsx` 的兩層抓取形狀（`react-hooks/set-state-in-effect` 為 **error** 級，違反即 CI 紅燈）；沿用 `apiUrl()` 不自造 URL 組裝；載入態與錯誤態須有 live region，**不得**沿用 `AdminPage.tsx:104` 的 4 秒 toast 形狀（無 `role`／`aria-live`） | `team.md ## Code Style`、`[US:D-08]` |
| `U24` | 交棒橫幅須**在落地時即存在於 DOM**，或改用等價的 `role="status"` 機制——`aria-live="polite"` 在其自述前提下不會被朗讀 | `[US:D-11]` |
| `U24` | 橫幅落點是使用者**自己的落地頁**（不限入口頁）。照「入口頁」實作會讓一個只有 `C1 view` 的合法成員**永遠看不到**這則通知，而通知的全部目的就是讓他知道自己成了管理者 | `[RA:FR12.4c]` 的更正、`[US:D-17]`（Critical） |

## 本站收到的九項指派／轉移／回報，逐項處置

| # | 來源與性質 | 處置 |
|---|---|---|
| `OQ-17` | `requirements.md` 指派 `units-generation`，**ALWAYS，不需轉移目標** | **已定案**（`[UG:G7]`=A）：入口端產生 request-scoped 識別字並一路傳遞，與 `thread_id` 並存且語意分離。寫進 `U22` 的注意事項 |
| `DG-4` | `ADR-015` 的 Consequences 段逐字指派 `units-generation`（ALWAYS） | **已定案**（`[UG:G9]`=A）：保留值列、畫面不渲染未宣告的組、未填計數只統計當前已宣告的欄位。寫進 `U18` 的 DDL 約束 |
| `DG-6` | domain-design 指派 `units-generation`（ALWAYS）：`ProgressChannel` 的完成條件橫跨新舊程式 | **已處置**：`U22` 的交付明列「取代 `design_agent.py` 的模組層全域」與「`wa_collab_orchestrator.py:79` 補傳 per-request 的鍵」，並在注意事項列出三個模組層可變狀態的逐一核對結果 |
| `DG-8` | domain-design 指派 `units-generation`（ALWAYS）：上游 `requirements.md` 的 stale 傳遞 | **已結案**：`FR12.0`／`FR12.4c`／`FR12.5b`／`FR12.5c` 四處已於 2026-10-03T00:44:37Z 的隔離單站補核取得正式核可（Summary Authorization Id `51d2bb1f…`，`single: true`、`gate: false`），`FR12.4c` 的落地頁落點**未改變**，故 `ReselectionEvent` 的相關設計不需重審 |
| `[US:D-10]` | `refined-mockups`（CONDITIONAL）→ 轉移 `units-generation`（ALWAYS） | **部分處置**：`U17 a11y-gate` 的掃描範圍由兩頁擴為四頁、`depends_on` 補兩個新 UI 單元。**`/admin/*` 的「不管」判定本站不翻案**，見交接事項 `UG-5` |
| `[US:D-15]` | `domain-design`（CONDITIONAL）→ 轉移 `units-generation`（ALWAYS）：§17 自標的「清除端沒有畫面」 | **已處置**：清除端的**語意**由 `ADR-015` 定案（`U18` 的 DDL ＋ `U20` 的清空端點），**畫面**則確認為真缺口——`U23` 的交付不含「清空欄位」的控件，因為已核可線框 §15–§18 沒有它。列為 `U23` 的 open item，見下方 Assumptions |
| `[US:US12.6]` | `units-generation`（ALWAYS，游標之後）：「成功邀請」與「成功移出」沒有自己的 FR | **已處置**：寫成 `U19` 的注意事項，明訂兩者為一級行為而非拒絕條款的反面 |
| `[US:Q-02]` | 回報下游（不在本站改已核可的 `delivery-planning`） | **已回報**：`U2` 的責任敘述就地更正為「納入既有契約」，並明記此事推翻 `delivery-planning` 當時「無 WS 機械閘門」的判定。見交接事項 `UG-3` |
| `[US:Q-13]` | `units-generation` ＋ `build-and-test`：agent routing 的 PBT 缺口 | **本站的那一半已處置**：`U11 intent-router` 的驗證方式已含「純函式 PBT（門檻判定）」（修訂 1 即有），本輪重申它仍受 `OQ-10`／`OQ-4` 未定案牽制。`build-and-test` 的那一半仍未關閉，見交接事項 `UG-4` |

**逐項對照 18 個 `OQ-<n>` 的結果（依 `units-generation:b0718371` 的要求，不是只寫我剛好想到的那一個）**：
只有 `OQ-17` 落在本站且已定案。`OQ-1`／`OQ-2`／`OQ-9`／`OQ-11`／`OQ-12`／`OQ-14` 的轉移
條件是「`domain-design` 被 skip」，而它**實際已執行並完成**，故六項不轉進本站。
`DG-5`（對話歷史的保存期限與筆數）的轉移條件是「`nfr-requirements` 被 skip」，而它在
本工作流程是 **EXECUTE**（且已為三個單元跑過），故它**留在 `nfr-requirements`**，本站
不假裝接手。仍會讓新單元無法完成的未定項：`OQ-15`／`OQ-16`（`U21` 的認證與傳輸）、
`A-7`（`U21` 的前提）、`OQ-10`／`OQ-4`（既有 `U11`，非本輪新增）。

## ADR-0006 Security Baseline 四面向逐項判定（修訂 4）

承已核可的 `requirements.md:617` 逐字結論「**四面向皆適用，無不適用項**」，本節**不重判
適用性**，只判「本輪七個新單元有沒有新落點」。

| 面向 | 判定 | 本輪新增的落點 |
|---|---|---|
| **IAM** | **適用（本輪最重的一面，四處）** | ① `U3` 擴為四個 story id（`K3`／`K4`），矩陣 330 → 352，須走 `ensure_missing_role_permissions`（不可依賴 `force=False`）並補 allow/deny 雙向 `TestClient`。② `U19` 是 **per-project 授權判定的唯一來源**，判定結論由伺服器產生、前端不得推導；且禁止的是**跳過它直接讀 `project_members` 表**，而 `sync` 入邊是預期且允許的呼叫方式（`ADR-012` 明記此區別）。③ `U19` 的「不得失去最後一位管理者」守門位在三條路徑的共同上游。④ `U21` 每次呼叫以使用者身分受權限檢查，`FR10.2` 禁止同進程繞過 `require_story_action` 的規定仍適用 |
| **Encryption** | **適用（一處）** | `U21` 的工具 schema **不得出現**任何名稱匹配 `token`／`key`／`secret`／`authorization`（不分大小寫）的欄位，且斷言採**白名單**。理由是不可逆——token 一旦進入 LLM context 就會被 LangGraph checkpointer 持久化。傳輸形式的加密要求隨 `OQ-16` 而定（stdio 不過網路；HTTP／SSE 須本機迴環或加密），本站不預選 |
| **Network exposure** | **適用（一處）** | `U21` 是本 intent 的**第二個**新增進程邊界（第一個是 Redis），**不得對外暴露、僅供同主機的大腦進程連接**。暴露範圍**不是**未定項——上游已鎖；未定的只有傳輸形式與認證機制 |
| **Audit logging** | **適用（三處）** | ① `U19` 的自動改選稽核須是 **UI 讀得到的持久層**而非 `logger.info`（`ReselectionEvent`），記誰、何時、對誰、舊角色、新角色。② `U19` 的角色指定同為授權變更，須留同一組欄位。③ `U20` 的清空動作留下 `clearedAt` 與 `updatedBy`，使「誰清」可被稽核。④ `U21` 的工具呼叫稽核主體必須是**使用者本人**而非大腦服務帳號 |

**四面向皆有新落點，無不適用項。**

### Property-based testing hard constraint 的逐項判定（修訂 4）

| 標的 | 判定 | 依據 |
|---|---|---|
| **自動改選的挑選邏輯**（`U19`） | **適用，且本輪是它在單元層第一次有落點** | 可失敗的性質是**排列不變性**而非「同一組輸入選出同一人」（後者對純函式恆真，正是 `user-stories:c4` 警告的形狀）。結構前提：挑選函式須為不讀 DB 的純函式 |
| **未填計數**（`U20`） | **不適用** | 對欄位集合的直接計算，值域不廣到需要生成器；兩處一致性由端點契約的相等斷言承接 |
| **併發隔離**（`U22`） | **不適用（但有不變量）** | 需要併發編排（`asyncio.Event` barrier）而非輸入空間探索 |
| **工具 schema 白名單**（`U21`） | **不適用，但可機械斷言** | 對 schema 的結構斷言，不需產生隨機輸入 |
| **agent routing**（既有 `U11`） | **本輪無新落點，缺口的另一半仍開著** | `U11` 的 PBT 落點（門檻判定純函式）自修訂 1 即在，但它建立在 `OQ-10` 未定案的前提上；`[US:Q-13]` 指派的 `build-and-test` 那一半尚未關閉，見 `UG-4` |

## 修訂 4 的七項送審前自檢逐項結果

| 自檢 | 結果 |
|---|---|
| **1 可達性** | **2 處**。① `U18` 的「清空」態（`value` 為 null 且 `clearedAt` 有值）在 `U20` 的清空端點落地前**不可達**，故 `U23` 的畫面在那之前只會看到「無列」一種未填——兩個單元的完成順序上有此隱含前提（非依賴邊，`U23` 不需等 `U20` 的清空端點才能開工）。② `U24` 的「同一人第二次被改選」情境（`I-6` 要求）需要兩個專案的 owner 先後被停用，可達但需刻意構造，驗證層只能是後端 `TestClient` 而非 Playwright |
| **2 契約端點三問** | **對七個新單元的每個宣告欄位與方法逐一跑，且範圍是全 stage 產出**。三個新實體：`ProjectMember`（寫＝`U19` 的建立專案自動寫入 ＋ 邀請成功／讀＝`U24` 成員頁 ＋ `U19` 授權判定／清＝`U19` 移出專案）；`ReselectionEvent`（寫＝`U19` 自動改選／讀＝`U24` 橫幅與變更紀錄／清＝`acknowledgedAt`，事件列本身不刪，刻意如此）；`SystemRequirementField`（寫＝`U20`，使用者或大腦代 agent／讀＝`U20` 計數 ＋ `U21` MCP ＋ `U23` 畫面／清＝`U20` 的清空端點）。**三個實體的三問全部有答案。** 另：`U22` 的通道（寫＝`U12`／`U13` 建立、讀＝`U13` 串流、**清＝`U22` 自己擁有清除端**）亦三問齊備 |
| **3 引用逐字核對** | **本輪新寫的每一處引用都開檔核對，且分開驗事實與驗定位**。已核對：`agent_router.py:125`（`thread_id=f"user-{current_user.id}-design"`，per-user ✓）、`design_agent.py:31`／`:32`／`:169`（三個模組層可變狀態 ✓，**上游說「三個」是對的**）、`:174`（`thread_id: str = "default-thread"` ✓）、`:198`（`config = {"configurable": {"thread_id": thread_id}}` ✓）、`:160`／`:163`（`_drain_progress` 與 `get_nowait()` ✓）、`wa_collab_orchestrator.py:79`（`run_design_agent(messages, current_xml)`，**確實不傳** `thread_id` ✓）、`backend/cost/advice_orchestrator.py:23-24`（per-key dict ＋ `threading.Lock` ✓，且 `:21` 確有 `_executor` ✓）、`backend/cost/estimate_readers.py:247-251`（`key=lambda item: (-item[1], item[0])` ✓）、`openapi.json` 的 55 個 operation 與狀態碼分佈 `{200:53, 422:45, 201:1, 204:1}`（以 Python 解析實算 ✓）、`user_router.py:673`（`target_user.is_active = request.is_active`，UPDATE ✓）。**一處上游引用確認為錯並就地標註**：`stories.md` 的 US13 DoD 寫 `cost/advice_orchestrator.py:23-24`，真實路徑為 `backend/cost/advice_orchestrator.py`（行號與內容正確，只有路徑前綴錯） |
| **4 檔案集合一致性** | 四份產出齊備並全部更新（`unit-of-work.md`／`unit-of-work-dependency.md`／`unit-of-work-story-map.md`／`traceability.json`）；問題檔亦同步 |
| **5 跨檔傳播** | 本輪改動的**事實**（非字串）逐一以其多種表達形式查證：單元總數（17 → 24）、邊數（25 → 46）、可平行根（4 → 5）、kind 分佈、故事覆蓋（20 → 31）、`U3` 的 story id 數（2 → 4）、矩陣列數（330 → 352）、`U17` 的掃描頁數（2 → 4）。**舊數字的反向 grep 逐處判定**：Plan Approval 區與修訂 1–3 的敘述中的舊數字為**合法的歷史紀錄**（當時據以核可的計畫），依修訂 3 已立的慣例**不改**，只在本節聲明現行數字以 yaml 邊塊為準 |
| **6 可算的數字先算再寫** | **全部由單一腳本從 yaml 邊塊的同一份資料結構輸出**，不是手寫後再核對：單元 24、邊 46（其中觸及新單元 21）、無環（DFS 三色法）、可平行根 5、層數 7、完全獨立對 146、kind `spec` 5／`service` 9／`ui` 5／`packaging` 3／`library` 2。**腳本是收尾動作**（在最後一個單元與最後一條邊寫定之後才跑），這是修訂 1 的 `R-10` 與 user-stories 的 `R-07` 同形失誤的補強 |
| **7 ADR-0006 ＋ PBT 逐項對照** | 見上方兩節。**本輪刻意不重判適用性**（`requirements.md:617` 已定四面向皆適用），只判新落點：IAM 四處、Encryption 一處、Network exposure 一處、Audit logging 三處；PBT 的唯一新適用標的是自動改選的挑選邏輯。**填表時逐格比對上游同名表格的判定欄**，無一格與上游相反——這是 user-stories 的 `R-02`／`R-03` 記下的失誤形狀（表格的存在本身就是「已檢查過」的訊號，一個與上游相反的判定會把這道檢查反過來用） |

## 修訂 4 的交接事項

| # | 事項 | 承接站 | execution |
|---|---|---|---|
| UG-1 | **`A-7`（MCP 生態可在本 repo 運作）仍未實測**，而它是 `U21 mcp-bridge` 能否完成的前提：repo 內零 MCP 基礎設施。承 domain-design `DG-7` | `contract-design`（2.8，CONDITIONAL）→ 轉移 `code-generation`（3.5，**ALWAYS**） | — |
| UG-2 | **`U18` 的三張表 ＋ `U3` 的 seed 語意變更，各自觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步，兩者不可互相替代**。承 domain-design `DG-9` | `code-generation`（3.5） | **ALWAYS** |
| UG-3 | **`delivery-planning` 的既有判定需重審**：它當時認定「無 WS 機械閘門」，而該閘門已交付（ADR-0019）。本站不改已核可的 `delivery-planning`，依 `[US:Q-02]` 回報 | `delivery-planning`（2.9） | **ALWAYS**（游標之後） |
| UG-4 | **`[US:Q-13]` 的另一半未關閉**：agent routing 的 PBT 在 `build-and-test` 的落點尚未指定 | `build-and-test`（3.6） | **ALWAYS** |
| UG-5 | **`/admin/*` 不納入 axe 閘門的判定須重審**：`[US:D-10]` 指出線框 §27（停用帳號的前置檢查畫面）落在 `/admin/*`，而該路徑被明文列為「不管」。本站只擴到四頁，不翻案已核可的範圍決定 | `refined-mockups`（2.5，CONDITIONAL）→ 轉移 `code-generation`（3.5，**ALWAYS**） | — |
| UG-6 | **`OQ-15`（MCP server 怎麼認證到既有 API）與 `OQ-16`（傳輸形式）未定**，兩者決定 `U21` 的完成條件與 Encryption 面的實際要求 | `OQ-15`：`contract-design`（2.8，CONDITIONAL）→ `code-generation`（ALWAYS）；`OQ-16`：`infrastructure-design`（3.4，CONDITIONAL）→ `code-generation`（ALWAYS） | — |
| UG-7 | **upstream stage 檔與引擎對 construction 目錄命名法不一致**：`units-generation.md:96` 要求 `u{n}-{description}`，而引擎三處（`aidlc-lib.ts:10032-10033`、`aidlc-orchestrate.ts:2118`／`:2617`、`aidlc-swarm.ts:746`／`:788`）與磁碟現況都用**裸單元名**。本站已以引擎為準修正 91 處引用，但**那一行 upstream 文字仍然錯著**，下一個 intent 會再踩一次。依 `project.md`，不得直接改 `.claude/` 下的 upstream 檔；正確處置是把這個不一致記進規則層或提給 upstream | 規則層（`aidlc/spaces/default/memory/project.md`，本站的學習儀式即寫入點） | — |

## 修訂 4 的 Assumptions & Open Questions

- 新單元的複雜度欄（S／M／L）同為**相對估計**，無工時基礎；`XL` 仍未使用 [assumption]
- `U23` 的「記憶摘要籤」依賴 `U8 memory-service`，但 `US11.1`–`US11.4` **沒有任何一條 AC
  涵蓋該籤的行為**——它的來源是 `FR11` 前言承的 `[S12]`=A 四項責任之一與線框的三籤結構。
  本站如實列出該依賴，但該籤的驗收面在上游是薄的 [assumption]
- **`[US:D-15]` 的畫面缺口確認為真**：清空需求欄位的**控件**在已核可線框 §15–§18 中不存在，
  故 `U23` 的交付不含它。清空的**語意**與**端點**已由 `ADR-015` 與 `U20` 承載，缺的只有
  使用者怎麼觸發它。本站不自行補畫面（那會擅自擴大已核可的 UI 範圍） [assumption]
- `U21` 的部署模型是本 intent 第二個 `standalone`（第一個是 `U9 memory-purge` 的 GitHub
  Actions workflow），但兩者性質不同：`U9` 跑在 GitHub 的 runner 上，`U21` 跑在**同一台
  staging 主機**上。`U1 brain-infra` 是否需要為它新增第七個 compose 服務，屬
  `infrastructure-design` 的範圍，本站不定 [assumption]
- 24 個單元的跨單元契約數量（**46 條邊**）未逐條展開為契約規格；那是
  `contract-design`（2.8，CONDITIONAL）的工作 [assumption]
