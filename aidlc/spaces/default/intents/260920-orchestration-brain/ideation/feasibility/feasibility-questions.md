# Feasibility & Constraints — 問題檔

本檔為 `feasibility` 階段的正式決策紀錄。所有 `[Answer]:` 由使用者填答，
AI 不得代答。回答格式為選項字母（可複選者以逗號分隔），或 `X` 並附文字說明。

## 適用性判定（CONDITIONAL stage）

本 stage 的 condition 為「Execute when there are integration constraints,
regulatory requirements, or significant technical uncertainty」。逐項判定：

| 條款 | 判定 | 依據 |
|---|---|---|
| 整合約束 | **成立** | 須銜接既有 agent 端點、既有 LLM provider 切換層、既有 auth／RBAC，並在既有 `user_diagrams` 之上疊「專案 → 系統」階層（上游 [Q5]=B） |
| 法規要求 | **部分成立** | episodic memory 為 by-user 的對話紀錄，有保存期與刪除的隱私面；但僅限自有 staging，無外部法規框架 |
| 顯著技術不確定性 | **成立** | LangGraph 與 Redis 在 repo 內引用為 0（S6）；三種記憶、推播皆無前例 |

三款有兩款明確成立 → 本 stage **EXECUTE**。

> **修訂 1 註（依 `functional-design:c22`：理由部分被推翻但判定不變）**：
> 上表「顯著技術不確定性」列所引的「LangGraph 引用為 0（S6）」對 LangGraph
> 已不成立（見 V8：已釘選並在部署環境運行）。**但本 stage 的 EXECUTE 判定
> 不受影響**——Redis 仍為 0（V9），三種記憶、推播、專案／系統階層亦皆無
> 前例，且「整合約束」一款獨立成立。原文不改，就地標註。

## 已由上游定案、本站不重問

依 `scope-definition:260822-c5`，每一項都附可引用的定案原文：

- **作業對象的綁定層級** — intent-capture [Q5]=B：「本次一併建立專案／系統
  階層：把『專案 → 系統 → 架構圖』做成正式資料模型，大腦綁到這三層。」
- **編排對象與成本能力範圍** — [Q12]=A：「編排既有的真實成本 agent：大腦把
  成本類問題路由到既有 `/api/cost/v1`，使用者真的問得到成本答案；不新建成本
  能力。」＋ [Q14]=A：「就地在入口頁呈現：大腦把成本 agent 的串流轉送到
  入口頁，使用者不離開入口頁就看到答案。」
  （修訂 1：本項原引用 [Q6]=C「成本 agent 的空殼」＋ [Q11]=B「空殼回
  『尚未提供』」。兩題的前提「成本能力不存在」已被推翻，上游已標示 Q6／Q11
  由 Q12 取代，故本清單改引用 Q12／Q14。）
- **編排執行層的落位** — [Q13]=B：「大腦自建獨立 runtime：大腦有自己的
  LangGraph 執行層，與成本 agent 那份並行、互不影響。」（修訂 1 新增；
  既有 `services/langgraph_runtime.py` 於出題當時尚未被本 intent 查證到。）
- **共享工作階段的涵蓋頁面** — [Q7]=A：「只有入口頁 ＋ `/workspace` ＋
  `/assessment`：實際會用到 AI 的頁面。」
- **決策者與組織阻礙** — [Q8]=A：「單一決策者（你），無其他關係人：範圍、
  優先順序、驗收皆由你決定，不需要對外回報節奏。」→ 故本站省略「組織阻礙
  （change freeze、競爭優先序）」一題。
- **成功指標的三個維度** — [Q3]=A,B,C（意圖識別準確率、跨頁面上下文保留率、
  首字回應時間）。**門檻值**未定，故本站以 F7 詢問它該在哪一站定案。

另依 `feasibility:c2` 省略 stage 檔範例題「What AWS services and accounts
are currently in use?」：本 repo 部署目標只有自有 staging（ADR-0007），
雲端供應商 production 環境與 credentials 由 ADR-0001／0002 排除在範圍外。

## Sources

出題前的唯讀查證結果。依 `feasibility:c4`，本站的查證結果登錄於此供題幹與
選項引用（此規則為 feasibility 專屬，與 intent-capture 的 register 限制並存
而不互相取代）。

- [S1] `deploy/docker-compose.deploy.yml` 的部署拓樸現為 **4 個服務**：
  `db`（`postgres:16-alpine`）、`backend`、`frontend`、`cloudflared`，
  外加具名 volume `cloud360_db`。
- [S2] `backend/requirements.txt` 共 12 行依賴。其中 `fastapi[standard]` 與
  `pydantic` **精確釘選**（`==0.141.1`、`==2.13.4`），檔內註解載明理由：
  OpenAPI 規格輸出在同版本下位元決定性、跨版本會飄，不釘會讓規格漂移檢查
  在無關 PR 上變紅。其餘 10 項（含 `claude-agent-sdk`）未 pin。
- [S3] **SSE 串流已經存在**：`backend/services/agent_router.py` 有 3 處
  `StreamingResponse(..., media_type="text/event-stream")`，檔頭並載明
  「response: text/event-stream，data 為 JSON {type, content}」的既有契約。
- [S4] **WebSocket 也已經存在**：`backend/services/collab_router.py` 用於
  架構圖共編。
- [S5] **端點變更會連動兩道機械檢查**：CI（`.github/workflows/ci.yml`）含
  `openapi.json` 漂移檢查；前端型別由 `npm run gen:types`
  （`openapi-typescript@7.13.0`）從 `openapi.json` 產生 `src/types/api.d.ts`。
  新增端點須在同一個 PR 內重產兩者。
- [S6] **Redis 在 repo 內只作為「架構圖詞彙」出現**（`wa_rule_engine.py`、
  `wa_lens_engine.py`、AWS 架構提示詞中的 ElastiCache/Redis 服務名），
  不存在任何執行期依賴、容器或設定。LangGraph 引用為 0。
  **（修訂 1 更正：Redis 半邊仍成立 [V9]；LangGraph 半邊已不成立——
  `langgraph==1.2.11` 已釘選且 `services/langgraph_runtime.py` 在用 [V8]。
  原文保留，因為它記載的是出題當時為真的事實。）**
- [S7] CI 的 Python 版本為 `3.12`（另有一處 `3.x`）。
- [S9] **pgvector 不在現用映像內**：`db` 服務為官方 `postgres:16-alpine`，
  不含 pgvector；repo 內無任何 `CREATE EXTENSION` 或向量欄位。語意記憶若要
  向量檢索，須換映像（如 `pgvector/pgvector:pg16`）或自建映像安裝 extension
  ——屬拓樸層變更。
- [S10] **`schema_rbac.sql` 是 init script，只在空的 data volume 上執行**
  （`docker-entrypoint-initdb.d/01-schema_rbac.sql`，唯讀掛載）。既有 staging
  的 volume 非空，故新增 extension 與資料表在既有環境上需要明確的手動遷移
  步驟。
- [S8] `project.md ## Mandated` 有一條 **blocking** 規則：新增 compose 消費
  的變數時，同一個 PR 必須讓 `deploy/render-env.sh` 寫它、
  `deploy/.env.example` 列它；失敗模式是無聲的（缺值變空字串，服務照常啟動
  但功能降級）。另一條 blocking 規則要求資料庫結構變更時
  `schema_rbac.sql` 與 `DEPLOY.md` 必須同步。

---

## F1. 模型路由要正式定案為哪一組？

你在對話中說過「本機用 Claude Code CLI 的 Claude Sonnet、伺服器用 OpenRouter
的 `google/gemini-3.7-flash`」，但這個決定**從未進入任何問題檔**，因此下游
無法引用。本題把它正式記錄下來。既有的 `llm_provider.py` 已有
openrouter／cli 雙模式切換（預設 openrouter）。

- A. **沿用既有切換層，兩種模式如你所述**：本機 cli 模式走 Claude Code CLI 的
  Sonnet；伺服器 openrouter 模式走 `google/gemini-3.7-flash`。大腦與既有功能
  共用同一個 provider 層。
- B. **沿用切換層，但大腦要能獨立指定模型**：編排層（意圖識別）與功能 agent
  （產圖、檢視）可以用不同模型，例如編排用便宜快速的、產圖用強的。
- C. **大腦自建獨立的模型存取路徑**，不走既有 `llm_provider.py`。
- D. 尚未定義——需要先討論再決定。
- X. Other（請說明）

[Answer]: B  <!-- 2026-09-21T01:59:43Z | Mode: guided -->

## F2. Redis 要以什麼形式進入部署？

目前部署拓樸只有 4 個服務（S1），沒有任何快取或佇列元件（S6）。新增 Redis
會是拓樸變更，並觸發 [S8] 的 blocking 規則（`render-env.sh` ＋
`.env.example` 必須同批更新）。

- A. **新增第 5 個容器**：在 `docker-compose.deploy.yml` 加一個 Redis 服務，
  與既有四個並列。最直觀，但多一個要維運的元件與一組新的連線設定。
- B. **不引入 Redis，session 層改用既有 PostgreSQL**：少一個元件、少一組設定，
  代價是失去 Redis 的過期機制與低延遲特性，session 讀寫會與業務資料共用同
  一個資料庫。
- C. **用外部託管的 Redis**（雲端服務）：不動部署拓樸，但會引入對外網路依賴
  與一組新憑證，且需確認是否牴觸「production credentials 不進版控」的邊界。
- D. 尚未定義——需要先評估再決定。
- X. Other（請說明）

[Answer]: A  <!-- 2026-09-21T01:59:43Z | Mode: guided -->

## F3. 三種記憶（semantic／procedure／episodic）放哪裡？

> **選項修訂（2026-09-21T01:59:43Z）**：初版的 B 把「獨立 schema」與「獨立資料庫」寫成同一個
> 選項，但兩者在使用者追問的那個軸上效果相反——**PostgreSQL 不支援跨
> database 查詢**（需 `postgres_fdw`／`dblink`），故「獨立資料庫」會傷害
> hybrid search 與 context 共享，而「同 database、獨立 schema」完全保留
> join 能力。本題據此把 B 拆為 B 與 C，原 C（獨立 Postgres 服務）併入新 C
> 的說明中作為同型後果，並新增 [S9]／[S10] 兩項查證事實。

你指定用 PostgreSQL。既有部署已有一個 `postgres:16-alpine` 服務與
`cloud360_db` volume（S1）。追問已釐清：真正的取捨軸是**授權邊界**與
**跨層 join 能力**，不是物理上拆不拆。

- A. **全部放既有 cloud360 資料庫的同一個 schema**：新增資料表即可。join
  能力最完整，但未來任何要用記憶層的服務，其憑證同時也構得到 `users`、
  `role_permissions`、`user_diagrams`。
- B. **同一個 database，獨立 schema**：跨 schema join 為原生（可直接做
  「只搜這個專案的記憶」這類混合查詢），同時能只把記憶 schema 的權限授予
  未來的其他 AI 服務。不新增容器。
- C. **獨立 database 或獨立 Postgres 服務**：隔離最強，但 **PostgreSQL 不支援
  跨 database 查詢**，hybrid search 與 context 共享都要改走 `postgres_fdw`
  或應用層合併；獨立服務還多一個容器。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: B  <!-- 2026-09-21T02:31:17Z | Mode: guided | 使用者原文：「希望在同一Database，而且可以存取DB的權限控制在記憶層的Schema，但介接的應用系統可以自定義使用者角色對應來管理自身權限」；經回讀確認儲存機制即 B，授權分工另立 F9 -->

## F4. 「串流架構，做到快速回覆」要用哪一種機制？

查證發現**串流已經存在**：既有 3 個端點以 SSE（`text/event-stream`）回應，
且有明文契約 `{type, content}`（S3）；架構圖共編另有 WebSocket（S4）。

- A. **沿用既有 SSE 契約**：大腦的回覆走同一種格式，前端既有的處理方式可
  重用。代價：SSE 是單向的，若大腦需要在同一條連線接收前端訊息會不夠用。
- B. **改用 WebSocket**：雙向，可承載「主動通知推播」。代價：與既有 3 個
  SSE 端點形成兩種並存的串流機制。
- C. **兩者並用**：回覆走 SSE，主動推播走 WebSocket（或反之）。
- D. 尚未定義——留給設計階段決定。
- X. Other（請說明）

[Answer]: B  <!-- 2026-09-21T01:59:43Z | Mode: guided -->

## F5. episodic memory 是 by-user 的對話紀錄——保存與刪除要求為何？

這是本 intent 唯一碰到隱私面的部分：系統會長期保存每位使用者的對話歷程。
本 repo 只部署到自有 staging，無外部法規框架適用，但保存期與刪除能力仍是
必須定的設計約束。

- A. **無限期保存，不提供刪除**：最簡單，但使用者無法要求清除自己的紀錄。
- B. **設定保存期限，逾期自動刪除**（期限值於後續階段定案）。
- C. **保存期限 ＋ 使用者可自行刪除自己的記憶**。
- D. 尚未定義——需要先討論再決定。
- X. Other（請說明）

[Answer]: C  <!-- 2026-09-21T02:09:48Z | Mode: guided -->

## F6. 技術不確定性最大的一塊是哪個？要不要先做 spike？

LangGraph 與 Redis 在 repo 內完全沒有前例（S6），三種記憶與推播亦然。
`phases/ideation.md` 要求可行性評估必須保守並明確標示假設。

> **修訂 1 註**：本題幹的「LangGraph 完全沒有前例」已不成立 [V8]，故其
> 選項 A 所述的試探已被 repo 內的可運行前例部分回答。**F6 的作答不改**
> （試探仍要做），但該試探的範圍已在 `feasibility-assessment.md` 的驗證
> 計畫表中收窄為本 intent 獨有的部分：多意圖分支結構、session 注入、
> 以及自建 runtime [Q13] 與既有那份的一致性。

- A. **LangGraph 的編排模型**：它能不能乾淨地包住既有那些以 SSE 回應的
  agent 端點，是整個架構的地基。建議先做 spike。
- B. **記憶層的資料模型**：三種記憶各自的形狀與查詢方式，直接決定資料庫設計。
  建議先做 spike。
- C. **專案／系統階層對既有資料的遷移**：既有架構圖直接掛在使用者底下，
  要怎麼歸屬到新階層而不破壞既有頁面。建議先做 spike。
- D. **不需要 spike**：直接進設計階段，不確定性在設計時解決。
- X. Other（請說明；可指出多個）

[Answer]: A, B  <!-- 2026-09-21T02:31:17Z | Mode: guided | 使用者原文：「1、2」，對應顯示順序第 1、2 項（LangGraph 編排模型、記憶層資料模型）；題幹 X 已明示可點名多項 -->

## F7. 三個成功指標的門檻值要在哪一站定案？

上游 [Q3] 已定下三個維度（意圖識別準確率、跨頁面上下文保留率、首字回應
時間），但門檻值全部留待後續。審查者的 R-04 指出：零起始錨點會讓下游從頭
議定。

- A. **在本站（feasibility）定**：由可行性評估一併給出可達成的數值範圍。
- B. **留到 requirements-analysis**：那一站本來就在寫可驗收的需求。
- C. **留到 nfr-requirements**：首字回應時間本質是效能 NFR，三項一起放那裡。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: B  <!-- 2026-09-21T02:09:48Z | Mode: guided -->

## F8. 有時程或預算上的約束嗎？

- A. **沒有硬性時程，也沒有預算上限**：做到對為止。
- B. **有目標時程**（請在 X 說明日期或期間與它的硬度：是期望還是死線）。
- C. **有預算或成本上限**（例如 LLM 呼叫的月費上限；請在 X 說明）。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: C  <!-- 2026-09-21T02:34:42Z | Mode: guided -->

## F9. 記憶層的授權模型：DB grant 與應用層授權的分工

本題來自 F3 的追問回覆。使用者描述的儲存機制即 F3 的 B（同一個 database、
獨立 schema），但另外加了一條 B 的敘述未涵蓋的約束，故獨立成題正式記錄：
**資料庫層的存取權限只鎖到記憶 schema，而「哪個使用者能看哪些記憶」這種
應用層授權，由各個介接的應用系統以自己的角色對應管理。**

這決定記憶層本身要不要內建一套權限模型。

- A. **記憶層不內建權限模型**：DB grant 鎖到 schema 即為全部邊界；記憶列上
  只帶識別欄位（如 user id、專案 id），由呼叫端自行過濾。介接的應用系統各自
  用自己的角色對應決定誰看得到什麼。
- B. **記憶層內建最小權限模型**：記憶列帶擁有者與可見範圍欄位，讀取一律經過
  記憶層的檢查，應用系統的角色對應映射到這組欄位。
- C. **沿用 Cloud-360 既有的 RBAC**：記憶層直接查既有 `role_permissions`
  決定可見性。代價：記憶層與 Cloud-360 的權限模型綁死，未來其他應用系統
  要接就得先接受這套 RBAC。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: B  <!-- 2026-09-21T02:31:17Z | Mode: guided -->


## F10. 既有資料遷到新階層這一塊，沒有任何驗證手段——怎麼處理？

本題來自答案收齊後的**覆蓋檢查**（非矛盾偵測）：把已定案的驗證計畫逐條對照
最高風險失敗模式，發現兩者有一處零交集。

- 上游 [Q5]=B 已把「建立專案 → 系統 → 架構圖 階層」變成第一級範圍項。
- [S10] 指出 `schema_rbac.sql` 是 init script，**只在空的 data volume 上執行**，
  既有 staging 的 volume 非空，故遷移必須手動。
- F6 選了 LangGraph 編排模型與記憶層資料模型兩個試探，**未含**既有資料遷移。

也就是說，這一塊目前既沒有試探、也沒有其他驗證計畫涵蓋它。

- A. **遷移風險交給設計階段處理**：不做試探，但要求 application-design 或
  functional-design 明確產出遷移步驟與回復方式。
- B. **加做第三個試探**：先用既有 staging 的資料副本在本機試跑一次遷移，
  確認既有架構圖能正確歸屬且既有頁面不壞。
- C. **避開遷移**：新階層只套用於新建資料，既有架構圖維持原樣（不歸屬到任何
  專案／系統），由使用者自行決定要不要搬。代價：系統內會同時存在兩種資料形狀。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: A  <!-- 2026-09-21T02:34:42Z | Mode: guided -->


## F11. 成本上限的形狀為何？

F8 選了「有預算或成本上限」但未說明數值。依 stage-protocol §3 的答案分析，
沒有形狀的上限無法驅動任何設計決定——它直接影響 F1=B（大腦可獨立指定模型）
實際要怎麼選模型，也影響記憶層要不要為了省 token 而做摘要壓縮。

- A. **硬性月費上限，有明確數字**（請在 X 寫出金額與計價單位）。
- B. **沒有硬數字，但原則是「盡量省」**：編排層一律選便宜快速的模型，
  昂貴模型只用在真正需要的地方（產圖、深度檢視）。
- C. **先記為已知約束、數值留到 requirements-analysis 定**（與 F7 的三個
  指標門檻同一站處理）。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: B  <!-- 2026-09-21T02:41:54Z | Mode: guided -->

> **作答更正（2026-09-21T02:41:54Z）**：本題先前被寫成 `[Answer]: C`，那是**轉錄錯誤**，不是
> 使用者的選擇。提問時選項順序與本檔不同（提問順序為 B→C→A→D），寫回時
> 依位置而非依內容對應，遂把使用者實選的 A（硬性月費上限，有明確數字）誤記為
> C（數值留到 requirements-analysis 定）。此即 `requirements-analysis:260822-ra-c2`
> 警告的形狀：同一個字母在兩份紀錄中指向不同內容。使用者隨後改選 **B**
> （沒有硬數字，原則是盡量省），故最終答案為 B。F13=A 與本題的銜接為：
> 成本上限由 OpenRouter 後台承載（本專案不記錄其數值），本 intent 內以
> 「盡量省」作為設計原則，兩者不衝突。



## F12. 硬性月費上限是多少？

F11 選了「硬性月費上限，有明確數字」但未附數值。沒有數字的話，約束登記表
只能寫「有上限但不知道是多少」，下游無從據以算出每次對話的 token 預算，
這比記為「未定」更糟——它看起來像已定案。

- A. 每月 **USD 50 以內**
- B. 每月 **USD 50–200**
- C. 每月 **USD 200–1000**
- D. 我要直接寫確切金額或改用別的計價單位（請用 X 寫出）
- X. Other（請說明；寫出金額與計價單位，例如「每月 USD 120」或「每月 TWD 3000」）

[Answer]: —（本題已由 F13 取代，不作答）

> **本題由 F13 取代（2026-09-21T02:39:59Z）**：使用者以 Other 回覆「用系統admin功能去設定」，
> 這使本題的前提（上限是一個現在要記下的固定數字）不成立——它描述的是一項
> **系統能力**而非一個約束值。依 `application-design:260822-ad-L3`（使用者的
> 回覆若是重新框定而非選項之一，先查證再決定採納或追問），已查證後改以 F13
> 詢問真正的決策點。本題 `[Answer]:` 維持空白。


## F13. 「成本上限由系統 admin 設定」——這項能力要不要做？

本題取代 F12。使用者的回覆是「用系統admin功能去設定」，查證後發現三件事：

- [S11] `backend/services/llm_limits.py` **管的是單次請求的 token 上限**
  （`get_llm_max_output_tokens`、`get_xml_context_max_chars`、
  `truncate_text_for_llm`），值來自環境變數（`LLM_MAX_OUTPUT_TOKENS` 等），
  **不是花費上限，也沒有任何 admin 介面**。
- [S12] `backend/services/user_router.py` 的管理端點全為使用者與角色相關
  （`/list`、`/roles`、`/authorization-requests/*`、`/{user_id}/active`、
  `/{user_id}/role`）；**repo 內不存在任何設定類端點**。「系統 admin 功能」
  目前不存在。
- [S13] **強制月費上限的前提是系統會計量花費**。而上游 [Q6]=C 與 [Q11]=B
  已定案「成本／FinOps 能力只做交接介面的空殼，不實作真正的成本計算」。
  兩者不能同時成立——這是一個跨階段矛盾，不是細節。

  > **修訂 1 註（依 `functional-design:c22`：理由被推翻但決定不變，原文不改
  > 只就地標註）。適用範圍為 F13 全題——本條 [S13] 以及下方選項 A、B 中每一
  > 處 [Q6]=C／[Q11]=B 的引用**：這些引用已由 [Q12]=A 取代，成本能力
  > 確實存在。**但 F13 的決定不受影響**，因為兩者談的不是同一種成本：
  > `backend/cost/` 計的是**使用者雲端架構的估價**，本系統仍然沒有任何
  > 「自身 LLM 花費」的計量機制（`llm_limits.py` 管的是單次請求的 token
  > 上限，非花費）。故「強制月費上限的前提不成立」這個結論原樣成立，
  > F13=A（上限改由 OpenRouter 後台承載）維持不變。不得因為「成本能力已
  > 存在」就推論本系統能計量自身花費——這正是本註記要防的誤讀。

此外，「admin 可設定的成本上限」不在 intent-capture 已核可的能力清單內。

- A. **上限不由本系統承載**：改在 OpenRouter 後台設定支出上限。本 intent 不做
  任何成本計量或 admin 設定，僅把「外部已設有成本上限」記入約束登記表。
  範圍不變，與 [Q6]=C／[Q11]=B 不衝突。
- B. **本 intent 要做**：admin 可設定並由系統強制的成本上限。這需要成本計量，
  與 [Q6]=C／[Q11]=B 直接矛盾，且超出 intent-capture 已核可的範圍。依
  `scope-definition:rev1-c4`，必須先回跳 intent-capture 以 Modify 模式擴充
  範圍、重走該站核可關卡，才能在本站產出。
- C. **列為未來能力，本 intent 不做**：成本控制在本 intent 只以設計原則承載
  （編排層用便宜模型、記憶層做摘要壓縮），不做可設定的上限。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: A  <!-- 2026-09-21T02:41:14Z | Mode: guided -->

## 修訂 1 的查證更新（2026-09-21）

上游 intent-capture 以 Modify 模式修訂後（Q12=A 編排既有的真實成本 agent、
Q13=B 大腦自建獨立 runtime、Q14=A 成本答案就地在入口頁呈現），本站以
Modify 模式重新開啟。下列查證於 2026-09-21 對本分支工作樹重跑：

- V-F1 — **成本 agent 的回覆是非同步 job，其「串流」是狀態輪詢而非 token
  串流**。`backend/cost/advice_orchestrator.py` 以 `ThreadPoolExecutor`
  排程（`enqueue_advice_job`／`_job`），狀態機含 `generating`；
  `backend/cost/advice_stream_router.py` 每 1 秒（`asyncio.sleep(1.0)`）
  查 DB，送出的事件型別為 `progress`／`completed`／`timeout`／`failed`／
  `heartbeat`。取得方式：實讀兩支模組。
- V-F2 — **成本端點的授權是 FastAPI dependency**：
  `advice_stream_router.py:165` 為 `Depends(require_story_action("C1","view"))`，
  `estimate_intake_router.py:52` 為 `Depends(require_story_action("C1","edit"))`。
  另有 `estimate_audit_events` 稽核表（`schema_rbac.sql`／`backend/models.py`）。
  取得方式：實讀 router 與 models。
- V-F3 — **C-T9 重查**：`/api/cost/v1` 的 10 條端點中無設定類端點
  （`settings`／`config`／`budget` 在 `backend/cost/` 的 router 層 0 命中），
  故 C-T9「repo 內不存在任何設定類端點」的主張仍成立。惟該句原寫於成本
  能力不存在時，本輪為重新查證後的確認，非沿用。取得方式：端點清單 grep。

**對上游已核可 artifact 的影響（依 `team.md ## Corrections` 不回改上游）**：
`intent-statement.md` 的 Assumptions 第 5 條把巢狀串流的處置寫成「逐字轉送、
彙整後再送、或兩者並存」，該三個選項預設成本端是 token 級串流；V-F1 顯示
實為狀態事件流，故該框架不成立。上游檔案不回改，以本站的 F15 定案向下游
傳遞。

## F14. 大腦要以哪種方式呼叫既有的成本能力？

本題由上游 Q12=A 逼出，且直接決定 `intent-statement.md` 的假設⑧（既有成本
授權不得被繞過）與⑨（稽核的行為主體認定）如何收斂。依 V-F2，授權掛在
FastAPI dependency 上——呼叫方式不同，這道檢查會不會執行也不同。

- A. **HTTP 呼叫自己的 `/api/cost/v1`，帶使用者的 token**：
  `require_story_action` 真的執行，授權無法被繞過；稽核記的是使用者本人。
- B. **同進程直接呼叫 service 層**：少一跳，但 dependency 不執行，授權須在
  大腦側自行重做，稽核主體須自行決定。
- C. **讀走 service、寫走 HTTP**：兩條路徑的授權語意不一致。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: A  <!-- 2026-09-21T10:09:50Z | Mode: guided | 修訂 1 -->

採 A 的後果：`intent-statement.md` 的假設⑧與⑨**在本站收斂為已定案**——
授權沿用既有 dependency、稽核主體為使用者本人，兩者皆不需新機制。代價為
同一服務內多一跳本機 HTTP。

## F15. 成本 agent 的狀態事件流要怎麼呈現給使用者？

依 V-F1，成本端送的是 job 狀態事件而非 token 串流。

- A. **轉譯狀態事件進大腦的訊息流**：`progress` 轉為進度訊息，`completed`
  後給結果；`timeout`／`failed` 各有對應訊息。
- B. **等 job 完成才開始回覆**：不轉送中間狀態。
- C. **先給確認訊息，完成再追一則**：中間的 `progress` 不轉送。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: A  <!-- 2026-09-21T10:09:50Z | Mode: guided | 修訂 1 -->

採 A 的理由與代價：B 會讓成本類提問的首字等到 job 跑完，與 intent 已核可的
成功指標「首字回應時間」直接矛盾；C 的中間長時間無訊息使「還在跑」與
「卡死了」不可區分，且既有的 `heartbeat` 事件等於浪費。A 的代價是進度文字
與兩種終態（`timeout`／`failed`）的訊息設計屬下游工作。

## 本站不重問的已定案項（修訂 1）

下列在修訂前已定案且與成本前提變動無關，本輪不重問：F1–F7（含三個成功
指標的門檻定案站）、F8（時程與預算約束）、F9（記憶層授權模型）、F10（既有
資料遷移的驗證手段）、F11（成本上限形狀＝B，無硬數字、原則盡量省）、
F12（硬性月費上限）、F13（admin 設定成本上限＝A，不做）。

F11–F13 談的是**本專案自身的 LLM 用量成本上限**（OpenRouter 後台），與
上游 Q12 談的「成本／FinOps 產品能力」是兩件不同的事，不因本輪前提變動而
受影響。

## Consolidated Summary Confirmation

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

<!-- 修訂 1（2026-09-21T10:09:50Z）於本確認之後新增 F14／F15，依 project.md
     `requirements-analysis:260822-ra-L3` 清空並重新取得確認。 -->
[Answer]: Looks correct
