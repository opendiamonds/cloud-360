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
| `U1` | `brain-infra` | `construction/u1-brain-infra/` | `packaging` | S | embedded（compose 服務定義；非程式碼） |
| `U2` | `brain-ws-contract` | `construction/u2-brain-ws-contract/` | `spec` | S | embedded（就地消費的型別來源 ＋ CI 檢查） |
| `U3` | `rbac-story-ids` | `construction/u3-rbac-story-ids/` | `spec` | S | embedded（seed ＋ SQL） |
| `U4` | `hierarchy-data` | `construction/u4-hierarchy-data/` | `spec` | M | embedded（DDL ＋ 一次性遷移程序） |
| `U5` | `memory-data` | `construction/u5-memory-data/` | `spec` | M | embedded（獨立 schema ＋ grant） |
| `U6` | `embedding-port` | `construction/u6-embedding-port/` | `library` | M | embedded（library，無獨立執行期） |
| `U7` | `hierarchy-service` | `construction/u7-hierarchy-service/` | `service` | M | embedded（同一 FastAPI process 的新 router） |
| `U8` | `memory-service` | `construction/u8-memory-service/` | `service` | L | embedded（同一 FastAPI process 的新 router） |
| `U9` | `memory-purge` | `construction/u9-memory-purge/` | `packaging` | S | standalone（GitHub Actions workflow，不在 FastAPI process 內） |
| `U10` | `session-store` | `construction/u10-session-store/` | `service` | M | embedded（同一 process；狀態外部化於 Redis） |
| `U11` | `intent-router` | `construction/u11-intent-router/` | `service` | L | embedded（同一 process） |
| `U12` | `work-orchestrator` | `construction/u12-work-orchestrator/` | `service` | L | embedded（同一 process） |
| `U13` | `brain-gateway` | `construction/u13-brain-gateway/` | `service` | M | embedded（同一 process 的 WebSocket route） |
| `U14` | `entry-page-ui` | `construction/u14-entry-page-ui/` | `ui` | L | embedded（同一 SPA bundle） |
| `U15` | `memory-page-ui` | `construction/u15-memory-page-ui/` | `ui` | M | embedded（同一 SPA bundle） |
| `U16` | `object-picker-ui` | `construction/u16-object-picker-ui/` | `ui` | M | embedded（同一 SPA bundle） |
| `U17` | `a11y-gate` | `construction/u17-a11y-gate/` | `packaging` | S | standalone（CI 步驟 ＋ devDependency） |

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
